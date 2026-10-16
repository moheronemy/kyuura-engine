"""v0.31: 保留していた 22 枚のために加えた共通の仕組みのテスト（docs/held-cards-v0.31.md 3 章）。

- 決定: 決定するプレイヤー・選べるもの・選ぶ数、不正な答え（ほかのプレイヤー・数・選べないもの）の拒否と原子性（状態・ログ・乱数が変わらない）
- 順番と乱数: コインの数・コインとトラッシュの順番・選んだ順によらないトラッシュの順番
- カードの保存: どの処理でもカードの総数・置き場所が合う（不変条件とログの監査）
- 持続する効果（番をまたぐ）: みちづれ（``DestinyBond``）・バリアー（``AttackBarrier``）・ちいさくなる（``DamageReduction``）・しっぽをふる
  （``CannotAttack``。相手に与える効果）の、はたらく番・期限・ベンチにもどる／進化で消えること
- ダメージを変える効果との関係: プラスパワー（控えへのダメージは変えない）・ディフェンダー・「弱点・抵抗力に関係なく」・ちいさくなる（p.321 の 8 段階）
- 特殊状態との関係: こんらんの「うら」でトラッシュしない（ワザの効果。ほのおのあらし）、ねむり・マヒ・こんらんの特殊能力
- 特殊能力: エナジーバーン（何度でも・番の終わりにもどる）・しぜんになおる（自分の番ごとに 1 回。回数は状態に持つ）・ほのおでかいふく（つけたとき）
- 相手のワザを自分のワザとして使う（ゆびをふる・ちょうのうりょく）: 選べるワザ・条件・弱点の計算・使ったワザの決定
- 書き出しの形式 10（``power_uses_this_turn``・``energy_burn``）
- 先読みの方法（``derived``・``derived_full``・``legacy``）による違いがないこと（ワザ × 盤面 × コインの組み合わせ）

盤面を直接作るテスト（``build_test_state``）は 1 か所の規定を確かめるためのもの。根拠は tests/test_held_cards_v0_31.py の説明と同じ（kyuura データの
採用と、記録のあるエラッタ・裁定。ガイドブックは読んでいない）。原典で決められない場合は tests/test_held_cards_v0_31_stops.py。
"""

from __future__ import annotations

import itertools
import unittest

from kyuura_engine import (
    AttachEnergy,
    EndTurn,
    EngineError,
    IllegalActionError,
    PlayTrainer,
    ResolveDecision,
    UseAttack,
    UsePokemonPower,
    state_to_dict,
)
from kyuura_engine.cards import EnergyType
from kyuura_engine.decisions import DISCARD_ENERGY, SELECT_ATTACK
from kyuura_engine.persistent import attack_barrier, cannot_attack, damage_reduction, destiny_bond
from kyuura_engine.resolution import PREFLIGHT_MODES
from kyuura_engine.rng import rng_fingerprint
from tests.helpers import (
    BASE_GASTLY,
    BLAINES_ARCANINE,
    BLAINES_CHARMELEON,
    BLAINES_NINETALES,
    BLAINES_VULPIX,
    BULBASAUR,
    CHARIZARD,
    CLEFABLE,
    CLEFAIRY,
    DARK_CHARIZARD,
    DARK_ELECTRODE,
    DARK_RAPIDASH,
    DEFENDER,
    EEVEE,
    FIGHTING,
    FIRE,
    GRASS,
    HAUNTER,
    GASTLY,
    HITMONCHAN,
    IVYSAUR,
    LIGHTNING,
    LT_SURGES_ELECTABUZZ,
    MAGMAR,
    MEWTWO,
    MISTYS_GOLDUCK,
    MISTYS_PSYDUCK,
    MOLTRES,
    MUK,
    GRIMER,
    NINETALES,
    PLUSPOWER,
    PSYCHIC,
    RATTATA,
    SLOWPOKE,
    SWITCH,
    GUST,
    V0_31_POKEMON,
    WATER,
    H,
    T,
    apply_kernel,
    build_test_state,
    with_coin_results,
)
from tests.test_held_cards_v0_31 import dealt, events, first, full, mon, play

TURN = 7


def board(active, opponent=None, *, bench=(), opponent_bench=(RATTATA,), hand=(), discard=(), opponent_hand=()):
    return build_test_state([
        {"active": active, "bench": list(bench), "hand": list(hand), "discard": list(discard)},
        {"active": opponent or mon(HITMONCHAN, (FIGHTING, FIGHTING)), "bench": list(opponent_bench), "hand": list(opponent_hand)},
    ], turn_number=TURN)


def snapshot(state):
    return full(state), rng_fingerprint(state.rng), len(state.log)


def total_cards(state):
    count = 0
    for p in state.players:
        count += len(p.hand) + len(p.deck) + len(p.discard) + len(p.prizes)
        for pokemon in p.in_play():
            count += len(pokemon.cards()) + len(pokemon.energy) + len(pokemon.trainers)
    return count + len(state.trainer_in_use or ())


def end_turn(state):
    """番を終えて、相手の番（ポケモンチェックのあと）に進める。"""
    return apply_kernel(state, EndTurn(state.current_player))


class DecisionTest(unittest.TestCase):
    """新しい決定の形と、不正な答えの拒否（原子性）。"""

    def assert_rejected(self, state, answer, player=None):
        d = state.decision
        before = snapshot(state)
        with self.assertRaises(EngineError):
            apply_kernel(state, ResolveDecision(d.player if player is None else player, d.id, tuple(answer)))
        self.assertEqual(snapshot(state), before)

    def test_invalid_answers_are_rejected_without_changes(self):
        """どの決定も、決定するプレイヤーでない・選ぶ数が違う・選べないもの・同じものを 2 回のどれも拒否し、状態・乱数・ログを変えない。"""
        cases = [
            # (盤面, ワザの位置, 決定の前の答え)
            (board(mon(NINETALES, (FIRE, FIRE)), opponent_bench=(RATTATA, BULBASAUR)), 0, ()),  # かどわかす
            (board(mon(CHARIZARD, (FIRE,) * 4)), 0, ()),  # ほのおのうず（2 枚）
            (board(mon(MOLTRES, (FIRE, FIRE))), 0, ()),  # やまやき（好きなだけ）
            (board(mon(SLOWPOKE, (PSYCHIC, PSYCHIC)), discard=(PLUSPOWER,)), 1, (first(),)),  # ゴミあさり（トレーナー）
            (board(mon(DARK_RAPIDASH, (FIRE, FIRE)), opponent_bench=(RATTATA, BULBASAUR)), 1, (first(),)),  # ひばしら（控え）
            (board(mon(DARK_ELECTRODE, (LIGHTNING, LIGHTNING)), bench=(RATTATA,)), 1, ()),  # エナジーボム（控え）
            (board(mon(LT_SURGES_ELECTABUZZ, (LIGHTNING,)), discard=(LIGHTNING, LIGHTNING)), 0, ()),  # たいでん
            (with_coin_results(board(mon(MISTYS_GOLDUCK, (WATER, PSYCHIC)), opponent=mon(HITMONCHAN, (FIGHTING,))), H), 1, ()),  # スーパーデストロイ
            (board(mon(CLEFABLE, (FIRE,))), 0, ()),  # ゆびをふる（ワザ）
        ]
        for state, index, before in cases:
            state = play(state, UseAttack(0, index), before)
            d = state.decision
            with self.subTest(kind=d.kind, attack=index):
                self.assertEqual(d.player, 0)
                self.assert_rejected(state, d.options[: max(d.min_choices, 1)], player=1)
                self.assert_rejected(state, (max(d.options) + 1000,))
                if d.max_choices < len(d.options):
                    self.assert_rejected(state, d.options[: d.max_choices + 1])
                if d.min_choices > 1:
                    self.assert_rejected(state, d.options[: d.min_choices - 1])
                if d.max_choices >= 2:
                    self.assert_rejected(state, (d.options[0], d.options[0]))
                # ほかの操作も受け付けない（決定を待つ間）
                before_snapshot = snapshot(state)
                for command in (EndTurn(0), UseAttack(0, 0), EndTurn(1)):
                    with self.assertRaises(EngineError):
                        apply_kernel(state, command)
                self.assertEqual(snapshot(state), before_snapshot)

    def test_discard_order_does_not_depend_on_the_choice_order(self):
        """2 枚以上を選ぶトラッシュは、選んだ順ではなく、ついている順にトラッシュする（順番で結果が変わらない）。"""
        state = board(mon(CHARIZARD, (FIRE, WATER, FIRE, FIRE, FIRE)))
        energy = list(state.players[0].active.energy)
        a = play(state, UseAttack(0, 0), [(energy[3], energy[1])])
        b = play(state, UseAttack(0, 0), [(energy[1], energy[3])])
        self.assertEqual(full(a), full(b))
        self.assertEqual([e["energy"] for e in events(a, len(state.log), "discard_energy")], [energy[1], energy[3]])

    def test_dark_charizard_coins_then_damage_then_discard(self):
        """れんぞくファイヤーボール: コインはついている炎の枚数（ほかのタイプは数えない）、ダメージのあとにトラッシュの決定（「おもて」の数ちょうど）。"""
        state = with_coin_results(board(mon(DARK_CHARIZARD, (FIRE, WATER, FIRE)), opponent=mon(HITMONCHAN)), H, H)
        new = apply_kernel(state, UseAttack(0, 1))
        coins = [e for e in events(new, len(state.log), "coin_flip") if e.get("source") == "attack"]
        self.assertEqual(len(coins), 2)
        kinds = [e["kind"] for e in events(new, len(state.log)) if e["kind"] in ("coin_flip", "damage")]
        self.assertEqual(kinds[-1], "damage")
        self.assertEqual((new.decision.kind, new.decision.min_choices, new.decision.max_choices, len(new.decision.options)), (DISCARD_ENERGY, 2, 2, 2))

    def test_electabuzz_discharge_flips_after_the_discard(self):
        """ほうでん: 雷をすべてトラッシュしてから、トラッシュした枚数ぶんのコイン（雷 0 枚なら起こらない。必要なエネルギーに雷がある）。"""
        state = with_coin_results(board(mon(LT_SURGES_ELECTABUZZ, (LIGHTNING, LIGHTNING, LIGHTNING)), opponent=mon(HITMONCHAN)), H, H, T)
        new = apply_kernel(state, UseAttack(0, 1))
        order = [e["kind"] for e in events(new, len(state.log)) if e["kind"] in ("discard_energy", "coin_flip", "damage")]
        self.assertEqual(order, ["discard_energy"] * 3 + ["coin_flip"] * 3 + ["damage"])
        self.assertEqual(dealt(new, len(state.log)), [60])


class ConservationTest(unittest.TestCase):
    """カードを動かすワザ（トラッシュ・山札・手札・控えにつける・相手のエネルギー）のあとも、カードの総数は同じ（盤面を直接作るので、ログの監査は
    正式な開始からの対戦で確かめる。tests/test_held_cards_v0_31_games.py）。"""

    def test_cards_are_conserved(self):
        cases = [
            (board(mon(MOLTRES, (FIRE, FIRE))), UseAttack(0, 0), [first(2)]),
            (board(mon(DARK_ELECTRODE, (LIGHTNING, LIGHTNING, FIRE)), bench=(RATTATA, BULBASAUR)), UseAttack(0, 1), [first(), first(), first()]),
            (board(mon(LT_SURGES_ELECTABUZZ, (LIGHTNING,)), discard=(LIGHTNING, LIGHTNING, LIGHTNING)), UseAttack(0, 0), [first(2)]),
            (board(mon(SLOWPOKE, (PSYCHIC, PSYCHIC)), discard=(PLUSPOWER, SWITCH)), UseAttack(0, 1), [first(), first()]),
            (with_coin_results(board(mon(MISTYS_GOLDUCK, (WATER, PSYCHIC)), opponent=mon(HITMONCHAN, (FIGHTING, FIGHTING)),
                                     opponent_bench=(mon(RATTATA, (FIRE,)),)), H), UseAttack(0, 1), [first(), first()]),
            (board(mon(BLAINES_CHARMELEON, (FIRE, FIRE, FIRE))), UseAttack(0, 1), [first(2)]),
            (board(mon("PMCG6-031", (FIRE, FIRE, FIRE))), UseAttack(0, 1), []),
            (board(mon("PMCG4-022", (PSYCHIC,))), UseAttack(0, 0), [first()]),
        ]
        for state, command, answers in cases:
            with self.subTest(card=state.card_def(state.players[0].active.card).id):
                total = total_cards(state)
                new = play(state, command, answers)
                self.assertEqual(total_cards(new), total)  # 不変条件（カードの保存則）は apply_command が確かめる


class PersistentEffectTest(unittest.TestCase):
    """番をまたぐ持続する効果（次の相手の番にはたらき、その番の終わりに消える。ベンチにもどる・進化・きぜつで消える。v0.4b と同じ置き場所と契機）。
    ワザを使うと番が終わるので、ワザのあとの状態は相手の番（8 番・プレイヤー 1）。"""

    def test_destiny_bond(self):
        """みちづれ: 次の相手の番に自分が相手のワザで「きぜつ」したら、相手の対戦ポケモンも「きぜつ」する（ログ ``destiny_bond``）。両方が
        サイドを取る（勝ち負けが決まらない場面）。きぜつしなければ何もしない（ゴースの抵抗力 闘 で、エビワラーのスペシャルパンチは 10）。"""
        for opponent, attack, knocked in ((mon(HITMONCHAN, (FIGHTING,) * 3), 1, False), (mon(MAGMAR, (FIRE, FIRE)), 0, True)):
            state = board(mon(BASE_GASTLY, (PSYCHIC, PSYCHIC)), opponent=opponent, bench=(RATTATA,))
            state = play(state, UseAttack(0, 1), [first()])
            self.assertEqual((state.turn_number, state.current_player), (TURN + 1, 1))
            self.assertIsNotNone(destiny_bond(state, state.players[0].active))
            new = apply_kernel(state, UseAttack(1, attack))
            with self.subTest(knocked=knocked):
                self.assertEqual(len(events(new, len(state.log), "destiny_bond")), int(knocked))
                self.assertEqual(sorted(e["player"] for e in events(new, len(state.log), "knock_out")), [0, 1] if knocked else [])

    def test_destiny_bond_works_only_on_the_next_opponent_turn(self):
        """みちづれは、与えた番 + 1（次の相手の番）だけにはたらき、その番の終わりに消える（理由 ``expired``）。"""
        state = play(board(mon(BASE_GASTLY, (PSYCHIC, PSYCHIC))), UseAttack(0, 1), [first()])
        [effect] = state.players[0].active.persistent_effects
        self.assertEqual((effect.created_turn, effect.active_turn), (TURN, TURN + 1))
        later = end_turn(state)
        self.assertEqual(later.players[0].active.persistent_effects, ())
        self.assertIn("expired", [e["reason"] for e in later.log[len(state.log):] if e["kind"] == "persistent_effect_removed"])

    def test_barrier(self):
        """バリアー: 次の相手の番、相手のワザのダメージ・効果を受けない（ダメージの要素は無効。ログ ``damage_prevented``）。"""
        state = play(board(mon(MEWTWO, (PSYCHIC, PSYCHIC)), opponent=mon(HITMONCHAN, (FIGHTING,) * 3)), UseAttack(0, 1), [first()])
        self.assertIsNotNone(attack_barrier(state, state.players[0].active))
        new = apply_kernel(state, UseAttack(1, 1))
        self.assertEqual(new.players[0].active.damage, 0)
        self.assertEqual(len(events(new, len(state.log), "damage_prevented")), 1)

    def test_barrier_is_removed_when_the_pokemon_leaves_the_active_spot(self):
        """自分に与えた持続する効果（バリアー）は、相手の番に突風でベンチにもどされると消える（理由 ``switch``）。もどったポケモンにはもうはたらかない。"""
        state = build_test_state([
            {"active": mon(MEWTWO, (PSYCHIC, PSYCHIC)), "bench": [mon(RATTATA, (FIRE,))]},
            {"active": mon(HITMONCHAN, (FIGHTING,) * 3), "bench": [RATTATA], "hand": [GUST]},
        ], turn_number=TURN)
        state = play(state, UseAttack(0, 1), [first()])
        gust = next(uid for uid in state.players[1].hand if state.card_def(uid).id == GUST)
        new = play(state, PlayTrainer(1, gust), [first()])
        mewtwo = new.players[0].bench[0]
        self.assertEqual((new.card_def(mewtwo.card).id, mewtwo.persistent_effects), (MEWTWO, ()))
        self.assertIn("switch", [e["reason"] for e in new.log[len(state.log):] if e["kind"] == "persistent_effect_removed"])

    def test_minimize_is_step_8(self):
        """ちいさくなる: 次の相手の番に受けるダメージを 20 へらす（p.321 の 8 段階。弱点のあと）。エビワラーのジャブ 20 → 弱点 闘で 40 → 20。"""
        state = play(board(mon(CLEFABLE, (FIRE, FIRE)), opponent=mon(HITMONCHAN, (FIGHTING, FIGHTING))), UseAttack(0, 1))
        self.assertIsNotNone(damage_reduction(state, state.players[0].active))
        new = apply_kernel(state, UseAttack(1, 0))
        self.assertEqual(new.players[0].active.damage, 20)
        [damage] = events(new, len(state.log), "damage")
        self.assertEqual((damage["amount"], damage["weakness"]), (20, True))

    def test_tail_wag_locks_the_defender_for_one_turn(self):
        """しっぽをふる（「おもて」）: 相手の対戦ポケモンは次の相手の番にワザを使えない（``ATTACK_PREVENTED``。拒否は状態を変えない）。その番の終わりに
        消える。ベンチにもどれば消え、入れ替わった控えはワザを使える。"""
        state = with_coin_results(board(mon(EEVEE, (FIRE,)), opponent=mon(HITMONCHAN, (FIGHTING, FIGHTING))), H)
        state = apply_kernel(state, UseAttack(0, 0))
        self.assertIsNotNone(cannot_attack(state, state.players[1].active))
        before = snapshot(state)
        with self.assertRaises(IllegalActionError) as ctx:
            apply_kernel(state, UseAttack(1, 0))
        self.assertEqual(ctx.exception.code, "ATTACK_PREVENTED")
        self.assertEqual(snapshot(state), before)
        later = end_turn(state)
        self.assertEqual(later.players[1].active.persistent_effects, ())
        state2 = with_coin_results(board(mon(EEVEE, (FIRE,)), opponent=mon(HITMONCHAN, (FIGHTING, FIGHTING)),
                                         opponent_bench=(mon(RATTATA, (FIRE,)),), opponent_hand=(SWITCH,)), H)
        state2 = apply_kernel(state2, UseAttack(0, 0))
        switch = next(uid for uid in state2.players[1].hand if state2.card_def(uid).id == SWITCH)
        state2 = play(state2, PlayTrainer(1, switch), [first()])
        self.assertEqual([p.persistent_effects for p in state2.players[1].bench], [()])
        apply_kernel(state2, UseAttack(1, 0))


class DamageModifierTest(unittest.TestCase):
    def test_pluspower_does_not_change_bench_damage(self):
        """やきはらう・ひばしら・もえひろがる: 控えへのダメージはプラスパワーで変わらない（p.257 の最新の説明「控えポケモンへのダメージは、そのまま」）。
        対戦ポケモンへのダメージは + 10（やきはらうは弱点・抵抗力に関係なく）。"""
        state = with_coin_results(board(mon(BLAINES_CHARMELEON, (FIRE, FIRE, FIRE), trainers=[(PLUSPOWER, TURN)]), opponent=mon(BULBASAUR),
                                        opponent_bench=(BULBASAUR, RATTATA)), H, T, T)
        new = play(state, UseAttack(0, 1), [first()])
        self.assertEqual((dealt(new, len(state.log)), [p.damage for p in new.players[1].bench]), ([20], [10, 10]))
        state = board(mon("PMCG6-027", (FIRE, FIRE), trainers=[(PLUSPOWER, TURN)]), opponent=mon(HITMONCHAN),
                      opponent_bench=(BULBASAUR,))
        new = play(state, UseAttack(0, 0))
        self.assertEqual((dealt(new, len(state.log)), [p.damage for p in new.players[1].bench]), ([30], [10]))

    def test_weakness_and_resistance_are_ignored_where_the_text_says_so(self):
        """「弱点・抵抗力に関係なく」のダメージ（やきはらうの対戦ポケモン・控え、ひばしら・もえひろがるの控え）はログに ``ignore_weakness_resistance``。
        ほかのダメージは今までどおり計算する（もえひろがるの対戦ポケモン: 弱点 炎のフシギダネに 20 → 40）。"""
        state = board(mon("PMCG6-027", (FIRE, FIRE)), opponent=mon(BULBASAUR), opponent_bench=(BULBASAUR,))
        new = play(state, UseAttack(0, 0))
        logs = events(new, len(state.log), "damage")
        self.assertEqual([(e["amount"], e.get("ignore_weakness_resistance", False)) for e in logs], [(40, False), (10, True)])

    def test_defender_on_the_opponent_active(self):
        """ディフェンダー（7 段階）は、やきはらうの対戦ポケモンへのダメージも 20 へらす（弱点・抵抗力だけを計算しない）。"""
        state = with_coin_results(board(mon(BLAINES_CHARMELEON, (FIRE, FIRE, FIRE)),
                                        opponent=mon(HITMONCHAN, (FIGHTING,), trainers=[(DEFENDER, TURN)])), H, H, H)
        new = play(state, UseAttack(0, 1), [first(3)])
        self.assertEqual(dealt(new, len(state.log)), [10])


class ConfusionTest(unittest.TestCase):
    def test_storm_discards_only_after_the_confusion_coin(self):
        """ほのおのあらし（RUL-ENERGY-DISCARD-ATTACKS の範囲。トラッシュはワザの効果）: こんらんの「うら」ならトラッシュしない（20 を受ける）、
        「おもて」ならトラッシュして 120。"""
        state = with_coin_results(board(mon(BLAINES_ARCANINE, (FIRE,) * 4, confusion=True)), T)
        new = apply_kernel(state, UseAttack(0, 1))
        self.assertEqual((len(new.players[0].active.energy), new.players[0].active.damage), (4, 20))
        state = with_coin_results(board(mon(BLAINES_ARCANINE, (FIRE,) * 4, confusion=True), opponent=mon(HITMONCHAN)), H)
        new = play(state, UseAttack(0, 1), [first(3)])
        self.assertEqual((len(new.players[0].active.energy), dealt(new, len(state.log))), (1, [120]))


class PowerTest(unittest.TestCase):
    def test_energy_burn(self):
        """エナジーバーン（TXT-CHARIZARD）: 何度でも使える。使った時点でついているエネルギーはこの番「炎」になり（あとでつけたカードはもう一度使うまで
        もとのまま）、番の終わりにもどる。ねむり・マヒ・こんらんのとき使えない。かがくへんかガスで使えない。"""
        state = board(mon(CHARIZARD, (WATER, WATER, WATER, FIRE)), hand=(WATER,), opponent=mon(HITMONCHAN))
        pid = state.players[0].active.pokemon_id
        with self.assertRaises(IllegalActionError):
            apply_kernel(state, UseAttack(0, 0))  # 炎 1 枚では「ほのおのうず」を使えない
        burned = apply_kernel(state, UsePokemonPower(0, pid, 0))
        self.assertEqual(burned.energy_types(burned.players[0].active), [EnergyType.FIRE] * 4)
        again = apply_kernel(burned, UsePokemonPower(0, pid, 0))  # 何度でも
        self.assertEqual(again.energy_burn, burned.energy_burn)
        attached = apply_kernel(burned, AttachEnergy(0, burned.players[0].hand[0], burned.players[0].active.card))
        self.assertEqual(attached.energy_types(attached.players[0].active).count(EnergyType.WATER), 1)
        new = play(burned, UseAttack(0, 0), [first(2)])
        self.assertEqual(dealt(new, len(burned.log)), [100])
        self.assertEqual(state_to_dict(end_turn(burned), format_version=10)["energy_burn"], [])
        for flag in ({"sleep": True}, {"confusion": True}, {"paralysis": TURN}):
            blocked = board(mon(CHARIZARD, (WATER,) * 4, **flag))
            before = snapshot(blocked)
            with self.assertRaises(EngineError):
                apply_kernel(blocked, UsePokemonPower(0, blocked.players[0].active.pokemon_id, 0))
            self.assertEqual(snapshot(blocked), before)
        gassed = board(mon(CHARIZARD, (WATER,) * 4), opponent=mon(MUK, evolved_from=GRIMER))
        with self.assertRaises(EngineError) as ctx:
            apply_kernel(gassed, UsePokemonPower(0, gassed.players[0].active.pokemon_id, 0))
        self.assertEqual(ctx.exception.code, "POWER_SUPPRESSED")

    def test_natural_cure_once_per_turn(self):
        """しぜんになおる: 自分の番ごとに 1 回、ダメージカウンターを 1 つとりのぞく。回数は状態（``power_uses_this_turn``）に持ち、次の自分の番に
        また使える。2 回目は ``POWER_ALREADY_USED``（状態を変えない）。"""
        state = board(mon(BLAINES_VULPIX, (FIRE,), damage=30))
        pid = state.players[0].active.pokemon_id
        once = apply_kernel(state, UsePokemonPower(0, pid, 0))
        self.assertEqual((once.players[0].active.damage, once.power_uses_this_turn), (20, ((pid, 0),)))
        before = snapshot(once)
        with self.assertRaises(IllegalActionError) as ctx:
            apply_kernel(once, UsePokemonPower(0, pid, 0))
        self.assertEqual(ctx.exception.code, "POWER_ALREADY_USED")
        self.assertEqual(snapshot(once), before)
        mine_again = end_turn(end_turn(once))
        self.assertEqual(mine_again.power_uses_this_turn, ())
        self.assertEqual(apply_kernel(mine_again, UsePokemonPower(0, pid, 0)).players[0].active.damage, 10)
        with self.assertRaises(ValueError):
            state_to_dict(once, format_version=9)

    def test_fire_recovery_on_attach(self):
        """ほのおでかいふく: このカードに「炎」の基本エネルギーカードをつけるたびに 1 つとりのぞく（手札からつけた・エナジーボムでつけた）。ほかのタイプ・
        ねむり・マヒ・こんらん・かがくへんかガス・ダメージなしでははたらかない。"""
        cases = [((FIRE,), {}, 10), ((WATER,), {}, 20), ((FIRE,), {"confusion": True}, 20), ((FIRE,), {"damage": 0}, 0)]
        for hand, flags, after in cases:
            spec = mon(BLAINES_NINETALES, (FIRE,), **({"damage": 20} | flags))
            state = board(spec, hand=hand)
            with self.subTest(hand=hand, flags=flags):
                new = apply_kernel(state, AttachEnergy(0, state.players[0].hand[0], state.players[0].active.card))
                self.assertEqual(new.players[0].active.damage, after)
                self.assertEqual(len(events(new, len(state.log), "power_heal")), 1 if after == 10 else 0)
        gassed = board(mon(BLAINES_NINETALES, (FIRE,), damage=20), hand=(FIRE,), opponent=mon(MUK, evolved_from=GRIMER))
        new = apply_kernel(gassed, AttachEnergy(0, gassed.players[0].hand[0], gassed.players[0].active.card))
        self.assertEqual(new.players[0].active.damage, 20)
        # エナジーボムで控えのカツラのキュウコンに「炎」をつけたときもはたらく
        state = board(mon(DARK_ELECTRODE, (LIGHTNING, LIGHTNING, FIRE)), bench=(mon(BLAINES_NINETALES, (), damage=30),))
        bench = state.players[0].bench[0].pokemon_id
        new = play(state, UseAttack(0, 1), [(bench,), (bench,), (bench,)])
        self.assertEqual(new.players[0].bench[0].damage, 20)

    def test_powers_are_rejected_when_not_declarable(self):
        """ほのおでかいふくは宣言しない（``POWER_NOT_DECLARABLE``）。"""
        state = board(mon(BLAINES_NINETALES, (FIRE,), damage=20))
        with self.assertRaises(IllegalActionError) as ctx:
            apply_kernel(state, UsePokemonPower(0, state.players[0].active.pokemon_id, 0))
        self.assertEqual(ctx.exception.code, "POWER_NOT_DECLARABLE")


class CopyAttackTest(unittest.TestCase):
    """相手のワザを自分のワザとして使う（ゆびをふる・ちょうのうりょくの「おもて」3 枚）。"""

    def test_clause_decides_which_attacks_can_be_chosen(self):
        """ほのおのあらし（「…トラッシュしなければ、このワザは使えない」）は、炎のないピクシー（ほかに必要な条件がたりなければ使えない）・ピッピ
        （説明にしたがう）のどちらでも選べない。だいもんじ（RUL-ENERGY-DISCARD-ATTACKS。トラッシュできなければダメージがなくなる）は、ピッピは説明に
        したがって使え、ダメージはない。ピクシーは、トラッシュが「ほかに必要な条件」にあたるか決められないので、選べるが選ぶと止まる（HC9）。"""
        for card, index in ((CLEFABLE, 0), (CLEFAIRY, 1)):
            state = play(board(mon(card, (WATER, WATER, WATER)), opponent=mon(BLAINES_ARCANINE, (FIRE,))), UseAttack(0, index))
            self.assertEqual((state.decision.kind, tuple(state.decision.options)), (SELECT_ATTACK, (0,)))
        state = play(board(mon(CLEFAIRY, (WATER, WATER, WATER)), opponent=mon(NINETALES, (FIRE,))), UseAttack(0, 1))
        self.assertEqual((tuple(state.decision.options), state.decision.context_value("unresolved_choices", ())), ((0, 1), ()))
        new = play(state, ResolveDecision(0, state.decision.id, (1,)))
        self.assertEqual(dealt(new, len(state.log)), [])
        self.assertEqual(len(events(new, len(state.log), "discard_energy_failed")), 1)
        state = play(board(mon(CLEFABLE, (WATER,)), opponent=mon(NINETALES, (FIRE,))), UseAttack(0, 0))
        self.assertEqual((tuple(state.decision.options), state.decision.context_value("unresolved_choices")), ((0, 1), (1,)))
        before = snapshot(state)
        with self.assertRaises(EngineError) as ctx:
            apply_kernel(state, ResolveDecision(0, state.decision.id, (1,)))
        self.assertEqual(ctx.exception.code, "UNRESOLVED_COPIED_ATTACK")
        self.assertEqual(snapshot(state), before)

    def test_copied_attack_uses_the_copier_type(self):
        """使ったワザのダメージの弱点・抵抗力は、ワザを使ったポケモンのタイプで計算する（ピクシーは無色。エビワラーの弱点 超にはかからない）。カスミの
        コダック（水）がフシギダネ（弱点 炎）のワザを使っても弱点にかからない。"""
        state = with_coin_results(board(mon(MISTYS_PSYDUCK, (PSYCHIC,)), opponent=mon(IVYSAUR, evolved_from=BULBASAUR)), H, H, H)
        new = play(state, UseAttack(0, 0), [(0,)])
        self.assertEqual(dealt(new, len(state.log)), [30])  # フシギソウの「つるのムチ」30。草のフシギソウに水のワザ（抵抗力なし）

    def test_copied_attack_with_a_decision(self):
        """使ったワザの決定（だいもんじの炎のトラッシュ）は、ワザを使ったポケモンについているカードから選ぶ（相手のカードではない）。"""
        state = play(board(mon(CLEFABLE, (FIRE, FIRE)), opponent=mon(NINETALES, (FIRE,))), UseAttack(0, 0), [(1,)])
        self.assertEqual(state.decision.kind, DISCARD_ENERGY)
        self.assertEqual(set(state.decision.options), set(state.players[0].active.energy))
        new = play(state, ResolveDecision(0, state.decision.id, (state.decision.options[0],)))
        self.assertEqual(dealt(new, len(state.log)), [80])
        self.assertEqual(len(new.players[0].active.energy), 1)


class FormatTest(unittest.TestCase):
    def test_format_10_fields(self):
        """形式 10 は 9 に ``power_uses_this_turn``・``energy_burn`` を加えた。どちらも空なら形式 1〜9 も今までどおり書き出せる。"""
        state = board(mon(CHARIZARD, (WATER,) * 4))
        self.assertEqual(state_to_dict(state, format_version=10)["power_uses_this_turn"], [])
        self.assertNotIn("energy_burn", state_to_dict(state, format_version=9))
        burned = apply_kernel(state, UsePokemonPower(0, state.players[0].active.pokemon_id, 0))
        data = state_to_dict(burned, format_version=10)
        self.assertEqual(len(data["energy_burn"]), 4)
        for version in range(1, 10):
            with self.subTest(version=version), self.assertRaises(ValueError):
                state_to_dict(burned, format_version=version)


class PreflightParityTest(unittest.TestCase):
    """v0.31 のすべてのワザを、相手の状態・自分の状態・コインの組み合わせで使い、先読みの方法のどれでも結果（受け付けたら形式 10 の書き出しと
    乱数、拒否したら例外の型とコード）が同じ（決定には最初の選べるものから答える）。"""

    OPPONENTS = {
        "plain": mon(HITMONCHAN, (FIGHTING, FIGHTING)),
        "defender": mon(HITMONCHAN, (FIGHTING,), trainers=[(DEFENDER, TURN)]),
        "haunter": mon(HAUNTER, (PSYCHIC,), evolved_from=GASTLY),
        "hurt": mon(HITMONCHAN, (FIGHTING,), damage=50),
    }

    def outcome(self, state, command, mode):
        try:
            new = apply_kernel(state, command, preflight=mode)
            steps = 0
            out = [(full(new), rng_fingerprint(new.rng))]
            while new.decision is not None and new.decision.resume == "attack" and steps < 8:
                d = new.decision
                blocked = set(d.context_value("unresolved_choices", ())) | set(d.context_value("unsupported_choices", ()))
                options = [o for o in d.options if o not in blocked] or list(d.options)
                count = max(d.min_choices, min(1, d.max_choices))
                new = apply_kernel(new, ResolveDecision(d.player, d.id, tuple(options[:count])), preflight=mode)
                out.append((full(new), rng_fingerprint(new.rng)))
                steps += 1
            return out
        except EngineError as error:
            return [(type(error).__name__, error.code)]

    def test_every_attack_in_every_mode(self):
        pool_attacks = [(card, attack.index, attack.cost) for card in V0_31_POKEMON
                        for attack in __import__("kyuura_engine").cards.load_card_pool().get(card).attacks]
        energy_of = {"fire": FIRE, "water": WATER, "lightning": LIGHTNING, "psychic": PSYCHIC, "grass": GRASS, "fighting": FIGHTING}
        checked = 0
        for (card, index, cost), (name, opponent), confused, coins in itertools.product(
                pool_attacks, self.OPPONENTS.items(), (False, True), ((H,) * 8, (T,) * 8, (H, T) * 4)):
            energy = [energy_of.get(t.value, FIRE) for t in cost] + [FIRE]
            attacker = mon(card, energy, damage=20, **({"confusion": True} if confused else {}))
            state = with_coin_results(build_test_state([
                {"active": attacker, "bench": [mon(RATTATA, (FIRE,))], "discard": [LIGHTNING, FIRE, PLUSPOWER], "deck": [FIRE, WATER] * 4},
                {"active": opponent, "bench": [RATTATA, mon(BULBASAUR, (GRASS,))], "deck": [FIRE] * 6},
            ], turn_number=TURN), *coins)
            results = [self.outcome(state, UseAttack(0, index), mode) for mode in PREFLIGHT_MODES]
            with self.subTest(card=card, attack=index, opponent=name, confused=confused, coins=coins[:2]):
                self.assertEqual(results[1], results[0])
                self.assertEqual(results[2], results[0])
            checked += 1
        self.assertEqual(checked, 52 * 4 * 2 * 3)


if __name__ == "__main__":
    unittest.main()

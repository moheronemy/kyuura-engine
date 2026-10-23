"""原典で決められない 5 件の裁定の回帰テストと境界（v0.3d。docs/unresolved-rulings-v0.3d.md）。

v0.3d で『ポケモンカードオフィシャルブック2000』を読み直しても決められなかった 5 件について、止める条件がちょうど
「決められない場合」だけであること（広すぎず狭すぎない）と、止める位置（乱数・ダメージ・エネルギーの前）を確かめる。

1. ``UNRESOLVED_RETREAT_AFTER_CONFUSION_CLEARED``（p.311。こんらんで「にげる」に失敗したあと、こんらんが消えて同じ番に
   バトル場に戻ったポケモンの再宣言）
2. ``UNRESOLVED_CONFUSION_DAMAGE_MODIFIERS``（p.257・p.309・p.321・p.322。こんらんの 20 とプラスパワー・ディフェンダー）
3. ``UNRESOLVED_POKEMON_CHECK_DOUBLE_KNOCKOUT``（pp.323〜325。ポケモンチェックのどくで両方の対戦ポケモンがきぜつ）
4. ``UNRESOLVED_POKEMON_CHECK_SLEEP_COIN_ORDER``（p.323・p.325。両方の対戦ポケモンがねむり）
5. ``UNRESOLVED_REPARALYSIS_RECOVERY_TURN``（p.322・p.323。マヒの再付与で回復する番が変わる）
"""

import itertools
import unittest

from kyuura_engine import (
    AttachEnergy,
    EndTurn,
    EngineError,
    Phase,
    PlayTrainer,
    ResolveDecision,
    Retreat,
    UnsupportedError,
    apply_command,
    check_invariants,
    load_card_pool,
    state_to_dict,
)
from kyuura_engine.conditions import paralyze
from kyuura_engine.damage import (
    DamageModifier,
    calculate_attack_damage,
    calculate_confusion_damage,
)
from kyuura_engine.effects import EQUIVALENT_CARDS
from kyuura_engine.rng import rng_fingerprint
from kyuura_engine.rules import RULES_2000_02_14
from tests.helpers import (
    FIRE,
    GROWLITHE,
    PONYTA,
    RATTATA,
    SWITCH,
    V0_69_POKEMON,
    VULPIX,
    H,
    T,
    build_test_state,
    with_coin_results,
)


def full(state):
    return state_to_dict(state, format_version=6)


def kinds(events):
    return [e["kind"] for e in events]


def assert_unchanged_rejection(test, state, command, code):
    before, fingerprint = full(state), rng_fingerprint(state.rng)
    with test.assertRaises(EngineError) as ctx:
        apply_command(state, command)
    test.assertEqual(ctx.exception.code, code)
    test.assertEqual((full(state), rng_fingerprint(state.rng)), (before, fingerprint))


# ---------------------------------------------------------------- 1. にげるの失敗のあと、こんらんが消えたポケモン


class RetreatAfterConfusionClearedTest(unittest.TestCase):
    """p.311「一度「にげる」に失敗したこんらん状態のポケモンは、今の自分の番では、もう「にげる」を宣言することができません」。
    「こんらん状態の」が、失敗したときの状態を指すのか、宣言するときの状態を指すのかが決められない。"""

    def failed(self):
        state = build_test_state([
            {"active": {"card": VULPIX, "energy": [FIRE, FIRE, FIRE], "confusion": True}, "bench": [PONYTA, GROWLITHE],
             "hand": [SWITCH, FIRE]},
            {"active": GROWLITHE, "bench": [RATTATA]},
        ])
        vulpix = state.players[0].active
        state = apply_command(with_coin_results(state, T), Retreat(0, (vulpix.energy[0],), state.players[0].bench[0].card))
        self.assertEqual(state.players[0].active.retreat_failed_turn, 3)
        return state, vulpix.pokemon_id

    def test_back_by_retreat_of_the_other_pokemon(self):
        """ポケモンいれかえで控えに戻し、新しい対戦ポケモンの「にげる」でバトル場に戻した場合も止める（ポケモンいれかえを
        2 回使う場合と同じ）。止めるのはエネルギーのトラッシュ・コインの前。"""
        state, vulpix_id = self.failed()
        switch = next(u for u in state.players[0].hand if state.cards[u].card_id == SWITCH)
        state = apply_command(state, PlayTrainer(0, switch))
        ponyta = state.players[0].bench[0]
        state = apply_command(state, ResolveDecision(0, state.decision.id, (ponyta.pokemon_id,)))
        energy = next(u for u in state.players[0].hand if state.cards[u].card_id == FIRE)
        state = apply_command(state, AttachEnergy(0, energy, ponyta.card))
        vulpix = state.find_pokemon(vulpix_id)[1]
        state = apply_command(state, Retreat(0, (state.players[0].active.energy[0],), vulpix.card))  # ポニータがにげる
        self.assertIs(state.players[0].active, state.find_pokemon(vulpix_id)[1])
        self.assertFalse(state.players[0].active.conditions.confused)
        command = Retreat(0, (state.players[0].active.energy[0],), state.players[0].bench[0].card)
        assert_unchanged_rejection(self, state, command, "UNRESOLVED_RETREAT_AFTER_CONFUSION_CLEARED")

    def test_boundaries(self):
        """止めるのは「記録があり、こんらんでない」ときだけ。こんらんのままなら決まる（RETREAT_ALREADY_FAILED）。記録のない
        ポケモン・次の番は、ふつうに宣言できる。"""
        state, vulpix_id = self.failed()
        assert_unchanged_rejection(self, state, Retreat(0, (state.players[0].active.energy[0],), state.players[0].bench[0].card),
                                   "RETREAT_ALREADY_FAILED")
        state = apply_command(apply_command(state, EndTurn(0)), EndTurn(1))
        self.assertIsNone(state.find_pokemon(vulpix_id)[1].retreat_failed_turn)
        new = apply_command(with_coin_results(state, H), Retreat(0, (state.players[0].active.energy[0],), state.players[0].bench[0].card))
        self.assertEqual(new.players[0].bench[0].pokemon_id, vulpix_id)


# ---------------------------------------------------------------- 2. こんらんの 20 とプラスパワー・ディフェンダー


def confusion_interpretations(definition, pluspowers, defenders):
    """こんらんの 20 の、ありうる読み方ごとの結果（docs/unresolved-rulings-v0.3d.md 2 章）。

    - プラスパワー（5 段階）・ディフェンダー（7 段階）を、それぞれ計算する・しないの 4 通り（こんらんのダメージが「ワザに
      よるダメージ」か、プラスパワーの「このカードをつけているポケモンのワザが…ダメージを与えるとき」にあたるかで分かれる）
    - 弱点・抵抗力は、どの読み方でも計算する（p.322）
    """
    results = {}
    for use_pluspower, use_defender in itertools.product((False, True), repeat=2):
        modifiers = ([DamageModifier(5, 10, "プラスパワー")] * pluspowers if use_pluspower else []) + \
                    ([DamageModifier(7, -20, "ディフェンダー")] * defenders if use_defender else [])
        if not modifiers:
            results[(use_pluspower, use_defender)] = calculate_confusion_damage(definition, RULES_2000_02_14, 20).final
        else:
            results[(use_pluspower, use_defender)] = calculate_attack_damage(20, definition, definition, RULES_2000_02_14, modifiers).final
    return results


class ConfusionDamageModifiersTest(unittest.TestCase):
    def test_the_stop_is_needed_for_every_playable_pokemon(self):
        """対戦に使えるポケモンでは、プラスパワー・ディフェンダーが 1 枚でもついていれば、読み方によって 20 の結果が変わる
        （0〜2 枚の組み合わせで確かめた）。結果が同じになる場合だけを処理する、という正規化の余地はない（止める範囲は
        広すぎない）。ついていなければ読み方は 1 通り（弱点・抵抗力だけ。p.322「このダメージは「弱点・抵抗力」の影響を受けます」）。

        v0.6 までは、ついていないときの値を 20 と固定していた（対戦に使えるポケモンに、自分のタイプを弱点に持つものがなかった）。
        v0.7 で対応にしたケーシィ・ユンゲラー・フーディン（超・弱点 超）は、こんらんの 20 が自分の弱点で 40 になる（v0.3c の
        ``calculate_confusion_damage``。p.149・p.151・p.153 の図版の弱点）ので、期待値を 1 通りの読み方の値にした（読み方が 1 通りで
        あることは変えていない）。

        v0.47 のプテラ（PMCG3-041。闘・抵抗力 闘 -30。kyuura データの採用）は、自分のタイプを抵抗力に持つ最初の対戦に使えるポケモンで、こんらんの 20 が
        自分の抵抗力で 0 になる。プラスパワーが 1 枚以下なら、どの読み方でも 0 で結果が同じになる（2 枚なら 40 − 30 = 10 で変わる）。エンジンは読み方ごとの
        結果を比べず、ダメージを変えるカードがついていれば止める（v0.3c のまま。止める範囲はこの組だけ必要より広い。docs/fossil-hidden-info-v0.47.md 10 章）。
        その組を ``coinciding`` に挙げ、ほかのポケモン・組では今までどおり結果が変わることを確かめる。"""
        pool = load_card_pool()
        # v0.69 の拡張パック以外の商品の同じカードの新しい id（tests/helpers.py の V0_69_POKEMON）は、元のカードと同じ結果になることを別に確かめる
        pokemon = [pool.get(c) for c in sorted(pool.playable_ids) if pool.get(c).category == "pokemon" and c not in V0_69_POKEMON]
        self.assertGreater(len(pokemon), 10)
        for card in V0_69_POKEMON:
            for pluspowers, defenders in itertools.product(range(3), repeat=2):
                with self.subTest(pokemon=card, pluspowers=pluspowers, defenders=defenders):
                    self.assertEqual(confusion_interpretations(pool.get(card), pluspowers, defenders),
                                     confusion_interpretations(pool.get(EQUIVALENT_CARDS[card]), pluspowers, defenders))
        coinciding = set()
        for definition in pokemon:
            for pluspowers, defenders in itertools.product(range(3), repeat=2):
                with self.subTest(pokemon=definition.id, pluspowers=pluspowers, defenders=defenders):
                    results = confusion_interpretations(definition, pluspowers, defenders)
                    if pluspowers == defenders == 0:
                        self.assertEqual(set(results.values()), {calculate_confusion_damage(definition, RULES_2000_02_14, 20).final})
                    elif len(set(results.values())) == 1:
                        coinciding.add((definition.id, pluspowers, defenders))
        # v0.77: グライガー（neo1-052。闘・抵抗力 闘 -30。kyuura データの採用）もプテラと同じ組で結果が同じ（止める範囲はこの組だけ必要より広い。v0.3c のまま）
        # v0.79: グライガー（neo4-071。闘・抵抗力 闘 -30）も同じ組
        self.assertEqual(coinciding, {(card, p, d) for card in ("PMCG3-041", "neo1-052", "neo4-071") for p in range(2) for d in range(3)}
                         - {("PMCG3-041", 0, 0), ("neo1-052", 0, 0), ("neo4-071", 0, 0)})
        # 自分のタイプを弱点に持つポケモン（v0.7 の超のポケモン・v0.18c のナツメのヤドン（超・弱点 超。p.155）・v0.28 のスリープ（超・弱点 超。
        # p.164）・v0.31 のミュウツー（PMCG1-050）・化石の秘密のヤドン（PMCG3-027）（どちらも超・弱点 超。kyuura データの採用。採用の記録の
        # カードデータ）・v0.32 のルージュラ（PMCG1-048。超・弱点 超。kyuura データの採用）・v0.37 のナツメのスリープ（PMCG6-045。超・弱点 超。kyuura
        # データの採用）・v0.38 のロケット団のケーシィ（PMCG4-031。超・弱点 超。kyuura データの採用）・v0.40 のわるいスリーパー（PMCG4-037。超・弱点 超。
        # kyuura データの採用）・v0.41 のロケット団のヤドン（PMCG4-032）・ナツメのヤドラン（PMCG6-048）・R団のミュウツー（PMCG6-055）（どれも超・弱点 超。
        # kyuura データの採用））・v0.42 のナツメのルージュラ（PMCG6-052）・ヤドラン（PMCG3-028）・ナツメのケーシィ（PMCG6-043）・ナツメのユンゲラー
        # （PMCG6-047）・わるいユンゲラー（PMCG4-034）・わるいフーディン（PMCG4-035）（どれも超・弱点 超。kyuura データの採用）・v0.43 のロケット団のスリープ
        # （PMCG4-033）・わるいヤドラン（PMCG4-036）（どちらも超・弱点 超。kyuura データの採用）・v0.44 のナツメのバリヤード（PMCG6-046。超・弱点 超。kyuura
        # データの採用）・v0.46 のバリヤード（PMCG2-027。超・弱点 超。kyuura データの採用）は 40、それ以外は 20
        # （v0.46 までは、対戦に使えるポケモンに抵抗力で自分のタイプを減らすものはなかった。v0.42 のエリカのピッピ・ピクシーは無色で抵抗力 超）
        doubled = {d.id for d in pokemon if calculate_confusion_damage(d, RULES_2000_02_14, 20).final == 40}
        self.assertEqual(doubled, {"PMCG1-043", "PMCG1-045", "PMCG1-046", "PMCG1-049", "PMCG6-044", "PMCG1-050", "PMCG3-027", "PMCG1-048",
                                   "PMCG6-045", "PMCG4-031", "PMCG4-037", "PMCG4-032", "PMCG6-048", "PMCG6-055",
                                   "PMCG6-052", "PMCG3-028", "PMCG6-043", "PMCG6-047", "PMCG4-034", "PMCG4-035", "PMCG4-033", "PMCG4-036",
                                   "PMCG6-046", "PMCG2-027", "PMCG3-032", "PMCG6-053", "PMCG3-033",
                                   "PMCG6-051",
                                   # v0.70: 拡張パック以外の商品のポケモンで、超・弱点 超のもの（ルージュラ ES2-019・QSG-031・PRN-013・IP1-037、ミュウ PR1-069、ネイティ
                                   # NIP2X-004、エーフィ PF2-004。kyuura データの採用）は 40
                                   "ES2-019", "QSG-031", "PRN-013", "IP1-037", "PR1-069", "NIP2X-004", "PF2-004",
                                   # v0.71: 再録のナツメのスリーパー（GD6-010。超・弱点 超）は 40
                                   "GD6-010",
                                   # v0.72: 拡張パック以外の商品のポケモンで、超・弱点 超のもの（ケーシィ ES1-020・QSG-026・NIP2X-003、ナツメのルージュラ GD6-012。kyuura データの採用）は 40
                                   "ES1-020", "QSG-026", "NIP2X-003", "GD6-012",
                                   # v0.75: ナツメのスリープ GD6-009・ミュウツー PR1-007・PR1-008（超・弱点 超。kyuura データの採用）は 40
                                   "GD6-009", "PR1-007", "PR1-008",
                                   # v0.76: ヤドン PR1-006（超・弱点 超。kyuura データの採用）は 40
                                   "PR1-006",
                                   # v0.77: タマタマ neo4-049（超・弱点 超。kyuura データの採用）は 40
                                   "neo4-049",
                                   # v0.79: ヤドン neo1-045・ネイティ neo1-046・neo2-022・エーフィ neo2-029・ヤドキング SI-014（どれも超・弱点 超。kyuura データの採用）は 40
                                   "neo1-045", "neo1-046", "neo2-022", "neo2-029", "SI-014",
                               # v0.83: ひかるミュウツー neo4-068・やさしいヤドラン neo4-054・ひかるミュウ PRN-044（どれも超・弱点 超。kyuura データの採用）は 40
                               "neo4-068", "neo4-054", "PRN-044",
                           # v0.88: スターミー neo3-034・ミュウ SI-004（どちらも超・弱点 超。kyuura データの採用）は 40
                           "neo3-034", "SI-004",
                           # v0.89: ナツメのバリヤード GD6-011（超・弱点 超。kyuura データの採用）は 40
                           "GD6-011"})
        # v0.47: スリーパー（PMCG3-032。超・弱点 超。kyuura データの採用）は 40、プテラ（PMCG3-041。闘・抵抗力 闘）は 0
        # v0.49: ナツメのフーディン（PMCG6-053。超・弱点 超。kyuura データの採用）は 40。メタモン（PMCG3-042。無色・弱点 闘）・タケシのキュウコン（PMCG5-019。炎・弱点 水）は 20
        # （印刷の定義で確かめる。［へんしん］・「ばける」の今の姿のこんらんの 20 は、今有効なタイプ・弱点・抵抗力で計算する。docs/virtual-attacks-transformation-v0.49.md）
        # v0.50: ミュウ（PMCG3-033。超・弱点 超。kyuura データの採用）は 40
        # v0.51: ナツメのスリーパー（PMCG6-051。超・弱点 超。kyuura データの採用）は 40
        zeroed = {d.id for d in pokemon if calculate_confusion_damage(d, RULES_2000_02_14, 20).final == 0}
        self.assertEqual(zeroed, {"PMCG3-041", "neo1-052", "neo4-071"})  # v0.77: グライガー（neo1-052。闘・抵抗力 闘）は 0。v0.79: neo4-071 も
        self.assertTrue(all(calculate_confusion_damage(d, RULES_2000_02_14, 20).final == 20 for d in pokemon if d.id not in doubled | zeroed))



# ---------------------------------------------------------------- 3. ポケモンチェックのどくで両方がきぜつ


class DoubleKnockOutBoundaryTest(unittest.TestCase):
    """両方の対戦ポケモンが同じポケモンチェックのどくできぜつするときだけ、ダメージの前に止める。"""

    def check(self, mine, theirs, *, my_bench=(PONYTA,), their_bench=(RATTATA,), my_prizes=6, their_prizes=6):
        state = build_test_state([
            {"active": {"card": VULPIX, **mine}, "bench": list(my_bench), "prizes": my_prizes},
            {"active": {"card": GROWLITHE, **theirs}, "bench": list(their_bench), "prizes": their_prizes},
        ])
        start = len(state.log)
        new = apply_command(state, EndTurn(0))
        return state, new, [dict(e) for e in new.log[start:]]

    def test_both_lethal_halts_before_the_damage(self):
        """控え・サイドの残りに関係なく止める（どの場合も、処理の順番によって結果か、決定を出す順番が変わる）。"""
        for my_bench, their_bench, my_prizes, their_prizes in itertools.product(((PONYTA,), ()), ((RATTATA,), ()), (6, 1), (6, 1)):
            with self.subTest(my_bench=my_bench, their_bench=their_bench, my_prizes=my_prizes, their_prizes=their_prizes):
                state, new, events = self.check({"poison": 10, "damage": 40}, {"poison": 10, "damage": 50}, my_bench=my_bench,
                                                their_bench=their_bench, my_prizes=my_prizes, their_prizes=their_prizes)
                self.assertEqual((new.phase, new.halt.code), (Phase.HALTED, "UNRESOLVED_POKEMON_CHECK_DOUBLE_KNOCKOUT"))
                self.assertEqual(kinds(events)[-3:], ["turn_end", "pokemon_check", "halted"])
                self.assertEqual((new.players[0].active.damage, new.players[1].active.damage), (40, 50))  # ダメージの前
                self.assertEqual(rng_fingerprint(new.rng), rng_fingerprint(state.rng))

    def test_only_one_lethal_is_processed(self):
        cases = [
            ({"poison": 10, "damage": 40}, {"poison": 10}),  # 相手はどくだが、きぜつしない
            ({"poison": 10, "damage": 40}, {}),  # 相手はどくでない
            ({"poison": 10}, {"poison": 10, "damage": 50}),
            ({"poison": 10, "damage": 40, "sleep": True}, {"poison": 10, "sleep": True}),  # ねむりのコインはきぜつのあと
        ]
        for mine, theirs in cases:
            with self.subTest(mine=mine, theirs=theirs):
                _, new, events = self.check(mine, theirs)
                self.assertNotEqual(new.phase, Phase.HALTED)
                self.assertEqual(kinds(events).count("knock_out"), 1)
                self.assertEqual(check_invariants(new), [])


# ---------------------------------------------------------------- 4. 両方の対戦ポケモンがねむり


class SleepCoinOrderBoundaryTest(unittest.TestCase):
    def check(self, mine, theirs):
        state = build_test_state([
            {"active": {"card": VULPIX, **mine}, "bench": [PONYTA]},
            {"active": {"card": GROWLITHE, **theirs}, "bench": [RATTATA]},
        ])
        state = with_coin_results(state, T, T)
        start = len(state.log)
        new = apply_command(state, EndTurn(0))
        return state, new, [dict(e) for e in new.log[start:]]

    def test_both_asleep_halts_before_any_coin(self):
        for mine, theirs in (({"sleep": True}, {"sleep": True}), ({"sleep": True, "poison": 10}, {"sleep": True})):
            with self.subTest(mine=mine):
                state, new, events = self.check(mine, theirs)
                self.assertEqual((new.phase, new.halt.code), (Phase.HALTED, "UNRESOLVED_POKEMON_CHECK_SLEEP_COIN_ORDER"))
                self.assertNotIn("coin_flip", kinds(events))
                self.assertEqual(rng_fingerprint(new.rng), rng_fingerprint(state.rng))

    def test_one_asleep_flips_one_coin(self):
        for other in ({}, {"poison": 10}, {"paralysis": 3}, {"confusion": True}):
            with self.subTest(other=other):
                _, new, events = self.check({"sleep": True}, other)
                flips = [e for e in events if e["kind"] == "coin_flip"]
                self.assertEqual([(e["player"], e["source"]) for e in flips], [(0, "pokemon_check")])
                self.assertNotEqual(new.phase, Phase.HALTED)

    def test_both_asleep_but_one_knocked_out_by_poison(self):
        """どく（2）できぜつしたポケモンは 3 の時点で場にいない（v0.3b。SUPPORTED）。交代のあと、残ったねむりのポケモンの
        持ち主だけがコインを投げる。止めない。"""
        state, new, _ = self.check({"sleep": True, "poison": 10, "damage": 40}, {"sleep": True})
        self.assertEqual((new.phase, new.decision.player), (Phase.TAKE_PRIZE, 1))
        new = apply_command(new, ResolveDecision(1, new.decision.id, (0,)))
        start = len(new.log)
        new = apply_command(new, ResolveDecision(0, new.decision.id, (new.decision.options[0],)))
        flips = [dict(e) for e in new.log[start:] if e["kind"] == "coin_flip"]
        self.assertEqual([(e["player"], e["source"]) for e in flips], [(1, "pokemon_check")])


# ---------------------------------------------------------------- 5. マヒの再付与


class ReparalysisBoundaryTest(unittest.TestCase):
    def own(self, paralyzed_turn):
        return build_test_state([{"active": {"card": GROWLITHE, "paralysis": paralyzed_turn}, "bench": [PONYTA]}, {"active": RATTATA}])

    def test_boundaries(self):
        """自分の番（3 番）に、自分のポケモンを再びマヒにする効果を受けた場合:
        - 2 番（相手の番）にマヒ → 回復は 3 番。3 番から数えると 5 番 → 決められない（止める。状態は変わらない）
        - 3 番にマヒ → 回復は 5 番。どちらから数えても 5 番 → 二重にならない（already）
        相手のポケモンを再びマヒにする場合は、いつも同じ番になる（test_effect_preflight_v0_3d.py ``ReparalysisProofTest``）。"""
        state = self.own(2)
        before = full(state)
        with self.assertRaises(UnsupportedError) as ctx:
            paralyze(state, 0, state.players[0].active, effect="test")
        self.assertEqual(ctx.exception.code, "UNRESOLVED_REPARALYSIS_RECOVERY_TURN")
        self.assertEqual(full(state), before)
        state = self.own(3)
        paralyze(state, 0, state.players[0].active, effect="test")
        self.assertTrue(state.log[-1]["already"])
        self.assertEqual((state.log[-1]["paralyzed_turn"], state.log[-1]["recovery_turn"]), (3, 5))


if __name__ == "__main__":
    unittest.main()

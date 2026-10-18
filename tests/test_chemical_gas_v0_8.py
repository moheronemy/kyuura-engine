"""ベトベトン（PMCG3-007。v0.8）のポケモンパワー「かがくへんかガス」: 登録と照合・常にはたらく効果の求め方・3 つの特殊能力
（エナジートランス・あまごい・ダメージスワップ）を消すこと・特殊状態・盤面の変化・ほかの操作・原子性・保存と復元・ログ。

根拠は『ポケモンカードオフィシャルブック2000』[P43]（kyuura の NEO-2000-OFFICIAL-RULES）。裁定の表は docs/chemical-gas-v0.8.md（G1〜G33）、
設計は docs/continuous-effects-v0.8.md・docs/architecture-v0.8.md。

- p.48: 見出し「ベターから進化 ベトベトン LV.34／HP70」「ポケモンカード第3弾化石の秘密」。「特殊能力」欄の最新の説明「このカードが場にいる
  かぎり、「かがくへんかガス」以外のすべての「特殊能力」は使えず、その力も消える。このカードが「ねむり・マヒ・こんらん」状態のとき、この力は
  消える。」。解説「他のポケモンの持っている特殊能力を無効にしてしまう能力」「自分のほうも特殊能力を使えなくなる」
- p.323: 「常にはたらいているため、使用を宣言しない特殊能力もあります。」の例が［かがくへんかガス］（場に「ある」かぎり）
- p.311: 「自分の場にいるポケモンが持っている特殊能力のうちで、そのとき使うことのできるものの使用を宣言することができます。」
- p.308: 「場」はバトル場とベンチ。p.322: 特殊状態になるのはバトル場のポケモンだけ。p.310・p.311・p.322: 進化・ベンチに戻ると特殊状態が消える
- p.265: まきちらせ！ベトベトガスの解説「［かがくへんかガス］の力を一時的に消す」（「その力も消える」は一時的。消える条件がなくなれば戻る）
- p.277: マチスの秘策の解説「特殊能力［かがくへんかガス］を持っている「ベトベトン」が場に出た場合　全体に働く効果」

盤面を直接作るテスト（``build_test_state``）は 1 か所の規定を確かめるためのもので、自然な対戦の結果ではない（自然な対戦は
tests/test_muk_games_v0_8.py）。
"""

import copy
import pickle
import unittest

from kyuura_engine import (
    AttachEnergy,
    EndTurn,
    EvolvePokemon,
    IllegalActionError,
    Phase,
    PlayTrainer,
    ResolveDecision,
    Retreat,
    UnsupportedError,
    UseAttack,
    UsePokemonPower,
    apply_command,
    check_invariants,
    power_suppressors,
    state_to_dict,
    working_power_suppressors,
)
from kyuura_engine.cards import EnergyType, load_card_pool, pool_from_extract, read_extract, read_verification
from kyuura_engine.continuous import suppressors_of
from kyuura_engine.decisions import DECISION_PHASES
from kyuura_engine.effects import DEFAULT_EFFECTS, PowerEffect, PowerKey, SuppressOtherPowers
from kyuura_engine.rng import rng_fingerprint
from tests.helpers import (
    ABRA,
    ALAKAZAM,
    BLASTOISE,
    BULBASAUR,
    BUTTERFREE,
    CATERPIE,
    FOSSIL_GRIMER,
    GRASS,
    GRIMER,
    HITMONCHAN,
    IVYSAUR,
    KADABRA,
    METAPOD,
    MUK,
    PSYCHIC,
    RATTATA,
    SEEL,
    SQUIRTLE,
    SWITCH,
    VENUSAUR,
    WARTORTLE,
    WATER,
    H,
    T,
    build_test_state,
    with_coin_results,
)
from tests.log_audit import LATEST_FORMAT, serialization_problems

GAS_PRINTED = ("ベトベトンが場にいる限り、場にいるすべてのポケモンの特殊能力は使えず、その力も消える。(ただし、この「かがくへんかガス」という"
               "特殊能力は除く)「ねむり・マヒ・こんらん」状態の時、この「かがくへんかガス」の力は消える。")
GAS_LATEST = ("このカードが場にいるかぎり、「かがくへんかガス」以外のすべての「特殊能力」は使えず、その力も消える。このカードが「ねむり・マヒ・"
              "こんらん」状態のとき、この力は消える。")
CHEMICAL_GAS = PowerKey(MUK, 0)
TURN = 7  # 先攻はプレイヤー 0。1 進化のベトベトン・2 進化のフシギバナなどを、今の番より前の自分の番に進化したものとして置ける


def full(state):
    """最新の形式（9）。v0.8 は形式を加えていない。"""
    return state_to_dict(state, format_version=9)


def muk(**extra):
    """ロケット団のベトベターから進化したベトベトン（盤面を直接作る）。"""
    return {"card": MUK, "evolved_from": GRIMER, **extra}


def venusaur(**extra):
    return {"card": VENUSAUR, "evolved_from": [BULBASAUR, IVYSAUR], **extra}


def blastoise(**extra):
    return {"card": BLASTOISE, "evolved_from": [SQUIRTLE, WARTORTLE], **extra}


def alakazam(**extra):
    return {"card": ALAKAZAM, "evolved_from": [ABRA, KADABRA], **extra}


def board(mine, theirs, *, turn=TURN, player=0, **kwargs):
    """プレイヤー ``player`` の番 ``turn`` の盤面。``mine``・``theirs`` は build_test_state の 1 人ぶん（active・bench・hand など）。"""
    specs = [mine, theirs] if player == 0 else [theirs, mine]
    return build_test_state(specs, current_player=player, turn_number=turn, **kwargs)


def card_id(state, pokemon):
    return state.cards[pokemon.card].card_id


def find(state, player, wanted):
    return next(pk for pk in state.players[player].in_play() if card_id(state, pk) == wanted)


def hand_uid(state, player, wanted):
    return next(u for u in state.players[player].hand if state.cards[u].card_id == wanted)


def assert_rejected(test, state, command, code, error=IllegalActionError):
    """拒否され、渡した状態（場・ダメージ・エネルギー・特殊状態・手札・山札・トラッシュ・サイド・番・段階。形式 9）もログも乱数も変わらない。"""
    before, fingerprint, log, length = full(state), rng_fingerprint(state.rng), state.log, len(state.log)
    with test.assertRaises(error) as ctx:
        apply_command(state, command)
    test.assertIs(type(ctx.exception), error)
    test.assertEqual(ctx.exception.code, code, ctx.exception)
    test.assertEqual((full(state), rng_fingerprint(state.rng)), (before, fingerprint))
    test.assertIs(state.log, log)
    test.assertEqual(len(state.log), length)
    return ctx.exception


def settle(state):
    """決定（サイド・バトル場に出すポケモン）を、選べるものの最初で答える。"""
    while state.phase in DECISION_PHASES:
        d = state.decision
        state = apply_command(state, ResolveDecision(d.player, d.id, tuple(d.options[:max(d.min_choices, 1)])))
    return state


# ---------------------------------------------------------------- 3 つの特殊能力のコマンド（盤面: power_board）


def power_board(my_active=RATTATA, my_extra=(), opp_active=HITMONCHAN, opp_bench=(SEEL,), **kwargs):
    """自分（プレイヤー 0）のベンチに、フシギバナ（「草」1 個・ダメージ 20）・カメックス・フーディン・ゼニガメ（HP 40）、手札に「水」1 枚。
    ``my_extra`` はベンチに足すポケモン（5 匹まで）。"""
    mine = {"active": my_active, "bench": [venusaur(energy=[GRASS], damage=20), blastoise(), alakazam(), SQUIRTLE, *my_extra],
            "hand": [WATER]}
    theirs = {"active": opp_active, "bench": list(opp_bench)}
    return board(mine, theirs, **kwargs)


def energy_trans(state):
    v, s = find(state, 0, VENUSAUR), find(state, 0, SQUIRTLE)
    return UsePokemonPower(0, v.pokemon_id, 0, v.energy[0], v.pokemon_id, s.pokemon_id)


def rain_dance(state):
    b, s = find(state, 0, BLASTOISE), find(state, 0, SQUIRTLE)
    return UsePokemonPower(0, b.pokemon_id, 0, hand_uid(state, 0, WATER), None, s.pokemon_id)


def damage_swap(state):
    a, v, s = find(state, 0, ALAKAZAM), find(state, 0, VENUSAUR), find(state, 0, SQUIRTLE)
    return UsePokemonPower(0, a.pokemon_id, 0, None, v.pokemon_id, s.pokemon_id)


POWERS = (("エナジートランス", energy_trans, "move_energy"), ("あまごい", rain_dance, "power_attach_energy"),
          ("ダメージスワップ", damage_swap, "move_damage_counter"))

# （名前, power_board の引数, かがくへんかガスがはたらいているか）。マヒはバトル場の自分のベトベトン（相手の番にマヒになった）
VARIANTS = (
    ("ベトベトンがいない", {}, False),
    ("ベトベターだけ（進化前）", {"opp_active": GRIMER}, False),
    ("相手のバトル場", {"opp_active": muk()}, True),
    ("相手のベンチ", {"opp_bench": (SEEL, muk())}, True),
    ("自分のバトル場", {"my_active": muk()}, True),
    ("自分のベンチ", {"my_extra": (muk(),)}, True),
    ("相手のバトル場・どく", {"opp_active": muk(poison=10)}, True),
    ("相手のバトル場・ねむり", {"opp_active": muk(sleep=True)}, False),
    ("相手のバトル場・こんらん", {"opp_active": muk(confusion=True)}, False),
    ("相手のバトル場・こんらんとどく", {"opp_active": muk(confusion=True, poison=10)}, False),
    ("自分のバトル場・マヒ", {"my_active": muk(paralysis=TURN - 1)}, False),
    ("自分のバトル場・ねむりとどく", {"my_active": muk(sleep=True, poison=10)}, False),
    ("相手のバトル場はこんらん・相手のベンチにもう 1 匹", {"opp_active": muk(confusion=True), "opp_bench": (SEEL, muk())}, True),
    ("自分のベンチと相手のバトル場（ねむり）", {"my_extra": (muk(),), "opp_active": muk(sleep=True)}, True),
    ("両方のプレイヤーのバトル場", {"my_active": muk(), "opp_active": muk()}, True),
    ("両方のバトル場で消えている", {"my_active": muk(paralysis=TURN - 1), "opp_active": muk(confusion=True)}, False),
)


# ---------------------------------------------------------------- 登録と照合


class ChemicalGasRegistrationTest(unittest.TestCase):
    def test_card_values(self):
        """p.48 で照合した値（300dpi・図版は 600dpi）: 「ベトベターから進化」の 1 進化、HP 70、草、弱点 超（×2）、抵抗力なし、にげる 2、
        ポケモンパワー 1 つ（かがくへんかガス）、ワザ 1 つ（ヘドロこうげき 草草草 30）。対戦用の進化元はロケット団のベトベター（p.45）。
        化石の秘密のベトベター（p.47）は v0.8〜v0.36 は「ちいさくなる」が未実装なので参照カード（デッキに入らない）だった。v0.37 で対戦用の
        組（pool_v0_37）に移した（docs/fifteen-reused-effects-v0.37.md）。"""
        pool = load_card_pool()
        d = pool.get(MUK)
        self.assertTrue(d.supported and pool.is_playable(MUK) and d.is_stage1_pokemon)
        self.assertEqual((d.name_ja, d.evolves_from, d.hp, d.pokemon_type, d.weakness, d.resistance, d.retreat_cost),
                         ("ベトベトン", "ベトベター", 70, EnergyType.GRASS, EnergyType.PSYCHIC, None, 2))
        self.assertEqual([(w.name_ja, w.kind, w.text_ja, w.supported) for w in d.powers],
                         [("かがくへんかガス", "pokemon_power", GAS_PRINTED, True)])
        self.assertEqual([(a.name_ja, [c.value for c in a.cost], a.damage, a.damage_modifier) for a in d.attacks],
                         [("ヘドロこうげき", ["grass"] * 3, 30, None)])
        extract = read_extract()
        self.assertEqual(extract["pool_v0_8"], [GRIMER, MUK])
        self.assertIn(FOSSIL_GRIMER, extract["pool_v0_37"])
        self.assertNotIn(FOSSIL_GRIMER, extract["reference_only"])
        self.assertTrue(pool.is_playable(FOSSIL_GRIMER))
        self.assertEqual(pool.get(FOSSIL_GRIMER).name_ja, pool.get(GRIMER).name_ja)  # 同じ名前（どちらからでも進化できる。p.310）

    def test_registered_entry_matches_the_verification(self):
        """登録（PowerKey("PMCG3-007", 0)）は、照合した印刷の文面・最新の説明（p.48）と同じ。実装は宣言しない ``SuppressOtherPowers``。
        p.323 の例の最新の説明（「場にある」「状態の時」）も照合の記録にある。"""
        entry = DEFAULT_EFFECTS.power_entry(MUK, 0)
        self.assertEqual(entry.effect, SuppressOtherPowers(exempt_name="かがくへんかガス"))
        self.assertFalse(entry.effect.declared)
        # 宣言しない特殊能力は、かがくへんかガスと、v0.9 のゴーストの「とうめい」（自動的にはたらく。docs/automatic-powers-v0.9.md）と、
        # v0.10 のカイリキーの「はんげき」（ダメージを受けたときに自動的にはたらく。docs/post-damage-powers-v0.10.md）と、v0.17b の R団のカビゴンの
        # 「わるいねぞう」（ねむり状態でダメージを受けたときに自動的にはたらく。docs/rocket-snorlax-v0.17b.md）と、v0.31 のカツラのキュウコンの
        # 「ほのおでかいふく」（炎エネルギーカードをつけたときに自動的にはたらく。docs/held-cards-v0.31.md）と、v0.42 のエリカのラフレシアの
        # 「ぼうぎょかふん」（バトル場でワザのダメージを受けたときに自動的にはたらく。docs/power-decisions-v0.42.md）と、v0.46 の常にはたらく特殊能力 8 つ
        # （なぞのかべ・ふしぎなバリアー・くつろぐかおり・きょうぼう・にげるサポート・ねんちゃくえき・アレルギーかふん・めんえき。docs/continuous-powers-v0.46.md）と、
        # v0.47 の常にはたらく特殊能力 3 つ（おみとおし・カブトアーマー・げんしのちから。docs/fossil-hidden-info-v0.47.md）と、v0.48 のナツメのゴースの
        # 「ガスのからだ」（常にはたらく。docs/effective-pokemon-properties-v0.48.md）と、v0.49 のナツメのフーディンの［サイコリンク］・メタモンの［へんしん］
        # （どちらも常にはたらく。docs/virtual-attacks-transformation-v0.49.md）と、v0.60 のカスミのギャラドスの［はんこう］（ワザを使う時に自動的にはたらく。
        # docs/coins-defense-rebellion-v0.60.md）と、v0.61 のわるいダグトリオの［おとしあな］（相手が「にげる」時に自動的にはたらく）・タケシのオコリザルの
        # ［ずらかる］（残りHPが「10」になった時に自動的にはたらく。docs/reactive-powers-trainer-damage-v0.61.md）だけ
        undeclared = {k for k in DEFAULT_EFFECTS.power_keys() if not DEFAULT_EFFECTS.power_entry(k.card_id, k.power_index).effect.declared}
        self.assertEqual(undeclared, {CHEMICAL_GAS, PowerKey("PMCG3-030", 0), PowerKey("PMCG1-057", 0), PowerKey("PMCG6-073", 0),
                                      PowerKey("PMCG6-033", 0), PowerKey("PMCG5-014", 0),
                                      *(PowerKey(card, 0) for card in ("PMCG2-027", "PMCG5-063", "PMCG6-010", "PMCG4-041", "PMCG2-040", "PMCG4-007",
                                                                       "PMCG4-010", "PMCG2-047", "PMCG3-015", "PMCG3-035", "PMCG3-041", "PMCG6-049",
                                                                       "PMCG6-053", "PMCG3-042", "PMCG5-035", "PMCG4-043", "PMCG5-051"))})
        self.assertTrue(PowerEffect.declared)
        self.assertEqual((entry.name_ja, entry.text_ja, entry.play_text_ja, entry.source), ("かがくへんかガス", GAS_PRINTED, GAS_LATEST, "P43 p.48"))
        self.assertEqual(DEFAULT_EFFECTS.id, "kyuura-engine-0.13")  # v0.9 でゴース・ゴースト、v0.10 でゴーリキー・カイリキー、v0.11 でサカキのワンリキー・ゴーリキー・カイリキー、v0.12 で R団のファイヤー、v0.13 で第4弾のゼニガメ・わるいカメールの登録を加えた（かがくへんかガスの登録は同じ）
        self.assertEqual(DEFAULT_EFFECTS.describe()["powers"]["PMCG3-007@power0"],
                         {"implementation": "suppress_other_powers", "name_ja": "かがくへんかガス", "source": "P43 p.48"})
        record = read_verification()["cards"][MUK]
        self.assertEqual((record["page"], record["pdf_page"], record["rules_page"], record["status"]), (48, 50, 323, "不一致あり"))
        self.assertEqual(record["power_latest_description_ja"], {"0": GAS_LATEST})
        self.assertIn("このカードが場にあるかぎり", record["power_rules_example_ja"]["0"])
        self.assertEqual(record["mismatches"][0]["kyuura"], GAS_PRINTED)
        self.assertIn("全て", record["power_card_image_text_ja"]["0"])

    def test_check_finds_wrong_registrations(self):
        """``SuppressOtherPowers.check`` は、除外する名前（かがくへんかガス）と違う名前のパワーへの登録（自分自身を消してしまう。
        はたらいているかの判定が循環する）・種類の違うパワーを問題にする。"""
        gas = DEFAULT_EFFECTS.power_entry(MUK, 0).effect
        pool = load_card_pool()
        self.assertEqual(gas.check(pool.get(MUK).powers[0]), [])
        problems = gas.check(pool.get(VENUSAUR).powers[0])
        self.assertTrue(any("自分自身を消してしまう" in p for p in problems), problems)
        wrong = SuppressOtherPowers(exempt_name="エナジートランス")
        self.assertTrue(wrong.check(pool.get(MUK).powers[0]))
        moved = DEFAULT_EFFECTS.with_powers("test-gas-on-venusaur", {PowerKey(VENUSAUR, 0): DEFAULT_EFFECTS.power_entry(MUK, 0)})
        self.assertIsNotNone(moved.power_problem(VENUSAUR, pool.get(VENUSAUR).powers[0]))

    def test_without_the_registration_the_card_is_unsupported(self):
        """登録を除くと、ベトベトンはデッキに入らない（パワーを持つカードを一括で対応にしない）。"""
        effects = DEFAULT_EFFECTS.without_powers("test-no-gas", [CHEMICAL_GAS])
        pool = pool_from_extract(read_extract(), effects)
        self.assertFalse(pool.is_playable(MUK))
        self.assertIn("かがくへんかガス", " ".join(pool.get(MUK).unsupported_reasons))
        self.assertTrue(pool.is_playable(GRIMER))

    def test_the_gas_is_not_declared(self):
        """常にはたらいている特殊能力は使用を宣言しない（p.311・p.323）。``UsePokemonPower`` は ``POWER_NOT_DECLARABLE``（バトル場・ベンチ・
        特殊状態・選ばせるものの有無に関係なく）。状態・乱数・ログは変わらない。相手のベトベトンは、所有の確認（共通の確認）が先。"""
        state = power_board(my_active=muk(confusion=True), my_extra=(muk(),), opp_active=muk())
        me = state.players[0]
        active_muk, bench_muk = me.active, me.bench[-1]
        for command in (UsePokemonPower(0, active_muk.pokemon_id, 0), UsePokemonPower(0, bench_muk.pokemon_id, 0),
                        UsePokemonPower(0, bench_muk.pokemon_id, 0, None, active_muk.pokemon_id, bench_muk.pokemon_id)):
            with self.subTest(command=command):
                assert_rejected(self, state, command, "POWER_NOT_DECLARABLE")
        assert_rejected(self, state, UsePokemonPower(0, state.players[1].active.pokemon_id, 0), "POKEMON_NOT_YOURS")
        assert_rejected(self, state, UsePokemonPower(0, active_muk.pokemon_id, 1), "NO_POKEMON_POWER")


# ---------------------------------------------------------------- 常にはたらく効果の求め方（D1）


class GasEvaluationTest(unittest.TestCase):
    def test_variants(self):
        """場のベトベトンの場所・特殊状態・両方のプレイヤー・複数のベトベトンで、はたらいているかがくへんかガスを求める（G1〜G5・G9〜G14・
        G20・G21）。はたらいているのは、場（バトル場・ベンチ）にいて、ねむり・マヒ・こんらんでないベトベトン。どくは関係しない。進化前の
        ベトベターにはない。かがくへんかガス自身は消されない。求めても状態・乱数・ログは変わらない。"""
        for name, kwargs, working in VARIANTS:
            with self.subTest(variant=name):
                state = power_board(**kwargs)
                before, fingerprint, length = full(state), rng_fingerprint(state.rng), len(state.log)
                muks = [pk for p in state.players for pk in p.in_play() if card_id(state, pk) == MUK]
                expected = tuple(pk.pokemon_id for pk in muks if not (pk.conditions.asleep or pk.conditions.paralyzed or pk.conditions.confused))
                self.assertEqual(bool(expected), working)
                self.assertEqual(working_power_suppressors(state), expected)
                for user in (VENUSAUR, BLASTOISE, ALAKAZAM):
                    self.assertEqual(power_suppressors(state, find(state, 0, user).pokemon_id, 0), expected)
                for pk in muks:  # かがくへんかガスどうしは消し合わない（「「かがくへんかガス」以外の」）
                    self.assertEqual(power_suppressors(state, pk.pokemon_id, 0), ())
                self.assertEqual((full(state), rng_fingerprint(state.rng), len(state.log)), (before, fingerprint, length))
                self.assertEqual(check_invariants(state), [])

    def test_query_errors(self):
        """場にいないポケモン・ない特殊能力は ``ValueError``（状態は変えない）。特殊能力のないポケモンには聞けない。"""
        state = power_board(opp_active=muk())
        with self.assertRaises(ValueError):
            power_suppressors(state, 999, 0)
        with self.assertRaises(ValueError):
            power_suppressors(state, find(state, 0, VENUSAUR).pokemon_id, 1)
        with self.assertRaises(ValueError):
            power_suppressors(state, state.players[0].active.pokemon_id, 0)  # コラッタ（特殊能力なし）

    def test_suppressors_of_uses_the_power_name(self):
        """消すかは特殊能力の名前で決める（「「かがくへんかガス」以外のすべての」）。別のカードの同じ名前の特殊能力も除かれる。"""
        state = power_board(opp_active=muk())
        pool = load_card_pool()
        self.assertEqual(suppressors_of(state, pool.get(MUK).powers[0]), ())
        for card in (VENUSAUR, BLASTOISE, ALAKAZAM):
            self.assertEqual(suppressors_of(state, pool.get(card).powers[0]), (state.players[1].active.pokemon_id,))


# ---------------------------------------------------------------- 3 つの特殊能力を消すこと（D2・D4）


class SuppressionTest(unittest.TestCase):
    def test_every_power_and_variant(self):
        """エナジートランス・あまごい・ダメージスワップは、かがくへんかガスがはたらいていなければ使え、はたらいていれば ``POWER_SUPPRESSED``
        （p.48「「かがくへんかガス」以外のすべての「特殊能力」は使えず」。G22〜G24）。拒否で状態（エネルギー・ダメージカウンター・手札・
        山札・トラッシュ・サイド・特殊状態・番・段階）・乱数・ログは変わらない。自分のベトベトンでも相手のベトベトンでも同じ（G4）。"""
        for name, kwargs, working in VARIANTS:
            for power, command_of, event in POWERS:
                with self.subTest(variant=name, power=power):
                    state = power_board(**kwargs)
                    command = command_of(state)
                    if working:
                        error = assert_rejected(self, state, command, "POWER_SUPPRESSED")
                        self.assertIn("使えず", error.message)
                    else:
                        new = apply_command(state, command)
                        self.assertEqual([e["kind"] for e in new.log[len(state.log):]], ["pokemon_power", event])
                        self.assertEqual((new.phase, new.current_player, check_invariants(new)), (Phase.MAIN, 0, []))

    def test_suppression_is_a_common_check(self):
        """かがくへんかガスの確認は、使うポケモン・特殊能力の有無・登録の確認（共通の確認）のあと、パワーごとの確認（使うポケモンの特殊状態・
        選ばせるもの）の前（API の約束の順番。docs/architecture-v0.8.md 2 章・13 章）。番・段階・使うポケモンの所有・特殊能力の位置の誤りは、
        今までどおりのコードが先。"""
        state = power_board(opp_active=muk(), my_active=alakazam(confusion=True))
        me = state.players[0]
        confused = me.active
        v, s = find(state, 0, VENUSAUR), find(state, 0, SQUIRTLE)
        # パワーごとの確認より先: 特殊状態のフーディン・選ばせるものの不足・エネルギーの指定
        assert_rejected(self, state, UsePokemonPower(0, confused.pokemon_id, 0, None, v.pokemon_id, s.pokemon_id), "POWER_SUPPRESSED")
        assert_rejected(self, state, UsePokemonPower(0, v.pokemon_id, 0), "POWER_SUPPRESSED")
        assert_rejected(self, state, UsePokemonPower(0, find(state, 0, BLASTOISE).pokemon_id, 0, v.energy[0], v.pokemon_id, s.pokemon_id),
                        "POWER_SUPPRESSED")
        # 共通の確認が先
        assert_rejected(self, state, UsePokemonPower(1, v.pokemon_id, 0, v.energy[0], v.pokemon_id, s.pokemon_id), "NOT_YOUR_TURN")
        assert_rejected(self, state, UsePokemonPower(0, state.players[1].active.pokemon_id, 0), "POKEMON_NOT_YOURS")
        assert_rejected(self, state, UsePokemonPower(0, v.pokemon_id, 1), "NO_POKEMON_POWER")
        assert_rejected(self, state, UsePokemonPower(0, 999, 0), "POKEMON_NOT_IN_PLAY")
        assert_rejected(self, state, UsePokemonPower(0, s.pokemon_id, 0), "NO_POKEMON_POWER")  # ゼニガメ（特殊能力なし）

    def test_rejection_keeps_every_zone(self):
        """拒否の前後で、場・手札・山札・トラッシュ・サイドのカードと、複製・pickle の結果も同じ（D4）。"""
        state = power_board(opp_active=muk())
        for _, command_of, _ in POWERS:
            command = command_of(state)
            zones = [(list(p.hand), list(p.deck), list(p.discard), list(p.prizes),
                      [(pk.pokemon_id, pk.card, tuple(pk.energy), pk.damage, pk.conditions) for pk in p.in_play()]) for p in state.players]
            assert_rejected(self, state, command, "POWER_SUPPRESSED")
            self.assertEqual(zones, [(list(p.hand), list(p.deck), list(p.discard), list(p.prizes),
                                      [(pk.pokemon_id, pk.card, tuple(pk.energy), pk.damage, pk.conditions) for pk in p.in_play()])
                                     for p in state.players])
            for copied in (state.clone(), copy.deepcopy(state), pickle.loads(pickle.dumps(state))):
                assert_rejected(self, copied, command, "POWER_SUPPRESSED")


# ---------------------------------------------------------------- 盤面の変化（D1。コマンドで）


class TransitionTest(unittest.TestCase):
    def test_evolving_into_muk(self):
        """ベトベターからベトベトンに進化したら、すぐにはたらく（p.310・p.48「このカードが場にいるかぎり」。G15・G25）。進化の前に使った
        エナジートランスの結果（つけかえたエネルギー）は、そのまま残る（G27。取り消さない）。進化のログは evolve だけ（かがくへんかガスの
        ログはない）。"""
        state = board({"active": GRIMER, "bench": [venusaur(energy=[GRASS], damage=20), SQUIRTLE], "hand": [MUK]},
                      {"active": HITMONCHAN, "bench": [SEEL]})
        state = apply_command(state, energy_trans(state))
        moved = find(state, 0, SQUIRTLE).energy
        self.assertEqual(len(moved), 1)
        self.assertEqual(working_power_suppressors(state), ())
        before = len(state.log)
        state = apply_command(state, EvolvePokemon(0, hand_uid(state, 0, MUK), state.players[0].active.pokemon_id))
        self.assertEqual([e["kind"] for e in state.log[before:]], ["evolve"])
        self.assertEqual(working_power_suppressors(state), (state.players[0].active.pokemon_id,))
        self.assertEqual(find(state, 0, SQUIRTLE).energy, moved)  # 前に使った特殊能力の結果は残る
        v = find(state, 0, VENUSAUR)
        self.assertEqual(v.energy, [])
        s = find(state, 0, SQUIRTLE)
        assert_rejected(self, state, UsePokemonPower(0, v.pokemon_id, 0, s.energy[0], s.pokemon_id, v.pokemon_id), "POWER_SUPPRESSED")

    def test_evolving_clears_the_condition_of_grimer(self):
        """ねむりのベトベターがベトベトンに進化したら、特殊状態は消える（p.310・p.322）ので、進化したベトベトンの力ははたらく。"""
        state = board({"active": {"card": GRIMER, "sleep": True}, "bench": [venusaur(energy=[GRASS]), SQUIRTLE], "hand": [MUK]},
                      {"active": HITMONCHAN})
        self.assertEqual(working_power_suppressors(state), ())
        state = apply_command(state, EvolvePokemon(0, hand_uid(state, 0, MUK), state.players[0].active.pokemon_id))
        self.assertFalse(state.players[0].active.conditions.asleep)
        self.assertEqual(working_power_suppressors(state), (state.players[0].active.pokemon_id,))

    def test_sleep_coin_brings_the_gas_back(self):
        """ねむりのベトベトン（相手）の力は消えている（G9）。ポケモンチェックでねむりから回復したら、また、はたらく（G13。SUPPORTED: p.48
        「状態のとき、この力は消える」・p.265「一時的に消す」）。回復しなければ、相手の番も消えたまま。"""
        mine = {"active": RATTATA, "bench": [alakazam(), {"card": SEEL, "damage": 20}], "deck": [PSYCHIC] * 5}
        theirs = {"active": muk(sleep=True), "bench": [blastoise()], "hand": [WATER], "deck": [WATER] * 5}
        state = board(mine, theirs)
        state = apply_command(state, damage_swap_of(state, 0))  # ねむりのベトベトン: 自分のダメージスワップを使える
        for coin, back in ((H, True), (T, False)):
            with self.subTest(coin=coin):
                after = apply_command(with_coin_results(state, coin), EndTurn(0))
                self.assertEqual((after.turn_number, after.current_player), (TURN + 1, 1))
                self.assertEqual(after.players[1].active.conditions.asleep, not back)
                rain = UsePokemonPower(1, find(after, 1, BLASTOISE).pokemon_id, 0, hand_uid(after, 1, WATER), None, find(after, 1, BLASTOISE).pokemon_id)
                if back:
                    assert_rejected(self, after, rain, "POWER_SUPPRESSED")
                else:
                    self.assertEqual(apply_command(after, rain).log[-1]["kind"], "power_attach_energy")

    def test_paralysis_recovery_brings_the_gas_back(self):
        """マヒのベトベトン（自分。相手の番にマヒ）の力は消えていて（G10）、自分の番はフシギバナのエナジートランスを使える。番の終わりの
        ポケモンチェックでマヒから回復したら、相手の番はかがくへんかガスがはたらく（相手のあまごいが使えない）。"""
        mine = {"active": muk(paralysis=TURN - 1), "bench": [venusaur(energy=[GRASS]), SQUIRTLE], "deck": [GRASS] * 5}
        theirs = {"active": HITMONCHAN, "bench": [blastoise()], "hand": [WATER], "deck": [WATER] * 5}
        state = board(mine, theirs)
        state = apply_command(state, energy_trans(state))
        state = apply_command(state, EndTurn(0))
        self.assertFalse(state.players[0].active.conditions.paralyzed)
        b = find(state, 1, BLASTOISE)
        assert_rejected(self, state, UsePokemonPower(1, b.pokemon_id, 0, hand_uid(state, 1, WATER), None, b.pokemon_id), "POWER_SUPPRESSED")

    def test_switch_and_retreat_bring_the_gas_back(self):
        """こんらんのベトベトン（自分）の力は消えている（G11）。ポケモンいれかえ・「にげる」でベンチに戻ると特殊状態が消える（p.311・p.322）
        ので、その番のうちに、かがくへんかガスがはたらく（G19）。ベンチのベトベトンは特殊状態にならない（p.322）。"""
        mine = {"active": muk(confusion=True, energy=[GRASS, GRASS]), "bench": [venusaur(energy=[GRASS]), SQUIRTLE], "hand": [SWITCH]}
        state = board(mine, {"active": HITMONCHAN})
        trans = energy_trans(state)
        self.assertEqual(apply_command(state, trans).log[-1]["kind"], "move_energy")
        switched = apply_command(state, PlayTrainer(0, hand_uid(state, 0, SWITCH)))
        if switched.phase is Phase.DECISION:
            switched = apply_command(switched, ResolveDecision(0, switched.decision.id, (find(state, 0, SQUIRTLE).pokemon_id,)))
        bench_muk = find(switched, 0, MUK)
        self.assertNotEqual(switched.players[0].active.pokemon_id, bench_muk.pokemon_id)
        self.assertEqual(working_power_suppressors(switched), (bench_muk.pokemon_id,))
        assert_rejected(self, switched, energy_trans(switched), "POWER_SUPPRESSED")
        # 「にげる」（こんらんのコインが「おもて」）でも同じ
        energies = tuple(state.players[0].active.energy)  # にげる 2（「草」2 個をトラッシュ）
        retreat = Retreat(0, energies, find(state, 0, SQUIRTLE).card)
        retreated = apply_command(with_coin_results(state, H), retreat)
        self.assertEqual(working_power_suppressors(retreated), (find(retreated, 0, MUK).pokemon_id,))
        assert_rejected(self, retreated, energy_trans(retreated), "POWER_SUPPRESSED")
        # 「うら」なら入れ替わらず、こんらんのまま（消えたまま）
        failed = apply_command(with_coin_results(state, T), retreat)
        self.assertEqual(failed.players[0].active.card, state.players[0].active.card)
        self.assertEqual(working_power_suppressors(failed), ())
        self.assertEqual(apply_command(failed, energy_trans(failed)).log[-1]["kind"], "move_energy")
        self.assertEqual(len(energies), 2)

    def test_knock_out_removes_the_gas(self):
        """ベトベトンがきぜつして場をはなれたら、かがくへんかガスはない（G17。p.48「場にいるかぎり」・p.323）。相手の番には、相手の
        ダメージスワップを使える（G26）。"""
        mine = {"active": alakazam(energy=[PSYCHIC] * 3), "deck": [PSYCHIC] * 5, "bench": [SEEL]}
        theirs = {"active": muk(damage=20), "bench": [alakazam(), {"card": RATTATA, "damage": 10}, SEEL], "deck": [GRASS] * 5}
        state = board({**mine, "prizes": 2}, {**theirs, "prizes": 2})
        assert_rejected(self, state, UsePokemonPower(0, state.players[0].active.pokemon_id, 0, None, state.players[0].active.pokemon_id,
                                                     state.players[0].bench[0].pokemon_id), "POWER_SUPPRESSED")
        state = apply_command(with_coin_results(state, T), UseAttack(0, 0))  # あやしいひかり 30 × 2（弱点 超）で、ダメージ 80（HP 70）
        state = settle(state)
        self.assertEqual(state.current_player, 1)
        self.assertEqual(working_power_suppressors(state), ())
        self.assertFalse(any(card_id(state, pk) == MUK for p in state.players for pk in p.in_play()))
        a, r = find(state, 1, ALAKAZAM), find(state, 1, RATTATA)
        target = next(pk for pk in state.players[1].in_play() if pk is not r and pk is not a)
        self.assertEqual(apply_command(state, UsePokemonPower(1, a.pokemon_id, 0, None, r.pokemon_id, target.pokemon_id)).log[-1]["kind"],
                         "move_damage_counter")

    def test_confusing_the_opponents_muk(self):
        """自分のフーディンの「あやしいひかり」で相手のベトベトンをこんらんにすると、相手の番はかがくへんかガスが消えていて、相手のあまごいを
        使える（ワザによって特殊状態になったので、常にはたらく効果が変わる。G11）。"""
        mine = {"active": alakazam(energy=[PSYCHIC] * 3), "deck": [PSYCHIC] * 5}
        theirs = {"active": muk(), "bench": [blastoise()], "hand": [WATER], "deck": [WATER] * 5}
        state = board(mine, theirs)
        state = apply_command(with_coin_results(state, H), UseAttack(0, 0))
        self.assertEqual((state.current_player, state.players[1].active.conditions.confused), (1, True))
        self.assertEqual(working_power_suppressors(state), ())
        b = find(state, 1, BLASTOISE)
        self.assertEqual(apply_command(state, UsePokemonPower(1, b.pokemon_id, 0, hand_uid(state, 1, WATER), None, b.pokemon_id)).log[-1]["kind"],
                         "power_attach_energy")

    def test_whirlwind_brings_the_gas_back(self):
        """相手のこんらんのベトベトンを、自分のバタフリーの「ふきとばし」（v0.4d）でベンチに戻すと、特殊状態が消える（p.311・p.322）ので、
        場にいるベトベトンのかがくへんかガスがはたらく（G13・G19）。次の相手の番、相手のあまごいは消されている。"""
        mine = {"active": {"card": BUTTERFREE, "evolved_from": [CATERPIE, METAPOD], "energy": [GRASS, GRASS]}, "deck": [GRASS] * 5}
        theirs = {"active": muk(confusion=True), "bench": [blastoise()], "hand": [WATER], "deck": [WATER] * 5}
        state = board(mine, theirs)
        self.assertEqual(working_power_suppressors(state), ())
        muk_id = state.players[1].active.pokemon_id
        state = apply_command(state, UseAttack(0, 0))
        self.assertEqual((state.phase, state.decision.player), (Phase.DECISION, 1))
        b = find(state, 1, BLASTOISE)
        new = apply_command(state, ResolveDecision(1, state.decision.id, (b.pokemon_id,)))
        removed = [e for e in new.log[len(state.log):] if e["kind"] == "special_conditions_removed"]
        self.assertEqual([(e["pokemon_id"], e["reason"]) for e in removed], [(muk_id, "forced_switch")])
        self.assertEqual((new.current_player, new.players[1].active.pokemon_id), (1, b.pokemon_id))
        self.assertEqual(working_power_suppressors(new), (muk_id,))
        assert_rejected(self, new, UsePokemonPower(1, b.pokemon_id, 0, hand_uid(new, 1, WATER), None, b.pokemon_id), "POWER_SUPPRESSED")

    def test_r13_is_unchanged(self):
        """あまごいでつけたあとにベトベトンに進化しても、R13（あまごいでつけたあと、その番の通常の操作。UNRESOLVED_ATTACH_AFTER_POWER_ATTACH）は
        今までどおり止まる（かがくへんかガスは R13 を決めない）。あまごいでつけた枚数（energy_attached_by_powers_this_turn）は 1 のまま。
        あまごいは POWER_SUPPRESSED。つけた「水」エネルギーはついたまま（G27）。"""
        mine = {"active": GRIMER, "bench": [blastoise(), SQUIRTLE], "hand": [WATER, WATER, MUK]}
        state = board(mine, {"active": HITMONCHAN})
        b, s = find(state, 0, BLASTOISE), find(state, 0, SQUIRTLE)
        state = apply_command(state, UsePokemonPower(0, b.pokemon_id, 0, hand_uid(state, 0, WATER), None, s.pokemon_id))
        self.assertEqual(state.energy_attached_by_powers_this_turn, 1)
        state = apply_command(state, EvolvePokemon(0, hand_uid(state, 0, MUK), state.players[0].active.pokemon_id))
        assert_rejected(self, state, UsePokemonPower(0, b.pokemon_id, 0, hand_uid(state, 0, WATER), None, s.pokemon_id), "POWER_SUPPRESSED")
        assert_rejected(self, state, AttachEnergy(0, hand_uid(state, 0, WATER), state.players[0].active.card),
                        "UNRESOLVED_ATTACH_AFTER_POWER_ATTACH", UnsupportedError)
        self.assertEqual(state.energy_attached_by_powers_this_turn, 1)
        self.assertEqual(len(find(state, 0, SQUIRTLE).energy), 1)

    def test_one_of_two_muks_is_knocked_out(self):
        """両方のプレイヤーにベトベトンがいて、相手のベトベトンがきぜつしても、自分のベトベトンのかがくへんかガスがはたらいている（G20・G21）。"""
        mine = {"active": alakazam(energy=[PSYCHIC] * 3), "bench": [muk(), SEEL], "deck": [PSYCHIC] * 5}
        theirs = {"active": muk(damage=20), "bench": [alakazam(), {"card": RATTATA, "damage": 10}], "deck": [GRASS] * 5}
        state = board({**mine, "prizes": 2}, {**theirs, "prizes": 2})
        self.assertEqual(len(working_power_suppressors(state)), 2)
        state = settle(apply_command(with_coin_results(state, T), UseAttack(0, 0)))
        self.assertEqual(working_power_suppressors(state), (find(state, 0, MUK).pokemon_id,))
        a, r = find(state, 1, ALAKAZAM), find(state, 1, RATTATA)
        assert_rejected(self, state, UsePokemonPower(1, a.pokemon_id, 0, None, r.pokemon_id, a.pokemon_id), "POWER_SUPPRESSED")


def damage_swap_of(state, player):
    """``player`` の場のフーディンで、ダメージのある最初のポケモンから、ほかのポケモンへ 1 個移すコマンド。"""
    mine = state.players[player].in_play()
    a = next(pk for pk in mine if card_id(state, pk) == ALAKAZAM)
    source = next(pk for pk in mine if pk.damage)
    target = next(pk for pk in mine if pk is not source and pk.damage + 10 < state.card_def(pk.card).hp)
    return UsePokemonPower(player, a.pokemon_id, 0, None, source.pokemon_id, target.pokemon_id)


# ---------------------------------------------------------------- ほかの操作は止めない（D3）


class OtherActionsTest(unittest.TestCase):
    """かがくへんかガスがはたらいていても、特殊能力でない操作（ワザ・手札からつける通常の操作・進化・にげる・トレーナー・番の終わり・
    きぜつ・サイド）は今までどおり（G8・G28。p.48 は「特殊能力」だけを書く）。"""

    def gas_board(self):
        mine = {"active": {"card": GRIMER, "energy": [GRASS, GRASS]}, "bench": [venusaur(energy=[GRASS]), SQUIRTLE],
                "hand": [GRASS, MUK, SWITCH], "deck": [GRASS] * 5}
        theirs = {"active": muk(damage=60), "bench": [SEEL], "deck": [GRASS] * 5}
        state = board({**mine, "prizes": 2}, {**theirs, "prizes": 2})
        self.assertTrue(working_power_suppressors(state))
        return state

    def test_actions(self):
        state = self.gas_board()
        grimer = state.players[0].active
        cases = (
            ("通常の操作", AttachEnergy(0, hand_uid(state, 0, GRASS), grimer.card), "attach_energy"),
            ("進化", EvolvePokemon(0, hand_uid(state, 0, MUK), grimer.pokemon_id), "evolve"),
            ("にげる", Retreat(0, (grimer.energy[0],), find(state, 0, SQUIRTLE).card), "retreat"),
            ("トレーナー", PlayTrainer(0, hand_uid(state, 0, SWITCH)), "play_trainer"),
            ("番の終わり", EndTurn(0), "end_turn_without_attack"),
        )
        for name, command, kind in cases:
            with self.subTest(action=name):
                new = apply_command(state, command)
                self.assertIn(kind, [e["kind"] for e in new.log[len(state.log):]])
                self.assertEqual(check_invariants(new), [])
        self.assertEqual(apply_command(state, AttachEnergy(0, hand_uid(state, 0, GRASS), grimer.card)).energy_attachments_this_turn, 1)

    def test_attack_knock_out_and_prize(self):
        """ねばりつく（「おもて」で 30）で相手のベトベトン（ダメージ 60）をきぜつさせ、サイドを取れる。そのあと、かがくへんかガスはない。"""
        state = self.gas_board()
        new = settle(apply_command(with_coin_results(state, H), UseAttack(0, 1)))
        kinds = [e["kind"] for e in new.log[len(state.log):]]
        self.assertIn("knock_out", kinds)
        self.assertIn("take_prize", kinds)
        self.assertEqual(working_power_suppressors(new), ())
        self.assertEqual(check_invariants(new), [])

    def test_muks_own_attack(self):
        """ベトベトン自身のワザ（ヘドロこうげき）も、かがくへんかガスがはたらいたまま使える（特殊能力ではない）。"""
        mine = {"active": muk(energy=[GRASS] * 3), "deck": [GRASS] * 5}
        state = board(mine, {"active": HITMONCHAN, "deck": [GRASS] * 5})
        self.assertTrue(working_power_suppressors(state))
        new = apply_command(with_coin_results(state, H), UseAttack(0, 0))
        events = [dict(e) for e in new.log[len(state.log):]]
        self.assertEqual([e["amount"] for e in events if e["kind"] == "damage"], [30])
        self.assertIsNotNone(new.players[1].active.conditions.poison)  # 番の終わりのポケモンチェックで、どくの 10 も受けた


# ---------------------------------------------------------------- 保存と復元・書き出し・ログ（D5）


class SaveRestoreTest(unittest.TestCase):
    STATES = (
        ("ベトベトンがいない", {}),
        ("はたらいている", {"opp_active": muk()}),
        ("消えている（こんらん）", {"opp_active": muk(confusion=True)}),
        ("両方のプレイヤー", {"my_extra": (muk(),), "opp_active": muk()}),
        ("複数（片方は消えている）", {"opp_active": muk(sleep=True), "opp_bench": (muk(), SEEL)}),
    )

    def r13_state(self):
        mine = {"active": GRIMER, "bench": [blastoise(), SQUIRTLE, venusaur(energy=[GRASS], damage=20), alakazam()],
                "hand": [WATER, WATER, MUK]}
        state = board(mine, {"active": HITMONCHAN})
        b, s = find(state, 0, BLASTOISE), find(state, 0, SQUIRTLE)
        state = apply_command(state, UsePokemonPower(0, b.pokemon_id, 0, hand_uid(state, 0, WATER), None, s.pokemon_id))
        return apply_command(state, EvolvePokemon(0, hand_uid(state, 0, MUK), state.players[0].active.pokemon_id))

    def outcome(self, state, command):
        try:
            new = apply_command(state, command)
        except (IllegalActionError, UnsupportedError) as error:
            return ("rejected", error.code, full(state), rng_fingerprint(state.rng))
        return ("accepted", None, full(new), rng_fingerprint(new.rng))

    def test_copies_give_the_same_answers(self):
        """pickle・copy.deepcopy・clone で写した状態でも、はたらいているかがくへんかガス・特殊能力の使用の結果（受け付けたか・拒否のコード・
        形式 9・乱数）が同じ。かがくへんかガスのために状態に持つものはない（形式 9 の書き出しは v0.7 と同じ項目。形式 10 はない）。"""
        states = [(name, power_board(**kwargs)) for name, kwargs in self.STATES] + [("R13 とベトベトン", self.r13_state())]
        for name, state in states:
            with self.subTest(state=name):
                commands = [energy_trans(state), damage_swap(state)]
                if hand_uid_or_none(state, 0, WATER) is not None:
                    commands.append(rain_dance(state))
                commands.append(AttachEnergy(0, state.players[0].hand[0], state.players[0].active.card) if state.players[0].hand
                                else EndTurn(0))
                expected = [self.outcome(state, c) for c in commands]
                for copied in (state.clone(), copy.deepcopy(state), pickle.loads(pickle.dumps(state))):
                    self.assertEqual(working_power_suppressors(copied), working_power_suppressors(state))
                    self.assertEqual(full(copied), full(state))
                    self.assertEqual([self.outcome(copied, c) for c in commands], expected)
                self.assertEqual(serialization_problems(state), [])
                self.assertEqual(LATEST_FORMAT, 21)  # 19 は v0.59（energy_roles）。18 は v0.58（trainer_stack・trainer_in_use の via）。17 は v0.57（stadium・stadium_uses_this_turn・trainer_in_use の user）。16 は v0.56（trainer_effects・禁止の origin）。 v0.8 では 9。10 は v0.31（power_uses_this_turn・energy_burn）、11 は v0.44（attacks_used_once・evolution_permission_turn）、12 は v0.47（trainer_locks）、13 は v0.48（type_shift）、14 は v0.49（disguise・recalls）、15 は v0.50（devolved_turn）。どれもガスの項目ではない
                self.assertFalse(any("gas" in key or "suppress" in key for key in full(state)))

    def test_r13_state(self):
        """R13 で止まる状態とベトベトンが同じ番にある状態を写しても、通常の操作は止まり、あまごいは消されたまま。"""
        state = self.r13_state()
        for copied in (state.clone(), pickle.loads(pickle.dumps(state))):
            assert_rejected(self, copied, rain_dance(copied), "POWER_SUPPRESSED")
            assert_rejected(self, copied, AttachEnergy(0, hand_uid(copied, 0, WATER), copied.players[0].active.card),
                            "UNRESOLVED_ATTACH_AFTER_POWER_ATTACH", UnsupportedError)


def hand_uid_or_none(state, player, wanted):
    return next((u for u in state.players[player].hand if state.cards[u].card_id == wanted), None)


if __name__ == "__main__":
    unittest.main()

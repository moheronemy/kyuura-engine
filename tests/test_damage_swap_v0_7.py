"""フーディン（PMCG1-049。v0.7）のポケモンパワー「ダメージスワップ」: 登録と照合・ダメージカウンターの移動・きぜつさせない制限・
特殊状態・拒否と原子性・ほかの処理との関係・ログ・書き出し・不変条件。

根拠は『ポケモンカードオフィシャルブック2000』[P43]（kyuura の NEO-2000-OFFICIAL-RULES）。裁定の表は docs/damage-swap-v0.7.md
（S1〜S25・A4）。

- p.153: 見出し「ユンゲラーから進化 フーディン LV.42／HP80」「ポケモンカード第1弾」。「特殊能力」欄の最新の説明「この力は、自分の番の
  中で何度でも使える。この力によってポケモンが「きぜつ」しないかぎり、自分の場にいるポケモンにのっているダメージカウンターを、自分の
  場にいる別のポケモンにのせかえる。このカードが「ねむり・マヒ・こんらん」状態のとき、この力は使えない。」。解説（フーディン自身へ
  移す・バトル場からベンチへ・HP ぎりぎりまで）
- p.98・p.235・p.248: ほかのカードの解説（ベンチの数匹に分散・HP120 に一時移動・自分のポケモンにふりわけてから進化）
- p.319: ダメージカウンター 1 個 = 10 ダメージ。ダメージが HP と同じか大きくなったら「きぜつ」
- p.320: 「ダメージカウンターの移動」（移動でダメージが HP 以上になればきぜつする・移動で増えたダメージは「ダメージを受けた」ことに
  ならない）・「ダメージの回復」（とりのぞくことで行う）
- p.310: 進化してもダメージカウンターはそのまま。進化したポケモンは、進化前の特殊能力を使えない
- p.311・p.323: 特殊能力の使い方（宣言 → 条件 → 処理。ベンチのポケモンも使える。何度でも。宣言したら、すべてすませてから）
- p.309: ワザを使ったら番は終わる（S21）
- p.322: 特殊状態になるのはバトル場のポケモンだけ。どくマーカーはダメージカウンターと区別できるもの（S9）

1 回の使用で 1 個を移すのは実装上の仮定（最新の説明は 1 回に移す数を書かず、印刷の文面は「自由に移動できる」。何度でも使えるので、
どの移し方も 1 個ずつに分けられ、移動先のダメージは増えていくだけなので途中できぜつする状態を通らない。S3・S18）。盤面を直接作る
テスト（``build_test_state``）は 1 か所の規定を確かめるためのもので、自然な対戦の結果ではない（自然な対戦は
tests/test_alakazam_games_v0_7.py）。
"""

import copy
import dataclasses
import pickle
import random
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
    StateIntegrityError,
    UnsupportedError,
    UseAttack,
    UsePokemonPower,
    apply_command,
    check_invariants,
    command_from_dict,
    command_to_dict,
    state_to_dict,
)
from kyuura_engine.cards import (
    EnergyType,
    load_card_pool,
    read_extract,
    read_verification,
)
from kyuura_engine.effects import (
    DEFAULT_EFFECTS,
    AttachEnergyFromHand,
    AttackEffect,
    EnergyTransfer,
    MoveDamageCounter,
    PowerEffect,
    PowerEntry,
    PowerKey,
    would_be_knocked_out,
)
from kyuura_engine.rng import rng_fingerprint
from tests.helpers import (
    ABRA,
    ALAKAZAM,
    BLASTOISE,
    BULBASAUR,
    DEFENDER,
    DEWGONG,
    GRASS,
    HITMONCHAN,
    IVYSAUR,
    KADABRA,
    PLUSPOWER,
    POTION,
    PSYCHIC,
    RATTATA,
    SEEL,
    SQUIRTLE,
    VENUSAUR,
    WARTORTLE,
    WATER,
    build_test_state,
)
from tests.log_audit import serialization_problems

DAMAGE_SWAP_PRINTED = "自分の場に出ているポケモンのダメージカウンターを、ポケモンが「きぜつ」しない範囲で自由に移動できる。「ねむり・マヒ・こんらん」状態の時は使えない。"
DAMAGE_SWAP_LATEST = ("この力は、自分の番の中で何度でも使える。この力によってポケモンが「きぜつ」しないかぎり、自分の場にいるポケモンにのっている"
                      "ダメージカウンターを、自分の場にいる別のポケモンにのせかえる。このカードが「ねむり・マヒ・こんらん」状態のとき、この力は使えない。")
DAMAGE_SWAP = PowerKey(ALAKAZAM, 0)
TURN = 7  # 先攻はプレイヤー 0。2 進化したフーディンを、今の番より前の自分の番（5）に進化したものとして置ける


def full(state):
    """最新の形式（9）。v0.7 は形式を加えていない。"""
    return state_to_dict(state, format_version=9)


def run(state, command):
    new = apply_command(state, command)
    return new, [dict(e) for e in new.log[len(state.log):]]


def kinds(events):
    return [e["kind"] for e in events]


def alakazam(**extra):
    """ケーシィ → ユンゲラー → フーディンと 2 進化したフーディン（盤面を直接作る。1 進化した番は状態に持たない）。"""
    return {"card": ALAKAZAM, "evolved_from": [ABRA, KADABRA], **extra}


DEWGONG_ON_SEEL = {"card": DEWGONG, "evolved_from": SEEL}  # ジュゴン（HP 80。パウワウから進化した 1 進化）


def kadabra(**extra):
    return {"card": KADABRA, "evolved_from": ABRA, **extra}


def board(active=None, *, bench=(None, None), hand=(), opponent=None, opponent_bench=(SEEL,), turn=TURN, player=0, **kwargs):
    """プレイヤー ``player`` の番 ``turn`` の盤面。既定はバトル場にダメージ 30 のフーディン、ベンチにダメージ 10 のコラッタ（HP 30）と
    ダメージのないジュゴン（HP 80）。相手はバトル場にエビワラー（HP 70）、ベンチにパウワウ（HP 60）。"""
    bench = [b for b in bench if b is not None] if any(b is not None for b in bench) else [{"card": RATTATA, "damage": 10}, DEWGONG_ON_SEEL]
    mine = {"active": active or alakazam(damage=30), "bench": list(bench), "hand": list(hand)}
    theirs = {"active": opponent or {"card": HITMONCHAN, "damage": 20}, "bench": list(opponent_bench)}
    specs = [mine, theirs] if player == 0 else [theirs, mine]
    return build_test_state(specs, current_player=player, turn_number=turn, **kwargs)


def pid(x):
    return x if isinstance(x, int) else x.pokemon_id


def user_of(state, player=None):
    player = state.current_player if player is None else player
    return next(pk for pk in state.players[player].in_play() if state.cards[pk.card].card_id == ALAKAZAM)


def swap(state, source, target, *, player=None, user=None, energy=None):
    """ダメージスワップを 1 回使うコマンド。``source``・``target``・``user`` は場のポケモン（PokemonInPlay）か場のポケモンの番号。"""
    player = state.current_player if player is None else player
    user = user_of(state, player) if user is None else user
    return UsePokemonPower(player, pid(user), 0, energy, None if source is None else pid(source), None if target is None else pid(target))


def damages(state, player=0):
    return {pk.pokemon_id: pk.damage for pk in state.players[player].in_play()}


def assert_rejected(test, state, command, code, error=IllegalActionError):
    """拒否され、渡した状態（場・ダメージ・手札・山札・トラッシュ・サイド・番・段階）もログも乱数も変わらない。"""
    before, fingerprint, log = full(state), rng_fingerprint(state.rng), state.log
    with test.assertRaises(error) as ctx:
        apply_command(state, command)
    test.assertIs(type(ctx.exception), error)
    test.assertEqual(ctx.exception.code, code)
    test.assertEqual((full(state), rng_fingerprint(state.rng)), (before, fingerprint))
    test.assertIs(state.log, log)


# ---------------------------------------------------------------- 登録と照合


class DamageSwapRegistrationTest(unittest.TestCase):
    def test_card_values(self):
        """p.153 で照合した値（300dpi・図版は 600dpi）: 「ユンゲラーから進化」の 2 進化、HP 80、超、弱点 超（×2）、抵抗力なし、にげる 3、
        ポケモンパワー 1 つ（ダメージスワップ）、ワザ 1 つ（あやしいひかり 超超超 30）。v0.6 までは参照カード（未対応）だった。"""
        pool = load_card_pool()
        d = pool.get(ALAKAZAM)
        self.assertTrue(d.supported and pool.is_playable(ALAKAZAM) and d.is_stage2_pokemon)
        self.assertEqual((d.name_ja, d.evolves_from, d.hp, d.pokemon_type, d.weakness, d.resistance, d.retreat_cost),
                         ("フーディン", "ユンゲラー", 80, EnergyType.PSYCHIC, EnergyType.PSYCHIC, None, 3))
        self.assertEqual([(w.name_ja, w.kind, w.text_ja, w.supported) for w in d.powers],
                         [("ダメージスワップ", "pokemon_power", DAMAGE_SWAP_PRINTED, True)])
        self.assertEqual([(a.name_ja, [c.value for c in a.cost], a.damage, a.damage_modifier) for a in d.attacks],
                         [("あやしいひかり", ["psychic"] * 3, 30, None)])
        extract = read_extract()
        self.assertEqual(extract["pool_v0_7"], [ABRA, KADABRA, ALAKAZAM])
        self.assertNotIn(ALAKAZAM, extract["reference_only"])  # v0.6 までは参照カード

    def test_registered_entry_matches_the_verification(self):
        """登録（PowerKey("PMCG1-049", 0)）は、照合した印刷の文面・最新の説明（p.153）と同じ。実装はダメージカウンターを移す
        ``MoveDamageCounter``（エネルギーを動かす実装とは別）。"""
        entry = DEFAULT_EFFECTS.power_entry(ALAKAZAM, 0)
        self.assertIsInstance(entry, PowerEntry)
        self.assertEqual(entry.effect, MoveDamageCounter())
        self.assertEqual((entry.name_ja, entry.text_ja, entry.play_text_ja, entry.source),
                         ("ダメージスワップ", DAMAGE_SWAP_PRINTED, DAMAGE_SWAP_LATEST, "P43 p.153"))
        record = read_verification()["cards"][ALAKAZAM]
        self.assertEqual((record["page"], record["pdf_page"], record["rules_page"], record["status"]), (153, 155, 320, "不一致あり"))
        self.assertEqual(record["power_card_image_text_ja"], {"0": DAMAGE_SWAP_PRINTED})
        self.assertEqual(record["power_latest_description_ja"], {"0": DAMAGE_SWAP_LATEST})
        self.assertEqual([m["field"] for m in record["mismatches"]], ["pokemon.powers[0].text.ja"])
        self.assertEqual(DEFAULT_EFFECTS.describe()["powers"]["PMCG1-049@power0"],
                         {"implementation": "move_damage_counter", "name_ja": "ダメージスワップ", "source": "P43 p.153"})
        self.assertEqual(DEFAULT_EFFECTS.id, "kyuura-engine-0.13")  # v0.8 でベトベター・ベトベトン、v0.9 でゴース・ゴースト、v0.10 でゴーリキー・カイリキー、v0.11 でサカキのワンリキー・ゴーリキー・カイリキー、v0.12 で R団のファイヤー、v0.13 で第4弾のゼニガメ・わるいカメールの登録を加えた（ダメージスワップの登録は同じ）

    def test_power_is_not_an_attack_nor_an_energy_power(self):
        """ダメージスワップはワザ（AttackEffect）でも、エネルギーを動かすパワー（エナジートランス・あまごい）でもない（別の実装・別のログ）。"""
        self.assertTrue(issubclass(MoveDamageCounter, PowerEffect))
        for other in (AttackEffect, EnergyTransfer, AttachEnergyFromHand):
            self.assertFalse(issubclass(MoveDamageCounter, other))
        self.assertEqual(len({MoveDamageCounter.implementation_id, EnergyTransfer.implementation_id,
                              AttachEnergyFromHand.implementation_id}), 3)

    def test_check_finds_wrong_registrations(self):
        """データの形が合わない登録（使用を宣言しないパワー・説明文のないパワー）は ``check`` が問題を返す（カードは未対応になる）。"""
        effect = DEFAULT_EFFECTS.power_entry(ALAKAZAM, 0).effect
        power = load_card_pool().get(ALAKAZAM).powers[0]
        self.assertEqual(effect.check(power), [])
        self.assertTrue(effect.check(dataclasses.replace(power, kind="pokemon_body")))
        self.assertTrue(effect.check(dataclasses.replace(power, text_ja=None)))

    def test_without_the_registration_the_card_is_unsupported(self):
        """パワーの登録を除いた登録表では、フーディンは使えない（未実装のパワーを効果がないものとして扱わない）。"""
        from kyuura_engine.cards import pool_from_extract
        effects = DEFAULT_EFFECTS.without_powers("test-no-damage-swap", [DAMAGE_SWAP])
        pool = pool_from_extract(read_extract(), effects)
        self.assertFalse(pool.is_playable(ALAKAZAM))
        self.assertIn("ポケモンパワー「ダメージスワップ」", " ".join(pool.get(ALAKAZAM).unsupported_reasons))
        self.assertTrue(pool.is_playable(KADABRA) and pool.is_playable(ABRA))
        state = board(effects=effects, pool=pool)
        assert_rejected(self, state, swap(state, state.players[0].active, state.players[0].bench[1]), "UNSUPPORTED_POKEMON_POWER",
                        UnsupportedError)


# ---------------------------------------------------------------- 移動（S1〜S6・S10〜S12・S18・S19）


class MoveTest(unittest.TestCase):
    def test_active_to_bench(self):
        """バトル場のポケモンのダメージカウンターをベンチのポケモンへ（p.153 の解説「バトル場で戦っているポケモンのダメージはすべて、
        ベンチの…ポケモンにのせかえ」）。1 回で 1 個（10）。移動元は 1 個へり、移動先は 1 個ふえ、ほかは変わらない（S10〜S12・S19）。"""
        state = board()
        me = state.players[0]
        new, events = run(state, swap(state, me.active, me.bench[1]))
        self.assertEqual(damages(new), {me.active.pokemon_id: 20, me.bench[0].pokemon_id: 10, me.bench[1].pokemon_id: 10})
        self.assertEqual(kinds(events), ["pokemon_power", "move_damage_counter"])
        self.assertEqual(damages(new, 1), damages(state, 1))
        self.assertEqual((new.phase, new.current_player, new.turn_number), (Phase.MAIN, 0, TURN))
        self.assertEqual(check_invariants(new), [])

    def test_bench_to_active_and_bench_to_bench(self):
        """ベンチのポケモンからバトル場のポケモンへ・ベンチのポケモンどうしでも移せる（「自分の場にいるポケモン」。p.308 の場の図。S12）。"""
        state = board(active=alakazam(damage=0))
        me = state.players[0]
        rattata, dewgong = me.bench
        to_active = apply_command(state, swap(state, rattata, me.active))
        self.assertEqual(damages(to_active), {me.active.pokemon_id: 10, rattata.pokemon_id: 0, dewgong.pokemon_id: 0})
        to_bench = apply_command(state, swap(state, rattata, dewgong))
        self.assertEqual(damages(to_bench), {me.active.pokemon_id: 0, rattata.pokemon_id: 0, dewgong.pokemon_id: 10})

    def test_alakazam_on_the_bench_can_use_it(self):
        """ベンチのフーディンも使える（p.311・p.323「特に指示されていないかぎり、ベンチにいるポケモンも特殊能力を使うことができます」。S4）。"""
        state = board(active={"card": DEWGONG, "evolved_from": SEEL, "damage": 40}, bench=(alakazam(), {"card": RATTATA}))
        me = state.players[0]
        user = me.bench[0]
        new, events = run(state, swap(state, me.active, user, user=user))
        self.assertEqual(new.players[0].bench[0].damage, 10)
        self.assertEqual(events[1]["pokemon_id"], user.pokemon_id)

    def test_alakazam_as_target_and_source(self):
        """フーディン自身を移動先にできる（p.153 の解説「自分の場のポケモンのダメージをこの「フーディン」に移動してきて」。CONFIRMED）。
        移動元にもできる（「自分の場にいるポケモン」に除外がない。SUPPORTED）。S5。"""
        state = board(active=alakazam(damage=0), bench=({"card": DEWGONG, "evolved_from": SEEL, "damage": 30}, RATTATA))
        me = state.players[0]
        to_self = apply_command(state, swap(state, me.bench[0], me.active))
        self.assertEqual(damages(to_self)[me.active.pokemon_id], 10)
        from_self = apply_command(to_self, swap(to_self, me.active, me.bench[1]))
        self.assertEqual(damages(from_self)[me.active.pokemon_id], 0)
        self.assertEqual(damages(from_self)[me.bench[1].pokemon_id], 10)

    def test_any_number_of_times_one_counter_each(self):
        """何度でも使える（回数を数えない。S2）。1 回の使用で 1 個（実装上の仮定。S3）。同じポケモンを移動元にしたあと移動先にしてもよい。
        合計のダメージは変わらない（移動で増えも減りもしない）。"""
        state = board(active=alakazam(damage=50), bench=({"card": DEWGONG, "evolved_from": SEEL, "damage": 10}, {"card": SEEL, "damage": 20}))
        me = state.players[0]
        a, d, s = me.active, me.bench[0], me.bench[1]
        total = sum(damages(state).values())
        plan = [(a, d), (a, d), (a, s), (s, d), (d, a), (a, s), (a, d), (s, d), (a, d)]
        for source, target in plan:
            before = damages(state)
            state, events = run(state, swap(state, source, target))
            after = damages(state)
            self.assertEqual(after[source.pokemon_id], before[source.pokemon_id] - 10)
            self.assertEqual(after[target.pokemon_id], before[target.pokemon_id] + 10)
            self.assertEqual((events[1]["count"], sum(after.values())), (1, total))
        self.assertEqual(sum(1 for e in state.log if e["kind"] == "move_damage_counter"), len(plan))
        self.assertEqual(state.phase, Phase.MAIN)

    def test_source_can_be_emptied(self):
        """のっているカウンターをすべて移したら、そのポケモンからはもう移せない（S15。``NO_DAMAGE_COUNTERS``）。"""
        state = board(active=alakazam(damage=20))
        me = state.players[0]
        state = apply_command(state, swap(state, me.active, me.bench[1]))
        state = apply_command(state, swap(state, me.active, me.bench[1]))
        self.assertEqual(state.players[0].active.damage, 0)
        assert_rejected(self, state, swap(state, me.active, me.bench[1]), "NO_DAMAGE_COUNTERS")

    def test_evolved_this_turn(self):
        """ユンゲラーからフーディンに進化したその番にも使える（進化した番に特殊能力を使えないという規定はない。p.310・p.311。SUPPORTED。
        S6）。進化前のユンゲラー（パワーなし）は使えない（p.310）。進化してもダメージカウンターはそのまま（p.310・p.323）。"""
        state = board(active=kadabra(damage=20), bench=({"card": DEWGONG, "evolved_from": SEEL}, RATTATA), hand=(ALAKAZAM,))
        me = state.players[0]
        assert_rejected(self, state, UsePokemonPower(0, me.active.pokemon_id, 0, None, me.active.pokemon_id, me.bench[0].pokemon_id),
                        "NO_POKEMON_POWER")
        evolved = apply_command(state, EvolvePokemon(0, state.players[0].hand[0], me.active.pokemon_id))
        self.assertEqual((evolved.players[0].active.damage, evolved.players[0].active.evolved_turn), (20, TURN))
        new = apply_command(evolved, swap(evolved, me.active, me.bench[0], user=me.active))
        self.assertEqual(damages(new)[me.bench[0].pokemon_id], 10)

    def test_poisoned_alakazam_can_use_it(self):
        """どく状態のフーディンは使える（説明が挙げるのはねむり・マヒ・こんらんだけ。p.323「特に記述されていないかぎり」。SUPPORTED。S8）。
        どくはダメージカウンターとは別のもの（p.322「ダメージカウンターと区別できるもの」）なので、移しても消えず、移らない。"""
        state = board(active=alakazam(damage=30, poison=10))
        me = state.players[0]
        new = apply_command(state, swap(state, me.active, me.bench[1]))
        self.assertEqual(new.players[0].active.damage, 20)
        self.assertIsNotNone(new.players[0].active.conditions.poison)
        self.assertEqual(new.players[0].bench[1].conditions.names(), ())

    def test_source_and_target_conditions_do_not_matter(self):
        """移動元・移動先の特殊状態は関係しない（説明に制限がない。S9。SUPPORTED）。ベンチのフーディンが、ねむり・マヒ・こんらん・どくの
        バトル場のポケモンとのあいだで移す。移しても特殊状態は変わらない。"""
        for condition in ({"sleep": True}, {"paralysis": TURN - 1}, {"confusion": True}, {"poison": 10}, {"poison": 10, "confusion": True}):
            with self.subTest(condition=condition):
                state = board(active={"card": DEWGONG, "evolved_from": SEEL, "damage": 30, **condition}, bench=(alakazam(damage=10), RATTATA))
                me = state.players[0]
                user = me.bench[0]
                out = apply_command(state, swap(state, me.active, me.bench[1], user=user))
                back = apply_command(out, swap(out, user, me.active, user=user))
                self.assertEqual(back.players[0].active.damage, 30)
                self.assertEqual(back.players[0].active.conditions, state.players[0].active.conditions)

    def test_moved_counters_are_not_damage(self):
        """移動で増えたダメージは「ダメージを受けた」ことにならない（p.320。S19）: 移動先のユンゲラー（超・弱点 超）にフーディン（超）から
        移しても弱点（×2）を計算せず、移動先についたディフェンダー（ワザによるダメージを -20）・使うフーディンについたプラスパワー（ワザの
        ダメージ +10）も計算しない（1 個 = 10。p.319）。``damage``・``damage_prevented`` のログもない。"""
        state = board(active=alakazam(damage=40), bench=(kadabra(), RATTATA), hand=(DEFENDER, PLUSPOWER))
        me = state.players[0]
        k = me.bench[0]
        state = apply_command(state, PlayTrainer(0, state.players[0].hand[0]))  # ディフェンダー
        if state.phase is Phase.DECISION:
            state = apply_command(state, ResolveDecision(0, state.decision.id, (k.pokemon_id,)))
        state = apply_command(state, PlayTrainer(0, state.players[0].hand[0]))  # プラスパワー（バトル場のフーディンに）
        self.assertEqual([len(pk.trainers) for pk in state.players[0].in_play()], [1, 1, 0])
        new, events = run(state, swap(state, me.active, k))
        self.assertEqual((new.players[0].active.damage, new.players[0].bench[0].damage), (30, 10))
        self.assertNotIn("damage", kinds(events))
        self.assertNotIn("damage_prevented", kinds(events))

    def test_no_randomness_and_the_turn_continues(self):
        """乱数を使わない（コインを投げない）。使っても番は終わらず、そのあとワザを使える（p.309。S21）。"""
        state = board(active=alakazam(damage=30, energy=[PSYCHIC] * 3))
        me = state.players[0]
        new = apply_command(state, swap(state, me.active, me.bench[1]))
        self.assertEqual(rng_fingerprint(new.rng), rng_fingerprint(state.rng))
        self.assertEqual((new.phase, new.current_player), (Phase.MAIN, 0))
        _, events = run(new, UseAttack(0, 0))
        self.assertIn("attack", kinds(events))

    def test_nothing_else_changes(self):
        """ダメージ以外（エネルギー・ついているトレーナー・特殊状態・持続する効果・進化の重なり・場所・手札・山札・トラッシュ・サイド・
        番・段階・つけた回数）は変わらない。"""
        state = board(active=alakazam(damage=30, energy=[PSYCHIC], poison=10), bench=({"card": DEWGONG, "evolved_from": SEEL, "energy": [WATER]}, RATTATA),
                      hand=(PSYCHIC,))
        me = state.players[0]
        new = apply_command(state, swap(state, me.active, me.bench[0]))
        before, after = full(state), full(new)
        for data in (before, after):
            for player in data["players"]:
                for pk in [player["active"], *player["bench"]]:
                    pk.pop("damage")
        before.pop("log", None), after.pop("log", None)
        self.assertEqual(after, before)


# ---------------------------------------------------------------- きぜつさせない（S16・S17・A4）


class KnockOutProhibitionTest(unittest.TestCase):
    def test_boundary_for_each_damage(self):
        """移動先のダメージ d（0〜HP-10）に 1 個のせられるのは d + 10 < HP のときだけ（p.319「HPと同じか、それより大きくなったら…
        きぜつ」・p.320・最新の説明「この力によってポケモンが「きぜつ」しないかぎり」。A4: 残り HP 10 のポケモンにはもう 1 個も
        のせられない。CONFIRMED）。HP 30・60・80 のポケモン（コラッタ・ユンゲラー・フーディン自身）で確かめる。"""
        for target_card, hp in ((RATTATA, 30), (KADABRA, 60), (ALAKAZAM, 80)):
            for d in range(0, hp, 10):
                with self.subTest(target=target_card, damage=d):
                    if target_card == ALAKAZAM:
                        state = board(active=alakazam(damage=d), bench=({"card": DEWGONG, "evolved_from": SEEL, "damage": 10}, RATTATA))
                        source, target = state.players[0].bench[0], state.players[0].active
                    else:
                        spec = kadabra(damage=d) if target_card == KADABRA else {"card": RATTATA, "damage": d}
                        state = board(active=alakazam(damage=10), bench=(spec, DEWGONG_ON_SEEL))
                        source, target = state.players[0].active, state.players[0].bench[0]
                    command = swap(state, source, target)
                    if d + 10 < hp:
                        new = apply_command(state, command)
                        self.assertEqual(new.find_pokemon(target.pokemon_id)[1].damage, d + 10)
                        self.assertFalse(any(e["kind"] == "knock_out" for e in new.log[len(state.log):]))
                    else:
                        assert_rejected(self, state, command, "WOULD_KNOCK_OUT")
                    self.assertEqual(would_be_knocked_out(state, target, d + 10), d + 10 >= hp)

    def test_fill_up_to_the_limit(self):
        """HP ぎりぎりまで（残り HP 10 まで）のせられる（p.153 の解説「ダメージカウンターをHPギリギリまでのせたら」）。そこで止まる。"""
        state = board(active=alakazam(damage=70), bench=({"card": DEWGONG, "evolved_from": SEEL, "damage": 0}, {"card": RATTATA, "damage": 10}))
        me = state.players[0]
        for _ in range(7):
            state = apply_command(state, swap(state, me.active, me.bench[0]))
        self.assertEqual((state.players[0].active.damage, state.players[0].bench[0].damage), (0, 70))  # ジュゴン（HP 80）の残り HP 10
        assert_rejected(self, state, swap(state, me.bench[1], me.bench[0]), "WOULD_KNOCK_OUT")
        moved = apply_command(state, swap(state, me.bench[1], me.active))  # ほかのポケモンへは移せる
        self.assertEqual(damages(moved)[me.active.pokemon_id], 10)

    def test_random_sequences_never_knock_out(self):
        """決まった seed のでたらめな使い方（移動元・移動先をどれでも選ぶ）を 300 回: 受け付けたものは合計のダメージを変えず、きぜつがなく、
        どのポケモンもダメージが HP より小さい。拒否はどれも理由のあるコード（S10〜S17）で、状態を変えない（拒否の確認は assert_rejected）。"""
        rng = random.Random("kyuura-v0.7-swap")
        state = board(active=alakazam(damage=40), bench=({"card": DEWGONG, "evolved_from": SEEL, "damage": 30}, {"card": RATTATA, "damage": 10},
                                                         kadabra(damage=50), {"card": SEEL, "damage": 20}))
        total = sum(damages(state).values())
        codes = set()
        accepted = 0
        for _ in range(300):
            mine = state.players[0].in_play()
            source, target = rng.choice(mine), rng.choice(mine)
            command = swap(state, source, target)
            try:
                new = apply_command(state, command)
            except IllegalActionError as error:
                codes.add(error.code)
                self.assertIn(error.code, ("SAME_POKEMON", "NO_DAMAGE_COUNTERS", "WOULD_KNOCK_OUT"))
                continue
            accepted += 1
            self.assertEqual(sum(damages(new).values()), total)
            self.assertTrue(all(pk.damage < new.card_def(pk.card).hp for pk in new.players[0].in_play()))
            self.assertFalse(any(e["kind"] == "knock_out" for e in new.log))
            state = new
        self.assertGreater(accepted, 50)
        self.assertEqual(codes, {"SAME_POKEMON", "NO_DAMAGE_COUNTERS", "WOULD_KNOCK_OUT"})

    def test_invariants_catch_a_broken_check(self):
        """実装の確認が壊れていて、きぜつするダメージにしても、``apply_command`` は不変条件（場のポケモンのダメージは HP より小さい）で
        ``StateIntegrityError`` にする（二重の確かめ。きぜつの処理を呼ばずに壊れた状態を返さない）。"""

        @dataclasses.dataclass(frozen=True)
        class Broken(MoveDamageCounter):
            def check_usable(self, state, use):
                pass

        entry = DEFAULT_EFFECTS.power_entry(ALAKAZAM, 0)
        effects = DEFAULT_EFFECTS.with_powers("test-broken-swap", {DAMAGE_SWAP: dataclasses.replace(entry, effect=Broken())})
        from kyuura_engine.cards import pool_from_extract
        state = board(active=alakazam(damage=30), bench=({"card": RATTATA, "damage": 20}, DEWGONG_ON_SEEL), effects=effects,
                      pool=pool_from_extract(read_extract(), effects))
        me = state.players[0]
        with self.assertRaises(StateIntegrityError):
            apply_command(state, swap(state, me.active, me.bench[0]))
        self.assertEqual(state.players[0].bench[0].damage, 20)


# ---------------------------------------------------------------- 拒否と原子性（S7・S13〜S15・S21）


class RejectionTest(unittest.TestCase):
    def test_special_conditions_of_the_user(self):
        """ねむり・マヒ・こんらんのフーディン（バトル場）は使えない（S7。CONFIRMED）。選ばせるものの確認より先（選ばせるものが正しくなくても
        このコード。v0.5・v0.6 と同じ順番。説明の「使えない」は使うための条件で、選ばせるものはそのあとの処理の内容）。こんらんでもコインを
        投げない（ワザ・にげるの規定を流用しない）。"""
        for condition, code in (({"sleep": True}, "POKEMON_ASLEEP"), ({"paralysis": TURN - 1}, "POKEMON_PARALYZED"),
                                ({"confusion": True}, "POKEMON_CONFUSED"), ({"confusion": True, "poison": 10}, "POKEMON_CONFUSED")):
            with self.subTest(condition=condition):
                state = board(active=alakazam(damage=30, **condition))
                me = state.players[0]
                assert_rejected(self, state, swap(state, me.active, me.bench[1]), code)
                assert_rejected(self, state, swap(state, None, None), code)
                assert_rejected(self, state, swap(state, me.active, me.active), code)

    def test_choices(self):
        """選ばせるもの（移動元・移動先）の誤り。どれも状態・ログ・乱数を変えない。"""
        state = board(active=alakazam(damage=30), bench=({"card": RATTATA, "damage": 20}, DEWGONG_ON_SEEL))
        me, them = state.players
        a, r, d = me.active, me.bench[0], me.bench[1]
        cases = [
            (swap(state, None, d), "POWER_CHOICE_MISSING"),
            (swap(state, a, None), "POWER_CHOICE_MISSING"),
            (swap(state, a, d, energy=me.deck[0]), "POWER_CHOICE_NOT_USED"),  # エネルギーは選ばない
            (swap(state, 999, d), "SOURCE_NOT_IN_PLAY"),
            (swap(state, a, 999), "TARGET_NOT_IN_PLAY"),
            (swap(state, them.active, d), "SOURCE_NOT_YOURS"),  # 相手のポケモンから（S13）
            (swap(state, a, them.active), "TARGET_NOT_YOURS"),  # 相手のポケモンへ（S13）
            (swap(state, them.bench[0], them.active), "SOURCE_NOT_YOURS"),
            (swap(state, a, a), "SAME_POKEMON"),  # 「別のポケモン」（S14）
            (swap(state, d, a), "NO_DAMAGE_COUNTERS"),  # カウンターのないポケモンから（S15）
            (swap(state, a, r), "WOULD_KNOCK_OUT"),  # コラッタ（HP 30）のダメージ 20 に 1 個（S16・S17）
        ]
        for command, code in cases:
            with self.subTest(code=code, command=command):
                assert_rejected(self, state, command, code)

    def test_user(self):
        """使うポケモンの誤り: ない番号・相手のフーディン・パワーのないポケモン・ない位置・登録のないパワー。"""
        state = board(opponent=alakazam(damage=20))
        me, them = state.players
        a, d = me.active, me.bench[1]
        for command, code, error in (
            (UsePokemonPower(0, 999, 0, None, a.pokemon_id, d.pokemon_id), "POKEMON_NOT_IN_PLAY", IllegalActionError),
            (UsePokemonPower(0, them.active.pokemon_id, 0, None, them.active.pokemon_id, them.bench[0].pokemon_id), "POKEMON_NOT_YOURS",
             IllegalActionError),
            (UsePokemonPower(0, d.pokemon_id, 0, None, a.pokemon_id, d.pokemon_id), "NO_POKEMON_POWER", IllegalActionError),
            (UsePokemonPower(0, a.pokemon_id, 1, None, a.pokemon_id, d.pokemon_id), "NO_POKEMON_POWER", IllegalActionError),
            (UsePokemonPower(0, a.pokemon_id, -1, None, a.pokemon_id, d.pokemon_id), "NO_POKEMON_POWER", IllegalActionError),
        ):
            with self.subTest(code=code):
                assert_rejected(self, state, command, code, error)

    def test_turn_and_phase(self):
        """相手の番・番でないプレイヤー・ワザのあと・決定を待つ間は使えない（p.309・p.311。S1・S21）。"""
        state = board(active=alakazam(damage=30, energy=[PSYCHIC] * 3), opponent=HITMONCHAN)  # あやしいひかり（弱点で 60）できぜつしない
        me = state.players[0]
        assert_rejected(self, state, swap(state, me.active, me.bench[1], player=1, user=me.active), "NOT_YOUR_TURN")
        assert_rejected(self, state, UsePokemonPower(2, me.active.pokemon_id, 0, None, me.active.pokemon_id, me.bench[1].pokemon_id),
                        "INVALID_PLAYER")
        attacked = apply_command(state, UseAttack(0, 0))  # あやしいひかり（コインの結果に関わらず番は終わる）
        self.assertEqual(attacked.current_player, 1)
        assert_rejected(self, attacked, swap(attacked, me.active, me.bench[1], player=0, user=me.active), "NOT_YOUR_TURN")
        # ユンゲラーの「じこさいせい」の決定を待つ間（ワザの途中。p.309「ワザを使っている最中に…特殊能力の使用を宣言してはいけません」）
        state = board(active=kadabra(damage=20, energy=[PSYCHIC, PSYCHIC]), bench=(alakazam(damage=10), DEWGONG_ON_SEEL))
        pending = apply_command(state, UseAttack(0, 0))
        self.assertEqual((pending.phase, pending.decision.kind), (Phase.DECISION, "discard_energy"))
        user = pending.players[0].bench[0]
        assert_rejected(self, pending, swap(pending, user, pending.players[0].bench[1], user=user), "WRONG_PHASE")

    def test_rejections_keep_every_zone(self):
        """拒否のあと、カードの位置（手札・山札・トラッシュ・サイド・場）・ダメージ・番・段階・乱数・ログが同じ（assert_rejected が形式 9 の
        書き出し全体を比べる）。書き出しの監査も通る。"""
        state = board(bench=({"card": RATTATA, "damage": 20}, DEWGONG_ON_SEEL), hand=(PSYCHIC, POTION), opponent_bench=(SEEL, RATTATA))
        me = state.players[0]
        for command, code in ((swap(state, me.active, me.active), "SAME_POKEMON"), (swap(state, me.bench[1], me.active), "NO_DAMAGE_COUNTERS"),
                              (swap(state, me.active, me.bench[0]), "WOULD_KNOCK_OUT")):
            with self.subTest(code=code):
                assert_rejected(self, state, command, code)
        self.assertEqual(serialization_problems(state), [])


# ---------------------------------------------------------------- ほかの処理との関係（S20・S22〜S25）


class InteractionTest(unittest.TestCase):
    def test_potion_after_moving(self):
        """移したカウンターは、きずぐすり（とりのぞく。p.320「ダメージの回復」）でとりのぞける（S25）。"""
        state = board(active=alakazam(damage=40), bench=({"card": DEWGONG, "evolved_from": SEEL, "damage": 0}, RATTATA), hand=(POTION,))
        me = state.players[0]
        for _ in range(3):
            state = apply_command(state, swap(state, me.active, me.bench[0]))
        state = apply_command(state, PlayTrainer(0, state.players[0].hand[0]))
        if state.phase is Phase.DECISION:
            state = apply_command(state, ResolveDecision(0, state.decision.id, (me.bench[0].pokemon_id,)))
        self.assertEqual((state.players[0].active.damage, state.players[0].bench[0].damage), (10, 10))

    def test_recover_after_moving_to_kadabra(self):
        """ユンゲラーへ移してから「じこさいせい」ですべてとりのぞく（p.153 の解説の「思い出させる」は未実装なので、ユンゲラー自身で）。"""
        state = board(active=kadabra(damage=10, energy=[PSYCHIC, PSYCHIC]), bench=(alakazam(damage=40), DEWGONG_ON_SEEL))
        me = state.players[0]
        user = me.bench[0]
        for _ in range(4):
            state = apply_command(state, swap(state, user, me.active, user=user))
        self.assertEqual(state.players[0].active.damage, 50)
        pending = apply_command(state, UseAttack(0, 0))
        done = apply_command(pending, ResolveDecision(0, pending.decision.id, (pending.decision.options[0],)))
        self.assertEqual((done.players[0].active.damage, done.players[0].bench[0].damage), (0, 0))

    def test_poison_check_after_moving(self):
        """ポケモンチェックのどく（p.323）できぜつしそうなバトル場のポケモンから移しておけば、きぜつしない（どくは残る。S8・S9）。"""
        state = board(active={"card": RATTATA, "damage": 20, "poison": 10}, bench=(alakazam(), DEWGONG_ON_SEEL))
        me = state.players[0]
        kept = apply_command(state, swap(state, me.active, me.bench[1], user=me.bench[0]))
        after = apply_command(kept, EndTurn(0))
        self.assertEqual(after.find_pokemon(me.active.pokemon_id)[1].damage, 20)
        self.assertFalse(any(e["kind"] == "knock_out" for e in after.log))
        lost = apply_command(state, EndTurn(0))
        self.assertTrue(any(e["kind"] == "knock_out" for e in lost.log))

    def test_counters_follow_the_pokemon(self):
        """移したカウンターは、進化・にげるでポケモンといっしょ（p.310・p.323「ダメージカウンターだけは、進化や退化をしても、そのまま
        受けつがれます」・p.311。S22・S23）。きぜつするかどうかは、いまのいちばん上のカードの HP で決める（p.310）。"""
        state = board(active=alakazam(damage=30, energy=[PSYCHIC] * 3), bench=({"card": ABRA}, DEWGONG_ON_SEEL), hand=(KADABRA,))
        me = state.players[0]
        abra = me.bench[0]
        state = apply_command(state, swap(state, me.active, abra))
        state = apply_command(state, swap(state, me.active, abra))
        self.assertEqual(state.find_pokemon(abra.pokemon_id)[1].damage, 20)  # HP 30 のケーシィに 20（ぎりぎり）
        assert_rejected(self, state, swap(state, me.active, abra), "WOULD_KNOCK_OUT")
        evolved = apply_command(state, EvolvePokemon(0, state.players[0].hand[0], abra.pokemon_id))
        grown = evolved.find_pokemon(abra.pokemon_id)[1]
        self.assertEqual((evolved.cards[grown.card].card_id, grown.damage), (KADABRA, 20))
        evolved = apply_command(evolved, swap(evolved, me.active, abra))  # HP 60 になったので、まだのせられる
        retreated = apply_command(evolved, Retreat(0, tuple(evolved.players[0].active.energy), grown.card))
        self.assertEqual((retreated.players[0].active.pokemon_id, retreated.players[0].active.damage), (abra.pokemon_id, 30))
        self.assertEqual(retreated.find_pokemon(me.active.pokemon_id)[1].damage, 0)

    def test_all_three_powers_on_the_same_field(self):
        """フシギバナ（エナジートランス）・カメックス（あまごい）・フーディン（ダメージスワップ）が同じ場にいる番に、3 つとも使える。
        どれも番を終わらせず、ほかのパワーの記録を変えない（ダメージスワップはあまごいの枚数 ``energy_attached_by_powers_this_turn`` に
        数えない）。R13（あまごいのあとの通常の操作）は今までどおり止まる。"""
        venusaur = {"card": VENUSAUR, "evolved_from": [BULBASAUR, IVYSAUR], "energy": [GRASS], "damage": 30}
        blastoise = {"card": BLASTOISE, "evolved_from": [SQUIRTLE, WARTORTLE]}
        state = board(active=venusaur, bench=(blastoise, alakazam(), {"card": SQUIRTLE}), hand=(WATER, WATER))
        me = state.players[0]
        v, b, a, s = me.active, *me.bench
        state, swap_events = run(state, swap(state, v, s, user=a))
        self.assertEqual(state.energy_attached_by_powers_this_turn, 0)
        state, rain_events = run(state, UsePokemonPower(0, b.pokemon_id, 0, state.players[0].hand[0], None, s.pokemon_id))
        state, trans_events = run(state, UsePokemonPower(0, v.pokemon_id, 0, v.energy[0], v.pokemon_id, b.pokemon_id))
        state, swap_again = run(state, swap(state, v, b, user=a))
        self.assertEqual([kinds(e)[1] for e in (swap_events, rain_events, trans_events, swap_again)],
                         ["move_damage_counter", "power_attach_energy", "move_energy", "move_damage_counter"])
        self.assertEqual(damages(state)[v.pokemon_id], 10)
        self.assertEqual(state.energy_attached_by_powers_this_turn, 1)
        assert_rejected(self, state, AttachEnergy(0, state.players[0].hand[0], v.card), "UNRESOLVED_ATTACH_AFTER_POWER_ATTACH", UnsupportedError)
        self.assertEqual((state.phase, check_invariants(state)), (Phase.MAIN, []))

    def test_damage_swap_does_not_count_as_attaching_energy(self):
        """ダメージスワップのあとの通常の操作（手札からつける。p.310）は、ふだんどおり受け付ける（R13 の停止はあまごいでつけたときだけ）。"""
        state = board(hand=(PSYCHIC,))
        me = state.players[0]
        state = apply_command(state, swap(state, me.active, me.bench[1]))
        attached = apply_command(state, AttachEnergy(0, state.players[0].hand[0], me.active.card))
        self.assertEqual((attached.energy_attachments_this_turn, attached.energy_attached_by_powers_this_turn), (1, 0))


# ---------------------------------------------------------------- ログ・書き出し・不変条件


class LogSerializationInvariantTest(unittest.TestCase):
    def test_log_fields(self):
        """宣言（``pokemon_power``）のすぐあとに ``move_damage_counter`` が 1 つ。項目は使ったポケモン・パワー・数（1）・移動元・移動先・
        移したあとのダメージ（公開の情報だけ。手札などの非公開の情報を書かない）。"""
        state = board()
        me = state.players[0]
        _, events = run(state, swap(state, me.active, me.bench[1]))
        self.assertEqual(set(events[0]), {"kind", "turn", "player", "pokemon", "pokemon_id", "power", "power_index"})
        self.assertEqual(events[1], {"kind": "move_damage_counter", "turn": TURN, "player": 0, "pokemon": me.active.card,
                                     "pokemon_id": me.active.pokemon_id, "power": "PMCG1-049@power0", "count": 1,
                                     "from_pokemon_id": me.active.pokemon_id, "to_pokemon_id": me.bench[1].pokemon_id,
                                     "from_total_damage": 20, "to_total_damage": 10})

    def test_no_new_format(self):
        """v0.7 は書き出しの形式を加えない（形式 9 のまま。移したカウンターは場のポケモンの ``damage``）。進化したフーディンがいるので形式 1〜6
        は ``ValueError``、7〜9 は書き出せる。形式 15 はない（10〜14 はその後の版で加えた）。"""
        state = board()
        new = apply_command(state, swap(state, state.players[0].active, state.players[0].bench[1]))
        data = full(new)
        self.assertEqual((data["format_version"], data["players"][0]["active"]["damage"], data["players"][0]["bench"][1]["damage"]), (9, 20, 10))
        for version in range(1, 7):
            with self.subTest(format_version=version), self.assertRaises(ValueError):
                state_to_dict(new, format_version=version)
        for version in (7, 8):
            self.assertEqual(state_to_dict(new, format_version=version)["players"][0]["active"]["damage"], 20)
        with self.assertRaises(ValueError):
            state_to_dict(new, format_version=18)  # v0.56 で 16、v0.57 で 17 を加えた。v0.7 では 10 がなかった。10 は v0.31、11 は v0.44、12 は v0.47、13 は v0.48、14 は v0.49、15 は v0.50（ダメージスワップの項目ではない）
        self.assertEqual(serialization_problems(new), [])

    def test_copies(self):
        """使ったあとの状態は、clone・deepcopy・pickle で同じものになり、同じ続きになる。渡した状態は変わらない。"""
        state = board()
        me = state.players[0]
        new = apply_command(state, swap(state, me.active, me.bench[1]))
        for copied in (new.clone(), copy.deepcopy(new), pickle.loads(pickle.dumps(new))):
            self.assertEqual(full(copied), full(new))
            again = apply_command(copied, swap(copied, me.active, me.bench[1]))
            self.assertEqual((damages(again)[me.bench[1].pokemon_id], check_invariants(again)), (20, []))
        self.assertEqual(damages(state)[me.active.pokemon_id], 30)

    def test_command_round_trip(self):
        command = UsePokemonPower(0, 5, 0, None, 3, 7)
        data = command_to_dict(command)
        self.assertEqual(data, {"type": "use_pokemon_power", "player": 0, "pokemon": 5, "power": 0, "energy": None, "source": 3, "target": 7})
        self.assertEqual(command_from_dict(data), command)

    def test_invariants_find_broken_damage(self):
        """ダメージの不変条件（10 の倍数・HP より小さい・0 以上）は、移したあとの状態でも働く（書きかえると見つかる）。"""
        state = board()
        new = apply_command(state, swap(state, state.players[0].active, state.players[0].bench[1]))
        self.assertEqual(check_invariants(new), [])
        for value in (-10, 5, 80, 90):
            broken = new.clone()
            broken.players[0].active.damage = value
            with self.subTest(value=value):
                self.assertTrue(check_invariants(broken))


if __name__ == "__main__":
    unittest.main()

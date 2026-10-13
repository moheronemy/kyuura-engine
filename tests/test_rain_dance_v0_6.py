"""カメックス（PMCG1-032。v0.6）のポケモンパワー「あまごい」: 登録と照合・手札から場へのエネルギーの移動・通常の操作との関係・
特殊状態・拒否と原子性・ほかの処理との関係・ログ・書き出し・不変条件。

根拠は『ポケモンカードオフィシャルブック2000』[P43]（kyuura の NEO-2000-OFFICIAL-RULES。kyuura の rule_history.json の
ポケモンパワーの記録は第4版（ed4）のもので、2000.02.14 版の記録はない）。裁定の表は docs/rain-dance-v0.6.md。

- p.90: 見出し「カメールから進化 カメックス LV.52／HP100」「ポケモンカード第1弾」。「特殊能力」欄の最新の説明「この力は、自分の番の
  中で何度でも使える。自分の手札から「水」エネルギーカードを出して、自分の場の「水」ポケモンにつける。このカードが「ねむり・マヒ・
  こんらん」状態のとき、この力は使えない。」（R1〜R10）
- p.307: カードの中に記述されている内容がプレイルールとむじゅんしているときは、カードの記述を優先する
- p.310: 手札からエネルギーをつける通常の操作は 1 回の自分の番ごとに 1 枚だけ。相手の場のポケモンには自分のエネルギーをつけられない。
  進化しても、ついているエネルギーはそのまま。進化したポケモンは、進化前の特殊能力を使えない
- p.311・p.323: 特殊能力の使い方（宣言 → 条件 → 処理。ベンチのポケモンも使える。エネルギーがついていなくても使える。何度でも。
  使用を宣言したら、それによって起こることをすべてすませてから）
- p.309: ワザを使ったら番は終わる（R14）
- p.322: 特殊状態になるのはバトル場のポケモンだけ（R9・R10）
- p.298: レインボーエネルギーは手札では色を持たないので、あまごいで水エネルギーとしてつけられない（特殊エネルギーは未実装。R4）

通常の操作（手札からつける。p.310）とあまごいの関係（R11〜R13）:

- R12（通常の操作でつけたあとのあまごい）: どちらの読み方でも使える（SUPPORTED）。受け付ける
- R13（あまごいでつけたあとの、その番の通常の操作）: 原典で決められない（UNRESOLVED）。``UNRESOLVED_ATTACH_AFTER_POWER_ATTACH``
  で止める。ここでは「止まること・状態が変わらないこと」だけを確かめ、受け付ける・拒否するのどちらにもテストで決めない

1 回の使用で 1 枚をつけるのは実装上の仮定（印刷の文面「1度に何枚でも」・最新の説明「何度でも使える」のどちらでも、何枚つけても 1 枚
ずつつけた結果と同じ）。盤面を直接作るテスト（``build_test_state``）は 1 か所の規定を確かめるためのもので、自然な対戦の結果では
ない（自然な対戦は tests/test_blastoise_games_v0_6.py）。
"""

import copy
import dataclasses
import pickle
import unittest

from kyuura_engine import (
    AttachEnergy, EndTurn, EvolvePokemon, IllegalActionError, Phase, PlayTrainer, ResolveDecision, Retreat, UnsupportedError, UseAttack,
    UsePokemonPower, apply_command, check_invariants, command_from_dict, command_to_dict, new_game, state_to_dict,
)
from kyuura_engine.cards import EnergyType, load_card_pool, read_extract, read_verification
from kyuura_engine.effects import (
    DEFAULT_EFFECTS, AttachEnergyFromHand, AttackEffect, EnergyTransfer, PowerEffect, PowerEntry, PowerKey,
)
from kyuura_engine.rng import rng_fingerprint

from tests.helpers import (
    ALAKAZAM, BLASTOISE, BULBASAUR, CHARIZARD, FIRE, FIRE_DECK, GRASS, HITMONCHAN, IVYSAUR, LIGHTNING, POTION, RATTATA, SEEL, SQUIRTLE, STARYU,
    SWITCH, VENUSAUR, WARTORTLE, WATER, WATER_FIGHTING_DECK, build_test_state,
)
from tests.log_audit import serialization_problems

RAIN_DANCE = PowerKey(BLASTOISE, 0)
RAIN_DANCE_PRINTED = "カメックスは自分の「水」ポケモンに対して、手札の「水」エネルギーを1度に何枚でもつけることができる。「ねむり・マヒ・こんらん」状態の時は使えない。"
RAIN_DANCE_LATEST = ("この力は、自分の番の中で何度でも使える。自分の手札から「水」エネルギーカードを出して、自分の場の「水」ポケモンにつける。"
                     "このカードが「ねむり・マヒ・こんらん」状態のとき、この力は使えない。")
TURN = 7  # 先攻はプレイヤー 0。2 進化したカメックスを、今の番より前の自分の番（5）に進化したものとして置ける


def full(state):
    """v0.6 の最新の形式（9。``energy_attached_by_powers_this_turn`` を含む）。"""
    return state_to_dict(state, format_version=9)


def run(state, command):
    new = apply_command(state, command)
    return new, [dict(e) for e in new.log[len(state.log):]]


def kinds(events):
    return [e["kind"] for e in events]


def hand_uids(state, player, card_id):
    return [u for u in state.players[player].hand if state.cards[u].card_id == card_id]


def blastoise(**extra):
    """ゼニガメ → カメール → カメックスと 2 進化したカメックス（盤面を直接作る。1 進化した番は状態に持たない）。"""
    return {"card": BLASTOISE, "evolved_from": [SQUIRTLE, WARTORTLE], **extra}


def wartortle(**extra):
    return {"card": WARTORTLE, "evolved_from": SQUIRTLE, **extra}


def board(active=None, *, bench=(SQUIRTLE, RATTATA), hand=(WATER, WATER, WATER, FIRE), opponent=None, opponent_bench=(SEEL,),
          opponent_hand=(WATER,), turn=TURN, player=0, **kwargs):
    """プレイヤー ``player`` の番 ``turn`` の盤面。既定はバトル場にエネルギーのないカメックス、ベンチにゼニガメ（水）とコラッタ（無色）、
    手札に水エネルギー 3 枚と炎エネルギー 1 枚。相手はバトル場にエビワラー（HP 70・闘・弱点 超）、ベンチにパウワウ（水）、手札に水
    エネルギー 1 枚。"""
    mine = {"active": active or blastoise(), "bench": list(bench), "hand": list(hand)}
    theirs = {"active": opponent or HITMONCHAN, "bench": list(opponent_bench), "hand": list(opponent_hand)}
    specs = [mine, theirs] if player == 0 else [theirs, mine]
    return build_test_state(specs, current_player=player, turn_number=turn, **kwargs)


def user_of(state, player=None):
    player = state.current_player if player is None else player
    return next(pk for pk in state.players[player].in_play() if state.cards[pk.card].card_id == BLASTOISE)


def rain_dance(state, energy, target, *, player=None, user=None, source=None):
    """あまごいを 1 回使うコマンド。``target``・``user`` は場のポケモン（PokemonInPlay）か場のポケモンの番号。"""
    player = state.current_player if player is None else player
    user = user_of(state, player) if user is None else user
    pid = (lambda x: x if isinstance(x, int) else x.pokemon_id)
    return UsePokemonPower(player, pid(user), 0, energy, source, pid(target))


def assert_rejected(test, state, command, code, error=IllegalActionError):
    """拒否され、渡した状態（場・手札・エネルギー・番・つけた回数・パワーでつけた枚数）もログも乱数も変わらない。"""
    before, fingerprint, log = full(state), rng_fingerprint(state.rng), state.log
    with test.assertRaises(error) as ctx:
        apply_command(state, command)
    test.assertIs(type(ctx.exception), error)
    test.assertEqual(ctx.exception.code, code)
    test.assertEqual((full(state), rng_fingerprint(state.rng)), (before, fingerprint))
    test.assertIs(state.log, log)


# ---------------------------------------------------------------- 登録と照合


class RainDanceRegistrationTest(unittest.TestCase):
    def test_card_values(self):
        """p.90 で照合した値（300dpi・図版は 600dpi）: 「カメールから進化」の 2 進化、HP 100、水、弱点 雷（×2）、抵抗力なし、にげる 3、
        ポケモンパワー 1 つ（あまごい）、ワザ 1 つ（ハイドロポンプ 水水水 40+）。v0.5 までは参照カード（未対応）だった。"""
        pool = load_card_pool()
        d = pool.get(BLASTOISE)
        self.assertTrue(d.supported and pool.is_playable(BLASTOISE) and d.is_stage2_pokemon)
        self.assertEqual((d.name_ja, d.evolves_from, d.hp, d.pokemon_type, d.weakness, d.resistance, d.retreat_cost),
                         ("カメックス", "カメール", 100, EnergyType.WATER, EnergyType.LIGHTNING, None, 3))
        self.assertEqual([(w.name_ja, w.kind, w.text_ja, w.supported) for w in d.powers],
                         [("あまごい", "pokemon_power", RAIN_DANCE_PRINTED, True)])
        self.assertEqual([(a.name_ja, [c.value for c in a.cost], a.damage, a.damage_modifier) for a in d.attacks],
                         [("ハイドロポンプ", ["water"] * 3, 40, "+")])
        extract = read_extract()
        self.assertEqual(extract["pool_v0_6"], [SQUIRTLE, WARTORTLE, BLASTOISE])
        self.assertNotIn(BLASTOISE, extract["reference_only"])  # v0.5 までは参照カード
        # 参照カードの役は v0.6 でフーディンへ移り、v0.7 でフーディンを対応にしたのでリザードンへ移った
        self.assertNotIn(ALAKAZAM, extract["reference_only"])
        self.assertIn(CHARIZARD, extract["reference_only"])

    def test_registered_entry_matches_the_verification(self):
        """登録（PowerKey("PMCG1-032", 0)）は、照合した印刷の文面・最新の説明（p.90）と同じ。実装は手札から「水」エネルギーを「水」
        ポケモンへつける ``AttachEnergyFromHand``（エナジートランスの ``EnergyTransfer`` とは別の実装）。"""
        entry = DEFAULT_EFFECTS.power_entry(BLASTOISE, 0)
        self.assertIsInstance(entry, PowerEntry)
        self.assertEqual(entry.effect, AttachEnergyFromHand(energy_type=EnergyType.WATER, pokemon_type=EnergyType.WATER))
        self.assertEqual((entry.name_ja, entry.text_ja, entry.play_text_ja, entry.source),
                         ("あまごい", RAIN_DANCE_PRINTED, RAIN_DANCE_LATEST, "P43 p.90"))
        record = read_verification()["cards"][BLASTOISE]
        self.assertEqual((record["page"], record["pdf_page"]), (90, 92))
        self.assertEqual(record["power_card_image_text_ja"], {"0": RAIN_DANCE_PRINTED})
        self.assertEqual(record["power_latest_description_ja"], {"0": RAIN_DANCE_LATEST})
        self.assertEqual([m["field"] for m in record["mismatches"]], ["pokemon.powers[0].text.ja", "pokemon.attacks[0].text.ja"])
        self.assertEqual(DEFAULT_EFFECTS.describe()["powers"]["PMCG1-032@power0"],
                         {"implementation": "attach_energy_from_hand", "name_ja": "あまごい", "source": "P43 p.90"})
        self.assertEqual(DEFAULT_EFFECTS.id, "kyuura-engine-0.8")  # v0.7 でフーディン、v0.8 でベトベター・ベトベトンの登録を加えた（あまごいの登録は同じ）

    def test_power_is_not_an_attack_nor_an_energy_transfer(self):
        """あまごいはワザ（AttackEffect）でも、場のエネルギーをつけかえるエナジートランスでもない（別の実装・別のログ）。"""
        self.assertTrue(issubclass(AttachEnergyFromHand, PowerEffect))
        self.assertFalse(issubclass(AttachEnergyFromHand, AttackEffect))
        self.assertFalse(issubclass(AttachEnergyFromHand, EnergyTransfer))
        self.assertNotEqual(AttachEnergyFromHand.implementation_id, EnergyTransfer.implementation_id)

    def test_check_finds_wrong_registrations(self):
        """データの形が合わない登録（使用を宣言しないパワー・説明文のないパワー）は ``check`` が問題を返す（カードは未対応になる）。"""
        effect = DEFAULT_EFFECTS.power_entry(BLASTOISE, 0).effect
        power = load_card_pool().get(BLASTOISE).powers[0]
        self.assertEqual(effect.check(power), [])
        self.assertTrue(effect.check(dataclasses.replace(power, kind="pokemon_body")))
        self.assertTrue(effect.check(dataclasses.replace(power, text_ja=None)))

    def test_unregistered_rain_dance_makes_the_card_unsupported(self):
        """登録を除いた登録表では、カメックスはデッキに入らない（あまごいを効果のないものとして扱わない）。"""
        from kyuura_engine.cards import pool_from_extract
        effects = DEFAULT_EFFECTS.without_powers("test-no-rain-dance", [RAIN_DANCE])
        pool = pool_from_extract(read_extract(), effects)
        self.assertFalse(pool.is_playable(BLASTOISE))
        self.assertEqual([(w.name_ja, w.supported) for w in pool.get(BLASTOISE).powers], [("あまごい", False)])
        self.assertTrue(pool.is_playable(SQUIRTLE) and pool.is_playable(WARTORTLE))


# ---------------------------------------------------------------- 手札から場へ（R1〜R8）


class RainDanceAttachTest(unittest.TestCase):
    def test_moves_the_same_card_from_hand(self):
        """手札の同じ uid の「水」エネルギーカードを、手札から取りのぞいて、つける先の ``energy`` の最後に加える（複製しない・なくさない・
        持ち主は変わらない）。通常の操作の回数（``energy_attachments_this_turn``）は変えず、パワーでつけた枚数が 1 増える。乱数は使わない。
        ログは ``pokemon_power``（宣言。p.311 の手順 1）→ ``power_attach_energy``（処理。手順 3）。番は続く（R14）。"""
        for attached in (0, 1):
            with self.subTest(energy_attachments_this_turn=attached):
                state = board(energy_attachments_this_turn=attached)
                me = state.players[0]
                water = hand_uids(state, 0, WATER)[1]
                fingerprint = rng_fingerprint(state.rng)
                new, events = run(state, rain_dance(state, water, me.active))
                p = new.players[0]
                self.assertEqual(p.active.energy, [water])
                self.assertEqual(p.hand, [u for u in me.hand if u != water])
                self.assertEqual((new.cards[water].owner, new.cards[water].card_id), (0, WATER))
                self.assertNotIn(water, (*p.deck, *p.discard, *p.prizes, *(u for pk in p.bench for u in pk.energy)))
                self.assertEqual((new.energy_attachments_this_turn, new.energy_attached_by_powers_this_turn), (attached, 1))
                self.assertEqual(rng_fingerprint(new.rng), fingerprint)
                self.assertEqual((new.phase, new.current_player, new.turn_number), (Phase.MAIN, 0, TURN))
                self.assertEqual(kinds(events), ["pokemon_power", "power_attach_energy"])
                self.assertEqual(events[0], {"kind": "pokemon_power", "turn": TURN, "player": 0, "pokemon": me.active.card,
                                             "pokemon_id": me.active.pokemon_id, "power": "あまごい", "power_index": 0})
                self.assertEqual(events[1], {"kind": "power_attach_energy", "turn": TURN, "player": 0, "pokemon": me.active.card,
                                             "pokemon_id": me.active.pokemon_id, "power": "PMCG1-032@power0", "energy": water,
                                             "to_pokemon_id": me.active.pokemon_id})
                self.assertEqual(check_invariants(new), [])

    def test_every_own_water_pokemon_is_a_target(self):
        """つける先は自分の場の「水」ポケモン（バトル場・ベンチ。カメックス自身を含む。R5〜R7）。カメックスはバトル場でもベンチでも
        使える（R8。p.311「特に指示されていないかぎり、ベンチにいるポケモンも」）。"""
        for user_on_bench in (False, True):
            if user_on_bench:
                state = board(active=SQUIRTLE, bench=(blastoise(), wartortle(), STARYU, RATTATA))
            else:
                state = board(bench=(SQUIRTLE, wartortle(), STARYU, RATTATA))
            water_pokemon = [pk for pk in state.players[0].in_play() if state.card_def(pk.card).pokemon_type is EnergyType.WATER]
            self.assertEqual(len(water_pokemon), 4)
            for target in water_pokemon:
                with self.subTest(user_on_bench=user_on_bench, target=state.cards[target.card].card_id):
                    water = hand_uids(state, 0, WATER)[0]
                    new = apply_command(state, rain_dance(state, water, target))
                    self.assertEqual(new.players[0].find_by_pokemon_id(target.pokemon_id).energy, [*target.energy, water])

    def test_many_uses_in_one_turn(self):
        """何度でも使える（R2）。1 回の使用で 1 枚（実装上の仮定。R3）: 4 回使えば 4 枚つき、ログは宣言と処理が 4 組。回数を制限しない。"""
        state = board(hand=(WATER,) * 4)
        me = state.players[0]
        targets = [me.active, me.bench[0], me.active, me.bench[0]]
        events = []
        for water, target in zip(hand_uids(state, 0, WATER), targets):
            state, new_events = run(state, rain_dance(state, water, target))
            events += new_events
        p = state.players[0]
        self.assertEqual((len(p.active.energy), len(p.bench[0].energy), p.hand), (2, 2, []))
        self.assertEqual(kinds(events), ["pokemon_power", "power_attach_energy"] * 4)
        self.assertEqual((state.energy_attachments_this_turn, state.energy_attached_by_powers_this_turn), (0, 4))
        self.assertEqual(check_invariants(state), [])

    def test_user_needs_no_energy(self):
        """エネルギーがついていないカメックスも使える（p.311「特に指示されていないかぎり、エネルギーカードをつけていなくても」）。"""
        state = board()
        self.assertEqual(state.players[0].active.energy, [])
        apply_command(state, rain_dance(state, hand_uids(state, 0, WATER)[0], state.players[0].bench[0]))

    def test_any_blastoise_can_be_the_user(self):
        """2 匹のカメックスのどちらでも使える（p.311「1回の自分の番の中で、複数のポケモンが」）。"""
        state = board(bench=(blastoise(), SQUIRTLE))
        me = state.players[0]
        for user in (me.active, me.bench[0]):
            with self.subTest(user=user.pokemon_id):
                apply_command(state, rain_dance(state, hand_uids(state, 0, WATER)[0], me.bench[1], user=user))

    def test_counter_resets_at_the_start_of_the_turn(self):
        """パワーでつけた枚数は番の最初に 0 にする（相手の番・次の自分の番）。"""
        state = board()
        state = apply_command(state, rain_dance(state, hand_uids(state, 0, WATER)[0], state.players[0].active))
        state = apply_command(state, EndTurn(0))
        self.assertEqual((state.current_player, state.energy_attached_by_powers_this_turn), (1, 0))
        state = apply_command(state, EndTurn(1))
        self.assertEqual((state.current_player, state.energy_attached_by_powers_this_turn), (0, 0))
        self.assertEqual(check_invariants(state), [])


# ---------------------------------------------------------------- 通常の操作との関係（R11〜R13）


class NormalAttachmentTest(unittest.TestCase):
    def test_rain_dance_after_attaching_from_hand(self):
        """R12: 通常の操作（p.310）でつけたあとも、あまごいを使える（p.307・p.90「何度でも使える」。どちらの読み方でも使える。SUPPORTED）。
        通常の操作の回数は 1 のまま、パワーでつけた枚数が増える。"""
        state = board()
        me = state.players[0]
        waters = hand_uids(state, 0, WATER)
        state = apply_command(state, AttachEnergy(0, waters[0], me.bench[1].card))  # コラッタ（無色）へ通常の操作
        for n, water in enumerate(waters[1:], start=1):
            state = apply_command(state, rain_dance(state, water, me.active))
            self.assertEqual((state.energy_attachments_this_turn, state.energy_attached_by_powers_this_turn), (1, n))

    def test_attaching_from_hand_after_rain_dance_is_not_decided(self):
        """R13: あまごいでつけたあと、通常の操作をまだしていない番の通常の操作は、原典で決められない（p.310 の「1枚だけ」に
        あまごいでつけたカードを数えるかが書かれていない）。``UNRESOLVED_ATTACH_AFTER_POWER_ATTACH`` で止め、状態は変えない。
        受け付ける・拒否するのどちらとも決めない（この裁定をテストで決めない。docs/rain-dance-v0.6.md）。"""
        state = board()
        me = state.players[0]
        waters = hand_uids(state, 0, WATER)
        fire = hand_uids(state, 0, FIRE)[0]
        state = apply_command(state, rain_dance(state, waters[0], me.active))
        for energy, target in ((waters[1], me.active), (fire, me.bench[1]), (fire, me.bench[0])):
            with self.subTest(energy=energy, target=target.pokemon_id):
                assert_rejected(self, state, AttachEnergy(0, energy, target.card), "UNRESOLVED_ATTACH_AFTER_POWER_ATTACH", UnsupportedError)

    def test_second_attachment_from_hand_is_still_rejected(self):
        """通常の操作は、どちらの読み方でも 1 番に 1 回だけ（p.310。CONFIRMED）。通常の操作 → あまごい → 通常の操作の 2 回目は
        ``ENERGY_ALREADY_ATTACHED``（R13 の止め方より先）。"""
        state = board()
        me = state.players[0]
        waters = hand_uids(state, 0, WATER)
        state = apply_command(state, AttachEnergy(0, waters[0], me.active.card))
        state = apply_command(state, rain_dance(state, waters[1], me.active))
        assert_rejected(self, state, AttachEnergy(0, waters[2], me.active.card), "ENERGY_ALREADY_ATTACHED")

    def test_energy_trans_is_not_an_attachment_from_hand(self):
        """エナジートランス（場のエネルギーのつけかえ）は手札からつけないので、パワーでつけた枚数を増やさない（v0.5 の V10 と同じく
        通常の操作の回数も変えない）。そのあとの通常の操作は止めない。"""
        venusaur = {"card": VENUSAUR, "evolved_from": [BULBASAUR, IVYSAUR], "energy": [GRASS, GRASS]}
        state = board(active=venusaur, bench=(blastoise(), BULBASAUR), hand=(GRASS, WATER))
        me = state.players[0]
        state = apply_command(state, UsePokemonPower(0, me.active.pokemon_id, 0, me.active.energy[0], me.active.pokemon_id,
                                                     me.bench[1].pokemon_id))
        self.assertEqual((state.energy_attachments_this_turn, state.energy_attached_by_powers_this_turn), (0, 0))
        state = apply_command(state, AttachEnergy(0, hand_uids(state, 0, GRASS)[0], me.active.card))
        self.assertEqual(state.energy_attachments_this_turn, 1)


# ---------------------------------------------------------------- 特殊状態（R9・R10）


class SpecialConditionTest(unittest.TestCase):
    def test_asleep_paralyzed_confused_blastoise_cannot_use_it(self):
        """R9: このカードがねむり・マヒ・こんらんのとき使えない（最新の説明）。こんらんでもコインは投げない（ワザ・にげるの規定ではない）。
        確かめるのは選ばせるものより先（選ばせるものがなくても、特殊状態のコードで拒否する）。"""
        for spec, code in (({"sleep": True}, "POKEMON_ASLEEP"), ({"paralysis": TURN - 1}, "POKEMON_PARALYZED"),
                           ({"confusion": True}, "POKEMON_CONFUSED"), ({"poison": 10, "confusion": True}, "POKEMON_CONFUSED")):
            with self.subTest(code=code, spec=spec):
                state = board(active=blastoise(**spec))
                me = state.players[0]
                assert_rejected(self, state, rain_dance(state, hand_uids(state, 0, WATER)[0], me.bench[0]), code)
                assert_rejected(self, state, UsePokemonPower(0, me.active.pokemon_id), code)

    def test_poisoned_blastoise_can_use_it(self):
        """どくは挙げられていないので使える（p.323「特に記述されていないかぎり」）。"""
        state = board(active=blastoise(poison=10))
        apply_command(state, rain_dance(state, hand_uids(state, 0, WATER)[0], state.players[0].active))

    def test_target_conditions_do_not_matter(self):
        """R10: つける先の特殊状態は関係しない。つけても特殊状態は変わらない。ベンチのカメックス（特殊状態にならない。p.322）は、バトル場
        のカメックスがねむりでも使える。"""
        for spec in ({"sleep": True}, {"paralysis": TURN - 1}, {"confusion": True}, {"poison": 10}):
            with self.subTest(spec=spec):
                state = board(active={"card": SQUIRTLE, **spec}, bench=(blastoise(),))
                new = apply_command(state, rain_dance(state, hand_uids(state, 0, WATER)[0], state.players[0].active))
                self.assertEqual(new.players[0].active.conditions, state.players[0].active.conditions)
        state = board(active=blastoise(sleep=True), bench=(blastoise(),))
        me = state.players[0]
        new = apply_command(state, rain_dance(state, hand_uids(state, 0, WATER)[0], me.active, user=me.bench[0]))
        self.assertEqual(len(new.players[0].active.energy), 1)


# ---------------------------------------------------------------- 不正な操作と原子性


class RejectionTest(unittest.TestCase):
    def test_cards_that_are_not_a_water_energy_in_own_hand(self):
        """つけるカードは自分の手札の基本エネルギーカードで、「水」を出すもの（R4）。ないカード・相手の手札・山札・トラッシュ・サイド・
        場についたカードは手札にない（``CARD_NOT_IN_HAND``）。同じカードは 2 回つけられない（1 回目で手札から出る）。"""
        state = board(hand=(WATER, FIRE, LIGHTNING, SQUIRTLE, POTION))
        me, them = state.players
        target = me.active
        water = hand_uids(state, 0, WATER)[0]
        attached = apply_command(state, rain_dance(state, water, target))
        cases = [
            (9999, "CARD_NOT_IN_HAND"), (-1, "CARD_NOT_IN_HAND"),
            (them.hand[0], "CARD_NOT_IN_HAND"),  # 相手の手札の水エネルギー
            (me.deck[0], "CARD_NOT_IN_HAND"), (me.prizes[0], "CARD_NOT_IN_HAND"),
            (them.active.card, "CARD_NOT_IN_HAND"),
            (hand_uids(state, 0, FIRE)[0], "WRONG_ENERGY_TYPE"), (hand_uids(state, 0, LIGHTNING)[0], "WRONG_ENERGY_TYPE"),
            (hand_uids(state, 0, SQUIRTLE)[0], "NOT_BASIC_ENERGY"), (hand_uids(state, 0, POTION)[0], "NOT_BASIC_ENERGY"),
        ]
        for energy, code in cases:
            with self.subTest(energy=energy, code=code):
                assert_rejected(self, state, rain_dance(state, energy, target), code)
        # 1 回目でついたカード（場のカード）を、もう一度つけようとする
        assert_rejected(self, attached, rain_dance(attached, water, attached.players[0].bench[0]), "CARD_NOT_IN_HAND")

    def test_targets_that_are_not_own_water_pokemon(self):
        """つける先は自分の場の「水」ポケモン（R5）。水でないポケモン（コラッタ）は ``WRONG_POKEMON_TYPE``、相手の場の水ポケモン（パウワウ）
        は ``TARGET_NOT_YOURS``（p.310「相手の場にいるポケモンに、自分のエネルギーカードをつけることはできません」）、場にいない番号は
        ``TARGET_NOT_IN_PLAY``。"""
        state = board()
        me, them = state.players
        water = hand_uids(state, 0, WATER)[0]
        for target, code in ((me.bench[1].pokemon_id, "WRONG_POKEMON_TYPE"), (them.bench[0].pokemon_id, "TARGET_NOT_YOURS"),
                             (them.active.pokemon_id, "TARGET_NOT_YOURS"), (999, "TARGET_NOT_IN_PLAY"), (0, "TARGET_NOT_IN_PLAY")):
            with self.subTest(target=target):
                assert_rejected(self, state, rain_dance(state, water, target), code)

    def test_choices(self):
        """選ばせるもの: つけるカード（``energy``）とつける先（``target``）が要る（``POWER_CHOICE_MISSING``）。移動元（``source``）は使わない
        （指定したら ``POWER_CHOICE_NOT_USED``。エナジートランスの形と取りちがえない）。型が整数でないものは ``BAD_COMMAND``。"""
        state = board()
        me = state.players[0]
        water = hand_uids(state, 0, WATER)[0]
        user = me.active.pokemon_id
        for command, code in (
            (UsePokemonPower(0, user), "POWER_CHOICE_MISSING"),
            (UsePokemonPower(0, user, 0, water), "POWER_CHOICE_MISSING"),
            (UsePokemonPower(0, user, 0, None, None, user), "POWER_CHOICE_MISSING"),
            (UsePokemonPower(0, user, 0, water, user, me.bench[0].pokemon_id), "POWER_CHOICE_NOT_USED"),
            (UsePokemonPower(0, user, 0, water, me.bench[0].pokemon_id, user), "POWER_CHOICE_NOT_USED"),
            (UsePokemonPower(0, user, 0, True, None, user), "BAD_COMMAND"),
            (UsePokemonPower(0, user, 0, water, None, str(user)), "BAD_COMMAND"),
        ):
            with self.subTest(command=command):
                assert_rejected(self, state, command, code)

    def test_user_and_turn(self):
        """使うのは自分の場のカメックス（相手のカメックスは ``POKEMON_NOT_YOURS``、カメール・コラッタ（パワーなし）・ない位置は
        ``NO_POKEMON_POWER``）。自分の番の ``Phase.MAIN`` だけ（相手の番 ``NOT_YOUR_TURN``・決定を待つ間 ``WRONG_PHASE``・
        対戦準備 ``WRONG_PHASE``）。"""
        state = board(bench=(wartortle(), RATTATA), opponent=blastoise())
        me, them = state.players
        water = hand_uids(state, 0, WATER)[0]
        for command, code in (
            (rain_dance(state, water, me.active, user=them.active), "POKEMON_NOT_YOURS"),
            (rain_dance(state, water, me.active, user=me.bench[0]), "NO_POKEMON_POWER"),  # カメール（パワーなし）
            (rain_dance(state, water, me.active, user=me.bench[1]), "NO_POKEMON_POWER"),
            (UsePokemonPower(0, me.active.pokemon_id, 1, water, None, me.active.pokemon_id), "NO_POKEMON_POWER"),
            (rain_dance(state, water, me.active, user=999), "POKEMON_NOT_IN_PLAY"),
            (rain_dance(state, them.hand[0], them.active, player=1, user=them.active), "NOT_YOUR_TURN"),
        ):
            with self.subTest(command=command):
                assert_rejected(self, state, command, code)
        setup = new_game(FIRE_DECK, WATER_FIGHTING_DECK, 1)
        self.assertIs(setup.phase, Phase.SETUP_PLACEMENT)
        assert_rejected(self, setup, UsePokemonPower(0, 1, 0, setup.players[0].hand[0], None, 1), "WRONG_PHASE")

    def test_not_during_a_decision(self):
        """決定を待つ間（きずぐすりの対象を選ぶ間）は使えない（p.311「ほかのことはできない」。``WRONG_PHASE``）。決定に答えたら使える。"""
        state = board(active=blastoise(damage=20), bench=(SQUIRTLE,), hand=(WATER, POTION))
        state = apply_command(state, PlayTrainer(0, hand_uids(state, 0, POTION)[0]))
        self.assertIs(state.phase, Phase.DECISION)
        me = state.players[0]
        water = hand_uids(state, 0, WATER)[0]
        assert_rejected(self, state, rain_dance(state, water, me.active), "WRONG_PHASE")
        done = apply_command(state, ResolveDecision(0, state.decision.id, (me.active.pokemon_id,)))
        apply_command(done, rain_dance(done, water, done.players[0].active))

    def test_after_an_attack_the_turn_is_over(self):
        """R14: ワザを使ったら番は終わる（p.309）ので、そのあとは使えない（相手の番。``NOT_YOUR_TURN``）。"""
        state = board(bench=(SQUIRTLE,), hand=(WATER,) * 4)
        for water in hand_uids(state, 0, WATER)[:3]:
            state = apply_command(state, rain_dance(state, water, state.players[0].active))
        attacked = apply_command(state, UseAttack(0, 0))  # ハイドロポンプ 40。エビワラー（HP 70）はきぜつしない
        self.assertEqual((attacked.current_player, attacked.phase), (1, Phase.MAIN))
        me = attacked.players[0]
        assert_rejected(self, attacked, rain_dance(attacked, hand_uids(attacked, 0, WATER)[0], me.active, player=0), "NOT_YOUR_TURN")

    def test_rejections_never_use_randomness_or_change_the_counters(self):
        """拒否した使用は乱数を使わず、通常の操作の回数・パワーでつけた枚数を変えない（変異: 不正なコマンドで数が増える、を見つける）。"""
        state = board()
        once = apply_command(state, rain_dance(state, hand_uids(state, 0, WATER)[0], state.players[0].active))
        me = once.players[0]
        for command in (rain_dance(once, hand_uids(once, 0, FIRE)[0], me.active), rain_dance(once, hand_uids(once, 0, WATER)[0], me.bench[1]),
                        UsePokemonPower(0, me.active.pokemon_id)):
            with self.assertRaises(IllegalActionError):
                apply_command(once, command)
            self.assertEqual((once.energy_attachments_this_turn, once.energy_attached_by_powers_this_turn), (0, 1))
            self.assertEqual(rng_fingerprint(once.rng), rng_fingerprint(state.rng))


# ---------------------------------------------------------------- ほかの処理との関係


class InteractionTest(unittest.TestCase):
    def test_attack_cost(self):
        """ワザに必要なエネルギーは、ワザを使うときについているエネルギーで決める（p.320）。あまごいでつけたエネルギーで払える。"""
        state = board(active=blastoise(energy=[WATER, WATER]))
        assert_rejected(self, state, UseAttack(0, 0), "INSUFFICIENT_ENERGY")
        powered = apply_command(state, rain_dance(state, hand_uids(state, 0, WATER)[0], state.players[0].active))
        attacked, events = run(powered, UseAttack(0, 0))
        self.assertEqual([e["amount"] for e in events if e["kind"] == "damage"], [40])

    def test_retreat_cost(self):
        """にげるエネルギー（p.311）は、そのときバトル場のポケモンについているエネルギーから選ぶ。あまごいでつけたエネルギーで払え、
        トラッシュする。"""
        state = board(active=SQUIRTLE, bench=(blastoise(),))
        me = state.players[0]
        assert_rejected(self, state, Retreat(0, (), me.bench[0].card), "WRONG_RETREAT_COST")
        water = hand_uids(state, 0, WATER)[0]
        powered = apply_command(state, rain_dance(state, water, me.active))
        retreated = apply_command(powered, Retreat(0, (water,), me.bench[0].card))
        self.assertIn(water, retreated.players[0].discard)
        self.assertEqual(retreated.players[0].active.pokemon_id, me.bench[0].pokemon_id)
        # バトル場に出たカメックスも使える（R8）
        apply_command(retreated, rain_dance(retreated, hand_uids(retreated, 0, WATER)[0], retreated.players[0].bench[0]))

    def test_attached_energy_is_discarded_with_the_knocked_out_pokemon(self):
        """きぜつしたら、ついているエネルギー（あまごいでつけたものも）はポケモンといっしょにトラッシュ（p.313・p.323）。ここでは
        ポケモンチェックのどく（p.323）できぜつさせる。"""
        state = board(active={"card": SQUIRTLE, "damage": 30, "poison": 10}, bench=(blastoise(),))
        water = hand_uids(state, 0, WATER)[0]
        powered = apply_command(state, rain_dance(state, water, state.players[0].active))
        after = apply_command(powered, EndTurn(0))
        knock = [dict(e) for e in after.log if e["kind"] == "knock_out"]
        self.assertEqual(len(knock), 1)
        self.assertEqual(knock[0]["discarded_energy"], (water,))
        self.assertIn(water, after.players[0].discard)
        self.assertEqual(check_invariants(after), [])

    def test_evolution_keeps_the_energy_and_the_new_blastoise_can_use_it(self):
        """進化してもついているエネルギーはそのまま（p.310）。R15: 進化したその番に、カメックスのあまごいを使える（進化した番に特殊能力を
        使えないという規定はない。p.310・p.311）。進化前のカメール（パワーなし）は使えない（p.310）。"""
        state = board(active=HITMONCHAN, bench=(wartortle(), SQUIRTLE), hand=(BLASTOISE, WARTORTLE, WATER, WATER))
        me = state.players[0]
        w, s = me.bench
        waters = hand_uids(state, 0, WATER)
        assert_rejected(self, state, rain_dance(state, waters[0], s, user=w), "NO_POKEMON_POWER")
        evolved = apply_command(state, EvolvePokemon(0, hand_uids(state, 0, BLASTOISE)[0], w.pokemon_id))
        powered = apply_command(evolved, rain_dance(evolved, waters[0], s, user=w))
        self.assertEqual(powered.players[0].bench[1].energy, [waters[0]])
        # つけたあとで進化させても、エネルギーは同じ uid のまま（ゼニガメ → カメール）
        grown = apply_command(powered, EvolvePokemon(0, hand_uids(powered, 0, WARTORTLE)[0], s.pokemon_id))
        self.assertEqual(grown.players[0].bench[1].energy, [waters[0]])
        self.assertEqual(grown.cards[grown.players[0].bench[1].card].card_id, WARTORTLE)
        apply_command(grown, rain_dance(grown, waters[1], s, user=w))  # 進化したカメールも「水」ポケモン

    def test_switch_keeps_the_energy(self):
        """ポケモンいれかえで入れ替わっても、あまごいでつけたエネルギーはついたまま（p.310「1度つけたエネルギーカードをはがすことは
        できません」）。"""
        state = board(active=SQUIRTLE, bench=(blastoise(),), hand=(WATER, SWITCH))
        me = state.players[0]
        water = hand_uids(state, 0, WATER)[0]
        state = apply_command(state, rain_dance(state, water, me.active))
        state = apply_command(state, PlayTrainer(0, hand_uids(state, 0, SWITCH)[0]))
        if state.phase is Phase.DECISION:
            state = apply_command(state, ResolveDecision(0, state.decision.id, (me.bench[0].pokemon_id,)))
        self.assertEqual(state.players[0].bench[0].energy, [water])
        self.assertEqual(state.players[0].active.pokemon_id, me.bench[0].pokemon_id)

    def test_not_confused_with_energy_trans(self):
        """エナジートランス（場のエネルギーのつけかえ）とあまごい（手札からつける）を取りちがえない: フシギバナのパワーに移動元を省くと
        ``POWER_CHOICE_MISSING``、カメックスのパワーに移動元を書くと ``POWER_CHOICE_NOT_USED``。あまごいは「草」ポケモンのフシギバナに
        つけられず（``WRONG_POKEMON_TYPE``）、エナジートランスは「水」エネルギーを動かせない（``WRONG_ENERGY_TYPE``）。ログも別。"""
        venusaur = {"card": VENUSAUR, "evolved_from": [BULBASAUR, IVYSAUR], "energy": [GRASS]}
        state = board(active=venusaur, bench=(blastoise(energy=[WATER]), SQUIRTLE), hand=(WATER, GRASS))
        me = state.players[0]
        v, b, s = me.active, me.bench[0], me.bench[1]
        water = hand_uids(state, 0, WATER)[0]
        assert_rejected(self, state, UsePokemonPower(0, v.pokemon_id, 0, water, None, s.pokemon_id), "POWER_CHOICE_MISSING")
        assert_rejected(self, state, UsePokemonPower(0, b.pokemon_id, 0, water, b.pokemon_id, s.pokemon_id), "POWER_CHOICE_NOT_USED")
        assert_rejected(self, state, rain_dance(state, water, v, user=b), "WRONG_POKEMON_TYPE")
        assert_rejected(self, state, UsePokemonPower(0, v.pokemon_id, 0, b.energy[0], b.pokemon_id, s.pokemon_id), "WRONG_ENERGY_TYPE")
        _, rain = run(state, rain_dance(state, water, s, user=b))
        _, trans = run(state, UsePokemonPower(0, v.pokemon_id, 0, v.energy[0], v.pokemon_id, s.pokemon_id))
        self.assertEqual((kinds(rain), kinds(trans)), (["pokemon_power", "power_attach_energy"], ["pokemon_power", "move_energy"]))


# ---------------------------------------------------------------- ログ・書き出し・不変条件


class LogSerializationInvariantTest(unittest.TestCase):
    def test_log_has_no_hand_contents(self):
        """ログは宣言と、つけたカード（場に出て公開される）とつける先だけ。手札のほかのカードは書かない（非公開の情報を増やさない）。"""
        state = board()
        _, events = run(state, rain_dance(state, hand_uids(state, 0, WATER)[0], state.players[0].active))
        self.assertEqual(set(events[0]), {"kind", "turn", "player", "pokemon", "pokemon_id", "power", "power_index"})
        self.assertEqual(set(events[1]), {"kind", "turn", "player", "pokemon", "pokemon_id", "power", "energy", "to_pokemon_id"})
        # カードの uid を書く項目は、使うポケモン（場の公開のカード）とつけたカード（つけたら場で公開）だけ
        self.assertEqual({events[1]["pokemon"], events[1]["energy"]}, {state.players[0].active.card, state.players[0].hand[0]})

    def test_format_9(self):
        """形式 9 は形式 8 に ``energy_attached_by_powers_this_turn`` を加えたもの。この数が 0 でなければ形式 1〜8 は ``ValueError``（黙って
        落とさない）。番が変わって 0 になれば、進化したカメックスのいる状態は形式 7・8 でも書き出せる。"""
        state = board()
        powered = apply_command(state, rain_dance(state, hand_uids(state, 0, WATER)[0], state.players[0].active))
        data = full(powered)
        self.assertEqual((data["format_version"], data["energy_attached_by_powers_this_turn"]), (9, 1))
        for version in range(1, 9):
            with self.subTest(format_version=version), self.assertRaises(ValueError):
                state_to_dict(powered, format_version=version)
        self.assertEqual(serialization_problems(powered), [])
        later = apply_command(powered, EndTurn(0))
        self.assertEqual(state_to_dict(later, format_version=9)["energy_attached_by_powers_this_turn"], 0)
        self.assertEqual({**state_to_dict(later, format_version=8), "format_version": 9, "energy_attached_by_powers_this_turn": 0},
                         state_to_dict(later, format_version=9))
        self.assertEqual(serialization_problems(later), [])

    def test_copies(self):
        """使ったあとの状態は、clone・deepcopy・pickle で同じものになり、同じ続きになる。"""
        state = board()
        new = apply_command(state, rain_dance(state, hand_uids(state, 0, WATER)[0], state.players[0].active))
        for copied in (new.clone(), copy.deepcopy(new), pickle.loads(pickle.dumps(new))):
            self.assertEqual(full(copied), full(new))
            again = apply_command(copied, rain_dance(copied, hand_uids(copied, 0, WATER)[0], copied.players[0].bench[0]))
            self.assertEqual((again.energy_attached_by_powers_this_turn, check_invariants(again)), (2, []))
        self.assertEqual(full(new.clone()), full(new))
        self.assertEqual(state.energy_attached_by_powers_this_turn, 0)  # 渡した状態は変わらない

    def test_command_round_trip(self):
        command = UsePokemonPower(0, 5, 0, 12, None, 7)
        data = command_to_dict(command)
        self.assertEqual(data, {"type": "use_pokemon_power", "player": 0, "pokemon": 5, "power": 0, "energy": 12, "source": None, "target": 7})
        self.assertEqual(command_from_dict(data), command)

    def test_invariants_find_a_broken_counter(self):
        """パワーでつけた枚数は、今の番のログの ``power_attach_energy`` の数と同じ（不変条件）。数を書きかえる・ログを消すと見つかる。"""
        state = board()
        powered = apply_command(state, rain_dance(state, hand_uids(state, 0, WATER)[0], state.players[0].active))
        for value in (0, 2, -1, True, "1"):
            broken = powered.clone()
            broken.energy_attached_by_powers_this_turn = value
            with self.subTest(value=value):
                self.assertTrue(check_invariants(broken))
        broken = powered.clone()
        broken.log = tuple(e for e in broken.log if e["kind"] != "power_attach_energy")
        self.assertTrue(check_invariants(broken))
        self.assertEqual(check_invariants(powered), [])

    def test_engine_never_moves_cards_on_an_unchecked_path(self):
        """手札から場へ動かす共通の処理（``zones.attach_energy_from_hand``）は、手札にないカード・相手のカード・相手のポケモンでは動かさない
        （確認の漏れを ``RuntimeError`` で見つける。状態を変える前）。"""
        from kyuura_engine.zones import attach_energy_from_hand
        state = board()
        me, them = state.players
        water = hand_uids(state, 0, WATER)[0]
        for player, energy, pokemon in ((0, me.deck[0], me.active), (0, them.hand[0], me.active), (0, water, them.active),
                                        (1, water, me.active)):
            work = state.clone()
            before = full(work)
            with self.subTest(energy=energy), self.assertRaises(RuntimeError):
                attach_energy_from_hand(work, player, energy, work.players[0].active if pokemon is me.active else work.players[1].active)
            self.assertEqual(full(work), before)


if __name__ == "__main__":
    unittest.main()

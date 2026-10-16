"""ポケモンパワー（特殊能力。v0.5）の基盤: 効果の登録表・カードの分類・コマンドの形・使う前の共通の確認・番が続くこと・原子性。

根拠は『ポケモンカードオフィシャルブック2000』[P43]（kyuura の NEO-2000-OFFICIAL-RULES。kyuura の rule_history.json の
ポケモンパワーの記録は第4版（ed4）のもので、2000.02.14 版の記録はない。docs/pokemon-powers-v0.5.md）。

- p.311「ポケモンの特殊能力を使う」: 自分の場にいるポケモンが持っている特殊能力のうちで、そのとき使うことのできるものの使用を
  宣言できる。手順は 1. 使うポケモンを示し名前を伝えて宣言 → 2. 使うための条件にしたがう（したがえないときは使えない）→
  3. 説明にしたがって処理。特に指示されていないかぎり、エネルギーをつけていなくても・ベンチにいても使える。
  特に指示されていないかぎり、いつでも・何度でも宣言でき、1 回の番の中で複数のポケモンが宣言してもよい。宣言したら、それに
  よって起こることをすべて済ませてからでないと、ほかのことはできない
- p.323「14 ポケモンの特殊能力」: 同じ内容（「特に記述されていないかぎり」）と、使用を宣言して使う特殊能力の例（エナジートランスの
  最新の説明）。常にはたらいている・決められたときに自動的にはたらく特殊能力は宣言しない（v0.5 では未対応）
- p.309: 自分の番の流れ。ワザを使ったら番は終わる（特殊能力の使用では終わらない）。番の最初に引くまでは何もできない
- p.310: 進化したポケモンが、進化前に持っていたワザや特殊能力を使うことはできない

エナジートランスの処理は tests/test_venusaur_v0_5.py。盤面を直接作るテスト（``build_test_state``）は 1 か所の規定を確かめる
ためのもので、自然な対戦の結果ではない（自然な対戦は tests/test_bulbasaur_games_v0_5.py）。
"""

import copy
import pickle
import unittest

from kyuura_engine import (
    AttachEnergy, EndTurn, EvolvePokemon, IllegalActionError, Phase, PlayTrainer, ResolveDecision, Retreat, UnsupportedError, UseAttack,
    UsePokemonPower, apply_command, check_invariants, command_from_dict, command_to_dict, state_to_dict,
)
from kyuura_engine.cards import EnergyType, load_card_pool, pool_from_extract, read_extract, read_verification
from kyuura_engine.deck import deck_problems
from kyuura_engine.effects import (
    DEFAULT_EFFECTS, AttackEffect, AttackKey, EnergyTransfer, PowerEffect, PowerEntry, PowerKey,
)
from kyuura_engine.rng import rng_fingerprint

from tests.helpers import (
    ALAKAZAM, BLASTOISE, BULBASAUR, CHARIZARD, FIRE, GRASS, GROWLITHE, HITMONCHAN, IVYSAUR, POTION, RATTATA, VENUSAUR, build_test_state,
    NO_CHARIZARD_EFFECTS, no_charizard_pool,
    expand_decklist,
)
from tests.log_audit import serialization_problems

ENERGY_TRANS_PRINTED = "フシギバナは自分の場にある「草」エネルギーを好きなだけ移動させることができる。「ねむり・マヒ・こんらん」状態の時には使えない。"
ENERGY_TRANS_LATEST = ("この力は、自分の番の中で何度でも使える。自分の場にいるポケモンについている「草」エネルギーを、自分の場にいる別の"
                       "ポケモンにつけかえる。このカードが「ねむり・マヒ・こんらん」状態のとき、この力は使えない。")
ENERGY_TRANS = PowerKey(VENUSAUR, 0)
RAIN_DANCE = PowerKey(BLASTOISE, 0)  # v0.6 で登録（tests/test_rain_dance_v0_6.py）
DAMAGE_SWAP = PowerKey(ALAKAZAM, 0)  # v0.7 で登録（tests/test_damage_swap_v0_7.py）
CHEMICAL_GAS = PowerKey("PMCG3-007", 0)  # v0.8 で登録（ベトベトンの「かがくへんかガス」。常にはたらく。tests/test_chemical_gas_v0_8.py）
TRANSPARENCY = PowerKey("PMCG3-030", 0)  # v0.9 で登録（ゴーストの「とうめい」。ワザを受けるときに自動的にはたらく。tests/test_transparency_v0_9.py）
STRIKES_BACK = PowerKey("PMCG1-057", 0)  # v0.10 で登録（カイリキーの「はんげき」。ダメージを受けたときに自動的にはたらく。tests/test_counterattack_v0_10.py）
# v0.11 で登録（サカキのカイリキーの「こんじょう」。相手のワザによるダメージできぜつするときに使える。tests/test_guts_v0_11.py）
GUTS = PowerKey("PMCG6-061", 0)
REBIRTH = PowerKey("PMCG5-020", 0)  # v0.12: R団のファイヤーの「ふしちょう」
RESTLESS_SLEEP = PowerKey("PMCG6-073", 0)  # v0.17b: R団のカビゴンの「わるいねぞう」（tests/test_rocket_snorlax_v0_17b.py）
# v0.31（docs/held-cards-v0.31.md）: リザードンの「エナジーバーン」・カツラのロコンの「しぜんになおる」・カツラのキュウコンの「ほのおでかいふく」
ENERGY_BURN = PowerKey("PMCG1-021", 0)
NATURAL_CURE = PowerKey("PMCG6-026", 0)
FIRE_RECOVERY = PowerKey("PMCG6-033", 0)
# 登録表の特殊能力（カード id の順）
# v0.42: ヒーリングかふん・おくびょう・へんなこうどう・のろい・かけつける・ぶっしつこうかん・ぼうぎょかふん・かおりのわな（docs/power-decisions-v0.42.md）
HEALING_POLLEN = PowerKey("PMCG2-014", 0)
COWARDICE = PowerKey("PMCG3-011", 0)
STRANGE_BEHAVIOR = PowerKey("PMCG3-028", 0)
CURSE = PowerKey("PMCG3-031", 0)
STEP_IN = PowerKey("PMCG3-043", 0)
MATTER_EXCHANGE = PowerKey("PMCG4-034", 0)
DEFENSIVE_POLLEN = PowerKey("PMCG5-014", 0)
SWEET_TRAP = PowerKey("PMCG5-015", 0)
# v0.43: くさいかふん・こっそりかみつく・ほのおをもらう・えんかくさいみん・つりあげる・しんかのひかり・てしたをよぶ・ようぶんきゅうしゅう・エナジーチャージ
# （docs/declared-entry-powers-v0.43.md）
POLLEN_STENCH = PowerKey("PMCG4-006", 0)
SNEAK_ATTACK = PowerKey("PMCG4-009", 0)
GATHER_FIRE = PowerKey("PMCG4-012", 0)
LONG_DISTANCE_HYPNOSIS = PowerKey("PMCG4-033", 0)
REEL_IN = PowerKey("PMCG4-036", 0)
EVOLUTIONARY_LIGHT = PowerKey("PMCG4-052", 0)
SUMMON_MINIONS = PowerKey("PMCG4-053", 0)
SOAK_UP = PowerKey("PMCG5-010", 0)
ENERGY_CHARGE = PowerKey("PMCG5-040", 0)
# v0.44: キョウのコクーンの［うか］・サカキのペルシアンの［ボスをよぶ］（docs/search-evolution-once-attacks-v0.44.md）
METAMORPHOSIS = PowerKey("PMCG6-011", 0)
BOSS_CALL = PowerKey("PMCG6-071", 0)
ALL_POWERS = (ENERGY_TRANS, ENERGY_BURN, RAIN_DANCE, DAMAGE_SWAP, STRIKES_BACK, HEALING_POLLEN, CHEMICAL_GAS, COWARDICE, STRANGE_BEHAVIOR,
              TRANSPARENCY, CURSE, STEP_IN, POLLEN_STENCH, SNEAK_ATTACK, GATHER_FIRE, LONG_DISTANCE_HYPNOSIS, MATTER_EXCHANGE, REEL_IN,
              EVOLUTIONARY_LIGHT, SUMMON_MINIONS, SOAK_UP, DEFENSIVE_POLLEN, SWEET_TRAP, REBIRTH, ENERGY_CHARGE, METAMORPHOSIS, NATURAL_CURE,
              FIRE_RECOVERY, GUTS, BOSS_CALL, RESTLESS_SLEEP)


def full(state):
    return state_to_dict(state, format_version=8)


def run(state, command):
    new = apply_command(state, command)
    return new, [dict(e) for e in new.log[len(state.log):]]


def kinds(events):
    return [e["kind"] for e in events]


def uid_of(state, player, card_id, zone="hand"):
    return next(u for u in getattr(state.players[player], zone) if state.cards[u].card_id == card_id)


def assert_rejected(test, state, command, code, error=IllegalActionError):
    """拒否され、渡した状態（場・手札・エネルギー・番・つけた回数）もログも乱数も変わらない。"""
    before, fingerprint, log = full(state), rng_fingerprint(state.rng), state.log
    with test.assertRaises(error) as ctx:
        apply_command(state, command)
    test.assertEqual(ctx.exception.code, code)
    test.assertEqual((full(state), rng_fingerprint(state.rng)), (before, fingerprint))
    test.assertIs(state.log, log)


def venusaur(**extra):
    """フシギダネ → フシギソウ → フシギバナと 2 進化したフシギバナ（盤面を直接作る。1 進化した番は状態に持たない）。"""
    return {"card": VENUSAUR, "evolved_from": [BULBASAUR, IVYSAUR], **extra}


def ivysaur(**extra):
    return {"card": IVYSAUR, "evolved_from": BULBASAUR, **extra}


def board(active=None, *, bench=(), hand=(), discard=(), opponent=None, opponent_bench=(RATTATA,), turn=7, player=0, **kwargs):
    """プレイヤー ``player`` の番 ``turn`` の盤面（先攻はプレイヤー 0）。既定はバトル場に草エネルギー 2 枚のフシギバナ、ベンチに
    草エネルギー 1 枚のフシギダネ。既定の番は 7（2 進化したフシギバナが、今の番より前の番（5）に進化したものとして置ける）。"""
    if active is None:
        active = venusaur(energy=[GRASS, GRASS])
    if not bench:
        bench = [{"card": BULBASAUR, "energy": [GRASS]}]
    mine = {"active": active, "bench": list(bench), "hand": list(hand), "discard": list(discard)}
    theirs = {"active": opponent or GROWLITHE, "bench": list(opponent_bench)}
    specs = [mine, theirs] if player == 0 else [theirs, mine]
    return build_test_state(specs, current_player=player, turn_number=turn, **kwargs)


def transfer(state, energy, source, target, *, player=None, user=None):
    """エナジートランスを 1 回使うコマンド。``source``・``target``・``user`` は場のポケモン（PokemonInPlay）。``user`` の既定は
    自分の場の最初のフシギバナ。"""
    player = state.current_player if player is None else player
    if user is None:
        user = next(pk for pk in state.players[player].in_play() if state.cards[pk.card].card_id == VENUSAUR)
    return UsePokemonPower(player, user.pokemon_id, 0, energy, source.pokemon_id, target.pokemon_id)


def pool_with(records, powers):
    """テスト専用のカード（実在のカードではない）を加えたカードの組と効果の登録表。``records`` は (カード id, もとのカード id,
    記録を変える関数)、``powers`` は PowerKey → PowerEntry。"""
    extract = copy.deepcopy(read_extract())
    for card_id, base, change in records:
        record = copy.deepcopy(next(c for c in extract["cards"] if c["id"] == base))
        record["id"] = card_id
        change(record)
        extract["cards"].append(record)
        extract["pool_v0_5"] = [*extract["pool_v0_5"], card_id]
    effects = DEFAULT_EFFECTS.with_powers("test-powers", powers)
    return pool_from_extract(extract, effects), effects


# ---------------------------------------------------------------- 登録表とカードの分類


class PowerRegistryTest(unittest.TestCase):
    def test_default_registry_registers_only_energy_trans(self):
        """v0.5 で登録したポケモンパワーは、フシギバナの「エナジートランス」だけ（ポケモンパワーを持つカードを一括で対応にしない）。
        v0.6 でカメックスの「あまごい」を、カードのページ（p.90）と照合して加えた（2 つ。tests/test_rain_dance_v0_6.py）。
        v0.7 でフーディンの「ダメージスワップ」を、カードのページ（p.153）と照合して加えた（3 つ。tests/test_damage_swap_v0_7.py）。
        v0.8 でベトベトンの「かがくへんかガス」（常にはたらく）を、カードのページ（p.48）と照合して加えた（4 つ。tests/test_chemical_gas_v0_8.py）。
        v0.9 でゴーストの「とうめい」（自動的にはたらく）を、カードのページ（p.160）と照合して加えた（5 つ。tests/test_transparency_v0_9.py）。
        v0.10 でカイリキーの「はんげき」（ダメージを受けたときに自動的にはたらく）を、カードのページ（p.192）と照合して加えた（6 つ。
        tests/test_counterattack_v0_10.py）。v0.11 でサカキのカイリキーの「こんじょう」（相手のワザによるダメージできぜつするときに使える。
        使うかは持ち主が決める）を、カードのページ（p.193）と照合して加えた（7 つ。tests/test_guts_v0_11.py）。v0.12 で R団のファイヤーの
        「ふしちょう」（このカードが「きぜつ」したとき、使える。使うかは持ち主が決める）を、カードのページ（p.82）と照合して加えた（8 つ。
        tests/test_phoenix_v0_12.py）。"""
        self.assertEqual(DEFAULT_EFFECTS.power_keys(), ALL_POWERS)  # v0.31 でエナジーバーン・しぜんになおる・ほのおでかいふく、v0.42 で 8 つ、v0.43 で 9 つ、v0.44 で 2 つを加えた
        entry = DEFAULT_EFFECTS.power_entry(VENUSAUR, 0)
        self.assertIsInstance(entry, PowerEntry)
        self.assertEqual(entry.effect, EnergyTransfer(energy_type=EnergyType.GRASS))
        self.assertEqual((entry.name_ja, entry.text_ja, entry.play_text_ja, entry.source),
                         ("エナジートランス", ENERGY_TRANS_PRINTED, ENERGY_TRANS_LATEST, "P43 p.16・p.323"))
        self.assertEqual(DEFAULT_EFFECTS.describe()["powers"]["PMCG1-011@power0"],
                         {"implementation": "energy_transfer", "name_ja": "エナジートランス", "source": "P43 p.16・p.323"})
        self.assertIsNone(DEFAULT_EFFECTS.power_entry(VENUSAUR, 1))
        # 登録のないパワーの例: v0.5 ではカメックス（v0.6 で登録した）、v0.6 ではフーディン（v0.7 で登録した）、v0.7〜v0.30 ではリザードン
        # （v0.31 で登録した。登録を除いた登録表 NO_CHARIZARD_EFFECTS で確かめる）
        self.assertIsNone(NO_CHARIZARD_EFFECTS.power_entry(CHARIZARD, 0))
        self.assertIsNotNone(DEFAULT_EFFECTS.power_entry(CHARIZARD, 0))
        # v0.5 は 1、v0.6 は 2、v0.7 は 3、v0.8 は 4、v0.9 は 5、v0.10 は 6、v0.11 は 7、v0.12 は 8、v0.17b は 9、v0.31 は 12、v0.42 は 20、v0.43 は 29、v0.44 は 31
        self.assertIn("31 powers", repr(DEFAULT_EFFECTS))

    def test_power_is_not_an_attack(self):
        """ポケモンパワーはワザ（AttackEffect）の一種ではない。識別子もワザ（AttackKey）とは別で、同じカードの同じ位置のワザ
        （ソーラービーム）とは別の登録になる。"""
        self.assertFalse(issubclass(EnergyTransfer, AttackEffect))
        self.assertTrue(issubclass(EnergyTransfer, PowerEffect))
        self.assertNotEqual(ENERGY_TRANS, AttackKey(VENUSAUR, 0))
        self.assertEqual((str(ENERGY_TRANS), str(AttackKey(VENUSAUR, 0))), ("PMCG1-011@power0", "PMCG1-011#0"))
        self.assertNotIn(ENERGY_TRANS, DEFAULT_EFFECTS.attack_keys())
        self.assertEqual(DEFAULT_EFFECTS.attack_entry(VENUSAUR, 0).name_ja, "ソーラービーム")

    def test_venusaur_is_supported_only_with_both_registrations(self):
        """フシギバナは、ポケモンパワーとワザの両方が登録されていて、データと合うときだけ使える。"""
        pool = load_card_pool()
        d = pool.get(VENUSAUR)
        self.assertTrue(d.supported and pool.is_playable(VENUSAUR))
        self.assertEqual([(w.index, w.name_ja, w.kind, w.text_ja, w.supported) for w in d.powers],
                         [(0, "エナジートランス", "pokemon_power", ENERGY_TRANS_PRINTED, True)])
        deck = expand_decklist({BULBASAUR: 4, IVYSAUR: 4, VENUSAUR: 4, GRASS: 48})
        self.assertEqual(deck_problems(deck, pool), [])
        for name, effects, reason in (
            ("パワーの登録がない", DEFAULT_EFFECTS.without_powers("test-no-power", [ENERGY_TRANS]), "ポケモンパワー「エナジートランス」"),
            ("ワザの登録がない", DEFAULT_EFFECTS.without_attacks("test-no-solarbeam", [AttackKey(VENUSAUR, 0)]), "ソーラービーム"),
        ):
            with self.subTest(name=name):
                unregistered = pool_from_extract(read_extract(), effects)
                self.assertFalse(unregistered.is_playable(VENUSAUR))
                self.assertIn(reason, " ".join(unregistered.get(VENUSAUR).unsupported_reasons))
                self.assertTrue(any("UNSUPPORTED_CARD" in p and VENUSAUR in p for p in deck_problems(deck, unregistered)))
                self.assertTrue(unregistered.is_playable(BULBASAUR) and unregistered.is_playable(IVYSAUR))

    def test_unregistered_power_of_another_card_stays_unsupported(self):
        """登録のないポケモンパワーを持つカードは使えない。名前や説明文の有無では決めない。v0.5 ではカメックスの「あまごい」で
        確かめていた。v0.6 であまごいを登録したので、フーディン（PMCG1-049）の「ダメージスワップ」で確かめていた。v0.7 でダメージ
        スワップを登録したので、リザードン（PMCG1-021。参照カード）の「エナジーバーン」で確かめていた。v0.31 でエナジーバーンを登録したので、
        その登録を除いた登録表（tests/helpers.py の NO_CHARIZARD_EFFECTS）で確かめる。"""
        pool = no_charizard_pool()
        self.assertTrue(load_card_pool().is_playable(CHARIZARD))
        d = pool.get(CHARIZARD)
        self.assertFalse(pool.is_playable(CHARIZARD))
        self.assertEqual([(w.name_ja, w.supported, w.unsupported_reason) for w in d.powers],
                         [("エナジーバーン", False, "ポケモンパワーの効果の実装が登録されていない")])
        # エナジートランス・あまごい・ダメージスワップの登録をリザードンの位置に写しても、名前が違うので使えない（データとの照合）
        for source in (ENERGY_TRANS, RAIN_DANCE, DAMAGE_SWAP):
            entry = DEFAULT_EFFECTS.power_entry(source.card_id, source.power_index)
            effects = NO_CHARIZARD_EFFECTS.with_powers("test-copied", {PowerKey(CHARIZARD, 0): entry})
            copied = pool_from_extract(read_extract(), effects)
            self.assertFalse(copied.get(CHARIZARD).powers[0].supported)
            self.assertIn("名前", copied.get(CHARIZARD).powers[0].unsupported_reason)

    def test_text_mismatch_makes_the_power_unsupported(self):
        """登録したときに照合した文面とデータの文面が違えば（データが変わったら）、使えない。"""
        entry = DEFAULT_EFFECTS.power_entry(VENUSAUR, 0)
        for name, changed in (
            ("文面", PowerEntry(entry.effect, entry.name_ja, entry.text_ja + "。", entry.play_text_ja, entry.source)),
            ("名前", PowerEntry(entry.effect, "エナジートランス2", entry.text_ja, entry.play_text_ja, entry.source)),
        ):
            with self.subTest(name=name):
                effects = DEFAULT_EFFECTS.with_powers("test-changed", {ENERGY_TRANS: changed})
                pool = pool_from_extract(read_extract(), effects)
                self.assertFalse(pool.is_playable(VENUSAUR))
                self.assertIsNone(effects.power_effect(VENUSAUR, pool.get(VENUSAUR).powers[0]))

    def test_power_kind_is_checked(self):
        """使用を宣言するポケモンパワー（kind ``pokemon_power``）でないデータには、エナジートランスの実装は使えない。"""
        def change(record):
            record["pokemon"]["powers"][0]["kind"] = "poke_body"

        pool, _ = pool_with([("TEST-VENUSAUR-OTHER-KIND", VENUSAUR, change)],
                                 {PowerKey("TEST-VENUSAUR-OTHER-KIND", 0): DEFAULT_EFFECTS.power_entry(VENUSAUR, 0)})
        power = pool.get("TEST-VENUSAUR-OTHER-KIND").powers[0]
        self.assertFalse(power.supported)
        self.assertIn("poke_body", power.unsupported_reason)

    def test_registration_follows_the_verified_latest_description(self):
        """p.16 の「特殊能力」欄・p.323 の例の最新の説明（画像で照合）と、印刷の文面（kyuura の写し・図版）が、照合の記録と同じ。"""
        from scripts import check_card_sources as card_sources

        verification = read_verification()
        sources = card_sources.load_sources()
        record = verification["cards"][VENUSAUR]
        self.assertEqual((record["page"], record["pdf_page"], record["rules_page"], record["status"]), (16, 18, 323, "不一致あり"))
        for key in DEFAULT_EFFECTS.power_keys():
            entry = DEFAULT_EFFECTS.power_entry(key.card_id, key.power_index)
            # 2026-10-15 からの方針（docs/card-data-policy.md）で kyuura データの採用の記録によって登録したパワーは、ガイドブックの照合の記録を
            # 求めない（採用の記録の play_text との対応は scripts/check_card_sources.py が確かめる）。登録の根拠の記録はどちらか一方だけ
            basis = card_sources.registration_basis(key.card_id, verification, sources)
            self.assertIn(basis, (card_sources.GUIDEBOOK_RECORD, card_sources.KYUURA_DATA), key)
            if basis == card_sources.KYUURA_DATA:
                self.assertIn(f"power/{key.power_index}", sources["cards"][key.card_id]["play_text"], key)
                continue
            card_record = verification["cards"][key.card_id]
            self.assertEqual(entry.play_text_ja, card_record["power_latest_description_ja"][str(key.power_index)])
            image = card_record["power_card_image_text_ja"][str(key.power_index)]
            if image != entry.text_ja:
                # v0.8: 図版の印刷の文面が kyuura の写しと違うと読めた（ベトベトンの「すべて／全て」）ときは、照合の記録の不一致
                # （mismatches）に、kyuura の写しの値と図版の読みが書いてある（登録の照合は kyuura の写しの値のまま）
                recorded = [m for m in card_record.get("mismatches", ()) if m["field"] == f"pokemon.powers[{key.power_index}].text.ja"]
                self.assertEqual(len(recorded), 1, key)
                self.assertEqual(recorded[0]["kyuura"], entry.text_ja, key)
                self.assertIn(image, recorded[0]["official_book_2000"], key)
            self.assertEqual(entry.text_ja, load_card_pool().get(key.card_id).powers[key.power_index].text_ja)

    def test_registry_methods_keep_the_other_registrations(self):
        """ワザ・トレーナーの登録を変えた新しい登録表も、ポケモンパワーの登録を引き継ぐ（元の登録表は変えない）。"""
        for registry in (
            DEFAULT_EFFECTS.with_attacks("a", {}), DEFAULT_EFFECTS.without_attacks("b", []), DEFAULT_EFFECTS.with_trainers("c", {}),
            DEFAULT_EFFECTS.without_trainers("d", []),
        ):
            # v0.5 は (ENERGY_TRANS,)、v0.6 は 2 つ、v0.7 は 3 つ、v0.8 は 4 つ、v0.9 は 5 つ、v0.10 は 6 つ、v0.11 は 7 つ、v0.12 は 8 つ、v0.17b は 9 つ、
            # v0.31 は 12
            self.assertEqual(registry.power_keys(), ALL_POWERS)
        removed = DEFAULT_EFFECTS.without_powers("e", ALL_POWERS)
        self.assertEqual((removed.power_keys(), removed.attack_keys(), removed.trainer_ids()),
                         ((), DEFAULT_EFFECTS.attack_keys(), DEFAULT_EFFECTS.trainer_ids()))
        self.assertEqual(DEFAULT_EFFECTS.without_powers("f", [ENERGY_TRANS]).power_keys(), ALL_POWERS[1:])
        # 元の登録表は変わらない
        self.assertEqual(DEFAULT_EFFECTS.power_keys(), ALL_POWERS)


# ---------------------------------------------------------------- コマンドの形


class CommandFormTest(unittest.TestCase):
    def test_v0_4e_two_field_form_is_still_read(self):
        """v0.4e までの 2 つの項目（player・pokemon）だけの辞書も読める（ほかの項目は既定の値）。"""
        command = command_from_dict({"type": "use_pokemon_power", "player": 0, "pokemon": 3})
        self.assertEqual(command, UsePokemonPower(0, 3))
        self.assertEqual((command.power, command.energy, command.source, command.target), (0, None, None, None))

    def test_round_trip(self):
        command = UsePokemonPower(1, 4, 0, 17, 2, 4)
        data = command_to_dict(command)
        self.assertEqual(data, {"type": "use_pokemon_power", "player": 1, "pokemon": 4, "power": 0, "energy": 17, "source": 2, "target": 4})
        self.assertEqual(command_from_dict(data), command)

    def test_bad_values_are_rejected_before_anything_else(self):
        """項目の値は整数（選ばせるものは整数か None）。bool・文字列・余分な項目は、状態を見る前に BAD_COMMAND。"""
        state = board()
        for command in (UsePokemonPower(0, True), UsePokemonPower(0, 1, "0"), UsePokemonPower(0, 1, 0, True, 1, 2),
                        UsePokemonPower(0, 1, 0, 3, None, 2.0), UsePokemonPower(None, 1)):
            with self.subTest(command=command):
                assert_rejected(self, state, command, "BAD_COMMAND")
        for data in ({"type": "use_pokemon_power", "player": 0},
                     {"type": "use_pokemon_power", "player": 0, "pokemon": 1, "energy_uid": 3}):
            with self.subTest(data=data), self.assertRaises(IllegalActionError) as ctx:
                command_from_dict(data)
            self.assertEqual(ctx.exception.code, "BAD_COMMAND")


# ---------------------------------------------------------------- 使う前の共通の確認（p.311）


class CommonChecksTest(unittest.TestCase):
    def test_rejections_change_nothing(self):
        """不正な使用は、状態・乱数・ログを変えない。確かめる順番: プレイヤー・段階・番 → 使うポケモン → 特殊能力の有無・登録 →
        パワーごとの条件（tests/test_venusaur_v0_5.py）。"""
        state = board(opponent=venusaur(energy=[GRASS]), opponent_bench=[{"card": BULBASAUR, "energy": [GRASS]}], turn=7)
        me, opponent = state.players
        v, b = me.active, me.bench[0]
        energy = v.energy[0]
        cases = [
            (UsePokemonPower(2, v.pokemon_id, 0, energy, v.pokemon_id, b.pokemon_id), "INVALID_PLAYER"),
            (UsePokemonPower(-1, v.pokemon_id), "INVALID_PLAYER"),
            # 相手の番ではない（相手は自分のフシギバナでも使えない）
            (UsePokemonPower(1, opponent.active.pokemon_id, 0, opponent.active.energy[0], opponent.active.pokemon_id,
                             opponent.bench[0].pokemon_id), "NOT_YOUR_TURN"),
            (UsePokemonPower(0, 999), "POKEMON_NOT_IN_PLAY"),
            (UsePokemonPower(0, 0), "POKEMON_NOT_IN_PLAY"),
            (UsePokemonPower(0, -3), "POKEMON_NOT_IN_PLAY"),
            # 相手の場のフシギバナの特殊能力は使えない
            (UsePokemonPower(0, opponent.active.pokemon_id, 0, opponent.active.energy[0], opponent.active.pokemon_id,
                             opponent.bench[0].pokemon_id), "POKEMON_NOT_YOURS"),
            # 特殊能力のないポケモン（フシギダネ）・ない位置
            (UsePokemonPower(0, b.pokemon_id, 0, energy, v.pokemon_id, b.pokemon_id), "NO_POKEMON_POWER"),
            (UsePokemonPower(0, v.pokemon_id, 1, energy, v.pokemon_id, b.pokemon_id), "NO_POKEMON_POWER"),
            (UsePokemonPower(0, v.pokemon_id, -1, energy, v.pokemon_id, b.pokemon_id), "NO_POKEMON_POWER"),
        ]
        for command, code in cases:
            with self.subTest(command=command, code=code):
                assert_rejected(self, state, command, code)

    def test_unregistered_power_is_unsupported(self):
        """実装を登録していない特殊能力は、効果がないものとして処理しない（``UNSUPPORTED_POKEMON_POWER``。状態は変えない）。"""
        effects = DEFAULT_EFFECTS.without_powers("test-no-energy-trans", [ENERGY_TRANS])
        state = board(effects=effects, pool=pool_from_extract(read_extract(), effects))
        me = state.players[0]
        assert_rejected(self, state, transfer(state, me.active.energy[0], me.active, me.bench[0]), "UNSUPPORTED_POKEMON_POWER",
                        UnsupportedError)

    def test_not_during_a_decision(self):
        """決定を待つ間（きずぐすりの対象を選ぶ間）は、特殊能力の使用を宣言できない（p.311「ほかのことはできない」。WRONG_PHASE）。"""
        state = board(active=venusaur(energy=[GRASS, GRASS], damage=20), hand=[POTION])
        state = apply_command(state, PlayTrainer(0, uid_of(state, 0, POTION)))
        self.assertIs(state.phase, Phase.DECISION)
        me = state.players[0]
        assert_rejected(self, state, transfer(state, me.active.energy[0], me.active, me.bench[0]), "WRONG_PHASE")
        done = apply_command(state, ResolveDecision(0, state.decision.id, (me.active.pokemon_id,)))
        self.assertIs(done.phase, Phase.MAIN)
        apply_command(done, transfer(done, me.active.energy[0], done.players[0].active, done.players[0].bench[0]))

    def test_after_an_attack_the_turn_is_over(self):
        """ワザを使ったら番は終わる（p.309）ので、そのあとは特殊能力を使えない（相手の番。NOT_YOUR_TURN）。"""
        state = board(active=venusaur(energy=[GRASS] * 4), opponent=HITMONCHAN)  # HP 70。ソーラービーム 60 ではきぜつしない
        me = state.players[0]
        attacked = apply_command(state, UseAttack(0, 0))
        self.assertEqual(attacked.current_player, 1)
        assert_rejected(self, attacked, transfer(attacked, me.active.energy[0], attacked.players[0].active, attacked.players[0].bench[0],
                                                 player=0), "NOT_YOUR_TURN")

    def test_pre_evolution_power_cannot_be_used(self):
        """どの特殊能力があるかは、いちばん上のカードで決める。進化したら、進化前に持っていた特殊能力は使えない（p.310）。

        テスト専用のカード（フシギダネの記録に、エナジートランスの記録を写したもの。実在のカードではない）で確かめる。"""
        def change(record):
            record["pokemon"]["powers"] = copy.deepcopy(
                next(c for c in read_extract()["cards"] if c["id"] == VENUSAUR)["pokemon"]["powers"])

        pool, effects = pool_with([("TEST-BULBASAUR-WITH-POWER", BULBASAUR, change)],
                                       {PowerKey("TEST-BULBASAUR-WITH-POWER", 0): DEFAULT_EFFECTS.power_entry(VENUSAUR, 0)})
        state = board(active={"card": "TEST-BULBASAUR-WITH-POWER", "energy": [GRASS, GRASS]}, hand=[IVYSAUR], pool=pool, effects=effects)
        me = state.players[0]
        user = me.active
        command = UsePokemonPower(0, user.pokemon_id, 0, user.energy[0], user.pokemon_id, me.bench[0].pokemon_id)
        apply_command(state, command)  # 進化する前は、いちばん上のカードの特殊能力として使える
        evolved = apply_command(state, EvolvePokemon(0, uid_of(state, 0, IVYSAUR), user.pokemon_id))
        self.assertEqual(evolved.players[0].active.pokemon_id, user.pokemon_id)  # 場のポケモンの番号は進化しても同じ
        assert_rejected(self, evolved, command, "NO_POKEMON_POWER")


# ---------------------------------------------------------------- 番は続く・回数を数えない


class TurnContinuesTest(unittest.TestCase):
    def test_using_a_power_does_not_end_the_turn(self):
        """特殊能力を使っても番は終わらない（段階・番のプレイヤー・番の番号はそのまま。番の終わり・ポケモンチェックのログもない）。
        そのあと、エネルギーをつける・トレーナー・にげる・ワザ・番を終えることができる。"""
        state = board(active=venusaur(energy=[GRASS] * 4, damage=20), hand=[GRASS, POTION], opponent=HITMONCHAN)
        me = state.players[0]
        new, events = run(state, transfer(state, me.bench[0].energy[0], me.bench[0], me.active))
        self.assertEqual((new.phase, new.current_player, new.turn_number, new.decision), (Phase.MAIN, 0, state.turn_number, None))
        self.assertEqual(kinds(events), ["pokemon_power", "move_energy"])
        p = new.players[0]
        # エネルギーをつける（手札からつけた回数はまだ 0）・トレーナー・にげる・ワザ・番を終える
        attached = apply_command(new, AttachEnergy(0, uid_of(new, 0, GRASS), p.bench[0].card))
        self.assertEqual(attached.energy_attachments_this_turn, 1)
        potion = apply_command(new, PlayTrainer(0, uid_of(new, 0, POTION)))
        self.assertIs(potion.phase, Phase.DECISION)
        retreated = apply_command(new, Retreat(0, tuple(p.active.energy[:2]), p.bench[0].card))
        self.assertEqual(retreated.players[0].active.pokemon_id, p.bench[0].pokemon_id)
        attacked = apply_command(new, UseAttack(0, 0))  # ソーラービーム（草 4）。ワザを使ったら番は終わる
        self.assertEqual((attacked.current_player, attacked.turn_number), (1, state.turn_number + 1))
        ended = apply_command(new, EndTurn(0))
        self.assertEqual(ended.current_player, 1)

    def test_powers_are_not_counted(self):
        """「何度でも使える」（p.16・p.323）ので、使った回数を状態に持たず、何回でも受け付ける（同じポケモンで続けて使える）。"""
        state = board(active=venusaur(energy=[GRASS] * 3), bench=[{"card": BULBASAUR, "energy": [GRASS]}, ivysaur()])
        for _ in range(8):
            me = state.players[0]
            source = max(me.in_play(), key=lambda pk: len(pk.energy))
            target = min(me.in_play(), key=lambda pk: len(pk.energy))
            state = apply_command(state, transfer(state, source.energy[0], source, target))
        self.assertEqual(sum(e["kind"] == "move_energy" for e in state.log), 8)
        self.assertEqual(sorted(len(pk.energy) for pk in state.players[0].in_play()), [1, 1, 2])
        self.assertEqual(state.energy_attachments_this_turn, 0)


# ---------------------------------------------------------------- 原子性・複製・書き出し


class AtomicityTest(unittest.TestCase):
    def test_apply_command_does_not_change_the_given_state(self):
        state = board()
        me = state.players[0]
        before, fingerprint = full(state), rng_fingerprint(state.rng)
        new = apply_command(state, transfer(state, me.active.energy[0], me.active, me.bench[0]))
        self.assertEqual((full(state), rng_fingerprint(state.rng)), (before, fingerprint))
        self.assertNotEqual(full(new), before)
        self.assertEqual(check_invariants(new), [])

    def test_copies_and_serialization(self):
        """使ったあとの状態は、clone・deepcopy・pickle で同じものになり、形式 1〜8 の書き出しの監査に通る（v0.5 では形式 9 はなかった）。

        v0.6 で形式 9（ポケモンパワーで手札からつけた枚数 ``energy_attached_by_powers_this_turn``）を加えた。エナジートランスは手札から
        つけないので、その数は 0 のまま（形式 7・8 で書き出せる）。形式 9 は、形式 8 にその項目（0）を加えたもの。"""
        state = board()
        me = state.players[0]
        new = apply_command(state, transfer(state, me.active.energy[0], me.active, me.bench[0]))
        for copied in (new.clone(), copy.deepcopy(new), pickle.loads(pickle.dumps(new))):
            self.assertEqual(full(copied), full(new))
            again = apply_command(copied, transfer(copied, copied.players[0].active.energy[0], copied.players[0].active,
                                                   copied.players[0].bench[0]))
            self.assertEqual(check_invariants(again), [])
        self.assertEqual(serialization_problems(new), [])
        self.assertEqual(new.energy_attached_by_powers_this_turn, 0)
        self.assertEqual(state_to_dict(new, format_version=9), {**full(new), "format_version": 9, "energy_attached_by_powers_this_turn": 0})
        with self.assertRaises(ValueError):
            state_to_dict(new, format_version=12)  # v0.5 では 10 がなかった。10 は v0.31（1 番に 1 回の特殊能力の使用・エナジーバーン）、11 は v0.44

    def test_invalid_powers_never_use_randomness(self):
        """拒否した使用は乱数を使わない（変異: 不正なコマンドで乱数が進む、を見つける）。受け付けた使用も乱数を使わない。"""
        state = board(hand=[FIRE], active=venusaur(energy=[GRASS, FIRE]))
        me = state.players[0]
        fire = me.active.energy[1]
        fingerprint = rng_fingerprint(state.rng)
        for command in (transfer(state, fire, me.active, me.bench[0]), UsePokemonPower(0, me.active.pokemon_id),
                        UsePokemonPower(0, me.bench[0].pokemon_id)):
            with self.assertRaises(IllegalActionError):
                apply_command(state, command)
            self.assertEqual(rng_fingerprint(state.rng), fingerprint)
        new = apply_command(state, transfer(state, me.active.energy[0], me.active, me.bench[0]))
        self.assertEqual(rng_fingerprint(new.rng), fingerprint)


if __name__ == "__main__":
    unittest.main()

"""v0.89（docs/selected-target-damage-v0.89.md）: 対象を選ぶダメージ・選べる回復のポケモン 17 枚（ワザ 26）と、選んだ個体を明示的に引き継ぐ共通の処理。

根拠は kyuura データの採用（kyuura ``7d3f4ca`` の data/cards.json の日本語の印刷の文面）と、既存の規定の記録（GR-2000-P309-ATTACK-PROCEDURE・GR-2000-P320-RECOVERY・
GR-2000-P321-DAMAGE-ORDER・UQ-BENCH-DAMAGE-WEAKNESS-RESISTANCE（JS1）など。docs 各章）。公式ガイドブックの新しい読み直し・カードの画像・pcg-search.com との照合はしていない。
盤面は ``build_test_state`` で作った 1 か所の規定を確かめるためのもので、``new_game`` からの自然な対戦の結果ではない（対戦は tools/existing_effect_games.py の ``--batch v0.89``）。
"""

from __future__ import annotations

import copy
import dataclasses
import json
import pathlib
import pickle
import unittest

from kyuura_engine import (
    DEFAULT_EFFECTS,
    AttackKey,
    EndTurn,
    ResolveDecision,
    UseAttack,
)
from kyuura_engine import effects as E
from kyuura_engine.cards import (
    EnergyType,
    load_card_pool,
    pool_from_extract,
    read_extract,
)
from kyuura_engine.coins import CoinSide
from kyuura_engine.errors import IllegalActionError, UnsupportedError
from kyuura_engine.observation import observe
from kyuura_engine.resolution import programs
from kyuura_engine.serialize import state_to_dict
from tests import helpers as H
from tests.helpers import apply_kernel, with_coin_results
from tests.test_entry_powers_energy_lifecycle_v0_85 import meganium, stage1
from tests.test_neo_trainer_components_v0_80 import (
    audited,
    mon,
    new_events,
    rejects,
    snapshot,
)
from tests.test_shining_gentle_v0_83 import answer, board, play

ROOT = pathlib.Path(__file__).resolve().parent.parent
DOC = ROOT / "docs" / "selected-target-damage-v0.89.md"
HD, TL = CoinSide.HEADS, CoinSide.TAILS
TURN = 7
W, G, L, P, F, FT = H.WATER, H.GRASS, H.LIGHTNING, H.PSYCHIC, H.FIRE, H.FIGHTING
DARK, DCE, RAINBOW = H.DARKNESS_ENERGY_NEO1, H.DOUBLE_COLORLESS_ENERGY, H.RAINBOW_ENERGY
FA1 = "UNRESOLVED_IGNORED_EFFECTS_SCOPE"
JS1 = "UNRESOLVED_BENCH_DAMAGE_WEAKNESS_RESISTANCE"
PREVENTED = "UNRESOLVED_PREVENTED_COIN_DAMAGE"
T19B = "UNRESOLVED_EVADED_EFFECT_COIN"
RB1 = "UNRESOLVED_RAINBOW_ENERGY_TYPE"
MEC1 = "UNRESOLVED_MIRACLE_ENERGY_AS_TYPE"
V089_ATTACKS = [AttackKey(c, i) for c in H.V0_89_POKEMON for i in range(len(load_card_pool().definitions[c].attacks))]


def umbreon(energy=(DARK, DARK, W), **extra):
    return stage1(H.UMBREON_NEO2, energy, base=H.EEVEE, **extra)


def omanyte(energy=(W, W, W), **extra):
    return stage1(H.DARK_OMANYTE, energy, base=H.MYSTERIOUS_FOSSIL, **extra)


def damages(before, after):
    """ダメージのログの (受けるものの種類, 受けたポケモンの番号（相手の対戦ポケモンは None）, 量)。"""
    return [(e.get("target", "opponent_active"), e.get("pokemon_id"), e["amount"]) for e in new_events(before, after, "damage")]


def declare(state, index, *coins, player=0):
    """ワザを宣言する（``coins`` はそのあとに投げるコインの結果。``with_coin_results``）。"""
    return apply_kernel(with_coin_results(state, *coins) if coins else state, UseAttack(player, index))


def pid(state, player, card_id):
    return next(p.pokemon_id for p in state.players[player].in_play() if state.cards[p.card].card_id == card_id)


def opponent_ids(state):
    return [p.pokemon_id for p in state.players[1].in_play()]


# ---------------------------------------------------------------- 1 章・2 章: 登録・写し・記録


class RegistrationTest(unittest.TestCase):
    """17 枚のどのワザ（26）も登録し、写しの名前・文面と照らす。v0.89 の登録を除くと、ちょうど 17 枚が未対応にもどる（ほかのカードは失われない）。"""

    def test_every_attack_is_registered(self):
        pool = load_card_pool()
        self.assertEqual(tuple(read_extract()["pool_v0_89"]), H.V0_89_CARDS)
        self.assertEqual(len(V089_ATTACKS), 26)
        for key in V089_ATTACKS:
            with self.subTest(key=key):
                entry = DEFAULT_EFFECTS.attack_entry(key.card_id, key.attack_index)
                attack = pool.definitions[key.card_id].attacks[key.attack_index]
                self.assertEqual((entry.name_ja, entry.text_ja), (attack.name_ja, attack.text_ja))
                self.assertEqual(entry.effect.check(attack), [])
                self.assertEqual(entry.play_text_ja, attack.text_ja)  # 処理に使う文面は kyuura の印刷の文面（LD-・エラッタはない）
        for card in H.V0_89_CARDS:
            self.assertIn(card, pool.playable_ids)
            self.assertEqual(pool.definitions[card].powers, ())  # 特殊能力の追加はない

    def test_unregistered_without_the_v0_89_entries(self):
        registry = DEFAULT_EFFECTS.without_attacks(DEFAULT_EFFECTS.id, V089_ATTACKS)
        before = pool_from_extract(read_extract(), registry)
        self.assertEqual(before.playable_ids, load_card_pool().playable_ids - set(H.V0_89_CARDS))

    def test_same_data_cards_share_registrations(self):
        """同じゲーム用データの 3 組だけをまとめる。名前だけが同じ別の版（第1弾のライチュウ・レアコイル・サンダー）とはまとめない。"""
        self.assertEqual(dict(E.SAME_DATA_CARDS_V0_89), {H.RAICHU_QSG: H.RAICHU_ES2, H.MAGNETON_QSG: H.MAGNETON_ES2, H.ZAPDOS_QSG: H.ZAPDOS_ES2})
        for copy_id, original in E.SAME_DATA_CARDS_V0_89.items():
            for index in range(len(load_card_pool().definitions[original].attacks)):
                self.assertIs(DEFAULT_EFFECTS.attack_entry(copy_id, index), DEFAULT_EFFECTS.attack_entry(original, index))
        for other, mine in ((H.RAICHU, H.RAICHU_ES2), (H.MAGNETON, H.MAGNETON_ES2), (H.ZAPDOS, H.ZAPDOS_ES2)):
            self.assertIsNot(DEFAULT_EFFECTS.attack_entry(other, 0), DEFAULT_EFFECTS.attack_entry(mine, 0))
        self.assertIsNot(DEFAULT_EFFECTS.attack_entry(H.ZAPDOS_PR1, 0), DEFAULT_EFFECTS.attack_entry(H.ZAPDOS_ES2, 0))

    def test_evolution_bases_are_names_and_stages(self):
        pool = load_card_pool()
        bases = {H.UMBREON_NEO2: "イーブイ", H.DARK_OMANYTE: "なにかの化石", H.MISTYS_SEAKING_GD2: "カスミのトサキント", H.RAICHU_ES2: "ピカチュウ",
                 H.MAGNETON_ES2: "コイル", H.EXEGGUTOR_SI: "タマタマ", H.MACHOKE_ES3: "ワンリキー"}
        names = {pool.get(c).name_ja for c in pool.playable_ids}
        for card, base in bases.items():
            self.assertEqual((pool.get(card).stage, pool.get(card).evolves_from), ("stage1", base))
            self.assertIn(base, names)

    def test_dark_omanyte_evolves_from_the_mysterious_fossil(self):
        """なにかの化石（v0.47。場では HP 10 のポケモンとしてあつかうトレーナー）から、名前と段階でわるいオムナイトに進化できる（化石の進化の例外を変えていない）。"""
        from kyuura_engine import EvolvePokemon, PlayTrainer

        state = board(mon(H.CHANSEY), hand=(H.MYSTERIOUS_FOSSIL, H.DARK_OMANYTE), opponent=mon(H.CHANSEY))
        fossil = next(u for u in state.players[0].hand if state.cards[u].card_id == H.MYSTERIOUS_FOSSIL)
        placed = apply_kernel(apply_kernel(state, PlayTrainer(0, fossil)), EndTurn(0))
        placed = apply_kernel(placed, EndTurn(1))
        target = next(p for p in placed.players[0].bench if placed.cards[p.card].card_id == H.MYSTERIOUS_FOSSIL)
        card = next(u for u in placed.players[0].hand if placed.cards[u].card_id == H.DARK_OMANYTE)
        evolved = apply_kernel(placed, EvolvePokemon(0, card, target.pokemon_id))
        self.assertEqual(evolved.cards[evolved.find_pokemon(target.pokemon_id)[1].card].card_id, H.DARK_OMANYTE)
        audited(self, evolved)

    def test_sources_and_research_links(self):
        data = ROOT / "kyuura_engine" / "data"
        sources = json.loads((data / "card_sources.json").read_text(encoding="utf-8"))["cards"]
        links = json.loads((data / "research_links.json").read_text(encoding="utf-8"))
        adopted = set(links["latest_descriptions"]["adopted_printed_text"])
        verification = json.loads((data / "card_verification.json").read_text(encoding="utf-8"))
        pool = load_card_pool()
        for card in H.V0_89_CARDS:
            record = sources[card]
            # v0.123: 研究の基準を 74b3ceb に上げて、ナッシー SI-013 に UQ-BILINGUAL-NAME-GLOSS の事例が加わった（tests/helpers.py の V0_123_KYUURA_RECORDS_ADDED）
            self.assertEqual((record["basis"], record["status"], record["external_checks"], record["kyuura_records"], record["kyuura_commit"]),
                             ("kyuura_data", "adopted", [], list(H.V0_123_KYUURA_RECORDS_ADDED.get(card, ())), "7d3f4ca76c084774efb4ac6a1d3a943387e183c3"))
            self.assertNotIn(card, verification.get("cards", verification))
            for index, attack in enumerate(pool.get(card).attacks):
                key = f"attack/{index}"
                self.assertEqual(record["play_text"].get(key), "kyuura_printed_text" if attack.text_ja is not None else None)
                self.assertEqual(f"{card}/{key}" in adopted, attack.text_ja is not None)
        stop = links["stop_codes"][FA1]
        self.assertEqual((stop["kyuura_disposition"], stop["engine_rulings"][0]["ruling_id"]), ("not_in_kyuura", "FA1"))

    def test_si010_name_is_kyuuras_correction(self):
        """ベロリンガ（SI-010）のワザ 1 の名前は、kyuura の台帳の修正（FIX-SI-010-ATK1-NAME）が写しの元にすでに当てはめた値。写しには当てはめ直さない（二重の修正・もとの値への
        巻き戻しをしない）。"""
        extract = read_extract()
        correction = next(c for c in extract["kyuura_corrections"] if c["id"] == "FIX-SI-010-ATK1-NAME")
        self.assertEqual((correction["before"], correction["after"], correction["basis"], correction["engine_saw_image"]), ("のびるべ口", "のびるベロ", "kyuura_existing_record", False))
        card = next(c for c in extract["cards"] if c["id"] == H.LICKITUNG_SI)
        self.assertEqual(card["pokemon"]["attacks"][1]["name"]["ja"], "のびるベロ")
        self.assertEqual(DEFAULT_EFFECTS.attack_entry(H.LICKITUNG_SI, 1).name_ja, "のびるベロ")

    def test_new_types_are_not_in_the_v0_13_verified_list(self):
        from kyuura_engine.resolution.v013_checks import VERIFIED

        new_types = {type(DEFAULT_EFFECTS.attack_entry(k.card_id, k.attack_index).effect) for k in V089_ATTACKS} - {
            E.DamageOnly, E.ParalyzeOnHeads, E.CoinBonusOrSelfDamage, E.CoinChooseOpponentPokemonDamage}
        self.assertEqual(len(new_types), 13)
        for effect_type in new_types:
            self.assertIn(effect_type, H.ATTACK_TYPES_SINCE_V0_17)
            self.assertNotIn(effect_type, VERIFIED)


class TextVariantTest(unittest.TestCase):
    """書き方の違いは、意味と引数を確かめたものだけを明示して受け付ける（全文で照らす）。似た別の型は、新しいワザの文面を受け付けない。"""

    def attack(self, card, index):
        return load_card_pool().get(card).attacks[index]

    def test_thunder_crash_is_accepted_only_with_matching_values(self):
        crash = self.attack(H.ZAPDOS_ES2, 1)
        self.assertEqual(E.CoinBonusOrSelfDamage(20, 20).check(crash), [])
        self.assertNotEqual(E.CoinBonusOrSelfDamage(20, 10).check(crash), [])
        self.assertNotEqual(E.CoinBonusOrSelfDamage(30, 20).check(crash), [])

    def test_older_types_do_not_accept_the_new_texts(self):
        cases = (
            (E.CoinChooseOpponentBenchDamage(30), (H.BROCKS_GEODUDE_GD1, 1)),  # かげからおそう（コインが先）とロングショット（選んでからコイン）
            (E.DamageThenChosenBenchCoinDamage(1, 10), (H.MISTYS_SEAKING_GD2, 1)),  # ほのおのかぜ（枚数 × の数）とだくりゅう
            (E.DamageIgnoringDefenderEffects(), (H.UMBREON_NEO2, 1)),  # スピードスター（相手の持っている）とだましうち
            (E.CoinChooseOpponentPokemonDamage(20), (H.MACHOKE_ES3, 1)),  # 弱点・抵抗力に関係なくと、控えにも計算するきあいだま
            (E.ChooseOpponentPokemonDamage(20), (H.MAGNETON_ES2, 0)),
            (E.CoinChosenSideHealAttack(2), (H.LICKITUNG_SI, 0)),  # あまいかおり（おもてなら自分・うらなら相手）ときずをなめる
            (E.CoinActiveElseChosenBenchDamage(20, 20, False), (H.MEOWTH_PR1, 0)),  # 選ぶプレイヤーと文面を組で照らす
            (E.CoinActiveElseChosenBenchDamage(30, 10, True), (H.CUBONE_ES3, 0)),
            (E.ChooseOpponentPokemonOwnEnergyDamage(EnergyType.WATER, 10, 2), (H.DARK_OMANYTE, 0)),  # 上限の個数
        )
        for effect, (card, index) in cases:
            with self.subTest(effect=type(effect).__name__, card=card):
                self.assertNotEqual(effect.check(self.attack(card, index)), [])

    def test_aimed_shot_text_keeps_the_transcribed_glyph(self):
        """ねらいだま（SI-013）の文面の「抵抗カ」（カタカナの「カ」）は写しのまま照らす（直さない）。漢字の「力」の書き方は、この写しのワザとは別の文面。"""
        text = self.attack(H.EXEGGUTOR_SI, 0).text_ja
        self.assertIn("「弱点・抵抗カ」", text)
        self.assertEqual(E.ChooseOpponentPokemonCoinsPerOwnEnergyDamage(EnergyType.GRASS, 10).check(self.attack(H.EXEGGUTOR_SI, 0)), [])
        self.assertNotIn("抵抗力", E.AIMED_SHOT_TEXT)


# ---------------------------------------------------------------- 3 章: 選ぶ要素と選んだ個体の引き継ぎ


class ChooseTargetTest(unittest.TestCase):

    def test_candidates_by_side_and_scope(self):
        state = board(mon(H.CHANSEY), bench=(H.RATTATA, H.SQUIRTLE), opponent=mon(H.CHARMANDER), opponent_bench=(H.RATTATA,))
        mine = [p.pokemon_id for p in state.players[0].in_play()]
        theirs = opponent_ids(state)
        cases = {(E.TARGET_SIDE_OPPONENT, E.TARGET_IN_PLAY): theirs, (E.TARGET_SIDE_OPPONENT, E.TARGET_BENCH): theirs[1:],
                 (E.TARGET_SIDE_OWN, E.TARGET_IN_PLAY): mine, (E.TARGET_SIDE_OWN, E.TARGET_BENCH): mine[1:],
                 (E.TARGET_SIDE_BOTH, E.TARGET_IN_PLAY): mine + theirs}
        for (side, scope), expected in cases.items():
            self.assertEqual([p.pokemon_id for _, p in E.target_candidates(state, 0, side, scope)], expected)
        with self.assertRaises(ValueError):
            programs.ChooseTarget(side="middle")

    def test_carried_target_keeps_identity_and_owner(self):
        """選んだ個体は続きの情報の ``chosen_targets`` に (名前, 番号, 持ち主) で運ぶ（v0.83 の (名前, 番号) の形も読める）。持ち主を入れかえた続きの情報は不変条件が拒否する。"""
        from kyuura_engine.engine import check_invariants

        mime = mon(H.SABRINAS_MR_MIME_GD6, (P, P), trainers=[(H.SABRINAS_ESP, TURN)])
        state = board(mime, opponent=mon(H.CHANSEY))
        bench = opponent_ids(state)[1]
        asking = answer(declare(state, 0, HD, TL, HD), (bench,))
        self.assertEqual(asking.decision.kind, "esp_redo")
        self.assertEqual(asking.decision.context_value("chosen_targets"), (("target", bench, 1),))
        audited(self, asking)
        bad = copy.deepcopy(asking)
        context = tuple(("chosen_targets", (("target", bench, 0),)) if k == "chosen_targets" else (k, v) for k, v in bad.decision.context)
        bad.decision = dataclasses.replace(bad.decision, context=context)
        self.assertTrue(any("持ち主" in problem for problem in check_invariants(bad)))

    def test_a_target_that_left_play_is_not_replaced(self):
        """選んだ相手の対戦ポケモン（カスミのドククラゲ）が、ダメージのあとの［にげこむ］で控えにもどったら、マイクロウェーブのトラッシュはそのポケモンにも、かわりに出たポケモンにも
        与えない（コインも投げない）。今の対戦ポケモンにすり替えない。"""
        tentacruel = mon(H.MISTYS_TENTACRUEL, (W, W), played_turn=2, evolved_from=H.MISTYS_TENTACOOL, evolved_turn=4)
        state = board(stage1(H.MAGNETON_ES2, (L, L, L), base=H.MAGNEMITE), opponent=tentacruel, opponent_bench=(mon(H.RATTATA, (W,)),))
        chosen = state.players[1].active.pokemon_id
        flee = answer(declare(state, 0), (chosen,))
        self.assertEqual(flee.decision.kind, "reaction_switch")
        moved = answer(flee, flee.decision.options)
        self.assertIsNone(moved.decision)
        self.assertEqual(new_events(flee, moved, "coin_flip"), [])
        self.assertEqual([p.energy for p in moved.players[1].in_play()], [state.players[1].bench[0].energy, state.players[1].active.energy])
        audited(self, moved)

    def test_damage_triggers_wait_until_the_chosen_bench_damage(self):
        """だくりゅう: 相手の対戦ポケモン（カイリキー［はんげき］）への 30 → 控えを選ぶ（決定）→ コイン → 控えに 10 → そのあとに［はんげき］の 10（ダメージの処理がすべて終わったあと。
        p.89・CR-COUNTERATTACK-TIMING）。決定をまたいで送る効果を運ぶ。"""
        machamp = mon(H.MACHAMP, played_turn=2, evolved_from=[H.MACHOP, H.MACHOKE], evolved_turn=6)
        state = board(stage1(H.MISTYS_SEAKING_GD2, (W, W), base=H.MISTYS_GOLDEEN), opponent=machamp)
        choosing = declare(state, 1, HD)
        self.assertEqual(choosing.decision.kind, "select_pokemon")
        self.assertTrue(choosing.decision.context_value("frame") and dict(choosing.decision.context_value("frame")).get("pending"))
        done = answer(choosing, (opponent_ids(state)[1],))
        kinds = [e["kind"] for e in new_events(state, done) if e["kind"] in ("damage", "counterattack")]
        self.assertEqual(kinds, ["damage", "damage", "counterattack"])
        self.assertEqual(damages(state, done)[:2], [("opponent_active", None, 30), ("opponent_bench", opponent_ids(state)[1], 10)])
        audited(self, done)


# ---------------------------------------------------------------- 4 章: 効果を除くダメージ（だましうち）と FA1


class FeintAttackTest(unittest.TestCase):
    """ブラッキー（neo2-040）の「だましうち」。受けるポケモン自身の持っている効果を除く（スピードスターと同じ処理）。説明がだれの効果かを書かないので、除く範囲の読み方で受ける
    ダメージが変わるポケモンは選ぶと止める（FA1）。"""

    def test_bench_target_ignores_its_own_effects(self):
        """控えのヒトカゲ（ついているディフェンダー・弱点）とゴースト（「とうめい」）。受けるポケモン自身の効果はどの読み方でも除くので、30 のまま（とうめいのコインもない）。"""
        charmander = mon(H.CHARMANDER, trainers=[(H.DEFENDER, TURN)])
        state = board(umbreon(), opponent=mon(H.CHANSEY), opponent_bench=(charmander, mon(H.HAUNTER, played_turn=2, evolved_from=H.GASTLY, evolved_turn=4)))
        choosing = declare(state, 1)
        bench = opponent_ids(state)[1:]
        self.assertEqual(choosing.decision.context_value("unresolved_choices"), (opponent_ids(state)[0],))  # 悪エネルギーの +10 がかかる相手の対戦ポケモンだけ
        for target in bench:
            with self.subTest(target=target):
                done = answer(choosing, (target,))
                hits = new_events(choosing, done, "damage")
                self.assertEqual([(e["target"], e["pokemon_id"], e["amount"], e.get("ignore_defender_effects"), e.get("ignore_effects_scope")) for e in hits],
                                 [("opponent_bench", target, 30, True, "unstated")])
                self.assertEqual(new_events(choosing, done, "coin_flip"), [])
                audited(self, done)

    def test_active_with_darkness_energy_is_an_unresolved_choice(self):
        """相手の対戦ポケモンへのダメージには、ワザを使うポケモンについている悪エネルギーの +10（受けるポケモンの持っていない効果）がかかるので、読み方で 50 と 30 が分かれる。選ぶと止める。"""
        state = board(umbreon(), opponent=mon(H.CHANSEY))
        choosing = declare(state, 1)
        rejects(self, choosing, ResolveDecision(0, choosing.decision.id, (opponent_ids(state)[0],)), FA1)

    def test_every_choice_blocked_stops_before_choosing(self):
        """相手に控えがいない（対戦ポケモンだけ）なら、どの答えでも止まるので、宣言の前に止める（状態・乱数・ログは変わらない）。"""
        state = board(umbreon(), opponent=mon(H.CHANSEY), opponent_bench=())
        rejects(self, state, UseAttack(0, 1), FA1)

    def test_invisible_wall_and_bench_guard_block_bench_targets(self):
        """見えない壁（トレーナーの効果）と、ほかのポケモンの［ベンチガード］は受けるポケモンの持っている効果ではないので、すべての効果を除く読み方とで結果が分かれる（FA1）。"""
        theirs_umbreon = mon(H.UMBREON_NEO2, (DARK, DARK, W), played_turn=2, evolved_from=H.EEVEE, evolved_turn=4)
        wall = board(mon(H.CHANSEY), opponent=theirs_umbreon, hand=(H.INVISIBLE_WALL,))
        theirs = apply_kernel(play(wall, H.INVISIBLE_WALL), EndTurn(0))
        rejects(self, theirs, UseAttack(1, 1), FA1)  # 控えは見えない壁、対戦ポケモンは悪エネルギーで、どの答えも止まる（宣言の前）
        rhydon = mon(H.BROCKS_RHYDON, played_turn=2, evolved_from="PMCG5-049", evolved_turn=4)
        state = board(umbreon(), opponent=mon(H.CHANSEY), opponent_bench=(mon(H.RATTATA), rhydon))
        choosing = declare(state, 1)
        rattata, rhydon_id = opponent_ids(state)[1:]
        self.assertEqual(choosing.decision.context_value("unresolved_choices"), (opponent_ids(state)[0], rattata))
        done = answer(choosing, (rhydon_id,))  # ［ベンチガード］はサイドン自身の受けるダメージには使わない
        self.assertEqual(damages(choosing, done), [("opponent_bench", rhydon_id, 30)])
        audited(self, done)

    def test_speed_star_keeps_its_own_reading(self):
        """スピードスター（「相手の持っている」）は v0.60 のまま（SS1 で比べ、FA1 の比べをしない。ログに ``ignore_effects_scope`` を書かない）。"""
        sandslash = stage1(H.BROCKS_SANDSLASH, (FT, FT), base="PMCG5-043")
        state = board(sandslash, opponent=mon(H.CHANSEY), hand=(H.PLUSPOWER,))
        done = declare(play(state, H.PLUSPOWER), 0)
        hit = new_events(state, done, "damage")[0]
        self.assertEqual((hit["amount"], hit.get("ignore_defender_effects"), "ignore_effects_scope" in hit), (30, True, False))


class WaterGunTest(unittest.TestCase):
    """わるいオムナイト（neo4-035）の「てっぽうみず」: 選んだポケモンに、自分の「水」エネルギーの数 × 10（3 個ぶんまで。弱点・抵抗力に関係なく）。"""

    def test_amounts_and_cap(self):
        for energy, expected in (((W,), 10), ((W, W), 20), ((W, W, W, W), 30), ((W, DCE), 10)):
            with self.subTest(energy=energy):
                state = board(omanyte(energy), opponent=mon(H.CHARMANDER))
                done = answer(declare(state, 0), (opponent_ids(state)[0],))
                self.assertEqual(damages(state, done), [("opponent_active", None, expected)])  # ヒトカゲの弱点（水）は計算しない
                audited(self, done)

    def test_cap_makes_an_undetermined_card_irrelevant(self):
        """どの読み方でも「水」3 個以上なら、レインボーエネルギーが「水」か（RB1）で量は変わらないので止めない。3 個に届かない読み方があれば止める（どの答えも同じなので宣言の前）。"""
        state = board(omanyte((W, W, W, RAINBOW)), opponent=mon(H.CHANSEY))
        done = answer(declare(state, 0), (opponent_ids(state)[1],))
        self.assertEqual(damages(state, done), [("opponent_bench", opponent_ids(state)[1], 30)])
        audited(self, done)
        short = board(omanyte((W, RAINBOW)), opponent=mon(H.CHANSEY))
        rejects(self, short, UseAttack(0, 0), RB1)


class LongShotTest(unittest.TestCase):
    """タケシのイシツブテ（GD1-007）の「ロングショット」: 相手の控えから選ぶ → コイン → 「おもて」で 30（弱点・抵抗力に関係なく）。控えがいなければ使えない。"""

    def geodude(self, **extra):
        return mon(H.BROCKS_GEODUDE_GD1, (FT, FT), **extra)

    def test_choose_then_flip(self):
        state = board(self.geodude(), opponent=mon(H.CHANSEY))
        choosing = declare(state, 1, HD)
        self.assertEqual((choosing.decision.kind, choosing.decision.options), ("select_pokemon", tuple(opponent_ids(state)[1:])))
        self.assertEqual(new_events(state, choosing, "coin_flip"), [])  # 選んでからコイン
        bench = opponent_ids(state)[1]
        done = answer(choosing, (bench,))
        self.assertEqual(damages(state, done), [("opponent_bench", bench, 30)])  # コラッタの弱点（闘）は計算しない
        missed = answer(declare(state, 1, TL), (bench,))
        self.assertEqual((damages(state, missed), len(new_events(state, missed, "coin_flip"))), ([], 1))
        audited(self, missed)

    def test_usage_condition(self):
        state = board(self.geodude(), opponent=mon(H.CHANSEY), opponent_bench=())
        rejects(self, state, UseAttack(0, 1), "NO_OPPONENT_BENCH", error=IllegalActionError)

    def test_damage_only_coin_against_protected_bench(self):
        """控えがみな見えない壁でダメージを受けないなら、コインはダメージだけを決めるので投げるかが決められない（v0.4b の問い。選ぶ前に止める）。"""
        wall = board(mon(H.CHANSEY), opponent=self.geodude(played_turn=2), hand=(H.INVISIBLE_WALL,))
        theirs = apply_kernel(play(wall, H.INVISIBLE_WALL), EndTurn(0))
        rejects(self, theirs, UseAttack(1, 1), PREVENTED)

    def test_bench_guard_after_the_coin(self):
        rhydon = mon(H.BROCKS_RHYDON, played_turn=2, evolved_from="PMCG5-049", evolved_turn=4)
        state = board(self.geodude(), opponent=mon(H.CHANSEY), opponent_bench=(mon(H.RATTATA), rhydon))
        rattata, rhydon_id = opponent_ids(state)[1:]
        guarding = answer(declare(state, 1, HD), (rattata,))
        self.assertEqual((guarding.decision.kind, guarding.decision.player, guarding.decision.options), ("bench_guard", 1, (rhydon_id,)))
        done = answer(guarding, (rhydon_id,))
        self.assertEqual(damages(state, done), [("opponent_bench", rattata, 20)])
        self.assertEqual([(e["pokemon_id"], e["amount"]) for e in new_events(state, done, "bench_guard")], [(rhydon_id, 10)])
        self.assertEqual(len(new_events(state, done, "coin_flip")), 1)  # 決定のあとでコインを投げ直さない
        audited(self, done)


class MuddyWaterTest(unittest.TestCase):
    """カスミのアズマオウ（GD2-011）の「だくりゅう」: 相手に 30 → 控えがいれば選ぶ → コイン → 「おもて」でその控えにも 10。"""

    def seaking(self):
        return stage1(H.MISTYS_SEAKING_GD2, (W, W), base=H.MISTYS_GOLDEEN)

    def test_heads_tails_and_no_bench(self):
        state = board(self.seaking(), opponent=mon(H.CHANSEY))
        bench = opponent_ids(state)[1]
        heads = answer(declare(state, 1, HD), (bench,))
        self.assertEqual(damages(state, heads), [("opponent_active", None, 30), ("opponent_bench", bench, 10)])
        tails = answer(declare(state, 1, TL), (bench,))
        self.assertEqual(damages(state, tails), [("opponent_active", None, 30)])
        alone = board(self.seaking(), opponent=mon(H.CHANSEY), opponent_bench=())
        done = declare(alone, 1, HD)
        self.assertEqual((done.decision, damages(alone, done), new_events(alone, done, "coin_flip")), (None, [("opponent_active", None, 30)], []))
        for result in (heads, tails, done):
            audited(self, result)

    def test_knocked_out_active_does_not_cancel_the_bench_part(self):
        """相手の対戦ポケモンが 30 で HP 以上になっても、別の控えへの内容は処理する（対象が違う。p.309）。"""
        state = board(self.seaking(), opponent=mon(H.RATTATA))
        bench = opponent_ids(state)[1]
        done = answer(declare(state, 1, HD), (bench,))
        self.assertEqual(damages(state, done), [("opponent_active", None, 30), ("opponent_bench", bench, 10)])
        self.assertEqual(done.decision.kind, "take_prize")
        audited(self, done)


class MagicDartsTest(unittest.TestCase):
    """ナツメのバリヤード（GD6-011）の「マジックダーツ」: 相手の場のポケモンを選ぶ → コイン 3 枚 → 「おもて」の数 × 10（弱点・抵抗力に関係なく）。"""

    def test_heads_times_ten(self):
        state = board(mon(H.SABRINAS_MR_MIME_GD6, (P, P)), opponent=mon(H.CHANSEY))
        done = answer(declare(state, 0, HD, TL, HD), (opponent_ids(state)[0],))
        self.assertEqual(damages(state, done), [("opponent_active", None, 20)])  # ラッキーの抵抗力（超）は計算しない
        audited(self, done)

    def test_esp_redo_keeps_the_chosen_target(self):
        """ナツメのESP: 選んだあとに投げた説明文のコインで、やり直しを聞く（選んだ個体は続きの情報で運び、選び直さない）。やり直さないなら最初の結果、やり直すなら 3 枚をすべて
        投げ直した結果を使う（ESP 1 枚なので ES2 に当たらない）。"""
        mime = mon(H.SABRINAS_MR_MIME_GD6, (P, P), trainers=[(H.SABRINAS_ESP, TURN)])
        state = board(mime, opponent=mon(H.CHANSEY))
        bench = opponent_ids(state)[1]
        asking = answer(declare(state, 0, HD, TL, HD), (bench,))
        self.assertEqual((asking.decision.kind, asking.decision.context_value("unresolved_choices")), ("esp_redo", None))
        self.assertEqual(asking.decision.context_value("chosen_targets"), (("target", bench, 1),))
        kept = answer(asking, ())
        self.assertEqual(damages(state, kept), [("opponent_bench", bench, 20)])
        self.assertEqual(len(new_events(state, kept, "coin_flip")), 3)
        redone = answer(with_coin_results(asking, HD, HD, HD), (1,))
        self.assertEqual(damages(state, redone), [("opponent_bench", bench, 30)])
        self.assertEqual(len(new_events(state, redone, "coin_flip")), 6)
        for result in (kept, redone):
            audited(self, result)


class ShockStorageTest(unittest.TestCase):
    """ライチュウ（ES2-013・QSG-022）の「ろうでん」: 選んだポケモンについている「水」エネルギーの数 × 10（弱点・抵抗力に関係なく）。"""

    def raichu(self, card=H.RAICHU_ES2):
        return stage1(card, (L, L), base=H.PIKACHU)

    def test_counts_the_chosen_pokemon(self):
        for card in (H.RAICHU_ES2, H.RAICHU_QSG):
            state = board(self.raichu(card), opponent=mon(H.CHANSEY, (W, DCE)), opponent_bench=(mon(H.SQUIRTLE, (W, W, W)),))
            active, bench = opponent_ids(state)
            first = answer(declare(state, 0), (active,))
            second = answer(declare(state, 0), (bench,))
            self.assertEqual((damages(state, first), damages(state, second)), ([("opponent_active", None, 10)], [("opponent_bench", bench, 30)]))
            audited(self, second)

    def test_undetermined_count_blocks_only_that_pokemon(self):
        """レインボーエネルギーのついたポケモンは、「水」エネルギーに当たるかが決まらないので選ぶと止める（RB1）。ほかのポケモンを選ぶ答えは止めない。"""
        state = board(self.raichu(), opponent=mon(H.CHANSEY, (W, RAINBOW)), opponent_bench=(mon(H.SQUIRTLE, (W,)),))
        active, bench = opponent_ids(state)
        choosing = declare(state, 0)
        self.assertEqual(choosing.decision.context_value("unresolved_choices"), (active,))
        rejects(self, choosing, ResolveDecision(0, choosing.decision.id, (active,)), RB1)
        done = answer(choosing, (bench,))
        self.assertEqual(damages(state, done), [("opponent_bench", bench, 10)])
        audited(self, done)


# ---------------------------------------------------------------- 5.3 節: 同じ個体への後続の効果（マイクロウェーブ）


class MicrowaveTest(unittest.TestCase):
    """レアコイル（ES2-015・QSG-024）の「マイクロウェーブ」: 相手の場のポケモンを選ぶ → 20（弱点・抵抗力に関係なく）→ コイン → 「おもて」なら、同じ個体のエネルギーカードを
    1 枚選んでトラッシュさせる。"""

    def magneton(self, card=H.MAGNETON_ES2):
        return stage1(card, (L, L, L), base=H.MAGNEMITE)

    def test_bench_target_loses_its_own_card(self):
        """控えを選んだら、その控えのエネルギーカードから選ぶ（対戦ポケモンのカードにすり替えない）。トラッシュは v0.82 の共通の経路（ログ ``discard_attached_energy``）。"""
        for card in (H.MAGNETON_ES2, H.MAGNETON_QSG):
            state = board(self.magneton(card), opponent=mon(H.CHANSEY, (W,)), opponent_bench=(mon(H.RATTATA, (W, F)),))
            bench = opponent_ids(state)[1]
            discard = answer(declare(state, 0, HD), (bench,))
            self.assertEqual((discard.decision.kind, discard.decision.options, discard.decision.context_value("target")),
                             ("discard_opponent_energy", tuple(state.players[1].bench[0].energy), bench))
            done = answer(discard, (state.players[1].bench[0].energy[1],))
            self.assertEqual(damages(state, done), [("opponent_bench", bench, 20)])
            self.assertEqual((done.players[1].bench[0].energy, done.players[1].active.energy), ([state.players[1].bench[0].energy[0]], state.players[1].active.energy))
            audited(self, done)

    def test_tails_no_energy_and_knocked_out_targets(self):
        state = board(self.magneton(), opponent=mon(H.CHANSEY, (W,)), opponent_bench=(mon(H.RATTATA), mon(H.RATTATA, (W,), damage=10)))
        active, bare, weak = opponent_ids(state)
        tails = answer(declare(state, 0, TL), (active,))
        self.assertEqual((tails.decision, len(new_events(state, tails, "coin_flip"))), (None, 1))
        for target in (bare, weak):  # エネルギーカードがない・このワザで HP 以上: 処理の対象がないので、コインを投げない
            with self.subTest(target=target):
                done = answer(declare(state, 0), (target,))
                self.assertEqual(new_events(state, done, "coin_flip"), [])
                audited(self, done)

    def test_recycle_energy_returns_through_the_shared_path(self):
        """リサイクルエネルギーは、ワザで場からトラッシュに置かれても持ち主の手札にもどる（v0.82 の共通の経路を手書きの移動で迂回しない）。"""
        state = board(self.magneton(), opponent=mon(H.CHANSEY, (H.RECYCLE_ENERGY,)))
        discard = answer(declare(state, 0, HD), (opponent_ids(state)[0],))
        recycle = state.players[1].active.energy[0]
        done = answer(discard, (recycle,))
        self.assertIn(recycle, done.players[1].hand)
        self.assertEqual([e["card"] for e in new_events(state, done, "energy_returned_to_hand")], [recycle])
        audited(self, done)

    def test_protected_and_evasive_candidates(self):
        """ゴースト（「とうめい」）を選ぶと、ダメージの要素で受けないと決まったあとのトラッシュのコインを投げるかが決められない（T19b）ので、選ぶと止める。ほかは選べる。"""
        haunter = mon(H.HAUNTER, (P,), played_turn=2, evolved_from=H.GASTLY, evolved_turn=4)
        state = board(self.magneton(), opponent=mon(H.CHANSEY, (W,)), opponent_bench=(haunter,))
        active, ghost = opponent_ids(state)
        choosing = declare(state, 0)
        self.assertEqual(choosing.decision.context_value("unresolved_choices"), (ghost,))
        rejects(self, choosing, ResolveDecision(0, choosing.decision.id, (ghost,)), T19B)
        done = answer(answer(with_coin_results(choosing, HD), (active,)), (state.players[1].active.energy[0],))
        self.assertEqual(done.players[1].active.energy, [])
        audited(self, done)


# ---------------------------------------------------------------- 5.4 節: 選べる回復（きずをなめる）


class LickWoundsTest(unittest.TestCase):
    """ベロリンガ（SI-010）の「きずをなめる」: コイン → 「おもて」なら、おたがいの場のポケモンから 1 匹を選び、ダメージカウンターを 2 つとりのぞく。"""

    def state(self):
        return board(mon(H.LICKITUNG_SI, (W,), damage=10), bench=(mon(H.RATTATA, damage=20),),
                     opponent=mon(H.CHANSEY, damage=50), opponent_bench=(mon(H.RATTATA),))

    def test_any_pokemon_on_either_side(self):
        state = self.state()
        choosing = declare(state, 0, HD)
        mine = [p.pokemon_id for p in state.players[0].in_play()]
        self.assertEqual((choosing.decision.options, choosing.decision.player), (tuple(mine + opponent_ids(state)), 0))
        # (持ち主, とりのぞいたあとのダメージ, とりのぞいた数)。のっている数まで（ベロリンガ自身は 1 つだけ）
        expected = {mine[0]: (0, 0, 1), mine[1]: (0, 0, 2), opponent_ids(state)[0]: (1, 30, 2)}
        for target, (owner, after, counters) in expected.items():
            with self.subTest(target=target):
                done = answer(choosing, (target,))
                self.assertEqual(done.find_pokemon(target)[1].damage, after)
                heals = new_events(choosing, done, "attack_heal")
                self.assertEqual([(e["player"], e["pokemon_id"], e["counters"], e.get("attacker")) for e in heals], [(owner, target, counters, 0 if owner == 1 else None)])
                audited(self, done)
        zero = answer(choosing, (opponent_ids(state)[1],))  # ダメージカウンターがない: 何もしない（効果を受けない）
        self.assertEqual(new_events(choosing, zero, "attack_heal"), [])
        audited(self, zero)

    def test_tails_does_nothing(self):
        state = self.state()
        done = declare(state, 0, TL)
        self.assertEqual((done.decision, new_events(state, done, "attack_heal")), (None, []))
        audited(self, done)


# ---------------------------------------------------------------- 6 章: 移した型（相手の場のポケモンを選ぶダメージ）と、のびるベロ・きあいだま


class ChooseOpponentPokemonTest(unittest.TestCase):
    """v0.43〜v0.87 の相手の場のポケモンを選ぶダメージ（``ChooseOpponentPokemonDamage``・``CoinChooseOpponentPokemonDamage``）を、選ぶ要素と選んだ個体へのダメージの要素に分けた。
    選ぶ決定の形・ログは v0.88 までと同じ。選んだ相手の対戦ポケモンへのダメージで、お上品攻撃の減らす量・順番の決定を出せるようになった（v0.88 まではエンジンの未対応で止めていた）。"""

    def test_decision_form_is_unchanged(self):
        cases = ((mon(H.LICKITUNG_SI, (W, W)), 1, (HD,)),
                 (mon(H.ROCKET_MEOWTH, (W, W)), 0, (HD,)), (mon(H.MAGNEMITE_ES2, (L,)), 0, ()))
        for attacker, index, coins in cases:
            with self.subTest(card=attacker["card"]):
                state = board(attacker, opponent=mon(H.CHANSEY))
                choosing = declare(state, index, *coins)
                d = choosing.decision
                self.assertEqual((d.kind, d.player, d.options, d.min_choices, d.max_choices), ("select_pokemon", 0, tuple(opponent_ids(state)), 1, 1))
                self.assertEqual(sorted(k for k, _ in d.context), ["frame", "use"])
                bench = opponent_ids(state)[1]
                done = answer(choosing, (bench,))
                self.assertEqual(damages(state, done), [("opponent_bench", bench, 10 if attacker["card"] == H.MAGNEMITE_ES2 else 20)])
                audited(self, done)

    def test_charity_reduction_for_a_chosen_active(self):
        """のびるベロ（お上品攻撃のついたベロリンガ）で相手の対戦ポケモンを選ぶと、減らす量の決定を出す（選んだ個体は続きの情報で運ぶ）。控えへのダメージには当てはめない。"""
        state = board(mon(H.LICKITUNG_SI, (W, W), trainers=[(H.CHARITY, TURN + 1)]), opponent=mon(H.CHANSEY))
        active, bench = opponent_ids(state)
        reducing = answer(declare(state, 1, HD), (active,))
        self.assertEqual((reducing.decision.kind, reducing.decision.options, reducing.decision.context_value("chosen_targets")),
                         ("damage_reduction", (0, 10, 20), (("target", active, 1),)))
        done = answer(reducing, (10,))
        self.assertEqual(damages(state, done), [("opponent_active", None, 10)])
        audited(self, done)
        plain = answer(declare(state, 1, HD), (bench,))
        self.assertEqual((plain.decision, damages(state, plain)), (None, [("opponent_bench", bench, 20)]))

    def test_coin_before_choice_against_a_protected_lone_active(self):
        """コインのあとに選ぶダメージ（こばんなげ・のびるベロ）で、選べるのが「ワザをうけない」相手の対戦ポケモンだけなら、v0.44 と同じく v0.4b の問い（コインの前）。"""
        state = board(mon(H.LICKITUNG_SI, (W, W)), opponent=mon(H.CHANSEY, prevent_damage=TURN - 1), opponent_bench=())
        rejects(self, state, UseAttack(0, 1), PREVENTED)

    def test_intended_changes_for_existing_cards(self):
        """docs 6 章の意図した変化。固定した v0.88（8de7bbb）の木では、1・2 は ``UNSUPPORTED_DAMAGE_REDUCTION_DECISION`` で止まり、3 はコインを投げて選ぶ決定を出していた
        （同じ盤面で確かめた）。

        1. わるいゴルバット（PMCG4-009）の「ふらふらとぶ」で、お上品攻撃のついたゴルバットが相手の対戦ポケモンを選ぶと、減らす量の決定を出す
        2. ひかるライチュウ（neo4-047）の「サンダースコール」（先に選んだ控えを運ぶ）の相手の対戦ポケモンへのダメージも、減らす量の決定を出す
        3. ロケット団のニャース（PMCG4-047）の「こばんなげ」で、選べるどのポケモンもダメージを受けない（相手の対戦ポケモンは「ダメージを受けない」状態、控えは見えない壁）なら、
           コインの前に v0.4b の問いで止める"""
        golbat = stage1(H.DARK_GOLBAT, (G, G), base=H.ROCKET_ZUBAT, trainers=[(H.CHARITY, TURN + 1)])
        state = board(golbat, opponent=mon(H.CHANSEY))
        reducing = answer(declare(state, 0), (opponent_ids(state)[0],))
        self.assertEqual((reducing.decision.kind, reducing.decision.options), ("damage_reduction", (0, 10, 20)))
        audited(self, answer(reducing, (20,)))
        raichu = mon(H.SHINING_RAICHU, (L, L, W, W), trainers=[(H.CHARITY, TURN + 1)])
        state = board(raichu, opponent=mon(H.CHANSEY))
        reducing = answer(declare(state, 0), (opponent_ids(state)[1],))
        self.assertEqual((reducing.decision.kind, reducing.decision.options), ("damage_reduction", (0, 10, 20, 30, 40)))
        audited(self, answer(reducing, (0,)))
        wall = board(mon(H.CHANSEY, prevent_damage=TURN), opponent=mon(H.ROCKET_MEOWTH, (W, W), played_turn=2), hand=(H.INVISIBLE_WALL,))
        theirs = apply_kernel(play(wall, H.INVISIBLE_WALL), EndTurn(0))
        rejects(self, theirs, UseAttack(1, 0), PREVENTED)

    def test_focus_blast_applies_weakness_and_resistance(self):
        """ゴーリキー（ES3-028）の「きあいだま」: 控えへのダメージも弱点・抵抗力を計算する（説明に明記。JS1 で止めない）。"""
        state = board(stage1(H.MACHOKE_ES3, (FT, FT, FT), base=H.MACHOP), opponent=mon(H.CHANSEY))
        active, bench = opponent_ids(state)
        for target, expected in ((active, ("opponent_active", None, 40)), (bench, ("opponent_bench", bench, 40))):
            done = answer(declare(state, 1, HD), (target,))
            self.assertEqual(damages(state, done), [expected])  # ラッキー・コラッタの弱点（闘）× 2
            audited(self, done)
        self.assertEqual(declare(state, 1, TL).decision, None)


class AimedShotTest(unittest.TestCase):
    """ナッシー（SI-013）の「ねらいだま」: 選んでから、自分の「草」エネルギーの数だけコインを投げ、「おもて」の数 × 10（弱点・抵抗力に関係なく）。"""

    def exeggutor(self, energy=(G, G, G)):
        return stage1(H.EXEGGUTOR_SI, energy, base=H.EXEGGCUTE)

    def test_coins_follow_grass_energy(self):
        state = board(self.exeggutor(), opponent=mon(H.CHARMANDER))
        choosing = declare(state, 0, HD, TL, HD)
        self.assertEqual(new_events(state, choosing, "coin_flip"), [])
        done = answer(choosing, (opponent_ids(state)[0],))
        self.assertEqual((len(new_events(state, done, "coin_flip")), damages(state, done)), (3, [("opponent_active", None, 20)]))  # ヒトカゲの弱点（草ではない）・計算しない
        audited(self, done)

    def test_wild_growth_doubles_the_coins(self):
        """［おいしげる］（メガニウム）のはたらく場では、「草」エネルギーカード 1 枚が「草」2 個ぶん（エネルギーの個数で数える）。"""
        state = board(self.exeggutor((G, G)), bench=(meganium(),), opponent=mon(H.CHANSEY))
        done = answer(declare(state, 0, HD, HD, TL, TL), (opponent_ids(state)[0],))
        self.assertEqual((len(new_events(state, done, "coin_flip")), damages(state, done)), (4, [("opponent_active", None, 20)]))
        audited(self, done)


# ---------------------------------------------------------------- 5.2 節: コインのあとに選ぶ・選ぶ側が違う


class BoneTossAndCatPunchTest(unittest.TestCase):
    """カラカラ（ES3-030）の「ほねをなげる」とニャース（PR1-057）の「ねこパンチ」: 1 枚のコインで、相手の対戦ポケモンへのダメージか、控えを選ぶダメージかを決める。"""

    def test_bone_toss(self):
        state = board(mon(H.CUBONE_ES3, (FT,)), opponent=mon(H.CHANSEY))
        heads = declare(state, 0, HD)
        self.assertEqual((heads.decision, damages(state, heads)), (None, [("opponent_active", None, 60)]))  # ラッキーの弱点（闘）× 2
        bench = opponent_ids(state)[1]
        tails = answer(declare(state, 0, TL), (bench,))
        self.assertEqual(damages(state, tails), [("opponent_bench", bench, 10)])  # 控えは弱点・抵抗力に関係なく
        alone = board(mon(H.CUBONE_ES3, (FT,)), opponent=mon(H.CHANSEY), opponent_bench=())
        nothing = declare(alone, 0, TL)  # 「うら」で控えがいなければ何もしない（ワザの失敗・使うための条件にしない）
        self.assertEqual((nothing.decision, damages(alone, nothing), new_events(alone, nothing, "attack_failed")), (None, [], []))
        for result in (heads, tails, nothing):
            audited(self, result)

    def test_cat_punch_is_chosen_by_the_opponent(self):
        state = board(mon(H.MEOWTH_PR1, (W, W)), opponent=mon(H.CHANSEY))
        choosing = declare(state, 0, TL)
        bench = opponent_ids(state)[1]
        self.assertEqual((choosing.decision.player, choosing.current_player, choosing.decision.options), (1, 0, (bench,)))
        rejects(self, choosing, ResolveDecision(0, choosing.decision.id, (bench,)), "NOT_YOUR_DECISION", error=IllegalActionError)
        self.assertNotIn("options", observe(choosing, 0)["decision"])  # 選べるものは決めるプレイヤーだけに見える
        done = answer(choosing, (bench,))
        self.assertEqual(damages(state, done), [("opponent_bench", bench, 20)])
        heads = declare(state, 0, HD)
        self.assertEqual(damages(state, heads), [("opponent_active", None, 20)])  # 無色のニャースのワザ（ラッキーの弱点は闘）
        for result in (done, heads):
            audited(self, result)

    def test_cat_punch_bench_weakness_is_js1_per_choice(self):
        """説明が控えへのダメージの弱点・抵抗力を書かないので、計算するかで受けるダメージが変わる控えは選ぶと止める（JS1。v0.39 のスパークと同じ）。ニャースは無色で、写しに無色の
        弱点・抵抗力のポケモンはないので、カスミのコダック（水）の「ちょうのうりょく」で「ねこパンチ」を使う。弱点 水 のヒトカゲは止め、コラッタは止めない（選ぶのは相手プレイヤー）。"""
        state = board(mon(H.MISTYS_PSYDUCK, (P,)), opponent=mon(H.MEOWTH_PR1, (W, W)), opponent_bench=(mon(H.CHARMANDER), mon(H.RATTATA)))
        selecting = declare(state, 0, HD, HD, HD)
        self.assertEqual(selecting.decision.kind, "select_attack")
        choosing = answer(with_coin_results(selecting, TL), (0,))
        charmander, rattata = opponent_ids(state)[1:]
        self.assertEqual((choosing.decision.player, choosing.decision.context_value("unresolved_choices"), choosing.decision.context_value("unresolved_code")),
                         (1, (charmander,), JS1))
        rejects(self, choosing, ResolveDecision(1, choosing.decision.id, (charmander,)), JS1)
        done = answer(choosing, (rattata,))
        self.assertEqual(damages(choosing, done), [("opponent_bench", rattata, 20)])
        audited(self, done)


class LightningBurnTest(unittest.TestCase):
    """サンダー（PR1-070）の「ライトニングバーン」: 30 → 1 枚のコインで、「おもて」なら選んだ控えにも 30、「うら」なら自分にも 30。"""

    def test_one_coin_decides_bench_or_self(self):
        state = board(mon(H.ZAPDOS_PR1, (L, L, L)), opponent=mon(H.CHANSEY))
        bench = opponent_ids(state)[1]
        heads = answer(declare(state, 0, HD), (bench,))
        self.assertEqual(damages(state, heads), [("opponent_active", None, 30), ("opponent_bench", bench, 30)])
        tails = declare(state, 0, TL)
        self.assertEqual((tails.decision, damages(state, tails)), (None, [("opponent_active", None, 30), ("self", state.players[0].active.pokemon_id, 30)]))
        for result in (heads, tails):
            self.assertEqual(len(new_events(state, result, "coin_flip")), 1)
            audited(self, result)


class ThunderboltFallTest(unittest.TestCase):
    """サンダー（ES2-018・QSG-056）の「らくらい」: 50 → コインの「うら」で、自分の場のポケモン（自分自身も）を選び、そのポケモンにも 30（弱点・抵抗力に関係なく）。"""

    def test_choose_self_or_own_bench(self):
        for card in (H.ZAPDOS_ES2, H.ZAPDOS_QSG):
            state = board(mon(card, (L, L, L)), bench=(mon(H.CHANSEY),), opponent=mon(H.CHANSEY))
            mine = [p.pokemon_id for p in state.players[0].in_play()]
            choosing = declare(state, 0, TL)
            self.assertEqual((choosing.decision.player, choosing.decision.options), (0, tuple(mine)))
            on_self = answer(choosing, (mine[0],))
            on_bench = answer(choosing, (mine[1],))
            self.assertEqual(damages(state, on_self), [("opponent_active", None, 50), ("self", mine[0], 30)])
            self.assertEqual(damages(state, on_bench), [("opponent_active", None, 50), ("self_bench", mine[1], 30)])
            heads = declare(state, 0, HD)
            self.assertEqual((heads.decision, damages(state, heads)), (None, [("opponent_active", None, 50)]))
            for result in (on_self, on_bench, heads):
                audited(self, result)

    def test_own_bench_guard_is_asked_to_the_attacker(self):
        """自分の控えへのダメージでも［ベンチガード］を聞く（v0.65。自分のワザでも聞く）。決めるのはサイドンの持ち主（ワザを使ったプレイヤー）。"""
        rhydon = stage1(H.BROCKS_RHYDON, base="PMCG5-049")
        state = board(mon(H.ZAPDOS_ES2, (L, L, L)), bench=(mon(H.CHANSEY), rhydon), opponent=mon(H.CHANSEY))
        chansey, rhydon_id = [p.pokemon_id for p in state.players[0].bench]
        guarding = answer(declare(state, 0, TL), (chansey,))
        self.assertEqual((guarding.decision.kind, guarding.decision.player, guarding.decision.options), ("bench_guard", 0, (rhydon_id,)))
        done = answer(guarding, ())
        self.assertEqual(damages(state, done)[-1], ("self_bench", chansey, 30))
        audited(self, done)

    def test_thunder_crash(self):
        state = board(mon(H.ZAPDOS_ES2, (L, L, L, L)), opponent=mon(H.CHANSEY))
        heads = declare(state, 1, HD)
        tails = declare(state, 1, TL)
        self.assertEqual(damages(state, heads), [("opponent_active", None, 70)])
        self.assertEqual(damages(state, tails), [("opponent_active", None, 50), ("self", state.players[0].active.pokemon_id, 20)])


# ---------------------------------------------------------------- 8 章: 決定の持ち越し・保存と復元・先読み・見えない情報


def fingerprint(state):
    return state_to_dict(state, format_version=23), [dict(e) for e in state.log], repr(state.rng.getstate())


class DecisionPersistenceTest(unittest.TestCase):
    """選んだ個体・コインの結果・途中のダメージ・待っている送る効果を、決定の前後で明示的に持ち越す。複製・deepcopy・pickle からの再開も同じ答えで同じ結果。"""

    def waiting_states(self):
        """選んだあとの決定（ESP のやり直し）・コインのあとの選ぶ決定（だくりゅう。前のダメージの［はんげき］を運ぶ）・相手が答える決定（ねこパンチ）・減らす量の決定（のびるベロ）。"""
        mime = mon(H.SABRINAS_MR_MIME_GD6, (P, P), trainers=[(H.SABRINAS_ESP, TURN)])
        esp_state = board(mime, opponent=mon(H.CHANSEY))
        machamp = mon(H.MACHAMP, played_turn=2, evolved_from=[H.MACHOP, H.MACHOKE], evolved_turn=6)
        muddy_state = board(stage1(H.MISTYS_SEAKING_GD2, (W, W), base=H.MISTYS_GOLDEEN), opponent=machamp)
        cat_state = board(mon(H.MEOWTH_PR1, (W, W)), opponent=mon(H.CHANSEY))
        charity_state = board(mon(H.LICKITUNG_SI, (W, W), trainers=[(H.CHARITY, TURN + 1)]), opponent=mon(H.CHANSEY))
        return (
            answer(declare(esp_state, 0, HD, TL, HD), (opponent_ids(esp_state)[1],)),
            declare(muddy_state, 1, HD),
            declare(cat_state, 0, TL),
            answer(declare(charity_state, 1, HD), (opponent_ids(charity_state)[0],)),
        )

    def test_resume_after_copy_and_pickle_is_identical(self):
        # 決定のあとに投げるコイン: ESP のやり直さない答え・ねこパンチ・減らす量は 0 枚（決定の前に投げたコインを投げ直さない）、だくりゅうは選んだあとの 1 枚
        for waiting, coins_after in zip(self.waiting_states(), (0, 1, 0, 0)):
            with self.subTest(kind=waiting.decision.kind):
                audited(self, waiting)
                d = waiting.decision
                choice = ResolveDecision(d.player, d.id, (d.options[0],) if d.min_choices else ())
                results = [apply_kernel(s, choice) for s in (waiting, waiting.clone(), copy.deepcopy(waiting), pickle.loads(pickle.dumps(waiting)))]
                reference = fingerprint(results[0])
                for other in results[1:]:
                    self.assertEqual(fingerprint(other), reference)
                self.assertEqual(len(new_events(waiting, results[0], "coin_flip")), coins_after)
                # ダメージを二重に与えない（相手の対戦ポケモンへのダメージのログは、ワザの宣言からちょうど 1 回まで）
                attack_at = max(i for i, e in enumerate(results[0].log) if e["kind"] == "attack")
                active_hits = [e for e in results[0].log[attack_at:] if e["kind"] == "damage" and e.get("target", "opponent_active") == "opponent_active"]
                self.assertLessEqual(len(active_hits), 1)
                audited(self, results[0])

    def test_invalid_answers_change_nothing(self):
        for waiting in self.waiting_states():
            with self.subTest(kind=waiting.decision.kind):
                d = waiting.decision
                before = snapshot(waiting)
                for bad in ((999,), tuple(d.options) + (d.options[0],)):
                    with self.assertRaises((IllegalActionError, UnsupportedError)):
                        apply_kernel(waiting, ResolveDecision(d.player, d.id, bad))
                    self.assertEqual(snapshot(waiting), before)

    def test_serialized_decision_keeps_the_target(self):
        """保存の形式 23 で、選んだ個体と持ち主が決定の続きの情報に書かれる（新しい形式は要らない）。形式 1 はワザの途中の決定を書けない（今までどおり）。"""
        waiting = self.waiting_states()[0]
        data = state_to_dict(waiting, format_version=23)
        self.assertEqual(dict(data["decision"]["context"])["chosen_targets"], [["target", opponent_ids(waiting)[1], 1]] if isinstance(
            dict(data["decision"]["context"])["chosen_targets"], list) else (("target", opponent_ids(waiting)[1], 1),))
        with self.assertRaises(ValueError):
            state_to_dict(waiting, format_version=1)


class PreflightTest(unittest.TestCase):
    """宣言の前の先読みは、選べるすべての答え・答えるプレイヤー・コインの結果を試す（選ぶと止めるポケモンは試さない）。受け付けるかがコインの結果で変わらない。旧 legacy は
    v0.89 の型に使わない（VERIFIED にない）。"""

    def test_acceptance_does_not_depend_on_coins(self):
        cases = (
            (board(mon(H.BROCKS_GEODUDE_GD1, (FT, FT)), opponent=mon(H.CHANSEY)), 1),
            (board(stage1(H.MISTYS_SEAKING_GD2, (W, W), base=H.MISTYS_GOLDEEN), opponent=mon(H.CHANSEY)), 1),
            (board(mon(H.CUBONE_ES3, (FT,)), opponent=mon(H.CHANSEY)), 0),
            (board(mon(H.MEOWTH_PR1, (W, W)), opponent=mon(H.CHANSEY)), 0),
            (board(mon(H.ZAPDOS_ES2, (L, L, L)), opponent=mon(H.CHANSEY)), 0),
            (board(mon(H.LICKITUNG_SI, (W,)), opponent=mon(H.CHANSEY, damage=20)), 0),
            (board(umbreon(), opponent=mon(H.CHANSEY), opponent_bench=()), 1),
            (board(omanyte((W, RAINBOW)), opponent=mon(H.CHANSEY)), 0),
        )
        for state, index in cases:
            for mode in ("derived", "derived_full", "legacy"):
                outcomes = set()
                for coins in ((HD,) * 4, (TL,) * 4, (HD, TL, HD, TL)):
                    try:
                        apply_kernel(with_coin_results(state, *coins), UseAttack(0, index), preflight=mode)
                        outcomes.add("accepted")
                    except UnsupportedError as error:
                        outcomes.add(error.code)
                with self.subTest(card=state.cards[state.players[0].active.card].card_id, mode=mode):
                    self.assertEqual(len(outcomes), 1, outcomes)


class HiddenInformationTest(unittest.TestCase):
    """うらのカード（マチスの秘策）を選べる。本当のカードを読む前の確かめ（JS1・FA1・数え方）はうらのカードには聞かず、ダメージを受ける時におもてにしてから処理する。選ぶ決定の
    選べるもの（場のポケモンの番号）は公開の情報で、相手の観測の決定は種類と決めるプレイヤーだけ。"""

    def test_face_down_bench_can_be_chosen(self):
        from tests.test_type_energy_colors_v0_88 import hide

        state = board(umbreon(), opponent=mon(H.CHANSEY), opponent_hand=(H.LT_SURGES_SECRET_PLAN, H.CHANSEY), current=1, turn=TURN - 1)
        hidden = apply_kernel(hide(state, H.CHANSEY, player=1), EndTurn(1))
        face_down = next(p.pokemon_id for p in hidden.players[1].bench if hidden.is_face_down(p))
        choosing = declare(hidden, 1)
        self.assertIn(face_down, choosing.decision.options)
        self.assertNotIn(face_down, choosing.decision.context_value("unresolved_choices") or ())
        self.assertNotIn("options", observe(choosing, 1)["decision"])
        done = answer(choosing, (face_down,))
        self.assertFalse(done.is_face_down(done.find_pokemon(face_down)[1]))
        self.assertEqual(damages(choosing, done), [("opponent_bench", face_down, 30)])
        audited(self, done)


class DocumentTest(unittest.TestCase):
    def test_document_exists_and_mentions_the_cards(self):
        text = DOC.read_text(encoding="utf-8")
        for card_id in H.V0_89_POKEMON:
            self.assertIn(card_id, text)
        for code in (FA1, "IGNORE_UNSTATED", "chosen_targets"):
            self.assertIn(code, text)

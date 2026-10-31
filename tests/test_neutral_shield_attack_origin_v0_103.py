"""v0.103（docs/neutral-shield-attack-origin-v0.103.md）: ミュウの 2 枚（ワザ 2・特殊能力 2）と、無効にする効果の判定に発生元を渡す共通の処理。

根拠は kyuura データの採用（kyuura ``73a1690`` の data/cards.json の日本語の印刷の文面。2 枚を指す LD-・CC-・CR-・UQ-・エラッタはない）と、既存の規定と読み方の記録（v0.10 の
カイリキーの［はんげき］の「カイリキーが」「つかえない」の読み方、v0.49 の今の姿のモデル、v0.31 のバリアーの窓、v0.4b・HC3 のコイン、v0.60 の SS1、v0.89 の FA1、v0.62 の受けた記録）。
英語版の文面・現代のルール・後年の裁定は持ち込まない。公式ガイドブックの新しい読み直し・カードの画像の照合はしていない。盤面は ``build_test_state`` で作った 1 か所の規定を確かめる
ためのもので、``new_game`` からの自然な対戦の結果ではない（対戦は tools/existing_effect_games.py の ``--batch v0.103``）。
"""

from __future__ import annotations

import copy
import dataclasses
import json
import pathlib
import pickle
import unittest
from unittest import mock

from kyuura_engine import (
    DEFAULT_EFFECTS,
    AttackKey,
    EvolvePokemon,
    PlayTrainer,
    ResolveDecision,
    UseAttack,
    UsePokemonPower,
)
from kyuura_engine import effects as E
from kyuura_engine.cards import load_card_pool, pool_from_extract, read_extract
from kyuura_engine.coins import CoinSide
from kyuura_engine.effects import PowerKey
from kyuura_engine.errors import IllegalActionError, UnsupportedError
from kyuura_engine.resolution import catalog as C
from kyuura_engine.resolution import flow as F
from kyuura_engine.resolution import kernel as K
from kyuura_engine.resolution import programs as P
from kyuura_engine.resolution.events import (
    FRAME_DAMAGE_CLASS,
    DamageClass,
    Frame,
    FrameKind,
    Incoming,
)
from kyuura_engine.resolution.questions import QUESTIONS
from kyuura_engine.serialize import FORMAT_VERSIONS
from kyuura_engine.state import Phase
from tests import helpers as H
from tests.helpers import apply_kernel, with_coin_results
from tests.log_audit import log_problems
from tests.release_catalog import cards_after, cards_before
from tests.test_counter_keep_energy_protection_v0_101 import attack, pid, play
from tests.test_neo_trainer_components_v0_80 import audited, new_events, rejects
from tests.test_sketch_perish_song_history_v0_100 import settle
from tests.test_unown_family_powers_v0_96 import TURN, board, same_answers, snap

ROOT = pathlib.Path(__file__).resolve().parent.parent
DOC = ROOT / "docs" / "neutral-shield-attack-origin-v0.103.md"
HD, TL = CoinSide.HEADS, CoinSide.TAILS
W, PS, G, F_, L, FT = H.WATER, H.PSYCHIC, H.GRASS, H.FIRE, H.LIGHTNING, H.FIGHTING
MEW, MEW_JR = "PR1-005", "PR1-012"
MEW_DEVOLUTION = "PR1-069"  # ミュウ（たいかビーム。特殊能力なし。同じ名前の別のカード）
V0103 = (MEW, MEW_JR)
V0103_ATTACKS = [AttackKey(card, 0) for card in V0103]
V0103_POWERS = [PowerKey(card, 0) for card in V0103]
CHARMANDER, CHARMELEON = H.CHARMANDER, H.CHARMELEON
GROWLITHE, ARCANINE = H.GROWLITHE, H.ARCANINE
PIKACHU, RAICHU = H.PIKACHU, H.RAICHU
STARYU, STARMIE = H.STARYU, H.STARMIE
MACHOP, MACHOKE, MACHAMP = H.MACHOP, H.MACHOKE, H.MACHAMP
CATERPIE, RATTATA, DROWZEE = H.CATERPIE, H.RATTATA, H.DROWZEE
SQUIRTLE, DARK_WARTORTLE = H.SQUIRTLE, H.DARK_WARTORTLE
ROCKETS_HITMONCHAN, WOBBUFFET, ROCKETS_MOLTRES = "PMCG5-054", "neo2-031", H.ROCKETS_MOLTRES
LT_SURGES_VOLTORB, LT_SURGES_ELECTRODE = H.LT_SURGES_VOLTORB, "GD3-009"
CLEFAIRY, CLEFABLE = H.CLEFAIRY, H.CLEFABLE
BROCKS_ZUBAT, BROCKS_GOLBAT = H.BROCKS_ZUBAT, H.BROCKS_GOLBAT
ERIKAS_DRATINI, ERIKAS_DRAGONAIR = H.ERIKAS_DRATINI, H.ERIKAS_DRAGONAIR
BROCKS_SANDSHREW, BROCKS_SANDSLASH = H.BROCKS_SANDSHREW, H.BROCKS_SANDSLASH
EEVEE, UMBREON = H.EEVEE, "neo2-040"
FOSSIL_GEODUDE, GRAVELER_ES2, QWILFISH = "PMCG3-034", "ES2-023", "neo3-015"
DIGLETT, DUGTRIO = H.DIGLETT, H.DUGTRIO
FOSSIL_GRIMER, MUK = "PMCG3-003", H.MUK
GOOP_GAS, GUST, DITTO = H.GOOP_GAS_ATTACK, H.GUST, H.DITTO
PIDGEY, PIDGEOTTO = H.PIDGEY, H.PIDGEOTTO
SABRINAS_GASTLY_GD6, SABRINAS_HAUNTER_GD6, SABRINAS_GENGAR_GD6 = "GD6-006", "GD6-007", "GD6-008"
BREEDER, GENGAR_PR1, FOSSIL_GASTLY = H.POKEMON_BREEDER, "PR1-053", "PMCG3-029"
BELOW = {CHARMELEON: CHARMANDER, ARCANINE: GROWLITHE, RAICHU: PIKACHU, STARMIE: STARYU, MACHAMP: [MACHOP, MACHOKE], DARK_WARTORTLE: SQUIRTLE,
         LT_SURGES_ELECTRODE: LT_SURGES_VOLTORB, CLEFABLE: CLEFAIRY, BROCKS_GOLBAT: BROCKS_ZUBAT, ERIKAS_DRAGONAIR: ERIKAS_DRATINI,
         BROCKS_SANDSLASH: BROCKS_SANDSHREW, UMBREON: EEVEE, GRAVELER_ES2: FOSSIL_GEODUDE, DUGTRIO: DIGLETT, MUK: FOSSIL_GRIMER, PIDGEOTTO: PIDGEY,
         SABRINAS_GENGAR_GD6: [SABRINAS_GASTLY_GD6, SABRINAS_HAUNTER_GD6]}
# 依頼で示された固定データの日本語（写しの文面と照らす。広い正規化をしない）
SHIELD_QUOTED = "ミュウは相手の進化ポケモンからの「ワザ」を受けない。「ねむり・マヒ・こんらん」状態のときにはつかえない。"
PSYSHOCK_QUOTED = "コインを投げて「おもて」なら、相手を「マヒ」状態にする。"
HC3, PREVENTED_COIN = "UNRESOLVED_PREVENTED_EFFECT_COIN", "UNRESOLVED_PREVENTED_COIN_DAMAGE"


def mon(card, energy=(), **extra):
    spec = {"card": card, "energy": list(energy), **extra}
    if card in BELOW and "evolved_from" not in spec:
        spec["evolved_from"] = BELOW[card]
    return spec


def damages(before, after):
    return new_events(before, after, "damage")


def voids(before, after):
    return new_events(before, after, "damage_prevented", "effect_prevented")


def shielded(before, after):
    """［ニュートラルシールド］で無効にしたログの (種類, 受けたポケモン, 発生元の使い手, 発生元の個体, 要素)。"""
    return [(e["kind"], e["pokemon_id"], e.get("attacker"), e.get("attacker_pokemon_id"), e.get("element", e.get("target")))
            for e in voids(before, after) if e.get("persistent_effect") == "neutral_shield"]


def frame_res(state, attacker_pid, key, *, player=0, kind=FrameKind.ATTACK):
    """解決の基盤の問い合わせを直接呼ぶための、ワザの枠を 1 つ開いた ``Resolution``（状態は変えない）。"""
    res = K.Resolution(state)
    fs = res.open_frame(kind, parent=None, player=player, source_pid=attacker_pid, attack_key=key)
    return res, fs


# ---------------------------------------------------------------- 2 章: 対象・登録・文面・記録


class RegistrationTest(unittest.TestCase):
    def test_entries_and_printed_texts(self):
        pool = load_card_pool()
        self.assertEqual(tuple(read_extract()["pool_v0_103"]), V0103)
        for card in V0103:
            definition = pool.definitions[card]
            (attack_def,), (power,) = definition.attacks, definition.powers
            self.assertEqual((definition.name_ja, definition.stage, definition.evolves_from, definition.hp, definition.pokemon_type, definition.weakness,
                              definition.resistance, definition.retreat_cost),
                             ("ミュウ", "basic", None, 40, E.EnergyType.PSYCHIC, E.EnergyType.PSYCHIC, None, 1))
            self.assertEqual((attack_def.name_ja, attack_def.text_ja, attack_def.damage, attack_def.damage_modifier, tuple(t.value for t in attack_def.cost)),
                             ("ねんりき", PSYSHOCK_QUOTED, 10, None, ("psychic",)))
            self.assertEqual((power.name_ja, power.text_ja, power.kind), ("ニュートラルシールド", SHIELD_QUOTED, "pokemon_power"))
            entry, power_entry = DEFAULT_EFFECTS.attack_entry(card, 0), DEFAULT_EFFECTS.power_entry(card, 0)
            self.assertEqual((entry.effect, entry.name_ja, entry.text_ja, entry.play_text_ja, entry.source),
                             (E.ParalyzeOnHeads(), "ねんりき", PSYSHOCK_QUOTED, PSYSHOCK_QUOTED, "kyuura data/cards.json"))
            self.assertEqual((power_entry.effect, power_entry.name_ja, power_entry.text_ja, power_entry.play_text_ja, power_entry.source),
                             (E.EvolvedOpponentAttackImmunity(), "ニュートラルシールド", SHIELD_QUOTED, SHIELD_QUOTED, "kyuura data/cards.json"))
            self.assertIn(card, pool.playable_ids)
            self.assertIsNone(DEFAULT_EFFECTS.attack_problem(card, attack_def, definition.attacks))

    def test_same_data_pair_shares_the_registration(self):
        """kyuura の同じカードの組（SC-PR1-005）は、日本語の名前・pokemon 欄の対戦の値が同じなので、id ごとに登録し同じ値にまとめる（id は消さない）。"""
        cards = {c["id"]: c for c in read_extract()["cards"]}
        self.assertEqual(E.SAME_DATA_CARDS_V0_103, {MEW_JR: MEW})
        self.assertEqual(cards[MEW_JR]["pokemon"], cards[MEW]["pokemon"])
        self.assertEqual(cards[MEW_JR]["name"]["ja"], cards[MEW]["name"]["ja"])
        self.assertEqual({cards[c]["same_card_group"] for c in V0103}, {"SC-PR1-005"})
        self.assertEqual(DEFAULT_EFFECTS.attack_entry(MEW_JR, 0), DEFAULT_EFFECTS.attack_entry(MEW, 0))
        self.assertEqual(DEFAULT_EFFECTS.power_entry(MEW_JR, 0), DEFAULT_EFFECTS.power_entry(MEW, 0))

    def test_attack_type_matches_the_printed_text(self):
        """型の既存の検査は形だけなので、処理と印刷の文面を照らす: ダメージの目安の 10 → コイン 1 枚 →「おもて」で相手をマヒ（v0.3b のキャタピーの「いとをはく」の p.17 の最新の説明と
        同じ文面の型）。"""
        psyshock = load_card_pool().definitions[MEW].attacks[0]
        self.assertEqual(E.ParalyzeOnHeads().check(psyshock), [])
        self.assertEqual(P.BUILDERS[E.ParalyzeOnHeads](E.ParalyzeOnHeads()),
                         (P.Damage(P.OPP, P.Printed()), P.Status(E.PARALYSIS, local_coin=HD, reparalysis_check=True)))
        self.assertEqual(E.PSYSHOCK_TEXT, PSYSHOCK_QUOTED)
        self.assertEqual(DEFAULT_EFFECTS.attack_entry(CATERPIE, 0).play_text_ja, PSYSHOCK_QUOTED)

    def test_power_text_is_not_normalized(self):
        shield = load_card_pool().definitions[MEW].powers[0]
        self.assertEqual(E.EvolvedOpponentAttackImmunity().check(shield), [])
        for changed in (shield.text_ja.replace("進化ポケモン", "ポケモン"), shield.text_ja.replace("相手の", ""), shield.text_ja.replace("ミュウは", "このカードは"),
                        shield.text_ja.replace("「ワザ」を", "「ワザ」のダメージを"), shield.text_ja.replace("「ねむり・マヒ・こんらん」状態のときにはつかえない。", "")):
            with self.subTest(changed=changed):
                self.assertNotEqual(E.EvolvedOpponentAttackImmunity().check(dataclasses.replace(shield, text_ja=changed)), [])

    def test_power_and_definition_types(self):
        """常にはたらく特殊能力（宣言しない・場のどこでも・ねむり・マヒ・こんらんで消える）。解決の基盤の定義はバリアーと同じ窓・処理で、発生元で判定する（今の番のプレイヤーで
        判定する ``by_opponent`` は使わない）。"""
        shield = E.EvolvedOpponentAttackImmunity()
        self.assertEqual((shield.declared, shield.location, shield.blocked_by_status, shield.self_excluding), (False, E.CONTINUOUS_IN_PLAY, True, False))
        self.assertIsInstance(shield, E.ContinuousPower)
        self.assertNotIsInstance(shield, E.WeaknessResistancePower)
        definition = C.definition_for(shield, C.POWER_DEFINITIONS)
        self.assertIs(definition, C.NEUTRAL_SHIELD)
        self.assertEqual((definition.timing, definition.windows, definition.action, definition.disabled_by, definition.suppressible, definition.by_opponent,
                          definition.from_evolved_opponent),
                         (C.Timing.VOID, frozenset({K.Window.BEFORE_DAMAGE, K.Window.BEFORE_EFFECT}), "void_attack", C.BLOCKING_CONDITIONS, True, False, True))
        self.assertEqual([d.name for _, d in C.POWER_DEFINITIONS + C.PERSISTENT_DEFINITIONS if d.from_evolved_opponent], ["neutral_shield"])

    def test_unregistered_without_the_v0_103_entries(self):
        """今回の登録だけを除くと、ちょうど 2 枚が未対応にもどる（同じデータの組も id ごとに数える）。"""
        registry = DEFAULT_EFFECTS.without_attacks(DEFAULT_EFFECTS.id, V0103_ATTACKS).without_powers(DEFAULT_EFFECTS.id, V0103_POWERS)
        before = pool_from_extract(read_extract(), registry)
        self.assertEqual(load_card_pool().playable_ids - before.playable_ids, frozenset(V0103))
        self.assertEqual(set(V0103) & set(cards_before(read_extract(), "0.103")), set())
        self.assertEqual(set(cards_after(read_extract(), "0.102")) & set(cards_before(read_extract(), "0.104")), set(V0103))

    def test_extract_values_keep_the_gaps_and_the_english_difference(self):
        """レベルの欠けは補わない。日本語の文面は pcg-search.com の転記。ねんりきの英語の欄は「Confused」で日本語の「マヒ」と違うが、日本語を採用し、英語で置きかえない。"""
        cards = {c["id"]: c for c in read_extract()["cards"]}
        for card in V0103:
            self.assertEqual(cards[card]["data_gaps"], ["jp_print.level"])
            self.assertIsNone(cards[card]["jp_print"]["level"])
            self.assertIn("pcg-search.com", cards[card]["ja_text_source"])
            attack_text = cards[card]["pokemon"]["attacks"][0]["text"]
            self.assertIn("「マヒ」", attack_text["ja"])
            self.assertIn("Confused", attack_text["en"])
            self.assertEqual(DEFAULT_EFFECTS.attack_entry(card, 0).play_text_ja, attack_text["ja"])

    def test_adoption_records(self):
        """採用の記録: kyuura データの採用（外部照合なし・kyuura の記録なし）。日英の違いは挙動に影響しない論点として書く（保留にしない）。"""
        sources = json.loads((ROOT / "kyuura_engine" / "data" / "card_sources.json").read_text(encoding="utf-8"))["cards"]
        links = json.loads((ROOT / "kyuura_engine" / "data" / "research_links.json").read_text(encoding="utf-8"))
        for card in V0103:
            record = sources[card]
            # v0.114: 研究の基準を e519b99 に上げて、kyuura の CR-NEUTRAL-SHIELD-EVOLVED-BABY がこのカードを指す（採用したときのデータのコミット・記録した日は変えない。tests/helpers.py）
            self.assertEqual((record["basis"], record["status"], record["kyuura_commit"], record["kyuura_records"], record["external_checks"], record["play_text"]),
                             ("kyuura_data", "adopted", "73a169063463bbf7bcaa3137d70cbf9721d11534", H.kyuura_records_since_v0_69(card), [],
                              {"power/0": "kyuura_printed_text", "attack/0": "kyuura_printed_text"}))
            (issue,) = record["issues"]
            self.assertEqual((issue["fields"], issue["affects_behavior"]), (["pokemon.attacks[0].text.ja"], False))
            for target in (f"{card}/power/0", f"{card}/attack/0"):
                self.assertIn(target, links["latest_descriptions"]["adopted_printed_text"])

    def test_no_new_codes_or_format(self):
        self.assertIn(26, FORMAT_VERSIONS)  # 力は今の場から求める。新しい状態・書き出しの形式は加えない。今の最新の形式は tests/test_catalog_contract.py（docs/testing.md）
        # v0.122 の FE3（「なにかの化石」から進化したポケモンの読み方。docs/unown-fossil-retreat-reactions-v0.122.md 4.1 節）は［ニュートラルシールド］の問いではない
        self.assertFalse([q for q in QUESTIONS.values() if q.code and ("NEUTRAL_SHIELD" in q.code or "EVOLVED" in q.code) and q.code != "UNRESOLVED_FOSSIL_EVOLVED_READING"])
        self.assertTrue(K.SOURCE_LEFT_CODE.startswith("UNSUPPORTED_"))  # エンジンの情報の不足（研究上の未解決ではない）

    def test_power_is_not_declared(self):
        """常にはたらく特殊能力なので、使う宣言は既存の ``POWER_NOT_DECLARABLE`` で拒否する（使うかどうかの選択・毎番 1 回の記録はない）。"""
        state = _turn_of(board(mon(CHARMELEON, (F_,) * 3), opponent=mon(MEW, (PS,))), 1)
        rejects(self, state, UsePokemonPower(1, pid(state, MEW, 1), 0), "POWER_NOT_DECLARABLE", error=IllegalActionError)


def _turn_of(state, player):
    """``player`` の番にした状態（複製。ワザ・決定のない場の、特殊能力の宣言の拒否を確かめるため）。"""
    new = state.clone()
    new.current_player = player
    new.turn_number = TURN + (1 if player == 1 else 0)
    return new


# ---------------------------------------------------------------- 3 章: 守る範囲


class ScopeTest(unittest.TestCase):
    def test_evolved_attackers_are_voided_and_basic_is_not(self):
        """1 進化（リザードのきりさく 30）・2 進化（カイリキーのちきゅうなげ 60）のワザのダメージは無効（ログ ``damage_prevented`` の ``neutral_shield`` と発生元）。たね（キャタピーの
        いとをはく）は 10 とマヒを受ける。2 枚のミュウのどちらも同じ。"""
        for mew in V0103:
            for attacker, index in ((mon(CHARMELEON, (F_,) * 3), 0), (mon(MACHAMP, (FT,) * 4), 0)):
                with self.subTest(mew=mew, attacker=attacker["card"]):
                    state = board(attacker, opponent=mon(mew, (PS,)))
                    after = attack(state, index)
                    self.assertEqual(shielded(state, after), [("damage_prevented", pid(state, mew, 1), 0, pid(state, attacker["card"], 0), "opponent_active")])
                    self.assertEqual((damages(state, after), after.players[1].active.damage), ([], 0))
                    audited(self, after)
            state = board(mon(CATERPIE, (G,)), opponent=mon(mew, (PS,)))
            after = attack(state, 0, HD)
            self.assertEqual([e["amount"] for e in damages(state, after)], [10])
            self.assertTrue(after.players[1].active.conditions.paralyzed)
            self.assertEqual(shielded(state, after), [])

    def test_bench_mew_and_the_rest_of_the_attack(self):
        """タケシのゴルバットのかいてんひこう（相手と相手の控え全員に 10）: ベンチのミュウだけ無効にし、バトル場のコラッタ・ほかの控えは 10 を受ける（ワザ全体を無効にしない）。"""
        state = board(mon(BROCKS_GOLBAT, (G,) * 3), opponent=mon(RATTATA), opponent_bench=(mon(MEW), mon(RATTATA)))
        after = attack(state, 1)
        bench_mew = next(p.pokemon_id for p in state.players[1].bench if state.cards[p.card].card_id == MEW)
        self.assertEqual(shielded(state, after), [("damage_prevented", bench_mew, 0, pid(state, BROCKS_GOLBAT, 0), "opponent_bench")])
        active = state.players[1].active.pokemon_id
        self.assertEqual(sorted(e.get("pokemon_id", active) for e in damages(state, after)),
                         sorted(p.pokemon_id for p in state.players[1].in_play() if p.pokemon_id != bench_mew))
        audited(self, after)

    def test_only_the_holder_is_protected(self):
        """ねむりのバトル場のミュウ（自分の力がはたらかない）・ベンチの特殊能力のないミュウ（PR1-069）は、ベンチのもう 1 匹のミュウの力で守られない（文面の「ミュウ」は持つ個体
        自身。名前の同じポケモンのグループの効果にしない）。ベンチのミュウ自身は守られる。"""
        state = board(mon(BROCKS_GOLBAT, (G,) * 3), opponent=mon(MEW, sleep=True), opponent_bench=(mon(MEW_JR), mon(MEW_DEVOLUTION)))
        after = attack(state, 1)
        self.assertEqual([e[0] for e in shielded(state, after)], ["damage_prevented"])
        self.assertEqual(shielded(state, after)[0][1], pid(state, MEW_JR, 1))
        self.assertEqual(after.players[1].active.damage, 10)
        self.assertEqual(after.find_pokemon(pid(state, MEW_DEVOLUTION, 1))[1].damage, 10)

    def test_own_evolved_pokemon_is_not_blocked(self):
        """自分の進化ポケモン（ダグトリオのじしん。自分の控え全員に 10）の自分の控えのミュウへのダメージは受ける（「相手の」）。"""
        state = board(mon(DUGTRIO, (FT,) * 4), bench=(mon(MEW),), opponent=mon(RATTATA, damage=0))
        after = attack(state, 1)
        own = [e for e in damages(state, after) if e.get("target") == "self_bench"]
        self.assertEqual([(e["pokemon_id"], e["amount"]) for e in own], [(pid(state, MEW, 0), 10)])
        self.assertEqual(shielded(state, after), [])

    def test_status_suppression_and_recovery(self):
        """ねむり・マヒ・こんらんのミュウ、かがくへんかガス（ベトベトン）・まきちらせ!ベトベトガスのはたらく場では、力がはたらかず 30 を受ける。ベトベトンがいなくなる・特殊状態が
        回復すれば、問い合わせのたびに今の場から求めるので、また守る（印を状態に残さない）。"""
        for status in ({"sleep": True}, {"paralysis": TURN - 1}, {"confusion": True}):
            with self.subTest(status=status):
                state = board(mon(CHARMELEON, (F_,) * 3), opponent=mon(MEW, (PS,), **status))
                self.assertEqual([e["amount"] for e in damages(state, attack(state, 0, HD))], [30])
                cured = board(mon(CHARMELEON, (F_,) * 3), opponent=mon(MEW, (PS,)))
                self.assertEqual(len(shielded(cured, attack(cured, 0))), 1)
        gassed = board(mon(CHARMELEON, (F_,) * 3), bench=(mon(MUK),), opponent=mon(MEW, (PS,)))
        self.assertEqual([e["amount"] for e in damages(gassed, attack(gassed, 0))], [30])
        lifted = gassed.clone()
        muk = lifted.players[0].bench.pop()  # ベトベトンが場をはなれた場（カードはトラッシュに置く。カードの保存則を保つ）
        lifted.players[0].discard.extend(muk.cards())
        self.assertEqual(len(shielded(lifted, attack(lifted, 0))), 1)
        goop = board(mon(CHARMELEON, (F_,) * 3), opponent=mon(MEW, (PS,)), hand=[GOOP_GAS])
        played = play(goop, GOOP_GAS)
        self.assertEqual([e["amount"] for e in damages(played, attack(played, 0))], [30])

    def test_costs_and_own_effects_remain(self):
        """ワザを使うための支払い・自分への効果は消さない: ウインディのかえんほうしゃは炎エネルギーをトラッシュしてから 50 が無効、とっしんは 80 が無効で自分の 30 は受ける。ワザの宣言は
        受け付ける（使えないことと、受けないことを分ける）。"""
        state = board(mon(ARCANINE, (F_,) * 4), opponent=mon(MEW, (PS,)))
        pending = attack(state, 0)
        self.assertEqual(pending.decision.kind, "discard_energy")  # トラッシュする炎エネルギーカードを選ぶ決定（ダメージの前）。無効の判定は再開のあとのダメージの時点
        after = apply_kernel(pending, ResolveDecision(0, pending.decision.id, pending.decision.options[:1]))
        self.assertEqual(len(after.players[0].active.energy), 3)
        self.assertEqual([e[0] for e in shielded(state, after)], ["damage_prevented"])
        after = attack(state, 1)
        self.assertEqual([(e.get("target"), e["amount"]) for e in damages(state, after)], [("self", 30)])
        self.assertEqual(after.players[0].active.damage, 30)
        audited(self, after)


# ---------------------------------------------------------------- 3 章: 借りたワザ・今の姿


class BorrowedAndFormTest(unittest.TestCase):
    def test_basic_copier_with_an_evolution_card_attack(self):
        """たねのピッピのゆびをふるで、相手の進化カード（タケシのゴルバット）のかいてんひこうを使う: 実際の使い手はたねポケモンなので、ベンチのミュウも 10 を受ける（借りたワザの
        ``AttackKey.card_id`` の段階を読まない）。"""
        state = board(mon(CLEFAIRY, (W,) * 3), opponent=mon(BROCKS_GOLBAT, (G,)), opponent_bench=(mon(MEW),))
        waiting = attack(state, 1)
        after = apply_kernel(waiting, ResolveDecision(0, waiting.decision.id, (1,)))
        self.assertEqual([e["copied"] for e in new_events(state, after, "copy_attack")], [f"{BROCKS_GOLBAT}#1"])
        self.assertIn((pid(state, MEW, 1), 10), [(e.get("pokemon_id"), e["amount"]) for e in damages(state, after)])
        self.assertEqual(shielded(state, after), [])
        audited(self, after)

    def test_evolved_copier_with_a_basic_card_attack(self):
        """進化したピクシーのゆびをふるで、ミュウ（たねポケモンのカード）のねんりきを使う: 実際の使い手は進化ポケモンなので、ダメージ・マヒを受けない。マヒだけを決めるコインは、無効な
        要素だけを決めるので既存の HC3 で宣言の前に止まる（受け付けない）。隣の例: たねのピッピなら 10 とマヒ。"""
        rejects(self, board(mon(CLEFABLE, (W,)), opponent=mon(MEW, (PS,))), UseAttack(0, 0), HC3)
        state = board(mon(CLEFAIRY, (W,) * 3), opponent=mon(MEW, (PS,)))
        waiting = attack(with_coin_results(state, HD), 1)
        after = apply_kernel(waiting, ResolveDecision(0, waiting.decision.id, (0,)))
        self.assertEqual([e["amount"] for e in damages(state, after)], [10])
        self.assertTrue(after.players[1].active.conditions.paralyzed)

    def test_transform_keeps_tf1(self):
        """［へんしん］のメタモンの相手の対戦ポケモンにミュウを出す（突風）と、写す常にはたらく特殊能力のある姿になる。v0.123 までは TF1 で受け付けなかった。v0.124 から、変身の対象の
        いちばん上のカードの特殊能力を持つ（CR-TRANSFORM-COPIES-TOP-CARD。docs/super-transform-dark-pulse-v0.124.md 3.1 節）ので受け付け、メタモンは［ニュートラルシールド］を持つ
        （意図した既存の動きの変化。v0.103 の新しい能力で TF1 を解決したのではなく、v0.124 の研究の採用による）。"""
        state = board(mon(DITTO, (PS,)), opponent=mon(RATTATA), opponent_bench=(mon(MEW),), hand=[GUST])
        played = apply_kernel(state, PlayTrainer(0, state.players[0].hand[0]))
        done = apply_kernel(played, ResolveDecision(0, played.decision.id, (played.players[1].bench[0].pokemon_id,)))
        self.assertIn(MEW, {slot.key.card_id for slot in E.powers_of(done, done.players[0].active)})

    def test_current_form_is_read_at_the_time_of_the_check(self):
        """段階は問い合わせの時点の今の姿（v0.49 の ``form_def``）: 同じ個体が進化する前はたね、進化したあとは 1 進化。宣言の前の場の値で固定しない。"""
        state = board(mon(CHARMANDER, (F_,)), hand=[CHARMELEON], opponent=mon(MEW, (PS,)))
        charmander = state.players[0].active
        incoming = Incoming(0, charmander.pokemon_id, DamageClass.ATTACK, AttackKey(CHARMANDER, 0))
        self.assertFalse(K.source_evolved(K.Resolution(state), incoming))
        evolved = apply_kernel(state, EvolvePokemon(0, state.players[0].hand[0], charmander.pokemon_id))
        self.assertTrue(K.source_evolved(K.Resolution(evolved), incoming))
        self.assertTrue(K.from_evolved_opponent(K.Resolution(evolved), incoming, 1))
        self.assertFalse(K.from_evolved_opponent(K.Resolution(evolved), incoming, 0))  # 自分のポケモンへ

    def test_left_play_uses_the_element_record_or_stops(self):
        """発生元がワザの途中で場をはなれたら、要素を始めたときの記録（``Resolution.source_forms``）を使う。記録がなければ推測せず、エンジンの未対応（情報の不足）として止める。"""
        state = board(mon(CHARMELEON, (F_,) * 3), opponent=mon(MEW, (PS,)))
        source = state.players[0].active.pokemon_id
        incoming = Incoming(0, source, DamageClass.ATTACK, AttackKey(CHARMELEON, 0))
        gone = state.clone()
        gone.players[0].active = None
        res = K.Resolution(gone)
        with self.assertRaises(UnsupportedError) as raised:
            K.source_evolved(res, incoming)
        self.assertEqual(raised.exception.code, K.SOURCE_LEFT_CODE)
        recorded = K.Resolution(state)
        K.note_source_form(recorded, Frame(1, FrameKind.ATTACK, None, 0, source, incoming.attack_key))  # 場にいる間に要素を始めた
        self.assertEqual(recorded.source_forms, {source: True})
        res.source_forms.update(recorded.source_forms)
        self.assertTrue(K.source_evolved(res, incoming))


# ---------------------------------------------------------------- 4 章: 処理の分類（返す効果・特殊能力・こんらん）


class OriginClassTest(unittest.TestCase):
    def test_evolution_shell_attack_is_voided(self):
        """ミュウがこうらがえしを受けたわるいカメール（1 進化）にねんりき: わるいカメールは 10 を受け、返す 10（返す効果の枠。ワザの分類）は無効（使い手は番でないプレイヤー）。"""
        state = board(mon(MEW, (PS,)), opponent=mon(DARK_WARTORTLE, (W,), retaliation_received=TURN - 1))
        after = attack(state, 0, TL)
        self.assertEqual([e["amount"] for e in new_events(state, after, "retaliation")], [10])
        self.assertEqual(shielded(state, after), [("damage_prevented", pid(state, MEW, 0), 1, pid(state, DARK_WARTORTLE, 1), "opponent_active")])
        self.assertTrue(all(e.get("retaliation") for e in voids(state, after)))
        self.assertEqual(after.players[0].active.damage, 0)
        audited(self, after)

    def test_basic_counters_reach_mew(self):
        """たねポケモンの返す効果（R団のエビワラーのクロスカウンター・ソーナンスのカウンター・R団のファイヤーのほのおのかべ）のダメージは受ける。"""
        given = attack(board(mon(ROCKETS_HITMONCHAN, (FT,)), opponent=mon(MEW, (PS,))), 0)
        after = attack(given, 0, HD, TL)
        self.assertIn(40, [e["amount"] for e in damages(given, after) if e.get("retaliation")])
        given = attack(board(mon(WOBBUFFET, (PS,)), opponent=mon(MEW, (PS,))), 0)
        after = attack(given, 0, HD, TL)
        self.assertIn(40, [e["amount"] for e in damages(given, after) if e.get("retaliation")])  # 受けた 20 を返し、ミュウの弱点（超）で 40
        state = board(mon(MEW, (PS,)), opponent=mon(ROCKETS_MOLTRES, retaliation=TURN - 1))
        after = attack(state, 0, TL)
        self.assertEqual([e["amount"] for e in damages(state, after) if e.get("retaliation")], [10])
        self.assertEqual(shielded(state, after), [])

    def test_evolution_power_damage_reaches_mew(self):
        """進化ポケモンの特殊能力のダメージ（カイリキーの［はんげき］・マチスのマルマインの［ショックボム］）は受ける（ワザにしない）。ワザを使ったポケモンが自分の番に「ダメージを受けない」
        状態だとする既存の不具合の確かめ・SB1 に、新しい能力で当たらない。"""
        state = board(mon(MEW, (PS,)), opponent=mon(MACHAMP, (FT,)))
        after = attack(state, 0, TL)
        self.assertEqual([e["amount"] for e in new_events(state, after, "counterattack")], [10])
        self.assertEqual(after.players[0].active.damage, 10)
        state = board(mon(MEW, (PS,)), opponent=mon(LT_SURGES_ELECTRODE, (L,)))
        after = attack(state, 0, TL, TL)
        self.assertIn(pid(state, MEW, 0), [e["target_pokemon_id"] for e in new_events(state, after, "shock_blast_damage")])
        audited(self, after)

    def test_classes_and_players(self):
        """発生元の判定: ワザの分類（宣言したワザ・返す効果）で、使い手が受けるポケモンの持ち主の相手で、今の姿が進化ポケモンのときだけ。特殊能力・こんらんは発生元が進化ポケモンでも
        当てはまらない。"""
        self.assertEqual({kind: FRAME_DAMAGE_CLASS[kind] for kind in FrameKind},
                         {FrameKind.ATTACK: DamageClass.ATTACK, FrameKind.RETALIATION: DamageClass.ATTACK, FrameKind.POWER_DAMAGE: DamageClass.POWER,
                          FrameKind.CONFUSION: DamageClass.CONFUSION})
        state = board(mon(CHARMELEON, (F_,) * 3), opponent=mon(MEW, (PS,)))
        res, source = K.Resolution(state), state.players[0].active.pokemon_id
        for damage_class, player, owner, expected in ((DamageClass.ATTACK, 0, 1, True), (DamageClass.POWER, 0, 1, False), (DamageClass.CONFUSION, 0, 1, False),
                                                      (DamageClass.ATTACK, 0, 0, False)):
            with self.subTest(damage_class=damage_class, owner=owner):
                self.assertIs(K.from_evolved_opponent(res, Incoming(player, source, damage_class, AttackKey(CHARMELEON, 0)), owner), expected)
        with self.assertRaises(RuntimeError):
            K.source_evolved(res, Incoming(1, source, DamageClass.ATTACK, AttackKey(CHARMELEON, 0)))  # 発生元の持ち主が使い手と違う

    def test_pre_frame_checks_pass_the_coming_origin(self):
        """子の枠を開く前の判定も、これから起こす処理の発生元を渡す: カイリキーの［はんげき］は特殊能力の分類・カイリキーの持ち主、「うら」が出るまでのコインの先読みの返す効果は
        返す側（わるいカメールとその持ち主・ワザの分類）。"""
        seen = []
        original = K.first_void

        def spy(res, incoming, owner, pokemon, *args, **kw):
            seen.append((incoming, owner, pokemon.pokemon_id))
            return original(res, incoming, owner, pokemon, *args, **kw)

        state = board(mon(MEW, (PS,)), opponent=mon(MACHAMP, (FT,)))
        with mock.patch.object(K, "first_void", spy):
            attack(state, 0, TL)
        machamp, mew = pid(state, MACHAMP, 1), pid(state, MEW, 0)
        self.assertIn((Incoming(1, machamp, DamageClass.POWER, AttackKey(MEW, 0)), 0, mew), seen)
        seen.clear()
        state = board(mon(QWILFISH, (W, W)), opponent=mon(DARK_WARTORTLE, (W,), retaliation_received=TURN - 1))
        with mock.patch.object(K, "first_void", spy), self.assertRaises(UnsupportedError):
            attack(state, 1, HD, TL)  # 上限なしのコインでわるいカメールがきぜつしうるうえ、返すダメージでハリーセンもきぜつしうる（既存の W24。先読みの組を作ったあとで止まる）
        wartortle, qwilfish = pid(state, DARK_WARTORTLE, 1), pid(state, QWILFISH, 0)
        self.assertIn((Incoming(1, wartortle, DamageClass.ATTACK, AttackKey(DARK_WARTORTLE, 1)), 0, qwilfish), seen)


# ---------------------------------------------------------------- 4 章: コインと残る要素


class CoinTest(unittest.TestCase):
    def test_coin_deciding_a_valid_element_is_flipped(self):
        """ライチュウのかみなり: 60 は無効。コインは有効な自分への 30 を決めるので投げ直さずに投げる（「うら」なら 30、「おもて」なら何もない）。"""
        state = board(mon(RAICHU, (L,) * 4), opponent=mon(MEW, (PS,)))
        for side, own in ((TL, 30), (HD, 0)):
            with self.subTest(side=side):
                after = attack(state, 1, side)
                self.assertEqual(len(new_events(state, after, "coin_flip")), 1)
                self.assertEqual((after.players[0].active.damage, after.players[1].active.damage), (own, 0))

    def test_coins_deciding_only_voided_elements_keep_the_existing_questions(self):
        """無効な要素だけを決めるコインは既存の問い: スターミーのスターフリーズ（マヒだけ。HC3）・ゴローンのれんぞくいわなげ（「うら」が出るまでの量。v0.4b）。隣の例: ねむりのミュウ・
        たねのハリーセンなら投げて進む。"""
        rejects(self, board(mon(STARMIE, (W,) * 3), opponent=mon(MEW, (PS,))), UseAttack(0, 1), HC3)
        rejects(self, board(mon(GRAVELER_ES2, (FT, FT)), opponent=mon(MEW, (PS,))), UseAttack(0, 0), PREVENTED_COIN)
        asleep = board(mon(STARMIE, (W,) * 3), opponent=mon(MEW, (PS,), sleep=True))
        self.assertEqual([e["amount"] for e in damages(asleep, attack(asleep, 1, HD))], [20])
        state = board(mon(QWILFISH, (W, W)), opponent=mon(MEW, (PS,)))
        after = attack(state, 1, HD, TL)
        self.assertEqual([e["amount"] for e in damages(state, after)], [20])

    def test_field_wide_effect_keeps_dw2(self):
        """ナツメのゲンガーのやみのはどう（お互いの場の特殊能力を止める）: ワザの効果を受けないポケモンがいるので既存の DW2。ねむりのミュウなら進む。"""
        rejects(self, board(mon(SABRINAS_GENGAR_GD6, (PS, PS)), opponent=mon(MEW, (PS,))), UseAttack(0, 0), "UNRESOLVED_DARK_WAVE_PROTECTED_POKEMON")
        state = board(mon(SABRINAS_GENGAR_GD6, (PS, PS)), opponent=mon(MEW, (PS,), sleep=True))
        self.assertEqual([e["amount"] for e in damages(state, attack(state, 0))], [40])


# ---------------------------------------------------------------- 4 章: 共通の問い合わせ（先読み・除く範囲・JS1・記録）


class SharedQueryTest(unittest.TestCase):
    def test_preflight_modes_agree(self):
        """宣言の前の確認の方法（``derived``・``derived_full``・比べる方法 ``legacy``）のどれでも同じ答え。v0.13 の止める関数は発生元を知らないので、ミュウが場にいれば ``legacy`` でも
        すべての結果を試す（``legacy_unknown_features``）。"""
        state = board(mon(CHARMELEON, (F_,) * 3), opponent=mon(MEW, (PS,)))
        results = {mode: snap(apply_kernel(state, UseAttack(0, 0), preflight=mode)) for mode in ("derived", "derived_full", "legacy")}
        self.assertEqual(len({repr(v) for v in results.values()}), 1)
        self.assertIn("ニュートラルシールド", F.legacy_unknown_features(state, state.players[0].active))
        plain = board(mon(CHARMELEON, (F_,) * 3), opponent=mon(RATTATA))
        self.assertNotIn("ニュートラルシールド", F.legacy_unknown_features(plain, plain.players[0].active))

    def test_effect_excluding_attacks_treat_it_as_held_by_mew(self):
        """スピードスター（タケシのサンドパン。1 進化）は受けるポケモン自身の持っている効果を除くので、ミュウ自身の力を当てはめず 20 を受ける（SS1 の読み方のまま）。だましうちの FA1 の
        3 つの読み方でも、受けるポケモン自身の力はどれでも除かれ、違いは生まれない（余分な停止を作らない）。"""
        state = board(mon(BROCKS_SANDSLASH, (FT, FT)), opponent=mon(MEW, (PS,)))
        after = attack(state, 0)
        self.assertEqual([(e["amount"], e.get("ignore_defender_effects")) for e in damages(state, after)], [(20, True)])
        umbreon = board(mon(UMBREON, (W, W, W)), opponent=mon(MEW, (PS,)))
        res, fs = frame_res(umbreon, umbreon.players[0].active.pokemon_id, AttackKey(UMBREON, 1))
        mew = umbreon.players[1].active
        self.assertIs(K.first_void(res, K.incoming_of(fs), 1, mew).definition, C.NEUTRAL_SHIELD)
        self.assertIsNone(K.first_void(res, K.incoming_of(fs), 1, mew, held_by_receiver=False))
        self.assertIsNone(K.ignored_effects_scope_difference(res, fs, umbreon.players[0].active, 1, mew, E.OPPONENT_ACTIVE, 30))

    def test_js1_comparison_uses_the_same_answer(self):
        """控えへのダメージの弱点・抵抗力の比べ（JS1）: 進化ポケモン（ナツメのゲンガー。超）から控えのミュウ（弱点 超）へのダメージは無効なので比べない。たね（スリープ）からなら比べる。"""
        for attacker, expected in ((mon(SABRINAS_GENGAR_GD6, (PS, PS)), False), (mon(DROWZEE, (PS,)), True)):
            with self.subTest(attacker=attacker["card"]):
                state = board(attacker, opponent=mon(RATTATA), opponent_bench=(mon(MEW),))
                source = state.players[0].active
                res, fs = frame_res(state, source.pokemon_id, AttackKey(attacker["card"], 0))
                self.assertIs(K.weakness_resistance_matters(res, fs, E.OPPONENT_BENCH, 10, pid(state, MEW, 1)), expected)

    def test_received_records_are_attack_barriers(self):
        """受けた記録（オウムがえしが読む）: ワザのダメージと効果を受けなかったことは「ワザをうけない」（``attack_barrier``）。ダメージだけの無効と取り違えない。"""
        state = board(mon(CHARMELEON, (F_,) * 3), bench=(mon(PIDGEOTTO),), opponent=mon(MEW, (PS,)))
        after = attack(state, 0)
        (record,) = after.players[1].active.history
        self.assertEqual((record.voided, record.reached, record.damage), ((("damage", "attack_barrier"),), (), 0))
        state = board(mon(ERIKAS_DRAGONAIR, (W,) * 4), bench=(mon(PIDGEOTTO),), opponent=mon(MEW, (PS,)))
        after = attack(state, 1)
        (record,) = after.players[1].active.history
        self.assertEqual(record.voided, (("return_in_play_to_deck", "attack_barrier"),))


# ---------------------------------------------------------------- 4.3 節: 決定・保存・場をはなれた発生元


class DecisionAndCopyTest(unittest.TestCase):
    def test_source_left_play_in_the_element(self):
        """エリカのハクリュー（1 進化）のつれさる: 自分を先に山札にもどしてから相手の対戦ポケモンを評価する。はなれたあとも、要素を始めたときの今の姿（1 進化）でミュウを守る。続く
        バトル場に出す決定を、複製・deepcopy・pickle から同じ答えで同じ結果にし、無効・山札にもどすログを重ねない。"""
        state = board(mon(ERIKAS_DRAGONAIR, (W,) * 4), bench=(mon(RATTATA),), opponent=mon(MEW, (PS,)))
        pending = attack(state, 1)
        self.assertEqual(shielded(state, pending), [("effect_prevented", pid(state, MEW, 1), 0, pid(state, ERIKAS_DRAGONAIR, 0), "return_in_play_to_deck")])
        self.assertIsNone(pending.find_pokemon(pid(state, ERIKAS_DRAGONAIR, 0)))
        self.assertEqual(pending.cards[pending.players[1].active.card].card_id, MEW)
        self.assertEqual(pending.decision.kind, "promote_active")
        after = settle(same_answers(self, pending, pending.decision.options[:1]))
        self.assertEqual(len(voids(state, after)), 1)
        self.assertEqual(len(new_events(state, after, "return_in_play_to_deck")), 1)
        audited(self, after)

    def test_resumed_decision_after_a_prevented_element(self):
        """無効にした要素のあとの決定（かいてんひこうできぜつしたコラッタのサイドを取る）を、同じ答えで同じ結果にする。無効のログは 1 回だけ。"""
        state = board(mon(BROCKS_GOLBAT, (G,) * 3), opponent=mon(RATTATA, damage=20), opponent_bench=(mon(MEW),))
        pending = attack(state, 1)
        self.assertEqual(pending.decision.kind, "take_prize")
        after = settle(same_answers(self, pending, pending.decision.options[:1]))
        self.assertEqual(len(shielded(state, after)), 1)
        audited(self, after)

    def test_rejections_do_not_change_the_state(self):
        """拒否されるコマンド（ミュウの特殊能力の宣言・決定への正しくない答え）は、状態・ログ・乱数・決定を変えない。"""
        state = board(mon(ERIKAS_DRAGONAIR, (W,) * 4), bench=(mon(RATTATA),), opponent=mon(MEW, (PS,)))
        pending = attack(state, 1)
        rejects(self, pending, ResolveDecision(0, pending.decision.id, (999,)), "INVALID_CHOICE", error=IllegalActionError)
        rejects(self, _turn_of(board(mon(RATTATA), opponent=mon(MEW, (PS,))), 1), lambda s: UsePokemonPower(1, s.players[1].active.pokemon_id, 0),
                "POWER_NOT_DECLARABLE", error=IllegalActionError)

    def test_snapshots_have_no_new_fields(self):
        state = board(mon(CHARMELEON, (F_,) * 3), opponent=mon(MEW, (PS,)))
        after = attack(state, 0)
        for other in (after.clone(), copy.deepcopy(after), pickle.loads(pickle.dumps(after))):
            self.assertEqual(snap(other), snap(after))


# ---------------------------------------------------------------- 9 章: 見つけた既存の不具合（トレーナーの使用中に対戦が終わる）


class GameEndDuringTrainerTest(unittest.TestCase):
    """v0.102 までは、トレーナーの効果の途中で使った特殊能力（ポケモン育て屋さんで進化させたゲンガー PR1-053 の［やみのちから］）で相手の場にポケモンがいなくなると、使用中の
    トレーナーを残したまま対戦が終わり、不変条件の違反（内部エラー）で止まった（v0.103 の対戦の M103 対 S87 で見つけた。ミュウのない盤面で、固定した v0.102 の木でも同じ）。"""

    @staticmethod
    def breeder(opponent_bench=()):
        state = board(mon(RATTATA), bench=opponent_bench, opponent=mon(FOSSIL_GASTLY, (PS,)), opponent_bench=(mon(RATTATA),),
                      opponent_hand=[BREEDER, GENGAR_PR1], current=1, turn=TURN + 1)
        state = with_coin_results(state, HD)
        state = apply_kernel(state, PlayTrainer(1, state.players[1].hand[0]))
        while state.decision is not None and state.decision.player == 1:
            d = state.decision
            state = apply_kernel(state, ResolveDecision(1, d.id, tuple(d.options[:max(1, d.min_choices)])))
        return state

    def test_game_end_discards_the_trainer_in_use(self):
        after = self.breeder()
        self.assertIs(after.phase, Phase.GAME_OVER)
        self.assertEqual((after.trainer_in_use, after.trainer_stack), (None, ()))
        self.assertEqual([e["kind"] for e in after.log[-3:]], ["return_in_play_to_hand", "discard_trainer", "game_end"])
        self.assertIn(BREEDER, [after.cards[uid].card_id for uid in after.players[1].discard])
        audited(self, after)

    def test_with_a_bench_the_order_is_unchanged(self):
        """隣の例: 相手にベンチがあれば対戦は終わらず、v0.102 と同じく、相手のバトル場に出す決定のあとにトレーナーをトラッシュする（使用中のあいだの決定の扱いは変えない）。"""
        pending = self.breeder(opponent_bench=(mon(RATTATA),))
        self.assertEqual((pending.decision.kind, pending.decision.player), ("promote_active", 0))
        self.assertIsNotNone(pending.trainer_in_use)
        after = apply_kernel(pending, ResolveDecision(0, pending.decision.id, pending.decision.options[:1]))
        self.assertEqual([e["kind"] for e in after.log[len(pending.log):] if e["kind"] in ("promote_active", "discard_trainer")][-1], "discard_trainer")
        self.assertIsNone(after.trainer_in_use)
        audited(self, after)


# ---------------------------------------------------------------- 6 章: 監査


class AuditTest(unittest.TestCase):
    """ログの監査（tests/log_audit.py の ``v103_problems``・``v103_received``）は、エンジンの ``first_void``・``from_evolved_opponent`` を読まずにログから組み立てた場で確かめる。
    エンジンの判定を一時的に誤らせた正式な開始からの対戦（tools/existing_effect_games.py の F30 対 M103・M103 対 W45。seed 0）で、監査がそれを見つける。"""

    @staticmethod
    def problems(fake):
        from tools import existing_effect_games as games

        found = []
        with mock.patch.object(K, "from_evolved_opponent", fake):
            for labels in (("F30", "M103"), ("M103", "W45")):
                state = games.play(labels, 0, keep_state=True).get("state")
                if state is not None:
                    found += [problem for problem in log_problems(state) if "ニュートラルシールド" in problem]
        return found

    def test_audit_finds_a_missing_void(self):
        """相手の進化ポケモンのワザなのに、エンジンが無効にしない。"""
        self.assertTrue([p for p in self.problems(lambda *a, **k: False) if "受けた" in p])

    def test_audit_finds_a_wrong_void(self):
        """たねポケモンのワザ・自分のワザも、エンジンが無効にする。"""
        found = self.problems(lambda *a, **k: True)
        self.assertTrue([p for p in found if "進化ポケモンではない" in p or "受けるポケモンの持ち主のワザ" in p])


class DocumentTest(unittest.TestCase):
    def test_document_names_the_shared_query(self):
        text = DOC.read_text(encoding="utf-8")
        for needle in ("Incoming", "first_void", "from_evolved_opponent", "source_evolved", "EvolvedOpponentAttackImmunity", "NEUTRAL_SHIELD", "form_def",
                       "SOURCE_LEFT_CODE", "HC3", "SS1", "FA1", "JS1", "TF1", "c315123", "73a1690", "Confused"):
            self.assertIn(needle, text)


if __name__ == "__main__":
    unittest.main()

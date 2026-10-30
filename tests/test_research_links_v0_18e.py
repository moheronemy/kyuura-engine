"""v0.18e: 研究の対応表（kyuura_engine/data/research_links.json）と、エンジンの停止コード・問い・登録・照合の記録が合うこと。
docs/research-alignment-v0.18a.md・docs/verification-reproducibility-v0.18e.md。

kyuura（研究の正本）の記録そのものは写さず、id の対応だけを持つ。ここでは kyuura がなくても確かめられること（エンジンの側の集合と対応表が
同じ）を確かめ、../kyuura があれば ``scripts/check_research_links.py`` で kyuura の研究の基準のコミットの記録とも照らす。

停止コード・登録を加えたのに対応表に書かないと失敗する（エンジンから研究の id を引けなくなるのを防ぐ）。kyuura の記録 id: engine_unresolved_index・
UQ-…・CR-…・LD-…・CC-…（v0.18 は kyuura adf9710。2026-10-15 の照合の記録の取り込みのあとは kyuura 3f34908。docs/verified-record-reuse.md）。
"""

from __future__ import annotations

import json
import pathlib
import re
import subprocess
import unittest

from kyuura_engine import effects as E
from kyuura_engine.cards import read_extract, read_verification
from kyuura_engine.resolution import questions

ROOT = pathlib.Path(__file__).resolve().parent.parent
LINKS = json.loads((ROOT / "kyuura_engine" / "data" / "research_links.json").read_text(encoding="utf-8"))
KYUURA = ROOT.parent / "kyuura"


def engine_stop_codes() -> set[str]:
    """エンジンの中の ``UNRESOLVED_…``（既定の UNRESOLVED_RULING を除く。tests/test_unresolved_boundaries_v0_4e.py の数え方と同じ）。"""
    codes = set()
    for path in (ROOT / "kyuura_engine").rglob("*.py"):
        codes |= set(re.findall(r"\bUNRESOLVED_[A-Z_]+[A-Z]\b", path.read_text(encoding="utf-8")))
    return codes - {"UNRESOLVED_RULING"}


def registered_targets() -> set[str]:
    registry = E.DEFAULT_EFFECTS
    found = {f"{k.card_id}/attack/{k.attack_index}" for k in registry.attack_keys()
             if registry.attack_entry(k.card_id, k.attack_index).play_text_ja is not None}
    found |= {f"{k.card_id}/power/{k.power_index}" for k in registry.power_keys()
              if getattr(registry.power_entry(k.card_id, k.power_index), "play_text_ja", None) is not None}
    # v0.73: トレーナーの処理に使う文面を kyuura のエラッタ（ERR-・TXT-・RUL-）にした登録（超エネルギー回収。研究の対応表の errata_text の <カード id>/trainer）
    found |= {f"{card}/trainer" for card in registry.trainer_ids()
              if (registry.trainer_entry(card).source or "").split("-")[0] in ("ERR", "TXT", "RUL")}
    return found


def all_engine_rulings():
    for entry in LINKS["stop_codes"].values():
        yield from entry["engine_rulings"]
    for entry in LINKS["codeless_questions"].values():
        yield from entry["engine_rulings"]
    for section in ("unresolved_without_code", "deferred_card_questions", "implementation_assumptions_with_issue"):
        for entry in LINKS[section]:
            yield from entry["engine_rulings"]


class ResearchLinksTest(unittest.TestCase):
    def test_commits(self):
        """研究の基準（kyuura 3f34908。2026-10-15 に adf9710 から上げた。docs/verified-record-reuse.md）とカードの写しの元（ecb2d69）を
        分けて持つ。写しの元は同梱の写しのコミットと同じ。"""
        self.assertRegex(LINKS["research_commit"], r"^[0-9a-f]{40}$")
        # v0.69: 研究の基準を kyuura 7d3f4ca（v0.68 までのエンジンの記録を取り込んだコミット。kyuura の main）に上げ、写しの元も同じコミットにした
        # （docs/equivalent-non-pack-cards-v0.69.md 7 章）。v0.68 までは研究の基準 3f34908・写しの元 ecb2d69 を分けて持っていた
        # v0.97: 研究の基準と写しの元を kyuura 73a1690（研究 78d090c を取り込んだ main の PR #5 のマージ。木は 78d090c と同じ）に上げた（docs/unown-research-idfnj-v0.97.md 2 章・3 章）
        # v0.114: 研究の基準と写しの元を kyuura e519b99（ブランチ claude/baby-data-engine-v0113-handover の固定コミット。親は 73a1690）に上げた（docs/baby-rules-evolution-v0.114.md 2 章）
        # v0.121: 研究の基準と写しの元を kyuura 2fe0bc0（ブランチ claude/neo2-fossil-type-cost-checks の固定コミット。親は 7b03fd9、研究 c932625 を含む）に上げた（docs/hand-bench-attack-conditions-v0.121.md 3 章）
        self.assertEqual(LINKS["research_commit"], "2fe0bc042ce187d191843819262f8036abbb343d")
        self.assertEqual(LINKS["engine_import_id"], "ENGINE-46A3E2E")
        self.assertEqual(LINKS["card_data_commit"], read_extract()["source"]["commit"])
        self.assertEqual(LINKS["research_commit"], LINKS["card_data_commit"])

    def test_every_stop_code_is_linked(self):
        """エンジンの停止コードの集合と、対応表の停止コードの集合が同じ（v0.30 までの 22 件 + v0.31 の 15 件 + v0.32 の 1 件 + v0.34 の 2 件 + v0.36 の 2 件 + v0.37 の 1 件 + v0.38 の 1 件 + v0.39 の 1 件 + v0.40 の 1 件 + v0.41 の 1 件 + v0.42 の 2 件 + v0.43 の 2 件 + v0.44 の 2 件 + v0.45 の 2 件 + v0.46 の 2 件 + v0.47 の 4 件 + v0.48 の 3 件 + v0.49 の 11 件 + v0.50 の 5 件 + v0.51 の 2 件 + v0.52 の 3 件 + v0.53 の 2 件 + v0.55 の 8 件 + v0.56 の 6 件 + v0.57 の 8 件 + v0.58 の 6 件 + v0.59 の 7 件 + v0.60 の 1 件 + v0.61 の 5 件 = 128 件）。論点のないものは kyuura の
        処理が out_of_scope。kyuura にまだ記録がない停止コードは not_in_kyuura（v0.21 の突風の UNRESOLVED_GUST_WITHOUT_OPPONENT_BENCH・v0.22 の
        パソコン通信の UNRESOLVED_COMPUTER_SEARCH_EMPTY_DECK・v0.23 のエネルギー回収の 2 件・v0.31 の HC1〜HC10 の 10 件・v0.32 の CD4・v0.34 の TP3・NK5・v0.36 の AC6・RD9・v0.37 の JS1・v0.38 の GK1・v0.39 の GS1・v0.40 の SG1・v0.41 の CX1・v0.42 の PW1・PW2・v0.43 の PW3・PW4・v0.44 の FC1・TR1・v0.45 の GV1・AC13・v0.46 の CP1・CP2・v0.47 の PF1・PF2・PF3・KA1・v0.48 の VS1・PG1・MH1・v0.49 の TE1・TF1・TF2・DG1〜DG3・VA1・RC1〜RC4・v0.50 の DV1〜DV5・v0.51 の RV1・FT1・v0.52 の FJ1・SU1・SU2・v0.53 の ST1・NG1・v0.55 の MW1・EM1・SP1・FH1・GL1・GL2・SB1・SB2・v0.56 の LS1・RT1・RG1・MY1・MS1・KG1・v0.57 の STB1・TG1・FG1・FG2・EX1・VG1・VM1・CH1。kyuura への報告事項）。
        v0.31 で、v0.30 まで起こらなかった（コードのない）5 件（T27・C34/C35・G40・P19・P32）が複数のポケモンにダメージを与えるワザで起こるように
        なったので停止コードにした。kyuura の論点（UQ-）はそのまま（kyuura の未解決の一覧ではコードのない行なので、``kyuura_index_engine_key`` で
        行を指す。scripts/check_research_links.py）。"""
        self.assertEqual(set(LINKS["stop_codes"]), engine_stop_codes())
        self.assertEqual(len(LINKS["stop_codes"]), LINKS["counts"]["engine_stop_codes"])
        not_in_kyuura = set()
        unindexed = set()  # v0.97: kyuura に論点はあるが、kyuura の未解決の一覧（v0.68 までの取り込み）にコードの行がない停止コード（issue_not_in_index）
        for code, entry in LINKS["stop_codes"].items():
            with self.subTest(code=code):
                if entry["kyuura_disposition"] == "not_in_kyuura":
                    self.assertIsNone(entry["kyuura_issue"])
                    not_in_kyuura.add(code)
                elif entry["kyuura_disposition"] == "issue_not_in_index":
                    self.assertIsNotNone(entry["kyuura_issue"])
                    unindexed.add(code)
                else:
                    self.assertEqual(entry["kyuura_disposition"], "issue" if entry["kyuura_issue"] else "out_of_scope")
        # v0.69: kyuura が、v0.68 までのエンジンの記録を取り込んで、not_in_kyuura だった停止コード 123 件をすべて論点（UQ-）に結んだ（kyuura の未解決の一覧。
        # docs/equivalent-non-pack-cards-v0.69.md 7 章）。v0.72 で加えた FH2・PD2 は kyuura の一覧にまだないので not_in_kyuura（kyuura への報告事項。同じ形の論点は
        # UQ-CARD-USE-WITHOUT-TARGET・UQ-UP-TO-ZERO-CHOICE。docs/status-coins-effect-reuse-v0.72.md）
        # v0.73 で加えた MR1・ML1・SR1・SR2・FV1 も kyuura の一覧にない（docs/search-recovery-trainers-v0.73.md 6 章）
        self.assertEqual(not_in_kyuura, {"UNRESOLVED_FULL_HEAL_WITHOUT_CONDITION", "UNRESOLVED_POKEDEX_UP_TO_ZERO",
                                         "UNRESOLVED_MAX_REVIVE_WITHOUT_TARGET", "UNRESOLVED_MASTER_BALL_SHORT_DECK",
                                         "UNRESOLVED_SUPER_ENERGY_RETRIEVAL_WITHOUT_TARGET", "UNRESOLVED_SUPER_ENERGY_RETRIEVAL_ZERO_CHOICE",
                                         "UNRESOLVED_FERVOR_RAINBOW_ENERGY",
                                         # v0.74 で加えた RS1・LK1・EN1・NJ1・PT1 も kyuura の一覧にない（docs/remaining-stadiums-v0.74.md 7 章）
                                         "UNRESOLVED_STADIUM_REUSE_AFTER_REPLACEMENT", "UNRESOLVED_LUCKY_STADIUM_UNSTATED_REPEAT",
                                         "UNRESOLVED_ENERGY_STADIUM_WITHOUT_TARGET", "UNRESOLVED_NINJA_GYM_WITHOUT_TARGET",
                                         "UNRESOLVED_POKEMON_TOWER_TRAINER_WITHOUT_EFFECT",
                                         # v0.75 で加えた RB5・DB1 も kyuura の一覧にない（docs/search-energy-pokemon-v0.75.md 5 章）
                                         "UNRESOLVED_RAINBOW_RECOVER_AS_TYPE", "UNRESOLVED_DOUBLED_DAMAGE_POWER_DAMAGE",
                                         "UNRESOLVED_METAL_ENERGY_POWER_ORDER", "UNRESOLVED_DARKNESS_DAMAGE_RECEIVED_POWER",
                                         # v0.79 で加えた PK1 も kyuura の一覧にない（docs/shared-checks-pokemon-reuse-v0.79.md 2 章）
                                         "UNRESOLVED_POKEMON_CHECK_MID_KNOCKOUT",
                                         # v0.80 で加えた 9 件も kyuura の一覧にない（docs/neo-trainer-components-v0.80.md 7 章）
                                         "UNRESOLVED_SUPER_ROD_WITHOUT_TARGET", "UNRESOLVED_TRAINER_UP_TO_ZERO_CHOICE",
                                         "UNRESOLVED_TRAINER_UP_TO_WITHOUT_TARGET", "UNRESOLVED_DECK_TOP_SHORT", "UNRESOLVED_HAND_TRAINER_LOCK_BORROW",
                                         "UNRESOLVED_DEVOLUTION_SPRAY_HYPER_WITHOUT_TARGET", "UNRESOLVED_MOOMOO_MILK_UNDAMAGED_TARGET",
                                         "UNRESOLVED_ALL_PURPOSE_POWDER_WITHOUT_TARGET", "UNRESOLVED_HEALING_FIELD_WITHOUT_DAMAGE",
                                         "UNRESOLVED_POKEMON_CHECK_BERRY_ORDER", "UNRESOLVED_BALLOON_BERRY_FAILED_RETREAT", "UNRESOLVED_FOCUS_BAND_TIMING",
                                     "UNRESOLVED_MAX_HP_SET_AND_INCREASE",  # v0.81a: MH2
                                 "UNRESOLVED_REFLECT_SHIELD_TIMING", "UNRESOLVED_ATTACK_DECK_TOP_SHORT",  # v0.83: RS1・LT1
                                 # v0.84: RF1・WD1・WD2（docs/light-powers-evolution-v0.84.md 7 章）
                                 "UNRESOLVED_REFLECT_SHIELD_OVERLAP", "UNRESOLVED_MIRACULOUS_WIND_CONVERTED_ENERGY",
                                 "UNRESOLVED_MIRACULOUS_WIND_ENERGY_BURN",
                             # v0.85: MEC1・MEW1（docs/entry-powers-energy-lifecycle-v0.85.md 7 章）
                             "UNRESOLVED_MIRACLE_ENERGY_AS_TYPE", "UNRESOLVED_MIRACLE_ENERGY_UNDER_WIND",
                             # v0.86: RA1・RA2・OT1・BT1・PL1・SO1（docs/entry-energy-evolution-reactions-v0.86.md 8 章。CV1 は v0.97 から issue_not_in_index）
                             "UNRESOLVED_REACTION_AFTER_KNOCKOUT", "UNRESOLVED_REACTION_CONDITION_CHANGED",
                             "UNRESOLVED_HOWL_OUTSIDE_OWN_TURN",
                             "UNRESOLVED_BOLT_DURING_OWN_ATTACK", "UNRESOLVED_PROTECTIVE_FLAME_SCOPE",
                             "UNRESOLVED_SOLAR_POWER_WITHOUT_CONDITION",
                             # v0.87: HP1・MG1・MG2・SB1（docs/movement-damage-reactions-v0.87.md 9 章）
                             "UNRESOLVED_HOT_PLATE_FACE_DOWN", "UNRESOLVED_STRANGE_GAS_NEW_POKEMON", "UNRESOLVED_STRANGE_GAS_PROTECTED_POKEMON",
                             "UNRESOLVED_POWER_DAMAGE_PREVENTED",
                             # v0.88: CE1・CE2・CE3（docs/type-energy-colors-v0.88.md 4 章）
                             "UNRESOLVED_COLOR_EFFECT_CONTINUATION", "UNRESOLVED_COLOR_REPLACEMENT_ORDER", "UNRESOLVED_COLOR_CHANGED_ENERGY_CARD",
                             # v0.89: FA1（docs/selected-target-damage-v0.89.md 4.3 節）
                             "UNRESOLVED_IGNORED_EFFECTS_SCOPE",
                             # v0.90: CM1・KR1（docs/markers-counters-v0.90.md 6 章・7 章）
                             "UNRESOLVED_COLOR_MARKER_PRECEDENCE", "UNRESOLVED_FULL_RECOVERY_COUNTERS",
                             # v0.91: KK1・HR1・HX1・ZC1・ZC2・ZC3（docs/marker-check-field-reset-v0.91.md 9 章）
                             "UNRESOLVED_POKEMON_CHECK_CHAR_COIN_ORDER", "UNRESOLVED_LIGHTNING_BOLT_DEFENDER_UNITS", "UNRESOLVED_HYPER_TEXTURE_UNMARKED_TARGET",
                             "UNRESOLVED_ALL_CLEAR_OTHER_EFFECTS", "UNRESOLVED_ALL_CLEAR_ATTACK_SOURCE", "UNRESOLVED_ALL_CLEAR_FOSSIL_IN_PLAY",
                             # v0.92: DW1・DW2・DW3・ML2（docs/power-suppression-lasting-locks-v0.92.md 10 章）
                             "UNRESOLVED_DARK_WAVE_NEW_POKEMON", "UNRESOLVED_DARK_WAVE_PROTECTED_POKEMON", "UNRESOLVED_DARK_WAVE_KNOCKED_OUT_POWER",
                             "UNRESOLVED_MEAN_LOOK_SOURCE_EVOLVED",
                             # v0.93: AL1・AL2・AL3・JC1・JC2・CJ1（docs/active-leave-locks-v0.93.md 10 章）
                             "UNRESOLVED_LEAVE_LOCK_KNOCKOUT", "UNRESOLVED_LEAVE_LOCK_NO_EFFECT", "UNRESOLVED_LEAVE_LOCK_SCRAM", "UNRESOLVED_JAW_CLAMP_SOURCE_RETURNED",
                             "UNRESOLVED_JAW_CLAMP_SOURCE_EVOLVED", "UNRESOLVED_CLAMPING_JAW_SOURCE_DEVOLVED",
                             # v0.96: EG1・OB1（docs/unown-family-powers-v0.96.md 9 章）
                             "UNRESOLVED_ENGAGE_EMPTY_HAND", "UNRESOLVED_POWER_DECK_TOP_SHORT",
                             # v0.98: BE1・BE2・VN1（docs/unown-bear-yield-vanish-give-v0.98.md 7 章。BE2・VN1 は UQ-CARD-USE-WITHOUT-TARGET と同じ形だが、kyuura の事例にない）
                             "UNRESOLVED_POWER_COUNTER_MOVE_TO_SAME_POKEMON", "UNRESOLVED_POWER_COUNTER_MOVE_WITHOUT_COUNTERS",
                             "UNRESOLVED_POWER_RETURN_WITHOUT_TARGET",
                             # v0.99: PFM1（docs/unown-perform-help-history-v0.99.md 7 章）
                             "UNRESOLVED_PERFORM_DAMAGE_PLACES",
                             # v0.100: SK1・SK2・PSG1（docs/sketch-perish-song-history-v0.100.md 8 章。SK2・PSG1 は UQ-COPIED-ATTACK と近い形だが、kyuura の事例にない）
                             "UNRESOLVED_SKETCH_PRESENCE", "UNRESOLVED_SKETCH_COPIED_ATTACK", "UNRESOLVED_PERISH_SONG_RECEIVED_ATTACK",
                             # v0.101: KP1・KP2・KP3（docs/counter-keep-energy-protection-v0.101.md 8 章。KP1 は UQ-TARGET-WITHOUT-EFFECT、KP2 は UQ-COIN-IN-NULLIFIED-ELEMENT と
                             # 同じ形だが、kyuura の事例にない）
                             "UNRESOLVED_KEEP_PROTECTED_TARGET", "UNRESOLVED_KEEP_VOIDED_DISCARD_COIN", "UNRESOLVED_KEEP_DETACHED_ENERGY_DISCARD",
                             # v0.109: GO1（docs/timed-damage-guards-v0.109.md 5 章。受けるときのコインで受けないと決める効果の重なり。RF1 と同じ形だが、kyuura の事例にない）
                             "UNRESOLVED_DAMAGE_GUARD_OVERLAP",
                             # v0.110: KS1・KS2（docs/endure-armor-up-v0.110.md 5 章。「きぜつ」しない効果の残りHPを「10」にする時点と、きぜつの判定の効果との順番。FB1・G40 と近い形だが、
                             # kyuura の事例にない）
                             "UNRESOLVED_KO_SURVIVAL_TIMING", "UNRESOLVED_KO_SURVIVAL_OVERLAP",
                             # v0.114: BX1・HP2・HV1（docs/baby-rules-evolution-v0.114.md 10 章。ベイビィの姿のメタモン・［ヒートプレート］とベイビィの進化・特殊能力の消えたポケモンの
                             # 「特殊能力」を持っているか。kyuura の事例にない）
                             "UNRESOLVED_TRANSFORM_BABY", "UNRESOLVED_HOT_PLATE_BABY_EVOLUTION", "UNRESOLVED_STOPPED_POWER_HOLDER",
                             # v0.115: RKB1・SLD1（docs/spread-damage-allocation-v0.115.md 10 章。ロックブラストの「最大5枚トラッシュ」の 0 枚は UQ-UP-TO-ZERO-CHOICE と同じ形だが、
                             # kyuura の事例にない。いしなだれで相手の対戦ポケモンを選ぶ扱いは kyuura に対応する記録がない）
                             "UNRESOLVED_DISCARD_UP_TO_ZERO", "UNRESOLVED_CHOSEN_ACTIVE_EXTRA_DAMAGE",
                             # v0.116: AT1（docs/energy-movement-attachment-devolution-v0.116.md 10 章。しこみどく・エナジーショックの「ついたとき」に場のつけ替え・［エネエネ］が当たるか。
                             # v0.59 の CB1 と同じ形の問いだが、kyuura の事例にない）
                             "UNRESOLVED_ATTACH_TRIGGER_SCOPE",
                             # v0.117: RR1・QK1・TW1・TW2・LB1・LB2・VH1・ES4（docs/retreat-return-active-powers-v0.117.md 10 章。にげる時の反応の時点・［QUICKEN］の効果と発生源の力・
                             # ［ときわたり］の時点と重なり・［でんせつのからだ］のトレーナーの範囲とベトベトガス・ぱっときえるの行き先・場をはなれたESP。どれも kyuura の事例にない）
                             "UNRESOLVED_RETREAT_REACTION_TIMING", "UNRESOLVED_QUICKEN_EFFECT_SUPPRESSED", "UNRESOLVED_TIME_TRAVEL_TIMING",
                             "UNRESOLVED_TIME_TRAVEL_OVERLAP", "UNRESOLVED_LEGEND_BODY_TRAINER_TARGET", "UNRESOLVED_LEGEND_BODY_GOOP_GAS",
                             "UNRESOLVED_VANISH_OTHER_ATTACHED", "UNRESOLVED_ESP_LEFT_BEFORE_COIN",
                             # v0.118: HZ1・XP1・SX1・SX2・TN1（docs/unbounded-coins-heal-allocation-v0.118.md 10 章）
                             "UNRESOLVED_HEAL_UP_TO_ZERO", "UNRESOLVED_GROUP_POWER_COIN_ORDER", "UNRESOLVED_TIME_SHIFT_WITHOUT_TARGET",
                             "UNRESOLVED_STADIUM_REUSE_AFTER_RETURN", "UNRESOLVED_TRANSPORT_WITHOUT_CARDS",
                             # v0.119: AM1・HS1・PO1・PO2・PO3・PX1・IA1・AP1・AP2・MD1（docs/damage-reactions-poison-sleep-v0.119.md 10 章。どれも kyuura に対応する記録がない）
                             "UNRESOLVED_SHELL_ARMOR_TIMING", "UNRESOLVED_HARD_SHELL_NONPOSITIVE", "UNRESOLVED_POISON_CHANGE_ORDER",
                             "UNRESOLVED_POISON_MIST_EARLIER_POISON", "UNRESOLVED_POISON_MIST_SOURCE", "UNRESOLVED_SECRETE_POISON_TARGET",
                             "UNRESOLVED_SCARE_SUPPRESSION_CYCLE", "UNRESOLVED_DISCARD_PROTECTED_COIN", "UNRESOLVED_DISCARD_PROTECTED_POWER_USE",
                             "UNRESOLVED_COMMAND_DAMAGE_SCOPE",
                             # v0.120: EC1（docs/fossil-basic-virtual-attacks-v0.120.md 2 章。kyuura の UQ-ESP-REDO の ES0 は同じワザの 2 回のコイントスで、別の問い）
                             "UNRESOLVED_ESP_COPIED_ATTACK_COINS",
                             # v0.120: PE1・PE2・VP1・FE1・FE2・TF3（docs/fossil-basic-virtual-attacks-v0.120.md 10 章。どれも kyuura に対応する記録がない）
                             "UNRESOLVED_PRE_EVOLUTION_ATTACK_STAGE", "UNRESOLVED_PRE_EVOLUTION_ATTACK_CONDITIONS", "UNRESOLVED_PERMITTED_ATTACK_HELD",
                             "UNRESOLVED_REVIVED_BASIC_DEVOLVED", "UNRESOLVED_REVIVE_HAND_BASIC_ENTRY", "UNRESOLVED_TRANSFORM_REVIVED_BASIC"})
        # v0.97（docs/unown-research-idfnj-v0.97.md 3 章）: kyuura が調査で立てた UQ-SELF-EXCLUDING-POWER-COPIES の事例にわるいデンリュウ（neo4-046）の［かんでん］があるので、
        # CV1 を論点に結んだ（kyuura は v0.86 を取り込んでいないので、未解決の一覧に CV1 の行はない。kyuura の事例は kyuura_cases_without_engine_ruling で照らす）
        # v0.97 で加えた DF1・DF2 も、kyuura に論点（UQ-SELF-EXCLUDING-POWER-COPIES・UQ-NON-ATTACK-DAMAGE-MODIFIERS）はあるが、未解決の一覧に行がない
        # v0.114: BQ1（UQ-ATTACK-PRE-DAMAGE-COIN-ORDER のベイビィの事例）・NB1・NB2（UQ-NEO-TEXT-BABY-CATEGORIES）も、kyuura に論点と事例はあるが、未解決の一覧に行がない
        # v0.121: GN1（A0 では kyuura に記録がなく not_in_kyuura。研究の基準を 2fe0bc0 に上げて、kyuura の UQ-GROWL-NON-ATTACK-DAMAGE と IP1-040 の事例に結んだ。未解決の一覧に行はない）
        self.assertEqual(unindexed, {"UNRESOLVED_CONDUCTIVITY_MULTIPLE_SOURCES", "UNRESOLVED_SELF_EXCLUDING_POWER_COPIES", "UNRESOLVED_POWER_DAMAGE_RECEIVED_POWER",
                                     "UNRESOLVED_BABY_RULE_COIN_ORDER", "UNRESOLVED_NEO_TEXT_BASIC_BABY", "UNRESOLVED_NEO_TEXT_EVOLUTION_CARD_BABY",
                                     "UNRESOLVED_GROWL_NON_ATTACK_DAMAGE"})
        # v0.31〜v0.68 は、kyuura の一覧でコードのない行を指していた停止コード 8 件（T27・C34/C35・G40・P19・P32・Z9・DR8・DR13）に kyuura_index_engine_key を
        # 書いていた。v0.69 で kyuura が停止コードを書いたので外した（scripts/check_research_links.py が、kyuura の一覧のコードで照らす）
        # v0.97: SS1（v0.60 のコードのない問い。kyuura の一覧ではコードのない行）にコードを付けたので、その行を指す（v0.31 と同じ形）
        self.assertEqual({code: entry["kyuura_index_engine_key"] for code, entry in LINKS["stop_codes"].items() if "kyuura_index_engine_key" in entry},
                         {"UNRESOLVED_SPEED_STAR_SCOPE": "SS1"})
        self.assertEqual(LINKS["unresolved_without_code"], [])

    def test_codeless_questions_exist(self):
        """コードのない問い（Z9・Z22）は、問いの表（questions.QUESTIONS）にコードなしである。"""
        for name in LINKS["codeless_questions"]:
            with self.subTest(name=name):
                self.assertIn(name, questions.QUESTIONS)
                self.assertIsNone(questions.QUESTIONS[name].code)

    def test_every_question_is_linked_to_its_rulings(self):
        """問いの表のどの問いも、対応表に裁定 id（か版）ごと載っている。コードのある問いは停止コードの行、コードのない問いはコードのない問いか
        起こらない未解決の行。問いを加えたら対応表も直す。

        v0.31 の ``UNSUPPORTED_…`` のコードの問い（``copied_attack_unsupported``。エンジンが表せないワザをまねるとき）は裁定の未解決ではなく
        エンジンの対応の範囲なので、停止コードの行には載せない（docs/held-cards-v0.31.md）。"""
        def ids(rulings):
            return {r["ruling_id"] or r["version"] for r in rulings} | {r["version"] for r in rulings}

        codeless_rows = [ids(e["engine_rulings"]) for e in LINKS["unresolved_without_code"]]
        for key, question in questions.QUESTIONS.items():
            with self.subTest(question=key):
                if question.code is not None and question.code.startswith("UNSUPPORTED_"):
                    self.assertNotIn(question.code, LINKS["stop_codes"])
                elif question.code is not None:
                    self.assertTrue(set(question.rulings) <= ids(LINKS["stop_codes"][question.code]["engine_rulings"]))
                elif key in LINKS["codeless_questions"]:
                    self.assertTrue(set(question.rulings) <= ids(LINKS["codeless_questions"][key]["engine_rulings"]))
                else:
                    self.assertTrue(any(set(question.rulings) <= row for row in codeless_rows), question.rulings)

    def test_counts(self):
        """未解決の裁定 43 件 = 停止コード 42 + コードのない未解決（Z9）。v0.32 で CD4 の 1 件、v0.34 で TP3・NK5 の 2 件、v0.36 で AC6・RD9 の 2 件を加えた。v0.30 までは 28 件 = 停止コード 22 + コードのない未解決（起こらない 5・Z9）
        で、v0.31 で起こらない 5 件を停止コードにし（数は同じ）、HC1〜HC10 の 10 件を加えた。kyuura の論点は 19 件で、別の数え方（v0.21 の
        GW5・v0.22 の CS6・v0.23 の ER9・ER10・v0.31 の HC1〜HC10・v0.32 の CD4・v0.34 の TP3・NK5・v0.36 の AC6・RD9 は kyuura に論点がない）。"""
        counted = len(LINKS["stop_codes"]) + len(LINKS["unresolved_without_code"]) + sum(
            v["counted_as_engine_unresolved"] for v in LINKS["codeless_questions"].values())
        self.assertEqual(counted, LINKS["counts"]["engine_unresolved_rulings"])
        issues = {v["kyuura_issue"] for v in LINKS["stop_codes"].values() if v["kyuura_issue"]}
        issues |= {v["kyuura_issue"] for v in LINKS["codeless_questions"].values() if v["kyuura_issue"]}
        for section in ("unresolved_without_code", "deferred_card_questions", "implementation_assumptions_with_issue"):
            issues |= {v["kyuura_issue"] for v in LINKS[section]}
        self.assertEqual(len(issues), LINKS["counts"]["kyuura_issues"])
        self.assertTrue(all(i.startswith("UQ-") for i in issues))

    def test_engine_ruling_ids_appear_in_their_documents(self):
        """対応表に書いたエンジンの裁定 id は、書いた文書にある（文書の表の行か本文）。"""
        for ruling in all_engine_rulings():
            with self.subTest(ruling=ruling):
                text = (ROOT / ruling["document"]).read_text(encoding="utf-8")
                if ruling["ruling_id"] is not None:
                    self.assertRegex(text, rf"(?<![A-Za-z0-9]){re.escape(ruling['ruling_id'])}(?![0-9])")

    def test_latest_descriptions_cover_every_registration(self):
        """最新の説明を登録したワザ・特殊能力は、どれも 6 つの区分（kyuura の LD-、文面が印刷と同じで kyuura の CC- に書かれたもの、CC- はあるが
        ワザの文面を照合していないもの、kyuura に記録なし、kyuura データの採用で処理に使う文面を kyuura の印刷の文面にしたもの（2026-10-15
        からの方針。docs/card-data-policy.md。採用の記録 card_sources.json との対応は scripts/check_card_sources.py が確かめる）、処理に使う
        文面を kyuura のエラッタ（RUL- など）にしたもの（v0.30 の errata_text）、処理に使う文面を kyuura の card_differences の最新の説明に
        したもの（v0.31 の difference_text。ピッピの「ゆびをふる」））のちょうど 1 つに挙げる（登録を加えたら対応表も直す）。
        文面の一致は scripts/check_research_links.py が kyuura で確かめる。"""
        section = LINKS["latest_descriptions"]
        groups = {name: set(section[name]) for name in
                  ("registered", "recorded_in_card_checks", "card_checks_without_text", "registered_without_kyuura_record",
                   "adopted_printed_text", "errata_text", "difference_text",
                   # v0.68: 利用者が示した訂正の文面（ガルーラのこどものおつかい）・エンジンの簡略化した仕様（イマクニ？のドードー）
                   "user_corrected_text", "engine_simplified_text",
                   # v0.69: 拡張パック以外の商品の同じカードの登録（元のカードの登録の区分にしたがう）
                   "equivalent_registrations",
                   # v0.71: 再録のカードの、元のカードの記録の文面を処理に使う登録
                   "reprint_registrations")}
        names = list(groups)
        for i, a in enumerate(names):
            for b in names[i + 1:]:
                with self.subTest(a=a, b=b):
                    self.assertFalse(groups[a] & groups[b])
        self.assertEqual(set().union(*groups.values()), registered_targets())
        # v0.18c のナツメのヤドンは、2026-10-15 にエンジンの照合の記録を kyuura に取り込んだ（CC-PMCG6-044-P155。kyuura は画像を読み直していない）。
        self.assertEqual(section["recorded_in_card_checks"]["PMCG6-044/attack/0"], "CC-PMCG6-044-P155")
        # ドードーのみだれづきは、図版の版が決まらないので kyuura の照合の記録で文面を照合していない（docs/verified-record-reuse.md 4 章）。
        self.assertEqual(set(section["card_checks_without_text"]), {"PMCG1-061/attack/0"})
        for target, ld_id in section["registered"].items():
            card, kind, index = target.split("/")
            self.assertEqual(ld_id, f"LD-{card}-{'ATK' if kind == 'attack' else 'PWR'}{index}")
        for target, cc_id in {**section["recorded_in_card_checks"], **section["card_checks_without_text"]}.items():
            card = target.split("/")[0]
            self.assertTrue(cc_id.startswith(f"CC-{card}-P"), cc_id)
            self.assertIn(cc_id, LINKS["card_checks"]["engine_verified"][card])
        # v0.30: 炎エネルギーをトラッシュするワザは kyuura の RUL-ENERGY-DISCARD-ATTACKS の文面にしたがう。記録の cards はウインディだけなので、
        # ほかのワザは適用の範囲（errata_scope。記録の notes の引用・同じ印刷の文面）で結ぶ。照らすのは scripts/check_research_links.py
        # v0.31: リザードンの「エナジーバーン」は TXT-CHARIZARD（記録の cards にリザードンがある。適用の範囲ではない）
        # v0.73: 超エネルギー回収（PR1-009/trainer）は ERR-SUPER-ENERGY-RETRIEVAL（記録の cards は pcg-search.com の id 1stp009。対応は errata_card_ids）
        self.assertEqual(set(section["errata_text"].values()), {"RUL-ENERGY-DISCARD-ATTACKS", "TXT-CHARIZARD", "ERR-SUPER-ENERGY-RETRIEVAL"})
        self.assertEqual(section["errata_text"]["PMCG1-021/power/0"], "TXT-CHARIZARD")
        self.assertEqual(section["errata_text"]["PR1-009/trainer"], "ERR-SUPER-ENERGY-RETRIEVAL")
        scoped = {target for scope in section["errata_scope"] for target in scope["targets"]}
        self.assertEqual(scoped, set(section["errata_text"]) - {"PMCG1-019/attack/0", "PMCG1-021/power/0", "PR1-009/trainer"})
        # v0.31: ピッピの「ゆびをふる」は kyuura の card_differences の最新の説明（p.223 の解説の記録。LD- はない。kyuura への報告事項）
        # v0.42: カイリューの［かけつける］は kyuura の card_differences の最新の説明（p.249 の記録。特殊状態の記述がない。LD- はない）
        self.assertEqual(section["difference_text"], {"PMCG1-067/attack/1": "kyuura data/curation/card_differences.json#PMCG1-067",
                                                      "PMCG3-043/power/0": "kyuura data/curation/card_differences.json#PMCG3-043"})
        for scope in section["errata_scope"]:
            self.assertEqual(section["errata_text"][scope["targets"][0]], scope["record"])

    def test_card_checks_cover_every_verified_card(self):
        """エンジンの照合の記録のあるカードは、kyuura の CC- の id か「kyuura に記録なし」のどちらかに挙げる。"""
        section = LINKS["card_checks"]
        cards = set(read_verification()["cards"])
        self.assertFalse(set(section["engine_verified"]) & set(section["engine_verified_without_kyuura_record"]))
        self.assertEqual(set(section["engine_verified"]) | set(section["engine_verified_without_kyuura_record"]), cards)
        self.assertFalse(set(section["not_in_engine"]) & cards)
        for card, ids in {**section["engine_verified"], **section["not_in_engine"]}.items():
            for cc_id in ids:
                self.assertTrue(cc_id.startswith(f"CC-{card}-"), cc_id)

    def test_classification_differences_do_not_change_behaviour(self):
        """分類の違い（17 件）は、どれも処理を変えない（docs/research-alignment-v0.18a.md 4・5 章）。"""
        self.assertEqual(len(LINKS["classification_differences"]), 17)
        for diff in LINKS["classification_differences"]:
            self.assertIn(diff["kyuura_status"], ("CONFIRMED", "SUPPORTED"))
            self.assertFalse(diff["behaviour_changed"])
            self.assertTrue(diff["kyuura_ruling"].startswith("CR-"))

    def test_z23_subcases(self):
        """Z23 の場合（docs/unresolved-research-v0.18b.md 3 章）を 4 つに分けて持つ。"""
        self.assertEqual([s["id"] for s in LINKS["subcases"]["Z23"]], ["Z23-a", "Z23-b", "Z23-c", "Z23-d"])

    @unittest.skipUnless((KYUURA / ".git").exists(), "../kyuura がない")
    def test_matches_the_research_commit(self):
        """../kyuura があれば、対応表を kyuura の研究の基準のコミットの記録と照らす（論点の分類・未解決の一覧・裁定の分類・最新の説明の文面・
        照合の記録・カードデータの違い）。"""
        result = subprocess.run(["python3", str(ROOT / "scripts" / "check_research_links.py"), "--kyuura", str(KYUURA)],
                                capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)


if __name__ == "__main__":
    unittest.main()

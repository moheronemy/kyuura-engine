"""停止の方針の分類台帳 docs/stop-policy-classification.json を作る・確かめる（調査・分類だけ。エンジンの動作は変えない）。

    python scripts/build_stop_policy_classification.py --write   # 台帳を書き出す
    python scripts/build_stop_policy_classification.py --check   # 現行コードから作り直した台帳と、書き出した台帳が同じか・不変条件を満たすか

台帳は、v0.133 の棚卸し（docs/pre-freeze-gap-inventory.json。基点・集計は書き換えない）の ID を参照し、モードの方針の軸を別に加える。棚卸しの各項目の
本文（到達条件・関連カード・研究の記録の写し）は複製しない（``inventory_ref`` で引く）。

方針の案はどれも利用者の承認を受けていない（``mode_policy_status`` は unconsidered・proposal・decision_required のどれか）。既存の利用者指定の
挙動の状態（承認・実装・検証）は ``existing_behavior_status`` に別に書く。
"""

from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import re
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import stop_policy_scan as scan

ROOT = pathlib.Path(__file__).resolve().parent.parent
OUTPUT = ROOT / "docs" / "stop-policy-classification.json"
INVENTORY = ROOT / "docs" / "pre-freeze-gap-inventory.json"
RESEARCH = ROOT / "kyuura_engine" / "data" / "research_links.json"

BASE = {
    "commit": "3e25ac5eff0f90dbea224045e77c2b60e025bf2d",
    "version": "0.136.0",
    "branch_of_base": "origin/claude/v0.136-card-flip-game",
    "contains": ["v0.134 991db7b（main にマージ済み。PR #28）", "v0.135 450c2be・da9d4e9（origin/claude/v0.135-quiz-answer-rejection。PR #29 は未マージ）",
                 "v0.136 a81952f・465db7e・4a20aec・3e25ac5"],
    "origin_main": "07acf1788321e068a3582c284418ef618ed86a42",
    "origin_main_is_ancestor": True,
    "note": "origin/main は v0.135・v0.136 を含まない。main だけを基準にすると、v0.135・v0.136 で直した漏れを未修正と読み違えるので、基点は v0.136 の最後のコミットにした",
}
KYUURA = {
    "pinned_commit": "71d1728938fb4c8fefde9b82779cdef74beb612d",
    "pinned_by": ["scripts/extract_kyuura_cards.py の KYUURA_COMMIT", "kyuura_engine/data/research_links.json の research_commit・card_data_commit"],
    "checkout_observed": "b9e7cff6d2b2c6b4539ec45e61bf453879adab3a",
    "checkout_relation": "C:/dev/kyuura の checkout（main。未コミットの変更なし）は固定コミットの祖先（固定コミットより古い）。この作業では kyuura を読んだだけで、分類の根拠には固定コミットの記録（エンジンの写し）を使った",
    "read_only": True,
}

STRICT_DEFINITIONS = {
    "STRICT-A": {"name": "公式の根拠だけ", "rule": "2000.02.14 版の公式ルールと、既存の公式資料（最新の説明・エラッタ・裁定）だけを使い、それ以外（利用者指定・エンジンの簡略化・実装上の仮定）"
                 "で決めている処理も止める"},
    "STRICT-B": {"name": "固定したルールセット", "rule": "公式の根拠に、明示的に承認された利用者指定・記録済みの簡略化・実装上の仮定を加えた、版で固定したルールセットに厳密にしたがう"
                 "（集合に入っていない処理は止める）"},
}
PLAY_DEFINITION = ("プレイ用モード: 厳密モードのルールセットに、項目ごとに承認したプレイ用の規約を加える。すべての停止をなくすことは目的にしない。安全に続けられない経路・未実装の経路は止める候補のまま")

# ---------------------------------------------------------------------------------------------------------------------------------------------------
# モードの定義の合意（2026-11-03。docs/ruleset-mode-design.md 2 章）。根拠は本会話の利用者の指示で、公式の裁定・kyuura の研究上の解決ではない。
# 合意したのはこの 6 項目だけ。規約集合の識別・採用の単位・途中の変更・旧保存状態・不足した構成の開始・個々の続行規約は未決（docs/ruleset-mode-decisions.md）
# ---------------------------------------------------------------------------------------------------------------------------------------------------
AGREEMENT_SOURCE = {"by": "user", "on": "2026-11-03", "where": "本会話の利用者の指示（作業ブランチ claude/ruleset-mode-design の依頼の「合意済みの定義」）",
                    "not_recorded_as": "公式の裁定・最新の説明・エラッタ・kyuura の研究上の解決（UQ- の論点は解決済みにしない）"}
AGREEMENTS = [
    {"id": "AGR-MODE-SHARED-ENGINE", "statement": "同じ処理基盤に、採用する規約集合を渡す。",
     "reading": "モードごとに別のエンジン・別の分岐を持たない。モードの違いは、渡す規約集合の中身の違いとして表す"},
    {"id": "AGR-MODE-STRICT", "statement": "厳密モードは、未決の裁定に当たったら停止する検証用モード。",
     "reading": "未決の裁定（研究の停止コード UNRESOLVED_*・コードのない問いのうち止めている場面）に当たったら、今のエンジンと同じく止める（拒否・HALTED・途中停止の区別も今のまま）"},
    {"id": "AGR-MODE-PLAY", "statement": "プレイ用モードは、未決の裁定を事前に定めた続行規約で処理し、実際の対戦を進めるモード。",
     "reading": "続行規約は対戦の前に集合に入れておくもの（対戦の途中で決めない）。どの未決の裁定にどの規約を当てるかは未決（個々の続行規約は 1 つも採っていない）"},
    {"id": "AGR-MODE-BASELINE-USER", "statement": "既存の承認済み利用者指定は、両モードに共通する基礎集合に含める。",
     "reading": "台帳の conventions のうち、利用者が明示的に指定した記録（baseline_category が user_specified）だけ。指定の対象・範囲は記録のまま（広げない・無効化しない）。"
                "エンジンの簡略化・実装上の仮定・データの訂正は、この合意に含まれない（DEC-BASELINE-NONUSER・DEC-CARD-DATA-CORRECTIONS）"},
    {"id": "AGR-MODE-SAFETY", "statement": "情報漏れ、状態破損、不正入力、実装不足、計算上限は、プレイ用だから無視してよいものではない。",
     "reading": "両モードで同じ安全境界（safety_boundaries の SB-*）を保つ。プレイ用の規約で漏れ・破損・未実装・上限の超過を解消したことにしない"},
    {"id": "AGR-MODE-PRIORITY", "statement": "続行規約の整備は、対戦全体を終端にする項目から優先する。",
     "reading": "準備の HALTED・ポケモンチェックの HALTED・途中停止（5 章の 14 コード）を、選択肢を 1 つ減らすだけの拒否より先に扱う。どの規約を採るかは決めていない"},
]
AGREEMENT_IDS = {a["id"] for a in AGREEMENTS}
AGREED_CONVENTION_STATUS = "user_agreed"  # 規約（conventions）だけが使える。合意 AGR-MODE-BASELINE-USER で基礎集合に入れた利用者指定。続行規約の採用ではない
MODE_DEFINITIONS_HISTORY = {
    "STRICT-A": "厳密モードの定義としては採用しない（過去の検討案。AGR-MODE-STRICT・AGR-MODE-BASELINE-USER と合わない）。研究・照合の用途の集合として別に作るかは決めていない",
    "STRICT-B": "AGR-MODE-STRICT・AGR-MODE-BASELINE-USER に置きかえた。STRICT-B が含めていたエンジンの簡略化・実装上の仮定を基礎集合に入れるかは未決（DEC-BASELINE-NONUSER）",
    "families_strict_columns": "族の strict の 2 列（STRICT-A・STRICT-B）は分類の時点の案のまま残す。合意後の厳密モードは、未決の裁定に当たったら止める（今の止め方。STRICT-B の列と同じ動き）",
    "play_at_classification": PLAY_DEFINITION,
}

# 判断事項の置き場所（見出し ``### <ID>`` が置き場所の文書にちょうど 1 つある。--check が確かめる）。DEC-STRICT-DEFINITION は合意で決まった（履歴として元の文書に残す）
STOP_DECISIONS_DOC = "docs/stop-policy-decisions.md"
RULESET_DECISIONS_DOC = "docs/ruleset-mode-decisions.md"
RULESET_DESIGN_DOC = ROOT / "docs" / "ruleset-mode-design.md"
RULESET_DECISIONS = [
    "DEC-RULESET-IDENTITY", "DEC-RULESET-VERSIONING", "DEC-CONVENTION-GRANULARITY", "DEC-CONVENTION-CONFLICTS", "DEC-MODE-CHANGE-DURING-GAME", "DEC-LEGACY-STATES",
    "DEC-PLAY-CONFIG-INCOMPLETE-START", "DEC-PLAY-DEBUG-PARTIAL", "DEC-BASELINE-NONUSER", "DEC-BASELINE-CENSUS", "DEC-CARD-DATA-CORRECTIONS", "DEC-RESUME-WITH-OTHER-RULESET",
    "DEC-EXISTING-USER-SPECS",
]
DECISION_STATUS = {
    "DEC-STRICT-DEFINITION": {"status": "agreed", "agreements": ["AGR-MODE-STRICT", "AGR-MODE-PLAY", "AGR-MODE-BASELINE-USER"],
                              "note": "STRICT-A は厳密モードの定義として採用しない（過去の検討案）。STRICT-B は合意済みの定義に置きかえた"},
    "DEC-EXISTING-USER-SPECS": {"status": "partly_agreed", "agreements": ["AGR-MODE-BASELINE-USER"],
                                "note": "利用者指定（12 件・USER-ID 9 つ）は基礎集合に入れる。エンジンの簡略化・実装上の仮定・データの訂正の扱いは DEC-BASELINE-NONUSER・DEC-CARD-DATA-CORRECTIONS で未決"},
}

SAFETY_CONDITIONS = {
    "SC-CARD": "カードの消失・重複・不正な領域移動がない",
    "SC-SECRET": "秘密情報が受理可否・エラー・候補から漏れない",
    "SC-RNG": "乱数の結果や分布を都合よく変えない",
    "SC-OPTIONS": "合法な選択肢を黙って削らない",
    "SC-TEXT-SEAT": "原文と異なる結果、先攻・席による偏りが生じない（生じるなら明示して承認を受ける）",
    "SC-RECORD": "保存・復元・再生・監査に必要な情報を保持できる",
    "SC-HALT-KIND": "拒否と、処理済みの途中停止を混同しない",
}

PLAY_GROUPS = {
    "1": "明示的な規約を決めれば続行できる",
    "2": "プレイヤーの選択を実装すれば続行できる（誰がいつ選べるか自体が未裁定なら、まず 1 の判断が必要）",
    "3": "機能・データの追加が必要（モード切替だけでは解決しない）",
    "4": "計算方法・探索の改善が必要（枝を黙って削る・未探索を安全とみなす方法は採用案にしない）",
    "5": "両モードで保護・拒否が必要（情報漏れ・カード保存則の破損・壊れた状態・不正入力など）",
    "6": "対象外・将来拡張・追加確認待ち",
}

REACHABILITY = {
    "legal_sequence": "初期状態（new_game）からの合法な操作の列で発生を観測した（対戦の道具の記録）",
    "constructed_board": "構築した盤面（テスト専用の build_test_state など）で発生を確かめた、またはテストが発生を表明する。その盤面に合法な操作の列で着くかは別",
    "test_only_mutation": "テスト専用の改変（合成した登録表・状態の直接の書き換え）でだけ確かめた",
    "static_only": "定義・参照・raise を静的に確かめただけ（発生は未確認）",
    "unknown": "確かめていない（到達しないという意味ではない）",
}

STOP_MECHANISMS = {
    "command_rejection": "コマンドを受け付けない（複製の上で処理するので、渡した状態・乱数・ログは変わらない）。手番のプレイヤーはほかの操作を選べる。"
                         "決定への答え・準備の最後で、どの答えでも同じ止め方になるなら、答えのない決定を残さずにその前の状態で HALTED にする（engine._apply_once の共通処理）",
    "answer_rejection": "決定への答えの一部を受け付けない（ほかの答えは受け付ける）",
    "setup_halt": "対戦の準備で HALTED（終端。再開の操作はない）",
    "pokemon_check_halt": "ポケモンチェック・番の終わりの処理で HALTED（どの操作でも避けられないので、コマンドを拒否せずに止める。終端）",
    "deferred_interruption": "途中停止（DeferredShortage。そこまでのコイン・処理を残した終端の HALTED と interruption の記録。拒否ではない）",
    "dynamic_halt_conversion": "ほかのコードの拒否を、どの答えでも止まる決定・ポケモンチェックの途中で HALTED に変える経路（コードは元の拒否のもの）",
    "deck_validation": "デッキの検査で拒否（INVALID_DECK の問題の文。対戦は始まらない）",
    "internal_error": "内部例外（RuntimeError・StateIntegrityError など）。未対応・未裁定ではなく、エンジンの不具合か壊れた状態を示す",
    "not_raised": "現行コードでは投げない（コメント・履歴だけ）",
    "unclassified": "静的に止め方を決めなかった",
}

MODE_POLICY_STATUS = ("unconsidered", "proposal", "decision_required")  # 今回の台帳では approved・implemented・verified を使わない
EXISTING_BEHAVIOR_STATUS = ("user_approved", "implemented", "verified")

# ---------------------------------------------------------------------------------------------------------------------------------------------------
# 研究の停止コード（固定研究基準の対応表 316 件）の族。メンバーはコードの UNRESOLVED_ を除いた名前。族は方針を書く単位で、コードの改名・分割はしない
# ---------------------------------------------------------------------------------------------------------------------------------------------------

FAMILY_MEMBERS = {
    "PF-USE-WITHOUT-EFFECT": """POTION_WITHOUT_DAMAGE POTION_UNDAMAGED_TARGET SWITCH_WITHOUT_BENCH GUST_WITHOUT_OPPONENT_BENCH COMPUTER_SEARCH_EMPTY_DECK
        ENERGY_RETRIEVAL_WITHOUT_TARGET POWER_HEAL_WITHOUT_DAMAGE POWER_SWITCH_WITHOUT_OPPONENT_BENCH POWER_DISCARD_WITHOUT_HAND TRAINER_WITHOUT_TARGET
        DEVOLUTION_SPRAY_WITHOUT_TARGET REVIVE_WITHOUT_TARGET POKEMON_FLUTE_WITHOUT_TARGET MR_FUJI_WITHOUT_BENCH SCOOP_UP_LAST_POKEMON SEARCH_TRAINER_WITHOUT_TARGET
        ENERGY_REMOVAL_WITHOUT_TARGET SUPER_POTION_UNDAMAGED_TARGET FULL_HEAL_SCOPE LAST_RESORT_WITHOUT_TARGET LAST_RESORT_UNDAMAGED_TARGET SABRINA_WITHOUT_TWO_POKEMON
        SABRINA_SOURCE_WITHOUT_ENERGY LT_SURGE_WITHOUT_BASIC ROCKET_GRUNT_WITHOUT_BENCH MISTYS_WISH_WITHOUT_HAND CELADON_GYM_WITHOUT_CONDITION FUCHSIA_GYM_WITHOUT_TARGET
        BLAINES_QUIZ_WITHOUT_POKEMON FULL_HEAL_WITHOUT_CONDITION MAX_REVIVE_WITHOUT_TARGET SUPER_ENERGY_RETRIEVAL_WITHOUT_TARGET ENERGY_STADIUM_WITHOUT_TARGET
        NINJA_GYM_WITHOUT_TARGET POKEMON_TOWER_TRAINER_WITHOUT_EFFECT SUPER_ROD_WITHOUT_TARGET TRAINER_UP_TO_WITHOUT_TARGET DEVOLUTION_SPRAY_HYPER_WITHOUT_TARGET
        MOOMOO_MILK_UNDAMAGED_TARGET ALL_PURPOSE_POWDER_WITHOUT_TARGET HEALING_FIELD_WITHOUT_DAMAGE SOLAR_POWER_WITHOUT_CONDITION ENGAGE_EMPTY_HAND
        POWER_COUNTER_MOVE_WITHOUT_COUNTERS POWER_COUNTER_MOVE_TO_SAME_POKEMON POWER_RETURN_WITHOUT_TARGET TIME_SHIFT_WITHOUT_TARGET TRANSPORT_WITHOUT_CARDS
        OLD_ROD_WITHOUT_TARGET MISTYS_CARE_WITHOUT_TARGET WANT_WITHOUT_TARGET FOSSIL_GUIDE_WITHOUT_TARGET FOSSILIZE_WITHOUT_TARGET POKEMON_TOWER_POWER_WITHOUT_EFFECT
        HELPING_HAND_WITHOUT_CONDITION THOUGHT_WAVE_MACHINE_WITHOUT_TARGET ENERGY_DRAIN_NO_ENERGY""",
    "PF-UP-TO-ZERO": """RECOVER_ZERO_ENERGY ENERGY_RETRIEVAL_ZERO_CHOICE DISCARD_ANY_NUMBER_ZERO ATTACH_FROM_DISCARD_ZERO BENCH_TARGETS_ZERO_CHOICE POWER_ZERO_CARDS
        NIGHTLY_GARBAGE_RUN_ZERO_CHOICE ROCKETS_TRAP_ZERO_CHOICE POKEDEX_UP_TO_ZERO SUPER_ENERGY_RETRIEVAL_ZERO_CHOICE TRAINER_UP_TO_ZERO_CHOICE DISCARD_UP_TO_ZERO
        HEAL_UP_TO_ZERO""",
    "PF-STATED-COUNT-SHORT": """DISCARD_DECK_SHORT STATED_CARDS_SHORT MISTYS_WRATH_SHORT_DECK VIRIDIAN_GYM_ONE_COUNTER MASTER_BALL_SHORT_DECK DECK_TOP_SHORT
        ATTACK_DECK_TOP_SHORT POWER_DECK_TOP_SHORT FLASH_DECK_SHORT DRY_UP_WATER_ENERGY_SHORT THOUGHT_WAVE_MACHINE_ENERGY_SHORT""",
    "PF-SIMULTANEOUS-ORDER": """POKEMON_CHECK_SLEEP_COIN_ORDER TRANSPARENCY_COIN_ORDER MULTIPLE_DAMAGE_TRIGGERS KO_PREVENTION_ORDER POST_KNOCKOUT_POWERS_ORDER
        SPECIAL_POISON_OVERWRITE KOGA_POISON_ORDER ATTACK_CHECK_CONFUSION MULTIPLE_ATTACK_CHECKS VERMILION_GYM_ATTACK_ORDER BENCH_COIN_TRANSPARENCY_ORDER
        NINJA_TRICK_ATTACK_COIN_ORDER METAL_ENERGY_POWER_ORDER POKEMON_CHECK_BERRY_ORDER COLOR_REPLACEMENT_ORDER POKEMON_CHECK_CHAR_COIN_ORDER BABY_RULE_COIN_ORDER
        POISON_CHANGE_ORDER GROUP_POWER_COIN_ORDER MIND_GAMES_CHAOS_GYM_ORDER DAMAGE_GUARD_OVERLAP REFLECT_SHIELD_OVERLAP KO_SURVIVAL_OVERLAP TIME_TRAVEL_OVERLAP
        COLOR_MARKER_PRECEDENCE MAX_HP_SET_AND_INCREASE""",
    "PF-KNOCKOUT-TIMING": """POKEMON_CHECK_DOUBLE_KNOCKOUT COUNTERATTACK_DOUBLE_KNOCKOUT RETALIATION_DOUBLE_KNOCKOUT DESTINY_BOND_KNOCKOUT RETURN_IN_PLAY_TO_DECK_KNOCKOUT
        PHOENIX_GAS_SOURCE_KNOCKOUT DEVOLUTION_INTERMEDIATE_KNOCKOUT POKEMON_CHECK_MID_KNOCKOUT KO_SURVIVAL_TIMING FOCUS_BAND_TIMING TRANSFORM_REVERT_KNOCKOUT_TIMING
        KO_PREVENTION_ATTACK_EFFECT ENERGY_DRAIN_ATTACKER_KNOCKED_OUT MAX_HP_DROP EVOLUTION_HP""",
    "PF-EFFECT-TIMING": """DAMAGE_TRIGGER_TIMING DISCARD_ENERGY_TIMING SINKHOLE_TIMING SCRAM_TIMING SCRAM_POWER_RESTORED REFLECT_SHIELD_TIMING SHELL_ARMOR_TIMING
        TIME_TRAVEL_TIMING VINE_PULL_TIMING DARK_PULSE_TIMING RETREAT_REACTION_TIMING REPARALYSIS_RECOVERY_TURN BALLOON_BERRY_FAILED_RETREAT""",
    "PF-PROTECTED-TARGET-EFFECT": """PREVENTED_COIN_DAMAGE EVADED_EFFECT_COIN PREVENTED_EFFECT_COIN KEEP_VOIDED_DISCARD_COIN DISCARD_PROTECTED_COIN COUNTER_TRANSFER_PROTECTED
        KEEP_PROTECTED_TARGET LOCK_ON_PROTECTED_TARGET POWER_DAMAGE_PREVENTED DISCARD_PROTECTED_POWER_USE KEEP_DETACHED_ENERGY_DISCARD EFFECT_AFTER_NO_DAMAGE""",
    "PF-DAMAGE-SCOPE": """CONFUSION_DAMAGE_MODIFIERS BENCH_DAMAGE_WEAKNESS_RESISTANCE POWER_DAMAGE_WEAKNESS_RESISTANCE POISON_DAMAGE_RECEIVED_POWER
        MINEFIELD_DAMAGE_RECEIVED_POWER RAINBOW_DAMAGE_RECEIVED_POWER TRAINER_DAMAGE_REDUCTION DOUBLED_DAMAGE_POWER_DAMAGE DARKNESS_DAMAGE_RECEIVED_POWER
        POWER_DAMAGE_RECEIVED_POWER GROWL_NON_ATTACK_DAMAGE INFLATE_NON_ATTACK_DAMAGE REDUCED_DAMAGE_BENCH_TARGET MISTY_SELF_DAMAGE CHARITY_BELOW_ZERO
        HARD_SHELL_NONPOSITIVE LIGHTNING_BOLT_DEFENDER_UNITS CHOSEN_ACTIVE_EXTRA_DAMAGE DISCARDED_ENERGY_DAMAGE_BONUS COMMAND_DAMAGE_SCOPE PRIMAL_DREAM_DAMAGE_STEP
        CALMING_AROMA_RETALIATION""",
    "PF-ENERGY-TYPE": """EXTRA_ENERGY_COLORLESS RAINBOW_ENERGY_TYPE RAINBOW_ATTACH_AS_TYPE RAINBOW_AS_BASIC_ENERGY_CARD TRANSFORM_SPECIAL_ENERGY BUZZAP_ENERGY_CARD_TYPE
        BUZZAP_COLOR FERVOR_RAINBOW_ENERGY RAINBOW_RECOVER_AS_TYPE MIRACLE_ENERGY_AS_TYPE MIRACLE_ENERGY_UNDER_WIND MIRACULOUS_WIND_CONVERTED_ENERGY
        MIRACULOUS_WIND_ENERGY_BURN ENERGY_BURN_TRANSFER COLOR_CHANGED_ENERGY_CARD COLOR_EFFECT_CONTINUATION SHIFT_COLOR_DURATION RETREAT_COST_FLOOR RETREAT_OVERPAY
        TRANSFORM_ENERGY_COLOR_LIST SUPER_TRANSFORM_ENERGY_COLORS""",
    "PF-COPY-TRANSFORM": """COPIED_ATTACK TRANSFORM_ENERGY_COUNT TRANSFORM_COPIED_POWER TRANSFORM_MODIFIED_DEFENDER SHAPESHIFT_SUPPRESSED SHAPESHIFT_ENTRY_POWER SHAPESHIFT_AGAIN
        VIRTUAL_ONCE_ATTACK RECALL_WITHOUT_PRE_EVOLUTION_ATTACK RECALL_EARLIER_STAGE RECALL_TARGET_CHANGED RECALL_FORM DEVOLUTION_TARGET_DISGUISED BUZZAP_DISGUISED
        MIRROR_MOVE_RECEIVED_ATTACK MIRROR_MOVE_ATTACK_CONDITIONS MIRROR_MOVE_LASTING_EFFECT MIRROR_MOVE_NON_ATTACK SKETCH_PRESENCE SKETCH_COPIED_ATTACK
        ALL_CLEAR_ATTACK_SOURCE TRANSFORM_BABY TRANSFORM_REVIVED_BASIC TRANSFORM_BABY_AND_BASIC SUPER_TRANSFORM_TARGET SUPER_TRANSFORM_SOURCE_CHANGE
        SUPER_TRANSFORM_COPIED_POWER SUPER_TRANSFORM_SUPPRESSED_FORM ESP_COPIED_ATTACK_COINS PRE_EVOLUTION_ATTACK_STAGE PRE_EVOLUTION_ATTACK_CONDITIONS
        PERMITTED_ATTACK_HELD VIRTUAL_ASLEEP_ONLY_ATTACK REACTIVE_SWITCH_TRANSFORMED_ATTACKER""",
    "PF-HISTORY-LASTING": """ATTACK_LOCK_SOURCE_RETURNED MEAN_LOOK_SOURCE_EVOLVED LEAVE_LOCK_KNOCKOUT LEAVE_LOCK_NO_EFFECT LEAVE_LOCK_SCRAM JAW_CLAMP_SOURCE_RETURNED
        JAW_CLAMP_SOURCE_EVOLVED CLAMPING_JAW_SOURCE_DEVOLVED PERISH_SONG_RECEIVED_ATTACK EVOLVE_AFTER_DEVOLUTION POWER_REUSE_AFTER_DEVOLUTION REVIVED_BASIC_DEVOLVED
        STADIUM_REUSE_AFTER_REPLACEMENT STADIUM_REUSE_AFTER_RETURN FUCHSIA_GYM_AFTER_REPLACEMENT BLAINE_SECOND_ATTACH POISON_MIST_EARLIER_POISON POISON_MIST_SOURCE
        RETREAT_AFTER_CONFUSION_CLEARED ATTACH_AFTER_POWER_ATTACH""",
    "PF-TEXT-READING": """OPPONENT_POKEMON_COUNTERS SPEED_STAR_SCOPE PROTECTIVE_FLAME_SCOPE ATTACH_BLOCK_SCOPE ATTACH_TRIGGER_SCOPE IGNORED_EFFECTS_SCOPE FULL_RECOVERY_COUNTERS
        HYPER_TEXTURE_UNMARKED_TARGET ALL_CLEAR_OTHER_EFFECTS ALL_CLEAR_FOSSIL_IN_PLAY BUZZAP_OPPONENT_TARGET LUCKY_STADIUM_UNSTATED_REPEAT SELF_EXCLUDING_POWER_COPIES
        CONDUCTIVITY_MULTIPLE_SOURCES MISTYS_CARE_OPPONENT_LAPRAS SECRETE_POISON_TARGET HOT_PLATE_BABY_EVOLUTION NEO_TEXT_BASIC_BABY NEO_TEXT_EVOLUTION_CARD_BABY
        FOSSIL_EVOLVED_READING HELPING_HAND_CHOICE PERFORM_DAMAGE_PLACES HAND_TRAINER_LOCK_BORROW CHAOS_GYM_BORROWED_TURN STADIUM_ACTIVATION_UNDER_TRAINER_BAN
        NINJA_TRICK_UNDER_TRAINER_BAN LEGEND_BODY_TRAINER_TARGET VANISH_OTHER_ATTACHED SCOOP_UP_ATTACHED_TRAINER NINJA_TRICK_LEAVES_WITH_POKEMON
        MIND_GAMES_BLOCKED_TURN_END REVIVE_HAND_BASIC_ENTRY EVOLUTION_PERMISSION_FROM_DECK CHANGE_ABSENT_WEAKNESS_RESISTANCE""",
    "PF-REACTION-DURING-PROCESS": """FLEE_DURING_OWN_ATTACK BENCH_GUARD_RECOMPUTE BENCH_GUARD_ZERO_DAMAGE_REACTION REACTION_BY_KNOCKED_OUT_POKEMON REACTION_AFTER_KNOCKOUT
        REACTION_CONDITION_CHANGED ENTRY_POWER_DURING_ATTACK BOLT_DURING_OWN_ATTACK ATTACK_HAND_BENCH_REACTION HOWL_OUTSIDE_OWN_TURN""",
    "PF-POWER-SUPPRESSION": """STRANGE_GAS_NEW_POKEMON STRANGE_GAS_PROTECTED_POKEMON GOOP_GAS_NEW_POKEMON DARK_WAVE_NEW_POKEMON DARK_WAVE_PROTECTED_POKEMON
        DARK_WAVE_KNOCKED_OUT_POWER LEGEND_BODY_GOOP_GAS SCARE_SUPPRESSION_CYCLE STOPPED_POWER_HOLDER QUICKEN_EFFECT_SUPPRESSED PRIMAL_DREAM_SUPPRESSED""",
    "PF-SETUP-PLAY-AS-POKEMON": """MULLIGAN_COMPENSATION PLAY_AS_POKEMON_SETUP PLAY_AS_POKEMON_RETREAT BREEDER_ON_PLAY_AS_POKEMON MIND_GAMES_PLAY_AS_POKEMON""",
    "PF-HIDDEN-INFORMATION": """SECRET_PLAN_HIDDEN_PROPERTY SECRET_PLAN_MINEFIELD HOT_PLATE_FACE_DOWN FACE_UP_DECK_CHECK FACE_UP_DECK_HIDDEN_TAKE FACE_UP_DECK_PLACE_TOP
        FACE_UP_DECK_LOOK_RETURN FACE_UP_DECK_MOVE""",
    "PF-ESP-REDO": """ESP_OPPONENT_COIN_TOSS ESP_MULTIPLE ESP_HOLDER_NOT_SABRINAS ESP_LEFT_BEFORE_COIN""",
}

# 族の方針（案）。strict は STRICT-A・STRICT-B の両方。play は候補（具体的な対象・時点・範囲・結果の違い）。どれも未承認
_COMMON_REGRESSION = ["止めている場面で、案の結果（状態・乱数・ログ・観測）を固定した盤面で確かめる", "隣の止めない場面（境界の反対側）の受理が変わらないこと",
                      "厳密モードで今の止め方（コード・拒否か HALTED か・状態を変えないこと）が変わらないこと", "両方の席・先攻後攻を入れかえた同じ盤面",
                      "保存・復元のあとで同じ結果（方針の識別子を含む）", "twin_command_problems（秘密だけが違う盤面の比較）"]

FAMILIES = {
    "PF-USE-WITHOUT-EFFECT": {
        "title": "対象・効果がない場面でカード・特殊能力を使えるか",
        "question": "使う対象（ダメージ・控え・手札・山札・トラッシュの選べるカードなど）がないとき、または使っても何も起こらないときに使えるか。使えるなら、カードのトラッシュ・回数の消費・コインはどうなるか",
        "play_groups": ["1"], "depends_on": [],
        "strict": {"STRICT-A": "今の止め方（使う前に UNRESOLVED_* で拒否）を保つ", "STRICT-B": "STRICT-A と同じ（承認済みの利用者指定はない）"},
        "play_candidates": [
            {"id": "P-UWE-1", "rule": "使えない（使う前に拒否）を規約として固定する", "target": "族のコードごとに、そのカード・特殊能力だけ（コードをまたいで一括にしない）",
             "timing": "使う宣言の時点（コイン・費用の前）", "result_difference": "結果は今と同じ（拒否の種類が規約による IllegalAction 相当になるだけ）",
             "safety": {"SC-SECRET": "停止の条件が非公開の領域（山札・サイド）の中身に依存するコードでは採らない（PSP-ST1-DECK-ORACLE の漏れをそのまま残す）", "SC-OPTIONS": "規約として明示すれば黙った削除にならない"}},
            {"id": "P-UWE-2", "rule": "使える。効果の対象がない部分は何もせず、カードはトラッシュ・回数は消費・コインは説明どおり投げる",
             "target": "族のコードごとに、そのカード・特殊能力だけ", "timing": "使う宣言を受け付け、効果の解決で対象がない要素を飛ばす",
             "result_difference": "カードの消費・回数・乱数の消費が今と変わる。山札を探す効果では、探して見つからないことが公開の結果になる（実際の対戦と同じ）",
             "safety": {"SC-RNG": "コインを投げる説明では乱数を 1 回以上消費する（分布は変えない）", "SC-SECRET": "探す効果では、山札を見たプレイヤーにだけ見つからないことが分かる形にする",
                        "SC-RECORD": "何もしなかった要素をログに残す"}},
        ],
        "requirements": {"research": "kyuura の UQ-CARD-USE-WITHOUT-TARGET 系の論点（カードごとに別の問い。ほかのカードの答えを流用しない記録がある）",
                         "user_decision": "コードごとに P-UWE-1・P-UWE-2 のどちらか（DEC-USE-WITHOUT-EFFECT）",
                         "implementation": "P-UWE-2 は、使用の受け付け・効果のない要素の処理・ログの共通化。P-UWE-1 は規約の記録と拒否の種類だけ"},
        "risks": ["一括の規約にすると、文面が違うカード（「てよい」「ことができる」の有無）を同じに扱う", "非公開の領域に依存する止め方（ST1 の山札・FC1 のエネルギーアーク）は、P-UWE-1 でも漏れが残る"],
        "regression": _COMMON_REGRESSION + ["対象がちょうど 1 つ・0 の境界", "非公開の領域の中身だけが違う 2 盤面"],
        "mode_policy_status": "proposal",
    },
    "PF-UP-TO-ZERO": {
        "title": "「最大N」「好きなだけ」に 0 を含むか",
        "question": "「最大N枚」「好きなだけ」（「てよい」「ことができる」がない）で、選べるものがあるのに 0 を選べるか",
        "play_groups": ["1", "2"], "depends_on": [],
        "strict": {"STRICT-A": "今の止め方（0 の答えを UNRESOLVED_* で拒否し、1 以上の答えは受け付ける。選べるものがなければ使う前に止めるコードもある）を保つ",
                   "STRICT-B": "STRICT-A と同じ"},
        "play_candidates": [
            {"id": "P-UTZ-1", "rule": "0 を選べない（1 以上）を規約として固定する", "target": "コードごと", "timing": "決定への答え",
             "result_difference": "今と同じ受理の範囲（0 の答えの拒否が規約による拒否になる）", "safety": {"SC-OPTIONS": "規約として明示する（0 が合法かは未裁定なので、黙った削除にしない）"}},
            {"id": "P-UTZ-2", "rule": "0 を選べる（選択肢に 0 を加える）", "target": "コードごと", "timing": "決定への答え",
             "result_difference": "0 を選んだとき、手札・トラッシュ・場が今と変わらずに効果が終わる", "safety": {"SC-RECORD": "0 を選んだことを決定の記録に残す"}},
        ],
        "requirements": {"research": "kyuura の UQ-UP-TO-ZERO-CHOICE（カードごとの問い）", "user_decision": "DEC-UP-TO-ZERO", "implementation": "P-UTZ-2 は決定の min_choices の変更と、0 のときの続き"},
        "risks": ["選べるものがない場面（0 しかない）と、あるのに 0 を選ぶ場面を混同する"],
        "regression": _COMMON_REGRESSION + ["0・1・最大の答え", "選べるものがない場面"],
        "mode_policy_status": "proposal",
    },
    "PF-STATED-COUNT-SHORT": {
        "title": "説明の決まった数に、処理できる数が足りない",
        "question": "「N枚」「N個」と決まった数を処理する説明で、山札・手札・エネルギーなどが N より少ないとき、あるだけ処理するか・使えないか・処理しないか",
        "play_groups": ["1"], "depends_on": [],
        "strict": {"STRICT-A": "今の止め方（使う前の拒否。DU1・TW1 はコインのあとの途中停止）を保つ", "STRICT-B": "STRICT-A と同じ。ひかるバンギラスの USER-MOUNTAIN-CRUSH-MILL-UP-TO-DECK はそのカードのワザだけで、この族へ広げない"},
        "play_candidates": [
            {"id": "P-SCS-1", "rule": "あるだけ処理する", "target": "コードごと。どの要素の数か（引く・トラッシュする・選ぶ・もどす）を明記する", "timing": "その要素を処理する時点（数量のチェック地点）",
             "result_difference": "足りない分を処理しない。DU1・TW1 では途中停止をせずに続く", "safety": {"SC-CARD": "処理しなかった分のカードは元の領域に残る", "SC-SECRET": "足りないかの判定は公開の数だけを使う"}},
            {"id": "P-SCS-2", "rule": "足りなければ使えない（使う前に拒否）", "target": "コードごと", "timing": "使う宣言の時点",
             "result_difference": "今の使う前の拒否と同じ結果。DU1・TW1 は使う前に分からない数（コインの「おもて」の数）なので採れない",
             "safety": {"SC-SECRET": "数が非公開の領域の中身で決まるとき（エネルギーアークの山札の基本エネルギー）は採らない", "SC-HALT-KIND": "途中停止（処理済み）と使う前の拒否を混同しない"}},
        ],
        "requirements": {"research": "kyuura の UQ-STATED-COUNT-SHORT（カードごと）", "user_decision": "DEC-STATED-COUNT-SHORT", "implementation": "P-SCS-1 は数量のチェック地点（interruption.check_quantity）の分岐と、要素ごとのあるだけの処理"},
        "risks": ["ひかるバンギラスの指定を自動的に広げる", "数が非公開の情報で決まる場面の使う前の拒否（漏れ）"],
        "regression": _COMMON_REGRESSION + ["N−1・N・N+1 の数", "途中停止の記録（interruption）が残らないこと（P-SCS-1）"],
        "mode_policy_status": "proposal",
    },
    "PF-SIMULTANEOUS-ORDER": {
        "title": "同時に起こる処理・コインの順番と、順番を決める人",
        "question": "同じ時点の 2 つ以上の処理（コイン・反応・効果・どく状態の上書きなど）の順番、またはその順番を決めるプレイヤーが原典から決まらない",
        "play_groups": ["1", "2"], "depends_on": [],
        "strict": {"STRICT-A": "今の止め方を保つ（順番で結果・乱数の割り当てが変わる場面だけ止めるコードと、場面だけで止めるコードがある。コードごとに確かめる）",
                   "STRICT-B": "STRICT-A と同じ。USER-DESTRUCTIVE-FIRE-DECLARE-ORDER-UP-TO・USER-MIND-GAMES-OPTIONAL-BEFORE-COST はそれぞれのカードだけ"},
        "play_candidates": [
            {"id": "P-SO-1", "rule": "順番を席によらない規則で固定する（例: 番のプレイヤーの側から。ポケモンチェックのようにどちらの番でもない処理では、その番のプレイヤーを基準にする）",
             "target": "コードごと", "timing": "その処理の時点", "result_difference": "決めた順番で乱数を割り当てる",
             "safety": {"SC-TEXT-SEAT": "席（プレイヤー 0・1）で決める規則は採らない。番のプレイヤーを基準にしても先攻・後攻で偏りうるので、偏りを記録して承認を受ける",
                        "SC-RNG": "順番で同じ乱数の列の割り当てが変わるので、規則を保存と記録に残す"}},
            {"id": "P-SO-2", "rule": "順番をプレイヤーが選ぶ（選ぶ人を規約で決める）", "target": "コードごと", "timing": "その処理の前の決定",
             "result_difference": "決定が 1 つ増える。選ぶ人の規約（P-SO-1 と同じ判断）が先に要る", "safety": {"SC-SECRET": "選ぶ人に見えない情報で順番の候補が変わらないこと"}},
            {"id": "P-SO-3", "rule": "すべての順番で結果が同じなら続ける（それ以外は止める）", "target": "コードごと（すでにそうしているコードは除く）", "timing": "その処理の前",
             "result_difference": "結果が同じ場面だけ止めなくなる", "safety": {"SC-RNG": "コインの数・順番が違えば同じ結果とみなさない（乱数の消費まで比べる）"}},
        ],
        "requirements": {"research": "kyuura の順番の論点（UQ-POKEMON-CHECK-SLEEP-COIN-ORDER・UQ-TRANSPARENCY-COIN-ORDER・UQ-MULTIPLE-DAMAGE-TRIGGERS-ONE-ATTACK など）",
                         "user_decision": "DEC-ORDER-RULE（とくに両側ねむり DEC-SLEEP-COIN-ORDER、錯乱ジム×ちえくらべ DEC-CHAOS-GYM-MIND-GAMES）",
                         "implementation": "P-SO-2 は順番の決定。P-SO-3 は全順番の比べ（探索の上限に注意）"},
        "risks": ["席で決める規則による偏り", "P-SO-3 の比べで乱数の消費の違いを見落とす"],
        "regression": _COMMON_REGRESSION + ["順番で結果が変わる盤面と変わらない盤面"],
        "mode_policy_status": "proposal",
    },
    "PF-KNOCKOUT-TIMING": {
        "title": "きぜつ・同時のきぜつ・残りHPと最大HPの判定の時点",
        "question": "きぜつの判定の時点、同時のきぜつか（p.324）、きぜつを避ける効果・最大HPが下がったときの判定の時点が原典から決まらない",
        "play_groups": ["1"], "depends_on": [],
        "strict": {"STRICT-A": "今の止め方を保つ（勝ち負けが変わりうる）", "STRICT-B": "STRICT-A と同じ"},
        "play_candidates": [
            {"id": "P-KO-1", "rule": "コードごとに読み方を 1 つ固定する（例: 「同時のきぜつとして p.324 の表で勝ち負けを決める」か「順に処理する」）", "target": "コードごと",
             "timing": "きぜつの判定", "result_difference": "サイド・勝ち負け・サドン・デスへの移り方が変わる",
             "safety": {"SC-TEXT-SEAT": "番のプレイヤーに有利な読み方を一律に採らない", "SC-RECORD": "勝ち負けの理由に規約の ID を残す"}},
        ],
        "requirements": {"research": "p.311・p.323〜325 の記録と kyuura の KO 系の論点", "user_decision": "DEC-KNOCKOUT-READINGS", "implementation": "judge の表・きぜつの処理の順番の分岐"},
        "risks": ["勝敗が変わる規約なので、影響が大きい", "サドン・デス（v0.134）の開始条件が変わる"],
        "regression": _COMMON_REGRESSION + ["p.311 の勝ち負けの表（tests/test_simultaneous_ko.py）", "サドン・デスへの移り方"],
        "mode_policy_status": "proposal",
    },
    "PF-EFFECT-TIMING": {
        "title": "効果・反応・状態の回復の時点",
        "question": "ダメージの前後・番の終わり・決定のあとなど、効果がはたらく時点が原典から決まらない",
        "play_groups": ["1"], "depends_on": [],
        "strict": {"STRICT-A": "今の止め方を保つ", "STRICT-B": "STRICT-A と同じ"},
        "play_candidates": [{"id": "P-ET-1", "rule": "コードごとに時点を 1 つ固定する", "target": "コードごと", "timing": "そのコードが書く時点",
                             "result_difference": "時点によってダメージ・きぜつ・コインの順番が変わる", "safety": {"SC-RNG": "時点でコインの順番が変わるときは規約に順番も書く"}}],
        "requirements": {"research": "各コードの研究の記録", "user_decision": "DEC-TIMING-READINGS", "implementation": "時点ごとの処理の分岐"},
        "risks": ["1 つの規約がほかの効果の時点の前提を変える"], "regression": _COMMON_REGRESSION, "mode_policy_status": "proposal",
    },
    "PF-PROTECTED-TARGET-EFFECT": {
        "title": "無効・保護された対象への効果と、それを決めるコイン",
        "question": "ダメージ・効果を受けない対象（とうめい・かたまる・KEEP など）について、無効になった要素だけを決めるコインを投げるか、残りの効果を処理するか",
        "play_groups": ["1"], "depends_on": [],
        "strict": {"STRICT-A": "今の止め方を保つ（投げるかで乱数の続きが変わる）", "STRICT-B": "STRICT-A と同じ"},
        "play_candidates": [
            {"id": "P-PT-1", "rule": "無効になった要素のコインは投げない", "target": "コードごと", "timing": "その要素", "result_difference": "乱数の続きが今の止める前の想定と変わる",
             "safety": {"SC-RNG": "投げる・投げないで後の乱数の割り当てが変わる。規約を保存に残し、比較の道具で区別する"}},
            {"id": "P-PT-2", "rule": "無効になった要素のコインも投げる（結果は使わない）", "target": "コードごと", "timing": "その要素", "result_difference": "乱数を消費する",
             "safety": {"SC-RNG": "P-PT-1 と同じ"}},
        ],
        "requirements": {"research": "kyuura の UQ-COIN-IN-NULLIFIED-ELEMENT・UQ-EFFECT-AFTER-NO-DAMAGE", "user_decision": "DEC-NULLIFIED-COINS", "implementation": "要素ごとのコインの扱い"},
        "risks": ["どちらの案も、厳密モードとプレイ用モードで同じ seed から乱数の列がずれる"], "regression": _COMMON_REGRESSION + ["コインのログ・乱数の状態の比べ"],
        "mode_policy_status": "proposal",
    },
    "PF-DAMAGE-SCOPE": {
        "title": "ダメージの計算に当てはめる範囲",
        "question": "弱点・抵抗力、ダメージを変える効果（プラスパワー・特殊能力・トレーナー）を、ワザ以外のダメージ・控えへのダメージ・自分へのダメージに当てはめるか",
        "play_groups": ["1"], "depends_on": [],
        "strict": {"STRICT-A": "今の止め方を保つ", "STRICT-B": "STRICT-A と同じ"},
        "play_candidates": [{"id": "P-DS-1", "rule": "コードごとに当てはめる・当てはめないを固定する", "target": "コードごと（同じ形でも別のカードの問いとして扱う）", "timing": "ダメージの計算",
                             "result_difference": "受けるダメージ・きぜつが変わる", "safety": {"SC-TEXT-SEAT": "原文の説明と違う結果になりうるので、規約の記録に読み方を書く"}}],
        "requirements": {"research": "kyuura の UQ-NON-ATTACK-DAMAGE-MODIFIERS・UQ-BENCH-DAMAGE-WEAKNESS-RESISTANCE など", "user_decision": "DEC-DAMAGE-READINGS",
                         "implementation": "ダメージの段階の分岐"},
        "risks": ["道具の対戦で頻度が高い（こんらんのダメージとプラスパワー・ディフェンダー）ので、規約の影響が広い"], "regression": _COMMON_REGRESSION + ["ダメージの 5 段階の表"],
        "mode_policy_status": "proposal",
    },
    "PF-ENERGY-TYPE": {
        "title": "特殊エネルギー・色・エネルギーの数え方",
        "question": "レインボー・ミラクル・色を変える効果のエネルギーが、どのタイプ・基本エネルギーカードとして数えられるか、にげるの支払い方",
        "play_groups": ["1"], "depends_on": [],
        "strict": {"STRICT-A": "今の止め方を保つ", "STRICT-B": "STRICT-A と同じ"},
        "play_candidates": [{"id": "P-EN-1", "rule": "コードごとに読み方を 1 つ固定する", "target": "コードごと", "timing": "エネルギーを数える・支払う時点",
                             "result_difference": "ワザを使えるか・ダメージ・トラッシュするカードが変わる", "safety": {"SC-OPTIONS": "支払い方の選択肢を減らす規約は、減らすことを明記する"}}],
        "requirements": {"research": "kyuura の UQ-SPECIAL-ENERGY-AS-TYPED-ENERGY など", "user_decision": "DEC-ENERGY-READINGS", "implementation": "色の読み方の探索（上限 256 は PF 外の技術上限）"},
        "risks": ["色の読み方の組が増え、UNSUPPORTED_COLOR_READINGS_LIMIT に当たる"], "regression": _COMMON_REGRESSION, "mode_policy_status": "proposal",
    },
    "PF-COPY-TRANSFORM": {
        "title": "コピー・変身・ばける・思い出す・オウムがえし",
        "question": "写したワザ・特殊能力の範囲、写す元・写した姿が変わったときの扱い",
        "play_groups": ["1", "3"], "depends_on": ["PF-RUNTIME-COPY-GAPS"],
        "strict": {"STRICT-A": "今の止め方を保つ", "STRICT-B": "STRICT-A と同じ"},
        "play_candidates": [{"id": "P-CT-1", "rule": "コードごとに読み方を固定し、写した処理を実装する", "target": "コード・写すワザの型の組（R7 の対応行列のセル）", "timing": "写す時点・使う時点",
                             "result_difference": "写せるワザ・特殊能力が増える",
                             "safety": {"SC-OPTIONS": "写す対象から外す（黙って候補を削る）方法は採らない", "SC-RECORD": "写した元・姿の記録を保存に残す"}}],
        "requirements": {"research": "kyuura の UQ-COPIED-ATTACK・UQ-TRANSFORM-SCOPE・UQ-SHAPESHIFT-SCOPE・UQ-RECALL-SCOPE・すごいへんしんの論点",
                         "user_decision": "DEC-COPY-SCOPE", "implementation": "UNSUPPORTED_COPIED_ATTACK などの実装の不足（PF-RUNTIME-COPY-GAPS）を先に埋める"},
        "risks": ["規約だけ決めても、写した処理が未実装なら止まる（モード切替では解決しない）"], "regression": _COMMON_REGRESSION + ["写す元の離脱・進化・退化"],
        "mode_policy_status": "proposal",
    },
    "PF-HISTORY-LASTING": {
        "title": "前の番の記録と、持続する効果の供給元の変化",
        "question": "持続する効果を与えたポケモンが山札にもどる・進化・退化・きぜつしたとき、前の番の記録をどう読むか",
        "play_groups": ["1", "3"], "depends_on": [],
        "strict": {"STRICT-A": "今の止め方を保つ", "STRICT-B": "STRICT-A と同じ"},
        "play_candidates": [{"id": "P-HL-1", "rule": "コードごとに効果が続く・終わるを固定する", "target": "コードごと", "timing": "供給元が変わった時点",
                             "result_difference": "ワザ・にげるの制限が続くか終わるかが変わる", "safety": {"SC-RECORD": "旧形式の保存に記録がない場合は推測で埋めない（UNSUPPORTED_HISTORY_* のまま）"}}],
        "requirements": {"research": "各コードの研究の記録", "user_decision": "DEC-LASTING-READINGS", "implementation": "記録が足りない旧状態の扱い（PF-RUNTIME-DATA）"},
        "risks": ["記録の足りない旧保存状態で、空値・0 で代用する"], "regression": _COMMON_REGRESSION, "mode_policy_status": "proposal",
    },
    "PF-TEXT-READING": {
        "title": "説明の読み方・範囲",
        "question": "「相手のポケモン」「その他の効果」などの範囲、ネオの文面の分類、場の効果の範囲が原典から決まらない",
        "play_groups": ["1"], "depends_on": [],
        "strict": {"STRICT-A": "今の止め方を保つ", "STRICT-B": "STRICT-A と同じ"},
        "play_candidates": [{"id": "P-TR-1", "rule": "コードごとに読み方を 1 つ固定する", "target": "コードごと（同じ言い回しでも別のカードの問いは別に決める）", "timing": "そのコードの時点",
                             "result_difference": "読み方による", "safety": {"SC-TEXT-SEAT": "後年の裁定・英語版の文面を根拠として持ち込まない（規約として記録する）"}}],
        "requirements": {"research": "各コードの研究の記録", "user_decision": "DEC-TEXT-READINGS", "implementation": "読み方ごとの分岐"},
        "risks": ["同じ言い回しの別のカードへ自動的に広げる"], "regression": _COMMON_REGRESSION, "mode_policy_status": "proposal",
    },
    "PF-REACTION-DURING-PROCESS": {
        "title": "ワザ・処理の途中の反応",
        "question": "ワザの途中・自分の番以外・きぜつしたあとに、反応する特殊能力・効果を使えるか",
        "play_groups": ["1", "3"], "depends_on": ["PF-RUNTIME-CONTINUATION"],
        "strict": {"STRICT-A": "今の止め方を保つ", "STRICT-B": "STRICT-A と同じ"},
        "play_candidates": [{"id": "P-RD-1", "rule": "コードごとに使える・使えないを固定し、使える場合は反応の続きを実装する", "target": "コードごと", "timing": "反応の時点",
                             "result_difference": "反応の決定が増える・なくなる", "safety": {"SC-HALT-KIND": "反応を黙って飛ばす実装をしない", "SC-SECRET": "反応の候補が非公開の情報で変わらないこと"}}],
        "requirements": {"research": "kyuura の UQ-REACTIVE-SWITCH-DURING-ATTACK など", "user_decision": "DEC-REACTION-READINGS", "implementation": "反応の継続（R6）"},
        "risks": ["使えないと決めても、使える場合の続きが未実装の経路は止まる"], "regression": _COMMON_REGRESSION + ["決定をまたぐ保存・復元"], "mode_policy_status": "proposal",
    },
    "PF-POWER-SUPPRESSION": {
        "title": "特殊能力を消す効果の範囲",
        "question": "ふしぎなガス・やみのはどう・まきちらせ!ベトベトガスなどが、新しく出たポケモン・保護されたポケモン・きぜつしたポケモンの特殊能力に及ぶか、循環するか",
        "play_groups": ["1"], "depends_on": [],
        "strict": {"STRICT-A": "今の止め方を保つ", "STRICT-B": "STRICT-A と同じ"},
        "play_candidates": [{"id": "P-PS-1", "rule": "コードごとに及ぶ・及ばないを固定する（循環は固定した優先で切る）", "target": "コードごと", "timing": "特殊能力の判定",
                             "result_difference": "特殊能力の可否が変わる", "safety": {"SC-TEXT-SEAT": "循環を切る優先を席で決めない"}}],
        "requirements": {"research": "各コードの研究の記録", "user_decision": "DEC-SUPPRESSION-READINGS", "implementation": "判定の分岐"},
        "risks": ["循環の切り方が先攻・後攻で偏る"], "regression": _COMMON_REGRESSION, "mode_policy_status": "proposal",
    },
    "PF-SETUP-PLAY-AS-POKEMON": {
        "title": "準備の切り直しの補償・なにかの化石・ピッピ人形",
        "question": "両者が切り直したあとの補償の数え方、ポケモンとして出すトレーナーの準備・にげる・育て屋の扱い",
        "play_groups": ["1"], "depends_on": [],
        "strict": {"STRICT-A": "今の止め方を保つ（準備の HALTED は対戦を始められない）", "STRICT-B": "STRICT-A と同じ"},
        "play_candidates": [
            {"id": "P-SU-1", "rule": "切り直しの補償の数え方を固定する（補償を数える単位: 相手の切り直しの総数か、両者の差か。引く時点: 最初のポケモンを置く前か後か）",
             "target": "UNRESOLVED_MULLIGAN_COMPENSATION（最初の対戦と延長戦の区間の両方）", "timing": "準備",
             "result_difference": "準備が HALTED にならず、手札の枚数が決まる", "safety": {"SC-TEXT-SEAT": "先攻・後攻（ジャンケンの勝ち負け）で偏らない数え方にする", "SC-RNG": "引く枚数で山札の残りが変わる"}},
            {"id": "P-SU-2", "rule": "なにかの化石・ピッピ人形を準備で出せる・出せないを固定する", "target": "UNRESOLVED_PLAY_AS_POKEMON_SETUP ほか", "timing": "準備・にげる・進化",
             "result_difference": "最初のポケモンの選択肢が変わる", "safety": {"SC-OPTIONS": "出せないとするなら規約として明記する"}},
        ],
        "requirements": {"research": "p.308 の準備の規定（切り直し）と、PF1〜PF3 の記録", "user_decision": "DEC-MULLIGAN-COMPENSATION・DEC-PLAY-AS-POKEMON",
                         "implementation": "準備の処理の分岐。延長戦の区間（v0.134）にも同じ規約を当てはめる"},
        "risks": ["通常の固定デッキでも起こる（道具の対戦で準備の HALTED を観測）ので、規約の影響が広い"], "regression": _COMMON_REGRESSION + ["延長戦の区間の準備"],
        "mode_policy_status": "proposal",
    },
    "PF-HIDDEN-INFORMATION": {
        "title": "うらのカード・おもての山札（フラッシュ）と秘密の情報",
        "question": "うらのカードの決まらない項目を読む処理、おもてのカードのある山札から引く・置く・見る処理の読み方",
        "play_groups": ["1", "5"], "depends_on": [],
        "strict": {"STRICT-A": "今の止め方を保つ（v0.135・v0.136 のクイズ・カードめくりゲームの使う前の保守的な止め方を含む）", "STRICT-B": "STRICT-A と同じ"},
        "play_candidates": [{"id": "P-HI-1", "rule": "FU3 などの読み方を固定する（例: おもてのカードを引く順番・公開の範囲）", "target": "コードごと", "timing": "山札を動かす時点",
                             "result_difference": "引けるカード・公開の範囲が変わる",
                             "safety": {"SC-SECRET": "受理・拒否・候補・理由の文が秘密に依存しないこと（twin_command_problems で確かめる）。v0.135・v0.136 の保守的な止め方は、読み方を決めたあとに両方の結果を確かめ直してから外す"}}],
        "requirements": {"research": "kyuura の UQ-FLASH-FACE-UP-DECK・UQ-FACE-DOWN-CARD", "user_decision": "DEC-FACE-UP-DECK", "implementation": "読み方ごとの山札の処理と、公開の範囲の観測"},
        "risks": ["読み方の規約で止めを外すと、v0.135・v0.136 で塞いだ漏れが別の形で戻る"], "regression": _COMMON_REGRESSION + ["v0.135・v0.136 の対のテスト"],
        "mode_policy_status": "proposal",
    },
    "PF-ESP-REDO": {
        "title": "ナツメのESPのやり直し",
        "question": "相手のコイン・2 枚以上の ESP・ナツメのポケモン以外・コインの前に離れた ESP の扱い",
        "play_groups": ["1"], "depends_on": [],
        "strict": {"STRICT-A": "今の止め方を保つ", "STRICT-B": "STRICT-A と同じ"},
        "play_candidates": [{"id": "P-ESP-1", "rule": "コードごとにやり直せる・やり直せないを固定する", "target": "コードごと", "timing": "コインの直後",
                             "result_difference": "やり直しの決定が増える・なくなる", "safety": {"SC-RNG": "やり直しで乱数をもう一度使う。都合のよい結果を選ぶ回数を規約に書く"}}],
        "requirements": {"research": "kyuura の UQ-ESP-REDO", "user_decision": "DEC-ESP-READINGS", "implementation": "ESP の決定の分岐"},
        "risks": ["やり直しの回数で結果の分布が変わる"], "regression": _COMMON_REGRESSION + ["コインのログ"], "mode_policy_status": "proposal",
    },
    # 表外のコード（エンジンの未対応・技術上限・データ）の族
    "PF-RUNTIME-REGISTRY": {
        "title": "登録・契約のガード（未登録・チェック不適合・旧契約）",
        "question": "登録表にない・チェックに合わない・旧契約の経路のコマンドやカード",
        "play_groups": ["5"], "depends_on": [],
        "strict": {"STRICT-A": "拒否を保つ", "STRICT-B": "拒否を保つ"},
        "play_candidates": [], "no_play_reason": "未登録・不正な登録の処理を推測で進めない（効果がないものとして扱わない）。通常対戦の対象 1,374 枚の登録とは別のガード",
        "requirements": {"research": "", "user_decision": "", "implementation": ""}, "risks": ["ガードを外すと、未登録のカードを効果なしで処理する"],
        "regression": ["不正な登録表・未登録のカードで拒否が変わらないこと"], "mode_policy_status": "proposal",
    },
    "PF-RUNTIME-COPY-GAPS": {
        "title": "コピー・オウムがえし・履歴の実装の不足",
        "question": "写したワザ・特殊能力の型、オウムがえしで返す型、必要な番の履歴がない",
        "play_groups": ["3"], "depends_on": [],
        "strict": {"STRICT-A": "拒否を保つ", "STRICT-B": "拒否を保つ"},
        "play_candidates": [], "no_play_reason": "実装の不足なので、モードを切り替えても処理できない。写す対象から外す・無効化して続ける方法は採らない",
        "requirements": {"research": "", "user_decision": "", "implementation": "コピーの対応行列（R7）。研究の論点（PF-COPY-TRANSFORM）と分ける"},
        "risks": ["無効化して続けると原文と違う結果になる"], "regression": ["行列のセルごとの動作・無効化・供給元・保存"], "mode_policy_status": "proposal",
    },
    "PF-RUNTIME-CONTINUATION": {
        "title": "決定・反応の継続の実装の不足",
        "question": "返すダメージ・おいうち・ワザの途中のエネルギーの反応・でんせつのからだ・ミラクルエネルギーなど、決定をまたぐ継続を表せない",
        "play_groups": ["3"], "depends_on": [],
        "strict": {"STRICT-A": "拒否を保つ", "STRICT-B": "拒否を保つ"},
        "play_candidates": [], "no_play_reason": "継続の状態がないので、モード切替では続けられない。反応を黙って飛ばさない",
        "requirements": {"research": "", "user_decision": "", "implementation": "共通の継続の状態と供給元の情報（R6）"},
        "risks": ["反応を飛ばすと、相手の選択肢を黙って削る"], "regression": ["各コードの最小の合法な経路・供給元の離脱・両席・保存と復元"], "mode_policy_status": "proposal",
    },
    "PF-RUNTIME-SEARCH-LIMIT": {
        "title": "先読み・探索・組合せの上限",
        "question": "先読み 4096 葉、裏のカードの割当 512、色の読み方 256、くろこげのコイン 6 枚、きのみ 3 個、無限のコインの先読み",
        "play_groups": ["4"], "depends_on": [],
        "strict": {"STRICT-A": "拒否・HALTED を保つ", "STRICT-B": "拒否・HALTED を保つ"},
        "play_candidates": [], "no_play_reason": "上限を超えた枝を黙って削る・未探索を安全とみなす方法は採用案にしない。同値類・相関による計算の改善は両モード共通の作業",
        "requirements": {"research": "", "user_decision": "上限を増やすかは別の判断（DEC-SEARCH-LIMITS）", "implementation": "R3・R4・R9"},
        "risks": ["上限で続ける（fail-open）と、答えのない決定や情報漏れを残す"], "regression": ["上限の前後（4095・4096・4097 など）", "旧完全探索との一致"], "mode_policy_status": "proposal",
    },
    "PF-RUNTIME-DATA": {
        "title": "属性・旧形式・最初のデッキの情報の不足",
        "question": "図鑑番号・身長がない、旧保存状態に履歴の場所・番の記録・デッキリストがない",
        "play_groups": ["3", "5"], "depends_on": [],
        "strict": {"STRICT-A": "拒否を保つ", "STRICT-B": "拒否を保つ"},
        "play_candidates": [], "no_play_reason": "値を推測で埋めない（0・空で代用しない）。データの追加（研究）と移行を分ける",
        "requirements": {"research": "図鑑番号の研究（v0.129 の USER-QUIZ-HEIGHT-OFFICIAL-ZUKAN の範囲の外）", "user_decision": "", "implementation": "新形式で値を持つ。旧形式は拒否か根拠のある変換"},
        "risks": ["推測した値で出題・計算する"], "regression": ["旧形式の読み込み"], "mode_policy_status": "proposal",
    },
    "PF-RUNTIME-GENERIC": {
        "title": "汎用の未裁定コード UNRESOLVED_RULING",
        "question": "選ぶと止める選択（unresolved_choices）の既定のコード。個別のコードを渡さない決定・答えの続きのない決定で使う",
        "play_groups": ["6"], "depends_on": [],
        "strict": {"STRICT-A": "拒否を保つ", "STRICT-B": "拒否を保つ"},
        "play_candidates": [], "no_play_reason": "どの問いの停止かがコードから分からないので、規約の対象にできない。発生した経路ごとに個別のコードを確かめる（追加確認待ち）",
        "requirements": {"research": "", "user_decision": "", "implementation": "発生した場合の経路の特定"}, "risks": ["一括で無視すると、どの問いを決めたのか記録できない"],
        "regression": [], "mode_policy_status": "unconsidered",
    },
}

RUNTIME_FAMILY = {
    "UNSUPPORTED_ACTION": "PF-RUNTIME-REGISTRY", "UNSUPPORTED_ATTACK": "PF-RUNTIME-REGISTRY", "UNSUPPORTED_POKEMON_POWER": "PF-RUNTIME-REGISTRY",
    "UNSUPPORTED_TRAINER": "PF-RUNTIME-REGISTRY", "UNSUPPORTED_EVOLUTION": "PF-RUNTIME-REGISTRY", "UNSUPPORTED_EVOLUTION_LINEAGE": "PF-RUNTIME-DATA",
    "UNSUPPORTED_LEGACY_PREFLIGHT": "PF-RUNTIME-REGISTRY", "UNSUPPORTED_CARD": "PF-RUNTIME-REGISTRY",
    "UNSUPPORTED_COPIED_ATTACK": "PF-RUNTIME-COPY-GAPS", "UNSUPPORTED_TRANSFORM_COPIED_POWER": "PF-RUNTIME-COPY-GAPS", "UNSUPPORTED_MIRROR_MOVE_ATTACK": "PF-RUNTIME-COPY-GAPS",
    "UNSUPPORTED_MIRROR_MOVE_EFFECT": "PF-RUNTIME-COPY-GAPS", "UNSUPPORTED_HISTORY_TURN_RECORD_MISSING": "PF-RUNTIME-COPY-GAPS",
    "UNSUPPORTED_ATTACK_SOURCE_LEFT_PLAY": "PF-RUNTIME-CONTINUATION", "UNSUPPORTED_BENCH_GUARD_OUTSIDE_ATTACK": "PF-RUNTIME-CONTINUATION",
    "UNSUPPORTED_DAMAGE_OPTION_ELEMENT": "PF-RUNTIME-CONTINUATION", "UNSUPPORTED_DAMAGE_REDUCTION_DECISION": "PF-RUNTIME-CONTINUATION",
    "UNSUPPORTED_DAMAGE_STEP_ORDER": "PF-RUNTIME-CONTINUATION", "UNSUPPORTED_ENERGY_DRAIN_DECISION": "PF-RUNTIME-CONTINUATION",
    "UNSUPPORTED_ENERGY_REACTION_DURING_ATTACK": "PF-RUNTIME-CONTINUATION", "UNSUPPORTED_ESP_CONTINUATION": "PF-RUNTIME-CONTINUATION",
    "UNSUPPORTED_LEGEND_BODY_PENDING_DISCARD": "PF-RUNTIME-CONTINUATION", "UNSUPPORTED_MAX_HP_DROP_DURING_ATTACK": "PF-RUNTIME-CONTINUATION",
    "UNSUPPORTED_MIRACLE_ENERGY_DURING_EFFECT": "PF-RUNTIME-CONTINUATION", "UNSUPPORTED_PURSUIT_DAMAGE_REACTION": "PF-RUNTIME-CONTINUATION",
    "UNSUPPORTED_ATTACH_TRIGGER_ORDER": "PF-RUNTIME-CONTINUATION", "UNSUPPORTED_SECRET_PLAN_LOST_TARGET": "PF-RUNTIME-CONTINUATION",
    "UNSUPPORTED_FACE_UP_DECK_PATH": "PF-RUNTIME-CONTINUATION", "UNSUPPORTED_DECISION_AFTER_DAMAGE_TRIGGER": "PF-RUNTIME-CONTINUATION",
    "UNSUPPORTED_PREFLIGHT_LIMIT": "PF-RUNTIME-SEARCH-LIMIT", "UNSUPPORTED_SECRET_PLAN_IDENTITIES": "PF-RUNTIME-SEARCH-LIMIT",
    "UNSUPPORTED_COLOR_READINGS_LIMIT": "PF-RUNTIME-SEARCH-LIMIT", "UNSUPPORTED_BERRY_ORDER_LIMIT": "PF-RUNTIME-SEARCH-LIMIT",
    "UNSUPPORTED_POKEMON_CHECK_CHAR_COINS": "PF-RUNTIME-SEARCH-LIMIT", "UNSUPPORTED_UNBOUNDED_COIN_PREFLIGHT": "PF-RUNTIME-SEARCH-LIMIT",
    "UNSUPPORTED_QUIZ_HEIGHT_WITHOUT_DEX": "PF-RUNTIME-DATA", "UNSUPPORTED_QUIZ_HEIGHT_NOT_AVAILABLE": "PF-RUNTIME-DATA",
    "UNSUPPORTED_HISTORY_DAMAGE_PLACE_UNKNOWN": "PF-RUNTIME-DATA", "UNSUPPORTED_SUDDEN_DEATH_INITIAL_DECK": "PF-RUNTIME-DATA",
    "UNSUPPORTED_DECISION": "PF-RUNTIME-DATA",  # v0.140: この版が扱えない決定の再開先（後の版・前の版の状態の写し。docs/prize-order-user-rule-v0.140.md 3 章）
    "UNRESOLVED_RULING": "PF-RUNTIME-GENERIC",
}

# 1 つのコードに、発生条件・対処の違う事例が混在するもの（コードは改名・分割しない。台帳の下位の事例として分ける）
CASES = {
    "UNRESOLVED_SEARCH_TRAINER_WITHOUT_TARGET": [
        {"case": "deck", "sites": ["kyuura_engine/effects.py:17340", "kyuura_engine/effects.py:40040"],
         "condition": "山札に選べるカードがあると、配分を読まない下限（effects.deck_target_lower_bound）で確かめられない（エネルギー転送・ボスのやりかた・タケシの育て方・遺跡の石版）",
         "secret_dependency": "owner_known_pool",
         "note": "v0.137 で修正（PSP-ST1-DECK-ORACLE）。本人に見えない自分のカードの集合と公開の枚数だけで決める。分類の時点（基点 3e25ac5。sites は effects.py:17289・:39921）は"
                 "実際の山札を読み、山札とサイドのどちらにあるかで受理・拒否が変わった（depends_on_hidden）。v0.137 の記録の sites は effects.py:17330・:39969（v0.138 の編集で行がずれた）"},
        {"case": "discard", "sites": ["kyuura_engine/effects.py:17553"], "condition": "トラッシュにカードがない（リサイクル）", "secret_dependency": "public_only", "note": "トラッシュは公開"},
    ],
    "UNRESOLVED_STATED_CARDS_SHORT": [
        {"case": "deck-contents", "sites": ["kyuura_engine/effects.py:31159"],
         "condition": "エネルギーアークで、山札の基本エネルギーカードがコインの枚数以上あると、配分を読まない下限（effects.deck_target_lower_bound）で確かめられない",
         "secret_dependency": "owner_known_pool",
         "note": "v0.137 で修正（PSP-FC1-ENERGY-ARK-ORACLE）。分類の時点（基点 3e25ac5。effects.py:31101）は実際の山札の枚数を読み、理由の文にも枚数を書いていた（depends_on_hidden）。v0.137 の記録の site は effects.py:31143（v0.138 の編集で行がずれた）"},
        {"case": "public-counts", "sites": ["kyuura_engine/effects.py:17450", "kyuura_engine/effects.py:18380", "kyuura_engine/effects.py:31230", "kyuura_engine/effects.py:31332",
                                            "kyuura_engine/effects.py:31918", "kyuura_engine/effects.py:31987", "kyuura_engine/effects.py:32049"],
         "condition": "手札・場・サイドの枚数・相手の手札の枚数など（メンテナンス・クルミ・クイズ・カードめくりゲーム・ロケット団の暗躍など）", "secret_dependency": "unchecked_per_site",
         "note": "数を読む領域は静的に公開（枚数）と読んだが、行ごとの比較プローブはしていない。v0.137・v0.138 で変えていない（v0.137 の記録の sites は 17440・18370・31207・31309・31895・31964・32026。v0.138 の編集で行がずれた）"},
    ],
    "UNRESOLVED_TRAINER_UP_TO_WITHOUT_TARGET": [
        {"case": "amplifier-deck", "sites": ["kyuura_engine/effects.py:31232", "kyuura_engine/effects.py:31237"],
         "condition": "エネルギー増幅装置で、特殊エネルギーカードをもどすとき、もどしたあとの山札に基本エネルギーカードがあると、配分を読まない下限（effects.deck_target_lower_bound）で確かめられない"
                      "（使う宣言: 手札のエネルギーカードがどれもそうなら。段階 1 の答え: その特殊エネルギーカードを選ぶと）",
         "secret_dependency": "owner_known_pool",
         "note": "v0.138 で修正（PSP-UPZ2-ENERGY-AMPLIFIER-ORACLE）。v0.137 まで（effects.py:31209・_blocked）は実際の山札に基本エネルギーカードがあるかを読み、使う宣言・段階 1 の答えの受理・拒否が"
                 "山札とサイドのどちらにあるかで変わった（depends_on_hidden）。基本エネルギーカードをもどす答えはいつも止めない"},
        {"case": "public-zones", "sites": ["kyuura_engine/effects.py:31081", "kyuura_engine/effects.py:34598"],
         "condition": "エネルギーチャージのトラッシュのエネルギーカード、育て屋さんの組の場のポケモン（どちらも公開の領域）", "secret_dependency": "public_only",
         "note": "v0.138 で変えていない（行ごとの比較プローブはしていない）"},
    ],
    "UNRESOLVED_FACE_UP_DECK_HIDDEN_TAKE": [
        {"case": "draw", "sites": ["kyuura_engine/faceup.py"], "condition": "おもてのカードが上からの並びの途中にある山札から 2 枚以上を引く（いちばん上だけは止めない）",
         "secret_dependency": "public_only", "note": "印（face_up_count）は公開"},
        {"case": "quiz-precheck", "sites": ["kyuura_engine/effects.py quiz_draw_outcome_stop"], "condition": "クイズその1〜3・性格判定・カードめくりゲームを使う前に、正誤の両方の引き方を確かめて止める（v0.135・v0.136）",
         "secret_dependency": "public_only", "note": "保守的な制限: 片方の結果だけなら進められる場面も止める。漏れは修正済み（GAP-*-REJECTION-ORACLE）。FU3 は未解決"},
        {"case": "decision-halt", "sites": ["kyuura_engine/engine.py:874"], "condition": "決定への答えのどれでも FU3 などに当たる", "secret_dependency": "public_only",
         "note": "答えのない決定を残さず、その前の状態で HALTED"},
    ],
    "UNRESOLVED_MULLIGAN_COMPENSATION": [
        {"case": "initial-setup", "sites": ["kyuura_engine/engine.py:515"], "condition": "最初の対戦の準備", "secret_dependency": "public_only", "note": "道具の対戦で観測（legal_sequence）"},
        {"case": "sudden-death-segment", "sites": ["kyuura_engine/engine.py:515"], "condition": "v0.134 の延長戦の区間の準備（同じ処理）", "secret_dependency": "public_only",
         "note": "延長戦の区間のまま HALTED。止まった状態からは延長戦を始める操作も受け付けない（docs/sudden-death-v0.134.md 6 章）"},
    ],
    "UNRESOLVED_PLAY_AS_POKEMON_SETUP": [
        {"case": "initial-setup", "sites": ["kyuura_engine/engine.py:494"], "condition": "最初の対戦の準備で、手札になにかの化石・ピッピ人形がある", "secret_dependency": "public_only", "note": ""},
        {"case": "sudden-death-segment", "sites": ["kyuura_engine/engine.py:494"], "condition": "延長戦の区間の準備（同じ処理）", "secret_dependency": "public_only", "note": ""},
    ],
    "UNRESOLVED_EVOLUTION_PERMISSION_FROM_DECK": [
        {"case": "coin-evolve-self-from-deck", "sites": ["kyuura_engine/effects.py:12383"], "condition": "キョウのスピアーなどの特殊能力の使う前の確かめで、山札の同じ名前のカードを読む",
         "secret_dependency": "depends_on_hidden_static", "note": "PSP-DECK-CONTENT-PRECHECKS（静的な候補。比較プローブはしていない）"},
        {"case": "other", "sites": [], "condition": "そのほかの経路", "secret_dependency": "unchecked_per_site", "note": ""},
    ],
    "UNRESOLVED_SCRAM_TIMING": [
        {"case": "pokemon-check", "sites": ["kyuura_engine/procedures.py:312"], "condition": "ポケモンチェックの途中で残りHPが「10」を通る", "secret_dependency": "public_only", "note": "HALTED"},
        {"case": "command", "sites": [], "condition": "コマンドの処理の中（道具の対戦で拒否を観測）", "secret_dependency": "public_only", "note": "拒否"},
    ],
}

# v0.137（docs/deck-search-oracle-v0.137.md）: 利用者の承認（2026-11-02「情報漏れ2件を先に修正すること」。厳密モードの定義・不足時の規約・プレイ用の規約の承認ではない）を受けて直した
# 2 項目の記録。発見の記録（found_in・trigger・reachability・impact）は分類の時点のまま残し、修正の内容・制限・検証を加える
V137_FIX_COMMON = {
    "fix": ("使う前の確かめを、実際の山札の候補の数から、配分を読まない下限 effects.deck_target_lower_bound に替えた。本人に見えない自分のカード（山札のうら・うらのサイド・見られない"
            "置いておくカード。effects.unseen_card_pool）のうち目的のカードが K 枚、山札の外の見えないカードが C 枚なら、山札に少なくとも max(0, K - C) 枚（鳩の巣の原理）。K は 2 つを合わせた"
            "集合（持ち主が所有するカードから見えるカードを除いたもの。デッキリストと両者が見た所有者の変更から持ち主が知っている）、C は公開の枚数だけで決まり、配分によらない。"
            "下限が必要な枚数に足りなければ、既存のコードのまま使う前に止める（理由の文は決まった文）"),
    "fix_limitations": ["実際には山札に目的のカードがあっても、下限が足りなければ使う前に止める（保守的な制限）",
                        "フラッシュでおもてにした山札のカード・過去に見た山札の内容は数えない（保守的）",
                        ("受理（使った事実は公開）は、相手・観戦者に「使ったプレイヤーの見えないカードのうち目的のカードが C + 必要な枚数以上ある」ことを伝える（分類の時点は「山札に必要な枚数以上ある」。"
                         "どちらも使ったプレイヤーの非公開の情報で、相手は試せない。docs/deck-search-oracle-v0.137.md 4.4 節）")],
    "fix_verification": ["tests/test_deck_search_oracle_v0_137.py（twin_command_problems に owner_knowledge を加えて、配分だけが違う状態を比べる）",
                         "docs/deck-search-oracle-v0.137.md 2 章（修正の前の再現: 構築盤面と、new_game からの合法な操作の列 seed 18・1）・10 章（検証）"],
    "status_basis": "v0.137 で漏れを修正。研究の論点（ST1・FC1）は未解決のまま。厳密モードの定義・プレイ用の規約は決めていない",
}
V137_FIX_ST1 = {**V137_FIX_COMMON, "fix_sites": ["kyuura_engine/effects.py SearchDeckTrainer.check_playable", "kyuura_engine/effects.py BenchNameGroupFromDeckTrainer.check_playable"]}
V137_FIX_FC1 = {**V137_FIX_COMMON, "fix_sites": ["kyuura_engine/effects.py CoinsSearchBasicEnergyPerHeads.check_playable"]}
# v0.138（docs/oracle-leak-fixes-v0.138.md）: 利用者の承認（2026-11-03「v0.137 で新たに見つかった 2 件の情報漏れを、モード共通の不具合として修正すること」。厳密モードの定義・プレイ用の
# 規約・検索の不足時の処理の承認ではない）を受けて直した 2 項目の記録。発見の記録（found_in・trigger・reachability・impact）は v0.137 のまま残し、修正の内容・制限・検証を加える
V138_FIX_COMMON = {
    "fixed_in": "v0.138（docs/oracle-leak-fixes-v0.138.md。基点 903a9bd）",
    "status_basis": "v0.138 で漏れを修正。研究の論点（GG1・MG1・DW1・UPZ2・ST1）は未解決のまま。厳密モードの定義・プレイ用の規約・検索の不足時の処理は決めていない",
    "fix_verification": ["tests/test_oracle_leak_fixes_v0_138.py（twin_command_problems に owner_knowledge を加えて、配分だけが違う状態を比べる。修正の前の木では failures 49・errors 18）",
                         "docs/oracle-leak-fixes-v0.138.md 2 章（修正の前の再現: 構築盤面と合法な操作の列）・9 章（検証）"],
}
V138_FIX_RUIN_WALL = {**V138_FIX_COMMON,
    "fix": ("使う前の確かめを、実際の山札の候補（bench_entry_unresolved。どれも止めるなら最後のカードの理由の文）から、配分を読まない下限 effects.bench_entry_unconfirmed に替えた。本人に"
            "見えない自分のカードのうち、アンノーン（たね）でベンチに出しても止めない（goop_gas_entry_check に当たらない）カードが U 枚、山札の外の見えないカードが C 枚なら、山札に少なくとも"
            "max(0, U - C) 枚（effects.deck_lower_bound_where。止めるかはカードの定義と公開の場の効果・持ち主だけで決まる）。1 より少なければ、止める効果のコード（GG1・MG1・DW1）と決まった文"
            "（コードの決まった理由 + effects.BENCH_ENTRY_UNCONFIRMED_DETAIL。カードの名前・uid・特殊能力の名前・枚数を書かない）で止める"),
    "fix_sites": ["kyuura_engine/effects.py bench_entry_unconfirmed・deck_lower_bound_where", "kyuura_engine/effects.py BenchNameGroupFromDeckTrainer.check_playable"],
    "fix_limitations": [("写しのアンノーンはどれも特殊能力を持つので、受理・拒否・コードは v0.137 と同じ（変わったのは理由の文だけ）。止めないカードと止めるカードが混ざる候補（今の写しにはない）では、"
                        "止めないカードが実際には山札にあっても下限が足りなければ止める（保守的な制限。共通処理のテストで確かめる）"),
                        "選んだあとの決定（山札をさがすので本人が見る）の選ぶと止める選択・理由の文は、今までどおり実際の山札の候補で決める",
                        "同じ bench_entry_unresolved を使う［INCREASE］の使う機会は変えていない（PSP-INCREASE-ENTRY-PW3-ORACLE。別の項目）"],
}
V138_FIX_AMPLIFIER = {**V138_FIX_COMMON,
    "fix": ("使う宣言・段階 1（手札からもどすカード）の UPZ2 の印（_blocked）を、実際の山札の基本エネルギーカードの有無から、配分を読まない下限 effects.deck_target_lower_bound に替えた。"
            "基本エネルギーカードをもどす答えは、もどしたカードが山札の基本エネルギーカードになるのでいつも止めない。特殊エネルギーカードをもどす答えは、下限が 1 以上のときだけ止めない。"
            "手札のエネルギーカードのどれも止める印なら使う前に止める（コードは UPZ2 のまま。理由の文は決まった文 effects.AMPLIFIER_UNCONFIRMED_REASON）"),
    "fix_sites": ["kyuura_engine/effects.py ReturnHandEnergyThenCoinSearchBasicEnergy._blocked・check_playable・resolve"],
    "fix_limitations": [("実際には山札に基本エネルギーカードがあっても、下限が 0 なら、特殊エネルギーカードをもどす答え（手札がそれだけなら使う宣言）を止める（保守的な制限。"
                        "サイド 6 枚の間は、見えない基本エネルギーカード 7 枚以上が要る）"),
                        ("受理（使った事実・もどしたカードは公開）は、相手・観戦者に「特殊エネルギーカードをもどしたなら、使ったプレイヤーの見えない基本エネルギーカードが C + 1 枚以上ある」ことを"
                        "伝える（v0.137 までは「山札に基本エネルギーカードがある」。どちらも使ったプレイヤーの非公開の情報で、相手は試せない。docs 5.4 節）")],
}
V137_NEW_FINDINGS = [
    {"id": "PSP-RUIN-WALL-BLOCKED-REASON-ORACLE", "entry_kind": "silent_information_leak", "status": "fixed", "classification": "A",
     "found_in": "v0.137 の作業（PSP-DECK-CONTENT-PRECHECKS の比較プローブ。基点 897103e）", **V138_FIX_RUIN_WALL,
     "summary": "遺跡の石版で、山札の候補のアンノーンがどれもベンチに出すと止めるカード（ベトベトガスの GG1 など）のとき、拒否の理由の文が最後に確かめた山札のカードの名前・uid を書く",
     "trigger": "BenchNameGroupFromDeckTrainer.check_playable（kyuura_engine/effects.py:39973）の bench_entry_unresolved の理由の文（goop_gas_entry_check の文はカードの uid・名前を含む）",
     "related_cards": ["neo2-054", "neo2-057"], "related_codes": ["UNRESOLVED_GOOP_GAS_NEW_POKEMON"],
     "reachability": {"status": "constructed_board",
                      "evidence": ["docs/deck-search-oracle-v0.137.md 9 章（見えないアンノーン[E]・[R] がサイド 1 枚と山札に分かれる 2 つの状態で、受理・コードは同じ、理由の文が違う）"],
                      "note": "合法な操作の列での再現はしていない。同じ bench_entry_unresolved を使うほかの経路（effects.py:36663・:40085・:40097）はプローブしていない"},
     "impact": "カードを使わずに、山札に（サイドではなく）どのアンノーンがあるかが理由の文から分かる。受理・拒否・コードは配分によらない（アンノーンはどれも特殊能力を持つので、止めるかは同じ）",
     "play_groups": ["5"], "mode_policy": "両モードで塞ぐ候補（修正は別の作業。v0.137 では変えていない）", "decision_refs": ["DEC-INFO-LEAK-FIXES"]},
    {"id": "PSP-UPZ2-ENERGY-AMPLIFIER-ORACLE", "entry_kind": "silent_information_leak", "status": "fixed", "classification": "A",
     "found_in": "v0.137 の作業（同じ型の横断。基点 897103e）", **V138_FIX_AMPLIFIER,
     "summary": "エネルギー増幅装置（neo4-102）の使う前の UPZ2 の拒否が、基本エネルギーカードが山札とサイドのどちらにあるかで変わる（手札のエネルギーカードが特殊エネルギーだけのとき）",
     "trigger": "ReturnHandEnergyThenCoinSearchBasicEnergy.check_playable（kyuura_engine/effects.py:31209）・_blocked（山札に基本エネルギーカードがあるかを実際の山札で読む）",
     "related_cards": ["neo4-102"], "related_codes": ["UNRESOLVED_TRAINER_UP_TO_WITHOUT_TARGET"],
     "reachability": {"status": "constructed_board",
                      "evidence": ["docs/deck-search-oracle-v0.137.md 9 章（手札に無色2個エネルギーだけ、炎エネルギー 1 枚が山札の盤面は受理、サイドの盤面は UPZ2。twin_command_problems が段 0 で検出）"],
                      "note": "合法な操作の列での再現はしていない"},
     "impact": "カードを使わずに、山札に基本エネルギーカードがあるか（＝サイドにあるか）を知れる", "play_groups": ["5"],
     "mode_policy": "両モードで塞ぐ候補（修正は別の作業。v0.137 では変えていない）", "decision_refs": ["DEC-INFO-LEAK-FIXES"]},
]
# v0.138 の作業で、今回触った共通処理（bench_entry_unresolved）のまわりと PSP-DECK-CONTENT-PRECHECKS の残りを比較プローブで確かめて見つけた項目（修正していない。承認の範囲の外）
V138_NEW_FINDINGS = [
    {"id": "PSP-INCREASE-ENTRY-PW3-ORACLE", "entry_kind": "silent_information_leak", "status": "active", "classification": "A",
     "found_in": "v0.138 の作業（bench_entry_unresolved を使うほかの経路の比較プローブ。基点 903a9bd）",
     "summary": "アンノーンI（neo2-023）の［INCREASE］の使う機会の決定で「使う」を答えると、山札に「アンノーン」がない（サイドにある）ときだけ PW3 で拒否される",
     "trigger": "BenchNameGroupFromDeckOnEntry.accept_problem（実際の山札の候補を読む）→ offer_entry_power の unresolved_choices（観測には出ないが、答えの受理・拒否で分かる）",
     "related_cards": ["neo2-023"], "related_codes": ["UNRESOLVED_POWER_ZERO_CARDS"],
     "reachability": {"status": "constructed_board",
                      "evidence": [("C:/dev/kyuura-engine-verification-v0.138/scripts/probe_routes_v0138.py (a)（見えないアンノーン[E] 1 枚が山札／サイド 1 枚。手札のアンノーンI をベンチに出す → "
                                   "「使う」の答えが受理／UNRESOLVED_POWER_ZERO_CARDS。twin_command_problems が段 1 で検出。「使わない」の答えは同じ）"),
                                   "docs/oracle-leak-fixes-v0.138.md 7 章"],
                      "note": "合法な操作の列での再現はしていない。基点と v0.138 で出力は同じ（v0.138 の修正はこの経路を変えていない）"},
     "impact": "アンノーンI を出すたびに、山札にアンノーンがあるか（＝サイドにあるか）を、拒否のあと「使わない」を答え直すことで、費用なしに知れる。まきちらせ!ベトベトガスなどのもとでは"
               "アンノーンI 自体を出せない（GG1 など）ので、［INCREASE］の「どれも止める」の理由の文の経路には届かない",
     "play_groups": ["5"], "mode_policy": "両モードで塞ぐ候補（修正は別の作業。v0.138 では変えていない）", "decision_refs": ["DEC-INFO-LEAK-FIXES"]},
    {"id": "PSP-COCOON-DV2-ORACLE", "entry_kind": "silent_information_leak", "status": "active", "classification": "A",
     "found_in": "v0.138 の作業（PSP-DECK-CONTENT-PRECHECKS の残りの比較プローブ。基点 903a9bd）",
     "summary": "キョウのコクーン（PMCG6-011）の［うか］の使う前の DV2（今の番に退化した）の拒否が、キョウのスピアーが山札とサイドのどちらにあるかで変わる",
     "trigger": "CoinEvolveSelfFromDeck.check_usable（実際の山札の「キョウのスピアー」を deck_evolution_devolved_pairs に渡す。山札になければ組がなく、受理）",
     "related_cards": ["PMCG6-011", "PMCG6-018"], "related_codes": ["UNRESOLVED_EVOLVE_AFTER_DEVOLUTION"],
     "reachability": {"status": "constructed_board",
                      "evidence": [("C:/dev/kyuura-engine-verification-v0.138/scripts/probe_routes_v0138.py (b)（キョウのスピアーを退化スプレーで 1 枚はがした（合法な操作）キョウのコクーン。"
                                   "見えないキョウのスピアー 1 枚が山札／サイド 1 枚。使う宣言が UNRESOLVED_EVOLVE_AFTER_DEVOLUTION／受理。twin_command_problems が段 0 で検出）"),
                                   "docs/oracle-leak-fixes-v0.138.md 7 章"],
                      "note": "合法な操作の列（new_game から）での再現はしていない。GV1（PERMISSION_FROM_DECK）・UNRESOLVED_EVOLUTION_HP の経路はプローブしていない"},
     "impact": "退化スプレーのあと、カードを使わずに（拒否は状態を変えない）、山札にキョウのスピアーがあるかを知れる",
     "play_groups": ["5"], "mode_policy": "両モードで塞ぐ候補（修正は別の作業。v0.138 では変えていない）", "decision_refs": ["DEC-INFO-LEAK-FIXES"]},
]
# 分類の後の更新（基点・集計の履歴は BASE・COUNTS_AT_CLASSIFICATION に残し、書き換えない）
UPDATES = [
    {"version": "0.137.0", "work": "情報漏れ 2 件の修正（PSP-ST1-DECK-ORACLE・PSP-FC1-ENERGY-ARK-ORACLE）", "document": "docs/deck-search-oracle-v0.137.md",
     "base": {"commit": "897103e4b67f670d1c223bb83d9a0a95c394cd2f", "branch_of_base": "main（PR #30 のマージ。v0.134〜v0.136 と停止の方針の分類を含む）"},
     "approval": "利用者の承認は「情報漏れ2件を先に修正すること」だけ。厳密モードの定義・不足時の規約・プレイ用の規約・既存の利用者指定の扱いは decision_required のまま",
     "changed_entries": ["PSP-ST1-DECK-ORACLE（fixed）", "PSP-FC1-ENERGY-ARK-ORACLE（fixed）", "UNRESOLVED_SEARCH_TRAINER_WITHOUT_TARGET#deck・UNRESOLVED_STATED_CARDS_SHORT#deck-contents（secret_dependency）",
                         "PSP-DECK-CONTENT-PRECHECKS（v0137_followup）"],
     "new_entries": ["PSP-RUIN-WALL-BLOCKED-REASON-ORACLE（active。修正していない）", "PSP-UPZ2-ENERGY-AMPLIFIER-ORACLE（active。修正していない）"],
     "unchanged": "研究の停止コード（ST1・FC1 を含む）は active のまま（停止コードを修正済みにしない）。族・規約・判断事項・方針の案は変えていない"},
    {"version": "0.138.0", "work": "情報漏れ 2 件の修正（PSP-RUIN-WALL-BLOCKED-REASON-ORACLE・PSP-UPZ2-ENERGY-AMPLIFIER-ORACLE）", "document": "docs/oracle-leak-fixes-v0.138.md",
     "base": {"commit": "903a9bdce6505c1881fbca154c38ff0761c49ba4", "branch_of_base": "main（PR #31 のマージ。v0.137 の最後 6473470 と同じ木）"},
     "approval": "利用者の承認は「v0.137 で新たに見つかった 2 件の情報漏れを、モード共通の不具合として修正すること」だけ（2026-11-03）。厳密モードの定義・プレイ用の規約・検索の不足時の処理は"
                 "decision_required のまま",
     "changed_entries": ["PSP-RUIN-WALL-BLOCKED-REASON-ORACLE（fixed）", "PSP-UPZ2-ENERGY-AMPLIFIER-ORACLE（fixed）", "UNRESOLVED_TRAINER_UP_TO_WITHOUT_TARGET（事例 amplifier-deck・public-zones を加えた）",
                         "PSP-DECK-CONTENT-PRECHECKS（v0138_followup）",
                         "事例の sites の行番号（ST1 #deck・#discard、FC1 #deck-contents・#public-counts。effects.py の編集で行がずれただけ。意味は変えていない。前の行は note に残した）"],
     "new_entries": ["PSP-INCREASE-ENTRY-PW3-ORACLE（active。修正していない）", "PSP-COCOON-DV2-ORACLE（active。修正していない）"],
     "unchanged": "研究の停止コード（GG1・MG1・DW1・UPZ2・ST1 を含む）は active のまま（停止コードを修正済みにしない）。族・規約・判断事項・方針の案は変えていない"},
    {"version": "0.138.0（版は変えない。文書・台帳・作成スクリプトだけ）", "work": "モードの定義の合意の反映と、規約集合の設計（docs/ruleset-mode-design.md・docs/ruleset-mode-decisions.md）",
     "document": "docs/ruleset-mode-design.md",
     "base": {"commit": "1bf94a13cae33ac4e07082fc88f0f07b431908b8", "branch_of_base": "main（PR #32 のマージ。v0.138 の最後 42e00f6 と同じ木）"},
     "approval": ("利用者の合意は mode_agreements の 6 項目（2026-11-03。本会話の利用者の指示。公式の裁定・kyuura の研究上の解決ではない）。規約集合の識別・採用の単位・途中の変更・"
                  "旧保存状態・不足した構成の開始・デバッグ用の構成・個々の続行規約は decision_required のまま"),
     "changed_entries": ["mode_definitions（合意済みの定義。STRICT-A・STRICT-B は履歴）", "conventions（baseline_category・対象・効果・承認の記録。利用者指定 12 件は user_agreed、ほかの 6 件は decision_required）",
                         "conventions の user_ids（簡略ルールの 4 対象を登録と同じ 1 つずつに直した）", "decision_status（DEC-STRICT-DEFINITION は agreed、DEC-EXISTING-USER-SPECS は partly_agreed）"],
     "new_entries": ["mode_agreements（AGR-MODE-* の 6 項目）", "判断事項 8 つ（DEC-RULESET-VERSIONING ほか。docs/ruleset-mode-decisions.md）"],
     "unchanged": "停止コード・事例・問題の項目・族・安全境界・方針の案は変えていない。エンジン・既存のテスト・カードデータ・保存形式は変えていない"},
]
# 分類の時点（基点 3e25ac5）の集計（counts）の写し。今の counts は現行コードから作り直した値
COUNTS_AT_CLASSIFICATION = {"research_stop_codes": 316, "runtime_codes_outside_table": 40, "runtime_codes_outside_table_active": 39, "test_tool_only_codes": 8, "cases": 15, "codes_with_cases": 7, "problems_new": 4, "problems_from_inventory": 28, "conventions": 18, "internal_guard_sites_current": 602, "internal_guard_sites_matched_to_inventory": 600, "internal_guard_sites_new_since_inventory": ["kyuura_engine/engine.py:445", "kyuura_engine/resolution/programs.py:10739"], "safety_boundaries": 8, "families": 23, "decisions": 29, "by_reachability": {"constructed_board": 145, "legal_sequence": 25, "static_only": 185}, "by_family": {"PF-COPY-TRANSFORM": 34, "PF-DAMAGE-SCOPE": 22, "PF-EFFECT-TIMING": 13, "PF-ENERGY-TYPE": 21, "PF-ESP-REDO": 4, "PF-HIDDEN-INFORMATION": 8, "PF-HISTORY-LASTING": 20, "PF-KNOCKOUT-TIMING": 15, "PF-POWER-SUPPRESSION": 11, "PF-PROTECTED-TARGET-EFFECT": 12, "PF-REACTION-DURING-PROCESS": 10, "PF-RUNTIME-CONTINUATION": 15, "PF-RUNTIME-COPY-GAPS": 5, "PF-RUNTIME-DATA": 5, "PF-RUNTIME-GENERIC": 1, "PF-RUNTIME-REGISTRY": 7, "PF-RUNTIME-SEARCH-LIMIT": 6, "PF-SETUP-PLAY-AS-POKEMON": 5, "PF-SIMULTANEOUS-ORDER": 26, "PF-STATED-COUNT-SHORT": 11, "PF-TEXT-READING": 34, "PF-UP-TO-ZERO": 13, "PF-USE-WITHOUT-EFFECT": 57}, "by_play_group": {"1": 316, "2": 39, "3": 89, "4": 6, "5": 20, "6": 1}, "by_mechanism": {"answer_rejection": 13, "command_rejection": 339, "deck_validation": 1, "deferred_interruption": 2, "pokemon_check_halt": 10, "setup_halt": 2}, "by_status": {"active": 402, "fixed": 5, "historical": 2, "unverified": 1}, "note": "停止コード・事例・規約・内部ガードは別の数。事例はコードの下位で、コードの数に足さない。棚卸しと同じ項目は独立した不足として数えない"}

# 新しく見つけた項目・後の版で変わった項目（v0.133 の棚卸しにない、またはその後に状態が変わったもの）
PROBLEMS = [
    {"id": "PSP-ST1-DECK-ORACLE", "entry_kind": "silent_information_leak", "status": "fixed", "classification": "A", "found_in": "この分類の作業（基点 3e25ac5）",
     "fixed_in": "v0.137（docs/deck-search-oracle-v0.137.md。基点 897103e）", **V137_FIX_ST1,
     "summary": "山札から決まったカードを選ぶトレーナー（エネルギー転送など。選ばなくてよいと書かれていないもの）の使う前の ST1 の拒否が、そのカードが山札とサイドのどちらにあるかで変わる",
     "trigger": "SearchDeckTrainer.check_playable（kyuura_engine/effects.py:17289）・BenchNameGroupFromDeckTrainer.check_playable（:39921）。使う人の山札に選べるカードがないと、使う前に UNRESOLVED_SEARCH_TRAINER_WITHOUT_TARGET",
     "related_cards": ["PMCG3-044", "PMCG4-060", "PMCG5-077", "neo2-054", "neo2-057"], "related_codes": ["UNRESOLVED_SEARCH_TRAINER_WITHOUT_TARGET"],
     "reachability": {"status": "constructed_board", "evidence": ["C:/dev/kyuura-engine-verification/stop-policy/probe_st1.py（エネルギー転送。炎エネルギーが山札の盤面は受理、サイドの盤面は ST1。twin_command_problems が段 0 で検出）"],
                      "note": "条件（必要なカードがサイドに入る）は通常の準備で起こりうるが、合法な操作の列での再現はしていない"},
     "impact": "カードを使わずに（費用・カードを消費せずに）、山札に目的のカードがあるか＝サイドにあるかを知れる。拒否は状態を変えないので、毎番くりかえせる",
     "play_groups": ["5", "1"], "mode_policy": "両モードで漏れを塞ぐ（PF-USE-WITHOUT-EFFECT の P-UWE-1 だけでは塞がらない）。塞ぎ方は v0.135・v0.136 と同じ型（公開の情報だけで決める・止める）か、P-UWE-2（使えて、探して見つからない）",
     "decision_refs": ["DEC-INFO-LEAK-FIXES", "DEC-USE-WITHOUT-EFFECT"], "inventory_root_cause": "QUIZ-CONDITIONAL-DRAW-REJECTION-ORACLE と同じ型（拒否の受理可否による漏れ）"},
    {"id": "PSP-FC1-ENERGY-ARK-ORACLE", "entry_kind": "silent_information_leak", "status": "fixed", "classification": "A", "found_in": "この分類の作業（基点 3e25ac5）",
     "fixed_in": "v0.137（docs/deck-search-oracle-v0.137.md。基点 897103e）", **V137_FIX_FC1,
     "summary": "エネルギーアーク（neo2-053）の使う前の FC1 の拒否が、基本エネルギーカードが山札とサイドのどちらにあるかで変わる",
     "trigger": "CoinsSearchBasicEnergyPerHeads.check_playable（kyuura_engine/effects.py:31101）。山札の基本エネルギーカードがコインの枚数（2）より少ないと UNRESOLVED_STATED_CARDS_SHORT",
     "related_cards": ["neo2-053"], "related_codes": ["UNRESOLVED_STATED_CARDS_SHORT"],
     "reachability": {"status": "constructed_board", "evidence": ["C:/dev/kyuura-engine-verification/stop-policy/probe_fc1.py（山札に 2 枚の盤面は受理、1 枚が山札・1 枚がサイドの盤面は FC1。twin_command_problems が段 0 で検出）"],
                      "note": "合法な操作の列での再現はしていない"},
     "impact": "カードを使わずに、山札の基本エネルギーカードが 2 枚以上あるかを知れる", "play_groups": ["5", "1"],
     "mode_policy": "両モードで漏れを塞ぐ。数の不足の規約（PF-STATED-COUNT-SHORT）の P-SCS-2 は、この事例では採らない",
     "decision_refs": ["DEC-INFO-LEAK-FIXES", "DEC-STATED-COUNT-SHORT"], "inventory_root_cause": "同上"},
    {"id": "PSP-DECK-CONTENT-PRECHECKS", "entry_kind": "information_leak_candidate", "status": "unverified", "classification": "A", "found_in": "この分類の作業（静的な横断）",
     "summary": "使う前の確かめ（check_playable・check_usable）が山札の中身を読んで UnsupportedError で止める、ほかの経路（比較プローブはしていない）",
     "trigger": "CoinEvolveSelfFromDeck.check_usable（effects.py:12375。山札の同じ名前のカードで GV1・DV2・UNRESOLVED_EVOLUTION_HP）、BenchNameGroupFromDeckTrainer の bench_entry_unresolved（effects.py:39924。山札の候補のどれもベンチに出すと止めるなら止める）",
     "v0137_followup": ("v0.137 で比較プローブをした: bench_entry_unresolved（遺跡の石版）は受理・コードは配分によらないが、理由の文が山札のカードの名前・uid を書く漏れを確認し、"
                        "PSP-RUIN-WALL-BLOCKED-REASON-ORACLE に分けた（修正していない）。CoinEvolveSelfFromDeck はプローブしていない（キョウのコクーン HP 60・キョウのスピアー HP 80 で、"
                        "UNRESOLVED_EVOLUTION_HP の盤面は通常のダメージでは作れない。GV1・DV2 の盤面も作っていない）。v0.137 の共通処理（deck_target_lower_bound）はこの 2 つの経路を変えていない"),
     "v0138_followup": ("v0.138 で PSP-RUIN-WALL-BLOCKED-REASON-ORACLE を修正した。CoinEvolveSelfFromDeck（キョウのコクーンの［うか］）の DV2 を比較プローブで確かめ、配分で受理・拒否が変わる漏れを"
                        "確認して PSP-COCOON-DV2-ORACLE に分けた（修正していない）。同じクラスの GV1（PERMISSION_FROM_DECK）・UNRESOLVED_EVOLUTION_HP の経路はプローブしていない（未確認の候補のまま）。"
                        "bench_entry_unresolved を使うほかの経路のうち、［INCREASE］の使う機会は PSP-INCREASE-ENTRY-PW3-ORACLE に分けた。［ぶんれつ］・［マグネット］は使う前に山札を読まない"
                        "（選んだあとの決定だけ。本人が山札を見る）"),
     "related_cards": ["neo2-054", "neo2-057"], "related_codes": ["UNRESOLVED_EVOLUTION_PERMISSION_FROM_DECK", "UNRESOLVED_EVOLVE_AFTER_DEVOLUTION", "UNRESOLVED_EVOLUTION_HP"],
     "reachability": {"status": "static_only", "evidence": ["scripts/stop_policy_scan.py の外で行った AST の横断（check_playable・check_usable で .deck・deck_cards_matching を読み UnsupportedError を投げる 19 クラスのうち、中身を読むもの）"]},
     "impact": "確かめれば PSP-ST1 と同じ型の漏れの可能性。熱血!（FV1。effects.py:29159）は山札とサイドを合わせて読むので、分け方に依存しない（候補から外した）",
     "play_groups": ["5"], "mode_policy": "比較プローブで確かめるまで、漏れとも安全とも数えない", "decision_refs": ["DEC-INFO-LEAK-FIXES"]},
    *V137_NEW_FINDINGS,
    *V138_NEW_FINDINGS,
    {"id": "SUDDEN_DEATH_NOT_IMPLEMENTED", "entry_kind": "nonprefix_stop", "status": "fixed", "classification": "A", "found_in": "v0.133 の棚卸し（P0）",
     "summary": "v0.134 で StartSuddenDeath を加えた。サドン・デスの状態にほかのコマンドを送ると IllegalActionError SUDDEN_DEATH_NOT_STARTED（UnsupportedError ではない）",
     "trigger": "Phase.SUDDEN_DEATH", "related_cards": [], "related_codes": ["SUDDEN_DEATH_NOT_STARTED", "NOT_SUDDEN_DEATH", "UNSUPPORTED_SUDDEN_DEATH_INITIAL_DECK"],
     "reachability": {"status": "constructed_board", "evidence": ["tests/test_sudden_death_v0_134.py", "tools/sudden_death_games.py（v0.134 の正式な対戦）"]},
     "impact": "延長戦を始めない既存の経路は変えていない。延長戦は自動では始めない（外から StartSuddenDeath を送る契約）", "play_groups": ["6"],
     "mode_policy": "モードによらない（停止ではなく、外から開始の操作を送る契約）。USER-SUDDEN-DEATH-OWNERSHIP-RESET は CONV に記録", "decision_refs": ["DEC-STRICT-DEFINITION"],
     "inventory_ref": "SUDDEN_DEATH_NOT_IMPLEMENTED"},
]

# 採用済みの利用者指定・独自規約（既存の挙動。今回は無効化も公式扱いもしない）
CONVENTIONS_EXTRA = [
    {"id": "CONV:USER-SUDDEN-DEATH-OWNERSHIP-RESET", "kind": "user_specified_rule", "user_ids": ["USER-SUDDEN-DEATH-OWNERSHIP-RESET"], "related_cards": ["PR1-027"], "scope": "延長戦を始めるときの、とりかえっこプリーズで所有者が変わったカード",
     "source": "docs/sudden-death-v0.134.md 2.2 節（利用者の指定 2026-11-02）・kyuura_engine/sudden_death.py USER_SUDDEN_DEATH_OWNERSHIP_RESET",
     "inventory_ref": None, "note": "v0.133 の棚卸しの後に加わった。UQ-SWAP-PLEASE-OWNERSHIP は未解決のまま"},
    # v0.140（docs/prize-order-user-rule-v0.140.md 2 章）: カードによらないサイドを取る順番の利用者の指定 2 件（decisions.USER_PRIZE_ORDER_RULES）
    {"id": "CONV:USER-PRIZE-ORDER-ALWAYS-CHOSEN", "kind": "user_specified_procedure", "user_ids": ["USER-PRIZE-ORDER-ALWAYS-CHOSEN"], "related_cards": [],
     "scope": "同じきぜつの処理で両方のプレイヤーがサイドを取るとき（先に取るプレイヤーの決定 prize_first）",
     "source": "docs/prize-order-user-rule-v0.140.md 2 章（利用者の指定 2026-11-03）・kyuura_engine/decisions.py USER_PRIZE_ORDER_ALWAYS_CHOSEN", "inventory_ref": None,
     "note": "v0.139 の「おもてのサイドがあるときだけ」の条件と、v0.2f の正規化を置きかえた。p.325 の一般規定・その当てはめの導出とは別の記録"},
    {"id": "CONV:USER-PRIZE-ORDER-PER-PLAYER", "kind": "user_specified_procedure", "user_ids": ["USER-PRIZE-ORDER-PER-PLAYER"], "related_cards": [],
     "scope": "先に取るプレイヤーが選ばれたあとの、両方のサイドを取る並び",
     "source": "docs/prize-order-user-rule-v0.140.md 2 章（利用者の指定 2026-11-03）・kyuura_engine/decisions.py USER_PRIZE_ORDER_PER_PLAYER", "inventory_ref": None,
     "note": "v0.139 の「1 枚ごとに次の人を選ぶ」実装上の仮定（ADD-PRIZE-ORDER-UNIT-ASSUMPTION）を置きかえた"},
    {"id": "CONV:ENGINE-USER-CORRECTION:PR1-069/name.ja", "kind": "user_provided_data_correction", "user_ids": [], "related_cards": ["PR1-069"], "scope": "PR1-069 の名前（kyuura の値「？？？」をミュウにした）",
     "source": "research_links.json engine_user_corrections・scripts/extract_kyuura_cards.py ENGINE_USER_CORRECTIONS（v0.70）", "inventory_ref": None,
     "note": "データの修正で、裁定ではない。v0.133 の棚卸しの採用済み 16 件には入っていない"},
]
# 対象ごとの USER-ID（登録の記録 effects.USER_SIMPLIFICATIONS などの rule と同じ。--check が登録と照らす）。分類の時点（3e25ac5〜v0.138）は簡略ルールの 4 対象に 2 つの ID を
# 両方書いていたが、登録では誕生日（PR1-044・PR1-090）と発話（PR1-072）は別の対象。この作業で登録に合わせて直した（docs/ruleset-mode-design.md 4.3 節）
CONVENTION_USER_IDS = {
    "POLICY:user_simplified_text:PR1-044/attack/0": ["USER-BIRTHDAY-COIN-ONLY"],
    "POLICY:user_simplified_text:PR1-072/attack/0": ["USER-SPOKEN-CONDITION-IGNORED"],
    "POLICY:user_simplified_text:PR1-072/attack/1": ["USER-SPOKEN-CONDITION-IGNORED"],
    "POLICY:user_simplified_text:PR1-090/attack/0": ["USER-BIRTHDAY-COIN-ONLY"],
    "POLICY:user_specified_references:GD5-016/trainer": ["USER-QUIZ-HEIGHT-OFFICIAL-ZUKAN"],
    "POLICY:user_specified_rules:PR1-027/trainer": ["USER-SWAP-OWNERSHIP-RECEIVER"],
    "POLICY:user_specified_rules:neo1-049/power/0": ["USER-MIND-GAMES-OPTIONAL-BEFORE-COST"],
    "POLICY:user_specified_rules:neo4-082/attack/0": ["USER-MOUNTAIN-CRUSH-MILL-UP-TO-DECK"],
    "POLICY:user_specified_rules:neo4-082/attack/1": ["USER-DESTRUCTIVE-FIRE-DECLARE-ORDER-UP-TO"],
    "POLICY:user_specified_names:PR1-075/name": ["USER-BILINGUAL-NAME-JAPANESE"],
    "POLICY:user_specified_names:PR1-077/name": ["USER-BILINGUAL-NAME-JAPANESE"],
}

# 基礎集合の区分（docs/ruleset-mode-design.md 4 章）。conventions の各項目は、このどれか 1 つ
BASELINE_CATEGORIES = {
    "user_specified": "利用者が明示的に指定した記録（指定の文・日・根拠の文書がある）。AGR-MODE-BASELINE-USER で両モードの基礎集合に入れる",
    "engine_simplification": "エンジンが記録している簡略化（利用者の指定の記録はない）。基礎集合に入れるかは未決（DEC-BASELINE-NONUSER）",
    "implementation_assumption": "実装上の仮定・エンジンの採用の仕様（公式に決まったことにしない）。基礎集合に入れるかは未決（DEC-BASELINE-NONUSER）",
    "card_data_correction": "カードのデータの訂正（写しの作り直しで当てはめる）。規約集合ではなくカードデータの層で識別する案（DEC-CARD-DATA-CORRECTIONS）",
}
# 登録の記録（対象・効果を名前だけでなく確かめる。--check が、登録の対象の鍵と USER-ID が同じことを照らす）
REGISTRY_OF_KIND = {
    "user_simplified_text": "effects.USER_SIMPLIFICATIONS", "user_specified_references": "effects.USER_SPECIFIED_REFERENCES",
    "user_specified_rules": "effects.USER_SPECIFIED_RULES", "user_specified_names": "effects.USER_SPECIFIED_NAMES",
}
_BIRTHDAY = {"category": "user_specified",
             "approval": {"document": "docs/deferred-shortage-user-promos-v0.127.md 4.1 節", "on": "2026-11-01", "instruction": "のピカチュウについては誕生日の確認をせずに通常のコイントスのみ"},
             "effect": "おたんじょうびの「今日がこのカードの持ち主の誕生日なら」を処理にふくめない。どの日もコイン 1 枚、「おもて」なら 50 追加（30+50）",
             "affects": ["ワザのダメージ（コイン 1 枚）", "乱数（どの日もコインを投げる）"],
             "not_covered": ["誕生日・日付・実名の入力（作らない。「いつも誕生日」とは記録しない）", "コスト・こんらんのコイン・弱点・抵抗力・ESP のやり直し（通常どおり）", "ほかのカードの日付・現実の条件"]}
_SPOKEN = {"category": "user_specified",
           "approval": {"document": "docs/deferred-shortage-user-promos-v0.127.md 4.1 節", "on": "2026-11-01", "instruction": "ハマちゃんのヤドキングに関しては発話要件を無視して実装"},
           "affects": ["ワザを使えるか（発話の条件で拒否しない）"],
           "not_covered": ["発話の申告・回数・音声（作らない）", "ほかのカードの発話・動作の条件（PMCG6-074 は別の記録の engine_simplification）"]}
CONVENTION_DETAILS = {
    "POLICY:user_simplified_text:PR1-044/attack/0": {**_BIRTHDAY, "target": "_のピカチュウ PR1-044 のワザ 0（おたんじょうび）"},
    "POLICY:user_simplified_text:PR1-090/attack/0": {**_BIRTHDAY, "target": "_のピカチュウ PR1-090 のワザ 0（おたんじょうび）"},
    "POLICY:user_simplified_text:PR1-072/attack/0": {**_SPOKEN, "target": "ハマちゃんのヤドキング PR1-072 のワザ 0（こまったなあ）",
                                                     "effect": "「「こまったなぁ」と3回つぶやかないとこのワザは使えない」を処理にふくめない。自分と相手の対戦ポケモンをこんらんにする"},
    "POLICY:user_simplified_text:PR1-072/attack/1": {**_SPOKEN, "target": "ハマちゃんのヤドキング PR1-072 のワザ 1（どつく）",
                                                     "effect": "「「ええのかなあ」と3回つぶやかないとこのワザは使えない」を処理にふくめない。相手の対戦ポケモンに 20（通常の計算）"},
    "POLICY:user_specified_references:GD5-016/trainer": {
        "category": "user_specified", "target": "カツラのクイズ その1 GD5-016 の正解",
        "approval": {"document": "docs/blaines-quiz-heights-v0.129.md 3 章", "on": "2026-11-01", "instruction": "クイズの正解には、今回収集した全国図鑑No.001〜251の通常の姿の公式図鑑値を採用します。"},
        "effect": "置いたカードの全国図鑑番号の種族の身長（公式図鑑の整数 cm。kyuura 9242b9b の値）を正解にし、答えが完全に同じなら正解",
        "affects": ["クイズの正誤（どちらが 2 枚引くか）", "図鑑番号のないカードの扱い（GAP-QUIZ-REFERENCE-DATA）"],
        "not_covered": ["処理に使う文面（印刷のまま）", "印刷の身長・カードの時期の図鑑の値と同じとは確かめていない", "その2・その3（GD5 以外のクイズ）の正解"]},
    "POLICY:user_specified_rules:PR1-027/trainer": {
        "category": "user_specified", "target": "とりかえっこプリーズ PR1-027 で交換が成立した 2 枚",
        "approval": {"document": "docs/trade-please-ownership-v0.130.md 3 章", "on": "2026-11-01", "instruction": "交換が成立した2枚は、対戦終了まで、それぞれの受取側が所有者になります。"},
        "effect": "2 枚それぞれの対戦の中の所有者を、受け取ったプレイヤーにする（片方だけを変えない）。再交換も同じ規則。トラッシュ・山札・サイド・場に置く処理は新しい所有者を基準にする",
        "affects": ["カードの行き先（所有者のゾーン）", "保存形式 33 の ownership_changes・origin", "延長戦の開始（USER-SUDDEN-DEATH-OWNERSHIP-RESET が出所にもどす）"],
        "not_covered": ["実物の所有権・次の対戦（CR-SWAP-PLEASE-REAL-TRADE-SEPARATE）", "錯乱ジムでかわりに使うときの「あなた」「相手」（UQ-CHAOS-GYM-BORROWED-TURN。止める）",
                        "あとから重ねた進化カード・つけたエネルギー・どうぐの所有者（変えない）", "デッキの構築の制限の当てはめ直し（しない）"]},
    "POLICY:user_specified_rules:neo1-049/power/0": {
        "category": "user_specified", "target": "ヤドキング neo1-049 の［ちえくらべ］",
        "approval": {"document": "docs/slowking-mind-games-v0.132.md 3 章", "on": "2026-11-01", "instruction": "発動は任意とし、順序を次のようにします。"},
        "effect": "相手がトレーナーを手札から出して使うとき: 状態を変えずに使えるか確かめる → ヤドキング側が使うか選ぶ（任意）→ 使うならコイン 1 回 →「おもて」なら使えず相手の山札の上（コスト・効果なし）→「うら」・使わないなら通常どおり",
        "affects": ["トレーナーの使用の可否", "乱数（使うと選んだときだけコイン）", "決定（使うかの選択）"],
        "not_covered": ["錯乱ジムのコインとの前後（MG1 で止める。DEC-CHAOS-GYM-MIND-GAMES。この指定の延長として扱えるかは未決）", "ポケモンとして出すトレーナー（MG2）",
                        "使ったら番が終わるトレーナーが使えなかったときの番（MG3）", "おもてのカードのある山札の上の向き（FU4）", "使えないトレーナーの宣言では選択もコインも出さない"]},
    "POLICY:user_specified_rules:neo4-082/attack/0": {
        "category": "user_specified", "target": "ひかるバンギラス neo4-082 のワザ 0（マウンテンクラッシュ）",
        "approval": {"document": "docs/shining-tyranitar-v0.133.md 3.1 節", "on": "2026-11-01", "instruction": "おもての数と相手の残り山札枚数の少ない方だけ、山札の上からトラッシュする。"},
        "effect": "「うら」が出るまでコインを投げ（山札 0 枚でも省かない）、「おもて」の数と相手の山札の枚数の少ない方だけトラッシュ。山札が空になっただけでは負けにしない",
        "affects": ["相手の山札の枚数", "乱数（コインを省かない）"],
        "not_covered": ["ほかのカードの「足りなければあるだけ」（たつまき FC1・ドライアップ DU1・怪電波マシーン TW1/TW2・HC6・MW1・FU1 などの止め方は変えない）", "相手のポケモンへの防護を山札へ当てはめるか（当てはめない既存の扱い）"]},
    "POLICY:user_specified_rules:neo4-082/attack/1": {
        "category": "user_specified", "target": "ひかるバンギラス neo4-082 のワザ 1（はかいのほのお）",
        "approval": {"document": "docs/shining-tyranitar-v0.133.md 3.2 節", "on": "2026-11-01", "instruction": "以下の順序を採用します。"},
        "effect": "炎エネルギーカード 0 枚なら宣言を拒否（状態を変えない）。1 枚以上ならその枚数のコイン →「おもて」の数の自分の炎をトラッシュ → 50 → 「おもて」の数の相手のエネルギー（足りなければすべて）",
        "affects": ["ワザを使えるか", "要素の順番（p.309 の「まずダメージ」と違う並び）", "相手のエネルギーの枚数"],
        "not_covered": ["特殊エネルギーを「炎」エネルギーカードに数えるか（UQ-SPECIAL-ENERGY-AS-TYPED-ENERGY。既存の止め方）", "ほかのカードの順番・数の不足の扱い"]},
    "POLICY:user_specified_names:PR1-075/name": {
        "category": "user_specified", "target": "ナッシー［Exeggutor］PR1-075 の名前・進化元・ワザ名",
        "approval": {"document": "docs/exeggutor-bilingual-names-v0.131.md 3 章", "on": "2026-11-01", "instruction": "対象2枚の英語併記は翻訳表示として扱い、判定に使いません。"},
        "effect": "判定には日本語の部分（ナッシー・タマタマ・ふみつけ）を使い、英語の併記は翻訳の表示として判定に使わない",
        "affects": ["デッキの同じ名前 4 枚の数え方（通常のナッシーと合わせる）", "進化元（タマタマから進化）", "名前を指定する効果・同じ名前を比べる効果", "カツラのクイズ その1・その3 の答えと伝える名前",
                    "変身したあとの名前", "ワザ名で比べる効果・ログ・観測"],
        "not_covered": ["名前以外の性能（このカードの写しの値のまま。通常のナッシーに置きかえない）", "ほかのカードの括弧書き・英語の名前", "英語だけの「Exeggutor」を別名として受け付けること"],
        "display_only": False},
    "POLICY:user_specified_names:PR1-077/name": {
        "category": "user_specified", "target": "ナッシー［Exeggutor］PR1-077 の名前・進化元・ワザ名",
        "approval": {"document": "docs/exeggutor-bilingual-names-v0.131.md 3 章", "on": "2026-11-01", "instruction": "対象2枚の英語併記は翻訳表示として扱い、判定に使いません。"},
        "effect": "PR1-075 と同じ（判定には日本語の部分を使う）", "affects": ["PR1-075 と同じ（同名制限・進化・名前を指定する効果・クイズ・変身・ワザ名）"],
        "not_covered": ["PR1-075 と同じ"], "display_only": False},
    "POLICY:engine_simplified_text:PMCG6-074/attack/0": {
        "category": "engine_simplification", "target": "イマクニ？のドードー PMCG6-074 のワザ 0（ハモる）",
        "basis": "docs/final-pmcg-cards-v0.68.md 4 章（エンジンの簡略化した仕様。利用者の指定の記録はない）",
        "effect": "歌を歌う状態・歌い終わりの通知を作らず、ふつうのワザとして相手の対戦ポケモンに 30", "affects": ["ワザのダメージ"], "not_covered": ["ほかのカードの動作の条件"]},
    "POLICY:engine_simplified_text:PMCG6-074/power/0": {
        "category": "engine_simplification", "target": "イマクニ？のドードー PMCG6-074 の特殊能力（にげまくり）",
        "basis": "docs/final-pmcg-cards-v0.68.md 4 章（エンジンの簡略化した仕様。利用者の指定の記録はない）",
        "effect": "カードを投げる動作を処理にふくめない。特殊能力は状態・ログ・乱数を変えず宣言できない。にげるは通常の規定", "affects": ["特殊能力の宣言の可否"], "not_covered": ["ほかのカードの動作の条件"]},
    "POLICY:implementation_assumption:1": {
        "category": "implementation_assumption", "target": "「ふしちょう」とサイド・勝ち負け・バトル場に出すの順番（P27・P28・P30。UQ-PHOENIX-KO-PROCESS-ORDER）",
        "basis": "docs/post-knockout-powers-v0.12.md 3 章（どの順番でも行き先・サイド・出せるポケモン・勝ち負け・乱数が変わらないことを確かめた正規化）",
        "effect": "選ばせずに「サイド → 勝ち負けの判定 →（続くなら）ふしちょう → バトル場に出す」に正規化", "affects": ["決定の順番（結果は同じと確かめた範囲）"],
        "not_covered": ["同時のきぜつで、番のプレイヤーがバトル場に出すポケモンを選ぶときに、相手の「ふしちょう」の使用を知っているか（正規化した順番の 1 つ）"]},
    "POLICY:implementation_assumption:2": {
        "category": "implementation_assumption", "target": "キョウのベトベトン PMCG6-023 の［だつりょくえき］の宣言（DR1・DR12。UQ-ENERGY-DRAIN-DECLARATION）",
        "basis": ("docs/final-pmcg-cards-v0.68.md 3 章（エンジンの採用の仕様。根拠は 2002-05-24 の Q&A・『トレーナーズ』Vol.13 で、2000.02.14 版の裁定ではない。"
                  "後年の資料を根拠にした採用で、CLAUDE.md の「後年の裁定で補わない」との関係は未判断。利用者の指定の記録はない）"),
        "effect": "自動的にはたらく（使わない選択・「おもて」のあとトラッシュしない選択はない）", "affects": ["決定の有無", "乱数（条件を満たせば必ずコイン）"],
        "not_covered": ["2002 年のほかの変更（持ち込まない）", "ほかの特殊能力の宣言"]},
    "POLICY:implementation_assumption:3": {
        "category": "implementation_assumption", "target": "キョウのベトベトン PMCG6-023 の［だつりょくえき］を処理する時点（DR6。UQ-ENERGY-DRAIN-TIMING）",
        "basis": "docs/final-pmcg-cards-v0.68.md 3 章（p.89 のこうらがえしの解説の時点を当てはめた類推。エンジンの採用の仕様。利用者の指定の記録はない）",
        "effect": "そのワザのすべての対象へのダメージのあと、ダメージ以外の効果の前", "affects": ["効果の順番（ほかの効果の前提）"], "not_covered": ["ダメージとほかの効果を交互に与える並び（GK1 のまま）"]},
    "CONV:USER-SUDDEN-DEATH-OWNERSHIP-RESET": {
        "category": "user_specified", "target": "延長戦を始めるとき（StartSuddenDeath）の、とりかえっこプリーズで所有者が変わったカード",
        "approval": {"document": "docs/sudden-death-v0.134.md 2.2 節", "on": "2026-11-02", "instruction": "とりかえっこプリーズで交換したカードは、元の所有者へ戻す。"},
        "effect": "そのカードを最初のデッキに入れたプレイヤー（出所 origin）のデッキにもどす（交換の直前の所有者ではない。再交換があっても最初の出所）。新しい区間の所有者の変更の記録は空から",
        "affects": ["延長戦の区間のデッキの中身", "保存形式 34 の segments"], "not_covered": ["同じ区間の中の交換（USER-SWAP-OWNERSHIP-RECEIVER のまま）", "実物の所有権・対戦の外の返し方"],
        "registry": "sudden_death.USER_SUDDEN_DEATH_OWNERSHIP_RESET"},
    "CONV:USER-PRIZE-ORDER-ALWAYS-CHOSEN": {
        "category": "user_specified", "target": "同じきぜつの処理で両方のプレイヤーがサイドを取るとき",
        "approval": {"document": "docs/prize-order-user-rule-v0.140.md 2.1 節", "on": "2026-11-03", "instruction": "両方のプレイヤーがサイドを取る場合は、表向き・うら向きや特殊能力の有無によらず、番のプレイヤーが先に取る人を選ぶ。"},
        "effect": "いつも番のプレイヤーに先に取るプレイヤーの決定（prize_first）を出す。おもてのサイド・［おみとおし］・本人だけが知るサイドで出すかどうかを変えない",
        "affects": ["決定の有無", "サイドを取る順番", "決定の時点の観測"], "not_covered": ["一方だけが取るとき（決定を出さない）", "トレーナー・特殊能力でサイドを取る処理（マチスの交渉）", "取ったサイドの位置の観測（今のまま。承認ではない）"],
        "registry": "decisions.USER_PRIZE_ORDER_RULES['USER-PRIZE-ORDER-ALWAYS-CHOSEN']"},
    "CONV:USER-PRIZE-ORDER-PER-PLAYER": {
        "category": "user_specified", "target": "先に取るプレイヤーを選んだあとの、両方のサイドを取る並び",
        "approval": {"document": "docs/prize-order-user-rule-v0.140.md 2.1 節", "on": "2026-11-03", "instruction": "先に選ばれたプレイヤーが必要な枚数を取り終え、その後、もう一方が必要な枚数を取る。1枚ごとの交互取得は認めない。"},
        "effect": "先に選ばれたプレイヤーがその処理の分をすべて取ってから、もう一方が取る。1 枚ごとに選び直さない",
        "affects": ["サイドを取る順番", "決定の数", "決定の時点の観測"], "not_covered": ["勝ち負け・サドン・デスの判定（すべて取ってから。v0.2f のまま）", "p.325 で順番を決める単位の公式の読み"],
        "registry": "decisions.USER_PRIZE_ORDER_RULES['USER-PRIZE-ORDER-PER-PLAYER']"},
    "CONV:ENGINE-USER-CORRECTION:PR1-069/name.ja": {
        "category": "card_data_correction", "target": "PR1-069 の名前（kyuura の値「？？？」）",
        "basis": "research_links.json engine_user_corrections（v0.70。利用者がミュウと同定し画像と資料の URL を示した。エンジンは画像を見ていない。kyuura の記録ではない）",
        "effect": "写しの作り直しで名前を「ミュウ」にする", "affects": ["デッキの同じ名前 4 枚の数え方", "名前を指定する効果・同じ名前を比べる効果", "クイズで伝える名前・観測・ログ"],
        "not_covered": ["名前以外の値"], "display_only": False, "user_provided": True,
        "registry": "scripts/extract_kyuura_cards.py ENGINE_USER_CORRECTIONS"},
}

# 両モードで維持する安全境界（内部ガードを独立した未裁定として数えない。棚卸しの GUARD:* を参照する）
SAFETY_BOUNDARIES = [
    {"id": "SB-NO-SILENT-SKIP", "rule": "未対応・未裁定を「効果がないもの」として処理しない（UnsupportedError の原則。errors.py）。内部例外を一括捕捉して効果なしで続ける案を採らない",
     "applies": "両モード", "evidence": ["kyuura_engine/errors.py UnsupportedError の説明", "remediation-plan R10"]},
    {"id": "SB-REJECTION-PURITY", "rule": "拒否は状態・乱数・ログを変えない（複製の上で処理）。拒否と途中停止（DeferredShortage）・HALTED を区別する", "applies": "両モード",
     "evidence": ["kyuura_engine/errors.py の冒頭", "tests/log_audit.py command_outcome の state_changed の確かめ", "kyuura_engine/interruption.py"]},
    {"id": "SB-SECRET-INDEPENDENCE", "rule": "受理・拒否・コード・理由の文・候補が、見る人に見えない情報に依存しない（twin_command_problems・_identity_independent）", "applies": "両モード",
     "evidence": ["tests/log_audit.py twin_command_problems", "kyuura_engine/engine.py _apply_checked（うらのカード）", "PSP-ST1-DECK-ORACLE・PSP-FC1-ENERGY-ARK-ORACLE はこの境界の違反"]},
    {"id": "SB-STATE-INTEGRITY", "rule": "カードの保存則・場の形・決定と段階の対応などの不変条件（StateIntegrityError・check_invariants）", "applies": "両モード",
     "guard_selector": {"types": ["StateIntegrityError"], "paths": ["kyuura_engine/zones.py", "kyuura_engine/checks.py"]}, "evidence": ["kyuura_engine/checks.py", "tests/test_state_integrity.py"]},
    {"id": "SB-ENGINE-BUG-GUARDS", "rule": "「エンジンの不具合」を示す RuntimeError・NotImplementedError・UnsupportedByKernel（呼び出しの約束・登録の形・到達しないはずの分岐）。合法な操作の列で起きたら最小の再現を付けて A に再分類する",
     "applies": "両モード", "guard_selector": {"types": ["RuntimeError", "NotImplementedError", "UnsupportedByKernel"]}, "evidence": ["remediation-plan R10"]},
    {"id": "SB-INPUT-VALIDATION", "rule": "不正な入力（コマンドの項目・番・段階・デッキの検査）を IllegalActionError・DeckValidationError で拒否する（ルール上の不正で、停止の方針の対象ではない）",
     "applies": "両モード", "evidence": ["kyuura_engine/commands.py check_command_fields", "kyuura_engine/deck.py"]},
    {"id": "SB-RECORD-REPLAY", "rule": "保存・復元・ログ・観測に、結果を再現する情報（乱数の状態・決定・途中停止の記録・区間）を残す。旧形式で足りない値を推測で埋めない", "applies": "両モード",
     "evidence": ["kyuura_engine/serialize.py FORMAT_VERSIONS", "UNSUPPORTED_HISTORY_DAMAGE_PLACE_UNKNOWN", "UNSUPPORTED_SUDDEN_DEATH_INITIAL_DECK"]},
    {"id": "SB-NO-FAIL-OPEN-SEARCH", "rule": "探索の上限で、未探索の枝を安全とみなさない（今 fail-open の 3 経路は GAP-ANSWER-SEARCH-FAIL-OPEN として要調査）", "applies": "両モード",
     "evidence": ["GAP-ANSWER-SEARCH-FAIL-OPEN", "UNSUPPORTED_PREFLIGHT_LIMIT"]},
]

DECISIONS = [
    "DEC-STRICT-DEFINITION", "DEC-RULESET-IDENTITY", "DEC-EXISTING-USER-SPECS", "DEC-INFO-LEAK-FIXES", "DEC-MULLIGAN-COMPENSATION", "DEC-SLEEP-COIN-ORDER",
    "DEC-CHAOS-GYM-MIND-GAMES", "DEC-USE-WITHOUT-EFFECT", "DEC-UP-TO-ZERO", "DEC-STATED-COUNT-SHORT", "DEC-ORDER-RULE", "DEC-DEFERRED-RESUME", "DEC-SEARCH-LIMITS",
    "DEC-FACE-UP-DECK", "DEC-MODE-CHANGE-DURING-GAME", "DEC-LEGACY-STATES", "DEC-PLAY-AS-POKEMON", "DEC-KNOCKOUT-READINGS", "DEC-TIMING-READINGS", "DEC-NULLIFIED-COINS",
    "DEC-DAMAGE-READINGS", "DEC-ENERGY-READINGS", "DEC-COPY-SCOPE", "DEC-LASTING-READINGS", "DEC-TEXT-READINGS", "DEC-REACTION-READINGS", "DEC-SUPPRESSION-READINGS",
    "DEC-ESP-READINGS", "DEC-CONVENTION-GRANULARITY",
    # 規約集合の設計の作業（2026-11-03）で加えた判断事項（置き場所は docs/ruleset-mode-decisions.md）
    "DEC-RULESET-VERSIONING", "DEC-CONVENTION-CONFLICTS", "DEC-PLAY-CONFIG-INCOMPLETE-START", "DEC-PLAY-DEBUG-PARTIAL", "DEC-BASELINE-NONUSER", "DEC-BASELINE-CENSUS",
    "DEC-CARD-DATA-CORRECTIONS", "DEC-RESUME-WITH-OTHER-RULESET",
]

FAMILY_DECISION = {
    "PF-USE-WITHOUT-EFFECT": ["DEC-USE-WITHOUT-EFFECT"], "PF-UP-TO-ZERO": ["DEC-UP-TO-ZERO"], "PF-STATED-COUNT-SHORT": ["DEC-STATED-COUNT-SHORT", "DEC-DEFERRED-RESUME"],
    "PF-SIMULTANEOUS-ORDER": ["DEC-ORDER-RULE"], "PF-KNOCKOUT-TIMING": ["DEC-KNOCKOUT-READINGS"], "PF-EFFECT-TIMING": ["DEC-TIMING-READINGS"],
    "PF-PROTECTED-TARGET-EFFECT": ["DEC-NULLIFIED-COINS"], "PF-DAMAGE-SCOPE": ["DEC-DAMAGE-READINGS"], "PF-ENERGY-TYPE": ["DEC-ENERGY-READINGS"],
    "PF-COPY-TRANSFORM": ["DEC-COPY-SCOPE"], "PF-HISTORY-LASTING": ["DEC-LASTING-READINGS"], "PF-TEXT-READING": ["DEC-TEXT-READINGS"],
    "PF-REACTION-DURING-PROCESS": ["DEC-REACTION-READINGS"], "PF-POWER-SUPPRESSION": ["DEC-SUPPRESSION-READINGS"],
    "PF-SETUP-PLAY-AS-POKEMON": ["DEC-MULLIGAN-COMPENSATION", "DEC-PLAY-AS-POKEMON"], "PF-HIDDEN-INFORMATION": ["DEC-FACE-UP-DECK"], "PF-ESP-REDO": ["DEC-ESP-READINGS"],
    "PF-RUNTIME-SEARCH-LIMIT": ["DEC-SEARCH-LIMITS"],
}
CODE_DECISION = {"UNRESOLVED_MULLIGAN_COMPENSATION": ["DEC-MULLIGAN-COMPENSATION"], "UNRESOLVED_POKEMON_CHECK_SLEEP_COIN_ORDER": ["DEC-SLEEP-COIN-ORDER"],
                 "UNRESOLVED_MIND_GAMES_CHAOS_GYM_ORDER": ["DEC-CHAOS-GYM-MIND-GAMES"], "UNRESOLVED_DRY_UP_WATER_ENERGY_SHORT": ["DEC-DEFERRED-RESUME"],
                 "UNRESOLVED_THOUGHT_WAVE_MACHINE_ENERGY_SHORT": ["DEC-DEFERRED-RESUME"], "UNRESOLVED_SEARCH_TRAINER_WITHOUT_TARGET": ["DEC-INFO-LEAK-FIXES"],
                 "UNRESOLVED_STATED_CARDS_SHORT": ["DEC-INFO-LEAK-FIXES"]}

# 道具の対戦の記録（初期状態からの合法な操作の列）。リポジトリの外の検証の証拠（v0.134〜v0.136 の検証の作業で保存）。ハッシュは --write の時点で計算して台帳に書く
TOOL_EVIDENCE_ROOT = pathlib.Path("C:/dev/kyuura-engine-verification")
OBSERVATION_KEYS = ("halt_codes", "unresolved_rejections")
LABEL_CODE_RE = re.compile(r"(?:UNSUPPORTED|UNRESOLVED)_[A-Z0-9_]*[A-Z0-9]")  # 道具の記録のキー（stopped_PlayTrainer_UNRESOLVED_… の形）
TEST_ASSERT_RE = re.compile(r"assert|Raises|\.code\b")  # 表明らしい行（assert・assertRaises・例外の .code を比べる行）。halt_codes などの一覧の行は数えない


def sha256(path: pathlib.Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def content_sha256(path: pathlib.Path) -> str:
    """v0.137: リポジトリのファイルの sha256 を、改行を LF にそろえて求める（git の内容と同じ値。作業の木の改行の設定（core.autocrlf）によらない）。分類の時点の台帳の
    research_reference.sha256（de05b447…）は CRLF の作業の木で求めた値で、内容は v0.137 の基点と同じ（LF の値 74609c8d…）。"""
    return hashlib.sha256(path.read_bytes().replace(b"\r\n", b"\n")).hexdigest()


def load_json(path: pathlib.Path):
    return json.loads(path.read_text(encoding="utf-8"))


def tool_observations() -> dict:
    """証拠の JSON の ``total.halt_codes``・``total.unresolved_rejections`` のキーから、コード → [(ファイル, 種類, 数)]。証拠がなければ空（--check は台帳の記録を使う）。"""
    observed: dict[str, list] = {}
    files = []
    if not TOOL_EVIDENCE_ROOT.exists():
        return {"available": False, "files": [], "codes": {}}
    for path in sorted(TOOL_EVIDENCE_ROOT.rglob("*.json")):
        name = path.relative_to(TOOL_EVIDENCE_ROOT).as_posix()
        if "fulltest" in name or name.endswith("compare.json"):
            continue
        try:
            data = load_json(path)
        except (ValueError, UnicodeDecodeError):
            continue
        total = data.get("total") if isinstance(data, dict) else None
        if not isinstance(total, dict):
            continue
        hit = False
        for key in OBSERVATION_KEYS:
            for label, count in (total.get(key) or {}).items():
                for code in LABEL_CODE_RE.findall(label):
                    observed.setdefault(code, []).append({"file": name, "key": key, "label": label, "count": count})
                    hit = True
        if hit:
            files.append({"file": name, "sha256": sha256(path)})
    return {"available": True, "files": files, "codes": observed}


def family_of(code: str) -> str | None:
    for family, members in FAMILY_MEMBERS.items():
        if code.removeprefix("UNRESOLVED_") in members.split():
            return family
    return RUNTIME_FAMILY.get(code)


def mechanisms(code: str, engine_sites: list[str], halt_codes: dict[str, list[str]]) -> list[dict]:
    found = []
    covered = set(halt_codes.get(code, {}).get("_span", []))
    for kind, sites in halt_codes.get(code, {}).items():
        if kind == "_span":
            continue
        found.append({"mechanism": kind, "sites": sites, "basis": "static: Halt(code=…)・check_quantity(code=…) の定数"})
    if code == "UNSUPPORTED_CARD":
        return [{"mechanism": "deck_validation", "sites": engine_sites, "basis": "static: deck.py の問題の文"}]
    if code == "UNSUPPORTED_DECISION_AFTER_DAMAGE_TRIGGER":
        return [{"mechanism": "not_raised", "sites": engine_sites, "basis": "static: コメントだけ（v0.34 で解消）"}]
    family = family_of(code)
    others = [s for s in engine_sites if s not in covered]
    if others or not found:
        kind = "answer_rejection" if family == "PF-UP-TO-ZERO" else "command_rejection"
        found.append({"mechanism": kind, "sites": others[:12], "basis": "static: UnsupportedError の文字列・定数の位置（決定で HALTED に変わる共通処理を含む）"})
    return found


def halt_code_map(root: pathlib.Path) -> dict[str, dict[str, list[str]]]:
    import ast
    constants = scan.module_code_constants(root)
    result: dict[str, dict[str, list[str]]] = {}
    setup_scopes = ("_prepare_segment", "new_game", "_deal", "_setup", "_place_starting", "_mulligan")
    for path in scan.python_files(root, scan.ENGINE_DIR):
        _, tree, scopes = scan.parsed(path)
        for node in ast.walk(tree):
            name = scan._call_name(node)
            if name not in ("Halt", "check_quantity"):
                continue
            for kw in node.keywords:
                if kw.arg != "code":
                    continue
                value = kw.value
                code = None
                if isinstance(value, ast.Constant) and isinstance(value.value, str):
                    code = value.value
                elif isinstance(value, ast.Name) and value.id.isupper():
                    code = constants.get(value.id)
                elif isinstance(value, ast.Attribute) and value.attr.isupper():
                    code = constants.get(value.attr)
                if not code:
                    continue
                site = f"{scan.rel(root, path)}:{node.lineno}"
                span = [f"{scan.rel(root, path)}:{line}" for line in range(node.lineno, (node.end_lineno or node.lineno) + 1)]
                if name == "check_quantity":
                    kind = "deferred_interruption"
                elif scan.rel(root, path) == "kyuura_engine/engine.py" and any(s in scopes.get(node.lineno, "") for s in setup_scopes):
                    kind = "setup_halt"
                elif scan.rel(root, path) == "kyuura_engine/engine.py":
                    kind = "setup_halt" if code in ("UNRESOLVED_MULLIGAN_COMPENSATION", "UNRESOLVED_PLAY_AS_POKEMON_SETUP") else "dynamic_halt_conversion"
                else:
                    kind = "pokemon_check_halt"
                result.setdefault(code, {}).setdefault(kind, []).append(site)
                result.setdefault(code, {}).setdefault("_span", []).extend(span)
    return result


_LINES: dict[str, list[str]] = {}


def test_evidence(code: str, occurrences: dict, constants_for_code: list[str], test_name_index: dict[str, list[str]]) -> dict:
    lines = list(occurrences.get("tests", {}).get("literal", []))
    for const in constants_for_code:
        lines += test_name_index.get(const, [])
    assert_like, other = [], []
    for ref in sorted(set(lines)):
        path, line = ref.rsplit(":", 1)
        if path not in _LINES:
            _LINES[path] = (ROOT / path).read_text(encoding="utf-8").splitlines()
        text = _LINES[path][int(line) - 1]
        (assert_like if TEST_ASSERT_RE.search(text) else other).append(ref)
    files = sorted({r.rsplit(":", 1)[0] for r in assert_like + other})
    return {"assert_like_lines": len(assert_like), "mention_lines": len(other), "files": files[:20], "files_total": len(files),
            "meaning": "静的な行の分類（表明らしい行・それ以外）。行の実行・発生・隣の受理枝は計測していない（v0.136 の全体のテスト 7,282 件・失敗 0 は同じ指紋のコード）",
            "adjacent_accept_branch": "unknown"}


def _convention(record: dict) -> dict:
    """規約（conventions）の 1 項目。基礎集合の区分・対象・効果・承認の記録（CONVENTION_DETAILS）を加え、合意 AGR-MODE-BASELINE-USER の利用者指定だけを user_agreed にする。"""
    detail = CONVENTION_DETAILS[record["id"]]
    category = detail["category"]
    user = category == "user_specified"
    record.update({key: value for key, value in detail.items() if key != "category"})
    record["baseline_category"] = category
    if "registry" not in record and record.get("kind") in REGISTRY_OF_KIND:
        record["registry"] = f"{REGISTRY_OF_KIND[record['kind']]}['{record['id'].split(':', 2)[2]}']"
    # 既存の挙動の状態（分類の時点と同じ）: 利用者指定と、利用者が示したデータの訂正（user_provided）は user_approved。区分（基礎集合の合意の対象か）とは別の軸
    record["existing_behavior_status"] = ["user_approved", "implemented", "verified"] if user or detail.get("user_provided") else ["implemented", "verified"]
    if user:
        record["mode_policy_status"] = AGREED_CONVENTION_STATUS
        record["agreement_refs"] = ["AGR-MODE-BASELINE-USER"]
        record["modes"] = {"strict": "基礎集合の一部として今のまま", "play": "基礎集合の一部として今のまま（続行規約ではない）"}
        record["decision_refs"] = []
    else:
        record["mode_policy_status"] = "decision_required"
        record["agreement_refs"] = []
        record["modes"] = {"strict": "今の挙動のまま（基礎集合に入れるかは未決。今回は無効化しない）", "play": "同じ"}
        record["decision_refs"] = ["DEC-CARD-DATA-CORRECTIONS"] if category == "card_data_correction" else ["DEC-BASELINE-NONUSER", "DEC-BASELINE-CENSUS"]
    record["extension"] = "ほかのカード・ほかのコード・隣の場面へ自動的に広げない（対象と not_covered は記録のまま）"
    return record


def build() -> dict:
    root = ROOT
    inventory = load_json(INVENTORY)
    research = load_json(RESEARCH)
    inv_entries = {e["id"]: e for e in inventory["entries"]}
    post_audit = {e["id"]: e for e in inventory.get("post_audit_entries", [])}
    codes = scan.prefixed_codes(root)
    constants = scan.module_code_constants(root)
    by_code: dict[str, list[str]] = {}
    for name, code in constants.items():
        by_code.setdefault(code, []).append(name.split("@")[0])
    test_name_index: dict[str, list[str]] = {}
    for path in scan.python_files(root, "tests"):
        text = path.read_text(encoding="utf-8")
        for number, line in enumerate(text.splitlines(), 1):
            for name in re.findall(r"\b([A-Z][A-Z0-9_]*_(?:CODE|STOP_CODE))\b", line):
                test_name_index.setdefault(name, []).append(f"{scan.rel(root, path)}:{number}")
    halts = halt_code_map(root)
    observations = tool_observations()
    guards = scan.guard_sites(root)
    inv_guards: dict[tuple[str, str], list[tuple[str, str]]] = {}
    for e in inventory["entries"]:
        if e["entry_kind"] == "internal_guard":
            tc = e["trigger_conditions"]
            inv_guards.setdefault((tc["path"], tc["source"]), []).append((e["id"], tc.get("scope", "")))
    # (ファイル, 文) で対応させる。同じ組が複数あれば、まず関数の名前（棚卸しの scope と、現行のいちばん内側の名前）が同じものを、残りは行の順に割り当てる
    guard_ref: dict[int, str | None] = {}
    for key, recorded in inv_guards.items():
        sites = sorted((i for i, g in enumerate(guards) if (g["path"], g["source"]) == key), key=lambda i: guards[i]["line"])
        remaining = sorted(recorded, key=lambda r: int(r[0].rsplit(":", 1)[1]))
        for site in list(sites):
            name = guards[site]["scope"].rsplit(".", 1)[-1]
            match = next((r for r in remaining if r[1] and r[1].rsplit(".", 1)[-1] == name), None) if len(sites) > 1 else None
            if match is not None:
                guard_ref[site] = match[0]
                remaining.remove(match)
                sites.remove(site)
        for site, record in zip(sites, remaining):
            guard_ref[site] = record[0]
    table = research["stop_codes"]

    entries = []

    def reach(code: str, test_ev: dict, inv: dict | None) -> dict:
        seen = observations["codes"].get(code, [])
        if seen:
            return {"status": "legal_sequence", "evidence": sorted({f"{o['file']}:{o['key']}" for o in seen})[:8], "evidence_total": len({o["file"] for o in seen}),
                    "basis": "対戦の道具（new_game の固定デッキ・合法なコマンドだけを送る方策）の記録に、このコードの停止・拒否がある"}
        if code == "UNRESOLVED_MIND_GAMES_CHAOS_GYM_ORDER":
            return {"status": "legal_sequence", "evidence": ["docs/slowking-mind-games-v0.132.md（v0.132 の正式な対戦 2 局の unexpected_rejection）", "v0.136 の前の版の組 v0.132（基点・現在の両方で同じ 2 件）"],
                    "basis": "道具の正式な対戦の記録（棚卸しの supported_by_existing_boundary_test_or_release_game_report）"}
        probes = [p["id"] for p in PROBLEMS if code in p.get("related_codes", []) and p["reachability"]["status"] == "constructed_board"
                  and p["entry_kind"] == "silent_information_leak"]
        if probes:
            return {"status": "constructed_board", "evidence": [f"{pid}（比較プローブ）" for pid in probes] + test_ev["files"][:3],
                    "basis": "比較プローブで発生を確かめた（構築盤面）"}
        if test_ev["assert_like_lines"]:
            return {"status": "constructed_board", "evidence": test_ev["files"][:5], "basis": "テストに表明らしい行がある（静的）。盤面の作り方・行の実行は個別に確かめていない"}
        if inv and inv.get("reachability", {}).get("status") not in (None, "unknown"):
            return {"status": "unknown", "evidence": inv["reachability"].get("evidence", []), "basis": f"棚卸しの記録 {inv['reachability']['status']}（現行で再確認していない）"}
        if code in codes and codes[code]["engine"].get("literal"):
            return {"status": "static_only", "evidence": codes[code]["engine"]["literal"][:3], "basis": "エンジンに定義・参照がある。発生は未確認"}
        return {"status": "unknown", "evidence": [], "basis": "確かめていない"}

    def code_entry(code: str, kind: str) -> dict:
        inv = inv_entries.get(code)
        occ = codes.get(code, {"engine": {}, "tests": {}, "tools": {}})
        engine_sites = sorted(set(occ["engine"].get("literal", []) + occ["engine"].get("name", [])))
        family = family_of(code)
        test_ev = test_evidence(code, occ, by_code.get(code, []), test_name_index)
        research_rec = table.get(code)
        decisions = sorted(set(FAMILY_DECISION.get(family, []) + CODE_DECISION.get(code, [])))
        entry = {
            "id": code, "entry_kind": kind, "inventory_ref": code if inv else None, "status": "active",
            "classification": inv["classification"] if inv else ("A" if code.startswith("UNSUPPORTED_") else "C"),
            "classification_basis": ("v0.133 の棚卸しの分類を保持" if inv else "v0.133 の後に加わったコード（棚卸しの基準で分類）"),
            "priority": inv["priority"] if inv else "P2",
            "family": family,
            "research": ({"in_stop_table": True, "ruling_ids": [r.get("ruling_id") for r in research_rec["engine_rulings"]],
                          "rulings_documents": sorted({r.get("document") for r in research_rec["engine_rulings"] if r.get("document")}),
                          "kyuura_issue": research_rec.get("kyuura_issue"), "kyuura_disposition": research_rec.get("kyuura_disposition"),
                          "checked": "固定研究基準 71d1728 の対応表とエンジンの記録（ruling の文書）を参照しただけ。公式資料の再調査・kyuura の後続の記録の照合はしていない",
                          "unverified_scope": "公式資料に記述がないことの再確認、kyuura の固定コミットより後の記録"}
                         if research_rec else {"in_stop_table": False, "note": "研究の対応表の外（エンジンの未対応・技術上限・データ・汎用）"}),
            "implementation_sites": engine_sites[:12], "implementation_sites_total": len(engine_sites),
            "current_stop": mechanisms(code, engine_sites, halts),
            "tests": test_ev,
            "stress": {"tool_observations": [{k: o[k] for k in ("file", "key", "count")} for o in observations["codes"].get(code, [])][:10]},
            "play_groups": FAMILIES[family]["play_groups"] if family else [],
            "decision_refs": decisions,
            "mode_policy_status": "decision_required" if decisions else (FAMILIES[family]["mode_policy_status"] if family else "unconsidered"),
            "policy_basis": "族の案（families）。承認されていない" if family else "未検討",
        }
        entry["reachability"] = reach(code, test_ev, inv)
        if code in CASES:
            entry["cases"] = [f"{code}#{c['case']}" for c in CASES[code]]
        return entry

    for code in sorted(table):
        entries.append(code_entry(code, "research_stop_code"))
    engine_codes = sorted(c for c, v in codes.items() if v["engine"].get("literal") or v["engine"].get("comment"))
    for code in engine_codes:
        if code in table or code == "UNSUPPORTED_COMMANDS":
            continue
        entry = code_entry(code, "runtime_stop_code")
        if code == "UNSUPPORTED_DECISION_AFTER_DAMAGE_TRIGGER":
            entry["status"] = "historical"
            entry["mode_policy_status"] = "unconsidered"
            entry["policy_basis"] = "現行では投げない（v0.34 で解消）。現行の停止として数えない"
        entries.append(entry)
    test_only = sorted(c for c, v in codes.items() if not v["engine"] and (v["tests"] or v["tools"]))
    for code in test_only:
        inv = inv_entries.get(code)
        entries.append({"id": code, "entry_kind": "test_tool_only_code", "inventory_ref": code if inv else None, "status": "active",
                        "classification": inv["classification"] if inv else "E", "classification_basis": "テスト・道具の中だけのコード（合成した登録表・比べの印・文字列の断片）",
                        "family": None, "play_groups": ["6"], "decision_refs": [], "mode_policy_status": "unconsidered",
                        "reachability": {"status": "test_only_mutation", "evidence": (codes[code]["tests"].get("literal", []) + codes[code]["tools"].get("literal", []))[:3],
                                         "basis": "エンジンに定義・参照がない（静的）"},
                        "current_stop": [{"mechanism": "not_raised", "sites": [], "basis": "エンジンでは投げない"}]})
    for code, case_list in CASES.items():
        for case in case_list:
            entries.append({"id": f"{code}#{case['case']}", "entry_kind": "case", "parent": code, "status": "active", "condition": case["condition"], "sites": case["sites"],
                            "secret_dependency": case["secret_dependency"], "note": case["note"]})
    for problem in PROBLEMS:
        record = dict(problem)
        record.setdefault("inventory_ref", None)
        record["mode_policy_status"] = "decision_required" if record.get("decision_refs") else "unconsidered"
        entries.append(record)
    # 棚卸しの構造上の問題（停止コード・ガード・採用済み以外）を参照する
    for inv in inventory["entries"]:
        if inv["entry_kind"] in ("stop_code", "internal_guard", "adopted_policy") or inv["id"] == "SUDDEN_DEATH_NOT_IMPLEMENTED":
            continue
        status = {"historical_resolved": "historical", "out_of_scope": "active"}.get(inv["entry_kind"], "active")
        if inv["id"] in ("GAP-QUIZ3-REJECTION-ORACLE", "GAP-QUIZ2-REJECTION-ORACLE", "GAP-PERSONALITY-REJECTION-ORACLE"):
            status = "fixed"
        groups = {"silent_information_leak": ["5"], "technical_limit": ["4"], "representation_limit": ["6"], "preflight_overrejection": ["4"], "terminal_limitation": ["3", "1"],
                  "data_limitation": ["3"], "historical_resolved": ["6"], "fallback_review": ["5"], "out_of_scope": ["6"], "metadata_limitation": ["6"], "codeless_question": ["6"],
                  "nonprefix_stop": ["6"]}.get(inv["entry_kind"], ["6"])
        decisions = {"GAP-DEFERRED-HALT-NO-RESUME": ["DEC-DEFERRED-RESUME"], "GAP-ANSWER-SEARCH-FAIL-OPEN": ["DEC-SEARCH-LIMITS"]}.get(inv["id"], [])
        if inv["id"].startswith("LIMIT:"):
            decisions = ["DEC-SEARCH-LIMITS"]
        entries.append({"id": inv["id"], "entry_kind": inv["entry_kind"], "inventory_ref": inv["id"], "status": status, "classification": inv["classification"],
                        "classification_basis": "v0.133 の棚卸しの分類を保持", "priority": inv["priority"], "play_groups": groups, "decision_refs": decisions,
                        "mode_policy_status": "decision_required" if decisions else "unconsidered",
                        "status_basis": ("v0.135 で修正（docs/quiz-answer-rejection-v0.135.md。FU3 は未解決）" if status == "fixed" else
                                         "v0.114 で修正済みの履歴（棚卸しの記録）" if status == "historical" else "現行で再確認していない（棚卸しの記録）"),
                        "reachability": {"status": "constructed_board" if status == "fixed" else "unknown", "evidence": inv.get("reachability", {}).get("evidence", []),
                                         "basis": f"棚卸しの記録 {inv.get('reachability', {}).get('status')}"}})
    for pid, post in post_audit.items():
        entries.append({"id": pid, "entry_kind": post["entry_kind"], "inventory_ref": f"post_audit_entries:{pid}", "status": "fixed", "classification": post["classification"],
                        "classification_basis": "棚卸しの post_audit_entries（v0.135 で発見・v0.136 で修正）", "play_groups": ["5"], "decision_refs": [],
                        "mode_policy_status": "unconsidered", "status_basis": "v0.136 で修正（docs/card-flip-answer-rejection-v0.136.md。FU3 は未解決）",
                        "reachability": {"status": "constructed_board", "evidence": ["tests/test_card_flip_answer_rejection_v0_136.py"], "basis": "対のテスト"}})

    conventions = []
    for inv in inventory["entries"]:
        if inv["entry_kind"] != "adopted_policy":
            continue
        conventions.append(_convention({"id": inv["id"], "inventory_ref": inv["id"], "user_ids": CONVENTION_USER_IDS.get(inv["id"], []), "kind": inv["id"].split(":")[1],
                                        "related_cards": inv.get("related_cards", []), "source": (inv.get("research") or {}).get("reference", "")}))
    for extra in CONVENTIONS_EXTRA:
        conventions.append(_convention(dict(extra)))

    boundaries = []
    for boundary in SAFETY_BOUNDARIES:
        record = dict(boundary)
        selector = record.pop("guard_selector", None)
        if selector:
            chosen = [i for i, g in enumerate(guards) if g["type"] in selector["types"]]
            selected = [guards[i] for i in chosen]
            refs = [guard_ref.get(i) for i in chosen]
            per_file: dict[str, int] = {}
            for g in selected:
                per_file[g["path"]] = per_file.get(g["path"], 0) + 1
            record["guards"] = {"current_sites": len(selected), "inventory_refs": sum(1 for r in refs if r), "new_since_inventory": [f"{g['path']}:{g['line']}" for g, r in zip(selected, refs) if not r],
                                "per_file": dict(sorted(per_file.items()))}
        boundaries.append(record)

    research_codes = [e for e in entries if e["entry_kind"] == "research_stop_code"]
    runtime_codes = [e for e in entries if e["entry_kind"] == "runtime_stop_code"]
    counts = {
        "research_stop_codes": len(research_codes),
        "runtime_codes_outside_table": len(runtime_codes),
        "runtime_codes_outside_table_active": sum(1 for e in runtime_codes if e["status"] == "active"),
        "test_tool_only_codes": sum(1 for e in entries if e["entry_kind"] == "test_tool_only_code"),
        "cases": sum(1 for e in entries if e["entry_kind"] == "case"),
        "codes_with_cases": len(CASES),
        "problems_new": len(PROBLEMS),
        "problems_from_inventory": sum(1 for e in entries if e.get("inventory_ref") and e["entry_kind"] not in ("research_stop_code", "runtime_stop_code", "test_tool_only_code", "case")),
        "conventions": len(conventions),
        "conventions_by_category": {c: sum(1 for x in conventions if x["baseline_category"] == c) for c in BASELINE_CATEGORIES},
        "internal_guard_sites_current": len(guards),
        "internal_guard_sites_matched_to_inventory": len(guard_ref),
        "internal_guard_sites_new_since_inventory": [f"{guards[i]['path']}:{guards[i]['line']}" for i in range(len(guards)) if i not in guard_ref],
        "safety_boundaries": len(boundaries),
        "families": len(FAMILIES),
        "decisions": len(DECISIONS),
        "by_reachability": {},
        "by_family": {},
        "by_play_group": {},
        "by_mechanism": {},
        "by_status": {},
        "note": "停止コード・事例・規約・内部ガードは別の数。事例はコードの下位で、コードの数に足さない。棚卸しと同じ項目は独立した不足として数えない",
    }
    for e in research_codes + [r for r in runtime_codes if r["status"] == "active"]:
        counts["by_reachability"][e["reachability"]["status"]] = counts["by_reachability"].get(e["reachability"]["status"], 0) + 1
        counts["by_family"][e["family"]] = counts["by_family"].get(e["family"], 0) + 1
        for m in e["current_stop"]:
            counts["by_mechanism"][m["mechanism"]] = counts["by_mechanism"].get(m["mechanism"], 0) + 1
        for g in e["play_groups"]:
            counts["by_play_group"][g] = counts["by_play_group"].get(g, 0) + 1
    for e in entries:
        counts["by_status"][e["status"]] = counts["by_status"].get(e["status"], 0) + 1
    for key in ("by_reachability", "by_family", "by_play_group", "by_mechanism", "by_status"):
        counts[key] = dict(sorted(counts[key].items(), key=lambda kv: str(kv[0])))

    return {
        "schema_version": 1,
        "title": "停止コードと未対応処理の分類（厳密モード・プレイ用モードの将来の導入に向けて）",
        "scope": ("調査・分類・設計の記録。モードの実装・既存の動作・裁定・保存形式は変えていない。利用者と合意したのはモードの定義の 6 項目（mode_agreements）だけで、"
                  "既存の利用者指定を基礎集合に入れること以外の方針の案（族の候補・個々の続行規約・規約集合の識別など）は承認を受けていない"),
        "base": BASE, "kyuura": KYUURA,
        "updates": UPDATES,
        "counts_at_classification": COUNTS_AT_CLASSIFICATION,
        "inventory_reference": {"path": "docs/pre-freeze-gap-inventory.json", "baseline_commit": inventory["baseline"]["commit"], "sha256": content_sha256(INVENTORY),
                                "entries": len(inventory["entries"]), "post_audit_entries": len(inventory.get("post_audit_entries", [])),
                                "note": "v0.133 の棚卸しの基点・集計は履歴として保持し、書き換えない。この台帳は ID で参照する"},
        "research_reference": {"path": "kyuura_engine/data/research_links.json", "sha256": content_sha256(RESEARCH), "research_commit": research["research_commit"],
                               "card_data_commit": research["card_data_commit"], "declared_counts": research["counts"]},
        "axes": {"classification": inventory["methodology"]["classification"], "play_groups": PLAY_GROUPS, "reachability": REACHABILITY, "stop_mechanisms": STOP_MECHANISMS,
                 "mode_policy_status": list(MODE_POLICY_STATUS), "existing_behavior_status": list(EXISTING_BEHAVIOR_STATUS),
                 "entry_status": {"active": "現在有効", "fixed": "修正済み", "historical": "履歴項目", "unverified": "未確認（候補）"}},
        "mode_agreements": {"source": AGREEMENT_SOURCE, "agreements": AGREEMENTS},
        "mode_definitions": {"strict": next(a["statement"] for a in AGREEMENTS if a["id"] == "AGR-MODE-STRICT"),
                             "play": next(a["statement"] for a in AGREEMENTS if a["id"] == "AGR-MODE-PLAY"),
                             "status": "agreed（AGR-MODE-STRICT・AGR-MODE-PLAY。2026-11-03）",
                             "strict_options_at_classification": STRICT_DEFINITIONS, "history": MODE_DEFINITIONS_HISTORY,
                             "design": "docs/ruleset-mode-design.md"},
        "baseline_categories": BASELINE_CATEGORIES,
        "safety_conditions": SAFETY_CONDITIONS,
        "families": FAMILIES,
        "safety_boundaries": boundaries,
        "conventions": conventions,
        "decisions": DECISIONS,
        "decision_status": {d: DECISION_STATUS.get(d, {"status": "decision_required"}) | {"document": RULESET_DECISIONS_DOC if d in RULESET_DECISIONS else STOP_DECISIONS_DOC}
                            for d in DECISIONS},
        "evidence": {"tool_observation_files": observations["files"], "tool_evidence_root": str(TOOL_EVIDENCE_ROOT).replace("\\", "/"),
                     "probes": ["PSP-ST1-DECK-ORACLE", "PSP-FC1-ENERGY-ARK-ORACLE"],
                     "v0137_probes": ["PSP-ST1-DECK-ORACLE", "PSP-FC1-ENERGY-ARK-ORACLE", "PSP-RUIN-WALL-BLOCKED-REASON-ORACLE", "PSP-UPZ2-ENERGY-AMPLIFIER-ORACLE"],
                     "v0137_probe_scripts": "docs/deck-search-oracle-v0.137.md 2 章・9 章（リポジトリの外の C:/dev/kyuura-engine-verification-v0.137/。この台帳の道具の証拠の場所には置かない）",
                     "v0138_probes": ["PSP-RUIN-WALL-BLOCKED-REASON-ORACLE", "PSP-UPZ2-ENERGY-AMPLIFIER-ORACLE", "PSP-INCREASE-ENTRY-PW3-ORACLE", "PSP-COCOON-DV2-ORACLE"],
                     "v0138_probe_scripts": "docs/oracle-leak-fixes-v0.138.md 2 章・7 章（リポジトリの外の C:/dev/kyuura-engine-verification-v0.138/。この台帳の道具の証拠の場所には置かない）",
                     "probe_scripts": "docs/stop-policy-classification.md 付録（エンジンを変えない比較プローブ。tests/log_audit.py の twin_command_problems を使う）"},
        "scan": {"engine_prefixed_codes": len([c for c, v in codes.items() if v["engine"]]), "engine_literal_codes": len([c for c, v in codes.items() if v["engine"].get("literal")]),
                 "nonprefix_unsupported_literals": scan.nonprefix_unsupported(root), "halt_sites": len(scan.halt_sites(root)),
                 "guard_sites_by_type": {t: sum(1 for g in guards if g["type"] == t) for t in scan.GUARD_TYPES}},
        "counts": counts,
        "entries": entries,
    }


def check(ledger: dict, fresh: dict) -> list[str]:
    problems = []
    ids = [e["id"] for e in ledger["entries"]]
    duplicates = sorted({i for i in ids if ids.count(i) > 1})
    if duplicates:
        problems.append(f"台帳の ID が重複: {duplicates}")
    known = set(ids)
    inventory_ids = {x["id"] for x in load_json(INVENTORY)["entries"]}
    for e in ledger["entries"]:
        for case in e.get("cases", []):
            if case not in known:
                problems.append(f"{e['id']}: 事例 {case} がない")
        if e["entry_kind"] == "case" and e["parent"] not in known:
            problems.append(f"{e['id']}: 親 {e['parent']} がない")
        for ref in e.get("decision_refs", []):
            if ref not in ledger["decisions"]:
                problems.append(f"{e['id']}: 判断事項 {ref} がない")
        family = e.get("family")
        if family is not None and family not in ledger["families"]:
            problems.append(f"{e['id']}: 族 {family} がない")
        if e["entry_kind"] in ("research_stop_code", "runtime_stop_code") and e["status"] == "active" and family is None:
            problems.append(f"{e['id']}: 族がない")
        if e.get("mode_policy_status") not in (None, *MODE_POLICY_STATUS):
            problems.append(f"{e['id']}: 方針の状態 {e.get('mode_policy_status')} は、今回の台帳で使わない（承認済み・実装済み・検証済みにしない）")
        if e.get("decision_refs") and e.get("mode_policy_status") != "decision_required":
            problems.append(f"{e['id']}: 判断事項があるのに decision_required でない")
        reach = e.get("reachability")
        if reach is not None:
            if reach["status"] not in REACHABILITY:
                problems.append(f"{e['id']}: 到達可能性 {reach['status']} が軸にない")
            if reach["status"] in ("legal_sequence", "constructed_board") and not reach.get("evidence"):
                problems.append(f"{e['id']}: 到達可能性 {reach['status']} に証拠がない")
        if "unreachable" in json.dumps(e, ensure_ascii=False):
            problems.append(f"{e['id']}: 到達不能の主張（根拠の軸がない）")
        if e.get("inventory_ref") and e["entry_kind"] != "case":
            ref = e["inventory_ref"]
            if not (ref.startswith("post_audit_entries:") or ref in inventory_ids):
                problems.append(f"{e['id']}: 棚卸しの参照 {ref} がない")
    for family, members in FAMILY_MEMBERS.items():
        for member in members.split():
            if f"UNRESOLVED_{member}" not in ledger_ids(ledger, "research_stop_code"):
                problems.append(f"族 {family} のメンバー UNRESOLVED_{member} が研究の対応表にない")
    all_members = [m for members in FAMILY_MEMBERS.values() for m in members.split()]
    if len(all_members) != len(set(all_members)):
        problems.append(f"族のメンバーが重複: {sorted({m for m in all_members if all_members.count(m) > 1})}")
    research_ids = ledger_ids(ledger, "research_stop_code")
    if research_ids != set(load_json(RESEARCH)["stop_codes"]):
        problems.append("研究の停止コードの集合が research_links.json と違う")
    current = scan.prefixed_codes(ROOT)
    engine_codes = {c for c, v in current.items() if v["engine"].get("literal") or v["engine"].get("comment")} - {"UNSUPPORTED_COMMANDS"}
    covered = research_ids | ledger_ids(ledger, "runtime_stop_code")
    if engine_codes - covered:
        problems.append(f"エンジンのコードが台帳にない: {sorted(engine_codes - covered)}")
    if covered - engine_codes:
        problems.append(f"台帳のコードがエンジンにない: {sorted(covered - engine_codes)}")
    if research_ids & ledger_ids(ledger, "runtime_stop_code"):
        problems.append("研究コードと表外コードが重なる")
    for e in ledger["entries"]:
        if e["status"] == "fixed" and e["entry_kind"] in ("research_stop_code", "runtime_stop_code"):
            problems.append(f"{e['id']}: 停止コードを修正済みにしない（修正済みは問題の項目）")
    problems += convention_problems(ledger)
    problems += agreement_problems(ledger)
    problems += decision_document_problems(ledger)
    problems += generated_block_problems(ledger)
    for family, spec in ledger["families"].items():
        for key in ("title", "play_groups", "strict", "requirements", "risks", "regression", "mode_policy_status"):
            if key not in spec:
                problems.append(f"族 {family}: {key} がない")
        if not spec.get("play_candidates") and not spec.get("no_play_reason"):
            problems.append(f"族 {family}: プレイ用の候補も、候補がない理由もない")
        for candidate in spec.get("play_candidates", []):
            for key in ("rule", "target", "timing", "result_difference", "safety"):
                if not candidate.get(key):
                    problems.append(f"族 {family} の {candidate.get('id')}: {key} がない")
            for sc in candidate.get("safety", {}):
                if sc not in SAFETY_CONDITIONS:
                    problems.append(f"族 {family} の {candidate.get('id')}: 安全条件 {sc} がない")
    if fresh is not None and stable(_without_tool(ledger)) != stable(_without_tool(fresh)):
        problems.append("現行コードから作り直した台帳と、書き出した台帳が違う（--write で作り直して差を確かめる）")
    return problems


# ---------------------------------------------------------------------------------------------------------------------------------------------------
# 規約集合の設計の作業（2026-11-03）で加えた確かめ。合意・規約・判断事項・設計文書の生成した表が、台帳と登録の記録と同じこと
# ---------------------------------------------------------------------------------------------------------------------------------------------------
# 判断事項を定義する行: 見出し「### DEC-…」か、表の最初の列「| DEC-… |」（族ごとの判断事項の表）。移した判断事項の履歴は「#### 」の見出しにして、定義に数えない
DECISION_HEADING_RE = re.compile(r"^(?:### |\| )(DEC-[A-Z0-9-]+)(?=\s)", re.MULTILINE)


def _engine_registries() -> dict:
    """登録の記録（対象の鍵 → 規則の ID）。カードの登録を名前だけでなく対象で照らすために読む（エンジンの動作は変えない）。"""
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))
    from kyuura_engine import decisions, effects, sudden_death
    registries = {name: {key: record.rule for key, record in getattr(effects, name.split(".", 1)[1]).items()} for name in set(REGISTRY_OF_KIND.values())}
    registries["sudden_death.USER_SUDDEN_DEATH_OWNERSHIP_RESET"] = {"": sudden_death.USER_SUDDEN_DEATH_OWNERSHIP_RESET.id}
    registries["decisions.USER_PRIZE_ORDER_RULES"] = {rule.id: rule.id for rule in decisions.USER_PRIZE_ORDER_RULES}  # v0.140
    return registries


def convention_problems(ledger: dict) -> list[str]:
    problems = []
    agreement_ids = {a["id"] for a in ledger.get("mode_agreements", {}).get("agreements", [])}
    registries = _engine_registries()
    seen: dict[str, set[str]] = {name: set() for name in registries}
    for c in ledger["conventions"]:
        cid, status, category = c["id"], c.get("mode_policy_status"), c.get("baseline_category")
        if category not in BASELINE_CATEGORIES:
            problems.append(f"{cid}: 基礎集合の区分 {category} がない")
        if status == AGREED_CONVENTION_STATUS:
            if category != "user_specified":
                problems.append(f"{cid}: {AGREED_CONVENTION_STATUS} は利用者指定（user_specified）だけ（区分 {category} は decision_required）")
            if "AGR-MODE-BASELINE-USER" not in c.get("agreement_refs", []):
                problems.append(f"{cid}: {AGREED_CONVENTION_STATUS} なのに合意 AGR-MODE-BASELINE-USER を参照しない")
            approval = c.get("approval") or {}
            if not (approval.get("document") and approval.get("on") and approval.get("instruction")):
                problems.append(f"{cid}: 利用者の指定の文書・日・指定の文がない")
            elif approval["instruction"] not in (ROOT / approval["document"].split(" ", 1)[0]).read_text(encoding="utf-8"):
                problems.append(f"{cid}: 指定の文が根拠の文書 {approval['document']} にない")
        elif status != "decision_required":
            problems.append(f"{cid}: 既存の規約の状態 {status} は使わない（{AGREED_CONVENTION_STATUS} は合意した利用者指定だけ、ほかは decision_required）")
        elif not c.get("decision_refs"):
            problems.append(f"{cid}: decision_required なのに判断事項がない")
        for ref in c.get("decision_refs", []):
            if ref not in ledger["decisions"]:
                problems.append(f"{cid}: 判断事項 {ref} がない")
        for ref in c.get("agreement_refs", []):
            if ref not in agreement_ids:
                problems.append(f"{cid}: 合意 {ref} がない")
        for key in ("target", "effect", "affects", "not_covered"):
            if not c.get(key):
                problems.append(f"{cid}: {key}（対象・効果・影響する判定・含まない場面）がない")
        if c.get("kind") == "user_specified_names" and c.get("display_only") is not False:
            problems.append(f"{cid}: 名前の扱いは判定（同じ名前・進化・クイズ）に影響する（表示だけにしない）")
        registry = c.get("registry", "")
        name = registry.split("[", 1)[0]
        if name in registries:
            key = registry.split("['", 1)[1].removesuffix("']") if "['" in registry else ""
            seen[name].add(key)
            rule = registries[name].get(key)
            if rule is None:
                problems.append(f"{cid}: 登録の記録 {registry} がない")
            elif c.get("user_ids") != [rule]:
                problems.append(f"{cid}: USER-ID {c.get('user_ids')} が登録の規則 {rule} と違う")
        elif category == "user_specified":
            problems.append(f"{cid}: 利用者指定なのに登録の記録（registry）を照らせない")
    for name, keys in registries.items():
        missing = sorted(set(keys) - seen[name])
        if missing:
            problems.append(f"登録の記録 {name} の対象 {missing} が台帳の conventions にない")
    return problems


def agreement_problems(ledger: dict) -> list[str]:
    problems = []
    block = ledger.get("mode_agreements") or {}
    source = block.get("source") or {}
    if source.get("by") != "user" or "公式" not in source.get("not_recorded_as", ""):
        problems.append("合意の出典は利用者の指示で、公式の裁定・kyuura の解決として記録しない")
    ids = [a.get("id") for a in block.get("agreements", [])]
    if not ids or len(ids) != len(set(ids)):
        problems.append(f"合意の ID が空か重複: {ids}")
    for a in block.get("agreements", []):
        if not (a.get("statement") and a.get("reading")):
            problems.append(f"{a.get('id')}: 合意の文・読み方がない")
    statuses = ledger.get("decision_status", {})
    if set(statuses) != set(ledger["decisions"]):
        problems.append("判断事項と判断事項の状態の集合が違う")
    for d, status in statuses.items():
        if status["status"] not in ("decision_required", "agreed", "partly_agreed"):
            problems.append(f"{d}: 判断事項の状態 {status['status']} は使わない")
        if status["status"] != "decision_required" and not (status.get("agreements") and set(status["agreements"]) <= set(ids)):
            problems.append(f"{d}: 合意の参照 {status.get('agreements')} がない")
    return problems


def decision_document_problems(ledger: dict) -> list[str]:
    problems = []
    headings = {doc: DECISION_HEADING_RE.findall((ROOT / doc).read_text(encoding="utf-8")) for doc in (STOP_DECISIONS_DOC, RULESET_DECISIONS_DOC) if (ROOT / doc).exists()}
    for d, status in ledger.get("decision_status", {}).items():
        doc = status["document"]
        if headings.get(doc, []).count(d) != 1:
            problems.append(f"{d}: 置き場所 {doc} に見出しがちょうど 1 つない（{headings.get(doc, []).count(d)}）")
        for other, found in headings.items():
            if other != doc and d in found:
                problems.append(f"{d}: 置き場所でない {other} にも見出しがある（同じ判断事項を 2 か所に書かない）")
    for doc, found in headings.items():
        for d in found:
            if d not in ledger["decisions"]:
                problems.append(f"{doc}: 見出しの判断事項 {d} が台帳にない")
    return problems


def _markers(name: str) -> tuple[str, str]:
    return (f"<!-- generated:{name} begin（scripts/build_stop_policy_classification.py --write が台帳から書く。手で直さない） -->", f"<!-- generated:{name} end -->")


def _cell(value) -> str:
    text = "・".join(value) if isinstance(value, list) else str(value)
    return text.replace("|", "／").replace("\n", " ")


def render_agreements(ledger: dict) -> str:
    rows = ["| ID | 合意の文（利用者の指示のまま） | 台帳での読み方 |", "|---|---|---|"]
    rows += [f"| `{a['id']}` | {_cell(a['statement'])} | {_cell(a['reading'])} |" for a in ledger["mode_agreements"]["agreements"]]
    return "\n".join(rows)


def render_baseline(ledger: dict) -> str:
    labels = {"user_specified": "利用者指定", "engine_simplification": "エンジンの簡略化", "implementation_assumption": "実装上の仮定", "card_data_correction": "データの訂正"}
    rows = ["| 規約（台帳の ID） | 区分 | USER-ID | 対象 | 効果 | 影響する判定 | 基礎集合 |", "|---|---|---|---|---|---|---|"]
    for c in ledger["conventions"]:
        inclusion = "含める（AGR-MODE-BASELINE-USER）" if c["mode_policy_status"] == AGREED_CONVENTION_STATUS else f"未決（{'・'.join(c['decision_refs'])}）"
        rows.append(f"| `{c['id']}` | {labels[c['baseline_category']]} | {_cell(c['user_ids']) or '—'} | {_cell(c['target'])} | {_cell(c['effect'])} | {_cell(c['affects'])} | {inclusion} |")
    return "\n".join(rows)


GENERATED_BLOCKS = {"mode-agreements": render_agreements, "baseline-conventions": render_baseline}


def with_generated_blocks(text: str, ledger: dict) -> str:
    for name, render in GENERATED_BLOCKS.items():
        begin, end = _markers(name)
        if text.count(begin) != 1 or text.count(end) != 1 or text.index(begin) > text.index(end):
            raise ValueError(f"{RULESET_DESIGN_DOC.name}: 生成する表 {name} の印がちょうど 1 組ない")
        head, rest = text.split(begin, 1)
        _, tail = rest.split(end, 1)
        text = f"{head}{begin}\n{render(ledger)}\n{end}{tail}"
    return text


def generated_block_problems(ledger: dict) -> list[str]:
    if not RULESET_DESIGN_DOC.exists():
        return [f"{RULESET_DESIGN_DOC.name} がない"]
    text = RULESET_DESIGN_DOC.read_text(encoding="utf-8")
    try:
        expected = with_generated_blocks(text, ledger)
    except ValueError as error:
        return [str(error)]
    return [] if expected == text else [f"{RULESET_DESIGN_DOC.name} の生成した表が台帳と違う（--write で書き直す）"]


def stable(ledger: dict) -> str:
    return json.dumps({k: v for k, v in ledger.items() if k != "evidence"}, ensure_ascii=False, sort_keys=True)


def ledger_ids(ledger: dict, kind: str) -> set[str]:
    return {e["id"] for e in ledger["entries"] if e["entry_kind"] == kind}


def _without_tool(ledger: dict) -> dict:
    """証拠のファイル（リポジトリの外）がない環境でも比べられるように、道具の記録に由来する項目を除いた写し。"""
    copy = json.loads(json.dumps(ledger, ensure_ascii=False))
    for e in copy["entries"]:
        e.pop("stress", None)
        if e.get("reachability", {}).get("status") == "legal_sequence":
            e["reachability"] = {"status": "legal_sequence"}
    copy["counts"].pop("by_reachability", None)
    return copy


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--write", action="store_true")
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    fresh = build()
    if args.write:
        OUTPUT.write_text(json.dumps(fresh, ensure_ascii=False, indent=1) + "\n", encoding="utf-8", newline="\n")
        print(f"wrote {OUTPUT.relative_to(ROOT).as_posix()}: {len(fresh['entries'])} entries")
        text = RULESET_DESIGN_DOC.read_text(encoding="utf-8")
        RULESET_DESIGN_DOC.write_text(with_generated_blocks(text, fresh), encoding="utf-8", newline="\n")
        print(f"wrote generated blocks of {RULESET_DESIGN_DOC.relative_to(ROOT).as_posix()}")
    ledger = load_json(OUTPUT)
    if not TOOL_EVIDENCE_ROOT.exists():
        fresh = None  # 道具の証拠がない環境では、作り直した台帳との比べを省く（不変条件だけ確かめる）
    problems = check(ledger, fresh)
    for problem in problems:
        print("PROBLEM", problem)
    print(json.dumps(ledger["counts"], ensure_ascii=False, indent=1))
    return 1 if problems else 0


if __name__ == "__main__":
    raise SystemExit(main())

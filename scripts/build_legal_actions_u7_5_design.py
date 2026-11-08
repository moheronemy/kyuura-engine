"""U7-5（残る操作の候補・入力・実行）の仕様と実装計画 docs/legal-actions-u7-5-design.json を作る・確かめる（調査と仕様だけ。候補の実装はしない）。

    python scripts/build_legal_actions_u7_5_design.py --write   # JSON と、設計・実装計画の文書の生成区画（表）を、このスクリプトの SPEC から書き直す
    python scripts/build_legal_actions_u7_5_design.py --check   # JSON・生成区画が作り直したものと同じか、コードとの対応（コマンドの項目と既定値・参照する関数・
                                                                # 登録の数・カードごとの確かめの静的な走査の結果）が合うか、計画の規則に反する値がないか

- 仕様の唯一の元は、このスクリプトの ``SPEC``。JSON と文書の表はここから作る（二重に手で書かない）。生成区画の外（本文）は手で書く
- 表の書き出しと生成区画の置きかえは、状態スナップショットの仕様案の生成器（scripts/build_state_snapshot_design.py）の関数をそのまま使う（U7 の仕様案の生成器と同じ）
- コードの参照は「ファイル::名前」（最上位の関数・クラス・定数、または「クラス.メソッド」）。行番号に頼らない（AST で在ることを確かめる）
- 停止のコードは、定数の参照（``code_ref``）で書き、JSON には作るときに定数の値を入れる（このファイルに停止のコードの文字列を書かない）
"""

from __future__ import annotations

import argparse
import ast
import dataclasses
import importlib.util
import json
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
OUTPUT = ROOT / "docs" / "legal-actions-u7-5-design.json"
DESIGN = ROOT / "docs" / "legal-actions-u7-5-design.md"
PLAN = ROOT / "docs" / "legal-actions-u7-5-implementation-plan.md"

_helpers_spec = importlib.util.spec_from_file_location("build_state_snapshot_design", ROOT / "scripts" / "build_state_snapshot_design.py")
_H = importlib.util.module_from_spec(_helpers_spec)
_helpers_spec.loader.exec_module(_H)
_table, render_into, dump = _H._table, _H.render_into, _H.dump

_scan_spec = importlib.util.spec_from_file_location("implementation_assumptions_scan", ROOT / "scripts" / "implementation_assumptions_scan.py")
_SCAN = importlib.util.module_from_spec(_scan_spec)
_scan_spec.loader.exec_module(_SCAN)

BASE_COMMIT = "1ad7f6bf9b3f72212ec6799080ffecabd3cd3824"
EFFECTS = "kyuura_engine/effects.py"
ENGINE = "kyuura_engine/engine.py"

# ---------------------------------------------------------------- 情報源の分類（A〜E）

SOURCES = [
    {"id": "A", "meaning": "公開情報と本人の知識だけで判断できる（場・トラッシュ・公開の枚数・番・特殊状態・本人の手札・本人のうらのカードの本当のカード）",
     "candidate_use": "候補・inputs・check に使ってよい（本人の候補だけ。相手・観戦者には出さない）"},
    {"id": "A-own", "meaning": "A のうち、本人の見えないカードの集合だけで決まる持ち主の知識の関数（unseen_card_pool・deck_target_lower_bound・possible_deck_cards・"
     "searchable_deck_cards。v0.137〜v0.151 で山札とサイドの配分によらないことを確かめた）",
     "candidate_use": "本人の候補だけに使ってよい。単位ごとに秘密の配分を変えた双子で確かめる（関数の既存の根拠を、候補の経路の根拠に数えない）"},
    {"id": "B", "meaning": "宣言の入力がそろうと判断できる（特殊能力の energy・source・target、スタジアムの energy の組）",
     "candidate_use": "inputs で組ごとに確かめ、check でそろった入力をもう一度確かめる（全組み合わせを先に列挙しない）"},
    {"id": "C", "meaning": "受理のあとのコイン・検索・決定で判断する（錯乱ジムのコイン・特殊能力のコイン・トレーナーの効果の決定・［ちえくらべ］の答えなど）",
     "candidate_use": "候補に持ち込まない。受理のあと answer_decision の候補で答える"},
    {"id": "D", "meaning": "秘密の状態を読む・実際の状態の上で処理を試すので、候補 API に使えない（処理のあとの確かめ・うらのカードの割り当ての試行・答えの続きの試行）",
     "candidate_use": "使わない。この確かめで止まりうる候補は may_stop_later（または unverified）"},
    {"id": "E", "meaning": "情報源・安全性が未確認（状態の複製の上で効果を試す事前確認で、読む値をたどっていないもの・他のモジュールへの呼び出しをたどっていないもの）",
     "candidate_use": "公開してよいと仮定しない（CORR-1）。処理可能性の unverified と、入力を示して安全か（input_disclosure）は別の軸で、unverified にするだけでは"
                      "選べるもの・件数・理由を返してよいことにならない。たどって安全と確かめるまで、その確かめに当たる候補は入力を返さない（unconfirmed・"
                      "INPUT_BOUNDARY_UNCONFIRMED）。型・生成箇所の登録だけで安全と認めない。実装計画で対応済みに数えない"},
]
SOURCE_IDS = {s["id"] for s in SOURCES}

# ---------------------------------------------------------------- コマンドごとの調査

# 項目: (名前, 意味, 分類, 誰がいつ知るか)。分類は declaration_required・declaration_optional・not_input（主体・内部の値）
# 既定値はコードから取る（_command_fields）。ここには書かない
COMMANDS = [
    {"command": "PlayTrainer", "kind": "play_trainer", "handler": f"{ENGINE}::_play_trainer", "actor": "番のプレイヤー（player）",
     "phase": "Phase.MAIN（checks.require_turn）。決定を待つあいだは段階が DECISION なので使えない",
     "fields": [["player", "使うプレイヤー", "not_input", "主体（取っ手が決める）"],
                ["card", "手札のトレーナーカードの uid", "declaration_required", "本人だけが手札の中身を知る（相手は手札の枚数だけ）"]],
     "after_acceptance": ["錯乱ジムのコイン（使うための条件の前。「うら」なら相手がかわりに使うかの決定 ACCEPT_REQUEST）",
                          "相手の［ちえくらべ］を使うかの決定（REACTION_POWER。決めるのは相手）",
                          "リムーブ禁止ジムの追加の条件（手札 2 枚。決定 DISCARD_FROM_HAND）",
                          "トレーナーの効果の決定（対象・枚数・山札の検索・見たカード。push_trainer_decision）",
                          "サイキックコントロール: 相手のトラッシュのトレーナーを使う決定（USE_DISCARD_TRAINER）と、その内側の使用（_start_nested_trainer。事前確認をもう一度しない）"],
     "order": "手札から出して見せ名前を伝える（ログ play_trainer。公開）→ スタジアムなら場に出す → 錯乱ジムのコイン → 追加の条件 → 使うための条件と説明 → トラッシュ（使用中は trainer_in_use）",
     "limits": "1 番に何枚でも（p.310）。使う条件は effect.check_playable。禁止は trainer_use_blockers（［アレルギーかふん］・期限のある禁止）。番を終えるトレーナー（may_end_turn）がある",
     "stops": [["MG1", f"{EFFECTS}::MIND_GAMES_CHAOS_GYM_CODE", "場に錯乱ジムと相手の［ちえくらべ］（スタジアム以外）。手札から出す前に止める"],
               ["登録なし", f"{ENGINE}::_play_trainer", "登録表にないトレーナー（trainer_problem の理由つき。処理可能性 not_implemented）"],
               ["カードごと", f"{EFFECTS}::TrainerEffect.check_playable", "77 の実装の未裁定・未対応（FU3・PT1・AL2・MH1 など。診断のコード表で分類）"]],
     "conventions": "手札から使う前の確かめに、続行規約の照会は見つからない（effects.py の中の呼び出しの閉包。ほかのモジュールは追っていない）。受理のあとのきぜつ・ポケモンチェックで集合の違いが出うる"},
    {"command": "UsePokemonPower", "kind": "use_power", "handler": f"{ENGINE}::_use_pokemon_power", "actor": "番のプレイヤー",
     "phase": "Phase.MAIN。自分の場（バトル場・ベンチ）のポケモン。相手の番・ポケモンチェック・反応の特殊能力は決定（このコマンドでない）",
     "fields": [["player", "使うプレイヤー", "not_input", "主体"],
                ["pokemon", "特殊能力を使う自分の場のポケモンの番号", "declaration_required", "公開（場の番号）"],
                ["power", "特殊能力の位置（印刷の順）", "declaration_required", "公開（おもてのカード）。本人のうらのカードは本人だけ（ただし宣言の前におもてにする）"],
                ["energy", "説明が選ばせるエネルギーカードの uid（ついているカード、または本人の手札のカード）", "declaration_optional", "ついているカードは公開。手札のカードは本人だけ"],
                ["source", "説明が選ばせる移動元の場のポケモンの番号", "declaration_optional", "公開"],
                ["target", "説明が選ばせる先の場のポケモンの番号（自分・相手）", "declaration_optional", "公開。相手のうらのカードを指すと、その本当のカードは相手だけが知る"],
                ["card", "特殊能力を印刷したカードの uid（「ばける」でのせたカード・［へんしん］の写し）", "declaration_optional", "公開（のせたカード・相手のバトル場のカード）"]],
     "after_acceptance": ["特殊能力のコイン（resolve の中）", "効果の決定（push_power_decision。再開先 power）", "あまごいでつけた事実への反応（reactions.attach_steps）",
                          "使用後の処理（resolution.after_power。きぜつ・サイド・バトル場に出す決定）"],
     "order": "うらのカードをおもてにする・指定したうらのカードをおもてにする（_reveal_for_action）→ 番 → 特殊能力の確かめ → 宣言（ログ pokemon_power）→ 回数の記録 → 処理",
     "limits": "「自分の番ごとに1回」（once_per_turn。power_uses_this_turn。宣言のときに記録）。消す効果（かがくへんかガス・まきちらせ!ベトベトガス・スタンウェーブ・［いあつ］・期限のある抑止・ショックアイ）",
     "stops": [["DV3", f"{EFFECTS}::POWER_REUSE_AFTER_DEVOLUTION_CODE", "退化して戻ったカードでこの番に使っていた"],
               ["TF1・SV3", f"{EFFECTS}::copied_declared_power_problem", "写した特殊能力の使用"],
               ["登録なし", f"{ENGINE}::_use_pokemon_power", "登録表にない特殊能力（not_implemented）"],
               ["秘策の対象", "kyuura_engine/zones.py::SECRET_PLAN_LOST_TARGET_CODE", "指定したうらのカードが「たねポケモン」でない"],
               ["割り当ての上限", f"{ENGINE}::SECRET_PLAN_IDENTITIES_CODE", "相手のうらのカードを 2 枚以上指定（受け付けるかを本当のカードによらないものにできない）"]],
     "conventions": "事前確認から続行規約の照会は見つからない（effects.py の中の閉包）。［ポイズンミスト］の量（PO の集合）は受理のあとのポケモンチェック"},
    {"command": "UseStadium", "kind": "use_stadium", "handler": f"{ENGINE}::_use_stadium", "actor": "番のプレイヤー（スタジアムの持ち主でなくてよい）",
     "phase": "Phase.MAIN。番でないプレイヤーは使えない（require_turn）",
     "fields": [["player", "使うプレイヤー", "not_input", "主体"],
                ["energy", "説明が選ばせるエネルギーカードの uid（タマムシシティジム・ヤマブキシティジム）", "declaration_optional", "公開（場についているカード）"]],
     "after_acceptance": ["スタジアムのコイン（activate の中。「うら」でも使ったことになる）", "決定（再開先 stadium。セキチクシティジムのポケモン・ラジオとうの見る枚数・キョウの忍者ジムの山札のカード・エネルギーの回収）",
                          "空いたバトル場の勝ち負け・交代（resolution.after_stadium）"],
     "order": "番 → 場のスタジアム → check_activation → ログ stadium_used → 回数の記録（records_uses）→ activate",
     "limits": "「自分の番ごとに1回」はプレイヤーとカードの組（stadium_uses_this_turn）。SX2・LK1・RS1・STB1（トレーナーの使用の禁止）",
     "stops": [["カードごと", f"{EFFECTS}::StadiumEffect.check_activation", "9 の実装（STB1・LK1・FG1・NJ1・GG1・TG1・RB3 など）"]],
     "conventions": "事前確認から続行規約の照会は見つからない"},
    {"command": "RemoveDisguise", "kind": "remove_disguise", "handler": f"{ENGINE}::_remove_disguise", "actor": "番のプレイヤー",
     "phase": "Phase.MAIN。特殊能力の宣言・トレーナーの使用ではない（回数・禁止は関係しない）",
     "fields": [["player", "主体", "not_input", "主体"], ["pokemon", "のせたカードをトラッシュする自分の場のポケモンの番号", "declaration_required", "公開（disguise は公開のログで出した）"]],
     "after_acceptance": ["なし（決定を出さない）"],
     "order": "番 → 自分の場のポケモン → disguise がある → のせたカードをトラッシュ（ログ disguise_removed）→ 処理のあとの確かめ（MH1・TK1）",
     "limits": "回数の制限なし（説明が許す操作）",
     "stops": [["MH1・TK1", f"{ENGINE}::_apply_once", "元の姿の最大HPがのっているダメージ以下（処理のあとの確かめ）"]],
     "conventions": "違いなし（受理のあとの決定がない）"},
    {"command": "DiscardFromPlay", "kind": "discard_from_play", "handler": f"{ENGINE}::_discard_from_play", "actor": "番のプレイヤー",
     "phase": "Phase.MAIN。トレーナーの使用・特殊能力ではない",
     "fields": [["player", "主体", "not_input", "主体"], ["pokemon", "すてる自分の場のなにかの化石・ピッピ人形の番号", "declaration_required", "公開（場のおもてのカード）"]],
     "after_acceptance": ["バトル場が空いたら勝ち負け・バトル場に出す決定（resolution.after_power）"],
     "order": "番 → 自分の場のポケモン → play_as_pokemon_effect・discardable_from_play → leave_lock → トラッシュ（ログ discard_from_play）→ 持続する効果を消す → after_power",
     "limits": "回数の制限なし。バトル場をはなれられない効果（LEAVE_ACTIVE_PREVENTED）",
     "stops": [["FD1", "kyuura_engine/errors.py::SECRET_PLAN_HIDDEN_CODE", "本人のうらのカードを指すと NOT_DISCARDABLE ではなく FD1（F-2）"]],
     "conventions": "受理のあとの勝ち負け・交代で、きぜつの時点の規約（S2a）は通らない（きぜつではない）"},
    {"command": "RevealFaceDown", "kind": "reveal_face_down", "handler": f"{ENGINE}::_reveal_face_down", "actor": "番のプレイヤー（うらのカードの持ち主）",
     "phase": "Phase.MAIN。決定を待つあいだ・処理の途中には割りこまない",
     "fields": [["player", "主体", "not_input", "主体"], ["pokemon", "おもてにする自分の場のうらのカードの番号", "declaration_required", "うらであることは公開（secret_plan_placed）。本当のカードは本人だけ"]],
     "after_acceptance": ["「たねポケモン」でなければ、ついているカードといっしょにトラッシュ（ログ secret_plan_discarded）", "空いたバトル場の勝ち負け・交代（resolution.after_power）"],
     "order": "番 → 自分の場のポケモン → うらである → おもてにする（ログ secret_plan_revealed。本当のカードの id を全員に公開）→ 残るか（本当のカード）→ after_power",
     "limits": "回数の制限なし",
     "stops": [],
     "conventions": "違いなし（本当のカードの種類で分かれるだけ）"},
    {"command": "CheckFaceUpDeckCard", "kind": "check_face_up_deck", "handler": f"{ENGINE}::_check_face_up_deck_card", "actor": "どちらのプレイヤーでも（番・段階を確かめない）",
     "phase": "番・段階を確かめない（対戦の終わり・延長戦の前・停止はエンジンの入口で拒否）。どの場合も受け付けない",
     "fields": [["player", "確かめたいプレイヤー", "not_input", "主体"], ["owner", "山札の持ち主", "declaration_required", "公開"],
                ["position", "山札の上からの位置（0 がいちばん上）", "declaration_required", "おもての枚数（face_up_count）は公開。いちばん上は全員、下は持ち主だけが知る"]],
     "after_acceptance": ["なし（受け付けない）"],
     "order": "プレイヤー → おもての位置（NOT_FACE_UP）→ いちばん上（ALREADY_VISIBLE）→ 持ち主（ALREADY_KNOWN）→ FU2 で止める",
     "limits": "受け付けない",
     "stops": [["FU2", "kyuura_engine/faceup.py::FACE_UP_DECK_CHECK_CODE", "相手の山札の 2 枚目より下のおもてのカードを確かめてよいかが決まらない"]],
     "conventions": "違いなし"},
]

# 7 種類の外に残る経路（同じ coverage の中で、7 種類では説明できないもの）
RESIDUAL_PATHS = [
    {"id": "R-1", "command": "AttachEnergy", "path": "energy2（カツラの効果の 2 枚目の「炎」エネルギー）", "unit_now": "U7-3 が使わない（docs/legal-actions-u7-3.md）",
     "proposal": "U7-5g（残りの経路）で、U7-3 の attach_energy に任意の 3 段目を加えるか決める（D-U75-ENERGY2）"},
    {"id": "R-2", "command": "UseAttack", "path": "自分のうらのバトル場のポケモンの、宣言といっしょに選ぶもの", "unit_now": "U7-4 は示さない（unverified）",
     "proposal": "U7-5b（うらのカード）の本人の知識の扱いが決まってから見直す"},
]

# ---------------------------------------------------------------- 確かめの分類（候補・inputs・check での使い方）

CHECKS = [
    # PlayTrainer
    {"id": "PT-1", "command": "PlayTrainer", "ref": "kyuura_engine/checks.py::require_turn", "source": "A", "use": "candidates", "note": "番・段階"},
    {"id": "PT-2", "command": "PlayTrainer", "ref": f"{ENGINE}::_require_in_hand", "source": "A", "use": "candidates", "note": "本人の手札"},
    {"id": "PT-3", "command": "PlayTrainer", "ref": f"{EFFECTS}::trainer_use_blockers", "source": "A", "use": "candidates", "note": "場の力・期限のある禁止（公開）"},
    {"id": "PT-4", "command": "PlayTrainer", "ref": f"{EFFECTS}::EffectRegistry.trainer_effect", "source": "A", "use": "candidates", "note": "登録の有無（本人の手札のカードの定義と登録表）"},
    {"id": "PT-5", "command": "PlayTrainer", "ref": f"{EFFECTS}::TrainerEffect.check_playable", "source": "A", "use": "candidates",
     "note": "77 の実装のうち、下の 2 群を除くもの（場・トラッシュ・枚数・本人の手札）"},
    {"id": "PT-5o", "command": "PlayTrainer", "ref": f"{EFFECTS}::deck_target_lower_bound", "source": "A-own", "use": "candidates", "note": "持ち主の知識の関数を呼ぶ 6 の実装（scan.check_playable.owner_knowledge）"},
    {"id": "PT-5e", "command": "PlayTrainer", "ref": f"{EFFECTS}::quiz_draw_outcome_stop", "source": "E", "use": "none",  # CORR-1: たどるまで候補の作成で呼ばない
     "note": "状態の複製の上で効果を試す 11 の実装（scan.check_playable.trials）のうち、実際の山札から引いて試す 5 つ（クイズ 4 種・とりかえっこプリーズ。"
             "legal_actions.PLAYABLE_NOT_EVALUATED）。たどっていない。v0.169: 候補・inputs・check で呼ばず unverified（入力は本人の手札だけで決まる）"},
    {"id": "PT-5t", "command": "PlayTrainer", "ref": f"{EFFECTS}::switch_max_hp_drop_check", "source": "A", "use": "candidates",
     "note": "v0.169: 11 の試行のうち、試すのが場の処理だけ（入れ替え・特殊状態・回復）の 6 つ（legal_actions.PLAYABLE_BOARD_TRIALS）。effects.py の閉包と、呼ぶ別のモジュールの関数の"
             "1 段目までをたどり、山札・サイド・手札・うらのカードの中身を読まないことを確かめた（うらのカードの定義は本当のカードによらず FD1。docs/legal-actions-u7-5c.md 4 章）"},
    {"id": "PT-6", "command": "PlayTrainer", "ref": f"{EFFECTS}::stadium_trainer_cost", "source": "A", "use": "candidates", "note": "リムーブ禁止ジム（本人の手札の枚数）"},
    {"id": "PT-7", "command": "PlayTrainer", "ref": f"{EFFECTS}::trainer_reaction_sources", "source": "A", "use": "candidates", "note": "相手の場の［ちえくらべ］と錯乱ジム（MG1）"},
    {"id": "PT-8", "command": "PlayTrainer", "ref": f"{ENGINE}::_trainer_reaction_decline_check", "source": "D", "use": "none", "note": "使わない答えの続きを実際の状態の複製で処理する"},
    {"id": "PT-9", "command": "PlayTrainer", "ref": f"{ENGINE}::_trainer_dead_end", "source": "D", "use": "none", "note": "効果の途中の決定の答えを状態の複製の上で試す"},
    {"id": "PT-10", "command": "PlayTrainer", "ref": f"{ENGINE}::_chaos_tails", "source": "C", "use": "none", "note": "錯乱ジムの「うら」。相手がかわりに使えるか（F-1）"},
    # UsePokemonPower
    {"id": "UP-0", "command": "UsePokemonPower", "ref": f"{ENGINE}::_reveal_for_action", "source": "D", "use": "none",
     "note": "使うポケモン・指定したうらのカードを、確かめの前におもてにする。相手のうらのカードを指せば _identity_independent の試行になる"},
    {"id": "UP-1", "command": "UsePokemonPower", "ref": "kyuura_engine/checks.py::require_turn", "source": "A", "use": "candidates", "note": "番・段階"},
    {"id": "UP-2", "command": "UsePokemonPower", "ref": f"{EFFECTS}::powers_of", "source": "A", "use": "candidates", "note": "今の姿・のせたカード・写しの特殊能力（本人のうらのカードは unverified）"},
    {"id": "UP-3", "command": "UsePokemonPower", "ref": "kyuura_engine/continuous.py::suppressors_of", "source": "A", "use": "candidates",
     "note": "かがくへんかガスほか、消す効果の 6 つの確かめ（goop_gas_effects・powers_stopped・scared_by・power_suppressed・powers_use_prevented も同じ）"},
    {"id": "UP-4", "command": "UsePokemonPower", "ref": f"{EFFECTS}::copied_declared_power_problem", "source": "A", "use": "candidates", "note": "写した特殊能力（TF1・SV3）"},
    {"id": "UP-5", "command": "UsePokemonPower", "ref": f"{EFFECTS}::PowerEffect.check_usable", "source": "B", "use": "inputs",
     "note": "宣言の入力（energy・source・target）がそろうと決まる。入力のない 45 の実装は A として候補に使える"},
    {"id": "UP-5o", "command": "UsePokemonPower", "ref": f"{EFFECTS}::possible_deck_cards", "source": "A-own", "use": "candidates", "note": "持ち主の知識の関数を呼ぶ 4 の実装（scan.check_usable.owner_knowledge）"},
    {"id": "UP-5t", "command": "UsePokemonPower", "ref": f"{EFFECTS}::state_stop_after", "source": "A", "use": "candidates",
     "note": "状態の複製の上で効果を試す 7 の実装（scan.check_usable.trials）。v0.171: パッケージ全体の呼び出しを名前で解決した閉包（効果のフックは同じ名前の実装をすべて根にした）で、山札・サイド・置いておくカード・乱数・うらのカードの集合を読まない（読むのは場・カードの定義・本人の手札。複製の上の書き込みだけ）とたどった。名前で解決できない呼び出し（状態のメソッド・登録表の引き・正規表現）は残る。指定するうらのカードを含む組は確かめない（docs/legal-actions-u7-5e.md 4 章）"},
    {"id": "UP-6", "command": "UsePokemonPower", "ref": f"{EFFECTS}::power_reuse_after_devolution", "source": "A", "use": "candidates", "note": "DV3（停止として表示）"},
    # UseStadium
    {"id": "US-1", "command": "UseStadium", "ref": "kyuura_engine/stadiums.py::stadium_in_play", "source": "A", "use": "candidates", "note": "場のスタジアム"},
    {"id": "US-2", "command": "UseStadium", "ref": f"{EFFECTS}::StadiumEffect.check_activation", "source": "B", "use": "inputs",
     "note": "energy を選ばせる 2 の実装は入力がそろうと決まる。ほかは A。キョウの忍者ジムは A-own"},
    {"id": "US-3", "command": "UseStadium", "ref": f"{EFFECTS}::CoinReturnOwnerPokemonStadium.check_activation", "source": "A", "use": "candidates",
     "note": "本人のうらのカードがあると、対象を調べる途中で FD1（F-3。本当のカードによらない）"},
    {"id": "US-4", "command": "UseStadium", "ref": f"{EFFECTS}::CoinBenchOwnerBasicFromDeckStadium.check_activation", "source": "A-own", "use": "candidates",
     "note": "v0.170: キョウの忍者ジムは持ち主の知識の下限（deck_target_lower_bound・bench_entry_unconfirmed）。山札を直接たどるのは、山札と見えないほかの場所を合わせた集合の"
             "エンジンの不具合の確かめ（placed_entry_power_guard）だけで、配分によらない。使える 8 の実装の閉包に状態の複製はない（docs/legal-actions-u7-5d.md 3 章）"},
    # RemoveDisguise
    {"id": "RD-1", "command": "RemoveDisguise", "ref": f"{ENGINE}::_remove_disguise", "source": "A", "use": "candidates", "note": "番・自分の場・disguise（どれも公開）"},
    {"id": "RD-2", "command": "RemoveDisguise", "ref": f"{EFFECTS}::max_hp_drops", "source": "D", "use": "none", "note": "処理のあとの確かめ（MH1・TK1）。値は公開だが、処理を試さないと決めない"},
    # DiscardFromPlay
    {"id": "DF-1", "command": "DiscardFromPlay", "ref": f"{EFFECTS}::play_as_pokemon_effect", "source": "A", "use": "candidates", "note": "おもてのカードの場での役割。うらのカードには呼ばない（F-2）"},
    {"id": "DF-2", "command": "DiscardFromPlay", "ref": "kyuura_engine/persistent.py::leave_lock", "source": "A", "use": "candidates", "note": "バトル場をはなれられない効果"},
    # RevealFaceDown
    {"id": "RF-1", "command": "RevealFaceDown", "ref": f"{ENGINE}::_reveal_face_down", "source": "A", "use": "candidates", "note": "番・自分の場・うらである（公開）"},
    {"id": "RF-2", "command": "RevealFaceDown", "ref": "kyuura_engine/zones.py::reveal_face_down", "source": "A", "use": "candidates",
     "note": "残るか・トラッシュかは本人の本当のカードで決まる（本人の知識）。候補に結果を書くなら本人だけ"},
    # CheckFaceUpDeckCard
    {"id": "CF-1", "command": "CheckFaceUpDeckCard", "ref": f"{ENGINE}::_check_face_up_deck_card", "source": "A", "use": "candidates", "note": "おもての枚数（公開）・持ち主・位置"},
    # 共通の処理のあとの確かめ
    {"id": "X-1", "command": "*", "ref": f"{ENGINE}::_identity_independent", "source": "D", "use": "none", "note": "相手のうらのカードを置きかえてコマンドを試す（最大 512 回）"},
    {"id": "X-2", "command": "*", "ref": f"{ENGINE}::_apply_once", "source": "D", "use": "none",
     "note": "処理のあとの確かめ（決められない姿・MH1・［ずらかる］・おもての山札・ミラクルエネルギー・［でんせつのからだ］・反応の決定の行きどまり）"},
]

# ---------------------------------------------------------------- カードごとの確かめ（登録と静的な走査）

# 走査: effects.py の各クラスの確かめのメソッドから、同じファイルの関数・self のメソッドへの呼び出しの閉包をたどり、持ち主の知識の関数を呼ぶもの・
# 状態の複製（.clone）を作るものを集める（ほかのモジュールは追わない）。走査の結果をここに記録し、--check で作り直して照らす
OWNER_KNOWLEDGE_FUNCS = ("unseen_card_pool", "deck_target_lower_bound", "deck_lower_bound_where", "possible_deck_cards", "searchable_deck_cards")
SCAN = {
    "check_playable": {
        "methods": 77,
        "owner_knowledge": ["BenchNameGroupFromDeckTrainer", "CoinsSearchBasicEnergyPerHeads", "DiscardDeckTopThenReturnTypeEnergy", "LookTopTakePokemonThenShuffle",
                            "ReturnHandEnergyThenCoinSearchBasicEnergy", "SearchDeckTrainer"],
        "trials": ["BlainesHeightQuiz", "BlainesQuiz", "CoinHealAndCureOwnActive", "CoinHealBothElseSleepBoth", "CoinStatusOnOpponentActiveTrainer", "ConditionOwnActiveTrainer",
                   "GuessOpponentPrizeKind", "SetAsideGuessKindQuiz", "SwapPleaseTrainer", "SwitchOpponentWithBench", "SwitchWithBench"],
    },
    "check_usable": {
        "methods": 70,
        "owner_knowledge": ["CoinAttachEnergyFromDeckToOwnPokemon", "CoinEvolveSelfFromDeck", "SearchDeckWithBenchLettersToHand", "SearchEvolutionCardToHand"],
        "trials": ["ChooseFossilEvolvedThenCoinDevolveAll", "CoinConditionOnEitherActive", "ReturnActiveToHandWithBenchLetters", "Shapeshift", "StopOpponentBenchPowersThisTurn",
                   "SwitchOpponentChosenByOpponent", "SwitchOpponentOnHeads"],
    },
    "check_activation": {"methods": 9, "owner_knowledge": ["CoinBenchOwnerBasicFromDeckStadium"], "trials": []},
}

REGISTRY = {"trainers": 269, "stadiums": 41, "usable_stadiums": 21, "play_as_pokemon": 2, "stays_in_play": 29, "may_end_turn": 5,
            "powers": 183, "declared": 104, "entry_or_triggered": 21, "decision_or_with_attack": 12, "command_usable": 71}

# 宣言の入力の形（監査で check_usable を読んだ結果。静的な走査では形を決められないので、所属だけを --check が照らす）
# 形: E = energy・S = source・T = target。hand = 本人の手札の uid、attached = ついているカード、own/opp = 自分・相手の場のポケモンの番号
POWER_SHAPES = {
    "E(attached)+S(own)+T(own)": ["EnergyTransfer", "MoveEnergyAmongNamed"],
    "E(attached)+S(own)": ["TakeEnergyToSelf", "ConvertBasicEnergyColor"],
    "E(hand)+T(own)": ["AttachEnergyFromHand"],
    "E(hand)": ["DiscardTypeEnergyFromHand"],
    "S(own)+T(own)": ["MoveDamageCounter"],
    "S(opp)+T(opp)": ["MoveOpponentDamageCounter"],
    "S(own)": ["MoveDamageCounterToSelf", "MoveGroupCounterToSelf"],
    "T(opp bench)": ["StopOpponentBenchPowersThisTurn"],
    "none": ["ChargeBenchEnergyToSelf", "ChooseFossilEvolvedThenCoinDevolveAll", "CoinAttachEnergyFromDeckToOwnPokemon", "CoinAttachFromDiscardToTypePokemon",
             "CoinBenchNamedFromDeck", "CoinConditionOnEitherActive", "CoinDamageOpponentActiveThenEndTurn", "CoinEachPlayerLooksOpponentHand",
             "CoinEachPlayerShufflesOpponentDeck", "CoinEvolveSelfFromDeck", "CoinFossilAttackBonusThisTurn", "CoinGroupAttackImmunityNextTurn",
             "CoinLookOpponentHandMayReturnTrainer", "CoinPeekOpponentDeckTopMayShuffle", "CoinPoisonMistUntilNextTurn", "CoinPutStadiumFromDiscard",
             "CoinRecoverNamedFromDiscard", "CoinRecoverTrainerWithBenchLetters", "CoinReviveFromDeck", "ConvertAttachedEnergy", "ConvertSelfToEnergy",
             "CureBothActivesOncePerTurn", "CureOneActiveConditionOnHeadsFromBench", "DiscardThenDraw", "DrawThenPutHandCardOnDeckTop", "GatherTypeEnergyCardsToSelf",
             "HealOwnPokemonOnHeads", "LookOpponentDeckTopKeepOrder", "LookOwnPrizeCard", "PeekCard", "RemoveOwnCounterOncePerTurn", "ReturnActiveToHandWithBenchLetters",
             "ReturnHandThenDrawSameWithBenchLetters", "ReturnSelfToHand", "SearchDeckWithBenchLettersToHand", "SearchEvolutionCardToHand", "Shapeshift", "ShiftColor",
             "SuperTransformPower", "SwapPrizeWithDeckTop", "SwitchOpponentChosenByOpponent", "SwitchOpponentOnHeads", "SwitchSelfFromBench", "TakeEnergiesToSelf",
             "TypeChangeSelfUntilTurnEnd"],
}
# 宣言のコマンドで使えない（決定・ワザの宣言といっしょに使う）宣言する特殊能力の型
POWER_NOT_BY_COMMAND = ["PreventKnockOutOnHeads", "ReturnToHandOnKnockOut", "BeamOnKnockOut", "FleeAfterAttackDamage", "TakeBenchDamageInstead", "BenchNamedFromDeckOnAttackDamage",
                        "ReturnToDeckOnHeadsInsteadOfKnockOut", "ExtraEnergyDamageWithAttack", "AttackDeclaredPower", "CoinsUntilTailsBonusToGroupAttack", "CounterBonusToGroupAttack"]
POWER_NOT_BY_COMMAND_BASES = ["EntryPower", "TriggeredPower"]

STADIUM_SHAPES = {
    "E(attached, own)": ["CureByDiscardingEnergyStadium", "ReturnBasicEnergyStadium"],
    "none": ["CoinReturnOwnerPokemonStadium", "CoinDrawStadium", "CoinRetrieveBasicEnergyStadium", "CoinBenchOwnerBasicFromDeckStadium", "CoinHealOwnActiveStadium",
             "LookDeckTopStadium"],
    "not_usable": ["StadiumEffect"],
}

# ---------------------------------------------------------------- 入力の契約

INPUT_REUSE = [
    {"need": "1 段（手札のトレーナー・場のポケモン 1 匹・おもての位置）", "existing": "choose_option の 1 段（U7-3 の play_basic と同じ）", "change": "なし"},
    {"need": "特殊能力 → 1 つの選ばせるもの（E(hand)・S(own)・T(opp bench)）", "existing": "2 段 + options_by_choice（U7-3 の _pair_candidate・U7-4 の宣言の選択）", "change": "なし"},
    {"need": "特殊能力 → E → T（エナジートランス・あまごいなど。S は E がついているポケモンで決まる）", "existing": "2 段目の選べるものの番号を組ごとに分け、3 段目の options_by_choice を 2 段目の番号で引く",
     "change": "depends_on_stage に 2 を許す（追加だけ。形式の版 1 のまま。既存のクライアントが 1 だけを仮定していれば読めない）"},
    {"need": "スタジアム → E（タマムシ・ヤマブキ）", "existing": "1 段（energy の組は 1 つだけなので 2 段にしない。使う候補が 1 つのときは options の各要素がエネルギーカード）", "change": "なし"},
    {"need": "選ばせるもののない特殊能力・スタジアム", "existing": "段のない候補（end_turn と同じ）", "change": "なし"},
    {"need": "受理のあとの決定（対象・枚数・検索・コイン後の選択）", "existing": "answer_decision（U7-1）", "change": "なし。宣言の前へ移さない"},
]
INPUT_RULES = [
    "宣言の前の入力を全組み合わせで列挙しない（段ごとに、前の段の番号で引く）",
    "宣言のあとの決定を宣言の前へ移さない（トレーナーの対象・枚数、スタジアムのコインのあとの選択）",
    "任意の辞退（宣言しない）・0 個の選択（energy を選ばない）・答えの並び（order）を区別する。宣言の選択は並びに意味がない（order: not_applicable）",
    "カード名・カード ID による共通処理の分岐を前提にしない。選ばせるものの形は、型ごとの宣言（登録の要素）から作る",
    ("選ばせるものの形の宣言は今の登録にない（check_usable の中にだけある）。最小の拡張: PowerEffect・StadiumEffect の型に、選ばせるもの（項目・指す場所）の宣言を加え、"
    "check_usable と食い違わないことを型ごとのテストで確かめる（D-U75-INPUT-DECL。エンジンの挙動は変えない）"),
]
# CORR-2: 比べる相手は GUI のコミット（GUI のリポジトリ）。GUI が固定するエンジンのコミットとは別に書く。読み取りだけで確かめた（GUI は実行していない）
GUI_REF = {"repository": "kyuura-engine-gui", "branch": "feature/engine-u7-4-attacks", "commit": "36499462cbdd68fe9e4b18b0c73428c9d628ddf3",
           "pinned_engine": "9506d6305e90ec262fbe77740d9aa57f04b980b6", "pinned_engine_version": "0.166.0",
           "main_commit": "7660ab4d4c4064334952b2d3c9a01ede33c4973b", "main_pinned_engine": "d0c5cfa9483aacae0cce2fd8d28166b1d8465500",
           "checked": "2026-11-08 に git fetch して、contract/kyuura-client-api-v1.json と web/src・server/tests の該当箇所を git show・git grep で読んだ（作業ツリーは変えていない）",
           "limit": "公開されている GUI のブランチのうち最新のコミット。GUI を実行していないので、画面で動くことは確かめていない。これより新しい未公開の作業は確かめられない"}
GUI_INPUTS = [
    {"item": "入力の種類", "gui": "choose_option・choose_value（contract の input_kinds）", "u7_5": "choose_option だけ", "same": True},
    {"item": "2 段と options_by_choice", "gui": "U7-3・U7-4 の候補を入力の画面で扱う（gui_operable_kinds に play_basic〜use_attack）", "u7_5": "使う（U7-5d・e）", "same": True},
    {"item": "3 段目の depends_on_stage = 2", "gui": "未確認（stage_keys に depends_on_stage はあるが、2 段目を前提にした画面は確かめていない）", "u7_5": "特殊能力の E → T で使う（U7-5e）",
     "same": False},
    {"item": "処理可能性・input_disclosure・理由の語彙", "gui": "契約の表の 6 区分・3 区分・reason_codes（13 語）", "u7_5": "U7-5a・b は既存の語だけを使う", "same": True},
    {"item": "候補の種類", "gui": "turn_kinds_not_covered に 7 種類。gui_operable_kinds にない種類は表示だけで選べない", "u7_5": "3 種類を足す（U7-5a・b）。GUI の契約の表を直すまで表示だけ",
     "same": False},
    {"item": "段の role", "gui": "stage_roles は use_attack だけ（ほかの種類の role の並びを決めていない）", "u7_5": "disguised・discard・face_down（1 段）", "same": False},
    {"item": "coverage の scope_kinds の並び", "gui": "server/tests/test_contract.py が main_kinds と同じ並びを確かめる", "u7_5": "MAIN_KINDS の順のまま（_scope_kinds）", "same": True},
]

# ---------------------------------------------------------------- 処理可能性の 4 つの軸

AXES = [
    {"command": "PlayTrainer", "display": "本人の手札のトレーナーごと（ゲーム上できないものは出さない。登録なし・未裁定は消さずに表示）",
     "input_disclosure": "confirmed（手札のカードの番号だけ）。E の 11 の実装に当たるカードは、たどるまで入力を返さない（unconfirmed。CORR-1）",
     "submit": "may_stop_later。not_implemented と停止は送れない",
     "after": "コイン・決定・［ちえくらべ］・使わない答えの続きの確かめ（D）で止まりうる。supported にしない"},
    {"command": "UsePokemonPower", "display": "自分の場のポケモンの宣言する特殊能力ごと（決定・ワザといっしょの特殊能力は出さない）",
     "input_disclosure": "形の宣言がある型は confirmed、ない型・E の 7 の実装は unconfirmed（INPUT_BOUNDARY_UNCONFIRMED。CORR-1）", "submit": "may_stop_later",
     "after": "コイン・決定・反応・相手のうらのカードの割り当ての試行（D）"},
    {"command": "UseStadium", "display": "場のスタジアムに使ってよい効果があるとき（番のプレイヤーだけ）", "input_disclosure": "confirmed（energy の 2 の実装）・no_input",
     "submit": "may_stop_later（コインのあとの決定）", "after": "コイン・決定・空いたバトル場"},
    {"command": "RemoveDisguise", "display": "disguise のある自分の場のポケモン", "input_disclosure": "confirmed", "submit": "may_stop_later（MH1・TK1）",
     "after": "決定なし。処理のあとの確かめ（D）だけ"},
    {"command": "DiscardFromPlay", "display": "自分の場のおもての化石・人形（うらのカードは出さない）", "input_disclosure": "confirmed",
     "submit": "supported の条件は U7-3 と同じ（受理のあとの停止のもとが場にないことを公開の情報で確かめた場合）。ほかは may_stop_later", "after": "バトル場が空けば勝ち負け・交代"},
    {"command": "RevealFaceDown", "display": "自分の場のうらのカード", "input_disclosure": "confirmed",
     "submit": "may_stop_later（トラッシュのあとの処理）", "after": "本当のカードで残るか決まる（本人は知る）"},
    {"command": "CheckFaceUpDeckCard", "display": "相手の山札の 2 枚目より下のおもての位置だけを unresolved_ruling（FU2）で表示（D-U75-FACE-UP）",
     "input_disclosure": "no_input（位置は候補ごと）", "submit": "送れない（どの場合も受け付けない）", "after": "なし"},
]

# ---------------------------------------------------------------- U7 全体の完了の基準と、判断事項の範囲

COMPLETION = [
    {"id": "C-1", "criterion": "対応するコマンドと宣言の経路: プレイヤーのコマンドの型すべてに候補の種類があり、7 種類の外に残る経路（R-1・R-2）を一覧で示す"},
    {"id": "C-2", "criterion": "必要な入力の取得と送信: 宣言の前の入力を段で取得でき、check と submit が同じエンジンの確かめを通る。受理のあとの決定は answer_decision で答えられる"},
    {"id": "C-3", "criterion": "未対応・未確認の経路の明示: not_implemented・unresolved_ruling・technical_limit・unverified の候補を消さない。E の確かめを対応済みに数えない"},
    {"id": "C-4", "criterion": "情報境界: 候補・inputs・check が D の確かめを呼ばない。A-own を使う経路ごとに秘密の配分を変えた双子が通る。拒否は相手・観戦者に知らせない"},
    {"id": "C-5", "criterion": "直接実行との一致: 候補どおりの送信と直接のコマンドで、状態・乱数・ログ・診断が一致する（意図した差は文書に書く）"},
    {"id": "C-6", "criterion": "段階・主体ごとの coverage: 段階（準備・番・決定・ホスト）と主体（番のプレイヤー・番でないプレイヤー・ホスト）ごとに evaluated・not_covered を示す。"
     "complete と称するのは、その段階・主体の種類がすべて evaluated で、E の確かめが残らないときだけ"},
]
DECISION_SCOPE = [
    {"id": "D-U7-COMPLETENESS", "now": "U7-5 の各単位のあとも main は partial のまま（E の確かめと R-1・R-2 が残るため）。complete の条件を C-6 で表すこと",
     "later": "U7-5 のすべての単位のあと、E が残らない段階・主体だけを complete と称するかの採用"},
    {"id": "D-U7-DISPLAY", "now": "U7-5 で新しい区分を足さない（6 区分のまま）。CheckFaceUpDeckCard の FU2 を unresolved_ruling で表示し送れないこと",
     "later": "区分ごとの GUI の表示（色・送信のボタン）。GUI の追従のときに決める"},
]

# ---------------------------------------------------------------- 実装の単位

VERIFY = [
    {"id": "V-NORMAL", "what": "正常・拒否・受理のあとの停止（拒否と受理のあとの停止を結果で区別する）"},
    {"id": "V-DECL", "what": "宣言の前の入力と、宣言のあとの決定（決定を宣言の前に移していない）"},
    {"id": "V-NONTURN", "what": "番でない主体の操作（候補が空・送っても拒否・相手に拒否を知らせない）"},
    {"id": "V-LIMIT", "what": "回数の制限（この番に使った・同じ番の再使用）"},
    {"id": "V-TWIN", "what": "非公開のカードと秘密の配分を変えた双子（候補・件数・並び・理由・不正な入力への応答が一致）"},
    {"id": "V-NOSIDE", "what": "候補・inputs・check で状態・乱数・ログが変わらない"},
    {"id": "V-BADQUERY", "what": "不正な問い合わせ（知らない番号・型の違う値・重なり）の安全性"},
    {"id": "V-PARITY", "what": "U7・client_api・直接のコマンドの結果の一致"},
    {"id": "V-HANDLE", "what": "取っ手の契約（受理で失効・拒否で他の主体の取っ手を失効させない・古い取っ手・別の主体・別の対戦）"},
    {"id": "V-CONV", "what": "3 つの規約集合（CS-KYUURA-CURRENT・CS-KYUURA-PLAY-S2A・CS-KYUURA-PLAY-PO）"},
    {"id": "V-INSTALL", "what": "Git の URL からの通常のインストールと client_api のスモークテスト"},
    {"id": "V-REGRESS", "what": "既存の U1〜U7 の回帰（U7-1〜U7-4・client_api・仕様の生成器の検査）"},
    {"id": "V-JSON", "what": "GUI が必要とする JSON の例（候補・入力・送信・決定への接続・停止と拒否）"},
]
EVERY_UNIT = ("V-NORMAL", "V-NONTURN", "V-NOSIDE", "V-BADQUERY", "V-PARITY", "V-HANDLE", "V-CONV", "V-INSTALL", "V-REGRESS", "V-JSON")
TEST_KINDS = {"board": "構築盤面（build_test_state）", "helper": "補助関数だけの確かめ（候補の作成を直接呼ぶ）", "sequence": "new_game からの合法な操作列"}

UNITS = [
    {"id": "U7-5a", "name": "場のポケモン 1 匹を指す操作（RemoveDisguise・DiscardFromPlay）", "commands": ["RemoveDisguise", "DiscardFromPlay"], "depends": ["U7-4"], "first": True,
     "basis": ["2 つの処理の受理の前の確かめは 3〜4 個で、どれも公開の値（番・自分の場・disguise・場での役割・leave_lock。RD-1・DF-1・DF-2）",
               "宣言の入力は pokemon 1 つだけ（登録が決める選ばせるものがない）。コイン・宣言の前の先読み・カードごとの確かめ（77・70・9 の実装）を通らない",
               "相手のうらのカードを指定しない（designate_face_down を呼ばない）ので、_identity_independent の試行が起こらない",
               "処理のあとの確かめで止まるのは RemoveDisguise の MH1・TK1 だけ。DiscardFromPlay は決定を出さず、空いたバトル場だけ"],
     "changes": ["engine.py: 2 つの処理の受理の前の部分を、同じ順番・同じコード・同じ文のまま check_remove_disguise・check_discard_from_play にする（U7-3 の check_* と同じ）",
                 "legal_actions.py: 2 種類の候補（1 段・choose_option・場のポケモンの番号）。うらのカードは DiscardFromPlay の候補に出さない（F-2 の FD1 に当てない）"],
     "tests": [["V-NORMAL", "board"], ["V-NONTURN", "board"], ["V-NOSIDE", "board"], ["V-BADQUERY", "helper"], ["V-PARITY", "board"], ["V-HANDLE", "board"],
               ["V-CONV", "sequence"], ["V-TWIN", "board"], ["V-INSTALL", "sequence"], ["V-REGRESS", "board"], ["V-JSON", "helper"]],
     "boards": ["tests/test_virtual_attacks_transformation_v0_49.py（タケシのキュウコンの「ばける」）", "tests/test_fossil_hidden_info_v0_47.py（なにかの化石・ピッピ人形）",
                "tests/test_active_leave_locks_v0_93.py（バトル場をはなれられない）"],
     "done": "2 種類が evaluated になり、MH1・TK1 に当たる候補は may_stop_later、DiscardFromPlay は U7-3 と同じ条件でだけ supported。直接のコマンドとの一致・双子（うらのカードの本当のカード）が通る",
     "gui": "1 段の choose_option（場のポケモンの番号）。決定への接続は promote_active の候補（空いたバトル場）",
     "open": [], "status": "implemented", "implemented_in": "v0.167（docs/legal-actions-u7-5ab.md）"},
    {"id": "U7-5b", "name": "うらのカード（RevealFaceDown）", "commands": ["RevealFaceDown"], "depends": ["U7-5a"], "first": False,
     "basis": ["受理の前の確かめは公開の値だけ（RF-1）。結果（残る・トラッシュ）は本人の本当のカードで決まり、本人は観測の real で知っている"],
     "changes": ["engine.py: _reveal_face_down の受理の前の部分を check_reveal_face_down にする", "legal_actions.py: 1 段の候補。候補に結果（残るか）を書くかは D-U75-REVEAL-OUTCOME"],
     "tests": [["V-NORMAL", "board"], ["V-NONTURN", "board"], ["V-NOSIDE", "board"], ["V-BADQUERY", "helper"], ["V-PARITY", "board"], ["V-HANDLE", "board"],
               ["V-CONV", "sequence"], ["V-TWIN", "board"], ["V-INSTALL", "sequence"], ["V-REGRESS", "board"], ["V-JSON", "helper"]],
     "boards": ["tests/test_secret_plan_v0_67.py（マチスの秘策）"],
     "done": "相手・観戦者の応答が、本人のうらのカードの本当のカードで変わらない双子（たね・たねでない）が通る。おもてにしたあとのログが観測の規則どおり",
     "gui": "1 段。おもてにしたあとの公開のログ（secret_plan_revealed・secret_plan_discarded）の表示", "open": [], "status": "implemented",
     "implemented_in": "v0.167（docs/legal-actions-u7-5ab.md）"},
    {"id": "T-F1", "name": "錯乱ジムの情報漏れ F-1 の修正（両モード共通の不具合。トレーナーの前の独立した作業）", "commands": [], "depends": ["U7-5b"], "first": False,
     "status": "implemented", "implemented_in": "v0.168（docs/chaos-gym-borrow-t-f1.md。サイキックコントロールの F-8 もいっしょに直した）",
     "basis": ["F-1: 錯乱ジムの「うら」で、相手がかわりに使えるかの確かめが相手の手札の中身を読み、その結果が公開のログと決定の有無で伝わる（再現済み）"],
     "changes": ["effects.py: borrow_public_unusable_reason・borrow_condition_stop・require_borrow_playable（公開の部分と、使う人だけが知る使うための条件を分ける）。サイキックコントロールの選べるもの・答えの確かめ",
                 "engine.py: _chaos_tails（公開の分岐）・_resume_trainer（「使う」の答えの確かめ）"],
     "tests": [["V-NORMAL", "board"], ["V-NONTURN", "board"], ["V-NOSIDE", "board"], ["V-BADQUERY", "helper"], ["V-PARITY", "board"], ["V-HANDLE", "board"],
               ["V-CONV", "sequence"], ["V-TWIN", "board"], ["V-INSTALL", "sequence"], ["V-REGRESS", "board"], ["V-JSON", "helper"]],
     "boards": ["tests/test_stadiums_v0_57.py（錯乱ジム）"], "done": "相手の手札の中身だけを変えた双子で、使ったプレイヤー・観戦者が受け取る公開の情報が一致する。2 つのモードで同じ扱い",
     "gui": "錯乱ジムの「うら」のあとは、使えない人にも決定が出る。「使う」の拒否は答えた人にだけ返る",
     "open": ["F-9（公開の情報だけで満たせないと分かる使うための条件を、公開の分岐に戻すかの判断と監査）"]},
    {"id": "U7-5c", "name": "手札のトレーナー（PlayTrainer）", "commands": ["PlayTrainer"], "depends": ["U7-5b", "T-F1"], "first": False,
     "dependencies_met": "T-F1 は v0.168 で実装（U7-5b は v0.167）",
     "status": "implemented", "implemented_in": "v0.169（docs/legal-actions-u7-5c.md）",
     "basis": ["宣言の入力は card だけ。対象・枚数・検索はすべて受理のあとの決定（answer_decision で答えられる）",
               "受理の前の確かめ（PT-1〜PT-7）は A・A-own で、カードごとの確かめの 11 の実装（試行）だけが E",
               "v0.169: E の 11 のうち、試すのが場の処理だけの 6 は読む値をたどって候補の作成で呼ぶ（PT-5t）。実際の山札から引いて試す 5 は呼ばない（PT-5e。unverified）"],
     "changes": ["engine.py: _play_trainer の手札から出す前の部分を check_play_trainer にする（同じ順番・同じコード・同じ文。use_condition が偽なら使うための条件だけを呼ばない）",
                 ("legal_actions.py: 1 段の候補 play_trainer（選べるものは本人の手札のトレーナーカード）。登録なしは not_implemented、停止は診断のコード表の分類。"
                  "使うための条件を呼ばないカード（PLAYABLE_NOT_EVALUATED）は unverified（入力は本人の手札だけで決まるので返す。条件の結果で選べるものを選り分けない）")],
     "tests": [["V-NORMAL", "board"], ["V-DECL", "board"], ["V-NONTURN", "board"], ["V-NOSIDE", "board"], ["V-BADQUERY", "helper"], ["V-PARITY", "board"],
               ["V-HANDLE", "board"], ["V-CONV", "sequence"], ["V-TWIN", "board"], ["V-INSTALL", "sequence"], ["V-REGRESS", "board"], ["V-JSON", "helper"]],
     "boards": ["tests/test_instant_trainers_v0_55.py", "tests/test_stadiums_v0_57.py（錯乱ジム・リムーブ禁止ジム）", "tests/test_slowking_mind_games_v0_132.py（［ちえくらべ］）"],
     "done": "A-own の 6 の実装で双子が通る。錯乱ジムの「うら」・［ちえくらべ］・サイキックコントロールは受理のあとの決定として new_game からの列でつながる。"
             "E のうち読む値をたどっていない 5 の実装は、使うための条件を呼ばず unverified（対応済みに数えない）",
     "gui": "1 段。受理のあとの決定の種類が多い（検索・見たカード。U7-1 の DECK_REVEALING_KINDS の契約の例外）",
     "open": ["PT-5e の 5 の実装（実際の山札から引いて試す）の読む値をたどる", "effects.py の外の閉包（PT-5t・A 群の呼ぶ別のモジュールの関数の 2 段目より先）"]},
    {"id": "U7-5d", "name": "場のスタジアム（UseStadium）", "commands": ["UseStadium"], "depends": ["U7-5a"], "first": False,
     "status": "implemented", "implemented_in": "v0.170（docs/legal-actions-u7-5d.md）",
     "basis": ["9 の実装のうち energy を選ばせるのは 2 つ。ほかは選ばせるものがない。キョウの忍者ジムだけ A-own",
               "v0.170: 使える 8 の実装の check_activation の閉包に、状態の複製・U7-5c の場の試行（state_stop_after・switch_max_hp_drop_check）はない（US-4）"],
     "changes": ["engine.py: _use_stadium の check_activation までを check_use_stadium にする（同じ順番・同じコード・同じ文）",
                 "effects.py: StadiumEffect.energy_choice（選ばせるものの宣言。挙動は変えない）",
                 "legal_actions.py: use_stadium。使ってよい効果（activated）だけ。選ばせるもののない候補と、energy の 1 段の候補"],
     "tests": [["V-NORMAL", "board"], ["V-DECL", "board"], ["V-NONTURN", "board"], ["V-LIMIT", "board"], ["V-NOSIDE", "board"], ["V-BADQUERY", "helper"],
               ["V-PARITY", "board"], ["V-HANDLE", "board"], ["V-CONV", "sequence"], ["V-TWIN", "board"], ["V-INSTALL", "sequence"], ["V-REGRESS", "board"], ["V-JSON", "helper"]],
     "boards": ["tests/test_stadiums_v0_57.py", "tests/test_remaining_stadiums_v0_74.py", "tests/test_ninja_gym_oracle_v0_146.py"],
     "done": "持ち主でないプレイヤーの使用・同じ番の 2 回目（STADIUM_ALREADY_USED・LK1）・キョウの忍者ジムの双子が通る", "gui": "選ばせるもののない候補と 1 段の候補",
     "open": ["キョウの忍者ジムの保守的な NJ1（山札の外の見えないカードの数より多くキョウのたねポケモンがないと止める。v0.146 のまま）",
              "check_activation が呼ぶ別のモジュールの関数の 2 段目より先"]},
    {"id": "U7-5e", "name": "宣言する特殊能力（UsePokemonPower）", "commands": ["UsePokemonPower"], "depends": ["U7-5b", "U7-5d"], "first": False,
     "status": "implemented", "implemented_in": "v0.171（docs/legal-actions-u7-5e.md）",
     "basis": ["宣言の入力の形が 9 通り（POWER_SHAPES）。形は check_usable の中にだけあり、登録が宣言していない", "相手のうらのカードを指す入力は X-1 の試行になる（D）",
               "v0.171: 型ごとの宣言 effects.POWER_INPUT_STAGES（56 の型）。3 段の依存は、前のすべての段の選び方ごとに別の番号（after・upstream_stages）"],
     "changes": ["effects.py: 型ごとの選ばせるものの宣言（D-U75-INPUT-DECL。挙動は変えない）", "engine.py: _use_pokemon_power の宣言の前の部分を check_use_pokemon_power にする（_reveal_for_action の扱いは D-U75-POWER-FACE-DOWN）",
                 "legal_actions.py: 特殊能力の位置ごとの候補 → 選ばせるもの（0〜3 段）"],
     "tests": [["V-NORMAL", "board"], ["V-DECL", "board"], ["V-NONTURN", "board"], ["V-LIMIT", "board"], ["V-NOSIDE", "board"], ["V-BADQUERY", "helper"],
               ["V-PARITY", "board"], ["V-HANDLE", "board"], ["V-CONV", "sequence"], ["V-TWIN", "board"], ["V-INSTALL", "sequence"], ["V-REGRESS", "board"], ["V-JSON", "helper"]],
     "boards": ["tests/test_power_decisions_v0_42.py", "tests/test_pokemon_powers_v0_5.py（エナジートランス）", "tests/test_rain_dance_v0_6.py"],
     "done": "形ごとに 1 つ以上の代表で、宣言の入力・受理のあとの決定・回数の制限が通る。相手のうらのカードは公開の位置・識別だけで扱う（ADOPT-U7-5AB）。"
             "E の 7 の実装は、たどるまで入力を返さない（CORR-1）",
     "gui": "2〜3 段（depends_on_stage = 2。前の段を変えたら、それに依存する後の段をすべて無効にする。ADOPT-U7-5AB）",
     "open": ["名前で解決できない呼び出し（状態のメソッド・登録表の引き・正規表現）の先（UP-5t）", "自分のうらのカードの特殊能力（候補にしない。R-2 と同じく残る）"]},
    {"id": "U7-5f", "name": "おもての山札の確かめ（CheckFaceUpDeckCard）", "commands": ["CheckFaceUpDeckCard"], "depends": ["U7-5a"], "first": False,
     "basis": ["どの場合も受け付けない。表示するのは FU2 の位置だけ（D-U75-FACE-UP）"],
     "changes": ["legal_actions.py: 相手の山札のおもての 2 枚目より下の位置を unresolved_ruling で示す（送れない）"],
     "tests": [["V-NORMAL", "board"], ["V-NONTURN", "board"], ["V-NOSIDE", "board"], ["V-BADQUERY", "helper"], ["V-PARITY", "board"], ["V-HANDLE", "board"],
               ["V-CONV", "sequence"], ["V-TWIN", "board"], ["V-INSTALL", "sequence"], ["V-REGRESS", "board"], ["V-JSON", "helper"]],
     "boards": ["tests/test_flash_faceup_deck_v0_126.py（フラッシュ）"],
     "done": "候補の位置が、おもての枚数（公開）だけで決まる双子（おもてのカードの中身を変える）が通る", "gui": "表示だけ（送信のボタンを出さない）", "open": []},
    {"id": "U7-5g", "name": "残りの経路と coverage の閉じ方", "commands": [], "depends": ["U7-5c", "U7-5e", "U7-5f"], "first": False,
     "basis": ["7 種類で説明できない経路（R-1・R-2）が残る"],
     "changes": ["R-1（カツラの 2 枚目）を attach_energy の任意の段として加える（ADOPT-U7-5AB で採用）・R-2 の見直し", "段階・主体ごとの coverage の表し方（C-6）"],
     "tests": [["V-NORMAL", "board"], ["V-NONTURN", "board"], ["V-NOSIDE", "board"], ["V-BADQUERY", "helper"], ["V-PARITY", "board"], ["V-HANDLE", "board"],
               ["V-CONV", "sequence"], ["V-INSTALL", "sequence"], ["V-REGRESS", "board"], ["V-JSON", "helper"]],
     "boards": [], "done": "C-1〜C-6 を満たすかを、単位ごとの結果から判断できる", "gui": "coverage の表示", "open": ["D-U7-COMPLETENESS"]},
]

# ---------------------------------------------------------------- 調査で見つけたこと（エンジンは直さない）

FINDINGS = [
    {"id": "F-1", "kind": "情報境界", "status": "fixed",
     "history": ["v0.166 のあとの U7-5 の設計の調査で見つけ、作業用のスクリプトの双子で再現した（2026-11-08）",
                 "T-F1 で、修正の前の木に回帰テスト（tests/test_chaos_gym_borrow_t_f1.py）を加えて再び再現した（漏れを見つけた失敗 4 件）",
                 "v0.168（T-F1。docs/chaos-gym-borrow-t-f1.md）で直した: 公開の分岐を公開の情報だけで決め、使うための条件は「使う」と答えたときに確かめる"],
     "summary": "錯乱ジムの「うら」で、相手がかわりに使えるかの確かめ（borrow_unusable_reason → check_playable）が相手の手札の中身を読み、その結果が公開のログ "
                "chaos_not_borrowable（理由にコード）と、決定 ACCEPT_REQUEST が出るかで、使ったプレイヤーに伝わる",
     "evidence": "双子（使ったプレイヤーの手札にポケモン育て屋さんとリザードン、場にヒトカゲ。相手のバトル場もヒトカゲ。相手の手札 1 枚がリザードンか水エネルギーかだけが違う）で、"
                 "片方は ACCEPT_REQUEST（相手）、片方は chaos_not_borrowable（NO_EVOLUTION_TARGET）",
     "refs": [f"{ENGINE}::_chaos_tails", f"{EFFECTS}::borrow_unusable_reason"],
     "impact": "U7 の候補は作らないが、受理のあとの決定と公開のログで起こる。両モード共通の不具合として、トレーナー（U7-5c）の前の独立の作業 T-F1 で直した（v0.168）。"
               "処理の段階: トレーナーを使う手順の錯乱ジムの「うら」のあと（engine._chaos_tails）。停止のコード（CH1・MG1・TL1）は不具合ではなく、変えていない"},
    {"id": "F-2", "kind": "拒否のコードの不一致", "status": "reproduced",
     "summary": "本人のうらのカードを DiscardFromPlay で指すと、NOT_DISCARDABLE ではなく FD1（HiddenPropertyRead）で拒否する（理由の文を作るときに名前を読む）",
     "evidence": "マチスの秘策でうらにしたディグダ・プラスパワー・ユンゲラーのどれでも同じ FD1（本当のカードによらない。漏れではない）",
     "refs": [f"{ENGINE}::_discard_from_play", f"{EFFECTS}::play_as_pokemon_effect"],
     "impact": "エンジンの拒否は変えない。U7-5a はエンジンの確かめの判定（UnsupportedError）どおり、選べるものとして示して実行できない区分にする（送る前に CANDIDATE_NOT_EXECUTABLE）。"
               "ゲーム上の禁止として消さない"},
    {"id": "F-3", "kind": "保守的な停止", "status": "code_basis",
     "summary": "セキチクシティジムの対象を調べる途中で、本人の場にうらのカードがあると、ほかに対象があっても FD1 で止まりうる",
     "evidence": "監査で CoinReturnOwnerPokemonStadium.check_activation の対象の走査が form_def(...).name_ja を読むことを確かめた（再現はしていない）",
     "refs": [f"{EFFECTS}::CoinReturnOwnerPokemonStadium.check_activation"], "impact": "本当のカードによらない。U7-5d で双子に含める"},
    {"id": "F-4", "kind": "保守的な停止", "status": "reproduced",
     "summary": "［シフト］の色の候補（shift_color_options）と ConvertSelfToEnergy の対象の確かめが、相手のうらのカードの項目を読み、FD1 で止まりうる",
     "evidence": "v0.171: 相手のベンチにうらのカード（マチスの秘策。本当のカードがディグダかユンゲラーかだけが違う双子）があると、モルフォンの［へんしょく］はどちらも FD1"
                 "（HiddenPropertyRead）で止まり、候補は unresolved_ruling（実行できない区分）で同じ。tests/test_legal_actions_u7_5e.py の FaceDownTwinTest",
     "refs": [f"{EFFECTS}::ShiftColor.check_usable", f"{EFFECTS}::ConvertSelfToEnergy.check_usable"],
     "impact": "本当のカードによらない保守的な停止（漏れではない）。U7-5e は止まる候補として示す（消さない）。止め方は変えていない"},
    {"id": "F-5", "kind": "入口の確かめの順", "status": "code_basis",
     "summary": "UsePokemonPower は、指定した source・target・energy のうらのカードを、番の確かめ・入力の形の確かめより前におもてにする（_reveal_for_action）。"
                "拒否のコードは _identity_independent が本当のカードによらないものにそろえる",
     "evidence": "engine.py の _reveal_for_action と _apply_checked を読んだ（再現していない）", "refs": [f"{ENGINE}::_reveal_for_action", f"{ENGINE}::_apply_checked"],
     "impact": "候補の作成はこの順を写さない。相手のうらのカードを指す入力は unverified（D-U75-POWER-FACE-DOWN）"},
    {"id": "F-6", "kind": "入口の確かめの範囲", "status": "code_basis",
     "summary": "CheckFaceUpDeckCard は番・段階を確かめない（どの場合も受け付けないので、状態は変わらない）",
     "evidence": "engine.py の _check_face_up_deck_card", "refs": [f"{ENGINE}::_check_face_up_deck_card"], "impact": "番でない主体の候補に出すかは D-U75-FACE-UP"},
    {"id": "F-8", "kind": "情報境界（F-1 と同じ共通の経路）", "status": "fixed",
     "summary": "ナツメのサイキックコントロールの選べるもの（相手のトラッシュのトレーナー）を、使う人の使うための条件（手札・山札を読みうる）で選り分けていたので、"
                "選べるものの数（相手にも見える option_count）と、選べるものがないときの公開のログ discard_trainer_use_none が、使う人の手札の中身で変わった",
     "evidence": "T-F1 の回帰テストの双子（使う人の手札の 1 枚がヒトカゲか水エネルギーか。相手のトラッシュにポケモン交換おじさん）で、修正の前は相手の観測が違った",
     "refs": [f"{EFFECTS}::discard_trainer_use_choices", f"{EFFECTS}::UseOpponentDiscardTrainer.resume"],
     "impact": "v0.168（T-F1）で直した。選べるものは公開の情報だけで作り、満たせないカードを選んだ答えを拒否する"},
    {"id": "F-9", "kind": "未対応（判断が要る）", "status": "code_basis",
     "summary": "公開の情報だけで満たせないと分かる使うための条件（自分のポケモンにエネルギーがない超エネルギーリムーブなど）も、T-F1 のあとは決定（または選べるもの）に残り、"
                "答えで拒否する。check_playable が、読む情報が公開か本人だけのものかを返さないため",
     "evidence": "tests/test_stadium_reuse_special_energy_v0_58.py の期待を直した（意図した差）",
     "refs": [f"{EFFECTS}::TrainerEffect.check_playable", f"{EFFECTS}::borrow_public_unusable_reason"],
     "impact": "公開の分岐に戻すには、77 の実装を型ごとに「公開の情報だけ」と宣言してテストで確かめる監査が要る。監査して戻すか、一様な扱いのままにするかは利用者の判断"},
    {"id": "F-7", "kind": "候補の取得の失敗（U7-3。直した）", "status": "reproduced",
     "summary": "にげるの候補が、バトル場のなにかの化石・ピッピ人形（PF2）と自分のうらのバトル場のポケモン（FD1）で、にげるエネルギーを求めて例外になり、"
                "候補の取得そのものが失敗していた（v0.165〜v0.166）",
     "evidence": "v0.47 の盤面（バトル場のなにかの化石）と、v0.67 の盤面でうらのカードをバトル場にした盤面で、candidates() が UnsupportedError・HiddenPropertyRead を上げた",
     "refs": ["kyuura_engine/legal_actions.py::_retreat_candidate", f"{EFFECTS}::retreat_cost"],
     "impact": "U7-5a・b で legal_actions だけを直した（エンジンは変えない）。PF2 は実行できない候補（選べるものなし）、FD1 は unverified で入力を返さない"},
]

ADOPTION_NEEDED = [
    {"id": "D-U75-ORDER", "question": "実装の単位と順（U7-5a → b → c → d → e → f → g）", "recommendation": "この順（共通の処理と情報境界の易しい順。GUI の対戦への効果は c が大きいが、a・b の型を先に固める）"},
    {"id": "D-U75-FIRST", "question": "最初の単位を U7-5a（RemoveDisguise・DiscardFromPlay）にするか", "recommendation": "する（7 章の根拠）"},
    {"id": "D-U75-CHAINED", "question": "3 段目の options_by_choice を 2 段目の番号で引く（depends_on_stage = 2）", "recommendation": "形式の版 1 のまま追加として許す。GUI の追従の文書に書く"},
    {"id": "D-U75-INPUT-DECL", "question": "特殊能力・スタジアムの型に、選ばせるものの宣言を加える（挙動は変えない）", "recommendation": "加える。宣言のない型は input_disclosure を unconfirmed にする"},
    {"id": "D-U75-POWER-FACE-DOWN", "question": "相手のうらのカードを指す特殊能力の入力を、候補でどう示すか", "recommendation": "unverified（選べるものには出し、送ればエンジンが判定する）"},
    {"id": "D-U75-REVEAL-OUTCOME", "question": "RevealFaceDown の候補に、本人のうらのカードが残るか（たねポケモンか）を書くか", "recommendation": "書かない（本人は観測の real で知っている。候補の項目を増やさない）"},
    {"id": "D-U75-FACE-UP", "question": "CheckFaceUpDeckCard を候補にどう出すか（番でない主体を含めるか）", "recommendation": "番のプレイヤーの候補に unresolved_ruling だけで出す。番でない主体には出さない"},
    {"id": "D-U75-CHAOS", "question": "F-1（錯乱ジムの借りる確かめの公開）をどう扱うか", "recommendation": "U7-5 では直さない。エンジンの別の作業として、原典の記録と照らして扱いを決める（推測で裁定にしない）"},
    {"id": "D-U75-ENERGY2", "question": "R-1（カツラの 2 枚目）を U7-5g で attach_energy の任意の段として加えるか", "recommendation": "加える（U7-3 の候補に任意の 3 段目。追加だけ）"},
]

ADOPTION = {"id": "U7-5-DESIGN", "date": "2026-11-08", "status": "proposed", "approval": "not_approved", "base": BASE_COMMIT,
            "scope": "U7-5 の調査・仕様・実装計画（候補の追加・エンジンの動作の変更はしない）"}

# 利用者の採用（実装とは別の記録）。後の単位の判断は採用の範囲の記録だけで、先に実装しない
ADOPTION_RECORD = {
    "id": "ADOPT-U7-5AB", "date": "2026-11-08", "by": "利用者",
    "scope": "U7-5 の進め方と、U7-5a＋U7-5b の実装",
    "order": ["U7-5a＋U7-5b を 1 つの作業で実装", "錯乱ジムの情報漏れ F-1 を別の作業 T-F1 で直す（両モード共通の不具合。トレーナーの前）", "U7-5c → U7-5d → U7-5e → U7-5f → U7-5g"],
    "adopted": [
        {"id": "D-U75-ORDER", "decision": "上の順（a＋b をまとめる。F-1 を c の前に直す）"},
        {"id": "D-U75-FIRST", "decision": "最初の実装は U7-5a＋U7-5b（RemoveDisguise・DiscardFromPlay・RevealFaceDown）"},
        {"id": "D-U75-CHAINED", "decision": "3 段の入力を認める。前の段を変えたら、それに依存する後の段をすべて無効にする（U7-5e で実装）"},
        {"id": "D-U75-INPUT-DECL", "decision": "型ごとの宣言の入力の記述（メタデータ）を設け、コマンドの作成・確かめとの対応をテストする（U7-5e で実装）"},
        {"id": "D-U75-POWER-FACE-DOWN", "decision": "相手のうらのカードは公開された位置・識別だけで扱い、隠れた定義を候補の作成に使わない（U7-5e で実装）"},
        {"id": "D-U75-REVEAL-OUTCOME", "decision": "RevealFaceDown では、おもてにしたあとに場に残るかを候補で予告しない（U7-5b で実装）"},
        {"id": "D-U75-FACE-UP", "decision": "CheckFaceUpDeckCard は FU2 による未対応として表示し、送れない（U7-5f で実装）"},
        {"id": "D-U75-CHAOS", "decision": "F-1 は両モード共通の不具合として別の作業 T-F1 で直す（トレーナーの前）。U7-5a・b では裁定・動作を変えない"},
        {"id": "D-U75-ENERGY2", "decision": "カツラの 2 枚目（AttachEnergy.energy2）は U7-5g に含める"},
        {"id": "D-U75-TRAINER", "decision": "U7-5c（2026-11-08 の依頼）: 手札の PlayTrainer だけを扱い、UsePokemonPower・UseStadium・CheckFaceUpDeckCard・energy2 は実装しない。"
         "カードの選択の表示は本人の手札だけで決まるので返す。読む情報を確かめていない使うための条件は呼ばず、処理可能性で示す（unverified）。F-9 の今の扱い（公開の情報だけで"
         "使えない場合も決定を出す）は変えない"},
        {"id": "D-U75-POWER", "decision": "U7-5e（2026-11-08 の依頼）: UsePokemonPower を、型ごとの宣言の入力（D-U75-INPUT-DECL）と 2〜3 段の依存する入力（D-U75-CHAINED）で扱う。"
         "CheckFaceUpDeckCard・energy2・R-2 は実装しない。相手のうらのカードは公開の位置だけで示し、指定する組は unverified（D-U75-POWER-FACE-DOWN）"},
        {"id": "D-U75-STADIUM", "decision": "U7-5d（2026-11-08 の依頼）: 場のスタジアムの UseStadium だけを扱い、特殊能力・CheckFaceUpDeckCard・energy2 は実装しない。"
         "候補は使ってよい効果の登録（activated）から作り、選ばせるものは型の宣言（energy_choice）から作る。3 段の入力の基盤は先に作らない。キョウの忍者ジムの保守的な NJ1 は緩めない"},
    ],
    "implemented_units": ["U7-5a", "U7-5b", "T-F1", "U7-5c", "U7-5d", "U7-5e"],  # T-F1 は 2026-11-08 の依頼で v0.168。U7-5c は v0.169、U7-5d は v0.170、U7-5e は v0.171
    "corrections": [
        {"id": "CORR-1", "subject": "E 群の意味", "text": "情報源が未確認の経路を、処理可能性の unverified だけで公開してよいと扱わない。処理可能性と入力の公開の安全性は別の軸。"
         "選べるもの・件数・理由を公開して安全と確かめられないなら、入力は返さない（unconfirmed）。型・生成箇所の登録だけで安全と認めない"},
        {"id": "CORR-2", "subject": "GUI への影響の比べる相手", "text": "設計の報告の d0c5cfa はエンジンのコミット（GUI の main が固定するエンジン）で、GUI のコミットではない。"
         "公開されている最新の GUI は feature/engine-u7-4-attacks の 3649946（エンジン 9506d63・0.166.0 を固定）。GUI のコミットと固定するエンジンを分けて書く（GUI_REF）"},
    ],
}

SPEC = {
    "id": "LEGAL-ACTIONS-U7-5-DESIGN", "adoption": ADOPTION, "sources": SOURCES, "commands": COMMANDS, "residual_paths": RESIDUAL_PATHS, "checks": CHECKS,
    "owner_knowledge_functions": list(OWNER_KNOWLEDGE_FUNCS), "scan": SCAN, "registry": REGISTRY, "power_shapes": POWER_SHAPES, "power_not_by_command": POWER_NOT_BY_COMMAND,
    "power_not_by_command_bases": POWER_NOT_BY_COMMAND_BASES, "stadium_shapes": STADIUM_SHAPES, "input_reuse": INPUT_REUSE, "input_rules": INPUT_RULES, "gui_inputs": GUI_INPUTS,
    "axes": AXES, "completion": COMPLETION, "decision_scope": DECISION_SCOPE, "verify": VERIFY, "every_unit": list(EVERY_UNIT), "test_kinds": TEST_KINDS, "units": UNITS,
    "findings": FINDINGS, "adoption_needed": ADOPTION_NEEDED, "adoption_record": ADOPTION_RECORD, "gui_ref": GUI_REF,
}


# ---------------------------------------------------------------- コードとの対応

def _command_fields(name: str) -> list[list]:
    from kyuura_engine import commands

    out = []
    for f in dataclasses.fields(getattr(commands, name)):
        default = None if f.default is dataclasses.MISSING else f.default
        out.append([f.name, f.type, "required" if f.default is dataclasses.MISSING and f.default_factory is dataclasses.MISSING else repr(default)])
    return out


def _resolve_code(ref: str) -> str | None:
    path, name = ref.split("::")
    if "." in name:
        return None
    module = importlib.import_module(path.removesuffix(".py").replace("/", "."))
    value = getattr(module, name, None)
    return value if isinstance(value, str) else None


def build() -> dict:
    spec = json.loads(json.dumps(SPEC, ensure_ascii=False))
    for command in spec["commands"]:
        command["code_fields"] = _command_fields(command["command"])
        for stop in command["stops"]:
            code = _resolve_code(stop[1])
            if code is not None:
                stop.append(code)
    return spec


def _defined(path: str, name: str) -> bool:
    tree = _ast(path)
    head, _, method = name.partition(".")
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.ClassDef)) and node.name == head:
            return not method or (isinstance(node, ast.ClassDef) and any(isinstance(b, ast.FunctionDef) and b.name == method for b in node.body))
        if not method and isinstance(node, (ast.Assign, ast.AnnAssign)):
            targets = node.targets if isinstance(node, ast.Assign) else [node.target]
            if any(isinstance(t, ast.Name) and t.id == head for t in targets):
                return True
    return False


_AST_CACHE: dict[str, ast.Module] = {}


def _ast(path: str) -> ast.Module:
    if path not in _AST_CACHE:
        _AST_CACHE[path] = ast.parse((ROOT / path).read_text(encoding="utf-8"))
    return _AST_CACHE[path]


def scan_checks() -> dict:
    """effects.py のカードごとの確かめのメソッドから、同じファイルの関数・self のメソッドへの呼び出しの閉包をたどる（ほかのモジュールは追わない）。"""
    tree = _ast(EFFECTS)
    funcs = {n.name: n for n in tree.body if isinstance(n, ast.FunctionDef)}
    classes = {n.name: n for n in tree.body if isinstance(n, ast.ClassDef)}

    def method(cls: str, name: str):
        queue = [cls]
        while queue:
            current = queue.pop(0)
            for b in classes[current].body:
                if isinstance(b, ast.FunctionDef) and b.name == name:
                    return current, b
            queue += [b.id for b in classes[current].bases if isinstance(b, ast.Name) and b.id in classes]
        return None

    def nodes(start, cls):
        seen, stack, found = set(), [(start, cls)], [start]
        while stack:
            node, current = stack.pop()
            for x in ast.walk(node):
                key = None
                if isinstance(x, ast.Name) and x.id in funcs:
                    key = ("f", x.id)
                elif isinstance(x, ast.Attribute) and isinstance(x.value, ast.Name) and x.value.id == "self" and current:
                    key = ("m", current, x.attr)
                if key is None or key in seen:
                    continue
                seen.add(key)
                if key[0] == "f":
                    found.append(funcs[key[1]])
                    stack.append((funcs[key[1]], None))
                else:
                    hit = method(key[1], key[2])
                    if hit:
                        found.append(hit[1])
                        stack.append((hit[1], hit[0]))
        return found

    out = {}
    for name in SCAN:
        owner, trials, count = [], [], 0
        for cls, node in classes.items():
            for b in node.body:
                if isinstance(b, ast.FunctionDef) and b.name == name:
                    count += 1
                    reached = nodes(b, cls)
                    if any(getattr(n, "name", None) in OWNER_KNOWLEDGE_FUNCS for n in reached):
                        owner.append(cls)
                    if any(isinstance(x, ast.Attribute) and x.attr == "clone" for n in reached for x in ast.walk(n)):
                        trials.append(cls)
        out[name] = {"methods": count, "owner_knowledge": sorted(owner), "trials": sorted(trials)}
    return out


def registry_counts() -> tuple[dict, set[str], set[str]]:
    from kyuura_engine import effects as E

    reg = E.DEFAULT_EFFECTS
    counts = dict.fromkeys(REGISTRY, 0)
    stadium_classes, power_classes = set(), set()
    not_by_command = set(POWER_NOT_BY_COMMAND)
    for entry in reg._trainers.values():
        effect = entry.effect
        counts["trainers"] += 1
        counts["stadiums"] += isinstance(effect, E.StadiumEffect)
        counts["play_as_pokemon"] += isinstance(effect, E.PlayAsPokemon)
        counts["stays_in_play"] += getattr(effect, "stays_in_play", False) is True
        counts["may_end_turn"] += getattr(effect, "may_end_turn", False) is True
        if isinstance(effect, E.StadiumEffect) and type(effect).check_activation is not E.StadiumEffect.check_activation:
            counts["usable_stadiums"] += 1
            stadium_classes.add(type(effect).__name__)
    for entry in reg._powers.values():
        effect = entry.effect
        counts["powers"] += 1
        if not effect.declared:
            continue
        counts["declared"] += 1
        mro = {b.__name__ for b in type(effect).__mro__}
        if mro & set(POWER_NOT_BY_COMMAND_BASES):
            counts["entry_or_triggered"] += 1
        elif mro & not_by_command:
            counts["decision_or_with_attack"] += 1
        else:
            counts["command_usable"] += 1
            power_classes.add(type(effect).__name__)
    return counts, stadium_classes, power_classes


def code_problems(spec: dict) -> list[str]:
    from kyuura_engine import commands, legal_actions

    problems = []
    refs = [c["ref"] for c in spec["checks"]] + [c["handler"] for c in spec["commands"]] + [s[1] for c in spec["commands"] for s in c["stops"]]
    refs += [r for f in spec["findings"] for r in f["refs"]]
    for ref in refs:
        path, sep, name = ref.partition("::")
        if not sep or not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*(\.[A-Za-z_][A-Za-z0-9_]*)?", name) or not (ROOT / path).exists():
            problems.append(f"参照の形が「ファイル::名前」でない・ファイルがない: {ref}")
        elif not _defined(path, name):
            problems.append(f"参照する名前がコードにない: {ref}")
    for unit in spec["units"]:
        for board in unit["boards"]:
            if not (ROOT / board.split("（")[0]).exists():
                problems.append(f"{unit['id']}: 代表の盤面のファイルがない: {board}")
    for command in spec["commands"]:
        code = _command_fields(command["command"])
        if [f[0] for f in code] != [f[0] for f in command["fields"]]:
            problems.append(f"{command['command']}: 項目の並びがコードと違う（{[f[0] for f in code]}）")
        if command.get("code_fields") is not None and command["code_fields"] != code:
            problems.append(f"{command['command']}: 項目の型・既定値がコードと違う")
    implemented = set(legal_actions.IMPLEMENTED_KINDS)
    main_spec = json.loads((ROOT / "docs" / "legal-actions-api-design.json").read_text(encoding="utf-8"))
    kind_of = {o["command"]: o["kind"] for o in main_spec["operations"]}
    remaining = sorted(name for name, cls in commands.COMMAND_TYPES.items() if kind_of.get(cls.__name__) not in implemented)
    done = {c for u in spec["units"] if u.get("status") == "implemented" for c in u["commands"]}
    listed = sorted(commands._TYPE_NAMES[getattr(commands, c["command"])] for c in spec["commands"] if c["command"] not in done)
    if remaining != listed:
        problems.append(f"候補の種類のないコマンドの型 {remaining} と、調べた 7 種類のうち実装していないもの {listed} が違う")
    for c in spec["commands"]:
        if c["command"] in done and c["kind"] not in implemented:
            problems.append(f"{c['command']}: 実装済みの単位のコマンドなのに、legal_actions.IMPLEMENTED_KINDS に種類 {c['kind']} がない")
    for command in spec["commands"]:
        if kind_of.get(command["command"]) != command["kind"]:
            problems.append(f"{command['command']}: 種類 {command['kind']} が U7 の仕様案の operations と違う")
        if command["kind"] not in legal_actions.MAIN_KINDS:
            problems.append(f"{command['command']}: 種類が legal_actions.MAIN_KINDS にない")
    if scan_checks() != spec["scan"]:
        problems.append("カードごとの確かめの静的な走査の結果が、記録と違う（監査をやり直してから SCAN を直す）")
    counts, stadium_classes, power_classes = registry_counts()
    if counts != spec["registry"]:
        problems.append(f"登録の数が記録と違う: {counts}")
    shaped = [c for group in spec["power_shapes"].values() for c in group]
    if len(shaped) != len(set(shaped)) or set(shaped) != power_classes:
        problems.append(f"特殊能力の形の表の型が、コマンドで使える宣言する特殊能力の型と違う（足りない {sorted(power_classes - set(shaped))}・余分 {sorted(set(shaped) - power_classes)}）")
    stadium_listed = {c for k, group in spec["stadium_shapes"].items() if k != "not_usable" for c in group}
    if stadium_listed != stadium_classes:
        problems.append(f"スタジアムの形の表が、使ってよい効果のある型と違う（{sorted(stadium_classes)}）")
    return problems


# ---------------------------------------------------------------- 計画の規則

def spec_problems(spec: dict) -> list[str]:
    problems = []
    ids = {c["id"] for c in spec["checks"]}
    if len(ids) != len(spec["checks"]):
        problems.append("確かめの ID が重なる")
    for c in spec["checks"]:
        if c["source"] not in SOURCE_IDS:
            problems.append(f"{c['id']}: 情報源の分類 {c['source']} が A〜E でない")
        if c["source"] in ("C", "D", "E") and c["use"] != "none":
            problems.append(f"{c['id']}: 分類 {c['source']} の確かめを候補・inputs・check に使う（{c['use']}）")
        if c["source"] in ("A", "A-own") and c["use"] not in ("candidates", "inputs"):
            problems.append(f"{c['id']}: 分類 {c['source']} の確かめの使い方 {c['use']}")
    commands = {c["command"] for c in spec["commands"]}
    for c in spec["checks"]:
        if c["command"] != "*" and c["command"] not in commands:
            problems.append(f"{c['id']}: 知らないコマンド {c['command']}")
    for command in spec["commands"]:
        if not any(ch["command"] == command["command"] for ch in spec["checks"]):
            problems.append(f"{command['command']}: 確かめの分類がない")
        for f in command["fields"]:
            if f[2] not in ("declaration_required", "declaration_optional", "not_input") or not f[3]:
                problems.append(f"{command['command']}.{f[0]}: 分類か、誰がいつ知るかがない")
    verify = {v["id"] for v in spec["verify"]}
    assigned = set()
    units = {u["id"]: u for u in spec["units"]}
    if sum(1 for u in spec["units"] if u["first"]) != 1:
        problems.append("最初に実装する単位が 1 つでない")
    covered = set()
    for u in spec["units"]:
        tested = {t[0] for t in u["tests"]}
        assigned |= tested
        covered |= set(u["commands"])
        if not tested <= verify or any(t[1] not in spec["test_kinds"] for t in u["tests"]):
            problems.append(f"{u['id']}: 知らない確かめ・テストの種類")
        missing = set(spec["every_unit"]) - tested
        if missing:
            problems.append(f"{u['id']}: すべての単位に要る確かめ {sorted(missing)} がない")
        if not {t[1] for t in u["tests"]} >= {"board", "sequence"}:
            problems.append(f"{u['id']}: 構築盤面と new_game からの列の両方がない")
        if any(d not in units and d not in ("U7-4",) for d in u["depends"]):
            problems.append(f"{u['id']}: 知らない依存 {u['depends']}")
        if u.get("status", "planned") not in ("planned", "implemented"):
            problems.append(f"{u['id']}: 状態が planned・implemented でない")
        if u.get("status") == "implemented" and u["id"] not in spec["adoption_record"]["implemented_units"]:
            problems.append(f"{u['id']}: 採用の記録にない単位を実装済みにしている")
        if not u["done"] or not u["gui"] or not u["changes"]:
            problems.append(f"{u['id']}: 変更範囲・完了の基準・GUI への引き継ぎがない")
    if covered != commands:
        problems.append(f"単位が扱わないコマンド {sorted(commands - covered)}")
    if verify - assigned:
        problems.append(f"どの単位にも割り当てない確かめ {sorted(verify - assigned)}")
    e_commands = {c["command"] for c in spec["checks"] if c["source"] == "E"}
    for u in spec["units"]:
        if set(u["commands"]) & e_commands and not u["open"]:
            problems.append(f"{u['id']}: 情報源が未確認（E）の確かめがあるのに、残る事項（open）がない")
    for f in spec["findings"]:
        if f["status"] not in ("reproduced", "code_basis", "unconfirmed", "fixed") or not f["evidence"] or not f["impact"]:
            problems.append(f"{f['id']}: 再現・根拠・影響範囲がない")
    if {d["id"] for d in spec["decision_scope"]} != {"D-U7-COMPLETENESS", "D-U7-DISPLAY"}:
        problems.append("D-U7-COMPLETENESS・D-U7-DISPLAY の範囲の分け方がない")
    if spec["adoption"]["approval"] != "not_approved":
        problems.append("採用の前の仕様が、承認済みになっている")
    return problems


# ---------------------------------------------------------------- 文書の生成区画

def _src(c) -> str:
    return f"`{c}`"


def blocks(spec: dict) -> dict[str, list[str]]:
    a = spec["adoption"]
    by_command = {c["command"]: c for c in spec["commands"]}
    return {
        "rest-adoption": [f"- `{a['id']}`（{a['date']}）: {a['scope']}", f"- 状態: `{a['status']}`・承認 `{a['approval']}`・基点 `{a['base']}`"],
        "rest-sources": _table(["分類", "意味", "候補での使い方"], [[f"`{s['id']}`", s["meaning"], s["candidate_use"]] for s in spec["sources"]]),
        "rest-commands": _table(["コマンド", "種類", "主体", "段階", "受理のあとの決定", "順序", "回数・禁止", "規約集合"],
                               [[f"`{c['command']}`", f"`{c['kind']}`", c["actor"], c["phase"], c["after_acceptance"], c["order"], c["limits"], c["conventions"]]
                                for c in spec["commands"]]),
        "rest-fields": _table(["コマンド", "項目", "型", "既定値", "分類", "意味", "誰がいつ知るか"],
                             [[f"`{c['command']}`", f"`{f[0]}`", f"`{code[1]}`", code[2], f"`{f[2]}`", f[1], f[3]]
                              for c in spec["commands"] for f, code in zip(c["fields"], c["code_fields"], strict=True)]),
        "rest-stops": _table(["コマンド", "場面", "参照", "コード", "説明"],
                            [[f"`{c['command']}`", s[0], _src(s[1]), f"`{s[3]}`" if len(s) > 3 else "（定数でない）", s[2]] for c in spec["commands"] for s in c["stops"]]),
        "rest-residual": _table(["ID", "コマンド", "経路", "今", "提案"], [[r["id"], f"`{r['command']}`", r["path"], r["unit_now"], r["proposal"]] for r in spec["residual_paths"]]),
        "rest-checks": _table(["ID", "コマンド", "参照", "分類", "使い方", "説明"],
                             [[c["id"], f"`{c['command']}`" if c["command"] != "*" else "共通", _src(c["ref"]), f"`{c['source']}`", f"`{c['use']}`", c["note"]] for c in spec["checks"]]),
        "rest-scan": _table(["確かめ", "実装の数", "持ち主の知識の関数を呼ぶ（A-own）", "状態の複製で試す（E）"],
                           [[f"`{k}`", v["methods"], [f"`{x}`" for x in v["owner_knowledge"]] or "なし", [f"`{x}`" for x in v["trials"]] or "なし"] for k, v in spec["scan"].items()])
                    + [""] + _table(["登録", "数"], [[f"`{k}`", v] for k, v in spec["registry"].items()]),
        "rest-power-shapes": _table(["宣言の入力の形", "型の数", "型"], [[f"`{k}`", len(v), [f"`{x}`" for x in v]] for k, v in spec["power_shapes"].items()])
                            + ["", "宣言のコマンドで使えない宣言する特殊能力の型（決定・ワザといっしょに使う）: "
                               + "・".join(f"`{x}`" for x in spec["power_not_by_command_bases"] + spec["power_not_by_command"])],
        "rest-stadium-shapes": _table(["宣言の入力の形", "型"], [[f"`{k}`", [f"`{x}`" for x in v]] for k, v in spec["stadium_shapes"].items()]),
        "rest-inputs": _table(["必要な入力", "既存の形", "変更"], [[r["need"], r["existing"], r["change"]] for r in spec["input_reuse"]])
                      + [""] + [f"- {r}" for r in spec["input_rules"]],
        "rest-gui": [f"- GUI のコミット: `{spec['gui_ref']['commit']}`（{spec['gui_ref']['repository']} の `{spec['gui_ref']['branch']}`）",
                     f"- その GUI が固定するエンジン: `{spec['gui_ref']['pinned_engine']}`（版 {spec['gui_ref']['pinned_engine_version']}）",
                     f"- GUI の main: `{spec['gui_ref']['main_commit']}`（固定するエンジン `{spec['gui_ref']['main_pinned_engine']}`）",
                     f"- 確かめ方: {spec['gui_ref']['checked']}", f"- 限界: {spec['gui_ref']['limit']}", ""]
                    + _table(["項目", "GUI（3649946）", "U7-5", "共通"], [[g["item"], g["gui"], g["u7_5"], g["same"]] for g in spec["gui_inputs"]]),
        "rest-axes": _table(["コマンド", "候補として表示", "入力を公開", "エンジンへ送信", "受理のあとに停止しうる"],
                           [[f"`{x['command']}`", x["display"], x["input_disclosure"], x["submit"], x["after"]] for x in spec["axes"]]),
        "rest-completion": _table(["ID", "基準"], [[c["id"], c["criterion"]] for c in spec["completion"]])
                          + [""] + _table(["判断事項", "今回決める部分", "保留できる部分"], [[f"`{d['id']}`", d["now"], d["later"]] for d in spec["decision_scope"]]),
        "rest-findings": _table(["ID", "種類", "状態", "内容", "再現・根拠", "参照", "影響範囲"],
                               [[f["id"], f["kind"], f"`{f['status']}`", f["summary"], [f["evidence"], *(f"履歴: {h}" for h in f.get("history", ()))], [_src(r) for r in f["refs"]],
                                 f["impact"]] for f in spec["findings"]]),
        "rest-adoption-needed": _table(["ID", "問い", "推奨"], [[f"`{d['id']}`", d["question"], d["recommendation"]] for d in spec["adoption_needed"]]),
        "rest-units": _table(["単位", "状態", "名前", "コマンド", "依存", "変更範囲", "完了の基準", "GUI への引き継ぎ", "残る事項"],
                            [[f"`{u['id']}`" + ("（最初）" if u["first"] else ""), f"`{u.get('status', 'planned')}`" + (f"（{u['implemented_in']}）" if u.get("implemented_in") else ""),
                              u["name"], [f"`{c}`" for c in u["commands"]] or "なし", u["depends"], u["changes"], u["done"], u["gui"], u["open"] or "なし"] for u in spec["units"]]),
        "rest-record": _record_lines(spec["adoption_record"]),
        "rest-first": [f"- {b}" for b in next(u for u in spec["units"] if u["first"])["basis"]]
                     + ["- 代表の盤面: " + "、".join(next(u for u in spec["units"] if u["first"])["boards"])],
        "rest-verify": _table(["確かめ", "意味"], [[f"`{v['id']}`", v["what"]] for v in spec["verify"]])
                      + [""] + _table(["単位"] + [v["id"] for v in spec["verify"]],
                                      [[f"`{u['id']}`"] + [next((spec["test_kinds"][t[1]] for t in u["tests"] if t[0] == v["id"]), "") for v in spec["verify"]] for u in spec["units"]])
                      + ["", "テストの種類: " + "・".join(f"`{k}` = {v}" for k, v in spec["test_kinds"].items())],
        "rest-command-index": [f"- `{name}`: " + "・".join(c["id"] for c in spec["checks"] if c["command"] == name) for name in by_command],
    }


def _record_lines(r: dict) -> list[str]:
    return ([f"- `{r['id']}`（{r['date']}・{r['by']}）: {r['scope']}", "  - 進め方:"] + [f"    {i}. {x}" for i, x in enumerate(r["order"], 1)]
            + ["  - 採用した判断:"] + [f"    - `{d['id']}`: {d['decision']}" for d in r["adopted"]]
            + ["  - 実装した単位: " + "、".join(f"`{u}`" for u in r["implemented_units"]), "  - 仕様の訂正:"]
            + [f"    - `{c['id']}`（{c['subject']}）: {c['text']}" for c in r["corrections"]])


DESIGN_BLOCKS = ("rest-adoption", "rest-record", "rest-sources", "rest-commands", "rest-fields", "rest-stops", "rest-residual", "rest-checks", "rest-command-index", "rest-scan", "rest-power-shapes",
                 "rest-stadium-shapes", "rest-inputs", "rest-gui", "rest-axes", "rest-completion", "rest-findings", "rest-adoption-needed")
PLAN_BLOCKS = ("rest-record", "rest-units", "rest-first", "rest-verify")


def text_problems(label: str, text: str) -> list[str]:
    """生成した文書の本文に、実装上の判断の一覧（docs/implementation-assumptions.json）の抽出が拾う語を入れない（この仕様は新しい判断を記録しない）。"""
    return [f"{label}: 抽出の語「{k}」を含む" for k in _SCAN.KEYWORDS if k in text]


def check(written: dict, design: str, plan: str) -> list[str]:
    spec = build()
    problems = []
    if written != spec:
        problems.append("書いた JSON が、作り直した仕様と違う（--write で作り直す）")
    rendered = blocks(spec)
    for label, text, names in (("設計の文書", design, DESIGN_BLOCKS), ("実装計画の文書", plan, PLAN_BLOCKS)):
        new, block_problems = render_into(text, rendered, names)
        problems += [f"{label}: {p}" for p in block_problems]
        if new != text:
            problems.append(f"{label}の生成区画が、作り直したものと違う（--write で作り直す）")
        problems += text_problems(label, text)
    return problems + spec_problems(written) + code_problems(written)


def main() -> int:
    parser = argparse.ArgumentParser()
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--write", action="store_true")
    group.add_argument("--check", action="store_true")
    args = parser.parse_args()
    spec = build()
    if args.write:
        problems = spec_problems(spec) + code_problems(spec)
        if problems:
            print("\n".join(problems))
            return 1
        OUTPUT.write_text(dump(spec), encoding="utf-8", newline="\n")
        rendered = blocks(spec)
        for path, names in ((DESIGN, DESIGN_BLOCKS), (PLAN, PLAN_BLOCKS)):
            text, block_problems = render_into(path.read_text(encoding="utf-8"), rendered, names)
            if block_problems:
                print("\n".join(f"{path.name}: {p}" for p in block_problems))
                return 1
            path.write_text(text, encoding="utf-8", newline="\n")
        print("書いた")
        return 0
    if not OUTPUT.exists():
        print("仕様の JSON がない（--write で作る）")
        return 1
    problems = check(json.loads(OUTPUT.read_text(encoding="utf-8")), DESIGN.read_text(encoding="utf-8"), PLAN.read_text(encoding="utf-8"))
    print("\n".join(problems) if problems else "problems=0")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())

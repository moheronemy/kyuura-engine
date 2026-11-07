"""合法手 API（U7。操作候補・必要な入力・処理可能性）の仕様案 docs/legal-actions-api-design.json を作る・確かめる（仕様と実装計画だけ。実装しない）。

    python scripts/build_legal_actions_api_design.py --write   # JSON と、設計・実装計画の文書の生成区画（表）を、このスクリプトの SPEC から書き直す
    python scripts/build_legal_actions_api_design.py --check   # JSON・生成区画が作り直したものと同じか、コマンドの型・段階・次の操作の種類・決定の選べるものの意味の
                                                               # すべてに対応があるか（コードと名前で照らす）、契約の原則に反する値がないか

- 仕様の唯一の元は、このスクリプトの ``SPEC``。JSON と文書の表はここから作る（二重に手で書かない）。生成区画の外（本文）は手で書く
- 表の書き出しと生成区画の置きかえは、状態スナップショットの仕様案の生成器（scripts/build_state_snapshot_design.py）の関数をそのまま使う
- 利用者が採用したのは原則（ADOPT-U7-PRINCIPLES）だけ。契約の細部は採用していない（``approval`` は ``not_approved``。判断事項はどれも ``pending``）
"""

from __future__ import annotations

import argparse
import dataclasses
import importlib.util
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
OUTPUT = ROOT / "docs" / "legal-actions-api-design.json"
DESIGN = ROOT / "docs" / "legal-actions-api-design.md"
PLAN = ROOT / "docs" / "legal-actions-api-implementation-plan.md"
U7_1 = ROOT / "docs" / "legal-actions-u7-1.md"
U7_2 = ROOT / "docs" / "legal-actions-u7-2.md"
AUDIT_DOC = ROOT / "docs" / "legal-actions-decision-audit.md"
_sites_spec = importlib.util.spec_from_file_location("legal_actions_decision_sites", ROOT / "scripts" / "legal_actions_decision_sites.py")
SITES = importlib.util.module_from_spec(_sites_spec)
_sites_spec.loader.exec_module(SITES)

_helpers_spec = importlib.util.spec_from_file_location("build_state_snapshot_design", ROOT / "scripts" / "build_state_snapshot_design.py")
_H = importlib.util.module_from_spec(_helpers_spec)
_helpers_spec.loader.exec_module(_H)
_cell, _table, render_into, dump = _H._cell, _H._table, _H.render_into, _H.dump

ADOPTION = {
    "id": "ADOPT-U7-PRINCIPLES", "date": "2026-11-07", "by": "利用者",
    "scope": "U7 で、操作候補（本人が知る情報から提示できる操作）・必要な入力（対象・枚数などの段階的な選択）・処理可能性（今の規約集合と実装で扱える範囲）を区別すること。"
             "候補に載ることと、そのあとの全分岐が完走することは別の保証。実際の秘密の状態にコマンドを試し、通るものだけを一覧にする設計は採らない。最終の判定は apply_command に残す",
}

ADOPTION_U7_1 = {
    "id": "ADOPT-U7-1", "date": "2026-11-07", "by": "利用者",
    "scope": "U7-1（決定への回答と番を終える）の最小の実装と、次の方針だけ。識別の方式の保留の判断（D-PROVENANCE ほか 7 件）・U7-2 以後の操作の種類の仕様・D-U7-DISPLAY・"
             "D-U7-COMPLETENESS の承認ではない。実装: v0.160（docs/legal-actions-u7-1.md）",
    "policies": [
        "候補の取得と実行を、信頼されたホストの境界で扱う",
        "操作主体のある操作と、対戦全体のホストの操作を区別する",
        "候補はホストが管理する不透明な取っ手に対応づける",
        "受理した操作で、その対戦の既存の取っ手を失効させる",
        "取っ手の生成にエンジンの乱数を使わない",
        "ホストの再起動・状態の復元・状態の差し替えで取っ手を失効させる",
        "拒否した操作だけでは、ほかの主体の取っ手を失効させない",
        "必要な入力は段階的に取得し、組み合わせを全展開しない",
        "未裁定・未実装を候補から黙って消さず、ゲーム上の禁止と区別する",
        "unverified は保証がないことを明示し、送信を許可する。最終の判定は既存のエンジンに任せる",
        "対応する操作の種類と、その範囲の完全性を明示する",
    ],
    "decisions": ["D-U7-API", "D-U7-TOKEN", "D-U7-REFINE", "D-U7-UNVERIFIED", "D-U7-HOST-OPS"],
    "units": ["U7-1"],
}

# 決定の選べるものの情報境界（v0.160 の補完。docs/legal-actions-u7-1.md 2 章。コードを読んだ判断）。決定を出す箇所の options の式を種類ごとに調べた。
# confirmed の一覧は kyuura_engine/legal_actions.DISCLOSURE_CONFIRMED_KINDS と同じ（--check が照らす）。ここにない種類・unconfirmed は、U7 で入力を返さない
_PUBLIC_VALUES = "選べるものの式が公開の値だけから決まる（場のポケモンの番号・公開の枚数の範囲・決まった語彙・(1,) などの決まった値）"
_OWN_CARDS = "選べるものの式が本人の手札・トラッシュ・場のスタジアムだけ（どれも本人に見えるカード）"
_AUDITED = ("v0.162 の監査で、生成箇所ごとに選べるもの・選ぶと止める選択・選ぶ数の式の情報源をたどった（docs/legal-actions-decision-audit.md。"
            "公開の値・本人のカード・始まった検索・持ち主の知識の関数だけ）")
DISCLOSURE = {
    **{k: ("confirmed", _PUBLIC_VALUES) for k in (
        "accept_request", "allocate_damage", "damage_option", "damage_step_order", "entry_power", "esp_redo", "evolution_heal", "heal_allocation", "janken_hand",
        "optional_coin", "optional_discard_all", "optional_drain", "optional_heal", "optional_shuffle", "peek_card", "prize_first", "promote_active", "quiz_answer",
        "quiz_attack", "quiz_height_answer", "reaction_order", "remove_counters", "select_counter_count", "select_devolve_count", "select_hand_card",
        "select_opponent_attack", "select_prize_card", "stadium_return_bench", "take_prize")},
    "knock_out_power": ("confirmed", "選べるものはきぜつするポケモンの番号 1 つ（resolution.codec.ko_check_decision の (pokemon_id,)）"),
    "reaction_power": ("confirmed", "選べるものは反応するポケモンの番号 1 つ（reactions.py の (pid,)）"),
    "select_look_count": ("confirmed", "山札の枚数（公開）までの範囲（effects の _count_options・programs の range(min(max_cards, len(deck)) + 1)）"),
    "select_draw_count": ("confirmed", "山札の枚数（公開）までの範囲（effects の _options・range(min(max_draw, len(deck)) + 1)）"),
    **{k: ("confirmed", _OWN_CARDS) for k in ("deck_top_from_hand", "discard_from_hand", "discard_stadium", "discard_to_deck_top", "hand_to_active", "hand_to_deck",
                                                "swap_with_prize")},
    "energy_drain_discard": ("confirmed", ("ダメージを与えたポケモン（場）についているエネルギーカード（resolution.kernel.drain_energy_from_damage_source の tuple(source.energy)）。"
                                          "決めるのは［だつりょくえき］の持ち主（相手の番の決定）。選ぶと止めるカードは energy_discard_problem（カードの定義と場の状態）")),
    "exp_all_energy": ("confirmed", ("きぜつするバトル場のポケモン（場）についている基本エネルギーとレインボーエネルギー（resolution.kernel.exp_all_options）。"
                                    "決めるのは学習装置の持ち主（相手の番の決定）。選ぶと止めるカードは exp_all_unresolved（場の状態）")),
    "magma_pool_energy": ("confirmed", ("［やけのこり］の持ち主の場のポケモン（holder）についているエネルギーカード（effects.magma_candidates の holder.energy）。"
                                       "決めるのは持ち主。選ぶと止めるカードはカードの定義と場の色の効果")),
    **{k: ("confirmed", _AUDITED) for k in (
        "attach_from_discard", "attach_from_hand", "bench_from_discard", "discard_energy", "discard_opponent_energy", "discard_to_deck", "move_energy",
        "move_opponent_energy", "post_knockout_power", "quiz_card", "recover_energy", "recover_pokemon", "recover_trainer", "retrieve_energy", "return_energy",
        "return_to_deck", "secret_plan_card", "select_attached_special_energy", "select_attached_trainer", "select_evolution_card", "stadium_from_discard",
        "use_discard_trainer", "attach_to_bench", "bench_guard", "damage_reduction", "evolution_song_pokemon", "forced_switch", "revive_source", "select_attack",
        "select_color", "select_deck_owner", "select_hand_positions", "select_marker_count", "select_opponent_prize", "select_pokemon", "select_special_condition",
        "ko_prevention", "ninja_trick", "reaction_switch")},
}
DISCLOSURE_BY_CONTRACT = "始まった検索・見たカード（DECK_REVEALING_KINDS・LOOKED_HAND_KINDS。決定は効果が見たあとに出る。契約の例外として実際のカードを示す）"

# 答えの並びの意味（確かめた分類だけ。legal_actions.ORDER_SIGNIFICANT_KINDS と同じ）
ORDER = {
    "arrange_deck_top": ("significant", "答えの並びが山札の上の新しい並び（effects・programs のどの出し方も deck[:count] = list(choices)）"),
    # v0.162: 回答の適用まで読んだ分類（docs/legal-actions-decision-audit.md 3 章）
    "bench_guard": ("significant", "かわりに受けるサイドンを答えの並びのまま処理する（kernel.bench_guard_answer の tuple(guard)。ログ・ダメージの順）"),
    "discard_energy": ("significant", "ワザの DiscardOwnEnergy._discard が答えの並びのままトラッシュに置く（トラッシュとログの順）。ほかの出し方は場の並びに直す"),
    "move_energy": ("significant", "バブルジャンプ（BubbleJump._move）が答えの並びのままつけ替える（ついている順・ログ）。ほかの出し方は決定の選べるものの並びに直す"),
    "recover_energy": ("significant", "ワザの RecoverEnergy が答えの並びのまま手札に加える（zones.return_discard_to_hand。手札の順・ログ）。コインの出し方はトラッシュの並びに直す"),
    "return_energy": ("significant", "ワザの ReturnOwnEnergyToHand._discard が答えの並びのまま手札にもどす（手札の順・ログ）。トレーナーの出し方はついている並びに直す"),
    "select_pokemon": ("significant", "ChosenBenchDamages が答えの並びのままダメージを与える（ダメージ・きぜつ・ログの順）。ほかの複数選択の出し方は場・決まった並びに直す"),
    "attach_from_discard": ("not_significant", "トラッシュの並びの順につける（AttachFromDiscard。ほかの出し方は 1 枚）"),
    "attach_from_hand": ("not_significant", "手札の並びの順につける（AttachFromHand・AttachFromHandToChosen）"),
    "discard_opponent_energy": ("not_significant", "ついている並びの順にトラッシュする（zones._attached_energy_cards・target.energy の並び）"),
    "discard_to_deck": ("not_significant", "トラッシュの並びの順に山札にもどす（zones.return_discard_to_deck・TakeFromDiscardTrainer・EachPlayerRecoversFromDiscard）"),
    "recover_pokemon": ("not_significant", "トラッシュの並びの順に手札に加える（RecoverPokemonFromDiscardOnEntry・EachPlayerRecoversFromDiscard。ほかは 1 枚）"),
    "recover_trainer": ("not_significant", "トラッシュの並びの順に手札に加える（TakeFromDiscardTrainer。ほかの出し方は 1 枚）"),
    "retrieve_energy": ("not_significant", "トラッシュの並びの順に手札に加える（DiscardFromHandThenRetrieveEnergy。スタジアムは 1 枚）"),
    "select_hand_positions": ("not_significant", "位置を小さい順に直して山札にもどす（zones.hand_positions_to_deck の sorted）"),
}

ADOPTION_U7_2 = {
    "id": "ADOPT-U7-2", "date": "2026-11-07", "by": "利用者",
    "scope": "U7-2（準備の操作とホストの操作。初期配置・切り直しの補償の引く枚数・ジャンケンの結果・延長戦の開始）の実装だけ。既存のコマンドの意味・ジャンケンの方式・先攻の"
             "決め方・補償の数と時点・続行規約・停止の扱いは変えない。U7-3 以後の操作の種類・識別の方式の移行・GUI・AI の承認ではない。実装: v0.163（docs/legal-actions-u7-2.md）",
    "policies": [
        "プレイヤーが行う操作（本人の初期配置・本人の補償の引く枚数）と、対戦全体のホストの操作（ジャンケンの結果・延長戦の開始）を分ける",
        "ホストの操作の入口は信頼されたアプリケーションだけが持ち、プレイヤーの入口から移れない。入口の所有と権限の確かめはホストするアプリケーションの責任",
        "U7-1 の取っ手・結果・coverage の契約を使う（ホストの取っ手とプレイヤーの取っ手を取り違えない）",
        "化石・人形の未裁定・規約による拒否を、候補から消さずゲーム上の禁止と区別する",
    ],
    "decisions": [],
    "units": ["U7-2"],
}

PRINCIPLES = [
    {"id": "P-ACTOR", "kind": "adopted", "text": "ホストが認証した操作主体（本人）にだけ、その時点の操作候補と必要な入力を返す。プレイヤーの番号を送るだけで、他人の候補・秘密の選択肢を取れない"},
    {"id": "P-NOT-NEXT", "kind": "adopted", "text": "U2 の next（次の操作の種類の手がかり）を合法手の一覧へ読み替えない。U7 は新しい契約"},
    {"id": "P-FINAL", "kind": "adopted", "text": "実行の最終の判定は apply_command。候補を取ったことは、あとの操作が受理される保証ではない"},
    {"id": "P-NO-TRIAL", "kind": "adopted", "text": "実際の秘密の状態にコマンドを試し、通るものだけを一覧にしない（候補の作成は apply_command・先読みを呼ばない）"},
    {"id": "P-SEPARATE", "kind": "adopted", "text": "候補に載ること・必要な入力・処理可能性を別の項目にする。候補に載ることは、そのあとの全分岐が完走する保証ではない"},
    {"id": "P-STAGED", "kind": "adopted", "text": "大量の組み合わせを全展開しない。段階的な入力（ワザ → 対象、トレーナー → 枚数とカード）で表す"},
    {"id": "P-NO-SIDE-EFFECT", "kind": "adopted", "text": "候補の取得で、ゲーム上の決定を作らない。状態・乱数・ログを変えない"},
    {"id": "P-TWIN", "kind": "adopted", "text": "同じ本人の知識と公開の情報を持つ双子の状態では、候補の一覧・理由・入力の制約から秘密の配分を区別できない（正当に始まった山札の検索の選択肢だけは実際の山札による）"},
    {"id": "P-NOT-HIDDEN", "kind": "adopted", "text": "エンジンの未対応を、候補から黙って消してゲームの禁止に見せない（処理可能性で表す）"},
    {"id": "P-COMPLETENESS", "kind": "adopted", "text": "上限を超えたとき、一部だけを返して完全な一覧と称さない。完全な列挙・部分的な候補・判定未確定を区別する。初版で保証できない完全性は保証しないと書く"},
    {"id": "P-NO-MODE-BRANCH", "kind": "adopted", "text": "3 つの規約集合の違いは、状態の規約集合の登録（続行規約の参照）から受け取る。モードの名前・カードの ID の分岐を engine.py・resolution/ に加えない"},
    {"id": "P-NO-VERIFIER-DATA", "kind": "adopted", "text": "検証者用の記録・スナップショット・確認値を、通常の API の応答に使わない"},
    {"id": "P-REVISION", "kind": "adopted", "text": "完全な状態のハッシュ・乱数の確認値を、公開の更新番号に使わない。ホストが管理する、秘密の状態を推測できない対応を使う"},
]

# 状態の区分（diagnostics.status_of）と段階（state.Phase）ごとの候補。--check がコードの Phase の値と照らす
PHASES = [
    {"phase": "setup_placement", "status": "in_progress", "actors": "両方のプレイヤー（まだ置いていない人）", "candidates": ["place_starting"], "complete_v1": True},
    {"phase": "setup_mulligan_draw", "status": "in_progress", "actors": "引く枚数の残るプレイヤー", "candidates": ["mulligan_draw"], "complete_v1": True},
    {"phase": "setup_first_player", "status": "in_progress", "actors": "ホスト（ジャンケンはエンジンの外の出来事）", "candidates": ["report_janken"], "complete_v1": True},
    {"phase": "main", "status": "in_progress", "actors": "番のプレイヤー", "candidates": ["end_turn", "play_basic", "attach_energy", "evolve", "retreat", "use_attack", "play_trainer",
                                                                    "use_power", "use_stadium", "remove_disguise", "discard_from_play", "reveal_face_down", "check_face_up_deck"],
     "complete_v1": False},
    {"phase": "take_prize", "status": "awaiting_decision", "actors": "決定のプレイヤー", "candidates": ["take_prize"], "complete_v1": True},
    {"phase": "promote_active", "status": "awaiting_decision", "actors": "決定のプレイヤー", "candidates": ["promote_active"], "complete_v1": True},
    {"phase": "decision", "status": "awaiting_decision", "actors": "決定のプレイヤー", "candidates": ["answer_decision"], "complete_v1": True},
    {"phase": "sudden_death", "status": "sudden_death_pending", "actors": "ホスト（対戦の進行の操作。どちらかのプレイヤーの選択ではない）", "candidates": ["start_sudden_death"],
     "complete_v1": True},
    {"phase": "game_over", "status": "game_over", "actors": "なし", "candidates": [], "complete_v1": True},
    {"phase": "halted", "status": "halted", "actors": "なし（再開する API はない）", "candidates": [], "complete_v1": True},
]

# 操作の種類。command はコマンドの型（--check が commands.py の dataclass と照らす）。inputs は段の並び
OPERATIONS = [
    {"kind": "place_starting", "command": "PlaceStartingPokemon", "actor": "player", "inputs": ["choose_cards:active(1)", "choose_cards:bench(0..5)"], "unit": "U7-2"},
    {"kind": "mulligan_draw", "command": "DrawMulliganCards", "actor": "player", "inputs": ["choose_count"], "unit": "U7-2"},
    {"kind": "report_janken", "command": "ReportJankenResult", "actor": "host", "inputs": ["choose_player"], "unit": "U7-2"},
    {"kind": "play_basic", "command": "PlayBasicToBench", "actor": "player", "inputs": [], "unit": "U7-3"},
    {"kind": "attach_energy", "command": "AttachEnergy", "actor": "player", "inputs": ["choose_pokemon"], "unit": "U7-3"},
    {"kind": "retreat", "command": "Retreat", "actor": "player", "inputs": ["choose_pokemon:new_active", "choose_energies:cost"], "unit": "U7-3"},
    {"kind": "evolve", "command": "EvolvePokemon", "actor": "player", "inputs": ["choose_pokemon"], "unit": "U7-3"},
    {"kind": "end_turn", "command": "EndTurn", "actor": "player", "inputs": [], "unit": "U7-1"},
    {"kind": "use_attack", "command": "UseAttack", "actor": "player", "inputs": ["choose_attack", "options:attack_modifiers（stadium_coin・attack_power・with_power(s)）", "after_acceptance:decision"],
     "unit": "U7-4"},
    {"kind": "take_prize", "command": "TakePrize", "actor": "player", "inputs": ["choose_option:position"], "unit": "U7-1"},
    {"kind": "promote_active", "command": "PromoteActive", "actor": "player", "inputs": ["choose_option:pokemon"], "unit": "U7-1"},
    {"kind": "answer_decision", "command": "ResolveDecision", "actor": "player", "inputs": ["choose_option:decision（observe の decision をそのまま使う）"], "unit": "U7-1"},
    {"kind": "play_trainer", "command": "PlayTrainer", "actor": "player", "inputs": ["after_acceptance:decision（枚数・カードは使ったあとの決定）"], "unit": "U7-5"},
    {"kind": "use_power", "command": "UsePokemonPower", "actor": "player", "inputs": ["choose_power", "registered:power_inputs（energy・source・target・card。カードの登録が決める）"],
     "unit": "U7-5"},
    {"kind": "use_stadium", "command": "UseStadium", "actor": "player", "inputs": ["registered:stadium_inputs（energy）"], "unit": "U7-5"},
    {"kind": "remove_disguise", "command": "RemoveDisguise", "actor": "player", "inputs": ["choose_pokemon"], "unit": "U7-5"},
    {"kind": "discard_from_play", "command": "DiscardFromPlay", "actor": "player", "inputs": ["choose_pokemon"], "unit": "U7-5"},
    {"kind": "reveal_face_down", "command": "RevealFaceDown", "actor": "player", "inputs": ["choose_pokemon"], "unit": "U7-5"},
    {"kind": "check_face_up_deck", "command": "CheckFaceUpDeckCard", "actor": "player", "inputs": ["choose_option:face_up_position（公開のおもての山札のカード）"], "unit": "U7-5"},
    {"kind": "start_sudden_death", "command": "StartSuddenDeath", "actor": "host", "inputs": [], "unit": "U7-2"},
]

# next（U2）との対応。next は手がかりのまま、U7 の候補の種類の上位の分類として使える
NEXT_MAP = {
    "place_starting_pokemon": ["place_starting"], "draw_mulligan_cards": ["mulligan_draw"], "report_janken_result": ["report_janken"],
    "turn_action": ["end_turn", "play_basic", "attach_energy", "evolve", "retreat", "use_attack", "play_trainer", "use_power", "use_stadium", "remove_disguise",
                    "discard_from_play", "reveal_face_down", "check_face_up_deck"],
    "answer_decision": ["answer_decision", "take_prize", "promote_active"], "start_sudden_death": ["start_sudden_death"],
}

INPUT_KINDS = [
    {"id": "choose_option", "meaning": "今の決定の選べるもの（observe(state, actor) の decision.options の value）から min_choices〜max_choices 個", "constraint": "個数・重複なし",
     "source": "既存の決定（再利用）"},
    {"id": "choose_cards", "meaning": "本人に見えるカード（observe の card。uid）から選ぶ", "constraint": "個数・条件（たねポケモンなど。カードの定義と公開の状態だけで決まるもの）", "source": "本人の知識"},
    {"id": "choose_pokemon", "meaning": "場のポケモンの番号（公開）から選ぶ", "constraint": "個数・条件", "source": "公開"},
    {"id": "choose_energies", "meaning": "ついているエネルギー（公開）から、費用を満たす組を選ぶ", "constraint": "費用（数・色）の条件で表し、組を全展開しない", "source": "公開"},
    {"id": "choose_attack", "meaning": "ワザの位置（印刷・今の姿のワザ。公開）", "constraint": "1 つ", "source": "公開"},
    {"id": "choose_power", "meaning": "ポケモンパワーの位置（公開）", "constraint": "1 つ", "source": "公開"},
    {"id": "choose_count", "meaning": "数（0〜上限。上限は公開の枚数から）", "constraint": "範囲", "source": "公開"},
    {"id": "choose_player", "meaning": "プレイヤー（0・1）", "constraint": "1 つ", "source": "ホストの入力"},
    {"id": "options", "meaning": "操作の任意の指定（ワザの宣言のスタジアムのコイン・パワーを使う宣言など）", "constraint": "真偽・指定の組", "source": "公開"},
    {"id": "registered", "meaning": "カードの登録（effects の登録表）が宣言する入力。共通の処理はカードの ID で分岐しない", "constraint": "登録が宣言する種類（上の語彙のどれか）",
     "source": "カードの登録"},
    {"id": "after_acceptance", "meaning": "受理したあとに、エンジンが決定として尋ねる入力（候補の取得では決定を作らない）", "constraint": "そのときの決定（choose_option）",
     "source": "受理のあとの決定"},
    {"id": "decline", "meaning": "任意の辞退（min_choices が 0 の決定・「てよい」の効果）", "constraint": "選ばないことを明示する（空の選択とは別の印にしない。既存の ResolveDecision の空の choices）",
     "source": "既存の決定"},
]

# observe の決定の選べるものの意味（observation.OPTION_MEANINGS の値）と入力の種類。--check がコードの語彙と照らす
OPTION_MEANING_MAP = {"card": "choose_option", "pokemon": "choose_option", "position": "choose_option", "number": "choose_option", "color": "choose_option",
                      "name": "choose_option", "janken": "choose_option", "peek_target": "choose_option", "value": "choose_option"}

PROCESSABILITY = [
    {"id": "supported", "meaning": "今の規約集合と実装で、宣言の前の確かめが扱える（そのあとの分岐の完走は保証しない）", "display": "表示", "executable": True,
     "derived_from": "本人の知識と公開の情報だけで決まる確かめ"},
    {"id": "may_stop_later", "meaning": "受理のあと、条件しだいで研究上の停止・エンジンの未対応で止まりうる（止まるかは秘密の情報・コイン・相手の選択による）", "display": "表示（止まりうる注意）",
     "executable": True, "derived_from": "カードの登録が宣言する停止の可能性（UNRESOLVED の場面の索引）。実際の配分を読まない"},
    {"id": "unresolved_ruling", "meaning": "記録で決まらない裁定のため、今の規約集合では処理できない（研究上の未解決）", "display": "表示（実行できない。ゲーム上の禁止ではない）",
     "executable": False, "derived_from": "診断のコード表の分類（未裁定）と、状態の規約集合の続行規約の参照"},
    {"id": "not_implemented", "meaning": "エンジンが未対応（研究上の未解決とは別）", "display": "表示（実行できない。ゲーム上の禁止ではない）", "executable": False,
     "derived_from": "診断のコード表の分類（未対応）"},
    {"id": "technical_limit", "meaning": "先読み・読み方の組などの上限を超える（MAX_BRANCHES・COLOR_READINGS_LIMIT など）", "display": "表示（実行できない理由として）", "executable": False,
     "derived_from": "上限が公開の情報だけで決まるときだけ。秘密の配分で決まる上限は unverified"},
    {"id": "unverified", "meaning": "候補の作成の時点で、本人の知識から処理可能性を決められない（判定未確定）", "display": "表示（送れば apply_command が判定する）", "executable": True,
     "derived_from": "上のどれにも決められないとき。拒否されても理由は双子で同じ（v0.135 以後の拒否の検査）"},
]

COMPLETENESS = [
    {"id": "complete", "meaning": "契約の範囲（その段階の候補の種類）で、本人に提示できる候補をすべて含む"},
    {"id": "partial", "meaning": "一部だけを含む（上限・初版の範囲の外）。理由のコードと、含めた種類を示す"},
    {"id": "undetermined", "meaning": "完全かどうかを決められない（判定未確定の候補を含むなど）"},
]

RESPONSE = [
    {"field": "kyuura_legal_actions_format", "meaning": "応答の形式の版（1 から）", "source": "固定"},
    {"field": "game", "meaning": "ホストが発行した対戦の取っ手（不透明な文字列。seed・記録の識別ではない）", "source": "ホスト"},
    {"field": "actor", "meaning": "ホストが認証した操作主体（0・1・host）", "source": "ホスト"},
    {"field": "revision", "meaning": "候補を作った状態との対応の取っ手（ホストが発行する不透明な値。状態のハッシュ・乱数の確認値・決定の通し番号ではない）", "source": "ホスト"},
    {"field": "status", "meaning": "状態の区分（diagnostics.status_of と同じ語彙）", "source": "公開"},
    {"field": "completeness", "meaning": "complete・partial・undetermined", "source": "契約"},
    {"field": "scope", "meaning": "含めた候補の種類（partial の理由のコードを含む）", "source": "契約"},
    {"field": "candidates", "meaning": "候補の並び（id・kind・source・inputs・processability・reasons）。並びは公開の値の順（カードは observe の並び、種類は OPERATIONS の順）", "source": "本人の知識と公開"},
]

CANDIDATE_FIELDS = [
    {"field": "id", "meaning": "応答の中だけの候補の番号（c1, c2, …。並びの順。秘密の値から作らない）"},
    {"field": "kind", "meaning": "操作の種類（OPERATIONS の kind）"},
    {"field": "source", "meaning": "操作に使うもの（本人に見えるカードの uid・場のポケモンの番号・ワザの位置。見えないカードの uid は入れない）"},
    {"field": "inputs", "meaning": "必要な入力の段（INPUT_KINDS。段ごとに種類・制約・選べるもの）。after_acceptance の段は受理のあとの決定で尋ねる"},
    {"field": "processability", "meaning": "PROCESSABILITY の 1 つ"},
    {"field": "reasons", "meaning": "理由のコード（決まった語彙。文は表示の側がコードから作る。実行時の例外の文・カードの位置を入れない）"},
]

INFO_BOUNDARY = [
    {"channel": "count", "rule": "候補の数・選べるものの数は、本人の知識と公開の情報だけで決まる"},
    {"channel": "order", "rule": "並びは公開の値の順（uid の順で山札の中身を伝えない）"},
    {"channel": "missing", "rule": "候補を落とすかは本人の知識だけで決まる。決められないものは落とさず unverified にする"},
    {"channel": "reason", "rule": "理由は決まった語彙のコード。双子で同じ"},
    {"channel": "identifier", "rule": "候補の番号は並びの順。見えないカードの uid・秘密の値から作った識別を入れない"},
    {"channel": "invalid_query", "rule": "不正な入力（知らない候補・見えないカード・範囲の外の数）を試す問い合わせも、決まったエラーで答え、秘密の情報で変わらない"},
    {"channel": "started_search", "rule": "正当に始まった山札の検索（DECK_REVEALING_KINDS の決定）の選択肢だけは、実際の山札による。始まっていない検索の候補に実際の山札を使わない"},
    {"channel": "other_viewers", "rule": "本人の候補を相手・観戦者に配らない（ホストの責任）"},
    {"channel": "verifier_data", "rule": "検証者用の記録・スナップショット・確認値を応答に使わない"},
]

KNOWLEDGE = [
    {"id": "public", "meaning": "全員に見える情報（観測の公開の項目）", "allowed": "いつも"},
    {"id": "actor_knowledge", "meaning": "本人が知る情報（自分の手札・デッキリスト・所有するカードの多重集合・見たカード）", "allowed": "いつも"},
    {"id": "started_search", "meaning": "正当に始まった検索で本人が見ているカード（決定の選べるもの）", "allowed": "その決定の入力だけ"},
    {"id": "secret", "meaning": "本人が知らない配分（山札・サイドの並び、相手の手札）", "allowed": "使わない"},
]

REVISION = {
    "source": "host_token",
    "forbidden_sources": ["state_hash", "rng_check", "decision_id", "log_length", "record_identity"],
    "design": "ホストが対戦・操作主体ごとに不透明な取っ手（乱数の 128 ビットの値）を発行し、ホストの中で（対戦, 操作主体, 状態の内部の版）と対応づける。受理した操作（どのプレイヤーの操作でも）"
              "で、その対戦の取っ手はすべて古くなる。拒否は状態を変えないので取っ手を変えない",
    "rejections": [
        {"case": "古い取っ手（状態が変わった）", "code": "CANDIDATES_STALE", "then": "候補を取り直す"},
        {"case": "別の対戦の取っ手", "code": "CANDIDATES_WRONG_GAME", "then": "その対戦の候補を取る"},
        {"case": "別の操作主体の取っ手", "code": "CANDIDATES_WRONG_ACTOR", "then": "自分の候補を取る（他人の候補の中身を答えない）"},
        {"case": "知らない候補・入力", "code": "CANDIDATE_UNKNOWN", "then": "候補を取り直す（理由は決まった文）"},
    ],
    "note": "取っ手を使わない直接のコマンドの送信（今の submit）は、そのまま使える。取っ手の確かめはホストの段で、エンジンに渡す前。受理するかの判定は apply_command",
}

HOST = [
    "操作主体の認証（ログイン・接続）と権限の確かめ。API はホストが確かめた操作主体を受け取り、要求に書かれたプレイヤーの番号を信じない",
    "応答を本人だけに渡す（相手・観戦者・記録に入れない）",
    "取っ手（game・revision）の発行・対応づけ・失効",
    "ホストの操作（ジャンケンの結果・延長戦の開始）は、ホストの操作主体だけに候補として出す",
]

LEAK_TESTS = [
    {"id": "T-TWIN-RESPONSE", "what": "持ち主の知識が同じで山札・サイドの配分だけが違う双子（twin_command_problems の owner_knowledge と同じ前提）で、各操作主体の応答（候補・数・並び・理由・入力の制約・"
     "completeness）が同じ"},
    {"id": "T-TWIN-REFINE", "what": "双子で、段階的な入力の問い合わせ（正しい入力・不正な入力）の答えが同じ"},
    {"id": "T-STARTED-SEARCH", "what": "山札の検索が始まったあとの決定の選択肢は実際の山札による（双子で違ってよい）。始まる前の候補は同じ"},
    {"id": "T-NO-SIDE-EFFECT", "what": "候補を何度取っても、状態・乱数・ログ・決定の通し番号が変わらない"},
    {"id": "T-OTHER-ACTOR", "what": "相手・観戦者として問い合わせても、本人の候補・選べるもの・数が出ない"},
    {"id": "T-STALE", "what": "古い・別の対戦・別の操作主体の取っ手を拒み、拒否の答えが秘密の情報で変わらない"},
    {"id": "T-NOT-HIDDEN", "what": "未裁定・未対応の操作は候補から消えず、processability で表される"},
    {"id": "T-NO-VERIFIER", "what": "応答に検証者用の値（確認値・seed・乱数・スナップショットの鍵）が入らない（閲覧用記録と同じ入ってはいけない項目の検査）"},
]

UNITS = [
    {"id": "U7-1", "status": "implemented", "name": "枠組みと決定への回答（最初の縦の単位）", "depends": [], "scope": ["応答の形式・取っ手（game・revision）・ホストの認証の境界・古い取っ手の拒否",
     "決定への回答（ResolveDecision・TakePrize・PromoteActive）を observe の decision から作る（complete）", "番を終える（EndTurn）", "番でない・終局・停止は空の候補（complete）"],
     "tests": ["T-TWIN-RESPONSE（決定）", "T-STARTED-SEARCH", "T-NO-SIDE-EFFECT", "T-OTHER-ACTOR", "T-STALE", "T-NO-VERIFIER", "候補どおりに送った回答を apply_command が受理する（既存の対戦の決定で）"],
     "done": "決定待ちのすべての種類（OPTION_MEANINGS の語彙）で候補ができ、漏れの回帰テストが通る。実装の識別の分類に legal_actions のファイルを加え、識別の設計の --check が通る"},
    {"id": "U7-2", "status": "implemented", "name": "準備とホストの操作", "depends": ["U7-1"], "scope": ["PlaceStartingPokemon（たねポケモンの手札から。段: バトル場 → ベンチ）", "DrawMulliganCards", "ReportJankenResult・StartSuddenDeath（ホストの操作主体だけ）"],
     "tests": ["T-TWIN-RESPONSE（準備）", "準備の候補から作った操作で、固定デッキの対戦が始まる"], "done": "準備の段階が complete"},
    {"id": "U7-3", "status": "planned", "name": "通常の操作（ワザ・トレーナー・パワーの外）", "depends": ["U7-2"], "scope": ["PlayBasicToBench・AttachEnergy・EvolvePokemon・Retreat（費用は条件で表す）"],
     "tests": ["T-TWIN-RESPONSE（通常の操作）", "T-NOT-HIDDEN"], "done": "これらの種類について、本人の知識だけで決まる確かめを候補の作成に使う。scope に含めた種類を示し、main は partial"},
    {"id": "U7-4", "status": "planned", "name": "ワザ", "depends": ["U7-3"], "scope": ["UseAttack（ワザ → 任意の指定。対象は受理のあとの決定）", "宣言の前の確かめのうち、本人の知識だけで決まるもの（v0.147〜v0.151 の持ち主の知識の関数）を processability に使う"],
     "tests": ["T-TWIN-RESPONSE（v0.147〜v0.151 の双子の盤面）", "T-TWIN-REFINE", "T-NOT-HIDDEN（未裁定のワザ）"], "done": "ワザの候補で、先読みを呼ばない。決められないものは unverified"},
    {"id": "U7-5", "status": "planned", "name": "トレーナー・パワー・スタジアムとその他", "depends": ["U7-4"], "scope": ["PlayTrainer・UsePokemonPower・UseStadium・RemoveDisguise・DiscardFromPlay・RevealFaceDown・CheckFaceUpDeckCard",
     "入力はカードの登録が宣言する（共通の処理にカード ID の分岐を加えない）"], "tests": ["T-TWIN-RESPONSE（トレーナー・パワー）", "登録のないカードは unverified（消さない）"],
     "done": "すべてのコマンドの型に候補の種類がある。main が complete と称せるかは D-U7-COMPLETENESS"},
    {"id": "U7-6", "status": "planned", "name": "GUI・ルールベースの AI への接続", "depends": ["U7-1"], "scope": ["API だけを使う方策（内部の状態・秘密の配分を読まない）", "GUI の表示（processability ごとの表示）",
     "既存の方策（tests/helpers の trainer_policy_command など）は内部の状態を読むので、公開の API に流用しない"],
     "tests": ["API だけを使う方策で固定デッキの対戦が終局・停止まで進む", "方策が受け取る値が応答だけであること"], "done": "決定・準備は U7-1・U7-2 のあとに接続できる。通常の操作は単位ごとに広げる"},
]

DECISIONS = [
    {"id": "D-U7-API", "question": "入口の形（HostedGame.legal_actions(actor) と、状態を受け取る関数 legal_actions(state, actor) を両方にするか）", "recommendation":
     "ホストの入口を正とし、状態を受け取る関数はホストの中とテストだけ（取っ手を持たない）", "status": "adopted", "adoption": "ADOPT-U7-1",
     "adopted": "ホストの入口（ActionHost）とクライアントの入口（ActorSession）を分ける。状態を受け取る公開の関数は作らない"},
    {"id": "D-U7-TOKEN", "question": "revision を乱数の不透明な値にするか、ホストの中の数（受理の数）を外に出すか", "recommendation": "不透明な値（受理の数は相手の見えない操作の数を伝えうる）",
     "status": "adopted", "adoption": "ADOPT-U7-1", "adopted": "secrets の乱数の不透明な値（エンジンの乱数・状態のハッシュ・決定の番号を使わない）"},
    {"id": "D-U7-REFINE", "question": "段階的な入力を、問い合わせ（refine）で次の段を取る形にするか、候補に全段の制約を書く形にするか", "recommendation":
     "初版は候補に段の制約を書く（ワザの対象・トレーナーの枚数は受理のあとの決定）。問い合わせは U7-4 で必要になったときに加える", "status": "adopted", "adoption": "ADOPT-U7-1",
     "adopted": "段階的に取得する（候補の一覧は段の種類だけ、選べるものと制約は inputs の問い合わせ）"},
    {"id": "D-U7-DISPLAY", "question": "処理可能性ごとの表示・実行の扱い（PROCESSABILITY の表）", "recommendation": "表のとおり。どれも候補から消さない", "status": "pending"},
    {"id": "D-U7-UNVERIFIED", "question": "判定未確定（unverified）の候補を実行できる候補にするか", "recommendation": "する（送れば apply_command が判定する。拒否の理由は双子で同じ）",
     "status": "adopted", "adoption": "ADOPT-U7-1", "adopted": "unverified は保証がないことを示して送信を許す"},
    {"id": "D-U7-COMPLETENESS", "question": "初版で main の候補を complete と称する範囲", "recommendation": "称さない（partial と scope）。決定・準備・延長戦の開始・終局・停止だけ complete",
     "status": "pending"},
    {"id": "D-U7-HOST-OPS", "question": "ジャンケンの結果・延長戦の開始をホストの操作主体の候補にするか", "recommendation": "する（プレイヤーの候補には出さない）", "status": "adopted", "adoption": "ADOPT-U7-1",
     "adopted": "操作主体のある操作とホストの操作を区別する（プレイヤーには waiting_for_host を返す）。ホストの操作の入口は U7-2"},
    {"id": "D-U7-DECISION-UID", "question": "決定の選べるもの（observe の decision.options の value）に、決める人に見えないカードの uid が入る種類があるか", "recommendation":
     "U7-1 の前に確かめる（未確認）。入るなら、U7 の応答では見えないカードを値の番号で表し、uid を入れない", "status": "checked",
     "result": "v0.160 の補完で種類ごとに options の式を調べ直した（docs/legal-actions-u7-1.md 2 章）。見えないカードの uid が入る種類は見つからない。情報境界を確かめた種類だけ入力を返し、"
               "確かめていない種類（unconfirmed）と、実行時に見えないカードが選べるものに来た場面は、選べるもの・数・並びを返さない（INPUT_BOUNDARY_UNCONFIRMED）。"
               "番号に置きかえるだけでは数・並びの漏れが消えないため"},
]

SPEC = {
    "id": "LEGAL-ACTIONS-API-DESIGN", "status": "proposed", "approval": "not_approved", "adoption": ADOPTION, "principles": PRINCIPLES, "phases": PHASES,
    "operations": OPERATIONS, "next_map": NEXT_MAP, "input_kinds": INPUT_KINDS, "option_meaning_map": OPTION_MEANING_MAP, "processability": PROCESSABILITY,
    "completeness": COMPLETENESS, "response": RESPONSE, "candidate_fields": CANDIDATE_FIELDS, "info_boundary": INFO_BOUNDARY, "knowledge": KNOWLEDGE,
    "revision": REVISION, "host": HOST, "leak_tests": LEAK_TESTS, "units": UNITS, "decisions": DECISIONS, "u7_1_adoption": ADOPTION_U7_1, "u7_2_adoption": ADOPTION_U7_2,
    "disclosure": {k: {"status": v[0], "basis": v[1]} for k, v in sorted(DISCLOSURE.items())}, "disclosure_by_contract": DISCLOSURE_BY_CONTRACT,
    "order": {k: {"status": v[0], "basis": v[1]} for k, v in sorted(ORDER.items())},
    "audit_categories": {
        "public": "公開の値（場のポケモン・ついているカード・トラッシュ・公開の枚数・決まった語彙）",
        "own_cards": "本人の手札と本人に見えるカード（決める人が持ち主）",
        "started_search": "正当に始まった検索・閲覧で本人が見ているカード（契約の例外）",
        "owner_knowledge": "選べるものは公開・本人のカード。選ぶと止める選択は持ち主の知識だけで決まる関数（searchable_deck_cards・deck_target_lower_bound など）",
        "inherits": "退避した決定を同じ種類・選べるもので戻す（元の出し方の情報源を引き継ぐ）",
    },
    "audit_orders": {"single": "選ぶ数が 1 以下", "significant": "答えの並びが結果（ゾーンの並び・ログ・解決の順）に入る", "not_significant": "適用の前に決まった並びに直す",
                     "unconfirmed": "確かめていない（v0.162 の対象の 39 種類の外）"},
}


def decision_sites() -> list[dict]:
    """走査した出し方（コード）と監査の判定（SITES.AUDIT）を合わせた一覧（(種類, ファイル, クラス, 関数) ごと。同じ関数の出し方はまとめる）。"""
    rows = {}
    for site in SITES.scan(ROOT):
        key = (site["kind"], site["file"], site["class"], site["func"])
        row = rows.setdefault(key, {"kind": key[0], "file": key[1], "class": key[2], "func": key[3], "player": site["player"], "options": [], "max": []})
        if site["options"] and site["options"] not in row["options"]:
            row["options"].append(site["options"])
        if site["max"] not in row["max"]:
            row["max"].append(site["max"])
        audit = SITES.AUDIT.get(key)
        row["category"], row["order"] = (audit if audit is not None else (None, None))
    return [rows[k] for k in sorted(rows, key=lambda k: (k[0], k[1], str(k[2]), str(k[3])))]


def build() -> dict:
    data = json.loads(json.dumps(SPEC, ensure_ascii=False))
    data["decision_sites"] = decision_sites()
    return data


def blocks(spec: dict) -> dict[str, list[str]]:
    a = spec["adoption"]
    return {
        "adoption": [f"- `{a['id']}`（{a['date']}・{a['by']}）: {a['scope']}", f"- 仕様案の状態: `{spec['status']}`・承認 `{spec['approval']}`"],
        "principles": [f"- `{p['id']}`（{'採用済み' if p['kind'] == 'adopted' else '推奨'}）: {p['text']}" for p in spec["principles"]],
        "phases": _table(["段階", "状態の区分", "操作主体", "候補の種類", "初版で complete"],
                         [[f"`{p['phase']}`", p["status"], p["actors"], [f"`{c}`" for c in p["candidates"]] or "なし", p["complete_v1"]] for p in spec["phases"]]),
        "operations": _table(["種類", "コマンド", "操作主体", "必要な入力の段", "単位"],
                             [[f"`{o['kind']}`", f"`{o['command']}`", o["actor"], o["inputs"] or "なし", o["unit"]] for o in spec["operations"]]),
        "next": _table(["next（U2）", "U7 の候補の種類"], [[f"`{k}`", [f"`{x}`" for x in v]] for k, v in spec["next_map"].items()]),
        "inputs": _table(["入力の種類", "意味", "制約", "情報の元"], [[f"`{i['id']}`", i["meaning"], i["constraint"], i["source"]] for i in spec["input_kinds"]]),
        "processability": _table(["区分", "意味", "表示", "実行の候補", "決め方"],
                                 [[f"`{p['id']}`", p["meaning"], p["display"], p["executable"], p["derived_from"]] for p in spec["processability"]]),
        "completeness": _table(["区分", "意味"], [[f"`{c['id']}`", c["meaning"]] for c in spec["completeness"]]),
        "response": _table(["項目", "意味", "元"], [[f"`{r['field']}`", r["meaning"], r["source"]] for r in spec["response"]]),
        "candidate": _table(["項目", "意味"], [[f"`{r['field']}`", r["meaning"]] for r in spec["candidate_fields"]]),
        "boundary": _table(["経路", "規則"], [[f"`{b['channel']}`", b["rule"]] for b in spec["info_boundary"]]),
        "knowledge": _table(["情報の元", "意味", "使ってよい"], [[f"`{k['id']}`", k["meaning"], k["allowed"]] for k in spec["knowledge"]]),
        "revision": [f"- 元: `{spec['revision']['source']}`（使わない元: " + "・".join(f"`{x}`" for x in spec["revision"]["forbidden_sources"]) + "）",
                     f"- 方式: {spec['revision']['design']}", f"- 注: {spec['revision']['note']}", ""]
                    + _table(["場合", "拒否のコード", "次"], [[r["case"], f"`{r['code']}`", r["then"]] for r in spec["revision"]["rejections"]]),
        "host": [f"- {h}" for h in spec["host"]],
        "leak-tests": _table(["ID", "確かめること"], [[f"`{t['id']}`", t["what"]] for t in spec["leak_tests"]]),
        "units": _table(["単位", "状態", "名前", "依存", "範囲", "回帰テスト", "完了の基準"],
                        [[f"`{u['id']}`", u["status"], u["name"], u["depends"] or "なし", u["scope"], u["tests"], u["done"]] for u in spec["units"]]),
        "decisions": _table(["ID", "問い", "推奨", "状態", "採用・確かめの結果"],
                            [[f"`{d['id']}`", d["question"], d["recommendation"], d["status"] + (f"（{d['adoption']}）" if d.get("adoption") else ""),
                              d.get("adopted") or d.get("result") or ""] for d in spec["decisions"]]),
        "setup-adoption": [f"- `{spec['u7_2_adoption']['id']}`（{spec['u7_2_adoption']['date']}・{spec['u7_2_adoption']['by']}）: {spec['u7_2_adoption']['scope']}",
                           "  - 方針:"] + [f"    - {x}" for x in spec["u7_2_adoption"]["policies"]]
                          + ["  - 判断事項: " + ("、".join(spec["u7_2_adoption"]["decisions"]) or "なし（新しく採用した判断事項はない）"),
                             "  - 実装単位: " + "、".join(spec["u7_2_adoption"]["units"])],
        "unit-adoption": [f"- `{spec['u7_1_adoption']['id']}`（{spec['u7_1_adoption']['date']}・{spec['u7_1_adoption']['by']}）: {spec['u7_1_adoption']['scope']}",
                          "  - 方針:"] + [f"    - {x}" for x in spec["u7_1_adoption"]["policies"]]
                         + ["  - 判断事項: " + "、".join(spec["u7_1_adoption"]["decisions"]), "  - 実装単位: " + "、".join(spec["u7_1_adoption"]["units"])],
        "decision-kinds": _decision_kind_rows(spec),
        "audit-categories": _table(["区分", "意味"], [[f"`{k}`", v] for k, v in spec["audit_categories"].items()])
                            + [""] + _table(["答えの並び", "意味"], [[f"`{k}`", v] for k, v in spec["audit_orders"].items()]),
        "audit-kinds": _audit_kind_rows(spec),
        "audit-sites": _table(["決定の種類", "出し方（ファイル・クラス.関数）", "決める人", "選べるものの式", "選ぶ数の上限", "情報源", "答えの並び"],
                              [[f"`{r['kind']}`", f"`{r['file'].removeprefix('kyuura_engine/')}` {r['class'] or ''}.{r['func']}", f"`{r['player']}`" if r["player"] else "",
                                [f"`{o}`" for o in r["options"]], [f"`{m}`" for m in r["max"]], r["category"], r["order"]] for r in spec["decision_sites"]]),
    }


def _audit_kind_rows(spec: dict) -> list[str]:
    """種類ごとの出し方の数（情報源の区分ごと）・情報境界・答えの並び（出し方の一覧から作る）。"""
    from collections import Counter

    by: dict[str, list[dict]] = {}
    for r in spec["decision_sites"]:
        by.setdefault(r["kind"], []).append(r)
    rows = []
    for kind in sorted(by):
        if kind == "restore":
            continue
        counts = Counter(r["category"] for r in by[kind])
        disclosure = spec["disclosure"].get(kind, {"status": "confirmed（契約の例外）"})["status"]
        order = spec["order"].get(kind, {"status": "unconfirmed" if any(r["order"] == "unconfirmed" for r in by[kind]) else "single"})["status"]
        rows.append([f"`{kind}`", len(by[kind]), "・".join(f"{c} {n}" for c, n in sorted(counts.items())), disclosure, order])
    return _table(["決定の種類", "出し方の数", "情報源の区分", "U7 の入力", "答えの並び"], rows)


def _decision_kind_rows(spec: dict) -> list[str]:
    """決定の種類ごとの情報の範囲と答えの並び（コードの語彙と DISCLOSURE・ORDER から作る）。"""
    from kyuura_engine import observation as O

    rows = []
    for kind, meaning in sorted(O.OPTION_MEANINGS.items()):
        if kind in O.DECK_REVEALING_KINDS or kind in O.LOOKED_HAND_KINDS:
            status, basis = "confirmed", spec["disclosure_by_contract"]
        else:
            item = spec["disclosure"].get(kind, {"status": "分類なし", "basis": ""})
            status, basis = item["status"], item["basis"]
        order = spec["order"].get(kind, {"status": "unconfirmed（選ぶ数が 1 以下なら not_applicable）"})["status"]
        others = "種類・決める人だけ" if kind in O.HIDDEN_COUNT_KINDS else "種類・決める人・選ぶ数・選べるものの数"
        rows.append([f"`{kind}`", meaning, status, basis, order, others])
    return _table(["決定の種類", "選べるものの意味", "U7 の入力の情報境界", "根拠", "答えの並び", "相手・観戦者に見えるもの（観測）"], rows)


DESIGN_BLOCKS = ("adoption", "principles", "phases", "operations", "next", "inputs", "processability", "completeness", "response", "candidate", "boundary", "knowledge",
                 "revision", "host", "leak-tests", "decisions")
PLAN_BLOCKS = ("units",)
U7_1_BLOCKS = ("unit-adoption", "decision-kinds")
U7_2_BLOCKS = ("setup-adoption",)
AUDIT_BLOCKS = ("audit-categories", "audit-kinds", "audit-sites")

# ---------------------------------------------------------------- 確かめ


def code_vocabulary() -> dict[str, list[str]]:
    from kyuura_engine import commands as C
    from kyuura_engine import diagnostics as D
    from kyuura_engine import legal_actions as LA
    from kyuura_engine import observation as O
    from kyuura_engine.observation import OPTION_MEANINGS
    from kyuura_engine.state import Phase

    return {
        "commands": [n for n, v in vars(C).items() if isinstance(v, type) and dataclasses.is_dataclass(v) and v.__module__ == C.__name__],
        "phases": [p.value for p in Phase],
        "next": [v for k, v in vars(D).items() if k.startswith("NEXT_") and isinstance(v, str)],
        "statuses": list(D.STATE_STATUSES),
        "meanings": sorted(set(OPTION_MEANINGS.values())),
        "plain_kinds": sorted(k for k in OPTION_MEANINGS if k not in O.DECK_REVEALING_KINDS and k not in O.LOOKED_HAND_KINDS),
        "confirmed_kinds": set(LA.DISCLOSURE_CONFIRMED_KINDS) - set(O.DECK_REVEALING_KINDS) - set(O.LOOKED_HAND_KINDS),
        "order_significant": set(LA.ORDER_SIGNIFICANT_KINDS),
        "order_not_significant": set(LA.ORDER_NOT_SIGNIFICANT_KINDS),
    }


def coverage_problems(spec: dict, code: dict[str, list[str]] | None = None) -> list[str]:
    code = code_vocabulary() if code is None else code
    problems = []
    mapped = [o["command"] for o in spec["operations"]]
    problems += [f"コマンドの型 {c} に候補の種類がない（コードに加わった型）" for c in code["commands"] if c not in mapped]
    problems += [f"候補の種類のコマンド {c} がコードにない" for c in mapped if c not in code["commands"]]
    phases = [p["phase"] for p in spec["phases"]]
    problems += [f"段階 {p} の行がない（コードに加わった段階）" for p in code["phases"] if p not in phases]
    problems += [f"段階 {p} の行があるが、コードにない" for p in phases if p not in code["phases"]]
    problems += [f"段階 {p['phase']} の状態の区分 {p['status']} がコードの語彙にない" for p in spec["phases"] if p["status"] not in code["statuses"]]
    problems += [f"next の種類 {n} の対応がない" for n in code["next"] if n not in spec["next_map"]]
    problems += [f"next の対応 {n} がコードにない" for n in spec["next_map"] if n not in code["next"]]
    problems += [f"決定の選べるものの意味 {m} に入力の種類の対応がない" for m in code["meanings"] if m not in spec["option_meaning_map"]]
    problems += [f"決定 {k} の情報境界の分類がない（D-U7-DECISION-UID）" for k in code.get("plain_kinds", []) if k not in spec["disclosure"]]
    problems += [f"情報境界の分類の決定 {k} がコードにない" for k in spec["disclosure"] if k not in code.get("plain_kinds", [])]
    if "confirmed_kinds" in code:
        written = {k for k, v in spec["disclosure"].items() if v["status"] == "confirmed"}
        if written != code["confirmed_kinds"]:
            problems.append(f"情報境界を確かめた種類が、legal_actions.DISCLOSURE_CONFIRMED_KINDS と違う（{sorted(written ^ code['confirmed_kinds'])}）")
    if "order_significant" in code and {k for k, v in spec["order"].items() if v["status"] == "significant"} != code["order_significant"]:
        problems.append("答えの並びに意味がある種類が、legal_actions.ORDER_SIGNIFICANT_KINDS と違う")
    if "order_not_significant" in code and {k for k, v in spec["order"].items() if v["status"] == "not_significant"} != code["order_not_significant"]:
        problems.append("答えの並びに意味がない種類が、legal_actions.ORDER_NOT_SIGNIFICANT_KINDS と違う")
    return problems + site_problems(spec)


def site_problems(spec: dict, scanned: set | None = None) -> list[str]:
    """出し方の一覧（監査の判定）と、コードの走査を (種類, ファイル, クラス, 関数) の組で照らす。種類ごとの情報境界・答えの並びが出し方の判定から決まること。"""
    from kyuura_engine import observation as O

    problems = []
    scanned = SITES.site_keys(SITES.scan(ROOT)) if scanned is None else scanned
    audited = set(SITES.AUDIT)
    problems += [f"決定の出し方 {k} に監査の判定がない（コードに加わった出し方）" for k in sorted(scanned - audited, key=str)]
    problems += [f"監査の判定の出し方 {k} がコードにない" for k in sorted(audited - scanned, key=str)]
    cats, orders = set(spec["audit_categories"]), set(spec["audit_orders"])
    for key, (cat, order) in sorted(SITES.AUDIT.items(), key=str):
        if cat not in cats or order not in orders:
            problems.append(f"出し方 {key} の判定 ({cat}, {order}) が語彙にない")
        if key[0] in (O.DECK_REVEALING_KINDS | O.LOOKED_HAND_KINDS) and cat != "started_search":
            problems.append(f"出し方 {key} は始まった検索の種類だが、情報源が started_search でない")
    by: dict[str, list] = {}
    for key, value in SITES.AUDIT.items():
        by.setdefault(key[0], []).append(value)
    for kind, item in spec["disclosure"].items():
        if item["status"] == "confirmed" and kind not in by:
            problems.append(f"情報境界を確かめた種類 {kind} に、監査した出し方がない")
    for kind, item in spec["order"].items():
        site_orders = {o for _, o in by.get(kind, [])}
        if item["status"] == "significant" and "significant" not in site_orders:
            problems.append(f"答えの並びに意味がある種類 {kind} に、意味がある出し方がない")
        if item["status"] == "not_significant" and (site_orders - {"single", "not_significant"} or "not_significant" not in site_orders):
            problems.append(f"答えの並びに意味がない種類 {kind} の出し方の判定が {sorted(site_orders)}（意味がない・1 以下だけであること）")
    for kind, values in by.items():
        if "significant" in {o for _, o in values} and spec["order"].get(kind, {}).get("status") != "significant":
            problems.append(f"種類 {kind} に答えの並びに意味がある出し方があるが、種類の分類が significant でない")
    return problems


def spec_problems(spec: dict) -> list[str]:
    problems = []
    if spec.get("approval") != "not_approved" or spec.get("status") != "proposed":
        problems.append("仕様案が承認済みになっている（原則の採用は adoption に書く）")
    kinds = [o["kind"] for o in spec["operations"]]
    if len(set(kinds)) != len(kinds):
        problems.append("候補の種類が重なる")
    for p in spec["phases"]:
        for c in p["candidates"]:
            if c not in kinds:
                problems.append(f"段階 {p['phase']} の候補 {c} が種類の一覧にない")
    for n, cs in spec["next_map"].items():
        for c in cs:
            if c not in kinds:
                problems.append(f"next {n} の候補 {c} が種類の一覧にない")
    covered = {c for cs in spec["next_map"].values() for c in cs}
    problems += [f"候補の種類 {k} が next のどれにも対応しない" for k in kinds if k not in covered]
    input_ids = {i["id"] for i in spec["input_kinds"]}
    for o in spec["operations"]:
        for step in o["inputs"]:
            if step.split(":")[0] not in input_ids:
                problems.append(f"種類 {o['kind']} の入力の段 {step} が入力の種類の語彙にない")
    problems += [f"決定の意味 {m} の入力の種類 {v} が語彙にない" for m, v in spec["option_meaning_map"].items() if v not in input_ids]
    if "decline" not in input_ids:
        problems.append("任意の辞退の入力がない")
    proc = {p["id"]: p for p in spec["processability"]}
    for need in ("supported", "unresolved_ruling", "not_implemented", "technical_limit", "may_stop_later", "unverified"):
        if need not in proc:
            problems.append(f"処理可能性の区分 {need} がない")
    for p in spec["processability"]:
        if "表示" not in p["display"]:
            problems.append(f"処理可能性 {p['id']} の候補を表示しない（候補から黙って消さない）")
    for need in ("unresolved_ruling", "not_implemented"):
        if need in proc and "ゲーム上の禁止ではない" not in proc[need]["display"]:
            problems.append(f"処理可能性 {need} の表示が、ゲーム上の禁止と区別されていない")
    if {c["id"] for c in spec["completeness"]} != {"complete", "partial", "undetermined"}:
        problems.append("完全性の区分が complete・partial・undetermined でない")
    if any(p["phase"] == "main" and p["complete_v1"] for p in spec["phases"]):
        problems.append("初版で main の候補を complete と称している（保証できない完全性は保証しない）")
    rev = spec["revision"]
    if rev["source"] in rev["forbidden_sources"] or rev["source"] in ("state_hash", "rng_check"):
        problems.append("revision の元が、状態のハッシュ・乱数の確認値など使わない元になっている")
    for need in ("state_hash", "rng_check"):
        if need not in rev["forbidden_sources"]:
            problems.append(f"revision の使わない元に {need} がない")
    channels = {b["channel"] for b in spec["info_boundary"]}
    for need in ("count", "order", "missing", "reason", "identifier", "invalid_query", "started_search", "other_viewers", "verifier_data"):
        if need not in channels:
            problems.append(f"情報境界の経路 {need} の規則がない")
    if not any(k["id"] == "secret" and k["allowed"] == "使わない" for k in spec["knowledge"]):
        problems.append("秘密の情報を使わないことが情報の元の表にない")
    adopted = {p["id"] for p in spec["principles"] if p["kind"] == "adopted"}
    for need in ("P-ACTOR", "P-NOT-NEXT", "P-FINAL", "P-NO-TRIAL", "P-TWIN", "P-NOT-HIDDEN", "P-COMPLETENESS", "P-REVISION", "P-NO-MODE-BRANCH"):
        if need not in adopted:
            problems.append(f"採用済みの原則 {need} がない")
    units = {u["id"]: u for u in spec["units"]}
    order = [u["id"] for u in spec["units"]]
    for u in spec["units"]:
        for dep in u["depends"]:
            if dep not in units:
                problems.append(f"単位 {u['id']} の依存 {dep} がない")
            elif order.index(dep) > order.index(u["id"]):
                problems.append(f"単位 {u['id']} があとの単位 {dep} に依存する")
        if not u["tests"] or not u["done"]:
            problems.append(f"単位 {u['id']} に回帰テスト・完了の基準がない")
    for o in spec["operations"]:
        if o["unit"] not in units:
            problems.append(f"種類 {o['kind']} の単位 {o['unit']} がない")
    test_ids = {t["id"] for t in spec["leak_tests"]}
    for u in spec["units"]:
        for t in u["tests"]:
            tid = t.split("（")[0]
            if tid.startswith("T-") and tid not in test_ids:
                problems.append(f"単位 {u['id']} のテスト {tid} が漏れの回帰テストの一覧にない")
    adoption = spec["u7_1_adoption"]
    for d in spec["decisions"]:
        if d.get("status") == "adopted":
            if d.get("adoption") != adoption["id"] or d["id"] not in adoption["decisions"] or not d.get("adopted"):
                problems.append(f"判断事項 {d['id']} の採用の記録（adoption・adopted）がない")
        elif d.get("status") == "checked":
            if not d.get("result"):
                problems.append(f"判断事項 {d['id']} の確かめの結果がない")
        elif d.get("status") != "pending":
            problems.append(f"判断事項 {d['id']} の状態 {d.get('status')} が pending・adopted・checked でない")
    if {d["id"] for d in spec["decisions"] if d.get("status") == "adopted"} != set(adoption["decisions"]):
        problems.append("採用した判断事項と、U7-1 の採用の記録の判断事項が違う")
    for need in ("D-U7-DISPLAY", "D-U7-COMPLETENESS"):
        if next((d for d in spec["decisions"] if d["id"] == need), {}).get("status") != "pending":
            problems.append(f"判断事項 {need} は U7-1 で採用していない（pending のまま）")
    adopted_units = set(adoption["units"]) | set(spec["u7_2_adoption"]["units"])
    if {u["id"] for u in spec["units"] if u.get("status") == "implemented"} != adopted_units:
        problems.append("実装した単位と、U7-1・U7-2 の採用の記録の単位が違う")
    if set(adoption["units"]) & set(spec["u7_2_adoption"]["units"]):
        problems.append("同じ単位を 2 つの採用の記録が実装したことになっている")
    if any(u.get("status") not in ("implemented", "planned") for u in spec["units"]):
        problems.append("単位の状態が implemented・planned でない")
    return problems + coverage_problems(spec)


def check(written: dict, design: str, plan: str, u7_1: str | None = None, audit: str | None = None, u7_2: str | None = None) -> list[str]:
    spec = build()
    problems = []
    if written != spec:
        problems.append("書いた JSON が、作り直した仕様案と違う（--write で作り直す）")
    rendered = blocks(spec)
    u7_1 = U7_1.read_text(encoding="utf-8") if u7_1 is None else u7_1
    audit = AUDIT_DOC.read_text(encoding="utf-8") if audit is None else audit
    u7_2 = U7_2.read_text(encoding="utf-8") if u7_2 is None else u7_2
    for label, text, names in (("設計の文書", design, DESIGN_BLOCKS), ("実装計画の文書", plan, PLAN_BLOCKS), ("U7-1 の文書", u7_1, U7_1_BLOCKS),
                               ("監査の文書", audit, AUDIT_BLOCKS), ("U7-2 の文書", u7_2, U7_2_BLOCKS)):
        new, block_problems = render_into(text, rendered, names)
        problems += [f"{label}: {p}" for p in block_problems]
        if new != text:
            problems.append(f"{label}の生成区画が、作り直したものと違う（--write で作り直す）")
    return problems + spec_problems(written)


def main() -> int:
    parser = argparse.ArgumentParser()
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--write", action="store_true")
    group.add_argument("--check", action="store_true")
    args = parser.parse_args()
    spec = build()
    if args.write:
        problems = spec_problems(spec)
        if problems:
            print("\n".join(problems))
            return 1
        OUTPUT.write_text(dump(spec), encoding="utf-8", newline="\n")
        rendered = blocks(spec)
        for path, names in ((DESIGN, DESIGN_BLOCKS), (PLAN, PLAN_BLOCKS), (U7_1, U7_1_BLOCKS), (AUDIT_DOC, AUDIT_BLOCKS), (U7_2, U7_2_BLOCKS)):
            text, block_problems = render_into(path.read_text(encoding="utf-8"), rendered, names)
            if block_problems:
                print("\n".join(f"{path.name}: {p}" for p in block_problems))
                return 1
            path.write_text(text, encoding="utf-8", newline="\n")
        print("書いた")
        return 0
    if not OUTPUT.exists():
        print("仕様案の JSON がない（--write で作る）")
        return 1
    problems = check(json.loads(OUTPUT.read_text(encoding="utf-8")), DESIGN.read_text(encoding="utf-8"), PLAN.read_text(encoding="utf-8"))
    print("\n".join(problems) if problems else "problems=0")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())

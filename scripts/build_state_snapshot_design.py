"""状態スナップショット（U6）の仕様案 docs/state-snapshot-design.json を作る・確かめる（仕様だけ。保存・復元は実装しない）。

    python scripts/build_state_snapshot_design.py --write   # JSON と、2 つの文書の生成区画（表）を、このスクリプトの SPEC から書き直す
    python scripts/build_state_snapshot_design.py --check   # JSON・生成区画が作り直したものと同じか、状態の全項目に分類があるか（kyuura_engine/state.py の dataclass と
                                                            # rules.RuleSet の項目と照らす）、参照・分類・判断事項の矛盾がないか

- 仕様の唯一の元は、このスクリプトの ``SPEC``。JSON と文書の表はここから作る（二重に手で書かない）。文書の生成区画の外（本文）は手で書く
- 項目の分類は、型ごとに項目の名前を書く（主要な型は項目ごとの分類、値の記録の型は「すべての項目を値で保存する」と項目の名前の並び）。コードに項目が増えた・減ったら
  --check が見つける（件数ではなく名前で照らす）
- 利用者が採用したのは原則（ADOPT-U6-PRINCIPLES）だけで、スキーマの細部・自動移行は採用していない（``approval`` は ``not_approved``。判断事項はどれも ``pending``）
"""

from __future__ import annotations

import argparse
import dataclasses
import json
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
OUTPUT = ROOT / "docs" / "state-snapshot-design.json"
DESIGN = ROOT / "docs" / "state-snapshot-design.md"
PLAN = ROOT / "docs" / "state-snapshot-implementation-plan.md"

CATEGORIES = {
    "value": "1. JSON に値を保存する",
    "resolve": "2. 固定した登録・依存データから解決する",
    "derive": "3. ほかの保存値から作り直す",
    "absent": "4. 保存の境界では存在してはいけない",
    "descriptive": "5. 説明用で復元には使わない",
}

VALUE_RECORD_TYPES = {
    "Asleep": (),
    "AttachedTrainer": ('card', 'player', 'discard_at_end_of_turn'),
    "AttackBarrier": ('source_card', 'source_player', 'created_turn', 'active_turn'),
    "AttackCoinCheck": ('source_card', 'source_player', 'created_turn', 'active_turn', 'single_use', 'lasting'),
    "AttackEffectGuard": ('source_card', 'source_player', 'created_turn', 'active_turn'),
    "AttackReceived": ('turn', 'card', 'player', 'source', 'declared', 'processed', 'damage', 'reached', 'voided', 'active_damage'),
    "AttackUsed": ('turn', 'card', 'declared', 'processed'),
    "BasicEntry": ('card', 'source', 'source_card', 'zone', 'turn'),
    "BenchAttackDamageGuard": ('source_card', 'source_player', 'created_turn', 'active_turn'),
    "BenchPowersStopped": ('source_card', 'source_player', 'created_turn', 'active_turn'),
    "BenchProtection": ('source_card', 'source_player', 'created_turn', 'active_turn'),
    "CannotAttachEnergy": ('source_card', 'source_player', 'created_turn', 'active_turn'),
    "CannotAttack": ('source_card', 'source_player', 'created_turn', 'active_turn'),
    "CannotAttackNextOwnTurn": ('source_card', 'source_player', 'created_turn', 'active_turn'),
    "CannotAttackWhileSourceActive": ('source_card', 'source_player', 'created_turn', 'active_turn'),
    "CannotRetreat": ('source_card', 'source_player', 'created_turn', 'active_turn'),
    "CannotRetreatNextOwnTurn": ('source_card', 'source_player', 'created_turn', 'active_turn'),
    "CannotUseAttack": ('source_card', 'source_player', 'created_turn', 'active_turn', 'attack_index', 'target_attack_index', 'attack_card', 'target_attack_card'),
    "CannotUseOwnAttack": ('source_card', 'source_player', 'created_turn', 'active_turn', 'attack_index', 'target_attack_index', 'attack_card'),
    "CannotUsePowers": ('source_card', 'source_player', 'created_turn', 'active_turn'),
    "ColorEffect": ('kind', 'player', 'source', 'source_card', 'power_index', 'target', 'color', 'turn', 'left_play'),
    "Confused": (),
    "DamageReduction": ('source_card', 'source_player', 'created_turn', 'active_turn', 'amount', 'non_attack_unresolved'),
    "DealtAttackDamageReduction": ('source_card', 'source_player', 'created_turn', 'active_turn', 'end_turn', 'source_pokemon', 'amount', 'while_source_active', 'ends_on'),
    "DestinyBond": ('source_card', 'source_player', 'created_turn', 'active_turn'),
    "DoubledDamage": ('source_card', 'source_player', 'created_turn', 'active_turn'),
    "EnergyRole": ('card', 'energy_type', 'units', 'owner', 'turn'),
    "EvolutionLock": ('source_card', 'source_player', 'created_turn', 'active_turn'),
    "FrozenForm": ('pokemon', 'card', 'kind', 'source'),
    "HalvedDamage": ('source_card', 'source_player', 'created_turn', 'active_turn'),
    "KnockOutSurvival": ('source_card', 'source_player', 'created_turn', 'active_turn', 'end_turn', 'scope', 'remaining_hp'),
    "Marker": ('kind', 'player', 'source_card', 'attack', 'turn', 'color'),
    "MaxHpSet": ('source_card', 'source_player', 'created_turn', 'active_turn', 'amount'),
    "NextTurnAttackDamage": ('source_card', 'source_player', 'created_turn', 'active_turn', 'attack_index', 'target_attack_index', 'amount', 'operation', 'includes_self_damage', 'attack_card'),
    "NextTurnFailureWaiver": ('source_card', 'source_player', 'created_turn', 'active_turn', 'attack_index', 'target_attack_index', 'target_player', 'target_pokemon', 'attack_card'),
    "OtherReceived": ('turn', 'card'),
    "OwnershipChange": ('card', 'card_id', 'previous', 'owner', 'origin', 'turn', 'trainer_card', 'exchange'),
    "Paralyzed": ('turn',),
    "PeriodAttackCoinCheck": ('source_card', 'source_player', 'created_turn', 'active_turn', 'end_turn', 'source_pokemon', 'while_source_active', 'ends_on'),
    "PeriodAttackLock": ('source_card', 'source_player', 'created_turn', 'active_turn', 'end_turn', 'source_pokemon', 'while_source_active', 'ends_on'),
    "PeriodLeaveLock": ('source_card', 'source_player', 'created_turn', 'active_turn', 'end_turn', 'source_pokemon', 'while_source_active', 'ends_on', 'knockout_exception', 'source_left'),
    "PeriodRetreatLock": ('source_card', 'source_player', 'created_turn', 'active_turn', 'end_turn', 'source_pokemon', 'while_source_active', 'ends_on'),
    "Poison": ('damage', 'multiplier'),
    "PoisonMist": ('player', 'pokemon_id', 'source_card', 'card_id', 'power_index', 'created_turn', 'poisoned_before', 'interrupted'),
    "PowersStopped": ('source_card', 'source_player', 'created_turn', 'active_turn'),
    "PreventAttackDamage": ('source_card', 'source_player', 'created_turn', 'active_turn'),
    "PreventDamage": ('source_card', 'source_player', 'created_turn', 'active_turn'),
    "PursuitOnRetreat": ('source_card', 'source_player', 'created_turn', 'active_turn', 'amount', 'attack'),
    "RecallEffect": ('player', 'turn', 'pokemon_id', 'card', 'trainer'),
    "ReceivedAttackDamageBonus": ('source_card', 'source_player', 'created_turn', 'active_turn', 'end_turn', 'source_pokemon', 'amount', 'while_source_active', 'ends_on'),
    "ReducedDamageToSource": ('source_card', 'source_player', 'created_turn', 'active_turn', 'amount'),
    "ReducedDamageToSourceNextTurn": ('source_card', 'source_player', 'created_turn', 'active_turn', 'amount'),
    "ReflectShield": ('source_card', 'source_player', 'created_turn', 'active_turn', 'attack_index', 'amount', 'attack_card'),
    "ReplacementPoison": ('player', 'knocked_pokemon_id', 'card_id', 'attack_index', 'attacker_player', 'attacker_pokemon_id', 'attacker_card', 'attacker_evolved', 'created_turn', 'status'),
    "ResistanceChange": ('source_card', 'source_player', 'created_turn', 'active_turn', 'color'),
    "Retaliation": ('source_card', 'source_player', 'created_turn', 'active_turn', 'attack_index', 'amount', 'basis', 'multiplier', 'on_heads', 'attack_card'),
    "RetreatCostIncrease": ('source_card', 'source_player', 'created_turn', 'active_turn', 'amount', 'attack'),
    "SecretePoison": ('source_card', 'source_player', 'created_turn', 'active_turn', 'attack_index', 'amount', 'attack_card'),
    "StadiumInPlay": ('owner', 'card', 'placed_turn'),
    "StatusImmunityNextTurn": ('source_card', 'source_player', 'created_turn', 'active_turn'),
    "StatusImmunityWhileActive": ('source_card', 'source_player', 'created_turn', 'active_turn', 'attack_index', 'given_by', 'attack_card'),
    "StatusOnEnergyAttach": ('source_card', 'source_player', 'created_turn', 'active_turn', 'condition', 'attack'),
    "SuperTransform": ('source', 'card', 'turn', 'left_active'),
    "TailsDamageGuard": ('source_card', 'source_player', 'created_turn', 'active_turn'),
    "TimedDamageGuard": ('source_card', 'source_player', 'created_turn', 'active_turn', 'prevent_on', 'flipper', 'scope'),
    "TrainerTurnEffect": ('kind', 'player', 'source_card', 'card_id', 'created_turn', 'expires_turn', 'pokemon_id', 'attack_index'),
    "TrainerUseLock": ('player', 'source_player', 'source_card', 'effect', 'created_turn', 'expires_turn', 'origin'),
    "TurnAttack": ('turn', 'player', 'pokemon_id', 'card', 'declared', 'processed'),
    "TurnField": ('turn', 'player', 'cards', 'face_down'),
    "TypeShift": ('color', 'turn', 'source_card', 'returned_to_bench'),
    "WeaknessChange": ('source_card', 'source_player', 'created_turn', 'active_turn', 'color'),
    "ZeroDamageAtLeast": ('source_card', 'source_player', 'created_turn', 'active_turn', 'threshold'),
    "ZeroDamageBelow": ('source_card', 'source_player', 'created_turn', 'active_turn', 'threshold'),
}

V = "value"
VERIFY_ROUND = "保存して復元した状態を、もう一度保存した JSON が同じ（往復）。継続の比べ（F）"
VERIFY_INVARIANT = "復元のあと check_invariants が空。継続の比べ（F）"


def f(category, basis, verify=VERIFY_ROUND):
    return {"category": category, "basis": basis, "verify": verify}


def value_all(names, basis, verify=VERIFY_ROUND):
    return {n: f(V, basis, verify) for n in names}


GAME_STATE = {
    "rules": f("resolve", "RuleSet の id だけを保存し、登録のルールの組（replay_record.KNOWN_RULES。今は RULES_2000_02_14 だけ）から解決する。値は数値の組で、入力から作らない",
               "知らない id は unsupported。解決したルールの組が保存した id と同じ"),
    "card_data": f(V, "カードデータの写しの元（repository・commit・path）。カードの定義は持たない", "既定のカードプールの写しの元と同じでなければ unsupported"),
    "seed": f(V, "new_game の seed。延長戦の開始でも保持する（sudden_death の keep）。乱数は seed から作り直さない（rng を保存する）"),
    "rng": f(V, "乱数の状態そのもの（rng.rng_state_to_json。形式 python-random-mt19937-v3）。指紋ではなく、正確な続きのために必要", "復元のあと rng_fingerprint が保存した確認値と同じ。継続のコイン・山札の切り方が同じ（F）"),
    "cards": f(V, "カードの対応表。CardInstance（uid・card_id・owner・origin）を対応表の並びの順に配列で保存する。鍵は各 CardInstance.uid から作り直す（項目でない値の表の derive）",
               "uid の重なりは不正（対応表にする前に見つける。重なりを後の値で上書きしない）。鍵と CardInstance.uid が同じ。cards の uid と、領域・場・置いておくカードに出てくる uid が同じ集まり（check_invariants）"),
    "definitions": f("resolve", "カード id → CardDefinition。new_game がカードプールから作り、返す状態では変えない（v0.154 の確かめ。engine.py の代入は new_game・区間の開始の引き継ぎと、返さない複製だけ）。"
                     "保存しない。cards に出てくる card_id から、既定のカードプール（load_card_pool）で解決する", "解決した定義の card_id の集まりが cards の card_id の集まりと同じ。知らない card_id は unsupported"),
    "decklists": f(V, "対戦開始時のデッキリスト（並び。uid の付け方を決め、延長戦で最初のデッキにもどすのに使う。sudden_death.initial_deck_owners）。cards から作り直せるのは並びの一部だけなので値で保存する",
                   "cards の uid の並び・出所（deck_owner）と同じ組であること"),
    "players": f(V, "2 人のプレイヤーの領域（PlayerState）"),
    "phase": f(V, "Phase の値（文字列）。知らない値は不正"),
    "effects": f("resolve", "効果の登録表。id だけを保存し、既定のカードプールの登録表（DEFAULT_EFFECTS）から解決する。関数・オブジェクトを入力から作らない", "id が既定の登録表と同じでなければ unsupported"),
    "turn_number": f(V, "番の番号"), "current_player": f(V, "番のプレイヤー"), "first_player": f(V, "先攻"),
    "energy_attachments_this_turn": f(V, "この番の手札からのエネルギーの数"), "mulligan_rounds": f(V, "切り直しの記録"),
    "result": f(V, "対戦の結果（GameResult）"), "halt": f(V, "停止の理由（Halt）。停止を解除しない"),
    "log": f(V, "今の区間のログ（イベントの並び。値はタプル・整数・文字列・真偽値・None）。ワザ・効果・不変条件・監査が読む", "JSON の配列はタプルにもどす（v0.156 の調べ）。往復"),
    "next_pokemon_id": f(V, "次の場のポケモンの番号"), "decision": f(V, "保留中の決定（PendingDecision。resume・context を含む）"), "next_decision_id": f(V, "次の決定の番号"),
    "trainer_in_use": f(V, "使っている最中のトレーナー（決定を待つ間）"), "energy_attached_by_powers_this_turn": f(V, "この番の特殊能力でつけた数"),
    "power_uses_this_turn": f(V, "この番に使った特殊能力"), "energy_burn": f(V, "この番の［エナジーバーン］"), "trainer_locks": f(V, "トレーナーの使用の禁止"),
    "recalls": f(V, "思い出させるの記録"), "trainer_effects": f(V, "トレーナーの期限のある効果"), "stadium": f(V, "場のスタジアム"),
    "stadium_uses_this_turn": f(V, "この番のスタジアムの使用"), "trainer_stack": f(V, "外側のトレーナーの使用"), "energy_roles": f(V, "エネルギーとしてついているカード"),
    "set_aside": f(V, "一時的に置いておくカード（見られるプレイヤーを含む）"), "face_up_prizes": f(V, "おもてのサイド"), "face_down_cards": f(V, "うらにしてベンチに出したカード"),
    "color_effects": f(V, "この番の色を変える効果"), "turn_history": f(V, "番ごとの記録（TurnAttack・TurnField の型の印つき）"), "poison_mists": f(V, "［ポイズンミスト］の効果"),
    "replacement_poisons": f(V, "まだ与えていないどく"), "frozen_forms": f(V, "処理のあいだ固定した変身（決定を待つ間）"), "face_up_deck": f(V, "おもての山札のカード"),
    "ownership_changes": f(V, "所有者の変更"),
    "pending_moves": f("absent", "ワザの途中の場の移動への反応のまだ処理していない段。コマンドの終わり・決定を待つ間は空（決定をまたぐ続きは決定の context の moves に移す。v0.154 の確かめ）。"
                       "check_invariants は空であることを確かめない（v0.155 の注釈の訂正）", "保存の前に空でなければ保存を拒む（緩めない）。復元のあと空。U4 の境界の確かめと同じ"),
    "segments": f(V, "終わった区間の記録（SegmentRecord。ログ・結果・所有者の変更・うらのままだったカード）"),
    "conventions": f("resolve", "規約集合の識別（ID・版・照合値・構成）を保存し、登録の集合（conventions.registered_identity）から解決して照らす。規約のオブジェクト・関数を入力から作らない。"
                     "記録のない旧状態（UNRECORDED）は保存しない", "登録の識別と保存した識別が同じでなければ unsupported（ほかの集合に差し替えない）"),
}

EXPLICIT_TYPES = {
    "GameState": GAME_STATE,
    "PlayerState": value_all(("deck", "hand", "prizes", "discard", "active", "bench", "placed_starting_pokemon", "mulligans", "mulligan_draws_remaining"),
                             "プレイヤーの領域と準備の記録。山札・サイドの並びも秘密の値として保存する（ホスト用）。リストはリストにもどす"),
    "PokemonInPlay": value_all(("card", "energy", "damage", "pokemon_id", "trainers", "conditions", "retreat_failed_turn", "evolution_stack", "played_turn", "evolved_turn",
                                "persistent_effects", "attacks_used_once", "evolution_permission_turn", "type_shift", "disguise", "devolved_turn", "history", "markers", "basic_entry",
                                "super_transform"), "場のポケモン（重なり・ついているカード・持続する効果・履歴・マーカー）。持続する効果・履歴は型の印つき"),
    "CardInstance": {"uid": f(V, ("カードの識別。領域・場・決定の options と context・持続する効果・マーカー・履歴・ログ・過去の区間が同じ整数で同じカードを指す。new_game が deck0・deck1 の"
                              "並びの位置（0 から）で付け、延長戦の開始（sudden_death）・とりかえっこプリーズの交換（zones の所有者の変更）でも付け直さない。次の uid のような採番の状態を"
                              "持つ項目はない（カードは new_game のあとに増えない）。構築盤面（デッキリストが空）は並びから作り直せないので、カードごとに値で保存する。名前・場所から付け直さない"),
                              "uid が重ならない・対応表の鍵と同じ。同名のカードが複数ある盤面・領域の移動・所有者の交換のあとも、保存の前と同じ uid が同じ card_id・owner・origin を持つ（往復と継続の比べ）"),
                     "card_id": f(V, "カード id"), "owner": f(V, "対戦の中の所有者"), "origin": f(V, "対戦開始時のデッキのプレイヤー（変更があったカードだけ）")},
    "PendingDecision": value_all(("id", "kind", "player", "options", "min_choices", "max_choices", "resume", "context"),
                                 "保留中の決定。resume は再開先の名前、context は続きの情報（値は整数・文字列とそのタプル）。知らない再開先は supported_decision_error で unsupported"),
    "Halt": {"code": f(V, "停止のコード"), "message": f(V, "診断用の文（説明用だが状態の一部。復元で変えない。閲覧者に渡さない）"),
             "references": f(V, "根拠の参照（説明用だが状態の一部）"), "interruption": f(V, "途中停止の記録")},
    "Interruption": value_all(("kind", "code", "kyuura_issue", "source", "player", "target_owner", "target", "element", "required", "available", "pending", "in_transit", "log_index"),
                              "途中停止の記録（そこまでの処理・在途のカード）"),
    "SegmentRecord": value_all(("index", "prize_count", "first_player", "turn_number", "mulligan_rounds", "result", "log", "ownership_changes", "face_down_cards"),
                               "終わった区間（ログは今の区間と同じくタプルにもどす）"),
    "GameResult": value_all(("outcome", "winner", "conditions"), "結果"),
    "DataSource": value_all(("repository", "commit", "path"), "カードデータの写しの元"),
    "SpecialConditions": value_all(("poison", "exclusive"), "特殊状態（exclusive は Asleep・Paralyzed・Confused の型の印つき）"),
    "TrainerInUse": value_all(("player", "card", "user", "via"), "使用中のトレーナー"),
    "SetAsideCards": value_all(("kind", "owner", "cards", "visible_to", "user", "trainer_card", "card_id", "created_turn", "return_turn"), "置いておくカード"),
    "RuleSet": {name: f("resolve", "ルールの組は id で登録から解決する（数値を入力から作らない）", "登録のルールの組の id と同じ")
                for name in ("id", "title", "deck_size", "max_copies_per_name", "opening_hand_size", "max_setup_bench", "max_bench", "prize_count",
                             "mulligan_draw_max_per_mulligan", "first_player_draws_on_first_turn", "energy_attachments_per_turn", "weakness_multiplier",
                             "damage_per_counter", "sudden_death_prize_count")},
}
TYPE_MODULES = {"RuleSet": "kyuura_engine.rules"}
VALUE_RECORD_BASIS = "値の記録（持続する効果・マーカー・履歴・効果の記録など）。すべての項目を値で保存し、型の名前の印（state.py の dataclass の名前の許した一覧）で作り直す"

NON_FIELD_ATTRIBUTES = [
    {"name": "GameState.cards の鍵", "category": "derive", "basis": "対応表の鍵は、配列で保存した CardInstance.uid から作り直す（同じ値を 2 か所に書かない。v0.157 の訂正で、uid そのものは CardInstance の値で保存する）",
     "verify": "保存の前に鍵と CardInstance.uid が同じこと。復元で uid が重なれば malformed"},
    {"name": "GameState._history_probe", "category": "absent", "basis": "history.open_probe が setattr で置き、close_probe がコマンドの終わりに取り除く一時的な属性（dataclass の項目ではない）",
     "verify": "保存の前に、状態の __dict__ に dataclass の項目のほかの名前があれば保存を拒む"},
    {"name": "zones.IDENTITY_CONSULTED", "category": "absent", "basis": "モジュールの変数（受け付けるかを確かめる間だけ使う）。状態ではない", "verify": "保存・復元で扱わない（コマンドの外では None）"},
]
SNAPSHOT_METADATA = [
    {"name": "header.git_commit", "category": "descriptive", "basis": "補助の情報（U3 と同じ。識別に使わない）"},
    {"name": "header.label・created_by", "category": "descriptive", "basis": "ホストが付ける説明"},
    {"name": "header.origin", "category": "descriptive", "basis": "どこから保存したか（完全な記録の game_id・seq など。対応付けのため）"},
]

SPEC = {
    "schema_version": 1,
    "title": "状態スナップショット（U6）の仕様案",
    "status": "proposed",
    "approval": "not_approved",
    "base": {"commit": "ffc48f9d3bfa0b7e0391db8cbe3e0a9fc7c32895", "engine_version": "0.155.0", "origin_main": "8d4beffd9e4cc77367df8a4eae1657c04ca824d0"},
    "adoption": {
        "id": "ADOPT-U6-PRINCIPLES", "date": "2026-11-06", "by": "利用者",
        "scope": "U6 の仕様の作成と次の原則だけ。スキーマの細部・自動移行の方法・U6 の実装の承認ではない",
        "principles": [
            "スナップショットは形式 35 をそのまま復元の形式に使わず、必要な全状態を明示した独立の形式にする",
            "初めの対応範囲は、同じ実装・依存データ・規約集合に限る",
            "カード定義・規約は、原則として識別の情報から登録済みのものを解決する",
            "乱数の状態を正確に保存・復元する",
            "決定待ちを保存・復元の対象に含める",
            "HALTED・途中停止も保存・復元できる設計にする。停止の解除・未対応の続行は認めない",
            "不正・未知の状態を推測で補ったり移したりしない",
            "スナップショットは完全な情報を持つホスト用で、閲覧用記録と分ける",
            "完了の基準は JSON の往復だけでなく、復元のあとの同じ操作の列で状態・乱数・ログ・観測が同じこと",
        ],
        "decisions_in_diagnostics_spec": ["D-SNAPSHOT-BASE", "D-HALT-SNAPSHOT"],
    },
    "format": {"key": "kyuura_snapshot_format", "name": "kyuura state snapshot", "version": 1, "status": "proposed",
               "note": "仕様案 docs/diagnostics-replay-api-design.json の版の表の kyuura_snapshot_format。形式 35（format_version）・再現用記録（kyuura_replay_format）・閲覧用記録（kyuura_view_format）とは別の番号"},
    "implementation_adoption": {
        "id": "ADOPT-U6-IMPL", "date": "2026-11-07", "by": "利用者",
        "scope": "U6 の S1〜S4・S6 の実装と、判断事項 6 件の採用（採用した内容は 8 章・実装計画 5 章の表）。S5（完全な記録の途中から再開して U4 で照らす）は別の作業",
        "decisions": ["DS-CONSTRUCTED", "DS-HALT-TEXT", "DS-CHECK", "DS-DEPTH", "DS-RECORD-LINK", "DS-INSTRUMENTATION"],
        "units": ["S1", "S2", "S3", "S4", "S6"],
        "not_implemented": ["S5"],
        "implemented_in": "v0.157（kyuura_engine/snapshot.py。docs/state-snapshot-v0.157.md）",
    },
    "categories": CATEGORIES,
    "explicit_types": EXPLICIT_TYPES,
    "value_record_types": {name: list(fields) for name, fields in VALUE_RECORD_TYPES.items()},
    "value_record_basis": VALUE_RECORD_BASIS,
    "non_field_attributes": NON_FIELD_ATTRIBUTES,
    "snapshot_metadata": SNAPSHOT_METADATA,
    "json_types": [
        {"python": "tuple", "json": "配列", "restore": "項目の型（スキーマ）がタプルなら、入れ子までタプルにもどす（ログ・決定の context の値は、入れ子の配列をすべてタプルに）"},
        {"python": "list", "json": "配列", "restore": "PlayerState の領域・PokemonInPlay.energy・trainers・GameState.players はリストにもどす（v0.156 の調べで、リストとタプルが混ざる）"},
        {"python": "Mapping（cards・log のイベント）", "json": "cards は CardInstance の配列（対応表の並びの順）、イベントはオブジェクト（鍵の順を保つ）",
         "restore": "cards は配列の順に、各 CardInstance.uid を鍵にした読み取り専用の対応表に（uid の重なりは不正）。イベントは MappingProxyType に"},
        {"python": "enum（Phase・EnergyType の値をもつ項目）", "json": "値の文字列", "restore": "項目ごとに決めた列挙型の値として読む。知らない値は不正"},
        {"python": "dataclass（値の記録・主要な型）", "json": "オブジェクト {\"type\": dataclass の名前, \"fields\": 項目}", "restore": "許した名前の一覧（state.py の dataclass）からだけ作る。項目の注釈が名前を決める位置では、その型（union ならその中の型）だけを受ける。ほかの名前・import は使わない"},
        {"python": "注釈が Any の位置（ログのイベントの値・決定の context の値・持続する効果・履歴）", "json": "配列（タプル）・整数・文字列・真偽値・null・型の印つきのオブジェクト",
         "restore": "配列はタプルに、{\"type\", \"fields\"} は値の記録に、{\"enum\", \"value\"} は Phase・EnergyType に。リスト・辞書・浮動小数・ほかの型は表さない（保存を拒む）"},
        {"python": "random.Random", "json": "rng_state_to_json の形", "restore": "rng_from_json（知らない形式は不正）"},
        {"python": "int・str・bool・None", "json": "同じ", "restore": "真偽値と整数を取り違えない（bool は int として受けない）。浮動小数・NaN は受けない"},
    ],
    "header": [
        {"item": "kyuura_snapshot_format", "required": True, "meaning": "スナップショットの形式の版（1）"},
        {"item": "engine", "required": True, "meaning": "エンジンの版と実装の識別（replay_record.implementation_identity と同じ。behavior_digest で扱えるかを決める）"},
        {"item": "runtime", "required": True, "meaning": "Python の実装と版・乱数の方式（replay_record.runtime_identity と同じ。実装と major・minor が同じときだけ扱える）"},
        {"item": "dependencies", "required": True, "meaning": "ルールの組の id・カードプール（default だけ）・カードデータの写しの元・効果の登録表の id"},
        {"item": "convention_set", "required": True, "meaning": "規約集合の ID・版・照合値・構成（ConventionSetIdentity.record）"},
        {"item": "formats", "required": True, "meaning": "参照する形式（確認値の方式 state-export-35-sha256/1・python-random-getstate-sha256/1、診断の形式）"},
        {"item": "check", "required": True, "meaning": "保存した状態の確認値（replay_record.checks と同じ。復元のあとに照らす期待値で、復元の入力ではない）"},
        {"item": "state", "required": True, "meaning": "状態の値（分類 1 の項目と、分類 2 の識別）。分類 3・4 は入れない"},
        {"item": "origin・label・git_commit", "required": False, "meaning": "説明用（分類 5）"},
    ],
    "limits": {"max_bytes": "64 MiB（replay_record.MAX_RECORD_BYTES と同じ）。保存も同じ上限で拒む（too_large）",
               "max_depth": ("64（replay_record.MAX_DEPTH と同じ。DS-DEPTH）。保存も同じ数え方・同じ上限で拒む（too_deep）。v0.157 の限定の監査で、実際のスナップショットの深さは最大 13"
                             "（テストの盤面と new_game からの対戦。上限の半分以下であることをテストで確かめる）"),
               "reader": "replay_record.read_json_object（重なった鍵・NaN・UTF-8 でないもの・最上位が辞書でないものを拒む。誤りの文に入力の値を入れない）",
               "unknown": "知らない項目・知らない値（列挙・決定の種類・再開先・持続する効果の型の名前）・知らない形式の版は拒む。今の既定の値で補わない"},
    "boundary": [
        "保存できるのは、ホストが持つ安定した状態だけ: new_game・adapter.start_game の結果、受理した操作（apply_command・adapter.submit・HostedGame・ReplayCollector）のあとの状態、拒否の結果の元の状態",
        "コマンドの処理の途中の内部の状態（解決の基盤の途中・先読みの複製・決定の答えの処理の途中）は保存しない",
        ("保存の前の確かめ: check_invariants が空、pending_moves が空、__dict__ に dataclass の項目のほかの名前がない、規約集合の識別が記録されている（UNRECORDED でない）、"
         "保留中の決定の再開先をこの版が扱える、カードプール（写しの元・定義）が既定のもの、効果の登録表が既定のカードプールの登録表そのもの、ルールの組が登録のもの、"
         "structure_problems が空、すべての項目を型の対応表で表せる、深さ・大きさが上限の中。どれかを満たさなければ保存を拒む（エンジンの不変条件を緩めない。保存のために状態を変えない・正規化しない）"),
        "失敗（failed）のあとの状態は保存しない（adapter が状態を返さない）",
    ],
    "states": [
        {"state": "通常の対戦中（in_progress）", "save": True, "after_restore": "同じ操作をすべて受け付けうる（受理・拒否は元の状態と同じ）"},
        {"state": "準備中（切り直し・ポケモンを出す・ジャンケン）", "save": True, "after_restore": "準備の操作。準備の決定待ちも同じ"},
        {"state": "ワザ・トレーナー・特殊能力の決定待ち（awaiting_decision）", "save": True,
         "after_restore": "決定への答えだけ（id・resume・context・使用中のトレーナー・固定した変身を保存する）。答えの処理の続きは元の状態と同じ"},
        {"state": "受理した結果の途中停止（halted・interruption）", "save": True, "after_restore": "どの操作も元の状態と同じく受け付けない。停止を解除しない・在途のカードを片付けない"},
        {"state": "HALTED（そのほかの停止）", "save": True, "after_restore": "同上。規約集合を差し替えて続ける API はない"},
        {"state": "終局（game_over）", "save": True, "after_restore": "どの操作も受け付けない（GAME_OVER）"},
        {"state": "サドン・デスの開始待ち（sudden_death_pending）", "save": True, "after_restore": "StartSuddenDeath だけ。延長戦の準備は保存した乱数の続きで切る"},
        {"state": "延長戦の途中", "save": True, "after_restore": "通常の対戦中と同じ。segments・initial_prize_count を保存する"},
        {"state": "複数の過去の区間を持つ状態", "save": True, "after_restore": "segments（区間ごとのログ・結果・所有者の変更・うらのままだったカード）をそのまま"},
        {"state": "pending_moves が空でない・一時的な属性がある・不変条件を満たさない", "save": False, "after_restore": "保存を拒む（境界の外。エンジンの不具合か、境界でない状態）"},
        {"state": "記録のない規約集合（UNRECORDED）・知らない再開先の決定", "save": False, "after_restore": "保存を拒む（unsupported）"},
    ],
    "restore_steps": [
        {"step": 1, "name": "安全な JSON の読み取り", "detail": "replay_record.read_json_object", "failure": "read_error（RecordFormatError）"},
        {"step": 2, "name": "形式・型・必須の項目", "detail": "形式の版（知らない版は unsupported）、見出しの項目の過不足と型、確認値の形、origin・label の形（状態の項目の型は段 5 で読む）",
         "failure": "malformed・unsupported（形式の版）"},
        {"step": 3, "name": "実装・依存・環境・規約の対応", "detail": "behavior_digest・Python の実装と major・minor・乱数の方式・ルールの組の id・カードデータ・効果の登録表・規約集合（登録と照合値）・確認値の方式",
         "failure": "unsupported（状態を組み立てない）"},
        {"step": 4, "name": "登録済みのデータの解決", "detail": ("状態の項目の過不足（malformed）、状態の識別と見出しの依存の一致（違えば inconsistent）、ルールの組・カードの定義（definitions の card_id から）・"
                                                              "効果の登録表・規約集合の識別。知らない card_id は unsupported"), "failure": "unsupported・malformed・inconsistent"},
        {"step": 5, "name": "状態の組み立て", "detail": ("項目の値を型の対応表で読み（bool と int・浮動小数・列挙の値・型の印・uid の重なり）、GameState を新しく作る（pickle・__setstate__ を使わない。"
                                                       "既定の値で補わない。pending_moves は境界で空）。乱数は形式・625 個の整数を確かめて setstate"), "failure": "malformed（型の誤り）・internal_error"},
        {"step": 6, "name": "不変条件と領域をまたぐ整合", "detail": ("知らない再開先（unsupported）、check_invariants（カードの保存則・uid の参照先・所有者・場の形・decklists と cards）、"
                                                              "structure_problems（cards の鍵と uid・definitions と cards の card_id・決定と場のポケモンの番号と採番の状態・区間の番号）、規約集合、"
                                                              "確認値（state・rng・log_length・segment・status・decision・halt）が見出しの check と同じ、もう一度保存した JSON が入力と同じ。"
                                                              "確認値だけで正常としない（構造の確かめを先にする）"), "failure": "inconsistent（状態の不整合）・unsupported（再開先）"},
        {"step": 7, "name": "ホストへ返す", "detail": "ホスト用の結果（復元した状態と、確かめの記録）。閲覧者には渡さない。どれかの段で止まったら状態を返さない（部分的な状態を通常の対戦に使わせない）", "failure": "—"},
    ],
    "results": [
        {"id": "restored", "meaning": "すべての段を通った（状態を返す）"},
        {"id": "read_error", "meaning": "JSON として読めない・大きすぎる・深すぎる"},
        {"id": "malformed", "meaning": "形式・型・必須の項目・知らない値"},
        {"id": "unsupported", "meaning": "実装・依存・環境・規約集合・形式の版・カード・再開先をこの版が扱えない"},
        {"id": "inconsistent", "meaning": "組み立てた状態が不変条件・整合・確認値を満たさない（状態の不整合）"},
        {"id": "internal_error", "meaning": "復元の道具の中の想定外の例外（ほかの結果に変えない。traceback は検証者用）"},
    ],
    "messages": "一般向けの文は結果の種類ごとの決まった文。seed・カード・非公開の領域・入力の値を入れない。項目の場所（JSON の経路）と問題の種類は検証者用の記録に置く",
    "verification": [
        {"id": "F1", "case": "通常の操作", "fixture": "ピカチュウのデッキ seed 9（new_game から方策の操作。U3 の収集器の記録）"},
        {"id": "F2", "case": "準備中の決定待ち・対戦中の決定待ち", "fixture": "準備の各段階・サイドを取る決定・山をさがす決定（v0.150 の盤面）・ドライアップの対象の決定"},
        {"id": "F3", "case": "拒否の操作", "fixture": "記録の拒否の行（seq の順）。復元のあとも同じ診断で拒否され、状態が変わらない"},
        {"id": "F4", "case": "途中停止・HALTED", "fixture": "ドライアップ seed 0（受理した結果の途中停止）・たねポケモン 1 枚のデッキ seed 1（準備の停止）"},
        {"id": "F5", "case": "終局", "fixture": "ピカチュウ seed 0"},
        {"id": "F6", "case": "サドン・デスの開始・複数の区間", "fixture": "ピカチュウ seed 9（開始待ちで保存→ StartSuddenDeath、延長戦の途中で保存）"},
        {"id": "F7", "case": "規約が当てはまる操作", "fixture": "3 つの集合（CS-KYUURA-CURRENT@1・CS-KYUURA-PLAY-S2A@1・CS-KYUURA-PLAY-PO@1）。続行規約のログ convention_applied が出る操作を含む盤面（v0.143・v0.145 のテストの盤面）"},
        {"id": "F8", "case": "持続する効果・マーカー・うらのカード・置いておくカード・使用中のトレーナー", "fixture": "既存の版のテストの構築盤面（v0.63・v0.67・v0.90 など）。構築盤面と合法な操作の列を区別する"},
        {"id": "F9", "case": "未知・不正・矛盾する入力の拒否", "fixture": "知らない項目・型の印・列挙の値・再開先、bool と int、NaN、大きすぎる入力、pending_moves、カードの重なり、確認値の違い、規約集合の照合値・Python の版の違い"},
    ],
    "comparison": [
        ("各境界で: 保存した全項目（スナップショットの JSON そのもの）・U3 の確認値（state・rng・log_length・segment・status・decision・halt）・ログ・observe（0・1・None）・"
         "adapter.submit の結果（outcome・status・診断の識別・view_for）を比べる"),
        "継続: 保存しない元の状態から続けたものと、保存して復元した状態から同じ操作の列（完全な記録の残りの行を seq の順）で続けたものが、各境界で同じ",
        "範囲を限った確認値（形式 35 の sha256）だけに頼らない（スナップショットは形式 35 が落とす乱数の状態・カードの定義の解決・決定の続きを持つので、スナップショットの JSON の一致も比べる）",
        "OS・Python の版をまたぐ保証は、U3 の範囲（実装と major・minor が同じ）を超えない",
    ],
    "decisions": [
        {"id": "DS-CONSTRUCTED", "question": "構築した盤面（new_game からでない状態）の保存を許すか", "options": ["許す（ホスト・テスト用。origin に印）", "new_game からの状態だけ"],
         "recommendation": "許す。復元の確かめは同じ。完全な記録との対応は origin で表す", "status": "adopted", "adoption": "ADOPT-U6-IMPL",
         "adopted": "構築盤面も、保存の境界と整合の確かめを満たせば保存できる。保存・復元できることと、new_game から合法に到達できることは別（到達できることは保証しない）。任意のカード定義・処理を入力から登録できる意味ではない"},
        {"id": "DS-HALT-TEXT", "question": "停止の診断用の文（Halt.message・references）を保存するか", "options": ["保存する（状態の一部）", "保存せず復元で空にする"],
         "recommendation": "保存する（状態の一致を保つ。ホスト用なので閲覧者に出ない）", "status": "adopted", "adoption": "ADOPT-U6-IMPL",
         "adopted": "停止の理由の文（Halt.message・references）も完全な情報の一部として保存する。閲覧者への表示は診断 API の安全な文（public_halt）を使い、保存した文をそのまま見せない"},
        {"id": "DS-CHECK", "question": "スナップショットに確認値（期待値）を入れるか", "options": ["入れる（U3 の checks）", "入れない"], "recommendation": "入れる（復元の段 6 で照らす。入力ではない）", "status": "adopted", "adoption": "ADOPT-U6-IMPL",
         "adopted": "保存したときの確認値を入れる。復元の結果を照らすためのもので、署名・認証・改ざんの防止ではない（作り直せるので、構造・不変条件の確かめの代わりにしない）"},
        {"id": "DS-DEPTH", "question": "入れ子の深さの上限", "options": ["64（U3 と同じ）", "状態に合わせて上げる"], "recommendation": "U6-S1 で状態の最大の深さを測ってから決める", "status": "adopted", "adoption": "ADOPT-U6-IMPL",
         "adopted": "実際の入れ子とエンコードの方式を確かめて固定の上限を決め、同じ上限を保存と読み取りに当てる（書き出せたものが上限で読めない状態を作らない）。決めた値は 5 章の limits"},
        {"id": "DS-RECORD-LINK", "question": "スナップショットと完全な再現用記録の対応", "options": ["origin に game_id・seq を書く（説明用）", "記録の中にスナップショットを入れる"],
         "recommendation": "origin に書くだけ（記録の形式は変えない）。記録の途中から再開する機能は U6-S5 で別に作る", "status": "adopted", "adoption": "ADOPT-U6-IMPL",
         "adopted": "完全な再現用記録との対応は任意の補助情報（origin の game_id・seq）。スナップショットだけの復元に完全な記録を求めない"},
        {"id": "DS-INSTRUMENTATION", "question": "記録・診断の部品の識別（instrumentation_digest）の違いを非対応にするか", "options": ["しない（U3 と同じ）", "する"],
         "recommendation": "しない（ゲームの挙動の識別だけで決める）", "status": "adopted", "adoption": "ADOPT-U6-IMPL",
         "adopted": "初版は記録・診断の部品の識別（instrumentation_digest）も一致を求め、違えば unsupported。互換性を推測しない（推奨と違う選択肢を採用）"},
    ],
    "units": [
        {"id": "S1", "status": "implemented", "title": "型の対応表と書き出し（保存）", "depends": [], "scope": "分類表から作る型の対応（型の印・列挙・タプルとリスト）、保存の前の境界の確かめ、書き出し",
         "tests": ["分類表とコードの項目が名前で一致（この仕様の --check と同じ）", "境界の外の状態（pending_moves・一時的な属性・不変条件）の保存を拒む", "状態の最大の深さ（DS-DEPTH の材料）"],
         "done": ["3 つの集合・F1〜F8 の盤面の状態を書き出せる", "書き出しが状態を変えない"]},
        {"id": "S2", "status": "implemented", "title": "読み取りと段 1〜4", "depends": ["S1"], "scope": "安全な読み取り、形式と型、対応、登録データの解決",
         "tests": ["F9 の不正・未知・非対応の入力を、段ごとに決めた結果で拒む", "誤りの文に入力の値がない"], "done": ["非対応・不正な入力で状態を作らない"]},
        {"id": "S3", "status": "implemented", "title": "組み立てと段 5〜7", "depends": ["S2"], "scope": "GameState を値から組み立て、不変条件・整合・確認値・往復で確かめ、ホストへ返す",
         "tests": ["往復で JSON が同じ", "確認値・不変条件の違いを inconsistent で見つける"], "done": ["部分的な状態を返さない", "pickle・__setstate__ を使わない"]},
        {"id": "S4", "status": "implemented", "title": "継続一致の検証", "depends": ["S3"], "scope": "保存しない状態と、保存して復元した状態から同じ操作の列で続け、各境界で比べる（F の比べ）",
         "tests": ["F1〜F8 の各境界で、保存した全項目・確認値・ログ・観測・診断が同じ"], "done": ["3 つの集合で同じ"]},
        {"id": "S5", "status": "planned", "title": "記録との接続", "depends": ["S4"], "scope": "完全な再現用記録の途中の行から、スナップショットで再開して残りを U4 で照らす（resume_from_snapshot）",
         "tests": ["記録の k 行目のあとで保存→復元→残りの行が一致", "違う記録・違う位置を見つける"], "done": ["U4 の結果の語彙に合わせる"]},
        {"id": "S6", "status": "implemented", "title": "ホストへの接続", "depends": ["S3"], "scope": "HostedGame・ReplayCollector・ViewHost から保存・復元する入口（閲覧者には渡さない）",
         "tests": ["閲覧用記録・view_for にスナップショットの値が出ない", "復元した対戦を続けた閲覧用記録が、保存しなかった場合と同じ"], "done": ["見る人の値で検証者の情報が取れない"]},
    ],
}


# ---------------------------------------------------------------- 生成


def build() -> dict:
    return json.loads(json.dumps(SPEC, ensure_ascii=False))


def dump(data: dict) -> str:
    return json.dumps(data, ensure_ascii=False, indent=1) + "\n"


def _cell(value) -> str:
    if value is None:
        return ""
    if isinstance(value, bool):
        return "はい" if value else "いいえ"
    if isinstance(value, (list, tuple)):
        return "<br>".join(_cell(v) for v in value)
    return str(value).replace("|", "\\|").replace("\n", " ")


def _table(headers, rows) -> list[str]:
    return ["| " + " | ".join(headers) + " |", "|" + "---|" * len(headers)] + ["| " + " | ".join(_cell(c) for c in row) + " |" for row in rows]


COUNT_KINDS = {"fields": "状態の dataclass の項目", "non_field": "項目でない値（対応表の鍵・一時的な属性・モジュールの変数）", "metadata": "見出しの補助情報"}


def category_counts(spec: dict) -> dict[str, dict[str, int]]:
    """分類ごとの数を、状態の dataclass の項目（state.py の dataclass と RuleSet）・項目でない属性・見出しの補助情報に分けて数える（別のものを 1 つの数に足さない）。"""
    counts = {c: dict.fromkeys(COUNT_KINDS, 0) for c in spec["categories"]}
    for fields in spec["explicit_types"].values():
        for item in fields.values():
            counts[item["category"]]["fields"] += 1
    counts["value"]["fields"] += sum(len(v) for v in spec["value_record_types"].values())
    for item in spec["non_field_attributes"]:
        counts[item["category"]]["non_field"] += 1
    for item in spec["snapshot_metadata"]:
        counts[item["category"]]["metadata"] += 1
    return counts


def blocks(spec: dict) -> dict[str, list[str]]:
    out: dict[str, list[str]] = {}
    a = spec["adoption"]
    out["adoption"] = [f"- `{a['id']}`（{a['date']}・{a['by']}）: {a['scope']}", "  - 原則:"] + [f"    - {p}" for p in a["principles"]] + [
        f"  - 仕様案（diagnostics-replay-api-design.json）の判断事項: {'、'.join(a['decisions_in_diagnostics_spec'])}"]
    counts = category_counts(spec)
    totals = {kind: sum(c[kind] for c in counts.values()) for kind in COUNT_KINDS}
    out["categories"] = _table(["分類", "意味", *COUNT_KINDS.values(), "計"],
                               [[f"`{c}`", label, *(counts[c][k] for k in COUNT_KINDS), sum(counts[c].values())] for c, label in spec["categories"].items()]
                               + [["計", "", *(totals[k] for k in COUNT_KINDS), sum(totals.values())]])
    out["game-state"] = _table(["GameState の項目", "分類", "根拠", "確かめ"],
                               [[f"`{name}`", item["category"], item["basis"], item["verify"]] for name, item in spec["explicit_types"]["GameState"].items()])
    rows = []
    for type_name, fields in spec["explicit_types"].items():
        if type_name == "GameState":
            continue
        for name, item in fields.items():
            rows.append([f"`{type_name}.{name}`", item["category"], item["basis"]])
    out["explicit-types"] = _table(["項目", "分類", "根拠"], rows)
    out["value-records"] = [f"分類はすべて `value`。{spec['value_record_basis']}", ""] + _table(
        ["型", "項目"], [[f"`{t}`", ", ".join(fields) or "（項目なし。型の印だけ）"] for t, fields in spec["value_record_types"].items()])
    out["non-field"] = _table(["名前", "分類", "根拠", "確かめ"],
                              [[f"`{i['name']}`", i["category"], i["basis"], i.get("verify", "")] for i in spec["non_field_attributes"] + spec["snapshot_metadata"]])
    out["json-types"] = _table(["Python の型", "JSON", "復元"], [[t["python"], t["json"], t["restore"]] for t in spec["json_types"]])
    out["header"] = _table(["項目", "必須", "意味"], [[f"`{h['item']}`", h["required"], h["meaning"]] for h in spec["header"]])
    fmt = spec["format"]
    lim = spec["limits"]
    out["limits"] = [f"- 形式: `{fmt['key']}` = {fmt['version']}（{fmt['name']}。{fmt['status']}）。{fmt['note']}"] + [f"- {k}: {v}" for k, v in lim.items()]
    out["boundary"] = [f"- {b}" for b in spec["boundary"]]
    out["states"] = _table(["状態", "保存", "復元のあとに許す操作"], [[s["state"], s["save"], s["after_restore"]] for s in spec["states"]])
    out["restore-steps"] = (_table(["段", "名前", "内容", "止まったときの結果"], [[s["step"], s["name"], s["detail"], s["failure"]] for s in spec["restore_steps"]])
                            + [""] + _table(["結果", "意味"], [[f"`{r['id']}`", r["meaning"]] for r in spec["results"]]) + ["", f"- 文: {spec['messages']}"])
    out["verification"] = (_table(["ID", "場面", "盤面"], [[v["id"], v["case"], v["fixture"]] for v in spec["verification"]]) + [""]
                           + [f"- {c}" for c in spec["comparison"]])
    out["units"] = _table(["単位", "状態", "内容", "依存", "範囲", "回帰テスト", "完了基準"],
                          [[u["id"], u["status"], u["title"], ", ".join(u["depends"]) or "なし", u["scope"], u["tests"], u["done"]] for u in spec["units"]])
    out["decisions"] = _table(["ID", "問い", "選択肢", "推奨（仕様案の作成者の提案）", "状態", "採用した内容"],
                              [[d["id"], d["question"], d["options"], d["recommendation"], f"{d['status']}（{d['adoption']}）" if d.get("adoption") else d["status"],
                                d.get("adopted", "")] for d in spec["decisions"]])
    impl = spec["implementation_adoption"]
    out["implementation-adoption"] = [f"- `{impl['id']}`（{impl['date']}・{impl['by']}）: {impl['scope']}", f"  - 判断事項: {'、'.join(impl['decisions'])}",
                                      f"  - 実装した単位: {'、'.join(impl['units'])}（{impl['implemented_in']}）", f"  - 実装しない単位: {'、'.join(impl['not_implemented'])}"]
    return out


DESIGN_BLOCKS = ("adoption", "categories", "game-state", "explicit-types", "value-records", "non-field", "json-types", "header", "limits", "boundary", "states",
                 "restore-steps", "verification")
PLAN_BLOCKS = ("implementation-adoption", "units", "decisions")
_BLOCK = re.compile(r"(<!-- generated:(?P<name>[a-z-]+) begin -->\n)(?P<body>.*?)(<!-- generated:(?P=name) end -->)", re.DOTALL)


def render_into(text: str, rendered, names) -> tuple[str, list[str]]:
    problems = []
    found = [m.group("name") for m in _BLOCK.finditer(text)]
    for name in names:
        if found.count(name) != 1:
            problems.append(f"生成区画 {name} が {found.count(name)} 個（1 個であること）")
    problems += [f"知らない生成区画 {name}" for name in found if name not in names]
    text = _BLOCK.sub(lambda m: m.group(1) + "\n".join(rendered[m.group("name")]) + "\n" + m.group(4) if m.group("name") in rendered else m.group(0), text)
    return text, problems


# ---------------------------------------------------------------- 確かめ


def code_fields() -> dict[str, list[str]]:
    """コードの型と項目（kyuura_engine/state.py の dataclass と rules.RuleSet）。"""
    from kyuura_engine import rules, state

    found = {name: [f.name for f in dataclasses.fields(value)] for name, value in vars(state).items()
             if isinstance(value, type) and dataclasses.is_dataclass(value) and value.__module__ == state.__name__ and value.__name__ == name}
    found["RuleSet"] = [f.name for f in dataclasses.fields(rules.RuleSet)]
    return found


def coverage_problems(spec: dict, code: dict[str, list[str]] | None = None) -> list[str]:
    """分類表とコードの型・項目の名前の照合（件数ではなく名前）。"""
    code = code_fields() if code is None else code
    problems = []
    explicit, records = spec["explicit_types"], spec["value_record_types"]
    for name in sorted(set(explicit) & set(records)):
        problems.append(f"型 {name} が主要な型と値の記録の型の両方にある")
    classified = set(explicit) | set(records)
    for name in sorted(set(code) - classified):
        problems.append(f"型 {name} に分類がない（コードに加わった型）")
    for name in sorted(classified - set(code)):
        problems.append(f"分類の型 {name} がコードにない")
    for name in sorted(set(code) & classified):
        listed = list(explicit[name]) if name in explicit else list(records[name])
        for field in sorted(set(code[name]) - set(listed)):
            problems.append(f"{name}.{field} に分類がない（コードに加わった項目）")
        for field in sorted(set(listed) - set(code[name])):
            problems.append(f"{name}.{field} の分類があるが、コードにない")
    return problems


def codec_problems(spec: dict, codec: dict[str, dict[str, str]] | None = None) -> list[str]:
    """分類表と、実装の型の対応表（kyuura_engine.snapshot.codec_fields）の照合。型・項目・扱い（value・resolve・absent）が名前で同じこと。"""
    if codec is None:
        from kyuura_engine import snapshot

        codec = snapshot.codec_fields()
    problems = []
    expected: dict[str, dict[str, str]] = {name: dict.fromkeys(fields, "value") for name, fields in spec["value_record_types"].items()}
    for name, fields in spec["explicit_types"].items():
        if name != "RuleSet":  # GameState.rules の識別から解決する（値の型の対応表に入れない）
            expected[name] = {field: item["category"] for field, item in fields.items()}
    for name in sorted(set(expected) | set(codec)):
        if name not in codec:
            problems.append(f"型 {name} が実装の型の対応表にない")
        elif name not in expected:
            problems.append(f"実装の型の対応表の型 {name} に分類がない")
        elif codec[name] != expected[name]:
            problems.append(f"型 {name} の項目・扱いが、分類表と実装の型の対応表で違う")
    return problems


def spec_problems(spec: dict) -> list[str]:
    problems = []
    if spec.get("approval") != "not_approved" or spec.get("status") != "proposed":
        problems.append("仕様案が承認済みになっている（原則の採用は adoption に書く）")
    cats = set(spec["categories"])
    for type_name, fields in spec["explicit_types"].items():
        for name, item in fields.items():
            if item.get("category") not in cats:
                problems.append(f"{type_name}.{name} の分類 {item.get('category')} が語彙にない")
            if not item.get("basis") or not item.get("verify"):
                problems.append(f"{type_name}.{name} に根拠か確かめがない")
    for item in spec["non_field_attributes"] + spec["snapshot_metadata"]:
        if item.get("category") not in cats:
            problems.append(f"{item['name']} の分類が語彙にない")
    gs = spec["explicit_types"]["GameState"]
    if gs["rng"]["category"] != "value":
        problems.append("乱数の状態を値で保存しない（正確に保存・復元する原則）")
    if gs["pending_moves"]["category"] != "absent":
        problems.append("pending_moves を保存の境界で存在してはいけないものにしていない")
    for name in ("definitions", "effects", "rules", "conventions"):
        if gs[name]["category"] != "resolve":
            problems.append(f"GameState.{name} を登録から解決していない（入力からオブジェクトを作らない原則）")
    if spec["explicit_types"]["CardInstance"]["uid"]["category"] != "value":
        problems.append("カードの uid を値で保存しない（構築盤面では作り直せない。名前・場所から付け直さない）")
    if gs["decision"]["category"] != "value" or spec["explicit_types"]["PendingDecision"]["context"]["category"] != "value":
        problems.append("決定待ち（決定と context）を保存しない")
    if spec["format"]["key"] in ("format_version", "kyuura_replay_format", "kyuura_view_format"):
        problems.append("スナップショットの形式の版の名前が、ほかの形式と同じ")
    halted = [s for s in spec["states"] if "HALTED" in s["state"] or "途中停止" in s["state"]]
    if not halted or not all(s["save"] for s in halted) or not all("解除" in s["after_restore"] or "同上" in s["after_restore"] for s in halted):
        problems.append("停止の状態を保存でき、解除しないことが書かれていない")
    steps = [s["step"] for s in spec["restore_steps"]]
    if steps != list(range(1, len(steps) + 1)):
        problems.append("復元の段の番号が連続していない")
    results = {r["id"] for r in spec["results"]}
    for s in spec["restore_steps"]:
        for word in re.findall(r"(?<![A-Za-z])[a-z_]+(?![A-Za-z])", s["failure"]):
            if word not in results:
                problems.append(f"段 {s['step']} の結果 {word} が結果の語彙にない")
    if "internal_error" not in results:
        problems.append("内部エラーの結果がない")
    for d in spec["decisions"]:
        if d.get("status") == "adopted":
            if d.get("adoption") != spec["implementation_adoption"]["id"] or d["id"] not in spec["implementation_adoption"]["decisions"] or not d.get("adopted"):
                problems.append(f"判断事項 {d['id']} の採用の記録（adoption・adopted）がない")
        elif d.get("status") != "pending":
            problems.append(f"判断事項 {d['id']} の状態 {d.get('status')} が pending・adopted でない")
    impl = spec["implementation_adoption"]
    if {u["id"] for u in spec["units"] if u.get("status") == "implemented"} != set(impl["units"]):
        problems.append("実装した単位と、採用の記録の単位が違う")
    if any(u.get("status") not in ("implemented", "planned") for u in spec["units"]):
        problems.append("単位の状態が implemented・planned でない")
    units = {u["id"]: u for u in spec["units"]}
    order = [u["id"] for u in spec["units"]]
    for u in spec["units"]:
        for dep in u["depends"]:
            if dep not in units:
                problems.append(f"単位 {u['id']} の依存 {dep} がない")
            elif order.index(dep) > order.index(u["id"]):
                problems.append(f"単位 {u['id']} があとの単位 {dep} に依存する")
        if not u["tests"] or not u["done"]:
            problems.append(f"単位 {u['id']} に回帰テスト・完了基準がない")
    sets = " ".join(v["fixture"] for v in spec["verification"])
    for key in ("CS-KYUURA-CURRENT@1", "CS-KYUURA-PLAY-S2A@1", "CS-KYUURA-PLAY-PO@1"):
        if key not in sets:
            problems.append(f"検証の計画に集合 {key} がない")
    return problems + coverage_problems(spec) + codec_problems(spec)


def check(written: dict, design: str, plan: str) -> list[str]:
    spec = build()
    problems = []
    if written != spec:
        problems.append("書いた JSON が、作り直した仕様案と違う（--write で作り直す）")
    rendered = blocks(spec)
    for label, text, names in (("設計の文書", design, DESIGN_BLOCKS), ("実装計画の文書", plan, PLAN_BLOCKS)):
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
        for path, names in ((DESIGN, DESIGN_BLOCKS), (PLAN, PLAN_BLOCKS)):
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

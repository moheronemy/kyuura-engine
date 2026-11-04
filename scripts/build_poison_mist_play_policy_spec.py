"""［ポイズンミスト］とどくの量の問い（PO1〜PO3）を扱う続行規約の仕様案 docs/poison-mist-play-policy-spec.json と、その文書 docs/poison-mist-play-policy-spec.md を作る・確かめる
（仕様案だけ。エンジンの動作・同梱の規約集合は変えない）。

    python scripts/build_poison_mist_play_policy_spec.py --write   # 仕様案の JSON と文書を、このスクリプトの記述から書き出す
    python scripts/build_poison_mist_play_policy_spec.py --check   # 書き出した JSON・文書が作り直したものと同じか、参照（場面・停止コード・研究・判断事項・テスト・コード・計測の局）に
                                                                   # 欠け・不正がないか、対象と除外の対応に漏れ・重なりがないか、規約を登録・有効化していないか

- 仕様の唯一の元は、このスクリプトの定数。JSON と文書（表・本文）はどちらもここから作る（二重に手で書かない。S2a の仕様案 scripts/build_play_policy_s2a_spec.py と同じ方式）。
- 場面 ID・停止コードは停止の方針の台帳（docs/stop-policy-classification.json）と同梱の場面の一覧（kyuura_engine/data/convention_records.json）の ID を引くだけで、台帳を書き換えない。
  まだ台帳にない事例は ``proposed_cases``（実装の段階で台帳に加える案）として分けて書く。
- 仕様案の状態は ``proposal``、承認は ``not_approved``。2026-11-05 の作業の指示（作業の承認）を、この仕様案の承認として記録しない（--check が確かめる）。
"""

from __future__ import annotations

import argparse
import json
import pathlib
import re
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
OUTPUT = ROOT / "docs" / "poison-mist-play-policy-spec.json"
DOCUMENT = ROOT / "docs" / "poison-mist-play-policy-spec.md"
LEDGER = ROOT / "docs" / "stop-policy-classification.json"
PLAN = ROOT / "docs" / "play-policy-family-plan.json"
RECORDS = ROOT / "kyuura_engine" / "data" / "convention_records.json"
RESEARCH = ROOT / "kyuura_engine" / "data" / "research_links.json"

SCHEMA_VERSION = 1
SPEC_STATUS = "proposal"  # 仕様案の状態（採用の判断の前）
SPEC_APPROVAL = "not_approved"  # 仕様案の中身の承認。作業の承認（WORK_APPROVAL）と混ぜない

BASE = {
    "commit": "7548ba46b37142983414688a215f4cbdef45161e",
    "version": "0.143.0",
    "published_on": "origin/claude/play-policy-s2a-impl（v0.143 の最後のコミット。2026-11-05 に fetch して確かめた）",
    "origin_main": "816bcffb86edeb3ea713ee08818a070e036fe0a8",
    "origin_main_contains_base": False,
    "origin_main_note": "v0.140 のマージ（PR #35）。v0.141〜v0.143（S1・S2a）を含まない（origin/main は 7548ba4 の祖先）",
    "why": "S2a の実装（規約の照会・規約を当てた記録・開発用の集合）を含む公開済みのコミットが 7548ba4 だけなので、main ではなくこれを基点にした",
    "branch": "claude/sc2-integrity-poison-mist-spec",
}
KYUURA = {"read_only": True, "note": "kyuura は読んでいない（この仕様は、エンジンの記録・固定した研究基準の写しの参照だけ）。変更・コミット・push をしていない"}

WORK_APPROVAL = {
    "status": "user_agreed",
    "date": "2026-11-05",
    "scope": ("作業の進め方: SC2 の状態の整合の不具合の修正（v0.144）・PO1〜PO3 をまとめて扱う続行規約の仕様案の作成・lockstep の記録の技術課題の記録。"
              "PO1〜PO3・TK1・SC2 の裁定への承認ではなく、この仕様案の中身の承認でもない"),
}
SPECIFICATION_APPROVAL = {
    "status": SPEC_APPROVAL,
    "note": "この仕様案（3 規約の中身・除外・依存・実装の段階）は、利用者の採用の判断を待つ。採用まで、エンジンに登録・有効化しない（--check が登録のないことを確かめる）",
}

GROUND_RULES = [
    "厳密側の現行集合 CS-KYUURA-CURRENT@1 と、開発用の集合 CS-KYUURA-PLAY-S2A@1 は、同じ ID・版のまま中身を変えない。PO1〜PO3 では従来どおり止まる",
    "採用されたら、新しい規約（ID@1）と、それを加えた新しい集合（新しい ID または版）で入れる。既存の集合の中身を書き換えない",
    "続行側は、採用された規約の対象の事例だけ続ける。対象でない事例・除外の事例は、続行側でも今の停止コードで止まる",
    "研究上の未解決（PO1・PO2・PO3）は未解決のまま。続行規約は研究上の解決・公式の裁定ではない",
    "カード固有の読み方を、根拠なくすべてのどく・すべての持続する効果へ一般化しない（［ポイズンミスト］の規約は［ポイズンミスト］の型の効果だけ）",
    "機能不足・技術的な制限・不具合を、規約で解消したことにしない",
    "停止の例外を捕まえて無視する構造にしない。続行は、止める理由を作る分岐の手前で規約を引き、規約があれば止める理由を作らない形にする（S2a と同じ）",
]

PRINCIPLES = [
    {"id": "P-CHECK-TIME-AMOUNT", "name": "どくの量はポケモンチェックの時点で、性質 → 場の効果 → 受ける側の減少の順に決める",
     "text": ("ポケモンチェックの 2 で受ける「どく」のダメージは、その時点の場で、(1) どく状態の性質（通常の 10・ワザで決まった量・ダメージカウンターの数にかける数。p.322 の「どく状態にかかるもの」）、"
              "(2) その時点にはたらく場の効果（［ポイズンミスト］の「20ダメージになる」。いつどく状態になったかを問わない）、(3) 受けるダメージを変える効果（鋼エネルギーの「-10」）の順に決める"),
     "conventions": ["PC-POISON-AMOUNT-ORDER", "PC-POISON-MIST-TARGETS"]},
    {"id": "P-MIST-SOURCE-PRESENCE", "name": "［ポイズンミスト］の効果は、使ったポケモンが場にいるあいだだけはたらく",
     "text": ("［ポイズンミスト］の効果は、使ったポケモン（発生源）に結び付く（説明が、発生源のねむり・マヒ・こんらんで効果が消えると書く）。発生源が場をはなれたら効果は終わる。"
              "場にいるまま特殊能力が消えた場合（かがくへんかガス・退化など）は、この原則で決めない（別の問い）"),
     "conventions": ["PC-POISON-MIST-SOURCE-LEFT"]},
]

# ---------------------------------------------------------------------------------------------------------------------------------------------------
# 3 規約
# ---------------------------------------------------------------------------------------------------------------------------------------------------
CONVENTIONS = [
    {
        "id": "PC-POISON-AMOUNT-ORDER",
        "version": 1,
        "label": "どくの量を変える効果の順番",
        "principle": "P-CHECK-TIME-AMOUNT",
        "question": ("ポケモンチェックの「どく」のダメージに、量を変える効果（特殊などくの決まった量・「どくどくエキス」のカウンターの数の 2 倍・［ポイズンミスト］の「20ダメージになる」・"
                     "鋼エネルギーの「-10」）が 2 つ以上当てはまり、当てはめる順番で量が変わるとき、どの順番で当てはめるか（PO1）"),
        "statement": ("どく状態の性質（決まった量、またはダメージカウンターの数にかける数）で量を求め、次に［ポイズンミスト］がはたらけばその量を 20 に置きかえ、最後に受けるダメージの"
                      "「-10」（鋼エネルギー）を当てはめる。この順番は、量の効果の組み合わせによらず同じ"),
        "applies_when": "effects.poison_check_amount の当てはめ方（effects._poison_orders）ごとの量が 2 つ以上ある（今 UNRESOLVED_POISON_CHANGE_ORDER で止める条件そのもの）",
        "codes": ["UNRESOLVED_POISON_CHANGE_ORDER"],
        "ruling_ids": ["PO1"],
        "decision_refs": ["DEC-DAMAGE-READINGS"],
        "targets": [{"scene": "UNRESOLVED_POISON_CHANGE_ORDER", "coverage": "full",
                     "note": "［ポイズンミスト］のある組（観測 1 局: どくどくエキスと［ポイズンミスト］。20・40）と、ない組（どくどくエキスと鋼エネルギー。10・0。構築の盤面で確かめた）の両方"}],
        "proposed_cases": [],
        "excludes": [
            {"what": "性質の違うどく状態への上書き（TP3）", "scene": "UNRESOLVED_SPECIAL_POISON_OVERWRITE",
             "reason": "量の順番ではなく、どく状態をどう置きかえるかの問い（共通規約の設計案の PC-ORDER-OVERLAP の対象。この仕様では扱わない）"},
            {"what": "受けるダメージを変える特殊能力をどくに当てはめるか（KA1）", "scene": "UNRESOLVED_POISON_DAMAGE_RECEIVED_POWER",
             "reason": "どの効果を当てはめるかの問い（PC-NON-ATTACK-DAMAGE-MODIFIERS の対象）。順番の規約に入れない"},
        ],
        "details": [
            ["今の量の扱い（変えない部分）", "特殊などく・［ポイズンミスト］は鋼エネルギーより先（v0.78 からの既存の扱い。effects._poison_orders の並べかえの制限）。この規約はそれを含む全体の順番を 1 つに決める"],
            ["組ごとの結果", ("どくどくエキス（10 × 2）と［ポイズンミスト］: 20。特殊などく 30（さんばいどく）と［ポイズンミスト］: 20。どくどくエキスと鋼エネルギー: 20 − 10 = 10。"
                         "どくどくエキス・［ポイズンミスト］・鋼エネルギー: 10。特殊などくとかける数は同時に持たない（上書きは TP3 で止める）")],
            ["「〜になる」の読み方", ("［ポイズンミスト］の「受ける「どく」のダメージは、20ダメージになる」を、どく状態の性質で決まった量を置きかえる場の効果として読む（性質の量に重ねて倍にしない）。"
                                 "かける数（「どくどくエキス」の「のせるダメージカウンターの数が、2倍になる」）は、どく状態の性質（p.322 の「どく状態にかかるもの」）として先に当てはめる")],
            ["0 以下", "鋼エネルギーの「-10」で 0 になる量は 0（今の energy_received_damage のまま。負にしない）"],
            ["［ポイズンミスト］の当てはまる相手", "PC-POISON-MIST-TARGETS（PO2）・PC-POISON-MIST-SOURCE-LEFT（PO3）が決める。この規約は、当てはまると決まったあとの順番だけ"],
        ],
        "strict": "当てはめ方で量が変われば、ポケモンチェックの前に HALTED（UNRESOLVED_POISON_CHANGE_ORDER）。今のまま",
        "continuation": ("止めずに、規約の順番の量でどくのダメージを与える。どくのダメージの前に、ログに規約を当てたこと（convention_applied: 規約 ID・版・場面・ポケモンの番号・量）を書く"),
        "depends_on": [],
        "related": ["PC-POISON-MIST-TARGETS", "PC-POISON-MIST-SOURCE-LEFT", "PC-NON-ATTACK-DAMAGE-MODIFIERS", "PC-ORDER-OVERLAP"],
        "conflicts_with": [],
        "sites": ["kyuura_engine/effects.py::poison_check_amount", "kyuura_engine/effects.py::_poison_orders", "kyuura_engine/procedures.py::pokemon_check_poison",
                  "kyuura_engine/procedures.py::_pokemon_check_plan", "kyuura_engine/procedures.py::mid_check_knockout_divergence"],
        "common_implementation": ("poison_check_amount の PO1 の分岐の手前で続行規約を引き、規約があれば規約の並び（性質 → ［ポイズンミスト］→ 鋼エネルギー）の量を返す。"
                                  "返す値に当てた規約を持たせ、実際のダメージの処理（pokemon_check_poison）だけが規約を当てた記録を書く（先読み・確かめは書かない）"),
        "card_specific": "なし（量の効果は登録の型・どく状態の性質で識別する）",
        "tests_existing": ["tests/test_damage_reactions_poison_sleep_v0_119.py::test_doubled_poison_with_mist_is_po1_and_metal_is_fixed_last",
                           "tests/test_damage_reactions_poison_sleep_v0_119.py::test_check_knockout_uses_the_same_amount"],
        "tests_new": [
            "続行側: どくどくエキスと［ポイズンミスト］で 20、どくどくエキスと鋼エネルギーで 10、3 つで 10。convention_applied と poison_damage の amount・amount_before・multiplier・poison_mists",
            "続行側: 量が 1 つに決まる組（通常のどくと鋼エネルギーなど）では規約を当てた記録を書かない（厳密側と同じログ）",
            "厳密側: 同じ盤面で今と同じ HALTED（コード・理由の文・ログ・乱数）",
            "ポケモンチェックの前の確かめ（きぜつの見積もり・PK1・［ずらかる］SC1・v0.144 の SC2）と実際のダメージが同じ量",
            "くろこげマーカーのコインの前の確かめ（すべての結果の組）が、規約の量で確かめること",
        ],
        "difference_from_current": "今止まる組だけ、止めずに規約の順番の量を与える。量が 1 つに決まる組は状態・乱数・ログとも今と同じ",
        "recommendation": {"option": "性質 → ［ポイズンミスト］→ 鋼エネルギー",
                           "reason": ("p.322 が量を変えるワザの効果を「どく状態にかかるもの」（どく状態の性質）として扱うので、性質を先に決め、そのあとにはたらく場の効果、最後に受けるダメージを"
                                      "変える効果、という並びは、今の既存の扱い（特殊などく・［ポイズンミスト］は鋼エネルギーより先）を延ばしたもの。組ごとの例外がない")},
        "alternatives": [
            {"option": "［ポイズンミスト］を先、かける数をあと（どくどくエキスと［ポイズンミスト］で 40）", "reason": "「20ダメージになる」を基本の量の置きかえとして読む読み方"},
            {"option": "鋼エネルギーをかける数より先（どくどくエキスと鋼エネルギーで 0）", "reason": "受ける側の効果を先に当てる読み方。今の既存の扱い（性質の量は鋼エネルギーより先）と合わない"},
            {"option": "［ポイズンミスト］のある組だけを規約にし、ない組（どくどくエキスと鋼エネルギー）は止める", "reason": "観測のない組を対象から外す（事例を分ける）"},
        ],
        "unverified": ["特殊などく 30（neo2-010 のさんばいどく）と［ポイズンミスト］の組で今 PO1 になることは、コード（_poison_orders）を読んで確かめただけ（盤面は作っていない）",
                       "公式資料に順番の記述がないことの再確認（研究上は未解決のまま）"],
        "observed_games": 1,
    },
    {
        "id": "PC-POISON-MIST-TARGETS",
        "version": 1,
        "label": "［ポイズンミスト］の当てはまるどく",
        "principle": "P-CHECK-TIME-AMOUNT",
        "question": "［ポイズンミスト］の「「どく」状態になったポケモン」に、この力を使う前からどく状態だったポケモンも当たるか（PO2）",
        "statement": "［ポイズンミスト］の効果は、ポケモンチェックの時点でどく状態のすべてのポケモン（お互いの場。いつ、何でどく状態になったかを問わない）が受ける「どく」のダメージに当てはまる",
        "applies_when": ("effects.poison_check_amount で、使う前からどく状態だったポケモン（PoisonMist.poisoned_before）に当てはめるかで量が変わる（今 UNRESOLVED_POISON_MIST_EARLIER_POISON で"
                         "止める条件そのもの）"),
        "codes": ["UNRESOLVED_POISON_MIST_EARLIER_POISON"],
        "ruling_ids": ["PO2"],
        "decision_refs": ["DEC-TEXT-READINGS"],
        "targets": [{"scene": "UNRESOLVED_POISON_MIST_EARLIER_POISON", "coverage": "full",
                     "note": "観測 11 局はどれも、使う前からの通常のどく（10）が［ポイズンミスト］で 20 になるかの組"}],
        "proposed_cases": [],
        "excludes": [
            {"what": "使ったポケモンが場をはなれた記録", "scene": "UNRESOLVED_POISON_MIST_SOURCE#source-left",
             "reason": "はたらくかは PC-POISON-MIST-SOURCE-LEFT が決める（この規約は、はたらく記録が当てはまる相手だけ）"},
        ],
        "details": [
            ["「なった」の読み方", ("「「どく」状態になったポケモン」を、ポケモンチェックの時点でどく状態であるポケモンとして読む。p.322 の例（「このワザによって、どく状態になったポケモンが…」）は"
                               "「このワザによって」で原因を限るが、［ポイズンミスト］の文には原因・時点の限定がない")],
            ["記録 poisoned_before", "状態の記録はそのまま（厳密側が使う）。続行側の量の判断では使わない"],
            ["使ったあとに回復して、またどく状態になったポケモン", "今も「使ったあとのどく」（conditions.py が poisoned_before から外す）。規約のもとでも同じ 20"],
            ["量が同じ組", "使う前からの特殊などく 20 は、当てはめても量が同じなので今も止めない（規約を当てた記録も書かない）"],
            ["どくの量の順番", "当てはまると決まったあとの量は PC-POISON-AMOUNT-ORDER の順番（この規約だけを採るなら、順番で量が変わる組は PO1 で止まる）"],
        ],
        "strict": "当てはめるかで量が変われば、ポケモンチェックの前に HALTED（UNRESOLVED_POISON_MIST_EARLIER_POISON）。今のまま",
        "continuation": "止めずに、使う前からどく状態だったポケモンにも当てはめた量を与える。どくのダメージの前に convention_applied（規約 ID・版・場面・ポケモンの番号・量・記録の発生源）",
        "depends_on": [],
        "related": ["PC-POISON-AMOUNT-ORDER", "PC-POISON-MIST-SOURCE-LEFT"],
        "conflicts_with": [],
        "sites": ["kyuura_engine/effects.py::poison_check_amount", "kyuura_engine/effects.py::CoinPoisonMistUntilNextTurn", "kyuura_engine/conditions.py::poison",
                  "kyuura_engine/procedures.py::pokemon_check_poison"],
        "common_implementation": "poison_check_amount の PO2 の分岐の手前で続行規約を引き、規約があれば「当てはめる」読み方の量を返す（PO1 と同じ返し方・記録の書き方）",
        "card_specific": "［ポイズンミスト］の型（CoinPoisonMistUntilNextTurn）の記録だけ。ほかの持続する効果へ広げない",
        "tests_existing": ["tests/test_damage_reactions_poison_sleep_v0_119.py::test_earlier_poison_is_po2_only_when_the_amount_differs",
                           "tests/test_damage_reactions_poison_sleep_v0_119.py::test_new_poison_takes_twenty"],
        "tests_new": [
            "続行側: 使う前からの通常のどく（自分の場・相手の場）が 20。convention_applied と poison_damage の poison_mists",
            "続行側: 使ったあとのどく・使う前からの特殊などく 20 では規約を当てた記録を書かない",
            "厳密側: 同じ盤面で今と同じ HALTED",
            "保存（形式 35）・観測・clone・pickle のあとに同じ量（記録 poisoned_before は変えない）",
        ],
        "difference_from_current": "今止まる場面だけ、止めずに 20 を与える",
        "recommendation": {"option": "ポケモンチェックの時点でどく状態のすべてのポケモンに当てはめる",
                           "reason": ("文に原因・時点の限定がなく、効果の対象が「ポケモンチェックで受けるどくのダメージ」なので、ポケモンチェックの時点の状態で決める読み方が文に近い。"
                                      "履歴（いつどく状態になったか）を使わずに決まり、量の規約（PC-POISON-AMOUNT-ORDER）と同じ原則（時点で決める）になる")},
        "alternatives": [
            {"option": "使ったあとに新しくどく状態になったポケモンだけ（今の poisoned_before で外す）", "reason": "「なった」を変化（使ったあとにどく状態になった）として読む読み方"},
        ],
        "unverified": ["公式資料・カードの解説に、使う前からのどくについての記述がないことの再確認（研究上は未解決のまま）"],
        "observed_games": 11,
    },
    {
        "id": "PC-POISON-MIST-SOURCE-LEFT",
        "version": 1,
        "label": "［ポイズンミスト］の発生源が場をはなれたとき",
        "principle": "P-MIST-SOURCE-PRESENCE",
        "question": "［ポイズンミスト］を使ったポケモンが場をはなれたあとも、「次の自分の番の始めまで」の効果が続くか（PO3 のうち、発生源が場にいない場合）",
        "statement": ("［ポイズンミスト］を使ったポケモンが場をはなれたら（きぜつ・手札や山札にもどる・トラッシュなど）、その記録の効果は終わる（そのあとのポケモンチェックで当てはめない）。"
                      "場にいるまま特殊能力が消えた記録（かがくへんかガス・退化など）は、この規約の対象外"),
        "applies_when": ("effects.poison_check_amount で、中断の印（PoisonMist.interrupted）のある記録の効果が続くかで量が変わり（今 UNRESOLVED_POISON_MIST_SOURCE で止める条件）、"
                         "その記録の発生源の番号のポケモンが今場にいない"),
        "codes": ["UNRESOLVED_POISON_MIST_SOURCE"],
        "ruling_ids": ["PO3"],
        "decision_refs": ["DEC-LASTING-READINGS"],
        "targets": [{"scene": "UNRESOLVED_POISON_MIST_SOURCE#source-left", "coverage": "full",
                     "note": "台帳にまだない事例（proposed_cases）。観測 7 局はどれもこの事例（使ったポケモンが、同じ番にガスばくはつの自分へのダメージできぜつした）"}],
        "proposed_cases": [
            {"id": "UNRESOLVED_POISON_MIST_SOURCE#source-left", "parent": "UNRESOLVED_POISON_MIST_SOURCE",
             "condition": "中断の印のある［ポイズンミスト］の記録の発生源（pokemon_id）のポケモンが、ポケモンチェックの時点で場にいない",
             "mechanism": "pokemon_check_halt", "secret_dependency": "public_only（記録・場・どく状態はどれも公開）"},
            {"id": "UNRESOLVED_POISON_MIST_SOURCE#power-lost", "parent": "UNRESOLVED_POISON_MIST_SOURCE",
             "condition": "中断の印のある［ポイズンミスト］の記録の発生源のポケモンが、ポケモンチェックの時点で場にいる（かがくへんかガス・退化・姿の変化で特殊能力が消えた、または消えたあともどった）",
             "mechanism": "pokemon_check_halt", "secret_dependency": "public_only"},
        ],
        "excludes": [
            {"what": "発生源が場にいるまま特殊能力が消えた記録", "scene": "UNRESOLVED_POISON_MIST_SOURCE#power-lost",
             "reason": ("「その効果も消える」をねむり・マヒ・こんらん以外の力の消え方へ広げるかの別の問い（v0.117 の QK1 と同じ形）。観測 0 局。続行側でも今のまま止める（9 章の選択肢 OC-PO-4）")},
            {"what": "ほかのカードの持続する効果の発生源の変化（かみつく・くろいまなざしなど）", "scene": "UNRESOLVED_JAW_CLAMP_SOURCE_RETURNED",
             "reason": "共通規約の設計案の PC-LASTING-SOURCE-CHANGE（proposal）の対象。この規約は［ポイズンミスト］の型だけで、候補を採用したことにしない"},
        ],
        "details": [
            ["「場をはなれた」の判定", ("ポケモンチェックの時点で、記録の発生源の番号（pokemon_id）のポケモンが場にいない。場のポケモンの番号は場に出るたびに新しくなるので、同じカードがもう一度"
                                     "場に出ても、もとの記録の発生源ではない")],
            ["中断の印の扱い", "今の poison_mist_upkeep の印（一度書いたら消さない）はそのまま。続行側の量の判断で、場にいない発生源の記録を「はたらかない」として扱う（状態を変えない）"],
            ["記録を消すか", ("推奨は、状態を変えない（量の判断で使わないだけ。記録は使ったプレイヤーの次の番の始めに今どおり消える）。厳密側と続行側で状態の形が同じになり、保存・観測が変わらない")],
            ["観測した局の形", ("7 局とも、マタドガスが［ポイズンミスト］を使い、同じ番にガスばくはつ（自分にも 30）できぜつし、かわりに出てきた相手の対戦ポケモンがどく状態になった。"
                              "6 局はその番の終わり、1 局は相手の番の終わりのポケモンチェックで止まった。規約のもとでは、かわりに出てきたポケモンのどくは 10")],
            ["発生源が 2 匹以上", "記録ごとに判断する。場にいる発生源の記録がはたらけば、量はそれで決まる（2 つ以上の記録は足さない。今のまま）"],
            ["PO2 との関係", "場にいない発生源の記録は当てはめないので、その記録について PO2 の問いは起こらない。はたらく記録の当てはまる相手は PC-POISON-MIST-TARGETS"],
        ],
        "strict": "続くかで量が変われば、ポケモンチェックの前に HALTED（UNRESOLVED_POISON_MIST_SOURCE）。今のまま（事例を分けても止め方・コードは同じ）",
        "continuation": ("発生源が場にいない記録は当てはめずに量を決め、止めない。どくのダメージの前に convention_applied（規約 ID・版・場面・ポケモンの番号・量・終わった記録の発生源）。"
                         "発生源が場にいる記録（#power-lost）で量が変わるなら、続行側でも今の停止コードで止める"),
        "depends_on": [],
        "related": ["PC-POISON-MIST-TARGETS", "PC-POISON-AMOUNT-ORDER", "PC-LASTING-SOURCE-CHANGE"],
        "conflicts_with": [],
        "sites": ["kyuura_engine/effects.py::poison_check_amount", "kyuura_engine/effects.py::poison_mist_upkeep", "kyuura_engine/effects.py::poison_mist_working",
                  "kyuura_engine/procedures.py::pokemon_check_poison"],
        "common_implementation": ("poison_check_amount の PO3 の分岐を、中断した記録ごとに事例（source-left・power-lost）へ分け、source-left の事例だけ続行規約を引く。"
                                  "事例の判定は、記録の発生源の番号が今場にいるか（新しい状態の項目は要らない）"),
        "card_specific": "［ポイズンミスト］の型（CoinPoisonMistUntilNextTurn）の記録だけ",
        "tests_existing": ["tests/test_damage_reactions_poison_sleep_v0_119.py::test_source_suppressed_is_po3",
                           "tests/test_damage_reactions_poison_sleep_v0_119.py::test_ends_on_status_and_expires_at_the_next_own_turn"],
        "tests_new": [
            "続行側: 使ったポケモンがきぜつした（ガスばくはつ・ワザのダメージ）・手札にもどった盤面で、記録を当てはめずに量が決まる。convention_applied",
            "続行側: 場にいるまま特殊能力が消えた（かがくへんかガス・退化）盤面は、今と同じ UNRESOLVED_POISON_MIST_SOURCE（#power-lost）",
            "続行側: 場をはなれた記録と、はたらく記録が両方ある盤面",
            "厳密側: どちらの事例も今と同じ HALTED",
            "台帳の事例を 2 つに分けたあと、同梱の場面の一覧と照会（事例を渡す）が合うこと",
        ],
        "difference_from_current": "今止まる場面のうち、発生源が場にいない記録だけ、止めずに当てはめない量を与える",
        "recommendation": {"option": "場をはなれたら効果は終わる",
                           "reason": ("説明が効果の終わりを発生源の状態（ねむり・マヒ・こんらん）に結び付けているので、発生源のいない効果を続けるより、発生源とともに終わる読み方が文の作りに近い。"
                                      "共通規約の設計案の PC-LASTING-SOURCE-CHANGE の推奨（場をはなれたら終わる）とも合う")},
        "alternatives": [
            {"option": "発生源によらず、次の自分の番の始めまで続く", "reason": "効果を場の記録とみなし、説明に書かれた終わり方（期限・特殊状態）だけで終える読み方"},
            {"option": "場にいるまま特殊能力が消えた記録（#power-lost）も同じく終わる", "reason": "「その効果も消える」を力が使えなくなるすべての場合へ広げる読み方。観測がなく、QK1 と同じ問いを先に決めることになる"},
        ],
        "unverified": ["公式資料・カードの解説に、使ったポケモンが場をはなれたときの記述がないことの再確認（研究上は未解決のまま）",
                       "#power-lost の盤面（かがくへんかガス）は既存のテストで止まることを確かめた。退化・姿の変化の盤面は作っていない"],
        "observed_games": 7,
    },
]

# 共通化しない問い（理由を添えて分ける）
SEPARATED = [
    {"question": "発生源が場にいるまま特殊能力が消えた［ポイズンミスト］の記録が続くか", "scene": "UNRESOLVED_POISON_MIST_SOURCE#power-lost",
     "reason": "力の消え方（かがくへんかガス・退化・姿の変化）ごとに読み方が分かれうる、QK1 と同じ形の問い。観測 0 局。この仕様案では止めたまま"},
    {"question": "受けるダメージを変える特殊能力（カブトアーマーなど）をどくに当てはめるか（KA1）", "scene": "UNRESOLVED_POISON_DAMAGE_RECEIVED_POWER",
     "reason": "どの効果を当てはめるかの問い。ワザ以外のダメージ全体の規約（PC-NON-ATTACK-DAMAGE-MODIFIERS）で扱う"},
    {"question": "性質の違うどく状態への上書き（TP3）・キョウのどくの順番", "scene": "UNRESOLVED_SPECIAL_POISON_OVERWRITE",
     "reason": "どく状態を与える側の順番・上書きの問い（PC-ORDER-OVERLAP の対象）。ポケモンチェックの量の規約に入れない"},
    {"question": "「どくをだす」でどく状態にする相手（PX1）", "scene": "UNRESOLVED_SECRETE_POISON_TARGET",
     "reason": "ワザの対象の文の読み方。どくの量の問いではない"},
]

RELATION_S2A = [
    ["ポケモンチェックの順番", "どくの量は 1 のあとの場で求める（今の _pokemon_check_plan）。3 規約は、その量の決め方だけを変え、1・2 の処理の順番・きぜつの判定の時点（PC-CHECK-KO-POINT）を変えない"],
    ["PC-CHECK-KO-POINT（きぜつ判定）", "2 のあとの HP 以上の判定に使う量が、規約の量になる。PK1 の違いの判定（mid_check_knockout_divergence）も同じ問い合わせの量を使うので、規約の有無で判定がずれない"],
    ["PC-CHECK-SIDE-ORDER（両側のコイン）", "くろこげマーカーのコインの前の確かめ（すべての結果の組）が、規約の量で確かめる。規約で PO1〜PO3 の停止がなくなると、コインの前に止まる組が減る"],
    ["v0.144 の SC2 の確かめ", "2 のあとにきぜつするポケモンの判定に規約の量を使う（同じ問い合わせ）。きぜつの処理で［ずらかる］の力がもどるなら、続行側でも今どおりダメージの前に SC2 で止める"],
    ["両方のきぜつ", "規約の量で両方のプレイヤーのポケモンが HP 以上になるなら、続行側でも今どおり UNRESOLVED_POKEMON_CHECK_DOUBLE_KNOCKOUT で止める（S2b の候補。この仕様の対象外）"],
]

STATE_SAVE_LOG = {
    "state": "新しい状態の項目はない（記録 PoisonMist の poisoned_before・interrupted と、どく状態の性質は今のまま）",
    "save": "書き出しの形式は 35 のまま。厳密側・続行側で同じ形",
    "log": ("規約を当てたときだけ、ポケモンチェックのどくのダメージ（poison_damage）の前に convention_applied を書く（規約 ID・版・場面・停止コード・ポケモンの番号 pokemon_id・量 amount・"
            "当てた／終わった記録の発生源 records）。conventions.APPLIED_FIELDS に amount・records を加える。先読み・確かめ・拒否したコマンドは書かない（S2a と同じ）"),
    "observation": "convention_applied は公開の記録（S2a と同じ）。新しい非公開の情報はない（量・記録・場・どく状態はどれも公開）",
    "audit": "tests/log_audit.py の s2a_problems と同じ形の独立な確かめ（規約の表を監査が別に持つ）: 当たる場面の数・量・記録の発生源がログから組み立てた値と合うこと",
}

SET_PROPOSAL = {
    "strict": {"id": "CS-KYUURA-CURRENT", "version": 1, "change": "なし（同じ ID・版・中身）"},
    "existing_development": {"id": "CS-KYUURA-PLAY-S2A", "version": 1, "change": "なし（同じ ID・版・中身。S2a の 5 規約だけ）"},
    "continuation": {
        "id": "CS-KYUURA-PLAY-PO", "version": 1, "usage": "development", "completeness": "halts_at_undecided",
        "members": "CS-KYUURA-PLAY-S2A@1 の規約（今の集合の 12 件と S2a の 5 件）と、採用した PO の規約（3 件まで）",
        "approval_of_members": "採用された規約だけを layer continuation・approval user_agreed で登録する。採用されなかった規約は登録しない（部分的な採用なら、その規約だけの集合にする）",
        "not_called": "すべての未決場面で止まらない完成したプレイ用の集合ではない（ほかの未決場面では今の停止コードで止まる）",
    },
    "version_policy": "既存の集合の中身を変えない。PO の規約を加えた集合は新しい ID で作る（集合の ID の S2A は S2a の 5 規約の意味を持つので、版を上げて加えない）",
}

STAGES = [
    {"id": "PO-0", "name": "事例の分割と照会の接続", "targets": ["台帳の事例 UNRESOLVED_POISON_MIST_SOURCE#source-left・#power-lost", "poison_check_amount の照会（事例を渡す）", "APPLIED_FIELDS・監査の表"],
     "prerequisites": ["この仕様案の採用"], "strict_invariant": "厳密側で、全体のテスト・lockstep・旧バッチが基点と同じ（停止コード・理由の文・ログ）",
     "continuation_done": "規約の登録の前に、続行側の集合でも今と同じに止まる"},
    {"id": "PO-1", "name": "量の規約（PO1・PO2）", "targets": ["PC-POISON-AMOUNT-ORDER", "PC-POISON-MIST-TARGETS"], "prerequisites": ["PO-0"],
     "strict_invariant": "厳密側のポケモンチェックの停止・ログ・乱数が今と同じ", "continuation_done": "PO1・PO2 の盤面で規約の量を与え、convention_applied を書く"},
    {"id": "PO-2", "name": "発生源の規約（PO3 の source-left）", "targets": ["PC-POISON-MIST-SOURCE-LEFT"], "prerequisites": ["PO-0"],
     "strict_invariant": "同上", "continuation_done": "場にいない発生源の記録を当てはめない。#power-lost は止まる"},
    {"id": "PO-3", "name": "計測と文書", "targets": ["新しい集合 CS-KYUURA-PLAY-PO@1"], "prerequisites": ["PO-1", "PO-2"],
     "strict_invariant": "全体のテスト（1 並列・モジュールごとに 1 プロセス）・lockstep・旧バッチ・延長戦が基点と同じ", "continuation_done": "10 章の計測を記録する（完走を保証しない）"},
]

# S2a の計測（v0.143。docs/play-policy-s2a-v0.143.md 8 章。続行側 CS-KYUURA-PLAY-S2A@1）で PO1〜PO3 で止まった 19 局（バッチ・組・席・seed・停止コード）。
# 席・seed は計測の記録のまま（選び直していない）。事例・規約は、この仕様案の作業で局をやり直して確かめた（10 章）
OBSERVED_CASES = [
    ("v0.119", "P119-D119", ["P119", "D119"], 1, "UNRESOLVED_POISON_MIST_EARLIER_POISON"),
    ("v0.119", "P119-D119", ["P119", "D119"], 2, "UNRESOLVED_POISON_MIST_SOURCE"),
    ("v0.119", "P119-D119", ["P119", "D119"], 3, "UNRESOLVED_POISON_MIST_SOURCE"),
    ("v0.119", "P119-D119", ["D119", "P119"], 0, "UNRESOLVED_POISON_MIST_EARLIER_POISON"),
    ("v0.119", "P119-D119", ["D119", "P119"], 1, "UNRESOLVED_POISON_MIST_SOURCE"),
    ("v0.119", "P119-D119", ["D119", "P119"], 2, "UNRESOLVED_POISON_MIST_EARLIER_POISON"),
    ("v0.119", "P119-W119", ["W119", "P119"], 0, "UNRESOLVED_POISON_MIST_EARLIER_POISON"),
    ("v0.119", "P119-W119", ["W119", "P119"], 2, "UNRESOLVED_POISON_MIST_EARLIER_POISON"),
    ("v0.119", "P119-W119", ["W119", "P119"], 3, "UNRESOLVED_POISON_CHANGE_ORDER"),
    ("v0.119", "P119-G119", ["P119", "G119"], 2, "UNRESOLVED_POISON_MIST_SOURCE"),
    ("v0.119", "P119-G119", ["G119", "P119"], 2, "UNRESOLVED_POISON_MIST_EARLIER_POISON"),
    ("v0.119", "P119-G119", ["G119", "P119"], 3, "UNRESOLVED_POISON_MIST_SOURCE"),
    ("v0.119", "P119-P31", ["P119", "P31"], 0, "UNRESOLVED_POISON_MIST_EARLIER_POISON"),
    ("v0.119", "P119-P31", ["P119", "P31"], 3, "UNRESOLVED_POISON_MIST_SOURCE"),
    ("v0.119", "P119-P31", ["P31", "P119"], 1, "UNRESOLVED_POISON_MIST_SOURCE"),
    ("v0.119", "P119-P31", ["P31", "P119"], 2, "UNRESOLVED_POISON_MIST_EARLIER_POISON"),
    ("v0.125", "W125-P119", ["W125", "P119"], 1, "UNRESOLVED_POISON_MIST_EARLIER_POISON"),
    ("v0.125", "W125-P119", ["W125", "P119"], 2, "UNRESOLVED_POISON_MIST_EARLIER_POISON"),
    ("v0.125", "W125-P119", ["P119", "W125"], 1, "UNRESOLVED_POISON_MIST_EARLIER_POISON"),
]
# 停止コード → 観測の局の事例（やり直しで確かめた。PO3 の 7 局は、どれも発生源の番号のポケモンが止まった時点で場にいない）
OBSERVED_SCENE = {
    "UNRESOLVED_POISON_MIST_EARLIER_POISON": "UNRESOLVED_POISON_MIST_EARLIER_POISON",
    "UNRESOLVED_POISON_MIST_SOURCE": "UNRESOLVED_POISON_MIST_SOURCE#source-left",
    "UNRESOLVED_POISON_CHANGE_ORDER": "UNRESOLVED_POISON_CHANGE_ORDER",
}
OBSERVED_NOTES = {
    "UNRESOLVED_POISON_MIST_EARLIER_POISON": "使う前からの通常のどく（10）。当てはめれば 20、当てはめなければ 10",
    "UNRESOLVED_POISON_MIST_SOURCE": "使ったマタドガスが同じ番のガスばくはつできぜつ（発生源は場にいない）。かわりに出てきたポケモンのどくが 20 か 10 か",
    "UNRESOLVED_POISON_CHANGE_ORDER": "どくどくエキス（× 2）のどくと［ポイズンミスト］。当てはめ方で 20・40",
}

MEASUREMENT = {
    "source": "docs/play-policy-s2a-v0.143.md 8 章（4,356 局。続行側 CS-KYUURA-PLAY-S2A@1 の停止 20 局）",
    "s2a_continuation_halts": 20,
    "covered_by_this_spec": 19,
    "not_covered": "UNSUPPORTED_TRANSFORM_COPIED_POWER 1 局（v0.49 A49-D49 seed 2。エンジンの未対応で、規約の対象にしない）",
    "now": "今回は一括の計測を繰り返さない（作業の指示）。19 局の内訳は、計測の記録の局を続行側の集合でやり直して確かめた（停止コード・止まった番・記録・発生源の場の有無）",
    "plan": [
        "実装の段階（PO-3）で、全 108 バッチ・seed 0〜3（4,356 局）を、CS-KYUURA-CURRENT@1・CS-KYUURA-PLAY-S2A@1・新しい集合の 3 つで走らせる（組・席・seed は選び直さない）",
        "厳密側と CS-KYUURA-PLAY-S2A@1 は v0.143 の記録（v0.144 の SC2 の修正の差があればその局）と同じであること",
        "新しい集合で、19 局の停止がなくなること・続けたあとにどの停止へ着くか・規約ごとの当たった局と回数・最初の差が convention_applied であること（ログのやり直しで比べる。lockstep の記録は集合を持たない: v0.144 の文書の技術課題）",
        "実装の前に、対象の経路を通るバッチ（v0.119・v0.125）を先に走らせ、対象を通らないバッチの成功を規約の確かめに数えない",
    ],
}

OPEN_CHOICES = [
    {"id": "OC-PO-1", "convention": "PC-POISON-AMOUNT-ORDER", "question": "量を変える効果の順番", "recommended": "性質 → ［ポイズンミスト］→ 鋼エネルギー",
     "alternatives": ["［ポイズンミスト］→ かける数 → 鋼エネルギー（40）", "鋼エネルギーをかける数より先", "［ポイズンミスト］のない組は止める"]},
    {"id": "OC-PO-2", "convention": "PC-POISON-MIST-TARGETS", "question": "使う前からのどくに当てはめるか", "recommended": "当てはめる（時点の状態で決める）",
     "alternatives": ["使ったあとに新しくどく状態になったポケモンだけ"]},
    {"id": "OC-PO-3", "convention": "PC-POISON-MIST-SOURCE-LEFT", "question": "発生源が場をはなれたら効果が終わるか", "recommended": "終わる",
     "alternatives": ["期限まで続く"]},
    {"id": "OC-PO-4", "convention": None, "question": "発生源が場にいるまま特殊能力が消えた記録（#power-lost）", "recommended": "この仕様では扱わない（続行側でも止める）",
     "alternatives": ["終わる（OC-PO-3 と同じ）", "続く"]},
    {"id": "OC-PO-5", "convention": None, "question": "集合の名前と、部分的な採用", "recommended": "新しい ID CS-KYUURA-PLAY-PO@1 に、採用した規約だけを加える",
     "alternatives": ["CS-KYUURA-PLAY-S2A の版を上げる（ID の意味が S2a の 5 規約からずれる）", "3 規約がそろうまで登録しない"]},
    {"id": "OC-PO-6", "convention": None, "question": "規約を当てたことをログに残すか", "recommended": "残す（convention_applied。S2a と同じ）", "alternatives": ["残さない"]},
]

UNVERIFIED = [
    "3 規約とも、公式資料に記述がないことの再確認はしていない（研究上の未解決は未解決のまま。続行規約は研究上の解決ではない）",
    "kyuura の記録は、固定した研究基準の写し・エンジンの記録の参照だけ（kyuura を読み直していない）",
    "特殊などく 30 と［ポイズンミスト］の PO1 は、コードを読んで確かめただけ",
    "#power-lost の退化・姿の変化の盤面、発生源が 2 匹以上の盤面は作っていない",
    "続けたあとにどの停止へ着くか（局の数）は、実装と計測のあとでしか分からない",
]

# 実行した確認（2026-11-05。この作業ブランチ。PYTHONUTF8=1・PYTHONHASHSEED=0。終了コードは各コマンドのもの）
VERIFICATION = {
    "executed": [
        "python scripts/build_poison_mist_play_policy_spec.py --check: problems=0（終了コード 0）",
        "わざと壊した仕様案（存在しない場面・対象の漏れ・規約の重なり・承認済みにした仕様・登録した規約・観測の局の数の違い）を --check が見つける: tests/test_poison_mist_play_policy_spec.py",
        ("19 局のやり直し（計測の記録の組・席・seed を、続行側の集合 CS-KYUURA-PLAY-S2A@1 で new_game から進めた）: 停止コードが記録と同じ。PO3 の 7 局は発生源の番号のポケモンが場にいない"
         "（ガスばくはつのきぜつ）、PO2 の 11 局は使う前からの通常のどく、PO1 の 1 局はどくどくエキスと［ポイズンミスト］（20・40）"),
        "構築の盤面: どくどくエキスのどくに鋼エネルギーをつけた盤面（［ポイズンミスト］なし）で、今 UNRESOLVED_POISON_CHANGE_ORDER（10・0）になる",
        "既存のテスト tests/test_damage_reactions_poison_sleep_v0_119.py（PO1〜PO3 の今の止め方）: 終了コード 0",
    ],
    "read_only": [
        "規約のもとでの量・ログ・監査は、実装していないので実行していない（仕様案）",
        "全体の対戦テスト・lockstep・一括の計測は、この仕様案のためには走らせていない（v0.144 の修正の検証は版の文書）",
    ],
}


def bundle_summary() -> list[dict]:
    return [{"id": c["id"], "version": c["version"], "label": c["label"], "codes": c["codes"], "recommended": c["recommendation"]["option"],
             "observed_games": c["observed_games"]} for c in CONVENTIONS]


def observed_cases() -> list[dict]:
    return [{"batch": b, "pair": p, "decks": d, "seed": s, "code": code, "scene": OBSERVED_SCENE[code], "note": OBSERVED_NOTES[code],
             "convention": next(c["id"] for c in CONVENTIONS if OBSERVED_SCENE[code] in [t["scene"] for t in c["targets"]])}
            for b, p, d, s, code in OBSERVED_CASES]


def build() -> dict:
    return {
        "schema_version": SCHEMA_VERSION,
        "title": "［ポイズンミスト］とどくの量の問い（PO1〜PO3）の続行規約の仕様案（採用の判断の前。エンジンの動作は変えていない）",
        "generated_by": "scripts/build_poison_mist_play_policy_spec.py",
        "status": SPEC_STATUS,
        "base": BASE,
        "kyuura": KYUURA,
        "approvals": {"work": WORK_APPROVAL, "specification": SPECIFICATION_APPROVAL},
        "ground_rules": GROUND_RULES,
        "principles": PRINCIPLES,
        "conventions": [{**c, "status": SPEC_STATUS, "approval": SPEC_APPROVAL} for c in CONVENTIONS],
        "bundle_summary": bundle_summary(),
        "separated_questions": SEPARATED,
        "relation_s2a": RELATION_S2A,
        "state_save_log": STATE_SAVE_LOG,
        "set_proposal": SET_PROPOSAL,
        "stages": STAGES,
        "observed_cases": observed_cases(),
        "measurement": MEASUREMENT,
        "open_choices": OPEN_CHOICES,
        "verification": VERIFICATION,
        "unverified": UNVERIFIED,
    }


# ---------------------------------------------------------------------------------------------------------------------------------------------------
# 文書
# ---------------------------------------------------------------------------------------------------------------------------------------------------
def _cell(text) -> str:
    if text is None:
        return "—"
    if isinstance(text, list):
        return "<br>".join(_cell(t) for t in text) if text else "—"
    return str(text).replace("|", "\\|").replace("\n", " ")


def render(spec: dict) -> str:
    out: list[str] = []
    w = out.append
    base = spec["base"]
    w("# ［ポイズンミスト］とどくの量の続行規約の仕様案（PO1〜PO3）")
    w("")
    w("<!-- この文書は scripts/build_poison_mist_play_policy_spec.py が docs/poison-mist-play-policy-spec.json と同じ元から作る。手で直さない（--check が違いを見つける） -->")
    w("")
    w("**これは仕様案です（状態 `proposal`・承認 `not_approved`）。** 規約の登録・有効化・エンジンの続行処理は加えていません。2026-11-05 の作業の指示は、この仕様案の承認・PO1〜PO3 の"
      "裁定の承認ではありません。同じ作業の SC2 の不具合の修正（v0.144）は [sc2-integrity-fix-v0.144.md](sc2-integrity-fix-v0.144.md) に分けて記録しています。")
    w("")
    w("## 1. 基点と範囲")
    w("")
    w(f"- 基点: `{base['commit']}`（版 {base['version']}。{base['published_on']}）。{base['why']}。")
    w(f"- `origin/main` は `{base['origin_main']}`（{base['origin_main_note']}）。")
    w(f"- 作業ブランチ: `{base['branch']}`。利用者の `.claude/` はコミットに入れていません。")
    w(f"- kyuura: {spec['kyuura']['note']}。")
    w("- 読んだもの: docs/play-policy-s2a-v0.143.md・docs/play-policy-s2a-spec.md・docs/play-policy-family-plan.md / .json・docs/ruleset-mode-design.md・停止の方針の台帳・研究の対応表・"
      "docs/damage-reactions-poison-sleep-v0.119.md 5 章、effects.py の［ポイズンミスト］・どくの量（poison_check_amount・_poison_orders・poison_mist_upkeep）、procedures.py のポケモンチェック、"
      "conditions.py の poison、tests/test_damage_reactions_poison_sleep_v0_119.py。")
    w("")
    w("## 2. 承認の記録")
    w("")
    work = spec["approvals"]["work"]
    w(f"- 作業の承認: `{work['status']}`（{work['date']}）。{work['scope']}。")
    sp = spec["approvals"]["specification"]
    w(f"- この仕様案の承認: `{sp['status']}`。{sp['note']}。")
    w("")
    w("## 3. 基本方針")
    w("")
    for rule in spec["ground_rules"]:
        w(f"- {rule}。")
    w("")
    w("## 4. 共通の原則と、一括で判断するための要約")
    w("")
    for p in spec["principles"]:
        w(f"- **{p['id']}**（{p['name']}）: {p['text']}。規約: {', '.join('`' + c + '`' for c in p['conventions'])}。")
    w("")
    w("| 規約（案） | 停止コード | 推奨 | 観測の局 |")
    w("|---|---|---|---:|")
    for row in spec["bundle_summary"]:
        w(f"| `{row['id']}@{row['version']}` {row['label']} | {_cell(['`' + c + '`' for c in row['codes']])} | {_cell(row['recommended'])} | {row['observed_games']} |")
    w("")
    total = sum(r["observed_games"] for r in spec["bundle_summary"])
    w(f"- 3 規約は互いに依存しません（requires なし）。対象の場面は重なりません。S2a の続行側に残った停止 {spec['measurement']['s2a_continuation_halts']} 局のうち {total} 局が対象です（10 章）。")
    w("- 3 規約をそろえても、#power-lost・両方のきぜつ・SC2 などでは今の停止コードで止まります（完成したプレイ用の集合ではありません）。")
    w("")
    w("## 5. 規約ごとの仕様")
    w("")
    for index, c in enumerate(spec["conventions"], 1):
        w(f"### 5.{index} `{c['id']}@{c['version']}` — {c['label']}")
        w("")
        w(f"状態: `{c['status']}`・承認: `{c['approval']}`。原則: {c['principle']}。研究の記録: {', '.join(c['ruling_ids'])}（未解決のまま）。判断事項: {', '.join(c['decision_refs'])}。")
        w("")
        w("| 項目 | 内容 |")
        w("|---|---|")
        w(f"| 解決する問い | {_cell(c['question'])} |")
        w(f"| 規約の文（推奨仕様） | {_cell(c['statement'])} |")
        w(f"| 適用条件 | {_cell(c['applies_when'])} |")
        w(f"| 停止コード | {_cell(['`' + x + '`' for x in c['codes']])} |")
        targets = ["`" + t["scene"] + "`（" + t["coverage"] + "）: " + t["note"] for t in c["targets"]]
        w(f"| 対象の事例 | {_cell(targets)} |")
        if c["proposed_cases"]:
            cases = ["`" + p["id"] + "`: " + p["condition"] for p in c["proposed_cases"]]
            w(f"| 台帳に加える事例（案） | {_cell(cases)} |")
        w(f"| 除外 | {_cell([x['what'] + ('（`' + x['scene'] + '`）' if x.get('scene') else '') + ': ' + x['reason'] for x in c['excludes']])} |")
        w(f"| 厳密側 | {_cell(c['strict'])} |")
        w(f"| 続行側 | {_cell(c['continuation'])} |")
        w(f"| 依存・関係・競合 | 依存: {'なし' if not c['depends_on'] else _cell(c['depends_on'])}。関係: {', '.join(c['related'])}。競合: {'なし' if not c['conflicts_with'] else _cell(c['conflicts_with'])} |")
        w(f"| 実装箇所 | {_cell(['`' + s + '`' for s in c['sites']])} |")
        w(f"| 共通処理 / カード固有 | {_cell(c['common_implementation'])} / {_cell(c['card_specific'])} |")
        w(f"| 既存のテスト | {_cell(['`' + t + '`' for t in c['tests_existing']])} |")
        w(f"| 回帰テスト（完了基準） | {_cell(c['tests_new'])} |")
        w(f"| 現行挙動からの差 | {_cell(c['difference_from_current'])} |")
        w(f"| 推奨 | {_cell(c['recommendation']['option'])}（{_cell(c['recommendation']['reason'])}） |")
        w(f"| 代替案 | {_cell([a['option'] + '（' + a['reason'] + '）' for a in c['alternatives']])} |")
        w(f"| 未確認 | {_cell(c['unverified'])} |")
        w("")
        w("具体化した点:")
        w("")
        for topic, text in c["details"]:
            w(f"- **{topic}**: {text}。")
        w("")
    w("## 6. 共通化しない問い")
    w("")
    w("| 問い | 場面 | 分ける理由 |")
    w("|---|---|---|")
    for s in spec["separated_questions"]:
        w(f"| {_cell(s['question'])} | `{s['scene']}` | {_cell(s['reason'])} |")
    w("")
    w("## 7. S2a のポケモンチェック・きぜつ判定との関係")
    w("")
    for topic, text in spec["relation_s2a"]:
        w(f"- **{topic}**: {text}。")
    w("")
    w("## 8. 状態・保存・ログ・集合")
    w("")
    ssl = spec["state_save_log"]
    for key, title in (("state", "状態"), ("save", "保存"), ("log", "ログ"), ("observation", "観測"), ("audit", "監査")):
        w(f"- **{title}**: {ssl[key]}。")
    sp = spec["set_proposal"]
    cont = sp["continuation"]
    w(f"- **厳密側**: `{sp['strict']['id']}@{sp['strict']['version']}`。変更: {sp['strict']['change']}。")
    w(f"- **既存の開発用の集合**: `{sp['existing_development']['id']}@{sp['existing_development']['version']}`。変更: {sp['existing_development']['change']}。")
    w(f"- **続行側（案）**: `{cont['id']}@{cont['version']}`（{cont['usage']}・{cont['completeness']}）。規約: {cont['members']}。{cont['approval_of_members']}。{cont['not_called']}。")
    w(f"- **版**: {sp['version_policy']}。")
    w("")
    w("## 9. 判断が残る選択肢")
    w("")
    w("| ID | 規約 | 問い | 推奨 | 代替案 |")
    w("|---|---|---|---|---|")
    for o in spec["open_choices"]:
        w(f"| {o['id']} | {_cell(o['convention'] and '`' + o['convention'] + '`')} | {_cell(o['question'])} | {_cell(o['recommended'])} | {_cell(o['alternatives'])} |")
    w("")
    w("実装の段階:")
    w("")
    w("| 段階 | 内容 | 対象 | 前提 | 厳密側の不変条件 | 続行側の完了条件 |")
    w("|---|---|---|---|---|---|")
    for st in spec["stages"]:
        w(f"| {st['id']} | {_cell(st['name'])} | {_cell(st['targets'])} | {_cell(st['prerequisites'])} | {_cell(st['strict_invariant'])} | {_cell(st['continuation_done'])} |")
    w("")
    m = spec["measurement"]
    w("## 10. 観測した局と計測の計画")
    w("")
    w(f"- 元: {m['source']}。対象 {m['covered_by_this_spec']} 局、対象外 {m['not_covered']}。")
    w(f"- {m['now']}。")
    w("")
    w("| バッチ | 組 | 席（先に書いた方がプレイヤー 0） | seed | 停止コード | 事例 | 規約（案） |")
    w("|---|---|---|---:|---|---|---|")
    for r in spec["observed_cases"]:
        w(f"| {r['batch']} | {r['pair']} | {' 対 '.join(r['decks'])} | {r['seed']} | `{r['code']}` | `{r['scene']}` | `{r['convention']}` |")
    w("")
    for code, note in OBSERVED_NOTES.items():
        w(f"- `{code}`: {note}。")
    w("")
    w("計測の計画:")
    w("")
    for line in m["plan"]:
        w(f"- {line}。")
    w("")
    w("## 11. 確かめたこと（実行した確認と、読んだだけの確認）")
    w("")
    for line in spec["verification"]["executed"]:
        w(f"- {line}。")
    w("")
    w("読んだだけ・走らせていないもの:")
    w("")
    for line in spec["verification"]["read_only"]:
        w(f"- {line}。")
    w("")
    w("## 12. 未確認")
    w("")
    for line in spec["unverified"]:
        w(f"- {line}。")
    w("")
    return "\n".join(out)


# ---------------------------------------------------------------------------------------------------------------------------------------------------
# 確かめ
# ---------------------------------------------------------------------------------------------------------------------------------------------------
def load(path: pathlib.Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def dump(data: dict) -> str:
    return json.dumps(data, ensure_ascii=False, indent=1) + "\n"


def _defined(path: str, name: str) -> bool:
    text = (ROOT / path).read_text(encoding="utf-8")
    return re.search(rf"^\s*(?:def|class)\s+{re.escape(name)}\b", text, re.MULTILINE) is not None


def check(written: dict, document: str) -> list[str]:
    problems: list[str] = []
    fresh = build()
    if fresh != written:
        problems.append("書いた JSON が、作り直した仕様案と違う（--write で作り直す）")
    if render(fresh) != document:
        problems.append("書いた文書が、作り直した文書と違う（--write で作り直す）")
    spec = written
    ledger, plan, records, research = load(LEDGER), load(PLAN), load(RECORDS), load(RESEARCH)
    entries = {e["id"]: e for e in ledger["entries"]}
    index_scenes = {s["id"] for s in records["scene_index"]["scenes"]}
    codes_index = records["scene_index"]["codes"]
    candidates = {c["id"]: c for c in plan["candidates"]}
    decisions = ledger["decision_status"]
    stop_codes = research["stop_codes"]

    try:
        subprocess.run(["git", "-C", str(ROOT), "merge-base", "--is-ancestor", spec["base"]["commit"], "HEAD"], check=True, capture_output=True)
    except (subprocess.CalledProcessError, FileNotFoundError):
        problems.append(f"基点 {spec['base']['commit']} が HEAD の祖先でない")

    # 承認・状態: 作業の承認を仕様の承認にしない
    if spec["status"] != SPEC_STATUS:
        problems.append(f"仕様案の状態が {SPEC_STATUS} でない")
    if spec["approvals"]["specification"]["status"] != "not_approved":
        problems.append("仕様案を承認済みにしている（作業の承認を仕様の承認として登録しない）")
    if "裁定" not in spec["approvals"]["work"]["scope"] or "承認ではな" not in spec["approvals"]["work"]["scope"]:
        problems.append("作業の承認の範囲に、裁定・仕様の承認ではないことが書かれていない")

    known_ids = {c["id"] for c in spec["conventions"]}
    principle_ids = {p["id"] for p in spec["principles"]}
    owners: dict[str, list[str]] = {}
    proposed: dict[str, dict] = {}
    for c in spec["conventions"]:
        for p in c["proposed_cases"]:
            proposed[p["id"]] = p
    for c in spec["conventions"]:
        cid = c["id"]
        if c["status"] != SPEC_STATUS or c["approval"] != SPEC_APPROVAL:
            problems.append(f"{cid}: 状態・承認が案のまま（{SPEC_STATUS}・{SPEC_APPROVAL}）でない")
        if c["principle"] not in principle_ids or cid not in next((p["conventions"] for p in spec["principles"] if p["id"] == c["principle"]), []):
            problems.append(f"{cid}: 原則 {c['principle']} がない、または原則の規約の一覧にない")
        for code in c["codes"]:
            if code not in entries or entries[code]["entry_kind"] not in ("research_stop_code", "runtime_stop_code"):
                problems.append(f"{cid}: 停止コード {code} が台帳の停止コードにない")
            if code not in stop_codes:
                problems.append(f"{cid}: 停止コード {code} が研究の対応表にない")
        rulings = {r["ruling_id"] for code in c["codes"] for r in stop_codes.get(code, {}).get("engine_rulings", [])}
        for rid in c["ruling_ids"]:
            if rid not in rulings:
                problems.append(f"{cid}: 研究の記録 {rid} が、停止コードの研究の対応表にない")
        for d in c["decision_refs"]:
            if d not in decisions:
                problems.append(f"{cid}: 判断事項 {d} が台帳にない")
        for p in c["proposed_cases"]:
            if p["parent"] not in c["codes"] or p["parent"] not in entries:
                problems.append(f"{cid}: 事例の案 {p['id']} の親 {p['parent']} が、この規約の停止コード・台帳にない")
            if not p["id"].startswith(p["parent"] + "#"):
                problems.append(f"{cid}: 事例の案 {p['id']} の ID が親のコードから始まらない")
        for t in c["targets"]:
            owners.setdefault(t["scene"], []).append(cid)
            if t["scene"] not in index_scenes and t["scene"] not in proposed:
                problems.append(f"{cid}: 対象の場面 {t['scene']} が同梱の場面の一覧にも事例の案にもない")
            if t["scene"].split("#")[0] not in c["codes"]:
                problems.append(f"{cid}: 対象の場面 {t['scene']} の停止コードが、この規約の停止コードにない")
        for x in c["excludes"]:
            if not x.get("reason"):
                problems.append(f"{cid}: 除外 {x['what']} に理由がない")
            if x.get("scene") and x["scene"] not in entries and x["scene"] not in index_scenes and x["scene"] not in proposed:
                problems.append(f"{cid}: 除外の {x['scene']} が台帳・事例の案にない")
        # 対象と除外の対応の漏れ: 規約の停止コードの場面（事例の案で分けるコードは、その事例）が、どれも対象か除外にある
        covered = {t["scene"] for t in c["targets"]} | {x.get("scene") for x in c["excludes"] if x.get("scene")}
        for code in c["codes"]:
            split = [pid for pid, p in proposed.items() if p["parent"] == code]
            for scene in split or codes_index.get(code, []):
                if scene not in covered:
                    problems.append(f"{cid}: 停止コード {code} の場面 {scene} が、対象にも除外にもない（対応の漏れ）")
        for ref in c["depends_on"] + c["conflicts_with"]:
            if ref not in known_ids:
                problems.append(f"{cid}: 依存・競合の {ref} が、この仕様の規約にない")
        for ref in c["related"]:
            if ref not in known_ids and ref not in candidates:
                problems.append(f"{cid}: 関係の {ref} が、この仕様の規約にも設計案の候補にもない")
        for site in c["sites"]:
            path, _, name = site.partition("::")
            if not (ROOT / path).exists() or not _defined(path, name):
                problems.append(f"{cid}: 実装箇所 {site} が見つからない")
        for test in c["tests_existing"]:
            path, _, name = test.partition("::")
            if not (ROOT / path).exists() or not _defined(path, name):
                problems.append(f"{cid}: 既存のテスト {test} が見つからない")
        observed = sum(1 for r in spec["observed_cases"] if r["convention"] == cid)
        if observed != c["observed_games"]:
            problems.append(f"{cid}: 観測の局 {c['observed_games']} が、観測した局の表の数 {observed} と違う")
    for scene, ids in owners.items():
        if len(ids) > 1:
            problems.append(f"場面 {scene} が 2 つ以上の規約（{ids}）の対象（競合）")
    for c in spec["conventions"]:
        for x in c["excludes"]:
            holders = owners.get(x.get("scene"), [])
            if c["id"] in holders:
                problems.append(f"{c['id']}: 除外の場面 {x['scene']} が、同じ規約の対象（対象と除外の食い違い）")
            elif holders and not any(h in x["reason"] for h in holders):
                problems.append(f"{c['id']}: 除外の場面 {x['scene']} は規約 {holders} の対象なのに、理由にその規約を書いていない")
    for s in spec["separated_questions"]:
        if s["scene"] not in entries and s["scene"] not in proposed:
            problems.append(f"共通化しない問いの場面 {s['scene']} が台帳・事例の案にない")
        if s["scene"] in owners:
            problems.append(f"共通化しない問いの場面 {s['scene']} が、規約の対象になっている")

    # 観測した局: 計測の記録の数と合う（S2a の文書の数・設計案の計測の停止コードの数）
    counts: dict[str, int] = {}
    for r in spec["observed_cases"]:
        counts[r["code"]] = counts.get(r["code"], 0) + 1
    halt_codes = plan["observation"]["halt_codes"]
    for code, count in counts.items():
        if halt_codes.get(code) != count:
            problems.append(f"観測した局の {code} の数 {count} が、設計案の計測の数 {halt_codes.get(code)} と違う")
    if len(spec["observed_cases"]) != spec["measurement"]["covered_by_this_spec"]:
        problems.append("観測した局の数と、対象の局の数が違う")
    if len({(r["batch"], tuple(r["decks"]), r["seed"]) for r in spec["observed_cases"]}) != len(spec["observed_cases"]):
        problems.append("観測した局の表に同じ局が 2 回ある")

    # 規約を登録・有効化していない（仕様案）。既存の集合の中身を変えていない
    sys.path.insert(0, str(ROOT))
    from kyuura_engine import conventions as C

    for c in spec["conventions"]:
        if any(key[0] == c["id"] for key in C.CONVENTIONS):
            problems.append(f"{c['id']} がエンジンに登録されている（仕様案のあいだは登録・有効化しない）")
    proposal_set = spec["set_proposal"]["continuation"]["id"]
    if any(key[0] == proposal_set for key in C.SETS):
        problems.append(f"集合 {proposal_set} がエンジンに登録されている（仕様案のあいだは登録しない）")
    if (spec["set_proposal"]["strict"]["id"], spec["set_proposal"]["strict"]["version"]) != C.DEFAULT_SET:
        problems.append("厳密側の集合が、エンジンの既定の集合と違う")
    existing = (spec["set_proposal"]["existing_development"]["id"], spec["set_proposal"]["existing_development"]["version"])
    if existing not in C.SETS:
        problems.append(f"既存の開発用の集合 {existing} がエンジンにない")
    for o in spec["open_choices"]:
        if o["convention"] is not None and o["convention"] not in known_ids:
            problems.append(f"{o['id']}: 規約 {o['convention']} がこの仕様にない")
    staged = {t for s in spec["stages"] for t in s["targets"]}
    for cid in known_ids:
        if cid not in staged:
            problems.append(f"規約 {cid} がどの実装の段階にもない")
    return problems


def main() -> int:
    parser = argparse.ArgumentParser()
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--write", action="store_true")
    group.add_argument("--check", action="store_true")
    args = parser.parse_args()
    if args.write:
        spec = build()
        OUTPUT.write_text(dump(spec), encoding="utf-8", newline="\n")
        DOCUMENT.write_text(render(spec), encoding="utf-8", newline="\n")
        print(f"wrote {OUTPUT.relative_to(ROOT)} {DOCUMENT.relative_to(ROOT)}")
        return 0
    if not OUTPUT.exists() or not DOCUMENT.exists():
        print("仕様案の JSON・文書がない（--write で作る）")
        return 1
    problems = check(load(OUTPUT), DOCUMENT.read_text(encoding="utf-8"))
    for problem in problems:
        print(problem)
    print(f"problems={len(problems)}")
    return 1 if problems else 0


if __name__ == "__main__":
    raise SystemExit(main())

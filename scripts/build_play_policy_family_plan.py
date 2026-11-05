"""未決場面を共通規約で扱うための設計案 docs/play-policy-family-plan.json を作る・確かめる（調査・設計だけ。エンジンの動作は変えない）。

    python scripts/build_play_policy_family_plan.py --write   # 設計案の JSON と、文書の生成した表を書き出す
    python scripts/build_play_policy_family_plan.py --check   # 停止の方針の台帳から作り直した設計案と、書き出した設計案が同じか・不変条件を満たすか

- 場面（事例）の唯一の元は停止の方針の台帳（docs/stop-policy-classification.json）の ``entries``。この設計案は ID で引くだけで、台帳の本文（到達可能性・止め方・研究の記録）を書き換えない。
- 共通規約の案（``CANDIDATES``）は**どれも案**で、利用者の承認を受けていない（``status`` は proposal だけ）。規約の採用・モードの実装・エンジンの変更はしていない。
- v0.143 の経過: 5 つの案（``ADOPTIONS``）は、S2a の続行規約として利用者が採用し、開発用の集合 CS-KYUURA-PLAY-S2A@1 に登録した（``status`` は adopted。採用の範囲は
  ``adoption`` に書き、案の対象（``targets``）は提案の時点のまま残す）。ほかの案は proposal のまま。
- v0.145 の経過: この設計案の候補ではない別の仕様案（docs/poison-mist-play-policy-spec.md）の続行規約 3 件（``SPEC_ADOPTIONS``）を、利用者が採用し、開発用の集合
  CS-KYUURA-PLAY-PO@1 に登録した。場面の行に採用した規約の印（``adopted_convention``）を付けるだけで、候補の状態は変えない。台帳が PO3 を事例（#source-left・#power-lost）に
  分けたので、場面の ID だけを事例に合わせた（PC-LASTING-SOURCE-CHANGE の対象・経路の一覧）。
- v0.146 の経過: PSP-NJ1-NINJA-GYM-ORACLE を両モード共通の不具合として直した（``NEW_FINDINGS`` の status を fixed、``DEFECT_COUPLING`` から外し、PC-USE-WITHOUT-TARGET の
  NJ1 の対象を blocked_by_defect から needs_secret_review にした。候補の対象の組・状態は変えない）。
- 各場面の区分（``plan_class``）は、利用者の依頼の A〜E の軸。台帳の ``classification``（棚卸しの A〜E。A=機能不足 …）とは**別の軸**で、同じ文字でも意味が違う。
- 対戦の道具の発生の記録（``OBSERVATION``）は、リポジトリの外の記録の集計の写し。版・組・方策・seed・分母・数え方を一緒に書く。停止コードの件数から停止率を推定しない。
"""

from __future__ import annotations

import argparse
import collections
import json
import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parent.parent
OUTPUT = ROOT / "docs" / "play-policy-family-plan.json"
DOCUMENT = ROOT / "docs" / "play-policy-family-plan.md"
LEDGER = ROOT / "docs" / "stop-policy-classification.json"
RESEARCH = ROOT / "kyuura_engine" / "data" / "research_links.json"

SCHEMA_VERSION = 1

BASE = {
    "commit": "8164194ca289c5f7f332c7f16d7f700a81a37215",
    "version": "0.141.0",
    "branch_of_base": "origin/claude/prize-order-v0140-cleanup（v0.141 の最後のコミット。main には未取り込み）",
    "origin_main": "816bcffb86edeb3ea713ee08818a070e036fe0a8",
    "origin_main_note": "PR #35（v0.140 claude/prize-order-user-rule）のマージ。木は c68b3cd と同じで、基点の祖先 c68b3cd と内容が同じ。v0.141（834cdcb〜8164194）を含まない",
    "why": "v0.141 で直した拒否の文（旧版の状態と矛盾した状態の書き分け）と legacy 参照の確かめを含めるため、main ではなく v0.141 の最後のコミットにした。v0.141 の変更は拒否の文・"
           "テスト・文書だけで、停止コードの集合・止め方は v0.140（main）と同じ",
    "branch": "claude/play-policy-family-plan",
}
KYUURA = {"pinned_commit": "71d1728938fb4c8fefde9b82779cdef74beb612d", "checkout_observed": "b9e7cff", "read_only": True}

STATUS = "proposal"  # 規約案の状態。承認済みにしない（--check が確かめる）
ADOPTED = "adopted"  # v0.143: 利用者が採用し、エンジンの規約集合に登録した案（``ADOPTIONS`` だけ。--check がエンジンの登録と範囲を照らす）

# v0.143（docs/play-policy-s2a-v0.143.md）: 採用した案と採用の範囲。案の対象（targets）は提案の時点のまま残し、採用で外した対象（excluded_targets）と加えた場面（added_scenes）を書く。
# 採用の範囲 = targets − excluded_targets + added_scenes が、登録した規約の場面とちょうど同じ（--check）
_S2A_ADOPTION = {"on": "2026-11-04", "by": "user", "version": "0.143.0", "set": ["CS-KYUURA-PLAY-S2A", 1], "document": "docs/play-policy-s2a-v0.143.md",
                 "spec": "docs/play-policy-s2a-spec.md", "not_recorded_as": "公式の裁定・エラッタ・kyuura の研究上の解決（続行側の集合の規約の採用）"}
ADOPTIONS = {
    "PC-SETUP-MULLIGAN-COUNT": {**_S2A_ADOPTION, "convention": ["PC-SETUP-MULLIGAN-COUNT", 1], "excluded_targets": [], "added_scenes": []},
    "PC-SETUP-PLAY-AS-POKEMON": {**_S2A_ADOPTION, "convention": ["PC-SETUP-PLAY-AS-POKEMON", 1], "excluded_targets": [],
                                 "added_scenes": [{"scene": "UNRESOLVED_PLAY_AS_POKEMON_SETUP#setup-placement", "coverage": "full",
                                                   "note": "v0.143 の採用で加えた場面（準備の配置の拒否。続行側は NOT_BASIC_POKEMON の拒否で、ほかの停止はない）"}]},
    "PC-CHECK-SIDE-ORDER": {**_S2A_ADOPTION, "convention": ["PC-CHECK-SIDE-ORDER", 1],
                            "excluded_targets": [{"scene": "UNRESOLVED_POKEMON_CHECK_BERRY_ORDER", "reason": "BY1 は効果の種類の順番を含む別の問い（S2a の仕様案 OC-7。採用仕様の除外）"}],
                            "added_scenes": []},
    "PC-COIN-COUNT-SHORT": {**_S2A_ADOPTION, "convention": ["PC-COIN-COUNT-SHORT", 1], "excluded_targets": [], "added_scenes": []},
    "PC-CHECK-KO-POINT": {**_S2A_ADOPTION, "convention": ["PC-CHECK-KO-POINT", 1], "excluded_targets": [], "added_scenes": []},
}
# v0.145（docs/poison-mist-play-po-v0.145.md）: この設計案の候補ではない、別の仕様案の続行規約の採用（場面の行の印と、エンジンの登録との照らし合わせだけ。候補の状態は変えない）
_PO_ADOPTION = {"on": "2026-11-05", "by": "user", "version": "0.145.0", "set": ["CS-KYUURA-PLAY-PO", 1], "document": "docs/poison-mist-play-po-v0.145.md",
                "spec": "docs/poison-mist-play-policy-spec.md", "not_recorded_as": "公式の裁定・エラッタ・kyuura の研究上の解決（続行側の集合の規約の採用）"}
SPEC_ADOPTIONS = {
    "PC-POISON-AMOUNT-ORDER": {**_PO_ADOPTION, "convention": ["PC-POISON-AMOUNT-ORDER", 1], "scenes": ["UNRESOLVED_POISON_CHANGE_ORDER"]},
    "PC-POISON-MIST-TARGETS": {**_PO_ADOPTION, "convention": ["PC-POISON-MIST-TARGETS", 1], "scenes": ["UNRESOLVED_POISON_MIST_EARLIER_POISON"]},
    "PC-POISON-MIST-SOURCE-LEFT": {**_PO_ADOPTION, "convention": ["PC-POISON-MIST-SOURCE-LEFT", 1], "scenes": ["UNRESOLVED_POISON_MIST_SOURCE#source-left"],
                                   "related_candidate": "PC-LASTING-SOURCE-CHANGE",
                                   "note": "PC-LASTING-SOURCE-CHANGE（proposal のまま）と同じ原則の［ポイズンミスト］の記録だけの規約。案そのものは採用していない"},
}

# ---------------------------------------------------------------------------------------------------------------------------------------------------
# 区分（利用者の依頼の A〜E。台帳の classification とは別の軸）
# ---------------------------------------------------------------------------------------------------------------------------------------------------
PLAN_CLASSES = {
    "A": "プレイ用の規約で続けられる候補の、研究上の未決場面（続けるのに実装・秘密への非依存の確かめ・別の規約が要るものは continuation に書く）",
    "B": "エンジンの機能不足（実装・データ・継続の状態がない）",
    "C": "技術的な制限（探索・組合せ・表現の上限）",
    "D": "情報漏れ・内部エラー・状態の整合性・止めすぎなど、両モードで直す共通の不具合（候補・未確認を含む）",
    "E": "採用済みの規約・修正済み・対象外・テストだけのコード・コードのない問いなど、そのほか",
}
PLAN_CLASS_SHORT = {"A": "研究上の未決場面", "B": "機能不足", "C": "技術的な制限", "D": "共通の不具合", "E": "そのほか"}
# 規約を当てたときに続けられるか（場面ごと）。full は、現行コードを読んで、規約が答えれば同じ分岐にほかの停止がないことを確かめたものだけ
COVERAGE = {
    "full": "規約だけで続けられる（現行コードの分岐を読んで、規約が答えればその停止の箇所にほかの停止がないことを確かめた）",
    "question_resolved_other_stops_possible": "規約は場面の問いに答えるが、その後の処理で既存のほかの停止に当たりうる（コードで確かめた）",
    "partial": "場面に問いが複数あり、規約が答えるのは一部",
    "needs_implementation": "規約に加えて、エンジンの実装（継続の状態・新しい処理）が要る",
    "needs_secret_review": "規約に加えて、秘密への非依存（対の比べ）の確かめ直しが要る",
    "blocked_by_defect": "同じ場面に未修正の共通の不具合（情報漏れ）がある。不具合を直す前に規約を採らない",
    "unverified": "停止の文・裁定の記録の行から当てたもので、規約で続けられるかはコードで確かめていない",
}
CONTINUABLE_COVERAGE = {"full"}
PARTIAL_COVERAGE = {"question_resolved_other_stops_possible", "partial"}
EXTRA_COVERAGE = {"needs_implementation", "needs_secret_review", "blocked_by_defect"}

# 場面の不足の種類（利用者の依頼の 5 つの区別。規約案の question_kind）
SHORTAGE_KINDS = {
    "absent_from_start": "対象が最初からない（使う宣言の時点。公開の領域・本人が知っている手札で決まる）",
    "lost_mid_effect": "効果の途中で対象・発生源がいなくなる",
    "coin_count_short": "コインで決まった必要な枚数が不足する（乱数のあと）",
    "stated_count_short": "説明の決まった枚数が、使う時点の公開の枚数より多い",
    "cost_unpayable": "コストを払えない",
    "hidden_search_empty": "非公開の場所（山札）を探して見つからない",
    "target_without_effect": "対象はあるが、選んでも・使っても何も起こらない",
}

# ---------------------------------------------------------------------------------------------------------------------------------------------------
# 共通規約の案。targets は台帳の場面 ID（事例のあるコードは事例 ID）。どれも案（承認されていない）
# ---------------------------------------------------------------------------------------------------------------------------------------------------
MULLIGAN = "UNRESOLVED_MULLIGAN_COMPENSATION"
PLAY_AS = "UNRESOLVED_PLAY_AS_POKEMON_SETUP"


def _t(scene, coverage=None, note=None):
    return {"scene": scene, **({"coverage": coverage} if coverage else {}), **({"note": note} if note else {})}


CANDIDATES = [
    {
        "id": "PC-SETUP-MULLIGAN-COUNT", "name": "回数の違う切り直しの補償の数え方", "cluster": "setup", "whole_game": True,
        "decision_refs": ["DEC-MULLIGAN-COMPENSATION"],
        "question": "両方のプレイヤーが同時に切り直した回のあとに、片方だけがさらに切り直したとき、相手は何回ぶんの補償（1 回ごとに最大 2 枚）を引けるか",
        "statement": "準備の切り直しを回ごとに数える。両方のプレイヤーが同時に切り直した回は、どちらにも補償を与えない。片方のプレイヤーだけが切り直した回は、1 回ごとに、もう一方のプレイヤーに"
                     "補償 1 回（山札から 0〜2 枚。DrawMulliganCards 1 回）を与える。引く時点は、回数が同じでない場合も今の補償と同じ（サイドを置いたあと、ジャンケンの前）",
        "applies_when": "engine._deal_opening_hands の切り直しの回の列（mulligan_rounds）に、両方の回と片方だけの回が両方ある（今 UNRESOLVED_MULLIGAN_COMPENSATION で準備を HALTED にする条件そのもの）",
        "targets": [_t(f"{MULLIGAN}#initial-setup", "full"), _t(f"{MULLIGAN}#sudden-death-segment", "full")],
        "excludes": ["片方だけの回しかない切り直し（今の補償のまま）", "両方の回しかない切り直し（今のまま、どちらも引かない）",
                     "なにかの化石・ピッピ人形がある手札（PC-SETUP-PLAY-AS-POKEMON。切り直しの前に止める）"],
        "exceptions": [],
        "depends_on": [], "related": ["PC-SETUP-PLAY-AS-POKEMON"],
        "conflicts_with": [],
        "strict_difference": "厳密は今のまま準備で HALTED。プレイ用は止めずに、片方だけの回の数（= 両者の切り直しの回数の差）ぶんの補償を与える",
        "impact": {"information": "変えない（切り直しの手札の公開・補償の枚数の選択は今のまま）", "rng": "補償で引くのは山札の上から（乱数を新しく使わない）。止めないので、その後の対戦の乱数を使う",
                   "cost": "なし", "order": "補償の時点は今と同じ"},
        "common_implementation": "engine._deal_opening_hands の HALTED の分岐を、規約の照会（規約集合に PC-SETUP-MULLIGAN-COUNT があるか）で補償の数に置きかえる。同じ関数を延長戦の区間も使う"
                                 "（engine._prepare_segment）ので、区間ごとの実装は要らない",
        "card_specific_remaining": "なし",
        "regression_tests": ["両方の回 1・片方だけの回 1・2 の盤面で、補償の回数・DrawMulliganCards の受け付け・ログ・観測", "片方だけの回だけ・両方の回だけの盤面が今と同じ（厳密・プレイ用とも）",
                             "延長戦の区間でも同じ", "厳密の集合では今と同じ HALTED"],
        "recommendation": {"option": "回ごとに数える（片方だけの回 1 回につき補償 1 回）",
                           "reason": "p.308 の 2 つの文（片方の切り直しごとの補償・両方のときはどちらも引かない）を、回ごとにそのまま当てはめる読み方で、席・先攻後攻によらない。数は両者の切り直しの回数の差と同じ"},
        "alternatives": [{"option": "両方の回が一度でもあれば、どちらも引かない", "reason": "「両方とも」の文を準備全体に当てはめる読み方。補償を受けられない側の不利が大きい"},
                         {"option": "相手の切り直しの総数ぶん引ける（両方の回も数える）", "reason": "「両方とも…引かない」の文と合わない（採らない案として記録）"}],
        "basis": ["docs/rules-2000-02-14.md の p.308 の表（切り直し・補償・両方とも切り直し）と未解決の行", "engine.py:513〜528（halt の条件と補償の数え方）", "kyuura docs/engine-readiness.md 4 章（読んだだけ）"],
        "unverified": ["公式資料に回数が違う場合の記述がないことの再確認（研究上は未解決のまま）"],
    },
    {
        "id": "PC-SETUP-PLAY-AS-POKEMON", "name": "準備の手札のなにかの化石・ピッピ人形", "cluster": "setup", "whole_game": True,
        "decision_refs": ["DEC-PLAY-AS-POKEMON"],
        "question": "たねポケモンがなく、なにかの化石・ピッピ人形（たねポケモンとして場に出せるトレーナー）がある最初の手札で、切り直すのか、それを最初のポケモンとして出せるのか",
        "statement": "準備の切り直しの判定では、たねポケモンとして場に出せるトレーナー（なにかの化石・ピッピ人形）を、たねポケモンカードとして数えない。たねポケモンカード・ベイビィポケモンカードが"
                     "なければ、今の切り直しと同じく切り直す",
        "applies_when": "engine._deal_opening_hands で、たねポケモンのない手札に play_as_pokemon_in_hand のカードがある（今 UNRESOLVED_PLAY_AS_POKEMON_SETUP で HALTED にする条件）",
        "targets": [_t(f"{PLAY_AS}#initial-setup", "question_resolved_other_stops_possible", "切り直すと決めても、その後の切り直しの回で PC-SETUP-MULLIGAN-COUNT の場面に当たりうる"),
                    _t(f"{PLAY_AS}#sudden-death-segment", "question_resolved_other_stops_possible")],
        "excludes": ["準備でない場面（にげる PF2・育て屋 PF3・ちえくらべ MG2）。同じカードでも別の問い", "たねポケモンもある手札（今のまま切り直さない）"],
        "exceptions": [],
        "depends_on": [], "related": ["PC-SETUP-MULLIGAN-COUNT"],
        "conflicts_with": [],
        "strict_difference": "厳密は今のまま準備で HALTED。プレイ用は切り直す（切り直しの回が増える）",
        "impact": {"information": "切り直しで手札を見せる（今の切り直しと同じ公開）", "rng": "切り直しで山札を切る（乱数を使う）", "cost": "なし", "order": "変えない"},
        "common_implementation": "engine._deal_opening_hands の HALTED の分岐を、規約の照会で切り直しに置きかえる",
        "card_specific_remaining": "対象のカードの一覧（play_as_pokemon_in_hand が見るカード）を規約の対象に明示する",
        "regression_tests": ["化石・人形だけの手札で切り直すこと（回数・ログ・公開）", "化石と人形とたねポケモンの手札が今と同じ", "延長戦の区間でも同じ", "厳密では今と同じ HALTED"],
        "recommendation": {"option": "数えない（切り直す）", "reason": "準備の規定の「たねポケモンカード」の語のまま当てはめ、最初のポケモンとして置く新しい処理（準備でのトレーナーの扱い）を作らない"},
        "alternatives": [{"option": "最初のポケモン（バトル場・ベンチ）として出せる", "reason": "カードの「たねポケモンとして場に出せる」を準備にも当てはめる読み方。準備で置く処理の実装と、裏向きで置くときの扱いの確かめが要る（needs_implementation）"}],
        "basis": ["docs/fossil-hidden-info-v0.47.md 3 章（PF1）", "engine.py:491〜500"],
        "unverified": ["kyuura の UQ-PLAY-AS-POKEMON の記録の再照合（固定コミットの写しだけを見た）"],
    },
    {
        "id": "PC-CHECK-SIDE-ORDER", "name": "ポケモンチェックで両方のプレイヤーが同じ処理をする順番", "cluster": "pokemon_check", "whole_game": True,
        "decision_refs": ["DEC-SLEEP-COIN-ORDER", "DEC-ORDER-RULE"],
        "question": "ポケモンチェック（どちらの番でもない）の同じ手順で、両方のプレイヤーがコインを投げる・処理をするとき、どちらから行うか",
        "statement": "ポケモンチェックの同じ手順で両方のプレイヤーが同じ種類の処理（ねむりのコイン・くろこげマーカーのコイン）をするときは、その番を終えたプレイヤー（ポケモンチェックの直前の"
                     "番のプレイヤー）の場から先に、それぞれの場はバトル場 → ベンチの順に行う（今のログの順と同じ）",
        "applies_when": "procedures.pokemon_check_sleep_and_paralysis で両方の対戦ポケモンがねむり（SLEEP_COIN_ORDER）、procedures._char_coin_stop で両方のプレイヤーがくろこげマーカーのコインを投げる（KK1）",
        "targets": [_t("UNRESOLVED_POKEMON_CHECK_SLEEP_COIN_ORDER", "question_resolved_other_stops_possible",
                       "順番の分岐のあとに、回復したときの止め方（_recovery_stop の MH1・TF1・TF2・DG1）とねむりのコインの数（sleep_check_coins）の処理がある"),
                    _t("UNRESOLVED_POKEMON_CHECK_CHAR_COIN_ORDER", "question_resolved_other_stops_possible",
                       "順番を決めても、コインの前の確かめ（どの結果でも BY1・PK1・SC1・両方のきぜつで止めないか）と上限 MAX_CHAR_COINS（UNSUPPORTED_POKEMON_CHECK_CHAR_COINS）が残る"),
                    _t("UNRESOLVED_POKEMON_CHECK_BERRY_ORDER", "unverified", "BY1 は 1 の「指示されたこと」の効果の種類（悪エネルギー・きのみ）の順番を含み、両方の側の順番だけの問いではない")],
        "excludes": ["ポケモンチェックの外の同時の処理（PC-ORDER-ATTACK-PRECHECK・PC-ORDER-OVERLAP）", "両方のきぜつ（PC-CHECK-DOUBLE-KNOCKOUT）",
                     "サイドを取る順番（利用者の指定 USER-PRIZE-ORDER-ALWAYS-CHOSEN は「同じきぜつの処理」の場面だけ。ポケモンチェックへ自動で広げない）"],
        "exceptions": ["片方のプレイヤーだけのコイン（今のまま）"],
        "depends_on": [], "related": ["PC-CHECK-DOUBLE-KNOCKOUT"],
        "conflicts_with": ["PC-ORDER-OVERLAP（ポケモンチェックの中に当てない。対象の一覧を分ける）"],
        "strict_difference": "厳密は今のまま HALTED。プレイ用はコインを投げて続ける",
        "impact": {"information": "変えない（コインは公開）", "rng": "どちらのコインが乱数のどの値になるかが決まる（席・先攻後攻で偏らない: 番を終えたプレイヤーは毎回入れかわる）",
                   "cost": "なし", "order": "ログの順と同じ"},
        "common_implementation": "2 か所の HALTED の分岐を、規約の照会で order（番を終えたプレイヤー → 相手）の順の処理に置きかえる。ねむりのコインの処理はすでに複数を順に扱う",
        "card_specific_remaining": "なし（くろこげマーカーのカードの一覧は今の登録のまま）",
        "regression_tests": ["両方ねむりの盤面で、コインの割り当て・回復・ログ（両方の番の終わりで）", "両方のくろこげマーカーで、コインの前の確かめが今どおりはたらくこと", "片方だけのときが今と同じ",
                             "厳密では今と同じ HALTED", "道具の対戦で先攻・後攻の偏り（勝率の差）を測る"],
        "recommendation": {"option": "番を終えたプレイヤーから", "reason": "席（プレイヤー 0・1）によらず、ログの順・p.325 の「番のプレイヤー」に近い。決定を増やさない"},
        "alternatives": [{"option": "番を終えたプレイヤーが順番を選ぶ（決定を出す）", "reason": "p.325 の決める人を当てはめる読み方。決定が増え、方策・ログが変わる"},
                         {"option": "次の番のプレイヤーから", "reason": "席によらないが、根拠が弱い"}],
        "basis": ["procedures.py:925〜960（SLEEP_COIN_ORDER）", "procedures.py:366〜388（KK1）", "docs/pokemon-check-v0.3b.md", "docs/marker-check-field-reset-v0.91.md 4 章"],
        "unverified": ["BY1 の順番の問いの中身（効果の種類の順番を含む）", "勝率の偏りの計測はしていない"],
    },
    {
        "id": "PC-CHECK-DOUBLE-KNOCKOUT", "name": "ポケモンチェックの両方のきぜつ", "cluster": "pokemon_check", "whole_game": True,
        "decision_refs": ["DEC-KNOCKOUT-READINGS", "DEC-ORDER-RULE"],
        "question": "ポケモンチェックの「どく」などで両方のプレイヤーのポケモンがきぜつするとき、(1) 同時のきぜつか、(2) バトル場に出す順番、(3) サイドを取る順番を決める人",
        "statement": "(1) 同じポケモンチェックの 2 のダメージで両方のプレイヤーのポケモンがきぜつしたら、同時のきぜつとして扱う（勝ち負けは p.311 の表・サドン・デスを含む）。(2)(3) バトル場に出す順番・"
                     "サイドを取る順番は、PC-CHECK-SIDE-ORDER と同じく番を終えたプレイヤーから（利用者の指定 USER-PRIZE-ORDER-ALWAYS-CHOSEN を、この場面に当てるかは利用者が別に決める）",
        "applies_when": "procedures._pokemon_check_plan が POKEMON_CHECK_DOUBLE_KNOCKOUT を返す条件（1・2 のあとに両方のプレイヤーの場に HP 以上のダメージのポケモンがいる）",
        "targets": [_t("UNRESOLVED_POKEMON_CHECK_DOUBLE_KNOCKOUT", "partial", "問いが 3 つ。(1) と (2)(3) は別に採れる。ポケモンチェックの続きで両方のサイド・交代を扱う処理は今ない（needs_implementation を含む）")],
        "excludes": ["ワザの処理の中の同時のきぜつ（利用者の指定 USER-PRIZE-ORDER-* が今のまま扱う）", "ポケモンチェックの途中のきぜつ（PC-CHECK-KO-POINT）"],
        "exceptions": [],
        "depends_on": ["PC-CHECK-SIDE-ORDER"], "related": ["CONV:USER-PRIZE-ORDER-ALWAYS-CHOSEN", "CONV:USER-PRIZE-ORDER-PER-PLAYER"],
        "conflicts_with": [],
        "strict_difference": "厳密は今のまま、ダメージの前に HALTED。プレイ用はダメージを与え、両方のきぜつの処理に進む",
        "impact": {"information": "サイドの取り方は今の公開の範囲（v0.140 のまま）", "rng": "なし（コインを使わない）", "cost": "なし", "order": "バトル場に出す・サイドを取る順番が決まる"},
        "common_implementation": "ポケモンチェックの続き（then が次の番）で、両方のプレイヤーのサイド・バトル場に出す決定の並びを作る（v0.140 はこの場面で prize_first を出さない）",
        "card_specific_remaining": "なし",
        "regression_tests": ["両方どくで両方きぜつする盤面で、勝ち負け・サドン・デス・サイドの並び・バトル場に出す順番", "片方だけのきぜつが今と同じ", "厳密では今と同じ HALTED"],
        "recommendation": {"option": "(1) 同時のきぜつとして扱う。(2)(3) は PC-CHECK-SIDE-ORDER にしたがう",
                           "reason": "p.324 の同時の勝利条件の扱いと合う。決める人は PC-CHECK-SIDE-ORDER と同じにして規約の数を増やさない"},
        "alternatives": [{"option": "(3) に利用者の指定 USER-PRIZE-ORDER-ALWAYS-CHOSEN を広げる（番を終えたプレイヤーに決定を出す）", "reason": "利用者の指定の範囲を変えることになるので、利用者の明示の承認が要る"},
                         {"option": "番を終えたプレイヤーのポケモンが先にきぜつ（同時ではない）", "reason": "ポケモンチェックの 2 のダメージは同時に与えるので、根拠が弱い"}],
        "basis": ["procedures.py:70〜78・_pokemon_check_plan", "docs/prize-order-user-rule-v0.140.md 2 章（ポケモンチェックの続きでは出さない）"],
        "unverified": ["ポケモンチェックの続きの両方のサイドの処理を作る実装の量"],
    },
    {
        "id": "PC-CHECK-KO-POINT", "name": "ポケモンチェックの途中のきぜつの判定の時点", "cluster": "pokemon_check", "whole_game": True,
        "decision_refs": ["DEC-KNOCKOUT-READINGS"],
        "question": "ポケモンチェックの 1（悪エネルギー・くろこげマーカー・きのみ）と 2（どく）のあいだで HP 以上のダメージになったポケモンを、いつきぜつさせるか",
        "statement": "ポケモンチェックの 1・2 の途中ではきぜつを判定しない。2 のあとに 1 回だけ判定する（2 の処理は 1 のあとの場で行い、HP 以上のダメージのポケモンにもどくのダメージを与える）",
        "applies_when": "procedures.mid_check_knockout_divergence が違いを返す（1 のあとに HP 以上になったポケモンがいて、判定の時点で結果が変わる）",
        "targets": [_t("UNRESOLVED_POKEMON_CHECK_MID_KNOCKOUT", "unverified")],
        "excludes": ["2 のあとのきぜつ（今のまま）", "ワザの処理の中のきぜつ"],
        "exceptions": [],
        "depends_on": [], "related": ["PC-CHECK-DOUBLE-KNOCKOUT"], "conflicts_with": [],
        "strict_difference": "厳密は今のまま HALTED",
        "impact": {"information": "なし", "rng": "なし", "cost": "なし", "order": "きぜつの判定の時点"},
        "common_implementation": "_pokemon_check_plan の PK1 の分岐を、規約の照会で 2 のあとの判定に置きかえる",
        "card_specific_remaining": "なし",
        "regression_tests": ["1 で HP 以上になったポケモンがどく状態のときの、ダメージ・きぜつ・ログ", "厳密では今と同じ"],
        "recommendation": {"option": "2 のあとに 1 回だけ判定", "reason": "p.323 の手順の番号順で、途中に判定の手順がない"},
        "alternatives": [{"option": "1 のあとにも判定する", "reason": "手順の途中にきぜつの判定を加える読み方"}],
        "basis": ["procedures.py の _pokemon_check_plan・docs/darkness-metal-energy-v0.78.md 6 章"],
        "unverified": ["mid_check_knockout_divergence のほかの条件"],
    },
    {
        "id": "PC-COIN-COUNT-SHORT", "name": "コインで決まった枚数が足りないとき（途中停止の 2 つ）", "cluster": "count", "whole_game": True,
        "question_kind": "coin_count_short",
        "decision_refs": ["DEC-STATED-COUNT-SHORT", "DEC-DEFERRED-RESUME"],
        "question": "コインの「おもて」の数で決まった枚数のエネルギーをトラッシュする効果で、対象のエネルギーが足りないとき、どうするか",
        "statement": "コインの結果で決まった枚数が、その時点の対象の枚数より多いときは、対象をすべて処理し、足りない分は何もしない（コインの結果・ほかの処理は変えない）",
        "applies_when": "共通の数量処理（check_quantity）で DeferredShortage が起こる場面のうち、DU1（ひからびさせる）・TW1（思念波マシーン）",
        "targets": [_t("UNRESOLVED_DRY_UP_WATER_ENERGY_SHORT", "unverified"), _t("UNRESOLVED_THOUGHT_WAVE_MACHINE_ENERGY_SHORT", "unverified")],
        "excludes": ["ひかるバンギラス neo4-082 の 2 つのワザ（利用者の指定のまま。この規約の根拠にしない・指定を広げない）", "使う前に決まった枚数が足りない（PC-STATED-COUNT-SHORT）",
                     "すでに途中停止した保存状態の再開（DEC-DEFERRED-RESUME。この規約は再開の操作を作らない）"],
        "exceptions": [],
        "depends_on": [], "related": ["PC-STATED-COUNT-SHORT", "POLICY:user_specified_rules:neo4-082/attack/0", "POLICY:user_specified_rules:neo4-082/attack/1"], "conflicts_with": [],
        "strict_difference": "厳密は今のまま途中停止（コインのあとの終端）。プレイ用は止めずに続ける",
        "impact": {"information": "なし（枚数は公開）", "rng": "コインはどちらでも投げる（同じ）", "cost": "なし", "order": "なし"},
        "common_implementation": "engine._interrupted に渡す DeferredShortage を、規約の照会で「あるだけ」の処理に置きかえる（共通の数量処理のチェック地点）",
        "card_specific_remaining": "なし（チェック地点はカードの登録が持つ）",
        "regression_tests": ["足りない盤面での処理・ログ", "足りる盤面が今と同じ", "厳密では今と同じ途中停止"],
        "recommendation": {"option": "あるだけ処理する", "reason": "コインのあとなので「使えない」にできず、途中停止のまま再開の操作もない（GAP-DEFERRED-HALT-NO-RESUME）"},
        "alternatives": [{"option": "効果全体を何もしない（足りなければトラッシュしない）", "reason": "結果が大きく変わる。根拠が弱い"}],
        "basis": ["docs/deferred-shortage-user-promos-v0.127.md 5 章", "engine.py の DeferredShortage の捕まえ方"],
        "unverified": ["2 つのチェック地点の後の処理（あるだけにしたあとの続き）をコードで確かめていない"],
    },
    {
        "id": "PC-STATED-COUNT-SHORT", "name": "説明の決まった枚数が公開の枚数より多いとき", "cluster": "count",
        "question_kind": "stated_count_short",
        "decision_refs": ["DEC-STATED-COUNT-SHORT"],
        "question": "説明が決まった枚数（山札の上から N 枚など）を処理させるのに、使う時点でその場所の枚数が足りないとき、使えるか・どれだけ処理するか",
        "statement": "使う時点で、その場所の公開の枚数が説明の枚数より少ないときは、使える。その場所のカードをすべて処理し、足りない分は何もしない",
        "applies_when": "使う前の確かめで、山札・手札・場などの公開の枚数（中身ではなく枚数）が説明の枚数に足りずに止める場面（対象の一覧のコード）",
        "targets": [_t("UNRESOLVED_ATTACK_DECK_TOP_SHORT"), _t("UNRESOLVED_DECK_TOP_SHORT"), _t("UNRESOLVED_DISCARD_DECK_SHORT"), _t("UNRESOLVED_FLASH_DECK_SHORT"),
                    _t("UNRESOLVED_MASTER_BALL_SHORT_DECK"), _t("UNRESOLVED_MISTYS_WRATH_SHORT_DECK"), _t("UNRESOLVED_POWER_DECK_TOP_SHORT"),
                    _t("UNRESOLVED_STATED_CARDS_SHORT#public-counts", "unverified", "事例の情報の条件は unchecked_per_site（箇所ごとに公開か確かめていない）"),
                    _t("UNRESOLVED_VIRIDIAN_GYM_ONE_COUNTER")],
        "excludes": ["山札の中身（目的のカードの有無・枚数）で決まる場面（PC-HIDDEN-SEARCH-EMPTY。STATED_CARDS_SHORT#deck-contents）", "コインのあとに分かる不足（PC-COIN-COUNT-SHORT）",
                     "ひかるバンギラス neo4-082（利用者の指定のまま）"],
        "exceptions": ["フラッシュ FU1 はおもての山札の問い（PC-FACE-UP-DECK）と重なる。重ねる場合の扱いは FU の規約と組で決める"],
        "depends_on": [], "related": ["PC-COIN-COUNT-SHORT"], "conflicts_with": [],
        "strict_difference": "厳密は今のまま使う前に拒否。プレイ用は使える",
        "impact": {"information": "なし（枚数は公開）", "rng": "使えるようになったカードのコインを投げる", "cost": "カードのトラッシュ・回数の消費が増える", "order": "なし"},
        "common_implementation": "使う前の確かめの拒否を、規約の照会で外し、効果の処理を「あるだけ」にする（効果の型ごとの処理が要る場合がある）",
        "card_specific_remaining": "効果の型ごとの「あるだけ」の処理（山札の上・手札・場で別の処理）",
        "regression_tests": ["足りない盤面での受け付け・処理・ログ・観測", "足りる盤面が今と同じ", "厳密では今と同じ拒否", "対の比べ（枚数だけで決まり、中身によらない）"],
        "recommendation": {"option": "使える（あるだけ処理する）", "reason": "枚数は公開で、秘密に依存しない。PC-COIN-COUNT-SHORT と同じ扱いにそろう"},
        "alternatives": [{"option": "使えない（今の拒否を規約にする）", "reason": "挙動は今と同じ。止める場面の記録を規約に変えるだけ"}],
        "basis": ["台帳の PF-STATED-COUNT-SHORT の候補 P-SCS-1・P-SCS-2"],
        "unverified": ["各コードの拒否が枚数だけで決まるか（中身を読まないか）を、箇所ごとに確かめていない"],
    },
    {
        "id": "PC-USE-WITHOUT-TARGET", "name": "選ぶ対象が最初からないときに使えるか", "cluster": "target",
        "question_kind": "absent_from_start",
        "decision_refs": ["DEC-USE-WITHOUT-EFFECT"],
        "question": "説明が選ばせる対象（控え・場のポケモン・トラッシュのカード・手札など）が、使う宣言の時点で 1 つもないときに、カード・特殊能力・スタジアムを使えるか",
        "statement": "使う宣言の時点で、説明が選ばせる対象が公開の領域（場・トラッシュ）と使う人の手札に 1 つもないときは、使えない（宣言を受け付けない。状態・乱数・ログを変えない。"
                     "トラッシュ・回数の消費・コインもない）",
        "applies_when": "使う前の確かめ（check_playable・check_usable・check_activation）が、対象の一覧が空であることだけを理由に止める場面。対象の有無が公開の情報と使う人の手札だけで決まるもの",
        "targets": [_t(s) for s in (
            "UNRESOLVED_ALL_PURPOSE_POWDER_WITHOUT_TARGET", "UNRESOLVED_BLAINES_QUIZ_WITHOUT_POKEMON", "UNRESOLVED_COMPUTER_SEARCH_EMPTY_DECK",
            "UNRESOLVED_DEVOLUTION_SPRAY_HYPER_WITHOUT_TARGET", "UNRESOLVED_DEVOLUTION_SPRAY_WITHOUT_TARGET", "UNRESOLVED_ENERGY_REMOVAL_WITHOUT_TARGET",
            "UNRESOLVED_ENERGY_RETRIEVAL_WITHOUT_TARGET", "UNRESOLVED_ENERGY_STADIUM_WITHOUT_TARGET", "UNRESOLVED_FOSSILIZE_WITHOUT_TARGET", "UNRESOLVED_FOSSIL_GUIDE_WITHOUT_TARGET",
            "UNRESOLVED_FUCHSIA_GYM_WITHOUT_TARGET", "UNRESOLVED_GUST_WITHOUT_OPPONENT_BENCH", "UNRESOLVED_LAST_RESORT_WITHOUT_TARGET", "UNRESOLVED_LT_SURGE_WITHOUT_BASIC",
            "UNRESOLVED_MAX_REVIVE_WITHOUT_TARGET", "UNRESOLVED_MISTYS_CARE_WITHOUT_TARGET", "UNRESOLVED_MISTYS_WISH_WITHOUT_HAND", "UNRESOLVED_MR_FUJI_WITHOUT_BENCH",
            "UNRESOLVED_OLD_ROD_WITHOUT_TARGET", "UNRESOLVED_POKEMON_FLUTE_WITHOUT_TARGET", "UNRESOLVED_POWER_COUNTER_MOVE_WITHOUT_COUNTERS",
            "UNRESOLVED_POWER_RETURN_WITHOUT_TARGET", "UNRESOLVED_POWER_SWITCH_WITHOUT_OPPONENT_BENCH", "UNRESOLVED_REVIVE_WITHOUT_TARGET", "UNRESOLVED_ROCKET_GRUNT_WITHOUT_BENCH",
            "UNRESOLVED_SABRINA_WITHOUT_TWO_POKEMON", "UNRESOLVED_SCOOP_UP_LAST_POKEMON", "UNRESOLVED_SEARCH_TRAINER_WITHOUT_TARGET#discard",
            "UNRESOLVED_SUPER_ENERGY_RETRIEVAL_WITHOUT_TARGET", "UNRESOLVED_SUPER_ROD_WITHOUT_TARGET", "UNRESOLVED_SWITCH_WITHOUT_BENCH",
            "UNRESOLVED_THOUGHT_WAVE_MACHINE_WITHOUT_TARGET", "UNRESOLVED_TIME_SHIFT_WITHOUT_TARGET", "UNRESOLVED_TRAINER_UP_TO_WITHOUT_TARGET#public-zones",
            "UNRESOLVED_TRAINER_WITHOUT_TARGET", "UNRESOLVED_TRANSPORT_WITHOUT_CARDS", "UNRESOLVED_WANT_WITHOUT_TARGET")]
        + [_t("UNRESOLVED_NINJA_GYM_WITHOUT_TARGET", "needs_secret_review",
              "使う前の確かめが山札の中身を読む漏れ（PSP-NJ1-NINJA-GYM-ORACLE。この調査の比較プローブで確かめた）。v0.146 で、配分を読まない下限で止めるように直した"
              "（提案の時点は blocked_by_defect）。山札を探すので PC-HIDDEN-SEARCH-EMPTY の対象でもあり、規約を採る前に対の比べの確かめ直しが要る（ST1 の #deck と同じ扱い）")],
        "excludes": ["山札（非公開）を探す場面（PC-HIDDEN-SEARCH-EMPTY）", "対象はあるが何も起こらない場面（PC-USE-WITHOUT-EFFECT・PC-CHOOSE-TARGET-WITHOUT-EFFECT）",
                     "効果の途中で対象がいなくなる場面（PC-TARGET-LOST-MID-EFFECT）", "コストを払えない場面（個別。PW2）", "「最大N」の 0（PC-UP-TO-ZERO）"],
        "exceptions": ["コインだけを投げて使い終われるかの問い（BP1・EN1・FG2・GU1・SX1・WT1・VN1・HF1 など。コインのあとに対象を選ぶ）も、この規約では「使えない」（コインを投げない）",
                       "kyuura・エンジンの記録が「ほかのカードの答えを流用しない」と書くカード（RG1・SU2・HY1 など）は、規約の対象の一覧で個別に承認する（一括の承認にしない）"],
        "depends_on": [], "related": ["PC-HIDDEN-SEARCH-EMPTY"], "conflicts_with": [],
        "strict_difference": "挙動の差はない（今の拒否と同じ）。プレイ用では、止める理由が未決の裁定から規約による拒否に変わる（記録・ログの区別だけ）",
        "impact": {"information": "変えない（今の拒否と同じ。対象の有無は公開・本人の手札で決まる）", "rng": "変えない", "cost": "変えない", "order": "なし"},
        "common_implementation": "止める箇所に事例の識別と規約の照会を加え、規約があれば「規約による拒否」（未決の裁定の停止と区別した記録）にする。処理は変えない",
        "card_specific_remaining": "なし（対象の一覧の承認だけ）",
        "regression_tests": ["対象のない盤面で、拒否の種類・状態・乱数・ログが変わらない", "対象がある盤面が今と同じ", "対の比べ（公開・本人の手札だけで決まる）"],
        "recommendation": {"option": "使えない", "reason": "今の挙動のまま（実装・乱数・情報の変更がない）。拒否は対戦を止めない（ほかの操作を選べる）ので、続行の効果は記録の区別だけ"},
        "alternatives": [{"option": "使える（カードはトラッシュ・回数は消費・コインは投げる。対象のない部分は何もしない）", "reason": "台帳の P-UWE-2。山札を減らす・コインを投げる使い方が増える。効果の型ごとの処理が要る"}],
        "basis": ["台帳の PF-USE-WITHOUT-EFFECT の候補 P-UWE-1・P-UWE-2", "各コードの理由の文（effects.py の *_REASON）"],
        "unverified": ["各コードの止める条件が対象の有無だけで、公開・本人の手札だけで決まることを、箇所ごとに比べの道具で確かめていない（NJ1 の漏れは見つけた）"],
    },
    {
        "id": "PC-HIDDEN-SEARCH-EMPTY", "name": "山札を探す効果で、目的のカードが見つからないとき", "cluster": "target",
        "question_kind": "hidden_search_empty",
        "decision_refs": ["DEC-USE-WITHOUT-EFFECT", "DEC-INFO-LEAK-FIXES"],
        "question": "山札（非公開）から決まったカードを選ぶ効果を、山札に目的のカードがないかもしれないとき（本人に見えない）に使えるか。見つからなければどうなるか",
        "statement": "山札から決まったカードを選ぶ効果は、山札にカードが 1 枚以上あれば使える（目的のカードの有無で使えるかを変えない）。山札を見て目的のカードがなければ何も選ばず、"
                     "説明のほかの処理（山札を切るなど）を行う",
        "applies_when": "使う前の確かめが、山札の中身の下限（effects.deck_target_lower_bound・bench_entry_unconfirmed）で止める場面（事例の secret_dependency が owner_known_pool・depends_on_hidden_static）",
        "targets": [_t("UNRESOLVED_SEARCH_TRAINER_WITHOUT_TARGET#deck", "needs_secret_review"), _t("UNRESOLVED_STATED_CARDS_SHORT#deck-contents", "needs_secret_review"),
                    _t("UNRESOLVED_TRAINER_UP_TO_WITHOUT_TARGET#amplifier-deck", "needs_secret_review"),
                    _t("UNRESOLVED_EVOLUTION_PERMISSION_FROM_DECK#coin-evolve-self-from-deck", "blocked_by_defect", "PSP-DECK-CONTENT-PRECHECKS の残り（GV1 の経路。未確認の漏れの候補）")],
        "excludes": ["公開の領域（トラッシュ）を探す場面（PC-USE-WITHOUT-TARGET）", "山札の枚数（公開）が足りない場面（PC-STATED-COUNT-SHORT）"],
        "exceptions": ["山札が 0 枚（公開）のときは PC-USE-WITHOUT-TARGET と同じ（使えない）"],
        "depends_on": [], "related": ["PC-USE-WITHOUT-TARGET"], "conflicts_with": [],
        "strict_difference": "厳密は今の保守的な下限で止める。プレイ用は使えて、見つからなければ何も選ばない",
        "impact": {"information": "使う人だけが山札を見る（見つからないことは使う人にだけ分かる。相手には何も選ばなかったことが公開）", "rng": "山札を切る説明なら乱数を使う",
                   "cost": "カードのトラッシュ・回数の消費", "order": "なし"},
        "common_implementation": "探して見つからない処理（決定の 0 個の答え・ログ）を共通にする。下限の確かめを規約の照会で外す",
        "card_specific_remaining": "効果の型ごとの見つからないときの続き（山札を切る・手札に加えないなど）",
        "regression_tests": ["目的のカードが山札・サイドにある 2 盤面の対の比べ（受理・拒否・理由・候補が同じ）", "見つからないときのログ・観測（相手に中身が伝わらない）", "厳密では今と同じ"],
        "recommendation": {"option": "使える（見つからなければ何も選ばない）", "reason": "受け付けが山札の配分によらないので、v0.137・v0.138 の下限による保守的な制限より秘密に強い。実際の対戦の扱いに近い"},
        "alternatives": [{"option": "今の下限で止める（規約にする）", "reason": "挙動は今と同じ。保守的に使えない場面が残る"}],
        "basis": ["docs/deck-search-oracle-v0.137.md", "docs/oracle-leak-fixes-v0.138.md", "台帳の事例の secret_dependency"],
        "unverified": ["見つからない処理の実装の量", "GV1 の経路の漏れの比べ（未確認）"],
    },
    {
        "id": "PC-USE-WITHOUT-EFFECT", "name": "使っても何も起こらないときに使えるか", "cluster": "target",
        "question_kind": "target_without_effect",
        "decision_refs": ["DEC-USE-WITHOUT-EFFECT"],
        "question": "回復・特殊状態の回復など、使っても何も起こらない（ダメージ・特殊状態がない）ときに、カード・特殊能力を使えるか",
        "statement": "使う宣言の時点で、効果が当たりうるポケモン（ダメージカウンター・特殊状態のあるポケモン）が 1 匹もいないときは、使えない（宣言を受け付けない。状態・乱数・ログを変えない）",
        "applies_when": "使う前の確かめが、効果の起こるポケモンがいないことだけを理由に止める場面（対象の一覧のコード）",
        "targets": [_t(s) for s in ("UNRESOLVED_POTION_WITHOUT_DAMAGE", "UNRESOLVED_FULL_HEAL_WITHOUT_CONDITION", "UNRESOLVED_SOLAR_POWER_WITHOUT_CONDITION",
                                    "UNRESOLVED_HELPING_HAND_WITHOUT_CONDITION", "UNRESOLVED_CELADON_GYM_WITHOUT_CONDITION", "UNRESOLVED_POWER_HEAL_WITHOUT_DAMAGE",
                                    "UNRESOLVED_HEALING_FIELD_WITHOUT_DAMAGE")],
        "excludes": ["選ぶ対象そのものがない場面（PC-USE-WITHOUT-TARGET）", "効果のないポケモンを選べるか（PC-CHOOSE-TARGET-WITHOUT-EFFECT）"],
        "exceptions": ["ばんのうごな BP1 は、ダメージと特殊状態の片方だけがあればある方を処理する（今のまま）。両方ないときは PC-USE-WITHOUT-TARGET の対象として記録した"],
        "depends_on": [], "related": ["PC-CHOOSE-TARGET-WITHOUT-EFFECT", "PC-USE-WITHOUT-TARGET"], "conflicts_with": [],
        "strict_difference": "挙動の差はない（今の拒否と同じ）。止める理由の記録だけが変わる",
        "impact": {"information": "変えない（ダメージ・特殊状態は公開）", "rng": "変えない", "cost": "変えない", "order": "なし"},
        "common_implementation": "PC-USE-WITHOUT-TARGET と同じ（規約による拒否の記録）",
        "card_specific_remaining": "なし",
        "regression_tests": ["何も起こらない盤面で、拒否・状態・乱数・ログが変わらない", "起こる盤面が今と同じ"],
        "recommendation": {"option": "使えない", "reason": "今の挙動のまま。拒否は対戦を止めない"},
        "alternatives": [{"option": "使える（カードをトラッシュし、回数を消費し、何もしない）", "reason": "ジム・特殊能力の「番に 1 回」を使い切る使い方が増える"}],
        "basis": ["kyuura の UQ-TARGET-WITHOUT-EFFECT・UQ-CARD-USE-WITHOUT-TARGET（台帳の研究の記録）"],
        "unverified": ["箇所ごとの止める条件"],
    },
    {
        "id": "PC-CHOOSE-TARGET-WITHOUT-EFFECT", "name": "選んでも何も起こらないポケモンを選べるか", "cluster": "target",
        "question_kind": "target_without_effect",
        "decision_refs": ["DEC-USE-WITHOUT-EFFECT"],
        "question": "回復などの対象を選ぶとき、ダメージカウンターののっていないポケモン（選んでも何も起こらない）を選べるか",
        "statement": "効果の対象を選ぶときは、選んで効果が起こるポケモンがいる限り、何も起こらないポケモンは選べない（候補に出さない）",
        "applies_when": "対象の選び方の確かめで、選んだポケモンに効果が起こらないことを理由に止める場面（対象の一覧のコード）",
        "targets": [_t(s) for s in ("UNRESOLVED_POTION_UNDAMAGED_TARGET", "UNRESOLVED_SUPER_POTION_UNDAMAGED_TARGET", "UNRESOLVED_LAST_RESORT_UNDAMAGED_TARGET",
                                    "UNRESOLVED_SABRINA_SOURCE_WITHOUT_ENERGY", "UNRESOLVED_MOOMOO_MILK_UNDAMAGED_TARGET")],
        "excludes": ["効果が起こるポケモンが 1 匹もいない（PC-USE-WITHOUT-EFFECT）"],
        "exceptions": [],
        "depends_on": ["PC-USE-WITHOUT-EFFECT"], "related": [], "conflicts_with": [],
        "strict_difference": "今の止め方（どの経路で止めるかはコードごと）を規約による候補の制限に変える",
        "impact": {"information": "変えない（公開）", "rng": "変えない", "cost": "変えない", "order": "なし"},
        "common_implementation": "候補の作り方に規約の照会を加える（候補を黙って減らさない: 規約で減らしたことを記録する）",
        "card_specific_remaining": "候補の作り方はカードの型ごと",
        "regression_tests": ["効果のあるポケモンとないポケモンがいる盤面で、候補・答えの受け付け", "厳密では今と同じ"],
        "recommendation": {"option": "選べない", "reason": "候補を減らすだけで、乱数・情報は変わらない"},
        "alternatives": [{"option": "選べる（何も起こらない）", "reason": "いいきずぐすりのエネルギーのトラッシュなど、効果の一部だけを使う使い方が増える（効果の型ごとに結果が違う）"}],
        "basis": ["kyuura の UQ-TARGET-WITHOUT-EFFECT（台帳の研究の記録）"],
        "unverified": ["箇所ごとの止め方（使う前の拒否か、答えの拒否か）"],
    },
    {
        "id": "PC-UP-TO-ZERO", "name": "「最大N」「好きなだけ」で 0 を選べるか", "cluster": "count",
        "decision_refs": ["DEC-UP-TO-ZERO"],
        "question": "「最大 N 枚」「好きなだけ」で選ぶとき、選べる候補があっても 0 を選べるか",
        "statement": "「最大 N」「好きなだけ」と書かれた選び方では、選べる候補があっても 0 を選べる（0 を選んだら、その選び方の結果の処理だけを行わない）",
        "applies_when": "答えの確かめが 0 個の答えを止める場面（台帳の PF-UP-TO-ZERO。止め方は answer_rejection）",
        "targets": [_t(s) for s in ("UNRESOLVED_ATTACH_FROM_DISCARD_ZERO", "UNRESOLVED_BENCH_TARGETS_ZERO_CHOICE", "UNRESOLVED_DISCARD_ANY_NUMBER_ZERO",
                                    "UNRESOLVED_DISCARD_UP_TO_ZERO", "UNRESOLVED_ENERGY_RETRIEVAL_ZERO_CHOICE", "UNRESOLVED_HEAL_UP_TO_ZERO",
                                    "UNRESOLVED_NIGHTLY_GARBAGE_RUN_ZERO_CHOICE", "UNRESOLVED_POKEDEX_UP_TO_ZERO", "UNRESOLVED_RECOVER_ZERO_ENERGY",
                                    "UNRESOLVED_ROCKETS_TRAP_ZERO_CHOICE", "UNRESOLVED_SUPER_ENERGY_RETRIEVAL_ZERO_CHOICE", "UNRESOLVED_TRAINER_UP_TO_ZERO_CHOICE")]
        + [_t("UNRESOLVED_POWER_ZERO_CARDS", "blocked_by_defect", "PSP-INCREASE-ENTRY-PW3-ORACLE（未修正の漏れ）")],
        "excludes": ["「N 枚」（最大と書かれていない）", "選べる候補がない場面（PC-USE-WITHOUT-TARGET）"],
        "exceptions": [],
        "depends_on": [], "related": [], "conflicts_with": [],
        "strict_difference": "厳密は今のまま 0 個の答えを受け付けない（ほかの答えは受け付ける）。プレイ用は 0 個も受け付ける",
        "impact": {"information": "変えない（候補は今のまま）", "rng": "なし", "cost": "使う宣言のコストは今のまま", "order": "なし"},
        "common_implementation": "答えの確かめの 0 個の拒否を、規約の照会で受け付けに変える（答えの範囲の確かめは共通の部品）",
        "card_specific_remaining": "0 個のときの続き（山札を切るか・ログ）がカードの型ごとに違う場合がある",
        "regression_tests": ["0 個の答えの受け付け・続き・ログ", "1 個以上の答えが今と同じ", "厳密では今と同じ"],
        "recommendation": {"option": "0 を選べる", "reason": "「最大」の語のまま。答えの範囲が広がるだけで、乱数・情報は変わらない"},
        "alternatives": [{"option": "候補があれば 1 以上（今の拒否を規約にする）", "reason": "挙動は今と同じ"}],
        "basis": ["台帳の PF-UP-TO-ZERO の候補 P-UTZ-1・P-UTZ-2", "kyuura の UQ-UP-TO-ZERO-CHOICE"],
        "unverified": ["0 個のときの続きをコードごとに確かめていない"],
    },
    {
        "id": "PC-NON-ATTACK-DAMAGE-MODIFIERS", "name": "ワザ以外のダメージに、ダメージを変える効果を当てはめるか", "cluster": "damage", "whole_game": True,
        "decision_refs": ["DEC-DAMAGE-READINGS"],
        "question": "ワザのダメージでないダメージ（どく・こんらんの自分へのダメージ・特殊能力・トレーナー・スタジアム・エネルギーのダメージ）に、受けるダメージ・与えるダメージを変える効果を当てはめるか",
        "statement": "ワザのダメージでないダメージには、ダメージの量を変える効果（受けるダメージ・与えるダメージを変える特殊能力・トレーナー・エネルギー・持続する効果）を当てはめない。"
                     "その効果の説明が、そのダメージを名指ししている場合だけ当てはめる",
        "applies_when": "ワザ以外のダメージの量を求めるとき、量を変える効果があって、当てはめるかで量が変わる場面（対象の一覧のコード）",
        "targets": [_t("UNRESOLVED_POISON_DAMAGE_RECEIVED_POWER", "unverified", "ポケモンチェックの HALTED（KA1）"), _t("UNRESOLVED_CONFUSION_DAMAGE_MODIFIERS"),
                    _t("UNRESOLVED_POWER_DAMAGE_RECEIVED_POWER"), _t("UNRESOLVED_INFLATE_NON_ATTACK_DAMAGE"), _t("UNRESOLVED_MINEFIELD_DAMAGE_RECEIVED_POWER"),
                    _t("UNRESOLVED_RAINBOW_DAMAGE_RECEIVED_POWER"), _t("UNRESOLVED_TRAINER_DAMAGE_REDUCTION"), _t("UNRESOLVED_DARKNESS_DAMAGE_RECEIVED_POWER"),
                    _t("UNRESOLVED_DOUBLED_DAMAGE_POWER_DAMAGE"), _t("UNRESOLVED_GROWL_NON_ATTACK_DAMAGE")],
        "excludes": ["弱点・抵抗力（PC-UNSTATED-WEAKNESS-RESISTANCE）", "ワザのダメージ（今のまま）", "効果を当てはめる順番（鋼エネルギーと特殊能力の MT1 など。個別）",
                     "説明に「〜に関係なく」とあるダメージ（今のまま当てはめない）"],
        "exceptions": ["くろこげマーカーのダメージの FA1（「その他の効果」に関係なく）の読み方は別の問い（個別）"],
        "depends_on": [], "related": ["PC-UNSTATED-WEAKNESS-RESISTANCE"], "conflicts_with": [],
        "strict_difference": "厳密は今のまま拒否・HALTED（KA1）。プレイ用は当てはめずに続ける",
        "impact": {"information": "なし", "rng": "なし", "cost": "なし", "order": "なし（量だけ）"},
        "common_implementation": "ワザ以外のダメージの計算の共通の部品（ダメージの量の問い合わせ）に、規約の照会を加える",
        "card_specific_remaining": "名指しの判定（説明がそのダメージを名指ししているか）はカードの登録ごと",
        "regression_tests": ["どく・こんらん・特殊能力・トレーナーのダメージで、量・ログ", "ワザのダメージが今と同じ", "厳密では今と同じ"],
        "recommendation": {"option": "当てはめない", "reason": "p.321 のダメージの計算はワザによるダメージの手順で、ワザ以外のダメージの手順はない。こんらんの自分へのダメージ（道具の対戦で拒否が多い）も含めて、1 つの規約で扱える"},
        "alternatives": [{"option": "受けるダメージを変える効果だけ当てはめる（与える側は当てはめない）", "reason": "「受けるダメージ」の語を広く読む読み方。効果の種類で分ける必要がある"},
                         {"option": "すべて当てはめる", "reason": "ワザのダメージと同じに扱う読み方"}],
        "basis": ["kyuura の UQ-NON-ATTACK-DAMAGE-MODIFIERS（6 コード）", "procedures.py の POISON_RECEIVED_POWER（KA1）"],
        "unverified": ["コードごとに、規約を当てた後の処理に別の停止がないか"],
    },
    {
        "id": "PC-UNSTATED-WEAKNESS-RESISTANCE", "name": "「弱点・抵抗力に関係なく」と書かれていないワザ以外・控えへのダメージの弱点・抵抗力", "cluster": "damage",
        "decision_refs": ["DEC-DAMAGE-READINGS"],
        "question": "説明に「弱点・抵抗力」に関係なく、と書かれていない、控えへのワザのダメージ・特殊能力のダメージに、弱点・抵抗力を計算するか",
        "statement": "弱点・抵抗力は、ワザで相手の対戦ポケモンに与えるダメージだけに計算する。控えへのダメージ・特殊能力のダメージには、説明に書かれていなくても計算しない",
        "applies_when": "控えへのワザのダメージ（JS1）・特殊能力のダメージ（Z9）で、受けるポケモンの弱点・抵抗力が与えるポケモンのタイプのときだけ（今の止める条件）",
        "targets": [_t("UNRESOLVED_BENCH_DAMAGE_WEAKNESS_RESISTANCE"), _t("UNRESOLVED_POWER_DAMAGE_WEAKNESS_RESISTANCE")],
        "excludes": ["ワザの対戦ポケモンへのダメージ（今のまま計算する）", "英語版の「Apply Weakness and Resistance」を根拠にしない"],
        "exceptions": [], "depends_on": [], "related": ["PC-NON-ATTACK-DAMAGE-MODIFIERS"], "conflicts_with": [],
        "strict_difference": "厳密は今のまま拒否。プレイ用は計算しないで続ける",
        "impact": {"information": "なし", "rng": "なし", "cost": "なし", "order": "なし"},
        "common_implementation": "弱点・抵抗力の計算の部品に規約の照会を加える",
        "card_specific_remaining": "なし",
        "regression_tests": ["控え・特殊能力のダメージの量", "対戦ポケモンへのワザのダメージが今と同じ"],
        "recommendation": {"option": "計算しない", "reason": "p.321 の計算の手順はワザの対戦ポケモンへのダメージ"},
        "alternatives": [{"option": "計算する", "reason": "書かれていない以上は通常の計算をする読み方"}],
        "basis": ["effects.py の POWER_DAMAGE_WR_REASON（Z9）", "kyuura の UQ-BENCH-DAMAGE-WEAKNESS-RESISTANCE・UQ-POWER-DAMAGE-WEAKNESS-RESISTANCE"],
        "unverified": ["JS1 が控えへのワザのダメージのどの説明の型か（コードで確かめていない）"],
    },
    {
        "id": "PC-SPECIAL-ENERGY-CARD-WORDING", "name": "特殊エネルギーカードは「X エネルギーカード」か", "cluster": "energy",
        "decision_refs": ["DEC-ENERGY-READINGS"],
        "question": "レインボーエネルギー・ミラクルエネルギーなど、X のエネルギーを出す特殊エネルギーカードを、説明の「X エネルギーカード」「基本エネルギーカード」に数えるか",
        "statement": "説明の「X エネルギーカード」（カードを指す語）には、基本 X エネルギーカードだけが当たる。特殊エネルギーカードは、場で X のエネルギーを出していても当たらない。"
                     "「X エネルギー」（出しているエネルギーを指す語）は、今のとおり出しているエネルギーで数える",
        "applies_when": "説明が「X エネルギーカード」を数える・選ぶ・トラッシュする場面で、特殊エネルギーカードが X を出していて、数えるかで結果が変わる（対象の一覧のコード）",
        "targets": [_t(s) for s in ("UNRESOLVED_BUZZAP_ENERGY_CARD_TYPE", "UNRESOLVED_RAINBOW_AS_BASIC_ENERGY_CARD", "UNRESOLVED_RAINBOW_ATTACH_AS_TYPE",
                                    "UNRESOLVED_RAINBOW_ENERGY_TYPE", "UNRESOLVED_TRANSFORM_SPECIAL_ENERGY", "UNRESOLVED_MIRACLE_ENERGY_AS_TYPE",
                                    "UNRESOLVED_RAINBOW_RECOVER_AS_TYPE", "UNRESOLVED_FERVOR_RAINBOW_ENERGY", "UNRESOLVED_COLOR_CHANGED_ENERGY_CARD")],
        "excludes": ["色を変える効果の続く間・順番（CE1・CE2・VS1。個別）", "きせきのかぜ（WD1・WD2・MEW1。個別）", "にげるのコストの払い方（PC-RETREAT-COST-PAYMENT）"],
        "exceptions": ["［エネエネ］で役割が変わったカード（BZ2）は、役割の記録の読み方と組（コードで確かめていない）"],
        "depends_on": [], "related": [], "conflicts_with": [],
        "strict_difference": "厳密は今のまま拒否。プレイ用は基本エネルギーカードだけを数えて続ける",
        "impact": {"information": "なし", "rng": "なし", "cost": "トラッシュするカードの選び方が変わる", "order": "なし"},
        "common_implementation": "エネルギーカードの種類を数える共通の部品に規約の照会を加える",
        "card_specific_remaining": "特殊エネルギーカードの登録ごとの役割",
        "regression_tests": ["レインボー・ミラクルがついた盤面で、数え方・選べる候補", "基本エネルギーだけの盤面が今と同じ"],
        "recommendation": {"option": "基本 X エネルギーカードだけ", "reason": "カードを指す語と出しているエネルギーを指す語を分ける読み方で、ほかのカードの記録と合わせやすい"},
        "alternatives": [{"option": "場で X を出しているあいだは X エネルギーカードとして数える", "reason": "場と場の外で数え方が変わる"}],
        "basis": ["kyuura の UQ-SPECIAL-ENERGY-AS-TYPED-ENERGY（5 コード）"],
        "unverified": ["コードごとの止める条件（数え方の違いだけか）"],
    },
    {
        "id": "PC-RETREAT-COST-PAYMENT", "name": "にげるのコストの払い方", "cluster": "energy",
        "question_kind": "cost_unpayable",
        "decision_refs": ["DEC-ENERGY-READINGS"],
        "question": "にげるのコストを、出すエネルギーが 2 個以上のカードで払うとき余ってよいか、コストを減らす効果で 0 より小さくなるとき",
        "statement": "にげるのコストは、トラッシュするエネルギーカードの出すエネルギーの合計がコスト以上になるように払う。どのカードを除いてもコストに足りなくなる組だけを選べる（余りは捨てる）。"
                     "コストを減らす効果で 0 より小さくなったら 0",
        "applies_when": "にげるで、トラッシュするエネルギーの出すエネルギーがコストより多い（RT1）・コストの計算が 0 を下回る（CP2）",
        "targets": [_t("UNRESOLVED_RETREAT_OVERPAY"), _t("UNRESOLVED_RETREAT_COST_FLOOR")],
        "excludes": ["ワザのエネルギーのコスト（今のまま）"], "exceptions": [],
        "depends_on": [], "related": [], "conflicts_with": [],
        "strict_difference": "厳密は今のまま拒否。プレイ用は払い方の決まりで続ける",
        "impact": {"information": "なし", "rng": "なし", "cost": "トラッシュするカード", "order": "なし"},
        "common_implementation": "にげるのコストの確かめ（共通の手順）に規約の照会を加える",
        "card_specific_remaining": "なし",
        "regression_tests": ["2 個のエネルギーを出すカードで 1 のコストを払う盤面", "通常のにげるが今と同じ"],
        "recommendation": {"option": "最小の組で払い、余りは捨てる。0 を下回ったら 0", "reason": "1 つの手順の中の 2 つの問いで、同じ論点（kyuura の UQ-RETREAT-COST-PAYMENT）"},
        "alternatives": [{"option": "余るカードでは払えない", "reason": "出すエネルギーの多いカードではにげられない場面が出る"}],
        "basis": ["kyuura の UQ-RETREAT-COST-PAYMENT"], "unverified": ["2 つのコードの止める条件の細部"],
    },
    {
        "id": "PC-NULLIFIED-ELEMENT-COIN", "name": "効果がはたらかない要素のコインを投げるか", "cluster": "coin",
        "decision_refs": ["DEC-NULLIFIED-COINS"],
        "question": "ワザ・効果の要素が、相手の「ダメージ・効果を受けない」「とうめい」などではたらかないと分かっているとき、その要素のコインを投げるか",
        "statement": "はたらかないことがコインの前に分かっている要素のコインも、説明どおりに投げる（乱数を使う）。結果はその要素に使わない。ほかの要素の処理は変えない",
        "applies_when": "要素のコインの前に、その要素の効果が無効（受けない・とうめい・［KEEP］など）と分かっていて、投げるかで乱数の列・ログが変わる場面（対象の一覧のコード）",
        "targets": [_t(s) for s in ("UNRESOLVED_EVADED_EFFECT_COIN", "UNRESOLVED_PREVENTED_COIN_DAMAGE", "UNRESOLVED_PREVENTED_EFFECT_COIN",
                                    "UNRESOLVED_DISCARD_PROTECTED_COIN", "UNRESOLVED_KEEP_VOIDED_DISCARD_COIN")],
        "excludes": ["対象の選び方の問い（KP1・LO1。個別）", "ダメージのない要素のあとの効果（Z23。個別）"],
        "exceptions": [], "depends_on": [], "related": [], "conflicts_with": [],
        "strict_difference": "厳密は今のまま拒否。プレイ用は投げて続ける",
        "impact": {"information": "コインの結果は公開", "rng": "乱数の列がずれる（投げない案でもずれる。どちらでも規約集合の識別で比べ分ける）", "cost": "なし", "order": "なし"},
        "common_implementation": "要素のコインの共通の部品に規約の照会を加える",
        "card_specific_remaining": "なし",
        "regression_tests": ["無効の盤面でのコイン・ログ・乱数の消費", "無効でない盤面が今と同じ", "厳密では今と同じ"],
        "recommendation": {"option": "投げる", "reason": "説明の手順のとおりで、要素ごとの「はたらかない」の判定をコインの前に読む必要がない"},
        "alternatives": [{"option": "投げない", "reason": "結果を使わないコインを省く読み方"}],
        "basis": ["kyuura の UQ-COIN-IN-NULLIFIED-ELEMENT（3 コード）"], "unverified": ["AP1・KP2 が同じ問いの型か（停止の文から当てた）"],
    },
    {
        "id": "PC-ORDER-ATTACK-PRECHECK", "name": "ワザのダメージの前の複数のコインの順番", "cluster": "order",
        "decision_refs": ["DEC-ORDER-RULE"],
        "question": "ワザを使うとき、ダメージの前に投げる複数のコイン（こんらん・ベイビィポケモンのルール・相手のとうめい・ジムなど）の順番",
        "statement": "ワザを使うとき、ダメージの前に投げる複数のコインは、ワザを使うプレイヤー（番のプレイヤー）が順番を選ぶ（決定を出す）。順番によらず結果の組が同じなら決定を出さない（今のまま）",
        "applies_when": "ワザの宣言からダメージまでのあいだに、2 つ以上のコインの処理があり、順番で結果が変わる場面（対象の一覧のコード）",
        "targets": [_t(s) for s in ("UNRESOLVED_ATTACK_CHECK_CONFUSION", "UNRESOLVED_BABY_RULE_COIN_ORDER", "UNRESOLVED_MULTIPLE_ATTACK_CHECKS",
                                    "UNRESOLVED_VERMILION_GYM_ATTACK_ORDER", "UNRESOLVED_TRANSPARENCY_COIN_ORDER", "UNRESOLVED_BENCH_COIN_TRANSPARENCY_ORDER",
                                    "UNRESOLVED_NINJA_TRICK_ATTACK_COIN_ORDER")],
        "excludes": ["ポケモンチェックの中（PC-CHECK-SIDE-ORDER）", "錯乱ジムとちえくらべ（MG1。利用者の指定 USER-MIND-GAMES-OPTIONAL-BEFORE-COST の範囲の判断が先。個別）"],
        "exceptions": [], "depends_on": [], "related": ["PC-ORDER-OVERLAP"], "conflicts_with": [],
        "strict_difference": "厳密は今のまま拒否。プレイ用は決定を出して続ける",
        "impact": {"information": "コインは公開", "rng": "どのコインが乱数のどの値になるかが、選んだ順番で決まる", "cost": "なし", "order": "決定が増える"},
        "common_implementation": "順番の決定（並びを選ぶ決定）を共通の部品にする。v0.140 の prize_first と同じ形の決定",
        "card_specific_remaining": "なし",
        "regression_tests": ["2 つのコインがある盤面で、決定・答えごとの結果", "順番によらない盤面が今と同じ（決定が出ない）", "厳密では今と同じ"],
        "recommendation": {"option": "番のプレイヤーが選ぶ", "reason": "ワザの手順は番のプレイヤーが進める。p.325 の「番のプレイヤーが決める」に近い"},
        "alternatives": [{"option": "p.309 の手順の番号順・同じ番号なら説明の順", "reason": "決定を増やさないが、手順の番号で分からないものが残る"}],
        "basis": ["kyuura の UQ-ATTACK-PRE-DAMAGE-COIN-ORDER（4 コード）・UQ-TRANSPARENCY-COIN-ORDER（2 コード）"],
        "unverified": ["NT1 が同じ型か（停止の文から当てた）"],
    },
    {
        "id": "PC-ORDER-OVERLAP", "name": "同じ時点にはたらく複数の効果の当てはめの順番", "cluster": "order",
        "decision_refs": ["DEC-ORDER-RULE"],
        "question": "同じ時点にはたらく 2 つ以上の効果（ダメージを防ぐ・きぜつを防ぐ・持続する効果・特殊状態の上書き・反応など）を、どの順番で当てはめるか",
        "statement": "同じ時点にはたらく複数の効果の順番で結果が変わるときは、その時点の番のプレイヤーが順番を選ぶ（決定を出す）。順番によらず結果が同じなら決定を出さない（今のまま）",
        "applies_when": "ワザ・トレーナー・特殊能力の処理の中で、同時の効果が 2 つ以上あり、順番で結果が変わる場面（対象の一覧のコード）。ポケモンチェックは除く",
        "targets": [_t(s, "unverified") for s in ("UNRESOLVED_DAMAGE_GUARD_OVERLAP", "UNRESOLVED_REFLECT_SHIELD_OVERLAP", "UNRESOLVED_TIME_TRAVEL_OVERLAP",
                                                  "UNRESOLVED_KO_PREVENTION_ORDER", "UNRESOLVED_KO_SURVIVAL_OVERLAP", "UNRESOLVED_KOGA_POISON_ORDER",
                                                  "UNRESOLVED_SPECIAL_POISON_OVERWRITE", "UNRESOLVED_MULTIPLE_DAMAGE_TRIGGERS", "UNRESOLVED_POST_KNOCKOUT_POWERS_ORDER",
                                                  "UNRESOLVED_GROUP_POWER_COIN_ORDER")],
        "excludes": ["ポケモンチェック（PC-CHECK-SIDE-ORDER）", "ワザのダメージの前のコイン（PC-ORDER-ATTACK-PRECHECK）",
                     "効果の種類の優先（色のマーカー CM1・色の置きかえ CE2・最大HP の MH2・どくの量の合わせ方 PO1・鋼エネルギーと特殊能力 MT1）: 順番ではなく、どの効果が勝つかの読み方（個別）"],
        "exceptions": ["サイドを取る順番は利用者の指定のまま（この規約に入れない）"],
        "depends_on": [], "related": ["PC-ORDER-ATTACK-PRECHECK"], "conflicts_with": ["PC-CHECK-SIDE-ORDER（ポケモンチェックには当てない）"],
        "strict_difference": "厳密は今のまま拒否。プレイ用は決定を出して続ける",
        "impact": {"information": "決定の候補は公開の効果だけ", "rng": "コインを含む効果は割り当てが変わる", "cost": "なし", "order": "決定が増える"},
        "common_implementation": "PC-ORDER-ATTACK-PRECHECK と同じ順番の決定の部品",
        "card_specific_remaining": "効果ごとの「同時」の判定は登録のまま",
        "regression_tests": ["2 つの効果がある盤面で、答えごとの結果", "順番によらない盤面が今と同じ", "厳密では今と同じ"],
        "recommendation": {"option": "番のプレイヤーが選ぶ", "reason": "p.325 の「同時に起こるときは番のプレイヤーが順番を決める」に近い（研究上の当てはめは未解決）"},
        "alternatives": [{"option": "効果を受けるポケモンの持ち主が選ぶ", "reason": "受ける側の効果の重なりでは自然だが、両方の側の効果が混ざると決まらない"}],
        "basis": ["台帳の PF-SIMULTANEOUS-ORDER の候補 P-SO-1〜3"],
        "unverified": ["対象の 10 コードが同じ型か（停止の文・裁定の記録の行から当てた。コードごとに確かめていない）"],
    },
    {
        "id": "PC-SUPPRESSION-LATER-POKEMON", "name": "特殊能力を消す効果は、あとから場に出たポケモンにも及ぶか", "cluster": "power",
        "decision_refs": ["DEC-SUPPRESSION-READINGS"],
        "question": "まきちらせ!ベトベトガス・やみのはどう・ふしぎなガスなど、特殊能力を消す効果がはたらいているあいだに場に出たポケモンの特殊能力も消えるか",
        "statement": "特殊能力を消す効果は、はたらいているあいだ、そのとき場にいるすべての対象に及ぶ（効果がはたらきはじめたあとに場に出たポケモンを含む）",
        "applies_when": "特殊能力を消す効果がはたらいているあいだに、特殊能力を持つカードを場に出す・進化させる場面（GG1・DW1・ふしぎなガス）",
        "targets": [_t("UNRESOLVED_GOOP_GAS_NEW_POKEMON"), _t("UNRESOLVED_DARK_WAVE_NEW_POKEMON"), _t("UNRESOLVED_STRANGE_GAS_NEW_POKEMON")],
        "excludes": ["「特殊能力の効果を受けない」ポケモン（DW2・ふしぎなガスの MG2。個別）", "消えていた特殊能力がもどる時点（SC2 など。個別）"],
        "exceptions": [], "depends_on": [], "related": [], "conflicts_with": [],
        "strict_difference": "厳密は今のまま拒否。プレイ用は消えたまま出す",
        "impact": {"information": "なし", "rng": "なし", "cost": "なし", "order": "なし"},
        "common_implementation": "特殊能力の有効性の問い合わせ（共通）に規約の照会を加える",
        "card_specific_remaining": "なし",
        "regression_tests": ["効果がはたらいているあいだに出したポケモンの特殊能力", "効果がないときが今と同じ"],
        "recommendation": {"option": "及ぶ", "reason": "持続する効果を「はたらいているあいだの場」に当てはめる読み方（CR-POWER-BACK-AFTER-RECOVERY と同じ向き）"},
        "alternatives": [{"option": "はたらきはじめた時点の場のポケモンだけ", "reason": "効果を一度だけ当てはめる読み方"}],
        "basis": ["effects.py の GG1・DW1 の理由の文", "kyuura の UQ-GOOP-GAS-NEW-POKEMON"], "unverified": ["3 コードの止める条件が同じ型か"],
    },
    {
        "id": "PC-NON-DAMAGE-HP-KNOCKOUT", "name": "ダメージ以外で HP がのっているダメージ以下になったポケモン", "cluster": "knockout", "whole_game": True,
        "decision_refs": ["DEC-KNOCKOUT-READINGS"],
        "question": "進化・退化・最大HPを下げる効果など、ダメージ以外の原因で HP がのっているダメージ以下になったポケモンは、いつきぜつするか",
        "statement": "ダメージ以外の原因で HP がのっているダメージ以下になったポケモンは、その原因になったコマンドの処理の終わりにきぜつの判定をする（ポケモンチェックの 3・4 で起こったら、ポケモンチェックの終わりに判定する）",
        "applies_when": "max_hp_drops が空でない・進化のあとに HP がダメージ以下（EVOLUTION_HP・DV1）",
        "targets": [_t("UNRESOLVED_MAX_HP_DROP", "needs_implementation", "ポケモンチェック・番の終わりでは HALTED の経路（動的）。判定の時点を加える実装が要る"),
                    _t("UNRESOLVED_EVOLUTION_HP", "blocked_by_defect", "PSP-DECK-CONTENT-PRECHECKS の残り（EVOLUTION_HP の経路。未確認の漏れの候補）"),
                    _t("UNRESOLVED_DEVOLUTION_INTERMEDIATE_KNOCKOUT", "unverified")],
        "excludes": ["変身がもどるときのきぜつの時点（TK1。個別）", "ワザのダメージによるきぜつ（今のまま）"],
        "exceptions": [], "depends_on": [], "related": [], "conflicts_with": [],
        "strict_difference": "厳密は今のまま拒否・HALTED。プレイ用はきぜつの判定をして続ける",
        "impact": {"information": "なし", "rng": "なし", "cost": "なし", "order": "きぜつの判定の時点が増える"},
        "common_implementation": "コマンドの終わり・ポケモンチェックの終わりに、きぜつの判定の窓を加える（今は MH1 で受け付けない・止める）",
        "card_specific_remaining": "なし",
        "regression_tests": ["最大HP が下がってきぜつする盤面（コマンド・ポケモンチェック・番の終わり）で、サイド・勝ち負け", "厳密では今と同じ"],
        "recommendation": {"option": "原因のコマンドの処理の終わりに判定", "reason": "きぜつの判定の時点を新しく決める必要がある中で、いちばん近い既存の判定の時点"},
        "alternatives": [{"option": "次のワザ・ポケモンチェックのきぜつの判定まで待つ", "reason": "HP 以上のダメージのポケモンが場に残る時間ができる"}],
        "basis": ["kyuura の UQ-EVOLUTION-HP-BELOW-DAMAGE（3 コード）", "engine.py の max_hp_drops の分岐・procedures.py の _recovery_stop"],
        "unverified": ["判定の窓を加える実装の量"],
    },
    {
        "id": "PC-REACTION-DOUBLE-KNOCKOUT", "name": "ワザのダメージと反応のダメージによる両方のきぜつ", "cluster": "knockout",
        "decision_refs": ["DEC-KNOCKOUT-READINGS"],
        "question": "ワザのダメージで相手がきぜつし、同じワザの処理の中の反応（返すダメージ・カウンター・みちづれ）でワザを使ったポケモンもきぜつするとき、同時のきぜつか",
        "statement": "同じワザの処理の中のダメージと、そのダメージへの反応のダメージで両方のプレイヤーのポケモンがきぜつしたら、同時のきぜつとして扱う（サイドを取る順番は利用者の指定 USER-PRIZE-ORDER-* のまま）",
        "applies_when": "ワザのダメージで相手の対戦ポケモンがきぜつしうるうえ、反応のダメージでワザを使ったポケモンもきぜつしうる場面（W24・C18・HC2）",
        "targets": [_t("UNRESOLVED_RETALIATION_DOUBLE_KNOCKOUT"), _t("UNRESOLVED_COUNTERATTACK_DOUBLE_KNOCKOUT"), _t("UNRESOLVED_DESTINY_BOND_KNOCKOUT")],
        "excludes": ["ポケモンチェックの両方のきぜつ（PC-CHECK-DOUBLE-KNOCKOUT）", "反応の効果がきぜつしたポケモンからはたらくか（KD1。PC-TARGET-LOST-MID-EFFECT）"],
        "exceptions": [], "depends_on": [], "related": ["CONV:USER-PRIZE-ORDER-ALWAYS-CHOSEN", "CONV:USER-PRIZE-ORDER-PER-PLAYER"], "conflicts_with": [],
        "strict_difference": "厳密は今のまま拒否。プレイ用は同時のきぜつとして続ける",
        "impact": {"information": "なし", "rng": "なし", "cost": "なし", "order": "勝ち負け・サドン・デスへの移り方が変わる"},
        "common_implementation": "ワザのあとのきぜつの処理（同時のきぜつの並びは v0.139・v0.140 で作った）に、反応のダメージのきぜつを同じ並びに入れる規約の照会を加える",
        "card_specific_remaining": "反応の登録ごとに、ダメージの時点がワザの処理の中か",
        "regression_tests": ["両方がきぜつする盤面で、サイドの決定（prize_first）・勝ち負け・サドン・デス", "片方だけのきぜつが今と同じ", "厳密では今と同じ"],
        "recommendation": {"option": "同時のきぜつ", "reason": "同じワザの処理の中のきぜつは、ワザのあとのきぜつの判定でまとめて処理する（p.323）"},
        "alternatives": [{"option": "反応のダメージのきぜつが後", "reason": "反応の時点を後に読む読み方。勝ち負けが変わる"}],
        "basis": ["kyuura の UQ-RETALIATION-DOUBLE-KO・UQ-COUNTERATTACK-DOUBLE-KO・UQ-DESTINY-BOND-KO"], "unverified": ["3 つの反応のダメージの時点"],
    },
    {
        "id": "PC-TARGET-LOST-MID-EFFECT", "name": "効果の途中で対象・発生源がいなくなったとき", "cluster": "target",
        "question_kind": "lost_mid_effect",
        "decision_refs": ["DEC-REACTION-READINGS", "DEC-COPY-SCOPE"],
        "question": "効果の処理の途中で、その効果の対象・発生源のポケモンが場をはなれた・きぜつした・条件を満たさなくなったとき、残りの処理をどうするか",
        "statement": "効果の処理の途中で、その効果の対象・発生源のポケモンが場をはなれた（きぜつを含む）・条件を満たさなくなったら、そのポケモンに関する残りの処理は行わない。ほかの処理は続ける",
        "applies_when": "処理の途中の確かめで、対象・発生源の変化を理由に止める場面（対象の一覧のコード）",
        "targets": [_t("UNRESOLVED_RECALL_TARGET_CHANGED"), _t("UNRESOLVED_REACTION_CONDITION_CHANGED"), _t("UNRESOLVED_REACTION_AFTER_KNOCKOUT"),
                    _t("UNRESOLVED_REACTION_BY_KNOCKED_OUT_POKEMON")],
        "excludes": ["最初から対象がない（PC-USE-WITHOUT-TARGET）", "持続する効果の発生源の進化・退化（PC-LASTING-SOURCE-CHANGE）"],
        "exceptions": ["エンジンの未対応のコード（UNSUPPORTED_ATTACK_SOURCE_LEFT_PLAY・UNSUPPORTED_SECRET_PLAN_LOST_TARGET・UNSUPPORTED_PURSUIT_DAMAGE_REACTION）は B（規約の対象にしない。同じ規約を前提にした実装の候補）"],
        "depends_on": [], "related": ["PC-LASTING-SOURCE-CHANGE"], "conflicts_with": [],
        "strict_difference": "厳密は今のまま拒否。プレイ用は残りを飛ばして続ける",
        "impact": {"information": "なし", "rng": "飛ばした処理のコインは投げない", "cost": "なし", "order": "なし"},
        "common_implementation": "反応・処理の継続の状態（台帳の PF-RUNTIME-CONTINUATION と同じ不足）が先に要る",
        "card_specific_remaining": "効果ごとに「そのポケモンに関する処理」の範囲",
        "regression_tests": ["途中で対象が場をはなれる盤面で、残りの処理・ログ", "厳密では今と同じ"],
        "recommendation": {"option": "そのポケモンに関する残りを行わない", "reason": "対象のない処理を推測で別のポケモンに移さない"},
        "alternatives": [{"option": "効果全体を止めない（対象がいなくても残りの処理の結果を記録する）", "reason": "処理の範囲が決まらない"}],
        "basis": ["台帳の PF-REACTION-DURING-PROCESS・PF-COPY-TRANSFORM"], "unverified": ["4 コードが同じ型か", "継続の実装の量"],
    },
    {
        "id": "PC-LASTING-SOURCE-CHANGE", "name": "持続する効果の発生源が進化・退化・場をはなれたとき", "cluster": "lasting", "whole_game": True,
        "decision_refs": ["DEC-LASTING-READINGS"],
        "question": "相手のポケモンに与えた持続する効果（にげられない・ワザを使えない・どくの量など）は、効果を与えたポケモンが進化・退化・場をはなれたら続くか",
        "statement": "発生源のポケモンに結び付いた持続する効果は、発生源が場をはなれたら終わる。発生源の進化・退化では終わらない（同じポケモンとして続く）",
        "applies_when": "持続する効果の記録の発生源が進化・退化・場をはなれた場面で、続くかで結果が変わる（対象の一覧のコード）",
        "targets": [_t(s) for s in ("UNRESOLVED_CLAMPING_JAW_SOURCE_DEVOLVED", "UNRESOLVED_JAW_CLAMP_SOURCE_EVOLVED", "UNRESOLVED_JAW_CLAMP_SOURCE_RETURNED",
                                    "UNRESOLVED_MEAN_LOOK_SOURCE_EVOLVED", "UNRESOLVED_ATTACK_LOCK_SOURCE_RETURNED")]
        # v0.145: 台帳が PO3 を事例に分けたので、提案の時点の対象（UNRESOLVED_POISON_MIST_SOURCE・partial。「使ったポケモンが場にいない場合は規約の文に当たるが、特殊能力が消えている
        # 場合は当たらない」）のうち、規約の文に当たる事例の ID にした。#power-lost は個別（INDIVIDUAL_REASON_BY_SCENE）
        + [_t("UNRESOLVED_POISON_MIST_SOURCE#source-left", "full", "［ポイズンミスト］の使ったポケモンが場にいない（ポケモンチェックの HALTED。道具の対戦で観測）。v0.145 に PO3 を事例に"
              "分ける前は UNRESOLVED_POISON_MIST_SOURCE（partial）。この事例は PC-POISON-MIST-SOURCE-LEFT@1 として別に採用した（この案は proposal のまま）")],
        "excludes": ["効果を受けたポケモンの側の変化（今のまま）", "「自分の番に 1 回」の記録（PC-ONCE-PER-TURN-IDENTITY）"],
        "exceptions": ["説明に終わる条件が書かれている効果（今のまま）"],
        "depends_on": [], "related": ["PC-TARGET-LOST-MID-EFFECT"], "conflicts_with": [],
        "strict_difference": "厳密は今のまま拒否。プレイ用は規約で続く・終わるを決める",
        "impact": {"information": "なし", "rng": "なし", "cost": "なし", "order": "なし"},
        "common_implementation": "持続する効果の記録の終わり方（共通の期限の処理）に規約の照会を加える。発生源の記録（前の番の記録）が要る場面がある",
        "card_specific_remaining": "効果ごとの発生源の結び付き",
        "regression_tests": ["発生源が進化・退化・場をはなれた盤面で、効果が続く・終わる", "厳密では今と同じ"],
        "recommendation": {"option": "場をはなれたら終わる・進化・退化では続く", "reason": "進化・退化は同じポケモン（p.316 の進化の扱い）で、場をはなれたら別のカード"},
        "alternatives": [{"option": "発生源によらず続く", "reason": "効果を受けたポケモンの記録とみなす読み方"}],
        "basis": ["台帳の PF-HISTORY-LASTING"], "unverified": ["6 コードが同じ型か"],
    },
    {
        "id": "PC-ONCE-PER-TURN-IDENTITY", "name": "「番に 1 回」「その番に〜した」の記録は、入れかわり・もどりで続くか", "cluster": "lasting",
        "decision_refs": ["DEC-LASTING-READINGS"],
        "question": "スタジアムを入れかえた・トラッシュからもどした、ポケモンが退化したなど、カード・ポケモンが入れかわったとき、同じ番の「1 回」「その番に〜した」の記録は続くか",
        "statement": "「自分の番に 1 回」の使用の記録と「その番に〜した」の記録は、同じ番のうちは、同じ名前のカード・同じポケモン（進化・退化を含む）に続く。入れかえ・もどりで使い直せない",
        "applies_when": "同じ番の中で、記録のあるカード・ポケモンが入れかわった・もどった・退化した場面（対象の一覧のコード）",
        "targets": [_t("UNRESOLVED_STADIUM_REUSE_AFTER_REPLACEMENT"), _t("UNRESOLVED_STADIUM_REUSE_AFTER_RETURN"), _t("UNRESOLVED_FUCHSIA_GYM_AFTER_REPLACEMENT"),
                    _t("UNRESOLVED_POWER_REUSE_AFTER_DEVOLUTION"),
                    _t("UNRESOLVED_EVOLVE_AFTER_DEVOLUTION", "blocked_by_defect", "PSP-COCOON-DV2-ORACLE（未修正の漏れ）")],
        "excludes": ["ラッキースタジアムの「くりかえし」（LK1。個別）", "エネルギーをつける回数（R13・BL1。個別）"],
        "exceptions": [], "depends_on": [], "related": [], "conflicts_with": [],
        "strict_difference": "厳密は今のまま拒否。プレイ用は記録を続けて拒否する（使い直せない）",
        "impact": {"information": "なし", "rng": "なし", "cost": "なし", "order": "なし"},
        "common_implementation": "番の記録の照会（共通の部品）に規約の照会を加える",
        "card_specific_remaining": "記録を同じとみなす単位（同じ名前・同じポケモン）はカードの型ごと",
        "regression_tests": ["入れかえ・もどり・退化のあとの使用", "厳密では今と同じ"],
        "recommendation": {"option": "続く（使い直せない）", "reason": "番ごとの制限を入れかえで外さない読み方。挙動は今の拒否に近い"},
        "alternatives": [{"option": "入れかわったら別のカードとして使える", "reason": "カードの物の同一性で読む読み方"}],
        "basis": ["台帳の PF-HISTORY-LASTING", "kyuura の UQ-DEVOLUTION-SAME-TURN・UQ-FUCHSIA-GYM-ONCE-PER-TURN"], "unverified": ["5 コードが同じ型か"],
    },
    {
        "id": "PC-COPIED-ATTACK-AS-OWN", "name": "写したワザは、写したポケモンのワザとして説明のすべてを処理するか", "cluster": "copy",
        "decision_refs": ["DEC-COPY-SCOPE"],
        "question": "ものまね・オウムがえし・バーチャルなど、ほかのポケモンのワザを使うとき、そのワザの使う条件・持続する効果・ワザ以外の説明をどこまで処理するか",
        "statement": "写したワザは、写したポケモン（使うポケモン）のワザとして、そのワザの説明のすべて（使う条件・持続する効果・ワザの効果でないものを除く）を処理する",
        "applies_when": "写したワザの説明に、使う条件・持続する効果・ねむりのときだけの条件・1 回だけの条件などがあり、写したときの扱いで結果が変わる場面（kyuura の UQ-COPIED-ATTACK の 7 コード）",
        "targets": [_t(s, "needs_implementation") for s in ("UNRESOLVED_COPIED_ATTACK", "UNRESOLVED_MIRROR_MOVE_ATTACK_CONDITIONS", "UNRESOLVED_MIRROR_MOVE_LASTING_EFFECT",
                                                            "UNRESOLVED_MIRROR_MOVE_NON_ATTACK", "UNRESOLVED_MIRROR_MOVE_RECEIVED_ATTACK", "UNRESOLVED_VIRTUAL_ASLEEP_ONLY_ATTACK",
                                                            "UNRESOLVED_VIRTUAL_ONCE_ATTACK")],
        "excludes": ["へんしん・ばける・すごいへんしん（カードの仕組みごとの別の問い。個別）", "思い出す（RC1〜RC4。個別）"],
        "exceptions": ["写したワザの型をエンジンが実装していない場合（UNSUPPORTED_COPIED_ATTACK・UNSUPPORTED_MIRROR_MOVE_*。B）は、規約があっても止める"],
        "depends_on": [], "related": [], "conflicts_with": [],
        "strict_difference": "厳密は今のまま拒否",
        "impact": {"information": "なし", "rng": "写したワザのコインを投げる", "cost": "なし", "order": "なし"},
        "common_implementation": "写したワザの処理の型ごとの実装（台帳の PF-RUNTIME-COPY-GAPS）が先",
        "card_specific_remaining": "写すワザの型ごと",
        "regression_tests": ["写したワザの条件・持続する効果の盤面", "厳密では今と同じ"],
        "recommendation": {"option": "写したポケモンのワザとして説明のすべてを処理", "reason": "ワザの説明を使う側で読み直す読み方"},
        "alternatives": [{"option": "ダメージとダメージの効果だけを処理", "reason": "使う条件・持続する効果を写さない読み方"}],
        "basis": ["kyuura の UQ-COPIED-ATTACK"], "unverified": ["実装の量"],
    },
    {
        "id": "PC-FACE-UP-DECK", "name": "フラッシュでおもてになった山札のカード", "cluster": "hidden", "whole_game": True,
        "decision_refs": ["DEC-FACE-UP-DECK"],
        "question": "フラッシュでおもてにした山札のカードが山札にあるあいだ、引く・見る・並べかえる・山札の上に置く・見えない場所へ移すときにどう扱うか",
        "statement": "おもての山札のカードは、山札にあるあいだはおもてのまま（両方に見える）。山札の上から見えない場所（手札・サイド）へ移すときは、移る時点でおもてだった情報だけを公開にし、"
                     "移ったあとは移った先の公開の範囲にしたがう。並べかえ・山札の上に置くときは、おもてのカードの位置を公開のまま更新する",
        "applies_when": "faceup.command_problem が FU2〜FU6 を返す場面",
        "targets": [_t("UNRESOLVED_FACE_UP_DECK_CHECK", "needs_secret_review"), _t("UNRESOLVED_FACE_UP_DECK_HIDDEN_TAKE#draw", "needs_secret_review"),
                    _t("UNRESOLVED_FACE_UP_DECK_HIDDEN_TAKE#quiz-precheck", "needs_secret_review", "v0.135・v0.136 の保守的な止め方（漏れを塞ぐ）を外す前に対の比べが要る"),
                    _t("UNRESOLVED_FACE_UP_DECK_HIDDEN_TAKE#decision-halt", "needs_secret_review", "決定のどの答えでも当たると HALTED（動的）"),
                    _t("UNRESOLVED_FACE_UP_DECK_LOOK_RETURN", "needs_secret_review"), _t("UNRESOLVED_FACE_UP_DECK_MOVE", "needs_secret_review"),
                    _t("UNRESOLVED_FACE_UP_DECK_PLACE_TOP", "needs_secret_review")],
        "excludes": ["マチスの秘策のうらのカード（FD1・FD2。個別）", "エンジンの未対応の経路（UNSUPPORTED_FACE_UP_DECK_PATH。B）"],
        "exceptions": [], "depends_on": [], "related": ["PC-STATED-COUNT-SHORT"], "conflicts_with": [],
        "strict_difference": "厳密は今のまま拒否（どの答えでも当たれば HALTED）",
        "impact": {"information": "公開の範囲そのものを決める規約。秘密への非依存を確かめ直す", "rng": "なし", "cost": "なし", "order": "なし"},
        "common_implementation": "faceup の止め方を規約の照会で外し、公開の範囲の更新を共通にする",
        "card_specific_remaining": "クイズ・性格判定・カードめくりゲームの正誤の確かめ（v0.135・v0.136）の扱い",
        "regression_tests": ["twin_command_problems の対の比べ（両方の集合で）", "観測の公開の範囲", "厳密では今と同じ"],
        "recommendation": {"option": "おもてのまま・移る時点の公開だけを残す", "reason": "公開の情報を増やさず、移ったあとの扱いを既存の領域の規則にそろえる"},
        "alternatives": [{"option": "おもてのカードを引いたら公開のまま手札に残る（相手に見える手札）", "reason": "手札に公開のカードの表現が要る"}],
        "basis": ["docs/flash-faceup-deck-v0.126.md 6 章", "kyuura の UQ-FLASH-FACE-UP-DECK"], "unverified": ["読み方ごとの公開の範囲（研究上の未解決）"],
    },
]

# 共通規約の対象にしない研究上の未決場面（A）の理由。族ごとに既定の理由を書き、族の中の対象は CANDIDATES に明示したものだけ
INDIVIDUAL_REASON_BY_FAMILY = {
    "PF-USE-WITHOUT-EFFECT": "カード固有の読み方（使う条件・自分自身を選べるか・範囲の読み方など）。対象の有無だけの問いではない",
    "PF-UP-TO-ZERO": "—",
    "PF-STATED-COUNT-SHORT": "—",
    "PF-SETUP-PLAY-AS-POKEMON": "準備の外の化石・人形の問い（にげる PF2・育て屋 PF3・ちえくらべ MG2）。カードごとの読み方",
    "PF-SIMULTANEOUS-ORDER": "効果の種類の優先（どの効果が勝つか）の読み方、または利用者の指定の範囲の判断が先の問い。順番を選ぶ規約では扱えない",
    "PF-KNOCKOUT-TIMING": "カード固有のきぜつの時点の読み方（きあいのハチマキ・こんじょう・ふしちょう・変身のもどり・山札にもどす効果など）",
    "PF-EFFECT-TIMING": "カード固有の効果の時点の読み方（ずらかる・おとしあな・はかいのはどう・時間の歪みなど）",
    "PF-PROTECTED-TARGET-EFFECT": "対象の選び方・ダメージのない要素のあとの効果の読み方（コインの問いではない）",
    "PF-DAMAGE-SCOPE": "カード固有のダメージの範囲・計算の読み方（ダメージの量を変える効果の当てはめの問いではない）",
    "PF-ENERGY-TYPE": "色を変える効果・きせきのかぜ・エナジーバーンなど、カード固有のエネルギーの読み方",
    "PF-COPY-TRANSFORM": "へんしん・ばける・すごいへんしん・思い出す・スケッチなど、1 つのカードの仕組みの中の問い（同じ仕組みのコードはまとめて判断できるが、ほかのカードに広げない）",
    "PF-HISTORY-LASTING": "カード固有の記録・持続する効果の読み方",
    "PF-TEXT-READING": "カード固有の説明の読み方（同じ言い回しの別のカードに広げない）",
    "PF-REACTION-DURING-PROCESS": "途中の反応を使えるか（継続の実装と組）のカード固有の問い",
    "PF-POWER-SUPPRESSION": "「特殊能力の効果を受けない」ポケモン・循環・消えた特殊能力の扱いなど、カード固有の問い",
    "PF-HIDDEN-INFORMATION": "マチスの秘策のうらのカード・ヒートプレートの読み方（カード固有。秘密への非依存の確かめ直しが要る）",
    "PF-ESP-REDO": "ナツメの ESP（1 枚のカードの仕組み）の問い",
}

# 族の既定より具体的な、個別の理由（場面ごと）
INDIVIDUAL_REASON_BY_SCENE = {
    "UNRESOLVED_POISON_MIST_SOURCE#power-lost": ("v0.145: ［ポイズンミスト］の発生源が場にいるまま力が消えた記録（かがくへんかガス・退化・へんしんなど）。QK1 と同じ形の、力が消えたあとの"
                                                  "効果の問い（docs/poison-mist-play-policy-spec.md の分けた問い）。続行側でも止める"),
    "UNRESOLVED_POWER_DISCARD_WITHOUT_HAND": "コストを払えない（特殊能力の手札のトラッシュ。cost_unpayable）。にげるのコスト（PC-RETREAT-COST-PAYMENT）と手順が違い、同じ問いの場面がほかにない",
    "UNRESOLVED_ENERGY_DRAIN_NO_ENERGY": "キョウのベトベトンの［だつりょくえき］。実装上の仮定（DR1・DR6）を基礎集合に入れるか（DEC-BASELINE-NONUSER）の判断が先",
    "UNRESOLVED_MIND_GAMES_CHAOS_GYM_ORDER": "利用者指定 USER-MIND-GAMES-OPTIONAL-BEFORE-COST の範囲（錯乱ジムのコインとの前後を含むか）の判断が先（DEC-CHAOS-GYM-MIND-GAMES）。順番の規約案に入れない",
    "UNRESOLVED_POKEMON_TOWER_POWER_WITHOUT_EFFECT": "ポケモンタワーで効果がすべて消えるときに使えるか（カード固有の読み方。対象の有無の問いではない）",
    "UNRESOLVED_POKEMON_TOWER_TRAINER_WITHOUT_EFFECT": "ポケモンタワーで効果がすべて消えるときに使えるか（カード固有の読み方。対象の有無の問いではない）",
    "UNRESOLVED_ENGAGE_EMPTY_HAND": "［ENGAGE］の「手札をすべて山札にもどす」を手札 0 枚で選べるか（効果の中の選択肢の読み方。使う条件の問いではない）",
    "UNRESOLVED_POWER_COUNTER_MOVE_TO_SAME_POKEMON": "［BEAR］で自分自身を選べるか（範囲の読み方）",
    "UNRESOLVED_FULL_HEAL_SCOPE": "なんでもなおしの対象の範囲の読み方",
}

# A 以外の区分（場面 ID → (区分, 理由)）。停止コードは族、そのほかの項目は種類で既定を決め、ここに例外を書く
RUNTIME_FAMILY_CLASS = {
    "PF-RUNTIME-CONTINUATION": ("B", "決定・反応の継続の状態がない（エンジンの未対応）"),
    "PF-RUNTIME-COPY-GAPS": ("B", "写したワザ・特殊能力の処理の実装がない"),
    "PF-RUNTIME-REGISTRY": ("B", "未登録・未対応のカード・ワザ・操作（登録の不足。推測で進めない）"),
    "PF-RUNTIME-DATA": ("B", "データ・記録の不足（図鑑番号・身長・進化元・旧状態の記録・デッキリスト）"),
    "PF-RUNTIME-SEARCH-LIMIT": ("C", "探索・組合せの上限（未探索の枝を安全とみなさない）"),
    "PF-RUNTIME-GENERIC": ("E", "汎用の UNRESOLVED_RULING。どの問いか分からない（名前が UNRESOLVED でも A にしない。到達可能性・問いは unknown）"),
}
RUNTIME_CODE_CLASS = {
    "UNSUPPORTED_CARD": ("E", "デッキの検査（不正入力。SB-INPUT-VALIDATION）"),
    "UNSUPPORTED_DECISION": ("E", "この版が知らない再開先の決定を待つ状態（状態の互換の拒否。v0.141 で文を直した。規約の対象ではない）"),
    "UNSUPPORTED_CONVENTION_SET": ("E", "この版が扱えない状態の規約集合（状態の互換・登録との不一致の拒否。v0.142。規約の対象ではない）"),
}
OTHER_KIND_CLASS = {
    "silent_information_leak": ("D", "情報漏れ（未修正）"),
    "information_leak_candidate": ("D", "情報漏れの候補（未確認）"),
    "preflight_overrejection": ("D", "先読みの止めすぎ（受け付けてよい操作を拒否する不具合の候補）"),
    "fallback_review": ("D", "代わりの処理の安全性の見直し（未確認）"),
    "technical_limit": ("C", "技術的な上限・探索の fail-open"),
    "representation_limit": ("C", "表現の上限"),
    "terminal_limitation": ("B", "途中停止の再開の操作がない（エンジンの未対応）"),
    "data_limitation": ("B", "参照データの不足（図鑑番号のない 225 枚）"),
    "metadata_limitation": ("E", "研究の基準の照合（記録の作業）"),
    "out_of_scope": ("E", "対象外（特別なルール）"),
    "codeless_question": ("E", "コードのない研究の問い。エンジンが止める場面かは確かめていない（到達可能性 unknown）"),
    "test_tool_only_code": ("E", "テスト・道具だけのコード（エンジンでは投げない）"),
}
OTHER_ID_CLASS = {
    "GAP-ANSWER-SEARCH-FAIL-OPEN": ("D", "代替回答探索の fail-open（未探索を受け付ける側に倒す。安全境界 SB-NO-FAIL-OPEN-SEARCH の候補）"),
}

# この調査で見つけた共通の不具合（修正していない。台帳には加えていない: 台帳の作成スクリプトは別の作業で直す）
NEW_FINDINGS = [
    {
        "id": "PSP-NJ1-NINJA-GYM-ORACLE", "plan_class": "D", "status": "fixed",
        "summary": "キョウの忍者ジム（PR1-067）の使う前の確かめ（CoinBenchOwnerBasicFromDeckStadium.check_activation。effects.py:21276〜21281）が、山札の実際の中身（deck_cards_matching）で NJ1 を判定する。"
                   "目的の「キョウのたねポケモン」が山札とサイドのどちらにあるかで、受理・拒否が変わる（v0.137 の PSP-ST1-DECK-ORACLE と同じ型）",
        "evidence": "比較プローブ（エンジンは変えない。tests.log_audit.twin_command_problems）: プレイヤー 0 から見て公開の情報が同じ 2 盤面（キョウのアーボ PMCG6-002 が山札の 11 枚目／サイドの 1 枚目）で、"
                    "UseStadium(0) が受理／UNRESOLVED_NINJA_GYM_WITHOUT_TARGET で拒否。twin_command_problems が段 0 で検出",
        "found_by": "v0.136 の漏れの横断（check_playable・check_usable）の外の check_activation を、AST で同じ型（山札を読んで UnsupportedError）を探した。ほかの check_activation で山札を読むものは"
                    "エネルギースタジアム（トラッシュ。公開）だけで、山札は読まない",
        "related_scene": "UNRESOLVED_NINJA_GYM_WITHOUT_TARGET",
        "not_done": "修正・台帳（stop-policy-classification.json）への追加はしていない。DEC-INFO-LEAK-FIXES の判断の材料",
        "fixed_in": ("v0.146（docs/play-set-verification-v0.146.md 3 章）: 使う前の確かめを配分を読まない下限（deck_target_lower_bound・bench_entry_unconfirmed）に替え、停止の方針の台帳に"
                     "fixed で加えた。not_done は提案の時点（調査の時点）の記録"),
    },
]

# 未修正・未確認の不具合と、同じ場面に当てる規約（blocked_by_defect の根拠）
DEFECT_COUPLING = {
    "UNRESOLVED_POWER_ZERO_CARDS": "PSP-INCREASE-ENTRY-PW3-ORACLE",
    "UNRESOLVED_EVOLVE_AFTER_DEVOLUTION": "PSP-COCOON-DV2-ORACLE",
    "UNRESOLVED_EVOLUTION_PERMISSION_FROM_DECK#coin-evolve-self-from-deck": "PSP-DECK-CONTENT-PRECHECKS",
    "UNRESOLVED_EVOLUTION_HP": "PSP-DECK-CONTENT-PRECHECKS",
}

# ---------------------------------------------------------------------------------------------------------------------------------------------------
# 対戦全体を止める経路（現行コードで確かめたもの。静的な Halt の定数と、動的に HALTED に変わる経路）
# ---------------------------------------------------------------------------------------------------------------------------------------------------
WHOLE_GAME_CHANNELS = [
    {"id": "WG-SETUP-MULLIGAN", "kind": "unresolved_ruling", "mechanism": "setup_halt", "site": "kyuura_engine/engine.py:513〜526（_deal_opening_hands）",
     "condition": "切り直しの回の列に、両方が切り直した回と片方だけが切り直した回が両方ある（両方の回は先、片方だけの回は同じプレイヤーが続ける形だけが起こる）。最初の対戦と延長戦（_prepare_segment）で同じ",
     "scenes": [f"{MULLIGAN}#initial-setup", f"{MULLIGAN}#sudden-death-segment"], "candidates": ["PC-SETUP-MULLIGAN-COUNT"],
     "continuation": "規約だけで続けられる（補償の数を決めれば、既存の DrawMulliganCards で引く）"},
    {"id": "WG-SETUP-PLAY-AS-POKEMON", "kind": "unresolved_ruling", "mechanism": "setup_halt", "site": "kyuura_engine/engine.py:491〜500",
     "condition": "たねポケモン・ベイビィのない手札に、なにかの化石・ピッピ人形がある（切り直す前に止める。切り直しの回ごとに確かめる）",
     "scenes": [f"{PLAY_AS}#initial-setup", f"{PLAY_AS}#sudden-death-segment"], "candidates": ["PC-SETUP-PLAY-AS-POKEMON"],
     "continuation": "「切り直す」なら規約だけ。「出せる」なら準備で置く処理の実装が要る。どちらでも、その後の切り直しで WG-SETUP-MULLIGAN に当たりうる"},
    {"id": "WG-CHECK-SLEEP-ORDER", "kind": "unresolved_ruling", "mechanism": "pokemon_check_halt", "site": "kyuura_engine/procedures.py:946〜961",
     "condition": "ポケモンチェックの 3 で、両方の対戦ポケモンがねむり", "scenes": ["UNRESOLVED_POKEMON_CHECK_SLEEP_COIN_ORDER"], "candidates": ["PC-CHECK-SIDE-ORDER"],
     "continuation": "規約で順番が決まる。そのあと回復したときの止め方（WG-CHECK-RECOVERY）に当たりうる"},
    {"id": "WG-CHECK-CHAR-ORDER", "kind": "unresolved_ruling", "mechanism": "pokemon_check_halt", "site": "kyuura_engine/procedures.py:374〜381",
     "condition": "ポケモンチェックの 1 で、両方のプレイヤーがくろこげマーカーのコインを投げる", "scenes": ["UNRESOLVED_POKEMON_CHECK_CHAR_COIN_ORDER"], "candidates": ["PC-CHECK-SIDE-ORDER"],
     "continuation": "規約で順番が決まる。コインの前の確かめ・上限（WG-CHECK-CHAR-LIMIT）が残る"},
    {"id": "WG-CHECK-CHAR-LIMIT", "kind": "technical_limit", "mechanism": "pokemon_check_halt", "site": "kyuura_engine/procedures.py:382〜385",
     "condition": "くろこげマーカーのコインが MAX_CHAR_COINS 枚を超える", "scenes": ["UNSUPPORTED_POKEMON_CHECK_CHAR_COINS"], "candidates": [],
     "continuation": "規約では続けられない（計算の改善が要る。C）"},
    {"id": "WG-CHECK-PLAN", "kind": "unresolved_ruling", "mechanism": "pokemon_check_halt", "site": "kyuura_engine/procedures.py:267〜330（_pokemon_check_plan）",
     "condition": "ポケモンチェックの 1・2 を複製で確かめて、BY1（1 の順番）・どくの量（PO1〜PO3。動的: poison_check_amount の UnsupportedError）・KA1・PK1・SC1（#pokemon-check）・両方のきぜつ・AL1・AL3・"
                  "きのみの上限（UNSUPPORTED_BERRY_ORDER_LIMIT。動的）で止める",
     "scenes": ["UNRESOLVED_POKEMON_CHECK_BERRY_ORDER", "UNRESOLVED_POISON_DAMAGE_RECEIVED_POWER", "UNRESOLVED_POKEMON_CHECK_MID_KNOCKOUT",
                "UNRESOLVED_SCRAM_TIMING#pokemon-check", "UNRESOLVED_POKEMON_CHECK_DOUBLE_KNOCKOUT", "UNRESOLVED_LEAVE_LOCK_KNOCKOUT", "UNRESOLVED_LEAVE_LOCK_SCRAM",
                "UNRESOLVED_POISON_CHANGE_ORDER", "UNRESOLVED_POISON_MIST_EARLIER_POISON", "UNRESOLVED_POISON_MIST_SOURCE#source-left",
                "UNRESOLVED_POISON_MIST_SOURCE#power-lost", "UNSUPPORTED_BERRY_ORDER_LIMIT"],
     "candidates": ["PC-CHECK-SIDE-ORDER", "PC-NON-ATTACK-DAMAGE-MODIFIERS", "PC-CHECK-KO-POINT", "PC-CHECK-DOUBLE-KNOCKOUT", "PC-LASTING-SOURCE-CHANGE"],
     "continuation": "コードごと。SC1・AL1・AL3・PO1・PO2 はカード固有（個別）。きのみの上限は C"},
    {"id": "WG-CHECK-SCRAM", "kind": "unresolved_ruling", "mechanism": "pokemon_check_halt", "site": "kyuura_engine/resolution/flow.py:1290〜1300",
     "condition": "ポケモンチェックの「どく」のあとの［ずらかる］の問い（OpenQuestion の error.code。SC2 など）", "scenes": ["UNRESOLVED_SCRAM_POWER_RESTORED"], "candidates": [],
     "continuation": "カード固有の時点の読み方（個別）"},
    {"id": "WG-CHECK-RECOVERY", "kind": "unresolved_ruling", "mechanism": "pokemon_check_halt", "site": "kyuura_engine/procedures.py:966〜981・1009〜1015（_recovery_stop → effects.state_stop_after）",
     "condition": "ポケモンチェックの 3・4 で回復すると、決められない姿（form_problems: DG1・MH2・BZ・色のカード・レインボーなど）・ダメージ以外の最大HPの低下（MH1）・［ずらかる］の力のもどり（SC2）になる",
     "scenes": ["UNRESOLVED_MAX_HP_DROP", "UNRESOLVED_SHAPESHIFT_SUPPRESSED", "UNRESOLVED_MAX_HP_SET_AND_INCREASE", "UNRESOLVED_SCRAM_POWER_RESTORED"],
     "candidates": ["PC-NON-DAMAGE-HP-KNOCKOUT"],
     "continuation": "MH1 は規約と判定の時点の実装。姿の問いはカード固有。コードの全件の列挙はしていない（form_problems が返すコードは静的に一部だけ確かめた）"},
    {"id": "WG-TURN-END-SUPPRESSION", "kind": "unresolved_ruling", "mechanism": "turn_end_halt", "site": "kyuura_engine/procedures.py:80〜99（expire_at_turn_end → state_stop_after）",
     "condition": "番の終わりに特殊能力を消す効果が消えると、決められない姿・MH1・SC2 になる", "scenes": ["UNRESOLVED_MAX_HP_DROP", "UNRESOLVED_SHAPESHIFT_SUPPRESSED", "UNRESOLVED_SCRAM_POWER_RESTORED"],
     "candidates": ["PC-NON-DAMAGE-HP-KNOCKOUT"], "continuation": "WG-CHECK-RECOVERY と同じ"},
    {"id": "WG-TURN-END-MIRACLE", "kind": "unresolved_ruling", "mechanism": "turn_end_halt", "site": "kyuura_engine/procedures.py:100〜105（miracle_turn_end_problem）",
     "condition": "番の終わりに、［きせきのかぜ］で効果の消えたミラクルエネルギーが場にある（MEW1）", "scenes": ["UNRESOLVED_MIRACLE_ENERGY_UNDER_WIND"], "candidates": [],
     "continuation": "カード固有（個別）"},
    {"id": "WG-DEFERRED-SHORTAGE", "kind": "unresolved_ruling", "mechanism": "deferred_interruption", "site": "kyuura_engine/engine.py:892〜895（DeferredShortage → _interrupted）",
     "condition": "共通の数量処理のチェック地点で、コインで決まった数が処理できる数より多い（DU1・TW1）。コインのあとの終端。再開の操作はない（GAP-DEFERRED-HALT-NO-RESUME）",
     "scenes": ["UNRESOLVED_DRY_UP_WATER_ENERGY_SHORT", "UNRESOLVED_THOUGHT_WAVE_MACHINE_ENERGY_SHORT"], "candidates": ["PC-COIN-COUNT-SHORT"],
     "continuation": "規約を採れば、途中停止にせず最初から規約で処理する（すでに途中停止した状態の再開は別の判断 DEC-DEFERRED-RESUME）"},
    {"id": "WG-DECISION-NO-ANSWER", "kind": "dynamic_conversion", "mechanism": "decision_halt", "site": "kyuura_engine/engine.py:579〜588・896〜903・943〜953（_decision_has_unstopped_answer）",
     "condition": "決定（バトル場に出す・サイドを取る・決定への答え）と対戦準備の最後（ReportJankenResult）で、どの答えでも、決められない姿・MH1・SC2・おもての山札の止め方（FU3 など）・うらのカードの決まらない項目（FD1）"
                  "になる。答えのない決定を残さずに、その前の状態で HALTED",
     "scenes": ["UNRESOLVED_FACE_UP_DECK_HIDDEN_TAKE#decision-halt", "UNRESOLVED_SECRET_PLAN_HIDDEN_PROPERTY", "UNRESOLVED_MAX_HP_DROP"],
     "candidates": ["PC-FACE-UP-DECK", "PC-NON-DAMAGE-HP-KNOCKOUT"],
     "continuation": "当たったコードの規約・実装による。どのコードがここを通るかの全件は静的に特定していない（台帳 14 章の限界のまま）"},
    {"id": "WG-OBSERVED-UNIDENTIFIED", "kind": "dynamic_conversion", "mechanism": "observed_halt",
     "site": "経路は特定していない（道具の対戦で HALTED を観測。tools/existing_effect_games.py の v0.49 の組 A49-D49・seed 2。6 章）",
     "condition": "エンジンの未対応のコードが、動的な経路（決められない姿の確かめなど）で HALTED になった", "scenes": ["UNSUPPORTED_TRANSFORM_COPIED_POWER"], "candidates": [],
     "continuation": "規約では続けられない（B。写した特殊能力の実装が要る）"},
    {"id": "WG-TOOL-LIMITS", "kind": "tool_cutoff", "mechanism": "tool_step_limit",
     "site": "tools/existing_effect_games.py の --max-steps・予期しない拒否（unexpected_rejection）・サドン・デスに移った局（延長戦を進めない）。tools/sudden_death_games.py の segment_limit",
     "condition": "道具の打ち切り。エンジンの停止ではない（予期しない拒否の 2 局は、エンジンが MG1 で拒否しただけで、対戦は終端になっていない）", "scenes": [], "candidates": [],
     "continuation": "規約の対象ではない（道具の設定）。集計では HALTED と分けて数える"},
]

# ---------------------------------------------------------------------------------------------------------------------------------------------------
# 採用・実装の段階（案）。burden は実装・検証の負担、risk は情報・処理順の危険。prerequisite_for はこの規約が前提になる規約
# ---------------------------------------------------------------------------------------------------------------------------------------------------
STAGES = {
    "S0": {"name": "両モード共通の不具合の修正（モードと別の版）", "rules": [],
           "prerequisites": [], "scope": "PSP-NJ1-NINJA-GYM-ORACLE（この調査で確認）・PSP-INCREASE-ENTRY-PW3-ORACLE・PSP-COCOON-DV2-ORACLE・PSP-DECK-CONTENT-PRECHECKS の残り（未確認）",
           "done_when": "対の比べ（twin_command_problems）で漏れがない。blocked_by_defect の場面の規約を採れる状態",
           "remains": "研究上の論点（NJ1・PW3・DV2・GV1 の裁定）は未解決のまま"},
    "S1": {"name": "規約集合を受け取る基盤と、今の挙動の保持", "rules": [],
           "prerequisites": ["DEC-RULESET-IDENTITY", "DEC-RULESET-VERSIONING", "DEC-CONVENTION-GRANULARITY", "DEC-CONVENTION-CONFLICTS", "DEC-MODE-CHANGE-DURING-GAME",
                             "DEC-LEGACY-STATES", "DEC-BASELINE-NONUSER", "DEC-CARD-DATA-CORRECTIONS"],
           "scope": "規約集合を new_game で受け取り状態に持つ（延長戦は keep）・止める箇所に事例の識別（場面 ID）・規約の照会の入口（登録の側。engine.py・resolution/ にカード ID・モード名の分岐を加えない）・"
                    "規約による拒否と未決の裁定の停止を区別する記録・構成の検査（ruleset-mode-design.md 6.4 節）・厳密と厳密の比べ",
           "done_when": "厳密の集合（基礎集合だけ）で、全体テスト・lockstep・前の版の組・サドン・デスの比べが今と同じ（意図した差 0）。規約の照会がどの場面でも「規約なし」を返し、止め方が今のまま",
           "remains": "続行規約は 1 つも入っていない。保存形式・識別の形は判断のあとに決める（この設計では決めない）"},
    "S2a": {"name": "対戦全体を止める規約（規約だけで足りるもの）", "rules": ["PC-SETUP-MULLIGAN-COUNT", "PC-SETUP-PLAY-AS-POKEMON", "PC-CHECK-SIDE-ORDER", "PC-COIN-COUNT-SHORT", "PC-CHECK-KO-POINT"],
            "prerequisites": ["S1", "DEC-PLAY-CONFIG-INCOMPLETE-START"], "scope": "準備・ポケモンチェック・途中停止の HALTED の分岐を、規約の照会で続行に置きかえる",
            "done_when": "規約ごとに、当たる盤面の結果（状態・乱数・ログ・観測）・隣の場面が変わらないこと・厳密との差が規約の当たった歩から始まること・道具の対戦で HALTED の減り方と先攻後攻の偏り",
            "remains": "WG-CHECK-PLAN・WG-CHECK-RECOVERY・WG-DECISION-NO-ANSWER のカード固有の停止、技術的な上限（くろこげマーカー・きのみ）"},
    "S2b": {"name": "対戦全体を止める規約（実装が要るもの）", "rules": ["PC-CHECK-DOUBLE-KNOCKOUT", "PC-NON-DAMAGE-HP-KNOCKOUT", "PC-NON-ATTACK-DAMAGE-MODIFIERS", "PC-LASTING-SOURCE-CHANGE"],
            "prerequisites": ["S2a"], "scope": "ポケモンチェックの続きの両方のサイド・交代の並び、ダメージ以外の HP 低下のきぜつの判定の窓、ワザ以外のダメージの量の問い合わせ",
            "done_when": "S2a と同じ。両方のきぜつ・サドン・デスへの移り方の比べ",
            "remains": "カード固有の時点の問い（SC1・SC2・AL1・AL3・MEW1 など）"},
    "S3": {"name": "多数のカードに共通する通常の操作の規約", "rules": ["PC-USE-WITHOUT-TARGET", "PC-USE-WITHOUT-EFFECT", "PC-CHOOSE-TARGET-WITHOUT-EFFECT", "PC-UP-TO-ZERO", "PC-STATED-COUNT-SHORT",
                                                                 "PC-UNSTATED-WEAKNESS-RESISTANCE", "PC-SPECIAL-ENERGY-CARD-WORDING", "PC-RETREAT-COST-PAYMENT", "PC-NULLIFIED-ELEMENT-COIN",
                                                                 "PC-ORDER-ATTACK-PRECHECK", "PC-ORDER-OVERLAP", "PC-SUPPRESSION-LATER-POKEMON", "PC-REACTION-DOUBLE-KNOCKOUT", "PC-ONCE-PER-TURN-IDENTITY"],
           "prerequisites": ["S1"], "scope": "使う前・答えの確かめの拒否を、規約の照会で規約による拒否・受け付けに置きかえる。順番の決定の共通の部品",
           "done_when": "規約ごとの回帰（当たる盤面・隣の場面・対の比べ・厳密との差）。対象の一覧の場面ごとに、止める条件が規約の適用条件と同じことをコードで確かめる（unverified を解消する）",
           "remains": "個別の場面（カード固有の読み方）"},
    "S4": {"name": "特殊な相互作用の規約（秘密の確かめ・実装が要るもの）", "rules": ["PC-HIDDEN-SEARCH-EMPTY", "PC-FACE-UP-DECK", "PC-TARGET-LOST-MID-EFFECT", "PC-COPIED-ATTACK-AS-OWN"],
           "prerequisites": ["S1", "S0"], "scope": "探して見つからない処理・おもての山札の公開の範囲・継続の状態・写したワザの型ごとの実装",
           "done_when": "両方の集合での対の比べ・継続の状態の保存と再生",
           "remains": "B の実装の不足（PF-RUNTIME-*）"},
}
PRIORITY = {
    "PC-SETUP-MULLIGAN-COUNT": {"burden": "小（1 か所の分岐）", "risk": "小（公開・乱数の新しい消費なし）", "prerequisite_for": []},
    "PC-SETUP-PLAY-AS-POKEMON": {"burden": "小（推奨案）・大（代替案）", "risk": "小", "prerequisite_for": []},
    "PC-CHECK-SIDE-ORDER": {"burden": "小（2 か所の分岐）", "risk": "中（乱数の割り当て・先攻後攻の偏りを測る）", "prerequisite_for": ["PC-CHECK-DOUBLE-KNOCKOUT"]},
    "PC-COIN-COUNT-SHORT": {"burden": "小（共通のチェック地点）", "risk": "小", "prerequisite_for": []},
    "PC-CHECK-KO-POINT": {"burden": "小", "risk": "中（勝ち負け）", "prerequisite_for": []},
    "PC-CHECK-DOUBLE-KNOCKOUT": {"burden": "中（ポケモンチェックの続きの並び）", "risk": "中（勝ち負け・サドン・デス）", "prerequisite_for": []},
    "PC-NON-DAMAGE-HP-KNOCKOUT": {"burden": "中（判定の窓）", "risk": "中（勝ち負け）", "prerequisite_for": []},
    "PC-NON-ATTACK-DAMAGE-MODIFIERS": {"burden": "中（量の問い合わせの部品）", "risk": "小（量だけ）", "prerequisite_for": []},
    "PC-USE-WITHOUT-TARGET": {"burden": "小（拒否の記録だけ）", "risk": "小（今と同じ。止める条件が公開で決まることの確かめが要る）", "prerequisite_for": []},
    "PC-USE-WITHOUT-EFFECT": {"burden": "小", "risk": "小", "prerequisite_for": ["PC-CHOOSE-TARGET-WITHOUT-EFFECT"]},
    "PC-CHOOSE-TARGET-WITHOUT-EFFECT": {"burden": "小", "risk": "小（候補を黙って減らさない記録）", "prerequisite_for": []},
    "PC-UP-TO-ZERO": {"burden": "小（答えの範囲の部品）", "risk": "小", "prerequisite_for": []},
    "PC-STATED-COUNT-SHORT": {"burden": "中（効果の型ごとのあるだけの処理）", "risk": "小（枚数は公開）", "prerequisite_for": []},
    "PC-UNSTATED-WEAKNESS-RESISTANCE": {"burden": "小", "risk": "小", "prerequisite_for": []},
    "PC-SPECIAL-ENERGY-CARD-WORDING": {"burden": "中", "risk": "小", "prerequisite_for": []},
    "PC-RETREAT-COST-PAYMENT": {"burden": "小", "risk": "小", "prerequisite_for": []},
    "PC-NULLIFIED-ELEMENT-COIN": {"burden": "小", "risk": "中（乱数の列）", "prerequisite_for": []},
    "PC-ORDER-ATTACK-PRECHECK": {"burden": "中（順番の決定の部品）", "risk": "中（乱数の割り当て・決定の増加）", "prerequisite_for": []},
    "PC-ORDER-OVERLAP": {"burden": "中", "risk": "中", "prerequisite_for": []},
    "PC-SUPPRESSION-LATER-POKEMON": {"burden": "小", "risk": "小", "prerequisite_for": []},
    "PC-REACTION-DOUBLE-KNOCKOUT": {"burden": "中", "risk": "中（勝ち負け）", "prerequisite_for": []},
    "PC-ONCE-PER-TURN-IDENTITY": {"burden": "小", "risk": "小", "prerequisite_for": []},
    "PC-HIDDEN-SEARCH-EMPTY": {"burden": "中（見つからない処理）", "risk": "大（秘密への非依存）", "prerequisite_for": []},
    "PC-FACE-UP-DECK": {"burden": "大", "risk": "大（公開の範囲そのもの）", "prerequisite_for": []},
    "PC-TARGET-LOST-MID-EFFECT": {"burden": "大（継続の状態）", "risk": "中", "prerequisite_for": []},
    "PC-LASTING-SOURCE-CHANGE": {"burden": "中（発生源の記録）", "risk": "小", "prerequisite_for": []},
    "PC-COPIED-ATTACK-AS-OWN": {"burden": "大（型ごとの実装）", "risk": "中", "prerequisite_for": []},
}


# ---------------------------------------------------------------------------------------------------------------------------------------------------
# 対戦の道具の発生の記録（リポジトリの外。数え方と分母を一緒に書く）
# ---------------------------------------------------------------------------------------------------------------------------------------------------
OBSERVATION_PATH = pathlib.Path("C:/dev/kyuura-engine-play-policy-evidence/census_summary.json")


def load_observation() -> dict | None:
    if not OBSERVATION_PATH.exists():
        return None
    return json.loads(OBSERVATION_PATH.read_text(encoding="utf-8"))


# ---------------------------------------------------------------------------------------------------------------------------------------------------

def load_json(path: pathlib.Path):
    return json.loads(path.read_text(encoding="utf-8"))


def scenes_from_ledger(ledger: dict) -> list[dict]:
    """台帳の現在有効な項目から場面の一覧を作る（事例のあるコードは事例を場面にし、コードは親として持つ）。"""
    entries = {e["id"]: e for e in ledger["entries"]}
    out = []
    for e in ledger["entries"]:
        if e["status"] not in ("active", "unverified") or e["entry_kind"] == "case":
            continue
        kind = e["entry_kind"]
        stops = sorted({s["mechanism"] for s in e.get("current_stop", [])})
        base = {"code": e["id"] if kind in ("research_stop_code", "runtime_stop_code") else None, "entry_kind": kind, "family": e.get("family"),
                "ledger_classification": e.get("classification"), "play_groups": e.get("play_groups", []), "mechanisms": stops,
                "reachability": (e.get("reachability") or {}).get("status", "unknown"),
                "ruling_ids": [r for r in (e.get("research") or {}).get("ruling_ids", []) if r], "kyuura_issue": (e.get("research") or {}).get("kyuura_issue"),
                "ruling_documents": (e.get("research") or {}).get("rulings_documents", [])}
        if e.get("cases"):
            for cid in e["cases"]:
                c = entries[cid]
                out.append({"id": cid, "parent": e["id"], **base, "secret_dependency": c.get("secret_dependency"), "condition": c.get("condition")})
        else:
            out.append({"id": e["id"], "parent": None, **base, "secret_dependency": None, "condition": None})
    return out


def classify(scene: dict) -> tuple[str, str]:
    kind = scene["entry_kind"]
    if kind == "research_stop_code":
        return "A", "研究上の未決の裁定（固定研究基準の対応表の停止コード）"
    if kind == "runtime_stop_code":
        if scene["code"] in RUNTIME_CODE_CLASS:
            return RUNTIME_CODE_CLASS[scene["code"]]
        return RUNTIME_FAMILY_CLASS[scene["family"]]
    if scene["id"] in OTHER_ID_CLASS:
        return OTHER_ID_CLASS[scene["id"]]
    return OTHER_KIND_CLASS[kind]


def continuation_floor(scene: dict) -> str | None:
    """台帳の対応群から、規約だけでは足りないことが分かっている場面の下限（3 = 実装・5 = 保護）。"""
    groups = set(scene["play_groups"])
    if "3" in groups:
        return "needs_implementation"
    if "5" in groups:
        return "needs_secret_review"
    return None


HALTING_MECHANISMS = {"setup_halt", "pokemon_check_halt", "deferred_interruption"}  # 対戦を終端にする止め方（事例は経路の一覧で明示したものだけ）


def build() -> dict:
    ledger = load_json(LEDGER)
    research = load_json(RESEARCH)
    scenes = scenes_from_ledger(ledger)
    target_of: dict[str, list[tuple[str, dict]]] = collections.defaultdict(list)
    for cand in CANDIDATES:
        for t in cand["targets"]:
            target_of[t["scene"]].append((cand["id"], t))
        for t in ADOPTIONS.get(cand["id"], {}).get("added_scenes", []):
            target_of[t["scene"]].append((cand["id"], t))  # v0.143: 採用で加えた場面
    adopted_scene = {(t if isinstance(t, str) else t["scene"]): ADOPTIONS[c["id"]]["convention"] for c in CANDIDATES if c["id"] in ADOPTIONS
                     for t in adoption_scenes(c)}
    adopted_scene.update({sid: a["convention"] for a in SPEC_ADOPTIONS.values() for sid in a["scenes"]})  # v0.145: 別の仕様案の採用
    whole_game_scenes = {s for ch in WHOLE_GAME_CHANNELS for s in ch["scenes"]}
    scene_rows = []
    for s in scenes:
        plan_class, reason = classify(s)
        row = {"id": s["id"], "parent": s["parent"], "code": s["code"], "entry_kind": s["entry_kind"], "family": s["family"],
               "ledger_classification": s["ledger_classification"], "plan_class": plan_class, "class_reason": reason,
               "mechanisms": s["mechanisms"], "reachability": s["reachability"], "whole_game": s["id"] in whole_game_scenes or (s["parent"] is None and bool(HALTING_MECHANISMS & set(s["mechanisms"]))),
               # static_halt: 台帳の止め方（事例は親のコードの止め方）に Halt・途中停止の定数があり、事例なら経路の一覧にある。listed_channel: 動的な経路でだけ止める
               "whole_game_basis": ("static_halt" if HALTING_MECHANISMS & set(s["mechanisms"]) and (s["parent"] is None or s["id"] in whole_game_scenes) else
                                    "listed_channel" if s["id"] in whole_game_scenes else None),
               "secret_dependency": s["secret_dependency"], "ruling_ids": s["ruling_ids"], "kyuura_issue": s["kyuura_issue"], "ruling_documents": s["ruling_documents"]}
        if s["id"] in DEFECT_COUPLING:
            row["coupled_defect"] = DEFECT_COUPLING[s["id"]]
        hits = target_of.get(s["id"], [])
        if plan_class == "A":
            if hits:
                cand_id, t = hits[0]
                coverage = t.get("coverage") or "unverified"
                floor = continuation_floor(s)
                if floor and coverage in ("unverified", "full", "question_resolved_other_stops_possible", "partial"):
                    coverage = floor
                row.update({"candidate": cand_id, "coverage": coverage, **({"coverage_note": t["note"]} if t.get("note") else {})})
            else:
                row.update({"candidate": None, "individual_reason": INDIVIDUAL_REASON_BY_SCENE.get(s["id"]) or INDIVIDUAL_REASON_BY_FAMILY.get(s["family"], "")})
        else:
            row["candidate"] = None
        if len(hits) > 1:
            row["also_candidates"] = [c for c, _ in hits[1:]]
        if s["id"] in adopted_scene:
            row["adopted_convention"] = adopted_scene[s["id"]]  # v0.143: 続行側の集合の規約が当たる場面
        scene_rows.append(row)
    for f in NEW_FINDINGS:
        scene_rows.append({"id": f["id"], "parent": None, "code": None, "entry_kind": "new_finding", "family": None, "ledger_classification": None,
                           "plan_class": f["plan_class"],
                           "class_reason": ("この調査で見つけた情報漏れ（v0.146 で修正し、停止の方針の台帳に fixed で加えた）" if f["status"] == "fixed" else
                                            "この調査で見つけた情報漏れ（未修正。台帳には未登録）"), "mechanisms": [], "reachability": "constructed_board",
                           "whole_game": False, "whole_game_basis": None, "secret_dependency": None, "ruling_ids": [], "kyuura_issue": None, "ruling_documents": [], "candidate": None})
    candidates = []
    for cand in CANDIDATES:
        rows = [r for r in scene_rows if r.get("candidate") == cand["id"]]
        codes = sorted({r["parent"] or r["code"] for r in rows})
        c = {**cand, "status": ADOPTED if cand["id"] in ADOPTIONS else STATUS, "codes": codes,
             **({"adoption": {**ADOPTIONS[cand["id"]], "scenes": adoption_scenes(cand)}} if cand["id"] in ADOPTIONS else {}),
             "scene_count": len(rows), "code_count": len(codes),
             "coverage_counts": dict(sorted(collections.Counter(r["coverage"] for r in rows).items())),
             "ruling_ids": sorted({rid for r in rows for rid in r["ruling_ids"]}),
             "kyuura_issues": sorted({r["kyuura_issue"] for r in rows if r["kyuura_issue"]}),
             "ruling_documents": sorted({d for r in rows for d in r["ruling_documents"]}),
             "reachability_counts": dict(sorted(collections.Counter(r["reachability"] for r in rows).items()))}
        c["targets"] = [{**t, "coverage": next((r["coverage"] for r in rows if r["id"] == t["scene"]), t.get("coverage"))} for t in cand["targets"]]
        candidates.append(c)
    plan = {
        "schema_version": SCHEMA_VERSION,
        "title": "未決場面を共通規約で扱うための設計案（調査・設計だけ。規約はどれも案で、採用していない）",
        "base": BASE, "kyuura": KYUURA,
        "sources": {"ledger": {"path": "docs/stop-policy-classification.json", "base_commit": ledger["base"]["commit"], "entries": len(ledger["entries"])},
                    "research": {"path": "kyuura_engine/data/research_links.json", "research_commit": research["research_commit"], "stop_codes": len(research["stop_codes"])}},
        "axes": {"plan_class": PLAN_CLASSES, "coverage": COVERAGE, "shortage_kinds": SHORTAGE_KINDS, "candidate_status": [STATUS, ADOPTED],
                 "note": "plan_class は利用者の依頼の A〜E。台帳の classification（棚卸しの A〜E: A=機能不足・B=技術的制限・C=未裁定・D=独自規約・E=その他）とは別の軸"},
        "candidates": candidates,
        "individual_reason_by_family": INDIVIDUAL_REASON_BY_FAMILY,
        "new_findings": NEW_FINDINGS,
        "defect_coupling": DEFECT_COUPLING,
        "whole_game_channels": WHOLE_GAME_CHANNELS,
        "stages": STAGES,
        "priority": priority_rows(candidates, scene_rows),
        "observation": load_observation(),
        "scenes": scene_rows,
        "adopted_conventions": [{"id": c["id"], "baseline_category": c["baseline_category"], "mode_policy_status": c["mode_policy_status"]} for c in ledger["conventions"]],
        "internal_guard_sites": ledger["counts"]["internal_guard_sites_current"],
    }
    plan["counts"] = counts(plan)
    return plan


def _observed(obs: dict | None, rows: list[dict]) -> dict:
    """規約案の対象の場面のコードの、道具の対戦の HALTED の局数・拒否の回数（コードの単位。事例を分けたコードは、ほかの事例の分を含む）。"""
    if not obs:
        return {"halted_games": "unknown", "rejections": "unknown", "rejection_games": "unknown", "note": "記録がない"}
    codes = {r["parent"] or r["code"] for r in rows}
    split = sorted({r["parent"] for r in rows if r["parent"]})
    rej = {c: (n, g) for c, n, g in obs["rejections"]}
    return {"halted_games": sum(n for c, n in obs["halt_codes"].items() if c in codes),
            "rejections": sum(rej[c][0] for c in codes if c in rej), "rejection_games": sum(rej[c][1] for c in codes if c in rej),
            **({"note": f"事例を分けたコード {split} の数は、ほかの事例の分を含む"} if split else {})}


def priority_rows(candidates: list[dict], scene_rows: list[dict]) -> list[dict]:
    obs = load_observation()
    stage_of = {r: k for k, st in STAGES.items() for r in st["rules"]}
    out = []
    for c in candidates:
        rows = [r for r in scene_rows if r.get("candidate") == c["id"]]
        residual = sum(1 for r in rows if r["coverage"] not in CONTINUABLE_COVERAGE)
        out.append({"candidate": c["id"], "stage": stage_of.get(c["id"]), "whole_game": bool(c.get("whole_game")), "scenes": len(rows), "codes": c["code_count"],
                    "observed": _observed(obs, rows), "prerequisite_for": PRIORITY[c["id"]]["prerequisite_for"], "burden": PRIORITY[c["id"]]["burden"],
                    "risk": PRIORITY[c["id"]]["risk"], "scenes_with_residual_stops_or_unverified": residual})
    return out


def counts(plan: dict) -> dict:
    scenes = plan["scenes"]
    a = [s for s in scenes if s["plan_class"] == "A"]
    covered = [s for s in a if s.get("candidate")]
    by_cand = collections.Counter(s["candidate"] for s in covered)
    dup_codes = sum(c["code_count"] for c in plan["candidates"])
    uniq_codes = len({code for c in plan["candidates"] for code in c["codes"]})
    stop_scenes = [s for s in scenes if s["entry_kind"] in ("research_stop_code", "runtime_stop_code")]
    return {
        "scenes": len(scenes),
        "stop_code_scenes": len(stop_scenes),
        "stop_codes": len({s["parent"] or s["code"] for s in stop_scenes}),
        "by_plan_class": dict(sorted(collections.Counter(s["plan_class"] for s in scenes).items())),
        "a_scenes": len(a),
        "a_scenes_with_candidate": len(covered),
        "a_scenes_individual": len(a) - len(covered),
        "candidates": len(plan["candidates"]),
        "candidate_scenes_with_duplicates": sum(c["scene_count"] for c in plan["candidates"]),
        "candidate_scenes_unique": len(covered),
        "candidate_codes_with_duplicates": dup_codes,
        "candidate_codes_unique": uniq_codes,
        "coverage": dict(sorted(collections.Counter(s["coverage"] for s in covered).items())),
        "fully_continuable_scenes": sum(1 for s in covered if s["coverage"] in CONTINUABLE_COVERAGE),
        "partially_continuable_scenes": sum(1 for s in covered if s["coverage"] in PARTIAL_COVERAGE),
        "scenes_needing_other_work": sum(1 for s in covered if s["coverage"] in EXTRA_COVERAGE),
        "unverified_scenes": sum(1 for s in covered if s["coverage"] == "unverified"),
        "scenes_per_candidate": dict(sorted(by_cand.items())),
        "whole_game_scenes": sum(1 for s in scenes if s["whole_game"]),
        "whole_game_static_halt_scenes": sum(1 for s in scenes if s["whole_game_basis"] == "static_halt"),
        "whole_game_dynamic_channel_scenes": sum(1 for s in scenes if s["whole_game_basis"] == "listed_channel"),
        "whole_game_a_scenes_with_candidate": sum(1 for s in covered if s["whole_game"]),
        "new_findings": len(plan["new_findings"]),
        "internal_guard_sites_not_listed_as_scenes": plan["internal_guard_sites"],
        "note": "場面は台帳の項目（事例のあるコードは事例）。重複を含む数は規約案ごとの対象の合計、重複を除いた数は場面・コードの集合の大きさ。内部ガードは場面に数えない（D。個数だけ）",
    }


# ---------------------------------------------------------------------------------------------------------------------------------------------------
# 確かめ
# ---------------------------------------------------------------------------------------------------------------------------------------------------
REQUIRED_CANDIDATE_FIELDS = ("id", "name", "question", "statement", "applies_when", "targets", "excludes", "depends_on", "conflicts_with", "strict_difference",
                             "impact", "common_implementation", "card_specific_remaining", "regression_tests", "recommendation", "alternatives", "basis", "unverified",
                             "decision_refs")
NONEMPTY_CANDIDATE_FIELDS = ("name", "question", "statement", "applies_when", "targets", "excludes", "strict_difference", "common_implementation",
                             "card_specific_remaining", "regression_tests", "basis", "unverified", "decision_refs")
VAGUE_STATEMENTS = ("できるだけ処理", "失敗しても続ける", "適当に", "可能な限り")


def adoption_scenes(cand: dict) -> list[str]:
    """v0.143: 採用の範囲（案の対象 − 採用で外した対象 + 採用で加えた場面）。"""
    adoption = ADOPTIONS[cand["id"]]
    excluded = {t["scene"] for t in adoption["excluded_targets"]}
    return sorted({t["scene"] for t in cand["targets"]} - excluded | {t["scene"] for t in adoption["added_scenes"]})


def adoption_problems(plan: dict) -> list[str]:
    """v0.143: 採用した案が、エンジンの登録（kyuura_engine.conventions）の規約・集合と範囲で一致するか。"""
    import sys

    sys.path.insert(0, str(ROOT))
    from kyuura_engine import conventions as C

    problems = []
    for c in plan["candidates"]:
        adoption = c.get("adoption")
        if (c["status"] == ADOPTED) != (c["id"] in ADOPTIONS) or (c["status"] == ADOPTED) != (adoption is not None):
            problems.append(f"{c['id']}: 状態 {c['status']} と採用の記録が合わない（採用は ADOPTIONS だけ）")
            continue
        if adoption is None:
            continue
        key = tuple(adoption["convention"])
        convention = C.CONVENTIONS.get(key)
        spec = C.SETS.get(tuple(adoption["set"]))
        if convention is None or spec is None or key not in spec.members:
            problems.append(f"{c['id']}: 採用の規約 {key} が、エンジンの登録の集合 {adoption['set']} にない")
            continue
        if convention.layer != C.LAYER_CONTINUATION or convention.approval != C.APPROVAL_USER_AGREED or spec.usage != C.USAGE_DEVELOPMENT:
            problems.append(f"{c['id']}: 採用の規約の層・承認・集合の区分が、開発用の集合の採用した続行規約ではない")
        if sorted(convention.scenes) != adoption["scenes"]:
            problems.append(f"{c['id']}: 採用の範囲 {adoption['scenes']} が、登録した規約の場面 {sorted(convention.scenes)} と違う")
        targets = {t["scene"] for t in c["targets"]}
        for t in adoption["excluded_targets"]:
            if t["scene"] not in targets or not t.get("reason"):
                problems.append(f"{c['id']}: 採用で外した {t['scene']} が案の対象にない・理由がない")
        for t in adoption["added_scenes"]:
            if t["scene"] in targets:
                problems.append(f"{c['id']}: 採用で加えた {t['scene']} が、もとから案の対象にある")
        scenes = {s["id"]: s for s in plan["scenes"]}
        for sid in adoption["scenes"]:
            if scenes.get(sid, {}).get("adopted_convention") != list(key):
                problems.append(f"{c['id']}: 採用の範囲の場面 {sid} に、採用した規約の印がない")
    scenes = {s["id"]: s for s in plan["scenes"]}
    for cid, adoption in SPEC_ADOPTIONS.items():  # v0.145: 別の仕様案の採用（候補ではない）
        key = tuple(adoption["convention"])
        convention, spec = C.CONVENTIONS.get(key), C.SETS.get(tuple(adoption["set"]))
        if cid in {c["id"] for c in plan["candidates"]} or convention is None or spec is None or key not in spec.members:
            problems.append(f"{cid}: 別の仕様案の採用の規約が、候補と同じ ID か、エンジンの登録の集合 {adoption['set']} にない")
            continue
        if convention.layer != C.LAYER_CONTINUATION or convention.approval != C.APPROVAL_USER_AGREED or spec.usage != C.USAGE_DEVELOPMENT:
            problems.append(f"{cid}: 採用の規約の層・承認・集合の区分が、開発用の集合の採用した続行規約ではない")
        if sorted(convention.scenes) != sorted(adoption["scenes"]):
            problems.append(f"{cid}: 採用の範囲 {adoption['scenes']} が、登録した規約の場面 {sorted(convention.scenes)} と違う")
        for sid in adoption["scenes"]:
            if scenes.get(sid, {}).get("adopted_convention") != list(key):
                problems.append(f"{cid}: 採用の範囲の場面 {sid} に、採用した規約の印がない")
    registered = {key for key, conv in C.CONVENTIONS.items() if conv.layer == C.LAYER_CONTINUATION}
    if registered != {tuple(a["convention"]) for a in (*ADOPTIONS.values(), *SPEC_ADOPTIONS.values())}:
        problems.append(f"エンジンに登録した続行規約 {sorted(registered)} が、採用した案と対応しない")
    return problems


def check(plan: dict, ledger: dict, fresh: dict | None) -> list[str]:
    problems = []
    entries = {e["id"]: e for e in ledger["entries"]}
    ledger_scene_ids = {s["id"] for s in scenes_from_ledger(ledger)}
    finding_ids = {f["id"] for f in plan["new_findings"]}
    scene_ids = [s["id"] for s in plan["scenes"]]
    if len(scene_ids) != len(set(scene_ids)):
        problems.append("場面の ID が重複している")
    missing = ledger_scene_ids - set(scene_ids)
    if missing:
        problems.append(f"台帳の現在有効な項目に、対応先がない: {sorted(missing)[:10]}")
    extra = set(scene_ids) - ledger_scene_ids - finding_ids
    if extra:
        problems.append(f"台帳にない場面がある（参照切れ）: {sorted(extra)[:10]}")
    cand_ids = [c["id"] for c in plan["candidates"]]
    if len(cand_ids) != len(set(cand_ids)):
        problems.append("規約案の ID が重複している")
    decisions = set(ledger["decisions"])
    known_refs = set(cand_ids) | {c["id"] for c in ledger["conventions"]}
    scenes = {s["id"]: s for s in plan["scenes"]}
    for c in plan["candidates"]:
        for f in REQUIRED_CANDIDATE_FIELDS:
            if f not in c:
                problems.append(f"{c['id']}: 項目 {f} がない")
        for f in NONEMPTY_CANDIDATE_FIELDS:
            if not c.get(f):
                problems.append(f"{c['id']}: 項目 {f} が空（適用条件・例外・根拠などの欠け）")
        if c.get("status") != (ADOPTED if c["id"] in ADOPTIONS else STATUS):
            problems.append(f"{c['id']}: 状態が {c.get('status')}（採用した案は adopted、ほかは案だけ。承認済みにしない）")
        if any(v in c.get("statement", "") for v in VAGUE_STATEMENTS):
            problems.append(f"{c['id']}: 規約の文が範囲の分からない言い方")
        rec = c.get("recommendation") or {}
        if not rec.get("option") or not rec.get("reason"):
            problems.append(f"{c['id']}: 推奨案と理由がない")
        if not c.get("alternatives") or any(not a.get("option") or not a.get("reason") for a in c["alternatives"]):
            problems.append(f"{c['id']}: 代替案と理由がない")
        for k in ("information", "rng", "cost", "order"):
            if not (c.get("impact") or {}).get(k):
                problems.append(f"{c['id']}: 影響の {k} がない")
        for d in c.get("decision_refs", []):
            if d not in decisions:
                problems.append(f"{c['id']}: 判断事項 {d} が台帳にない")
        for r in list(c.get("depends_on", [])) + list(c.get("related", [])):
            if r not in known_refs:
                problems.append(f"{c['id']}: 依存・関係の {r} がない")
        for t in c.get("targets", []):
            s = scenes.get(t["scene"])
            if s is None:
                problems.append(f"{c['id']}: 対象 {t['scene']} が場面にない")
                continue
            if s["plan_class"] != "A":
                problems.append(f"{c['id']}: 対象 {t['scene']} は {s['plan_class']}（機能不足・技術的制限・不具合・そのほかを規約の対象にしない）")
            if t.get("coverage") not in COVERAGE:
                problems.append(f"{c['id']}: 対象 {t['scene']} の続けられ方 {t.get('coverage')} が軸にない")
            if t["scene"] in plan["defect_coupling"] and t.get("coverage") != "blocked_by_defect":
                problems.append(f"{c['id']}: 対象 {t['scene']} に未修正の不具合 {plan['defect_coupling'][t['scene']]} があるのに blocked_by_defect でない")
            if s["entry_kind"] == "research_stop_code" and entries.get(t["scene"], {}).get("cases"):
                problems.append(f"{c['id']}: 対象 {t['scene']} は事例のあるコード（事例 ID で当てる）")
        has_whole_game = any(scenes.get(t["scene"], {}).get("whole_game") for t in c.get("targets", []))
        if c.get("whole_game") and not has_whole_game:
            problems.append(f"{c['id']}: 対戦全体を止める規約としたのに、対象に対戦全体を止める場面がない")
        if has_whole_game and not c.get("whole_game"):
            problems.append(f"{c['id']}: 対象に対戦全体を止める場面があるのに、対戦全体を止める規約にしていない（優先の付け方がずれる）")
    covered: dict[str, list[str]] = collections.defaultdict(list)
    for c in plan["candidates"]:
        for t in c["targets"]:
            covered[t["scene"]].append(c["id"])
    for sid, cs in covered.items():
        if len(cs) > 1:
            problems.append(f"場面 {sid} に 2 つ以上の規約案が当たる（暗黙の優先にしない）: {cs}")
    for s in plan["scenes"]:
        if s["plan_class"] not in PLAN_CLASSES:
            problems.append(f"{s['id']}: 区分 {s['plan_class']} が軸にない")
        if s["plan_class"] == "A" and not s.get("candidate") and not s.get("individual_reason"):
            problems.append(f"{s['id']}: A の場面に、規約案も個別の理由もない（未分類）")
        if s["plan_class"] == "A" and s["entry_kind"] != "research_stop_code":
            problems.append(f"{s['id']}: 研究の停止コードでない項目を A にした")
        if s.get("candidate") and s["plan_class"] != "A":
            problems.append(f"{s['id']}: A でない場面に規約案を当てた")
        if s["reachability"] not in ("legal_sequence", "constructed_board", "static_only", "test_only_mutation", "unknown"):
            problems.append(f"{s['id']}: 到達可能性 {s['reachability']} が軸にない")
        if s.get("coverage") == "full" and s["reachability"] == "unknown":
            problems.append(f"{s['id']}: 到達可能性が unknown なのに full")
    for ch in plan["whole_game_channels"]:
        for sid in ch["scenes"]:
            if sid not in scenes:
                problems.append(f"{ch['id']}: 場面 {sid} がない")
        for cid in ch["candidates"]:
            if cid not in cand_ids:
                problems.append(f"{ch['id']}: 規約案 {cid} がない")
    staged = [r for st in plan["stages"].values() for r in st["rules"]]
    if sorted(staged) != sorted(cand_ids) or len(staged) != len(set(staged)):
        problems.append("段階の規約の一覧が、規約案とちょうど 1 回ずつ対応しない")
    if {p["candidate"] for p in plan["priority"]} != set(cand_ids):
        problems.append("優先の表が規約案と対応しない")
    for p in plan["priority"]:
        for r in p["prerequisite_for"]:
            if r not in cand_ids:
                problems.append(f"優先の表の {p['candidate']}: 前提になる規約 {r} がない")
    if counts(plan) != plan["counts"]:
        problems.append("集計が場面・規約案から求めた値と違う")
    for code in ("UNRESOLVED_RULING",):
        s = scenes.get(code)
        if s is not None and s["plan_class"] == "A":
            problems.append(f"{code}: 名前が UNRESOLVED だけを理由に A にしない")
    if fresh is not None and stable(fresh) != stable(plan):
        problems.append("台帳・作成スクリプトから作り直した設計案と、書き出した設計案が違う（--write で書き直す）")
    problems += generated_block_problems(plan)
    problems += adoption_problems(plan)
    return problems


# ---------------------------------------------------------------------------------------------------------------------------------------------------
# 文書の生成した表
# ---------------------------------------------------------------------------------------------------------------------------------------------------
def _markers(name: str) -> tuple[str, str]:
    return (f"<!-- generated:{name} begin（scripts/build_play_policy_family_plan.py --write が書く。手で直さない） -->", f"<!-- generated:{name} end -->")


def _cell(value) -> str:
    return str(value).replace("|", "／").replace("\n", " ")


def render_counts(plan: dict) -> str:
    c = plan["counts"]
    rows = [("場面（台帳の現在有効な項目。事例のあるコードは事例）", c["scenes"]), ("うち停止コードの場面", c["stop_code_scenes"]), ("停止コード（重複を除く）", c["stop_codes"])]
    rows += [(f"区分 {k}（{PLAN_CLASS_SHORT[k]}）", v) for k, v in c["by_plan_class"].items()]
    rows += [("A のうち規約案の対象", c["a_scenes_with_candidate"]), ("A のうち個別（共通化しない）", c["a_scenes_individual"]), ("規約案", c["candidates"]),
             ("規約案の対象の場面（重複を含む）", c["candidate_scenes_with_duplicates"]), ("規約案の対象の場面（重複を除く）", c["candidate_scenes_unique"]),
             ("関連する停止コード（重複を含む）", c["candidate_codes_with_duplicates"]), ("関連する停止コード（重複を除く）", c["candidate_codes_unique"]),
             ("規約だけで続けられる場面（full）", c["fully_continuable_scenes"]), ("一部だけ扱える場面", c["partially_continuable_scenes"]),
             ("追加の実装・秘密の確かめ・不具合の修正が要る場面", c["scenes_needing_other_work"]), ("続けられるか未確認の場面（unverified）", c["unverified_scenes"]),
             ("対戦全体を止める場面（静的な止め方と、経路の一覧の場面）", c["whole_game_scenes"]), ("うち静的な Halt・途中停止の定数で止める", c["whole_game_static_halt_scenes"]),
             ("うち動的な経路（4 章の一覧）でだけ止める（ほかの場面では拒否）", c["whole_game_dynamic_channel_scenes"]), ("対戦全体を止める場面のうち規約案の対象", c["whole_game_a_scenes_with_candidate"]), ("この調査で見つけた不具合", c["new_findings"]),
             ("内部ガード（場面に数えない。D）", c["internal_guard_sites_not_listed_as_scenes"])]
    return "\n".join(["| 対象 | 件数 |", "|---|---:|"] + [f"| {_cell(a)} | {b} |" for a, b in rows])


def render_candidates(plan: dict) -> str:
    lines = ["| 規約案 | 名前 | 群 | 全体停止 | 場面 | コード | 続けられ方（場面の数） | 推奨（案） | 判断事項 |", "|---|---|---|:---:|---:|---:|---|---|---|"]
    for c in plan["candidates"]:
        cov = "・".join(f"{k} {v}" for k, v in c["coverage_counts"].items())
        lines.append(f"| `{c['id']}` | {_cell(c['name'])} | {c['cluster']} | {'○' if c.get('whole_game') else ''} | {c['scene_count']} | {c['code_count']} | {cov} | "
                     f"{_cell(c['recommendation']['option'])} | {'・'.join(c['decision_refs'])} |")
    return "\n".join(lines)


def render_whole_game(plan: dict) -> str:
    lines = ["| 経路 | 種類 | 止め方 | 箇所 | 場面 | 規約案 | 続けるのに要るもの |", "|---|---|---|---|---|---|---|"]
    for ch in plan["whole_game_channels"]:
        lines.append(f"| `{ch['id']}` | {ch['kind']} | {ch['mechanism']} | {_cell(ch['site'])} | {len(ch['scenes'])} | {'・'.join(ch['candidates']) or '—'} | {_cell(ch['continuation'])} |")
    return "\n".join(lines)


def render_classes(plan: dict) -> str:
    groups = collections.defaultdict(collections.Counter)
    for s in plan["scenes"]:
        if s["plan_class"] != "A":
            groups[s["plan_class"]][s["class_reason"]] += 1
    lines = ["| 区分 | 理由 | 場面 |", "|---|---|---:|"]
    for k in sorted(groups):
        for reason, n in sorted(groups[k].items(), key=lambda x: -x[1]):
            lines.append(f"| {k} | {_cell(reason)} | {n} |")
    return "\n".join(lines)


def render_individual(plan: dict) -> str:
    per = collections.Counter(s["family"] for s in plan["scenes"] if s["plan_class"] == "A" and not s.get("candidate"))
    lines = ["| 族（台帳） | 個別の場面 | 共通化しない理由 |", "|---|---:|---|"]
    for fam, n in sorted(per.items(), key=lambda x: -x[1]):
        lines.append(f"| {fam} | {n} | {_cell(INDIVIDUAL_REASON_BY_FAMILY.get(fam, ''))} |")
    return "\n".join(lines)


def render_observation(plan: dict) -> str:
    obs = plan.get("observation")
    if not obs:
        return "（記録がない環境。リポジトリの外の C:/dev/kyuura-engine-play-policy-evidence/census_summary.json）"
    lines = [f"- 木: `{obs['head']}`（版 {obs['version']}）。道具: {obs['tool']}。方策: {obs['policy']}。seed: {obs['seeds']}。組: {obs['batches']} バッチ（各バッチの組 × 2 席 × seed）",
             f"- 分母: 対戦 {obs['games']} 局。数え方: 1 局の終わり方（game_over・halted・道具の打ち切り）を 1 回ずつ。拒否は局ごとの回数の合計（同じ局の同じ拒否を重ねて数える）",
             "", "| 終わり方 | 局 | 意味 |", "|---|---:|---|"]
    meaning = obs.get("outcome_meaning", {})
    lines += [f"| {k} | {v} | {_cell(meaning.get(k, ''))} |" for k, v in obs["outcomes"].items()]
    by_code = collections.defaultdict(list)
    for s in plan["scenes"]:
        by_code[s["parent"] or s["code"] or s["id"]].append(s)

    def where(code):
        rows = by_code.get(code, [])
        cands = sorted({s["candidate"] for s in rows if s.get("candidate")})
        if cands:
            return "・".join(cands) + ("（事例ごと）" if len(rows) > 1 else "")
        return "・".join(sorted({f"{s['plan_class']}（{'個別' if s['plan_class'] == 'A' else '規約の対象外'}）" for s in rows})) or "—"

    lines += ["", "| 終端のコード（HALTED・途中停止） | 局 | 規約案・区分 |", "|---|---:|---|"]
    for code, n in obs["halt_codes"].items():
        lines.append(f"| `{code}` | {n} | {where(code)} |")
    lines += ["", "| 拒否（回数の多い順。上位 25。対戦は止まらず、道具は別の操作を選んだ） | 回 | 局 | 規約案・区分 |", "|---|---:|---:|---|"]
    for code, n, g in obs["rejections"][:25]:
        lines.append(f"| `{code}` | {n} | {g} | {where(code)} |")
    if obs.get("sudden_death"):
        sd = obs["sudden_death"]
        lines += ["", (f"- サドン・デスの道具（{sd['tool']}。corpus {'・'.join(sd['corpora'])}・seed {sd['seeds']}）: 対戦 {sd['games']} 局、終わり方 {sd['outcomes']}、"
                       f"延長戦の開始 {sd['extensions_started']} 回、延長戦の準備の HALTED {sd['halt_codes'] or 'なし'}")]
    return "\n".join(lines)


def render_priority(plan: dict) -> str:
    lines = ["| 段階 | 規約案 | 全体停止 | 場面 | コード | HALTED の局 | 拒否（回・局） | 前提になる規約 | 負担 | 危険 | 別の停止・未確認の残る場面 |",
             "|---|---|:---:|---:|---:|---:|---|---|---|---|---:|"]
    order = list(plan["stages"])
    for p in sorted(plan["priority"], key=lambda p: (order.index(p["stage"]), -p["whole_game"], -p["scenes"])):
        o = p["observed"]
        mark = "＊" if o.get("note") else ""  # 事例を分けたコードの数は、ほかの事例の分を含む
        lines.append(f"| {p['stage']} | `{p['candidate']}` | {'○' if p['whole_game'] else ''} | {p['scenes']} | {p['codes']} | {o['halted_games']}{mark} | {o['rejections']}・{o['rejection_games']}{mark} | "
                     f"{'・'.join(p['prerequisite_for']) or '—'} | {_cell(p['burden'])} | {_cell(p['risk'])} | {p['scenes_with_residual_stops_or_unverified']} |")
    return "\n".join(lines)


def render_stages(plan: dict) -> str:
    lines = ["| 段階 | 名前 | 規約案 | 先に要るもの | 共通処理の変更の範囲 | 完了の基準 | 残るもの |", "|---|---|---|---|---|---|---|"]
    for k, st in plan["stages"].items():
        lines.append(f"| {k} | {_cell(st['name'])} | {'・'.join(st['rules']) or '—'} | {'・'.join(st['prerequisites']) or '—'} | {_cell(st['scope'])} | {_cell(st['done_when'])} | {_cell(st['remains'])} |")
    return "\n".join(lines)


def render_candidate_details(plan: dict) -> str:
    out = []
    for c in plan["candidates"]:
        targets = "、".join(f"`{t['scene']}`（{t['coverage']}）" for t in c["targets"])
        out += [f"#### {c['id']}: {c['name']}", "",
                f"- **問い**: {c['question']}",
                f"- **規約の文（案）**: {c['statement']}",
                f"- **適用条件**: {c['applies_when']}",
                f"- **対象の場面（続けられ方）**: {targets}",
                f"- **除外・対象外の隣の場面**: {'／'.join(c['excludes'])}",
                *( [f"- **例外**: {'／'.join(c['exceptions'])}"] if c.get("exceptions") else [] ),
                f"- **依存・関係・競合**: 依存 {'・'.join(c['depends_on']) or 'なし'}／関係 {'・'.join(c.get('related', [])) or 'なし'}／競合 {'・'.join(c['conflicts_with']) or 'なし'}",
                f"- **厳密モードとの差**: {c['strict_difference']}",
                f"- **影響**: 公開の情報 {c['impact']['information']}／乱数 {c['impact']['rng']}／コスト {c['impact']['cost']}／処理の順番 {c['impact']['order']}",
                f"- **共通処理で実装できる範囲**: {c['common_implementation']}",
                f"- **カード固有の対応が残る範囲**: {c['card_specific_remaining']}",
                f"- **回帰テスト**: {'／'.join(c['regression_tests'])}",
                f"- **推奨（案）**: {c['recommendation']['option']}（{c['recommendation']['reason']}）",
                f"- **代替案**: {'／'.join(a['option'] + '（' + a['reason'] + '）' for a in c['alternatives'])}",
                f"- **根拠**: {'／'.join(c['basis'])}。研究の記録: 裁定 {'・'.join(c['ruling_ids']) or '—'}、kyuura の論点 {'・'.join(c['kyuura_issues']) or '—'}",
                f"- **未確認**: {'／'.join(c['unverified'])}",
                f"- **判断事項**: {'・'.join(c['decision_refs'])}（状態 {c['status']}）", ""]
    return "\n".join(out).rstrip()


def render_individual_observed(plan: dict) -> str:
    """個別（共通化しない）の場面のうち、道具の対戦で多く当たったもの（終端の局数 → 拒否のあった局数の順。上位 12）。"""
    obs = plan.get("observation")
    if not obs:
        return "（記録がない環境）"
    rej = {c: (n, g) for c, n, g in obs["rejections"]}
    rows = []
    for s in plan["scenes"]:
        if s["plan_class"] != "A" or s.get("candidate") or s["parent"]:
            continue
        h = obs["halt_codes"].get(s["code"], 0)
        n, g = rej.get(s["code"], (0, 0))
        if h or g:
            rows.append((h, g, n, s))
    rows.sort(key=lambda r: (-r[0], -r[1], -r[2], r[3]["id"]))
    lines = ["| 場面 | 族 | 終端の局 | 拒否（回・局） | 個別の理由 |", "|---|---|---:|---|---|"]
    for h, g, n, s in rows[:12]:
        lines.append(f"| `{s['id']}` | {s['family']} | {h} | {n}・{g} | {_cell(s['individual_reason'])} |")
    return "\n".join(lines)


RENDERERS = {"plan-counts": render_counts, "plan-candidates": render_candidates, "plan-whole-game": render_whole_game, "plan-classes": render_classes,
             "plan-individual": render_individual, "plan-observation": render_observation, "plan-individual-observed": render_individual_observed,
             "plan-priority": render_priority, "plan-stages": render_stages,
             "plan-candidate-details": render_candidate_details}


def with_generated_blocks(text: str, plan: dict) -> str:
    for name, render in RENDERERS.items():
        begin, end = _markers(name)
        pattern = re.compile(re.escape(begin) + r".*?" + re.escape(end), re.DOTALL)
        if not pattern.search(text):
            raise SystemExit(f"文書に生成の印 {name} がない")
        block = begin + "\n" + render(plan) + "\n" + end
        text = pattern.sub(lambda _m, block=block: block, text)
    return text


def generated_block_problems(plan: dict) -> list[str]:
    if not DOCUMENT.exists():
        return [f"{DOCUMENT.name} がない"]
    text = DOCUMENT.read_text(encoding="utf-8")
    problems = []
    for name in RENDERERS:
        begin, end = _markers(name)
        if text.count(begin) != 1 or text.count(end) != 1:
            problems.append(f"{DOCUMENT.name}: 生成の印 {name} がちょうど 1 つでない")
    if not problems and with_generated_blocks(text, plan) != text:
        problems.append(f"{DOCUMENT.name}: 生成した表が設計案と違う（--write で書き直す）")
    return problems


def stable(plan: dict) -> str:
    return json.dumps(plan, ensure_ascii=False, sort_keys=True)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--write", action="store_true")
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    fresh = build()
    if args.write:
        OUTPUT.write_text(json.dumps(fresh, ensure_ascii=False, indent=1) + "\n", encoding="utf-8", newline="\n")
        print(f"wrote {OUTPUT.relative_to(ROOT).as_posix()}: {len(fresh['scenes'])} scenes, {len(fresh['candidates'])} candidates")
        DOCUMENT.write_text(with_generated_blocks(DOCUMENT.read_text(encoding="utf-8"), fresh), encoding="utf-8", newline="\n")
        print(f"wrote generated blocks of {DOCUMENT.relative_to(ROOT).as_posix()}")
    plan = load_json(OUTPUT)
    if fresh.get("observation") is None:
        # 記録（リポジトリの外）がない環境では、記録の写しと、記録から求めた優先の表の数を比べない
        fresh = dict(fresh, observation=plan.get("observation"), priority=plan.get("priority"))
    problems = check(plan, load_json(LEDGER), fresh)
    for problem in problems:
        print("PROBLEM", problem)
    print(json.dumps(plan["counts"], ensure_ascii=False, indent=1))
    return 1 if problems else 0


if __name__ == "__main__":
    raise SystemExit(main())

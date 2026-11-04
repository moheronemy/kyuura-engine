# v0.142: 規約集合の識別・版の管理と、共通処理基盤 S1

この版は、規約集合を対戦へ渡し、状態に持つための基盤（共通規約の設計案の段階 S1）を実装した版です。**規約集合として実装したのは、今の挙動をそのまま固定した集合だけです。**
共通規約の案 27 件（[play-policy-family-plan.md](play-policy-family-plan.md)）は 1 つも採用していません。未決の場面を続ける処理も加えていません。未決の場面は、今までどおり止まります
（拒否・HALTED・途中停止の区別も、停止コード・理由の文も同じ）。

- 構造化した記録: [stop-policy-classification.json](stop-policy-classification.json) の `ruleset_agreements`・`decision_status`・`updates`、同梱の記録
  `kyuura_engine/data/convention_records.json`（`scripts/build_convention_records.py` が台帳から作る）
- 実装: `kyuura_engine/conventions.py`
- テスト: `tests/test_conventions_v0_142.py`

## 1. 基点と承認

| 項目 | 値 |
|---|---|
| 基点 | `0a3ee994f3d9a89a5e3a536e7b0ab9be9900a5fa`（`claude/play-policy-family-plan` の最後。v0.141 の最後 `8164194ca289c5f7f332c7f16d7f700a81a37215` と共通規約の設計案を含む。どちらも `origin/main` `816bcffb86edeb3ea713ee08818a070e036fe0a8` には未取り込み） |
| 作業ブランチ | `claude/ruleset-s1-foundation` |
| 基点を選んだ理由 | 設計案（S1 の範囲・完了の基準）と v0.141 の版の両方を含む公開済みの履歴。main（v0.140）から作ると v0.141 と設計案が欠ける |
| 利用者の変更 | 追跡していない `.claude/` だけ（変えていない） |
| kyuura | 読んだだけ（変えていない） |

**承認された設計方針（2026-11-04。この版の依頼で、利用者が「この指示を設計方針への承認として記録する」と明記したもの）**。エンジンの設計方針で、公式の裁定・kyuura の研究上の
解決ではありません。台帳の `ruleset_agreements` に記録しました（モードの定義の合意 `mode_agreements` の 6 項目（2026-11-03）とは別の出典）。

| ID | 方針 | 実装 |
|---|---|---|
| AGR-RULESET-IDENTITY | 規約集合は、集合ID・版・含まれる規約IDと各版・内容ハッシュで識別する | 4 章 |
| AGR-RULESET-IMMUTABLE | 同じ集合IDと版の内容は不変とする | 4.3 節（固定した照合値） |
| AGR-RULESET-VERSIONING | 規約の意味の変更と、エンジンの不具合修正を区別する | 4.4 節 |
| AGR-RULESET-NO-MIDGAME-CHANGE | 対戦開始後の規約集合の変更は禁止する | 3 章（変えるコマンドはない） |
| AGR-RULESET-SUDDEN-DEATH | サドン・デスへ同じ規約集合を引き継ぐ | 3 章（`SEGMENT_FIELD_POLICY` の keep） |
| AGR-RULESET-LEGACY | 規約集合の記録がない旧状態は、旧来の固定集合として扱う。現在のプレイ用集合へ自動変換しない | 6 章 |
| AGR-RULESET-DEVELOPMENT | 規約がそろわない構成は開発用として区別し、通常のプレイ用として完成扱いにしない | 4.2 節・5 章 |

判断事項の状態（[ruleset-mode-decisions.md](ruleset-mode-decisions.md)）: DEC-RULESET-IDENTITY・DEC-RULESET-VERSIONING・DEC-MODE-CHANGE-DURING-GAME・DEC-LEGACY-STATES は `agreed`、
DEC-PLAY-DEBUG-PARTIAL・DEC-PLAY-CONFIG-INCOMPLETE-START は `partly_agreed`（区別することだけ承認。開発用の集合を設けるか・不足のある構成で始められるかは未決）。DEC-LEGACY-STATES の
承認の中身は、設計の時点の推奨案（作成した版が分かる場合だけその版に対応付ける）とは違います（旧来の固定集合として扱う）。設計・判断事項の文書の過去の推奨は書き換えず、経過を追記しました。

ほかの判断事項（DEC-BASELINE-NONUSER・DEC-BASELINE-CENSUS・DEC-CARD-DATA-CORRECTIONS・DEC-CONVENTION-GRANULARITY・DEC-CONVENTION-CONFLICTS・DEC-RESUME-WITH-OTHER-RULESET と、
個々の続行規約の判断事項）は未決のままです。

## 2. 分けたもの

| もの | どこ | 変わるとき |
|---|---|---|
| エンジンの版 | `kyuura_engine.__version__`（0.142.0）。書き出しの形式 35 の `engine_version` | 不具合の修正・最適化・新しいカード・規約の処理の実装 |
| 書き出しの形式の版 | `serialize.FORMAT_VERSIONS`（この版で 35） | 書き出しの形が変わる |
| 対戦の条件のルールの組 | `rules.RuleSet`（`JP-2000.02.14`。デッキ 60 枚・サイド 6 枚など） | 変えていない |
| 規約集合 | `conventions.ConventionSet`（集合 ID・版・区分・含む規約・完全性の主張） | 規約を加える・除く・規約の版を上げる |
| 規約 | `conventions.Convention`（規約 ID・版・層・承認の状態・意味の内容） | 規約の意味・範囲を変える |

**ルールの組との関係**: 規約集合は、ルールの組の値（枚数など）を持ちません。ルールの組は `new_game` の `rules`・`GameState.rules` のまま（規約集合の照合値にも入れない）。
同じ値を 2 か所に持たないので、食い違いは起こりません。規約集合が決めるのは、ルールの組で決まらない場面（利用者の指定・今の実装の仮定・将来の続行規約）の扱いです。

## 3. 対戦への組み込み

- `new_game(..., conventions=None)`: 省略すると今の挙動の集合 `CS-KYUURA-CURRENT@1`。`ConventionSet`・`"ID@版"`・`ConventionSetIdentity` を受け付け、登録した集合と内容が同じときだけ
  始めます。合わなければ対戦を作らずに `ConventionSetError`（`INVALID_CONVENTION_SET`）。
- 状態（`GameState.conventions`）には、確かめた識別の値（`ConventionSetIdentity`。文字列・整数・tuple だけ）を置き、渡したオブジェクトは持ちません。
- コマンド（`apply_command` の入口）と観測（`observe`）の前に、状態の識別がこの版の登録の内容と同じかを確かめます（`conventions.require_state_conventions`）。登録の記録（利用者の
  指定の登録・同梱の記録）を後から差しかえて内容が変わったら、推測で続けずに `UnsupportedError`（`UNSUPPORTED_CONVENTION_SET`）。確かめは処理の前で、状態・乱数・ログを変えません。
- サドン・デスの延長戦は同じ値を引き継ぎます（`SEGMENT_FIELD_POLICY` の keep）。複製（`clone`・`peek`・`deepcopy`・pickle）・決定待ち・途中停止の状態も同じ値を持ちます。
- 対戦中に集合を変えるコマンドは加えていません。
- 盤面を直接作った状態（`GameState(...)`）の既定値は、今の挙動の集合です。
- 「厳密」という名前で処理を分けていません。今の集合は、承認された利用者の指定と、承認のない今の実装の記録を含む「今の挙動」の集合で、公式の根拠だけの集合ではありません。

## 4. モデルと識別

### 4.1 この版の規約と集合

| 規約 ID | 層 | 承認 | 内容 |
|---|---|---|---|
| 利用者の指定 11（`USER-BIRTHDAY-COIN-ONLY` ほか。既存の指定の ID をそのまま使う） | `baseline_user` | `user_agreed`（AGR-MODE-BASELINE-USER） | エンジンの登録の記録（`effects.USER_SIMPLIFICATIONS`・`USER_SPECIFIED_REFERENCES`・`USER_SPECIFIED_RULES`・`USER_SPECIFIED_NAMES`・`decisions.USER_PRIZE_ORDER_RULES`・`sudden_death.USER_SUDDEN_DEATH_OWNERSHIP_RESET`）を指定の ID ごとに集めたもの |
| `CB-IMPLEMENTATION-ASSUMPTIONS` | `current_behavior` | `not_approved` | 実装上の仮定の一覧（[implementation-assumptions.json](implementation-assumptions.json)）の、今の実装にある項目（状態 `adopted_current`・`documented_impl_unverified`。利用者の指定を除く）の ID・区分・状態 |

| 集合 | 区分 | 含む規約 | 用途 |
|---|---|---|---|
| `CS-KYUURA-CURRENT@1` | `standard` | 上の 12 | 省略したときの集合。今の挙動 |
| `CS-KYUURA-LEGACY-UNRECORDED@1` | `legacy` | 上の 12（同じ版） | 記録のない旧状態の対応付けだけ（6 章）。新しい対戦には使えない |

- 承認のない実装上の仮定・簡略化・データの訂正は、`CB-IMPLEMENTATION-ASSUMPTIONS` の **今の挙動の記録**として入れました。承認・採用の記録ではありません（層・承認の状態で区別し、
  `not_approved` 以外にした構成は拒否する）。DEC-BASELINE-NONUSER の答え（基礎集合に入れるか）ではありません。
- データの訂正（PR1-069 の名前など）を規約集合の要素にするかは未決（DEC-CARD-DATA-CORRECTIONS）。この版では、実装上の仮定の一覧にあるデータの訂正の項目を今の挙動の記録に含めただけで、
  カードデータの識別（写しの元のコミット）は今までどおり `card_data` です。
- 続行規約（層 `continuation`）は 1 つもありません。

### 4.2 区分と完全性の主張

- `usage`: `standard`（通常）・`development`（規約がそろわない開発・検証用。承認のない続行規約を入れられるのはこれだけ）・`legacy`（旧状態用）。この版に開発用の集合はありません。
- `completeness`: この版の集合はどれも `halts_at_undecided`（未決の場面で止まる）。「止まらずに対戦を終えられる」集合（`play_complete`）の完全性の判定は実装していないので、
  その主張は構成の誤りとして拒否します（拡張点 `conventions.completeness_problems`）。今の集合を「止まらずに完了できる集合」とは表示しません。

### 4.3 照合値

- 照合値は内容を識別するための SHA-256 です。署名・認証ではありません（誰が作ったか・改ざんされていないことは示さない）。
- 正規化（`conventions.canonical_bytes`）: 文字列は NFC・改行を LF、並びは list、辞書は文字列のキーだけでキーの順に並べる、列挙は値、dataclass は項目の辞書。浮動小数点数は受け付けない。
  `json.dumps(ensure_ascii=False, sort_keys=True, separators=(",", ":"))` の UTF-8 に、規約・集合で別の区切りの前置きを付けて SHA-256。ファイルの絶対パス・実行環境・`PYTHONHASHSEED` に
  よりません（テストが 3 つの `PYTHONHASHSEED` で同じ値を確かめる）。
- 意味の内容に入れるもの: 規約の ID・版・層・承認の状態・文・内容（登録の記録の項目）・`requires`・`conflicts`・当たる場面。入れないもの: 説明上の参照（規約の `references`、
  登録の記録の `source`・`document`・`kyuura_record`・`print_check`）、集合の説明。行番号は内容に入りません。
- 集合の照合値は、集合の ID・版・区分・完全性の主張と、含む規約の (ID, 版, 照合値) を ID の順に並べたものから作ります。
- 固定した値: `conventions.PINNED_CONVENTION_DIGESTS`・`PINNED_SET_DIGESTS`。計算した値が違えば「同じ ID・版のまま内容を変えた」として拒否します。内容を変えるときは版を上げ、新しい値を
  加えます（古い値は書き換えない）。

### 4.4 規約の意味の変更とエンジンの修正

- 規約の照合値は意味の記録だけに付け、エンジンのコードには付けません。同じ規約の処理の不具合を直しても、規約・集合の版は変わりません（エンジンの版が変わる。書き出しの形式 35 の
  `engine_version` で区別する）。
- 利用者の指定の登録の記録の意味の項目（対象・規則・範囲・処理に使う文面など）を変えると、照合値が変わり、版を上げるまで対戦を始められません（テストが確かめる）。
- 実装上の仮定の一覧が変わる（項目が増える・状態が変わる）と、同梱の記録を作り直したときに `CB-IMPLEMENTATION-ASSUMPTIONS` の照合値が変わります。そのときは、規約集合の版を上げるか、
  記録の更新を戻すかを判断します（黙って同じ版のまま通らない）。

## 5. 構成の検査（開始の前）

`conventions.validate` が、対戦を始める前に次を確かめます。どれかに当たれば `ConventionSetError` で始めません。

| 検査 | 内容 |
|---|---|
| 集合の ID・版・内容 | 未知の集合 ID・版。登録した同じ ID・版と中身（区分・完全性・含む規約）が違う。照合値が固定した値と違う |
| 規約の存在と版 | 未知の規約 ID・版。照合値が固定されていない・違う |
| 重複・競合・依存 | 同じ ID の規約の重複。`conflicts` の同居。`requires` の不足。同じ場面に 2 つ以上の規約（暗黙の優先順位を作らない。DEC-CONVENTION-CONFLICTS の推奨の既定と同じで、上書きの仕組みは作っていない） |
| 実装 | この版のエンジンが処理を持たない規約（続行規約はどれも未実装） |
| 層と承認 | 利用者の指定の層が承認されていない。今の挙動の記録を承認済みにした。承認のない続行規約を通常の集合に入れた |
| 利用者の指定を外した集合 | エンジンの登録はいつもはたらくので、外した集合はこの版では実装できない |
| 区分 | 旧状態用の集合で新しい対戦を始める |
| 完全性 | `play_complete` の主張（判定は未実装） |

## 6. 記録のない旧状態

- v0.141 までの状態の写し（pickle）は `conventions` の項目を持ちません。`GameState.__setstate__` は、項目がないときだけ「記録なし」（`conventions.UNRECORDED`）を置きます（今の集合の
  既定値にしない）。
- 記録なしの状態を、次の条件を満たすときだけ `CS-KYUURA-LEGACY-UNRECORDED@1` に対応付けます（`conventions.legacy_problems`）: 最初の区間のログの最初が `game_created` で、項目が v0.141 までの
  形（kind・turn・rules・seed・card_data_commit）のまま、値が状態のルールの組・seed・写しの元と同じ（`new_game` で作った対戦の状態）。
- 満たさない状態（盤面を直接作った状態・ログの合わない状態）と、記録の形が違う状態・この版が知らない集合の状態・登録の内容と違う識別の状態は、観測・コマンドの前に
  `UNSUPPORTED_CONVENTION_SET` で拒否し、形式 35 の書き出しは `ValueError` にします。理由の文に状態の中の値を書きません。
- 作った版・使われた規約を「記録がない」ことから推測しません。旧状態用の集合の処理は、この版のエンジンの処理です。**過去のすべてのエンジンの版の異なる挙動を再現するとは主張しません。**
  前の版が後の版の状態を扱えるという保証も加えていません。今の集合（将来のプレイ用の集合を含む）へ自動で変換しません（延長戦を始めても記録なしのまま）。
- 新しい読み込みの機能・pickle の安全化はしていません（pickle は信頼できない写しを読む形式ではない。v0.140 の互換性の約束のまま）。

## 7. 保存・書き出し・観測・ログ

- 書き出しの形式 35（`serialize.state_to_dict`）: 34 の最上位に `convention_set`（`{"id", "version", "digest", "usage", "completeness", "members"}`）と `engine_version` を加えた。
  形式の番号は形の版なので、新しい最上位の項目のために上げました。
- 形式 1〜34: 規約集合の項目を持たないので、記録のない状態の意味（その版のエンジンの今の挙動）と同じ意味の集合（`CS-KYUURA-CURRENT@1`・`CS-KYUURA-LEGACY-UNRECORDED@1`。
  `conventions.IMPLICIT_IN_OLD_FORMATS`）と記録なしの状態だけを書けます。ほかの集合（開発用・後の版の集合）は、落とすと意味が変わるので `ValueError`。今の集合の形式 1〜34 の書き出しは
  v0.141 と同じです。
- 観測（`observe`）: 最上位に `convention_set`（書き出しと同じ形。全員に見える公開の情報。秘密の情報は入らない）を加えた。旧状態は旧状態用の集合を示します。
- ログ: 変えていません（`game_created` に識別を加えていない）。形式 1 の参照データ（v0.1 の互換性の参照）がログ全体を比べるので、ログを変えると参照データの再生成が要るためです。対戦の
  開始時の識別は、状態・書き出し・観測から分かります。規約を当てはめたイベントは、続行規約がないので書きません。
- 監査（`tests/log_audit.py`）: 形式の番号と項目の表を独立に更新しました（`LATEST_FORMAT` 35、`convention_set`・`engine_version` は 35 から。古い形式に書いてよい集合の一覧も独立に持つ）。

## 8. 場面の ID と規約の照会

- 場面の ID は、停止の方針の台帳の項目 ID（事例のあるコードは事例 `コード#事例`）をそのまま使います（新しい ID の体系を作らない）。同梱の記録の `scene_index` は台帳から機械的に作り、
  停止コード → 場面の対応を持ちます（`scripts/build_convention_records.py --check` が、台帳の停止コードの対応の漏れ・不正な参照・事例との食い違い・設計案の場面との違いを見つける）。
- 停止コードと場面を区別します。同じ場面に複数のコードを対応付けられる形（場面の `codes` は並び）です（今の台帳では、どの場面も 1 つのコード）。
- 照会（`conventions.continuation_lookup`）: 事例を指定しないとき、事例が 2 つ以上あるコードは `case_not_identified`（コードだけで規約を決めない）。台帳にないコードは `unknown_scene`。
  続行規約は集合にないので、どの場面も `convention` は None です（テストが全場面で確かめる）。
- 止める箇所での照会（`conventions.stop_without_continuation`）を、対戦を止める 4 か所に置きました。止める前に引くだけで、停止の例外を捕まえて無視する仕組みではありません。
  規約が見つかったらエンジンの不具合として `RuntimeError`（この版の構成の検査が続行規約を受け付けないので起こらない）。

| 箇所 | 事例の特定 |
|---|---|
| 準備の化石・ピッピ人形の手札（`engine._deal_opening_hands`。`UNRESOLVED_PLAY_AS_POKEMON_SETUP`） | `#initial-setup`・`#sudden-death-segment`（区間で決める） |
| 準備の切り直しの補償（同。`UNRESOLVED_MULLIGAN_COMPENSATION`） | 同上 |
| HALTED にする共通の処理（`procedures.halt`。ポケモンチェック・番の終わり・答えのない決定） | 特定しない（事例が 2 つ以上のコード `UNRESOLVED_SCRAM_TIMING` などは `case_not_identified`） |
| 途中停止（`interruption.interrupt`。DU1・TW1 など） | 事例のないコードだけ |

- **未接続（次の段階）**: コマンドの拒否で止める場面（台帳の `command_rejection`・`answer_rejection`。止める場面の大部分）は、拒否を投げる箇所に照会を置いていません。続けるには箇所ごとに
  処理を書く必要があり（S2b・S3）、この版では止め方を変えないためです。事例が 2 つ以上のコードのうち、HALTED にする共通の処理を通るもの（`UNRESOLVED_SCRAM_TIMING#pokemon-check`、
  `UNRESOLVED_FACE_UP_DECK_HIDDEN_TAKE#decision-halt`）は、その箇所で事例を特定していません（`case_not_identified` で止める）。
- **利用者の指定との区別**: 利用者の指定（基礎の規約）は、エンジンの登録がいつも当てはめます。照会は続行規約だけを引き、基礎の規約を場面の照会で引きません（利用者の指定の ID を照会すると
  `unknown_scene`）。基礎の規約は、構成の検査で集合から外せないことを確かめます。
- 規約による拒否と未決の裁定の停止を区別する記録は、照会の結果の `status` の語彙だけを用意しました（規約による拒否は、続行規約がないので起こらない）。

`engine.py`・`resolution/` にモードの名前・カード ID による分岐は加えていません（`engine.py` に加えたのは、入口の確かめ 1 つと準備の照会 2 つ）。

## 9. 今の挙動との比べ

基点の木（`0a3ee99`。`tools/engine_lockstep.py tree` で展開。版 0.141.0）と、この版の木（版 0.142.0）を同じ入力で走らせました。

**事前に列挙した、許す差**（これ以外の差は意図しない差として調べる）:

1. 書き出しの形式 35 の最上位の `convention_set`・`engine_version`（形式 35 は基点にない。基点の最新の形式は 34）
2. 観測の最上位の `convention_set`
3. エンジンの版の文字列（0.141.0 → 0.142.0）

ログ・乱数・選択肢・拒否のコードと理由の文・形式 1〜34 の書き出しは、差を許しません。項目の広い除外・ログの削除はしていません。

| 比べ | 範囲 | 結果 |
|---|---|---|
| 生の比べ（lockstep。1 歩ごとに受け付けたか・拒否のコード・理由の文の指紋・形式 9 の書き出しの指紋） | `--corpus all --seeds 20 --stress-seeds 10`: 対戦 760・136,716 歩 | 食い違い 0・許した差 0 |
| 同（1 歩ごとに pickle で保存・復元してから続ける） | `--corpus natural --seeds 10 --save-every 7`: 対戦 230・27,538 歩 | 食い違い 0 |
| 生の比べ（最新の形式の書き出しの全体の sha256） | 下の 36 対戦・2,293 歩 | 2,289 歩で違う（どの歩も、許す差 1 の項目と形式の番号がある。違わない 4 歩は拒否の歩で書き出しを記録していない） |
| 識別だけを対応付けた比べ（最新の形式の書き出しから `convention_set`・`engine_version` だけを除き、`format_version` を 34 にそろえる） | ピカチュウ・交換・コイルの 3 組 × seed 0〜11（36 対戦・2,293 歩。各歩でプレイヤー 0・1・観戦者の観測も） | 違う歩 0 |
| 行動・選択肢・乱数・カードの移動・公開の情報・結果 | 同（コマンド・拒否のコード・乱数の指紋・ログの長さ・段階・決定の選べるもの・結果、書き出しのゾーン、観測から `convention_set` だけを除いたもの） | 違う歩 0 |
| 旧バッチ | `tools/existing_effect_games.py` の全 108 バッチ（seed 0〜3。4,356 局）。基点の記録は共通規約の設計案の調査の記録（`C:/dev/kyuura-engine-play-policy-evidence/batches`。木 `8164194` で、エンジン・道具は `0a3ee99` と同じ） | 108 バッチすべて、時間の項目を除いて同じ。終了コード 0 でないのは基点と同じ v0.132（予期しない拒否の 2 局） |
| サドン・デス | `tools/sudden_death_games.py` の magnemite・swap（seed 0〜199。400 局） | どちらも時間の項目を除いて同じ |

対戦上の差（識別の情報以外の差）は見つかりませんでした。

道具の記録: lockstep の記録と比べの出力、対応付けた比べの道具（`mapped_compare.py`）、旧バッチの出力は作業用の領域に置き、リポジトリには入れていません（停止の方針の台帳の証拠の root
`C:/dev/kyuura-engine-verification` の下にも置いていない。台帳が証拠として読むため）。

## 10. 未実装の部分と次の段階

- 続行規約はありません（S2a の 5 件 PC-SETUP-MULLIGAN-COUNT・PC-SETUP-PLAY-AS-POKEMON・PC-CHECK-SIDE-ORDER・PC-COIN-COUNT-SHORT・PC-CHECK-KO-POINT を含め、どれも採用していない）。
- プレイ用の集合・開発用の集合はありません。完全性の判定（`play_complete`）は未実装です。
- コマンドの拒否で止める場面の照会は未接続です（8 章）。
- 規約を当てはめたことのログ・厳密とプレイ用の比べの道具は、続行規約ができてから作ります。
- 次に利用者の判断が要るもの: S2a の規約の内容（DEC-MULLIGAN-COMPENSATION・DEC-PLAY-AS-POKEMON・DEC-SLEEP-COIN-ORDER など）と、DEC-PLAY-CONFIG-INCOMPLETE-START の残り
  （不足のある構成で始められるか）、DEC-CONVENTION-GRANULARITY・DEC-CONVENTION-CONFLICTS（上書きの扱い）。

## 11. 検証

**全体のテスト**（[testing](testing.md) の手順。1 並列・モジュールごとに 1 プロセス。Python 3.14.6。`PYTHONUTF8=1 PYTHONHASHSEED=0`）:

| 項目 | 結果 |
|---|---|
| モジュール | 261（完了 261） |
| テスト | 7,502 |
| 失敗・エラー | 0・0 |
| 飛ばし | 1（`test_cross_version_compatibility` の大きな比較。`KYUURA_COMPAT_BASE` を設定したときだけ） |
| 終了コード 0 でないモジュール・時間切れ | なし・なし |
| 実行の前後の木の指紋（追跡するファイル 350 の内容と道） | 前後で同じ（`33555e00…0a17e9`） |

全体の実行とは別に、途中で次を走らせました（全体の総数には数えない）: 修正の前の探索の並列の実行（261 モジュール・7,497 テスト。失敗 2 は
`test_sudden_death_v0_134` の形式の範囲と `test_preset_decks_v0_20` の版で、どちらも直した）、直したあとの 3 モジュール
（`test_sudden_death_v0_134`・`test_preset_decks_v0_20`・`test_conventions_v0_142`。69 テスト OK）。

**台帳・データ・静的検査**（どれも終了コードを直接見た。パイプの末尾のコマンドの終了コードではない）:

- `scripts/build_stop_policy_classification.py --check`・`scripts/build_play_policy_family_plan.py --check`・`scripts/build_convention_records.py --check`: 問題 0
- `check_card_sources`・`check_research_links`・`check_implementation_assumptions --check`・`check_normalization_revalidation --check`: 終了コード 0
- 既存のデータ・固定デッキ・参照データ（`kyuura_engine/data`・`tests/fixtures`）の差は、新しい `convention_records.json` だけ
- ruff: 基点と同じ版・同じ設定で、指摘の件数と種類が基点と同じ（492）。新しい抑制（`noqa`）はない
- kyuura（`C:/dev/kyuura`）は変更していない

**S1 の完了の条件**: 満たしたと判断します。新しい対戦は既定で `CS-KYUURA-CURRENT@1` を持ち、識別・版・照合値・開始の前の拒否・
対戦中の不変・延長戦の引き継ぎ・保存と書き出し・旧い状態の扱い・未決の場面の照会（どれも「続行規約なし」）が動き、対戦上の挙動は変わっていません（9 章）。
ただし、基礎の規則だけの厳密な集合は作っていません（DEC-BASELINE-NONUSER が未決で、利用者の指定以外の基礎の規則を基礎集合に入れるかが決まっていないため。
今の挙動の記録は `CB-IMPLEMENTATION-ASSUMPTIONS` の承認されていない記録として持つ）。

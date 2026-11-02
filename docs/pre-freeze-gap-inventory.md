# 機能凍結前の未対応処理総合棚卸し

## 1. 基点・範囲・結論

基点は公開main `90c5439cbca2907b68254547d671de1e05b97c0d`（v0.133マージ）。最終リリース `298f08d603c1f763fc45a97fc306291d8b95abb0` と木が同じことを確認した。元のローカル作業ブランチはこの環境にはなく、専用cloneで公開済みの現行コードを固定した。未公開変更は監査対象外。監査日時はJSONの `baseline.generated_at_jst` を参照。

通常対戦対象1,374枚の登録完了は、全ての合法操作・全ての裁定への対応完了ではない。サドン・デスの継続未実装、回答拒否による情報漏れ、探索予算、コピー・反応の一部制限が残る。今回、エンジン・既存テスト・参照データを変更していない。コミット・push・PR作成もしていない。

この棚卸しは**静的な全件抽出と、重要候補の限定的な動作確認**である。全合法盤面の到達性証明や全分岐のカバレッジ測定ではない。unknownを到達不能と読み替えない。600個の内部ガードを600個の不具合と数えない。

成果物：[構造化台帳](pre-freeze-gap-inventory.json)、[修正計画](pre-freeze-remediation-plan.md)。JSONには実行結果・再現プローブ・ソースSHA256を含む。

## 2. 集計と分類基準

|対象|件数|意味|
|---|---:|---|
|研究対応表の停止コード|316|全件が現行Pythonの定義または記号参照に存在。全件C。ただし公式資料の不存在を再調査した数ではない|
|表外の現行プレフィックスコード|37|UNSUPPORTED 36件＋汎用UNRESOLVED_RULING 1件。対応漏れと一律に判定しない|
|現行プレフィックスコード計|353|文字列定義・単純別名を解決した静的集合|
|エンジンに定義・参照を見つけないコード|8|テスト・道具専用または過去の残骸候補。実行不能の全体証明ではない|
|非プレフィックスの重要な停止|1|SUDDEN_DEATH_NOT_IMPLEMENTED。上の353件とは別|
|内部例外ガード|600|RuntimeError・NotImplementedError・AssertionError・StateIntegrityErrorのコンストラクタ箇所。到達性は個別unknown|
|採用済み規約・仮定|16|利用者指定11件、エンジン簡略化2件、実装上の仮定3件。未実装残件ではない|
|コードなし研究論点|5|過去のreachable=falseを現行の証明に流用しない|

分類：A=機能不足、B=技術的制限、C=研究上の未裁定、D=明示的独自規約で処理済み、E=その他の停止・内部ガード・対象外・履歴上修正済み。P0=合法な状態へ到達したあと進行が必ず止まる重大不足、P1=通常対戦の結果・合法操作への重要な影響、P2=条件付き／到達性unknownの要調査、P3=対象外・採用済み・過去項目。

P0は「全ての対戦が必ず止まる」という意味ではなく、記載した条件に到達すると手の選び直しでは進めないという条件付き評価。P1の探索fail-openは未再現の修正候補で、確定不具合とは分ける。各優先度の確度はJSONのpriority_basisとreachabilityを読む。

台帳は停止コード単位と構造上の問題単位を併記している。LIMIT項目と対応する停止コードは同じ問題を別の角度から記録しており、単純合算を「独立した不具合数」としない。

|分類|台帳レコード数|
|---|---:|
|A|38|
|B|14|
|C|321|
|D|16|
|E|615|

|優先度|レコード数|
|---|---:|
|P0|1|
|P1|9|
|P2|966|
|P3|28|

## 3. P0・P1の修正候補

|優先度・分類|項目|到達条件・影響|根拠と処置|
|---|---|---|---|
|P0・A|サドン・デスの開始未実装|両者同時勝利等でSUDDEN_DEATHへ進むと、通常コマンドは全て拒否。延長戦を開始できない|[kyuura_engine/engine.py:787](../kyuura_engine/engine.py#L787)、[tests/test_simultaneous_ko.py:223](../tests/test_simultaneous_ko.py#L223)。既存テストで再現。まず延長戦の原典規定を確認し、専用開始経路を設計|
|P1・A|クイズその2・その3・性格判定の回答拒否オラクル|同じ公開観測・同じ「はたく」ヒントで、ミニリュウを伏せた場合だけ「ミニリュウ」が受理される。スリープなら同じ回答がFU3で拒否|[kyuura_engine/effects.py:22119](../kyuura_engine/effects.py#L22119)。3種類それぞれの2盤面比較で再現。その2と性格判定はeffects.py:31753・31817の共通処理。回答前に全分岐を安全に判断する方式へ改善|
|P1・B|代替回答探索256件でfail-open|上限時にTrue／Noneを返し、受理できる続きがあると仮定。答えが全て拒否になる決定を残す可能性|[kyuura_engine/engine.py:940](../kyuura_engine/engine.py#L940)、[kyuura_engine/engine.py:1078](../kyuura_engine/engine.py#L1078)、[kyuura_engine/engine.py:1121](../kyuura_engine/engine.py#L1121)。正常な現行カードからの詰まり再現はunknown。最初に境界再現と証明を行う|
|P1・B|先読み4096葉の合法ワザ拒否|だいらんとうは12匹で4095枝、こんらんが加わると上限超過|[tests/test_hand_bench_attack_conditions_v0_121.py:419](../tests/test_hand_bench_attack_conditions_v0_121.py#L419)。上限を無条件に増やさず、相関・同値類による削減を検討|
|P1・C|準備の切り直し補償|両者の切り直し後、片側だけ追加で切り直すと準備HALTED|[kyuura_engine/engine.py:462](../kyuura_engine/engine.py#L462)。通常のデッキでも発生。研究の回答または明示的な採用仕様が先。停止を削除しない|
|P1・C|両側ねむりのチェック順|両側がねむりのポケモンチェックでHALTED|[kyuura_engine/procedures.py:936](../kyuura_engine/procedures.py#L936)。既存境界テストと過去版の対戦報告あり。順序を推測で固定しない|
|P1・C|錯乱ジムとちえくらべ|両方が関係するトレーナー使用がMG1で拒否|[kyuura_engine/effects.py:49060](../kyuura_engine/effects.py#L49060)。v0.132の正式対戦2局が道具上unexpected_rejectionだったが、内部エラーではない。裁定／仕様を別途決める|

P0/P1のうちC分類は「エンジンを直せば済む不足」ではない。研究または利用者指定の決定を依存条件とする。

## 4. 重要なP2・採用済み仕様・履歴の再評価

- コピーした特殊能力、返すダメージ内の決定、ワザ中の付与反応、にげる中のおいうちにはA分類の明示的な拒否がある。カード登録数とは別に能力・経路の対応行列が必要。
- 図鑑番号なし225枚は身長クイズで選ぶと拒否。公式図鑑の種族参照が揃っていることと、カードの種族対応が揃うことは別。原文の欠けを推測補完しない。
- DU1/TW1の途中停止は終端で再開APIがない。根の枚数不足裁定Cと、再開機構Eを分離。ひかるバンギラスのmin処理を他へ流用しない。
- プレゼントの回復・ダメージの相関を見ない止めすぎは既知の候補。現行盤面の独立再現はunknown。
- v0.113で発見されたESP後のからめとるのマヒ省略は、v0.114でswitched_resultsを引き継ぐ修正がある。現行の未修正不具合として重複計上しない。
- 唯一のpassはlasting(effect)の無期限効果の期限チェックを省く意図した処理。空の未実装ハンドラではない。
- _bench_limit_or_defaultはRuntimeErrorを通常ベンチ上限へ代替する。壊れた状態の不変条件検査用だが、正常経路を隠すかはunknown。
- v0.132の辞退枝の事前検査により、阻止に成功する枝があっても使用全体を拒否する場合がある。テストは合成レジストリ。全ての実カード経路で同じだとは断定しない。

### 4.1 D分類：凍結時に保持する仕様

利用者指定は誕生日・発話省略4対象、公式図鑑参照1対象、交換所有権・ちえくらべ・ひかるバンギラス2ワザの規則4対象、ナッシーの名前2対象。別にキョウのベトベトンのエンジン簡略化2対象と実装上の仮定3件を記録。公式の論点を解決済みにしない。

ガルーラルール等の専用ルールと目録専用の45項目は通常対戦の対象外。新たな未登録カードとして戻さない。

## 5. 停止と内部例外の制御経路

|経路|入力・結果|確認箇所|
|---|---|---|
|通常の拒否|IllegalActionError／UnsupportedError。複製に実行するため入力状態・乱数・ログを変更しない|[kyuura_engine/engine.py:777](../kyuura_engine/engine.py#L777)|
|準備・ポケモンチェックのHALTED|Halt理由を持つ状態を返す。次の操作は理由コードで拒否|[kyuura_engine/engine.py:442](../kyuura_engine/engine.py#L442)、[kyuura_engine/procedures.py:936](../kyuura_engine/procedures.py#L936)|
|答えのない決定のHALTED化|回答・昇格・サイド等の全ての続きが進めないと元の状態を停止|[kyuura_engine/engine.py:814](../kyuura_engine/engine.py#L814)、[kyuura_engine/engine.py:1108](../kyuura_engine/engine.py#L1108)|
|DeferredShortage|指定された数量要素だけを_apply_onceで捕捉。コイン等を保持した終端HALTED|[kyuura_engine/interruption.py:1](../kyuura_engine/interruption.py#L1)、[kyuura_engine/engine.py:809](../kyuura_engine/engine.py#L809)|
|内部エラー|RuntimeError・不変条件違反等。未対応や未裁定へ一括変換しない|JSONのinternal_guardとall_raise_statementsを参照|
|サドン・デス|HALTEDとは別の終端。次のコマンドはSUDDEN_DEATH_NOT_IMPLEMENTED|[kyuura_engine/engine.py:787](../kyuura_engine/engine.py#L787)|

ASTで全raise文1,844箇所、UnsupportedErrorコンストラクタ347箇所、HALTED代入／Halt生成／停止ヘルパー等38箇所、exceptハンドラ145箇所を収録した。複数箇所は同じ経路の前後であり、別問題の数ではない。全raiseと動的コード形成もJSONに保存した。

Noneを返す756箇所は正常な問い合わせも含む一次調査候補。全てを未対応スキップと判定しない。関係するフォールバックを上で個別に分類し、残りの意味・合法到達性は未確認として残す。600内部ガードの全分岐は未実行。PythonのKeyError・IndexErrorが意図せず起きる可能性を全合法状態で否定したものではない。

## 6. 技術上限

|上限|値|超過時・影響|
|---|---:|---|
|先読みの葉|4096|旧検査のVERIFIEDと未知機能の有無を確認し、安全な旧経路だけフォールバック。ほかは拒否|
|裏カードの複数割当試行|512|2枚以上の割当で超過したらUNSUPPORTED_SECRET_PLAN_IDENTITIES。1枚時の動的予算超過は内部不具合ガード|
|代替回答・継続探索|256|一部は超過時に続行可能と仮定。独立した要調査候補|
|色の読み方の組|256|UNSUPPORTED_COLOR_READINGS_LIMIT|
|くろこげのコイン比較|6枚|全結果比較を止めHALTED。ルール上の個数上限ではない|
|問い合わせを変えるきのみ|3個|順序の組合せを拒否。通常のきのみ総数上限ではない|
|値回答の最大整数|2^53−1|JSONで値を落とさないための表現制約。身長の正解集合による候補制限ではない|
|実際のうらまでコイン|上限なし|乱数を1枚ずつ消費し全ログ保持。資源枚数で打ち切らない。時間・メモリのハード上限なし|

固定の5匹ベンチ・60枚デッキ等のゲーム規定は、技術上限と混同しない。ストレス道具のstepsは検証予算で、エンジンの対戦ルールではない。

## 7. 研究対応表

固定研究基準は `71d1728938fb4c8fefde9b82779cdef74beb612d`。stop_codes 316件とengine_unresolved_rulings 317件は別の集計。コードなしで数える論点があり、差を欠落コードと断定しない。5件のコードなし論点、17件の分類差、個別事例、Z23等のsubcasesもJSONへ保持した。

316件のkyuura_dispositionはissue 142、not_in_kyuura 134、issue_not_in_index 32、out_of_scope 8。out_of_scopeは研究の取り込み分類であり、現在のカードが通常対戦対象外という意味ではない。not_in_kyuuraも、現在最新のkyuuraに記録がないことの証明ではなく固定基準での状態。

表外のUNSUPPORTEDが36件あることは意図的な区別であり、全てをUQへ追加すべきという結論ではない。汎用UNRESOLVED_RULINGはE分類にした。

check_research_linksは固定基準との一致に成功。既存の古いローカルkyuura cloneでは固定コミットがなく最初の実行は失敗したため、読み取り用の新規bare cloneを用意し、その固定オブジェクトから再実行した。元のkyuuraリポジトリは変更していない。

## 8. テスト・ストレスの確認と限界

本監査で既存テスト計53件を実行し全て成功。初回6選定は49件、追加でだいらんとうの先読み上限とESPの入れ替え結果の引き継ぎの4件を実行した。全体テスト・全変異試験・全旧バッチは再実行していない。

|選定テスト|件数|結果|
|---|---:|---|
|tests.test_simultaneous_ko.WinTableTest|10|exit 0|
|tests.test_preflight_v0_15c.LimitTest|5|exit 0|
|tests.test_unresolved_boundaries_v0_4e|23|exit 0|
|tests.test_blaines_quiz_heights_v0_129.TrainerPathTest|2|exit 0|
|tests.test_slowking_mind_games_v0_132.DeclineLookaheadTest|1|exit 0|
|tests.test_deferred_shortage_user_promos_v0_127.FoundationTest|8|exit 0|
|だいらんとう上限境界＋EspSwitchContinuationTest|4|exit 0|

4局の短いストレス（venusaur・haunter各seed0〜1、各120手）はaccepted 233、rejected_illegal 233、rejected_unresolved 14、serialization_audits 10、failures 0。4局とも最終phaseはmainであり、完走4局とは書かない。未裁定の拒否はとうめい10回、ベンチなしのいれかえ4回。全カード・全停止コードのストレス証明ではない。

クイズの漏れは、ミニリュウ／スリープを伏せた2盤面で相手の公開観測が完全一致することを確認。同じ「ミニリュウ」という回答の受理・拒否が逆転した。その2でもポケモン／トレーナー、性格判定でもわるい／通常の進化カードの2盤面で同じ現象を確認した。3つのプローブのコードと出力をJSONに保存した。

テストでコード文字列が見つかることは動作検証の証拠ではない。一覧の期待にあるだけのものを含む。逆に文字列が見つからなくても、定数や間接経路で試されている可能性がある。静的言及なしは次の8件で、未テストと断定せず追加確認対象にする：

- `UNSUPPORTED_COLOR_READINGS_LIMIT`
- `UNSUPPORTED_DAMAGE_REDUCTION_DECISION`
- `UNSUPPORTED_ENERGY_DRAIN_DECISION`
- `UNSUPPORTED_ENERGY_REACTION_DURING_ATTACK`
- `UNSUPPORTED_LEGACY_PREFLIGHT`
- `UNSUPPORTED_MAX_HP_DROP_DURING_ATTACK`
- `UNSUPPORTED_MIRACLE_ENERGY_DURING_EFFECT`
- `UNSUPPORTED_POKEMON_CHECK_CHAR_COINS`

v0.133の既存報告は247モジュール7208件で失敗2、その後3モジュール82件成功。最後の追加テストで7209件になるが、その全体通過を本監査で確認したわけではない。

## 9. 表外の未対応コード（全36件）

到達性は明示した実行証拠以外unknown。関連カードの完全逆引きがない項目も、無関係・到達不能としない。詳細な発生箇所・条件・テスト候補はJSONを参照。

|コード|分類・優先度|条件・不足|主な実装箇所|
|---|---|---|---|
|`UNSUPPORTED_ACTION`|A・P2|APIが実装しないコマンド型。登録カード未実装0とは別のAPIガード。|[kyuura_engine/engine.py:780](../kyuura_engine/engine.py#L780)|
|`UNSUPPORTED_ATTACH_TRIGGER_ORDER`|A・P2|手札以外からの付与で反応の順番を処理できない（エナジーショック等とほのおでかいふく）。AT1という研究上の範囲の問いとは別。|[kyuura_engine/effects.py:8483](../kyuura_engine/effects.py#L8483)|
|`UNSUPPORTED_ATTACK`|A・P2|登録チェック不適合、旧契約経路、または要素ビルダーのないワザ。通常登録とテスト用レジストリを区別して調査。|[kyuura_engine/checks.py:135](../kyuura_engine/checks.py#L135)|
|`UNSUPPORTED_ATTACK_SOURCE_LEFT_PLAY`|A・P2|返すダメージ等の発生源が場を離れ、供給元のダメージ計算情報を復元できない。|[kyuura_engine/resolution/kernel.py:557](../kyuura_engine/resolution/kernel.py#L557)|
|`UNSUPPORTED_BENCH_GUARD_OUTSIDE_ATTACK`|A・P2|控えの防護をワザ外のダメージに適用する決定経路の不足。|[kyuura_engine/effects.py:22399](../kyuura_engine/effects.py#L22399)|
|`UNSUPPORTED_BERRY_ORDER_LIMIT`|B・P2|他の問い合わせを変えるきのみが3個を超えると順序比較を拒否。|[kyuura_engine/procedures.py:541](../kyuura_engine/procedures.py#L541)|
|`UNSUPPORTED_COLOR_READINGS_LIMIT`|B・P2|色の解釈の組が256を超えると支払い・読み方の探索を拒否。|[kyuura_engine/effects.py:10650](../kyuura_engine/effects.py#L10650)|
|`UNSUPPORTED_COPIED_ATTACK`|A・P2|copy_problemが返す実装上の非対応。HC9などの原典未解決とは区別する。|[kyuura_engine/resolution/programs.py:3958](../kyuura_engine/resolution/programs.py#L3958)|
|`UNSUPPORTED_DAMAGE_OPTION_ELEMENT`|A・P2|シェルアーマー等、返す効果のダメージの中で任意の減算を質問できない。|[kyuura_engine/resolution/questions.py:545](../kyuura_engine/resolution/questions.py#L545)|
|`UNSUPPORTED_DAMAGE_REDUCTION_DECISION`|A・P2|対象経路でダメージ減少の決定を待てない。|[kyuura_engine/resolution/questions.py:375](../kyuura_engine/resolution/questions.py#L375)|
|`UNSUPPORTED_DAMAGE_STEP_ORDER`|A・P2|同じ計算段階の非可換効果の順序決定を出せない経路。順番のルールそのものの欠如ではない。|[kyuura_engine/resolution/questions.py:116](../kyuura_engine/resolution/questions.py#L116)|
|`UNSUPPORTED_ENERGY_DRAIN_DECISION`|A・P2|エネルギードレインの決定を返す効果等の経路で処理できない。|[kyuura_engine/resolution/questions.py:403](../kyuura_engine/resolution/questions.py#L403)|
|`UNSUPPORTED_ENERGY_REACTION_DURING_ATTACK`|A・P2|ワザ途中のエネルギー付与で、かんでん・いなびかり等の続きの決定を扱えない。|[kyuura_engine/resolution/questions.py:474](../kyuura_engine/resolution/questions.py#L474)|
|`UNSUPPORTED_ESP_CONTINUATION`|A・P2|ESPをまたぐ未分類の前段結果。からめとるの具体的不具合はv0.114で修正済み。現行の新たな正常到達はunknown。|[kyuura_engine/resolution/programs.py:396](../kyuura_engine/resolution/programs.py#L396)|
|`UNSUPPORTED_EVOLUTION`|A・P2|登録・データ欠けの進化カードに対するガード。通常対象全登録後も不正レジストリ等と分ける。|[kyuura_engine/effects.py:6950](../kyuura_engine/effects.py#L6950)|
|`UNSUPPORTED_EVOLUTION_LINEAGE`|A・P2|進化系統データの不足。カード登録済みでも lineage の完全性と同じではない。|[kyuura_engine/effects.py:6952](../kyuura_engine/effects.py#L6952)|
|`UNSUPPORTED_FACE_UP_DECK_PATH`|A・P2|フラッシュ後の山札変化がFU1〜6の分類外。黙って裏向き扱いにしない。|[kyuura_engine/faceup.py:64](../kyuura_engine/faceup.py#L64)|
|`UNSUPPORTED_HISTORY_DAMAGE_PLACE_UNKNOWN`|A・P2|古い保存記録に受けた場所の情報がなく、バトル場でのダメージを計算できない。|[kyuura_engine/history.py:269](../kyuura_engine/history.py#L269)|
|`UNSUPPORTED_HISTORY_TURN_RECORD_MISSING`|A・P2|コピー等で必要な番の履歴がない。空値や0で代用しない。|[kyuura_engine/resolution/questions.py:500](../kyuura_engine/resolution/questions.py#L500)|
|`UNSUPPORTED_LEGACY_PREFLIGHT`|A・P2|旧v0.13の検査が知らない盤面に旧契約を使用できない。|[kyuura_engine/resolution/flow.py:176](../kyuura_engine/resolution/flow.py#L176)|
|`UNSUPPORTED_LEGEND_BODY_PENDING_DISCARD`|A・P2|でんせつのからだによるエネルギートラッシュを決定待ち状態で処理できない。|[kyuura_engine/effects.py:44298](../kyuura_engine/effects.py#L44298)|
|`UNSUPPORTED_MAX_HP_DROP_DURING_ATTACK`|A・P2|ワザの途中の決定中に最大HPがダメージ以下へ下がる状態を表せない。古い今のカードでは起こらないという記述は再証明していない。|[kyuura_engine/effects.py:14350](../kyuura_engine/effects.py#L14350)|
|`UNSUPPORTED_MIRACLE_ENERGY_DURING_EFFECT`|A・P2|決定中にミラクルエネルギーを付けられる条件を失ったときの自動トラッシュを扱えない。|[kyuura_engine/effects.py:34749](../kyuura_engine/effects.py#L34749)|
|`UNSUPPORTED_MIRROR_MOVE_ATTACK`|A・P2|オウムがえしで再現できないワザの型。|[kyuura_engine/resolution/questions.py:354](../kyuura_engine/resolution/questions.py#L354)|
|`UNSUPPORTED_MIRROR_MOVE_EFFECT`|A・P2|オウムがえしで返せない非ダメージ効果。|[kyuura_engine/resolution/questions.py:352](../kyuura_engine/resolution/questions.py#L352)|
|`UNSUPPORTED_POKEMON_CHECK_CHAR_COINS`|B・P2|くろこげコイン6枚超の全結果確認を行わずHALTEDにする。|[kyuura_engine/procedures.py:363](../kyuura_engine/procedures.py#L363)|
|`UNSUPPORTED_POKEMON_POWER`|A・P2|未登録・チェック不適合の特殊能力ガード。コピー時の不足とは別。|[kyuura_engine/engine.py:2225](../kyuura_engine/engine.py#L2225)|
|`UNSUPPORTED_PREFLIGHT_LIMIT`|B・P1|先読み4096葉を超え、旧検査への安全なフォールバックもできないワザを拒否。 だいらんとうの12匹4095枝は収まるが、こんらんが加わると超える。|[kyuura_engine/resolution/flow.py:168](../kyuura_engine/resolution/flow.py#L168)|
|`UNSUPPORTED_PURSUIT_DAMAGE_REACTION`|A・P2|にげる中のおいうちで、ダメージ順序・防護・きぜつ反応の決定等を扱えない。|[kyuura_engine/resolution/kernel.py:2749](../kyuura_engine/resolution/kernel.py#L2749)|
|`UNSUPPORTED_QUIZ_HEIGHT_NOT_AVAILABLE`|A・P2|図鑑番号に対応する単一の身長参照がない。欠け・複数種等を推測しない。|[kyuura_engine/effects.py:48560](../kyuura_engine/effects.py#L48560)|
|`UNSUPPORTED_QUIZ_HEIGHT_WITHOUT_DEX`|A・P2|図鑑番号のないカードのクイズ出題を受け付けない。|[kyuura_engine/effects.py:48555](../kyuura_engine/effects.py#L48555)|
|`UNSUPPORTED_SECRET_PLAN_IDENTITIES`|B・P2|2枚以上の裏のカードの公開情報だけによる試行が512を超える。1枚の動的予算と区別。|[kyuura_engine/engine.py:748](../kyuura_engine/engine.py#L748)|
|`UNSUPPORTED_SECRET_PLAN_LOST_TARGET`|A・P2|裏のカードを指定して公開した結果、カードが場に残らず後続処理を続けられない。|[kyuura_engine/zones.py:155](../kyuura_engine/zones.py#L155)|
|`UNSUPPORTED_TRAINER`|A・P2|未登録・チェック不適合のトレーナーガード。|[kyuura_engine/engine.py:1841](../kyuura_engine/engine.py#L1841)|
|`UNSUPPORTED_TRANSFORM_COPIED_POWER`|A・P2|変身で写した能力の一部（ワザ供給等）の未対応。能力を無効化して続けるのではなく拒否。|[kyuura_engine/effects.py:19822](../kyuura_engine/effects.py#L19822)|
|`UNSUPPORTED_UNBOUNDED_COIN_PREFLIGHT`|A・P2|無限のコイン結果を有限の同値類へ安全にまとめられない。現行合法経路の有無はunknown。|[kyuura_engine/resolution/questions.py:357](../kyuura_engine/resolution/questions.py#L357)|

## 10. 研究停止コード全316件の索引

以下のテスト数は静的参照数であり、実行数やカバレッジ率ではない。関連カード・到達条件・reason定数・研究の原記録はJSONの各レコードを参照。P2・unknownを既定とし、到達不能と判断しない。

|コード|優先度|裁定ID|kyuura論点・状態|実装参照|テスト静的参照数|
|---|---|---|---|---|---:|
|`UNRESOLVED_ALL_CLEAR_ATTACK_SOURCE`|P2|ZC2|not_in_kyuura|[kyuura_engine/resolution/questions.py:221](../kyuura_engine/resolution/questions.py#L221)|5|
|`UNRESOLVED_ALL_CLEAR_FOSSIL_IN_PLAY`|P2|ZC3|not_in_kyuura|[kyuura_engine/resolution/questions.py:224](../kyuura_engine/resolution/questions.py#L224)|6|
|`UNRESOLVED_ALL_CLEAR_OTHER_EFFECTS`|P2|ZC1|not_in_kyuura|[kyuura_engine/resolution/questions.py:217](../kyuura_engine/resolution/questions.py#L217)|6|
|`UNRESOLVED_ALL_PURPOSE_POWDER_WITHOUT_TARGET`|P2|BP1|not_in_kyuura|[kyuura_engine/effects.py:30802](../kyuura_engine/effects.py#L30802)|3|
|`UNRESOLVED_ATTACH_AFTER_POWER_ATTACH`|P2|R13|UQ-RAIN-DANCE-ATTACH-COUNT|[kyuura_engine/engine.py:1443](../kyuura_engine/engine.py#L1443)|19|
|`UNRESOLVED_ATTACH_BLOCK_SCOPE`|P2|CB1|UQ-ATTACH-BLOCK-SCOPE|[kyuura_engine/effects.py:19606](../kyuura_engine/effects.py#L19606)|5|
|`UNRESOLVED_ATTACH_FROM_DISCARD_ZERO`|P2|HC7|UQ-UP-TO-ZERO-CHOICE|[kyuura_engine/resolution/programs.py:3689](../kyuura_engine/resolution/programs.py#L3689)|9|
|`UNRESOLVED_ATTACH_TRIGGER_SCOPE`|P2|AT1|not_in_kyuura|[kyuura_engine/effects.py:8476](../kyuura_engine/effects.py#L8476)|7|
|`UNRESOLVED_ATTACK_CHECK_CONFUSION`|P2|AC6|UQ-ATTACK-PRE-DAMAGE-COIN-ORDER|[kyuura_engine/resolution/questions.py:120](../kyuura_engine/resolution/questions.py#L120)|10|
|`UNRESOLVED_ATTACK_DECK_TOP_SHORT`|P2|LT1|not_in_kyuura|[kyuura_engine/resolution/questions.py:400](../kyuura_engine/resolution/questions.py#L400)|5|
|`UNRESOLVED_ATTACK_HAND_BENCH_REACTION`|P2|HB1|not_in_kyuura|[kyuura_engine/effects.py:46774](../kyuura_engine/effects.py#L46774)|3|
|`UNRESOLVED_ATTACK_LOCK_SOURCE_RETURNED`|P2|SG1|UQ-ATTACK-LOCK-SOURCE-RETURNED|[kyuura_engine/effects.py:7316](../kyuura_engine/effects.py#L7316)|20|
|`UNRESOLVED_BABY_RULE_COIN_ORDER`|P2|BQ1|UQ-ATTACK-PRE-DAMAGE-COIN-ORDER|[kyuura_engine/resolution/questions.py:261](../kyuura_engine/resolution/questions.py#L261)|5|
|`UNRESOLVED_BALLOON_BERRY_FAILED_RETREAT`|P2|BB1|not_in_kyuura|[kyuura_engine/effects.py:32573](../kyuura_engine/effects.py#L32573)|4|
|`UNRESOLVED_BENCH_COIN_TRANSPARENCY_ORDER`|P2|TS1|UQ-TRANSPARENCY-COIN-ORDER|[kyuura_engine/resolution/questions.py:294](../kyuura_engine/resolution/questions.py#L294)|6|
|`UNRESOLVED_BENCH_DAMAGE_WEAKNESS_RESISTANCE`|P2|JS1|UQ-BENCH-DAMAGE-WEAKNESS-RESISTANCE|[kyuura_engine/resolution/questions.py:135](../kyuura_engine/resolution/questions.py#L135)|26|
|`UNRESOLVED_BENCH_GUARD_RECOMPUTE`|P2|BG1|UQ-REACTIVE-SWITCH-DURING-ATTACK|[kyuura_engine/effects.py:22197](../kyuura_engine/effects.py#L22197)|4|
|`UNRESOLVED_BENCH_GUARD_ZERO_DAMAGE_REACTION`|P2|BG2|UQ-REACTIVE-SWITCH-DURING-ATTACK|[kyuura_engine/effects.py:22202](../kyuura_engine/effects.py#L22202)|4|
|`UNRESOLVED_BENCH_TARGETS_ZERO_CHOICE`|P2|GS1|UQ-UP-TO-ZERO-CHOICE|[kyuura_engine/resolution/programs.py:5180](../kyuura_engine/resolution/programs.py#L5180)|16|
|`UNRESOLVED_BLAINES_QUIZ_WITHOUT_POKEMON`|P2|QZ1,QZ1|UQ-CARD-USE-WITHOUT-TARGET|[kyuura_engine/effects.py:21774](../kyuura_engine/effects.py#L21774)|12|
|`UNRESOLVED_BLAINE_SECOND_ATTACH`|P2|BL1|UQ-BLAINE-SECOND-ATTACH|[kyuura_engine/effects.py:19546](../kyuura_engine/effects.py#L19546)|4|
|`UNRESOLVED_BOLT_DURING_OWN_ATTACK`|P2|BT1|not_in_kyuura|[kyuura_engine/effects.py:35969](../kyuura_engine/effects.py#L35969)|3|
|`UNRESOLVED_BREEDER_ON_PLAY_AS_POKEMON`|P2|PF3|UQ-PLAY-AS-POKEMON|[kyuura_engine/effects.py:13481](../kyuura_engine/effects.py#L13481)|7|
|`UNRESOLVED_BUZZAP_COLOR`|P2|BZ3|UQ-BUZZAP-TARGET-AND-COLOR|[kyuura_engine/effects.py:14497](../kyuura_engine/effects.py#L14497)|3|
|`UNRESOLVED_BUZZAP_DISGUISED`|P2|BZ4|UQ-SHAPESHIFT-SCOPE|[kyuura_engine/effects.py:14503](../kyuura_engine/effects.py#L14503)|3|
|`UNRESOLVED_BUZZAP_ENERGY_CARD_TYPE`|P2|BZ2|UQ-SPECIAL-ENERGY-AS-TYPED-ENERGY|[kyuura_engine/effects.py:14491](../kyuura_engine/effects.py#L14491)|4|
|`UNRESOLVED_BUZZAP_OPPONENT_TARGET`|P2|BZ1|UQ-BUZZAP-TARGET-AND-COLOR|[kyuura_engine/effects.py:14485](../kyuura_engine/effects.py#L14485)|3|
|`UNRESOLVED_CALMING_AROMA_RETALIATION`|P2|CP1|UQ-CALMING-AROMA-RETALIATION|[kyuura_engine/resolution/questions.py:181](../kyuura_engine/resolution/questions.py#L181)|7|
|`UNRESOLVED_CELADON_GYM_WITHOUT_CONDITION`|P2|TG1|UQ-TARGET-WITHOUT-EFFECT|[kyuura_engine/effects.py:20838](../kyuura_engine/effects.py#L20838)|3|
|`UNRESOLVED_CHANGE_ABSENT_WEAKNESS_RESISTANCE`|P2|PG1|UQ-CHANGE-ABSENT-WEAKNESS-RESISTANCE|[kyuura_engine/effects.py:13972](../kyuura_engine/effects.py#L13972)|9|
|`UNRESOLVED_CHAOS_GYM_BORROWED_TURN`|P2|CH1,CH1|UQ-CHAOS-GYM-BORROWED-TURN|[kyuura_engine/effects.py:21599](../kyuura_engine/effects.py#L21599)|10|
|`UNRESOLVED_CHARITY_BELOW_ZERO`|P2|CA1|UQ-CHARITY-BELOW-ZERO|[kyuura_engine/resolution/questions.py:371](../kyuura_engine/resolution/questions.py#L371)|4|
|`UNRESOLVED_CHOSEN_ACTIVE_EXTRA_DAMAGE`|P2|SLD1|not_in_kyuura|[kyuura_engine/effects.py:43274](../kyuura_engine/effects.py#L43274)|5|
|`UNRESOLVED_CLAMPING_JAW_SOURCE_DEVOLVED`|P2|CJ1|not_in_kyuura|[kyuura_engine/effects.py:38667](../kyuura_engine/effects.py#L38667)|4|
|`UNRESOLVED_COLOR_CHANGED_ENERGY_CARD`|P2|CE3|not_in_kyuura|[kyuura_engine/effects.py:10436](../kyuura_engine/effects.py#L10436)|3|
|`UNRESOLVED_COLOR_EFFECT_CONTINUATION`|P2|CE1|not_in_kyuura|[kyuura_engine/effects.py:10416](../kyuura_engine/effects.py#L10416)|3|
|`UNRESOLVED_COLOR_MARKER_PRECEDENCE`|P2|CM1|not_in_kyuura|[kyuura_engine/effects.py:10430](../kyuura_engine/effects.py#L10430)|6|
|`UNRESOLVED_COLOR_REPLACEMENT_ORDER`|P2|CE2|not_in_kyuura|[kyuura_engine/effects.py:10423](../kyuura_engine/effects.py#L10423)|3|
|`UNRESOLVED_COMMAND_DAMAGE_SCOPE`|P2|MD1|not_in_kyuura|[kyuura_engine/effects.py:45337](../kyuura_engine/effects.py#L45337)|4|
|`UNRESOLVED_COMPUTER_SEARCH_EMPTY_DECK`|P2|CS6|UQ-COMPUTER-SEARCH-EMPTY-DECK|[kyuura_engine/effects.py:6573](../kyuura_engine/effects.py#L6573)|3|
|`UNRESOLVED_CONDUCTIVITY_MULTIPLE_SOURCES`|P2|CV1|UQ-SELF-EXCLUDING-POWER-COPIES|[kyuura_engine/effects.py:36106](../kyuura_engine/effects.py#L36106)|7|
|`UNRESOLVED_CONFUSION_DAMAGE_MODIFIERS`|P2|—|out_of_scope|[kyuura_engine/procedures.py:1090](../kyuura_engine/procedures.py#L1090)|32|
|`UNRESOLVED_COPIED_ATTACK`|P2|HC9|UQ-COPIED-ATTACK|[kyuura_engine/resolution/programs.py:4010](../kyuura_engine/resolution/programs.py#L4010)|17|
|`UNRESOLVED_COUNTERATTACK_DOUBLE_KNOCKOUT`|P2|C18,Z13,C18|UQ-COUNTERATTACK-DOUBLE-KO|[kyuura_engine/effects.py:1026](../kyuura_engine/effects.py#L1026)|55|
|`UNRESOLVED_COUNTER_TRANSFER_PROTECTED`|P2|CX1|UQ-COUNTER-TRANSFER-PROTECTED|[kyuura_engine/resolution/questions.py:144](../kyuura_engine/resolution/questions.py#L144)|11|
|`UNRESOLVED_DAMAGE_GUARD_OVERLAP`|P2|GO1|not_in_kyuura|[kyuura_engine/resolution/questions.py:512](../kyuura_engine/resolution/questions.py#L512)|8|
|`UNRESOLVED_DAMAGE_TRIGGER_TIMING`|P2|GK1|UQ-DAMAGE-TRIGGER-TIMING|[kyuura_engine/resolution/questions.py:139](../kyuura_engine/resolution/questions.py#L139)|9|
|`UNRESOLVED_DARKNESS_DAMAGE_RECEIVED_POWER`|P2|DE1|not_in_kyuura|[kyuura_engine/effects.py:10175](../kyuura_engine/effects.py#L10175)|8|
|`UNRESOLVED_DARK_PULSE_TIMING`|P2|DP1|UQ-DARK-PULSE-TIMING|[kyuura_engine/effects.py:47974](../kyuura_engine/effects.py#L47974)|3|
|`UNRESOLVED_DARK_WAVE_KNOCKED_OUT_POWER`|P2|DW3|not_in_kyuura|[kyuura_engine/effects.py:38510](../kyuura_engine/effects.py#L38510)|3|
|`UNRESOLVED_DARK_WAVE_NEW_POKEMON`|P2|DW1|not_in_kyuura|[kyuura_engine/effects.py:38499](../kyuura_engine/effects.py#L38499)|4|
|`UNRESOLVED_DARK_WAVE_PROTECTED_POKEMON`|P2|DW2|not_in_kyuura|[kyuura_engine/effects.py:38505](../kyuura_engine/effects.py#L38505)|4|
|`UNRESOLVED_DECK_TOP_SHORT`|P2|TOP1|not_in_kyuura|[kyuura_engine/effects.py:30785](../kyuura_engine/effects.py#L30785)|3|
|`UNRESOLVED_DESTINY_BOND_KNOCKOUT`|P2|HC2,HC2|UQ-DESTINY-BOND-KO|[kyuura_engine/resolution/questions.py:88](../kyuura_engine/resolution/questions.py#L88)|6|
|`UNRESOLVED_DEVOLUTION_INTERMEDIATE_KNOCKOUT`|P2|DV1|UQ-EVOLUTION-HP-BELOW-DAMAGE|[kyuura_engine/effects.py:16389](../kyuura_engine/effects.py#L16389)|7|
|`UNRESOLVED_DEVOLUTION_SPRAY_HYPER_WITHOUT_TARGET`|P2|HY1|not_in_kyuura|[kyuura_engine/effects.py:30793](../kyuura_engine/effects.py#L30793)|3|
|`UNRESOLVED_DEVOLUTION_SPRAY_WITHOUT_TARGET`|P2|DV4|UQ-CARD-USE-WITHOUT-TARGET|[kyuura_engine/effects.py:16375](../kyuura_engine/effects.py#L16375)|7|
|`UNRESOLVED_DEVOLUTION_TARGET_DISGUISED`|P2|DV5|UQ-SHAPESHIFT-SCOPE|[kyuura_engine/effects.py:16382](../kyuura_engine/effects.py#L16382)|9|
|`UNRESOLVED_DISCARDED_ENERGY_DAMAGE_BONUS`|P2|DK1|not_in_kyuura|[kyuura_engine/effects.py:46768](../kyuura_engine/effects.py#L46768)|3|
|`UNRESOLVED_DISCARD_ANY_NUMBER_ZERO`|P2|HC5,HC5,HC5|UQ-UP-TO-ZERO-CHOICE|[kyuura_engine/effects.py:17611](../kyuura_engine/effects.py#L17611)|1184|
|`UNRESOLVED_DISCARD_DECK_SHORT`|P2|HC6|UQ-STATED-COUNT-SHORT|[kyuura_engine/effects.py:34915](../kyuura_engine/effects.py#L34915)|24|
|`UNRESOLVED_DISCARD_ENERGY_TIMING`|P2|HC1|UQ-DISCARD-ENERGY-TIMING-CONFUSION|[kyuura_engine/resolution/questions.py:84](../kyuura_engine/resolution/questions.py#L84)|9|
|`UNRESOLVED_DISCARD_PROTECTED_COIN`|P2|AP1|not_in_kyuura|[kyuura_engine/resolution/questions.py:561](../kyuura_engine/resolution/questions.py#L561)|7|
|`UNRESOLVED_DISCARD_PROTECTED_POWER_USE`|P2|AP2|not_in_kyuura|[kyuura_engine/effects.py:46215](../kyuura_engine/effects.py#L46215)|7|
|`UNRESOLVED_DISCARD_UP_TO_ZERO`|P2|RKB1|not_in_kyuura|[kyuura_engine/resolution/programs.py:13811](../kyuura_engine/resolution/programs.py#L13811)|4|
|`UNRESOLVED_DOUBLED_DAMAGE_POWER_DAMAGE`|P2|DB1|not_in_kyuura|[kyuura_engine/effects.py:19965](../kyuura_engine/effects.py#L19965)|4|
|`UNRESOLVED_DRY_UP_WATER_ENERGY_SHORT`|P2|DU1|UQ-STATED-COUNT-SHORT|[kyuura_engine/effects.py:48255](../kyuura_engine/effects.py#L48255)|4|
|`UNRESOLVED_EFFECT_AFTER_NO_DAMAGE`|P2|Z23|UQ-EFFECT-AFTER-NO-DAMAGE|[kyuura_engine/effects.py:2321](../kyuura_engine/effects.py#L2321)|2023|
|`UNRESOLVED_ENERGY_BURN_TRANSFER`|P2|HC10|UQ-ENERGY-BURN-TRANSFER|[kyuura_engine/effects.py:9165](../kyuura_engine/effects.py#L9165)|8|
|`UNRESOLVED_ENERGY_DRAIN_ATTACKER_KNOCKED_OUT`|P2|DR8,DR8|UQ-ENERGY-DRAIN-ATTACKER-KO|[kyuura_engine/effects.py:22631](../kyuura_engine/effects.py#L22631)|4|
|`UNRESOLVED_ENERGY_DRAIN_NO_ENERGY`|P2|DR13,DR13|UQ-ENERGY-DRAIN-NO-ENERGY|[kyuura_engine/effects.py:22632](../kyuura_engine/effects.py#L22632)|2|
|`UNRESOLVED_ENERGY_REMOVAL_WITHOUT_TARGET`|P2|EM1|UQ-CARD-USE-WITHOUT-TARGET|[kyuura_engine/effects.py:18063](../kyuura_engine/effects.py#L18063)|5|
|`UNRESOLVED_ENERGY_RETRIEVAL_WITHOUT_TARGET`|P2|ER10|UQ-ENERGY-RETRIEVAL-WITHOUT-TARGET|[kyuura_engine/effects.py:6655](../kyuura_engine/effects.py#L6655)|9|
|`UNRESOLVED_ENERGY_RETRIEVAL_ZERO_CHOICE`|P2|ER9|UQ-ENERGY-RETRIEVAL-ZERO-CHOICE|[kyuura_engine/effects.py:6660](../kyuura_engine/effects.py#L6660)|5|
|`UNRESOLVED_ENERGY_STADIUM_WITHOUT_TARGET`|P2|EN1|not_in_kyuura|[kyuura_engine/effects.py:21054](../kyuura_engine/effects.py#L21054)|3|
|`UNRESOLVED_ENGAGE_EMPTY_HAND`|P2|EG1|not_in_kyuura|[kyuura_engine/effects.py:39562](../kyuura_engine/effects.py#L39562)|4|
|`UNRESOLVED_ENTRY_POWER_DURING_ATTACK`|P2|PW4|UQ-ENTRY-POWER-DURING-ATTACK|[kyuura_engine/resolution/questions.py:149](../kyuura_engine/resolution/questions.py#L149)|10|
|`UNRESOLVED_ESP_COPIED_ATTACK_COINS`|P2|EC1|not_in_kyuura|[kyuura_engine/effects.py:22424](../kyuura_engine/effects.py#L22424)|4|
|`UNRESOLVED_ESP_HOLDER_NOT_SABRINAS`|P2|ES3|UQ-ESP-REDO|[kyuura_engine/effects.py:22419](../kyuura_engine/effects.py#L22419)|11|
|`UNRESOLVED_ESP_LEFT_BEFORE_COIN`|P2|ES4|not_in_kyuura|[kyuura_engine/effects.py:44400](../kyuura_engine/effects.py#L44400)|5|
|`UNRESOLVED_ESP_MULTIPLE`|P2|ES2|UQ-ESP-REDO|[kyuura_engine/effects.py:22416](../kyuura_engine/effects.py#L22416)|6|
|`UNRESOLVED_ESP_OPPONENT_COIN_TOSS`|P2|ES1|UQ-ESP-REDO|[kyuura_engine/effects.py:22413](../kyuura_engine/effects.py#L22413)|4|
|`UNRESOLVED_EVADED_EFFECT_COIN`|P2|T19b,L5,L13|UQ-COIN-IN-NULLIFIED-ELEMENT|[kyuura_engine/effects.py:905](../kyuura_engine/effects.py#L905)|46|
|`UNRESOLVED_EVOLUTION_HP`|P2|—|UQ-EVOLUTION-HP-BELOW-DAMAGE|[kyuura_engine/effects.py:6899](../kyuura_engine/effects.py#L6899)|16|
|`UNRESOLVED_EVOLUTION_PERMISSION_FROM_DECK`|P2|GV1,GV1|UQ-EVOLUTION-PERMISSION-FROM-DECK|[kyuura_engine/effects.py:12429](../kyuura_engine/effects.py#L12429)|10|
|`UNRESOLVED_EVOLVE_AFTER_DEVOLUTION`|P2|DV2|UQ-DEVOLUTION-SAME-TURN|[kyuura_engine/effects.py:6898](../kyuura_engine/effects.py#L6898)|14|
|`UNRESOLVED_EXTRA_ENERGY_COLORLESS`|P2|HC4|UQ-EXTRA-ENERGY-COLORLESS|[kyuura_engine/resolution/questions.py:93](../kyuura_engine/resolution/questions.py#L93)|8|
|`UNRESOLVED_FACE_UP_DECK_CHECK`|P2|FU2|UQ-FLASH-FACE-UP-DECK|[kyuura_engine/engine.py:2466](../kyuura_engine/engine.py#L2466)|4|
|`UNRESOLVED_FACE_UP_DECK_HIDDEN_TAKE`|P2|FU3|UQ-FLASH-FACE-UP-DECK|[kyuura_engine/faceup.py:40](../kyuura_engine/faceup.py#L40)|11|
|`UNRESOLVED_FACE_UP_DECK_LOOK_RETURN`|P2|FU5|UQ-FLASH-FACE-UP-DECK|[kyuura_engine/effects.py:17978](../kyuura_engine/effects.py#L17978)|4|
|`UNRESOLVED_FACE_UP_DECK_MOVE`|P2|FU6|UQ-FLASH-FACE-UP-DECK|[kyuura_engine/effects.py:13777](../kyuura_engine/effects.py#L13777)|4|
|`UNRESOLVED_FACE_UP_DECK_PLACE_TOP`|P2|FU4|UQ-FLASH-FACE-UP-DECK|[kyuura_engine/effects.py:45588](../kyuura_engine/effects.py#L45588)|6|
|`UNRESOLVED_FERVOR_RAINBOW_ENERGY`|P2|FV1,FV1|not_in_kyuura|[kyuura_engine/effects.py:28995](../kyuura_engine/effects.py#L28995)|15|
|`UNRESOLVED_FLASH_DECK_SHORT`|P2|FU1|UQ-STATED-COUNT-SHORT|[kyuura_engine/effects.py:48191](../kyuura_engine/effects.py#L48191)|5|
|`UNRESOLVED_FLEE_DURING_OWN_ATTACK`|P2|FL1|UQ-REACTIVE-SWITCH-DURING-ATTACK|[kyuura_engine/effects.py:22192](../kyuura_engine/effects.py#L22192)|4|
|`UNRESOLVED_FOCUS_BAND_TIMING`|P2|FB1|not_in_kyuura|[kyuura_engine/effects.py:32612](../kyuura_engine/effects.py#L32612)|3|
|`UNRESOLVED_FOSSILIZE_WITHOUT_TARGET`|P2|FS1|not_in_kyuura|[kyuura_engine/effects.py:47251](../kyuura_engine/effects.py#L47251)|3|
|`UNRESOLVED_FOSSIL_EVOLVED_READING`|P2|FE3|not_in_kyuura|[kyuura_engine/effects.py:47226](../kyuura_engine/effects.py#L47226)|4|
|`UNRESOLVED_FOSSIL_GUIDE_WITHOUT_TARGET`|P2|GU1|not_in_kyuura|[kyuura_engine/effects.py:47247](../kyuura_engine/effects.py#L47247)|3|
|`UNRESOLVED_FUCHSIA_GYM_AFTER_REPLACEMENT`|P2|FG1|UQ-FUCHSIA-GYM-ONCE-PER-TURN|[kyuura_engine/effects.py:20887](../kyuura_engine/effects.py#L20887)|4|
|`UNRESOLVED_FUCHSIA_GYM_WITHOUT_TARGET`|P2|FG2|UQ-CARD-USE-WITHOUT-TARGET|[kyuura_engine/effects.py:20891](../kyuura_engine/effects.py#L20891)|3|
|`UNRESOLVED_FULL_HEAL_SCOPE`|P2|FH1|UQ-CARD-USE-WITHOUT-TARGET|[kyuura_engine/effects.py:18075](../kyuura_engine/effects.py#L18075)|5|
|`UNRESOLVED_FULL_HEAL_WITHOUT_CONDITION`|P2|FH2|not_in_kyuura|[kyuura_engine/effects.py:18513](../kyuura_engine/effects.py#L18513)|5|
|`UNRESOLVED_FULL_RECOVERY_COUNTERS`|P2|KR1|not_in_kyuura|[kyuura_engine/resolution/questions.py:203](../kyuura_engine/resolution/questions.py#L203)|6|
|`UNRESOLVED_GOOP_GAS_NEW_POKEMON`|P2|GG1|UQ-GOOP-GAS-NEW-POKEMON|[kyuura_engine/effects.py:19017](../kyuura_engine/effects.py#L19017)|12|
|`UNRESOLVED_GROUP_POWER_COIN_ORDER`|P2|XP1|not_in_kyuura|[kyuura_engine/effects.py:44962](../kyuura_engine/effects.py#L44962)|5|
|`UNRESOLVED_GROWL_NON_ATTACK_DAMAGE`|P2|GN1|UQ-GROWL-NON-ATTACK-DAMAGE|[kyuura_engine/effects.py:19960](../kyuura_engine/effects.py#L19960)|4|
|`UNRESOLVED_GUST_WITHOUT_OPPONENT_BENCH`|P2|GW5|UQ-GUST-WITHOUT-OPPONENT-BENCH|[kyuura_engine/effects.py:7309](../kyuura_engine/effects.py#L7309)|5|
|`UNRESOLVED_HAND_TRAINER_LOCK_BORROW`|P2|TL1|not_in_kyuura|[kyuura_engine/effects.py:30789](../kyuura_engine/effects.py#L30789)|3|
|`UNRESOLVED_HARD_SHELL_NONPOSITIVE`|P2|HS1|not_in_kyuura|[kyuura_engine/resolution/questions.py:556](../kyuura_engine/resolution/questions.py#L556)|6|
|`UNRESOLVED_HEALING_FIELD_WITHOUT_DAMAGE`|P2|HF1|not_in_kyuura|[kyuura_engine/effects.py:30806](../kyuura_engine/effects.py#L30806)|3|
|`UNRESOLVED_HEAL_UP_TO_ZERO`|P2|HZ1|not_in_kyuura|[kyuura_engine/effects.py:44957](../kyuura_engine/effects.py#L44957)|7|
|`UNRESOLVED_HELPING_HAND_CHOICE`|P2|HH2|UQ-HELPING-HAND-CHOICE|[kyuura_engine/effects.py:48076](../kyuura_engine/effects.py#L48076)|3|
|`UNRESOLVED_HELPING_HAND_WITHOUT_CONDITION`|P2|HH1|UQ-CARD-USE-WITHOUT-TARGET|[kyuura_engine/effects.py:48070](../kyuura_engine/effects.py#L48070)|3|
|`UNRESOLVED_HOT_PLATE_BABY_EVOLUTION`|P2|HP2|not_in_kyuura|[kyuura_engine/effects.py:36388](../kyuura_engine/effects.py#L36388)|4|
|`UNRESOLVED_HOT_PLATE_FACE_DOWN`|P2|HP1|not_in_kyuura|[kyuura_engine/effects.py:36381](../kyuura_engine/effects.py#L36381)|3|
|`UNRESOLVED_HOWL_OUTSIDE_OWN_TURN`|P2|OT1|not_in_kyuura|[kyuura_engine/effects.py:36145](../kyuura_engine/effects.py#L36145)|3|
|`UNRESOLVED_HYPER_TEXTURE_UNMARKED_TARGET`|P2|HX1|not_in_kyuura|[kyuura_engine/resolution/questions.py:212](../kyuura_engine/resolution/questions.py#L212)|7|
|`UNRESOLVED_IGNORED_EFFECTS_SCOPE`|P2|FA1|not_in_kyuura|[kyuura_engine/procedures.py:68](../kyuura_engine/procedures.py#L68)|15|
|`UNRESOLVED_INFLATE_NON_ATTACK_DAMAGE`|P2|IF1|UQ-NON-ATTACK-DAMAGE-MODIFIERS|[kyuura_engine/effects.py:19972](../kyuura_engine/effects.py#L19972)|3|
|`UNRESOLVED_JAW_CLAMP_SOURCE_EVOLVED`|P2|JC2|not_in_kyuura|[kyuura_engine/effects.py:38662](../kyuura_engine/effects.py#L38662)|4|
|`UNRESOLVED_JAW_CLAMP_SOURCE_RETURNED`|P2|JC1|not_in_kyuura|[kyuura_engine/effects.py:38657](../kyuura_engine/effects.py#L38657)|4|
|`UNRESOLVED_KEEP_DETACHED_ENERGY_DISCARD`|P2|KP3|not_in_kyuura|[kyuura_engine/resolution/questions.py:507](../kyuura_engine/resolution/questions.py#L507)|3|
|`UNRESOLVED_KEEP_PROTECTED_TARGET`|P2|KP1|not_in_kyuura|[kyuura_engine/effects.py:40759](../kyuura_engine/effects.py#L40759)|4|
|`UNRESOLVED_KEEP_VOIDED_DISCARD_COIN`|P2|KP2|not_in_kyuura|[kyuura_engine/resolution/questions.py:504](../kyuura_engine/resolution/questions.py#L504)|3|
|`UNRESOLVED_KOGA_POISON_ORDER`|P2|KG1|UQ-POISON-OVERWRITE-ORDER|[kyuura_engine/resolution/questions.py:286](../kyuura_engine/resolution/questions.py#L286)|3|
|`UNRESOLVED_KO_PREVENTION_ATTACK_EFFECT`|P2|G37,G30|UQ-GUTS-ATTACK-EFFECT|[kyuura_engine/effects.py:1199](../kyuura_engine/effects.py#L1199)|36|
|`UNRESOLVED_KO_PREVENTION_ORDER`|P2|G40,G16|UQ-KO-PREVENTION-ORDER|[kyuura_engine/resolution/questions.py:73](../kyuura_engine/resolution/questions.py#L73)|6|
|`UNRESOLVED_KO_SURVIVAL_OVERLAP`|P2|KS2|not_in_kyuura|[kyuura_engine/resolution/questions.py:521](../kyuura_engine/resolution/questions.py#L521)|10|
|`UNRESOLVED_KO_SURVIVAL_TIMING`|P2|KS1|not_in_kyuura|[kyuura_engine/resolution/questions.py:517](../kyuura_engine/resolution/questions.py#L517)|7|
|`UNRESOLVED_LAST_RESORT_UNDAMAGED_TARGET`|P2|GL2|UQ-TARGET-WITHOUT-EFFECT|[kyuura_engine/effects.py:18087](../kyuura_engine/effects.py#L18087)|3|
|`UNRESOLVED_LAST_RESORT_WITHOUT_TARGET`|P2|GL1|UQ-CARD-USE-WITHOUT-TARGET|[kyuura_engine/effects.py:18082](../kyuura_engine/effects.py#L18082)|3|
|`UNRESOLVED_LEAVE_LOCK_KNOCKOUT`|P2|AL1|not_in_kyuura|[kyuura_engine/effects.py:38642](../kyuura_engine/effects.py#L38642)|4|
|`UNRESOLVED_LEAVE_LOCK_NO_EFFECT`|P2|AL2|not_in_kyuura|[kyuura_engine/effects.py:38647](../kyuura_engine/effects.py#L38647)|6|
|`UNRESOLVED_LEAVE_LOCK_SCRAM`|P2|AL3|not_in_kyuura|[kyuura_engine/effects.py:38652](../kyuura_engine/effects.py#L38652)|4|
|`UNRESOLVED_LEGEND_BODY_GOOP_GAS`|P2|LB2|not_in_kyuura|[kyuura_engine/effects.py:44293](../kyuura_engine/effects.py#L44293)|7|
|`UNRESOLVED_LEGEND_BODY_TRAINER_TARGET`|P2|LB1|not_in_kyuura|[kyuura_engine/decisions.py:516](../kyuura_engine/decisions.py#L516)|11|
|`UNRESOLVED_LIGHTNING_BOLT_DEFENDER_UNITS`|P2|HR1|not_in_kyuura|[kyuura_engine/resolution/questions.py:207](../kyuura_engine/resolution/questions.py#L207)|7|
|`UNRESOLVED_LOCK_ON_PROTECTED_TARGET`|P2|LO1|not_in_kyuura|[kyuura_engine/effects.py:46763](../kyuura_engine/effects.py#L46763)|3|
|`UNRESOLVED_LT_SURGE_WITHOUT_BASIC`|P2|LS1|UQ-CARD-USE-WITHOUT-TARGET|[kyuura_engine/effects.py:18942](../kyuura_engine/effects.py#L18942)|3|
|`UNRESOLVED_LUCKY_STADIUM_UNSTATED_REPEAT`|P2|LK1|not_in_kyuura|[kyuura_engine/effects.py:21050](../kyuura_engine/effects.py#L21050)|3|
|`UNRESOLVED_MASTER_BALL_SHORT_DECK`|P2|ML1|not_in_kyuura|[kyuura_engine/effects.py:28975](../kyuura_engine/effects.py#L28975)|8|
|`UNRESOLVED_MAX_HP_DROP`|P2|MH1|UQ-EVOLUTION-HP-BELOW-DAMAGE|[kyuura_engine/effects.py:13978](../kyuura_engine/effects.py#L13978)|35|
|`UNRESOLVED_MAX_HP_SET_AND_INCREASE`|P2|MH2|not_in_kyuura|[kyuura_engine/effects.py:14080](../kyuura_engine/effects.py#L14080)|12|
|`UNRESOLVED_MAX_REVIVE_WITHOUT_TARGET`|P2|MR1|not_in_kyuura|[kyuura_engine/effects.py:28968](../kyuura_engine/effects.py#L28968)|7|
|`UNRESOLVED_MEAN_LOOK_SOURCE_EVOLVED`|P2|ML2|not_in_kyuura|[kyuura_engine/effects.py:38585](../kyuura_engine/effects.py#L38585)|8|
|`UNRESOLVED_METAL_ENERGY_POWER_ORDER`|P2|MT1|not_in_kyuura|[kyuura_engine/effects.py:19979](../kyuura_engine/effects.py#L19979)|5|
|`UNRESOLVED_MIND_GAMES_BLOCKED_TURN_END`|P2|MG3|not_in_kyuura|[kyuura_engine/effects.py:49073](../kyuura_engine/effects.py#L49073)|3|
|`UNRESOLVED_MIND_GAMES_CHAOS_GYM_ORDER`|P1|MG1|UQ-MIND-GAMES-TRAINER-STEP|[kyuura_engine/effects.py:49060](../kyuura_engine/effects.py#L49060)|3|
|`UNRESOLVED_MIND_GAMES_PLAY_AS_POKEMON`|P2|MG2|UQ-MIND-GAMES-TRAINER-STEP|[kyuura_engine/effects.py:49067](../kyuura_engine/effects.py#L49067)|3|
|`UNRESOLVED_MINEFIELD_DAMAGE_RECEIVED_POWER`|P2|EX1|UQ-NON-ATTACK-DAMAGE-MODIFIERS|[kyuura_engine/effects.py:21374](../kyuura_engine/effects.py#L21374)|3|
|`UNRESOLVED_MIRACLE_ENERGY_AS_TYPE`|P2|MEC1|not_in_kyuura|[kyuura_engine/effects.py:34609](../kyuura_engine/effects.py#L34609)|10|
|`UNRESOLVED_MIRACLE_ENERGY_UNDER_WIND`|P2|MEW1|not_in_kyuura|[kyuura_engine/effects.py:34615](../kyuura_engine/effects.py#L34615)|10|
|`UNRESOLVED_MIRACULOUS_WIND_CONVERTED_ENERGY`|P2|WD1|not_in_kyuura|[kyuura_engine/effects.py:34383](../kyuura_engine/effects.py#L34383)|4|
|`UNRESOLVED_MIRACULOUS_WIND_ENERGY_BURN`|P2|WD2|not_in_kyuura|[kyuura_engine/effects.py:34388](../kyuura_engine/effects.py#L34388)|3|
|`UNRESOLVED_MIRROR_MOVE_ATTACK_CONDITIONS`|P2|MM2|UQ-COPIED-ATTACK|[kyuura_engine/resolution/questions.py:342](../kyuura_engine/resolution/questions.py#L342)|6|
|`UNRESOLVED_MIRROR_MOVE_LASTING_EFFECT`|P2|OM1|UQ-COPIED-ATTACK|[kyuura_engine/resolution/questions.py:345](../kyuura_engine/resolution/questions.py#L345)|4|
|`UNRESOLVED_MIRROR_MOVE_NON_ATTACK`|P2|OM2|UQ-COPIED-ATTACK|[kyuura_engine/resolution/questions.py:348](../kyuura_engine/resolution/questions.py#L348)|4|
|`UNRESOLVED_MIRROR_MOVE_RECEIVED_ATTACK`|P2|MM1|UQ-COPIED-ATTACK|[kyuura_engine/resolution/questions.py:339](../kyuura_engine/resolution/questions.py#L339)|5|
|`UNRESOLVED_MISTYS_CARE_OPPONENT_LAPRAS`|P2|MQ1|not_in_kyuura|[kyuura_engine/effects.py:46785](../kyuura_engine/effects.py#L46785)|3|
|`UNRESOLVED_MISTYS_CARE_WITHOUT_TARGET`|P2|MQ2|not_in_kyuura|[kyuura_engine/effects.py:46790](../kyuura_engine/effects.py#L46790)|3|
|`UNRESOLVED_MISTYS_WISH_WITHOUT_HAND`|P2|MY1|UQ-CARD-USE-WITHOUT-TARGET|[kyuura_engine/effects.py:18958](../kyuura_engine/effects.py#L18958)|3|
|`UNRESOLVED_MISTYS_WRATH_SHORT_DECK`|P2|MW1|UQ-STATED-COUNT-SHORT|[kyuura_engine/effects.py:18057](../kyuura_engine/effects.py#L18057)|3|
|`UNRESOLVED_MISTY_SELF_DAMAGE`|P2|MS1|UQ-MISTY-SELF-DAMAGE|[kyuura_engine/resolution/questions.py:257](../kyuura_engine/resolution/questions.py#L257)|3|
|`UNRESOLVED_MOOMOO_MILK_UNDAMAGED_TARGET`|P2|MK1|not_in_kyuura|[kyuura_engine/effects.py:30797](../kyuura_engine/effects.py#L30797)|3|
|`UNRESOLVED_MR_FUJI_WITHOUT_BENCH`|P2|FJ1|UQ-CARD-USE-WITHOUT-TARGET|[kyuura_engine/effects.py:16877](../kyuura_engine/effects.py#L16877)|6|
|`UNRESOLVED_MULLIGAN_COMPENSATION`|P1|—|out_of_scope|[kyuura_engine/effects.py:2321](../kyuura_engine/effects.py#L2321)|870|
|`UNRESOLVED_MULTIPLE_ATTACK_CHECKS`|P2|AC13,AC13|UQ-ATTACK-PRE-DAMAGE-COIN-ORDER|[kyuura_engine/resolution/questions.py:126](../kyuura_engine/resolution/questions.py#L126)|12|
|`UNRESOLVED_MULTIPLE_DAMAGE_TRIGGERS`|P2|C34,C35,S7,Z18,DR18|UQ-MULTIPLE-DAMAGE-TRIGGERS-ONE-ATTACK|[kyuura_engine/resolution/questions.py:71](../kyuura_engine/resolution/questions.py#L71)|5|
|`UNRESOLVED_NEO_TEXT_BASIC_BABY`|P2|NB1|UQ-NEO-TEXT-BABY-CATEGORIES|[kyuura_engine/effects.py:15293](../kyuura_engine/effects.py#L15293)|7|
|`UNRESOLVED_NEO_TEXT_EVOLUTION_CARD_BABY`|P2|NB2|UQ-NEO-TEXT-BABY-CATEGORIES|[kyuura_engine/effects.py:15297](../kyuura_engine/effects.py#L15297)|6|
|`UNRESOLVED_NIGHTLY_GARBAGE_RUN_ZERO_CHOICE`|P2|NG1|UQ-UP-TO-ZERO-CHOICE|[kyuura_engine/effects.py:17034](../kyuura_engine/effects.py#L17034)|7|
|`UNRESOLVED_NINJA_GYM_WITHOUT_TARGET`|P2|NJ1|not_in_kyuura|[kyuura_engine/effects.py:21059](../kyuura_engine/effects.py#L21059)|3|
|`UNRESOLVED_NINJA_TRICK_ATTACK_COIN_ORDER`|P2|NT1|UQ-REACTIVE-SWITCH-DURING-ATTACK|[kyuura_engine/effects.py:22175](../kyuura_engine/effects.py#L22175)|4|
|`UNRESOLVED_NINJA_TRICK_LEAVES_WITH_POKEMON`|P2|NT2|UQ-ATTACHED-CARDS-WHEN-RETURNED|[kyuura_engine/effects.py:22177](../kyuura_engine/effects.py#L22177)|4|
|`UNRESOLVED_NINJA_TRICK_UNDER_TRAINER_BAN`|P2|NT3|UQ-TRAINER-BAN-SCOPE|[kyuura_engine/effects.py:22182](../kyuura_engine/effects.py#L22182)|3|
|`UNRESOLVED_OLD_ROD_WITHOUT_TARGET`|P2|OR1|UQ-CARD-USE-WITHOUT-TARGET|[kyuura_engine/effects.py:46780](../kyuura_engine/effects.py#L46780)|3|
|`UNRESOLVED_OPPONENT_POKEMON_COUNTERS`|P2|CD4|UQ-OPPONENT-POKEMON-COUNTERS|[kyuura_engine/resolution/questions.py:101](../kyuura_engine/resolution/questions.py#L101)|6|
|`UNRESOLVED_PERFORM_DAMAGE_PLACES`|P2|PFM1|not_in_kyuura|[kyuura_engine/effects.py:40510](../kyuura_engine/effects.py#L40510)|4|
|`UNRESOLVED_PERISH_SONG_RECEIVED_ATTACK`|P2|PSG1|not_in_kyuura|[kyuura_engine/resolution/questions.py:496](../kyuura_engine/resolution/questions.py#L496)|3|
|`UNRESOLVED_PERMITTED_ATTACK_HELD`|P2|VP1|not_in_kyuura|[kyuura_engine/effects.py:15848](../kyuura_engine/effects.py#L15848)|3|
|`UNRESOLVED_PHOENIX_GAS_SOURCE_KNOCKOUT`|P2|P19|UQ-PHOENIX-GAS-SOURCE-KO|[kyuura_engine/resolution/questions.py:77](../kyuura_engine/resolution/questions.py#L77)|4|
|`UNRESOLVED_PLAY_AS_POKEMON_RETREAT`|P2|PF2|UQ-PLAY-AS-POKEMON|[kyuura_engine/effects.py:13468](../kyuura_engine/effects.py#L13468)|10|
|`UNRESOLVED_PLAY_AS_POKEMON_SETUP`|P2|PF1|UQ-PLAY-AS-POKEMON|[kyuura_engine/effects.py:13474](../kyuura_engine/effects.py#L13474)|13|
|`UNRESOLVED_POISON_CHANGE_ORDER`|P2|PO1|not_in_kyuura|[kyuura_engine/effects.py:45886](../kyuura_engine/effects.py#L45886)|6|
|`UNRESOLVED_POISON_DAMAGE_RECEIVED_POWER`|P2|KA1|UQ-NON-ATTACK-DAMAGE-MODIFIERS|[kyuura_engine/procedures.py:59](../kyuura_engine/procedures.py#L59)|12|
|`UNRESOLVED_POISON_MIST_EARLIER_POISON`|P2|PO2|not_in_kyuura|[kyuura_engine/effects.py:45891](../kyuura_engine/effects.py#L45891)|6|
|`UNRESOLVED_POISON_MIST_SOURCE`|P2|PO3|not_in_kyuura|[kyuura_engine/effects.py:45895](../kyuura_engine/effects.py#L45895)|6|
|`UNRESOLVED_POKEDEX_UP_TO_ZERO`|P2|PD2|not_in_kyuura|[kyuura_engine/effects.py:17600](../kyuura_engine/effects.py#L17600)|5|
|`UNRESOLVED_POKEMON_CHECK_BERRY_ORDER`|P2|BY1|not_in_kyuura|[kyuura_engine/procedures.py:410](../kyuura_engine/procedures.py#L410)|11|
|`UNRESOLVED_POKEMON_CHECK_CHAR_COIN_ORDER`|P2|KK1|not_in_kyuura|[kyuura_engine/procedures.py:360](../kyuura_engine/procedures.py#L360)|6|
|`UNRESOLVED_POKEMON_CHECK_DOUBLE_KNOCKOUT`|P2|—|out_of_scope|[kyuura_engine/procedures.py:71](../kyuura_engine/procedures.py#L71)|50|
|`UNRESOLVED_POKEMON_CHECK_MID_KNOCKOUT`|P2|PK1|not_in_kyuura|[kyuura_engine/procedures.py:735](../kyuura_engine/procedures.py#L735)|14|
|`UNRESOLVED_POKEMON_CHECK_SLEEP_COIN_ORDER`|P1|Z29|UQ-POKEMON-CHECK-SLEEP-COIN-ORDER|[kyuura_engine/procedures.py:952](../kyuura_engine/procedures.py#L952)|12|
|`UNRESOLVED_POKEMON_FLUTE_WITHOUT_TARGET`|P2|FT1|UQ-CARD-USE-WITHOUT-TARGET|[kyuura_engine/effects.py:16574](../kyuura_engine/effects.py#L16574)|6|
|`UNRESOLVED_POKEMON_TOWER_POWER_WITHOUT_EFFECT`|P2|PW5|not_in_kyuura|[kyuura_engine/effects.py:47256](../kyuura_engine/effects.py#L47256)|3|
|`UNRESOLVED_POKEMON_TOWER_TRAINER_WITHOUT_EFFECT`|P2|PT1|not_in_kyuura|[kyuura_engine/effects.py:21296](../kyuura_engine/effects.py#L21296)|4|
|`UNRESOLVED_POST_KNOCKOUT_POWERS_ORDER`|P2|P32|UQ-POST-KO-POWERS-ORDER|[kyuura_engine/resolution/questions.py:75](../kyuura_engine/resolution/questions.py#L75)|3|
|`UNRESOLVED_POTION_UNDAMAGED_TARGET`|P2|—|out_of_scope|[kyuura_engine/effects.py:7100](../kyuura_engine/effects.py#L7100)|3|
|`UNRESOLVED_POTION_WITHOUT_DAMAGE`|P2|—|out_of_scope|[kyuura_engine/effects.py:7086](../kyuura_engine/effects.py#L7086)|5|
|`UNRESOLVED_POWER_COUNTER_MOVE_TO_SAME_POKEMON`|P2|BE1|not_in_kyuura|[kyuura_engine/effects.py:40201](../kyuura_engine/effects.py#L40201)|3|
|`UNRESOLVED_POWER_COUNTER_MOVE_WITHOUT_COUNTERS`|P2|BE2|not_in_kyuura|[kyuura_engine/effects.py:40208](../kyuura_engine/effects.py#L40208)|3|
|`UNRESOLVED_POWER_DAMAGE_PREVENTED`|P2|SB1|not_in_kyuura|[kyuura_engine/resolution/questions.py:446](../kyuura_engine/resolution/questions.py#L446)|3|
|`UNRESOLVED_POWER_DAMAGE_RECEIVED_POWER`|P2|DF2|UQ-NON-ATTACK-DAMAGE-MODIFIERS|[kyuura_engine/effects.py:40102](../kyuura_engine/effects.py#L40102)|4|
|`UNRESOLVED_POWER_DAMAGE_WEAKNESS_RESISTANCE`|P2|Z9,Z9|UQ-POWER-DAMAGE-WEAKNESS-RESISTANCE|[kyuura_engine/effects.py:19931](../kyuura_engine/effects.py#L19931)|11|
|`UNRESOLVED_POWER_DECK_TOP_SHORT`|P2|OB1|not_in_kyuura|[kyuura_engine/effects.py:39688](../kyuura_engine/effects.py#L39688)|4|
|`UNRESOLVED_POWER_DISCARD_WITHOUT_HAND`|P2|PW2|UQ-CARD-USE-WITHOUT-TARGET|[kyuura_engine/effects.py:8987](../kyuura_engine/effects.py#L8987)|5|
|`UNRESOLVED_POWER_HEAL_WITHOUT_DAMAGE`|P2|HC8|UQ-TARGET-WITHOUT-EFFECT|[kyuura_engine/effects.py:8409](../kyuura_engine/effects.py#L8409)|5|
|`UNRESOLVED_POWER_RETURN_WITHOUT_TARGET`|P2|VN1|not_in_kyuura|[kyuura_engine/effects.py:40394](../kyuura_engine/effects.py#L40394)|3|
|`UNRESOLVED_POWER_REUSE_AFTER_DEVOLUTION`|P2|DV3|UQ-DEVOLUTION-SAME-TURN|[kyuura_engine/effects.py:7737](../kyuura_engine/effects.py#L7737)|7|
|`UNRESOLVED_POWER_SWITCH_WITHOUT_OPPONENT_BENCH`|P2|PW1|UQ-CARD-USE-WITHOUT-TARGET|[kyuura_engine/effects.py:8924](../kyuura_engine/effects.py#L8924)|5|
|`UNRESOLVED_POWER_ZERO_CARDS`|P2|PW3|UQ-UP-TO-ZERO-CHOICE|[kyuura_engine/effects.py:9051](../kyuura_engine/effects.py#L9051)|49|
|`UNRESOLVED_PREVENTED_COIN_DAMAGE`|P2|—|UQ-COIN-IN-NULLIFIED-ELEMENT|[kyuura_engine/effects.py:486](../kyuura_engine/effects.py#L486)|51|
|`UNRESOLVED_PREVENTED_EFFECT_COIN`|P2|HC3|UQ-COIN-IN-NULLIFIED-ELEMENT|[kyuura_engine/resolution/questions.py:91](../kyuura_engine/resolution/questions.py#L91)|62|
|`UNRESOLVED_PRE_EVOLUTION_ATTACK_CONDITIONS`|P2|PE2|not_in_kyuura|[kyuura_engine/effects.py:16059](../kyuura_engine/effects.py#L16059)|3|
|`UNRESOLVED_PRE_EVOLUTION_ATTACK_STAGE`|P2|PE1|not_in_kyuura|[kyuura_engine/effects.py:15842](../kyuura_engine/effects.py#L15842)|3|
|`UNRESOLVED_PRIMAL_DREAM_DAMAGE_STEP`|P2|PM2|not_in_kyuura|[kyuura_engine/effects.py:47237](../kyuura_engine/effects.py#L47237)|3|
|`UNRESOLVED_PRIMAL_DREAM_SUPPRESSED`|P2|PM1|not_in_kyuura|[kyuura_engine/effects.py:47232](../kyuura_engine/effects.py#L47232)|3|
|`UNRESOLVED_PROTECTIVE_FLAME_SCOPE`|P2|PL1|not_in_kyuura|[kyuura_engine/effects.py:35754](../kyuura_engine/effects.py#L35754)|3|
|`UNRESOLVED_QUICKEN_EFFECT_SUPPRESSED`|P2|QK1|not_in_kyuura|[kyuura_engine/effects.py:44272](../kyuura_engine/effects.py#L44272)|6|
|`UNRESOLVED_RAINBOW_AS_BASIC_ENERGY_CARD`|P2|RB3|UQ-SPECIAL-ENERGY-AS-TYPED-ENERGY|[kyuura_engine/effects.py:9765](../kyuura_engine/effects.py#L9765)|7|
|`UNRESOLVED_RAINBOW_ATTACH_AS_TYPE`|P2|RB2|UQ-SPECIAL-ENERGY-AS-TYPED-ENERGY|[kyuura_engine/effects.py:9759](../kyuura_engine/effects.py#L9759)|7|
|`UNRESOLVED_RAINBOW_DAMAGE_RECEIVED_POWER`|P2|RB4|UQ-NON-ATTACK-DAMAGE-MODIFIERS|[kyuura_engine/effects.py:9771](../kyuura_engine/effects.py#L9771)|5|
|`UNRESOLVED_RAINBOW_ENERGY_TYPE`|P2|RB1|UQ-SPECIAL-ENERGY-AS-TYPED-ENERGY|[kyuura_engine/effects.py:9752](../kyuura_engine/effects.py#L9752)|22|
|`UNRESOLVED_RAINBOW_RECOVER_AS_TYPE`|P2|RB5|not_in_kyuura|[kyuura_engine/resolution/questions.py:253](../kyuura_engine/resolution/questions.py#L253)|4|
|`UNRESOLVED_REACTION_AFTER_KNOCKOUT`|P2|RA1|not_in_kyuura|[kyuura_engine/reactions.py:75](../kyuura_engine/reactions.py#L75)|3|
|`UNRESOLVED_REACTION_BY_KNOCKED_OUT_POKEMON`|P2|KD1|UQ-REACTIVE-SWITCH-DURING-ATTACK|[kyuura_engine/effects.py:22207](../kyuura_engine/effects.py#L22207)|6|
|`UNRESOLVED_REACTION_CONDITION_CHANGED`|P2|RA2|not_in_kyuura|[kyuura_engine/reactions.py:80](../kyuura_engine/reactions.py#L80)|4|
|`UNRESOLVED_REACTIVE_SWITCH_TRANSFORMED_ATTACKER`|P2|RX1|UQ-REACTIVE-SWITCH-DURING-ATTACK|[kyuura_engine/effects.py:22187](../kyuura_engine/effects.py#L22187)|5|
|`UNRESOLVED_RECALL_EARLIER_STAGE`|P2|RC2|UQ-RECALL-SCOPE|[kyuura_engine/effects.py:15727](../kyuura_engine/effects.py#L15727)|7|
|`UNRESOLVED_RECALL_FORM`|P2|RC4|UQ-RECALL-SCOPE|[kyuura_engine/effects.py:15737](../kyuura_engine/effects.py#L15737)|9|
|`UNRESOLVED_RECALL_TARGET_CHANGED`|P2|RC3|UQ-RECALL-SCOPE|[kyuura_engine/effects.py:15732](../kyuura_engine/effects.py#L15732)|9|
|`UNRESOLVED_RECALL_WITHOUT_PRE_EVOLUTION_ATTACK`|P2|RC1|UQ-RECALL-SCOPE|[kyuura_engine/effects.py:15722](../kyuura_engine/effects.py#L15722)|7|
|`UNRESOLVED_RECOVER_ZERO_ENERGY`|P2|H4|UQ-ENERGY-CONVERSION-ZERO|[kyuura_engine/resolution/programs.py:2875](../kyuura_engine/resolution/programs.py#L2875)|3|
|`UNRESOLVED_REDUCED_DAMAGE_BENCH_TARGET`|P2|NK5|UQ-REDUCED-DAMAGE-BENCH-TARGET|[kyuura_engine/resolution/questions.py:111](../kyuura_engine/resolution/questions.py#L111)|6|
|`UNRESOLVED_REFLECT_SHIELD_OVERLAP`|P2|RF1|not_in_kyuura|[kyuura_engine/resolution/questions.py:389](../kyuura_engine/resolution/questions.py#L389)|5|
|`UNRESOLVED_REFLECT_SHIELD_TIMING`|P2|RS1|not_in_kyuura|[kyuura_engine/resolution/questions.py:384](../kyuura_engine/resolution/questions.py#L384)|3|
|`UNRESOLVED_REPARALYSIS_RECOVERY_TURN`|P2|—|out_of_scope|[kyuura_engine/conditions.py:249](../kyuura_engine/conditions.py#L249)|10|
|`UNRESOLVED_RETALIATION_DOUBLE_KNOCKOUT`|P2|W24,S37|UQ-RETALIATION-DOUBLE-KO|[kyuura_engine/effects.py:36508](../kyuura_engine/effects.py#L36508)|1194|
|`UNRESOLVED_RETREAT_AFTER_CONFUSION_CLEARED`|P2|—|out_of_scope|[kyuura_engine/engine.py:1538](../kyuura_engine/engine.py#L1538)|7|
|`UNRESOLVED_RETREAT_COST_FLOOR`|P2|CP2|UQ-RETREAT-COST-PAYMENT|[kyuura_engine/engine.py:1585](../kyuura_engine/engine.py#L1585)|15|
|`UNRESOLVED_RETREAT_OVERPAY`|P2|RT1|UQ-RETREAT-COST-PAYMENT|[kyuura_engine/effects.py:9780](../kyuura_engine/effects.py#L9780)|5|
|`UNRESOLVED_RETREAT_REACTION_TIMING`|P2|RR1|not_in_kyuura|[kyuura_engine/effects.py:44266](../kyuura_engine/effects.py#L44266)|9|
|`UNRESOLVED_RETURN_IN_PLAY_TO_DECK_KNOCKOUT`|P2|RD9|UQ-RETURN-TO-DECK-KO-ORDER|[kyuura_engine/resolution/questions.py:130](../kyuura_engine/resolution/questions.py#L130)|16|
|`UNRESOLVED_REVIVED_BASIC_DEVOLVED`|P2|FE1|not_in_kyuura|[kyuura_engine/effects.py:46343](../kyuura_engine/effects.py#L46343)|3|
|`UNRESOLVED_REVIVE_HAND_BASIC_ENTRY`|P2|FE2|not_in_kyuura|[kyuura_engine/effects.py:46337](../kyuura_engine/effects.py#L46337)|3|
|`UNRESOLVED_REVIVE_WITHOUT_TARGET`|P2|RV1|UQ-CARD-USE-WITHOUT-TARGET|[kyuura_engine/effects.py:16567](../kyuura_engine/effects.py#L16567)|7|
|`UNRESOLVED_ROCKETS_TRAP_ZERO_CHOICE`|P2|RT1|UQ-UP-TO-ZERO-CHOICE|[kyuura_engine/effects.py:18947](../kyuura_engine/effects.py#L18947)|3|
|`UNRESOLVED_ROCKET_GRUNT_WITHOUT_BENCH`|P2|RG1|UQ-CARD-USE-WITHOUT-TARGET|[kyuura_engine/effects.py:18953](../kyuura_engine/effects.py#L18953)|3|
|`UNRESOLVED_SABRINA_SOURCE_WITHOUT_ENERGY`|P2|SB2|UQ-TARGET-WITHOUT-EFFECT|[kyuura_engine/effects.py:18098](../kyuura_engine/effects.py#L18098)|3|
|`UNRESOLVED_SABRINA_WITHOUT_TWO_POKEMON`|P2|SB1|UQ-CARD-USE-WITHOUT-TARGET|[kyuura_engine/effects.py:18093](../kyuura_engine/effects.py#L18093)|3|
|`UNRESOLVED_SCARE_SUPPRESSION_CYCLE`|P2|IA1|not_in_kyuura|[kyuura_engine/effects.py:46105](../kyuura_engine/effects.py#L46105)|7|
|`UNRESOLVED_SCOOP_UP_ATTACHED_TRAINER`|P2|SU1|UQ-ATTACHED-CARDS-WHEN-RETURNED|[kyuura_engine/effects.py:16886](../kyuura_engine/effects.py#L16886)|7|
|`UNRESOLVED_SCOOP_UP_LAST_POKEMON`|P2|SU2|UQ-CARD-USE-WITHOUT-TARGET|[kyuura_engine/effects.py:16893](../kyuura_engine/effects.py#L16893)|6|
|`UNRESOLVED_SCRAM_POWER_RESTORED`|P2|SC2|UQ-SCRAM-TIMING|[kyuura_engine/effects.py:19952](../kyuura_engine/effects.py#L19952)|10|
|`UNRESOLVED_SCRAM_TIMING`|P2|SC1|UQ-SCRAM-TIMING|[kyuura_engine/effects.py:19945](../kyuura_engine/effects.py#L19945)|20|
|`UNRESOLVED_SEARCH_TRAINER_WITHOUT_TARGET`|P2|ST1|UQ-CARD-USE-WITHOUT-TARGET|[kyuura_engine/effects.py:17027](../kyuura_engine/effects.py#L17027)|20|
|`UNRESOLVED_SECRETE_POISON_TARGET`|P2|PX1|not_in_kyuura|[kyuura_engine/effects.py:45711](../kyuura_engine/effects.py#L45711)|5|
|`UNRESOLVED_SECRET_PLAN_HIDDEN_PROPERTY`|P2|FD1|UQ-FACE-DOWN-CARD|[kyuura_engine/effects.py:47117](../kyuura_engine/effects.py#L47117)|15|
|`UNRESOLVED_SECRET_PLAN_MINEFIELD`|P2|FD2|UQ-FACE-DOWN-CARD|[kyuura_engine/effects.py:21977](../kyuura_engine/effects.py#L21977)|4|
|`UNRESOLVED_SELF_EXCLUDING_POWER_COPIES`|P2|DF1|UQ-SELF-EXCLUDING-POWER-COPIES|[kyuura_engine/effects.py:40094](../kyuura_engine/effects.py#L40094)|19|
|`UNRESOLVED_SHAPESHIFT_AGAIN`|P2|DG3|UQ-SHAPESHIFT-SCOPE|[kyuura_engine/effects.py:16202](../kyuura_engine/effects.py#L16202)|7|
|`UNRESOLVED_SHAPESHIFT_ENTRY_POWER`|P2|DG2|UQ-SHAPESHIFT-SCOPE|[kyuura_engine/effects.py:16197](../kyuura_engine/effects.py#L16197)|8|
|`UNRESOLVED_SHAPESHIFT_SUPPRESSED`|P2|DG1|UQ-SHAPESHIFT-SCOPE|[kyuura_engine/effects.py:16192](../kyuura_engine/effects.py#L16192)|8|
|`UNRESOLVED_SHELL_ARMOR_TIMING`|P2|AM1|not_in_kyuura|[kyuura_engine/resolution/questions.py:541](../kyuura_engine/resolution/questions.py#L541)|6|
|`UNRESOLVED_SHIFT_COLOR_DURATION`|P2|VS1|UQ-SHIFT-COLOR-DURATION|[kyuura_engine/effects.py:13963](../kyuura_engine/effects.py#L13963)|11|
|`UNRESOLVED_SINKHOLE_TIMING`|P2|SH1|UQ-SINKHOLE-TIMING|[kyuura_engine/effects.py:19938](../kyuura_engine/effects.py#L19938)|7|
|`UNRESOLVED_SKETCH_COPIED_ATTACK`|P2|SK2|not_in_kyuura|[kyuura_engine/resolution/questions.py:493](../kyuura_engine/resolution/questions.py#L493)|3|
|`UNRESOLVED_SKETCH_PRESENCE`|P2|SK1|not_in_kyuura|[kyuura_engine/resolution/questions.py:490](../kyuura_engine/resolution/questions.py#L490)|3|
|`UNRESOLVED_SOLAR_POWER_WITHOUT_CONDITION`|P2|SO1|not_in_kyuura|[kyuura_engine/effects.py:35901](../kyuura_engine/effects.py#L35901)|3|
|`UNRESOLVED_SPECIAL_POISON_OVERWRITE`|P2|15,TP3|UQ-POISON-OVERWRITE-ORDER|[kyuura_engine/resolution/questions.py:108](../kyuura_engine/resolution/questions.py#L108)|8|
|`UNRESOLVED_SPEED_STAR_SCOPE`|P2|SS1,SS1|UQ-SPEED-STAR-SCOPE|[kyuura_engine/resolution/questions.py:315](../kyuura_engine/resolution/questions.py#L315)|5|
|`UNRESOLVED_STADIUM_ACTIVATION_UNDER_TRAINER_BAN`|P2|STB1|UQ-TRAINER-BAN-SCOPE|[kyuura_engine/effects.py:20571](../kyuura_engine/effects.py#L20571)|4|
|`UNRESOLVED_STADIUM_REUSE_AFTER_REPLACEMENT`|P2|RS1|not_in_kyuura|[kyuura_engine/effects.py:21045](../kyuura_engine/effects.py#L21045)|4|
|`UNRESOLVED_STADIUM_REUSE_AFTER_RETURN`|P2|SX2|not_in_kyuura|[kyuura_engine/effects.py:44974](../kyuura_engine/effects.py#L44974)|5|
|`UNRESOLVED_STATED_CARDS_SHORT`|P2|FC1,FC1|UQ-STATED-COUNT-SHORT|[kyuura_engine/effects.py:11059](../kyuura_engine/effects.py#L11059)|42|
|`UNRESOLVED_STOPPED_POWER_HOLDER`|P2|HV1|not_in_kyuura|[kyuura_engine/effects.py:42926](../kyuura_engine/effects.py#L42926)|4|
|`UNRESOLVED_STRANGE_GAS_NEW_POKEMON`|P2|MG1|not_in_kyuura|[kyuura_engine/effects.py:36785](../kyuura_engine/effects.py#L36785)|4|
|`UNRESOLVED_STRANGE_GAS_PROTECTED_POKEMON`|P2|MG2|not_in_kyuura|[kyuura_engine/effects.py:36790](../kyuura_engine/effects.py#L36790)|3|
|`UNRESOLVED_SUPER_ENERGY_RETRIEVAL_WITHOUT_TARGET`|P2|SR1|not_in_kyuura|[kyuura_engine/effects.py:28982](../kyuura_engine/effects.py#L28982)|6|
|`UNRESOLVED_SUPER_ENERGY_RETRIEVAL_ZERO_CHOICE`|P2|SR2|not_in_kyuura|[kyuura_engine/effects.py:28987](../kyuura_engine/effects.py#L28987)|6|
|`UNRESOLVED_SUPER_POTION_UNDAMAGED_TARGET`|P2|SP1|UQ-TARGET-WITHOUT-EFFECT|[kyuura_engine/effects.py:18069](../kyuura_engine/effects.py#L18069)|3|
|`UNRESOLVED_SUPER_ROD_WITHOUT_TARGET`|P2|SRD1|not_in_kyuura|[kyuura_engine/effects.py:30772](../kyuura_engine/effects.py#L30772)|3|
|`UNRESOLVED_SUPER_TRANSFORM_COPIED_POWER`|P2|SV3|UQ-SUPER-TRANSFORM-COPIED-POWERS|[kyuura_engine/effects.py:15039](../kyuura_engine/effects.py#L15039)|5|
|`UNRESOLVED_SUPER_TRANSFORM_ENERGY_COLORS`|P2|SV5|UQ-SUPER-TRANSFORM-ENERGY-COLORS|[kyuura_engine/effects.py:15047](../kyuura_engine/effects.py#L15047)|4|
|`UNRESOLVED_SUPER_TRANSFORM_SOURCE_CHANGE`|P2|SV2|UQ-SUPER-TRANSFORM-SOURCE-CHANGES|[kyuura_engine/effects.py:15035](../kyuura_engine/effects.py#L15035)|4|
|`UNRESOLVED_SUPER_TRANSFORM_SUPPRESSED_FORM`|P2|SV4|UQ-SUPER-TRANSFORM-SUPPRESSED-FORM|[kyuura_engine/effects.py:15043](../kyuura_engine/effects.py#L15043)|4|
|`UNRESOLVED_SUPER_TRANSFORM_TARGET`|P2|SV1|UQ-SUPER-TRANSFORM-TARGETS|[kyuura_engine/effects.py:15031](../kyuura_engine/effects.py#L15031)|4|
|`UNRESOLVED_SWITCH_WITHOUT_BENCH`|P2|—|out_of_scope|[kyuura_engine/effects.py:7154](../kyuura_engine/effects.py#L7154)|7|
|`UNRESOLVED_THOUGHT_WAVE_MACHINE_ENERGY_SHORT`|P2|TW1|UQ-STATED-COUNT-SHORT|[kyuura_engine/effects.py:48262](../kyuura_engine/effects.py#L48262)|3|
|`UNRESOLVED_THOUGHT_WAVE_MACHINE_WITHOUT_TARGET`|P2|TW2|UQ-CARD-USE-WITHOUT-TARGET|[kyuura_engine/effects.py:48268](../kyuura_engine/effects.py#L48268)|3|
|`UNRESOLVED_TIME_SHIFT_WITHOUT_TARGET`|P2|SX1|not_in_kyuura|[kyuura_engine/effects.py:44968](../kyuura_engine/effects.py#L44968)|5|
|`UNRESOLVED_TIME_TRAVEL_OVERLAP`|P2|TW2|not_in_kyuura|[kyuura_engine/effects.py:44283](../kyuura_engine/effects.py#L44283)|6|
|`UNRESOLVED_TIME_TRAVEL_TIMING`|P2|TW1|not_in_kyuura|[kyuura_engine/effects.py:44278](../kyuura_engine/effects.py#L44278)|6|
|`UNRESOLVED_TRAINER_DAMAGE_REDUCTION`|P2|TD1|UQ-NON-ATTACK-DAMAGE-MODIFIERS|[kyuura_engine/effects.py:19986](../kyuura_engine/effects.py#L19986)|7|
|`UNRESOLVED_TRAINER_UP_TO_WITHOUT_TARGET`|P2|UPZ2|not_in_kyuura|[kyuura_engine/effects.py:30781](../kyuura_engine/effects.py#L30781)|4|
|`UNRESOLVED_TRAINER_UP_TO_ZERO_CHOICE`|P2|UPZ1|not_in_kyuura|[kyuura_engine/effects.py:30776](../kyuura_engine/effects.py#L30776)|4|
|`UNRESOLVED_TRAINER_WITHOUT_TARGET`|P2|TR1|UQ-CARD-USE-WITHOUT-TARGET|[kyuura_engine/effects.py:12485](../kyuura_engine/effects.py#L12485)|11|
|`UNRESOLVED_TRANSFORM_BABY`|P2|BX1|not_in_kyuura|[kyuura_engine/effects.py:15301](../kyuura_engine/effects.py#L15301)|3|
|`UNRESOLVED_TRANSFORM_BABY_AND_BASIC`|P2|BX2|UQ-TRANSFORM-BABY-AND-BASIC|[kyuura_engine/effects.py:15309](../kyuura_engine/effects.py#L15309)|4|
|`UNRESOLVED_TRANSFORM_COPIED_POWER`|P2|TF1|UQ-TRANSFORM-SCOPE|[kyuura_engine/effects.py:19701](../kyuura_engine/effects.py#L19701)|11|
|`UNRESOLVED_TRANSFORM_ENERGY_COLOR_LIST`|P2|TC1|UQ-TRANSFORM-ENERGY-COLOR-LIST|[kyuura_engine/effects.py:10809](../kyuura_engine/effects.py#L10809)|5|
|`UNRESOLVED_TRANSFORM_ENERGY_COUNT`|P2|TE1|UQ-TRANSFORM-SCOPE|[kyuura_engine/effects.py:36925](../kyuura_engine/effects.py#L36925)|7|
|`UNRESOLVED_TRANSFORM_MODIFIED_DEFENDER`|P2|TF2|UQ-TRANSFORM-SCOPE|[kyuura_engine/effects.py:19709](../kyuura_engine/effects.py#L19709)|8|
|`UNRESOLVED_TRANSFORM_REVERT_KNOCKOUT_TIMING`|P2|TK1|UQ-TRANSFORM-REVERT-KNOCKOUT-TIMING|[kyuura_engine/effects.py:15234](../kyuura_engine/effects.py#L15234)|17|
|`UNRESOLVED_TRANSFORM_REVIVED_BASIC`|P2|TF3|not_in_kyuura|[kyuura_engine/effects.py:46348](../kyuura_engine/effects.py#L46348)|4|
|`UNRESOLVED_TRANSFORM_SPECIAL_ENERGY`|P2|TE2|UQ-SPECIAL-ENERGY-AS-TYPED-ENERGY|[kyuura_engine/effects.py:9773](../kyuura_engine/effects.py#L9773)|16|
|`UNRESOLVED_TRANSPARENCY_COIN_ORDER`|P2|T27|UQ-TRANSPARENCY-COIN-ORDER|[kyuura_engine/resolution/questions.py:80](../kyuura_engine/resolution/questions.py#L80)|9|
|`UNRESOLVED_TRANSPORT_WITHOUT_CARDS`|P2|TN1|not_in_kyuura|[kyuura_engine/effects.py:44979](../kyuura_engine/effects.py#L44979)|5|
|`UNRESOLVED_VANISH_OTHER_ATTACHED`|P2|VH1|not_in_kyuura|[kyuura_engine/effects.py:44368](../kyuura_engine/effects.py#L44368)|6|
|`UNRESOLVED_VERMILION_GYM_ATTACK_ORDER`|P2|VM1|UQ-ATTACK-PRE-DAMAGE-COIN-ORDER|[kyuura_engine/effects.py:21507](../kyuura_engine/effects.py#L21507)|4|
|`UNRESOLVED_VINE_PULL_TIMING`|P2|VL1|not_in_kyuura|[kyuura_engine/effects.py:47261](../kyuura_engine/effects.py#L47261)|3|
|`UNRESOLVED_VIRIDIAN_GYM_ONE_COUNTER`|P2|VG1|UQ-STATED-COUNT-SHORT|[kyuura_engine/effects.py:21434](../kyuura_engine/effects.py#L21434)|3|
|`UNRESOLVED_VIRTUAL_ASLEEP_ONLY_ATTACK`|P2|SQ1|UQ-COPIED-ATTACK|[kyuura_engine/effects.py:46757](../kyuura_engine/effects.py#L46757)|4|
|`UNRESOLVED_VIRTUAL_ONCE_ATTACK`|P2|VA1|UQ-COPIED-ATTACK|[kyuura_engine/effects.py:15717](../kyuura_engine/effects.py#L15717)|8|
|`UNRESOLVED_WANT_WITHOUT_TARGET`|P2|WT1|not_in_kyuura|[kyuura_engine/effects.py:47243](../kyuura_engine/effects.py#L47243)|3|

## 11. 内部例外・未確認項目の引き継ぎ

|ファイル|内部ガード箇所数|
|---|---:|
|[kyuura_engine/checks.py](../kyuura_engine/checks.py)|1|
|[kyuura_engine/coins.py](../kyuura_engine/coins.py)|3|
|[kyuura_engine/conditions.py](../kyuura_engine/conditions.py)|5|
|[kyuura_engine/continuous.py](../kyuura_engine/continuous.py)|3|
|[kyuura_engine/damage.py](../kyuura_engine/damage.py)|3|
|[kyuura_engine/decisions.py](../kyuura_engine/decisions.py)|5|
|[kyuura_engine/effects.py](../kyuura_engine/effects.py)|173|
|[kyuura_engine/engine.py](../kyuura_engine/engine.py)|24|
|[kyuura_engine/evolution.py](../kyuura_engine/evolution.py)|3|
|[kyuura_engine/faceup.py](../kyuura_engine/faceup.py)|1|
|[kyuura_engine/history.py](../kyuura_engine/history.py)|5|
|[kyuura_engine/interruption.py](../kyuura_engine/interruption.py)|3|
|[kyuura_engine/markers.py](../kyuura_engine/markers.py)|2|
|[kyuura_engine/movement.py](../kyuura_engine/movement.py)|2|
|[kyuura_engine/persistent.py](../kyuura_engine/persistent.py)|1|
|[kyuura_engine/procedures.py](../kyuura_engine/procedures.py)|4|
|[kyuura_engine/reactions.py](../kyuura_engine/reactions.py)|7|
|[kyuura_engine/resolution/contract.py](../kyuura_engine/resolution/contract.py)|5|
|[kyuura_engine/resolution/flow.py](../kyuura_engine/resolution/flow.py)|18|
|[kyuura_engine/resolution/kernel.py](../kyuura_engine/resolution/kernel.py)|33|
|[kyuura_engine/resolution/preflight.py](../kyuura_engine/resolution/preflight.py)|5|
|[kyuura_engine/resolution/programs.py](../kyuura_engine/resolution/programs.py)|220|
|[kyuura_engine/resolution/questions.py](../kyuura_engine/resolution/questions.py)|1|
|[kyuura_engine/resolution/unbounded.py](../kyuura_engine/resolution/unbounded.py)|6|
|[kyuura_engine/stadiums.py](../kyuura_engine/stadiums.py)|1|
|[kyuura_engine/zones.py](../kyuura_engine/zones.py)|66|

内部ガードは各条件と関数名をJSONに列挙。原因が壊れた保存状態、テスト用のレジストリ、呼び出し側の直接変更、正常プレイの潜在不具合のどれかを、静的なraiseだけで確定しない。正常な操作列で到達した場合にのみAへ再分類し、再現盤面と固定seedを付ける。

本監査中、エンジンコードを意図せず変更した箇所はない。監査プローブの初版には決定段階とカードIDの指定ミスがあり、監査用スクリプトだけ修正した。これらの失敗をエンジンの不具合として数えていない。

実行前後のkyuura_engine・tests・tools・scriptsのSHA256は一致。既存文書・固定デッキ・参照データも変更していない。作成物はこの3文書のみ。

## 12. 凍結前に明示しておく未確認範囲

静的全件索引は完了したが、全項目の合法な到達性・全関連カード・全テストの実効カバレッジを確認したものではない。JSONのunknownと一次調査候補を、追加調査の残件として保持する。特に600内部ガード、756nullable候補の全件意味確認、代替回答探索256超の実カードからの完全詰まり再現、8件の静的テスト言及なしコードは残る。

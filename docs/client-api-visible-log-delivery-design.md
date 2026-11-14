# client_api の可視ログの配信（設計）: ポケモン交換おじさんの公開カードを GUI へ届ける

2026-11-14。調査・設計・文書化だけです。エンジン・client_api・GUI・judge・方策・データは変えていません。テスト・ビルド・対戦・judge・replay も実行していません（コード・文書・保存済みの応答の読み取りと静的解析だけ）。

- 前の単位: [v0.182 の実装](trader-reveal-identification-v0.182.md)。`return_to_deck`・`reveal_from_deck` に `card_id` を足し、エンジンの出来事と閲覧用記録は修正済みです。client_api のログの配信と GUI の表示は未実装でした（同じ文書 7 章の段階 2・3）。
- 証跡: `kyuura-engine-verification-vai/verifier/runs/trader-log-delivery-design/`（事前計画 `PLAN.md`、作業の記録 `commands.txt`、補助スクリプト `scripts/`、出力 `out/`）。

**結論**

- 既存の client_api（形式 1）には、閲覧者別のログを返す口がありません。`view` と `updates` は status と observation だけを返します。GUI の公開の基点（`2674efd`）の文書と README も同じ結論です（3 章）。
- 推奨は、各入口に読み取りだけの要求 `log` を加える案です（6 章の案 B）。
  - `ClientHub` が、受理のたびに閲覧者ごとの可視ログの「その時点の写し」を貯めます。
  - 位置は、閲覧用記録と同じ `(区間, ログの番号)` で示します。
  - 既存の応答（`view`・`updates`・`candidates` など）の形は変えません。形式の版は 1 のままで、要求の種類を 1 つ加えるだけです。
- 今の GUI の接続層は、`game_created` の `hidden.seed`（項目の名前だけ。値は null）を禁じた名前として応答全体を返しません。GUI の段階で、閲覧用記録の検査と同じ規則（`hidden` の中の名前は除く）に合わせる必要があります（5.4）。

## 1. 基点と識別

| 項目 | 値 |
|---|---|
| エンジンの基点 | `claude/trader-reveal-identification-v0182` の `3452000`（`34520004f1f3…`。origin と一致・変更 0。`origin/main` `7b3d53c` は祖先で、基点は main に入っていない） |
| 前の単位の配布の固定コミット | `95206ec9c52a3534b23ac10135b636513c57efe8`（0.182.0） |
| 前の単位のマニフェスト | 証跡の `sha256.json` の sha256 は `220739a4f5ad80256d8b0d0d3dca78148a49ef80128d41bc7638784b589ea44a`（前の単位の更新のあとの値と一致。前の単位の項目は 139、全体は 6677。`out/prior_reference.json`） |
| 作業 | 新しい worktree `C:\dev\kyuura-engine-lt20`、ブランチ `claude/trader-log-delivery-design`（文書だけ） |
| GUI の参照の基点 | `origin/feature/gui-energy-holder-label` の `2674efd`（`ls-remote` でも同じ。リモートで最も新しいブランチ。`origin/main` `434d1fa` から 18 コミット先で、main に入っていない） |
| GUI の作業ツリー | `C:/dev/kyuura-engine-gui-wt-0181eh`（`2674efd`）には、追跡するファイル 139 に未コミットの変更がある（追加と削除が同じ 20584 行で、改行の違いの見込み）。作業ツリーは読まず、`2674efd` の git のオブジェクトだけを読んだ（blob の一覧は `out/gui_blobs_2674efd.txt`） |
| 保護 | 利用者の main・lt5・既存の worktree（エンジン・GUI）は触っていない。GUI の何も変えていない |

## 2. 調べたもの

- エンジン（`3452000`）:
  - `client_api.py`・`legal_actions.py`・`adapter.py`・`observation.py`・`view_record.py`・`state.py`・`engine.py`・`replay_record.py`
  - `tools/verification_ai/judge.py`・`observe.py`
  - 文書: `client-api-v0.164.md`・`view-record-v0.155.md`
- GUI（`2674efd`）:
  - 接続層: `local_match.py`・`app.py`・`safety.py`
  - 画面の側: `api/transport.ts`・`validate.ts`・`types.ts`、`state/useEndpointSession.ts`・`logSummary.ts`、`components/Panels.tsx`、`App.tsx`、`cards/definitions.ts`
  - 契約と文書: `contract/kyuura-client-api-v1.json`・`docs/engine-contract.md`・`README.md`
- 静的解析（`scripts/scan_event_keys.py` → `out/event_keys_scan.json`。ソースを `ast.parse` で読むだけで、import しない）:
  - `add_event` の呼び出し 606、文字列の種類 372（動的な種類は 3）
  - 見える範囲の表: `PUBLIC_EVENTS` 338・`PRIVATE_FIELDS` 39。表にない種類は 0
  - 出来事の項目の名前 213 のうち、GUI の接続層の禁じた名前と重なるのは `seed`（`game_created`）だけ
  - `return_to_deck`・`reveal_from_deck` は公開、`search_deck` は非公開の項目あり
- 保存済みの閲覧用記録（`scripts/view_record_stats.py` → `out/view_record_stats.json`。vai のバッチの記録 177。JSON を読むだけ）:

  | 値 | 中央値 | 90% | 最大 |
  |---|---|---|---|
  | 1 局の出来事の数 | 514 | 1098 | 2191 |
  | 1 局の出来事の JSON | 約 35 KB | 約 129 KB | 約 304 KB |
  | 1 つの出来事の JSON | — | — | 233 バイト |
  | 1 回の受理で増える出来事 | 8 | — | 15 |
  | 閲覧者ごとの更新の項目の数 | 184 | — | 1001 |

  - 177 の記録のすべてに `hidden.seed` がある。
  - 交換おじさんの 2 種類の出来事は 24（どれも 0.181.0 の記録で `card_id` なし）。
  - 区間が 2 つ以上の記録は 0。

## 3. 現状の取得・更新の構造

### 3.1 エンジン（client_api 形式 1）

| 場面 | 今の仕組み | ログ |
|---|---|---|
| 初期の接続・観測 | `view`: `status`（`segment` をふくむ）と、その閲覧者の `observe` | なし |
| 送信のあと | `submit` の応答は本人の結果（`ActorDiagnostic`）だけ。受理（と処理できない結果）のときだけ、`ClientHub._on_result` が閲覧者（0・1・観戦者・ホスト）ごとに `update` を 1 つ作る（`number` と status と observation）。拒否では作らない | なし |
| 主体の切り替え | 入口ごとに主体が決まっている（要求で主体を選ぶ項目はない）。ホストの入口の観測は観戦者と同じ範囲 | — |
| 再取得・再接続 | `updates` は箱から取り出すと消える。同じ閲覧者の入口どうしで箱を共有する。`view` で今の観測を取り直す | なし |
| 履歴 | `client-api-v0.164.md` 6 章: 「履歴の表示には閲覧用記録（U5）を使う（このアダプタの応答には入れていない）」。契約だけで、機能は作っていない | なし |

- 可視ログの部品（`observation.py`）:
  - `visible_event(event, viewer)` は 1 つの出来事を 1 つの写しにします（見えない項目は除いて `hidden` に名前と枚数を書く。出来事そのものは除かない）。表にない種類は `ValueError` です。
  - 見えるかどうかは出来事と閲覧者だけで決まり（`PRIVATE_FIELDS` の判定の関数は `(event, viewer)`）、状態を読みません。例外は `_mask_face_down` です。これは**今の**状態のうらのカード（マチスの秘策）の uid を、過去の出来事からも伏せます。おもてにしたら、過去の出来事でも見えるようになります（3.3）。
  - ログの長さは、閲覧者によらず `state.log` と同じです。検証用 AI の `observe.py` も同じ前提です。
- 閲覧用記録（`ViewRecorder`）は、受理のたびに `visible_log` の新しい部分（`{"segment", "log_index", "event"}`）を JSON の写しとして固定します。後から遡って作り直しません。
  - 区間が変わったときは、前の区間の残りを `visible_segment_logs` から取ります。
  - ホストの側の部品で、client_api の応答ではありません。
- ログは `state.add_event` がタプルに足すだけです（書きかえない）。区間は `segment_index = len(segments)` で、0 から連続します。
- 拒否の結果の `state` は渡した状態そのものです（`CommandResult` の説明）。拒否ではログが増えません。

### 3.2 GUI（`2674efd`）

| 層 | 今の仕組み |
|---|---|
| 接続層 `LocalMatch` | 入口を Python の側で持ち、ブラウザには関連付けの識別子だけを渡す。要求のたびに hub の `updates` を取り出し、席ごとに最大 100 の更新を保持する（古いものから捨てる）。`GET …/updates?after=n` は `number` が `n` より新しいものを返す。保持の範囲の外なら `gap`。`updates` 以外の種類は、エンジンへそのまま渡す |
| 接続層 `safety.py` | ブラウザへの応答のどの深さにも、`view_record.FORBIDDEN_KEYS` と `state`・`snapshot` などの名前を含めない（含めば `GUI_RESPONSE_WITHHELD`）。`hidden` の中の名前の例外はない |
| `useEndpointSession` | 取り直し（refresh）は `view` → `candidates`（操作できる入口だけ）→ `updates(after)` の順。`gap` なら「保持範囲の外」と書き、`view` を基準にする。部品は `(対戦, 席)` ごとに `key` を変えて作り直す（切り替えると前の主体の状態は消える）。遅れた応答は世代の番号で捨てる |
| ログ欄 | `logSummary.ts` が、更新を 1 行の要約（段階・番・入力待ち・枚数）にする。エンジンの対戦ログは読まない |
| 文書 | `engine-contract.md`（51 行・85 行）と README の制限: 「client_api 形式 1 は閲覧者別の対戦ログを返さない。ログを出すなら、エンジンの契約に閲覧者別のログ（または閲覧用記録）の要求を加える必要がある」。`verifier`・`CommandResult`・hub の内部は使わない方針 |
| カードの名前 | `App.tsx` が `/api/cards` の表を `card_id` → 名前の `Map` で持つ（`loadCatalog`）。`validate.ts` は更新の項目の知らない名前を拒まない（coverage など一部だけ厳しい） |

**前回の結論の確認**: 「client_api は今ログを配らない」は、公開の基点（エンジン `3452000`・GUI `2674efd`）でも正しいです。

- GUI の側に、それに代わる取得口はありません。
- 保存済みの記録では、閲覧者ごとの更新の項目が中央値 184・最大 1001 です。接続層の保持（100）を超えるので、新しく開いた画面では `gap` が普通に起きます。更新に差分を付けるだけでは、過去のログを取り直せません。

### 3.3 既存の可視ログの「取得の時点の投影」

`visible_log(state, viewer)` を後の状態で呼ぶと、過去の出来事の uid の伏せ方が、その時点の状態で決まります。

- 出来事の時点でうらだったカードが後でおもてになると、過去の出来事の uid が見えるようになります。
- 逆に、後でうらになったカードの uid は、過去の出来事からも伏せられます。

このため、「接続したときに `visible_log` をまとめて返す」作り方は、5 章の条件（後の状態から過去を補わない・受け取った過去を書きかえない）を満たしません。閲覧用記録と同じく、受理の時点の写しを貯めることが必要な最小の変更です。

## 4. 主体別の情報の境界（配るもの・配らないもの）

| 配る | 配らない |
|---|---|
| 入口の閲覧者（プレイヤー 0・1 は本人、観戦者・ホストは観戦者）の `visible_event` の写し（受理の時点の `_mask_face_down` をふくむ）と、その位置 `(segment, log_index)` | 完全な記録（`state.log` そのもの・`replay_record`）・スナップショット・`CommandResult`・`verifier` |
| 区間の終わりのログは `visible_segment_logs` の写し（区間の終わりにうらだったカードの uid は見せない） | 非公開のカードの対応表（uid とデッキの並び・相手のデッキリスト） |
| 交換おじさんの 2 つの出来事の `card_id`（公開の出来事。書かれた時点の値） | パソコン通信の `search_deck` の `card`（`PRIVATE_FIELDS` で本人だけ。相手・観戦者には `hidden: {"card": null}`） |
| — | 本人だけの拒否の診断（`submit` の応答だけに残る。拒否ではログが増えないので、ログの位置・数からも伝わらない） |

- 位置と件数が明かすもの:
  - `log_index`・`end` は、その区間のログの長さです。`visible_event` は出来事を除かないので、どの閲覧者でも同じ値です。
  - 他人の非公開の出来事も、種類と `hidden`（項目の名前と並びの枚数）として、どの閲覧者にも 1 件ずつ届きます。これは観測の部品の既存の公開の約束（`observation.py` の冒頭・`PRIVATE_FIELDS`）で、閲覧用記録にも入っている値です。
  - したがって、位置・件数は、届く出来事の並び以上のことを明かしません。拒否はログを増やさないので、拒否の有無も伝わりません。区間の番号は `view` の `status.segment` で公開済みです。
- この配信で GUI に新しく届く情報:
  - 今まで GUI が受け取っていなかった、閲覧者別の出来事の並びそのもの（出来事の種類・順番・公開の uid と `card_id`・伏せた並びの枚数）です。
  - 観測（各時点の盤面の枚数）より細かい時間の粒度で、相手の手順（何回引いた・山札をさがした、など）が分かります。どれも `visible_event` が見てよいと定めた範囲です。
  - 交換おじさんでは、見せた時点に、もどしたカードと手に入れたカードの `(uid, card_id)` の組が 2 つ届きます。これは「相手に見せる」指示（PT6・PT13）どおりの公開です。
  - 公開の場のカードは、もともと観測で `(uid, card_id)` が分かります。uid はデッキの並びから決まるので、組が増えるほど相手のデッキリストの並びの手がかりは増えます。この性質は既存の公開（トラッシュ・場・ほかの公開の出来事）と同じ種類で、uid の方式全体の安全性はこの設計では証明していません。
- 方策・GUI に、ホストの内部の状態（`GameState`・`CommandResult`・`verifier`・hub の内部）を渡しません。ログを受け取るために、`candidates`・`inputs`・`check` を呼ぶ必要はありません。

## 5. 公開の時点・過去の情報

1. **生成の時点の値**: `card_id` は出来事を書いた時点の `state.cards[card].card_id` です（v0.182）。配信はその出来事の写しを渡すだけで、後の状態から補いません。
2. **受理の時点の写し**:
   - hub は受理のたびに、増えた出来事だけを、その時点の `visible_log`（区間が変わったら `visible_segment_logs`）から写して固定します（JSON の値の写し）。
   - 後でカードがおもてになっても・うらになっても、すでに貯めた写しは変えません（`ViewRecorder` と同じ性質）。
3. **新しく接続した主体**: 返すのは貯めた写しです。したがって、過去の出来事は受理の時点の公開の範囲のままです。
4. **hub を作る前のログ**（`ClientHub.from_state`。固定例・構築盤面・復元した状態）:
   - 作った時点の投影で写します（`ViewRecorder.attach` と同じ）。元の各時点の投影は作り直せません。
   - その境の位置を応答の `baseline_end` で示します。`ClientHub.start` で作った hub では、開始の直後の位置です。
5. **旧形式の出来事**: `card_id` のない `return_to_deck`・`reveal_from_deck`（0.181.0 以前の記録と、ほかの 18 の呼ぶ箇所）は、「見せたカード（識別の情報なし）」として扱います。観測・後のログ・完全な記録・カードの表から補いません。
6. **完全な記録からの補い**: しません。配信の値の出どころは、`visible_event` を通した写しだけです。

### 5.4 GUI の接続層の禁じた名前（GUI の段階で必要）

- `game_created` の `seed` は、だれにも見せない項目です（`_nobody`）。可視ログでは `{"hidden": {"seed": null}}` になります（値は出ない。名前だけ）。
- 閲覧用記録の検査（`view_record._forbidden`）は、`hidden` の中では名前を見ず、値が null か整数であることだけを確かめます。GUI の `safety.forbidden_paths` にはこの例外がないので、今のままでは最初の `log` の応答が `GUI_RESPONSE_WITHHELD` になります。
- GUI の段階で、`safety.py` に同じ規則（`hidden` の値が辞書なら、中の名前は禁じた名前として扱わず、値が null か真偽でない整数かだけを確かめる）を加えます。
- 静的解析では、禁じた名前と重なる出来事の項目は `seed` だけでした（そのほかの出来事の項目は禁じた名前と重ならない）。

## 6. 配信の方式の比較と推奨

| 比べる項目 | A. 初期の応答と更新に差分を付ける | **B. 専用の読み取りの口（位置から）** | C. 既存の取得口と更新の知らせの組み合わせ |
|---|---|---|---|
| 形 | `update` に、その受理で増えた可視ログを付ける。初期は `view` に全体を付ける | 入口に `log` を加える。hub が受理の時点の写しを貯め、位置から返す | `update` に差分だけを付け、GUI の接続層の 100 件の保持と `after` を使う |
| 初期・再接続 | `view` が呼ぶたびに全体を返す（最大 約 304 KB を取り直しのたびに）か、別の口が要る | 位置を指定して必要な分だけ返す | 保持の外（`gap`。中央値 184 件で普通に起きる）では過去のログを取り直せない |
| 受理の時点の値 | 差分は受理の時点。初期に `visible_log` を返すと今の状態での投影（3.3）になり、条件を満たさない | 貯めた写しだけを返す | 差分は受理の時点。取り直しの手段がない |
| 既存の応答の形 | `update`・`view` の形が変わる（旧 GUI の検査は知らない項目を拒まないが、契約の値は変わる） | 変えない（要求の種類と誤りのコードを 1 つずつ加えるだけ） | `update` の形が変わる |
| 更新の箱の性質 | 取り出すと消える箱に、ログの唯一の写しを載せる | 箱と別。読み取りだけで、何度でも同じ値 | A と同じ |
| GUI の変更 | `view`・更新の型と、`gap` のときの扱い | 1 つの要求と位置の管理 | 取り直しを諦める表示 |

**推奨: B。** 理由は 3 つです。

- 初期の取得・差分・再接続・閲覧者の切り替え・保持の外を、1 つの読み取り（位置から）で扱えます。
- 返すのは受理の時点の写しだけなので、5 章の条件を満たします。
- 既存の応答の形を変えないので、旧 GUI・検証用 AI（`updates` を記録する）に影響しません。

既存のもので足りるか（閲覧用記録をそのまま使う）も検討しました。`ViewRecorder` は受理の時点の写しを作る既存の部品です。しかし、ホストの側で `CommandResult`（完全な状態をふくむ）を受け取って作るものです。GUI の接続層は「hub の内部・`CommandResult`・`verifier` を使わない」方針（engine-contract.md 51 行）なので、そのまま GUI へ渡す取得口にはなりません。そこで B は、`ViewRecorder` と同じ手順（同じ関数 `visible_log`・`visible_segment_logs`・同じ位置 `(segment, log_index)`）を `ClientHub` の中で行い、client_api の要求として返します。新しい ID・汎用の配信の基盤は作りません。

## 7. API の仕様（案 B）

### 7.1 要求

| 種類 | 入口 | 項目 |
|---|---|---|
| `log` | プレイヤー・観戦者・ホスト | `from`（任意。`{"segment": 整数, "index": 整数}`） |

```json
{"contract": "kyuura-client-api", "format": 1, "type": "log"}
{"contract": "kyuura-client-api", "format": 1, "type": "log", "from": {"segment": 0, "index": 256}}
```

**`from` の検査**（どれも状態・貯めた写し・更新を変えない）:
- 次の場合は `CLIENT_FIELD_INVALID` です。
  - `from` が辞書でない
  - `from` の名前がちょうど `segment`・`index` の 2 つでない
  - 値が整数でない（`bool` は整数として扱わない）
  - 値が 0 未満、または 2**31 以上
- `from` を省くと、区間 0 の番号 0 から読みます。

### 7.2 応答

```json
{"contract": "kyuura-client-api", "format": 1, "type": "log", "ok": true,
 "entries": [{"segment": 0, "log_index": 256, "event": {"kind": "return_to_deck", "turn": 5, "player": 0, "card": 2, "card_id": "…"}}, "…"],
 "next": {"segment": 0, "index": 512},
 "end": {"segment": 0, "index": 530},
 "complete": false,
 "baseline_end": {"segment": 0, "index": 14}}
```

| 項目 | 意味 |
|---|---|
| `entries` | `from` から古い順に、最大 `MAX_LOG_ENTRIES`（256）。各項目は閲覧用記録の出来事と同じ形 `{"segment", "log_index", "event"}`。`event` はその入口の閲覧者の、受理の時点の写し |
| `next` | 次に送る `from`（最後に返した出来事の次の位置を、下の正規化をした値）。`entries` が空なら `from`（正規化した値） |
| `end` | 応答の時点で貯めた最後の位置の次（今の区間と、そのログの長さ）。`view` の `status.segment` と同じ区間 |
| `complete` | `next == end` |
| `baseline_end` | hub を作ったときの位置（5 章の 4）。これより前の出来事は作った時点の投影。hub を作ったあとは変わらない |

**位置の正規化**: `index` がその区間の長さと等しく、後ろに区間があるときは、`(segment + 1, 0)` に読みかえます（区間の終わりと次の区間の始まりは同じ位置）。

**範囲外**: `segment` が貯めた区間にない、または `index` がその区間の長さより大きいときは、新しい誤りのコード `CLIENT_LOG_POSITION_UNKNOWN`（決まった文「ログの位置がこの対戦の範囲にない」）を返します。

- 古い位置はありません。保持の上限がなく、すべての位置が読めます。
- 範囲外になるのは、別の対戦の位置か、GUI の誤りのときだけです。

**処理できない結果のあと**: `log` は状態を読まず、貯めた写しを返します（`CLIENT_GAME_UNAVAILABLE` にしない。8 章の判断 J4）。

- 処理できない結果では、出来事を足しません。`end` はその前の受理の位置のままです。

### 7.3 hub の中の手順（実装担当がそのまま書く粒度）

```text
定数: MAX_LOG_ENTRIES = 256、LOG_VIEWERS = (0, 1, None)   # ホストの入口は None（観戦者と同じ範囲）を読む

ClientHub.__init__(game):
  state = 包んだ対戦の今の状態
  for v in LOG_VIEWERS:
    self._log[v] = {}
    for s in visible_segment_logs(state, v):  self._log[v][s["index"]] = [_json({"segment": s["index"], "log_index": i, "event": e}) for i, e in enumerate(s["log"])]
    self._log[v][state.segment_index] = [_json({"segment": state.segment_index, "log_index": i, "event": e}) for i, e in enumerate(visible_log(state, v))]
  self._log_at = (state.segment_index, len(state.log))
  self._log_baseline = self._log_at

_on_result(actor, result):      # verifier の呼び出しのあと、拒否の return のあと（受理と処理できない結果だけ）、更新を作る前
  if result.state is None: 何もしない（処理できない結果）
  else:
    state = result.state; (seg, cursor) = self._log_at
    for v in LOG_VIEWERS:
      if state.segment_index != seg:
        logs = {s["index"]: s["log"] for s in visible_segment_logs(state, v)}
        self._log[v][seg] += 写し(seg, logs[seg][cursor:], 番号は cursor から)
        for s in range(seg + 1, state.segment_index):  self._log[v][s] = 写し(s, logs[s], 0 から)
        self._log[v][state.segment_index] = 写し(state.segment_index, visible_log(state, v), 0 から)
      else:
        self._log[v][seg] += 写し(seg, visible_log(state, v)[cursor:], 番号は cursor から)
    self._log_at = (state.segment_index, len(state.log))

_Endpoint._log(request):        # 状態を読まない（_hub._state() を呼ばない）
  v = この入口の閲覧者（プレイヤーは本人、観戦者・ホストは None）
  from を検査・正規化（7.1・7.2）→ 範囲外なら CLIENT_LOG_POSITION_UNKNOWN
  区間をまたいで古い順に MAX_LOG_ENTRIES まで集める
  応答 {"entries", "next", "end", "complete", "baseline_end"}（_envelope("log", ok=True, …)）
```

- 写しは `_json`（JSON の値の写し）で作り、貯めたあとは変えません。応答は貯めた値の写しで、貯めた値を外へ渡しません。
- 1 回の受理で 2 つ以上の区間が始まる場合も扱います。`ViewRecorder.add` は 1 つだけを扱いますが、ここでは上の `for s in range(...)` で扱います。
- `visible_log` は呼ぶたびにログの全体を写します（1 局で最大 約 2200 件・3 閲覧者）。受理 1 回あたりの手間は、`observe` を 4 回作る今の更新と同じ程度の見込みです（測っていない）。
- `visible_event` が表にない種類で `ValueError` を出すと、`_on_result` から例外が出ます。今の `ViewRecorder` と同じ前提（すべての種類が表にあることは既存のテスト `log_audit` が確かめる）で、捕まえて黙らせません。
- hub の入口を通らずに包んだ対戦へ直接送った操作は、契約の外です（更新と同じ）。次の受理で、その出来事もその時点の投影で写します。

### 7.4 取得の約束

| 場面 | 扱い |
|---|---|
| 初期の取得 | `from` なしで始め、`complete` まで `next` で続ける（1 局の最大 約 2200 件は 9 回） |
| 差分の取得 | 前の `next` を `from` に送る。返るのは、その位置から古い順。終わりは `end` |
| 同じ要求の再実行 | 同じ `from` には、同じ位置の同じ値を返す（貯めた写しは足すだけで変えない）。`end`・`complete` と、上限までの件数は、その間の受理で増えうる |
| 再取得・再接続 | 持っている `next` から読めば欠けも重なりもない。位置を失ったら `from` なしで始め直す（上限がないので、どこからでも読める） |
| 重なりの排除 | 受け取る側は位置 `(segment, log_index)` で比べ、持っている次の位置より前の項目を捨てる。次の位置より後から始まる応答は、受け取る側の誤りとして扱い、始め直す |
| 閲覧者の切り替え | 写しは閲覧者ごとに別。入口が違えば、同じ位置でも別の閲覧者の写しになる。位置の値は閲覧者によらず同じ（4 章）なので、位置そのものは情報を漏らさない。受け取る側は、閲覧者ごとに位置とログを別に持つ |
| 区間が変わる | 区間の終わりの位置は、次の区間の `(n, 0)` と同じ（正規化）。`entries` は区間をまたいで続く |
| 保持の上限 | なし（`state.log` と閲覧用記録と同じ。1 局で閲覧者ごとに最大 約 300 KB・3 閲覧者）。上限は設けないので「古い位置」の誤りもない |
| 1 回の応答の量 | 最大 256 件（1 件の最大 233 バイトで 約 60 KB）。分割は `next` で続ける |
| ゲームの終了後 | 読める（終局でも写しはそのまま） |
| 拒否のあと | 拒否ではログが増えないので、何も変わらない。本人の診断は `submit` の応答だけ |
| 処理できない結果のあと | 貯めた写しを返す（7.2） |

## 8. 採用の判断が要る事項と推奨値

| # | 事項 | 推奨値 | 代わりの案 |
|---|---|---|---|
| J1 | 方式 | B（専用の `log`） | A・C（6 章） |
| J2 | 形式の版 | 1 のまま（要求の種類と誤りのコードを足すだけ。既存の応答は同じ） | 2 に上げる（旧クライアントは影響を受けないので不要） |
| J3 | 1 回の上限 `MAX_LOG_ENTRIES` | 256 | 512（約 120 KB） |
| J4 | 処理できない結果のあとの `log` | 貯めた写しを返す | ほかの要求と同じ `CLIENT_GAME_UNAVAILABLE` |
| J5 | 範囲外の位置のコード | 新しい `CLIENT_LOG_POSITION_UNKNOWN` | `CLIENT_FIELD_INVALID`（GUI が自分の誤りと区別できない） |
| J6 | `baseline_end` | 含める | 含めない（構築盤面・固定例の過去を、受理の時点の値と区別できない） |
| J7 | ホストの入口 | 観戦者の写しを読む | ホストの入口では受け付けない |
| J8 | GUI の `safety.py` の `hidden` の例外 | 閲覧用記録の検査と同じ規則 | 接続層で `game_created` を除く（ログの位置がずれるので推奨しない） |

## 9. GUI への受け渡し（GUI の段階。今回は変えない）

- **接続層**:
  - `forward` は `updates` 以外の種類をエンジンへそのまま渡すので、`log` の口は加えなくてよいです（`POST /api/seat/{token}`・`/api/host/{token}`）。
  - 変えるのは `safety.py` の `hidden` の規則だけです（5.4）。接続層はログを貯めません（貯めるのは hub）。
- **`transport.ts`・`validate.ts`**:
  - `EndpointClient` に `log(from?)` を加えます。
  - 応答の検査: `entries` の各項目は `segment`・`log_index` が整数で、`event` はオブジェクト・`kind` が文字列。`next`・`end`・`baseline_end` は位置。`complete` は真偽。
  - `CLIENT_LOG_POSITION_UNKNOWN` は誤りのコードの表（契約の表 `client_error_codes`）に加えます。
- **`useEndpointSession`**:
  - 部品（`(対戦, 席)` の `key`）ごとに、次の位置 `logNext`（初めは null）と、表示用の行を持ちます。部品を作り直すと消えるので、主体・対戦は混ざりません。
  - `refresh` の最後（`updates` のあと）に、`complete` まで `log(logNext)` を続けます（1 回の refresh で最大 16 回）。
  - 各応答は世代の番号で確かめ、古い世代の応答は捨てます。
  - 項目は `logNext` と位置で比べて重なりを捨てます。`logNext` より後から始まる応答と `CLIENT_LOG_POSITION_UNKNOWN` は、`logNext` を null にもどし、行を捨てて、次の refresh で始め直します。
  - 別の対戦の応答: 対戦を作り直すと識別子が変わり、古い識別子は `GUI_SEAT_UNKNOWN` になるので、別の対戦の位置は届きません。
  - `log` は `candidates`・`inputs`・`check` を呼ばずに読めます。観戦者の入口でも読めます。
- **表示**（今回の目的に要る範囲だけ）:
  - `kind` が `return_to_deck`・`reveal_from_deck` の出来事だけを、ログ欄の「公開のログ（エンジン）」の行にします。
    - 「プレイヤー N が見せて山札にもどした: 〈名前〉」
    - 「プレイヤー N が見せて手札に加えた: 〈名前〉」
  - 〈名前〉の決め方:
    - `card_id` があり、表（`/api/cards` の `card_id` → 名前）にある: その名前
    - 表にない: 「カード定義にないカード（〈card_id〉）」
    - `card_id` がない: 「見せたカード（識別の情報なし）」
    - 観測・ほかの出来事・uid からは補いません。
  - ほかの種類の出来事は表示しません。全体のログの表示や、対戦の履歴の画面の作り直しはしません。
  - 拒否の診断（`notices`）とは別の欄・見出しにします。拒否はログに出ません。
  - この行を、送れるかどうか・`check` の門・候補の表示に使いません。相手の手札・山札の今の中身の推測にも使いません（観測の手札・山札の表示は今のまま）。
  - 出来事の項目 `effect`・`power` の有無で効果の名前を出す処理はしません（ほかの 18 の呼ぶ箇所の出来事は、`card_id` がなければ「識別の情報なし」）。

## 10. 互換性・版・識別

| 項目 | 影響 |
|---|---|
| client_api の契約・形式 | 形式 1 のまま（J2）。要求の種類 `log` と誤りのコード 1 つを加える。既存の要求・応答・`update`・`number` は同じ |
| 旧 GUI・旧クライアント | `log` を送らないので変わらない |
| 新しい GUI と旧エンジン | `CLIENT_REQUEST_UNKNOWN` になる。GUI はエンジンの版を固定してから追従する（11 章の順序） |
| エンジンの版 | `client_api.py` は識別の behavior のファイル（`replay_record.INSTRUMENTATION_FILES` に入っていない）なので、`behavior_digest` が変わる。版を上げる（0.183.0 の想定） |
| 検証用 AI | P1・P3 の basis のファイルは `client_api.py` をふくまないので、basis は変わらない。`TOOL_VERSION`・判定の規則・形式も変わらない。`updates` の形が同じなので、記録の形も同じ。計画の識別は版と behavior をふくむので、新しい計画で実行する |
| 旧記録・スナップショット・閲覧用記録 | 変えない。hub の写しは状態に入れない（スナップショットの形は同じ）。復元した状態から作った hub の過去のログは、作った時点の投影（`baseline_end`） |
| ゲームの処理 | 状態・乱数・ログ・決定・候補・受理の判定は変わらない（hub が読むだけ） |

## 11. テスト（将来）と段階

**エンジンの段階のテスト**（構築盤面と new_game）

| 種類 | 確かめること |
|---|---|
| 正 | 交換おじさんの 2 つの出来事が、使用者・相手・観戦者・ホストの `log` に、受理の時点の位置で、正しい `card_id` とともに届く |
| 負 | パソコン通信の `search_deck` は、相手・観戦者・ホストの `log` で `hidden: {"card": null}`。使用者には `card` |
| 負 | 拒否のあと、どの入口の `log` も `end`・内容が同じ。本人の診断は `submit` の応答だけ |
| 正 | 初期の取得（`from` なし）・差分（`next`）・上限 256 での分割・`complete` |
| 正 | 同じ `from` の再実行で、同じ位置の値が同じ |
| 正 | 再接続（新しい入口・同じ hub）で、前と同じ値。閲覧者の入口ごとに写しが別（同じ位置で、観戦者と本人の違いが PRIVATE_FIELDS のとおり） |
| 負 | 範囲外（大きい `index`・ない区間）で `CLIENT_LOG_POSITION_UNKNOWN`。型・名前・負の値で `CLIENT_FIELD_INVALID`。どちらも状態・写し・更新を変えない |
| 正 | 区間の変化（サドン・デスの延長戦。構築盤面）で、区間の終わりの正規化と、区間をまたぐ読み取り |
| 不変 | 公開の前の位置には `card_id` がなく、公開のあとの受理の写しは後の受理で変わらない。マチスの秘策のうらのカードが後でおもてになっても、前に貯めた写しの uid は伏せたまま（`ViewRecorder` と同じ値） |
| 旧形式 | `card_id` のない出来事（ほかの呼ぶ箇所）はそのまま届く |
| 一致 | `log` の内容が、同じ閲覧者の `ViewRecorder` の出来事と位置・値で一致する。`view` の `status.segment` と `end.segment` が同じ |
| 不変 | `log` を呼んでも、状態・乱数の指紋・ログ・更新の箱・`number`・候補の取っ手が変わらない。`log` を加える前後で、同じ操作の列の操作の結果・更新が同じ |
| 処理できない結果 | そのあとも、貯めた写しが返る（J4） |

**GUI の段階のテスト**:
- `safety.py` が `hidden.seed` を通し、`hidden` の値が文字列なら止める。
- 交換おじさんの行の表示: 名前・表にない・`card_id` なし。
- 重なりの排除・`gap` によらない取り直し、閲覧者の切り替えと遅い応答の破棄。
- 拒否の表示との区別。送信の門・check がログの行に依存しないこと。

**段階**（それぞれ別の単位・別のコミット）:

1. エンジン: `ClientHub` の写しと `log` の要求、上のテスト、版 0.183.0、配布の確かめ（固定コミット・wheel・Git の URL からの導入・スモーク）。
2. GUI: エンジンの依存を 1 の固定コミットにしたあとで、`safety.py`・`transport`・`validate`・`useEndpointSession`・ログ欄の交換おじさんの行と、そのテスト。
3. 監査（別の単位）: ほかの 18 の呼ぶ箇所の文面と公開。w1 の残り 6 分類・57 件。今回は完了していません。

## 12. 未確認・失敗・修正

- 未確認:
  - 推奨の案の実装での動作と、受理 1 回あたりの手間（測っていない）
  - 保存済みの記録にない、2 つ以上の区間の実際の値（記録は 0）
  - GUI の作業ツリーの未コミットの変更の中身（読んでいない）
  - uid の方式全体の安全性
- 失敗・修正: なし（読み取りと静的解析だけ。補助スクリプトは 1 回ずつ実行し、exit 0）。

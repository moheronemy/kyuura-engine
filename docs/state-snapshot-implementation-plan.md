# 状態スナップショット（U6）の実装計画

[仕様](state-snapshot-design.md)を実装するときの単位・依存・回帰テスト・完了基準です。v0.156 で案として作り、v0.157 で判断事項 6 件を採用して（`ADOPT-U6-IMPL`）、S1〜S4・S6 を実装しました（[state-snapshot-v0.157.md](state-snapshot-v0.157.md)）。S5 は実装していません（別の作業）。

<!-- generated:implementation-adoption begin -->
- `ADOPT-U6-IMPL`（2026-11-07・利用者）: U6 の S1〜S4・S6 の実装と、判断事項 6 件の採用（採用した内容は 8 章・実装計画 5 章の表）。S5（完全な記録の途中から再開して U4 で照らす）は別の作業
  - 判断事項: DS-CONSTRUCTED、DS-HALT-TEXT、DS-CHECK、DS-DEPTH、DS-RECORD-LINK、DS-INSTRUMENTATION
  - 実装した単位: S1、S2、S3、S4、S6（v0.157（kyuura_engine/snapshot.py。docs/state-snapshot-v0.157.md））
  - 実装しない単位: S5
<!-- generated:implementation-adoption end -->

表（`<!-- generated:… -->` の区画）は、仕様の JSON（[state-snapshot-design.json](state-snapshot-design.json)）と同じ元から `scripts/build_state_snapshot_design.py --write` で作ります。

## 1. 前提

- 採用済み: 仕様 3 章の原則（ADOPT-U6-PRINCIPLES）と、判断事項 6 件（ADOPT-U6-IMPL。5 章）。自動移行は採用していない
- 既存の機能を使う: 実装と環境の識別・確認値（`replay_record`）、安全な JSON の読み取り（`replay_record.read_json_object`）、再実行（`replay_run`）、乱数の JSON（`rng`）、規約集合の識別（`conventions`）、不変条件（`engine.check_invariants`）、再開先の確かめ（`engine.supported_decision_error`）
- エンジンの動作・不変条件を変えない。`engine.py`・`resolution/` にカード ID・モードの名前の分岐を加えない。例外を広く捕まえない（境界の内部エラーの扱いは adapter と同じ）
- 実装の識別の方式（`kyuura-package-files-sha256/1`）は変えない。新しいモジュールは今の分け方ではゲームの挙動の側に入る（v0.155 の文書 1 章）。分け方を変えるなら方式の名前を変える別の判断
- テストは固定の少数の盤面・seed と、構築盤面・合法な操作の列・補助関数だけの確かめを区別する。全 108 組・4,356 局・lockstep・ストレス実行を完了の条件にしない

## 2. 実装単位

<!-- generated:units begin -->
| 単位 | 状態 | 内容 | 依存 | 範囲 | 回帰テスト | 完了基準 |
|---|---|---|---|---|---|---|
| S1 | implemented | 型の対応表と書き出し（保存） | なし | 分類表から作る型の対応（型の印・列挙・タプルとリスト）、保存の前の境界の確かめ、書き出し | 分類表とコードの項目が名前で一致（この仕様の --check と同じ）<br>境界の外の状態（pending_moves・一時的な属性・不変条件）の保存を拒む<br>状態の最大の深さ（DS-DEPTH の材料） | 3 つの集合・F1〜F8 の盤面の状態を書き出せる<br>書き出しが状態を変えない |
| S2 | implemented | 読み取りと段 1〜4 | S1 | 安全な読み取り、形式と型、対応、登録データの解決 | F9 の不正・未知・非対応の入力を、段ごとに決めた結果で拒む<br>誤りの文に入力の値がない | 非対応・不正な入力で状態を作らない |
| S3 | implemented | 組み立てと段 5〜7 | S2 | GameState を値から組み立て、不変条件・整合・確認値・往復で確かめ、ホストへ返す | 往復で JSON が同じ<br>確認値・不変条件の違いを inconsistent で見つける | 部分的な状態を返さない<br>pickle・__setstate__ を使わない |
| S4 | implemented | 継続一致の検証 | S3 | 保存しない状態と、保存して復元した状態から同じ操作の列で続け、各境界で比べる（F の比べ） | F1〜F8 の各境界で、保存した全項目・確認値・ログ・観測・診断が同じ | 3 つの集合で同じ |
| S5 | planned | 記録との接続 | S4 | 完全な再現用記録の途中の行から、スナップショットで再開して残りを U4 で照らす（resume_from_snapshot） | 記録の k 行目のあとで保存→復元→残りの行が一致<br>違う記録・違う位置を見つける | U4 の結果の語彙に合わせる |
| S6 | implemented | ホストへの接続 | S3 | HostedGame・ReplayCollector・ViewHost から保存・復元する入口（閲覧者には渡さない） | 閲覧用記録・view_for にスナップショットの値が出ない<br>復元した対戦を続けた閲覧用記録が、保存しなかった場合と同じ | 見る人の値で検証者の情報が取れない |
<!-- generated:units end -->

## 3. 依存と推奨の順

```
S1 型の対応表と書き出し
 └─ S2 読み取りと段 1〜4
     └─ S3 組み立てと段 5〜7
         ├─ S4 継続一致の検証
         │   └─ S5 記録との接続（記録の途中から再開して U4 で照らす）
         └─ S6 ホストへの接続
```

推奨の順は S1 → S2 → S3 → S4 → S5 → S6。S4 までで「保存して復元した状態から同じ操作の列で続けると、各境界で同じ」ことを確かめられる。v0.157 は S1〜S4 と S6 を実装し、S5 を残した（S6 は S3 だけに依存する）。

## 4. 完了基準（U6 全体）

1. 分類表とコードの項目が名前で一致する（この仕様の `--check` を実装でも使う）
2. 3 つの集合（CS-KYUURA-CURRENT@1・CS-KYUURA-PLAY-S2A@1・CS-KYUURA-PLAY-PO@1）と F1〜F8 の盤面で、保存して復元した状態から同じ操作の列で続けたとき、各境界で、保存した全項目（スナップショットの JSON）・U3 の確認値・ログ・観測（0・1・None）・診断（outcome・status・識別・view_for）が、保存しないで続けたものと同じ
3. F9 の不正・未知・矛盾・非対応の入力を、段ごとに決めた結果で拒み、状態を返さない。誤りの文に入力の値・秘密の値を入れない
4. 停止の状態を復元しても停止を解除しない。規約集合を差し替える API がない
5. 閲覧用記録・`view_for` にスナップショットの値が出ない
6. 既存の API・3 つの集合の識別と照合値・U1〜U5 のテストが変わらない

JSON の往復だけを完了の基準にしない。OS・Python の版をまたぐ保証は、U3 の範囲（実装と major・minor が同じ）を超えない。

v0.157 の結果: 1・3・4・5・6 は S1〜S4・S6 の範囲で満たした。2 は 3 つの集合と F1〜F8 の盤面で確かめた（[state-snapshot-v0.157.md](state-snapshot-v0.157.md) 6 章）。S5 の完全な記録との接続は残っている。

## 5. 判断事項

推奨は、v0.156 の仕様案の作成者の提案です。v0.157 で利用者が 6 件を採用しました（DS-INSTRUMENTATION は推奨と違う選択肢）。採用した内容は表の右の列です。

<!-- generated:decisions begin -->
| ID | 問い | 選択肢 | 推奨（仕様案の作成者の提案） | 状態 | 採用した内容 |
|---|---|---|---|---|---|
| DS-CONSTRUCTED | 構築した盤面（new_game からでない状態）の保存を許すか | 許す（ホスト・テスト用。origin に印）<br>new_game からの状態だけ | 許す。復元の確かめは同じ。完全な記録との対応は origin で表す | adopted（ADOPT-U6-IMPL） | 構築盤面も、保存の境界と整合の確かめを満たせば保存できる。保存・復元できることと、new_game から合法に到達できることは別（到達できることは保証しない）。任意のカード定義・処理を入力から登録できる意味ではない |
| DS-HALT-TEXT | 停止の診断用の文（Halt.message・references）を保存するか | 保存する（状態の一部）<br>保存せず復元で空にする | 保存する（状態の一致を保つ。ホスト用なので閲覧者に出ない） | adopted（ADOPT-U6-IMPL） | 停止の理由の文（Halt.message・references）も完全な情報の一部として保存する。閲覧者への表示は診断 API の安全な文（public_halt）を使い、保存した文をそのまま見せない |
| DS-CHECK | スナップショットに確認値（期待値）を入れるか | 入れる（U3 の checks）<br>入れない | 入れる（復元の段 6 で照らす。入力ではない） | adopted（ADOPT-U6-IMPL） | 保存したときの確認値を入れる。復元の結果を照らすためのもので、署名・認証・改ざんの防止ではない（作り直せるので、構造・不変条件の確かめの代わりにしない） |
| DS-DEPTH | 入れ子の深さの上限 | 64（U3 と同じ）<br>状態に合わせて上げる | U6-S1 で状態の最大の深さを測ってから決める | adopted（ADOPT-U6-IMPL） | 実際の入れ子とエンコードの方式を確かめて固定の上限を決め、同じ上限を保存と読み取りに当てる（書き出せたものが上限で読めない状態を作らない）。決めた値は 5 章の limits |
| DS-RECORD-LINK | スナップショットと完全な再現用記録の対応 | origin に game_id・seq を書く（説明用）<br>記録の中にスナップショットを入れる | origin に書くだけ（記録の形式は変えない）。記録の途中から再開する機能は U6-S5 で別に作る | adopted（ADOPT-U6-IMPL） | 完全な再現用記録との対応は任意の補助情報（origin の game_id・seq）。スナップショットだけの復元に完全な記録を求めない |
| DS-INSTRUMENTATION | 記録・診断の部品の識別（instrumentation_digest）の違いを非対応にするか | しない（U3 と同じ）<br>する | しない（ゲームの挙動の識別だけで決める） | adopted（ADOPT-U6-IMPL） | 初版は記録・診断の部品の識別（instrumentation_digest）も一致を求め、違えば unsupported。互換性を推測しない（推奨と違う選択肢を採用） |
<!-- generated:decisions end -->

## 6. この計画でしないこと

- 旧形式（形式 1〜35・pickle）からの自動移行、すべての過去の版のスナップショットへの対応
- 異なる規約集合での再開、停止の解除、続行規約の追加
- 合法手・AI・画面・通信

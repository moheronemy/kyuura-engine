# v0.185: 化石の発掘の山札の側の card_id と、スロットゲームの束の card_ids

2026-11-15。[設計](fossil-slot-reveal-identification-design.md)の推奨値（J-F1・J-F2・J-S1・J-S2・J-3）を実装しました。見せる範囲・時点・相手は変えず、文面で見せたカードを API で識別できるようにしただけです。新しい裁定・ゲームの処理の変更はありません。GUI の追従・新しい対戦はしていません。

- 前の単位: [設計](fossil-slot-reveal-identification-design.md)・[0.184.0](reveal-identify-v0.184.md)・[静的な監査](reveal-call-sites-identification-audit.md)
- 証跡: `kyuura-engine-verification-vai/verifier/runs/fossil-slot-reveal-v0185/`（事前計画 `PLAN.md`、作業の記録 `commands.txt`、スクリプト `scripts/`、出力 `out/`・`scripts/tests/`・`smoke/`）

**状態**

| 範囲 | 状態 |
|---|---|
| 化石の発掘の山札の側 | 今回の明示の識別の対象。`reveal_from_deck` に見せたカード自身の `card_id` |
| 化石の発掘のトラッシュの側 | 既存の公開のまま（`retrieve_trainer` は変えていない。トラッシュは公開で、動く前の観測に uid と `card_id` の組がある） |
| スロットゲームの束 | 今回の識別の対象。`reveal_deck_top` に `card_ids` |
| GUI の束の表示・依存の更新 | 未実施（別の単位。6 章） |
| uid の方式全体 | 対象外 |

## 1. 基点・コミット・識別

| 項目 | 値 |
|---|---|
| 基点 | `claude/fossil-slot-reveal-design` の `fd53939`（origin と一致・変更 0・main に未取り込み。版 0.184.0） |
| 作業 | 新しい worktree `C:\dev\kyuura-engine-lt27`、ブランチ `claude/fossil-slot-reveal-v0185` |
| コミット | `b0aa599`（F 化石の発掘）・`8ea90fc`（S 束と新しいテスト）・`fa98012`（版を 0.185.0 にする。配布の確かめの固定コミット `fa98012f7534fe89667730ffa3e997342bde22a6`） |

**識別の前後**（`out/identity_before_fd53939.json`・`identity_after_fix_8ea90fc.json`・`identity_after_fa98012.json`。実測）

| 項目 | 前（0.184.0） | 修正のあと（版の前） | 後（0.185.0） |
|---|---|---|---|
| パッケージの版 | 0.184.0 | 0.184.0 | 0.185.0 |
| behavior_digest | `4aa17538…` | `ca3ff672…` | `a3b65dbe…` |
| instrumentation_digest | `d3436748…` | 同じ | 同じ |
| P1 の basis | `dc2ba8ff…` | `06ec1daf…` | `06ec1daf…` |
| P3 の basis | `02e3eb1e…` | `6a8287f9…` | `6a8287f9…` |
| `TOOL_VERSION`・道具の識別 | 10・`7b56ed5a…` | 同じ | 同じ |
| 判定の規則・計画と完了の形式 | 8・6 | 同じ | 同じ |

- basis の変化は `effects.py` の変更によります（どちらの basis の対象のファイルにも `effects.py` がある）。basis の範囲は変えていません。旧 basis との不一致を例外にしていません。
- 旧記録・snapshot・検証用 AI の計画は、それを作った版の実装に結び付いたままです（移行・再開・識別の書き換え・旧イベントへの項目の追加はしない）。

## 2. 変更

| 論点 | 箇所（クラスと呼び出しで特定） | 変更 |
|---|---|---|
| F | `effects.py` `SearchNamedFromDeckOrDiscard.resume` の山札の側の `reveal_deck_to_hand` | `identify=True` を渡す（`zones.py` の既定は `False` のまま） |
| S | `effects.py` `RevealDeckTopTakeSameNamed.resolve` の `state.add_event("reveal_deck_top", ...)` | `card_ids=tuple(state.cards[uid].card_id for uid in cards)` を足す |

- F の出来事: `{"kind": "reveal_from_deck", "turn", "player", "card", "card_id"}`（0.184.0 の 17 か所と同じ形。見せたカード自身の `card_id` だけ）。
- S の出来事: 既存の `kind`・`turn`・`player`・`count`・`cards`・`trainer_card` に `card_ids` を足した。
  - `len(card_ids) == len(cards) == count`（3）。`card_ids[i]` は `cards[i]` のカードの ID。
  - 同じ名前・同じ ID のカードも位置ごとに並ぶ（まとめない・並べかえない）。一部だけの値は作らない。
  - 順は `cards`（切ったあとの山札の上からの順）と同じというだけで、あとの山札の順を保証する意味はない。
  - 書く時点は、1 回目に切ったあと・手札に加える前（既存の処理順のまま）。あとの状態から補わない。
- 名前・画像・山札全体・uid の対応表は足していません。`reveal_deck_top` の生成はパッケージの中でこの 1 か所だけです（テストで固定）。
- 変えていないもの: カードの移動・山札の順・切る・乱数の消費、決定・候補・入力・check・受理、TOP1（3 枚より少ない山札）、本人だけの束、パソコン通信・`reveal=False` の検索、client_api・閲覧用記録・snapshot の形式の番号、judge・runner・方策・カードデータ・裁定、GUI。

## 3. 主体別の公開と時点

| 主体 | F | S |
|---|---|---|
| 使った本人 | 前から知っている（決定の選べるもの）。出来事に `card_id` が加わる | 束の uid は前から見えていた。`card_ids` が加わる |
| 相手・観戦者 | 受理の時点の `log` で識別できる（新しく） | 受理の時点の `log` で、手札に加えたカードも山札にもどしたカードも識別できる（新しく） |
| ホスト | 観戦者の写しと同じ | 同じ |

- 選ぶ前（化石の発掘の決定の時点）は、本人以外に決定の種類と決める人だけが届き、選べるもの・その数・uid と `card_id` の組は届きません。
- スロットゲームには決定がなく、受理の前に束の出来事はありません。
- 4 つの入口の値は同じで、3 閲覧者の閲覧用記録と `log` は一致します。あとの受理（番を終える）のあとも、前に固定した `log` の項目は同じです。

## 4. テスト

**新しいテスト** `tests/test_fossil_slot_reveal_v0_185.py`（14。盤面は既存のテストの盤面の関数。構築盤面で、new_game からの到達の実績には数えない。進め方は v0.184 のテストの `Run`・`Recorder` を再利用）

| 設計の番号 | テスト |
|---|---|
| F1・F2・F3 | 山札から選んだカードの `card_id`（4 つの入口）・選ぶ前の非公開（選べるものの数も）・選ばなかった山札のカードが出ない・前の項目の不変 |
| N2 | トラッシュの側（`retrieve_trainer` の項目が同じ・見せるヘルパーを通らない・動く前の観測に組）、選ばない・選べるものなし、ポケモンタワーの下で山札から選ぶ（F と同じく `card_id`） |
| S1〜S4 | 同じ名前 2 枚と 1 枚・同じ ID 3 枚・同じ名前なし・山札 6 枚の上 3 枚・名前の表記ゆれ（別の ID の同じ名前）。長さ・順・位置ごとの値、加えたカードと同じ位置の値、もどしたカードの識別、公開の前に出来事なし |
| S5 | `reveal_deck_top` の生成が 1 か所で、`card_ids` を書く |
| N1 | 山札 2 枚: カーネルで TOP1（状態・ログ・乱数が同じ）、hub で受理されず `log` が増えない |
| N3 | 本人だけの束の代表（マスターボール・新ポケモン図鑑HANDY808）: 相手・観戦者・ホストに `cards` は `hidden`、組も `card_ids` も届かない。パソコン通信・`reveal=False`・ポケモンギア・みずかきの対照は v0.184 のテストにあり、重ねていない |
| N5 | `card_ids` のない旧形式の束をふくむ閲覧用記録が読み込め、検査の結果が同じ（補わない） |
| N6 | 化石の発掘の山札の側だけが `identify=True`、トラッシュの側は `retrieve_trainer` のまま |

- **修正前のソース**（`fd53939` に新しいテストだけを置いた状態）では 14 のうち 10 が失敗し、どれも `card_id`・`card_ids` がないことで落ちました（`scripts/tests/prefix_new_test/`）。残る 4 つは非公開・変えない部分の対照です。F の段階では S の 7 つだけが失敗し（`stage_F`）、S のあとは 14 とも成功しました。

**既存のテストの期待**（新しい項目に合わせた最小の更新。旧の期待は docstring・コメントに残した）

- `tests/test_reveal_identify_v0_184.py`: `test_fossil_excavation_unchanged`（化石の発掘は既定 → 山札の側だけ `identify=True`）・`ScopeTest.test_identify_true_sites`（19 → 20）・`test_a_slot_game_taken_cards_only`（束に `card_ids`）
- `tests/test_trader_reveal_identification_v0_182.py` `test_only_trader_passes_identify`（許した一覧に化石の発掘を足した）
- `tests/test_preset_decks_v0_20.py`（版）

**関連のテスト**（モジュールごとに別のプロセス。UTF-8・`PYTHONDONTWRITEBYTECODE=1`。JUnit と終了コードは `scripts/tests/`）

| 実行 | モジュール | 失敗 |
|---|---|---|
| `stage_S`（新しいテスト・v0.184・v0.182・v0.80・v0.131・v0.73・v0.74） | 7（197 テスト） | 0 |
| `related_a`（トレーナー・v0.122・v0.135・v0.47・v0.126・v0.95・client_api・可視ログ・閲覧用記録・snapshot・snapshot の再現・観測・決定の監査・effects・パソコン通信・v0.53・検証用 AI の v2_repeat） | 17 | 0 |
| `related_b`（既存の効果の対戦の束 v0.28・v0.29） | 2 | 0 |
| `version_bump`（preset_decks_v0_20・distribution・新しいテスト） | 3 | 0 |
| `docs`（README・実装状況などの文書を読むテスト。文書の更新のあと） | 19 | 0 |

- 検証用 AI の行動・契約の指紋（v2_repeat の固定値）は変えずに成功しました（差なし。固定値を先に変えていない）。
- 全体のテスト・GUI・E2E・新しい対戦・seed の探索・旧記録の judge・replay はしていません。

## 5. 修正前後の比較（`scripts/dump_cases_v0185.py`・`compare_v0185.py` → `out/compare_before_after.json`）

18 事例（化石の発掘 6・スロットゲーム 6（TOP1 をふくむ）・非公開の対照 6）を、修正前（lt26 = `fd53939`）と修正後（lt27 = `8ea90fc`）で別のプロセスで実行し、各段の値を比べました。

- 比べた値: 候補・inputs・check・送信の結果（outcome・refusal・本人の結果）・両者の手札・山札・トラッシュ・サイドの並び・乱数の指紋・決定の通し番号・ログの長さ・4 つの入口の log・view・更新・3 閲覧者の閲覧用記録（各段と始めの時点）。
- 取っ手（`game`・`revision`。`secrets` の乱数）だけを同じ記号に置きかえました（各側 62 か所）。ほかは何も除かず、差を項目ごとに分類しました。
- 結果: 許した 2 種類の差だけ。化石の発掘の `card_id` 14 か所（山札から選ぶ 2 事例 × 7（4 つの log・3 つの閲覧用記録））、束の `card_ids` 35 か所（5 事例 × 7）。値はすべて本当のカード（各事例の始めの状態の uid → card_id。前後で同じ）と一致（119 値・照合できなかったもの 0）。ほかの差は 0。
- トラッシュの側・選ばない・選べるものなし・タワーの下で選ばない・TOP1・非公開の対照 6 は差 0。

## 6. 配布の確かめ（固定コミット `fa98012`）

1. `git ls-tree` の `kyuura_engine` の数: 62（`a9add68` と同じ）。パッケージの差は `__init__.py`・`effects.py`。`pyproject.toml` の差は版の 1 行で、依存は増えていません。
2. `git archive fa98012` の展開から wheel を作りました（`pip wheel --no-deps`: exit 0。`kyuura_engine-0.185.0-py3-none-any.whl`・sha256 `7b9d8cd1…`）。`scripts/check_distribution.py --wheel`: exit 0（required=62・problems=0）。
3. スモーク用のスナップショット: 同じ展開から、この版で新しく作りました（化石の発掘・スロットゲーム・パソコン通信。旧版のスナップショットは使っていない）。
4. リポジトリの外（scratchpad）の新しい venv に `pip install git+https://github.com/moheronemy/kyuura-engine.git@fa98012…` で導入しました（exit 0。入ったのは kyuura-engine 0.185.0 と pip だけ）。
5. スモーク（`scripts/smoke_v0185.py`。tests を使わない）:
   - 導入物: site-packages から読み込み、direct_url は vcs の commit `fa98012…` で editable ではない、`requires` なし・62 ファイル・識別はソースと一致
   - 化石の発掘: 4 つの入口の `reveal_from_deck` に正しい `card_id`
   - スロットゲーム: 4 つの入口の束の `card_ids` が正しく、加えた 2 枚が同じ位置の値と一致
   - パソコン通信: 相手・観戦者・ホストに `hidden` のまま（使用者には `card`）
   - ソースの木と導入物で結果（`result_sha256` `00c4368e…`）が同じ

## 7. GUI への引き継ぎ（未実施）

- 化石の発掘: 既存の「見せたカード」の欄（`reveal_from_deck`）でそのまま表示できる見込み。依存の固定の更新と、契約の表の説明（「化石の発掘は持たない」）の直しが要る。
- 束（`reveal_deck_top`）: 今の GUI は表示も検証もしていない。最小の追従:
  - 契約の表の `identified_events` に `reveal_deck_top` を足す
  - 検証: `card_ids` があるなら文字列の配列で、長さが `cards` と同じ（`cards` の要素は整数か、うらのカードの伏せの `null`）。一部だけの値（`null` の要素）は受け付けない
  - 表示: 「（プレイヤー）が山札の上から 3 枚を見せた: 名前 ID・…」を出来事の並びの順に 1 行（見せた人は出来事の `player`。順に山札の順の意味を持たせない）
  - `card_ids` がない旧形式: 「見せたカード（識別の情報なし）」のまま（推測しない）。カード名表にない ID は 1 枚ごとに「カード定義にないカード（ID）」
  - `baseline_end` より前の出来事の注記と、閲覧者ごとのログの分け方は今のまま
- 広げないこと: 全部の出来事の履歴・相手の今の山札の復元・名前からの推論。

## 8. 失敗・修正・再実行・未確認

- 失敗・修正・再実行（どれも道具の側。製品のコードの期待を変えて通したものはない。前の出力は `out/attempt1_*`）:
  1. 補助の出力を `python -I` で書いたとき、`-I` が `PYTHONUTF8` を無視して表示の写しが cp932 になった（JSON は UTF-8）。`-X utf8` に直して書き直した。テストの実行の補助にも `-X utf8`・`PYTHONUTF8=1` を足した。
  2. 比較の 1 回目は、本当のカードを観測の組だけから引き、山札にもどした束のカードの値 56 を照らせなかった（差の判定は ok）。事例の始めの状態の uid → card_id（検証者用）を書き出すようにして、前後とも書き出し直し、2 回目で 119 値すべてを照合した。
  3. 配布の wheel の 1 回目に `--no-build-isolation` を付け、setuptools がなく失敗した（exit 2）。前の単位と同じ（隔離あり）に直して成功。展開の 1 回目は msys の tar が Windows のパスを開けず失敗し、`git archive -o` と Python の `tarfile` に直した。
  4. 主体別の表（`scripts/publication_matrix.py`）の 1 回目は、決める人をプレイヤー 0 と決めつけ、みずかきの相手の決定（決める人は相手）と、HANDY808 の数だけの項目（中身は見せない）を問題として数えた（4 行）。決める人を決定の `player` にし、決める人でない入口に選べるものが届かないことを確かめる形に直した 2 回目で、問題 0（124 行）。製品の値は修正前と同じ（5 章で差 0）。
- 未確認: GUI の画面、new_game からの到達、全体のテスト、同じ効果のほかのカード（スロットゲーム・化石の発掘は 1 枚ずつで、共有のカードはない）。

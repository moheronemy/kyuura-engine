# v0.184: 見せる 17 の呼ぶ箇所で、見せたカードの card_id を出来事に書く

2026-11-15。[再現と修正の設計](reveal-call-sites-repro-fix-design.md)で公開の不足を再現した 17 の呼ぶ箇所に、既存のヘルパーの `identify=True` を渡しました（0.182.0 の交換おじさんと同じ引数）。新しい裁定・ゲームの処理の変更はありません。GUI の追従・新しい対戦はしていません。

- 前の単位: [18 の呼ぶ箇所の静的な分類](reveal-call-sites-identification-audit.md)・[0.182.0 の交換おじさん](trader-reveal-identification-v0.182.md)・[0.183.0 の log](client-api-visible-log-v0.183.md)
- 証跡: `kyuura-engine-verification-vai/verifier/runs/reveal-identify-v0184/`（事前計画 `PLAN.md`、作業の記録 `commands.txt`、スクリプト `scripts/`、出力 `out/`・`scripts/tests/`・`smoke/`）

**状態**

| 範囲 | 状態 |
|---|---|
| 今回の 17 の呼ぶ箇所 | 実装した。それぞれ構築盤面で実際に通し、4 つの入口の log と閲覧用記録で確かめた（20 事例） |
| 同じ呼ぶ箇所を通るほかのカード | 同じ行・同じ分岐を通るので同じ修正がかかる（共有の処理による裏づけ）。実行はしていない（3 章） |
| GUI | 既存の表示（`7a4b3d9` の「見せたカード」の欄）で扱える見込み。0.184.0 への依存の更新・限定の確かめは未実施 |
| 化石の発掘 | 判断待ち（既定のまま。テストで確かめた） |
| スロットゲームの束全体（`reveal_deck_top`） | 未修正（加えたカードだけを識別できるようになった） |
| uid の方式全体 | 今回の対象外 |

## 1. 基点と識別

| 項目 | 値 |
|---|---|
| 基点 | `claude/reveal-call-sites-repro` の `bf9efd7`（origin と一致・変更 0。`origin/main` は祖先、main に入っていない。版 0.183.0） |
| 作業 | 新しい worktree `C:\dev\kyuura-engine-lt25`、ブランチ `claude/reveal-identify-v0184` |
| コミット | `3d2ebbf`（A トレーナー）・`0987780`（B 特殊能力）・`59b1f23`（C ワザの要素）・`a9add68`（版を 0.184.0 にする。配布の確かめの固定コミット `a9add68b1e56a574e9bc1672951d48cad2b3b814`） |

**識別の前後**（`out/identity_before.json`・`identity_after.json`。実測）

| 項目 | 前（0.183.0） | 後（0.184.0） |
|---|---|---|
| behavior_digest | `fc76af65…` | `4aa17538…`（変わる） |
| instrumentation_digest | `d3436748…` | 同じ |
| P1 の basis | `a83547d8…` | `dc2ba8ff…`（変わる。対象のファイルに `effects.py` がある） |
| P3 の basis | `0a8f7530…` | `02e3eb1e…`（変わる。同上） |
| `TOOL_VERSION`・道具の識別 | 10・`7b56ed5a…` | 同じ |
| 判定の規則・計画と完了の形式 | 8・6 | 同じ |

- `resolution/programs.py` は、P1・P3 のどちらの basis の対象のファイルにも入っていません（`tools/verification_ai/judge.py` の `LOST_TARGET_BASIS_FILES`・`LOST_TARGET_P3_BASIS_FILES`）。basis の変化は `effects.py` の変更によるものです。basis の範囲は変えていません。
- 旧記録・snapshot・検証用 AI の計画は、それを作った版の実装に結び付いたままです（移行・再開・識別の書き換えはしない）。0.184.0 では新しい計画で実行します。

## 2. 変更（17 か所）

対象は再現の文書の対応表です。今のソースで、クラス・ヘルパー・呼び出しを AST で特定し（行番号では決めない）、呼び出しに `identify=True` を足しました（`scripts/patch_identify.py`）。ヘルパー（`zones.py`）と既定値 `False`、交換おじさんの 2 か所は変えていません。

| まとまり | クラス（効果）・ヘルパー |
|---|---|
| A トレーナー 8（effects.py） | `SearchDeckTrainer`（`reveal=True` の分岐。山をさがすトレーナー）・`LookTopTakePokemonThenShuffle`（マスターボール）・`CoinsSearchBasicEnergyPerHeads`（エネルギーアーク）・`ReturnHandEnergyThenCoinSearchBasicEnergy`（エネルギー増幅装置。もどす `return_hand_to_deck`・加える）・`RevealDeckTopTakeSameNamed`（スロットゲーム。加えるカードだけ）・`LookTopTakeTrainerThenShuffleLock`（ポケモンギア）・`BreederCoupleSearch`（ポケモン育て屋夫婦） |
| B 特殊能力 3（effects.py） | `SearchEvolutionCardToHand`（しんかのひかり）・`EachPlayerSearchToolOnEntry`（おくりもの）・`SearchDeckWithBenchLettersToHand`（［FIND］・［JOIN］） |
| C ワザの要素 6（resolution/programs.py） | `RevealPokemonFromDeck`（でんれい）・`RevealNamedPokemonFromDeck`（くらげのむれ・りゅうのきずな）・`RevealTrainerFromDeck` の 2 か所（おつかい・ひらめく・おつきみ／みんなでおどる）・`ReturnHandThenRevealEnergy`（てじな）・`EachPlayerLooksTakesBasicEnergy`（みずかき） |

- 出来事（`reveal_from_deck`・`return_to_deck`）に、見せたカード自身の `card_id`（出来事を書く時点の `state.cards[card].card_id`）が 1 つ加わるだけです。出来事の種類・uid・順序・ほかの項目（`effect`・`power`）は同じです。
- 2 つの出来事は公開（`PUBLIC_EVENTS`）なので、受理の時点に、持ち主・相手・観戦者・ホストへ同じ値が届きます（0.183.0 の `log` と閲覧用記録）。配信・観測・client_api の形式は変えていません。
- `engine.py`・`resolution/` にカード ID による分岐は加えていません（C は要素の呼び出しに引数を足すだけ）。
- 対象外（変えていない）: 化石の発掘（`SearchNamedFromDeckOrDiscard`）・スロットゲームの束の `reveal_deck_top`・見せないもどし（`hand_to_deck`）・`reveal=False` の検索（`search_deck`）・パソコン通信。

## 3. テスト

**新しいテスト** `tests/test_reveal_identify_v0_184.py`（20）

- 盤面は再現の単位と同じ既存のテストの盤面の関数です（構築盤面。new_game からの到達の実績には数えない）。
- 17 か所それぞれについて（20 事例。くらげのむれとりゅうのきずな、おつかい・ひらめく・おつきみは別の事例）:
  - 呼び元を記録する包みで、その呼び出しを実際に通ったことと、受理した状態への呼び出しであることを確かめる
  - 持ち主・相手・観戦者・ホストの `log` の、その出来事に正しい `card_id`。その入口に届いた値で uid と card_id の組が分かる
  - 選ぶ前（その段の前までに届いた値）には、持ち主以外に組がない
  - 3 閲覧者の閲覧用記録と `log` が一致。ホストは観戦者と同じ
  - 後の段のあとも、前に固定した `log` の項目は同じ
- 非公開の対照:
  - ポケモンギアの見た束（`look_at_deck_top` は相手に `hidden` で枚数だけ）と、選ばなかったトレーナー
  - みずかきの相手の見た束
  - てじなの見せないもどし（`hand_to_deck` の `cards` は伏せたまま。`card_id` なし）
  - エネルギー転送（`reveal=False`）とパソコン通信（17 か所のヘルパーを通らず、`search_deck` は `hidden: {"card": null}`）
  - スロットゲームの束の `reveal_deck_top`（`card_id` なしのまま）
  - 化石の発掘（呼び出しに `identify` がないまま）
- 補助の確かめ: `identify=True` を渡す呼び出しの一覧（交換おじさん 2 とこの版の 17）と、ヘルパーの既定値。合否は上の公開の値で決め、数だけでは決めていません。
- **修正前のソース**（`bf9efd7` に新しいテストのファイルだけを置いた lt25）では 20 のうち 19 が失敗し、どれも相手の `log` の出来事の `card_id` が None で落ちました（`out/new_test_on_prefix_bf9efd7.txt`。残る 1 つは既定値の確かめ）。修正後は 20 とも成功しました。

**共有の範囲**（実行していないカード。同じ行・同じ分岐を通ることは静的な対応表から）

- `reveal=True` の山をさがすトレーナーのほかの 10 枚
- マスターボールのほかの 4 枚
- ［JOIN］
- りゅうのきずなの同じデータの 1 枚
- おつかいの同じデータの 2 枚

**既存のテストの期待**

- `tests/test_trader_reveal_identification_v0_182.py` の「`identify=True` は交換おじさんだけ」を、交換おじさんの 2 つがあること・渡す箇所が許した一覧の中だけにあること・化石の発掘が既定のままであることに直しました（旧の期待は docstring）。
- 2 つの出来事に触れるほかの既存のテスト（32 のモジュール）は、修正後に期待を変えずに成功しました。この 17 か所の出来事の形をそのまま比べている既存のテストはありませんでした。

**関連のテスト**（モジュールごとに別のプロセス。PowerShell・`MSYS=noglob`・UTF-8・`PYTHONDONTWRITEBYTECODE=1`。JUnit と終了コードは `scripts/tests/`）

| 実行 | モジュール | テスト | 失敗 |
|---|---|---|---|
| `events_first`（2 つの出来事に触れるテスト。修正後のコード） | 32 | 1128 | 0 |
| `related_final`（client_api・閲覧用記録・snapshot・検索・観測・配布・検証用 AI の v2_repeat・盤面の出どころ。最終のコード） | 17 | 421 | 0 |
| `version_bump`（preset_decks_v0_20・distribution・新しいテスト） | 3 | — | 0 |

- 検証用 AI の行動・契約の指紋（v2_repeat の固定値）は変えずに成功しました（差なし）。
- 全体のテストは実行していません。

## 4. 修正前後の比較（`scripts/dump_cases.py`・`compare_dumps.py` → `out/compare_before_after.json`）

再現の単位の 22 事例（D の 19・非公開の対照 2・交換おじさん 1）を、修正前（lt24 = `bf9efd7`）と修正後（lt25）で別のプロセスで実行し、各段の値を比べました。

- 比べた値: 候補・inputs・check・送信の結果と本人の結果・両者の手札・山札・トラッシュ・サイドの並び・乱数の指紋・決定の通し番号・ログの長さ・4 つの入口の log・view・更新・3 閲覧者の閲覧用記録。
- 取っ手（`game`・`revision`）は `secrets` の乱数なので、値が文字列のこの 2 つの項目を同じ記号に置きかえてから比べました（各側 110 か所）。
- 意図した差の扱い: 2 つの出来事の `card_id` だけを両側から取り除いて比べました。修正前にあった `card_id` は交換おじさんの事例の 21 か所だけ。ログ全体を比べる対象から外していません。
- 結果: 22 事例すべてで、ほかの差は 0。修正後に足した `card_id` は 238 か所（log・閲覧用記録・観測の写しのうち出来事をふくむ所）で、値の誤りは 0（その uid の観測の組と照合）。対照 2 事例に足した `card_id` は 0。
- したがって、カードの移動・山札と手札の並び・乱数・決定・候補・inputs・check・送信の結果・ほかの出来事と非公開の情報は変わっていません。

## 5. 配布の確かめ（固定コミット `a9add68`）

1. `git ls-tree` の `kyuura_engine` の数: 62（`0529041` と同じ）。`pyproject.toml` の差は版の 1 行で、依存は増えていません。
2. `git archive a9add68` の展開から wheel を作りました（`pip wheel --no-deps`: exit 0。`kyuura_engine-0.184.0-py3-none-any.whl`・sha256 `fba6866e…`）。`scripts/check_distribution.py --wheel`: exit 0（required=62・problems=0）。
3. スモーク用のスナップショット: 同じ展開から、この版で新しく作りました（A マスターボール・B しんかのひかり・C くらげのむれ・対照のパソコン通信。旧版のスナップショットは使っていない）。
4. scratchpad の新しい venv に `pip install git+https://github.com/moheronemy/kyuura-engine.git@a9add68…` で導入しました（exit 0。入ったのは kyuura-engine 0.184.0 と pip だけ）。
5. スモーク（`scripts/smoke_v0184.py`。tests を使わない）:
   - 導入物: site-packages から読み込み、direct_url は vcs の commit `a9add68…` で editable ではない、`requires` なし・62 ファイル・識別はソースと一致
   - A・B・C の 3 つとも、4 つの入口の log の出来事に正しい `card_id`
   - パソコン通信は、相手・観戦者・ホストに `hidden` のまま（使用者には `card`）
   - ソースの木と導入物で結果（`result_sha256` `2358e742…`）が同じ

## 6. GUI への引き継ぎ（未実施）

- `7a4b3d9` の「見せたカード」の欄は、出来事の種類（`return_to_deck`・`reveal_from_deck`）だけで表示し、`card_id` があればカードの名前表で引きます。検査は `effect`・`power` などのほかの項目を拒みません（再現の文書 8 章で読んだ）。
- 0.184.0 への依存の更新と、限定の確かめ（実際の応答・画面）は、GUI の側の別の単位です。

## 7. 前回の件数の訂正（再現の単位）

再現の文書の「17 か所の 20 事例」は誤りで、正しくは 19 事例です（6・7 のエネルギー増幅装置は 1 つの事例で 2 か所を通る）。実行の全体は、D の 19 事例（段 47・対象のカード 26）、非公開の対照 2（段 5）、交換おじさんの道具の対照 1（段 3）の、合わせて 22 事例・55 段です（`reveal-call-sites-repro/out/repro_raw.json`。元の出力は変えていない）。この版のテストの 20 事例は、16 番を 3 つ（おつかい・ひらめく・おつきみ）、14 番を 2 つに分けた数です。

## 8. 失敗・修正・再実行・未確認

- 未確認: 共有のカードの実行、GUI の画面、new_game からの到達、全体のテスト、化石の発掘・スロットゲームの束の判断。
- 失敗・修正・再実行（どれも道具・テストの側。製品のコードの期待を変えて通したものはない。前の出力は `out/attempt1_*` に残した）:
  1. 新しいテストの初版を修正前に実行したとき、最初に落ちたのが呼び出しの引数の確かめだった。公開の値（log の `card_id`）を先に確かめるように並べ替え、修正前でもう一度実行した（19 失敗。どれも `card_id` が None）。
  2. 比較の書き出しのスクリプトの改行の文字列を、シェルの写しで壊した（構文の誤り。実行前に止まった）。Edit で直した。
  3. 比較の 1 回目は、修正後の側だけで `card_id` を取り除き、修正前から `card_id` のある交換おじさんの事例が差 21 になった。両側で取り除くように直した 2 回目で差 0。
  4. 3 つのまとまりを一度に当てて確かめたあと、コミットを分けるために元にもどし、A・B・C の順に当て直した（最後の状態は、一度に当てたものと同じことをファイルの比較で確かめた）。段階 A では v0.182 の範囲のテストが「交換おじさんだけ」の期待で落ちたので、どの段階でも成り立つ形（許した一覧の中だけ）に直した。

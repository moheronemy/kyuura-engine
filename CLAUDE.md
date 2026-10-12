# CLAUDE.md

このリポジトリで作業するときの約束です。

## 役割

- **kyuura**（https://github.com/moheronemy/kyuura）が歴史資料の正本です。カードデータ、ルールの版、公式エラッタ、出典と確度はそこにあります。
- **kyuura-engine**（このリポジトリ）は対戦処理の実装です。資料の正本ではありません。
- kyuura のデータを勝手に変更しないでください（このリポジトリの作業で kyuura にコミット・プッシュしない）。資料の誤りや食い違いを見つけたら、報告事項として記録し（docs/data-provenance.md、docs/rules-2000-02-14.md の「kyuura の記録との違い」）、kyuura 側の作業として扱います。

## 研究資料の参照コミットを固定する

- 参照する kyuura のコミットは `ecb2d694e6280ec5dc9ddd2a8f709cea16a6b691` です（scripts/extract_kyuura_cards.py の `KYUURA_COMMIT`）。
- カードデータの写し `kyuura_engine/data/kyuura_cards.json` は手で編集せず、`python3 scripts/extract_kyuura_cards.py --kyuura ../kyuura` で作り直します。
- 参照するコミットを上げるときは、写しを作り直し、変わった項目に対応するテストと docs を見直します。

## ルールの扱い

- 基準のルールは「ポケットモンスターカードゲーム公式ルール 2000.02.14版」（『ポケモンカードオフィシャルブック2000』pp.306〜326、kyuura の `NEO-2000-OFFICIAL-RULES`）です。
- **現代のルールで補完しないでください。** 当時の第4版の冊子や後年の裁定も混ぜません。
- 原典で確かめた規定と、実装の都合で決めたこと（実装上の仮定）を区別して書きます（docs/rules-2000-02-14.md の 5章・6章）。
- 原文で決められない処理は、推測で「公式ルール」として実装しません。`UnsupportedError` や `Phase.HALTED` で明示的に止め、docs/implementation-status.md の「裁定が未解決」に書きます。
- 未実装のカード効果を、効果がないものとして処理しないでください。対応していないカード・ワザ・操作は、分類（cards.py）・デッキの検査（deck.py）・`UnsupportedError` で明示的に拒否します。

## 変更するとき

- 規定を加えたり直したりしたら、対応する自動テストを加えます。テストの docstring かコメントに、根拠の誌面のページと kyuura の記録 id を書きます。
- 対戦のテストは、正式な開始（`new_game`、60 枚のデッキ、サイド 6 枚）を使います。盤面を直接作る `tests/helpers.py` の `build_test_state` は、1 か所の規定を確かめるテストだけに使い、対戦準備やデッキのテストには使いません。
- 乱数は `GameState.rng`（seed から作る）だけを使います。
- `apply_command` は渡された状態を変えません（clone してから処理する）。この性質を壊さないでください。
- `new_game`・`apply_command` は、返す状態を `check_invariants` で確かめます（破れていれば `StateIntegrityError`）。ゾーン・段階・保留中の決定を加えたら、その不変条件も `check_invariants` に加えます。段階やコマンドの種類を加えたら、tests/test_state_integrity.py の `ALLOWED`・`sample_commands` も更新します。
- 乱数・カードの番号の付け方・状態の形を変えると、tests/test_reproducibility.py の固定値が変わります。意図した変更のときだけ値を更新し、理由をコミットに書きます。
- docs（README.md、docs/implementation-status.md など）を実態に合わせます。対応していないものを対応済みと書かないでください。
- テスト: `python3 -m unittest`（リポジトリの直下。標準ライブラリだけ）。

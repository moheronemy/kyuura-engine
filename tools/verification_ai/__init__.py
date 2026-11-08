"""エンジン検証用 AI（V0。docs/verification-ai-v0.md。仕様 docs/verification-ai-design.md）。

U7 の公開の入口（``kyuura_engine.client_api``）だけで対戦を進め、操作・診断・終わり方を記録して再現する道具です。配布物（``kyuura_engine``）には含めません。

- ``actions``: 行動生成（B）。API が返した段の契約から入力を組み立てる。カード名・カード ID・効果の型で判定しない（``kyuura_engine`` を import しない）
- ``policies``: 戦略（C）。渡された選べるものの中から選ぶだけ（``kyuura_engine`` を import しない）
- ``runner``: 検証ランナー（D）。ホスト・両プレイヤー・決定の回答者の進行、上限、結果の分類
- ``records``: 記録の包み（CN-1）・識別・意味の表現・書き出し
- ``run_v0``: 固定条件の 1 対戦の実行の入口
"""

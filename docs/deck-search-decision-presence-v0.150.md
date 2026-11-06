# v0.150: 山札をさがす効果の「決定の有無」による情報漏れの修正（両モード共通）

v0.149 で見つけて記録だけにした `PSP-DECK-SEARCH-DECISION-PRESENCE-OTHERS`（おつかい・［うか］）と、同じ形の静的な候補（`attach_energy_from_deck_none`・`bench_from_deck_none`・
ほかの `reveal_from_deck_none`）を、現行コードで数え直して呼び出し元ごとに確かめ、処理の種類ごとにまとめて直した版です。**新しい続行規約は採用していません**。研究上の問い（FC1・RB2・
HC7・H1 など）は決めていません。既存の 3 つの規約集合（`CS-KYUURA-CURRENT@1`・`CS-KYUURA-PLAY-S2A@1`・`CS-KYUURA-PLAY-PO@1`）の ID・版・中身・照合値は変えていません。

## 1. 基点と範囲

- 基点: `c4b90b473c7ad9a1827f99304b1476a9997963e6`（v0.149 の最後。`claude/optional-deck-evolution-presence` の先端。main には未マージ）。作業ブランチは `claude/deck-search-decision-presence`
- 範囲: (1) 確認済みの `PSP-DECK-SEARCH-DECISION-PRESENCE-OTHERS`（おつかい・［うか］）、(2) 静的に見つかった未確認の経路、(3) v0.149 の未確認事項（［おたけび］のミラクルエネルギーの
  確かめの双子）。共通処理に直接関係する近接の経路は 2 章の表に含め、加えた理由を書いた。決定の有無ではない別の形の漏れ（研究上の停止が実際の山札を読む）は直さず、6 章で別件にした
- 盤面の種類（テストの説明にも書いた）: 構築盤面（`build_test_state`）・構築盤面からの合法な操作（宣言・答え・くすぐりマシーン）・補助関数だけの確かめを区別した。`new_game` からの
  合法な対戦での到達は確かめていない（長時間の到達探索はしていない）
- kyuura は読んでいない（変更・コミット・push もしていない）。固定デッキ・過去の参照データは変えていない

## 2. 対象経路の一覧と分類

### 2.1 数え直し（現行コード。同じ要素を使うワザは 1 つの経路として数えた）

| ログ | v0.149 の報告 | 現行コードの記録の場所 | 要素 |
|---|---|---|---|
| `attach_energy_from_deck_none` | 6 か所 | 6 か所 | 5 つ: `AttachFromDeck._none`・`AttachFromDeckToBench._none`・`AttachFromDeckUpToNamedCount`（2 か所）・`AttachFromDeckByHeads._none`・`AttachBasicEnergyFromDeckToSelf._none` |
| `bench_from_deck_none` | 1 か所 | 1 か所 | `BenchFromDeck`（12 のワザ。効果の実装 5 つ） |
| `reveal_from_deck_none` | ほかの 3 か所 | 4 か所（おつかいを含む） | `RevealTrainerFromDeck`（おつかい・おつきみ・ひらめく）・`RevealPokemonFromDeck`・`RevealNamedPokemonFromDeck`・`ReturnHandThenRevealEnergy` |
| `evolve_from_deck_none` | （［うか］） | effects.py 1 か所 | `CoinEvolveSelfFromDeck`（［うか］）。ほかの `evolve_from_deck_none` は v0.84・v0.105・v0.149 で決定を出す形（範囲の外。変えていない） |

effects.py の 2 つの説明の文（12128 行・12294 行付近）は、`RevealTrainerFromDeck`・`BenchFromDeck` を使う効果の実装の説明で、別の記録の場所ではない。

### 2.2 経路ごとの整理

分類: **A** 秘密情報で検索の決定を出すかが変わる（漏れ）／**B** 正当に検索した結果として公開される処理が変わる（原文の処理が公開する結果）／**C** 公開情報だけで検索しないことが
決まる（違いを保ってよい）／**D** 未確認。

| 経路（要素）とワザ | 任意・必須 | 検索を始める条件（公開） | コイン | 候補がないとき（v0.149 まで → v0.150） | 決定（相手・観戦者に見えるもの） | 検索後の公開 | 山札を切る | 研究上の停止 | 分類 |
|---|---|---|---|---|---|---|---|---|---|
| `BenchFromDeck`: なかまをよぶ 5 枚・たすけをよぶ（闘） | 必須（1 匹） | ベンチに空き（宣言の前の `BENCH_FULL`）・山札 1 枚以上 | なし | 決定なし `bench_from_deck_none` → 0〜0 の決定、答えのあと同じログ | `BENCH_FROM_DECK`（種類・プレイヤー。`HIDDEN_COUNT_KINDS`） | `bench_from_deck`（出したカード） | いつも（0 枚でも） | なし | A（決定の有無）・B（出したか） |
| 同: ハネッコ・ヤミカラスの「なかまをよぶ」・いっしょにあそぼ | 必須 | ベンチに空きがなければワザの失敗（山札を見ない） | なし | 同上 | 同上 | 同上 | 失敗なら切らない | なし | A・B。満員は C |
| 同: たすけをよぶ（タケシ 2 枚・カスミ） | 任意（0〜1） | ベンチに空き・「おもて」・山札 1 枚以上 | 「うら」は見ない・切らない（C） | 決定なし `bench_from_deck_none` → 0〜1 の決定（空）、0 枚の答えは `bench_from_deck_declined`（理由は本人だけ） | 同上 | 同上 | 「おもて」ならいつも | なし | A |
| `RevealTrainerFromDeck`: おつかい 4 枚 | 任意 | 「おもて」・山札 1 枚以上 | 「うら」は C | `reveal_from_deck_none` → 0〜1 の決定（空）、`reveal_from_deck_declined`（理由は本人だけ） | `SEARCH_DECK` | `reveal_from_deck`（見せたカード） | 「おもて」ならいつも | なし | A |
| 同: おつきみ | 任意 | 山札 1 枚以上 | なし | 同上 | 同上 | 同上 | いつも | なし | A |
| 同: ひらめく | 必須 | 「おもて」・山札 1 枚以上 | 「うら」は C | `reveal_from_deck_none` → 0〜0 の決定、答えのあと同じログ | 同上 | 同上 | 「おもて」ならいつも | なし | A・B |
| 同 `heads_of`: みんなでおどる | 任意（0〜H） | H ≧ 1 | H = 0 は決定なし（C） | v0.113 から決定を出す（変えていない） | 同上 | 同上 | いつも | なし | 問題なし（双子で確認）。0 枚の答えの理由を本人だけにした |
| `RevealNamedPokemonFromDeck`: くらげのむれ | 任意（0〜選べる数） | 山札 1 枚以上 | なし | `reveal_from_deck_none` → 0〜0 の決定（空）、`reveal_from_deck_declined`（理由は本人だけ） | `SEARCH_DECK` | `reveal_from_deck` | いつも | なし | A |
| 同: りゅうのきずな 2 枚 | 必須（1 枚） | 山札 1 枚以上 | なし | `reveal_from_deck_none` → 0〜0 の決定、答えのあと同じログ | 同上 | 同上 | いつも | なし | A・B |
| `RevealPokemonFromDeck`: でんれい | 必須 | 自分を山札にもどしたあと（山札は 1 枚以上） | なし | 同上 | 同上 | 同上 | いつも | なし | A・B |
| `ReturnHandThenRevealEnergy`: てじな（段階 2） | 必須（もどした枚数） | 手札があれば段階 1（もどす）。もどしたあと | なし | 段階 2 の決定なし `reveal_from_deck_none` → 0〜0 の決定、答えのあと同じログ | 同上 | 同上 | いつも | GS1（0 枚）・FC1（段階 1 の答え。6 章の別件） | A・B。手札なしは C |
| `AttachFromDeck`: ひなたぼっこ・じゅうでん 2 枚 | 任意（0〜1） | 山札 1 枚以上・つけられる（クリスタルビームは C） | なし | 決定なし `no_candidates` → 0〜1 の決定（空）、答えのあと `no_candidates`（`declined` とともに理由は本人だけ） | `ATTACH_FROM_DECK` | `attach_energy_from_deck` | いつも | RB2（宣言の前。6 章の別件） | A |
| 同: もえあがる 2 枚 | 必須（1 枚） | 同上 | なし | 決定なし → 0〜0 の決定、答えのあと `no_candidates` | 同上 | 同上 | いつも | RB2（同上） | A・B |
| 同: しおまねき | 「最大3枚」（選べるとき 0 枚は HC7） | 「おもて」・山札 1 枚以上 | 「うら」は C | 決定なし → 0〜0 の決定、答えのあと `no_candidates` | 同上 | 同上 | 切らない（説明にない） | HC7（山札を見たあとの答え）・RB2 | A |
| `AttachFromDeckToBench`: エナジーサポート | 必須 | 控えがいる（いなければ `no_bench`。C）・山札 1 枚以上 | なし | 決定なし → 0〜0 の決定（段階 card）、答えのあと `no_candidates` | `ATTACH_FROM_DECK` | `attach_energy_from_deck`・`deck_energy_evaded` | いつも | RB2 | A・B |
| 同 `bench_first`: あたためる | 必須 | 控えを選んだあと・山札 1 枚以上（0 枚は見ないので切らない） | なし | 同上 | 同上 | 同上 | 山札を見たとき | RB2 | A・B。控えなしの失敗は C |
| `AttachFromDeckUpToNamedCount`: せいでんき | 任意（0〜数） | 数 ≧ 1・つけられる | なし | v0.85 から決定を出す（変えていない） | 同上 | 同上 | いつも | RB2 | 問題なし（双子で確認） |
| `AttachFromDeckByHeads`: ゆうでん | 「おもて」の数ちょうど | 「おもて」≧ 1・つけられるポケモン | ワザ全体 | v0.113 から決定を出す（A3） | 同上 | 同上 | いつも | FC1・RB2（宣言の前の先読み。6 章の別件） | 決定の有無は問題なし |
| `AttachBasicEnergyFromDeckToSelf`: はらだいこ | 2 枚ちょうど | HP 未満・つけられる | なし | v0.116 から決定を出す（A3） | 同上 | 同上 | いつも | FC1（宣言の前の先読み。6 章の別件） | 決定の有無は問題なし |
| `CoinEvolveSelfFromDeck`: ［うか］（特殊能力） | 必須（1 枚） | 使える（ねむり・マヒ・こんらんでない。番に 1 回）・「おもて」・山札 1 枚以上 | 「うら」は見ない・切らない（C） | 決定なし `evolve_from_deck_none` → 0〜0 の決定、答えのあと同じログ | `SEARCH_DECK` | `evolve`（重ねたカード） | 「おもて」ならいつも | GV1・DV2・H1（使う前。v0.147 で配分によらない確かめ） | A・B |

本人が山札を見てよい時点は、どの経路も「山札をさがす決定を出したとき」（宣言を受理し、コイン・前の段の答えのあと）。それより前（宣言の前の先読み・使う前の確かめ・前の段の答え）は、
持ち主が知っている情報と公開の情報だけで決める（v0.147・v0.148 の境界）。この版で決定を出すようにしたのは、すべてこの時点のあとで、決定の有無だけが山札の中身で分かれていた。

### 2.3 情報の境界

- 相手・観戦者: 山札をさがす決定は、種類と決めるプレイヤーだけ（`BENCH_FROM_DECK`・`SEARCH_DECK`・`ATTACH_FROM_DECK` は `HIDDEN_COUNT_KINDS`。選べるものの数・空であること・選ぶ数は
  見えない。v0.149 までと同じ）。「てよい」の 0 枚の答えは、選ばなかったときも選べるものがなかったときも同じログ（理由は見えない）
- 本人: 実際の山札の候補と、選ばなかった理由（`declined`・`no_target`・`no_candidates`）。検索を始めたあとに本人が得る正当な情報
- ルール上公開される情報: 検索が行われたこと（決定を待つこと・山札を切ること）、選んだ結果（ベンチに出した・見せて手札に加えた・つけた・重ねた）。必ず選ぶ経路では、選べるカードが
  あれば必ず選ぶので、答えのあとの結果から選べるカードがなかったことが分かる。これは原文の処理が公開する結果（B）で、修正の対象ではない（v0.84 の A3・v0.149 のつきのちからと同じ区別）

## 3. 原因と修正の共通原則

**原因**: 各要素が「選べるものがなければ決定を出さずに `…_none` で進む」分岐を持っていた。決定の有無とそのあとのログは相手・観戦者に見えるので、選べるカードが山札にあるか（なければ
サイド・置いておくカードにある）が伝わった。「てよい」の経路では、0 枚の答えのログ（`…_declined`）と `…_none` の違いも公開されていた。

**共通原則**（v0.84 の A3・v0.149 と同じ）:

1. 山札にカードがあれば（実際にさがすとき）、選べるカードがなくても決定を出して答えを待つ。山札が 0 枚（公開の枚数）・コインの「うら」・控えがいない・つけられない・「おもて」が 0 など、
   公開の情報だけで決まる「さがさない」は今までどおり決定を出さない（C の違いは保つ）
2. 選ぶ数: 必ず選ぶ説明は、選べるものがあれば今までどおり、なければ 0〜0（`effects.required_search_choices`）。「てよい」（1 枚）は 0〜1 のまま（最大の数を選べるものの数で小さくしない）。
   「好きなだけ」「最大N枚」は今までどおり 0〜選べるものの数（決めるプレイヤーだけに見える）
3. 「てよい」の 0 枚の答えは、選ばなかった・選べるものがなかったを同じ公開のログにし、理由は本人だけが見る（`observation.PRIVATE_FIELDS`。v0.84 のみずかき・v0.149 のたきのぼりしんかと同じ）:
   `bench_from_deck_declined`・`reveal_from_deck_declined` の `reason`（`declined`・`no_target`）、`attach_energy_from_deck_none` の `reason` のうち `declined`・`no_candidates`
   （公開の情報で決まる `attach_prevented`・`no_bench`・`no_heads`・`no_target`・`no_count` は全員に見える。`observation._deck_search_reason`）
4. 必ず選ぶ経路の選べるもののない決定の答えのあとは、今までどおり `…_none` と山札を切る（ログの種類は変えない。結果は公開）
5. 山札を切る条件は変えない（しおまねきは切らない、あたためるは山札 0 枚なら切らない、など v0.149 までと同じ）
6. 決定の形の確かめ（各 `AttackEffect.decision_problems`・`CoinEvolveSelfFromDeck.decision_problems`）に、選べるもののない決定と、山札が 0 枚のときに出した決定の禁止
   （`effects.empty_search_problems`）を加えた。必ず選ぶ決定に選べるカードがあるのに 0 枚の答えが来たら、今までどおりエンジンの不具合（`RuntimeError`。決定の確かめが先に拒否する）

効果ごとに違うのは、選ぶ数（2.）とログの種類（3.・4.）だけで、どちらも説明の「てよい」の有無から決まる。カード ID・モード名による分岐は `engine.py`・`resolution/` に加えていない。
例外を一括で捕まえる処理は加えていない。

### 3.1 修正の場所

- `kyuura_engine/resolution/programs.py`: `BenchFromDeck`・`RevealPokemonFromDeck`・`RevealNamedPokemonFromDeck`・`RevealTrainerFromDeck`・`ReturnHandThenRevealEnergy`（段階 2）・
  `AttachFromDeck`・`AttachFromDeckToBench`（両方の順番）の `run`・`resume`・`dry_choices`（先読みは選べるもののない決定の答え 0 枚を試す）
- `kyuura_engine/effects.py`: `CoinEvolveSelfFromDeck`（`resolve`・`resume`・`decision_problems`）、`required_search_choices`・`empty_search_problems`（新規）、16 の効果の実装の
  `decision_problems`
- `kyuura_engine/observation.py`: `PRIVATE_FIELDS`（3 つのログ）・`PUBLIC_EVENTS`（3 つを移した）・`DECK_SEARCH_REASONS`・`_deck_search_reason`

## 4. 修正の前の再現（構築盤面と双子）

`tests/test_deck_search_decision_presence_v0_150.py` を修正の前の木（`c4b90b4`）に置いて実行した（一時的な作業ツリー。実行後に消した）:

- `test_search_decision_does_not_depend_on_the_deck`（18 の経路 × 3 つの集合。山札とうらのサイドの双子）: 54 すべて失敗（選べるカードがないほうだけ決定がない）
- `test_hidden_set_aside_twin`（山札と持ち主に見えない置いておくカードの双子。代表 3 つ × 3 つの集合）: 9 すべて失敗
- `test_optional_decline_and_no_target_look_the_same`（「てよい」の 6 経路 × 3 つの集合。0 枚の答えのあと）: 18 すべて失敗
- ［うか］の双子（3 つの集合）: 3 すべて失敗（v0.149 の `RemainingDecisionPresenceLeakTest` と同じ）
- 修正の前から決定の有無が配分によらない経路（せいでんき・みんなでおどる）: 修正の前の木でも成功（`AlreadyUniformTest`）
- そのほかのテスト（選べるもののない決定の形・保存と復元など）は、修正の前の木では決定がないので誤り（漏れの挙動）

修正の前の比較プローブ（テストの外）でも同じ 18 の経路が違い、修正のあとに同じになった。双子はどれも構築盤面（またはくすぐりマシーンの合法な操作のあと）で、`new_game` からの合法な
操作の列での再現はしていない。

## 5. 検証

### 5.1 新しいテスト（`tests/test_deck_search_decision_presence_v0_150.py`）

- `DecisionPresenceTwinTest`: 双子（山札とサイド・山札と置いておくカード）で、山札をさがす決定までの相手・観戦者の観測とログ・受理・拒否が同じ（`twin_command_problems`。所有カードも同じ）。
  「てよい」の 0 枚の答えのあとも同じで、本人には理由が見える。必ず選ぶ経路の答えのあとの違いは公開の結果
- `OwnerAndNormalUseTest`: 本人に実際の候補（カード id）を見せ、選んだ結果（出す・見せて加える・つける）と山札を切る回数が今までどおり。候補なし・任意の辞退・山札が 0 枚（決定なし）・
  コインの「うら」（見ない・切らない）・控えがいない（決定なし・理由は公開）・山札の外の公開の場所にあるカード
- `InvalidAnswerTest`: 選べないカード・相手プレイヤーの答え・必ず選ぶ決定の 0 枚は拒否し、状態・乱数・ログを変えない。相手プレイヤーの答えの拒否は双子で同じ
- `SaveRestoreTest`: 選べるもののない決定・選べる決定を待つ状態の pickle の往復
- `CocoonPowerTest`: ［うか］の双子・答え・山札 0 枚・「うら」・不正な答え・保存と復元
- `AlreadyUniformTest`: せいでんき・みんなでおどる（修正していない）
- `BoundaryHelperTest`: `required_search_choices`・`empty_search_problems`・`_deck_search_reason`（補助関数だけの確かめ）
- `HowlMiracleEnergyTwinTest`: v0.149 の未確認事項。［おたけび］のミラクルエネルギーの確かめ（MEC1）は、山札とサイド・山札と置いておくカードの双子で受理・拒否・コード・理由の文が同じ
  （3 つの集合。理由の文に uid を書かない）。**調べた範囲で問題なし**（v0.149 の候補集合の修正で配分によらない）
- `SeparateStopOracleTest`: 6 章の別件（`expectedFailure`。漏れを正常な仕様として固定しない）
- 共通処理のテストと代表的な呼び出し元の組み合わせ: 双子は経路（要素とその設定）ごとに 1 つのワザで確かめ、同じ要素を使うほかのワザ（なかまをよぶの 5 枚・おつかいの 4 枚など）は複製しない

### 5.2 v0.148・v0.149 の再発の確かめ

- `tests/test_optional_deck_evolution_presence_v0_149.py` の `RemainingDecisionPresenceLeakTest`（`expectedFailure`）は、`OtherDecisionPresenceNoLeakTest` に名前を変えて通常のテストにした
  （おつかい・［うか］の漏れがないこと）
- v0.148 の宣言の前の先読み（`test_attack_deck_evolution_preflight_v0_148`）・v0.149 の決定の有無と候補集合（`test_optional_deck_evolution_presence_v0_149`）・v0.147 の使う前の確かめ
  （`test_deck_content_prechecks_v0_147`）は変えずに通る

### 5.3 実行した検証

5.5 節にまとめる。

### 5.4 既存のテストの調整（意図した処理の差）

どのテストも、本来の目的（候補なしで出さない・加えない・つけない・重ねない、そのあと切る／切らない、理由の値）は変えず、選べるもののない決定に 0 枚で答えてから同じことを確かめる形にした。
「てよい」の経路は、そのあとのログを `…_declined`（理由 `no_target`）で確かめる。

| テスト | 本来の目的 | 調整 |
|---|---|---|
| test_bench_search_counter_drain_v0_32 `test_no_target_in_the_deck` | 候補なしで出さず切る（山札 0・1 枚は乱数を使わない） | 山札にカードがあれば 0〜0 の決定に答える。山札 0 枚は決定なしのまま |
| test_barrier_resume_coin_bonus_v0_34 `test_no_candidate_shuffles_without_benching` | たすけをよぶ（闘）の候補なし | 0〜0 の決定に答えてから |
| test_bench_switch_combined_v0_38 `test_no_candidates_shuffles_once_without_a_decision` | でんれいの候補なしで 1 回切る | 0〜0 の決定に答えてから（テストの名前は v0.38 のまま） |
| test_heal_counter_status_v0_41 `test_decline_and_no_candidates_still_shuffle` | ひなたぼっこの辞退・候補なしで切る | 候補なしは 0〜1 の決定（空）に答えてから。理由 `no_candidates` は本人のログで確かめる |
| test_search_evolution_once_attacks_v0_44 `test_errand_without_trainers_shuffles` | おつかいの候補なしで切る | 0〜1 の決定（空）に答える。ログは `reveal_from_deck_declined`（`no_target`） |
| 同 `test_zero_cards_is_gs1_and_short_energy_is_fc1` | てじなの GS1・FC1・候補 0 枚 | 候補 0 枚は段階 2 の 0〜0 の決定に答えてから（GS1・FC1 の確かめは変えていない） |
| 同 `test_metamorphosis_power`・`test_metamorphosis_keeps_the_normal_restrictions` | ［うか］の候補なし・通常の進化の制限 | 0〜0 の決定に答えてから |
| test_conditional_damage_energy_v0_45 `test_call_for_family_without_candidates_or_bench_space` | タケシのイシツブテの候補なし | 0〜1 の決定（空）に答える。ログは `bench_from_deck_declined`（`no_target`） |
| test_fossil_hidden_info_v0_47 `test_every_evolution_entry_point_is_blocked` | プテラがいると［うか］で重ねられない | 0〜0 の決定に答えてから |
| test_status_coins_effect_reuse_v0_72 `test_no_basic_energy_in_the_deck` | おつきみの候補なし | 0〜1 の決定（空）に答える。ログは `reveal_from_deck_declined`（`no_target`） |
| test_search_energy_pokemon_v0_75 `test_stoke_exactly_one`・`test_no_candidates` | もえあがる・くらげのむれの候補なし | 0〜0 の決定に答えてから。くらげのむれのログは `reveal_from_deck_declined` |
| test_shared_checks_pokemon_reuse_v0_79 `test_no_trainer_and_tails` | ひらめくの候補なし・「うら」 | 0〜0 の決定に答えてから（「うら」は変えていない） |
| test_energy_discard_return_v0_82 `test_no_fire_in_deck_attaches_nothing_but_shuffles` | あたためるの候補なしで切る | 控えを選んだあとの 0〜0 の決定に答えてから |
| test_shining_gentle_v0_83 `test_no_target_shuffles_without_revealing` | りゅうのきずなの候補なし | 0〜0 の決定に答えてから |
| test_variable_coins_search_attachments_v0_113 `test_no_candidates_is_not_a_failure` | ヤミカラスの候補なしは失敗ではない | 0〜0 の決定に答えてから |

### 5.5 実行した検証の結果

- 新しいテスト: 22 テスト（うち 3 つは 6 章の別件の `expectedFailure`）。修正のあとの木ですべて期待どおり（OK）。修正の前の木の結果は 4 章
- 関係するモジュール（1 つずつ。`PYTHONUTF8=1`。重い処理を並行にしない）: v0.149（19）・v0.148（24）・v0.147（18）・v0.32（30）・v0.34（60）・v0.38（58）・v0.40（61）・v0.41（75）・
  v0.42（58）・v0.43（61）・v0.44（49）・v0.45（69）・v0.47（55）・v0.48（48）・v0.51（44）・v0.52（40）・v0.63（39）・v0.72（55）・v0.73（38）・v0.74（34）・v0.75（38）・v0.79（45）・
  v0.80（52）・v0.82（56）・v0.83（54）・v0.84（56）・v0.85（45）・v0.86（65）・v0.87（52）・v0.95（46）・v0.105（47）・v0.113（55）・v0.114（38）・v0.116（66）と、対戦のテスト
  v0.32・v0.34・v0.38・v0.40・v0.41・v0.42 の `_games`（4・4・6・5・5・7）、台帳・設計案・規約集合・版のテスト（13・19・31・15）。すべて OK。最初の実行で失敗したのは 5.4 節の
  既存のテスト（漏れの挙動を前提にした期待）だけで、調整のあとに通った。v0.114 の `test_extract_cards_are_the_v0_113_cards` は、Git Bash から起動したとき `git show` が作業ツリーを
  読めない環境の問題で 1 度失敗し、PowerShell から起動して通った（変更とは関係ない）
- 生成物・データの検査（終了コードは検査本体から）: `build_stop_policy_classification.py --check`・`build_play_policy_family_plan.py --check`・`build_convention_records.py --check`・
  `check_implementation_assumptions.py --check`・`check_normalization_revalidation.py --check` はすべて 0
- ruff 0.17.2（基点と同じ版・設定）: 基点と同じ 492 件で、指摘の集合（ファイル・規則・文）が同じ。途中で増えた 5 件（新しいテストの import の並び 2・台帳の作成スクリプトの文字列の連結 3）は
  直した。新しい抑制（`noqa`）はない
- `check_implementation_assumptions.py --sites`: 新しい候補 198 → 198・消えた候補 5 → 5。違いは `tests/test_preset_decks_v0_20.py` の版の注記の行の ID（`S-572e092c1f14` → `S-484a487d485f`）
  だけで、版の注記を書き足したことによる（新しい実装上の仮定ではない。文面は件数に合わせて変えていない）
- 自然な対戦（対象・seed・目的を先に固定した少数）: 目的は、選べるもののない決定を含む対戦の記録の検査が通ることと、目的の経路に届いたかの記録。v0.41 の組（ひなたぼっこ・
  なかまをよぶ。seed 0〜1。24 局）と v0.44 の組（おつかい・てじな・［うか］。seed 0〜1。16 局）を 1 つずつ実行し、どちらもすべて `game_over`・記録の検査の失敗 0（終了コード 0）。
  ひなたぼっこは 22 回使われ `attach_energy_from_deck_none` が 6 回、なかまをよぶ（PMCG2-005）の `bench_from_deck_none` が 3 回あったが、記録の集計は山札が 0 枚のときと選べるものの
  ない決定を区別しないので、新しい決定を通ったかは確かめられなかった（届いたかは未確認。試行は増やしていない）。v0.44 の組の記録は、この 3 つの経路の候補なしを数えない

### 5.6 実行していない検証

全体テスト・全 108 組・4,356 局の一括計測・lockstep 全体・広い範囲のストレステストは実行していない（8 章の計画）。

## 6. 別件: 山札をさがす前の研究上の停止が実際の山札を読む（PSP-DECK-SEARCH-STOP-ORACLES。修正していない）

経路の確かめの途中で、同じ要素の研究上の停止が、山札を見る前（宣言の前の先読み・前の段の答え）に実際の山札を読むことを見つけた。決定の有無の漏れではなく、v0.147・v0.148 の
「使う前の確かめ」の形の漏れなので、この版の範囲の外として直さず、台帳に `PSP-DECK-SEARCH-STOP-ORACLES`（active）として加え、`SeparateStopOracleTest` を `expectedFailure` で置いた:

- RB2（`rainbow_attach_question`）: `AttachFromDeck`・`AttachFromDeckToBench`・`AttachFromDeckUpToNamedCount` の `candidates`、`AttachFromDeckByHeads.run`。宣言の前の先読みが通るので、
  山札のレインボーエネルギーで宣言を拒否し、理由の文に uid を書く。ひなたぼっこで再現（構築盤面。サイドにあれば受理）
- FC1（`stated_cards_short`）: `AttachBasicEnergyFromDeckToSelf.run`（はらだいこ）・`AttachFromDeckByHeads.run`（ゆうでん）。先読みが山札の基本エネルギーカードの枚数で宣言を拒否する。
  はらだいこはテストで再現、ゆうでんは比較プローブだけ
- FC1（てじなの段階 1）: `ReturnHandThenRevealEnergy.resume` の手札をもどす答え（山札を見る前）が、山札の基本エネルギーカードの枚数で拒否し（理由の文に枚数）、決定は待ったまま
  （答え直せる）。再現（構築盤面）
- 未確認: 同じ `rainbow_attach_question` を通るほかのワザ（じゅうでん・もえあがる・しおまねき・エナジーサポート・あたためる・せいでんき・ゆうでん）の RB2 は個別に確かめていない。
  続行規約の集合（S2A の FC1 の規約など）での違いは確かめていない
- 直す候補: v0.147・v0.148 の共通処理（`possible_deck_cards`・`deck_lower_bound_where`）の形。RB2・FC1 の研究上の問いは決めない

## 7. 意図した差・増えた制限・維持した経路

- 決定・操作列: 山札にカードがあって選べるカードがないとき、2.2 節の A の経路は決定を 1 つ待つ（対戦の記録のコマンドが 1 つ増える。本人は 0 枚で答える）。自然な対戦の乱数の並び・
  局面は、この決定のあとで変わりうる（自動の方策が答えを選ぶため）
- ログ: 「てよい」の経路の候補なしは `…_none` から `…_declined`（理由 `no_target`。本人だけ）に変わった（ひなたぼっこ・じゅうでんは `attach_energy_from_deck_none` の `no_candidates` のまま、
  理由が本人だけになった）。`bench_from_deck_declined`・`reveal_from_deck_declined` に `reason` を加え、見える範囲を `PRIVATE_FIELDS` に移した。必ず選ぶ経路のログの種類は変えていない
- 増えた制限: なし（止める条件・使える条件は変えていない）。新しい停止もない
- 維持した経路: 実候補を選ぶ正常な使用・任意の辞退・山札 0 枚（決定なし）・コインの両面・控えがいない・つけられない・満員の失敗・必須の配置・付与・公開・山札を切る条件・
  v0.148 の宣言の前の確かめ・v0.149 の決定の有無と候補集合
- 状態の書き出しの形式は変えていない。新しい決定の種類はない

## 8. 残る項目・監査の区切り・総合検証の計画

### 8.1 残る不具合・未確認事項

1. `PSP-DECK-SEARCH-STOP-ORACLES`（active。6 章）: 山札をさがす前の RB2・FC1 が実際の山札を読む（決定の有無とは別の形）。ひなたぼっこ・はらだいこ・てじなは構築盤面で再現、ゆうでんは
   プローブだけ、ほかの RB2 の経路は未確認。直すなら v0.147・v0.148 の共通処理の形（研究上の問いは決めない）
2. `new_game` からの合法な対戦での到達: どの経路も構築盤面（と合法な操作）だけで確かめた。自然な対戦の少数の標本では、新しい決定を通ったかを記録から区別できなかった
3. 続行規約の集合ごとの別件の違い: 6 章の別件の `expectedFailure` は今の挙動の集合だけで確かめた（S2A の FC1 の規約などで違うかは確かめていない）。この版の修正の双子は 3 つの集合で確かめた
4. 設計案の組（`DEFECT_COUPLING`）: 別件は FC1・RB2 の一部のワザの経路の漏れなので、停止コードの全体の場面とは組にしていない（候補の対象の組・状態は変えない）。組にするかは別件を直す
   作業で決める

### 8.2 この監査を一区切りにできるか

**山札をさがす効果の「決定の有無」の監査は一区切りにできる**と判断する。根拠:

- v0.149 の確認済みの 2 つと、静的な候補（現行コードの 3 つのログの 11 か所、9 つの要素）をすべて呼び出し元ごとに分類した（2 章）。決定の有無が山札の中身で分かれた経路は、どれも構築盤面の
  双子で再現し、同じ原則（3 章）で直した。修正の前から A3 の形だった経路は双子で問題なしを確かめた
- 公開の情報で決まる「さがさない」（山札 0 枚・コイン・控え・つけられない）は違いを保ち、必ず選ぶ経路の答えのあとの結果（B）は修正の対象から分けた
- 残る `PSP-DECK-SEARCH-STOP-ORACLES` は決定の有無ではなく、山札を見る前の研究上の停止の条件が配分を読む形（v0.147・v0.148 の「使う前の確かめ」の監査の型）で、別件として台帳に
  記録した。未確認の項目（8.1 の 2・3）は、確かめられなかった理由と次の検証を書いた
- ただし、秘密情報の監査全体（使う前の確かめ・研究上の停止の条件）は、別件が active なので終わっていない

### 8.3 マージ前の総合検証の計画（今回は自動で開始しない）

- 対象のコミット: このブランチの最後のコミット（`claude/deck-search-decision-presence` の先端。v0.149 の 4 コミットと v0.150 のコミットを含む。main には v0.148〜v0.150 が未マージ）
- 範囲: docs/testing.md の全体テスト（コードとテストを変えない状態で `python3 -m unittest` を 1 回。Windows では `PYTHONUTF8=1`。時間を測るなら `tools/test_runner.py --report`。
  対戦のテスト `_games` と、`../kyuura` があれば写しの比較を含む。skip は件数と理由を報告する）。全 108 組・4,356 局の一括計測・lockstep 全体は
  別の判断（決定が 1 つ増える経路の自然な対戦の乱数の並び・局面が変わりうるので、過去の集計と比べるなら、比べる版を決めてから）
- 所要時間の目安: この環境で、関係するモジュールの 1 つずつの実行が数秒〜75 秒。全体はこれまでの全体の実行と同じ程度（数十分）を見込む（測っていない）
- 残る懸念: (1) Windows の cp932 で読む既存のテスト（v0.73 など。`PYTHONUTF8=1` で通る）と、Git Bash から起動したときの `git show`（v0.114。PowerShell で通る）の環境の問題、
  (2) 対戦の記録の検査（`tests/log_audit.py`）は、選べるもののない決定を含む自然な対戦で、今回の少数の標本より多くの経路を通る、(3) 道具の集計（`tools/existing_effect_games.py`）の
  `…_none`・`…_declined` の数は、「てよい」の経路で数え方が変わる（候補なしが `…_declined` に入る）。過去の集計と比べるときは注意

### 8.4 次の開発への引き継ぎ（着手していない）

この監査の区切りのあと、次の開発は「診断 API と対戦記録・再現インターフェースの仕様作成」とする（利用者の指示）。この版では実装に着手していない。引き継ぐ材料:

- 双子の比較（`tests/log_audit.py` の `twin_command_problems`・`public_view`・`command_outcome`）と、構築盤面・合法な操作・補助関数の区別は、テストだけの道具で、外から使う API ではない
- 自然な対戦の記録は、決定の有無・選べるもののない決定の答えを経路ごとに数えない（5.5 節）。再現のインターフェースの仕様では、どの経路を通ったか（決定の種類・選べるものの有無は本人の
  観測の範囲）を記録から区別できる形を検討する
- 見える範囲（`observation.PRIVATE_FIELDS`・`HIDDEN_COUNT_KINDS`）は、診断の出力が本人以外に秘密情報を出さない境界として使える

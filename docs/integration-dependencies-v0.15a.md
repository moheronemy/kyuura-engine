# 内部依存の整理（v0.15a）

v0.14 のプロトタイプ（`experiments/event_kernel/`）は、本番の `engine.py` の非公開の関数を 14 直接呼んでいました（[event-prototype-verification-v0.14.md](event-prototype-verification-v0.14.md) 1 章）。v0.15a では、新しい解決の基盤を本番に入れる前に、この依存を整理しました。新しい基盤を標準の経路にはしていません（v0.15b・v0.15d）。

- 「確認した事実」は実際に動かした結果、「評価」はその解釈です。
- ルールの意味（処理・ログの形と順番・乱数の使い方・拒否のコードと順番）は変えていません（5 章で確かめた）。

## 1. 14 の関数の分類

| 関数（v0.13） | 中身 | v0.13 の経路で使う所 | プロトタイプで使っていた所 | 分類 | v0.15a の置き場所 |
|---|---|---|---|---|---|
| `_require_phase` | 段階の確認 | 多数 | 決定への答え | 共通の処理 | `checks.require_phase` |
| `_require_player` | プレイヤーの番号の確認 | 多数 | 決定への答え | 共通の処理 | `checks.require_player` |
| `_require_turn` | 番の確認 | 多数 | ワザ・番の終わり | 共通の処理 | `checks.require_turn` |
| `_require_not_asleep_or_paralyzed` | ねむり・マヒでワザ・にげるを拒否 | ワザ・にげる | ワザ | 共通の処理 | `checks.require_not_asleep_or_paralyzed` |
| `_current_decision` | 保留中の決定（なければ `StateIntegrityError`） | 決定への答え | 決定への答え | 共通の処理 | `checks.current_decision` |
| `_confusion_check` | こんらんのコインとログ | ワザ・にげる | ワザ | 共通の処理 | `procedures.confusion_check` |
| `_confusion_damage` | こんらんの 20 とログ | ワザ | ワザ | 共通の処理 | `procedures.confusion_damage` |
| `_confusion_damage_problem` | こんらんの 20 に変更効果がつくなら止める（v0.13 の止める関数） | ワザの宣言の前 | 先読みの `legacy` | 旧経路に残してよい処理（先読みの `legacy` と共有） | `procedures.confusion_damage_problem` |
| `_knock_out` | きぜつ（トラッシュ・ログ・持続する効果を消す） | ワザのあと・ポケモンチェック | 同じ | 共通の処理 | `procedures.knock_out` |
| `_finish` | 対戦の終わり | 多数 | 勝ち負け | 共通の処理 | `procedures.finish` |
| `_halt` | 対戦を止める（`Phase.HALTED`） | 準備・ポケモンチェック | ポケモンチェック | 共通の処理 | `procedures.halt` |
| `_discard_expired_attachments` | 番の終わりのついているトレーナー | 番の終わり | 番の終わり | 共通の処理 | `procedures.discard_expired_attachments`（番の終わりの期限の全体は `procedures.expire_at_turn_end`） |
| `_pokemon_check_sleep_and_paralysis` | ポケモンチェックの 3・4 と次の番 | ポケモンチェック | 同じ | 共通の処理 | `procedures.pokemon_check_sleep_and_paralysis`（`_begin_turn` も `procedures.begin_turn` に移した） |
| `_require_integrity` | 不変条件の確認 | コマンドの入口 | コマンドの入口 | 本番エンジン固有の制御処理 | `engine.py` に残す（v0.15b からはコマンドの入口が両方の経路に対して呼ぶ） |

「新しい基盤へ移すべき処理」は、14 の中にはありません。14 はどれも効果の解決（どの効果がいつはたらくか）ではなく、ルールの手続き（確認・コイン・きぜつ・番の進行）で、新しい基盤はそれを使う側です。新しい基盤に移すのは、v0.13 の効果の解決の部分（`deal_attack_damage` の効果を探す処理・`finish_damage_elements`・止める関数など。v0.16 で外す候補）です。

## 2. 新しい部品

| モジュール | 行 | 中身 | 読み込むもの |
|---|---|---|---|
| `kyuura_engine/checks.py` | 153 | コマンドの確認。上の 5 つと、ワザの確認の全体 `attack_request`（番 → ワザの位置 → ねむり・マヒ → 登録 → エネルギー。v0.13 の `_use_attack` の前半と同じ順番・同じコード）、決定への答えの確認 `resolve_decision_choices`・`take_prize_choices`・`promote_active_choices`（`decision_choices` で振り分け） | cards・commands・decisions・effects・errors・state |
| `kyuura_engine/procedures.py` | 315 | 状態を変える共通の手続き。上の 9 つ（`begin_turn` を含む）と、番の終わりの期限 `expire_at_turn_end`・ポケモンチェックの 2 `pokemon_check_poison`・止める理由 `POKEMON_CHECK_DOUBLE_KNOCKOUT`・定数 `NEXT_TURN` | judge・coins・conditions・damage・effects・errors・persistent・state・zones |

- どちらも `engine.py` を読み込みません。`engine.py` を読み込むのはパッケージの `__init__.py` だけです（確認した事実。`ast` で読み込みを数えた）。v0.15b で入れる解決の基盤（`kyuura_engine/resolution/`）も、この 2 つを使い、`engine.py` を読み込みません。依存の向きは `engine → resolution → checks・procedures → state・effects…` の一方向で、`engine.py → resolution → engine.py` の循環は起こりません。
- 関数の中身は v0.13 のまま移し、名前の先頭の `_` をとっただけです（`_begin_turn` の中の `_draw(state, player, 1)` は、`_draw` の中身の `draw_cards(state, player, 1)` に置きかえた）。
- `expire_at_turn_end`・`pokemon_check_poison` は、v0.13 の `_end_turn`・`_pokemon_check` の前半と、プロトタイプの同じ処理（v0.14 で複製していた）を 1 つにしたものです。止める理由の文（`POKEMON_CHECK_DOUBLE_KNOCKOUT`）も 1 か所になりました。
- 14 を機械的にすべて移したのではありません。`_require_integrity` はコマンドの入口の制御なので `engine.py` に残し、プロトタイプは公開の `check_invariants` を使うようにしました。`_require_in_hand` など、新しい基盤が使わない確認は移していません。

## 3. `engine.py` の変更

- 移した 14 のうち 13 の定義を消し、v0.13 の名前で読み込みます（`from .procedures import knock_out as _knock_out` など）。v0.13 の経路の関数の本体は、名前を変えずにそのまま使えます。`engine.PLAYERS`・`engine.NEXT_TURN` も今までどおり使えます。
- 確認を共通の関数にした所: `_use_attack` の前半（`checks.attack_request`）、`_resolve_decision`・`_take_prize`・`_promote_active`（`checks.*_choices`）。
- 手続きを共通の関数にした所: `_end_turn` の期限（`procedures.expire_at_turn_end`）、`_pokemon_check` の始まりと 2（`procedures.pokemon_check_poison`）。
- 使われなくなった読み込み 12 を消しました（`ruff --select F401`）。
- 差分: `engine.py` は 31 行を加え 361 行を消した（2,276 行になった）。

v0.13 の経路は、新しい基盤に依存していません。共通の部品（`checks`・`procedures`）は v0.13 のコードを移したもので、v0.13 の経路と新しい基盤の両方が使います。共通の部品を変えると両方の経路が同じように変わるので、同じ木の中の比較では見つかりません。そのため、5 章では、固定した v0.13（`8facf3a`）の木を別のプロセスで動かして比べました。

## 4. プロトタイプの変更

- `experiments/event_kernel/` から `engine.py` の非公開の関数への参照: 14 → 0（確認した事実。`ENG.` の数）。使うのは `checks`・`procedures`・公開の `apply_command`（受け持たないコマンドを渡す）・公開の `check_invariants` です。
- ワザの確認・決定への答えの確認は、v0.13 の経路と同じ関数（`checks.attack_request`・`checks.decision_choices`）になりました（v0.14 は同じ処理を複製していた）。
- 番の終わり・ポケモンチェックの 2 も同じ関数になりました。プロトタイプに残る複製は、窓の記録（`WindowOpened`）と、きぜつの処理の窓（ふしちょうの写し）だけです。

## 5. 確かめたこと（確認した事実）

| 確認 | 結果 |
|---|---|
| `python3 -m unittest`（3.11.17・3.12.3・3.13.16） | どれも 1,731 件 OK（skipped 1。v0.14 と同じ）。変更の前（基準）も同じ数で OK |
| 固定した v0.13（`8facf3a` を `git archive` で取り出した木）と、変更後の木を、別々のプロセス（`python3 -I`）で同じ対戦を進めて比べた（`tools/engine_lockstep.py`） | 対戦のテストの方針 23 × seed 0〜99 と、ストレス実行 26 組 × seed 0〜9（拒否されるコマンドを混ぜる）。2,560 対戦・350,533 歩（うち新しい基盤が受け持つ種類のコマンド 140,707）で、受け付けたか・拒否の例外の種類とコード・書き出しの形式 9 の全体（ログ・乱数の指紋・決定を含む）の指紋が、すべての歩で同じ。7 歩ごとに状態を pickle で保存・復元してから続けた（41,228 回） |
| プロトタイプと変更後の本番の 1 歩ごとの比較（`tools/event_kernel_compare.py --stress-seeds 3 --natural-seeds 5 --mode both --mixed`） | 193 対戦・42,888 歩（プロトタイプが受け持つ 14,795）で食い違い 0（2 つの先読み・交互の状態） |
| `ruff check --select F,E9 .` | 問題なし |

- 比較の道具が違いを見つけることも確かめました。変更後の木の写しでこんらんのダメージを 20 から 30 にすると、`test_confusion_games` の seed 1 の 124 歩目で食い違いを報告しました（同じ道具・同じ対戦で、変更していない木は食い違い 0）。
- 比較の道具は、対戦の始めの状態（`new_game` の結果。対戦準備の途中で止まった対戦を含む）も記録するようにしました（この表の比較のあとで加えた。v0.15b 以降の比較で使う）。

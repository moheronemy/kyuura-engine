# 前の版との互換性の比較（v0.4e）

v0.4e の変更（不変条件を強めた・トレーナーの決定の形の宣言を加えた。ルールの処理は変えていない）が、v0.4d（基準のコミット `4bd97bf`）と同じ入力に対して同じ結果を返すことを、リポジトリの中の道具で確かめた記録です。v0.4d までは比較の手順を作業ごとの一時的な台本で行っていましたが、v0.4e で再実行できる道具とテストにしました。

## 1. 道具

| ファイル | 役割 |
|---|---|
| tools/compat_driver.py | 駆動。1 つの版のエンジンを動かし、1 手ごとの記録を作る。エンジンの公開の API（`new_game`・`apply_command`・`state_to_dict`・コマンドのクラス・状態の読み取り）だけを使い、版ごとのテストの道具・手順には頼らない |
| tools/compare_engine_versions.py | 比べる 2 つの版の木を用意し、版ごとに別のプロセスで駆動を動かし、記録を比べて報告する |
| tests/test_cross_version_compatibility.py | 軽い回帰テスト（参照データとの比較）と、道具のセルフテスト |
| tests/fixtures/compat_base_4bd97bf.json | 参照データ。基準の版（`4bd97bf`）で駆動が作った記録の指紋（4 局・約 480 手） |

### 1.1 版の分離

- 基準の版は `git archive <commit> kyuura_engine` で一時ディレクトリに取り出す（ネットワークは使わない。ローカルの git の履歴だけ）。比べる版は既定で今の作業ツリー（`--new <commit>` で別のコミット）。
- 版ごとに `python3 -I tools/compat_driver.py --tree DIR` を別のプロセスで起動する。`-I` で環境変数（`PYTHONPATH`）・利用者の site を読まず、スクリプトの場所も `sys.path` に入れないので、`DIR` の `kyuura_engine` だけを読み込む。駆動は読み込んだ `kyuura_engine.__file__` が `DIR` の下にあることを確かめ、比べる側も記録に残った場所を確かめる（import のキャッシュは、プロセスが別なので混ざらない）。

### 1.2 比べる組（`SCENARIOS`）

| 組 | 内容 | seed |
|---|---|---|
| `basics` | たねポケモンだけ（v0.1 のデッキ） | 0〜5 |
| `trainers` | マサキ・きずぐすり・ポケモンいれかえ・プラスパワー・ディフェンダー・ドードー・ピカチュウ | 0〜5 |
| `status` | どく（ビードル）・マヒ（キャタピー）・ねむり（パラス）・こんらん（ロコン） | 0〜5 |
| `evolution` | パラス → パラセクト、パウワウ → ジュゴン | 0〜5 |
| `harden` | キャタピー → トランセル、ビードル → コクーン（かたまる） | 0〜5 |
| `stage2` | ビードル → コクーン → スピアー | 0〜5 |
| `butterfree` | キャタピー → トランセル → バタフリー（ふきとばし・メガドレイン） | 0〜5 |
| `all` | すべての対応カード（tests/test_combined_games_v0_4e.py と同じデッキ） | 0〜7（500 手） |

操作は駆動用の乱数（`random.Random("kyuura-compat:<組>:<seed>")`。エンジンの乱数とは別）で選ぶ。ルール上できそうな操作（ベンチに出す・進化・エネルギー・トレーナー・にげる・ワザ・番を終える・決定への答え）に、わざと不正な操作（ほかのプレイヤー・ない番号・段階の違うコマンド・選べない答えなど）を 15% 混ぜる。対戦相手の AI ではない。

### 1.3 比べるもの・除くもの

1 手ごとに、次のすべてを比べる:

- 送った操作（`command_to_dict`）
- 受け付けたか、拒否の種類とコード（`IllegalActionError:WRONG_PHASE` など）。内部の誤り（`EngineError` 以外の例外）はその場で記録して止める。拒否で渡した状態が変わったら、それも記録する
- 状態の指紋: 形式 8 の書き出しの sha256（ログ・乱数の指紋 `rng_state_sha256`・保留中の決定・止めた理由・結果・カードの表を含む）
- 乱数の指紋・段階・ログの長さ
- 形式 1〜8 の書き出し（書き出せたら指紋、表せなければ `ValueError`）

除くのは、形式 2 以上の `effects`（効果の登録表の id。版の名前）だけです。v0.4e では登録表を変えていないので id も同じ（`kyuura-engine-0.4d`）ですが、登録表の id は版の名前で、登録の中身の違いは記録の動きに表れるので比べません。ルールの動きに関わる状態・ログは除いていません。

### 1.4 食い違いの報告

最初に食い違った手について、両方の版で同じ手まで進め直し（`--dump`）、seed・組・手の番号・送った操作・両方の結果・乱数の指紋・その手の前の状態の違い・あとの状態の違い（項目の場所と値）・増えたログを報告します。`--report report.json` を渡すと、前の状態（形式 8）を `report.<組>-<seed>-<手>.before.json` に書きます。終了コードは食い違いがあれば 1。

## 2. 再実行の方法

```sh
# 大きな比較（すべての組・既定の seed。4bd97bf と今の作業ツリー。約 4 分）
python3 tools/compare_engine_versions.py --base 4bd97bf --report report.json

# 一部だけ・別のコミットどうし
python3 tools/compare_engine_versions.py --base 4bd97bf --new HEAD --scenario butterfree --seeds 2 --steps 200

# 軽い回帰テスト（ふだんの python3 -m unittest に含まれる。数秒）
python3 -m unittest tests.test_cross_version_compatibility

# 大きな比較をテストとして（ふだんは走らない）
KYUURA_COMPAT_BASE=4bd97bf python3 -m unittest tests.test_cross_version_compatibility
```

参照データは基準の版から作ります（今の版から作ると、前の版との比較ではなくなる）。駆動を変えたら、参照データの `how` の引数で作り直します（テストが駆動の指紋の違いを知らせる）。

```sh
python3 tools/compare_engine_versions.py --base 4bd97bf --write-fixture tests/fixtures/compat_base_4bd97bf.json \
    --scenario all --scenario butterfree --scenario status --scenario trainers --seeds 1 --steps 120
```

## 3. 結果（v0.4e。2026-10-12）

| 項目 | 結果 |
|---|---|
| 基準 | `4bd97bfe7906e2c5c37515e6ec6b2b81e36000c6`（v0.4d） |
| 比べた版 | v0.4e の作業ツリー（コミット前。`kyuura_engine` の変更を含む） |
| 読み込んだエンジン | 基準: 一時ディレクトリの `trees/4bd97bfe7906/kyuura_engine`、v0.4e: リポジトリの `kyuura_engine` |
| 対戦 | 50 局（8 組） |
| 記録（手） | 11,377（初めの状態 50・受け付けた 6,005・拒否 5,322（うち原典で決められない拒否 412）・内部の誤り 0） |
| 途中の状態・ログ・乱数 | 11,377 手のすべてで状態の指紋（ログ・乱数を含む）と乱数の指紋を比べた |
| 書き出し | 形式 1〜8 の 91,016 件 |
| 終わった段階 | 勝敗 39・HALTED 1（切り直しの補償）・手数の上限 10（番の途中 8・決定 1・バトル場に出す 1） |
| 食い違い | **0** |
| 除いた情報 | `effects`（効果の登録表の id）だけ |
| かかった時間 | 252 秒 |

拒否のコードの内訳（多い順）: `WRONG_RETREAT_COST` 1,900・`INSUFFICIENT_ENERGY` 799・`WRONG_PHASE` 792・`CARD_NOT_IN_HAND` 430・`UNRESOLVED_POTION_WITHOUT_DAMAGE` 221・`NOT_YOUR_TURN` 221・`POKEMON_PARALYZED` 218・`UNRESOLVED_POTION_UNDAMAGED_TARGET` 162・`INVALID_ATTACK` 102・`NOT_ON_BENCH` 92・`PLAYED_THIS_TURN` 81・`POKEMON_ASLEEP` 77・`FIRST_TURN_EVOLUTION` 74・`EVOLVED_THIS_TURN` 62・`UNRESOLVED_SWITCH_WITHOUT_BENCH` 26 ほか（両方の版で同じ）。

軽い回帰テスト（参照データ）は、v0.4e のすべての手で基準と同じでした。既存の固定値（tests/test_reproducibility.py・各対戦のテストの `GOLDEN_DIGEST`・tests/fixtures/v0_1_reference.json）も変わっていません。

v0.4e で強めた不変条件（[integration-audit-v0.4e.md](integration-audit-v0.4e.md) 4 章）は、`new_game`・`apply_command` から作った状態では成り立っているので、受け付ける操作・拒否のコード・状態は v0.4d と同じです（比較で確かめた）。違いが出るのは、呼び出し側が壊した状態を `check_invariants` に渡したときだけです。

## 4. セルフテスト

tests/test_cross_version_compatibility.py:

- `ComparisonLogicTest`: 最初の食い違いの位置と項目、書き出しの違いの場所、数え方（作った記録で確かめる）
- `DriverTest`: 駆動が決定的（同じ seed で同じ記録）で、比べる組のデッキが合法で、指示された対応カード（パラセクト・ジュゴン・トランセル・コクーン・スピアー・バタフリー・特殊状態のカード・トレーナー）を含む
- `IsolationTest`: 今のエンジンを写して 1 か所だけ壊した木（にげるエネルギーの数の確認を外す）と今の木を、別のプロセスで動かし、それぞれの木の `kyuura_engine` を読み込んだこと、記録の食い違い（受け付けたか）を見つけることを確かめる
- `FixtureComparisonTest`: 参照データとの比較（参照データが基準のコミットと今の駆動で作られたことも確かめる）

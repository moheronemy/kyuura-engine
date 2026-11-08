# インストール（通常のインストールと開発用のインストール）

`kyuura_engine` は標準ライブラリだけを使う Python のパッケージです（実行時の依存はない。`requires-python = ">=3.11"`）。パッケージの登録先（PyPI など）には公開していません。

## 1. v0.164 の配布の不具合と修正

- **不具合**: v0.164 までの `pyproject.toml` は `[tool.setuptools] packages = ["kyuura_engine"]` の固定の一覧だけで、サブパッケージ `kyuura_engine.resolution`（12 ファイル）が wheel にも sdist にも入らなかった。通常のインストール（wheel・`pip install "kyuura-engine @ git+…"`）では `import kyuura_engine` が `ImportError: cannot import name 'resolution' from partially initialized module 'kyuura_engine' (most likely due to a circular import)` で失敗する（循環の読み込みではなく、ファイルがない）。同梱のデータ（`data/*.json` の 7 ファイル）は入っていた。編集可能インストール（`-e`）はソースの木を直接読むので動いていた
- **修正**（コミット `e8c518fc214f6a626b33b43c8979f5ca89da459b`。版は 0.164.0 のまま。`kyuura_engine` の中身は変えていない）:
  - `[tool.setuptools.packages.find]` で `kyuura_engine` と `kyuura_engine.*` を探す（`namespaces = false`。`__init__.py` のあるディレクトリだけ。tests・scripts・tools・examples は入らない）
  - `MANIFEST.in` の `prune tests`: setuptools が既定で sdist に入れる `tests/test*.py` を除く（テストはリポジトリの docs・scripts などに依存し、配布物だけでは動かない）
  - データの読み方は変えていない（`importlib.resources` と、パッケージのディレクトリからの相対の読み込み。作業ディレクトリ・ソースの木に依存しない）
- **影響を受けるコミット**: `e8c518f` より前のすべてのコミット（GUI が固定した `d0c5cfa` を含む）は、通常のインストールでは動かない。通常のインストールでは `e8c518f` 以降のコミットを固定する

## 2. 通常のインストール

Git の固定したコミットから（推奨。完全なコミットハッシュで固定する）:

```sh
python -m pip install "kyuura-engine @ git+https://github.com/moheronemy/kyuura-engine@<40 桁のコミットハッシュ>"
```

`requirements.txt` に書く場合:

```
kyuura-engine @ git+https://github.com/moheronemy/kyuura-engine@<40 桁のコミットハッシュ>
```

wheel から（手元で作って配る場合）:

```sh
python -m pip install build                # ビルド用の仮想環境で
python -m build --wheel --outdir dist .    # リポジトリの直下で。dist/kyuura_engine-<版>-py3-none-any.whl
python -m pip install dist/kyuura_engine-<版>-py3-none-any.whl   # 使う側の仮想環境で
```

- sdist（`python -m build --sdist`）から wheel を作っても同じ中身になる（`python -m build --wheel <展開した sdist>`）
- 同じ版の番号（0.164.0）で中身の違う配布物（修正の前と後）があるので、キャッシュした古い wheel を使わないよう、コミットハッシュで固定する
- インストールした先で、Git のコミットを確かめるには `importlib.metadata.distribution("kyuura-engine").read_text("direct_url.json")` の `vcs_info.commit_id` を使う（`site-packages` のディレクトリで `git rev-parse` をすると、仮想環境を置いたリポジトリ（GUI など）の HEAD を返すことがある。エンジンの `replay_record.git_commit()` も補助の情報で、通常のインストールではこの値を当てにしない）

## 3. 開発用のインストール（編集可能）

```sh
git clone https://github.com/moheronemy/kyuura-engine.git
cd kyuura-engine
python -m pip install -e .    # 任意。リポジトリの直下でテストを動かすだけなら不要
```

編集可能インストールはエンジン自体を開発するときのためのもので、別のリポジトリ（GUI など）から使うときの必須の手段ではありません。

## 4. 配布物の確かめ

```sh
python scripts/check_distribution.py --wheel dist/kyuura_engine-<版>-py3-none-any.whl --sdist dist/kyuura_engine-<版>.tar.gz
<インストールした仮想環境>/python scripts/smoke_installed_package.py   # リポジトリの外を作業ディレクトリにして（スクリプトを写して）実行する
```

- `check_distribution.py`: 配布物の中のファイルを、ソースの木のパッケージのファイル（実装の識別が数える `.py` と `data/*.json`）と名前で照らす。欠け・パッケージの外のファイル・一覧にないファイルを名前で示す（終了コード 1）
- `smoke_installed_package.py`: site-packages から読み込んだことを確かめ、全モジュールの読み込み・版・同梱のカードデータと登録データ・3 つの規約集合の照合値・`new_game`・`ClientHub` の開始と各入口・初期配置・公開の更新・実装の識別を出す。実装の識別（`implementation_identity()`）はソースの木と同じになる（改行・場所によらない）
- 回帰テスト: `tests/test_distribution.py`（パッケージの設定と照合の関数。ビルドはしない）

## 5. 対応する Python

- `requires-python = ">=3.11"`。README の「3.11・3.12・3.13 でテスト済み」はリポジトリの直下でのテスト
- 配布の修正の確かめ（wheel・sdist・Git の URL からの通常のインストール）は Python 3.14.6（Windows）だけで行った。3.11〜3.13 での通常のインストールは確かめていない

## 6. GUI（kyuura-engine-gui）が暫定の回避を外す手順

GUI の側の作業です（このリポジトリでは GUI を変更していません）。

1. `server/requirements.txt` の `-e git+https://github.com/moheronemy/kyuura-engine@d0c5cfa…#egg=kyuura-engine` を、修正を含むコミットの通常の指定に置きかえる: `kyuura-engine @ git+https://github.com/moheronemy/kyuura-engine@<修正を含む 40 桁のコミットハッシュ>`（注釈の「-e で入れる理由」も消す）
2. `contract/kyuura-client-api-v1.json` の `engine.commit` を同じハッシュにする（版は 0.164.0 のまま）
3. `server/tests/test_contract.py` のコミットの確かめを、`site-packages` での `git rev-parse` から `direct_url.json` の `vcs_info.commit_id` に変える（通常のインストールでは clone がなく、`server/.venv` は GUI のリポジトリの中にあるので `git rev-parse` が GUI の HEAD を返す）
4. 古い環境を消して入れ直す: `server/.venv` を作り直す（`npm run setup`）。`server/.venv/src/kyuura-engine` の clone が残らないことを確かめる
5. README の「編集可能モード（-e）で入れる理由（エンジン側の既知の問題）」の段落を消し、固定コミットを更新する
6. GUI のテスト（`server/tests`）と接続確認を動かす

# kyuura-engine

旧裏ポケモンカードゲーム（1996〜2001年のメディアファクトリー版）の対戦エンジンです。**「ポケットモンスターカードゲーム公式ルール 2000.02.14版」**（『ポケモンカードオフィシャルブック2000』pp.306〜326）に基づき、少数のカードで 1 試合を最後まで進められる最小の構成です。

- v0.1: 最小の対戦（対戦準備・番の進行・効果のないワザ・きぜつ・勝敗）
- v0.2a: v0.1 と同じルール・カード・対戦の結果のまま、カード効果を実装するための構造を整えた（効果の登録表、保留中の決定、場のポケモンの番号、乱数の状態の保存）。[docs/architecture-v0.2a.md](docs/architecture-v0.2a.md)
- v0.2b: トレーナーカード 3 枚（マサキ・きずぐすり・ポケモンいれかえ）を、『オフィシャルブック2000』の「最新の説明」と照合して実装した。[docs/trainers-v0.2b.md](docs/trainers-v0.2b.md)（原典照合）、[docs/architecture-v0.2b.md](docs/architecture-v0.2b.md)（設計）
- v0.2c（今の版）: プラスパワーを実装し、ポケモンについて場に残るトレーナー・有効期限（番の終わり）・ダメージ計算の段階（p.321 の 5 段階）への効果の適用を加えた。[docs/pluspower-v0.2c.md](docs/pluspower-v0.2c.md)（原典照合）、[docs/architecture-v0.2c.md](docs/architecture-v0.2c.md)（設計）

最重要の目標は、全カード対応ではなく、史料に基づいて正しく動くことです。原典で確かめられない処理は、現代のルールや推測で補わずに「未対応」「未解決」として扱います。

## kyuura との役割分担

| リポジトリ | 役割 |
|---|---|
| [kyuura](https://github.com/moheronemy/kyuura) | 歴史資料の**正本**。カードデータ、ルールの版と変遷、公式エラッタ、出典と確度の記録 |
| kyuura-engine（このリポジトリ） | 対戦処理の実装。kyuura の固定したコミットのデータとルールの記録を参照する |

- 参照している kyuura のコミット: `ecb2d694e6280ec5dc9ddd2a8f709cea16a6b691`
- カードデータは、そのコミットの `data/cards.json` から必要なカードだけを抜き出した写し（`kyuura_engine/data/kyuura_cards.json`）を同梱しています。写しはカード情報の正本ではありません。由来と照合の記録は [docs/data-provenance.md](docs/data-provenance.md)。
- このリポジトリから kyuura を変更することはありません。資料の誤りや食い違いを見つけたら、kyuura 側で確かめて記録します。

## 実行環境

- Python 3.11 以降（3.11・3.12・3.13 でテスト済み）
- 標準ライブラリだけを使います。外部のパッケージは不要です。
- 自動テストはネットワークや kyuura の clone なしで動きます。

## セットアップ

```sh
git clone https://github.com/moheronemy/kyuura-engine.git
cd kyuura-engine
python3 -m pip install -e .   # 任意。リポジトリの直下で使うだけなら不要
```

## テストの実行

リポジトリの直下で:

```sh
python3 -m unittest
```

`pytest` があれば `pytest` でも実行できます。kyuura を隣に clone しておくと（`../kyuura`）、同梱のカードデータが固定したコミットと同じかを確かめるテストも動きます。

```sh
git clone https://github.com/moheronemy/kyuura.git ../kyuura
python3 scripts/extract_kyuura_cards.py --kyuura ../kyuura --check
```

## 使い方

ゲームの状態は `GameState`、プレイヤーの操作はコマンド（`commands.py` の dataclass）です。`apply_command` はコマンドを検査してから新しい状態を返し、渡した状態は変えません。不正な操作は `IllegalActionError`、未対応のものは `UnsupportedError` になります。返す状態は毎回、カードの保存則などの不変条件で確かめ、破れていれば `StateIntegrityError` を投げます（エンジンの不具合か、呼び出し側が状態を書き換えたことを示す）。

```python
from kyuura_engine import (
    AttachEnergy, PlaceStartingPokemon, ReportJankenResult, UseAttack,
    apply_command, expand_decklist, new_game, state_to_dict,
)

# 60 枚のデッキ（カード id は kyuura の data/cards.json の id）
deck0 = expand_decklist({"PMCG1-018": 4, "PMCG1-016": 4, "PMCG1-060": 4, "PMCG1-065": 4, "PMCG1-037": 4, "PMCG1-098": 40})
deck1 = expand_decklist({"PMCG1-025": 4, "PMCG1-029": 4, "PMCG1-052": 4, "PMCG1-053": 4, "PMCG1-058": 4,
                         "PMCG1-099": 20, "PMCG1-102": 20})

state = new_game(deck0, deck1, seed=1)          # 山札を切り、7 枚配り、切り直しまで
for player in (0, 1):                            # バトル場に 1 匹、ベンチに 5 匹まで
    basics = [uid for uid in state.players[player].hand if state.card_def(uid).is_basic_pokemon]
    state = apply_command(state, PlaceStartingPokemon(player, basics[0], tuple(basics[1:6])))
state = apply_command(state, ReportJankenResult(winner=0))  # ジャンケンの勝者が先攻。番の最初の 1 枚も引く

me = state.players[0]
energy = next(uid for uid in me.hand if state.card_def(uid).is_basic_energy)
state = apply_command(state, AttachEnergy(0, energy, me.active.card))
state = apply_command(state, UseAttack(0, 0))    # ワザを使うと番が終わり、相手の番になる
print(state_to_dict(state)["phase"], state.turn_number)
```

- カード 1 枚ごとに対戦内の番号（uid）があり、コマンドは uid でカード・ポケモンを指定します。場のポケモンには、カードの uid とは別に、場に出たときに番号（`pokemon_id`）が付きます。にげる・交代では変わらず、場を離れると無効になります。
- 処理の途中でプレイヤーの選択が要るとき（きぜつさせたときのサイド、バトル場に出すポケモン、きずぐすり・ポケモンいれかえの対象）、`state.decision` に保留中の決定が入ります。決定する人は `decision.player`、選べるものは `decision.options` です。`ResolveDecision(player, decision.id, choices)` で答えます（サイドは `TakePrize`、バトル場に出すポケモンは `PromoteActive` でも答えられる）。決定を待っている間は、ほかの操作は受け付けません。
- ワザ・トレーナーを使えるのは、効果の登録表（`DEFAULT_EFFECTS`）に、カード id（ワザはカード id とワザの位置）で実装が登録されているときだけです。説明文が空なことは、使える根拠にしません。
- 原典で扱いを決められない場面（たとえば、ダメージのあるポケモンがいないときのきずぐすり）は、推測で処理せず `UnsupportedError`（コードは `UNRESOLVED_…`）になり、状態は変わりません。決定の選べるもののうち、そういうものは `decision.context_value("unresolved_choices")` に入っています。
- 乱数は `seed`（0 以上の整数）だけから作ります。同じデッキ・同じ seed・同じ操作の列なら、同じ結果になります（Python 3.11・3.12・3.13 で同じ値になることを固定値のテストで確かめています）。
- 状態は `copy.deepcopy`・`pickle` できます。状態どうしを比べるときは `==` ではなく `state_to_dict` の結果を比べてください。
- 対戦が終わったかどうかは `state.phase` で判断します（`game_over`・`sudden_death`・`halted`）。`halted` のときは `state.result` が `None` です。
- ジャンケンの結果は外から渡します（エンジンは決めません）。
- `state_to_dict` は状態を JSON にできる辞書にし、`command_to_dict` / `command_from_dict` はコマンドを辞書と相互に変換します（ほかの言語や画面から使うための境界）。`state_to_dict` の既定の形式は v0.1 と同じで、`format_version=2` で場のポケモンの番号・保留中の決定などが、`format_version=3` で使用中のトレーナーカードが、`format_version=4` でポケモンについているトレーナーカード（プラスパワーなど）が加わります（トレーナーのある対戦では形式 4 を使う。古い形式は、表せないカードがある状態を書き出さずに `ValueError` にする）。どれも隠れた情報（山札の順番・相手の手札・サイドの中身）を含む内部の状態で、プレイヤーに見せる形ではありません。ログ（`state.log`）も内部の完全な記録で、引いたカードなどを含みます。見る人ごとに伏せたログはまだありません。
- 乱数の状態の保存・復元は `kyuura_engine.rng`（`rng_state_to_json`・`rng_from_json`）にあります。

### トレーナーカードを使う（v0.2b）

```python
from kyuura_engine import (
    PlaceStartingPokemon, PlayTrainer, ReportJankenResult, ResolveDecision,
    apply_command, expand_decklist, new_game, state_to_dict,
)

# トレーナー（マサキ PMCG1-074・きずぐすり PMCG1-071・ポケモンいれかえ PMCG1-073）を入れた 60 枚
deck0 = expand_decklist({"PMCG1-018": 4, "PMCG1-016": 4, "PMCG1-060": 4, "PMCG1-065": 4, "PMCG1-037": 4,
                         "PMCG1-074": 4, "PMCG1-071": 4, "PMCG1-073": 4, "PMCG1-098": 28})
deck1 = expand_decklist({"PMCG1-025": 4, "PMCG1-029": 4, "PMCG1-052": 4, "PMCG1-053": 4, "PMCG1-058": 4,
                         "PMCG1-099": 20, "PMCG1-102": 20})
state = new_game(deck0, deck1, seed=3)
for player in (0, 1):
    basics = [uid for uid in state.players[player].hand if state.card_def(uid).is_basic_pokemon]
    state = apply_command(state, PlaceStartingPokemon(player, basics[0], tuple(basics[1:6])))
state = apply_command(state, ReportJankenResult(winner=0))

def in_hand(card_id):
    return next(uid for uid in state.players[0].hand if state.cards[uid].card_id == card_id)

state = apply_command(state, PlayTrainer(0, in_hand("PMCG1-074")))   # マサキ: 山札から 2 枚引き、トラッシュへ
state = apply_command(state, PlayTrainer(0, in_hand("PMCG1-073")))   # ポケモンいれかえ: 対象を選ぶ決定が出る
d = state.decision                       # d.kind == "select_pokemon"、d.options は自分のベンチのポケモンの番号
state = apply_command(state, ResolveDecision(0, d.id, (d.options[0],)))  # 入れ替えて、トラッシュへ
print(state.phase.value, state_to_dict(state, format_version=3)["trainer_in_use"])  # main None
```

- トレーナーは自分の番（`main`）に、1 番に何枚でも使えます。使ったカードはトラッシュします（p.310）。
- 対象を選ぶトレーナーは決定を出します。決定を待っている間（`decision` の段階）は、決定に答える `ResolveDecision` しか受け付けません（別のトレーナーも使えない）。
- マサキは山札が足りなければ引けるだけ引きます（負けにはならない。p.312）。きずぐすりは選んだ 1 匹のダメージカウンターを 2 個（1 個なら 1 個）とりのぞきます。ポケモンいれかえは、にげるエネルギーを払わずに入れ替えます。
- プラスパワー（v0.2c）は、`PlayTrainer` で使うと自分の対戦ポケモンにつきます（`state.players[p].active.trainers`）。そのポケモンのワザのダメージは、ダメージ計算の 5 段階（弱点・抵抗力のあと）で +10 されます（p.321）。使った番の終わりにトラッシュします。にげる・入れ替えではポケモンといっしょに移ります。

```python
from kyuura_engine import (
    AttachEnergy, PlaceStartingPokemon, PlayTrainer, ReportJankenResult, UseAttack,
    apply_command, expand_decklist, new_game,
)

deck0 = expand_decklist({"PMCG1-018": 4, "PMCG1-016": 4, "PMCG1-060": 4, "PMCG1-065": 4, "PMCG1-037": 4,
                         "PMCG1-081": 4, "PMCG1-098": 36})   # プラスパワー（PMCG1-081）4 枚
deck1 = expand_decklist({"PMCG1-025": 4, "PMCG1-029": 4, "PMCG1-052": 4, "PMCG1-053": 4, "PMCG1-058": 4,
                         "PMCG1-099": 20, "PMCG1-102": 20})
state = new_game(deck0, deck1, seed=1)

def in_hand(player, card_id):
    return next(uid for uid in state.players[player].hand if state.cards[uid].card_id == card_id)

state = apply_command(state, PlaceStartingPokemon(0, in_hand(0, "PMCG1-060")))   # コラッタをバトル場に
basics = [uid for uid in state.players[1].hand if state.card_def(uid).is_basic_pokemon]
state = apply_command(state, PlaceStartingPokemon(1, basics[0], tuple(basics[1:6])))
state = apply_command(state, ReportJankenResult(winner=0))
state = apply_command(state, AttachEnergy(0, in_hand(0, "PMCG1-098"), state.players[0].active.card))
state = apply_command(state, PlayTrainer(0, in_hand(0, "PMCG1-081")))  # 自分の対戦ポケモンにつく
state = apply_command(state, UseAttack(0, 0))                          # かみつく 20 → 5 段階で +10
damage = [e for e in state.log if e["kind"] == "damage"][-1]
print(damage["steps"])  # (('1 基本となる計算', 20), ('5 プラスパワー', 30))
```

### 操作（コマンド）

| コマンド | 内容 |
|---|---|
| `PlaceStartingPokemon(player, active, bench)` | 対戦準備: バトル場に 1 匹、ベンチに 5 匹まで |
| `DrawMulliganCards(player, count)` | 対戦準備: 相手の切り直し 1 回ぶん、0〜2 枚引く |
| `ReportJankenResult(winner)` | 対戦準備: ジャンケンの勝者（先攻） |
| `PlayBasicToBench(player, card)` | 手札のたねポケモンをベンチに出す |
| `AttachEnergy(player, energy, target)` | エネルギーをつける（1 番に 1 枚） |
| `Retreat(player, discard, new_active)` | にげる（何度でも） |
| `UseAttack(player, attack_index)` | ワザを使う（番が終わる） |
| `EndTurn(player)` | ワザを使わずに番を終える |
| `TakePrize(player, index)` | きぜつさせたとき、サイドを 1 枚選んで取る |
| `PromoteActive(player, pokemon)` | バトル場のポケモンがいなくなったとき、ベンチから出す |
| `ResolveDecision(player, decision, choices)` | 保留中の決定に答える（どの種類の決定にも使える。v0.2a） |
| `PlayTrainer(player, card)` | 手札のトレーナーカードを使う（v0.2b。対応した 4 枚だけ。プラスパワーは v0.2c） |
| `EvolvePokemon`・`UsePokemonPower` | 未対応（`UnsupportedError`） |

## 現在の対応ルール（公式ルール 2000.02.14版）

詳しくは [docs/rules-2000-02-14.md](docs/rules-2000-02-14.md)（項目ごとの誌面のページ・kyuura の記録 id・テスト）と [docs/implementation-status.md](docs/implementation-status.md)。

- デッキ 60 枚ちょうど、同じ名前のカードは 4 枚まで（基本エネルギーは制限なし）、たねポケモン必須
- 手札 7 枚。たねポケモンがなければ切り直し（来るまでくりかえす）。相手は切り直し 1 回ごとに、サイドを置いた後で最大 2 枚引ける。両方とも切り直したらどちらも引かない
- バトル場 1 匹、対戦準備のベンチは 5 匹まで、サイド 6 枚、ジャンケンで勝った人が先攻
- 番の最初に必ず 1 枚引く（先攻の最初の番も引く）。山札がなくて引けなければ負け
- たねポケモンをベンチに出す（5 匹まで）、エネルギーは 1 番に 1 枚、にげるは 1 番に何度でも
- ワザは必要なエネルギー（無色はどの色でも）があれば使え、使うと番が終わる
- ダメージ計算: 基本 → 弱点（2 倍）→ 抵抗力（−30）。0 以下なら 0
- HP 以上のダメージできぜつ、サイドを 1 枚選んで取る、ベンチから代わりを出す
- 勝ち負け: サイドを取り終えた、バトル場に出せるポケモンがいない、番の最初に山札がない。同時に満たしたら p.311 の表
- トレーナーカード（v0.2b）: 自分の番に何枚でも使える、使ったらトラッシュ、使っている最中はほかのことができない（p.310）。効果で引くときは山札が足りなくても負けにならない（p.312）
- ついているトレーナー（v0.2c）: ポケモンのいる場所にある（p.313）。にげるときはいっしょに移り（p.311）、きぜつしたらいっしょにトラッシュ（p.323）。ダメージ計算の 5 段階（p.321）

## 現在の対応カード

第1弾の、効果のないワザだけを持つたねポケモン 10 種と、基本エネルギー 6 種、トレーナー 4 種（v0.2b・v0.2c）です（kyuura docs/engine-readiness.md 5章の段階 1）。『オフィシャルブック2000』のカードのページと照合済みです（ポニータのワザ名、きずぐすり・ポケモンいれかえの文面に食い違い。[docs/data-provenance.md](docs/data-provenance.md)）。

| id | カード | id | カード |
|---|---|---|---|
| PMCG1-016 | ポニータ | PMCG1-053 | ワンリキー |
| PMCG1-018 | ガーディ | PMCG1-058 | エビワラー |
| PMCG1-025 | ヒトデマン | PMCG1-060 | コラッタ |
| PMCG1-029 | パウワウ | PMCG1-065 | ミニリュウ |
| PMCG1-037 | ビリリダマ | PMCG1-097〜102 | 草・炎・水・雷・超・闘エネルギー |
| PMCG1-052 | ディグダ | | |

| id | トレーナー（v0.2b） | 処理（『オフィシャルブック2000』p.254 の最新の説明） | 原典で決められないため止める場合 |
|---|---|---|---|
| PMCG1-074 | マサキ | 山札からカードを2枚引いて、手札に加える（足りなければ引けるだけ） | なし |
| PMCG1-071 | きずぐすり | 自分の場のポケモンを1匹選び、ダメージカウンターを2個とりのぞく | ダメージのあるポケモンがいない、ダメージのないポケモンを選ぶ |
| PMCG1-073 | ポケモンいれかえ | 自分の控えポケモンを1匹選び、対戦ポケモンと入れ替える | 控えポケモンがいない |
| PMCG1-081 | プラスパワー（v0.2c。p.257） | 自分の対戦ポケモンにつけて使い、自分の番の終わりにトラッシュ。ついているポケモンのワザが対戦ポケモンに与えるダメージを 5 段階で +10（控えへのダメージは変えない） | なし |

これ以外のカード（効果のあるワザを持つポケモン、進化、ほかのトレーナー、特殊エネルギーなど）はデッキに入れられません。効果のあるワザを「ダメージだけのワザ」として扱うことはしません。対戦用のたねポケモンのワザは、効果の登録表に「効果のないワザ」として 1 つずつ登録してあります（v0.2a）。v0.2a で対応したカード・ルールは v0.1 と同じです。トレーナーは、カード id で効果の実装を登録した 4 枚だけが使えます（v0.2b・v0.2c）。

## 未実装の機能

進化・退化、特殊状態、ポケモンパワー、ほかのトレーナーカード、スタジアム、ポケモンのどうぐ、ベイビィポケモン、特殊エネルギー、効果のあるワザ（コインを使うワザなど）、コイン、サドン・デスの延長戦、旧裏の複数の時期のルールの切り替え、大会のレギュレーション、隠れた情報の管理（見る人ごとの状態）、合法な操作の一覧、状態を辞書からもどす処理、AI、GUI、Web アプリ、ネットワーク対戦。一覧は [docs/implementation-status.md](docs/implementation-status.md#未実装)。

原文から決められないため止める処理: 両方が同時に切り直したあと、片方だけがさらに切り直した場合の補償（`Phase.HALTED`）。トレーナーの上の表の場合（`UnsupportedError`。対戦は続けられる）。

## ディレクトリ

```
kyuura_engine/
  rules.py       ルールの組（2000.02.14版の数値）と根拠の一覧
  cards.py       カードの定義、kyuura のデータの読み込み、対応・未対応の分類
  effects.py     効果の登録表（ワザ: カード id・ワザの位置 → 実装、トレーナー: カード id → 実装）と、トレーナー 4 枚の実装。v0.2a〜v0.2c
  deck.py        デッキの検査
  state.py       ゲームの状態（ゾーン、場のポケモン、番、結果）
  commands.py    プレイヤーの操作
  decisions.py   保留中の決定（出す・確かめる）。v0.2a
  engine.py      対戦の進行（new_game・apply_command）
  damage.py      ワザのダメージ計算（p.321 の 8 段階。2・5〜8 段階の変更効果は v0.2c）
  judge.py       勝ち負けの判定（p.311 の表）
  serialize.py   状態を辞書にする（形式 1〜4）
  zones.py       山札から引く・トレーナーをポケモンにつける処理（エンジンとトレーナーで共通）。v0.2b・v0.2c
  rng.py         乱数の状態の指紋・保存・復元。v0.2a
  data/kyuura_cards.json       kyuura のカードデータの写し（生成物）
  data/card_verification.json  『オフィシャルブック2000』との照合の記録
scripts/extract_kyuura_cards.py  kyuura から写しを作る
scripts/make_compat_fixture.py   v0.1 の対戦結果の参照データを作った道具（作り直さない）
tests/                           自動テスト（unittest）
tests/fixtures/                  v0.1 の対戦結果の参照データ（互換性のテスト用）
docs/                            ルールの仕様、実装状況、データの由来、v0.1 のレビュー、API のレビュー、v0.2a〜v0.2c のアーキテクチャ、トレーナーの原典照合
```

# kyuura-engine

旧裏ポケモンカードゲーム（1996〜2001年のメディアファクトリー版）の対戦エンジンです。**「ポケットモンスターカードゲーム公式ルール 2000.02.14版」**（『ポケモンカードオフィシャルブック2000』pp.306〜326）に基づき、少数のカードで 1 試合を最後まで進められる最小の構成です。

- v0.1: 最小の対戦（対戦準備・番の進行・効果のないワザ・きぜつ・勝敗）
- v0.2a: v0.1 と同じルール・カード・対戦の結果のまま、カード効果を実装するための構造を整えた（効果の登録表、保留中の決定、場のポケモンの番号、乱数の状態の保存）。[docs/architecture-v0.2a.md](docs/architecture-v0.2a.md)
- v0.2b: トレーナーカード 3 枚（マサキ・きずぐすり・ポケモンいれかえ）を、『オフィシャルブック2000』の「最新の説明」と照合して実装した。[docs/trainers-v0.2b.md](docs/trainers-v0.2b.md)（原典照合）、[docs/architecture-v0.2b.md](docs/architecture-v0.2b.md)（設計）
- v0.2c: プラスパワーを実装し、ポケモンについて場に残るトレーナー・有効期限（番の終わり）・ダメージ計算の段階（p.321 の 5 段階）への効果の適用を加えた。[docs/pluspower-v0.2c.md](docs/pluspower-v0.2c.md)（原典照合）、[docs/architecture-v0.2c.md](docs/architecture-v0.2c.md)（設計）
- v0.2d: コイントス（p.319）と、コインの結果でダメージが変わるワザ（ドードーの「みだれづき」）を実装した。コインは対戦の乱数（seed から作る）だけで決まり、1 枚ごとにログに残る。[docs/coin-rules-v0.2d.md](docs/coin-rules-v0.2d.md)（コイントスの原典照合）、[docs/coin-attacks-v0.2d.md](docs/coin-attacks-v0.2d.md)（みだれづき）、[docs/architecture-v0.2d.md](docs/architecture-v0.2d.md)（設計）
- v0.2e: ディフェンダーを実装し、自分の場のポケモンを選んでつけるトレーナー・防御側のダメージ変更（p.321 の 7 段階）・相手の番の終わりまで続く有効期限を加えた。[docs/defender-v0.2e.md](docs/defender-v0.2e.md)（原典照合）、[docs/architecture-v0.2e.md](docs/architecture-v0.2e.md)（設計）
- v0.2f: ワザで自分に与えるダメージ（ダメージの発生源と受けるポケモンを分け、p.321 の順番で計算する）と、1 つのワザで両方のプレイヤーのポケモンがきぜつする同時のきぜつ（サイド・勝ち負け・交代の順番）を、ピカチュウの「かじる」「でんげき」とともに実装した。[docs/self-damage-v0.2f.md](docs/self-damage-v0.2f.md)（自分へのダメージの原典照合）、[docs/simultaneous-ko-v0.2f.md](docs/simultaneous-ko-v0.2f.md)（同時のきぜつ）、[docs/pikachu-v0.2f.md](docs/pikachu-v0.2f.md)（カード）、[docs/architecture-v0.2f.md](docs/architecture-v0.2f.md)（設計）
- v0.3a: 特殊状態の共通基盤と「どく」、番と番のあいだにエンジンが自動で行うポケモンチェック（どくのダメージ・それによるきぜつ・サイド・交代のあとで次の番）を、ビードルの「どくばり」とともに実装した。にげる・ポケモンいれかえでどくが消える。[docs/special-conditions-v0.3a.md](docs/special-conditions-v0.3a.md)（特殊状態・どくの原典照合）、[docs/pokemon-check-v0.3a.md](docs/pokemon-check-v0.3a.md)（ポケモンチェック）、[docs/weedle-v0.3a.md](docs/weedle-v0.3a.md)（カード）、[docs/architecture-v0.3a.md](docs/architecture-v0.3a.md)（設計）
- v0.3b: 「ねむり」「マヒ」と、それによるワザ・にげるの制限、ポケモンチェックの 3（ねむりのコイン）・4（マヒの自動回復）を、キャタピーの「いとをはく」・パラスの「ひっかく」「キノコのほうし」とともに実装した。どくのきぜつ・サイド・交代のあとで 3・4 を行う。原典で決められない場合（両方の対戦ポケモンがねむり、マヒの再付与で回復する番が変わる）は、コインの前に止める。[docs/sleep-paralysis-v0.3b.md](docs/sleep-paralysis-v0.3b.md)（ねむり・マヒの原典照合）、[docs/pokemon-check-v0.3b.md](docs/pokemon-check-v0.3b.md)（ポケモンチェック）、[docs/cards-v0.3b.md](docs/cards-v0.3b.md)（カード）、[docs/architecture-v0.3b.md](docs/architecture-v0.3b.md)（設計）
- v0.3c: 「こんらん」と、こんらん状態のポケモンのワザ（宣言のあとにコインを投げ、「うら」ならワザの内容の代わりに自分に 20 ダメージ。弱点・抵抗力の影響を受ける）・にげる（エネルギーをトラッシュしてからコインを投げ、「うら」なら失敗。失敗したポケモンはその番もう宣言できない）を、ロコンの「あやしいひかり」とともに実装した。正しく宣言した行動がルールで失敗すること（コイン・エネルギー・番の終わりが残る）と、不正なコマンド（拒否し、状態も乱数も変えない）を分ける。原典で決められない場合（こんらんの 20 とプラスパワー・ディフェンダー、失敗のあとこんらんが消えたポケモンの再宣言）は、コインの前に止める。[docs/confusion-v0.3c.md](docs/confusion-v0.3c.md)（こんらんの原典照合）、[docs/confusion-attacks-v0.3c.md](docs/confusion-attacks-v0.3c.md)（ワザ・ロコン）、[docs/retreat-confusion-v0.3c.md](docs/retreat-confusion-v0.3c.md)（にげる）、[docs/architecture-v0.3c.md](docs/architecture-v0.3c.md)（設計）
- v0.3d: カード・ルールを加えず、特殊状態 4 種類のすべての組み合わせ（8 つの状態 × 付与・上書き・解除・操作・ポケモンチェック）を、新しい対戦からの総合テスト・負荷テスト・変異テストとともに確かめた。原典で決められないとして止めていた裁定を調べ直し、5 件（こんらんの 20 とプラスパワー・ディフェンダー、失敗のあとの再宣言、ポケモンチェックの両方のどくのきぜつ・両方のねむり、マヒの再付与）は決められないので止めたまま、v0.2f の自分へのワザのダメージの弱点・抵抗力は p.90 の解説で決まった（SUPPORTED。計算する）。コインの前に確かめ終えていることを、コインの結果で受け付けるかが変わらない性質として確かめた。進化（v0.4）の準備を調べた（実装していない）。[docs/special-conditions-audit-v0.3d.md](docs/special-conditions-audit-v0.3d.md)（総合検証）、[docs/unresolved-rulings-v0.3d.md](docs/unresolved-rulings-v0.3d.md)（未解決の裁定）、[docs/effect-preflight-v0.3d.md](docs/effect-preflight-v0.3d.md)（コインの前の検証）、[docs/architecture-v0.3d.md](docs/architecture-v0.3d.md)（設計）、[docs/evolution-readiness-v0.4.md](docs/evolution-readiness-v0.4.md)（進化の準備）
- v0.4a: 進化（たねポケモン → 1 進化ポケモン）を、パラセクト（パラスから進化）・ジュゴン（パウワウから進化）とともに実装した。進化の条件（名前・最初の番・場に出た番・進化した番。p.309・p.310）、重なったカードの管理、ダメージ・エネルギー・ついているトレーナーの引き継ぎ、特殊状態の回復（p.322）、進化したポケモンのきぜつ（重なったカードをすべてトラッシュ、サイドは 1 枚）。こんらんで「にげる」に失敗したポケモンが進化したら、失敗の記録を消す（SUPPORTED）。進化したあとの HP がダメージ以下になる場合は原典で決められないので止める（`UNRESOLVED_EVOLUTION_HP`。対応カードでは起こらない）。[docs/evolution-rules-v0.4a.md](docs/evolution-rules-v0.4a.md)（進化のルールの原典照合）、[docs/evolution-cards-v0.4a.md](docs/evolution-cards-v0.4a.md)（カード）、[docs/evolution-state-v0.4a.md](docs/evolution-state-v0.4a.md)（状態の持ち方・検証）、[docs/architecture-v0.4a.md](docs/architecture-v0.4a.md)（設計）
- v0.4b: ワザによる持続する効果（番をまたいで残り、期限・ベンチに戻る・進化・きぜつで消える。特殊状態・ついているトレーナーとは別に持つ）を、トランセル（キャタピーから進化）・コクーン（ビードルから進化）の「かたまる」（コインが「おもて」なら、次の相手の番、ダメージを受けない。ダメージ以外の効果は受ける）とともに実装した。「ダメージを受けない」状態のポケモンへのワザのダメージの要素は無効（計算しない。p.321）で、どく・マヒ・こんらんなどの効果の要素は有効。ポケモンチェックのどくのダメージは受ける（p.323）。コインでダメージの量を決めるワザ（みだれづき）をそのポケモンに使う場合は、コインを投げるかが原典で決められないので止める（`UNRESOLVED_PREVENTED_COIN_DAMAGE`）。[docs/persistent-effects-v0.4b.md](docs/persistent-effects-v0.4b.md)（持続する効果の原典照合）、[docs/harden-v0.4b.md](docs/harden-v0.4b.md)（カード・かたまる）、[docs/persistent-damage-v0.4b.md](docs/persistent-damage-v0.4b.md)（ダメージ計算）、[docs/architecture-v0.4b.md](docs/architecture-v0.4b.md)（設計）
- v0.4c: 2 進化（1 進化ポケモン → 2 進化ポケモン）を、スピアー（コクーンから進化）の「ダブルニードル」（コイン 2 枚、「おもて」の数 × 30）・「どくばり」（40、「おもて」なら相手をどく状態に）とともに実装した。たねポケモン・1 進化ポケモン・2 進化ポケモンの 3 枚で構成される 1 匹のポケモンを、v0.4a の `EvolvePokemon`・`evolution_stack` の上で扱う（状態の項目・コマンド・書き出しの形式は増やしていない）。同じ番に 1 進化したポケモンは 2 進化できない（`EVOLVED_THIS_TURN`。p.310）、たねポケモンに 2 進化カードを直接重ねられない、2 進化ポケモンがきぜつしたら 3 枚すべてをトラッシュしてサイドは 1 枚。「かたまる」の相手へのダブルニードルは v0.4b と同じく止める（`UNRESOLVED_PREVENTED_COIN_DAMAGE`）。[docs/stage2-evolution-v0.4c.md](docs/stage2-evolution-v0.4c.md)（2 進化のルールの原典照合）、[docs/beedrill-v0.4c.md](docs/beedrill-v0.4c.md)（スピアー）、[docs/stage2-state-v0.4c.md](docs/stage2-state-v0.4c.md)（3 枚の重なりの状態・検証）、[docs/architecture-v0.4c.md](docs/architecture-v0.4c.md)（設計・v0.4d の準備）
- v0.4d: ワザの途中で相手プレイヤーの決定を待ち、答えのあとで同じワザを再開する処理と、ワザが与えたダメージの結果（`DamageResult`）を後の要素に渡す処理を、バタフリー（トランセルから進化する 2 進化）の「ふきとばし」（20 のあと、相手の対戦ポケモンを相手が選んだ控えと入れ替える）・「メガドレイン」（40。与えたダメージの半分（切り上げ）のダメージカウンターを自分からとりのぞく）とともに実装した。決定するのは相手（`decision.player`）で、番のプレイヤーは変わらない（決定の種類 `forced_switch`。段階・コマンド・状態の項目・書き出しの形式は増やしていない）。相手に控えがいなければ入れ替えない、20 で相手がきぜつするなら入れ替えない（対象がいない。p.309・p.89・p.213）。ベンチにもどったポケモンの特殊状態・持続する効果は消える。「与えたダメージ」は最終ダメージ（HP で上限を付けない。0・「ダメージを受けない」相手なら与えていないので回復しない。p.319）。新しい未解決の裁定はない。[docs/forced-switch-v0.4d.md](docs/forced-switch-v0.4d.md)（強制交代）、[docs/damage-drain-v0.4d.md](docs/damage-drain-v0.4d.md)（与えたダメージと回復）、[docs/butterfree-v0.4d.md](docs/butterfree-v0.4d.md)（バタフリー）、[docs/architecture-v0.4d.md](docs/architecture-v0.4d.md)（設計）
- v0.4e: カード・ルールを加えず、v0.4a〜v0.4d（進化・持続する効果・2 進化・強制交代・与えたダメージ・メガドレイン）の総合監査をした。組み合わせの表（段階 × 場所 × 特殊状態 8 通り × 持続する効果 × ついているカード × ダメージ × 決定。1,147 の subTest）、壊した状態の検出、ログだけから組み立て直した状態と状態の一致、書き出しの形式 1〜8 の監査、原典で決められない 11 件の範囲、変異テスト（24 個すべて検出）。不変条件の検出の漏れ 5 件（トレーナーの決定の形・サイドと交代の決定・サイドを取る人・交代の順番・番の番号）を直した（ルールの処理・ログ・書き出しは v0.4d と同じ）。前の版との比較（`tools/compare_engine_versions.py`）とストレス実行（`tools/stress_engine.py`）をリポジトリの道具にした。[docs/integration-audit-v0.4e.md](docs/integration-audit-v0.4e.md)（監査）、[docs/interaction-matrix-v0.4e.md](docs/interaction-matrix-v0.4e.md)（組み合わせの表）、[docs/compatibility-v0.4e.md](docs/compatibility-v0.4e.md)（互換性）、[docs/unresolved-audit-v0.4e.md](docs/unresolved-audit-v0.4e.md)（未解決の範囲）、[docs/architecture-v0.4e.md](docs/architecture-v0.4e.md)（設計）、[docs/v0.5-readiness.md](docs/v0.5-readiness.md)（ポケモンパワーの準備）
- v0.5（今の版）: ポケモンパワー（2000.02.14 版の用語では「特殊能力」）の基盤（`UsePokemonPower`・パワーの登録表）を、フシギバナ（PMCG1-011）の「エナジートランス」と、進化元のフシギダネ（やどりぎのタネ）・フシギソウ（つるのむち・どくのこな（コインなし））とともに実装した。一般の規定（p.309〜p.311・p.322・p.323）とカードのページ（p.13・p.14・p.16）を画像で照合した。使っても番は終わらず、何度でも・ベンチからも使え、使うフシギバナがねむり・マヒ・こんらんなら使えない（どくなら使える）。つけかえは手札からつけること（1 番に 1 回）ではなく、乱数を使わない。前の版（v0.4e）との比較で、フシギバナのいない対戦の結果は同じ。[docs/pokemon-powers-v0.5.md](docs/pokemon-powers-v0.5.md)（規定）、[docs/venusaur-v0.5.md](docs/venusaur-v0.5.md)（フシギバナ）、[docs/bulbasaur-line-v0.5.md](docs/bulbasaur-line-v0.5.md)（フシギダネ・フシギソウ）、[docs/energy-transfer-v0.5.md](docs/energy-transfer-v0.5.md)（処理）、[docs/architecture-v0.5.md](docs/architecture-v0.5.md)（設計）、[docs/v0.5-verification.md](docs/v0.5-verification.md)（確かめた結果）

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

ふだんのテスト（`python3 -m unittest`）には、速い単体テスト（段階 A）と、決まった seed の対戦・ログと書き出しの監査・前の版の参照データとの比較・小さなストレス実行（段階 B）が入っています。大きな実行（段階 C）は明示的に走らせます（v0.4e。[docs/architecture-v0.4e.md](docs/architecture-v0.4e.md) 4 章）:

```sh
# 前の版（v0.4e の c1e13ec。v0.4e では v0.4d の 4bd97bf）と今の作業ツリーを、同じ入力で別々のプロセスで動かして比べる（約 4 分。ネットワーク不要）
python3 tools/compare_engine_versions.py --base c1e13ec --report report.json
# 大規模なストレス実行（でたらめな操作を混ぜ、結果を分類して数える。問題のある seed を報告する）
python3 tools/stress_engine.py --seeds 100 --steps 600 --report stress.json
# フシギバナの組だけ（エナジートランスの使用を混ぜる。v0.5）
python3 tools/stress_engine.py --scenario venusaur --scenario venusaur_status
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
- 乱数は `seed`（0 以上の整数）だけから作ります。同じデッキ・同じ seed・同じ操作の列なら、同じ結果になります（Python 3.11・3.12・3.13 で同じ値になることを固定値のテストで確かめています）。乱数を使うのは、山札を切るときと、コインを投げるとき（v0.2d）だけです。コインの結果をコマンドで指定する方法はありません。
- 状態は `copy.deepcopy`・`pickle` できます。状態どうしを比べるときは `==` ではなく `state_to_dict` の結果を比べてください。
- 対戦が終わったかどうかは `state.phase` で判断します（`game_over`・`sudden_death`・`halted`）。`halted` のときは `state.result` が `None` です。
- ジャンケンの結果は外から渡します（エンジンは決めません）。
- `state_to_dict` は状態を JSON にできる辞書にし、`command_to_dict` / `command_from_dict` はコマンドを辞書と相互に変換します（ほかの言語や画面から使うための境界）。`state_to_dict` の既定の形式は v0.1 と同じで、`format_version=2` で場のポケモンの番号・保留中の決定などが、`format_version=3` で使用中のトレーナーカードが、`format_version=4` でポケモンについているトレーナーカード（プラスパワーなど）が、`format_version=5` で特殊状態（v0.3a〜v0.3c）が、`format_version=6` でこんらんで「にげる」に失敗した記録（v0.3c）が、`format_version=7` で進化の重なり・場に出た番・進化した番（v0.4a）が、`format_version=8` でワザによる持続する効果（v0.4b）が加わります（いまの対戦は形式 8 を使う。古い形式は、表せないもの（カード・特殊状態・失敗の記録・進化・持続する効果）がある状態を書き出さずに `ValueError` にする）。どれも隠れた情報（山札の順番・相手の手札・サイドの中身）を含む内部の状態で、プレイヤーに見せる形ではありません。ログ（`state.log`）も内部の完全な記録で、引いたカードなどを含みます。見る人ごとに伏せたログはまだありません。
- 乱数の状態の保存・復元は `kyuura_engine.rng`（`rng_state_to_json`・`rng_from_json`）にあります。ゲーム状態全体を JSON から読み込む処理はまだありません。

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

### ディフェンダー（v0.2e）

ディフェンダー（PMCG1-079）は、自分の場（バトル場・ベンチ）のポケモンを選んでつけ、次の相手の番の終わりにトラッシュします。ついているポケモンがワザによるダメージを受けるとき、そのダメージはダメージ計算の 7 段階（弱点・抵抗力・プラスパワーのあと）で −20 されます（p.257・p.321）。

```python
from kyuura_engine import (
    EndTurn, PlaceStartingPokemon, PlayTrainer, ReportJankenResult, ResolveDecision,
    apply_command, expand_decklist, new_game,
)

deck0 = expand_decklist({"PMCG1-018": 4, "PMCG1-016": 4, "PMCG1-060": 4, "PMCG1-065": 4, "PMCG1-037": 4,
                         "PMCG1-079": 4, "PMCG1-098": 36})   # ディフェンダー（PMCG1-079）4 枚
deck1 = expand_decklist({"PMCG1-025": 4, "PMCG1-029": 4, "PMCG1-052": 4, "PMCG1-053": 4, "PMCG1-058": 4,
                         "PMCG1-099": 20, "PMCG1-102": 20})
state = new_game(deck0, deck1, seed=1)
for player in (0, 1):
    basics = [uid for uid in state.players[player].hand if state.card_def(uid).is_basic_pokemon]
    state = apply_command(state, PlaceStartingPokemon(player, basics[0], tuple(basics[1:6])))
state = apply_command(state, ReportJankenResult(winner=0))

defender = next(uid for uid in state.players[0].hand if state.cards[uid].card_id == "PMCG1-079")
state = apply_command(state, PlayTrainer(0, defender))       # 自分の場のポケモンを選ぶ決定が出る
d = state.decision                                           # d.options: 自分のバトル場・ベンチのポケモンの番号
state = apply_command(state, ResolveDecision(0, d.id, (d.options[0],)))   # バトル場のポケモンにつける
print(state.turn_number, state.players[0].active.trainers)   # 1 [AttachedTrainer(card=23, player=0, discard_at_end_of_turn=2)]
state = apply_command(state, EndTurn(0))                     # 自分の番の終わりにはトラッシュしない
print(state.turn_number, len(state.players[0].active.trainers))   # 2 1
state = apply_command(state, EndTurn(1))                     # 次の相手の番の終わりにトラッシュする
print(state.turn_number, len(state.players[0].active.trainers), defender in state.players[0].discard)   # 3 0 True
```

- つけるポケモンは決定（`select_pokemon`）で選びます。1 匹しかいなくても選びます。相手のポケモンは選べません。
- 使った番の終わりにはトラッシュしません（プラスパワーは使った番の終わり）。期限は `AttachedTrainer.discard_at_end_of_turn`（使った番 + 1）です。きぜつしたらポケモンといっしょにトラッシュし、勝敗が決まったらついたまま残ります。
- 例: 相手のワザ 30 + プラスパワー 10 − ディフェンダー 20 = 20。途中がマイナスでも計算を続け、最後に 0 以下なら 0 です。

### どくとポケモンチェック（v0.3a）

ビードル（PMCG1-004）の「どくばり」は、相手の対戦ポケモンに 10 ダメージを与え、コインを投げて「おもて」なら相手をどく状態にします（p.19 の最新の説明「コインを投げて「おもて」なら、相手を「どく」状態にする。」）。どく状態のポケモンは、番と番のあいだのポケモンチェックのたびに 10 ダメージを受けます（p.322・p.323）。

```python
from kyuura_engine import (
    AttachEnergy, EndTurn, PlaceStartingPokemon, ReportJankenResult, UseAttack,
    apply_command, expand_decklist, new_game,
)

deck0 = expand_decklist({"PMCG1-004": 4, "PMCG1-018": 4, "PMCG1-016": 4, "PMCG1-060": 4, "PMCG1-037": 4,
                         "PMCG1-097": 40})   # ビードル（PMCG1-004）4 枚、草エネルギー 40 枚
deck1 = expand_decklist({"PMCG1-025": 4, "PMCG1-029": 4, "PMCG1-052": 4, "PMCG1-053": 4, "PMCG1-058": 4,
                         "PMCG1-099": 20, "PMCG1-102": 20})
state = new_game(deck0, deck1, seed=1)

def in_hand(player, card_id):
    return next(uid for uid in state.players[player].hand if state.cards[uid].card_id == card_id)

state = apply_command(state, PlaceStartingPokemon(0, in_hand(0, "PMCG1-004")))   # ビードルをバトル場に
basics = [uid for uid in state.players[1].hand if state.card_def(uid).is_basic_pokemon]
state = apply_command(state, PlaceStartingPokemon(1, basics[0], tuple(basics[1:6])))
state = apply_command(state, ReportJankenResult(winner=0))
state = apply_command(state, AttachEnergy(0, in_hand(0, "PMCG1-097"), state.players[0].active.card))
state = apply_command(state, UseAttack(0, 0))   # どくばり: 相手に 10 → コイン → 「おもて」ならどく。番が終わり、ポケモンチェック
print([e["kind"] for e in state.log[-9:]])
# ['attack', 'damage', 'coin_flip', 'special_condition', 'turn_end', 'pokemon_check', 'poison_damage', 'turn_start', 'draw']
print(state.players[1].active.damage, state.players[1].active.conditions)   # 20 SpecialConditions(poison=Poison(damage=10), exclusive=None)
state = apply_command(state, EndTurn(1))        # 相手の番の終わりのポケモンチェックでも 10
print(state.players[1].active.damage)   # 30
```

- どくのダメージは「ワザによるダメージ」ではありません（p.321）。弱点・抵抗力・プラスパワー・ディフェンダーは関係せず、ログもワザの `damage` とは別の `poison_damage` です。
- ポケモンチェックは、番の終わり（ログ `turn_end`）のあと、次の番（`turn_start`）の前に、エンジンが自動で行います（p.309）。どくできぜつしたら、きぜつしたポケモンの相手側がサイドを取り、持ち主がベンチから出してから、次の番が始まります（決定 `take_prize`・`promote_active` の `context` の `then` が `"next_turn"`）。
- どく状態のポケモンがにげる・ポケモンいれかえでベンチに戻ると、どくは消えます（p.311・p.322）。どくは積み重ならず、自然には回復しません。きずぐすりでも消えません。
- 両方のプレイヤーのポケモンが同じポケモンチェックのどくできぜつする場合は、原典で決められないので対戦を止めます（`Phase.HALTED`、`UNRESOLVED_POKEMON_CHECK_DOUBLE_KNOCKOUT`。[docs/pokemon-check-v0.3a.md](docs/pokemon-check-v0.3a.md) 3 章）。
- 特殊状態は形式 5 の `state_to_dict(state, format_version=5)` で書き出せます（形式 1〜4 は特殊状態があると `ValueError`）。

### こんらん（v0.3c）

ロコン（PMCG1-015）の「あやしいひかり」は、相手の対戦ポケモンに 10 ダメージを与え、コインを投げて「おもて」なら相手をこんらん状態にします（p.67）。こんらん状態のポケモンもワザ・にげるを宣言できますが、宣言のあとで持ち主がコインを投げます（p.309・p.311・p.322）。

```python
from kyuura_engine import (
    AttachEnergy, EndTurn, IllegalActionError, PlaceStartingPokemon, ReportJankenResult, Retreat, UseAttack,
    apply_command, expand_decklist, new_game,
)

deck0 = expand_decklist({"PMCG1-015": 4, "PMCG1-018": 4, "PMCG1-016": 4, "PMCG1-060": 4, "PMCG1-037": 4,
                         "PMCG1-098": 40})   # ロコン（PMCG1-015）4 枚、炎エネルギー 40 枚
deck1 = expand_decklist({"PMCG1-025": 4, "PMCG1-029": 4, "PMCG1-052": 4, "PMCG1-053": 4, "PMCG1-058": 4,
                         "PMCG1-099": 20, "PMCG1-102": 20})
state = new_game(deck0, deck1, seed=222)

def in_hand(player, card_id):
    return next(uid for uid in state.players[player].hand if state.cards[uid].card_id == card_id)

state = apply_command(state, PlaceStartingPokemon(0, in_hand(0, "PMCG1-015")))   # ロコンをバトル場に
basics = [uid for uid in state.players[1].hand if state.card_def(uid).is_basic_pokemon]
state = apply_command(state, PlaceStartingPokemon(1, basics[0], tuple(basics[1:6])))   # ヒトデマンと控え
state = apply_command(state, ReportJankenResult(winner=0))
for player in (0, 1):   # 1 番・2 番: エネルギーを 1 枚ずつつけて番を終える
    energy = "PMCG1-098" if player == 0 else "PMCG1-099"
    state = apply_command(state, AttachEnergy(player, in_hand(player, energy), state.players[player].active.card))
    state = apply_command(state, EndTurn(player))
state = apply_command(state, AttachEnergy(0, in_hand(0, "PMCG1-098"), state.players[0].active.card))
state = apply_command(state, UseAttack(0, 0))   # あやしいひかり: 相手に 10 → コイン → 「おもて」ならこんらん
print(state.players[1].active.conditions)   # SpecialConditions(poison=None, exclusive=Confused())

# 4 番: こんらん状態のヒトデマンが「にげる」。エネルギーをトラッシュしてからコインを投げる
state = apply_command(state, AttachEnergy(1, in_hand(1, "PMCG1-099"), state.players[1].active.card))
staryu = state.players[1].active
state = apply_command(state, Retreat(1, (staryu.energy[0],), state.players[1].bench[0].card))
print([(e["kind"], e.get("source"), e.get("result")) for e in state.log[-3:]])
# [('coin_flip', 'confusion', 'tails'), ('confusion_check', None, 'tails'), ('retreat_failed', None, None)]
print(state.players[1].active.retreat_failed_turn, len(state.players[1].active.energy))   # 4 1（エネルギーは戻らない）
try:   # 失敗したポケモンは、この番はもう「にげる」を宣言できない（p.311）
    apply_command(state, Retreat(1, (state.players[1].active.energy[0],), state.players[1].bench[0].card))
except IllegalActionError as error:
    print(error.code)   # RETREAT_ALREADY_FAILED
state = apply_command(state, UseAttack(1, 0))   # こんらん状態のワザ: コイン → 「うら」なら自分に 20
print([(e["kind"], e.get("amount")) for e in state.log if e["kind"] in ("confusion_check", "confusion_damage")][-2:])
# [('confusion_check', None), ('confusion_damage', 20)]
print(state.players[1].active.damage, state.current_player)   # 30 0（ワザは使ったことになり、番が終わった）
```

- ワザ: 必要なエネルギーの確認と宣言のあとで、持ち主がコインを 1 枚投げます（p.309 の手順 5）。「おもて」ならワザの説明どおり、「うら」ならもとのワザの内容に関わらず、ワザを使ったポケモン自身に 20 ダメージです（p.322）。20 ダメージは弱点・抵抗力の影響を受けます（自分のタイプと自分の弱点・抵抗力で見る）。どちらでもワザは使ったことになり、番が終わります。自分がきぜつしたら、サイドは相手が取ります。
- にげる: エネルギーをトラッシュしてから、コインを 1 枚投げます（p.311 の手順 3）。「うら」なら失敗で、エネルギーは戻らず、入れ替えません。番は続きます。失敗したポケモンは、その番はもう「にげる」を宣言できません（`RETREAT_ALREADY_FAILED`）。次の自分の番には宣言できます。制限はポケモンごとで、ポケモンいれかえ（コインなし）で出たほかのポケモンはにげられます。
- こんらんは自然には回復しません（ポケモンチェックで何もしない）。ベンチに戻ったら消えます。ねむり・マヒとは重複せず置きかわり、どくとは重複します（p.322）。
- コインはログの `coin_flip`（`source: "confusion"`）と `confusion_check`（`action`・`succeeded`）、自分への 20 は `confusion_damage`、にげるの失敗は `retreat_failed` に残ります。
- 原典で決められない場合は止めます: ダメージを変えるカード（プラスパワー・ディフェンダー）がついたこんらん状態のポケモンのワザ（`UNRESOLVED_CONFUSION_DAMAGE_MODIFIERS`）、失敗のあとベンチに戻ってこんらんが消え、同じ番にバトル場に戻ったポケモンの「にげる」（`UNRESOLVED_RETREAT_AFTER_CONFUSION_CLEARED`）。どちらもコイン・エネルギーの前に `UnsupportedError` です。
- こんらんは形式 5（`special_conditions` の `confusion: {}`）、にげるの失敗の記録は形式 6（場のポケモンごとの `retreat_failed_turn`）で書き出せます（古い形式は `ValueError`）。

### ねむり・マヒ（v0.3b）

キャタピー（PMCG1-002）の「いとをはく」は、相手の対戦ポケモンに 10 ダメージを与え、コインを投げて「おもて」なら相手をマヒ状態にします（p.17）。パラス（PMCG2-003）の「キノコのほうし」は、ダメージを与えずに相手をねむり状態にします（p.38）。ねむり・マヒのポケモンはワザを使えず、にげるを宣言できません（p.309・p.311・p.322）。

```python
from kyuura_engine import (
    AttachEnergy, EndTurn, IllegalActionError, PlaceStartingPokemon, ReportJankenResult, UseAttack,
    apply_command, expand_decklist, new_game,
)

deck0 = expand_decklist({"PMCG1-002": 4, "PMCG2-003": 4, "PMCG1-018": 4, "PMCG1-060": 4, "PMCG1-037": 4,
                         "PMCG1-097": 40})   # キャタピー（PMCG1-002）・パラス（PMCG2-003）各 4 枚、草エネルギー 40 枚
deck1 = expand_decklist({"PMCG1-025": 4, "PMCG1-029": 4, "PMCG1-052": 4, "PMCG1-053": 4, "PMCG1-058": 4,
                         "PMCG1-099": 20, "PMCG1-102": 20})
state = new_game(deck0, deck1, seed=1)

def in_hand(player, card_id):
    return next(uid for uid in state.players[player].hand if state.cards[uid].card_id == card_id)

state = apply_command(state, PlaceStartingPokemon(0, in_hand(0, "PMCG1-002")))   # キャタピーをバトル場に
basics = [uid for uid in state.players[1].hand if state.card_def(uid).is_basic_pokemon]
state = apply_command(state, PlaceStartingPokemon(1, basics[0], tuple(basics[1:6])))
state = apply_command(state, ReportJankenResult(winner=0))
state = apply_command(state, AttachEnergy(0, in_hand(0, "PMCG1-097"), state.players[0].active.card))
state = apply_command(state, UseAttack(0, 0))   # いとをはく: 相手に 10 → コイン → 「おもて」ならマヒ
print([e["kind"] for e in state.log[-8:]])
# ['attack', 'damage', 'coin_flip', 'special_condition', 'turn_end', 'pokemon_check', 'turn_start', 'draw']
print(state.players[1].active.conditions)   # SpecialConditions(poison=None, exclusive=Paralyzed(turn=1))
try:
    apply_command(state, UseAttack(1, 0))   # マヒのあいだはワザを使えない（にげるも同じ）
except IllegalActionError as error:
    print(error.code)   # POKEMON_PARALYZED
state = apply_command(state, EndTurn(1))   # 持ち主の次の番（2 番）の終わりのポケモンチェックで自動的に回復
print([(e["kind"], e.get("reason")) for e in state.log if e["kind"] == "special_conditions_removed"])
# [('special_conditions_removed', 'paralysis_end')]
```

- マヒは、マヒ状態になった番の「次の自分（そのポケモンの持ち主）の番」の終わりのポケモンチェックで、コインなしで回復します（p.323）。マヒ状態は、なった番（`Paralyzed.turn`）を持ち、回復する番は持ち主の番を数えて決めます（番の数 + 1 ではない）。
- ねむりは、ポケモンチェックのたびに持ち主がコインを投げ、「おもて」なら回復します（p.322・p.323）。ログは `coin_flip`（`source: "pokemon_check"`、`effect: "sleep"`）と `sleep_check`（`recovered`）です。
- ねむり・マヒ・こんらんは重複しません。マヒのポケモンがねむりになったら、マヒは消えてねむりになります（p.322。ログ `special_conditions_removed` の `reason` は `replaced`）。どくはほかの特殊状態と重複します。
- ねむり・マヒのポケモンでも、ポケモンいれかえでは入れ替えます（p.325）。ベンチに戻ったら特殊状態はすべて消えます（p.311・p.322）。エネルギーをつける・ベンチに出す・トレーナーを使うことはできます（p.322）。
- ポケモンチェックでは、どくのダメージ（2）→ どくのきぜつ・サイド・交代 → ねむりのコイン（3）→ マヒの回復（4）→ 次の番の順に行います。どくできぜつしたポケモンのねむりのコインは投げません（[docs/pokemon-check-v0.3b.md](docs/pokemon-check-v0.3b.md)）。
- 両方の対戦ポケモンがねむりのときは、どちらが先にコインを投げるかが原典で決まらないので、コインを投げる前に対戦を止めます（`Phase.HALTED`、`UNRESOLVED_POKEMON_CHECK_SLEEP_COIN_ORDER`。対応カードでは起こらない）。
- ねむり・マヒは形式 5（`special_conditions` の `sleep: {}`・`paralysis: {"turn": n}`）で書き出せます。

### 自分へのダメージと同時のきぜつ（v0.2f）

ピカチュウ（PMCG1-035）の「でんげき」は、相手の対戦ポケモンに 30 ダメージを与え、コインを投げて「うら」なら自分にも 10 ダメージを与えます（p.125 の最新の説明「コインを投げて「うら」なら、自分にも10ダメージ。」）。自分へのダメージも「ワザによるダメージ」で、相手へのダメージと同じ p.321 の順番で計算します。

```python
from kyuura_engine import (
    AttachEnergy, EndTurn, PlaceStartingPokemon, ReportJankenResult, UseAttack,
    apply_command, expand_decklist, new_game,
)

deck0 = expand_decklist({"PMCG1-035": 4, "PMCG1-018": 4, "PMCG1-016": 4, "PMCG1-060": 4, "PMCG1-037": 4,
                         "PMCG1-100": 40})   # ピカチュウ（PMCG1-035）4 枚、雷エネルギー 40 枚
deck1 = expand_decklist({"PMCG1-025": 4, "PMCG1-029": 4, "PMCG1-052": 4, "PMCG1-053": 4, "PMCG1-058": 4,
                         "PMCG1-099": 20, "PMCG1-102": 20})
state = new_game(deck0, deck1, seed=9)

def in_hand(player, card_id):
    return next(uid for uid in state.players[player].hand if state.cards[uid].card_id == card_id)

state = apply_command(state, PlaceStartingPokemon(0, in_hand(0, "PMCG1-035")))   # ピカチュウをバトル場に
basics = [uid for uid in state.players[1].hand if state.card_def(uid).is_basic_pokemon]
state = apply_command(state, PlaceStartingPokemon(1, basics[0], tuple(basics[1:6])))
state = apply_command(state, ReportJankenResult(winner=0))
state = apply_command(state, AttachEnergy(0, in_hand(0, "PMCG1-100"), state.players[0].active.card))
state = apply_command(state, EndTurn(0))
state = apply_command(state, EndTurn(1))
state = apply_command(state, AttachEnergy(0, in_hand(0, "PMCG1-100"), state.players[0].active.card))
state = apply_command(state, UseAttack(0, 1))   # でんげき: 相手に 30 → コイン → 「うら」なら自分にも 10
print([e["result"] for e in state.log if e["kind"] == "coin_flip"])   # ['tails']
print([(e["player"], e["amount"], e.get("target")) for e in state.log if e["kind"] == "damage"])
# [(1, 30, None), (0, 10, 'self')]
print(state.players[0].active.damage)   # 10
```

- 自分へのダメージには、ピカチュウについているプラスパワー（5 段階 +10）とディフェンダー（7 段階 −20）が一度ずつ効きます（p.257 の解説）。相手についているディフェンダーは変えません。ログ `damage` に `target: "self"`・`pokemon_id`・`effect` が加わります。
- 自分へのダメージでピカチュウがきぜつしたら、相手がサイドを取ります（p.323）。相手のポケモンもいっしょにきぜつしたら「同時」で（p.324。ログ `knock_out` に `simultaneous`）、サイドは番のプレイヤー → 相手、バトル場に出すのは番でないプレイヤー → 番のプレイヤーの順に、決定（`take_prize`・`promote_active`）が 1 つずつ出ます。勝ち負けは両方がサイドを取ってから p.311 の表で決め、両方が最後のサイドを取ったらサドン・デスです（延長戦は未実装で、`Phase.SUDDEN_DEATH` で止まる）。
- 両方がサイドを取る順番は、原典（p.325）では番のプレイヤーが決めますが、どちらの順でも選べるもの・情報・結果が変わらないので、選ばせずに番のプレイヤーから取ります（[docs/simultaneous-ko-v0.2f.md](docs/simultaneous-ko-v0.2f.md) 5 章）。
- 自分へのダメージの弱点・抵抗力は、ワザを使うポケモンのタイプと自分の弱点・抵抗力で計算します（v0.3d。p.90 の解説「自分自身が受けるダメージは、「プラスパワー」、弱点・抵抗力などの影響を受ける」。SUPPORTED）。v0.2f〜v0.3c では、自分のタイプが自分の弱点・抵抗力のタイプなら `UNRESOLVED_SELF_DAMAGE_WEAKNESS_RESISTANCE` で止めていました（ピカチュウでは起こらないので、対戦の結果は変わらない。[docs/unresolved-rulings-v0.3d.md](docs/unresolved-rulings-v0.3d.md) 6 章）。

### コインを投げるワザ（v0.2d）

ドードー（PMCG1-061）の「みだれづき」は、コインを 2 枚投げ、「おもて」の数×10 のダメージを相手の対戦ポケモンに与えます（p.231 の最新の説明）。コインはワザの処理の中でエンジンが投げ（対戦の乱数）、1 枚ごとにログ `coin_flip` が残ります。

```python
from kyuura_engine import (
    AttachEnergy, PlaceStartingPokemon, ReportJankenResult, UseAttack,
    apply_command, expand_decklist, new_game,
)

deck0 = expand_decklist({"PMCG1-061": 4, "PMCG1-018": 4, "PMCG1-016": 4, "PMCG1-060": 4, "PMCG1-037": 4,
                         "PMCG1-098": 40})   # ドードー（PMCG1-061）4 枚
deck1 = expand_decklist({"PMCG1-025": 4, "PMCG1-029": 4, "PMCG1-052": 4, "PMCG1-053": 4, "PMCG1-058": 4,
                         "PMCG1-099": 20, "PMCG1-102": 20})
state = new_game(deck0, deck1, seed=9)

def in_hand(player, card_id):
    return next(uid for uid in state.players[player].hand if state.cards[uid].card_id == card_id)

state = apply_command(state, PlaceStartingPokemon(0, in_hand(0, "PMCG1-061")))   # ドードーをバトル場に
basics = [uid for uid in state.players[1].hand if state.card_def(uid).is_basic_pokemon]
state = apply_command(state, PlaceStartingPokemon(1, basics[0], tuple(basics[1:6])))
state = apply_command(state, ReportJankenResult(winner=0))
state = apply_command(state, AttachEnergy(0, in_hand(0, "PMCG1-098"), state.players[0].active.card))
state = apply_command(state, UseAttack(0, 0))   # みだれづき: コインを 2 枚投げ、「おもて」の数×10
print([e["result"] for e in state.log if e["kind"] == "coin_flip"])   # ['tails', 'heads']
print([e for e in state.log if e["kind"] == "damage"][-1]["steps"])   # (('1 基本となる計算', 10),)
```

- 「おもて」が 0 枚なら、ダメージ計算は 2 段階のあとで終わり、「ダメージを与えなかった」ことになります（p.321。ログ `damage` に `stopped_after_step_2`）。プラスパワーをつけていても +10 されません。ワザは使ったことになり、番は終わります。
- 「おもて」が 1 枚以上なら、弱点・抵抗力・プラスパワーは、今までどおり p.321 の段階で計算します。
- エネルギーが足りないなど、ワザを使えない操作は拒否され、コインは投げません（渡した状態も乱数も変わらない）。

### 進化（v0.4a）

手札の 1 進化カードを、「○○から進化」の名前の自分の場のポケモン（バトル場・ベンチ）に重ねます（p.309・p.310）。`EvolvePokemon(player, card, target)` の `target` は場のポケモンの番号（`pokemon_id`）で、進化しても番号は変わりません。

```python
from kyuura_engine import (
    AttachEnergy, EndTurn, EvolvePokemon, IllegalActionError, PlaceStartingPokemon, ReportJankenResult, UseAttack,
    apply_command, expand_decklist, new_game, state_to_dict,
)

deck0 = expand_decklist({"PMCG2-003": 4, "PMCG2-010": 4, "PMCG1-016": 4, "PMCG1-060": 4, "PMCG1-037": 4,
                         "PMCG1-097": 40})   # パラス（PMCG2-003）・パラセクト（PMCG2-010）4 枚ずつ、草エネルギー 40 枚
deck1 = expand_decklist({"PMCG1-025": 4, "PMCG1-029": 4, "PMCG1-052": 4, "PMCG1-053": 4, "PMCG1-058": 4,
                         "PMCG1-099": 20, "PMCG1-102": 20})
state = new_game(deck0, deck1, seed=8)

def in_hand(player, card_id):
    return next(uid for uid in state.players[player].hand if state.cards[uid].card_id == card_id)

state = apply_command(state, PlaceStartingPokemon(0, in_hand(0, "PMCG2-003")))   # パラスをバトル場に
basics = [uid for uid in state.players[1].hand if state.card_def(uid).is_basic_pokemon]
state = apply_command(state, PlaceStartingPokemon(1, basics[0], tuple(basics[1:6])))   # ヒトデマンと控え
state = apply_command(state, ReportJankenResult(winner=0))
paras = state.players[0].active.pokemon_id      # 場のポケモンの番号。進化しても変わらない
state = apply_command(state, AttachEnergy(0, in_hand(0, "PMCG1-097"), state.players[0].active.card))
try:   # おたがいの最初の番には進化できない（p.310）
    apply_command(state, EvolvePokemon(0, in_hand(0, "PMCG2-010"), paras))
except IllegalActionError as error:
    print(error.code)   # FIRST_TURN_EVOLUTION
state = apply_command(state, EndTurn(0))
state = apply_command(state, AttachEnergy(1, in_hand(1, "PMCG1-099"), state.players[1].active.card))
state = apply_command(state, UseAttack(1, 0))   # ヒトデマンのワザでパラスに 20

# 3 番: パラスをパラセクトに進化させる。ダメージ・エネルギーはそのまま
state = apply_command(state, EvolvePokemon(0, in_hand(0, "PMCG2-010"), paras))
parasect = state.players[0].active
print(state.card_def(parasect.card).name_ja, parasect.pokemon_id == paras, parasect.damage, len(parasect.energy))
# パラセクト True 20 1
print([state.cards[uid].card_id for uid in parasect.evolution_stack], parasect.played_turn, parasect.evolved_turn)
# ['PMCG2-003'] 0 3（下のカード、場に出た番（対戦準備は 0）、進化した番）
state = apply_command(state, AttachEnergy(0, in_hand(0, "PMCG1-097"), parasect.card))
state = apply_command(state, UseAttack(0, 0))   # パラセクトのキノコのほうし: 相手をねむりにする
print(state.players[1].active.conditions.asleep)   # True（ポケモンチェックのねむりのコインは「うら」）
print(state_to_dict(state, format_version=7)["players"][0]["active"]["evolution_stack"])
# [{'card': 0, 'card_id': 'PMCG2-003'}]
try:   # 形式 1〜6 は進化しているポケモンを書き出せない
    state_to_dict(state, format_version=6)
except ValueError:
    print("形式 6 では書き出せない")
```

- おたがいの最初の番（1 番・2 番）には進化できません（`FIRST_TURN_EVOLUTION`）。その番に場に出したポケモン・その番に進化したポケモンも進化できません（`PLAYED_THIS_TURN`・`EVOLVED_THIS_TURN`。p.310）。名前が違えば `EVOLUTION_NAME_MISMATCH` です。1 回の番に何匹進化させてもかまいません。
- ダメージ・エネルギー・ついているトレーナー（プラスパワー・ディフェンダーの効果と有効期限も）はそのまま受け継ぎます（p.310）。HP・タイプ・弱点・抵抗力・にげる・ワザは、いちばん上のカードのものになります。
- 特殊状態はすべて消えます（p.322。ログ `special_conditions_removed`、`reason: "evolve"`）。こんらんで「にげる」に失敗したポケモンが進化したら、失敗の記録も消え（ログ `retreat_failure_cleared`）、同じ番にまた「にげる」を宣言できます（p.310・p.311・p.322 から導いた。SUPPORTED）。
- 進化したポケモンがきぜつしたら、重なったカードもすべてトラッシュし（p.313）、相手が取るサイドは 1 枚です（p.323）。
- 進化したあとの HP が、のっているダメージ以下になる場合は、原典で決められないので、状態を変えずに `UnsupportedError`（`UNRESOLVED_EVOLUTION_HP`）です（対応カードは HP が増えるので起こらない）。
- 対応している進化カードは、パラセクト（PMCG2-010）とジュゴン（PMCG1-030）だけです（v0.4b でトランセル・コクーン、v0.4c で 2 進化のスピアーを加えた。下の「2 進化（v0.4c）」）。ベイビィ・退化は未実装です。

### かたまる（v0.4b）

トランセル（PMCG1-003）・コクーン（PMCG1-009）の「かたまる」は、コインを投げて「おもて」なら、次の相手の番、そのポケモンは「ダメージを受けない」状態になります（p.18・p.21 の最新の説明「コインを投げて「おもて」なら、次の相手の番、このカードはダメージを受けない。（ダメージ以外の効果は受ける）」）。効果は場のポケモンの `persistent_effects` に入ります（特殊状態・ついているトレーナーとは別）。

```python
from kyuura_engine import (
    AttachEnergy, EndTurn, EvolvePokemon, PlaceStartingPokemon, ReportJankenResult, UseAttack,
    apply_command, expand_decklist, new_game, state_to_dict,
)

deck0 = expand_decklist({"PMCG1-004": 4, "PMCG1-009": 4, "PMCG1-016": 4, "PMCG1-060": 4, "PMCG1-037": 4,
                         "PMCG1-097": 40})   # ビードル（PMCG1-004）・コクーン（PMCG1-009）4 枚ずつ、草エネルギー 40 枚
deck1 = expand_decklist({"PMCG1-025": 4, "PMCG1-029": 4, "PMCG1-052": 4, "PMCG1-053": 4, "PMCG1-058": 4,
                         "PMCG1-099": 20, "PMCG1-102": 20})
state = new_game(deck0, deck1, seed=65)

def in_hand(player, card_id):
    return next(uid for uid in state.players[player].hand if state.cards[uid].card_id == card_id)

state = apply_command(state, PlaceStartingPokemon(0, in_hand(0, "PMCG1-004")))   # ビードルをバトル場に
basics = [uid for uid in state.players[1].hand if state.card_def(uid).is_basic_pokemon]
state = apply_command(state, PlaceStartingPokemon(1, basics[0], tuple(basics[1:6])))   # ヒトデマンと控え
state = apply_command(state, ReportJankenResult(winner=0))
for player, energy in ((0, "PMCG1-097"), (1, "PMCG1-099")):   # 1 番・2 番: エネルギーをつけて番を終える
    state = apply_command(state, AttachEnergy(player, in_hand(player, energy), state.players[player].active.card))
    state = apply_command(state, EndTurn(player))

# 3 番: コクーンに進化して「かたまる」。コインが「おもて」なら、次の相手の番（4 番）にダメージを受けない
state = apply_command(state, EvolvePokemon(0, in_hand(0, "PMCG1-009"), state.players[0].active.pokemon_id))
state = apply_command(state, AttachEnergy(0, in_hand(0, "PMCG1-097"), state.players[0].active.card))
state = apply_command(state, UseAttack(0, 0))
print(state.players[0].active.persistent_effects)
# (PreventDamage(source_card=..., source_player=0, created_turn=3, active_turn=4),)

# 4 番: ヒトデマンの「ひらてうち」。コクーンへのダメージの要素は無効（計算しない。ログは damage_prevented）
before = len(state.log)
state = apply_command(state, UseAttack(1, 0))
print([e["kind"] for e in state.log[before:]][:5])
# ['attack', 'damage_prevented', 'persistent_effect_removed', 'turn_end', 'pokemon_check']
print(state.players[0].active.damage, state.players[0].active.persistent_effects)   # 0 ()（4 番の終わりに消えた）
print(state_to_dict(state, format_version=8)["players"][0]["active"]["persistent_effects"])   # []
```

- 「ダメージを受けない」状態のポケモンにダメージを与えるワザの要素は無効です（p.321。ダメージを計算しない。ログ `damage_prevented`）。ダメージ以外の効果（どく・マヒ・こんらん・ねむり）・ほかのポケモンへのダメージ（でんげきの自分への 10）は有効で、効果のコインも投げます。
- 効果がはたらくのは次の相手の番だけで、その番の終わりに消えます（ログ `persistent_effect_removed`、`reason: "expired"`）。ポケモンチェックはどちらの番でもないので、どくのダメージは受けます（p.323）。
- ベンチに戻る（にげる・ポケモンいれかえ）・進化・きぜつでも消え、一度消えたら復活しません（p.311・p.322・p.323）。ついているプラスパワー・ディフェンダーは進化しても受け継ぎます（別のもの）。
- ドードーの「みだれづき」（コインでダメージの量を決める）をこのポケモンに使うと、無効になる要素のコインを投げるかが原典で決められないので、コインの前に `UnsupportedError`（`UNRESOLVED_PREVENTED_COIN_DAMAGE`）です。
- `state_to_dict(state, format_version=8)` の場のポケモンごとの `persistent_effects` に書き出されます（形式 1〜7 は効果があると `ValueError`）。

### 2 進化（v0.4c）

手札の 2 進化カードを、「○○から進化」の名前の自分の場の 1 進化ポケモンに重ねます（同じ `EvolvePokemon`。p.309・p.316・p.319）。対応している 2 進化カードはスピアー（PMCG1-012。コクーンから進化）だけです。

```python
from kyuura_engine import (
    AttachEnergy, EndTurn, EvolvePokemon, IllegalActionError, PlaceStartingPokemon, ReportJankenResult, UseAttack,
    apply_command, expand_decklist, new_game, state_to_dict,
)

deck0 = expand_decklist({"PMCG1-004": 4, "PMCG1-009": 4, "PMCG1-012": 4, "PMCG1-097": 48})
# ビードル（PMCG1-004）・コクーン（PMCG1-009）・スピアー（PMCG1-012）4 枚ずつ、草エネルギー 48 枚
deck1 = expand_decklist({"PMCG1-025": 4, "PMCG1-029": 4, "PMCG1-052": 4, "PMCG1-053": 4, "PMCG1-058": 4,
                         "PMCG1-099": 20, "PMCG1-102": 20})
state = new_game(deck0, deck1, seed=1)

def in_hand(player, card_id):
    return next(uid for uid in state.players[player].hand if state.cards[uid].card_id == card_id)

state = apply_command(state, PlaceStartingPokemon(0, in_hand(0, "PMCG1-004")))   # ビードルをバトル場に
basics = [uid for uid in state.players[1].hand if state.card_def(uid).is_basic_pokemon]
state = apply_command(state, PlaceStartingPokemon(1, basics[0], tuple(basics[1:6])))
state = apply_command(state, ReportJankenResult(winner=0))
weedle = state.players[0].active.pokemon_id      # 場のポケモンの番号。2 進化しても変わらない
for player, energy in ((0, "PMCG1-097"), (1, "PMCG1-099")):   # 1 番・2 番: エネルギーをつけて番を終える
    state = apply_command(state, AttachEnergy(player, in_hand(player, energy), state.players[player].active.card))
    state = apply_command(state, EndTurn(player))

# 3 番: ビードルをコクーンに進化。同じ番にはスピアーに進化できない（p.310）
state = apply_command(state, EvolvePokemon(0, in_hand(0, "PMCG1-009"), weedle))
try:
    apply_command(state, EvolvePokemon(0, in_hand(0, "PMCG1-012"), weedle))
except IllegalActionError as error:
    print(error.code)   # EVOLVED_THIS_TURN
state = apply_command(state, AttachEnergy(0, in_hand(0, "PMCG1-097"), state.players[0].active.card))
state = apply_command(state, EndTurn(0))
state = apply_command(state, EndTurn(1))

# 5 番: コクーンをスピアーに進化（2 進化）。重なりは下から ビードル・コクーン
state = apply_command(state, EvolvePokemon(0, in_hand(0, "PMCG1-012"), weedle))
beedrill = state.players[0].active
print(state.card_def(beedrill.card).name_ja, beedrill.pokemon_id == weedle, beedrill.played_turn, beedrill.evolved_turn)
# スピアー True 0 5
print([state.cards[uid].card_id for uid in beedrill.cards()])   # ['PMCG1-004', 'PMCG1-009', 'PMCG1-012']
state = apply_command(state, AttachEnergy(0, in_hand(0, "PMCG1-097"), beedrill.card))
before = len(state.log)
state = apply_command(state, UseAttack(0, 0))   # ダブルニードル: コイン 2 枚、「おもて」の数 × 30
print([e["result"] for e in state.log[before:] if e["kind"] == "coin_flip"], state.players[1].active.damage)
# ['heads', 'heads'] 60
print(state_to_dict(state, format_version=8)["players"][0]["active"]["evolution_stack"])
# [{'card': 2, 'card_id': 'PMCG1-004'}, {'card': 5, 'card_id': 'PMCG1-009'}]
```

- 同じ番に 1 進化したポケモンは、その番には 2 進化できません（`EVOLVED_THIS_TURN`）。次の自分の番にはできます。ほかのポケモンは同じ番に進化させてかまいません（制限は 1 匹ごと）。
- たねポケモンに 2 進化カードを直接重ねることはできません（ビードルにスピアーは `EVOLUTION_NAME_MISMATCH`）。2 進化カードは手札から場に直接出せません（`NOT_BASIC_POKEMON`）。
- ダメージ・エネルギー・ついているトレーナー・場に出た番・場のポケモンの番号は受け継ぎ、特殊状態・持続する効果・にげるの失敗の記録は消えます（1 進化と同じ）。HP・ワザなどはいちばん上のスピアーのものです（コクーンと同じ HP 80）。
- 2 進化ポケモンがきぜつしたら、ビードル・コクーン・スピアーの 3 枚と、ついているカードをすべてトラッシュし、相手が取るサイドは 1 枚です。
- ダブルニードルを「かたまる」で「ダメージを受けない」状態のポケモンに使うと、みだれづきと同じく、コインの前に `UnsupportedError`（`UNRESOLVED_PREVENTED_COIN_DAMAGE`）です。どくばりは、ダメージの要素だけが無効で、コインとどくは有効です。
- 状態の辞書は形式 8 のままで、`evolution_stack` が下から順に 2 つになります。

### ふきとばし・メガドレイン（v0.4d）

バタフリー（PMCG2-007。トランセルから進化する 2 進化）の「ふきとばし」は、20 ダメージのあと、相手の対戦ポケモンをベンチにもどし、**相手が選んだ**控えポケモンをバトル場に出します。エンジンはワザの途中で止まり、相手の決定（`state.decision`。種類 `forced_switch`）を待ちます。番のプレイヤーはワザを使ったプレイヤーのままです。「メガドレイン」は、相手に与えたダメージの半分（10 単位に切り上げ）のダメージカウンターを、バタフリーから、のっている数までとりのぞきます。

```python
from kyuura_engine import (
    AttachEnergy, EndTurn, EvolvePokemon, PlaceStartingPokemon, ReportJankenResult, ResolveDecision, UseAttack,
    apply_command, expand_decklist, new_game, state_to_dict,
)

deck0 = expand_decklist({"PMCG1-002": 4, "PMCG1-003": 4, "PMCG2-007": 4, "PMCG1-097": 48})
# キャタピー（PMCG1-002）・トランセル（PMCG1-003）・バタフリー（PMCG2-007）4 枚ずつ、草エネルギー 48 枚
deck1 = expand_decklist({"PMCG1-025": 4, "PMCG1-029": 4, "PMCG1-052": 4, "PMCG1-053": 4, "PMCG1-058": 4,
                         "PMCG1-099": 20, "PMCG1-102": 20})
state = new_game(deck0, deck1, seed=1)

def in_hand(player, card_id):
    return next(uid for uid in state.players[player].hand if state.cards[uid].card_id == card_id)

state = apply_command(state, PlaceStartingPokemon(0, in_hand(0, "PMCG1-002")))   # キャタピーをバトル場に
basics = [uid for uid in state.players[1].hand if state.card_def(uid).is_basic_pokemon]
state = apply_command(state, PlaceStartingPokemon(1, basics[0], tuple(basics[1:6])))
state = apply_command(state, ReportJankenResult(winner=0))
me = state.players[0].active.pokemon_id

def my_turn(evolve_to=None):
    global state
    if evolve_to:
        state = apply_command(state, EvolvePokemon(0, in_hand(0, evolve_to), me))
    state = apply_command(state, AttachEnergy(0, in_hand(0, "PMCG1-097"), state.players[0].active.card))

def their_turn():
    global state
    p = state.players[1]
    energy = next(u for u in p.hand if state.card_def(u).is_basic_energy)
    state = apply_command(state, AttachEnergy(1, energy, p.active.card))
    state = apply_command(state, EndTurn(1))

my_turn(); state = apply_command(state, EndTurn(0)); their_turn()                 # 1・2 番
my_turn("PMCG1-003"); state = apply_command(state, EndTurn(0)); their_turn()      # 3 番: トランセルに進化
my_turn("PMCG2-007")                                                               # 5 番: バタフリーに 2 進化
print([state.cards[uid].card_id for uid in state.players[0].active.cards()])
# ['PMCG1-002', 'PMCG1-003', 'PMCG2-007']

# ふきとばし（無色 2）: 20 ダメージのあと、相手が入れ替わる控えを選ぶ決定を待つ（番はプレイヤー 0 のまま）
target = state.players[1].active
state = apply_command(state, UseAttack(0, 0))
d = state.decision
print(state.phase.value, state.current_player, d.kind, d.player, d.options)
# decision 0 forced_switch 1 (3, 4)       決定するのはプレイヤー 1、選べるものは相手のベンチのポケモンの番号
print(state_to_dict(state, format_version=8)["decision"]["context"])
# {'use': [0, 1, 'PMCG2-007', 0], 'target': 2}
state = apply_command(state, ResolveDecision(1, d.id, (d.options[1],)))   # 相手（プレイヤー 1）が答える
event = next(e for e in state.log if e["kind"] == "forced_switch")
print(event["player"], event["attacker"], event["old_active_pokemon_id"], event["new_active_pokemon_id"])
# 1 0 2 4
print(state.current_player, state.players[1].active.pokemon_id == d.options[1])   # 入れ替えのあと番が終わった
# 1 True
print(next(p.damage for p in state.players[1].bench if p.pokemon_id == target.pokemon_id))   # ダメージはいっしょに移る
# 20

# 6 番: 相手は新しいバトル場のポケモンにエネルギーをつけてワザを使う
p = state.players[1]
state = apply_command(state, AttachEnergy(1, next(u for u in p.hand if state.card_def(u).is_basic_energy), p.active.card))
print(state.card_def(state.players[1].active.card).name_ja)
# パウワウ
state = apply_command(state, UseAttack(1, 0))
print(state.players[0].active.damage)
# 10

# 7 番: 草エネルギーが 4 個になったので、メガドレイン（40）。与えたダメージの半分（切り上げ）のカウンターを自分からとりのぞく
my_turn()
before = len(state.log)
state = apply_command(state, UseAttack(0, 1))
for e in state.log[before:]:
    if e["kind"] in ("damage", "drain_heal"):
        print(e["kind"], {k: e[k] for k in ("amount", "dealt", "counters", "total_damage") if k in e})
# damage {'amount': 40, 'total_damage': 40}
# drain_heal {'amount': 10, 'dealt': 40, 'counters': 1, 'total_damage': 0}   半分の 2 個のうち、のっている 1 個だけ
```

- 決定を待つ間は、どちらのプレイヤーの通常の操作も `WRONG_PHASE` です。答えられるのは相手（`decision.player`）だけで、ワザを使ったプレイヤーの答えは `NOT_YOUR_DECISION`、古い決定の番号は `WRONG_DECISION`、相手のベンチにいないポケモンの番号は `INVALID_CHOICE` です（どれも状態を変えません）。
- 相手に控えがいなければ入れ替えません（決定なし。ログ `forced_switch_skipped`）。20 ダメージで相手の対戦ポケモンがきぜつするなら、入れ替えずに通常のきぜつ・サイド・交代です。
- ベンチにもどったポケモンの特殊状態・持続する効果（「かたまる」）は消えます。ダメージ・エネルギー・ついているトレーナー・場のポケモンの番号はそのままです。「にげる」ではないので、にげるエネルギーもこんらんのコインもありません。
- メガドレインの「与えたダメージ」は、弱点・抵抗力・プラスパワー・ディフェンダーを計算した最終ダメージで、相手の残りの HP で上限を付けません（p.319）。最終ダメージが 0 のとき・「ダメージを受けない」状態の相手のときは、ダメージを与えていないので回復しません。
- 状態の辞書は形式 8 のままで、決定は `decision`（`player`・`options`・`context`）に入ります。形式 1 はワザの途中の決定を表せないので `ValueError` です。

### ポケモンパワー・エナジートランス（v0.5）

自分の番に、自分の場のポケモン（バトル場・ベンチ）の特殊能力（ポケモンパワー）を使います（`UsePokemonPower`。p.311）。対応している特殊能力はフシギバナ（PMCG1-011）の「エナジートランス」だけで、1 回の使用で、自分の場のポケモンについている「草」の基本エネルギーカード 1 枚（`energy`）を、そのポケモン（`source`）から自分の場の別のポケモン（`target`）につけかえます（ポケモンは場のポケモンの番号で指す）。使っても番は終わらず、何度でも使えます。

```python
from kyuura_engine import (
    AttachEnergy, EndTurn, EvolvePokemon, IllegalActionError, PlaceStartingPokemon, ReportJankenResult, UseAttack,
    UsePokemonPower, apply_command, expand_decklist, new_game,
)

deck0 = expand_decklist({"PMCG1-001": 4, "PMCG1-008": 4, "PMCG1-011": 4, "PMCG1-097": 48})
# フシギダネ（PMCG1-001）・フシギソウ（PMCG1-008）・フシギバナ（PMCG1-011）4 枚ずつ、草エネルギー 48 枚
deck1 = expand_decklist({"PMCG1-025": 4, "PMCG1-029": 4, "PMCG1-052": 4, "PMCG1-053": 4, "PMCG1-058": 4,
                         "PMCG1-099": 20, "PMCG1-102": 20})
state = new_game(deck0, deck1, seed=130)

def in_hand(player, card_id):
    return next(uid for uid in state.players[player].hand if state.cards[uid].card_id == card_id)

bulbasaurs = [uid for uid in state.players[0].hand if state.cards[uid].card_id == "PMCG1-001"]
state = apply_command(state, PlaceStartingPokemon(0, bulbasaurs[0], tuple(bulbasaurs[1:2])))   # バトル場とベンチにフシギダネ
basics = [uid for uid in state.players[1].hand if state.card_def(uid).is_basic_pokemon]
state = apply_command(state, PlaceStartingPokemon(1, basics[0], tuple(basics[1:6])))
state = apply_command(state, ReportJankenResult(winner=0))
active, bench = state.players[0].active.pokemon_id, state.players[0].bench[0].pokemon_id
for player, energy in ((0, "PMCG1-097"), (1, "PMCG1-099")):   # 1 番・2 番: エネルギーをつけて番を終える
    state = apply_command(state, AttachEnergy(player, in_hand(player, energy), state.players[player].active.card))
    state = apply_command(state, EndTurn(player))
# 3 番: バトル場のフシギダネをフシギソウに進化。ベンチのフシギダネに草エネルギー
state = apply_command(state, EvolvePokemon(0, in_hand(0, "PMCG1-008"), active))
state = apply_command(state, AttachEnergy(0, in_hand(0, "PMCG1-097"), state.players[0].bench[0].card))
state = apply_command(state, EndTurn(0))
state = apply_command(state, EndTurn(1))

# 5 番: フシギソウをフシギバナに進化（2 進化）。その番にエナジートランスを使える
state = apply_command(state, EvolvePokemon(0, in_hand(0, "PMCG1-011"), active))
state = apply_command(state, AttachEnergy(0, in_hand(0, "PMCG1-097"), state.players[0].active.card))
venusaur = state.players[0].active
print(state.card_def(venusaur.card).name_ja, [p.name_ja for p in state.card_def(venusaur.card).powers], len(venusaur.energy))
# フシギバナ ['エナジートランス'] 2
grass = state.players[0].bench[0].energy[0]   # ベンチのフシギダネの草エネルギー
before = len(state.log)
state = apply_command(state, UsePokemonPower(0, venusaur.pokemon_id, 0, energy=grass, source=bench, target=active))
print([e["kind"] for e in state.log[before:]], state.current_player, state.energy_attachments_this_turn)
# ['pokemon_power', 'move_energy'] 0 1      番は続き、手札からつけた回数（この番は 1）は変わらない
print(len(state.players[0].active.energy), state.players[0].bench[0].energy)
# 3 []
try:
    apply_command(state, UsePokemonPower(0, venusaur.pokemon_id, 0, energy=grass, source=active, target=active))
except IllegalActionError as error:
    print(error.code)   # SAME_POKEMON（移動先は、移動元と別のポケモン）
```

- 使えるのは番のプレイヤーの通常の段階（`Phase.MAIN`）だけです。決定を待つ間は `WRONG_PHASE`、ワザを使ったあとは相手の番なので `NOT_YOUR_TURN` です。
- 特殊能力を使うフシギバナがねむり・マヒ・こんらんなら `POKEMON_ASLEEP`・`POKEMON_PARALYZED`・`POKEMON_CONFUSED` です（コインは投げない）。どくだけなら使えます。ベンチのフシギバナは特殊状態にならないので、いつでも使えます。移動元・移動先の特殊状態は関係しません。
- 「草」でないエネルギーは `WRONG_ENERGY_TYPE`、相手のポケモンは `SOURCE_NOT_YOURS`・`TARGET_NOT_YOURS`、移動元についていないエネルギーは `ENERGY_NOT_ATTACHED`、選ぶものが足りなければ `POWER_CHOICE_MISSING` です。特殊能力のないポケモン（進化前のフシギソウなど）は `NO_POKEMON_POWER`、実装を登録していない特殊能力は `UNSUPPORTED_POKEMON_POWER`（`UnsupportedError`）です。どれも状態・乱数・ログを変えません。
- つけかえは手札からエネルギーをつけること（1 番に 1 回）ではないので、`energy_attachments_this_turn` は変わりません。乱数も使いません。ワザ・にげるに必要なエネルギーは、そのときついているエネルギーで決まります。
- ログは `pokemon_power`（宣言）のすぐあとに `move_energy`（`energy`・`from_pokemon_id`・`to_pokemon_id`）です。手札からつけた `attach_energy` とは別です。
- 1 回の使用で 1 枚は実装上の仮定です（何度でも使えるので、何枚まとめて移しても結果は同じ。[docs/energy-transfer-v0.5.md](docs/energy-transfer-v0.5.md) 3 章）。

### 操作（コマンド）

| コマンド | 内容 |
|---|---|
| `PlaceStartingPokemon(player, active, bench)` | 対戦準備: バトル場に 1 匹、ベンチに 5 匹まで |
| `DrawMulliganCards(player, count)` | 対戦準備: 相手の切り直し 1 回ぶん、0〜2 枚引く |
| `ReportJankenResult(winner)` | 対戦準備: ジャンケンの勝者（先攻） |
| `PlayBasicToBench(player, card)` | 手札のたねポケモンをベンチに出す |
| `AttachEnergy(player, energy, target)` | エネルギーをつける（1 番に 1 枚） |
| `Retreat(player, discard, new_active)` | にげる（何度でも）。ねむり・マヒのポケモンは宣言できない（`POKEMON_ASLEEP`・`POKEMON_PARALYZED`。v0.3b）。こんらんのポケモンはエネルギーをトラッシュしてからコイン、「うら」なら失敗し、そのポケモンはその番もう宣言できない（`RETREAT_ALREADY_FAILED`。v0.3c） |
| `UseAttack(player, attack_index)` | ワザを使う（番が終わる）。コインを投げるワザ（v0.2d・v0.2f・v0.3a・v0.3b・v0.3c）は、エンジンがコインを投げる。番の終わりのあと、エンジンがポケモンチェックをする（v0.3a）。ねむり・マヒのポケモンは使えない（v0.3b）。こんらんのポケモンは宣言のあとでコイン、「うら」なら自分に 20 で番が終わる（v0.3c）。「ダメージを受けない」状態の相手へのダメージの要素は無効（v0.4b） |
| `EndTurn(player)` | ワザを使わずに番を終える（そのあとポケモンチェック。v0.3a） |
| `TakePrize(player, index)` | 相手のポケモンがきぜつしたとき、サイドを 1 枚選んで取る（自分のワザで自分のポケモンがきぜつしたら相手が取る。v0.2f） |
| `PromoteActive(player, pokemon)` | バトル場のポケモンがいなくなったとき、ベンチから出す |
| `ResolveDecision(player, decision, choices)` | 保留中の決定に答える（どの種類の決定にも使える。v0.2a）。答えるのは `decision.player`（v0.4d のふきとばしでは、ワザを使われた側のプレイヤー） |
| `PlayTrainer(player, card)` | 手札のトレーナーカードを使う（v0.2b。対応した 5 枚だけ。プラスパワーは v0.2c、ディフェンダーは v0.2e） |
| `EvolvePokemon(player, card, target)` | 手札の進化カードで、自分の場のポケモン（`target` は場のポケモンの番号）を進化させる（v0.4a。v0.4c から 1 進化 → 2 進化も。対応した進化カードだけ） |
| `UsePokemonPower(player, pokemon, power=0, energy=None, source=None, target=None)` | 自分の場のポケモン（`pokemon` は場のポケモンの番号）の特殊能力を使う（v0.5。番は終わらない。対応した特殊能力だけ。エナジートランスは `energy`・`source`・`target` を指定する） |

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
- 特殊状態（v0.3a〜v0.3c）: どく・ねむり・マヒ・こんらん。バトル場のポケモンだけがなり、ベンチに戻ったら消える。ねむり・マヒ・こんらんは重複せず、どくはほかと重複する（p.322）。ねむり・マヒはワザ・にげるができない（p.309・p.311）。こんらんはワザ・にげるの宣言のあとでコイン（「うら」ならワザは自分に 20、にげるは失敗。p.309・p.311・p.322）。ポケモンチェック（番と番のあいだ。指示されたこと → どく → ねむり → マヒ。p.323）で、どくは 10（弱点・抵抗力・プラスパワー・ディフェンダーは関係しない。p.322）、ねむりは持ち主のコインで回復、マヒは持ち主の次の番の終わりに回復
- 自分へのワザのダメージ（v0.2f）: p.320 のワザの要素の順番、p.321 の計算の順番。きぜつしたらきぜつしたポケモンの相手側がサイドを取る（p.323）。1 つのワザで複数がきぜつしたら同時（p.324）。両方の対戦ポケモンがきぜつしたら番でないプレイヤーが先に出す（pp.323〜324）
- 勝ち負け: サイドを取り終えた、バトル場に出せるポケモンがいない、番の最初に山札がない。同時に満たしたら p.311 の表
- トレーナーカード（v0.2b）: 自分の番に何枚でも使える、使ったらトラッシュ、使っている最中はほかのことができない（p.310）。効果で引くときは山札が足りなくても負けにならない（p.312）
- ついているトレーナー（v0.2c）: ポケモンのいる場所にある（p.313）。にげるときはいっしょに移り（p.311）、きぜつしたらいっしょにトラッシュ（p.323）。ダメージ計算の 5 段階（p.321）
- ディフェンダー（v0.2e）: 自分の場のポケモンにつけ、次の相手の番の終わりにトラッシュ。ワザで受けるダメージを 7 段階（p.321）で −20
- コイントス（v0.2d）: 「おもて」か「うら」（p.319）。ワザの説明のコインは、ワザを使う手順 6 で投げる（p.309）。「×」のダメージは説明にしたがって計算し、0 倍もある（p.320）
- 進化（v0.4a）: 手札の「○○から進化」の進化カードを、その名前の自分の場のポケモンに重ねる（p.309・p.324）。おたがいの最初の番・その番に場に出した・進化したポケモンはできない（p.310）。ダメージ・エネルギー・ついているトレーナーを受け継ぎ、特殊状態は消える（p.310・p.322）。進化したポケモンがきぜつしたら、重なったカードもすべてトラッシュ（p.313）。たねポケモン → 1 進化（v0.4a）と 1 進化 → 2 進化（v0.4c。重なりは 3 枚まで。p.319。同じ番の 1 進化 → 2 進化はできない）
- ワザの途中の相手の決定（v0.4d）: ワザの説明が相手に選ばせるとき（ふきとばし）、ワザの途中で相手の決定を待ち、答えのあとで同じワザの続きだけを処理する。待つ間はどちらのプレイヤーもほかの操作をできない（p.309）。相手の強制交代では、ベンチにもどったポケモンの特殊状態・持続する効果が消える（p.311・p.322）
- 与えたダメージ（v0.4d）: 最終ダメージ（HP で上限を付けない。0 以下・「ダメージを受けない」なら与えていない。p.319・p.321）。メガドレインはその半分（10 単位に切り上げ）を自分から回復する
- ポケモンの特殊能力（v0.5）: 自分の場のポケモン（ベンチも）の特殊能力のうち、そのとき使えるものを宣言して使う。特に指示されていないかぎり、何度でも・エネルギーなしでも使え、使っても番は終わらない。進化前の特殊能力は使えない。宣言したら、すべてすませてから（p.311・p.323）。特殊状態の制限は特殊能力の説明ごと（エナジートランスは「このカード」のねむり・マヒ・こんらん）
- ワザによる持続する効果（v0.4b）: ワザが与え、番をまたいで残る（p.322）。「かたまる」の効果（次の相手の番、ダメージを受けない）は、そのポケモンへのダメージの要素を無効にし（p.321）、次の相手の番の終わりに消える。ベンチに戻る・場をはなれる・進化で消え、復活しない（p.311・p.322・p.323）。ポケモンチェックははたらかない（p.323）

## 現在の対応カード

第1弾の、効果のないワザだけを持つたねポケモン 10 種と、基本エネルギー 6 種、トレーナー 5 種（v0.2b・v0.2c・v0.2e）（kyuura docs/engine-readiness.md 5章の段階 1 とディフェンダー）、コインを投げるワザを持つドードー（v0.2d）、自分へのダメージのワザを持つピカチュウ（v0.2f）、相手をどく状態にするワザを持つビードル（v0.3a）、相手をマヒ・ねむり状態にするワザを持つキャタピー・パラス（v0.3b）、相手をこんらん状態にするワザを持つロコン（v0.3c）、1 進化ポケモンのパラセクト・ジュゴン（v0.4a）・トランセル・コクーン（v0.4b）、2 進化ポケモンのスピアー（v0.4c）・バタフリー（v0.4d）、ポケモンパワーを持つ 2 進化ポケモンのフシギバナとその進化元のフシギダネ・フシギソウ（v0.5）です。『オフィシャルブック2000』のカードのページと照合済みです（ポニータ・フシギソウのワザ名、きずぐすり・ポケモンいれかえ・ディフェンダーの文面、ドードーのワザの説明の書き方に食い違い。[docs/data-provenance.md](docs/data-provenance.md)）。

| id | カード | id | カード |
|---|---|---|---|
| PMCG1-016 | ポニータ | PMCG1-053 | ワンリキー |
| PMCG1-018 | ガーディ | PMCG1-058 | エビワラー |
| PMCG1-025 | ヒトデマン | PMCG1-060 | コラッタ |
| PMCG1-029 | パウワウ | PMCG1-065 | ミニリュウ |
| PMCG1-037 | ビリリダマ | PMCG1-097〜102 | 草・炎・水・雷・超・闘エネルギー |
| PMCG1-052 | ディグダ | PMCG1-061 | ドードー（v0.2d。みだれづき: コイン 2 枚、「おもて」の数×10。p.231） |
| PMCG1-035 | ピカチュウ（v0.2f。かじる 10、でんげき 30・コインが「うら」なら自分にも 10。p.125） | PMCG1-004 | ビードル（v0.3a。どくばり 10・コインが「おもて」なら相手をどく状態に。p.19） |
| PMCG1-002 | キャタピー（v0.3b。いとをはく 10・コインが「おもて」なら相手をマヒ状態に。p.17） | PMCG2-003 | パラス（v0.3b。ひっかく 20、キノコのほうし（ダメージなし）で相手をねむり状態に。p.38） |
| PMCG1-015 | ロコン（v0.3c。あやしいひかり 10・コインが「おもて」なら相手をこんらん状態に。p.67） | PMCG2-010 | パラセクト（v0.4a。パラスから進化。キノコのほうし（ダメージなし）で相手をねむり状態に、きりさく 30。p.39） |
| PMCG1-030 | ジュゴン（v0.4a。パウワウから進化。オーロラビーム 50、れいとうビーム 30・コインが「おもて」なら相手をマヒ状態に。p.102） | PMCG1-003 | トランセル（v0.4b。キャタピーから進化。かたまる（コインが「おもて」なら次の相手の番ダメージを受けない）、しびれごな 20・コインが「おもて」なら相手をマヒ状態に。p.18） |
| PMCG1-009 | コクーン（v0.4b。ビードルから進化。かたまる、どくのこな 20・コインが「おもて」なら相手をどく状態に。p.21） | PMCG1-012 | スピアー（v0.4c。コクーンから進化する 2 進化。ダブルニードル 30×（コイン 2 枚の「おもて」の数 × 30）、どくばり 40・コインが「おもて」なら相手をどく状態に。p.21） |
| PMCG2-007 | バタフリー（v0.4d。トランセルから進化する 2 進化。ふきとばし 20・相手の対戦ポケモンを相手が選んだ控えと入れ替える、メガドレイン 40・与えたダメージの半分（切り上げ）のダメージカウンターを自分からとりのぞく。p.19） | PMCG1-001 | フシギダネ（v0.5。やどりぎのタネ 20・ダメージを与えたら自分のダメージカウンターを 1 個とりのぞく。p.13） |
| PMCG1-008 | フシギソウ（v0.5。フシギダネから進化。つるのむち 30、どくのこな 20・コインなしで相手をどく状態に。p.14） | PMCG1-011 | フシギバナ（v0.5。フシギソウから進化する 2 進化。ポケモンパワー「エナジートランス」: 自分の番の中で何度でも、自分の場のポケモンについている「草」エネルギーを別の自分のポケモンにつけかえる、ソーラービーム 60。p.16・p.323） |

| id | トレーナー（v0.2b） | 処理（『オフィシャルブック2000』p.254 の最新の説明） | 原典で決められないため止める場合 |
|---|---|---|---|
| PMCG1-074 | マサキ | 山札からカードを2枚引いて、手札に加える（足りなければ引けるだけ） | なし |
| PMCG1-071 | きずぐすり | 自分の場のポケモンを1匹選び、ダメージカウンターを2個とりのぞく | ダメージのあるポケモンがいない、ダメージのないポケモンを選ぶ |
| PMCG1-073 | ポケモンいれかえ | 自分の控えポケモンを1匹選び、対戦ポケモンと入れ替える | 控えポケモンがいない |
| PMCG1-079 | ディフェンダー（v0.2e。p.257） | 自分の場のポケモンを1匹選んでつけ、次の相手の番の終わりにトラッシュ。ついているポケモンがワザで受けるダメージを 7 段階で −20 | なし |
| PMCG1-081 | プラスパワー（v0.2c。p.257） | 自分の対戦ポケモンにつけて使い、自分の番の終わりにトラッシュ。ついているポケモンのワザが対戦ポケモンに与えるダメージを 5 段階で +10（控えへのダメージは変えない） | なし |

これ以外のカード（ドードーのほかの効果のあるワザを持つポケモン、ほかの進化カード（スピアー・バタフリー・フシギバナのほかの 2 進化を含む）、エナジートランスのほかのポケモンパワーを持つカード、ほかのトレーナー、特殊エネルギーなど）はデッキに入れられません。効果のあるワザを「ダメージだけのワザ」として扱うことはしません。対戦用のたねポケモンのワザは、効果の登録表に「効果のないワザ」として 1 つずつ登録してあります（v0.2a）。v0.2a で対応したカード・ルールは v0.1 と同じです。トレーナーは、カード id で効果の実装を登録した 5 枚だけが使えます（v0.2b・v0.2c・v0.2e）。説明文のあるワザは、ドードーの「みだれづき」（v0.2d）、ピカチュウの「でんげき」（v0.2f）、ビードルの「どくばり」（v0.3a）、キャタピーの「いとをはく」・パラスの「キノコのほうし」（v0.3b）、ロコンの「あやしいひかり」（v0.3c）、パラセクトの「キノコのほうし」・ジュゴンの「れいとうビーム」（v0.4a）、トランセル・コクーンの「かたまる」「しびれごな」「どくのこな」（v0.4b。かたまるはカードごとに照合し、印刷の文面ではなく最新の説明にしたがう）、スピアーの「ダブルニードル」「どくばり」（v0.4c。ビードルのどくばりとは別に、スピアーのカード id で登録）、バタフリーの「ふきとばし」「メガドレイン」（v0.4d。印刷の文面ではなく最新の説明にしたがう）、フシギダネの「やどりぎのタネ」・フシギソウの「どくのこな」（v0.5。どくのこなはコクーンのものと違いコインを投げない）だけを、照合した説明文とともに登録しています。ポケモンパワーは、フシギバナの「エナジートランス」（v0.5）だけを、照合した文面とともに登録しています（パラセクトのキノコのほうしは、パラスと同じ名前なので同じとは決めず、p.39 で照合した）。

## 未実装の機能

退化・パラセクト・ジュゴン・トランセル・コクーン・スピアー・バタフリー・フシギソウ・フシギバナのほかの進化カード、ほかの相手の強制交代・与えたダメージによる回復のワザ、「かたまる」のほかのワザによる持続する効果（すなかけ・からまるいと・マーカーをのせる効果など）、ポケモンチェックの 1（指示されたこと）、特殊などく、エナジートランスのほかのポケモンパワー（自動的にはたらく・常にはたらく・回数の制限のある・特殊能力を止める・決定を出す特殊能力。[docs/architecture-v0.5.md](docs/architecture-v0.5.md) 9 章）、ほかのトレーナーカード、スタジアム、ポケモンのどうぐ、ベイビィポケモン、特殊エネルギー、効果のあるワザ（みだれづき・でんげきのほか。特殊状態・控えへのダメージ・でんげき以外の自分へのダメージ・「うら」で失敗などのコインのワザを含む）、コインを使うトレーナー、ワザの失敗、サドン・デスの延長戦、旧裏の複数の時期のルールの切り替え、大会のレギュレーション、隠れた情報の管理（見る人ごとの状態）、合法な操作の一覧、状態を辞書からもどす処理、AI、GUI、Web アプリ、ネットワーク対戦。一覧は [docs/implementation-status.md](docs/implementation-status.md#未実装)。

原文から決められないため止める処理: 両方が同時に切り直したあと、片方だけがさらに切り直した場合の補償（`Phase.HALTED`）。トレーナーの上の表の場合（`UnsupportedError`。対戦は続けられる）。ポケモンチェックのどくで両方のプレイヤーのポケモンがきぜつする場合（v0.3a。`Phase.HALTED`）。ポケモンチェックで両方の対戦ポケモンがねむりの場合（v0.3b。`Phase.HALTED`。対応カードでは起こらない）。マヒの再付与で回復する番が変わる場合（v0.3b。`UnsupportedError`。対応カードでは起こらない）。ダメージを変えるカードがついたこんらん状態のポケモンのワザ、「にげる」に失敗したあとこんらんが消えて同じ番にバトル場に戻ったポケモンの「にげる」（v0.3c。`UnsupportedError`。コインの前）。v0.3d で調べ直し、どれも原典で決められないので止めたままです（[docs/unresolved-rulings-v0.3d.md](docs/unresolved-rulings-v0.3d.md)。v0.4a〜v0.4c でも変えていない）。進化したあとの HP が、のっているダメージ以下になる場合（v0.4a。`UnsupportedError`、`UNRESOLVED_EVOLUTION_HP`。対応カードでは起こらない。[docs/evolution-rules-v0.4a.md](docs/evolution-rules-v0.4a.md)）。「ダメージを受けない」状態（「かたまる」）のポケモンに、コインでダメージの量を決めるワザ（みだれづき、v0.4c からスピアーのダブルニードルも）を使う場合（v0.4b。`UnsupportedError`、`UNRESOLVED_PREVENTED_COIN_DAMAGE`。コインの前。[docs/persistent-damage-v0.4b.md](docs/persistent-damage-v0.4b.md) 5 章）。2 進化で新しく止める場合はありません（v0.4c）。相手の強制交代・与えたダメージによる回復（v0.4d）でも、新しく止める場合はありません（ふきとばしの致死ダメージ・「ダメージを受けない」相手へのメガドレインは原典から導けた。[docs/forced-switch-v0.4d.md](docs/forced-switch-v0.4d.md) 4 章・[docs/damage-drain-v0.4d.md](docs/damage-drain-v0.4d.md) 4 章）。ポケモンパワー・エナジートランス・やどりぎのタネ・どくのこな（v0.5）でも、新しく止める場合はありません（[docs/pokemon-powers-v0.5.md](docs/pokemon-powers-v0.5.md) 3 章）。

## ディレクトリ

```
kyuura_engine/
  rules.py       ルールの組（2000.02.14版の数値）と根拠の一覧
  conditions.py  特殊状態（どく・ねむり・マヒ・こんらん）を付ける・置きかえる・回復する・ベンチに戻ったら・進化したら消す。v0.3a〜v0.4a
  persistent.py  ワザによる持続する効果（「かたまる」の「ダメージを受けない」）を付ける・期限・ベンチ・進化・きぜつで消す・はたらいているか。v0.4b
  cards.py       カードの定義、kyuura のデータの読み込み、対応・未対応の分類
  effects.py     効果の登録表（ワザ: カード id・ワザの位置 → 実装、トレーナー: カード id → 実装）と、トレーナー 5 枚・みだれづき・でんげき・どくばり・いとをはく・キノコのほうし・あやしいひかり・れいとうビーム・かたまるの実装（v0.4c のスピアーのワザは既存の実装の登録）、ふきとばし（ワザの途中の相手の決定）・メガドレイン（v0.4d）の実装、ワザのダメージを与える処理（相手・自分。v0.2f。「ダメージを受けない」状態なら無効。v0.4b。結果 `DamageResult` を返す。v0.4d）。決定を出すトレーナーの決定の形の宣言（`decision_problems`。v0.4e）。ポケモンパワーの登録（カード id・パワーの位置 → 実装）とエナジートランス、やどりぎのタネ・どくのこな（コインなし）の実装（v0.5）。v0.2a〜v0.5
  coins.py       コイントス（対戦の乱数で決め、1 枚ごとにログに残す）。v0.2d
  deck.py        デッキの検査
  state.py       ゲームの状態（ゾーン、場のポケモン、進化の重なり（v0.4a。v0.4c から 2 進化の 3 枚まで）・場に出た番・進化した番（v0.4a）、ワザによる持続する効果（v0.4b）、特殊状態（v0.3a〜v0.3c）、にげるの失敗の記録（v0.3c）、番、結果）
  commands.py    プレイヤーの操作
  decisions.py   保留中の決定（出す・確かめる）。v0.2a
  engine.py      対戦の進行（new_game・apply_command）、きぜつ・サイド・勝ち負け・交代（同時のきぜつは v0.2f）、ポケモンチェック（v0.3a・v0.3b）、こんらんのワザ・にげるのコイン（v0.3c）、進化（v0.4a。2 進化は v0.4c）、不変条件（v0.4e でトレーナーの決定・サイドと交代の決定・番の番号を強めた）
  damage.py      ワザのダメージ計算（p.321 の 8 段階。2・5〜8 段階の変更効果は v0.2c）、こんらんの 20 の計算（v0.3c）
  judge.py       勝ち負けの判定（p.311 の表）
  serialize.py   状態を辞書にする（形式 1〜8）
  zones.py       山札から引く・トレーナーをポケモンにつける処理（エンジンとトレーナーで共通）。v0.2b・v0.2c
  rng.py         乱数の状態の指紋・保存・復元。v0.2a（コインも同じ乱数）
  data/kyuura_cards.json       kyuura のカードデータの写し（生成物）
  data/card_verification.json  『オフィシャルブック2000』との照合の記録
scripts/extract_kyuura_cards.py  kyuura から写しを作る
scripts/make_compat_fixture.py   v0.1 の対戦結果の参照データを作った道具（作り直さない）
tools/compat_driver.py           版の比較の駆動（公開の API だけで 1 つの版を動かし、1 手ごとの記録を作る）。v0.4e
tools/compare_engine_versions.py 2 つの版の比較（git archive で取り出し、版ごとに別のプロセス。最初の食い違いを診断）。v0.4e
tools/stress_engine.py           大規模なストレス実行（ふだんのテストでは走らせない）。v0.4e。v0.5 でフシギバナの組（エナジートランスの使用を混ぜる）
tests/                           自動テスト（unittest）。tests/log_audit.py はログと書き出しの監査の道具（v0.4e。テストではない）
tests/fixtures/                  v0.1 の対戦結果の参照データ、v0.4d（4bd97bf）の記録の指紋（v0.4e。互換性のテスト用）
docs/                            ルールの仕様、実装状況、データの由来、v0.1 のレビュー、API のレビュー、v0.2a〜v0.5 のアーキテクチャ、トレーナー・コイントス・みだれづき・ディフェンダー・自分へのダメージ・同時のきぜつ・ピカチュウ・特殊状態・ポケモンチェック・ビードル・ねむり・マヒ・キャタピー・パラス・こんらん・ロコンの原典照合、特殊状態の総合検証・未解決の裁定・コインの前の検証（v0.3d）、進化の準備（v0.4）、進化のルール・カード・状態の持ち方（v0.4a）、持続する効果・かたまる・持続する効果とダメージ計算（v0.4b）、2 進化のルール・スピアー・3 枚の重なりの状態（v0.4c）、相手の強制交代・与えたダメージと回復・バタフリー（v0.4d）、総合監査・組み合わせの表・互換性・未解決の範囲・v0.5 の準備（v0.4e）、ポケモンパワーの規定・フシギバナ・フシギダネとフシギソウ・エナジートランスの処理・確かめた結果（v0.5）
```

# 状態スナップショット（U6）の仕様案

この文書は U6「JSON の状態の保存・復元」の**仕様案**です（状態 `proposed`、承認 `not_approved`）。保存・復元の機能はまだ実装していません。利用者が採用したのは 3 章の原則だけで、スキーマの細部・自動移行の方法・実装は採用していません（8 章の判断事項と、[実装計画](state-snapshot-implementation-plan.md)）。

構造化した仕様は [state-snapshot-design.json](state-snapshot-design.json) です。この文書の表（`<!-- generated:… -->` の区画）は、JSON と同じ元（`scripts/build_state_snapshot_design.py` の `SPEC`）から作ります。区画の中を手で直さないでください（`--check` が違いと、コードの項目との食い違いを見つけます）。

関係する文書: [診断 API と対戦記録・再現インターフェースの仕様案](diagnostics-replay-api-design.md)（U6 の位置づけ・版の表）、[再現用記録 v0.153](replay-record-v0.153.md)（実装の識別・確認値）、[再実行 v0.154](replay-run-v0.154.md)、[閲覧用記録 v0.155](view-record-v0.155.md)。

## 1. 基点と範囲

- 基点: `ffc48f9`（v0.155 の最後。`origin/claude/view-record-u5`。`origin/main` の `8d4beff` はその祖先）。作業ブランチ `claude/state-snapshot-spec`。エンジンの版は 0.155.0 のまま
- この作業でしたこと: U5 の過去のログの情報境界の確かめ（2 章。修正は要らなかった。別のコミット）、状態の全項目の棚卸しと分類（4 章）、スナップショットの契約（5 章）、状態別の扱い（6 章）、復元の手順（7 章）、継続一致の検証計画（実装計画）
- しないこと: U6 の保存・復元の API の本体、旧形式の自動移行、異なる規約集合での再開、停止の解除、合法手・AI・画面・通信、閲覧用記録の差分、実装の識別の方式の変更

## 2. U5 の過去のログの情報境界（確かめた結果）

うらのカード（マチスの秘策）をあとでおもてにすると、`visible_log` は**過去のイベントの uid も見せる**（構築盤面で確かめた: うらのポケモンにつけたエネルギーの `attach_energy` の `target` が、おもてにする前は `None`、あとは uid）。閲覧用記録が毎回ログを取り直していれば、ここから過去の非公開の情報が漏れる。

確かめた結果、閲覧用記録ではこの経路は起きない（修正は要らなかった）:

- 収集器は、前に記録した位置より後ろのログだけを、その時点の `visible_log` から写す。過去の位置の内容を取り直さない・更新しない・同じ位置を 2 回出さない
- 延長戦で区間が変わるときも、前の区間のまだ記録していない位置だけを写す
- 完全な記録からの変換も同じ収集器（`ViewRecorder.add`）を通る（マチスの秘策を含む合法な対戦の記録での変換は確かめていない。コードが同じことによる）
- テスト: `tests/test_view_record_v0_155.py` の `PastLogBoundaryTest`（構築盤面から合法な操作）。詳しくは [v0.155 の文書の追記](view-record-v0.155.md)

途中から始めた記録（`attach`）の保証の範囲: 始まりの項目の過去のログは、**記録を始めた時点の投影**で固定する。各イベントが起きた時点の投影は作り直さない（その時点の知識は状態に残っていないので、推測で作らない）。始めた位置は `header.origin` が `attached` で表す。各イベントが起きた時点の投影を持つのは、対戦の開始から集めた記録（`origin` が `new_game`）だけ。

## 3. 採用した原則（範囲つき）

<!-- generated:adoption begin -->
- `ADOPT-U6-PRINCIPLES`（2026-11-06・利用者）: U6 の仕様の作成と次の原則だけ。スキーマの細部・自動移行の方法・U6 の実装の承認ではない
  - 原則:
    - スナップショットは形式 35 をそのまま復元の形式に使わず、必要な全状態を明示した独立の形式にする
    - 初めの対応範囲は、同じ実装・依存データ・規約集合に限る
    - カード定義・規約は、原則として識別の情報から登録済みのものを解決する
    - 乱数の状態を正確に保存・復元する
    - 決定待ちを保存・復元の対象に含める
    - HALTED・途中停止も保存・復元できる設計にする。停止の解除・未対応の続行は認めない
    - 不正・未知の状態を推測で補ったり移したりしない
    - スナップショットは完全な情報を持つホスト用で、閲覧用記録と分ける
    - 完了の基準は JSON の往復だけでなく、復元のあとの同じ操作の列で状態・乱数・ログ・観測が同じこと
  - 仕様案（diagnostics-replay-api-design.json）の判断事項: D-SNAPSHOT-BASE、D-HALT-SNAPSHOT
<!-- generated:adoption end -->

診断の仕様案の判断事項 D-SNAPSHOT-BASE（形式 35 を元にするか）と D-HALT-SNAPSHOT（停止の状態を保存するか）は、この原則で決まった（形式 35 をそのまま使わない・停止も保存できるが解除しない）。スナップショットの具体的なスキーマは、8 章の判断事項と実装の段階で決める。

## 4. 状態の全項目の棚卸しと分類

対象: `kyuura_engine/state.py` の dataclass のすべて（`GameState` から参照される型と、持続する効果・履歴・マーカーなどの値の記録の型）と `rules.RuleSet`。`GameState` の型ヒントは前方参照（`EffectRegistry` など）を含むので、参照をたどるのではなく、`state.py` で定義した dataclass をすべて対象にした（`tuple[Any, ...]` の項目に入る型も、ここで漏れなく数える）。`--check` は、分類表とコードの型・項目を**名前で**照らす（件数では照らさない）。コードに型・項目が加わると、分類がないものとして見つける。

<!-- generated:categories begin -->
| 分類 | 意味 | 状態の dataclass の項目 | 項目でない値（対応表の鍵・一時的な属性・モジュールの変数） | 見出しの補助情報 | 計 |
|---|---|---|---|---|---|
| `value` | 1. JSON に値を保存する | 526 | 0 | 0 | 526 |
| `resolve` | 2. 固定した登録・依存データから解決する | 18 | 0 | 0 | 18 |
| `derive` | 3. ほかの保存値から作り直す | 0 | 1 | 0 | 1 |
| `absent` | 4. 保存の境界では存在してはいけない | 1 | 2 | 0 | 3 |
| `descriptive` | 5. 説明用で復元には使わない | 0 | 0 | 3 | 3 |
| 計 |  | 545 | 3 | 3 | 551 |
<!-- generated:categories end -->

数の訂正（v0.157 の最初）: v0.156 の報告は、分類ごとの数（525＋18＋1＋3＋3＝550）と「545 項目」を同じ表の数のように書いていた。545 は**状態の dataclass の項目**（state.py の dataclass 86 型の 531 項目と RuleSet の 14 項目）の数で、550 はそれに**項目でない属性**（`GameState._history_probe`・`zones.IDENTITY_CONSULTED` の 2 つ）と**見出しの補助情報**（3 つ）を足した数。別のものを 1 つの数に足さないよう、表を 3 つの列に分けた（分類は変えていない）。状態の dataclass の項目の数は、コードの項目の名前と照らした数と同じ（`tests/test_state_snapshot_design.py`）。

uid の訂正（v0.157 の最初。数の訂正とは別のコミット）: v0.156 は `CardInstance.uid` を「cards の鍵から作り直す（derive）」にしていた。確かめた結果:

- uid は、領域（山札・手札・サイド・トラッシュ・場）・ついているカード・決定の `options` と `context`・持続する効果の `source_card`・マーカー・履歴・ログ・過去の区間のログが、同じ整数で同じカードを指す識別。同名のカードが複数あっても uid で区別する
- `new_game` は deck0・deck1 の並びの位置（0 から）で付け（`engine.new_game`）、延長戦の開始（`_start_sudden_death`）も、とりかえっこプリーズの所有者の交換（`zones` の交換）も付け直さない。次の uid のような採番の状態を持つ項目はない（カードは対戦の途中で増えない）
- `new_game` の状態ではデッキリストの並びから作り直せるが、構築盤面（デッキリストが空）では作り直せない

そのため、uid は `CardInstance` の値として**カードごとに明示して保存する**（分類を value に訂正）。作り直すのは対応表の鍵だけで（4.4 の表の derive）、鍵と uid が同じこと・uid が重ならないことを保存の前と復元で確かめる。名前・今の場所から付け直さない。分類の数は、状態の dataclass の項目の value が 1 増え、derive が項目でない値に移った。

### 4.1 GameState の項目

<!-- generated:game-state begin -->
| GameState の項目 | 分類 | 根拠 | 確かめ |
|---|---|---|---|
| `rules` | resolve | RuleSet の id だけを保存し、登録のルールの組（replay_record.KNOWN_RULES。今は RULES_2000_02_14 だけ）から解決する。値は数値の組で、入力から作らない | 知らない id は unsupported。解決したルールの組が保存した id と同じ |
| `card_data` | value | カードデータの写しの元（repository・commit・path）。カードの定義は持たない | 既定のカードプールの写しの元と同じでなければ unsupported |
| `seed` | value | new_game の seed。延長戦の開始でも保持する（sudden_death の keep）。乱数は seed から作り直さない（rng を保存する） | 保存して復元した状態を、もう一度保存した JSON が同じ（往復）。継続の比べ（F） |
| `rng` | value | 乱数の状態そのもの（rng.rng_state_to_json。形式 python-random-mt19937-v3）。指紋ではなく、正確な続きのために必要 | 復元のあと rng_fingerprint が保存した確認値と同じ。継続のコイン・山札の切り方が同じ（F） |
| `cards` | value | カードの対応表。CardInstance（uid・card_id・owner・origin）を対応表の並びの順に配列で保存する。鍵は各 CardInstance.uid から作り直す（項目でない値の表の derive） | uid の重なりは不正（対応表にする前に見つける。重なりを後の値で上書きしない）。鍵と CardInstance.uid が同じ。cards の uid と、領域・場・置いておくカードに出てくる uid が同じ集まり（check_invariants） |
| `definitions` | resolve | カード id → CardDefinition。new_game がカードプールから作り、返す状態では変えない（v0.154 の確かめ。engine.py の代入は new_game・区間の開始の引き継ぎと、返さない複製だけ）。保存しない。cards に出てくる card_id から、既定のカードプール（load_card_pool）で解決する | 解決した定義の card_id の集まりが cards の card_id の集まりと同じ。知らない card_id は unsupported |
| `decklists` | value | 対戦開始時のデッキリスト（並び。uid の付け方を決め、延長戦で最初のデッキにもどすのに使う。sudden_death.initial_deck_owners）。cards から作り直せるのは並びの一部だけなので値で保存する | cards の uid の並び・出所（deck_owner）と同じ組であること |
| `players` | value | 2 人のプレイヤーの領域（PlayerState） | 保存して復元した状態を、もう一度保存した JSON が同じ（往復）。継続の比べ（F） |
| `phase` | value | Phase の値（文字列）。知らない値は不正 | 保存して復元した状態を、もう一度保存した JSON が同じ（往復）。継続の比べ（F） |
| `effects` | resolve | 効果の登録表。id だけを保存し、既定のカードプールの登録表（DEFAULT_EFFECTS）から解決する。関数・オブジェクトを入力から作らない | id が既定の登録表と同じでなければ unsupported |
| `turn_number` | value | 番の番号 | 保存して復元した状態を、もう一度保存した JSON が同じ（往復）。継続の比べ（F） |
| `current_player` | value | 番のプレイヤー | 保存して復元した状態を、もう一度保存した JSON が同じ（往復）。継続の比べ（F） |
| `first_player` | value | 先攻 | 保存して復元した状態を、もう一度保存した JSON が同じ（往復）。継続の比べ（F） |
| `energy_attachments_this_turn` | value | この番の手札からのエネルギーの数 | 保存して復元した状態を、もう一度保存した JSON が同じ（往復）。継続の比べ（F） |
| `mulligan_rounds` | value | 切り直しの記録 | 保存して復元した状態を、もう一度保存した JSON が同じ（往復）。継続の比べ（F） |
| `result` | value | 対戦の結果（GameResult） | 保存して復元した状態を、もう一度保存した JSON が同じ（往復）。継続の比べ（F） |
| `halt` | value | 停止の理由（Halt）。停止を解除しない | 保存して復元した状態を、もう一度保存した JSON が同じ（往復）。継続の比べ（F） |
| `log` | value | 今の区間のログ（イベントの並び。値はタプル・整数・文字列・真偽値・None）。ワザ・効果・不変条件・監査が読む | JSON の配列はタプルにもどす（v0.156 の調べ）。往復 |
| `next_pokemon_id` | value | 次の場のポケモンの番号 | 保存して復元した状態を、もう一度保存した JSON が同じ（往復）。継続の比べ（F） |
| `decision` | value | 保留中の決定（PendingDecision。resume・context を含む） | 保存して復元した状態を、もう一度保存した JSON が同じ（往復）。継続の比べ（F） |
| `next_decision_id` | value | 次の決定の番号 | 保存して復元した状態を、もう一度保存した JSON が同じ（往復）。継続の比べ（F） |
| `trainer_in_use` | value | 使っている最中のトレーナー（決定を待つ間） | 保存して復元した状態を、もう一度保存した JSON が同じ（往復）。継続の比べ（F） |
| `energy_attached_by_powers_this_turn` | value | この番の特殊能力でつけた数 | 保存して復元した状態を、もう一度保存した JSON が同じ（往復）。継続の比べ（F） |
| `power_uses_this_turn` | value | この番に使った特殊能力 | 保存して復元した状態を、もう一度保存した JSON が同じ（往復）。継続の比べ（F） |
| `energy_burn` | value | この番の［エナジーバーン］ | 保存して復元した状態を、もう一度保存した JSON が同じ（往復）。継続の比べ（F） |
| `trainer_locks` | value | トレーナーの使用の禁止 | 保存して復元した状態を、もう一度保存した JSON が同じ（往復）。継続の比べ（F） |
| `recalls` | value | 思い出させるの記録 | 保存して復元した状態を、もう一度保存した JSON が同じ（往復）。継続の比べ（F） |
| `trainer_effects` | value | トレーナーの期限のある効果 | 保存して復元した状態を、もう一度保存した JSON が同じ（往復）。継続の比べ（F） |
| `stadium` | value | 場のスタジアム | 保存して復元した状態を、もう一度保存した JSON が同じ（往復）。継続の比べ（F） |
| `stadium_uses_this_turn` | value | この番のスタジアムの使用 | 保存して復元した状態を、もう一度保存した JSON が同じ（往復）。継続の比べ（F） |
| `trainer_stack` | value | 外側のトレーナーの使用 | 保存して復元した状態を、もう一度保存した JSON が同じ（往復）。継続の比べ（F） |
| `energy_roles` | value | エネルギーとしてついているカード | 保存して復元した状態を、もう一度保存した JSON が同じ（往復）。継続の比べ（F） |
| `set_aside` | value | 一時的に置いておくカード（見られるプレイヤーを含む） | 保存して復元した状態を、もう一度保存した JSON が同じ（往復）。継続の比べ（F） |
| `face_up_prizes` | value | おもてのサイド | 保存して復元した状態を、もう一度保存した JSON が同じ（往復）。継続の比べ（F） |
| `face_down_cards` | value | うらにしてベンチに出したカード | 保存して復元した状態を、もう一度保存した JSON が同じ（往復）。継続の比べ（F） |
| `color_effects` | value | この番の色を変える効果 | 保存して復元した状態を、もう一度保存した JSON が同じ（往復）。継続の比べ（F） |
| `turn_history` | value | 番ごとの記録（TurnAttack・TurnField の型の印つき） | 保存して復元した状態を、もう一度保存した JSON が同じ（往復）。継続の比べ（F） |
| `poison_mists` | value | ［ポイズンミスト］の効果 | 保存して復元した状態を、もう一度保存した JSON が同じ（往復）。継続の比べ（F） |
| `replacement_poisons` | value | まだ与えていないどく | 保存して復元した状態を、もう一度保存した JSON が同じ（往復）。継続の比べ（F） |
| `frozen_forms` | value | 処理のあいだ固定した変身（決定を待つ間） | 保存して復元した状態を、もう一度保存した JSON が同じ（往復）。継続の比べ（F） |
| `face_up_deck` | value | おもての山札のカード | 保存して復元した状態を、もう一度保存した JSON が同じ（往復）。継続の比べ（F） |
| `ownership_changes` | value | 所有者の変更 | 保存して復元した状態を、もう一度保存した JSON が同じ（往復）。継続の比べ（F） |
| `pending_moves` | absent | ワザの途中の場の移動への反応のまだ処理していない段。コマンドの終わり・決定を待つ間は空（決定をまたぐ続きは決定の context の moves に移す。v0.154 の確かめ）。check_invariants は空であることを確かめない（v0.155 の注釈の訂正） | 保存の前に空でなければ保存を拒む（緩めない）。復元のあと空。U4 の境界の確かめと同じ |
| `segments` | value | 終わった区間の記録（SegmentRecord。ログ・結果・所有者の変更・うらのままだったカード） | 保存して復元した状態を、もう一度保存した JSON が同じ（往復）。継続の比べ（F） |
| `conventions` | resolve | 規約集合の識別（ID・版・照合値・構成）を保存し、登録の集合（conventions.registered_identity）から解決して照らす。規約のオブジェクト・関数を入力から作らない。記録のない旧状態（UNRECORDED）は保存しない | 登録の識別と保存した識別が同じでなければ unsupported（ほかの集合に差し替えない） |
<!-- generated:game-state end -->

U3・U4 で確かめたこととの関係:

- `definitions`: U4 で、返す状態で変わらないことを確かめた。スナップショットには入れず、`cards` の card_id から既定のカードプールで解決する（カード定義を入力から作らない）
- `decklists`: 延長戦で最初のデッキにもどすのに使う（`sudden_death.initial_deck_owners`）。並びは cards の uid の付け方と一致するが、作り直すより値で保存して照らす
- `pending_moves`: コマンドの境界では空（決定をまたぐ続きは決定の `context`）。ただし `check_invariants` は確かめない（v0.155 の注釈の訂正）ので、保存の前に空でなければ保存を拒む。不変条件は緩めない
- `conventions`: 識別を保存し、登録から解決して照らす（ほかの集合に差し替えない）。記録のない旧状態は保存しない
- 形式 35 で落ちているのは乱数の状態そのもの・カードの定義・デッキリスト・`pending_moves`・規約集合のオブジェクト（U3 の 3 章）。形式 35 で落ちていることを、保存しない理由にはしていない（乱数とデッキリストは値で保存する）

### 4.2 そのほかの主要な型

<!-- generated:explicit-types begin -->
| 項目 | 分類 | 根拠 |
|---|---|---|
| `PlayerState.deck` | value | プレイヤーの領域と準備の記録。山札・サイドの並びも秘密の値として保存する（ホスト用）。リストはリストにもどす |
| `PlayerState.hand` | value | プレイヤーの領域と準備の記録。山札・サイドの並びも秘密の値として保存する（ホスト用）。リストはリストにもどす |
| `PlayerState.prizes` | value | プレイヤーの領域と準備の記録。山札・サイドの並びも秘密の値として保存する（ホスト用）。リストはリストにもどす |
| `PlayerState.discard` | value | プレイヤーの領域と準備の記録。山札・サイドの並びも秘密の値として保存する（ホスト用）。リストはリストにもどす |
| `PlayerState.active` | value | プレイヤーの領域と準備の記録。山札・サイドの並びも秘密の値として保存する（ホスト用）。リストはリストにもどす |
| `PlayerState.bench` | value | プレイヤーの領域と準備の記録。山札・サイドの並びも秘密の値として保存する（ホスト用）。リストはリストにもどす |
| `PlayerState.placed_starting_pokemon` | value | プレイヤーの領域と準備の記録。山札・サイドの並びも秘密の値として保存する（ホスト用）。リストはリストにもどす |
| `PlayerState.mulligans` | value | プレイヤーの領域と準備の記録。山札・サイドの並びも秘密の値として保存する（ホスト用）。リストはリストにもどす |
| `PlayerState.mulligan_draws_remaining` | value | プレイヤーの領域と準備の記録。山札・サイドの並びも秘密の値として保存する（ホスト用）。リストはリストにもどす |
| `PokemonInPlay.card` | value | 場のポケモン（重なり・ついているカード・持続する効果・履歴・マーカー）。持続する効果・履歴は型の印つき |
| `PokemonInPlay.energy` | value | 場のポケモン（重なり・ついているカード・持続する効果・履歴・マーカー）。持続する効果・履歴は型の印つき |
| `PokemonInPlay.damage` | value | 場のポケモン（重なり・ついているカード・持続する効果・履歴・マーカー）。持続する効果・履歴は型の印つき |
| `PokemonInPlay.pokemon_id` | value | 場のポケモン（重なり・ついているカード・持続する効果・履歴・マーカー）。持続する効果・履歴は型の印つき |
| `PokemonInPlay.trainers` | value | 場のポケモン（重なり・ついているカード・持続する効果・履歴・マーカー）。持続する効果・履歴は型の印つき |
| `PokemonInPlay.conditions` | value | 場のポケモン（重なり・ついているカード・持続する効果・履歴・マーカー）。持続する効果・履歴は型の印つき |
| `PokemonInPlay.retreat_failed_turn` | value | 場のポケモン（重なり・ついているカード・持続する効果・履歴・マーカー）。持続する効果・履歴は型の印つき |
| `PokemonInPlay.evolution_stack` | value | 場のポケモン（重なり・ついているカード・持続する効果・履歴・マーカー）。持続する効果・履歴は型の印つき |
| `PokemonInPlay.played_turn` | value | 場のポケモン（重なり・ついているカード・持続する効果・履歴・マーカー）。持続する効果・履歴は型の印つき |
| `PokemonInPlay.evolved_turn` | value | 場のポケモン（重なり・ついているカード・持続する効果・履歴・マーカー）。持続する効果・履歴は型の印つき |
| `PokemonInPlay.persistent_effects` | value | 場のポケモン（重なり・ついているカード・持続する効果・履歴・マーカー）。持続する効果・履歴は型の印つき |
| `PokemonInPlay.attacks_used_once` | value | 場のポケモン（重なり・ついているカード・持続する効果・履歴・マーカー）。持続する効果・履歴は型の印つき |
| `PokemonInPlay.evolution_permission_turn` | value | 場のポケモン（重なり・ついているカード・持続する効果・履歴・マーカー）。持続する効果・履歴は型の印つき |
| `PokemonInPlay.type_shift` | value | 場のポケモン（重なり・ついているカード・持続する効果・履歴・マーカー）。持続する効果・履歴は型の印つき |
| `PokemonInPlay.disguise` | value | 場のポケモン（重なり・ついているカード・持続する効果・履歴・マーカー）。持続する効果・履歴は型の印つき |
| `PokemonInPlay.devolved_turn` | value | 場のポケモン（重なり・ついているカード・持続する効果・履歴・マーカー）。持続する効果・履歴は型の印つき |
| `PokemonInPlay.history` | value | 場のポケモン（重なり・ついているカード・持続する効果・履歴・マーカー）。持続する効果・履歴は型の印つき |
| `PokemonInPlay.markers` | value | 場のポケモン（重なり・ついているカード・持続する効果・履歴・マーカー）。持続する効果・履歴は型の印つき |
| `PokemonInPlay.basic_entry` | value | 場のポケモン（重なり・ついているカード・持続する効果・履歴・マーカー）。持続する効果・履歴は型の印つき |
| `PokemonInPlay.super_transform` | value | 場のポケモン（重なり・ついているカード・持続する効果・履歴・マーカー）。持続する効果・履歴は型の印つき |
| `CardInstance.uid` | value | カードの識別。領域・場・決定の options と context・持続する効果・マーカー・履歴・ログ・過去の区間が同じ整数で同じカードを指す。new_game が deck0・deck1 の並びの位置（0 から）で付け、延長戦の開始（sudden_death）・とりかえっこプリーズの交換（zones の所有者の変更）でも付け直さない。次の uid のような採番の状態を持つ項目はない（カードは new_game のあとに増えない）。構築盤面（デッキリストが空）は並びから作り直せないので、カードごとに値で保存する。名前・場所から付け直さない |
| `CardInstance.card_id` | value | カード id |
| `CardInstance.owner` | value | 対戦の中の所有者 |
| `CardInstance.origin` | value | 対戦開始時のデッキのプレイヤー（変更があったカードだけ） |
| `PendingDecision.id` | value | 保留中の決定。resume は再開先の名前、context は続きの情報（値は整数・文字列とそのタプル）。知らない再開先は supported_decision_error で unsupported |
| `PendingDecision.kind` | value | 保留中の決定。resume は再開先の名前、context は続きの情報（値は整数・文字列とそのタプル）。知らない再開先は supported_decision_error で unsupported |
| `PendingDecision.player` | value | 保留中の決定。resume は再開先の名前、context は続きの情報（値は整数・文字列とそのタプル）。知らない再開先は supported_decision_error で unsupported |
| `PendingDecision.options` | value | 保留中の決定。resume は再開先の名前、context は続きの情報（値は整数・文字列とそのタプル）。知らない再開先は supported_decision_error で unsupported |
| `PendingDecision.min_choices` | value | 保留中の決定。resume は再開先の名前、context は続きの情報（値は整数・文字列とそのタプル）。知らない再開先は supported_decision_error で unsupported |
| `PendingDecision.max_choices` | value | 保留中の決定。resume は再開先の名前、context は続きの情報（値は整数・文字列とそのタプル）。知らない再開先は supported_decision_error で unsupported |
| `PendingDecision.resume` | value | 保留中の決定。resume は再開先の名前、context は続きの情報（値は整数・文字列とそのタプル）。知らない再開先は supported_decision_error で unsupported |
| `PendingDecision.context` | value | 保留中の決定。resume は再開先の名前、context は続きの情報（値は整数・文字列とそのタプル）。知らない再開先は supported_decision_error で unsupported |
| `Halt.code` | value | 停止のコード |
| `Halt.message` | value | 診断用の文（説明用だが状態の一部。復元で変えない。閲覧者に渡さない） |
| `Halt.references` | value | 根拠の参照（説明用だが状態の一部） |
| `Halt.interruption` | value | 途中停止の記録 |
| `Interruption.kind` | value | 途中停止の記録（そこまでの処理・在途のカード） |
| `Interruption.code` | value | 途中停止の記録（そこまでの処理・在途のカード） |
| `Interruption.kyuura_issue` | value | 途中停止の記録（そこまでの処理・在途のカード） |
| `Interruption.source` | value | 途中停止の記録（そこまでの処理・在途のカード） |
| `Interruption.player` | value | 途中停止の記録（そこまでの処理・在途のカード） |
| `Interruption.target_owner` | value | 途中停止の記録（そこまでの処理・在途のカード） |
| `Interruption.target` | value | 途中停止の記録（そこまでの処理・在途のカード） |
| `Interruption.element` | value | 途中停止の記録（そこまでの処理・在途のカード） |
| `Interruption.required` | value | 途中停止の記録（そこまでの処理・在途のカード） |
| `Interruption.available` | value | 途中停止の記録（そこまでの処理・在途のカード） |
| `Interruption.pending` | value | 途中停止の記録（そこまでの処理・在途のカード） |
| `Interruption.in_transit` | value | 途中停止の記録（そこまでの処理・在途のカード） |
| `Interruption.log_index` | value | 途中停止の記録（そこまでの処理・在途のカード） |
| `SegmentRecord.index` | value | 終わった区間（ログは今の区間と同じくタプルにもどす） |
| `SegmentRecord.prize_count` | value | 終わった区間（ログは今の区間と同じくタプルにもどす） |
| `SegmentRecord.first_player` | value | 終わった区間（ログは今の区間と同じくタプルにもどす） |
| `SegmentRecord.turn_number` | value | 終わった区間（ログは今の区間と同じくタプルにもどす） |
| `SegmentRecord.mulligan_rounds` | value | 終わった区間（ログは今の区間と同じくタプルにもどす） |
| `SegmentRecord.result` | value | 終わった区間（ログは今の区間と同じくタプルにもどす） |
| `SegmentRecord.log` | value | 終わった区間（ログは今の区間と同じくタプルにもどす） |
| `SegmentRecord.ownership_changes` | value | 終わった区間（ログは今の区間と同じくタプルにもどす） |
| `SegmentRecord.face_down_cards` | value | 終わった区間（ログは今の区間と同じくタプルにもどす） |
| `GameResult.outcome` | value | 結果 |
| `GameResult.winner` | value | 結果 |
| `GameResult.conditions` | value | 結果 |
| `DataSource.repository` | value | カードデータの写しの元 |
| `DataSource.commit` | value | カードデータの写しの元 |
| `DataSource.path` | value | カードデータの写しの元 |
| `SpecialConditions.poison` | value | 特殊状態（exclusive は Asleep・Paralyzed・Confused の型の印つき） |
| `SpecialConditions.exclusive` | value | 特殊状態（exclusive は Asleep・Paralyzed・Confused の型の印つき） |
| `TrainerInUse.player` | value | 使用中のトレーナー |
| `TrainerInUse.card` | value | 使用中のトレーナー |
| `TrainerInUse.user` | value | 使用中のトレーナー |
| `TrainerInUse.via` | value | 使用中のトレーナー |
| `SetAsideCards.kind` | value | 置いておくカード |
| `SetAsideCards.owner` | value | 置いておくカード |
| `SetAsideCards.cards` | value | 置いておくカード |
| `SetAsideCards.visible_to` | value | 置いておくカード |
| `SetAsideCards.user` | value | 置いておくカード |
| `SetAsideCards.trainer_card` | value | 置いておくカード |
| `SetAsideCards.card_id` | value | 置いておくカード |
| `SetAsideCards.created_turn` | value | 置いておくカード |
| `SetAsideCards.return_turn` | value | 置いておくカード |
| `RuleSet.id` | resolve | ルールの組は id で登録から解決する（数値を入力から作らない） |
| `RuleSet.title` | resolve | ルールの組は id で登録から解決する（数値を入力から作らない） |
| `RuleSet.deck_size` | resolve | ルールの組は id で登録から解決する（数値を入力から作らない） |
| `RuleSet.max_copies_per_name` | resolve | ルールの組は id で登録から解決する（数値を入力から作らない） |
| `RuleSet.opening_hand_size` | resolve | ルールの組は id で登録から解決する（数値を入力から作らない） |
| `RuleSet.max_setup_bench` | resolve | ルールの組は id で登録から解決する（数値を入力から作らない） |
| `RuleSet.max_bench` | resolve | ルールの組は id で登録から解決する（数値を入力から作らない） |
| `RuleSet.prize_count` | resolve | ルールの組は id で登録から解決する（数値を入力から作らない） |
| `RuleSet.mulligan_draw_max_per_mulligan` | resolve | ルールの組は id で登録から解決する（数値を入力から作らない） |
| `RuleSet.first_player_draws_on_first_turn` | resolve | ルールの組は id で登録から解決する（数値を入力から作らない） |
| `RuleSet.energy_attachments_per_turn` | resolve | ルールの組は id で登録から解決する（数値を入力から作らない） |
| `RuleSet.weakness_multiplier` | resolve | ルールの組は id で登録から解決する（数値を入力から作らない） |
| `RuleSet.damage_per_counter` | resolve | ルールの組は id で登録から解決する（数値を入力から作らない） |
| `RuleSet.sudden_death_prize_count` | resolve | ルールの組は id で登録から解決する（数値を入力から作らない） |
<!-- generated:explicit-types end -->

### 4.3 値の記録の型

<!-- generated:value-records begin -->
分類はすべて `value`。値の記録（持続する効果・マーカー・履歴・効果の記録など）。すべての項目を値で保存し、型の名前の印（state.py の dataclass の名前の許した一覧）で作り直す

| 型 | 項目 |
|---|---|
| `Asleep` | （項目なし。型の印だけ） |
| `AttachedTrainer` | card, player, discard_at_end_of_turn |
| `AttackBarrier` | source_card, source_player, created_turn, active_turn |
| `AttackCoinCheck` | source_card, source_player, created_turn, active_turn, single_use, lasting |
| `AttackEffectGuard` | source_card, source_player, created_turn, active_turn |
| `AttackReceived` | turn, card, player, source, declared, processed, damage, reached, voided, active_damage |
| `AttackUsed` | turn, card, declared, processed |
| `BasicEntry` | card, source, source_card, zone, turn |
| `BenchAttackDamageGuard` | source_card, source_player, created_turn, active_turn |
| `BenchPowersStopped` | source_card, source_player, created_turn, active_turn |
| `BenchProtection` | source_card, source_player, created_turn, active_turn |
| `CannotAttachEnergy` | source_card, source_player, created_turn, active_turn |
| `CannotAttack` | source_card, source_player, created_turn, active_turn |
| `CannotAttackNextOwnTurn` | source_card, source_player, created_turn, active_turn |
| `CannotAttackWhileSourceActive` | source_card, source_player, created_turn, active_turn |
| `CannotRetreat` | source_card, source_player, created_turn, active_turn |
| `CannotRetreatNextOwnTurn` | source_card, source_player, created_turn, active_turn |
| `CannotUseAttack` | source_card, source_player, created_turn, active_turn, attack_index, target_attack_index, attack_card, target_attack_card |
| `CannotUseOwnAttack` | source_card, source_player, created_turn, active_turn, attack_index, target_attack_index, attack_card |
| `CannotUsePowers` | source_card, source_player, created_turn, active_turn |
| `ColorEffect` | kind, player, source, source_card, power_index, target, color, turn, left_play |
| `Confused` | （項目なし。型の印だけ） |
| `DamageReduction` | source_card, source_player, created_turn, active_turn, amount, non_attack_unresolved |
| `DealtAttackDamageReduction` | source_card, source_player, created_turn, active_turn, end_turn, source_pokemon, amount, while_source_active, ends_on |
| `DestinyBond` | source_card, source_player, created_turn, active_turn |
| `DoubledDamage` | source_card, source_player, created_turn, active_turn |
| `EnergyRole` | card, energy_type, units, owner, turn |
| `EvolutionLock` | source_card, source_player, created_turn, active_turn |
| `FrozenForm` | pokemon, card, kind, source |
| `HalvedDamage` | source_card, source_player, created_turn, active_turn |
| `KnockOutSurvival` | source_card, source_player, created_turn, active_turn, end_turn, scope, remaining_hp |
| `Marker` | kind, player, source_card, attack, turn, color |
| `MaxHpSet` | source_card, source_player, created_turn, active_turn, amount |
| `NextTurnAttackDamage` | source_card, source_player, created_turn, active_turn, attack_index, target_attack_index, amount, operation, includes_self_damage, attack_card |
| `NextTurnFailureWaiver` | source_card, source_player, created_turn, active_turn, attack_index, target_attack_index, target_player, target_pokemon, attack_card |
| `OtherReceived` | turn, card |
| `OwnershipChange` | card, card_id, previous, owner, origin, turn, trainer_card, exchange |
| `Paralyzed` | turn |
| `PeriodAttackCoinCheck` | source_card, source_player, created_turn, active_turn, end_turn, source_pokemon, while_source_active, ends_on |
| `PeriodAttackLock` | source_card, source_player, created_turn, active_turn, end_turn, source_pokemon, while_source_active, ends_on |
| `PeriodLeaveLock` | source_card, source_player, created_turn, active_turn, end_turn, source_pokemon, while_source_active, ends_on, knockout_exception, source_left |
| `PeriodRetreatLock` | source_card, source_player, created_turn, active_turn, end_turn, source_pokemon, while_source_active, ends_on |
| `Poison` | damage, multiplier |
| `PoisonMist` | player, pokemon_id, source_card, card_id, power_index, created_turn, poisoned_before, interrupted |
| `PowersStopped` | source_card, source_player, created_turn, active_turn |
| `PreventAttackDamage` | source_card, source_player, created_turn, active_turn |
| `PreventDamage` | source_card, source_player, created_turn, active_turn |
| `PursuitOnRetreat` | source_card, source_player, created_turn, active_turn, amount, attack |
| `RecallEffect` | player, turn, pokemon_id, card, trainer |
| `ReceivedAttackDamageBonus` | source_card, source_player, created_turn, active_turn, end_turn, source_pokemon, amount, while_source_active, ends_on |
| `ReducedDamageToSource` | source_card, source_player, created_turn, active_turn, amount |
| `ReducedDamageToSourceNextTurn` | source_card, source_player, created_turn, active_turn, amount |
| `ReflectShield` | source_card, source_player, created_turn, active_turn, attack_index, amount, attack_card |
| `ReplacementPoison` | player, knocked_pokemon_id, card_id, attack_index, attacker_player, attacker_pokemon_id, attacker_card, attacker_evolved, created_turn, status |
| `ResistanceChange` | source_card, source_player, created_turn, active_turn, color |
| `Retaliation` | source_card, source_player, created_turn, active_turn, attack_index, amount, basis, multiplier, on_heads, attack_card |
| `RetreatCostIncrease` | source_card, source_player, created_turn, active_turn, amount, attack |
| `SecretePoison` | source_card, source_player, created_turn, active_turn, attack_index, amount, attack_card |
| `StadiumInPlay` | owner, card, placed_turn |
| `StatusImmunityNextTurn` | source_card, source_player, created_turn, active_turn |
| `StatusImmunityWhileActive` | source_card, source_player, created_turn, active_turn, attack_index, given_by, attack_card |
| `StatusOnEnergyAttach` | source_card, source_player, created_turn, active_turn, condition, attack |
| `SuperTransform` | source, card, turn, left_active |
| `TailsDamageGuard` | source_card, source_player, created_turn, active_turn |
| `TimedDamageGuard` | source_card, source_player, created_turn, active_turn, prevent_on, flipper, scope |
| `TrainerTurnEffect` | kind, player, source_card, card_id, created_turn, expires_turn, pokemon_id, attack_index |
| `TrainerUseLock` | player, source_player, source_card, effect, created_turn, expires_turn, origin |
| `TurnAttack` | turn, player, pokemon_id, card, declared, processed |
| `TurnField` | turn, player, cards, face_down |
| `TypeShift` | color, turn, source_card, returned_to_bench |
| `WeaknessChange` | source_card, source_player, created_turn, active_turn, color |
| `ZeroDamageAtLeast` | source_card, source_player, created_turn, active_turn, threshold |
| `ZeroDamageBelow` | source_card, source_player, created_turn, active_turn, threshold |
<!-- generated:value-records end -->

### 4.4 dataclass の項目でない値・説明用の見出し

<!-- generated:non-field begin -->
| 名前 | 分類 | 根拠 | 確かめ |
|---|---|---|---|
| `GameState.cards の鍵` | derive | 対応表の鍵は、配列で保存した CardInstance.uid から作り直す（同じ値を 2 か所に書かない。v0.157 の訂正で、uid そのものは CardInstance の値で保存する） | 保存の前に鍵と CardInstance.uid が同じこと。復元で uid が重なれば malformed |
| `GameState._history_probe` | absent | history.open_probe が setattr で置き、close_probe がコマンドの終わりに取り除く一時的な属性（dataclass の項目ではない） | 保存の前に、状態の __dict__ に dataclass の項目のほかの名前があれば保存を拒む |
| `zones.IDENTITY_CONSULTED` | absent | モジュールの変数（受け付けるかを確かめる間だけ使う）。状態ではない | 保存・復元で扱わない（コマンドの外では None） |
| `header.git_commit` | descriptive | 補助の情報（U3 と同じ。識別に使わない） |  |
| `header.label・created_by` | descriptive | ホストが付ける説明 |  |
| `header.origin` | descriptive | どこから保存したか（完全な記録の game_id・seq など。対応付けのため） |  |
<!-- generated:non-field end -->

### 4.5 JSON との型の対応

状態には、同じ「並び」でもリスト（プレイヤーの領域・場のエネルギー・ついているトレーナー）とタプル（ほとんどの記録）が混ざり、ログと決定の `context` には入れ子のタプルがある（v0.156 で、ピカチュウの対戦の延長戦までとドライアップの途中停止までの状態から調べた）。JSON の配列からは、項目ごとに決めた型にもどす。

<!-- generated:json-types begin -->
| Python の型 | JSON | 復元 |
|---|---|---|
| tuple | 配列 | 項目の型（スキーマ）がタプルなら、入れ子までタプルにもどす（ログ・決定の context の値は、入れ子の配列をすべてタプルに） |
| list | 配列 | PlayerState の領域・PokemonInPlay.energy・trainers・GameState.players はリストにもどす（v0.156 の調べで、リストとタプルが混ざる） |
| Mapping（cards・log のイベント） | cards は CardInstance の配列（対応表の並びの順）、イベントはオブジェクト（鍵の順を保つ） | cards は配列の順に、各 CardInstance.uid を鍵にした読み取り専用の対応表に（uid の重なりは不正）。イベントは MappingProxyType に |
| enum（Phase・EnergyType の値をもつ項目） | 値の文字列 | 項目ごとに決めた列挙型の値として読む。知らない値は不正 |
| dataclass（値の記録） | オブジェクト（"type" に dataclass の名前） | 許した名前の一覧（state.py の dataclass）からだけ作る。ほかの名前・import は使わない |
| random.Random | rng_state_to_json の形 | rng_from_json（知らない形式は不正） |
| int・str・bool・None | 同じ | 真偽値と整数を取り違えない（bool は int として受けない）。浮動小数・NaN は受けない |
<!-- generated:json-types end -->

## 5. スナップショットの契約（提案）

<!-- generated:limits begin -->
- 形式: `kyuura_snapshot_format` = 1（kyuura state snapshot。proposed）。仕様案 docs/diagnostics-replay-api-design.json の版の表の kyuura_snapshot_format。形式 35（format_version）・再現用記録（kyuura_replay_format）・閲覧用記録（kyuura_view_format）とは別の番号
- max_bytes: 64 MiB（replay_record.MAX_RECORD_BYTES と同じ）
- max_depth: 64 を基本にする。状態の入れ子（決定の context・ログのタプル）の最大の深さを U6-S1 で測り、足りなければ判断事項 DS-DEPTH
- reader: replay_record.read_json_object（重なった鍵・NaN・UTF-8 でないもの・最上位が辞書でないものを拒む。誤りの文に入力の値を入れない）
- unknown: 知らない項目・知らない値（列挙・決定の種類・再開先・持続する効果の型の名前）・知らない形式の版は拒む。今の既定の値で補わない
<!-- generated:limits end -->

見出し（実装・依存・環境・規約の識別は、U3 の再現用記録の見出しと同じ関数と同じ意味にする）:

<!-- generated:header begin -->
| 項目 | 必須 | 意味 |
|---|---|---|
| `kyuura_snapshot_format` | はい | スナップショットの形式の版（1） |
| `engine` | はい | エンジンの版と実装の識別（replay_record.implementation_identity と同じ。behavior_digest で扱えるかを決める） |
| `runtime` | はい | Python の実装と版・乱数の方式（replay_record.runtime_identity と同じ。実装と major・minor が同じときだけ扱える） |
| `dependencies` | はい | ルールの組の id・カードプール（default だけ）・カードデータの写しの元・効果の登録表の id |
| `convention_set` | はい | 規約集合の ID・版・照合値・構成（ConventionSetIdentity.record） |
| `formats` | はい | 参照する形式（確認値の方式 state-export-35-sha256/1・python-random-getstate-sha256/1、診断の形式） |
| `check` | はい | 保存した状態の確認値（replay_record.checks と同じ。復元のあとに照らす期待値で、復元の入力ではない） |
| `state` | はい | 状態の値（分類 1 の項目と、分類 2 の識別）。分類 3・4 は入れない |
| `origin・label・git_commit` | いいえ | 説明用（分類 5） |
<!-- generated:header end -->

保存できる境界:

<!-- generated:boundary begin -->
- 保存できるのは、ホストが持つ安定した状態だけ: new_game・adapter.start_game の結果、受理した操作（apply_command・adapter.submit・HostedGame・ReplayCollector）のあとの状態、拒否の結果の元の状態
- コマンドの処理の途中の内部の状態（解決の基盤の途中・先読みの複製・決定の答えの処理の途中）は保存しない
- 保存の前の確かめ: check_invariants が空、pending_moves が空、__dict__ に dataclass の項目のほかの名前がない、規約集合の識別が記録されている（UNRECORDED でない）、保留中の決定の再開先をこの版が扱える、カードプールが既定のもの。どれかを満たさなければ保存を拒む（エンジンの不変条件を緩めない）
- 失敗（failed）のあとの状態は保存しない（adapter が状態を返さない）
<!-- generated:boundary end -->

カード定義・規約・ルールの組・効果の登録表は、識別から登録済みのものを解決し、入力から任意の Python のオブジェクト・関数を作らない。pickle・`GameState.__setstate__` を経由しない。スナップショットは完全な情報（山札・サイドの並び・乱数の状態・seed）を持つホスト用で、閲覧用記録（U5）・観測とは分ける（見る人に渡さない。見る人の値で取り出せる API にしない）。

## 6. 状態別の扱い

<!-- generated:states begin -->
| 状態 | 保存 | 復元のあとに許す操作 |
|---|---|---|
| 通常の対戦中（in_progress） | はい | 同じ操作をすべて受け付けうる（受理・拒否は元の状態と同じ） |
| 準備中（切り直し・ポケモンを出す・ジャンケン） | はい | 準備の操作。準備の決定待ちも同じ |
| ワザ・トレーナー・特殊能力の決定待ち（awaiting_decision） | はい | 決定への答えだけ（id・resume・context・使用中のトレーナー・固定した変身を保存する）。答えの処理の続きは元の状態と同じ |
| 受理した結果の途中停止（halted・interruption） | はい | どの操作も元の状態と同じく受け付けない。停止を解除しない・在途のカードを片付けない |
| HALTED（そのほかの停止） | はい | 同上。規約集合を差し替えて続ける API はない |
| 終局（game_over） | はい | どの操作も受け付けない（GAME_OVER） |
| サドン・デスの開始待ち（sudden_death_pending） | はい | StartSuddenDeath だけ。延長戦の準備は保存した乱数の続きで切る |
| 延長戦の途中 | はい | 通常の対戦中と同じ。segments・initial_prize_count を保存する |
| 複数の過去の区間を持つ状態 | はい | segments（区間ごとのログ・結果・所有者の変更・うらのままだったカード）をそのまま |
| pending_moves が空でない・一時的な属性がある・不変条件を満たさない | いいえ | 保存を拒む（境界の外。エンジンの不具合か、境界でない状態） |
| 記録のない規約集合（UNRECORDED）・知らない再開先の決定 | いいえ | 保存を拒む（unsupported） |
<!-- generated:states end -->

停止の状態を復元しても、停止の理由を解除したり、規約集合を差し替えて続けたりしない（その API を作らない）。復元した状態でも、操作の受理・拒否は保存した状態と同じになる（6 章の表の「許す操作」はエンジンが決めることで、スナップショットが新しく許すものではない）。

## 7. 復元と検証の順

<!-- generated:restore-steps begin -->
| 段 | 名前 | 内容 | 止まったときの結果 |
|---|---|---|---|
| 1 | 安全な JSON の読み取り | replay_record.read_json_object | read_error（RecordFormatError） |
| 2 | 形式・型・必須の項目 | 形式の版、見出し・状態の項目の過不足と型、型の印の名前、列挙の値、JSON の型（bool と int・浮動小数） | malformed |
| 3 | 実装・依存・環境・規約の対応 | behavior_digest・Python の実装と major・minor・乱数の方式・ルールの組の id・カードデータ・効果の登録表・規約集合（登録と照合値）・確認値の方式 | unsupported（状態を組み立てない） |
| 4 | 登録済みのデータの解決 | ルールの組・カードの定義（cards の card_id から）・効果の登録表・規約集合の識別。知らない card_id は unsupported | unsupported |
| 5 | 状態の組み立て | GameState を項目の値から新しく作る（pickle・__setstate__ を使わない。既定の値で補わない）。乱数は rng_from_json | malformed（型の誤り）・internal_error |
| 6 | 不変条件と領域をまたぐ整合 | check_invariants が空、require_state_conventions・supported_decision_error、pending_moves が空、decklists と cards の一致、確認値（state・rng・log_length・segment・status・decision・halt）が見出しの check と同じ、もう一度保存した JSON が入力と同じ | inconsistent（状態の不整合） |
| 7 | ホストへ返す | ホスト用の結果（復元した状態と、確かめの記録）。閲覧者には渡さない。どれかの段で止まったら状態を返さない（部分的な状態を通常の対戦に使わせない） | — |

| 結果 | 意味 |
|---|---|
| `restored` | すべての段を通った（状態を返す） |
| `read_error` | JSON として読めない・大きすぎる・深すぎる |
| `malformed` | 形式・型・必須の項目・知らない値 |
| `unsupported` | 実装・依存・環境・規約集合・形式の版・カード・再開先をこの版が扱えない |
| `inconsistent` | 組み立てた状態が不変条件・整合・確認値を満たさない（状態の不整合） |
| `internal_error` | 復元の道具の中の想定外の例外（ほかの結果に変えない。traceback は検証者用） |

- 文: 一般向けの文は結果の種類ごとの決まった文。seed・カード・非公開の領域・入力の値を入れない。項目の場所（JSON の経路）と問題の種類は検証者用の記録に置く
<!-- generated:restore-steps end -->

- 非対応・不正な入力から、部分的に組み立てた状態を通常の対戦用に返さない
- 知らない版・欠けた項目を、今の既定の値で黙って補わない（`GameState.__setstate__` の既定の値の補いは pickle の後方互換のためのもので、スナップショットでは使わない）
- 内部エラーを非対応・不正に変えない（U2〜U4 と同じ）

## 8. 継続一致の検証計画

<!-- generated:verification begin -->
| ID | 場面 | 盤面 |
|---|---|---|
| F1 | 通常の操作 | ピカチュウのデッキ seed 9（new_game から方策の操作。U3 の収集器の記録） |
| F2 | 準備中の決定待ち・対戦中の決定待ち | 準備の各段階・サイドを取る決定・山をさがす決定（v0.150 の盤面）・ドライアップの対象の決定 |
| F3 | 拒否の操作 | 記録の拒否の行（seq の順）。復元のあとも同じ診断で拒否され、状態が変わらない |
| F4 | 途中停止・HALTED | ドライアップ seed 0（受理した結果の途中停止）・たねポケモン 1 枚のデッキ seed 1（準備の停止） |
| F5 | 終局 | ピカチュウ seed 0 |
| F6 | サドン・デスの開始・複数の区間 | ピカチュウ seed 9（開始待ちで保存→ StartSuddenDeath、延長戦の途中で保存） |
| F7 | 規約が当てはまる操作 | 3 つの集合（CS-KYUURA-CURRENT@1・CS-KYUURA-PLAY-S2A@1・CS-KYUURA-PLAY-PO@1）。続行規約のログ convention_applied が出る操作を含む盤面（v0.143・v0.145 のテストの盤面） |
| F8 | 持続する効果・マーカー・うらのカード・置いておくカード・使用中のトレーナー | 既存の版のテストの構築盤面（v0.63・v0.67・v0.90 など）。構築盤面と合法な操作の列を区別する |
| F9 | 未知・不正・矛盾する入力の拒否 | 知らない項目・型の印・列挙の値・再開先、bool と int、NaN、大きすぎる入力、pending_moves、カードの重なり、確認値の違い、規約集合の照合値・Python の版の違い |

- 各境界で: 保存した全項目（スナップショットの JSON そのもの）・U3 の確認値（state・rng・log_length・segment・status・decision・halt）・ログ・observe（0・1・None）・adapter.submit の結果（outcome・status・診断の識別・view_for）を比べる
- 継続: 保存しない元の状態から続けたものと、保存して復元した状態から同じ操作の列（完全な記録の残りの行を seq の順）で続けたものが、各境界で同じ
- 範囲を限った確認値（形式 35 の sha256）だけに頼らない（スナップショットは形式 35 が落とす乱数の状態・カードの定義の解決・決定の続きを持つので、スナップショットの JSON の一致も比べる）
- OS・Python の版をまたぐ保証は、U3 の範囲（実装と major・minor が同じ）を超えない
<!-- generated:verification end -->

実装の単位・依存・完了基準と、新しく判断が要る事項は [実装計画](state-snapshot-implementation-plan.md) にあります。

## 9. 検証と未確認

- `python scripts/build_state_snapshot_design.py --check`: JSON・生成区画が同じ元から作ったものか、分類表とコードの型・項目が名前で一致するか、原則に反する分類（乱数を保存しない・pending_moves を許す・登録から解決しない・決定を保存しない）・停止の扱い・復元の段と結果の語彙・単位の依存・3 つの集合の計画を確かめる。`tests/test_state_snapshot_design.py` は、壊した仕様と、項目を加えた・消したコードの代わりの値で、これらの確かめが問題を見つけることを確かめる
- この作業で実行した確かめ（限定。全体テスト・全 108 組・4,356 局・lockstep・ストレス実行はしていない。終了コードは確かめの本体から）:
  - `build_state_snapshot_design.py --check`: problems=0。`tests.test_state_snapshot_design`: OK
  - U5 の情報境界: `tests.test_view_record_v0_155`（`PastLogBoundaryTest` を含む）: OK
  - 診断の仕様案（ADOPT-U6-PRINCIPLES を加えた）: `build_diagnostics_replay_api_design.py --check` problems=0、`tests.test_diagnostics_replay_api_design` と v0.152〜v0.155 の文書のテスト: OK。
    期待を変えたテスト（目的は同じ）: v0.153・v0.154・v0.155 のテストが D-SNAPSHOT-BASE・D-HALT-SNAPSHOT を pending と固定していたのを、後の ADOPT-U6-PRINCIPLES だけが決めたことを確かめる形に、
    仕様のテストの `test_approval_cannot_be_recorded` は保留の判断事項がなくなったので、記録のない判断事項をテストで加える形にした
  - 生成物の `--check`（診断のコード表・停止の方針の台帳・共通規約の設計案・同梱の規約集合の記録・実装上の仮定・正規化の再確認）: すべて終了コード 0
  - 変えた文書を読む既存のテストのメソッド 17 件: OK。ruff 0.17.2: 新しい・変えたスクリプトとテストに指摘なし、新しい抑制なし
  - `check_implementation_assumptions.py --sites`（基点の木と比べた差）: 0 件
- 未確認: 状態の入れ子の最大の深さ（DS-DEPTH）、ログ・決定の context に、タプルでない配列・浮動小数などが入る場面がないこと（v0.156 で調べたのはピカチュウの対戦とドライアップだけ。U6-S1 で既存のテストの盤面に広げる）、マチスの秘策を含む合法な対戦の閲覧用記録の変換

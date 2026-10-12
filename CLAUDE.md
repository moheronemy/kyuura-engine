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
- ワザを使えるのは、効果の登録表（kyuura_engine/effects.py の `DEFAULT_EFFECTS`）に（カード id, ワザの位置）で実装が登録されているときだけです（v0.2a）。説明文が空なことを実装がある証拠にしないでください。登録するカードは、先に『オフィシャルブック2000』のページと照合し、`kyuura_engine/data/card_verification.json` に記録します（tests/test_effects.py が確かめる）。
- トレーナーも同じです（v0.2b）。カード id で `TrainerEntry` を登録し、kyuura の写しの名前・文面（照合用）と、実装がしたがう『オフィシャルブック2000』の「最新の説明」（`play_text_ja`）・出典を書きます。照合の記録には `latest_description_ja` を書きます（tests/test_trainers.py が確かめる）。英語版の文面や現代のカードの文面で日本語版の処理を決めないでください。
- 説明文のあるワザ（v0.2d から）は、`AttackEntry` に kyuura の写しの説明文（`text_ja`。照合用）と、実装がしたがう「最新の説明」（`play_text_ja`）・出典（`source`）を書き、照合の記録に `latest_description_ja` を書きます（tests/test_effects.py `test_attacks_with_text_follow_the_verified_latest_description` が確かめる）。登録した説明文とデータの説明文が違えば、そのワザは使えません。
- カード効果の中で原典で決められない場合は、成功を仮定せず `UnsupportedError`（コードは `UNRESOLVED_…`）で止めます。使えるかどうかなら `TrainerEffect.check_playable`、決定の選択なら `push_trainer_decision` の `unresolved_choices` を使います。テストは「止まること・状態が変わらないこと」を確かめ、仮定に基づく成功のテストは書きません。決めた根拠と未解決の事項は docs/trainers-v0.2b.md のように、原典の記述・分類（CONFIRMED・SUPPORTED・UNRESOLVED・CONFLICT）・コード・テストを対応づけて書きます。

## 状態の作り（v0.2a）

- プレイヤーの選択を待つ処理は、`kyuura_engine/decisions.py` の `push_decision` で保留中の決定（`GameState.decision`）を作り、engine.py の再開先（`_RESUMERS`）で続けます。段階や保留中のリストを別に増やさないでください。決定は一度に 1 つです。
- 場のポケモンは `pokemon_id`（場に出たときに付ける番号。進化しても同じ、場を離れたら無効、使い回さない）で指します。カードの uid はカードの番号で、場のポケモンの番号ではありません。v0.1 のコマンド（`PromoteActive` など）はカードの uid のまま受け付けます。
- 状態の書き出しは `state_to_dict(state)` が v0.1 の形（`format_version` 1）、`state_to_dict(state, format_version=2)` が v0.2a の項目を加えた形です。既定の形を変えると固定値と互換性のテストが変わります。
- tests/fixtures/v0_1_reference.json は v0.1 の結果の参照データです。互換性を確かめるためのものなので、scripts/make_compat_fixture.py で作り直さないでください（作り直すと v0.1 との比較ではなくなります）。v0.1 で未対応だった操作を対応にしたら、参照データは変えずに tests/test_compat_v0_1.py の `NOW_SUPPORTED` に加え、エラーコードが変わる件数と内訳を docs に書きます（v0.2b の `play_trainer`）。
- トレーナーを使っている最中（決定を待つ間）のカードは `GameState.trainer_in_use` にあります（カードの保存則の対象）。この状態は形式 1・2 では書き出せないので、トレーナーのある対戦のテストは形式 3 以上で比べます。
- ポケモンについて場に残るトレーナー（v0.2c。プラスパワーなど）は `PokemonInPlay.trainers`（`AttachedTrainer`）にあります。使用中（`trainer_in_use`）とは別の領域です。実装は `TrainerEffect.stays_in_play = True` にし、有効期限の長さを `discard_turn_offset`（使った番からいくつ後の番の終わりにトラッシュするか。プラスパワー 0、ディフェンダー 1 = 次の相手の番。v0.2e）で宣言して、`zones.attach_trainer(..., discard_at_end_of_turn=effect.attachment_discard_turn(state))` でつけます。有効期限（`discard_at_end_of_turn`）の番の終わりにエンジンがトラッシュし、きぜつしたらポケモンといっしょにトラッシュします。勝敗が決まった番は番の終わりが来ないので、何もしません。形式 1〜3 は、ついているトレーナーを書き出せない（`ValueError`）ので、形式 4 で比べます。番は先攻から 1 つずつ交互に進むこと（番のプレイヤー = `engine.turn_owner(state, turn_number)`）を不変条件で確かめているので、「次の相手の番」は番の番号 + 1 で表します。番を飛ばす・続ける効果を加えるときは、この前提と有効期限の表し方を見直してください。
- ダメージを変えるカードの効果は、`damage.DamageModifier`（段階と加える数）で p.321 の段階に渡します。最終ダメージに直接足さないでください。加算でない効果を加えるときは、同じ段階の順番を決めるプレイヤー（`DAMAGE_STEP_CHOOSER`）に決定で選ばせます。
- コイン（v0.2d）は `kyuura_engine/coins.py` の `flip_coins` だけで投げます（1 枚 1 回 `GameState.rng.getrandbits(1)`、1 なら「おもて」。1 枚ごとにログ `coin_flip`）。コインの結果をコマンドや引数で指定する口を作らないでください。テストで結果を決めるときは、tests/helpers.py の `with_coin_results`（状態の乱数を差し替える）を使います。コインを投げる効果は、投げる前に使えるかどうか・原典で決められない場合を確かめ終えておきます。コインの使い方（回数・順番）を変えると、tests/test_coins.py・tests/test_coin_games.py の固定値が変わります。
- ワザのダメージ（v0.2f）は `effects.deal_attack_damage(state, use, target, base)` で与えます。発生源はいつもワザを使うポケモンで、受けるポケモンは `target`（`OPPONENT_ACTIVE`・`SELF`。p.320 のダメージの (1)・(3)）で決めます。ポケモンの `damage` に最終ダメージを直接足さないでください。控えポケモンへのダメージ（(2)・(4)）を加えるときは、種類を足す前に、受けるポケモンの選び方と計算（弱点・抵抗力・プラスパワーなどの扱い。p.257）を原典で確かめます。自分へのダメージの弱点・抵抗力は、ワザを使うポケモンのタイプと自分の弱点・抵抗力で計算します（v0.3d。p.90 の解説。SUPPORTED。v0.2f〜v0.3c の `self_damage_problem` は外した）。こんらんの 20（`calculate_confusion_damage`）とは別の計算のままにしてください（docs/unresolved-rulings-v0.3d.md 6 章）。
- きぜつは、ワザの要素をすべて処理したあとで `engine._finish_attack` がまとめて判定します（p.309・p.324）。ワザの効果の中でポケモンをトラッシュしないでください。サイドはきぜつしたポケモンの相手側のプレイヤーが取り（p.323）、勝ち負けはすべてのサイドを取ってから p.311 の表で判定します。同時のきぜつで両方がサイドを取る順番は、番のプレイヤーが選ぶ（p.325）ところを、結果が変わらないので番のプレイヤーからに正規化しています。サイドに関わるカードを加えるときはこの前提を見直してください（docs/simultaneous-ko-v0.2f.md 5 章）。バトル場に出す順番（番でないプレイヤーが先。pp.323〜324）はルールで決まった順番で、選択ではありません。
- 特殊状態（v0.3a〜v0.3c）は場のポケモンの `PokemonInPlay.conditions`（`SpecialConditions`。frozen なので `dataclasses.replace` で置きかえる）に持ちます。カードの uid や `GameState` の別の一覧で持たないでください。付けるのは `conditions.poison`・`put_to_sleep`・`paralyze`・`confuse`（v0.3c）、消すのは `conditions.clear_special_conditions`（にげる・ポケモンいれかえでベンチに戻ったとき。p.311・p.322）・`recover_from_sleep`・`recover_from_paralysis`（ポケモンチェック）。特殊状態になるのはバトル場のポケモンだけで、ベンチのポケモンに特殊状態があれば不変条件の違反です。どくはほかの特殊状態と重複し（`SpecialConditions.poison`）、ねむり・マヒ・こんらんはたがいに重複しない（p.322）ので 1 つの項目（`SpecialConditions.exclusive`。`Asleep`・`Paralyzed`・`Confused`）に持ちます。「特殊状態は 1 つだけ」という形にしないでください。ねむり・マヒ・こんらんが置きかわる・回復するときに、どくを消さないでください。形式 1〜4 は特殊状態を書き出せない（`ValueError`）ので、形式 5 以上で比べます。
- ポケモンチェック（v0.3a）は、番の終わり（`_end_turn`）のあとに `engine._pokemon_check` が 1 回だけ行い、最後（v0.3b からは 3・4 の `_pokemon_check_sleep_and_paralysis` の最後）に次の番を始めます（`_begin_turn` をほかの場所から呼ばない）。段階（`Phase`）は増やしていません。ポケモンチェックの中のきぜつは、ワザのあとと同じ `_after_knockouts` で処理し、決定の `context` の `"then"`（`engine.NEXT_TURN`）で「交代のあとはポケモンチェックの残り（3・4）をして次の番を始める」ことを表します（ワザのあとの決定には書かない）。どくのダメージはワザによるダメージではない（p.321）ので、`deal_attack_damage` を通さず、ログも `poison_damage` です。両方のプレイヤーのポケモンがポケモンチェックのどくできぜつする場合は原典で決められないので、ダメージを与える前に `Phase.HALTED`（`UNRESOLVED_POKEMON_CHECK_DOUBLE_KNOCKOUT`）で止めます。番の進行（番と番のあいだに `turn_end` → `pokemon_check` が 1 回ずつ）は不変条件（`_progress_problems`）で確かめています。
- ポケモンチェックの 3（ねむり）・4（マヒ）（v0.3b）は `engine._pokemon_check_sleep_and_paralysis` が行い、最後に `_begin_turn` を呼びます。呼ぶのは、2 できぜつがないときと、2 のきぜつの決定（`then` が `engine.NEXT_TURN`）が終わったときの 2 か所だけです。2 のきぜつ・サイド・判定・交代は 3 より先です（HP 以上のダメージできぜつしてトラッシュ・すぐに出す。p.311・p.313・p.323。きぜつしたポケモンのねむりのコインは投げない）。`then` の値は v0.3a と同じ `"next_turn"`（書き出しの形を変えないため）で、交代のあとは 3・4 → 次の番です。3・4 で決定を出す効果（ポケモンチェックの 1 など）を加えるときは、続きの持ち方を見直してください（docs/pokemon-check-v0.3b.md 3 章・docs/architecture-v0.3b.md 6 章）。
- ねむりのコインは持ち主が `flip_coins(state, owner, 1, source="pokemon_check", effect="sleep", …)` で投げ、結果を `sleep_check` に残します。両方の対戦ポケモンがねむりなら、投げる順番が原典で決まらず乱数の割り当てが変わるので、コインの前に `Phase.HALTED`（`UNRESOLVED_POKEMON_CHECK_SLEEP_COIN_ORDER`）で止めます。番のプレイヤーから投げるような正規化をしないでください。
- マヒ（v0.3b）は、マヒ状態になった番（`Paralyzed.turn`）を持ち、回復する番は `conditions.paralysis_recovery_turn`（`turn` より後の、持ち主の最初の番。`state.turn_owner`）で求めます。`turn + 1` で決めないでください（持ち主の番にマヒ状態になったら 2 つ後）。期限の過ぎたマヒが残らないことは不変条件で確かめています。マヒの再付与で回復する番が変わる場合は原典で決められないので、コインの前に `conditions.paralysis_problem` で確かめ、`UnsupportedError`（`UNRESOLVED_REPARALYSIS_RECOVERY_TURN`）にします。
- ねむり・マヒのポケモンのワザ・にげるは、処理の前に `IllegalActionError`（`POKEMON_ASLEEP`・`POKEMON_PARALYZED`）で拒否します（p.309 の手順 1 はエネルギーの確認より前。p.311）。ポケモンいれかえは制限しません（p.325）。ワザ・にげるを制限する状態を加えるときは `engine._require_not_asleep_or_paralyzed` と同じ場所で確かめます。
- こんらん（v0.3c）は、ワザ・にげるの宣言を拒否しません（p.309・p.311 の宣言できない状態はねむり・マヒだけ）。宣言が正しく成り立ったあとで、持ち主が `engine._confusion_check`（`flip_coins` の `source="confusion"`、ログ `confusion_check`）でコインを投げます。ワザ（p.309 の手順 5）は「うら」なら効果の `resolve` を呼ばずに `engine._confusion_damage`（`damage.calculate_confusion_damage`。20、弱点・抵抗力だけ。ログ `confusion_damage`）→ `_finish_attack`。にげる（p.311 の手順 3）はエネルギーをトラッシュしてから投げ、「うら」なら入れ替えずに `retreat_failed`（番は続く）。どちらも不正なコマンド（`IllegalActionError`）にしないでください（コイン・エネルギー・20 ダメージ・番の終わりは状態に残る）。こんらんの 20 を `deal_attack_damage`（ワザによるダメージ）に通したり、v0.2f の自分へのダメージの規定と混ぜたりしないでください（docs/confusion-attacks-v0.3c.md 5 章）。
- ワザの効果の実装で、ワザを使う前に分かる「原典で決められない場合」は `AttackEffect.problem` で返します（v0.3c。エンジンがこんらんのコインの前に聞く。v0.3d の対応カードの実装はどれも既定の None）。受け付けるか・拒否のコードがコインの結果で変わらないことを tests/test_effect_preflight_v0_3d.py の `CoinIndependenceTest` で確かめているので、ワザの実装を加えたら `ATTACKS` にも加えます（docs/effect-preflight-v0.3d.md）。こんらんの 20 にプラスパワー・ディフェンダーを計算するかは決められないので、ワザを使うこんらん状態のポケモンにダメージを変えるカードがついていれば、コインの前に `UNRESOLVED_CONFUSION_DAMAGE_MODIFIERS` で止めます（`engine._confusion_damage_problem`）。
- こんらんで「にげる」に失敗した記録（v0.3c）は、場のポケモンの `PokemonInPlay.retreat_failed_turn`（失敗した番の番号）に持ち、`_end_turn` で消します。プレイヤー単位の「この番はもうにげられない」フラグや、`GameState` の別の一覧にしないでください（p.311 の制限はポケモンごと）。こんらんのまま再宣言したら `RETREAT_ALREADY_FAILED`、失敗のあとこんらんが消えて同じ番にバトル場に戻ったポケモンの宣言は原典で決められないので `UNRESOLVED_RETREAT_AFTER_CONFUSION_CLEARED`（どちらもエネルギー・コインの前）。形式 1〜5 はこの記録を書き出せない（`ValueError`）ので、形式 6 で比べます。記録は、今の番のログの `retreat_failed`（同じ `pokemon_id`）と対応することを不変条件で確かめています（v0.3d）。テストで記録を置くときは、`build_test_state` の `"retreat_failed_turn"` か、対応するログといっしょに置いてください。進化・特殊状態を回復するトレーナーを加えるときは、この記録の扱いを見直してください（進化では消す。docs/evolution-readiness-v0.4.md 3 章 Q2）。
- ダメージの目安の数字がないワザ（パラスの「キノコのほうし」）は、ダメージの要素がないワザとして実装します（`PutToSleep`。ダメージの計算も `damage` のログもない）。`DamageOnly` に 0 を渡す登録にしないでください（docs/sleep-paralysis-v0.3b.md 4 章）。
- ログのイベントに `turn` の項目を渡さないでください（`add_event` が `ValueError`。ログの `turn` はいつも今の番。マヒの番は `paralyzed_turn`）。
- ログは内部の完全な記録です（引いたカードなどの隠れた情報を含む）。イベントを加えるときは、隠す情報を決まった項目にだけ入れます（docs/architecture-v0.2b.md 9 章）。
- 進化（v0.4 の予定）は v0.3d では実装していません。進化カードを登録・実装するときは、先に docs/evolution-readiness-v0.4.md の論点（`pokemon_id` を変えない案、「いまの姿で場に出た番」、失敗の記録を消す、形式 7、ついているトレーナーの効果）を原典と照合し、決められないものは止めます。
- 原典で決められないとして止めている裁定（`UNRESOLVED_…`）の分類を変えるときは、根拠の誌面と読み方の比較を docs/unresolved-rulings-v0.3d.md のように書きます。SUPPORTED を根拠なく CONFIRMED にしないでください。

## 変更するとき

- 規定を加えたり直したりしたら、対応する自動テストを加えます。テストの docstring かコメントに、根拠の誌面のページと kyuura の記録 id を書きます。
- 対戦のテストは、正式な開始（`new_game`、60 枚のデッキ、サイド 6 枚）を使います。盤面を直接作る `tests/helpers.py` の `build_test_state` は、1 か所の規定を確かめるテストだけに使い、対戦準備やデッキのテストには使いません。
- 乱数は `GameState.rng`（seed から作る）だけを使います。
- `apply_command` は渡された状態を変えません（clone してから処理する）。この性質を壊さないでください。
- `new_game`・`apply_command` は、返す状態を `check_invariants` で確かめます（破れていれば `StateIntegrityError`）。ゾーン・段階・保留中の決定を加えたら、その不変条件も `check_invariants` に加えます。段階やコマンドの種類を加えたら、tests/test_state_integrity.py の `ALLOWED`・`sample_commands` も更新します。
- 乱数・カードの番号の付け方・状態の形を変えると、tests/test_reproducibility.py の固定値が変わります。意図した変更のときだけ値を更新し、理由をコミットに書きます。
- docs（README.md、docs/implementation-status.md など）を実態に合わせます。対応していないものを対応済みと書かないでください。
- テスト: `python3 -m unittest`（リポジトリの直下。標準ライブラリだけ）。

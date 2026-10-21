# v0.80: v0.79 の共通処理の修正（A・B）と、トレーナー 30 枚

作業ブランチ `claude/v0.80-neo-trainer-components`（v0.79 の `a84f836` から作った）。写しの元・研究の基準は kyuura `7d3f4ca76c084774efb4ac6a1d3a943387e183c3` のまま、
ルールの基準は 2000.02.14 版のまま。カードデータは kyuura の `data/cards.json`（日本語の欄）を採用した。公式ガイドブックの新しいキャプチャ・OCR・読み直しはしていない。30 枚の
pcg-search.com のページ・カードの画像も照合していない（外部照合なし。kyuura の日本語の文面は nazonobasho.com・ポケモンWiki・pcg-search.com の転記で、同じ転記元を開き直す
ことは独立した照合にならない）。英語版の文面・現代のルール・2000.02.14 版のあとの規定（2002 年のサポーターの規定・ポケモンのどうぐの区分など）で日本語の不足を補っていない。
CC-・LD- の記録がないこと・サイトに接続できないことだけを理由に保留したカードはない。

## 1. 対象と数

| | v0.79 | v0.80 |
|---|---|---|
| 写し・対応するカード | 943・943 | 973・973 |
| 対応ポケモン・トレーナー・エネルギー | 695・213・35 | 695・243・35 |
| ワザ・特殊能力・トレーナー・特殊エネルギーの登録 | 1,182・74・213・17 | 1,182・74・243・17 |
| スタジアム（トレーナーの登録のうち） | 33 | 37 |
| 未対応（全対象・neo・拡張パック以外） | 434・227・207 | 404・202・202 |
| 停止コード・未解決の裁定 | 166・168 | 175・177 |

- 写しの組 `pool_v0_80`（30 枚。依頼の順）を加え、写しの作り直しの道具で作った（手で直していない）。v0.79 までの 943 枚の写しの値・組は変わらない（`--check` が通る）。
  未対応の数は kyuura data/engine_targets.json（7d3f4ca）の対象 1,377 件から今の登録を差し引いて数えた（`engine_status` は v0.68 の時点の索引なので使わない）。
- 30 枚の登録だけを除くと、30 枚とも未対応にもどる（tests の `test_unregistered_without_the_v0_80_entries`）。`engine.py`・`resolution/` にカード id の分岐はない。
- 書き出しの形式（22）・公開の API の呼び方・コマンドは変えていない。

## 2. A: ポケモンチェックの 1 と 2 のあいだの交代（PK1 の確かめの修正）

v0.79 の PK1（`UNRESOLVED_POKEMON_CHECK_MID_KNOCKOUT`）は、1（悪エネルギー）で HP 以上になったポケモンが場をはなれる読み方を、バトル場を空けたまま比べていた。2 の前にバトル場に
出しうるポケモン（控え）によって、［へんしん］のメタモンの姿・最大HP（v0.48・v0.49 の問い合わせ）が変わり、2 の「どく」のあとのきぜつの判定が変わる場面を見落としていた。

再現例（依頼の盤面）: プレイヤー 0 のワンリキー（ダメージ 40・悪エネルギー）の控えがポニータだけ、プレイヤー 1 のメタモンはワンリキーの姿でダメージ 30・どく。v0.79 は
サイドを取る決定に進み、ポニータを出す答えが MH1 で拒否されて答えのない決定が残った。

- `procedures.mid_check_knockout_divergence` を書き直した。場をはなれる読み方は、バトル場が空いたそれぞれのプレイヤーの控えの出し方のすべての組（`_mid_check_leave_readings`。控えが
  いない側はバトル場が空いたまま）を作り、どれか 1 つでも場に残る読み方の問い合わせ（`_mid_check_view`）と違えば、ダメージを与える前に PK1 で止める。
- 場をはなれる読み方で 2 の前に対戦が終わりうる（場のポケモンがいなくなる・取るサイドが残りのサイド以上になる。`_mid_check_game_ends`）のに、場に残る読み方では 2 のあとに
  ほかのきぜつがある場合も止める（勝ち負けが変わりうる）。
- 対照: 出すポケモンが同じ最大HP（ワンリキー）・どくがない・メタモンがいない盤面は、v0.79 と同じに進む（`test_controls_proceed`）。
- PK1 の裁定は決めていない（1 と 2 のあいだのきぜつの判定の時点を決めない）。

## 3. B: ワザが失敗しても処理する要素と、失敗のコイン

v0.79 のメタルクラッシュ（ハガネール PRN-014。`FailOnTailsDamageThenSelfCannotAttack`）は、コインの「うら」でワザが失敗しても次の自分の番にワザを使えない効果（要素の
`after_failure`）を、失敗のコインが決める要素に数えていた。そのため「ダメージを受けない」相手（かたまるのコクーン）にも「有効な要素がある」としてコインを投げていた。

- `programs.FailOnTails.run` は、`void_coin_question` に `after_failure` でない要素だけを渡す（失敗しても処理する要素は、コインの結果で変わらない）。
- メタルクラッシュを「ダメージを受けない」相手に使うと、どの先読みの方法（`derived`・`derived_full`・`legacy`）・どちらのコインの面でも、宣言の前に既存の
  `UNRESOLVED_PREVENTED_COIN_DAMAGE` で止まる（デルビル neo4-081 のおいつめるとの比べ: 同じ問い）。ふつうの相手には今までどおりコインを投げ、どちらの面でも効果を与える。

## 4. エフェクトガード（ES2-033）と、コインの前の確かめ

エフェクトガードは「相手のワザによる「ダメージ以外の効果」を受けない」（ダメージはそのまま受ける）。解決の基盤の効果の定義 `catalog.EFFECT_GUARD`（出どころ `TRAINER_EFFECT`・
窓は `BEFORE_EFFECT` だけ・`by_opponent`）で、効果の要素だけを無効にする。場のポケモンについているカード（`effects.effect_guards`）から問い合わせ、状態に印を持たない。

- 相手のワザだけ（`by_opponent`。持ち主の番のワザの効果・自分のワザの自分への効果は止めない）。トレーナー・特殊能力・ワザでないダメージは止めない。
- 履歴の受けなかった理由は `VOID_EFFECT_ONLY`（`effect_only`）。ログは既存の `effect_prevented`（`persistent_effect` は `effect_guard`）。
- コインの前の確かめ（`programs.void_coin_question`）は、コインが決める要素の役割ごとに、効果の要素（`BEFORE_EFFECT`）とダメージの要素を別々に確かめる。

| 相手の対戦ポケモン | コイン | 結果（ねばりつく: 「おもて」なら + 20 とマヒ） |
|---|---|---|
| エフェクトガードだけ | 投げる | ダメージは受け、マヒは受けない |
| 「ダメージを受けない」だけ | 投げる | ダメージは受けず、マヒは受ける |
| 両方 | 投げない | 既存の HC3（`UNRESOLVED_PREVENTED_EFFECT_COIN`）で宣言の前に止める |
| どちらもない | 投げる | ふつう |

- コインがマヒだけを決めるワザ（でんじは）は、エフェクトガードだけで既存の HC3 になる（新しい問いにしない）。
- 有効期限は次の相手の番の終わり（`discard_turn_offset = 1`）。ポケモンのどうぐ（ネオ以降の区分）としては扱っていない。

## 5. 共通の処理

- **手札から出して使うことの禁止**（ウツギはかせ・タイムカプセル・ポケモンギア）: v0.47 の `TrainerUseLock` を出どころ `HAND_TRAINER_LOCK`（`"hand"`）で使う（`add_hand_trainer_lock`）。
  消える番は「次の相手の番の終わり」（`hand_lock_expiry`。使ったプレイヤーの番に使えば与えた番 + 1）。ロケット団の実験（`origin="trainer"`。+ 2）は変えていない。止めるのは手札から
  出して使うことだけ（`trainer_use_blockers(..., from_hand=True)`）で、スタジアムを使うこと・ついているカードの効果は止めない（STB1 の確かめは `from_hand=False`）。使ったプレイヤー・
  番のプレイヤー・カードの持ち主は別に扱う。錯乱ジムで、この禁止を受けているプレイヤーがかわりに使うかは TL1（使うを選ぶと止める）。
- **その番の進化の禁止**（退化スプレーHYPER）: 期限のある効果 `TrainerTurnEffect` の種類 `EVOLUTION_BAN` と `pokemon_id`（書き出しは値のあるときだけ）。どの進化の入口でも
  `evolution_forbidden` が `EVOLUTION_PREVENTED` で拒否する（カードの説明が書いた禁止。ほかの効果で退化したポケモンの DV2 は解決していない）。
- **相手のサイドを扱う**: `zones.reveal_prize`（カードめくりゲーム。おもてのサイドの記録）・`look_at_prizes`・`prizes_to_deck`（にせオーキドの発明。サイドを取ることではない。おもての
  記録を除く）・`deck_top_to_prizes`。
- **スタジアム**: いやしの野原 `CoinHealOwnActiveStadium`（ログ `stadium_heal`）・ラジオとう `LookDeckTopStadium`（決定 `select_look_count`。順番を変えない）。エネルギースタジアム・
  ラッキースタジアム（neo4）は v0.74 の型で、印刷の文面の改行の位置の違いだけを受け付ける（`ENERGY_STADIUM_NEO_TEXT`・`LUCKY_STADIUM_NEO_TEXT`）。置き方の文が段落でなく同じ行に
  続く書き方（`STADIUM_INLINE_PLACEMENTS`）を受け付ける。
- **kyuura の種類 `goldenrod_game_corner`**（スロットゲーム・カードめくりゲーム）は、この種類だけのときに受け付ける（`game_corner_ok`。この種類を区別する規定の記録がなく、参照する
  カードもない）。
- 新しい決定の種類は `select_opponent_prize`・`take_looked_trainer`（観測の選べるものの数を相手に見せない `HIDDEN_COUNT_KINDS`・山札の中身 `DECK_REVEALING_KINDS`）。新しいログの
  イベントは `prize_revealed`・`prize_guess`・`deck_top_to_prizes`・`reveal_deck_top`・`quiz_kind_answer`・`quiz_kind_reveal`・`trainer_bench_from_deck`・`stadium_heal`（公開）と
  `look_at_prizes`・`prizes_to_deck`・`trainer_bench_from_deck_declined`（非公開の項目あり）。

## 6. 30 枚

処理に使う文面はどれも kyuura の印刷の文面（`source` は `kyuura data/cards.json`）。採用の記録は `kyuura_engine/data/card_sources.json`（30 件。`kyuura_records` は空・外部照合なし）。

| id | 名前 | 型・処理 |
|---|---|---|
| neo1-074 | すごいつりざお | `CoinTakeEvolutionOrBasicFromDiscard`: 「おもて」なら進化カード、「うら」ならたねポケモンを 1 枚トラッシュから手札に。どちらもなければ SRD1（コインの前） |
| neo1-087 | エネルギーチャージ | `CoinReturnEnergyFromDiscardToDeck`: 「おもて」ならトラッシュのエネルギーカード（基本・特殊）を最大 2 枚山札にもどして切る。0 枚の答えは UPZ1、対象なしは UPZ2 |
| neo1-092 | 超エネルギー回収 | `SuperEnergyRetrievalPrinted`: この版の印刷の文面。PR1-009 のエラッタ ERR-SUPER-ENERGY-RETRIEVAL の範囲としては扱わない（記録の cards は 1stp009 だけ）。処理は v0.73 と同じ（SR1・SR2） |
| neo2-053 | エネルギーアーク | `CoinsSearchBasicEnergyPerHeads`: コイン 3 枚の「おもて」の数ちょうどの基本エネルギーカードを見せて手札に。足りなければ FC1（コインの前） |
| neo4-102 | エネルギー増幅装置 | `ReturnHandEnergyThenCoinSearchBasicEnergy`: 手札のエネルギーカード 1 枚を見せて山札にもどし、「おもて」なら基本エネルギーカード 3 枚まで。FC1・UPZ1・UPZ2 |
| neo1-078 | ウツギはかせ | `ReturnHandDrawThenHandLock`: 手札をすべて山札にもどして切り、7 枚引く。手札から出して使うことの禁止 |
| neo1-089 | クルミ | `DrawThenReturnHandCardsToDeck`: 2 枚引き、手札からちょうど 2 枚を見せずに山札にもどして切る。FC1 |
| neo1-091 | タイムカプセル | `EachPlayerReturnDiscardToDeckThenHandLock`: おたがいがのぞむならトラッシュのたねポケモン・進化カード・基本エネルギーカードを最大 5 枚山札に。禁止 |
| neo4-100 | マサキのメール | `DrawUntilHandSize`: 手札が 4 枚になるまで引く。このカードを含む手札が 5 枚以上なら手札から出す前に `TOO_MANY_CARDS_IN_HAND` |
| neo1-082 | 新ポケモン図鑑HANDY808 | `ShuffleThenArrangeDeckTop`: 切ってから上の 5 枚を見て並べかえる。山札が 5 枚より少なければ TOP1 |
| neo1-090 | スロットゲーム | `RevealDeckTopTakeSameNamed`: 切ってから上の 3 枚を見せ、2 枚以上の同じ名前のカードを手札に。TOP1 |
| neo1-093 | ポケモンギア | `LookTopTakeTrainerThenShuffleLock`: 上の 7 枚からトレーナーカード 1 枚を見せて手札に・切る・禁止。TOP1 |
| neo1-075 | ポケモンぎゃくしめい | `OpponentChoosesMySwitchThenISwitchTheirs`: 相手が使ったプレイヤーの控えを選んで入れ替え、そのあと使ったプレイヤーが相手の控えを選ぶ。控えがいない側は入れ替えない。SG1 |
| neo1-076 | ポケモンマーチ | `EachPlayerMayBenchBasicFromDeck`: おたがいがのぞむなら山札のたねポケモン 1 枚をベンチに・切る。ベンチに空きがないプレイヤーは何もしない。GG1 |
| neo2-056 | 退化スプレーHYPER | `DevolveOneToHandWithBan`: いちばん上の進化カードを手札にもどし、その番は進化させない。HY1・DV5 |
| GD5-017 | カツラのクイズ その2 | `SetAsideGuessKindQuiz("card_kind")`: 置いたカードの種類を相手が答え、正解なら相手、正解でないなら使ったプレイヤーが 2 枚引く。FC1 |
| neo1-080 | カードめくりゲーム | `GuessOpponentPrizeKind`: 相手のうらのサイドを選んで種類を答え、おもてにする（そのまま）。正解なら 2 枚引く。FC1 |
| neo4-105 | ポケモン性格判定 | `SetAsideGuessKindQuiz("personality")`: 手札の進化カードを置き、相手が「わるい」「やさしい」それ以外を答える（3 枚）。手札に進化カードがなければ `NO_EVOLUTION_CARD_IN_HAND` |
| neo4-107 | ロケット団の暗躍 | `LookOpponentHandReturnOneThenMayDraw`: 相手の手札を見て 1 枚を相手の山札にもどし、相手はのぞむなら 2 枚まで引く。相手の手札 0 枚は FC1 |
| neo4-111 | にせオーキドの発明 | `LookOpponentPrizesMayRedeal`: 相手のサイドをすべて見て、のぞむなら山札にもどして切り、上から同じ枚数を置く |
| PR1-013 | イマクニ？ | `ConditionOwnActiveTrainer("confusion")`: 自分の対戦ポケモンをこんらんにする |
| PR1-074 | トロピカルウインド | `CoinHealBothElseSleepBoth`: 「おもて」ならおたがいの対戦ポケモンから 2 個ずつとりのぞき、「うら」ならおたがいの対戦ポケモンをねむりにする |
| PRN-026 | おどれ！neo★イマクニ？ | `ConditionOwnActiveTrainer(None)`: どく・ねむり・マヒ・こんらんから 1 つを選び、自分の対戦ポケモンをその状態にする |
| neo1-077 | モーモーミルク | `ChooseOwnPokemonCoinsHeal`: 自分のポケモン 1 匹を選び、コイン 2 枚の「おもて」の数 × 2 個をとりのぞく。MK1 |
| neo4-099 | ばんのうごな | `CoinHealAndCureOwnActive`: 「おもて」なら自分の対戦ポケモンから 2 個とりのぞき特殊状態を回復。BP1 |
| neo3-054 | いやしの野原 | スタジアム `CoinHealOwnActiveStadium`: 自分の番ごとに 1 回、「おもて」なら自分の対戦ポケモンから 2 個。HF1 |
| neo4-101 | エネルギースタジアム | スタジアム（v0.74 の型。EN1） |
| neo4-106 | ラッキースタジアム | スタジアム（v0.74 の型） |
| neo4-112 | ラジオとう | スタジアム `LookDeckTopStadium`: 自分の番ごとに 1 回、山札の上から 2 枚まで見る |
| ES2-033 | エフェクトガード | `AttachedEffectGuard`（4 章） |

## 7. 決められない場面

新しい停止コード 9 件（どれも kyuura の未解決の一覧にない `not_in_kyuura`。推測で決めていない）:

| id | コード | 場面 |
|---|---|---|
| SRD1 | `UNRESOLVED_SUPER_ROD_WITHOUT_TARGET` | すごいつりざおで、トラッシュに進化カードもたねポケモンもない（コインの前） |
| UPZ1 | `UNRESOLVED_TRAINER_UP_TO_ZERO_CHOICE` | 「最大」「まで」の選択で、選べるのに 0 枚を答えた（決定は待ったまま） |
| UPZ2 | `UNRESOLVED_TRAINER_UP_TO_WITHOUT_TARGET` | 「最大」「まで」の選択で、選べるカードがない |
| TOP1 | `UNRESOLVED_DECK_TOP_SHORT` | 山札の上から決まった枚数を見る・見せるのに、山札が足りない |
| TL1 | `UNRESOLVED_HAND_TRAINER_LOCK_BORROW` | 手札から出して使うことの禁止を受けているプレイヤーが、錯乱ジムでかわりに使う |
| HY1 | `UNRESOLVED_DEVOLUTION_SPRAY_HYPER_WITHOUT_TARGET` | 退化スプレーHYPER で、自分の場に進化ポケモンがいない |
| MK1 | `UNRESOLVED_MOOMOO_MILK_UNDAMAGED_TARGET` | モーモーミルクで、ダメージカウンターののっていないポケモンを選ぶ |
| BP1 | `UNRESOLVED_ALL_PURPOSE_POWDER_WITHOUT_TARGET` | ばんのうごなで、自分の対戦ポケモンにダメージカウンターも特殊状態もない |
| HF1 | `UNRESOLVED_HEALING_FIELD_WITHOUT_DAMAGE` | いやしの野原で、自分の対戦ポケモンにダメージカウンターがない |

既存の問いを使う場面: FC1（エネルギーアーク・エネルギー増幅装置・クルミ・カツラのクイズ その2・カードめくりゲーム・ロケット団の暗躍）、SR1・SR2（neo の超エネルギー回収）、DV5（退化スプレーHYPER の
「ばける」のポケモン）、SG1（ポケモンぎゃくしめい）、GG1（ポケモンマーチ）、EN1（エネルギースタジアム）、CH1（説明が使ったプレイヤーの番を書くカードを錯乱ジムで借りる）、HC3（エフェクト
ガードとダメージを受けない状態が重なる）。ほかのカードの「対象がない」「0 枚」の問いの答えを流用していない。停止コード 175 件、未解決の裁定 177 件。

## 8. 実装上の読み方（ルールとして扱わない）

- おたがいのプレイヤーが選ぶ処理（タイムカプセル・ポケモンマーチ）は、使ったプレイヤー → 相手の順（v0.54 の HD1 と同じ実装上の順番）。
- 「てよい」「のぞむなら」は選ばなくてよい（0 枚）。「最大」「まで」で「てよい」のない選択の 0 枚は UPZ1。
- エネルギーアークの「おもて」が 0 なら、山札を見ず・切らない（「その後」は選び出したあと）。コインの「うら」で何もしない処理（エネルギーチャージ・エネルギー増幅装置の 2 回目）も山札を切らない（v0.53 の MB1 と同じ読み方）。
- にせオーキドの発明は、置きなおすかを使ったプレイヤーが決める（決定 `accept_request`）。

## 9. kyuura への報告事項（kyuura は変更していない）

- neo1-090（スロットゲーム）の `ja_text_source` の URL は `neo01-091-slotgame` で、カード番号（090）と違う。転記元のページの番号の誤りか、kyuura の記録の誤りかは確かめていない。
- neo4-101・neo4-106 の `data_gaps` に `jp_print.series` がある（処理には使わない欄）。
- 30 枚とも kyuura に LD-・CC-・CR-・UQ-・エラッタの記録はない。neo1-092 は同じカードの組 SC-PR1-009 にあるが、ERR-SUPER-ENERGY-RETRIEVAL の `cards` は 1stp009 だけ（範囲として
  当てはめていない）。

## 10. 検証

- 単体テスト: tests/test_neo_trainer_components_v0_80.py（A・B・エフェクトガードの表・手札から出して使うことの禁止・退化スプレーHYPER・登録と文面・カードごとの処理と止める場面・
  書き出しと複製）。無効な答えで状態・乱数・ログが変わらないこと、カードの保存則、clone・deepcopy・pickle を確かめる。
- 対戦: tools/existing_effect_games.py `--batch v0.80`（N80 対 S80・N80 対 P31・S80 対 W79、席を入れかえ、seed 0〜3）の 24 局。22 局が通常の勝敗（サイドをすべて取った 8・相手が
  バトル場に出せない 6・相手の山札が尽きた 8）、2 局が既知の `UNRESOLVED_POKEMON_CHECK_SLEEP_COIN_ORDER` で停止。監査の失敗 0。30 枚とも手から使った（スタジアム 4 枚は場で使った）。
  対戦で使う前に止まった場面（数は 1 局ごとの記録の合計）: SRD1 49・HY1 36・BP1 32・MK1 26・UPZ2 19・FC1 13・TOP1 4・HF1 73（スタジアムを使う前）・SR1 34・EN1 3・
  `NO_EVOLUTION_CARD_IN_HAND` 133・`TOO_MANY_CARDS_IN_HAND` 13・手札から出して使うことの禁止による `TRAINER_PREVENTED` 32。対戦で起こらず単体テストだけで確かめた境界:
  エフェクトガードで効果を受けなかった場面と表の 4 行、TL1、UPZ1（0 枚の答え）、A・B の盤面。
- ログの監査（tests/log_audit.py）に、ポケモンマーチ・ラジオとう・いやしの野原・手札から出して使うことの禁止・退化スプレーHYPER・カードめくりゲーム・にせオーキドの発明・
  タイムカプセル・クルミ・ウツギはかせ・エネルギー増幅装置・すごいつりざお・カツラのクイズ その2・ポケモン性格判定・ロケット団の暗躍・ポケモンギア・新ポケモン図鑑の組み立て直しを加えた。
- 前の版との比較: 固定した v0.79 の木（`a84f836`）と別のプロセスで `tools/engine_lockstep.py`（760 対戦・136,537 歩）を比べて食い違い 0・許した差 0。前の版の組（v0.31・v0.44・
  v0.47・v0.57・v0.58・v0.61・v0.63・v0.74・v0.78・v0.79 の 148 局）は、v0.80 の空の集計（`v080`）を除いて v0.79 の木と同じ。A・B の再現例を v0.79 と v0.80 の木で直接走らせた
  （v0.79: A はポニータを出す答えが MH1 で拒否され答えのない決定が残る・B は「ダメージを受けない」相手にコインを投げる。v0.80: A は PK1 で止まりダメージなし・対照は同じに進む・B はどの方法・面でも
  `UNRESOLVED_PREVENTED_COIN_DAMAGE`）。
- 検査: 写しの `--check`・`scripts/check_card_sources.py`・`scripts/check_research_links.py --kyuura ../kyuura`・`tools/run_mutants.py check` が通る。ruff の指摘は v0.79 と同じ（新しい指摘なし）。
  凍結した写しで全体のテスト 4,703 件が通った（飛ばしたもの 1）。

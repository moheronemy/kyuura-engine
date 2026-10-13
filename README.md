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
- v0.5: ポケモンパワー（2000.02.14 版の用語では「特殊能力」）の基盤（`UsePokemonPower`・パワーの登録表）を、フシギバナ（PMCG1-011）の「エナジートランス」と、進化元のフシギダネ（やどりぎのタネ）・フシギソウ（つるのむち・どくのこな（コインなし））とともに実装した。一般の規定（p.309〜p.311・p.322・p.323）とカードのページ（p.13・p.14・p.16）を画像で照合した。使っても番は終わらず、何度でも・ベンチからも使え、使うフシギバナがねむり・マヒ・こんらんなら使えない（どくなら使える）。つけかえは手札からつけること（1 番に 1 回）ではなく、乱数を使わない。前の版（v0.4e）との比較で、フシギバナのいない対戦の結果は同じ。[docs/pokemon-powers-v0.5.md](docs/pokemon-powers-v0.5.md)（規定）、[docs/venusaur-v0.5.md](docs/venusaur-v0.5.md)（フシギバナ）、[docs/bulbasaur-line-v0.5.md](docs/bulbasaur-line-v0.5.md)（フシギダネ・フシギソウ）、[docs/energy-transfer-v0.5.md](docs/energy-transfer-v0.5.md)（処理）、[docs/architecture-v0.5.md](docs/architecture-v0.5.md)（設計）、[docs/v0.5-verification.md](docs/v0.5-verification.md)（確かめた結果）
- v0.6: カメックス（PMCG1-032）のポケモンパワー「あまごい」（自分の番の中で何度でも、手札の「水」エネルギーカードを自分の場の「水」ポケモンにつける）とワザ「ハイドロポンプ」（40+）、進化元のゼニガメ（あわ・からにこもる）・カメール（からにこもる・かみつく）を実装した。カードのページ（p.87・p.88・p.90）と一般の規定（p.307〜p.311・p.320〜p.323）を画像で照合し、15 の論点を記録した。手札から場への移動を 1 か所の処理にし、通常の操作（p.310。1 番に 1 枚）の回数とあまごいでつけた枚数を別に数える。通常の操作でつけたあとのあまごいは使える（R12）。あまごいでつけたあとの通常の操作は原典で決められないので止める（R13。`UNRESOLVED_ATTACH_AFTER_POWER_ATTACH`）。そのため書き出しの形式 9 を加えた。前の版（v0.5）との比較で、カメックスのいない対戦の結果は同じ。[docs/rain-dance-v0.6.md](docs/rain-dance-v0.6.md)（原典の照合と裁定）、[docs/architecture-v0.6.md](docs/architecture-v0.6.md)（設計）、[docs/v0.6-verification.md](docs/v0.6-verification.md)（確かめた結果）
- v0.7: フーディン（PMCG1-049）のポケモンパワー「ダメージスワップ」（自分の番の中で何度でも、この力によってポケモンが「きぜつ」しないかぎり、自分の場のポケモンにのっているダメージカウンターを自分の場の別のポケモンにのせかえる）とワザ「あやしいひかり」、進化元のケーシィ（ねんりき）・ユンゲラー（じこさいせい・ちょうねんりき）を実装した。カードのページ（p.149・p.151・p.153）とほかのカードの解説（p.98・p.235・p.248）・一般の規定（p.307〜p.311・p.319〜p.323）を画像で照合し、25 の論点（S1〜S25）ときぜつの禁止（A4）を記録した。1 回の使用で1 個（実装上の仮定。何度でも使えるので、たどりつける状態は変わらない）、のせたらきぜつする移動は状態を変える前に拒否する（`WOULD_KNOCK_OUT`）、移したカウンターは「ダメージを受けた」ことにならない（p.320）。じこさいせいでトラッシュする「超」エネルギーは、ワザを使うプレイヤーが決定で選ぶ。新しい未解決の裁定・状態の項目・書き出しの形式はない（形式 9 のまま）。v0.6 の R13 は変えていない。前の版（v0.6）との比較で、フーディンの系統のいない対戦の結果は同じ。[docs/damage-swap-v0.7.md](docs/damage-swap-v0.7.md)（原典の照合と裁定）、[docs/alakazam-line-v0.7.md](docs/alakazam-line-v0.7.md)（ケーシィ・ユンゲラー・フーディン）、[docs/architecture-v0.7.md](docs/architecture-v0.7.md)（設計）、[docs/v0.7-verification.md](docs/v0.7-verification.md)（確かめた結果）
- v0.8: ベトベトン（PMCG3-007）のポケモンパワー「かがくへんかガス」（常にはたらいていて宣言しない。このカードが場にいるかぎり、「かがくへんかガス」以外のすべての特殊能力は使えず、その力も消える。このカードがねむり・マヒ・こんらんのとき、この力は消える）とワザ「ヘドロこうげき」、進化元のロケット団のベトベター（PMCG4-004。どくガス・ねばりつく）を実装した。カードのページ（p.45・p.47・p.48）と一般の規定（p.308・p.310・p.311・p.322〜p.324）・解説（p.265・p.277）を画像で照合し、33 の論点（G1〜G33）と「使えず」「力も消える」の区別（A4）を記録した。かがくへんかガスがはたらいているかは、状態に持たず、場・いちばん上のカード・特殊状態から問い合わせのたびに求める（進化・きぜつ・特殊状態の回復・ベンチに戻ること・保存と復元のあとも古くならない）。消された特殊能力（エナジートランス・あまごい・ダメージスワップ）は、自分・相手のどちらのベトベトンでも、宣言の前に `POWER_SUPPRESSED` で拒否する。ワザ・トレーナー・通常の操作は止めない。新しい未解決の裁定・状態の項目・書き出しの形式・ログのイベントはない（形式 9 のまま）。R13 は変えていない。前の版（v0.7）との比較で、ベトベトンのいない対戦の結果は同じ。[docs/chemical-gas-v0.8.md](docs/chemical-gas-v0.8.md)（原典の照合と裁定）、[docs/grimer-line-v0.8.md](docs/grimer-line-v0.8.md)（ベトベター・ベトベトン）、[docs/continuous-effects-v0.8.md](docs/continuous-effects-v0.8.md)（常にはたらく効果の求め方）、[docs/architecture-v0.8.md](docs/architecture-v0.8.md)（設計）、[docs/v0.8-verification.md](docs/v0.8-verification.md)（確かめた結果）
- v0.9: ゴースト（PMCG3-030。化石の秘密）のポケモンパワー「とうめい」（ワザによってダメージや効果を受けるとき、自動的にはたらく。コインを投げて「おもて」なら、そのダメージと効果を受けない。ねむり・マヒ・こんらんのとき、この力は消える）とワザ「あくむ」、進化元のゴース（PMCG3-029。したでなめる・エナジーへんかん）を実装した。カードのページ（p.158・p.160）と特殊能力解説（p.159）・一般の規定（p.309・p.320・p.321・p.323）を画像で照合し、42 の論点（T1〜T42）と A4（1 つのワザで何回投げるか・ワザの成立・ベトベトンとの関係）、ゴースとゴーストのワザの 13 の論点（H1〜H13）を記録した。宣言しない自動的にはたらく特殊能力を、ワザの要素の処理の境界（ダメージは最終ダメージが決まってからのせる前、効果は与える前）で評価する（汎用のイベントの仕組みは作っていない）。コインはゴースト側のプレイヤーが 1 つのワザにつき 1 匹 1 枚投げ、その結果をそのワザのダメージと効果のすべてに使う（SUPPORTED）。最終ダメージが 0 なら投げない。ワザは失敗にならず（エネルギーはついたまま・番は終わる）、ワザを使う側への要素は処理する。かがくへんかガス（v0.8）がはたらいていれば「とうめい」は消える（v0.8 の判定を使う）。原典で決められない 2 件は止める（「おもて」で受けないと決まったあとのワザのコイン（T19b。`UNRESOLVED_EVADED_EFFECT_COIN`。ワザの前）・エナジーへんかんで 0 枚を選ぶ（H4。`UNRESOLVED_RECOVER_ZERO_ENERGY`））。状態の項目・書き出しの形式（9 のまま）・コマンド・段階は加えていない。R13 は変えていない。前の版（v0.8）との比較で、ゴーストのいない対戦の結果は同じ。[docs/transparency-v0.9.md](docs/transparency-v0.9.md)（原典の照合と裁定）、[docs/haunter-line-v0.9.md](docs/haunter-line-v0.9.md)（ゴース・ゴースト）、[docs/automatic-powers-v0.9.md](docs/automatic-powers-v0.9.md)（自動的にはたらく特殊能力の仕組み）、[docs/architecture-v0.9.md](docs/architecture-v0.9.md)（設計）、[docs/v0.9-verification.md](docs/v0.9-verification.md)（確かめた結果）
- v0.10（今の版）: カイリキー（PMCG1-057。第1弾）のポケモンパワー「はんげき」（相手のワザによってダメージを受けたとき、それによってきぜつしても、ダメージを与えたポケモンに弱点・抵抗力に関係なく 10 ダメージ。ダメージを受けるとき、すでにねむり・マヒ・こんらんならはたらかない）とワザ「ちきゅうなげ」、進化元のゴーリキー（PMCG1-055。からてチョップ・じごくぐるま）を実装した（ワンリキーは v0.1 から）。カードのページ（p.189・p.190・p.192・p.193）と、同じ形の発動条件の解説（p.89 の「こうらがえし」・p.138［ショックボム］・p.203「クロスカウンター」・p.245［わるいねぞう］・p.20［どくのたいえき］）・一般の規定（p.309・p.319〜p.324）を画像で照合し、43 の論点（C1〜C43）と A4 の 6 つの論点、ゴーリキーの系統の 12 の論点（M1〜M12）を記録した。宣言しない自動的にはたらく特殊能力で、相手のワザのダメージの要素（`deal_attack_damage`）でダメージを受けるときの状態から判定し、そのワザのダメージの処理（自分へのダメージを含む）が終わったところ・ダメージ以外の効果の前に与える（p.89。汎用のイベントの仕組みは作っていない）。「はんげき」の 10 は特殊能力によるダメージで、弱点・抵抗力・プラスパワー・ディフェンダー・「とうめい」を計算せず、別の「はんげき」もはたらかせない（連鎖しない）。きぜつ・サイド・交代・勝ち負けは今までどおりワザのあと。かがくへんかガス（v0.8）がはたらいていれば消える。原典で決められない 1 件は止める（カイリキーがワザで、ワザを使ったポケモンが「はんげき」できぜつする場合が同時のきぜつか（C18。`UNRESOLVED_COUNTERATTACK_DOUBLE_KNOCKOUT`。ワザの宣言の前））。状態の項目・書き出しの形式（9 のまま）・コマンド・段階・決定の種類は加えていない。前の版（v0.9）との比較で、カイリキーのいない対戦の結果は同じ。[docs/counterattack-v0.10.md](docs/counterattack-v0.10.md)（原典の照合と裁定）、[docs/machamp-line-v0.10.md](docs/machamp-line-v0.10.md)（ワンリキー・ゴーリキー・カイリキー）、[docs/post-damage-powers-v0.10.md](docs/post-damage-powers-v0.10.md)（ダメージを受けたあとに自動的にはたらく特殊能力の仕組み）、[docs/architecture-v0.10.md](docs/architecture-v0.10.md)（設計）、[docs/v0.10-verification.md](docs/v0.10-verification.md)（確かめた結果）

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
# 前の版（v0.9 の 995504e。v0.9 では v0.8 の d057f57）と今の作業ツリーを、同じ入力で別々のプロセスで動かして比べる（約 5 分。ネットワーク不要）
python3 tools/compare_engine_versions.py --base 995504e --report report.json
# 大規模なストレス実行（でたらめな操作を混ぜ、結果を分類して数える。問題のある seed を報告する）
python3 tools/stress_engine.py --seeds 100 --steps 600 --report stress.json
# フシギバナの組だけ（エナジートランスの使用を混ぜる。v0.5）
python3 tools/stress_engine.py --scenario venusaur --scenario venusaur_status
# カメックスの組だけ（あまごいの使用を混ぜる。v0.6）
python3 tools/stress_engine.py --scenario blastoise --scenario blastoise_mixed
# フーディンの組だけ（ダメージスワップの使用を混ぜる。alakazam_mixed はフシギバナ・カメックス・フーディンを同じデッキに。v0.7）
python3 tools/stress_engine.py --scenario alakazam --scenario alakazam_mixed
# ベトベトンの組だけ（かがくへんかガスが特殊能力を消す場面。muk_mixed は両方のデッキにベトベトン。v0.8）
python3 tools/stress_engine.py --scenario muk --scenario muk_mixed
# ゴーストの組だけ（「とうめい」がはたらく場面。haunter_muk は両方のデッキにゴースト、一方にベトベトン。v0.9）
python3 tools/stress_engine.py --scenario haunter --scenario haunter_muk
# カイリキーの組だけ（「はんげき」がはたらく場面。machamp_mixed は両方のデッキにカイリキー、一方にベトベトン、もう一方にゴースト。v0.10）
python3 tools/stress_engine.py --scenario machamp --scenario machamp_mixed
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

### ポケモンパワー・あまごい（v0.6）

カメックス（PMCG1-032）の「あまごい」は、自分の番の中で何度でも、自分の手札の「水」エネルギーカード（`energy`。カードの uid）を、自分の場の「水」ポケモン（`target`。場のポケモンの番号。バトル場・ベンチ・カメックス自身）につけます（`source` は使わない）。1 回の使用で 1 枚です（実装上の仮定）。

```python
from kyuura_engine import (
    AttachEnergy, EndTurn, EvolvePokemon, PlaceStartingPokemon, ReportJankenResult, UnsupportedError, UseAttack,
    UsePokemonPower, apply_command, expand_decklist, new_game, state_to_dict,
)

deck0 = expand_decklist({"PMCG1-023": 4, "PMCG1-027": 4, "PMCG1-032": 4, "PMCG1-099": 48})
# ゼニガメ（PMCG1-023）・カメール（PMCG1-027）・カメックス（PMCG1-032）4 枚ずつ、水エネルギー 48 枚
deck1 = expand_decklist({"PMCG1-025": 4, "PMCG1-029": 4, "PMCG1-052": 4, "PMCG1-053": 4, "PMCG1-058": 4,
                         "PMCG1-099": 20, "PMCG1-102": 20})
state = new_game(deck0, deck1, seed=373)

def in_hand(player, card_id):
    return next(uid for uid in state.players[player].hand if state.cards[uid].card_id == card_id)

squirtles = [uid for uid in state.players[0].hand if state.cards[uid].card_id == "PMCG1-023"]
state = apply_command(state, PlaceStartingPokemon(0, squirtles[0], tuple(squirtles[1:2])))   # バトル場とベンチにゼニガメ
basics = [uid for uid in state.players[1].hand if state.card_def(uid).is_basic_pokemon]
state = apply_command(state, PlaceStartingPokemon(1, basics[0], tuple(basics[1:6])))
state = apply_command(state, ReportJankenResult(winner=0))
active, bench = state.players[0].active.pokemon_id, state.players[0].bench[0].pokemon_id
for player in (0, 1):   # 1 番・2 番: 水エネルギーをつけて番を終える
    state = apply_command(state, AttachEnergy(player, in_hand(player, "PMCG1-099"), state.players[player].active.card))
    state = apply_command(state, EndTurn(player))
# 3 番: バトル場のゼニガメをカメールに進化
state = apply_command(state, EvolvePokemon(0, in_hand(0, "PMCG1-027"), active))
state = apply_command(state, EndTurn(0))
state = apply_command(state, EndTurn(1))

# 5 番: カメールをカメックスに進化（2 進化）。その番にあまごいを使える
state = apply_command(state, EvolvePokemon(0, in_hand(0, "PMCG1-032"), active))
blastoise = state.players[0].active
print(state.card_def(blastoise.card).name_ja, [p.name_ja for p in state.card_def(blastoise.card).powers], len(blastoise.energy))
# カメックス ['あまごい'] 1
water = in_hand(0, "PMCG1-099")
before = len(state.log)
state = apply_command(state, UsePokemonPower(0, blastoise.pokemon_id, 0, energy=water, target=bench))   # 手札からベンチのゼニガメへ
print([e["kind"] for e in state.log[before:]], state.players[0].bench[0].energy == [water], water in state.players[0].hand)
# ['pokemon_power', 'power_attach_energy'] True False      同じ uid のカードが手札からベンチのゼニガメへ
print(state.energy_attachments_this_turn, state.energy_attached_by_powers_this_turn)
# 0 1      通常の操作の回数は変わらず、あまごいでつけた枚数を別に数える
try:   # あまごいでつけたあと（通常の操作をまだしていない番）の通常の操作は、原典で決められないので止める（R13）
    apply_command(state, AttachEnergy(0, in_hand(0, "PMCG1-099"), state.players[0].active.card))
except UnsupportedError as error:
    print(error.code)   # UNRESOLVED_ATTACH_AFTER_POWER_ATTACH（状態は変わらない）
for _ in range(3):   # バトル場のカメックス自身に 3 枚（何度でも使える）
    state = apply_command(state, UsePokemonPower(0, blastoise.pokemon_id, 0, energy=in_hand(0, "PMCG1-099"), target=active))
print(len(state.players[0].active.energy), state_to_dict(state, format_version=9)["energy_attached_by_powers_this_turn"])
# 4 4
try:
    state_to_dict(state, format_version=8)
except ValueError:
    print("形式 8 では書き出せない")   # あまごいでつけた枚数が 0 でない番は形式 9 だけ
before = len(state.log)
state = apply_command(state, UseAttack(0, 0))   # ハイドロポンプ: 水 4 個 = 必要な 3 個 + 多い 1 個 → 40 + 10
print([(e["kind"], e.get("amount")) for e in state.log[before:] if e["kind"] in ("attack", "damage")])
# [('attack', None), ('damage', 50)]
```

- 使えるのは番のプレイヤーの通常の段階（`Phase.MAIN`）だけです。カメックスはバトル場でもベンチでも使えます。使うカメックスがねむり・マヒ・こんらんなら `POKEMON_ASLEEP`・`POKEMON_PARALYZED`・`POKEMON_CONFUSED`（どくだけなら使える）。つける先の特殊状態は関係しません。
- 手札にないカード（ない番号・相手の手札・山札・場についたカード）は `CARD_NOT_IN_HAND`、エネルギーでないカードは `NOT_BASIC_ENERGY`、「水」でないエネルギーは `WRONG_ENERGY_TYPE`、「水」でないポケモンは `WRONG_POKEMON_TYPE`、相手のポケモンは `TARGET_NOT_YOURS`、`source` を指定したら `POWER_CHOICE_NOT_USED` です。どれも状態・乱数・ログを変えません。
- 通常の操作（`AttachEnergy`。1 番に 1 枚）でつけたあとも、あまごいは使えます（R12）。あまごいでつけたあと、その番にまだ通常の操作をしていなければ、通常の操作は `UnsupportedError`（`UNRESOLVED_ATTACH_AFTER_POWER_ATTACH`）です。あまごいでつけたカードを「1 番に 1 枚」に数えるかが『オフィシャルブック2000』に書かれていないためで、受け付けるとも拒否するとも決めていません（R13。[docs/rain-dance-v0.6.md](docs/rain-dance-v0.6.md)）。
- ログは `pokemon_power`（宣言）のすぐあとに `power_attach_energy`（`energy`・`to_pokemon_id`）です。通常の操作の `attach_energy`・エナジートランスの `move_energy` とは別です。乱数は使いません。
- あまごいでつけた枚数（`energy_attached_by_powers_this_turn`）が 0 でない番の状態は、書き出しの形式 9 だけが表せます（形式 1〜8 は `ValueError`。0 なら形式 1〜8 は v0.5 と同じ）。
- ハイドロポンプ（水水水・40+）は、ついている「水」エネルギーのうち必要な 3 個より多いもの 1 個につき 10 を、2 個ぶんまで追加します（p.321 の基本となるダメージ。弱点・プラスパワーなどはそのあと）。

### ポケモンパワー・ダメージスワップ（v0.7）

フーディン（PMCG1-049）の「ダメージスワップ」は、自分の番の中で何度でも、自分の場のポケモン（`source`。場のポケモンの番号）にのっているダメージカウンターを 1 個、自分の場の別のポケモン（`target`）にのせかえます（`energy` は使わない）。バトル場・ベンチのどちらのフーディンも使え、フーディン自身を移動元・移動先にできます。1 回の使用で 1 個です（実装上の仮定）。

```python
from kyuura_engine import (
    AttachEnergy, EndTurn, EvolvePokemon, IllegalActionError, PlaceStartingPokemon, ReportJankenResult, UseAttack, UsePokemonPower,
    apply_command, expand_decklist, new_game, state_to_dict,
)
from kyuura_engine.rng import rng_fingerprint

deck0 = expand_decklist({"PMCG1-043": 4, "PMCG1-046": 4, "PMCG1-049": 4, "PMCG1-101": 48})
# ケーシィ（PMCG1-043）・ユンゲラー（PMCG1-046）・フーディン（PMCG1-049）4 枚ずつ、超エネルギー 48 枚
deck1 = expand_decklist({"PMCG1-060": 4, "PMCG1-098": 56})   # コラッタ 4 枚・炎エネルギー 56 枚
state = new_game(deck0, deck1, seed=130)

def in_hand(player, card_id):
    return next(uid for uid in state.players[player].hand if state.cards[uid].card_id == card_id)

abras = [uid for uid in state.players[0].hand if state.cards[uid].card_id == "PMCG1-043"]
state = apply_command(state, PlaceStartingPokemon(0, abras[0], tuple(abras[1:2])))   # バトル場とベンチにケーシィ
state = apply_command(state, PlaceStartingPokemon(1, in_hand(1, "PMCG1-060"), ()))   # 相手はバトル場にコラッタ
state = apply_command(state, ReportJankenResult(winner=0))
active, bench = state.players[0].active.pokemon_id, state.players[0].bench[0].pokemon_id
for turn in (1, 3):   # 1 番・3 番は自分、2 番・4 番は相手（コラッタの「かみつく」20。弱点ではない）
    if turn == 3:
        state = apply_command(state, EvolvePokemon(0, in_hand(0, "PMCG1-046"), active))   # 3 番: ケーシィ → ユンゲラー
    state = apply_command(state, AttachEnergy(0, in_hand(0, "PMCG1-101"), state.players[0].active.card))
    state = apply_command(state, EndTurn(0))
    state = apply_command(state, AttachEnergy(1, in_hand(1, "PMCG1-098"), state.players[1].active.card))
    state = apply_command(state, UseAttack(1, 0))

# 5 番: ユンゲラーをフーディンに進化（2 進化）。ダメージ（40）はそのまま。その番にダメージスワップを使える
state = apply_command(state, EvolvePokemon(0, in_hand(0, "PMCG1-049"), active))
alakazam = state.players[0].active
print(state.card_def(alakazam.card).name_ja, [p.name_ja for p in state.card_def(alakazam.card).powers],
      [(pk.pokemon_id, pk.damage) for pk in state.players[0].in_play()])
# フーディン ['ダメージスワップ'] [(1, 40), (2, 0)]
before, fingerprint = len(state.log), rng_fingerprint(state.rng)
state = apply_command(state, UsePokemonPower(0, alakazam.pokemon_id, 0, source=active, target=bench))   # 1 個（10）をベンチのケーシィへ
print([e["kind"] for e in state.log[before:]], [(pk.pokemon_id, pk.damage) for pk in state.players[0].in_play()],
      rng_fingerprint(state.rng) == fingerprint)
# ['pokemon_power', 'move_damage_counter'] [(1, 30), (2, 10)] True      乱数は使わない
state = apply_command(state, UsePokemonPower(0, alakazam.pokemon_id, 0, source=active, target=bench))   # 何度でも使える
print([(pk.pokemon_id, pk.damage) for pk in state.players[0].in_play()], state.phase.value, state.current_player)
# [(1, 20), (2, 20)] main 0      番は続く（合計のダメージは変わらない）
try:   # HP 30 のケーシィ（ダメージ 20）にもう 1 個のせると「きぜつ」するので使えない
    apply_command(state, UsePokemonPower(0, alakazam.pokemon_id, 0, source=active, target=bench))
except IllegalActionError as error:
    print(error.code)
# WOULD_KNOCK_OUT      状態・乱数・ログは変わらない
try:   # 同じポケモンへは移せない（「別のポケモン」）
    apply_command(state, UsePokemonPower(0, alakazam.pokemon_id, 0, source=active, target=active))
except IllegalActionError as error:
    print(error.code)
# SAME_POKEMON
print(dict(state.log[-1]))
# {'kind': 'move_damage_counter', 'turn': 5, 'player': 0, 'pokemon': 8, 'pokemon_id': 1, 'power': 'PMCG1-049@power0', 'count': 1,
#  'from_pokemon_id': 1, 'to_pokemon_id': 2, 'from_total_damage': 20, 'to_total_damage': 20}
print(state_to_dict(state, format_version=9)["format_version"])
# 9      書き出しの形式は v0.6 と同じ
```

- のせたら移動先のダメージが HP と同じか大きくなる（きぜつする）移動は `WOULD_KNOCK_OUT` で、状態を変える前に拒否します（「この力によってポケモンが「きぜつ」しないかぎり」。p.153・p.320）。この力でポケモンがきぜつすることはありません。
- 移したカウンターは「ダメージを受けた」ことになりません（p.320）。弱点・抵抗力・プラスパワー・ディフェンダーは計算せず、ログ `damage` も出ません。ログは `pokemon_power`（宣言）のすぐあとに `move_damage_counter`（`count`・`from_pokemon_id`・`to_pokemon_id`・移したあとのダメージ）です。乱数は使いません。
- 使うフーディンがねむり・マヒ・こんらんなら `POKEMON_ASLEEP`・`POKEMON_PARALYZED`・`POKEMON_CONFUSED`（どくだけなら使える）。移動元・移動先の特殊状態は関係しません。相手のポケモンは `SOURCE_NOT_YOURS`・`TARGET_NOT_YOURS`、同じポケモンは `SAME_POKEMON`、カウンターのないポケモンからは `NO_DAMAGE_COUNTERS`、`energy` を指定したら `POWER_CHOICE_NOT_USED`。
- ユンゲラーの「じこさいせい」（超超）は、ワザを使うプレイヤーが、ついている「超」エネルギーカードから 1 枚を決定（`decision.kind` が`discard_energy`。`ResolveDecision` で答える）で選んでトラッシュし、ダメージカウンターをすべてとりのぞきます。
- 状態の項目・書き出しの形式は加えていません（形式 9 のまま）。

### ポケモンパワー・かがくへんかガス（v0.8）

ベトベトン（PMCG3-007）の「かがくへんかガス」は常にはたらいていて、使用を宣言しません。場（バトル場・ベンチ）にいて、ねむり・マヒ・こんらんでないベトベトンが 1 匹でもいれば、両方のプレイヤーの「かがくへんかガス」以外の特殊能力は使えません（`POWER_SUPPRESSED`）。はたらいているかは `working_power_suppressors(state)`、ある特殊能力を消しているベトベトンは `power_suppressors(state, pokemon_id, power_index)` で、コマンドを送らずに調べられます。

```python
from kyuura_engine import (
    AttachEnergy, EndTurn, EvolvePokemon, IllegalActionError, PlaceStartingPokemon, ReportJankenResult, UseAttack, UsePokemonPower,
    apply_command, expand_decklist, new_game, power_suppressors, state_to_dict, working_power_suppressors,
)
from kyuura_engine.rng import rng_fingerprint

deck0 = expand_decklist({"PMCG1-043": 4, "PMCG1-046": 4, "PMCG1-049": 4, "PMCG1-060": 4, "PMCG1-101": 44})
# ケーシィ・ユンゲラー・フーディン・コラッタ 4 枚ずつ、超エネルギー 44 枚
deck1 = expand_decklist({"PMCG4-004": 4, "PMCG3-007": 4, "PMCG1-097": 52})
# ロケット団のベトベター（PMCG4-004）・ベトベトン（PMCG3-007）4 枚ずつ、草エネルギー 52 枚
state = new_game(deck0, deck1, seed=167)

def in_hand(player, card_id):
    return next(uid for uid in state.players[player].hand if state.cards[uid].card_id == card_id)

state = apply_command(state, PlaceStartingPokemon(0, in_hand(0, "PMCG1-043"), (in_hand(0, "PMCG1-060"),)))  # ケーシィ・ベンチにコラッタ
state = apply_command(state, PlaceStartingPokemon(1, in_hand(1, "PMCG4-004"), ()))   # 相手はバトル場にベトベター
state = apply_command(state, ReportJankenResult(winner=0))
alakazam, rattata = state.players[0].active.pokemon_id, state.players[0].bench[0].pokemon_id
muk = state.players[1].active.pokemon_id
state = apply_command(state, AttachEnergy(0, in_hand(0, "PMCG1-101"), state.players[0].active.card))
state = apply_command(state, EndTurn(0))
state = apply_command(state, AttachEnergy(1, in_hand(1, "PMCG1-097"), state.players[1].active.card))
state = apply_command(state, UseAttack(1, 0))   # 2 番: ベトベターの「どくガス」（ダメージなし・コインなしでどく）→ ポケモンチェックで 10
state = apply_command(state, EvolvePokemon(0, in_hand(0, "PMCG1-046"), alakazam))   # 3 番: ユンゲラーに進化（どくは消える）
state = apply_command(state, AttachEnergy(0, in_hand(0, "PMCG1-101"), state.players[0].active.card))
state = apply_command(state, EndTurn(0))

# 4 番: 相手のベトベターがベトベトンに進化。かがくへんかガスは、進化した番から常にはたらく（宣言しない）
state = apply_command(state, EvolvePokemon(1, in_hand(1, "PMCG3-007"), muk))
print(working_power_suppressors(state))
# (3,)
try:
    apply_command(state, UsePokemonPower(1, muk, 0))
except IllegalActionError as error:
    print(error.code)
# POWER_NOT_DECLARABLE      常にはたらいている特殊能力は使用を宣言しない（p.311・p.323）
state = apply_command(state, AttachEnergy(1, in_hand(1, "PMCG1-097"), state.players[1].active.card))
state = apply_command(state, EndTurn(1))

# 5 番: ユンゲラーをフーディンに進化。ダメージスワップは、相手のベトベトンのかがくへんかガスに消されている
state = apply_command(state, EvolvePokemon(0, in_hand(0, "PMCG1-049"), alakazam))
print(power_suppressors(state, alakazam, 0), [(pk.pokemon_id, pk.damage) for pk in state.players[0].in_play()])
# (3,) [(1, 10), (2, 0)]
before, fingerprint = state_to_dict(state, format_version=9), rng_fingerprint(state.rng)
try:
    apply_command(state, UsePokemonPower(0, alakazam, 0, source=alakazam, target=rattata))
except IllegalActionError as error:
    print(error.code)
# POWER_SUPPRESSED
print(state_to_dict(state, format_version=9) == before, rng_fingerprint(state.rng) == fingerprint)
# True True      宣言の前に拒否するので、状態・乱数・ログは変わらない
state = apply_command(state, AttachEnergy(0, in_hand(0, "PMCG1-101"), state.players[0].active.card))
state = apply_command(state, UseAttack(0, 0))   # フーディンの「あやしいひかり」（30）。コインが「おもて」なら相手をこんらんに
print(state.players[1].active.conditions.confused, working_power_suppressors(state))
# True ()      こんらんのベトベトンのかがくへんかガスは消える（p.48）
state = apply_command(state, EndTurn(1))

# 7 番: ベトベトンはこんらんのまま。ダメージスワップをまた使える（同じ盤面でも、今の状態から求める）
before = len(state.log)
state = apply_command(state, UsePokemonPower(0, alakazam, 0, source=alakazam, target=rattata))
print([e["kind"] for e in state.log[before:]], [(pk.pokemon_id, pk.damage) for pk in state.players[0].in_play()])
# ['pokemon_power', 'move_damage_counter'] [(1, 0), (2, 10)]
print(any("gas" in e["kind"] or "suppress" in e["kind"] for e in state.log), state_to_dict(state, format_version=9)["format_version"])
# False 9      かがくへんかガスのログ・状態の項目はない（書き出しは v0.7 と同じ形式 9）
```

- はたらいているかは、問い合わせのたびに今の状態（場のポケモン・いちばん上のカード・特殊状態）から求めます。進化した番からはたらき、きぜつ・ねむり・マヒ・こんらんで消え、回復（ねむりのコイン・マヒの回復・にげる・ポケモンいれかえ・ふきとばし）したら、その時点からまたはたらきます。どくは関係しません。
- 自分のベトベトンのかがくへんかガスも、自分の特殊能力を消します（p.48 の解説「自分のほうも特殊能力を使えなくなる」）。かがくへんかガスどうしは消し合いません。
- ワザ・トレーナー・手札からつける通常の操作・進化・にげるは止めません。消える前にすませた特殊能力の結果（つけかえた・つけたエネルギー、移したダメージカウンター）は戻しません。
- ロケット団のベトベター（PMCG4-004）の「どくガス」はダメージなし・コインなしで相手をどく状態に、「ねばりつく」（10+）はコインが「おもて」なら 20 を加えた 30 で相手をマヒ状態にします。化石の秘密のベトベター（PMCG3-003）は「ちいさくなる」が未実装でデッキに入りません。
- 状態の項目・書き出しの形式・ログのイベントは加えていません（形式 9 のまま）。

### ポケモンパワー・とうめい（v0.9）

ゴースト（PMCG3-030。化石の秘密）の「とうめい」は、ワザによってダメージや効果を受けるときに自動的にはたらき、使用を宣言しません（`UsePokemonPower` は `POWER_NOT_DECLARABLE`）。受けるときに、ゴースト側のプレイヤーがコインを 1 枚投げ、「おもて」ならそのワザのダメージと効果を受けません（1 つのワザにつき 1 匹 1 回）。ねむり・マヒ・こんらんのとき、かがくへんかガスがはたらいているときは、コインを投げずに受けます。はたらいているかは `working_evasion_power(state, pokemon_id)` で、コマンドを送らずに調べられます。

```python
from kyuura_engine import (
    AttachEnergy, EndTurn, EvolvePokemon, IllegalActionError, PlaceStartingPokemon, ReportJankenResult, UseAttack, UsePokemonPower,
    apply_command, expand_decklist, new_game, state_to_dict, working_evasion_power,
)

deck0 = expand_decklist({"PMCG3-029": 4, "PMCG3-030": 4, "PMCG1-101": 52})
# 化石の秘密のゴース（PMCG3-029）・ゴースト（PMCG3-030）4 枚ずつ、超エネルギー 52 枚
deck1 = expand_decklist({"PMCG1-060": 4, "PMCG4-004": 4, "PMCG3-007": 4, "PMCG1-097": 48})
# コラッタ（PMCG1-060）・ロケット団のベトベター（PMCG4-004）・ベトベトン（PMCG3-007）4 枚ずつ、草エネルギー 48 枚
state = new_game(deck0, deck1, seed=65)

def in_hand(player, card_id):
    return next(uid for uid in state.players[player].hand if state.cards[uid].card_id == card_id)

state = apply_command(state, PlaceStartingPokemon(0, in_hand(0, "PMCG3-029"), ()))   # バトル場にゴース
state = apply_command(state, PlaceStartingPokemon(1, in_hand(1, "PMCG1-060"), (in_hand(1, "PMCG4-004"),)))  # コラッタ・ベンチにベトベター
state = apply_command(state, ReportJankenResult(winner=0))
ghost, grimer = state.players[0].active.pokemon_id, state.players[1].bench[0].pokemon_id
state = apply_command(state, AttachEnergy(0, in_hand(0, "PMCG1-101"), state.players[0].active.card))
state = apply_command(state, EndTurn(0))
state = apply_command(state, AttachEnergy(1, in_hand(1, "PMCG1-097"), state.players[1].active.card))
state = apply_command(state, EndTurn(1))

# 3 番: ゴースをゴーストに進化。「とうめい」は進化した番からはたらく（自動的にはたらき、宣言しない）
state = apply_command(state, EvolvePokemon(0, in_hand(0, "PMCG3-030"), ghost))
print(working_evasion_power(state, ghost))
# PMCG3-030@power0
try:
    apply_command(state, UsePokemonPower(0, ghost, 0))
except IllegalActionError as error:
    print(error.code)
# POWER_NOT_DECLARABLE
state = apply_command(state, EndTurn(0))

# 4 番: コラッタの「かみつく」（20）がゴーストへ。ダメージを受けるとき、ゴースト側のプレイヤー（0）がコインを投げる
before = len(state.log)
state = apply_command(state, UseAttack(1, 0))
for e in state.log[before:]:
    if e["kind"] in ("attack", "coin_flip", "evade_check", "attack_evaded", "damage"):
        print(e["kind"], {k: e[k] for k in ("player", "source", "result", "element", "evaded", "amount") if k in e})
# attack {'player': 1}
# coin_flip {'player': 0, 'source': 'power', 'result': 'heads'}
# evade_check {'player': 0, 'result': 'heads', 'element': 'damage', 'evaded': True}
# attack_evaded {'player': 0, 'element': 'damage', 'amount': 20}      「おもて」: 20 を受けない（damage のログはない）
print(state.players[0].active.damage, state.turn_number, state.current_player)
# 0 5 0      ワザは使ったことになり、番は終わった（ワザの失敗ではない）
state = apply_command(state, EndTurn(0))

# 6 番: ベンチのベトベターをベトベトンに進化。かがくへんかガスで「とうめい」の力は消え、コインを投げない
state = apply_command(state, EvolvePokemon(1, in_hand(1, "PMCG3-007"), grimer))
print(working_evasion_power(state, ghost))
# None
before = len(state.log)
state = apply_command(state, UseAttack(1, 0))
print([e["kind"] for e in state.log[before:]][:3], state.players[0].active.damage)
# ['attack', 'damage', 'turn_end'] 20
print(state_to_dict(state, format_version=9)["format_version"])
# 9      書き出しの形式は v0.8 と同じ（「とうめい」の結果はワザの処理の中だけで使い、状態に持たない）
```

- コインは最初に受ける要素で 1 回だけ投げ、その結果をそのワザのダメージと効果（どく・ねむり・マヒ・こんらん・入れ替え）のすべてに使います。「おもて」なら受けなかった要素ごとに `attack_evaded`、「うら」ならいつもどおり `damage`・`special_condition` などが続きます。
- 弱点・抵抗力・プラスパワー・ディフェンダーを計算して最終ダメージが 0 なら、その要素ではコインを投げません（「ダメージを受けなかった」。p.321）。同じワザの効果を受けるときに投げます。
- ワザを使う側への要素（ピカチュウの「でんげき」の自分へのダメージなど）はそのまま処理します。受けなかったダメージでは、「ダメージを与えたら」の回復（メガドレイン・やどりぎのタネ）は起こりません。トレーナー・特殊能力・ポケモンチェックのどく・こんらんの 20 には、はたらきません。
- 「ダメージ → ワザのコイン → 特殊状態」のワザ（どくばり・したでなめるなど）を、はたらいている「とうめい」のゴーストに使い、最終ダメージが 0 より大きいときは、「おもて」のあとのワザのコインを投げるかが原典で決められないので、ワザの前に止めます（`UNRESOLVED_EVADED_EFFECT_COIN`）。
- ゴースの「エナジーへんかん」は、トラッシュのエネルギーカードを最大 2 枚、ワザの途中の決定（`recover_energy`）で選んで手札に加え、そのあと自分に 10。0 枚を選ぶのは原典で決められないので止めます（`UNRESOLVED_RECOVER_ZERO_ENERGY`。決定は待ったまま）。

### ポケモンパワー・はんげき（v0.10）

カイリキー（PMCG1-057）の「はんげき」は、相手のワザによってダメージを受けたときに自動的にはたらき、使用を宣言しません（`UsePokemonPower` は `POWER_NOT_DECLARABLE`）。ダメージを受けるとき、すでにねむり・マヒ・こんらんなら、かがくへんかガスがはたらいていれば、はたらきません。そのワザのダメージの処理が終わったところで、ダメージを与えたポケモン（ワザを使ったポケモン）に、弱点・抵抗力に関係なく 10 ダメージを与えます（カイリキーがそのダメージできぜつしても与える）。はたらいているかは `working_counterattack_power(state, pokemon_id)` で、コマンドを送らずに調べられます。

```python
from kyuura_engine import (
    AttachEnergy, EndTurn, EvolvePokemon, IllegalActionError, PlaceStartingPokemon, ReportJankenResult, ResolveDecision, UseAttack,
    UsePokemonPower, apply_command, expand_decklist, new_game, state_to_dict, working_counterattack_power,
)

deck0 = expand_decklist({"PMCG1-053": 4, "PMCG1-055": 4, "PMCG1-057": 4, "PMCG1-102": 48})
# ワンリキー（PMCG1-053）・ゴーリキー（PMCG1-055）・カイリキー（PMCG1-057）4 枚ずつ、闘エネルギー 48 枚
deck1 = expand_decklist({"PMCG1-058": 4, "PMCG1-102": 56})
# エビワラー（PMCG1-058。ジャブ 20・スペシャルパンチ 40）4 枚、闘エネルギー 56 枚
state = new_game(deck0, deck1, seed=130)

def in_hand(player, card_id):
    return next(uid for uid in state.players[player].hand if state.cards[uid].card_id == card_id)

def attach(player):
    return apply_command(state, AttachEnergy(player, in_hand(player, "PMCG1-102"), state.players[player].active.card))

def show(start, kinds):
    for e in state.log[start:]:
        if e["kind"] in kinds:
            print(e["kind"], {k: e[k] for k in ("player", "amount", "total_damage", "attacker_pokemon_id", "knocked_out") if k in e})

machops = [uid for uid in state.players[0].hand if state.cards[uid].card_id == "PMCG1-053"]
state = apply_command(state, PlaceStartingPokemon(0, machops[0], (machops[1],)))   # バトル場とベンチにワンリキー
state = apply_command(state, PlaceStartingPokemon(1, in_hand(1, "PMCG1-058"), ()))  # バトル場にエビワラー
state = apply_command(state, ReportJankenResult(winner=0))
machamp, hitmonchan = state.players[0].active.pokemon_id, state.players[1].active.pokemon_id
state = attach(0)
state = apply_command(state, EndTurn(0))
state = attach(1)
state = apply_command(state, UseAttack(1, 0))  # 2 番: ジャブ 20（ワンリキーは「はんげき」を持たない）

# 3 番: ゴーリキーに、5 番: カイリキーに進化（場のポケモンの番号は変わらない。ダメージ 20・40 はそのまま）
state = apply_command(state, EvolvePokemon(0, in_hand(0, "PMCG1-055"), machamp))
state = attach(0)
state = apply_command(state, EndTurn(0))
state = attach(1)
state = apply_command(state, UseAttack(1, 0))  # 4 番: ジャブ 20
state = apply_command(state, EvolvePokemon(0, in_hand(0, "PMCG1-057"), machamp))
print(working_counterattack_power(state, machamp), state.players[0].active.damage)
# PMCG1-057@power0 40      自動的にはたらく（宣言しない）
try:
    apply_command(state, UsePokemonPower(0, machamp, 0))
except IllegalActionError as error:
    print(error.code)
# POWER_NOT_DECLARABLE
state = attach(0)
state = apply_command(state, EndTurn(0))

# 6 番: エビワラーのスペシャルパンチ（40）。カイリキーがダメージを受けたので、ワザを使ったエビワラーに 10（弱点・抵抗力に関係なく）
state = attach(1)
before = len(state.log)
state = apply_command(state, UseAttack(1, 1))
show(before, ("attack", "damage", "counterattack", "coin_flip", "turn_end"))
# attack {'player': 1}
# damage {'player': 0, 'amount': 40, 'total_damage': 80}
# counterattack {'player': 0, 'amount': 10, 'total_damage': 10, 'attacker_pokemon_id': 3, 'knocked_out': False}
# turn_end {'player': 1}      乱数を使わない（coin_flip はない）
state = apply_command(state, EndTurn(0))

# 8 番: もう一度スペシャルパンチ。カイリキーは 120 で HP 以上になるが、それによって「きぜつ」しても 10 を与える。
# きぜつの処理（サイド・交代）はワザのあと
before = len(state.log)
state = apply_command(state, UseAttack(1, 1))
show(before, ("damage", "counterattack", "knock_out"))
# damage {'player': 0, 'amount': 40, 'total_damage': 120}
# counterattack {'player': 0, 'amount': 10, 'total_damage': 20, 'attacker_pokemon_id': 3, 'knocked_out': False}
# knock_out {'player': 0}
print(state.decision.kind, state.decision.player, state.players[1].active.damage)
# take_prize 1 20      エビワラーの持ち主がサイドを取る
state = apply_command(state, ResolveDecision(1, state.decision.id, (0,)))
state = apply_command(state, ResolveDecision(0, state.decision.id, (state.players[0].bench[0].pokemon_id,)))
print(state.cards[state.players[0].active.card].card_id, state.current_player, state_to_dict(state, format_version=9)["format_version"])
# PMCG1-053 0 9      ベンチのワンリキーが出て、番が進んだ。書き出しの形式は v0.9 と同じ
```

- 「はんげき」の 10 は特殊能力によるダメージです。ワザによるダメージではないので、プラスパワー・ディフェンダー・「とうめい」を計算せず、相手のカイリキーの「はんげき」もはたらかせません（カイリキーどうしでも 1 回だけ）。
- 与えるのは、そのワザのダメージの処理（自分へのダメージを含む。ゴーリキーのじごくぐるま・ピカチュウのでんげき）のあと、ダメージ以外の効果（ワザのコイン・特殊状態・ふきとばしの入れ替え・メガドレインの回復）の前です（p.89）。同じワザの効果でダメージのあとに特殊状態になっても、はたらきます（「すでに」）。
- 最終ダメージが 0（抵抗力・ディフェンダー・からてチョップの 0 以下）・ダメージのないワザ・どく・こんらんの 20・ダメージスワップ・自分のワザでは、はたらきません。
- 「はんげき」でワザを使ったポケモンがきぜつしたら、カイリキーの持ち主がサイドを取ります（番のプレイヤーでなくても）。そのあとの自分の回復（メガドレイン）は処理しません（`drain_heal_skipped`）。ワザを使ったポケモンが同じワザの自分へのダメージですでにきぜつしていれば、与えません（`counterattack_skipped`）。
- カイリキーがワザできぜつし、ワザを使ったポケモンが「はんげき」できぜつする（「はんげき」がなければきぜつしない）場合は、同時のきぜつか（p.324）が原典で決められないので、ワザの宣言の前に止めます（`UNRESOLVED_COUNTERATTACK_DOUBLE_KNOCKOUT`。状態・乱数・ログは変わらない）。
- ゴーリキーの「からてチョップ」は、50 から自分のダメージカウンターの数 × 10 を引いた数が基本となるダメージ（0 以下ならダメージを与えない）、「じごくぐるま」は 60 のあと自分にも 20 です。

### 操作（コマンド）

| コマンド | 内容 |
|---|---|
| `PlaceStartingPokemon(player, active, bench)` | 対戦準備: バトル場に 1 匹、ベンチに 5 匹まで |
| `DrawMulliganCards(player, count)` | 対戦準備: 相手の切り直し 1 回ぶん、0〜2 枚引く |
| `ReportJankenResult(winner)` | 対戦準備: ジャンケンの勝者（先攻） |
| `PlayBasicToBench(player, card)` | 手札のたねポケモンをベンチに出す |
| `AttachEnergy(player, energy, target)` | エネルギーをつける（1 番に 1 枚） |
| `Retreat(player, discard, new_active)` | にげる（何度でも）。ねむり・マヒのポケモンは宣言できない（`POKEMON_ASLEEP`・`POKEMON_PARALYZED`。v0.3b）。こんらんのポケモンはエネルギーをトラッシュしてからコイン、「うら」なら失敗し、そのポケモンはその番もう宣言できない（`RETREAT_ALREADY_FAILED`。v0.3c） |
| `UseAttack(player, attack_index)` | ワザを使う（番が終わる）。コインを投げるワザ（v0.2d・v0.2f・v0.3a・v0.3b・v0.3c）は、エンジンがコインを投げる。番の終わりのあと、エンジンがポケモンチェックをする（v0.3a）。ねむり・マヒのポケモンは使えない（v0.3b）。こんらんのポケモンは宣言のあとでコイン、「うら」なら自分に 20 で番が終わる（v0.3c）。「ダメージを受けない」状態の相手へのダメージの要素は無効（v0.4b）。受けるポケモンの「とうめい」がはたらいていれば、受けるときにゴースト側のプレイヤーがコインを投げる（v0.9）。ダメージを受けた相手のポケモンの「はんげき」がはたらいていれば、ダメージの処理のあとにワザを使ったポケモンに 10（v0.10） |
| `EndTurn(player)` | ワザを使わずに番を終える（そのあとポケモンチェック。v0.3a） |
| `TakePrize(player, index)` | 相手のポケモンがきぜつしたとき、サイドを 1 枚選んで取る（自分のワザで自分のポケモンがきぜつしたら相手が取る。v0.2f） |
| `PromoteActive(player, pokemon)` | バトル場のポケモンがいなくなったとき、ベンチから出す |
| `ResolveDecision(player, decision, choices)` | 保留中の決定に答える（どの種類の決定にも使える。v0.2a）。答えるのは `decision.player`（v0.4d のふきとばしでは、ワザを使われた側のプレイヤー） |
| `PlayTrainer(player, card)` | 手札のトレーナーカードを使う（v0.2b。対応した 5 枚だけ。プラスパワーは v0.2c、ディフェンダーは v0.2e） |
| `EvolvePokemon(player, card, target)` | 手札の進化カードで、自分の場のポケモン（`target` は場のポケモンの番号）を進化させる（v0.4a。v0.4c から 1 進化 → 2 進化も。対応した進化カードだけ） |
| `UsePokemonPower(player, pokemon, power=0, energy=None, source=None, target=None)` | 自分の場のポケモン（`pokemon` は場のポケモンの番号）の特殊能力を使う（v0.5。番は終わらない。対応した特殊能力だけ。エナジートランスは `energy`（ついているカード）・`source`・`target`、v0.6 のあまごいは `energy`（手札のカード）・`target`、v0.7 のダメージスワップは `source`・`target` を指定する。v0.8 のかがくへんかガス・v0.9 のとうめい・v0.10 のはんげきは宣言しないので `POWER_NOT_DECLARABLE`、はたらいているかがくへんかガスに消されている特殊能力は `POWER_SUPPRESSED`） |

## 現在の対応ルール（公式ルール 2000.02.14版）

詳しくは [docs/rules-2000-02-14.md](docs/rules-2000-02-14.md)（項目ごとの誌面のページ・kyuura の記録 id・テスト）と [docs/implementation-status.md](docs/implementation-status.md)。

- デッキ 60 枚ちょうど、同じ名前のカードは 4 枚まで（基本エネルギーは制限なし）、たねポケモン必須
- 手札 7 枚。たねポケモンがなければ切り直し（来るまでくりかえす）。相手は切り直し 1 回ごとに、サイドを置いた後で最大 2 枚引ける。両方とも切り直したらどちらも引かない
- バトル場 1 匹、対戦準備のベンチは 5 匹まで、サイド 6 枚、ジャンケンで勝った人が先攻
- 番の最初に必ず 1 枚引く（先攻の最初の番も引く）。山札がなくて引けなければ負け
- たねポケモンをベンチに出す（5 匹まで）、エネルギーは 1 番に 1 枚（あまごいでつけたあとの通常の操作は止める。v0.6 の R13）、にげるは 1 番に何度でも
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
- ポケモンの特殊能力（v0.5）: 自分の場のポケモン（ベンチも）の特殊能力のうち、そのとき使えるものを宣言して使う。特に指示されていないかぎり、何度でも・エネルギーなしでも使え、使っても番は終わらない。進化前の特殊能力は使えない。宣言したら、すべてすませてから（p.311・p.323）。特殊状態の制限は特殊能力の説明ごと（エナジートランス・あまごいは「このカード」のねむり・マヒ・こんらん）。カードの記述がルールとむじゅんするときはカードの記述を優先する（p.307。あまごいは通常の操作でつけたあとも使える）
- ダメージカウンターの移動（v0.7。ダメージスワップ）: 移動でダメージが HP 以上になるならきぜつする（p.320）が、ダメージスワップはきぜつさせる移動ができない（p.153）。移動で増えたダメージは「ダメージを受けた」ことにならない（p.320）。ダメージカウンター 1 個 = 10（p.319）。進化してもカウンターはそのまま（p.310・p.323）
- 常にはたらく特殊能力（v0.8。かがくへんかガス）: 使用を宣言しない（p.311・p.323）。このカードが場にいるかぎり、「かがくへんかガス」以外のすべての特殊能力は使えず、その力も消える。このカードがねむり・マヒ・こんらんのとき、この力は消える（p.48）。自分と相手の両方の特殊能力を消す。ワザ・トレーナーは止めない
- 自動的にはたらく特殊能力（v0.9。とうめい）: 使用を宣言しない（p.323）。このカードがワザによってダメージや効果を受けるとき、コインを投げて「おもて」なら、このカードはそのダメージと効果を受けない（p.160）。1 つのワザにつき 1 回、ゴースト側のプレイヤーが投げる。バトル場でもベンチでも、相手・自分のワザのどちらでもはたらき、ワザを失敗させる効果ではない（p.159）。ねむり・マヒ・こんらん・かがくへんかガスで消える
- ダメージを受けたときに自動的にはたらく特殊能力（v0.10。はんげき）: 使用を宣言しない（p.323）。このカードが相手のワザによってダメージを受けたとき、（それによってこのカードが「きぜつ」しても、）ダメージを与えたポケモンに、「弱点・抵抗力」に関係なく、10ダメージ。ダメージを受けるとき、すでにねむり・マヒ・こんらんならはたらかない（p.192）。与えるのはワザのダメージの処理のあと・ダメージ以外の効果の前（p.89）。特殊能力によるダメージで、ディフェンダーで防げず、別の「はんげき」をはたらかせない（p.138・p.245・p.321）。最終ダメージが 0 なら「ダメージを受けなかった」（p.319）。かがくへんかガスで消える
- ワザによる持続する効果（v0.4b）: ワザが与え、番をまたいで残る（p.322）。「かたまる」の効果（次の相手の番、ダメージを受けない）は、そのポケモンへのダメージの要素を無効にし（p.321）、次の相手の番の終わりに消える。ベンチに戻る・場をはなれる・進化で消え、復活しない（p.311・p.322・p.323）。ポケモンチェックははたらかない（p.323）

## 現在の対応カード

第1弾の、効果のないワザだけを持つたねポケモン 10 種と、基本エネルギー 6 種、トレーナー 5 種（v0.2b・v0.2c・v0.2e）（kyuura docs/engine-readiness.md 5章の段階 1 とディフェンダー）、コインを投げるワザを持つドードー（v0.2d）、自分へのダメージのワザを持つピカチュウ（v0.2f）、相手をどく状態にするワザを持つビードル（v0.3a）、相手をマヒ・ねむり状態にするワザを持つキャタピー・パラス（v0.3b）、相手をこんらん状態にするワザを持つロコン（v0.3c）、1 進化ポケモンのパラセクト・ジュゴン（v0.4a）・トランセル・コクーン（v0.4b）、2 進化ポケモンのスピアー（v0.4c）・バタフリー（v0.4d）、ポケモンパワーを持つ 2 進化ポケモンのフシギバナとその進化元のフシギダネ・フシギソウ（v0.5）、ポケモンパワーを持つ 2 進化ポケモンのカメックスとその進化元のゼニガメ・カメール（v0.6）、ポケモンパワーを持つ 2 進化ポケモンのフーディンとその進化元のケーシィ・ユンゲラー（v0.7）、常にはたらくポケモンパワーを持つ 1 進化ポケモンのベトベトンとその進化元のロケット団のベトベター（v0.8）、ワザを受けるときに自動的にはたらくポケモンパワーを持つ 1 進化ポケモンの化石の秘密のゴーストとその進化元の化石の秘密のゴース（v0.9）、ダメージを受けたときに自動的にはたらくポケモンパワーを持つ 2 進化ポケモンのカイリキーとその進化元のゴーリキー（v0.10。ワンリキーは v0.1 から）です。『オフィシャルブック2000』のカードのページと照合済みです（ポニータ・フシギソウのワザ名、きずぐすり・ポケモンいれかえ・ディフェンダーの文面、ドードーのワザの説明の書き方、ケーシィのワザの説明の読点に食い違い。[docs/data-provenance.md](docs/data-provenance.md)）。

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
| PMCG1-023 | ゼニガメ（v0.6。あわ 10・コインが「おもて」なら相手をマヒ状態に、からにこもる（コインが「おもて」なら次の相手の番ダメージを受けない）。p.87） | PMCG1-027 | カメール（v0.6。ゼニガメから進化。からにこもる、かみつく 40。p.88） |
| PMCG1-032 | カメックス（v0.6。カメールから進化する 2 進化。ポケモンパワー「あまごい」: 自分の番の中で何度でも、手札の「水」エネルギーカードを自分の場の「水」ポケモンにつける、ハイドロポンプ 40+（必要な 3 個より多い「水」エネルギー 1 個につき +10、2 個まで）。p.90） | PMCG1-043 | ケーシィ（v0.7。ねんりき 10・コインが「おもて」なら相手をマヒ状態に。にげる 0。p.149） |
| PMCG1-046 | ユンゲラー（v0.7。ケーシィから進化。じこさいせい（ついている「超」エネルギーカードを選んで 1 枚トラッシュし、自分のダメージカウンターをすべてとりのぞく）、ちょうねんりき 50。p.151） | PMCG1-049 | フーディン（v0.7。ユンゲラーから進化する 2 進化。ポケモンパワー「ダメージスワップ」: 自分の番の中で何度でも、きぜつさせないかぎり、自分の場のポケモンのダメージカウンターを自分の場の別のポケモンにのせかえる（1 回 1 個）、あやしいひかり 30・コインが「おもて」なら相手をこんらん状態に。p.153） |
| PMCG4-004 | ベトベター（v0.8。ポケモンカード第4弾ロケット団。どくガス・ダメージなし・コインなしで相手をどく状態に、ねばりつく 10+・コインが「おもて」なら 20 を追加して相手をマヒ状態に。p.45） | PMCG3-007 | ベトベトン（v0.8。ベトベターから進化。ポケモンパワー「かがくへんかガス」: 常にはたらき、場にいるかぎり「かがくへんかガス」以外のすべての特殊能力を使えなくする（ねむり・マヒ・こんらんのときは消える）、ヘドロこうげき 30・コインが「おもて」なら相手をどく状態に。p.48） |
| PMCG3-029 | ゴース（v0.9。ポケモンカード第3弾化石の秘密。したでなめる 10・コインが「おもて」なら相手をマヒ状態に、エナジーへんかん・自分のトラッシュの「エネルギーカード」を最大 2 枚手札に加え、その後、自分に 10。にげる 0。p.158） | PMCG3-030 | ゴースト（v0.9。化石の秘密。ゴースから進化。ポケモンパワー「とうめい」: ワザによってダメージや効果を受けるときに自動的にはたらき、コインが「おもて」ならそのダメージと効果を受けない（ねむり・マヒ・こんらんのときは消える）、あくむ 10・コインなしで相手をねむり状態に。にげる 0。p.160。第1弾のゴースト PMCG1-047 は別のカードで未対応） |
| PMCG1-055 | ゴーリキー（v0.10。ワンリキーから進化。からてチョップ 50−・自分にのっているダメージカウンターの数 × 10 だけ小さくなる、じごくぐるま 60・自分にも 20。p.190） | PMCG1-057 | カイリキー（v0.10。ゴーリキーから進化する 2 進化。ポケモンパワー「はんげき」: 相手のワザによってダメージを受けたとき（きぜつしても）、ダメージを与えたポケモンに弱点・抵抗力に関係なく 10（ダメージを受けるとき、すでにねむり・マヒ・こんらんならはたらかない）、ちきゅうなげ 60。p.192。サカキのカイリキー PMCG6-061 は別のカードで未対応） |

| id | トレーナー（v0.2b） | 処理（『オフィシャルブック2000』p.254 の最新の説明） | 原典で決められないため止める場合 |
|---|---|---|---|
| PMCG1-074 | マサキ | 山札からカードを2枚引いて、手札に加える（足りなければ引けるだけ） | なし |
| PMCG1-071 | きずぐすり | 自分の場のポケモンを1匹選び、ダメージカウンターを2個とりのぞく | ダメージのあるポケモンがいない、ダメージのないポケモンを選ぶ |
| PMCG1-073 | ポケモンいれかえ | 自分の控えポケモンを1匹選び、対戦ポケモンと入れ替える | 控えポケモンがいない |
| PMCG1-079 | ディフェンダー（v0.2e。p.257） | 自分の場のポケモンを1匹選んでつけ、次の相手の番の終わりにトラッシュ。ついているポケモンがワザで受けるダメージを 7 段階で −20 | なし |
| PMCG1-081 | プラスパワー（v0.2c。p.257） | 自分の対戦ポケモンにつけて使い、自分の番の終わりにトラッシュ。ついているポケモンのワザが対戦ポケモンに与えるダメージを 5 段階で +10（控えへのダメージは変えない） | なし |

これ以外のカード（ドードーのほかの効果のあるワザを持つポケモン、ほかの進化カード（スピアー・バタフリー・フシギバナ・カメックス・フーディンのほかの 2 進化を含む）、エナジートランス・あまごい・ダメージスワップ・かがくへんかガス・とうめい・はんげきのほかのポケモンパワーを持つカード（サカキのカイリキーなど）、化石の秘密のベトベター・第1弾のゴーストなど効果を登録していないワザを持つカード、ほかのトレーナー、特殊エネルギーなど）はデッキに入れられません。効果のあるワザを「ダメージだけのワザ」として扱うことはしません。対戦用のたねポケモンのワザは、効果の登録表に「効果のないワザ」として 1 つずつ登録してあります（v0.2a）。v0.2a で対応したカード・ルールは v0.1 と同じです。トレーナーは、カード id で効果の実装を登録した 5 枚だけが使えます（v0.2b・v0.2c・v0.2e）。説明文のあるワザは、ドードーの「みだれづき」（v0.2d）、ピカチュウの「でんげき」（v0.2f）、ビードルの「どくばり」（v0.3a）、キャタピーの「いとをはく」・パラスの「キノコのほうし」（v0.3b）、ロコンの「あやしいひかり」（v0.3c）、パラセクトの「キノコのほうし」・ジュゴンの「れいとうビーム」（v0.4a）、トランセル・コクーンの「かたまる」「しびれごな」「どくのこな」（v0.4b。かたまるはカードごとに照合し、印刷の文面ではなく最新の説明にしたがう）、スピアーの「ダブルニードル」「どくばり」（v0.4c。ビードルのどくばりとは別に、スピアーのカード id で登録）、バタフリーの「ふきとばし」「メガドレイン」（v0.4d。印刷の文面ではなく最新の説明にしたがう）、フシギダネの「やどりぎのタネ」・フシギソウの「どくのこな」（v0.5。どくのこなはコクーンのものと違いコインを投げない）、ゼニガメの「あわ」「からにこもる」・カメールの「からにこもる」・カメックスの「ハイドロポンプ」（v0.6。からにこもる・ハイドロポンプは印刷の文面ではなく最新の説明にしたがう）、ケーシィの「ねんりき」・ユンゲラーの「じこさいせい」・フーディンの「あやしいひかり」（v0.7。じこさいせいは印刷の文面ではなく最新の説明にしたがう。フーディンのあやしいひかりは、ロコンと同じ名前でもフーディンのカード id で登録）、ロケット団のベトベターの「どくガス」「ねばりつく」・ベトベトンの「ヘドロこうげき」（v0.8）、化石の秘密のゴースの「したでなめる」「エナジーへんかん」・ゴーストの「あくむ」（v0.9。エナジーへんかんは印刷の文面ではなく最新の説明にしたがう）、ゴーリキーの「からてチョップ」「じごくぐるま」（v0.10。からてチョップは印刷の文面ではなく最新の説明にしたがう）だけを、照合した説明文とともに登録しています。ポケモンパワーは、フシギバナの「エナジートランス」（v0.5）・カメックスの「あまごい」（v0.6）・フーディンの「ダメージスワップ」（v0.7）・ベトベトンの「かがくへんかガス」（v0.8。常にはたらく）・ゴーストの「とうめい」（v0.9。自動的にはたらく）・カイリキーの「はんげき」（v0.10。ダメージを受けたときに自動的にはたらく）だけを、照合した文面とともに登録しています（パラセクトのキノコのほうしは、パラスと同じ名前なので同じとは決めず、p.39 で照合した）。

## 未実装の機能

退化・パラセクト・ジュゴン・トランセル・コクーン・スピアー・バタフリー・フシギソウ・フシギバナ・ゼニガメの系統・ケーシィの系統のほかの進化カード、ほかの相手の強制交代・与えたダメージによる回復のワザ、「かたまる」のほかのワザによる持続する効果（すなかけ・からまるいと・マーカーをのせる効果など）、ポケモンチェックの 1（指示されたこと）、特殊などく、エナジートランス・あまごい・ダメージスワップ・かがくへんかガス・とうめい・はんげきのほかのポケモンパワー（とうめい・はんげきのほかの自動的にはたらく（きぜつを取り消す［こんじょう］など）・かがくへんかガスのほかの常にはたらく・回数の制限のある・期限のある特殊能力を止める効果・決定を出す特殊能力。[docs/architecture-v0.5.md](docs/architecture-v0.5.md) 9 章・[docs/architecture-v0.6.md](docs/architecture-v0.6.md) 12 章・[docs/architecture-v0.7.md](docs/architecture-v0.7.md) 13 章・[docs/architecture-v0.8.md](docs/architecture-v0.8.md) 14 章・[docs/architecture-v0.9.md](docs/architecture-v0.9.md) 14 章・[docs/architecture-v0.10.md](docs/architecture-v0.10.md) 17 章）、ベンチ・複数のポケモンにダメージを与えるワザ、退化・手札に戻す効果、進化前のワザを使うカード（思い出させる）、ほかのトレーナーカード、スタジアム、ポケモンのどうぐ、ベイビィポケモン、特殊エネルギー、効果のあるワザ（みだれづき・でんげきのほか。特殊状態・控えへのダメージ・でんげき以外の自分へのダメージ・「うら」で失敗などのコインのワザを含む）、コインを使うトレーナー、ワザの失敗、サドン・デスの延長戦、旧裏の複数の時期のルールの切り替え、大会のレギュレーション、隠れた情報の管理（見る人ごとの状態）、合法な操作の一覧、状態を辞書からもどす処理、AI、GUI、Web アプリ、ネットワーク対戦。一覧は [docs/implementation-status.md](docs/implementation-status.md#未実装)。

原文から決められないため止める処理: 両方が同時に切り直したあと、片方だけがさらに切り直した場合の補償（`Phase.HALTED`）。トレーナーの上の表の場合（`UnsupportedError`。対戦は続けられる）。ポケモンチェックのどくで両方のプレイヤーのポケモンがきぜつする場合（v0.3a。`Phase.HALTED`）。ポケモンチェックで両方の対戦ポケモンがねむりの場合（v0.3b。`Phase.HALTED`。対応カードでは起こらない）。マヒの再付与で回復する番が変わる場合（v0.3b。`UnsupportedError`。対応カードでは起こらない）。ダメージを変えるカードがついたこんらん状態のポケモンのワザ、「にげる」に失敗したあとこんらんが消えて同じ番にバトル場に戻ったポケモンの「にげる」（v0.3c。`UnsupportedError`。コインの前）。v0.3d で調べ直し、どれも原典で決められないので止めたままです（[docs/unresolved-rulings-v0.3d.md](docs/unresolved-rulings-v0.3d.md)。v0.4a〜v0.4c でも変えていない）。進化したあとの HP が、のっているダメージ以下になる場合（v0.4a。`UnsupportedError`、`UNRESOLVED_EVOLUTION_HP`。対応カードでは起こらない。[docs/evolution-rules-v0.4a.md](docs/evolution-rules-v0.4a.md)）。「ダメージを受けない」状態（「かたまる」）のポケモンに、コインでダメージの量を決めるワザ（みだれづき、v0.4c からスピアーのダブルニードルも）を使う場合（v0.4b。`UnsupportedError`、`UNRESOLVED_PREVENTED_COIN_DAMAGE`。コインの前。[docs/persistent-damage-v0.4b.md](docs/persistent-damage-v0.4b.md) 5 章）。2 進化で新しく止める場合はありません（v0.4c）。相手の強制交代・与えたダメージによる回復（v0.4d）でも、新しく止める場合はありません（ふきとばしの致死ダメージ・「ダメージを受けない」相手へのメガドレインは原典から導けた。[docs/forced-switch-v0.4d.md](docs/forced-switch-v0.4d.md) 4 章・[docs/damage-drain-v0.4d.md](docs/damage-drain-v0.4d.md) 4 章）。ポケモンパワー・エナジートランス・やどりぎのタネ・どくのこな（v0.5）でも、新しく止める場合はありません（[docs/pokemon-powers-v0.5.md](docs/pokemon-powers-v0.5.md) 3 章）。あまごいでつけたあと、その番にまだ通常の操作をしていないときの通常の操作（v0.6。`UnsupportedError`、`UNRESOLVED_ATTACH_AFTER_POWER_ATTACH`。カードを動かす前。[docs/rain-dance-v0.6.md](docs/rain-dance-v0.6.md) の R13）。ダメージスワップ・ケーシィ・ユンゲラー・フーディンのワザ（v0.7）でも、新しく止める場合はありません（[docs/damage-swap-v0.7.md](docs/damage-swap-v0.7.md) 5 章）。かがくへんかガス・ベトベター・ベトベトンのワザ（v0.8）でも、新しく止める場合はありません（[docs/chemical-gas-v0.8.md](docs/chemical-gas-v0.8.md) 5 章）。はたらいている「とうめい」のゴーストに、「ダメージ → ワザのコイン → 特殊状態」のワザを使い、最終ダメージが 0 より大きい場合（v0.9。`UnsupportedError`、`UNRESOLVED_EVADED_EFFECT_COIN`。ワザの宣言の前。[docs/transparency-v0.9.md](docs/transparency-v0.9.md) の T19b）。エナジーへんかんで、トラッシュにエネルギーカードがあるのに 0 枚を選ぶ場合（v0.9。`UnsupportedError`、`UNRESOLVED_RECOVER_ZERO_ENERGY`。決定は待ったまま。[docs/haunter-line-v0.9.md](docs/haunter-line-v0.9.md) の H4）。カイリキーがワザのダメージできぜつし、ワザを使ったポケモンが「はんげき」のダメージできぜつする（「はんげき」がなければきぜつしない）場合（v0.10。`UnsupportedError`、`UNRESOLVED_COUNTERATTACK_DOUBLE_KNOCKOUT`。ワザの宣言の前。[docs/counterattack-v0.10.md](docs/counterattack-v0.10.md) の C18）。

## ディレクトリ

```
kyuura_engine/
  rules.py       ルールの組（2000.02.14版の数値）と根拠の一覧
  conditions.py  特殊状態（どく・ねむり・マヒ・こんらん）を付ける・置きかえる・回復する・ベンチに戻ったら・進化したら消す。v0.3a〜v0.4a
  persistent.py  ワザによる持続する効果（「かたまる」の「ダメージを受けない」）を付ける・期限・ベンチ・進化・きぜつで消す・はたらいているか。v0.4b
  continuous.py  常にはたらく特殊能力（かがくへんかガス）がはたらいているか・消している特殊能力を、今の状態から求める。v0.8（v0.9 の「とうめい」・v0.10 の「はんげき」の評価も使う）
  cards.py       カードの定義、kyuura のデータの読み込み、対応・未対応の分類
  effects.py     効果の登録表（ワザ: カード id・ワザの位置 → 実装、トレーナー: カード id → 実装）と、トレーナー 5 枚・みだれづき・でんげき・どくばり・いとをはく・キノコのほうし・あやしいひかり・れいとうビーム・かたまるの実装（v0.4c のスピアーのワザは既存の実装の登録）、ふきとばし（ワザの途中の相手の決定）・メガドレイン（v0.4d）の実装、ワザのダメージを与える処理（相手・自分。v0.2f。「ダメージを受けない」状態なら無効。v0.4b。結果 `DamageResult` を返す。v0.4d）。決定を出すトレーナーの決定の形の宣言（`decision_problems`。v0.4e）。ポケモンパワーの登録（カード id・パワーの位置 → 実装）とエナジートランス、やどりぎのタネ・どくのこな（コインなし）の実装（v0.5）。あまごい（手札から「水」エネルギーをつける）・ハイドロポンプ（多い「水」エネルギーでダメージを追加）の実装（v0.6）。ダメージスワップ・じこさいせい（v0.7）、かがくへんかガス・どくガス・ねばりつく（v0.8）、とうめい（ワザを受けるときに自動的にはたらく。ワザの要素の処理の境界の評価 `attack_reaches`）・あくむ・エナジーへんかん（v0.9）、はんげき（ダメージを受けたときに自動的にはたらく。判定は `deal_attack_damage`、与えるのは `finish_damage_elements`）・からてチョップ・じごくぐるま（v0.10）。v0.2a〜v0.10
  coins.py       コイントス（対戦の乱数で決め、1 枚ごとにログに残す）。v0.2d
  deck.py        デッキの検査
  state.py       ゲームの状態（ゾーン、場のポケモン、進化の重なり（v0.4a。v0.4c から 2 進化の 3 枚まで）・場に出た番・進化した番（v0.4a）、ワザによる持続する効果（v0.4b）、特殊状態（v0.3a〜v0.3c）、にげるの失敗の記録（v0.3c）、番、ポケモンパワーで手札からつけた枚数（v0.6）、結果）
  commands.py    プレイヤーの操作
  decisions.py   保留中の決定（出す・確かめる）。v0.2a
  engine.py      対戦の進行（new_game・apply_command）、きぜつ・サイド・勝ち負け・交代（同時のきぜつは v0.2f）、ポケモンチェック（v0.3a・v0.3b）、こんらんのワザ・にげるのコイン（v0.3c）、進化（v0.4a。2 進化は v0.4c）、不変条件（v0.4e でトレーナーの決定・サイドと交代の決定・番の番号を強めた。v0.6 でパワーでつけた枚数とログの対応）、あまごいのあとの通常の操作の停止（v0.6）
  damage.py      ワザのダメージ計算（p.321 の 8 段階。2・5〜8 段階の変更効果は v0.2c）、こんらんの 20 の計算（v0.3c）
  judge.py       勝ち負けの判定（p.311 の表）
  serialize.py   状態を辞書にする（形式 1〜9。9 は v0.6）
  zones.py       山札から引く・トレーナーをポケモンにつける・手札のエネルギーカードを場のポケモンにつける処理（エンジン・トレーナー・ポケモンパワーで共通）。v0.2b・v0.2c・v0.6
  rng.py         乱数の状態の指紋・保存・復元。v0.2a（コインも同じ乱数）
  data/kyuura_cards.json       kyuura のカードデータの写し（生成物）
  data/card_verification.json  『オフィシャルブック2000』との照合の記録
scripts/extract_kyuura_cards.py  kyuura から写しを作る
scripts/make_compat_fixture.py   v0.1 の対戦結果の参照データを作った道具（作り直さない）
tools/compat_driver.py           版の比較の駆動（公開の API だけで 1 つの版を動かし、1 手ごとの記録を作る）。v0.4e
tools/compare_engine_versions.py 2 つの版の比較（git archive で取り出し、版ごとに別のプロセス。最初の食い違いを診断）。v0.4e
tools/stress_engine.py           大規模なストレス実行（ふだんのテストでは走らせない）。v0.4e。v0.5 でフシギバナの組（エナジートランスの使用を混ぜる）、v0.6 でカメックスの組（あまごいの使用を混ぜる）、v0.7 でフーディンの組、v0.8 でベトベトンの組、v0.9 でゴーストの組、v0.10 でカイリキーの組
tests/                           自動テスト（unittest）。tests/log_audit.py はログと書き出しの監査の道具（v0.4e。v0.6 で手札・あまごいの組み立て直しと形式 9。v0.8 でかがくへんかガス、v0.9 で「とうめい」の判定とエナジーへんかん、v0.10 で「はんげき」。テストではない）
tests/fixtures/                  v0.1 の対戦結果の参照データ、v0.4d（4bd97bf）の記録の指紋（v0.4e。互換性のテスト用）
docs/                            ルールの仕様、実装状況、データの由来、v0.1 のレビュー、API のレビュー、v0.2a〜v0.6 のアーキテクチャ、トレーナー・コイントス・みだれづき・ディフェンダー・自分へのダメージ・同時のきぜつ・ピカチュウ・特殊状態・ポケモンチェック・ビードル・ねむり・マヒ・キャタピー・パラス・こんらん・ロコンの原典照合、特殊状態の総合検証・未解決の裁定・コインの前の検証（v0.3d）、進化の準備（v0.4）、進化のルール・カード・状態の持ち方（v0.4a）、持続する効果・かたまる・持続する効果とダメージ計算（v0.4b）、2 進化のルール・スピアー・3 枚の重なりの状態（v0.4c）、相手の強制交代・与えたダメージと回復・バタフリー（v0.4d）、総合監査・組み合わせの表・互換性・未解決の範囲・v0.5 の準備（v0.4e）、ポケモンパワーの規定・フシギバナ・フシギダネとフシギソウ・エナジートランスの処理・確かめた結果（v0.5）、あまごいの原典の照合と裁定・確かめた結果（v0.6）、ダメージスワップ・ケーシィの系統（v0.7）、かがくへんかガス・ベトベターの系統・常にはたらく効果の求め方（v0.8）、とうめいの原典の照合と裁定・ゴースの系統・自動的にはたらく特殊能力の仕組み・設計・確かめた結果（v0.9）、はんげきの原典の照合と裁定・ワンリキーの系統・ダメージを受けたあとに自動的にはたらく特殊能力の仕組み・設計・確かめた結果（v0.10）
```

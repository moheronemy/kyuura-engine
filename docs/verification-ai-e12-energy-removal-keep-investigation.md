# E12 の調査: エネルギー・リムーブで相手のうらについたエネルギーを選ぶと RuntimeError になる

2026-11-14。調査と文書化だけ。エンジン・judge・runner・方策・テストは変えていない。版 0.180.0。

関連: [P3 の設計](verification-ai-lost-target-p3-decision-design.md) 6.2 の E12（P3o の性質の記録。登録の対象外）。

## 1. 基点と保護

- 公開基点 `claude/lost-target-p3-design`（`1eed4d1`）から、調査ブランチ `claude/e12-energy-removal-keep-investigation` を作った。
- 停止中の P3s の作業は変えていない。
  - ブランチ `claude/lost-target-p3s-judge-rule8`。ローカルだけで、HEAD は `1eed4d1`。
  - 未追跡のテスト `tests/test_lost_target_p3_decision_v0_180.py` は、証跡の写しと SHA-256 が同じ。
- E7〜E11（P3s）が成功したことは別の事実として変わらない。

## 2. 現象

本人（プレイヤー 0）がエネルギー・リムーブを使い、相手のうらのカードについた基本エネルギーを決定で選ぶと、`apply_command` から `RuntimeError` が出る。

- 発生元は `effects.require_discard_not_voided` で、「［KEEP］でなくなるトラッシュの効果で…（確かめの漏れ。エンジンの不具合）」という文。
- うらの本当のカードがたねでも、たねでなくても同じになる。
- E12 が期待した `UnsupportedError(UNSUPPORTED_SECRET_PLAN_LOST_TARGET)` にはならない。

## 3. 盤面と入力の妥当性

テストの組み方の問題ではない。

- 盤面は `tests/test_secret_plan_v0_67.py` の部品（`build_test_state`）で作った構築盤面で、new_game からの対戦ではない。
- うらのカード、エネルギー、トレーナーの使用、決定への回答は、どれも `apply_command` の正規の入口を通した。
  - うらは、相手が自分の番にマチスの秘策で出した。
  - 基本エネルギーは、相手が自分の番に自分のうらへつけた（持ち主は相手）。基本エネルギーはつけたときの効果がないので、うらのまま残る。
  - トレーナーを使ったプレイヤー、決定のプレイヤー、答えたプレイヤーは同じ（プレイヤー 0）。
  - 選んだエネルギーは決定の選べるものにあり、本人の観測にも出る。
- 各段階で `check_invariants` は空で、uid は一意。
- new_game から到達するかは調べていない。

## 4. 最小再現と対照

| 場面 | 確かめること | 結果 |
| --- | --- | --- |
| R0（元の E12。たね・非たねの双子） | 元の現象 | どちらも内部の `RuntimeError` |
| R1（本当のカードが［KEEP］を持つたね） | 置きかえの試しを通らない本物の処理でも起こるか | 本物の 1 回目の処理で同じ `RuntimeError`。試しは 0 回 |
| C1（［KEEP］のカードがおもて） | 決定を出す時点の KEEP の確かめの通常の経路 | 選ぶと止める選択（KP1）として示し、答えると `UnsupportedError`（`UNRESOLVED_KEEP_PROTECTED_TARGET`）。通常の拒否 |
| C2（KEEP のないたねがおもて） | 受理の基準 | 受理してトラッシュ |
| C3（［KEEP］のカードがおもてで、別のうらにエネルギー） | うらのポケモンの KEEP を、決定の前にどう確かめるか | エネルギー・リムーブを使う時点で FD1（`HiddenPropertyRead`。`UnsupportedError` の下位）。決定は出ない |

- 元の E12 は、停止中のテストの写しを調査の作業ツリーで 1 回だけ実行した。結果は前回と同じ例外 2 つと、その結果の `IndexError`。
- 置きかえの試し（`_identity_independent`）の順は「割り当てなし」→ たね・ベイビィの代表 → 「たねでない」の代表（`_NONBASIC`）。
  - R0 では、たねの代表のうち［KEEP］（`VoidOpponentEnergyDiscardOnGroup`）を持つ 1 枚に来たところで例外になった。
  - それより前のたねの代表はすべて受理した。それより後と `_NONBASIC` は試していない。
- 試したカードと順序は、非公開の証跡だけに残した。公開のカードの一覧を独自に総当たりしてはいない。

## 5. 原因（確定）

有効な構築盤面で再現する、エンジンの不具合と判断した。

1. **決定を出す時点**: `DiscardAttachedEnergyTrainer._voided` は、相手のポケモンごとに `energy_discard_void` を呼ぶ。
   - 相手の場にはたらく［KEEP］がなければ、名前を読まずに「当たらない」とする。
   - うらのポケモンは特殊能力のない定義なので、うらにある［KEEP］のカードは数えられない。
   - そのため、選ぶと止める選択（KP1）にはならない。
2. **回答時**: `_designate_answer` が、エネルギーのついたうらのポケモンを効果の対象として指定し、おもてにする（たねなら場に残る）。
   - 本当のカードが［KEEP］を持つたねなら、ここで初めて［KEEP］がはたらき出す。
3. **トラッシュ**: `resume` の段階 3 は KEEP を確かめ直さずに `zones.discard_attached_energy_cards` を呼ぶ。
   - その中の `require_discard_not_voided` は「呼ぶ側が先に確かめる」前提の確かめなので、`RuntimeError` を出す。
4. **変換されない理由**: `_apply_checked` と `_identity_independent` が捕まえるのは、`IllegalActionError`・`UnsupportedError` と試しの内部の信号だけ。
   - `RuntimeError` は通常の拒否に変わらずに、そのまま外へ出る。
   - API（`ActionHost`）では送信が `failed`（`INTERNAL_ERROR`）になり、対戦は続けられない。

KEEP は仮説として調べ、R1（試しなし）と C1・C3（KEEP が見えている場合）で確かめた。

- 例外は、置きかえの試しのしくみではなく「指定でおもてにしたら KEEP がはたらき出す」場面を、エネルギー・リムーブの回答の処理が扱っていないことから起こる。
- 試しは、その場面を公開のカードの一覧から作るので、本当のカードによらず必ず通る。そのため、どの本当のカードでも同じ例外になる。

付随する記述のずれ:

- `energy_discard_void` の説明に「今の写しでは、うらのカードにエネルギーカードはつかない（つけるときにおもてにする）」とある。
- 基本エネルギーは、うらのままつく（3 章の手順で観測した）。

## 6. 無副作用と情報境界（確かめた範囲）

R0 の 2 つ、R1、C1、C2 で、例外や拒否の前後に次が同じだった。

- 呼び出し元の状態（`state_to_dict` と乱数の指紋）
- 相手と観戦者の `observe`・`visible_log`
- 決定（同じオブジェクト）と不変条件

一時状態の `zones.IDENTITY_CONSULTED`・`IDENTITY_ORACLE` は前後とも None で、`finally` で戻る。

例外より前の API の応答（状態の写しから作ったホスト。プレイヤー 0）:

- 候補は answer_decision 1 つで、`may_stop_later`（`continuation_not_evaluated`）。
- 選ぶものは `may_stop_later` で、検査は valid。
- 送信だけが `failed` になった。C1 は検査の段階で `CANDIDATE_NOT_EXECUTABLE` で断る（`refused`）。

API の配信（相手・観戦者への更新）は調べていない。エンジンを直接呼んだときの観測が変わらないことだけを確かめた。

## 7. 本来の結果と E12 の期待値

`RuntimeError` は想定外。

- 発生元の確かめが、自分で「確かめの漏れ。エンジンの不具合」と書いている。
- KEEP でなくなる効果は、呼ぶ側が先に止める約束になっている（KP1。`KEEP_TARGET_CODE`）。

E12 の期待値（どの本当のカードでも `UNSUPPORTED_SECRET_PLAN_LOST_TARGET`）が本来返るかは**未確定**で、直し方で変わる。

- **案 A**: おもてにして KEEP がはたらき出したら、今の KP1 と同じく `UnsupportedError(UNRESOLVED_KEEP_PROTECTED_TARGET)` で止める。
  - 試しの順で最初の拒否は［KEEP］のたねになるので、本当のカードによらず KP1 のコードになる（LOST_TARGET ではない）。
- **案 B**: おもてにしたあと効果がなくなる（トラッシュしない）として受理する。
  - 残りのたねの代表がどれも受理すれば `_NONBASIC` の LOST_TARGET になる。残りは今回試していない。
- どちらにするかは、［KEEP］で効果がなくなるカードを選んだときの扱いの問題で、既存の KP1（選べるかが記録から決まらない）と同じ論点。
  - この調査では裁定の記録を探していない。

## 8. 修正案（実装しない。別の単位）

**直す位置**: `DiscardAttachedEnergyTrainer.resume` の段階 3（相手のエネルギーをトラッシュする前）。

- `_designate_answer` のあとの今の場で `energy_discard_void` を確かめ、当たれば状態を変える前に止める。
- 案 A なら `UnsupportedError(KEEP_TARGET_CODE, KEEP_TARGET_REASON …)` で止める。理由の文に本当のカードを書かない。
  - `_apply_once` は複製の上で処理するので、呼び出し元の状態は変わらない。
- 超エネルギーリムーブは、段階 2 のポケモンの指定でおもてにしたあと段階 3 の決定を出す。
  - 段階 3 の決定を出す前（`resume` の段階 2）に同じ確かめが要る見込み。静的な読みだけで、実行していない。

**しないこと**: 根拠なしに次の案は取らない。

- `RuntimeError` を広く捕まえる。
- 無条件に未対応へ変える。
- ［KEEP］のカードを試しから除く（試しの一覧は公開の情報で決まり、除くと受け付けるかが本当のカードによる）。
- E12 を消す、xfail にする、KEEP の当たらない効果に替える。

**秘密によらない受理判定への影響**:

- 直せば、試しは［KEEP］のたねでも通常の例外で終わる。
- `_identity_independent` は最初の拒否のコードで、本当のカードによらず拒否する（案 A）か、受理の分岐を続ける（案 B）。

**回帰テスト**:

- 正: R0 の双子と R1（本当のカードが［KEEP］のたね）が、同じ通常の拒否（案 A なら同じコード・同じ文）になる。
  - あわせて、状態・乱数・公開・決定・一時状態が変わらない。
- 負:
  - C1（おもての KEEP は今までどおり KP1）
  - C2（KEEP なしは受理）
  - C3（使う時点の FD1）
  - 本人のうら（P3s の E7〜E11）が変わらない
- 超エネルギーリムーブの段階 2 からの同じ場面。

**版・識別・配布**:

- `effects.py` のエンジンの処理を変えるので、`behavior_digest` が変わる。版を上げる（0.181.0 など）。
- 検証用 AI の P1・P3 の basis（`effects.py`・`engine.py` をふくむ）の値も変わる。
- 判定の規則と道具の版は、エンジンの修正とは別に扱う。

**その他**: `energy_discard_void` の説明のずれ（5 章）を同じ単位で直す。

## 9. P3s への影響

- P3s（本人のうら。ディフェンダーの `select_pokemon`）は、相手のうらを指定しない。E7〜E11 の成功と、規則 8 の条件 D1〜D12 は、この不具合の影響を受けない。
  - D9 は本人のうらに限る。
  - 決定の選べるものは本人の場に限る。
- 影響は E12（P3o の性質の記録）だけ。
- P3s の根拠登録は、E12 をこの調査の結論（不具合の候補・期待値は未確定）に合わせて扱えば進められる。
  - その扱い方は、P3s の実装の単位で決める。
  - E12 の削除・xfail 化や KEEP を避ける効果への差し替えで、解決扱いにはしない。

## 10. 未確認

- new_game からの到達
- 超エネルギーリムーブの段階 2 → 3 の実行
- 特殊能力・スタジアムの回答の経路（`_designate_answer` を通るほかの再開先）で、相手のエネルギーをトラッシュする効果があるか
- ワザの経路（`resolution` の `designate` のあとの `energy_discard_void`）は静的にだけ読み、実行していない
- 試しの残り（［KEEP］のたねより後のたねの代表と `_NONBASIC`）
- API の配信
- KEEP と指定の裁定の記録

## 11. 証跡

- 非公開: `kyuura-engine-verification-vai/verifier/runs/e12-energy-removal-keep-investigation/`
  - 事前計画、出典とハッシュ、再現と対照のスクリプト・出力、試しの記録、識別（前後同じ）、コマンドと終了コード、結果のまとめ。
- 公開: `public/runs/e12-energy-removal-keep-investigation/summary.json`（件数と分類だけ）。

## 12. 修正の結果（2026-11-14 の追記）

- 0.181.0 で、7 章の案 A（KP1 と同じ通常の拒否）・8 章の位置で直した。詳細は [v0.181 の修正](keep-designated-energy-removal-v0.181.md)。
- E12 の場面は、どの本当のカードでも `UNRESOLVED_KEEP_PROTECTED_TARGET` になる（LOST_TARGET ではない）。
- 超エネルギーリムーブの段階 2 も同じ前提の漏れがあったので、同じ単位で直した。

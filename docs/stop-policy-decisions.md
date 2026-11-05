# 停止の方針: 利用者が決める事項

[分類](stop-policy-classification.md)と[台帳](stop-policy-classification.json)の `decision_refs` から引く判断事項の一覧です。

- 推奨は**案**です。どれも承認されていません（状態は `decision_required`）。例外は、2026-11-03 に利用者と合意したモードの定義の 6 項目（台帳の `mode_agreements`。
  [ruleset-mode-design.md](ruleset-mode-design.md) 2 章）で、これにより DEC-STRICT-DEFINITION は合意済み、DEC-EXISTING-USER-SPECS は利用者指定の部分だけ合意済みになりました（台帳の
  `decision_status`）。合意の根拠は本会話の利用者の指示で、公式の裁定・kyuura の研究上の解決ではありません。
- 推奨を書いても、規約を採ったことにはなりません。挙動も変えていません。個々の続行規約（切り直しの補償・両側ねむり・錯乱ジムとちえくらべなど）は、どれも決めていません。
- モードと規約集合の構造の判断事項（規約集合の識別・採用の単位・途中の変更・旧保存状態など）は [ruleset-mode-decisions.md](ruleset-mode-decisions.md) に移しました。この文書には、分類の時点の
  案を「移した判断事項（履歴）」として残します（1.1 節）。台帳の `decision_status.<ID>.document` が、それぞれの判断事項の置き場所です。
- 影響に書く件数は台帳の集計（基点 `3e25ac5`）です。

## 優先して決めるもの

| 順 | 判断事項 | 理由 |
|---:|---|---|
| 1 | DEC-INFO-LEAK-FIXES | モードによらない漏れ。v0.137・v0.138 で 4 件を修正。PSP-INCREASE-ENTRY-PW3-ORACLE・PSP-COCOON-DV2-ORACLE（未修正）と PSP-DECK-CONTENT-PRECHECKS の残り（未確認）が残る |
| 2 | DEC-STRICT-DEFINITION | **合意済み**（2026-11-03。AGR-MODE-STRICT・AGR-MODE-PLAY・AGR-MODE-BASELINE-USER） |
| 3 | DEC-RULESET-IDENTITY | 保存・比較・監査の前提（[ruleset-mode-decisions.md](ruleset-mode-decisions.md) に移した） |
| 4 | DEC-MULLIGAN-COMPENSATION | 通常の固定デッキで準備が HALTED（道具の対戦で観測）。AGR-MODE-PRIORITY の対戦全体を終端にする項目 |
| 5 | DEC-SLEEP-COIN-ORDER | ポケモンチェックで HALTED（道具の対戦で観測）。同上 |
| 6 | DEC-CHAOS-GYM-MIND-GAMES | v0.132 の正式な対戦で拒否を観測 |
| 7 | DEC-EXISTING-USER-SPECS | 利用者指定の部分は合意済み。残り（簡略化・仮定・データの訂正）は DEC-BASELINE-NONUSER・DEC-CARD-DATA-CORRECTIONS（[ruleset-mode-decisions.md](ruleset-mode-decisions.md)） |

順の 4〜6 の続行規約は、合意（AGR-MODE-PRIORITY）で優先の順を決めただけで、どの規約を採るかは決めていません。

## 1. モードと規約の集合

### DEC-STRICT-DEFINITION — 「厳密モード」の意味

- **問い**: 厳密モードを STRICT-A（公式の根拠だけ。ほかで決めている処理も止める）と STRICT-B（承認済みの利用者指定を含む、版で固定したルールセットに厳密にしたがう）のどちらにするか。
- **選択肢**:
  - **STRICT-A**: 利用者指定・簡略化・仮定・データの修正の 18 件が、止める候補になる。
  - **STRICT-B**: 今の挙動のまま。
  - **両方を持つ**: 集合の ID で区別する。
- **推奨（案）**: 両方を、規約の集合の 2 つの定義として持つ（DEC-RULESET-IDENTITY）。既定は STRICT-B（今の挙動）にする。STRICT-A は研究・照合の用途として、既存の規約に当たったら止める。
- **影響**:
  - STRICT-A にすると、次の処理で新しい停止が要る。誕生日・発話の省略（PR1-044・PR1-072・PR1-090）、公式図鑑の参照（GD5-016）、交換の所有権（PR1-027）、ちえくらべ（neo1-049）、
    ひかるバンギラスの 2 ワザ（neo4-082）、ナッシーの名前（PR1-075・PR1-077）、サドン・デスの所有者の戻し、キョウのベトベトン（PMCG6-074）、実装上の仮定 3 件、PR1-069 の名前。
  - エネルギードレインの v0.68 の仕様は 2002 年の Q&A が根拠で、2000.02.14 版の裁定ではない。そのため、STRICT-A では止める候補に入る。
- **依存**: なし。DEC-EXISTING-USER-SPECS・DEC-RULESET-IDENTITY がこれに依存する。
- **訂正（2026-11-03）**: 上の「影響」の「キョウのベトベトン（PMCG6-074）」は誤りで、キョウのベトベトンは PMCG6-023 です（PMCG6-074 はイマクニ？のドードー。エンジンの簡略化の記録）。
  分類の時点の文はそのまま残し、ここで訂正します。
- **経過（2026-11-03。合意済み）**: 利用者と次を合意しました（台帳の `mode_agreements`。根拠は本会話の利用者の指示で、公式の裁定・kyuura の研究上の解決ではない）。
  - 同じ処理基盤に、採用する規約集合を渡す（AGR-MODE-SHARED-ENGINE）。
  - 厳密モードは、未決の裁定に当たったら停止する検証用モード（AGR-MODE-STRICT）。
  - プレイ用モードは、未決の裁定を事前に定めた続行規約で処理し、実際の対戦を進めるモード（AGR-MODE-PLAY）。
  - 既存の承認済み利用者指定は、両モードに共通する基礎集合に含める（AGR-MODE-BASELINE-USER）。
  - 情報漏れ・状態破損・不正入力・実装不足・計算上限は、プレイ用だから無視してよいものではない（AGR-MODE-SAFETY）。
  - 続行規約の整備は、対戦全体を終端にする項目から優先する（AGR-MODE-PRIORITY）。

  **STRICT-A（公式の根拠だけ）は、厳密モードの定義としては採用しません**（過去の検討案として残す）。STRICT-B は合意済みの定義に置きかえました。STRICT-B が含めていたエンジンの
  簡略化・実装上の仮定を基礎集合に入れるかは未決です（DEC-BASELINE-NONUSER）。上の「推奨（案）」「影響」は分類の時点の記録として残します。

### 1.1 移した判断事項（履歴）

次の 5 つの判断事項は [ruleset-mode-decisions.md](ruleset-mode-decisions.md) に移しました（置き場所は 1 つ。台帳の `decision_status`）。この節の下の 4 段の見出し（`####`）は、分類の時点
（基点 `3e25ac5`）の案の記録で、今の推奨ではありません。

- DEC-RULESET-IDENTITY・DEC-EXISTING-USER-SPECS・DEC-CONVENTION-GRANULARITY・DEC-MODE-CHANGE-DURING-GAME・DEC-LEGACY-STATES

#### DEC-RULESET-IDENTITY — 規約の集合の識別

- **問い**: モード名と別に、採る規約の集合をどう識別するか（ID・版・中身の列挙）。
- **選択肢**:
  - **モード名だけ**: 採らない案。巨大な分岐になる。
  - **集合の ID と版**: 例 `kyuura-2000-02-14+user@N`・`…+play@M`。
  - **規約の ID の列挙を保存に持つ**。
- **推奨（案）**: 集合の ID と版を持ち、保存には中身の列挙も持つ。読むときに、ID と列挙が合うかを確かめる。
- **影響**: 書き出しの形式を上げる（保存形式の変更は別の版の作業）。lockstep・前の版の組の比べは、同じ集合どうしでだけ比べる。
- **依存**: DEC-STRICT-DEFINITION。

#### DEC-EXISTING-USER-SPECS — 既存の利用者指定の扱い

- **問い**: 採用済みの 18 件（台帳の `conventions`）を、各モードでどう扱うか。
- **選択肢**:
  - **すべて STRICT-B の集合に入れる**。
  - **一部を STRICT-A でも許す**: 例えば名前の指定（分類の時点は「表示だけの指定」と書いたが誤り。判定に影響する。下の訂正）。
  - **すべて STRICT-A では止める**。
- **推奨（案）**: STRICT-B の集合にすべて入れる。STRICT-A では、挙動に影響する指定は止める。名前の指定（ナッシーの日英併記の名前・PR1-069 の名前。分類の時点は「表示だけの指定」と書いた）は、別に判断する。
- **訂正（2026-11-03）**: 分類の時点の「表示だけの指定」は誤りです。ナッシー［Exeggutor］（PR1-075・PR1-077）の名前の扱いは、デッキの同じ名前 4 枚の数え方・進化元（タマタマ）・名前を指定する効果・
  同じ名前を比べる効果・カツラのクイズの答え・変身したあとの名前・ワザ名に使います（`effects.USER_SPECIFIED_NAMES` の `applies_to`。docs/exeggutor-bilingual-names-v0.131.md 3 章）。
  PR1-069 の名前（ミュウ）も、同じ名前の数え方と名前を指定する効果に使うデータの訂正です。どちらも表示だけではありません。台帳の `conventions` の `affects`・`display_only: false` に記録しました。
- **影響**:
  - 公式の論点（UQ-SWAP-PLEASE-OWNERSHIP など）は、どちらでも解決済みにしない。
  - ひかるバンギラスの指定をほかのカードへ広げない。
- **依存**: DEC-STRICT-DEFINITION。

#### DEC-CONVENTION-GRANULARITY — プレイ用の規約を採る単位

- **問い**: プレイ用の規約を、コード単位・族単位・カード単位のどれで採るか。
- **選択肢**:
  - **コード単位**。
  - **族単位**: 一括で同じ規則を当てはめる。
  - **カード単位**。
- **推奨（案）**: コード単位（記録は族ごとの書式で揃える）。同じ言い回しの別のカードの問いは、kyuura・エンジンの記録で別の問いとして扱っているので、一括にしない。
- **影響**: 判断の数が多くなる（族 23・研究コード 316）。頻度の高いものから順に決める。
- **依存**: DEC-RULESET-IDENTITY。

#### DEC-MODE-CHANGE-DURING-GAME — 対戦の途中の変更

- **問い**: 対戦の途中で規約の集合を変えられるか。
- **選択肢**: 変えられない／止まった状態からだけ変えられる／いつでも変えられる。
- **推奨（案）**: 変えられない（開始時に固定）。
  - HALTED になった対戦を別の集合で続けたい場合は、新しい対戦として、その状態から始める明示の操作（監査の記録付き）を別に設計する。
  - サドン・デスの延長戦は、同じ集合を引き継ぐ。
- **影響**: 途中で変えると、乱数の列・ログの意味が区間の途中で変わり、再生・比較ができなくなる。
- **依存**: DEC-RULESET-IDENTITY。

#### DEC-LEGACY-STATES — 方針の情報がない旧保存状態

- **問い**: 規約の集合の情報がない旧保存状態を、どう読むか。
- **選択肢**: その版の挙動（STRICT-B 相当）として読む／読むのを拒否する／読む人が指定する。
- **推奨（案）**: その版の採用済みの集合（STRICT-B 相当）として読み、読み込んだ記録に「推定した」ことを残す。ほかの集合を推測で当てはめない。
- **影響**: 旧形式の読み込みのテスト（形式 1〜34）。
- **依存**: DEC-RULESET-IDENTITY。

## 2. 両モード共通の不具合

### DEC-INFO-LEAK-FIXES — 新しく見つけた漏れ

- **問い**: `PSP-ST1-DECK-ORACLE`（エネルギー転送など）・`PSP-FC1-ENERGY-ARK-ORACLE`（エネルギーアーク）の漏れを直すか。`PSP-DECK-CONTENT-PRECHECKS`（静的な候補）を比較プローブで確かめるか。
- **選択肢**:
  - **公開の情報だけで止める**: v0.135・v0.136 と同じ型。たとえば、デッキリストから見て山札とサイドのどちらかにありうるなら、使う前には止めない。止めるなら、公開の情報だけで決まる条件で止める。
  - **使えて、探して見つからない処理にする**: PF-USE-WITHOUT-EFFECT の P-UWE-2。規約の判断が要る。
  - **今の拒否のまま、漏れとして記録する**。
- **推奨（案）**: 次の版で、公開の情報だけで決める止め方に直す。研究の答えを作らず、保守的な制限として記録する。候補の 2 経路は、同じ版で比較プローブを作ってから判断する。
- **影響**: 止める場面が増える（保守的）か、使える場面が増える（P-UWE-2）。どちらも秘密への非依存（SB-SECRET-INDEPENDENCE）を対のテストで確かめる。
- **依存**: P-UWE-2 を採るなら DEC-USE-WITHOUT-EFFECT。
- **経過（v0.137。2026-11-02）**: 利用者は「情報漏れ 2 件を先に修正すること」を承認し、v0.137 で `PSP-ST1-DECK-ORACLE`・`PSP-FC1-ENERGY-ARK-ORACLE` を直しました（[deck-search-oracle-v0.137.md](deck-search-oracle-v0.137.md)）。
  止め方は上の選択肢の「公開の情報だけで止める」そのものではなく、持ち主が知っている見えない自分のカードの集合と公開の枚数から求めた下限で止める形です（公開の情報だけでは実際にほぼ
  使えなくなるため。受理が相手に伝える内容が変わる点を版の文書 4.4 節に記録）。P-UWE-2（使えて見つからない）・P-SCS（あるだけ）は採っていません。この承認は、厳密モードの定義・
  不足時の規約・プレイ用の規約・既存の利用者指定の扱いの承認ではありません（DEC-STRICT-DEFINITION・DEC-USE-WITHOUT-EFFECT・DEC-STATED-COUNT-SHORT ほかは未決のまま）。
  `PSP-DECK-CONTENT-PRECHECKS` の残り（キョウのコクーン）と、v0.137 で見つけた `PSP-RUIN-WALL-BLOCKED-REASON-ORACLE`・`PSP-UPZ2-ENERGY-AMPLIFIER-ORACLE` の扱いは未決です。
- **経過（v0.138。2026-11-03）**: 利用者は「v0.137 で新たに見つかった 2 件の情報漏れを、モード共通の不具合として修正すること」を承認し、v0.138 で `PSP-RUIN-WALL-BLOCKED-REASON-ORACLE`・
  `PSP-UPZ2-ENERGY-AMPLIFIER-ORACLE` を直しました（[oracle-leak-fixes-v0.138.md](oracle-leak-fixes-v0.138.md)）。止め方は v0.137 と同じ型（持ち主が知っている見えない自分のカードの集合と
  公開の枚数から求めた下限）で、既存のコード（GG1・MG1・DW1・UPZ2）のまま決まった文で止めます。この承認は、厳密モードの定義・プレイ用の規約・検索の不足時の処理の承認ではありません。
  比較プローブで見つけた `PSP-INCREASE-ENTRY-PW3-ORACLE`・`PSP-COCOON-DV2-ORACLE` と、`PSP-DECK-CONTENT-PRECHECKS` の残り（GV1・EVOLUTION_HP の経路）の扱いは未決です。

- **材料（2026-11-04。判断はしていない）**: 共通規約の設計案（[play-policy-family-plan.md](play-policy-family-plan.md) 7 章）の調査で、キョウの忍者ジム（PR1-067）の
  使う前の確かめ（NJ1）が、山札の実際の中身で受理・拒否を変える漏れ `PSP-NJ1-NINJA-GYM-ORACLE` を、比較プローブで確かめました（未修正）。
- **経過（v0.146。[play-set-verification-v0.146.md](play-set-verification-v0.146.md) 3 章）**: 利用者の指示で `PSP-NJ1-NINJA-GYM-ORACLE` を直しました（v0.137 の ST1 と同じ配分を読まない下限。コードは NJ1 のまま、決まった文で止める）。`PSP-INCREASE-ENTRY-PW3-ORACLE`・`PSP-COCOON-DV2-ORACLE`・`PSP-DECK-CONTENT-PRECHECKS` の残りは直していません。この判断事項の状態は変えていません。

### DEC-SEARCH-LIMITS — 探索・組合せの上限

- **問い**: 4096・512・256・6・3 の上限と、256 件の代替回答探索の fail-open の 3 経路を、どう扱うか。
- **選択肢**: 上限を増やす／同値類・相関で計算を減らす／今の拒否・HALTED のまま。fail-open の経路は、再現と安全性の確認が先。
- **推奨（案）**: 両モード共通で、計算の改善（棚卸しの R3・R4・R9）を別の作業にする。プレイ用モードでも、枝を黙って削る・未探索を安全とみなす方法は採らない。上限を増やすかは、計測のあとで別に判断する。
- **影響**: 対応群 4 のコード 6 件と、`LIMIT:*` 7 件。
- **依存**: なし。

## 3. 対戦を止める項目

### DEC-MULLIGAN-COMPENSATION — 準備の切り直しの補償

- **問い**: 両者が切り直したあと、片方だけが追加で切り直したときの補償（`UNRESOLVED_MULLIGAN_COMPENSATION`）。準備の HALTED は、最初の対戦と延長戦の区間の両方で起こる。
- **選択肢**:
  - **補償を数える単位を固定する**: 相手の切り直しの総数か、両者の差か。
  - **引く時点を固定する**: 最初のポケモンを置く前か後か。
  - **今のまま**: 準備で止める。
- **推奨（案）**: p.308 の記録と kyuura の論点を確かめ直す。決まらなければ、プレイ用の規約として、先攻・後攻（ジャンケン）で偏らない数え方を 1 つ採る。厳密モードは今のまま止める。
- **影響**: 道具の対戦（v0.126・v0.130・v0.133 の組、開発用の種）で準備の HALTED を観測した。規約を採れば、これらの対戦は始められるようになる。乱数（引く枚数）が変わる。
- **依存**: DEC-STRICT-DEFINITION（研究の答えがない場合）。

### DEC-PLAY-AS-POKEMON — なにかの化石・ピッピ人形

- **問い**: 準備で出せるか（PF1。準備の HALTED）、にげる（PF2）、育て屋（PF3）、ちえくらべ（MG2）。
- **選択肢**: コードごとに、できる／できないを固定する。今のままにする。
- **推奨（案）**: PF1（準備で止まる）を先に判断する。PF2 は道具の対戦で拒否が多いので、次に判断する。
- **影響**: 最初のポケモンの選択肢・にげるの可否。
- **依存**: DEC-CONVENTION-GRANULARITY。

### DEC-SLEEP-COIN-ORDER — 両側ねむりのコインの順番

- **問い**: ポケモンチェックで両方の対戦ポケモンがねむりのとき、どちらが先にコインを投げるか（`UNRESOLVED_POKEMON_CHECK_SLEEP_COIN_ORDER`。HALTED）。
- **選択肢**:
  - **番のプレイヤーの側から**: その番のプレイヤーを基準にする。
  - **番でないプレイヤーの側から**。
  - **順番によらない形**: 結果の組が同じなら続ける。2 枚のコインで割り当てが変わるので、この場面では使えない可能性が高い。
  - **今のまま**。
- **推奨（案）**: プレイ用の規約として「番のプレイヤーの側から」を候補にする。ただし先攻・後攻の偏りを、道具の対戦で測ってから採る。席（プレイヤー 0・1）で決める規則は採らない。
- **影響**: v0.80 の組で HALTED を観測した。乱数の割り当て（どちらのコインがどの値か）が決まる。
- **依存**: DEC-ORDER-RULE。

### DEC-CHAOS-GYM-MIND-GAMES — 錯乱ジムとちえくらべ

- **問い**: 錯乱ジムのコインと、ちえくらべの反応の順番（`UNRESOLVED_MIND_GAMES_CHAOS_GYM_ORDER`。MG1）。
- **選択肢**: 錯乱ジムのコインが先／ちえくらべが先／今のまま。
- **推奨（案）**: USER-MIND-GAMES-OPTIONAL-BEFORE-COST（v0.132）の範囲を確かめ、その指定の延長として扱えるかを先に判断する。扱えなければ、別のプレイ用の規約にする。
- **影響**: v0.132 の正式な対戦 2 局の拒否（基点・現在で同じ）。
- **依存**: DEC-EXISTING-USER-SPECS。

### DEC-DEFERRED-RESUME — 途中停止の再開

- **問い**: DU1・TW1 の途中停止（コインのあとの終端）を、規約・裁定の入力で再開する操作を設けるか。
- **選択肢**: 再開の操作を設ける（規約の集合に入っていれば、その規約で続ける）／途中停止のまま。
- **推奨（案）**: 規約（DEC-STATED-COUNT-SHORT）を採るなら、途中停止にせず最初からその規約で処理する。再開の操作は、旧保存状態の途中停止を続けるときだけの別の設計にする。どちらも、拒否と処理済みの途中停止を混同しない。
- **影響**: 再開の操作は保存形式・ログ・監査の変更を伴う。
- **依存**: DEC-STATED-COUNT-SHORT・DEC-RULESET-IDENTITY。

## 4. 族ごとの規約（コード単位で決める）

各族の候補の具体的な対象・時点・範囲・結果の違い・安全条件は、台帳の `families.<族>.play_candidates` にあります。

| 判断事項 | 族（コード数） | 選択肢（台帳の候補 ID） | 推奨（案） | 主な危険 |
|---|---|---|---|---|
| DEC-USE-WITHOUT-EFFECT | PF-USE-WITHOUT-EFFECT（57） | P-UWE-1 使えない・P-UWE-2 使えて何もしない | コードごと。非公開の領域に依存するコードは P-UWE-1 にしない | 漏れが残る（DEC-INFO-LEAK-FIXES） |
| DEC-UP-TO-ZERO | PF-UP-TO-ZERO（13） | P-UTZ-1 0 は選べない・P-UTZ-2 0 を選べる | コードごと。P-UTZ-1 は規約として明示する | 選択肢の黙った削除 |
| DEC-STATED-COUNT-SHORT | PF-STATED-COUNT-SHORT（11） | P-SCS-1 あるだけ・P-SCS-2 使えない | コードごと。ひかるバンギラスの指定を広げない。数が秘密で決まる場面は P-SCS-2 にしない | 漏れ・途中停止との混同 |
| DEC-ORDER-RULE | PF-SIMULTANEOUS-ORDER（26） | P-SO-1 固定・P-SO-2 選ばせる・P-SO-3 同じなら続ける | 席で決めない。偏りを測ってから | 先攻・後攻の偏り・乱数の割り当て |
| DEC-KNOCKOUT-READINGS | PF-KNOCKOUT-TIMING（15） | P-KO-1 読み方の固定 | 勝敗が変わるので、道具の対戦で差を測ってから | 勝敗・サドン・デスへの移り方 |
| DEC-TIMING-READINGS | PF-EFFECT-TIMING（13） | P-ET-1 時点の固定 | コードごと | ほかの効果の前提を変える |
| DEC-NULLIFIED-COINS | PF-PROTECTED-TARGET-EFFECT（12） | P-PT-1 投げない・P-PT-2 投げる | どちらでも乱数の列がずれるので、集合の ID で比べ分ける | 乱数 |
| DEC-DAMAGE-READINGS | PF-DAMAGE-SCOPE（22） | P-DS-1 当てはめる・当てはめない | 頻度の高いこんらんのダメージ（CONFUSION_DAMAGE_MODIFIERS）から | 広い影響 |
| DEC-ENERGY-READINGS | PF-ENERGY-TYPE（21） | P-EN-1 読み方の固定 | コードごと | 色の読み方の上限 |
| DEC-COPY-SCOPE | PF-COPY-TRANSFORM（34） | P-CT-1 読み方＋実装 | 実装の不足（PF-RUNTIME-COPY-GAPS）を先に | 規約だけでは止まる |
| DEC-LASTING-READINGS | PF-HISTORY-LASTING（20） | P-HL-1 続く・終わる | コードごと | 旧状態の記録の不足 |
| DEC-TEXT-READINGS | PF-TEXT-READING（34） | P-TR-1 読み方の固定 | 後年の裁定・英語版を根拠にしない（規約として記録） | 別のカードへの拡大 |
| DEC-REACTION-READINGS | PF-REACTION-DURING-PROCESS（10） | P-RD-1 使える・使えない＋継続の実装 | 継続の実装（R6）と組にする | 反応を黙って飛ばす |
| DEC-SUPPRESSION-READINGS | PF-POWER-SUPPRESSION（11） | P-PS-1 及ぶ・及ばない | 循環を席で切らない | 偏り |
| DEC-FACE-UP-DECK | PF-HIDDEN-INFORMATION（8） | P-HI-1 読み方の固定 | 決めたあと、v0.135・v0.136 の保守的な止め方を外す前に、対のテストで確かめ直す | 塞いだ漏れが戻る |
| DEC-ESP-READINGS | PF-ESP-REDO（4） | P-ESP-1 やり直せる・やり直せない | コードごと | 結果の分布 |

## 5. 決めないで残すもの

- 実装の不足（PF-RUNTIME-COPY-GAPS・PF-RUNTIME-CONTINUATION）・データの不足（PF-RUNTIME-DATA）・登録のガード（PF-RUNTIME-REGISTRY）は、判断事項ではありません。両モードで拒否のまま、別の作業単位で実装します。
- 汎用の `UNRESOLVED_RULING` は、発生した経路の個別のコードを確かめるまで、方針を検討しません（未検討）。
- 内部ガード（602 箇所）は判断事項ではありません。合法な操作の列で起きたら不具合として扱います。

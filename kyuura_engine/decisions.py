"""保留中の決定（v0.2a、レビューの M4）。

処理の途中でプレイヤーの選択が要るとき、エンジンは決定（``state.PendingDecision``）を出して止まり、
選択を受け取ったら、決定に書いた再開先（``resume``）から処理を続けます。

- 決定は一度に 1 つだけです（``GameState.decision``）。決定を待っている間は、その決定に答える
  コマンドしか受け付けません。
- 1 つの処理が何回も選択を求めるときは、再開した処理が次の決定を出します（複数段階の決定）。
  続きに必要な情報は、決定の ``context`` に入れます（読み取り専用・JSON にできる値）。
- 再開先は関数ではなく名前（文字列）で持ちます。状態を pickle・JSON にしても再開先が失われない
  ようにするためです。

再開先の名前:

- ``"take_prize"``・``"promote_active"``: エンジンの中のきぜつのあとの処理（``engine`` が持つ）
- ``"attack"``: ワザの効果の続き。``context`` の ``"use"`` から、効果の登録表の実装を引き、
  その ``resume`` を呼ぶ（``effects.AttackEffect.resume``）。決定するのは、ふつうはワザを使ったプレイヤー。v0.4d から、
  ワザを使われた側のプレイヤーが決定する種類（``FORCED_SWITCH``）がある。どちらの場合も番のプレイヤー
  （``GameState.current_player``）はワザを使ったプレイヤーのまま。ワザの実装は、自分が出す決定の形を
  ``AttackEffect.decision_problems`` で宣言し、不変条件（``engine._decision_problems``）が確かめる
- ``"trainer"``: トレーナーの効果の続き（v0.2b）。``context`` の ``"use"`` から実装を引き、
  ``effects.TrainerEffect.resume`` を呼ぶ。決定がなくなったら、エンジンがカードをトラッシュする
- ``"knock_out"``: ワザのあとのきぜつの判定の続き（v0.11）。相手のワザによるダメージで「きぜつ」するときに使える特殊能力
  （サカキのカイリキーの「こんじょう」）を使うかを、そのポケモンの持ち主が決める（``KO_PREVENTION``）。選んだら宣言・コイン・
  残り HP、選ばなければ何もせず、そのあと、まだ HP 以上のポケモンをきぜつさせる（``engine._resume_knock_out``）。番のプレイヤーは
  ワザを使ったプレイヤーのまま。``context`` は ``"attack"``（ワザ）と ``"power"``（特殊能力）。v0.12 から、番のプレイヤーのワザを使った
  ポケモンが、相手の「ほのおのかべ」（相手のワザによるダメージ）で「きぜつ」するときにも出す（決定するのは番のプレイヤー）
- ``"power"``: 宣言して使う特殊能力の処理の続き（v0.42。docs/power-decisions-v0.42.md）。``context`` の ``"use"``（(プレイヤー, 場のポケモンの番号,
  カード id, 特殊能力の位置)）から実装を引き、``effects.PowerEffect.resume`` を呼ぶ。決定がなくなったら、エンジンが特殊能力の処理のあとの場を整え
  （きぜつ・空いたバトル場。``resolution.after_power``）、番のプレイヤーの番にもどる（番は終わらない）。決定するのは特殊能力を使ったプレイヤー。
  v0.43: 場に出たときに使う特殊能力の使う機会（``ENTRY_POWER``）も再開先 ``"power"``。トレーナーの効果の途中で場に出たら、``context`` の ``"return_to"``
  で、特殊能力の処理のあとにそのトレーナーの処理（トラッシュ）にもどる
- ``"post_knockout"``: きぜつの処理（トラッシュ・サイド・勝ち負けの判定）のあとの続き（v0.12）。ポケモンが「きぜつ」したときに使える
  特殊能力（R団のファイヤーの「ふしちょう」）を使うかを、そのカードの持ち主が決める（``POST_KNOCKOUT_POWER``）。選んだら宣言して、
  そのカードをトラッシュから手札に加え、選ばなければ何もせず、そのあとバトル場にポケモンを出す（``engine._resume_post_knockout``）。
  ``context`` は ``"power"``（特殊能力）と、ポケモンチェックの中のきぜつなら ``"then"``

選べるもののうち、原典で処理を決められないもの（v0.2b）: カードの文面では選べるが、選んだときの扱いを
原典で決められないものは、``context`` の ``"unresolved_choices"`` に入れる。それを選ぶと、状態を変えずに
``UnsupportedError``（``"unresolved_code"``・``"unresolved_reason"``）になる。推測で処理しないため。
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Iterable

from .errors import IllegalActionError, UnsupportedError
from .state import PendingDecision, Phase

if TYPE_CHECKING:
    from .effects import AttackUse, TrainerUse
    from .state import GameState

# 決定の種類（kind）。v0.1 からある 2 つは、段階（phase）も v0.1 と同じものを使う
TAKE_PRIZE = "take_prize"  # きぜつさせたプレイヤーが、サイドの位置を 1 つ選ぶ（p.312, p.323）
PROMOTE_ACTIVE = "promote_active"  # バトル場のポケモンがいなくなったプレイヤーが、ベンチのポケモンを 1 匹選ぶ（p.313, p.323）
SELECT_POKEMON = "select_pokemon"  # 効果の対象の場のポケモンを選ぶ（v0.2b。選べるものは場のポケモンの番号）
# ワザの効果で相手の対戦ポケモンをベンチにもどすとき、入れ替わる控えポケモンを、入れ替えられるプレイヤー（ワザを使った
# プレイヤーの相手）が選ぶ（v0.4d。バタフリーの「ふきとばし」。p.19 の最新の説明「入れ替わるポケモンは、相手が選ぶ。」・
# p.213 のワザ解説。選べるものは相手のベンチのポケモンの番号。段階は Phase.DECISION）
FORCED_SWITCH = "forced_switch"
# ワザの効果で、ワザを使うポケモン自身についているエネルギーカードを 1 枚トラッシュするとき、どのカードかを、ワザを使った
# プレイヤーが選ぶ（v0.7。ユンゲラーの「じこさいせい」。p.151 の最新の説明「自分についている「超」エネルギーカードを1枚
# トラッシュして…」。選べるものはカードの uid（ついている順）。段階は Phase.DECISION）
DISCARD_ENERGY = "discard_energy"
# ワザの効果で、自分のトラッシュのエネルギーカードを手札に加えるとき、どのカードを何枚加えるかを、ワザを使ったプレイヤーが選ぶ
# （v0.9。化石の秘密のゴースの「エナジーへんかん」。p.158 の最新の説明「自分のトラッシュから、「エネルギーカード」を最大2枚
# 選び出し、手札に加える。」。選べるものはカードの uid（トラッシュの順）。0 枚を選ぶと原典で決められないので止める。段階は Phase.DECISION）
RECOVER_ENERGY = "recover_energy"
# ワザのあとのきぜつの判定で、相手のワザによるダメージで「きぜつ」するときに使える特殊能力（v0.11。サカキのカイリキーの「こんじょう」。
# p.193 の最新の説明「この力は、相手のワザによるダメージで、このカードが「きぜつ」するとき、使える。」）を使うかを、そのポケモンの持ち主
# （ワザを使われた側のプレイヤー）が決める。選べるものはそのポケモンの番号 1 つで、0 個（使わない。p.311「かならずしも特殊能力の使用を
# 宣言する必要はありません」）か 1 個（使用を宣言する）。コインはこの決定のあと（宣言のあと。p.311 の手順）なので、選ぶ前に結果は
# 決まっていない。再開先は "knock_out"。段階は Phase.DECISION
KO_PREVENTION = "ko_prevention"
# v0.61: ワザのあとのきぜつの判定で、相手のワザによって「きぜつ」する時に使える、ダメージを与える特殊能力（わるいギャラドスの［ファイナルビーム］）を使うかを、そのポケモンの
# 持ち主が決める。選べるものはそのポケモンの番号 1 つで、0 個（使わない）か 1 個（使用を宣言する）。``context`` は "attack"・"power"（こんじょうと同じ）と "source"
# （「きぜつ」させたポケモンの番号）。コインは答えのあと。再開先は "knock_out"（こんじょうと同じ続きの情報。特殊能力の定義で処理を分ける）。段階は Phase.DECISION
KNOCK_OUT_POWER = "knock_out_power"
# v0.81（docs/pokemon-tools-stadiums-v0.81.md 5 章）: ワザのあとのきぜつの判定で、相手の番にワザのダメージで「きぜつ」する対戦ポケモンについている基本エネルギーカードを、
# 学習装置をつけたポケモンにつけ替えるか（どれをつけ替えるか）を、持ち主が決める。選べるものはきぜつする対戦ポケモンについている基本エネルギーカード（とレインボーエネルギー。
# 選ぶと RB3 で止める）で、0 個（つけ替えない）か 1 個。``context`` は "attack"（こんじょうと同じ）・"tool"（学習装置のカード）・"holder"（学習装置をつけたポケモンの番号）・
# "source"（きぜつする対戦ポケモンの番号）。再開先は "knock_out"。段階は Phase.DECISION
EXP_ALL_ENERGY = "exp_all_energy"
# v0.65（docs/reactive-decisions-v0.65.md）: ワザの途中の任意の決定（再開先は "attack"。続きの情報は ``resolution.codec.AttackContinuation`` の extra。段階は Phase.DECISION）
# - 相手がワザを使う時（ワザの要素の前）に、つけた「キョウ秘伝,変わり身の術」で入れ替えるか。決めるのは、つけたポケモンの持ち主（ワザを使われた側）。選べるものは自分の控えの
#   番号で、0 個（入れ替えない）か 1 個。``context`` の "boundary"（入れ替えのあとに処理を始める要素の位置。0）・"tricks"（ついている変わり身の術のカード）
NINJA_TRICK = "ninja_trick"
# - ワザのダメージのあと・ダメージ以外の効果の前に、カスミのドククラゲの［にげこむ］を使うか（入れ替える控えを選ぶ）。決めるのは持ち主。選べるものは自分の控えの番号で、0 個
#   （使わない）か 1 個。``context`` の "boundary"（次に処理する要素の位置）・"flee"（(持ち主, ポケモンの番号, カード id, 特殊能力の位置)）
REACTION_SWITCH = "reaction_switch"
# - ダメージを受ける処理の中（ダメージを計算して、のせる前）に、タケシのサイドンの［ベンチガード］で、自分の控えポケモンが受けるダメージのうち 10 を、かわりに受けるか。決めるのは
#   受けるポケモンの持ち主。選べるものは使えるサイドンの番号で、0 個（使わない）から min(サイドンの数, ダメージ ÷ 10) 個。``context`` の "element"（ダメージの要素の位置）・
#   "bench_guard"（ダメージを受けるポケモン・残りのダメージの並び）
BENCH_GUARD = "bench_guard"
# v0.68（docs/final-pmcg-cards-v0.68.md 3 章）: キョウのベトベトンの［だつりょくえき］のコインが「おもて」のとき、ダメージを与えたポケモンについているエネルギーカードから 1 枚
# トラッシュするカードを選ぶ（使わない選択はない。1 枚しかなくても出す）。決めるのは［だつりょくえき］の持ち主（ワザを使われた側）。選べるものはダメージを与えたポケモンに
# ついているエネルギーカードの uid（ついている順）で、ちょうど 1 個。``context`` の "boundary"（次に処理する要素の位置）・"drain"（(持ち主, ポケモンの番号, カード id,
# 特殊能力の位置, ダメージを与えたポケモンの番号)）
ENERGY_DRAIN_DISCARD = "energy_drain_discard"
# ポケモンが「きぜつ」したときに使える特殊能力（v0.12。R団のファイヤーの「ふしちょう」。p.82 の最新の説明「この力は、このカードが「きぜつ」
# したとき、使える。このカードをトラッシュからとり出し、相手プレイヤーに見せてから、手札に加える。」）を使うかを、そのカードの持ち主が
# 決める。選べるものはトラッシュにあるそのカードの uid 1 つで、0 個（使わない。p.311）か 1 個（使用を宣言する）。きぜつの処理（トラッシュ・
# サイド・勝ち負けの判定）のあと、対戦が続くときだけ、バトル場にポケモンを出す前に出す（docs/post-knockout-powers-v0.12.md）。再開先は
# "post_knockout"。段階は Phase.DECISION
POST_KNOCKOUT_POWER = "post_knockout_power"
# トレーナーの「使うための条件」で、使用中のカードを除く手札からトラッシュするカードを、トレーナーを使ったプレイヤーが選ぶ（v0.22。パソコン通信の
# 「手札からカードを2枚選んでトラッシュしなければ、このカードは使えない。」。p.260・p.310）。選べるものは手札のカードの uid（手札の並び）。
# 段階は Phase.DECISION。再開先は "trainer"
DISCARD_FROM_HAND = "discard_from_hand"
# トレーナーの効果で、自分の山札からカードを選び出して手札に加えるとき、どのカードかを、トレーナーを使ったプレイヤーが選ぶ（v0.22。パソコン通信の
# 「あなたの山札からカードを1枚選び出し、手札に加える。」。p.260）。選べるものは山札のカードの uid（山札の並びを決定に写さないよう、uid の
# 小さい順）。山札の中身は選ぶプレイヤーだけが見る情報で、ログには書かない。段階は Phase.DECISION。再開先は "trainer"
SEARCH_DECK = "search_deck"
# v0.24 からポケモン交換おじさんの「あなたの山札から「たねポケモン」または「進化カード」を1枚選び出し、相手プレイヤーに見せてから、手札に
# 加える。」（p.259）でも SEARCH_DECK を使う（選べるものは山札のたねポケモン・進化カード。uid の小さい順。山札にもどしたカードを含む）。
# 選べるもの（山札の中身）はどちらもログに書かない。選んだカードを相手に見せるかはカードごと（パソコン通信は見せない・ポケモン交換
# おじさんは見せる。ログのイベントが違う）
# v0.38 からワザ（キョウのポッポの「でんれい」の「自分の山札から「キョウのポッポ」以外の「ポケモン」を1枚選び出し、相手に見せてから手札に加え」）の
# 途中の決定でも SEARCH_DECK を使う（再開先は "attack"。選べるものは山札のポケモンのカードで名前が除くものでないもの。uid の小さい順）
# トレーナーの効果で、自分の手札のカードを選び、相手に見せてから山札にもどすとき、どのカードかを、トレーナーを使ったプレイヤーが選ぶ
# （v0.24。ポケモン交換おじさんの「手札から「たねポケモン」または「進化カード」を1枚選び、相手プレイヤーに見せてから、あなたの山札に
# もどす。」。p.259）。選べるものは手札のたねポケモン・進化カードの uid（手札の並び）。段階は Phase.DECISION。再開先は "trainer"
RETURN_TO_DECK = "return_to_deck"
# トレーナーの効果で、自分の場のポケモンを進化させるとき、その上に重ねる手札の進化カードを、トレーナーを使ったプレイヤーが選ぶ
# （v0.25。ポケモン育て屋さんの「そのポケモンの上に「2進化カード」を直接のせ、1進化をとばして「2進化ポケモン」に進化させる。」。p.259）。
# 進化させるポケモンは先に SELECT_POKEMON で選ぶ（p.310 の進化の手順 1 の順。ポケモンを示してから、進化させるカードを見せる）。選べるものは
# 手札の進化カードの uid（手札の並び）。段階は Phase.DECISION。再開先は "trainer"
SELECT_EVOLUTION_CARD = "select_evolution_card"
# トレーナーの効果で、自分のトラッシュの基本エネルギーカードを選び出して手札に加えるとき、どのカードかを、トレーナーを使ったプレイヤーが選ぶ
# （v0.23。エネルギー回収の「あなたのトラッシュから「基本エネルギーカード」を最大2枚選び出し、手札に加える。ただし、このカードを使うために
# トラッシュしたカードを選ぶことはできない。」。p.257）。選べるものはトラッシュの基本エネルギーカードの uid（トラッシュの並び。トラッシュは
# 公開の情報）から、このカードを使うためにトラッシュしたカード（``context`` の ``"discarded"``）を除いたもの。段階は Phase.DECISION。
# 再開先は "trainer"。ワザ（ゴースのエナジーへんかん）の ``RECOVER_ENERGY`` とは別の決定（選べるカードの種類・除くカードが違う）
RETRIEVE_ENERGY = "retrieve_energy"
# v0.31（docs/held-cards-v0.31.md）。どれもワザの途中の決定（再開先は "attack"、段階は Phase.DECISION）で、決めるのはワザを使ったプレイヤー
# 相手のワザを自分のワザとして使うとき、相手の対戦ポケモンのワザのどれを使うか（ピクシー・ピッピの「ゆびをふる」、カスミのコダックの「ちょうのうりょく」の
# 「おもて」が 3 枚）。選べるものはワザの位置（相手の対戦ポケモンのいちばん上のカードの。``context`` の ``"copy_from"`` がそのカード id）
SELECT_ATTACK = "select_attack"
# 相手のポケモンについているエネルギーカードをトラッシュするとき、どのカードか（カツラのヒトカゲの「メラメラ」、カスミのゴルダックの「スーパー
# デストロイ」）。選べるものはそのポケモン（``context`` の ``"target"``）についているエネルギーカードの uid（ついている順）
DISCARD_OPPONENT_ENERGY = "discard_opponent_energy"
# ワザを使ったポケモンについているエネルギーカードを自分の控えポケモンにつけるとき、どの控えポケモンにつけるか（わるいマルマインの「エナジーボム」）。
# エネルギーカード 1 枚ごと（``context`` の ``"energy"``）に、選べるものは自分のベンチのポケモンの番号
ATTACH_TO_BENCH = "attach_to_bench"
# 自分のトラッシュのトレーナーカードを手札に加えるとき、どのカードか（化石の秘密のヤドンの「ゴミあさり」）。選べるものはトラッシュのトレーナーカードの uid。
# v0.53: トレーナー（ダウジングマシーン。0〜1 枚。再開先は "trainer"）でも使う
RECOVER_TRAINER = "recover_trainer"
# 自分のトラッシュのエネルギーカードを自分につけるとき、どのカードを何枚か（マチスのエレブーの「たいでん」。最大 2 枚。0 枚は決められない。HC7）
ATTACH_FROM_DISCARD = "attach_from_discard"
# v0.32（docs/bench-search-counter-drain-v0.32.md）。ワザの効果で、自分の山札から説明の名前のたねポケモンを 1 匹さがしてベンチに出すとき、どのカードか
# （ニドラン♀・マダツボミ・クラブの「なかまをよぶ」、ナゾノクサの「ふえる」）。決めるのはワザを使ったプレイヤーで、選べるものは山札の、説明の名前の
# たねポケモンのカードの uid（山札の並びを決定に写さないよう uid の小さい順）。1 匹（省略できない）。山札の中身は選ぶプレイヤーだけが見る情報で、
# ログには書かない（出したカードは場に出るので公開）。トレーナーの ``SEARCH_DECK``（手札に加える）とは別の決定。再開先は "attack"
BENCH_FROM_DECK = "bench_from_deck"
# v0.35（docs/coin-groups-damage-order-v0.35.md 3 章）。ワザのダメージの計算（p.321）の同じ段階に、加算でない変更効果を含む 2 つ以上の効果があり、
# 計算の順番によって結果が変わるとき、その順番（p.321。2・5・6 段階はワザを使うプレイヤー、7・8 段階はワザを受けるプレイヤー。``damage.DAMAGE_STEP_CHOOSER``）。
# 選べるものは、その段階の変更効果の集めた順番の番号の並べかえ（``damage.step_orders``。辞書順）の位置。``context`` に段階・変更効果・並べかえ・
# 基本となるダメージ（コインを投げ直さない）・前に選んだ段階の順番を持つ
DAMAGE_STEP_ORDER = "damage_step_order"
# v0.66（docs/optional-trainers-v0.66.md）: ワザの途中の決定（再開先は "attack"）
# - お上品攻撃（ワザを使うポケモンについている）の「のぞむなら、そのダメージを好きなだけ小さくしてよい」で減らす量（p.321 の 5 段階）。決めるのはワザを使ったプレイヤー。
#   選べるものは減らす量（0 = 減らさない、ダメージカウンターの単位ずつ 5 段階のダメージまで）で 1 つ。``context`` は "element"・"base"・"orders"・"receiver"・"value"（順番の
#   決定と同じ形の続きの情報）
DAMAGE_REDUCTION = "damage_reduction"
# - ナツメのESP（ワザを使うポケモンについている）の「そのワザの説明文に書かれているすべてのコイントスを、もう1度やり直してよい」。決めるのはワザを使ったプレイヤー。選べる
#   ものは 1（やり直す）で、0 個（やり直さない）か 1 個。``context`` の "esp"（コインを投げた要素の位置・枚数・投げたプレイヤー・最初の結果・ESP のカード）
ESP_REDO = "esp_redo"
# v0.82（docs/energy-discard-return-v0.82.md 6 章）: ライチュウ（neo3-025）の「らいげき」の「のぞむなら、自分についている「雷」エネルギーカードをすべてトラッシュしてよい」。
# 決めるのはワザを使ったプレイヤー。選べるものは 1（すべてトラッシュする）で、0 個（トラッシュしない）か 1 個（一部だけはトラッシュできない）。ついている「雷」エネルギー
# カードがなければ出さない。再開先は "attack"
OPTIONAL_DISCARD_ALL = "optional_discard_all"
# - カスミの勝負（トレーナー。再開先は "trainer"）の「じゃんけん」の手。決めるのは使ったプレイヤー（``context`` の "stage" 0）→ 相手プレイヤー（"stage" 1）。選べるものは
#   0 グー・1 チョキ・2 パーで 1 つ。"round" はあいこのくり返しの回数（1 から）、"first" は 1 人目の手（2 人目の決定だけ。観測には出さない）
JANKEN_HAND = "janken_hand"
# v0.72（docs/status-coins-effect-reuse-v0.72.md）。ゴルバット（ES1-009）・パラセクト（ES1-011）の「きゅうけつ」の「相手にダメージを与えたら、与えたぶんのダメージカウンターを、
# このカードから取りのぞいてよい。」で、取りのぞくか。決めるのはワザを使ったプレイヤー。選べるものはワザを使ったポケモンの番号 1 つで、0 個（取りのぞかない）か 1 個（与えたぶん
# （のっている数まで）を取りのぞく）。``context`` の "dealt"（与えたダメージ）・"counters"（与えたぶんのカウンターの数）。再開先は "attack"
OPTIONAL_DRAIN = "optional_drain"
# v0.73: トレーナーの効果で、自分の山札または自分のトラッシュから、決まったカード（化石の発掘の「「なにかの化石」」）を合わせて 0〜1 枚選び出して手札に加えるとき、どの
# カードかを、使ったプレイヤーが選ぶ（docs/search-recovery-trainers-v0.73.md 3 章）。選べるものは山札の対象のカード（uid の小さい順）→ トラッシュの対象のカード（トラッシュの
# 並び）。山札の中身は選ぶプレイヤーだけが見る情報（観測は決めるプレイヤーにだけ選べるものを見せる）。段階は Phase.DECISION。再開先は "trainer"
SEARCH_DECK_OR_DISCARD = "search_deck_or_discard"
# v0.73: トレーナーの効果で、自分の山札の上から見たカード（マスターボールの「あなたの山札の上から7枚を見る」）のうち、ポケモンのカード（たねポケモン・進化カード）から
# 1 枚を、使ったプレイヤーが選ぶ。選べるものは見たカードのうちポケモンのカード（山札の上からの順）。見た範囲より下の山札のカードは選べない。選べるもの・その数は決める
# プレイヤーだけが見る（observation.HIDDEN_COUNT_KINDS）。段階は Phase.DECISION。再開先は "trainer"
TAKE_LOOKED_POKEMON = "take_looked_pokemon"
# v0.35: カスミのニョロモの「ドわすれ」の「相手のワザを1つ選ぶ。」。決めるのはワザを使ったプレイヤーで、選べるものは相手の対戦ポケモン（``context`` の
# ``"target"``）のいちばん上のカードのワザの位置
SELECT_OPPONENT_ATTACK = "select_opponent_attack"
# v0.41（docs/heal-counter-status-v0.41.md）。エリカのクサイハナの「ミラクルかふん」の「「ねむり・マヒ・こんらん・どく」の中から1つを選び、相手をその状態に
# する。」。決めるのはワザを使ったプレイヤーで、選べるものは説明の並びの番号（0 ねむり・1 マヒ・2 こんらん・3 どく。``effects.CHOSEN_CONDITIONS``）。
# ``context`` の ``"target"`` が相手の対戦ポケモン。選ぶと原典で決められない状態（マヒの再付与で回復する番が変わる）は ``"unresolved_choices"``
SELECT_SPECIAL_CONDITION = "select_special_condition"
# v0.41: ロケット団のヤドンの「ひなたぼっこ」の「自分の山札から「超」エネルギーカードを1枚選び出し、このカードにつけてよい。」。決めるのはワザを使った
# プレイヤーで、選べるものは山札の「超」の基本エネルギーカードの uid（山札の並びを決定に写さないよう uid の小さい順）。0〜1 枚（「つけてよい」なので
# 選ばなくてよい）。山札の中身は選ぶプレイヤーだけが見る情報で、ログには書かない（つけたカードは場に出るので公開）。再開先は "attack"
ATTACH_FROM_DECK = "attach_from_deck"
# v0.42（docs/power-decisions-v0.42.md）。ナツメのルージュラの「よいおこない」の「そのポケモンにのっているダメージカウンターを、好きなだけとりのぞく」。決めるのは
# ワザを使ったプレイヤーで、選べるものはとりのぞく数（0〜のっている数。``context`` の ``"target"`` がそのポケモン）。0 は「好きなだけ」で 0 を選べるかが
# 決められない（HC5 と同じ問い）ので ``"unresolved_choices"``。再開先は "attack"
REMOVE_COUNTERS = "remove_counters"
# v0.42: ナツメのケーシィの「エネループ」の「自分についている「超」エネルギーカードを1枚選び、はがして手札にもどす」。決めるのはワザを使ったプレイヤーで、
# 選べるものはワザを使ったポケモンについている「超」の基本エネルギーカードの uid（ついている順。1 枚でも決定を出す。DISCARD_ENERGY と同じ形）。トラッシュの
# DISCARD_ENERGY とは行き先が違うので別の種類。再開先は "attack"
RETURN_ENERGY = "return_energy"
# v0.43（docs/declared-entry-powers-v0.43.md）。場に出たときに 1 度だけ使える特殊能力（わるいゴルバットの［こっそりかみつく］・わるいヤドランの［つりあげる］・
# わるいカイリューの［てしたをよぶ］）を使うかを、そのポケモンの持ち主が決める（使う機会）。選べるものはそのポケモンの番号 1 つで、0〜1 個（選ばない = 使わない）。
# 再開先は "power"（使ったら宣言のログ ``pokemon_power`` のあと、特殊能力の処理。使わなければログ ``entry_power_declined``）。``context`` の ``"entry"`` は場に出た
# 経路（今は手札から（``"hand"``）だけ）、``"return_to"`` は場に出した元の処理（トレーナーの効果の途中なら ("trainer", プレイヤー, カード, カード id)）
ENTRY_POWER = "entry_power"
# v0.43: 自分の場のポケモンについているエネルギーカードを選んで、特殊能力を使ったポケモン（このカード）につけかえるとき、どのカードか（エリカのマダツボミの
# ［ようぶんきゅうしゅう］（最大 2 枚）・マチスのレアコイルの［エナジーチャージ］（好きなだけ））。選べるものはエネルギーカードの uid（場の並び（バトル場 →
# ベンチ）・ついている順）。再開先は "power"
MOVE_ENERGY = "move_energy"
# v0.43: 自分のトラッシュのポケモンのカードを選んで、見せてから手札に加えるとき、どのカードか（わるいヤドランの［つりあげる］。最大 3 枚）。選べるものは
# トラッシュのポケモンのカード（たねポケモン・進化カード）の uid（トラッシュの並び）。同じカードを 2 回選べない（``check_choices``）。再開先は "power"
RECOVER_POKEMON = "recover_pokemon"
# v0.44（docs/search-evolution-once-attacks-v0.44.md）。ワザの効果で、自分の手札のカードを選び、相手に見せずに山札にもどすとき、どのカードか（ナツメのバリヤードの
# 「てじな」の「自分の手札から最大3枚のカードを選び、山札にもどす」（0〜3 枚。0 枚は GS1 と同じ問い）・_____のラッキーの「ラッキーたまご」の「自分の手札から
# カードを2枚選び、山札にもどして」（2 枚））。決めるのはワザを使ったプレイヤーで、選べるものは手札のカードの uid（手札の並び）。v0.24 のポケモン交換おじさんの
# RETURN_TO_DECK（トレーナー。見せる。たねポケモン・進化カードだけ）とは別の決定。再開先は "attack"。v0.53: トレーナー（エリカのお付きの使うための条件・メンテナンス。
# どちらも見せる指示がなく、どの種類のカードでもよい。2 枚）でも使う（再開先は "trainer"）
HAND_TO_DECK = "hand_to_deck"
# v0.44: カツラのマンキーの「わるいいたずら」の「相手のトラッシュからカードを1枚選び出し、相手の山札の上にのせる」。決めるのはワザを使ったプレイヤーで、選べるものは
# 相手のトラッシュのカードの uid（トラッシュの並び。公開の情報）。1 枚。再開先は "attack"。v0.53: リサイクル（自分のトラッシュの好きなカード 1 枚。再開先は "trainer"）
DISCARD_TO_DECK_TOP = "discard_to_deck_top"
# v0.45（docs/conditional-damage-energy-v0.45.md）。わるいレアコイルの「じりょくせん」の「相手の対戦ポケモンのエネルギーカード(特殊エネルギーカード以外)を1枚選んで
# はがす」。決めるのはワザを使ったプレイヤーで、選べるものは相手の対戦ポケモン（``context`` の ``"target"``）についている基本エネルギーカードの uid（ついている順。
# 1 枚でも決定を出す）。つける控えポケモンは続けて ``SELECT_POKEMON``（``context`` の ``"energy"`` がはがすカード）で選ぶ。v0.31 の DISCARD_OPPONENT_ENERGY（トラッシュ）
# とは行き先が違うので別の種類。再開先は "attack"
MOVE_OPPONENT_ENERGY = "move_opponent_energy"
# v0.46（docs/continuous-powers-v0.46.md）。エリカのフシギバナの「せいちょう」の「コインを投げて「おもて」なら、自分の手札にある「草」エネルギーカードを最大2枚、このカードに
# つける」。決めるのはワザを使ったプレイヤーで、選べるものは手札の「草」の基本エネルギーカードの uid（手札の並び）。0〜min(2, 枚数) 枚（0 枚は「最大2枚」が 0 枚を
# 含むかが決められない。v0.31 の HC7（トラッシュからつける「最大2枚」）と同じ問いで、答えのときに止める）。手札からつける通常の操作（p.310。1 番に 1 枚）とは別の処理
# （回数に数えない）。v0.41 の ATTACH_FROM_DECK（山札）・v0.31 の ATTACH_FROM_DISCARD（トラッシュ）とは選ぶ場所が違うので別の種類。再開先は "attack"
ATTACH_FROM_HAND = "attach_from_hand"
# v0.47（docs/fossil-hidden-info-v0.47.md 4 章）: 裏向きのカード・見えないカードを、内容を知らずに位置で選ぶ決定と、見たカードの並べかえ。選べるものはどれも位置・プレイヤー・
# 数で、カードの uid を選べるものに入れない（見る前に内容を漏らさない）。ARRANGE_DECK_TOP だけは、見たプレイヤーが見たカード（uid）の並びを答える
# マンキーの［スパイ］: 見るカード（``context`` の ``"targets"`` の位置。(``"deck"``, 持ち主)・(``"prize"``, 持ち主, 位置)・(``"hand"``, 持ち主, 位置)）
PEEK_CARD = "peek_card"
# コラッタ（ロケット団）の［わるふざけ］: 自分のサイドの位置
SELECT_PRIZE_CARD = "select_prize_card"
# スリーパーの「みらいよち」: 見る山札の持ち主（プレイヤー）→ 見る枚数 → 見たカードのもどす並び（上から順。見たカードの uid）
SELECT_DECK_OWNER = "select_deck_owner"
SELECT_LOOK_COUNT = "select_look_count"
ARRANGE_DECK_TOP = "arrange_deck_top"
# マチスのイーブイの「おどろかす」: 相手の手札の位置（おもてを見ないで選ぶ）
SELECT_HAND_CARD = "select_hand_card"
# v0.48（docs/effective-pokemon-properties-v0.48.md）: 色（タイプ）を選ぶ。選べるものは ``effects.COLORS`` の位置（ポリゴンの「テクスチャー1」「テクスチャー2」は無色以外の
# 色。モルフォンの［へんしょく］は場にいるポケモンの色）。決めるのはワザ・特殊能力を使ったプレイヤー
SELECT_COLOR = "select_color"
# v0.50（docs/mew-devolution-spray-v0.50.md）: 退化スプレーで、選んだポケモンからはがす進化カードの枚数（0〜重なっている進化カードの数）。決めるのは使ったプレイヤー。
# 0 枚は「ことができる」の、はがさないこと（はがさなければ退化しない）
SELECT_DEVOLVE_COUNT = "select_devolve_count"
# v0.51（docs/discard-to-bench-v0.51.md）: トラッシュのたねポケモンのカードを選んで、持ち主のベンチに出すとき、どのカードか（ナツメのスリーパーの「よみがえらせる」は
# 自分または相手のトラッシュ（再開先 "attack"）、元気のかけらは自分のトラッシュ、ポケモンの笛は相手のトラッシュ（どちらも再開先 "trainer"））。決めるのはワザ・トレーナーを
# 使ったプレイヤー（ポケモンの笛でも、出される側の相手ではない）。選べるものはトラッシュのカードの uid（使ったプレイヤーのトラッシュ → 相手のトラッシュ、それぞれトラッシュの並び。
# トラッシュは公開の情報）。山札の ``BENCH_FROM_DECK`` とは選ぶ場所が違うので別の種類
BENCH_FROM_DISCARD = "bench_from_discard"
# v0.53（docs/search-retrieval-trainers-v0.53.md）: 夜の廃品回収で、自分のトラッシュから山札にもどすカード（ポケモンのカード・基本エネルギーカード。最大 3 枚）。決めるのは
# 使ったプレイヤー。選べるものはトラッシュのカードの uid（トラッシュの並び。トラッシュは公開の情報）。山札の一番上にのせる ``DISCARD_TO_DECK_TOP``（わるいいたずら・
# リサイクル。1 枚。切らない）とは、枚数・行き先・切るかが違うので別の種類
DISCARD_TO_DECK = "discard_to_deck"
# v0.54（docs/hand-deck-trainers-v0.54.md）: エリカの「のぞむなら最大3枚まで、山札からカードを引いてよい」で引く枚数（0〜min(3, 自分の山札の枚数)）。決めるのは引くプレイヤー
# （先に使ったプレイヤー、引き終わってから相手プレイヤー。``context`` の ``"stage"``）。0 枚は「のぞむなら」の、引かないこと
SELECT_DRAW_COUNT = "select_draw_count"
# v0.55（docs/instant-trainers-v0.55.md）: カスミのいかりで、見た山札の上のカード（7 枚）から手札に加える 2 枚。決めるのは使ったプレイヤー。選べるものは見たカードの uid
# （山札の上からの順。決めるプレイヤーは見ている）。残りはトラッシュする。山札をさがす ``SEARCH_DECK`` とは、選べるカード（見た上の 7 枚だけ）・残りの行き先が違うので別の種類
TAKE_LOOKED_CARDS = "take_looked_cards"
# v0.55: ロケット団のおねーさんで、見た相手の手札のトレーナーカードから、相手の山札にもどさせる 1 枚。決めるのは使ったプレイヤー（手札を見た）。選べるものは相手の手札の
# トレーナーカードの uid（手札の並び）。相手のポケモン・山札を選ぶ決定とは別
OPPONENT_HAND_TO_DECK = "opponent_hand_to_deck"
# v0.55: いいきずぐすりで、選んだポケモンからとりのぞくダメージカウンターの数（0〜min(4, のっている数)。「4個まで…ことができる」）。決めるのは使ったプレイヤー
SELECT_COUNTER_COUNT = "select_counter_count"
# v0.56（docs/trainer-decisions-turn-effects-v0.56.md 3 章）: トレーナーの説明が「…かどうか、相手プレイヤーにたずねる」とき（マチスの交渉・カスミのわがまま）の、相手の
# 答え。決めるのは使ったプレイヤーの相手。選べるものは 1（オーケー）だけで、0〜1 個（選ばない = オーケーでない）。続きの情報には使ったカードとたずねる内容の段階だけを
# 書き、見たサイドのカードを書かない（相手に渡らない）
ACCEPT_REQUEST = "accept_request"
# v0.56: エリカの香水で、見た相手の手札の「たねポケモン」から相手のベンチに出させるもの。決めるのは使ったプレイヤー（手札を見た）。選べるものは相手の手札のたねポケモンの
# uid（手札の並び）。0〜min(ベンチの空き, 数) 枚（「好きなだけ…てよい」）
OPPONENT_HAND_TO_BENCH = "opponent_hand_to_bench"
# v0.56: ロケット団のワナで、相手の手札から「おもてを見ないで」選ぶ位置。決めるのは使ったプレイヤー。選べるものは相手の手札の位置（0 から。カードの uid・中身は渡さない）
SELECT_HAND_POSITIONS = "select_hand_positions"
# v0.56: マチスで、手札から直接バトル場に出す「たねポケモン」。決めるのは使ったプレイヤー。選べるものは自分の手札のたねポケモンの uid（手札の並び）
HAND_TO_ACTIVE = "hand_to_active"
# v0.56: カスミのわがままで、見たサイドのカードと交換する手札のカード。決めるのは使ったプレイヤー。選べるものは自分の手札のカードの uid（手札の並び。使っているこの
# カードは手札にない）
SWAP_WITH_PRIZE = "swap_with_prize"
# v0.57（docs/stadiums-v0.57.md 5 章）: せまいジムが場に出た時、ベンチにポケモンが 5 匹いるプレイヤーが、その中から手札にもどす 1 匹。決めるのはそのプレイヤー（ベンチの
# 持ち主）。選べるものはそのプレイヤーの控えポケモンの番号。両方のプレイヤーが 5 匹なら、番でないプレイヤーが先（実装上の順番。``context`` の ``"remaining"``）
STADIUM_RETURN_BENCH = "stadium_return_bench"
# v0.57: トキワシティジムがある時、自分の「サカキのポケモン」を進化させる時に、のっているダメージカウンターを 2 つとりのぞくか。決めるのは進化させたプレイヤー（持ち主）。
# 選べるものはそのポケモンの番号 1 つで、0〜1 個（選ばない = とりのぞかない。「のぞむなら」）
EVOLUTION_HEAL = "evolution_heal"
# v0.58（docs/stadium-reuse-special-energy-v0.58.md 4 章）: ナツメのサイキックコントロールの「おもて」で、相手のトラッシュから使うトレーナーカード。決めるのは使ったプレイヤー。
# 選べるものは相手のトラッシュのトレーナーカード（トラッシュの並び。公開の情報）のうち、使えるもの。0〜1 枚（選ばない = 使わない。「使ってよい」）
USE_DISCARD_TRAINER = "use_discard_trainer"
# v0.63（docs/hidden-card-trainers-v0.63.md）。どれもトレーナーの効果の途中の決定（再開先は "trainer"、段階は Phase.DECISION）
# たたきつけろ!挑戦状で、自分の山札から選んでうらにしてベンチに出すたねポケモンのカード。決めるのはそれぞれのプレイヤー（使ったプレイヤー → 相手プレイヤーの順）。選べるものは
# 自分の山札のたねポケモンのカード（uid の小さい順）。0〜min(ベンチの空き, 選べる枚数) 枚（0 枚は HC5 で止める）。選べるもの・選ぶ数は決めるプレイヤーだけが見る（観測）
CHALLENGE_BENCH = "challenge_bench"
# カツラのクイズ その3で、おもてを下にして置く手札のポケモンのカード（ワザを持つもの）。決めるのは使ったプレイヤー。選べるもの・選ぶ数は使ったプレイヤーだけが見る
QUIZ_CARD = "quiz_card"
# 置いたカードの、相手に伝えるワザ。選べるものはそのカードのワザの位置。決めるのは使ったプレイヤー（選べるもの・選ぶ数は使ったプレイヤーだけが見る。相手にはワザの名前だけを伝える）
QUIZ_ATTACK = "quiz_attack"
# 相手プレイヤーが答えるカードの名前。選べるものは ``context`` の ``"names"``（カードのデータのポケモンの名前の並び。置いたカード・手札によらない）の位置。決めるのは相手プレイヤー
QUIZ_ANSWER = "quiz_answer"

# v0.67（docs/secret-plan-preflight-v0.67.md）: マチスの秘策で、うらにしてベンチに出す手札のカード。決めるのは使ったプレイヤー。選べるものは手札のカード（どの種類でもよい）。
# 0〜1 枚（0 枚は出さない）。選べるもの・選ぶ数は使ったプレイヤーだけが見る（観測）
SECRET_PLAN_CARD = "secret_plan_card"

# v0.80（docs/neo-trainer-components-v0.80.md）。どれもトレーナーの効果の途中の決定（再開先は "trainer"、段階は Phase.DECISION）
# カードめくりゲームで選ぶ、うらになっている相手のサイドの位置。決めるのは使ったプレイヤー（位置で選ぶ。選ぶ前に内容を見せない）
SELECT_OPPONENT_PRIZE = "select_opponent_prize"
# ポケモンギアで、見た山札の上の 7 枚のうちのトレーナーカードから手札に加える 1 枚。決めるのは使ったプレイヤー（選べるものの数は山札の中身を漏らすので、ほかの人に見せない）
TAKE_LOOKED_TRAINER = "take_looked_trainer"

# v0.84（docs/light-powers-evolution-v0.84.md）。どれもワザの途中の決定（再開先は "attack"、段階は Phase.DECISION）
# やさしいイノムーの「つきくずす」で、場のスタジアムをトラッシュするか。決めるのはワザを使ったプレイヤー。選べるものは場のスタジアムのカード 1 つ。0〜1 個（選ばない = トラッシュしない）
DISCARD_STADIUM = "discard_stadium"
# やさしいプクリンの「しんかのうた」で、進化させる自分の場のポケモン。決めるのはそれぞれのプレイヤー（``context`` の ``"stage"``）。選べるものはそのプレイヤーの場のポケモンの番号。
# 0〜1 匹（0 は選ばない）。選ぶと止めるポケモン（``unresolved_choices``）が山札の中身で決まるので、選べるものの数・止める選択は決めるプレイヤーだけが見る（観測）
EVOLUTION_SONG_POKEMON = "evolution_song_pokemon"

# v0.86（docs/entry-energy-evolution-reactions-v0.86.md 2 章）。再開先は "reaction"（``reactions``）
# 同じ時点に起こる 2 つ以上の反応（手札からつけたエネルギーカード・進化への反応）の順番。決めるのはその時に番を行っているプレイヤー（GR-2000-P325-SAME-TIMING）。
# 選べるものは待っている反応の位置（``context`` の ``"reaction"``）。1 つ選ぶと、それを処理し、残りの反応はそのあとに処理する
REACTION_ORDER = "reaction_order"
# v0.87: ［やけのこり］で新しい対戦ポケモンにつけ替える「炎」エネルギーカード（決めるのは持ち主。選べるものはこのカードについているカード。1 枚）
MAGMA_POOL_ENERGY = "magma_pool_energy"
# v0.87: ［ぶんれつ］でベンチに出す山札の「ドガース」（決めるのは持ち主。0〜1 枚。選べるものの数は山札の中身を漏らすので、決めるプレイヤーだけに見せる）
SPLIT_FROM_DECK = "split_from_deck"
# 決められた事実（手札からエネルギーカードをつけた・ほかのポケモンが進化した）のときに使える特殊能力（［エナジーしんか］・［れんさしんか］）の使う機会。決めるのは持ち主。
# 選べるものはそのポケモンの番号 1 つ。0 個（使わない）か 1 個（使う）
REACTION_POWER = "reaction_power"
# v0.90（docs/markers-counters-v0.90.md 4 章）: ワザの説明の「のぞむなら、このカードにのっている「…カウンター」を…取りのぞき、…ダメージを追加してもよい」で取りのぞく数（ボーンキラーは
# 0〜1・ころがるは 0〜のっている数）。決めるのはワザを使ったプレイヤー。選べるものは数（0 = 取りのぞかない）で 1 つ。``context`` の "marker"（種類）。再開先は "attack"
SELECT_MARKER_COUNT = "select_marker_count"
# v0.95（docs/private-looks-deck-movement-v0.95.md）: エイパムの「とりさる」の「相手の場のポケモンについている「トレーナーカード」を1枚選び」で、相手の山札にもどすカード。決めるのは
# ワザを使ったプレイヤー。選べるものは相手の場のポケモン（バトル場 → ベンチの並び）についているトレーナーカードの uid（ついている順。場の公開のカード）で 1 枚。再開先は "attack"
SELECT_ATTACHED_TRAINER = "select_attached_trainer"
# v0.95: わるいヤドキングの［わるぢえ］の「その後、のぞむなら、その山札をよく切る」で、見た山札を切るか。決めるのは特殊能力を使ったプレイヤー。選べるものは山札の持ち主の
# プレイヤーの番号 1 つで、0 個（切らない）か 1 個（切る）。再開先は "power"
OPTIONAL_SHUFFLE = "optional_shuffle"
# v0.104（docs/healing-pokemon-v0.104.md 4.4 節）: プリン（PR1-002・PR1-004）の「かいふく」の「自分についているダメージカウンターを1つ取り除くことができる。」で、取り除くか。決めるのは
# ワザを使ったプレイヤー。選べるものはワザを使ったポケモンの番号 1 つで、0 個（取り除かない）か 1 個（取り除く）。``context`` の "counters"（取り除く数）。ワザを使ったポケモンに
# ダメージカウンターがのっていなければ出さない。v0.72 の OPTIONAL_DRAIN（「相手にダメージを与えたら」の条件と与えたダメージを持つ）とは別の種類。再開先は "attack"
OPTIONAL_HEAL = "optional_heal"
# v0.114（docs/baby-rules-evolution-v0.114.md 6 章）: ムチュール（neo3-031）の「サイコキッス」の「相手の場のポケモンについている「特殊エネルギーカード」を1枚選び、相手の山札にもどす」で、
# もどすカード。決めるのはワザを使ったプレイヤー。選べるものは相手の場のポケモン（バトル場 → ベンチの並び）についている特殊エネルギーカード（ついている間の定義。場の公開のカード）の
# uid（ついている順）で 1 枚。``context`` の ``"owner"`` はカードとポケモンの持ち主（相手）。v0.95 の SELECT_ATTACHED_TRAINER（トレーナーカード）とは選ぶカードが違うので別の種類。
# 再開先は "attack"
SELECT_ATTACHED_SPECIAL_ENERGY = "select_attached_special_energy"
# v0.115（docs/spread-damage-allocation-v0.115.md 4.3 節）: シードラの「ウォーターボム」・ゴローンの「がんせきくだき」・ゴローニャの「ロックブラスト」の、得たダメージの単位を相手の場の
# ポケモンに配る配分（得た分をすべて配る。同じポケモンに配った単位は合算する）。決めるのはワザを使ったプレイヤーで、選べるものは ``context`` の ``"table"``（配る先のポケモン（``"allocation"``
# の番号の並び）ごとの単位の数の組の並び。合計はちょうど得た単位の数）の位置。ちょうど 1 つ。重ならない選択の並びで回数を表さない（決定の答えの重複の拒否は変えない）。再開先は "attack"
ALLOCATE_DAMAGE = "allocate_damage"
# v0.118（docs/unbounded-coins-heal-allocation-v0.118.md 7 章）: フシギソウ（SI-008）の「ふしぎなかおり」の「自分の場のポケモンにのっているダメージカウンターを、最大3つとりのぞく」・ラフレシア
# （SI-011）の「ごくらくかふん」の「そのポケモンにのっているダメージカウンター最大2つと、自分にのっているダメージカウンター最大2つを、それぞれ、とりのぞく」の、とりのぞく数の配分。
# 決めるのはとりのぞくポケモンの持ち主（ふしぎなかおりは「おもて」を出したプレイヤーごと、ごくらくかふんはワザを使ったプレイヤー）。選べるものは ``context`` の ``"table"``（とりのぞく先
# （``"heal"`` の番号の並び）ごとの数の組の並び）の位置。ちょうど 1 つ。0 の組（とりのぞけるのに 0 を選ぶ）は選べるが選ぶと止める（HZ1）。再開先は "attack"
HEAL_ALLOCATION = "heal_allocation"
# v0.118: ルギア（PF3-008）の「エアロウイング」の「のぞむなら、コインを投げてよい」。決めるのはワザを使ったプレイヤー。選べるものは (1,)（1 個: 投げる・0 個: 投げない）。再開先は "attack"
OPTIONAL_COIN = "optional_coin"
# v0.118: わるいポリゴン2（neo4-097）の［じくうへんかん］の「自分のトラッシュから「スタジアムカード」を1枚選び出し、場に出す」で、場に出すカード。決めるのは特殊能力を使ったプレイヤー。
# 選べるものは自分のトラッシュのスタジアムカード（トラッシュの並び。公開のカード）で 1 枚。再開先は "power"
STADIUM_FROM_DISCARD = "stadium_from_discard"
# v0.118: カイリュー（PR1-043）の［トランスポート］の「その後、自分の手札からカードを1枚選び、山札の上に置く」で、山札の上に置く手札のカード（引いたカードも選べる）。決めるのは特殊能力を
# 使ったプレイヤー。選べるものは手札のカード（手札の並び）で 1 枚。手札の中身・選べる数は相手に見せない（観測の ``HIDDEN_COUNT_KINDS``）。再開先は "power"
DECK_TOP_FROM_HAND = "deck_top_from_hand"
# v0.119（docs/damage-reactions-poison-sleep-v0.119.md 3 章）: カスミのパルシェン（GD2-007）の［シェルアーマー］の「この力は、このカードがワザによるダメージを受けるたびに、1回使える。このカードが
# 受けるダメージを「-10」する。」を、そのダメージで使うか（p.321 の 8 段階。ダメージの計算が 8 段階に来たとき）。決めるのはダメージを受けるポケモンの持ち主。選べるものは受けるポケモンの
# 番号 1 つ（1 個: 使う・0 個: 使わない）。``context`` は順番の決定と同じ形の続きの情報と ``"option"``（(段階, 発生源のカード, 数)）・``"value"``（8 段階の前のダメージ）・``"finals"``
# （使わないときの最終ダメージ）。控えポケモンへのダメージの要素では ``"bench_guard"``（運ぶ並び）。再開先は "attack"
DAMAGE_OPTION = "damage_option"

_PHASE_FOR_KIND = {TAKE_PRIZE: Phase.TAKE_PRIZE, PROMOTE_ACTIVE: Phase.PROMOTE_ACTIVE}

# 決定を待っている段階。並び（DECISION_PHASE_ORDER。段階の定義の順）は、決定への答えを拒否する理由の文（WRONG_PHASE）に書く順番。
# v0.13〜v0.15 は frozenset の並び（文字列のハッシュで決まる）で書いていたので、プロセスごとに文が変わっていた（v0.16d で決めた。
# 受け付ける段階・例外の種類・コードは同じ。docs/legacy-test-migration-v0.16d.md 5 章）
DECISION_PHASE_ORDER = (Phase.TAKE_PRIZE, Phase.PROMOTE_ACTIVE, Phase.DECISION)
DECISION_PHASES = frozenset(DECISION_PHASE_ORDER)


def phase_for(kind: str) -> Phase:
    """決定の種類に対応する段階。v0.1 からある種類はそれぞれの段階、それ以外は Phase.DECISION。"""
    return _PHASE_FOR_KIND.get(kind, Phase.DECISION)


def push_decision(
    state: GameState,
    *,
    kind: str,
    player: int,
    options: Iterable[int],
    resume: str,
    context: Iterable[tuple[str, Any]] = (),
    min_choices: int = 1,
    max_choices: int = 1,
) -> PendingDecision:
    """決定を出し、その決定を待つ段階にする。"""
    if state.decision is not None:
        raise RuntimeError("決定を待っている間に、別の決定を出そうとした（エンジンの不具合）")
    decision = PendingDecision(
        id=state.next_decision_id,
        kind=kind,
        player=player,
        options=tuple(options),
        min_choices=min_choices,
        max_choices=max_choices,
        resume=resume,
        context=tuple(context),
    )
    state.decision = decision
    state.next_decision_id += 1
    state.phase = phase_for(kind)
    return decision


def push_attack_decision(
    state: GameState,
    use: AttackUse,
    *,
    kind: str,
    player: int,
    options: Iterable[int],
    context: Iterable[tuple[str, Any]] = (),
    min_choices: int = 1,
    max_choices: int = 1,
) -> PendingDecision:
    """ワザの効果の途中で決定を出す（v0.13 の約束の補助関数）。選ばれたら、そのワザの実装の ``resume`` が呼ばれる。

    決定の形は v0.13 と同じ（再開先 ``"attack"``、``context`` は ``("use", (プレイヤー, 場のポケモンの番号, カード id, ワザの位置))`` と
    ``context``）。v0.16b から、解決の基盤のワザの枠（``use.runtime``）に委ねる（``AttackRun.suspend``。決定を出す前に、そのワザの
    ダメージではたらいた「ダメージを受けたとき」の効果が残っていれば ``RuntimeError``。``finish_damage_elements`` のあとに出す。p.89）。
    ``use.runtime`` がなければ ``RuntimeError``。
    """
    runtime = getattr(use, "runtime", None)
    if runtime is None:
        raise RuntimeError(f"ワザ {use.key} の決定は、解決の基盤がワザを処理している間だけ出せる（AttackUse に解決の基盤の入口がない）")
    return runtime.push_decision(state, kind=kind, player=player, options=options, context=tuple(context), min_choices=min_choices,
                                 max_choices=max_choices)


def push_trainer_decision(
    state: GameState,
    use: TrainerUse,
    *,
    kind: str,
    player: int,
    options: Iterable[int],
    context: Iterable[tuple[str, Any]] = (),
    min_choices: int = 1,
    max_choices: int = 1,
    unresolved_choices: Iterable[int] = (),
    unresolved_code: str = "UNRESOLVED_RULING",
    unresolved_reason: str = "",
    unresolved_detail: Iterable[tuple[int, str, str]] = (),
) -> PendingDecision:
    """トレーナーの効果の途中で決定を出す（v0.2b）。選ばれたら、そのトレーナーの実装の ``resume`` が呼ばれる。

    ``unresolved_choices``: ``options`` のうち、選んだときの扱いを原典で決められないもの（選ぶと
    ``UnsupportedError(unresolved_code, unresolved_reason)``）。
    """
    entries = [("use", (use.player, use.card, use.card_id))]
    options = tuple(options)
    unresolved = tuple(unresolved_choices)
    detail = tuple(tuple(item) for item in unresolved_detail)
    # v0.117（docs/retreat-return-active-powers-v0.117.md 5 章）: ［でんせつのからだ］で「トレーナーカード」の効果を受けないポケモン・そのポケモンについているカードは、選べるが選ぶと止める
    # （LB1。選べるものの意味が場のポケモン・カードの決定だけ。決定を出す時点で、コイン・山札の中身の前に決める）。止める選択（``unresolved_choices``）に加え、選択ごとの理由
    # （``unresolved_detail``）を LB1 にし、加えた選択を ``legend_body_choices`` に書く（不変条件がトレーナーの実装の決定の形を確かめるときは、その選択を除いた形で比べる）
    from .effects import (
        LEGEND_BODY_TARGET_CODE,
        LEGEND_BODY_TARGET_REASON,
        legend_body_option_stops,
        trainer_card_effect,
    )

    stops = tuple(o for o in legend_body_option_stops(state, kind, options) if o not in unresolved) if trainer_card_effect(state, use.card) else ()
    if stops:
        entries.append(("legend_body_choices", stops))
        detail += tuple((o, LEGEND_BODY_TARGET_CODE, LEGEND_BODY_TARGET_REASON) for o in stops)
        unresolved += stops
    if unresolved:
        entries += [("unresolved_choices", unresolved), ("unresolved_code", unresolved_code), ("unresolved_reason", unresolved_reason)]
    if detail:
        # v0.49: 選ぶと止める選択ごとの (選択, コード, 理由)。選択によって止める理由が違うとき（「ばける」の候補）だけ書く。``check_choices`` が優先して使う
        if not {item[0] for item in detail} <= set(unresolved):
            raise RuntimeError(f"選択ごとの止める理由 {detail} の選択が、選ぶと止める選択 {unresolved} にない（エンジンの不具合）")
        entries.append(("unresolved_detail", detail))
    return push_decision(
        state,
        kind=kind,
        player=player,
        options=options,
        resume="trainer",
        context=(*entries, *tuple(context)),
        min_choices=min_choices,
        max_choices=max_choices,
    )


def push_power_decision(
    state: GameState,
    use,
    *,
    kind: str,
    player: int,
    options: Iterable[int],
    context: Iterable[tuple[str, Any]] = (),
    min_choices: int = 1,
    max_choices: int = 1,
    unresolved_choices: Iterable[int] = (),
    unresolved_code: str = "UNRESOLVED_RULING",
    unresolved_reason: str = "",
    unresolved_detail: Iterable[tuple[int, str, str]] = (),
) -> PendingDecision:
    """宣言して使う特殊能力の処理の途中で決定を出す（v0.42）。選ばれたら、その特殊能力の実装の ``resume`` が呼ばれる（再開先 ``"power"``）。

    ``context`` は ``("use", (プレイヤー, 場のポケモンの番号, カード id, 特殊能力の位置))`` と、``unresolved_choices``（トレーナーの決定と同じ。選ぶと
    ``UnsupportedError(unresolved_code, unresolved_reason)``）と、実装が決定をまたいで使う値（``context``）。決定の形はトレーナーの決定（v0.2b）と同じ考え方で、
    実装が ``PowerEffect.decision_problems`` で宣言する。
    """
    entries = [("use", (use.player, use.pokemon_id, use.key.card_id, use.key.power_index))]
    card = getattr(use, "card", None)
    found = state.find_pokemon(use.pokemon_id)
    if card is not None and found is not None and card != found[1].card:
        # v0.49: 特殊能力を印刷したカードが、ポケモンのいちばん上のカードでない（「ばける」でのせたカード）。そのカードの uid（ふつうは書かない。v0.48 と同じ形）
        entries.append(("power_card", card))
    if getattr(use, "return_to", None) is not None:
        # v0.43: 場に出したトレーナーの効果の途中で使う特殊能力（ポケモン育て屋さんで場に出たわるいカイリューの［てしたをよぶ］）。終わったらその処理にもどる
        entries.append(("return_to", use.return_to))
    unresolved = tuple(unresolved_choices)
    if unresolved:
        entries += [("unresolved_choices", unresolved), ("unresolved_code", unresolved_code), ("unresolved_reason", unresolved_reason)]
    detail = tuple(tuple(item) for item in unresolved_detail)
    if detail:
        # v0.49: 選ぶと止める選択ごとの (選択, コード, 理由)。選択によって止める理由が違うとき（「ばける」の候補）だけ書く。``check_choices`` が優先して使う
        if not {item[0] for item in detail} <= set(unresolved):
            raise RuntimeError(f"選択ごとの止める理由 {detail} の選択が、選ぶと止める選択 {unresolved} にない（エンジンの不具合）")
        entries.append(("unresolved_detail", detail))
    return push_decision(
        state,
        kind=kind,
        player=player,
        options=options,
        resume="power",
        context=(*entries, *tuple(context)),
        min_choices=min_choices,
        max_choices=max_choices,
    )


def push_stadium_decision(
    state: GameState,
    *,
    stadium: int,
    stage: str,
    kind: str,
    player: int,
    options: Iterable[int],
    context: Iterable[tuple[str, Any]] = (),
    min_choices: int = 1,
    max_choices: int = 1,
    unresolved_choices: Iterable[int] = (),
    unresolved_code: str = "UNRESOLVED_RULING",
    unresolved_reason: str = "",
    unresolved_detail: Iterable[tuple[int, str, str]] = (),
) -> PendingDecision:
    """場のスタジアムの効果の途中で決定を出す（v0.57。再開先 ``"stadium"``。``engine._resume_stadium`` が ``stage`` で続きを選ぶ）。``context`` の ``"stadium"`` は
    スタジアムカードの uid、``"stage"`` は段階（``narrow``: せまいジムが場に出た時の控えポケモンを手札にもどす・``fuchsia``: セキチクシティジムの「おもて」のあとの
    ポケモンを選ぶ・``evolution_heal``: トキワシティジムの進化の時のダメージカウンター。v0.74 から ``energy_stadium``: エネルギースタジアムの「おもて」のあとのトラッシュの基本
    エネルギーカード・``ninja_gym``: キョウの忍者ジムの「おもて」のあとの山札の「キョウのたねポケモン」）。``unresolved_choices`` はトレーナーの決定と同じ（選ぶと止める）。"""
    entries = [("stadium", stadium), ("stage", stage)]
    unresolved = tuple(unresolved_choices)
    if unresolved:
        entries += [("unresolved_choices", unresolved), ("unresolved_code", unresolved_code), ("unresolved_reason", unresolved_reason)]
    detail = tuple(tuple(item) for item in unresolved_detail)
    if detail:
        # v0.93: 選ぶと止める選択ごとの (選択, コード, 理由)（トレーナーの決定と同じ。理由の違う選択があるときだけ書く）
        if not {item[0] for item in detail} <= set(unresolved):
            raise RuntimeError(f"選択ごとの止める理由 {detail} の選択が、選ぶと止める選択 {unresolved} にない（エンジンの不具合）")
        if len({item[1] for item in detail}) > 1:
            entries.append(("unresolved_detail", detail))
    return push_decision(state, kind=kind, player=player, options=options, resume="stadium", context=(*entries, *tuple(context)),
                         min_choices=min_choices, max_choices=max_choices)


def check_choices(decision: PendingDecision, choices: tuple[int, ...]) -> None:
    """選択が決定に合っているかを確かめる（状態は変えない）。

    合わなければ ``IllegalActionError``。選べるものの中でも、原典で扱いを決められないもの
    （``context`` の ``"unresolved_choices"``）を選んだら ``UnsupportedError``。
    """
    if not decision.min_choices <= len(choices) <= decision.max_choices:
        raise IllegalActionError(
            "INVALID_CHOICE_COUNT", f"選ぶ数は {decision.min_choices}〜{decision.max_choices}（{len(choices)} 個選んでいる）"
        )
    if len(set(choices)) != len(choices):
        raise IllegalActionError("DUPLICATE_CHOICE", "同じものを 2 回選んでいる")
    for choice in choices:
        if choice not in decision.options:
            raise IllegalActionError("INVALID_CHOICE", f"{choice!r} はこの決定で選べるものではない（{decision.options}）")
    unresolved = decision.context_value("unresolved_choices", ())
    detail = {item[0]: item for item in decision.context_value("unresolved_detail", ())}  # v0.49: 選択ごとの止める理由
    for choice in choices:
        if choice in detail:
            raise UnsupportedError(detail[choice][1], detail[choice][2])
        if choice in unresolved:
            raise UnsupportedError(
                decision.context_value("unresolved_code", "UNRESOLVED_RULING"),
                decision.context_value("unresolved_reason", "") or f"{choice!r} を選んだときの扱いは原典で決められない",
            )

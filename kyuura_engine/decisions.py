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
# 自分のトラッシュのトレーナーカードを手札に加えるとき、どのカードか（化石の秘密のヤドンの「ゴミあさり」）。選べるものはトラッシュのトレーナーカードの uid
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
# RETURN_TO_DECK（トレーナー。見せる。たねポケモン・進化カードだけ）とは別の決定。再開先は "attack"
HAND_TO_DECK = "hand_to_deck"
# v0.44: カツラのマンキーの「わるいいたずら」の「相手のトラッシュからカードを1枚選び出し、相手の山札の上にのせる」。決めるのはワザを使ったプレイヤーで、選べるものは
# 相手のトラッシュのカードの uid（トラッシュの並び。公開の情報）。1 枚。再開先は "attack"
DISCARD_TO_DECK_TOP = "discard_to_deck_top"

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
) -> PendingDecision:
    """トレーナーの効果の途中で決定を出す（v0.2b）。選ばれたら、そのトレーナーの実装の ``resume`` が呼ばれる。

    ``unresolved_choices``: ``options`` のうち、選んだときの扱いを原典で決められないもの（選ぶと
    ``UnsupportedError(unresolved_code, unresolved_reason)``）。
    """
    entries = [("use", (use.player, use.card, use.card_id))]
    unresolved = tuple(unresolved_choices)
    if unresolved:
        entries += [("unresolved_choices", unresolved), ("unresolved_code", unresolved_code), ("unresolved_reason", unresolved_reason)]
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
) -> PendingDecision:
    """宣言して使う特殊能力の処理の途中で決定を出す（v0.42）。選ばれたら、その特殊能力の実装の ``resume`` が呼ばれる（再開先 ``"power"``）。

    ``context`` は ``("use", (プレイヤー, 場のポケモンの番号, カード id, 特殊能力の位置))`` と、``unresolved_choices``（トレーナーの決定と同じ。選ぶと
    ``UnsupportedError(unresolved_code, unresolved_reason)``）と、実装が決定をまたいで使う値（``context``）。決定の形はトレーナーの決定（v0.2b）と同じ考え方で、
    実装が ``PowerEffect.decision_problems`` で宣言する。
    """
    entries = [("use", (use.player, use.pokemon_id, use.key.card_id, use.key.power_index))]
    if getattr(use, "return_to", None) is not None:
        # v0.43: 場に出したトレーナーの効果の途中で使う特殊能力（ポケモン育て屋さんで場に出たわるいカイリューの［てしたをよぶ］）。終わったらその処理にもどる
        entries.append(("return_to", use.return_to))
    unresolved = tuple(unresolved_choices)
    if unresolved:
        entries += [("unresolved_choices", unresolved), ("unresolved_code", unresolved_code), ("unresolved_reason", unresolved_reason)]
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
    for choice in choices:
        if choice in unresolved:
            raise UnsupportedError(
                decision.context_value("unresolved_code", "UNRESOLVED_RULING"),
                decision.context_value("unresolved_reason", "") or f"{choice!r} を選んだときの扱いは原典で決められない",
            )

"""v0.28・v0.29: 既存の効果の型の登録だけで加えたポケモン（v0.28 の 10 枚・v0.29 の 14 枚）と、v0.30 のエネルギーをトラッシュしてダメージを
与えるワザで加えたポケモン（5 枚）の検証用デッキの対戦（docs/existing-effect-pokemon-v0.28.md 5 章・docs/existing-effect-pokemon-v0.29.md 4.2・
docs/discard-energy-attacks-v0.30.md 6 章）。

C 段階の道具（ふだんのテストは tests/test_existing_effect_games_v0_28.py・tests/test_existing_effect_games_v0_29.py・
tests/test_discard_energy_games_v0_30.py が数局だけ走らせる）。対戦相手の AI ではなく、カードの強さ・採用価値・
釣り合いを判断する道具でもない。勝敗は、対戦が通常の終わり方をしたかの確かめにだけ使う。

使い方::

    python3 tools/existing_effect_games.py --seeds 10 --out <作業用の場所>/existing.json   # 3 組 × 2 席 × 10 seed = 60 局
    python3 tools/existing_effect_games.py --batch v0.29 --seeds 10 --out <作業用の場所>/existing29.json   # v0.29 の 3 組（60 局）
    python3 tools/existing_effect_games.py --batch v0.30 --seeds 10 --out <作業用の場所>/existing30.json   # v0.30 の 3 組（60 局）

検証用デッキ（``DECKS``。公開の固定のデッキ ``kyuura_engine.decks`` には入れない。どれも対応済みのカードと基本エネルギーだけの 60 枚）:

- ``W28``（水・無色）: ラプラス 3・ヒトデマン 3・スターミー 2・トサキント 3・アズマオウ 2・シェルダー 3・ラッキー 2、トレーナー 12（マサキ・
  ポケモンいれかえ・きずぐすり・プラスパワー・ディフェンダー・突風 2 枚ずつ）、水エネルギー 30。
- ``G28``（草・超・無色）: カイロス 4・タマタマ 4・プリン 4・スリープ 4、トレーナーは ``W28`` と同じ 12、草エネルギー 16・超エネルギー 16。
- 組（``PAIRINGS``）: ``W28`` 対 ``G28``（新しいカードどうし）・``W28`` 対 ``B2``（第2版のフシギバナ・パラセクト）・``G28`` 対 ``A2``（第2版の
  エビワラー・ジュゴン）。どれも同じ seed で、席を入れかえて 1 局ずつ（先攻・後攻は seed の偶奇）。
- v0.29（``--batch v0.29``。``PAIRINGS_V0_29``）: ``GW29``（草・水）: アーボ・ズバット・ナゾノクサ・ドガース・タケシのズバット・ニョロモ・
  カスミのトサキント 3 枚ずつ、トレーナーは ``W28`` と同じ 12、草エネルギー 16・水エネルギー 11。``LF29``（雷・闘・無色）: ビリリダマ・マチスの
  コイル・マチスのビリリダマ・ワンリキー・タケシのイシツブテ・ミニリュウ・タケシのベロリンガ 3 枚ずつ、同じトレーナー 12、雷エネルギー 14・
  闘エネルギー 13。組は ``GW29`` 対 ``LF29``・``GW29`` 対 ``B2``・``LF29`` 対 ``A2``。v0.28 のデッキに v0.29 のカードは入っていないので、
  v0.28 の組の結果は v0.28 と同じ。
- v0.30（``--batch v0.30``。``PAIRINGS_V0_30``）: ``F30``（炎）: ヒトカゲ 4・リザード 3・ガーディ（第1弾。v0.2a から）4・ウインディ 3・ブーバー 3・
  第4弾ロケット団のポニータ 4、トレーナーは ``W28`` と同じ 12、炎エネルギー 27。組は ``F30`` 対 ``B2``（第2版のフシギバナ・パラセクト）・``F30`` 対
  ``A2``（第2版のエビワラー・ジュゴン）・``F30`` 対 ``G28``。v0.28・v0.29 のデッキに v0.30 のカードは入っていないので、その組の結果は変わらない。
- v0.32（``--batch v0.32``。``PAIRINGS_V0_32``。docs/bench-search-counter-drain-v0.32.md）: ``G32``（草）: ニドラン♀ 4・ニドリーナ 3・ナゾノクサ（第2弾）3・
  第4弾のナゾノクサ 1・マダツボミ 4・ウツドン 3・コンパン 3・ズバット（化石の秘密）3・ゴルバット 2、トレーナー 12、草エネルギー 22。``W32``（水・超）:
  コイキング 4・ギャラドス 3・クラブ 4・キングラー 3・ルージュラ 4、トレーナー 12、水エネルギー 20・超エネルギー 10。組は ``G32`` 対 ``W32``・``G32`` 対
  ``A2``・``W32`` 対 ``B2``。山札からベンチに出すワザの決定は元の手順のまま（1 つ目の選べるもの）。ベンチに空きがなくて使えないワザ（``BENCH_FULL``）と
  CD4 で止まったワザは、場から確かめてから別の操作を続ける（``V031_STOPS``）。前の版のデッキに v0.32 のカードは入っていないので、その組の結果は変わらない。
- v0.33（``--batch v0.33``。``PAIRINGS_V0_33``。docs/cd4-opponent-energy-coins-v0.33.md）: ``N33``（草・闘）: ニドラン♂ 4・ニドリーノ 3・サカキのニドラン♀ 3・
  ナツメのコンパン 3・タケシのディグダ 3・タケシのサイホーン 3・カツラのサイホーン 3、トレーナー 12、草エネルギー 12・闘エネルギー 12・超エネルギー 2。
  ``W33``（水）: コダック（ロケット団）4・ゴルダック（化石の秘密）3・イーブイ 4・わるいシャワーズ 3・シェルダー 4・パルシェン 3、トレーナー 12、水エネルギー 22・
  超エネルギー 5。``C33``（無色・雷）: ミニリュウ（第1弾・ロケット団）2 枚ずつ・ハクリュー 3・コラッタ 4・わるいラッタ 3・マチスのコイル（PMCG5-039）4・
  マチスのオニスズメ 3・カツラのドードー 3、トレーナー 12、雷エネルギー 24。組は ``N33`` 対 ``W33``・``C33`` 対 ``N33``・``W33`` 対 ``C33``。v0.33 のワザの
  決定（相手のエネルギーカード・相手の控え）は元の手順のまま（1 つ目の選べるもの）。かけぬけるの控えを選ぶ前に「ダメージを受けたとき」の効果が残る場面
  （エンジンの未対応）は、場から確かめてから別の操作を続ける（``V031_STOPS``）。前の版のデッキに v0.33 のカードは入っていないので、その組の結果は変わらない。
  v0.34 でこの場面は決定をまたいで処理するようにしたので、止まらない（``V031_STOPS`` から外した）。
- v0.34（``--batch v0.34``。``PAIRINGS_V0_34``。docs/barrier-resume-coin-bonus-v0.34.md）: ``F34``（炎・雷）: ポニータ（第1弾・ロケット団）2 枚ずつ・ギャロップ 3・
  イーブイ 4・ブースター 2・サンダース 2・タケシのロコン 3・エレブー 3、トレーナー 12、炎エネルギー 15・雷エネルギー 12。``G34``（草・超）: ドガース 4・
  ニドラン♂ 4・ニドリーノ 3・ニドキング 2・タマタマ 4・ナッシー 3・サカキのカイロス 3、トレーナー 12、草エネルギー 20・超エネルギー 5。``C34``（無色・闘・水）:
  ケンタロス 3・カツラのガルーラ 3・カラカラ 4・ガラガラ 3・イーブイ 3・シャワーズ 3・ディグダ（第1弾。たすけをよぶで選べる闘のたねポケモン）2、トレーナー 12、
  闘エネルギー 15・水エネルギー 12。組は ``F34`` 対 ``G34``・``C34`` 対 ``F34``・``G34`` 対 ``C34``。v0.34 のワザの決定（テレポート・うしろなげ・たすけをよぶ・
  かえんほうしゃのトラッシュ）は元の手順のまま（1 つ目の選べるもの）。原典で決められないとして止まったワザ（TP3・NK5・HC4）は、場から確かめてから別の操作を
  続ける（``V031_STOPS``）。前の版のデッキに v0.34 のカードは入っていないので、その組の結果は変わらない（ねばりつく・じごくがためはどのデッキにもない）。
- v0.35（``--batch v0.35``。``PAIRINGS_V0_35``。docs/coin-groups-damage-order-v0.35.md）: ``S35``（無色・水）: マチスのコラッタ 4・マチスのラッタ 3・
  カスミのニョロモ 4・カスミのニョロゾ 3・カツラのケンタロス 3、トレーナー 12、水エネルギー 31。組は ``S35`` 対 ``C34``（カラカラのなきつく）・``G34``
  （ナッシーのたまなげMAX）対 ``S35``・``S35`` 対 ``A2``。v0.35 のワザの決定（ドわすれのワザ・ダメージの計算の順番・はかいのうずのエネルギー）は元の手順の
  まま（1 つ目の選べるもの）。あわあわ・ドわすれで使えないワザを選んだときは、場から確かめてから別の操作を続ける（``V031_STOPS`` の ``ATTACK_LOCKED``）。
  前の版のデッキに v0.35 のカードは入っていないので、その組の結果は変わらない。
- v0.37（``--batch v0.37``。``PAIRINGS_V0_37``。docs/fifteen-reused-effects-v0.37.md）: ``F37``（闘）: サイホーン 4・タケシのサンド 4・タケシのイワーク 4・
  ディグダ（第1弾）4・ダグトリオ 3、トレーナー 12、闘エネルギー 29（どのポケモンも闘に弱点・抵抗力を持たないので、じしんは JS1 で止まらない）。``W37``（水）:
  ニョロモ（第1弾）4・ニョロゾ 3・ニョロボン 3・カスミのコイキング 4、トレーナー 12、水エネルギー 24・闘エネルギー 10（みずでっぽうは「水」が 3 つ以上なら HC4）。
  ``L37``（雷・無色）: ピカチュウ（第1弾）4・ライチュウ 3・ニャース 4・ペルシアン 3・ロケット団のイーブイ 4、トレーナー 12、雷エネルギー 30。``G37``（草・超）:
  化石の秘密のベトベター 4・化石の秘密のアーボ 4・キョウのモンジャラ 4・ナツメのスリープ 4、トレーナー 12、草エネルギー 20・超エネルギー 12。組は ``F37`` 対
  ``L37``・``W37`` 対 ``G37``・``L37`` 対 ``W37``・``G37`` 対 ``F37``。v0.37 のワザの決定（ドわすれのワザ・うずしおのエネルギー）は元の手順のまま（1 つ目の
  選べるもの）。JS1・HC4 で止まったワザは、場から確かめてから別の操作を続ける（``V031_STOPS``）。前の版のデッキに v0.37 のカードは入っていないので、その組の
  結果は変わらない。
- v0.38（``--batch v0.38``。``PAIRINGS_V0_38``。docs/bench-switch-combined-v0.38.md）: ``F38``（闘・炎・無色）: サワムラー 3・サイホーン 4・サイドン 3・
  カツラのポニータ 3・カツラのギャロップ 3・タケシのロコン（PMCG5-017）3・キョウのポッポ（PMCG6-067。進化先のないデッキ）4、トレーナー 12、闘エネルギー 14・
  炎エネルギー 11。``G38``（草）: エリカのモンジャラ 3・
  タケシのズバット 3・タケシのゴルバット 3・化石の秘密のアーボ 3・アーボック 3・キョウのビードル 3・サカキのニドラン♀ 4・サカキのニドリーナ 4、トレーナー 12、
  草エネルギー 22。``C38``（無色・水・超）: フリーザー 4・ナツメのポリゴン 4・ロケット団のケーシィ 4・キョウのポッポ（PMCG6-062）4・
  キョウのピジョン 3、トレーナー 12、水エネルギー 16・超エネルギー 13。組は ``F38`` 対 ``G38``・``G38`` 対 ``C38``・``C38`` 対 ``F38``・``C38`` 対 ``P31``
  （ピッピ・ピクシー・カスミのコダックが、でんれい・いなくなるなどを自分のワザとして使う）。v0.38 のワザの決定（控えの選択・入れ替え・かわりの対戦
  ポケモン・山札をさがす）は元の手順のまま（1 つ目の選べるもの）。のびるキックの使うための条件（``NO_OPPONENT_BENCH``）・GK1 で止まったワザは、場から
  確かめてから別の操作を続ける（``V031_STOPS``）。v0.38 のカードは、使えるワザをどれも 1 回以上使い、まだ使っていないワザがエネルギーの不足で使えないとき、
  その番はワザを使わずに番を終える（でんれいは自分を山札にもどすので、つばさでうつを使うための手順）。前の版のデッキに v0.38 のカードは入っていないので、
  その組の結果は変わらない。
- v0.39（``--batch v0.39``。``PAIRINGS_V0_39``。docs/selfdestruct-spread-count-v0.39.md）: ``L39``（雷）: コイル（第1弾・ロケット団）2 枚ずつ・レアコイル（第1弾・
  化石の秘密）2 枚ずつ・ピカチュウ（ジャングル）4・ライチュウ（化石の秘密）3・ビリリダマ（第1弾）4・マルマイン 3、トレーナー 12、雷エネルギー 26。``G39``（草）:
  キョウのドガース（PMCG6-008）4・キョウのマタドガス 3・ドガース（第1弾）4・マタドガス（化石の秘密）3・エリカのパラス 4、トレーナー 12、草エネルギー 30。
  ``C39``（無色・水）: ポッポ 4・プリン 4・プクリン 3・カスミのニョロモ 4・カスミのニョロゾ 3・カスミのニョロボン 2、トレーナー 12、水エネルギー 28。``N39``（草）:
  ニドラン♀ 4・ニドリーナ 3・ニドクイン 3・ニドラン♂ 4・ニドリーノ 3・ニドキング 2、トレーナー 12、草エネルギー 29。組は ``L39`` 対 ``C39``・``C39`` 対 ``G39``・
  ``G39`` 対 ``N39``・``N39`` 対 ``L39``（どのデッキも 2 組に入る）。v0.39 のワザの決定（スパーク・ギガスパークの控えの選択）は、原典で決められない選択
  （``unresolved_choices``。JS1）を選ばず、ギガスパークは 1〜3 匹を順に選ぶ（0 匹は GS1 なので選ばない）。かぜおこしの入れ替えは元の手順のまま（1 つ目の
  選べるもの）。JS1・TP3 で止まったワザは、場から確かめてから別の操作を続ける（``V031_STOPS``）。v0.39 のカードも、使っていないワザのためにエネルギーを
  ためる手順（v0.38 と同じ）を使う。前の版のデッキに v0.39 のカードは入っていないので、その組の結果は変わらない。
- v0.40（``--batch v0.40``。``PAIRINGS_V0_40``。docs/count-condition-switch-return-v0.40.md）: ``G40``（草）: キョウのズバット 4・キョウのゴルバット 3・
  ドガース（第1弾）4・わるいマタドガス 3・エリカのマダツボミ（PMCG5-005）4・エリカのウツドン 3、トレーナー 12、草エネルギー 27。``N40``（草）: サカキのニドラン♂ 4・
  サカキのニドリーノ 3・サカキのニドキング 2・サカキのニドラン♀ 4・サカキのニドリーナ 3・サカキのニドクイン 2・ドガース（ロケット団）3、トレーナー 12、
  草エネルギー 27。``F40``（闘）: ワンリキー（ロケット団）4・わるいゴーリキー 3・わるいカイリキー 2・マンキー 4・オコリザル 3・タケシのマンキー 4、トレーナー 12、
  闘エネルギー 28。``P40``（超・水）: スリープ 4・わるいスリーパー 3・カスミのタッツー（PMCG5-025）4・カスミのシードラ 3、トレーナー 12、超エネルギー 17・
  水エネルギー 17。組は ``G40`` 対 ``N40``・``N40`` 対 ``F40``・``F40`` 対 ``P40``・``P40`` 対 ``G40``（どのデッキも 2 組に入る）。v0.40 のワザの決定は
  ``_v040_decision``（むれでおそうの出す数は番の番号で 選べるだけ・0 枚・1 枚、ひきずりだす・さそってとかすの控えは決定のたびに 最後・最初 を順に）。使うための
  条件で拒否されたワザ（いかりのいちげきの ``NOT_ENOUGH_DAMAGE_COUNTERS``・すごむの ``ATTACK_PREVENTED``・``NO_OPPONENT_BENCH``）は、場から確かめてから別の操作を
  続ける（``V031_STOPS``）。v0.40 のカードも、使っていないワザのためにエネルギーをためる手順（v0.38 と同じ）を使う。前の版のデッキに v0.40 のカードは入っていない
  ので、その組の結果は変わらない。

手順: tools/preset_deck_games.py の ``make_policy``（v0.26 から変えていない手順。決定ごとの持ち主・使用中のカードの確かめ ``check_…`` も数える）に、
v0.28・v0.29 のカード（``TARGETS``）のワザの選び方だけを重ねる（``make_policy``）。バトル場がそのカードで、元の手順がワザか番の終わりを選んだとき、払えるワザ
（この番に拒否されたワザを除く）のうち、その局でそのカードがまだ使った回数の少ないワザを選ぶ（同じなら、ダメージの目安の数字が大きいもの →
位置の小さいもの）。ダメージを与えないワザ（さいみんじゅつ・こもりうた・ちょうおんぱ・まるまる・からをとじる・じこさいせい）も使うための手順で、
強さを目指したものではない。そのほかの判断（エネルギー・進化・トレーナー・にげる・決定への答え）は元の手順のまま。

終わり方の分類は tools/preset_deck_games.py と同じ（通常の勝敗・サドンデス・既知の未解決の裁定による停止・手数の上限・想定外の拒否・内部エラー）。
原典で決められないとして拒否された操作（``UNRESOLVED_…``）のあと別の操作で続けた回数は、終わり方とは別に数える。監査（``audit``）は、
受け付けた操作の列を ``new_game`` からやり直してログが同じか・不変条件・ログの監査・書き出しの監査・トレーナーのログの並び・決定ごとの確かめ。
v0.28 のカードの動きはログだけから数える（``card_uses``。選ぶ操作を変えない）。
"""

from __future__ import annotations

import argparse
import json
import sys
import time
import traceback
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from kyuura_engine import (  # noqa: E402
    EndTurn, IllegalActionError, Phase, ResolveDecision, Retreat, UnsupportedError, UseAttack, UsePokemonPower, apply_command, check_invariants,
    new_game, preset_deck,
)
from kyuura_engine.cards import EnergyType, can_pay_cost  # noqa: E402
from kyuura_engine.decisions import ATTACH_FROM_DISCARD, BENCH_FROM_DECK, DISCARD_ENERGY, FORCED_SWITCH, SELECT_ATTACK, SELECT_POKEMON  # noqa: E402
from kyuura_engine.effects import AttackKey as E_AttackKey, AttackUse, preview_attack_damage, working_counterattack_power  # noqa: E402
from kyuura_engine.persistent import (  # noqa: E402
    attack_barrier, attack_coin_checks, attack_locked, cannot_attack, cannot_attack_while_source_active, cannot_retreat, destiny_bond,
    reduced_damage_to_source, retaliation,
)
from tests.log_audit import log_problems, serialization_problems  # noqa: E402
from tests.v017_games import play_game  # noqa: E402
from tools import preset_deck_games as driver  # noqa: E402

LAPRAS, STARMIE, GOLDEEN, SEAKING, PINSIR = "PMCG3-022", "PMCG1-026", "PMCG2-021", "PMCG2-022", "PMCG2-018"
EXEGGCUTE, JIGGLYPUFF, CHANSEY, DROWZEE, SHELLDER = "PMCG2-006", "PMCG2-035", "PMCG1-068", "PMCG1-045", "PMCG3-012"
V0_28 = (LAPRAS, STARMIE, GOLDEEN, SEAKING, PINSIR, EXEGGCUTE, JIGGLYPUFF, CHANSEY, DROWZEE, SHELLDER)
# v0.29（kyuura データの採用。どれもたねポケモン）
POLIWAG, ROCKET_EKANS, ROCKET_ZUBAT, ROCKET_ODDISH, ROCKET_KOFFING = "PMCG1-024", "PMCG4-001", "PMCG4-002", "PMCG4-003", "PMCG4-005"
ROCKET_VOLTORB, ROCKET_MACHOP, ROCKET_DRATINI, BROCKS_ZUBAT, MISTYS_GOLDEEN = "PMCG4-027", "PMCG4-040", "PMCG4-051", "PMCG5-001", "PMCG5-026"
LT_SURGES_MAGNEMITE, LT_SURGES_VOLTORB, BROCKS_GEODUDE, BROCKS_LICKITUNG = "PMCG5-037", "PMCG5-038", "PMCG5-046", "PMCG5-061"
V0_29 = (POLIWAG, ROCKET_EKANS, ROCKET_ZUBAT, ROCKET_ODDISH, ROCKET_KOFFING, ROCKET_VOLTORB, ROCKET_MACHOP, ROCKET_DRATINI, BROCKS_ZUBAT,
         MISTYS_GOLDEEN, LT_SURGES_MAGNEMITE, LT_SURGES_VOLTORB, BROCKS_GEODUDE, BROCKS_LICKITUNG)
# v0.30（エネルギーをトラッシュしてダメージを与えるワザ。リザードはヒトカゲから、ウインディはガーディから進化）
CHARMANDER, CHARMELEON, ARCANINE, MAGMAR, ROCKET_PONYTA = "PMCG1-014", "PMCG1-017", "PMCG1-019", "PMCG1-020", "PMCG4-013"
V0_30 = (CHARMANDER, CHARMELEON, ARCANINE, MAGMAR, ROCKET_PONYTA)
GROWLITHE = "PMCG1-018"
# v0.31（v0.30 で保留した 22 枚と、進化元として加えた 7 枚。docs/held-cards-v0.31.md）
NINETALES, CHARIZARD, ZAPDOS, GASTLY1, MEWTWO, CLEFABLE = "PMCG1-022", "PMCG1-021", "PMCG1-042", "PMCG1-044", "PMCG1-050", "PMCG2-044"
MOLTRES, SLOWPOKE, DARK_RAPIDASH, DARK_CHARMELEON, DARK_FLAREON, DARK_CHARIZARD = "PMCG3-009", "PMCG3-027", "PMCG4-014", "PMCG4-015", "PMCG4-016", "PMCG4-017"
DARK_GOLDUCK, DARK_ELECTRODE, MISTYS_GOLDUCK, LT_SURGES_ELECTABUZZ = "PMCG4-022", "PMCG4-028", "PMCG5-032", "PMCG5-041"
BLAINES_CHARMANDER, BLAINES_CHARMELEON, BLAINES_MAGMAR, BLAINES_NINETALES, BLAINES_ARCANINE = "PMCG6-025", "PMCG6-029", "PMCG6-031", "PMCG6-033", "PMCG6-034"
LT_SURGES_RAICHU = "PMCG6-041"
V0_31_TARGETS = (NINETALES, CHARIZARD, ZAPDOS, GASTLY1, MEWTWO, CLEFABLE, MOLTRES, SLOWPOKE, DARK_RAPIDASH, DARK_CHARMELEON, DARK_FLAREON,
                 DARK_CHARIZARD, DARK_GOLDUCK, DARK_ELECTRODE, MISTYS_GOLDUCK, LT_SURGES_ELECTABUZZ, BLAINES_CHARMANDER, BLAINES_CHARMELEON,
                 BLAINES_MAGMAR, BLAINES_NINETALES, BLAINES_ARCANINE, LT_SURGES_RAICHU)
CLEFAIRY, EEVEE, PSYDUCK, MISTYS_PSYDUCK, BLAINES_VULPIX, BLAINES_GROWLITHE, LT_SURGES_PIKACHU = (
    "PMCG1-067", "PMCG2-037", "PMCG4-019", "PMCG5-021", "PMCG6-026", "PMCG6-027", "PMCG5-036")
V0_31_DEPENDENCIES = (CLEFAIRY, EEVEE, PSYDUCK, MISTYS_PSYDUCK, BLAINES_VULPIX, BLAINES_GROWLITHE, LT_SURGES_PIKACHU)
V0_31 = V0_31_TARGETS + V0_31_DEPENDENCIES
VULPIX = "PMCG1-015"
# v0.32（山札からベンチに出す・ダメージカウンターでダメージが決まる・与えたぶん回復するワザのポケモンと進化先。docs/bench-search-counter-drain-v0.32.md）
NIDORAN_F, ODDISH, BELLSPROUT, KRABBY, NIDORINA, WEEPINBELL = "PMCG2-001", "PMCG2-002", "PMCG2-005", "PMCG3-013", "PMCG2-008", "PMCG2-011"
MAGIKARP, GYARADOS, KINGLER, JYNX, VENONAT, FOSSIL_ZUBAT, GOLBAT = "PMCG1-031", "PMCG1-034", "PMCG3-019", "PMCG1-048", "PMCG2-004", "PMCG3-002", "PMCG3-005"
V0_32 = (NIDORAN_F, ODDISH, BELLSPROUT, KRABBY, NIDORINA, WEEPINBELL, MAGIKARP, GYARADOS, KINGLER, JYNX, VENONAT, FOSSIL_ZUBAT, GOLBAT)
# v0.33（相手のエネルギーカードをトラッシュする・コインで失敗する／ダメージを与えられない・控えにもダメージを与えるワザのポケモンと進化先。
# docs/cd4-opponent-energy-coins-v0.33.md）
DRAGONAIR, FOSSIL_GOLDUCK, DARK_VAPOREON, LT_SURGES_MAGNEMITE_30, SABRINAS_VENONAT = "PMCG1-069", "PMCG3-016", "PMCG4-023", "PMCG5-039", "PMCG6-006"
NIDORAN_M, NIDORINO, CLOYSTER, DARK_RATICATE, BROCKS_DIGLETT = "PMCG1-005", "PMCG1-010", "PMCG3-018", "PMCG4-046", "PMCG5-044"
BROCKS_RHYHORN, LT_SURGES_SPEAROW, GIOVANNIS_NIDORAN_F, BLAINES_RHYHORN, BLAINES_DODUO = "PMCG5-049", "PMCG5-057", "PMCG6-003", "PMCG6-058", "PMCG6-064"
V0_33 = (DRAGONAIR, FOSSIL_GOLDUCK, DARK_VAPOREON, LT_SURGES_MAGNEMITE_30, SABRINAS_VENONAT, NIDORAN_M, NIDORINO, CLOYSTER, DARK_RATICATE,
         BROCKS_DIGLETT, BROCKS_RHYHORN, LT_SURGES_SPEAROW, GIOVANNIS_NIDORAN_F, BLAINES_RHYHORN, BLAINES_DODUO)
# v0.34（バリアーに対するコインの見直し・ダメージのあとの決定をまたぐ処理と合わせて加えた 14 枚。docs/barrier-resume-coin-bonus-v0.34.md）
RAPIDASH, FLAREON, VAPOREON, JOLTEON, ELECTABUZZ, TAUROS = "PMCG2-019", "PMCG2-020", "PMCG2-023", "PMCG2-026", "PMCG1-041", "PMCG2-042"
BROCKS_VULPIX, GIOVANNIS_PINSIR, BLAINES_KANGASKHAN, KOFFING, NIDOKING = "PMCG5-018", "PMCG6-024", "PMCG6-069", "PMCG1-006", "PMCG1-013"
EXEGGUTOR, CUBONE, MAROWAK, PONYTA, DIGLETT = "PMCG2-012", "PMCG2-029", "PMCG2-032", "PMCG1-016", "PMCG1-052"
V0_34 = (RAPIDASH, FLAREON, VAPOREON, JOLTEON, ELECTABUZZ, TAUROS, BROCKS_VULPIX, GIOVANNIS_PINSIR, BLAINES_KANGASKHAN, KOFFING, NIDOKING,
         EXEGGUTOR, CUBONE, MAROWAK)
# v0.35（可変枚数のコインの先読み・ダメージの計算の順番の決定と合わせて加えた 5 枚。docs/coin-groups-damage-order-v0.35.md）
LT_SURGES_RATTATA, LT_SURGES_RATICATE, MISTYS_POLIWAG, MISTYS_POLIWHIRL, BLAINES_TAUROS = "PMCG5-056", "PMCG5-059", "PMCG5-022", "PMCG5-029", "PMCG6-065"
V0_35 = (LT_SURGES_RATTATA, LT_SURGES_RATICATE, MISTYS_POLIWAG, MISTYS_POLIWHIRL, BLAINES_TAUROS)
DRATINI, RATTATA, MACHAMP, ROCKETS_SNORLAX = "PMCG1-065", "PMCG1-060", "PMCG1-057", "PMCG6-073"
# v0.36（p.309 の手順 4 のコイン・「にげる」ことができない効果・自分を山札にもどす効果と合わせて加えた 11 枚。docs/sand-attack-retreat-lock-v0.36.md）
SANDSHREW, SANDSLASH, FOSSIL_MAGMAR, HORSEA, MISTYS_HORSEA = "PMCG1-051", "PMCG3-036", "PMCG3-008", "PMCG3-014", "PMCG5-025"
KOGAS_PIDGEY, DARK_JOLTEON, MISTYS_SEEL, LT_SURGES_FEAROW, KOGAS_KOFFING, ERIKAS_BELLSPROUT = (
    "PMCG6-062", "PMCG4-029", "PMCG5-023", "PMCG5-064", "PMCG6-015", "PMCG5-005")
V0_36 = (SANDSHREW, SANDSLASH, FOSSIL_MAGMAR, HORSEA, MISTYS_HORSEA, KOGAS_PIDGEY, DARK_JOLTEON, MISTYS_SEEL, LT_SURGES_FEAROW, KOGAS_KOFFING,
         ERIKAS_BELLSPROUT)
# v0.37（既存の効果の再利用を中心にした 15 枚。docs/fifteen-reused-effects-v0.37.md）。進化元はピカチュウ・ディグダ・ニョロモ（第1弾）・ニャース（v0.37）
RHYHORN, FOSSIL_GRIMER, ROCKET_EEVEE, BROCKS_SANDSHREW, SABRINAS_DROWZEE = "PMCG2-030", "PMCG3-003", "PMCG4-049", "PMCG5-043", "PMCG6-045"
RAICHU, DUGTRIO, POLIWHIRL, POLIWRATH, FOSSIL_EKANS = "PMCG1-038", "PMCG1-056", "PMCG1-028", "PMCG1-033", "PMCG3-001"
BROCKS_ONIX, MEOWTH, KOGAS_TANGELA, MISTYS_MAGIKARP, PERSIAN = "PMCG5-048", "PMCG2-036", "PMCG6-009", "PMCG5-028", "PMCG2-039"
V0_37 = (RHYHORN, FOSSIL_GRIMER, ROCKET_EEVEE, BROCKS_SANDSHREW, SABRINAS_DROWZEE, RAICHU, DUGTRIO, POLIWHIRL, POLIWRATH, FOSSIL_EKANS, BROCKS_ONIX,
         MEOWTH, KOGAS_TANGELA, MISTYS_MAGIKARP, PERSIAN)
# v0.38（控えへのダメージ・入れ替え・同じコインの複数の効果・軽減・山札にもどる効果の 15 枚。docs/bench-switch-combined-v0.38.md）。進化元はタケシのズバット（v0.29）・
# 化石の秘密のアーボ・サイホーン（v0.37）・サカキのニドラン♀（v0.33）・キョウのポッポ（v0.36・v0.38）・カツラのポニータ（v0.38）
ARTICUNO, HITMONLEE, ERIKAS_TANGELA, BROCKS_VULPIX_50, BROCKS_GOLBAT = "PMCG3-023", "PMCG3-039", "PMCG5-006", "PMCG5-017", "PMCG5-008"
ARBOK, RHYDON, BLAINES_PONYTA, BLAINES_RAPIDASH, KOGAS_PIDGEOTTO = "PMCG3-004", "PMCG2-033", "PMCG6-028", "PMCG6-030", "PMCG6-070"
KOGAS_WEEDLE, GIOVANNIS_NIDORINA, SABRINAS_PORYGON, ROCKET_ABRA, KOGAS_PIDGEY_40 = "PMCG6-001", "PMCG6-012", "PMCG6-066", "PMCG4-031", "PMCG6-067"
V0_38 = (ARTICUNO, HITMONLEE, ERIKAS_TANGELA, BROCKS_VULPIX_50, BROCKS_GOLBAT, ARBOK, RHYDON, BLAINES_PONYTA, BLAINES_RAPIDASH, KOGAS_PIDGEOTTO,
         KOGAS_WEEDLE, GIOVANNIS_NIDORINA, SABRINAS_PORYGON, ROCKET_ABRA, KOGAS_PIDGEY_40)
PIKACHU = "PMCG1-035"
# v0.39（じばく・控えへのダメージ・場のポケモンの数でダメージが決まるワザの 15 枚。docs/selfdestruct-spread-count-v0.39.md）。進化元はコイル・ドガース・ピカチュウ・
# ビリリダマ（第1弾）・カスミのニョロゾ（v0.35）・プリン（v0.28）・ニドリーナ（v0.32）・キョウのドガース
MAGNEMITE, MAGNETON, FOSSIL_WEEZING, FOSSIL_MAGNETON, JUNGLE_PIKACHU = "PMCG1-036", "PMCG1-039", "PMCG3-006", "PMCG3-025", "PMCG2-024"
FOSSIL_RAICHU, ELECTRODE, KOGAS_KOFFING_40, MISTYS_POLIWRATH, ROCKET_MAGNEMITE = "PMCG3-024", "PMCG2-025", "PMCG6-008", "PMCG6-039", "PMCG4-026"
WIGGLYTUFF, NIDOQUEEN, KOGAS_WEEZING, PIDGEY, ERIKAS_PARAS = "PMCG2-045", "PMCG2-013", "PMCG6-016", "PMCG1-059", "PMCG5-004"
V0_39 = (MAGNEMITE, MAGNETON, FOSSIL_WEEZING, FOSSIL_MAGNETON, JUNGLE_PIKACHU, FOSSIL_RAICHU, ELECTRODE, KOGAS_KOFFING_40, MISTYS_POLIWRATH,
         ROCKET_MAGNEMITE, WIGGLYTUFF, NIDOQUEEN, KOGAS_WEEZING, PIDGEY, ERIKAS_PARAS)
VOLTORB = "PMCG1-037"
# v0.40（場の数・条件付きの効果・入れ替え・カードの移動の 15 枚。docs/count-condition-switch-return-v0.40.md）。進化元はキョウのズバット・ドガース・スリープ・
# サカキのニドラン♂・サカキのニドリーノ・サカキのニドリーナ（v0.38）・ワンリキー・わるいゴーリキー・エリカのマダツボミ・カスミのタッツー・マンキー
KOGAS_ZUBAT, KOGAS_GOLBAT, DARK_WEEZING, DARK_HYPNO, GIOVANNIS_NIDORAN_M = "PMCG6-005", "PMCG6-014", "PMCG4-011", "PMCG4-037", "PMCG6-004"
GIOVANNIS_NIDORINO, GIOVANNIS_NIDOKING, GIOVANNIS_NIDOQUEEN, DARK_MACHOKE, DARK_MACHAMP = "PMCG6-013", "PMCG6-021", "PMCG6-020", "PMCG4-042", "PMCG4-044"
ERIKAS_WEEPINBELL, MISTYS_SEADRA, BROCKS_MANKEY, MANKEY, PRIMEAPE = "PMCG5-011", "PMCG5-034", "PMCG5-045", "PMCG4-039", "PMCG2-031"
V0_40 = (KOGAS_ZUBAT, KOGAS_GOLBAT, DARK_WEEZING, DARK_HYPNO, GIOVANNIS_NIDORAN_M, GIOVANNIS_NIDORINO, GIOVANNIS_NIDOKING, GIOVANNIS_NIDOQUEEN,
         DARK_MACHOKE, DARK_MACHAMP, ERIKAS_WEEPINBELL, MISTYS_SEADRA, BROCKS_MANKEY, MANKEY, PRIMEAPE)
TARGETS = V0_28 + V0_29 + V0_30 + V0_31 + V0_32 + V0_33 + V0_34 + V0_35 + V0_36 + V0_37 + V0_38 + V0_39 + V0_40  # ワザの選び方を重ね、動きを数えるカード
STARYU = "PMCG1-025"
GRASS, FIRE, WATER, LIGHTNING, PSYCHIC, FIGHTING = "PMCG1-097", "PMCG1-098", "PMCG1-099", "PMCG1-100", "PMCG1-101", "PMCG1-102"
SWITCH = "PMCG1-073"
TRAINERS = ((driver.BILL, 2), (SWITCH, 2), (driver.POTION, 2), (driver.PLUSPOWER, 2), (driver.DEFENDER, 2), (driver.GUST, 2))
# 検証用デッキ（(カード id, 枚数) の並び）。第2版の固定のデッキはそのまま使う
DECKS = {
    "W28": ((LAPRAS, 3), (STARYU, 3), (STARMIE, 2), (GOLDEEN, 3), (SEAKING, 2), (SHELLDER, 3), (CHANSEY, 2), *TRAINERS, (WATER, 30)),
    "G28": ((PINSIR, 4), (EXEGGCUTE, 4), (JIGGLYPUFF, 4), (DROWZEE, 4), *TRAINERS, (GRASS, 16), (PSYCHIC, 16)),
    "GW29": ((ROCKET_EKANS, 3), (ROCKET_ZUBAT, 3), (ROCKET_ODDISH, 3), (ROCKET_KOFFING, 3), (BROCKS_ZUBAT, 3), (POLIWAG, 3), (MISTYS_GOLDEEN, 3),
             *TRAINERS, (GRASS, 16), (WATER, 11)),
    "LF29": ((ROCKET_VOLTORB, 3), (LT_SURGES_MAGNEMITE, 3), (LT_SURGES_VOLTORB, 3), (ROCKET_MACHOP, 3), (BROCKS_GEODUDE, 3), (ROCKET_DRATINI, 3),
             (BROCKS_LICKITUNG, 3), *TRAINERS, (LIGHTNING, 14), (FIGHTING, 13)),
    "F30": ((CHARMANDER, 4), (CHARMELEON, 3), (GROWLITHE, 4), (ARCANINE, 3), (MAGMAR, 3), (ROCKET_PONYTA, 4), *TRAINERS, (FIRE, 27)),
    # v0.31: 炎（第1弾・ロケット団・化石の秘密）。リザードンのエナジーバーンのために水・超を少し入れる
    "R31": ((CHARMANDER, 4), (CHARMELEON, 2), (CHARIZARD, 2), (DARK_CHARMELEON, 2), (DARK_CHARIZARD, 2), (VULPIX, 3), (NINETALES, 2),
            (ROCKET_PONYTA, 3), (DARK_RAPIDASH, 2), (EEVEE, 3), (DARK_FLAREON, 2), (MOLTRES, 2), *TRAINERS, (FIRE, 17), (WATER, 2)),
    # v0.31: カツラのポケモン（闇からの挑戦）
    "K31": ((BLAINES_CHARMANDER, 4), (BLAINES_CHARMELEON, 3), (BLAINES_VULPIX, 4), (BLAINES_NINETALES, 3), (BLAINES_GROWLITHE, 4),
            (BLAINES_ARCANINE, 3), (BLAINES_MAGMAR, 3), *TRAINERS, (FIRE, 24)),
    # v0.31: 雷・超（第1弾・ロケット団・リーダーズスタジアム・闇からの挑戦）
    "E31": ((ZAPDOS, 2), (LT_SURGES_ELECTABUZZ, 3), (LT_SURGES_PIKACHU, 3), (LT_SURGES_RAICHU, 2), (ROCKET_VOLTORB, 3), (DARK_ELECTRODE, 2),
            (GASTLY1, 3), (MEWTWO, 2), *TRAINERS, (LIGHTNING, 16), (PSYCHIC, 12)),
    # v0.31: 超・水・無色（化石の秘密・ジャングル・ロケット団・リーダーズスタジアム）
    "P31": ((SLOWPOKE, 3), (CLEFAIRY, 3), (CLEFABLE, 2), (PSYDUCK, 3), (DARK_GOLDUCK, 2), (MISTYS_PSYDUCK, 3), (MISTYS_GOLDUCK, 2),
            *TRAINERS, (PSYCHIC, 15), (WATER, 15)),
    # v0.32: 草（ジャングル・化石の秘密）。ふえるで同じ名前の別のカードを選べることを見るため、第4弾のナゾノクサを 1 枚入れる
    "G32": ((NIDORAN_F, 4), (NIDORINA, 3), (ODDISH, 3), (ROCKET_ODDISH, 1), (BELLSPROUT, 4), (WEEPINBELL, 3), (VENONAT, 3), (FOSSIL_ZUBAT, 3),
            (GOLBAT, 2), *TRAINERS, (GRASS, 22)),
    # v0.32: 水・超（第1弾・化石の秘密）
    "W32": ((MAGIKARP, 4), (GYARADOS, 3), (KRABBY, 4), (KINGLER, 3), (JYNX, 4), *TRAINERS, (WATER, 20), (PSYCHIC, 10)),
    # v0.33: 草・闘（第1弾・リーダーズスタジアム・闇からの挑戦）。ナツメのコンパンのはかいビーム（超無）のために超を少し入れる
    "N33": ((NIDORAN_M, 4), (NIDORINO, 3), (GIOVANNIS_NIDORAN_F, 3), (SABRINAS_VENONAT, 3), (BROCKS_DIGLETT, 3), (BROCKS_RHYHORN, 3),
            (BLAINES_RHYHORN, 3), *TRAINERS, (GRASS, 12), (FIGHTING, 12), (PSYCHIC, 2)),
    # v0.33: 水（化石の秘密・ジャングル・ロケット団）。ゴルダックのねんりき（超）のために超を入れる
    "W33": ((PSYDUCK, 4), (FOSSIL_GOLDUCK, 3), (EEVEE, 4), (DARK_VAPOREON, 3), (SHELLDER, 4), (CLOYSTER, 3), *TRAINERS, (WATER, 22), (PSYCHIC, 5)),
    # v0.33: 無色・雷（第1弾・ロケット団・リーダーズスタジアム・闇からの挑戦）。ハクリューの進化元は第1弾とロケット団のミニリュウ（名前で進化）
    "C33": ((DRATINI, 2), (ROCKET_DRATINI, 2), (DRAGONAIR, 3), (RATTATA, 4), (DARK_RATICATE, 3), (LT_SURGES_MAGNEMITE_30, 4), (LT_SURGES_SPEAROW, 3),
            (BLAINES_DODUO, 3), *TRAINERS, (LIGHTNING, 24)),
    # v0.34: 炎・雷（第1弾・ジャングル・ロケット団・リーダーズスタジアム）。ギャロップの進化元は第1弾とロケット団のポニータ（名前で進化）
    "F34": ((PONYTA, 2), (ROCKET_PONYTA, 2), (RAPIDASH, 3), (EEVEE, 4), (FLAREON, 2), (JOLTEON, 2), (BROCKS_VULPIX, 3), (ELECTABUZZ, 3),
            *TRAINERS, (FIRE, 15), (LIGHTNING, 12)),
    # v0.34: 草・超（第1弾・ジャングル・闇からの挑戦）。ナッシーのテレポート（超）のために超を入れる
    "G34": ((KOFFING, 4), (NIDORAN_M, 4), (NIDORINO, 3), (NIDOKING, 2), (EXEGGCUTE, 4), (EXEGGUTOR, 3), (GIOVANNIS_PINSIR, 3), *TRAINERS,
            (GRASS, 20), (PSYCHIC, 5)),
    # v0.34: 無色・闘・水（ジャングル・闇からの挑戦・第1弾）。たすけをよぶで選べる闘のたねポケモンとして第1弾のディグダを入れる
    "C34": ((TAUROS, 3), (BLAINES_KANGASKHAN, 3), (CUBONE, 4), (MAROWAK, 3), (EEVEE, 3), (VAPOREON, 3), (DIGLETT, 2), *TRAINERS,
            (FIGHTING, 15), (WATER, 12)),
    # v0.35: 無色・水（リーダーズスタジアム・闇からの挑戦）。どのワザも水と無色で払える
    "S35": ((LT_SURGES_RATTATA, 4), (LT_SURGES_RATICATE, 3), (MISTYS_POLIWAG, 4), (MISTYS_POLIWHIRL, 3), (BLAINES_TAUROS, 3), *TRAINERS, (WATER, 31)),
    # v0.36: 水・闘・無色（第1弾・化石の秘密・リーダーズスタジアム・闇からの挑戦）。マチスのオニドリルの進化元はマチスのオニスズメ（v0.33）
    "W36": ((SANDSHREW, 4), (SANDSLASH, 3), (HORSEA, 3), (MISTYS_HORSEA, 3), (MISTYS_SEEL, 4), (KOGAS_PIDGEY, 3), (LT_SURGES_SPEAROW, 3),
            (LT_SURGES_FEAROW, 2), *TRAINERS, (FIGHTING, 11), (WATER, 12)),
    # v0.36: 草・炎・雷（化石の秘密・ロケット団・リーダーズスタジアム・闇からの挑戦）。わるいサンダースの進化元はイーブイ（v0.31）
    "K36": ((KOGAS_KOFFING, 4), (ERIKAS_BELLSPROUT, 4), (FOSSIL_MAGMAR, 4), (EEVEE, 4), (DARK_JOLTEON, 3), *TRAINERS, (GRASS, 10), (FIRE, 10),
            (LIGHTNING, 9)),
    # v0.37: 闘（第1弾・ジャングル・リーダーズスタジアム）。どのポケモンも闘に弱点・抵抗力を持たない（ダグトリオのじしんは JS1 で止まらない）
    "F37": ((RHYHORN, 4), (BROCKS_SANDSHREW, 4), (BROCKS_ONIX, 4), (DIGLETT, 4), (DUGTRIO, 3), *TRAINERS, (FIGHTING, 29)),
    # v0.37: 水（第1弾・リーダーズスタジアム）。ニョロボンのみずでっぽう（水水無）のために闘を入れる（「水」が 3 つ以上なら HC4 で止まる）
    "W37": ((POLIWAG, 4), (POLIWHIRL, 3), (POLIWRATH, 3), (MISTYS_MAGIKARP, 4), *TRAINERS, (WATER, 24), (FIGHTING, 10)),
    # v0.37: 雷・無色（第1弾・ジャングル・ロケット団）
    "L37": ((PIKACHU, 4), (RAICHU, 3), (MEOWTH, 4), (PERSIAN, 3), (ROCKET_EEVEE, 4), *TRAINERS, (LIGHTNING, 30)),
    # v0.37: 草・超（化石の秘密・闇からの挑戦）
    "G37": ((FOSSIL_GRIMER, 4), (FOSSIL_EKANS, 4), (KOGAS_TANGELA, 4), (SABRINAS_DROWZEE, 4), *TRAINERS, (GRASS, 20), (PSYCHIC, 12)),
    # v0.38: 闘・炎（化石の秘密・ジャングル・闇からの挑戦・リーダーズスタジアム）
    # （キョウのポッポ（PMCG6-067）は、進化先のキョウのピジョンのないこのデッキに入れる（でんれいとつばさでうつを使う）
    "F38": ((HITMONLEE, 3), (RHYHORN, 4), (RHYDON, 3), (BLAINES_PONYTA, 3), (BLAINES_RAPIDASH, 3), (BROCKS_VULPIX_50, 3), (KOGAS_PIDGEY_40, 4), *TRAINERS,
            (FIGHTING, 14), (FIRE, 11)),
    # v0.38: 草（リーダーズスタジアム・化石の秘密・闇からの挑戦）
    "G38": ((ERIKAS_TANGELA, 3), (BROCKS_ZUBAT, 3), (BROCKS_GOLBAT, 3), (FOSSIL_EKANS, 3), (ARBOK, 3), (KOGAS_WEEDLE, 3), (GIOVANNIS_NIDORAN_F, 4),
            (GIOVANNIS_NIDORINA, 4), *TRAINERS, (GRASS, 22)),
    # v0.38: 無色・水・超（化石の秘密・ロケット団・闇からの挑戦）
    "C38": ((ARTICUNO, 4), (SABRINAS_PORYGON, 4), (ROCKET_ABRA, 4), (KOGAS_PIDGEY, 4), (KOGAS_PIDGEOTTO, 3), *TRAINERS, (WATER, 16), (PSYCHIC, 13)),
    # v0.39: 雷（第1弾・ジャングル・化石の秘密・ロケット団）。同じ名前の「コイル」「レアコイル」は 2 枚ずつ（合わせて 4 枚）。ちょくれつじりょくは、ベンチの
    # 2 種類のコイルとレアコイルを数える
    "L39": ((MAGNEMITE, 2), (ROCKET_MAGNEMITE, 2), (MAGNETON, 2), (FOSSIL_MAGNETON, 2), (JUNGLE_PIKACHU, 4), (FOSSIL_RAICHU, 3), (VOLTORB, 4),
            (ELECTRODE, 3), *TRAINERS, (LIGHTNING, 26)),
    # v0.39: 草（第1弾・化石の秘密・リーダーズスタジアム・闇からの挑戦）。キョウのマタドガスの進化元は PMCG6-008 のキョウのドガース
    "G39": ((KOGAS_KOFFING_40, 4), (KOGAS_WEEZING, 3), (KOFFING, 4), (FOSSIL_WEEZING, 3), (ERIKAS_PARAS, 4), *TRAINERS, (GRASS, 30)),
    # v0.39: 無色・水（第1弾・ジャングル・リーダーズスタジアム・闇からの挑戦）
    "C39": ((PIDGEY, 4), (JIGGLYPUFF, 4), (WIGGLYTUFF, 3), (MISTYS_POLIWAG, 4), (MISTYS_POLIWHIRL, 3), (MISTYS_POLIWRATH, 2), *TRAINERS, (WATER, 28)),
    # v0.39: 草（第1弾・ジャングル）。ラブラブアタックで数えるニドキングを入れる
    "N39": ((NIDORAN_F, 4), (NIDORINA, 3), (NIDOQUEEN, 3), (NIDORAN_M, 4), (NIDORINO, 3), (NIDOKING, 2), *TRAINERS, (GRASS, 29)),
    # v0.40: 草（闇からの挑戦・第1弾・リーダーズスタジアム）。むれでおそうで山札から出すキョウのズバット、みんなでばくはつで数えるドガース
    "G40": ((KOGAS_ZUBAT, 4), (KOGAS_GOLBAT, 3), (KOFFING, 4), (DARK_WEEZING, 3), (ERIKAS_BELLSPROUT, 4), (ERIKAS_WEEPINBELL, 3), *TRAINERS, (GRASS, 27)),
    # v0.40: 草（闇からの挑戦）。ラブラリアットで見るサカキのニドキング。みんなでばくはつで相手の場の数に入るドガース（ロケット団。たいあたりは無色）
    "N40": ((GIOVANNIS_NIDORAN_M, 4), (GIOVANNIS_NIDORINO, 3), (GIOVANNIS_NIDOKING, 2), (GIOVANNIS_NIDORAN_F, 4), (GIOVANNIS_NIDORINA, 3),
            (GIOVANNIS_NIDOQUEEN, 2), (ROCKET_KOFFING, 3), *TRAINERS, (GRASS, 27)),
    # v0.40: 闘（ロケット団・第2弾・リーダーズスタジアム）。オコリザルの進化元はロケット団のマンキー
    "F40": ((ROCKET_MACHOP, 4), (DARK_MACHOKE, 3), (DARK_MACHAMP, 2), (MANKEY, 4), (PRIMEAPE, 3), (BROCKS_MANKEY, 4), *TRAINERS, (FIGHTING, 28)),
    # v0.40: 超・水（第1弾・ロケット団・リーダーズスタジアム）
    "P40": ((DROWZEE, 4), (DARK_HYPNO, 3), (MISTYS_HORSEA, 4), (MISTYS_SEADRA, 3), *TRAINERS, (PSYCHIC, 17), (WATER, 17)),
}
PRESETS = {"A2": driver.DECK_A2, "B2": driver.DECK_B2}
PAIRINGS = (("W28", "G28"), ("W28", "B2"), ("G28", "A2"))
PAIRINGS_V0_29 = (("GW29", "LF29"), ("GW29", "B2"), ("LF29", "A2"))
PAIRINGS_V0_30 = (("F30", "B2"), ("F30", "A2"), ("F30", "G28"))
PAIRINGS_V0_31 = (("R31", "K31"), ("E31", "P31"), ("R31", "P31"), ("K31", "E31"))
PAIRINGS_V0_32 = (("G32", "W32"), ("G32", "A2"), ("W32", "B2"))
PAIRINGS_V0_33 = (("N33", "W33"), ("C33", "N33"), ("W33", "C33"))
PAIRINGS_V0_34 = (("F34", "G34"), ("C34", "F34"), ("G34", "C34"))
PAIRINGS_V0_35 = (("S35", "C34"), ("G34", "S35"), ("S35", "A2"))
# v0.36: K36 対 P31（ピッピ・ピクシー・カスミのコダックが、えんまく・くもがくれガスなどを自分のワザとして使う）
PAIRINGS_V0_36 = (("W36", "K36"), ("K36", "P31"), ("W36", "A2"))
PAIRINGS_V0_37 = (("F37", "L37"), ("W37", "G37"), ("L37", "W37"), ("G37", "F37"))
# v0.38: C38 対 P31（ピッピ・ピクシー・カスミのコダックが、でんれい・いなくなる・ふぶきなどを自分のワザとして使う）
PAIRINGS_V0_38 = (("F38", "G38"), ("G38", "C38"), ("C38", "F38"), ("C38", "P31"))
PAIRINGS_V0_39 = (("L39", "C39"), ("C39", "G39"), ("G39", "N39"), ("N39", "L39"))
PAIRINGS_V0_40 = (("G40", "N40"), ("N40", "F40"), ("F40", "P40"), ("P40", "G40"))
BATCHES = {"v0.28": PAIRINGS, "v0.29": PAIRINGS_V0_29, "v0.30": PAIRINGS_V0_30, "v0.31": PAIRINGS_V0_31, "v0.32": PAIRINGS_V0_32,
           "v0.33": PAIRINGS_V0_33, "v0.34": PAIRINGS_V0_34, "v0.35": PAIRINGS_V0_35, "v0.36": PAIRINGS_V0_36, "v0.37": PAIRINGS_V0_37,
           "v0.38": PAIRINGS_V0_38, "v0.39": PAIRINGS_V0_39, "v0.40": PAIRINGS_V0_40}
CHECK_FAILURES = ("check_decision_player_mismatch", "check_in_use_mismatch", "check_in_use_left_in_main")
# ワザの結果として数えるログ（v0.28・v0.29 のカードのワザの中に出たもの）
RESULT_EVENTS = ("special_condition", "persistent_effect_added", "discard_energy", "remove_all_damage_counters", "drain_heal",
                 "damage_prevented", "confusion_damage", "attack_evaded",
                 # v0.31
                 "discard_energy_failed", "discard_attached_energy", "attack_heal", "recover_trainer", "attach_energy_from_discard",
                 "attack_attach_energy", "discard_from_deck", "copy_attack", "attack_failed", "effect_prevented", "effect_skipped", "draw",
                 "forced_switch", "destiny_bond",
                 # v0.32
                 "bench_from_deck", "bench_from_deck_none",
                 # v0.33
                 "forced_switch_skipped",
                 # v0.34（テレポート）
                 "switch",
                 # v0.36（くもがくれガス）
                 "return_in_play_to_deck")
# v0.38: v0.38 のカードのワザの中に出た結果のログ（v0.38 のカードだけで数える。前の版のカードの数え方は変えない）
V038_RESULT_EVENTS = ("discard_attached_cards", "reveal_from_deck", "reveal_from_deck_none", "promote_active")
# v0.40: v0.40 のカードのワザの中に出た結果のログ（v0.40 のカードだけで数える）。``shuffle`` はワザの効果で切ったもの（ログの ``effect``）だけ
V040_RESULT_EVENTS = ("bench_from_deck_declined", "shuffle")


def _attacker(state, command):
    return state.players[command.player].active


def _copier(state, command):
    effect = state.effects.attack_effect(state.card_def(_attacker(state, command).card).id,
                                         state.card_def(_attacker(state, command).card).attacks[command.attack_index],
                                         state.card_def(_attacker(state, command).card).attacks)
    return type(effect).__name__ in ("CopyOpponentAttackEffect", "ThreeCoinPsychicPower")


def _defender(state, command):
    return state.players[1 - command.player].active


def _attack_effect(state, command):
    definition = state.card_def(_attacker(state, command).card)
    return state.effects.attack_effect(definition.id, definition.attacks[command.attack_index], definition.attacks)


# v0.31: 原典で決められない場合・エンジンの未対応で止まったワザを、場から確かめる関数（tests/v017_games.py の ``extra_stop``。止まるのが正しいなら True）
V031_STOPS = {
    "UNRESOLVED_DISCARD_ENERGY_TIMING": lambda st, c: _attacker(st, c).conditions.confused,  # HC1
    # HC4（第4弾のコダック・v0.34 のシャワーズの「みずでっぽう」）
    "UNRESOLVED_EXTRA_ENERGY_COLORLESS": lambda st, c: type(_attack_effect(st, c)).__name__ == "ExtraEnergyDamageMixed",
    "UNRESOLVED_PREVENTED_EFFECT_COIN": lambda st, c: attack_barrier(st, _defender(st, c)) is not None,  # HC3
    "UNRESOLVED_DESTINY_BOND_KNOCKOUT": lambda st, c: destiny_bond(st, _defender(st, c)) is not None,  # HC2
    # しっぽをふる。v0.40: すごむ（効果を与えたポケモンがバトル場にいる間）
    "ATTACK_PREVENTED": lambda st, c: (cannot_attack(st, _attacker(st, c)) is not None
                                       or cannot_attack_while_source_active(st, _attacker(st, c)) is not None),
    "UNRESOLVED_DISCARD_DECK_SHORT": lambda st, c: (  # HC6: マグマふんしゅつ（自分の山札 5 枚未満）・やまやき（相手の山札 0 枚）
        (st.card_def(_attacker(st, c).card).id, c.attack_index) == (BLAINES_MAGMAR, 1) and len(st.players[c.player].deck) < 5
        or (st.card_def(_attacker(st, c).card).id, c.attack_index) == (MOLTRES, 0) and not st.players[1 - c.player].deck),
    "NO_DAMAGE_COUNTERS": lambda st, c: st.card_def(_attacker(st, c).card).id == SLOWPOKE and _attacker(st, c).damage == 0,  # ぼーっとする
    "UNRESOLVED_COPIED_ATTACK": lambda st, c: _copier(st, c),  # HC9
    "UNSUPPORTED_COPIED_ATTACK": lambda st, c: _copier(st, c),
    # 試す結果の数が上限（4,096）を超える（れんぞくファイヤーボール・エナジーボム・ほうでん・やまやきで、ついているエネルギーが多いとき）
    "UNSUPPORTED_PREFLIGHT_LIMIT": lambda st, c: len(_attacker(st, c).energy) >= 6,
    # v0.32: なかまをよぶ・ふえる（ベンチに空きがなければ使えない。ワザを使うための条件）
    "BENCH_FULL": lambda st, c: (type(_attack_effect(st, c)).__name__ in ("PutBasicFromDeckOntoBench", "PutTypeBasicFromDeckOntoBench")  # v0.34 のたすけをよぶ
                                 and len(st.players[c.player].bench) >= st.rules.max_bench),
    # v0.32: ヨガのポーズ（相手の控えポケモンにダメージカウンターがのっている。CD4）
    "UNRESOLVED_OPPONENT_POKEMON_COUNTERS": lambda st, c: (type(_attack_effect(st, c)).__name__ == "DamagePlusDefenderCounters"
                                                           and any(p.damage for p in st.players[1 - c.player].bench)),
    # v0.34: どくどく（相手が受けるダメージの違うどく状態。TP3（v0.3a の 15））
    "UNRESOLVED_SPECIAL_POISON_OVERWRITE": lambda st, c: (type(_attack_effect(st, c)).__name__ in ("DamageAndSpecialPoison",
                                                                                              "DamageThenSpecialPoisonOnHeads")  # v0.39 のどくどくガス
                                                          and _defender(st, c).conditions.poison is not None
                                                          and _defender(st, c).conditions.poison.damage != _attack_effect(st, c).poison_damage),
    # v0.35: あわあわ（自分）・ドわすれ（相手が選んだワザ）で、この番は使えないワザ（ワザを使うための条件と同じく宣言の前に拒否する）
    "ATTACK_LOCKED": lambda st, c: attack_locked(st, _attacker(st, c), c.attack_index) is not None,
    # v0.36: こんらん状態のポケモンが、手順 4 のコインの効果（すなかけ・えんまくなど）を受けてワザを使う（AC6）
    "UNRESOLVED_ATTACK_CHECK_CONFUSION": lambda st, c: _attacker(st, c).conditions.confused and bool(attack_coin_checks(st, _attacker(st, c))),
    # v0.36: くもがくれガス（自分のワザ・相手のワザとして使うワザ）で、同じワザで相手の対戦ポケモンが HP 以上になりうる（RD9）
    "UNRESOLVED_RETURN_IN_PLAY_TO_DECK_KNOCKOUT": lambda st, c: _deck_return_with_knockout(st, c),
    # v0.36: くもがくれガスの「ダメージを与えた後」で、ダメージを与えない（Z23。最終ダメージが 0・受けない）
    "UNRESOLVED_EFFECT_AFTER_NO_DAMAGE": lambda st, c: _deck_return_without_damage(st, c),
    # v0.37: 説明に「弱点・抵抗力」に関係なくのない自分の控えへのダメージ（ダグトリオのじしん）で、控えにワザを使うポケモンのタイプに弱点・抵抗力を
    # 持つポケモンがいる（JS1）
    "UNRESOLVED_BENCH_DAMAGE_WEAKNESS_RESISTANCE": lambda st, c: _bench_reading_matters(st, c),
    # v0.34: なきつくを受けたポケモンが、なきつくを使ったポケモンが控えにいるときに控えにダメージを与える（NK5）
    "UNRESOLVED_REDUCED_DAMAGE_BENCH_TARGET": lambda st, c: (reduced_damage_to_source(st, _attacker(st, c)) is not None
                                                             and any(p.card == reduced_damage_to_source(st, _attacker(st, c)).source_card
                                                                     for p in st.players[1 - c.player].bench)),
    # v0.38: のびるキック（相手に控えポケモンがいなければ使えない。ワザを使うための条件）
    # v0.40: ひきずりだす・さそってとかす・つまみだす（相手に控えがいなければ使えない）
    "NO_OPPONENT_BENCH": lambda st, c: ((type(_attack_effect(st, c)).__name__ == "ChooseOpponentBenchDamage" and _attack_effect(st, c).requires_bench
                                         or type(_attack_effect(st, c)).__name__ in ("SwitchOpponentThenDamage", "ReturnOpponentActiveToDeck"))
                                        and not st.players[1 - c.player].bench),
    # v0.40: いかりのいちげき（自分にダメージカウンターが 2 つ以上のっていなければ使えない）
    "NOT_ENOUGH_DAMAGE_COUNTERS": lambda st, c: (type(_attack_effect(st, c)).__name__ == "DamageRequiringOwnCounters"
                                                 and _attacker(st, c).damage // st.rules.damage_per_counter < _attack_effect(st, c).minimum),
    # v0.38: げきとつ（自分のワザ・相手のワザとして使うワザ）で、相手の対戦ポケモンが「ダメージを受けたとき」の効果を持つ（GK1）
    "UNRESOLVED_DAMAGE_TRIGGER_TIMING": lambda st, c: _damage_trigger_before_later_damage(st, c),
}


def _damage_trigger_before_later_damage(state, command):
    """GK1（v0.38）: 使うワザ（相手のワザとして使うワザなら、相手の対戦ポケモンのワザのどれか）が、入れ替えのあとに自分へのダメージのあるワザ（げきとつ）で、
    相手の対戦ポケモンが「ダメージを受けたとき」の効果（はたらいている「はんげき」・「わるいねぞう」、ほのおのかべ・こうらがえしの持続する効果）を持つ。"""
    attacker, defender = _attacker(state, command), _defender(state, command)
    candidates = [(attacker, command.attack_index)]
    if _copier(state, command):
        candidates = [(defender, a.index) for a in state.card_def(defender.card).attacks]
    rams = []
    for pokemon, index in candidates:
        definition = state.card_def(pokemon.card)
        rams.append(type(state.effects.attack_effect(definition.id, definition.attacks[index], definition.attacks)).__name__
                    == "DamageThenForceSwitchThenSelfDamage")
    return any(rams) and (working_counterattack_power(state, defender.pokemon_id) is not None or retaliation(state, defender) is not None)


def _bench_reading_matters(state, command):
    """JS1（v0.37）: ワザが説明に「弱点・抵抗力」に関係なくのない自分の控えへのダメージ（``DamageAndOwnBenchDamage`` の ``weakness_resistance_stated`` が
    偽）で、自分の控えに、ワザを使うポケモンのタイプに弱点・抵抗力を持つポケモンがいる（まねるワザは対戦に入れていないので見ない）。

    v0.39: 第1弾のじばく（``SelfDestruct`` の ``weakness_resistance_stated`` が偽。お互いの控えの全員）・ビリビリ（``DamageThenSameTypeBenchDamage``。お互いの
    控えの、相手の対戦ポケモンと同じタイプのポケモン）は、受ける控えのどれかが、スパーク（``DamageThenChosenBenchDamage`` の ``weakness_resistance_stated`` が
    偽）は、選べる相手の控えのすべてが、ワザを使うポケモンのタイプに弱点・抵抗力を持つ（1 匹でも持たなければ、宣言は受け付けて、選ぶときに避ける）。"""
    effect = _attack_effect(state, command)
    kind = state.card_def(_attacker(state, command).card).pokemon_type

    def related(pokemon):
        return kind in (state.card_def(pokemon.card).weakness, state.card_def(pokemon.card).resistance)

    name = type(effect).__name__
    both = state.players[command.player].bench + state.players[1 - command.player].bench
    if name == "SelfDestruct" and not effect.weakness_resistance_stated:
        return any(related(p) for p in both)
    if name == "DamageThenSameTypeBenchDamage":
        wanted = state.card_def(_defender(state, command).card).pokemon_type
        return any(related(p) for p in both if state.card_def(p.card).pokemon_type is wanted)
    if name == "NamedPokemonExplosion":
        # v0.40: みんなでばくはつ（お互いの控えの、名前の合うポケモン全員）
        return any(related(p) for p in both if state.card_def(p.card).name_ja in effect.names)
    if name == "DamageThenChosenBenchDamage" and not effect.weakness_resistance_stated:
        bench = state.players[1 - command.player].bench
        return bool(bench) and all(related(p) for p in bench)
    if name != "DamageAndOwnBenchDamage" or effect.weakness_resistance_stated:
        return False
    return any(related(p) for p in state.players[command.player].bench)


def _deck_return_attacks(state, command):
    """ワザ（相手のワザとして使うワザなら、相手の対戦ポケモンのワザ）のうち、くもがくれガス（``DamageThenReturnSelfToDeckOnHeads``）の (カード id, ワザ)（v0.36）。"""
    candidates = [(_attacker(state, command), command.attack_index)]
    if _copier(state, command):
        defender = _defender(state, command)
        candidates = [(defender, a.index) for a in state.card_def(defender.card).attacks]
    found = []
    for pokemon, index in candidates:
        definition = state.card_def(pokemon.card)
        effect = state.effects.attack_effect(definition.id, definition.attacks[index], definition.attacks)
        if type(effect).__name__ == "DamageThenReturnSelfToDeckOnHeads":
            found.append((definition.id, definition.attacks[index]))
    return found


def _deck_return_preview(state, command):
    """くもがくれガスの相手へのダメージの最終ダメージ（状態を変えない計算。``effects.preview_attack_damage``。受けないなら None）の一覧。"""
    attacker = _attacker(state, command)
    return [preview_attack_damage(state, AttackUse(command.player, attacker.pokemon_id, E_AttackKey(card_id, attack.index)), "opponent_active",
                                  attack.damage)
            for card_id, attack in _deck_return_attacks(state, command)]


def _deck_return_with_knockout(state, command):
    defender = _defender(state, command)
    left = state.card_def(defender.card).hp - defender.damage
    return any(amount is not None and amount >= left for amount in _deck_return_preview(state, command))


def _deck_return_without_damage(state, command):
    return any(amount is None or amount <= 0 for amount in _deck_return_preview(state, command))


def _v036_retreat_probe(state, tried, counts):
    """v0.36: バトル場のポケモンが「にげる」ことができない効果（アイスバーン・わしづかみ）を受けているはたらく番に、1 度だけ「にげる」を宣言する
    （エネルギー・コインの前の拒否 ``RETREAT_PREVENTED`` を起こし、状態が変わらないことを確かめる。効果がなければ何もしないので、前の版の組の結果は
    変わらない）。ねむり・マヒ（先に別のコードで拒否する）とにげるエネルギーが足りないときはしない。"""
    player = state.current_player
    p = state.players[player]
    active = p.active
    if "retreat_lock_probe" in tried or not p.bench or cannot_retreat(state, active) is None:
        return None
    if active.conditions.asleep or active.conditions.paralyzed:
        return None
    cost = state.card_def(active.card).retreat_cost
    if len(active.energy) < cost:
        return None
    tried.add("retreat_lock_probe")
    counts["v036_retreat_probe"] += 1
    return Retreat(player, tuple(active.energy[:cost]), p.bench[0].card)


def deck_cards(label):
    """60 枚のカード id の並び。検証用デッキは ``DECKS`` の順、第2版は公開の固定のデッキのまま。"""
    if label in PRESETS:
        return preset_deck(PRESETS[label]).cards()
    if label not in DECKS:
        raise ValueError(f"知らないデッキ {label!r}（{sorted(DECKS) + sorted(PRESETS)}）")
    cards = [card for card, count in DECKS[label] for _ in range(count)]
    if len(cards) != 60:
        raise ValueError(f"{label} は {len(cards)} 枚")
    return cards


def _uses_so_far(state, player, card_id):
    """その局でプレイヤーが ``card_id`` のポケモンで宣言したワザの回数（ワザの位置ごと）。"""
    used = Counter()
    for e in state.log:
        if e["kind"] == "attack" and e["player"] == player and state.cards[e["pokemon"]].card_id == card_id:
            used[e["attack_index"]] += 1
    return used


def _v031_decision(state, counts):
    """v0.31 のカードのワザの決定への答え（元の手順は 1 つ目の選べるもの 1 つを選ぶので、2 枚以上を選ぶ決定・選ばなくてもよい決定に答えられない）。
    原典で決められない選択・エンジンの未対応の選択（``context`` の ``unresolved_choices``・``unsupported_choices``）は選ばない。"""
    d = state.decision
    if d is None or d.resume != "attack":
        return None
    use = d.context_value("use")
    if use is None or use[2] not in V0_31:
        return None
    blocked = set(d.context_value("unresolved_choices", ())) | set(d.context_value("unsupported_choices", ()))
    options = [o for o in d.options if o not in blocked]
    if d.kind == SELECT_ATTACK:
        counts["v031_select_attack"] += 1
        return ResolveDecision(d.player, d.id, (options[counts["v031_select_attack"] % len(options)],))
    if d.kind == ATTACH_FROM_DISCARD:
        count = d.max_choices  # たいでん: つけられるだけつける（0 枚は HC7）
    elif d.kind == DISCARD_ENERGY and d.min_choices == 0:
        count = 1  # やまやき（好きなだけ。0 枚は HC5）・ひばしら（のぞむなら）: 1 枚
    else:
        count = max(d.min_choices, min(1, d.max_choices))
    counts[f"v031_decision_{d.kind}_{count}"] += 1
    return ResolveDecision(d.player, d.id, tuple(options[:count]))


def _v039_decision(state, counts):
    """v0.39 のカードのワザの控えを選ぶ決定への答え（スパーク・ギガスパーク）。原典で決められない選択（``unresolved_choices``。スパークの JS1）は選ばない。
    ギガスパーク（``min_choices`` 0）は、決定のたびに 1・2・3 匹（控えの数まで）を順に選ぶ（0 匹は GS1 で止まるので選ばない）。"""
    d = state.decision
    if d is None or d.resume != "attack" or d.kind != SELECT_POKEMON:
        return None
    use = d.context_value("use")
    if use is None or use[2] not in V0_39:
        return None
    blocked = set(d.context_value("unresolved_choices", ()))
    options = [o for o in d.options if o not in blocked]
    if d.min_choices == 0:
        count = 1 + counts["v039_targets"] % d.max_choices
        counts["v039_targets"] += 1
    else:
        count = d.min_choices
    counts[f"v039_decision_{count}"] += 1
    return ResolveDecision(d.player, d.id, tuple(options[:count]))


def _v040_decision(state, counts):
    """v0.40 のカードのワザの決定への答え。むれでおそう（``BENCH_FROM_DECK``。0 枚〜）は、番の番号で 選べるだけ・0 枚・1 枚 のどれかを選ぶ（出さない選択も
    起こす。1 局で使う回数が少ないので、局ごとの回数ではなく番の番号で分ける）。ひきずりだす・さそってとかす（``FORCED_SWITCH``。ワザを使ったプレイヤーが選ぶ）は、決定のたびに 最後・最初 の控えを順に選ぶ。"""
    d = state.decision
    if d is None or d.resume != "attack":
        return None
    use = d.context_value("use")
    if use is None or use[2] not in V0_40:
        return None
    if d.kind == BENCH_FROM_DECK:
        count = (d.max_choices, 0, 1)[state.turn_number % 3]
        counts["v040_bench_from_deck"] += 1
        counts[f"v040_bench_from_deck_{min(count, d.max_choices)}"] += 1
        return ResolveDecision(d.player, d.id, tuple(d.options[:min(count, d.max_choices)]))
    if d.kind == FORCED_SWITCH and d.player == use[0]:
        index = -1 if counts["v040_switch"] % 2 == 0 else 0
        counts["v040_switch"] += 1
        return ResolveDecision(d.player, d.id, (d.options[index],))
    return None


def _v031_power(state, tried, counts):
    """v0.31 の宣言する特殊能力を使う手順: カツラのロコンの「しぜんになおる」（ダメージがあり、この番にまだ使っていない）・リザードンの「エナジーバーン」
    （炎でないエネルギーがついていて、その番にまだ使っていない）。使えない特殊状態のときは使わない（拒否を起こさない）。"""
    player = state.current_player
    p = state.players[player]
    for pokemon in p.in_play():
        card_id = state.card_def(pokemon.card).id
        blocked = pokemon is p.active and (pokemon.conditions.asleep or pokemon.conditions.paralyzed or pokemon.conditions.confused)
        if blocked:
            continue
        if card_id == BLAINES_VULPIX and pokemon.damage > 0 and (pokemon.pokemon_id, 0) not in state.power_uses_this_turn:
            counts["v031_power_natural_cure"] += 1
            return UsePokemonPower(player, pokemon.pokemon_id, 0)
        marker = ("energy_burn", pokemon.pokemon_id)
        if card_id == CHARIZARD and marker not in tried and any(state.energy_type_of(pokemon, u) is not EnergyType.FIRE for u in pokemon.energy):
            tried.add(marker)
            counts["v031_power_energy_burn"] += 1
            return UsePokemonPower(player, pokemon.pokemon_id, 0)
    return None


def make_policy(seen: dict, counts: Counter):
    """tools/preset_deck_games.py の手順（``checks=True``）に、v0.28〜v0.31 のカードのワザの選び方を重ねる（モジュールの説明）。v0.31 からは、
    v0.31 のカードのワザの決定への答え（``_v031_decision``）と、宣言する特殊能力の使用（``_v031_power``）も重ねる。v0.31 のカードのない局では
    何もしないので、v0.28〜v0.30 の組の結果は変わらない。"""
    base = driver.make_policy(seen, counts, checks=True)

    def policy(state, *, janken_winner, cure, tried):
        command = base(state, janken_winner=janken_winner, cure=cure, tried=tried)
        if state.phase is Phase.DECISION:
            return _v031_decision(state, counts) or _v039_decision(state, counts) or _v040_decision(state, counts) or command
        if state.phase is Phase.MAIN and isinstance(command, (UseAttack, EndTurn)):
            power = _v031_power(state, tried, counts)
            if power is not None:
                return power
            probe = _v036_retreat_probe(state, tried, counts)  # v0.36
            if probe is not None:
                return probe
        if state.phase is not Phase.MAIN or not isinstance(command, (UseAttack, EndTurn)) or "attack" in tried:
            return command
        player = state.current_player
        active = state.players[player].active
        card_id = state.cards[active.card].card_id
        if card_id not in TARGETS:
            return command
        attacks = state.card_def(active.card).attacks
        provided = state.energy_types(active)
        usable = [a.index for a in attacks if can_pay_cost(a.cost, provided) and ("attack_index", a.index) not in tried]
        if not usable:
            return command
        used = _uses_so_far(state, player, card_id)
        if card_id in V0_31 and all(used[i] >= 2 for i in usable) and any(used[a.index] == 0 and a.index not in usable for a in attacks):
            # v0.31: エネルギーをトラッシュするワザ（やまやき・メラメラなど）を使い続けると、エネルギーがたまらず、もう一つのワザが使えるようにならない。
            # 使えるワザをどれも 2 回以上使い、まだ使っていないワザが必要なエネルギーの不足で使えないときは、この番はワザを使わずに番を終える
            counts[f"v031_wait_{card_id}"] += 1
            return EndTurn(player)
        if card_id in V0_38 + V0_39 + V0_40 and all(used[i] >= 1 for i in usable) and any(used[a.index] == 0 and a.index not in usable for a in attacks):
            # v0.38: 必要なエネルギーの少ないワザ（でんれい・どくばりタックルなど）を使い続けると、もう一つのワザが使えるようにならない（でんれいは自分を
            # 山札にもどす）。使えるワザをどれも 1 回以上使い、まだ使っていないワザが必要なエネルギーの不足で使えないときは、この番はワザを使わずに番を終える
            counts[f"v038_wait_{card_id}"] += 1  # v0.39・v0.40 のカードも同じ手順（じばく・メガトンパンチ・ギガスパークなど）
            return EndTurn(player)
        choice = min(usable, key=lambda i: (used[i], -(attacks[i].damage or 0), i))
        chosen = UseAttack(player, choice)
        if chosen != command:
            counts[f"coverage_choice_{card_id}#{choice}"] += 1
        return chosen

    return policy


def play(labels, seed, *, max_steps=8000, keep_state=False):
    """1 局を進め、終わり方と動きを返す（終わり方の分類は tools/preset_deck_games.py の ``play`` と同じ）。"""
    seen, counts = {}, Counter()
    decks = tuple(deck_cards(label) for label in labels)
    result = {"seed": seed, "decks": list(labels), "first": seed % 2}
    commands = []
    try:
        state, commands, observed = play_game(decks, seed, policy=make_policy(seen, counts), max_steps=max_steps, extra_stop=V031_STOPS)
        outcome = state.phase.value
        if state.phase is Phase.HALTED:
            outcome = "halted"
            result["halt_code"] = next((e["code"] for e in reversed(state.log) if e["kind"] == "halted"), None)
    except AssertionError as error:
        state, observed = seen.get("state"), Counter()
        outcome = "step_limit" if str(error) == driver.STEP_LIMIT else "internal_error"
        result["error"] = str(error)[:500]
    except (IllegalActionError, UnsupportedError) as error:
        state, observed = seen.get("state"), Counter()
        outcome = "unexpected_rejection"
        result["error"] = f"{error.code}: {error}"[:500]
    except Exception as error:  # noqa: BLE001  内部エラーも集計から落とさない
        state, observed = seen.get("state"), Counter()
        outcome = "internal_error"
        result["error"] = "".join(traceback.format_exception_only(type(error), error))[:500]
    result["outcome"] = outcome
    result["steps"] = len(commands)
    result["observed"] = dict(observed)
    result["unresolved_rejections"] = {k: v for k, v in observed.items() if "UNRESOLVED_" in k}
    result["policy"] = dict(counts)
    if state is not None:
        result["turns"] = state.turn_number
        if state.result is not None:
            result["winner_deck"] = labels[state.result.winner] if state.result.winner is not None else None
            result["conditions"] = [c[1] for c in state.result.conditions]
        result["card_uses"] = card_uses(state)
        result["trainer_sequence_problems"] = driver.trainer_sequence_problems(state)
    result["audit"] = audit(result, state, commands)
    if keep_state:
        result["state"] = state
        result["commands"] = commands
    return result


def audit(result, state, commands):
    """監査の失敗の数（失敗がなければ空）。やり直しと監査は、終わりまで進んだ局（通常の勝敗・サドンデス・停止）だけ。"""
    failures = Counter()
    if state is None or result["outcome"] not in ("game_over", "sudden_death", "halted"):
        return {"not_audited": 1}
    current = new_game(*(deck_cards(label) for label in result["decks"]), result["seed"])
    for command in commands:
        current = apply_command(current, command)
    failures["replay_mismatch"] += [dict(e) for e in current.log] != [dict(e) for e in state.log]
    failures["invariants"] += bool(check_invariants(state))
    failures["log"] += bool(log_problems(state))
    failures["serialization"] += bool(serialization_problems(state))
    failures["trainer_sequence"] += bool(result.get("trainer_sequence_problems"))
    for key in CHECK_FAILURES:
        failures[key] += result["policy"].get(key, 0)
    return {k: v for k, v in failures.items() if v}


def card_uses(state):
    """ログから数えた v0.28〜v0.30 のカードの動き（カード id ごと）。

    - ``in_play``: 場に出した枚数（対戦準備・ベンチに出す）。``evolved_to``: そのカードに進化した回数（``evolve`` の ``to_card``）
    - ``attack#i``: ワザの宣言の回数（こんらんのコインで「うら」だったワザも数える）。``confused_failed#i``: そのうちこんらんの 20 になったもの
    - ``damage#i``: そのワザで相手に与えたダメージのログ（``damage_prevented`` は数えない）。``self_damage#i``: 自分へのダメージのログ
    - ``base#i=N``: 相手へのダメージの基本となるダメージ（p.321 の 1 段階。「みずでっぽう」の追加・コインのダメージの「おもて」の数を見る）
    - ``<ログの種類>#i``: そのワザの中に出た結果のログ（``RESULT_EVENTS``。特殊状態は ``special_condition_<状態>#i``）。v0.30 のワザの
      エネルギーのトラッシュは ``discard_energy#i``、トラッシュのあとダメージのログが続いたものは ``discard_then_damage#i``
    - ``protected_by_own_effect``: 自分のワザ（まるまる・からをとじる）の効果で、相手のワザのダメージを受けなかった回数（``damage_prevented``）。
      ``effect_removed_<理由>``: そのカードの持続する効果が消えた回数（``expired``・``retreat``・``switch``・``knock_out`` など）
    - ``knocked_out``: きぜつした回数
    - v0.31: ``energy_burn``（エナジーバーン）・``power_heal``（しぜんになおる）・``power_heal_on_attach``（ほのおでかいふく）: 特殊能力のログの数
    - v0.32: ``benched_from_deck``: ワザの効果（なかまをよぶ・ふえる）で山札からベンチに出された回数（``in_play`` にも数える）
    - v0.33: ``opponent_bench_damage#i``・``self_bench_damage#i``: v0.33 のカードのワザが控えポケモンに与えたダメージのログ（v0.34 のうしろなげも）
    - v0.40: ``bench_from_deck_declined#i``・``shuffle#i``（ワザの効果で切った山札）・``opponent_coin_<面>#i``（相手が投げたワザのコイン）
    """
    card = {uid: c.card_id for uid, c in state.cards.items()}
    uses = {cid: Counter() for cid in TARGETS}
    current = None  # (カード id, ワザの位置)
    attacker = None  # ワザを使ったプレイヤー
    discarded = False
    for e in state.log:
        kind = e["kind"]
        if kind == "place_starting_pokemon":
            for uid in (e["active"], *e["bench"]):
                if card[uid] in uses:
                    uses[card[uid]]["in_play"] += 1
        elif kind == "play_to_bench" and card[e["card"]] in uses:
            uses[card[e["card"]]]["in_play"] += 1
        elif kind == "bench_from_deck" and card[e["card"]] in uses:
            uses[card[e["card"]]]["in_play"] += 1  # v0.32: ワザの効果で山札からベンチに出した
            uses[card[e["card"]]]["benched_from_deck"] += 1
        elif kind == "evolve" and card[e["to_card"]] in uses:
            uses[card[e["to_card"]]]["evolved_to"] += 1
        elif kind == "knock_out" and card.get(e.get("pokemon")) in uses:
            uses[card[e["pokemon"]]]["knocked_out"] += 1
        elif kind == "damage_prevented" and card[e["pokemon"]] in uses and e.get("source_card") == e["pokemon"]:
            uses[card[e["pokemon"]]]["protected_by_own_effect"] += 1  # 「まるまる」「からをとじる」の効果で、相手のワザのダメージを受けなかった
        elif kind == "persistent_effect_removed" and card[e["pokemon"]] in uses:
            uses[card[e["pokemon"]]][f"effect_removed_{e['reason']}"] += 1
        elif kind == "attack_check" and card[e["source_card"]] in uses:
            # v0.36: 相手が、このカードのワザ（すなかけ・えんまくなど）の効果を受けてワザを使ったときの手順 4 のコイン（結果ごと）
            uses[card[e["source_card"]]][f"attack_check_{e['result']}"] += 1
        elif kind == "persistent_effect_added" and card[e["source_card"]] in uses and e["persistent_effect"] in ("attack_coin_check", "cannot_retreat") \
                and e["source_card"] != e["pokemon"]:
            uses[card[e["source_card"]]][f"gave_{e['persistent_effect']}"] += 1  # v0.36: 相手に与えた効果（まねたワザで与えたものも）
        elif kind == "damage" and any(card.get(m[1]) in V0_37 + V0_38 for m in e.get("modifiers", ())):
            for step, source, _ in e["modifiers"]:  # v0.37: ちいさくなる（8 段階）・かみつく（2 段階）、v0.38: バリアアタック（8 段階）でへったダメージ
                if card.get(source) in V0_37 + V0_38:
                    uses[card[source]][f"reduced_step{step}"] += 1
        if kind in ("energy_burn", "power_heal") and card[e["pokemon"]] in uses:
            # v0.31: 特殊能力（エナジーバーン・しぜんになおる・ほのおでかいふく（つけたカード ``trigger`` があるもの））
            uses[card[e["pokemon"]]]["power_heal_on_attach" if "trigger" in e else kind] += 1
        if kind == "attack":
            discarded = False
            current = (card[e["pokemon"]], e["attack_index"]) if card[e["pokemon"]] in uses else None
            attacker = e["player"]
            if current is not None:
                uses[current[0]][f"attack#{current[1]}"] += 1
        elif kind in ("turn_end", "turn_start"):
            current = None
        elif current is not None:
            cid, index = current
            if kind == "confusion_damage":
                uses[cid][f"confused_failed#{index}"] += 1
            elif kind == "damage" and not e.get("retaliation") and e.get("target") == "self":
                uses[cid][f"self_damage#{index}"] += 1
                if e.get("damage_multiplied"):
                    uses[cid][f"self_damage_multiplied#{index}"] += 1  # v0.35: マチスのラッタのきあいだめ（自分へのダメージも 2 倍）
            elif kind == "damage" and not e.get("retaliation") and e.get("target") in ("opponent_bench", "self_bench") and cid in V0_33 + V0_34 + V0_37 + V0_38 + V0_39 + V0_40:
                uses[cid][f"{e['target']}_damage#{index}"] += 1  # v0.33: 控えポケモンへのダメージ（かけぬける・ミニじしん）
            elif kind == "damage" and not e.get("retaliation") and "target" not in e:
                uses[cid][f"damage#{index}"] += 1
                uses[cid][f"base#{index}={e['steps'][0][1]}"] += 1
                if e.get("damage_multiplied"):
                    uses[cid][f"damage_multiplied#{index}"] += 1  # v0.35: きあいだめの 2 倍
                if e.get("step_orders"):
                    uses[cid][f"step_order#{index}"] += 1  # v0.35: 同じ段階の計算の順番を決定で選んだ
            elif kind == "special_condition" and e.get("effect") == f"{cid}#{index}":
                uses[cid][f"special_condition_{e['condition']}#{index}"] += 1
            elif kind in RESULT_EVENTS and kind != "special_condition":
                uses[cid][f"{kind}#{index}"] += 1
            elif kind in V038_RESULT_EVENTS and cid in V0_38:
                uses[cid][f"{kind}#{index}"] += 1  # v0.38: いなくなる・でんれいのログ
            elif kind in V040_RESULT_EVENTS and cid in V0_40 and (kind != "shuffle" or e.get("effect") == f"{cid}#{index}"):
                uses[cid][f"{kind}#{index}"] += 1  # v0.40: むれでおそうで出さなかった・ワザの効果で山札を切った
            elif kind == "coin_flip" and cid in V0_40 and e["source"] == "attack" and e["player"] != attacker:
                uses[cid][f"opponent_coin_{e['result']}#{index}"] += 1  # v0.40: ベンチをあやつる（相手が投げるコイン）
            if kind == "discard_energy":
                discarded = True
            elif discarded and ((kind == "damage" and "target" not in e and not e.get("retaliation"))
                                or (kind == "damage_prevented" and e["target"] == "opponent_active") or kind == "attack_evaded"):
                uses[cid][f"discard_then_damage#{index}"] += 1  # v0.30: トラッシュのあとに、そのワザのダメージの要素
                discarded = False
    return {cid: dict(c) for cid, c in uses.items() if c}


def summarize(games):
    """1 組（または全体）の集計。終わり方・停止のコード・``UNRESOLVED_…`` のあと続けた回数・監査の失敗・対象のカードの動きの合計と局数。"""
    s = {"games": len(games), "outcomes": Counter(r["outcome"] for r in games), "halt_codes": Counter(r["halt_code"] for r in games
                                                                                                     if r.get("halt_code")),
         "unresolved_rejections": Counter(), "audit_failures": Counter(), "end_conditions": Counter(), "wins": Counter(),
         "cards": {}, "games_with": {}}
    for r in games:
        s["unresolved_rejections"].update(r["unresolved_rejections"])
        s["audit_failures"].update(r["audit"])
        s["end_conditions"].update(r.get("conditions", []))
        if r.get("winner_deck"):
            s["wins"][r["winner_deck"]] += 1
        for cid, counts in r.get("card_uses", {}).items():
            s["cards"].setdefault(cid, Counter()).update(counts)
            s["games_with"].setdefault(cid, Counter()).update({k: 1 for k, v in counts.items() if v})
    return json.loads(json.dumps(s))


def run(seeds, *, max_steps=8000, pairings=PAIRINGS):
    results = {}
    for a, b in pairings:
        games = [play(seat, seed, max_steps=max_steps) for seat in ((a, b), (b, a)) for seed in seeds]
        results[f"{a}-{b}"] = {"games": games, "summary": summarize(games)}
    return results


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--batch", choices=sorted(BATCHES), default="v0.28", help="組の一覧（v0.28・v0.29・v0.30・v0.32〜v0.36 のどれかの 3 組、v0.31・v0.37〜v0.40 の 4 組）")
    parser.add_argument("--seeds", type=int, default=10, help="組ごと・席ごとの seed の数（1 組の局数はこの 2 倍。1 以上）")
    parser.add_argument("--start", type=int, default=0, help="最初の seed")
    parser.add_argument("--max-steps", type=int, default=8000)
    parser.add_argument("--out", type=Path, help="1 局ごとの記録と集計を書き出す JSON")
    args = parser.parse_args(argv)
    if args.seeds < 1:
        parser.error("--seeds は 1 以上")
    seeds = range(args.start, args.start + args.seeds)
    began = time.time()
    results = run(seeds, max_steps=args.max_steps, pairings=BATCHES[args.batch])
    total = summarize([g for v in results.values() for g in v["games"]])
    elapsed = round(time.time() - began, 1)
    if args.out:
        args.out.write_text(json.dumps({"batch": args.batch, "seeds": [args.start, args.start + args.seeds], "elapsed": elapsed, "runs": results, "total": total},
                                       ensure_ascii=False, indent=1), encoding="utf-8")
    brief = {name: {k: v["summary"][k] for k in ("games", "outcomes", "halt_codes", "unresolved_rejections", "audit_failures")}
             for name, v in results.items()}
    print(json.dumps({"elapsed": elapsed, "runs": brief, "total_cards": total["cards"]}, ensure_ascii=False))
    bad = sum(total["outcomes"].get(k, 0) for k in ("internal_error", "unexpected_rejection", "step_limit"))
    bad += sum(total["audit_failures"].values())
    return 0 if bad == 0 else 1


if __name__ == "__main__":
    sys.exit(main())

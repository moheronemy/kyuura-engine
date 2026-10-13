"""大規模なストレス実行（v0.4e のテストの段階 C。docs/integration-audit-v0.4e.md 10 章）。ふだんの単体テストでは走らせない。

使い方（リポジトリの直下で）::

    python3 tools/stress_engine.py                         # すべての組 × 40 seed × 600 手
    python3 tools/stress_engine.py --seeds 200 --steps 800 --report stress.json
    python3 tools/stress_engine.py --scenario butterfree --start 1000 --seeds 50
    python3 tools/stress_engine.py --scenario venusaur --scenario venusaur_status   # v0.5（ポケモンパワー）
    python3 tools/stress_engine.py --scenario blastoise --scenario blastoise_mixed  # v0.6（あまごい）
    python3 tools/stress_engine.py --scenario alakazam --scenario alakazam_mixed    # v0.7（ダメージスワップ）
    python3 tools/stress_engine.py --scenario muk --scenario muk_mixed              # v0.8（かがくへんかガス）
    python3 tools/stress_engine.py --scenario haunter --scenario haunter_muk        # v0.9（とうめい）
    python3 tools/stress_engine.py --scenario machamp --scenario machamp_mixed      # v0.10（はんげき）
    python3 tools/stress_engine.py --scenario giovanni --scenario giovanni_mixed    # v0.11（こんじょう）
    python3 tools/stress_engine.py --scenario moltres --scenario moltres_mixed      # v0.12（ふしちょう・ほのおのかべ）
    python3 tools/stress_engine.py --scenario wartortle --scenario wartortle_mixed  # v0.13（こうらがえし）

- 今の作業ツリーのエンジンを、tools/compat_driver.py の組（デッキ）と駆動（ルール上できそうな操作と、わざと不正な操作を混ぜる。
  ``--illegal-rate`` で割合を変える）で動かす。
- 1 手ごとに: 受け付けたら、返った状態は ``apply_command`` が不変条件で確かめている。拒否したら、渡した状態・乱数・ログが
  変わっていないことを確かめる。書き出しの監査（tests/log_audit.py の ``serialization_problems``）は ``--serialize-every`` 手ごと。
  対戦の終わりに、ログと状態の整合（``log_problems``）を確かめる。
- 結果を分類して数える: 受け付けた操作・ルール上できない操作（``IllegalActionError``）・未対応の操作（``UNSUPPORTED_…``）・原典で
  決められない裁定（``UNRESOLVED_…``。拒否）・止めた対戦（``HALTED``）・勝敗（``GAME_OVER``）・サドン・デス・内部の誤り。
  拒否と HALTED は別に数える。
- 問題（内部の誤り・壊れた状態・拒否で変わった状態・ログや書き出しの問題）のあった seed を ``--report`` に書く。終了コード 1。
- v0.5: ポケモンパワーの組（``POWER_SCENARIOS``。フシギバナのデッキ）を加えた。駆動（tools/compat_driver.py）は版の比較の参照データと
  結びついているので変えず、ここで、自分の番に場にフシギバナがいるときだけ、エナジートランスの使用（ルール上できそうなものと、
  わざと不正なもの）を混ぜる（``choose_command``）。フシギバナのいない組では駆動とまったく同じ操作になる（駆動用の乱数も同じに使う）。
- v0.6: カメックスの組（``blastoise``・``blastoise_mixed``）を加え、自分の場にカメックスがいる番に、あまごいの使用（手札の「水」
  エネルギーを自分の「水」ポケモンへ。わざと不正なもの（手札にないカード・相手の手札のカード・つけたカード・水でないエネルギー・
  水でないポケモン・相手のポケモン・移動元の指定・番でない・ない番号）も）を混ぜる。フシギバナ・カメックスのどちらもいない組では
  駆動とまったく同じ操作になり、フシギバナだけの組では v0.5 と同じ操作になる（乱数の使い方を変えていない）。拒否の前後の比較と
  書き出しの監査は形式 9（v0.6 の ``energy_attached_by_powers_this_turn`` を含む）。
- v0.7: フーディンの組（``alakazam``・``alakazam_mixed``。``alakazam_mixed`` はフシギバナ・カメックス・フーディンを同じデッキに入れる）を
  加え、自分の場にフーディンがいる番に、ダメージスワップの使用（自分の場のダメージカウンターがのったポケモンから、自分の場の別の
  ポケモンへ 1 個。わざと不正なもの（同じポケモン・カウンターのないポケモン・きぜつする移動先・相手のポケモン・エネルギーの指定・
  選ばせるものの不足・番でない・ない番号・ない位置・パワーのないポケモン）も）を混ぜる。ユンゲラーの「じこさいせい」の決定
  （``DISCARD_ENERGY``）は駆動がほかの決定と同じに答える。フーディンのいない組では v0.6 と同じ操作になる（乱数の使い方を変えていない。
  ポケモンパワーを持つポケモンの種類の並び ``POWER_USERS`` の最後に加えたので、フシギバナ・カメックスだけの組の選び方は同じ）。
- v0.8: ベトベトンの組（``muk``・``muk_mixed``。``muk_mixed`` は両方のデッキにベトベトン）を加えた。自分の場にベトベトンがいる番は、
  ときどき「かがくへんかガス」の使用を試す（常にはたらいていて宣言しないので ``POWER_NOT_DECLARABLE`` になるはず）。特殊能力の使用の
  たびに、エンジンとは別に、その時点の場からかがくへんかガスに消されているか（``power_suppressors``）を求め、消されているのに受け付けた・
  消されていないのに ``POWER_SUPPRESSED`` で拒否した、を問題として数える。MAIN の手ごとに、かがくへんかガスがはたらいているか・
  ベトベトンがいるのに消えているか・切り替わったかを数える。``POWER_USERS`` の最後に加えたので、ベトベトンのいない組の操作は v0.7 と同じ。
- v0.9: ゴーストの組（``haunter``・``haunter_muk``。``haunter_muk`` は両方のデッキにゴースト、一方にベトベトン）を加えた。自分の場にゴースト
  がいる番は、ときどき「とうめい」の使用を試す（自動的にはたらいていて宣言しないので ``POWER_NOT_DECLARABLE`` になるはず）。ワザを
  受け付けるたびに、ワザの前の場の ``working_evasion_power``（エンジンの公開の問い合わせ）と比べて、「とうめい」の判定（``evade_check``）は
  はたらいているゴーストだけ・コインはゴースト側のプレイヤー・はたらいているバトル場のゴーストが判定なしでダメージを受けていないことを
  確かめ、判定・「おもて」「うら」・受けなかった要素・ガスや特殊状態で消えていたゴーストへのワザを数える。``UNRESOLVED_EVADED_EFFECT_COIN``
  で止めたら、相手の対戦ポケモンの「とうめい」がはたらいていることを確かめる。エナジーへんかんの決定には、駆動が 0〜2 枚で答える（0 枚は
  ``UNRESOLVED_RECOVER_ZERO_ENERGY`` で止まり、状態は変わらない）。``POWER_USERS`` の最後に加えたので、ゴーストのいない組の操作は v0.8 と同じ。
- v0.10: カイリキーの組（``machamp``・``machamp_mixed``。``machamp_mixed`` は両方のデッキにカイリキー、一方にベトベトン、もう一方にゴースト）を
  加えた。自分の場にカイリキーがいる番は、ときどき「はんげき」の使用を試す（自動的にはたらいて宣言しないので ``POWER_NOT_DECLARABLE`` に
  なるはず）。ワザ（と決定の答え）を受け付けるたびに、ワザの前の場の ``working_counterattack_power``（エンジンの公開の問い合わせ）と比べて、
  相手のワザのダメージ（0 より大きい）を、はたらいている「はんげき」を持つポケモンが受けたときだけ ``counterattack``（か
  ``counterattack_skipped``）があり、与える相手がワザを使ったポケモン・量が 10 であることを確かめ、回数・きぜつ・きぜつしたカイリキーの
  反撃・ベンチ・ガスや特殊状態で消えていたカイリキーへのワザを数える。``UNRESOLVED_COUNTERATTACK_DOUBLE_KNOCKOUT`` で止めたら、相手の
  対戦ポケモンの「はんげき」がはたらいていることを確かめる。``POWER_USERS`` の最後に加えたので、カイリキーのいない組の操作は v0.9 と同じ。
- v0.11: サカキのカイリキーの組（``giovanni``・``giovanni_mixed``。``giovanni`` はサカキのカイリキーの系統とエビワラーのデッキと、サカキの
  カイリキーに使うワザの種類を多くしたデッキ（ユンゲラー・カイリキー・ピカチュウ・ロコン・キャタピー・ベトベトン）、``giovanni_mixed`` は
  両方のデッキにサカキのカイリキー、一方にベトベトン・ゴースト、もう一方にカイリキー・ロコン）を加えた。自分の場にサカキのカイリキーがいる番は、
  ときどき UsePokemonPower で「こんじょう」を試す（決められたときにしか使えないので ``POWER_NOT_USABLE_NOW``、かがくへんかガスがはたらいて
  いれば ``POWER_SUPPRESSED`` になるはず）。「こんじょう」を使うかの決定（``KO_PREVENTION``。選ぶ数 0〜1）には、駆動がほかの決定と同じに
  答える（使う・使わない）。ワザ・決定の答え・番の終わりを受け付けるたびに、操作の前の場の ``available_ko_prevention_power``（エンジンの
  公開の問い合わせ）と比べて、決定が出るのは使える「こんじょう」のポケモンが相手のワザで HP 以上になったときだけ・「おもて」なら残り HP 10・
  使えるのに決定がないままきぜつしていないことを確かめ、決定・使う・使わない・「おもて」「うら」・ガスや特殊状態で使えずにきぜつ・どく
  できぜつを数える。``UNRESOLVED_KO_PREVENTION_ATTACK_EFFECT`` で止めたら、相手の対戦ポケモンの「こんじょう」を使えることを確かめる。
  ``POWER_USERS`` の最後に加えたので、サカキのカイリキーのいない組の操作は v0.10 と同じ。
- v0.12: R団のファイヤーの組（``moltres``・``moltres_mixed``。``moltres`` は R団のファイヤーと炎のたねポケモンのデッキと、R団のファイヤーに
  使うワザ・特殊能力の種類を多くしたデッキ（カイリキー・ゴースト・ベトベトン・バタフリー・ビードル・ユンゲラー・ピカチュウ・サカキのカイリキー）、
  ``moltres_mixed`` は両方のデッキに R団のファイヤー、一方にベトベトン・ゴースト・ロコン、もう一方にカイリキー・バタフリー）を加えた。自分の場に
  R団のファイヤーがいる番は、ときどき UsePokemonPower で「ふしちょう」を試す（場にいるときは使えないので ``POWER_NOT_USABLE_NOW``、
  かがくへんかガスがはたらいていれば ``POWER_SUPPRESSED`` になるはず）。「ふしちょう」を使うかの決定（``POST_KNOCKOUT_POWER``。選ぶ数 0〜1）
  には、駆動がほかの決定と同じに答える（使う・使わない）。操作を受け付けるたびに、操作の前の場（特殊状態・かがくへんかガス）とログから、
  R団のファイヤーがきぜつしたら（対戦が終わらなければ）決定が出ること・使えないのに決定が出ないこと・回収したのはそのカードだけで手札に
  あること、今の番にはたらく「ほのおのかべ」を持つポケモンが相手のワザのダメージを受けたら「ほのおのかべ」があること・ワザを使ったポケモン
  へのダメージの基本となるダメージが 10 であることを確かめ、決定・使う・使わない・回収・特殊状態やガスで使えない・効果・はたらいた・
  ダメージ・期限で消えたを数える。``UNRESOLVED_RETALIATION_DOUBLE_KNOCKOUT`` で止めたら、相手の対戦ポケモンに今の番にはたらく
  「ほのおのかべ」があることを確かめる。``POWER_USERS`` の最後に加えたので、R団のファイヤーのいない組の操作は v0.11 と同じ。
- v0.13: わるいカメールの組（``wartortle``・``wartortle_mixed``。``wartortle`` はわるいカメールのデッキと、わるいカメールに使うワザ・特殊能力の
  種類を多くしたデッキ（ピカチュウ（わるいカメールの弱点 雷）・ポニータ・ガーディ（弱点 水）・カイリキー・ゴースト・バタフリー・ビードル・
  ベトベトン・サカキのカイリキー）、``wartortle_mixed`` は両方のデッキにわるいカメール、一方に R団のファイヤー・ポニータ・ロコン、もう一方に
  ピカチュウ・ドードー・バタフリー）を加えた。わるいカメールはポケモンパワーを持たないので ``POWER_USERS`` は変えていない（ほかの組の操作は
  v0.12 と同じ。組ごとの乱数は組の名前から作る）。操作を受け付けるたびに、操作の前の場とログから、今の番にはたらく「こうらがえし」を持つ
  ポケモンが相手のワザのダメージを受けたら「こうらがえし」があること・受けたダメージ（received_damage）と基本となるダメージがそのダメージの
  最終ダメージと同じこと・返すダメージの基本となる計算がその値で、受けたのがワザを使ったポケモンであることを確かめ（``_observe_shell``）、
  効果・はたらいた・受けたダメージの合計・返したダメージ（合計・弱点・抵抗力・ディフェンダー・きぜつ）・「とうめい」・期限で消えた・S37 を
  数える。``UNRESOLVED_RETALIATION_DOUBLE_KNOCKOUT`` で止めたら、相手の対戦ポケモンに今の番にはたらく「ほのおのかべ」か「こうらがえし」が
  あることを確かめる。``_observe_moltres`` は「ほのおのかべ」（効果を与えたワザが R団のファイヤーの位置 0）のログだけを数える（R団のファイヤーの
  組の数は v0.12 と同じ）。
"""

from __future__ import annotations

import argparse
import json
import pathlib
import random
import sys
import time
from collections import Counter

ROOT = pathlib.Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import kyuura_engine as engine  # noqa: E402
from kyuura_engine.rng import rng_fingerprint  # noqa: E402

from tests.log_audit import log_problems, serialization_problems  # noqa: E402

sys.path.insert(0, str(ROOT / "tools"))
import compat_driver as driver  # noqa: E402


VENUSAUR, IVYSAUR, BULBASAUR = "PMCG1-011", "PMCG1-008", "PMCG1-001"
POWER_SCENARIOS = (
    driver.Scenario("venusaur", {BULBASAUR: 4, IVYSAUR: 4, VENUSAUR: 4, driver.WEEDLE: 4, driver.KAKUNA: 2, driver.SWITCH: 2,
                                 driver.POTION: 2, driver.BILL: 2, driver.PLUSPOWER: 2, driver.GRASS: 30, driver.FIRE: 4},
                    {BULBASAUR: 4, IVYSAUR: 3, VENUSAUR: 3, driver.VULPIX: 3, driver.PARAS: 3, driver.CATERPIE: 3, driver.DEFENDER: 2,
                     driver.BILL: 2, driver.GRASS: 31, driver.FIRE: 6}, tuple(range(6)), tags=("フシギバナ", "エナジートランス")),
    driver.Scenario("venusaur_status", {BULBASAUR: 4, IVYSAUR: 3, VENUSAUR: 3, driver.BUTTERFREE: 2, driver.METAPOD: 2,
                                        driver.CATERPIE: 3, driver.SWITCH: 2, driver.DEFENDER: 2, driver.GRASS: 39},
                    {driver.VULPIX: 4, driver.PARAS: 4, driver.CATERPIE: 4, driver.WEEDLE: 4, BULBASAUR: 3, IVYSAUR: 3, VENUSAUR: 2,
                     driver.POTION: 2, driver.GRASS: 26, driver.FIRE: 8}, tuple(range(6)), tags=("フシギバナ", "特殊状態", "ふきとばし")),
)
BLASTOISE, WARTORTLE, SQUIRTLE = "PMCG1-032", "PMCG1-027", "PMCG1-023"
POWER_SCENARIOS += (
    driver.Scenario("blastoise", {SQUIRTLE: 4, WARTORTLE: 4, BLASTOISE: 4, driver.SEEL: 3, driver.DEWGONG: 2, driver.STARYU: 3,
                                  driver.SWITCH: 2, driver.POTION: 2, driver.BILL: 2, driver.PLUSPOWER: 2, driver.WATER: 28, driver.FIRE: 4},
                    {SQUIRTLE: 4, WARTORTLE: 3, BLASTOISE: 3, driver.PIKACHU: 4, driver.VULPIX: 3, driver.CATERPIE: 3, driver.DEFENDER: 2,
                     driver.BILL: 2, driver.WATER: 24, driver.LIGHTNING: 6, driver.FIRE: 6}, tuple(range(6)), tags=("カメックス", "あまごい")),
    driver.Scenario("blastoise_mixed", {SQUIRTLE: 4, WARTORTLE: 3, BLASTOISE: 3, BULBASAUR: 3, IVYSAUR: 2, VENUSAUR: 2, driver.SEEL: 2,
                                        driver.SWITCH: 2, driver.DEFENDER: 2, driver.WATER: 25, driver.GRASS: 12},
                    {driver.VULPIX: 4, driver.PARAS: 4, driver.CATERPIE: 4, driver.WEEDLE: 4, SQUIRTLE: 3, WARTORTLE: 2, BLASTOISE: 2,
                     driver.BUTTERFREE: 2, driver.METAPOD: 2, driver.POTION: 2, driver.WATER: 15, driver.GRASS: 10, driver.FIRE: 6},
                    tuple(range(6)), tags=("カメックス", "フシギバナ", "特殊状態", "ふきとばし")),
)
ALAKAZAM, KADABRA, ABRA, PSYCHIC = "PMCG1-049", "PMCG1-046", "PMCG1-043", "PMCG1-101"
POWER_SCENARIOS += (
    driver.Scenario("alakazam", {ABRA: 4, KADABRA: 4, ALAKAZAM: 4, driver.DODUO: 3, driver.RATTATA: 3, driver.SWITCH: 2, driver.POTION: 2,
                                 driver.BILL: 2, driver.DEFENDER: 2, driver.PLUSPOWER: 2, PSYCHIC: 28, driver.FIRE: 4},
                    {ABRA: 4, KADABRA: 3, ALAKAZAM: 3, driver.VULPIX: 3, driver.WEEDLE: 3, driver.CATERPIE: 3, driver.DEFENDER: 2,
                     driver.BILL: 2, PSYCHIC: 25, driver.GRASS: 6, driver.FIRE: 6}, tuple(range(6)), tags=("フーディン", "ダメージスワップ")),
    driver.Scenario("alakazam_mixed", {BULBASAUR: 3, IVYSAUR: 2, VENUSAUR: 2, SQUIRTLE: 3, WARTORTLE: 2, BLASTOISE: 2, ABRA: 3, KADABRA: 3,
                                       ALAKAZAM: 3, driver.SWITCH: 2, driver.POTION: 2, driver.GRASS: 11, driver.WATER: 11, PSYCHIC: 11},
                    {driver.VULPIX: 4, driver.PARAS: 4, driver.CATERPIE: 4, driver.WEEDLE: 4, ABRA: 3, KADABRA: 3, ALAKAZAM: 2,
                     driver.BUTTERFREE: 2, driver.METAPOD: 2, driver.POTION: 2, PSYCHIC: 14, driver.GRASS: 10, driver.FIRE: 6},
                    tuple(range(6)), tags=("フーディン", "カメックス", "フシギバナ", "特殊状態", "ふきとばし")),
)
MUK, GRIMER = "PMCG3-007", "PMCG4-004"
POWER_SCENARIOS += (
    # ベトベトン（v0.8。かがくへんかガス）: 自分のフシギバナ・相手のフーディン・カメックスの特殊能力を消す。相手はロコン（こんらん）・
    # キャタピー（マヒ）・パラス（ねむり）・ケーシィ（マヒ）でベトベトンの力を消し、ポケモンいれかえ・にげるで特殊状態が消える
    driver.Scenario("muk", {GRIMER: 4, MUK: 4, BULBASAUR: 3, IVYSAUR: 3, VENUSAUR: 3, driver.SWITCH: 2, driver.POTION: 2, driver.BILL: 2,
                            driver.DEFENDER: 2, driver.GRASS: 35},
                    {ABRA: 3, KADABRA: 3, ALAKAZAM: 3, SQUIRTLE: 3, WARTORTLE: 2, BLASTOISE: 2, driver.VULPIX: 3, driver.CATERPIE: 3,
                     driver.PARAS: 3, driver.SWITCH: 2, PSYCHIC: 14, driver.WATER: 10, driver.GRASS: 4, driver.FIRE: 5},
                    tuple(range(6)), tags=("ベトベトン", "かがくへんかガス", "フシギバナ", "フーディン", "カメックス", "特殊状態")),
    # 両方のデッキにベトベトン（両方のかがくへんかガス・どちらかだけがはたらいている場面）
    driver.Scenario("muk_mixed", {GRIMER: 4, MUK: 3, ABRA: 3, KADABRA: 3, ALAKAZAM: 3, driver.VULPIX: 3, driver.SWITCH: 2, driver.POTION: 2,
                                  driver.GRASS: 18, PSYCHIC: 15, driver.FIRE: 4},
                    {GRIMER: 4, MUK: 3, SQUIRTLE: 3, WARTORTLE: 3, BLASTOISE: 3, driver.CATERPIE: 3, driver.PARAS: 3, driver.DEFENDER: 2,
                     driver.BILL: 2, driver.GRASS: 18, driver.WATER: 16},
                    tuple(range(6)), tags=("ベトベトン", "かがくへんかガス", "フーディン", "カメックス", "特殊状態")),
)
GASTLY, HAUNTER = "PMCG3-029", "PMCG3-030"
POWER_SCENARIOS += (
    # ゴースト（v0.9。とうめい）: 相手はダメージだけ・ダメージとどく（フシギソウ）・ふきとばし・メガドレイン（バタフリー）・キノコのほうし
    # （パラス）・でんげき（ピカチュウ）・抵抗力で 0（ワンリキー）・みだれづき（ドードー）・どくばり（ビードル。T19b で止まる）・どくガス・
    # ねばりつく（ロケット団のベトベター）
    driver.Scenario("haunter", {GASTLY: 4, HAUNTER: 4, driver.RATTATA: 3, driver.DODUO: 3, driver.SWITCH: 2, driver.POTION: 2,
                                driver.BILL: 2, driver.DEFENDER: 2, PSYCHIC: 30, driver.FIRE: 8},
                    {BULBASAUR: 3, IVYSAUR: 3, driver.CATERPIE: 3, driver.METAPOD: 2, driver.BUTTERFREE: 2, driver.PARAS: 3,
                     driver.PIKACHU: 2, driver.MACHOP: 2, driver.WEEDLE: 2, GRIMER: 2, driver.PLUSPOWER: 2, driver.GRASS: 28,
                     driver.LIGHTNING: 3, driver.FIGHTING: 3},
                    tuple(range(6)), tags=("ゴースト", "とうめい", "特殊状態", "ふきとばし")),
    # 両方のデッキにゴースト（あくむ）、一方にベトベトン（かがくへんかガスで「とうめい」が消える）・ロコン・キャタピー（特殊状態で消える）
    driver.Scenario("haunter_muk", {GASTLY: 4, HAUNTER: 3, GRIMER: 3, MUK: 3, driver.VULPIX: 3, driver.SWITCH: 2, driver.POTION: 2,
                                    PSYCHIC: 20, driver.GRASS: 16, driver.FIRE: 4},
                    {GASTLY: 4, HAUNTER: 3, ABRA: 3, KADABRA: 2, driver.CATERPIE: 3, driver.PARAS: 3, driver.RATTATA: 3, driver.DEFENDER: 2,
                     driver.BILL: 2, PSYCHIC: 25, driver.GRASS: 10},
                    tuple(range(6)), tags=("ゴースト", "とうめい", "ベトベトン", "かがくへんかガス", "特殊状態")),
)
MACHOKE, MACHAMP = "PMCG1-055", "PMCG1-057"
POWER_SCENARIOS += (
    # カイリキー（v0.10。はんげき）: 相手はダメージだけ（ケーシィの弱点 2 倍・ユンゲラー）・でんげき（ピカチュウ。自分へのダメージ）・
    # ふきとばし・メガドレイン（バタフリー）・やどりぎのタネ・どくのこな（フシギダネ・フシギソウ）・いとをはく（キャタピー）・
    # みだれづき（ドードー）・ディフェンダー・プラスパワー
    driver.Scenario("machamp", {driver.MACHOP: 4, MACHOKE: 4, MACHAMP: 4, driver.HITMONCHAN: 3, driver.SWITCH: 2, driver.POTION: 2,
                                driver.BILL: 2, driver.PLUSPOWER: 2, driver.DEFENDER: 2, driver.FIGHTING: 35},
                    {driver.PIKACHU: 3, driver.CATERPIE: 3, driver.METAPOD: 2, driver.BUTTERFREE: 2, BULBASAUR: 3, IVYSAUR: 2, ABRA: 3,
                     KADABRA: 2, driver.DODUO: 2, driver.DEFENDER: 2, driver.PLUSPOWER: 2, driver.BILL: 2, driver.GRASS: 18,
                     driver.LIGHTNING: 6, PSYCHIC: 8},
                    tuple(range(6)), tags=("カイリキー", "はんげき", "メガドレイン", "ふきとばし", "特殊状態")),
    # 両方のデッキにカイリキー（ミラー。「はんげき」のダメージで「はんげき」ははたらかない）、一方にベトベトン（かがくへんかガスで消える）・
    # ロコン（こんらん）、もう一方にゴースト（とうめい・抵抗力。「はんげき」は受ける）・ビードル（どく）・パラス（ねむり）
    driver.Scenario("machamp_mixed", {driver.MACHOP: 4, MACHOKE: 3, MACHAMP: 3, GRIMER: 3, MUK: 3, driver.VULPIX: 2, driver.SWITCH: 2,
                                      driver.POTION: 2, driver.FIGHTING: 26, driver.GRASS: 12},
                    {driver.MACHOP: 4, MACHOKE: 3, MACHAMP: 3, GASTLY: 3, HAUNTER: 2, driver.WEEDLE: 3, driver.PARAS: 2,
                     driver.DEFENDER: 2, driver.BILL: 2, driver.FIGHTING: 20, PSYCHIC: 10, driver.GRASS: 6},
                    tuple(range(6)), tags=("カイリキー", "はんげき", "ベトベトン", "かがくへんかガス", "ゴースト", "とうめい", "特殊状態")),
)
GIOVANNIS_MACHOP, GIOVANNIS_MACHOKE, GIOVANNIS_MACHAMP = "PMCG6-057", "PMCG6-059", "PMCG6-061"
POWER_SCENARIOS += (
    # サカキのカイリキー（v0.11。こんじょう）: 相手はダメージだけ（ユンゲラーのちょうねんりき 50 × 弱点 2・カイリキーのちきゅうなげ）・でんげき
    # （ピカチュウ）・いとをはく（キャタピー。G37 で止まる）・あやしいひかり（ロコン）・ベトベトン（かがくへんかガス）・プラスパワー
    driver.Scenario("giovanni", {GIOVANNIS_MACHOP: 4, GIOVANNIS_MACHOKE: 4, GIOVANNIS_MACHAMP: 4, driver.HITMONCHAN: 2, driver.SWITCH: 2,
                                 driver.POTION: 2, driver.BILL: 4, driver.DEFENDER: 2, driver.PLUSPOWER: 2, driver.FIGHTING: 34},
                    {ABRA: 3, KADABRA: 3, driver.MACHOP: 3, MACHOKE: 2, MACHAMP: 2, driver.PIKACHU: 2, driver.CATERPIE: 2, driver.VULPIX: 2,
                     GRIMER: 2, MUK: 1, driver.PLUSPOWER: 2, driver.BILL: 4, PSYCHIC: 10, driver.FIGHTING: 12, driver.LIGHTNING: 3,
                     driver.GRASS: 4, driver.FIRE: 3},
                    tuple(range(6)), tags=("サカキのカイリキー", "こんじょう", "ハリケーンパンチ", "はんげき", "かがくへんかガス", "特殊状態")),
    # 両方のデッキにサカキのカイリキー（ミラー。いちかばちか・じごくがため・いかりのスーパーパンチ）、一方にベトベトン・ゴースト（とうめい）、
    # もう一方にカイリキー（はんげき）・ロコン（こんらん）
    driver.Scenario("giovanni_mixed", {GIOVANNIS_MACHOP: 4, GIOVANNIS_MACHOKE: 3, GIOVANNIS_MACHAMP: 3, GRIMER: 3, MUK: 2, GASTLY: 2,
                                       HAUNTER: 2, driver.SWITCH: 2, driver.POTION: 2, driver.FIGHTING: 22, PSYCHIC: 8, driver.GRASS: 7},
                    {GIOVANNIS_MACHOP: 4, GIOVANNIS_MACHOKE: 3, GIOVANNIS_MACHAMP: 3, driver.MACHOP: 2, MACHOKE: 2, MACHAMP: 2,
                     driver.VULPIX: 2, driver.DEFENDER: 2, driver.BILL: 2, driver.FIGHTING: 34, driver.FIRE: 4},
                    tuple(range(6)), tags=("サカキのカイリキー", "こんじょう", "はんげき", "ベトベトン", "かがくへんかガス", "ゴースト", "特殊状態")),
)
ROCKETS_MOLTRES = "PMCG5-020"
POWER_SCENARIOS += (
    # R団のファイヤー（v0.12。ふしちょう・ほのおのかべ）: 相手はカイリキー（はんげき）・ゴースト（とうめい・あくむ）・ベトベター・ベトベトン
    # （どくガス・かがくへんかガス）・キャタピー・トランセル・バタフリー（ふきとばし・メガドレイン。弱点 炎）・ビードル（どくばり）・ユンゲラー
    # （ちょうねんりき）・ピカチュウ（でんげき）・サカキのカイリキー（こんじょう）・ディフェンダー
    driver.Scenario("moltres", {ROCKETS_MOLTRES: 4, driver.PONYTA: 3, driver.GROWLITHE: 3, driver.VULPIX: 2, driver.SWITCH: 2, driver.POTION: 2,
                                driver.BILL: 4, driver.DEFENDER: 2, driver.PLUSPOWER: 2, driver.FIRE: 36},
                    {driver.MACHOP: 2, MACHOKE: 2, MACHAMP: 2, GASTLY: 2, HAUNTER: 2, GRIMER: 2, MUK: 1, driver.CATERPIE: 2, driver.METAPOD: 1,
                     driver.BUTTERFREE: 1, driver.WEEDLE: 2, ABRA: 2, KADABRA: 2, driver.PIKACHU: 2, GIOVANNIS_MACHOP: 1, GIOVANNIS_MACHOKE: 1,
                     GIOVANNIS_MACHAMP: 1, ROCKETS_MOLTRES: 2, driver.PLUSPOWER: 2, driver.BILL: 4, driver.DEFENDER: 2, driver.FIGHTING: 6,
                     PSYCHIC: 8, driver.GRASS: 6, driver.LIGHTNING: 2},
                    tuple(range(6)), tags=("R団のファイヤー", "ふしちょう", "ほのおのかべ", "はんげき", "とうめい", "かがくへんかガス", "特殊状態")),
    # 両方のデッキに R団のファイヤー（ミラー）、一方にベトベトン・ゴースト・ロコン（こんらん）、もう一方にカイリキー・バタフリー
    driver.Scenario("moltres_mixed", {ROCKETS_MOLTRES: 4, GRIMER: 3, MUK: 2, GASTLY: 2, HAUNTER: 2, driver.VULPIX: 2, driver.SWITCH: 2,
                                      driver.POTION: 2, driver.FIRE: 22, PSYCHIC: 8, driver.GRASS: 9, driver.BILL: 2},
                    {ROCKETS_MOLTRES: 4, driver.MACHOP: 3, MACHOKE: 2, MACHAMP: 2, driver.CATERPIE: 3, driver.METAPOD: 2, driver.BUTTERFREE: 2,
                     driver.DEFENDER: 2, driver.BILL: 2, driver.FIRE: 18, driver.FIGHTING: 12, driver.GRASS: 8},
                    tuple(range(6)), tags=("R団のファイヤー", "ふしちょう", "ほのおのかべ", "はんげき", "ふきとばし", "とうめい", "かがくへんかガス")),
)
ROCKET_SQUIRTLE, DARK_WARTORTLE = "PMCG4-018", "PMCG4-021"
POWER_SCENARIOS += (
    # わるいカメール（v0.13。こうらがえし・おうふくびんた。ポケモンパワーを持たないので POWER_USERS には加えない）: 相手はピカチュウ（わるいカメールの
    # 弱点 雷）・ポニータ・ガーディ（弱点 水）・カイリキー（はんげき）・ゴースト（とうめい・あくむ）・バタフリー（ふきとばし・メガドレイン）・
    # ビードル（どくばり）・ベトベトン（かがくへんかガス）・サカキのカイリキー（こんじょう・ハリケーンパンチ）・ディフェンダー・プラスパワー
    driver.Scenario("wartortle", {ROCKET_SQUIRTLE: 3, SQUIRTLE: 1, DARK_WARTORTLE: 4, driver.STARYU: 3, driver.SEEL: 2, driver.SWITCH: 2,
                                  driver.POTION: 2, driver.BILL: 4, driver.DEFENDER: 2, driver.PLUSPOWER: 2, driver.WATER: 35},
                    {driver.PIKACHU: 3, driver.PONYTA: 2, driver.GROWLITHE: 2, driver.MACHOP: 2, MACHOKE: 2, MACHAMP: 2, GASTLY: 2, HAUNTER: 2,
                     driver.CATERPIE: 2, driver.METAPOD: 1, driver.BUTTERFREE: 1, driver.WEEDLE: 2, GRIMER: 1, MUK: 1, GIOVANNIS_MACHOP: 1,
                     GIOVANNIS_MACHOKE: 1, GIOVANNIS_MACHAMP: 1, driver.DEFENDER: 2, driver.PLUSPOWER: 2, driver.BILL: 2, driver.LIGHTNING: 6,
                     driver.FIRE: 5, driver.FIGHTING: 7, PSYCHIC: 4, driver.GRASS: 4},
                    tuple(range(6)), tags=("わるいカメール", "こうらがえし", "おうふくびんた", "はんげき", "とうめい", "こんじょう", "ディフェンダー")),
    # 両方のデッキにわるいカメール（ミラー）、一方に R団のファイヤー（ほのおのかべ・ふしちょう）・ポニータ・ロコン、もう一方にピカチュウ・ドードー・バタフリー
    driver.Scenario("wartortle_mixed", {ROCKET_SQUIRTLE: 3, SQUIRTLE: 1, DARK_WARTORTLE: 4, ROCKETS_MOLTRES: 2, driver.PONYTA: 2, driver.VULPIX: 2,
                                        driver.SWITCH: 2, driver.DEFENDER: 2, driver.BILL: 2, driver.WATER: 24, driver.FIRE: 16},
                    {ROCKET_SQUIRTLE: 3, SQUIRTLE: 1, DARK_WARTORTLE: 4, driver.PIKACHU: 3, driver.DODUO: 2, driver.CATERPIE: 2, driver.METAPOD: 1,
                     driver.BUTTERFREE: 1, driver.PLUSPOWER: 2, driver.BILL: 2, driver.WATER: 22, driver.LIGHTNING: 10, driver.GRASS: 7},
                    tuple(range(6)), tags=("わるいカメール", "こうらがえし", "ほのおのかべ", "ふしちょう", "ふきとばし", "ミラー")),
)
ALL_SCENARIOS = (*driver.SCENARIOS, *POWER_SCENARIOS)
POWER_RATE = 0.35  # 自分の場にフシギバナ・カメックス・フーディン・ベトベトン・ゴースト・カイリキー・サカキのカイリキー・R団のファイヤーがいる番で、ポケモンパワーを試す割合
# 並びの最後にベトベトン（v0.8）・ゴースト（v0.9）・カイリキー（v0.10）・サカキのカイリキー（v0.11）・R団のファイヤー（v0.12）を加えた。ベトベトンの
# いない組の選び方（乱数の使い方）は v0.7 と同じ、ゴーストのいない組は v0.8 と同じ、カイリキーのいない組は v0.9 と同じ、サカキのカイリキーのいない組は
# v0.10 と同じ、R団のファイヤーのいない組は v0.11 と同じ
POWER_USERS = (VENUSAUR, BLASTOISE, ALAKAZAM, MUK, HAUNTER, MACHAMP, GIOVANNIS_MACHAMP, ROCKETS_MOLTRES)
HAUNTER_DECLARE_SKIP = 0.75  # ゴースト・カイリキーを選んだときに、宣言を試さずに駆動の操作にする割合（いない組の乱数の使い方は変えない）


def choose_command(state, rng: random.Random, illegal_rate: float):
    """駆動の操作に、ポケモンパワー（エナジートランス・あまごい・ダメージスワップ）の使用を混ぜる。自分の番（MAIN）に自分の場に
    フシギバナ・カメックス・フーディンがいなければ、駆動と同じ（v0.4e と同じ）。フシギバナだけがいれば v0.5 と同じ、フシギバナ・
    カメックスだけなら v0.6 と同じ（乱数の使い方も同じ）。"""
    player = state.current_player
    if state.phase is not engine.Phase.MAIN or player not in (0, 1):
        return driver.choose_command(engine, state, rng, illegal_rate)
    mine = state.players[player].in_play()
    kinds = [card_id for card_id in POWER_USERS if any(state.cards[pk.card].card_id == card_id for pk in mine)]
    if not kinds or rng.random() >= POWER_RATE:
        return driver.choose_command(engine, state, rng, illegal_rate)
    kind = kinds[0] if len(kinds) == 1 else rng.choice(kinds)
    if kind in (HAUNTER, MACHAMP, GIOVANNIS_MACHAMP, ROCKETS_MOLTRES) and rng.random() < HAUNTER_DECLARE_SKIP:
        return driver.choose_command(engine, state, rng, illegal_rate)  # 宣言の試しを減らして、ワザの手を増やす（v0.9〜v0.12）
    if kind in (MUK, HAUNTER, MACHAMP, GIOVANNIS_MACHAMP, ROCKETS_MOLTRES):
        # かがくへんかガスは常にはたらいていて（v0.8）、「とうめい」（v0.9）・「はんげき」（v0.10）は自動的にはたらいて宣言しない
        # （POWER_NOT_DECLARABLE になるはず）。「こんじょう」（v0.11）は決められたとき（相手のワザのダメージできぜつするとき。決定で答える）
        # にしか使えない（POWER_NOT_USABLE_NOW になるはず）。「ふしちょう」（v0.12）は、このカードが「きぜつ」したとき（決定で答える）にしか
        # 使えない（POWER_NOT_USABLE_NOW になるはず）
        user = rng.choice([pk for pk in mine if state.cards[pk.card].card_id == kind])
        return engine.UsePokemonPower(player, user.pokemon_id, 0)
    if kind == ALAKAZAM:
        return _damage_swap_command(state, rng)
    return _power_command(state, rng) if kind == VENUSAUR else _rain_dance_command(state, rng)


def _damage_swap_command(state, rng: random.Random):
    """ダメージスワップの使用（v0.7）: たいていはルール上できそうなもの（自分のフーディン・ダメージカウンターがのった自分のポケモン・
    1 個のせてもきぜつしない自分の別のポケモン）、ときどき不正なもの（同じポケモン・カウンターのないポケモン・きぜつする移動先・
    相手のポケモン・エネルギーの指定・選ばせるものの不足・番でない・ない番号・ない位置・パワーのないポケモン）。"""
    player = state.current_player
    mine, theirs = state.players[player].in_play(), state.players[1 - player].in_play()
    user = rng.choice([pk for pk in mine if state.cards[pk.card].card_id == ALAKAZAM])
    damaged = [pk for pk in mine if pk.damage]
    source = rng.choice(damaged or mine)
    room = [pk for pk in mine if pk is not source and pk.damage + 10 < state.card_def(pk.card).hp]
    target = rng.choice(room or [pk for pk in mine if pk is not source] or mine)
    command = engine.UsePokemonPower(player, user.pokemon_id, 0, None, source.pokemon_id, target.pokemon_id)
    if rng.random() < 0.7:
        return command
    full = [pk for pk in mine if pk.damage + 10 >= state.card_def(pk.card).hp]
    clean = [pk for pk in mine if not pk.damage]
    odd = [
        engine.UsePokemonPower(player, user.pokemon_id),  # 選ばせるものがない
        engine.UsePokemonPower(player, user.pokemon_id, 0, None, source.pokemon_id),  # 移動先がない
        engine.UsePokemonPower(player, user.pokemon_id, 0, rng.choice(sorted(state.cards)), source.pokemon_id, target.pokemon_id),  # エネルギー
        engine.UsePokemonPower(player, user.pokemon_id, 0, None, source.pokemon_id, source.pokemon_id),  # 同じポケモン
        engine.UsePokemonPower(player, user.pokemon_id, 1, None, source.pokemon_id, target.pokemon_id),  # ない位置
        engine.UsePokemonPower(1 - player, user.pokemon_id, 0, None, source.pokemon_id, target.pokemon_id),  # 番でない
        engine.UsePokemonPower(player, user.pokemon_id, 0, None, 999, target.pokemon_id),
        engine.UsePokemonPower(player, user.pokemon_id, 0, None, source.pokemon_id, 999),
        engine.UsePokemonPower(player, rng.choice(mine).pokemon_id, 0, None, source.pokemon_id, target.pokemon_id),  # パワーのないポケモンかも
    ]
    if full:
        odd.append(engine.UsePokemonPower(player, user.pokemon_id, 0, None, source.pokemon_id, rng.choice(full).pokemon_id))  # きぜつするかも
    if clean:
        odd.append(engine.UsePokemonPower(player, user.pokemon_id, 0, None, rng.choice(clean).pokemon_id, target.pokemon_id))  # カウンターなし
    if theirs:
        other = rng.choice(theirs)
        odd += [
            engine.UsePokemonPower(player, user.pokemon_id, 0, None, source.pokemon_id, other.pokemon_id),  # 相手のポケモンへ
            engine.UsePokemonPower(player, user.pokemon_id, 0, None, other.pokemon_id, target.pokemon_id),  # 相手のポケモンから
            engine.UsePokemonPower(player, other.pokemon_id, 0, None, source.pokemon_id, target.pokemon_id),  # 相手のポケモンのパワー
        ]
    return rng.choice(odd)


def _rain_dance_command(state, rng: random.Random):
    """あまごいの使用（v0.6）: たいていはルール上できそうなもの（自分のカメックス・手札の「水」エネルギー・自分の「水」ポケモン）、
    ときどき不正なもの（手札にないカード・相手の手札・場についたカード・水でないエネルギー・水でないポケモン・相手のポケモン・
    移動元の指定・選ばせるものの不足・番でない・ない番号・ない位置）。"""
    player = state.current_player
    p, q = state.players[player], state.players[1 - player]
    mine, theirs = p.in_play(), q.in_play()
    user = rng.choice([pk for pk in mine if state.cards[pk.card].card_id == BLASTOISE])
    waters = [u for u in p.hand if state.card_def(u).is_basic_energy and state.card_def(u).provides is engine.EnergyType.WATER]
    water_pokemon = [pk for pk in mine if state.card_def(pk.card).pokemon_type is engine.EnergyType.WATER]
    energy = rng.choice(waters) if waters else rng.choice(sorted(state.cards))
    target = rng.choice(water_pokemon or mine)
    command = engine.UsePokemonPower(player, user.pokemon_id, 0, energy, None, target.pokemon_id)
    if rng.random() < 0.7:
        return command
    attached = [u for pk in mine for u in pk.energy]
    others = [u for u in p.hand if u not in waters]
    odd = [
        engine.UsePokemonPower(player, user.pokemon_id),  # 選ばせるものがない
        engine.UsePokemonPower(player, user.pokemon_id, 0, energy, user.pokemon_id, target.pokemon_id),  # 移動元を指定した
        engine.UsePokemonPower(player, user.pokemon_id, 1, energy, None, target.pokemon_id),  # ない位置
        engine.UsePokemonPower(1 - player, user.pokemon_id, 0, energy, None, target.pokemon_id),  # 番でない
        engine.UsePokemonPower(player, user.pokemon_id, 0, rng.choice(sorted(state.cards)), None, target.pokemon_id),  # 手札にないかも
        engine.UsePokemonPower(player, user.pokemon_id, 0, energy, None, rng.choice(mine).pokemon_id),  # 水でないポケモンかも
        engine.UsePokemonPower(player, user.pokemon_id, 0, energy, None, 999),
        engine.UsePokemonPower(player, rng.choice(mine).pokemon_id, 0, energy, None, target.pokemon_id),  # パワーのないポケモンかも
    ]
    if attached:
        odd.append(engine.UsePokemonPower(player, user.pokemon_id, 0, rng.choice(attached), None, target.pokemon_id))  # 場のカード
    if others:
        odd.append(engine.UsePokemonPower(player, user.pokemon_id, 0, rng.choice(others), None, target.pokemon_id))  # 水でないカード
    if q.hand:
        odd.append(engine.UsePokemonPower(player, user.pokemon_id, 0, rng.choice(q.hand), None, target.pokemon_id))  # 相手の手札
    if theirs:
        other = rng.choice(theirs)
        odd += [
            engine.UsePokemonPower(player, user.pokemon_id, 0, energy, None, other.pokemon_id),  # 相手のポケモンへ
            engine.UsePokemonPower(player, other.pokemon_id, 0, energy, None, target.pokemon_id),  # 相手のポケモンのパワー
        ]
    return rng.choice(odd)


def _power_command(state, rng: random.Random):
    """エナジートランスの使用: たいていはルール上できそうなもの（自分のフシギバナ・自分の場のエネルギー・別の自分のポケモン）、
    ときどき不正なもの（相手のポケモン・同じポケモン・選ばせるものの不足・ない位置・パワーのないポケモン・ない番号）。"""
    player = state.current_player
    mine = state.players[player].in_play()
    theirs = state.players[1 - player].in_play()
    users = [pk for pk in mine if state.cards[pk.card].card_id == VENUSAUR]
    user = rng.choice(users)
    sources = [pk for pk in mine if pk.energy] or mine
    source = rng.choice(sources)
    energy = rng.choice(source.energy) if source.energy else rng.choice(sorted(state.cards))
    others = [pk for pk in mine if pk is not source] or mine
    target = rng.choice(others)
    command = engine.UsePokemonPower(player, user.pokemon_id, 0, energy, source.pokemon_id, target.pokemon_id)
    roll = rng.random()
    if roll < 0.7:
        return command
    odd = [
        engine.UsePokemonPower(player, user.pokemon_id),  # 選ばせるものがない
        engine.UsePokemonPower(player, user.pokemon_id, 1, energy, source.pokemon_id, target.pokemon_id),  # ない位置
        engine.UsePokemonPower(player, user.pokemon_id, 0, energy, source.pokemon_id, source.pokemon_id),  # 同じポケモン
        engine.UsePokemonPower(player, rng.choice(mine).pokemon_id, 0, energy, source.pokemon_id, target.pokemon_id),  # パワーのないポケモンかも
        engine.UsePokemonPower(1 - player, user.pokemon_id, 0, energy, source.pokemon_id, target.pokemon_id),  # 番でない
        engine.UsePokemonPower(player, user.pokemon_id, 0, rng.choice(sorted(state.cards)), source.pokemon_id, target.pokemon_id),
        engine.UsePokemonPower(player, 999, 0, energy, source.pokemon_id, target.pokemon_id),
    ]
    if theirs:
        other = rng.choice(theirs)
        odd += [
            engine.UsePokemonPower(player, user.pokemon_id, 0, energy, source.pokemon_id, other.pokemon_id),  # 相手のポケモンへ
            engine.UsePokemonPower(player, user.pokemon_id, 0, (other.energy or [energy])[0], other.pokemon_id, target.pokemon_id),
            engine.UsePokemonPower(player, other.pokemon_id, 0, energy, source.pokemon_id, target.pokemon_id),  # 相手のポケモンのパワー
        ]
    return rng.choice(odd)


def classify(error: Exception) -> str:
    if isinstance(error, engine.StateIntegrityError):
        return "internal_state_integrity"
    if isinstance(error, engine.UnsupportedError):
        if error.code.startswith("UNRESOLVED_"):
            return "rejected_unresolved"
        return "rejected_unsupported"
    if isinstance(error, engine.IllegalActionError):
        return "rejected_illegal"
    return "internal_error"


def _suppression_of(state, command):
    """コマンドの特殊能力を、今消している場のポケモンの番号（v0.8。エンジンとは別に、場から求める。使う特殊能力が分からなければ None）。"""
    found = state.find_pokemon(command.pokemon) if isinstance(command.pokemon, int) else None
    if found is None or found[0] != command.player or not isinstance(command.power, int):
        return None
    definition = state.card_def(found[1].card)
    if not 0 <= command.power < len(definition.powers):
        return None
    return engine.power_suppressors(state, command.pokemon, command.power)


def _evasion_before(state) -> dict[int, object]:
    """場のポケモンの番号 → 今はたらいている「とうめい」（v0.9。エンジンの公開の問い合わせ ``working_evasion_power``）。"""
    return {pk.pokemon_id: engine.working_evasion_power(state, pk.pokemon_id) for p in state.players for pk in p.in_play()}


def _observe_attack(state, new, evasion, counted, problems, index, command) -> None:
    """受け付けたワザ（とその決定の答え）のログを、ワザの前の場の「とうめい」と比べる（v0.9）。"""
    events = [dict(e) for e in new.log[len(state.log):]]
    checked = set()
    for position, e in enumerate(events):
        if e["kind"] == "evade_check":
            counted["observed:evade_check"] += 1
            counted[f"observed:evade_{e['result']}"] += 1
            checked.add(e["pokemon_id"])
            owner = state.find_pokemon(e["pokemon_id"])
            coin = events[position - 1] if position else {}
            if evasion.get(e["pokemon_id"]) is None or owner is None or owner[0] != e["player"] or coin.get("player") != e["player"]:
                problems.append(f"{index} 手目 {engine.command_to_dict(command)}: はたらいていない「とうめい」・ゴースト側でないプレイヤーの判定 {e}")
        elif e["kind"] == "attack_evaded":
            counted[f"observed:evaded_{e['element']}"] += 1
        elif e["kind"] == "recover_energy":
            counted["observed:recover_energy"] += 1
            counted[f"observed:recover_energy_{len(e['cards'])}"] += 1
        elif e["kind"] == "damage" and e["amount"] > 0 and e.get("target") != "self":
            pid = next((pk.pokemon_id for p in state.players for pk in p.in_play() if pk.card == e["pokemon"]), None)
            if evasion.get(pid) is not None and pid not in checked:
                problems.append(f"{index} 手目 {engine.command_to_dict(command)}: はたらいている「とうめい」のポケモン {pid} が判定なしでダメージを受けた")
    if isinstance(command, engine.UseAttack):
        target = state.players[1 - state.current_player].active
        if target is not None and state.cards[target.card].card_id == HAUNTER:
            c = target.conditions
            if c.asleep or c.paralyzed or c.confused:
                counted["observed:haunter_attacked_while_blocked"] += 1
            elif evasion.get(target.pokemon_id) is None:
                counted["observed:haunter_attacked_under_gas"] += 1
            else:
                counted["observed:haunter_attacked_working"] += 1


def _counter_before(state) -> dict[int, object]:
    """場のポケモンの番号 → 今はたらいている「はんげき」（v0.10。エンジンの公開の問い合わせ ``working_counterattack_power``）。"""
    return {pk.pokemon_id: engine.working_counterattack_power(state, pk.pokemon_id) for p in state.players for pk in p.in_play()}


def _observe_counterattack(state, new, before, counted, problems, index, command) -> None:
    """受け付けたワザ（とその決定の答え）のログを、ワザの前の場の「はんげき」と比べる（v0.10）。エンジンとは別に、ダメージのログから
    「はんげき」がはたらくはずのポケモンを求める。"""
    events = [dict(e) for e in new.log[len(state.log):]]
    attack = next((e for e in reversed(state.log + new.log[len(state.log):]) if e["kind"] == "attack"), None)
    attacker_player = state.current_player
    expected = []
    owners = {pk.pokemon_id: player for player, p in enumerate(state.players) for pk in p.in_play()}
    cards = {pk.card: pk.pokemon_id for p in state.players for pk in p.in_play()}
    for e in events:
        if e["kind"] == "damage" and e["amount"] > 0:
            pid = e.get("pokemon_id", cards.get(e["pokemon"]))
            if before.get(pid) is not None and owners.get(pid) != attacker_player:
                expected.append(pid)
                hp = state.card_def(e["pokemon"]).hp
                counted["observed:counter_trigger"] += 1
                if e["total_damage"] >= hp:
                    counted["observed:counter_trigger_knocked_out_machamp"] += 1
                if state.players[owners[pid]].active is None or state.players[owners[pid]].active.pokemon_id != pid:
                    counted["observed:counter_trigger_bench"] += 1
        elif e["kind"] in ("counterattack", "counterattack_skipped"):
            counted[f"observed:{e['kind']}"] += 1
            if not expected or expected[0] != e["pokemon_id"]:
                problems.append(f"{index} 手目 {engine.command_to_dict(command)}: はたらくはずのない「はんげき」 {e}")
                continue
            expected.pop(0)
            if attack is None or e["attacker_pokemon_id"] != state.players[attacker_player].active.pokemon_id:
                problems.append(f"{index} 手目 {engine.command_to_dict(command)}: 「はんげき」の相手がワザを使ったポケモンではない {e}")
            if e["kind"] == "counterattack":
                counted["observed:counter_damage_total"] += e["amount"]
                if e["amount"] != 10:
                    problems.append(f"{index} 手目 {engine.command_to_dict(command)}: 「はんげき」の量が 10 ではない {e}")
                if e["knocked_out"]:
                    counted["observed:counter_knock_out"] += 1
        elif e["kind"] == "knock_out" and e.get("simultaneous"):
            counted["observed:simultaneous_knock_out"] += 1
    if expected:
        problems.append(f"{index} 手目 {engine.command_to_dict(command)}: はたらいた「はんげき」（ポケモン {expected}）のログがない")
    if isinstance(command, engine.UseAttack):
        target = state.players[1 - state.current_player].active
        if target is not None and state.cards[target.card].card_id == MACHAMP:
            c = target.conditions
            if c.asleep or c.paralyzed or c.confused:
                counted["observed:machamp_attacked_while_blocked"] += 1
            elif before.get(target.pokemon_id) is None:
                counted["observed:machamp_attacked_under_gas"] += 1
            else:
                counted["observed:machamp_attacked_working"] += 1


def _guts_before(state) -> dict[int, object]:
    """場のポケモンの番号 → 今の状態で相手のワザのダメージできぜつするなら使える「こんじょう」（v0.11。エンジンの公開の問い合わせ
    ``available_ko_prevention_power``）。"""
    return {pk.pokemon_id: engine.available_ko_prevention_power(state, pk.pokemon_id) for p in state.players for pk in p.in_play()}


def _observe_guts(state, new, before, counted, problems, index, command) -> None:
    """受け付けたワザ・決定の答え・番の終わりのログと決定を、操作の前の場の「こんじょう」と比べる（v0.11）。"""
    events = [dict(e) for e in new.log[len(state.log):]]
    where = f"{index} 手目 {engine.command_to_dict(command)}"
    owners = {pk.pokemon_id: player for player, p in enumerate(state.players) for pk in p.in_play()}
    by_card = {pk.card: pk for p in state.players for pk in p.in_play()}
    d = new.decision
    if d is not None and d.kind == "ko_prevention":
        pid = d.options[0]
        pokemon = new.find_pokemon(pid)
        counted["observed:guts_offered"] += 1
        # v0.12: 番のプレイヤーのポケモンは、相手の「ほのおのかべ」のダメージ（相手のワザによるダメージ）を受けたときだけ
        by_retaliation = any(e["kind"] == "damage" and e.get("retaliation") and e.get("pokemon_id") == pid for e in events)
        if (before.get(pid) is None or (owners.get(pid) == state.current_player and not by_retaliation) or pokemon is None
                or pokemon[1].damage < new.card_def(pokemon[1].card).hp):
            problems.append(f"{where}: 使えないはずの「こんじょう」の決定 {d}")
        elif state.players[owners[pid]].active is None or state.players[owners[pid]].active.pokemon_id != pid:
            counted["observed:guts_offered_on_bench"] += 1
    answered = {e["pokemon_id"] for e in events if e["kind"] in ("ko_prevention_declined", "ko_prevention_failed")}
    for e in events:
        kind = e["kind"]
        if kind in ("ko_prevention_declined", "ko_prevention_declared", "ko_prevented", "ko_prevention_failed"):
            counted[f"observed:{kind}"] += 1
        if kind == "ko_prevented":
            pokemon = new.find_pokemon(e["pokemon_id"])
            if pokemon is None or pokemon[1].damage != new.card_def(pokemon[1].card).hp - 10:
                problems.append(f"{where}: 「おもて」のあとに残り HP 10 で場にいない {e}")
        if kind == "knock_out":
            pokemon = by_card.get(e["pokemon"])
            if pokemon is None or state.cards[pokemon.card].card_id != GIOVANNIS_MACHAMP:
                continue
            counted["observed:giovannis_machamp_knocked_out"] += 1
            if pokemon.pokemon_id in answered:
                continue
            c = pokemon.conditions
            if e.get("timing") == "pokemon_check":
                counted["observed:guts_not_applicable_poison"] += 1
            elif owners[pokemon.pokemon_id] == state.current_player and not any(
                g["kind"] == "damage" and g.get("retaliation") and g.get("pokemon_id") == pokemon.pokemon_id for g in events
            ):
                counted["observed:guts_not_applicable_own_turn"] += 1  # 自分のワザ・こんらん・「はんげき」
            elif c.asleep or c.paralyzed or c.confused:
                counted["observed:guts_blocked_by_condition"] += 1
            elif before.get(pokemon.pokemon_id) is None:
                counted["observed:guts_suppressed_by_gas"] += 1
            else:
                problems.append(f"{where}: 「こんじょう」を使えるのに決定がないまま、きぜつした {e}")


def _rebirth_field(state) -> dict[int, tuple[str, str | None]]:
    """場のポケモンの番号 → (カード id, ねむり・マヒ・こんらん)（v0.12。「ふしちょう」を使えるかを、エンジンの関数を使わずに求めるため）。"""
    return {pk.pokemon_id: (state.cards[pk.card].card_id, None if pk.conditions.exclusive is None else pk.conditions.exclusive.name)
            for p in state.players for pk in p.in_play()}


FIRE_WALL = f"{ROCKETS_MOLTRES}#0"
SHELL = f"{DARK_WARTORTLE}#1"
SHELL_KIND = "retaliation_received_damage"


def _observe_shell(state, new, counted, problems, index, command) -> None:
    """受け付けた操作のログを、操作の前の場から求めた「こうらがえし」と比べる（v0.13）: 今の番にはたらく「こうらがえし」を持つポケモンが相手の
    ワザのダメージ（0 より大きい）を受けたら、その直後の処理に「こうらがえし」（retaliation か retaliation_skipped）があり、受けたダメージ
    （received_damage）と基本となるダメージ（amount）がそのダメージの最終ダメージと同じで、返すダメージの基本となる計算がその値で、受けたのは
    ワザを使ったポケモン（番のプレイヤーのバトル場）であること。効果・はたらいた・返したダメージ・弱点・ディフェンダー・きぜつ・期限で消えたを数える。"""
    events = [dict(e) for e in new.log[len(state.log):]]
    where = f"{index} 手目 {engine.command_to_dict(command)}"
    by_card = {pk.card: pk for p in state.players for pk in p.in_play()}
    pending = []  # (場のポケモンの番号, 受けたダメージ)
    expected_base = None
    for e in events:
        kind = e["kind"]
        if kind == "persistent_effect_added" and e["persistent_effect"] == SHELL_KIND:
            counted["observed:shell_effect_added"] += 1
        if kind == "persistent_effect_removed" and e["persistent_effect"] == SHELL_KIND:
            counted[f"observed:shell_effect_removed_{e['reason']}"] += 1
        if kind == "damage" and e["amount"] > 0 and not e.get("retaliation"):
            pid = e.get("pokemon_id", by_card[e["pokemon"]].pokemon_id if e["pokemon"] in by_card else None)
            holder = state.find_pokemon(pid) if pid is not None else None
            if holder is not None and holder[0] != state.current_player and any(
                x.kind == SHELL_KIND and x.active_turn == state.turn_number for x in holder[1].persistent_effects
            ):
                pending.append((pid, e["amount"]))
        if kind in ("retaliation", "retaliation_skipped") and e["effect"] == SHELL:
            counted[f"observed:shell_{kind}"] += 1
            if not pending or pending[0][0] != e["pokemon_id"]:
                problems.append(f"{where}: はたらくはずのない「こうらがえし」 {e}")
                continue
            _, received = pending.pop(0)
            if kind == "retaliation":
                if (e.get("basis"), e.get("received_damage"), e["amount"]) != ("received_damage", received, received):
                    problems.append(f"{where}: 「こうらがえし」の受けたダメージ・基本となるダメージが {received} ではない {e}")
                counted["observed:shell_received_total"] += received
                expected_base = received
        if kind == "damage" and e.get("retaliation") and e["effect"] == SHELL:
            counted["observed:shell_damage"] += 1
            counted["observed:shell_damage_total"] += e["amount"]
            counted["observed:shell_weakness"] += bool(e["weakness"])
            counted["observed:shell_resistance"] += bool(e["resistance"])
            counted["observed:shell_modifiers"] += bool(e.get("modifiers"))
            if e["steps"][0][1] != expected_base or e["pokemon_id"] != state.players[state.current_player].active.pokemon_id:
                problems.append(f"{where}: 「こうらがえし」の返すダメージの基本となるダメージ・相手が違う {e}")
            if e["total_damage"] >= new.card_def(e["pokemon"]).hp:
                counted["observed:shell_knock_out"] += 1
        if kind == "attack_evaded" and e.get("effect") == SHELL:
            counted["observed:shell_evaded"] += 1
    if pending:
        problems.append(f"{where}: はたらいた「こうらがえし」（ポケモン {[p for p, _ in pending]}）のログがない")


def _observe_moltres(state, new, counted, problems, index, command) -> None:
    """受け付けた操作のログと決定を、操作の前の場から求めた「ふしちょう」「ほのおのかべ」と比べる（v0.12）。きぜつするときの特殊状態・
    かがくへんかガスは、操作の前の場をこの操作のログ（special_condition・special_conditions_removed・knock_out）で進めて求める。"""
    events = [dict(e) for e in new.log[len(state.log):]]
    where = f"{index} 手目 {engine.command_to_dict(command)}"
    by_card = {pk.card: pk for p in state.players for pk in p.in_play()}
    field = _rebirth_field(state)
    d = new.decision
    if d is not None and d.kind == "post_knockout_power":
        counted["observed:rebirth_offered"] += 1
    if state.decision is not None and state.decision.kind == "take_prize" and state.decision.context_value("post_knockout") is not None \
            and new.phase in engine.TERMINAL_PHASES:
        counted["observed:rebirth_not_offered_game_over"] += 1
    batches, batch = [], set()
    for e in events:
        if e["kind"] == "knock_out" and e["pokemon"] in by_card:
            batch.add(by_card[e["pokemon"]].pokemon_id)
        elif e["kind"] != "persistent_effect_removed" and batch:
            batches.append(batch)
            batch = set()
    if batch:
        batches.append(batch)
    pending_retaliation = []
    for position, e in enumerate(events):
        kind = e["kind"]
        if kind in ("retaliation", "retaliation_skipped") and e["effect"] != FIRE_WALL:
            continue  # v0.13: 「こうらがえし」は _observe_shell で確かめる
        if kind in ("post_knockout_power_declined", "post_knockout_power_declared", "return_to_hand", "retaliation", "retaliation_skipped",
                    "persistent_effect_skipped"):
            counted[f"observed:{kind}"] += 1
        if kind == "return_to_hand":
            card = e["card"]
            if state.cards[card].card_id != ROCKETS_MOLTRES or (new.phase not in engine.TERMINAL_PHASES and card not in new.players[e["player"]].hand):
                problems.append(f"{where}: 回収したカードが R団のファイヤーでない・手札にない {e}")
        if kind == "special_condition" and e["condition"] in ("sleep", "paralysis", "confusion") and e["pokemon_id"] in field:
            field[e["pokemon_id"]] = (field[e["pokemon_id"]][0], e["condition"])
        if kind == "special_conditions_removed" and e["pokemon_id"] in field and field[e["pokemon_id"]][1] in e["conditions"]:
            field[e["pokemon_id"]] = (field[e["pokemon_id"]][0], None)
        if kind == "persistent_effect_added" and e["persistent_effect"] == "retaliation":
            counted["observed:retaliation_effect_added"] += 1
        if kind == "persistent_effect_removed" and e["persistent_effect"] == "retaliation":
            counted[f"observed:retaliation_effect_removed_{e['reason']}"] += 1
        if kind == "damage" and e["amount"] > 0 and not e.get("retaliation"):
            pid = e.get("pokemon_id", by_card[e["pokemon"]].pokemon_id if e["pokemon"] in by_card else None)
            holder = state.find_pokemon(pid) if pid is not None else None
            if holder is not None and holder[0] != state.current_player and any(
                x.kind == "retaliation" and x.active_turn == state.turn_number for x in holder[1].persistent_effects
            ):
                pending_retaliation.append(pid)
        if kind in ("retaliation", "retaliation_skipped"):
            if not pending_retaliation or pending_retaliation[0] != e["pokemon_id"]:
                problems.append(f"{where}: はたらくはずのない「ほのおのかべ」 {e}")
            else:
                pending_retaliation.pop(0)
        if kind == "damage" and e.get("retaliation") and e["effect"] == FIRE_WALL:
            counted["observed:retaliation_damage"] += 1
            counted["observed:retaliation_damage_total"] += e["amount"]
            if e["steps"][0][1] != 10 or e["pokemon_id"] != state.players[state.current_player].active.pokemon_id:
                problems.append(f"{where}: 「ほのおのかべ」のダメージ・相手が違う {e}")
            if e["total_damage"] >= new.card_def(e["pokemon"]).hp:
                counted["observed:retaliation_knock_out"] += 1
        if kind == "knock_out" and e["pokemon"] in by_card:
            pokemon = by_card[e["pokemon"]]
            knocked = next(b for b in batches if pokemon.pokemon_id in b)
            card_id, condition = field.pop(pokemon.pokemon_id)
            if card_id != ROCKETS_MOLTRES:
                continue
            counted["observed:rockets_moltres_knocked_out"] += 1
            snapshot = {**_rebirth_field(state), **field}
            gases = [pid for pid, (kind_id, exclusive) in snapshot.items() if kind_id == MUK and exclusive is None]
            answered = any(r["kind"] in ("post_knockout_power_declined", "post_knockout_power_declared") and r["card"] == e["pokemon"]
                           for r in events)
            waiting = d is not None and (d.options == (e["pokemon"],) and d.kind == "post_knockout_power" or any(
                c[1] == e["pokemon"] for c in d.context_value("post_knockout", ())))
            if condition is not None:
                counted["observed:rebirth_blocked_condition"] += 1
                if answered or waiting:
                    problems.append(f"{where}: ねむり・マヒ・こんらんのまま「きぜつ」したのに「ふしちょう」の決定 {e}")
            elif gases and any(pid not in knocked for pid in gases):
                counted["observed:rebirth_blocked_gas"] += 1
                if answered or waiting:
                    problems.append(f"{where}: かがくへんかガスがはたらいているのに「ふしちょう」の決定 {e}")
            elif not (answered or waiting) and new.phase not in engine.TERMINAL_PHASES:
                problems.append(f"{where}: 「ふしちょう」を使えるのに決定がないまま {e}")
    if pending_retaliation:
        problems.append(f"{where}: はたらいた「ほのおのかべ」（ポケモン {pending_retaliation}）のログがない")


def run_game(scenario, seed: int, *, steps: int, illegal_rate: float, serialize_every: int) -> tuple[Counter, list[str]]:
    """1 局を進め、数えた結果と問題を返す。"""
    counted, problems = Counter(), []
    rng = random.Random(f"kyuura-stress:{scenario.name}:{seed}")
    state = engine.new_game(driver._deck(scenario.deck0), driver._deck(scenario.deck1), seed)
    gas_before = ()
    for index in range(steps):
        if state.phase in engine.TERMINAL_PHASES:
            break
        gas = engine.working_power_suppressors(state)
        if state.phase is engine.Phase.MAIN:
            muk_in_play = any(state.cards[pk.card].card_id == MUK for p in state.players for pk in p.in_play())
            if gas:
                counted["observed:gas_working"] += 1
            elif muk_in_play:
                counted["observed:gas_off_with_muk"] += 1
            if bool(gas) != bool(gas_before):
                counted["observed:gas_toggled"] += 1  # かがくへんかガスがはたらく／消えるが切り替わった（前に見た MAIN の手から）
            gas_before = gas
        command = choose_command(state, rng, illegal_rate)
        suppression = _suppression_of(state, command) if isinstance(command, engine.UsePokemonPower) else None
        evasion = _evasion_before(state) if isinstance(command, (engine.UseAttack, engine.ResolveDecision)) else None
        counter = _counter_before(state) if isinstance(command, (engine.UseAttack, engine.ResolveDecision)) else None
        guts = _guts_before(state) if isinstance(command, (engine.UseAttack, engine.ResolveDecision, engine.EndTurn)) else None
        before = engine.state_to_dict(state, format_version=9)
        fingerprint, log = rng_fingerprint(state.rng), state.log
        try:
            new = engine.apply_command(state, command)
        except engine.EngineError as error:
            category = classify(error)
            counted[category] += 1
            counted[f"code:{error.code}"] += 1
            if category.startswith("internal"):
                problems.append(f"{index} 手目 {engine.command_to_dict(command)}: {error}")
                break
            if engine.state_to_dict(state, format_version=9) != before or rng_fingerprint(state.rng) != fingerprint or state.log is not log:
                problems.append(f"{index} 手目 {engine.command_to_dict(command)}: 拒否（{error.code}）で渡した状態が変わった")
            if error.code == "POWER_SUPPRESSED" and not suppression:
                problems.append(f"{index} 手目 {engine.command_to_dict(command)}: かがくへんかガスがはたらいていないのに POWER_SUPPRESSED")
            if error.code == "UNRESOLVED_COUNTERATTACK_DOUBLE_KNOCKOUT":
                target = state.players[1 - state.current_player].active
                if target is None or engine.working_counterattack_power(state, target.pokemon_id) is None:
                    problems.append(f"{index} 手目 {engine.command_to_dict(command)}: 「はんげき」がはたらいていないのに UNRESOLVED_COUNTERATTACK_DOUBLE_KNOCKOUT")
            if error.code == "UNRESOLVED_KO_PREVENTION_ATTACK_EFFECT":
                target = state.players[1 - state.current_player].active
                if target is None or engine.available_ko_prevention_power(state, target.pokemon_id) is None:
                    problems.append(f"{index} 手目 {engine.command_to_dict(command)}: 「こんじょう」を使えないのに UNRESOLVED_KO_PREVENTION_ATTACK_EFFECT")
            if error.code == "POWER_NOT_USABLE_NOW":
                found = state.find_pokemon(command.pokemon) if isinstance(command, engine.UsePokemonPower) else None
                if found is None or state.cards[found[1].card].card_id not in (GIOVANNIS_MACHAMP, ROCKETS_MOLTRES):
                    problems.append(f"{index} 手目 {engine.command_to_dict(command)}: サカキのカイリキー・R団のファイヤーでないのに POWER_NOT_USABLE_NOW")
            if error.code == "UNRESOLVED_RETALIATION_DOUBLE_KNOCKOUT":
                target = state.players[1 - state.current_player].active
                active = [x for x in (target.persistent_effects if target is not None else ())
                          if x.kind in ("retaliation", SHELL_KIND) and x.active_turn == state.turn_number]
                if not active:
                    problems.append(f"{index} 手目 {engine.command_to_dict(command)}: 「ほのおのかべ」「こうらがえし」がはたらいていないのに UNRESOLVED_RETALIATION_DOUBLE_KNOCKOUT")
                elif active[0].kind == SHELL_KIND:
                    counted["observed:shell_stopped_w24"] += 1  # v0.13: S37（W24 と同じ問い）
            if error.code == "UNRESOLVED_EVADED_EFFECT_COIN":
                target = state.players[1 - state.current_player].active
                if target is None or engine.working_evasion_power(state, target.pokemon_id) is None:
                    problems.append(f"{index} 手目 {engine.command_to_dict(command)}: 「とうめい」がはたらいていないのに UNRESOLVED_EVADED_EFFECT_COIN")
            continue
        except Exception as error:  # noqa: BLE001  内部の誤り
            counted["internal_error"] += 1
            problems.append(f"{index} 手目 {engine.command_to_dict(command)}: {type(error).__name__}: {error}")
            break
        counted["accepted"] += 1
        counted[f"accepted:{type(command).__name__}"] += 1
        if isinstance(command, engine.UsePokemonPower):
            if suppression:
                problems.append(f"{index} 手目 {engine.command_to_dict(command)}: かがくへんかガス（{suppression}）がはたらいているのに特殊能力を受け付けた")
            if any(state.cards[pk.card].card_id == MUK for p in state.players for pk in p.in_play()):
                counted["accepted:power_with_muk_in_play"] += 1  # ベトベトンが場にいるが、力が消えている（ねむり・マヒ・こんらん）
        if isinstance(command, engine.UsePokemonPower) and new.log[-1]["kind"] == "power_attach_energy":
            counted["accepted:rain_dance"] += 1
        if isinstance(command, engine.UsePokemonPower) and new.log[-1]["kind"] == "move_damage_counter":
            counted["accepted:damage_swap"] += 1
        if any(e["kind"] == "discard_energy" for e in new.log[len(state.log):]):
            counted["accepted:recover"] += 1  # ユンゲラーの「じこさいせい」（決定に答えて処理した）
        if evasion is not None:
            _observe_attack(state, new, evasion, counted, problems, index, command)
        if counter is not None:
            _observe_counterattack(state, new, counter, counted, problems, index, command)
        if guts is not None:
            _observe_guts(state, new, guts, counted, problems, index, command)
        if any(state.cards[uid].card_id == ROCKETS_MOLTRES for uid in state.cards):
            _observe_moltres(state, new, counted, problems, index, command)  # v0.12
        if any(state.cards[uid].card_id == DARK_WARTORTLE for uid in state.cards):
            _observe_shell(state, new, counted, problems, index, command)  # v0.13
        if new.phase is engine.Phase.HALTED and state.phase is not engine.Phase.HALTED:
            counted[f"halted:{new.halt.code}"] += 1
        if serialize_every and index % serialize_every == 0:
            counted["serialization_audits"] += 1
            problems.extend(f"{index} 手目のあと: {p}" for p in serialization_problems(new))
        state = new
    counted[f"final:{state.phase.value}"] += 1
    if state.phase is engine.Phase.HALTED:
        counted[f"final_halted:{state.halt.code}"] += 1
    problems.extend(f"対戦の終わり: {p}" for p in log_problems(state))
    problems.extend(f"対戦の終わり: {p}" for p in engine.check_invariants(state))
    return counted, problems


def run(scenarios, seeds, *, steps: int, illegal_rate: float, serialize_every: int) -> dict:
    total, failures = Counter(), []
    for scenario in scenarios:
        for seed in seeds:
            counted, problems = run_game(scenario, seed, steps=steps, illegal_rate=illegal_rate, serialize_every=serialize_every)
            total.update(counted)
            total["games"] += 1
            if problems:
                failures.append({"scenario": scenario.name, "seed": seed, "problems": problems[:20]})
    return {"counts": dict(sorted(total.items())), "failures": failures}


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="大規模なストレス実行（ふだんの単体テストでは走らせない）")
    parser.add_argument("--scenario", action="append", help="組（tools/compat_driver.py の SCENARIOS と POWER_SCENARIOS。省略ですべて）")
    parser.add_argument("--start", type=int, default=0)
    parser.add_argument("--seeds", type=int, default=40)
    parser.add_argument("--steps", type=int, default=600)
    parser.add_argument("--illegal-rate", type=float, default=0.25)
    parser.add_argument("--serialize-every", type=int, default=25, help="書き出しの監査をする間隔（0 でしない）")
    parser.add_argument("--report", type=pathlib.Path, default=None)
    args = parser.parse_args(argv)
    scenarios = [s for s in ALL_SCENARIOS if not args.scenario or s.name in args.scenario]
    started = time.time()
    result = run(scenarios, range(args.start, args.start + args.seeds), steps=args.steps, illegal_rate=args.illegal_rate,
                 serialize_every=args.serialize_every)
    result["seconds"] = round(time.time() - started, 1)
    result["arguments"] = vars(args) | {"report": str(args.report) if args.report else None}
    if args.report:
        args.report.write_text(json.dumps(result, ensure_ascii=False, indent=1) + "\n")
    counts = result["counts"]
    print(f"対戦 {counts.get('games', 0)}・受け付けた {counts.get('accepted', 0)}・できない {counts.get('rejected_illegal', 0)}・"
          f"未対応 {counts.get('rejected_unsupported', 0)}・原典で決められない（拒否） {counts.get('rejected_unresolved', 0)}・"
          f"HALTED {sum(v for k, v in counts.items() if k.startswith('final_halted:'))}・GAME_OVER {counts.get('final:game_over', 0)}・"
          f"SUDDEN_DEATH {counts.get('final:sudden_death', 0)}・内部の誤り {counts.get('internal_error', 0) + counts.get('internal_state_integrity', 0)}・"
          f"ポケモンパワー（受け付けた） {counts.get('accepted:UsePokemonPower', 0)}（うちあまごい {counts.get('accepted:rain_dance', 0)}・"
          f"ダメージスワップ {counts.get('accepted:damage_swap', 0)}）・じこさいせい {counts.get('accepted:recover', 0)}・"
          f"かがくへんかガスで拒否 {counts.get('code:POWER_SUPPRESSED', 0)}（はたらいている MAIN {counts.get('observed:gas_working', 0)}・"
          f"消えている MAIN {counts.get('observed:gas_off_with_muk', 0)}・切り替わり {counts.get('observed:gas_toggled', 0)}）・"
          f"とうめいの判定 {counts.get('observed:evade_check', 0)}（おもて {counts.get('observed:evade_heads', 0)}・"
          f"うら {counts.get('observed:evade_tails', 0)}）・"
          f"はんげき {counts.get('observed:counterattack', 0)}（与えなかった {counts.get('observed:counterattack_skipped', 0)}・"
          f"きぜつさせた {counts.get('observed:counter_knock_out', 0)}・きぜつしたカイリキーの {counts.get('observed:counter_trigger_knocked_out_machamp', 0)}）・"
          f"こんじょうの決定 {counts.get('observed:guts_offered', 0)}（使う {counts.get('observed:ko_prevention_declared', 0)}・"
          f"使わない {counts.get('observed:ko_prevention_declined', 0)}・おもて {counts.get('observed:ko_prevented', 0)}・"
          f"うら {counts.get('observed:ko_prevention_failed', 0)}・ベンチ {counts.get('observed:guts_offered_on_bench', 0)}・"
          f"ガスで使えずきぜつ {counts.get('observed:guts_suppressed_by_gas', 0)}・特殊状態で使えずきぜつ {counts.get('observed:guts_blocked_by_condition', 0)}・"
          f"G37 {counts.get('code:UNRESOLVED_KO_PREVENTION_ATTACK_EFFECT', 0)}）・"
          f"R団のファイヤーのきぜつ {counts.get('observed:rockets_moltres_knocked_out', 0)}（ふしちょうの決定 {counts.get('observed:rebirth_offered', 0)}・"
          f"使う {counts.get('observed:post_knockout_power_declared', 0)}・使わない {counts.get('observed:post_knockout_power_declined', 0)}・"
          f"特殊状態 {counts.get('observed:rebirth_blocked_condition', 0)}・ガス {counts.get('observed:rebirth_blocked_gas', 0)}・"
          f"対戦の終わり {counts.get('observed:rebirth_not_offered_game_over', 0)}）・"
          f"ほのおのかべ {counts.get('observed:retaliation_effect_added', 0)}（はたらいた {counts.get('observed:retaliation', 0)}・"
          f"ダメージ {counts.get('observed:retaliation_damage', 0)}・期限 {counts.get('observed:retaliation_effect_removed_expired', 0)}・"
          f"W24 {counts.get('code:UNRESOLVED_RETALIATION_DOUBLE_KNOCKOUT', 0)}）・"
          f"こうらがえし {counts.get('observed:shell_effect_added', 0)}（はたらいた {counts.get('observed:shell_retaliation', 0)}・"
          f"受けたダメージの合計 {counts.get('observed:shell_received_total', 0)}・返したダメージ {counts.get('observed:shell_damage', 0)}"
          f"（合計 {counts.get('observed:shell_damage_total', 0)}・弱点 {counts.get('observed:shell_weakness', 0)}・"
          f"抵抗力 {counts.get('observed:shell_resistance', 0)}・ディフェンダー {counts.get('observed:shell_modifiers', 0)}・"
          f"きぜつ {counts.get('observed:shell_knock_out', 0)}）・とうめい {counts.get('observed:shell_evaded', 0)}・"
          f"期限 {counts.get('observed:shell_effect_removed_expired', 0)}・S37 {counts.get('observed:shell_stopped_w24', 0)}）"
          f"（{result['seconds']} 秒）")
    for failure in result["failures"]:
        print(f"- {failure['scenario']} seed {failure['seed']}: {failure['problems'][0]}")
    return 1 if result["failures"] else 0


if __name__ == "__main__":
    sys.exit(main())

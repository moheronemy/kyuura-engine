"""原典で決められない場合（既知の問い）の表（docs/event-model-v0.14.md 7 章）。

仕組みの共通の検出（同時のきぜつの原因の分かれ方・無効な要素のためのコインなど）が当たったら、この表で v0.13 の ``UNRESOLVED_…``
のコードと裁定の番号を引きます。表にない検出・コードのない問い（今の対応カードでは起こらない）は、推測で解決せず、エンジンの
不具合として止めます。

``priority`` は、2 つ以上の問いに当たったときに選ぶ順番で、v0.13 の ``engine._use_attack`` の確認の順番（ワザの実装の
``problem`` → こんらんのダメージの変更効果 → C18 → G37 → W24 → ワザの途中の確認）に合わせています。
"""

from __future__ import annotations

from dataclasses import dataclass

from ..errors import UnsupportedError


@dataclass(frozen=True)
class Question:
    key: str
    code: str | None  # None: 今の対応カードでは起こらない（当たったらエンジンの不具合）
    rulings: tuple[str, ...]
    priority: int
    message: str


QUESTIONS: dict[str, Question] = {
    q.key: q
    for q in (
        Question(
            "prevented_coin_damage", "UNRESOLVED_PREVENTED_COIN_DAMAGE", ("v0.4b",), 10,
            "「ダメージを受けない」状態の相手へのダメージの要素の量だけを決めるコインを投げるかは、原典（p.309・p.319・p.320・p.321）から"
            "決められない（投げるかどうかで乱数の続きが変わる）",
        ),
        Question(
            "evaded_effect_coin", "UNRESOLVED_EVADED_EFFECT_COIN", ("T19b",), 10,
            "「とうめい」で受けないと決まったポケモンへの効果を決めるワザのコインを投げるかは、原典（p.159・p.160・p.309・p.321）から"
            "決められない（投げるかどうかで乱数の続きが変わる）",
        ),
        Question(
            "effect_after_no_damage", "UNRESOLVED_EFFECT_AFTER_NO_DAMAGE", ("Z23",), 10,
            "説明が「ダメージを与えた後、…」の効果で、そのダメージの要素がダメージを与えなかったときに効果を与えるかは、原典（p.155・p.245・"
            "p.309・p.319〜p.321）から決められない（v0.17b）",
        ),
        Question(
            "confusion_damage_modifiers", "UNRESOLVED_CONFUSION_DAMAGE_MODIFIERS", ("v0.3c",), 20,
            "こんらんしたワザの 20 ダメージに、プラスパワー・ディフェンダーの効果を計算するかは、原典（p.257・p.309・p.321・p.322）から"
            "決められない",
        ),
        Question(
            "counterattack_double_knockout", "UNRESOLVED_COUNTERATTACK_DOUBLE_KNOCKOUT", ("C18",), 30,
            "ワザによるきぜつと、それがはたらかせた特殊能力のダメージによるきぜつが「同時に「きぜつ」した」ことになるか（p.324）は、"
            "原典（p.89・p.192・p.311・p.323〜p.325）から決められない",
        ),
        Question(
            "ko_prevention_attack_effect", "UNRESOLVED_KO_PREVENTION_ATTACK_EFFECT", ("G37",), 40,
            "「こんじょう」で「きぜつ」しなかったポケモンが、そのワザの効果を受けるかは、原典（p.89・p.193・p.309・p.311・p.320〜p.324）から"
            "決められない",
        ),
        Question(
            "retaliation_double_knockout", "UNRESOLVED_RETALIATION_DOUBLE_KNOCKOUT", ("W24", "S37"), 50,
            "このワザによるきぜつと、前の番のワザの効果のダメージによるきぜつが「同時に「きぜつ」した」ことになるか（p.324）は、原典"
            "（p.82・p.89・p.311・p.321・p.323〜p.325）から決められない",
        ),
        Question(
            "reparalysis_recovery_turn", "UNRESOLVED_REPARALYSIS_RECOVERY_TURN", ("v0.3b",), 60,
            "マヒの再付与で回復する番が変わる場合の扱いは、原典から決められない",
        ),
        # v0.31: 控えポケモン・複数のポケモンにダメージ・効果を与えるワザ（docs/held-cards-v0.31.md）で起こるようになったので、コードを付けた
        # （v0.30 まではコードのない問い。裁定の分類は変えていない）
        Question("multiple_deferred_effects", "UNRESOLVED_MULTIPLE_DAMAGE_TRIGGERS", ("C34", "C35"), 70,
                 "1 つのワザで 2 つ以上の「ダメージを受けたとき」の効果がはたらく場合の順番は、原典（p.192・p.325）から決められない"),
        Question("multiple_ko_prevention", "UNRESOLVED_KO_PREVENTION_ORDER", ("G40", "G16"), 70,
                 "きぜつするときに使える特殊能力の候補が 2 つ以上ある場合の順番は、原典（p.311・p.325）から決められない"),
        Question("multiple_post_knockout", "UNRESOLVED_POST_KNOCKOUT_POWERS_ORDER", ("P32",), 70,
                 "きぜつしたときに使える特殊能力の候補が 2 つ以上ある場合の順番は、原典（p.82・p.325）から決められない"),
        Question("post_knockout_gas_source_knocked", "UNRESOLVED_PHOENIX_GAS_SOURCE_KNOCKOUT", ("P19",), 70,
                 "かがくへんかガスの発生源が、消している特殊能力（ふしちょう）のポケモンといっしょにきぜつする場合に、その特殊能力を使えるかは、"
                 "原典（p.48・p.82・p.323・p.324）から決められない"),
        Question("multiple_evasion", "UNRESOLVED_TRANSPARENCY_COIN_ORDER", ("T27",), 70,
                 "1 つのワザで 2 匹以上の「とうめい」を持つポケモンがダメージ・効果を受ける場合の、コインの順番は、原典（p.159・p.325）から"
                 "決められない（順番で乱数の割り当てが変わる）"),
        # v0.31（docs/held-cards-v0.31.md）
        Question("discard_energy_timing", "UNRESOLVED_DISCARD_ENERGY_TIMING", ("HC1",), 5,
                 "こんらん状態のポケモンが、自分のエネルギーカードを「はがしてすてる」と書かれた（炎エネルギーカードをトラッシュして大きなダメージを"
                 "与えるタイプ以外の）ワザを使うとき、トラッシュがワザを使うための条件（宣言のとき）かワザの効果（こんらんのコインのあと）かは、"
                 "kyuura の RUL-ENERGY-DISCARD-ATTACKS の未解決の問い（炎以外のワザ）のとおり決められない（「うら」でトラッシュするかが変わる）"),
        Question("destiny_bond_knockout", "UNRESOLVED_DESTINY_BOND_KNOCKOUT", ("HC2",), 55,
                 "「みちづれ」で相手の対戦ポケモンも「きぜつ」するとき、それが同時のきぜつ（p.324）かは決められず、勝ち負けが決まる場合は"
                 "どちらの読み方かで結果が変わる"),
        Question("prevented_effect_coin", "UNRESOLVED_PREVENTED_EFFECT_COIN", ("HC3",), 10,
                 "「ワザをうけない」状態のポケモンへの効果だけを決めるコインを投げるかは、原典から決められない（投げるかどうかで乱数の続きが変わる）"),
        Question("extra_energy_colorless", "UNRESOLVED_EXTRA_ENERGY_COLORLESS", ("HC4",), 10,
                 "無色エネルギーをふくむワザで「ワザに必要なエネルギーよりも多く「水」エネルギーがついている時」の多いエネルギーの数は、無色の"
                 "ぶんを「水」エネルギーで払うかで変わり、決められない"),
        Question("deck_short", "UNRESOLVED_DISCARD_DECK_SHORT", ("HC6",), 10,
                 "山札の上から決まった枚数をトラッシュする効果で、山札の枚数が足りない場合の処理は、原典から決められない"),
        Question("copied_attack", "UNRESOLVED_COPIED_ATTACK", ("HC9",), 10,
                 "相手のワザを自分のワザとして使う効果で、選べるワザがすべて、使えないか処理が決められない"),
        # v0.32（docs/bench-search-counter-drain-v0.32.md）
        Question("opponent_pokemon_counters", "UNRESOLVED_OPPONENT_POKEMON_COUNTERS", ("CD4",), 10,
                 "ルージュラの「ヨガのポーズ」の「相手のポケモンにのっているダメージカウンター」が、相手の対戦ポケモンのものか、相手の場のポケモン"
                 "すべてのものかは決められず、相手の控えポケモンにダメージカウンターがのっていると、読み方で基本となるダメージが変わる"),
        # ルールの問いではなく、エンジンの未対応（コードは UNSUPPORTED_…。研究の対応表の停止コードには入れない）
        Question("copied_attack_unsupported", "UNSUPPORTED_COPIED_ATTACK", ("v0.31",), 10,
                 "相手のワザを自分のワザとして使う効果で、処理できるワザがなく、エンジンが対応していないワザがある"),
        # v0.34（docs/barrier-resume-coin-bonus-v0.34.md）
        Question("special_poison_overwrite", "UNRESOLVED_SPECIAL_POISON_OVERWRITE", ("TP3",), 10,
                 "どく状態のポケモンが、どくのダメージの違う特殊などく状態にする効果を受けたときにどちらのどく状態になるかは、原典から決められない"
                 "（p.322 は、特殊などくのポケモンが通常のどくを受けたときだけを書く。docs/special-conditions-v0.3a.md の 15）"),
        Question("reduced_damage_bench_target", "UNRESOLVED_REDUCED_DAMAGE_BENCH_TARGET", ("NK5",), 10,
                 "「なきつく」の「このカードにワザを使う時、与えるダメージが20へる」が、そのポケモンが控えにいるときの控えポケモンへのダメージにも"
                 "当てはまるかは、原典から決められない"),
        # v0.35 から、ダメージの要素（``programs.Damage``）は順番の決定を出す。この問いに当たるのは、決定を出せない呼ぶ側（控えへのダメージ・返す
        # 効果のダメージ・v0.13 の約束で書いたワザ・前の要素の結果を決定のあとに運べない並び。今の対応カードでは起こらない）だけ
        Question("damage_step_order", "UNSUPPORTED_DAMAGE_STEP_ORDER", ("v0.34", "v0.35"), 10,
                 "p.321 の同じ段階に加算でない効果を含む 2 つ以上の効果があり、計算の順番で結果が変わるが、このダメージの処理は順番を選ぶ決定を"
                 "出せない（エンジンの未対応）"),
        # v0.36（docs/sand-attack-retreat-lock-v0.36.md）
        Question("attack_check_confusion", "UNRESOLVED_ATTACK_CHECK_CONFUSION", ("AC6",), 6,
                 "こんらん状態のポケモンが、ワザを失敗させる効果（「すなかけ」・「えんまく」など。p.309 の手順 4）を受けてワザを使うとき、手順 4 の"
                 "コインでワザが失敗したら、手順 5 のこんらんのコイン（「うら」なら自分に 20 ダメージ）をおこなうかは、原典（p.309・p.322・p.323）"
                 "から決められない（コインの数・ダメージが変わる）"),
        # v0.45: v0.36 の AC13（2 つ以上の手順 4 の効果。v0.36 では起こらなかった）。カスミのタッツーの「スミをかける」（期限のない効果）で起こる
        # （docs/conditional-damage-energy-v0.45.md）
        Question("multiple_attack_checks", "UNRESOLVED_MULTIPLE_ATTACK_CHECKS", ("AC13",), 5,
                 "ワザを使うポケモンが、ワザを失敗させる効果（p.309 の手順 4。「スミをかける」の「それ以後」の効果・「えんまく」など）を 2 つ以上受けているとき、"
                 "効果ごとにコインを投げるのか（その順番）、1 枚のコインで両方を決めるのかは、原典（p.309・p.322・p.323）から決められない（コインの数・ワザが"
                 "失敗するかが変わる）"),
        Question("return_in_play_to_deck_with_knockout", "UNRESOLVED_RETURN_IN_PLAY_TO_DECK_KNOCKOUT", ("RD9",), 50,
                 "ワザを使ったポケモンが、ワザの効果で自分と自分についているカードを山札にもどし（バトル場が空く）、同じワザで HP 以上になった"
                 "ポケモンがいるとき、バトル場に出す時点と、きぜつの処理（サイド・勝ち負け・相手がバトル場に出す）との順番は、原典（p.311・p.313・"
                 "p.323・p.324）から決められない（出す順番・勝ち負けが変わりうる）"),
        # v0.37（docs/fifteen-reused-effects-v0.37.md 4 章）
        Question("bench_damage_weakness_resistance", "UNRESOLVED_BENCH_DAMAGE_WEAKNESS_RESISTANCE", ("JS1",), 10,
                 "説明に「「弱点・抵抗力」に関係なく」のない控えポケモンへのダメージ（第1弾のダグトリオの「じしん」）に、弱点・抵抗力を計算するかは、"
                 "2000.02.14 版の記録から決められず、控えに、ワザを使うポケモンのタイプに弱点・抵抗力を持つポケモンがいると、読み方で受けるダメージが変わる"),
        # v0.38（docs/bench-switch-combined-v0.38.md 4 章）
        Question("damage_trigger_timing", "UNRESOLVED_DAMAGE_TRIGGER_TIMING", ("GK1",), 10,
                 "「ダメージを受けたとき」の効果（はんげき・わるいねぞう・ほのおのかべ・こうらがえし）がはたらき、ワザの要素がダメージ以外の効果をはさんで"
                 "もう一度ダメージの要素を持つ（サイドンの「げきとつ」の入れ替え → 自分にも 20）とき、その効果を処理する時点は、記録（ダメージの処理を"
                 "すべてのせたあと、かつダメージ以外の効果の前。p.89・p.309）から決められない（自分へのダメージとの順番で、同時のきぜつ・効果を与えるかが変わりうる）"),
        # v0.41（docs/heal-counter-status-v0.41.md 4 章）
        Question("counter_transfer_protected", "UNRESOLVED_COUNTER_TRANSFER_PROTECTED", ("CX1",), 10,
                 "ワザで自分の側のダメージカウンターを相手の対戦ポケモンにのせる・取り替える効果（ナツメのゴルダックの「ダメージシフト」・R団のミュウツーの"
                 "「チェンジダメージ」）で、相手の対戦ポケモンがその効果を受けない（「ワザをうけない」状態・「とうめい」）とき、自分の側のダメージカウンターを"
                 "とりのぞく・取り替えるかは、記録（p.309・p.320・p.321）から決められない（自分のポケモンのダメージが変わる）"),
        # v0.43（docs/declared-entry-powers-v0.43.md 4 章）
        Question("entry_power_during_attack", "UNRESOLVED_ENTRY_POWER_DURING_ATTACK", ("PW4",), 10,
                 "ワザの効果で山札から進化カードを重ねた（エリカのピッピの「つきのちから」）とき、そのカードの「場に出た時」に使える特殊能力（わるいカイリューの"
                 "［てしたをよぶ］）を使えるかは、記録（p.309「ワザを使っている最中に…特殊能力の使用を宣言してはいけません」と、場に出た時に1度だけ使える説明）から"
                 "決められない"),
        # v0.43: 山札の進化カードがどれも、重ねると HP がのっているダメージ以下になる（v0.4a の H1。つきのちから。選べる答えがない決定にしない）
        Question("evolution_hp_every_card", "UNRESOLVED_EVOLUTION_HP", ("v0.4a",), 10,
                 "進化すると HP がのっているダメージ以下になる。そのときにきぜつするか（いつきぜつの判定をするか）は『オフィシャルブック2000』（p.310・p.323）から"
                 "決められない（v0.4a の H1）"),
        # v0.44（docs/search-evolution-once-attacks-v0.44.md 5 章）
        # v0.46: エリカのフシギバナの「かくさんソーラービーム」の「相手の控えポケモンを2匹選び」で、控えが 1 匹のときも同じ問い（選ぶのがカードでなくポケモン。
        # 新しい問いにしない）
        Question("stated_cards_short", "UNRESOLVED_STATED_CARDS_SHORT", ("FC1",), 10,
                 "説明が決まった数（「カードを2枚選び」「もどしたのと同じ枚数」「控えポケモンを2匹選び」）のカード・ポケモンを選ばせるとき、選べるものがその数より少ない"
                 "場合に、選べるだけ選ぶのか、その内容を処理しないのか（山札を切るか）は、kyuura の記録・印刷の文面から決められない（p.309 の「処理の対象がなくなって"
                 "しまっている場合」は対象がないときの規定で、足りないときを書かない）"),
        # v0.44 の GV1。v0.44 ではコードのない問い（今の対応カードでは起こらない）としたが、エリカのピッピの「つきのちから」は自分の場のほかのポケモン（サカキの
        # コイキング）も進化させられるので起こる（公開の apply_command で内部エラーになっていた）。v0.45 で停止コードを付けた（裁定は未解決のまま。
        # docs/conditional-damage-energy-v0.45.md 2 章）
        # v0.50（docs/mew-devolution-spray-v0.50.md 5 章）。ミュウの「たいかビーム」で選べる、進化カードの重なっているポケモンが、どれも「ばける」でのせたカードのあるポケモン
        # （「進化・退化」はできない）（DV5）。選べるか・選んだらどうなるかで結果が変わる
        Question("devolution_target_disguised", "UNRESOLVED_DEVOLUTION_TARGET_DISGUISED", ("DV5",), 10,
                 "「ばける」でのせたカードのあるポケモン（説明に「(ただし「進化・退化」はできない)」）を、退化させる効果で選べるか、選んだらのせたカードをはがすのか何も"
                 "起こらないのかは、記録で決まらない"),
        # v0.50（docs/mew-devolution-spray-v0.50.md 5 章）。今の番に退化したポケモンを、山札から重ねる効果で進化させる組（DV2。手札から重ねる進化と同じ問い）
        Question("evolve_after_devolution", "UNRESOLVED_EVOLVE_AFTER_DEVOLUTION", ("DV2",), 10,
                 "今の番に退化したポケモンを、同じ番に進化させられるかは、退化したポケモンが「退化前とは別のポケモン」（p.324）であることと、p.310 の「その番の最初から"
                 "場に出ていた」「その番に進化した」の関係が記録で決まらない"),
        Question("evolution_permission_from_deck", "UNRESOLVED_EVOLUTION_PERMISSION_FROM_DECK", ("GV1",), 10,
                 "トレーナー「サカキ」で今の番に進化させてよいポケモン（今の番に場に出した・進化した）を、山札から重ねる効果で進化させられるかは、説明の「(ポケモンを"
                 "進化させる時には、あなたの手札から「進化カード」を出して、そのポケモンの上にのせる)」が許可を手札から重ねる進化に限るのかが決められない"),
        # v0.46（docs/continuous-powers-v0.46.md 5 章）。返す効果のダメージ（ほのおのかべ・こうらがえし・クロスカウンター。前の番のワザの効果）に、ワザが使われた時の
        # 特殊状態で決める常にはたらく特殊能力（エリカのフシギソウの［くつろぐかおり］）が当てはまるかで結果が変わる
        Question("calming_retaliation", "UNRESOLVED_CALMING_AROMA_RETALIATION", ("CP1",), 10,
                 "返す効果のダメージ（前の番のワザの効果。GR-2000-P321-ATTACK-DAMAGE でそのワザのダメージ）に［くつろぐかおり］の「ワザが使われた時、すでに…状態なら、"
                 "この力ははたらかない」を当てはめるとき、「ワザが使われた時」が返す効果を与えた前の番のワザか、きっかけになったこの番のワザかは、印刷の文面・kyuura の"
                 "記録から決められない（前の番のワザのときの特殊状態は記録していない）"),
        # v0.48（docs/effective-pokemon-properties-v0.48.md 3 章・4 章）
        Question("shift_color_duration", "UNRESOLVED_SHIFT_COLOR_DURATION", ("VS1",), 10,
                 "モルフォンの［へんしょく］で変えた色が、使った番のあと・バトル場からベンチにもどったあと・この力が消えている（ねむり・マヒ・こんらん状態・"
                 "かがくへんかガス）あいだも続くかは、印刷の文面（効果の期限を書かない）・kyuura の記録から決められず、変えた色と印刷の色で結果が変わる"),
        # v0.88（docs/type-energy-colors-v0.88.md 4 章）: 特殊能力で色を変える効果（［せんすい］・［エナジーコンバーター］）とこうごうせい
        Question("color_effect_continuation", "UNRESOLVED_COLOR_EFFECT_CONTINUATION", ("CE1",), 10,
                 "［せんすい］・［エナジーコンバーター］の「この番が終わるまで」の効果が、使ったあとに力が消えた・発生源が場をはなれた・発生源のカードが変わった・色を変えた"
                 "エネルギーカードが場をはなれてもう一度ついたあとも続くかは、印刷の文面・kyuura の記録（CR-CHEMICAL-GAS-PRIOR-RESULTS は消える前にすませた結果のもの）から"
                 "決められず、続く読み方と続かない読み方で結果が変わる"),
        Question("color_replacement_order", "UNRESOLVED_COLOR_REPLACEMENT_ORDER", ("CE2",), 10,
                 "同じエネルギー・同じポケモンの色を、続いてはたらく 2 つの効果が違う色にする（エナジーコンバーターとこうごうせい・エナジーバーン、こうごうせいと［きせきのかぜ］、"
                 "［せんすい］と［へんしょく］）とき、どちらの色になるかは、印刷の文面・kyuura の記録（GR-2000-P325-SAME-TIMING は続いてはたらく置きかえの優先を決めない）から"
                 "決められない"),
        # v0.90（docs/markers-counters-v0.90.md 6 章）: ドーブルの「ペイント」の色マーカーと、特殊能力で色を変える効果（CE2 は特殊能力・エネルギーの効果どうしの問い）
        Question("color_marker_precedence", "UNRESOLVED_COLOR_MARKER_PRECEDENCE", ("CM1",), 10,
                 "ドーブルの「ペイント」の色マーカーと、特殊能力で色を変える効果（［へんしょく］・［せんすい］）が同じポケモンにあるとき、どちらの色としてあつかうか（のせた・使った順か、"
                 "どちらかが優先するか）は、印刷の文面・2000.02.14 版の公式ルール・kyuura の記録から決められない"),
        # v0.90（docs/markers-counters-v0.90.md 8 章）: ミュウツーの「かんぜんかいふく」の「ダメージカウンターやマーカー」
        Question("full_recovery_counters", "UNRESOLVED_FULL_RECOVERY_COUNTERS", ("KR1",), 10,
                 "ミュウツーの「かんぜんかいふく」の「自分にのっているダメージカウンターやマーカーをすべて取りのぞき」が、ダメージカウンター以外のカウンター（ほねカウンター・"
                 "たべものカウンター）も取りのぞくかは、印刷の文面（「ダメージカウンターやマーカー」）・2000.02.14 版の公式ルール・kyuura の記録から決められず、のっていると結果が変わる"),
        # v0.91（docs/marker-check-field-reset-v0.91.md 5 章）: エレブーの「かみなりショック」で、ひらいしんマーカーののった相手の対戦ポケモンが受ける目安と 20 の 2 つのダメージ
        Question("lightning_bolt_units", "UNRESOLVED_LIGHTNING_BOLT_DEFENDER_UNITS", ("HR1",), 10,
                 "エレブーの「かみなりショック」で、ひらいしんマーカーののっている相手の対戦ポケモンが受ける、ダメージの目安（p.320 の省略された「相手に10ダメージ」）と「それぞれ20"
                 "ダメージ」を、別々のダメージとして p.321 の段階で計算するか（v0.40 の NE3 はわるいマタドガスの「みんなでばくはつ」の実装上の判断）、合わせて 1 つのダメージとして計算するかは、"
                 "印刷の文面・2000.02.14 版の公式ルール・kyuura の記録から決められず、受けるダメージ（プラスパワー・抵抗力・ダメージを変える効果）や「ダメージを受けたとき」の効果が変わる"),
        # v0.91（docs/marker-check-field-reset-v0.91.md 6 章）: ポリゴンの「ハイパーテクスチャー」の「のっているなら」のかかる範囲
        Question("hyper_texture_unmarked", "UNRESOLVED_HYPER_TEXTURE_UNMARKED_TARGET", ("HX1",), 10,
                 "ポリゴンの「ハイパーテクスチャー」で、色マーカーののっていないポケモンを選んだとき、「そのポケモンに「色マーカー」がのっているなら、それをとりのぞき、好きな「色(タイプ)」"
                 "(無色以外)を選んでから、そのポケモンの上に「色マーカー」を1つのせる」の「のっているなら」が、とりのぞくことだけにかかる（新しくのせる）のか、そのあとの選ぶ・のせるにも"
                 "かかる（何もしない）のかは、印刷の文面・kyuura の記録から決められない（日本語の文の形からは後者が自然だが、記録がない）"),
        # v0.91（docs/marker-check-field-reset-v0.91.md 7 章）: ポリゴンの「オールクリア」
        Question("all_clear_other_effects", "UNRESOLVED_ALL_CLEAR_OTHER_EFFECTS", ("ZC1",), 10,
                 "ポリゴンの「オールクリア」の「おたがいの場にいるポケモン全員を…「その他の効果」から、すべて回復させる」が、ワザによる持続する効果のほか、特殊能力で色を変えた記録"
                 "（［へんしょく］）や、プレイヤーに与えた効果で場のポケモンにはたらき、この番のあとも続くもの（見えない壁・まきちらせ!ベトベトガス・ふしぎなガス）も消すかは、印刷の文面・"
                 "kyuura の記録から決められない"),
        Question("all_clear_attack_source", "UNRESOLVED_ALL_CLEAR_ATTACK_SOURCE", ("ZC2",), 10,
                 "ポリゴンの「オールクリア」を、特殊能力で持ったワザとして使う（［へんしん］・［サイコリンク］・「ばける」など）と、「このワザを使っているあいだ…特殊能力を使うことが"
                 "できず、その力も消える」で、使っているワザを持たなくなる。そのあとワザの処理を続けるかは、印刷の文面・kyuura の記録から決められない"),
        Question("all_clear_fossil", "UNRESOLVED_ALL_CLEAR_FOSSIL_IN_PLAY", ("ZC3",), 10,
                 "ポリゴンの「オールクリア」の「おたがいの場にある、すべての「トレーナーカード」」に、場のなにかの化石のカード（「場に出ている限りポケモンとしてあつかわれる」。ピッピ人形の"
                 "「場に出ているとき以外は、トレーナーカードとしてあつかう」とは書き方が違う）が入るかは、印刷の文面・kyuura の記録から決められない"),
        Question("color_changed_energy_card", "UNRESOLVED_COLOR_CHANGED_ENERGY_CARD", ("CE3",), 10,
                 "エナジーコンバーター・こうごうせいで「エネルギー」の色が変わったエネルギーカードが、説明の「「○」エネルギーカード」（カードとしての色。「基本エネルギー"
                 "カード」の色を含む）に当たるかは、印刷の文面・kyuura の記録（エナジーバーンの同じ問い UQ-ENERGY-BURN-TRANSFER も未解決）から決められない"),
        Question("change_absent_weakness_resistance", "UNRESOLVED_CHANGE_ABSENT_WEAKNESS_RESISTANCE", ("PG1",), 10,
                 "弱点（抵抗力）を持たないポケモンの弱点（抵抗力）を「好きな「色」にかえる」効果（ポリゴンの「テクスチャー1」「テクスチャー2」）で、弱点（抵抗力）を新しく"
                 "持たせるのか、何もしないのか（抵抗力なら引く数も）は、印刷の文面・kyuura の記録から決められない（英語版の「If the Defending Pokémon has a Weakness」は"
                 "持ち込まない）"),
        # v0.49（docs/virtual-attacks-transformation-v0.49.md 5 章）
        Question("transform_energy_count", "UNRESOLVED_TRANSFORM_ENERGY_COUNT", ("TE1",), 10,
                 "メタモンの［へんしん］の「エネルギーカードは、このカードについている限り、どの色のエネルギーとしても使うことができる」が、ワザに必要なエネルギーの"
                 "支払いのほか、ワザの説明がついている「○」エネルギー（カード）を数える・トラッシュするときにも当てはまる（どの色としても数える・選べる）かは、"
                 "印刷の文面・kyuura の記録から決められず、2 つの読み方で数える・選べるカードが変わる"),
        # v0.58（docs/stadium-reuse-special-energy-v0.58.md）
        Question("rainbow_energy_type", "UNRESOLVED_RAINBOW_ENERGY_TYPE", ("RB1",), 10,
                 "場のレインボーエネルギー（「どの色の基本エネルギーカードとして使ってもよい」）を、ワザの説明の「「○」エネルギー(カード)」として数える・選ぶかは、"
                 "印刷の文面・kyuura の記録から決められず、数える・選べるカードが変わる（支払い・エナジートランスの「草」は決まっている）"),
        Question("rainbow_attach_type", "UNRESOLVED_RAINBOW_ATTACH_AS_TYPE", ("RB2",), 10,
                 "山札・トラッシュ・手札のレインボーエネルギーを、「「○」エネルギーカード」をつけるワザの効果で、その色のエネルギーカードとして選べるかは、kyuura の記録から"
                 "決められない"),
        # v0.85（docs/entry-powers-energy-lifecycle-v0.85.md）
        Question("miracle_energy_type", "UNRESOLVED_MIRACLE_ENERGY_AS_TYPE", ("MEC1",), 10,
                 "場のミラクルエネルギー（「すべての「色(タイプ)」の「エネルギー」2個ぶんの「エネルギーカード」」）を、ワザの説明の「「○」エネルギー(カード)」として数える・選ぶか"
                 "（［おいしげる］の「「草」エネルギーカード」を含む）は、印刷の文面・kyuura の記録から決められず、数える・選べるカードが変わる"),
        Question("rainbow_basic_energy_card", "UNRESOLVED_RAINBOW_AS_BASIC_ENERGY_CARD", ("RB3",), 10,
                 "場のポケモンについているレインボーエネルギーを、説明の「基本エネルギーカード」として選べるかは、印刷の文面・kyuura の記録から決められない"),
        # v0.75（docs/search-energy-pokemon-v0.75.md 5 章）
        Question("rainbow_recover_type", "UNRESOLVED_RAINBOW_RECOVER_AS_TYPE", ("RB5",), 10,
                 "トラッシュのレインボーエネルギー（場の外の特殊エネルギーカード）を、ワザの効果でトラッシュから手札に加える「「○」エネルギーカード」として選べるかは、"
                 "印刷の文面・kyuura の記録から決められない（RB2・FV1 と同じ種類の、別の場面の問い）"),
        # v0.56（docs/trainer-decisions-turn-effects-v0.56.md 7 章）
        Question("trainer_self_bonus", "UNRESOLVED_MISTY_SELF_DAMAGE", ("MS1",), 10,
                 "トレーナー「カスミ」の「「カスミのポケモン」が使うワザが対戦ポケモンにダメージを与える時、…「+20」される。(控えポケモンへのダメージは、そのまま)」を、"
                 "ワザを使うポケモン自身（自分の対戦ポケモン）へのダメージに当てはめるかは、印刷の文面・kyuura の記録から決められず、当てはめるかどうかで最終ダメージが変わる"),
        Question("vermilion_attack_order", "UNRESOLVED_VERMILION_GYM_ATTACK_ORDER", ("VM1",), 5,
                 "クチバシティジムのコイン（「ワザを使う時」）と、p.309 のワザを使う手順 4（ワザを失敗させる効果のコイン）・手順 5（こんらんのコイン）・ワザの失敗の順番と、"
                 "ワザが失敗したときに「うら」の自分への 10 ダメージを与えるかは、2000.02.14 版の公式ルール・印刷の文面・kyuura の記録から決められない（v0.57）"),
        Question("trainer_poison_order", "UNRESOLVED_KOGA_POISON_ORDER", ("KG1",), 10,
                 "トレーナー「キョウ」の効果でどく状態にしたポケモンを、同じワザの効果が受けるダメージの違うどく状態（特殊などく）にするとき、キョウの効果とワザの効果の"
                 "順番（どちらのどく状態が残るか）は、印刷の文面・kyuura の記録から決められない"),
        # v0.59（docs/energy-control-power-suppression-v0.59.md）
        Question("buzzap_energy_type", "UNRESOLVED_BUZZAP_ENERGY_CARD_TYPE", ("BZ2",), 10,
                 "マルマインの［エネエネ］で「○」エネルギー2個分になってついているマルマインのカードを、ワザの説明の「「○」エネルギー(カード)」として数える・選ぶかは、"
                 "印刷の文面・kyuura の記録から決められず、数える・選べるカードが変わる（出すエネルギーの個数と色は決まっている）"),
        # v0.60（docs/coins-defense-rebellion-v0.60.md）
        Question("bench_coin_transparency_order", "UNRESOLVED_BENCH_COIN_TRANSPARENCY_ORDER", ("TS1",), 70,
                 "サンダーの「サンダーストーム」の控えポケモンそれぞれのコインを、すべて投げてからダメージを与えるのか、1 匹ずつ投げてダメージを与えるのかは、印刷の文面・"
                 "kyuura の記録から決められない。どちらでも結果の分布は同じだが、「とうめい」のコインがあいだに入ると乱数の割り当てが変わる"),
        # 今の対応カードでは起こらない（コードがない。当たったらエンジンの不具合として止める）
        # v0.17b（docs/rocket-snorlax-v0.17b.md）
        # v0.61: わるいギャラドスの［ファイナルビーム］で起こるようになった（Z9 の停止コードを付けた。［ファイナルビーム］は決定で使うを選んだときに同じコードで止める。
        # ``effects.BeamOnKnockOut.use_problem``）
        Question("power_damage_weakness_resistance", "UNRESOLVED_POWER_DAMAGE_WEAKNESS_RESISTANCE", ("Z9",), 90,
                 "説明に「弱点・抵抗力」に関係なく、と書かれていない特殊能力のダメージで、受けるポケモンの弱点・抵抗力が与えるポケモンのタイプ"
                 "（弱点・抵抗力を計算するかで結果が変わる）"),
        Question("ko_prevention_self_effect", None, ("Z22",), 90,
                 "ワザを使ったポケモン自身への効果の前に、そのポケモンが HP 以上になり、きぜつの判定で任意の効果（こんじょう）を使える"),
        # v0.31: 「みちづれ」がはたらくワザのきぜつの判定で、任意の効果（こんじょう）の候補もある（v0.60 までは対応カードで起こらない、コードのない問い）。
        # v0.61: 「みちづれ」で「きぜつ」するわるいギャラドスが［ファイナルビーム］を使えるか（みちづれのきぜつが「相手のワザによって」か。みちづれのきぜつの扱いの問いで、
        # HC2 と同じコード。docs/reactive-powers-trainer-damage-v0.61.md 2.3 節）で起こるようになった
        Question("destiny_bond_with_ko_prevention", "UNRESOLVED_DESTINY_BOND_KNOCKOUT", ("HC2",), 90,
                 "「みちづれ」がはたらくワザのあとのきぜつの判定で、きぜつするときに使える特殊能力の候補もある"),
        # v0.60（docs/coins-defense-rebellion-v0.60.md）: 「ワザのダメージを変える常にはたらく特殊能力」で、持っているのが相手の対戦ポケモン以外の相手の場のポケモンのものは、
        # 今の写しにない（［くつろぐかおり］はバトル場にいる限りはたらくので、持っているのは受けるポケモン自身）
        # v0.97（docs/unown-research-idfnj-v0.97.md 9 章）: ベンチのアンノーン[N] の［NORMAL df］（相手の場のほかのポケモンの特殊能力）と、「無色」ポケモンが写したスピードスターで
        # 起こるようになったので、コードを付けた（問い・分類は変えていない。v0.96 まではコードのない問い）
        Question("speed_star_scope", "UNRESOLVED_SPEED_STAR_SCOPE", ("SS1",), 90,
                 "タケシのサンドパンの「スピードスター」の「相手の持っている…その他の効果」に、相手の対戦ポケモン自身が持っている効果だけでなく、相手の場のほかのポケモンが"
                 "持っている常にはたらく特殊能力も含むかは、印刷の文面・kyuura の記録から決められず、最終ダメージが変わる"),
        # v0.97（docs/unown-research-idfnj-v0.97.md 8 章）: ［DARK df］・［NORMAL df］（「自分の場のほかの…がはたらいているとき、この力は、はたらかない」）が 2 匹以上ではたらきうる
        Question("self_excluding_power_copies", "UNRESOLVED_SELF_EXCLUDING_POWER_COPIES", ("DF1",), 10,
                 "「自分の場のほかのアンノーン「D」の「DARK df」がはたらいているとき、この力は、はたらかない」の特殊能力（［DARK df］・［NORMAL df］）がはたらきうるカードが自分の場に "
                 "2 匹以上いるとき、どれがはたらくか・1 つもはたらかないのかは、印刷の文面・kyuura の記録から決められず（多くても 1 つ。CR-UNOWN-DF-AT-MOST-ONE。kyuura の "
                 "UQ-SELF-EXCLUDING-POWER-COPIES）、読み方で受けるダメージ・要る決定が変わる（uid・場の並び・場に出た順で代表を選ばない）"),
        # v0.89（docs/selected-target-damage-v0.89.md 4.3 節）: ブラッキーの「だましうち」（だれの効果かを書かない「…その他の効果」に関係なく）
        Question("ignored_effects_scope", "UNRESOLVED_IGNORED_EFFECTS_SCOPE", ("FA1",), 10,
                 "ブラッキーの「だましうち」の「「弱点・抵抗力・特殊能力・その他の効果」に関係なく」（「相手の持っている」「そのポケモンの持っている」のない書き方）が、"
                 "受けるポケモン自身の持っている効果だけを除くのか、受けるポケモンの持ち主の場のポケモンの効果も除くのか、ワザを使うポケモン・スタジアム・トレーナーの効果も"
                 "含めてすべてを除くのかは、印刷の文面・kyuura の記録から決められず、読み方で受けるダメージ（無効になるか・［ベンチガード］を含む）が変わる"),
        # v0.61（docs/reactive-powers-trainer-damage-v0.61.md 4 章）: タケシのオコリザルの［ずらかる］
        Question("scram_timing", "UNRESOLVED_SCRAM_TIMING", ("SC1",), 90,
                 "ワザの処理の途中で残りHPが「10」になったときに［ずらかる］がはたらく時点（その時点か、ダメージの処理のあとか、ワザのあとか）は、印刷の文面・2000.02.14 版の"
                 "記録から決められず、時点で結果が変わる（「10」を通ってさらにダメージを受けた・そのポケモンによるワザの残りの要素がある・2 匹が同時にもどる）"),
        Question("scram_power_restored", "UNRESOLVED_SCRAM_POWER_RESTORED", ("SC2",), 90,
                 "残りHPが「10」のまま、ねむり・マヒ・こんらん・かがくへんかガスなどで［ずらかる］の力が消えていたポケモンの力がもどったとき、「残りHPが「10」になった時」に"
                 "当たるかは、印刷の文面・kyuura の記録から決められない"),
        # v0.62（docs/history-attacks-v0.62.md 7 章）: 前の番のワザの履歴を読むワザ
        Question("earthdrill_copied_use", None, ("ED1",), 10,
                 "タケシのダグトリオの「ドリルホール」の「このカードが、前の自分の番に「あながくれ」を使っていた」に、ほかのワザ（「ゆびをふる」など）で「あながくれ」を"
                 "自分のワザとして使ったことが当たるかは、印刷の文面・kyuura の記録から決められない"),
        Question("mirror_move_received_attack", "UNRESOLVED_MIRROR_MOVE_RECEIVED_ATTACK", ("MM1",), 10,
                 "ピジョンの「オウムがえし」の「前の相手の番で受けた「ワザ」」が、ダメージの要素だけを受けなかった（「ダメージを受けない」状態など）ワザ・相手のワザを"
                 "自分のワザとして使ったワザ（宣言したワザと処理したワザのどちら）を指すかは、印刷の文面・kyuura の記録から決められない"),
        Question("mirror_move_attack_conditions", "UNRESOLVED_MIRROR_MOVE_ATTACK_CONDITIONS", ("MM2",), 10,
                 "ピジョンの「オウムがえし」で「同じ「ワザ」をだす」とき、そのワザに必要なエネルギー・説明が書く使うための条件をみたす必要があるか（「ゆびをふる」の"
                 "「必要なエネルギーがついていなくても、かまわない」は書かれていない）は、印刷の文面・kyuura の記録から決められない"),
        Question("mirror_move_lasting_effect", "UNRESOLVED_MIRROR_MOVE_LASTING_EFFECT", ("OM1",), 10,
                 "オニスズメの「オウムがえし」で、続く効果（ねむり・こんらん・どく・持続する効果）を与えるとき、「「オウムがえし」の効果は1回で消える」が、受けたものを"
                 "1 度だけ与えることか、与えた効果が 1 回で消えることかは、印刷の文面・kyuura の記録から決められない（与えた効果が続くかが変わる）"),
        Question("mirror_move_non_attack", "UNRESOLVED_MIRROR_MOVE_NON_ATTACK", ("OM2",), 10,
                 "オニスズメの「オウムがえし」の「前の相手の番に、このカードが受けたダメージと効果」に、相手のワザ以外（トレーナー・特殊能力など）で受けたダメージ・効果を"
                 "含むかは、印刷の文面・kyuura の記録から決められない"),
        # ルールの問いではなく、エンジンの未対応（コードは UNSUPPORTED_…。研究の対応表の停止コードには入れない）
        Question("mirror_move_unsupported_effect", "UNSUPPORTED_MIRROR_MOVE_EFFECT", ("v0.62",), 10,
                 "オニスズメの「オウムがえし」で、受けたダメージ・マヒ以外の効果（入れ替え・エネルギー・ダメージカウンター・回復など）を与えるのは、エンジンが対応していない"),
        Question("mirror_move_unsupported_attack", "UNSUPPORTED_MIRROR_MOVE_ATTACK", ("v0.62",), 10,
                 "ピジョンの「オウムがえし」で出すワザを、エンジンが自分のワザとして処理できない（場に出てから1回しか使えないワザ・要素の並びのないワザ）"),
        # v0.64（docs/geodude-line-unbounded-coins-v0.64.md 3 章）。ルールの問いではなく、エンジンの未対応（今の写しでは起こらない場だけ）
        Question("unbounded_coin_preflight", "UNSUPPORTED_UNBOUNDED_COIN_PREFLIGHT", ("v0.64",), 10,
                 "「うら」が出るまで投げるコインの、先読みの有限の組の根拠が扱っていない計算・前提の場（エンジンの未対応）"),
        # v0.65（docs/reactive-decisions-v0.65.md 6 章）
        Question("ninja_trick_attack_order", "UNRESOLVED_NINJA_TRICK_ATTACK_COIN_ORDER", ("NT1",), 10,
                 "キョウ秘伝,変わり身の術の「相手がワザを使う時」の入れ替えと、ワザの宣言のあとにワザの要素より先に投げるコイン（p.309 の手順 4（すなかけ・［はんこう］）・手順 5"
                 "（こんらん）・クチバシティジム）のどちらが先かは、印刷の文面・kyuura の記録から決められない（入れ替えるかを決めるときにコインの結果が分かるか・ワザが失敗したあとも"
                 "入れ替えられるかが変わる）"),
        Question("ninja_trick_leaves_play", "UNRESOLVED_NINJA_TRICK_LEAVES_WITH_POKEMON", ("NT2",), 10,
                 "キョウ秘伝,変わり身の術がついているポケモンを、ついているすべてのカードといっしょに山札・手札にもどす効果で、このカードもいっしょにもどすか、「そのポケモンがバトル場を"
                 "はなれた時、このカードをトラッシュする」にしたがってトラッシュするかは、印刷の文面・kyuura の記録から決められない"),
        Question("bench_guard_zero_reaction", "UNRESOLVED_BENCH_GUARD_ZERO_DAMAGE_REACTION", ("BG2",), 10,
                 "［ベンチガード］で、もとのポケモンが受けるダメージがすべてサイドンに移って 0 になるとき、もとのポケモンが「ダメージを受けた」ことになるか（「ダメージを受けたとき」の"
                 "効果・こんじょうがはたらくか）は、印刷の文面・kyuura の記録から決められない（2 匹以上のサイドンで 0 になる答えがある）"),
        # v0.66（docs/optional-trainers-v0.66.md 5 章）
        Question("charity_below_zero", "UNRESOLVED_CHARITY_BELOW_ZERO", ("CA1",), 10,
                 "お上品攻撃の「そのダメージを好きなだけ小さくしてよい」が、p.321 の 5 段階のダメージを 0 より小さくすること（そのあとの段階で増える効果があるとき、0 にしたときと"
                 "結果が変わる）を含むかは、印刷の文面・kyuura の記録から決められない（p.321 は計算の途中の 0・マイナスを認めるが、「小さくする」量の下限は書かれていない）"),
        # ルールの問いではなく、エンジンの未対応（コードは UNSUPPORTED_…。研究の対応表の停止コードには入れない）
        Question("damage_reduction_decision", "UNSUPPORTED_DAMAGE_REDUCTION_DECISION", ("v0.66",), 10,
                 "お上品攻撃で減らす量を選ぶ決定を、このダメージ（前の番のワザの効果で返すダメージ・前の要素の結果を運べない並び）では出せない（エンジンの未対応）"),
        # v0.68（docs/final-pmcg-cards-v0.68.md 3 章）: キョウのベトベトンの［だつりょくえき］。採用の仕様（自動的にはたらく・ダメージの要素のあと）でも決まらない場合
        Question("energy_drain_attacker_knocked_out", "UNRESOLVED_ENERGY_DRAIN_ATTACKER_KNOCKED_OUT", ("DR8",), 10,
                 "［だつりょくえき］を処理する時点で、ダメージを与えたポケモンがすでに HP 以上のダメージを受けているとき（同じワザの自分へのダメージ・返す効果のダメージなど）、"
                 "コインを投げ、エネルギーカードを選んでトラッシュするかは、印刷の文面・最新の説明・kyuura の記録（UQ-ENERGY-DRAIN-ATTACKER-KO）から決められない"),
        Question("energy_drain_no_energy", "UNRESOLVED_ENERGY_DRAIN_NO_ENERGY", ("DR13",), 10,
                 "ダメージを与えたポケモンにエネルギーカードがついていないとき、［だつりょくえき］のコインを投げるかは、日本語の文面・kyuura の記録（UQ-ENERGY-DRAIN-NO-ENERGY）"
                 "から決められない（英語版の「if it has any」は使わない）"),
        Question("reflect_shield_timing", "UNRESOLVED_REFLECT_SHIELD_TIMING", ("RS1",), 50,
                 "「リフレクトシールド」の「おもて」の「相手に20ダメージを与え」を、ダメージを受けるときにすぐ与えるか、そのワザのダメージの要素のあとに与えるかは、"
                 "日本語の文面・kyuura の記録から決められない。コインのあとにダメージを与えたポケモンのダメージが変わる（同じワザの自分へのダメージなど）と、"
                 "どちらの時点かで結果（きぜつ・返す効果の対象）が変わりうる"),
        # v0.84（docs/light-powers-evolution-v0.84.md 2 章の A2）: ゆびをふる・ちょうのうりょくなどで、ほかのワザの効果を 1 匹に重ねたとき
        Question("reflect_shield_overlap", "UNRESOLVED_REFLECT_SHIELD_OVERLAP", ("RF1",), 50,
                 "「リフレクトシールド」と、ダメージを受けるときにコインで受けないと決める効果（「かげぶんしん」・「とうめい」）が、同じポケモンが受ける 1 つのダメージに"
                 "はたらくとき、どちらのコインを先に投げるか（先の「うら」・「おもて」であとのコインを投げるか、20 を返すか）は、日本語の文面・kyuura の記録から決められない"),
        # v0.95（docs/private-looks-deck-movement-v0.95.md 5 章）: 山札の上からトラッシュしたカードの中の「「X」エネルギーカード」を数える・手札に加えるワザ（マグマふんしゅつ・
        # マグマラッシュ・やまくずし）で、山札・サイドにレインボーエネルギーがあるとき。v0.73 の熱血!の FV1 と同じ問い（同じコード）
        Question("milled_rainbow_energy", "UNRESOLVED_FERVOR_RAINBOW_ENERGY", ("FV1",), 10,
                 "山札の上からトラッシュしたレインボーエネルギー（場の外の特殊エネルギーカード）が、説明の「「X」エネルギーカード」に当たるか（数える・手札に加えるか）は、"
                 "印刷の文面・kyuura の記録で決まらない（v0.73 の熱血!と同じ問い。トラッシュするまで山札の上のカードは分からないので、山札・サイドにレインボーエネルギーがあるとき、"
                 "宣言の前に止める）"),
        Question("attack_deck_top_short", "UNRESOLVED_ATTACK_DECK_TOP_SHORT", ("LT1",), 10,
                 "「山札の上からカードを3枚見る」ワザ（ひかるミュウの「フラッシュサーチ」・やさしいゴルダックの「みずかき」）で、見るプレイヤーの山札が 3 枚より"
                 "少ないとき（あるだけ見るか）は、日本語の文面・kyuura の記録から決められない（トレーナーの TOP1・ML1・MW1 と同じ形の、別のカードの問い）"),
        Question("energy_drain_decision", "UNSUPPORTED_ENERGY_DRAIN_DECISION", ("v0.68",), 10,
                 "［だつりょくえき］のトラッシュするカードの決定を、v0.13 の約束で書いたワザの実装の中では出せない（エンジンの未対応）"),
        # v0.81（docs/pokemon-tools-stadiums-v0.81.md 5 章）: きあいのハチマキのコインを投げる時点（残りHPがなくなったすぐあとか、きぜつの判定の時か）で結果が変わる場合
        Question("focus_band_timing", "UNRESOLVED_FOCUS_BAND_TIMING", ("FB1",), 10,
                 "きあいのハチマキの「相手のワザによるダメージで、…残りHPがなくなったとき、コインを投げる」を、残りHPがなくなったすぐあとに処理するか、ワザの処理のあとのきぜつの"
                 "判定の時に処理するかは、印刷の文面・kyuura の記録から決められず、同じワザのあとの処理がこのポケモンにダメージ・効果を与えるかで結果が変わる"),
        # v0.86（docs/entry-energy-evolution-reactions-v0.86.md 8 章）
        Question("bolt_during_own_attack", "UNRESOLVED_BOLT_DURING_OWN_ATTACK", ("BT1",), 10,
                 "エンテイの［はしりさる］が、エンテイの持ち主のワザの処理の中で受けた相手の返す効果のワザによるダメージではたらき、ワザを使っているエンテイ自身をワザの途中で"
                 "山札にもどすとき、そのワザの残りの処理と番の終わりをどうするかは、印刷の文面・kyuura の記録から決められない（v0.65 の FL1 と同じ場面の、自動的にはたらく"
                 "特殊能力の問い）"),
        Question("protective_flame_scope", "UNRESOLVED_PROTECTIVE_FLAME_SCOPE", ("PL1",), 10,
                 "エンテイの「ほのおのまもり」の「次の相手の番が終わるまで、自分の控えポケモン全員は、ワザによるダメージや効果を受けない」が、効果を与えたときの控えポケモン"
                 "（バトル場に出たあとも）か、ワザを受ける時点の控えポケモン（あとから控えになったポケモンも）かは、印刷の文面・kyuura の記録から決められず、当てはめるかで"
                 "結果が変わる"),
        # v0.87（docs/movement-damage-reactions-v0.87.md 9 章）: 場の移動への反応（ワザの途中）。同じ時点の反応の RA1・RA2 は v0.86 と同じコード
        Question("reaction_after_knockout", "UNRESOLVED_REACTION_AFTER_KNOCKOUT", ("RA1",), 10,
                 "同じ時点に起こる反応のうち、先に処理した反応でポケモンが HP 以上になったとき、そのポケモンの「きぜつ」の判定を残りの反応の前にするか後にするかは、"
                 "記録（GR-2000-P325-SAME-TIMING）から決められない"),
        Question("reaction_condition_changed", "UNRESOLVED_REACTION_CONDITION_CHANGED", ("RA2",), 10,
                 "同じ時点に起こる反応のうち、先に処理した反応で場が変わり、あとの反応の特殊能力がはたらくかが事実の時点と変わるとき、どちらの時点の状態で決めるかは、"
                 "記録から決められない"),
        Question("power_damage_prevented", "UNRESOLVED_POWER_DAMAGE_PREVENTED", ("SB1",), 10,
                 "マチスのマルマインの［ショックボム］の特殊能力のダメージを、「ダメージを受けない」状態（「かたまる」など。説明はワザによるダメージを書く）のポケモンが受けるかは、"
                 "印刷の文面・kyuura の記録から決められない（トレーナーのダメージの p.235 の解説の記録は特殊能力のダメージを書かない）"),
        Question("strange_gas_protected", "UNRESOLVED_STRANGE_GAS_PROTECTED_POKEMON", ("MG2",), 10,
                 "ドガースの「ふしぎなガス」の「相手の場にいるポケモン」に、ワザの効果を受けないポケモン（「ワザをうけない」状態・［オーロラヴェール］の控え・エフェクトガード・"
                 "［クリスタルボディ］・「とうめい」など）がいるとき、そのポケモンの特殊能力も止まるのかは、印刷の文面・kyuura の記録から決められない"),
        # v0.92（docs/power-suppression-lasting-locks-v0.92.md 8 章）: ナツメのゲンガーの「やみのはどう」（MG2 とは別のカードの問い。新しく場に出すポケモンの DW1 は登場時のガード）
        Question("dark_wave_protected", "UNRESOLVED_DARK_WAVE_PROTECTED_POKEMON", ("DW2",), 10,
                 "ナツメのゲンガーの「やみのはどう」の「お互いの場にいるすべてのポケモン」に、相手のワザの効果を受けないポケモン（「ワザをうけない」状態・［オーロラヴェール］の控え・"
                 "エフェクトガード・［クリスタルボディ］・「とうめい」など）がいるとき、そのポケモンの特殊能力も止まるのかは、印刷の文面・kyuura の記録から決められない"),
        Question("dark_wave_knocked_out_power", "UNRESOLVED_DARK_WAVE_KNOCKED_OUT_POWER", ("DW3",), 10,
                 "「やみのはどう」で HP 以上になったポケモン（きぜつの判定の前）の、きぜつの判定・きぜつのあとに使える特殊能力（［ファイナルビーム］・ふしちょうなど）も、このワザの"
                 "「お互いの場にいるすべてのポケモン」として止まるのか（処理の対象がいないので受けないのか。p.309）は、印刷の文面・kyuura の記録から決められない（こんじょうは G37）"),
        # v0.93（docs/active-leave-locks-v0.93.md 10 章）: 「バトル場をはなれられない」効果
        Question("leave_locked_coin", "UNRESOLVED_LEAVE_LOCK_NO_EFFECT", ("AL2",), 10,
                 "「バトル場をはなれられない」効果を受けたポケモンをバトル場からはなれさせる部分だけを決めるコインを投げるか（その部分は起こらない）は、印刷の文面・kyuura の記録から"
                 "決められない（投げるかどうかで乱数の続きが変わる。HC3 と同じ形の、別の原因の問い）"),
        Question("leave_lock_knockout", "UNRESOLVED_LEAVE_LOCK_KNOCKOUT", ("AL1",), 40,
                 "きぜつしたときを除くと書いていない「バトル場をはなれられない」効果（からまるいと・ねばるみつ）を受けたポケモンが、きぜつの処理でバトル場をはなれるのかは、"
                 "印刷の文面・kyuura の記録から決められない（ほかのカードの括弧書きを補わない。p.323）"),
        Question("leave_lock_scram", "UNRESOLVED_LEAVE_LOCK_SCRAM", ("AL3",), 90,
                 "［ずらかる］が、「バトル場をはなれられない」効果を受けたポケモンで必ずはたらくとき、もどれないまま効果がなくなったあとにはたらくのかは、印刷の文面・kyuura の記録から"
                 "決められない（SC2 と同じ形の、別の原因の問い）"),
        # v0.94（docs/switch-return-attacks-v0.94.md 7 章）: ワザの効果の入れ替えで、ワザを使っている［へんしん］のメタモンの今の姿が変わる（v0.65 の RX1 と同じ問い）
        Question("attack_switch_transformed_attacker", "UNRESOLVED_REACTIVE_SWITCH_TRANSFORMED_ATTACKER", ("RX1",), 10,
                 "ワザの効果で相手の対戦ポケモンを入れ替えると、ワザを使っている［へんしん］のメタモンの今の姿（相手の対戦ポケモンのカード）が変わり、あとのダメージの要素をどの姿で"
                 "処理するかは、印刷の文面・kyuura の記録から決められない（選べるどの控えでも姿が変わる。v0.65 のワザの途中の入れ替えと同じ問い）"),
        # ルールの問いではなく、エンジンの未対応（コードは UNSUPPORTED_…。研究の対応表の停止コードには入れない）
        Question("energy_reaction_during_attack", "UNSUPPORTED_ENERGY_REACTION_DURING_ATTACK", ("v0.86",), 10,
                 "ワザの効果で手札からエネルギーカードをつけたときにはたらく相手の［かんでん］・つけたポケモンの［いなびかり］を、ワザの処理の途中で処理する続きは"
                 "エンジンが扱わない（エンジンの未対応。［エナジーしんか］はワザの最中の宣言なので PW4）"),
        # 今の写しのワザの並びでは起こらない（コードのない問い。当たったらエンジンの不具合）
        Question("esp_separate_coin_tosses", None, ("ES0",), 10,
                 "ナツメのESPのやり直しのあとに、同じワザの説明文のコイントスをもう一度投げる並びのワザは、今の写しにない（どのワザも説明文のコイントスは 1 回にまとまっている）"),
        # 今の写しのワザの並びでは起こらない（コードのない問い。当たったらエンジンの不具合）
        Question("flee_then_damage", None, ("FL0",), 10,
                 "［にげこむ］で入れ替えたあとに、そのワザの残りのダメージの要素がかわりに出たポケモンに来る並びのワザは、今の写しにない"),
        Question("bench_guard_element", None, ("BG0",), 10,
                 "［ベンチガード］の決定を出せないダメージの要素で、控えポケモンが 10 以上のダメージを受ける（今の写しのワザの要素はどれも出せる）"),
        # v0.100（docs/sketch-perish-song-history-v0.100.md 8 章）
        Question("sketch_presence", "UNRESOLVED_SKETCH_PRESENCE", ("SK1",), 10,
                 "ドーブルの「スケッチ」の「前の相手の番、このカードが場に出ていなければ、このワザは失敗する」が、前の相手の番の途中に場に出たカード・前の相手の番に場にいて、そのあと場を"
                 "はなれて出し直したカード・前の相手の番がない（先攻の最初の番）ときに失敗するかは、印刷の文面・kyuura の記録から決められない（失敗するか、ワザを使うか・何もしないかが変わる）"),
        Question("sketch_copied_attack", "UNRESOLVED_SKETCH_COPIED_ATTACK", ("SK2",), 10,
                 "ドーブルの「スケッチ」の「前の相手の番に、相手のポケモンがワザを使っていたなら、そのワザを」が、相手が使ったワザが相手のワザなどを自分のワザとして使ったもの（宣言したワザと"
                 "処理したワザが違う）のとき、どちらのワザを指すかは、印刷の文面・kyuura の記録から決められない"),
        Question("perish_song_received_attack", "UNRESOLVED_PERISH_SONG_RECEIVED_ATTACK", ("PSG1",), 10,
                 "ムウマの「ほろびのうた」の「前の自分の番に「やみのひとみ」を受けていたなら」が、効果だけを無効にする効果で受けなかった「やみのひとみ」・相手のワザなどを自分のワザとして"
                 "使った「やみのひとみ」（宣言したワザと処理したワザが違う）を受けていたことになるかは、印刷の文面・kyuura の記録から決められない（今ねむりの相手が「きぜつ」するかが変わる）"),
        # ルールの問いではなく、エンジンの持つ情報の不足（コードは UNSUPPORTED_…。研究の対応表の停止コードには入れない）
        Question("turn_history_missing", "UNSUPPORTED_HISTORY_TURN_RECORD_MISSING", ("v0.100",), 10,
                 "前の相手の番のプレイヤーの番ごとの記録（使ったワザ・場にいたカード）がない（v0.99 までの状態の写しなど）。記録がないことを「ワザを使わなかった」「場にいなかった」と読まない"
                 "（エンジンの持つ情報の不足）"),
    )
}


class OpenQuestion(Exception):
    """仕組みの共通の検出が、既知の問い（``QUESTIONS``）に当たった。先読み（``preflight``）が集め、実際の処理では止める。"""

    def __init__(self, key: str, detail: str = "", error: UnsupportedError | None = None):
        if key not in QUESTIONS:
            raise KeyError(f"知らない問い {key!r}（questions.QUESTIONS に加える）")
        super().__init__(f"{key}: {detail}")
        self.key = key
        self.detail = detail
        self.error = error  # v0.13 の部品が作った理由（マヒの再付与）。あればそのまま使う


def to_error(key: str, detail: str = "", error: UnsupportedError | None = None) -> UnsupportedError:
    """問いを ``UnsupportedError`` にする。コードのない問いは ``RuntimeError``（今の対応カードでは起こらないので、エンジンの不具合）。"""
    question = QUESTIONS[key]
    if question.code is None:
        raise RuntimeError(f"今の対応カードでは起こらないはずの問い {key}（{'・'.join(question.rulings)}）: {question.message}。{detail}")
    if error is not None and error.code == question.code:
        return error
    return UnsupportedError(question.code, f"{question.message}（{'・'.join(question.rulings)}。{detail}）")


def pick(keys) -> str:
    """当たった問いのうち、優先度のいちばん高い（数の小さい）もの。同じ優先度なら名前の順（決まった答えにする）。"""
    return min(keys, key=lambda k: (QUESTIONS[k].priority, k))

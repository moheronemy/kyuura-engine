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
- v0.41（``--batch v0.41``。``PAIRINGS_V0_41``。docs/heal-counter-status-v0.41.md）: ``G41``（草）: ナゾノクサ（第2弾）4・クサイハナ 3・マダツボミ 4・ウツドン 3・
  ウツボット 2・エリカのナゾノクサ（PMCG5-002・PMCG5-003）2 枚ずつ・エリカのクサイハナ 3、トレーナー 12、草エネルギー 25。``P41``（超・水）: ナツメのコダック 4・
  ナツメのゴルダック 3・ナツメのヤドン 4・ナツメのヤドラン 3・ロケット団のヤドン 4・R団のミュウツー 3、トレーナー 12、超エネルギー 21・水エネルギー 6。``C41``
  （無色・水）: ニャース 4・わるいペルシアン 3・タッツー 4・シードラ 3・エリカのプリン 4・ラッキー 4、トレーナー 12、水エネルギー 26。``R41``（炎・草・超）: カツラのファイヤー 4・
  ナツメのコンパン 4・ナツメのモルフォン 3、トレーナー 12、炎エネルギー 25・草エネルギー 6・超エネルギー 6。組は ``G41`` 対 ``P41``・``P41`` 対 ``C41``・
  ``C41`` 対 ``R41``・``R41`` 対 ``G41``・``G41`` 対 ``P31``（ピッピ・ピクシー・カスミのコダックが v0.41 のワザを自分のワザとして使う）・``R41`` 対 ``F37``
  （タケシのイワーク（HP 100）。カツラのファイヤーの 90 で HP 以上にならない相手。ほかの相手はほとんど HP 以上になり、ひのとりは RD9 で止まる）。v0.41 のワザの決定は
  ``_v041_decision``（ミラクルかふんは ねむり・マヒ・こんらん・どく を順に、ひなたぼっこは つける・つける・つけない を順に）。原典で決められない場合（CX1・RD9・
  Z23・HC3・HC4）・使うための条件（ゆうわくの ``NO_OPPONENT_BENCH``）・きあいずつきの ``ATTACK_LOCKED`` で拒否されたワザは、場から確かめてから別の操作を続ける
  （``V031_STOPS``）。v0.41 のカードも、使っていないワザのためにエネルギーをためる手順（v0.38 と同じ）を使う。前の版のデッキに v0.41 のカードは入っていない
  ので、その組の結果は変わらない（``P31`` の組の決定・停止の確かめは v0.31 と同じ）。
- v0.43（``--batch v0.43``。``PAIRINGS_V0_43``。docs/declared-entry-powers-v0.43.md）: ``G43``（草）: ナゾノクサ（第2弾・ロケット団）2 枚ずつ・わるいクサイハナ 3・
  ズバット（化石の秘密・ロケット団）2 枚ずつ・わるいゴルバット 3・エリカのマダツボミ（PMCG5-010）4・エリカのウツドン 2、トレーナー 12、草エネルギー 28。``R43``（炎・超）:
  ロケット団のヒトカゲ 4・リザード 2・ロケット団のスリープ 4・わるいスリーパー 2・ロケット団のヤドン 4・わるいヤドラン 3、トレーナー 12、炎エネルギー 15・超エネルギー 14。
  ``L43``（雷・無色）: マチスのコイル（PMCG5-037・PMCG5-039）2 枚ずつ・マチスのレアコイル 3・ロケット団のミニリュウ 4・わるいハクリュー 3・わるいカイリュー 2・
  ポケモン育て屋さん 2、トレーナー 12、雷エネルギー 30。組は ``G43`` 対 ``R43``・``R43`` 対 ``L43``・``L43`` 対 ``G43``・``G43`` 対 ``P31``（ピッピ・ピクシー・
  カスミのコダックが v0.43 のワザを自分のワザとして使う）。v0.43 の宣言する特殊能力は ``_v043_power`` で使い（くさいかふんは相手の対戦ポケモンがこんらんでないとき、
  えんかくさいみんはどちらの対戦ポケモンもねむりでないとき（両方のねむりはポケモンチェックの既知の停止 ``UNRESOLVED_POKEMON_CHECK_SLEEP_COIN_ORDER`` になる）、
  エナジーチャージは番ごとに 1 度だけ試す）、決定は ``_v043_decision`` で答える（場に出たときの特殊能力の使う機会は 4 回に 1 回、使うことを選ぶと止める（PW3）ときは
  いつも使わない。v0.43 の決定は元の手順より先に答える）。v0.43 のカードも、使っていないワザのためにエネルギーをためる手順（v0.38 と同じ）を使う。前の版のデッキに
  v0.43 のカードは入っていないので、その組の結果は変わらない（``P31`` の組の決定・停止の確かめは v0.31 と同じ）。
- v0.44（``--batch v0.44``。``PAIRINGS_V0_44``。docs/search-evolution-once-attacks-v0.44.md）: ``K44``（草・闘）: キョウのビードル 4・キョウのコクーン 3・キョウのスピアー 2・
  エリカのフシギダネ 4・ディグダ（ロケット団）4・カツラのマンキー 4、トレーナー 12、草エネルギー 15・闘エネルギー 12。``V44``（水・闘）: サカキのニャース 4・サカキのペルシアン 3・
  サカキのコイキング 4・サカキのギャラドス 3・サカキのワンリキー 3・サカキのゴーリキー 2・サカキのカイリキー 1・サカキ 4、トレーナー 12、水エネルギー 14・闘エネルギー 10。
  ``W44``（水・超・無色）: カスミのヒトデマン 4・コイキング（ロケット団）4・ギャラドス（第1弾）2・ナツメのバリヤード 4・_____のラッキー 4・カモネギ 3・ニャース（ロケット団）4、
  トレーナー 12、水エネルギー 16・超エネルギー 7。組は ``K44`` 対 ``V44``・``V44`` 対 ``W44``・``W44`` 対 ``K44``・``W44`` 対 ``P31``（ピッピ・ピクシー・カスミのコダックが
  v0.44 のワザを自分のワザとして使う。1 度だけ使えるワザはまねられない）。決定は ``_v044_decision``（元の手順より先に答える）、［うか］は ``_v044_power``、サカキと許可のある
  ポケモンの進化は ``_v044_trainer``（今の番に場に出した・進化したサカキのポケモンと、そのポケモンから進化するカードが手札にあるときだけサカキを使う）。1 度しか使えないワザで
  使ったものは選ばない。原典で決められない場合（FC1・RD9）で拒否されたワザは、場から確かめてから別の操作を続ける（``V031_STOPS``）。前の版のデッキに v0.44 のカードは
  入っていないので、その組の結果は変わらない。
- v0.45（``--batch v0.45``。``PAIRINGS_V0_45``。docs/conditional-damage-energy-v0.45.md）: ``G45``（草・水）: キョウのアーボ 4・キョウのアーボック 3・キョウのベトベター 4・
  カスミのタッツー（PMCG5-024）4・カスミのパウワウ 3・カスミのジュゴン 2、トレーナー 12、草エネルギー 15・水エネルギー 13。``R45``（炎・雷）: カツラのヒトカゲ 4・
  カツラのリザード 3・カツラのリザードン 2・コイル（第1弾）4・わるいレアコイル 3・R団のサンダー 3、トレーナー 12、炎エネルギー 15・雷エネルギー 14。``F45``（闘・無色）:
  イワーク 3・コラッタ 4・ラッタ 3・R団のエビワラー 3・タケシのイシツブテ（PMCG5-047）4・タケシのサイホーン 1・タケシのサンド 1・サカキのニャース（PMCG6-068）3、
  トレーナー 12、闘エネルギー 26。``W45``（水・超）: ゼニガメ（ロケット団）4・わるいカメール 3・わるいカメックス 2・ゴース（第1弾）4・ゴースト（第1弾）3、トレーナー 12、
  水エネルギー 18・超エネルギー 14。組は ``G45`` 対 ``R45``・``R45`` 対 ``F45``・``F45`` 対 ``W45``・``W45`` 対 ``G45``・``G45`` 対 ``P31``（ピッピ・ピクシー・
  カスミのコダックが v0.45 のワザを自分のワザとして使う。クロスカウンターはまねられない）。決定は ``_v045_decision``（じりょくせんは はがすカードの 1 つ目・つける控えの
  最後、たすけをよぶは 4 回に 1 回は出さない）。原典で決められない場合（AC13・AC6・W24）で拒否されたワザは、場から確かめてから別の操作を続ける（``V031_STOPS``）。
  v0.45 のカードも、使っていないワザのためにエネルギーをためる手順（v0.38 と同じ）を使う。前の版のデッキに v0.45 のカードは入っていないので、その組の結果は変わらない。
- v0.46（``--batch v0.46``。``PAIRINGS_V0_46``。docs/continuous-powers-v0.46.md）: ``G46``（草・超）: エリカのフシギダネ 4・エリカのフシギソウ 3・エリカのフシギバナ 2・
  エリカのタマタマ 4・エリカのナッシー 3・ナゾノクサ（第2弾・ロケット団）2 枚ずつ・わるいクサイハナ 3・わるいラフレシア 2、トレーナー 12、草エネルギー 17・超エネルギー 6。
  ``P46``（超・無色）: バリヤード 4・エリカのミニリュウ 4・カビゴン 3・ドードー 4・ドードリオ 3、トレーナー 12、超エネルギー 30。``D46``（闘・草）: マンキー 4・
  わるいオコリザル 3・ベトベター（ロケット団）4・わるいベトベトン 3・ドードー 2・ドードリオ 2、トレーナー 12、闘エネルギー 15・草エネルギー 15。組は ``G46`` 対 ``P46``・
  ``P46`` 対 ``D46``・``D46`` 対 ``G46``・``G46`` 対 ``P31``（ピッピ・ピクシー・カスミのコダックが v0.46 のワザを自分のワザとして使う）。決定は ``_v046_decision``（せいちょうは
  選べるだけ・1 枚 を順に、かくさんソーラービームは控えの最初の 2 匹）。「にげる」のエネルギーの数が常にはたらく特殊能力で変わるときは ``_v046_retreat`` が 1 局に 3 回まで
  「にげる」を宣言する（少なくできるなら少ない数、増えるなら増えた数。少なくしてから 0 で止める読み方と答えが変わる数（CP2）は 1 度だけ試す）。［アレルギーかふん］で
  トレーナーカードを使えない番は、元の手順に手札のトレーナーカードを見せずに選ばせる（``make_policy``）。元の手順が印刷の数で宣言した「にげる」（``WRONG_RETREAT_COST``）・
  CP2・``TRAINER_PREVENTED`` は、場から確かめてから別の操作を続ける（tests/v017_games.py の ``play_game``）。v0.46 のカードも、使っていないワザのためにエネルギーをためる
  手順（v0.38 と同じ）を使う。前の版のデッキに v0.46 のカードは入っていないので、その組の結果は変わらない。
- v0.47（``--batch v0.47``。``PAIRINGS_V0_47``。docs/fossil-hidden-info-v0.47.md）: ``F47``（水・闘・超）: なにかの化石 4・オムナイト 3・オムスター 2・カブト 3・
  カブトプス 2・マンキー（第2弾）4・コラッタ（ロケット団）4・コダック（化石の秘密）4・ピッピ人形 2、トレーナー 12、水エネルギー 7・闘エネルギー 11・超エネルギー 2。
  ``H47``（超・雷）: スリープ 4・スリーパー 3・マチスのイーブイ 4・マチスのサンダース 3・コラッタ（ロケット団）4・コダック（化石の秘密）4・ピッピ人形 2、トレーナー 12、
  超エネルギー 12・雷エネルギー 12。``A47``（闘・雷）: なにかの化石 4・プテラ 3・カブト 2・マンキー（第2弾）4・マチスのイーブイ 4・マチスのサンダース 2・
  コラッタ（ロケット団）4・ピッピ人形 2、トレーナー 12、闘エネルギー 12・雷エネルギー 11。組は ``F47`` 対 ``H47``・``H47`` 対 ``A47``・``A47`` 対 ``F47``・``H47`` 対
  ``P31``（ピッピ・ピクシー・カスミのコダックが、みらいよち・おどろかす・ずつう・こうしゅうはを自分のワザとして使う）。なにかの化石・ピッピ人形は、手札にありベンチに
  空きがあれば場に出し（``_v047_trainer``。トレーナーの使用を禁止された番は 1 度拒否されてから出さない）、バトル場に出ている（ワザのない）なにかの化石・ピッピ人形は
  控えがいればすてる（ベンチのピッピ人形も、番の番号が 7 の倍数の番にすてる）。［スパイ］・［わるふざけ］は使える番に使う（``_v047_power``）。決定は ``_v047_decision``
  （［スパイ］の見る場所・［わるふざけ］のサイドの位置・おどろかすの手札の位置は順に、みらいよちは自分・相手の山札を順に、枚数は 3・1・2 枚を順に（0 枚は選ばない）、
  並びは逆に）。［げんしのちから］で進化できない番（この番に ``EVOLUTION_PREVENTED`` で拒否された）は、元の手順に手札の進化カードを見せずに選ばせる（``make_policy``）。
  バトル場のなにかの化石・ピッピ人形の「にげる」（PF2）・``EVOLUTION_PREVENTED``・``TRAINER_PREVENTED``（期限のある禁止も）は、場から確かめてから別の操作を続ける
  （tests/v017_games.py の ``play_game``）。監査（``audit``）は、受け付けた操作ごとに、プレイヤー・観戦者に渡す観測（``observation_problems``）も確かめる。前の版の
  デッキに v0.47 のカードは入っていないので、その組の結果は変わらない。
- v0.48（``--batch v0.48``。``PAIRINGS_V0_48``。docs/effective-pokemon-properties-v0.48.md）: ``C48``（草・超）: ポリゴン（第1弾）2・ポリゴン（ロケット団）2・
  キョウのメタモン 4・コンパン（第2弾）4・モルフォン 3、トレーナー 12、草エネルギー 19・超エネルギー 14。``S48``（超・草）: ナツメのゴース 4・ナツメのゴースト 3・
  ナツメのゲンガー 3・キョウのメタモン 2・ベトベター（ロケット団）3・ベトベトン（化石の秘密。［かがくへんかガス］）2、トレーナー 12、超エネルギー 25・草エネルギー 6。組は ``C48`` 対
  ``S48``（両方の席）・``C48`` 対 ``P31``・``S48`` 対 ``P31``（ピッピ・ピクシー・カスミのコダックが、v0.48 のワザを自分のワザとして使う）。［へんしょく］は使える番に
  使い（``_v048_power``）、テクスチャー・［へんしょく］の色は ``_v048_decision`` が選べる色を順に選ぶ（原典で決められない色は選ばない）。ベトベトンへの進化で
  ［ガスのからだ］が消えるなど、最大HPがのっているダメージ以下に下がる操作（MH1）と、［ガスのからだ］で最大HPが上がったポケモンの進化で HP がダメージ以下になる操作
  （v0.4a の H1）は、場から確かめてから、その番はそのカードを手順に見せずに別の操作を続ける（tests/v017_games.py の ``play_game``・``make_policy``）。弱点・抵抗力の
  ないポケモンへのテクスチャー（PG1）は ``V031_STOPS`` で場から確かめる。手順は、今有効な最大HP が印刷の HP と違う v0.48 のポケモンのいる盤面を数える
  （``_v048_observe``。``v048_max_hp_<カード>_raised``・``…_over_printed``）。前の版のデッキに v0.48 のカードは入っていないので、その組の結果は変わらない。
- v0.49（``--batch v0.49``。``PAIRINGS_V0_49``。docs/virtual-attacks-transformation-v0.49.md）: ``A49``（超）: ナツメのケーシィ 4・ナツメのユンゲラー 3・
  ナツメのフーディン 3・ルージュラ 2・ケーシィ 3・ユンゲラー 2・思い出させる 4、トレーナー 12、超エネルギー 27。``D49``（炎・無）: タケシのロコン 4・
  タケシのキュウコン 3・メタモン 4・ヒトカゲ 3・リザード 3・思い出させる 3、トレーナー 12、炎エネルギー 28。組は ``A49`` 対 ``D49``（両方の席）・``A49`` 対 ``P31``・
  ``D49`` 対 ``P31``（ピッピ・ピクシー・カスミのコダックが、［サイコリンク］で持つワザ・［へんしん］の今の姿のワザを選ぶ）。手順は、今持つワザ（``available_attacks``）の
  うち出どころが今の姿のいちばん上のカードでないもの（［サイコリンク］・［へんしん］・「ばける」・「思い出させる」）を、払えて止める理由がなければ優先して使い、
  使った回数の少ないものから選ぶ（``_v049_attack``。``UseAttack`` の ``card``）。「ばける」は使える番に使い（のせるカードは選べるものを順に。``_v049_power``・
  ``_v049_decision``）、のせたカードは 4 番ごとにもどす（``RemoveDisguise``。最大HPがダメージ以下に下がるときはもどさない）。「思い出させる」は対戦ポケモンが進化して
  いて、すぐ下のカードのワザを払えるときに使う（``_v049_trainer``）。決められない姿（TF1・TF2・DG1）・MH1 で拒否される決定の答え・操作は、場から確かめてから別の答え・
  操作を続ける（``_v049_answer``・tests/v017_games.py の ``play_game``）。どの答えでも止まる決定は対戦を止める（``halted``）。前の版のデッキに v0.49 のカードは
  入っていないので、その組の結果は変わらない（ワザのログに ``card_id`` が書かれるのは v0.49 の出どころのワザだけ）。

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
    AttachEnergy, EndTurn, EvolvePokemon, IllegalActionError, Phase, PlayTrainer, ResolveDecision, Retreat, UnsupportedError, UseAttack, UsePokemonPower, apply_command,
    UseStadium, check_invariants, max_hp, new_game, preset_deck,
    RevealFaceDown,
)
from kyuura_engine.errors import HiddenPropertyRead  # v0.67
from kyuura_engine.cards import EnergyType, can_pay_cost  # noqa: E402
from kyuura_engine.commands import DiscardFromPlay  # noqa: E402
from kyuura_engine.decisions import (  # noqa: E402
    ARRANGE_DECK_TOP, PEEK_CARD, SELECT_DECK_OWNER, SELECT_HAND_CARD, SELECT_LOOK_COUNT, SELECT_PRIZE_CARD,
    ATTACH_FROM_DECK, ATTACH_FROM_DISCARD, ATTACH_FROM_HAND, BENCH_FROM_DECK, DISCARD_ENERGY, DISCARD_FROM_HAND, DISCARD_TO_DECK_TOP, ENTRY_POWER, FORCED_SWITCH, HAND_TO_DECK,
    MOVE_ENERGY, MOVE_OPPONENT_ENERGY, RECOVER_POKEMON, ATTACH_TO_BENCH, OPTIONAL_DRAIN,
    REMOVE_COUNTERS, RETURN_ENERGY, SEARCH_DECK, SELECT_ATTACK, SELECT_COLOR, SELECT_EVOLUTION_CARD, SELECT_POKEMON, SELECT_SPECIAL_CONDITION,
)
from kyuura_engine.effects import (  # noqa: E402
    AttackKey as E_AttackKey, AttackUse, preview_attack_damage, retreat_cost, working_counterattack_power, working_evasion_power,
)
from kyuura_engine.effects import COLORS, resistance_of, shift_color_options, type_readings, weakness_of  # noqa: E402  v0.48
from kyuura_engine.resolution.programs import compile_attack  # noqa: E402
from kyuura_engine.persistent import (  # noqa: E402
    attack_barrier, attack_coin_checks, attack_locked, cannot_attack, cannot_attack_while_source_active, cannot_retreat, destiny_bond,
    reduced_damage_to_source, retaliation,
)
from kyuura_engine.effects import trainer_use_blockers  # noqa: E402
from kyuura_engine.commands import PromoteActive, RemoveDisguise, TakePrize  # noqa: E402  v0.49
from kyuura_engine.effects import PowerKey as E_PowerKey  # noqa: E402  v0.49
from kyuura_engine.effects import (  # noqa: E402  v0.49
    any_color_energy, attack_cost_payable, available_attacks, current_form, find_attack_option, recall_records, shapeshift_choices,
)
from kyuura_engine.decisions import SELECT_DEVOLVE_COUNT  # noqa: E402  v0.50
from kyuura_engine.effects import devolution_candidates, devolution_forbidden  # noqa: E402  v0.50
from kyuura_engine.stadiums import bench_limit  # v0.57
from kyuura_engine.decisions import USE_DISCARD_TRAINER  # v0.58
from kyuura_engine.decisions import SELECT_OPPONENT_ATTACK  # v0.76
from kyuura_engine.continuous import goop_gas_effects  # v0.59
from kyuura_engine.effects import blaine_effects  # v0.59
from kyuura_engine.effects import DamageThenCoinPerOpponentBench, attack_rebellion_powers, evasion_power  # v0.60
from kyuura_engine.persistent import tails_damage_guard  # v0.60
from kyuura_engine.decisions import KNOCK_OUT_POWER  # v0.61
from kyuura_engine.effects import energy_unit_count  # v0.61
from kyuura_engine.effects import LASTING_RECEIVED_ELEMENTS, REFLECTABLE_RECEIVED_ELEMENTS, used_attack_last_turn  # v0.62
from kyuura_engine.history import other_received_on, received_on  # v0.62
from kyuura_engine.decisions import BENCH_FROM_DISCARD  # noqa: E402  v0.51
from kyuura_engine.effects import bench_from_discard_candidates, trainer_attack_damage_bonuses, trainer_poison_effects  # noqa: E402  v0.51・v0.56
from kyuura_engine.resolution.programs import all_answers  # noqa: E402  v0.49
from tests.log_audit import log_problems, observation_problems, serialization_problems  # noqa: E402
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
# v0.41（回復・ダメージカウンターの移動・特殊状態の変化を中心とする 15 枚。docs/heal-counter-status-v0.41.md）。進化元はナゾノクサ（第2弾）・ウツドン（v0.32）・
# タッツー（v0.36）・ニャース（v0.37）・エリカのナゾノクサ・ナツメのコダック・ナツメのコンパン（v0.33）・ナツメのヤドン（v0.18c）
GLOOM, VICTREEBEL, SEADRA, DARK_PERSIAN, BLAINES_MOLTRES = "PMCG2-009", "PMCG2-016", "PMCG3-020", "PMCG4-048", "PMCG6-035"
ROCKET_SLOWPOKE, ERIKAS_ODDISH, ERIKAS_ODDISH_40, ERIKAS_GLOOM, SABRINAS_PSYDUCK = "PMCG4-032", "PMCG5-002", "PMCG5-003", "PMCG5-009", "PMCG6-036"
SABRINAS_GOLDUCK, SABRINAS_VENOMOTH, SABRINAS_SLOWBRO, ERIKAS_JIGGLYPUFF, ROCKETS_MEWTWO = "PMCG6-038", "PMCG6-022", "PMCG6-048", "PMCG5-058", "PMCG6-055"
V0_41 = (GLOOM, VICTREEBEL, SEADRA, DARK_PERSIAN, BLAINES_MOLTRES, ROCKET_SLOWPOKE, ERIKAS_ODDISH, ERIKAS_ODDISH_40, ERIKAS_GLOOM, SABRINAS_PSYDUCK,
         SABRINAS_GOLDUCK, SABRINAS_VENOMOTH, SABRINAS_SLOWBRO, ERIKAS_JIGGLYPUFF, ROCKETS_MEWTWO)
SABRINAS_SLOWPOKE = "PMCG6-044"
# v0.42（回復・カウンター操作と、特殊能力を持つ進化系統を中心とする 15 枚。docs/power-decisions-v0.42.md）。進化元はクサイハナ（v0.41）・ヤドン（化石の秘密）・
# ゴースト（化石の秘密。v0.9）・エリカのクサイハナ（v0.41）・ハクリュー（v0.33）・エリカのウツドン（v0.40）・ケーシィ（第1弾）
SABRINAS_JYNX, VILEPLUME, SLOWBRO, GENGAR, ERIKAS_VILEPLUME = "PMCG6-052", "PMCG2-014", "PMCG3-028", "PMCG3-031", "PMCG5-014"
SABRINAS_ABRA, SABRINAS_KADABRA, DRAGONITE, ERIKAS_VICTREEBEL, DARK_KADABRA = "PMCG6-043", "PMCG6-047", "PMCG3-043", "PMCG5-015", "PMCG4-034"
DARK_ALAKAZAM, TENTACOOL, TENTACRUEL, ERIKAS_CLEFAIRY, ERIKAS_CLEFABLE = "PMCG4-035", "PMCG3-011", "PMCG3-017", "PMCG5-060", "PMCG5-065"
V0_42 = (SABRINAS_JYNX, VILEPLUME, SLOWBRO, GENGAR, ERIKAS_VILEPLUME, SABRINAS_ABRA, SABRINAS_KADABRA, DRAGONITE, ERIKAS_VICTREEBEL, DARK_KADABRA,
         DARK_ALAKAZAM, TENTACOOL, TENTACRUEL, ERIKAS_CLEFAIRY, ERIKAS_CLEFABLE)
ABRA, GASTLY, HAUNTER = "PMCG1-043", "PMCG3-029", "PMCG3-030"
# v0.43（宣言して使う特殊能力・場に出たときに使う特殊能力を持つ 9 枚。docs/declared-entry-powers-v0.43.md）。進化元はナゾノクサ（第2弾・ロケット団）・ズバット（化石の秘密・
# ロケット団）・ヤドン（ロケット団）・ミニリュウ（ロケット団）・マチスのコイル（v0.29・v0.33）
DARK_GLOOM, ROCKET_DROWZEE, ROCKET_CHARMANDER, ERIKAS_BELLSPROUT_40, LT_SURGES_MAGNETON = "PMCG4-006", "PMCG4-033", "PMCG4-012", "PMCG5-010", "PMCG5-040"
DARK_DRAGONAIR, DARK_GOLBAT, DARK_SLOWBRO, DARK_DRAGONITE = "PMCG4-052", "PMCG4-009", "PMCG4-036", "PMCG4-053"
V0_43 = (DARK_GLOOM, ROCKET_DROWZEE, ROCKET_CHARMANDER, ERIKAS_BELLSPROUT_40, LT_SURGES_MAGNETON, DARK_DRAGONAIR, DARK_GOLBAT, DARK_SLOWBRO, DARK_DRAGONITE)
# v0.44（検索・進化・1 度だけ使えるワザの 14 枚。docs/search-evolution-once-attacks-v0.44.md）。トレーナーのサカキは TARGETS に入れない（ワザがない）
ROCKET_DIGLETT, ROCKET_MEOWTH, ERIKAS_BULBASAUR, MISTYS_STARYU, ROCKET_MAGIKARP = "PMCG4-038", "PMCG4-047", "PMCG5-007", "PMCG5-027", "PMCG4-020"
KOGAS_KAKUNA, KOGAS_BEEDRILL, FARFETCHD, GIOVANNIS_MAGIKARP, GIOVANNIS_GYARADOS = "PMCG6-011", "PMCG6-018", "PMCG1-063", "PMCG6-037", "PMCG6-040"
SABRINAS_MR_MIME, BLAINES_MANKEY, BLANK_CHANSEY, GIOVANNIS_PERSIAN = "PMCG6-046", "PMCG6-056", "PMCG6-075", "PMCG6-071"
V0_44 = (ROCKET_DIGLETT, ROCKET_MEOWTH, ERIKAS_BULBASAUR, MISTYS_STARYU, ROCKET_MAGIKARP, KOGAS_KAKUNA, KOGAS_BEEDRILL, FARFETCHD, GIOVANNIS_MAGIKARP,
         GIOVANNIS_GYARADOS, SABRINAS_MR_MIME, BLAINES_MANKEY, BLANK_CHANSEY, GIOVANNIS_PERSIAN)
GIOVANNI = "PMCG6-095"
GIOVANNIS_MEOWTH, GIOVANNIS_MACHOP, GIOVANNIS_MACHOKE, GIOVANNIS_MACHAMP = "PMCG6-063", "PMCG6-057", "PMCG6-059", "PMCG6-061"
# v0.45（条件つきのダメージ・エネルギーの移動とトラッシュ・受けたダメージを返す効果などの 15 枚。docs/conditional-damage-energy-v0.45.md）。進化元はゴース（第1弾）・
# カスミのパウワウ（v0.36）・キョウのアーボ・わるいカメール（v0.13）・コイル（第1弾）・カツラのリザード（v0.31）・コラッタ（第1弾）
BASE_HAUNTER, MISTYS_HORSEA_50, MISTYS_DEWGONG, KOGAS_EKANS, KOGAS_ARBOK = "PMCG1-047", "PMCG5-024", "PMCG5-031", "PMCG6-002", "PMCG6-019"
KOGAS_GRIMER, DARK_BLASTOISE, DARK_MAGNETON, BLAINES_CHARIZARD, ROCKETS_ZAPDOS = "PMCG6-007", "PMCG4-024", "PMCG4-030", "PMCG6-032", "PMCG6-042"
ONIX, RATICATE, ROCKETS_HITMONCHAN, BROCKS_GEODUDE_40, GIOVANNIS_MEOWTH_40 = "PMCG1-054", "PMCG1-062", "PMCG5-054", "PMCG5-047", "PMCG6-068"
V0_45 = (BASE_HAUNTER, MISTYS_HORSEA_50, MISTYS_DEWGONG, KOGAS_EKANS, KOGAS_ARBOK, KOGAS_GRIMER, DARK_BLASTOISE, DARK_MAGNETON, BLAINES_CHARIZARD,
         ROCKETS_ZAPDOS, ONIX, RATICATE, ROCKETS_HITMONCHAN, BROCKS_GEODUDE_40, GIOVANNIS_MEOWTH_40)
BASE_GASTLY, ROCKET_SQUIRTLE, DARK_WARTORTLE = "PMCG1-044", "PMCG4-018", "PMCG4-021"
MR_MIME, ERIKAS_DRATINI, ERIKAS_IVYSAUR, DARK_PRIMEAPE, DODRIO, DARK_MUK = "PMCG2-027", "PMCG5-063", "PMCG6-010", "PMCG4-041", "PMCG2-040", "PMCG4-007"
DARK_VILEPLUME, SNORLAX, ERIKAS_VENUSAUR, ERIKAS_EXEGGCUTE, ERIKAS_EXEGGUTOR = "PMCG4-010", "PMCG2-047", "PMCG6-017", "PMCG5-012", "PMCG5-013"
V0_46 = (MR_MIME, ERIKAS_DRATINI, ERIKAS_IVYSAUR, DARK_PRIMEAPE, DODRIO, DARK_MUK, DARK_VILEPLUME, SNORLAX, ERIKAS_VENUSAUR, ERIKAS_EXEGGCUTE, ERIKAS_EXEGGUTOR)
DODUO, GRIMER = "PMCG1-061", "PMCG4-004"
# v0.47（docs/fossil-hidden-info-v0.47.md）
MYSTERIOUS_FOSSIL, CLEFAIRY_DOLL = "PMCG3-046", "PMCG1-091"
OMANYTE, OMASTAR, KABUTO, KABUTOPS, AERODACTYL = "PMCG3-015", "PMCG3-021", "PMCG3-035", "PMCG3-040", "PMCG3-041"
JUNGLE_MANKEY, ROCKET_RATTATA, HYPNO, LT_SURGES_EEVEE, LT_SURGES_JOLTEON, FOSSIL_PSYDUCK = (
    "PMCG2-028", "PMCG4-045", "PMCG3-032", "PMCG5-062", "PMCG5-042", "PMCG3-010")
V0_47 = (OMANYTE, OMASTAR, KABUTO, KABUTOPS, AERODACTYL, JUNGLE_MANKEY, ROCKET_RATTATA, HYPNO, LT_SURGES_EEVEE, LT_SURGES_JOLTEON, FOSSIL_PSYDUCK)
V0_47_TRAINERS = (MYSTERIOUS_FOSSIL, CLEFAIRY_DOLL)
# v0.48（docs/effective-pokemon-properties-v0.48.md）。進化元はコンパン（第2弾。v0.32）。かがくへんかガスはベトベトン（化石の秘密。v0.8）
PORYGON, ROCKET_PORYGON, VENOMOTH, KOGAS_DITTO = "PMCG1-064", "PMCG4-050", "PMCG2-015", "PMCG6-072"
SABRINAS_GASTLY, SABRINAS_HAUNTER, SABRINAS_GENGAR = "PMCG6-049", "PMCG6-050", "PMCG6-054"
V0_48 = (PORYGON, ROCKET_PORYGON, VENOMOTH, SABRINAS_GASTLY, SABRINAS_HAUNTER, SABRINAS_GENGAR, KOGAS_DITTO)
MUK = "PMCG3-007"
# v0.49（docs/virtual-attacks-transformation-v0.49.md）。進化元はナツメのケーシィ・ナツメのユンゲラー（v0.42）・タケシのロコン（v0.36）
SABRINAS_ALAKAZAM, DITTO, BROCKS_NINETALES, RECALL = "PMCG6-053", "PMCG3-042", "PMCG5-019", "PMCG5-071"
V0_49 = (SABRINAS_ALAKAZAM, DITTO, BROCKS_NINETALES)
V0_49_TRAINERS = (RECALL,)
KADABRA = "PMCG1-046"  # ユンゲラー（第1弾。ケーシィから進化。「思い出させる」でケーシィの「ねんりき」を使う）
# v0.50（docs/mew-devolution-spray-v0.50.md）。退化させる進化ポケモンは、第1弾のケーシィ・ユンゲラー・化石の秘密のゴースの系統・キョウのビードルの系統（［うか］）・
# 第1弾のフシギダネの系統（ポケモン育て屋さんで 1 進化を飛ばした重なり）
MEW, DEVOLUTION_SPRAY = "PMCG3-033", "PMCG1-086"
V0_50 = (MEW,)
V0_50_TRAINERS = (DEVOLUTION_SPRAY,)
BULBASAUR, IVYSAUR, VENUSAUR = "PMCG1-001", "PMCG1-008", "PMCG1-011"
# v0.51（docs/discard-to-bench-v0.51.md）。トラッシュのたねポケモンを持ち主のベンチに出す（よみがえらせる・元気のかけら・ポケモンの笛）
SABRINAS_DROWZEE, SABRINAS_HYPNO, REVIVE, POKEMON_FLUTE = "PMCG6-045", "PMCG6-051", "PMCG1-078", "PMCG1-084"
V0_51 = (SABRINAS_HYPNO,)
V0_51_TRAINERS = (REVIVE, POKEMON_FLUTE)
# v0.52（docs/field-return-v0.52.md）。場のポケモンを場から手札・山札にもどす（フジろうじん・ポケモン回収・つれさる）。進化元はエリカのミニリュウ（v0.46）
MR_FUJI, SCOOP_UP, ERIKAS_DRAGONAIR = "PMCG3-048", "PMCG1-092", "PMCG5-066"
V0_52 = (ERIKAS_DRAGONAIR,)
V0_52_TRAINERS = (MR_FUJI, SCOOP_UP)
# v0.53（docs/search-retrieval-trainers-v0.53.md）。山札・トラッシュからカードを選ぶトレーナー 10 枚
ENERGY_SEARCH, POKE_BALL, BOSS_WAY, BROCK_TRAINING, MISTYS_TEARS = "PMCG3-044", "PMCG2-048", "PMCG4-060", "PMCG5-077", "PMCG5-069"
ERIKAS_MAIDS, MAINTENANCE, ITEM_FINDER, RECYCLE, NIGHTLY_GARBAGE_RUN = "PMCG5-072", "PMCG1-085", "PMCG1-087", "PMCG3-047", "PMCG4-057"
V0_53_TRAINERS = (ENERGY_SEARCH, POKE_BALL, BOSS_WAY, BROCK_TRAINING, MISTYS_TEARS, ERIKAS_MAIDS, MAINTENANCE, ITEM_FINDER, RECYCLE,
                  NIGHTLY_GARBAGE_RUN)
DARK_GOLBAT_53 = "PMCG4-009"  # わるいゴルバット（ロケット団のズバットから進化。ボスのやりかたで選べる「わるい」進化カード）
# v0.54（docs/hand-deck-trainers-v0.54.md）。手札の入れ替え・ドロー・情報の確認のトレーナー 10 枚
IMPOSTER_OAK, IMPOSTER_OAKS_REVENGE, GAMBLER, SABRINAS_GAZE, BLAINES_LAST_RESORT = "PMCG1-089", "PMCG4-059", "PMCG3-045", "PMCG6-078", "PMCG6-081"
ERIKA, SECRET_MISSION, BLAINES_GAMBLE, LASS, POKEDEX = "PMCG5-083", "PMCG5-088", "PMCG6-076", "PMCG1-095", "PMCG1-082"
V0_54_TRAINERS = (IMPOSTER_OAK, IMPOSTER_OAKS_REVENGE, GAMBLER, SABRINAS_GAZE, BLAINES_LAST_RESORT, ERIKA, SECRET_MISSION, BLAINES_GAMBLE, LASS, POKEDEX)
# v0.55（docs/instant-trainers-v0.55.md）。すぐに使い終わるトレーナー 16 枚
MISTYS_WRATH, ROCKETS_SNEAK_ATTACK, GOOD_MANNERS, TRASH_EXCHANGE = "PMCG5-075", "PMCG4-061", "PMCG5-082", "PMCG6-077"
ENERGY_REMOVAL, SUPER_ENERGY_REMOVAL, SUPER_POTION, FULL_HEAL = "PMCG1-070", "PMCG1-088", "PMCG1-075", "PMCG1-080"
POKEMON_CENTER, SLEEP_TRAINER, ENERGY_FLOW, ERIKAS_KINDNESS = "PMCG1-083", "PMCG4-054", "PMCG5-067", "PMCG5-084"
BROCK_TRAINER, GIOVANNIS_LAST_RESORT, SABRINA_TRAINER, WARP_POINT = "PMCG5-089", "PMCG6-096", "PMCG6-098", "PMCG6-080"
V0_55_TRAINERS = (MISTYS_WRATH, ROCKETS_SNEAK_ATTACK, GOOD_MANNERS, TRASH_EXCHANGE, ENERGY_REMOVAL, SUPER_ENERGY_REMOVAL, SUPER_POTION, FULL_HEAL,
                  POKEMON_CENTER, SLEEP_TRAINER, ENERGY_FLOW, ERIKAS_KINDNESS, BROCK_TRAINER, GIOVANNIS_LAST_RESORT, SABRINA_TRAINER, WARP_POINT)
# v0.56（docs/trainer-decisions-turn-effects-v0.56.md）。相手の決定・番の終わり・期限のある効果のトレーナー 10 枚
ERIKAS_PERFUME, LT_SURGE_TRAINER, ROCKETS_TRAP, ROCKET_GRUNT, LT_SURGES_TREATY = "PMCG5-073", "PMCG5-092", "PMCG5-096", "PMCG6-089", "PMCG5-081"
MISTYS_WISH, MISTY_TRAINER, KOGA_TRAINER, INVISIBLE_WALL, ROCKETS_EXPERIMENT = "PMCG5-086", "PMCG5-085", "PMCG6-094", "PMCG6-079", "PMCG6-091"
V0_56_TRAINERS = (ERIKAS_PERFUME, LT_SURGE_TRAINER, ROCKETS_TRAP, ROCKET_GRUNT, LT_SURGES_TREATY, MISTYS_WISH, MISTY_TRAINER, KOGA_TRAINER,
                  INVISIBLE_WALL, ROCKETS_EXPERIMENT)
# 決められない姿・MH1 で拒否される操作のコード（v0.49。場から確かめてから別の操作を続ける）
V049_FORM_STOPS = ("UNRESOLVED_TRANSFORM_COPIED_POWER", "UNRESOLVED_TRANSFORM_MODIFIED_DEFENDER", "UNRESOLVED_SHAPESHIFT_SUPPRESSED",
                   "UNRESOLVED_MAX_HP_DROP")
# v0.70（docs/non-pack-effect-reuse-v0.70.md）: 拡張パック以外の商品のポケモン 82 枚（写しの組 pool_v0_70。既存の効果の型の登録と、ダメージのない型 2 つ）。TARGETS に加え、
# 使っていないワザを選ぶ手順・エネルギーをためる手順を重ねる（v0.70 のカードのないデッキでは何もしない）
V0_70 = tuple(__import__("kyuura_engine.cards", fromlist=["read_extract"]).read_extract()["pool_v0_70"])
# v0.72（docs/status-coins-effect-reuse-v0.72.md）: 拡張パック以外の商品のポケモン 43 枚（写しの組 pool_v0_72）。v0.70 と同じく TARGETS に加え、使っていないワザを選ぶ手順・
# エネルギーをためる手順を重ねる。ワザの決定（きゅうけつの取りのぞくか・デンキとばし・おつきみ）は ``_v072_decision``
V0_72 = tuple(__import__("kyuura_engine.cards", fromlist=["read_extract"]).read_extract()["pool_v0_72"])
# v0.73（docs/search-recovery-trainers-v0.73.md）: 拡張パック以外の商品の、検索・回収・ドローのトレーナー 18 枚（写しの組 pool_v0_73）。受け付けるなら使う手順 ``_v073_trainer``、
# 決定への答え ``_v073_decision``（相手の決定にも答える）。パソコン大暴走！は番を終えるので、手順がもう番を終えるところ（``EndTurn``）でだけ使う
V0_73 = tuple(__import__("kyuura_engine.cards", fromlist=["read_extract"]).read_extract()["pool_v0_73"])
# v0.74（docs/remaining-stadiums-v0.74.md）: 拡張パック以外の商品のスタジアム 13 枚（写しの組 pool_v0_74）。手札のスタジアムを出す手順 ``_v074_trainer``、場のスタジアムを使う手順
# ``_v074_stadium``、決定への答え ``_v074_decision``。ポケモンタワーの下で使うと止まる・消えるトレーナー（エネルギー回収・ダウジングマシーン）も ``_v074_trainer`` が試す
V0_74 = tuple(__import__("kyuura_engine.cards", fromlist=["read_extract"]).read_extract()["pool_v0_74"])
V0_74_TOWER, V0_74_NINJA, V0_74_ENERGY = "ES3-036", "PR1-067", "NIP1X-009"
V0_74_RECOVERY = ("PMCG1-076", "PMCG1-087")  # エネルギー回収・ダウジングマシーン（ポケモンタワーでは PT1）
# v0.75（docs/search-energy-pokemon-v0.75.md）: 拡張パック以外の商品のポケモン 15 枚（写しの組 pool_v0_75）。v0.72 と同じく TARGETS に加え、使っていないワザを選ぶ手順・
# エネルギーをためる手順を重ねる。ワザの決定（くらげのむれ・しおまねき・じゅうでん・エネルギーきゅうしゅう・たすけをよぶなど）は ``_v075_decision``
V0_75 = tuple(__import__("kyuura_engine.cards", fromlist=["read_extract"]).read_extract()["pool_v0_75"])
# v0.76（docs/persistent-attack-modifiers-v0.76.md）: 拡張パック以外の商品の、持続する効果・ワザの使用の制限を中心とするポケモン 24 枚（写しの組 pool_v0_76）。v0.75 と同じく TARGETS に
# 加え、使っていないワザを選ぶ手順・エネルギーをためる手順を重ねる。ドわすれ・かなしばりの決定（SELECT_OPPONENT_ATTACK）は ``_v076_decision``
V0_76 = tuple(__import__("kyuura_engine.cards", fromlist=["read_extract"]).read_extract()["pool_v0_76"])
# v0.77（docs/neo-existing-effects-v0.77.md）: neo 期の拡張パック（neo1〜neo4）の、既存の効果の型で表せるカード 52 枚（写しの組 pool_v0_77）。ポケモン 50 枚は v0.76 と同じく TARGETS に
# 加え、使っていないワザを選ぶ手順・エネルギーをためる手順を重ねる。ドわすれの決定は ``_v076_decision``、2 枚のトレーナー（v0.73 と同じ型）は ``_v073_trainer``・``_v073_decision`` で使う
V0_77 = tuple(__import__("kyuura_engine.cards", fromlist=["read_extract"]).read_extract()["pool_v0_77"])
V0_77_TRAINERS = ("neo1-083", "neo1-084")  # スーパーポケモン回収・マサキの転送装置
V0_77_POKEMON = tuple(card for card in V0_77 if card not in V0_77_TRAINERS)
# v0.78（docs/darkness-metal-energy-v0.78.md）: 悪・鋼エネルギー 5 枚と、「悪」「鋼」エネルギーを使うポケモン 8 枚（写しの組 pool_v0_78）。ポケモンは v0.77 と同じく TARGETS に加え、
# 使っていないワザを選ぶ手順を重ねる（悪・鋼エネルギーは同じ名前 4 枚までで足りなくなりやすく、エネルギーをためる手順（v038_wait）を重ねると対戦が進まないので
# 重ねない）。特殊エネルギーは ``_v078_energy`` がつける（元の手順は基本エネルギーだけをつける）
V0_78 = tuple(__import__("kyuura_engine.cards", fromlist=["read_extract"]).read_extract()["pool_v0_78"])
V0_78_ENERGIES = ("neo1-094", "neo1-095", "NIP1X-010", "NIP2X-010", "PRN-002")
V0_78_POKEMON = tuple(card for card in V0_78 if card not in V0_78_ENERGIES)
# v0.79（docs/shared-checks-pokemon-reuse-v0.79.md）: ポケモン 52 枚（写しの組 pool_v0_79）。v0.77 と同じく TARGETS に加え、使っていないワザを選ぶ手順を重ねる。ワザの決定
# （ファイヤーテールのトラッシュ・かげからおそうの控え・ひらめくの山札）は元の手順と ``_v079_decision``（ひらめくは 1 枚を選ぶ）
V0_79 = tuple(__import__("kyuura_engine.cards", fromlist=["read_extract"]).read_extract()["pool_v0_79"])
# v0.80（docs/neo-trainer-components-v0.80.md）: トレーナー 30 枚（スタジアム 4 枚を含む。写しの組 pool_v0_80）。受け付けるなら使う手順 ``_v080_trainer``（スタジアムは場のスタジアムと
# 名前が違えば出す）、場の v0.80 のスタジアムを使う手順 ``_v080_stadium``、決定への答え ``_v080_decision``（相手の決定にも答える）、ログから数える ``v080_uses``
V0_80 = tuple(__import__("kyuura_engine.cards", fromlist=["read_extract"]).read_extract()["pool_v0_80"])
V0_80_STADIUMS = ("neo3-054", "neo4-101", "neo4-106", "neo4-112")
# v0.81（docs/pokemon-tools-stadiums-v0.81.md）: ポケモンのどうぐ 11 枚・ピントレンズ・常にはたらくスタジアム 3 枚（写しの組 pool_v0_81）。受け付けるなら使う手順 ``_v081_trainer``（どうぐは
# つけるポケモンを ``_v081_decision`` が回して選ぶ。スタジアムは場のスタジアムと名前が違えば出す）、学習装置の決定（相手の決定）への答え ``_v081_decision``、ログから数える ``v081_uses``
V0_81 = tuple(__import__("kyuura_engine.cards", fromlist=["read_extract"]).read_extract()["pool_v0_81"])
V0_81_STADIUMS = ("neo1-085", "neo3-057", "neo4-110")
# v0.82（docs/energy-discard-return-v0.82.md）: リサイクルエネルギー・エコロジムと、エネルギーカードをトラッシュするワザを持つポケモン 18 枚（写しの組 pool_v0_82）。ポケモンは TARGETS に
# 加え、使っていないワザを選ぶ手順・エネルギーをためる手順を重ねる（払えるかはエンジンの支払いの問い合わせ。リサイクルエネルギーは state.energy_types で数えない）。リサイクル
# エネルギーは ``_v082_energy`` がつけ、エコロジムは ``_v082_trainer`` が出し、ワザの決定は ``_v082_decision`` が答える。ログから数えるのは ``v082_uses``
V0_82 = tuple(__import__("kyuura_engine.cards", fromlist=["read_extract"]).read_extract()["pool_v0_82"])
V0_82_POKEMON = V0_82[2:]
V0_82_TRAINERS = ("neo1-086",)
RECYCLE_ENERGY = "neo1-096"
TARGETS = (V0_28 + V0_29 + V0_30 + V0_31 + V0_32 + V0_33 + V0_34 + V0_35 + V0_36 + V0_37 + V0_38 + V0_39 + V0_40 + V0_41 + V0_42 + V0_43
           + V0_44 + V0_45 + V0_46 + V0_47 + V0_48 + V0_49 + V0_50 + V0_51 + V0_52
           + ("PMCG5-052", "PMCG5-053")  # ワザの選び方を重ね、動きを数えるカード（v0.58: タケシのゴローン・ゴローニャ）
           + ("PMCG1-040", "PMCG5-030", "PMCG4-008")  # v0.59: マルマイン（第1弾）・カスミのメノクラゲ・わるいアーボック
           + ("PMCG3-026", "PMCG5-016", "PMCG5-035", "PMCG5-050")  # v0.60: サンダー（化石の秘密）・R団のストライク・カスミのギャラドス・タケシのサンドパン
           + ("PMCG4-025", "PMCG4-043", "PMCG5-051")  # v0.61: わるいギャラドス・わるいダグトリオ・タケシのオコリザル
           + ("PMCG1-066", "PMCG2-034", "PMCG2-038", "PMCG2-043", "PMCG6-060", "PMCG2-041")  # v0.62
           + ("PMCG3-034", "PMCG3-037", "PMCG3-038")  # v0.64: 化石の秘密のイシツブテ・ゴローン・ゴローニャ
           + V0_70  # v0.70: 拡張パック以外の商品のポケモン 82 枚
           + V0_72  # v0.72: 拡張パック以外の商品のポケモン 43 枚
           + V0_75  # v0.75: 拡張パック以外の商品のポケモン 15 枚
           + V0_76  # v0.76: 拡張パック以外の商品のポケモン 24 枚
           + V0_77_POKEMON  # v0.77: neo 期の拡張パックのポケモン 50 枚
           + V0_78_POKEMON  # v0.78: 「悪」「鋼」エネルギーを使うポケモン 8 枚
           + V0_79  # v0.79: ポケモン 52 枚
           + V0_82_POKEMON)  # v0.82: エネルギーカードをトラッシュするワザを持つポケモン 18 枚
STARYU = "PMCG1-025"
GRASS, FIRE, WATER, LIGHTNING, PSYCHIC, FIGHTING = "PMCG1-097", "PMCG1-098", "PMCG1-099", "PMCG1-100", "PMCG1-101", "PMCG1-102"
SWITCH = "PMCG1-073"
# v0.57: スタジアム 14 枚（docs/stadiums-v0.57.md）
PEWTER_CITY_GYM, CERULEAN_CITY_GYM, RESISTANCE_GYM, ROCKETS_TRAINING_GYM, CINNABAR_CITY_GYM = "PMCG5-079", "PMCG5-080", "PMCG5-091", "PMCG5-095", "PMCG6-085"
CELADON_CITY_GYM, FUCHSIA_CITY_GYM, SAFFRON_CITY_GYM, NARROW_GYM, ROCKETS_MINEFIELD_GYM = "PMCG5-078", "PMCG6-086", "PMCG6-090", "PMCG5-070", "PMCG6-092"
VIRIDIAN_CITY_GYM, VERMILION_CITY_GYM, NO_REMOVAL_GYM, CHAOS_GYM = "PMCG6-097", "PMCG5-076", "PMCG5-094", "PMCG5-087"
V0_57_STADIUMS = (PEWTER_CITY_GYM, CERULEAN_CITY_GYM, RESISTANCE_GYM, ROCKETS_TRAINING_GYM, CINNABAR_CITY_GYM, CELADON_CITY_GYM, FUCHSIA_CITY_GYM,
                  SAFFRON_CITY_GYM, NARROW_GYM, ROCKETS_MINEFIELD_GYM, VIRIDIAN_CITY_GYM, VERMILION_CITY_GYM, NO_REMOVAL_GYM, CHAOS_GYM)
TRAINERS = ((driver.BILL, 2), (SWITCH, 2), (driver.POTION, 2), (driver.PLUSPOWER, 2), (driver.DEFENDER, 2), (driver.GUST, 2))
# v0.58（docs/stadium-reuse-special-energy-v0.58.md）。タケシのゴローン・ゴローニャ（進化元はタケシのイシツブテ PMCG5-046・047）・ナツメのサイキックコントロール・
# 特殊エネルギー 4 枚
BROCKS_GEODUDE_40, BROCKS_GRAVELER, BROCKS_GOLEM, PSYCHIC_CONTROL = "PMCG5-047", "PMCG5-052", "PMCG5-053", "PMCG6-088"
DOUBLE_COLORLESS, POTION_ENERGY, FULL_HEAL_ENERGY, RAINBOW_ENERGY = "PMCG1-096", "PMCG4-063", "PMCG4-064", "PMCG4-065"
V0_58 = (BROCKS_GRAVELER, BROCKS_GOLEM)
V0_58_ENERGIES = (DOUBLE_COLORLESS, POTION_ENERGY, FULL_HEAL_ENERGY, RAINBOW_ENERGY)
SQUIRTLE, WARTORTLE, BLASTOISE = "PMCG1-023", "PMCG1-027", "PMCG1-032"
# v0.59（docs/energy-control-power-suppression-v0.59.md）。マルマイン（第1弾。ビリリダマから進化）・カスミのメノクラゲ・わるいアーボック（アーボから進化）と、
# トレーナーのカツラ・タケシの保護・まきちらせ!ベトベトガス
BUZZAP_ELECTRODE, MISTYS_TENTACOOL, DARK_ARBOK = "PMCG1-040", "PMCG5-030", "PMCG4-008"
BLAINE_TRAINER, BROCKS_PROTECTION, GOOP_GAS_ATTACK = "PMCG6-093", "PMCG5-090", "PMCG4-056"
V0_59 = (BUZZAP_ELECTRODE, MISTYS_TENTACOOL, DARK_ARBOK)
V0_59_TRAINERS = (BLAINE_TRAINER, BROCKS_PROTECTION, GOOP_GAS_ATTACK)
# v0.60（docs/coins-defense-rebellion-v0.60.md）。サンダー（化石の秘密）・R団のストライク・カスミのギャラドス（カスミのコイキングから進化）・タケシのサンドパン
# （タケシのサンドから進化）
FOSSIL_ZAPDOS, ROCKETS_SCYTHER, MISTYS_GYARADOS, BROCKS_SANDSLASH = "PMCG3-026", "PMCG5-016", "PMCG5-035", "PMCG5-050"
FOSSIL_GASTLY, FOSSIL_HAUNTER = "PMCG3-029", "PMCG3-030"
BASE_MACHOP, BASE_MACHOKE, BASE_MACHAMP = "PMCG1-053", "PMCG1-055", "PMCG1-057"
V0_60 = (FOSSIL_ZAPDOS, ROCKETS_SCYTHER, MISTYS_GYARADOS, BROCKS_SANDSLASH)
# v0.61（docs/reactive-powers-trainer-damage-v0.61.md）。わるいギャラドス（コイキング（ロケット団）から進化）・わるいダグトリオ（ディグダ（ロケット団）から進化）・
# タケシのオコリザル（タケシのマンキーから進化）と、トレーナーのバトル場は穴だらけ!
DARK_GYARADOS, DARK_DUGTRIO, BROCKS_PRIMEAPE, DIGGER = "PMCG4-025", "PMCG4-043", "PMCG5-051", "PMCG4-055"
V0_61 = (DARK_GYARADOS, DARK_DUGTRIO, BROCKS_PRIMEAPE)
# v0.62（docs/history-attacks-v0.62.md）。ピジョン（ポッポから進化）・オニスズメ・オニドリル（オニスズメから進化）・ピジョット（ピジョンから進化）・
# タケシのダグトリオ（タケシのディグダから進化）・ベロリンガ（kyuura の確定した修正を当てはめた写し）
PIDGEOTTO, SPEAROW, FEAROW, PIDGEOT, BROCKS_DUGTRIO, LICKITUNG = "PMCG1-066", "PMCG2-034", "PMCG2-038", "PMCG2-043", "PMCG6-060", "PMCG2-041"
V0_62 = (PIDGEOTTO, SPEAROW, FEAROW, PIDGEOT, BROCKS_DUGTRIO, LICKITUNG)
HERE_COMES_TEAM_ROCKET, TICKLING_MACHINE, CHALLENGE, BLAINES_QUIZ_3 = "PMCG4-062", "PMCG6-084", "PMCG4-058", "PMCG6-082"
V0_63_TRAINERS = (HERE_COMES_TEAM_ROCKET, TICKLING_MACHINE, CHALLENGE, BLAINES_QUIZ_3)
# v0.64（docs/geodude-line-unbounded-coins-v0.64.md）。化石の秘密のイシツブテ → ゴローン → ゴローニャ（「タケシの」系統とは別のカード）
FOSSIL_GEODUDE, FOSSIL_GRAVELER, FOSSIL_GOLEM = "PMCG3-034", "PMCG3-037", "PMCG3-038"
V0_64 = (FOSSIL_GEODUDE, FOSSIL_GRAVELER, FOSSIL_GOLEM)
# v0.65（docs/reactive-decisions-v0.65.md）。キョウ秘伝,変わり身の術・カスミのドククラゲ（カスミのメノクラゲから進化）・タケシのサイドン（タケシのサイホーンから進化）
KOGAS_NINJA_TRICK, MISTYS_TENTACRUEL, BROCKS_RHYDON = "PMCG6-083", "PMCG5-033", "PMCG5-055"
V0_65 = (KOGAS_NINJA_TRICK, MISTYS_TENTACRUEL, BROCKS_RHYDON)
V0_65_REACTIONS = ("ninja_trick", "reaction_switch", "bench_guard")
# v0.66（docs/optional-trainers-v0.66.md）。お上品攻撃・ナツメのESP・カスミの勝負（どれもトレーナー）
CHARITY, SABRINAS_ESP, MISTYS_DUEL = "PMCG5-074", "PMCG6-087", "PMCG5-068"
V0_66 = (CHARITY, SABRINAS_ESP, MISTYS_DUEL)
V0_66_DECISIONS = ("damage_reduction", "esp_redo", "janken_hand")
# v0.67（docs/secret-plan-preflight-v0.67.md）。マチスの秘策（手札から 1 枚をうらにしてベンチに出してよい）
LT_SURGES_SECRET_PLAN, HITMONCHAN = "PMCG5-093", "PMCG1-058"
V0_67 = (LT_SURGES_SECRET_PLAN,)
# v0.68（docs/final-pmcg-cards-v0.68.md）。ガルーラ（利用者が示した訂正の文面）・キョウのベトベトン（だつりょくえき）・イマクニ？のドードー（簡略化した仕様）
KANGASKHAN, KOGAS_MUK, IMAKUNI_DODUO = "PMCG2-046", "PMCG6-023", "PMCG6-074"
V0_68 = (KANGASKHAN, KOGAS_MUK, IMAKUNI_DODUO)
# v0.69（docs/equivalent-non-pack-cards-v0.69.md）。拡張パック以外の商品の、登録したカードと処理に使う欄が同じカード（写しの組 pool_v0_69）を、元のカードと混ぜたデッキ
V0_69 = tuple(__import__("kyuura_engine.cards", fromlist=["read_extract"]).read_extract()["pool_v0_69"])
# v0.71（docs/reprint-text-variants-v0.71.md）。拡張パック以外の商品の再録のカード（写しの組 pool_v0_71。effects.REPRINT_CARDS）。v0.69 の新しい id と同じ手順
# （_v069_step・_v069_decision）で使う（再録のカードのないデッキでは何もしない）
V0_71 = tuple(__import__("kyuura_engine.cards", fromlist=["read_extract"]).read_extract()["pool_v0_71"])
NEW_IDS = frozenset(V0_69) | frozenset(V0_71)
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
    # v0.41: 草（第2弾・リーダーズスタジアム）。同じ名前のエリカのナゾノクサ（PMCG5-002・PMCG5-003）は合わせて 4 枚
    "G41": ((ODDISH, 4), (GLOOM, 3), (BELLSPROUT, 4), (WEEPINBELL, 3), (VICTREEBEL, 2), (ERIKAS_ODDISH, 2), (ERIKAS_ODDISH_40, 2), (ERIKAS_GLOOM, 3),
            *TRAINERS, (GRASS, 25)),
    # v0.41: 超・水（闇からの挑戦・ロケット団）。ひなたぼっこで山札からつける超エネルギー
    "P41": ((SABRINAS_PSYDUCK, 4), (SABRINAS_GOLDUCK, 3), (SABRINAS_SLOWPOKE, 4), (SABRINAS_SLOWBRO, 3), (ROCKET_SLOWPOKE, 4), (ROCKETS_MEWTWO, 3),
            *TRAINERS, (PSYCHIC, 21), (WATER, 6)),
    # v0.41: 無色・水（ロケット団・第2弾・化石の秘密・リーダーズスタジアム）
    # ラッキー（HP 120）はカツラのファイヤーの 90 を受けても HP 未満のことがある（ほかの対戦ポケモンは 90 で HP 以上になり、ひのとりは RD9 で止まる）
    "C41": ((MEOWTH, 4), (DARK_PERSIAN, 3), (HORSEA, 4), (SEADRA, 3), (ERIKAS_JIGGLYPUFF, 4), (CHANSEY, 4), *TRAINERS, (WATER, 26)),
    # v0.41: 炎・草・超（闇からの挑戦）。ひのとりの炎 5 つ
    "R41": ((BLAINES_MOLTRES, 4), (SABRINAS_VENONAT, 4), (SABRINAS_VENOMOTH, 3), *TRAINERS, (FIRE, 25), (GRASS, 6), (PSYCHIC, 6)),
    # v0.42: 草（第2弾・リーダーズスタジアム）。ヒーリング（ラフレシア）・ぼうぎょかふん（エリカのラフレシア）・かおりのわな（エリカのウツボット）
    "G42": ((ODDISH, 4), (GLOOM, 3), (VILEPLUME, 2), (ERIKAS_ODDISH, 2), (ERIKAS_ODDISH_40, 2), (ERIKAS_GLOOM, 3), (ERIKAS_VILEPLUME, 2),
            (ERIKAS_BELLSPROUT, 4), (ERIKAS_WEEPINBELL, 3), (ERIKAS_VICTREEBEL, 2), *TRAINERS, (GRASS, 21)),
    # v0.42: 超（闇からの挑戦・化石の秘密）。へんなこうどう（ヤドラン）・のろい（ゲンガー）。ゴースト（化石の秘密）の「とうめい」もはたらく
    "P42": ((SABRINAS_JYNX, 3), (SLOWPOKE, 4), (SLOWBRO, 3), (GASTLY, 4), (HAUNTER, 3), (GENGAR, 2), *TRAINERS, (PSYCHIC, 29)),
    # v0.42: 超（闇からの挑戦・第1弾・ロケット団）。ぶっしつこうかん（わるいユンゲラー）
    "D42": ((SABRINAS_ABRA, 4), (SABRINAS_KADABRA, 3), (ABRA, 4), (DARK_KADABRA, 3), (DARK_ALAKAZAM, 2), *TRAINERS, (PSYCHIC, 32)),
    # v0.42: 水・無色（化石の秘密・第1弾・リーダーズスタジアム）。おくびょう（メノクラゲ）・かけつける（カイリュー）
    "W42": ((TENTACOOL, 4), (TENTACRUEL, 3), (DRATINI, 4), (DRAGONAIR, 3), (DRAGONITE, 2), (ERIKAS_CLEFAIRY, 4), (ERIKAS_CLEFABLE, 3), *TRAINERS,
            (WATER, 25)),
    # v0.43: 草（第2弾・ロケット団・化石の秘密・リーダーズスタジアム）。くさいかふん（わるいクサイハナ）・こっそりかみつく（わるいゴルバット）・ようぶんきゅうしゅう
    # （エリカのマダツボミ（PMCG5-010））。ナゾノクサ・ズバットは同じ名前の 2 つの版を 2 枚ずつ
    "G43": ((ODDISH, 2), (ROCKET_ODDISH, 2), (DARK_GLOOM, 3), (FOSSIL_ZUBAT, 2), (ROCKET_ZUBAT, 2), (DARK_GOLBAT, 3), (ERIKAS_BELLSPROUT_40, 4),
            (ERIKAS_WEEPINBELL, 2), *TRAINERS, (GRASS, 28)),
    # v0.43: 炎・超（ロケット団・第1弾）。ほのおをもらう（ロケット団のヒトカゲ）・えんかくさいみん（ロケット団のスリープ）・つりあげる（わるいヤドラン）。リザード・わるい
    # スリーパーはヒトカゲ・スリープ（名前）から進化する
    "R43": ((ROCKET_CHARMANDER, 4), (CHARMELEON, 2), (ROCKET_DROWZEE, 4), (DARK_HYPNO, 2), (ROCKET_SLOWPOKE, 4), (DARK_SLOWBRO, 3), *TRAINERS,
            (FIRE, 15), (PSYCHIC, 14)),
    # v0.43: 雷・無色（リーダーズスタジアム・ロケット団）。エナジーチャージ（マチスのレアコイル）・しんかのひかり（わるいハクリュー）・てしたをよぶ（わるいカイリュー。
    # 手札からの進化とポケモン育て屋さん）。マチスのコイルは同じ名前の 2 つの版を 2 枚ずつ
    "L43": ((LT_SURGES_MAGNEMITE, 2), (LT_SURGES_MAGNEMITE_30, 2), (LT_SURGES_MAGNETON, 3), (ROCKET_DRATINI, 4), (DARK_DRAGONAIR, 3), (DARK_DRAGONITE, 2),
            (driver.POKEMON_BREEDER, 2), *TRAINERS, (LIGHTNING, 30)),
    # v0.44: 草・闘（闇からの挑戦・リーダーズスタジアム・ロケット団）。［うか］（キョウのコクーン）・ひっさつばり（キョウのスピアー）・おつかい（エリカのフシギダネ）・
    # じめんにもぐる（ディグダ）・わるいいたずら（カツラのマンキー）
    "K44": ((KOGAS_WEEDLE, 4), (KOGAS_KAKUNA, 3), (KOGAS_BEEDRILL, 2), (ERIKAS_BULBASAUR, 4), (ROCKET_DIGLETT, 4), (BLAINES_MANKEY, 4), *TRAINERS,
            (GRASS, 15), (FIGHTING, 12)),
    # v0.44: 水・闘・無色（闇からの挑戦）。［ボスをよぶ］（サカキのペルシアン）・サカキ（今の番に場に出した・進化したサカキのポケモンを進化させる）・りゅうのきおく・
    # りゅうのたつまき・あらしをよぶ。サカキのワンリキー → ゴーリキー → カイリキーで、同じ番の 2 回の進化
    "V44": ((GIOVANNIS_MEOWTH, 4), (GIOVANNIS_PERSIAN, 3), (GIOVANNIS_MAGIKARP, 4), (GIOVANNIS_GYARADOS, 3), (GIOVANNIS_MACHOP, 3), (GIOVANNIS_MACHOKE, 2),
            (GIOVANNIS_MACHAMP, 1), (GIOVANNI, 4), *TRAINERS, (WATER, 14), (FIGHTING, 10)),
    # v0.44: 水・超・無色（リーダーズスタジアム・ロケット団・闇からの挑戦・第1弾）。スターブーメラン・たきのぼりしんか（コイキング → ギャラドス（第1弾））・
    # てじな（ナツメのバリヤード）・ラッキーたまご（_____のラッキー）・ネギでたたく（カモネギ）・こばんなげ（ニャース）
    "W44": ((MISTYS_STARYU, 4), (ROCKET_MAGIKARP, 4), (GYARADOS, 2), (SABRINAS_MR_MIME, 4), (BLANK_CHANSEY, 4), (FARFETCHD, 3), (ROCKET_MEOWTH, 4),
            *TRAINERS, (WATER, 16), (PSYCHIC, 7)),
    # v0.45: 草・水（闇からの挑戦・リーダーズスタジアム）。とつぜんどく・どくをためる・ポイズンパワー・ベトベトハンド・スミをかける（それ以後の手順 4 のコイン）・
    # こおりのつぶて
    "G45": ((KOGAS_EKANS, 4), (KOGAS_ARBOK, 3), (KOGAS_GRIMER, 4), (MISTYS_HORSEA_50, 4), (MISTYS_SEEL, 3), (MISTYS_DEWGONG, 2), *TRAINERS,
            (GRASS, 15), (WATER, 13)),
    # v0.45: 炎・雷（闇からの挑戦・第1弾・ロケット団）。ファイヤーブレス（多いエネルギーのトラッシュ）・かえんひこう・じりょくせん（相手のエネルギーのつけかえ）・
    # ソニックブーム・プラズマ・エレクトロバーン
    "R45": ((BLAINES_CHARMANDER, 4), (BLAINES_CHARMELEON, 3), (BLAINES_CHARIZARD, 2), (MAGNEMITE, 4), (DARK_MAGNETON, 3), (ROCKETS_ZAPDOS, 3), *TRAINERS,
            (FIRE, 15), (LIGHTNING, 14)),
    # v0.45: 闘・無色（第1弾・リーダーズスタジアム・闇からの挑戦）。かたくなる・いかりのまえば・クロスカウンター・たすけをよぶ（タケシのポケモン）・スパイラルショット・
    # てつだうふり・ダブルひっかき
    "F45": ((ONIX, 3), (RATTATA, 4), (RATICATE, 3), (ROCKETS_HITMONCHAN, 3), (BROCKS_GEODUDE_40, 4), (BROCKS_RHYHORN, 1), (BROCKS_SANDSHREW, 1),
            (GIOVANNIS_MEOWTH_40, 3), *TRAINERS, (FIGHTING, 26)),
    # v0.45: 水・超（ロケット団・第1弾）。ハイドロキャノン・ロケットタックル・さいみんじゅつ・ゆめくい（相手がねむりでないと失敗）
    "W45": ((ROCKET_SQUIRTLE, 4), (DARK_WARTORTLE, 3), (DARK_BLASTOISE, 2), (BASE_GASTLY, 4), (BASE_HAUNTER, 3), *TRAINERS, (WATER, 18), (PSYCHIC, 14)),
    # v0.46: 草・超（闇からの挑戦・リーダーズスタジアム・第2弾・ロケット団）。［くつろぐかおり］・［アレルギーかふん］（お互いにトレーナーを使えない）・せいちょう・
    # かくさんソーラービーム・リフレクター・タマゴばくだん・サイコエクスチェンジ・はなびらのうず
    "G46": ((ERIKAS_BULBASAUR, 4), (ERIKAS_IVYSAUR, 3), (ERIKAS_VENUSAUR, 2), (ERIKAS_EXEGGCUTE, 4), (ERIKAS_EXEGGUTOR, 3), (ODDISH, 2), (ROCKET_ODDISH, 2),
            (DARK_GLOOM, 3), (DARK_VILEPLUME, 2), *TRAINERS, (GRASS, 17), (PSYCHIC, 6)),
    # v0.46: 超・無色（第2弾・リーダーズスタジアム・第1弾）。［なぞのかべ］・［ふしぎなバリアー］・［めんえき］・［にげるサポート］・ヨガのポーズ・いかり
    "P46": ((MR_MIME, 4), (ERIKAS_DRATINI, 4), (SNORLAX, 3), (DODUO, 4), (DODRIO, 3), *TRAINERS, (PSYCHIC, 30)),
    # v0.46: 闘・草（ロケット団・第1弾・第2弾）。［きょうぼう］・あばれくるう・［ねんちゃくえき］・［にげるサポート］
    "D46": ((MANKEY, 4), (DARK_PRIMEAPE, 3), (GRIMER, 4), (DARK_MUK, 3), (DODUO, 2), (DODRIO, 2), *TRAINERS, (FIGHTING, 15), (GRASS, 15)),
    # v0.47: 水・闘・超（化石の秘密・第2弾・ロケット団・第1弾）。なにかの化石から進化するオムナイト・カブトの系統（［おみとおし］・［カブトアーマー］）・ピッピ人形・
    # ［スパイ］・［わるふざけ］・ずつう
    "F47": ((MYSTERIOUS_FOSSIL, 4), (OMANYTE, 3), (OMASTAR, 2), (KABUTO, 3), (KABUTOPS, 2), (JUNGLE_MANKEY, 4), (ROCKET_RATTATA, 4), (FOSSIL_PSYDUCK, 4),
            (CLEFAIRY_DOLL, 2), *TRAINERS, (WATER, 7), (FIGHTING, 11), (PSYCHIC, 2)),
    # v0.47: 超・雷（化石の秘密・第1弾・リーダーズスタジアム・ロケット団）。みらいよち・おどろかす・こうしゅうは・いかりのサンダー・ずつう
    "H47": ((DROWZEE, 4), (HYPNO, 3), (LT_SURGES_EEVEE, 4), (LT_SURGES_JOLTEON, 3), (ROCKET_RATTATA, 4), (FOSSIL_PSYDUCK, 4), (CLEFAIRY_DOLL, 2),
            *TRAINERS, (PSYCHIC, 12), (LIGHTNING, 12)),
    # v0.47: 闘・雷（化石の秘密・第2弾・リーダーズスタジアム・ロケット団）。［げんしのちから］（お互いに進化できない）
    "A47": ((MYSTERIOUS_FOSSIL, 4), (AERODACTYL, 3), (KABUTO, 2), (JUNGLE_MANKEY, 4), (LT_SURGES_EEVEE, 4), (LT_SURGES_JOLTEON, 2), (ROCKET_RATTATA, 4),
            (CLEFAIRY_DOLL, 2), *TRAINERS, (FIGHTING, 12), (LIGHTNING, 11)),
    # v0.48: 無色・草（第1弾・ロケット団・ジャングル・闇からの挑戦）。テクスチャー1・2・サイケこうせん・［へんしょく］・りんぷん・きょだいか・はたく
    # （「ポリゴン」は同じ名前なので、第1弾・ロケット団の 2 枚ずつで 4 枚）
    "C48": ((PORYGON, 2), (ROCKET_PORYGON, 2), (KOGAS_DITTO, 4), (VENONAT, 4), (VENOMOTH, 3), *TRAINERS, (GRASS, 19), (PSYCHIC, 14)),
    # v0.48: 超・草（闇からの挑戦・化石の秘密・ロケット団）。［ガスのからだ］・ナイトスピリッツ・ダメージぞうふく・やみのこえ・かがくへんかガス（［ガスのからだ］・
    # ［へんしょく］を消す）・きょだいか
    "S48": ((SABRINAS_GASTLY, 4), (SABRINAS_HAUNTER, 3), (SABRINAS_GENGAR, 3), (KOGAS_DITTO, 2), (GRIMER, 3), (MUK, 2), *TRAINERS,
            (PSYCHIC, 25), (GRASS, 6)),
    # v0.49: 超（闇からの挑戦・第1弾・リーダーズスタジアム）。［サイコリンク］（ルージュラ・ナツメのユンゲラー・ユンゲラーのワザ）・メガバーン・思い出させる
    "A49": ((SABRINAS_ABRA, 4), (SABRINAS_KADABRA, 3), (SABRINAS_ALAKAZAM, 3), (JYNX, 2), (ABRA, 3), (KADABRA, 2), (RECALL, 4), *TRAINERS,
            (PSYCHIC, 27)),
    # v0.49: 炎・無（リーダーズスタジアム・化石の秘密・第1弾）。「ばける」（リザード・タケシのキュウコンをのせる）・おにび・［へんしん］・思い出させる
    "D49": ((BROCKS_VULPIX, 4), (BROCKS_NINETALES, 3), (DITTO, 4), (CHARMANDER, 3), (CHARMELEON, 3), (RECALL, 3), *TRAINERS, (FIRE, 28)),
    # v0.50: 超（化石の秘密・第1弾）。サイコウェーブ・たいかビーム（自分・相手の進化ポケモン）・退化スプレー（ケーシィ・ゴースの系統。ゴーストの［とうめい］・
    # ゲンガーの［のろい］）。第1弾のフーディンは入れない（v0.7 の手順のダメージスワップは、きぜつさせる移動をわざと試し、その拒否は tests/test_alakazam_games_v0_7.py の
    # 対戦の手順だけが数える。tests/v017_games.py の ``play_game`` では想定外の拒否になる）
    "M50": ((MEW, 4), (ABRA, 4), (KADABRA, 3), (GASTLY, 4), (HAUNTER, 3), (GENGAR, 2), (DEVOLUTION_SPRAY, 4), *TRAINERS, (PSYCHIC, 24)),
    # v0.50: 草（第1弾・闇からの挑戦）。退化スプレー（フシギバナの系統・キョウのビードルの系統。ポケモン育て屋さんで 1 進化を飛ばした重なり・［うか］で重ねた進化）
    "E50": ((BULBASAUR, 4), (IVYSAUR, 2), (VENUSAUR, 2), (KOGAS_WEEDLE, 4), (KOGAS_KAKUNA, 3), (KOGAS_BEEDRILL, 2), (DEVOLUTION_SPRAY, 3),
            (driver.POKEMON_BREEDER, 2), *TRAINERS, (GRASS, 26)),
    # v0.51: 超（闇からの挑戦・化石の秘密・第1弾）。よみがえらせる（自分・相手のトラッシュ）・ふりこののろい・元気のかけら・ポケモンの笛。きぜつしやすいたねポケモン
    # （ケーシィ・ミュウ）でトラッシュにたねポケモンをためる
    "H51": ((SABRINAS_DROWZEE, 4), (SABRINAS_HYPNO, 3), (ABRA, 4), (MEW, 2), (REVIVE, 3), (POKEMON_FLUTE, 3), *TRAINERS, (PSYCHIC, 29)),
    # v0.51: 超（闇からの挑戦）。ナツメのフーディンの［サイコリンク］で、ベンチのナツメのスリーパーのワザ（よみがえらせる・ふりこののろい）を使う（ワザの出どころが
    # いちばん上のカードでない）。元気のかけらでナツメのケーシィ・ナツメのスリープをもどす
    "S51": ((SABRINAS_ABRA, 4), (SABRINAS_KADABRA, 3), (SABRINAS_ALAKAZAM, 2), (SABRINAS_DROWZEE, 4), (SABRINAS_HYPNO, 3), (REVIVE, 3),
            *TRAINERS, (PSYCHIC, 29)),
    # v0.52: 無色（リーダーズスタジアム・化石の秘密・第1弾）。エリカのハクリューのふぶき・つれさる、フジろうじん（控えの進化ポケモン・ダメージのあるポケモンを山札へ）・
    # ポケモン回収（ダメージのあるポケモンのたねポケモンを手札へ。バトル場なら控えから出す）。もどしたたねポケモンは手札から出し直す（元の手順）
    "R52": ((ERIKAS_DRATINI, 4), (ERIKAS_DRAGONAIR, 4), (RATTATA, 4), (RATICATE, 2), (MR_FUJI, 3), (SCOOP_UP, 3), *TRAINERS, (WATER, 28)),
    # v0.53: 草・水（リーダーズスタジアム・ロケット団）。山札をさがすトレーナー: タケシの育て方（タケシのズバット・タケシのゴルバット）・ボスのやりかた（わるいゴルバット）・
    # モンスターボール（コイン）・エネルギー転送（基本エネルギーカード。見せない）・カスミのなみだ（「水」エネルギーカード。手札 1 枚をトラッシュ）
    "S53": ((BROCKS_ZUBAT, 4), (BROCKS_GOLBAT, 2), (ROCKET_ZUBAT, 3), (DARK_GOLBAT_53, 2), (ENERGY_SEARCH, 3), (POKE_BALL, 3), (BOSS_WAY, 3),
            (BROCK_TRAINING, 3), (MISTYS_TEARS, 2), *TRAINERS, (GRASS, 15), (WATER, 8)),
    # v0.53: 草（リーダーズスタジアム）。エリカのお付き（手札 2 枚を山札にもどして「エリカのポケモン」）・メンテナンス・ダウジングマシーン（すてたトレーナーも選べる）・
    # リサイクル（山札の一番上に置いたカードを次に引く）・夜の廃品回収（トラッシュのポケモン・基本エネルギーを山札へ）
    "R53": ((ERIKAS_ODDISH, 4), (ERIKAS_GLOOM, 3), (ERIKAS_BELLSPROUT, 4), (ERIKAS_WEEPINBELL, 2), (ERIKAS_MAIDS, 3), (MAINTENANCE, 3),
            (ITEM_FINDER, 3), (RECYCLE, 3), (NIGHTLY_GARBAGE_RUN, 3), *TRAINERS, (GRASS, 20)),
    # v0.54: 水・無色（リーダーズスタジアム・第1弾）。手札を山札にもどすトレーナー: にせオーキドはかせ・にせオーキドの逆襲（相手の手札）・ギャンブラー（自分。コイン）・
    # ナツメの眼（両方。もどした枚数）・ミニスカート（見せ合ってトレーナーカードを山札へ）・カツラの奥の手（手札がこのカードだけのとき）
    "H54": ((ERIKAS_DRATINI, 4), (ERIKAS_DRAGONAIR, 4), (RATTATA, 4), (RATICATE, 2), (IMPOSTER_OAK, 3), (IMPOSTER_OAKS_REVENGE, 3), (GAMBLER, 2),
            (SABRINAS_GAZE, 2), (BLAINES_LAST_RESORT, 3), (LASS, 3), *TRAINERS, (WATER, 18)),
    # v0.54: 超（闇からの挑戦）。エリカ（両方が 0〜3 枚引く。相手が決める）・スパイ作戦（相手の手札を見る）・カツラのギャンブル（コイン）・ポケモン図鑑（山札の上を並べかえる）。
    # なにかの化石（手札にある間はトレーナーカード。ミニスカートで山札にもどる）
    "D54": ((SABRINAS_DROWZEE, 4), (SABRINAS_HYPNO, 3), (ABRA, 4), (MYSTERIOUS_FOSSIL, 2), (ERIKA, 3), (SECRET_MISSION, 3), (BLAINES_GAMBLE, 3),
            (POKEDEX, 3), *TRAINERS, (PSYCHIC, 23)),
    # v0.55: 闘・超（闇からの挑戦）。サカキのポケモンとナツメのポケモン: サカキの切り札（サカキのワンリキー・ゴーリキーのダメージをすべて → 手札をトラッシュ）・ナツメ
    # （ナツメのゴース・ゴースト（［ガスのからだ］）・ケーシィのあいだでエネルギーカードをすべてつけなおす）・いいきずぐすり・ポケモンセンター・タケシ・
    # エネルギーサーキュレート・ワープポイント
    "G55": ((GIOVANNIS_MACHOP, 4), (GIOVANNIS_MACHOKE, 3), (SABRINAS_GASTLY, 4), (SABRINAS_HAUNTER, 2), (SABRINAS_ABRA, 3),
            (GIOVANNIS_LAST_RESORT, 3), (SABRINA_TRAINER, 3), (SUPER_POTION, 3), (POKEMON_CENTER, 2), (BROCK_TRAINER, 2), (ENERGY_FLOW, 2), (WARP_POINT, 2),
            *TRAINERS, (FIGHTING, 8), (PSYCHIC, 7)),
    # v0.55: 水（第1弾・化石の秘密・ポケモンジャングル）。カスミのいかり・ロケット団のおねーさん・礼儀作法（たねポケモンの少ない手札）・トラッシュ交換・エネルギー・リムーブ・
    # 超エネルギーリムーブ・なんでもなおし・ねむれ!ねむれ!・エリカの親切
    "U55": ((LAPRAS, 3), (STARYU, 4), (STARMIE, 2), (GOLDEEN, 3), (SEAKING, 2), (MISTYS_WRATH, 3), (ROCKETS_SNEAK_ATTACK, 3), (GOOD_MANNERS, 3),
            (TRASH_EXCHANGE, 2), (ENERGY_REMOVAL, 3), (SUPER_ENERGY_REMOVAL, 2), (FULL_HEAL, 3), (SLEEP_TRAINER, 3), (ERIKAS_KINDNESS, 2), (WATER, 22)),
    # v0.56: 水（ジム拡張第1弾）。カスミのポケモン（カスミ（+20）の相手）・エリカの香水・マチス・ロケット団のワナ・マチスの交渉・カスミのわがまま・なんでもなおし
    # （キョウのどくを受けた自分の対戦ポケモンだけを回復する場面）
    "M56": ((MISTYS_SEEL, 4), (MISTYS_DEWGONG, 3), (MISTYS_PSYDUCK, 4), (MISTYS_GOLDUCK, 2), (MISTYS_STARYU, 3), (ERIKAS_PERFUME, 3),
            (LT_SURGE_TRAINER, 2), (ROCKETS_TRAP, 3), (LT_SURGES_TREATY, 2), (MISTYS_WISH, 2), (MISTY_TRAINER, 3), (FULL_HEAL, 3), (WATER, 26)),
    # v0.56: 草・無色（ジム拡張第2弾）。キョウのポケモン（キョウ（どく）の相手）・見えない壁・ロケット団員・ロケット団の実験・なんでもなおし
    "K56": ((KOGAS_PIDGEY, 3), (KOGAS_PIDGEOTTO, 2), (KOGAS_KOFFING, 3), (KOGAS_WEEZING, 2), (KOGAS_EKANS, 3), (KOGAS_ARBOK, 2), (KOGAS_GRIMER, 2),
            (KOGA_TRAINER, 3), (INVISIBLE_WALL, 3), (ROCKET_GRUNT, 3), (ROCKETS_EXPERIMENT, 3), (FULL_HEAL, 3), (GRASS, 28)),
    # v0.57: ジム拡張第1弾のスタジアム 9 枚と、タケシ・カスミ・エリカ・マチスのポケモン（ニビ: タケシのイシツブテの抵抗力・ハナダ: カスミのパウワウの「にげる」・
    # タマムシ: エリカのナゾノクサの特殊状態・クチバ: マチスのコラッタのワザのコイン）。せまいジム・抵抗力低下ジム・ロケット団の特訓ジム・錯乱ジム（突風・きずぐすりを
    # 相手が借りる）・リムーブ禁止ジム（エネルギー・リムーブの 2 枚の追加の条件）
    "L57": ((BROCKS_GEODUDE, 4), (MISTYS_SEEL, 4), (MISTYS_DEWGONG, 2), (LT_SURGES_RATTATA, 4), (ERIKAS_ODDISH, 4),
            (PEWTER_CITY_GYM, 2), (CERULEAN_CITY_GYM, 2), (CELADON_CITY_GYM, 2), (VERMILION_CITY_GYM, 2), (NARROW_GYM, 1), (RESISTANCE_GYM, 1),
            (ROCKETS_TRAINING_GYM, 1), (CHAOS_GYM, 2), (NO_REMOVAL_GYM, 1), (ENERGY_REMOVAL, 2), (driver.POTION, 2), (driver.GUST, 2),
            (FIGHTING, 8), (WATER, 8), (GRASS, 6)),
    # v0.57: ジム拡張第2弾のスタジアム 5 枚と、キョウ・ナツメ・サカキ・カツラのポケモン（セキチク: キョウのドガース・ヤマブキ: ナツメのケーシィの基本エネルギー・
    # トキワ: サカキのコイキング → ギャラドス・グレン: 水のワザを受けるカツラのポニータ・爆発ジム: ベンチに出すたねポケモン）
    "D57": ((KOGAS_KOFFING, 4), (KOGAS_WEEZING, 2), (SABRINAS_ABRA, 4), (GIOVANNIS_MAGIKARP, 4), (GIOVANNIS_GYARADOS, 2), (BLAINES_PONYTA, 4),
            (FUCHSIA_CITY_GYM, 2), (SAFFRON_CITY_GYM, 2), (CINNABAR_CITY_GYM, 2), (ROCKETS_MINEFIELD_GYM, 2), (VIRIDIAN_CITY_GYM, 2), (driver.POTION, 2),
            (GRASS, 10), (PSYCHIC, 8), (WATER, 10)),
    # v0.58: 闘・無色。タケシのイシツブテ → ゴローン → ゴローニャ（ばくれつで場のスタジアムをトラッシュ・いわなだれで相手の控えを選ぶ）・特殊エネルギー 4 種類・
    # ナツメのサイキックコントロール（相手のトラッシュのトレーナーを使う）・ニビシティジム（ばくれつでトラッシュするスタジアム）
    "E58": ((BROCKS_GEODUDE, 3), (BROCKS_GEODUDE_40, 1), (BROCKS_GRAVELER, 3), (BROCKS_GOLEM, 2), (RATTATA, 4), (PEWTER_CITY_GYM, 2),
            (PSYCHIC_CONTROL, 3), (DOUBLE_COLORLESS, 4), (POTION_ENERGY, 3), (FULL_HEAL_ENERGY, 3), (RAINBOW_ENERGY, 3), (FIGHTING, 29)),
    # v0.58: 草・水。フシギバナ（エナジートランスでレインボーエネルギーを「草」としてつけかえる）・カメックス（あまごい。レインボーエネルギーは RB2）・
    # 特殊エネルギー 4 種類・ナツメのサイキックコントロール
    "R58": ((BULBASAUR, 4), (IVYSAUR, 3), (VENUSAUR, 2), (SQUIRTLE, 4), (WARTORTLE, 3), (BLASTOISE, 2), (RAINBOW_ENERGY, 4), (DOUBLE_COLORLESS, 3),
            (POTION_ENERGY, 2), (FULL_HEAL_ENERGY, 2), (PSYCHIC_CONTROL, 2), (GRASS, 15), (WATER, 14)),
    # v0.59: 雷・草・水。ビリリダマ → マルマイン（［エネエネ］で自分のポケモンにつく）・アーボ（ロケット団）→ わるいアーボック（ショックアイ・どくのきり）・
    # カスミのメノクラゲ（クリスタルビーム）・まきちらせ!ベトベトガス
    "Z59": ((VOLTORB, 4), (BUZZAP_ELECTRODE, 3), (ROCKET_EKANS, 4), (DARK_ARBOK, 3), (MISTYS_TENTACOOL, 4), (GOOP_GAS_ATTACK, 3), *TRAINERS,
            (LIGHTNING, 10), (GRASS, 11), (WATER, 6)),
    # v0.59: 炎・闘。カツラのガーディ → ウインディ・カツラのポニータ → ギャロップ（カツラで「炎」2 枚をいっしょにつける）・タケシのイシツブテ → ゴローン・
    # タケシのロコン（タケシの保護をつける）・カツラ・タケシの保護
    # （カツラを使う場面（手札にカツラと「炎」2 枚）を起こすため、トレーナーはマサキ・ポケモンいれかえ・きずぐすりだけにし、炎エネルギーを多くした）
    "B59": ((BLAINES_GROWLITHE, 4), (BLAINES_ARCANINE, 2), (BLAINES_PONYTA, 4), (BLAINES_RAPIDASH, 2), (BROCKS_GEODUDE, 4),
            (BROCKS_VULPIX, 3), (BLAINE_TRAINER, 4), (BROCKS_PROTECTION, 4), (driver.BILL, 2), (SWITCH, 2), (driver.POTION, 2), (FIRE, 21), (FIGHTING, 6)),
    # v0.60: 雷・草・闘。サンダー（化石の秘密。サンダーストーム）・R団のストライク（かげぶんしん・こうそくカマ）・タケシのサンド → タケシのサンドパン
    # （スピードスター・とげボール）
    "Z60": ((FOSSIL_ZAPDOS, 4), (ROCKETS_SCYTHER, 4), (BROCKS_SANDSHREW, 4), (BROCKS_SANDSLASH, 3), *TRAINERS, (LIGHTNING, 13), (GRASS, 8), (FIGHTING, 12)),
    # v0.60: 水・超・闘。カスミのコイキング → カスミのギャラドス（［はんこう］・ハイドロクラッシュ）と、受ける側の効果（化石の秘密のゴース → ゴーストの「とうめい」。サンダー
    # ストームの控えのコインとの順番（TS1）・スピードスターで無視する効果）・ワンリキー → ゴーリキー → カイリキー（［はんげき］。控えでもはたらく）
    "M60": ((MISTYS_MAGIKARP, 4), (MISTYS_GYARADOS, 3), (FOSSIL_GASTLY, 3), (FOSSIL_HAUNTER, 2), (BASE_MACHOP, 3), (BASE_MACHOKE, 2), (BASE_MACHAMP, 1),
            *TRAINERS, (WATER, 18), (PSYCHIC, 6), (FIGHTING, 6)),
    # v0.61: 水・闘。コイキング（ロケット団）→ わるいギャラドス（［ファイナルビーム］・れいとうビーム）・ディグダ（ロケット団）→ わるいダグトリオ（［おとしあな］・
    # つきおとす）・バトル場は穴だらけ!
    "G61": ((ROCKET_MAGIKARP, 4), (DARK_GYARADOS, 3), (ROCKET_DIGLETT, 4), (DARK_DUGTRIO, 3), (DIGGER, 4), *TRAINERS, (WATER, 18), (FIGHTING, 12)),
    # v0.61: 闘。タケシのマンキー → タケシのオコリザル（［ずらかる］・おおあばれ）・ニビシティジム（おおあばれでトラッシュするスタジアム）・バトル場は穴だらけ!
    "P61": ((BROCKS_MANKEY, 4), (BROCKS_PRIMEAPE, 4), (BROCKS_GEODUDE, 4), (DIGGER, 3), (PEWTER_CITY_GYM, 3), *TRAINERS, (FIGHTING, 30)),
    # v0.62: 無色（エネルギーは草・水）。ポッポ → ピジョン（ふきとばし・オウムがえし）→ ピジョット（つばさでうつ・ハリケーン）・オニスズメ（つつく・オウムがえし）→
    # オニドリル（こうそくいどう・ドリルくちばし）・ベロリンガ（まきつくベロ・ちょうおんぱ）
    "H62": ((PIDGEY, 4), (PIDGEOTTO, 3), (PIDGEOT, 2), (SPEAROW, 4), (FEAROW, 3), (LICKITUNG, 3), *TRAINERS, (GRASS, 15), (WATER, 14)),
    # v0.62: 闘・無色。タケシのディグダ → タケシのダグトリオ（あながくれ・ドリルホール）・オニスズメ → オニドリル・ベロリンガ
    "D62": ((BROCKS_DIGLETT, 4), (BROCKS_DUGTRIO, 3), (SPEAROW, 3), (FEAROW, 2), (LICKITUNG, 3), *TRAINERS, (FIGHTING, 20), (GRASS, 13)),
    # v0.63: 無色（エネルギーは草・水）。ポッポ → ピジョン → ピジョット・オニスズメ → オニドリル・ベロリンガ（カツラのクイズで置くワザのあるポケモン）と、v0.63 の 4 枚・
    # おもてになったサイドを取る・入れかえるマチスの交渉・カスミのわがまま
    # v0.64: 闘。化石の秘密のイシツブテ → ゴローン → ゴローニャ（れんぞくいしなげ・かたくなる・いわおとし・いわころがり・じばく）とイワーク（第1弾）
    "G64": ((FOSSIL_GEODUDE, 4), (FOSSIL_GRAVELER, 3), (FOSSIL_GOLEM, 3), (ONIX, 4), *TRAINERS, (FIGHTING, 34)),
    # v0.65: 草・水。キョウのポケモン（キョウのドガース・キョウのアーボ → キョウのアーボック・キョウのベトベター）と変わり身の術、カスミのメノクラゲ → カスミのドククラゲ
    # （［にげこむ］・クラゲどく）
    "K65": ((KOGAS_KOFFING, 4), (KOGAS_EKANS, 3), (KOGAS_ARBOK, 2), (KOGAS_GRIMER, 3), (MISTYS_TENTACOOL, 4), (MISTYS_TENTACRUEL, 3), (KOGAS_NINJA_TRICK, 4),
            *TRAINERS, (GRASS, 13), (WATER, 12)),
    # v0.65: 闘。タケシのサイホーン → タケシのサイドン（［ベンチガード］・ラリアット）を控えに置き、タケシのサンド・タケシのディグダで戦う
    "R65": ((BROCKS_RHYHORN, 4), (BROCKS_RHYDON, 4), (BROCKS_SANDSHREW, 4), (BROCKS_DIGLETT, 4), *TRAINERS, (FIGHTING, 32)),
    # v0.66: 草・超・水。ナツメのコンパン → ナツメのモルフォン（はかいビーム・かいふくりんぷん）・ナツメのコダック（こまったねんりき）・ナツメのゴース → ゴースト → ゲンガー
    # （やみのこえ）とナツメのESP、カスミの勝負
    "S66": ((SABRINAS_VENONAT, 4), (SABRINAS_VENOMOTH, 3), (SABRINAS_PSYDUCK, 4), (SABRINAS_GASTLY, 3), (SABRINAS_HAUNTER, 2), (SABRINAS_GENGAR, 2),
            (SABRINAS_ESP, 4), (MISTYS_DUEL, 3), *TRAINERS, (PSYCHIC, 12), (GRASS, 7), (WATER, 4)),
    # v0.66: 闘。化石の秘密のイシツブテ → ゴローン（れんぞくいしなげ・かたくなる）・イワークとお上品攻撃、カスミの勝負
    "C66": ((FOSSIL_GEODUDE, 4), (FOSSIL_GRAVELER, 3), (ONIX, 4), (CHARITY, 4), (MISTYS_DUEL, 3), *TRAINERS, (FIGHTING, 30)),
    # v0.67: 闘・超。たねポケモン（ディグダ・エビワラー・ケーシィ）と 1 進化のユンゲラー・トレーナー（うらにして出すカードに、たねポケモン・進化カード・トレーナー・
    # エネルギーのどれもある）とマチスの秘策
    "L67": ((DIGLETT, 4), (HITMONCHAN, 4), (ABRA, 4), (KADABRA, 3), (LT_SURGES_SECRET_PLAN, 4), *TRAINERS, (FIGHTING, 15), (PSYCHIC, 14)),
    # v0.68: 草・無色。ガルーラ（こどものおつかい・れんぞくパンチ）・キョウのベトベター → キョウのベトベトン（だつりょくえき・ヘドロのうず）・イマクニ？のドードー（ハモる）
    "K68": ((KANGASKHAN, 4), (KOGAS_GRIMER, 4), (KOGAS_MUK, 3), (IMAKUNI_DODUO, 4), *TRAINERS, (GRASS, 33)),
    # v0.69: 水・闘。カスミのメノクラゲ（PMCG5-030・PR1-048）→ カスミのドククラゲ（PMCG5-033・GD2-004。［にげこむ］）・タケシのサイホーン → タケシのサイドン（PMCG5-055・
    # GD1-013。［ベンチガード］）・カスミのヒトデマン（GD2-012・PR1-031）・カスミのタッツー（GD2-008）・カスミの勝負（GD2-017）・カスミ（GD2-015）・無色2個エネルギー
    # （PMCG1-096・GD1-025）・基本エネルギー（IP2-005・NIP2-005・PMCG1-099・IP2-012・NIP1-006）。同じ名前のカードは版をまたいで 4 枚まで
    "M69": (("PMCG5-030", 2), ("PR1-048", 2), ("PMCG5-033", 1), ("GD2-004", 2), ("PMCG5-049", 4), ("PMCG5-055", 1), ("GD1-013", 2), ("GD2-012", 2),
            ("PR1-031", 2), ("GD2-008", 3), ("GD2-017", 2), ("GD2-015", 2), ("PMCG1-096", 2), ("GD1-025", 2), *TRAINERS, ("IP2-005", 5), ("NIP2-005", 2),
            ("PMCG1-099", 5), ("IP2-012", 4), ("NIP1-006", 3)),
    # v0.69: 超・草。ナツメのケーシィ（PMCG6-043）→ ナツメのユンゲラー（GD6-003・PMCG6-047）→ ナツメのフーディン（GD6-004。［サイコリンク］）・ナツメのポリゴン（GD6-013）・
    # エリカのミニリュウ（GD4-013・PR1-039。［ふしぎなバリアー］）・エリカのマダツボミ（GD4-006）→ エリカのウツドン（PMCG5-011）→ エリカのウツボット（GD4-008。［かおりのわな］）・
    # ナツメのESP（GD6-018）・エリカの香水（GD4-018）・マチス（GD3-021）・無色2個エネルギー（GD3-025・IP1-023）・基本エネルギー（IP1-024・NIP2-007・PMCG1-101・IP1-004・NIP1-003）
    "S69": (("PMCG6-043", 4), ("GD6-003", 2), ("PMCG6-047", 1), ("GD6-004", 2), ("GD6-013", 2), ("GD4-013", 2), ("PR1-039", 2), ("GD4-006", 4),
            ("PMCG5-011", 3), ("GD4-008", 2), ("GD6-018", 3), ("GD4-018", 2), ("GD3-021", 2), ("GD3-025", 2), ("IP1-023", 2), *TRAINERS, ("IP1-024", 4),
            ("NIP2-007", 2), ("PMCG1-101", 1), ("IP1-004", 3), ("NIP1-003", 3)),
    # v0.70: 水。ニョロモ（ES1-016・PMCG1-024）→ ニョロゾ（ES1-017・QSG-015。ぐるぐる）→ ニョロボン（ES1-018・QSG-016。ハイドロポンプ）・カスミのヒトデマン（GD2-013）→
    # カスミのスターミー（GD2-014。みずでっぽう）・タッツー（ES3-015。かくれる・みずでっぽう）・ゼニガメ（IP2-016）→ カメール（SI-015・IP2-003）・ワニノコ（NIP2-016・PF1-007）→
    # アリゲイツ（NIP2-004）・マリル（PR1-066・NIP2-002）・ラプラス（ES2-010・QSG-019）
    "W70": (("ES1-016", 2), ("PMCG1-024", 2), ("ES1-017", 2), ("QSG-015", 1), ("ES1-018", 1), ("QSG-016", 1), ("GD2-013", 3), ("GD2-014", 2), ("ES3-015", 2),
            ("IP2-016", 2), ("SI-015", 1), ("IP2-003", 1), ("NIP2-016", 2), ("PF1-007", 2), ("NIP2-004", 2), ("PR1-066", 2), ("NIP2-002", 1), ("ES2-010", 1),
            ("QSG-019", 1), *TRAINERS, (WATER, 17)),
    # v0.70: 草・雷。チコリータ（NIP1-001・PRN-006・PRN-009）→ ベイリーフ（NIP1-024）・メリープ（NIP2-018）→ モココ（NIP2-026）・マチスのピカチュウ（GD3-002。たいでん）・
    # マチスのビリリダマ（GD3-008）・レディバ（SI-001。こうそくいどう）・エレブー（IP1-026）・ヒマナッツ（NIP1-002）・パラス（NIP1-022・PMCG2-003）・エリカのマダツボミ
    # （GD4-005）・ドガース（IP1-039）・ハネッコ（PRN-047）
    "L70": (("NIP1-001", 2), ("PRN-006", 1), ("PRN-009", 1), ("NIP1-024", 3), ("NIP2-018", 3), ("NIP2-026", 2), ("GD3-002", 3), ("GD3-008", 2), ("SI-001", 2),
            ("IP1-026", 2), ("NIP1-002", 1), ("NIP1-022", 2), ("PMCG2-003", 1), ("GD4-005", 2), ("IP1-039", 2), ("PRN-047", 2), *TRAINERS, (GRASS, 9), (LIGHTNING, 8)),
    # v0.70: 超・闘・無色・炎。ミュウ（PR1-069（名前を訂正した写し）・PMCG3-033）・ガルーラ（ES3-033・QSG-044・PMCG2-046）・ワンリキー（PMCG1-053）→ ゴーリキー（ES2-022・
    # QSG-036）・サワムラー（ES2-026）・ルージュラ（ES2-019・QSG-031・IP1-037・PRN-013）・ポッポ（ES1-024）→ ピジョン（PMCG1-066）→ ピジョット（SI-005）・オニスズメ（IP2-013）
    # → オニドリル（ES2-031）・カツラのポニータ（GD5-008。こうそくいどう）・ノコッチ（PRN-038）・トゲピー（SI-007）。同じ名前のカードは版をまたいで 4 枚まで
    "C70": (("PR1-069", 2), ("PMCG3-033", 2), ("ES3-033", 2), ("QSG-044", 1), ("PMCG2-046", 1), ("PMCG1-053", 3), ("ES2-022", 2), ("QSG-036", 1), ("ES2-026", 2),
            ("ES2-019", 1), ("QSG-031", 1), ("IP1-037", 1), ("PRN-013", 1), ("ES1-024", 2), ("PMCG1-066", 1), ("SI-005", 1), ("IP2-013", 2), ("ES2-031", 1),
            ("GD5-008", 2), ("PRN-038", 1), ("SI-007", 1), *TRAINERS, (PSYCHIC, 6), (FIGHTING, 6), (WATER, 3), (FIRE, 2)),
    # v0.70: 闘・超・水。タケシのサンド（PMCG5-043）→ タケシのサンドパン（GD1-004。ぜんしんばり・サンドストーム）・タケシのイシツブテ（PMCG5-046）→ タケシのゴローン（GD1-008）・
    # ナツメのゴース（GD6-006。まとわりつく）・カツラのドードー（PMCG6-064）→ カツラのドードリオ（GD5-013）・イーブイ（ES1-032・PMCG2-037）→ エーフィ（PF2-004）・ベロリンガ
    # （ES1-030・QSG-042）・ハリーセン（NIP2-024）・ネイティ（NIP2X-004）
    "B70": (("PMCG5-043", 3), ("GD1-004", 2), ("PMCG5-046", 3), ("GD1-008", 2), ("GD6-006", 2), ("PMCG6-064", 2), ("GD5-013", 2), ("ES1-032", 2), ("PMCG2-037", 1),
            ("PF2-004", 2), ("ES1-030", 1), ("QSG-042", 1), ("NIP2-024", 2), ("NIP2X-004", 2), *TRAINERS, (FIGHTING, 10), (PSYCHIC, 7), (WATER, 4)),
    # v0.71: 炎。ヒトカゲ → リザード → リザードン（プロモ PR1-030。ほのおのうずは無色2個エネルギーも 1 枚）・カツラのブーバー（GD5-011・PMCG6-031）・ブーバーと、再録の
    # トレーナー（元気のかけら GD1-017・エネルギー転送 GD4-015・QSG-048・ポケモン図鑑の 3 つの id・グレンタウンジムなど）。同じ名前は版をまたいで 4 枚まで
    "R71": (("PMCG1-014", 4), ("PMCG1-017", 3), ("PR1-030", 2), ("PMCG1-021", 1), ("GD5-011", 2), ("PMCG6-031", 1), ("PMCG1-020", 2),
            ("GD1-017", 2), ("PMCG1-078", 1), ("GD4-015", 2), ("QSG-048", 1), ("PMCG3-044", 1), ("GD1-016", 1), ("NIP1-015", 1), ("GD2-021", 1),
            ("NIP2X-007", 1), ("GD1-021", 1), ("IP1-019", 1), ("GD1-014", 2), ("QSG-050", 1), ("GD1-022", 1), ("GD5-023", 1), ("PMCG1-082", 1),
            ("GD4-023", 2), ("GD2-020", 1), ("GD5-024", 1), ("NIP1-020", 2), (DOUBLE_COLORLESS, 2), (FIRE, 18)),
    # v0.71: 草・超。フシギダネ → フシギソウ → フシギバナ（IPH-001・PR1-029。エナジートランス）・エリカのナゾノクサ → エリカのクサイハナ → エリカのラフレシア（GD4-004）・
    # ナツメのスリープ → ナツメのスリーパー（GD6-010）・カモネギ（PR1-033）と、再録のトレーナー（ジム 2・お上品攻撃・リサイクル・ワープポイントなど）
    "G71": (("PMCG1-001", 4), ("PMCG1-008", 3), ("IPH-001", 1), ("PR1-029", 1), ("PMCG5-002", 3), ("PMCG5-009", 2), ("GD4-004", 2), ("PMCG6-045", 3),
            ("GD6-010", 2), ("PR1-033", 2), ("GD4-027", 1), ("GD6-025", 1), ("GD3-014", 1), ("GD1-023", 1), ("GD1-018", 1), ("GD4-019", 1), ("GD4-025", 1),
            ("GD6-024", 1), ("GD2-022", 1), ("GD3-023", 1), ("QSG-053", 1), ("GD3-019", 1), ("IP2-019", 1), ("GD4-014", 1), (GRASS, 13), (PSYCHIC, 10)),
    # v0.71: 水・闘。ゼニガメ → カメール → カメックス（PR1-028・IPH-002・PMCG1-032。あまごい）・ニョロモ（IP2-009）・タケシのイシツブテ（GD1-006）・ディグダと、再録の
    # トレーナー（ジム 3・きずぐすり・ディフェンダー・プラスパワー・突風・ポケモンいれかえ・なんでもなおし・マサキ・エネルギー回収・ポケモンセンター）
    "W71": (("PMCG1-023", 4), ("PMCG1-027", 3), ("PR1-028", 1), ("IPH-002", 1), ("PMCG1-032", 1), ("IP2-009", 3), ("GD1-006", 3), ("PMCG1-052", 2),
            ("GD1-024", 1), ("GD2-023", 1), ("GD3-024", 1), ("GD2-019", 1), ("IP2-024", 1), ("GD3-017", 1), ("NIP2X-006", 1), ("GD6-021", 1), ("NIP1X-006", 1),
            ("QSG-051", 1), ("IP1-028", 1), ("QSG-052", 1), ("NIP1X-007", 1), ("IP2-007", 1), ("NIP2-025", 2), ("QSG-047", 1), ("GD6-022", 1),
            (WATER, 16), (FIGHTING, 8)),
    # v0.72: 闘・雷・炎。タケシのサンド（GD1-003）・タケシのサイホーン（GD1-012。つのでなげる）・イシツブテ（PMCG3-034）→ ゴローン（ES2-023。れんぞくいわなげ・じしん）・
    # イワーク（ES2-024・QSG-037）・エビワラー（ES2-027・QSG-038）・マチスのエレブー（GD3-010・PR1-040。たいでん・デンキとばし）・ピカチュウ（ES1-019・QSG-020）・
    # カツラのガーディ（GD5-005・PR1-059。ふりとばす）
    "F72": (("GD1-003", 3), ("GD1-012", 3), ("PMCG3-034", 3), ("ES2-023", 2), ("ES2-024", 2), ("QSG-037", 1), ("ES2-027", 2), ("QSG-038", 1),
            ("GD3-010", 2), ("PR1-040", 1), ("ES1-019", 2), ("QSG-020", 1), ("GD5-005", 2), ("PR1-059", 1), *TRAINERS, (FIGHTING, 13), (LIGHTNING, 6), (FIRE, 3)),
    # v0.72: 草・超。エリカのナゾノクサ（PMCG5-002）→ エリカのクサイハナ（GD4-003。ゆめみのまい・くさいにおい）・エリカのマダツボミ（GD4-006）→ エリカのウツドン（GD4-007。
    # ねむけどく）・ニドラン♀（ES1-006・QSG-004）・マダツボミ（ES3-005）・ストライク（ES3-008・QSG-054）・パラス（NIP1-022）→ パラセクト（ES1-011。きゅうけつ）・
    # ズバット（ES1-008）→ ゴルバット（ES1-009。きゅうけつ）・エリカのタマタマ（GD4-009。たまなげ）・ナツメのルージュラ（GD6-012。めざめのキッス）
    "G72": (("PMCG5-002", 3), ("GD4-003", 2), ("GD4-006", 3), ("GD4-007", 2), ("ES1-006", 2), ("QSG-004", 1), ("ES3-005", 2), ("ES3-008", 1),
            ("QSG-054", 1), ("NIP1-022", 2), ("ES1-011", 2), ("ES1-008", 2), ("ES1-009", 2), ("GD4-009", 2), ("GD6-012", 2), *TRAINERS, (GRASS, 14), (PSYCHIC, 5)),
    # v0.72: 無色・水・超。エリカのピッピ（GD4-012。おつきみ）・コラッタ（ES1-025・QSG-039）・ドードー（IP1-030）→ ドードリオ（ES1-029）・ラッキー（ES1-031・QSG-043）・
    # オニスズメ（ES2-030）・ガルーラ（PR1-037）・ルギア（PRN-042。エアロブラスト）・エアームド（PF3-009）・カスミのニョロモ（GD2-002。めまわし）・コイキング（PR1-036）・
    # テッポウオ（NIP2-010）・コダック（PMCG3-010）→ ゴルダック（ES3-013）・ケーシィ（NIP2X-003）
    "C72": (("GD4-012", 2), ("ES1-025", 2), ("QSG-039", 1), ("IP1-030", 2), ("ES1-029", 2), ("ES1-031", 2), ("QSG-043", 1), ("ES2-030", 2), ("PR1-037", 2),
            ("PRN-042", 2), ("PF3-009", 1), ("GD2-002", 2), ("PR1-036", 2), ("NIP2-010", 2), ("PMCG3-010", 2), ("ES3-013", 2), ("NIP2X-003", 2), *TRAINERS,
            (DOUBLE_COLORLESS, 2), (WATER, 11), (PSYCHIC, 4)),
    # v0.73: 無色・炎。コラッタ → ラッタ・ポッポ → ピジョン（月の石で山札から無色の進化カード）・ドードー・ロコン・なにかの化石（化石の発掘）と、元気のかたまり（両方の版）・
    # 熱血!・マスターボール 4 枚（同じ名前 4 枚まで）・化石の発掘・月の石・ポケモン再転送
    "S73": (("PMCG1-060", 4), ("PMCG1-062", 3), ("PMCG1-059", 4), ("PMCG1-066", 3), ("PMCG1-061", 3), ("PMCG1-015", 3), ("PMCG3-046", 2),
            ("GD5-019", 2), ("ES2-034", 2), ("GD5-021", 3), ("GD6-023", 1), ("ES2-036", 1), ("QSG-058", 1), ("NIP1-021", 1), ("ES1-035", 2), ("ES1-036", 3),
            ("ES3-035", 2), (FIRE, 13), (DOUBLE_COLORLESS, 4), (WATER, 3)),
    # v0.73: 闘・無色。エビワラー・ディグダ・ドードー・コラッタ → ラッタと、スーパーポケモン回収（両方）・マサキの転送装置（両方）・超エネルギー回収・パソコン大暴走！（両方）・
    # マスターボール（NIP2-022）
    "R73": (("PMCG1-058", 4), ("PMCG1-052", 4), ("PMCG1-061", 4), ("PMCG1-060", 4), ("PMCG1-062", 3), ("IP1-009", 2), ("IP2-029", 2), ("IP1-020", 2),
            ("IP2-021", 2), ("PR1-009", 3), ("PR1-026", 2), ("PR1-041", 2), ("NIP2-022", 1), (FIGHTING, 16), (FIRE, 5), (WATER, 4)),
    # v0.74: 超・炎。ゴース → ゴースト（エナジーへんかん）・R団のファイヤー（ふしちょう）・ヤドン（ゴミあさり）→ わるいヤドラン（［つりあげる］）と、ポケモンタワー・エネルギースタジアム
    # （タワーを入れかえる）・エネルギー回収・熱血!・ダウジングマシーン
    "T74": (("PMCG3-029", 4), ("PMCG3-030", 2), ("PMCG5-020", 3), ("PMCG3-027", 4), ("PMCG4-036", 2), ("PMCG1-014", 2), ("ES3-036", 3), ("NIP1X-009", 2),
            ("PMCG1-076", 2), ("GD5-021", 2), ("PMCG1-087", 1), (PSYCHIC, 17), (FIRE, 16)),
    # v0.75: 水・雷。カスミのコダック（GD2-001。たすけをよぶ）・カスミのメノクラゲ（GD2-003。くらげのむれ・PMCG5-030）→ カスミのドククラゲ（PMCG5-033）・メノクラゲ（PMCG3-011）→
    # ドククラゲ（PMCG3-017）・クラブ（PMCG3-013）→ キングラー（ES3-014。しおまねき・もろばバサミ）・ピカチュウ（QSG-021・PR1-020。じゅうでん・10まんボルト）
    "W75": (("GD2-001", 3), ("GD2-003", 3), ("PMCG5-030", 1), ("PMCG5-033", 2), ("PMCG3-011", 2), ("PMCG3-017", 2), ("PMCG3-013", 3), ("ES3-014", 2),
            ("QSG-021", 2), ("PR1-020", 2), *TRAINERS, (WATER, 18), (LIGHTNING, 8)),
    # v0.75: 炎・超・草。カツラのロコン（GD5-003。おにびあつめ）・カツラのガーディ（GD5-006。もえあがる）・ガーディ（ES3-010・QSG-009。おつかい・ひのこ）・ナツメのスリープ
    # （GD6-009。エナジーサポート）・ミュウツー（PR1-007・PR1-008。エネルギーきゅうしゅう）・タケシのズバット（GD1-001。しらせる）・パラス（ES1-010。ほうしをとばす）・
    # ヒマナッツ（PRN-032。せいちょう）と無色2個エネルギー
    "F75": (("GD5-003", 3), ("GD5-006", 3), ("ES3-010", 2), ("QSG-009", 1), ("GD6-009", 3), ("PR1-007", 2), ("PR1-008", 1), ("GD1-001", 3),
            ("ES1-010", 3), ("PRN-032", 2), *TRAINERS, (FIRE, 9), (PSYCHIC, 7), (GRASS, 7), (DOUBLE_COLORLESS, 2)),
    # v0.76: 闘・炎・草・無色。ワンリキー（ES2-021・QSG-035。きあいいっぱつ）・マチスのコラッタ（GD3-011。きあいだめ → かじる）・ニドラン♂（ES1-007・QSG-005。きあいだめ →
    # つのでとっしん）・ドードー（ES1-028・QSG-041）・ヒトカゲ（ES1-013・QSG-007。なきごえ）・ヒノアラシ（PF1-004。にらみつける・スピードスター）・ガーディ（IP2-026。とびかかる・ひのこ）・
    # コンパン（ES3-004。かなしばり・サイケこうせん）
    "K76": (("ES2-021", 3), ("QSG-035", 1), ("GD3-011", 3), ("ES1-007", 2), ("QSG-005", 1), ("ES1-028", 2), ("QSG-041", 1), ("ES1-013", 2), ("QSG-007", 1),
            ("PF1-004", 3), ("IP2-026", 3), ("ES3-004", 3), *TRAINERS, (FIGHTING, 6), (FIRE, 9), (GRASS, 8)),
    # v0.76: 水・雷・草・超。ゼニガメ（ES1-015・QSG-013・IP2-018。ウォーターパワー → はたく）・マリル（PRN-028。はずむ → とびのる）・パウワウ（ES2-006・QSG-017）・ピカチュウ（IP1-040）・
    # チコリータ（PF1-001。なきごえ）・ヤドン（PR1-006。ドわすれ）・ウパー（PRN-003。しっぽをふる・みずでっぽう）・ワニノコ（PRN-008・PRN-011。にらみつける・みだれひっかき）
    "W76": (("ES1-015", 2), ("QSG-013", 1), ("IP2-018", 1), ("PRN-028", 3), ("ES2-006", 2), ("QSG-017", 1), ("IP1-040", 3), ("PF1-001", 3), ("PR1-006", 3),
            ("PRN-003", 3), ("PRN-008", 2), ("PRN-011", 1), *TRAINERS, (WATER, 7), (LIGHTNING, 4), (GRASS, 4), (PSYCHIC, 8)),
    # v0.77: 草・超。ヒマナッツ（せいちょう・メガドレイン）・ハネッコ（neo2-004）→ ポポッコ（neo1-012・neo3-003）・キャタピー・イトマル・ズバット（どくをとばす）・パラス・コンパン・
    # クヌギダマ・ストライク（こうそくいどう）・ヘラクロス（とつげきホーン）・タマタマ・ゴースと、スーパーポケモン回収・マサキの転送装置
    "G77": (("neo1-006", 2), ("neo2-004", 3), ("neo1-012", 2), ("neo3-003", 1), ("neo2-001", 2), ("neo2-003", 2), ("neo3-001", 2), ("neo3-002", 2),
            ("neo4-001", 2), ("neo4-005", 2), ("neo4-007", 2), ("neo4-009", 2), ("neo4-049", 2), ("neo4-048", 2), *TRAINERS, ("neo1-083", 2), ("neo1-084", 2),
            (GRASS, 12), (PSYCHIC, 4)),
    # v0.77: 水・闘。ウパー（ドわすれ）→ ヌオー（じしん）・ワニノコ（neo1-024 にらみつける・neo4-028 みずでっぽう）・ウリムー・マンタイン・タッツー → シードラ → キングドラ
    # （りゅうのたつまき）・ニョロモ（neo2-013）→ ニョロゾ（PMCG1-028）→ ニョロボン（neo2-037）・トサキント・ヒトデマン・パウワウ・テッポウオと、マサキの転送装置
    "W77": (("neo1-026", 3), ("neo1-031", 2), ("neo1-024", 2), ("neo4-028", 2), ("neo1-027", 1), ("neo4-029", 1), ("neo1-028", 2), ("PMCG3-014", 2),
            ("PMCG3-020", 1), ("neo1-035", 1), ("neo2-013", 2), ("PMCG1-028", 2), ("neo2-037", 1), ("neo3-012", 1), ("neo3-013", 1), ("neo4-027", 1),
            ("neo4-030", 1), *TRAINERS, ("neo1-084", 2), (WATER, 13), (FIGHTING, 7)),
    # v0.77: 無色・闘・炎・雷・超。オタチ → オオタチ・ホーホー・オドシシ・トゲピー・ポリゴン・エレブー（スピードスター）・キリンリキ・ウソッキー（じたばた）・グライガー・ヨーギラス・
    # ノコッチ・イシツブテ・ウリムー（neo3-038）・ブーバー・ガーディ・マグマッグ・メリープ（neo2-020・neo4-042）・ワンリキー・ゴマゾウ・サワムラー（かかとおとし）と、スーパーポケモン回収
    "C77": (("neo1-059", 3), ("neo1-064", 2), ("neo1-060", 2), ("neo1-062", 1), ("neo1-066", 1), ("neo4-086", 1), ("neo1-039", 1), ("neo1-047", 1),
            ("neo1-051", 2), ("neo1-052", 2), ("neo2-034", 1), ("neo2-047", 1), ("neo3-037", 1), ("neo3-038", 1), ("neo1-019", 1), ("neo4-015", 1),
            ("neo4-017", 1), ("neo2-020", 1), ("neo4-042", 1), ("neo4-069", 1), ("neo4-072", 1), ("neo4-075", 1), *TRAINERS, ("neo1-083", 2),
            (FIGHTING, 8), (FIRE, 4), (LIGHTNING, 4), (PSYCHIC, 2)),
    # v0.78: 悪。ニューラ（ふくろだたき）・デルビル（neo2-039・NIP2X-005 ごうだつ、neo4-081 おいつめる。同じ名前 4 枚まで）と、悪エネルギー 4 枚（neo1-094・PRN-002・NIP2X-010。同じ名前 4 枚まで）。
    # 「悪」でないエビワラー・サワムラー（neo4-075）に悪エネルギーがつくと、ポケモンチェックのたびに 10 ダメージ・ダメージカウンター 1 個。プラスパワー・ディフェンダーは
    # ごうだつでトラッシュされる（TRAINERS）
    "D78": (("neo1-056", 4), ("neo2-039", 2), ("NIP2X-005", 1), ("neo4-081", 1), (HITMONCHAN, 4), ("neo4-075", 3), *TRAINERS,
            ("neo1-094", 2), ("PRN-002", 1), ("NIP2X-010", 1), ("PMCG1-077", 4), (FIGHTING, 15), (DOUBLE_COLORLESS, 4), (WATER, 6)),
    # v0.78: 鋼。イワーク（PMCG1-054）→ ハガネール・ストライク（PMCG2-017）→ ハッサム（みねうち）・エアームド（neo1-058 はがねのつばさ、NIP1X-005 メタルスラッシュ。同じ名前
    # 4 枚まで）と、鋼エネルギー 4 枚（neo1-095・NIP1X-010。同じ名前 4 枚まで）。「鋼」でないイワーク・ストライクに鋼エネルギーがつくと、与えるワザのダメージも -10
    "M78": (("PMCG1-054", 3), ("neo1-057", 2), ("PMCG2-017", 3), ("neo2-045", 2), ("neo1-058", 2), ("NIP1X-005", 2), *TRAINERS,
            ("neo1-095", 2), ("NIP1X-010", 2), ("PMCG1-077", 4), (FIGHTING, 11), (GRASS, 11), (DOUBLE_COLORLESS, 4)),
    # v0.79: 水・雷。マリル（neo1-025・SI-017）→ マリルリ（バブルシャワー）・メリープ → モココ（エレキテール）→ デンリュウ（ギガショック）・ピカチュウ（neo1-036。こうそくいどう）・
    # チョンチー・フリーザー（PR1-064。ダイヤモンドダスト）・エレブー（PR1-010）・ハリーセン・テッポウオ・タッツー → シードラ（neo1-029）・トサキント → アズマオウ（neo3-017）・
    # サニーゴ・マンタイン
    "W79": (("neo1-025", 3), ("SI-017", 1), ("neo1-034", 2), ("neo2-020", 3), ("neo3-027", 2), ("neo1-043", 1), ("neo1-036", 2), ("neo1-037", 2),
            ("PR1-064", 1), ("PR1-010", 1), ("neo3-015", 1), ("neo3-016", 1), ("PMCG3-014", 2), ("neo1-029", 1), ("PMCG2-021", 2), ("neo3-017", 1),
            ("neo2-017", 1), ("neo4-031", 1), (driver.BILL, 2), (SWITCH, 2), (driver.POTION, 2), (WATER, 14), (LIGHTNING, 10), (FIGHTING, 2)),
    # v0.79: 超・水。ヤドン（neo1-045）→ ヤドキング（ひらめく）・ネイティ（neo1-046 テレキネシス・neo2-022）・ゴース（ES3-022・QSG-028。こわがらせる）・ナツメのゴース → ナツメのゴースト
    # （かげからおそう）・ルージュラ（あやしいおどり）・イーブイ → エーフィ・キリンリキと、プラスパワー・ディフェンダー（だましとるの相手）
    "P79": (("neo1-045", 3), ("SI-014", 2), ("neo1-046", 2), ("neo2-022", 2), ("ES3-022", 2), ("QSG-028", 2), ("PMCG6-049", 3), ("GD6-007", 2),
            ("neo3-018", 2), ("PMCG2-037", 2), ("neo2-029", 1), ("neo4-089", 2), *TRAINERS, (PSYCHIC, 19), (WATER, 4)),
    # v0.79: 草・炎。ナゾノクサ・チコリータ・レディバ・ツボツボ・ヒマナッツ → キマワリ・ハネッコ → ポポッコ → ワタッコ・ビードル → コクーン → スピアー（さんばいどく）・デルビル
    # （neo2-012）・ロコン（neo4-014）・マグマッグ・ホウオウ・カツラのヒトカゲ（ファイヤーテール）・ヒノアラシ → マグマラシ
    "F79": (("neo1-001", 2), ("neo1-002", 2), ("neo1-003", 2), ("neo1-007", 1), ("neo1-006", 2), ("neo1-013", 1), ("neo2-004", 2), ("neo1-012", 1),
            ("neo1-016", 1), ("PMCG1-004", 2), ("PMCG1-009", 1), ("neo2-010", 1), ("neo2-012", 2), ("neo4-014", 2), ("neo3-008", 1), ("neo3-011", 1),
            ("GD5-001", 3), ("PF1-004", 2), ("NIP1-013", 1), (driver.BILL, 2), (SWITCH, 1), (GRASS, 13), (FIRE, 14)),
    # v0.79: 闘・無色・悪・鋼。サンド（ES2-020・QSG-033。スピードスター）・タケシのマンキー（からかう）・マンキー → オコリザル（SI-012）・マチスのコラッタ → マチスのラッタ（GD3-012）・
    # ニューラ（PF3-003。だましとる）・イワーク → ハガネール（PRN-014。メタルクラッシュ）・カポエラー・グライガー・プリン（neo4-085）・ミニリュウ（neo4-087。だっぴ）・ブルー（いかりのずつき）・
    # ラッキー（neo4-092）と、悪・鋼エネルギー・無色2個エネルギー
    "C79": (("ES2-020", 2), ("QSG-033", 2), ("GD1-005", 2), ("PMCG2-028", 2), ("SI-012", 1), ("GD3-011", 2), ("GD3-012", 1), ("PF3-003", 2),
            ("PMCG1-054", 2), ("PRN-014", 1), ("neo2-038", 2), ("neo4-071", 2), ("neo4-085", 2), ("neo4-087", 2), ("neo3-048", 2), ("neo4-092", 1),
            (driver.BILL, 2), (SWITCH, 2), ("neo1-094", 4), ("neo1-095", 4), (DOUBLE_COLORLESS, 2), (FIGHTING, 18)),
    # v0.74: 草。キョウのアーボ → キョウのアーボック・キョウのドガース → キョウのマタドガス・キョウのベトベター・キョウのズバット → キョウのゴルバットと、キョウの忍者ジム・
    # ラッキースタジアム（NIP2X-009・PRN-015・PRN-016・PRN-027。同じ名前 4 枚まで）・セキチクシティジム（名前の違うスタジアムの記録で FG1 にしない）
    "L74": (("PMCG6-002", 4), ("PMCG6-019", 2), ("PMCG6-015", 3), ("PMCG6-016", 2), ("PMCG6-007", 3), ("PMCG6-005", 3), ("PMCG6-014", 2), ("PR1-067", 3),
            ("NIP2X-009", 1), ("PRN-015", 1), ("PRN-016", 1), ("PRN-027", 1), ("PMCG6-086", 1), (GRASS, 29), (DOUBLE_COLORLESS, 4)),
    # v0.80: 闘・無色。ワンリキー → ゴーリキー・コラッタ → ラッタ・ドードーと、v0.80 のトレーナーの前半 15 種類（すごいつりざお〜退化スプレーHYPER）
    "N80": (("PMCG1-053", 4), ("PMCG1-055", 3), ("PMCG1-060", 4), ("PMCG1-062", 3), ("PMCG1-061", 3), ("neo1-074", 1), ("neo1-087", 1), ("neo1-092", 1),
            ("neo2-053", 1), ("neo4-102", 1), ("neo1-078", 1), ("neo1-089", 2), ("neo1-091", 1), ("neo4-100", 1), ("neo1-082", 1), ("neo1-090", 1),
            ("neo1-093", 1), ("neo1-075", 1), ("neo1-076", 2), ("neo2-056", 2), (FIGHTING, 25)),
    # v0.80: 草。フシギダネ → フシギソウ・ロケット団のナゾノクサ → わるいクサイハナ（性格判定の「わるい」）と、v0.80 のトレーナーの後半 15 種類（カツラのクイズ その2〜エフェクトガード。
    # スタジアム 4 枚を含む）
    "S80": (("PMCG1-001", 4), ("PMCG1-008", 3), ("PMCG4-003", 4), ("PMCG4-006", 3), ("GD5-017", 1), ("neo1-080", 1), ("neo4-105", 2), ("neo4-107", 1),
            ("neo4-111", 1), ("PR1-013", 1), ("PR1-074", 1), ("PRN-026", 1), ("neo1-077", 2), ("neo4-099", 2), ("neo3-054", 1), ("neo4-101", 1),
            ("neo4-106", 1), ("neo4-112", 1), ("ES2-033", 2), (GRASS, 27)),
    # v0.81: 闘・無色。ワンリキー → ゴーリキー・エビワラー・コラッタ → ラッタ・ドードーと、ポケモンのどうぐ 11 種類（きのみは 4 枚の id で 4 枚まで）・ピントレンズ
    "T81": (("PMCG1-053", 4), ("PMCG1-055", 3), ("PMCG1-058", 3), ("PMCG1-060", 3), ("PMCG1-062", 2), ("PMCG1-061", 2), ("neo1-073", 1), ("PRN-004", 1),
            ("NIP1X-008", 1), ("NIP2X-008", 1), ("neo1-079", 2), ("neo1-081", 1), ("PRN-005", 1), ("neo3-055", 2), ("neo1-088", 2), ("neo4-103", 2),
            ("neo4-109", 2), ("neo4-104", 2), (FIGHTING, 25)),
    # v0.81: 草・無色。ロケット団のアーボ → わるいアーボック・コラッタ → わるいラッタ（わるいポケモンはロケット団のアジトで最大HP +20）・ポッポ（無色のワザはマダツボミのとうで -30）と、
    # 常にはたらくスタジアム 3 種類・きのみ・きせきのみ・悪エネルギー（ポケモンチェックの 1 できのみと順番が問題になる）
    "D81": (("PMCG4-001", 4), ("PMCG4-008", 3), ("PMCG1-060", 3), ("PMCG4-046", 3), ("PMCG1-059", 3), ("neo1-085", 2), ("neo3-057", 2), ("neo4-110", 2),
            ("neo1-073", 2), ("neo1-081", 2), ("neo1-094", 3), (GRASS, 31)),
    # v0.82: 炎・無色。ヒノアラシ（3 つの id で 4 枚）→ マグマラシ・ポニータ（2 つの id）→ ギャロップ・ブーバー（2 つの id）・イーブイ → やさしいブースター・ファイヤー・
    # ひかるリザードン（デッキに 1 枚まで）と、リサイクルエネルギー・エコロジム
    "E82": (("neo1-018", 2), ("PRN-007", 1), ("PRN-010", 1), ("PF1-005", 3), ("ES3-011", 2), ("QSG-010", 2), ("QSG-011", 2), ("ES3-012", 2),
            ("QSG-012", 2), ("PMCG2-037", 3), ("neo4-019", 2), ("PR1-071", 2), ("neo4-025", 1), ("neo1-096", 4), ("neo1-086", 2), (FIRE, 25), (LIGHTNING, 4)),
    # v0.82: 雷・水。ピカチュウ（プロモ）→ ライチュウ（2 つの id）・メリープ → モココ・ルギア（炎・水・雷）・ウパー → ヌオー（相手のエネルギーをトラッシュする）と、
    # リサイクルエネルギー・エコロジム
    "L82": (("PR1-062", 3), ("IP1-003", 2), ("neo3-025", 2), ("neo2-020", 3), ("neo1-041", 3), ("neo1-072", 2), ("neo1-026", 3), ("neo3-014", 2),
            ("neo1-096", 4), ("neo1-086", 2), (LIGHTNING, 18), (WATER, 12), (FIRE, 4)),
    "T63": ((PIDGEY, 4), (PIDGEOTTO, 3), (PIDGEOT, 2), (SPEAROW, 4), (FEAROW, 3), (LICKITUNG, 3), (HERE_COMES_TEAM_ROCKET, 2), (TICKLING_MACHINE, 3),
            (CHALLENGE, 3), (BLAINES_QUIZ_3, 3), (LT_SURGES_TREATY, 2), (MISTYS_WISH, 2), (driver.BILL, 2), (SWITCH, 2), (GRASS, 11), (WATER, 11)),
    # v0.63: 闘。タケシのディグダ → タケシのダグトリオ・タケシのマンキー → タケシのオコリザル・タケシのイシツブテ（挑戦状でうらにしてベンチに出すたねポケモンが多い）と、
    # v0.63 の 4 枚
    "Q63": ((BROCKS_DIGLETT, 4), (BROCKS_DUGTRIO, 3), (BROCKS_MANKEY, 4), (BROCKS_PRIMEAPE, 3), (BROCKS_GEODUDE, 4), (HERE_COMES_TEAM_ROCKET, 2),
            (TICKLING_MACHINE, 3), (CHALLENGE, 3), (BLAINES_QUIZ_3, 3), (driver.BILL, 2), (SWITCH, 2), (FIGHTING, 27)),
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
PAIRINGS_V0_41 = (("G41", "P41"), ("P41", "C41"), ("C41", "R41"), ("R41", "G41"), ("G41", "P31"), ("R41", "F37"))
# v0.42: D42 対 P31（ピッピ・ピクシー・カスミのコダックが、エネループ・ライフダウン・テレポートブラスト・マインドショックなどを自分のワザとして使う）
PAIRINGS_V0_42 = (("G42", "P42"), ("P42", "D42"), ("D42", "W42"), ("W42", "G42"), ("D42", "P31"))
# v0.43: G43 対 P31（ピッピ・ピクシー・カスミのコダックが、ふらふらとぶ・のびるつる・どくのこななどを自分のワザとして使う）
PAIRINGS_V0_43 = (("G43", "R43"), ("R43", "L43"), ("L43", "G43"), ("G43", "P31"))
# v0.44: W44 対 P31（ピッピ・ピクシー・カスミのコダックが、てじな・ラッキーたまご・スターブーメランなどを自分のワザとして使う。1 度だけ使えるワザはまねられない）
PAIRINGS_V0_44 = (("K44", "V44"), ("V44", "W44"), ("W44", "K44"), ("W44", "P31"))
# v0.45: G45 対 P31（ピッピ・ピクシー・カスミのコダックが、スミをかける・とつぜんどく・ポイズンパワー・ベトベトハンドなどを自分のワザとして使う）
PAIRINGS_V0_45 = (("G45", "R45"), ("R45", "F45"), ("F45", "W45"), ("W45", "G45"), ("G45", "P31"))
# v0.46: G46 対 P31（ピッピ・ピクシー・カスミのコダックが、せいちょう・かくさんソーラービーム・リフレクター・サイコエクスチェンジなどを自分のワザとして使う）
PAIRINGS_V0_46 = (("G46", "P46"), ("P46", "D46"), ("D46", "G46"), ("G46", "P31"))
# v0.47: H47 対 P31（ピッピ・ピクシー・カスミのコダックが、みらいよち・おどろかす・ずつう・こうしゅうはを自分のワザとして使う）
PAIRINGS_V0_47 = (("F47", "H47"), ("H47", "A47"), ("A47", "F47"), ("H47", "P31"))
# v0.48: C48 対 P31・S48 対 P31（ピッピ・ピクシー・カスミのコダックが、テクスチャー1・2・きょだいか・はたく・ナイトスピリッツ・ダメージぞうふく・やみのこえを
# 自分のワザとして使う）
PAIRINGS_V0_48 = (("C48", "S48"), ("S48", "C48"), ("C48", "P31"), ("S48", "P31"))
# v0.49: A49 対 P31・D49 対 P31（ピッピ・ピクシー・カスミのコダックが、［サイコリンク］で持つワザ・［へんしん］の今の姿のワザを自分のワザとして使う）
PAIRINGS_V0_49 = (("A49", "D49"), ("D49", "A49"), ("A49", "P31"), ("D49", "P31"))
# v0.50: M50 対 P31（ピッピ・ピクシー・カスミのコダックが、サイコウェーブ・たいかビームを自分のワザとして使う）・M50 対 D49（タケシのキュウコンの「ばける」の
# ポケモン（退化させられない。DV5）・［へんしん］のメタモン（今の姿でなく実際の重なりで選ぶ））
PAIRINGS_V0_50 = (("M50", "E50"), ("E50", "M50"), ("M50", "P31"), ("M50", "D49"))
# v0.51: H51 対 E50（相手のトラッシュのたねポケモン（フシギダネ・キョウのビードル）をよみがえらせる・ポケモンの笛で出す）・H51 対 P31（ピッピ・ピクシー・カスミのコダックが、
# よみがえらせる・ふりこののろいを自分のワザとして使う）・S51 対 H51（［サイコリンク］で持つよみがえらせる・ふりこののろい）
PAIRINGS_V0_51 = (("H51", "E50"), ("E50", "H51"), ("H51", "P31"), ("S51", "H51"))
# v0.52: R52 対 H51（よみがえらせる・元気のかけら・ポケモンの笛で、もどしたたねポケモンとトラッシュの関係）・R52 対 E50（つれさるで相手のポケモン育て屋さんで重ねた
# フシギバナ・［うか］で重ねたキョウのスピアーを山札にもどす。退化スプレーのあとのポケモン）・R52 対 P31（ピッピ・ピクシー・カスミのコダックが、ふぶき・つれさるを自分の
# ワザとして使う）。D49（メタモン）は、エリカのミニリュウ（［ふしぎなバリアー］）を写す対戦準備で既存の TF1 に当たるので組にしない（「ばける」・［へんしん］の場面は単体テスト）
PAIRINGS_V0_52 = (("R52", "H51"), ("H51", "R52"), ("R52", "E50"), ("R52", "P31"))
# v0.53: S53 対 R53・S53 対 P31（ピッピ・ピクシー・カスミのコダックのいる相手）・R53 対 H51（よみがえらせる・元気のかけら・ポケモンの笛のトラッシュの取り合い。夜の廃品回収で
# トラッシュのたねポケモンを山札にもどす）・R53 対 K44（カツラのマンキーのわるいいたずらで、R53 のトラッシュのカードが山札の上にのる。リサイクル・夜の廃品回収と同じトラッシュ）。
# どの組も席を入れかえて同じ seed で 2 局（``run``）
PAIRINGS_V0_53 = (("S53", "R53"), ("S53", "P31"), ("R53", "H51"), ("R53", "K44"))
# v0.54: H54 対 D54（手札を山札にもどすトレーナーと、エリカ・スパイ作戦・ポケモン図鑑の相手）・H54 対 R53（ミニスカート・にせオーキドはかせで、トレーナーの多い相手の手札が
# 山札にもどる）・D54 対 P31（ピッピ・ピクシー・カスミのコダックのいる相手）
PAIRINGS_V0_54 = (("H54", "D54"), ("D54", "H54"), ("H54", "R53"), ("D54", "P31"))
# v0.55: G55 対 U55（エネルギーをはがす・回復・特殊状態の回復と、その相手）・G55 対 S48（ナツメのゴースト・ゲンガー（［ガスのからだ］）とかがくへんかガスの相手。ワープポイントの
# 相手の入れ替え）・U55 対 H54（トレーナーの多い相手の手札をロケット団のおねーさんで見る。にせオーキドはかせなどで手札が入れ替わる）
PAIRINGS_V0_55 = (("G55", "U55"), ("U55", "G55"), ("G55", "S48"), ("U55", "H54"))
# v0.56: M56 対 K56（カスミの +20・キョウのどく・見えない壁・ロケット団員・ロケット団の実験と、エリカの香水・マチス・ワナ・交渉・わがまま。``run`` が席を入れかえる
# ので、K56 対 M56 は組にしない（v0.55 の G55-U55・U55-G55 は同じ局の重複だった）・K56 対 P31（ピッピ・ピクシー・カスミのコダックのいる相手。キョウのポケモンの
# ワザを相手のワザとして使う）・M56 対 G55（トレーナーの多い相手の手札をエリカの香水で見る）・K56 対 U55（なんでもなおし・エネルギー・リムーブの相手に、キョウの
# どく・見えない壁・ロケット団員）
PAIRINGS_V0_56 = (("M56", "K56"), ("K56", "P31"), ("M56", "G55"), ("K56", "U55"))
# v0.57: L57 対 D57（ジム拡張第1弾・第2弾のスタジアムを出し合い、入れかえる）・L57 対 U55（エネルギー・リムーブ・超エネルギーリムーブの相手のリムーブ禁止ジム。トレーナーの
# 多い相手の錯乱ジム）・D57 対 M56（カスミのポケモンのいる相手のハナダシティジム・グレンタウンジム（水のワザ）。エリカの香水で出させるたねポケモンの爆発ジム）・
# D57 対 P31（ピッピ・ピクシー・カスミのコダックがマチスのポケモンでないワザを使う相手）。``run`` が席を入れかえる
PAIRINGS_V0_57 = (("L57", "D57"), ("L57", "U55"), ("D57", "M56"), ("D57", "P31"))
# v0.58: E58 対 R58（特殊エネルギーとサイキックコントロールどうし）・E58 対 U55（エネルギー・リムーブなどのトラッシュのトレーナーを使う。特殊エネルギーをはがされる）・
# R58 対 H54（にせオーキドはかせなど手札を入れかえるトレーナーをトラッシュから使う）・E58 対 L57（錯乱ジム・リムーブ禁止ジムの場でサイキックコントロールを使う。
# ばくれつでスタジアムをトラッシュ）。``run`` が席を入れかえる
PAIRINGS_V0_58 = (("E58", "R58"), ("E58", "U55"), ("R58", "H54"), ("E58", "L57"))
# v0.59: Z59 対 B59（ベトベトガス・ショックアイ・クリスタルビームとカツラ・タケシの保護）・Z59 対 R58（エナジートランス・あまごいをベトベトガス・ショックアイで止め、
# クリスタルビームを受けたポケモンにつける）・B59 対 U55（タケシの保護をつけたポケモンのエネルギーカードを、エネルギー・リムーブなどではがせない）・
# Z59 対 D46（［きょうぼう］・［ねんちゃくえき］などの常にはたらく特殊能力を、ベトベトガスで止める）
PAIRINGS_V0_59 = (("Z59", "B59"), ("Z59", "R58"), ("B59", "U55"), ("Z59", "D46"))
# v0.60: Z60 対 M60（サンダーストームの控えのコイン・かげぶんしん・スピードスターとはんこう・とうめい・はんげき）・M60 対 Z59（はんこうをまきちらせ!ベトベトガスで止め、
# ショックアイでは止めない）・Z60 対 D46（わるいベトベトン・わるいオコリザルの常にはたらく特殊能力をスピードスターで無視する）・Z60 対 P31（ゆびをふるでサンダーストーム・
# かげぶんしんを相手のワザとして使う）
PAIRINGS_V0_60 = (("Z60", "M60"), ("M60", "Z59"), ("Z60", "D46"), ("Z60", "P31"))
# v0.61: G61 対 P61（［おとしあな］で「10」になったタケシのオコリザルの［ずらかる］・［ファイナルビーム］の相手・バトル場は穴だらけ!どうし）・P61 対 M60（カイリキーの
# ［はんげき］・カスミのギャラドスの［はんこう］と［ずらかる］）・G61 対 Z60（R団のストライクのかげぶんしん・スピードスターの相手の［ファイナルビーム］）・G61 対 P31
# （ピッピ・ピクシー・カスミのコダックが、つきおとす・れいとうビームを自分のワザとして使う）。``run`` が席を入れかえる
PAIRINGS_V0_61 = (("G61", "P61"), ("P61", "M60"), ("G61", "Z60"), ("G61", "P31"))
# v0.62: H62 対 D62（オウムがえし・ハリケーン・あながくれとドリルホール。どちらの席でも）・H62 対 G61（れいとうビームのマヒ・バトル場は穴だらけ!のダメージを受けた
# オニスズメのオウムがえし（マヒを与える・OM2）・ハリケーンとファイナルビーム）・D62 対 M60（はんげき・「とうめい」・はんこうのあとのドリルホール・オウムがえし）・
# H62 対 P31（ピッピ・ピクシー・カスミのコダックが、オウムがえし・ドリルくちばし・ハリケーンを自分のワザとして使う）。``run`` が席を入れかえる
PAIRINGS_V0_62 = (("H62", "D62"), ("H62", "G61"), ("D62", "M60"), ("H62", "P31"))
# v0.63: T63 対 Q63（どちらの席でも 4 枚を使う。挑戦状を受ける・受けない、クイズの正解・不正解、くすぐりマシーンで置いた手札がもどる、ロケット団参上! のあとの
# マチスの交渉・カスミのわがまま・サイドを取る）・T63 対 H62（v0.62 のオウムがえし・ハリケーンと、相手の手札を置いておく）・Q63 対 K56（ロケット団の実験・
# キョウの効果と、挑戦状・クイズ）。``run`` が席を入れかえる
PAIRINGS_V0_63 = (("T63", "Q63"), ("T63", "H62"), ("Q63", "K56"))
# v0.64: G64 対 H62（ピジョンの「オウムがえし」で受けたれんぞくいしなげを出す・ワザの履歴）・G64 対 D46（わるいオコリザル・ドードリオなど。
# 受けるダメージを変える効果のない相手）・G64 対 P61（タケシのオコリザルの［ずらかる］）・G64 対 W45（わるいカメールの「こうらがえし」）
PAIRINGS_V0_64 = (("G64", "H62"), ("G64", "D46"), ("G64", "P61"), ("G64", "W45"))
# v0.65: K65 対 R65（変わり身の術・［にげこむ］と［ベンチガード］）・R65 対 L39（控えへのダメージ（じばく・スパーク・ビリビリ）で［ベンチガード］）・R65 対 Z60
# （サンダーストーム）・K65 対 H62（ふきとばし・ハリケーンの相手に変わり身の術・［にげこむ］）
PAIRINGS_V0_65 = (("K65", "R65"), ("R65", "L39"), ("R65", "Z60"), ("K65", "H62"))
# v0.66: S66 対 C66（ESP・お上品攻撃・カスミの勝負）・C66 対 P46（お上品攻撃とバリヤードの［なぞのかべ］・エリカのミニリュウの［ふしぎなバリアー］）・S66 対 H62・C66 対 R65
PAIRINGS_V0_66 = (("S66", "C66"), ("C66", "P46"), ("S66", "H62"), ("C66", "R65"))
# v0.67: L67 対 C66（相手のうらのカードにれんぞくいしなげ・お上品攻撃）・L67 対 R65（じしん系のベンチへのダメージ）・L67 対 S66・L67 対 G64
PAIRINGS_V0_67 = (("L67", "C66"), ("L67", "R65"), ("L67", "S66"), ("L67", "G64"))
# v0.68: K68 対 R65（ベンチへのダメージ・ラリアット）・K68 対 C66（れんぞくいしなげ）・K68 対 L67（マチスの秘策）・K68 対 P31
PAIRINGS_V0_68 = (("K68", "R65"), ("K68", "C66"), ("K68", "L67"), ("K68", "P31"))
# v0.69: M69 対 S69（新しい id どうし）・M69 対 R65（タケシのサイドンの新旧）・S69 対 S66（ナツメのESP・ナツメのポケモンの新旧）
PAIRINGS_V0_69 = (("M69", "S69"), ("M69", "R65"), ("S69", "S66"))
# v0.70: W70 対 L70・C70 対 B70・L70 対 C70・B70 対 W70（どのデッキも v0.70 のカードと前の版のカードを混ぜる）
PAIRINGS_V0_70 = (("W70", "L70"), ("C70", "B70"), ("L70", "C70"), ("B70", "W70"))
PAIRINGS_V0_71 = (("R71", "G71"), ("W71", "R71"), ("G71", "W71"))
# v0.72: F72 対 G72・C72 対 F72・G72 対 C72・C72 対 W70（どのデッキも v0.72 のカードと前の版のカードを混ぜる）
PAIRINGS_V0_72 = (("F72", "G72"), ("C72", "F72"), ("G72", "C72"), ("C72", "W70"))
# v0.73: S73 対 R73・S73 対 C72・R73 対 F72（どのデッキも v0.73 のカードと前の版のカードを混ぜる）
PAIRINGS_V0_73 = (("S73", "R73"), ("S73", "C72"), ("R73", "F72"))
# v0.74: T74 対 L74（ポケモンタワーとラッキースタジアム・忍者ジムの入れかえ）・T74 対 S73（ポケモンタワーの下の化石の発掘・熱血!・元気のかたまり）・L74 対 R73
PAIRINGS_V0_74 = (("T74", "L74"), ("T74", "S73"), ("L74", "R73"))
# v0.75: W75 対 F75・F75 対 T74（ポケモンタワーの下のおにびあつめ）・W75 対 P31（ゆびをふる・ちょうのうりょくで v0.75 のワザをまねる）
PAIRINGS_V0_75 = (("W75", "F75"), ("F75", "T74"), ("W75", "P31"))
# v0.76: K76 対 W76・K76 対 P31（ゆびをふる・ちょうのうりょくで v0.76 のワザをまねる）・W76 対 C72
PAIRINGS_V0_76 = (("K76", "W76"), ("K76", "P31"), ("W76", "C72"))
# v0.77: G77 対 W77・C77 対 G77・W77 対 C77（どのデッキも v0.77 のカードで組み、W77 は前の版のタッツー・シードラ・ニョロゾで 2 進化の系統を通す）
PAIRINGS_V0_77 = (("G77", "W77"), ("C77", "G77"), ("W77", "C77"))
# v0.78: D78 対 M78（悪エネルギーの + 10 と鋼エネルギーの - 10 が同じダメージに重なる）・D78 対 G77・M78 対 C77
PAIRINGS_V0_78 = (("D78", "M78"), ("D78", "G77"), ("M78", "C77"))
# v0.79: W79 対 C79・P79 対 F79・W79 対 P79（どのデッキも v0.79 のカードを中心に組む。P79 のプラスパワー・ディフェンダーは C79 のニューラのだましとるの相手にならないので、
# C79 対 P79 も加える）
PAIRINGS_V0_79 = (("W79", "C79"), ("P79", "F79"), ("W79", "P79"), ("C79", "P79"))
# v0.80: N80 対 S80（両方のデッキの v0.80 のトレーナーが相手の場・手札・サイドに向く）・N80 対 P31・S80 対 W79
PAIRINGS_V0_80 = (("N80", "S80"), ("N80", "P31"), ("S80", "W79"))
# v0.81: T81 対 D81（どうぐとスタジアムが同じ対戦にある）・T81 対 P31・D81 対 N80
PAIRINGS_V0_81 = (("T81", "D81"), ("T81", "P31"), ("D81", "N80"))
# v0.82: E82 対 L82（どちらもリサイクルエネルギー・エコロジム。相手のワザでトラッシュされるエネルギー）・E82 対 P31・L82 対 W79
PAIRINGS_V0_82 = (("E82", "L82"), ("E82", "P31"), ("L82", "W79"))
BATCHES = {"v0.28": PAIRINGS, "v0.29": PAIRINGS_V0_29, "v0.30": PAIRINGS_V0_30, "v0.31": PAIRINGS_V0_31, "v0.32": PAIRINGS_V0_32,
           "v0.33": PAIRINGS_V0_33, "v0.34": PAIRINGS_V0_34, "v0.35": PAIRINGS_V0_35, "v0.36": PAIRINGS_V0_36, "v0.37": PAIRINGS_V0_37,
           "v0.38": PAIRINGS_V0_38, "v0.39": PAIRINGS_V0_39, "v0.40": PAIRINGS_V0_40, "v0.41": PAIRINGS_V0_41, "v0.42": PAIRINGS_V0_42,
           "v0.43": PAIRINGS_V0_43, "v0.44": PAIRINGS_V0_44, "v0.45": PAIRINGS_V0_45, "v0.46": PAIRINGS_V0_46, "v0.47": PAIRINGS_V0_47,
           "v0.48": PAIRINGS_V0_48, "v0.49": PAIRINGS_V0_49, "v0.50": PAIRINGS_V0_50, "v0.51": PAIRINGS_V0_51,
           "v0.52": PAIRINGS_V0_52, "v0.53": PAIRINGS_V0_53, "v0.54": PAIRINGS_V0_54, "v0.55": PAIRINGS_V0_55,
           "v0.56": PAIRINGS_V0_56, "v0.57": PAIRINGS_V0_57, "v0.58": PAIRINGS_V0_58, "v0.59": PAIRINGS_V0_59, "v0.60": PAIRINGS_V0_60,
           "v0.61": PAIRINGS_V0_61, "v0.62": PAIRINGS_V0_62, "v0.63": PAIRINGS_V0_63,
           "v0.64": PAIRINGS_V0_64, "v0.65": PAIRINGS_V0_65, "v0.66": PAIRINGS_V0_66, "v0.67": PAIRINGS_V0_67, "v0.68": PAIRINGS_V0_68,
           "v0.69": PAIRINGS_V0_69, "v0.70": PAIRINGS_V0_70, "v0.71": PAIRINGS_V0_71, "v0.72": PAIRINGS_V0_72, "v0.73": PAIRINGS_V0_73,
           "v0.74": PAIRINGS_V0_74, "v0.75": PAIRINGS_V0_75, "v0.76": PAIRINGS_V0_76,
           "v0.77": PAIRINGS_V0_77, "v0.78": PAIRINGS_V0_78, "v0.79": PAIRINGS_V0_79, "v0.80": PAIRINGS_V0_80,
           "v0.81": PAIRINGS_V0_81, "v0.82": PAIRINGS_V0_82}
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
                 # v0.45
                 "move_opponent_energy", "take_deck_top",
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
# v0.41: v0.41 のカードのワザの中に出た結果のログ（v0.41 のカードだけで数える）。``shuffle`` はワザの効果で切ったもの（ログの ``effect``）だけ
V041_RESULT_EVENTS = ("place_damage_counters", "swap_damage_counters", "attach_energy_from_deck", "attach_energy_from_deck_none", "shuffle")
# v0.42: v0.42 のカードのワザの中に出た結果のログ（v0.42 のカードだけで数える）。``shuffle`` はワザの効果で切ったもの（ログの ``effect``）だけ
V042_RESULT_EVENTS = ("return_energy_to_hand", "place_damage_counters", "evolve", "evolve_from_deck_none", "return_in_play_to_hand", "switch_declined",
                      "shuffle")
# v0.42: v0.42 のカードの特殊能力のログ（使ったカード・自動的にはたらいたカードで数える。宣言 pokemon_power も）
V042_POWER_EVENTS = ("pokemon_power", "power_heal", "move_damage_counter", "switch", "discard_from_hand", "return_in_play_to_hand", "power_confusion",
                     "power_confusion_skipped")
# v0.43: v0.43 のカードの特殊能力のログ（使ったカードで数える。``power`` か ``effect`` に特殊能力の識別子があるもの）
V043_POWER_EVENTS = ("special_condition", "move_energy", "reveal_from_deck", "shuffle", "bench_from_deck", "recover_pokemon", "recover_pokemon_none",
                     "power_damage")
# v0.46: v0.46 のカードのワザの中に出た結果のログ（v0.46 のカードだけで数える）。``shuffle`` はワザの効果で切ったもの（ログの ``effect``）だけ
V046_RESULT_EVENTS = ("attach_energy_from_hand", "hand_to_deck", "shuffle")
# v0.47: v0.47 のカードのワザの中に出た結果のログ（v0.47 のカードだけで数える）
V047_RESULT_EVENTS = ("look_at_deck_top", "look_at_deck_top_none", "arrange_deck_top", "look_at_card", "hand_to_deck", "shuffle", "trainer_lock_added")
# v0.48: v0.48 のカードのワザの中に出た結果のログ（v0.48 のカードだけで数える。``shuffle`` はワザの効果で切ったもの（ログの ``effect``）だけ）
V048_RESULT_EVENTS = ("place_damage_counters", "shuffle")


def _attacker(state, command):
    return state.players[command.player].active


def _attack_definition(state, command):
    """v0.49: 使おうとするワザを印刷したカードの定義（``UseAttack.card``。None なら今の姿のカード。v0.48 までは、いちばん上のカード）。"""
    option = find_attack_option(state, _attacker(state, command), getattr(command, "card", None), command.attack_index)
    return state.definitions[option.card_id] if option is not None else state.card_def(_attacker(state, command).card)


def _copier(state, command):
    definition = _attack_definition(state, command)
    effect = state.effects.attack_effect(definition.id, definition.attacks[command.attack_index], definition.attacks)
    return type(effect).__name__ in ("CopyOpponentAttackEffect", "ThreeCoinPsychicPower")


def _attack_and_copied_types(state, command):
    """v0.49: 使おうとするワザの実装の型の名前と、相手のワザを自分のワザとして使うワザ（ゆびをふる・ちょうのうりょく）なら、相手の対戦ポケモンが今持つワザ
    （［サイコリンク］で持つワザ・［へんしん］の今の姿のワザも）の実装の型の名前。宣言の前の先読みは、まねるワザの選び方のすべてを試す。"""
    names = {type(_attack_effect(state, command)).__name__}
    if "RepeatReceivedAttack" in names:
        # v0.62: ピジョンのオウムがえしは、前の相手の番に受けたワザ（受けた記録の処理したワザ）を出す
        record = received_on(_attacker(state, command), state.turn_number - 1)
        if record is not None:
            definition = state.definitions[record.processed[0]]
            names.add(type(state.effects.attack_effect(definition.id, definition.attacks[record.processed[1]], definition.attacks)).__name__)
    defender = _defender(state, command)
    if _copier(state, command) and defender is not None:
        for option in available_attacks(state, defender):
            definition = state.definitions[option.card_id]
            effect = state.effects.attack_effect(definition.id, definition.attacks[option.attack_index], definition.attacks)
            names.add(type(effect).__name__)
    return names


def _defender(state, command):
    return state.players[1 - command.player].active


def _attack_effect(state, command):
    definition = _attack_definition(state, command)
    return state.effects.attack_effect(definition.id, definition.attacks[command.attack_index], definition.attacks)


# v0.31: 原典で決められない場合・エンジンの未対応で止まったワザを、場から確かめる関数（tests/v017_games.py の ``extra_stop``。止まるのが正しいなら True）
def _thunderstorm_transparency(state, command) -> bool:
    """v0.60（TS1）: 使うワザ（相手のワザとして使うワザなら、相手の対戦ポケモンのワザのどれか）がサンダーストームで、相手の控えの並びの最後でないところに、
    はたらいている「とうめい」のポケモンがいる。"""
    attacker, defender = _attacker(state, command), _defender(state, command)
    candidates = [(attacker, command.attack_index)]
    if _copier(state, command):
        candidates = [(defender, a.index) for a in state.card_def(defender.card).attacks]
    if not any(isinstance(state.effects.attack_effect(state.card_def(p.card).id, state.card_def(p.card).attacks[i], state.card_def(p.card).attacks),
                          DamageThenCoinPerOpponentBench) for p, i in candidates):
        return False
    bench = state.players[1 - command.player].bench
    return any(evasion_power(state, p) is not None for p in bench[:-1])


def _v081_tools_on(state, players, kinds) -> bool:
    """v0.81: ``players`` の場のポケモンに、効果の実装が ``kinds`` のどれかのポケモンのどうぐがついているか。"""
    from kyuura_engine import effects

    types = tuple(getattr(effects, name) for name in kinds)
    return any(effects.tool_effect_of(state, p, types) is not None for player in players for p in state.players[player].in_play())


V031_STOPS = {
    # v0.81: きぜつの判定の窓できあいのハチマキ・学習装置がほかの効果と重なる（G40）・きあいのハチマキの処理の時点（FB1）・はんげきのツメのダメージカウンターでワザを使った
    # ポケモンもきぜつし勝ち負けが変わる（C18）。どれも場にそのどうぐがついているときだけ
    "UNRESOLVED_KO_PREVENTION_ORDER": lambda st, c: _v081_tools_on(st, (0, 1), ("FocusBand", "ExpAll")),
    "UNRESOLVED_FOCUS_BAND_TIMING": lambda st, c: _v081_tools_on(st, (0, 1), ("FocusBand",)),
    "UNRESOLVED_COUNTERATTACK_DOUBLE_KNOCKOUT": lambda st, c: _v081_tools_on(st, (1 - c.player,), ("CounterClaw",)),
    # v0.68: 相手のうらのカード（マチスの秘策）を 2 枚以上、効果の対象にするコマンド（控え全員へのダメージなど）は、受け付けるかを本当のカードによらないものにできない
    # （エンジンの未対応。docs/final-pmcg-cards-v0.68.md 5.3 節）。コマンドを出したプレイヤーの相手の場に、うらのカードが 2 枚以上ある
    "UNSUPPORTED_SECRET_PLAN_IDENTITIES": lambda st, c: sum(
        1 for q in st.players[1 - c.player].in_play() if st.is_face_down(q)) >= 2,
    # v0.49: ［へんしん］のメタモンが、タイプのエネルギーの数を数える・トラッシュするワザを使う（どの色としても数えるかが決まらない。TE1）
    "UNRESOLVED_TRANSFORM_ENERGY_COUNT": lambda st, c: any_color_energy(st, _attacker(st, c)),
    "UNRESOLVED_DISCARD_ENERGY_TIMING": lambda st, c: _attacker(st, c).conditions.confused,  # HC1
    # HC4（第4弾のコダック・v0.34 のシャワーズの「みずでっぽう」）
    "UNRESOLVED_EXTRA_ENERGY_COLORLESS": lambda st, c: "ExtraEnergyDamageMixed" in _attack_and_copied_types(st, c),  # v0.62: オウムがえしで出すワザも
    # HC3。v0.80: 相手の対戦ポケモンについているエフェクトガード（効果の要素だけを受けない。ダメージの要素も無効なら同じ問い）
    "UNRESOLVED_PREVENTED_EFFECT_COIN": lambda st, c: attack_barrier(st, _defender(st, c)) is not None
    or bool(__import__("kyuura_engine.effects", fromlist=["effect_guards"]).effect_guards(st, _defender(st, c))),
    "UNRESOLVED_DESTINY_BOND_KNOCKOUT": lambda st, c: destiny_bond(st, _defender(st, c)) is not None,  # HC2
    # しっぽをふる。v0.40: すごむ（効果を与えたポケモンがバトル場にいる間）
    "ATTACK_PREVENTED": lambda st, c: (cannot_attack(st, _attacker(st, c)) is not None
                                       or cannot_attack_while_source_active(st, _attacker(st, c)) is not None),
    "UNRESOLVED_DISCARD_DECK_SHORT": lambda st, c: (  # HC6: マグマふんしゅつ（自分の山札 5 枚未満）・やまやき（相手の山札 0 枚）
        (_attack_definition(st, c).id, c.attack_index) in ((BLAINES_MAGMAR, 1), ("GD5-011", 1)) and len(st.players[c.player].deck) < 5
        or (_attack_definition(st, c).id, c.attack_index) == (MOLTRES, 0) and not st.players[1 - c.player].deck),
    # ぼーっとする（v0.49: ワザを印刷したカードで見る。［へんしん］のメタモンがヤドンと同じカードのとき）
    "NO_DAMAGE_COUNTERS": lambda st, c: _attack_definition(st, c).id == SLOWPOKE and _attacker(st, c).damage == 0,
    "UNRESOLVED_COPIED_ATTACK": lambda st, c: _copier(st, c),  # HC9
    "UNSUPPORTED_COPIED_ATTACK": lambda st, c: _copier(st, c),
    # 試す結果の数が上限（4,096）を超える（れんぞくファイヤーボール・エナジーボム・ほうでん・やまやきで、ついているエネルギーが多いとき）
    "UNSUPPORTED_PREFLIGHT_LIMIT": lambda st, c: len(_attacker(st, c).energy) >= 6,
    # v0.32: なかまをよぶ・ふえる（ベンチに空きがなければ使えない。ワザを使うための条件）
    "BENCH_FULL": lambda st, c: (type(_attack_effect(st, c)).__name__ in ("PutBasicFromDeckOntoBench", "PutTypeBasicFromDeckOntoBench",  # v0.34 のたすけをよぶ
                                                                          "PutOwnerBasicFromDeckOntoBenchOnHeads")  # v0.45 のたすけをよぶ
                                 and len(st.players[c.player].bench) >= bench_limit(st, c.player)),
    # v0.32: ヨガのポーズ（相手の控えポケモンにダメージカウンターがのっている。CD4）
    "UNRESOLVED_OPPONENT_POKEMON_COUNTERS": lambda st, c: (("DamagePlusDefenderCounters" in _attack_and_copied_types(st, c))
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
    # v0.36: くもがくれガスの「ダメージを与えた後」で、ダメージを与えない（Z23。最終ダメージが 0・受けない）。v0.41: 「ダメージを与えた後」の効果のある
    # ワザ（要素の ``after_damage``。v0.41 のひのとり・v0.18c のナツメのヤドンのぐうたらこうげきなど）すべてに広げた
    "UNRESOLVED_EFFECT_AFTER_NO_DAMAGE": lambda st, c: _deck_return_without_damage(st, c) or _after_damage_without_damage(st, c),
    # v0.37: 説明に「弱点・抵抗力」に関係なくのない自分の控えへのダメージ（ダグトリオのじしん）で、控えにワザを使うポケモンのタイプに弱点・抵抗力を
    # 持つポケモンがいる（JS1）
    "UNRESOLVED_BENCH_DAMAGE_WEAKNESS_RESISTANCE": lambda st, c: _bench_reading_matters(st, c),
    # v0.34: なきつくを受けたポケモンが、なきつくを使ったポケモンが控えにいるときに控えにダメージを与える（NK5）
    "UNRESOLVED_REDUCED_DAMAGE_BENCH_TARGET": lambda st, c: (reduced_damage_to_source(st, _attacker(st, c)) is not None
                                                             and any(p.card == reduced_damage_to_source(st, _attacker(st, c)).source_card
                                                                     for p in st.players[1 - c.player].bench)),
    # v0.38: のびるキック（相手に控えポケモンがいなければ使えない。ワザを使うための条件）
    # v0.40: ひきずりだす・さそってとかす・つまみだす（相手に控えがいなければ使えない）
    # v0.41: ゆうわく（「(相手に控えがいない時、このワザは使えない)」）
    "NO_OPPONENT_BENCH": lambda st, c: ((type(_attack_effect(st, c)).__name__ == "ChooseOpponentBenchDamage" and _attack_effect(st, c).requires_bench
                                         or type(_attack_effect(st, c)).__name__ in ("SwitchOpponentThenDamage", "ReturnOpponentActiveToDeck",
                                                                                     "SwitchOpponentActiveOnHeads"))
                                        and not st.players[1 - c.player].bench),
    # v0.40: いかりのいちげき（自分にダメージカウンターが 2 つ以上のっていなければ使えない）
    "NOT_ENOUGH_DAMAGE_COUNTERS": lambda st, c: (type(_attack_effect(st, c)).__name__ == "DamageRequiringOwnCounters"
                                                 and _attacker(st, c).damage // st.rules.damage_per_counter < _attack_effect(st, c).minimum),
    # v0.38: げきとつ（自分のワザ・相手のワザとして使うワザ）で、相手の対戦ポケモンが「ダメージを受けたとき」の効果を持つ（GK1）
    "UNRESOLVED_DAMAGE_TRIGGER_TIMING": lambda st, c: _damage_trigger_before_later_damage(st, c),
    # v0.41: ダメージシフト・チェンジダメージ（自分のワザ・相手のワザとして使うワザ）で、相手の対戦ポケモンが「ワザをうけない」状態・はたらいている
    # 「とうめい」（CX1）
    "UNRESOLVED_COUNTER_TRANSFER_PROTECTED": lambda st, c: _counter_transfer_protected(st, c),
    # v0.44: ラッキーたまご（自分のワザ・相手のワザとして使うワザ）で、「うら」のとき手札が 2 枚より少ない（FC1。山札にもどすカードが足りない）
    # v0.46: かくさんソーラービーム（相手の控えポケモン 2 匹）で、相手の控えが 1 匹（FC1）
    "UNRESOLVED_STATED_CARDS_SHORT": lambda st, c: _hand_return_short(st, c) or _exact_bench_short(st, c) or _surprise_short(st, c),
    # v0.44: 場に出てから 1 度しか使えないワザ（ネギでたたく・りゅうのきおく・ひっさつばり）を、このポケモンがもう使った（場のポケモンの記録 ``attacks_used_once``）
    "ATTACK_ALREADY_USED": lambda st, c: (_attacker(st, c).card, c.attack_index) in _attacker(st, c).attacks_used_once,
    # v0.45: ワザを使うポケモンが手順 4 の効果を 2 つ以上受けている（AC13。スミをかけるの「それ以後」の効果が重なる）
    # v0.60: カスミのギャラドスの［はんこう］も手順 4 の効果として数える
    "UNRESOLVED_MULTIPLE_ATTACK_CHECKS": lambda st, c: len(attack_coin_checks(st, _attacker(st, c))) + len(attack_rebellion_powers(st, _attacker(st, c))) >= 2,
    # v0.60: サンダーストーム（自分のワザ・相手のワザとして使うワザ）で、はたらいている「とうめい」の相手の控えポケモンのあとにほかの控えがいる（TS1）
    "UNRESOLVED_BENCH_COIN_TRANSPARENCY_ORDER": lambda st, c: _thunderstorm_transparency(st, c),
    # v0.60: 控えにもダメージ・効果を与えるワザ（どくのきりなど）で、相手の場に、はたらいている「とうめい」のポケモンが 2 匹以上いる（T27。v0.60 の M60 で初めて起こった）
    "UNRESOLVED_TRANSPARENCY_COIN_ORDER": lambda st, c: sum(evasion_power(st, p) is not None for p in st.players[1 - c.player].in_play()) >= 2,
    # v0.45: 相手の対戦ポケモンが返す効果（クロスカウンター。ほのおのかべ・こうらがえしも）を持ち、そろってきぜつしうる（W24・S37）
    "UNRESOLVED_RETALIATION_DOUBLE_KNOCKOUT": lambda st, c: retaliation(st, _defender(st, c)) is not None,
    # v0.48: ［へんしょく］で変えた色の読み方が 2 つある（使った番のあと・ベンチにもどったあと・この力が消えている）場のポケモンがいる（VS1。読み方で結果が変わるときだけ
    # 止まる。止まらない場合は場から確かめられないので、止まったときに読み方が 2 つあるポケモンがいることだけを確かめる）
    "UNRESOLVED_SHIFT_COLOR_DURATION": lambda st, c: any(len(type_readings(st, p)) > 1 for pl in st.players for p in pl.in_play()),
    # v0.50: たいかビーム（自分のワザ・相手のワザとして使うワザ）で、自分・相手の場の進化ポケモンがどれも「ばける」でのせたカードのポケモン（DV5）
    "UNRESOLVED_DEVOLUTION_TARGET_DISGUISED": lambda st, c: _all_devolution_targets_disguised(st, c),
    # v0.48: テクスチャー1（相手の対戦ポケモンに弱点がない）・テクスチャー2（自分に抵抗力がない）。相手のワザとして使うワザなら、相手の対戦ポケモンのワザのどれか（PG1）
    "UNRESOLVED_CHANGE_ABSENT_WEAKNESS_RESISTANCE": lambda st, c: _conversion_absent(st, c),
    # v0.56: カスミの +20 がはたらくワザを使うポケモンが、自分にもダメージを与えるワザを使う（+20 を当てはめるかで結果が変わるときだけ止まる。MS1）
    "UNRESOLVED_MISTY_SELF_DAMAGE": lambda st, c: bool(trainer_attack_damage_bonuses(st, _attacker(st, c))),
    # v0.56: キョウのどくがはたらくワザを使うポケモンが、同じワザで受けるダメージの違う特殊などくを与える（KG1）
    "UNRESOLVED_KOGA_POISON_ORDER": lambda st, c: bool(trainer_poison_effects(st, _attacker(st, c))),
    # v0.62: ドリルホール（前の自分の番に、このカードが「あながくれ」を使っていなければ使えない。ワザを使うための条件）
    "PREVIOUS_ATTACK_NOT_USED": lambda st, c: (type(_attack_effect(st, c)).__name__ == "DamageIfUsedAttackLastTurn"
                                               and used_attack_last_turn(st, _attacker(st, c), 0, "あながくれ") != "used"),
    # v0.62: オウムがえし（ピジョン）: 受けた「ワザ」が決まらない（ダメージだけを受けなかった・受けたワザが相手のワザを自分のワザとして使ったもの。MM1）・
    # 出すワザの必要なエネルギー・条件（MM2）・出すワザがエンジンの未対応
    "UNRESOLVED_MIRROR_MOVE_RECEIVED_ATTACK": lambda st, c: _v062_received(st, c, lambda r: bool(r.voided) or r.declared != r.processed),
    "UNRESOLVED_MIRROR_MOVE_ATTACK_CONDITIONS": lambda st, c: _v062_received(st, c, lambda r: True),
    "UNSUPPORTED_MIRROR_MOVE_ATTACK": lambda st, c: _v062_received(st, c, lambda r: True),
    # v0.62: オウムがえし（オニスズメ）: 続く効果（OM1）・ワザ以外で受けた（OM2）・与えるのが未対応の効果
    "UNRESOLVED_MIRROR_MOVE_LASTING_EFFECT": lambda st, c: _v062_received(st, c, lambda r: bool(set(r.reached) & LASTING_RECEIVED_ELEMENTS)),
    "UNRESOLVED_MIRROR_MOVE_NON_ATTACK": lambda st, c: other_received_on(_attacker(st, c), st.turn_number - 1),
    "UNSUPPORTED_MIRROR_MOVE_EFFECT": lambda st, c: _v062_received(st, c, lambda r: bool(set(r.reached) - REFLECTABLE_RECEIVED_ELEMENTS)),
    # v0.65: 変わり身の術のついた相手の対戦ポケモンに、手順 4・5・クチバシティジムのコインを投げるワザを使う（NT1）・変わり身の術のついたポケモンを山札・手札にもどす（NT2）
    "UNRESOLVED_NINJA_TRICK_ATTACK_COIN_ORDER": lambda st, c: _v065_tricked(st, 1 - c.player),
    "UNRESOLVED_NINJA_TRICK_LEAVES_WITH_POKEMON": lambda st, c: _v065_tricked(st, c.player) or _v065_tricked(st, 1 - c.player),
}


def _v065_tricked(state, player) -> bool:
    active = state.players[player].active
    return active is not None and any(state.cards[t.card].card_id == KOGAS_NINJA_TRICK for t in active.trainers)


def _v062_received(state, command, test) -> bool:
    """v0.62: 使うワザがオウムがえし（ピジョン・オニスズメ）で、前の相手の番にバトル場のポケモン（このカード）が受けた記録があり、``test`` に当たる。"""
    if type(_attack_effect(state, command)).__name__ not in ("RepeatReceivedAttack", "ReflectReceivedDamageAndEffects"):
        return False
    record = received_on(_attacker(state, command), state.turn_number - 1)
    return record is not None and test(record)


def _all_devolution_targets_disguised(state, command):
    """DV5（v0.50）: 使うワザ（相手のワザとして使うワザなら、相手の対戦ポケモンのワザのどれか）がたいかビームで、自分・相手の場の進化ポケモンがどれも「ばける」でのせた
    カードのポケモン。"""
    if "DevolveChosenPokemon" not in _attack_and_copied_types(state, command):
        return False
    candidates = devolution_candidates(state, (command.player, 1 - command.player))
    return bool(candidates) and all(devolution_forbidden(state, state.find_pokemon(pid)[1]) for pid in candidates)


def _conversion_absent(state, command):
    """PG1（v0.48）: 使うワザ（相手のワザとして使うワザなら、相手の対戦ポケモンのワザのどれか）が、弱点を変えるワザで相手の対戦ポケモンに弱点がない・抵抗力を変える
    ワザで自分に抵抗力がない。"""
    attacker, defender = _attacker(state, command), _defender(state, command)
    candidates = [(attacker, command.attack_index)]
    if _copier(state, command):
        candidates = [(defender, a.index) for a in state.card_def(defender.card).attacks]
    for pokemon, index in candidates:
        definition = state.card_def(pokemon.card)
        name = type(state.effects.attack_effect(definition.id, definition.attacks[index], definition.attacks)).__name__
        if (name == "ChangeOpponentWeakness" and weakness_of(state, defender) is None) or (
                name == "ChangeOwnResistance" and resistance_of(state, attacker)[0] is None):
            return True
    return False


def _hand_return_short(state, command):
    """FC1（v0.44）: 使うワザ（相手のワザとして使うワザなら、相手の対戦ポケモンのワザのどれか）が「うら」で手札をもどすワザ（``CoinDrawOrReturnHandToDeck``）で、
    手札がもどす枚数より少ない。"""
    attacker = _attacker(state, command)
    candidates = [(attacker, command.attack_index)]
    if _copier(state, command):
        defender = _defender(state, command)
        candidates = [(defender, a.index) for a in state.card_def(defender.card).attacks]
    for pokemon, index in candidates:
        definition = state.card_def(pokemon.card)
        effect = state.effects.attack_effect(definition.id, definition.attacks[index], definition.attacks)
        if type(effect).__name__ == "CoinDrawOrReturnHandToDeck" and len(state.players[command.player].hand) < effect.count:
            return True
    return False


def _exact_bench_short(state, command):
    """FC1（v0.46）: 使うワザ（相手のワザとして使うワザなら、相手の対戦ポケモンのワザのどれか）が、相手の控えポケモンを決まった数選ぶワザ
    （``DamageThenExactBenchTargets``。かくさんソーラービーム）で、相手の控えが 1 匹以上その数より少ない。"""
    attacker = _attacker(state, command)
    candidates = [(attacker, command.attack_index)]
    if _copier(state, command):
        defender = _defender(state, command)
        candidates = [(defender, a.index) for a in state.card_def(defender.card).attacks]
    bench = len(state.players[1 - command.player].bench)
    for pokemon, index in candidates:
        definition = state.card_def(pokemon.card)
        effect = state.effects.attack_effect(definition.id, definition.attacks[index], definition.attacks)
        if type(effect).__name__ == "DamageThenExactBenchTargets" and 0 < bench < effect.targets:
            return True
    return False


def _surprise_short(state, command):
    """FC1（v0.47）: 使うワザ（相手のワザとして使うワザなら、相手の対戦ポケモンのワザのどれか）が、相手の手札を 1 枚見て山札にもどさせるワザ
    （``LookOpponentHandCardToDeck``。おどろかす）で、相手の手札が 0 枚。"""
    attacker = _attacker(state, command)
    candidates = [(attacker, command.attack_index)]
    if _copier(state, command):
        defender = _defender(state, command)
        candidates = [(defender, a.index) for a in state.card_def(defender.card).attacks]
    for pokemon, index in candidates:
        definition = state.card_def(pokemon.card)
        effect = state.effects.attack_effect(definition.id, definition.attacks[index], definition.attacks)
        if type(effect).__name__ == "LookOpponentHandCardToDeck" and not state.players[1 - command.player].hand:
            return True
    return False


def _counter_transfer_protected(state, command):
    """CX1（v0.41）: 使うワザ（相手のワザとして使うワザなら、相手の対戦ポケモンのワザのどれか）が、ダメージカウンターを相手にのせる・取り替えるワザで、
    相手の対戦ポケモンが「ワザをうけない」状態か、はたらいている「とうめい」を持つ。"""
    attacker, defender = _attacker(state, command), _defender(state, command)
    candidates = [(attacker, command.attack_index)]
    if _copier(state, command):
        candidates = [(defender, a.index) for a in state.card_def(defender.card).attacks]
    names = set()
    for pokemon, index in candidates:
        definition = state.card_def(pokemon.card)
        names.add(type(state.effects.attack_effect(definition.id, definition.attacks[index], definition.attacks)).__name__)
    protected = attack_barrier(state, defender) is not None or working_evasion_power(state, defender.pokemon_id) is not None
    return bool(names & {"MoveOwnCountersToOpponent", "SwapCountersOnHeads"}) and protected


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
    """ワザ（相手のワザとして使うワザなら、相手の対戦ポケモンのワザ）のうち、くもがくれガス（``DamageThenReturnSelfToDeckOnHeads``）・v0.41 のひのとり
    （``DamageThenReturnSelfToDeckOnTails``）の (カード id, ワザ)（v0.36）。"""
    candidates = [(_attacker(state, command), command.attack_index)]
    if _copier(state, command):
        defender = _defender(state, command)
        candidates = [(defender, a.index) for a in state.card_def(defender.card).attacks]
    found = []
    for pokemon, index in candidates:
        definition = state.card_def(pokemon.card)
        effect = state.effects.attack_effect(definition.id, definition.attacks[index], definition.attacks)
        if type(effect).__name__ in ("DamageThenReturnSelfToDeckOnHeads", "DamageThenReturnSelfToDeckOnTails",  # v0.41: ひのとり（「うら」）
                                     "DamageThenReturnSelfToHandOnHeads"):  # v0.44: スターブーメラン（手札にもどす。RD9 と同じ問い）
            found.append((definition.id, definition.attacks[index]))
    return found


def _deck_return_preview(state, command):
    """くもがくれガスの相手へのダメージの最終ダメージ（状態を変えない計算。``effects.preview_attack_damage``。受けないなら None）の一覧。"""
    attacker = _attacker(state, command)
    return [preview_attack_damage(state, AttackUse(command.player, attacker.pokemon_id, E_AttackKey(card_id, attack.index)), "opponent_active",
                                  attack.damage)
            for card_id, attack in _deck_return_attacks(state, command)]


def _after_damage_without_damage(state, command):
    """Z23（v0.41）: 使うワザ（相手のワザとして使うワザなら、相手の対戦ポケモンのワザのどれか）が「ダメージを与えた後」の効果（要素の並びの
    ``after_damage``）を持ち、相手の対戦ポケモンへの最終ダメージ（状態を変えない計算 ``effects.preview_attack_damage``）が 0 以下か、受けない。"""
    attacker = _attacker(state, command)
    candidates = [(attacker, command.attack_index)]
    if _copier(state, command):
        defender = _defender(state, command)
        candidates = [(defender, a.index) for a in state.card_def(defender.card).attacks]
    for pokemon, index in candidates:
        definition = state.card_def(pokemon.card)
        attack = definition.attacks[index]
        effect = state.effects.attack_effect(definition.id, attack, definition.attacks)
        try:
            program = compile_attack(effect)
        except Exception:  # noqa: BLE001  要素の並びのない実装（v0.13 の約束）は数えない
            continue
        if any(getattr(element, "after_damage", None) is not None for element in program):
            amount = preview_attack_damage(state, AttackUse(command.player, attacker.pokemon_id, E_AttackKey(definition.id, index)), "opponent_active",
                                           attack.damage)
            # v0.60: 相手の対戦ポケモンが「かげぶんしん」の効果を持てば、そのコインの「うら」でダメージを受けない（Z23-c と同じく受けない場合がある）
            if amount is None or amount <= 0 or tails_damage_guard(_defender(state, command)) is not None:
                return True
            if working_evasion_power(state, _defender(state, command).pokemon_id) is not None:
                return True  # v0.74: 相手の対戦ポケモンの「とうめい」のコインで受けない場合がある（Z23-c。v0.73 までの組では、とうめいの相手にこのワザを使う場面がなかった）
    return False


def _deck_return_with_knockout(state, command):
    defender = _defender(state, command)
    left = max_hp(state, defender) - defender.damage
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
    cost = retreat_cost(state, player).maximum  # v0.46: 常にはたらく特殊能力で変わった数（変わらなければ印刷の数）
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
    if use is None or (use[2] not in V0_31 and use[2] not in V0_71):  # v0.71: 再録のカード（プロモのリザードンの「ほのおのうず」など）も同じ答え方
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


def _v076_decision(state, counts):
    """v0.76 のカードのワザの決定への答え（v0.76 のカードのワザでないときは元の手順に任せる）: ドわすれ・かなしばり（SELECT_OPPONENT_ATTACK）は、決定のたびに選べるワザを
    前から順にずらして選ぶ。原典で決められない選択（``unresolved_choices``）は選ばない。"""
    d = state.decision
    if d is None or d.resume != "attack" or d.kind != SELECT_OPPONENT_ATTACK:
        return None
    use = d.context_value("use")
    copied = d.context_value("copied")
    card = copied[0] if copied else (use[2] if use is not None else None)
    if card not in V0_76 + V0_77:
        return None
    blocked = set(d.context_value("unresolved_choices") or ())
    options = tuple(o for o in d.options if o not in blocked)
    if not options:
        return None
    prefix = "v076" if card in V0_76 else "v077"  # v0.77: ウパー（neo1-026）のドわすれも同じ手順で答える（v0.76 のカードの数え方は変えない）
    counts[f"{prefix}_select_opponent_attack"] += 1
    pick = options[(counts[f"{prefix}_select_opponent_attack"] - 1) % len(options)]
    counts[f"{prefix}_select_opponent_attack_{pick}"] += 1
    return ResolveDecision(d.player, d.id, (pick,))


def _v075_decision(state, counts):
    """v0.75 のカードのワザの決定への答え（v0.75 のカードのワザでないときは元の手順に任せる）: くらげのむれ（SEARCH_DECK。好きなだけ）は 決定のたびに すべて・0 枚・1 枚 を
    順に選ぶ。たすけをよぶ・じゅうでん（0〜1 枚）は選ぶ・選ばないを交互にする。しおまねき・エネルギーきゅうしゅう（「最大」。0 枚は HC7 で止まるので選ばない）は 1 枚から
    最大まで順に選ぶ。ほかの決定（ちょうど決まった数）は選べるものの前から。原典で決められない選択（``unresolved_choices``）は選ばない。"""
    d = state.decision
    if d is None or d.resume != "attack":
        return None
    use = d.context_value("use")
    copied = d.context_value("copied")
    card = copied[0] if copied else (use[2] if use is not None else None)
    if card not in V0_75:
        return None
    blocked = set(d.context_value("unresolved_choices") or ())
    options = tuple(o for o in d.options if o not in blocked)
    key = f"v075_{d.kind}"
    counts[key] += 1
    n = counts[key]
    if d.kind == SEARCH_DECK and d.max_choices > 1:
        pick = (options, (), options[:1])[n % 3]
    elif d.min_choices == 0 and d.max_choices == 1:
        pick = options[:1] if n % 2 else ()
    elif d.min_choices == 0:
        pick = options[:1 + (n - 1) % d.max_choices]
    else:
        pick = options[:d.min_choices]
    counts[f"{key}_{len(pick)}"] += 1
    return ResolveDecision(d.player, d.id, tuple(pick))


def _v072_decision(state, counts):
    """v0.72 のカードのワザの決定への答え: きゅうけつの取りのぞくか（OPTIONAL_DRAIN）・おつきみの山札のカード（SEARCH_DECK。0〜1 枚）は、決定のたびに選ぶ・選ばないを
    交互にする。デンキとばしのはがすカード（MOVE_ENERGY）・つける控え（ATTACH_TO_BENCH）は、選べるものの最初。ほかの決定は元の手順に任せる。"""
    d = state.decision
    if d is None or d.resume != "attack":
        return None
    use = d.context_value("use")
    if use is None or use[2] not in V0_72:
        return None
    if d.kind in (OPTIONAL_DRAIN, SEARCH_DECK) and d.min_choices == 0:
        counts[f"v072_{d.kind}"] += 1
        take = counts[f"v072_{d.kind}"] % 2 == 1
        counts[f"v072_{d.kind}_{'take' if take else 'decline'}"] += 1
        return ResolveDecision(d.player, d.id, tuple(d.options[:1]) if take else ())
    if d.kind in (MOVE_ENERGY, ATTACH_TO_BENCH):
        counts[f"v072_{d.kind}"] += 1
        return ResolveDecision(d.player, d.id, tuple(d.options[:1]))
    return None


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


def _v041_decision(state, counts):
    """v0.41 のカードのワザの決定への答え。ミラクルかふん（``SELECT_SPECIAL_CONDITION``）は、決定のたびに ねむり・マヒ・こんらん・どく を順に選ぶ（原典で
    決められない選択 ``unresolved_choices`` は選ばない）。ひなたぼっこ（``ATTACH_FROM_DECK``。0〜1 枚）は、決定のたびに 1 枚つける・1 枚つける・つけない を順に
    選ぶ（つけない選択も起こす）。さそうかおり・ゆうわくの控えの選択は元の手順のまま（1 つ目の選べるもの）。"""
    d = state.decision
    if d is None or d.resume != "attack":
        return None
    use = d.context_value("use")
    if use is None or use[2] not in V0_41:
        return None
    if d.kind == SELECT_SPECIAL_CONDITION:
        blocked = set(d.context_value("unresolved_choices", ()))
        options = [o for o in d.options if o not in blocked]
        choice = options[counts["v041_condition"] % len(options)]
        counts["v041_condition"] += 1
        counts[f"v041_condition_{choice}"] += 1
        return ResolveDecision(d.player, d.id, (choice,))
    if d.kind == ATTACH_FROM_DECK:
        attach = counts["v041_sunbath"] % 3 != 2
        counts["v041_sunbath"] += 1
        counts[f"v041_sunbath_{'attach' if attach else 'decline'}"] += 1
        return ResolveDecision(d.player, d.id, tuple(d.options[:1]) if attach else ())
    return None


def _v042_decision(state, counts):
    """v0.42 のカードのワザ・特殊能力の決定への答え（原典で決められない選択 ``unresolved_choices`` は選ばない）。

    - 特殊能力（再開先 ``power``）: ヒーリングはダメージのいちばん多いポケモン、かおりのわなは残り HP のいちばん少ない相手の控え、ぶっしつこうかんは手札に基本
      エネルギーカードが 2 枚以上あればその最後の 1 枚、なければ手札の最後のカード
    - よいおこない: ダメージのいちばん多い相手のポケモン → とりのぞく数は 1・のっている数すべて・半分（切り上げ）を順に
    - テレポートブラスト（0〜1 匹）: 入れ替える（最初の控え）・入れ替えない を順に。ナイトヘッド: 残り HP のいちばん少ない控え
    - つきのちから: 山札の進化カードは 1 つ目、進化させるポケモンはワザを使ったポケモン・ほかのポケモン を順に
    - ようせいのきせき（1 匹以上）: ダメージのいちばん多いポケモン 1 匹・控えのポケモンすべて を順に（控えがいなければ 1 匹）
    - エネループ: 1 つ目のエネルギーカード"""
    d = state.decision
    if d is None or d.resume not in ("attack", "power"):
        return None
    use = d.context_value("use")
    if use is None or use[2] not in V0_42:
        return None
    blocked = set(d.context_value("unresolved_choices", ()))
    options = [o for o in d.options if o not in blocked]
    card_id = use[2]

    def answer(choices, label):
        counts[f"v042_{label}"] += 1
        return ResolveDecision(d.player, d.id, tuple(choices))

    def damage(pid):
        return state.find_pokemon(pid)[1].damage

    def remaining(pid):
        pokemon = state.find_pokemon(pid)[1]
        return max_hp(state, pokemon) - pokemon.damage

    if d.resume == "power":
        if card_id == VILEPLUME and d.kind == SELECT_POKEMON:
            return answer((max(options, key=lambda o: (damage(o), -options.index(o))),), "healing_target")
        if card_id == ERIKAS_VICTREEBEL and d.kind == SELECT_POKEMON:
            return answer((min(options, key=lambda o: (remaining(o), options.index(o))),), "sweet_trap_target")
        if card_id == DARK_KADABRA and d.kind == DISCARD_FROM_HAND:
            energy = [u for u in options if state.card_def(u).is_basic_energy]
            choice = energy[-1] if len(energy) >= 2 else options[-1]
            return answer((choice,), f"matter_exchange_{'energy' if choice in energy else 'other'}")
        return None
    if card_id == SABRINAS_JYNX and d.kind == SELECT_POKEMON:
        return answer((max(options, key=lambda o: (damage(o), -options.index(o))),), "good_deed_target")
    if card_id == SABRINAS_JYNX and d.kind == REMOVE_COUNTERS:
        top = max(options)
        choice = (1, top, (top + 1) // 2)[counts["v042_good_deed_count"] % 3]
        counts["v042_good_deed_count"] += 1
        return answer((max(1, choice),), f"good_deed_remove_{'all' if choice == top else 'some'}")
    if card_id == DARK_ALAKAZAM and d.kind == SELECT_POKEMON:
        switch = counts["v042_teleport"] % 2 == 0
        counts["v042_teleport"] += 1
        return answer(tuple(options[:1]) if switch else (), f"teleport_{'switch' if switch else 'decline'}")
    if card_id == GENGAR and d.kind == SELECT_POKEMON:
        return answer((min(options, key=lambda o: (remaining(o), options.index(o))),), "night_head_target")
    if card_id == ERIKAS_CLEFAIRY and d.kind == SEARCH_DECK:
        return answer(tuple(options[:1]), "moon_power_card")
    if card_id == ERIKAS_CLEFAIRY and d.kind == SELECT_POKEMON:
        self_first = counts["v042_moon_target"] % 2 == 0
        counts["v042_moon_target"] += 1
        choice = use[1] if self_first and use[1] in options else next((o for o in options if o != use[1]), options[0])
        return answer((choice,), f"moon_power_{'self' if choice == use[1] else 'other'}")
    if card_id == ERIKAS_CLEFABLE and d.kind == SELECT_POKEMON:
        bench = [p.pokemon_id for p in state.players[d.player].bench if p.pokemon_id in options]
        single = counts["v042_fairy"] % 2 == 0 or not bench
        counts["v042_fairy"] += 1
        choices = (max(options, key=lambda o: (damage(o), -options.index(o))),) if single else tuple(bench)
        return answer(choices, f"fairy_{'single' if single else 'bench'}")
    if card_id == SABRINAS_ABRA and d.kind == RETURN_ENERGY:
        return answer(tuple(options[:1]), "energy_loop")
    return None


def _v042_power(state, tried, counts):
    """v0.42 の宣言する特殊能力を使う手順（使えない特殊状態・この番に使ったものは使わない。拒否を起こさない）:

    - ヒーリング（ラフレシア）: 自分の場にダメージカウンターがのったポケモンがいれば
    - へんなこうどう（ヤドラン）: ほかの自分のポケモン（バトル場を先に）にカウンターがあり、ヤドランに 1 つのせても残り HP が 20 以上なら（1 番に 2 回まで）
    - のろい（ゲンガー）: 相手の場に 2 匹以上いて、カウンターがのったポケモンがいれば。のせる先は残り HP のいちばん少ない別のポケモン（きぜつさせることもある）
    - かけつける（ベンチのカイリュー）: 自分の対戦ポケモンにダメージがあれば
    - かおりのわな（エリカのウツボット）: 相手に控えがいれば
    - ぶっしつこうかん（わるいユンゲラー）: 手札があれば
    - おくびょう（メノクラゲ）: 場に出した番でなく、ダメージがあり、バトル場なら控えがいれば"""
    player = state.current_player
    p = state.players[player]
    opponent = state.players[1 - player]
    per = state.rules.damage_per_counter

    def free(pokemon):
        conditions = pokemon.conditions
        return not (conditions.asleep or conditions.paralyzed or conditions.confused)

    def used(pokemon):
        return (pokemon.pokemon_id, 0) in state.power_uses_this_turn

    def remaining(pokemon):
        return max_hp(state, pokemon) - pokemon.damage

    for pokemon in p.in_play():
        if state.is_face_down(pokemon):
            continue  # v0.67
        card_id = state.card_def(pokemon.card).id
        if card_id not in V0_42 or not free(pokemon):
            continue
        pid = pokemon.pokemon_id
        if card_id == VILEPLUME and not used(pokemon) and any(q.damage >= per for q in p.in_play()):
            counts["v042_power_healing"] += 1
            return UsePokemonPower(player, pid, 0)
        if card_id == SLOWBRO and sum(1 for t in tried if isinstance(t, tuple) and t[:2] == ("v042_strange", pid)) < 2 \
                and remaining(pokemon) - per >= 20:
            sources = [q for q in p.in_play() if q is not pokemon and q.damage >= per]
            if sources:
                tried.add(("v042_strange", pid, len(tried)))
                counts["v042_power_strange_behavior"] += 1
                return UsePokemonPower(player, pid, 0, source=sources[0].pokemon_id)
        if card_id == GENGAR and not used(pokemon):
            targets = opponent.in_play()
            sources = [q for q in targets if q.damage >= per]
            if len(targets) >= 2 and sources:
                source = max(sources, key=lambda q: q.damage)
                target = min((q for q in targets if q is not source), key=remaining)
                counts["v042_power_curse"] += 1
                counts[f"v042_power_curse_{'ko' if remaining(target) <= per else 'move'}"] += 1
                return UsePokemonPower(player, pid, 0, source=source.pokemon_id, target=target.pokemon_id)
        if card_id == DRAGONITE and pokemon is not p.active and not used(pokemon) and p.active is not None and p.active.damage > 0:
            counts["v042_power_step_in"] += 1
            return UsePokemonPower(player, pid, 0)
        if card_id == ERIKAS_VICTREEBEL and not used(pokemon) and opponent.bench:
            counts["v042_power_sweet_trap"] += 1
            return UsePokemonPower(player, pid, 0)
        if card_id == DARK_KADABRA and not used(pokemon) and p.hand:
            counts["v042_power_matter_exchange"] += 1
            return UsePokemonPower(player, pid, 0)
        if card_id == TENTACOOL and pokemon.played_turn < state.turn_number and pokemon.damage > 0 and (pokemon is not p.active or p.bench):
            counts[f"v042_power_cowardice_{'active' if pokemon is p.active else 'bench'}"] += 1
            return UsePokemonPower(player, pid, 0)
    return None


def _v043_decision(state, counts):
    """v0.43 のカードのワザ・特殊能力の決定への答え（原典で決められない選択 ``unresolved_choices`` は選ばない）。

    - 場に出たときの特殊能力の使う機会（``ENTRY_POWER``）: 使う（4 回に 1 回は使わない）。使うことを選ぶと止める場合（PW3）は使わない
    - こっそりかみつく: 残り HP のいちばん少ない相手のポケモン。つりあげる: 選べるだけ（最大 3 枚）。てしたをよぶ: 選べるだけ・1 枚 を順に
    - ようぶんきゅうしゅう: 1 枚・2 枚（選べるだけ）を順に。エナジーチャージ: 選べるものすべて。しんかのひかり: 1 つ目
    - ふらふらとぶ: 相手の対戦ポケモン・残り HP のいちばん少ない控え を順に（控えがいなければ対戦ポケモン）。のびるつる: 残り HP のいちばん少ない控え"""
    d = state.decision
    if d is None or d.resume not in ("attack", "power"):
        return None
    use = d.context_value("use")
    if use is None or use[2] not in V0_43:
        return None
    blocked = set(d.context_value("unresolved_choices", ()))
    options = [o for o in d.options if o not in blocked]
    card_id = use[2]

    def answer(choices, label):
        counts[f"v043_{label}"] += 1
        return ResolveDecision(d.player, d.id, tuple(choices))

    def remaining(pid):
        pokemon = state.find_pokemon(pid)[1]
        return max_hp(state, pokemon) - pokemon.damage

    if d.kind == ENTRY_POWER:
        if not options:
            return answer((), f"entry_declined_unresolved_{d.context_value('unresolved_code')}")
        decline = counts["v043_entry_seen"] % 4 == 3
        counts["v043_entry_seen"] += 1
        return answer(() if decline else tuple(options), f"entry_{'declined' if decline else 'used'}_{card_id}")
    if d.resume == "power":
        if card_id == DARK_GOLBAT and d.kind == SELECT_POKEMON:
            choice = min(options, key=lambda o: (remaining(o), options.index(o)))
            return answer((choice,), f"sneak_attack_{'ko' if remaining(choice) <= 10 else 'damage'}")
        if card_id == DARK_SLOWBRO and d.kind == RECOVER_POKEMON:
            return answer(tuple(options[:d.max_choices]), f"reel_in_{min(len(options), d.max_choices)}")
        if card_id == DARK_DRAGONITE and d.kind == BENCH_FROM_DECK:
            count = d.max_choices if counts["v043_summon"] % 2 == 0 else 1
            counts["v043_summon"] += 1
            return answer(tuple(options[:count]), f"summon_{count}")
        if card_id == ERIKAS_BELLSPROUT_40 and d.kind == MOVE_ENERGY:
            count = min(d.max_choices, 1 + counts["v043_soak"] % 2)
            counts["v043_soak"] += 1
            return answer(tuple(options[:count]), f"soak_up_{count}")
        if card_id == LT_SURGES_MAGNETON and d.kind == MOVE_ENERGY:
            return answer(tuple(options), f"energy_charge_{len(options)}")
        if card_id == DARK_DRAGONAIR and d.kind == SEARCH_DECK:
            return answer(tuple(options[:1]), "evolutionary_light")
        return None
    if card_id == DARK_GOLBAT and d.kind == SELECT_POKEMON:
        active = state.players[1 - d.player].active.pokemon_id
        bench = [o for o in options if o != active]
        active_turn = counts["v043_flitter"] % 2 == 0 or not bench
        counts["v043_flitter"] += 1
        choice = active if active_turn and active in options else min(bench, key=lambda o: (remaining(o), bench.index(o)))
        return answer((choice,), f"flitter_{'active' if choice == active else 'bench'}")
    if card_id == ERIKAS_BELLSPROUT_40 and d.kind == SELECT_POKEMON:
        return answer((min(options, key=lambda o: (remaining(o), options.index(o))),), "stretch_vine")
    return None


def _v044_decision(state, counts):
    """v0.44 のカードのワザ・特殊能力・トレーナーの決定への答え（原典で決められない選択 ``unresolved_choices`` は選ばない。0 枚（GS1）・足りない枚数（FC1）を選ばない）。

    - サカキ: 今の番に場に出した・進化したサカキのポケモンで、手札にそのポケモンから進化するカードがあるもの（なければ 1 つ目）
    - ［ボスをよぶ］の使う機会: 使う（その局の 2 回目ごとに使わない。山札にサカキがない（PW3）ときは使わない）。山札のサカキ: 1 つ目。［うか］: 選べる 1 つ目
    - じめんにもぐる・こばんなげ: 相手の対戦ポケモン・残り HP のいちばん少ない控え を順に。りゅうのたつまき: 相手の控えの 最後・最初 を順に
    - おつかい・たきのぼりしんか: 選ぶ（4 回に 1 回は選ばない）。てじな: 1・2・3 枚を順に（山札の基本エネルギーカードが足りる枚数まで）、そのあと選べるだけの基本エネルギーカード。
      ラッキーたまご: 手札の 1 つ目から 2 枚。わるいいたずら: 相手のトラッシュの 1 つ目"""
    d = state.decision
    if d is None:
        return None
    use = d.context_value("use")
    if use is None:
        return None
    blocked = set(d.context_value("unresolved_choices", ()))
    options = [o for o in d.options if o not in blocked]

    def answer(choices, label):
        counts[f"v044_{label}"] += 1
        return ResolveDecision(d.player, d.id, tuple(choices))

    def remaining(pid):
        pokemon = state.find_pokemon(pid)[1]
        return max_hp(state, pokemon) - pokemon.damage

    if d.resume == "trainer":
        if use[2] != GIOVANNI or d.kind != SELECT_POKEMON:
            return None
        hand = state.players[d.player].hand
        ready = [o for o in options if any(state.card_def(u).evolves_from == state.card_def(state.find_pokemon(o)[1].card).name_ja for u in hand)
                 and state.find_pokemon(o)[1].current_form_turn >= state.turn_number]
        return answer((ready[0] if ready else options[0],), f"giovanni_{'ready' if ready else 'other'}")
    if d.resume not in ("attack", "power") or use[2] not in V0_44:
        return None
    card_id = use[2]
    if d.kind == ENTRY_POWER:
        if not options:
            return answer((), f"entry_declined_unresolved_{d.context_value('unresolved_code')}")
        decline = counts["v044_entry_seen"] % 2 == 1
        counts["v044_entry_seen"] += 1
        return answer(() if decline else tuple(options), f"entry_{'declined' if decline else 'used'}")
    if d.resume == "power":
        if d.kind == SEARCH_DECK and options:
            return answer(options[:1], f"power_search_{card_id}")
        return None
    if card_id in (ROCKET_DIGLETT, ROCKET_MEOWTH) and d.kind == SELECT_POKEMON:
        active = state.players[1 - d.player].active.pokemon_id
        bench = [o for o in options if o != active]
        active_turn = counts["v044_choose_target"] % 2 == 0 or not bench
        counts["v044_choose_target"] += 1
        choice = active if active_turn and active in options else min(bench, key=lambda o: (remaining(o), bench.index(o)))
        return answer((choice,), f"choose_{'active' if choice == active else 'bench'}_{card_id}")
    if card_id == GIOVANNIS_GYARADOS and d.kind in (SELECT_POKEMON, FORCED_SWITCH):
        choice = options[-1] if counts["v044_whirlpool"] % 2 == 0 else options[0]
        counts["v044_whirlpool"] += 1
        return answer((choice,), "dragon_whirlwind")
    if card_id in (ERIKAS_BULBASAUR, ROCKET_MAGIKARP) and d.kind == SEARCH_DECK and d.min_choices == 0:
        decline = not options or counts[f"v044_optional_{card_id}"] % 4 == 3
        counts[f"v044_optional_{card_id}"] += 1
        return answer(() if decline else options[:1], f"{'declined' if decline else 'chosen'}_{card_id}")
    if card_id == SABRINAS_MR_MIME and d.kind == HAND_TO_DECK:
        energy_in_deck = sum(1 for u in state.players[d.player].deck if state.card_def(u).is_basic_energy)
        wanted = 1 + counts["v044_sleight"] % 3
        counts["v044_sleight"] += 1
        hand = list(d.options)
        for count in range(min(wanted, d.max_choices), 0, -1):
            chosen = hand[:count]
            available = energy_in_deck + sum(1 for u in chosen if state.card_def(u).is_basic_energy)
            if available >= count or available == 0:
                return answer(chosen, f"sleight_return_{count}")
        return None
    if card_id == SABRINAS_MR_MIME and d.kind == SEARCH_DECK:
        return answer(options[:d.min_choices], f"sleight_reveal_{d.min_choices}")
    if card_id == BLANK_CHANSEY and d.kind == HAND_TO_DECK:
        return answer(options[:d.min_choices], "lucky_return")
    if card_id == BLAINES_MANKEY and d.kind == DISCARD_TO_DECK_TOP:
        return answer(options[:1], "mischief")
    return None


def _v045_decision(state, counts):
    """v0.45 のカードのワザの決定への答え（原典で決められない選択 ``unresolved_choices`` は選ばない）。

    - じりょくせん: はがすカードは 1 つ目、つける相手の控えは 最後・最初 を順に
    - たすけをよぶ: 選べる 1 つ目（4 回に 1 回は出さない。0 枚は「出してよい」の選ばないこと）
    - ファイヤーブレス: 多い枚数ちょうど（ついている順の 1 つ目から）。かえんひこう: 相手の対戦ポケモン・残り HP のいちばん少ない控え を順に"""
    d = state.decision
    if d is None or d.resume != "attack":
        return None
    use = d.context_value("use")
    if use is None or use[2] not in V0_45:
        return None
    blocked = set(d.context_value("unresolved_choices", ()))
    options = [o for o in d.options if o not in blocked]
    card_id = use[2]

    def answer(choices, label):
        counts[f"v045_{label}"] += 1
        return ResolveDecision(d.player, d.id, tuple(choices))

    if card_id == DARK_MAGNETON and d.kind == MOVE_OPPONENT_ENERGY:
        return answer(options[:1], "magnetic_energy")
    if card_id == DARK_MAGNETON and d.kind == SELECT_POKEMON:
        choice = options[-1] if counts["v045_magnetic_bench_seen"] % 2 == 0 else options[0]
        counts["v045_magnetic_bench_seen"] += 1
        return answer((choice,), "magnetic_bench")
    if card_id == BROCKS_GEODUDE_40 and d.kind == BENCH_FROM_DECK:
        decline = not options or counts["v045_call_seen"] % 4 == 3
        counts["v045_call_seen"] += 1
        return answer(() if decline else options[:1], "call_declined" if decline else "call_benched")
    if card_id == BLAINES_CHARIZARD and d.kind == DISCARD_ENERGY:
        return answer(options[:d.min_choices], f"fire_breath_{d.min_choices}")
    if card_id == BLAINES_CHARIZARD and d.kind == SELECT_POKEMON:
        active = state.players[1 - d.player].active.pokemon_id
        bench = [o for o in options if o != active]
        active_turn = counts["v045_flame_flight"] % 2 == 0 or not bench
        counts["v045_flame_flight"] += 1
        if active_turn and active in options:
            return answer((active,), "flame_flight_active")
        remaining = {o: max_hp(state, state.find_pokemon(o)[1]) - state.find_pokemon(o)[1].damage for o in bench}
        return answer((min(bench, key=lambda o: (remaining[o], bench.index(o))),), "flame_flight_bench")
    return None


def _v046_decision(state, counts):
    """v0.46 のカードのワザの決定への答え（相手のワザとして使ったワザ（``copied``）も。原典で決められない選択 ``unresolved_choices`` は選ばない）。

    - せいちょう（``ATTACH_FROM_HAND``）: 選べるだけ・1 枚 を順に（0 枚は選ばない。HC7 で止まる）
    - かくさんソーラービーム（``SELECT_POKEMON``。ちょうど 2 匹）: 相手の控えの最初の 2 匹"""
    d = state.decision
    if d is None or d.resume != "attack":
        return None
    use = d.context_value("use")
    copied = d.context_value("copied")
    card_id = copied[0] if copied is not None else (use[2] if use is not None else None)
    if card_id not in V0_46:
        return None
    blocked = set(d.context_value("unresolved_choices", ()))
    options = [o for o in d.options if o not in blocked]
    if card_id == ERIKAS_VENUSAUR and d.kind == ATTACH_FROM_HAND:
        many = counts["v046_growth_seen"] % 2 == 0
        counts["v046_growth_seen"] += 1
        chosen = options[:d.max_choices] if many else options[:1]
        counts[f"v046_growth_{len(chosen)}"] += 1
        return ResolveDecision(d.player, d.id, tuple(chosen))
    if card_id == ERIKAS_VENUSAUR and d.kind == SELECT_POKEMON:
        counts[f"v046_spread_{d.min_choices}"] += 1
        return ResolveDecision(d.player, d.id, tuple(options[:d.min_choices]))
    return None


def _v046_retreat(state, tried, counts):
    """v0.46: 常にはたらく特殊能力（［ねんちゃくえき］・［にげるサポート］）で「にげる」のエネルギーの数が変わるとき、「にげる」を宣言する（1 局に 3 回まで。
    同じ番に 1 度）。少なくしてから 0 で止める読み方と答えが変わる数（CP2）は 1 局に 1 度だけ試し（拒否のあとは増えた数）、少なくできるなら少ない数、ほかは
    増えた数。ねむり・マヒ・エネルギーが足りないときはしない。数が変わらなければ何もしないので、前の版の組の結果は変わらない。"""
    player = state.current_player
    p = state.players[player]
    active = p.active
    if not p.bench or active.conditions.asleep or active.conditions.paralyzed or cannot_retreat(state, active) is not None:
        return None
    if state.card_def(active.card).play_role is not None:
        return None  # v0.47: なにかの化石・ピッピ人形の「にげる」は決まらない（PF2。_v047_trainer が 1 局に 1 度だけ試す）
    if "retreat" in tried or ("v046_retreat", state.turn_number) in tried or counts[f"v046_retreat_{player}"] >= 3:
        return None
    cost = retreat_cost(state, player)
    if not cost.modified:
        return None
    if cost.floor_first_minimum > cost.minimum and "retreat_floor" not in tried and not counts["v046_floor_probe"]:
        count, label = cost.minimum, "floor_probe"
    elif cost.reductions and cost.floor_first_minimum < cost.maximum:
        count, label = cost.floor_first_minimum, "reduced"
    else:
        count, label = cost.maximum, "increased" if cost.increases else "full"
    if len(active.energy) < count:
        return None
    if label != "floor_probe":
        tried.add(("v046_retreat", state.turn_number))
        counts[f"v046_retreat_{player}"] += 1
    counts[f"v046_{label}"] += 1
    return Retreat(player, tuple(active.energy[:count]), p.bench[0].card)


def _v047_decision(state, counts):
    """v0.47 のカードの決定への答え（相手のワザとして使ったワザ（``copied``）も。原典で決められない選択は選ばない）。元の手順より先に答える。

    - ［スパイ］（``PEEK_CARD``）・［わるふざけ］（``SELECT_PRIZE_CARD``）・おどろかす（``SELECT_HAND_CARD``）: 選べる位置を順に
    - みらいよち: 見る山札（``SELECT_DECK_OWNER``）は自分・相手を順に、枚数（``SELECT_LOOK_COUNT``）は 3・1・2 枚を順に（その山札の枚数まで。0 枚は選ばない。GS1）、
      並び（``ARRANGE_DECK_TOP``）は見たカードの逆
    - ナイトヘッド（``SELECT_POKEMON``）: 相手の控えの最初"""
    d = state.decision
    if d is None or d.resume not in ("attack", "power"):
        return None
    use = d.context_value("use")
    copied = d.context_value("copied") if d.resume == "attack" else None
    card_id = copied[0] if copied is not None else (use[2] if use is not None else None)
    if card_id not in V0_47:
        return None
    blocked = set(d.context_value("unresolved_choices", ()))
    options = [o for o in d.options if o not in blocked]
    if d.kind in (PEEK_CARD, SELECT_PRIZE_CARD, SELECT_HAND_CARD):
        seen = counts[f"v047_{d.kind}_seen"]
        counts[f"v047_{d.kind}_seen"] += 1
        chosen = options[seen % len(options)]
        if d.kind == PEEK_CARD:
            counts[f"v047_peek_{d.context_value('targets')[chosen][0]}"] += 1
        return ResolveDecision(d.player, d.id, (chosen,))
    if d.kind == SELECT_DECK_OWNER:
        seen = counts["v047_prophecy_owner_seen"]
        counts["v047_prophecy_owner_seen"] += 1
        owner = (d.player, 1 - d.player)[seen % 2]
        counts["v047_prophecy_" + ("own" if owner == d.player else "opponent")] += 1
        return ResolveDecision(d.player, d.id, (owner,))
    if d.kind == SELECT_LOOK_COUNT:
        seen = counts["v047_prophecy_count_seen"]
        counts["v047_prophecy_count_seen"] += 1
        wanted = (3, 1, 2)[seen % 3]
        chosen = min(wanted, max(o for o in options))
        counts[f"v047_prophecy_count_{chosen}"] += 1
        return ResolveDecision(d.player, d.id, (chosen,))
    if d.kind == ARRANGE_DECK_TOP:
        counts["v047_prophecy_arranged"] += 1
        return ResolveDecision(d.player, d.id, tuple(reversed(d.options)))
    if d.kind == SELECT_POKEMON and options:
        return ResolveDecision(d.player, d.id, (options[0],))
    return None


def _v047_power(state, tried, counts):
    """v0.47 の宣言する特殊能力を使う手順: マンキー（第2弾）の［スパイ］・コラッタ（ロケット団）の［わるふざけ］（この番にまだ使っておらず、ねむり・マヒ・こんらんでなく、
    見る・入れかえるカードがあるとき）。拒否を起こさない。"""
    player = state.current_player
    p = state.players[player]
    for pokemon in p.in_play():
        if state.is_face_down(pokemon):
            continue  # v0.67
        card_id = state.card_def(pokemon.card).id
        if card_id not in (JUNGLE_MANKEY, ROCKET_RATTATA) or (pokemon.pokemon_id, 0) in state.power_uses_this_turn:
            continue
        conditions = pokemon.conditions
        if conditions.asleep or conditions.paralyzed or conditions.confused:
            continue
        if card_id == ROCKET_RATTATA and not (p.prizes and p.deck):
            continue
        counts[f"v047_power_{card_id}"] += 1
        return UsePokemonPower(player, pokemon.pokemon_id, 0)
    return None


def _v047_trainer(state, tried, counts):
    """v0.47: なにかの化石・ピッピ人形を場に出す・すてる手順。手札にあり、ベンチに空きがあれば場に出す（トレーナーの使用を禁止された番は、1 度拒否されたら出さない）。
    バトル場の（進化していない）なにかの化石・ピッピ人形は、控えがいればすてる。ベンチのピッピ人形は、番の番号が 7 の倍数の番にすてる。"""
    player = state.current_player
    p = state.players[player]
    active = p.active
    if active is not None and state.card_def(active.card).play_role is not None and p.bench and not counts[f"v047_pf2_probe_{player}"] \
            and "retreat" not in tried:
        # バトル場のなにかの化石・ピッピ人形の「にげる」（PF2）を、1 局に 1 度だけ試す（エネルギー・コインの前に拒否される）
        counts[f"v047_pf2_probe_{player}"] += 1
        return Retreat(player, (), p.bench[0].card)
    if active is not None and state.card_def(active.card).play_role is not None and p.bench and ("v047_discard", active.pokemon_id) not in tried:
        tried.add(("v047_discard", active.pokemon_id))
        counts[f"v047_discard_active_{state.card_def(active.card).play_role}"] += 1
        return DiscardFromPlay(player, active.pokemon_id)
    if state.turn_number % 7 == 0:
        for pokemon in p.bench:
            if state.card_def(pokemon.card).play_role == "doll" and ("v047_discard", pokemon.pokemon_id) not in tried:
                tried.add(("v047_discard", pokemon.pokemon_id))
                counts["v047_discard_bench_doll"] += 1
                return DiscardFromPlay(player, pokemon.pokemon_id)
    if "trainer_locked" in tried or len(p.bench) >= bench_limit(state, player):
        return None
    for uid in p.hand:
        card_id = state.cards[uid].card_id
        if card_id in V0_47_TRAINERS and ("v047_play", uid) not in tried:
            tried.add(("v047_play", uid))
            counts[f"v047_play_{card_id}" + ("_locked" if trainer_use_blockers(state, player) else "")] += 1
            return PlayTrainer(player, uid)
    return None


def _v048_decision(state, counts):
    """v0.48 のカードの決定への答え（相手のワザとして使ったワザ（``copied``）も。原典で決められない選択は選ばない）。元の手順より先に答える。

    - テクスチャー1・2（ワザの ``SELECT_COLOR``）・［へんしょく］（特殊能力の ``SELECT_COLOR``）: 選べる色を順に（決定ごとに 1 つずつずらす）"""
    d = state.decision
    if d is None or d.resume not in ("attack", "power") or d.kind != SELECT_COLOR:
        return None
    use = d.context_value("use")
    copied = d.context_value("copied") if d.resume == "attack" else None
    card_id = copied[0] if copied is not None else (use[2] if use is not None else None)
    if card_id not in V0_48:
        return None
    blocked = set(d.context_value("unresolved_choices", ()))
    options = [o for o in d.options if o not in blocked]
    if not options:
        return None
    seen = counts[f"v048_color_seen_{d.resume}"]
    counts[f"v048_color_seen_{d.resume}"] += 1
    chosen = options[seen % len(options)]
    counts[f"v048_color_{d.resume}_{COLORS[chosen].value}"] += 1
    return ResolveDecision(d.player, d.id, (chosen,))


def _v048_observe(state, counts):
    """v0.48: 手順が呼ばれた盤面で、今有効な最大HPが印刷の HP と違う v0.48 のポケモン（［ガスのからだ］・「きょだいか」）を数える（``v048_max_hp_<カード>_raised``、
    のっているダメージが印刷の HP 以上で場にいるなら ``…_over_printed``）。盤面を数えるだけで、選ぶ操作は変えない。"""
    for player in state.players:
        for pokemon in player.in_play():
            if state.is_face_down(pokemon):
                continue  # v0.67: うらのカードは数えない（定義を読まない）
            card = state.card_def(pokemon.card)
            if card.id in V0_48 and card.hp is not None and max_hp(state, pokemon) != card.hp:
                counts[f"v048_max_hp_{card.id}_{'over_printed' if pokemon.damage >= card.hp else 'raised'}"] += 1


def _v048_power(state, tried, counts):
    """v0.48 の宣言する特殊能力を使う手順: モルフォンの［へんしょく］（この番にまだ使っておらず、ねむり・マヒ・こんらんでなく、決まって場にいる色があるとき。
    バトル場・ベンチのどちらでも使う）。拒否を起こさない。"""
    player = state.current_player
    p = state.players[player]
    for pokemon in p.in_play():
        if state.is_face_down(pokemon):
            continue  # v0.67
        if state.card_def(pokemon.card).id != VENOMOTH or (pokemon.pokemon_id, 0) in state.power_uses_this_turn:
            continue
        conditions = pokemon.conditions
        if conditions.asleep or conditions.paralyzed or conditions.confused or ("v048_shift", pokemon.pokemon_id) in tried:
            continue
        if not shift_color_options(state)[0]:
            continue
        tried.add(("v048_shift", pokemon.pokemon_id))
        counts["v048_power_shift"] += 1
        return UsePokemonPower(player, pokemon.pokemon_id, 0)
    return None


def _v049_relevant(state):
    """v0.49: 姿が変わりうるカード（メタモン・タケシのキュウコン）が場にいる（決められない姿・MH1 で拒否される答えを避ける手順を使う盤面）。"""
    return any(state.cards[pokemon.card].card_id in (DITTO, BROCKS_NINETALES) for player in state.players for pokemon in player.in_play())


def _v049_decision(state, counts):
    """v0.49 の決定への答え: 「ばける」でのせる手札の進化カード（選べるもののうち、選ぶと止めるものを除いて、順に）。元の手順より先に答える。"""
    d = state.decision
    if d is None or d.resume != "power" or d.kind != SELECT_EVOLUTION_CARD:
        return None
    use = d.context_value("use")
    if use is None or use[2] != BROCKS_NINETALES:
        return None
    blocked = set(d.context_value("unresolved_choices", ()))
    options = [o for o in d.options if o not in blocked]
    if not options:
        return None
    seen = counts["v049_shapeshift_seen"]
    counts["v049_shapeshift_seen"] += 1
    chosen = options[seen % len(options)]
    counts[f"v049_shapeshift_{state.cards[chosen].card_id}"] += 1
    return ResolveDecision(d.player, d.id, (chosen,))


def _v049_answer(state, command, counts):
    """v0.49: 決定への答え（``ResolveDecision``・``PromoteActive``・``TakePrize``）が、決められない姿（TF1・TF2・DG1）・MH1 で拒否されるなら、受け付けられる別の答えにする
    （姿が変わりうるカードが場にいるときだけ。状態の複製の上で試す）。どの答えも拒否されるなら元の答え（エンジンが対戦を止める）。"""
    if state.decision is None or not isinstance(command, (ResolveDecision, PromoteActive, TakePrize)) or not _v049_relevant(state):
        return command
    try:
        apply_command(state, command)
        return command
    except UnsupportedError as error:
        if error.code not in V049_FORM_STOPS:
            return command
        counts[f"v049_answer_stopped_{error.code}"] += 1
    d = state.decision
    for choices in all_answers(d):
        if set(choices) & set(d.context_value("unresolved_choices", ())):
            continue
        alternative = ResolveDecision(d.player, d.id, tuple(choices))
        try:
            apply_command(state, alternative)
        except (IllegalActionError, UnsupportedError):
            continue
        counts["v049_answer_alternative"] += 1
        return alternative
    return command


def _v049_power(state, tried, counts):
    """v0.49: タケシのキュウコンの「ばける」（のせていない・この番にまだ使っていない・ねむり・マヒ・こんらんでない・手札に止めずにのせられる進化カードがあるとき。
    バトル場・ベンチのどちらでも）と、のせたカードをもどす操作（番の番号が 4 の倍数の番。最大HPがのっているダメージ以下に下がるならもどさない）。拒否を起こさない。"""
    player = state.current_player
    p = state.players[player]
    for pokemon in p.in_play():
        if state.cards[pokemon.card].card_id != BROCKS_NINETALES:
            continue
        if pokemon.disguise is not None:
            if state.turn_number % 4 == 0 and pokemon.damage < state.card_def(pokemon.card).hp and ("v049_revert", pokemon.pokemon_id) not in tried:
                tried.add(("v049_revert", pokemon.pokemon_id))
                counts["v049_revert"] += 1
                return RemoveDisguise(player, pokemon.pokemon_id)
            continue
        conditions = pokemon.conditions
        if conditions.asleep or conditions.paralyzed or conditions.confused or ("v049_shapeshift", pokemon.pokemon_id) in tried:
            continue
        if any(use[0] == pokemon.pokemon_id for use in state.power_uses_this_turn):
            continue
        options, blocked = shapeshift_choices(state, player, pokemon, E_PowerKey(BROCKS_NINETALES, 0))
        if len(options) == len(blocked):
            continue
        tried.add(("v049_shapeshift", pokemon.pokemon_id))
        counts["v049_power_shapeshift"] += 1
        return UsePokemonPower(player, pokemon.pokemon_id, 0, card=pokemon.card)
    return None


def _v049_trainer(state, tried, counts):
    """v0.49: 思い出させる（対戦ポケモンが進化していて、今の姿がいちばん上のカードで、すぐ下のカードのワザに払えるものがあり、この番にまだ使っていないとき）。"""
    player = state.current_player
    p = state.players[player]
    active = p.active
    if active is None or "trainer_locked" in tried or recall_records(state, player) or current_form(state, active).kind != "printed":
        return None
    if not active.evolution_stack:
        return None
    below = active.evolution_stack[-1]
    if not any(attack_cost_payable(state, active, attack) for attack in state.card_def(below).attacks):
        return None
    for uid in p.hand:
        if state.cards[uid].card_id == RECALL and ("v049_recall", uid) not in tried:
            tried.add(("v049_recall", uid))
            counts["v049_play_recall"] += 1
            return PlayTrainer(player, uid)
    return None


def _v049_attack(state, tried, counts):
    """v0.49: 今持つワザのうち、出どころが今の姿のいちばん上のカードでないワザ（［サイコリンク］・［へんしん］・「ばける」・「思い出させる」）で、払えて止める理由がなく、
    この番に拒否されていないものを、使った回数の少ないものから使う（``UseAttack`` の ``card``）。"""
    player = state.current_player
    active = state.players[player].active
    if active is None or "attack" in tried:
        return None
    form = current_form(state, active)
    used = Counter((e.get("card_id"), e["attack_index"]) for e in state.log if e["kind"] == "attack" and e.get("player") == player)
    candidates = []
    for option in available_attacks(state, active):
        if option.route == "form" and form.kind == "printed":
            continue
        if option.problem is not None or ("v049_attack", option.card, option.attack_index) in tried:
            continue
        if attack_locked(state, active, option.key) is not None:
            continue
        if not attack_cost_payable(state, active, state.definitions[option.card_id].attacks[option.attack_index]):
            continue
        candidates.append(option)
    if not candidates:
        return None
    option = min(candidates, key=lambda o: (used[(o.card_id, o.attack_index)], o.route, o.card_id, o.attack_index))
    tried.add(("v049_attack", option.card, option.attack_index))
    counts[f"v049_attack_{option.route}" + ("" if form.kind == "printed" else f"_{form.kind}")] += 1
    return UseAttack(player, option.attack_index, card=option.card)


def _v050_beam_decision(d):
    """v0.50: たいかビームの決定（ワザを使ったポケモンのワザ・相手のワザとして使ったワザ・［サイコリンク］で持つワザのどれでも、ワザの続きの情報の ``use``・``copied``）。"""
    if d.resume != "attack" or d.kind != SELECT_POKEMON:
        return False
    use = d.context_value("use")
    copied = d.context_value("copied")
    return (use is not None and tuple(use[2:4]) == (MEW, 1)) or (copied is not None and tuple(copied) == (MEW, 1))


def _v050_decision(state, counts):
    """v0.50 の決定への答え（元の手順より先に答える）:

    - たいかビーム: 選ぶと止める（DV5）ものを除き、3 回に 2 回は相手の進化ポケモン、1 回は自分の進化ポケモン（どちらかしかなければそれ）を、順に選ぶ
    - 退化スプレー: 退化させるポケモンは選ぶと止める（DV5）ものを除いて順に。はがす枚数は、選ぶと止める（DV1）枚数を除いて、1 枚・すべて・0 枚を順に
    """
    d = state.decision
    if d is None:
        return None
    blocked = set(d.context_value("unresolved_choices", ()))
    if _v050_beam_decision(d):
        options = [o for o in d.options if o not in blocked]
        if not options:
            return None
        mine = [o for o in options if state.find_pokemon(o)[0] == d.player]
        theirs = [o for o in options if o not in mine]
        seen = counts["v050_beam_seen"]
        counts["v050_beam_seen"] += 1
        group = mine if (seen % 3 == 2 and mine) or not theirs else theirs
        chosen = group[seen % len(group)]
        counts["v050_beam_" + ("own" if chosen in mine else "opponent")] += 1
        return ResolveDecision(d.player, d.id, (chosen,))
    use = d.context_value("use")
    if d.resume != "trainer" or use is None or use[2] != DEVOLUTION_SPRAY:
        return None
    options = [o for o in d.options if o not in blocked]
    if not options:
        return None
    if d.kind == SELECT_POKEMON:
        seen = counts["v050_spray_target_seen"]
        counts["v050_spray_target_seen"] += 1
        return ResolveDecision(d.player, d.id, (options[seen % len(options)],))
    if d.kind != SELECT_DEVOLVE_COUNT:
        return None
    seen = counts["v050_spray_count_seen"]
    counts["v050_spray_count_seen"] += 1
    if blocked:
        counts["v050_spray_count_dv1_avoided"] += 1
    wanted = (1, max(d.options), 0)[seen % 3]
    chosen = wanted if wanted in options else options[-1]
    counts[f"v050_spray_count_{chosen}"] += 1
    return ResolveDecision(d.player, d.id, (chosen,))


def _v050_trainer(state, tried, counts):
    """v0.50: 退化スプレー（自分の場に、実際に進化カードが重なっていて「ばける」でないポケモンがいて、この番にまだ使っていないとき。番の番号が 3 の倍数の番は、
    ダメージがのっている進化ポケモンがいれば使う。それ以外の番は、ダメージがのっていて退化すればきぜつしないポケモンがいれば使う）。拒否を起こさない。"""
    player = state.current_player
    p = state.players[player]
    if "trainer_locked" in tried or ("v050_spray", state.turn_number) in tried:
        return None
    candidates = [state.find_pokemon(pid)[1] for pid in devolution_candidates(state, (player,))]
    candidates = [pokemon for pokemon in candidates if not devolution_forbidden(state, pokemon)]
    if not candidates:
        return None
    damaged = [pokemon for pokemon in candidates if pokemon.damage > 0]
    if not damaged and state.turn_number % 3 != 0:
        return None
    for uid in p.hand:
        if state.cards[uid].card_id == DEVOLUTION_SPRAY:
            tried.add(("v050_spray", state.turn_number))
            counts["v050_play_spray"] += 1
            return PlayTrainer(player, uid)
    return None


def _v051_decision(state, counts):
    """v0.51 の決定への答え（元の手順より先に答える）:

    - よみがえらせる（ワザを使ったポケモンのワザ・相手のワザとして使ったワザ・［サイコリンク］で持つワザのどれでも）: 自分のトラッシュのカードと相手のトラッシュのカードを
      交互に（どちらかしかなければそれ）、それぞれの前から順に選ぶ
    - 元気のかけら・ポケモンの笛: 1 局の中で、それぞれ 2 回目・5 回目…（3 回に 1 回）は選ばない（「ことができる」の 0 枚）。それ以外は選べるものを順に
    """
    d = state.decision
    if d is None or d.kind != BENCH_FROM_DISCARD:
        return None
    if d.resume == "attack":
        mine = [o for o in d.options if state.cards[o].owner == d.player]
        theirs = [o for o in d.options if o not in mine]
        seen = counts["v051_invigorate_seen"]
        counts["v051_invigorate_seen"] += 1
        group = mine if (seen % 2 == 0 and mine) or not theirs else theirs
        chosen = group[(seen // 2) % len(group)]
        counts["v051_invigorate_" + ("own" if chosen in mine else "opponent")] += 1
        return ResolveDecision(d.player, d.id, (chosen,))
    use = d.context_value("use")
    if d.resume != "trainer" or use is None or use[2] not in V0_51_TRAINERS:
        return None
    key = f"v051_{'revive' if use[2] == REVIVE else 'flute'}_seen"
    seen = counts[key]
    counts[key] += 1
    if seen % 3 == 1:
        counts[key.replace("_seen", "_declined")] += 1
        return ResolveDecision(d.player, d.id, ())
    return ResolveDecision(d.player, d.id, (d.options[seen % len(d.options)],))


def _v051_trainer(state, tried, counts):
    """v0.51: 元気のかけら（自分のトラッシュに、自分のベンチに出せるたねポケモンのカードがあるとき）・ポケモンの笛（相手のトラッシュに、相手のベンチに出せるたねポケモンの
    カードがあり、番の番号が偶数のとき）。それぞれ 1 番に 1 回まで。出せるカードがないとき（RV1・FT1）は使わない（その場面は単体テストで確かめる）。拒否を起こさない。"""
    player = state.current_player
    if "trainer_locked" in tried:
        return None
    hand = state.players[player].hand
    for card_id, owner, label in ((REVIVE, player, "revive"), (POKEMON_FLUTE, 1 - player, "flute")):
        if (f"v051_{label}", state.turn_number) in tried or not bench_from_discard_candidates(state, (owner,)):
            continue
        if label == "flute" and state.turn_number % 2:
            continue
        for uid in hand:
            if state.cards[uid].card_id == card_id:
                tried.add((f"v051_{label}", state.turn_number))
                counts[f"v051_play_{label}"] += 1
                return PlayTrainer(player, uid)
    return None


_V052_REAL: dict = {}  # v0.52: 手順に渡した本当の状態（手札を隠した写しで apply_command を呼ぶと、カードの保存則の不変条件で止まる）


def _v052_accepted(state, command) -> bool:
    """v0.52: 操作を受け付けるか（渡した状態は変えない。``apply_command`` は複製してから処理する）。止まる操作（SU1・SU2・FJ1・MH1 など）を手順に選ばせないため。
    手札を隠した写し（v0.46〜v0.48 の手順）を渡されても、本当の状態で確かめる。"""
    real = _V052_REAL.get("state")
    if real is not None and real.turn_number == state.turn_number and real.decision == state.decision:
        state = real
    try:
        apply_command(state, command)
    except (IllegalActionError, UnsupportedError):
        return False
    return True


def _v052_decision(state, counts):
    """v0.52 の決定への答え（元の手順より先に答える）: フジろうじん・ポケモン回収で選ぶポケモン。受け付ける答え（SU1・SU2・MH1 で止まらない）のうち、
    ポケモン回収は 1 局の中で、バトル場 → ベンチ → … の順に（選べるときは）、フジろうじんは控えの前から順に選ぶ。"""
    d = state.decision
    if d is None or d.resume != "trainer":
        return None
    use = d.context_value("use")
    if use is None or use[2] not in V0_52_TRAINERS:
        return None
    label = "scoop_up" if use[2] == SCOOP_UP else "fuji"
    accepted = [o for o in d.options if _v052_accepted(state, ResolveDecision(d.player, d.id, (o,)))]
    seen = counts[f"v052_{label}_seen"]
    counts[f"v052_{label}_seen"] += 1
    counts[f"v052_{label}_stopped_choices"] += len(d.options) - len(accepted)
    if not accepted:
        return None
    active = state.players[d.player].active
    if label == "scoop_up":
        wanted = [o for o in accepted if (active is not None and o == active.pokemon_id) == (seen % 2 == 0)] or accepted
        chosen = wanted[0]
        counts["v052_scoop_up_" + ("active" if active is not None and chosen == active.pokemon_id else "bench")] += 1
    else:
        chosen = accepted[seen % len(accepted)]
    return ResolveDecision(d.player, d.id, (chosen,))


def _v052_trainer(state, tried, counts):
    """v0.52: フジろうじん（自分の控えに、ダメージのあるポケモンか進化ポケモンがいるとき）・ポケモン回収（自分の場に、ダメージのあるポケモンがいるとき）。それぞれ 1 番に
    1 回まで。使う前に止まる場面（FJ1・SU1・SU2・どの答えも止まる）は使わない（その場面は単体テストで確かめる）。拒否を起こさない。"""
    player = state.current_player
    if "trainer_locked" in tried:
        return None
    p = state.players[player]
    for card_id, label, wanted in ((SCOOP_UP, "scoop_up", any(pk.damage for pk in p.in_play())),
                                   (MR_FUJI, "fuji", any(pk.damage or pk.evolution_stack for pk in p.bench))):
        if (f"v052_{label}", state.turn_number) in tried or not wanted:
            continue
        for uid in p.hand:
            if state.cards[uid].card_id == card_id:
                tried.add((f"v052_{label}", state.turn_number))
                command = PlayTrainer(player, uid)
                if not _v052_accepted(state, command):
                    counts[f"v052_{label}_not_playable"] += 1
                    break
                counts[f"v052_play_{label}"] += 1
                return command
    return None


def _v053_decision(state, counts):
    """v0.53 の決定への答え（元の手順より先に答える）: 山札・トラッシュからカードを選ぶトレーナーの決定。受け付ける答え（NG1 の 0 枚などで止まらない）のうち、
    使うための条件の手札は手札の後ろから、選ぶカードは「選べるだけ → 0 枚（選ばなくてよいとき）→ 1 枚」の順に回して選ぶ（選ばない・最大の枚数の両方を起こす）。"""
    d = state.decision
    if d is None or d.resume != "trainer":
        return None
    use = d.context_value("use")
    if use is None or use[2] not in V0_53_TRAINERS:
        return None
    seen = counts[f"v053_{use[2]}_{d.kind}_seen"]
    counts[f"v053_{use[2]}_{d.kind}_seen"] += 1
    if d.kind in ("discard_from_hand", "hand_to_deck"):
        candidates = [tuple(d.options[-d.max_choices:])]
    else:
        sizes = [d.max_choices, d.min_choices, min(1, d.max_choices)]
        size = sizes[seen % 3]
        candidates = [tuple(d.options[:size]), tuple(d.options[-size:] if size else ()), *[(o,) for o in d.options], ()]
    for choices in candidates:
        if d.min_choices <= len(choices) <= d.max_choices and _v052_accepted(state, ResolveDecision(d.player, d.id, choices)):
            counts[f"v053_{use[2]}_chose_{len(choices)}"] += 1
            return ResolveDecision(d.player, d.id, choices)
    counts[f"v053_{use[2]}_no_accepted_answer"] += 1
    return None


def _v053_trainer(state, tried, counts):
    """v0.53: 山札・トラッシュからカードを選ぶトレーナーを、受け付けるなら使う（種類ごとに 1 番に 1 回まで）。使う前に止まる場面（ST1・NG1・FC1・手札が足りない）は
    使わない（その場面は単体テストで確かめる。``v053_<カード>_not_playable`` に数える）。拒否を起こさない。"""
    player = state.current_player
    if "trainer_locked" in tried:
        return None
    p = state.players[player]
    for card_id in V0_53_TRAINERS:
        if (f"v053_{card_id}", state.turn_number) in tried:
            continue
        for uid in p.hand:
            if state.cards[uid].card_id == card_id:
                tried.add((f"v053_{card_id}", state.turn_number))
                command = PlayTrainer(player, uid)
                real = _V052_REAL.get("state")
                try:
                    apply_command(real if real is not None and real.turn_number == state.turn_number and real.decision == state.decision else state, command)
                except (IllegalActionError, UnsupportedError) as error:
                    counts[f"v053_{card_id}_not_playable_{error.code}"] += 1  # 使う前に止まる・拒否される場面（コードごと）
                    break
                counts[f"v053_play_{card_id}"] += 1
                return command
    return None


def _v054_decision(state, counts):
    """v0.54 の決定への答え（元の手順より先に答える）: 手札の入れ替え・ドロー・情報の確認のトレーナーの決定。決めるのが相手プレイヤー（エリカの 2 つめ）でも同じ手順で答える。
    使うための条件の手札は手札の後ろから。手札のトラッシュ（スパイ作戦・カツラのギャンブル）・引く枚数（エリカ）・見る枚数（ポケモン図鑑）は「できるだけ → 0 → 1」の順に
    回し（0 で止まる答え（HC5）は受け付けないので次の候補）、並べかえは逆順。"""
    d = state.decision
    if d is None or d.resume != "trainer":
        return None
    use = d.context_value("use")
    if use is None or use[2] not in V0_54_TRAINERS:
        return None
    seen = counts[f"v054_{use[2]}_{d.kind}_seen"]
    counts[f"v054_{use[2]}_{d.kind}_seen"] += 1
    if d.kind == "arrange_deck_top":
        candidates = [tuple(reversed(d.options))]
    elif d.kind in ("select_draw_count", "select_look_count"):
        candidates = [(d.options[[-1, 0, min(1, len(d.options) - 1)][seen % 3]],), *[(o,) for o in d.options]]
    elif d.kind == "discard_from_hand" and d.min_choices == d.max_choices:
        candidates = [tuple(d.options[-d.max_choices:])]
    else:
        size = [d.max_choices, 0, min(1, d.max_choices)][seen % 3]
        candidates = [tuple(d.options[-size:] if size else ()), tuple(d.options[-1:]), ()]
    for choices in candidates:
        if d.min_choices <= len(choices) <= d.max_choices and _v052_accepted(state, ResolveDecision(d.player, d.id, choices)):
            counts[f"v054_{use[2]}_{d.kind}_{'opponent' if d.player != use[0] else 'user'}_{len(choices) if d.kind != 'select_draw_count' else choices[0]}"] += 1
            return ResolveDecision(d.player, d.id, choices)
    counts[f"v054_{use[2]}_no_accepted_answer"] += 1
    return None


def _v054_trainer(state, tried, counts):
    """v0.54: 手札の入れ替え・ドロー・情報の確認のトレーナーを、受け付けるなら使う（種類ごとに 1 番に 1 回まで）。使う前に止まる・拒否される場面（カツラの奥の手の
    ``OTHER_CARDS_IN_HAND``・にせオーキドの逆襲の手札不足・カツラのギャンブルの HC5）は使わず ``v054_<カード>_not_playable_<コード>`` に数える。"""
    player = state.current_player
    if "trainer_locked" in tried:
        return None
    p = state.players[player]
    for card_id in V0_54_TRAINERS:
        if (f"v054_{card_id}", state.turn_number) in tried:
            continue
        for uid in p.hand:
            if state.cards[uid].card_id == card_id:
                tried.add((f"v054_{card_id}", state.turn_number))
                command = PlayTrainer(player, uid)
                real = _V052_REAL.get("state")
                try:
                    apply_command(real if real is not None and real.turn_number == state.turn_number and real.decision == state.decision else state, command)
                except (IllegalActionError, UnsupportedError) as error:
                    counts[f"v054_{card_id}_not_playable_{error.code}"] += 1
                    break
                counts[f"v054_play_{card_id}"] += 1
                return command
    return None


def _v055_decision(state, counts):
    """v0.55 の決定への答え（元の手順より先に答える）: すぐに使い終わるトレーナーの決定。決めるのが相手プレイヤー（ワープポイントの 1 つめ）でも同じ手順で答える。
    ちょうどの枚数は選べるものの後ろから、範囲（エネルギーサーキュレート）は「すべて → 0 → 1」の順に回し、数（いいきずぐすりのとりのぞく数）は「最大 → 0 → 1」。
    受け付けない答え（選ぶと止める選択・MH1）は次の候補。"""
    d = state.decision
    if d is None or d.resume != "trainer":
        return None
    use = d.context_value("use")
    if use is None or use[2] not in V0_55_TRAINERS:
        return None
    seen = counts[f"v055_{use[2]}_{d.kind}_seen"]
    counts[f"v055_{use[2]}_{d.kind}_seen"] += 1
    if d.kind == "select_counter_count":
        candidates = [(d.options[[-1, 0, min(1, len(d.options) - 1)][seen % 3]],), *[(o,) for o in d.options]]
    elif d.min_choices == d.max_choices:
        candidates = [tuple(d.options[-d.max_choices:]), tuple(d.options[:d.max_choices]), *[(o,) for o in d.options if d.max_choices == 1]]
    else:
        size = [d.max_choices, 0, min(1, d.max_choices)][seen % 3]
        candidates = [tuple(d.options[-size:] if size else ()), tuple(d.options[-1:]), ()]
    for choices in candidates:
        if d.min_choices <= len(choices) <= d.max_choices and _v052_accepted(state, ResolveDecision(d.player, d.id, choices)):
            value = choices[0] if d.kind == "select_counter_count" else len(choices)
            counts[f"v055_{use[2]}_{d.kind}_{'opponent' if d.player != use[0] else 'user'}_{value}"] += 1
            return ResolveDecision(d.player, d.id, choices)
    counts[f"v055_{use[2]}_no_accepted_answer"] += 1
    return None


def _v055_trainer(state, tried, counts):
    """v0.55: すぐに使い終わるトレーナーを、受け付けるなら使う（種類ごとに 1 番に 1 回まで）。使う前に止まる・拒否される場面（MW1・EM1・FC1・SP1・FH1・GL1・GL2・SB1・SB2・
    使うための条件（NO_ENERGY_TO_DISCARD・BASIC_POKEMON_IN_HAND）・MH1 など）は使わず ``v055_<カード>_not_playable_<コード>`` に数える。"""
    player = state.current_player
    if "trainer_locked" in tried:
        return None
    p = state.players[player]
    for card_id in V0_55_TRAINERS:
        if (f"v055_{card_id}", state.turn_number) in tried:
            continue
        for uid in p.hand:
            if state.cards[uid].card_id == card_id:
                tried.add((f"v055_{card_id}", state.turn_number))
                command = PlayTrainer(player, uid)
                real = _V052_REAL.get("state")
                try:
                    apply_command(real if real is not None and real.turn_number == state.turn_number and real.decision == state.decision else state, command)
                except (IllegalActionError, UnsupportedError) as error:
                    counts[f"v055_{card_id}_not_playable_{error.code}"] += 1
                    break
                counts[f"v055_play_{card_id}"] += 1
                return command
    return None


def _v056_decision(state, counts):
    """v0.56 の決定への答え（元の手順より先に答える）: 相手の決定・番の終わり・期限のある効果のトレーナーの決定。相手プレイヤーの決定（たずねる ``accept_request``・
    エリカの香水の相手が出すたねポケモンなど）も同じ手順で答える。たずねる答えは「オーケー → オーケーでない」を交互に、ちょうどの枚数は選べるものの後ろから、範囲は
    「すべて → 0 → 1」の順に回す。受け付けない答え（RT1 の 0 個・選ぶと止める選択・MH1）は次の候補。"""
    d = state.decision
    if d is None or d.resume != "trainer":
        return None
    use = d.context_value("use")
    if use is None or use[2] not in V0_56_TRAINERS:
        return None
    seen = counts[f"v056_{use[2]}_{d.kind}_seen"]
    counts[f"v056_{use[2]}_{d.kind}_seen"] += 1
    if d.kind == "accept_request":
        candidates = [tuple(d.options) if seen % 2 == 0 else (), ()]
    elif d.min_choices == d.max_choices:
        candidates = [tuple(d.options[-d.max_choices:]), tuple(d.options[:d.max_choices]), *[(o,) for o in d.options if d.max_choices == 1]]
    else:
        size = [d.max_choices, 0, min(1, d.max_choices)][seen % 3]
        candidates = [tuple(d.options[-size:] if size else ()), tuple(d.options[-1:]), tuple(d.options[:max(d.min_choices, 1)]), ()]
    for choices in candidates:
        if d.min_choices <= len(choices) <= d.max_choices and _v052_accepted(state, ResolveDecision(d.player, d.id, choices)):
            counts[f"v056_{use[2]}_{d.kind}_{'opponent' if d.player != use[0] else 'user'}_{len(choices)}"] += 1
            return ResolveDecision(d.player, d.id, choices)
    counts[f"v056_{use[2]}_no_accepted_answer"] += 1
    return None


def _v056_trainer(state, tried, counts, *, only=V0_56_TRAINERS):
    """v0.56: 相手の決定・番の終わり・期限のある効果のトレーナーを、受け付けるなら使う（種類ごとに 1 番に 1 回まで）。使う前に止まる・拒否される場面（LS1・RT1・RG1・MY1・
    ST1・BENCH_FULL・使うための条件・トレーナーの使用の禁止・MH1 など）は使わず ``v056_<カード>_not_playable_<コード>`` に数える。"""
    player = state.current_player
    if "trainer_locked" in tried:
        return None
    p = state.players[player]
    for card_id in only:
        if (f"v056_{card_id}", state.turn_number) in tried:
            continue
        for uid in p.hand:
            if state.cards[uid].card_id == card_id:
                tried.add((f"v056_{card_id}", state.turn_number))
                command = PlayTrainer(player, uid)
                real = _V052_REAL.get("state")
                try:
                    apply_command(real if real is not None and real.turn_number == state.turn_number and real.decision == state.decision else state, command)
                except (IllegalActionError, UnsupportedError) as error:
                    counts[f"v056_{card_id}_not_playable_{error.code}"] += 1
                    break
                counts[f"v056_play_{card_id}"] += 1
                return command
    return None


def _v057_accepted(state, command):
    """v0.57: 手順の操作を、手札を隠した写しではなく本当の状態で受け付けるか（v0.52 の ``_v052_accepted`` と同じ）。"""
    return _v052_accepted(state, command)


def _v057_decision(state, counts):
    """v0.57 のスタジアムの決定への答え（元の手順より先に答える）: せまいジムの控えを手札にもどす（後ろの控え）・セキチクシティジムのキョウのポケモン（いちばん後ろ）・
    トキワシティジムのとりのぞく機会（使う → 使わないを交互に）・錯乱ジムの借りるかの問い（借りる → 借りないを交互に）・リムーブ禁止ジムの追加の 2 枚（手札の後ろの 2 枚）。
    受け付けない答え（VG1・CH1 など選ぶと止める選択）は次の候補。"""
    d = state.decision
    if d is None:
        return None
    if d.resume == "stadium":
        stage = d.context_value("stage")
    elif d.resume == "trainer" and d.context_value("chaos") is not None:
        stage = "chaos"
    elif d.resume == "trainer" and d.context_value("stadium_cost") is not None:
        stage = "stadium_cost"
    else:
        return None
    seen = counts[f"v057_{stage}_seen"]
    counts[f"v057_{stage}_seen"] += 1
    if stage in ("evolution_heal", "chaos"):
        candidates = [tuple(d.options) if seen % 2 == 0 else (), ()]
    else:
        size = max(d.min_choices, min(d.max_choices, len(d.options)))
        candidates = [tuple(d.options[-size:]), tuple(d.options[:size])]
    for choices in candidates:
        if d.min_choices <= len(choices) <= d.max_choices and _v057_accepted(state, ResolveDecision(d.player, d.id, choices)):
            counts[f"v057_{stage}_{len(choices)}"] += 1
            return ResolveDecision(d.player, d.id, choices)
    counts[f"v057_{stage}_no_accepted_answer"] += 1
    return None


def _v057_trainer(state, tried, counts):
    """v0.57: 手札のスタジアムを、場に同じ名前のスタジアムがなければ出す（スタジアムごとに 1 番に 1 回まで。相手のスタジアムを入れかえる場面を起こす）。受け付けない場面
    （トレーナーの使用の禁止など）は出さず ``v057_<カード>_not_playable_<コード>`` に数える。"""
    player = state.current_player
    p = state.players[player]
    current = None if state.stadium is None else state.cards[state.stadium.card].card_id
    for uid in p.hand:
        card_id = state.cards[uid].card_id
        if card_id not in V0_57_STADIUMS or card_id == current or (f"v057_{card_id}", state.turn_number) in tried:
            continue
        tried.add((f"v057_{card_id}", state.turn_number))
        command = PlayTrainer(player, uid)
        try:
            apply_command(_V052_REAL.get("state") if _V052_REAL.get("state") is not None and _V052_REAL["state"].turn_number == state.turn_number
                          and _V052_REAL["state"].decision == state.decision else state, command)
        except (IllegalActionError, UnsupportedError) as error:
            counts[f"v057_{card_id}_not_playable_{error.code}"] += 1
            continue
        counts[f"v057_play_{card_id}" + ("_replacing" if current is not None else "")] += 1
        return command
    return None


def _v057_stadium(state, tried, counts):
    """v0.57: 自分の番に使うスタジアムの効果（タマムシ: 特殊状態のエリカのポケモンのエネルギーカード 1 枚・セキチク: 1 番に 1 回（2 番に 1 回まで）・ヤマブキ: 基本エネルギー
    カードが 2 枚以上ついたナツメのポケモンから 1 枚（1 番に 1 回まで））を、受け付けるなら使う。止まる場面（TG1・FG1・FG2・STB1）は使わず数える。"""
    stadium = state.stadium
    if stadium is None:
        return None
    card_id = state.cards[stadium.card].card_id
    player = state.current_player
    p = state.players[player]
    marker = ("v057_stadium", card_id, state.turn_number)
    if marker in tried:
        return None
    command = None
    if card_id == CELADON_CITY_GYM:
        for pokemon in p.in_play():
            if state.is_face_down(pokemon):
                continue  # v0.67
            if state.card_def(pokemon.card).name_ja.startswith("エリカの") and pokemon.conditions.names() and pokemon.energy:
                command = UseStadium(player, pokemon.energy[-1])
                break
    elif card_id == FUCHSIA_CITY_GYM and state.turn_number % 4 in (1, 2):
        command = UseStadium(player)
    elif card_id == SAFFRON_CITY_GYM:
        for pokemon in p.in_play():
            basics = [u for u in pokemon.energy if state.card_def(u).is_basic_energy]
            if state.card_def(pokemon.card).name_ja.startswith("ナツメの") and len(basics) >= 2:
                command = UseStadium(player, basics[-1])
                break
    if command is None:
        return None
    tried.add(marker)
    try:
        apply_command(state, command)
    except (IllegalActionError, UnsupportedError) as error:
        counts[f"v057_use_{card_id}_rejected_{error.code}"] += 1
        return None
    counts[f"v057_use_{card_id}"] += 1
    return command


def _v057_attack(state, command, tried, counts):
    """v0.57: クチバシティジムが場にあり、マチスのポケモンがワザを使うときは、コインを投げることを交互に選ぶ（``UseAttack.stadium_coin``）。受け付けなければ元の操作。"""
    if not isinstance(command, UseAttack) or command.stadium_coin or state.stadium is None:
        return command
    if state.cards[state.stadium.card].card_id != VERMILION_CITY_GYM:
        return command
    active = state.players[command.player].active
    if active is None or not state.card_def(current_form(state, active).card).name_ja.startswith("マチスの"):
        return command
    seen = counts["v057_vermilion_attack_seen"]
    counts["v057_vermilion_attack_seen"] += 1
    if seen % 2:
        counts["v057_vermilion_declined"] += 1
        return command
    coined = UseAttack(command.player, command.attack_index, card=command.card, stadium_coin=True)
    try:
        apply_command(state, coined)
    except (IllegalActionError, UnsupportedError) as error:
        counts[f"v057_vermilion_rejected_{error.code}"] += 1
        return command
    counts["v057_vermilion_coin"] += 1
    return coined


def _v058_energy(state, command, tried, counts):
    """v0.58: この番に手札からまだエネルギーカードをつけておらず、手札に特殊エネルギーがあれば、2 番に 1 回、元の手順のかわりに特殊エネルギーをつける（元の手順は基本
    エネルギーだけをつける）。つけ先: きずぐすり配合エネルギーはダメージのあるポケモン、なんでもなおし配合エネルギーは特殊状態のバトル場のポケモン（なければバトル場）、
    レインボーエネルギーはそのダメージできぜつしないポケモン（3 回に 1 回は、きぜつするポケモンがいればそれにつける）、無色2個エネルギーはバトル場。受け付けない場面
    （RB1・RB4 など）はつけず ``v058_attach_<カード>_rejected_<コード>`` に数える。"""
    if state.phase is not Phase.MAIN or state.energy_attachments_this_turn or ("v058_energy", state.turn_number) in tried:
        return None
    if not isinstance(command, (AttachEnergy, UseAttack, EndTurn)):
        return None
    player = state.current_player
    p = state.players[player]
    specials = [u for u in p.hand if state.cards[u].card_id in V0_58_ENERGIES]
    if not specials or (state.turn_number // 2) % 2:
        return None
    tried.add(("v058_energy", state.turn_number))
    pokemons = list(p.in_play())
    for uid in specials:
        card_id = state.cards[uid].card_id
        target = None
        if card_id == POTION_ENERGY:
            target = next((pk for pk in pokemons if pk.damage), p.active)
        elif card_id == FULL_HEAL_ENERGY:
            target = p.active
        elif card_id == RAINBOW_ENERGY:
            seen = counts["v058_rainbow_seen"]
            counts["v058_rainbow_seen"] += 1
            knocked = [pk for pk in pokemons if max_hp(state, pk) - pk.damage <= 10]
            safe = [pk for pk in pokemons if max_hp(state, pk) - pk.damage > 10]
            target = knocked[0] if knocked and seen % 3 == 2 and p.bench else (safe[0] if safe else None)
        else:
            target = p.active
        if target is None:
            continue
        attach = AttachEnergy(player, uid, target.card)
        try:
            apply_command(_V052_REAL.get("state") if _V052_REAL.get("state") is not None and _V052_REAL["state"].turn_number == state.turn_number
                          and _V052_REAL["state"].decision == state.decision else state, attach)
        except (IllegalActionError, UnsupportedError) as error:
            counts[f"v058_attach_{card_id}_rejected_{error.code}"] += 1
            continue
        where = "active" if target is p.active else "bench"
        counts[f"v058_attach_{card_id}_{where}"] += 1
        if card_id == POTION_ENERGY and target.damage:
            counts["v058_potion_energy_heals"] += 1
        if card_id == FULL_HEAL_ENERGY and target.conditions.names():
            counts["v058_full_heal_energy_cures"] += 1
        if card_id == RAINBOW_ENERGY and max_hp(state, target) - target.damage <= 10:
            counts["v058_rainbow_knock_out"] += 1
        return attach
    return None


def _v058_trainer(state, tried, counts):
    """v0.58: ナツメのサイキックコントロールを、相手のトラッシュにトレーナーカードがあり、受け付けるなら使う（1 番に 1 回まで）。"""
    player = state.current_player
    if "trainer_locked" in tried or ("v058_psychic_control", state.turn_number) in tried:
        return None
    p = state.players[player]
    if not any(state.card_def(u).category == "trainer" for u in state.players[1 - player].discard):
        return None
    for uid in p.hand:
        if state.cards[uid].card_id != PSYCHIC_CONTROL:
            continue
        tried.add(("v058_psychic_control", state.turn_number))
        command = PlayTrainer(player, uid)
        if not _v052_accepted(state, command):
            counts["v058_psychic_control_not_playable"] += 1
            return None
        counts["v058_play_psychic_control"] += 1
        return command
    return None


def _v058_decision(state, counts):
    """v0.58 の決定への答え（元の手順より先に答える）: サイキックコントロールで使う相手のトラッシュのトレーナー（4 回に 1 回は使わない。ほかは選べるものの後ろから、
    受け付けるもの）。いわなだれの相手の控え（最大 3 匹。3・1・2 匹を順に。0 匹は選ばない）。"""
    d = state.decision
    if d is None:
        return None
    if d.kind == USE_DISCARD_TRAINER:
        seen = counts["v058_use_discard_trainer_seen"]
        counts["v058_use_discard_trainer_seen"] += 1
        candidates = ([()] if seen % 4 == 3 else []) + [(o,) for o in reversed(d.options)] + [()]
        for choices in candidates:
            if _v052_accepted(state, ResolveDecision(d.player, d.id, choices)):
                if choices:
                    counts[f"v058_use_discard_{state.cards[choices[0]].card_id}"] += 1
                else:
                    counts["v058_use_discard_declined"] += 1
                return ResolveDecision(d.player, d.id, choices)
        counts["v058_use_discard_no_accepted_answer"] += 1
        return None
    if d.resume == "attack" and d.kind == SELECT_POKEMON and d.max_choices > 1:
        last = next((e for e in reversed(state.log) if e["kind"] == "attack"), None)
        if last is None or state.cards[last.get("card", last["pokemon"])].card_id != BROCKS_GOLEM:
            return None
        seen = counts["v058_rock_slide_seen"]
        counts["v058_rock_slide_seen"] += 1
        size = max(1, min(d.max_choices, len(d.options), (3, 1, 2)[seen % 3]))
        for choices in (tuple(d.options[:size]), tuple(d.options[-size:]), tuple(d.options[:1])):
            if _v052_accepted(state, ResolveDecision(d.player, d.id, choices)):
                counts[f"v058_rock_slide_{len(choices)}"] += 1
                return ResolveDecision(d.player, d.id, choices)
    return None


def _v058_retreat(state, tried, counts):
    """v0.58: バトル場のポケモンに無色2個エネルギーがついていて控えがいれば、4 番に 1 回、それだけをトラッシュして「にげる」を試す（にげるエネルギー 2 なら受け付け、1 なら
    RT1。拒否は ``v058_retreat_dce_rejected_<コード>`` に数え、別の操作を続ける）。"""
    player = state.current_player
    p = state.players[player]
    active = p.active
    if active is None or not p.bench or state.turn_number % 4 or ("v058_retreat", state.turn_number) in tried:
        return None
    dce = [u for u in active.energy if state.cards[u].card_id == DOUBLE_COLORLESS]
    if not dce:
        return None
    tried.add(("v058_retreat", state.turn_number))
    command = Retreat(player, (dce[0],), p.bench[0].card)
    try:
        apply_command(state, command)
    except (IllegalActionError, UnsupportedError) as error:
        counts[f"v058_retreat_dce_rejected_{error.code}"] += 1
        return None
    counts["v058_retreat_dce"] += 1
    return command


def _v068_retreat(state, tried, counts):
    """v0.68: バトル場のイマクニ？のドードー（にげるエネルギー 0。［にげまくり］は投げる動作を処理しない簡略化した仕様）に控えがいれば、3 番に 1 回、エネルギーカードを
    トラッシュせずに「にげる」を試す（拒否は ``v068_doduo_retreat_rejected_<コード>`` に数え、別の操作を続ける）。"""
    player = state.current_player
    p = state.players[player]
    active = p.active
    if active is None or not p.bench or state.turn_number % 3 or state.cards[active.card].card_id != IMAKUNI_DODUO \
            or ("v068_retreat", state.turn_number) in tried:
        return None
    tried.add(("v068_retreat", state.turn_number))
    command = Retreat(player, (), p.bench[0].card)
    try:
        apply_command(state, command)
    except (IllegalActionError, UnsupportedError) as error:
        counts[f"v068_doduo_retreat_rejected_{error.code}"] += 1
        return None
    counts["v068_doduo_retreat"] += 1
    return command


def _v059_power(state, tried, counts):
    """v0.59: マルマイン（第1弾）の［エネエネ］を、自分の場にほかのポケモンがいて、受け付けるとき、番の番号が 3 の倍数か、マルマインにダメージがあれば使う（1 番に 1 回）。
    拒否（BZ1〜BZ4・まきちらせ!ベトベトガス・ショックアイなど）は ``v059_buzzap_rejected_<コード>`` に数える。"""
    player = state.current_player
    p = state.players[player]
    if ("v059_buzzap", state.turn_number) in tried or len(list(p.in_play())) < 2:
        return None
    for pokemon in p.in_play():
        if state.cards[pokemon.card].card_id != BUZZAP_ELECTRODE or not (state.turn_number % 3 == 0 or pokemon.damage):
            continue
        tried.add(("v059_buzzap", state.turn_number))
        command = UsePokemonPower(player, pokemon.pokemon_id, 0)
        try:
            apply_command(state, command)
        except (IllegalActionError, UnsupportedError) as error:
            counts[f"v059_buzzap_rejected_{error.code}"] += 1
            return None
        counts["v059_buzzap_declared"] += 1
        return command
    return None


def _v059_decision(state, counts):
    """v0.59 の決定への答え（元の手順より先に答える）: ［エネエネ］のつける先（自分のバトル場のポケモン、なければ受け付ける最初の自分のポケモン）・色（つける先の
    タイプ。基本エネルギーの色でなければ受け付ける最初の色）・ショックアイの相手のポケモン（特殊能力を持つポケモン、なければバトル場）・タケシの保護のつける先。"""
    d = state.decision
    if d is None:
        return None
    if d.resume == "power" and d.kind in (SELECT_POKEMON, SELECT_COLOR):
        use = d.context_value("use")
        if use is None or use[2] != BUZZAP_ELECTRODE:
            return None
        if d.kind == SELECT_POKEMON:
            active = state.players[d.player].active
            order = ([active.pokemon_id] if active is not None else []) + list(d.options)
        else:
            target = state.find_pokemon(d.context_value("target"))
            own_type = state.card_def(target[1].card).pokemon_type if target is not None else None
            order = ([COLORS.index(own_type)] if own_type in COLORS else []) + list(d.options)
        for option in order:
            if option in d.options and _v052_accepted(state, ResolveDecision(d.player, d.id, (option,))):
                counts[f"v059_buzzap_{'target' if d.kind == SELECT_POKEMON else 'color'}"] += 1
                return ResolveDecision(d.player, d.id, (option,))
        counts["v059_buzzap_no_accepted_answer"] += 1
        return None
    if d.resume == "attack" and d.kind == SELECT_POKEMON:
        last = next((e for e in reversed(state.log) if e["kind"] == "attack"), None)
        if last is None or state.cards[last.get("card", last["pokemon"])].card_id != DARK_ARBOK:
            return None
        with_power = [o for o in d.options if state.card_def(state.find_pokemon(o)[1].card).powers]
        for option in (*with_power, *d.options):
            if _v052_accepted(state, ResolveDecision(d.player, d.id, (option,))):
                counts["v059_shock_eye_power_holder" if option in with_power else "v059_shock_eye_other"] += 1
                return ResolveDecision(d.player, d.id, (option,))
    return None


def _v059_trainer(state, tried, counts, only=V0_59_TRAINERS):
    """v0.59: まきちらせ!ベトベトガス（相手の場に特殊能力を持つポケモンがいて、効果がはたらいていないとき）・タケシの保護（自分の場のタケシのポケモンにまだついていないとき）・
    カツラ（この番に手札からまだつけておらず、手札に「炎」エネルギーカードが 2 枚以上あり、場にカツラのポケモンがいるとき）を、受け付けるなら使う。"""
    player = state.current_player
    p = state.players[player]
    if "trainer_locked" in tried:
        return None
    opponent_powers = any(state.card_def(pk.card).powers for pk in state.players[1 - player].in_play())
    for uid in p.hand:
        card_id = state.cards[uid].card_id
        key = ("v059_trainer", card_id, state.turn_number)
        if card_id not in only or key in tried:
            continue
        if card_id == GOOP_GAS_ATTACK and not (opponent_powers and not goop_gas_effects(state)):
            continue
        if card_id == BROCKS_PROTECTION and not any(state.card_def(pk.card).name_ja.startswith("タケシの") and not pk.trainers for pk in p.in_play()):
            continue
        if card_id == BLAINE_TRAINER and (state.energy_attachments_this_turn or blaine_effects(state, player)
                                          or sum(state.cards[u].card_id == FIRE for u in p.hand) < 2
                                          or not any(state.card_def(pk.card).name_ja.startswith("カツラの") for pk in p.in_play())):
            continue
        tried.add(key)
        command = PlayTrainer(player, uid)
        if not _v052_accepted(state, command):
            counts[f"v059_{card_id}_not_playable"] += 1
            continue
        counts[f"v059_play_{card_id}"] += 1
        return command
    return None


def _v059_energy(state, command, tried, counts):
    """v0.59: カツラの効果がはたらいていて、この番に手札からまだつけておらず、手札に「炎」エネルギーカードが 2 枚以上あれば、元の手順のかわりに 2 枚をいっしょに
    カツラのポケモン（バトル場を先に）につける（``AttachEnergy.energy2``）。受け付けない場面は ``v059_blaine_attach_rejected_<コード>`` に数える。"""
    if state.phase is not Phase.MAIN or state.energy_attachments_this_turn or ("v059_blaine_attach", state.turn_number) in tried:
        return None
    player = state.current_player
    if not blaine_effects(state, player):
        # 元の手順がつける前に、カツラを使う（使える場面なら。使ったら次の手でこの関数が 2 枚をつける）
        return _v059_trainer(state, set(), counts, only=(BLAINE_TRAINER,)) if isinstance(command, AttachEnergy) else None
    p = state.players[player]
    fire = [u for u in p.hand if state.cards[u].card_id == FIRE]
    targets = [pk for pk in p.in_play() if state.card_def(pk.card).name_ja.startswith("カツラの")]
    if len(fire) < 2 or not targets:
        return None
    tried.add(("v059_blaine_attach", state.turn_number))
    attach = AttachEnergy(player, fire[0], targets[0].card, energy2=fire[1])
    try:
        apply_command(state, attach)
    except (IllegalActionError, UnsupportedError) as error:
        counts[f"v059_blaine_attach_rejected_{error.code}"] += 1
        return None
    counts["v059_blaine_double_attach"] += 1
    return attach


def _v061_decision(state, counts):
    """v0.61 の決定への答え（元の手順より先に答える）: ［ファイナルビーム］を使うか。使うと止める（Z9・C18・RB1・BZ2）なら使わない。ほかは 1 局の中で
    4 回に 3 回使う（使わない場面も起こす）。"""
    d = state.decision
    if d is None or d.kind != KNOCK_OUT_POWER:
        return None
    unresolved = d.context_value("unresolved_choices", ())
    if unresolved:
        counts[f"v061_beam_stopped_{d.context_value('unresolved_code')}"] += 1
        return ResolveDecision(d.player, d.id, ())
    counts["v061_beam_offers"] += 1
    if counts["v061_beam_offers"] % 4 == 0:
        counts["v061_beam_declined_by_policy"] += 1
        return ResolveDecision(d.player, d.id, ())
    return ResolveDecision(d.player, d.id, (d.options[0],))


def _v065_decision(state, counts):
    """v0.65 の決定への答え（元の手順より先に答える。決めるのはワザを受ける相手プレイヤー）: 変わり身の術・［にげこむ］の入れ替え、［ベンチガード］。
    選ぶと止める選択（NT3・RX1・FL1・KD1 など）は選ばない。ほかは 1 局の中で 3 回に 2 回使い（入れ替えは控えを順に回す）、3 回に 1 回使わない。"""
    d = state.decision
    if d is None or d.kind not in V0_65_REACTIONS:
        return None
    stopped = set(d.context_value("unresolved_choices", ()))
    free = [o for o in d.options if o not in stopped]
    if stopped:
        counts[f"v065_{d.kind}_stopped_{d.context_value('unresolved_code')}"] += 1
    counts[f"v065_{d.kind}_offers"] += 1
    n = counts[f"v065_{d.kind}_offers"]
    if not free or n % 3 == 0:
        counts[f"v065_{d.kind}_declined_by_policy"] += 1
        return ResolveDecision(d.player, d.id, ())
    if d.kind == "bench_guard":
        size = min(d.max_choices, len(free), 1 + n % 2)
        counts[f"v065_bench_guard_used_{size}"] += 1
        return ResolveDecision(d.player, d.id, tuple(free[:size]))
    counts[f"v065_{d.kind}_used"] += 1
    return ResolveDecision(d.player, d.id, (free[n % len(free)],))


def _v065_trainer(state, tried, counts):
    """v0.65: 変わり身の術を、バトル場の「キョウのポケモン」にまだついていなければ、受け付けるなら使う（1 番に 1 回）。拒否・止まる場面は ``v065_trick_rejected_<コード>``。"""
    player = state.current_player
    p = state.players[player]
    if "trainer_locked" in tried or ("v065_trick", state.turn_number) in tried or p.active is None:
        return None
    uid = next((u for u in p.hand if state.cards[u].card_id == KOGAS_NINJA_TRICK), None)
    if uid is None or any(state.cards[t.card].card_id == KOGAS_NINJA_TRICK for t in p.active.trainers):
        return None
    tried.add(("v065_trick", state.turn_number))
    command = PlayTrainer(player, uid)
    try:
        apply_command(state, command)
    except (IllegalActionError, UnsupportedError) as error:
        counts[f"v065_trick_rejected_{error.code}"] += 1
        return None
    counts["v065_trick_played"] += 1
    return command


def _v066_decision(state, counts):
    """v0.66 の決定への答え（元の手順より先に答える）: お上品攻撃のへらす数・ナツメのESPのやり直し・カスミの勝負の手（相手の決定にも答える）。
    選ぶと止める選択は選ばない。へらす数は 0・いちばん大きい数・真ん中を順に、ESP はやり直す・やり直さないを交互に、じゃんけんの手は決めるプレイヤーごとに
    グー・チョキ・パーを順に回す（2 人の回し方を変えて、あいこも勝ち負けも起こる）。"""
    d = state.decision
    if d is None or d.kind not in V0_66_DECISIONS:
        return None
    stopped = set(d.context_value("unresolved_choices", ()))
    free = [o for o in d.options if o not in stopped]
    if stopped:
        counts[f"v066_{d.kind}_stopped_{d.context_value('unresolved_code')}"] += 1
    counts[f"v066_{d.kind}_offers"] += 1
    n = counts[f"v066_{d.kind}_offers"]
    if d.kind == "esp_redo":
        if not free or n % 2 == 0:
            counts["v066_esp_declined_by_policy"] += 1
            return ResolveDecision(d.player, d.id, ())
        counts["v066_esp_redo_by_policy"] += 1
        return ResolveDecision(d.player, d.id, (free[0],))
    if d.kind == "damage_reduction":
        if not free:
            raise AssertionError("お上品攻撃のへらす数に選べる答えがない")
        pick = (free[0], free[-1], free[len(free) // 2])[n % 3]
        counts[f"v066_reduction_{'zero' if pick == 0 else 'some'}"] += 1
        return ResolveDecision(d.player, d.id, (pick,))
    key = f"v066_janken_{d.player}"
    counts[key] += 1
    m = counts[key]
    # 2 人が同じ手を回し続けるとあいこが終わらないので、2 人目（プレイヤー 1）は回し方を変える（ときどきあいこになる）
    return ResolveDecision(d.player, d.id, (free[(m if d.player == 0 else m + m // 2) % len(free)],))


def _v066_trainer(state, command, tried, counts):
    """v0.66: お上品攻撃（ワザを使う番に、バトル場のポケモンにまだついていなければ）・ナツメのESP（ワザを使う番に、バトル場の「ナツメのポケモン」にまだついていなければ）・
    カスミの勝負（1 番に 1 回）を、受け付けるなら使う。拒否・止まる場面は ``v066_<カード>_rejected_<コード>``。"""
    player = state.current_player
    p = state.players[player]
    if "trainer_locked" in tried or p.active is None:
        return None
    attached = {state.cards[t.card].card_id for t in p.active.trainers}
    wanted = []
    if isinstance(command, UseAttack):
        if CHARITY not in attached:
            wanted.append(("charity", CHARITY))
        if SABRINAS_ESP not in attached and state.card_def(p.active.card).name_ja.startswith("ナツメの"):
            wanted.append(("esp", SABRINAS_ESP))
    wanted.append(("duel", MISTYS_DUEL))
    for label, card_id in wanted:
        if (f"v066_{label}", state.turn_number) in tried:
            continue
        uid = next((u for u in p.hand if state.cards[u].card_id == card_id), None)
        if uid is None:
            continue
        tried.add((f"v066_{label}", state.turn_number))
        trainer = PlayTrainer(player, uid)
        try:
            apply_command(state, trainer)
        except (IllegalActionError, UnsupportedError) as error:
            counts[f"v066_{label}_rejected_{error.code}"] += 1
            continue
        counts[f"v066_{label}_played"] += 1
        return trainer
    return None


def _v067_decision(state, counts):
    """v0.67 の決定への答え（元の手順より先に答える）: マチスの秘策でうらにして出すカード。たねポケモン・たねポケモンでないカード（進化カード・トレーナー・エネルギー）・
    出さない、を順に回す。選ぶと止める選択（爆発ジムの FD2）は選ばない。"""
    d = state.decision
    if d is None or d.kind != "secret_plan_card":
        return None
    stopped = set(d.context_value("unresolved_choices", ()))
    if stopped:
        counts[f"v067_place_stopped_{d.context_value('unresolved_code')}"] += 1
    free = [o for o in d.options if o not in stopped]
    counts["v067_place_offers"] += 1
    n = counts["v067_place_offers"]
    basic = [o for o in free if state.printed_def(o).is_basic_pokemon]
    other = [o for o in free if not state.printed_def(o).is_basic_pokemon]
    evolution = [o for o in other if state.printed_def(o).is_evolution_pokemon]
    if n % 5 == 0:
        pick = []
    elif n % 2 == 1:
        pick = basic or evolution or other
    else:
        pick = evolution or other or basic
    if not pick:
        counts["v067_place_declined_by_policy"] += 1
        return ResolveDecision(d.player, d.id, ())
    kind = "basic" if pick is basic else "other"
    counts[f"v067_place_{kind}"] += 1
    return ResolveDecision(d.player, d.id, (pick[0],))


def _v067_trainer(state, tried, counts):
    """v0.67: マチスの秘策（1 番に 1 回）を、受け付けるなら使う。"""
    player = state.current_player
    p = state.players[player]
    if ("v067_plan", state.turn_number) in tried:
        return None
    uid = next((u for u in p.hand if state.cards[u].card_id == LT_SURGES_SECRET_PLAN), None)
    if uid is None:
        return None
    tried.add(("v067_plan", state.turn_number))
    trainer = PlayTrainer(player, uid)
    try:
        apply_command(state, trainer)
    except (IllegalActionError, UnsupportedError) as error:
        counts[f"v067_plan_rejected_{error.code}"] += 1
        return None
    counts["v067_plan_played"] += 1
    return trainer


def _v067_reveal(state, tried, counts):
    """v0.67: 自分のうらのカードの扱い（自分の番の ``MAIN``。元の手順より先）。バトル場のうらのカードは、ワザ（位置 0）を受け付けるならワザを使っておもてにし、受け付けなければ
    ``RevealFaceDown``（元の手順はうらのカードの定義を読まないように、おもてにしてから続ける）。ベンチのうらのカードは、手札に重ねられる進化カードがあれば進化させて
    おもてにし（その番に出したカードは進化できないので拒否される）、なければ 4 番に 1 回おもてにする（ほかの番はうらのまま。相手のワザ・効果を受けておもてにすることもある）。"""
    if state.phase is not Phase.MAIN or not state.face_down_cards:
        return None
    player = state.current_player
    p = state.players[player]
    own = [q for q in p.in_play() if state.is_face_down(q)]
    if not own:
        return None
    if p.active is not None and state.is_face_down(p.active):
        if state.turn_number % 3 == 1 and p.bench and ("v067_retreat", state.turn_number) not in tried:
            # 「にげる」でおもてにする（「たねポケモン」でエネルギーが足りなければ拒否され、状態は変わらない）
            tried.add(("v067_retreat", state.turn_number))
            retreat = Retreat(player, tuple(p.active.energy[:1]), p.bench[0].card)
            try:
                apply_command(state, retreat)
            except (IllegalActionError, UnsupportedError) as error:
                counts[f"v067_retreat_rejected_{error.code}"] += 1
            else:
                counts["v067_retreat_from_face_down"] += 1
                return retreat
        if ("v067_attack", state.turn_number) not in tried:
            tried.add(("v067_attack", state.turn_number))
            attack = UseAttack(player, 0)
            try:
                apply_command(state, attack)
            except (IllegalActionError, UnsupportedError) as error:
                counts[f"v067_attack_rejected_{error.code}"] += 1
            else:
                counts["v067_attack_from_face_down"] += 1
                return attack
        counts["v067_reveal_active"] += 1
        return RevealFaceDown(player, p.active.pokemon_id)
    for q in own:
        real = state.printed_def(q.card)
        evolution = next((u for u in p.hand if state.printed_def(u).is_stage1_pokemon and real.is_basic_pokemon
                          and state.printed_def(u).evolves_from == real.name_ja), None)
        if evolution is None and not real.is_basic_pokemon and state.turn_number % 2 == 1:
            # たねポケモンでないうらのカードに進化カードを重ねようとする（おもてにしてトラッシュし、コマンドは受け付けられる）
            evolution = next((u for u in p.hand if state.printed_def(u).is_stage1_pokemon), None)
        if evolution is not None and ("v067_evolve", q.pokemon_id, state.turn_number) not in tried:
            tried.add(("v067_evolve", q.pokemon_id, state.turn_number))
            command = EvolvePokemon(player, evolution, q.pokemon_id)
            try:
                apply_command(state, command)
            except (IllegalActionError, UnsupportedError) as error:
                counts[f"v067_evolve_rejected_{error.code}"] += 1
                continue
            counts["v067_evolve_from_face_down"] += 1
            return command
    if state.turn_number % 4 == 0 and ("v067_reveal", state.turn_number) not in tried:
        tried.add(("v067_reveal", state.turn_number))
        counts["v067_reveal_bench"] += 1
        return RevealFaceDown(player, own[0].pokemon_id)
    return None


def _v067_fallback(state, tried, counts):
    """v0.67: 手順がうらのカードの定義を読めなかったときの、受け付けられるコマンド（本当の状態で確かめる）。決定なら選べるものの小さい答えから、自分の番ならワザ
    （位置 0・1・2）→ 番を終える。"""
    from kyuura_engine.resolution.programs import iter_answers

    d = state.decision
    candidates = []
    if d is not None:
        stopped = set(d.context_value("unresolved_choices", ()))
        candidates = [ResolveDecision(d.player, d.id, tuple(a)) for a in iter_answers(d) if not set(a) & stopped][:64]
    elif state.phase is Phase.MAIN:
        player = state.current_player
        candidates = [UseAttack(player, i) for i in range(3)] + [EndTurn(player)]
    for command in candidates:
        try:
            apply_command(state, command)
        except (IllegalActionError, UnsupportedError):
            continue
        counts[f"v067_fallback_{type(command).__name__}"] += 1
        return command
    raise AssertionError("うらのカードの定義を読めない手順の代わりのコマンドがない")


def _v069_step(state, command, tried, counts):
    """v0.69: 写しの組 pool_v0_69 のカード（新しい id）を、元のカードの手順（カード id で選ぶ）のかわりに使う手順（新しい id がない局では何もしない。前の版の局の操作は
    変わらない）。手札からつける通常の操作の前に、無色2個エネルギー（新しい id）をバトル場につける（2 番に 1 回）。宣言して使う特殊能力（新しい id）と、トレーナー
    （新しい id）を、受け付けるなら使う（どれもカード id ごとに 1 番に 1 回）。決定への答えは元の手順（決定の種類で答える）。受け付けない操作は使わず
    ``v069_<id>_not_usable_<コード>`` に数える。"""
    if state.phase is not Phase.MAIN or not isinstance(command, (AttachEnergy, UseAttack, EndTurn)):
        return None
    player = state.current_player
    p = state.players[player]
    new = NEW_IDS  # v0.71: 再録のカード（pool_v0_71）も同じ手順
    if not state.energy_attachments_this_turn and ("v069_energy", state.turn_number) not in tried and (state.turn_number // 2) % 2 == 0:
        tried.add(("v069_energy", state.turn_number))
        for uid in p.hand:
            card_id = state.cards[uid].card_id
            if card_id in new and state.card_def(uid).is_special_energy:
                attach = AttachEnergy(player, uid, p.active.card)
                if _v052_accepted(state, attach):
                    counts[f"v069_attach_{card_id}"] += 1
                    return attach
                counts[f"v069_{card_id}_not_usable"] += 1
    if not isinstance(command, (UseAttack, EndTurn)):
        return None
    for pokemon in p.in_play():
        card_id = state.cards[pokemon.card].card_id
        if card_id not in new or (f"v069_power_{card_id}", state.turn_number) in tried:
            continue
        for power in state.card_def(pokemon.card).powers:
            effect = state.effects.power_entry(card_id, power.index)
            if effect is None or not getattr(effect.effect, "declared", True):
                continue
            tried.add((f"v069_power_{card_id}", state.turn_number))
            use = UsePokemonPower(player, pokemon.pokemon_id, power.index)
            if _v052_accepted(state, use):
                counts[f"v069_power_{card_id}"] += 1
                return use
            counts[f"v069_{card_id}_power_not_usable"] += 1
    if "trainer_locked" in tried:
        return None
    for uid in p.hand:
        card_id = state.cards[uid].card_id
        if card_id not in new or state.card_def(uid).category != "trainer" or (f"v069_trainer_{card_id}", state.turn_number) in tried:
            continue
        tried.add((f"v069_trainer_{card_id}", state.turn_number))
        play = PlayTrainer(player, uid)
        if _v052_accepted(state, play):
            counts[f"v069_trainer_{card_id}"] += 1
            return play
        counts[f"v069_{card_id}_not_usable"] += 1
    return None


def _v069_decision(state, counts):
    """v0.69: 新しい id のトレーナーを使っている最中の決定（元の手順はカード id で答えるので、新しい id では答えられないことがある）のうち、ほかの手順が答えないものに、受け付ける答えのうち最初のもの
    （選べるものの並びの前から、選ぶ数の下限（0 なら 1）だけ）で答える。新しい id のトレーナーを使っていなければ何もしない（前の版の局の操作は変わらない）。"""
    d = state.decision
    use = state.trainer_in_use
    if d is None or d.resume != "trainer" or use is None or state.cards[use.card].card_id not in NEW_IDS:
        return None
    count = max(d.min_choices, 1) if d.max_choices else 0
    for start in range(max(1, len(d.options) - count + 1)):
        answer = ResolveDecision(d.player, d.id, tuple(d.options[start:start + count]))
        if _v052_accepted(state, answer):
            counts[f"v069_decision_{d.kind}"] += 1
            return answer
    return None


def _v073_decision(state, counts):
    """v0.73 の決定への答え（元の手順より先に答える）: 18 枚のトレーナーの決定（パソコン大暴走！の相手の決定にも答える）。受け付ける答えのうち、選ぶ数を「選べるだけ →
    下限 → 1」の順に回す（選ばない・最大の両方を起こす）。0 枚で止まる答え（SR2）は受け付けないので次の候補。v0.73 のトレーナーを使っていなければ何もしない。"""
    d = state.decision
    if d is None or d.resume != "trainer":
        return None
    use = d.context_value("use")
    if use is None or use[2] not in V0_73 + V0_77_TRAINERS:  # v0.77: neo1 のスーパーポケモン回収・マサキの転送装置も同じ手順で答える
        return None
    seen = counts[f"v073_{use[2]}_{d.kind}_seen"]
    counts[f"v073_{use[2]}_{d.kind}_seen"] += 1
    if d.kind == "select_draw_count":
        candidates = [(d.options[[-1, 0, min(1, len(d.options) - 1)][seen % 3]],), *[(o,) for o in d.options]]
    elif d.min_choices == d.max_choices == 1:
        candidates = [(d.options[seen % len(d.options)],), *[(o,) for o in d.options]]  # 選べるものを順に回す（スーパーポケモン回収のバトル場のポケモンも選ぶ）
    elif d.min_choices == d.max_choices:
        candidates = [tuple(d.options[-d.max_choices:])]
    else:
        size = [d.max_choices, d.min_choices, min(1, d.max_choices)][seen % 3]
        candidates = [tuple(d.options[:size]), tuple(d.options[-size:] if size else ()), *[(o,) for o in d.options], ()]
    for choices in candidates:
        if d.min_choices <= len(choices) <= d.max_choices and _v052_accepted(state, ResolveDecision(d.player, d.id, choices)):
            who = "opponent" if d.player != use[0] else "user"
            counts[f"v073_{use[2]}_{d.kind}_{who}_{choices[0] if d.kind == 'select_draw_count' else len(choices)}"] += 1
            return ResolveDecision(d.player, d.id, choices)
    counts[f"v073_{use[2]}_no_accepted_answer"] += 1
    return None


def _v073_trainer(state, command, tried, counts, only=None):
    """v0.73: 18 枚のトレーナーを、受け付けるなら使う（カード id ごとに 1 番に 1 回まで）。使う前に止まる・拒否される場面（MR1・ML1・SR1・FV1・HC6・ST1・
    BENCH_FULL・手札が足りない）は使わず ``v073_<カード>_not_playable_<コード>`` に数える。番を終えるパソコン大暴走！は、手順が番を終えるところでだけ使う。"""
    player = state.current_player
    if "trainer_locked" in tried:
        return None
    p = state.players[player]
    for uid in p.hand:
        card_id = state.cards[uid].card_id
        if card_id not in (V0_73 if only is None else only) or (f"v073_{card_id}", state.turn_number) in tried:
            continue
        if card_id in ("PR1-026", "PR1-041") and not isinstance(command, EndTurn):
            continue
        tried.add((f"v073_{card_id}", state.turn_number))
        play = PlayTrainer(player, uid)
        real = _V052_REAL.get("state")
        try:
            apply_command(real if real is not None and real.turn_number == state.turn_number and real.decision == state.decision else state, play)
        except (IllegalActionError, UnsupportedError) as error:
            counts[f"v073_{card_id}_not_playable_{error.code}"] += 1
            continue
        counts[f"v073_play_{card_id}"] += 1
        return play
    return None


def _v074_decision(state, counts):
    """v0.74 の決定への答え（元の手順より先に答える）: エネルギースタジアム・キョウの忍者ジムの「おもて」のあとの 1 枚（選べるものを順に回す。選ぶと止める GG1 の選択は
    受け付けないので次の候補）。v0.74 のスタジアムの決定でなければ何もしない。"""
    d = state.decision
    if d is None or d.resume != "stadium" or d.context_value("stage") not in ("energy_stadium", "ninja_gym"):
        return None
    stage = d.context_value("stage")
    seen = counts[f"v074_{stage}_seen"]
    counts[f"v074_{stage}_seen"] += 1
    for choices in [(d.options[seen % len(d.options)],), *[(o,) for o in d.options]]:
        if _v052_accepted(state, ResolveDecision(d.player, d.id, choices)):
            counts[f"v074_{stage}_answered"] += 1
            return ResolveDecision(d.player, d.id, choices)
    counts[f"v074_{stage}_no_accepted_answer"] += 1
    return None


def _v074_trainer(state, tried, counts):
    """v0.74: 手札の v0.74 のスタジアムを、場のスタジアムと名前が違えば出す（同じ名前の別のカードへの入れかえも 3 番に 1 回は試し、RS1 の場面を起こす）。スタジアムごとに 1 番に
    1 回まで。ポケモンタワーが場にあるときは、効果がすべて消えるトレーナー（エネルギー回収・ダウジングマシーン）も試し、受け付けない場面（PT1・手札が足りない）は
    ``v074_<カード>_not_playable_<コード>`` に数える（受け付けるなら使う）。"""
    player = state.current_player
    if "trainer_locked" in tried:
        return None
    p = state.players[player]
    current = None if state.stadium is None else state.card_def(state.stadium.card).name_ja
    for uid in p.hand:
        card_id = state.cards[uid].card_id
        if card_id not in V0_74 + V0_74_RECOVERY or (f"v074_{card_id}", state.turn_number) in tried:
            continue
        if card_id in V0_74_RECOVERY and (state.stadium is None or state.cards[state.stadium.card].card_id != V0_74_TOWER):
            continue  # エネルギー回収・ダウジングマシーンは、ポケモンタワーが場にあるときだけ試す（前の版の組の手順を変えない）
        if card_id in V0_74 and state.card_def(uid).name_ja == current and state.turn_number % 3:
            continue
        tried.add((f"v074_{card_id}", state.turn_number))
        play = PlayTrainer(player, uid)
        real = _V052_REAL.get("state")
        try:
            apply_command(real if real is not None and real.turn_number == state.turn_number and real.decision == state.decision else state, play)
        except (IllegalActionError, UnsupportedError) as error:
            counts[f"v074_{card_id}_not_playable_{error.code}"] += 1
            continue
        counts[f"v074_play_{card_id}"] += 1
        return play
    return None


def _v074_stadium(state, tried, counts):
    """v0.74: 場の v0.74 のスタジアム（ラッキースタジアム・エネルギースタジアム・キョウの忍者ジム）を、受け付けるなら使う。1 番に 2 回まで試す（2 回目は STADIUM_ALREADY_USED・
    PRN-027 の LK1 の場面を起こす）。止まる・拒否される場面（RS1・LK1・EN1・NJ1・STB1・GG1）は使わず ``v074_use_<カード>_rejected_<コード>`` に数える。"""
    stadium = state.stadium
    if stadium is None or state.cards[stadium.card].card_id not in V0_74 or state.cards[stadium.card].card_id == V0_74_TOWER:
        return None
    card_id = state.cards[stadium.card].card_id
    player = state.current_player
    attempt = sum(1 for marker in tried if marker[:2] == ("v074_stadium", state.turn_number))
    if attempt >= 2:
        return None
    tried.add(("v074_stadium", state.turn_number, attempt))
    command = UseStadium(player)
    real = _V052_REAL.get("state")  # 手札を隠した写し（v0.46〜v0.48 の手順）ではなく、本当の状態で確かめる
    try:
        apply_command(real if real is not None and real.turn_number == state.turn_number and real.decision == state.decision else state, command)
    except (IllegalActionError, UnsupportedError) as error:
        counts[f"v074_use_{card_id}_rejected_{error.code}"] += 1
        return None
    counts[f"v074_use_{card_id}"] += 1
    return command


def v076_uses(state):
    """v0.76: ログから数えた v0.76 のカードのワザの動き（ない局では空）。``attack_<id>#<位置>``（宣言。まねたワザは ``copied_<id>#<位置>``）・``effect_<種類>``（v0.76 のワザが与えた
    持続する効果）・``coin_<id>#<位置>_<面>``（v0.76 のワザのコイン）・``boosted``（v0.76 のワザが与えた 2 段階の「数をかける」「その数にする」効果がはたらいたダメージ）・
    ``reduced``（なきごえの 2 段階）・``failed``（ワザの失敗）。"""
    counts = Counter()
    current = None
    for e in state.log:
        kind = e["kind"]
        if kind == "attack":
            current = f"{state.cards[e['pokemon']].card_id}#{e['attack_index']}" if "card_id" not in e else f"{e['card_id']}#{e['attack_index']}"
            if current.split("#")[0] in V0_76:
                counts[f"attack_{current}"] += 1
            continue
        if kind == "copy_attack" and str(e.get("copied", "")).split("#")[0] in V0_76:
            counts[f"copied_{e['copied']}"] += 1
        if kind == "damage":
            for label, _ in e.get("steps") or ():
                if str(label).startswith("2 ") and "reduced_damage_to_source_next_turn" in str(label):
                    counts["reduced"] += 1
                elif str(label)[2:] in ("きあいだめ", "ウォーターパワー", "はずむ", "きあいいっぱつ") and current and current.split("#")[0] in V0_76:
                    counts[f"boosted_{str(label)[2:]}"] += 1
        effect = str(e.get("effect", ""))
        if effect.split("#")[0] not in V0_76:
            continue
        if kind == "persistent_effect_added":
            counts[f"effect_{e['persistent_effect']}"] += 1
        elif kind == "coin_flip" and e.get("source") == "attack":
            counts[f"coin_{effect}_{e['result']}"] += 1
        elif kind == "attack_failed":
            counts["failed"] += 1
    return dict(counts)


def _v078_energy(state, command, tried, counts):
    """v0.78: この番に手札からまだエネルギーカードをつけておらず、手札に悪・鋼エネルギーがあれば、元の手順のかわりにつける（元の手順は基本エネルギーだけをつける）。つけ先は、
    ワザに必要なエネルギーにその色（「悪」「鋼」）があり、まだ払えないポケモン（バトル場 → ベンチ）。なければ 3 番に 1 回はバトル場（「悪」「鋼」でないポケモンにつく場面を
    起こす）、ほかは何もしない。受け付けない場面はつけず ``v078_attach_<カード>_rejected_<コード>`` に数える。"""
    if state.phase is not Phase.MAIN or state.energy_attachments_this_turn or ("v078_energy", state.turn_number) in tried:
        return None
    if not isinstance(command, (AttachEnergy, UseAttack, EndTurn)):
        return None
    player = state.current_player
    p = state.players[player]
    specials = [u for u in p.hand if state.cards[u].card_id in V0_78_ENERGIES]
    if not specials:
        return None
    tried.add(("v078_energy", state.turn_number))
    for uid in specials:
        card_id = state.cards[uid].card_id
        color = EnergyType.METAL if card_id in ("neo1-095", "NIP1X-010") else EnergyType.DARKNESS
        target = None
        for pk in p.in_play():
            if state.is_face_down(pk):
                continue
            attacks = state.card_def(current_form(state, pk).card).attacks
            if any(color in a.cost and not attack_cost_payable(state, pk, a) for a in attacks):
                target = pk
                break
        if target is None and state.turn_number % 3 == 0 and p.active is not None and not state.is_face_down(p.active):
            target = p.active
        if target is None:
            continue
        try:
            apply_command(_V052_REAL.get("state") if _V052_REAL.get("state") is not None and _V052_REAL["state"].turn_number == state.turn_number
                          and _V052_REAL["state"].decision == state.decision else state, AttachEnergy(player, uid, target.card))
        except (IllegalActionError, UnsupportedError) as error:
            counts[f"v078_attach_{card_id}_rejected_{error.code}"] += 1
            continue
        where = "active" if target is p.active else "bench"
        counts[f"v078_attach_{card_id}_{where}"] += 1
        return AttachEnergy(player, uid, target.card)
    return None


def _v080_decision(state, counts):
    """v0.80 の決定への答え（元の手順より先に答える）: 30 枚のトレーナーの決定（相手プレイヤーの決定にも答える）とラジオとうの見る枚数。受け付ける答えのうち、選ぶ数を
    「選べるだけ → 下限 → 1」の順に回し、1 つを選ぶ決定は選べるものを順に回す（止まる答えは受け付けないので次の候補）。v0.80 のカードを使っていなければ何もしない。"""
    d = state.decision
    if d is None:
        return None
    if d.resume == "stadium" and d.context_value("stage") == "radio_tower":
        key = "v080_radio_tower"
    elif d.resume == "trainer" and d.context_value("use") is not None and d.context_value("use")[2] in V0_80:
        key = f"v080_{d.context_value('use')[2]}"
    else:
        return None
    seen = counts[f"{key}_{d.kind}_seen"]
    counts[f"{key}_{d.kind}_seen"] += 1
    if d.min_choices == d.max_choices == 1 or (d.min_choices == 0 and d.max_choices == 1):
        candidates = [(d.options[seen % len(d.options)],), *[(o,) for o in d.options], ()]
    elif d.min_choices == d.max_choices:
        candidates = [tuple(d.options[:d.max_choices]), tuple(d.options[-d.max_choices:])]
    else:
        size = [d.max_choices, d.min_choices, min(1, d.max_choices)][seen % 3]
        candidates = [tuple(d.options[:size]), tuple(d.options[-size:] if size else ()), *[(o,) for o in d.options], ()]
    for choices in candidates:
        if d.min_choices <= len(choices) <= d.max_choices and _v052_accepted(state, ResolveDecision(d.player, d.id, choices)):
            who = "opponent" if d.resume == "trainer" and d.player != d.context_value("use")[0] else "user"
            counts[f"{key}_{d.kind}_{who}_{len(choices)}"] += 1
            return ResolveDecision(d.player, d.id, choices)
    counts[f"{key}_no_accepted_answer"] += 1
    return None


def _v080_trainer(state, tried, counts):
    """v0.80: 手札の 30 枚のトレーナーを、受け付けるなら使う（カード id ごとに 1 番に 1 回まで。スタジアムは場のスタジアムと名前が違うときだけ出す）。使う前に止まる・拒否される場面
    （SRD1・UPZ2・TOP1・HY1・MK1・BP1・HF1・FC1・TL1・TOO_MANY_CARDS_IN_HAND・手札からのトレーナーの使用の禁止など）は使わず ``v080_<カード>_not_playable_<コード>`` に数える。"""
    player = state.current_player
    if "trainer_locked" in tried:
        return None
    p = state.players[player]
    current = None if state.stadium is None else state.card_def(state.stadium.card).name_ja
    for uid in p.hand:
        card_id = state.cards[uid].card_id
        if card_id not in V0_80 or (f"v080_{card_id}", state.turn_number) in tried:
            continue
        if card_id in V0_80_STADIUMS and state.card_def(uid).name_ja == current:
            continue
        tried.add((f"v080_{card_id}", state.turn_number))
        play = PlayTrainer(player, uid)
        real = _V052_REAL.get("state")
        try:
            apply_command(real if real is not None and real.turn_number == state.turn_number and real.decision == state.decision else state, play)
        except (IllegalActionError, UnsupportedError) as error:
            counts[f"v080_{card_id}_not_playable_{error.code}"] += 1
            continue
        counts[f"v080_play_{card_id}"] += 1
        return play
    return None


def _v080_stadium(state, tried, counts):
    """v0.80: 場の v0.80 のスタジアム（いやしの野原・エネルギースタジアム・ラッキースタジアム・ラジオとう）を、受け付けるなら使う（1 番に 2 回まで試す。2 回目は
    STADIUM_ALREADY_USED の場面）。止まる・拒否される場面（HF1・EN1・STB1 など）は ``v080_use_<カード>_rejected_<コード>`` に数える。"""
    stadium = state.stadium
    if stadium is None or state.cards[stadium.card].card_id not in V0_80_STADIUMS:
        return None
    card_id = state.cards[stadium.card].card_id
    attempt = sum(1 for marker in tried if marker[:2] == ("v080_stadium", state.turn_number))
    if attempt >= 2:
        return None
    tried.add(("v080_stadium", state.turn_number, attempt))
    command = UseStadium(state.current_player)
    real = _V052_REAL.get("state")
    try:
        apply_command(real if real is not None and real.turn_number == state.turn_number and real.decision == state.decision else state, command)
    except (IllegalActionError, UnsupportedError) as error:
        counts[f"v080_use_{card_id}_rejected_{error.code}"] += 1
        return None
    counts[f"v080_use_{card_id}"] += 1
    return command


def _v081_decision(state, counts):
    """v0.81 の決定への答え（元の手順より先に答える）: v0.81 のどうぐ・ピントレンズをつけるポケモン（選べるものを順に回す）と、学習装置（相手プレイヤーの決定。つけ替える・
    つけ替えないを交互に）。受け付ける答えだけを選ぶ。v0.81 のカードを使っていなければ何もしない。"""
    d = state.decision
    if d is None:
        return None
    if d.kind == "exp_all_energy":
        key = "v081_exp_all"
    elif d.resume == "trainer" and d.context_value("use") is not None and d.context_value("use")[2] in V0_81:
        key = f"v081_{d.context_value('use')[2]}"
    else:
        return None
    seen = counts[f"{key}_{d.kind}_seen"]
    counts[f"{key}_{d.kind}_seen"] += 1
    if d.kind == "exp_all_energy":
        candidates = [(d.options[0],), ()] if seen % 2 == 0 else [(), (d.options[0],)]
    else:
        candidates = [(d.options[seen % len(d.options)],), *[(o,) for o in d.options]]
    for choices in candidates:
        if d.min_choices <= len(choices) <= d.max_choices and _v052_accepted(state, ResolveDecision(d.player, d.id, choices)):
            counts[f"{key}_{d.kind}_{len(choices)}"] += 1
            return ResolveDecision(d.player, d.id, choices)
    counts[f"{key}_no_accepted_answer"] += 1
    return None


def _v081_trainer(state, tried, counts):
    """v0.81: 手札の v0.81 のカードを、受け付けるなら使う（カード id ごとに 1 番に 1 回まで。スタジアムは場のスタジアムと名前が違うときだけ出す）。使う前に止まる・拒否される
    場面（TR1・手札からのトレーナーの使用の禁止など）は使わず ``v081_<カード>_not_playable_<コード>`` に数える。"""
    player = state.current_player
    p = state.players[player]
    current = None if state.stadium is None else state.card_def(state.stadium.card).name_ja
    for uid in p.hand:
        card_id = state.cards[uid].card_id
        if card_id not in V0_81 or (f"v081_{card_id}", state.turn_number) in tried:
            continue
        if card_id in V0_81_STADIUMS and state.card_def(uid).name_ja == current:
            continue
        tried.add((f"v081_{card_id}", state.turn_number))
        play = PlayTrainer(player, uid)
        real = _V052_REAL.get("state")
        try:
            apply_command(real if real is not None and real.turn_number == state.turn_number and real.decision == state.decision else state, play)
        except (IllegalActionError, UnsupportedError) as error:
            counts[f"v081_{card_id}_not_playable_{error.code}"] += 1
            continue
        counts[f"v081_play_{card_id}"] += 1
        return play
    return None


def _v082_decision(state, counts):
    """v0.82 のワザの決定への答え（元の手順より先に答える）: らいげきの「のぞむなら」（すべて・しないを交互に）、ファイヤーバーン・かえんじごくの「のぞむなら」（選べるだけ →
    1 枚 → 0 枚を回す）、ほかの v0.82 のワザの決定（エレメンタルブラスト・ひばな・ハイパーフレイム・ヒートフレイム・あたためる・ほのおのかぜ・デンキとばし。選べるものを
    順に回す）。受け付ける答えだけを選ぶ。番のプレイヤーのバトル場のポケモンが v0.82 のポケモンでなければ何もしない。"""
    d = state.decision
    if d is None or d.resume != "attack" or d.player != state.current_player:
        return None
    active = state.players[state.current_player].active
    if active is None or state.cards[active.card].card_id not in V0_82_POKEMON:
        return None
    card_id = state.cards[active.card].card_id
    key = f"v082_{card_id}_{d.kind}"
    seen = counts[f"{key}_seen"]
    counts[f"{key}_seen"] += 1
    if d.kind == "optional_discard_all":
        candidates = [(1,), ()] if seen % 2 == 0 else [(), (1,)]
    elif d.kind == "discard_energy" and d.min_choices == 0:
        top = tuple(d.options[:d.max_choices])
        candidates = [[top, tuple(d.options[:1]), ()], [tuple(d.options[:1]), (), top], [(), top, tuple(d.options[:1])]][seen % 3]
    else:
        count = max(d.min_choices, 1) if d.max_choices else 0
        rotated = list(d.options[seen % len(d.options):]) + list(d.options[:seen % len(d.options)]) if d.options else []
        candidates = [tuple(rotated[:count]), *[(o,) for o in d.options]]
    for choices in candidates:
        if d.min_choices <= len(choices) <= d.max_choices and _v052_accepted(state, ResolveDecision(d.player, d.id, choices)):
            counts[f"{key}_{len(choices)}"] += 1
            return ResolveDecision(d.player, d.id, choices)
    counts[f"{key}_no_accepted_answer"] += 1
    return None


def _v082_trainer(state, tried, counts):
    """v0.82: 手札のエコロジムを、場のスタジアムと名前が違い、受け付けるなら出す（1 番に 1 回まで）。受け付けない場面は ``v082_<カード>_not_playable_<コード>`` に数える。"""
    player = state.current_player
    p = state.players[player]
    current = None if state.stadium is None else state.card_def(state.stadium.card).name_ja
    for uid in p.hand:
        card_id = state.cards[uid].card_id
        if card_id not in V0_82_TRAINERS or (f"v082_{card_id}", state.turn_number) in tried or state.card_def(uid).name_ja == current:
            continue
        tried.add((f"v082_{card_id}", state.turn_number))
        play = PlayTrainer(player, uid)
        real = _V052_REAL.get("state")
        try:
            apply_command(real if real is not None and real.turn_number == state.turn_number and real.decision == state.decision else state, play)
        except (IllegalActionError, UnsupportedError) as error:
            counts[f"v082_{card_id}_not_playable_{error.code}"] += 1
            continue
        counts[f"v082_play_{card_id}"] += 1
        return play
    return None


def _v082_energy(state, command, tried, counts):
    """v0.82: この番に手札からまだエネルギーカードをつけておらず、手札にリサイクルエネルギーがあれば、2 番に 1 回、元の手順のかわりにつける（元の手順は基本エネルギーだけを
    つける）。つけ先は、ワザに必要なエネルギーをまだ払えないポケモン（バトル場 → ベンチ）。受け付けない場面はつけず ``v082_attach_rejected_<コード>`` に数える。"""
    if state.phase is not Phase.MAIN or state.energy_attachments_this_turn or ("v082_energy", state.turn_number) in tried:
        return None
    if not isinstance(command, (AttachEnergy, UseAttack, EndTurn)) or state.turn_number % 4 not in (1, 2):
        return None
    player = state.current_player
    p = state.players[player]
    recycle = [u for u in p.hand if state.cards[u].card_id == RECYCLE_ENERGY]
    if not recycle:
        return None
    tried.add(("v082_energy", state.turn_number))
    for pk in p.in_play():
        if state.is_face_down(pk):
            continue
        attacks = state.card_def(current_form(state, pk).card).attacks
        if not any(not attack_cost_payable(state, pk, a) for a in attacks):
            continue
        attach = AttachEnergy(player, recycle[0], pk.card)
        real = _V052_REAL.get("state")
        try:
            apply_command(real if real is not None and real.turn_number == state.turn_number and real.decision == state.decision else state, attach)
        except (IllegalActionError, UnsupportedError) as error:
            counts[f"v082_attach_rejected_{error.code}"] += 1
            continue
        counts[f"v082_attach_{'active' if pk is p.active else 'bench'}"] += 1
        return attach
    return None


def v082_uses(state):
    """v0.82: ログから数えた v0.82 のカードの動き（ない局では空）。``attack_<id>#<位置>``（v0.82 のポケモンのワザを使った）・``returned_<理由>_<原因>``（場からトラッシュに
    置かれて手札にもどしたエネルギーカード）・``play_<id>``・``recycle_reattached``（もどしたリサイクルエネルギーをもう一度つけた）・``discard_declined``（のぞむならトラッシュ
    しなかった）・``discard_failed_<扱い>``（トラッシュできなかった）・``attack_failed_<理由>``（v0.82 のワザの失敗）・``self_damage``（しゃくねつのほのおの自分へのダメージ）・
    ``bench_coin_damage``（ほのおのかぜの控えへのダメージ）・``ecogym_in_play_discards``（エコロジムが場にあるあいだに場からトラッシュに置かれたエネルギーカードの数）。"""
    counts = Counter()
    if not any(state.cards[uid].card_id in V0_82 for uid in state.cards):
        return counts
    eco = None
    returned = set()
    for e in state.log:
        kind = e["kind"]
        effect = e.get("effect")
        ours = isinstance(effect, str) and effect.split("#")[0] in V0_82_POKEMON
        if kind == "attack" and ours:
            counts[f"attack_{effect}"] += 1
        elif kind == "play_trainer" and e.get("card") is not None and state.cards[e["card"]].card_id in V0_82:
            counts[f"play_{state.cards[e['card']].card_id}"] += 1
        elif kind == "stadium_placed":
            eco = e["card"] if state.cards[e["card"]].card_id in V0_82_TRAINERS else None
        elif kind == "stadium_discarded" and e.get("card") == eco:
            eco = None
        elif kind == "energy_returned_to_hand":
            for reason in e["reasons"]:
                counts[f"returned_{reason}_{e['cause']}"] += 1
            returned.add(e["card"])
        elif kind == "attach_energy" and e.get("energy") in returned:
            counts["recycle_reattached"] += 1
        elif kind == "discard_energy_declined" and ours:
            counts["discard_declined"] += 1
        elif kind == "discard_energy_failed" and ours:
            counts[f"discard_failed_{e['outcome']}"] += 1
        elif kind == "attack_failed" and ours:
            counts[f"attack_failed_{e.get('reason')}"] += 1
        elif kind == "damage" and ours and e.get("target") == "self":
            counts["self_damage"] += 1
        elif kind == "damage" and ours and e.get("target") == "opponent_bench":
            counts["bench_coin_damage"] += 1
        if eco is not None and kind in ("discard_energy", "discard_attached_energy", "trainer_discard_energy", "energy_drain_discard"):
            counts["ecogym_in_play_discards"] += 1
    return counts


def v081_uses(state):
    """v0.81: ログから数えた v0.81 のカードの動き（ない局では空）。``play_<id>``（手札から使った・出した）・``attach_<id>``（つけた）・``discard_<id>_<理由>``（効果を使い終えた・
    「にげる」でトラッシュしたどうぐ）・``tool_heal``・``miracle_cure``・``focus_band_heads``・``focus_band_tails``・``claw_heads``・``claw_tails``・``claw_counters``・``exp_all_moved``・
    ``exp_all_declined``・``lens_ignored_resistance``・``tower_reduced``・``bumpy_retreat``・``balloon_retreat``・``hideout_dark_hp``（ロケット団のアジトが場にあるあいだに、わるい
    ポケモンがダメージを受けた回数）・``knock_out_with_tool``（どうぐのついたままきぜつした）。"""
    counts = Counter()
    if not any(state.cards[uid].card_id in V0_81 for uid in state.cards):
        return counts
    hideout = None
    for e in state.log:
        kind = e["kind"]
        card = e.get("card")
        if kind == "play_trainer" and card is not None and state.cards[card].card_id in V0_81:
            counts[f"play_{state.cards[card].card_id}"] += 1
        elif kind == "stadium_placed":
            hideout = card if state.cards[card].card_id == "neo3-057" else None
        elif kind == "stadium_discarded" and card == hideout:
            hideout = None
        elif kind == "attach_trainer" and state.cards[card].card_id in V0_81:
            counts[f"attach_{state.cards[card].card_id}"] += 1
        elif kind == "discard_attached_trainer" and state.cards[card].card_id in V0_81:
            counts[f"discard_{state.cards[card].card_id}_{e.get('reason')}"] += 1
        elif kind == "tool_heal":
            counts["tool_heal"] += 1
        elif kind == "special_conditions_removed" and e.get("tool_card") is not None:
            counts["miracle_cure"] += 1
        elif kind == "focus_band":
            counts["focus_band_heads" if e["survived"] else "focus_band_tails"] += 1
        elif kind == "counter_claw":
            counts[f"claw_{e['result']}"] += 1
        elif kind == "tool_damage_counters":
            counts["claw_counters"] += 1
        elif kind == "tool_move_energy":
            counts["exp_all_moved"] += 1
        elif kind == "exp_all_declined":
            counts["exp_all_declined"] += 1
        elif kind == "damage":
            if e.get("resistance_ignored_by") is not None:
                counts["lens_ignored_resistance"] += 1
            if any(state.cards[source].card_id == "neo1-085" for _, source, _ in e.get("modifiers", ()) if source is not None):
                counts["tower_reduced"] += 1
            if hideout is not None and state.card_def(e["pokemon"]).name_ja.startswith("わるい"):
                counts["hideout_dark_hp"] += 1
        elif kind in ("retreat", "retreat_failed"):
            if any(state.cards[c].card_id == "neo4-110" for c, _ in e.get("retreat_cost_stadium", ())):
                counts["bumpy_retreat"] += 1
            if e.get("retreat_cost_zeroed"):
                counts["balloon_retreat"] += 1
        elif kind == "knock_out" and any(state.cards[c].card_id in V0_81 for c in e.get("discarded_trainers", ())):
            counts["knock_out_with_tool"] += 1
    return counts


def v080_uses(state):
    """v0.80: ログから数えた v0.80 のカードの動き（ない局では空）。``play_<id>``（手札から使った・出した）・``coin_<id>_<面>``（トレーナー・スタジアムのコイン）・
    ``stadium_used_<id>``・``hand_lock``（手札からのトレーナーの使用の禁止を加えた回数）・``evolution_ban``（退化スプレーHYPER）・``effect_guard_prevented``（エフェクトガードで
    受けなかった効果）・``prize_revealed``・``prizes_redealt``・``quiz_kind_correct``・``quiz_kind_wrong``・``bench_from_deck``（ポケモンマーチ）・``remove_counters``（v0.80 のトレーナーで
    とりのぞいた回数）。"""
    counts = Counter()
    played = {}
    for e in state.log:
        kind = e["kind"]
        card = e.get("card")
        if kind in ("play_trainer", "stadium_placed") and card is not None and state.cards[card].card_id in V0_80:
            counts[f"play_{state.cards[card].card_id}"] += 1
            played[card] = state.cards[card].card_id
        elif kind == "coin_flip" and e.get("source") in ("trainer", "stadium") and card is not None and state.cards[card].card_id in V0_80:
            counts[f"coin_{state.cards[card].card_id}_{e['result']}"] += 1
        elif kind == "stadium_used" and card is not None and state.cards[card].card_id in V0_80:
            counts[f"stadium_used_{state.cards[card].card_id}"] += 1
        elif kind == "trainer_lock_added" and e.get("origin") == "hand":
            counts["hand_lock"] += 1
        elif kind == "trainer_effect_added" and e.get("effect_kind", e.get("trainer_effect")) == "evolution_ban":
            counts["evolution_ban"] += 1
        elif kind == "effect_prevented" and e.get("persistent_effect") == "effect_guard":
            counts["effect_guard_prevented"] += 1
        elif kind == "prize_revealed":
            counts["prize_revealed"] += 1
        elif kind == "prizes_to_deck":
            counts["prizes_redealt"] += 1
        elif kind == "quiz_kind_reveal":
            counts["quiz_kind_correct" if e.get("correct") else "quiz_kind_wrong"] += 1
        elif kind == "trainer_bench_from_deck":
            counts["bench_from_deck"] += 1
        elif kind in ("remove_damage_counters", "stadium_heal") and e.get("trainer_card", card) in played:
            counts["remove_counters"] += 1
    return counts


def v079_uses(state):
    """v0.79: ログから数えた v0.79 のカードの動き（ない局では空）。``attack_<id>#<位置>``（宣言。まねたワザは数えない）・``coin_<id>#<位置>_<面>``・``effect_<種類>``（v0.79 の
    ワザが与えた持続する効果）・``status_<種類>``（v0.79 のワザで付けた特殊状態）・``failed``・``bench_damage``（控えへのダメージ）・``discard_energy``・``discard_energy_skipped``・
    ``trainers_discarded``（だましとる）・``search``・``search_none``（ひらめく）・``heal``・``evolve_<id>``・``locked_attack``（メタルクラッシュ・おおなみの効果のある番の
    ワザの宣言の拒否は手順が数える）。"""
    counts = Counter()
    for e in state.log:
        kind = e["kind"]
        if kind == "attack":
            current = f"{state.cards[e['pokemon']].card_id}#{e['attack_index']}" if "card_id" not in e else f"{e['card_id']}#{e['attack_index']}"
            if current.split("#")[0] in V0_79:
                counts[f"attack_{current}"] += 1
        if kind == "evolve" and e.get("to_card_id") in V0_79:
            counts[f"evolve_{e['to_card_id']}"] += 1
        effect = str(e.get("effect", ""))
        if effect.split("#")[0] not in V0_79:
            continue
        if kind == "persistent_effect_added":
            counts[f"effect_{e['persistent_effect']}"] += 1
        elif kind == "special_condition":
            counts[f"status_{e.get('condition')}"] += 1
        elif kind == "coin_flip" and e.get("source") == "attack":
            counts[f"coin_{effect}_{e['result']}"] += 1
        elif kind == "attack_failed":
            counts["failed"] += 1
        elif kind == "damage" and e.get("target") in ("opponent_bench", "self_bench"):
            counts["bench_damage"] += 1
        elif kind == "discard_energy":
            counts["discard_energy"] += 1
        elif kind == "discard_energy_failed":
            counts["discard_energy_skipped"] += 1
        elif kind == "discard_attached_trainer" and e.get("reason") == "attack":
            counts["trainers_discarded"] += 1
        elif kind == "reveal_from_deck":
            counts["search"] += 1
        elif kind == "reveal_from_deck_none":
            counts["search_none"] += 1
        elif kind == "attack_heal":
            counts["heal"] += 1
    return counts


def v078_uses(state):
    """v0.78: ログから数えた v0.78 のカードの動き（ない局では空）。``attack_<id>#<位置>``（宣言）・``coin_<id>#<位置>_<面>``・``effect_<種類>``（v0.78 のワザが与えた持続する
    効果）・``failed``・``plunder_trainers``（ごうだつでトラッシュしたトレーナー）・``evolve_<id>``・``darkness_bonus``・``metal_attacker``・``metal_defender``（ワザのダメージの
    5・7 段階に悪・鋼エネルギーがあった回数）・``darkness_damage``・``darkness_damage_reduced``・``darkness_counters``（ポケモンチェックの悪エネルギー）・``metal_nonattack``
    （ワザでないダメージを鋼エネルギー（NIP1X-010）で減らした回数）・``nonattack_zeroed``（v0.79: そのうち最終のダメージが 0 になった回数。悪エネルギーのダメージも含む。
    ``darkness_damage_reduced`` は悪エネルギーの 10 ダメージを減らした回数だけで、意味を変えていない）・``attached_<id>``（手札からつけた悪・鋼エネルギー）。"""
    counts = Counter()
    for e in state.log:
        kind = e["kind"]
        if kind == "attack":
            current = f"{state.cards[e['pokemon']].card_id}#{e['attack_index']}" if "card_id" not in e else f"{e['card_id']}#{e['attack_index']}"
            if current.split("#")[0] in V0_78:
                counts[f"attack_{current}"] += 1
        if kind == "attach_energy" and state.cards[e["energy"]].card_id in V0_78 if "energy" in e and e.get("energy") in state.cards else False:
            counts[f"attached_{state.cards[e['energy']].card_id}"] += 1
        if kind == "evolve" and e.get("to_card_id") in V0_78:
            counts[f"evolve_{e['to_card_id']}"] += 1
        if kind == "damage":
            labels = [label for label, _ in e.get("steps", ())]
            counts["darkness_bonus"] += sum(1 for label in labels if label == "5 悪エネルギー")
            counts["metal_attacker"] += sum(1 for label in labels if label == "5 鋼エネルギー")
            counts["metal_defender"] += sum(1 for label in labels if label == "7 鋼エネルギー")
        if kind == "darkness_energy_damage":
            counts["darkness_damage"] += 1
            counts["darkness_damage_reduced"] += 1 if e.get("energy_reduction") else 0
            counts["nonattack_zeroed"] += 1 if e.get("energy_reduction") and e["amount"] == 0 else 0
        if kind == "darkness_energy_counters":
            counts["darkness_counters"] += 1
        if kind in ("poison_damage", "power_damage", "counterattack", "trainer_damage", "energy_damage", "stadium_damage", "sinkhole_damage",
                    "knock_out_power_damage") and (e.get("energy_reduction") or any(m[0] in state.cards and state.cards[m[0]].card_id == "NIP1X-010"
                                                                                      for m in e.get("received_modifiers", ()))):
            counts["metal_nonattack"] += 1
            counts["nonattack_zeroed"] += 1 if e.get("amount") == 0 else 0
        effect = str(e.get("effect", ""))
        if effect.split("#")[0] not in V0_78:
            continue
        if kind == "persistent_effect_added":
            counts[f"effect_{e['persistent_effect']}"] += 1
        elif kind == "coin_flip" and e.get("source") == "attack":
            counts[f"coin_{effect}_{e['result']}"] += 1
        elif kind == "attack_failed":
            counts["failed"] += 1
        elif kind == "discard_attached_trainer" and e.get("reason") == "attack":
            counts["plunder_trainers"] += 1
    return counts


def v077_uses(state):
    """v0.77: ログから数えた v0.77 のカードの動き（ない局では空）。``attack_<id>#<位置>``（宣言。まねたワザは ``copied_<id>#<位置>``）・``coin_<id>#<位置>_<面>``・``effect_<種類>``
    （v0.77 のワザが与えた持続する効果）・``status_<種類>``（v0.77 のワザで付けた特殊状態）・``failed``・``self_damage``・``bench_damage``（じしんの自分の控え）・``switch``
    （りゅうのたつまき）・``drain``（メガドレイン）・``attach_from_hand``（せいちょう）・``evolve_<id>``（v0.77 のカードへの進化）・``trainer_<id>``（使ったトレーナー）・
    ``trainer_coin_<id>_<面>``・``scoop_cards``（スーパーポケモン回収で手札にもどしたカード）・``teleporter_draw``（マサキの転送装置で引いた枚数）。"""
    counts = Counter()
    current = None
    trainer = None
    for e in state.log:
        kind = e["kind"]
        if kind == "turn_start":
            trainer = None  # 番の最初に引くカードを、マサキの転送装置で引いた枚数に数えない
            continue
        if kind == "attack":
            current = f"{state.cards[e['pokemon']].card_id}#{e['attack_index']}" if "card_id" not in e else f"{e['card_id']}#{e['attack_index']}"
            if current.split("#")[0] in V0_77:
                counts[f"attack_{current}"] += 1
            trainer = None
            continue
        if kind == "play_trainer":
            trainer = state.cards[e["card"]].card_id if e.get("card") in state.cards else None
            if trainer in V0_77:
                counts[f"trainer_{trainer}"] += 1
            continue
        if kind == "evolve" and e.get("to_card_id") in V0_77:
            counts[f"evolve_{e['to_card_id']}"] += 1
        if kind == "copy_attack" and str(e.get("copied", "")).split("#")[0] in V0_77:
            counts[f"copied_{e['copied']}"] += 1
        if trainer in V0_77_TRAINERS:
            if kind == "coin_flip" and e.get("source") == "trainer":
                counts[f"trainer_coin_{trainer}_{e['result']}"] += 1
            elif kind == "return_in_play_to_hand":
                counts["scoop_cards"] += len(e.get("cards") or ())
            elif kind == "draw":
                counts["teleporter_draw"] += len(e.get("cards") or ()) if isinstance(e.get("cards"), (list, tuple)) else e.get("count", 0)
        effect = str(e.get("effect", ""))
        if effect.split("#")[0] not in V0_77:
            continue
        if kind == "persistent_effect_added":
            counts[f"effect_{e['persistent_effect']}"] += 1
        elif kind == "coin_flip" and e.get("source") == "attack":
            counts[f"coin_{effect}_{e['result']}"] += 1
        elif kind == "special_condition":
            counts[f"status_{e.get('condition')}"] += 1
        elif kind == "attack_failed":
            counts["failed"] += 1
        elif kind == "damage" and e.get("target") == "self":
            counts["self_damage"] += 1
        elif kind == "damage" and e.get("target") == "self_bench":
            counts["bench_damage"] += 1
        elif kind == "switch":
            counts["switch"] += 1
        elif kind == "drain_heal":
            counts["drain"] += 1
        elif kind == "attach_energy_from_hand":
            counts["attach_from_hand"] += 1
    return dict(counts)


def v075_uses(state):
    """v0.75: ログから数えた v0.75 のカードのワザの動き（ない局では空）。``attack_<id>#<位置>``（宣言。まねたワザは ``copied_<id>#<位置>``）・``reveal``（くらげのむれで見せた枚数）・
    ``recover``（おにびあつめで手札に加えた枚数）・``deck_attach``（山札からつけた枚数）・``deck_evaded``・``discard_attach``（エネルギーきゅうしゅう）・``doubled``（2 倍にした
    ダメージ）・``suppressed``（ポケモンタワーで消えたおにびあつめ）・``switch``（しらせる）・``bench``（山札からベンチに出した）・``alert_draw``。"""
    counts = Counter()
    current = None
    for e in state.log:
        kind = e["kind"]
        if kind == "attack":
            current = f"{state.cards[e['pokemon']].card_id}#{e['attack_index']}" if "card_id" not in e else f"{e['card_id']}#{e['attack_index']}"
            if current.split("#")[0] in V0_75:
                counts[f"attack_{current}"] += 1
            continue
        if kind == "copy_attack" and str(e.get("copied", "")).split("#")[0] in V0_75:
            counts[f"copied_{e['copied']}"] += 1
        effect = str(e.get("effect", ""))
        if effect.split("#")[0] not in V0_75:
            if kind == "damage" and e.get("damage_multiplied") and any(m[0] == 8 for m in e["damage_multiplied"]):
                counts["doubled"] += 1
            continue
        if kind == "reveal_from_deck":
            counts["reveal"] += 1
        elif kind == "recover_energy":
            counts["recover"] += len(e["cards"])
        elif kind == "attach_energy_from_deck":
            counts["deck_attach"] += 1
        elif kind == "deck_energy_evaded":
            counts["deck_evaded"] += 1
        elif kind == "attach_energy_from_discard":
            counts["discard_attach"] += len(e["cards"])
        elif kind == "discard_to_hand_suppressed":
            counts["suppressed"] += 1
        elif kind == "switch":
            counts["switch"] += 1
        elif kind == "bench_from_deck":
            counts["bench"] += 1
        elif kind in ("attach_energy_from_deck_none", "reveal_from_deck_none", "reveal_from_deck_declined", "bench_from_deck_declined", "persistent_effect_added"):
            counts[kind] += 1
    return dict(counts)


def v074_uses(state):
    """v0.74: ログから数えた v0.74 のスタジアムの動き（ない局では空）。``placed_<id>``・``used_<id>``・``coin_<id>_<heads|tails>``・``lucky_draw``（引いた枚数）・
    ``energy_stadium_retrieve``・``ninja_gym_bench``・``suppressed_<effect|power|trainer_card>``（ポケモンタワーで消えた効果）・``tower_left``（ポケモンタワーが入れかわった）。"""
    counts = Counter()
    card = {uid: c.card_id for uid, c in state.cards.items()}
    lucky_due = False
    for e in state.log:
        kind = e["kind"]
        if kind == "stadium_placed" and card.get(e["card"]) in V0_74:
            counts[f"placed_{card[e['card']]}"] += 1
        elif kind == "stadium_discarded" and card.get(e["card"]) == V0_74_TOWER:
            counts["tower_left"] += 1
        elif kind == "stadium_used" and card.get(e["card"]) in V0_74:
            counts[f"used_{card[e['card']]}"] += 1
        elif kind == "coin_flip" and e.get("source") == "stadium" and e.get("effect") in V0_74:
            counts[f"coin_{e['effect']}_{e['result']}"] += 1
            lucky_due = e["result"] == "heads" and e["effect"] not in (V0_74_NINJA, V0_74_ENERGY)
            continue
        elif kind == "draw" and lucky_due:
            counts["lucky_draw"] += len(e["cards"])
        elif kind == "stadium_retrieve_energy":
            counts["energy_stadium_retrieve"] += 1
        elif kind == "stadium_bench_from_deck":
            counts["ninja_gym_bench"] += 1
        elif kind == "discard_to_hand_suppressed":
            source = next(k for k in ("effect", "power", "trainer_card") if k in e)
            counts[f"suppressed_{source}"] += 1
        lucky_due = False
    return dict(counts)


def v073_uses(state):
    """v0.73: ログから数えた 18 枚の動き（ない局では空）。``trainer_<id>``（使った）・``bench_from_discard``（元気のかたまり）・``milled``・``milled_fire``（熱血!）・
    ``master_ball_take``・``master_ball_none``・``fossil_from_deck``・``fossil_from_discard``・``moon_stone``・``retriever_top``・``scoop_up_<zone>``・``teleporter_draw``・
    ``retrieve_energy``（超エネルギー回収の枚数）・``computer_error_draw_<user|opponent>``・``computer_error_turn_end``・``taken_then_<処理>``（手に入れたカードのそのあとの使い道）。"""
    counts = Counter()
    ids = set(V0_73)
    card = {uid: c.card_id for uid, c in state.cards.items()}
    trainer = user = None
    taken = {}
    for e in state.log:
        kind = e["kind"]
        if kind == "play_trainer":
            trainer, user = card.get(e.get("card")), e.get("player")
            if trainer in ids:
                counts[f"trainer_{trainer}"] += 1
        elif kind == "discard_trainer" and card.get(e.get("card")) == trainer:
            trainer = None
        if kind == "trainer_turn_end" and card.get(e.get("trainer_card")) in ids:
            counts["computer_error_turn_end"] += 1  # 使い終えて（トラッシュして）から番を終える
            continue
        if trainer not in ids:
            if kind in ("play_basic_to_bench", "evolve", "attach_energy", "play_trainer"):
                uid = e.get("card") if kind != "attach_energy" else e.get("energy")
                if uid in taken:
                    counts[f"taken_then_{kind}"] += 1
                    taken.pop(uid)
            continue
        if kind == "bench_from_discard":
            counts["bench_from_discard"] += 1
        elif kind == "deck_top_to_discard":
            counts["milled"] += len(e["cards"])
        elif kind == "milled_to_hand":
            counts["milled_fire"] += len(e["cards"])
            taken.update({uid: kind for uid in e["cards"]})
        elif kind == "reveal_from_deck":
            name = {"ES1-035": "fossil_from_deck", "ES1-036": "moon_stone"}.get(trainer, "master_ball_take")
            counts[name] += 1
            taken[e["card"]] = kind
        elif kind == "retrieve_trainer":
            counts["fossil_from_discard"] += 1
        elif kind == "trainer_take_none":
            counts[f"take_none_{trainer}"] += 1
        elif kind == "put_discard_on_deck_top":
            counts["retriever_top"] += 1
        elif kind == "return_in_play_to_hand":
            counts[f"scoop_up_{e.get('zone')}"] += 1
        elif kind == "draw":
            label = "teleporter_draw" if trainer in ("IP1-020", "IP2-021") else f"computer_error_draw_{'user' if e['player'] == user else 'opponent'}"
            counts[label] += e.get("count", len(e.get("cards", ())))
        elif kind == "retrieve_energy":
            counts["retrieve_energy"] += len(e["cards"])
    return dict(counts)


def v069_uses(state, ids=None):
    """v0.69: ログから数えた、写しの組 pool_v0_69 のカード（新しい id。v0.71: ``ids`` を渡せば、そのカード）の動き（ない局では空）。``in_deck``（デッキの枚数）・``attack_<id>_<位置>``・``power_<id>_<位置>``・
    ``trainer_<id>``・``attach_<id>``（手札からつけた）・``evolve_<下の id>_to_<上の id>``（進化の重なりの新しい id をふくむもの）・``bench_<id>``（ベンチに出した）。"""
    counts = Counter()
    new = set(V0_69 if ids is None else ids)
    card = {uid: c.card_id for uid, c in state.cards.items()}
    counts["in_deck"] = sum(1 for cid in card.values() if cid in new)
    for e in state.log:
        kind = e["kind"]
        if kind == "attack":
            cid = e.get("card_id") or card.get(e.get("pokemon"))
            if cid in new:
                counts[f"attack_{cid}_{e.get('attack_index')}"] += 1
        elif kind == "pokemon_power" and card.get(e.get("pokemon")) in new:
            counts[f"power_{card[e['pokemon']]}_{e.get('power_index')}"] += 1
        elif kind == "play_trainer" and card.get(e.get("card")) in new:
            counts[f"trainer_{card[e['card']]}"] += 1
        elif kind == "attach_energy" and card.get(e.get("energy")) in new:
            counts[f"attach_{card[e['energy']]}"] += 1
        elif kind == "evolve" and (e.get("from_card_id") in new or e.get("to_card_id") in new):
            counts[f"evolve_{e.get('from_card_id')}_to_{e.get('to_card_id')}"] += 1
        elif kind == "play_to_bench" and card.get(e.get("card")) in new:
            counts[f"bench_{card[e['card']]}"] += 1
        elif kind in ("bench_guard", "flee", "flee_declined", "esp_redo", "esp_redo_declined", "duel_janken"):
            counts[kind] += 1
    return dict(counts)


def v071_uses(state):
    """v0.71: ログから数えた、写しの組 pool_v0_71 のカード（再録のカード）の動き（ない局では空）。``v069_uses`` の数え方に加えて、``revive_bench``（元気のかけら GD1-017 で
    ベンチに出した）・``revive_counters``（そのあとのせたダメージカウンター）・``energy_search_reveal``（エネルギー転送の再録の版で見せて手札に加えた）・
    ``energy_search_none``（選ばなかった・選べるカードがなかった）・``fire_spin_discard``（ほのおのうず（PR1-030）でトラッシュしたエネルギーカード）・
    ``fire_spin_lacking``（足りずにダメージが 0）・``fire_spin_damage``（そのワザのダメージ）。"""
    counts = Counter(v069_uses(state, V0_71))
    card = {uid: c.card_id for uid, c in state.cards.items()}
    trainer = None
    current = attacker = None
    for e in state.log:
        kind = e["kind"]
        if kind == "play_trainer":
            trainer = card.get(e.get("card"))
        elif kind == "discard_trainer":
            trainer = None
        if kind == "attack":
            current = e.get("card_id") or card.get(e.get("pokemon"))
            attacker = e.get("player")
        elif kind == "turn_end":
            current = None
        if kind == "bench_from_discard" and e.get("trainer") == "GD1-017":
            counts["revive_bench"] += 1
        elif kind == "trainer_place_damage_counters" and e.get("trainer") == "GD1-017":
            counts["revive_counters"] += e["counters"]
        elif kind == "reveal_from_deck" and trainer in ("GD4-015", "QSG-048"):
            counts["energy_search_reveal"] += 1
        elif kind == "trainer_take_none" and trainer in ("GD4-015", "QSG-048"):
            counts["energy_search_none"] += 1
        elif kind == "discard_energy" and current == "PR1-030":
            counts["fire_spin_discard"] += 1
        elif kind == "discard_energy_failed" and current == "PR1-030":
            counts["fire_spin_lacking"] += 1
        elif kind == "damage" and current == "PR1-030" and e.get("player") != attacker:
            counts["fire_spin_damage"] += 1
    return dict(counts)


def v068_uses(state):
    """v0.68: ログから数えた 3 枚の動き（ない局では空）。``attack_<カード id>_<位置>``（ワザの宣言）・``fetch_draw``（こどものおつかいのあとの ``draw``）・
    ``drain_heads``・``drain_tails``・``drain_discard``（だつりょくえきでトラッシュしたカード）・``drain_decision``（そのまえの決定。ログ ``energy_drain_discard`` の数と同じ）・
    ``doduo_retreat_cost_<数>``（イマクニ？のドードーの「にげる」でトラッシュしたカードの数）。"""
    counts = Counter()
    card = {uid: c.card_id for uid, c in state.cards.items()}
    last_attack = None
    for e in state.log:
        kind = e["kind"]
        if kind == "attack":
            cid = card.get(e.get("pokemon")) if e.get("card_id") is None else e["card_id"]
            last_attack = (cid, e.get("attack_index"))
            if cid in V0_68:
                counts[f"attack_{cid}_{e.get('attack_index')}"] += 1
        elif kind == "draw" and last_attack == (KANGASKHAN, 0) and e.get("player") is not None:
            counts["fetch_draw"] += 1
            last_attack = None
        elif kind == "energy_drain_check":
            counts["drain_heads" if e.get("result") == "heads" else "drain_tails"] += 1
        elif kind == "energy_drain_discard":
            counts["drain_discard"] += 1
        elif kind == "retreat" and card.get(e.get("old_active")) == IMAKUNI_DODUO:
            counts[f"doduo_retreat_cost_{len(e.get('discarded') or ())}"] += 1
        elif kind == "turn_start":
            last_attack = None
    return dict(counts)


def v067_uses(state):
    """v0.67: ログから数えたマチスの秘策の動き（ない局では空）。``played``・``placed``・``declined``・``none``・``revealed_<理由>``・``revealed_basic``・``discarded``・
    ``discarded_with_energy``（ついていたエネルギーカードごと）・``target_lost``（効果で指定した対象がいなくなった）・``promoted_face_down``（うらのままバトル場に出た）。"""
    counts = Counter()
    card = {uid: c.card_id for uid, c in state.cards.items()}
    face_down = set()
    for e in state.log:
        kind = e["kind"]
        if kind == "play_trainer" and card.get(e.get("card")) == LT_SURGES_SECRET_PLAN:
            counts["played"] += 1
        elif kind == "secret_plan_placed":
            counts["placed"] += 1
            face_down.add(e["pokemon_id"])
        elif kind == "secret_plan_declined":
            counts["declined"] += 1
        elif kind == "secret_plan_none":
            counts[f"none_{e.get('reason')}"] += 1
        elif kind == "secret_plan_revealed":
            counts[f"revealed_{e.get('cause')}"] += 1
            face_down.discard(e["pokemon_id"])
        elif kind == "secret_plan_discarded":
            counts["discarded"] += 1
            if e.get("energy"):
                counts["discarded_with_energy"] += 1
        elif kind == "secret_plan_target_lost":
            counts["target_lost"] += 1
        elif kind in ("promote_active", "promote") and e.get("pokemon_id") in face_down:
            counts["promoted_face_down"] += 1
    revealed = sum(v for k, v in counts.items() if k.startswith("revealed_"))
    counts["revealed_basic"] = revealed - counts["discarded"]
    return dict(counts)


def v066_uses(state):
    """v0.66: ログから数えた v0.66 の 3 枚の動き（どれもない局では空）。

    - ``charity_played``・``charity_reduced``・``charity_reduced_to_zero``・``charity_returned``・``charity_discarded``: お上品攻撃（使った・へらした・最終ダメージが 0 に
      なった・相手の番の終わりに手札にもどった・きぜつしてトラッシュした）
    - ``esp_played``・``esp_redo``・``esp_redo_declined``・``esp_redo_changed``・``esp_discarded``: ナツメのESP（やり直した・やり直さなかった・やり直して「おもて」の数が
      変わった・番の終わりにトラッシュした）
    - ``duel_played``・``janken``・``janken_tie``・``duel_won_by_user``・``duel_won_by_opponent``・``duel_draw_<枚数>``: カスミの勝負
    """
    counts = Counter()
    card = {uid: c.card_id for uid, c in state.cards.items()}
    for e in state.log:
        kind = e["kind"]
        if kind == "play_trainer":
            label = {CHARITY: "charity", SABRINAS_ESP: "esp", MISTYS_DUEL: "duel"}.get(card.get(e.get("card")))
            if label:
                counts[f"{label}_played"] += 1
        elif kind == "damage" and e.get("damage_reduced"):
            counts["charity_reduced"] += 1
            if e.get("amount") == 0:
                counts["charity_reduced_to_zero"] += 1
        elif kind == "return_attached_trainer" and card.get(e.get("card")) == CHARITY:
            counts["charity_returned"] += 1
        elif kind in ("discard_attached_trainer", "knock_out"):
            for uid in (e.get("discarded_trainers", ()) if kind == "knock_out" else (e.get("card"),)):
                if card.get(uid) == CHARITY:
                    counts["charity_discarded"] += 1
                elif card.get(uid) == SABRINAS_ESP:
                    counts["esp_discarded"] += 1
        elif kind == "esp_redo":
            counts["esp_redo"] += 1
            if e.get("original", ()).count("heads") != e.get("redone", ()).count("heads"):
                counts["esp_redo_changed"] += 1
        elif kind == "esp_redo_declined":
            counts["esp_redo_declined"] += 1
        elif kind == "duel_janken":
            counts["janken"] += 1
            if e.get("winner") is None:
                counts["janken_tie"] += 1
            else:
                counts["duel_won_by_user" if e["winner"] == e["player"] else "duel_won_by_opponent"] += 1
    return counts


def v065_uses(state):
    """v0.65: ログから数えた v0.65 の 3 枚の動き（どれもない局では空）。

    - ``ninja_trick``・``ninja_trick_declined``・``trick_discarded_<理由>``: 変わり身の術（入れ替えた・使わなかった・トラッシュした理由）
    - ``flee``・``flee_declined``・``flee_effect_skipped``: ［にげこむ］（入れ替えた・使わなかった・入れ替えたので受けなかった効果）
    - ``bench_guard``・``bench_guard_knock_out``: ［ベンチガード］（かわりに受けた・そのダメージで HP 以上になった）
    - ``jellyfish_poison``・``lariat``: クラゲどく・ラリアット
    """
    counts = Counter()
    log = state.log
    names = {(MISTYS_TENTACRUEL, "クラゲどく"): "jellyfish_poison", (BROCKS_RHYDON, "ラリアット"): "lariat"}
    for e in log:
        kind = e["kind"]
        if kind in ("ninja_trick", "ninja_trick_declined", "flee", "flee_declined", "flee_effect_skipped"):
            counts[kind] += 1
        elif kind == "discard_attached_trainer" and state.cards[e["card"]].card_id == KOGAS_NINJA_TRICK:
            counts[f"trick_discarded_{e.get('reason')}"] += 1
        elif kind == "bench_guard":
            counts["bench_guard"] += 1
            if e.get("knocked_out"):
                counts["bench_guard_knock_out"] += 1
        elif kind == "attack":
            label = names.get((state.cards[e.get("card", e["pokemon"])].card_id, e["attack"]))
            if label:
                counts[label] += 1
    return {k: v for k, v in counts.items() if v}


def _v061_trainer(state, tried, counts):
    """v0.61: バトル場は穴だらけ!を、受け付けるなら番の番号が 2 の倍数の番に使う（1 番に 1 回）。止まる場面（TD1 など）は ``v061_digger_rejected_<コード>``。"""
    player = state.current_player
    p = state.players[player]
    if "trainer_locked" in tried or ("v061_digger", state.turn_number) in tried or state.turn_number % 2:
        return None
    uid = next((u for u in p.hand if state.cards[u].card_id == DIGGER), None)
    if uid is None:
        return None
    tried.add(("v061_digger", state.turn_number))
    command = PlayTrainer(player, uid)
    try:
        apply_command(state, command)
    except (IllegalActionError, UnsupportedError) as error:
        counts[f"v061_digger_rejected_{error.code}"] += 1
        return None
    counts["v061_digger_played"] += 1
    return command


def _v061_retreat(state, tried, counts):
    """v0.61: 相手の場にわるいダグトリオがいて、控えがいれば、3 番に 1 回「にげる」を試す（［おとしあな］の場面を起こす。にげるエネルギーはついている前から）。
    拒否は ``v061_retreat_rejected_<コード>`` に数え、別の操作を続ける。"""
    player = state.current_player
    p = state.players[player]
    active = p.active
    if active is None or not p.bench or state.turn_number % 3 or ("v061_retreat", state.turn_number) in tried or "retreat" in tried:
        return None
    if not any(state.cards[pk.card].card_id == DARK_DUGTRIO for pk in state.players[1 - player].in_play()):
        return None
    tried.add(("v061_retreat", state.turn_number))
    try:
        cost = retreat_cost(state, player)
    except UnsupportedError as error:
        counts[f"v061_retreat_rejected_{error.code}"] += 1
        return None
    paid = []
    for uid in active.energy:
        if energy_unit_count(state, paid, active) >= cost.minimum:
            break
        paid.append(uid)
    command = Retreat(player, tuple(paid), p.bench[-1].card)
    try:
        apply_command(state, command)
    except (IllegalActionError, UnsupportedError) as error:
        counts[f"v061_retreat_rejected_{error.code}"] += 1
        return None
    counts["v061_retreat"] += 1
    return command


def v061_uses(state):
    """v0.61: ログから数えた v0.61 の 4 枚の動き（どれもない局では空）。

    - ``beam_declined``・``beam_declared``・``beam_heads``・``beam_tails``: ［ファイナルビーム］。``beam_ko``: そのダメージで HP 以上。``beam_energy_<数>``: 数えた「水」エネルギー
    - ``ice_beam_paralysis``: れいとうビームでマヒ
    - ``sinkhole_checks``・``sinkhole_damage``・``sinkhole_ko``: ［おとしあな］のコイン・20 ダメージ・きぜつ
    - ``knock_down``・``knock_down_tails``: つきおとすのコイン（相手が投げる）・「うら」
    - ``scram_after_<きっかけ>``: ［ずらかる］で山札にもどった（直前のイベントの種類）
    - ``mega_thrash``・``mega_thrash_stadium``・``mega_thrash_no_stadium``: おおあばれ・スタジアムのトラッシュ
    - ``digger``・``digger_coins_<枚数>``・``digger_loser_user``・``digger_loser_opponent``・``digger_ko``: バトル場は穴だらけ!
    """
    counts = Counter()
    log = state.log
    for i, e in enumerate(log):
        kind = e["kind"]
        if kind == "knock_out_power_declined":
            counts["beam_declined"] += 1
        elif kind == "knock_out_power_declared":
            counts["beam_declared"] += 1
        elif kind == "knock_out_power_failed":
            counts["beam_tails"] += 1
        elif kind == "knock_out_power_damage":
            counts["beam_heads"] += 1
            counts[f"beam_energy_{e['energy']}"] += 1
            if e["knocked_out"]:
                counts["beam_ko"] += 1
        elif kind == "special_condition" and e.get("condition") == "paralysis" and str(e.get("effect", "")).startswith(DARK_GYARADOS):
            counts["ice_beam_paralysis"] += 1
        elif kind == "sinkhole_check":
            counts["sinkhole_checks"] += 1
        elif kind == "sinkhole_damage":
            counts["sinkhole_damage"] += 1
            if e["knocked_out"]:
                counts["sinkhole_ko"] += 1
        elif kind == "attack" and e.get("attack") == "つきおとす":
            counts["knock_down"] += 1
            coin = next((x for x in log[i + 1:i + 6] if x["kind"] == "coin_flip"), None)
            if coin is not None and coin["result"] == "tails":
                counts["knock_down_tails"] += 1
        elif kind == "scram":
            before = log[i - 1]["kind"] if i else "none"
            counts[f"scram_after_{before}"] += 1
        elif kind == "attack" and e.get("attack") == "おおあばれ":
            counts["mega_thrash"] += 1
        elif kind == "stadium_discarded" and e.get("reason") == "attack" and str(e.get("effect", "")).startswith(BROCKS_PRIMEAPE):
            counts["mega_thrash_stadium"] += 1
        elif kind == "stadium_discard_none" and str(e.get("effect", "")).startswith(BROCKS_PRIMEAPE):
            counts["mega_thrash_no_stadium"] += 1
        elif kind == "digger_result":
            counts["digger"] += 1
            counts[f"digger_coins_{e['coins']}"] += 1
            counts["digger_loser_user" if e["loser"] == e["player"] else "digger_loser_opponent"] += 1
        elif kind == "knock_out" and e.get("timing") == "trainer" and any(
                x["kind"] == "trainer_damage" and x["pokemon"] == e["pokemon"] for x in log[max(0, i - 8):i]):
            counts["digger_ko"] += 1
    return {k: v for k, v in counts.items() if v}


def _v063_decision(state, counts):
    """v0.63 の決定への答え（元の手順より先に答える。相手の決定にも答える）。

    - 挑戦状のたずねる決定: 受ける・受けないを、番の番号とカードの番号で回す（``…_accept``・``…_refuse``）
    - 挑戦状のうらにしてベンチに出すたねポケモン: 選べるものがあれば 1 匹 → 出せるだけ → 1 匹 の順に回す（0 匹は HC5 なので選ばない）。選ぶと止める選択（GG1）は除く
    - クイズのポケモン: 選べるものを順に、ワザ: 選べる位置を順に、答え: 正解・不正解を同じように回す（``…_answer_correct``・``…_wrong``）
    受け付けない答えは次の候補（``_v052_accepted``）。"""
    d = state.decision
    if d is None or d.resume != "trainer":
        return None
    use = d.context_value("use")
    if use is None or use[2] not in (CHALLENGE, BLAINES_QUIZ_3):
        return None
    # 回し方の番号は状態から決める（手順が同じ決定に何度か呼ばれても同じ答えにする）
    seen = state.turn_number // 2 + use[1]
    counts[f"v063_{d.kind}_seen"] += 1
    if d.kind == "accept_request":
        candidates = [(tuple(d.options), "accept"), ((), "refuse")]
        if seen % 2:
            candidates.reverse()
    elif d.kind == "challenge_bench":
        stopped = set(d.context_value("unresolved_choices", ()))
        free = [o for o in d.options if o not in stopped]
        size = [1, d.max_choices, 1][seen % 3]
        candidates = [(tuple(free[:size]), f"pick_{min(size, len(free))}"), (tuple(free[:1]), "pick_1")]
    elif d.kind == "quiz_card":
        candidates = [((d.options[(seen + i) % len(d.options)],), "card") for i in range(len(d.options))]
    elif d.kind == "quiz_attack":
        candidates = [((d.options[seen % len(d.options)],), f"attack_{seen % len(d.options)}")]
    elif d.kind == "quiz_answer":
        names = d.context_value("names")
        right = names.index(state.card_def(d.context_value("quiz_card")).name_ja)
        wrong = (right + 1) % len(names)
        order = [(right, "correct"), (wrong, "wrong")] if seen % 2 == 0 else [(wrong, "wrong"), (right, "correct")]
        candidates = [((index,), f"answer_{label}") for index, label in order]
    else:
        return None
    for choices, label in candidates:
        if d.min_choices <= len(choices) <= d.max_choices and _v052_accepted(state, ResolveDecision(d.player, d.id, choices)):
            counts[f"v063_{use[2]}_{d.kind}_{label}"] += 1
            return ResolveDecision(d.player, d.id, choices)
    counts[f"v063_{use[2]}_no_accepted_answer"] += 1
    return None


def _v063_trainer(state, tried, counts):
    """v0.63: 4 枚を、受け付けるなら使う（種類ごとに 1 番に 1 回まで）。ロケット団参上! はサイドにうらのカードが残っているときだけ。使う前に止まる・拒否される場面
    （QZ1・トレーナーの使用の禁止など）は使わず ``v063_<カード>_not_playable_<コード>`` に数える。"""
    player = state.current_player
    if "trainer_locked" in tried:
        return None
    p = state.players[player]
    for card_id in V0_63_TRAINERS:
        if (f"v063_{card_id}", state.turn_number) in tried:
            continue
        if card_id == HERE_COMES_TEAM_ROCKET and all(u in state.face_up_prizes for q in state.players for u in q.prizes):
            continue
        uid = next((u for u in p.hand if state.cards[u].card_id == card_id), None)
        if uid is None:
            continue
        tried.add((f"v063_{card_id}", state.turn_number))
        command = PlayTrainer(player, uid)
        real = _V052_REAL.get("state")
        try:
            apply_command(real if real is not None and real.turn_number == state.turn_number and real.decision == state.decision else state, command)
        except (IllegalActionError, UnsupportedError) as error:
            counts[f"v063_{card_id}_not_playable_{error.code}"] += 1
            continue
        counts[f"v063_play_{card_id}"] += 1
        return command
    return None


def v063_uses(state):
    """v0.63: ログから数えた v0.63 の 4 枚の動き（どれもない局では空）。

    - ``prizes_revealed``・``face_up_prize_taken``・``face_up_prize_swapped``: ロケット団参上! とそのあと、おもてのサイドを取った（``take_prize``・``trainer_take_prize``）・
      入れかえた（``swap_prize_with_hand``・``swap_prize_with_deck_top``）
    - ``tickle_heads``・``tickle_cards_<枚数>``・``tickle_tails_turn_end``・``set_aside_returned_<理由>``: くすぐりマシーン（置いた枚数・「うら」で番が終わった・もどった理由）
    - ``challenge_accepted``・``challenge_refused``・``face_down_bench_<枚数>``・``face_down_revealed``・``challenge_skipped_<理由>``: 挑戦状
    - ``quiz_correct``・``quiz_wrong``・``quiz_stage_<段階>``: カツラのクイズ その3（置いたポケモンの段階）
    """
    counts = Counter()
    log = state.log
    for i, e in enumerate(log):
        kind = e["kind"]
        if kind == "prizes_revealed":
            counts["prizes_revealed"] += 1
        elif kind in ("take_prize", "trainer_take_prize") and e.get("face_up"):
            counts["face_up_prize_taken"] += 1
        elif kind == "swap_prize_with_hand" and e.get("face_up") or kind == "swap_prize_with_deck_top" and e.get("face_up_card") is not None:
            counts["face_up_prize_swapped"] += 1
        elif kind == "set_aside_hand":
            counts["tickle_heads"] += 1
            counts[f"tickle_cards_{e['count']}"] += 1
        elif kind == "trainer_turn_end" and state.cards[e["trainer_card"]].card_id == TICKLING_MACHINE:
            counts["tickle_tails_turn_end"] += 1
        elif kind == "set_aside_returned":
            counts[f"set_aside_returned_{e['reason']}"] += 1
        elif kind == "request_answered" and e.get("trainer_card") is not None and state.cards[e["trainer_card"]].card_id == CHALLENGE:
            counts["challenge_accepted" if e["accepted"] else "challenge_refused"] += 1
        elif kind == "face_down_bench":
            counts[f"face_down_bench_{len(e['cards'])}"] += 1
        elif kind == "face_down_revealed":
            counts["face_down_revealed"] += len(e["cards"])
        elif kind == "challenge_bench_skipped":
            counts[f"challenge_skipped_{e['reason']}"] += 1
        elif kind == "quiz_reveal":
            counts["quiz_correct" if e["correct"] else "quiz_wrong"] += 1
            counts[f"quiz_stage_{state.definitions[e['card_id']].stage}"] += 1
    return {k: v for k, v in counts.items() if v}


def v064_uses(state):
    """v0.64: ログから数えた v0.64 の 3 枚の動き（どれもない局では空）。

    - ``barrage``・``barrage_heads_<数>``（6 以上は ``barrage_heads_6plus``）・``barrage_zero``・``barrage_max_heads``: れんぞくいしなげ（実際に出た「おもて」の数・
      1 枚目が「うら」の 0 ダメージ・1 局のいちばん長い「おもて」の並び）
    - ``barrage_copied``: ほかのポケモンのワザ（ピジョンのオウムがえしなど）としてれんぞくいしなげを使った
    - ``harden``・``harden_zeroed``・``harden_passed``: かたくなる（効果を与えた・受けたダメージを 0 にした（ログ damage_zero_below）・40 以上でそのまま受けた）
    - ``rock_throw``・``avalanche``・``selfdestruct``・``selfdestruct_knock_outs``: いわおとし・いわころがり・じばく（じばくのあとのきぜつの数）
    """
    counts = Counter()
    log = state.log
    names = {(FOSSIL_GEODUDE, "れんぞくいしなげ"): "barrage", (FOSSIL_GRAVELER, "かたくなる"): "harden", (FOSSIL_GRAVELER, "いわおとし"): "rock_throw",
             (FOSSIL_GOLEM, "いわころがり"): "avalanche", (FOSSIL_GOLEM, "じばく"): "selfdestruct"}
    graveler = {uid for uid, c in state.cards.items() if c.card_id == FOSSIL_GRAVELER}
    for i, e in enumerate(log):
        kind = e["kind"]
        if kind == "copy_attack" and e.get("copied") == f"{FOSSIL_GEODUDE}#0":
            counts["barrage_copied"] += 1
        if kind == "damage":
            for _, source, _ in e.get("damage_zero_below", ()):
                if source in graveler:
                    counts["harden_zeroed" if e["amount"] == 0 else "harden_passed"] += 1
        if kind != "attack":
            continue
        card_id = e.get("card_id") or state.cards[e["pokemon"]].card_id
        name = names.get((card_id, e["attack"]))
        if name is None:
            continue
        counts[name] += 1
        window = []
        for x in log[i + 1:]:
            if x["kind"] in ("attack", "turn_end"):
                break
            window.append(x)
        if name == "barrage":
            heads = sum(1 for x in window if x["kind"] == "coin_flip" and x.get("until") == "tails" and x["result"] == "heads")
            if any(x["kind"] == "coin_flip" and x.get("until") == "tails" for x in window):
                counts[f"barrage_heads_{heads if heads < 6 else '6plus'}"] += 1
                counts["barrage_max_heads"] = max(counts["barrage_max_heads"], heads)
                if heads == 0:
                    counts["barrage_zero"] += 1
        if name == "selfdestruct":
            counts["selfdestruct_knock_outs"] += sum(1 for x in window if x["kind"] == "knock_out")
    return +counts



def _v062_attack(state, tried, counts):
    """v0.62: 前の番の履歴を読むワザを、使える番に優先して使う（どれもない局では何もしない）。

    - タケシのダグトリオ: 前の自分の番に「あながくれ」を使っていて、ドリルホールを払えれば、ドリルホール（``v062_earthdrill``）。そうでなく「あながくれ」を払えれば、
      2 回に 1 回は「あながくれ」（``v062_lie_low``。次の番のドリルホールのため）
    - ピジョン・オニスズメ: 前の相手の番に受けた記録（``history.received_on``）があり、オウムがえしを払えれば、オウムがえし（``v062_mirror_<カード>``）。止まる場面
      （MM1・MM2・OM1・OM2・未対応）は ``V031_STOPS`` で場から確かめ、別の操作を続ける
    この番に拒否されたワザ（``("attack_index", 位置)``）は選ばない。"""
    if "attack" in tried:
        return None
    player = state.current_player
    active = state.players[player].active
    if active is None or active.conditions.asleep or active.conditions.paralyzed or current_form(state, active).kind != "printed":
        return None
    card_id = state.cards[active.card].card_id
    attacks = state.card_def(active.card).attacks

    def payable(index):
        return ("attack_index", index) not in tried and attack_cost_payable(state, active, attacks[index])

    if card_id == BROCKS_DUGTRIO:
        if used_attack_last_turn(state, active, 0, "あながくれ") == "used" and payable(1):
            counts["v062_earthdrill"] += 1
            return UseAttack(player, 1)
        if payable(0) and counts["v062_lie_low_turns"] % 2 == 0:
            counts["v062_lie_low_turns"] += 1
            counts["v062_lie_low"] += 1
            return UseAttack(player, 0)
        counts["v062_lie_low_turns"] += 1
        return None
    if card_id in (PIDGEOTTO, SPEAROW) and received_on(active, state.turn_number - 1) is not None and payable(1):
        counts[f"v062_mirror_{card_id}"] += 1
        return UseAttack(player, 1)
    return None


def v062_uses(state):
    """v0.62: ログから数えた v0.62 の 6 枚の動き（どれもない局では空）。

    - ``lie_low``・``earthdrill``: あながくれ・ドリルホール（ドリルホールの直前の自分の番の宣言を確かめる）
    - ``repeat``・``repeat_<出したワザ>``・``repeat_none_<理由>``: ピジョンのオウムがえし（出したワザ・何もしなかった理由）
    - ``reflect``・``reflect_damage``・``reflect_paralysis``・``reflect_none_<理由>``: オニスズメのオウムがえし（与えたダメージ・マヒ・何もしなかった理由）
    - ``hurricane``・``hurricane_returned``・``hurricane_knocked_out``: ハリケーン（手札にもどした・きぜつで処理しなかった）
    - ``whirlwind``・``agility_barrier``・``drill_peck``・``wing_attack``・``peck``・``lickitung_paralysis``・``supersonic_confusion``: ほかのワザ
    """
    counts = Counter()
    log = state.log
    names = {(PIDGEOTTO, "ふきとばし"): "whirlwind", (FEAROW, "こうそくいどう"): "agility", (FEAROW, "ドリルくちばし"): "drill_peck",
             (PIDGEOT, "つばさでうつ"): "wing_attack", (SPEAROW, "つつく"): "peck", (LICKITUNG, "まきつくベロ"): "tongue_wrap",
             (LICKITUNG, "ちょうおんぱ"): "supersonic", (BROCKS_DUGTRIO, "あながくれ"): "lie_low", (BROCKS_DUGTRIO, "ドリルホール"): "earthdrill",
             (PIDGEOT, "ハリケーン"): "hurricane", (PIDGEOTTO, "オウムがえし"): "repeat", (SPEAROW, "オウムがえし"): "reflect"}
    for i, e in enumerate(log):
        kind = e["kind"]
        if kind == "attack":
            card_id = e.get("card_id") or state.cards[e["pokemon"]].card_id
            name = names.get((card_id, e["attack"]))
            if name is None:
                continue
            counts[name] += 1
            window = []
            for x in log[i + 1:]:
                if x["kind"] in ("attack", "turn_end"):
                    break
                window.append(x)
            kinds = [x["kind"] for x in window]
            if name == "hurricane":
                if "return_in_play_to_hand" in kinds:
                    counts["hurricane_returned"] += 1
                elif any(x["kind"] == "knock_out" for x in window):
                    counts["hurricane_knocked_out"] += 1
            elif name == "repeat":
                copy = next((x for x in window if x["kind"] == "copy_attack"), None)
                if copy is not None:
                    counts[f"repeat_{copy['copied_attack']}"] += 1
                none = next((x for x in window if x["kind"] == "mirror_move_none"), None)
                if none is not None:
                    counts[f"repeat_none_{none['reason']}"] += 1
            elif name == "reflect":
                got = next((x for x in window if x["kind"] == "reflect_received"), None)
                if got is not None:
                    counts["reflect_received"] += 1
                    counts["reflect_damage"] += bool(got["damage"])
                    counts["reflect_paralysis"] += "paralysis" in got["effects"]
                none = next((x for x in window if x["kind"] == "mirror_move_none"), None)
                if none is not None:
                    counts[f"reflect_none_{none['reason']}"] += 1
            elif name == "agility" and "persistent_effect_added" in kinds:
                counts["agility_barrier"] += 1
            elif name == "tongue_wrap" and any(x["kind"] == "special_condition" and x.get("condition") == "paralysis" for x in window):
                counts["tongue_wrap_paralysis"] += 1
            elif name == "supersonic" and any(x["kind"] == "special_condition" and x.get("condition") == "confusion" for x in window):
                counts["supersonic_confusion"] += 1
            elif name == "whirlwind" and "forced_switch" in kinds:
                counts["whirlwind_switch"] += 1
    return {k: v for k, v in counts.items() if v}


def v060_uses(state):
    """v0.60: ログから数えた v0.60 の 4 枚の動き（どれもない局では空）。

    - ``thunderstorm``: サンダーストーム。``thunderstorm_coins``・``thunderstorm_heads``: 控えのコインの枚数・「おもて」。``thunderstorm_attacks``: サンダーストームの宣言（控えがなければコインはない）。
      ``thunderstorm_bench_damage``・``thunderstorm_self_damage``: 控え・自分へのダメージ。``copied_thunderstorm``: 相手のワザとして使った
    - ``shadow_images``: かげぶんしんの効果を与えた。``guard_received``・``guard_dodged``: 相手のワザのダメージを受ける時のコイン。``guard_removed_<理由>``: 消えた理由
    - ``rebellion_passed``・``rebellion_failed``: ［はんこう］のコイン。``rebellion_confused``: こんらん状態ではたらいた。``rebellion_returned``: 山札にもどした
    - ``speed_star``: スピードスターのダメージ（相手の持っている効果を除いた）。``needle_ball_poison``: とげボールでどく
    """
    counts = Counter()
    for i, e in enumerate(state.log):
        kind = e["kind"]
        if kind == "attack" and e.get("attack") == "サンダーストーム":
            counts["thunderstorm_attacks"] += 1
        elif kind == "bench_coin_results":
            counts["thunderstorm"] += 1
            counts["thunderstorm_coins"] += len(e["results"])
            counts["thunderstorm_heads"] += e["results"].count("heads")
        elif kind == "copy_attack" and str(e.get("copied", "")).startswith(FOSSIL_ZAPDOS):
            counts["copied_thunderstorm"] += 1
        elif kind == "damage" and e.get("target") == "opponent_bench" and str(e.get("effect", "")).startswith(FOSSIL_ZAPDOS):
            counts["thunderstorm_bench_damage"] += 1
        elif kind == "damage" and e.get("target") == "self" and str(e.get("effect", "")).startswith(FOSSIL_ZAPDOS):
            counts["thunderstorm_self_damage"] += 1
        elif kind == "persistent_effect_added" and e.get("persistent_effect") == "tails_damage_guard":
            counts["shadow_images"] += 1
        elif kind == "damage_guard_check":
            counts["guard_received" if e["received"] else "guard_dodged"] += 1
        elif kind == "persistent_effect_removed" and e.get("persistent_effect") == "tails_damage_guard":
            counts[f"guard_removed_{e['reason']}"] += 1
        elif kind == "rebellion_check":
            counts["rebellion_failed" if e["failed"] else "rebellion_passed"] += 1
            if any(x["kind"] == "confusion_check" and x.get("pokemon_id") == e["pokemon_id"] for x in state.log[i:i + 6]):
                counts["rebellion_confused"] += 1
        elif kind == "return_in_play_to_deck" and e.get("power", "").startswith(MISTYS_GYARADOS):
            counts["rebellion_returned"] += 1
        elif kind == "damage" and e.get("ignore_defender_effects"):
            counts["speed_star"] += 1
        elif kind == "special_condition" and e.get("condition") == "poison" and str(e.get("effect", "")).startswith(BROCKS_SANDSLASH + "#1"):
            counts["needle_ball_poison"] += 1
    return {k: v for k, v in counts.items() if v}


def v059_uses(state):
    """v0.59: ログから数えた v0.59 の 6 枚の動き（どれもない局では空）。

    - ``buzzap``・``buzzap_<色>``: ［エネエネ］でエネルギーとしてついた（色ごと）。``converted_energy_paid``: そのカードがついたポケモンのワザ
    - ``shock_eye``・``shock_eye_bench``: ショックアイの効果を与えた（ベンチのポケモンに）。``crystal_beam``: クリスタルビームの効果を与えた
    - ``poison_vapor_bench``: どくのきりの控えへのダメージ。``goop_gas``: まきちらせ!ベトベトガスを使った。``blaine_double_attach``: カツラで 2 枚をいっしょにつけた
    - ``protection_attached``: タケシの保護をつけた。``attach_skipped``: ワザでつける効果がクリスタルビームで飛んだ
    """
    counts = Counter()
    converted = {}
    for e in state.log:
        kind = e["kind"]
        if kind == "energy_conversion":
            counts["buzzap"] += 1
            counts[f"buzzap_{e['energy_type']}"] += 1
            converted[e["card"]] = e["target"]
        elif kind == "persistent_effect_added" and e.get("persistent_effect") == "cannot_use_powers":
            counts["shock_eye"] += 1
        elif kind == "persistent_effect_added" and e.get("persistent_effect") == "cannot_attach_energy":
            counts["crystal_beam"] += 1
        elif kind == "damage" and e.get("target") == "opponent_bench" and str(e.get("effect", "")).startswith(DARK_ARBOK + "#1"):
            counts["poison_vapor_bench"] += 1
        elif kind == "play_trainer" and state.cards[e["card"]].card_id in V0_59_TRAINERS:
            counts[f"play_{state.cards[e['card']].card_id}"] += 1
        elif kind == "attach_energy" and "energy2" in e:
            counts["blaine_double_attach"] += 1
        elif kind == "attach_trainer" and state.cards[e["card"]].card_id == BROCKS_PROTECTION:
            counts["protection_attached"] += 1
        elif kind == "effect_skipped" and e.get("reason") == "attach_prevented":
            counts["attach_skipped"] += 1
        elif kind == "attack" and e["pokemon"] in converted.values():
            counts["converted_energy_paid"] += 1  # ［エネエネ］のカードがついたあとの、つけた先（そのときのいちばん上のカード）のワザ
    for e in state.log:
        if e["kind"] == "persistent_effect_added" and e.get("persistent_effect") == "cannot_use_powers":
            found = state.find_pokemon(e["pokemon_id"])
            if found is not None and found[1] is not state.players[found[0]].active:
                counts["shock_eye_bench"] += 1
    return dict(counts)


def _v044_power(state, tried, counts):
    """v0.44 の宣言する特殊能力を使う手順: キョウのコクーンの［うか］（この番にまだ使っておらず、ねむり・マヒ・こんらんでなく、その番の最初から場にいて、おたがいの最初の番
    でないとき。山札にキョウのスピアーがなくても 2 回までは使う（「おもて」で重ねられない場合を起こす））。拒否を起こさない。"""
    player = state.current_player
    p = state.players[player]
    if state.turn_number <= 2:
        return None
    for pokemon in p.in_play():
        if state.is_face_down(pokemon):
            continue  # v0.67
        if state.card_def(pokemon.card).id != KOGAS_KAKUNA:
            continue
        conditions = pokemon.conditions
        if conditions.asleep or conditions.paralyzed or conditions.confused or (pokemon.pokemon_id, 0) in state.power_uses_this_turn:
            continue
        if pokemon.current_form_turn >= state.turn_number:
            continue
        in_deck = any(state.card_def(u).id == KOGAS_BEEDRILL for u in p.deck)
        if not in_deck and counts["v044_power_metamorphosis_without_card"] >= 2:
            continue
        counts["v044_power_metamorphosis" + ("" if in_deck else "_without_card")] += 1
        return UsePokemonPower(player, pokemon.pokemon_id, 0)
    return None


def _v044_trainer(state, tried, counts):
    """v0.44 のトレーナー「サカキ」の手順: 今の番に場に出した・進化したサカキのポケモンがいて、手札にそのポケモンから進化するカードがあり、まだ許可がなければ、サカキを使う。
    許可のあるポケモン（``evolution_permission_turn``）がいて、手札にそのポケモンから進化するカードがあれば進化させる（同じ番に 2 回目の進化も）。拒否を起こさない
    （場にサカキのポケモンがいない（TR1）ときは使わない）。"""
    player = state.current_player
    p = state.players[player]
    if state.turn_number <= 2:
        return None
    for pokemon in p.in_play():
        if pokemon.evolution_permission_turn != state.turn_number:
            continue
        name = state.card_def(pokemon.card).name_ja
        card = next((u for u in p.hand if state.card_def(u).evolves_from == name), None)
        if card is not None:
            counts["v044_permitted_evolve_" + ("again" if pokemon.evolved_turn == state.turn_number else "played")] += 1
            return EvolvePokemon(player, card, pokemon.pokemon_id)
    giovanni = next((u for u in p.hand if state.card_def(u).id == GIOVANNI), None)
    if giovanni is None:
        return None
    for pokemon in p.in_play():
        if state.is_face_down(pokemon):
            continue  # v0.67
        name = state.card_def(pokemon.card).name_ja
        if not name.startswith("サカキの") or pokemon.current_form_turn < state.turn_number or pokemon.evolution_permission_turn == state.turn_number:
            continue
        if any(state.card_def(u).evolves_from == name for u in p.hand):
            counts["v044_play_giovanni"] += 1
            return PlayTrainer(player, giovanni)
    return None


def _v043_power(state, tried, counts):
    """v0.43 の宣言する特殊能力を使う手順（使えない特殊状態・この番に使ったもの・原典で決められない場合（PW3・HC10）は使わない。拒否を起こさない）:

    - くさいかふん（わるいクサイハナ）: この番にまだ使っておらず、相手の対戦ポケモンがこんらんでなければ。えんかくさいみん（ロケット団のスリープ）: この番にまだ使って
      おらず、どちらの対戦ポケモンもねむりでなければ（コインの「うら」なら自分の対戦ポケモンがその状態になる）
    - ほのおをもらう（ロケット団のヒトカゲ）: ほかの自分のポケモンに基本「炎」エネルギーカード（エナジーバーンで「炎」になったものでない）があれば、その 1 枚目
    - ようぶんきゅうしゅう（エリカのマダツボミ）: ほかの自分のポケモンに基本「草」エネルギーカードがあれば
    - エナジーチャージ（バトル場のマチスのレアコイル）: 控えに基本「雷」エネルギーカードがあれば（回数の制限はないが、この手順は 1 番に 1 回）
    - しんかのひかり（わるいハクリュー）: 山札に進化カードがあれば"""
    player = state.current_player
    p = state.players[player]

    def free(pokemon):
        conditions = pokemon.conditions
        return not (conditions.asleep or conditions.paralyzed or conditions.confused)

    def used(pokemon):
        return (pokemon.pokemon_id, 0) in state.power_uses_this_turn

    def energy_on(holders, energy_type):
        return [(holder, uid) for holder in holders for uid in holder.energy
                if state.card_def(uid).provides is energy_type and (holder.pokemon_id, uid) not in state.energy_burn]

    for pokemon in p.in_play():
        if state.is_face_down(pokemon):
            continue  # v0.67
        card_id = state.card_def(pokemon.card).id
        if card_id not in V0_43 or not free(pokemon):
            continue
        pid = pokemon.pokemon_id
        others = [q for q in p.in_play() if q is not pokemon]
        actives = (p.active, state.players[1 - player].active)
        if card_id == DARK_GLOOM and not used(pokemon) and not actives[1].conditions.confused:
            counts[f"v043_power_coin_condition_{card_id}"] += 1
            return UsePokemonPower(player, pid, 0)
        if card_id == ROCKET_DROWZEE and not used(pokemon) and not any(a.conditions.asleep for a in actives):
            # 両方の対戦ポケモンがねむりになるとポケモンチェックで止まる（UNRESOLVED_POKEMON_CHECK_SLEEP_COIN_ORDER）ので、どちらかがねむりなら使わない
            counts[f"v043_power_coin_condition_{card_id}"] += 1
            return UsePokemonPower(player, pid, 0)
        if card_id == ROCKET_CHARMANDER and not used(pokemon):
            found = energy_on(others, EnergyType.FIRE)
            if found:
                holder, uid = found[0]
                counts["v043_power_gather_fire"] += 1
                return UsePokemonPower(player, pid, 0, energy=uid, source=holder.pokemon_id)
        if card_id == ERIKAS_BELLSPROUT_40 and not used(pokemon) and energy_on(others, EnergyType.GRASS):
            counts["v043_power_soak_up"] += 1
            return UsePokemonPower(player, pid, 0)
        marker = ("v043_energy_charge", pid)
        if card_id == LT_SURGES_MAGNETON and pokemon is p.active and marker not in tried and energy_on(p.bench, EnergyType.LIGHTNING):
            tried.add(marker)
            counts["v043_power_energy_charge"] += 1
            return UsePokemonPower(player, pid, 0)
        if card_id == DARK_DRAGONAIR and not used(pokemon) and any(state.card_def(u).is_evolution_pokemon for u in p.deck):
            counts["v043_power_evolutionary_light"] += 1
            return UsePokemonPower(player, pid, 0)
    return None


def _v031_power(state, tried, counts):
    """v0.31 の宣言する特殊能力を使う手順: カツラのロコンの「しぜんになおる」（ダメージがあり、この番にまだ使っていない）・リザードンの「エナジーバーン」
    （炎でないエネルギーがついていて、その番にまだ使っていない）。使えない特殊状態のときは使わない（拒否を起こさない）。"""
    player = state.current_player
    p = state.players[player]
    for pokemon in p.in_play():
        if state.is_face_down(pokemon):
            continue  # v0.67
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

    def choose(state, *, janken_winner, cure, tried):
        if state.phase is Phase.DECISION:
            # v0.43: v0.43 のカードの決定（場に出たときの特殊能力の使う機会など）は、元の手順より先に答える（元の手順は、選ぶと止める選択しかない決定（使うことを選ぶと
            # PW3 で止まる使う機会）に答えられない）。v0.43 のカードのない局では何もしない
            early = (_v082_decision(state, counts)  # v0.82: エネルギーカードをトラッシュするワザの決定（v0.82 のポケモンのない局では何もしない）
                     or _v081_decision(state, counts)  # v0.81: どうぐ・ピントレンズのつけるポケモン・学習装置（v0.81 のカードのない局では何もしない）
                     or _v080_decision(state, counts)  # v0.80: 30 枚のトレーナー・ラジオとうの決定（相手の決定にも答える。v0.80 のカードのない局では何もしない）
                     or _v076_decision(state, counts)  # v0.76: ドわすれ・かなしばり（v0.76 のカードのない局では何もしない）
                     or _v075_decision(state, counts)  # v0.75: v0.75 のカードのワザの決定（v0.75 のカードのない局では何もしない）
                     or _v074_decision(state, counts)  # v0.74: エネルギースタジアム・キョウの忍者ジムの「おもて」のあとの 1 枚（v0.74 のスタジアムのない局では何もしない）
                     or _v073_decision(state, counts)  # v0.73: 18 枚のトレーナーの決定（相手の決定にも答える。v0.73 のカードのない局では何もしない）
                     or _v072_decision(state, counts)  # v0.72: きゅうけつ・デンキとばし・おつきみ（v0.72 のカードのない局では何もしない）
                     or _v067_decision(state, counts)  # v0.67: マチスの秘策でうらにして出すカード
                     or _v066_decision(state, counts)  # v0.66: お上品攻撃・ナツメのESP・カスミの勝負（相手の決定にも答える）
                     or _v065_decision(state, counts)  # v0.65: 変わり身の術・［にげこむ］・［ベンチガード］（ワザを受ける相手の決定）
                     or _v063_decision(state, counts)  # v0.63: 挑戦状・クイズの決定（相手の決定にも答える）
                     or _v043_decision(state, counts) or _v044_decision(state, counts)  # v0.44 の決定も元の手順より先に答える
                     or _v045_decision(state, counts) or _v046_decision(state, counts)  # v0.45・v0.46 の決定も
                     or _v047_decision(state, counts) or _v048_decision(state, counts)  # v0.47・v0.48
                     or _v049_decision(state, counts) or _v050_decision(state, counts)  # v0.49・v0.50
                     or _v051_decision(state, counts) or _v052_decision(state, counts)  # v0.51・v0.52
                     or _v053_decision(state, counts) or _v054_decision(state, counts)  # v0.53・v0.54
                     or _v055_decision(state, counts) or _v056_decision(state, counts)  # v0.55・v0.56
                     or _v057_decision(state, counts) or _v058_decision(state, counts)  # v0.57・v0.58
                     or _v059_decision(state, counts) or _v061_decision(state, counts)  # v0.59・v0.61
                     or _v069_decision(state, counts))  # v0.69: 新しい id のトレーナーの決定（ほかの手順が答えないときだけ。新しい id がなければ何もしない）
            if early is not None:
                return early
        reveal = _v067_reveal(state, tried, counts)  # v0.67: 自分のうらのカード（元の手順の前。元の手順はうらのカードの定義を読まない）
        if reveal is not None:
            return reveal
        command = base(state, janken_winner=janken_winner, cure=cure, tried=tried)
        if state.phase is Phase.MAIN and type(command).__name__ == "PlayBasicToBench" and state.turn_number % 2 == 0:
            # v0.67: マチスの秘策は、手順がたねポケモンをベンチに出す前にも使う（手札にたねポケモンが残り、うらにして出すカードにたねポケモンを選べる）
            plan = _v067_trainer(state, tried, counts)
            if plan is not None:
                return plan
        if state.phase is Phase.MAIN and type(command).__name__ == "PlayBasicToBench":
            # v0.56: マチス（手札のたねポケモンをバトル場に出す）は、手順がたねポケモンをベンチに出す前に使う（出したあとの手札にたねポケモンが残らず、LS1 ばかりになる）
            surge = _v056_trainer(state, tried, counts, only=(LT_SURGE_TRAINER,))
            if surge is not None:
                return surge
        if state.phase is Phase.MAIN and isinstance(command, AttachEnergy):
            # v0.73: 元気のかたまりは手札のエネルギーカード 2 枚が要るので、手順がエネルギーをつける前に試す（v0.73 のカードのないデッキでは何もしない）
            revive = _v073_trainer(state, command, tried, counts, only=("GD5-019", "ES2-034"))
            if revive is not None:
                return revive
        special = (_v059_energy(state, command, tried, counts)  # v0.59: カツラの 2 枚（カツラの効果がなければ何もしない）
                   or _v082_energy(state, command, tried, counts)  # v0.82: リサイクルエネルギー（手札にないデッキでは何もしない）
                   or _v078_energy(state, command, tried, counts)  # v0.78: 悪・鋼エネルギー（手札にないデッキでは何もしない）
                   or _v058_energy(state, command, tried, counts)  # v0.58: 特殊エネルギー（手札にないデッキでは何もしない）
                   or _v069_step(state, command, tried, counts))  # v0.69: 新しい id の特殊エネルギー・特殊能力・トレーナー（ないデッキでは何もしない）
        if special is not None:
            return special
        if state.phase is Phase.DECISION:
            return (_v031_decision(state, counts) or _v039_decision(state, counts) or _v040_decision(state, counts) or _v041_decision(state, counts)
                    or _v042_decision(state, counts) or command)
        if state.phase is Phase.MAIN and isinstance(command, (UseAttack, EndTurn)):
            power = (_v031_power(state, tried, counts) or _v042_power(state, tried, counts) or _v043_power(state, tried, counts)
                     or _v044_power(state, tried, counts) or _v044_trainer(state, tried, counts)
                     or _v047_power(state, tried, counts) or _v047_trainer(state, tried, counts)  # v0.47
                     or _v048_power(state, tried, counts)  # v0.48
                     or _v049_power(state, tried, counts) or _v049_trainer(state, tried, counts)  # v0.49
                     or _v050_trainer(state, tried, counts) or _v051_trainer(state, tried, counts)  # v0.50・v0.51
                     or _v052_trainer(state, tried, counts) or _v053_trainer(state, tried, counts)  # v0.52・v0.53
                     or _v054_trainer(state, tried, counts) or _v055_trainer(state, tried, counts)  # v0.54・v0.55
                     or _v056_trainer(state, tried, counts)  # v0.56
                     or _v057_trainer(state, tried, counts) or _v057_stadium(state, tried, counts)  # v0.57
                     or _v058_trainer(state, tried, counts)  # v0.58
                     or _v059_trainer(state, tried, counts) or _v059_power(state, tried, counts)  # v0.59
                     or _v061_trainer(state, tried, counts)  # v0.61
                     or _v063_trainer(state, tried, counts)  # v0.63
                     or _v065_trainer(state, tried, counts)  # v0.65
                     or _v066_trainer(state, command, tried, counts)  # v0.66
                     or _v067_trainer(state, tried, counts)  # v0.67
                     or _v073_trainer(state, command, tried, counts)  # v0.73
                     or _v073_trainer(state, command, tried, counts, only=V0_77_TRAINERS)  # v0.77: neo1 のスーパーポケモン回収・マサキの転送装置
                     or _v074_trainer(state, tried, counts) or _v074_stadium(state, tried, counts)  # v0.74
                     or _v080_trainer(state, tried, counts) or _v080_stadium(state, tried, counts)  # v0.80
                     or _v081_trainer(state, tried, counts)  # v0.81
                     or _v082_trainer(state, tried, counts))  # v0.82: エコロジム
            if power is not None:
                return power
            history = _v062_attack(state, tried, counts)  # v0.62: 履歴を読むワザ（ドリルホール・オウムがえし）を使える番に使う
            if history is not None:
                return history
            virtual = _v049_attack(state, tried, counts)  # v0.49: 出どころがいちばん上のカードでないワザ
            if virtual is not None:
                return virtual
            probe = _v036_retreat_probe(state, tried, counts)  # v0.36
            if probe is not None:
                return probe
            retreat = (_v046_retreat(state, tried, counts) or _v058_retreat(state, tried, counts) or _v068_retreat(state, tried, counts)  # v0.46・v0.58
                       or _v061_retreat(state, tried, counts))  # v0.61
            if retreat is not None:
                return retreat
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
        if card_id in V0_78_POKEMON + V0_79 + V0_82_POKEMON:  # v0.79 のポケモンも（C79 は悪・鋼エネルギーを使う）。v0.82 のポケモンも（リサイクルエネルギー）
            # v0.78: 悪・鋼エネルギー（特殊エネルギー）は ``state.energy_types`` では数えられない（provides がない）ので、エンジンの支払いの問い合わせで払えるかを見る
            # （v0.78 のポケモンだけ。前の版の組の手順は変えない）
            usable = [a.index for a in attacks if attack_cost_payable(state, active, a) and ("attack_index", a.index) not in tried]
        if current_form(state, active).kind != "printed":
            # v0.50: 今の姿が「ばける」・［へんしん］のカードのとき、ワザの位置は今の姿のカードのワザ（v0.49 の ``UseAttack``）。いちばん上のカードのワザで払えるかを
            # 見ていたので、今の姿のワザを払えないときに INSUFFICIENT_ENERGY の想定外の拒否になった（v0.50 の M50 対 D49 で起こった。v0.49 の組では起こらなかった）。
            # 今の姿のワザで払えるかを見て、払えるワザがなければ番を終える
            attacks = state.card_def(current_form(state, active).card).attacks
            usable = [a.index for a in attacks if attack_cost_payable(state, active, a) and ("attack_index", a.index) not in tried]
            if not usable and isinstance(command, UseAttack):
                counts[f"v050_form_unpayable_end_{card_id}"] += 1
                return EndTurn(player)
        if card_id in V0_44:
            # v0.44: 場に出てから 1 度しか使えないワザで、このポケモンがもう使ったもの（場のポケモンの記録）は選ばない
            usable = [i for i in usable if (active.card, i) not in active.attacks_used_once]
            if not usable and isinstance(command, UseAttack):
                counts[f"v044_once_used_end_{card_id}"] += 1
                return EndTurn(player)
        if not usable:
            return command
        used = _uses_so_far(state, player, card_id)
        if card_id in V0_31 and all(used[i] >= 2 for i in usable) and any(used[a.index] == 0 and a.index not in usable for a in attacks):
            # v0.31: エネルギーをトラッシュするワザ（やまやき・メラメラなど）を使い続けると、エネルギーがたまらず、もう一つのワザが使えるようにならない。
            # 使えるワザをどれも 2 回以上使い、まだ使っていないワザが必要なエネルギーの不足で使えないときは、この番はワザを使わずに番を終える
            counts[f"v031_wait_{card_id}"] += 1
            return EndTurn(player)
        if card_id in V0_38 + V0_39 + V0_40 + V0_41 + V0_42 + V0_43 + V0_44 + V0_45 + V0_46 + V0_47 + V0_48 + V0_51 + V0_52 + V0_58 + V0_64 + V0_70 + V0_72 + V0_75 + V0_76 + V0_77_POKEMON + V0_79 + V0_82_POKEMON and all(used[i] >= 1 for i in usable) and any(used[a.index] == 0 and a.index not in usable for a in attacks):
            # v0.38: 必要なエネルギーの少ないワザ（でんれい・どくばりタックルなど）を使い続けると、もう一つのワザが使えるようにならない（でんれいは自分を
            # 山札にもどす）。使えるワザをどれも 1 回以上使い、まだ使っていないワザが必要なエネルギーの不足で使えないときは、この番はワザを使わずに番を終える
            counts[f"v038_wait_{card_id}"] += 1  # v0.39〜v0.41 のカードも同じ手順（じばく・メガトンパンチ・ギガスパーク・ひのとりなど）
            return EndTurn(player)
        choice = min(usable, key=lambda i: (used[i], -(attacks[i].damage or 0), i))
        chosen = UseAttack(player, choice)
        if chosen != command:
            counts[f"coverage_choice_{card_id}#{choice}"] += 1
        return chosen

    def policy(state, *, janken_winner, cure, tried):
        if state.face_down_cards:
            # v0.67: 自分のうらのカードは先におもてにする（ワザ・進化でおもてにすることも試す。本当の状態で受け付けるかを確かめる）
            reveal = _v067_reveal(state, tried, counts) if state.phase is Phase.MAIN else None
            if reveal is not None:
                return reveal
            # この手順は対戦を進めるための試験の道具で、場のポケモンの定義を読む。うらのカード（マチスの秘策）の定義は読めない（HiddenPropertyRead）ので、読めなかったら
            # 受け付けられる簡単なコマンドにする（``_v067_fallback``。本当の状態で確かめる）
            try:
                return _policy_body(state, janken_winner=janken_winner, cure=cure, tried=tried)
            except HiddenPropertyRead:
                counts["v067_policy_fallback"] += 1
                return _v067_fallback(state, tried, counts)
        return _policy_body(state, janken_winner=janken_winner, cure=cure, tried=tried)

    def _policy_body(state, *, janken_winner, cure, tried):
        _V052_REAL["state"] = state  # v0.52: 手札を隠した写し（view）ではなく、本当の状態で受け付けるかを確かめる
        _v048_observe(state, counts)
        # v0.48: この番に、最大HPがのっているダメージ以下に下がる（MH1）ので拒否された手札のカード（進化カード・トレーナー）。この番に拒否がなければ空
        blocked = {marker[1] for marker in tried if isinstance(marker, tuple) and marker[0] == "max_hp_drop_card"}
        if state.phase is Phase.MAIN and (blocked or "trainer_locked" in tried or "evolution_prevented" in tried):
            # v0.46: ［アレルギーかふん］でトレーナーカードを使えない番（この番に TRAINER_PREVENTED で拒否された）。元の手順・重ねた手順に、手札のトレーナーカードを
            # 見せずに選ばせる（同じ拒否を繰り返さない）。この番に拒否がなければ何もしないので、前の版の組の結果は変わらない
            # v0.47: ［げんしのちから］で進化できない番（この番に EVOLUTION_PREVENTED で拒否された）も、手札の進化カードを見せずに選ばせる
            # v0.48: MH1 で拒否された手札のカードも見せない
            view = state.clone()
            hand = view.players[state.current_player].hand
            if blocked:
                hand[:] = [uid for uid in hand if uid not in blocked]
                counts["v048_max_hp_drop_masked"] += 1
            if "trainer_locked" in tried:
                hand[:] = [uid for uid in hand if view.card_def(uid).category != "trainer"]
                counts["v046_trainer_masked"] += 1
            if "evolution_prevented" in tried:
                hand[:] = [uid for uid in hand if not view.card_def(uid).is_evolution_pokemon]
                counts["v047_evolution_masked"] += 1
            command = choose(view, janken_winner=janken_winner, cure=cure, tried=tried)
            seen["state"] = state
        else:
            command = choose(state, janken_winner=janken_winner, cure=cure, tried=tried)
        if ("max_hp_drop_command", command) in tried:
            # v0.48: MH1 で拒否された特殊能力の使用をくり返さない（この番を終える）
            counts["v048_max_hp_drop_end_turn"] += 1
            return EndTurn(state.current_player)
        command = _v049_answer(state, command, counts)  # v0.49: 決められない姿・MH1 で拒否される決定の答えを避ける
        if state.phase is Phase.MAIN:
            command = _v057_attack(state, command, tried, counts)  # v0.57: クチバシティジムのコイン
        return command

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
        result["v058"] = v058_uses(state)
        result["v059"] = v059_uses(state)
        result["v060"] = v060_uses(state)
        result["v061"] = v061_uses(state)
        result["v062"] = v062_uses(state)
        result["v063"] = v063_uses(state)
        result["v064"] = v064_uses(state)
        result["v065"] = v065_uses(state)
        result["v066"] = v066_uses(state)
        result["v067"] = v067_uses(state)
        result["v068"] = v068_uses(state)
        result["v069"] = v069_uses(state)
        result["v071"] = v071_uses(state)
        result["v073"] = v073_uses(state)
        result["v074"] = v074_uses(state)
        result["v075"] = v075_uses(state)
        result["v076"] = v076_uses(state)
        result["v077"] = v077_uses(state)
        result["v078"] = v078_uses(state)
        result["v079"] = v079_uses(state)
        result["v080"] = v080_uses(state)
        result["v081"] = v081_uses(state)
        result["v082"] = v082_uses(state)
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
    watch = any(state.cards[uid].card_id in V0_47 + V0_47_TRAINERS + V0_48 + V0_54_TRAINERS + V0_55_TRAINERS + V0_56_TRAINERS + V0_63_TRAINERS
                for uid in state.cards)  # v0.48: 観測の今有効な値も（v0.54・v0.55: 見る・見せるトレーナー）
    for command in commands:
        current = apply_command(current, command)
        if watch:
            failures["observation"] += bool(observation_problems(current))  # v0.47: 受け付けた操作ごとに、プレイヤー・観戦者に渡す観測
    failures["replay_mismatch"] += [dict(e) for e in current.log] != [dict(e) for e in state.log]
    failures["invariants"] += bool(check_invariants(state))
    failures["log"] += bool(log_problems(state))
    failures["serialization"] += bool(serialization_problems(state))
    failures["trainer_sequence"] += bool(result.get("trainer_sequence_problems"))
    for key in CHECK_FAILURES:
        failures[key] += result["policy"].get(key, 0)
    return {k: v for k, v in failures.items() if v}


def v058_uses(state):
    """v0.58: ログから数えた特殊エネルギー・ナツメのサイキックコントロール・ばくれつの動き（特殊エネルギーのない局では空）。

    - ``attach_<カード id>``: 手札からつけた特殊エネルギー（通常の操作）。``energy_heal``・``energy_damage``・``energy_cure``（なんでもなおし配合エネルギーで回復した）・
      ``energy_knock_out``（レインボーエネルギーの 10 できぜつ）
    - ``moved_special_energy``: 場の特殊エネルギーのつけかえ（エナジートランス）。``retreat_special_energy``: 特殊エネルギーをトラッシュした「にげる」
    - ``psychic_control_inner_<カード id>``: サイキックコントロールで使った相手のトラッシュのトレーナー。``psychic_control_none``・``psychic_control_declined``
    - ``explosion_discarded_stadium``・``explosion_without_stadium``: ばくれつで場のスタジアムをトラッシュした・場にスタジアムがなかった
    """
    counts = Counter()
    special = {uid for uid, c in state.cards.items() if c.card_id in V0_58_ENERGIES}
    for e in state.log:
        kind = e["kind"]
        if kind == "attach_energy" and e["energy"] in special:
            counts[f"attach_{state.cards[e['energy']].card_id}"] += 1
        elif kind in ("energy_heal", "energy_damage"):
            counts[kind] += 1
        elif kind == "special_conditions_removed" and e.get("energy_card") is not None:
            counts["energy_cure"] += 1
        elif kind == "knock_out" and e.get("timing") == "energy":
            counts["energy_knock_out"] += 1
        elif kind == "move_energy" and e.get("energy") in special:
            counts["moved_special_energy"] += 1
        elif kind == "retreat" and any(u in special for u in e.get("discarded", e.get("energy", ())) or ()):
            counts["retreat_special_energy"] += 1
        elif kind == "play_trainer" and e.get("source_zone") == "discard":
            counts[f"psychic_control_inner_{state.cards[e['card']].card_id}"] += 1
        elif kind == "discard_trainer_use_none":
            counts["psychic_control_none"] += 1
        elif kind == "discard_trainer_use_declined":
            counts["psychic_control_declined"] += 1
        elif kind == "stadium_discarded" and e.get("reason") == "attack":
            counts["explosion_discarded_stadium"] += 1
        elif kind == "stadium_discard_none":
            counts["explosion_without_stadium"] += 1
    return dict(counts)


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
    - v0.41: ``place_damage_counters#i``・``swap_damage_counters#i``・``attach_energy_from_deck#i``・``attach_energy_from_deck_none#i``・``shuffle#i``、
      ``self_special_condition_<状態>#i``（自分を特殊状態にした）・``attack_heal_own#i``・``attack_heal_opponent#i``（回復したポケモンの持ち主）
    - v0.46: 常にはたらく特殊能力・リフレクターがはたらいたダメージ（発生源のカードで数える）: ``wall_zeroed``・``wall_kept``（［なぞのかべ］。しきい値以上で 0・
      しきい値より小さくそのまま）、``barrier_capped``・``barrier_kept``（［ふしぎなバリアー］）、``halved_<相手>_step<段階>``（［くつろぐかおり］。相手は ``opponent``・
      ``opponent_bench``・``self_bench``・``self``）、``reflector_halved``、``frenzy_bonus``（［きょうぼう］）、``power_damage_modified``（特殊能力のダメージに
      ［ふしぎなバリアー］・［なぞのかべ］を当てはめた）、``immunity_prevented_<状態>``（［めんえき］）、``retreat_increased``（［ねんちゃくえき］）・``retreat_reducible``・
      ``retreat_reduced``（［にげるサポート］で数を変えられた「にげる」・印刷の数より少なくした「にげる」）。ワザの結果は ``attach_energy_from_hand#i``・
      ``hand_to_deck#i``・``shuffle#i``・``self_special_condition_confusion#i``
    - v0.51: ``bench_from_discard_own``・``bench_from_discard_opponent``（トラッシュから持ち主のベンチに出したカードの持ち主が、使ったプレイヤーか相手か）・
      ``bench_from_discard_with_counters``（元気のかけら）・``bench_from_discard_none``・``bench_from_discard_declined``・``invigorate_counters``（よみがえらせるで
      のせたカウンター）・``via_<持ち方>#i``・``copied#i``（ナツメのスリーパーのワザを、ほかのポケモンが［サイコリンク］などで持って使った・まねて使った）・
      ``revived_then_<ログの種類>``（出したポケモンのそのあとの進化・エネルギー・ワザ・バトル場に出す・にげる・きぜつ）。出した効果のカード（よみがえらせるは
      ナツメのスリーパー）で数える
    """
    card = {uid: c.card_id for uid, c in state.cards.items()}
    # v0.69: 写しの組 pool_v0_69 のカード（新しい id）も、元のカードと同じ数え方で数える（元のカードの欄に混ぜない。v0.71: 再録のカード pool_v0_71 も）
    uses = {cid: Counter() for cid in TARGETS + V0_47_TRAINERS + V0_49_TRAINERS + V0_50_TRAINERS + V0_51_TRAINERS + V0_52_TRAINERS + V0_53_TRAINERS
            + V0_54_TRAINERS + V0_55_TRAINERS + V0_56_TRAINERS + V0_69 + V0_71 + V0_73 + V0_74}  # v0.71: 再録のカードも同じ数え方。v0.73: 18 枚のトレーナー
    using55: dict[int, str] = {}  # v0.55: 使っている最中の v0.55 のトレーナー（使ったプレイヤー → カード id）
    using56: dict[int, str] = {}  # v0.56: 使っている最中の v0.56 のトレーナー（使ったプレイヤー → カード id）
    using54: dict[int, str] = {}  # v0.54: 使っている最中の v0.54 のトレーナー（使ったプレイヤー → カード id）
    returned_cards: dict[int, str] = {}  # v0.52: 場から手札・山札にもどしたカードの uid → もどした効果のカード id（そのあと場に出し直したかを数える）
    taken: dict[int, str] = {}  # v0.53: 山札・トラッシュから手札に加えた・山札の一番上に置いたカードの uid → トレーナーのカード id（そのあとの使い道を数える）
    using53: dict[int, str] = {}  # v0.53: 使っている最中の v0.53 のトレーナー（プレイヤー → カード id）
    revived: dict[int, str] = {}  # v0.51: トラッシュからベンチに出した場のポケモンの番号 → 出した効果のカード id（そのあとの行動を数える）
    revived_cards: dict[int, str] = {}  # v0.51: そのポケモンのいちばん上のカードの uid（出したカード・進化で重ねたカード）→ 出した効果のカード id
    current = None  # (カード id, ワザの位置)
    attacker = None  # ワザを使ったプレイヤー
    discarded = False
    power_user = None
    for e in state.log:
        kind = e["kind"]
        if kind == "knock_out" and e.get("timing") == "trainer":
            uses[DEVOLUTION_SPRAY]["knock_out_after_spray"] += 1  # v0.50: 退化スプレーで最大HPがダメージ以下になったポケモンのきぜつ
        # v0.51: トラッシュから持ち主のベンチに出した（よみがえらせる・元気のかけら・ポケモンの笛）と、出したポケモンのそのあとの行動（進化・エネルギー・バトル場・ワザ・きぜつ）
        if kind == "bench_from_discard":
            source = card.get(e.get("trainer_card")) if "trainer_card" in e else SABRINAS_HYPNO
            side = "own" if e["player"] == e["by_player"] else "opponent"
            uses[source][f"bench_from_discard_{side}"] += 1
            if "counters" in e:
                uses[source]["bench_from_discard_with_counters"] += 1
            revived[e["to_pokemon_id"]] = source
            revived_cards[e["card"]] = source
        elif kind in ("bench_from_discard_none", "bench_from_discard_declined"):
            uses[card.get(e.get("trainer_card")) if "trainer_card" in e else SABRINAS_HYPNO][kind] += 1
        elif kind == "place_damage_counters" and e.get("effect") == f"{SABRINAS_HYPNO}#0":
            uses[SABRINAS_HYPNO]["invigorate_counters"] += 1
        elif kind == "attack" and e.get("card_id") == SABRINAS_HYPNO and e.get("route"):
            uses[SABRINAS_HYPNO][f"via_{e['route']}#{e['attack_index']}"] += 1  # ［サイコリンク］・［へんしん］など、ほかのポケモンが使った
        elif kind == "copy_attack" and e["copied"].startswith(SABRINAS_HYPNO + "#"):
            uses[SABRINAS_HYPNO][f"copied{e['copied'][len(SABRINAS_HYPNO):]}"] += 1  # ゆびをふる・ちょうのうりょく・ぼーっとする
        # v0.53: 山札・トラッシュからカードを選ぶトレーナー（選んだ・選ばなかった・コイン）と、選んだカードのそのあとの使い道（場に出した・つけた・進化・使った・引いた）
        if kind == "play_trainer" and card[e["card"]] in V0_53_TRAINERS:
            using53[e["player"]] = card[e["card"]]
            uses[card[e["card"]]]["played"] += 1
        elif kind == "discard_trainer":
            using53.pop(e["player"], None)
        elif e.get("player") in using53 and kind in ("reveal_from_deck", "search_deck", "retrieve_trainer", "put_discard_on_deck_top", "discard_to_deck",
                                                     "trainer_take_none", "hand_to_deck", "discard_from_hand", "coin_flip", "draw"):
            source = using53[e["player"]]
            label = {"trainer_take_none": f"none_{e.get('reason')}", "coin_flip": f"coin_{e.get('result')}"}.get(kind, kind)
            uses[source][label] += 1
            for uid in ([e["card"]] if kind in ("reveal_from_deck", "search_deck", "retrieve_trainer", "put_discard_on_deck_top") else []):
                taken[uid] = source
        elif kind == "draw":
            for uid in e["cards"]:
                if uid in taken:
                    uses[taken.pop(uid)]["taken_then_draw"] += 1  # リサイクルで山札の一番上に置いたカードを、あとで引いた
        # v0.54: 手札の入れ替え・ドロー・情報の確認のトレーナー（もどした・見せた・見た・引いた枚数とプレイヤーの側・コイン・引かない／見ない）
        if kind == "play_trainer" and card[e["card"]] in V0_54_TRAINERS:
            using54[e["player"]] = card[e["card"]]
            uses[card[e["card"]]]["played"] += 1
        elif kind == "discard_trainer":
            using54.pop(e["player"], None)
        elif using54 and kind in ("hand_to_deck", "revealed_hand_to_deck", "reveal_hand", "look_at_hand", "shuffle", "draw", "coin_flip", "discard_from_hand",
                                  "trainer_draw_declined", "trainer_discard_declined", "look_at_deck_top", "look_at_deck_top_none",
                                  "look_at_deck_top_declined", "arrange_deck_top"):
            user, source = next(iter(using54.items()))
            side = "user" if e.get("player") == user else "opponent"
            size = len(e.get("cards", ())) if kind in ("hand_to_deck", "revealed_hand_to_deck", "reveal_hand", "look_at_hand", "draw", "discard_from_hand",
                                                     "look_at_deck_top", "arrange_deck_top") else None
            label = {"coin_flip": f"coin_{e.get('result')}", "trainer_draw_declined": f"draw_declined_{e.get('reason')}",
                     "trainer_discard_declined": f"discard_declined_{e.get('reason')}"}.get(kind, kind)
            uses[source][f"{label}_{side}"] += 1
            if size == 0:
                uses[source][f"{label}_{side}_zero"] += 1
        # v0.55: すぐに使い終わるトレーナー（見た・もどした・はがした・つけなおした・とりのぞいた・回復した・入れ替えた。プレイヤーの側と 0 枚の場合）
        if kind == "play_trainer" and card[e["card"]] in V0_55_TRAINERS:
            using55[e["player"]] = card[e["card"]]
            uses[card[e["card"]]]["played"] += 1
        elif kind == "discard_trainer":
            using55.pop(e["player"], None)
        elif using55 and kind in ("look_at_deck_top", "looked_to_hand", "looked_to_discard", "look_at_hand", "opponent_hand_to_deck", "reveal_hand",
                                  "reveal_from_deck", "trainer_take_none", "shuffle", "discard_pile_to_deck", "deck_top_to_discard", "trainer_discard_energy",
                                  "trainer_return_energy", "trainer_move_energy", "remove_damage_counters", "special_conditions_removed", "coin_flip",
                                  "special_condition", "special_condition_prevented", "discard_hand", "switch", "trainer_switch_skipped", "power_heal"):
            user, source = next(iter(using55.items()))
            side = "user" if e.get("player") == user else "opponent"
            label = {"coin_flip": f"coin_{e.get('result')}", "trainer_take_none": f"none_{e.get('reason')}"}.get(kind, kind)
            uses[source][f"{label}_{side}"] += 1
            if kind in ("looked_to_hand", "discard_pile_to_deck", "deck_top_to_discard", "discard_hand", "trainer_move_energy") and not e.get("cards"):
                uses[source][f"{label}_{side}_zero"] += 1
            if kind == "remove_damage_counters":
                uses[source][f"counters_{e['counters']}_{side}"] += 1
        # v0.56: 相手の決定・番の終わり・期限のある効果のトレーナー（相手の答え・出した・もどした・取ったサイド・番の終わり・効果と使用の禁止の追加と期限）
        if kind == "play_trainer" and card[e["card"]] in V0_56_TRAINERS:
            using56[e["player"]] = card[e["card"]]
            uses[card[e["card"]]]["played"] += 1
        elif kind == "discard_trainer":
            using56.pop(e["player"], None)
        elif using56 and kind in ("look_at_hand", "trainer_bench_from_hand", "trainer_hand_to_active", "return_in_play_to_hand", "hand_positions_to_deck",
                                  "request_answered", "trainer_take_prize", "look_at_card", "swap_prize_with_hand", "coin_flip", "draw",
                                  "discard_from_hand", "trainer_effect_added", "trainer_lock_added", "search_deck", "shuffle"):
            user, source = next(iter(using56.items()))
            side = "user" if e.get("player") == user else "opponent"
            label = {"coin_flip": f"coin_{e.get('result')}", "request_answered": f"answered_{e.get('accepted')}"}.get(kind, kind)
            uses[source][f"{label}_{side}"] += 1
        if kind == "trainer_turn_end":
            uses[ROCKET_GRUNT]["turn_end"] += 1
        elif kind == "trainer_effect_removed":
            uses[{"attack_damage_bonus": MISTY_TRAINER, "poison_on_attack_damage": KOGA_TRAINER}.get(e.get("effect_kind"), INVISIBLE_WALL)]["expired"] += 1
        elif kind == "trainer_lock_removed" and e.get("origin") == "trainer":
            uses[ROCKETS_EXPERIMENT]["lock_expired"] += 1
        elif kind == "damage" and any(m[0] == 6 and card.get(m[1]) == MISTY_TRAINER for m in e.get("modifiers", ())):
            uses[MISTY_TRAINER]["bonus_applied"] += 1
        elif kind == "special_condition" and e.get("effect") == KOGA_TRAINER:
            uses[KOGA_TRAINER]["poisoned"] += 1
        elif kind == "damage_prevented" and e.get("persistent_effect") == "bench_attack_damage_prevention":
            uses[INVISIBLE_WALL]["bench_damage_prevented"] += 1
        hit = {"play_to_bench": e.get("card"), "attach_energy": e.get("energy"), "evolve": e.get("to_card"), "play_trainer": e.get("card"),
               "disguise": e.get("card")}.get(kind)
        if hit in taken:
            uses[taken.pop(hit)][f"taken_then_{kind}"] += 1
        # v0.52: 場から手札・山札にもどした（フジろうじん・ポケモン回収・つれさる）と、もどしたカードをそのあと場に出し直したか
        if kind == "return_basic_to_hand":
            uses[SCOOP_UP][f"returned_{e['zone']}"] += 1
            uses[SCOOP_UP]["returned_with_evolution"] += bool(e["evolution_cards"])
            uses[SCOOP_UP]["returned_with_disguise"] += "disguise" in e
            returned_cards[e["card"]] = SCOOP_UP
        elif kind == "return_in_play_to_deck" and ("trainer_card" in e or e.get("effect") == f"{ERIKAS_DRAGONAIR}#1"):
            source = MR_FUJI if "trainer_card" in e else ERIKAS_DRAGONAIR
            uses[source][f"returned_player{e['player']}"] += 1
            uses[source]["returned_with_evolution"] += bool(e["evolution_stack"])
            uses[source]["returned_with_disguise"] += "disguise" in e
            for uid in e["cards"]:
                returned_cards[uid] = source
        elif kind in ("play_to_bench", "place_starting_pokemon") and e.get("card") in returned_cards:
            uses[returned_cards.pop(e["card"])]["returned_then_replayed"] += 1
        if kind == "evolve" and e.get("pokemon_id") in revived:
            uses[revived[e["pokemon_id"]]]["revived_then_evolve"] += 1
            revived_cards[e["to_card"]] = revived[e["pokemon_id"]]
        uid = {"attach_energy": e.get("target"), "attack": e.get("pokemon"), "knock_out": e.get("pokemon"), "promote_active": e.get("pokemon"),
               "retreat": e.get("new_active")}.get(kind)
        if uid in revived_cards:
            uses[revived_cards[uid]][f"revived_then_{kind}"] += 1
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
        elif kind in ("retaliation", "retaliation_skipped") and card[e["pokemon"]] in V0_45:
            # v0.45: クロスカウンター（効果を持つポケモンのカード）。返した（「おもて」）・コインの「うら」・対象がいない
            uses[card[e["pokemon"]]][f"{kind}_{e.get('coin') or e.get('reason')}"] += 1
        elif kind == "damage" and e.get("damage_zero_below") and card.get(e["damage_zero_below"][0][1]) in V0_45:
            # v0.45: かたくなる（8 段階で 0 になった相手のワザのダメージ・しきい値以上でそのまま受けたダメージ）
            uses[card[e["damage_zero_below"][0][1]]]["zeroed_damage" if e["amount"] == 0 else "harden_exceeded"] += 1
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
        # v0.47: なにかの化石・ピッピ人形（場に出した・すてた・カウントされないきぜつ・重ねた進化）、トレーナーの使用の禁止、見る・入れかえる特殊能力とワザ
        if kind == "play_trainer_as_pokemon":
            uses[card[e["card"]]]["played_as_pokemon"] += 1
        elif kind == "discard_from_play":
            uses[card[e["pokemon"]]]["discarded_from_play" + ("_with_energy" if e["energy"] else "")] += 1
        elif kind == "knock_out" and e.get("counted") is False:
            uses[card[e["pokemon"]]]["knocked_out_uncounted"] += 1
        elif kind == "evolve" and card[e["from_card"]] in V0_47_TRAINERS:
            uses[card[e["from_card"]]][f"evolved_into_{card[e['to_card']]}"] += 1
        elif kind == "trainer_lock_added" and e["effect"].split("#")[0] in uses:
            uses[e["effect"].split("#")[0]]["trainer_lock_added" + ("" if card[e["source_card"]] == e["effect"].split("#")[0] else "_copied")] += 1
        elif kind == "look_at_card" and "power" in e:
            uses[e["power"].split("@")[0]][f"peek_{e['zone']}_{'own' if e['owner'] == e['player'] else 'opponent'}"] += 1
        elif kind == "swap_prize_with_deck_top":
            uses[e["power"].split("@")[0]]["swap_prize"] += 1
        elif kind == "type_shift":
            uses[e["power"].split("@")[0]][f"type_shift_{e['color']}"] += 1  # v0.48: ［へんしょく］（選んだ色ごと）
        if kind == "damage" and e.get("damage_halved"):
            for _, source, rounding in e["damage_halved"]:
                if card[source] == KABUTO:
                    uses[KABUTO]["armor_halved"] += 1  # v0.47: ［カブトアーマー］（8 段階。切りすて）
        if kind in ("counterattack", "power_damage") and any(card[m[0]] == KABUTO for m in e.get("received_modifiers", ())):
            uses[KABUTO]["armor_halved_power_damage"] += 1
        if kind == "damage":
            # v0.46: 常にはたらく特殊能力・リフレクターの記録（docs/continuous-powers-v0.46.md）。前の版のカードの数え方は変えない
            steps = e.get("steps") or ()
            before = {str(step[0]).partition(" ")[2]: steps[i - 1][1] for i, step in enumerate(steps) if i}
            for _, source, threshold in e.get("damage_zero_at_least", ()):
                value = next((v for label, v in before.items() if label.startswith(state.card_def(source).name_ja + "［")), 0)
                uses[card[source]]["wall_zeroed" if value >= threshold else "wall_kept"] += 1
            for _, source, threshold, _ in e.get("damage_set_if_at_least", ()):
                value = next((v for label, v in before.items() if label.startswith(state.card_def(source).name_ja + "［")), 0)
                uses[card[source]]["barrier_capped" if value >= threshold else "barrier_kept"] += 1
            for step, source, rounding in e.get("damage_halved", ()):
                if card[source] in V0_46:
                    key = "reflector_halved" if rounding == "down" else f"halved_{e.get('target', 'opponent')}_step{step}"
                    uses[card[source]][key] += 1
            for _, source, _ in e.get("modifiers", ()):
                if card.get(source) == DARK_PRIMEAPE:
                    uses[DARK_PRIMEAPE]["frenzy_bonus"] += 1
        elif kind in ("counterattack", "power_damage") and e.get("received_modifiers"):
            for source, *_ in e["received_modifiers"]:
                uses[card[source]]["power_damage_modified"] += 1
        elif kind == "special_condition_prevented" and card[e["pokemon"]] in V0_46:
            uses[card[e["pokemon"]]][f"immunity_prevented_{e['condition']}"] += 1
        elif kind in ("retreat", "retreat_failed") and "retreat_cost" in e:
            for pid, key, _ in e["retreat_cost_increases"]:
                uses[key.split("@")[0]]["retreat_increased"] += 1
            for pid, key, _ in e["retreat_cost_reductions"]:
                uses[key.split("@")[0]]["retreat_reducible"] += 1
                if len(e["discarded"]) < e["retreat_cost_printed"] + sum(x[2] for x in e["retreat_cost_increases"]):
                    uses[key.split("@")[0]]["retreat_reduced"] += 1
        power_key = next((str(e[f]) for f in ("power", "effect") if "@power" in str(e.get(f, ""))), None)
        if kind == "pokemon_power":
            power_user = e["player"]  # v0.43: 特殊能力を使ったプレイヤー（くさいかふん・えんかくさいみんの特殊状態がどちらの側か）
        if kind == "pokemon_power" and card[e["pokemon"]] in V0_42 + V0_43:
            uses[card[e["pokemon"]]]["power_declared"] += 1  # v0.42: 宣言する特殊能力の宣言
            if "entry" in e:
                uses[card[e["pokemon"]]]["power_entry_used"] += 1  # v0.43: 場に出たときの特殊能力を使う機会に使った
        elif kind == "entry_power_declined" and card[e["pokemon"]] in V0_43:
            uses[card[e["pokemon"]]]["power_entry_declined"] += 1  # v0.43: 場に出たときの特殊能力を使う機会に使わなかった
        elif kind == "coin_flip" and power_key is not None and power_key.split("@")[0] in V0_43:
            uses[power_key.split("@")[0]][f"power_coin_{e['result']}"] += 1  # v0.43: くさいかふん・えんかくさいみんのコイン
        elif kind in V043_POWER_EVENTS and power_key is not None and power_key.split("@")[0] in V0_43:
            # v0.43: 特殊能力の処理のログ（特殊状態は相手・自分のどちらにしたか）
            side = ("_own" if e["player"] == power_user else "_opponent") if kind == "special_condition" else ""
            uses[power_key.split("@")[0]][f"power_{kind}{side}"] += 1
        elif kind == "coin_flip" and power_key is not None and power_key.split("@")[0] in V0_42:
            uses[power_key.split("@")[0]][f"power_coin_{e['result']}"] += 1  # v0.42: 特殊能力のコイン（ヒーリング・かおりのわな・ぼうぎょかふん）
        elif kind in V042_POWER_EVENTS and power_key is not None and power_key.split("@")[0] in V0_42:
            # v0.42: 特殊能力の処理のログ（使ったカード・はたらいたカードで数える。こんらんにしたかも）
            uses[power_key.split("@")[0]][f"power_{kind}" + (f"_{e['confused']}" if kind == "power_confusion" else "")] += 1
        if kind in ("energy_burn", "power_heal") and card[e["pokemon"]] in uses and not (power_key or "").split("@")[0] in V0_42:
            # v0.31: 特殊能力（エナジーバーン・しぜんになおる・ほのおでかいふく（つけたカード ``trigger`` があるもの））
            uses[card[e["pokemon"]]]["power_heal_on_attach" if "trigger" in e else kind] += 1
        if kind == "attack":
            discarded = False
            # v0.49: ワザを印刷したカード（ログの ``card_id``。出どころがいちばん上のカードでないワザだけに書かれる）で数える。出どころはワザを使ったカードで数える
            printing = e.get("card_id", card[e["pokemon"]])
            current = (printing, e["attack_index"]) if printing in uses else None
            attacker = e["player"]
            if current is not None:
                uses[current[0]][f"attack#{current[1]}"] += 1
            if "route" in e and card[e["pokemon"]] in uses:
                uses[card[e["pokemon"]]][f"v049_route_{e['route']}"] += 1
                if current is not None:
                    uses[current[0]][f"used_by_{card[e['pokemon']]}#{current[1]}"] += 1
        elif kind in ("disguise", "disguise_removed") and card.get(e.get("pokemon")) in uses:
            uses[card[e["pokemon"]]][kind if kind == "disguise" else f"disguise_removed_{e['reason']}"] += 1  # v0.49: 「ばける」
        elif kind == "recall":
            uses[RECALL]["recall"] += 1  # v0.49: 思い出させる
        elif kind == "devolve":
            # v0.50: たいかビーム（ワザの効果。自分・相手のポケモン）・退化スプレー（はがした枚数）
            if "trainer_card" in e:
                uses[DEVOLUTION_SPRAY][f"devolve_{len(e['removed'])}"] += 1
            else:
                uses[MEW]["beam_devolve_" + ("own" if e["player"] == e["by_player"] else "opponent")] += 1
        elif kind == "devolve_declined":
            uses[DEVOLUTION_SPRAY]["devolve_declined"] += 1
        elif kind == "devolve_none":
            uses[MEW]["beam_devolve_none"] += 1
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
            elif kind == "damage" and not e.get("retaliation") and e.get("target") in ("opponent_bench", "self_bench") and cid in V0_33 + V0_34 + V0_37 + V0_38 + V0_39 + V0_40 + V0_43 + V0_46:
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
            elif kind in V041_RESULT_EVENTS and cid in V0_41 and (kind != "shuffle" or e.get("effect") == f"{cid}#{index}"):
                uses[cid][f"{kind}#{index}"] += 1  # v0.41: ダメージシフト・チェンジダメージ・ひなたぼっこ（つけない・つけるものがないも）
            elif kind in V042_RESULT_EVENTS and cid in V0_42 and e.get("effect", f"{cid}#{index}") == f"{cid}#{index}":
                uses[cid][f"{kind}#{index}"] += 1  # v0.42: エネループ・ライフダウン・つきのちから・ようせいのきせき・テレポートブラスト（入れ替えない）
            elif kind in V046_RESULT_EVENTS and cid in V0_46 and e.get("effect") == f"{cid}#{index}":
                uses[cid][f"{kind}#{index}"] += 1  # v0.46: せいちょう・サイコエクスチェンジ
            elif kind in V047_RESULT_EVENTS and cid in V0_47 and e.get("effect") == f"{cid}#{index}":
                uses[cid][f"{kind}#{index}"] += 1  # v0.47: みらいよち・おどろかす・ずつう・こうしゅうは
            elif kind in V048_RESULT_EVENTS and cid in V0_48 and e.get("effect") == f"{cid}#{index}":
                uses[cid][f"{kind}#{index}"] += 1  # v0.48: ダメージぞうふく・やみのこえ（山札を切った）
            if cid in V0_41 + V0_46 and kind == "special_condition" and e.get("effect") == f"{cid}#{index}" and e["player"] == attacker:
                uses[cid][f"self_special_condition_{e['condition']}#{index}"] += 1  # v0.41: くさいにおい・いねむり・こまったねんりきの自分の特殊状態
            if cid in V0_41 and kind == "attack_heal":
                uses[cid][f"attack_heal_{'opponent' if 'attacker' in e else 'own'}#{index}"] += 1  # v0.41: みんなでかいふく（相手のポケモンの回復）
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
         "cards": {}, "games_with": {}, "v058": Counter(), "v058_policy": Counter(), "v059": Counter(), "v059_policy": Counter(),
         "v059_games_with": Counter(), "v060": Counter(), "v060_games_with": Counter(), "v061": Counter(), "v061_games_with": Counter(),
         "v061_policy": Counter(), "v062": Counter(), "v062_games_with": Counter(), "v062_policy": Counter(),
         "v063": Counter(), "v063_games_with": Counter(), "v063_policy": Counter(), "v064": Counter(), "v064_games_with": Counter(),
         "v065": Counter(), "v065_games_with": Counter(), "v065_policy": Counter(),
         "v066": Counter(), "v066_games_with": Counter(), "v066_policy": Counter(),
         "v067": Counter(), "v067_games_with": Counter(), "v067_policy": Counter(),
         "v076": Counter(), "v076_games_with": Counter(), "v076_policy": Counter(),
         "v077": Counter(), "v077_games_with": Counter(), "v077_policy": Counter(),
         "v078": Counter(), "v078_games_with": Counter(), "v078_policy": Counter(),
         "v079": Counter(), "v079_games_with": Counter(), "v079_policy": Counter(),
         "v080": Counter(), "v080_games_with": Counter(), "v080_policy": Counter(),
         "v081": Counter(), "v081_games_with": Counter(), "v081_policy": Counter(),
         "v082": Counter(), "v082_games_with": Counter(), "v082_policy": Counter()}
    for r in games:
        s["v058"].update(r.get("v058", {}))  # v0.58
        s["v058_policy"].update({k: v for k, v in r.get("policy", {}).items() if k.startswith("v058_")})
        s["v059"].update(r.get("v059", {}))  # v0.59
        s["v059_games_with"].update({k: 1 for k, v in r.get("v059", {}).items() if v})
        s["v059_policy"].update({k: v for k, v in r.get("policy", {}).items() if k.startswith("v059_")})
        s["v060"].update(r.get("v060", {}))  # v0.60
        s["v060_games_with"].update({k: 1 for k, v in r.get("v060", {}).items() if v})
        s["v061"].update(r.get("v061", {}))  # v0.61
        s["v061_games_with"].update({k: 1 for k, v in r.get("v061", {}).items() if v})
        s["v061_policy"].update({k: v for k, v in r.get("policy", {}).items() if k.startswith("v061_")})
        s["v062"].update(r.get("v062", {}))  # v0.62
        s["v062_games_with"].update({k: 1 for k, v in r.get("v062", {}).items() if v})
        s["v062_policy"].update({k: v for k, v in r.get("policy", {}).items() if k.startswith("v062_")})
        s["v063"].update(r.get("v063", {}))  # v0.63
        s["v063_games_with"].update({k: 1 for k, v in r.get("v063", {}).items() if v})
        s["v063_policy"].update({k: v for k, v in r.get("policy", {}).items() if k.startswith("v063_")})
        s["v064"].update({k: v for k, v in r.get("v064", {}).items() if k != "barrage_max_heads"})  # v0.64
        s["v064"]["barrage_max_heads"] = max(s["v064"]["barrage_max_heads"], r.get("v064", {}).get("barrage_max_heads", 0))
        s["v064_games_with"].update({k: 1 for k, v in r.get("v064", {}).items() if v})
        s["v065"].update(r.get("v065", {}))  # v0.65
        s["v065_games_with"].update({k: 1 for k, v in r.get("v065", {}).items() if v})
        s["v065_policy"].update({k: v for k, v in r.get("policy", {}).items() if k.startswith("v065_")})
        s["v066"].update(r.get("v066", {}))  # v0.66
        s["v066_games_with"].update({k: 1 for k, v in r.get("v066", {}).items() if v})
        s["v066_policy"].update({k: v for k, v in r.get("policy", {}).items() if k.startswith("v066_")})
        s["v067"].update(r.get("v067", {}))  # v0.67
        s["v067_games_with"].update({k: 1 for k, v in r.get("v067", {}).items() if v})
        s["v067_policy"].update({k: v for k, v in r.get("policy", {}).items() if k.startswith("v067_")})
        s["v076"].update(r.get("v076", {}))  # v0.76
        s["v076_games_with"].update({k: 1 for k, v in r.get("v076", {}).items() if v})
        s["v076_policy"].update({k: v for k, v in r.get("policy", {}).items() if k.startswith("v076_")})
        s["v077"].update(r.get("v077", {}))  # v0.77
        s["v077_games_with"].update({k: 1 for k, v in r.get("v077", {}).items() if v})
        s["v077_policy"].update({k: v for k, v in r.get("policy", {}).items() if k.startswith(("v077_", "v073_neo"))})
        s["v078"].update(r.get("v078", {}))  # v0.78
        s["v078_games_with"].update({k: 1 for k, v in r.get("v078", {}).items() if v})
        s["v078_policy"].update({k: v for k, v in r.get("policy", {}).items() if k.startswith("v078_")})
        s["v079"].update(r.get("v079", {}))  # v0.79
        s["v079_games_with"].update({k: 1 for k, v in r.get("v079", {}).items() if v})
        s["v079_policy"].update({k: v for k, v in r.get("policy", {}).items() if k.startswith("v079_")})
        s["v080"].update(r.get("v080", {}))  # v0.80
        s["v080_games_with"].update({k: 1 for k, v in r.get("v080", {}).items() if v})
        s["v080_policy"].update({k: v for k, v in r.get("policy", {}).items() if k.startswith("v080_")})
        s["v081"].update(r.get("v081", {}))  # v0.81
        s["v081_games_with"].update({k: 1 for k, v in r.get("v081", {}).items() if v})
        s["v081_policy"].update({k: v for k, v in r.get("policy", {}).items() if k.startswith("v081_")})
        s["v082"].update(r.get("v082", {}))  # v0.82
        s["v082_games_with"].update({k: 1 for k, v in r.get("v082", {}).items() if v})
        s["v082_policy"].update({k: v for k, v in r.get("policy", {}).items() if k.startswith("v082_")})
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
    """組ごとに、席を入れかえた 2 とおり × seed の局を行う。v0.56: 組の一覧に同じ 2 つのデッキの組が席を入れかえて 2 回ある（v0.55 の G55-U55 と U55-G55 など）と、
    同じ局（同じデッキの中身・席・seed。先攻とプレイヤーの手順は seed と席で決まる）を 2 回行っていた。1 回目だけを行い、2 回目は行わずに
    ``duplicates``（組の名前・席・seed）に数える（席の違う局は別の局として残す）。局数は ``planned``（組 × 席 × seed）と ``distinct``（行った局）の両方を返す。"""
    results = {}
    played: set[tuple] = set()
    for a, b in pairings:
        games, duplicates = [], []
        for seat in ((a, b), (b, a)):
            for seed in seeds:
                key = (tuple(tuple(deck_cards(label)) for label in seat), seat, seed)
                if key in played:
                    duplicates.append([list(seat), seed])
                    continue
                played.add(key)
                games.append(play(seat, seed, max_steps=max_steps))
        results[f"{a}-{b}"] = {"games": games, "summary": summarize(games), "duplicates": duplicates}
    return results


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--batch", choices=sorted(BATCHES), default="v0.28",
                        help="組の一覧（v0.28・v0.29・v0.30・v0.32〜v0.36 のどれかの 3 組、v0.31・v0.37〜v0.40・v0.43・v0.44・v0.46 の 4 組、v0.41 の 6 組、v0.42・v0.45 の 5 組）")
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
        args.out.write_text(json.dumps({"batch": args.batch, "seeds": [args.start, args.start + args.seeds], "elapsed": elapsed,
                                        "planned": len(BATCHES[args.batch]) * 2 * args.seeds, "distinct": sum(len(v["games"]) for v in results.values()),
                                        "runs": results, "total": total},
                                       ensure_ascii=False, indent=1), encoding="utf-8")
    brief = {name: {**{k: v["summary"][k] for k in ("games", "outcomes", "halt_codes", "unresolved_rejections", "audit_failures")},
                    "duplicates_skipped": len(v["duplicates"])}
             for name, v in results.items()}
    planned = len(BATCHES[args.batch]) * 2 * args.seeds
    distinct = sum(len(v["games"]) for v in results.values())
    print(json.dumps({"elapsed": elapsed, "planned": planned, "distinct": distinct, "runs": brief, "total_cards": total["cards"]}, ensure_ascii=False))
    bad = sum(total["outcomes"].get(k, 0) for k in ("internal_error", "unexpected_rejection", "step_limit"))
    bad += sum(total["audit_failures"].values())
    return 0 if bad == 0 else 1


if __name__ == "__main__":
    sys.exit(main())

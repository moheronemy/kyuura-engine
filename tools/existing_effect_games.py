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
import dataclasses
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
    MOVE_ENERGY, MOVE_OPPONENT_ENERGY, RECOVER_POKEMON, ATTACH_TO_BENCH, OPTIONAL_DRAIN, OPTIONAL_HEAL, ALLOCATE_DAMAGE,
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
from kyuura_engine.effects import color_effect_status, photosynthesis_on, trainer_use_blockers  # noqa: E402  v0.88: color_effect_status・photosynthesis_on
from kyuura_engine.commands import PromoteActive, RemoveDisguise, TakePrize  # noqa: E402  v0.49
from kyuura_engine.effects import PowerKey as E_PowerKey  # noqa: E402  v0.49
from kyuura_engine.effects import (  # v0.95
    ArrangeDeckTopExactlyEffect, DamageThenMillReturnTypeEnergy, MillSelfThenDamage, discard_to_hand_suppressor, rainbow_cards_in,
)
from kyuura_engine.effects import (  # noqa: E402  v0.49
    any_color_energy, attack_cost_payable, available_attacks, current_form, find_attack_option, recall_records, shapeshift_choices,
)
from kyuura_engine.decisions import SELECT_DEVOLVE_COUNT  # noqa: E402  v0.50
from kyuura_engine import effects as E  # v0.85
from kyuura_engine.effects import devolution_candidates, devolution_forbidden  # noqa: E402  v0.50
from kyuura_engine.stadiums import bench_limit  # v0.57
from kyuura_engine.decisions import USE_DISCARD_TRAINER  # v0.58
from kyuura_engine.decisions import SELECT_OPPONENT_ATTACK  # v0.76
from kyuura_engine.decisions import SELECT_MARKER_COUNT  # v0.90
from kyuura_engine.state import AttackBarrier  # v0.107: そらをとぶの防護（v107_uses）
from kyuura_engine.markers import marker_count  # v0.90
from kyuura_engine.continuous import goop_gas_effects  # v0.59
from kyuura_engine.effects import blaine_effects  # v0.59
from kyuura_engine.effects import DamageThenCoinPerOpponentBench, attack_rebellion_powers, evasion_power  # v0.60
from kyuura_engine.persistent import tails_damage_guard  # v0.60
from kyuura_engine.persistent import retreat_pursuits  # v0.117
from kyuura_engine.decisions import KNOCK_OUT_POWER  # v0.61
from kyuura_engine.effects import energy_unit_count  # v0.61
from kyuura_engine.effects import LASTING_RECEIVED_ELEMENTS, REFLECTABLE_RECEIVED_ELEMENTS, used_attack_last_turn  # v0.62
from kyuura_engine.history import other_received_on, received_on  # v0.62
from kyuura_engine.decisions import BENCH_FROM_DISCARD  # noqa: E402  v0.51
from kyuura_engine.effects import bench_from_discard_candidates, trainer_attack_damage_bonuses, trainer_poison_effects  # noqa: E402  v0.51・v0.56
from kyuura_engine.resolution.programs import all_answers  # noqa: E402  v0.49
from tests.log_audit import log_problems, observation_problems, serialization_problems  # noqa: E402
from tests.v017_games import V093_LEAVE_CODES, play_game  # noqa: E402
from tests.test_machamp_games_v0_10 import working as counter_working  # v0.99: C18 の止める関数（はんげき）
from tests.test_rocket_snorlax_v0_17b import restless_working  # v0.99: C18 の止める関数（わるいねぞう）
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
                   "UNRESOLVED_MAX_HP_DROP",
                   "UNRESOLVED_TRANSFORM_REVIVED_BASIC",  # v0.120: TF3（［へんしん］で写す相手が、たねポケモンとしてあつかう進化カード）
                   # v0.124: 変身の共通ルール・すごいへんしんで、決められない・扱えない姿（TK1・BX2・SV2〜SV4・写した特殊能力の未対応）
                   "UNRESOLVED_TRANSFORM_REVERT_KNOCKOUT_TIMING", "UNRESOLVED_TRANSFORM_BABY_AND_BASIC", "UNRESOLVED_SUPER_TRANSFORM_SOURCE_CHANGE",
                   "UNRESOLVED_SUPER_TRANSFORM_COPIED_POWER", "UNRESOLVED_SUPER_TRANSFORM_SUPPRESSED_FORM", "UNSUPPORTED_TRANSFORM_COPIED_POWER")
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
# v0.83（docs/shining-gentle-pokemon-v0.83.md）: ひかるポケモン 10 枚・やさしいポケモン 7 枚・ギャロップ（ES1-014）（写しの組 pool_v0_83）。ポケモンは TARGETS に加え、使っていないワザを
# 選ぶ手順・エネルギーをためる手順を重ねる（払えるかはエンジンの支払いの問い合わせ）。ワザの決定（相手プレイヤーの決定を含む）は ``_v083_decision`` が答える。ログから数えるのは ``v083_uses``
V0_83 = tuple(__import__("kyuura_engine.cards", fromlist=["read_extract"]).read_extract()["pool_v0_83"])
# v0.84（docs/light-powers-evolution-v0.84.md）: ポケモン育て屋夫婦・やさしいポケモン 12 枚（写しの組 pool_v0_84）。ポケモンは TARGETS に加え、使っていないワザを選ぶ手順・
# エネルギーをためる手順を重ねる。ワザ・特殊能力・トレーナーの決定（相手プレイヤーの決定・場に出たときの特殊能力の使う機会を含む）は ``_v084_decision``、宣言して使う
# ［おいはらう］とポケモン育て屋夫婦は ``_v084_step`` が使う。ログから数えるのは ``v084_uses``
V0_84 = tuple(__import__("kyuura_engine.cards", fromlist=["read_extract"]).read_extract()["pool_v0_84"])
V0_84_POKEMON = V0_84[1:]
V0_84_TRAINERS = V0_84[:1]
# v0.85（docs/entry-powers-energy-lifecycle-v0.85.md）: 進化したときの特殊能力・エネルギーを動かすポケモン 13 枚とミラクルエネルギー（写しの組 pool_v0_85）。ポケモンは TARGETS に加え、
# 使っていないワザを選ぶ手順・エネルギーをためる手順を重ねる（払えるかはエンジンの支払いの問い合わせ。［おいしげる］で変わる）。決定（使う機会を含む）は ``_v085_decision``、
# 宣言して使う特殊能力（［ファイヤーリチャージ］・［どしゃぶり］・［ファイヤーレイズ］）は ``_v085_step``、ミラクルエネルギーは ``_v085_energy``。ログから数えるのは ``v085_uses``、
# ［きせきのかぜ］で効果の消えた場の特殊エネルギーは手順の中で数える（``v085_wind_neutralized_<カード>``）
V0_85 = tuple(__import__("kyuura_engine.cards", fromlist=["read_extract"]).read_extract()["pool_v0_85"])
V0_85_POKEMON = V0_85[:13]
MIRACLE_ENERGY = "neo4-113"
# v0.86（docs/entry-energy-evolution-reactions-v0.86.md）: 登場・エネルギー・進化への反応 13 枚（写しの組 pool_v0_86）。ポケモンは TARGETS に加え、使っていないワザを選ぶ手順・
# エネルギーをためる手順を重ねる（払えるかはエンジンの支払いの問い合わせ）。反応の決定（順番・使う機会・進化カード・［いなびかり］の入れ替え。相手の決定にも答える）と
# v0.86 のカードのワザ・特殊能力の決定は ``_v086_decision``、［ソーラーパワー］は ``_v086_step``。ログから数えるのは ``v086_uses``
V0_86 = tuple(__import__("kyuura_engine.cards", fromlist=["read_extract"]).read_extract()["pool_v0_86"])
V0_86_POKEMON = V0_86
# v0.87（docs/movement-damage-reactions-v0.87.md）: 場の移動・ダメージへの反応と、控えの保護・「にげる」の禁止のポケモン 14 枚（写しの組 pool_v0_87）。ポケモンは TARGETS に加え、
# 使っていないワザを選ぶ手順・エネルギーをためる手順を重ねる。v0.87 の反応の決定（［やけのこり］のカード・［ぶんれつ］・同じ時点の順番）と v0.87 のカードのワザ・特殊能力の決定は
# ``_v087_decision``、［マグネット］と、相手の［とおせんぼ］のある番の「にげる」の確かめは ``_v087_step``。ログから数えるのは ``v087_uses``
V0_87 = tuple(__import__("kyuura_engine.cards", fromlist=["read_extract"]).read_extract()["pool_v0_87"])
V0_87_POKEMON = V0_87
# v0.88（docs/type-energy-colors-v0.88.md）: ポケモンのタイプとエネルギーの色を変える特殊能力、色を選ぶ・数えるワザ、変えたカードをつけ替える特殊能力の 11 枚（写しの組 pool_v0_88）。
# ポケモンは TARGETS に加え、使っていないワザを選ぶ手順・エネルギーをためる手順を重ねる（払えるかはエンジンの支払いの問い合わせ。色を変える効果で変わる）。v0.88 のカードのワザ・特殊能力の
# 決定（色・特殊状態・トラッシュのカード）は ``_v088_decision``、［せんすい］・［エナジーコンバーター］・［でんじりょく］は ``_v088_step``、［すいりょくはつでん］（ワザの宣言といっしょ）は
# ``_v088_attack``。ログから数えるのは ``v088_uses``
V0_88 = tuple(__import__("kyuura_engine.cards", fromlist=["read_extract"]).read_extract()["pool_v0_88"])
V0_88_POKEMON = V0_88
# v0.89（docs/selected-target-damage-v0.89.md）: 対象を選ぶダメージ・選べる回復のポケモン 17 枚（写しの組 pool_v0_89）。ポケモンは TARGETS に加え、使っていないワザを選ぶ手順・
# エネルギーをためる手順を重ねる。v0.89 のワザの決定（選ぶポケモン（相手が選ぶものも）・トラッシュのカード・減らす量・ESP）は ``_v089_decision``（選ぶと止める答えは選ばない）。ログから
# 数えるのは ``v089_uses``
V0_89 = tuple(__import__("kyuura_engine.cards", fromlist=["read_extract"]).read_extract()["pool_v0_89"])
V0_89_POKEMON = V0_89
# v0.90（docs/markers-counters-v0.90.md）: マーカー・ダメージカウンター以外のカウンターのポケモン 7 枚（写しの組 pool_v0_90）。ポケモンは TARGETS に加え、使っていないワザを選ぶ手順・
# エネルギーをためる手順を重ねる。v0.90 のワザの決定（取りのぞく数・色・相手のエネルギーカード）は ``_v090_decision``。ログから数えるのは ``v090_uses``
V0_90 = tuple(__import__("kyuura_engine.cards", fromlist=["read_extract"]).read_extract()["pool_v0_90"])
V0_90_POKEMON = V0_90
# v0.91（docs/marker-check-field-reset-v0.91.md）: 残りのマーカーのポケモン 3 枚とヒノアラシ（写しの組 pool_v0_91）。ポケモンは TARGETS に加え、使っていないワザを選ぶ手順・
# エネルギーをためる手順を重ねる。v0.91 のワザの決定（選ぶポケモン・色）は ``_v091_decision``。ログから数えるのは ``v091_uses``
V0_91 = tuple(__import__("kyuura_engine.cards", fromlist=["read_extract"]).read_extract()["pool_v0_91"])
V0_91_POKEMON = V0_91
# v0.92（docs/power-suppression-lasting-locks-v0.92.md）: 能力の消去・続く制限のポケモン 8 枚（写しの組 pool_v0_92）。ポケモンは TARGETS に加え、使っていないワザを選ぶ手順・
# エネルギーをためる手順を重ねる。v0.92 のワザの決定（だましうちの選ぶポケモン）は ``_v092_decision``。ログから数えるのは ``v092_uses``
V0_92 = tuple(__import__("kyuura_engine.cards", fromlist=["read_extract"]).read_extract()["pool_v0_92"])
V0_92_POKEMON = V0_92
# v0.93（docs/active-leave-locks-v0.93.md）: バトル場をはなれられない効果・続くワザの制限のポケモン 9 枚（写しの組 pool_v0_93）。ポケモンは TARGETS に加え、使っていないワザを選ぶ手順・
# エネルギーをためる手順を重ねる。はなれられない対戦ポケモンの「にげる」・入れ替えのトレーナーを 1 番に 1 度試す（``_v093_probe``）。ログから数えるのは ``v093_uses``
V0_93 = tuple(__import__("kyuura_engine.cards", fromlist=["read_extract"]).read_extract()["pool_v0_93"])
V0_93_POKEMON = V0_93
# v0.94（docs/switch-return-attacks-v0.94.md）: 入れ替え・帰還のワザのポケモン 13 枚（写しの組 pool_v0_94）。ポケモンは TARGETS に加え、使っていないワザを選ぶ手順・エネルギーをためる手順を
# 重ねる。v0.94 のワザの決定（きつねびの任意の入れ替えは、入れ替えない答えも順に選ぶ）は ``_v094_decision``。ログから数えるのは ``v094_uses``
V0_94 = tuple(__import__("kyuura_engine.cards", fromlist=["read_extract"]).read_extract()["pool_v0_94"])
V0_94_POKEMON = V0_94
# v0.95（docs/private-looks-deck-movement-v0.95.md）: 手札・山札を見る効果とカードを動かすポケモン 11 枚（写しの組 pool_v0_95）。ポケモンは TARGETS に加え、使っていないワザを選ぶ手順・
# エネルギーをためる手順を重ねる。v0.95 のワザ・特殊能力の決定は ``_v095_decision``、［みやぶる］・［わるぢえ］は ``_v095_step``。ログから数えるのは ``v095_uses``
V0_95 = tuple(__import__("kyuura_engine.cards", fromlist=["read_extract"]).read_extract()["pool_v0_95"])
V0_95_POKEMON = V0_95
V095_DECLARED = ("neo1-065", "neo4-061")  # ヨルノズク［みやぶる］・わるいヤドキング［わるぢえ］
# v0.96（docs/unown-family-powers-v0.96.md）: アンノーン 7 枚（ワザ 7・特殊能力 7）と遺跡の石版 2 枚（写しの組 pool_v0_96）。ポケモンは TARGETS に加える。v0.96 の特殊能力・トレーナーの
# 決定は ``_v096_decision``、［OBSERVE］・［LAUGH］・［SEARCH］・［TELL］は ``_v096_step``、遺跡の石版は ``_v096_trainer``、［ZOOM］の「にげる」は ``_v096_retreat``。ログから数えるのは
# ``v096_uses``。デッキのアンノーンはどれも合わせて 4 枚まで（カードのルール文。デッキの検査を緩めない）
V0_96 = tuple(__import__("kyuura_engine.cards", fromlist=["read_extract"]).read_extract()["pool_v0_96"])
V0_96_POKEMON = V0_96[:7]
V0_96_TRAINERS = V0_96[7:]
V096_DECLARED = ("PF2-003", "neo4-050", "neo4-051", "neo4-052")  # アンノーン[O]［OBSERVE］・L［LAUGH］・S［SEARCH］・T［TELL］
# v0.97（docs/unown-research-idfnj-v0.97.md）: アンノーンI・D・F・[N]・[J] の 5 枚（写しの組 pool_v0_97）。ポケモンは TARGETS に加える。v0.97 の特殊能力の決定は ``_v097_decision``、
# ［FIND］・［JOIN］は ``_v097_step``。ログから数えるのは ``v097_uses``。デッキのアンノーンはどれも合わせて 4 枚まで（カードのルール文。デッキの検査を緩めない）
V0_97 = tuple(__import__("kyuura_engine.cards", fromlist=["read_extract"]).read_extract()["pool_v0_97"])
V0_97_POKEMON = V0_97
V097_DECLARED = ("neo2-026", "PRN-034")  # アンノーンF［FIND］・アンノーン[J]［JOIN］
V097_DF = {"neo2-025": "D", "PF2-001": "N"}  # ［DARK df］・［NORMAL df］
# v0.98（docs/unown-bear-yield-vanish-give-v0.98.md）: アンノーンB・Y・V・G の 4 枚（写しの組 pool_v0_98）。ポケモンは TARGETS に加える。v0.98 の特殊能力の決定（［VANISH］の使う機会・
# 選ぶアンノーン、［YIELD］・［GIVE］のカード・つける先）は ``_v098_decision``、［BEAR］・［YIELD］・［GIVE］は ``_v098_step``。ログから数えるのは ``v098_uses``。デッキのアンノーンはどれも
# 合わせて 4 枚まで（カードのルール文。デッキの検査を緩めない）
V0_98 = tuple(__import__("kyuura_engine.cards", fromlist=["read_extract"]).read_extract()["pool_v0_98"])
V0_98_POKEMON = V0_98
V098_DECLARED = ("neo3-032", "neo3-033", "neo4-062")  # アンノーンB［BEAR］・Y［YIELD］・G［GIVE］
# v0.99（docs/unown-perform-help-history-v0.99.md）: アンノーンP・H とタッツーの 3 枚（写しの組 pool_v0_99）。ポケモンは TARGETS に加える。［HELP］は ``_v099_step``（宣言して使う）、
# ［PERFORM］は常にはたらく（手順は何もしない）。ログから数えるのは ``v099_uses``（前の相手の番に受けたダメージは、ログのダメージから場所ごとに組み立て直す）。デッキのアンノーンはどれも
# 合わせて 4 枚まで（H99 は H・E・L・P の 4 枚。I を加えない）
V0_99 = tuple(__import__("kyuura_engine.cards", fromlist=["read_extract"]).read_extract()["pool_v0_99"])
V0_99_POKEMON = V0_99
V099_DECLARED = ("neo4-063",)  # アンノーンH［HELP］
UNOWN_P, UNOWN_H, NEO_HORSEA = "neo4-058", "neo4-063", "neo1-023"
# v0.100（docs/sketch-perish-song-history-v0.100.md）: ドーブル・ムウマの 2 枚（写しの組 pool_v0_100）。ポケモンは TARGETS に加える。ワザの選び方は ``_v100_attack``（スケッチは払えれば
# 使う。ムウマは相手がねむりなら「ほろびのうた」、ねむりでなければ「やみのひとみ」）。ログから数えるのは ``v100_uses``
V0_100 = tuple(__import__("kyuura_engine.cards", fromlist=["read_extract"]).read_extract()["pool_v0_100"])
V0_100_POKEMON = V0_100
SMEARGLE, MISDREAVUS, GASTLY_BASE = "neo2-052", "neo3-035", "PMCG1-044"
# v0.101（docs/counter-keep-energy-protection-v0.101.md）: ソーナンス・アンノーンK の 2 枚（写しの組 pool_v0_101）。ポケモンは TARGETS に加える。ソーナンスは払えれば「カウンター」を使う
# （``_v101_attack``）。アンノーンK の［KEEP］は常にはたらく（手順は何もしない）。ログから数えるのは ``v101_uses``
V0_101 = tuple(__import__("kyuura_engine.cards", fromlist=["read_extract"]).read_extract()["pool_v0_101"])
V0_101_POKEMON = V0_101
WOBBUFFET, UNOWN_K, UNOWN_D = "neo2-031", "neo3-030", "neo2-025"
# v0.102（docs/weakness-resistance-powers-v0.102.md）: トランセル・バリヤードの 4 枚（写しの組 pool_v0_102。同じデータの 2 組で、デッキには id ごとに 2 枚ずつ入れる）。ポケモンは TARGETS に
# 加える。ワザ（ふしぎなこな・ジャグリング）は既存の手順のまま選ぶ。［グリーンシールド］・［ニュートラルダメージ］は常にはたらく（手順は何もしない）。ワザを宣言した時点の配置は
# ``_v102_attack_observe``、ログから数えるのは ``v102_uses``
V0_102 = tuple(__import__("kyuura_engine.cards", fromlist=["read_extract"]).read_extract()["pool_v0_102"])
V0_102_POKEMON = V0_102
METAPOD_ES1, METAPOD_QSG, MR_MIME_ES1, MR_MIME_QSG = "ES1-003", "QSG-003", "ES1-021", "QSG-030"
# v0.103（docs/neutral-shield-attack-origin-v0.103.md）: ミュウの 2 枚（写しの組 pool_v0_103。同じデータの 1 組で、デッキには id ごとに 2 枚ずつ入れる）。ポケモンは TARGETS に加える。
# ワザ（ねんりき）は既存の手順のまま選ぶ。［ニュートラルシールド］は常にはたらく（手順は何もしない）。ログから数えるのは ``v103_uses``
V0_103 = tuple(__import__("kyuura_engine.cards", fromlist=["read_extract"]).read_extract()["pool_v0_103"])
V0_103_POKEMON = V0_103
MEW_COROCORO, MEW_JR = "PR1-005", "PR1-012"
# v0.104（docs/healing-pokemon-v0.104.md）: 回復のワザを持つポケモンの 12 枚（写しの組 pool_v0_104。同じデータの 3 組と、同じカードの組で文面の違う IP1-018）。ポケモンは TARGETS に
# 加える。ワザは既存の手順のまま選ぶ（使った数の少ないワザから）。決定（あまいみつの選ぶポケモン・プリンのかいふくの取り除くか）は ``_v104_decision``。ログから数えるのは ``v104_uses``
V0_104 = tuple(__import__("kyuura_engine.cards", fromlist=["read_extract"]).read_extract()["pool_v0_104"])
V0_104_POKEMON = V0_104
BELLOSSOM, MILTANK, TEDDIURSA, PILOSWINE = "neo1-015", "neo1-069", "neo2-048", "neo3-041"
BULBASAUR_ES1, BULBASAUR_QSG, BULBASAUR_IP1 = "ES1-001", "QSG-001", "IP1-018"
DEWGONG_ES2, DEWGONG_QSG, JIGGLYPUFF_COROCORO, JIGGLYPUFF_BOOK, LAPRAS_SI = "ES2-007", "QSG-018", "PR1-002", "PR1-004", "SI-018"
NEO_ODDISH, NEO_GLOOM, PRN_BELLOSSOM, SEEL_ES2, SWINUB_NEO3 = "neo1-001", "neo1-008", "PRN-043", "ES2-006", "neo3-038"
BASE_CATERPIE, BASE_DROWZEE, BASE_BELLSPROUT = "PMCG1-002", "PMCG1-045", "PMCG2-005"
# v0.105（docs/recovery-evolution-coin-branches-v0.105.md）: 回復・山札からの進化・コインの分岐のポケモンの 5 枚（写しの組 pool_v0_105）。ポケモンは TARGETS に加える。ワザは既存の手順のまま
# 選ぶ（使った数の少ないワザから）。決定（山札から重ねる進化カード）は ``_v105_decision``。ログから数えるのは ``v105_uses``。山札を見た場合だけ切ることは、やり直しの状態の山札の枚数で
# 照らす（``v105_replay_problems``。監査の ``v105_shuffle``）
V0_105 = tuple(__import__("kyuura_engine.cards", fromlist=["read_extract"]).read_extract()["pool_v0_105"])
V0_105_POKEMON = V0_105
METAPOD_NEO2, SUNKERN_NEO4, BUTTERFREE_NEO2, CELEBI_PF3, DELIBIRD_NEO3 = "neo2-006", "neo4-003", "neo2-009", "PF3-002", "neo3-050"
CATERPIE_NEO2, BUTTERFREE_JUNGLE, SUNFLORA_NEO1, LIGHT_SUNFLORA = "neo2-001", "PMCG2-007", "neo1-013", "neo4-004"
# v0.106（docs/counts-coins-compositions-v0.106.md）: 数とコインを組み合わせるポケモンの 11 枚（写しの組 pool_v0_106。同じデータの 2 組）。ポケモンは TARGETS に加える。ワザは既存の手順のまま
# 選ぶ（使った数の少ないワザから）。v0.106 のワザは新しい決定を出さない（順番・お上品攻撃・［にげこむ］などの既存の決定は既存の手順が答える）。ログから数えるのは ``v106_uses``
V0_106 = tuple(__import__("kyuura_engine.cards", fromlist=["read_extract"]).read_extract()["pool_v0_106"])
V0_106_POKEMON = V0_106
GRANBULL_NEO1, SCYTHER_NEO2, KABUTOPS_NEO2, FARFETCHD_NEO3, GEODUDE_ES1 = "neo1-068", "neo2-008", "neo2-018", "neo3-046", "ES1-023"
VOLTORB_ES2, VOLTORB_QSG, NIDORINA_ES3, HAUNTER_ES3_GRUDGE, SANDSLASH_ES3, SANDSLASH_QSG = "ES2-016", "QSG-025", "ES3-002", "ES3-023", "ES3-027", "QSG-034"
SNUBBULL_NEO1, SANDSHREW_ES2, SANDSHREW_QSG, NIDORAN_F_ES1, NIDORAN_F_QSG, NIDORAN_M_ES1 = "neo1-061", "ES2-020", "QSG-033", "ES1-006", "QSG-004", "ES1-007"
NIDORINO_ES3, GASTLY_ES3, GASTLY_QSG = "ES3-003", "ES3-022", "QSG-028"
# v0.107（docs/coin-failure-status-flight-v0.107.md）: コインによる成否・特殊状態・防護のポケモンの 9 枚（写しの組 pool_v0_107）。ポケモンは TARGETS に加える。ワザは既存の手順のまま
# 選ぶ（使った数の少ないワザから）。v0.107 のワザは新しい決定を出さない（［にげこむ］・お上品攻撃・ESP などの既存の決定は既存の手順が答える）。ログから数えるのは ``v107_uses``
V0_107 = tuple(__import__("kyuura_engine.cards", fromlist=["read_extract"]).read_extract()["pool_v0_107"])
V0_107_POKEMON = V0_107
WEEDLE_NEO2, PINECO_NEO2, URSARING_NEO2, PSYDUCK_NEO4, MISTYS_SHELLDER = "neo2-002", "neo2-005", "neo2-051", "neo4-026", "GD2-006"
FLYING_PIKACHU_18, FLYING_PIKACHU_42, FLYING_PIKACHU_63, BUTTERFREE_SI, CATERPIE_ES1 = "PR1-018", "PR1-042", "PR1-063", "SI-003", "ES1-002"
# v0.108（docs/damage-modifiers-condition-bonuses-v0.108.md）: 持続するダメージの変更・相手の特殊状態を参照するポケモンの 5 枚（写しの組 pool_v0_108）。ポケモンは TARGETS に加える。ワザは
# 既存の手順のまま選ぶ（使った数の少ないワザから）。v0.108 のワザは新しい決定を出さない（かえんほうしゃのトラッシュするカード・順番・お上品攻撃などの既存の決定は既存の手順が答える）。
# ログから数えるのは ``v108_uses``
V0_108 = tuple(__import__("kyuura_engine.cards", fromlist=["read_extract"]).read_extract()["pool_v0_108"])
V0_108_POKEMON = V0_108
HOUNDOOM_NEO2, CHINCHOU_NEO3, TOGEPI_NEO4, DARK_WIGGLYTUFF, ARBOK_ES3, HOUNDOUR_NEO2 = "neo2-041", "neo3-024", "neo4-088", "neo4-091", "ES3-001", "neo2-012"
DARKNESS_NEO1 = "neo1-094"  # 悪エネルギー（かみくだくの悪 1 個）
# v0.109（docs/timed-damage-guards-v0.109.md）: 次の相手の番に受けるときのコインでダメージを防ぐ効果・相手のタイプで決まるダメージのポケモンの 3 枚（写しの組 pool_v0_109）。ポケモンは
# TARGETS に加える。ワザは既存の手順のまま選ぶ（使った数の少ないワザから。使っていないワザのためにエネルギーをためる手順も v0.38〜と同じ）。v0.109 のワザは新しい決定を出さない（受けるときの
# コインは決定ではない）。ログから数えるのは ``v109_uses``
V0_109 = tuple(__import__("kyuura_engine.cards", fromlist=["read_extract"]).read_extract()["pool_v0_109"])
V0_109_POKEMON = V0_109
WOOPER_NEO2, HITMONCHAN_NEO4, KADABRA_ES3 = "neo2-015", "neo4-070", "ES3-019"
GASTLY_NEO4 = "neo4-048"  # ゴース（neo4。あくむ（超）10）。P109 の「超」のたねポケモン
# v0.110（docs/endure-armor-up-v0.110.md）: 使うときのコインで、残りHPがなくなっても「きぜつ」しない期間つきの効果を自分に与えるワザのポケモンの 2 枚（写しの組 pool_v0_110）。ポケモンは
# TARGETS に加える。ワザは既存の手順のまま選ぶ（使った数の少ないワザから。使っていないワザのためにエネルギーをためる手順も v0.38〜と同じ）。v0.110 のワザは新しい決定を出さない（「きぜつ」
# しない効果は自動で、使うときのコインは決定ではない）。ログから数えるのは ``v110_uses``
V0_110 = tuple(__import__("kyuura_engine.cards", fromlist=["read_extract"]).read_extract()["pool_v0_110"])
V0_110_POKEMON = V0_110
PHANPY_NEO1, DARK_FORRETRESS = "neo1-053", "neo4-008"
PINECO_NEO4, PINECO_NEO2 = "neo4-005", "neo2-005"  # クヌギダマ（neo4。たいあたり（無無）20）・クヌギダマ（neo2。とつぜんじばく（草）40）。わるいフォレトスの進化元
# v0.111（docs/field-energy-card-counts-v0.111.md）: 場のエネルギーカードの枚数でダメージ・ワザの使用条件が決まるポケモンの 4 枚（写しの組 pool_v0_111）。ポケモンは TARGETS に加える。
# ワザは既存の手順のまま選ぶ（使った数の少ないワザから。使っていないワザのためにエネルギーをためる手順も v0.38〜と同じ。ただし、この番にシンクロウェーブを枚数の違いで拒否されたなら
# 待たない）。シンクロウェーブの拒否（ENERGY_CARD_COUNTS_DIFFER）は既知の拒否（``V031_STOPS``。場の枚数を道具が別に数えて確かめる）。v0.111 のワザは新しい決定を出さない。ログから数える
# のは ``v111_uses``、宣言の時点の場は ``_v111_attack_observe``
V0_111 = tuple(__import__("kyuura_engine.cards", fromlist=["read_extract"]).read_extract()["pool_v0_111"])
V0_111_POKEMON = V0_111
MEWTWO_ES1, MEWTWO_QSG, SABRINAS_ABRA_GD6, SABRINAS_ABRA_PR1 = "ES1-022", "QSG-032", "GD6-001", "PR1-060"
# v0.112（docs/energy-coins-draw-v0.112.md）: 水エネルギーの個数によるコインとドロー・コインのマヒと自分のワザの制限のポケモンの 2 枚（写しの組 pool_v0_112）。ポケモンは TARGETS に
# 加える。ワザは既存の手順のまま選ぶ（使った数の少ないワザから。使っていないワザのためにエネルギーをためる手順も v0.38〜と同じ。ただし、この番にふしょくえきを「うら」の制限で拒否された
# なら待たない）。ふしょくえきの「うら」の制限で使えないワザの拒否（ATTACK_LOCKED）は既存の既知の拒否。v0.112 のワザは新しい決定を出さない。ログから数えるのは ``v112_uses``、
# 宣言の時点の場（「水」の基本エネルギーカードの枚数・山札の枚数）は ``_v112_attack_observe``
V0_112 = tuple(__import__("kyuura_engine.cards", fromlist=["read_extract"]).read_extract()["pool_v0_112"])
V0_112_POKEMON = V0_112
TENTACRUEL_SI, OMASTAR_PR1 = "SI-016", "PR1-051"
# v0.113（docs/variable-coins-search-attachments-v0.113.md）: 可変枚数のコインと、山札の検索・つける・場全体のトラッシュのポケモンの 6 枚（写しの組 pool_v0_113）。ポケモンは TARGETS に
# 加える。ワザは既存の手順のまま選ぶ（使った数の少ないワザから。使っていないワザのためにエネルギーをためる手順も v0.38〜と同じ。悪エネルギー（特殊エネルギー）で払うくろいキバのため、
# 払えるかはエンジンの問い合わせで見る（v0.78 と同じ））。v0.113 のワザの決定（みんなでおどるの山札のカード・ゆうでんのカードとつける先・ダークフレイムとファイヤーラッシュのトラッシュ・
# ダークフレイムのつけるカード・なかまをよぶの出すカード）は ``_v113_decision`` が答える。ログから数えるのは ``v113_uses``、処理する時点の場は ``_v113_attack_observe``
V0_113 = tuple(__import__("kyuura_engine.cards", fromlist=["read_extract"]).read_extract()["pool_v0_113"])
V0_113_POKEMON = V0_113
CLEFAIRY_NEO1, AMPHAROS_NEO3, MURKROW_NEO3, HOUNDOOM_NEO3, DARK_TYPHLOSION_NEO4, ROCKETS_MEOWTH_PR1 = V0_113
MAREEP_NEO1, FLAAFFY_NEO1, HOUNDOUR_NEO2, CYNDAQUIL_NEO4, DARK_QUILAVA_NEO4, MURKROW_NEO1 = "neo1-038", "neo1-041", "neo2-039", "neo4-016", "neo4-020", "neo1-055"
DARKNESS_PRN, DARKNESS_NIP2X = "PRN-002", "NIP2X-010"
# v0.114（docs/baby-rules-evolution-v0.114.md）: ベイビィポケモン 13 枚（写しの組 pool_v0_114）。ポケモンは TARGETS に加える（ワザは既存の手順のまま。ワザのないエレキッド・ププリンは
# 番を終える）。対戦準備・ベンチに出す手順（tests/helpers.py の ``basics_in_hand``）はベイビィポケモンのカードもたねポケモンと同じに出す（ベイビィのないデッキでは前の版と同じ）。
# ベイビィの進化（手札のたねポケモンカードを重ねる）は ``_v114_evolve``、［じっとみる］・［わんぱくパンチ］は ``_v114_power``、ログから数えるのは ``v114_uses``、ワザの停止は ``V0_114_STOPS``
V0_114 = tuple(__import__("kyuura_engine.cards", fromlist=["read_extract"]).read_extract()["pool_v0_114"])
V0_114_POKEMON = V0_114
# v0.115（docs/spread-damage-allocation-v0.115.md）: 場・ベンチへのダメージ、対象ごとのコイン、ダメージの配分のポケモン 13 枚（写しの組 pool_v0_115）。ポケモンは TARGETS に加える（ワザは
# 既存の手順のまま選ぶ）。v0.115 のワザの決定（配分・選ぶポケモン・ロックブラストのトラッシュ・ばくれつしんかの山札のカード）は ``_v115_decision`` が答える。ログから数えるのは ``v115_uses``、
# ワザの停止は ``V0_115_STOPS``
V0_115 = tuple(__import__("kyuura_engine.cards", fromlist=["read_extract"]).read_extract()["pool_v0_115"])
V0_115_POKEMON = V0_115
# v0.116（docs/energy-movement-attachment-devolution-v0.116.md）: エネルギーの付け替え・ついた時の効果・付属カードの回収と退化のポケモン 13 枚（写しの組 pool_v0_116）。ポケモンは TARGETS に
# 加える（ワザは既存の手順のまま選ぶ）。v0.116 のワザの決定（選ぶ控え・はがすカード・つけるポケモン・退化させるポケモン・ベンチに出すカード・手札に加えるカード）は ``_v116_decision`` が
# 答える。ログから数えるのは ``v116_uses``、ワザ・特殊能力の停止は ``V0_116_STOPS``
V0_116 = tuple(__import__("kyuura_engine.cards", fromlist=["read_extract"]).read_extract()["pool_v0_116"])
V0_116_POKEMON = V0_116
# v0.117（docs/retreat-return-active-powers-v0.117.md）: 場の移動・にげる時の反応・条件付きの特殊能力のポケモン 13 枚（写しの組 pool_v0_117）。ポケモンは TARGETS に加える（ワザは既存の
# 手順のまま選ぶ）。［QUICKEN］は ``_v117_step``、［CHASE］・おいうちのある「にげる」は ``_v117_retreat``、ログから数えるのは ``v117_uses``。止まる場面は tests/v017_games.py の
# ``v117_stop_expected`` が場から確かめる
V0_117 = tuple(__import__("kyuura_engine.cards", fromlist=["read_extract"]).read_extract()["pool_v0_117"])
V0_117_POKEMON = V0_117
# v0.118（docs/unbounded-coins-heal-allocation-v0.118.md）: 上限なしコイン・攻撃時の能力・回復の配分のポケモン 9 枚（写しの組 pool_v0_118）。ポケモンは TARGETS に加える（ワザは既存の
# 手順のまま選ぶ）。ワザの決定（とりのぞく数の配分・選ぶ控え・のぞむならのコイン）は ``_v118_decision``、特殊能力の決定（トラッシュのスタジアム・山札の上に置く手札）は
# ``_v118_power_decision``、［トランスポート］・［じくうへんかん］は ``_v118_step``、［XXXXX］（ワザの宣言といっしょ）は ``_v118_attack``、ログから数えるのは ``v118_uses``。止まる場面は
# tests/v017_games.py の ``v118_stop_expected`` が場から確かめる
V0_118 = tuple(__import__("kyuura_engine.cards", fromlist=["read_extract"]).read_extract()["pool_v0_118"])
V0_118_POKEMON = V0_118
# v0.119（docs/damage-reactions-poison-sleep-v0.119.md）: 受けるダメージの選択・どくとねむり・場の効果のポケモン 11 枚（写しの組 pool_v0_119）。ポケモンは TARGETS に加える（ワザは
# 既存の手順のまま選ぶ）。ワザの決定（ひきずりこむの任意の入れ替え・［シェルアーマー］を使うか）は ``_v119_decision``、［ポイズンミスト］は ``_v119_step``、［めいれい］（ワザの宣言と
# いっしょ）は ``_v119_attack``、ログから数えるのは ``v119_uses``。止まる場面は tests/v017_games.py の ``v119_stop_expected`` が場から確かめる
V0_119 = tuple(__import__("kyuura_engine.cards", fromlist=["read_extract"]).read_extract()["pool_v0_119"])
V0_119_POKEMON = V0_119
# v0.120（docs/fossil-basic-virtual-attacks-v0.120.md）: 化石の復活と仮想ワザの供給の 11 枚（写しの組 pool_v0_120。ポケモン 10・トレーナー 1）。ポケモンは TARGETS に加える（ワザは既存の
# 手順のまま選び、許可で使えるワザ（［げんしのきおく］・［にんぎょうつかい］・［ものまね］）は v0.49 の ``_v049_attack`` が支払うポケモンで払えるかを見て使う）。ワザ・特殊能力・たまごの化石の
# 決定は ``_v120_decision``、［なかまのふっかつ］・［かせきのふっかつ］は ``_v120_step``、たまごの化石は ``_v120_trainer``、ログから数えるのは ``v120_uses``。止まる場面は
# tests/v017_games.py の ``v120_stop_expected`` と、この道具の止まる理由の表が場から確かめる
V0_120 = tuple(__import__("kyuura_engine.cards", fromlist=["read_extract"]).read_extract()["pool_v0_120"])
V0_120_TRAINERS = ("neo2-055",)
V0_120_POKEMON = tuple(card for card in V0_120 if card not in V0_120_TRAINERS)
# v0.121（docs/hand-bench-attack-conditions-v0.121.md）: 手札からの登場とワザの使用条件の 9 枚（写しの組 pool_v0_121。ポケモン 7・トレーナー 2）。ポケモンは TARGETS に加える（ワザは既存の
# 手順のまま選び、ねむり状態のおおいびきも宣言できるかをエンジンに問い合わせる。悪エネルギーはエンジンの支払いの問い合わせで払う）。ワザ・トレーナーの決定は ``_v121_decision``、
# ボロのつりざお・カスミのてあては ``_v121_trainer``、ログから数えるのは ``v121_uses``。止まる場面は、この道具の止まる理由の表が場から確かめる
V0_121 = tuple(__import__("kyuura_engine.cards", fromlist=["read_extract"]).read_extract()["pool_v0_121"])
V0_121_TRAINERS = ("neo3-053", "PR1-073")
V0_121_POKEMON = tuple(card for card in V0_121 if card not in V0_121_TRAINERS)
V121_OLD_ROD, V121_MISTYS_CARE = V0_121_TRAINERS
# v0.122（docs/unown-fossil-retreat-reactions-v0.122.md）: アンノーンの併用・化石の進化履歴・退却時の反応の 13 枚（写しの組 pool_v0_122。どれもポケモン）。TARGETS に加える（ワザは既存の手順のまま
# 選び、悪・鋼エネルギー・無色2個エネルギーはエンジンの支払いの問い合わせで払う）。［ANGER］と［XXXXX］のいっしょの宣言は ``_v122_attack``、宣言する特殊能力は ``_v122_step``、［つるでひっぱる］の
# 「にげる」は ``_v122_retreat``、決定は ``_v122_decision``、ログから数えるのは ``v122_uses``。止まる場面は、この道具の止まる理由の表が場から確かめる
V0_122 = tuple(__import__("kyuura_engine.cards", fromlist=["read_extract"]).read_extract()["pool_v0_122"])
V0_122_POKEMON = V0_122
V122_M, V122_U, V122_A, V122_W = "neo2-027", "neo2-028", "neo2-030", "neo4-064"
V122_RAICHU, V122_OMANYTE, V122_KABUTO, V122_AERODACTYL, V122_OMANYTE3 = "GD3-003", "ES2-011", "ES2-028", "ES2-029", "ES3-018"
V122_CAPOEIRA, V122_IVYSAUR, V122_VENUSAUR, V122_FEAROW = "PRN-030", "PRN-039", "PRN-040", "PRN-045"
V122_POWER_HOLDERS = (V122_U, V122_W, V122_OMANYTE, V122_KABUTO, V122_OMANYTE3)
# v0.123（docs/arcanine-name-migration-v0.123.md 9 章）: ウィンディ系の 3 枚（写しの組 pool_v0_123。どれもポケモン）。TARGETS に加える（ワザは既存の手順のまま選び、いかりのほのお・ほのおのあらしの
# 炎エネルギーカードを選ぶ決定も元の手順のまま答える。新しい手順は加えていない）。ログから数えるのは ``v123_uses``（名前を直した登録済みの 2 枚のワザも数える）
V0_123 = tuple(__import__("kyuura_engine.cards", fromlist=["read_extract"]).read_extract()["pool_v0_123"])
V0_123_POKEMON = V0_123
V123_RENAMED = (ARCANINE, BLAINES_ARCANINE)  # 段 v0.123 で名前を直した登録済みのカード（第1弾のウィンディ・カツラのウィンディ）
V123_RAGE_FLAMES = "PR1-016#1"
# v0.124（docs/super-transform-dark-pulse-v0.124.md 10 章）: メタモン（拡張シート第2弾赤版。［すごいへんしん］）と GR団のミュウツー（［わるいはどう］・わるいぞうふく）。TARGETS に加え、
# ［すごいへんしん］を使う手順 ``_v124_power`` と選ぶポケモンの決定 ``_v124_decision`` を重ねる。ログから数えるのは ``v124_uses``
V0_124 = tuple(__import__("kyuura_engine.cards", fromlist=["read_extract"]).read_extract()["pool_v0_124"])
V0_124_POKEMON = V0_124
V124_SUPER_DITTO, V124_GR_MEWTWO = "ES2-032", "PRN-041"
# v0.125（docs/wigglytuff-helping-hand-v0.125.md 11 章）: プクリン（拡張シート第1弾青版。［てだすけ］・ふくらむ）。TARGETS に加え、［てだすけ］を使う手順 ``_v125_power`` を重ねる。
# ログから数えるのは ``v125_uses``
V0_125 = tuple(__import__("kyuura_engine.cards", fromlist=["read_extract"]).read_extract()["pool_v0_125"])
V0_125_POKEMON = V0_125
V125_WIGGLYTUFF = "ES1-027"
# v0.126（docs/flash-faceup-deck-v0.126.md 10 章）: フラッシュ（拡張シート第2弾赤版。トレーナー）。使う手順 ``_v126_trainer``・並べかえの答え ``_v126_decision``・おもてのいちばん上を
# 見てサカキのニャースのワザを選ぶ手順 ``_v126_attack`` を重ねる。ログから数えるのは ``v126_uses``
V0_126 = tuple(__import__("kyuura_engine.cards", fromlist=["read_extract"]).read_extract()["pool_v0_126"])
V126_FLASH = "ES2-035"
# v0.127（docs/deferred-shortage-user-promos-v0.127.md 12 章）: ファイヤー 2 枚（ドライアップ）・怪電波マシーン（枚数不足の途中停止）と、利用者が指定した簡略ルールのプロモ 3 枚（_のピカチュウ 2 枚・
# ハマちゃんのヤドキング）。ワザ・トレーナーの手順 ``_v127_attack``・``_v127_trainer``・決定の答え ``_v127_decision`` を重ねる。ログから数えるのは ``v127_uses``
V0_127 = tuple(__import__("kyuura_engine.cards", fromlist=["read_extract"]).read_extract()["pool_v0_127"])
V127_MOLTRES, V127_TWM, V127_PIKACHU, V127_SLOWKING = ("ES2-005", "QSG-055"), "neo4-108", ("PR1-044", "PR1-090"), "PR1-072"
# v0.129（docs/blaines-quiz-heights-v0.129.md 8 章）: カツラのクイズ その1。使う手順 ``_v129_trainer``・置くカードと身長の答え ``_v129_decision`` を重ねる。ログから数えるのは ``v129_uses``。
# 答えの方策は 2 つ（``V129_ANSWER_POLICIES``）: ``knowledge``（正解を目ざす。観測の伝えた名前と、公開のカードの一覧（名前 → 全国図鑑番号）・公開の身長の参照値だけを読む）と ``wrong``
# （開発用の、意図して誤る方策。knowledge の答えに 1 cm を足す）。どちらも置いたカード・続きの情報の正解を読まない。どちらを使うかは公開の情報（番の番号と使ったトレーナーの uid）で決まる
# 決まった割り当てで、結果を見て答えを変えない
V0_129 = tuple(__import__("kyuura_engine.cards", fromlist=["read_extract"]).read_extract()["pool_v0_129"])
V129_QUIZ = "GD5-016"
V129_ANSWER_POLICIES = ("knowledge", "wrong")
# v0.130（docs/trade-please-ownership-v0.130.md 10 章）: とりかえっこプリーズ。使う手順 ``_v130_trainer``・選ぶカードと答え ``_v130_decision`` を重ねる。ログから数えるのは ``v130_uses``。
# 方策はどれも公開の情報と、決めるプレイヤーが見ている手札（選べるもの）だけを読む決まった割り当てで、正式な対戦の前に決めた（結果を見て変えない）: 使ったプレイヤーが選ぶカードは
# 選べるもののうち (番の番号 + 使ったトレーナーの uid) を数で割った余りの位置、相手が選ぶカードは (3 × 番の番号 + 使ったトレーナーの uid) の余りの位置、答えは (番の番号 + 使ったトレーナーの
# uid) が偶数ならオーケー、奇数ならオーケーでない
V0_130 = tuple(__import__("kyuura_engine.cards", fromlist=["read_extract"]).read_extract()["pool_v0_130"])
V130_SWAP = "PR1-027"
# v0.131（docs/exeggutor-bilingual-names-v0.131.md 10 章）: ナッシー[Exeggutor] 2 枚（日英併記の名前は利用者が指定した扱い）。新しい方策は加えない（進化・ワザは元の手順、カツラのクイズ
# その3 は v0.63 の手順、スロットゲームは v0.80 の手順のまま）。ログから数えるのは ``v131_uses``
V0_131 = tuple(__import__("kyuura_engine.cards", fromlist=["read_extract"]).read_extract()["pool_v0_131"])
V131_EXEGGUTOR, V131_EXEGGUTOR_B = V0_131
V131_SLOT_GAME = "neo1-090"
DEFAULT_EFFECTS_FOR_TOOL = E.DEFAULT_EFFECTS
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
           + V0_82_POKEMON  # v0.82: エネルギーカードをトラッシュするワザを持つポケモン 18 枚
           + V0_83  # v0.83: ひかるポケモン 10 枚・やさしいポケモン 7 枚・ギャロップ（ES1-014）
           + V0_84_POKEMON  # v0.84: やさしいポケモン 12 枚
           + V0_85_POKEMON  # v0.85: 進化したときの特殊能力・エネルギーを動かすポケモン 13 枚
           + V0_86_POKEMON  # v0.86: 登場・エネルギー・進化への反応 13 枚
           + V0_87_POKEMON  # v0.87: 場の移動・ダメージへの反応と、控えの保護・「にげる」の禁止 14 枚
           + V0_88_POKEMON  # v0.88: タイプとエネルギーの色を変える・色を選ぶ・数えるポケモン 11 枚
           + V0_89_POKEMON  # v0.89: 対象を選ぶダメージ・選べる回復のポケモン 17 枚
           + V0_90_POKEMON  # v0.90: マーカー・ダメージカウンター以外のカウンターのポケモン 7 枚
           + V0_91_POKEMON  # v0.91: 残りのマーカーのポケモン 3 枚とヒノアラシ
           + V0_92_POKEMON  # v0.92: 能力の消去・続く制限のポケモン 8 枚
           + V0_93_POKEMON  # v0.93: バトル場をはなれられない効果・続くワザの制限のポケモン 9 枚
           + V0_94_POKEMON  # v0.94: 入れ替え・帰還のワザのポケモン 13 枚
           + V0_95_POKEMON  # v0.95: 手札・山札を見る効果とカードを動かすポケモン 11 枚
           + V0_96_POKEMON  # v0.96: アンノーン 7 枚
           + V0_97_POKEMON  # v0.97: アンノーン 5 枚
           + V0_98_POKEMON  # v0.98: アンノーン 4 枚
           + V0_99_POKEMON  # v0.99: アンノーンP・H とタッツー
           + V0_100_POKEMON  # v0.100: ドーブル・ムウマ
           + V0_101_POKEMON  # v0.101: ソーナンス・アンノーンK
           + V0_102_POKEMON  # v0.102: トランセル・バリヤード
           + V0_103_POKEMON  # v0.103: ミュウ（ニュートラルシールド）
           + V0_104_POKEMON  # v0.104: 回復のワザを持つポケモン 12 枚
           + V0_105_POKEMON  # v0.105: 回復・山札からの進化・コインの分岐のポケモン 5 枚
           + V0_106_POKEMON  # v0.106: 数とコインを組み合わせるポケモン 11 枚
           + V0_107_POKEMON  # v0.107: コインによる成否・特殊状態・防護のポケモン 9 枚
           + V0_108_POKEMON  # v0.108: 持続するダメージの変更・相手の特殊状態を参照するポケモン 5 枚
           + V0_109_POKEMON  # v0.109: 次の相手の番に受けるときのコインでダメージを防ぐ効果・相手のタイプで決まるダメージのポケモン 3 枚
           + V0_110_POKEMON  # v0.110: 使うときのコインで、残りHPがなくなっても「きぜつ」しない期間つきの効果を自分に与えるワザのポケモン 2 枚
           + V0_111_POKEMON  # v0.111: 場のエネルギーカードの枚数でダメージ・ワザの使用条件が決まるポケモン 4 枚
           + V0_112_POKEMON  # v0.112: 水エネルギーの個数によるコインとドロー・コインのマヒと自分のワザの制限のポケモン 2 枚
           + V0_113_POKEMON  # v0.113: 可変枚数のコインと、山札の検索・つける・場全体のトラッシュのポケモン 6 枚
           + V0_114_POKEMON  # v0.114: ベイビィポケモン 13 枚
           + V0_115_POKEMON  # v0.115: 場・ベンチへのダメージ、対象ごとのコイン、ダメージの配分のポケモン 13 枚
           + V0_116_POKEMON  # v0.116: エネルギーの付け替え・ついた時の効果・付属カードの回収と退化のポケモン 13 枚
           + V0_117_POKEMON  # v0.117: 場の移動・にげる時の反応・条件付きの特殊能力のポケモン 13 枚
           + V0_118_POKEMON  # v0.118: 上限なしコイン・攻撃時の能力・回復の配分のポケモン 9 枚
           + V0_119_POKEMON  # v0.119: 受けるダメージの選択・どくとねむり・場の効果のポケモン 11 枚
           + V0_120_POKEMON  # v0.120: 化石の復活と仮想ワザの供給のポケモン 10 枚
           + V0_121_POKEMON  # v0.121: 手札からの登場とワザの使用条件のポケモン 7 枚
           + V0_122_POKEMON  # v0.122: アンノーンの併用・化石の進化履歴・退却時の反応のポケモン 13 枚
           + V0_123_POKEMON  # v0.123: ウィンディ系の 3 枚
           + V0_124_POKEMON  # v0.124: メタモン（すごいへんしん）・GR団のミュウツー
           + V0_125_POKEMON)  # v0.125: プクリン（てだすけ・ふくらむ）
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
    # v0.126: 無色・闘。フラッシュ 4 枚と、山札を引く（マサキ）・山札をさがして切る（パソコン通信）トレーナー。コラッタ → ラッタ・イワーク
    "F126": ((RATTATA, 4), (RATICATE, 3), (ONIX, 3), (V126_FLASH, 4), (driver.BILL, 2), (driver.COMPUTER_SEARCH, 3), (SWITCH, 2), (driver.POTION, 2),
             (FIGHTING, 37)),
    # v0.126: 闘。サカキのニャース（てつだうふり。相手の山札のいちばん上のカードの種類で変わる）4 枚とフラッシュ 3 枚。おもてにした相手のいちばん上を見て、ワザを選ぶ（CR-FLASH-TOP-CARD-SEEN）
    "M126": ((GIOVANNIS_MEOWTH_40, 4), (RATTATA, 4), (RATICATE, 3), (ONIX, 3), (V126_FLASH, 3), (driver.BILL, 2), (SWITCH, 2), (driver.POTION, 2),
             (FIGHTING, 37)),
    # v0.127: 炎・無色。ファイヤー 4 枚（ES2-005・QSG-055 を 2 枚ずつ。同じ名前で 4 枚まで）と怪電波マシーン 3 枚。相手の「水」エネルギーカードを見てドライアップを使う（足りなければ途中停止）
    "F127": (("ES2-005", 2), ("QSG-055", 2), (RATTATA, 4), (RATICATE, 3), (V127_TWM, 3), (driver.BILL, 2), (SWITCH, 2), (driver.POTION, 2), (FIRE, 40)),
    # v0.127: 雷・超。_のピカチュウ 4 枚（PR1-044・PR1-090 を 2 枚ずつ。同じ名前で 4 枚まで）とヤドン → ハマちゃんのヤドキング（利用者が指定した簡略ルールのワザ）。怪電波マシーンは入れない
    # （通常のプロモの対戦。途中停止の起こる対戦と分けて数える）
    "P127": (("PR1-044", 2), ("PR1-090", 2), (SLOWPOKE, 4), (V127_SLOWKING, 3), (driver.BILL, 2), (SWITCH, 2), (driver.POTION, 2), (LIGHTNING, 22), (PSYCHIC, 21)),
    # v0.129: 闘・無色。カツラのクイズ その1 4 枚と、出題に使うポケモン: ディグダ（いちばん低い 20cm の種族）・ダグトリオ・イワーク（880cm）・ハガネール（いちばん高い 920cm。鋼のワザは
    # 使えないが手札で出題できる）・ポリゴン・ポリゴン2（公式の表記は「ポリゴン２」）・エリカのフシギダネ（所有者名つき。図鑑番号 1）。図鑑番号のないポリゴン ES1-033・イワーク ES2-024 は
    # 選べるが選ぶと止める（手順は選ばず、出たことを数える）
    "Q129": ((V129_QUIZ, 4), ("PMCG1-052", 4), ("PMCG1-056", 2), ("PMCG1-054", 2), ("ES2-024", 1), ("neo1-057", 1), ("PMCG1-064", 2), ("ES1-033", 2),
             ("neo3-051", 2), ("PMCG5-007", 2), (driver.BILL, 2), (SWITCH, 2), (driver.POTION, 2), (FIGHTING, 32)),
    # v0.130: 闘・無色。とりかえっこプリーズ 4 枚と、交換したカードを場に出す・進化させる・つける・トラッシュする・山札にもどす・手札にもどす・サイドに置く経路のカード: たね（エビワラー・
    # コラッタ・イワーク）と 1 進化（ラッタ）、退化スプレー（進化カードを手札にもどす）・ポケモン回収（たねを手札にもどし、ほかはトラッシュ）・ポケモン交換おじさん（手札のポケモンを山札に
    # もどす）・にせオーキドはかせ（相手の手札を山札にもどす）・オーキドはかせ（手札をトラッシュ）・にせオーキドの発明（相手のサイドを山札にもどして置きなおす）・プラスパワー（つける
    # トレーナー）・錯乱ジム（相手がかわりに使うことを選ぶと止まる経路。UQ-CHAOS-GYM-BORROWED-TURN）
    "T130": ((V130_SWAP, 4), (HITMONCHAN, 3), (RATTATA, 4), (RATICATE, 3), (ONIX, 2), ("PMCG1-086", 1), ("PMCG1-092", 1), ("PMCG1-093", 1), ("PMCG1-089", 1),
             ("PMCG1-077", 1), ("neo4-111", 1), ("PMCG5-087", 1), (driver.BILL, 2), (SWITCH, 1), (driver.POTION, 1), (driver.PLUSPOWER, 2), (FIGHTING, 31)),
    # v0.131: 草・超。タマタマ（PMCG2-006・neo4-049 を 2 枚ずつ。「タマタマ」4 枚）→ ナッシー[Exeggutor]（PR1-075 2 枚・PR1-077 1 枚）と通常のナッシー（PMCG2-012）1 枚（「ナッシー」をちょうど 4 枚。デッキの
    # 同じ名前の数え方を通す）、カツラのクイズ その3（置くカード・伝えるワザ名・答えの名前）・スロットゲーム（同じ名前のカード）、ピッピ（ゆびをふる。相手のワザをまねる）・メタモン
    # （［へんしん］。相手の対戦ポケモンと同じカードとしてあつかう）
    "X131": ((EXEGGCUTE, 2), ("neo4-049", 2), (V131_EXEGGUTOR, 2), (V131_EXEGGUTOR_B, 1), ("PMCG2-012", 1), (CLEFAIRY, 2), (DITTO, 1), (BLAINES_QUIZ_3, 3),
             (V131_SLOT_GAME, 2), (driver.BILL, 2), (driver.POTION, 1), (SWITCH, 1), (GRASS, 26), (PSYCHIC, 14)),
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
    # v0.83: ひかるポケモン（名前ごとに 1 枚まで。ひかるコイキングは neo3-022 の 1 枚だけ）と、闘・無色のたねポケモン。鋼エネルギー（4 枚まで）でひかるハガネールのワザを払う
    "S83": (("neo3-022", 1), ("neo3-023", 1), ("neo4-013", 1), ("neo4-047", 1), ("neo4-068", 1), ("neo4-080", 1), ("neo4-084", 1), ("neo4-098", 1),
            ("PRN-044", 1), ("PMCG1-058", 4), ("PMCG1-060", 4), ("neo1-095", 4), (WATER, 10), (FIRE, 6), (LIGHTNING, 7), (PSYCHIC, 6), (FIGHTING, 8), (GRASS, 2)),
    # v0.83: やさしいポケモン 7 種類（進化元は名前の完全一致）・ギャロップ（ES1-014。QSG-011 と同じデータ）
    "G83": (("neo1-006", 3), ("neo4-004", 2), ("PMCG2-004", 3), ("neo4-006", 2), ("PMCG3-010", 2), ("neo4-032", 2), ("PMCG2-037", 2), ("neo4-034", 2),
            ("neo1-037", 2), ("neo4-045", 2), ("PMCG3-027", 2), ("neo4-054", 2), ("PMCG1-065", 2), ("neo4-093", 2), ("PMCG1-016", 2), ("ES1-014", 2),
            (GRASS, 6), (WATER, 6), (PSYCHIC, 5), (LIGHTNING, 5), (FIRE, 4)),
    # v0.84: 草・炎・闘・無色のやさしいポケモン（進化元は名前の完全一致）と、ポケモン育て屋夫婦
    "G84": (("neo1-003", 4), ("neo4-010", 3), ("neo4-014", 3), ("neo4-018", 2), ("neo4-015", 3), ("neo4-021", 2), ("neo4-069", 4), ("neo4-074", 3),
            ("neo4-077", 2), ("neo4-085", 3), ("neo4-090", 2), ("neo1-066", 3), ("neo4-095", 2), ("neo3-056", 4), (GRASS, 5), (FIRE, 8), (FIGHTING, 7)),
    # v0.84: 水・雷・無色のやさしいポケモンと、やさしいカイリュー（［きせきのかぜ］）。特殊エネルギー（無色2個エネルギー・リサイクルエネルギー・悪エネルギー）・エコロジム
    "W84": (("neo4-027", 3), ("neo4-033", 2), ("neo1-025", 4), ("neo4-040", 3), ("neo4-029", 3), ("neo4-041", 2), ("PMCG2-037", 3), ("neo4-043", 2),
            ("PMCG1-065", 4), ("neo4-093", 3), ("neo4-094", 2), ("PMCG1-096", 4), ("neo1-096", 4), ("neo1-094", 2), ("neo1-086", 2), (WATER, 11),
            (LIGHTNING, 6)),
    # v0.85: 草・炎・雷（チコリータ → ベイリーフ → メガニウム（［おいしげる］・［ハーブのかおり］）・ヒノアラシ → マグマラシ → バクフーン（［ファイヤーリチャージ］・
    # ［ファイヤーブースト］）・メリープ（せいでんき））
    "M85": (("neo1-002", 4), ("neo1-009", 2), ("PF1-002", 2), ("neo1-014", 2), ("PF1-003", 1), ("NIP1X-001", 1), ("neo1-018", 4), ("PF1-005", 3),
            ("neo1-021", 1), ("PF1-006", 1), ("neo1-038", 4), (GRASS, 16), (FIRE, 12), (LIGHTNING, 7)),
    # v0.85: 水・炎（ワニノコ → アリゲイツ → オーダイル（［あばれんぼう］・［どしゃぶり］）・ヒトカゲ → リザード → リザードン（［ファイヤーレイズ］））と、ポケモン育て屋さん
    "F85": (("neo1-024", 4), ("PF1-008", 3), ("NIP2-004", 1), ("neo1-033", 2), ("PF1-009", 1), ("NIP2X-001", 1), ("PMCG1-014", 4), ("PMCG1-017", 3),
            ("PF2-009", 2), ("PMCG1-094", 2), (WATER, 20), (FIRE, 17)),
    # v0.85: やさしいカイリュー（［きせきのかぜ］）・やさしいトゲチック・ひかるコイキングと、ミラクルエネルギー・無色2個エネルギー・リサイクルエネルギー・悪エネルギー・鋼エネルギー
    # （［きせきのかぜ］で効果の消える特殊エネルギーを、正式な対戦の場に出す）
    "L85": (("PMCG1-065", 4), ("neo4-093", 3), ("neo4-094", 2), ("neo1-066", 3), ("neo4-095", 2), ("neo3-022", 1), (MIRACLE_ENERGY, 4), ("PMCG1-096", 4),
            ("neo1-096", 4), ("neo1-094", 2), ("neo1-095", 2), (WATER, 21), (LIGHTNING, 8)),
    # v0.86: イーブイ（［エナジーしんか］2 枚・［れんさしんか］1 枚。同じ名前で 4 枚まで）と進化カード、ライコウ（［いなびかり］）・スイクン（［クリスタルボディ］）・エンテイ
    # （［おたけび］）、メリープ → わるいモココ → わるいデンリュウ（［かんでん］）と、マチス（手札のたねポケモンをバトル場に出す。エンテイの［おたけび］の経路）
    "R86": (("neo2-049", 2), ("PF2-005", 1), ("PRN-024", 1), ("PMCG2-023", 2), ("PMCG2-026", 2), ("PMCG2-020", 2), ("neo3-029", 2), ("neo3-021", 2),
            ("neo3-010", 2), ("neo1-038", 4), ("neo4-044", 3), ("neo4-046", 2), ("PMCG5-092", 2), (WATER, 11), (LIGHTNING, 14), (FIRE, 8)),
    # v0.86: ラッキー → ハピナス（［タマゴうみ］）・ミニリュウ → ハクリュー → カイリュー（［いやしのかぜ］）・ズバット → わるいゴルバット → わるいクロバット（［とつぜんかみつく］）・
    # フシギダネ → フシギソウ → フシギバナ（［ソーラーパワー］）・エンテイ（［はしりさる］）と、ポケモン育て屋さん・エリカの香水（相手の手札のたねポケモンを相手の場に出させる）
    "D86": (("PMCG1-068", 3), ("neo3-052", 2), ("PMCG1-065", 3), ("PMCG1-069", 2), ("PR1-056", 2), ("neo3-001", 4), ("PMCG4-009", 3), ("neo4-012", 2),
            ("PMCG1-001", 3), ("PMCG1-008", 2), ("PR1-058", 2), ("PF2-008", 2), ("PMCG1-094", 2), ("PMCG5-073", 2), (GRASS, 18), (FIRE, 8)),
    # v0.87: クヌギダマ → フォレトス（［まきびし］・こうそくスピン）・マグマッグ → マグカルゴ（［やけのこり］）・わるいマグカルゴ（［ヒートプレート］）・カビゴン 2 枚（［とおせんぼ］・
    # ねころぶ）と、ポケモンいれかえ・突風（バトル場とベンチの移動）・ロケット団の爆発ジム（［ヒートプレート］と同じ時点）・鋼エネルギー（こうそくスピン）
    "M87": (("neo4-005", 4), ("neo2-044", 3), ("neo3-008", 4), ("neo3-009", 2), ("neo4-023", 2), ("ES1-034", 1), ("QSG-046", 1), (SWITCH, 3), (driver.GUST, 2),
            ("PMCG6-092", 1), ("neo1-095", 4), (FIRE, 21), ("PMCG1-096", 4), (WATER, 8)),
    # v0.87: マチスのビリリダマ → マチスのマルマイン（［ショックボム］）・ビードル → コクーン（［どくのたいえき］）・ドガース（［ぶんれつ］・ふしぎなガス）・コイル 2 枚（［マグネット］）・
    # フリーザー 2 枚（［オーロラヴェール］）・ディグダ → ダグトリオ（［もぐる］）・ゴース → ゴースト → ゲンガー（［やみのちから］）と、ポケモン育て屋さん
    "S87": (("PMCG5-038", 3), ("GD3-009", 2), ("PMCG1-004", 3), ("ES1-005", 2), ("ES2-003", 4), ("ES2-014", 2), ("QSG-023", 2), ("ES2-012", 1), ("QSG-057", 1),
            ("PMCG1-052", 3), ("PR1-046", 2), ("PMCG3-029", 3), ("PMCG3-030", 2), ("PR1-053", 2), ("PMCG1-094", 2), (LIGHTNING, 5), (GRASS, 5), (WATER, 6),
            (FIGHTING, 6), (PSYCHIC, 4)),
    # v0.88: チョンチー → ランターン（［すいりょくはつでん］・［せんすい］）・ポリゴン → ポリゴン2（［エナジーコンバーター］）・エリカのナゾノクサ（こうごうせい）・コイル → レアコイル
    # （［でんじりょく］・プラズマ）・わるいレアコイル（［でんじりょく］のつけ替えの相手）
    "C88": (("neo1-037", 4), ("neo1-040", 2), ("neo3-026", 2), ("PMCG1-064", 3), ("neo3-051", 2), ("GD4-001", 3), ("PMCG1-036", 4), ("neo3-045", 2),
            ("PMCG4-030", 1), (SWITCH, 2), (driver.BILL, 2), (LIGHTNING, 14), (WATER, 13), (GRASS, 6)),
    # v0.88: ヒトデマン → スターミー（コアストリーム）・ミュウ（レインボーウェーブ）・ホウオウ（レインボーバーン）・ポリゴン 2 種（テクスチャー2）・かっこいいポリゴン（テクスチャー
    # マジック）と、いろいろな色の基本エネルギー・無色2個エネルギー
    "R88": (("PMCG1-025", 4), ("neo3-034", 2), ("SI-004", 3), ("PF3-007", 2), ("ES1-033", 2), ("QSG-045", 2), ("PR1-023", 2), (SWITCH, 2), (driver.BILL, 2),
            (PSYCHIC, 10), (WATER, 10), (FIRE, 7), (LIGHTNING, 6), (GRASS, 2), ("PMCG1-096", 4)),
    # v0.89: 雷・水。ピカチュウ → ライチュウ 2 種（ろうでん）・コイル → レアコイル 2 種（マイクロウェーブ）・サンダー 3 種（ライトニングバーン・らくらい・サンダークラッシュ。同じ名前
    # 4 枚まで）・カスミのトサキント → カスミのアズマオウ（だくりゅう）
    "S89": (("PMCG1-035", 4), ("ES2-013", 2), ("QSG-022", 1), ("PMCG1-036", 4), ("ES2-015", 2), ("QSG-024", 1), ("PR1-070", 2), ("ES2-018", 1), ("QSG-056", 1),
            ("PMCG5-026", 4), ("GD2-011", 2), (SWITCH, 2), (driver.BILL, 2), (LIGHTNING, 20), (WATER, 12)),
    # v0.89: 闘・超・草。タケシのイシツブテ（ロングショット）・ワンリキー → ゴーリキー（きあいだま）・カラカラ（ほねをなげる）・ナツメのバリヤード（マジックダーツ）と、ナツメのESP・
    # タマタマ → ナッシー（ねらいだま）・お上品攻撃（選んだ相手の対戦ポケモンへのダメージの減らす量）
    "F89": (("GD1-007", 4), ("PMCG1-053", 4), ("ES3-028", 3), ("ES3-030", 4), ("GD6-011", 3), ("PMCG2-006", 3), ("SI-013", 2), (SABRINAS_ESP, 2), (CHARITY, 1),
            (driver.BILL, 2), (FIGHTING, 18), (PSYCHIC, 7), (GRASS, 7)),
    # v0.89: 悪・無色・水。イーブイ → ブラッキー（だましうち。悪エネルギー 4 枚）・なにかの化石 → わるいオムナイト（てっぽうみず）・ベロリンガ（きずをなめる・のびるベロ）・
    # ニャース（ねこパンチ）と、無色2個エネルギー
    "D89": (("PMCG2-037", 4), ("neo2-040", 3), (MYSTERIOUS_FOSSIL, 4), ("neo4-035", 3), ("SI-010", 3), ("PR1-057", 3), ("neo1-094", 2), ("PRN-002", 2),
            (DOUBLE_COLORLESS, 4), (driver.BILL, 2), (SWITCH, 2), (WATER, 28)),
    # v0.90: 草・闘。ベトベター（ベトベトえき・どくえき）・カラカラ（PR1-034。ほねさがし・ボーンキラー）→ ガラガラ（ES2-025。ほねさがし・ほねこんぼう）と、退化スプレー（進化・退化で
    # マーカー・カウンターを取りのぞく場面）
    "M90": (("ES2-002", 4), ("PR1-034", 4), ("ES2-025", 3), (DEVOLUTION_SPRAY, 2), (SWITCH, 2), (driver.BILL, 2), (GRASS, 20), (FIGHTING, 23)),
    # v0.90: 超・無・水。ミュウツー（ES3-026。かんぜんかいふく・サイコブラスト）・ルージュラ（あくまののろい・つららパンチ）・くいしんぼカビゴン（たべる・ころがる）・ドーブル（ペイント）と、
    # リサイクルエネルギー（かんぜんかいふくのトラッシュの共通の経路）・無色2個エネルギー
    "C90": (("ES3-026", 3), ("PR1-035", 3), ("PR1-024", 3), ("PRN-029", 3), (RECYCLE_ENERGY, 2), (DOUBLE_COLORLESS, 4), (SWITCH, 2), (driver.BILL, 2),
            (PSYCHIC, 22), (WATER, 16)),
    # v0.91: 炎・雷。ヒノアラシ（neo4-016。えんまく）→ マグマラシ（neo1-020。えんまく・やきこがす）・エレブー（ES2-017。ひらいしん・かみなりショック）と、退化スプレー（進化・退化で
    # くろこげマーカー・ひらいしんマーカーを取りのぞく場面）
    "K91": (("neo4-016", 4), ("neo1-020", 3), ("ES2-017", 4), (DEVOLUTION_SPRAY, 2), (SWITCH, 2), (driver.BILL, 2), (FIRE, 22), (LIGHTNING, 21)),
    # v0.91: 無色・水。ポリゴン（PRN-023。オールクリア・ハイパーテクスチャー）・ドーブル（PRN-029。ペイントで相手に色マーカー）と、場のトレーナーカード（プラスパワー・ディフェンダー・
    # せまいジム・きのみ）・無色2個エネルギー
    "P91": (("PRN-023", 4), ("PRN-029", 4), (driver.PLUSPOWER, 2), (driver.DEFENDER, 2), ("PMCG5-070", 2), ("neo1-073", 2), (SWITCH, 2), (driver.BILL, 2),
            (DOUBLE_COLORLESS, 4), (WATER, 36)),
    # v0.92: 草・闘。イトマル（neo1-004。こわいかお・いとをはく）→ アリアドス（neo1-011。クモのす・きゅうけつどく）・ズバット（neo3-001）→ ゴルバット（neo3-004。いやなおと・
    # きゅうけつどく）・イワーク（neo1-050。いやなおと・いかり）と、ポケモンいれかえ・突風（受けたポケモン・発生源をバトル場からはなす入れ替え）
    "S92": (("neo1-004", 4), ("neo1-011", 3), ("neo3-001", 4), ("neo3-004", 3), ("neo1-050", 3), (SWITCH, 2), (driver.GUST, 2), (driver.BILL, 2),
            (GRASS, 22), (FIGHTING, 15)),
    # v0.92: 超・悪。ナツメのゴース（GD6-006）→ ナツメのゴースト（GD6-007）→ ナツメのゲンガー（GD6-008。やみのはどう・かげしばり）・ヤミカラス（neo1-055。くろいまなざし・
    # だましうち）と悪エネルギー
    "G92": (("GD6-006", 4), ("GD6-007", 3), ("GD6-008", 2), ("neo1-055", 3), ("neo1-094", 4), (SWITCH, 2), (driver.BILL, 2), (PSYCHIC, 40)),
    # v0.92: 鋼・闘・草。ストライク（PMCG2-017）→ ハッサム（PRN-025。にらみつける・メタルニッパー）・ヨーギラス（neo4-073。にらみつける・いわおとし）と鋼エネルギー・突風
    "H92": (("PMCG2-017", 4), ("PRN-025", 3), ("neo4-073", 4), ("neo1-095", 4), (driver.GUST, 2), (SWITCH, 2), (driver.BILL, 2), (FIGHTING, 20), (GRASS, 19)),
    # v0.93: 草。キャタピー（ES1-002・QSG-002。からまるいと）・モンジャラ（ES2-004。からみつく）・ナゾノクサ（neo1-001）→ クサイハナ（neo1-008。へんなこな・ねばるみつ）・イトマル
    # （neo1-004）→ わるいアリアドス（neo4-011。からめとる・どくしばり）と、ポケモンいれかえ・突風・ポケモン回収（はなれられないポケモンの入れ替え・手札にもどす）
    "L93": (("ES1-002", 3), ("QSG-002", 1), ("ES2-004", 4), ("neo1-001", 4), ("neo1-008", 3), ("neo1-004", 4), ("neo4-011", 3), (SWITCH, 2), (driver.GUST, 2),
            ("PMCG1-092", 2), (driver.BILL, 2), (GRASS, 30)),
    # v0.93: 水。ワニノコ（neo1-024）→ アリゲイツ（neo1-030。いやなおと・くいつく）・ワニノコ（neo4-028）→ わるいアリゲイツ（neo4-036。かぶりつく）・ウリムー（neo1-027）→
    # イノムー（neo1-032。こおりつかせる・ふぶき）・テッポウオ（neo3-016）→ オクタン（neo3-019。からみつく・オクタンほう）と、突風（くいつくの発生源をはなす）
    "W93": (("neo1-024", 2), ("neo1-030", 3), ("neo4-028", 2), ("neo4-036", 3), ("neo1-027", 4), ("neo1-032", 3), ("neo3-016", 4), ("neo3-019", 3), (SWITCH, 2),
            (driver.GUST, 2), (driver.BILL, 2), (WATER, 30)),  # ワニノコは 2 つの版を合わせて 4 枚（同じ名前は 4 枚まで）
    # v0.93: 超・水・無色。タマタマ（PMCG2-006）→ ナッシー（PMCG2-012。テレポート）・ポッポ（PMCG1-059。ふきとばし）・カツラのポニータ（GD5-009。けりにげ）・メノクラゲ（PMCG3-011。
    # ［おくびょう］）と、ワープポイント・マチス・ポケモン回収（はなれられないポケモンの、ワザ・特殊能力・トレーナーでの移動の経路）
    "M93": (("PMCG2-006", 4), ("PMCG2-012", 3), ("PMCG1-059", 4), ("GD5-009", 4), ("PMCG3-011", 4), ("PMCG6-080", 2), ("PMCG5-092", 2), ("PMCG1-092", 2),
            (SWITCH, 2), (driver.BILL, 2), (PSYCHIC, 16), (WATER, 15)),
    # v0.94: 無色。ピッピ（ES1-026・QSG-040。このゆびとまれ・ひかるゆび）・プリン（SI-002。ひとみでさそう・うたう）・ブルー（neo1-061。ほえる・したでなめる）・トゲピー（PRN-033。
    # はしゃぐ）・ケンタロス（ES3-034。ふんだりけったり）と、ポケモンいれかえ・突風
    "C94": (("ES1-026", 3), ("QSG-040", 1), ("SI-002", 4), ("neo1-061", 4), ("PRN-033", 4), ("ES3-034", 4), (SWITCH, 2), (driver.GUST, 2), (driver.BILL, 2),
            (WATER, 17), (PSYCHIC, 17)),
    # v0.94: 草。コンパン（PMCG2-004）→ モルフォン（ES2-001。たつまきおこし・レインボーパウダー）・ナゾノクサ（neo1-001）→ クサイハナ（neo1-008）→ キレイハナ（PRN-043。フローラルスピン）と、
    # キャタピー（ES1-002。からまるいと。はなれられない効果との組み合わせ）
    "G94": (("PMCG2-004", 4), ("ES2-001", 3), ("neo1-001", 4), ("neo1-008", 3), ("PRN-043", 3), ("ES1-002", 3), (SWITCH, 2), (driver.GUST, 2), (driver.BILL, 2),
            (GRASS, 34)),
    # v0.94: 闘・炎。ゴマゾウ（neo4-072）→ ドンファン（neo1-054。じたばた・こうそくスピン）・わるいドンファン（neo4-078。すくいなげ・きょだいなキバ）・ワンリキー（PMCG1-053）→
    # ゴーリキー（PMCG1-055）→ カイリキー（PR1-052。いかりばくはつ・なげとばす）・ロコン（ES3-009・QSG-008。きつねび）
    "F94": (("neo4-072", 4), ("neo1-054", 3), ("neo4-078", 2), ("PMCG1-053", 4), ("PMCG1-055", 3), ("PR1-052", 2), ("ES3-009", 3), ("QSG-008", 1), (SWITCH, 2),
            (driver.GUST, 2), (driver.BILL, 2), (FIGHTING, 20), (FIRE, 12)),
    # v0.95: 超。ネイティ（neo1-046）→ ネイティオ（neo1-048。みらいよち・あやしいひかり）・ゴース（ES3-022・QSG-028）→ ゴースト（ES3-024・QSG-029。ポルターガイスト・ナイトメア）・
    # ナツメのケーシィ（GD6-002。とうし・クイックアタック）・ヤドン（neo1-045）→ わるいヤドキング（neo4-061。マインドショック・［わるぢえ］）と、相手が見て選ぶ・とりさるの対象の
    # トレーナー（ディフェンダー・プラスパワー・きずぐすり）
    "P95": (("neo1-046", 4), ("neo1-048", 3), ("ES3-022", 3), ("QSG-028", 1), ("ES3-024", 2), ("QSG-029", 1), ("GD6-002", 4), ("neo1-045", 4), ("neo4-061", 3),
            (driver.DEFENDER, 2), (driver.PLUSPOWER, 2), (driver.POTION, 2), (driver.BILL, 2), (PSYCHIC, 27)),
    # v0.95: 無色・鋼。ホーホー（neo1-060）→ ヨルノズク（neo1-065。つばさでうつ・［みやぶる］）・オタチ（neo2-046。さぐる・たいあたり）・エイパム（neo3-047。とりさる・しっぽでパンチ）・
    # ストライク（neo4-007）→ わるいハッサム（neo4-083。おどす・きりさく）と、ディフェンダー・プラスパワー
    "C95": (("neo1-060", 4), ("neo1-065", 3), ("neo2-046", 4), ("neo3-047", 4), ("neo4-007", 4), ("neo4-083", 3), (driver.DEFENDER, 2), (driver.PLUSPOWER, 2),
            (driver.POTION, 2), (SWITCH, 2), (driver.BILL, 2), (WATER, 28)),
    # v0.95: 炎・闘。ヒノアラシ（neo1-018）→ わるいマグマラシ（neo4-020。もやす・マグマラッシュ）・サイホーン（PMCG2-030）→ サイドン（ES3-031。やまくずし・にだんづき）・ワンリキー（PMCG1-053）と、
    # ポケモンタワー（やまくずしの手札に加える部分だけを消す）・ディフェンダー・プラスパワー
    "F95": (("neo1-018", 4), ("neo4-020", 3), ("PMCG2-030", 4), ("ES3-031", 3), ("PMCG1-053", 4), (V0_74_TOWER, 2), (driver.DEFENDER, 2), (driver.PLUSPOWER, 2),
            (driver.BILL, 2), (FIRE, 17), (FIGHTING, 17)),
    # v0.95: F95 の炎エネルギー 1 枚をレインボーエネルギーにした組（山札・サイドにあるあいだ、マグマラッシュ・やまくずしを FV1 で止める）
    "F95R": (("neo1-018", 4), ("neo4-020", 3), ("PMCG2-030", 4), ("ES3-031", 3), ("PMCG1-053", 4), (V0_74_TOWER, 2), (driver.DEFENDER, 2), (driver.PLUSPOWER, 2),
             (driver.BILL, 2), ("PMCG4-065", 1), (FIRE, 16), (FIGHTING, 17)),
    # v0.96: 超。アンノーン[E]（PF2-002。［ENGAGE］）2 枚・アンノーン[R]（PRN-035。［REASSURE］）2 枚（「アンノーン」は合わせて 4 枚まで）と遺跡の石版 2 種（neo2-054・neo2-057。
    # 山札から出すので手札からの機会はない）・ネイティ（neo1-046）→ ネイティオ（neo1-048）・ナツメのケーシィ（GD6-002）と、きずぐすり・ポケモンいれかえ
    "U96": (("PF2-002", 2), ("PRN-035", 2), ("neo2-054", 1), ("neo2-057", 1), ("neo1-046", 4), ("neo1-048", 2), ("GD6-002", 4),
            (driver.POTION, 2), (SWITCH, 2), (driver.BILL, 2), (PSYCHIC, 38)),
    # v0.96: 超。アンノーン[O]（PF2-003。［OBSERVE］）2 枚・アンノーンZ（neo4-060。［ZOOM］）2 枚と遺跡の石版 2 種・ヤドン（neo1-045）→ わるいヤドキング（neo4-061）・ナツメのケーシィ（GD6-002）と、
    # ふうせんのみ（［ZOOM］と本当のふうせんのみの重なり）・ポケモンいれかえ
    "Z96": (("PF2-003", 2), ("neo4-060", 2), ("neo2-054", 1), ("neo2-057", 1), ("neo1-045", 4), ("neo4-061", 2), ("GD6-002", 3), ("neo3-055", 2),
            (SWITCH, 2), (driver.BILL, 2), (PSYCHIC, 39)),
    # v0.96: 超。アンノーンL（neo4-050。［LAUGH］）・アンノーンS（neo4-051。［SEARCH］）・アンノーンT（neo4-052。［TELL］）・アンノーンZ（neo4-060）の 4 枚と遺跡の石版 2 種・ヤドン（neo1-045）→
    # わるいヤドキング（neo4-061）・ゴース（ES3-022）→ ゴースト（ES3-024）と、エリカの香水（相手の手札のアンノーン[E]・[R] を相手の番でないときに場に出させる）・ふうせんのみ（［ZOOM］と
    # 本当のふうせんのみの重なり）
    "L96": (("neo4-050", 1), ("neo4-051", 1), ("neo4-052", 1), ("neo4-060", 1), ("neo2-054", 1), ("neo2-057", 1), ("neo1-045", 4), ("neo4-061", 2), ("ES3-022", 3),
            ("ES3-024", 2), (ERIKAS_PERFUME, 2), ("neo3-055", 2), (SWITCH, 2), (driver.BILL, 2), (PSYCHIC, 35)),
    # v0.97: 超・無色。アンノーンF（neo2-026。［FIND］）・I（neo2-023。［INCREASE］）・[N]（PF2-001。［NORMAL df］）・D（neo2-025。［DARK df］）の 4 枚（「アンノーン」は合わせて 4 枚まで）と
    # 遺跡の石版 2 種。4 文字をベンチにそろえるためのバトル場の要員に、エリカのミニリュウ → エリカのハクリュー（無色。「ふぶき」の「うら」は自分の控え全員に 10。自分の［NORMAL df］が
    # 自分の控えのアンノーンを守る）・ヒノアラシ（PF1-004。スピードスター。相手のピジョンが受けて「オウムがえし」で出す手順の候補）と、きずぐすり・ポケモンいれかえ
    "F97": (("neo2-026", 1), ("neo2-023", 1), ("PF2-001", 1), ("neo2-025", 1), ("neo2-054", 1), ("neo2-057", 1), (ERIKAS_DRATINI, 4), (ERIKAS_DRAGONAIR, 3),
            ("PF1-004", 4), (driver.POTION, 2), (SWITCH, 2), (driver.BILL, 2), (PSYCHIC, 20), (FIRE, 17)),
    # v0.97: 超・無色。アンノーン[J]（PRN-034。［JOIN］）・[O]（PF2-003）・I・[N] の 4 枚と遺跡の石版 2 種。バトル場の要員にポッポ → ピジョン（無色。オウムがえし）・コラッタ（無色）と、
    # 突風（相手の控えのアンノーンをバトル場に出す）。炎エネルギーはピジョンが受けたスピードスターを出す支払いのため
    "J97": (("PRN-034", 1), ("PF2-003", 1), ("neo2-023", 1), ("PF2-001", 1), ("neo2-054", 1), ("neo2-057", 1), (PIDGEY, 4), (PIDGEOTTO, 3), ("PMCG1-060", 3),
            (driver.GUST, 2), (driver.POTION, 2), (SWITCH, 2), (driver.BILL, 2), (PSYCHIC, 18), (FIRE, 18)),
    # v0.97: 悪・無色（［DARK df］・［NORMAL df］の相手）。ヤミカラス（neo1-055。だましうちは選んだポケモンの持っている効果を除く）・イーブイ → ブラッキー（neo2-040。だましうちは FA1 の型）・
    # コラッタ（無色。かみつく）・R団のカビゴン（無色。［わるいねぞう］の特殊能力のダメージ）と、悪エネルギー（neo1-094）・突風
    "K97": (("neo1-055", 4), ("PMCG2-037", 4), ("neo2-040", 3), ("PMCG1-060", 4), ("PMCG6-073", 2), ("neo1-094", 4), (driver.GUST, 2), (driver.POTION, 2), (SWITCH, 2),
            (driver.BILL, 2), (WATER, 31)),
    # v0.98: 超・無色。アンノーンG（neo4-062。［GIVE］）・I（neo2-023）・V（neo4-053。［VANISH］）・[E]（PF2-002）の 4 枚（「アンノーン」は合わせて 4 枚まで。B・Y は入れない）と
    # 遺跡の石版 2 種。4 文字をベンチにそろえるためのバトル場の要員に、ポッポ → ピジョン・コラッタ（無色）。［GIVE］で山札からつける基本エネルギーを超・水の 2 色、［VANISH］で
    # トラッシュしてから手札にもどるリサイクルエネルギー 2 枚
    "G98": (("neo4-062", 1), ("neo2-023", 1), ("neo4-053", 1), ("PF2-002", 1), ("neo2-054", 1), ("neo2-057", 1), (PIDGEY, 4), (PIDGEOTTO, 3), ("PMCG1-060", 3),
            (RECYCLE_ENERGY, 2), (driver.POTION, 2), (SWITCH, 2), (driver.BILL, 2), (PSYCHIC, 18), (WATER, 18)),
    # v0.98: 超・無色。アンノーンB（neo3-032。［BEAR］）2 枚・アンノーンY（neo3-033。［YIELD］）2 枚（合わせて 4 枚）。バトル場の要員にエリカのミニリュウ → エリカのハクリュー（「ふぶき」の
    # 「うら」は自分の控え全員に 10。［BEAR］でのせ替えるカウンター）・コラッタと、山札のレインボーエネルギー 1 枚（［YIELD］の RB2。手札からつければ 10 ダメージ）・ミラクルエネルギー
    # 1 枚（山札では色がないので［YIELD］で選べない。止めない）
    "B98": (("neo3-032", 2), ("neo3-033", 2), (ERIKAS_DRATINI, 4), (ERIKAS_DRAGONAIR, 3), ("PMCG1-060", 3), (RAINBOW_ENERGY, 1), (MIRACLE_ENERGY, 1),
            (driver.POTION, 2), (SWITCH, 2), (driver.BILL, 2), (PSYCHIC, 20), (WATER, 18)),
    # v0.99: 超・無色。アンノーンH（neo4-063。［HELP］）・[E]（PF2-002）・L（neo4-050）・P（neo4-058）の 4 枚（「アンノーン」は合わせて 4 枚まで。I は入れない）と、山札から「アンノーン」を
    # ベンチに出す遺跡の石版 2 種 4 枚（4 文字をベンチにそろえる。E の［ENGAGE］は手札から出したときだけ）。バトル場の要員にポッポ → ピジョン・コラッタ（無色）。P がバトル場で
    # ワザを使うあいだは H の条件を満たさない（P がベンチにいない）
    "H99": ((UNOWN_H, 1), ("PF2-002", 1), ("neo4-050", 1), (UNOWN_P, 1), ("neo2-054", 2), ("neo2-057", 2), (PIDGEY, 4), (PIDGEOTTO, 3), ("PMCG1-060", 3),
            (driver.POTION, 2), (SWITCH, 2), (driver.BILL, 2), (PSYCHIC, 18), (WATER, 18)),
    # v0.99: 超・無色。アンノーンP（neo4-058。［PERFORM］）4 枚（合わせて 4 枚）。バトル場で相手のワザを受けて残った P が次の番に「めざめるパワー」を使う。控えの要員にポッポ →
    # ピジョン・コラッタ（入れ替え・にげるで、ベンチで受けた P をバトル場に出す場面もある）
    "P99": ((UNOWN_P, 4), (PIDGEY, 4), (PIDGEOTTO, 3), ("PMCG1-060", 3), (driver.POTION, 2), (SWITCH, 2), (driver.BILL, 2), (PSYCHIC, 22), (WATER, 18)),
    # v0.99: 水・無色。タッツー（neo1-023。「ひれがえし」水水・20+）4 枚と、相手と相手の控え全員に 10 を与えるタケシのズバット → タケシのゴルバット（かいてんひこう。相手の控えの P・
    # タッツーがベンチでだけ受ける場面）。受けたあとに使えるよう水エネルギーを多くする
    "T99": ((NEO_HORSEA, 4), (BROCKS_ZUBAT, 4), (BROCKS_GOLBAT, 3), (driver.POTION, 2), (SWITCH, 2), (driver.BILL, 2), (WATER, 43)),
    # v0.100: 無色。ドーブル（neo2-052。スケッチ 無無）4 枚と無色2個エネルギー 4 枚（出した番にも払える。前の相手の番に場にいなければ失敗する場面）。前の番に相手のワザを受ける要員と、
    # 相手のワザを自分のワザとして使うピッピ（ゆびをふる。スケッチで「まねたワザ」に当たる場面）・ポッポ → ピジョン（ふきとばし・オウムがえし）・コラッタ
    "S100": ((SMEARGLE, 4), (DOUBLE_COLORLESS, 4), ("PMCG1-060", 3), (PIDGEY, 3), (PIDGEOTTO, 2), (CLEFAIRY, 2), (driver.POTION, 2), (SWITCH, 2), (driver.BILL, 2),
             (WATER, 18), (PSYCHIC, 18)),
    # v0.100: 超・無色。ムウマ（neo3-035。やみのひとみ 超・ほろびのうた 超超超）4 枚と、第1弾のゴース（さいみんガス・みちづれ）・コラッタ。ほろびのうたのために超エネルギーを多くする。
    # ねむりは通常のポケモンチェックのコインのまま（使う回数を増やすために書きかえない）
    "M100": ((MISDREAVUS, 4), (GASTLY_BASE, 3), ("PMCG1-060", 3), (driver.POTION, 2), (SWITCH, 2), (driver.BILL, 2), (PSYCHIC, 30), (WATER, 14)),
    # v0.101: 超・無色。ソーナンス（neo2-031。カウンター 超・ダメージなし）4 枚と、ダメージを与える要員のポッポ → ピジョン・コラッタ（無色）。ソーナンスは払えればカウンターを使う
    "C101": ((WOBBUFFET, 4), (PIDGEY, 4), (PIDGEOTTO, 3), ("PMCG1-060", 3), (driver.POTION, 2), (SWITCH, 2), (driver.BILL, 2), (PSYCHIC, 40)),
    # v0.101: 超・無色。アンノーンK（neo3-030。［KEEP］）3 枚とアンノーンD（neo2-025。［DARK df］）1 枚（「アンノーン」は合わせて 4 枚まで）と、山札から「アンノーン」をベンチに出す
    # 遺跡の石版 2 種 4 枚。バトル場の要員にポッポ → ピジョン・コラッタ（無色。［KEEP］で守らない「アンノーン」でないポケモン）
    "K101": ((UNOWN_K, 3), (UNOWN_D, 1), ("neo2-054", 2), ("neo2-057", 2), (PIDGEY, 4), (PIDGEOTTO, 3), ("PMCG1-060", 3), (driver.POTION, 2), (SWITCH, 2),
             (driver.BILL, 2), (PSYCHIC, 36)),
    # v0.102: 草。トランセル（［グリーンシールド］・ふしぎなこな 草草）を ES1-003・QSG-003 で 2 枚ずつ、進化元は第1弾のキャタピー（PMCG1-002。商品をまたぐ名前の進化）。ほかの草ポケモンは
    # 第2弾のマダツボミ（炎が弱点。相手の炎のワザで［グリーンシールド］が弱点を当てはめない場面）
    "G102": ((BASE_CATERPIE, 4), (METAPOD_ES1, 2), (METAPOD_QSG, 2), (BASE_BELLSPROUT, 4), (driver.POTION, 2), (SWITCH, 2), (driver.BILL, 2), (GRASS, 42)),
    # v0.102: 超・無色。バリヤード（［ニュートラルダメージ］・ジャグリング 超無）を ES1-021・QSG-030 で 2 枚ずつ（「バリヤード」は合わせて 4 枚）。バトル場の要員は第1弾のスリープ
    # （超。超が弱点）とコラッタ（無色。超の抵抗力）。ベンチのバリヤードがお互いの対戦ポケモンの弱点・抵抗力を当てはめない場面
    "N102": ((MR_MIME_ES1, 2), (MR_MIME_QSG, 2), (BASE_DROWZEE, 4), ("PMCG1-060", 3), (driver.POTION, 2), (SWITCH, 2), (driver.BILL, 2), (PSYCHIC, 43)),
    # v0.103: 超・無色。ミュウ（［ニュートラルシールド］・ねんりき 超）を PR1-005・PR1-012 で 2 枚ずつ（「ミュウ」は合わせて 4 枚）。ほかのたねポケモンは第1弾のスリープ（超）・コラッタ（無色）。
    # 相手の進化ポケモンのワザ（返す効果を含む）をバトル場・ベンチで受けない場面と、たねポケモン・特殊能力・こんらんのダメージは受ける場面
    "M103": ((MEW_COROCORO, 2), (MEW_JR, 2), (BASE_DROWZEE, 4), ("PMCG1-060", 3), (driver.POTION, 2), (SWITCH, 2), (driver.BILL, 2), (PSYCHIC, 43)),
    # v0.104: 草・無色。ナゾノクサ → クサイハナ（neo1）→ キレイハナ（neo1-015。あまいみつ・フラワーダンス）3 枚と、名前の同じ別のカードのキレイハナ（PRN-043）1 枚（「キレイハナ」は合わせて
    # 4 枚。フラワーダンスで今の姿の名前で数える）、フシギダネ（ES1-001・QSG-001 を 1 枚ずつ・IP1-018 を 2 枚。合わせて 4 枚）、プリン（PR1-002・PR1-004 を 2 枚ずつ）、ミルタンク 4 枚
    "G104": ((NEO_ODDISH, 4), (NEO_GLOOM, 3), (BELLOSSOM, 3), (PRN_BELLOSSOM, 1), (BULBASAUR_ES1, 1), (BULBASAUR_QSG, 1), (BULBASAUR_IP1, 2), (JIGGLYPUFF_COROCORO, 2),
             (JIGGLYPUFF_BOOK, 2), (MILTANK, 4), (driver.POTION, 2), (SWITCH, 2), (driver.BILL, 2), (GRASS, 31)),
    # v0.104: 水・闘・無色。パウワウ（ES2-006）→ ジュゴン（ES2-007・QSG-018 を 2 枚ずつ。ねむる・オーロラウェーブ）、ラプラス（SI-018。やさしいうた・れいとうビーム）3 枚、ウリムー（neo3-038）→
    # イノムー（neo3-041。ひとやすみ・もうとっしん）3 枚、ヒメグマ（neo2-048。ひっかく・おひるね）4 枚
    "W104": ((SEEL_ES2, 4), (DEWGONG_ES2, 2), (DEWGONG_QSG, 2), (LAPRAS_SI, 3), (SWINUB_NEO3, 4), (PILOSWINE, 3), (TEDDIURSA, 4), (driver.POTION, 2), (SWITCH, 2),
             (driver.BILL, 2), (WATER, 16), (FIGHTING, 16)),
    # v0.105: 草。キャタピー（neo2-001）→ トランセル（neo2-006。かたくなる・からやぶりしんか）4 枚 → バタフリー（neo2-009。ミラクルりんぷん・ハイパーリバース）2 枚と、名前の同じ別のカードの
    # バタフリー（PMCG2-007）1 枚（山札から選べる進化カードが 2 種類）、ヒマナッツ（neo4-003。ころがる・ひざしをあびる）4 枚 → キマワリ（neo1-013）1 枚・やさしいキマワリ（neo4-004）1 枚、
    # セレビィ（PF3-002。サイコリーフ）3 枚。進化カードを少なくして、トランセル・ヒマナッツが場に残る（手札から進化させる元の手順のまま、山札から進化させるワザを使う場面と、山札に
    # 選べるカードがない場面が起こる）
    "B105": ((CATERPIE_NEO2, 4), (METAPOD_NEO2, 4), (BUTTERFREE_NEO2, 2), (BUTTERFREE_JUNGLE, 1), (SUNKERN_NEO4, 4), (SUNFLORA_NEO1, 1), (LIGHT_SUNFLORA, 1),
             (CELEBI_PF3, 3), (driver.POTION, 2), (SWITCH, 2), (driver.BILL, 2), (GRASS, 34)),
    # v0.105: 無色・水。デリバード（neo3-050。プレゼント 無無）4 枚と、無色2個エネルギー 4 枚（相手のハイパーリバース・サイコリーフで数えるエネルギーの個数がカードの枚数と違う場面）。
    # ほかはパウワウ（ES2-006）→ ジュゴン（ES2-007）、ミルタンク（neo1-069）、ラプラス（SI-018）（ダメージカウンターののったポケモンにプレゼントの回復が当たる場面）
    "D105": ((DELIBIRD_NEO3, 4), (SEEL_ES2, 3), (DEWGONG_ES2, 2), (MILTANK, 3), (LAPRAS_SI, 2), (DOUBLE_COLORLESS, 4), (driver.POTION, 2), (SWITCH, 2),
             (driver.BILL, 2), (WATER, 36)),
    # v0.106: 無色・水。ブルー（neo1-061）→ グランブル（neo1-068。たいあたり・いかりのとっしん）3 枚、カモネギ（neo3-046。かぜおこし・ネギでつく）4 枚、なにかの化石 → カブト →
    # カブトプス（neo2-018。きりさく・ハイドロカッター）2 枚。水エネルギー（カブトプスにつくエネルギーカードの枚数を増やす）と無色2個エネルギー（カード 1 枚で 2 個。ハイドロカッターで
    # 数えるのはカードの枚数）。たねポケモンを 12 枚にするコラッタ（PMCG1-060）4 枚（手札がなにかの化石だけの PF1・マリガンを減らす）
    "C106": ((SNUBBULL_NEO1, 4), (GRANBULL_NEO1, 3), (FARFETCHD_NEO3, 4), (RATTATA, 4), (MYSTERIOUS_FOSSIL, 2), (KABUTO, 2), (KABUTOPS_NEO2, 2), (driver.POTION, 2),
             (SWITCH, 2), (driver.BILL, 2), (FIGHTING, 10), (WATER, 19), (DOUBLE_COLORLESS, 4)),
    # v0.106: 闘。サンド（ES2-020・QSG-033）→ サンドパン（ES3-027・QSG-034 を 2 枚ずつ。すながくれ・ローリングニードル）、イシツブテ（ES1-023。たいあたり・かたくなる）4 枚と、
    # たねポケモンを 12 枚にするワンリキー（PMCG1-053）4 枚（マリガンを減らす）
    "F106": ((SANDSHREW_ES2, 2), (SANDSHREW_QSG, 2), (SANDSLASH_ES3, 2), (SANDSLASH_QSG, 2), (GEODUDE_ES1, 4), (BASE_MACHOP, 4), (driver.POTION, 2), (SWITCH, 2),
             (driver.BILL, 2), (FIGHTING, 38)),
    # v0.106: 雷・草・超。ビリリダマ（ES2-016・QSG-025 を 2 枚ずつ。でんきショック・みんなでスパーク）、ニドラン♀（ES1-006・QSG-004）→ ニドリーナ（ES3-002。なかまのちから・みだれ
    # ひっかき）3 枚と、ベンチに並ぶ名前の違うニドラン♂（ES1-007）→ ニドリーノ（ES3-003）→ ニドキング（PMCG1-013）、ゴース（ES3-022・QSG-028）→ ゴースト（ES3-023。ぶきみなひかり・
    # おんねん）3 枚、ストライク（neo2-008。れんぞくぎり）3 枚
    "E106": ((VOLTORB_ES2, 2), (VOLTORB_QSG, 2), (NIDORAN_F_ES1, 2), (NIDORAN_F_QSG, 2), (NIDORINA_ES3, 3), (NIDORAN_M_ES1, 3), (NIDORINO_ES3, 2), (NIDOKING, 1),
             (GASTLY_ES3, 2), (GASTLY_QSG, 2), (HAUNTER_ES3_GRUDGE, 3), (SCYTHER_NEO2, 3), (driver.POTION, 2), (SWITCH, 2), (driver.BILL, 2),
             (LIGHTNING, 9), (GRASS, 10), (PSYCHIC, 8)),
    # v0.107: 草。ビードル（neo2-002。とげでつつく）4 枚・クヌギダマ（neo2-005。とつぜんじばく）4 枚、キャタピー（ES1-002）→ トランセル（ES1-003）→ バタフリー（SI-003。そらをとぶ・
    # レインボーパウダー）3 枚。マリガン（両方の切り直しのあとの補償の停止）を減らすコラッタ（PMCG1-060）2 枚、無色2個エネルギー（そらをとぶの無色 3 個）
    "B107": ((WEEDLE_NEO2, 4), (PINECO_NEO2, 4), (CATERPIE_ES1, 4), (METAPOD_ES1, 3), (BUTTERFREE_SI, 3), (RATTATA, 2), (DOUBLE_COLORLESS, 2), (driver.POTION, 2),
             (SWITCH, 2), (driver.BILL, 2), (GRASS, 32)),
    # v0.107: 雷・無色。そらをとぶピカチュウ（PR1-018・PR1-063 を 2 枚ずつ。でんきショック・そらをとぶ。同じ名前は 4 枚まで）、ヒメグマ（neo2-048）→ リングマ（neo2-051。ヘッドプレス・
    # ダブルラリアット）3 枚、マリガンを減らすコラッタ（PMCG1-060）4 枚、無色2個エネルギー
    "E107": ((FLYING_PIKACHU_18, 2), (FLYING_PIKACHU_63, 2), (TEDDIURSA, 4), (URSARING_NEO2, 3), (RATTATA, 4), (DOUBLE_COLORLESS, 4), (driver.POTION, 2), (SWITCH, 2),
             (driver.BILL, 2), (LIGHTNING, 35)),
    # v0.107: 水・超・雷。コダック（neo4-026。みずかけ・へんずつう（超無））4 枚・カスミのシェルダー（GD2-006。たいあたり・からではさむ）4 枚・そらをとぶピカチュウ（PR1-042。でんげき・そらをとぶ）
    # 3 枚と、マリガンを減らすコラッタ 4 枚
    "W107": ((PSYDUCK_NEO4, 4), (MISTYS_SHELLDER, 4), (FLYING_PIKACHU_42, 3), (RATTATA, 4), (driver.POTION, 2), (SWITCH, 2), (driver.BILL, 2), (WATER, 23), (PSYCHIC, 8),
             (LIGHTNING, 8)),
    # v0.108: 悪・炎。デルビル（neo2-012。スモッグ・ほのおをまとう（炎）。悪エネルギーを使わないので、悪エネルギーは場にヘルガーがいるときヘルガーにつく）→ ヘルガー（neo2-041。かみくだく（悪無無）・
    # かえんほうしゃ（炎炎無））4 枚と、トゲピー（neo4-088。あまえる・とげたまタックル）4 枚。かみくだくの悪エネルギー（neo1-094。同じ名前は 4 枚まで）を引くためのマサキ 4 枚・無色2個
    # エネルギー 4 枚。たねポケモンを 12 枚にするコラッタ（PMCG1-060）4 枚（マリガンを減らす）
    "D108": ((HOUNDOUR_NEO2, 4), (HOUNDOOM_NEO2, 4), (TOGEPI_NEO4, 4), (RATTATA, 4), (DARKNESS_NEO1, 4), (DOUBLE_COLORLESS, 4), (driver.POTION, 2), (SWITCH, 2),
             (driver.BILL, 4), (FIRE, 28)),
    # v0.108: 雷・水・無色。チョンチー（neo3-024。プラスイオン（雷）・マイナスイオン（水））4 枚と、プリン（PMCG2-035。こもりうたでねむりにする）→ わるいプクリン（neo4-091。わるいうた・
    # たたきおこす）3 枚、コラッタ 4 枚、無色2個エネルギー
    "L108": ((CHINCHOU_NEO3, 4), (JIGGLYPUFF, 4), (DARK_WIGGLYTUFF, 3), (RATTATA, 4), (DOUBLE_COLORLESS, 4), (driver.POTION, 2), (SWITCH, 2), (driver.BILL, 2),
             (LIGHTNING, 19), (WATER, 16)),
    # v0.108: 草。アーボ（PMCG3-001・PMCG4-001 を 2 枚ずつ。どくえき・どくばりで相手をどくにする）→ アーボック（ES3-001。まきつく・もうどく）3 枚と、トゲピー 4 枚、コラッタ 4 枚
    "G108": ((FOSSIL_EKANS, 2), (ROCKET_EKANS, 2), (ARBOK_ES3, 3), (TOGEPI_NEO4, 4), (RATTATA, 4), (DOUBLE_COLORLESS, 2), (driver.POTION, 2), (SWITCH, 2),
             (driver.BILL, 2), (GRASS, 37)),
    # v0.109: 水・闘。ウパー（neo2-015。ぬるぬる（水）・しっぽでたたく（無無））4 枚とエビワラー（neo4-070。かわす（闘）・マッハストレート（闘闘闘））4 枚、マリガンを減らすコラッタ 4 枚。
    # 特殊エネルギーは入れない（支払いは state.energy_types で数えられる）
    "W109": ((WOOPER_NEO2, 4), (HITMONCHAN_NEO4, 4), (RATTATA, 4), (driver.POTION, 2), (SWITCH, 2), (driver.BILL, 2), (WATER, 21), (FIGHTING, 21)),
    # v0.109: 超。ケーシィ（PMCG1-043。ねんりき）→ ユンゲラー（ES3-019。サイコパニック（超超）・ブリンク（超超超））4 枚と、マリガンを減らすたねポケモンにスリープ（PMCG1-045。はたく・
    # あやしいひかり）4 枚・ゴース（neo4-048。あくむ）4 枚。たねポケモンもすべて「超」ポケモン（抵抗力 超 のコラッタを入れない）なので、同じデッキどうしではサイコパニックの基本となる
    # ダメージが 60 になる
    "P109": ((ABRA, 4), (KADABRA_ES3, 4), (DROWZEE, 4), (GASTLY_NEO4, 4), (driver.POTION, 2), (SWITCH, 2), (driver.BILL, 2), (PSYCHIC, 38)),
    # v0.110: 闘。ゴマゾウ（neo1-053。たいあたり（無）・こらえる（闘））4 枚と、エビワラー（neo4-070。かわす・マッハストレート）2 枚、マリガンと早いきぜつを減らすワンリキー（PMCG1-053）・
    # サンド（PMCG1-051）・コラッタ 4 枚ずつ。きあいのハチマキは入れない（「きぜつ」しない効果とハチマキの重なり（KS2）は、ハチマキのある相手のデッキ T81 との組で起こしうる）
    "F110": ((PHANPY_NEO1, 4), (HITMONCHAN_NEO4, 2), (BASE_MACHOP, 4), (SANDSHREW, 4), (RATTATA, 4), (driver.POTION, 2), (SWITCH, 2), (driver.BILL, 2), (FIGHTING, 36)),
    # v0.110: 草。クヌギダマ（neo4-005・neo2-005 を 2 枚ずつ）→ わるいフォレトス（neo4-008。こうてつか（無）・だいばくはつ（草草）60・自分にも 60）4 枚と、マリガンと早いきぜつを減らす
    # フシギダネ（PMCG1-001）・ナゾノクサ（PMCG2-002）・コラッタ 4 枚ずつ
    "G110": ((PINECO_NEO4, 2), (PINECO_NEO2, 2), (DARK_FORRETRESS, 4), (BULBASAUR, 4), (ODDISH, 4), (RATTATA, 4), (driver.POTION, 2), (SWITCH, 2), (driver.BILL, 2),
             (GRASS, 34)),
    # v0.111: 超。ミュウツー（ES1-022・QSG-032 を 2 枚ずつ。サイコクラッシュ（超）10×・ちょうねんりき（超超無）50）と、ナツメのケーシィ（GD6-001・PR1-060 を 2 枚ずつ。はたく（無）10・
    # シンクロウェーブ（超無）40）、マリガンを減らすスリープ（PMCG1-045）・ゴース（neo4-048）4 枚ずつ。無色2個エネルギー 2 枚（シンクロウェーブでは 1 枚と数える）。たねポケモンはすべて
    # 「超」ポケモン（同じデッキどうしではサイコクラッシュの数える「超」エネルギーカードが多い）
    "P111": ((MEWTWO_ES1, 2), (MEWTWO_QSG, 2), (SABRINAS_ABRA_GD6, 2), (SABRINAS_ABRA_PR1, 2), (DROWZEE, 4), (GASTLY_NEO4, 4), (DOUBLE_COLORLESS, 2), (driver.POTION, 2),
             (SWITCH, 2), (driver.BILL, 2), (PSYCHIC, 36)),
    # v0.112: 水。メノクラゲ（PMCG3-011）→ ドククラゲ（SI-016。しょくしゅをつかう（水）・どくばり（水水）20）4 枚と、マリガン・早い負けを減らすゼニガメ・ヒトデマン・コラッタ
    # 4 枚ずつ。無色2個エネルギー 2 枚（「水」エネルギーの個数に入らない）と、レインボーエネルギー 1 枚（しょくしゅをつかうの数える「水」が決まらない RB1 の境界）
    "T112": ((TENTACOOL, 4), (TENTACRUEL_SI, 4), (SQUIRTLE, 4), (STARYU, 4), (RATTATA, 4), (DOUBLE_COLORLESS, 2), (RAINBOW_ENERGY, 1), (driver.POTION, 2), (SWITCH, 2),
             (driver.BILL, 2), (WATER, 31)),
    # v0.112: 水。なにかの化石 → オムナイト（PMCG3-015）→ オムスター（PR1-051。しょくしゅをつかう（水）・ふしょくえき（水水水）40）を 4 枚ずつ（2 進化まで進めるため）と、マリガン・
    # 対戦準備のなにかの化石の止まり（PF1）・早い負けを減らすゼニガメ・ヒトデマン・コラッタ 4 枚ずつ
    "O112": ((MYSTERIOUS_FOSSIL, 4), (OMANYTE, 4), (OMASTAR_PR1, 4), (SQUIRTLE, 4), (STARYU, 4), (RATTATA, 4), (driver.POTION, 2), (SWITCH, 2), (driver.BILL, 2),
             (WATER, 30)),
    # v0.113: 無色。ピッピ（neo1-063。おうふくビンタ（無無）10×・みんなでおどる（無無無））とロケット団のニャース（PR1-078。だいぎゃくてん？（無））4 枚ずつと、お互いの場のポケモンの数を
    # 増やすコラッタ 4 枚。山札の基本エネルギーカード（水・闘）と、基本エネルギーカードでない無色2個エネルギー 3 枚（みんなでおどるで選べない）
    "P113": ((CLEFAIRY_NEO1, 4), (ROCKETS_MEOWTH_PR1, 4), (RATTATA, 4), (DOUBLE_COLORLESS, 3), (driver.POTION, 2), (SWITCH, 2), (driver.BILL, 2), (WATER, 22),
             (FIGHTING, 17)),
    # v0.113: 雷。メリープ → モココ → デンリュウ（neo3-028。ゆうでん（雷）20・ギガボルト（雷雷雷無）40+）を 4 枚ずつと、ゆうでんでつける先の「雷」ポケモンのピカチュウ 4 枚。山札の
    # レインボーエネルギー 1 枚（ゆうでんのカードの RB2。選べるが選ぶと止める）
    "L113": ((MAREEP_NEO1, 4), (FLAAFFY_NEO1, 4), (AMPHAROS_NEO3, 4), (PIKACHU, 4), (RAINBOW_ENERGY, 1), (driver.POTION, 2), (SWITCH, 2), (driver.BILL, 2),
             (LIGHTNING, 37)),
    # v0.113: 悪。ヤミカラス（neo3-043。なかまをよぶ（無）・むれでつつく（無無）10+）3 枚・ほかのヤミカラス（neo1-055）1 枚（同じ名前は 4 枚まで）と、デルビル → ヘルガー（neo3-044。
    # ダークフレイム（炎）20・くろいキバ（悪無無）30+）4 枚ずつ。悪エネルギー 3 種 4 枚（同じ名前は 4 枚まで。ダークフレイムでトラッシュからつける・くろいキバで数える）と炎（ダークフレイムで
    # トラッシュする）
    "D113": ((MURKROW_NEO3, 3), (MURKROW_NEO1, 1), (HOUNDOUR_NEO2, 4), (HOUNDOOM_NEO3, 4), (DARKNESS_NEO1, 2), (DARKNESS_PRN, 1), (DARKNESS_NIP2X, 1),
             (driver.POTION, 2), (SWITCH, 2), (driver.BILL, 2), (FIRE, 28), (WATER, 10)),
    # v0.113: 炎。ヒノアラシ → わるいマグマラシ → わるいバクフーン（neo4-022。つめできりさく（無）20・ファイヤーラッシュ（炎）40×）4 枚ずつと、ベンチで「炎」エネルギーカードを持つ
    # ヒトカゲ 4 枚（ファイヤーラッシュは自分の場全体からトラッシュする）。エコロジム 2 枚（自分のワザのトラッシュでは手札にもどさない）
    "T113": ((CYNDAQUIL_NEO4, 4), (DARK_QUILAVA_NEO4, 4), (DARK_TYPHLOSION_NEO4, 4), (CHARMANDER, 4), ("neo1-086", 2), (driver.POTION, 2), (SWITCH, 2),
             (driver.BILL, 2), (FIRE, 36)),
    # v0.114: 雷。ピチュー（neo1-042。パチパチ・PF2-007。いっしょにあそぼ）2 枚ずつ・エレキッド（neo1-044。［わんぱくパンチ］。ワザなし）4 枚と、進化先のピカチュウ（PMCG1-035）・
    # エレブー（PMCG1-041）4 枚ずつ。相手のサイコキッスで山札にもどる無色2個エネルギー 2 枚
    "L114": (("neo1-042", 2), ("PF2-007", 2), ("neo1-044", 4), (PIKACHU, 4), ("PMCG1-041", 4), (DOUBLE_COLORLESS, 2), (driver.POTION, 2), (SWITCH, 2),
             (driver.BILL, 2), (LIGHTNING, 36)),
    # v0.114: 無色。ピィ（neo1-070。ピピピ・PRN-012。ピッピッ）2 枚ずつ・ププリン（neo2-050。［じっとみる］。ワザなし・PRN-031。おやすみのうた）2 枚ずつと、進化先のピッピ（PMCG1-067）・
    # プリン（PMCG2-035）4 枚ずつ
    "C114": (("neo1-070", 2), ("PRN-012", 2), ("neo2-050", 2), ("PRN-031", 2), ("PMCG1-067", 4), ("PMCG2-035", 4), (DOUBLE_COLORLESS, 2), (driver.POTION, 2),
             (SWITCH, 2), (driver.BILL, 2), (WATER, 18), (FIGHTING, 18)),
    # v0.114: 炎・闘。ブビィ（neo1-022。モクモク・NIP1X-002。パンチ）2 枚ずつ・バルキー（neo2-033。スマッシュパンチ）4 枚と、進化先のブーバー（PMCG1-020）4 枚・エビワラー（PMCG1-058）・
    # サワムラー（PMCG3-039）2 枚ずつ
    "F114": (("neo1-022", 2), ("NIP1X-002", 2), ("neo2-033", 4), ("PMCG1-020", 4), ("PMCG1-058", 2), ("PMCG3-039", 2), (DOUBLE_COLORLESS, 2), (driver.POTION, 2),
             (SWITCH, 2), (driver.BILL, 2), (FIRE, 18), (FIGHTING, 18)),
    # v0.114: 超・水。ムチュール（neo3-031。サイコキッス・PRN-037（水）。なげキッス）2 枚ずつと、進化先のルージュラ（PMCG1-048）4 枚、ピチュー（NIP2X-002。はたく）2 枚・
    # ミュウ（PR1-005。［ニュートラルシールド］。相手のベイビィから進化したポケモンのワザを受けない）2 枚・コラッタ 4 枚
    "P114": (("neo3-031", 2), ("PRN-037", 2), ("PMCG1-048", 4), ("NIP2X-002", 2), ("PR1-005", 2), (RATTATA, 4), (DOUBLE_COLORLESS, 2), (driver.POTION, 2),
             (SWITCH, 2), (driver.BILL, 2), (PSYCHIC, 24), (WATER, 12)),
    # v0.115: 悪・闘。ヨーギラス（neo2-034）→ サナギラス（neo2-036。ロケットずつき・すなあらし）→ バンギラス（neo2-042。悪。たたきつける・なぎたおす）と、自分の控えのアンノーンD（neo2-025。
    # ［DARK df］。自分のなぎたおすのダメージも減らす。CR-UNOWN-DF-SOURCE-TYPE）・イシツブテ（neo3-037）→ ゴローン（neo3-039。じしん・がんせきおとし）・すなあらしを受ける闘でないコラッタ。
    # 2 進化に届くようにポケモン育て屋さん 2 枚。なぎたおすの悪 2 個のため、悪エネルギー 3 種 4 枚（同じ名前は 4 枚まで。第4弾のレインボーエネルギーは「悪」を出さないので入れない）を、
    # その系統に進化する前からつける（``_v115_energy``）。悪エネルギーを引くため、ビル 4 枚・オーキドはかせ 2 枚。たねポケモンは 10 枚
    "T115": (("neo2-034", 4), ("neo2-036", 3), ("neo2-042", 3), ("neo2-025", 2), ("neo3-037", 3), ("neo3-039", 3), (RATTATA, 1), (driver.POKEMON_BREEDER, 2),
             (DARKNESS_NEO1, 2), (DARKNESS_PRN, 1), (DARKNESS_NIP2X, 1), (driver.POTION, 1), (SWITCH, 1), (driver.BILL, 4), (driver.PROFESSOR_OAK, 2),
             (FIGHTING, 27)),
    # v0.115: 闘。ヨーギラス（neo4-073）→ わるいサナギラス（neo4-076。だんがんタックル・ばくれつしんか）→ わるいバンギラス（neo4-079。闘。やまくだき・ぶんなげる。ばくれつしんかで山札から
    # 重ねる）と、ワンリキー・コラッタ（控え）・ポケモン育て屋さん 2 枚。たねポケモンは 10 枚
    "D115": (("neo4-073", 4), ("neo4-076", 4), ("neo4-079", 3), ("PMCG1-053", 4), (RATTATA, 2), (driver.POKEMON_BREEDER, 2), (driver.POTION, 1), (SWITCH, 1),
             (driver.BILL, 2), (FIGHTING, 37)),
    # v0.115: 闘。イシツブテ（NIP1X-004。いしなだれ）4 枚 → ゴローン（ES3-029。がんせきくだき）4 枚 → ゴローニャ（PR1-054。ころがる・ロックブラスト）2 枚と、タケシのイワーク（GD1-010。
    # しめつける・ちていいどう）・ワンリキー・ポケモン育て屋さん 2 枚。たねポケモンは 9 枚
    "R115": (("NIP1X-004", 4), ("ES3-029", 4), ("PR1-054", 2), ("GD1-010", 3), ("PMCG1-053", 2), (driver.POKEMON_BREEDER, 2), (DOUBLE_COLORLESS, 2), (driver.POTION, 1),
             (SWITCH, 1), (driver.BILL, 2), (FIGHTING, 37)),
    # v0.115: 水・草。タッツー（ES3-015）→ シードラ（ES3-016。ウォーターボム。多い「水」エネルギーを相手の控えに配る）と、ヤンヤンマ（neo2-011。しょうげきは・スピードスター）・コラッタ。
    # たねポケモンは 11 枚
    "W115": (("ES3-015", 4), ("ES3-016", 3), ("neo2-011", 4), (RATTATA, 3), (driver.POTION, 1), (SWITCH, 1), (driver.BILL, 2), (WATER, 27), (GRASS, 15)),
    # v0.115: 超・雷。イーブイ（PMCG2-037）→ わるいエーフィ（neo4-067。つめをだす・サイコスプラッシュ）と、ピカチュウ（PMCG1-035）→ わるいライチュウ（neo2-021。びっくりサンダー）・コラッタ。
    # たねポケモンは 10 枚
    "E115": (("PMCG2-037", 4), ("neo4-067", 3), (PIKACHU, 4), ("neo2-021", 3), (RATTATA, 2), (DOUBLE_COLORLESS, 2), (driver.POTION, 1), (SWITCH, 1), (driver.BILL, 2),
             (PSYCHIC, 18), (LIGHTNING, 20)),
    # v0.116: 草・無色。ハネッコ（neo1-005。はねる・ふえる）4 枚、レディバ（neo1-003）→ レディアン（neo1-010。バトンタッチ。付け替える先の「草」の控えが多い）、マダツボミ（ES3-005）→
    # ウツドン（ES3-006。さいせい・ようかい）、ポッポ（ES1-024）→ ピジョン（ES3-032。ツイスター・そらをとぶ）。相手のエナジーショック・しこみどくの効果を受けたあとに手札からつける
    # なんでもなおし配合エネルギー 2 枚（同じ時点の反応の順番）・ツイスターでもどる自分のきあいのハチマキ・ディフェンダー 2 枚ずつ。たねポケモンは 15 枚
    "G116": (("neo1-005", 4), ("neo1-003", 4), ("neo1-010", 3), ("ES3-005", 4), ("ES3-006", 3), ("ES1-024", 3), ("ES3-032", 3), (FULL_HEAL_ENERGY, 2),
             ("neo1-088", 2), (driver.DEFENDER, 2), (SWITCH, 1), (driver.POTION, 1), (driver.BILL, 2), (GRASS, 26)),
    # v0.116: 水・草。ニョロモ（neo2-013）→ ニョロゾ（neo2-016。はらだいこ・みずでっぽう）、なにかの化石 → わるいオムナイト（neo4-035）→ わるいオムスター（neo4-038。げんしのしずく・
    # やみのしょくしゅ）、ズバット（neo3-001）→ ゴルバット（neo3-004）→ クロバット（neo3-006。しこみどく・クロスアタック）・コラッタ。なんでもなおし配合エネルギー 2 枚・レインボー
    # エネルギー 1 枚（エナジーコントロールの RB3）・ツイスターでもどるディフェンダー 2 枚。たねポケモンは 10 枚・なにかの化石は 3 枚（手札にたねポケモンがなく化石だけのときの対戦準備は PF1 で止まるので、たねポケモンを多く）
    "W116": (("neo2-013", 4), ("neo2-016", 3), (MYSTERIOUS_FOSSIL, 3), ("neo4-035", 3), ("neo4-038", 2), ("neo3-001", 4), ("neo3-004", 3), ("neo3-006", 2),
             (RATTATA, 2), (FULL_HEAL_ENERGY, 2), (RAINBOW_ENERGY, 1), (driver.DEFENDER, 2), (SWITCH, 1), (driver.POTION, 1), (driver.BILL, 2), (WATER, 15),
             (GRASS, 10)),
    # v0.116: 超。ネイティ（neo2-022）→ ネイティオ（neo2-024。エナジーサイクル・ちょうねんりき）、ゴース（neo4-048）→ わるいゴースト（neo4-055。よびもどす・とりかこむ）、ケーシィ → ユンゲラー
    # （ES3-020・QSG-027。エナジーさいせい・エナジーショック）→ フーディン（PR1-055。サイコパニック・トランスダメージ）、ミュウツー（PR1-022。エナジーコントロール・テレキネシス）。
    # エナジーさいせいで手札にもどす特殊エネルギーカード（ダブル無色エネルギー 3 枚・リサイクルエネルギー 2 枚）。フーディンに届くようにポケモン育て屋さん 2 枚・ツイスターでもどる
    # ディフェンダー 2 枚。たねポケモンは 14 枚
    "P116": (("neo2-022", 4), ("neo2-024", 3), (GASTLY_NEO4, 4), ("neo4-055", 3), ("QSG-026", 2), ("ES1-020", 2), ("ES3-020", 2), ("QSG-027", 2), ("PR1-055", 3),
             ("PR1-022", 2), (DOUBLE_COLORLESS, 3), (RECYCLE_ENERGY, 2), (driver.POKEMON_BREEDER, 2), (driver.DEFENDER, 2), (SWITCH, 1), (driver.POTION, 1),
             (driver.BILL, 2), (PSYCHIC, 20)),
    # v0.116: 草・超・無色。ズバット → ゴルバット → クロバット（しこみどく）・ポッポ（ES1-024）→ ピジョン（ES3-032）・ケーシィ → ユンゲラー（ES3-020。エナジーショック）・ミュウツー（PR1-022）。
    # 相手の場のエネルギーを動かすワザを受ける自分のなんでもなおし配合エネルギー 2 枚・きあいのハチマキ・ディフェンダー 2 枚ずつ。たねポケモンは 13 枚
    "C116": (("neo3-001", 4), ("neo3-004", 3), ("neo3-006", 2), ("ES1-024", 3), ("ES3-032", 2), ("QSG-026", 3), ("ES3-020", 3), ("PR1-022", 3),
             (FULL_HEAL_ENERGY, 2), ("neo1-088", 2), (DOUBLE_COLORLESS, 2), (driver.DEFENDER, 2), (SWITCH, 1), (driver.POTION, 1), (driver.BILL, 2), (GRASS, 14),
             (PSYCHIC, 11)),
    # v0.117: 超。アンノーンC（neo4-057。［CHASE］）・アンノーンQ（neo4-059。［QUICKEN］）2 枚ずつ（「アンノーン」はデッキに 4 枚まで）、セレビィ（neo3-036。サイキックダメージ・［ときわたり］）、
    # ナツメのゴース（GD6-005。したでなめる・ぱっときえる）とナツメのESP 2 枚（ナツメのゴースのしたでなめるのコイン）。たねポケモンは 12 枚
    "U117": (("neo4-057", 2), ("neo4-059", 2), ("neo3-036", 4), ("GD6-005", 4), (SABRINAS_ESP, 2), (SWITCH, 2), (driver.POTION, 2), (driver.BILL, 2), (driver.GUST, 2),
             (PSYCHIC, 38)),
    # v0.117: 悪・無色。イーブイ（PF2-005）→ ブラッキー（PF2-006。でんこうせっか・おいうち）、ヤミカラス（PRN-001。つつく・おいうち）、エイパム（neo1-067。もちさる・しっぽビンタ）、オドシシ
    # （neo3-049。いかく・うしろなげ）。おいうちの悪は悪エネルギー 4 枚（neo1-094・PRN-002。同じ名前 4 枚まで。第4弾のレインボーエネルギー 2 枚は「悪」を出さず、ほかの色）。たねポケモンは 14 枚
    "D117": (("PF2-005", 4), ("PF2-006", 3), ("PRN-001", 4), ("neo1-067", 3), ("neo3-049", 3), (DARKNESS_NEO1, 2), (DARKNESS_PRN, 2), (RAINBOW_ENERGY, 2),
             (DOUBLE_COLORLESS, 4), (SWITCH, 2), (driver.POTION, 1), (driver.BILL, 2), (driver.DEFENDER, 2), (WATER, 26)),
    # v0.117: 雷・炎・水。ライコウ（PF3-004）・エンテイ（PF3-005）・スイクン（PF3-006）3 枚ずつ（［でんせつのからだ］。にげるエネルギー 0）とエイパム 2 枚。自分の場のポケモンに使う
    # トレーナー（突風・ポケモンいれかえ・プラスパワー・ディフェンダー・きずぐすり・ポケモンセンター・エネルギー・リムーブ・なんでもなおし）。たねポケモンは 11 枚
    "L117": (("PF3-004", 3), ("PF3-005", 3), ("PF3-006", 3), ("neo1-067", 2), (driver.GUST, 2), (SWITCH, 2), (driver.PLUSPOWER, 2), (driver.DEFENDER, 2),
             (driver.POTION, 2), (POKEMON_CENTER, 1), (ENERGY_REMOVAL, 2), (FULL_HEAL, 1), (driver.BILL, 2), (LIGHTNING, 11), (FIRE, 11), (WATER, 11)),
    # v0.117: 草・水・無色。ヘラクロス（neo1-017。メガホーン・［きしかいせい］）、ニョロモ（neo2-013）→ ニョロゾ（neo2-016）→ ニョロトノ（neo2-019。おうふくビンタ・［かえるのうた］）と
    # ニョロトノに届くポケモン育て屋さん 2 枚、エイパム・オドシシ 2 枚ずつ。たねポケモンは 13 枚
    "N117": (("neo1-017", 3), ("neo2-013", 4), ("neo2-016", 3), ("neo2-019", 2), ("neo1-067", 2), ("neo3-049", 2), (DOUBLE_COLORLESS, 3), (SWITCH, 2),
             (driver.POTION, 2), (driver.BILL, 2), (driver.POKEMON_BREEDER, 2), (GRASS, 15), (WATER, 18)),
    # v0.118: 超・無色。アンノーンX（neo4-065。めざめるパワー・［XXXXX］）4 枚（「アンノーン」はデッキに 4 枚まで）、タマタマ（neo4-049）→ わるいナッシー（neo4-056。トリプルずつき・
    # わるわるMAX）、ルギア（PF3-008。エアロウイング）。たねポケモンは 10 枚
    "X118": (("neo4-065", 4), ("neo4-049", 4), ("neo4-056", 3), ("PF3-008", 2), (DOUBLE_COLORLESS, 3), (SWITCH, 2), (driver.POTION, 2), (driver.BILL, 2),
             (PSYCHIC, 38)),
    # v0.118: 草・無色。フシギダネ（PMCG1-001）→ フシギソウ（SI-008。ふしぎなかおり・はっぱカッター）、ナゾノクサ（neo1-001）→ クサイハナ（neo1-008）→ ラフレシア（SI-011。ごくらくかふん・
    # さいあくかふん）とラフレシアに届くポケモン育て屋さん 2 枚、ニャース（PR1-025。ひっかく・まるもうけ）。たねポケモンは 11 枚
    "G118": (("PMCG1-001", 4), ("SI-008", 3), ("neo1-001", 4), ("neo1-008", 3), ("SI-011", 2), ("PR1-025", 3), (driver.POKEMON_BREEDER, 2), (SWITCH, 1),
             (driver.BILL, 2), (GRASS, 36)),
    # v0.118: 水・無色。テッポウオ（neo4-030）→ わるいオクタン（neo4-037。スミでっぽう・しめつづける）、ミニリュウ（PMCG1-065）→ ハクリュー（PMCG1-069）→ カイリュー（PR1-043。マッハひこう・
    # ［トランスポート］）とカイリューに届くポケモン育て屋さん 2 枚、ニャース 2 枚。スミでっぽうの多いエネルギーに無色2個エネルギー。たねポケモンは 10 枚
    "W118": (("neo4-030", 4), ("neo4-037", 3), ("PMCG1-065", 4), ("PMCG1-069", 3), ("PR1-043", 2), ("PR1-025", 2), (DOUBLE_COLORLESS, 3),
             (driver.POKEMON_BREEDER, 2), (SWITCH, 2), (driver.BILL, 2), (WATER, 33)),
    # v0.118: 無色・超・水。ポリゴン（neo4-086）→ わるいポリゴン2（neo4-097。まるまるアタック・［じくうへんかん］）と、トラッシュにたまるスタジアム（せまいジム・ラッキースタジアム・
    # でこぼこジム 2 枚ずつ。同じ名前 4 枚まで）、ニャース 4 枚・ルギア 2 枚。たねポケモンは 10 枚
    "S118": (("neo4-086", 4), ("neo4-097", 3), ("PR1-025", 4), ("PF3-008", 2), (NARROW_GYM, 2), ("PRN-015", 2), ("neo4-110", 2), (DOUBLE_COLORLESS, 4),
             (driver.BILL, 2), (SWITCH, 1), (PSYCHIC, 17), (WATER, 17)),
    # v0.119: 草。ビードル（neo2-002）→ コクーン（neo2-007。どくをだす）、ドガース（PMCG1-006。くさいガス）→ マタドガス（ES3-007。ガスばくはつ・［ポイズンミスト］）、レディバ（neo4-002。
    # スピードスター）。たねポケモンは 10 枚。ツボツボ（どくどくエキス）は別のデッキに入れる（同じデッキで［ポイズンミスト］とかける数のどくが重なると PO1 で止まる局が多い。開発中の
    # seed 50・51 で確かめた）
    "P119": (("neo2-002", 4), ("neo2-007", 4), ("PMCG1-006", 4), ("ES3-007", 4), ("neo4-002", 2), (driver.POTION, 2), (driver.BILL, 2), (SWITCH, 2), (GRASS, 36)),
    # v0.119: 水・超。ワニノコ（neo4-028）→ わるいアリゲイツ（neo4-036）→ わるいオーダイル（neo4-039。はかいのいちげき・［いあつ］）、ゴース（neo4-048）→ わるいゴースト（neo4-055）→
    # わるいゲンガー（neo4-066。ひきずりこむ・［ふかいねむり］）と 2 進化に届くポケモン育て屋さん 2 枚、ムウマ（PRN-036。いたみわけ・あやしいひかり）。たねポケモンは 11 枚
    "D119": (("neo4-028", 4), ("neo4-036", 3), ("neo4-039", 2), ("neo4-048", 4), ("neo4-055", 3), ("neo4-066", 2), ("PRN-036", 3), (driver.POKEMON_BREEDER, 2),
             (driver.BILL, 2), (SWITCH, 1), (WATER, 17), (PSYCHIC, 17)),
    # v0.119: 水・草。カスミのシェルダー（GD2-006）→ カスミのパルシェン（GD2-007。トリプルキャノン・［シェルアーマー］）、ヒトデマン（ES3-017。なぞのこうせん・かいてんアタック）、パラス
    # （neo3-002）→ パラセクト（neo3-005。ねむりバサミ・［アレルギーほうし］）、ツボツボ（neo3-040。どくどくエキス・［かたいから］）。たねポケモンは 13 枚
    "W119": (("GD2-006", 4), ("GD2-007", 3), ("ES3-017", 3), ("neo3-002", 4), ("neo3-005", 3), ("neo3-040", 2), (DOUBLE_COLORLESS, 2), (driver.POTION, 2),
             (driver.BILL, 2), (SWITCH, 1), (WATER, 17), (GRASS, 17)),
    # v0.119: 草・無色。サカキのニドラン♂（PMCG6-004）→ サカキのニドリーノ（PMCG6-013）→ サカキのニドキング（PR1-068。じひびき・［めいれい］）と 2 進化に届くポケモン育て屋さん 4 枚、マサキ 4 枚・オーキドはかせ 2 枚・パソコン通信 2 枚・ポケモン交換おじさん 2 枚。
    # たねポケモンはサカキのニドラン♂ 4 枚だけ（［めいれい］を使う場面（バトル場のニドラン♂・ニドリーノと場のニドキング）が起こるように。最初のたねポケモンがバトル場に出る手順なので、
    # レディバ・ツボツボはこのデッキに入れない。開発中の seed 50〜52 で確かめた）
    "G119": (("PMCG6-004", 4), ("PMCG6-013", 4), ("PR1-068", 4), (driver.POKEMON_BREEDER, 4), (DOUBLE_COLORLESS, 4), (driver.BILL, 4),
             (driver.PROFESSOR_OAK, 2), (driver.COMPUTER_SEARCH, 2), (driver.POKEMON_TRADER, 2), (GRASS, 30)),
    # v0.120: 闘・水。カブト（neo2-014。ちからをあわせる・［なかまのふっかつ］）・オムナイト（neo2-032。しめつける・［かせきのふっかつ］）・プテラ（neo3-042。そらをとぶ・［げんしのきおく］）と、
    # たまごの化石 4 枚、復活したカブト・オムナイトから進化するカブトプス（neo2-018）・オムスター（neo2-035）。たねポケモンはウソッキー（PF3-001。たたきつける・［ものまね］）・ミュウ（PR1-021。
    # はたく・サイコデュープ）・タッツー（ES3-015）。なにかの化石は入れない（対戦準備の PF1 を避ける。化石の進化カードは復活の 3 つの経路だけで場に出す）
    "F120": (("PF3-001", 4), ("PR1-021", 3), ("ES3-015", 3), ("neo2-014", 4), ("neo2-032", 4), ("neo3-042", 3), ("neo2-018", 2), ("neo2-035", 2),
             ("neo2-055", 4), (driver.BILL, 4), (driver.POTION, 2), (SWITCH, 2), (FIGHTING, 11), (WATER, 9), (PSYCHIC, 3)),
    # v0.120: 無色・超・雷。トゲピー（PR1-065。なきつく・ゆびをふる）→ トゲチック（neo1-071。おおきくゆびをふる・そらをとぶ）、ミュウ（PR1-021）、ウソッキー（PF3-001）と、ピチュー（neo1-042）→
    # ピカチュウ（PMCG1-035）→ ライチュウ（PMCG1-038。ベイビィから進化したポケモン）。無色2個エネルギー 4 枚
    "T120": (("PR1-065", 4), ("neo1-071", 3), ("PR1-021", 3), ("PF3-001", 2), ("neo1-042", 2), ("PMCG1-035", 3), ("PMCG1-038", 2), (DOUBLE_COLORLESS, 4),
             (driver.BILL, 4), (driver.POTION, 2), (SWITCH, 2), (PSYCHIC, 10), (LIGHTNING, 10), (FIGHTING, 9)),
    # v0.120: 超・水。スリープ（PMCG1-045）→ スリーパー（ES3-025。マインドショック・［にんぎょうつかい］）とピッピ人形 2 枚、タッツー（ES3-015）→ シードラ（ES3-016）→ キングドラ（neo3-020。
    # りゅうのいでんし・たつまき）と 2 進化に届くポケモン育て屋さん 2 枚、ミュウ（PR1-021）。ピッピ人形があるので、対戦準備の PF1 で止まる局がありうる（既知の停止）
    "S120": (("PMCG1-045", 4), ("ES3-025", 3), (CLEFAIRY_DOLL, 2), ("ES3-015", 4), ("ES3-016", 3), ("neo3-020", 2), ("PR1-021", 2), (driver.POKEMON_BREEDER, 2),
             (driver.BILL, 4), (driver.POTION, 2), (SWITCH, 2), (PSYCHIC, 14), (WATER, 16)),
    # v0.120: 草。ハネッコ（neo1-005・neo2-004）→ ポポッコ（neo1-012・neo3-003）→ ワタッコ（neo3-007。しんかのほうし・ソーラービーム）と、ピカチュウ（PMCG1-035）
    "J120": (("neo1-005", 3), ("neo2-004", 1), ("neo1-012", 2), ("neo3-003", 2), ("neo3-007", 3), ("PMCG1-035", 2), (driver.BILL, 4), (driver.POTION, 2), (SWITCH, 2),
             (GRASS, 32), (LIGHTNING, 7)),
    # v0.121: 雷。コイル（neo2-043。ロックオン・でんじほう）とピカチュウ 3 枚（PR1-001・PR1-003・PR1-017 を 1 枚ずつ。なきごえは最新の説明）・ピカチュウ IP1-040（同じ名前は 4 枚まで）、ビリリダマ（PMCG1-037）、ボロのつりざお 2 枚
    "C121": (("neo2-043", 4), ("PR1-001", 1), ("PR1-003", 1), ("PR1-017", 1), ("IP1-040", 1), ("neo3-053", 2), ("PMCG1-037", 4), (driver.BILL, 4), (driver.POTION, 2), (SWITCH, 2),
             (LIGHTNING, 28), (WATER, 10)),
    # v0.121: 炎・悪。デルビル（neo2-012）→ わるいヘルガー（neo4-229。ぶきみなとおぼえ・じごくのほのお）と悪エネルギー 4 枚、ガーディ（PMCG1-018）・ポニータ（PMCG1-016）、ボロのつりざお 2 枚
    "H121": (("neo2-012", 4), ("neo4-229", 3), ("PMCG1-018", 3), ("PMCG1-016", 4), ("neo3-053", 2), (DARKNESS_NEO1, 4), (driver.BILL, 4), (driver.POTION, 2), (SWITCH, 2),
             (FIRE, 22), (WATER, 10)),
    # v0.121: 無色・水。ヒメグマ（neo2-048）→ わるいリングマ（neo4-096。ちょうはつ・だいらんとう）、ラプラス（PMCG3-022）とカスミのてあて 3 枚、コラッタ（PMCG1-060）、無色2個エネルギー 4 枚
    "U121": (("neo2-048", 4), ("neo4-096", 3), ("PMCG3-022", 3), ("PMCG1-060", 4), ("PR1-073", 3), (DOUBLE_COLORLESS, 4), (driver.BILL, 4), (driver.POTION, 2), (SWITCH, 2),
             (WATER, 21), (FIGHTING, 10)),
    # v0.121: 超。ヤドン（PMCG3-027）→ ヤドラン（ES3-021。おおあくび・おおいびき）、スリープ（PMCG1-045）・ケーシィ（PMCG1-043）
    "Y121": (("PMCG3-027", 4), ("ES3-021", 3), ("PMCG1-045", 3), ("PMCG1-043", 4), (driver.BILL, 4), (driver.POTION, 2), (SWITCH, 2), (PSYCHIC, 28), (WATER, 10)),
    # v0.122: 超。アンノーン 4 枚（[N] PF2-001・A neo2-030・X neo4-065・M neo2-027。文字を問わず合わせて 4 枚）と遺跡の石版 2 枚、ケーシィ（PMCG1-043）・スリープ（PMCG1-045）。［ANGER］と［XXXXX］の
    # いっしょの宣言・［METAL df］
    "A122": (("PF2-001", 1), ("neo2-030", 1), ("neo4-065", 1), ("neo2-027", 1), ("neo2-054", 1), ("neo2-057", 1), ("PMCG1-043", 4), ("PMCG1-045", 4),
             (driver.BILL, 4), (driver.POTION, 2), (SWITCH, 2), (PSYCHIC, 28), (WATER, 10)),
    # v0.122: 超。アンノーン 4 枚（U neo2-028・[N] PF2-001・D neo2-025・[O] PF2-003）と遺跡の石版 4 枚（ベンチに文字をそろえる）、ケーシィ・スリープ。［UNDO］
    "U122": (("neo2-028", 1), ("PF2-001", 1), ("neo2-025", 1), ("PF2-003", 1), ("neo2-054", 2), ("neo2-057", 2), ("PMCG1-043", 4), ("PMCG1-045", 4),
             (driver.BILL, 4), (driver.POTION, 2), (SWITCH, 2), (PSYCHIC, 26), (WATER, 10)),
    # v0.122: 超。アンノーン 4 枚（W neo4-064・A neo2-030・[N] PF2-001・T neo4-052）と遺跡の石版 4 枚、ケーシィ・スリープ。トラッシュのトレーナーを［WANT］で回収する
    "W122": (("neo4-064", 1), ("neo2-030", 1), ("PF2-001", 1), ("neo4-052", 1), ("neo2-054", 2), ("neo2-057", 2), ("PMCG1-043", 4), ("PMCG1-045", 4),
             (driver.BILL, 4), (driver.POTION, 2), (SWITCH, 2), (PSYCHIC, 26), (WATER, 10)),
    # v0.122: 水・闘。なにかの化石 4 枚 → オムナイト（ES2-011［げんしのゆめ］・ES3-018［かせきのみちびき］）・カブト（ES2-028［かせきか］）→ カブトプス（neo2-018）・プテラ（ES2-029）と化石の発掘 2 枚
    "F122": ((MYSTERIOUS_FOSSIL, 4), ("ES2-011", 2), ("ES3-018", 2), ("ES2-028", 3), ("neo2-018", 2), ("ES2-029", 2), ("ES1-035", 2), (JUNGLE_MANKEY, 4),
             (driver.BILL, 4), (driver.POTION, 2), (SWITCH, 2), (WATER, 15), (FIGHTING, 16)),
    # v0.122: 草・闘。フシギダネ（PMCG1-001）→ わるいフシギソウ（PRN-039。みだれうち・［つるでひっぱる］）→ わるいフシギバナ（PRN-040。いやなかふん）、カポエラー（PRN-030）
    "B122": (("PMCG1-001", 4), ("PRN-039", 3), ("PRN-040", 2), ("PRN-030", 3), (driver.BILL, 4), (driver.POTION, 2), (SWITCH, 2), (GRASS, 26), (FIGHTING, 14)),
    # v0.122: 雷・無色。マチスのピカチュウ（GD3-001）→ マチスのライチュウ（GD3-003。メガトンパンチ・10まんボルト）、オニスズメ（PMCG2-034）→ わるいオニドリル（PRN-045。たかくとぶ・ドリルダイブ）
    "L122": (("GD3-001", 4), ("GD3-003", 3), ("PMCG2-034", 4), ("PRN-045", 3), (driver.BILL, 4), (driver.POTION, 2), (SWITCH, 2), (DOUBLE_COLORLESS, 2), (LIGHTNING, 36)),
    # v0.123: 炎。ガーディ（PMCG1-018）→ ウィンディ 4 枚（プロモ PR1-016 2 枚・イントロパック IP2-032 1 枚・第1弾 PMCG1-019 1 枚。印刷の名前が同じ「ウィンディ」なので合わせて 4 枚まで）、
    # ポニータ（PMCG1-016）
    "W123": ((GROWLITHE, 4), ("PR1-016", 2), ("IP2-032", 1), (ARCANINE, 1), ("PMCG1-016", 4), (driver.BILL, 4), (driver.POTION, 2), (SWITCH, 2), (FIRE, 40)),
    # v0.123: 炎。カツラのガーディ 4 枚（PMCG6-027 2 枚・GD5-005 2 枚）→ カツラのウィンディ 4 枚（ポケモンジム第3弾 GD5-007 2 枚・闇からの挑戦 PMCG6-034 2 枚。「カツラのウィンディ」で
    # 合わせて 4 枚まで。「ウィンディ」とは別の名前）、カツラのヒトカゲ（PMCG6-025）→ カツラのリザード（PMCG6-029）
    "K123": ((BLAINES_GROWLITHE, 2), ("GD5-005", 2), ("GD5-007", 2), (BLAINES_ARCANINE, 2), (BLAINES_CHARMANDER, 4), (BLAINES_CHARMELEON, 2),
             (driver.BILL, 4), (driver.POTION, 2), (SWITCH, 2), (FIRE, 38)),
    # v0.124: 水・超。メタモン 4 枚（拡張シート第2弾赤版 ES2-032 2 枚・化石の秘密 PMCG3-042 2 枚。印刷の名前が同じ「メタモン」なので合わせて 4 枚まで）、ラプラス、ヒトデマン（PMCG1-025）
    "S124": ((V124_SUPER_DITTO, 2), (DITTO, 2), (LAPRAS, 3), (STARYU, 4), (driver.BILL, 4), (driver.POTION, 2), (SWITCH, 2), (WATER, 37), (PSYCHIC, 4)),
    # v0.124: 超・炎。GR団のミュウツー 3 枚と「わるい」ポケモン（ロケット団のポニータ → わるいギャロップ、イーブイ → わるいブースター）
    "G124": ((V124_GR_MEWTWO, 3), (ROCKET_PONYTA, 4), (DARK_RAPIDASH, 3), (EEVEE, 3), (DARK_FLAREON, 2), (driver.BILL, 4), (driver.POTION, 2), (SWITCH, 2),
             (FIRE, 21), (PSYCHIC, 16)),
    # v0.125: 無色。プリン（PMCG2-035。こもりうた・はたく）→ プクリン（ES1-027。［てだすけ］・ふくらむ）4 枚と、ラッキー（PMCG1-068）。無色2個エネルギーと超エネルギー。
    # ベンチのプクリンが、相手のワザで特殊状態になった自分の対戦ポケモンを［てだすけ］で回復する
    "W125": ((JIGGLYPUFF, 4), (V125_WIGGLYTUFF, 4), (CHANSEY, 3), (driver.BILL, 4), (driver.POTION, 2), (SWITCH, 2), (DOUBLE_COLORLESS, 4), (PSYCHIC, 37)),
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
# v0.83: S83 対 G83（おたがいのプレイヤーが選ぶワザ・ひかるポケモン）・S83 対 E82（リサイクルエネルギー・エコロジムの場でひかるポケモン）・G83 対 P31
PAIRINGS_V0_83 = (("S83", "G83"), ("S83", "E82"), ("G83", "P31"))
# v0.84: G84 対 W84（やさしいポケモンどうし・［きせきのかぜ］）・W84 対 E82（リサイクルエネルギー・エコロジムの場で［きせきのかぜ］）・G84 対 P31
PAIRINGS_V0_84 = (("G84", "W84"), ("W84", "E82"), ("G84", "P31"))
# v0.85: M85 対 F85（進化したときの特殊能力・エネルギーを動かす特殊能力どうし）・L85 対 M85（［きせきのかぜ］とミラクルエネルギー・［おいしげる］）・F85 対 W84（W84 の
# ［きせきのかぜ］の場で［あばれんぼう］・［どしゃぶり］）・L85 対 E82（エコロジムの場でミラクルエネルギー・特殊エネルギー）
PAIRINGS_V0_85 = (("M85", "F85"), ("L85", "M85"), ("F85", "W84"), ("L85", "E82"))
# v0.86: R86 対 D86（手札からつけたエネルギー・進化・場に出したときの反応どうし。エリカの香水で相手の場に出させるエンテイ）・R86 対 F85（F85 の［あばれんぼう］・育て屋さんの場で
# ［かんでん］・［いなびかり］）・D86 対 P31
PAIRINGS_V0_86 = (("R86", "D86"), ("R86", "F85"), ("D86", "P31"))
PAIRINGS_V0_87 = (("M87", "S87"), ("M87", "R86"), ("S87", "P31"))
# v0.88: C88 対 R88（色を変える効果と、色を選ぶ・数えるワザ）・C88 対 S87（S87 のかがくへんかガスのない場・［ショックボム］の場で［せんすい］・［エナジーコンバーター］）・R88 対 P31
PAIRINGS_V0_88 = (("C88", "R88"), ("C88", "S87"), ("R88", "P31"))
# v0.89: S89 対 F89・D89 対 S89・F89 対 D89（選ぶダメージどうし）・F89 対 R65（R65 のタケシのサイドン［ベンチガード］の場で、選んだ控えへのダメージ）
PAIRINGS_V0_89 = (("S89", "F89"), ("D89", "S89"), ("F89", "D89"), ("F89", "R65"))
# v0.90: M90 対 C90（ベトベトマーカー・のろいマーカー（ベトベターは超の弱点）・色マーカーとカウンター）・C90 対 C88（C88 のランターン［せんすい］・ポリゴン2 の場で色マーカー）・
# M90 対 C88（ベトベトマーカーとチョンチー → ランターンの進化・［でんじりょく］の場）
PAIRINGS_V0_90 = (("M90", "C90"), ("C90", "C88"), ("M90", "C88"))
# v0.91: K91 対 P91（くろこげマーカー・ひらいしんマーカーとオールクリア・場のトレーナー）・K91 対 C88（C88 の色を変える特殊能力・かがくへんかガスのない場のポケモンチェック）・
# P91 対 C90（C90 のペイント・のろいマーカー・たべものカウンターとオールクリア・ハイパーテクスチャー）
PAIRINGS_V0_91 = (("K91", "P91"), ("K91", "C88"), ("P91", "C90"))
# v0.92: S92 対 G92（クモのす・くろいまなざしと入れ替え、きゅうけつどく・いやなおととやみのはどう）・G92 対 H92（やみのはどうとヨーギラス・ハッサムのにらみつけるの発生源を突風で
# はなす場面、メタルニッパー）・H92 対 S92（突風で受けたポケモン・発生源をはなす・こわいかお）・G92 対 C88（C88 の色を変える特殊能力とやみのはどうの抑止）
PAIRINGS_V0_92 = (("S92", "G92"), ("G92", "H92"), ("H92", "S92"), ("G92", "C88"))
# v0.93: L93 対 W93（はなれられない効果どうし・くいつくの発生源の突風・かぶりつくのコイン・こおりつかせる）・W93 対 M93（くいつく・こおりつかせる・オクタンほうと、テレポート・
# ふきとばし・けりにげ・おくびょう・ワープポイント・マチス）・M93 対 L93（からまるいと・ねばるみつ・どくしばり・からめとると、同じ移動の経路）
PAIRINGS_V0_93 = (("L93", "W93"), ("W93", "M93"), ("M93", "L93"))
# v0.94: C94 対 G94（このゆびとまれ・ひとみでさそう・ほえる・はしゃぐ・ふんだりけったりと、たつまきおこし・フローラルスピン）・G94 対 F94（こうそくスピン・すくいなげ・なげとばす・きつねびと、
# からまるいとのはなれられない効果）・F94 対 C94（相手の入れ替え・帰還と自分の入れ替え）・F94 対 L93（v0.93 のはなれられない効果を受けた側の、片側だけの入れ替え・コインの AL2）
PAIRINGS_V0_94 = (("C94", "G94"), ("G94", "F94"), ("F94", "C94"), ("F94", "L93"))
# v0.95: P95 対 C95（見る・山札にもどす・ポルターガイストと［みやぶる］・おどす・とりさる）・C95 対 F95（相手の手札・場のトレーナーと、もやす・マグマラッシュ・やまくずし）・F95 対 P95
# （山札のトラッシュ・ポケモンタワーと、みらいよち・［わるぢえ］）・F95R 対 C95（山札・サイドのレインボーエネルギーでマグマラッシュ・やまくずしを止める FV1）
PAIRINGS_V0_95 = (("P95", "C95"), ("C95", "F95"), ("F95", "P95"), ("F95R", "C95"))
# v0.96: U96 対 L96（アンノーンどうし。エリカの香水で相手の手札のアンノーン[E]・[R] を出させる）・Z96 対 U96（［OBSERVE］・［ZOOM］と［ENGAGE］・［REASSURE］）・L96 対 P95・
# Z96 対 C95（v0.95 の組を相手にする）。組・席・seed は先に決めた（seed 0〜7。局を選び直さない）
PAIRINGS_V0_96 = (("U96", "L96"), ("Z96", "U96"), ("L96", "P95"), ("Z96", "C95"))
# v0.97: F97 対 K97・J97 対 K97（［DARK df］・［NORMAL df］と悪・無色のワザ）・F97 対 J97（［FIND］・［JOIN］・［INCREASE］のアンノーンどうし。無色のピジョン・コラッタのワザ）・J97 対 U96
# （v0.96 の組を相手にする）。組・席・seed は先に決めた（seed 0〜3。局を選び直さない）
PAIRINGS_V0_97 = (("F97", "K97"), ("J97", "K97"), ("F97", "J97"), ("J97", "U96"))
# v0.98: G98 対 K97・B98 対 K97（相手の悪・無色のワザでアンノーンにのるカウンター）・G98 対 B98（アンノーンどうし）・B98 対 F97（v0.97 の組を相手にする）。組・席・seed は先に決めた
# （seed 0〜3。局を選び直さない）
PAIRINGS_V0_98 = (("G98", "K97"), ("B98", "K97"), ("G98", "B98"), ("B98", "F97"))
# v0.99: P99 対 T99（P とタッツーがおたがいのワザを受けてから使う。かいてんひこうのベンチのダメージ）・H99 対 T99（［HELP］の 4 文字と、タッツーのワザ）・H99 対 P99（アンノーンどうし）・
# T99 対 K97（v0.97 の組の悪・無色のワザを受けたタッツー）。組・席・seed は先に決めた（seed 0〜3。局を選び直さない）
PAIRINGS_V0_99 = (("P99", "T99"), ("H99", "T99"), ("H99", "P99"), ("T99", "K97"))
# v0.100: S100 対 M100（スケッチでやみのひとみ・ほろびのうたを使う・ドーブルがねむる）・S100 対 H62（ハリケーン・ふきとばし・オウムがえしの v0.62 の組。手札にもどされたドーブル・まねるワザ）・
# M100 対 G61（わるいギャラドスの［ファイナルビーム］）・M100 対 V44（サカキのカイリキーの［こんじょう］）・M100 対 T74（R団のファイヤーの「ふしちょう」・ゴーストの「とうめい」）・
# S100 対 P31（ピッピ・ピクシーの「ゆびをふる」・ヤドンの「ぼーっとする」）。組・席・seed は先に決めた（seed 0〜3。局を選び直さない）
PAIRINGS_V0_100 = (("S100", "M100"), ("S100", "H62"), ("M100", "G61"), ("M100", "V44"), ("M100", "T74"), ("S100", "P31"))
# v0.101: K101 対 W33（はかいこうせん・うずしお。コインのない相手のワザのトラッシュ）・K101 対 C33（はかいでんぱのコイン・ハクリューのはかいこうせん）・K101 対 R45（メラメラの一部だけ
# なくなるトラッシュ・じりょくせん）・K101 対 U55（エネルギー・リムーブ・超エネルギーリムーブ）・K101 対 K68（キョウのベトベトンの［だつりょくえき］）・K101 対 L82（ヌオーのうずしお・
# エコロジム・リサイクルエネルギー）・C101 対 K101（新しいカードどうし）・C101 対 P31（ゆびをふるで写すカウンター・スーパーデストロイ）・C101 対 S100（スケッチで写すカウンター）。
# 組・席・seed は先に決めた（seed 0〜3。局を選び直さない）
PAIRINGS_V0_101 = (("K101", "W33"), ("K101", "C33"), ("K101", "R45"), ("K101", "U55"), ("K101", "K68"), ("K101", "L82"), ("C101", "K101"), ("C101", "P31"),
                   ("C101", "S100"))
# v0.102: G102 対 F30（炎のワザを受ける草ポケモンの弱点）・G102 対 R31（炎・ロケット団のリザードンなど）・G102 対 N102（新しいカードどうし。ふしぎなこなのこんらんと、両方の力が重なる
# 草の対戦ポケモン）・N102 対 C33（超の抵抗力を持つ無色のポケモン。抵抗力を当てはめず量が増える場面）・N102 対 G32（超が弱点の草ポケモン）・N102 対 C101（ソーナンスのカウンターで返す
# ダメージ）・N102 対 S48（ベトベトンの［かがくへんかガス］で力が消える場面）。組・席・seed は先に決めた（seed 0〜3。局を選び直さない）
PAIRINGS_V0_102 = (("G102", "F30"), ("G102", "R31"), ("G102", "N102"), ("N102", "C33"), ("N102", "G32"), ("N102", "C101"), ("N102", "S48"))
# v0.103: M103 対 F30（リザード・ウインディの進化ポケモンのワザと、ヒトカゲ・ガーディ・ブーバーのたねポケモンのワザ）・M103 対 W45（わるいカメールのこうらがえしで返すダメージ・わるいカメックス・
# ゴースト）・M103 対 C101（ソーナンスのカウンター（たねポケモンの返す効果）・ピジョン（進化ポケモン。受けた記録を読むオウムがえし））・M103 対 R52（エリカのハクリューのつれさる（自分を先に
# 山札にもどす）・ふぶき・ラッタ）・M103 対 S87（マチスのマルマインの［ショックボム］（進化ポケモンの特殊能力のダメージ）・コクーン・ダグトリオ・ゲンガー）・M103 対 S48（ベトベトンの
# ［かがくへんかガス］で力が消える場面）・M103 対 P31（ピッピ・ピクシーのゆびをふる（借りたワザと実際の使い手）・わるいゴルダック）。組・席・seed は先に決めた（seed 0〜3。局を選び直さない）
PAIRINGS_V0_103 = (("M103", "F30"), ("M103", "W45"), ("M103", "C101"), ("M103", "R52"), ("M103", "S87"), ("M103", "S48"), ("M103", "P31"))
# v0.104: G104 対 W104（新しいカードどうし）・W104 対 M103（ミュウの［ニュートラルシールド］と、たねのラプラス・進化したジュゴン・イノムーのワザ）・G104 対 M103（進化したキレイハナ・
# たねのプリン・ミルタンク・フシギダネ）・W104 対 P31・G104 対 P31（ピッピ・ピクシーのゆびをふるで、回復のワザを相手のワザとして使う。もうとっしんは既存の未対応で選ぶと止める）・
# W104 対 C101（ピジョンのオウムがえしで、受けたやさしいうた・オーロラウェーブを出す）・W104 対 M60（化石の秘密のゴース・ゴーストの「とうめい」）。組・席・seed は先に決めた
# （seed 0〜3。局を選び直さない）
PAIRINGS_V0_104 = (("G104", "W104"), ("W104", "M103"), ("G104", "M103"), ("W104", "P31"), ("G104", "P31"), ("W104", "C101"), ("W104", "M60"))
# v0.105: B105 対 D105（新しいカードどうし。無色2個エネルギーのついたポケモンをハイパーリバース・サイコリーフで数える・プレゼントの回復）・B105 対 M103・D105 対 M103（ミュウの
# ［ニュートラルシールド］と、進化したトランセル・バタフリーのワザ、たねのヒマナッツ・セレビィ・デリバードのワザ）・B105 対 P31・D105 対 P31（ピッピ・ピクシーのゆびをふるで、からやぶりしんか・
# ひざしをあびる・ハイパーリバース・サイコリーフ・プレゼントを相手のワザとして使う）・D105 対 C101（ピジョンのオウムがえしで受けたプレゼントを出す・ソーナンスのカウンター）・B105 対 M60・
# D105 対 M60（化石の秘密のゴース・ゴーストの「とうめい」）。組・席・seed は先に決めた（seed 0〜3。局を選び直さない）
PAIRINGS_V0_105 = (("B105", "D105"), ("B105", "M103"), ("D105", "M103"), ("B105", "P31"), ("D105", "P31"), ("D105", "C101"), ("B105", "M60"), ("D105", "M60"))
# v0.106: C106・F106 対 E106（新しいカードどうし）・C106・F106・E106 対 M103（ミュウの［ニュートラルシールド］と、進化したグランブル・カブトプス・サンドパン・ニドリーナ・ゴーストのワザ、
# たねのストライク・カモネギ・イシツブテ・ビリリダマのワザ）・C106・F106・E106 対 P31（ピッピ・ピクシーのゆびをふるで v0.106 のワザを相手のワザとして使う）・F106 対 M60（化石の秘密の
# ゴース・ゴーストの「とうめい」・カイリキーの［はんげき］）・E106 対 LF29（相手の場のロケット団のビリリダマ（名前「ビリリダマ」）とマチスのビリリダマ（数えない別の名前））・
# E106 対 T63（マチスの交渉で取ったサイド。きぜつ以外で取ったサイドをおんねんで数える）。組・席・seed は先に決めた（seed 0〜3。局を選び直さない）
PAIRINGS_V0_106 = (("C106", "E106"), ("F106", "E106"), ("C106", "M103"), ("F106", "M103"), ("E106", "M103"), ("C106", "P31"), ("F106", "P31"),
                   ("E106", "P31"), ("F106", "M60"), ("E106", "LF29"), ("E106", "T63"))
# v0.107: B107・E107・W107 の互い（新しいカードどうし）・B107・E107 対 M103（ミュウの［ニュートラルシールド］と、2 進化のバタフリー・1 進化のリングマのワザ、たねのビードル・クヌギダマ・
# そらをとぶピカチュウのワザ）・B107・E107・W107 対 P31（ピッピ・ピクシーのゆびをふるで v0.107 のワザを相手のワザとして使う）・E107・W107 対 M60（化石の秘密のゴースの「とうめい」・
# カイリキーの［はんげき］）・B107 対 M69（カスミのドククラゲの［にげこむ］・タケシのサイドンの［ベンチガード］）。組・席・seed は先に決めた（seed 0〜3。局を選び直さない）
PAIRINGS_V0_107 = (("B107", "E107"), ("E107", "W107"), ("W107", "B107"), ("B107", "M103"), ("E107", "M103"), ("B107", "P31"), ("E107", "P31"),
                   ("W107", "P31"), ("E107", "M60"), ("W107", "M60"), ("B107", "M69"))
# v0.108: D108・L108・G108 の互い（新しいカードどうし。与える -10 と受ける +20・状態の参照の組み合わせ）・D108・G108 対 M103（ミュウの［ニュートラルシールド］と、1 進化のヘルガー・アーボックの
# ワザ、たねのトゲピー・チョンチーのワザ）・L108・G108 対 P31（ピッピ・ピクシーのゆびをふるで v0.108 のワザを相手のワザとして使う。ピクシーのちいさくなる（8 段階））・D108・L108 対 M60
# （化石の秘密のゴーストの「とうめい」・カイリキーの［はんげき］）・L108 対 K76（なきごえ（「このカード」へのダメージだけの 2 段階の -10）と、使うワザのダメージ全体の -10）・D108 対 S92
# （いやなおと（8 段階の +20）とかみくだく）・L108 対 H62（オニスズメのオウムがえしが受けた -10 を返そうとする）。組・席・seed は先に決めた（seed 0〜3。局を選び直さない）
PAIRINGS_V0_108 = (("D108", "L108"), ("L108", "G108"), ("G108", "D108"), ("D108", "M103"), ("G108", "M103"), ("L108", "P31"), ("G108", "P31"),
                   ("D108", "M60"), ("L108", "M60"), ("L108", "K76"), ("D108", "S92"), ("L108", "H62"))
# v0.109: W109 対 P109（ぬるぬる・かわすとブリンクの互い）・P109 どうし（サイコパニックの 60。席を入れかえた局は同じ局なので 1 回だけ行う）・W109・P109 対 D108・L108（v0.108 の与える -10・
# 受ける +20 の計算の結果でコインの要否が決まる）・W109 対 G108（どくのウパー・エビワラーのポケモンチェックのダメージで効果が消えない）・W109・P109 対 M60（「とうめい」のゴースト（超）・
# カイリキーの［はんげき］（特殊能力のダメージにはコインを投げない））・W109・P109 対 P31（ピッピ・ピクシーのゆびをふるで v0.109 のワザを相手のワザとして使う。効果は使ったポケモンに）・
# P109 対 S83（ひかるミュウツー（超）のリフレクトシールド）・P109 対 M103（ミュウの［ニュートラルシールド］。1 進化のユンゲラーのワザは無効、ミュウのワザにはブリンクのコイン）・
# W109 対 Z60（かげぶんしん）・W109 対 G64・P109 対 H92（「うら」が出るまで投げるコインのダメージにも受けるときのコイン）。組・席・seed は先に決めた（seed 0〜3。局を選び直さない）
PAIRINGS_V0_109 = (("W109", "P109"), ("P109", "P109"), ("W109", "D108"), ("P109", "L108"), ("W109", "G108"), ("W109", "M60"), ("P109", "M60"),
                   ("W109", "P31"), ("P109", "P31"), ("P109", "S83"), ("P109", "M103"), ("W109", "Z60"), ("W109", "G64"), ("P109", "H92"))
# v0.110: F110 対 G110（こらえるとだいばくはつ・こうてつか）・G110 どうし（だいばくはつで両方の「きぜつ」しない効果。席を入れかえた局は同じ局なので 1 回だけ行う）・F110・G110 対 W45
# （ゴースのみちづれ（KS2）・わるいカメールのこうらがえし（返す効果のダメージ））・F110・G110 対 T81（相手のきあいのハチマキ・学習装置・はんげきのツメ）・G110 対 V44（サカキのカイリキーの
# こんじょう）・G110 対 G61（［ファイナルビーム］）・F110・G110 対 P31（ピッピ・ピクシーのゆびをふるで、こらえる・こうてつか・だいばくはつを相手のワザとして使う）・F110 対 G64（「うら」が
# 出るまで投げるコインのダメージ）・F110 対 Z60（スピードスター・かげぶんしん）・G110 対 P109（あやしいひかりのこんらんの 20・v0.109 のコイン）・F110 対 G108（どくのダメージ）・
# G110 対 M60（カイリキーの［はんげき］の特殊能力のダメージ）。組・席・seed は先に決めた（seed 0〜3。局を選び直さない）
PAIRINGS_V0_110 = (("F110", "G110"), ("G110", "G110"), ("F110", "W45"), ("G110", "W45"), ("F110", "T81"), ("G110", "T81"), ("G110", "V44"), ("G110", "G61"),
                   ("F110", "P31"), ("G110", "P31"), ("F110", "G64"), ("F110", "Z60"), ("G110", "P109"), ("F110", "G108"), ("G110", "M60"))
# v0.111: P111 どうし（サイコクラッシュの数える相手の「超」エネルギーカードが多い・シンクロウェーブの枚数がそろう。席を入れかえた局は同じ局なので 1 回だけ行う）・P111 対 P109（「超」ポケモンの
# 弱点 超）・W109（「超」エネルギーカードのない相手で基本となるダメージ 0）・B98（レインボーエネルギー・ミラクルエネルギー。RB1・MEC1）・R58（レインボーエネルギー・無色2個エネルギー・特殊
# エネルギー）・L85（ミラクルエネルギー・無色2個エネルギー・リサイクルエネルギー・悪・鋼エネルギー）・Z59（［エネエネ］でエネルギーとしてついたカード。BZ2・シンクロウェーブで 1 枚）・P31
# （ピッピ・ピクシーのゆびをふるで、サイコクラッシュ・シンクロウェーブを相手のワザとして使う）・K65（変わり身の術。宣言のあとの入れ替え）・G83（やさしいモルフォンの使ってから失敗する
# シンクロウェーブ）・L67（マチスの秘策。場のうらのカード）・R88（色を変える特殊能力・いろいろな色のエネルギー）・M50（ミュウのサイコウェーブ・控えの「とうめい」）・G110（v0.110 の
# 「きぜつ」しない効果）。組・席・seed は先に決めた（seed 0〜3。局を選び直さない）
PAIRINGS_V0_111 = (("P111", "P111"), ("P111", "P109"), ("P111", "W109"), ("P111", "B98"), ("P111", "R58"), ("P111", "L85"), ("P111", "Z59"), ("P111", "P31"),
                   ("P111", "K65"), ("P111", "G83"), ("P111", "L67"), ("P111", "R88"), ("P111", "M50"), ("P111", "G110"))
# v0.112: T112 対 O112（2 枚が同じ局に出る）・O112 どうし（ふしょくえきの「うら」の制限。席を入れかえた局は同じ局なので 1 回だけ行う）・T112・O112 対 P31（ピッピ・ピクシーの
# ゆびをふるで、しょくしゅをつかう（実際に使ったポケモンの「水」の数）・ふしょくえき（相手のワザとして使えない既存の未対応））・O112 対 E31（ミュウツーのバリアーでマヒが無効でも
# 「うら」の制限は有効）・O112 対 M60（ゴーストの［とうめい］・カイリキーの［はんげき］）・O112 対 K65（変わり身の術）・T112 対 W109（受けるときのコインの効果）・O112 対 T81（相手の
# きあいのハチマキ・学習装置・はんげきのツメ）。組・席・seed は先に決めた（seed 0〜3。局を選び直さない）
PAIRINGS_V0_112 = (("T112", "O112"), ("O112", "O112"), ("T112", "P31"), ("O112", "P31"), ("O112", "E31"), ("O112", "M60"), ("O112", "K65"), ("T112", "W109"),
                   ("O112", "T81"))
# v0.113: 4 つの v0.113 のデッキどうし（6 組。同じデッキどうしの組は置かない）・P113 と D113 対 P31（ピッピ・ピクシーのゆびをふるで、だいぎゃくてん？・くろいキバ・ダークフレイムなどを
# 実際に使ったポケモンで処理する）・L113 対 E31（ミュウツーのバリアーでギガボルトが HC3。ゆうでんはバリアーでも投げる）・T113 対 M60（ゴーストの［とうめい］・カイリキーの［はんげき］）・
# D113 対 T81（相手のきあいのハチマキ・学習装置・はんげきのツメ）。組・席・seed は先に決めた（seed 0〜3。局を選び直さない）
PAIRINGS_V0_113 = (("P113", "L113"), ("P113", "D113"), ("P113", "T113"), ("L113", "D113"), ("L113", "T113"), ("D113", "T113"), ("P113", "P31"), ("D113", "P31"),
                   ("L113", "E31"), ("T113", "M60"), ("D113", "T81"))
# v0.114: 4 つのベイビィのデッキどうし（6 組）と、L114 対 D49（メタモンの［へんしん］でベイビィの姿になる BX1・思い出させる）・C114 対 M103（ミュウの［ニュートラルシールド］と
# ベイビィから進化したポケモン）・F114 対 M50（ミュウのたいかビーム・退化スプレーでベイビィの上のたねポケモンカードをはがす）・P114 対 L67（マチスの秘策のうらのカードの試すカードに
# ベイビィ）・L114 対 M87（［ヒートプレート］・爆発ジムとベンチに出すベイビィ。ベイビィの進化は HP2 なので手順が使わない）・L114 対 K65（変わり身の術とベイビィのルールのコイン。NT1）・
# C114 対 P31（ピッピ・ピクシーのゆびをふるで、ベイビィのワザを相手のワザとして使う）。組・席・seed は先に決めた（seed 0〜3。局を選び直さない）
PAIRINGS_V0_114 = (("L114", "C114"), ("L114", "F114"), ("L114", "P114"), ("C114", "F114"), ("C114", "P114"), ("F114", "P114"), ("L114", "D49"), ("C114", "M103"),
                   ("F114", "M50"), ("P114", "L67"), ("L114", "M87"), ("L114", "K65"), ("C114", "P31"))
# v0.115: 5 つの v0.115 のデッキどうしの 8 組（通常とわるいバンギラスの系統どうし・おたがいの控え・配分の集中と分散）と、T115 対 F97（相手の控えのアンノーンD の［DARK df］となぎたおす）・
# W115 対 R65（相手のタケシのサイドンの［ベンチガード］と控えへのダメージ・配分）・E115 対 M60（相手のゴーストの［とうめい］と控えへのダメージ。TS1・T27）・D115 対 P31（ピッピ・ピクシーの
# ゆびをふるで、やまくだき・ぶんなげる・ばくれつしんかを相手のワザとして使う）・R115 対 M103（ミュウの［ニュートラルシールド］と進化ポケモンのワザ）。組・席・seed は先に決めた
# （正式な対戦は seed 0〜3。開発中に手順を確かめた seed 50・51 とは別。局を選び直さない）
PAIRINGS_V0_115 = (("T115", "D115"), ("T115", "R115"), ("T115", "W115"), ("D115", "R115"), ("D115", "E115"), ("R115", "W115"), ("R115", "E115"), ("W115", "E115"),
                   ("T115", "F97"), ("W115", "R65"), ("E115", "M60"), ("D115", "P31"), ("R115", "M103"))
# v0.116: 4 つの v0.116 のデッキどうしの 6 組（ついた時の効果を受けたポケモンへの、手札・ワザ・はらだいこの山札からのエネルギーのつけ方、バトンタッチ・エナジーサイクル・エナジーコントロールの
# 付け替え、げんしのしずく・さいせいの退化、ツイスターの付属カード）と、P116・C116 対 R58（相手のカメックスの［あまごい］・フシギバナの［エナジートランス］で効果を受けたポケモンに
# つける・つけ替える。AT1）・W116 対 P31（ピッピ・ピクシーのゆびをふるで、はらだいこ・げんしのしずく・やみのしょくしゅを相手のワザとして使う）・G116 対 M60（相手のゴーストの［とうめい］と
# ツイスター・ようかい）・P116 対 M103（ミュウの［ニュートラルシールド］と進化ポケモンのワザ）・W116 対 C114（ベイビィから進化したポケモンへのげんしのしずく。NB2）・C116 対 E50（退化スプレー・
# フシギバナ）。組・席・seed は先に決めた（正式な対戦は seed 0〜3。開発中に手順を確かめた seed 50・51 とは別。局を選び直さない）
PAIRINGS_V0_116 = (("G116", "W116"), ("G116", "P116"), ("G116", "C116"), ("W116", "P116"), ("W116", "C116"), ("P116", "C116"),
                   ("P116", "R58"), ("C116", "R58"), ("W116", "P31"), ("G116", "M60"), ("P116", "M103"), ("W116", "C114"), ("C116", "E50"))
# v0.117: 4 つの v0.117 のデッキどうしの 6 組（［CHASE］・おいうちと「にげる」、［QUICKEN］の防護、［ときわたり］、［でんせつのからだ］と相手・自分のトレーナー、もちさる・ぱっときえる・
# メガフレイム・いかく・［きしかいせい］・［かえるのうた］）と、U117 対 G61（わるいダグトリオの［おとしあな］）・D117 対 M87（マグカルゴの［やけのこり］・フォレトスの［まきびし］とおいうち）・
# L117 対 Z59（まきちらせ!ベトベトガスと［でんせつのからだ］。LB2）・N117 対 S66（ナツメのESP）・L117 対 G61（突風・ディフェンダーなどの相手のトレーナー）・D117 対 P31（ゆびをふるで
# おいうち・いかくを相手のワザとして使う）・N117 対 M60（相手のゴーストの［とうめい］とおうふくビンタ・メガホーン）。組・席・seed は先に決めた（正式な対戦は seed 0〜3。開発中に手順を
# 確かめた seed 50・51 とは別。局を選び直さない）
PAIRINGS_V0_117 = (("U117", "D117"), ("U117", "L117"), ("U117", "N117"), ("D117", "L117"), ("D117", "N117"), ("L117", "N117"),
                   ("U117", "G61"), ("D117", "M87"), ("L117", "Z59"), ("N117", "S66"), ("L117", "G61"), ("D117", "P31"), ("N117", "M60"))
# v0.118: 4 つの v0.118 のデッキどうしの 6 組（［XXXXX］といっしょのめざめるパワー・わるわるMAX・エアロウイング、ふしぎなかおり・ごくらくかふん（相手の場の回復をふくむ）・まるもうけ、
# スミでっぽう・しめつづけるの「にげる」・マッハひこう・［トランスポート］、［じくうへんかん］とスタジアム）と、X118 対 Z59（まきちらせ!ベトベトガスと［XXXXX］）・G118 対 M60（相手のゴーストの
# ［とうめい］とふしぎなかおり）・G118 対 P31（ゆびをふるで、ふしぎなかおり・ごくらくかふん・まるもうけを相手のワザとして使う）・W118 対 P31（同じく、スミでっぽう・しめつづける・マッハひこう）・
# S118 対 T74（ポケモンタワー・エネルギースタジアムを［じくうへんかん］でトラッシュから出す）・S118 対 L57（v0.57 のスタジアムどうしの置きかえ）。組・席・seed は先に決めた（正式な対戦は
# seed 0〜3。開発中に手順を確かめた seed 50・51 とは別。局を選び直さない）
PAIRINGS_V0_118 = (("X118", "G118"), ("X118", "W118"), ("X118", "S118"), ("G118", "W118"), ("G118", "S118"), ("W118", "S118"),
                   ("X118", "Z59"), ("G118", "M60"), ("G118", "P31"), ("W118", "P31"), ("S118", "T74"), ("S118", "L57"))
# v0.119: 4 つの v0.119 のデッキどうしの 6 組（どく・［ポイズンミスト］・どくどくエキス・どくをだす・ガスばくはつと、［シェルアーマー］・［かたいから］・［いあつ］・［ふかいねむり］・
# ひきずりこむ・いたみわけ・なぞのこうせん・［めいれい］・スピードスター・［アレルギーほうし］）と、D119 対 F114（相手のベイビィポケモンとブビィの「モクモク」）・D119 対 L114（相手の
# エレキッドの［わんぱくパンチ］・ピチュー）・W119 対 T74（エナジーへんかん・ゴミあさり・ふしちょう・［つりあげる］・ポケモンタワー）・W119 対 M85（［ファイヤーリチャージ］）・W119 対 F75
# （おにびあつめ）・P119 対 P31（ゆびをふるで、ガスばくはつ・どくをだすを相手のワザとして使う）。組・席・seed は先に決めた（正式な対戦は seed 0〜3。開発中に手順を確かめた seed 50・51
# とは別。局を選び直さない）
PAIRINGS_V0_119 = (("P119", "D119"), ("P119", "W119"), ("P119", "G119"), ("D119", "W119"), ("D119", "G119"), ("W119", "G119"),
                   ("D119", "F114"), ("D119", "L114"), ("W119", "T74"), ("W119", "M85"), ("W119", "F75"), ("P119", "P31"))
# v0.120: 4 つの v0.120 のデッキどうしの 6 組（復活と場でのたねのあつかい・たまごの化石・ゆびをふる・おおきくゆびをふる・サイコデュープ・りゅうのいでんし・たつまき・しんかのほうし・
# ちからをあわせる・［げんしのきおく］・［にんぎょうつかい］・［ものまね］）と、F120 対 M103（相手のミュウの［ニュートラルシールド］と、復活したたね・その上に進化したポケモンのワザ）・F120 対 M50
# （たいかビーム・退化スプレーと復活したカードの上に進化したポケモン。FE1）・F120 対 L114（相手のベイビィから進化したポケモンと［げんしのきおく］）・F120 対 D49（相手のメタモンの［へんしん］と
# 復活したたね。TF3）。組・席・seed は正式な対戦の前に決めた（正式な対戦は seed 0〜3。開発中に手順を確かめる seed 60〜63 とは別。局を選び直さない）
PAIRINGS_V0_120 = (("F120", "T120"), ("F120", "S120"), ("F120", "J120"), ("T120", "S120"), ("T120", "J120"), ("S120", "J120"),
                   ("F120", "M103"), ("F120", "M50"), ("F120", "L114"), ("F120", "D49"))
# v0.121: 4 つの v0.121 のデッキどうしの 6 組（ロックオン・でんじほう・なきごえ・ぶきみなとおぼえ・じごくのほのお・ちょうはつ・だいらんとう・おおあくび・おおいびき・ボロのつりざお・
# カスミのてあて）と、C121 対 L114（エレキッドの［わんぱくパンチ］となきごえ。GN1）・H121 対 M87（わるいマグカルゴの［ヒートプレート］と手札から出すワザ。HB1）・C121 対 T74（ゴーストの
# 「とうめい」とロックオン。LO1）。組・席・seed は正式な対戦の前に決めた（正式な対戦は seed 0〜3。開発中に手順を確かめる seed 70〜73 とは別。局を選び直さない）
# v0.122: 6 つの v0.122 のデッキの 8 組（アンノーンの 3 デッキどうし・化石・草・雷の 3 デッキどうしと、アンノーン対化石・草）と、A122 対 C121（コイル neo2-043 は鋼タイプ。［METAL df］）・
# U122 対 M78（鋼のエアームド・ハガネールなど。［METAL df］はない側の［UNDO］）。組・席・seed は正式な対戦の前に決めた（正式な対戦は seed 0〜3。開発中に手順を確かめる seed 80〜83 とは
# 別。局を選び直さない）
PAIRINGS_V0_122 = (("A122", "U122"), ("A122", "W122"), ("U122", "W122"), ("F122", "B122"), ("F122", "L122"), ("B122", "L122"), ("A122", "F122"), ("W122", "B122"),
                   ("A122", "C121"), ("U122", "M78"))
PAIRINGS_V0_121 = (("C121", "H121"), ("C121", "U121"), ("C121", "Y121"), ("H121", "U121"), ("H121", "Y121"), ("U121", "Y121"),
                   ("C121", "L114"), ("H121", "M87"), ("C121", "T74"))
# v0.123: W123 対 K123（ウィンディ 3 枚の 3 つのワザとカツラのウィンディ 2 枚。「ウィンディ」と「カツラのウィンディ」の別のデッキ）・W123 対 P31（ピクシー・ピッピのゆびをふるで、相手のワザとして
# 使うでんこうせっか・いかりのほのお。炎エネルギーカードのない使い手はいかりのほのおを選べない）・W123 対 E82（相手の場のエコロジム・リサイクルエネルギーと、自分のワザでトラッシュする炎エネルギー
# カード）・K123 対 F30（v0.30 のデッキの第1弾のウィンディ（名前を直した PMCG1-019）と、ほのおのあらし）。組・席・seed は正式な対戦の前に決めた（正式な対戦は seed 0〜3。開発中に手順を
# 確かめる seed 90〜93 とは別。局を選び直さない）
PAIRINGS_V0_123 = (("W123", "K123"), ("W123", "P31"), ("W123", "E82"), ("K123", "F30"))
# v0.124: S124 対 G124（相手の GR団のミュウツー・わるいポケモンに変身する・わるいはどう）・S124 対 W123（炎のワザを写す。悪・鋼の記号はない）・G124 対 W123（わるいポケモンのワザへの追加）・
# S124 対 L122（雷のワザを写す）・G124 対 B122（草・闘の相手へのわるいぞうふく）・S124 対 F30（化石のメタモンと［すごいへんしん］の両方が相手の炎のポケモンを写す）。組・席・seed は正式な
# 対戦の前に決めた（正式な対戦は seed 0〜3。開発中に手順を確かめる seed 90〜93 とは別。局を選び直さない）
PAIRINGS_V0_124 = (("S124", "G124"), ("S124", "W123"), ("G124", "W123"), ("S124", "L122"), ("G124", "B122"), ("S124", "F30"))
# v0.125: W125 対 P109（あやしいひかりのこんらん・あくむのねむり）・W125 対 P119（どくをだす・ガスばくはつ・［ポイズンミスト］のどく）・W125 対 G108（どくえき・どくばりのどく）。
# 1 つの状態をつける相手と組ませ、［てだすけ］とふくらむを狙う。開発用の seed 90〜93 で、ねむりの相手 Y121 は自分のプリンの「こもりうた」と重なってポケモンチェックの既存の停止
# （UNRESOLVED_POKEMON_CHECK_SLEEP_COIN_ORDER）で止まりやすく、E115 は特殊状態がつかなかったので、P109・G108 に替えた。組・席・seed は正式な対戦の前に決めた（正式な対戦は seed 0〜3。
# 局を選び直さない）
PAIRINGS_V0_125 = (("W125", "P109"), ("W125", "P119"), ("W125", "G108"))
# v0.126: M126 対 F126（お互いにフラッシュを使い、サカキのニャースがおもてのいちばん上を見てワザを選ぶ。マサキ・パソコン通信で引く・切る）・M126 対 W125・F126 対 F45（相手のサカキの
# ニャースが、フラッシュでおもてにした山札のいちばん上を見る）。組・席・seed は正式な対戦の前に決めた（正式な対戦は seed 0〜3。開発中に手順を確かめる seed 90〜93 とは別。局を選び直さない）
PAIRINGS_V0_126 = (("M126", "F126"), ("M126", "W125"), ("F126", "F45"))
# v0.127: 途中停止の起こりうる対戦（F127 対 W28・F127 対 S124: 「水」エネルギーの多い相手にドライアップ・怪電波マシーン、F127 対 F45: 「水」のない相手に怪電波マシーン）と、通常のプロモの
# 対戦（P127 対 W28・P127 対 F45: 利用者が指定した簡略ルールのワザ。途中停止の起こるカードはない）。組・席・seed は正式な対戦の前に決めた（正式な対戦は seed 0〜3。開発中に手順を確かめる
# seed 90〜93 とは別。途中停止した局を除かない・seed を選び直さない）
PAIRINGS_V0_127 = (("F127", "W28"), ("F127", "S124"), ("F127", "F45"), ("P127", "W28"), ("P127", "F45"))
# v0.129: Q129 対 W28（水・無色）・Q129 対 F45（闘）・Q129 対 Q129（お互いにクイズを使い、お互いに答える）。組・席・seed は正式な対戦の前に決めた（正式な対戦は seed 0〜3。開発中に
# 手順を確かめる seed 90〜93 とは別。局・seed を選び直さない）
PAIRINGS_V0_129 = (("Q129", "W28"), ("Q129", "F45"), ("Q129", "Q129"))
# v0.130: T130 どうし（お互いに使い、受け取ったカードをふたたび交換しうる。席を入れかえた局は同じ局なので 1 回だけ行う）・T130 対 W28（水・無色）・T130 対 F45（闘）。組・席・seed は正式な
# 対戦の前に決めた（正式な対戦は seed 0〜3。開発中に手順を確かめる seed 90〜93 とは別。局・seed・方策を選び直さない）
PAIRINGS_V0_130 = (("T130", "T130"), ("T130", "W28"), ("T130", "F45"))
# v0.131: X131 どうし（相手のナッシー[Exeggutor] をゆびをふる・［へんしん］で写しうる。席を入れかえた局は同じ局なので 1 回だけ行う）・X131 対 W28（水・無色）・X131 対 F45（闘）。組・席・seed は
# 正式な対戦の前に決めた（正式な対戦は seed 0〜3。開発中に手順を確かめる seed 90〜93 とは別。局・seed を選び直さない）
PAIRINGS_V0_131 = (("X131", "X131"), ("X131", "W28"), ("X131", "F45"))
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
           "v0.81": PAIRINGS_V0_81, "v0.82": PAIRINGS_V0_82, "v0.83": PAIRINGS_V0_83,
           "v0.84": PAIRINGS_V0_84, "v0.85": PAIRINGS_V0_85, "v0.86": PAIRINGS_V0_86,
           "v0.87": PAIRINGS_V0_87, "v0.88": PAIRINGS_V0_88, "v0.89": PAIRINGS_V0_89, "v0.90": PAIRINGS_V0_90, "v0.91": PAIRINGS_V0_91,
           "v0.92": PAIRINGS_V0_92, "v0.93": PAIRINGS_V0_93, "v0.94": PAIRINGS_V0_94, "v0.95": PAIRINGS_V0_95,
           "v0.96": PAIRINGS_V0_96, "v0.97": PAIRINGS_V0_97, "v0.98": PAIRINGS_V0_98, "v0.99": PAIRINGS_V0_99, "v0.100": PAIRINGS_V0_100,
           "v0.101": PAIRINGS_V0_101, "v0.102": PAIRINGS_V0_102, "v0.103": PAIRINGS_V0_103, "v0.104": PAIRINGS_V0_104,
           "v0.105": PAIRINGS_V0_105, "v0.106": PAIRINGS_V0_106, "v0.107": PAIRINGS_V0_107,
           "v0.108": PAIRINGS_V0_108, "v0.109": PAIRINGS_V0_109, "v0.110": PAIRINGS_V0_110, "v0.111": PAIRINGS_V0_111, "v0.112": PAIRINGS_V0_112,
           "v0.113": PAIRINGS_V0_113, "v0.114": PAIRINGS_V0_114, "v0.115": PAIRINGS_V0_115,
           "v0.116": PAIRINGS_V0_116, "v0.117": PAIRINGS_V0_117, "v0.118": PAIRINGS_V0_118,
           "v0.119": PAIRINGS_V0_119, "v0.120": PAIRINGS_V0_120, "v0.121": PAIRINGS_V0_121, "v0.122": PAIRINGS_V0_122,
           "v0.123": PAIRINGS_V0_123, "v0.124": PAIRINGS_V0_124, "v0.125": PAIRINGS_V0_125, "v0.126": PAIRINGS_V0_126,
           "v0.127": PAIRINGS_V0_127, "v0.129": PAIRINGS_V0_129, "v0.130": PAIRINGS_V0_130,
           "v0.131": PAIRINGS_V0_131}
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


def _v113_attract_short(state, command, *, rainbow=False) -> bool:
    """v0.113: ゆうでん（相手のワザとして使うものも）を、山札の「雷」の基本エネルギーカードがコインの枚数（3）より少ない（``rainbow`` なら、山札にレインボーエネルギーもある。そうでなければ
    1 枚以上ある）ときに宣言した（FC1・RB2。「おもて」の数によっては H 枚を選べない）。道具が山札を数える（エンジンの問い合わせを読まない）。"""
    if "DamageThenCoinsAttachTypedEnergyFromDeck" not in _attack_and_copied_types(state, command):
        return False
    deck = state.players[command.player].deck
    lightning = sum(1 for uid in deck if _v113_basic(state, uid, EnergyType.LIGHTNING))
    if rainbow:
        return lightning < 3 and any(state.cards[uid].card_id == RAINBOW_ENERGY for uid in deck)
    return 0 < lightning < 3


def _v113_static_rainbow(state, command) -> bool:
    """v0.113: メリープ（neo1-038）のせいでんき（既存の ``AttachFromDeckUpToNamedCount``）を、山札にレインボーエネルギーがあるときに宣言した（既存の RB2。v0.113 の L113 のデッキに
    レインボーエネルギーを入れたので起こる。それまでのデッキでは起こらなかった）。"""
    return "AttachFromDeckUpToNamedCount" in _attack_and_copied_types(state, command) and any(
        state.cards[uid].card_id == RAINBOW_ENERGY for uid in state.players[command.player].deck)


def _v113_discard_rainbow(state, command) -> bool:
    """v0.113: ダークフレイム（相手のワザとして使うものも）を、自分のトラッシュにレインボーエネルギーがあるときに宣言した（RB2）。"""
    return "DiscardEnergyThenDamageThenAttachFromDiscard" in _attack_and_copied_types(state, command) and any(
        state.cards[uid].card_id == RAINBOW_ENERGY for uid in state.players[command.player].discard)


def _attack_effect_of(state, command):
    """v0.99: 使おうとするワザの登録の実装（``_attack_definition`` のワザ。相手のワザとして使うワザは、そのワザ自身）。"""
    definition = _attack_definition(state, command)
    return state.effects.attack_effect(definition.id, definition.attacks[command.attack_index], definition.attacks)


def _copier(state, command):
    definition = _attack_definition(state, command)
    effect = state.effects.attack_effect(definition.id, definition.attacks[command.attack_index], definition.attacks)
    # v0.100: スケッチ（前の相手の番のワザを自分のワザとして使う。HC9・UNSUPPORTED_COPIED_ATTACK）も
    return type(effect).__name__ in ("CopyOpponentAttackEffect", "ThreeCoinPsychicPower", "UseLastOpponentAttack",
                                     "CopyAttackFromSource")  # v0.120: ゆびをふる・おおきくゆびをふる・サイコデュープ・りゅうのいでんし（HC9・PE2・UNSUPPORTED_COPIED_ATTACK）


def _v119_recover_by_heads_short(state, command) -> bool:
    """v0.119: おにびあつめ（``CoinsRecoverEnergyByHeads``。v0.75）で、自分のトラッシュのその色の基本エネルギーカードが 1 枚以上・コインの枚数より少ない（「おもて」の数ぶんを選べない
    ことがある。FC1）。ポケモンタワー・はたらく［アレルギーほうし］があれば当たらない（コインの前のほかの扱い）。道具が場・トラッシュから数える。"""
    effect = _attack_effect(state, command)
    if type(effect).__name__ != "CoinsRecoverEnergyByHeads" or discard_to_hand_suppressor(state) is not None:
        return False
    if any(isinstance(slot.effect, E.DiscardPileImmunityToPokemonEffects) for side in state.players for p in side.in_play() for slot in E.powers_of(state, p)):
        return False
    count = sum(1 for uid in state.players[command.player].discard if state.card_def(uid).is_basic_energy and state.card_def(uid).provides is effect.energy_type)
    return 1 <= count < effect.coins


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
    if "UseLastOpponentAttack" in names:
        # v0.100: スケッチは、ログの前の相手の番に相手が宣言したワザを使う
        copied = _v100_sketch_copy_type(state, command)
        if copied is not None:
            names.add(copied)
    defender = _defender(state, command)
    if _copier(state, command) and defender is not None and "UseLastOpponentAttack" not in names:
        for option in available_attacks(state, defender):
            definition = state.definitions[option.card_id]
            effect = state.effects.attack_effect(definition.id, definition.attacks[option.attack_index], definition.attacks)
            names.add(type(effect).__name__)
    copier = _attack_effect(state, command)
    if isinstance(copier, E.CopyAttackFromSource) and copier.source != E.COPY_FROM_DEFENDER:
        # v0.120: おおきくゆびをふる・サイコデュープ（相手の場のポケモンのワザ）・りゅうのいでんし（自分の進化前のカードのワザ）は、その範囲の選べるワザの型も（宣言の前の先読みは
        # 選び方のすべてを試す）。ゆびをふるは上の相手の対戦ポケモンのワザと同じ
        for key, _problem in E.copy_source_entries(state, command.player, _attacker(state, command), copier.source):
            definition = state.definitions[key.card_id]
            names.add(type(state.effects.attack_effect(definition.id, definition.attacks[key.attack_index], definition.attacks)).__name__)
    return names


def _defender(state, command):
    return state.players[1 - command.player].active


def _attack_effect(state, command):
    definition = _attack_definition(state, command)
    return state.effects.attack_effect(definition.id, definition.attacks[command.attack_index], definition.attacks)


def _v095_mill_count(state, command):
    """v0.95: 使うワザが、自分の山札の上からトラッシュしたカードの「「X」エネルギーカード」を数える・手札に加えるワザ（マグマふんしゅつ・マグマラッシュ・やまくずし）なら、トラッシュする
    枚数。ほかのワザなら None。"""
    effect = _attack_effect(state, command)
    return effect.count if isinstance(effect, (MillSelfThenDamage, DamageThenMillReturnTypeEnergy)) else None


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


def _v087_shock_blast_on(state, player) -> bool:
    """v0.87: ``player`` の場に、今はたらく［ショックボム］（``CoinDamageBothActivesOnAttackDamage``）を持つポケモンがいるか（ねむり・マヒ・こんらんでなく、力が消えていない）。"""
    from kyuura_engine import effects
    from kyuura_engine.continuous import power_suppressed

    for pokemon in state.players[player].in_play():
        c = pokemon.conditions
        if c.asleep or c.paralyzed or c.confused:
            continue
        if any(isinstance(slot.effect, effects.CoinDamageBothActivesOnAttackDamage) and not power_suppressed(state, slot.power, pokemon)
               for slot in effects.powers_of(state, pokemon)):
            return True
    return False


def _v086_crystal_body(state, pokemon) -> bool:
    """v0.86: 場のポケモン ``pokemon`` の［クリスタルボディ］が今はたらくか（ねむり・マヒ・こんらんでなく、かがくへんかガスなど・スタンウェーブで力が消えていない）。"""
    from kyuura_engine import effects
    from kyuura_engine.continuous import power_suppressed
    from kyuura_engine.persistent import powers_stopped

    c = pokemon.conditions
    if c.asleep or c.paralyzed or c.confused or powers_stopped(state, pokemon) is not None:
        return False
    return any(isinstance(slot.effect, effects.OpponentAttackEffectImmunity) and not power_suppressed(state, slot.power, pokemon)
               for slot in effects.powers_of(state, pokemon))


def _v103_neutral_shield(state, command) -> bool:
    """v0.103: 相手の場のポケモン（バトル場・ベンチ。カスミのゴルダックの「スーパーデストロイ」はエネルギーのついた相手のポケモン全員が対象）に、今はたらく［ニュートラルシールド］
    （ねむり・マヒ・こんらんでなく、かがくへんかガスなど・スタンウェーブで力が消えていない）を持つポケモンがいて、ワザを使うポケモンの今の姿が進化ポケモンか（場から確かめる。HC3 の
    止める理由のワザの効果を受けないポケモン）。"""
    from kyuura_engine import effects

    attacker = _attacker(state, command)
    if not any(_v086_power_working(state, pokemon, effects.EvolvedOpponentAttackImmunity) for pokemon in state.players[1 - command.player].in_play()):
        return False
    return effects.is_evolution_in_play(state, attacker)  # v0.114: ベイビィから進化したたねポケモンも進化ポケモン（GR-2000-P315-EVOLVED-BABY）


def _v086_power_working(state, pokemon, kind) -> bool:
    """v0.103: 場のポケモン ``pokemon`` の、型 ``kind`` の特殊能力が今はたらくか（``_v086_crystal_body`` と同じ確かめ）。"""
    from kyuura_engine import effects
    from kyuura_engine.continuous import power_suppressed
    from kyuura_engine.persistent import powers_stopped

    c = pokemon.conditions
    if c.asleep or c.paralyzed or c.confused or powers_stopped(state, pokemon) is not None:
        return False
    return any(isinstance(slot.effect, kind) and not power_suppressed(state, slot.power, pokemon) for slot in effects.powers_of(state, pokemon))


def _v091_marked(st, player, kind):
    """v0.91: ``player`` の場の（うらでない）ポケモンの、種類 ``kind`` のマーカーがのっているかの並び。"""
    return [any(m.kind == kind for m in p.markers) for p in st.players[player].in_play() if not st.is_face_down(p)]


def _v120_permission_in_play(state) -> bool:
    """v0.120: 許可で使えるワザ（VP1）を与えうる特殊能力（［げんしのきおく］・［にんぎょうつかい］・［ものまね］）を持つポケモンが場にいる（場から確かめる。はたらいているかは見ない）。"""
    kinds = (E.PreEvolutionAttacksForEvolvedActives, E.DollUsesHolderAttacks, E.UseDefenderAttacks)
    return any(isinstance(slot.effect, kinds) for side in state.players for p in side.in_play() if not state.is_face_down(p) for slot in E.powers_of(state, p))


def _v124_copied_present(st) -> bool:
    """v0.124: 場に変身している（［へんしん］・［すごいへんしん］）ポケモンがいるか（変身の共通ルールの停止を、場から確かめる）。"""
    return any(not st.is_face_down(p) and E.current_form(st, p).kind in E.COPIED_FORMS for pl in st.players for p in pl.in_play())


def _v124_pulse_applies(st, c) -> bool:
    """v0.124: ワザを使うポケモンが「わるい」ポケモンで、持ち主の場に［わるいはどう］がはたらきうる（DP1・DF1 を場から確かめる）。"""
    attacker = st.players[c.player].active
    return attacker is not None and bool(E.dark_pulse_holders(st, c.player)) and E.field_name_matches(st, attacker, E.DARK_POKEMON)


def _v125_active_conditions(st, player) -> tuple:
    """v0.125: ``player`` の対戦ポケモンの特殊状態（［てだすけ］の HH1・HH2 を場から確かめる）。"""
    active = st.players[player].active
    return () if active is None else active.conditions.names()


def _v125_helping_hand(st, c) -> bool:
    """v0.125: コマンドが［てだすけ］の宣言か（のせたカード・写したカードの供給もふくめ、宣言する特殊能力の実装で見分ける）。"""
    if not isinstance(c, UsePokemonPower):
        return False
    found = st.find_pokemon(c.pokemon_id)
    if found is None:
        return False
    return any(isinstance(slot.effect, E.CureOneActiveConditionOnHeadsFromBench) and slot.key.power_index == c.power
               for slot in E.powers_of(st, found[1]))


def _v125_inflated_present(st) -> bool:
    """v0.125: 場に、今の番にはたらく「ふくらむ」の効果（ワザ以外のダメージに当てはめるかが決まらない印のある ``DamageReduction``）があるか（IF1 を場から確かめる）。"""
    return any((r := E.damage_reduction(st, p)) is not None and r.non_attack_unresolved for pl in st.players for p in pl.in_play())


V031_STOPS = {
    # v0.125（docs/wigglytuff-helping-hand-v0.125.md 11 章）: ［てだすけ］の対象 0 個・2 個（HH1・HH2）と、「ふくらむ」の効果があるときのワザ以外のダメージ（IF1）。どれも場から確かめる
    "UNRESOLVED_HELPING_HAND_WITHOUT_CONDITION": lambda st, c: _v125_helping_hand(st, c) and not _v125_active_conditions(st, c.player),
    "UNRESOLVED_HELPING_HAND_CHOICE": lambda st, c: _v125_helping_hand(st, c) and len(_v125_active_conditions(st, c.player)) == 2,
    "UNRESOLVED_INFLATE_NON_ATTACK_DAMAGE": lambda st, c: _v125_inflated_present(st),
    # v0.124（docs/super-transform-dark-pulse-v0.124.md 10 章）: 変身の共通ルール・すごいへんしん・わるいはどうの停止。どれも場から確かめる
    "UNRESOLVED_DARK_PULSE_TIMING": lambda st, c: isinstance(c, UseAttack) and _v124_pulse_applies(st, c),
    "UNRESOLVED_SELF_EXCLUDING_POWER_COPIES": lambda st, c: isinstance(c, UseAttack) and _v124_pulse_applies(st, c) and len(E.dark_pulse_holders(st, c.player)) > 1,
    "UNRESOLVED_TRANSFORM_ENERGY_COLOR_LIST": lambda st, c: isinstance(c, UseAttack) and _v124_copied_present(st),
    "UNRESOLVED_TRANSFORM_REVERT_KNOCKOUT_TIMING": lambda st, c: _v124_copied_present(st),
    "UNRESOLVED_TRANSFORM_BABY_AND_BASIC": lambda st, c: _v124_copied_present(st),
    "UNRESOLVED_SUPER_TRANSFORM_TARGET": lambda st, c: _v124_copied_present(st) or any(st.cards[p.card].card_id == V124_SUPER_DITTO for pl in st.players for p in pl.in_play()),
    "UNRESOLVED_SUPER_TRANSFORM_SOURCE_CHANGE": lambda st, c: _v124_copied_present(st),
    "UNRESOLVED_SUPER_TRANSFORM_COPIED_POWER": lambda st, c: _v124_copied_present(st),
    "UNRESOLVED_SUPER_TRANSFORM_SUPPRESSED_FORM": lambda st, c: _v124_copied_present(st),
    "UNRESOLVED_SUPER_TRANSFORM_ENERGY_COLORS": lambda st, c: _v124_copied_present(st),
    "UNSUPPORTED_TRANSFORM_COPIED_POWER": lambda st, c: _v124_copied_present(st),
    # v0.122（docs/unown-fossil-retreat-reactions-v0.122.md 10 章）: 「なにかの化石」から進化したポケモンの読み方（FE3）・［げんしのゆめ］の効果の消えた発生源（PM1）・使ったポケモン自身の段階（PM2）・
    # ［WANT］・［かせきのみちびき］・［かせきか］の対象なし（WT1・GU1・FS1）・ポケモンタワーの下の回収の力（PW5）・［つるでひっぱる］の時点（VL1）。どれも場から確かめる
    "UNRESOLVED_FOSSIL_EVOLVED_READING": lambda st, c: (isinstance(c, UseAttack) and bool(E.fossil_attack_bonuses(st)))
    or (isinstance(c, UsePokemonPower) and st.cards[st.find_pokemon(c.pokemon_id)[1].card].card_id == V122_KABUTO),
    "UNRESOLVED_PRIMAL_DREAM_SUPPRESSED": lambda st, c: isinstance(c, UseAttack) and bool(E.fossil_attack_bonuses(st)),
    "UNRESOLVED_PRIMAL_DREAM_DAMAGE_STEP": lambda st, c: isinstance(c, UseAttack) and any(r.pokemon_id == st.players[c.player].active.pokemon_id
                                                                                        for r, _ in E.fossil_attack_bonuses(st)),
    "UNRESOLVED_WANT_WITHOUT_TARGET": lambda st, c: isinstance(c, UsePokemonPower) and st.cards[st.find_pokemon(c.pokemon_id)[1].card].card_id == V122_W,
    "UNRESOLVED_FOSSIL_GUIDE_WITHOUT_TARGET": lambda st, c: isinstance(c, UsePokemonPower) and st.cards[st.find_pokemon(c.pokemon_id)[1].card].card_id == V122_OMANYTE3,
    "UNRESOLVED_FOSSILIZE_WITHOUT_TARGET": lambda st, c: isinstance(c, UsePokemonPower) and st.cards[st.find_pokemon(c.pokemon_id)[1].card].card_id == V122_KABUTO,
    "UNRESOLVED_POKEMON_TOWER_POWER_WITHOUT_EFFECT": lambda st, c: isinstance(c, UsePokemonPower) and E.discard_to_hand_suppressor(st) is not None
    and st.cards[st.find_pokemon(c.pokemon_id)[1].card].card_id in (V122_W, V122_OMANYTE3),
    "UNRESOLVED_VINE_PULL_TIMING": lambda st, c: isinstance(c, Retreat) and st.cards[st.players[c.player].active.card].card_id == V122_IVYSAUR,
    # v0.121（docs/hand-bench-attack-conditions-v0.121.md 10 章）: じごくのほのおでトラッシュする悪エネルギーの「+10」（DK1）・ロックオンの相手の防護（LO1）・ワザで手札から出すときの反応（HB1）・
    # ボロのつりざお（OR1）・カスミのてあて（MQ2）・ほかのカードのワザとしてのおおいびき（SQ1）・なきごえを受けたポケモンの特殊能力のダメージ（GN1）。どれも場から確かめる
    "UNRESOLVED_DISCARDED_ENERGY_DAMAGE_BONUS": lambda st, c: isinstance(c, UseAttack)
    and bool(E.attached_typed_energy_cards(st, _attacker(st, c), EnergyType.DARKNESS)),
    "UNRESOLVED_LOCK_ON_PROTECTED_TARGET": lambda st, c: isinstance(c, UseAttack) and "WaiveTailsFailureNextTurn" in _attack_and_copied_types(st, c),
    "UNRESOLVED_ATTACK_HAND_BENCH_REACTION": lambda st, c: isinstance(c, UseAttack) and bool(
        {"BenchOpponentHandBasicThenSwitchOrFail", "EachPlayerBenchesOpponentHandBasics"} & set(_attack_and_copied_types(st, c))),
    "UNRESOLVED_OLD_ROD_WITHOUT_TARGET": lambda st, c: isinstance(c, PlayTrainer) and st.cards[c.card].card_id == V121_OLD_ROD,
    "UNRESOLVED_MISTYS_CARE_WITHOUT_TARGET": lambda st, c: isinstance(c, PlayTrainer) and st.cards[c.card].card_id == V121_MISTYS_CARE,
    "UNRESOLVED_VIRTUAL_ASLEEP_ONLY_ATTACK": lambda st, c: isinstance(c, UseAttack) and "FailUnlessAsleepDamage" in _attack_and_copied_types(st, c),
    "UNRESOLVED_GROWL_NON_ATTACK_DAMAGE": lambda st, c: isinstance(c, UsePokemonPower),
    # v0.120（docs/fossil-basic-virtual-attacks-v0.120.md 10 章）: 2 進化ポケモンの進化前のいちばん下のカードのワザ（PE1）・りゅうのいでんしで選ぶワザの条件（PE2）・許可で使えるワザを
    # 「持っているワザ」として選ぶ（VP1）・ESPのコピー先のコイン（EC1）。どれも場から確かめる
    "UNRESOLVED_PRE_EVOLUTION_ATTACK_STAGE": lambda st, c: len(_attacker(st, c).evolution_stack) >= 2,
    "UNRESOLVED_PRE_EVOLUTION_ATTACK_CONDITIONS": lambda st, c: "CopyAttackFromSource" in _attack_and_copied_types(st, c) and bool(_attacker(st, c).evolution_stack),
    "UNRESOLVED_PERMITTED_ATTACK_HELD": lambda st, c: _v120_permission_in_play(st),
    "UNRESOLVED_ESP_COPIED_ATTACK_COINS": lambda st, c: bool(E.esp_cards(st, _attacker(st, c))),
    "UNRESOLVED_REVIVED_BASIC_DEVOLVED": lambda st, c: any(p.basic_entry is not None and p.evolution_stack for side in st.players for p in side.in_play()),
    # v0.120: 既存の MH1（v0.48）。［へんしん］のメタモンが、写す相手（相手の対戦ポケモン）をきぜつさせると、メタモンの最大HPが印刷の HP にもどり、のっているダメージ以下になる。
    # F120 対 D49 で初めて届いた（ワザの前に場から確かめる: ワザを使うのがはたらく［へんしん］のメタモンで、のっているダメージがメタモンの印刷の HP 以上）
    "UNRESOLVED_MAX_HP_DROP": lambda st, c: ((st.cards[_attacker(st, c).card].card_id == DITTO and E.transform_defender(st, _attacker(st, c)) is not None)
                                             or _v124_copied_present(st))  # v0.124: ［すごいへんしん］のメタモンも
    and _attacker(st, c).damage >= st.card_def(_attacker(st, c).card).hp,
    # v0.92（docs/power-suppression-lasting-locks-v0.92.md 8 章）: やみのはどうで、相手の場にワザの効果を受けない特殊能力のポケモン（DW2）・HP 以上になるポケモンのきぜつの時の
    # 特殊能力（DW3）。どれもワザがやみのはどう（相手のワザとして使うものも）のときだけ
    "UNRESOLVED_DARK_WAVE_PROTECTED_POKEMON": lambda st, c: "DamageThenFieldPowerSuppression" in _attack_and_copied_types(st, c),
    "UNRESOLVED_DARK_WAVE_KNOCKED_OUT_POWER": lambda st, c: "DamageThenFieldPowerSuppression" in _attack_and_copied_types(st, c),
    # v0.91（docs/marker-check-field-reset-v0.91.md）: ハイパーテクスチャーで色マーカーののっていないポケモンを選ぶ（HX1）・かみなりショックの相手の対戦ポケモンにひらいしんマーカー
    # （HR1）・オールクリアの「その他の効果」（ZC1）・特殊能力で持ったワザ（ZC2）・場のなにかの化石（ZC3）。どれも場から確かめる
    "UNRESOLVED_HYPER_TEXTURE_UNMARKED_TARGET": lambda st, c: not all(_v091_marked(st, 1 - c.player, "color")),
    "UNRESOLVED_LIGHTNING_BOLT_DEFENDER_UNITS": lambda st, c: st.players[1 - c.player].active is not None and any(
        m.kind == "lightning_rod" for m in st.players[1 - c.player].active.markers),
    "UNRESOLVED_ALL_CLEAR_OTHER_EFFECTS": lambda st, c: any(p.type_shift is not None for q in st.players for p in q.in_play()) or any(
        r.kind in ("bench_attack_damage_prevention", "power_suppression", "opponent_power_suppression") and r.expires_turn > st.turn_number for r in st.trainer_effects),
    "UNRESOLVED_ALL_CLEAR_ATTACK_SOURCE": lambda st, c: current_form(st, _attacker(st, c)).kind != "printed",
    "UNRESOLVED_ALL_CLEAR_FOSSIL_IN_PLAY": lambda st, c: any(st.in_play_def(uid).play_role == "fossil" for q in st.players for p in q.in_play() for uid in p.cards()),
    # v0.81: きぜつの判定の窓できあいのハチマキ・学習装置がほかの効果と重なる（G40）・きあいのハチマキの処理の時点（FB1）・はんげきのツメのダメージカウンターでワザを使った
    # ポケモンもきぜつし勝ち負けが変わる（C18）。どれも場にそのどうぐがついているときだけ
    "UNRESOLVED_KO_PREVENTION_ORDER": lambda st, c: _v081_tools_on(st, (0, 1), ("FocusBand", "ExpAll")),
    "UNRESOLVED_FOCUS_BAND_TIMING": lambda st, c: _v081_tools_on(st, (0, 1), ("FocusBand",)),
    # v0.110: 残りHPがなくなっても「きぜつ」しない効果（こらえる・こうてつか）の、残りHPを 10 にする時点（KS1）・きぜつの判定の効果との重なり（KS2）。場のどれかのポケモンが、
    # 今はたらいている効果を持つときだけ（ログから組み立てず、場の持続する効果の期間で確かめる）
    "UNRESOLVED_KO_SURVIVAL_TIMING": lambda st, c: _v110_survival_on(st),
    "UNRESOLVED_KO_SURVIVAL_OVERLAP": lambda st, c: _v110_survival_on(st),
    # v0.111: シンクロウェーブを、自分と相手の対戦ポケモンについているカードの枚数が違うときに宣言した（通常の不正な操作。研究上の未解決ではない）。道具が場の枚数を別に数え、違うときだけ
    # 認める（エンジンの問い合わせを読まない）
    "ENERGY_CARD_COUNTS_DIFFER": lambda st, c: _v111_counts_differ(st, c),
    # v0.87: 相手の場の［ショックボム］（受けたワザのダメージで、両方の対戦ポケモンに特殊能力のダメージ。ワザを使ったポケモンもきぜつし勝ち負けが変わる）も
    # v0.99: この組の一覧で、ほかの止める関数より先に聞くので、相手の対戦ポケモンのはたらいている「はんげき」・［わるいねぞう］（v0.10・v0.17b の止める関数が確かめる場面）も含める
    # （T99 対 K97 で、ねむりの R団のカビゴンの［わるいねぞう］で止まった。それまでの組では起こらなかった）
    "UNRESOLVED_COUNTERATTACK_DOUBLE_KNOCKOUT": lambda st, c: _v081_tools_on(st, (1 - c.player,), ("CounterClaw",)) or _v087_shock_blast_on(st, 1 - c.player)
    or counter_working(st, st.players[1 - c.player].active) or restless_working(st, st.players[1 - c.player].active),
    # v0.99: ブラッキーの「だましうち」（「その他の効果」に関係なく。除く範囲の書き方のない型）で、どの選べるポケモンでも読み方の結果が変わり、宣言の前に止まる（FA1。相手に控えが
    # いない・控えが見えない壁などで守られている）。ワザがその型のときだけ（T99 対 K97 で起こった。それまでの組では起こらなかった）
    "UNRESOLVED_IGNORED_EFFECTS_SCOPE": lambda st, c: type(_attack_effect_of(st, c)).__name__ == "ChooseOpponentPokemonDamageIgnoringEffects",
    # v0.68: 相手のうらのカード（マチスの秘策）を 2 枚以上、効果の対象にするコマンド（控え全員へのダメージなど）は、受け付けるかを本当のカードによらないものにできない
    # （エンジンの未対応。docs/final-pmcg-cards-v0.68.md 5.3 節）。コマンドを出したプレイヤーの相手の場に、うらのカードが 2 枚以上ある
    "UNSUPPORTED_SECRET_PLAN_IDENTITIES": lambda st, c: sum(
        1 for q in st.players[1 - c.player].in_play() if st.is_face_down(q)) >= 2,
    # v0.49: ［へんしん］のメタモンが、タイプのエネルギーの数を数える・トラッシュするワザを使う（どの色としても数えるかが決まらない。TE1）
    "UNRESOLVED_TRANSFORM_ENERGY_COUNT": lambda st, c: any_color_energy(st, _attacker(st, c)),
    # HC1。v0.114: 相手のバトル場のベイビィポケモンのルールのコイン（宣言のあと・説明の処理の前）も、トラッシュの時点が決まらないワザのコイン
    "UNRESOLVED_DISCARD_ENERGY_TIMING": lambda st, c: _attacker(st, c).conditions.confused or E.baby_rule_applies(st, c.player),
    # HC4（第4弾のコダック・v0.34 のシャワーズの「みずでっぽう」）
    "UNRESOLVED_EXTRA_ENERGY_COLORLESS": lambda st, c: "ExtraEnergyDamageMixed" in _attack_and_copied_types(st, c),  # v0.62: オウムがえしで出すワザも
    # HC3。v0.80: 相手の対戦ポケモンについているエフェクトガード（効果の要素だけを受けない。ダメージの要素も無効なら同じ問い）
    "UNRESOLVED_PREVENTED_EFFECT_COIN": lambda st, c: attack_barrier(st, _defender(st, c)) is not None
    or bool(__import__("kyuura_engine.effects", fromlist=["effect_guards"]).effect_guards(st, _defender(st, c)))
    # v0.85: やさしいカイリューの「ひかりのはどう」（v0.84。相手のワザの効果の要素だけを受けない。v0.84 の組では、コインが効果だけを決めるワザで当たらなかった）
    or __import__("kyuura_engine.persistent", fromlist=["attack_effect_guard"]).attack_effect_guard(st, _defender(st, c)) is not None
    # v0.86: スイクンの［クリスタルボディ］（相手のワザのダメージ以外の効果を受けない。特殊状態・ガス・スタンウェーブでは、はたらかない）
    or _v086_crystal_body(st, _defender(st, c))
    # v0.103: ミュウの［ニュートラルシールド］（相手の進化ポケモンからのワザを受けない。ワザを使うポケモンの今の姿で決まる）
    or _v103_neutral_shield(st, c)
    # v0.117: アンノーンQ の［QUICKEN］の「おもて」の効果（次の相手の番、使ったプレイヤーの場の「アンノーン」全員がワザによるダメージや効果を受けない）
    or bool(E.group_attack_immunities(st, 1 - c.player, _defender(st, c))),
    "UNRESOLVED_DESTINY_BOND_KNOCKOUT": lambda st, c: destiny_bond(st, _defender(st, c)) is not None,  # HC2
    # しっぽをふる。v0.40: すごむ（効果を与えたポケモンがバトル場にいる間）
    "ATTACK_PREVENTED": lambda st, c: (cannot_attack(st, _attacker(st, c)) is not None
                                       or cannot_attack_while_source_active(st, _attacker(st, c)) is not None
                                       # v0.119: 相手のバトル場のわるいオーダイルの［いあつ］で、ベイビィポケモンはワザを使えない
                                       or bool(E.scared_by(st, c.player, _attacker(st, c)))),
    "UNRESOLVED_DISCARD_DECK_SHORT": lambda st, c: (  # HC6: マグマふんしゅつ（自分の山札 5 枚未満）・やまやき（相手の山札 0 枚）
        (_attack_definition(st, c).id, c.attack_index) in ((BLAINES_MAGMAR, 1), ("GD5-011", 1)) and len(st.players[c.player].deck) < 5
        or (_attack_definition(st, c).id, c.attack_index) == (MOLTRES, 0) and not st.players[1 - c.player].deck
        # v0.95: マグマラッシュ・やまくずし（自分の山札が説明の枚数より少ない）
        or _v095_mill_count(st, c) is not None and len(st.players[c.player].deck) < _v095_mill_count(st, c)
        # v0.115: やまくだき（相手の山札が、使うポケモンの「闘」の基本エネルギーカードの枚数より少ない）
        or _v115_mill_short(st, c)),
    # v0.95（FV1。v0.73 の熱血!と同じ問い）: 山札の上からトラッシュしたカードの「「X」エネルギーカード」を数える・手札に加えるワザで、自分の山札・サイドにレインボーエネルギーがある
    # （やまくずしは場のポケモンタワーで手札に加える部分が消えるなら当たらない）
    "UNRESOLVED_FERVOR_RAINBOW_ENERGY": lambda st, c: _v095_mill_count(st, c) is not None and bool(rainbow_cards_in(
        st, (*st.players[c.player].deck, *(uid for uid in st.players[c.player].prizes if uid is not None)))) and not (
        isinstance(_attack_effect(st, c), DamageThenMillReturnTypeEnergy) and discard_to_hand_suppressor(st) is not None),
    # v0.95（LT1）: みらいよち（ネイティオ）で、自分の山札も相手の山札も 3 枚より少ない
    "UNRESOLVED_ATTACK_DECK_TOP_SHORT": lambda st, c: isinstance(_attack_effect(st, c), ArrangeDeckTopExactlyEffect) and all(
        len(p.deck) < _attack_effect(st, c).count for p in st.players),
    # ぼーっとする（v0.49: ワザを印刷したカードで見る。［へんしん］のメタモンがヤドンと同じカードのとき）
    "NO_DAMAGE_COUNTERS": lambda st, c: _attack_definition(st, c).id == SLOWPOKE and _attacker(st, c).damage == 0,
    "UNRESOLVED_COPIED_ATTACK": lambda st, c: _copier(st, c),  # HC9
    # v0.100: SK1（スケッチを使うポケモンが前の相手の番の途中か今の番に場に出た・先攻の最初の番）・SK2（前の相手の番のワザがまねたワザ）・PSG1（ねむりの相手の、前の自分の番の
    # やみのひとみが効果だけを無効にする効果で無効になった・まねたワザだった）。どれもログと場から確かめる
    "UNRESOLVED_SKETCH_PRESENCE": lambda st, c: "UseLastOpponentAttack" in _attack_and_copied_types(st, c) and (
        st.turn_number == 1 or _attacker(st, c).current_form_turn >= st.turn_number - 1),
    "UNRESOLVED_SKETCH_COPIED_ATTACK": lambda st, c: "UseLastOpponentAttack" in _attack_and_copied_types(st, c) and (
        (_logged_turn_attack(st, st.turn_number - 1) or [None, None, None])[2] is not None),
    "UNRESOLVED_PERISH_SONG_RECEIVED_ATTACK": lambda st, c: "KnockOutIfAsleepAndReceived" in _attack_and_copied_types(st, c) and _v100_night_eyes_unclear(st, c),
    "UNSUPPORTED_COPIED_ATTACK": lambda st, c: _copier(st, c),
    # v0.101: KP2（［KEEP］でなくなるトラッシュだけを決めるコイン）・KP3（［KEEP］のはたらくアンノーンからはがしたカードを、受けない控えのためにトラッシュする）。場から確かめる
    # （エンジンの ``energy_discard_void`` を読まない）
    "UNRESOLVED_KEEP_VOIDED_DISCARD_COIN": lambda st, c: _v101_keep_coin_expected(st, c),
    "UNRESOLVED_KEEP_DETACHED_ENERGY_DISCARD": lambda st, c: "DamageThenMoveOpponentEnergyToBench" in _attack_and_copied_types(st, c)
    and _v101_keep_on(st, 1 - c.player, st.players[1 - c.player].active),
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
    # v0.116: キョウのコクーンの「どくどくえき」（SpecialPoisonOnHeadsWithoutDamage。v0.44）も（C116 対 E50 の開発中の局で、退化スプレーでもどったキョウのコクーンが、通常のどくの
    # 相手に使って初めて起こった。エンジンは正しく止め、この確かめの一覧に型がなかった）
    "UNRESOLVED_SPECIAL_POISON_OVERWRITE": lambda st, c: (type(_attack_effect(st, c)).__name__ in ("DamageAndSpecialPoison",
                                                                                              "DamageThenSpecialPoisonOnHeads",  # v0.39 のどくどくガス
                                                                                              "SpecialPoisonOnHeadsWithoutDamage")
                                                          and _defender(st, c).conditions.poison is not None
                                                          and _defender(st, c).conditions.poison.damage != _attack_effect(st, c).poison_damage)
    # v0.119: ツボツボの「どくどくエキス」（ダメージカウンターの数を倍にするどく。相手のワザとして使うときも）で、相手が性質の違うどく状態（量・かける数のどちらかが違う）
    or ("ToxicPoisonOnHeadsWithoutDamage" in _attack_and_copied_types(st, c) and _defender(st, c).conditions.poison is not None
        and (_defender(st, c).conditions.poison.damage, _defender(st, c).conditions.poison.multiplier) != (10, 2)),
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
    # v0.89: タケシのイシツブテのロングショット（「(相手に控えがいないとき、このワザは使えない)」）
    # v0.90: ほねこんぼう（「このカードに「ほねカウンター」がのっている時だけ、使える」）・たべる（「…が2つのっている時、このワザは使えない」）。数えるのはワザを使うポケモンのもの
    "MARKER_REQUIRED": lambda st, c: (type(_attack_effect(st, c)).__name__ == "DamageThenRemoveOwnMarkerParalyzeOnHeads"
                                      and marker_count(_attacker(st, c), _attack_effect(st, c).kind) == 0),
    "MARKER_LIMIT": lambda st, c: (type(_attack_effect(st, c)).__name__ == "MarkSelfUpToLimit"
                                   and marker_count(_attacker(st, c), _attack_effect(st, c).kind) >= _attack_effect(st, c).limit),
    "NO_OPPONENT_BENCH": lambda st, c: ((type(_attack_effect(st, c)).__name__ == "ChooseOpponentBenchDamage" and _attack_effect(st, c).requires_bench
                                         or type(_attack_effect(st, c)).__name__ in ("SwitchOpponentThenDamage", "ReturnOpponentActiveToDeck",
                                                                                     "SwitchOpponentActiveOnHeads", "ChooseOpponentBenchThenCoinDamage",
                                                                                     "SwitchOpponentActiveRequiringBench"))  # v0.94: このゆびとまれ
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
    # v0.116: はらだいこ（山札の基本エネルギーカードが 1 枚）
    "UNRESOLVED_STATED_CARDS_SHORT": lambda st, c: (_hand_return_short(st, c) or _exact_bench_short(st, c) or _surprise_short(st, c) or _v113_attract_short(st, c)
                                                    or _v116_belly_drum_short(st, c)
                                                    # v0.120: たつまき（相手のエネルギーカードが 1 枚で、「おもて」2 枚ぶんを選べないことがある）
                                                    or _v120_twister_short(st, c)
                                                    # v0.119: おにびあつめ（v0.75。W119 対 F75 で初めて起こった）。トラッシュの「炎」の基本エネルギーカードが 1 枚以上でコインの枚数より少ない
                                                    or _v119_recover_by_heads_short(st, c)),
    # v0.113: ゆうでんの山札のレインボーエネルギー（「雷」エネルギーカードが「おもて」の数より少ないとき、それを選ばないと足りない）・ダークフレイムのトラッシュのレインボーエネルギー
    # （RB2）。道具が山札・トラッシュのカードを別に数えて確かめる
    "UNRESOLVED_RAINBOW_ATTACH_AS_TYPE": lambda st, c: _v113_attract_short(st, c, rainbow=True) or _v113_discard_rainbow(st, c) or _v113_static_rainbow(st, c),
    # v0.44: 場に出てから 1 度しか使えないワザ（ネギでたたく・りゅうのきおく・ひっさつばり）を、このポケモンがもう使った（場のポケモンの記録 ``attacks_used_once``）
    "ATTACK_ALREADY_USED": lambda st, c: (_attacker(st, c).card, c.attack_index) in _attacker(st, c).attacks_used_once,
    # v0.45: ワザを使うポケモンが手順 4 の効果を 2 つ以上受けている（AC13。スミをかけるの「それ以後」の効果が重なる）
    # v0.60: カスミのギャラドスの［はんこう］も手順 4 の効果として数える
    "UNRESOLVED_MULTIPLE_ATTACK_CHECKS": lambda st, c: len(attack_coin_checks(st, _attacker(st, c))) + len(attack_rebellion_powers(st, _attacker(st, c))) >= 2,
    # v0.60: サンダーストーム（自分のワザ・相手のワザとして使うワザ）で、はたらいている「とうめい」の相手の控えポケモンのあとにほかの控えがいる（TS1）
    "UNRESOLVED_BENCH_COIN_TRANSPARENCY_ORDER": lambda st, c: _thunderstorm_transparency(st, c) or _v115_mow_transparency(st, c),  # v0.115: なぎたおすも
    # v0.60: 控えにもダメージ・効果を与えるワザ（どくのきりなど）で、相手の場に、はたらいている「とうめい」のポケモンが 2 匹以上いる（T27。v0.60 の M60 で初めて起こった）
    "UNRESOLVED_TRANSPARENCY_COIN_ORDER": lambda st, c: sum(evasion_power(st, p) is not None for p in st.players[1 - c.player].in_play()) >= 2,
    # v0.45: 相手の対戦ポケモンが返す効果（クロスカウンター。ほのおのかべ・こうらがえしも）を持ち、そろってきぜつしうる（W24・S37）
    "UNRESOLVED_RETALIATION_DOUBLE_KNOCKOUT": lambda st, c: retaliation(st, _defender(st, c)) is not None
    # v0.119: 「どくをだす」（相手のワザのダメージを受けたときの、相手の控え全員へのダメージ）も同じ問い（W24・S37）。今の番にはたらく効果を持つ
    or any(e.kind == "secrete_poison" and e.created_turn + 1 == st.turn_number for e in _defender(st, c).persistent_effects),
    # v0.48: ［へんしょく］で変えた色の読み方が 2 つある（使った番のあと・ベンチにもどったあと・この力が消えている）場のポケモンがいる（VS1。読み方で結果が変わるときだけ
    # 止まる。止まらない場合は場から確かめられないので、止まったときに読み方が 2 つあるポケモンがいることだけを確かめる）
    "UNRESOLVED_SHIFT_COLOR_DURATION": lambda st, c: any(len(type_readings(st, p)) > 1 for pl in st.players for p in pl.in_play()),
    # v0.50: たいかビーム（自分のワザ・相手のワザとして使うワザ）で、自分・相手の場の進化ポケモンがどれも「ばける」でのせたカードのポケモン（DV5）
    # v0.116: げんしのしずく（相手の場の進化ポケモンがどれも「ばける」かベイビィから進化したたねポケモン）・さいせい（「ばける」の自分）
    "UNRESOLVED_DEVOLUTION_TARGET_DISGUISED": lambda st, c: (_all_devolution_targets_disguised(st, c) or _v116_primal_drop_stopped(st, c)
                                                             or _v116_regenerate_disguised(st, c)),
    # v0.116（NB2）: げんしのしずくで、相手の場の進化ポケモンがどれもベイビィから進化したたねポケモンか「ばける」（候補の最初がベイビィから進化したたねポケモン）
    "UNRESOLVED_NEO_TEXT_EVOLUTION_CARD_BABY": lambda st, c: _v116_primal_drop_stopped(st, c),
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
    # v0.87: 1 つのワザで「ダメージを受けたとき」の効果が 2 つ以上はたらく（C34/C35。わるいマグカルゴの「かえんだん」で対戦ポケモンと控えのコクーンの［どくのたいえき］など）。
    # 場から確かめる（相手の場に「ダメージを受けたとき」の送る効果を持つポケモンがいる）
    "UNRESOLVED_MULTIPLE_DAMAGE_TRIGGERS": lambda st, c: _v087_damage_triggers(st, 1 - c.player) >= 1,
    # v0.88: 色を変える効果（［せんすい］・［エナジーコンバーター］の記録・こうごうせい）で、色の読み方が 2 つ以上になる（CE1・CE2）・カードとしての色が決まらない（CE3）。
    # 場から確かめる（続くかが決まらない記録がある・色を変える効果がはたらいている）
    "UNRESOLVED_COLOR_EFFECT_CONTINUATION": lambda st, c: any(color_effect_status(st, r) == "ambiguous" for r in st.color_effects),
    "UNRESOLVED_COLOR_REPLACEMENT_ORDER": lambda st, c: _v088_color_layer_on(st),
    "UNRESOLVED_COLOR_CHANGED_ENERGY_CARD": lambda st, c: _v088_color_layer_on(st),
    # v0.114: ベイビィポケモンのルールのコインと手順 4・5（BQ1）・ベイビィの姿のメタモン（BX1）・特殊能力の消えたポケモン（HV1）。関数は下の V0_114_STOPS（場から確かめる）
    "UNRESOLVED_BABY_RULE_COIN_ORDER": lambda st, c: V0_114_STOPS["UNRESOLVED_BABY_RULE_COIN_ORDER"](st, c),
    "UNRESOLVED_TRANSFORM_BABY": lambda st, c: V0_114_STOPS["UNRESOLVED_TRANSFORM_BABY"](st, c),
    "UNRESOLVED_STOPPED_POWER_HOLDER": lambda st, c: V0_114_STOPS["UNRESOLVED_STOPPED_POWER_HOLDER"](st, c),
    # v0.115: いしなだれを、相手に控えがいないときに使う（選べるのが目安のダメージを受けた相手の対戦ポケモンだけ。SLD1）。関数は下の V0_115_STOPS（場から確かめる）
    "UNRESOLVED_CHOSEN_ACTIVE_EXTRA_DAMAGE": lambda st, c: V0_115_STOPS["UNRESOLVED_CHOSEN_ACTIVE_EXTRA_DAMAGE"](st, c),
    # v0.116: しこみどく・エナジーショックの効果を受けたポケモンへのワザの付け替え（AT1）・はらだいこなどでつけるときのマヒと［ほのおでかいふく］（エンジンの未対応）。関数は下の
    # V0_116_STOPS（場から確かめる）
    "UNRESOLVED_ATTACH_TRIGGER_SCOPE": lambda st, c: V0_116_STOPS["UNRESOLVED_ATTACH_TRIGGER_SCOPE"](st, c),
    "UNSUPPORTED_ATTACH_TRIGGER_ORDER": lambda st, c: V0_116_STOPS["UNSUPPORTED_ATTACH_TRIGGER_ORDER"](st, c),
}


def _v088_color_layer_on(state) -> bool:
    """v0.88: 場に、エネルギーの色を変える効果（［エナジーコンバーター］の記録・はたらいているこうごうせい）があるか。"""
    return any(r.kind == "energy" for r in state.color_effects) or any(
        photosynthesis_on(state, p) for player in state.players for p in player.in_play())


def _v087_damage_triggers(state, player):
    """v0.87: プレイヤー ``player`` の場の、「ダメージを受けたとき」の窓の送る効果（はんげき・［どくのたいえき］・［ショックボム］・［ぶんれつ］など）を持つポケモンの数。"""
    from kyuura_engine.resolution import catalog as C
    from kyuura_engine.resolution.events import Window
    return sum(any(i.definition.timing is C.Timing.DEFER for i in C.in_window(state, Window.DAMAGE_RECEIVING, player, p))
               for p in state.players[player].in_play())


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
    # v0.116: 相手の対戦ポケモンの［ニュートラルシールド］（進化ポケモンのワザを受けない。P116 対 M103 の開発中の局で、フーディンのトランスダメージで初めて起こった）
    protected = protected or _v086_power_working(state, defender, E.EvolvedOpponentAttackImmunity) and E.is_evolution_in_play(state, attacker)
    # v0.116: トランスダメージ（自分のダメージカウンターをすべて相手にのせかえる）も
    return bool(names & {"MoveOwnCountersToOpponent", "SwapCountersOnHeads", "DiscardAllEnergyThenMoveAllSelfCountersToOpponent"}) and protected


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
                                     "DamageThenReturnSelfToHandOnHeads",  # v0.44: スターブーメラン（手札にもどす。RD9 と同じ問い）
                                     "DamageThenReturnSelfAndEnergyToHand"):  # v0.117: ぱっときえる（自分とエネルギーカードを手札にもどす。RD9 と同じ問い）
            found.append((definition.id, definition.attacks[index]))
        elif type(effect).__name__ == "DamageThenBubbleJump" and state.players[command.player].bench:
            # v0.84: バブルジャンプ（「おもて」なら手札にもどす。控えがいなければ効果はすべてなくなるので、RD9 にならない）
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


def _v093_probe(state, tried, counts):
    """v0.93: バトル場のポケモンが「バトル場をはなれられない」効果を受けているはたらく番に、1 番に 1 度ずつ「にげる」と手札の入れ替えのトレーナー（ポケモンいれかえ・ポケモン回収・
    ワープポイント・マチス）を試す（エネルギー・コインの前の拒否 LEAVE_ACTIVE_PREVENTED・使う前の AL2、ワープポイントはもう一方の側だけ入れ替える）。効果がなければ何もしないので、前の版の
    組の結果は変わらない。ねむり・マヒとにげるエネルギーが足りないときは「にげる」を試さない。はなれられない効果と別の理由で使う前に止まる・拒否されるトレーナー（マチスの
    BENCH_FULL・LS1 など）は使わず ``v093_<カード>_not_playable_<コード>`` に数える。"""
    from kyuura_engine.persistent import leave_lock

    player = state.current_player
    p = state.players[player]
    active = p.active
    if active is None or not p.bench or state.is_face_down(active):
        return None
    try:
        lock = leave_lock(state, player, active)
    except UnsupportedError:
        lock = True  # JC1・JC2（決められない）。「にげる」を試して止まることを確かめる
    if lock is None:
        return None
    if ("v093_retreat", state.turn_number) not in tried and not (active.conditions.asleep or active.conditions.paralyzed):
        tried.add(("v093_retreat", state.turn_number))
        cost = retreat_cost(state, player).maximum
        if len(active.energy) >= cost:
            counts["v093_retreat_probe"] += 1
            return Retreat(player, tuple(active.energy[:cost]), p.bench[0].card)
    for card_id in (SWITCH, "PMCG1-092", "PMCG6-080", "PMCG5-092"):
        held = next((uid for uid in p.hand if state.cards[uid].card_id == card_id), None)
        if held is not None and ("v093_trainer", card_id, state.turn_number) not in tried and ("max_hp_drop_card", held) not in tried:
            tried.add(("v093_trainer", card_id, state.turn_number))
            command = PlayTrainer(player, held)
            real = _V052_REAL.get("state")
            try:
                apply_command(real if real is not None and real.turn_number == state.turn_number and real.decision == state.decision else state, command)
            except (IllegalActionError, UnsupportedError) as error:
                if error.code not in V093_LEAVE_CODES:
                    counts[f"v093_{card_id}_not_playable_{error.code}"] += 1
                    continue
            counts[f"v093_trainer_probe_{card_id}"] += 1
            return command
    return None


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
        apply_command(_v052_real(state), command)
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
            apply_command(_v052_real(state), alternative)
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
        payer = active if option.payer is None else state.find_pokemon(option.payer)[1]  # v0.120: ［にんぎょうつかい］はスリーパーが払う
        if not attack_cost_payable(state, payer, state.definitions[option.card_id].attacks[option.attack_index]):
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
        # v0.114: 出せるカードは、そのトレーナーの説明の版の「たねポケモン」（どちらもネオより前のカード。ベイビィポケモンカードをふくむ。effects.TEXT_ERAS）
        if (f"v051_{label}", state.turn_number) in tried or not bench_from_discard_candidates(state, (owner,), E.text_era(card_id)):
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


def _v052_real(state):
    """v0.117: 手順の中の確かめ（``apply_command`` を写しの上で試す）に渡された状態が、この手順の呼び出しで作った手札を隠した写し（``_V052_REAL["view"]``。v0.46〜v0.48 の
    手順）なら本当の状態、ほかは渡した状態のまま。写しで ``apply_command`` を呼ぶと、隠したカードがどこにもないので不変条件で止まる（v0.117 の組で、［でんせつのからだ］で
    止まったトレーナーを隠した番に、v0.61・v0.66 の手順の確かめが写しを使って内部エラーになった）。写しでなければ動きは変わらない（写しの確かめは、前の版では必ず止まっていた）。"""
    if state is _V052_REAL.get("view"):
        return _V052_REAL["state"]
    return state


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
        apply_command(_v052_real(state), command)
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
        apply_command(_v052_real(state), coined)
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
        apply_command(_v052_real(state), command)
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
        apply_command(_v052_real(state), command)
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
            apply_command(_v052_real(state), command)
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
        apply_command(_v052_real(state), attach)
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
        apply_command(_v052_real(state), command)
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
            apply_command(_v052_real(state), trainer)
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
        apply_command(_v052_real(state), trainer)
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
                apply_command(_v052_real(state), retreat)
            except (IllegalActionError, UnsupportedError) as error:
                counts[f"v067_retreat_rejected_{error.code}"] += 1
            else:
                counts["v067_retreat_from_face_down"] += 1
                return retreat
        if ("v067_attack", state.turn_number) not in tried:
            tried.add(("v067_attack", state.turn_number))
            attack = UseAttack(player, 0)
            try:
                apply_command(_v052_real(state), attack)
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
                apply_command(_v052_real(state), command)
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
            apply_command(_v052_real(state), command)
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


def _v083_decision(state, counts):
    """v0.83 のワザの決定への答え（元の手順より先に答える。相手プレイヤーの決定（おたがいのプレイヤーが選ぶワザの段階 1）にも答える）。選べるものを順に回し、選ぶ数は
    決定の上限・下限から交互に選ぶ。受け付ける答えだけを選ぶ（選ぶと止める答え（TE2・HC7 など）は選ばない）。決定の続きの情報のワザが v0.83 のポケモンのワザでなければ何もしない。"""
    d = state.decision
    if d is None or d.resume != "attack":
        return None
    use = d.context_value("use")
    copied = d.context_value("copied")
    card_id = copied[0] if copied else (use[2] if use else None)
    if card_id not in V0_83:
        return None
    key = f"v083_{card_id}_{d.kind}"
    seen = counts[f"{key}_seen"]
    counts[f"{key}_seen"] += 1
    rotated = list(d.options[seen % len(d.options):]) + list(d.options[:seen % len(d.options)]) if d.options else []
    sizes = [d.max_choices, d.min_choices, max(d.min_choices, 1)] if seen % 2 == 0 else [d.min_choices, max(d.min_choices, 1), d.max_choices]
    candidates = []
    if d.kind == "select_draw_count":
        candidates = [(o,) for o in rotated]
    else:
        candidates = [tuple(rotated[:n]) for n in sizes] + [(o,) for o in d.options]
    for choices in candidates:
        if d.min_choices <= len(choices) <= d.max_choices and _v052_accepted(state, ResolveDecision(d.player, d.id, choices)):
            counts[f"{key}_{len(choices)}"] += 1
            return ResolveDecision(d.player, d.id, choices)
    counts[f"{key}_no_accepted_answer"] += 1
    return None


def v083_uses(state):
    """v0.83: ログから数えた v0.83 のカードの動き（ない局では空）。``attack_<id>#<位置>``（ワザを使った）・``attack_failed_<理由>``・``draw_<段階>``（きんいろのうろこで引いた・
    引かなかった）・``recover_<プレイヤー>``・``recover_declined``・``discard_to_deck``（すくいあげる）・``webbing_taken``（みずかきで手札に加えた基本エネルギーカード）・
    ``reflect_check_<結果>``・``reflect_damage``・``reflect_skipped``（リフレクトシールド）・``status_<状態>``（v0.83 のワザが与えた特殊状態）・``heal``（とりのぞいた回数）・
    ``attach_from_hand``（ひざしをかえす）・``self_damage``・``bench_damage``・``returned_<理由>_<原因>``（リサイクルエネルギー・エコロジムでもどしたエネルギーカード）。"""
    counts = Counter()
    if not any(state.cards[uid].card_id in V0_83 for uid in state.cards):
        return counts
    current = None
    for e in state.log:
        kind = e["kind"]
        effect = e.get("effect")
        ours = isinstance(effect, str) and effect.split("#")[0] in V0_83
        if kind == "attack":
            current = effect if ours else None
            if ours:
                counts[f"attack_{effect}"] += 1
        elif kind == "turn_end":
            current = None
        elif kind == "attack_failed" and ours:
            counts[f"attack_failed_{e.get('reason')}"] += 1
        elif kind == "draw" and current is not None and current in ("neo3-022#0", "PRN-046#0"):
            counts["draw_drawn"] += 1
        elif kind == "attack_draw_declined":
            counts[f"draw_{e['reason']}"] += 1
        elif kind == "each_player_recover":
            counts[f"recover_{'attacker' if e['player'] == e['attacker'] else 'opponent'}"] += 1
        elif kind == "each_player_declined":
            counts[f"recover_{e['reason']}"] += 1
        elif kind == "each_player_discard_to_deck":
            counts["discard_to_deck"] += 1
        elif kind == "reveal_from_deck" and ours:
            counts["revealed_from_deck"] += 1
        elif kind == "reflect_shield_check":
            counts[f"reflect_check_{e['result']}"] += 1
        elif kind == "reflect_shield_damage":
            counts["reflect_damage"] += 1
        elif kind == "reflect_shield_skipped":
            counts["reflect_skipped"] += 1
        elif kind == "special_condition" and ours:
            counts[f"status_{e['condition']}"] += 1
        elif kind == "attack_heal" and ours:
            counts["heal"] += 1
        elif kind == "attach_energy_from_hand" and ours:
            counts["attach_from_hand"] += 1
        elif kind == "damage" and current is not None and e.get("target") == "self":
            counts["self_damage"] += 1
        elif kind == "damage" and current is not None and e.get("target") in ("opponent_bench", "self_bench"):
            counts["bench_damage"] += 1
        elif kind == "energy_returned_to_hand" and current is not None:
            for reason in e["reasons"]:
                counts[f"returned_{reason}_{e['cause']}"] += 1
    return counts


def _v084_source(state, d):
    """v0.84: 決定のもとになった v0.84 のカードの id（ワザ・特殊能力・トレーナー。なければ None）。"""
    if d.resume == "attack":
        use = d.context_value("use")
        copied = d.context_value("copied")
        return copied[0] if copied else (use[2] if use else None)
    if d.resume == "power":
        use = d.context_value("use")
        return use[2] if use else None
    if d.resume == "trainer" and state.trainer_in_use is not None:
        return state.cards[state.trainer_in_use.card].card_id
    return None


def _v084_decision(state, counts):
    """v0.84 のカードの決定への答え（元の手順より先に答える。相手プレイヤーの決定・場に出たときの特殊能力の使う機会にも答える）。選べるものを順に回し、選ぶ数は決定の
    上限・下限から交互に選ぶ（使う機会は使う・使わないが交互になる）。受け付ける答えだけを選ぶ。v0.84 のカードの決定でなければ何もしない。"""
    d = state.decision
    if d is None:
        return None
    card_id = _v084_source(state, d)
    if card_id not in V0_84:
        return None
    key = f"v084_{card_id}_{d.kind}"
    seen = counts[f"{key}_seen"]
    counts[f"{key}_seen"] += 1
    rotated = list(d.options[seen % len(d.options):]) + list(d.options[:seen % len(d.options)]) if d.options else []
    sizes = [d.max_choices, d.min_choices, max(d.min_choices, 1)] if seen % 2 == 0 else [d.min_choices, max(d.min_choices, 1), d.max_choices]
    candidates = [tuple(rotated[:n]) for n in sizes] + [(o,) for o in d.options]
    for choices in candidates:
        if d.min_choices <= len(choices) <= d.max_choices and _v052_accepted(state, ResolveDecision(d.player, d.id, choices)):
            counts[f"{key}_{len(choices)}"] += 1
            return ResolveDecision(d.player, d.id, choices)
    counts[f"{key}_no_accepted_answer"] += 1
    return None


def _v084_step(state, tried, counts):
    """v0.84: ［おいはらう］（宣言して使う特殊能力）とポケモン育て屋夫婦を、受け付けるなら使う（それぞれ 1 番に 1 回）。v0.84 のカードがない局では何もしない。"""
    player = state.current_player
    p = state.players[player]
    for pokemon in p.in_play():
        card_id = state.cards[pokemon.card].card_id
        if card_id != "neo4-021" or ("v084_power", state.turn_number) in tried:
            continue
        tried.add(("v084_power", state.turn_number))
        use = UsePokemonPower(player, pokemon.pokemon_id, 0)
        if _v052_accepted(state, use):
            counts["v084_power_neo4-021"] += 1
            return use
        counts["v084_power_neo4-021_not_usable"] += 1
    if "trainer_locked" in tried:
        return None
    for uid in p.hand:
        card_id = state.cards[uid].card_id
        if card_id not in V0_84_TRAINERS or ("v084_trainer", state.turn_number) in tried:
            continue
        tried.add(("v084_trainer", state.turn_number))
        play = PlayTrainer(player, uid)
        if _v052_accepted(state, play):
            counts[f"v084_trainer_{card_id}"] += 1
            return play
        counts[f"v084_trainer_{card_id}_not_usable"] += 1
    return None


def v084_uses(state):
    """v0.84: ログから数えた v0.84 のカードの動き（ない局では空）。``attack_<id>#<位置>``・``attack_failed_<理由>``・``power_<イベント>``（［おいはらう］・［ふかふかなからだ］・
    ［たすけだす］・［おくりもの］）・``entry_declined``・``breeder_coins``・``breeder_revealed``・``evolve_by_attack``（しんかのうたで進化した）・``status_prevented``
    （きらめきタッチの効果で特殊状態にならなかった）・``wind_turns``（［きせきのかぜ］がはたらいていた番の数）。"""
    counts = Counter()
    if not any(state.cards[uid].card_id in V0_84 for uid in state.cards):
        return counts
    for e in state.log:
        kind = e["kind"]
        effect = e.get("effect")
        ours = isinstance(effect, str) and effect.split("#")[0].split("@")[0] in V0_84
        if kind == "attack" and ours:
            counts[f"attack_{effect}"] += 1
        elif kind == "attack_failed" and ours:
            counts[f"attack_failed_{e.get('reason')}"] += 1
        elif kind in ("power_sleep", "power_sleep_skipped", "tag_team_heal", "gift_declined", "gift_take_none"):
            counts[f"power_{kind}"] += 1
        elif kind == "pokemon_power" and ours:
            counts[f"power_{effect}"] += 1
        elif kind == "entry_power_declined" and ours:
            counts["entry_declined"] += 1
        elif kind == "breeder_couple_coins":
            counts["breeder_coins"] += 1
        elif kind == "reveal_from_deck" and e.get("trainer_card") is not None and state.cards[e["trainer_card"]].card_id in V0_84_TRAINERS:
            counts["breeder_revealed"] += 1
        elif kind == "evolve" and ours:
            counts["evolve_by_attack"] += 1
        elif kind == "special_condition_prevented" and e.get("persistent_effect"):
            counts["status_prevented"] += 1
        elif kind == "stadium_discarded" and ours:
            counts["stadium_discarded"] += 1
    return counts


_V085_WIND_SEEN: dict = {}  # id(数える表) → (数える表, 数えた (番, カード) の組)。1 局の数える表ごとに、番とカードで 1 回だけ数える（数える表を持っておき、id を使い回させない）


def _v085_observe_wind(state, counts):
    """v0.85: ［きせきのかぜ］がはたらいている場の特殊エネルギーカード（効果が消えて「無色」1 個）を、番とカードごとに 1 回数える（``v085_wind_neutralized_<カード id>``）。
    手順は変えない。［きせきのかぜ］のない局では何もしない。"""
    if not E.miraculous_wind_sources(state):
        return
    for side in state.players:
        for pokemon in side.in_play():
            for uid in pokemon.energy:
                if not state.card_def(uid).is_special_energy or not E.wind_neutralizes(state, uid):
                    continue
                seen = _V085_WIND_SEEN.setdefault(id(counts), (counts, set()))[1]
                if (state.turn_number, uid) in seen:
                    continue
                seen.add((state.turn_number, uid))
                counts[f"v085_wind_neutralized_{state.cards[uid].card_id}"] += 1


def _v085_source(state, d):
    """v0.85: 決定のもとになった v0.85 のカードの id（ワザ・特殊能力。なければ None）。"""
    if d.resume in ("attack", "power"):
        use = d.context_value("use")
        copied = d.context_value("copied") if d.resume == "attack" else None
        return copied[0] if copied else (use[2] if use else None)
    return None


def _v085_decision(state, counts):
    """v0.85 のカードの決定への答え（元の手順より先に答える。場に出たときの特殊能力の使う機会にも答える）。v0.84 の ``_v084_decision`` と同じ回し方（選べるものを順に回し、
    選ぶ数は上限・下限から交互に選ぶ。受け付ける答えだけを選ぶ）。v0.85 のカードの決定でなければ何もしない。"""
    d = state.decision
    if d is None:
        return None
    card_id = _v085_source(state, d)
    if card_id not in V0_85:
        return None
    key = f"v085_{card_id}_{d.kind}"
    seen = counts[f"{key}_seen"]
    counts[f"{key}_seen"] += 1
    rotated = list(d.options[seen % len(d.options):]) + list(d.options[:seen % len(d.options)]) if d.options else []
    sizes = [d.max_choices, d.min_choices, max(d.min_choices, 1)] if seen % 2 == 0 else [d.min_choices, max(d.min_choices, 1), d.max_choices]
    candidates = [tuple(rotated[:n]) for n in sizes] + [(o,) for o in d.options]
    for choices in candidates:
        if d.min_choices <= len(choices) <= d.max_choices and _v052_accepted(state, ResolveDecision(d.player, d.id, choices)):
            counts[f"{key}_{len(choices)}"] += 1
            return ResolveDecision(d.player, d.id, choices)
    counts[f"{key}_no_accepted_answer"] += 1
    return None


def _v085_step(state, tried, counts):
    """v0.85: 宣言して使う特殊能力（［ファイヤーリチャージ］・［ファイヤーレイズ］は 1 番に 1 回。［どしゃぶり］は手札の「水」エネルギーカードを 1 番に 1 枚まで）を、受け付けるなら
    使う。v0.85 のカードがない局では何もしない。"""
    player = state.current_player
    p = state.players[player]
    for pokemon in p.in_play():
        card_id = state.cards[pokemon.card].card_id
        if card_id not in ("neo1-021", "PF2-009", "PF1-009", "NIP2X-001") or ("v085_power", pokemon.pokemon_id, state.turn_number) in tried:
            continue
        tried.add(("v085_power", pokemon.pokemon_id, state.turn_number))
        energy = None
        if card_id in ("PF1-009", "NIP2X-001"):
            waters = [u for u in p.hand if state.cards[u].card_id == WATER]
            if len(waters) < 2 or state.turn_number % 3:
                continue  # 3 番に 1 回、手札に「水」エネルギーカードが 2 枚以上あるときだけ（つけるカードを残す）
            energy = waters[0]
        use = UsePokemonPower(player, pokemon.pokemon_id, 0, energy=energy)
        if _v052_accepted(state, use):
            counts[f"v085_power_{card_id}"] += 1
            return use
        counts[f"v085_power_{card_id}_not_usable"] += 1
    return None


def _v085_energy(state, command, tried, counts):
    """v0.85: この番に手札からまだエネルギーカードをつけておらず、手札にミラクルエネルギーがあれば、元の手順のかわりに、場の「ひかる」「やさしい」ポケモン（バトル場 → ベンチ）に
    つける（3 番に 1 回は、「ひかる」「やさしい」でないポケモンにつけようとして、拒否されることを数える）。受け付けない場面はつけず ``v085_attach_rejected_<コード>`` に数える。"""
    if state.phase is not Phase.MAIN or state.energy_attachments_this_turn or ("v085_energy", state.turn_number) in tried:
        return None
    if not isinstance(command, (AttachEnergy, UseAttack, EndTurn)):
        return None
    player = state.current_player
    p = state.players[player]
    miracles = [u for u in p.hand if state.cards[u].card_id == MIRACLE_ENERGY]
    if not miracles:
        return None
    tried.add(("v085_energy", state.turn_number))
    targets = [pk for pk in p.in_play() if not state.is_face_down(pk) and E.shining_or_light(state, pk)]
    others = [pk for pk in p.in_play() if not state.is_face_down(pk) and not E.shining_or_light(state, pk)]
    if others and state.turn_number % 3 == 0:
        try:
            apply_command(_v052_real(state), AttachEnergy(player, miracles[0], others[0].card))
            counts["v085_attach_non_light_accepted"] += 1
        except (IllegalActionError, UnsupportedError) as error:
            counts[f"v085_attach_non_light_rejected_{error.code}"] += 1
    for target in targets:
        attach = AttachEnergy(player, miracles[0], target.card)
        try:
            apply_command(_v052_real(state), attach)
        except (IllegalActionError, UnsupportedError) as error:
            counts[f"v085_attach_rejected_{error.code}"] += 1
            continue
        counts["v085_attach_miracle"] += 1
        return attach
    return None


def _v086_decision(state, counts):
    """v0.86 の決定への答え（元の手順より先に答える）: 反応の決定（再開先 ``"reaction"``。順番・使う機会・進化カード・［いなびかり］の入れ替え。決めるのは番のプレイヤー・
    持ち主・相手）と、v0.86 のカードのワザ・特殊能力の決定（場に出たときの特殊能力の使う機会を含む）。v0.85 の ``_v085_decision`` と同じ回し方（選べるものを順に回し、選ぶ数は
    上限・下限から交互に選ぶ。受け付ける答えだけを選ぶ）。どちらでもなければ何もしない。"""
    d = state.decision
    if d is None:
        return None
    if d.resume == "reaction":
        key = f"v086_reaction_{d.kind}"
    else:
        card_id = _v085_source(state, d)
        if card_id not in V0_86:
            return None
        key = f"v086_{card_id}_{d.kind}"
    seen = counts[f"{key}_seen"]
    counts[f"{key}_seen"] += 1
    rotated = list(d.options[seen % len(d.options):]) + list(d.options[:seen % len(d.options)]) if d.options else []
    sizes = [d.max_choices, d.min_choices, max(d.min_choices, 1)] if seen % 2 == 0 else [d.min_choices, max(d.min_choices, 1), d.max_choices]
    candidates = [tuple(rotated[:n]) for n in sizes] + [(o,) for o in d.options]
    for choices in candidates:
        if d.min_choices <= len(choices) <= d.max_choices and _v052_accepted(state, ResolveDecision(d.player, d.id, choices)):
            counts[f"{key}_{len(choices)}"] += 1
            return ResolveDecision(d.player, d.id, choices)
    counts[f"{key}_no_accepted_answer"] += 1
    return None


def _v086_step(state, tried, counts):
    """v0.86: ［ソーラーパワー］（自分の番ごとに 1 回）を、受け付けるなら使う（SO1 の場面は受け付けないので使わない）。v0.86 のカードがない局では何もしない。"""
    player = state.current_player
    for pokemon in state.players[player].in_play():
        card_id = state.cards[pokemon.card].card_id
        if card_id != "PR1-058" or ("v086_power", pokemon.pokemon_id, state.turn_number) in tried:
            continue
        tried.add(("v086_power", pokemon.pokemon_id, state.turn_number))
        use = UsePokemonPower(player, pokemon.pokemon_id, 0)
        if _v052_accepted(state, use):
            counts[f"v086_power_{card_id}"] += 1
            return use
        counts[f"v086_power_{card_id}_not_usable"] += 1
    return None


def _v087_decision(state, counts):
    """v0.87 の決定への答え（元の手順より先に答える）: ［やけのこり］のカード・［ぶんれつ］・ワザの途中の同じ時点の反応の順番と、v0.87 のカードのワザ・特殊能力の決定（使う機会を
    含む。相手の決定にも答える）。v0.86 の ``_v086_decision`` と同じ回し方。どちらでもなければ何もしない。"""
    d = state.decision
    if d is None:
        return None
    if d.kind in ("magma_pool_energy", "split_from_deck") or (d.kind == "reaction_order" and d.context_value("move_order") is not None):
        key = f"v087_reaction_{d.kind}"
    else:
        card_id = _v085_source(state, d)
        if card_id not in V0_87:
            return None
        key = f"v087_{card_id}_{d.kind}"
    seen = counts[f"{key}_seen"]
    counts[f"{key}_seen"] += 1
    rotated = list(d.options[seen % len(d.options):]) + list(d.options[:seen % len(d.options)]) if d.options else []
    sizes = [d.max_choices, d.min_choices, max(d.min_choices, 1)] if seen % 2 == 0 else [d.min_choices, max(d.min_choices, 1), d.max_choices]
    candidates = [tuple(rotated[:n]) for n in sizes] + [(o,) for o in d.options]
    for choices in candidates:
        if d.min_choices <= len(choices) <= d.max_choices and _v052_accepted(state, ResolveDecision(d.player, d.id, choices)):
            counts[f"{key}_{len(choices)}"] += 1
            return ResolveDecision(d.player, d.id, choices)
    counts[f"{key}_no_accepted_answer"] += 1
    return None


def _v087_step(state, tried, counts):
    """v0.87: ［マグネット］（自分の番ごとに 1 回）を、受け付けるなら使う。相手のバトル場に［とおせんぼ］のカビゴンがいる番に 1 度だけ、自分のバトル場のポケモンの「にげる」を
    エンジンに渡して、拒否（``RETREAT_PREVENTED``）を数える（手順は変えない。受け付けたら数えるだけで使わない）。v0.87 のカードがない局では何もしない。"""
    player = state.current_player
    for pokemon in state.players[player].in_play():
        card_id = state.cards[pokemon.card].card_id
        if card_id not in ("ES2-014", "QSG-023") or ("v087_power", pokemon.pokemon_id, state.turn_number) in tried:
            continue
        tried.add(("v087_power", pokemon.pokemon_id, state.turn_number))
        use = UsePokemonPower(player, pokemon.pokemon_id, 0)
        if _v052_accepted(state, use):
            counts[f"v087_power_{card_id}"] += 1
            return use
        counts[f"v087_power_{card_id}_not_usable"] += 1
    opponent = state.players[1 - player].active
    active = state.players[player].active
    if opponent is not None and active is not None and state.players[player].bench and state.cards[opponent.card].card_id in ("ES1-034", "QSG-046") \
            and ("v087_guard", state.turn_number) not in tried:
        tried.add(("v087_guard", state.turn_number))
        try:
            apply_command(_v052_real(state), Retreat(player, tuple(active.energy), state.players[player].bench[0].card))
            counts["v087_guard_retreat_accepted"] += 1
        except IllegalActionError as error:
            counts[f"v087_guard_retreat_{error.code}"] += 1
        except UnsupportedError as error:
            counts[f"v087_guard_retreat_{error.code}"] += 1
    return None


def v087_uses(state):
    """v0.87: ログから数えた v0.87 のカードの動き（ない局では空）。``attack_<id>#<位置>``（そのカードが使ったワザ）・``power_<id>``（宣言・使う機会で使った）と、特殊能力が実際に
    はたらいたこと（``spikes_<id>``・``magma_<id>``・``magma_none``・``hot_plate_<id>``・``shock_<id>_<面>``・``poison_fluid_<id>``・``split_<id>``・``split_declined``・``split_skipped_<理由>``・
    ``aurora_<id>``・``dig_<id>``・``strange_gas``）。在場していること・まねて使ったこと・同じ組の別の id の使用は、その id の使用に数えない。"""
    counts = Counter()
    if not any(state.cards[uid].card_id in V0_87 for uid in state.cards):
        return counts

    def card_of(uid):
        return state.cards[uid].card_id if isinstance(uid, int) and uid in state.cards else None

    for e in state.log:
        kind = e["kind"]
        holder = card_of(e.get("pokemon"))
        if kind == "attack" and holder in V0_87 and e.get("card_id", holder) == holder:
            counts[f"attack_{holder}#{e['attack_index']}"] += 1
        elif kind == "pokemon_power" and holder in V0_87:
            counts[f"power_{holder}"] += 1
        elif kind in ("spikes_damage", "hot_plate_damage", "magma_pool", "poison_fluid") and holder in V0_87:
            counts[f"{kind.split('_')[0]}_{holder}"] += 1
        elif kind == "magma_pool_none":
            counts["magma_none"] += 1
        elif kind == "shock_blast_check" and holder in V0_87:
            counts[f"shock_{holder}_{e['result']}"] += 1
        elif kind == "bench_from_deck" and isinstance(e.get("power"), str) and e["power"].startswith("ES2-003"):
            counts["split_ES2-003"] += 1
        elif kind == "split_declined":
            counts["split_declined"] += 1
        elif kind == "split_skipped":
            counts[f"split_skipped_{e['reason']}"] += 1
        elif kind in ("damage_prevented", "effect_prevented") and e.get("persistent_effect") in ("aurora_veil", "dig_under"):
            counts[f"{'aurora' if e['persistent_effect'] == 'aurora_veil' else 'dig'}_{card_of(e.get('source_card'))}"] += 1
        elif kind == "trainer_effect_added" and e.get("effect_kind") == "opponent_power_suppression":
            counts["strange_gas"] += 1
    return counts


def _v088_decision(state, counts):
    """v0.88 のカードのワザ・特殊能力の決定への答え（元の手順より先に答える）: ［エナジーコンバーター］の色・デルタビームの特殊状態・コアストリーム・レインボーウェーブの色・プラズマの
    カード・テクスチャー2・テクスチャーマジックの色（変えない（0 個）も選ぶ）。v0.87 の ``_v087_decision`` と同じ回し方。v0.88 のカードの決定でなければ何もしない。"""
    d = state.decision
    if d is None:
        return None
    card_id = _v085_source(state, d)
    if card_id not in V0_88:
        return None
    key = f"v088_{card_id}_{d.kind}"
    seen = counts[f"{key}_seen"]
    counts[f"{key}_seen"] += 1
    rotated = list(d.options[seen % len(d.options):]) + list(d.options[:seen % len(d.options)]) if d.options else []
    sizes = [d.max_choices, d.min_choices, max(d.min_choices, 1)] if seen % 2 == 0 else [d.min_choices, max(d.min_choices, 1), d.max_choices]
    candidates = [tuple(rotated[:n]) for n in sizes] + [(o,) for o in d.options]
    for choices in candidates:
        if d.min_choices <= len(choices) <= d.max_choices and _v052_accepted(state, ResolveDecision(d.player, d.id, choices)):
            counts[f"{key}_{len(choices)}"] += 1
            return ResolveDecision(d.player, d.id, choices)
    counts[f"{key}_no_accepted_answer"] += 1
    return None


V088_DECLARED = ("neo3-026", "neo3-051", "neo3-045")  # ［せんすい］・［エナジーコンバーター］・［でんじりょく］
V088_MAGNETIC_NAMES = ("コイル", "レアコイル", "わるいレアコイル")


def _v088_power_uses(state, player, pokemon, card_id):
    """v0.88: 宣言して使う特殊能力の候補（受け付けるかは呼ぶ側が確かめる）。［エナジーコンバーター］は自分の場の基本エネルギーカード（バトル場から）、［でんじりょく］はベンチの
    名前の合うポケモンのエネルギーカードをバトル場の名前の合うポケモンへ（バトル場がそうでなければベンチどうし）。"""
    me = state.players[player]
    if card_id == "neo3-026":
        return [UsePokemonPower(player, pokemon.pokemon_id, 0)]
    if card_id == "neo3-051":
        return [UsePokemonPower(player, pokemon.pokemon_id, 0, energy=uid, source=holder.pokemon_id)
                for holder in me.in_play() if not state.is_face_down(holder) for uid in holder.energy if state.card_def(uid).is_basic_energy]
    named = [p for p in me.in_play() if not state.is_face_down(p) and current_form(state, p) is not None
             and state.card_def(current_form(state, p).card).name_ja in V088_MAGNETIC_NAMES]
    targets = [p for p in named if p is me.active] or named
    found = [UsePokemonPower(player, pokemon.pokemon_id, 0, energy=uid, source=source.pokemon_id, target=target.pokemon_id)
             for target in targets for source in named if source is not target for uid in source.energy]
    if me.active in named and len(me.active.energy) >= 4:
        # バトル場の名前の合うポケモンに 4 枚以上ついていれば（レアコイルのワザは 3 個）、ベンチの名前の合うポケモンへも 1 枚つけ替える候補にする
        found += [UsePokemonPower(player, pokemon.pokemon_id, 0, energy=me.active.energy[-1], source=me.active.pokemon_id, target=target.pokemon_id)
                  for target in named if target is not me.active]
    return found


def _v088_step(state, tried, counts):
    """v0.88: ［せんすい］・［エナジーコンバーター］・［でんじりょく］を、自分の番ごとに 1 回（［でんじりょく］も手順では 1 回）、受け付けるなら使う。v0.88 のカードがない局では
    何もしない。"""
    player = state.current_player
    for pokemon in state.players[player].in_play():
        if state.is_face_down(pokemon):
            continue
        card_id = state.cards[pokemon.card].card_id
        marker = ("v088_power", pokemon.pokemon_id, state.turn_number)
        if card_id not in V088_DECLARED or marker in tried:
            continue
        tried.add(marker)
        for use in _v088_power_uses(state, player, pokemon, card_id):
            if _v052_accepted(state, use):
                counts[f"v088_power_{card_id}"] += 1
                return use
        counts[f"v088_power_{card_id}_not_usable"] += 1
    return None


def _v088_attack(state, command, tried, counts):
    """v0.88: ランターン（neo1-040）が「まぶしいひかり」を使うとき、［すいりょくはつでん］をいっしょに使う（受け付けるなら。2 回に 1 回は使わない）。ほかのコマンドはそのまま。

    元の手順はワザを払えるかを印刷の色（``state.energy_types``）で見るので、［エナジーコンバーター］の記録・こうごうせいのある場では、払えないワザを選ぶことがある。そのときは
    エンジンの支払いの問い合わせで確かめ、払えなければ番を終える（色を変える効果のない局では何もしない）。"""
    if not isinstance(command, UseAttack) or command.attack_power or command.card is not None:
        return command
    active = state.players[command.player].active
    if active is not None and not state.is_face_down(active) and _v088_color_layer_on(state):
        attacks = state.card_def(current_form(state, active).card).attacks
        if 0 <= command.attack_index < len(attacks) and not attack_cost_payable(state, active, attacks[command.attack_index]):
            counts[f"v088_unpayable_end_{state.cards[active.card].card_id}"] += 1
            return EndTurn(command.player)
    if active is None or state.is_face_down(active) or state.cards[active.card].card_id != "neo1-040" or command.attack_index != 0:
        return command
    seen = counts["v088_hydroelectric_seen"]
    counts["v088_hydroelectric_seen"] += 1
    if seen % 2:
        return command
    with_power = dataclasses.replace(command, attack_power=True)
    if _v052_accepted(state, with_power):
        counts["v088_hydroelectric_used"] += 1
        return with_power
    counts["v088_hydroelectric_not_accepted"] += 1
    return command


def v088_uses(state):
    """v0.88: ログから数えた v0.88 のカードの動き（ない局では空）。``attack_<id>#<位置>``（そのカードが使ったワザ）・``power_<id>``（宣言した）・``attack_power``（［すいりょくはつでん］を
    いっしょに使った）・``color_<種類>``（色を変える効果を与えた）・``color_removed_<理由>``・``color_chosen``・``color_none``・``color_declined``・``magnetic_moves``。"""
    counts = Counter()
    if not any(state.cards[uid].card_id in V0_88 for uid in state.cards):
        return counts

    def card_of(uid):
        return state.cards[uid].card_id if isinstance(uid, int) and uid in state.cards else None

    for e in state.log:
        kind = e["kind"]
        holder = card_of(e.get("pokemon"))
        if kind == "attack" and holder in V0_88 and e.get("card_id", holder) == holder:
            counts[f"attack_{holder}#{e['attack_index']}"] += 1
        elif kind == "pokemon_power" and holder in V0_88:
            counts[f"power_{holder}"] += 1
        elif kind == "attack_power":
            counts["attack_power"] += 1
        elif kind == "color_effect_added":
            counts[f"color_{e['color_effect']}"] += 1
        elif kind == "color_effect_removed":
            counts[f"color_removed_{e['reason']}"] += 1
        elif kind == "attack_color_chosen":
            counts["color_chosen"] += 1
        elif kind == "attack_color_none":
            counts["color_none"] += 1
        elif kind == "color_change_declined":
            counts["color_declined"] += 1
        elif kind == "move_energy" and isinstance(e.get("power"), str) and e["power"].startswith("neo3-045"):
            counts["magnetic_moves"] += 1
    return counts


def _v089_decision(state, counts):
    """v0.89 のワザの決定への答え（元の手順より先に答える）: 選ぶポケモン（相手プレイヤーが選ぶねこパンチも）・マイクロウェーブのトラッシュのカード・お上品攻撃の減らす量・ナツメのESPの
    やり直し・［ベンチガード］。v0.88 の ``_v088_decision`` と同じ回し方（選べるものを順に回し、受け付ける答えだけを選ぶ。選ぶと止める答え（FA1・JS1 など）は選ばない）。v0.89 のワザの
    決定でなければ何もしない。"""
    d = state.decision
    if d is None:
        return None
    card_id = _v085_source(state, d)
    if card_id not in V0_89:
        return None
    key = f"v089_{card_id}_{d.kind}"
    seen = counts[f"{key}_seen"]
    counts[f"{key}_seen"] += 1
    blocked = set(d.context_value("unresolved_choices", ()) or ())
    if blocked:
        counts[f"{key}_blocked_choices"] += 1
    rotated = list(d.options[seen % len(d.options):]) + list(d.options[:seen % len(d.options)]) if d.options else []
    sizes = [d.max_choices, d.min_choices, max(d.min_choices, 1)] if seen % 2 == 0 else [d.min_choices, max(d.min_choices, 1), d.max_choices]
    candidates = [tuple(o for o in rotated if o not in blocked)[:n] for n in sizes] + [(o,) for o in d.options if o not in blocked]
    for choices in candidates:
        if d.min_choices <= len(choices) <= d.max_choices and _v052_accepted(state, ResolveDecision(d.player, d.id, choices)):
            counts[f"{key}_{len(choices)}"] += 1
            return ResolveDecision(d.player, d.id, choices)
    counts[f"{key}_no_accepted_answer"] += 1
    return None


def _v091_decision(state, counts):
    """v0.91 のワザの決定への答え（元の手順より先に答える）: ひらいしん・ハイパーテクスチャーの選ぶポケモン・ハイパーテクスチャーの色。v0.89 の ``_v089_decision`` と同じ回し方
    （選べるものを順に回し、受け付ける答えだけを選ぶ。選ぶと止める答えは選ばない）。v0.91 のワザの決定でなければ何もしない。"""
    d = state.decision
    if d is None:
        return None
    card_id = _v085_source(state, d)
    if card_id not in V0_91:
        return None
    key = f"v091_{card_id}_{d.kind}"
    seen = counts[f"{key}_seen"]
    counts[f"{key}_seen"] += 1
    blocked = set(d.context_value("unresolved_choices", ()) or ())
    if blocked:
        counts[f"{key}_blocked_choices"] += 1
    rotated = list(d.options[seen % len(d.options):]) + list(d.options[:seen % len(d.options)]) if d.options else []
    for choice in [o for o in rotated if o not in blocked]:
        if _v052_accepted(state, ResolveDecision(d.player, d.id, (choice,))):
            counts[f"{key}_answered"] += 1
            return ResolveDecision(d.player, d.id, (choice,))
    counts[f"{key}_no_accepted_answer"] += 1
    return None


def _v092_decision(state, counts):
    """v0.92 のワザの決定への答え（元の手順より先に答える）: だましうちの選ぶポケモン。v0.89 の ``_v089_decision`` と同じ回し方（選べるものを順に回し、受け付ける答えだけを
    選ぶ。選ぶと止める答えは選ばない）。v0.92 のワザの決定でなければ何もしない。"""
    d = state.decision
    if d is None:
        return None
    card_id = _v085_source(state, d)
    if card_id not in V0_92:
        return None
    key = f"v092_{card_id}_{d.kind}"
    seen = counts[f"{key}_seen"]
    counts[f"{key}_seen"] += 1
    blocked = set(d.context_value("unresolved_choices", ()) or ())
    if blocked:
        counts[f"{key}_blocked_choices"] += 1
    rotated = list(d.options[seen % len(d.options):]) + list(d.options[:seen % len(d.options)]) if d.options else []
    for choice in [o for o in rotated if o not in blocked]:
        if _v052_accepted(state, ResolveDecision(d.player, d.id, (choice,))):
            counts[f"{key}_answered"] += 1
            return ResolveDecision(d.player, d.id, (choice,))
    counts[f"{key}_no_accepted_answer"] += 1
    return None


def v092_uses(state):
    """v0.92: ログから数えた v0.92 のカードの動き（v0.92 のカードのない局では空）。``attack_<id>#<位置>``（v0.92 のカードが使ったワザ）・``coin_<id>#<位置>_<表裏>``（ワザの最初の
    コイン）・``lock_added_<種類>``・``lock_removed_<種類>_<理由>``（期間を明示した禁止・こわいかお・かげしばりの禁止・いやなおと）・``drain_heal``・``drain_counters``・``poison_after_drain``・
    ``field_suppression_added``・``field_suppression_removed_<理由>``・``pincer_flips``（メタルニッパーの投げた枚数の合計）・``pincer_heads_<数>``・``bonus_damage``（8 段階の +20 の
    あるダメージ）・``feint_<受けるものの種類>``。"""
    counts = Counter()
    if not any(state.cards[uid].card_id in V0_92 for uid in state.cards):
        return counts
    current = None
    first_coin = False
    pincer = None
    for e in state.log:
        kind = e["kind"]
        if kind == "attack":
            holder = state.cards[e["pokemon"]].card_id if e.get("pokemon") in state.cards else None
            current = e.get("card_id", holder)
            current = f"{current}#{e['attack_index']}" if current in V0_92 else None
            first_coin = False
            if current is not None:
                counts[f"attack_{current}"] += 1
            if pincer is not None:
                counts[f"pincer_heads_{pincer}"] += 1
                pincer = None
            if current == "PRN-025#1":
                pincer = 0
        elif kind in ("turn_start", "turn_end"):
            if pincer is not None:
                counts[f"pincer_heads_{pincer}"] += 1
                pincer = None
            current = None
        elif kind == "coin_flip" and current is not None and e.get("source") == "attack":
            if not first_coin:
                counts[f"coin_{current}_{e['result']}"] += 1
                first_coin = True
            if current == "PRN-025#1":
                counts["pincer_flips"] += 1
                if e["result"] == "heads" and pincer is not None:
                    pincer += 1
        elif kind == "persistent_effect_added" and e["persistent_effect"] in ("period_retreat_lock", "period_attack_lock", "received_attack_damage_bonus",
                                                                            "cannot_attack", "cannot_retreat", "cannot_attack_while_source_active") \
                and current is not None:
            counts[f"lock_added_{e['persistent_effect']}"] += 1
        elif kind == "persistent_effect_removed" and e["persistent_effect"] in ("period_retreat_lock", "period_attack_lock", "received_attack_damage_bonus"):
            counts[f"lock_removed_{e['persistent_effect']}_{e['reason']}"] += 1
        elif kind == "drain_heal" and current in ("neo1-011#1", "neo3-004#1"):
            counts["drain_heal"] += 1
            counts["drain_counters"] += e["counters"]
        elif kind == "special_condition" and current in ("neo1-011#1", "neo3-004#1") and e.get("condition") == "poison":
            counts["poison_after_drain"] += 1
        elif kind == "trainer_effect_added" and e.get("effect_kind") == "attack_field_power_suppression":
            counts["field_suppression_added"] += 1
        elif kind == "trainer_effect_removed" and e.get("effect_kind") == "attack_field_power_suppression":
            counts[f"field_suppression_removed_{e['reason']}"] += 1
        elif kind == "damage" and any(str(step[0]).startswith("8 ") and str(step[0]).endswith("（received_attack_damage_bonus）") for step in e.get("steps") or ()):
            counts["bonus_damage"] += 1
        elif kind == "damage" and current == "neo1-055#1":
            counts[f"feint_{e.get('target', 'opponent_active')}"] += 1
    if pincer is not None:
        counts[f"pincer_heads_{pincer}"] += 1
    return +counts


def _v095_decision(state, counts):
    """v0.95 のワザ・特殊能力の決定への答え（元の手順より先に答える）: 選べるものを順に回す（選ぶと止める答えは選ばない。みらいよちの山札の持ち主は、山札が 3 枚より少ない持ち主を
    選ばない）。並べかえ（``ARRANGE_DECK_TOP``）は、そのままの並びと逆の並びを交互に答える。［わるぢえ］の切るか（``OPTIONAL_SHUFFLE``）は、切らない・切るを交互に答える。v0.95 のカードの
    決定でなければ何もしない。"""
    d = state.decision
    if d is None or d.resume not in ("attack", "power"):
        return None
    card_id = _v085_source(state, d)
    if card_id not in V0_95:
        return None
    key = f"v095_{card_id}_{d.kind}"
    seen = counts[f"{key}_seen"]
    counts[f"{key}_seen"] += 1
    blocked = set(d.context_value("unresolved_choices", ()) or ())
    if blocked:
        counts[f"{key}_blocked_choices"] += 1
    if d.min_choices == d.max_choices and d.max_choices > 1:
        order = tuple(d.options) if seen % 2 == 0 else tuple(reversed(d.options))
        if _v052_accepted(state, ResolveDecision(d.player, d.id, order)):
            counts[f"{key}_{'kept' if seen % 2 == 0 else 'reversed'}"] += 1
            return ResolveDecision(d.player, d.id, order)
        counts[f"{key}_no_accepted_answer"] += 1
        return None
    if d.min_choices == 0 and seen % 2 == 0:
        counts[f"{key}_declined"] += 1
        return ResolveDecision(d.player, d.id, ())
    rotated = list(d.options[seen % len(d.options):]) + list(d.options[:seen % len(d.options)]) if d.options else []
    for choice in [o for o in rotated if o not in blocked]:
        if _v052_accepted(state, ResolveDecision(d.player, d.id, (choice,))):
            counts[f"{key}_answered"] += 1
            return ResolveDecision(d.player, d.id, (choice,))
    if d.min_choices == 0:
        counts[f"{key}_declined_no_choice"] += 1
        return ResolveDecision(d.player, d.id, ())
    counts[f"{key}_no_accepted_answer"] += 1
    return None


def _v095_step(state, tried, counts):
    """v0.95: ［みやぶる］・［わるぢえ］を、場のポケモンごとに自分の番ごとに 1 回、受け付けるなら使う（使えない特殊状態・特殊能力を消す効果・相手の山札 0 枚の PW3 で受け付けない
    なら使わない）。v0.95 のカードがない局では何もしない。"""
    player = state.current_player
    for pokemon in state.players[player].in_play():
        if state.is_face_down(pokemon):
            continue
        card_id = state.cards[pokemon.card].card_id
        marker = ("v095_power", pokemon.pokemon_id, state.turn_number)
        if card_id not in V095_DECLARED or marker in tried:
            continue
        tried.add(marker)
        use = UsePokemonPower(player, pokemon.pokemon_id, 0)
        if _v052_accepted(state, use):
            counts[f"v095_power_{card_id}"] += 1
            return use
        counts[f"v095_power_{card_id}_not_usable"] += 1
    return None


def v095_uses(state):
    """v0.95: ログから数えた v0.95 のカードの動き（v0.95 のカードのない局では空）。``attack_<id>#<位置>``・``coin_<id>#<位置>_<表裏>``（ワザの最初のコイン）・
    ``looked_hand_<id>#<位置>_<0 か n>``（見た相手の手札が 0 枚か）・``hand_trainer_to_deck_<id>#<位置>``・``shuffle_<id>#<位置>``・``deck_top_<id>#<位置>_<discarded か returned か none>``・
    ``looked_deck_top_<id>#<位置>_<own か opponent>``・``arranged_<id>#<位置>``・``milled_<id>#<位置>``・``milled_to_hand_<id>#<位置>=<枚数>``・``tower_suppressed_<id>#<位置>``・
    ``attached_trainer_to_deck_<id>#<位置>``・``effect_prevented_<id>#<位置>``・``evaded_<id>#<位置>``・``damage_<id>#<位置>=<量>``（相手の対戦ポケモンへの最初のダメージ）と、特殊能力の
    ``power_<名前>``・``power_coin_<名前>_<表裏>``・``power_looked_<名前>``・``power_returned_<名前>``・``power_shuffle_<名前>``・``power_shuffle_declined_<名前>``。"""
    counts = Counter()
    if not any(state.cards[uid].card_id in V0_95 for uid in state.cards):
        return counts
    current = None
    power = None
    first_coin = first_damage = False
    for e in state.log:
        kind = e["kind"]
        if kind == "attack":
            holder = state.cards[e["pokemon"]].card_id if e.get("pokemon") in state.cards else None
            current = e.get("card_id", holder)
            current = f"{current}#{e['attack_index']}" if current in V0_95 else None
            power = None
            first_coin = first_damage = False
            if current is not None:
                counts[f"attack_{current}"] += 1
            continue
        if kind == "pokemon_power":
            holder = state.cards[e["pokemon"]].card_id if e.get("pokemon") in state.cards else None
            power = e["power"] if holder in V095_DECLARED else None
            current = None
            if power is not None:
                counts[f"power_{power}"] += 1
            continue
        if kind in ("turn_start", "turn_end"):
            current = power = None
            continue
        if power is not None and e.get("power"):
            if kind == "coin_flip":
                counts[f"power_coin_{power}_{e['result']}"] += 1
            elif kind in ("look_at_hand", "look_at_card"):
                counts[f"power_looked_{power}"] += 1
            elif kind == "opponent_hand_to_deck":
                counts[f"power_returned_{power}"] += 1
            elif kind == "shuffle":
                counts[f"power_shuffle_{power}"] += 1
            elif kind == "shuffle_declined":
                counts[f"power_shuffle_declined_{power}"] += 1
            continue
        if current is None:
            continue
        if kind == "coin_flip" and e.get("source") == "attack" and not first_coin:
            counts[f"coin_{current}_{e['result']}"] += 1
            first_coin = True
        elif kind == "look_at_hand":
            counts[f"looked_hand_{current}_{'0' if not e['cards'] else 'n'}"] += 1
        elif kind == "opponent_hand_to_deck":
            counts[f"hand_trainer_to_deck_{current}"] += 1
        elif kind == "shuffle" and e.get("effect"):
            counts[f"shuffle_{current}"] += 1
        elif kind == "look_at_deck_top_none":
            counts[f"deck_top_{current}_none"] += 1
        elif kind == "deck_top_returned":
            counts[f"deck_top_{current}_returned"] += 1
        elif kind == "discard_from_deck":
            counts[f"{'deck_top' if e.get('attacker') is not None else 'milled'}_{current}{'_discarded' if e.get('attacker') is not None else ''}"] += 1
        elif kind == "look_at_deck_top":
            counts[f"looked_deck_top_{current}_{'own' if e['owner'] == e['player'] else 'opponent'}"] += 1
        elif kind == "arrange_deck_top":
            counts[f"arranged_{current}"] += 1
        elif kind == "milled_to_hand":
            counts[f"milled_to_hand_{current}={len(e['cards'])}"] += 1
        elif kind == "discard_to_hand_suppressed":
            counts[f"tower_suppressed_{current}"] += 1
        elif kind == "attached_trainer_to_deck":
            counts[f"attached_trainer_to_deck_{current}"] += 1
        elif kind == "effect_prevented":
            counts[f"effect_prevented_{current}"] += 1
        elif kind == "attack_evaded":
            counts[f"evaded_{current}"] += 1
        elif kind == "damage" and not first_damage:
            counts[f"damage_{current}={e['amount']}"] += 1
            first_damage = True
    return +counts


def _v096_source(state, d):
    """v0.96: 決定のもとになった v0.96 のカードの id（アンノーンのワザ・特殊能力・遺跡の石版。なければ None）。"""
    if d.resume == "trainer":
        use = d.context_value("use")
        return use[2] if use is not None and use[2] in V0_96_TRAINERS else None
    card_id = _v085_source(state, d)
    return card_id if card_id in V0_96_POKEMON else None


def _v096_decision(state, counts):
    """v0.96 の決定への答え（元の手順より先に答える）: 場に出たときの特殊能力の使う機会・［ENGAGE］のそれぞれのもどすか・［SEARCH］のサイドの位置・遺跡の石版のベンチに出すカード。
    場に出たときの特殊能力の使う機会（``ENTRY_POWER``）は、局の中で使う・使わないを交互に答え（最初の機会は使う）、［ENGAGE］のもどすか（``ACCEPT_REQUEST``）は、番の数の偶奇で、
    偶数の番は使ったプレイヤーがもどして相手がもどさず、奇数の番はその逆に答える（1 回の［ENGAGE］で、もどす・もどさないの両方が出る。数えるのは局ごとなので、局の中の回数では回さない）。
    選ぶ決定は選べるものを順に回す（選ぶと止める答えは選ばない）。v0.96 のカードの決定でなければ何もしない。"""
    d = state.decision
    if d is None:
        return None
    card_id = _v096_source(state, d)
    if card_id is None:
        return None
    use = d.context_value("use")
    who = "user" if use is not None and d.player == use[0] else "opponent"
    key = f"v096_{card_id}_{d.kind}_{who}"
    seen = counts[f"{key}_seen"]
    counts[f"{key}_seen"] += 1
    blocked = set(d.context_value("unresolved_choices", ()) or ())
    if blocked:
        counts[f"{key}_blocked_choices"] += 1
    if d.kind == "accept_request":
        decline = (state.turn_number + (0 if who == "user" else 1)) % 2 == 1
    else:
        decline = seen % 2 == 1
    if d.min_choices == 0 and decline:
        counts[f"{key}_declined"] += 1
        return ResolveDecision(d.player, d.id, ())
    rotated = list(d.options[seen % len(d.options):]) + list(d.options[:seen % len(d.options)]) if d.options else []
    for choice in [o for o in rotated if o not in blocked]:
        if _v052_accepted(state, ResolveDecision(d.player, d.id, (choice,))):
            counts[f"{key}_answered"] += 1
            return ResolveDecision(d.player, d.id, (choice,))
    if d.min_choices == 0:
        counts[f"{key}_declined_no_choice"] += 1
        return ResolveDecision(d.player, d.id, ())
    counts[f"{key}_no_accepted_answer"] += 1
    return None


def _v096_step(state, tried, counts):
    """v0.96: ［OBSERVE］・［LAUGH］・［SEARCH］・［TELL］を、場のポケモンごとに自分の番ごとに 1 回、受け付けるなら使う（特殊能力を消す効果・PW3・OB1 で受け付けないなら使わない）。
    v0.96 のカードがない局では何もしない。"""
    player = state.current_player
    for pokemon in state.players[player].in_play():
        if state.is_face_down(pokemon):
            continue
        card_id = state.cards[pokemon.card].card_id
        marker = ("v096_power", pokemon.pokemon_id, state.turn_number)
        if card_id not in V096_DECLARED or marker in tried:
            continue
        tried.add(marker)
        use = UsePokemonPower(player, pokemon.pokemon_id, 0)
        if _v052_accepted(state, use):
            counts[f"v096_power_{card_id}"] += 1
            return use
        counts[f"v096_power_{card_id}_not_usable"] += 1
    return None


def _v096_trainer(state, tried, counts):
    """v0.96: 手札の遺跡の石版を、受け付けるなら使う（カード id ごとに 1 番に 1 回まで）。使う前に止まる・拒否される場面（BENCH_FULL・ST1・GG1）は使わず
    ``v096_<カード>_not_playable_<コード>`` に数える。"""
    player = state.current_player
    for uid in state.players[player].hand:
        card_id = state.cards[uid].card_id
        if card_id not in V0_96_TRAINERS or (f"v096_{card_id}", state.turn_number) in tried:
            continue
        tried.add((f"v096_{card_id}", state.turn_number))
        play = PlayTrainer(player, uid)
        real = _V052_REAL.get("state")
        try:
            apply_command(real if real is not None and real.turn_number == state.turn_number and real.decision == state.decision else state, play)
        except (IllegalActionError, UnsupportedError) as error:
            counts[f"v096_{card_id}_not_playable_{error.code}"] += 1
            continue
        counts[f"v096_play_{card_id}"] += 1
        return play
    return None


def _v096_retreat(state, tried, counts):
    """v0.96: 自分のベンチの［ZOOM］がはたらき、バトル場のアンノーン（今の姿）の「にげる」エネルギーがなくなっているとき、1 番に 1 回、エネルギーをトラッシュせずに「にげる」（入れ替える
    控えは、局の中で順に回す。［ZOOM］のアンノーンも選ぶ）。受け付けない（CP2・BB1・ねむり・マヒなど）なら「にげる」ず、``v096_zoom_retreat_not_accepted`` に数える。"""
    player = state.current_player
    p = state.players[player]
    marker = ("v096_retreat", state.turn_number)
    if marker in tried or p.active is None or not p.bench or state.is_face_down(p.active):
        return None
    try:
        cost = retreat_cost(state, player)
    except (UnsupportedError, ValueError):
        return None
    if not cost.power_zeroed:
        return None
    tried.add(marker)
    seen = counts["v096_zoom_retreat_seen"]
    counts["v096_zoom_retreat_seen"] += 1
    targets = [b.card for b in p.bench if not state.is_face_down(b)]
    for card in targets[seen % len(targets):] + targets[:seen % len(targets)] if targets else []:
        command = Retreat(player, (), card)
        if _v052_accepted(state, command):
            counts[f"v096_zoom_retreat{'_balloon' if cost.zeroed else ''}{'_confused' if p.active.conditions.confused else ''}"] += 1
            return command
    counts["v096_zoom_retreat_not_accepted"] += 1
    return None


def v096_uses(state):
    """v0.96: ログから数えた v0.96 のカードの動き（v0.96 のカードのない局では空）。``attack_<id>#0``（めざめるパワー）・``power_<id>``（宣言・場に出たときの使う答え）・
    ``entry_declined_<id>``・``engage_returned_<user か opponent>``・``engage_declined_<user か opponent>``・``engage_draw=<枚数>``・``reassure_healed``・``observe_looked``・
    ``search_looked``・``laugh_coin_<表裏>``・``laugh_shuffled``・``tell_coin_<表裏>``・``tell_looked``・``zoom_retreat``（``_balloon``・``_failed``）・``ruin_wall_<id>``・
    ``ruin_wall_benched``・``unown_in_deck=<枚数>``（その局のデッキのアンノーンの枚数の最大）。"""
    counts = Counter()
    if not any(state.cards[uid].card_id in V0_96 for uid in state.cards):
        return counts
    for player in (0, 1):
        owned = sum(1 for uid in state.cards if state.cards[uid].owner == player and state.card_def(uid).category == "pokemon"
                    and state.printed_def(uid).name_group == "アンノーン")
        counts[f"unown_in_deck_p{player}={owned}"] += 1
    power = None
    user = turn_player = None
    for e in state.log:
        kind = e["kind"]
        if kind == "turn_start":
            turn_player = e.get("player")
        if kind == "attack":
            holder = state.cards[e["pokemon"]].card_id if e.get("pokemon") in state.cards else None
            current = e.get("card_id", holder)
            if current in V0_96_POKEMON:
                counts[f"attack_{current}#{e['attack_index']}"] += 1
            power = None
            continue
        if kind == "pokemon_power":
            holder = state.cards[e["pokemon"]].card_id if e.get("pokemon") in state.cards else None
            power, user = (holder, e["player"]) if holder in V0_96_POKEMON else (None, None)
            if power is not None:
                counts[f"power_{power}{'_entry' if e.get('entry') else ''}{'_outside_turn' if e['player'] != turn_player else ''}"] += 1
            continue
        if kind == "entry_power_declined" and e.get("pokemon") in state.cards and state.cards[e["pokemon"]].card_id in V0_96_POKEMON:
            counts[f"entry_declined_{state.cards[e['pokemon']].card_id}"] += 1
            continue
        if kind == "play_trainer" and e.get("card") in state.cards and state.cards[e["card"]].card_id in V0_96_TRAINERS:
            counts[f"ruin_wall_{state.cards[e['card']].card_id}"] += 1
            continue
        if kind == "trainer_bench_from_deck" and e.get("trainer_card") in state.cards and state.cards[e["trainer_card"]].card_id in V0_96_TRAINERS:
            counts[f"ruin_wall_benched_{state.cards[e['card']].card_id}"] += 1
            continue
        if kind in ("retreat", "retreat_failed") and e.get("retreat_cost_power_zeroed"):
            counts[f"zoom_{kind}{'_balloon' if e.get('retreat_cost_zeroed') else ''}"] += 1
            continue
        if kind in ("turn_start", "turn_end"):
            power = None
            continue
        if power is None or not e.get("power", "").startswith(power):
            continue
        who = "user" if e.get("player") == user else "opponent"
        if kind == "hand_to_deck":
            counts[f"engage_returned_{who}"] += 1
        elif kind == "hand_return_declined":
            counts[f"engage_declined_{who}"] += 1
        elif kind == "draw":
            counts[f"engage_draw={len(e['cards'])}"] += 1
        elif kind == "remove_damage_counters":
            counts["reassure_healed"] += 1
        elif kind == "look_at_deck_top":
            counts["observe_looked"] += 1
        elif kind == "look_at_card":
            counts["search_looked"] += 1
        elif kind == "coin_flip":
            counts[f"{'laugh' if power == 'neo4-050' else 'tell'}_coin_{e['result']}"] += 1
        elif kind == "shuffle" and "shuffled_by" in e:
            counts["laugh_shuffled"] += 1
        elif kind == "look_at_hand":
            counts["tell_looked"] += 1
    return +counts


def _v097_source(state, d):
    """v0.97: 決定のもとになった v0.97 のカードの id（アンノーンの特殊能力。なければ None）。"""
    card_id = _v085_source(state, d)
    return card_id if card_id in V0_97_POKEMON else None


def _v097_decision(state, counts):
    """v0.97 の決定への答え（元の手順より先に答える）: ［INCREASE］の使う機会（局の中で使う・使わないを交互に答え、最初の機会は使う。選ぶと止める答え（PW3）は選ばない）・ベンチに出す
    山札のアンノーン・［FIND］・［JOIN］の山札のカード（選べるものを順に回す）。v0.97 のカードの決定でなければ何もしない。"""
    d = state.decision
    if d is None:
        return None
    card_id = _v097_source(state, d)
    if card_id is None:
        return None
    key = f"v097_{card_id}_{d.kind}"
    seen = counts[f"{key}_seen"]
    counts[f"{key}_seen"] += 1
    blocked = set(d.context_value("unresolved_choices", ()) or ())
    if blocked:
        counts[f"{key}_blocked_{d.context_value('unresolved_code')}"] += 1
    if d.min_choices == 0 and (seen % 2 == 1 or all(o in blocked for o in d.options)):
        counts[f"{key}_declined"] += 1
        return ResolveDecision(d.player, d.id, ())
    rotated = list(d.options[seen % len(d.options):]) + list(d.options[:seen % len(d.options)]) if d.options else []
    for choice in [o for o in rotated if o not in blocked]:
        if _v052_accepted(state, ResolveDecision(d.player, d.id, (choice,))):
            counts[f"{key}_answered"] += 1
            return ResolveDecision(d.player, d.id, (choice,))
    if d.min_choices == 0:
        counts[f"{key}_declined_no_choice"] += 1
        return ResolveDecision(d.player, d.id, ())
    counts[f"{key}_no_accepted_answer"] += 1
    return None


def _v097_step(state, tried, counts):
    """v0.97: ［FIND］・［JOIN］を、場のポケモンごとに自分の番ごとに 1 回、受け付けるなら使う。受け付けない理由（文字がそろっていない・ベンチにいない・PW3・特殊能力を消す効果）は
    ``v097_power_<カード>_not_usable_<コード>`` に数える。v0.97 のカードがない局では何もしない。"""
    player = state.current_player
    for pokemon in state.players[player].in_play():
        if state.is_face_down(pokemon):
            continue
        card_id = state.cards[pokemon.card].card_id
        marker = ("v097_power", pokemon.pokemon_id, state.turn_number)
        if card_id not in V097_DECLARED or marker in tried:
            continue
        tried.add(marker)
        use = UsePokemonPower(player, pokemon.pokemon_id, 0)
        real = _V052_REAL.get("state")
        try:
            apply_command(real if real is not None and real.turn_number == state.turn_number and real.decision == state.decision else state, use)
        except (IllegalActionError, UnsupportedError) as error:
            counts[f"v097_power_{card_id}_not_usable_{error.code}"] += 1
            continue
        counts[f"v097_power_{card_id}"] += 1
        return use
    return None


def v097_uses(state):
    """v0.97: ログから数えた v0.97 のカードの動き（v0.97 のカードのない局では空）。``attack_<id>#0``（めざめるパワー）・``power_<id>``（宣言・場に出たときの使う答え）・
    ``entry_declined_<id>``・``increase_benched_<id>``・``find_revealed_<種類>``・``join_revealed_<段階>``・``df_<D か N>_step<段階>_<own か opponent の攻撃>_final<0 か pos>``
    （［DARK df］・［NORMAL df］の「-30」を当てはめたワザのダメージ。持ち主の場のアンノーンが受けた）・``unown_in_deck_p<プレイヤー>=<枚数>``。"""
    counts = Counter()
    if not any(state.cards[uid].card_id in V0_97 for uid in state.cards):
        return counts
    for player in (0, 1):
        owned = sum(1 for uid in state.cards if state.cards[uid].owner == player and state.card_def(uid).category == "pokemon"
                    and state.printed_def(uid).name_group == "アンノーン")
        counts[f"unown_in_deck_p{player}={owned}"] += 1
    power = None
    attacker = None
    for e in state.log:
        kind = e["kind"]
        if kind == "attack":
            holder = state.cards[e["pokemon"]].card_id if e.get("pokemon") in state.cards else None
            current = e.get("card_id", holder)
            if current in V0_97_POKEMON:
                counts[f"attack_{current}#{e['attack_index']}"] += 1
            attacker = e.get("player")
            power = None
            continue
        if kind == "pokemon_power":
            holder = state.cards[e["pokemon"]].card_id if e.get("pokemon") in state.cards else None
            power = holder if holder in V0_97_POKEMON else None
            if power is not None:
                counts[f"power_{power}{'_entry' if e.get('entry') else ''}"] += 1
            continue
        if kind == "entry_power_declined" and e.get("pokemon") in state.cards and state.cards[e["pokemon"]].card_id in V0_97_POKEMON:
            counts[f"entry_declined_{state.cards[e['pokemon']].card_id}"] += 1
            continue
        if kind == "damage":
            for step, source, amount in e.get("modifiers") or ():
                card_id = state.cards[source].card_id if source in state.cards else None
                if card_id in V097_DF and amount == -30:
                    who = "own" if attacker == e.get("player") else "opponent"
                    counts[f"df_{V097_DF[card_id]}_step{step}_{who}_attack_final{'0' if e['amount'] == 0 else 'pos'}"] += 1
            continue
        if kind in ("turn_start", "turn_end"):
            power = None
            continue
        if power is None or not str(e.get("power", "")).startswith(power):
            continue
        if kind == "bench_from_deck":
            counts[f"increase_benched_{state.cards[e['card']].card_id}"] += 1
        elif kind == "reveal_from_deck":
            definition = state.printed_def(e["card"])
            counts[f"{'find' if power == 'neo2-026' else 'join'}_revealed_{definition.category if power == 'neo2-026' else definition.stage}"] += 1
    return +counts


def _v098_source(state, d):
    """v0.98: 決定のもとになった v0.98 のカードの id（アンノーンの特殊能力。なければ None）。"""
    card_id = _v085_source(state, d)
    return card_id if card_id in V0_98_POKEMON else None


def _v098_decision(state, counts):
    """v0.98 の決定への答え（元の手順より先に答える）: ［VANISH］の使う機会（局の中で使う・使わないを交互に答え、最初の機会は使う。選ぶと止める答え（VN1・FD1・AL2）は選ばない）・
    手札にもどすアンノーン、［YIELD］・［GIVE］の山札のカード・つける先（選べるものを順に回す。選ぶと止める答え（RB2・FD1）は選ばない）。v0.98 のカードの決定でなければ何もしない。"""
    d = state.decision
    if d is None:
        return None
    card_id = _v098_source(state, d)
    if card_id is None:
        return None
    key = f"v098_{card_id}_{d.kind}"
    seen = counts[f"{key}_seen"]
    counts[f"{key}_seen"] += 1
    blocked = set(d.context_value("unresolved_choices", ()) or ())
    if blocked:
        counts[f"{key}_blocked_{d.context_value('unresolved_code')}"] += 1
    if d.min_choices == 0 and (seen % 2 == 1 or all(o in blocked for o in d.options)):
        counts[f"{key}_declined"] += 1
        return ResolveDecision(d.player, d.id, ())
    rotated = list(d.options[seen % len(d.options):]) + list(d.options[:seen % len(d.options)]) if d.options else []
    for choice in [o for o in rotated if o not in blocked]:
        if _v052_accepted(state, ResolveDecision(d.player, d.id, (choice,))):
            counts[f"{key}_answered"] += 1
            return ResolveDecision(d.player, d.id, (choice,))
    if d.min_choices == 0:
        counts[f"{key}_declined_no_choice"] += 1
        return ResolveDecision(d.player, d.id, ())
    counts[f"{key}_no_accepted_answer"] += 1
    return None


def _v098_step(state, tried, counts):
    """v0.98: ［BEAR］・［YIELD］・［GIVE］を、場のポケモンごとに自分の番ごとに 1 回、受け付けるなら使う。［BEAR］の移動元は、このカード以外のカウンターののったアンノーンを順に回す
    （なければ、このカード自身（BE1）・移動元なし（BE2）を試し、拒否の理由を数える）。受け付けない理由は ``v098_power_<カード>_not_usable_<コード>`` に数える。v0.98 のカードがない局では
    何もしない。"""
    player = state.current_player
    for pokemon in state.players[player].in_play():
        if state.is_face_down(pokemon):
            continue
        card_id = state.cards[pokemon.card].card_id
        marker = ("v098_power", pokemon.pokemon_id, state.turn_number)
        if card_id not in V098_DECLARED or marker in tried:
            continue
        tried.add(marker)
        if card_id == "neo3-032":
            effect = E.DEFAULT_EFFECTS.power_entry(card_id, 0).effect
            others = [pid for pid in effect.sources(state, player) if pid != pokemon.pokemon_id]
            seen = counts["v098_bear_seen"]
            counts["v098_bear_seen"] += 1
            if others:
                source = others[seen % len(others)]
            elif pokemon.damage >= state.rules.damage_per_counter:
                source = pokemon.pokemon_id
            else:
                source = None
            use = UsePokemonPower(player, pokemon.pokemon_id, 0, source=source)
        else:
            use = UsePokemonPower(player, pokemon.pokemon_id, 0)
        real = _V052_REAL.get("state")
        try:
            apply_command(real if real is not None and real.turn_number == state.turn_number and real.decision == state.decision else state, use)
        except (IllegalActionError, UnsupportedError) as error:
            counts[f"v098_power_{card_id}_not_usable_{error.code}"] += 1
            continue
        counts[f"v098_power_{card_id}"] += 1
        return use
    return None


def v098_uses(state):
    """v0.98: ログから数えた v0.98 のカードの動き（v0.98 のカードのない局では空）。``attack_<id>#0``（めざめるパワー）・``power_<id>``（宣言・場に出たときの使う答え）・
    ``entry_declined_<id>``・``coin_<id>_<表裏>``・``bear_moved_remaining<のせ替えたあとのこのカードの残りHP>``・``attached_<id>_<エネルギーのカード>_to_<self か
    unown か other>``・``vanish_returned_<もどしたカード>``・``vanish_discarded_energy``・``vanish_discarded_trainer``・``vanish_recycled``・``unown_in_deck_p<プレイヤー>=<枚数>``。"""
    counts = Counter()
    if not any(state.cards[uid].card_id in V0_98 for uid in state.cards):
        return counts
    for player in (0, 1):
        owned = sum(1 for uid in state.cards if state.cards[uid].owner == player and state.card_def(uid).category == "pokemon"
                    and state.printed_def(uid).name_group == "アンノーン")
        counts[f"unown_in_deck_p{player}={owned}"] += 1
    power = None
    user = None
    for e in state.log:
        kind = e["kind"]
        if kind == "attack":
            holder = state.cards[e["pokemon"]].card_id if e.get("pokemon") in state.cards else None
            current = e.get("card_id", holder)
            if current in V0_98_POKEMON:
                counts[f"attack_{current}#{e['attack_index']}"] += 1
            power = None
            continue
        if kind == "pokemon_power":
            holder = state.cards[e["pokemon"]].card_id if e.get("pokemon") in state.cards else None
            power, user = (holder, e.get("pokemon_id")) if holder in V0_98_POKEMON else (None, None)
            if power is not None:
                counts[f"power_{power}{'_entry' if e.get('entry') else ''}"] += 1
            continue
        if kind == "entry_power_declined" and e.get("pokemon") in state.cards and state.cards[e["pokemon"]].card_id in V0_98_POKEMON:
            counts[f"entry_declined_{state.cards[e['pokemon']].card_id}"] += 1
            continue
        if kind in ("turn_start", "turn_end"):
            power = None
            continue
        if kind == "energy_returned_to_hand" and power == "neo4-053" and e.get("cause") == "power":
            counts["vanish_recycled"] += 1  # ［VANISH］でトラッシュしたあとに手札にもどったリサイクルエネルギー（discard_attached_cards のすぐあと）
            continue
        if power is None or not str(e.get("power", e.get("effect", ""))).startswith(power):
            continue
        if kind == "coin_flip":
            counts[f"coin_{power}_{e['result']}"] += 1
        elif kind == "move_damage_counter":
            counts[f"bear_moved_remaining{state.printed_def(e['pokemon']).hp - e['to_total_damage']}"] += 1  # のせ替えたあとのこのカードの残りHP
        elif kind == "power_attach_from_deck":
            target = "self" if e["pokemon_id"] == user else "unown" if state.printed_def(e["pokemon"]).name_group == "アンノーン" else "other"
            counts[f"attached_{power}_{state.cards[e['card']].card_id}_to_{target}"] += 1
        elif kind == "discard_attached_cards":
            counts["vanish_discarded_energy"] += len(e["energy"])
            counts["vanish_discarded_trainer"] += len(e["trainers"])
        elif kind == "return_in_play_to_hand":
            counts[f"vanish_returned_{state.cards[e['pokemon']].card_id}"] += 1
    return +counts


def _v099_step(state, tried, counts):
    """v0.99: ［HELP］を、場のポケモンごとに自分の番ごとに 1 回、受け付けるなら使う（手札の枚数によらない）。受け付けない理由（このカードがベンチにいない・文字がそろっていない・特殊能力を
    消す効果）は ``v099_power_<カード>_not_usable_<コード>`` に数える。v0.99 のカードがない局では何もしない。［PERFORM］は宣言しない（手順は何もしない）。"""
    player = state.current_player
    for pokemon in state.players[player].in_play():
        if state.is_face_down(pokemon):
            continue
        card_id = state.cards[pokemon.card].card_id
        marker = ("v099_power", pokemon.pokemon_id, state.turn_number)
        if card_id not in V099_DECLARED or marker in tried:
            continue
        tried.add(marker)
        use = UsePokemonPower(player, pokemon.pokemon_id, 0)
        real = _V052_REAL.get("state")
        try:
            apply_command(real if real is not None and real.turn_number == state.turn_number and real.decision == state.decision else state, use)
        except (IllegalActionError, UnsupportedError) as error:
            counts[f"v099_power_{card_id}_not_usable_{error.code}"] += 1
            continue
        counts[f"v099_power_{card_id}"] += 1
        return use
    return None


def v099_uses(state):
    """v0.99: ログから数えた v0.99 のカードの動き（v0.99 のカードのない局では空）。前の相手の番に受けたダメージ（場のポケモンの番号ごとの、バトル場で受けた分・ベンチで受けた分）は、
    ログの相手のワザのダメージ（返す効果を除く。``target`` のないダメージはバトル場、控えへのダメージはベンチ。ベンチガードの 10 はベンチ）から組み立て直す（エンジンの履歴を読まない）。

    - ``attack_<id>#0``（めざめるパワー・ひれがえし）
    - ［PERFORM］: ``perform_added_<量>``（2 段階の記録があった）・``perform_not_added_<理由>``（``no_damage``: 前の相手の番に受けていない・``zero``: 受けたが 0・``bench_only``:
      ベンチでだけ受けた・``suppressed``: 受けていたが記録がない（特殊能力が消えていた））
    - 「ひれがえし」: ``fin_slap_plus``（基本となる計算 30）・``fin_slap_plain``（20）と、``fin_slap_plus_from_bench``（ベンチでだけ受けていた）
    - ［HELP］: ``help_used``・``help_returned_<枚数>``・``help_drew_<枚数>``・``help_empty_hand``
    - ``unown_in_deck_p<プレイヤー>=<枚数>``"""
    counts = Counter()
    if not any(state.cards[uid].card_id in V0_99 for uid in state.cards):
        return counts
    for player in (0, 1):
        owned = sum(1 for uid in state.cards if state.cards[uid].owner == player and state.card_def(uid).category == "pokemon"
                    and state.printed_def(uid).name_group == "アンノーン")
        counts[f"unown_in_deck_p{player}={owned}"] += 1
    # (番, いちばん上のカードの uid) → [バトル場, ベンチ]。v0.99 のカードはどれもたねポケモン（進化しない）なので、場にいるあいだはいちばん上のカードで同じポケモンを表す。場をはなれたら
    # （きぜつ・手札・山札にもどる）そのカードの記録を消す（出し直したポケモンは別のポケモン）
    received: dict[tuple[int, int], list[int]] = {}
    attack = None  # (番, ワザを使ったプレイヤー, いちばん上のカードの uid, カードの id, ワザの位置)
    helping = None
    for e in state.log:
        kind = e["kind"]
        if kind in ("knock_out", "return_in_play_to_hand", "return_in_play_to_deck"):
            received = {key: value for key, value in received.items() if key[1] != e.get("pokemon")}
        if kind in ("turn_start", "turn_end"):
            attack, helping = None, None
            continue
        if kind == "attack":
            holder = state.cards[e["pokemon"]].card_id if e.get("pokemon") in state.cards else None
            current = e.get("card_id", holder)
            attack = (e["turn"], e["player"], e.get("pokemon"), current, e["attack_index"])
            if current in V0_99_POKEMON:
                counts[f"attack_{current}#{e['attack_index']}"] += 1
            continue
        if kind in ("damage", "bench_guard") and attack is not None and e["player"] != attack[1] and not e.get("retaliation"):
            bench = kind == "bench_guard" or e.get("target", "opponent_active") != "opponent_active"
            received.setdefault((e["turn"], e["pokemon"]), [0, 0])[1 if bench else 0] += e["amount"]
        if kind == "damage" and attack is not None and e["player"] != attack[1] and not e.get("retaliation") and attack[3] in (UNOWN_P, NEO_HORSEA):
            before = received.get((attack[0] - 1, attack[2]), [0, 0])
            steps = [tuple(step) for step in e.get("steps") or ()]
            if attack[3] == UNOWN_P:
                added = [step for step in steps if "［PERFORM" in str(step[0])]
                if added:
                    counts[f"perform_added_{added[0][1] - steps[0][1]}"] += 1
                elif before[0] > 0:
                    counts["perform_not_added_suppressed"] += 1
                elif before[1] > 0:
                    counts["perform_not_added_bench_only"] += 1
                elif (attack[0] - 1, attack[2]) in received:
                    counts["perform_not_added_zero"] += 1
                else:
                    counts["perform_not_added_no_damage"] += 1
            else:
                plus = bool(steps) and steps[0][1] > 20
                counts["fin_slap_plus" if plus else "fin_slap_plain"] += 1
                if plus and before[0] == 0 and before[1] > 0:
                    counts["fin_slap_plus_from_bench"] += 1
        if kind == "pokemon_power" and e.get("pokemon") in state.cards and state.cards[e["pokemon"]].card_id == UNOWN_H:
            counts["help_used"] += 1
            helping = e["player"]
            continue
        if helping is not None and kind == "hand_to_deck" and str(e.get("power", "")).startswith(UNOWN_H):
            counts[f"help_returned_{len(e['cards'])}"] += 1
        elif helping is not None and kind == "shuffle" and str(e.get("power", "")).startswith(UNOWN_H):
            pass
        elif helping is not None and kind == "draw":
            counts[f"help_drew_{len(e['cards'])}"] += 1
            if not e["cards"]:
                counts["help_empty_hand"] += 1
            helping = None
    return +counts



def _logged_turn_attack(state, turn):
    """v0.100: ログの ``turn`` 番に番のプレイヤーが使ったワザ（[プレイヤー, 宣言したワザ, まねたワザ（なければ None）]。なければ None）。エンジンのプレイヤーの記録を読まない。"""
    found = None
    for e in state.log:
        if e.get("turn") != turn:
            continue
        if e["kind"] == "attack":
            card_id = e.get("card_id") or state.cards[e["pokemon"]].card_id
            found = [e["player"], f"{card_id}#{e['attack_index']}", None]
        elif e["kind"] == "copy_attack" and found is not None:
            found[2] = e["copied"]
    return found


def _v100_sketch_copy_type(state, command):
    """v0.100: スケッチで使うワザ（ログの前の相手の番の宣言したワザ）の実装の型の名前（なければ None）。"""
    found = _logged_turn_attack(state, state.turn_number - 1)
    if found is None or found[0] == command.player:
        return None
    card_id, index = found[1].split("#")
    definition = state.definitions[card_id]
    return type(state.effects.attack_effect(card_id, definition.attacks[int(index)], definition.attacks)).__name__


def _v100_night_eyes_unclear(state, command):
    """v0.100（PSG1 の確かめ）: 相手の対戦ポケモンが今ねむりで、ログの前の自分の番（2 つ前の番）に、そのポケモンへのやみのひとみの効果が「効果だけを無効にする効果」で無効になったか、
    やみのひとみが相手のワザなどを自分のワザとして使ったもの（copy_attack の copied）だった。"""
    defender = _defender(state, command)
    if defender is None or not defender.conditions.asleep:
        return False
    turn = state.turn_number - 2
    window = None
    for e in state.log:
        if e.get("turn") != turn:
            continue
        if e["kind"] == "attack" and e["player"] == command.player:
            window = "declared"
        elif (e["kind"] == "copy_attack" and window is not None and e["copied"] == f"{MISDREAVUS}#0") or (
                e["kind"] == "effect_prevented" and e.get("pokemon_id") == defender.pokemon_id and e.get("element") == "sleep"
                and e.get("persistent_effect") != "attack_barrier"):
            return True
    return False


def _v100_attack(state, tried, counts):
    """v0.100: スケッチ（払えれば使う）・やみのひとみ（相手の対戦ポケモンがねむりでなければ）・ほろびのうた（相手がねむりなら。ねむりでなく、やみのひとみを払えないときも使う）。
    v0.100 のカードのない局では何もしない。この番に拒否されたワザ（``("attack_index", 位置)``）は選ばない。"""
    if "attack" in tried:
        return None
    player = state.current_player
    active = state.players[player].active
    if active is None or active.conditions.asleep or active.conditions.paralyzed or current_form(state, active).kind != "printed":
        return None
    card_id = state.cards[active.card].card_id
    if card_id not in V0_100:
        return None
    attacks = state.card_def(active.card).attacks

    def payable(index):
        return ("attack_index", index) not in tried and attack_cost_payable(state, active, attacks[index])

    if card_id == SMEARGLE and payable(0):
        counts["v100_sketch"] += 1
        return UseAttack(player, 0)
    if card_id == MISDREAVUS:
        target = state.players[1 - player].active
        asleep = target is not None and target.conditions.asleep
        if asleep and payable(1):
            counts["v100_perish_song_asleep"] += 1
            return UseAttack(player, 1)
        if not asleep and payable(0):
            counts["v100_night_eyes"] += 1
            return UseAttack(player, 0)
        if payable(1):
            counts["v100_perish_song_awake"] += 1
            return UseAttack(player, 1)
    return None


def _v101_keep_on(state, owner, pokemon) -> bool:
    """v0.101: プレイヤー ``owner`` の場に、はたらいている［KEEP］（アンノーンK）があり、場のポケモン ``pokemon`` の今の姿が「アンノーン」か（場から確かめる。かがくへんかガスなどは
    共通の ``continuous_powers``。エンジンの ``energy_discard_void`` は読まない）。"""
    if pokemon is None or state.is_face_down(pokemon) or E.form_def(state, pokemon).name_group != "アンノーン":
        return False
    return any(o == owner for o, _, _, _ in E.continuous_powers(state, E.VoidOpponentEnergyDiscardOnGroup))


def _v101_sample_program(cls, build):
    """v0.101: 登録表にある ``cls`` の実装の 1 つから作った要素の並び（写したワザの型の名前から、トラッシュだけを決めるコインを持つかを見るため）。"""
    for key in DEFAULT_EFFECTS_FOR_TOOL.attack_keys():
        entry = DEFAULT_EFFECTS_FOR_TOOL.attack_entry(key.card_id, key.attack_index)
        if type(entry.effect) is cls:
            return tuple(build(entry.effect))
    return ()


def _v101_keep_coin_expected(state, command) -> bool:
    """v0.101（KP2 の確かめ）: このワザ（写したワザも）が相手のアンノーンのエネルギーカードのトラッシュだけを決めるコインを持ち、相手の場のエネルギーカードのついたアンノーンに
    ［KEEP］がはたらく。または、ワザを使うアンノーンに自分の［KEEP］がはたらき、相手の対戦ポケモンが［だつりょくえき］を持つ。"""
    from kyuura_engine.resolution.programs import BUILDERS, DiscardOpponentEnergy

    coin_types = {cls.__name__ for cls, build in BUILDERS.items()
                  if any(isinstance(element, DiscardOpponentEnergy) and element.local_coin is not None for element in _v101_sample_program(cls, build))}
    opponent = 1 - command.player
    effect = _attack_effect(state, command)
    own = any(isinstance(element, DiscardOpponentEnergy) and element.local_coin is not None for element in BUILDERS.get(type(effect), lambda e: ())(effect))
    if (own or coin_types & (_attack_and_copied_types(state, command) - {type(effect).__name__})) and any(
            pokemon.energy and _v101_keep_on(state, opponent, pokemon) for pokemon in state.players[opponent].in_play()):
        return True
    defender = state.players[opponent].active
    return defender is not None and any(isinstance(slot.effect, E.DiscardAttackerEnergyOnDamage) for slot in E.powers_of(state, defender)) \
        and _v101_keep_on(state, command.player, _attacker(state, command))


def _v101_attack(state, tried, counts):
    """v0.101: ソーナンスは「カウンター」を払えれば使う（ほかにワザがない。ダメージを与えない）。v0.101 のカードのない局では何もしない。この番に拒否されたワザは選ばない。
    アンノーンK の「めざめるパワー」は既存の手順のまま。"""
    if "attack" in tried:
        return None
    player = state.current_player
    active = state.players[player].active
    if active is None or active.conditions.asleep or active.conditions.paralyzed or current_form(state, active).kind != "printed":
        return None
    if state.cards[active.card].card_id != WOBBUFFET:
        return None
    attack = state.card_def(active.card).attacks[0]
    if ("attack_index", 0) not in tried and attack_cost_payable(state, active, attack):
        counts["v101_counter"] += 1
        return UseAttack(player, 0)
    return None


def _v102_attack_observe(state, seen, counts) -> None:
    """v0.102: 前に見た番の場（``seen["v102"]``。番のプレイヤーと、相手の対戦ポケモンに当てはまるはたらく力の有無）のあとに、そのプレイヤーのワザのログ（``attack``）があれば、
    ワザを宣言した時点で相手の対戦ポケモンに［グリーンシールド］・［ニュートラルダメージ］が当てはまる配置にあったとして数え（``v102_attack_power_weakness``・
    ``v102_attack_power_resistance``）、今の場を記録する。拒否されたコマンドはワザのログを残さないので数えない。v0.102 の力のない場では何も記録しない（前の版の組の結果は変わらない）。
    数えるのに使う問い合わせはエンジンの ``weakness_resistance_ignored``（監査はログから別に組み立てる）。"""
    previous = seen.pop("v102", None)
    if previous is not None:
        index, player, weakness, resistance = previous
        if any(e["kind"] == "attack" and e["player"] == player for e in state.log[index:]):
            if weakness:
                counts["v102_attack_power_weakness"] += 1
            if resistance:
                counts["v102_attack_power_resistance"] += 1
    if state.phase is not Phase.MAIN or not E.continuous_powers(state, E.WeaknessResistancePower):
        return
    player = state.current_player
    receiver = state.players[1 - player].active
    if receiver is None or state.is_face_down(receiver):
        return
    receiving = E.Receiving(1 - player, receiver)
    found = [E.weakness_resistance_ignored(state, receiving, color) for color in E.type_readings(state, receiver)]
    weakness, resistance = any(f.weakness for f in found), any(f.resistance for f in found)
    if weakness or resistance:
        seen["v102"] = (len(state.log), player, weakness, resistance)


_V102_NON_ADD = ("damage_set", "damage_multiplied", "damage_zero_below", "damage_zero_at_least", "damage_set_if_at_least", "damage_halved", "damage_reduced",
                 "bench_guard", "weakness_multiplier")


def _v102_final_without(state, e, stadium_seen: bool) -> int | None:
    """v0.102: 力で影響を受けなかった弱点・抵抗力を当てはめていたときの最終ダメージ（ログの計算の段階から求める）。2 段階のあとが加算（``modifiers``）だけで、スタジアムのない局の
    ときだけ求め、ほかは None（決めない）。"""
    if stadium_seen or any(key in e for key in _V102_NON_ADD):
        return None
    steps = [tuple(step) for step in e.get("steps") or ()]
    early = [amount for label, amount in steps if str(label)[:1] in ("1", "2") or e["kind"] == "confusion_damage" and label == "こんらん"]
    if not early:
        return None
    amount = early[-1]
    if e.get("weakness_ignored_by_powers"):
        amount *= state.rules.weakness_multiplier
    if e.get("resistance_ignored_by_powers"):
        amount -= state.card_def(e["pokemon"]).resistance_value or 0
    amount += sum(added for step, _, added in e.get("modifiers", ()) if step >= 5)
    return max(amount, 0)


def v102_uses(state):
    """v0.102: ログから数えた v0.102 のカードの動き（v0.102 のカードのない局では空）。

    - ``attack_<id>#0``（ふしぎなこな・ジャグリング。id ごと）
    - 力で影響を受けなかった弱点・抵抗力（ログ ``weakness_ignored_by_powers``・``resistance_ignored_by_powers``）: ``<damage|confusion_damage|retaliation>_weakness_ignored``・
      ``…_resistance_ignored``、はたらいた力のカードの id ごとの ``weakness_ignored_by_<id>``・``resistance_ignored_by_<id>``、受けたポケモンの場所 ``ignored_on_bench``
    - 最終ダメージ: ``final_changed``（当てはめていたら違った）・``final_same``・``final_undetermined``（加算でない計算・スタジアム・ベンチガードなどで求めない）"""
    counts = Counter()
    if not any(state.cards[uid].card_id in V0_102 for uid in state.cards):
        return counts
    stadium_seen = False
    for e in state.log:
        kind = e["kind"]
        if kind == "stadium_placed":
            stadium_seen = True
        if kind == "attack":
            current = e.get("card_id") or state.cards[e["pokemon"]].card_id
            if current in V0_102:
                counts[f"attack_{current}#{e['attack_index']}"] += 1
            continue
        if kind not in ("damage", "confusion_damage"):
            continue
        weakness, resistance = e.get("weakness_ignored_by_powers", ()), e.get("resistance_ignored_by_powers", ())
        if not weakness and not resistance:
            continue
        label = "retaliation" if e.get("retaliation") else kind
        for part, sources in (("weakness", weakness), ("resistance", resistance)):
            if sources:
                counts[f"{label}_{part}_ignored"] += 1
                for card in sorted({str(source[1]).split("@")[0] for source in sources}):
                    counts[f"{part}_ignored_by_{card}"] += 1
        if e.get("target") in ("opponent_bench", "self_bench"):
            counts["ignored_on_bench"] += 1
        without = _v102_final_without(state, e, stadium_seen)
        counts["final_undetermined" if without is None else "final_changed" if without != e["amount"] else "final_same"] += 1
    return counts


def _v103_stage(state, uid) -> str | None:
    """v0.103: 数えるための、カード ``uid``（場のポケモンのいちばん上のカード）の印刷の段階（今の姿は数えない。監査は今の姿をログから別に組み立てる）。"""
    return None if uid is None else state.printed_def(uid).stage


def v103_uses(state):
    """v0.103: ログから数えたミュウの［ニュートラルシールド］の動き（ミュウのない局では空）。

    - ``attack_<id>#0``（ねんりき。id ごと）
    - 候補: 相手のワザ（返す効果を含む）の要素がミュウを対象にした回数（``candidate_<damage|effect>``。ログ ``damage``・``damage_prevented``・``effect_prevented``・ワザの ``special_condition``）
    - 防いだもの: ``prevented_damage_<attack|retaliation>``・``prevented_effect_<要素>``、発生元の段階ごとの ``prevented_by_<段階>``、ベンチで防いだ ``prevented_on_bench``
    - 防がずに進んだもの: たねポケモンのワザ（``passed_basic_<damage|effect>``）・自分のワザ（``passed_own``）・進化ポケモンのワザで力がはたらかなかった・受けるポケモン自身の効果を除く
      ワザ（``passed_evolved_unprotected``）・特殊能力のダメージ（``power_damage_on_mew``）・こんらん（``confusion_on_mew``）
    - 防いだワザの中で残った有効な要素（``remaining_after_prevented``。同じワザの、ほかのポケモン・自分へのダメージと効果のログ）"""
    counts = Counter()
    if not any(state.cards[uid].card_id in V0_103 for uid in state.cards):
        return counts
    window = None  # 今のワザの {"player", "stage", "ret": (player, stage) | None, "prevented": bool}
    for e in state.log:
        kind = e["kind"]
        if kind == "attack":
            current = e.get("card_id") or state.cards[e["pokemon"]].card_id
            if current in V0_103:
                counts[f"attack_{current}#{e['attack_index']}"] += 1
            window = {"player": e["player"], "stage": _v103_stage(state, e["pokemon"]), "ret": None, "prevented": False}
            continue
        if kind in ("turn_end", "game_end", "halted"):
            window = None
            continue
        if window is None:
            continue
        if kind == "retaliation":
            window["ret"] = (e["player"], _v103_stage(state, e["pokemon"]))
            continue
        if kind in ("counterattack", "shock_blast_damage"):
            target = e.get("attacker_pokemon") if kind == "counterattack" else e.get("target_pokemon")
            if target is not None and state.cards[target].card_id in V0_103:
                counts["power_damage_on_mew"] += 1
            continue
        if kind == "confusion_damage":
            if state.cards[e["pokemon"]].card_id in V0_103:
                counts["confusion_on_mew"] += 1
            continue
        if kind not in ("damage", "damage_prevented", "effect_prevented", "special_condition"):
            continue
        if kind == "special_condition" and e.get("effect", "").find("#") < 0:
            continue  # ワザでない特殊状態（特殊能力・トレーナー）
        on_mew = state.cards[e["pokemon"]].card_id in V0_103
        retaliation = bool(e.get("retaliation"))  # 返す効果のダメージ（damage・damage_prevented の印）
        player, stage = window["ret"] if retaliation and window["ret"] is not None else (window["player"], window["stage"])
        part = "damage" if kind in ("damage", "damage_prevented") else "effect"
        if not on_mew:
            if window["prevented"] and kind in ("damage", "special_condition"):
                counts["remaining_after_prevented"] += 1
            continue
        if player == e["player"]:
            counts["passed_own"] += 1
            continue
        counts[f"candidate_{part}"] += 1
        if kind in ("damage_prevented", "effect_prevented"):
            if e.get("persistent_effect") == "neutral_shield":
                window["prevented"] = True
                counts[f"prevented_damage_{'retaliation' if retaliation else 'attack'}" if part == "damage" else f"prevented_effect_{e.get('element')}"] += 1
                counts[f"prevented_by_{stage}"] += 1
                if e.get("target") == "opponent_bench":
                    counts["prevented_on_bench"] += 1
            continue
        counts[f"passed_basic_{part}" if stage == "basic" else "passed_evolved_unprotected"] += 1
    return counts


def _v104_decision(state, counts):
    """v0.104 のワザの決定への答え（元の手順より先に答える）: あまいみつの選ぶポケモン（自分の場。選べるものを順に回す。ダメージカウンターののっていないポケモンも順に選ぶ）・プリンの
    かいふくの取り除くか（対戦の中の 2 回目ごとに取り除かない）・相手の v0.104 のワザを自分のワザとして使うときのワザ（相手がねむりなら、自分をねむりにするワザを選ばない）。受け付ける
    答えだけを選ぶ。v0.104 のワザの決定（相手のワザとして使ったものも）でなければ何もしない。"""
    d = state.decision
    if d is None:
        return None
    if d.kind == SELECT_ATTACK and d.context_value("copy_from") in V0_104:
        # 相手の v0.104 のワザを自分のワザとして使う（ゆびをふる）: 相手の対戦ポケモンがねむりなら、自分をねむりにするワザ（おひるね・ねむる）は選ばない（両方のねむりは、ポケモン
        # チェックの既知の停止）。ほかは元の手順のまま
        opponent = state.players[1 - d.player].active
        source = d.context_value("copy_from")
        if opponent is None or not opponent.conditions.asleep:
            return None
        awake = [i for i in d.options if not isinstance(state.effects.attack_entry(source, i).effect, E.HealAllSelfThenSelfSleep)
                 and i not in (d.context_value("unsupported_choices", ()) or ()) and i not in (d.context_value("unresolved_choices", ()) or ())]
        for choice in awake:
            if _v052_accepted(state, ResolveDecision(d.player, d.id, (choice,))):
                counts["v104_copied_self_sleep_avoided"] += 1
                return ResolveDecision(d.player, d.id, (choice,))
        return None
    card_id = _v085_source(state, d)
    if card_id not in V0_104 or d.kind not in (SELECT_POKEMON, OPTIONAL_HEAL):
        return None
    key = f"v104_{card_id}_{d.kind}"
    counts[f"{key}_seen"] += 1
    seen = counts[f"v104_{d.kind}_seen"]  # 決定の種類ごとに、対戦の中で数える
    counts[f"v104_{d.kind}_seen"] += 1
    if d.kind == OPTIONAL_HEAL:
        candidates = [()] if seen % 2 == 1 else [tuple(d.options), ()]
    else:
        blocked = set(d.context_value("unresolved_choices", ()) or ())
        rotated = list(d.options[seen % len(d.options):]) + list(d.options[:seen % len(d.options)]) if d.options else []
        candidates = [(o,) for o in rotated if o not in blocked]
    for choices in candidates:
        if d.min_choices <= len(choices) <= d.max_choices and _v052_accepted(state, ResolveDecision(d.player, d.id, choices)):
            counts[f"{key}_{len(choices)}"] += 1
            return ResolveDecision(d.player, d.id, choices)
    counts[f"{key}_no_accepted_answer"] += 1
    return None


def v104_uses(state):
    """v0.104: ログから数えた回復のワザの動き（v0.104 のカードのない局では空）。

    - ``attack_<id>#<位置>``（宣言したワザ。印刷したカードの id ごと）・``copied_<id>#<位置>``（ほかのワザが相手のワザとして使った v0.104 のワザ）
    - ``heal_<実装>``（attack_heal の回数）・``heal_counters_<実装>``（とりのぞいた数の合計）・``heal_full_<実装>``（のっているすべてをとりのぞいた）・
      ``heal_other_own``（ワザを使ったポケモンでない自分のポケモンから）・``heal_opponent``（相手のポケモンから）・``heal_none_<実装>``（ワザの処理でとりのぞかなかった。0 個・「うら」・受けなかった）・``heal_declined``（取り除かなかった）
    - ``milk_heads_<数>``（ミルクのみの「おもて」の数）・``flower_dance_base_<量>``（フラワーダンスの基本となるダメージ）
    - ``sleep_self``・``sleep_opponent``（v0.104 のワザのねむり）・``cured_<状態>``（ねむるで回復させた特殊状態）・``replaced_by_sleep``（おひるねでねむりに置きかわった）
    - ``lock_added``・``lock_skipped``（もうとっしんの「使えない」効果）
    - ``prevented_<要素>``・``evaded_<要素>``・``immune_<状態>``（v0.104 のワザの要素を受けなかった。［ニュートラルシールド］など・「とうめい」・［めんえき］）"""
    counts = Counter()
    if not any(state.cards[uid].card_id in V0_104 for uid in state.cards):
        return counts
    window = None  # 今のワザの {"keys": v0.104 のワザの effect, "impl": 実装, "healed": bool, "declined": bool}
    for e in state.log:
        kind = e["kind"]
        if kind in ("attack", "turn_end", "game_end", "halted"):
            if window is not None and window["impl"] is not None and not window["healed"] and not window["declined"] and window["impl"] in V104_HEAL_IMPLS:
                counts[f"heal_none_{window['impl']}"] += 1
            window = None
        if kind == "attack":
            current = e.get("card_id") or state.cards[e["pokemon"]].card_id
            key = f"{current}#{e['attack_index']}"
            if current in V0_104:
                counts[f"attack_{key}"] += 1
            window = {"key": key, "impl": _v104_impl(state, key) if current in V0_104 else None, "healed": False, "declined": False, "attacker_card": e["pokemon"]}
            continue
        if window is None:
            continue
        if kind == "copy_attack" and e["copied"].split("#")[0] in V0_104:
            counts[f"copied_{e['copied']}"] += 1
            window["key"], window["impl"] = e["copied"], _v104_impl(state, e["copied"])
            continue
        if e.get("effect") != window["key"] or window["impl"] is None:
            if kind == "damage" and window["impl"] == "own_named_pokemon_count_damage" and not e.get("retaliation") and e.get("steps"):
                counts[f"flower_dance_base_{e['steps'][0][1]}"] += 1
            if kind == "special_conditions_removed" and e.get("reason") == "replaced" and window["impl"] == "heal_all_self_then_self_sleep":
                counts["replaced_by_sleep"] += 1  # 置きかえのログは effect を持たない（ねむりにする直前のログ）
            continue
        impl = window["impl"]
        if kind == "attack_heal":
            window["healed"] = True
            counts[f"heal_{impl}"] += 1
            counts[f"heal_counters_{impl}"] += e["counters"]
            if e["total_damage"] == 0:
                counts[f"heal_full_{impl}"] += 1
            if "attacker" in e:
                counts["heal_opponent"] += 1
            elif e["pokemon"] != window["attacker_card"]:
                counts["heal_other_own"] += 1  # ワザを使ったポケモンでない自分のポケモン（あまいみつの控え）
        elif kind == "attack_heal_declined":
            window["declined"] = True
            counts["heal_declined"] += 1
        elif kind == "special_condition" and e.get("condition") == "sleep":
            counts["sleep_opponent" if "attacker" in e or impl == "heal_both_actives_then_sleep" else "sleep_self"] += 1
        elif kind == "special_conditions_removed":
            if e.get("reason") == "cured":
                for condition in e["conditions"]:
                    counts[f"cured_{condition}"] += 1
        elif kind == "persistent_effect_added" and e.get("persistent_effect") == "cannot_use_own_attack":
            counts["lock_added"] += 1
        elif kind == "persistent_effect_skipped":
            counts["lock_skipped"] += 1
        elif kind in ("effect_prevented", "damage_prevented"):
            counts[f"prevented_{e.get('element', 'damage')}"] += 1
        elif kind == "attack_evaded":
            counts[f"evaded_{e.get('element')}"] += 1
        elif kind == "special_condition_prevented":
            counts[f"immune_{e.get('condition')}"] += 1
    # ミルクのみの「おもて」の数（ワザごと）
    window_key, heads = None, None
    for e in state.log:
        if e["kind"] == "attack":
            if heads is not None:
                counts[f"milk_heads_{heads}"] += 1
            window_key, heads = f"{e.get('card_id') or state.cards[e['pokemon']].card_id}#{e['attack_index']}", None
            if window_key == f"{MILTANK}#0":
                heads = 0
        elif e["kind"] == "copy_attack" and e["copied"] == f"{MILTANK}#0":
            window_key, heads = e["copied"], 0
        elif e["kind"] == "coin_flip" and heads is not None and e.get("effect") == window_key and e.get("source") == "attack":
            heads += e["result"] == "heads"
        elif e["kind"] == "esp_redo" and heads is not None and e.get("effect") == window_key:
            heads = list(e["redone"]).count("heads")
    if heads is not None:
        counts[f"milk_heads_{heads}"] += 1
    return counts


def _v105_decision(state, counts):
    """v0.105 のワザの決定への答え（元の手順より先に答える）: からやぶりしんか・ひざしをあびる（相手のワザとして使ったものも）の山札から重ねる進化カード（SEARCH_DECK）は、選べるものを
    順に回して 1 枚（選ぶと止めるものは選ばない）。選べるもののない決定は 0 枚。v0.105 のワザの決定でなければ何もしない。"""
    d = state.decision
    if d is None or d.resume != "attack" or d.kind != SEARCH_DECK:
        return None
    use = d.context_value("use")
    copied = d.context_value("copied")
    source = copied if copied else (None if use is None else (use[2], use[3]))
    if source is None or source[0] not in V0_105:
        return None
    entry = state.effects.attack_entry(source[0], source[1])
    if entry is None or not isinstance(entry.effect, E.CoinHealAllThenEvolveSelfFromDeck):
        return None
    seen = counts["v105_search_seen"]
    counts["v105_search_seen"] += 1
    blocked = set(d.context_value("unresolved_choices", ()) or ()) | set(d.context_value("entry_power_choices", ()) or ())
    rotated = list(d.options[seen % len(d.options):]) + list(d.options[:seen % len(d.options)]) if d.options else []
    candidates = [(o,) for o in rotated if o not in blocked] if d.max_choices else [()]
    for choices in candidates:
        if _v052_accepted(state, ResolveDecision(d.player, d.id, choices)):
            counts[f"v105_search_{len(choices)}"] += 1
            return ResolveDecision(d.player, d.id, choices)
    counts["v105_search_no_accepted_answer"] += 1
    return None


def v105_uses(state):
    """v0.105: ログから数えた 5 枚のワザの動き（v0.105 のカードのない局では空）。

    - ``attack_<id>#<位置>``（宣言したワザ）・``copied_<id>#<位置>``（ほかのワザが相手のワザとして使った v0.105 のワザ）
    - ``evolve_coin_<面>``（からやぶりしんか・ひざしをあびるのコイン）・``evolve_heal``・``evolve_heal_counters``（「おもて」でとりのぞいた回数・数）・``evolve_to_<カード id>``（山札から重ねた
      進化カード）・``evolve_none``（選べるカードがない・山札がない）・``evolve_shuffle``（そのワザで切った）・``evolve_by_copier``（相手のワザとして使ったポケモンが進化した）
    - ``hyper_reverse_base_<量>``・``psychic_leaf_base_<量>``・``present_damage_base_<量>``（相手への基本となるダメージ）・``psychic_leaf_coins_<枚数>``・``drain_<実装>``・
      ``drain_counters_<実装>``（与えたぶんの回復）・``drain_none_<実装>``（ダメージを与えなかった・のっていない・受けなかった）
    - ``present_heads_<数>``・``present_heal``・``present_heal_counters``・``present_heal_none``（「おもて」2 枚・0 枚で、相手にのっていない・受けなかった）
    - ``harden_zero``・``harden_through``（トランセルのかたくなるの持続する効果を計算したダメージで、0 にした・しきい値以上でそのまま受けた）
    - ``prevented_<要素>``・``evaded_<要素>``（v0.105 のワザの要素を受けなかった。［ニュートラルシールド］など・「とうめい」）"""
    counts = Counter()
    if not any(state.cards[uid].card_id in V0_105 for uid in state.cards):
        return counts
    window = None
    for e in state.log:
        kind = e["kind"]
        if kind == "damage" and not e.get("retaliation"):
            labels = [str(step[0]) for step in (e.get("steps") or ())[1:]]
            if any("トランセル（zero_damage_below）" in label for label in labels):
                counts["harden_zero" if e.get("amount") == 0 else "harden_through"] += 1
        if kind in ("attack", "turn_end", "game_end", "halted"):
            if window is not None:
                _v105_close(window, counts)
            window = None
        if kind == "attack":
            current = e.get("card_id") or state.cards[e["pokemon"]].card_id
            key = f"{current}#{e['attack_index']}"
            if current in V0_105:
                counts[f"attack_{key}"] += 1
            window = {"key": key, "impl": _v104_impl(state, key) if current in V0_105 else None, "player": e["player"], "copied": False, "heads": 0, "coins": 0,
                      "drained": False, "healed": False}
            continue
        if window is None:
            continue
        if kind == "copy_attack" and e["copied"].split("#")[0] in V0_105:
            counts[f"copied_{e['copied']}"] += 1
            window["key"], window["impl"], window["copied"] = e["copied"], _v104_impl(state, e["copied"]), True
            continue
        impl = window["impl"]
        if impl is None:
            continue
        if kind == "damage" and impl in V105_DAMAGE_IMPLS and not e.get("retaliation") and e.get("steps") and e["player"] != window["player"]:
            counts[f"{V105_DAMAGE_IMPLS[impl]}_base_{e['steps'][0][1]}"] += 1  # damage のログは effect を持たない
            continue
        if e.get("effect") != window["key"]:
            continue
        if kind == "coin_flip" and e.get("source") == "attack":
            window["coins"] += 1
            window["heads"] += e["result"] == "heads"
            if impl == "coin_heal_all_then_evolve_self_from_deck":
                counts[f"evolve_coin_{e['result']}"] += 1
        elif kind == "esp_redo":
            window["coins"], window["heads"] = len(e["redone"]), list(e["redone"]).count("heads")
        elif kind == "attack_heal":
            window["healed"] = True
            if impl == "coin_heal_all_then_evolve_self_from_deck":
                counts["evolve_heal"] += 1
                counts["evolve_heal_counters"] += e["counters"]
            elif impl == "three_coin_damage_or_opponent_heal":
                counts["present_heal"] += 1
                counts["present_heal_counters"] += e["counters"]
        elif kind == "evolve":
            counts[f"evolve_to_{state.cards[e['to_card']].card_id}"] += 1
            if window["copied"]:
                counts["evolve_by_copier"] += 1
        elif kind == "evolve_from_deck_none":
            counts["evolve_none"] += 1
        elif kind == "shuffle":
            counts["evolve_shuffle"] += 1
        elif kind == "drain_heal":
            window["drained"] = True
            counts[f"drain_{impl}"] += 1
            counts[f"drain_counters_{impl}"] += e["counters"]
        elif kind in ("effect_prevented", "damage_prevented"):
            counts[f"prevented_{e.get('element', 'damage')}"] += 1
        elif kind == "attack_evaded":
            counts[f"evaded_{e.get('element')}"] += 1
    if window is not None:
        _v105_close(window, counts)
    return counts


V105_DAMAGE_IMPLS = {"defender_energy_units_damage_and_full_drain": "hyper_reverse", "coins_per_defender_energy_bonus_and_full_drain": "psychic_leaf",
                     "three_coin_damage_or_opponent_heal": "present_damage"}


def _v105_close(window, counts):
    """v0.105: 1 回のワザの終わりに数える（サイコリーフのコインの枚数・与えたぶんの回復がなかった・プレゼントの「おもて」の数と回復がなかった）。"""
    impl = window["impl"]
    if impl == "coins_per_defender_energy_bonus_and_full_drain":
        counts[f"psychic_leaf_coins_{window['coins']}"] += 1
    if impl in ("defender_energy_units_damage_and_full_drain", "coins_per_defender_energy_bonus_and_full_drain") and not window["drained"]:
        counts[f"drain_none_{impl}"] += 1
    if impl == "three_coin_damage_or_opponent_heal" and window["coins"] == 3:
        counts[f"present_heads_{window['heads']}"] += 1
        if window["heads"] in (0, 2) and not window["healed"]:
            counts["present_heal_none"] += 1


def v105_replay_problems(state, deck_before: dict[int, int]) -> list[str]:
    """v0.105: からやぶりしんか・ひざしをあびる（相手のワザとして使ったものも）の山札を切る回数を、やり直しの状態で数えたワザの宣言の直前の山札の枚数（``deck_before``。宣言を処理する
    前のログの長さ → 枚数）と照らす（エンジンの ``EvolveAttackerFromDeck`` を読まない）: コインが「おもて」で山札にカードがあれば、そのワザで 1 回だけ切る（見たので）。「うら」・山札が 0 枚なら
    切らない。宣言から山札を見るまでのあいだに山札のカードは動かない（コイン・回復だけ）。宣言を受け付けなかった（ログが増えない・attack のない）操作は数えない。"""
    problems = []
    log = state.log
    starts = {}
    for position, count in deck_before.items():
        index = next((j for j in range(position, len(log)) if log[j]["kind"] == "attack"), None)
        if index is not None and all(log[j]["turn"] == log[index]["turn"] for j in range(position, index + 1)):
            starts[index] = count
    for index, e in enumerate(log):
        if e["kind"] != "attack" or index not in starts:
            continue
        key = f"{e.get('card_id') or state.cards[e['pokemon']].card_id}#{e['attack_index']}"
        end = next((j for j in range(index + 1, len(log)) if log[j]["kind"] in ("attack", "turn_end", "game_end", "halted")), len(log))
        body = log[index + 1:end]
        copied = next((x["copied"] for x in body if x["kind"] == "copy_attack" and x.get("effect") == key), None)
        key = copied or key
        if _v104_impl(state, key) != "coin_heal_all_then_evolve_self_from_deck":
            continue
        flips = [x for x in body if x["kind"] == "coin_flip" and x.get("source") == "attack" and x.get("effect") == key]
        redo = [x for x in body if x["kind"] == "esp_redo" and x.get("effect") == key]
        result = next(iter(redo[-1]["redone"])) if redo else (flips[0]["result"] if flips else None)
        shuffles = sum(1 for x in body if x["kind"] == "shuffle" and x.get("effect") == key and x["player"] == e["player"])
        expected = 1 if result == "heads" and starts[index] > 0 else 0
        if result is not None and shuffles != expected:
            problems.append(f"{e['turn']} 番の {key}（コイン {result}・宣言の前の山札 {starts[index]} 枚）で山札を {shuffles} 回切った（{expected} 回のはず）")
    return problems


# v0.106: 数える実装（登録の実装の id → 数える名前）。みんなでスパーク・なかまのちからは v0.39 の型なので、v0.106 のカードのワザのときだけ（名前で分ける）
V106_IMPLS = {"damage_plus_own_counters_then_self_damage": "raging", "coins_heads_table_bonus_damage": "fury", "capped_coins_per_attached_energy_cards_damage": "hydro",
              "damage_plus_opponent_prizes_taken": "grudge", "coins_bonus_and_self_damage_per_heads": "needle"}
V106_COUNT_NAMES = {"みんなでスパーク": "spark", "なかまのちから": "family"}


def v106_uses(state):
    """v0.106: ログから数えた 11 枚のワザの動き（v0.106 のカードのない局では空）。

    - ``attack_<id>#<位置>``（宣言したワザ）・``copied_<id>#<位置>``（ほかのワザが相手のワザとして使った v0.106 のワザ）
    - ``<名前>_base_<量>``（相手への基本となるダメージ。raging・fury・hydro・grudge・needle・spark・family）・``<名前>_self_<量>``（自分への基本となるダメージ。raging・needle）
    - ``fury_heads_<数>``・``hydro_coins_<枚数>``・``needle_heads_<数>``（このワザのコインの枚数・「おもて」の数。ESP でやり直したらやり直した結果）
    - ``spark_counted_<数>``・``family_counted_<数>``・``grudge_taken_<数>``（基本となるダメージから求めた、数えたポケモン・相手が取ったサイドの数）
    - ``opponent_void_<名前>``（相手へのダメージを無効にした・受けなかった）・``self_after_void_<名前>``（そのあとの自分へのダメージ）
    - ``<名前>_interrupted``（こんらんのコインなどでワザが失敗した。コイン・ダメージを数えない）
    - ``leek_lock``（ネギでつくの持続する効果）・``harden_zero``・``harden_through``（イシツブテのかたくなるの持続する効果を計算したダメージで、0 にした・そのまま受けた）・
      ``sand_cloak``（すながくれの「ダメージを受けない」状態）・``paralyzed``・``confused``（でんきショック・ぶきみなひかり）"""
    counts = Counter()
    if not any(state.cards[uid].card_id in V0_106 for uid in state.cards):
        return counts
    window = None
    for e in state.log:
        kind = e["kind"]
        if kind == "damage" and not e.get("retaliation"):
            labels = [str(step[0]) for step in (e.get("steps") or ())[1:]]
            if any("イシツブテ（zero_damage_below）" in label for label in labels):
                counts["harden_zero" if e.get("amount") == 0 else "harden_through"] += 1
        if kind in ("attack", "turn_end", "game_end", "halted"):
            if window is not None:
                _v106_close(window, counts)
            window = None
        if kind == "attack":
            current = e.get("card_id") or state.cards[e["pokemon"]].card_id
            key = f"{current}#{e['attack_index']}"
            if current in V0_106:
                counts[f"attack_{key}"] += 1
            window = _v106_window(state, key, e["player"]) if current in V0_106 else None
            if window is None:
                window = {"key": key, "name": None, "player": e["player"], "copied": False}
            continue
        if window is None:
            continue
        if kind == "copy_attack" and e["copied"].split("#")[0] in V0_106:
            counts[f"copied_{e['copied']}"] += 1
            window = _v106_window(state, e["copied"], window["player"])
            window["copied"] = True
            continue
        name = window["name"]
        if name is None:
            continue
        if kind == "damage" and not e.get("retaliation") and e.get("steps"):
            base = e["steps"][0][1]
            if e["player"] != window["player"]:
                window["bases"].append(base)  # damage のログは effect を持たない
            else:
                window["selfs"].append(base)
                if window["voided"]:
                    counts[f"self_after_void_{name}"] += 1
            continue
        if kind == "damage_prevented" and e.get("player") != window["player"]:
            window["voided"] = True
            counts[f"opponent_void_{name}"] += 1
            continue
        if kind in ("confusion_damage", "attack_failed"):
            window["interrupted"] = True  # こんらんのコイン・手順 4 のコインで失敗した（コインを投げず、ダメージもない）
            continue
        if e.get("effect") != window["key"]:
            continue
        if kind == "coin_flip" and e.get("source") == "attack":
            window["coins"] += 1
            window["heads"] += e["result"] == "heads"
        elif kind == "esp_redo":
            window["coins"], window["heads"] = len(e["redone"]), list(e["redone"]).count("heads")
        elif kind == "attack_evaded" and e.get("element") == "damage":
            window["voided"] = True
            counts[f"opponent_void_{name}"] += 1
        elif kind == "persistent_effect_added":
            counts[{"leek": "leek_lock", "sand": "sand_cloak"}.get(name, f"{name}_effect")] += 1
        elif kind == "special_condition":
            counts[{"paralysis": "paralyzed", "confusion": "confused"}.get(e.get("condition"), f"status_{e.get('condition')}")] += 1
    if window is not None:
        _v106_close(window, counts)
    return counts


def _v106_window(state, key: str, player: int) -> dict:
    """v0.106: 1 回のワザの数える窓（数える名前・目安・コイン・基本となるダメージ）。v0.106 のカードのワザでなければ名前は None。"""
    card_id, index = key.split("#")
    impl = _v104_impl(state, key)
    attack = state.definitions[card_id].attacks[int(index)]
    name = V106_IMPLS.get(impl) if card_id in V0_106 else None
    if name is None and card_id in V0_106:
        name = V106_COUNT_NAMES.get(attack.name_ja) or {"ネギでつく": "leek", "すながくれ": "sand", "かたくなる": "harden"}.get(attack.name_ja, "other")
    return {"key": key, "name": name, "player": player, "copied": False, "printed": attack.damage, "coins": 0, "heads": 0, "bases": [], "selfs": [],
            "voided": False, "interrupted": False}


def _v106_close(window, counts):
    """v0.106: 1 回のワザの終わりに数える（基本となるダメージ・コイン・数えたポケモンとサイドの数）。"""
    name = window.get("name")
    if name is None:
        return
    if window.get("interrupted"):
        counts[f"{name}_interrupted"] += 1
        return
    for base in window["bases"]:
        counts[f"{name}_base_{base}"] += 1
        if name in ("spark", "family", "grudge") and window["printed"] is not None:
            counts[f"{name}_{'taken' if name == 'grudge' else 'counted'}_{(base - window['printed']) // 10}"] += 1
    for base in window["selfs"]:
        counts[f"{name}_self_{base}"] += 1
    if name in ("fury", "needle"):
        counts[f"{name}_heads_{window['heads']}"] += 1
    if name == "hydro":
        counts[f"hydro_coins_{window['coins']}"] += 1


# v0.107: 数える実装（登録の実装の id → 数える名前）。ヘッドプレス・からではさむ（v0.33 の型）・レインボーパウダー（v0.41 の型）・ダブルラリアット・でんきショック・でんげき・みずかけ・
# たいあたりは、v0.107 のカードのワザのときだけ（ワザの名前で分ける）
V107_IMPLS = {"fail_on_tails_damage_then_poison": "stab", "fail_on_tails_self_destruct": "boom", "fail_on_tails_damage_then_self_barrier": "fly",
              "damage_then_confuse_opponent_or_self": "migraine"}
V107_NAMES = {"ヘッドプレス": "headpress", "からではさむ": "clamp", "レインボーパウダー": "rainbow", "ダブルラリアット": "lariat", "でんきショック": "shock", "でんげき": "jolt",
              "みずかけ": "splash", "たいあたり": "tackle"}
V107_FLIERS = (FLYING_PIKACHU_18, FLYING_PIKACHU_42, FLYING_PIKACHU_63, BUTTERFREE_SI)


def v107_uses(state):
    """v0.107: ログから数えた 9 枚のワザの動き（v0.107 のカードのない局では空）。

    - ``attack_<id>#<位置>``（宣言したワザ）・``copied_<id>#<位置>``（ほかのワザが相手のワザとして使った v0.107 のワザ）
    - ``<名前>_heads``・``<名前>_tails``（このワザのコイン 1 枚の面。ESP でやり直したらやり直した結果）・``<名前>_failed``（「うら」でワザ全体が失敗）・``lariat_heads_<数>``
    - ``<名前>_<特殊状態>``（stab・headpress・clamp・rainbow の相手の特殊状態）・``migraine_confusion_opponent``・``migraine_confusion_self``・``<名前>_status_blocked``（「おもて」・「うら」で
      決まった特殊状態を、無効・「とうめい」・［にげこむ］・HP 以上で受けなかった）
    - ``fly_barrier``・``fly_barrier_skipped``（そらをとぶの防護を与えた・使ったポケモンが HP 以上で与えなかった）・``barrier_blocked``（その防護で次の相手の番のワザのダメージ・効果を受けなかった）
    - ``boom_self``・``boom_bench``（とつぜんじばくの自分・控えへのダメージの要素）・``opponent_void_<名前>``（相手へのダメージを無効にした・受けなかった）
    - ``<名前>_interrupted``（こんらんのコイン・手順 4 のコインでワザが失敗した。コイン・ダメージを数えない）"""
    counts = Counter()
    if not any(state.cards[uid].card_id in V0_107 for uid in state.cards):
        return counts
    window = None
    for e in state.log:
        kind = e["kind"]
        if kind in ("damage_prevented", "effect_prevented") and e.get("persistent_effect") == AttackBarrier.kind and state.cards[e["pokemon"]].card_id in V107_FLIERS:
            counts["barrier_blocked"] += 1
        if kind in ("attack", "turn_end", "game_end", "halted"):
            if window is not None:
                _v107_close(window, counts)
            window = None
        if kind == "attack":
            current = e.get("card_id") or state.cards[e["pokemon"]].card_id
            key = f"{current}#{e['attack_index']}"
            if current in V0_107:
                counts[f"attack_{key}"] += 1
            window = _v107_window(state, key, e["player"]) if current in V0_107 else {"key": key, "name": None, "player": e["player"]}
            continue
        if window is None:
            continue
        if kind == "copy_attack" and e["copied"].split("#")[0] in V0_107:
            counts[f"copied_{e['copied']}"] += 1
            window = _v107_window(state, e["copied"], window["player"])
            continue
        name = window["name"]
        if name is None:
            continue
        if kind in ("confusion_damage",) or (kind == "attack_failed" and e.get("reason") != "coin"):
            window["interrupted"] = True
            continue
        if kind == "damage" and not e.get("retaliation"):
            if name == "boom" and e.get("target") in ("self", "opponent_bench", "self_bench"):
                counts["boom_self" if e["target"] == "self" else "boom_bench"] += 1
            continue
        if kind == "damage_prevented" and e.get("player") != window["player"] and e.get("target", "opponent_active") == "opponent_active":
            counts[f"opponent_void_{name}"] += 1
            continue
        if e.get("effect") != window["key"]:
            continue
        if kind == "coin_flip" and e.get("source") == "attack":
            window["coins"].append(e["result"])
        elif kind == "esp_redo":
            window["coins"] = list(e["redone"])
        elif kind == "attack_failed":
            window["failed"] = True
        elif kind == "attack_evaded" and e.get("element") == "damage":
            counts[f"opponent_void_{name}"] += 1
        elif kind in ("attack_evaded", "effect_prevented", "special_condition_prevented", "flee_effect_skipped"):
            window["blocked"] = True
        elif kind == "persistent_effect_added" and e.get("persistent_effect") == AttackBarrier.kind:
            counts["fly_barrier"] += 1
        elif kind == "persistent_effect_skipped" and e.get("persistent_effect") == AttackBarrier.kind:
            counts["fly_barrier_skipped"] += 1
        elif kind == "special_condition":
            if name == "migraine":
                counts["migraine_confusion_" + ("self" if e["player"] == window["player"] else "opponent")] += 1
            else:
                counts[f"{name}_{e['condition']}"] += 1
            window["status"] = True
    if window is not None:
        _v107_close(window, counts)
    return counts


V108_NAMES = {"かみくだく": "crunch", "かえんほうしゃ": "flamethrower", "プラスイオン": "plus_ion", "マイナスイオン": "minus_ion", "あまえる": "charm",
              "とげたまタックル": "spike_tackle", "わるいうた": "dark_song", "たたきおこす": "slap_awake", "まきつく": "wrap", "もうどく": "toxic"}
V108_DEALT_KIND, V108_BONUS_KIND = "dealt_attack_damage_reduction", "received_attack_damage_bonus"


def v108_uses(state):
    """v0.108: ログから数えた 5 枚のワザの動き（v0.108 のカードのない局では空）。

    - ``attack_<id>#<位置>``（宣言したワザ）・``copied_<id>#<位置>``（ほかのワザが相手のワザとして使った v0.108 のワザ）・``<名前>_interrupted``（こんらん・手順 4 のコインで失敗）
    - 与える -10: ``<名前>_given``（マイナスイオン・あまえるの効果を与えた）・``<名前>_blocked``（受けなかった）・``dealt_reduction_applied_<受けた場所>``（2 段階の -10 を計算した
      ワザのダメージ。``opponent_active``・``opponent_bench``・``self``・``self_bench``・``retaliation``）・``dealt_reduction_to_zero``（そのダメージが 0）・``dealt_reduction_removed_<理由>``
    - 受ける +20: ``crunch_given``・``crunch_blocked``・``crunch_bonus_applied``（ヘルガーの効果の 8 段階の +20 を計算したダメージ）・``crunch_bonus_removed_<理由>``
    - 状態の参照: ``toxic_base_<基本となるダメージ>``・``toxic_poison``・``slap_awake_base_<基本となるダメージ>``・``slap_awake_cured_<回復させた状態>``・``slap_awake_blocked``
    - そのほか: ``plus_ion_<面>``・``dark_song_<面>``・``dark_song_<特殊状態>``・``wrap_<面>``・``wrap_paralysis``・``flamethrower_discard``・``spike_tackle_self``"""
    counts = Counter()
    if not any(state.cards[uid].card_id in V0_108 for uid in state.cards):
        return counts
    window = None
    houndoom = state.definitions.get(HOUNDOOM_NEO2)  # 対戦にあるカードだけが定義を持つ
    crunch_label = None if houndoom is None else f"8 {houndoom.name_ja}（{V108_BONUS_KIND}）"
    for e in state.log:
        kind = e["kind"]
        if kind == "damage":
            labels = [str(step[0]) for step in (e.get("steps") or ())]
            if any(label.startswith("2 ") and label.endswith(f"（{V108_DEALT_KIND}）") for label in labels):
                place = "retaliation" if e.get("retaliation") else e.get("target") or "opponent_active"
                counts[f"dealt_reduction_applied_{place}"] += 1
                if e["amount"] == 0:
                    counts["dealt_reduction_to_zero"] += 1
            if crunch_label is not None and crunch_label in labels:
                counts["crunch_bonus_applied"] += 1
        if kind == "persistent_effect_removed" and e.get("persistent_effect") in (V108_DEALT_KIND, V108_BONUS_KIND) \
                and state.cards[e["source_card"]].card_id in V0_108:
            counts[f"{'dealt_reduction' if e['persistent_effect'] == V108_DEALT_KIND else 'crunch_bonus'}_removed_{e['reason']}"] += 1
        if kind in ("attack", "turn_end", "game_end", "halted"):
            window = None
        if kind == "attack":
            current = e.get("card_id") or state.cards[e["pokemon"]].card_id
            key = f"{current}#{e['attack_index']}"
            if current in V0_108:
                counts[f"attack_{key}"] += 1
                window = {"key": key, "name": V108_NAMES.get(state.definitions[current].attacks[e["attack_index"]].name_ja, "other"), "player": e["player"]}
            else:
                window = {"key": key, "name": None, "player": e["player"]}
            continue
        if window is None:
            continue
        if kind == "copy_attack" and e["copied"].split("#")[0] in V0_108:
            counts[f"copied_{e['copied']}"] += 1
            card_id, index = e["copied"].split("#")
            window = {"key": e["copied"], "name": V108_NAMES.get(state.definitions[card_id].attacks[int(index)].name_ja, "other"), "player": window["player"]}
            continue
        name = window["name"]
        if name is None:
            continue
        if kind == "confusion_damage" or kind == "attack_failed":
            counts[f"{name}_interrupted"] += 1
            window["name"] = None
            continue
        if kind == "damage" and not e.get("retaliation"):
            # このワザのダメージの要素（相手の対戦ポケモンへのダメージのログは effect・target を持たない。窓の中の返す効果でないダメージはこのワザのもの）
            if e.get("target") == "self":
                counts[f"{name}_self"] += 1
            elif e.get("target") is None and name in ("toxic", "slap_awake") and e.get("steps"):
                counts[f"{name}_base_{e['steps'][0][1]}"] += 1
            continue
        if e.get("effect") != window["key"]:
            continue
        if kind == "coin_flip" and e.get("source") == "attack":
            counts[f"{name}_{e['result']}"] += 1
        elif kind == "special_condition":
            counts[f"{name}_{e['condition']}"] += 1
        elif kind == "special_conditions_removed" and e.get("reason") == "cured":
            for condition in e["conditions"]:
                counts[f"{name}_cured_{condition}"] += 1
        elif kind == "persistent_effect_added":
            counts[f"{name}_given"] += 1
        elif kind in ("attack_evaded", "effect_prevented", "special_condition_prevented") and (kind != "attack_evaded" or e.get("element") != "damage"):
            counts[f"{name}_blocked"] += 1
        elif kind in ("discard_energy", "discard_attached_energy"):
            counts[f"{name}_discard"] += 1  # かえんほうしゃのトラッシュ（ワザを使ったポケモンのエネルギー。ログ discard_energy）
    return counts


V109_NAMES = {"ぬるぬる": "slime", "しっぽでたたく": "tail_slap", "かわす": "dodge", "マッハストレート": "mach_straight", "サイコパニック": "psychic_panic", "ブリンク": "blink"}
V109_GUARD_KIND = "timed_damage_guard"


def v109_uses(state):
    """v0.109: ログから数えた 3 枚のワザの動き（v0.109 のカードのない局では空）。

    - ``attack_<id>#<位置>``（宣言したワザ）・``copied_<id>#<位置>``（ほかのワザが相手のワザとして使った v0.109 のワザ）・``<名前>_interrupted``（こんらん・手順 4 のコインで失敗）
    - 効果を与えた: ``<名前>_given``・``<名前>_skipped``（ワザを使ったポケモンがこのワザの中で HP 以上）・``blink_given_after_opponent_ko``（ブリンクのダメージで相手が HP 以上になった
      あとに与えた）・``<名前>_removed_<理由>``（消えた理由。``expired`` は期限）・``<名前>_kept_through_poison``（与えた番のポケモンチェックのどくのダメージのあとも残った）
    - 受けるときのコイン（効果を与えたワザの名前ごと）: ``<名前>_check``・``<名前>_flipped_by_<owner|opponent>``・``<名前>_coin_<面>``・``<名前>_prevented``（受けなかった）・
      ``<名前>_prevented_amount``（受けなかったダメージの合計）・``<名前>_received``・``<名前>_check_retaliation``（返す効果のダメージ）・``<名前>_check_own_attack``（持ち主のワザ）・
      ``<名前>_prevented_then_<ログの種類>``（受けなかったあと、同じワザでそのポケモンが受けたダメージ以外の効果）
    - サイコパニック: ``psychic_panic_base_<基本となるダメージ>``
    - そのほか: ``<名前>_damage``（相手の対戦ポケモンへのダメージ。しっぽでたたく・マッハストレート・ブリンク）"""
    counts = Counter()
    if not any(state.cards[uid].card_id in V0_109 for uid in state.cards):
        return counts
    window = None
    guards = {}  # (持つポケモンの番号, 与えた番) → 与えたワザの名前
    alive = set()  # 消えていない効果の (持つポケモンの番号, 与えた番)
    prevented = None  # 受けなかったポケモンの番号と名前（同じワザの、そのポケモンへのダメージ以外の効果を数える）
    for e in state.log:
        kind = e["kind"]
        if kind == "persistent_effect_added" and e.get("persistent_effect") == V109_GUARD_KIND:
            card_id, index = e["effect"].split("#")
            name = V109_NAMES.get(state.definitions[card_id].attacks[int(index)].name_ja, "other")
            guards[(e["pokemon_id"], e["turn"])] = name
            alive.add((e["pokemon_id"], e["turn"]))
            counts[f"{name}_given"] += 1
            if window is not None and window.get("opponent_ko"):
                counts[f"{name}_given_after_opponent_ko"] += 1
        elif kind == "persistent_effect_removed" and e.get("persistent_effect") == V109_GUARD_KIND:
            alive.discard((e["pokemon_id"], e["created_turn"]))
            counts[f"{guards.get((e['pokemon_id'], e['created_turn']), 'other')}_removed_{e['reason']}"] += 1
        elif kind == "persistent_effect_skipped" and e.get("persistent_effect") == V109_GUARD_KIND:
            card_id, index = e["effect"].split("#")
            counts[f"{V109_NAMES.get(state.definitions[card_id].attacks[int(index)].name_ja, 'other')}_skipped"] += 1
        elif kind == "poison_damage" and (e["pokemon_id"], e["turn"]) in alive:
            counts[f"{guards[(e['pokemon_id'], e['turn'])]}_kept_through_poison"] += 1  # 与えた番のポケモンチェックのどくのダメージ（効果は消えない。監査が確かめる）
        elif kind == "timed_damage_guard_check":
            name = guards.get((e["pokemon_id"], e["created_turn"]), "other")
            counts[f"{name}_check"] += 1
            counts[f"{name}_flipped_by_{'owner' if e['flipped_by'] == e['player'] else 'opponent'}"] += 1
            counts[f"{name}_coin_{e['result']}"] += 1
            if e.get("retaliation"):
                counts[f"{name}_check_retaliation"] += 1
            if e["attacker"] == e["player"]:
                counts[f"{name}_check_own_attack"] += 1
            if e["received"]:
                counts[f"{name}_received"] += 1
            else:
                counts[f"{name}_prevented"] += 1
                counts[f"{name}_prevented_amount"] += e["amount"]
                prevented = (e["pokemon_id"], name)
        if kind in ("attack", "turn_end", "game_end", "halted"):
            window, prevented = None, None
        if kind == "attack":
            current = e.get("card_id") or state.cards[e["pokemon"]].card_id
            key = f"{current}#{e['attack_index']}"
            if current in V0_109:
                counts[f"attack_{key}"] += 1
                window = {"key": key, "name": V109_NAMES.get(state.definitions[current].attacks[e["attack_index"]].name_ja, "other"), "player": e["player"]}
            else:
                window = {"key": key, "name": None, "player": e["player"]}
            continue
        if window is None:
            continue
        if prevented is not None and e.get("pokemon_id") == prevented[0] and kind not in ("timed_damage_guard_check", "damage", "coin_flip") \
                and e.get("effect") == window["key"]:
            counts[f"{prevented[1]}_prevented_then_{kind}"] += 1
        if kind == "copy_attack":
            if e["copied"].split("#")[0] in V0_109:
                counts[f"copied_{e['copied']}"] += 1
                card_id, index = e["copied"].split("#")
                window = {"key": e["copied"], "name": V109_NAMES.get(state.definitions[card_id].attacks[int(index)].name_ja, "other"), "player": window["player"]}
            else:
                window["key"] = e["copied"]
            continue
        name = window["name"]
        if name is None:
            continue
        if kind in ("confusion_damage", "attack_failed"):
            counts[f"{name}_interrupted"] += 1
            window["name"] = None
            continue
        if kind == "damage" and not e.get("retaliation") and e.get("target") is None and e["player"] != window["player"]:
            counts[f"{name}_damage"] += 1
            if name == "psychic_panic" and e.get("steps"):
                counts[f"psychic_panic_base_{e['steps'][0][1]}"] += 1
            if e.get("total_damage", 0) >= state.in_play_def(e["pokemon"]).hp:
                window["opponent_ko"] = True
    return counts


def _v110_survival_on(state) -> bool:
    """v0.110: 場のどれかのポケモンが、今の番にはたらいている「きぜつ」しない効果（種類 knockout_survival。はたらき始める番〜最後の番）を持つか。"""
    return any(effect.kind == V110_SURVIVAL_KIND and effect.active_turn <= state.turn_number <= effect.end_turn
               for side in state.players for pokemon in side.in_play() for effect in pokemon.persistent_effects)


V111_NAMES = {"サイコクラッシュ": "psycho_crush", "ちょうねんりき": "super_psy", "はたく": "pound", "シンクロウェーブ": "synchro_wave"}


def _v111_cards(state, pokemon, psychic_only: bool) -> int:
    """v0.111: 場のポケモン ``pokemon`` についているカードの枚数（``psychic_only`` なら、印刷の定義が「超」の基本エネルギーカードのものだけ）。道具が数えるための値で、エンジンの問い合わせ
    （``attached_energy_cards``・``field_energy_cards_of_type``）を読まない。"""
    if not psychic_only:
        return len(pokemon.energy)
    return sum(1 for uid in pokemon.energy
               if state.definitions[state.cards[uid].card_id].is_basic_energy and state.definitions[state.cards[uid].card_id].provides is EnergyType.PSYCHIC)


def _v111_counts_differ(state, command) -> bool:
    """v0.111: ``command`` を宣言するポケモン（バトル場）と相手の対戦ポケモンについているカードの枚数が違う（相手の対戦ポケモンがいなければ 0 枚）。"""
    attacker, defender = _attacker(state, command), state.players[1 - command.player].active
    return attacker is not None and _v111_cards(state, attacker, False) != (0 if defender is None else _v111_cards(state, defender, False))


def _v111_attack_observe(state, seen, counts) -> None:
    """v0.111: 前に見た場（``seen["v111"]``。番のプレイヤーと、そのときの場から道具が数えた枚数）のあとに、そのプレイヤーのワザのログ（``attack``。相手のワザとして使ったなら ``copy_attack``）
    があり、処理したワザが v0.111 のワザなら、宣言の時点の場として数える。

    - サイコクラッシュ: ``v111_psycho_crush_declared_cards_<枚数>``（相手の場の「超」の基本エネルギーカード）・``v111_psycho_crush_bench_cards``（そのうち控えのカードの合計）・
      ``v111_psycho_crush_with_bench_cards``（控えにカードのあった宣言）
    - シンクロウェーブ: ``v111_synchro_wave_declared_equal_<枚数>``（自分と相手の対戦ポケモンのカードの枚数が同じ）・``v111_synchro_wave_declared_unequal``（違う。あってはならない）

    拒否されたコマンドはログを残さないので数えない。v0.111 のカードが番のプレイヤーか相手のバトル場にいないときは何も記録しない（前の版の組の結果は変わらない）。決定のあいだは前の場を
    残す（ゆびをふるの使うワザを選ぶ決定のあとに ``copy_attack`` がある）。"""
    if state.phase is Phase.DECISION:
        return
    previous = seen.pop("v111", None)
    if previous is not None:
        index, player, fields = previous
        name = None
        for e in state.log[index:]:
            if e["kind"] == "attack" and e["player"] == player:
                current = e.get("card_id") or state.cards[e["pokemon"]].card_id
                name = V111_NAMES.get(state.definitions[current].attacks[e["attack_index"]].name_ja) if current in V0_111 else None
            elif e["kind"] == "copy_attack" and name is None:
                card_id, attack_index = e["copied"].split("#")
                name = V111_NAMES.get(state.definitions[card_id].attacks[int(attack_index)].name_ja) if card_id in V0_111 else None
            elif e["kind"] in ("turn_end", "game_end", "halted"):
                break
        active_cards, bench_cards, own, theirs = fields
        if name == "psycho_crush":
            counts[f"v111_psycho_crush_declared_cards_{active_cards + bench_cards}"] += 1
            counts["v111_psycho_crush_bench_cards"] += bench_cards
            if bench_cards:
                counts["v111_psycho_crush_with_bench_cards"] += 1
        elif name == "synchro_wave":
            counts[f"v111_synchro_wave_declared_equal_{own}" if own == theirs else "v111_synchro_wave_declared_unequal"] += 1
    if state.phase is not Phase.MAIN:
        return
    player = state.current_player
    attacker, defender = state.players[player].active, state.players[1 - player].active
    if attacker is None or not any(p is not None and state.cards[p.card].card_id in V0_111 for p in (attacker, defender)):
        return
    side = state.players[1 - player]
    active_cards = 0 if defender is None else _v111_cards(state, defender, True)
    bench_cards = sum(_v111_cards(state, p, True) for p in side.bench)
    seen["v111"] = (len(state.log), player,
                    (active_cards, bench_cards, _v111_cards(state, attacker, False), 0 if defender is None else _v111_cards(state, defender, False)))


def v111_uses(state):
    """v0.111: ログから数えた 4 枚のワザの動き（v0.111 のカードのない局では空）。

    - ``attack_<id>#<位置>``（宣言したワザ）・``copied_<id>#<位置>``（ほかのワザが相手のワザとして使った v0.111 のワザ）・``<名前>_interrupted``（こんらん・手順 4 のコインで失敗）
    - 相手の対戦ポケモンへのダメージ: ``<名前>_damage``・``<名前>_prevented``（無効。damage_prevented）
    - サイコクラッシュ: ``psycho_crush_base_<基本となるダメージ>``（ログの計算の 1 段階）・``psycho_crush_counted_cards_<基本となるダメージ ÷ 10>``・``psycho_crush_zero_base``
    - シンクロウェーブ: ``synchro_wave_used``（宣言を受け付けた。拒否は ``observed`` の ``stopped_attack_ENERGY_CARD_COUNTS_DIFFER``）"""
    counts = Counter()
    if not any(state.cards[uid].card_id in V0_111 for uid in state.cards):
        return counts
    window = None
    for e in state.log:
        kind = e["kind"]
        if kind in ("attack", "turn_end", "game_end", "halted"):
            window = None
        if kind == "attack":
            current = e.get("card_id") or state.cards[e["pokemon"]].card_id
            name = V111_NAMES.get(state.definitions[current].attacks[e["attack_index"]].name_ja, "other") if current in V0_111 else None
            if current in V0_111:
                counts[f"attack_{current}#{e['attack_index']}"] += 1
                if name == "synchro_wave":
                    counts["synchro_wave_used"] += 1
            window = {"name": name}
            continue
        if window is None:
            continue
        if kind == "copy_attack":
            card_id, index = e["copied"].split("#")
            window["name"] = V111_NAMES.get(state.definitions[card_id].attacks[int(index)].name_ja, "other") if card_id in V0_111 else None
            if card_id in V0_111:
                counts[f"copied_{e['copied']}"] += 1
            continue
        name = window["name"]
        if name is None:
            continue
        if kind in ("confusion_damage", "attack_failed"):
            counts[f"{name}_interrupted"] += 1
            window["name"] = None
        elif kind == "damage_prevented":
            counts[f"{name}_prevented"] += 1
        elif kind == "damage" and not e.get("retaliation") and (e.get("target") or "opponent_active") == "opponent_active":
            counts[f"{name}_damage"] += 1
            if name == "psycho_crush":
                base = e["steps"][0][1] if e.get("steps") else 0
                counts[f"psycho_crush_base_{base}"] += 1
                counts[f"psycho_crush_counted_cards_{base // 10}"] += 1
                if base == 0:
                    counts["psycho_crush_zero_base"] += 1
    return counts


V112_NAMES = {"しょくしゅをつかう": "tentacle_grip", "どくばり": "poison_sting", "ふしょくえき": "corrosive_acid"}


def _v112_water_cards(state, pokemon) -> int:
    """v0.112: 場のポケモン ``pokemon`` についている、印刷の定義が「水」の基本エネルギーカードの枚数（道具が数えるための値で、エンジンの ``typed_units_for`` を読まない）。"""
    return sum(1 for uid in pokemon.energy
               if state.definitions[state.cards[uid].card_id].is_basic_energy and state.definitions[state.cards[uid].card_id].provides is EnergyType.WATER)


def _v112_attack_observe(state, seen, counts) -> None:
    """v0.112: 前に見た場（``seen["v112"]``。番のプレイヤーと、そのときの場から道具が数えた値）のあとに、そのプレイヤーのワザのログ（``attack``。相手のワザとして使ったなら
    ``copy_attack``）があり、処理したワザがしょくしゅをつかうなら、宣言の時点の場として照らす（拒否されたコマンドはログを残さないので数えない）。

    - ``v112_grip_declared_water_cards_<枚数>``（ワザを使うポケモンの「水」の基本エネルギーカード。ほかの種類のエネルギーカードのないとき、「水」エネルギーの個数と同じ）・
      ``v112_grip_other_energy``（ほかの種類のエネルギーカードもついていた）
    - ``v112_grip_draw_checked``・``v112_grip_draw_mismatch``（そのワザのコインの「おもて」の数 × 2 と、宣言の時点の山札の枚数の小さいほうが、引いた枚数と違う。あってはならない）

    v0.112 のカードが番のプレイヤーか相手のバトル場にいないときは何も記録しない（前の版の組の結果は変わらない）。決定のあいだは前の場を残す。"""
    if state.phase is Phase.DECISION:
        return
    previous = seen.pop("v112", None)
    if previous is not None:
        index, player, water, others, deck = previous
        name, key, heads, drawn = None, None, 0, None
        for e in state.log[index:]:
            if e["kind"] == "attack" and e["player"] == player:
                current = e.get("card_id") or state.cards[e["pokemon"]].card_id
                key = f"{current}#{e['attack_index']}"
                name = V112_NAMES.get(state.definitions[current].attacks[e["attack_index"]].name_ja) if current in V0_112 else None
            elif e["kind"] == "copy_attack" and name is None and key is not None:
                card_id, attack_index = e["copied"].split("#")
                key = e["copied"]
                name = V112_NAMES.get(state.definitions[card_id].attacks[int(attack_index)].name_ja) if card_id in V0_112 else None
            elif e["kind"] == "coin_flip" and name == "tentacle_grip" and e.get("source") == "attack" and e.get("effect") == key and e["result"] == "heads":
                heads += 1
            elif e["kind"] == "draw" and name == "tentacle_grip" and e["player"] == player and drawn is None:
                drawn = len(e["cards"])
            elif e["kind"] in ("turn_end", "game_end", "halted"):
                break
        if name == "tentacle_grip":
            counts[f"v112_grip_declared_water_cards_{water}"] += 1
            if others:
                counts["v112_grip_other_energy"] += 1
            if drawn is not None:
                counts["v112_grip_draw_checked"] += 1
                if drawn != min(2 * heads, deck):
                    counts["v112_grip_draw_mismatch"] += 1
    if state.phase is not Phase.MAIN:
        return
    player = state.current_player
    attacker, defender = state.players[player].active, state.players[1 - player].active
    if attacker is None or not any(p is not None and state.cards[p.card].card_id in V0_112 for p in (attacker, defender)):
        return
    water = _v112_water_cards(state, attacker)
    seen["v112"] = (len(state.log), player, water, len(attacker.energy) - water, len(state.players[player].deck))


def v112_uses(state):
    """v0.112: ログから数えた 2 枚のワザの動き（v0.112 のカードのない局では空）。

    - ``attack_<id>#<位置>``（宣言したワザ）・``copied_<id>#<位置>``（ほかのワザが相手のワザとして使った v0.112 のワザ）・``<名前>_interrupted``（こんらん・手順 4 のコインで失敗）
    - しょくしゅをつかう: ``tentacle_grip_coins_<N>``（そのワザのコインの枚数）・``tentacle_grip_heads_<H>``・``tentacle_grip_requested``（2H の合計）・``tentacle_grip_drawn``（引いた
      枚数の合計）・``tentacle_grip_short``（引いた枚数が 2H より少ない。山札が足りない）・``tentacle_grip_no_coins``（N = 0）
    - どくばり・ふしょくえき: ``<名前>_damage``・``<名前>_coin_<面>``・``poison_sting_poisoned``・``corrosive_acid_paralyzed``・``corrosive_acid_locked``（「うら」で自分に与えた
      使えない効果）・``corrosive_acid_lock_skipped``"""
    counts = Counter()
    if not any(state.cards[uid].card_id in V0_112 for uid in state.cards):
        return counts
    window = None

    def close(w):
        if w is not None and w["name"] == "tentacle_grip" and not w.get("closed"):
            w["closed"] = True
            counts[f"tentacle_grip_coins_{w['coins']}"] += 1
            counts[f"tentacle_grip_heads_{w['heads']}"] += 1
            counts["tentacle_grip_requested"] += 2 * w["heads"]
            counts["tentacle_grip_drawn"] += w["drawn"] or 0
            if (w["drawn"] or 0) < 2 * w["heads"]:
                counts["tentacle_grip_short"] += 1
            if w["coins"] == 0:
                counts["tentacle_grip_no_coins"] += 1

    for e in state.log:
        kind = e["kind"]
        if kind in ("attack", "turn_end", "game_end", "halted"):
            close(window)
            window = None
        if kind == "attack":
            current = e.get("card_id") or state.cards[e["pokemon"]].card_id
            key = f"{current}#{e['attack_index']}"
            name = V112_NAMES.get(state.definitions[current].attacks[e["attack_index"]].name_ja, "other") if current in V0_112 else None
            if current in V0_112:
                counts[f"attack_{key}"] += 1
            window = {"name": name, "key": key, "player": e["player"], "pokemon_id": e.get("pokemon_id"), "coins": 0, "heads": 0, "drawn": None}
            continue
        if window is None:
            continue
        if kind == "copy_attack":
            card_id, index = e["copied"].split("#")
            window["name"] = V112_NAMES.get(state.definitions[card_id].attacks[int(index)].name_ja, "other") if card_id in V0_112 else None
            window["key"] = e["copied"]
            if card_id in V0_112:
                counts[f"copied_{e['copied']}"] += 1
            continue
        name = window["name"]
        if name is None:
            continue
        if kind in ("confusion_damage", "attack_failed"):
            counts[f"{name}_interrupted"] += 1
            window["name"] = None
        elif kind == "coin_flip" and e.get("source") == "attack" and e.get("effect") == window["key"]:
            if name == "tentacle_grip":
                window["coins"] += 1
                window["heads"] += e["result"] == "heads"
            else:
                counts[f"{name}_coin_{e['result']}"] += 1
        elif kind == "draw" and name == "tentacle_grip" and e["player"] == window["player"] and window["drawn"] is None:
            window["drawn"] = len(e["cards"])
        elif kind == "damage" and name != "tentacle_grip" and not e.get("retaliation") and (e.get("target") or "opponent_active") == "opponent_active":
            counts[f"{name}_damage"] += 1
        elif kind == "special_condition" and name == "poison_sting" and e.get("condition") == "poison":
            counts["poison_sting_poisoned"] += 1
        elif kind == "special_condition" and name == "corrosive_acid" and e.get("condition") == "paralysis":
            counts["corrosive_acid_paralyzed"] += 1
        elif kind == "persistent_effect_added" and name == "corrosive_acid" and e.get("persistent_effect") == "cannot_use_own_attack":
            counts["corrosive_acid_locked"] += 1
        elif kind == "persistent_effect_skipped" and name == "corrosive_acid" and e.get("persistent_effect") == "cannot_use_own_attack":
            counts["corrosive_acid_lock_skipped"] += 1
    close(window)
    return counts


V113_NAMES = {"おうふくビンタ": "doubleslap", "みんなでおどる": "squaredance", "ゆうでん": "attract_current", "ギガボルト": "gigavolt", "なかまをよぶ": "call_for_family",
              "むれでつつく": "flock_attack", "ダークフレイム": "dark_flame", "くろいキバ": "black_fang", "つめできりさく": "claw_swipe", "ファイヤーラッシュ": "rushing_flames",
              "だいぎゃくてん？": "miraculous_comeback"}


def _v113_name(state, key: str | None) -> str | None:
    """v0.113: ワザ ``key``（"カード id#位置"）が v0.113 のワザなら、その集計の名前（ほかは None）。"""
    if key is None:
        return None
    card_id, index = key.split("#")
    return V113_NAMES.get(state.definitions[card_id].attacks[int(index)].name_ja) if card_id in V0_113 else None


def _v113_typed_units(state, cards, color) -> int:
    """v0.113: カード ``cards`` の出す「``color``」エネルギーの個数（道具が印刷の定義と登録の出すエネルギーから数える値。エンジンの ``typed_units_for`` を読まない）。"""
    total = 0
    for uid in cards:
        definition = state.definitions[state.cards[uid].card_id]
        if definition.is_basic_energy:
            total += definition.provides is color
        elif definition.category == "energy":
            total += sum(1 for unit in state.effects.energy_effect(definition).units() if unit == frozenset({color}))
    return total


def _v113_basic(state, uid, color=None) -> bool:
    definition = state.definitions[state.cards[uid].card_id]
    return definition.is_basic_energy and (color is None or definition.provides is color)


def _v113_attack_observe(state, seen, counts) -> None:
    """v0.113: 前に見た場（``seen["v113"]``。番のプレイヤーと、そのときの場から道具が数えた値）のあとに、そのプレイヤーのワザのログ（``attack``。相手のワザとして使ったなら
    ``copy_attack``）があり、処理したワザが v0.113 のワザなら、宣言の時点の場と照らす（拒否されたコマンドはログを残さないので数えない）。数えた値と照らした結果は
    ``v113_<名前>_checked``・``v113_<名前>_mismatch``（あってはならない）:

    - お互いの場のポケモンの数（みんなでおどる・だいぎゃくてん？のコインの枚数）・自分のベンチの名前が「ヤミカラス」のポケモンの数（むれでつつく）・使うポケモンの「悪」エネルギーの個数
      （くろいキバ。印刷の定義と登録の出すエネルギー）・自分の場の「炎」の基本エネルギーカード（ファイヤーラッシュのトラッシュは、その中から 1 枚以上で、コインはトラッシュした枚数）・山札の
      基本エネルギーカード（みんなでおどるで見せた枚数は「おもて」の数とその枚数の小さいほう以下）・山札の「雷」の基本エネルギーカード（ゆうでんでつけた枚数は、それが「おもて」の数以上なら
      「おもて」の数、0 枚なら 0）・トラッシュの悪エネルギー（ダークフレイムでつけたのは、あれば 1 枚・なければ 0 枚。失敗・HP 以上のときを除く）・ベンチの空き（なかまをよぶの失敗）

    v0.113 のカードが番のプレイヤーか相手のバトル場にいないときは何も記録しない（前の版の組の結果は変わらない）。決定のあいだは前の場を残す。"""
    if state.phase is Phase.DECISION:
        return
    previous = seen.pop("v113", None)
    if previous is not None:
        index, player, board = previous
        name, key, coins, heads, revealed, attached, discarded, dark_attached, failed, skipped, bases, reasons = None, None, 0, 0, 0, 0, 0, 0, [], False, [], []
        for e in state.log[index:]:
            if e["kind"] == "attack" and e["player"] == player:
                current = e.get("card_id") or state.cards[e["pokemon"]].card_id
                key = f"{current}#{e['attack_index']}"
                name = _v113_name(state, key)
            elif e["kind"] == "copy_attack" and key is not None:
                key = e["copied"]
                name = _v113_name(state, key)
            elif name is None:
                continue
            elif e["kind"] == "coin_flip" and e.get("source") == "attack" and e.get("effect") == key:
                coins += 1
                heads += e["result"] == "heads"
            elif e["kind"] == "reveal_from_deck" and e.get("effect") == key:
                revealed += 1
            elif e["kind"] in ("attach_energy_from_deck", "deck_energy_evaded") and e.get("effect") == key:
                attached += 1
            elif e["kind"] == "attach_energy_from_deck_none" and e.get("effect") == key:
                reasons.append(e["reason"])
            elif e["kind"] == "discard_energy" and e.get("effect") == key:
                discarded += 1
            elif e["kind"] == "attach_energy_from_discard" and e.get("effect") == key:
                dark_attached += len(e["cards"])
            elif e["kind"] == "attack_failed":
                failed.append(e.get("reason"))
            elif e["kind"] == "effect_skipped" and e.get("effect") == key:
                skipped = True
            elif e["kind"] == "damage" and not e.get("retaliation") and (e.get("target") or "opponent_active") == "opponent_active" and e.get("steps"):
                bases.append(e["steps"][0][1])
            elif e["kind"] in ("esp_redo",):
                coins -= len(e["original"])
                heads -= sum(1 for side in e["original"] if side == "heads")
            elif e["kind"] in ("turn_end", "game_end", "halted"):
                break
        if name is not None and "confusion" not in failed and "attack_check" not in failed:
            expected = {"squaredance": coins == board["field"] and revealed <= min(heads, board["deck_basic"]),
                        "miraculous_comeback": coins == board["field"],
                        "flock_attack": board["bench_named"] is None or coins == board["bench_named"],
                        "black_fang": coins == board["dark_units"],
                        "rushing_flames": coins == discarded <= board["field_fire"] and (discarded > 0 or board["field_fire"] == 0),
                        "attract_current": (coins == attached == 0) if reasons == ["no_target"] else (attached == 0 == heads) if reasons == ["no_heads"]
                        else attached == (heads if board["deck_lightning"] >= heads else 0),
                        "dark_flame": failed == ["discard"] or skipped or dark_attached == min(1, board["discard_dark"]),
                        "call_for_family": (failed == ["bench_full"]) == board["bench_full"]}.get(name)
            if expected is not None:
                counts[f"v113_{name}_checked"] += 1
                if not expected:
                    counts[f"v113_{name}_mismatch"] += 1
    if state.phase is not Phase.MAIN:
        return
    player = state.current_player
    attacker, defender = state.players[player].active, state.players[1 - player].active
    if attacker is None or not any(p is not None and state.cards[p.card].card_id in V0_113 for p in (attacker, defender)):
        return
    p = state.players[player]
    names = None if any(state.is_face_down(b) for b in p.bench) else sum(1 for b in p.bench if state.card_def(b.card).name_ja == "ヤミカラス")
    board = {"field": sum(len(side.in_play()) for side in state.players), "bench_named": names, "dark_units": _v113_typed_units(state, attacker.energy, EnergyType.DARKNESS),
             "field_fire": sum(1 for q in p.in_play() for uid in q.energy if _v113_basic(state, uid, EnergyType.FIRE)),
             "deck_basic": sum(1 for uid in p.deck if _v113_basic(state, uid)), "deck_lightning": sum(1 for uid in p.deck if _v113_basic(state, uid, EnergyType.LIGHTNING)),
             "discard_dark": sum(1 for uid in p.discard if state.cards[uid].card_id in ("neo1-094", "PRN-002", "NIP2X-010")),
             "bench_full": len(p.bench) >= state.rules.max_bench}
    seen["v113"] = (len(state.log), player, board)


def _v113_decision(state, counts):
    """v0.113 のワザの決定への答え（元の手順より先に答える。処理しているワザが v0.113 のワザでなければ何もしない）。受け付ける答えだけを選び、原典で決められない選択
    （``unresolved_choices``。ゆうでんのレインボーエネルギー・うらのカード）・0 枚の HC5 の答えは選ばない。

    - みんなでおどる（SEARCH_DECK。0〜H 枚）: 決定のたびに 選べるだけ・0 枚・1 枚 を順に
    - ゆうでん: カード（ATTACH_FROM_DECK。H 枚ちょうど）は選べるものの前から。つける先（SELECT_POKEMON）は決定のたびに選べるものを順に回す（1 匹に 2 枚以上をつける場面も起こる）
    - ダークフレイム・ファイヤーラッシュのトラッシュ（DISCARD_ENERGY）: 1 枚ちょうどは前から、「好きなだけ」は すべて・1 枚 を交互に
    - ダークフレイムのつけるカード・なかまをよぶの出すカード: 選べるものの前から"""
    d = state.decision
    if d is None or d.resume != "attack" or d.player != state.current_player:
        return None
    use = d.context_value("use")
    copied = d.context_value("copied")
    key = f"{copied[0]}#{copied[1]}" if copied else (f"{use[2]}#{use[3]}" if use is not None else None)
    name = _v113_name(state, key)
    if name is None or d.kind not in (SEARCH_DECK, ATTACH_FROM_DECK, SELECT_POKEMON, DISCARD_ENERGY, ATTACH_FROM_DISCARD, BENCH_FROM_DECK):
        return None
    blocked = set(d.context_value("unresolved_choices") or ())
    options = tuple(o for o in d.options if o not in blocked)
    label = f"v113_{name}_{d.kind}"
    seen = counts[label]
    counts[label] += 1
    if d.kind == SEARCH_DECK:
        top = options[:d.max_choices]
        candidates = [top, (), options[:1]][seen % 3:] + [top, (), options[:1]][:seen % 3]
    elif d.kind == SELECT_POKEMON:
        rotated = options[seen % len(options):] + options[:seen % len(options)] if options else ()
        candidates = [(o,) for o in rotated]
    elif d.kind == DISCARD_ENERGY and d.min_choices == 0:
        candidates = [options, options[:1]] if seen % 2 == 0 else [options[:1], options]
    else:
        candidates = [options[:d.min_choices]]
    for choices in candidates:
        command = ResolveDecision(d.player, d.id, tuple(choices))
        if d.min_choices <= len(choices) <= d.max_choices and _v052_accepted(state, command):
            counts[f"{label}_{len(choices)}"] += 1
            return command
    counts[f"{label}_no_accepted_answer"] += 1
    return None


def v113_uses(state):
    """v0.113: ログから数えた 6 枚のワザの動き（v0.113 のカードのない局では空）。

    - ``attack_<id>#<位置>``（宣言したワザ）・``copied_<id>#<位置>``（ほかのワザが相手のワザとして使った v0.113 のワザ）・``<名前>_interrupted``（こんらん・手順 4 のコインで失敗）・
      ``esp_redo``・``esp_redo_declined``
    - コインを投げるワザ: ``<名前>_coins_<N>``・``<名前>_heads_<H>``（ESPでやり直したら、やり直した結果）・``<名前>_no_coins``
    - みんなでおどる: ``squaredance_revealed_<枚数>``・``squaredance_declined``・``squaredance_shuffled``
    - ゆうでん: ``attract_current_attached``（つけた枚数の合計）・``attract_current_to_active``・``attract_current_to_bench``・``attract_current_several_to_one``・``attract_current_evaded``・
      ``attract_current_none_<理由>``
    - ギガボルト: ``gigavolt_base_<基本となるダメージ>``・``gigavolt_paralyzed``
    - なかまをよぶ: ``call_for_family_benched``・``call_for_family_none``・``call_for_family_failed_bench_full``
    - むれでつつく・くろいキバ: ``<名前>_base_<基本となるダメージ>``
    - ダークフレイム: ``dark_flame_discarded``・``dark_flame_failed``・``dark_flame_attached``・``dark_flame_no_dark``（つけなかった。トラッシュに悪エネルギーがない）・``dark_flame_skipped``
    - ファイヤーラッシュ: ``rushing_flames_discarded_<N>``・``rushing_flames_from_bench``（控えのカードもトラッシュした）・``rushing_flames_base_<基本となるダメージ>``
    - だいぎゃくてん？: ``miraculous_comeback_pair_<相手>_<自分>``（基本となるダメージの組）・``miraculous_comeback_self_knock_out``"""
    counts = Counter()
    if not any(state.cards[uid].card_id in V0_113 for uid in state.cards):
        return counts
    window = None

    def close(w):
        if w is None or w["name"] is None or w.get("closed"):
            return
        w["closed"] = True
        name = w["name"]
        if w["coin_names"]:
            counts[f"{name}_coins_{len(w['coins'])}"] += 1
            counts[f"{name}_heads_{sum(1 for side in w['coins'] if side == 'heads')}"] += 1
            if not w["coins"]:
                counts[f"{name}_no_coins"] += 1
        if name == "squaredance" and w["decided"] is not None:
            counts[f"squaredance_revealed_{w['revealed']}"] += 1
        if name == "attract_current":
            targets = Counter(w["targets"])
            if any(n > 1 for n in targets.values()):
                counts["attract_current_several_to_one"] += 1
        if name == "rushing_flames":
            counts[f"rushing_flames_discarded_{w['discarded']}"] += 1
        if name == "dark_flame" and not w["failed"] and not w["attached"] and not w["skipped"]:
            counts["dark_flame_no_dark"] += 1
        if name == "miraculous_comeback" and w["bases"] and w["self_bases"]:
            counts[f"miraculous_comeback_pair_{w['bases'][0]}_{w['self_bases'][0]}"] += 1

    for e in state.log:
        kind = e["kind"]
        if kind in ("attack", "turn_end", "game_end", "halted"):
            close(window)
            window = None
        if kind == "attack":
            current = e.get("card_id") or state.cards[e["pokemon"]].card_id
            key = f"{current}#{e['attack_index']}"
            name = _v113_name(state, key)
            if name is not None:
                counts[f"attack_{key}"] += 1
            window = {"name": name, "key": key, "player": e["player"], "card": e["pokemon"], "coins": [], "coin_names": False, "revealed": 0, "decided": None,
                      "targets": [], "discarded": 0, "failed": False, "attached": 0, "skipped": False, "bases": [], "self_bases": []}
            window["coin_names"] = name in ("doubleslap", "squaredance", "attract_current", "gigavolt", "flock_attack", "black_fang", "rushing_flames", "miraculous_comeback")
            continue
        if window is None:
            continue
        if kind == "copy_attack":
            window["key"] = e["copied"]
            name = window["name"] = _v113_name(state, e["copied"])
            window["coin_names"] = name in ("doubleslap", "squaredance", "attract_current", "gigavolt", "flock_attack", "black_fang", "rushing_flames", "miraculous_comeback")
            if name is not None:
                counts[f"copied_{e['copied']}"] += 1
            continue
        name = window["name"]
        if name is None:
            continue
        if kind in ("confusion_damage",) or (kind == "attack_failed" and e.get("reason") in ("attack_check", "confusion")):
            counts[f"{name}_interrupted"] += 1
            window["name"] = None
        elif kind == "coin_flip" and e.get("source") == "attack" and e.get("effect") == window["key"]:
            window["coins"].append(e["result"])
        elif kind == "esp_redo" and e.get("effect") == window["key"]:
            counts["esp_redo"] += 1
            del window["coins"][-2 * len(e["original"]):-len(e["original"])]
        elif kind == "esp_redo_declined" and e.get("effect") == window["key"]:
            counts["esp_redo_declined"] += 1
        elif kind == "reveal_from_deck" and e.get("effect") == window["key"]:
            window["revealed"] += 1
            window["decided"] = True
        elif kind == "reveal_from_deck_declined" and e.get("effect") == window["key"]:
            counts["squaredance_declined"] += 1
            window["decided"] = True
        elif kind == "shuffle" and e.get("effect") == window["key"] and name == "squaredance":
            counts["squaredance_shuffled"] += 1
        elif kind in ("attach_energy_from_deck", "deck_energy_evaded") and e.get("effect") == window["key"]:
            counts["attract_current_attached"] += 1
            counts["attract_current_evaded" if kind == "deck_energy_evaded" else
                   ("attract_current_to_active" if e.get("pokemon") == window["card"] else "attract_current_to_bench")] += 1
            window["targets"].append(e["pokemon_id"])
        elif kind == "attach_energy_from_deck_none" and e.get("effect") == window["key"]:
            counts[f"attract_current_none_{e['reason']}"] += 1
        elif kind == "bench_from_deck" and name == "call_for_family":
            counts["call_for_family_benched"] += 1
        elif kind == "bench_from_deck_none" and name == "call_for_family":
            counts["call_for_family_none"] += 1
        elif kind == "attack_failed":
            counts[f"{name}_failed_{e.get('reason')}" if name == "call_for_family" else f"{name}_failed"] += 1
            window["failed"] = True
        elif kind == "discard_energy" and e.get("effect") == window["key"]:
            window["discarded"] += 1
            if name == "dark_flame":
                counts["dark_flame_discarded"] += 1
            elif e.get("attacker_pokemon_id") is not None:
                counts["rushing_flames_from_bench"] += 1
        elif kind == "attach_energy_from_discard" and e.get("effect") == window["key"]:
            window["attached"] += len(e["cards"])
            counts["dark_flame_attached"] += len(e["cards"])
        elif kind == "effect_skipped" and e.get("effect") == window["key"]:
            window["skipped"] = True
            counts[f"{name}_skipped"] += 1
        elif kind == "special_condition" and e.get("effect") == window["key"] and e.get("condition") == "paralysis":
            counts["gigavolt_paralyzed"] += 1
        elif kind == "damage" and not e.get("retaliation") and e.get("steps"):
            base = e["steps"][0][1]
            if e.get("target") == "self":
                window["self_bases"].append(base)
            elif (e.get("target") or "opponent_active") == "opponent_active":
                window["bases"].append(base)
                if name in ("gigavolt", "flock_attack", "black_fang", "rushing_flames"):
                    counts[f"{name}_base_{base}"] += 1
                elif name in ("attract_current", "dark_flame", "claw_swipe", "doubleslap"):
                    counts[f"{name}_damage"] += 1
        elif kind == "knock_out" and name == "miraculous_comeback" and e.get("pokemon") == window["card"]:
            counts["miraculous_comeback_self_knock_out"] += 1
    close(window)
    return counts


V110_NAMES = {"たいあたり": "tackle", "こらえる": "endure", "こうてつか": "armor_up", "だいばくはつ": "explosion"}
V110_SURVIVAL_KIND = "knockout_survival"
V110_HITS = ("damage", "poison_damage", "confusion_damage", "place_damage_counters", "power_damage", "counterattack", "tool_damage_counters", "move_damage_counters")


def v110_uses(state):
    """v0.110: ログから数えた 2 枚のワザの動き（v0.110 のカードのない局では空）。

    - ``attack_<id>#<位置>``（宣言したワザ）・``copied_<id>#<位置>``（ほかのワザが相手のワザとして使った v0.110 のワザ）・``<名前>_interrupted``（こんらん・手順 4 のコインで失敗）
    - 使うときのコイン（こらえる・こうてつか）: ``<名前>_coin_<面>``（ESPでやり直したならやり直したあとの面）・``<名前>_given``・``<名前>_not_given``（「うら」）・``<名前>_skipped``
    - 「きぜつ」しなかった（``knockout_survived``。効果を与えたワザの名前ごと）: ``<名前>_survived``・``<名前>_survived_<own|opponent>_attack``（HP 以上にしたダメージの使い手）・
      ``<名前>_survived_retaliation``（返す効果のダメージ）・``<名前>_survived_<exact|overkill>``（ちょうど HP・HP を超えるダメージ）・``<名前>_survived_remaining_<残りHP>``・
      ``<名前>_survived_again``（同じ効果で 2 回目から）・
      ``survived_two_in_one_attack``（同じワザで 2 匹）
    - 効果のはたらく番に持つポケモンが受けたダメージ: ``<名前>_nonlethal_damage``（ワザのダメージで HP 以上にならなかった）・``<名前>_knocked_out_<最後に受けたものの種類>``（効果がはたらく
      番に、効果を持ったまま「きぜつ」した。どく・特殊能力のダメージ・ダメージカウンターなど）
    - 消えた理由: ``<名前>_removed_<理由>``（``expired`` は期限）
    - だいばくはつ: ``explosion_damage``・``explosion_opponent_ko``・``explosion_self_damage``・``explosion_self_lethal``・``explosion_self_survived``"""
    counts = Counter()
    if not any(state.cards[uid].card_id in V0_110 for uid in state.cards):
        return counts
    window = None
    effects = {}  # (持つポケモンの番号, 与えた番) → {"name", "active", "end", "survived"}
    last_hit = {}  # 場のポケモンの番号 → 最後に受けたダメージ・カウンターのログの種類
    pids = {}  # いちばん上のカード → 場のポケモンの番号（pokemon_id のないログのため。数えるためだけ）
    for e in state.log:
        kind = e["kind"]
        if e.get("pokemon") is not None and e.get("pokemon_id") is not None:
            pids[e["pokemon"]] = e["pokemon_id"]
        pid = e.get("pokemon_id", pids.get(e.get("pokemon")))
        if kind == "persistent_effect_added" and e.get("persistent_effect") == V110_SURVIVAL_KIND:
            card_id, index = e["effect"].split("#")
            name = V110_NAMES.get(state.definitions[card_id].attacks[int(index)].name_ja, "other")
            effects[(pid, e["turn"])] = {"name": name, "active": e["active_turn"], "end": e["end_turn"], "survived": 0}
            counts[f"{name}_given"] += 1
            if window is not None:
                window["given"] = True
        elif kind == "persistent_effect_removed" and e.get("persistent_effect") == V110_SURVIVAL_KIND:
            info = effects.pop((pid, e["created_turn"]), {"name": "other", "active": None, "end": None})
            counts[f"{info['name']}_removed_{e['reason']}"] += 1
            if e["reason"] == "knock_out" and info["active"] is not None and info["active"] <= e["turn"] <= info["end"]:
                counts[f"{info['name']}_knocked_out_{last_hit.get(pid, 'none')}"] += 1
        elif kind == "persistent_effect_skipped" and e.get("persistent_effect") == V110_SURVIVAL_KIND:
            card_id, index = e["effect"].split("#")
            counts[f"{V110_NAMES.get(state.definitions[card_id].attacks[int(index)].name_ja, 'other')}_skipped"] += 1
        elif kind == "knockout_survived":
            for created in e["created_turns"]:
                info = effects.get((pid, created), {"name": "other"})
                name = info["name"]
                counts[f"{name}_survived"] += 1
                counts[f"{name}_survived_{'own' if e['attacker'] == e['player'] else 'opponent'}_attack"] += 1
                if last_hit.get(pid) == "retaliation":
                    counts[f"{name}_survived_retaliation"] += 1
                counts[f"{name}_survived_{'exact' if e['damage_before'] == e['total_damage'] + e['remaining_hp'] else 'overkill'}"] += 1
                counts[f"{name}_survived_remaining_{e['remaining_hp']}"] += 1
                if info.get("survived"):
                    counts[f"{name}_survived_again"] += 1
                if "survived" in info:
                    info["survived"] += 1
            if window is not None:
                window["survivors"] = window.get("survivors", 0) + 1
                if window["survivors"] == 2:
                    counts["survived_two_in_one_attack"] += 1
                if window.get("name") == "explosion" and e["player"] == window["player"]:
                    counts["explosion_self_survived"] += 1
        if kind in V110_HITS:
            target = e.get("target_pokemon_id", pid) if kind in ("place_damage_counters", "tool_damage_counters", "counterattack") else pid
            last_hit[target] = "retaliation" if kind == "damage" and e.get("retaliation") else kind
            live = [info for (holder, _), info in effects.items() if holder == target and info["active"] <= e["turn"] <= info["end"]]
            if kind == "damage" and live and e["total_damage"] < state.in_play_def(e["pokemon"]).hp:
                for info in live:
                    counts[f"{info['name']}_nonlethal_damage"] += 1
        if window is not None and window["name"] in ("endure", "armor_up") and window.get("coin") is not None and not window.get("counted") \
                and kind in ("turn_end", "game_end", "halted"):
            window["counted"] = True
            counts[f"{window['name']}_coin_{window['coin']}"] += 1
            if not window.get("given"):
                counts[f"{window['name']}_not_given"] += 1
        if kind in ("attack", "turn_end", "game_end", "halted"):
            window = None
        if kind == "attack":
            current = e.get("card_id") or state.cards[e["pokemon"]].card_id
            key = f"{current}#{e['attack_index']}"
            name = V110_NAMES.get(state.definitions[current].attacks[e["attack_index"]].name_ja, "other") if current in V0_110 else None
            if current in V0_110:
                counts[f"attack_{key}"] += 1
            window = {"key": key, "name": name, "player": e["player"], "coin": None}
            continue
        if window is None:
            continue
        if kind == "copy_attack":
            if e["copied"].split("#")[0] in V0_110:
                counts[f"copied_{e['copied']}"] += 1
                card_id, index = e["copied"].split("#")
                window["name"] = V110_NAMES.get(state.definitions[card_id].attacks[int(index)].name_ja, "other")
            else:
                window["name"] = None
            window["key"] = e["copied"]
            continue
        name = window["name"]
        if name is None:
            continue
        if kind in ("confusion_damage", "attack_failed"):
            counts[f"{name}_interrupted"] += 1
            window["name"] = None
            continue
        if name in ("endure", "armor_up"):
            if kind == "coin_flip" and e.get("source") == "attack" and e["player"] == window["player"]:
                window["coin"] = e["result"]
            elif kind == "esp_redo":
                window["coin"] = e["redone"][-1]
        if name == "explosion" and kind == "damage" and not e.get("retaliation"):
            if e.get("target") == "self":
                counts["explosion_self_damage"] += 1
                if e["total_damage"] >= state.in_play_def(e["pokemon"]).hp:
                    counts["explosion_self_lethal"] += 1
            elif e.get("target") is None and e["player"] != window["player"]:
                counts["explosion_damage"] += 1
                if e["total_damage"] >= state.in_play_def(e["pokemon"]).hp:
                    counts["explosion_opponent_ko"] += 1
    return counts


def _v107_window(state, key: str, player: int) -> dict:
    """v0.107: 1 回のワザの数える窓（数える名前・コイン・失敗・特殊状態）。v0.107 のカードのワザでなければ名前は None。"""
    card_id, index = key.split("#")
    attack = state.definitions[card_id].attacks[int(index)]
    name = None
    if card_id in V0_107:
        name = V107_IMPLS.get(_v104_impl(state, key)) or V107_NAMES.get(attack.name_ja, "other")
    return {"key": key, "name": name, "player": player, "coins": [], "failed": False, "status": False, "blocked": False, "interrupted": False}


def _v107_close(window, counts):
    """v0.107: 1 回のワザの終わりに数える（コインの面・失敗・受けなかった特殊状態）。"""
    name = window.get("name")
    if name is None:
        return
    if window.get("interrupted"):
        counts[f"{name}_interrupted"] += 1
        return
    coins = window["coins"]
    if name == "lariat":
        counts[f"lariat_heads_{coins.count('heads')}"] += 1
    elif len(coins) == 1:
        counts[f"{name}_{coins[0]}"] += 1
    if window["failed"]:
        counts[f"{name}_failed"] += 1
    if name in ("stab", "headpress", "clamp", "rainbow", "migraine", "shock") and coins and not window["failed"] and not window["status"] and window["blocked"]:
        counts[f"{name}_status_blocked"] += 1


V104_HEAL_IMPLS = ("coin_choose_own_pokemon_heal_all", "coins_heal_self_times", "heal_all_self_then_self_sleep", "heal_self_without_damage", "optional_heal_self",
                   "heal_both_actives_then_sleep")


def _v104_impl(state, key: str) -> str | None:
    """v0.104: ワザ ``key``（カード id#位置）の登録の実装の id（なければ None）。"""
    card_id, index = key.split("#")
    entry = state.effects.attack_entry(card_id, int(index))
    return None if entry is None else entry.effect.implementation_id


def v101_uses(state):
    """v0.101: ログから数えた v0.101 の動き（ソーナンス・アンノーンK のない局では空）。

    - カウンター: ``attack_neo2-031#0``（宣言）・``counter_given``（効果を与えた）・``counter_skipped``（与えなかった）・``counter_coin_heads``・``counter_coin_tails``・
      ``counter_returned``（返したダメージの回数。``counter_returned_amount`` は基本となる量の合計）・``counter_target_knocked_out``（返す相手がすでに HP 以上）・
      ``counter_holder_knocked_out``（返したときソーナンスが HP 以上だった）・``counter_expired``（はたらかずに消えた）・``counter_removed_<理由>``
    - ［KEEP］: ``keep_voided_<原因>``・``keep_voided_<原因>_<ワザ・特殊能力・トレーナーのカード id>``（なくなったトラッシュ）と、なくなった効果のワザの中で続いたほかの処理
      （``keep_attack_damage``（正のダメージ）・``keep_attack_other_discard``（ほかのポケモンのトラッシュ）・``keep_attack_own_discard``（自分のエネルギーのトラッシュ））"""
    counts = Counter()
    if not any(state.cards[uid].card_id in V0_101 for uid in state.cards):
        return counts
    counter_key = f"{WOBBUFFET}#0"
    window = None  # 今のワザの {"voided": bool, "events": [...]}
    windows = []
    for e in state.log:
        kind = e["kind"]
        if kind == "attack":
            key = f"{e.get('card_id') or state.cards[e['pokemon']].card_id}#{e['attack_index']}"
            if key == counter_key:
                counts[f"attack_{key}"] += 1
            window = {"voided": False, "events": [], "holders": set()}
            windows.append(window)
        elif kind in ("turn_end", "turn_start"):
            window = None
        elif window is not None:
            window["events"].append(e)
        if kind == "persistent_effect_added" and e.get("effect") == counter_key:
            counts["counter_given"] += 1
        elif kind == "persistent_effect_skipped" and e.get("effect") == counter_key:
            counts["counter_skipped"] += 1
        elif kind == "coin_flip" and e.get("effect") == counter_key and e.get("source") == "attack":
            counts[f"counter_coin_{e['result']}"] += 1
        elif kind == "retaliation" and e.get("effect") == counter_key:
            counts["counter_returned"] += 1
            counts["counter_returned_amount"] += e["amount"]
            if window is not None:
                window["holders"].add(e["pokemon"])
        elif kind == "knock_out" and window is not None and e.get("pokemon") in window["holders"]:
            counts["counter_holder_knocked_out"] += 1  # 返したワザのあとのきぜつの処理で、ソーナンスもきぜつした（返すダメージは受けたダメージそのもの）
        elif kind == "retaliation_skipped" and e.get("effect") == counter_key and e.get("reason") == "knocked_out":
            counts["counter_target_knocked_out"] += 1
        elif kind == "persistent_effect_removed" and e.get("persistent_effect") == "retaliation_received_damage_scaled" \
                and state.cards[e["source_card"]].card_id == WOBBUFFET:
            counts["counter_expired" if e.get("reason") == "expired" else f"counter_removed_{e.get('reason')}"] += 1
        elif kind == "energy_discard_voided":
            source = e.get("effect") or e.get("power") or (state.cards[e["trainer_card"]].card_id if "trainer_card" in e else None)
            counts[f"keep_voided_{e['cause']}"] += 1
            counts[f"keep_voided_{e['cause']}_{str(source).split('#')[0].split('@')[0]}"] += 1
            if window is not None and e["cause"] == "attack":
                window["voided"] = True
    for w in windows:
        if not w["voided"]:
            continue
        counts["keep_attack_damage"] += sum(1 for e in w["events"] if e["kind"] == "damage" and e["amount"] > 0)
        counts["keep_attack_other_discard"] += sum(1 for e in w["events"] if e["kind"] == "discard_attached_energy")
        counts["keep_attack_own_discard"] += sum(1 for e in w["events"] if e["kind"] == "discard_energy")
    return +counts


def v100_uses(state):
    """v0.100: ログから数えた v0.100 のカードの動き（v0.100 のカードのない局では空）。ワザの宣言の回数と、効果の結果を分けて数える。

    - ``attack_<id>#<位置>``: 宣言（スケッチ・やみのひとみ・ほろびのうた。こんらんの「うら」・手順 4 の失敗も数える）
    - スケッチ: ``sketch_copied``・``sketch_copied_<ワザ>``（切りかえた）・``sketch_none_no_attack``（前の相手の番にワザがない）・``sketch_failed_not_in_play``（場に出ていなかった）
    - やみのひとみ: ``night_eyes_slept``（ねむり状態にした。``already`` を含む）・``night_eyes_immune``（［めんえき］）・``night_eyes_prevented``（バリアーなど）・``night_eyes_evaded``
    - ほろびのうた: ``perish_not_asleep``・``perish_not_received``・``perish_knock_out``（ワザの効果のきぜつ）・``perish_prevented``・``perish_evaded``
    - まねたワザ: ``copied_<まねたワザ>_by_<宣言したワザ>``（ゆびをふる・スケッチでやみのひとみ・ほろびのうたを使った）"""
    counts = Counter()
    if not any(state.cards[uid].card_id in V0_100 for uid in state.cards):
        return counts
    names = {f"{SMEARGLE}#0": "sketch", f"{MISDREAVUS}#0": "night_eyes", f"{MISDREAVUS}#1": "perish_song"}
    current = None  # 今のワザ（宣言したワザ・まねたワザ）
    for e in state.log:
        kind = e["kind"]
        if kind in ("turn_start", "turn_end"):
            current = None
            continue
        if kind == "attack":
            key = f"{e.get('card_id') or state.cards[e['pokemon']].card_id}#{e['attack_index']}"
            current = [key, None]
            if key in names:
                counts[f"attack_{key}"] += 1
            continue
        if current is None:
            continue
        if kind == "copy_attack":
            current[1] = e["copied"]
            if e.get("used_turn") is not None:
                counts["sketch_copied"] += 1
                counts[f"sketch_copied_{e['copied']}"] += 1
            if e["copied"] in names:
                counts[f"copied_{names[e['copied']]}_by_{current[0]}"] += 1
        elif kind == "sketch_none":
            counts[f"sketch_none_{e['reason']}"] += 1
        elif kind == "attack_failed" and current[0] == f"{SMEARGLE}#0":
            counts[f"sketch_failed_{e['reason']}"] += 1
        effective = current[1] or current[0]
        if effective == f"{MISDREAVUS}#0":
            if kind == "special_condition" and e.get("condition") == "sleep":
                counts["night_eyes_slept"] += 1
            elif kind == "special_condition_prevented" and e.get("condition") == "sleep":
                counts["night_eyes_immune"] += 1
            elif kind == "effect_prevented" and e.get("element") == "sleep":
                counts["night_eyes_prevented"] += 1
            elif kind == "attack_evaded" and e.get("element") == "sleep":
                counts["night_eyes_evaded"] += 1
        if effective == f"{MISDREAVUS}#1":
            if kind == "knock_out_condition":
                counts["perish_not_asleep" if not e["asleep"] else "perish_checked_received" if e["received"] == "received" else "perish_not_received"] += 1
            elif kind == "effect_knock_out":
                counts["perish_knock_out"] += 1
            elif kind == "effect_prevented" and e.get("element") == "knock_out":
                counts["perish_prevented"] += 1
            elif kind == "attack_evaded" and e.get("element") == "knock_out":
                counts["perish_evaded"] += 1
    return +counts

def _v094_decision(state, counts):
    """v0.94 のワザの決定への答え（元の手順より先に答える）: きつねびの任意の入れ替え（``FORCED_SWITCH`` の 0〜1 匹）は、決定のたびに 入れ替えない・控えを順に を回す（入れ替えない
    答えも起こす）。ほかの v0.94 のワザの決定（相手・自分の入れ替えの控え）は、選べるものを順に回す（v0.92 の ``_v092_decision`` と同じ。選ぶと止める答えは選ばない）。v0.94 のワザの
    決定でなければ何もしない。"""
    d = state.decision
    if d is None or d.resume != "attack":
        return None
    card_id = _v085_source(state, d)
    if card_id not in V0_94:
        return None
    key = f"v094_{card_id}_{d.kind}"
    seen = counts[f"{key}_seen"]
    counts[f"{key}_seen"] += 1
    blocked = set(d.context_value("unresolved_choices", ()) or ())
    if blocked:
        counts[f"{key}_blocked_choices"] += 1
    if d.min_choices == 0 and seen % 3 == 0:
        counts[f"{key}_declined"] += 1
        return ResolveDecision(d.player, d.id, ())
    rotated = list(d.options[seen % len(d.options):]) + list(d.options[:seen % len(d.options)]) if d.options else []
    for choice in [o for o in rotated if o not in blocked]:
        if _v052_accepted(state, ResolveDecision(d.player, d.id, (choice,))):
            counts[f"{key}_answered"] += 1
            return ResolveDecision(d.player, d.id, (choice,))
    if d.min_choices == 0:
        counts[f"{key}_declined_no_choice"] += 1
        return ResolveDecision(d.player, d.id, ())
    counts[f"{key}_no_accepted_answer"] += 1
    return None


def v094_uses(state):
    """v0.94: ログから数えた v0.94 のカードの動き（v0.94 のカードのない局では空）。``attack_<id>#<位置>``（v0.94 のカードが使ったワザ）・``coin_<id>#<位置>_<表裏>``（ワザの最初の
    コイン）・``opponent_switched_<id>#<位置>_<選んだ側>``・``self_switched_<id>#<位置>``（どちら側が入れ替わったか）・``switch_declined_<id>#<位置>``（任意の辞退）・
    ``switch_skipped_<id>#<位置>_<理由>``・``returned_to_hand_<id>#<位置>``（帰還）・``attack_failed_<id>#<位置>_<理由>``・``leave_prevented_<id>#<位置>_<原因>``・
    ``status_<id>#<位置>_<種類>``・``damage_<id>#<位置>=<量>``（相手の対戦ポケモンへの最初のダメージ）・``promote_after_return``（帰還のあとに相手が出したポケモン）。"""
    counts = Counter()
    if not any(state.cards[uid].card_id in V0_94 for uid in state.cards):
        return counts
    current = None
    first_coin = first_damage = False
    returned = False
    for e in state.log:
        kind = e["kind"]
        if kind == "attack":
            holder = state.cards[e["pokemon"]].card_id if e.get("pokemon") in state.cards else None
            current = e.get("card_id", holder)
            current = f"{current}#{e['attack_index']}" if current in V0_94 else None
            first_coin = first_damage = False
            if current is not None:
                counts[f"attack_{current}"] += 1
        elif kind in ("turn_start", "turn_end"):
            current = None
        elif kind == "promote_active" and returned:
            counts["promote_after_return"] += 1
            returned = False
        elif current is None:
            continue
        elif kind == "coin_flip" and e.get("source") == "attack" and not first_coin:
            counts[f"coin_{current}_{e['result']}"] += 1
            first_coin = True
        elif kind == "forced_switch":
            counts[f"opponent_switched_{current}_{'attacker' if e.get('chosen_by') == 'attacker' else 'opponent'}"] += 1
        elif kind == "switch" and e.get("effect"):
            counts[f"self_switched_{current}"] += 1
        elif kind == "forced_switch_declined":
            counts[f"switch_declined_{current}"] += 1
        elif kind == "forced_switch_skipped":
            counts[f"switch_skipped_{current}_{e['reason']}"] += 1
        elif kind == "return_in_play_to_hand":
            counts[f"returned_to_hand_{current}"] += 1
            returned = True
        elif kind == "attack_failed":
            counts[f"attack_failed_{current}_{e.get('reason')}"] += 1
        elif kind == "leave_prevented":
            counts[f"leave_prevented_{current}_{e['cause']}"] += 1
        elif kind == "special_condition":
            counts[f"status_{current}_{e.get('condition')}"] += 1
        elif kind == "damage" and not first_damage:
            counts[f"damage_{current}={e['amount']}"] += 1
            first_damage = True
    return +counts


def v093_uses(state):
    """v0.93: ログから数えた v0.93 のカードの動き（v0.93 のカードのない局では空）。``attack_<id>#<位置>``（v0.93 のカードが使ったワザ）・``coin_<id>#<位置>_<表裏>``（ワザの最初の
    コイン）・``lock_added_<種類>``・``lock_removed_<種類>_<理由>``（はなれられない効果・期間を明示したワザの禁止・手順 4 のコイン・にげるの禁止・オクタンほう）・
    ``leave_prevented_<原因>``（はなれさせる部分が起こらなかった）・``source_left_marked``（くいつく）・``attack_check_<種類>_<結果>``（受けた効果の手順 4 のコイン）・
    ``entangle_switched``・``entangle_paralyzed``・``entangle_failed``・``poison_bind_poison``・``status_<種類>``（へんなこな・からみつく）・``bonus_damage``（いやなおとの +20）。"""
    counts = Counter()
    if not any(state.cards[uid].card_id in V0_93 for uid in state.cards):
        return counts
    kinds = ("period_leave_lock", "period_attack_lock", "period_attack_coin_check", "period_retreat_lock", "attack_coin_check", "received_attack_damage_bonus")
    current = None
    first_coin = False
    for e in state.log:
        kind = e["kind"]
        if kind == "attack":
            holder = state.cards[e["pokemon"]].card_id if e.get("pokemon") in state.cards else None
            current = e.get("card_id", holder)
            current = f"{current}#{e['attack_index']}" if current in V0_93 else None
            first_coin = False
            if current is not None:
                counts[f"attack_{current}"] += 1
        elif kind in ("turn_start", "turn_end"):
            current = None
        elif kind == "coin_flip" and current is not None and e.get("source") == "attack" and not first_coin:
            counts[f"coin_{current}_{e['result']}"] += 1
            first_coin = True
        elif kind == "persistent_effect_added" and current is not None and e["persistent_effect"] in kinds:
            counts[f"lock_added_{e['persistent_effect']}"] += 1
        elif kind == "persistent_effect_removed" and e["persistent_effect"] in ("period_leave_lock", "period_attack_lock", "period_attack_coin_check", "period_retreat_lock"):
            counts[f"lock_removed_{e['persistent_effect']}_{e['reason']}"] += 1
        elif kind == "leave_prevented":
            counts[f"leave_prevented_{e['cause']}"] += 1
        elif kind == "persistent_effect_source_left":
            counts["source_left_marked"] += 1
        elif kind == "attack_check" and e.get("persistent_effect") in ("period_attack_coin_check", "attack_coin_check"):
            counts[f"attack_check_{e['persistent_effect']}_{e['result']}"] += 1
        elif kind == "forced_switch" and current == "neo4-011#0":
            counts["entangle_switched"] += 1
        elif kind == "attack_failed" and current == "neo4-011#0":
            counts[f"entangle_failed_{e.get('reason')}"] += 1
        elif kind == "special_condition" and current is not None:
            counts[f"status_{current}_{e.get('condition')}"] += 1
        elif kind == "damage" and current is not None and any(str(step[0]).endswith("（received_attack_damage_bonus）") for step in e.get("steps") or ()):
            counts["bonus_damage"] += 1
    return +counts


def _v090_decision(state, counts):
    """v0.90 のワザの決定への答え（元の手順より先に答える）: ボーンキラー・ころがるの取りのぞく数（0 も選ぶ）・ペイントの色・サイコブラストのトラッシュするカード。v0.89 の
    ``_v089_decision`` と同じ回し方（選べるものを順に回し、受け付ける答えだけを選ぶ。選ぶと止める答えは選ばない）。v0.90 のワザの決定でなければ何もしない。"""
    d = state.decision
    if d is None:
        return None
    card_id = _v085_source(state, d)
    if card_id not in V0_90:
        return None
    key = f"v090_{card_id}_{d.kind}"
    seen = counts[f"{key}_seen"]
    counts[f"{key}_seen"] += 1
    blocked = set(d.context_value("unresolved_choices", ()) or ())
    if blocked:
        counts[f"{key}_blocked_choices"] += 1
    rotated = list(d.options[seen % len(d.options):]) + list(d.options[:seen % len(d.options)]) if d.options else []
    sizes = [d.max_choices, d.min_choices, max(d.min_choices, 1)] if seen % 2 == 0 else [d.min_choices, max(d.min_choices, 1), d.max_choices]
    candidates = [tuple(o for o in rotated if o not in blocked)[:n] for n in sizes] + [(o,) for o in d.options if o not in blocked]
    for choices in candidates:
        if d.min_choices <= len(choices) <= d.max_choices and _v052_accepted(state, ResolveDecision(d.player, d.id, choices)):
            label = choices[0] if d.kind == SELECT_MARKER_COUNT and choices else len(choices)  # 取りのぞく数は答えの値を数える
            counts[f"{key}_{label}"] += 1
            return ResolveDecision(d.player, d.id, choices)
    counts[f"{key}_no_accepted_answer"] += 1
    return None


def v091_uses(state):
    """v0.91: ログから数えた v0.91 のカードの動き（v0.91 のカードのない局では空）。``attack_<id>#<位置>``（v0.91 のカードが使ったワザ）・``char_check_<表裏>``・``char_damage``・
    ``char_knock_out``（ポケモンチェックでくろこげマーカーのポケモンがきぜつした）・``bolt_<受けるものの種類>``（かみなりショックのマーカーのポケモンへの 20）・``rod_placed``・
    ``recolored``（ハイパーテクスチャー）・``all_clear_trainers``・``all_clear_stadium``・``all_clear_conditions``・``all_clear_effects``・``all_clear_markers_<種類>``・
    ``power_suppression``（オールクリアの期間の始まりと終わりの組）・``attack_check_<成功・失敗>``（えんまくのコイン）。"""
    counts = Counter()
    if not any(state.cards[uid].card_id in V0_91 for uid in state.cards):
        return counts
    current = None
    figure = False  # かみなりショックの目安のダメージ（最初の相手の対戦ポケモンへのダメージ）を数えた
    char_cards: set[int] = set()  # 「うら」のくろこげマーカーのポケモンのいちばん上のカード（ログ knock_out は番号を書かない）
    for e in state.log:
        kind = e["kind"]
        if kind == "attack":
            holder = state.cards[e["pokemon"]].card_id if e.get("pokemon") in state.cards else None
            current = e.get("card_id", holder)
            current = f"{current}#{e['attack_index']}" if current in V0_91 else None
            figure = False
            if current is not None:
                counts[f"attack_{current}"] += 1
        elif kind in ("turn_start", "turn_end"):
            current = None
        elif kind == "char_check":
            counts[f"char_check_{e['result']}"] += 1
            if e["damaged"]:
                char_cards.add(e["pokemon"])
        elif kind == "char_damage":
            counts["char_damage"] += 1
        elif kind == "knock_out" and e.get("timing") == "pokemon_check" and e.get("pokemon") in char_cards:
            counts["char_knock_out"] += 1
        elif kind == "damage" and current == "ES2-017#1":
            if e.get("target") is None and not figure:
                figure = True  # 目安の 10
            else:
                counts[f"bolt_{e.get('target', 'opponent_active')}"] += 1
        elif kind == "marker_added" and e["marker"] == "lightning_rod":
            counts["rod_placed"] += 1
        elif kind == "marker_added" and e["marker"] == "color" and current == "PRN-023#1":
            counts["recolored"] += 1
        elif kind == "discard_attached_trainer" and current == "PRN-023#0" and e.get("reason") == "attack":
            counts["all_clear_trainers"] += 1
        elif kind == "stadium_discarded" and current == "PRN-023#0":
            counts["all_clear_stadium"] += 1
        elif kind == "special_conditions_removed" and current == "PRN-023#0":
            counts["all_clear_conditions"] += 1
        elif kind == "persistent_effect_removed" and current == "PRN-023#0" and e.get("reason") == "cured":
            counts["all_clear_effects"] += 1
        elif kind == "marker_removed" and e.get("reason") == "cleared" and current == "PRN-023#0":
            counts[f"all_clear_markers_{e['marker']}"] += e["count"]
        elif kind == "trainer_effect_removed" and e.get("reason") == "attack_end":
            counts["power_suppression"] += 1
        elif kind == "attack_check":
            counts[f"attack_check_{'ok' if e['succeeded'] else 'failed'}"] += 1
    return +counts


def v090_uses(state):
    """v0.90: ログから数えた、マーカー・カウンターの動き（v0.90 のカードのない局では空）。``attack_<id>#<位置>``（v0.90 のカードが使ったワザ）・``added_<種類>``（のせた）・
    ``removed_<理由>_<種類>``（取りのぞいた。used（消費）・evolve・devolve・replaced・cleared）・``declined_<種類>``（のぞまなかった）・``kept_on_bench``（のっているポケモンが
    にげる・入れ替えでベンチにもどった）・``left_play_with_markers``（のっているポケモンがきぜつ・手札や山札にもどった）・``retreat_sticky``（ベトベトマーカーで増やしたにげる）・
    ``curse_x4``（のろいマーカーで「×4」にしたダメージ）・``painted_attacker``（色マーカーののったポケモンがワザを使った）。"""
    counts = Counter()
    if not any(state.cards[uid].card_id in V0_90 for uid in state.cards):
        return counts
    marks: dict[int, list[str]] = {}
    pid_of_card: dict[int, int] = {}
    for e in state.log:
        kind = e["kind"]
        if "pokemon_id" in e and "pokemon" in e:
            pid_of_card[e["pokemon"]] = e["pokemon_id"]
        if kind == "attack":
            holder = state.cards[e["pokemon"]].card_id if e.get("pokemon") in state.cards else None
            current = e.get("card_id", holder)
            if current in V0_90:
                counts[f"attack_{current}#{e['attack_index']}"] += 1
            if "color" in marks.get(pid_of_card.get(e.get("pokemon")), []):
                counts["painted_attacker"] += 1
        elif kind == "marker_added":
            marks.setdefault(e["pokemon_id"], []).append(e["marker"])
            counts[f"added_{e['marker']}"] += 1
        elif kind == "marker_removed":
            for _ in range(e["count"]):
                marks[e["pokemon_id"]].remove(e["marker"])
            counts[f"removed_{e['reason']}_{e['marker']}"] += e["count"]
        elif kind == "marker_removal_declined":
            counts[f"declined_{e['marker']}"] += 1
        elif kind == "retreat":
            counts["retreat_sticky"] += bool(e.get("retreat_cost_markers"))
            counts["kept_on_bench"] += bool(marks.get(pid_of_card.get(e["old_active"])))
        elif kind in ("switch", "forced_switch"):
            counts["kept_on_bench"] += bool(marks.get(e.get("old_active_pokemon_id")))
        elif kind in ("knock_out", "return_in_play_to_hand", "return_in_play_to_deck"):
            pid = e.get("pokemon_id", pid_of_card.get(e.get("pokemon")))
            if marks.get(pid):
                counts["left_play_with_markers"] += 1
                marks[pid] = []
        elif kind == "damage":
            counts["curse_x4"] += e.get("weakness_multiplier") == 4
    return +counts


def v089_uses(state):
    """v0.89: ログから数えた v0.89 のカードの動き（ない局では空）。``attack_<id>#<位置>``（そのカードが使ったワザ）・``target_<受けるものの種類>``（v0.89 のカードのワザの中のダメージの
    受けるもの。選んだ個体へのダメージを含む）・``ignore_effects_scope``（だましうちのダメージ）・``damage_reduced``・``heal``・``microwave_discard``・``bench_guard``・``esp_redo``・
    ``esp_redo_declined``。"""
    counts = Counter()
    if not any(state.cards[uid].card_id in V0_89 for uid in state.cards):
        return counts
    current = None  # 処理しているワザを印刷したカード（ワザの宣言から次の番の始まりまで）
    for e in state.log:
        kind = e["kind"]
        if kind == "attack":
            holder = state.cards[e["pokemon"]].card_id if e.get("pokemon") in state.cards else None
            current = e.get("card_id", holder)
            if current in V0_89:
                counts[f"attack_{current}#{e['attack_index']}"] += 1
        elif kind == "turn_start":
            current = None
        elif current not in V0_89:
            continue
        elif kind == "damage":
            counts[f"target_{e.get('target', 'opponent_active')}"] += 1
            counts["ignore_effects_scope"] += bool(e.get("ignore_effects_scope"))
            counts["damage_reduced"] += bool(e.get("damage_reduced"))
        elif kind == "attack_heal":
            counts["heal"] += 1
        elif kind == "discard_attached_energy":
            counts["microwave_discard"] += 1
        elif kind in ("bench_guard", "esp_redo", "esp_redo_declined"):
            counts[kind] += 1
    return +counts


def v086_uses(state):
    """v0.86: ログから数えた v0.86 のカードの動き（ない局では空）。``attack_<id>#<位置>``・``power_<id>``（宣言・使う機会で使った・かならずはたらく）・``entry_declined``・
    ``reaction_declined``・``reaction_evolved``（［エナジーしんか］・［れんさしんか］で山札から重ねた）・``conductivity``・``burst_switched``・``burst_skipped``・``bolt_<面>``・
    ``bolt_returned``・``howl_turn_end``・``drain_coins``・``hand_lock``・``powers_stopped``・``bench_protected``・``crystal_body``（効果の要素を受けなかった）。
    能力のあるカードが場にいることではなく、ログに残った効果の発動を数える。"""
    counts = Counter()
    if not any(state.cards[uid].card_id in V0_86 for uid in state.cards):
        return counts
    for e in state.log:
        kind = e["kind"]
        effect = e.get("effect")
        ours = isinstance(effect, str) and effect.split("#")[0].split("@")[0] in V0_86
        power = e.get("power")
        ours_power = isinstance(power, str) and power.split("#")[0].split("@")[0] in V0_86
        if kind == "attack" and isinstance(e.get("pokemon"), int) and state.cards[e["pokemon"]].card_id in V0_86:
            counts[f"attack_{state.cards[e['pokemon']].card_id}#{e['attack_index']}"] += 1
        elif kind == "pokemon_power" and isinstance(e.get("pokemon"), int) and state.cards[e["pokemon"]].card_id in V0_86:
            counts[f"power_{state.cards[e['pokemon']].card_id}{'_forced' if e.get('forced') else ''}"] += 1
        elif kind == "entry_power_declined" and isinstance(e.get("pokemon"), int) and state.cards[e["pokemon"]].card_id in V0_86:
            counts["entry_declined"] += 1
        elif kind == "reaction_power_declined":
            counts["reaction_declined"] += 1
        elif kind == "evolve" and ours_power and e.get("source_zone") == "deck":
            counts["reaction_evolved"] += 1
        elif kind == "conductivity":
            counts["conductivity"] += 1
        elif kind == "switch" and ours_power:
            counts["burst_switched"] += 1
        elif kind == "lightning_burst_skipped":
            counts["burst_skipped"] += 1
        elif kind == "bolt_check":
            counts[f"bolt_{e['result']}"] += 1
        elif kind == "return_in_play_to_deck" and ours_power:
            counts["bolt_returned"] += 1
        elif kind == "power_turn_end":
            counts["howl_turn_end"] += 1
        elif kind == "pokemon_coin_results" and ours:
            counts["drain_coins"] += 1
        elif kind == "trainer_lock_added" and ours:
            counts["hand_lock"] += 1
        elif kind == "persistent_effect_added" and ours:
            counts[f"persistent_{e.get('persistent_effect', e.get('effect_kind', 'effect'))}"] += 1
        elif kind == "effect_prevented" and e.get("persistent_effect") == "crystal_body":
            counts["crystal_body"] += 1
        elif kind == "power_damage" and ours_power:
            counts["surprise_bite"] += 1
        elif kind == "remove_damage_counters" and ours_power:
            counts["entry_heal"] += 1
        elif kind == "special_conditions_removed" and ours_power:
            counts["solar_cured"] += 1
    return counts


def v085_uses(state):
    """v0.85: ログから数えた v0.85 のカードの動き（ない局では空）。``attack_<id>#<位置>``・``power_<id>@<位置>``（宣言・かならずはたらく）・``entry_declined``・
    ``berserk_<自分|相手>``・``herbal_heal``・``boost_attached``・``recharge_attached``・``downpour``・``raise_moved``・``miracle_<理由>``（ミラクルエネルギーのトラッシュ）・
    ``riptide_returned``・``static_attached``。"""
    counts = Counter()
    if not any(state.cards[uid].card_id in V0_85 for uid in state.cards):
        return counts
    for e in state.log:
        kind = e["kind"]
        effect = e.get("effect")
        ours = isinstance(effect, str) and effect.split("#")[0].split("@")[0] in V0_85
        power = e.get("power")
        ours_power = isinstance(power, str) and power.split("#")[0].split("@")[0] in V0_85
        if kind == "attack" and ours:
            counts[f"attack_{effect}"] += 1
        elif kind == "pokemon_power" and e.get("power") and isinstance(e.get("pokemon"), int) and state.cards[e["pokemon"]].card_id in V0_85:
            counts[f"power_{state.cards[e['pokemon']].card_id}{'_forced' if e.get('forced') else ''}"] += 1
        elif kind == "entry_power_declined" and isinstance(e.get("pokemon"), int) and state.cards[e["pokemon"]].card_id in V0_85:
            counts["entry_declined"] += 1
        elif kind == "power_discard_deck":
            counts["berserk_" + ("self" if e["player"] == e["user"] else "opponent")] += 1
        elif kind == "remove_damage_counters" and ours_power:
            counts["herbal_heal"] += 1
        elif kind == "power_attach_from_deck":
            counts["boost_attached"] += 1
        elif kind == "power_attach_from_discard":
            counts["recharge_attached"] += 1
        elif kind == "discard_from_hand" and ours_power:
            counts["downpour"] += 1
        elif kind == "move_energy" and ours_power:
            counts["raise_moved"] += 1
        elif kind == "miracle_energy_discarded":
            counts[f"miracle_{e['reason']}"] += 1
        elif kind == "attack_discard_to_deck":
            counts["riptide_returned"] += len(e["cards"])
        elif kind == "attach_energy_from_deck" and ours and effect.startswith("neo1-038"):
            counts["static_attached"] += 1
    return counts


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
        apply_command(_v052_real(state), command)
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
        apply_command(_v052_real(state), command)
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


# ---------------------------------------------------------------- v0.114（docs/baby-rules-evolution-v0.114.md）: ベイビィポケモン 13 枚の手順と数え方


def _v114_baby_targets(state, player):
    """v0.114: 自分の場の、今の番に進化させてよい（おたがいの最初の番でない・その番の最初から場にいた・うらでない・進化を禁じる効果がない）進化していないベイビィポケモンと、
    手札の、その進化先の名前のたねポケモンカードの組（(場のポケモン, 手札のカード)。場の並び → 手札の並び）。進化できるかの確かめはエンジン（ここは拒否を起こさないための見分け）。"""
    p = state.players[player]
    if state.turn_number <= 2:
        return []
    found = []
    for pokemon in p.in_play():
        if state.is_face_down(pokemon) or not E.is_baby_in_play(state, pokemon) or pokemon.current_form_turn >= state.turn_number:
            continue
        if E.evolution_preventers(state) or E.evolution_forbidden(state, pokemon) is not None:
            continue
        names = state.card_def(pokemon.card).evolves_to
        found.extend((pokemon, uid) for uid in p.hand if state.card_def(uid).is_basic_pokemon and state.card_def(uid).name_ja in names)
    return found


def _v114_evolve(state, tried, counts):
    """v0.114: 手札のたねポケモンカードで、自分の場のベイビィポケモンを進化させる（GR-2000-P310-BABY-EVOLUTION。1 番に 1 匹ずつ。手順がそのカードをベンチに出す前にも使う）。
    ［ヒートプレート］がはたらいているときは使わない（HP2。単体のテストだけ）。進化したあとの HP がのっているダメージ以下になる組（H1）も使わない。拒否を起こさない。"""
    player = state.current_player
    if E.hot_plates(state):
        if ("v114_hot_plate", state.turn_number) not in tried and _v114_baby_targets(state, player):
            tried.add(("v114_hot_plate", state.turn_number))
            counts["v114_evolve_skipped_hot_plate"] += 1
        return None
    for pokemon, card in _v114_baby_targets(state, player):
        if ("max_hp_drop_card", card) in tried or E.evolution_hp(state, pokemon, card) <= pokemon.damage:
            continue
        counts["v114_evolve_baby_" + ("active" if pokemon is state.players[player].active else "bench")] += 1
        return EvolvePokemon(player, card, pokemon.pokemon_id)
    return None


def _v114_power(state, command, tried, counts):
    """v0.114: ププリン（neo2-050）の［じっとみる］（この番にまだ使っておらず、力が止まっていなくて、相手のベンチに「特殊能力」を持っているポケモン（決まっているもの）がいれば、その
    いちばん前）と、エレキッド（neo1-044）の［わんぱくパンチ］（手順が番を終えるとき。ねむり・マヒ・こんらんでなく、この番にまだ使っておらず、力が止まっていなくて、コインの前に
    止める理由（Z9・DB1・MT1・DF2）がないとき。使ったら番が終わる）。拒否を起こさない。"""
    from kyuura_engine.continuous import power_suppressed
    from kyuura_engine.persistent import powers_use_prevented

    player = state.current_player
    p = state.players[player]
    for pokemon in p.in_play():
        if state.is_face_down(pokemon):
            continue
        card_id = state.cards[pokemon.card].card_id
        if card_id not in ("neo2-050", "neo1-044") or (pokemon.pokemon_id, 0) in state.power_uses_this_turn:
            continue
        definition = state.card_def(pokemon.card)
        if power_suppressed(state, definition.powers[0], pokemon) or powers_use_prevented(state, pokemon) is not None:
            continue
        use = E.PowerUse(player, pokemon.pokemon_id, E_PowerKey(card_id, 0))
        if card_id == "neo2-050":
            targets = [b for b in state.players[1 - player].bench if E.holds_power(state, b) is True]
            if ("v114_stare", pokemon.pokemon_id, state.turn_number) in tried or not targets:
                continue
            tried.add(("v114_stare", pokemon.pokemon_id, state.turn_number))
            counts["v114_power_stare"] += 1
            return UsePokemonPower(player, pokemon.pokemon_id, 0, target=targets[0].pokemon_id)
        if not isinstance(command, EndTurn):
            continue
        conditions = pokemon.conditions
        if conditions.asleep or conditions.paralyzed or conditions.confused:
            continue
        effect = state.effects.power_effect(card_id, definition.powers[0])
        problem = effect.damage_problem(state, use)
        if problem is not None:
            counts[f"v114_bratty_punch_skipped_{problem.code}"] += 1
            continue
        counts["v114_power_bratty_punch"] += 1
        return UsePokemonPower(player, pokemon.pokemon_id, 0)
    return None


def _v114_rule_stop(state, command) -> bool:
    """v0.114（BQ1）: 相手のバトル場の進化していないベイビィポケモンのルールのコインと、手順 4・5 のコイン（すなかけなど・［はんこう］・こんらん）の順番。場から確かめる。"""
    from kyuura_engine.resolution.flow import attack_rebellion_powers as rebellion

    defender = state.players[1 - command.player].active
    attacker = _attacker(state, command)
    return (defender is not None and E.is_baby_in_play(state, defender)
            and (attacker.conditions.confused or bool(attack_coin_checks(state, attacker)) or bool(rebellion(state, attacker))))


V0_114_STOPS = {
    "UNRESOLVED_BABY_RULE_COIN_ORDER": _v114_rule_stop,
    # BX1: ［へんしん］で相手のベイビィポケモンと同じカードとしてあつかわれているメタモンに、ワザを使う
    "UNRESOLVED_TRANSFORM_BABY": lambda st, c: E.transform_baby_question(st, st.players[1 - c.player].active) is not None,
    # HV1: 「特殊能力」を持っているポケモンにダメージを与えるワザ（パチパチ）で、特殊能力がすべてほかの効果で消えているポケモンが場にいる
    "UNRESOLVED_STOPPED_POWER_HOLDER": lambda st, c: any(E.holds_power(st, pk) is None for side in st.players for pk in side.in_play()),
}


# ---------------------------------------------------------------- v0.115（docs/spread-damage-allocation-v0.115.md 8 章）: 場・ベンチへのダメージ、対象ごとのコイン、ダメージの配分

V115_NAMES = {
    "しょうげきは": "shock_wave", "スピードスター": "swift", "びっくりサンダー": "surprise_thunder", "ロケットずつき": "rocket_headbutt", "すなあらし": "sandstorm",
    "たたきつける": "slam", "なぎたおす": "mow_down", "じしん": "earthquake", "がんせきおとし": "rock_fall", "つめをだす": "claw", "サイコスプラッシュ": "psycho_splash",
    "だんがんタックル": "bullet_tackle", "ばくれつしんか": "explosive_evolution", "やまくだき": "mountain_smash", "ぶんなげる": "hurl", "しめつける": "bind",
    "ちていいどう": "earth_move", "ウォーターボム": "water_bomb", "がんせきくだき": "rock_smash", "ころがる": "rollout", "ロックブラスト": "rock_blast", "いしなだれ": "rock_slide",
}


def _v115_name(state, key: str | None) -> str | None:
    """v0.115: ワザ ``key``（"カード id#位置"）が v0.115 のワザなら、その集計の名前（ほかは None）。"""
    if key is None:
        return None
    card_id, index = key.split("#")
    return V115_NAMES.get(state.definitions[card_id].attacks[int(index)].name_ja) if card_id in V0_115 else None


def _v115_decision(state, counts):
    """v0.115 のワザの決定への答え（元の手順より先に答える。処理しているワザが v0.115 のワザでなければ何もしない）。受け付ける答えだけを選び、原典で決められない選択
    （``unresolved_choices``。いしなだれの相手の対戦ポケモン（SLD1））・0 枚・0 匹の答え（RKB1・GS1）は選ばない。

    - 配分（ALLOCATE_DAMAGE）: 決定のたびに、1 匹に集める（集める先を順に回す）・できるだけ分ける を交互に
    - ちていいどう（SELECT_POKEMON。0〜2 匹）: 選べるだけ・1 匹 を交互に（選ぶ控えは順に回す）。ぶんなげる・いしなだれ（1 匹）: 選べるものを順に回す
    - ロックブラスト（DISCARD_ENERGY。0〜5 枚）: 選べるだけ・1 枚・2 枚 を順に
    - ばくれつしんか（SEARCH_DECK）: 選べるものの前から（選べるものがなければ 0 枚）"""
    d = state.decision
    if d is None or d.resume != "attack" or d.player != state.current_player:
        return None
    use = d.context_value("use")
    copied = d.context_value("copied")
    key = f"{copied[0]}#{copied[1]}" if copied else (f"{use[2]}#{use[3]}" if use is not None else None)
    name = _v115_name(state, key)
    if name is None or d.kind not in (ALLOCATE_DAMAGE, SELECT_POKEMON, DISCARD_ENERGY, SEARCH_DECK):
        return None
    blocked = set(d.context_value("unresolved_choices") or ())
    options = tuple(o for o in d.options if o not in blocked)
    label = f"v115_{name}_{d.kind}"
    seen = counts[label]
    counts[label] += 1
    if d.kind == ALLOCATE_DAMAGE:
        table = [tuple(row) for row in d.context_value("table")]
        slots = len(table[0]) if table else 1
        concentrated = [i for i, row in enumerate(table) if max(row) == sum(row)]
        spread = sorted(range(len(table)), key=lambda i: (max(table[i]), table[i]))
        target = concentrated[(seen // 2) % len(concentrated)] if concentrated else 0
        order = [target, spread[0]] if seen % 2 == 0 else [spread[0], target]
        candidates = [(i,) for i in order] + [(i,) for i in range(len(table))]
        counts[f"v115_{name}_allocation_{'concentrated' if order[0] in concentrated and slots > 1 else 'spread' if slots > 1 else 'single'}"] += 1
    elif d.kind == SELECT_POKEMON:
        rotated = options[seen % len(options):] + options[:seen % len(options)] if options else ()
        if d.max_choices >= 2:
            top = rotated[:d.max_choices]
            candidates = [top, rotated[:1]] if seen % 2 == 0 else [rotated[:1], top]
        else:
            candidates = [(o,) for o in rotated]
    elif d.kind == DISCARD_ENERGY:
        top = options[:d.max_choices]
        candidates = [[top, options[:1], options[:2]][(seen + i) % 3] for i in range(3)]
    else:
        candidates = [options[:d.max_choices] if d.min_choices else options[:min(1, d.max_choices)], ()]
    for choices in candidates:
        command = ResolveDecision(d.player, d.id, tuple(choices))
        if d.min_choices <= len(choices) <= d.max_choices and _v052_accepted(state, command):
            counts[f"{label}_{len(choices)}"] += 1
            return command
    counts[f"{label}_no_accepted_answer"] += 1
    return None


def _v115_mow_transparency(state, command) -> bool:
    """v0.115（TS1）: 使うワザ（相手のワザとして使うものも）がなぎたおすで、おたがいの控えの並び（相手 → 自分）の最後でないところに、はたらいている「とうめい」のポケモンがいる。"""
    if "DamageThenCoinPerBothBenches" not in _attack_and_copied_types(state, command):
        return False
    targets = list(state.players[1 - command.player].bench) + list(state.players[command.player].bench)
    return any(evasion_power(state, p) is not None for p in targets[:-1])


def _v115_mill_short(state, command) -> bool:
    """v0.115（HC6）: やまくだき（相手のワザとして使うものも）を、相手の山札が、使うポケモンの「闘」の基本エネルギーカードの枚数（コインの枚数）より少ないときに宣言した（「おもて」の数に
    よってはトラッシュする枚数が足りない）。道具が数える（エンジンの問い合わせを読まない）。"""
    if "CoinsPerOwnEnergyCardsDamageThenMillOpponent" not in _attack_and_copied_types(state, command):
        return False
    attacker = _attacker(state, command)
    fighting = sum(1 for uid in attacker.energy if state.card_def(uid).is_basic_energy and state.card_def(uid).provides is EnergyType.FIGHTING)
    return len(state.players[1 - command.player].deck) < fighting


def _v115_bench_void(state, command) -> bool:
    """v0.115（v0.4b の問い）: 控えへのダメージだけを決めるコイン（びっくりサンダー・がんせきくだき・なぎたおす）を、受ける控えポケモンがどれもダメージを受けない（見えない壁・こおりのはしら・
    ［ニュートラルシールド］など）ときに宣言した。道具は相手の控えがいて、どれかが守られていることだけを確かめる（止まったときに場があり得ることの確かめ）。"""
    names = _attack_and_copied_types(state, command)
    if not names & {"DamageThenChainedCoinsBenchDamage", "DamageThenCoinsAllocateToBench", "DamageThenCoinPerBothBenches"}:
        return False
    return bool(state.players[1 - command.player].bench) or bool(state.players[command.player].bench)


V115_TYRANITAR_LINE = ("neo2-034", "neo2-036", "neo2-042")  # ヨーギラス → サナギラス → バンギラス（悪）
V115_DARK_CAPABLE = ("neo1-094", "NIP2X-010", "PRN-002")  # 悪エネルギー 3 種（なぎたおすの「悪」を払えるカード。第4弾のレインボーエネルギーは「悪」を出さない）


def _v115_energy(state, command, tried, counts):
    """v0.115: なぎたおす（悪悪無無）のため、バンギラス（neo2-042）を持つプレイヤーは、この番に手札からまだエネルギーカードをつけておらず、手札に悪エネルギーが
    あれば、元の手順のかわりに、その系統（ヨーギラス neo2-034 → サナギラス → バンギラス）で、まだ 2 枚ついていないポケモンにつける（進化する前からためる。進化の進んだポケモンから、
    同じ段階なら控え → バトル場）。
    バンギラス（neo2-042）のカードを持たないプレイヤー（前の版のデッキ）では何もしない。受け付けない場面はつけず ``v115_attach_rejected_<コード>`` に数える。"""
    if state.phase is not Phase.MAIN or state.energy_attachments_this_turn or ("v115_energy", state.turn_number) in tried:
        return None
    if not isinstance(command, (AttachEnergy, UseAttack, EndTurn)):
        return None
    player = state.current_player
    if not any(card.card_id == "neo2-042" and card.owner == player for card in state.cards.values()):
        return None
    p = state.players[player]
    dark = [u for u in p.hand if state.cards[u].card_id in V115_DARK_CAPABLE]
    if not dark:
        return None
    tried.add(("v115_energy", state.turn_number))
    line = [pk for pk in p.in_play() if not state.is_face_down(pk) and state.cards[current_form(state, pk).card].card_id in V115_TYRANITAR_LINE]
    # 進化の進んだポケモンから（同じ段階なら、きぜつしにくい控え → バトル場）。1 匹に 2 枚ためる
    line.sort(key=lambda pk: (-V115_TYRANITAR_LINE.index(state.cards[current_form(state, pk).card].card_id), pk is p.active))
    for pk in line:
        if sum(1 for u in pk.energy if state.cards[u].card_id in V115_DARK_CAPABLE) >= 2:
            continue
        try:
            apply_command(_V052_REAL.get("state") if _V052_REAL.get("state") is not None and _V052_REAL["state"].turn_number == state.turn_number
                          and _V052_REAL["state"].decision == state.decision else state, AttachEnergy(player, dark[0], pk.card))
        except (IllegalActionError, UnsupportedError) as error:
            counts[f"v115_attach_rejected_{error.code}"] += 1
            continue
        counts[f"v115_attach_dark_{'active' if pk is p.active else 'bench'}"] += 1
        return AttachEnergy(player, dark[0], pk.card)
    return None


V0_115_STOPS = {
    # SLD1: いしなだれ（相手のワザとして使うものも）を、相手に控えがいないときに宣言した（選べるのが目安のダメージを受けた相手の対戦ポケモンだけ）
    "UNRESOLVED_CHOSEN_ACTIVE_EXTRA_DAMAGE": lambda st, c: "DamageThenChosenOpponentPokemonDamage" in _attack_and_copied_types(st, c)
    and not st.players[1 - c.player].bench,
}


def v115_uses(state):
    """v0.115: ログから数えた 13 枚・22 のワザの動き（v0.115 のカードのない局では空）。

    - ``attack_<id>#<位置>``（宣言したワザ。カード自身の使用）・``copied_<id>#<位置>``（ほかのワザが相手のワザとして使った v0.115 のワザ）・``<名前>_interrupted``・``esp_redo``
    - しょうげきは・ばくれつしんか: ``<名前>_heads``・``<名前>_tails``・``shock_wave_switched``・``shock_wave_switch_skipped_<理由>``・``explosive_evolution_evolved``・
      ``explosive_evolution_none``・``explosive_evolution_shuffled``
    - びっくりサンダー: ``surprise_thunder_chain_<T|HT|HH>``・``surprise_thunder_no_bench``・``surprise_thunder_bench_damage_<量>``
    - すなあらし: ``sandstorm_<受けるポケモンの種類>``・``sandstorm_receivers_<数>``・``sandstorm_self``（使い手が受けた）
    - なぎたおす: ``mow_down_targets_<数>``・``mow_down_heads_<数>``・``mow_down_opponent_bench_damage``・``mow_down_own_bench_damage``・``mow_down_dark_df_<own|opponent>``（受ける側の
      ［DARK df］で減らした）・``mow_down_both_benches``（おたがいの控えがいた）
    - サイコスプラッシュ: ``psycho_splash_receivers_<数>``・``psycho_splash_cards_<枚数>``（受けたポケモンごとの枚数）
    - やまくだき: ``mountain_smash_coins_<数>``・``mountain_smash_heads_<数>``・``mountain_smash_milled_<枚数>``・``mountain_smash_prevented_milled``（ダメージは無効でトラッシュした）
    - ぶんなげる: ``hurl_with_bench``・``hurl_without_bench``。ちていいどう: ``earth_move_targets_<数>``・``earth_move_locked``
    - 配分: ``<名前>_units_<数>``・``<名前>_concentrated``（1 匹に集めた）・``<名前>_spread``（2 匹以上に分けた）・``rock_blast_discarded_<枚数>``・``rock_blast_active``（相手の対戦ポケモンに配った）・
      ``rock_blast_repeated``（同じポケモンに 2 単位以上）
    - いしなだれ: ``rock_slide_bench``。そのほか: ``bench_guard``・``evade_check``・``damage_prevented_<効果>``（これらのワザの中）"""
    counts = Counter()
    if not any(state.cards[uid].card_id in V0_115 for uid in state.cards):
        return counts
    window = None

    def close(w):
        if w is None or w.get("closed"):
            return
        w["closed"] = True
        name = w["name"]
        coins = w["coins"]
        if w["interrupted"]:
            counts[f"{name}_interrupted"] += 1
            return
        if name in ("shock_wave", "explosive_evolution") and coins:
            counts[f"{name}_{coins[0]}"] += 1
        if name == "surprise_thunder":
            if coins:
                counts["surprise_thunder_chain_" + "".join("H" if side == "heads" else "T" for side in coins)] += 1
            else:
                counts["surprise_thunder_no_bench"] += 1
        if name == "sandstorm":
            counts[f"sandstorm_receivers_{len(w['receivers'])}"] += 1
        if name == "mow_down" and w["targets"] is not None:
            counts[f"mow_down_targets_{len(w['targets'])}"] += 1
            counts[f"mow_down_heads_{sum(1 for side in w['faces'] if side == 'heads')}"] += 1
            if set(w["owners"]) == {0, 1}:
                counts["mow_down_both_benches"] += 1
        if name == "psycho_splash":
            counts[f"psycho_splash_receivers_{len(w['receivers'])}"] += 1
        if name == "mountain_smash":
            counts[f"mountain_smash_coins_{len(coins)}"] += 1
            counts[f"mountain_smash_heads_{sum(1 for side in coins if side == 'heads')}"] += 1
            counts[f"mountain_smash_milled_{w['milled']}"] += 1
            if w["milled"] and w["prevented"]:
                counts["mountain_smash_prevented_milled"] += 1
        if name == "earth_move":
            counts[f"earth_move_targets_{len(w['receivers'])}"] += 1
        for allocation in w["allocations"]:
            counts[f"{name}_units_{allocation['units']}"] += 1
            used = [c for c in allocation["counts"] if c]
            counts[f"{name}_{'concentrated' if len(used) == 1 else 'spread'}"] += 1
            if name == "rock_blast" and any(c > 1 for c in allocation["counts"]):
                counts["rock_blast_repeated"] += 1
        if name == "rock_blast":
            counts[f"rock_blast_discarded_{w['discarded']}"] += 1
            if w["active_allocated"]:
                counts["rock_blast_active"] += 1

    for e in state.log:
        kind = e["kind"]
        if kind in ("attack", "turn_end", "game_end", "halted"):
            close(window)
            window = None
        if kind == "attack":
            current = e.get("card_id") or state.cards[e["pokemon"]].card_id
            key = f"{current}#{e['attack_index']}"
            name = _v115_name(state, key)
            if name is not None:
                counts[f"attack_{key}"] += 1
                window = {"key": key, "name": name, "coins": [], "receivers": [], "targets": None, "faces": (), "owners": (), "milled": 0, "prevented": False,
                          "allocations": [], "discarded": 0, "active_allocated": False, "interrupted": False, "player": e["player"], "pokemon_id": e.get("pokemon_id")}
            continue
        if kind == "copy_attack":
            name = _v115_name(state, e["copied"])
            if name is not None:
                counts[f"copied_{e['copied']}"] += 1
                window = {"key": e["copied"], "name": name, "coins": [], "receivers": [], "targets": None, "faces": (), "owners": (), "milled": 0, "prevented": False,
                          "allocations": [], "discarded": 0, "active_allocated": False, "interrupted": False, "player": e["player"], "pokemon_id": e.get("pokemon_id")}
            else:
                window = None
            continue
        if window is None:
            continue
        name = window["name"]
        effect = str(e.get("effect", ""))
        if kind == "confusion_damage" or (kind == "attack_failed" and e.get("reason") in ("attack_check", "confusion", "baby_rule")):
            window["interrupted"] = True
        elif kind == "coin_flip" and e.get("source") == "attack" and effect == window["key"]:
            window["coins"].append(e["result"])
        elif kind == "esp_redo" and effect == window["key"]:
            counts["esp_redo"] += 1
            first, last = len(e["original"]), len(e["redone"])
            del window["coins"][-(first + last):-last]
        elif kind == "damage" and effect in (window["key"], "") and not e.get("retaliation"):
            target = e.get("target", "opponent_active")
            window["receivers"].append(e.get("pokemon_id"))
            if name == "sandstorm":
                counts[f"sandstorm_{target}"] += 1
            if name == "surprise_thunder" and target == "opponent_bench":
                counts[f"surprise_thunder_bench_damage_{e['steps'][0][1] if e.get('steps') else None}"] += 1
            if name == "mow_down" and target in ("opponent_bench", "self_bench"):
                counts[f"mow_down_{'own' if target == 'self_bench' else 'opponent'}_bench_damage"] += 1
                if any(source is not None and state.cards[source].card_id == "neo2-025" for _step, source, _amount in e.get("modifiers", ())):
                    counts[f"mow_down_dark_df_{'own' if target == 'self_bench' else 'opponent'}"] += 1
            if name == "psycho_splash" and e.get("steps"):
                counts[f"psycho_splash_cards_{e['steps'][0][1] // 10}"] += 1
            if name == "hurl" and target == "opponent_active":
                counts["hurl_with_bench" if e.get("steps") and e["steps"][0][1] == 30 else "hurl_without_bench"] += 1
            if name == "rock_slide" and target == "opponent_bench":
                counts["rock_slide_bench"] += 1
        elif kind == "damage_prevented" and effect == window["key"]:
            window["prevented"] = True
            counts[f"damage_prevented_{e.get('persistent_effect')}"] += 1
        elif kind == "pokemon_coin_results" and effect == window["key"]:
            window["targets"], window["faces"], window["owners"] = tuple(e["targets"]), tuple(e["results"]), tuple(e.get("owners", ()))
        elif kind == "chained_coin_results" and effect == window["key"]:
            window["coins"] = list(e["results"])  # 続けて投げたまとまりの最後の並び（ESPのあとはやり直した並び）
        elif kind == "discard_from_deck" and effect == window["key"] and e["player"] != window["player"]:
            window["milled"] += len(e["cards"])
        elif kind == "forced_switch" and effect == window["key"]:
            counts["shock_wave_switched"] += 1
        elif kind == "forced_switch_skipped" and effect == window["key"]:
            counts[f"shock_wave_switch_skipped_{e.get('reason')}"] += 1
        elif kind == "evolve" and effect == window["key"]:
            counts["explosive_evolution_evolved"] += 1
        elif kind == "evolve_from_deck_none" and effect == window["key"]:
            counts["explosive_evolution_none"] += 1
        elif kind == "shuffle" and name == "explosive_evolution":
            counts["explosive_evolution_shuffled"] += 1
        elif kind == "persistent_effect_added" and name == "earth_move" and e.get("persistent_effect") == "cannot_attack_next_own_turn":
            counts["earth_move_locked"] += 1
        elif kind == "damage_allocated" and effect == window["key"]:
            window["allocations"].append(e)
            if name == "rock_blast" and e["counts"] and e["counts"][0]:
                window["active_allocated"] = True  # 配る先の並びの最初は相手の対戦ポケモン（バトル場 → ベンチ）
        elif kind == "discard_energy" and name == "rock_blast" and effect == window["key"]:
            window["discarded"] += 1
        elif kind == "bench_guard":
            counts["bench_guard"] += 1
        elif kind == "evade_check":
            counts["evade_check"] += 1
    close(window)
    return counts


# ---------------------------------------------------------------- v0.116（docs/energy-movement-attachment-devolution-v0.116.md 9 章）: エネルギーの付け替え・ついた時の効果・付属カードの回収と退化

V116_NAMES = {
    "はねる": "splash", "ふえる": "multiply", "バトンタッチ": "baton_pass", "はらだいこ": "belly_drum", "みずでっぽう": "water_gun", "エナジーサイクル": "energy_cycle",
    "ちょうねんりき": "super_psy", "しこみどく": "poison_seed", "クロスアタック": "cross_attack", "げんしのしずく": "primal_drop", "やみのしょくしゅ": "dark_tentacle",
    "よびもどす": "call_back", "とりかこむ": "surround", "さいせい": "regenerate", "ようかい": "dissolve", "エナジーさいせい": "energy_recycle", "エナジーショック": "energy_shock",
    "ツイスター": "twister", "そらをとぶ": "fly", "エナジーコントロール": "energy_control", "テレキネシス": "telekinesis", "サイコパニック": "psychic_panic",
    "トランスダメージ": "trans_damage",
}
# エネルギーカードがついたログ（つけたカードの項目）。ついた時に発動する持続効果がはたらいたときに、どの入口でついたかを数える（``v116_uses``）
V116_ATTACH_EVENTS = {"attach_energy": ("energy", "energy2"), "attach_energy_from_deck": ("card",), "attach_energy_from_discard": ("cards",),
                      "attach_energy_from_hand": ("cards",), "power_attach_from_deck": ("card",), "power_attach_from_discard": ("cards",),
                      "attack_attach_energy": ("energy",), "move_opponent_energy": ("energy",), "power_attach_energy": ("energy",)}
V116_ONE_COIN = ("energy_cycle", "primal_drop", "surround", "twister", "fly", "energy_control", "dissolve")  # コイン 1 枚のワザ（「おもて」「うら」を数える）


def _v116_name(state, key: str | None) -> str | None:
    """v0.116: ワザ ``key``（"カード id#位置"）が v0.116 のワザなら、その集計の名前（ほかは None）。"""
    if key is None:
        return None
    card_id, index = key.split("#")
    return V116_NAMES.get(state.definitions[card_id].attacks[int(index)].name_ja) if card_id in V0_116 else None


def _v116_decision(state, counts):
    """v0.116 のワザの決定への答え（元の手順より先に答える。処理しているワザが v0.116 のワザでなければ何もしない）。選べるものを決定のたびに 1 つずつずらして選び（選ぶ控え・はがす
    カード・つけるポケモン・退化させるポケモン・ベンチに出すカード・手札に加えるカードが偏らない）、原典で決められない選択（``unresolved_choices``。バトンタッチの FD1・VS1、
    エナジーコントロールの RB3、げんしのしずくの DV5・NB2）は選ばない。決まった枚数の決定（はらだいこの 2 枚）は、ずらした並びの前からその枚数。受け付ける答えだけを選ぶ。"""
    d = state.decision
    if d is None or d.resume != "attack" or d.player != state.current_player:
        return None
    use = d.context_value("use")
    copied = d.context_value("copied")
    key = f"{copied[0]}#{copied[1]}" if copied else (f"{use[2]}#{use[3]}" if use is not None else None)
    name = _v116_name(state, key)
    if name is None:
        return None
    blocked = set(d.context_value("unresolved_choices") or ())
    options = tuple(o for o in d.options if o not in blocked)
    label = f"v116_{name}_{d.kind}"
    seen = counts[label]
    counts[label] += 1
    shift = seen % len(options) if options else 0
    rotated = options[shift:] + options[:shift]
    candidates = [tuple(rotated[:d.min_choices])] if d.min_choices > 1 else []
    candidates += [(o,) for o in rotated] + [()]
    for choices in candidates:
        command = ResolveDecision(d.player, d.id, tuple(choices))
        if d.min_choices <= len(choices) <= d.max_choices and _v052_accepted(state, command):
            counts[f"{label}_{len(choices)}"] += 1
            return command
    counts[f"{label}_no_accepted_answer"] += 1
    return None


def _v116_belly_drum_short(state, command) -> bool:
    """v0.116（FC1）: はらだいこ（相手のワザとして使うものも）を、自分の山札の基本エネルギーカードが 1 枚（2 枚に足りない・0 枚ではない）のときに宣言した。道具が山札を数える
    （エンジンの問い合わせを読まない。のせるダメージカウンターで HP 以上になるなら山札を見ないので止まらない）。"""
    if "SelfCountersThenAttachBasicEnergyFromDeck" not in _attack_and_copied_types(state, command):
        return False
    return sum(1 for uid in state.players[command.player].deck if state.card_def(uid).is_basic_energy) == 1


def _v116_primal_drop_stopped(state, command) -> bool:
    """v0.116（NB2・DV5）: げんしのしずく（相手のワザとして使うものも）を、相手の場の進化ポケモン（重なりのあるポケモン）がどれも、ベイビィから進化したたねポケモン（いちばん上が
    進化カードでない）か「ばける」のポケモンのときに宣言した（「おもて」で選べる候補がどれも止まる）。"""
    if "CoinDevolveOpponentEvolvedToDeck" not in _attack_and_copied_types(state, command):
        return False
    candidates = [p for p in state.players[1 - command.player].in_play() if p.evolution_stack]
    return bool(candidates) and all(devolution_forbidden(state, p) or not state.card_def(p.card).is_evolution_pokemon for p in candidates)


def _v116_regenerate_disguised(state, command) -> bool:
    """v0.116（DV5）: さいせい（相手のワザとして使うものも）を、「ばける」でカードをのせた自分が使う。"""
    return "HealAllThenRegressToBasic" in _attack_and_copied_types(state, command) and devolution_forbidden(state, _attacker(state, command))


def _v116_trigger_holder(state, command=None) -> bool:
    """v0.116: 今の番にはたらく、ついた時に発動するワザの持続効果（しこみどく・エナジーショック）を受けているポケモンが場にいる（AT1・反応の順番の未対応の停止を場から確かめる）。"""
    return any(E.attach_status_triggers(state, p) for pl in state.players for p in pl.in_play())


V0_116_STOPS = {
    # AT1: しこみどく・エナジーショックの効果がはたらいているポケモンへの、場のエネルギーのつけ替え・［エネエネ］（場から確かめる）
    "UNRESOLVED_ATTACH_TRIGGER_SCOPE": _v116_trigger_holder,
    # 手札からつける通常の操作・あまごいでない入口で、効果を受けたポケモンにつき、マヒの持続効果と［ほのおでかいふく］が同じ時点にはたらく（エンジンの未対応）
    "UNSUPPORTED_ATTACH_TRIGGER_ORDER": _v116_trigger_holder,
}


def v116_uses(state):
    """v0.116: ログから数えた 13 枚・25 のワザの動き（v0.116 のカードのない局では空）。

    - ``attack_<id>#<位置>``（宣言したワザ）・``copied_<id>#<位置>``（ほかのワザが相手のワザとして使った v0.116 のワザ）・``attack_failed_<理由>``・``<名前>_<heads|tails>``（コイン 1 枚の
      ワザ）・``esp_redo``
    - ついた時の持続効果（しこみどく・エナジーショック）: ``attach_status_given_<特殊状態>``・``attach_status_triggered_<特殊状態>``・``attach_status_route_<ついたログ>``・
      ``attach_status_after_<直前のログ>``（同じ時点のほかの反応との順番）・``attach_status_second_in_turn``（同じ番・同じポケモンの 2 度目）・``attach_status_removed_<理由>``
    - やみのしょくしゅ: ``evolution_lock_given``・``evolution_lock_removed_<理由>``・``evolution_while_locked_<attack|power>``（効果がはたらく番の、効果を受けたポケモンの進化。
      ワザ・特殊能力の効果の進化だけのはず。``<hand|trainer>`` が出たら誤り）
    - バトンタッチ: ``baton_pass_moved_<枚数>``・``baton_pass_switched``・``baton_pass_<no_target|effect_target_knocked_out>``・``baton_pass_evaded``
    - はらだいこ: ``belly_drum_attached_<枚数>``・``belly_drum_none_<理由>``・``belly_drum_knocked_out``。ふえる: ``multiply_benched``
    - エナジーサイクル・エナジーコントロール: ``<名前>_moved_<attached|evaded>``・``energy_cycle_special``（特殊エネルギーカード）・``energy_control_same_pokemon``・
      ``energy_control_other_pokemon``
    - げんしのしずく: ``primal_drop_devolved``・``primal_drop_none``。さいせい: ``regenerate_healed``・``regenerate_devolved_<枚数>``・``regenerate_energy_<枚数>``
    - よびもどす: ``call_back_benched``・``call_back_baby``・``call_back_none``・``call_back_knocked_out``（のせたカウンターで HP 以上）。とりかこむ: ``surround_sleep``・
      ``surround_retreat_lock``
    - ツイスター: ``twister_returned``・``twister_energy_<枚数>``・``twister_trainers_<枚数>``・``twister_other_owner``（持ち主が受けたポケモンの持ち主でないカード）。
      エナジーさいせい: ``energy_recycle_recovered``。そらをとぶ: ``fly_barrier``
    - クロスアタック: ``cross_attack_heads_<数>``・``cross_attack_confused``。トランスダメージ: ``trans_damage_discarded_<枚数>``・``trans_damage_counters_<数>``"""
    counts = Counter()
    if not any(state.cards[uid].card_id in V0_116 for uid in state.cards):
        return counts
    window = None
    triggered: Counter = Counter()
    locked: dict[int, int] = {}  # やみのしょくしゅの効果を受けたポケモンの番号 → 効果がはたらく番
    route: dict[int, str] = {}  # ついたカード → ついたログ
    previous = None

    def close(w):
        if w is None or w.get("closed"):
            return
        w["closed"] = True
        name = w["name"]
        if name in V116_ONE_COIN and w["coins"]:
            counts[f"{name}_{w['coins'][0]}"] += 1
        if name == "cross_attack" and w["coins"]:
            counts[f"cross_attack_heads_{sum(1 for side in w['coins'] if side == 'heads')}"] += 1
        if name == "baton_pass" and w["switched"]:
            counts[f"baton_pass_moved_{w['moved']}"] += 1
        if name == "belly_drum" and w["attached"]:
            counts[f"belly_drum_attached_{w['attached']}"] += 1
        if name == "regenerate" and w["healed"] is not None:
            counts[f"regenerate_energy_{w['discarded']}"] += 1
        if name == "trans_damage" and w["discarded"]:
            counts[f"trans_damage_discarded_{w['discarded']}"] += 1

    for e in state.log:
        kind = e["kind"]
        effect = str(e.get("effect", ""))
        for field in V116_ATTACH_EVENTS.get(kind, ()):
            value = e.get(field)
            for uid in (value if isinstance(value, (tuple, list)) else (value,)):
                if uid is not None:
                    route[uid] = kind
        if kind == "persistent_effect_added" and e.get("persistent_effect") == "status_on_energy_attach":
            counts[f"attach_status_given_{e.get('condition')}"] += 1
        elif kind == "persistent_effect_removed" and e.get("persistent_effect") == "status_on_energy_attach":
            counts[f"attach_status_removed_{e.get('reason')}"] += 1
        elif kind == "attach_status_triggered":
            counts[f"attach_status_triggered_{e['condition']}"] += 1
            counts[f"attach_status_route_{route.get(e['energy'], 'unknown')}"] += 1
            counts[f"attach_status_after_{previous}"] += 1
            counts[f"attach_status_card_{state.cards[e['energy']].card_id}"] += 1  # ついたカード（なんでもなおし配合エネルギーなら、同じ時点の反応の順番）
            triggered[(e["turn"], e["pokemon_id"])] += 1
            if triggered[(e["turn"], e["pokemon_id"])] == 2:
                counts["attach_status_second_in_turn"] += 1
        elif kind == "persistent_effect_added" and e.get("persistent_effect") == "evolution_lock":
            counts["evolution_lock_given"] += 1
            locked[e["pokemon_id"]] = e["active_turn"]
        elif kind == "persistent_effect_removed" and e.get("persistent_effect") == "evolution_lock":
            counts[f"evolution_lock_removed_{e.get('reason')}"] += 1
            locked.pop(e["pokemon_id"], None)
        elif kind == "evolve" and locked.get(e.get("pokemon_id")) == e["turn"]:
            way = "attack" if e.get("effect") else "power" if e.get("power") else "trainer" if e.get("trainer_card") else "hand"
            counts[f"evolution_while_locked_{way}"] += 1
        previous = kind
        if kind in ("attack", "turn_end", "game_end", "halted"):
            close(window)
            window = None
        if kind == "attack":
            current = e.get("card_id") or state.cards[e["pokemon"]].card_id
            key = f"{current}#{e['attack_index']}"
            name = _v116_name(state, key)
            if name is not None:
                counts[f"attack_{key}"] += 1
                window = {"key": key, "name": name, "coins": [], "moved": 0, "switched": False, "attached": 0, "healed": None, "discarded": 0, "player": e["player"]}
            continue
        if kind == "copy_attack":
            close(window)
            name = _v116_name(state, e["copied"])
            window = None
            if name is not None:
                counts[f"copied_{e['copied']}"] += 1
                window = {"key": e["copied"], "name": name, "coins": [], "moved": 0, "switched": False, "attached": 0, "healed": None, "discarded": 0,
                          "player": e["player"]}
            continue
        if window is None or effect != window["key"]:
            continue
        name = window["name"]
        if kind == "coin_flip" and e.get("source") == "attack":
            window["coins"].append(e["result"])
        elif kind == "esp_redo":
            counts["esp_redo"] += 1
            first, last = len(e["original"]), len(e["redone"])
            del window["coins"][-(first + last):-last]
        elif kind == "attack_failed":
            counts[f"attack_failed_{e.get('reason')}"] += 1
        elif kind == "attack_attach_energy" and name == "baton_pass":
            window["moved"] += 1
        elif kind == "switch" and name == "baton_pass":
            window["switched"] = True
            counts["baton_pass_switched"] += 1
        elif kind == "effect_skipped" and e.get("element") == "baton_pass":
            counts[f"baton_pass_{e.get('reason')}"] += 1
        elif kind == "effect_skipped" and e.get("element") == "attach_from_deck":
            counts["belly_drum_knocked_out"] += 1
        elif kind == "discard_energy" and name == "baton_pass" and e.get("reason") == "evaded":
            counts["baton_pass_evaded"] += 1
        elif kind == "attach_energy_from_deck" and name == "belly_drum":
            window["attached"] += 1
        elif kind == "attach_energy_from_deck_none" and name == "belly_drum":
            counts[f"belly_drum_none_{e.get('reason')}"] += 1
        elif kind == "bench_from_deck" and name == "multiply":
            counts["multiply_benched"] += 1
        elif kind == "move_opponent_energy" and name in ("energy_cycle", "energy_control"):
            counts[f"{name}_moved_{e.get('result')}"] += 1
            if name == "energy_cycle" and not state.card_def(e["energy"]).is_basic_energy:
                counts["energy_cycle_special"] += 1
            if name == "energy_control":
                counts["energy_control_same_pokemon" if e["pokemon_id"] == e["to_pokemon_id"] else "energy_control_other_pokemon"] += 1
        elif kind == "devolve" and name == "primal_drop":
            counts["primal_drop_devolved"] += 1
        elif kind == "devolve_none" and name == "primal_drop":
            counts["primal_drop_none"] += 1
        elif kind == "remove_all_damage_counters" and name == "regenerate":
            window["healed"] = e["counters"]
            counts["regenerate_healed"] += 1
        elif kind == "devolve" and name == "regenerate":
            counts[f"regenerate_devolved_{len(e['removed'])}"] += 1
        elif kind == "discard_energy" and name in ("regenerate", "trans_damage"):
            window["discarded"] += 1
        elif kind == "bench_from_discard" and name == "call_back":
            counts["call_back_benched"] += 1
            if state.card_def(e["card"]).is_baby_pokemon:
                counts["call_back_baby"] += 1
            if e.get("damage", 0) >= state.card_def(e["card"]).hp:
                counts["call_back_knocked_out"] += 1
        elif kind == "bench_from_discard_none" and name == "call_back":
            counts["call_back_none"] += 1
        elif kind == "special_condition" and name in ("cross_attack", "surround"):
            counts["cross_attack_confused" if name == "cross_attack" else "surround_sleep"] += 1
        elif kind == "persistent_effect_added" and name == "surround":
            counts["surround_retreat_lock"] += 1
        elif kind == "persistent_effect_added" and name == "fly":
            counts["fly_barrier"] += 1
        elif kind == "attached_cards_to_hand" and name == "twister":
            counts["twister_returned"] += 1
            counts[f"twister_energy_{len(e['energy'])}"] += 1
            counts[f"twister_trainers_{len(e['trainers'])}"] += 1
            if any(owner != e["player"] for owner in e["owners"]):
                counts["twister_other_owner"] += 1
        elif kind == "recover_energy" and name == "energy_recycle":
            counts["energy_recycle_recovered"] += 1
        elif kind == "place_damage_counters" and name == "trans_damage":
            counts[f"trans_damage_counters_{e['counters']}"] += 1
    close(window)
    return counts


def v114_uses(state):
    """v0.114: ログから数えたベイビィポケモンのルール・進化・13 枚のワザ・特殊能力の動き（v0.114 のカードのない局では空）。

    - ``attack_<id>#<位置>``（宣言したベイビィのワザ）・``copied_<id>#<位置>``（ほかのワザが相手のワザとして使ったベイビィのワザ）・``power_<id>``（宣言した特殊能力）
    - ベイビィポケモンのルール: ``baby_rule_coin``・``baby_rule_heads``・``baby_rule_tails``・``baby_rule_failed``（「うら」でワザの失敗）・``baby_rule_defender_<id>``（コインのもとのベイビィ）
    - 場に出す・進化: ``setup_baby_active``・``setup_baby_bench``（対戦準備）・``bench_baby``（手札からベンチ）・``evolve_baby_<進化前>_<進化後>``・``devolve_to_baby``（退化でベイビィにもどる）
    - モクモク: ``smokescreen_field_suppression``（期限 + 2）。パチパチ: ``pachipachi_damage_<受けるポケモンの種類>``。サイコキッス: ``psychic_kiss_heads``・``psychic_kiss_returned``
    - いっしょにあそぼ: ``play_together_benched``・``play_together_none``・``play_together_failed_bench_full``。なげキッス: ``blow_kiss_counters_<active|bench>``
    - ［わんぱくパンチ］: ``bratty_punch_heads``・``bratty_punch_tails``・``bratty_punch_knock_out``。［じっとみる］: ``stare_added``・``stare_removed_<理由>``"""
    counts = Counter()
    babies = {"neo1-022", "neo1-042", "neo1-044", "neo1-070", "neo2-033", "neo2-050", "neo3-031", "PF2-007", "NIP1X-002", "NIP2X-002", "PRN-012", "PRN-031", "PRN-037"}
    if not any(state.cards[uid].card_id in babies for uid in state.cards):
        return counts

    def cid(uid):
        return state.cards[uid].card_id if uid in state.cards else None

    for e in state.log:
        kind = e["kind"]
        effect = str(e.get("effect", ""))
        if kind == "attack" and cid(e["pokemon"]) in babies:
            counts[f"attack_{cid(e['pokemon'])}#{e['attack_index']}"] += 1
        elif kind == "copy_attack" and effect.split("#")[0] in babies:
            counts[f"copied_{effect}"] += 1
        elif kind == "pokemon_power" and cid(e["pokemon"]) in babies:
            counts[f"power_{cid(e['pokemon'])}"] += 1
        elif kind == "baby_rule_coin":
            counts["baby_rule_coin"] += 1
            counts["baby_rule_heads" if e["heads"] else "baby_rule_tails"] += 1
            counts[f"baby_rule_defender_{cid(e['baby'])}"] += 1
        elif kind == "attack_failed" and e.get("reason") == "baby_rule":
            counts["baby_rule_failed"] += 1
        elif kind == "attack_failed" and e.get("reason") == "bench_full" and effect.startswith("PF2-007"):
            counts["play_together_failed_bench_full"] += 1
        elif kind == "place_starting_pokemon":
            counts["setup_baby_active"] += int(cid(e.get("active")) in babies)
            counts["setup_baby_bench"] += sum(1 for uid in e.get("bench", ()) if cid(uid) in babies)
        elif kind == "play_to_bench" and cid(e.get("card")) in babies:
            counts["bench_baby"] += 1
        elif kind == "evolve" and e.get("from_card_id") in babies:
            counts[f"evolve_baby_{e['from_card_id']}_{e['to_card_id']}"] += 1
        elif kind == "devolve" and e.get("to_card_id") in babies:
            counts["devolve_to_baby"] += 1
        elif kind == "trainer_effect_added" and e.get("card_id") == "neo1-022":
            counts["smokescreen_field_suppression"] += 1
        elif kind == "damage" and effect.startswith("neo1-042"):
            counts[f"pachipachi_damage_{e.get('target', 'opponent_active')}"] += 1
        elif kind == "coin_flip" and e.get("source") == "attack" and effect.startswith("neo3-031") and e.get("result") == "heads":
            counts["psychic_kiss_heads"] += 1
        elif kind == "attached_energy_to_deck":
            counts["psychic_kiss_returned"] += 1
        elif kind == "bench_from_deck" and effect.startswith("PF2-007"):
            counts["play_together_benched"] += 1
        elif kind == "bench_from_deck_none" and effect.startswith("PF2-007"):
            counts["play_together_none"] += 1
        elif kind == "place_damage_counters" and effect.startswith("PRN-037"):
            counts["blow_kiss_counters"] += 1
        elif kind == "coin_flip" and e.get("source") == "power" and effect.startswith("neo1-044"):
            counts["bratty_punch_" + e["result"]] += 1
        elif kind == "power_damage" and str(e.get("power", "")).startswith("neo1-044") and e.get("knocked_out"):
            counts["bratty_punch_knock_out"] += 1
        elif kind == "persistent_effect_added" and e.get("persistent_effect") == "bench_powers_stopped":
            counts["stare_added"] += 1
        elif kind == "persistent_effect_removed" and e.get("persistent_effect") == "bench_powers_stopped":
            counts[f"stare_removed_{e.get('reason')}"] += 1
    return counts


# ---------------------------------------------------------------- v0.117（docs/retreat-return-active-powers-v0.117.md 10 章）: 場の移動・にげる時の反応・条件付きの特殊能力

V117_NAMES = {
    "メガホーン": "megahorn", "もちさる": "take_away", "しっぽビンタ": "tail_slap", "おうふくビンタ": "double_slap", "サイキックダメージ": "psychic_damage",
    "いかく": "intimidate", "うしろなげ": "back_throw", "めざめるパワー": "hidden_power", "したでなめる": "lick", "ぱっときえる": "vanish",
    "でんこうせっか": "quick_attack", "おいうち": "pursuit", "ライトニングスパーク": "lightning_spark", "メガフレイム": "mega_flame",
    "クリスタルウェーブ": "crystal_wave", "つつく": "peck",
}


def _v117_name(state, key: str | None) -> str | None:
    """v0.117: ワザ ``key``（"カード id#位置"）が v0.117 のワザなら、その集計の名前（ほかは None）。"""
    if key is None:
        return None
    card_id, index = key.split("#")
    return V117_NAMES.get(state.definitions[card_id].attacks[int(index)].name_ja) if card_id in V0_117 else None


def _v117_decision(state, counts):
    """v0.117 のワザの決定への答え（元の手順より先に答える。処理しているワザが v0.117 のワザでなければ何もしない）。``_v116_decision`` と同じく、選べるものを決定のたびに
    1 つずつずらして選び、原典で決められない選択（``unresolved_choices``）は選ばない。決まった枚数の決定（メガフレイムの「うら」2 枚ぶんのトラッシュ）は、ずらした並びの前から
    その枚数（元の手順は 1 枚を選んで拒否された。v0.117 の正式な対戦の 1 回目の L117 対 G61 の seed 1）。受け付ける答えだけを選ぶ。"""
    d = state.decision
    if d is None or d.resume != "attack" or d.player != state.current_player:
        return None
    use = d.context_value("use")
    copied = d.context_value("copied")
    key = f"{copied[0]}#{copied[1]}" if copied else (f"{use[2]}#{use[3]}" if use is not None else None)
    name = _v117_name(state, key)
    if name is None:
        return None
    blocked = set(d.context_value("unresolved_choices") or ())
    options = tuple(o for o in d.options if o not in blocked)
    label = f"v117_{name}_{d.kind}"
    seen = counts[label]
    counts[label] += 1
    shift = seen % len(options) if options else 0
    rotated = options[shift:] + options[:shift]
    candidates = [tuple(rotated[:d.min_choices])] if d.min_choices > 1 else []
    candidates += [(o,) for o in rotated] + [()]
    for choices in candidates:
        command = ResolveDecision(d.player, d.id, tuple(choices))
        if d.min_choices <= len(choices) <= d.max_choices and _v052_accepted(state, command):
            counts[f"{label}_{len(choices)}"] += 1
            return command
    counts[f"{label}_no_accepted_answer"] += 1
    return None


def _v117_step(state, tried, counts):
    """v0.117: アンノーンQ の［QUICKEN］を、自分の番ごとに場のアンノーンQ のどれか 1 匹で、受け付けるなら使う（この番にほかの個体が使っていれば使わない。v0.117 のカードのない局では
    何もしない）。"""
    player = state.current_player
    for pokemon in state.players[player].in_play():
        if state.is_face_down(pokemon) or state.cards[pokemon.card].card_id != "neo4-059":
            continue
        marker = ("v117_quicken", pokemon.pokemon_id, state.turn_number)
        if marker in tried:
            continue
        tried.add(marker)
        use = UsePokemonPower(player, pokemon.pokemon_id, 0)
        if _v052_accepted(state, use):
            counts["v117_quicken_declared"] += 1
            return use
        counts["v117_quicken_not_usable"] += 1
    return None


def _v117_retreat(state, tried, counts):
    """v0.117: 相手のバトル場に［CHASE］のアンノーンC がいる・自分のバトル場のポケモンがおいうちの効果を受けているとき、「にげる」を宣言する（同じ番に 1 度。1 局にプレイヤーごと 4 回まで）。
    にげるエネルギーの数のぶん、ついている順にトラッシュする。ねむり・マヒ・「にげる」ことができない効果・エネルギーが足りないときはしない。決まらない場面（RR1）・扱えない処理で
    止まれば、道具が場から確かめる（tests/v017_games.py の ``v117_stop_expected``）。どちらもないなら何もしないので、前の版の組の結果は変わらない。"""
    player = state.current_player
    p = state.players[player]
    active = p.active
    if not p.bench or active is None or active.conditions.asleep or active.conditions.paralyzed or cannot_retreat(state, active) is not None:
        return None
    if state.card_def(active.card).play_role is not None or "retreat" in tried or ("v117_retreat", state.turn_number) in tried:
        return None
    chase = E.retreat_chase_holders(state, player)
    pursuit = retreat_pursuits(state, active)
    if not (chase or pursuit) or counts[f"v117_retreat_{player}"] >= 4:
        return None
    cost = retreat_cost(state, player)
    if cost.floor_ambiguous(cost.maximum) or len(active.energy) < cost.maximum:
        return None
    tried.add(("v117_retreat", state.turn_number))
    counts[f"v117_retreat_{player}"] += 1
    counts["v117_retreat_" + "_".join(name for name, on in (("chase", chase), ("pursuit", pursuit)) if on)] += 1
    return Retreat(player, tuple(active.energy[:cost.maximum]), p.bench[0].card)


def v117_uses(state):
    """v0.117: ログから数えた 13 枚・18 のワザ・8 の特殊能力の動き（v0.117 のカードのない局では空）。

    - ``attack_<id>#<位置>``（宣言したワザ）・``<名前>_<heads|tails>``（ワザのコイン）
    - ［CHASE］: ``chase_<heads|tails>``・``chase_counters``・``chase_skipped``。おいうち: ``pursuit_given``・``pursuit_damage_<量>``・``pursuit_knocked_out``・``pursuit_skipped``・
      ``pursuit_prevented``・``pursuit_removed_<理由>``（にげる以外で消えた・期限）。同じ時点の反応の順番の決定: ``retreat_reaction_order``
    - ［ときわたり］: ``time_travel_<heads|tails>``。［QUICKEN］: ``quicken_used``・``quicken_heads``・``quicken_prevented_<damage|effect>``
    - ［でんせつのからだ］: ``legend_body_discard_<枚数>``・``trainer_effect_blocked``
    - もちさる: ``take_away_returned``・``take_away_recovered``・``take_away_no_discard``。ぱっときえる: ``vanish_returned``。メガフレイム: ``mega_flame_discarded_<枚数>``・
      ``mega_flame_none``。いかく: ``intimidate_locked``・``intimidate_not_basic``。サイキックダメージ: ``psychic_damage_counters_<数>``
    - ［きしかいせい］: ``desperation_set``（ダメージの記録の変更効果に 2 段階の 120）。［かえるのうた］: ``frog_song_bonus``"""
    counts = Counter()
    if not any(state.cards[uid].card_id in V0_117 for uid in state.cards):
        return counts
    card = {uid: c.card_id for uid, c in state.cards.items()}
    current = None
    for e in state.log:
        kind = e["kind"]
        effect = str(e.get("effect") or "")
        power = str(e.get("power") or "")
        if kind == "attack":
            key = f"{card.get(e.get('pokemon'))}#{e.get('attack_index')}" if e.get("attack_index") is not None else None
            current = _v117_name(state, key) if key is not None and card.get(e.get("pokemon")) in V0_117 else None
            if current is not None:
                counts[f"attack_{key}"] += 1
        elif kind == "turn_end":
            current = None
        elif kind == "coin_flip" and e.get("source") == "attack" and current is not None:
            counts[f"{current}_{e['result']}"] += 1
        if kind == "chase_check":
            counts[f"chase_{e['result']}"] += 1
        elif kind in ("chase_counters", "chase_skipped", "pursuit_skipped", "pursuit_prevented", "trainer_effect_blocked"):
            counts[kind] += 1
        elif kind == "persistent_effect_added" and e.get("persistent_effect") == "pursuit_on_retreat":
            counts["pursuit_given"] += 1
        elif kind == "persistent_effect_removed" and e.get("persistent_effect") == "pursuit_on_retreat":
            counts[f"pursuit_removed_{e.get('reason')}"] += 1
        elif kind == "pursuit_damage":
            counts[f"pursuit_damage_{e['amount']}"] += 1
            if e.get("knocked_out"):
                counts["pursuit_knocked_out"] += 1
        elif kind == "time_travel":
            counts[f"time_travel_{e['result']}"] += 1
        elif kind == "trainer_effect_added" and e.get("effect_kind") == "quicken_used":
            counts["quicken_used"] += 1
        elif kind == "trainer_effect_added" and e.get("effect_kind") == "group_attack_immunity":
            counts["quicken_heads"] += 1
        elif kind in ("damage_prevented", "effect_prevented") and e.get("persistent_effect") == "group_attack_immunity":
            counts[f"quicken_prevented_{'damage' if kind == 'damage_prevented' else 'effect'}"] += 1
        elif kind == "legend_body_discard":
            counts[f"legend_body_discard_{len(e.get('cards', ()))}"] += 1
        elif kind == "return_in_play_to_deck" and effect.startswith("neo1-067#0"):
            counts["take_away_returned"] += 1
        elif kind == "attack_discard_to_deck" and effect.startswith("neo1-067#0"):
            counts["take_away_recovered"] += 1
        elif kind == "return_in_play_to_hand" and effect.startswith("GD6-005#1"):
            counts["vanish_returned"] += 1
        elif kind == "discard_energy" and effect.startswith("PF3-005#0"):
            counts["mega_flame_discarded_card"] += 1
        elif kind == "discard_energy_failed" and effect.startswith("PF3-005#0"):
            counts["mega_flame_none"] += 1
        elif kind == "persistent_effect_added" and effect.startswith("neo3-049#0"):
            counts["intimidate_locked"] += 1
        elif kind == "place_damage_counters" and effect.startswith("neo3-036#0"):
            counts[f"psychic_damage_counters_{e.get('counters')}"] += 1
        elif kind == "damage" and any(m[0] == 2 for m in e.get("modifiers", ())):
            sources = {card.get(m[1]) for m in e.get("modifiers", ()) if m[0] == 2}
            if "neo1-017" in sources:
                counts["desperation_set"] += 1
            if "neo2-019" in sources:
                counts["frog_song_bonus"] += 1
        elif kind == "decision" and e.get("decision_kind") == "reaction_order":
            counts["retreat_reaction_order"] += 1
        if power.startswith(("PF3-004", "PF3-005", "PF3-006")) and kind == "legend_body_discard":
            counts["legend_body_discard"] += 1
    return counts


# ---------------------------------------------------------------- v0.118（docs/unbounded-coins-heal-allocation-v0.118.md 11 章）: 上限なしコイン・攻撃時の能力・回復の配分

V118_NAMES = {
    "スミでっぽう": "ink_shot", "しめつづける": "constrict", "トリプルずつき": "triple_headbutt", "わるわるMAX": "dark_max", "めざめるパワー": "hidden_power",
    "まるまるアタック": "rolling_attack", "ふしぎなかおり": "wonder_aroma", "はっぱカッター": "razor_leaf", "ごくらくかふん": "bliss_pollen",
    "さいあくかふん": "worst_pollen", "ひっかく": "scratch", "まるもうけ": "windfall", "マッハひこう": "mach_flight", "エアロウイング": "aero_wing",
}
V118_X, V118_PORYGON2, V118_DRAGONITE = "neo4-065", "neo4-097", "PR1-043"


def _v118_name(state, key: str | None) -> str | None:
    """v0.118: ワザ ``key``（"カード id#位置"）が v0.118 のワザなら、その集計の名前（ほかは None）。"""
    if key is None:
        return None
    card_id, index = key.split("#")
    return V118_NAMES.get(state.definitions[card_id].attacks[int(index)].name_ja) if card_id in V0_118 else None


def _v118_decision(state, counts):
    """v0.118 のワザの決定への答え（元の手順より先に答える。処理しているワザが v0.118 のワザでなければ何もしない）。ふしぎなかおりの配分は、「おもて」を出したプレイヤーがそれぞれ答える
    （相手プレイヤーの決定にも答える）。選べるものを決定のたびに 1 つずつずらして選び、原典で決められない選択（``unresolved_choices``。HZ1 の 0 個の組・先読みで問いに当たった組）は
    選ばない。のぞむならのコイン（エアロウイング）は、局の中で投げる・投げないを交互に答える（最初は投げる）。受け付ける答えだけを選ぶ。"""
    d = state.decision
    if d is None or d.resume != "attack":
        return None
    use = d.context_value("use")
    copied = d.context_value("copied")
    key = f"{copied[0]}#{copied[1]}" if copied else (f"{use[2]}#{use[3]}" if use is not None else None)
    name = _v118_name(state, key)
    if name is None:
        return None
    blocked = set(d.context_value("unresolved_choices") or ())
    options = tuple(o for o in d.options if o not in blocked)
    label = f"v118_{name}_{d.kind}"
    seen = counts[label]
    counts[label] += 1
    if blocked:
        counts[f"{label}_blocked_{d.context_value('unresolved_code')}"] += 1
    shift = seen % len(options) if options else 0
    rotated = options[shift:] + options[:shift]
    candidates = [(o,) for o in rotated] + [()]
    if d.min_choices == 0 and seen % 2 == 1:
        candidates = [()] + [(o,) for o in rotated]
    for choices in candidates:
        command = ResolveDecision(d.player, d.id, tuple(choices))
        if d.min_choices <= len(choices) <= d.max_choices and _v052_accepted(state, command):
            counts[f"{label}_{len(choices)}"] += 1
            return command
    counts[f"{label}_no_accepted_answer"] += 1
    return None


def _v118_power_decision(state, counts):
    """v0.118 の特殊能力の決定への答え: ［じくうへんかん］のトラッシュのスタジアムカード・［トランスポート］の山札の上に置く手札（選べるものを決定のたびに 1 つずつずらす）。"""
    d = state.decision
    if d is None or d.resume != "power":
        return None
    use = d.context_value("use")
    if use is None or use[2] not in (V118_PORYGON2, V118_DRAGONITE):
        return None
    label = f"v118_{use[2]}_{d.kind}"
    seen = counts[label]
    counts[label] += 1
    rotated = list(d.options[seen % len(d.options):]) + list(d.options[:seen % len(d.options)]) if d.options else []
    for choice in rotated:
        command = ResolveDecision(d.player, d.id, (choice,))
        if _v052_accepted(state, command):
            counts[f"{label}_answered"] += 1
            return command
    counts[f"{label}_no_accepted_answer"] += 1
    return None


def _v118_step(state, tried, counts):
    """v0.118: ［トランスポート］（カイリュー）・［じくうへんかん］（わるいポリゴン2）を、自分の番ごとに 1 匹につき 1 回、受け付けるなら使う。［じくうへんかん］は自分のトラッシュに
    スタジアムカードがあるときだけ試す（ないときは SX1 で止まる。使う前に場から確かめるのは手順で、エンジンの問い合わせではない）。v0.118 のカードのない局では何もしない。"""
    player = state.current_player
    p = state.players[player]
    for pokemon in p.in_play():
        if state.is_face_down(pokemon):
            continue
        card_id = state.cards[pokemon.card].card_id
        if card_id not in (V118_PORYGON2, V118_DRAGONITE):
            continue
        marker = ("v118_power", pokemon.pokemon_id, state.turn_number)
        if marker in tried:
            continue
        tried.add(marker)
        name = "time_shift" if card_id == V118_PORYGON2 else "transport"
        if card_id == V118_PORYGON2 and not any("stadium" in state.card_def(uid).trainer_kinds for uid in p.discard):
            counts["v118_time_shift_no_stadium"] += 1
            continue
        use = UsePokemonPower(player, pokemon.pokemon_id, 0)
        if _v052_accepted(state, use):
            counts[f"v118_{name}_declared"] += 1
            return use
        counts[f"v118_{name}_not_usable"] += 1
    return None


def _v118_attack(state, command, tried, counts):
    """v0.118: 自分の場の「アンノーン」が「めざめるパワー」を使うとき、場のアンノーンX の［XXXXX］をいっしょに使う（受け付けるなら）。宣言ごとに、使わない → ベンチのX → ワザを使う
    X 自身の順に回す（いなければ次）。ほかのコマンドはそのまま。"""
    if not isinstance(command, UseAttack) or command.attack_power or command.card is not None or command.with_power is not None:
        return command
    active = state.players[command.player].active
    if active is None or state.is_face_down(active):
        return command
    form = state.card_def(current_form(state, active).card)
    attacks = form.attacks
    if form.name_group != "アンノーン" or not (0 <= command.attack_index < len(attacks)) or attacks[command.attack_index].name_ja != "めざめるパワー":
        return command
    holders = [pk for pk in state.players[command.player].in_play() if not state.is_face_down(pk) and state.cards[pk.card].card_id == V118_X]
    if not holders:
        return command  # 場にアンノーンX がいなければ何もしない（前の版の組の手順・集計は変わらない）
    bench = [pk for pk in holders if pk is not active]
    seen = counts["v118_x_seen"]
    counts["v118_x_seen"] += 1
    order = (None, bench[0] if bench else None, active if active in holders else None)  # 位置 0 は使わない
    for position in ((seen + i) % 3 for i in range(3)):
        holder = order[position]
        if position == 0:
            counts["v118_x_not_used"] += 1
            return command
        if holder is None:
            continue
        with_power = dataclasses.replace(command, with_power=holder.pokemon_id)
        if _v052_accepted(state, with_power):
            counts["v118_x_used_" + ("self" if holder is active else "bench")] += 1
            return with_power
        counts["v118_x_not_accepted"] += 1
    return command


def v118_uses(state):
    """v0.118: ログから数えた 9 枚・14 のワザ・3 つの特殊能力の動き（v0.118 のカードのない局では空）。

    - ``attack_<id>#<位置>``（宣言したワザ）・``<名前>_<heads|tails>``（ワザのコイン）
    - まるもうけ: ``windfall_drew_<枚数>``・``windfall_short``（「おもて」の数より山札が少なかった）。［XXXXX］: ``x_power_<self|bench>``・``x_power_heads_<数>``（「おもて」の数）
    - ふしぎなかおり・ごくらくかふん: ``heal_<own|opponent>_<個数>``（1 つのワザの中で、そのプレイヤーがとりのぞいた合計）・``heal_two_targets``（2 匹以上から）・
      ``heal_prevented``（受けない）。しめつづける: ``retreat_cost_given``・``retreat_paid_more``（効果がはたらく番に、増えた数で「にげる」）
    - エアロウイング: ``aero_<chosen|declined>``。［トランスポート］: ``transport_used``・``transport_drawn_<枚数>``。［じくうへんかん］: ``time_shift_<heads|tails>``・
      ``time_shift_placed``・``time_shift_replaced``（前のスタジアムをトラッシュした）・``time_shift_narrow``（せまいジムの場に出た時の決定）"""
    counts = Counter()
    if not any(state.cards[uid].card_id in V0_118 for uid in state.cards):
        return counts
    card = {uid: c.card_id for uid, c in state.cards.items()}
    current = None
    healed: Counter = Counter()
    heal_targets: dict = {}
    power = None
    attacker_player = windfall_heads = 0

    def close():
        for (player, side), total in healed.items():
            counts[f"heal_{side}_{total}"] += 1
            if len(heal_targets[(player, side)]) >= 2:
                counts["heal_two_targets"] += 1
        healed.clear()
        heal_targets.clear()

    for e in state.log:
        kind = e["kind"]
        if kind in ("attack", "turn_end"):
            close()
        if kind == "attack":
            key = f"{card.get(e.get('pokemon'))}#{e.get('attack_index')}" if e.get("attack_index") is not None else None
            current = _v118_name(state, key) if key is not None and card.get(e.get("pokemon")) in V0_118 else None
            attacker_player = e["player"]
            if current is not None:
                counts[f"attack_{key}"] += 1
        elif kind == "turn_end":
            current = None
        elif kind == "coin_flip" and e.get("source") == "attack" and current is not None:
            counts[f"{current}_{e['result']}"] += 1
        if kind == "pokemon_power":
            power = card.get(e.get("pokemon"))
            if power == V118_DRAGONITE:
                counts["transport_used"] += 1
        elif kind in ("attack", "play_trainer", "attach_energy", "evolve", "retreat", "turn_start", "turn_end"):
            power = None
        if kind == "attack":
            windfall_heads = 0
        elif kind == "coin_flip" and e.get("source") == "attack" and current == "windfall" and e["result"] == "heads":
            windfall_heads += 1
        elif kind == "esp_redo" and current == "windfall":
            windfall_heads = 0  # ナツメのESPのやり直し（最後の結果だけを使う）
        if kind == "draw" and power == V118_DRAGONITE:
            counts[f"transport_drawn_{len(e.get('cards', ()))}"] += 1
            power = None
        elif kind == "draw" and current == "windfall" and e["player"] == attacker_player:
            counts[f"windfall_drew_{len(e.get('cards', ()))}"] += 1
            if windfall_heads > len(e.get("cards", ())):
                counts["windfall_short"] += 1
        elif kind == "coin_flip" and e.get("source") == "power" and power == V118_PORYGON2:
            counts[f"time_shift_{e['result']}"] += 1
        elif kind == "stadium_placed" and e.get("from_zone") == "discard":
            counts["time_shift_placed"] += 1
            if e.get("replaces") is not None:
                counts["time_shift_replaced"] += 1
        elif kind == "decision" and e.get("decision_kind") == "stadium_return_bench" and power == V118_PORYGON2:
            counts["time_shift_narrow"] += 1
        elif kind == "group_attack_power":
            counts["x_power_" + ("self" if e.get("pokemon_id") == e.get("attacker_pokemon_id") else "bench")] += 1
        elif kind == "group_attack_power_coins":
            counts[f"x_power_heads_{e.get('heads')}"] += 1
        elif kind == "attack_heal" and current in ("wonder_aroma", "bliss_pollen"):
            side = "own" if e["player"] == attacker_player else "opponent"
            healed[(e["player"], side)] += e.get("counters", 0)
            heal_targets.setdefault((e["player"], side), set()).add(e.get("pokemon_id"))
        elif kind == "effect_prevented" and current in ("wonder_aroma",):
            counts["heal_prevented"] += 1
        elif kind == "persistent_effect_added" and e.get("persistent_effect") == "retreat_cost_increase":
            counts["retreat_cost_given"] += 1
        elif kind == "retreat" and e.get("retreat_cost_effects"):
            counts["retreat_paid_more"] += 1
        elif kind == "optional_coin_chosen":
            counts["aero_chosen"] += 1
        elif kind == "optional_coin_declined":
            counts["aero_declined"] += 1
    close()
    return counts


# ---------------------------------------------------------------- v0.119（docs/damage-reactions-poison-sleep-v0.119.md 11 章）: 受けるダメージの選択・どくとねむり・場の効果

V119_NAMES = {
    "どくをだす": "secrete_poison", "ねむりバサミ": "sleep_pinchers", "どくどくエキス": "toxic_saliva", "スピードスター": "swift", "はかいのいちげき": "destructive_blow",
    "ひきずりこむ": "pull_in", "トリプルキャノン": "triple_cannon", "ガスばくはつ": "gas_explosion", "なぞのこうせん": "mystery_beam", "かいてんアタック": "spin_attack",
    "いたみわけ": "pain_split", "あやしいひかり": "confuse_ray", "じひびき": "earthquake",
}
V119_MATADOGAS, V119_NIDOKING = "ES3-007", "PR1-068"
V119_COMMANDED = ("サカキのニドラン♂", "サカキのニドリーノ")


def _v119_name(state, key: str | None) -> str | None:
    """v0.119: ワザ ``key``（"カード id#位置"）が v0.119 のワザなら、その集計の名前（ほかは None）。"""
    if key is None:
        return None
    card_id, index = key.split("#")
    return V119_NAMES.get(state.definitions[card_id].attacks[int(index)].name_ja) if card_id in V0_119 else None


def _v119_decision(state, counts):
    """v0.119 の決定への答え（元の手順より先に答える）。［シェルアーマー］を使うか（``damage_option``。受けるポケモンの持ち主。どのワザのダメージでも）は、局の中で使う・使わないを交互に答える
    （最初は使う）。ひきずりこむの任意の入れ替え（ワザを使ったプレイヤー）は、決定のたびに 入れ替えない・控えを順に を回す。受け付ける答えだけを選ぶ（選ぶと止める答えは選ばない）。
    ほかの決定・v0.119 のカードのない局では何もしない。"""
    d = state.decision
    if d is None or d.resume != "attack":
        return None
    if d.kind == "damage_option":
        seen = counts["v119_armor_seen"]
        counts["v119_armor_seen"] += 1
        order = [tuple(d.options), ()] if seen % 2 == 0 else [(), tuple(d.options)]
        for choices in order:
            command = ResolveDecision(d.player, d.id, choices)
            if d.min_choices <= len(choices) <= d.max_choices and _v052_accepted(state, command):
                counts["v119_armor_" + ("used" if choices else "declined")] += 1
                return command
        counts["v119_armor_no_accepted_answer"] += 1
        return None
    use = d.context_value("use")
    copied = d.context_value("copied")
    key = f"{copied[0]}#{copied[1]}" if copied else (f"{use[2]}#{use[3]}" if use is not None else None)
    name = _v119_name(state, key)
    if name is None:
        return None
    blocked = set(d.context_value("unresolved_choices") or ())
    options = tuple(o for o in d.options if o not in blocked)
    label = f"v119_{name}_{d.kind}"
    seen = counts[label]
    counts[label] += 1
    shift = seen % len(options) if options else 0
    rotated = options[shift:] + options[:shift]
    candidates = [(o,) for o in rotated]
    candidates = ([()] + candidates) if seen % 2 == 0 else (candidates + [()])
    for choices in candidates:
        command = ResolveDecision(d.player, d.id, tuple(choices))
        if d.min_choices <= len(choices) <= d.max_choices and _v052_accepted(state, command):
            counts[f"{label}_{len(choices)}"] += 1
            return command
    counts[f"{label}_no_accepted_answer"] += 1
    return None


def _v119_step(state, tried, counts):
    """v0.119: ［ポイズンミスト］（マタドガス）を、自分の番ごとに 1 匹につき 1 回、受け付けるなら使う。v0.119 のカードのない局では何もしない。"""
    player = state.current_player
    for pokemon in state.players[player].in_play():
        if state.is_face_down(pokemon) or state.cards[pokemon.card].card_id != V119_MATADOGAS:
            continue
        marker = ("v119_power", pokemon.pokemon_id, state.turn_number)
        if marker in tried:
            continue
        tried.add(marker)
        use = UsePokemonPower(player, pokemon.pokemon_id, 0)
        if _v052_accepted(state, use):
            counts["v119_poison_mist_declared"] += 1
            return use
        counts["v119_poison_mist_not_usable"] += 1
    return None


def _v119_attack(state, command, tried, counts):
    """v0.119: 自分の場の「サカキのニドラン♂」「サカキのニドリーノ」がワザを使うとき、場のサカキのニドキングの［めいれい］を、自分の番ごとに 使う・使わない を交互に、受け付けるなら
    いっしょに使う。ほかのコマンド・場にサカキのニドキングがいない局はそのまま（前の版の組の手順・集計は変わらない）。"""
    if not isinstance(command, UseAttack) or command.attack_power or command.card is not None or command.with_power is not None:
        return command
    active = state.players[command.player].active
    if active is None or state.is_face_down(active):
        return command
    if state.card_def(current_form(state, active).card).name_ja not in V119_COMMANDED:
        return command
    holders = [pk for pk in state.players[command.player].in_play() if not state.is_face_down(pk) and state.cards[pk.card].card_id == V119_NIDOKING]
    if not holders:
        return command
    counts["v119_command_seen"] += 1
    if (state.turn_number // 2) % 2 == 1:
        # 使う・使わないは、自分の番ごとに交互（同じ番の中で拒否されたワザのかわりのワザも、同じ答え）
        counts["v119_command_not_used"] += 1
        return command
    with_power = dataclasses.replace(command, with_power=holders[0].pokemon_id)
    if _v052_accepted(state, with_power):
        counts["v119_command_used"] += 1
        return with_power
    counts["v119_command_not_accepted"] += 1
    return command


def v119_uses(state):
    """v0.119: ログから数えた 11 枚・13 のワザ・7 つの特殊能力の動き（v0.119 のカードのない局では空）。

    - ``attack_<id>#<位置>``（宣言したワザ）・``<名前>_<heads|tails>``（ワザのコイン）
    - ［シェルアーマー］: ``armor_used``・``armor_declined``（damage_option のログ）。［かたいから］: ``hard_shell_set``（damage_set_if_at_most）。［めいれい］: ``command_used``
    - どく: ``toxic_poisoned``（multiplier 2 のどく）・``poison_damage_<量>``（ポケモンチェックのどくのダメージ）・``poison_mist_added``・``poison_mist_interrupted``・``poison_mist_removed``・
      ``poison_with_mist``（ポケモンチェックのどくに［ポイズンミスト］がかかわった）・``poison_multiplied``（カウンターの数を倍にするどくのダメージ）
    - ねむり: ``sleep_check_<coins>coins_<recovered|asleep>``。ひきずりこむ: ``pull_in_switched``・``pull_in_declined``
    - どくをだす: ``secrete_poison_added``・``secrete_poison``（はたらいた）・``secrete_poison_bench_damage``（控えへのダメージ）・``secrete_poison_skipped``。ガスばくはつ: ``replacement_poison_<pending|knocked|applied|removed>``
    - ［アレルギーほうし］: ``discard_protected_<element|power>``。［いあつ］: ``scare_attack_prevented``（ワザの宣言の拒否は手順が数える）。なぞのこうせん: ``weakness_immunity_added``。
      いたみわけ: ``pain_split_<個数>``"""
    counts = Counter()
    if not any(state.cards[uid].card_id in V0_119 for uid in state.cards):
        return counts
    card = {uid: c.card_id for uid, c in state.cards.items()}
    current = None
    for e in state.log:
        kind = e["kind"]
        if kind == "attack":
            key = f"{card.get(e.get('pokemon'))}#{e.get('attack_index')}" if e.get("attack_index") is not None else None
            current = _v119_name(state, key) if key is not None and card.get(e.get("pokemon")) in V0_119 else None
            if current is not None:
                counts[f"attack_{key}"] += 1
        elif kind == "turn_end":
            current = None
        elif kind == "coin_flip" and e.get("source") == "attack" and current is not None:
            counts[f"{current}_{e['result']}"] += 1
        if kind == "damage" and e.get("damage_option"):
            counts["armor_" + ("used" if e["damage_option"][0][3] else "declined")] += 1
        if kind == "damage" and e.get("damage_set_if_at_most"):
            counts["hard_shell_set"] += 1
        if kind == "damage" and e.get("secrete_poison"):
            counts["secrete_poison_bench_damage"] += 1
        if kind == "group_attack_power" and card.get(e.get("pokemon")) == V119_NIDOKING:
            counts["command_used"] += 1
        if kind == "special_condition" and e.get("condition") == "poison" and e.get("multiplier", 1) != 1:
            counts["toxic_poisoned"] += 1
        if kind == "poison_damage":
            counts[f"poison_damage_{e.get('amount')}"] += 1
            if e.get("poison_mists"):
                counts["poison_with_mist"] += 1
            if e.get("multiplier", 1) != 1:
                counts["poison_multiplied"] += 1
        if kind in ("poison_mist_added", "poison_mist_interrupted", "poison_mist_removed", "secrete_poison", "secrete_poison_skipped"):
            counts[kind] += 1
        if kind == "persistent_effect_added" and e.get("persistent_effect") == "secrete_poison":
            counts["secrete_poison_added"] += 1
        if kind in ("replacement_poison_pending", "replacement_poison_knocked", "replacement_poison_removed"):
            counts[kind] += 1
        if kind == "replacement_poison":
            counts["replacement_poison_applied"] += 1
        if kind == "sleep_check":
            coins = e.get("coins", 1)
            counts[f"sleep_check_{coins}coins_" + ("recovered" if e.get("recovered") else "asleep")] += 1
        if kind == "forced_switch" and current == "pull_in":
            counts["pull_in_switched"] += 1
        if kind == "forced_switch_declined" and current == "pull_in":
            counts["pull_in_declined"] += 1
        if kind == "discard_protected":
            counts["discard_protected_" + (e.get("element") or "power")] += 1
        if kind == "trainer_effect_added" and e.get("effect_kind") == "attack_field_weakness_immunity":
            counts["weakness_immunity_added"] += 1
        if kind == "place_damage_counters" and current == "pain_split":
            counts[f"pain_split_{e.get('counters')}"] += 1
    return counts


# ---------------------------------------------------------------- v0.120（docs/fossil-basic-virtual-attacks-v0.120.md 11 章）: 化石の復活と仮想ワザの供給

V120_NAMES = {
    "おおきくゆびをふる": "super_metronome", "そらをとぶ": "fly", "ちからをあわせる": "work_together", "しめつける": "bind", "しんかのほうし": "evolutionary_spore",
    "ソーラービーム": "solarbeam", "りゅうのいでんし": "genetic_memory", "たつまき": "twister", "マインドショック": "mind_shock", "はたく": "pound",
    "サイコデュープ": "psycho_dupe", "なきつく": "snivel", "ゆびをふる": "metronome", "たたきつける": "slam",
}
V120_REVIVE_HOLDERS = ("neo2-014", "neo2-032")  # ［なかまのふっかつ］・［かせきのふっかつ］
V120_EGG = "neo2-055"
V120_DECISION_KINDS = ("revive_source", "bench_from_deck_or_hand")


def _v120_name(state, key: str | None) -> str | None:
    """v0.120: ワザ ``key``（"カード id#位置"）が v0.120 のワザなら、その集計の名前（ほかは None）。"""
    if key is None:
        return None
    card_id, index = key.split("#")
    return V120_NAMES.get(state.definitions[card_id].attacks[int(index)].name_ja) if card_id in V0_120_POKEMON else None


def _v120_first(state, d, counts, label, *, all_options=False):
    """v0.120: 選ぶと止める選択を除いた選べるものから答える（局の中で順に回す）。``all_options`` なら、止めない選べるものをすべて選ぶ（しんかのほうしの選ぶポケモン）。受け付ける答えだけ。"""
    blocked = set(d.context_value("unresolved_choices") or ()) | set(d.context_value("unsupported_choices") or ()) | set(d.context_value("entry_power_choices") or ())
    options = tuple(o for o in d.options if o not in blocked)
    seen = counts[label]
    counts[label] += 1
    if all_options:
        candidates = [options] if options else []
    else:
        size = max(d.min_choices, 1) if options else 0
        shift = seen % len(options) if options else 0
        rotated = options[shift:] + options[:shift]
        candidates = [tuple(rotated[:size])] if size <= len(rotated) and size > 0 else []
        candidates += [tuple((o,) + tuple(x for x in rotated if x != o)[:size - 1]) for o in rotated[1:]] if size > 0 else []
    if d.min_choices == 0:
        candidates.append(())
    for choices in candidates:
        command = ResolveDecision(d.player, d.id, tuple(choices))
        if d.min_choices <= len(choices) <= d.max_choices and _v052_accepted(state, command):
            counts[f"{label}_{len(choices)}"] += 1
            return command
    counts[f"{label}_no_accepted_answer"] += 1
    return None


def _v120_decision(state, counts):
    """v0.120 の決定への答え（元の手順より先に答える）。v0.120 のカードのない局では何もしない。

    - たまごの化石: 手札から選ぶか山札を見るか（``revive_source``）は、手札から選べるときは 1 回ごとに 手札・山札 を交互に。ベンチに出すカード（``select_evolution_card``・
      ``bench_from_deck_or_hand``）は止めない選べるものから順に
    - ［なかまのふっかつ］・［かせきのふっかつ］のベンチに出すカード（``bench_from_deck``）: 止めない選べるものから順に
    - v0.120 のワザの決定: ワザを選ぶ（ゆびをふる・おおきくゆびをふる・サイコデュープ・りゅうのいでんし）は止めない選べるものから順に。しんかのほうしの選ぶポケモンは止めないものをすべて、
      進化カードは止めないものから順に。たつまきのトラッシュするカードは「おもて」の数を、止めないものから
    """
    d = state.decision
    if d is None or not any(state.cards[uid].card_id in V0_120 for uid in state.cards):
        return None
    if d.resume == "trainer":
        use = d.context_value("use")
        if use is None or use[2] != V120_EGG:
            return None
        if d.kind == "revive_source":
            seen = counts["v120_egg_source_seen"]
            counts["v120_egg_source_seen"] += 1
            order = [(0,), (1,)] if seen % 2 == 0 else [(1,), (0,)]
            for choices in order:
                command = ResolveDecision(d.player, d.id, choices)
                if choices[0] in d.options and _v052_accepted(state, command):
                    counts["v120_egg_source_" + ("hand" if choices == (0,) else "deck")] += 1
                    return command
            counts["v120_egg_source_no_accepted_answer"] += 1
            return None
        return _v120_first(state, d, counts, f"v120_egg_{d.kind}")
    if d.resume == "power":
        use = d.context_value("use")
        if use is None or d.kind != "bench_from_deck" or use[2] not in V120_REVIVE_HOLDERS:
            return None
        return _v120_first(state, d, counts, "v120_revive_bench_from_deck")
    if d.resume != "attack":
        return None
    use = d.context_value("use")
    copied = d.context_value("copied")
    key = f"{copied[0]}#{copied[1]}" if copied else (f"{use[2]}#{use[3]}" if use is not None else None)
    name = _v120_name(state, key)
    if name is None:
        return None
    if name == "evolutionary_spore" and d.kind == "select_pokemon":
        return _v120_first(state, d, counts, "v120_spore_targets", all_options=True)
    return _v120_first(state, d, counts, f"v120_{name}_{d.kind}")


def _v120_step(state, tried, counts):
    """v0.120: ［なかまのふっかつ］・［かせきのふっかつ］を、自分の番ごとに 1 匹につき 1 回、受け付けるなら使う（使えない理由（ベンチに空きがない・特殊状態）は数える）。"""
    player = state.current_player
    for pokemon in state.players[player].in_play():
        if state.is_face_down(pokemon) or state.cards[pokemon.card].card_id not in V120_REVIVE_HOLDERS:
            continue
        marker = ("v120_power", pokemon.pokemon_id, state.turn_number)
        if marker in tried:
            continue
        tried.add(marker)
        use = UsePokemonPower(player, pokemon.pokemon_id, 0)
        if _v052_accepted(state, use):
            counts[f"v120_revive_declared_{state.cards[pokemon.card].card_id}"] += 1
            return use
        counts["v120_revive_not_usable"] += 1
    return _v120_retreat_to_doll(state, tried, counts)


def _v120_retreat_to_doll(state, tried, counts):
    """v0.120: 自分の場に、エネルギーで「マインドショック」を払える［にんぎょうつかい］のスリーパー（ES3-025）と、ベンチのピッピ人形があり、バトル場がピッピ人形でないなら、番ごとに
    1 回、バトル場のポケモンをにがしてピッピ人形を出す（受け付けるときだけ。ついているエネルギーの前から、にげるエネルギーの数だけトラッシュ）。ピッピ人形がバトル場で
    スリーパーのワザを使う（スリーパーが払う）場面を対戦に作る。"""
    player = state.current_player
    p = state.players[player]
    marker = ("v120_doll_retreat", state.turn_number)
    if marker in tried or p.active is None or state.cards[p.active.card].card_id == CLEFAIRY_DOLL:
        return None
    doll = next((b for b in p.bench if state.cards[b.card].card_id == CLEFAIRY_DOLL), None)
    hypnos = [q for q in p.in_play() if state.cards[q.card].card_id == "ES3-025"]
    if doll is None or not any(attack_cost_payable(state, q, state.card_def(q.card).attacks[0]) for q in hypnos):
        return None
    tried.add(marker)
    if state.is_face_down(p.active) or p.active.conditions.asleep or p.active.conditions.paralyzed:
        return None
    try:
        cost = retreat_cost(state, player).maximum
    except UnsupportedError:
        return None  # バトル場がなにかの化石（PF2）
    if len(p.active.energy) < cost:
        return None
    command = Retreat(player, tuple(p.active.energy[:cost]), doll.card)
    if not _v052_accepted(state, command):
        counts["v120_doll_retreat_rejected"] += 1
        return None
    counts["v120_doll_retreat"] += 1
    tried.add(("v047_discard", doll.pokemon_id))  # この番は、v0.47 の手順がバトル場に出したピッピ人形をすてない（スリーパーのワザを使う）
    return command


def _v120_trainer(state, tried, counts):
    """v0.120: 手札のたまごの化石を、1 番に 1 回まで、受け付けるなら使う（ベンチに空きがないなど、使えない理由は数える）。"""
    player = state.current_player
    marker = ("v120_egg", state.turn_number)
    if marker in tried:
        return None
    for uid in state.players[player].hand:
        if state.cards[uid].card_id != V120_EGG:
            continue
        tried.add(marker)
        play = PlayTrainer(player, uid)
        real = _V052_REAL.get("state")
        try:
            apply_command(real if real is not None and real.turn_number == state.turn_number and real.decision == state.decision else state, play)
        except (IllegalActionError, UnsupportedError) as error:
            counts[f"v120_egg_not_playable_{error.code}"] += 1
            return None
        counts["v120_egg_played"] += 1
        return play
    return None



def _v121_attack_key(state, d) -> str | None:
    """v0.121: ワザの途中の決定 ``d`` の、処理しているワザ（"カード id#位置"。写したワザなら写したワザ）。"""
    use = d.context_value("use")
    copied = d.context_value("copied")
    return f"{copied[0]}#{copied[1]}" if copied else (f"{use[2]}#{use[3]}" if use is not None else None)


def _v121_decision(state, counts):
    """v0.121 の決定への答え（元の手順より先に答える）。v0.121 のカードのない局では何もしない。

    - ワザ: ぶきみなとおぼえ・ちょうはつの相手の手札から出すカード（``opponent_hand_to_bench``。選ぶと止める選択を除いて順に。ちょうはつは 1 枚か出さない）、じごくのほのおのトラッシュする
      カード（``discard_energy``）
    - ボロのつりざおの回収するカード（``recover_pokemon``・``recover_trainer``）、カスミのてあての対象（``select_pokemon``。選ぶと止める相手のラプラスは選ばない）・とりのぞく数
      （``select_counter_count``。いちばん多い数）
    """
    d = state.decision
    if d is None or not any(state.cards[uid].card_id in V0_121 for uid in state.cards):
        return None
    if d.resume == "trainer":
        use = d.context_value("use")
        if use is None or use[2] not in V0_121_TRAINERS:
            return None
        if d.kind == "select_counter_count":
            command = ResolveDecision(d.player, d.id, (max(d.options),))
            if _v052_accepted(state, command):
                counts[f"v121_care_counters_{max(d.options)}"] += 1
                return command
            return None
        return _v120_first(state, d, counts, f"v121_{use[2]}_{d.kind}")
    if d.resume != "attack":
        return None
    key = _v121_attack_key(state, d)
    if key is None or key.split("#")[0] not in V0_121_POKEMON:
        return None
    return _v120_first(state, d, counts, f"v121_{key}_{d.kind}")


def _v121_trainer(state, tried, counts):
    """v0.121: 手札のボロのつりざお・カスミのてあてを、それぞれ 1 番に 1 回まで、受け付けるなら使う（使えない理由（OR1・MQ2 など）は数える）。"""
    player = state.current_player
    for card_id in V0_121_TRAINERS:
        marker = ("v121_trainer", card_id, state.turn_number)
        if marker in tried:
            continue
        for uid in state.players[player].hand:
            if state.cards[uid].card_id != card_id:
                continue
            tried.add(marker)
            play = PlayTrainer(player, uid)
            real = _V052_REAL.get("state")
            try:
                apply_command(real if real is not None and real.turn_number == state.turn_number and real.decision == state.decision else state, play)
            except (IllegalActionError, UnsupportedError) as error:
                counts[f"v121_{card_id}_not_playable_{error.code}"] += 1
                break
            counts[f"v121_{card_id}_played"] += 1
            return play
    return None


def v121_uses(state):
    """v0.121: ログから数えた 9 枚・14 のワザ・トレーナー 2 枚の動き（v0.121 のカードのない局では空）。

    - ``attack_<id>#<位置>``（宣言した v0.121 のワザ）・``snore_asleep``・``snore_failed``（おおいびきをねむり状態で使った・起きていて失敗した）・``yawn_both_asleep``
    - ``lock_on_added``・``lock_on_removed_<理由>``・``bolt_waived``（ロックオンで「うら」でも失敗しなかった）・``bolt_failed``・``bolt_hit``
    - ``dark_fire_discarded``・``dark_fire_none``、``frenzy_coins_<枚数>``・``frenzy_heads``、``howl_placed``・``howl_switched``・``howl_none``・``howl_failed``、``provoke_placed_<段>``・
      ``provoke_declined``・``provoke_none``、``old_rod_<HH|TT|HT>``・``old_rod_retrieved``、``care_healed_<数>``・``care_declined``、``growl_<id>``（なきごえの効果を与えた）
    """
    counts = Counter()
    if not any(state.cards[uid].card_id in V0_121 for uid in state.cards):
        return counts
    card = {uid: c.card_id for uid, c in state.cards.items()}
    current = None
    rod_coins: list[str] = []
    for e in state.log:
        kind = e["kind"]
        if kind == "attack":
            pokemon_card = e.get("card", e.get("pokemon"))
            key = f"{card.get(pokemon_card)}#{e.get('attack_index')}" if e.get("attack_index") is not None else None
            current = key if key is not None and card.get(pokemon_card) in V0_121_POKEMON else None
            if current is not None:
                counts[f"attack_{current}"] += 1
        elif kind == "turn_end":
            current = None
        effect = e.get("effect")
        if kind == "attack_failed" and effect == "ES3-021#1" and e.get("reason") == "not_asleep":
            counts["snore_failed"] += 1
        if kind == "damage" and effect == "ES3-021#1":
            counts["snore_asleep"] += 1
        if kind == "special_condition" and effect == "ES3-021#0":
            counts["yawn_status"] += 1
        if kind == "persistent_effect_added" and e.get("persistent_effect") == "next_turn_failure_waiver":
            counts["lock_on_added"] += 1
        if kind == "persistent_effect_removed" and e.get("persistent_effect") == "next_turn_failure_waiver":
            counts[f"lock_on_removed_{e.get('reason')}"] += 1
        if kind == "attack_failure_waived":
            counts["bolt_waived"] += 1
        if effect == "neo2-043#1":
            if kind == "attack_failed":
                counts["bolt_failed"] += 1
            if kind == "damage":
                counts["bolt_hit"] += 1
        if effect == "neo4-229#1":
            if kind == "discard_energy":
                counts["dark_fire_discarded"] += 1
            if kind == "discard_energy_failed":
                counts["dark_fire_none"] += 1
        if kind == "pokemon_coin_results" and effect == "neo4-096#1":
            counts[f"frenzy_coins_{len(e.get('results', ()))}"] += 1
            counts["frenzy_heads"] += sum(1 for r in e.get("results", ()) if r == "heads")
        if effect == "neo4-229#0":
            if kind == "attack_bench_from_hand":
                counts["howl_placed"] += 1
            if kind == "forced_switch":
                counts["howl_switched"] += 1
            if kind == "attack_bench_from_hand_none":
                counts["howl_none"] += 1
            if kind == "attack_failed":
                counts["howl_failed"] += 1
        if effect == "neo4-096#0":
            if kind == "attack_bench_from_hand":
                counts[f"provoke_placed_by_{'attacker' if e.get('chooser') == e.get('attacker') else 'opponent'}"] += 1
            if kind == "attack_bench_from_hand_declined":
                counts["provoke_declined"] += 1
            if kind == "attack_bench_from_hand_none":
                counts["provoke_none"] += 1
        if kind == "persistent_effect_added" and e.get("persistent_effect") == "reduced_damage_to_source_next_turn":
            source = e.get("effect", "")
            if source.split("#")[0] in ("PR1-001", "PR1-003", "PR1-017"):
                counts[f"growl_{source}"] += 1
        if kind == "play_trainer" and card.get(e.get("card")) == V121_OLD_ROD:
            rod_coins = []
        if kind == "coin_flip" and e.get("source") == "trainer" and card.get(e.get("card")) == V121_OLD_ROD:
            rod_coins.append("H" if e["result"] == "heads" else "T")
            if len(rod_coins) == 2:
                counts[f"old_rod_{''.join(sorted(rod_coins))}"] += 1
        if kind == "retrieve_trainer" and card.get(e.get("trainer_card")) == V121_OLD_ROD:
            counts["old_rod_retrieved"] += 1
        if kind == "remove_damage_counters" and card.get(e.get("trainer_card")) == V121_MISTYS_CARE:
            counts[f"care_healed_{e.get('counters')}"] += 1
        if kind == "trainer_take_none" and card.get(e.get("trainer_card")) == V121_MISTYS_CARE:
            counts["care_declined"] += 1
    return counts


def _v122_present(state) -> bool:
    return any(state.cards[uid].card_id in V0_122 for uid in state.cards)


def _v122_unown_aside(state, command, counts):
    """v0.122: ［UNDO］・［WANT］（ベンチにアンノーンU・W 自身と 3 つの文字がそろうときに使える）を持つデッキのプレイヤーは、対戦準備でバトル場に出すたねポケモンと、バトル場に出す
    ベンチのポケモンに、アンノーン（``name_group``）でないポケモンがいればそれを選ぶ（元の手順は手札・ベンチの最初のポケモン。アンノーンがバトル場に出ると、ベンチに文字がそろわない。
    開発用の seed 80〜83 では、どちらも一度も使えなかった）。ベンチは元の手順のまま（バトル場に出すカードを入れかえるだけ）。アンノーンU・W のないデッキのプレイヤー・v0.122 のカードの
    ない局では何もしない（前の版の組と、U122・W122 のない v0.122 の組の結果は変わらない）。"""
    if type(command).__name__ not in ("PlaceStartingPokemon", "PromoteActive"):
        return command
    player = command.player
    if not any(c.owner == player and c.card_id in (V122_U, V122_W) for c in state.cards.values()):
        return command

    def unown(uid):
        return state.card_def(uid).name_group == "アンノーン"

    if type(command).__name__ == "PlaceStartingPokemon":
        if not unown(command.active):
            return command
        others = [uid for uid in state.players[player].hand if state.card_def(uid).is_basic_pokemon and not unown(uid)]
        if not others:
            return command
        counts["v122_setup_unown_aside"] += 1
        return type(command)(player, others[0], tuple(uid for uid in (command.active, *command.bench) if uid != others[0])[:5])
    if not unown(command.pokemon):
        return command
    others = [p.card for p in state.players[player].bench if not unown(p.card)]
    if not others:
        return command
    counts["v122_promote_unown_aside"] += 1
    return type(command)(player, others[0])


def _v122_attack(state, command, tried, counts):
    """v0.122: 自分の場の「アンノーン」が「めざめるパワー」を使うとき、場のアンノーンA の［ANGER］・アンノーンX の［XXXXX］をいっしょに使う（受け付けるなら）。宣言ごとに、両方（``with_powers``）
    → ［ANGER］だけ → ［XXXXX］だけ → 使わない の順を、局の中で回す（いっしょに使えるのが 1 つなら ``with_power``。v0.118 の手順と同じ形）。v0.122 のカードのない局・ほかのコマンドは
    そのまま（前の版の組の手順・集計は変わらない）。"""
    if not isinstance(command, UseAttack) or command.attack_power or command.card is not None or command.with_power is not None or command.with_powers:
        return command
    if not _v122_present(state):
        return command
    active = state.players[command.player].active
    if active is None or state.is_face_down(active):
        return command
    form = state.card_def(current_form(state, active).card)
    attacks = form.attacks
    if form.name_group != "アンノーン" or not (0 <= command.attack_index < len(attacks)) or attacks[command.attack_index].name_ja != "めざめるパワー":
        return command
    own = [pk for pk in state.players[command.player].in_play() if not state.is_face_down(pk)]
    angers = [pk for pk in own if state.cards[pk.card].card_id == V122_A]
    xs = [pk for pk in own if state.cards[pk.card].card_id == V118_X]
    if not angers:
        return command  # アンノーンA がいなければ v0.118 の手順のまま
    seen = counts["v122_anger_seen"]
    counts["v122_anger_seen"] += 1
    plans = []
    if xs:
        plans.append(("both", (angers[0].pokemon_id, xs[0].pokemon_id)))
    plans.append(("anger", (angers[0].pokemon_id,)))
    plans.append(("none", ()))
    for position in ((seen + i) % len(plans) for i in range(len(plans))):
        name, holders = plans[position]
        if not holders:
            counts["v122_anger_not_used"] += 1
            return command
        chosen = dataclasses.replace(command, with_powers=holders) if len(holders) > 1 else dataclasses.replace(command, with_power=holders[0])
        if _v052_accepted(state, chosen):
            counts[f"v122_anger_used_{name}_" + ("self" if angers[0] is active else "bench")] += 1
            return chosen
        counts[f"v122_anger_not_accepted_{name}"] += 1
    return command


def _v122_step(state, tried, counts):
    """v0.122: ［UNDO］・［WANT］・［げんしのゆめ］・［かせきか］・［かせきのみちびき］を、自分の番ごとに 1 匹につき 1 回、受け付けるなら使う（使えない理由は数える）。［UNDO］は、バトル場の
    ポケモンにダメージカウンターがのっているときだけ使う（手札にもどして、もう一度出す）。"""
    if not _v122_present(state):
        return None
    player = state.current_player
    p = state.players[player]
    for pokemon in p.in_play():
        if state.is_face_down(pokemon):
            continue
        card_id = state.cards[pokemon.card].card_id
        if card_id not in V122_POWER_HOLDERS:
            continue
        if card_id == V122_U and (p.active is None or p.active.damage == 0):
            continue
        marker = ("v122_power", pokemon.pokemon_id, state.turn_number)
        if marker in tried:
            continue
        tried.add(marker)
        use = UsePokemonPower(player, pokemon.pokemon_id, 0)
        real = _V052_REAL.get("state")
        try:
            apply_command(real if real is not None and real.turn_number == state.turn_number and real.decision == state.decision else state, use)
        except (IllegalActionError, UnsupportedError) as error:
            counts[f"v122_{card_id}_not_usable_{error.code}"] += 1
            continue
        counts[f"v122_{card_id}_declared"] += 1
        return use
    return None


def _v122_retreat(state, tried, counts):
    """v0.122: バトル場がわるいフシギソウ（［つるでひっぱる］）で、相手に控えがいて、この番にまだはたらいていないとき、「にげる」を宣言する（同じ番に 1 度。1 局にプレイヤーごと 4 回まで）。
    にげるエネルギーの数のぶん、ついている順にトラッシュする。ねむり・マヒ・「にげる」ことができない効果・エネルギーが足りないときはしない。決まらない場面（VL1）で止まれば、道具が
    場から確かめる。わるいフシギソウがいなければ何もしないので、前の版の組の結果は変わらない。"""
    player = state.current_player
    p = state.players[player]
    active = p.active
    if not p.bench or active is None or state.is_face_down(active) or state.cards[active.card].card_id != V122_IVYSAUR:
        return None
    if active.conditions.asleep or active.conditions.paralyzed or cannot_retreat(state, active) is not None or not state.players[1 - player].bench:
        return None
    if "retreat" in tried or ("v122_retreat", state.turn_number) in tried or counts[f"v122_retreat_{player}"] >= 4:
        return None
    if not E.retreat_vine_pulls(state, player, active):
        return None
    cost = retreat_cost(state, player)
    if cost.floor_ambiguous(cost.maximum) or len(active.energy) < cost.maximum:
        return None
    tried.add(("v122_retreat", state.turn_number))
    command = Retreat(player, tuple(active.energy[:cost.maximum]), p.bench[0].card)
    if not _v052_accepted(state, command):
        counts["v122_retreat_not_accepted"] += 1
        return None
    counts[f"v122_retreat_{player}"] += 1
    counts["v122_retreat_vine_pull"] += 1
    return command


def _v122_decision(state, counts):
    """v0.122 の決定への答え（元の手順より先に答える）。v0.122 のカードのない局では何もしない。

    - ［WANT］・［かせきのみちびき］の回収するカード（``recover_trainer``）・［かせきか］の選ぶポケモン（``select_pokemon``。選ぶと止める FE3 などは選ばない）
    - ［つるでひっぱる］の相手プレイヤーが選ぶ控え（再開先 ``reaction`` の ``select_pokemon``）
    - みだれうちの相手プレイヤーが選ぶ配分（``allocate_damage``）・10まんボルトなどのワザの決定
    """
    d = state.decision
    if d is None or not _v122_present(state):
        return None
    if d.resume == "power":
        use = d.context_value("use")
        if use is None or use[2] not in V0_122_POKEMON:
            return None
        return _v120_first(state, d, counts, f"v122_{use[2]}_{d.kind}")
    if d.resume == "reaction":
        item = d.context_value("reaction")
        if not isinstance(item, tuple) or not item or item[0] != "vine":
            return None
        return _v120_first(state, d, counts, "v122_vine_pull_select")
    if d.resume != "attack":
        return None
    key = _v121_attack_key(state, d)
    if key is None or key.split("#")[0] not in V0_122_POKEMON:
        return None
    return _v120_first(state, d, counts, f"v122_{key}_{d.kind}")


def _v126_trainer(state, tried, counts):
    """v0.126: 手札のフラッシュを、この番にまだ試していなければ使う（両方の山札が 5 枚以上のときだけ。5 枚より少ないときの FU1 は単体のテストで確かめる）。"""
    player = state.current_player
    if any(len(p.deck) < 5 for p in state.players) or state.trainer_in_use is not None:
        return None
    for card in state.players[player].hand:
        if state.cards[card].card_id != V126_FLASH:
            continue
        key = ("v126_flash", state.turn_number)
        if key in tried:
            return None
        tried.add(key)
        counts["v126_flash_played"] += 1
        return PlayTrainer(player, card)
    return None


def _v126_decision(state, counts):
    """v0.126: フラッシュの並べかえ（決めるのは並べる本人。見た 5 枚の並べかえを、そのまま・逆・1 つずらし・カードの id の順で順に答える）と、おもての山札のある間の 1 枚を選ぶ決定で、
    自分の山札の 2 枚目より下のおもてのカードを避ける（選ぶと FU3。選べるものから黙って除かれてはいないので、手順が避ける）。どちらでもなければ何もしない。"""
    d = state.decision
    used = state.trainer_in_use
    if d.kind == ARRANGE_DECK_TOP and used is not None and state.cards[used.card].card_id == V126_FLASH:
        seen = counts["v126_arrange_seen"]
        counts["v126_arrange_seen"] += 1
        options = list(d.options)
        orders = (options, list(reversed(options)), options[1:] + options[:1], sorted(options, key=lambda uid: (state.cards[uid].card_id, uid)))
        chosen = tuple(orders[seen % len(orders)])
        counts[f"v126_arrange_{('same', 'reversed', 'rotated', 'by_id')[seen % len(orders)]}"] += 1
        return ResolveDecision(d.player, d.id, chosen)
    if not state.face_up_deck or d.max_choices != 1:
        return None
    deck = state.players[d.player].deck
    hidden_face_up = {uid for uid in deck[1:] if uid in state.face_up_deck}
    if not hidden_face_up & set(d.options):
        return None
    allowed = [o for o in d.options if o not in hidden_face_up and o not in set(d.context_value("unresolved_choices", ()) or ())]
    counts["v126_avoided_face_up_choice"] += 1
    if allowed:
        return ResolveDecision(d.player, d.id, (allowed[0],))
    return ResolveDecision(d.player, d.id, ()) if d.min_choices == 0 else None


def _v126_attack(state, command, counts):
    """v0.126: サカキのニャース（PMCG6-068）がバトル場にいて、相手の山札のいちばん上がおもて（観測の ``face_up_top``。CR-FLASH-TOP-CARD-SEEN）なら、その種類でワザを選ぶ: トレーナーカード
    ならてつだうふり（トラッシュさせる）、そうでなければダブルひっかき。見る情報は使うプレイヤーの観測だけ（エンジンの状態の山札を読まない）。どちらでもなければ元の手順のまま。"""
    from kyuura_engine.observation import observe

    if not isinstance(command, UseAttack):
        return None
    active = state.players[command.player].active
    if active is None or state.cards[active.card].card_id != GIOVANNIS_MEOWTH_40:
        return None
    top = observe(state, command.player)["players"][1 - command.player]["deck"].get("face_up_top")
    if top is None:
        return None
    wanted = 0 if state.definitions[top["card_id"]].category == "trainer" else 1
    counts[f"v126_meowth_seen_top_{'trainer' if wanted == 0 else 'other'}"] += 1
    if wanted == command.attack_index:
        return None
    try:
        apply_command(state, UseAttack(command.player, wanted))  # 使えるか（エネルギー・止める理由）を、状態を変えずに確かめる
    except (IllegalActionError, UnsupportedError):
        counts[f"v126_meowth_kept_{command.attack_index}"] += 1
        return None
    counts[f"v126_meowth_chose_{wanted}"] += 1
    return UseAttack(command.player, wanted)


def _v127_water(state, pokemon) -> int:
    return len(E.attached_typed_energy_cards(state, pokemon, EnergyType.WATER))


def _v127_attack(state, command, counts):
    """v0.127: バトル場のファイヤーは、相手の場に「水」エネルギーカードがあればドライアップ（ワザ 0）を選び、なければほのおのつばさ（ワザ 1。使えなければ番を終える）。ハマちゃんのヤドキングは、相手の対戦ポケモンが
    こんらん状態でなければこまったなあ（ワザ 0。利用者の簡略ルールで発話の条件はない）、こんらんならどつく（ワザ 1）。使えるか（エネルギー・止める理由）は状態を変えずに確かめ、使えなければ
    元の手順のまま（途中停止になる結果も「使える」に数える。拒否ではない）。どちらのカードでもなければ何もしない。"""
    if not isinstance(command, (UseAttack, EndTurn)):
        return None
    player = state.current_player
    active = state.players[player].active
    if active is None:
        return None
    card_id = state.cards[active.card].card_id
    opponent = state.players[1 - player]
    if card_id in V127_MOLTRES:
        wanted = 0 if any(_v127_water(state, p) for p in opponent.in_play()) else 1
    elif card_id == V127_SLOWKING:
        wanted = 1 if opponent.active is not None and opponent.active.conditions.confused else 0
    else:
        return None
    if isinstance(command, UseAttack) and command.attack_index == wanted:
        return None
    try:
        apply_command(state, UseAttack(player, wanted))
    except (IllegalActionError, UnsupportedError):
        if card_id in V127_MOLTRES and wanted == 1 and isinstance(command, UseAttack) and command.attack_index == 0:
            counts[f"v127_{card_id}_no_water_end_turn"] += 1  # 「水」エネルギーカードのない相手にドライアップを使わない（ほのおのつばさを使えなければ番を終える）
            return EndTurn(player)
        counts[f"v127_{card_id}_kept"] += 1
        return None
    counts[f"v127_{card_id}_chose_{wanted}"] += 1
    return UseAttack(player, wanted)


def _v127_trainer(state, command, tried, counts):
    """v0.127: 手札の怪電波マシーンを、相手の対戦ポケモンにエネルギーカードが 2 枚以上あるか、ワザを使えずに番を終えるとき（この番にまだ試していなければ）使う（番が終わるので、ワザの
    かわりに使う）。相手の対戦ポケモンにエネルギーカードがないときは使わない（TW2 は単体のテストで確かめる）。"""
    player = state.current_player
    if state.trainer_in_use is not None:
        return None
    target = state.players[1 - player].active
    energy = 0 if target is None else len([uid for uid in target.energy if state.card_def(uid).category == "energy"])
    if energy == 0 or not (energy >= 2 or isinstance(command, EndTurn)):
        return None
    for card in state.players[player].hand:
        if state.cards[card].card_id != V127_TWM:
            continue
        key = ("v127_twm", state.turn_number)
        if key in tried:
            return None
        tried.add(key)
        counts["v127_twm_played"] += 1
        return PlayTrainer(player, card)
    return None


def _v127_decision(state, counts):
    """v0.127: ドライアップの選ぶポケモン（相手の場で「水」エネルギーカードのいちばん多いポケモン。選ぶと止めるポケモンは選ばない）と、トラッシュ・手札にもどすカード（はじめの「おもて」の数の
    枚数）。どちらでもなければ何もしない。"""
    from kyuura_engine import decisions as D

    d = state.decision
    used = state.trainer_in_use
    if d.resume == "trainer" and used is not None and state.cards[used.card].card_id == V127_TWM and d.kind == D.RETURN_ENERGY:
        counts["v127_twm_decision"] += 1
        return ResolveDecision(d.player, d.id, tuple(d.options[:d.min_choices]))
    attacker = state.players[d.player].active if d.player == state.current_player else None
    if d.resume != "attack" or attacker is None or state.cards[attacker.card].card_id not in V127_MOLTRES:
        return None
    if d.kind == D.SELECT_POKEMON:
        blocked = set(d.context_value("unresolved_choices", ()) or ())
        options = [pid for pid in d.options if pid not in blocked]
        if not options:
            return None
        best = max(options, key=lambda pid: (_v127_water(state, state.find_pokemon(pid)[1]), -options.index(pid)))
        counts[f"v127_dry_up_target_water_{_v127_water(state, state.find_pokemon(best)[1])}"] += 1
        return ResolveDecision(d.player, d.id, (best,))
    if d.kind == D.DISCARD_OPPONENT_ENERGY:
        counts["v127_dry_up_decision"] += 1
        return ResolveDecision(d.player, d.id, tuple(d.options[:d.min_choices]))
    return None


def _v129_trainer(state, tried, counts):
    """v0.129: 手札のカツラのクイズ その1を、ワザか番の終わりの前に使う（1 つの番に 1 回。使う前に止まるなら、その番は試さない）。"""
    player = state.current_player
    if state.trainer_in_use is not None:
        return None
    for card in state.players[player].hand:
        if state.cards[card].card_id != V129_QUIZ:
            continue
        key = ("v129_quiz", state.turn_number)
        if key in tried:
            return None
        tried.add(key)
        command = PlayTrainer(player, card)
        if not _v052_accepted(state, command):
            counts["v129_quiz_not_played"] += 1
            return None
        counts["v129_quiz_played"] += 1
        return command
    return None


def v129_public_answer(state, d, policy: str) -> int:
    """v0.129: 身長の答え（整数 cm）を、答えるプレイヤーの観測と公開の情報だけで決める（置いたカード・決定の続きの情報の置いたカードを読まない）。

    - ``knowledge``（正解を目ざす方策）: 観測の伝えた名前のカードを、公開のカードの一覧（同梱の写しの定義）から引き、全国図鑑番号が 1 つに決まれば、公開の身長の参照値の原表記（「0.2m」）を
      人向けの答えの換算（``heights.height_answer_cm``）で整数 cm にする。決まらなければ 100
    - ``wrong``（開発用の、意図して誤る方策）: knowledge の答え + 1"""
    from kyuura_engine.cards import load_card_pool
    from kyuura_engine.heights import height_answer_cm, load_species_heights
    from kyuura_engine.observation import observe

    name = observe(state, d.player)["decision"]["name"]
    numbers = {d_.dex for d_ in load_card_pool().definitions.values() if d_.category == "pokemon" and d_.name_ja == name and d_.dex}
    heights = load_species_heights().by_dex
    known = None
    if len(numbers) == 1 and len(next(iter(numbers))) == 1 and next(iter(numbers))[0] in heights:
        known = height_answer_cm(heights[next(iter(numbers))[0]].height_raw)
    value = 100 if known is None else known
    return value + 1 if policy == "wrong" else value


def _v129_decision(state, counts):
    """v0.129: カツラのクイズ その1の置くカード（選べるもののうち、選ぶと止めるカードを除いたものを順に。止めるカードがあったことを数える）と、相手プレイヤーの身長の答え（方策の割り当て
    ``V129_ANSWER_POLICIES``: 番の番号と使ったトレーナーの uid の和が偶数なら knowledge、奇数なら wrong）。"""
    from kyuura_engine import decisions as D

    d = state.decision
    used = state.trainer_in_use
    if d is None or d.resume != "trainer" or used is None or state.cards[used.card].card_id != V129_QUIZ:
        return None
    if d.kind == D.QUIZ_CARD:
        blocked = set(d.context_value("unresolved_choices", ()) or ())
        free = [uid for uid in d.options if uid not in blocked]
        if blocked:
            counts["v129_blocked_offered"] += 1
        if not free:
            return None
        chosen = free[(state.turn_number // 2 + used.card) % len(free)]
        counts["v129_card_chosen"] += 1
        return ResolveDecision(d.player, d.id, (chosen,))
    if d.kind == D.QUIZ_HEIGHT_ANSWER:
        policy = V129_ANSWER_POLICIES[(state.turn_number + used.card) % 2]
        counts[f"v129_answer_{policy}"] += 1
        return ResolveDecision(d.player, d.id, (v129_public_answer(state, d, policy),))
    return None


def v129_uses(state):
    """v0.129: ログから数えたカツラのクイズ その1の動き（このカードのない局では空）。

    - ``played``・``correct``・``wrong``・``drawn_by_answerer``・``drawn_by_user``（引いた枚数）・``short_draw``（2 枚より少なく引いた）・``returned``（手札にもどした）
    - ``card_<id>``（置いたカード）・``height_<cm>``（置いたカードの参照値）"""
    counts = Counter()
    if not any(state.cards[uid].card_id in V0_129 for uid in state.cards):
        return counts
    log = list(state.log)
    for i, e in enumerate(log):
        kind = e["kind"]
        if kind == "play_trainer" and state.cards[e["card"]].card_id == V129_QUIZ:
            counts["played"] += 1
        elif kind == "quiz_height_reveal":
            counts["correct" if e["correct"] else "wrong"] += 1
            counts[f"card_{e['card_id']}"] += 1
            counts[f"height_{e['height_cm']}"] += 1
            following = log[i + 1] if i + 1 < len(log) else None
            drawn = len(following["cards"]) if following is not None and following["kind"] == "draw" else 0
            counts["drawn_by_answerer" if e["correct"] else "drawn_by_user"] += drawn
            if drawn < 2:
                counts["short_draw"] += 1
        elif kind == "set_aside_returned" and e.get("reason") == "quiz" and state.cards[e["trainer_card"]].card_id == V129_QUIZ:
            counts["returned"] += 1
    return counts


def _v130_trainer(state, tried, counts):
    """v0.130: 手札のとりかえっこプリーズを、ワザか番の終わりの前に使う（1 つの番に 1 回。使う前に止まる・拒否されるなら、その番は試さない）。"""
    player = state.current_player
    if state.trainer_in_use is not None:
        return None
    for card in state.players[player].hand:
        if state.cards[card].card_id != V130_SWAP:
            continue
        key = ("v130_swap", state.turn_number)
        if key in tried:
            return None
        tried.add(key)
        command = PlayTrainer(player, card)
        if not _v052_accepted(state, command):
            counts["v130_swap_not_played"] += 1
            return None
        counts["v130_swap_played"] += 1
        return command
    return None


def _v130_decision(state, counts):
    """v0.130: とりかえっこプリーズの選ぶカード（使ったプレイヤー・相手プレイヤー）と、相手プレイヤーの答え（``V130_SWAP`` の上の決まった割り当て）。錯乱ジムで相手がかわりに使うかの問い
    （使うことを選ぶと止まる）には答えない（元の手順が止まらない答えを選ぶ）。"""
    from kyuura_engine import decisions as D

    d = state.decision
    used = state.trainer_in_use
    if d is None or d.resume != "trainer" or used is None or state.cards[used.card].card_id != V130_SWAP or d.context_value("stage") is None:
        return None
    stage = d.context_value("stage")
    if d.kind == D.SELECT_EXCHANGE_CARD:
        offset = state.turn_number if stage == "take" else 3 * state.turn_number
        counts[f"v130_select_{stage}"] += 1
        return ResolveDecision(d.player, d.id, (d.options[(offset + used.card) % len(d.options)],))
    if d.kind == D.ACCEPT_REQUEST and stage == "accept":
        accept = (state.turn_number + used.card) % 2 == 0
        counts["v130_answer_accept" if accept else "v130_answer_decline"] += 1
        return ResolveDecision(d.player, d.id, (1,) if accept else ())
    return None


def v130_uses(state):
    """v0.130: ログから数えたとりかえっこプリーズと、交換したカードの動き（このカードのない局では空）。

    - ``played``・``accepted``・``declined``・``exchanged_cards``（交換したカードの延べ枚数）・``re_exchanged``（2 回以上交換したカード）・``drawn_on_decline``（オーケーでないときに引いた
      枚数）・``short_draw``（2 枚より少なく引いた）・``chaos_offered``（錯乱ジムの「うら」で、相手がかわりに使うかを問われた）
    - ``after_<ログの種類>``: 交換したあとのログで、交換したカードの uid が出たもの（交換のログを除く。そのカードを使う・場に出す・進化させる・つける・トラッシュする・山札・手札・サイドに
      移すなど。同じログに 2 枚出れば 2）。``swapped_<種類>``: 交換したカードの印刷の分類"""
    counts = Counter()
    if not any(state.cards[uid].card_id in V0_130 for uid in state.cards):
        return counts
    from kyuura_engine.observation import _uid_field

    log = list(state.log)
    swapped: dict[int, int] = {}  # uid → 交換した回数
    for i, e in enumerate(log):
        kind = e["kind"]
        if kind == "play_trainer" and state.cards[e["card"]].card_id == V130_SWAP:
            counts["played"] += 1
        elif kind == "request_answered" and e.get("trainer_card") in state.cards and state.cards[e["trainer_card"]].card_id == V130_SWAP:
            counts["accepted" if e["accepted"] else "declined"] += 1
            following = log[i + 1] if i + 1 < len(log) else None
            if not e["accepted"]:
                drawn = len(following["cards"]) if following is not None and following["kind"] == "draw" else 0
                counts["drawn_on_decline"] += drawn
                counts["short_draw"] += drawn < 2
        elif kind in ("chaos_answered", "chaos_not_borrowable") and state.cards[e["card"]].card_id == V130_SWAP:
            counts["chaos_" + ("answered" if kind == "chaos_answered" else "not_borrowable")] += 1
        if kind == "cards_exchanged":
            for uid in (e["given_card"], e["taken_card"]):
                swapped[uid] = swapped.get(uid, 0) + 1
                counts["exchanged_cards"] += 1
                counts[f"swapped_{state.printed_def(uid).category}"] += 1
            continue
        if not swapped:
            continue
        for name, value in e.items():
            if not _uid_field(name):
                continue
            values = value if isinstance(value, (list, tuple)) else (value,)
            counts.update(f"after_{kind}" for v in values if type(v) is int and v in swapped)
    counts["re_exchanged"] = sum(1 for n in swapped.values() if n > 1)
    chaos_offers = sum(1 for e in log if e["kind"] == "chaos_check" and e.get("card") in state.cards and state.cards[e["card"]].card_id == V130_SWAP)
    counts["chaos_checks"] = chaos_offers
    return +counts


def v131_uses(state):
    """v0.131: ログから数えたナッシー[Exeggutor]（``V0_131``）の動き（このカードのない局では空）。

    - ``in_deck_<id>``: デッキに入れた枚数（同じ名前 4 枚の数え方を通ったデッキ）。``evolve_<id>_from_<下のカード>``: 手札から進化させた（下のポケモンのカード）
    - ``attack_<id>``: このカードがワザ（ふみつけ）を宣言した。``attack_heads``・``attack_tails``: そのコイン。``form_attack_<id>``: ［へんしん］の今の姿のワザとして宣言された
    - ``copied_<id>``: ゆびをふるなどでワザをまねられた。``quiz_card_<id>``・``quiz_hint_<ワザ名>``・``quiz_answer_<正解か>``: カツラのクイズ その3 で置いた・伝えたワザ名・答え
    - ``slot_same_name``: スロットゲームで、このカードがほかの「ナッシー」と同じ名前のカードとして手札に加わった"""
    counts = Counter()
    if not any(state.cards[uid].card_id in V0_131 for uid in state.cards):
        return counts
    log = list(state.log)
    for card in state.cards.values():
        if card.card_id in V0_131:
            counts[f"in_deck_{card.card_id}"] += 1
    quiz_cards = set()
    for i, e in enumerate(log):
        kind = e["kind"]
        if kind == "evolve" and e.get("to_card_id") in V0_131:
            counts[f"evolve_{e['to_card_id']}_from_{e['from_card_id']}"] += 1
        elif kind == "attack":
            source = e.get("card_id") or state.cards[e["pokemon"]].card_id
            if source in V0_131:
                counts[f"{'form_' if e.get('route') == 'form' else ''}attack_{source}"] += 1
                flip = next((x for x in log[i + 1:] if x["kind"] in ("coin_flip", "attack", "turn_end")), None)
                if flip is not None and flip["kind"] == "coin_flip":
                    counts[f"attack_{flip['result']}"] += 1
        elif kind == "copy_attack" and str(e.get("copied", "")).split("#")[0] in V0_131:
            counts[f"copied_{e['copied'].split('#')[0]}"] += 1
        elif kind == "quiz_card_set" and state.cards[e["card"]].card_id in V0_131:
            quiz_cards.add(e["trainer_card"])
            counts[f"quiz_card_{state.cards[e['card']].card_id}"] += 1
        elif kind == "quiz_hint" and e.get("trainer_card") in quiz_cards:
            counts[f"quiz_hint_{e['attack_name']}"] += 1
        elif kind == "quiz_reveal" and e.get("card_id") in V0_131:
            counts[f"quiz_answer_{'correct' if e['correct'] else 'wrong'}"] += 1
        elif kind == "reveal_deck_top":
            taken = [x["card"] for x in log[i + 1:i + 4] if x["kind"] == "reveal_from_deck"]
            if any(state.cards[uid].card_id in V0_131 for uid in taken) and len(taken) >= 2:
                counts["slot_same_name"] += 1
                counts[f"slot_with_{'_'.join(sorted(state.cards[uid].card_id for uid in taken))}"] += 1
    return +counts


def v127_uses(state):
    """v0.127: ログから数えたドライアップ・怪電波マシーン・利用者の簡略ルールのワザの動き（v0.127 のカードのない局では空）。

    - ``dry_up``（宣言した回数）・``dry_up_heads_<H>``（ワザの「うら」が出るまでのコインの一まとまりの「おもて」の数。ナツメのESPのやり直しがあればまとまりごと）・``dry_up_discarded``
      （トラッシュした「水」エネルギーカードの枚数）
    - ``twm_played``・``twm_heads_<H>``・``twm_returned``（相手の手札にもどしたカードの枚数）・``twm_finished``（使い終えた。番を終える）
    - ``interrupted_<コード>``・``interrupted_required_<H>``・``interrupted_available_<N>``（途中停止）
    - ``birthday_heads``・``birthday_tails``（おたんじょうびのコイン）・``troubled``（こまったなあ）・``troubled_confused``（こまったなあでこんらんにした数）・``smack``（どつく）"""
    counts = Counter()
    if not any(state.cards[uid].card_id in V0_127 for uid in state.cards):
        return counts
    for e in state.log:
        kind = e["kind"]
        effect = str(e.get("effect") or "")
        if kind == "attack":
            card_id = e.get("card_id") or state.cards[e["pokemon"]].card_id
            index = e.get("attack_index")
            if card_id in V127_MOLTRES and index == 0:
                counts["dry_up"] += 1
            elif card_id == V127_SLOWKING:
                counts["troubled" if index == 0 else "smack"] += 1
        elif kind == "coin_flip" and e.get("source") == "attack" and effect.split("#")[0] in V127_MOLTRES and e.get("until") == "tails" and e["result"] == "tails":
            counts[f"dry_up_heads_{e['count'] - 1}"] += 1
        elif kind == "coin_flip" and e.get("source") == "attack" and effect.split("#")[0] in V127_PIKACHU:
            counts[f"birthday_{e['result']}"] += 1
        elif kind == "coin_flip" and e.get("source") == "trainer" and effect == V127_TWM and e["result"] == "tails":
            counts[f"twm_heads_{e['count'] - 1}"] += 1
        elif kind == "discard_attached_energy" and effect.split("#")[0] in V127_MOLTRES:
            counts["dry_up_discarded"] += 1
        elif kind == "play_trainer" and state.cards[e["card"]].card_id == V127_TWM:
            counts["twm_played"] += 1
        elif kind == "trainer_return_energy" and state.cards[e["trainer_card"]].card_id == V127_TWM:
            counts["twm_returned"] += len(e["cards"])
        elif kind == "discard_trainer" and state.cards[e["card"]].card_id == V127_TWM:
            counts["twm_finished"] += 1
        elif kind == "halted" and e.get("interrupted"):
            counts[f"interrupted_{e['code']}"] += 1
            counts[f"interrupted_required_{e['required']}"] += 1
            counts[f"interrupted_available_{e['available']}"] += 1
        elif kind == "special_condition" and effect.split("#")[0] == V127_SLOWKING:
            counts["troubled_confused"] += 1
    return counts


def _v125_power(state, tried, counts):
    """v0.125: 自分のベンチのプクリン（ES1-027。［てだすけ］。この番にまだ使っていない）で、自分の対戦ポケモンが特殊状態なら使う（コインは状態の乱数）。状態が 1 つなら受け付け、
    2 つならエンジンが HH2 で拒否する（番ごとに 1 回だけ試す。拒否のあとは元の手順に任せる）。状態がないときは試さない（HH1 は単体のテストで確かめる）。"""
    player = state.current_player
    names = _v125_active_conditions(state, player)
    if not names:
        return None
    for pokemon in state.players[player].bench:
        if state.is_face_down(pokemon) or state.cards[pokemon.card].card_id != V125_WIGGLYTUFF or (pokemon.pokemon_id, 0) in state.power_uses_this_turn:
            continue
        key = ("v125_helping_hand", state.turn_number, pokemon.pokemon_id)
        if key in tried:
            continue
        tried.add(key)
        counts[f"v125_power_helping_hand_{len(names)}"] += 1
        return UsePokemonPower(player, pokemon.pokemon_id, 0, card=pokemon.card)
    return None


def v126_uses(state):
    """v0.126: ログから数えたフラッシュ・おもての山札の動き（フラッシュのない局では空）。

    - ``flash_played``（使った回数）・``flash_arranged``（並べかえを終えた側の数。``flash_face_up``）・``flash_completed``（両方の側を並べ終えて使い終えた回数）
    - ``top_revealed``（いちばん上のおもてのカードが変わって公開された回数。``face_up_deck_top`` のカードのあるもの）・``top_none``（おもてのカードがなくなった）
    - ``drew_face_up``（番の最初・効果で引いた、いちばん上のおもてのカード）・``shuffle_cleared``（切る前に印を消した回数）・``cleared_cards``（消した印の数）
    - ``meowth_took_face_up_<行き先>``（てつだうふりで、おもてのいちばん上を動かした）"""
    counts = Counter()
    if not any(state.cards[uid].card_id in V0_126 for uid in state.cards):
        return counts
    marks = {0: [], 1: []}
    prior = None
    for e in state.log:
        kind = e["kind"]
        if kind == "play_trainer" and state.cards[e["card"]].card_id == V126_FLASH:
            counts["flash_played"] += 1
        elif kind == "flash_face_up":
            counts["flash_arranged"] += 1
            if prior is not None and prior["kind"] == "arrange_deck_top":
                marks[e["owner"]] = list(prior["cards"])
        elif kind == "discard_trainer" and state.cards[e["card"]].card_id == V126_FLASH:
            counts["flash_completed"] += 1
        elif kind == "face_up_deck_top":
            counts["top_revealed" if e["card_id"] is not None else "top_none"] += 1
        elif kind == "shuffle" and e.get("face_up_cleared"):
            counts["shuffle_cleared"] += 1
            counts["cleared_cards"] += e["face_up_cleared"]
            marks[e["player"]] = []
        elif kind == "draw" and marks[e["player"]] and e["cards"] and e["cards"][0] == marks[e["player"]][0]:
            counts["drew_face_up"] += 1
            marks[e["player"]] = [uid for uid in marks[e["player"]] if uid not in e["cards"]]
        elif kind == "take_deck_top" and marks[e["player"]] and e["card"] == marks[e["player"]][0]:
            counts[f"meowth_took_face_up_{e['destination']}"] += 1
            marks[e["player"]] = marks[e["player"]][1:]
        elif kind == "shuffle":
            marks[e["player"]] = []
        prior = e
    return counts


def v125_uses(state):
    """v0.125: ログから数えた［てだすけ］・ふくらむの動き（v0.125 のカードのない局では空）。

    - ``helping_hand_<heads|tails>``（［てだすけ］のコインの面）・``helping_hand_cured_<状態>``（回復した状態）
    - ``inflate_used``（ふくらむを使った回数）・``inflate_reduced``（受けたワザのダメージの 8 段階に「ふくらむ」の -10 の記録があるダメージ）・``inflate_zero``（そのうち 0 になったもの）"""
    counts = Counter()
    if not any(state.cards[uid].card_id in V0_125 for uid in state.cards):
        return counts
    card = {uid: c.card_id for uid, c in state.cards.items()}
    inflated = {}  # 効果を持つポケモンのカード（uid）→ はたらく番
    for e in state.log:
        kind = e["kind"]
        if kind == "coin_flip" and e.get("source") == "power" and e.get("effect") == f"{V125_WIGGLYTUFF}@power0":
            counts[f"helping_hand_{e.get('result')}"] += 1
        elif kind == "special_conditions_removed" and e.get("effect") == f"{V125_WIGGLYTUFF}@power0":
            for name in e.get("conditions", ()):
                counts[f"helping_hand_cured_{name}"] += 1
        elif kind == "attack" and card.get(e.get("card", e.get("pokemon"))) == V125_WIGGLYTUFF and e.get("attack_index") == 0:
            counts["inflate_used"] += 1
        elif kind == "persistent_effect_added" and e.get("persistent_effect") == "damage_reduction" and e.get("effect") == f"{V125_WIGGLYTUFF}#0":
            inflated[e.get("pokemon")] = e.get("active_turn")
        elif kind == "damage" and inflated.get(e.get("pokemon")) == e.get("turn") and any(
                tuple(m) == (8, e.get("pokemon"), -10) for m in e.get("modifiers") or ()):
            # ダメージの変更の記録 (段階, 発生源のカード, 量)。8 段階の、受けるポケモン自身の -10
            counts["inflate_reduced"] += 1
            if e.get("amount") == 0:
                counts["inflate_zero"] += 1
    return counts


def _v124_power(state, tried, counts):
    """v0.124: 自分のバトル場の［すごいへんしん］のメタモン（変身していない・この番に使っていない・ねむり・マヒ・こんらんでない）なら使う（コインは状態の乱数）。変身しているときは使わない
    （「うら」でもどるので）。使う前に止まる場面（選べるどのポケモンも止める）は、エンジンが拒否し、元の手順に任せる。"""
    player = state.current_player
    active = state.players[player].active
    if active is None or state.is_face_down(active) or state.cards[active.card].card_id != V124_SUPER_DITTO or active.super_transform is not None:
        return None
    conditions = active.conditions
    if conditions.asleep or conditions.paralyzed or conditions.confused or (active.pokemon_id, 0) in state.power_uses_this_turn:
        return None
    key = ("v124_super", state.turn_number, active.pokemon_id)
    if key in tried:
        return None
    tried.add(key)
    counts["v124_power_super_transform"] += 1
    return UsePokemonPower(player, active.pokemon_id, 0, card=active.card)


def _v124_decision(state, counts):
    """v0.124: ［すごいへんしん］の選ぶポケモン。止める選択（自分自身など。``unresolved_choices``）を選ばず、相手のバトル場 → 相手のベンチ → 自分のベンチの順に、最初の選べるものを選ぶ。"""
    d = state.decision
    if d is None or d.resume != "power" or d.kind != "select_pokemon":
        return None
    use = d.context_value("use")
    if not use or use[2] != V124_SUPER_DITTO:
        return None
    blocked = set(d.context_value("unresolved_choices", ())) | set(d.context_value("unsupported_choices", ()))
    opponent = state.players[1 - d.player]
    order = [p.pokemon_id for p in opponent.in_play()] + [p.pokemon_id for p in state.players[d.player].bench]
    choice = next((pid for pid in order if pid in d.options and pid not in blocked), None)
    if choice is None:
        return None
    side = "opponent" if any(p.pokemon_id == choice for p in opponent.in_play()) else "own"
    counts[f"v124_super_target_{side}"] += 1
    return ResolveDecision(d.player, d.id, (choice,))


def v124_uses(state):
    """v0.124: ログから数えた［すごいへんしん］・［わるいはどう］・わるいぞうふくの動き（v0.124 のカードのない局では空）。

    - ``super_<id>``（選んだ変身のもとのカード）・``super_side_<own|opponent>``・``super_reverted_<理由>``・``super_attack_<id>#<位置>``（変身したメタモンが使ったワザ。写したワザ）
    - ``pulse_<量>``（わるいはどうの追加 0・10・20）・``pulse_coins_<枚数>``・``costume_bench_<わるいポケモンの数>``・``costume_heads_<おもての数>``（わるいぞうふく）
    - ``classic_attack_<id>#<位置>``（化石のメタモンが写して使ったワザ）"""
    counts = Counter()
    if not any(state.cards[uid].card_id in V0_124 for uid in state.cards):
        return counts
    card = {uid: c.card_id for uid, c in state.cards.items()}
    for e in state.log:
        kind = e["kind"]
        if kind == "super_transform":
            counts[f"super_{e.get('card_id')}"] += 1
            counts[f"super_side_{'own' if e.get('source_player') == e.get('player') else 'opponent'}"] += 1
        elif kind == "super_transform_reverted":
            counts[f"super_reverted_{e.get('reason')}"] += 1
        elif kind == "dark_pulse":
            counts[f"pulse_{e.get('amount')}"] += 1
            counts[f"pulse_coins_{len(e.get('coins', ()))}"] += 1
        elif kind == "attack":
            pokemon_card = card.get(e.get("pokemon"))
            printed = card.get(e.get("card", e.get("pokemon")))
            if pokemon_card == V124_SUPER_DITTO and printed != V124_SUPER_DITTO:
                counts[f"super_attack_{printed}#{e.get('attack_index')}"] += 1
            elif pokemon_card == DITTO and printed != DITTO:
                counts[f"classic_attack_{printed}#{e.get('attack_index')}"] += 1
            elif pokemon_card == V124_GR_MEWTWO:
                counts["costume_used"] += 1
    return counts


def _v123_decision(state, counts):
    """v0.123: v0.123 のカードのワザ（相手のワザとして使ったときもふくむ）の決定への答え。トラッシュするエネルギーカード（いかりのほのお 2 枚・ほのおのあらし 3 枚。ちょうどの枚数の決定）は、
    選べるもののうち前から決定の数だけ選ぶ（v0.31 の ``_v031_decision`` と同じ答え方。元の手順は 1 つだけ選ぶ）。原典で決められない選択・未対応の選択は選ばない。ほかの決定は元の手順に任せる。"""
    d = state.decision
    if d is None or d.resume != "attack" or d.kind != DISCARD_ENERGY:
        return None
    use = d.context_value("use")
    copied = d.context_value("copied")
    card = copied[0] if copied else (use[2] if use is not None else None)
    if card not in V0_123:
        return None
    blocked = set(d.context_value("unresolved_choices", ())) | set(d.context_value("unsupported_choices", ()))
    options = [o for o in d.options if o not in blocked]
    counts[f"v123_{card}_discard_{d.min_choices}"] += 1
    return ResolveDecision(d.player, d.id, tuple(options[:d.min_choices]))


def v123_uses(state):
    """v0.123: ログから数えた 3 枚・5 のワザと、名前を直した登録済みの 2 枚のワザの動き（v0.123 のカードのない局では空）。

    - ``attack_<id>#<位置>``（v0.123 のカード自身が宣言したワザ）・``renamed_attack_<id>#<位置>``（PMCG1-019・PMCG6-034 が宣言したワザ）・``copied_<id>#<位置>``（相手のワザとして使った
      v0.123 のワザ。ゆびをふるなど）・``confused_<id>#<位置>``（こんらんの「うら」でワザが起きなかった）
    - ``rage_discard_<枚数>``（いかりのほのおでトラッシュした炎エネルギーカード）・``rage_base_<量>``・``rage_counters_<数>``（相手の対戦ポケモンへのダメージの基本となる計算と、
      そこから目安 40 を引いた 10 ごとの数。宣言のときのダメージカウンターの数との一致はログの監査 v123_problems が確かめる）・``rage_no_damage``（トラッシュのあと相手へのダメージの記録がない）
    - ``firestorm_discard_<枚数>``（ほのおのあらし）・``self_damage_<id>#<位置>_<量>``（ヒートタックル・とっしん）・``quick_heads``・``quick_tails``（でんこうせっか）
    """
    counts = Counter()
    if not any(state.cards[uid].card_id in V0_123 for uid in state.cards):
        return counts
    card = {uid: c.card_id for uid, c in state.cards.items()}
    window = None

    def close(w):
        if w is None or w["key"] is None:
            return
        if w["key"] == V123_RAGE_FLAMES and w["discards"]:
            counts[f"rage_discard_{w['discards']}"] += 1
            if w["base"] is None:
                counts["rage_no_damage"] += 1
            else:
                counts[f"rage_base_{w['base']}"] += 1
                counts[f"rage_counters_{(w['base'] - 40) // 10}"] += 1
        if w["key"].endswith("#1") and w["key"].split("#")[0] in ("GD5-007", BLAINES_ARCANINE) and w["discards"]:
            counts[f"firestorm_discard_{w['discards']}"] += 1

    for e in state.log:
        kind = e["kind"]
        if kind in ("attack", "turn_end", "game_end", "halted"):
            close(window)
            window = None
        if kind == "attack":
            pokemon_card = e.get("card", e.get("pokemon"))
            key = f"{card.get(pokemon_card)}#{e.get('attack_index')}"
            if card.get(pokemon_card) in V0_123_POKEMON:
                counts[f"attack_{key}"] += 1
            elif card.get(pokemon_card) in V123_RENAMED:
                counts[f"renamed_attack_{key}"] += 1
            window = {"key": key, "discards": 0, "base": None}
            continue
        if window is None:
            continue
        if kind == "copy_attack":
            window = {"key": e["copied"], "discards": 0, "base": None}
            if e["copied"].split("#")[0] in V0_123_POKEMON:
                counts[f"copied_{e['copied']}"] += 1
            continue
        key = window["key"]
        if kind == "confusion_damage" and key.split("#")[0] in V0_123_POKEMON:
            counts[f"confused_{key}"] += 1
        if kind == "discard_energy" and e.get("effect") == key:
            window["discards"] += 1
        if kind == "damage" and e.get("target") == "self" and e.get("effect") == key and key.split("#")[0] in V0_123_POKEMON + V123_RENAMED:
            counts[f"self_damage_{key}_{e['amount']}"] += 1
        if kind == "damage" and e.get("target", "opponent_active") == "opponent_active" and not e.get("retaliation") and window["base"] is None:
            window["base"] = dict(e["steps"]).get("1 基本となる計算")
        if kind == "coin_flip" and e.get("source") == "attack" and e.get("effect") == "PR1-016#0":
            counts[f"quick_{e['result']}"] += 1
    close(window)
    return counts


def v122_uses(state):
    """v0.122: ログから数えた 13 枚・17 のワザ・8 の特殊能力の動き（v0.122 のカードのない局では空）。

    - ``attack_<id>#<位置>``（宣言した v0.122 のワザ）
    - ［ANGER］: ``anger_used_<self|bench>``・``anger_counters_<数>``・``anger_with_xxxxx``（同じ宣言で［XXXXX］も）。［METAL df］: ``metal_df_applied``（ダメージの記録の変更効果）
    - ［UNDO］: ``undo_returned``。［WANT］: ``want_<heads|tails>``・``want_recovered``。［げんしのゆめ］: ``primal_dream_<heads|tails>``・``primal_dream_bonus``（ダメージの記録の 6 段階の追加）
    - ［かせきか］: ``fossilize_target``・``fossilize_<heads|tails>``・``fossilize_devolved``。［かせきのみちびき］: ``fossil_guide_<heads|tails>``・``fossil_guide_recovered``
    - ［つるでひっぱる］: ``vine_pull``・``vine_pull_switched``・``vine_pull_skipped``。みだれうち: ``random_strike_targets_<数>``（相手が選んだ配分の 0 でないポケモンの数）
    - 10まんボルト: ``thunderbolt_discarded``・``thunderbolt_zero``。きりもみアタック: ``spin_attack_self``。いやなかふん: ``pollen_flips``・``pollen_heads_<数>``（2 枚のうちの「おもて」）・
      ``pollen_<状態>``。たかくとぶ: ``fly_high_set``。ドリルダイブ: ``drill_dive_step2_<p.321 の 2 段階までの値>``（相手の対戦ポケモンへのダメージのログ。たかくとぶのあとは 80）・
      ``drill_dive_locks``。れんぞくキック: ``kick_heads_<数>``。こうそくスピン: ``rapid_spin_switch``
    - ダメージのログにはワザの欄がないので、直前のワザの宣言（``attack``。ほかのワザとして使えば ``copy_attack``）のカードとワザの位置で、どのワザのダメージかを決める。
      コインはワザのコイン（``source`` が ``attack``）だけを数える（こんらんのコインを除く）
    """
    counts = Counter()
    if not _v122_present(state):
        return counts
    card = {uid: c.card_id for uid, c in state.cards.items()}
    current = None  # 今のワザ（カード id#位置）
    heads = 0
    for e in state.log:
        kind = e["kind"]
        effect = e.get("effect")
        if kind == "attack":
            current = f"{card.get(e.get('card', e.get('pokemon')))}#{e.get('attack_index')}"
        elif kind == "copy_attack":
            current = e.get("copied")
        elif kind in ("turn_end", "game_end"):
            current = None
        if kind == "attack":
            pokemon_card = e.get("card", e.get("pokemon"))
            if card.get(pokemon_card) in V0_122_POKEMON and e.get("attack_index") is not None:
                counts[f"attack_{card.get(pokemon_card)}#{e.get('attack_index')}"] += 1
        if kind == "group_attack_power" and e.get("card_id") == V122_A:
            counts["anger_used_" + ("self" if e.get("pokemon_id") == e.get("attacker_pokemon_id") else "bench")] += 1
        if kind == "group_attack_power_counters":
            counts[f"anger_counters_{e.get('counters')}"] += 1
        if kind == "group_attack_power_coins" and any(x.get("kind") == "group_attack_power_counters" and x.get("effect") == effect and x.get("turn") == e.get("turn")
                                                      for x in state.log if x.get("turn") == e.get("turn")):
            counts["anger_with_xxxxx"] += 1
        if kind == "damage":
            # ダメージの記録の変更効果は (段階, 発生源のカード, 量)。［METAL df］はアンノーンM の -30、［げんしのゆめ］はオムナイト ES2-011 の +10
            for m in e.get("modifiers", ()):
                if isinstance(m, (tuple, list)) and len(m) >= 3 and card.get(m[1]) == V122_M and m[2] < 0:
                    counts["metal_df_applied"] += 1
                if isinstance(m, (tuple, list)) and len(m) >= 3 and card.get(m[1]) == V122_OMANYTE and m[2] > 0:
                    counts[f"primal_dream_bonus_step{m[0]}"] += 1
        if kind == "pokemon_power" and e.get("on_retreat"):
            counts["vine_pull"] += 1
        if kind == "coin_flip" and e.get("source") == "power":
            name = {V122_W: "want", V122_OMANYTE: "primal_dream", V122_KABUTO: "fossilize", V122_OMANYTE3: "fossil_guide"}.get(card.get(e.get("card")))
            if name is not None:
                counts[f"{name}_{e['result']}"] += 1
        if kind == "return_in_play_to_hand" and str(e.get("power", "")).startswith(V122_U):
            counts["undo_returned"] += 1
        if kind == "power_recover_from_discard":
            counts[("want" if str(e.get("power", "")).startswith(V122_W) else "fossil_guide") + "_recovered"] += 1
        if kind == "fossilize_target":
            counts["fossilize_target"] += 1
        if kind == "devolve" and str(e.get("power", "")).startswith(V122_KABUTO):
            counts["fossilize_devolved"] += 1
        if kind == "switch" and str(e.get("power", "")).startswith(V122_IVYSAUR):
            counts["vine_pull_switched"] += 1
        if kind == "vine_pull_skipped":
            counts["vine_pull_skipped"] += 1
        if kind == "trainer_effect_added" and e.get("effect_kind") == "fossil_attack_bonus":
            counts["primal_dream_bonus_added"] += 1
        if kind == "damage_allocated" and effect == f"{V122_IVYSAUR}#0":
            counts[f"random_strike_targets_{sum(1 for c in e.get('counts', ()) if c)}"] += 1
        if effect == f"{V122_RAICHU}#1":
            if kind == "discard_energy":
                counts["thunderbolt_discarded"] += 1
            if kind == "discard_energy_failed":
                counts["thunderbolt_zero"] += 1
        if kind == "damage" and effect == f"{V122_AERODACTYL}#1" and e.get("target") == "self":
            counts["spin_attack_self"] += 1
        if kind == "coin_flip" and effect in (f"{V122_VENUSAUR}#0", f"{V122_CAPOEIRA}#0") and e.get("source") == "attack":  # こんらんのコインは数えない
            heads = (0 if e.get("number") == 1 else heads) + (e.get("result") == "heads")
            if e.get("number") == e.get("count"):
                counts["pollen_flips" if effect == f"{V122_VENUSAUR}#0" else f"kick_heads_{heads}"] += 1
                if effect == f"{V122_VENUSAUR}#0":
                    counts[f"pollen_heads_{heads}"] += 1
        if kind == "special_condition" and effect == f"{V122_VENUSAUR}#0":
            counts[f"pollen_{e.get('condition')}"] += 1
        if kind == "persistent_effect_added" and effect == f"{V122_FEAROW}#0":
            counts["fly_high_set"] += 1
        if kind == "damage" and current == f"{V122_FEAROW}#1" and e.get("target", "opponent_active") == "opponent_active" and not e.get("retaliation"):
            upto_2 = [value for label, value in (e.get("steps") or ()) if str(label)[:2] in ("1 ", "2 ")]
            counts[f"drill_dive_step2_{upto_2[-1] if upto_2 else None}"] += 1
        if kind == "persistent_effect_added" and effect == f"{V122_FEAROW}#1":
            counts["drill_dive_locks"] += 1
        if kind == "switch" and effect == f"{V122_CAPOEIRA}#1":
            counts["rapid_spin_switch"] += 1
    return counts


def _v120_setup(state, command, counts):
    """v0.120: 対戦準備でバトル場に出すたねポケモン（元の手順は手札の最初のたねポケモン）が、決められない姿（v0.49 の TF1・TF2、v0.120 の TF3。相手のバトル場のポケモンを写す
    メタモン）で拒否されるなら、受け付けられる別のたねポケモンをバトル場に出す（ベンチは元の手順のまま、出すポケモンを除く）。どれも拒否されるなら元の操作（エンジンが拒否する）。
    F120 対 D49（相手のバトル場のウソッキーの［ものまね］を写す TF1）で初めて起こった。v0.119 までの組では拒否がないので、何もしない。"""
    if state.phase is not Phase.SETUP_PLACEMENT or type(command).__name__ != "PlaceStartingPokemon":
        return command
    try:
        apply_command(state, command)
        return command
    except UnsupportedError as error:
        if error.code not in V049_FORM_STOPS:
            return command
        counts[f"v120_setup_stopped_{error.code}"] += 1
    basics = [uid for uid in state.players[command.player].hand if state.card_def(uid).is_basic_pokemon and uid != command.active]
    for active in basics:
        alternative = type(command)(command.player, active, tuple(uid for uid in command.bench if uid != active))
        try:
            apply_command(state, alternative)
        except (IllegalActionError, UnsupportedError):
            continue
        counts["v120_setup_alternative"] += 1
        return alternative
    return command


def _v120_twister_short(state, command) -> bool:
    """v0.120: たつまき（``CoinsDiscardOpponentEnergyElseFail``。相手のワザとして使うときも）を、相手の対戦ポケモンについているエネルギーカードが 1 枚以上・コインの枚数より少ないときに
    宣言した（「おもて」の数ぶんを選べないことがある。FC1）。道具が場のカードを数える（タケシの保護は数えない。今のデッキにない）。"""
    if "CoinsDiscardOpponentEnergyElseFail" not in _attack_and_copied_types(state, command):
        return False
    defender = state.players[1 - command.player].active
    count = sum(1 for uid in defender.energy if state.card_def(uid).category == "energy")
    return 1 <= count < 2


def v120_uses(state):
    """v0.120: ログから数えた 11 枚・15 のワザ・5 つの特殊能力の動き（v0.120 のカードのない局では空）。

    - ``attack_<id>#<位置>``（宣言した v0.120 のワザ）・``route_<prehistoric|puppet|mimic>``（許可で使ったワザ。``payer`` のあるものは ``puppet_paid``）
    - ``copy_<範囲>``（ワザを選んで自分のワザとして使った。``copy_source``）・``psycho_dupe_copied``（サイコデュープ）・``metronome_tails``（コインの「うら」で選ばなかった）
    - 復活: ``revived_<power|trainer>_<deck|hand>``（``bench_as_basic``）・``revive_none_<理由>``・``egg_looked``（たまごの化石で山札を見た）・``evolved_on_revived``（たねとしてあつかう
      進化カードの上に進化した）・``revived_attacked``（たねとしてあつかうポケモンがワザを宣言した）
    - しんかのほうし: ``spore_targets_<数>``・``spore_evolved``・``spore_none``。たつまき: ``twister_failed``・``twister_discarded``。ちからをあわせる: ``work_together_<基本となるダメージ>``
    """
    counts = Counter()
    if not any(state.cards[uid].card_id in V0_120 for uid in state.cards):
        return counts
    card = {uid: c.card_id for uid, c in state.cards.items()}
    revived: set[int] = set()  # たねとしてあつかう進化カード（いちばん上のあいだ）
    current = current_key = None
    for e in state.log:
        kind = e["kind"]
        if kind == "attack":
            pokemon_card = e.get("card", e.get("pokemon"))
            key = f"{card.get(pokemon_card)}#{e.get('attack_index')}" if e.get("attack_index") is not None else None
            current = _v120_name(state, key) if key is not None and card.get(pokemon_card) in V0_120_POKEMON else None
            current_key = key if current is not None else None
            if current is not None:
                counts[f"attack_{key}"] += 1
            if e.get("route") in ("prehistoric", "puppet", "mimic"):
                counts[f"route_{e['route']}"] += 1
                if e.get("payer") is not None:
                    counts["puppet_paid"] += 1
            if e.get("pokemon") in revived:
                counts["revived_attacked"] += 1
        elif kind == "turn_end":
            current = None
        elif kind == "coin_flip" and e.get("source") == "attack" and current is not None and e.get("effect") == current_key:
            counts[f"{current}_{e['result']}"] += 1  # このワザのコインだけ（選んで使ったワザのコインは数えない）
        if kind == "copy_attack" and e.get("copy_source"):
            counts[f"copy_{e['copy_source']}"] += 1
            if e.get("effect") == "PR1-021#1":
                counts["psycho_dupe_copied"] += 1
        if kind == "bench_as_basic":
            counts[f"revived_{'trainer' if e.get('trainer_card') is not None else 'power'}_{e.get('zone')}"] += 1
            revived.add(e.get("card"))
        if kind == "revive_none":
            counts[f"revive_none_{e.get('reason')}"] += 1
        if kind == "look_at_deck":
            counts["egg_looked"] += 1
        if kind == "evolve" and e.get("from_card") in revived:
            counts["evolved_on_revived"] += 1
            revived.discard(e.get("from_card"))
        if kind == "evolve_targets":
            counts[f"spore_targets_{len(e.get('targets', ()))}"] += 1
        if kind == "evolve" and current == "evolutionary_spore":
            counts["spore_evolved"] += 1
        if kind == "evolve_from_deck_none" and current == "evolutionary_spore":
            counts["spore_none"] += 1
        if kind == "attack_failed" and current == "twister":
            counts["twister_failed"] += 1
        if kind == "discard_attached_energy" and current == "twister":
            counts["twister_discarded"] += 1
        if kind == "damage" and current == "work_together":
            counts[f"work_together_{dict(e.get('steps', ())).get('1 基本となる計算')}"] += 1
    return counts


def make_policy(seen: dict, counts: Counter):
    """tools/preset_deck_games.py の手順（``checks=True``）に、v0.28〜v0.31 のカードのワザの選び方を重ねる（モジュールの説明）。v0.31 からは、
    v0.31 のカードのワザの決定への答え（``_v031_decision``）と、宣言する特殊能力の使用（``_v031_power``）も重ねる。v0.31 のカードのない局では
    何もしないので、v0.28〜v0.30 の組の結果は変わらない。"""
    base = driver.make_policy(seen, counts, checks=True)

    def choose(state, *, janken_winner, cure, tried):
        _v085_observe_wind(state, counts)  # v0.85: ［きせきのかぜ］で効果の消えた場の特殊エネルギーを数える（手順は変えない）
        if state.phase is Phase.DECISION:
            # v0.43: v0.43 のカードの決定（場に出たときの特殊能力の使う機会など）は、元の手順より先に答える（元の手順は、選ぶと止める選択しかない決定（使うことを選ぶと
            # PW3 で止まる使う機会）に答えられない）。v0.43 のカードのない局では何もしない
            early = (_v130_decision(state, counts)  # v0.130: とりかえっこプリーズの選ぶカード・答え（相手の決定にも答える。ないデッキでは何もしない）
                     or _v129_decision(state, counts)  # v0.129: カツラのクイズ その1の置くカード・身長の答え（相手の決定にも答える。ないデッキでは何もしない）
                     or _v127_decision(state, counts)  # v0.127: ドライアップの選ぶポケモン・トラッシュ、怪電波マシーンのもどすカード（ないデッキでは何もしない）
                     or _v126_decision(state, counts)  # v0.126: フラッシュの並べかえ・おもての山札のある間の選択（フラッシュのない局では何もしない）
                     or _v124_decision(state, counts)  # v0.124: ［すごいへんしん］の選ぶポケモン（v0.124 のカードの決定でなければ何もしない）
                     or _v123_decision(state, counts)  # v0.123: いかりのほのお・ほのおのあらしの炎エネルギーカードのトラッシュ（v0.123 のカードのワザでない決定では何もしない）
                     or _v122_decision(state, counts)  # v0.122: v0.122 の特殊能力・反応・ワザの決定（v0.122 のカードのない局では何もしない）
                     or _v121_decision(state, counts)  # v0.121: v0.121 のワザ・トレーナーの決定（v0.121 のカードのない局では何もしない）
                     or _v120_decision(state, counts)  # v0.120: たまごの化石・復活・ワザを選ぶ・しんかのほうし・たつまきの決定（v0.120 のカードのない局では何もしない）
                     or _v119_decision(state, counts)  # v0.119: ［シェルアーマー］を使うか・ひきずりこむの任意の入れ替え（v0.119 のワザでない決定では何もしない）
                     or _v118_decision(state, counts)  # v0.118: v0.118 のワザの決定（相手プレイヤーの配分もふくむ。v0.118 のワザでない決定では何もしない）
                     or _v118_power_decision(state, counts)  # v0.118: ［じくうへんかん］・［トランスポート］の決定
                     or _v117_decision(state, counts)  # v0.117: v0.117 のワザの決定（v0.117 のワザでない決定では何もしない）
                     or _v116_decision(state, counts)  # v0.116: v0.116 のワザの決定（v0.116 のワザでない決定では何もしない）
                     or _v115_decision(state, counts)  # v0.115: v0.115 のワザの決定（v0.115 のワザでない決定では何もしない）
                     or _v113_decision(state, counts)  # v0.113: v0.113 のワザの決定（v0.113 のワザでない決定では何もしない）
                     or _v105_decision(state, counts)  # v0.105: 山札から重ねる進化カード（v0.105 のワザでない決定では何もしない）
                     or _v104_decision(state, counts)  # v0.104: あまいみつの選ぶポケモン・プリンのかいふく（v0.104 のカードのない局では何もしない）
                     or _v098_decision(state, counts)  # v0.98: v0.98 の特殊能力の決定（v0.98 のカードのない局では何もしない）
                     or _v097_decision(state, counts)  # v0.97: v0.97 の特殊能力の決定（v0.97 のカードのない局では何もしない）
                     or _v096_decision(state, counts)  # v0.96: v0.96 の特殊能力・遺跡の石版の決定（v0.96 のカードのない局では何もしない）
                     or _v095_decision(state, counts)  # v0.95: v0.95 のワザ・特殊能力の決定（v0.95 のカードのない局では何もしない）
                     or _v094_decision(state, counts)  # v0.94: v0.94 のワザの決定（きつねびの入れ替えない答えを含む。v0.94 のカードのない局では何もしない）
                     or _v092_decision(state, counts)  # v0.92: v0.92 のワザの決定（だましうちの選ぶポケモン。v0.92 のカードのない局では何もしない）
                     or _v091_decision(state, counts)  # v0.91: v0.91 のワザの決定（選ぶポケモン・色。v0.91 のカードのない局では何もしない）
                     or _v090_decision(state, counts)  # v0.90: v0.90 のワザの決定（取りのぞく数・色。v0.90 のカードのない局では何もしない）
                     or _v089_decision(state, counts)  # v0.89: v0.89 のワザの決定（相手が選ぶ決定にも答える。v0.89 のカードのない局では何もしない）
                     or _v088_decision(state, counts)  # v0.88: v0.88 のカードの決定（v0.88 のカードのない局では何もしない）
                     or _v087_decision(state, counts)  # v0.87: v0.87 の反応の決定・v0.87 のカードの決定（v0.87 のカードのない局では何もしない）
                     or _v086_decision(state, counts)  # v0.86: 反応の決定・v0.86 のカードの決定（相手の決定にも答える。v0.86 のカードのない局では何もしない）
                     or _v085_decision(state, counts)  # v0.85: v0.85 のカードの決定（使う機会を含む。v0.85 のカードのない局では何もしない）
                     or _v084_decision(state, counts)  # v0.84: v0.84 のカードの決定（相手の決定・使う機会を含む。v0.84 のカードのない局では何もしない）
                     or _v083_decision(state, counts)  # v0.83: v0.83 のワザの決定（相手プレイヤーの決定を含む。v0.83 のポケモンのない局では何もしない）
                     or _v082_decision(state, counts)  # v0.82: エネルギーカードをトラッシュするワザの決定（v0.82 のポケモンのない局では何もしない）
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
        if state.phase is Phase.MAIN and type(command).__name__ in ("PlayBasicToBench", "UseAttack", "EndTurn"):
            # v0.114: 手札のたねポケモンカードでベイビィポケモンを進化させる（手順がそのカードをベンチに出す前・ワザ・番の終わりの前。ベイビィのないデッキでは何もしない）
            evolve = _v114_evolve(state, tried, counts)
            if evolve is not None:
                return evolve
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
        special = (_v115_energy(state, command, tried, counts)  # v0.115: なぎたおすの悪（バンギラスのないデッキでは何もしない）
                   or _v085_energy(state, command, tried, counts)  # v0.85: ミラクルエネルギー（手札にないデッキでは何もしない）
                   or _v059_energy(state, command, tried, counts)  # v0.59: カツラの 2 枚（カツラの効果がなければ何もしない）
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
            swap = _v130_trainer(state, tried, counts)  # v0.130: とりかえっこプリーズ（ないデッキでは何もしない）
            if swap is not None:
                return swap
            quiz = _v129_trainer(state, tried, counts)  # v0.129: カツラのクイズ その1（ないデッキでは何もしない）
            if quiz is not None:
                return quiz
            machine = _v127_trainer(state, command, tried, counts)  # v0.127: 怪電波マシーン（ないデッキでは何もしない）
            if machine is not None:
                return machine
            aimed = _v127_attack(state, command, counts)  # v0.127: ファイヤー・ハマちゃんのヤドキングのワザ（ほかのデッキでは何もしない）
            if aimed is not None and ("v127_aimed", state.turn_number) not in tried:
                tried.add(("v127_aimed", state.turn_number))
                return aimed
            flash = _v126_trainer(state, tried, counts)  # v0.126: フラッシュ（ないデッキでは何もしない）
            if flash is not None:
                return flash
            aimed = _v126_attack(state, command, counts)  # v0.126: おもてのいちばん上を見たサカキのニャースのワザ（ほかのデッキでは何もしない）
            if aimed is not None and ("v126_aimed", state.turn_number) not in tried:
                tried.add(("v126_aimed", state.turn_number))
                return aimed
        if state.phase is Phase.MAIN and isinstance(command, (UseAttack, EndTurn)):
            power = (_v125_power(state, tried, counts)  # v0.125: ［てだすけ］（プクリンのないデッキでは何もしない）
                     or _v124_power(state, tried, counts)  # v0.124: ［すごいへんしん］（メタモンのないデッキでは何もしない）
                     or _v114_power(state, command, tried, counts)  # v0.114: ［じっとみる］・［わんぱくパンチ］（ベイビィのないデッキでは何もしない）
                     or _v031_power(state, tried, counts) or _v042_power(state, tried, counts) or _v043_power(state, tried, counts)
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
                     or _v082_trainer(state, tried, counts)  # v0.82: エコロジム
                     or _v084_step(state, tried, counts)  # v0.84: ［おいはらう］・ポケモン育て屋夫婦
                     or _v085_step(state, tried, counts)  # v0.85: ［ファイヤーリチャージ］・［どしゃぶり］・［ファイヤーレイズ］
                     or _v086_step(state, tried, counts)  # v0.86: ［ソーラーパワー］
                     or _v087_step(state, tried, counts)  # v0.87: ［マグネット］・［とおせんぼ］の「にげる」の確かめ
                     or _v088_step(state, tried, counts)  # v0.88: ［せんすい］・［エナジーコンバーター］・［でんじりょく］
                     or _v095_step(state, tried, counts)  # v0.95: ［みやぶる］・［わるぢえ］
                     or _v096_trainer(state, tried, counts)  # v0.96: 遺跡の石版
                     or _v096_step(state, tried, counts)  # v0.96: ［OBSERVE］・［LAUGH］・［SEARCH］・［TELL］
                     or _v097_step(state, tried, counts)  # v0.97: ［FIND］・［JOIN］
                     or _v098_step(state, tried, counts)  # v0.98: ［BEAR］・［YIELD］・［GIVE］
                     or _v099_step(state, tried, counts)  # v0.99: ［HELP］
                     or _v117_step(state, tried, counts)  # v0.117: ［QUICKEN］
                     or _v118_step(state, tried, counts)  # v0.118: ［トランスポート］・［じくうへんかん］
                     or _v119_step(state, tried, counts)  # v0.119: ［ポイズンミスト］
                     or _v120_trainer(state, tried, counts)  # v0.120: たまごの化石
                     or _v121_trainer(state, tried, counts)  # v0.121: ボロのつりざお・カスミのてあて
                     or _v122_step(state, tried, counts)  # v0.122: ［UNDO］・［WANT］・［げんしのゆめ］・［かせきか］・［かせきのみちびき］
                     or _v120_step(state, tried, counts))  # v0.120: ［なかまのふっかつ］・［かせきのふっかつ］
            if power is not None:
                return power
            history = _v062_attack(state, tried, counts)  # v0.62: 履歴を読むワザ（ドリルホール・オウムがえし）を使える番に使う
            if history is not None:
                return history
            history = _v100_attack(state, tried, counts)  # v0.100: スケッチ・やみのひとみ・ほろびのうた
            if history is not None:
                return history
            history = _v101_attack(state, tried, counts)  # v0.101: カウンター
            if history is not None:
                return history
            virtual = _v049_attack(state, tried, counts)  # v0.49: 出どころがいちばん上のカードでないワザ
            if virtual is not None:
                return virtual
            probe = _v093_probe(state, tried, counts) or _v036_retreat_probe(state, tried, counts)  # v0.93・v0.36
            if probe is not None:
                return probe
            retreat = (_v122_retreat(state, tried, counts)  # v0.122: ［つるでひっぱる］
                       or _v117_retreat(state, tried, counts)  # v0.117: ［CHASE］・おいうち
                       or _v096_retreat(state, tried, counts)  # v0.96: ［ZOOM］
                       or _v046_retreat(state, tried, counts) or _v058_retreat(state, tried, counts) or _v068_retreat(state, tried, counts)  # v0.46・v0.58
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
        if card_id in V0_78_POKEMON + V0_79 + V0_82_POKEMON + V0_83 + V0_84_POKEMON + V0_85_POKEMON + V0_86_POKEMON + V0_87_POKEMON + V0_88_POKEMON + V0_89_POKEMON + V0_90_POKEMON + V0_91_POKEMON + V0_92_POKEMON + V0_93_POKEMON + V0_94_POKEMON + V0_95_POKEMON + V0_108_POKEMON + V0_113_POKEMON + V0_115_POKEMON + V0_116_POKEMON + V0_117_POKEMON + V0_118_POKEMON + V0_119_POKEMON + V0_121_POKEMON + V0_122_POKEMON:  # v0.122 のポケモンも（無色2個エネルギー）。v0.121 のポケモンも（じごくのほのおの悪エネルギー・無色2個エネルギー）。v0.119 のポケモンも（無色2個エネルギー）。v0.118 のポケモンも（無色2個エネルギー）。v0.117 のポケモンも（おいうちの悪エネルギー・無色2個エネルギー）。v0.116 のポケモンも（ダブル無色・リサイクル・なんでもなおし配合・レインボーエネルギー）。v0.115 のポケモンも（なぎたおすの悪エネルギー・無色2個エネルギー）。v0.113 のポケモンも（くろいキバの悪エネルギー・無色2個エネルギー）。v0.108 のポケモンも（かみくだくの悪エネルギー・無色2個エネルギー）。v0.95・v0.94・v0.93・v0.92（悪・鋼エネルギー）・v0.91・v0.90 のポケモンも（リサイクルエネルギー・無色2個エネルギー）。v0.89 のポケモンも（だましうちの悪エネルギー・無色2個エネルギー）。v0.83 のポケモンも（鋼エネルギー）。v0.79 のポケモンも（C79 は悪・鋼エネルギーを使う）。v0.82 のポケモンも（リサイクルエネルギー）
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
        if card_id in V0_120_POKEMON:
            # v0.120: サイコデュープ（必要なエネルギーを合わせて照らすワザ）は、合わせた必要なエネルギーを払える相手のワザがないときは選ばない（ワザを使うための条件。エンジンの
            # ``usage_problem`` を、宣言の前に道具が同じ問い合わせで確かめる）
            unusable = [i for i in usable if state.effects.attack_effect(card_id, attacks[i], attacks).usage_problem(state, active) is not None]
            if unusable:
                counts[f"v120_unusable_{card_id}"] += 1
                usable = [i for i in usable if i not in unusable]
                if not usable and isinstance(command, UseAttack):
                    return EndTurn(player)
        if card_id in V0_44:
            # v0.44: 場に出てから 1 度しか使えないワザで、このポケモンがもう使ったもの（場のポケモンの記録）は選ばない
            usable = [i for i in usable if (active.card, i) not in active.attacks_used_once]
            if not usable and isinstance(command, UseAttack):
                counts[f"v044_once_used_end_{card_id}"] += 1
                return EndTurn(player)
        if card_id in V0_104 and usable:
            # v0.104: 相手の対戦ポケモンがねむりのとき、自分をねむりにするワザ（おひるね・ねむる）は選ばない（両方のねむりは、ポケモンチェックの既知の停止
            # UNRESOLVED_POKEMON_CHECK_SLEEP_COIN_ORDER になる。v0.43 のえんかくさいみんと同じ避け方）。ほかに使えるワザがなければ番を終える
            opponent = state.players[1 - player].active
            napping = [i for i in usable if isinstance(state.effects.attack_entry(card_id, i).effect, E.HealAllSelfThenSelfSleep)]
            if opponent is not None and opponent.conditions.asleep:
                awake = [i for i in usable if i not in napping]
                if napping:
                    counts[f"v104_self_sleep_avoided_{card_id}"] += 1
                    if not awake:
                        return EndTurn(player)
                    usable = awake
            elif napping and (active.conditions.poison is not None or active.conditions.confused):
                # v0.104: どく・こんらんのときは、自分をねむりにするワザ（ねむるは回復させる。おひるねはどくが残り、こんらんはねむりで置きかわる）を選ぶ
                counts[f"v104_status_nap_{card_id}"] += 1
                usable = napping
        if not usable:
            return command
        used = _uses_so_far(state, player, card_id)
        if card_id in V0_31 and all(used[i] >= 2 for i in usable) and any(used[a.index] == 0 and a.index not in usable for a in attacks):
            # v0.31: エネルギーをトラッシュするワザ（やまやき・メラメラなど）を使い続けると、エネルギーがたまらず、もう一つのワザが使えるようにならない。
            # 使えるワザをどれも 2 回以上使い、まだ使っていないワザが必要なエネルギーの不足で使えないときは、この番はワザを使わずに番を終える
            counts[f"v031_wait_{card_id}"] += 1
            return EndTurn(player)
        if card_id in V0_38 + V0_39 + V0_40 + V0_41 + V0_42 + V0_43 + V0_44 + V0_45 + V0_46 + V0_47 + V0_48 + V0_51 + V0_52 + V0_58 + V0_64 + V0_70 + V0_72 + V0_75 + V0_76 + V0_77_POKEMON + V0_79 + V0_82_POKEMON + V0_83 + V0_84_POKEMON + V0_85_POKEMON + V0_86_POKEMON + V0_87_POKEMON + V0_88_POKEMON + V0_89_POKEMON + V0_90_POKEMON + V0_91_POKEMON + V0_92_POKEMON + V0_93_POKEMON + V0_94_POKEMON + V0_95_POKEMON + V0_106_POKEMON + V0_107_POKEMON + V0_108_POKEMON + V0_109_POKEMON + V0_110_POKEMON + V0_113_POKEMON + V0_115_POKEMON + V0_116_POKEMON + V0_117_POKEMON + V0_118_POKEMON + V0_119_POKEMON and all(used[i] >= 1 for i in usable) and any(used[a.index] == 0 and a.index not in usable for a in attacks):
            # v0.38: 必要なエネルギーの少ないワザ（でんれい・どくばりタックルなど）を使い続けると、もう一つのワザが使えるようにならない（でんれいは自分を
            # 山札にもどす）。使えるワザをどれも 1 回以上使い、まだ使っていないワザが必要なエネルギーの不足で使えないときは、この番はワザを使わずに番を終える
            # v0.106: 数とコインを組み合わせる 11 枚も同じ手順（すながくれ・かぜおこしなどを使い続けて、ローリングニードル・ネギでつくなどが使えるようにならない。v0.106 のカードの
            # ない局では何もしない）
            # v0.107: コインによる成否・特殊状態・防護の 9 枚も同じ手順（でんきショック・たいあたりなどを使い続けて、そらをとぶ・ダブルラリアットなどが使えるようにならない。v0.107 の
            # カードのない局では何もしない）
            # v0.115: 場・ベンチへのダメージ・配分の 13 枚も同じ手順（たたきつける・しめつけるなどを使い続けて、なぎたおす・ちていいどうなどが使えるようにならない。v0.115 のカードの
            # ない局では何もしない）
            # v0.116: 13 枚も同じ手順（さいせい・トランスダメージはエネルギーカードをすべてトラッシュするので、ようかい・サイコパニックなどを使えるようにためる。v0.116 のカードのない局では
            # 何もしない）
            counts[f"v038_wait_{card_id}"] += 1  # v0.39〜v0.41 のカードも同じ手順（じばく・メガトンパンチ・ギガスパーク・ひのとりなど）
            return EndTurn(player)
        if card_id in V0_111_POKEMON and all(used[i] >= 1 for i in usable) and any(
                used[a.index] == 0 and a.index not in usable and ("attack_index", a.index) not in tried for a in attacks):
            # v0.111: v0.38 と同じ手順（はたく・サイコクラッシュを使い続けて、シンクロウェーブ・ちょうねんりきが使えるようにならない）。ただし、この番にシンクロウェーブを宣言して枚数の違いで
            # 拒否された（``tried`` にある）ときは待たない（相手の枚数は待っても変わらないことがあるので、使えるワザを使う）
            counts[f"v111_wait_{card_id}"] += 1
            return EndTurn(player)
        if card_id in V0_112_POKEMON and all(used[i] >= 1 for i in usable) and any(
                used[a.index] == 0 and a.index not in usable and ("attack_index", a.index) not in tried for a in attacks):
            # v0.112: v0.38 と同じ手順（しょくしゅをつかうを使い続けて、どくばり・ふしょくえきが使えるようにならない）。この番にふしょくえきを「うら」の制限で拒否された（``tried``
            # にある）ときは待たない
            counts[f"v112_wait_{card_id}"] += 1
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
        _v102_attack_observe(state, seen, counts)  # v0.102: ワザを宣言した時点の［グリーンシールド］・［ニュートラルダメージ］の配置
        _v111_attack_observe(state, seen, counts)  # v0.111: ワザを宣言した時点の場のエネルギーカードの枚数
        _v112_attack_observe(state, seen, counts)  # v0.112: しょくしゅをつかうの宣言の時点の「水」の基本エネルギーカード・山札の枚数
        _v113_attack_observe(state, seen, counts)  # v0.113: 処理する時点の場（お互いの場の数・ベンチの名前・悪エネルギー・場の炎・山札のカード）
        # v0.48: この番に、最大HPがのっているダメージ以下に下がる（MH1）ので拒否された手札のカード（進化カード・トレーナー）。この番に拒否がなければ空
        blocked = {marker[1] for marker in tried if isinstance(marker, tuple) and marker[0] == "max_hp_drop_card"}
        if state.phase is Phase.MAIN and (blocked or "trainer_locked" in tried or "evolution_prevented" in tried):
            # v0.46: ［アレルギーかふん］でトレーナーカードを使えない番（この番に TRAINER_PREVENTED で拒否された）。元の手順・重ねた手順に、手札のトレーナーカードを
            # 見せずに選ばせる（同じ拒否を繰り返さない）。この番に拒否がなければ何もしないので、前の版の組の結果は変わらない
            # v0.47: ［げんしのちから］で進化できない番（この番に EVOLUTION_PREVENTED で拒否された）も、手札の進化カードを見せずに選ばせる
            # v0.48: MH1 で拒否された手札のカードも見せない
            view = state.clone()
            _V052_REAL["view"] = view  # v0.117: 手順の中の確かめは、この写しでなく本当の状態で（``_v052_real``）
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
        command = _v120_setup(state, command, counts)  # v0.120: 決められない姿で拒否される対戦準備のバトル場のポケモンを避ける
        command = _v122_unown_aside(state, command, counts)  # v0.122: ［UNDO］・［WANT］のデッキは、バトル場にアンノーンでないポケモンを出す
        if state.phase is Phase.MAIN:
            command = _v057_attack(state, command, tried, counts)  # v0.57: クチバシティジムのコイン
            command = _v088_attack(state, command, tried, counts)  # v0.88: ［すいりょくはつでん］（ワザの宣言といっしょ）
            command = _v122_attack(state, command, tried, counts)  # v0.122: ［ANGER］（［XXXXX］といっしょも）
            command = _v118_attack(state, command, tried, counts)  # v0.118: ［XXXXX］（ワザの宣言といっしょ）
            command = _v119_attack(state, command, tried, counts)  # v0.119: ［めいれい］（ワザの宣言といっしょ）
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
            # v0.127: 途中停止（数量のチェック地点の終端。``Halt.interruption``）は、従来の停止と別に数える（拒否されたので別の操作を試す扱いにしない）
            outcome = "interrupted" if state.halt is not None and state.halt.interruption is not None else "halted"
            result["halt_code"] = next((e["code"] for e in reversed(state.log) if e["kind"] == "halted"), None)
    except AssertionError as error:
        state, observed = seen.get("state"), Counter()
        outcome = "step_limit" if str(error) == driver.STEP_LIMIT else "internal_error"
        result["error"] = str(error)[:500]
    except (IllegalActionError, UnsupportedError) as error:
        state, observed = seen.get("state"), Counter()
        outcome = "unexpected_rejection"
        if error.code in V049_FORM_STOPS and state is not None and state.phase is Phase.SETUP_PLACEMENT:
            # v0.120: 対戦準備でバトル場に出せるたねポケモンが、どれも決められない姿になる（手札のたねポケモンがメタモンだけで、相手のバトル場のポケモンの特殊能力を写す TF1 など）。
            # エンジンは出す操作を受け付けないので、対戦はその前の状態で止まる（v0.49 からの既存の止め方。``_v120_setup`` が別のたねポケモンを試したあと。F120 対 D49 で初めて
            # 起こった）。停止の理由のコードを数える
            outcome = "setup_stopped"
            result["halt_code"] = error.code
        result["error"] = f"{error.code}: {error}"[:500]
    except Exception as error:  # noqa: BLE001  内部エラーも集計から落とさない
        state, observed = seen.get("state"), Counter()
        outcome = "internal_error"
        result["error"] = "".join(traceback.format_exception_only(type(error), error))[:500]
    if state is not None:
        _v102_attack_observe(state, seen, counts)  # v0.102: 最後の番のワザ（このあとに手順が呼ばれない）
        _v111_attack_observe(state, seen, counts)  # v0.111: 同じ
        _v112_attack_observe(state, seen, counts)  # v0.112: 同じ
        _v113_attack_observe(state, seen, counts)  # v0.113: 同じ
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
        result["v083"] = v083_uses(state)
        result["v084"] = v084_uses(state)
        result["v085"] = v085_uses(state)
        result["v086"] = v086_uses(state)
        result["v087"] = v087_uses(state)
        result["v088"] = v088_uses(state)
        result["v089"] = v089_uses(state)
        result["v090"] = v090_uses(state)
        result["v091"] = v091_uses(state)
        result["v092"] = v092_uses(state)
        result["v093"] = v093_uses(state)
        result["v094"] = v094_uses(state)
        result["v095"] = v095_uses(state)
        result["v096"] = v096_uses(state)
        result["v097"] = v097_uses(state)
        result["v098"] = v098_uses(state)
        result["v099"] = v099_uses(state)
        result["v100"] = v100_uses(state)
        result["v101"] = v101_uses(state)
        result["v102"] = v102_uses(state)
        result["v103"] = v103_uses(state)
        result["v104"] = v104_uses(state)
        result["v105"] = v105_uses(state)
        result["v106"] = v106_uses(state)
        result["v107"] = v107_uses(state)
        result["v108"] = v108_uses(state)
        result["v109"] = v109_uses(state)
        result["v110"] = v110_uses(state)
        result["v111"] = v111_uses(state)
        result["v112"] = v112_uses(state)
        result["v113"] = v113_uses(state)
        result["v114"] = v114_uses(state)
        result["v115"] = v115_uses(state)
        result["v116"] = v116_uses(state)
        result["v117"] = v117_uses(state)
        result["v118"] = v118_uses(state)
        result["v119"] = v119_uses(state)
        result["v120"] = v120_uses(state)
        result["v121"] = v121_uses(state)
        result["v122"] = v122_uses(state)
        result["v123"] = v123_uses(state)
        result["v124"] = v124_uses(state)
        result["v125"] = v125_uses(state)
        result["v126"] = v126_uses(state)
        result["v127"] = v127_uses(state)
        result["v129"] = v129_uses(state)
        result["v130"] = v130_uses(state)
        result["v131"] = v131_uses(state)
        result["trainer_sequence_problems"] = driver.trainer_sequence_problems(state)
    result["audit"] = audit(result, state, commands)
    if keep_state:
        result["state"] = state
        result["commands"] = commands
    return result


def audit(result, state, commands):
    """監査の失敗の数（失敗がなければ空）。やり直しと監査は、終わりまで進んだ局（通常の勝敗・サドンデス・停止）だけ。"""
    failures = Counter()
    if state is not None and result["outcome"] == "setup_stopped":
        # v0.120: 対戦準備で止まった局（受け付けた操作は対戦準備だけで、操作の並びは残らない）は、止まる前の状態の不変条件・ログ・保存だけを確かめる
        failures["invariants"] += bool(check_invariants(state))
        failures["log"] += bool(log_problems(state))
        failures["serialization"] += bool(serialization_problems(state))
        return {k: v for k, v in failures.items() if v}
    if state is None or result["outcome"] not in ("game_over", "sudden_death", "halted", "interrupted"):
        return {"not_audited": 1}
    current = new_game(*(deck_cards(label) for label in result["decks"]), result["seed"])
    watch = any(state.cards[uid].card_id in V0_47 + V0_47_TRAINERS + V0_48 + V0_54_TRAINERS + V0_55_TRAINERS + V0_56_TRAINERS + V0_63_TRAINERS + V0_95 + V0_96
                + V0_97 + V0_130 for uid in state.cards)  # v0.48: 観測の今有効な値も（v0.54・v0.55: 見る・見せるトレーナー。v0.95: 手札・山札を見るワザ・特殊能力）
    deck_before: dict[int, int] = {}  # v0.105: ワザの宣言の直前の、ワザを使ったプレイヤーの山札の枚数（宣言を処理する前のログの長さ → 枚数）
    for command in commands:
        if isinstance(command, UseAttack):
            deck_before[len(current.log)] = len(current.players[command.player].deck)
            active = current.players[command.player].active
            if "v106" in result and command.attack_index == 1 and active is not None and current.cards[active.card].card_id == KABUTOPS_NEO2:
                # v0.106: カブトプスのハイドロカッターの宣言の直前の、ついているエネルギーカードの枚数（やり直しの状態で数える。上限 3 枚を超えた場面があったか）
                result["v106"][f"hydro_cards_{E.attached_energy_cards(current, active)}"] += 1
        current = apply_command(current, command)
        if watch:
            failures["observation"] += bool(observation_problems(current))  # v0.47: 受け付けた操作ごとに、プレイヤー・観戦者に渡す観測
    failures["replay_mismatch"] += [dict(e) for e in current.log] != [dict(e) for e in state.log]
    failures["v105_shuffle"] += bool(v105_replay_problems(current, deck_before))
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
         "v082": Counter(), "v082_games_with": Counter(), "v082_policy": Counter(),
         "v083": Counter(), "v083_games_with": Counter(), "v083_policy": Counter(),
         "v084": Counter(), "v084_games_with": Counter(), "v084_policy": Counter(),
         "v085": Counter(), "v085_games_with": Counter(), "v085_policy": Counter(),
         "v086": Counter(), "v086_games_with": Counter(), "v086_policy": Counter(),
         "v087": Counter(), "v087_games_with": Counter(), "v087_policy": Counter(),
         "v088": Counter(), "v088_games_with": Counter(), "v088_policy": Counter(),
         "v089": Counter(), "v089_games_with": Counter(), "v089_policy": Counter(),
         "v090": Counter(), "v090_games_with": Counter(), "v090_policy": Counter(),
         "v091": Counter(), "v091_games_with": Counter(), "v091_policy": Counter(),
         "v092": Counter(), "v092_games_with": Counter(), "v092_policy": Counter(),
         "v093": Counter(), "v093_games_with": Counter(), "v093_policy": Counter(),
         "v094": Counter(), "v094_games_with": Counter(), "v094_policy": Counter(),
         "v095": Counter(), "v095_games_with": Counter(), "v095_policy": Counter(),
         "v096": Counter(), "v096_games_with": Counter(), "v096_policy": Counter()}
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
        s["v083"].update(r.get("v083", {}))  # v0.83
        s["v083_games_with"].update({k: 1 for k, v in r.get("v083", {}).items() if v})
        s["v083_policy"].update({k: v for k, v in r.get("policy", {}).items() if k.startswith("v083_")})
        s["v084"].update(r.get("v084", {}))  # v0.84
        s["v084_games_with"].update({k: 1 for k, v in r.get("v084", {}).items() if v})
        s["v084_policy"].update({k: v for k, v in r.get("policy", {}).items() if k.startswith("v084_")})
        s["v085"].update(r.get("v085", {}))  # v0.85
        s["v085_games_with"].update({k: 1 for k, v in r.get("v085", {}).items() if v})
        s["v085_policy"].update({k: v for k, v in r.get("policy", {}).items() if k.startswith("v085_")})
        s["v086"].update(r.get("v086", {}))  # v0.86
        s["v086_games_with"].update({k: 1 for k, v in r.get("v086", {}).items() if v})
        s["v086_policy"].update({k: v for k, v in r.get("policy", {}).items() if k.startswith("v086_")})
        s["v087"].update(r.get("v087", {}))  # v0.87
        s["v087_games_with"].update({k: 1 for k, v in r.get("v087", {}).items() if v})
        s["v087_policy"].update({k: v for k, v in r.get("policy", {}).items() if k.startswith("v087_")})
        s["v088"].update(r.get("v088", {}))  # v0.88
        s["v088_games_with"].update({k: 1 for k, v in r.get("v088", {}).items() if v})
        s["v088_policy"].update({k: v for k, v in r.get("policy", {}).items() if k.startswith("v088_")})
        s["v089"].update(r.get("v089", {}))  # v0.89
        s["v089_games_with"].update({k: 1 for k, v in r.get("v089", {}).items() if v})
        s["v089_policy"].update({k: v for k, v in r.get("policy", {}).items() if k.startswith("v089_")})
        s["v090"].update(r.get("v090", {}))  # v0.90
        s["v090_games_with"].update({k: 1 for k, v in r.get("v090", {}).items() if v})
        s["v090_policy"].update({k: v for k, v in r.get("policy", {}).items() if k.startswith("v090_")})
        s["v091"].update(r.get("v091", {}))  # v0.91
        s["v091_games_with"].update({k: 1 for k, v in r.get("v091", {}).items() if v})
        s["v091_policy"].update({k: v for k, v in r.get("policy", {}).items() if k.startswith("v091_")})
        s["v092"].update(r.get("v092", {}))  # v0.92
        s["v092_games_with"].update({k: 1 for k, v in r.get("v092", {}).items() if v})
        s["v092_policy"].update({k: v for k, v in r.get("policy", {}).items() if k.startswith("v092_")})
        s["v093"].update(r.get("v093", {}))  # v0.93
        s["v093_games_with"].update({k: 1 for k, v in r.get("v093", {}).items() if v})
        s["v093_policy"].update({k: v for k, v in r.get("policy", {}).items() if k.startswith("v093_")})
        s["v094"].update(r.get("v094", {}))  # v0.94
        s["v094_games_with"].update({k: 1 for k, v in r.get("v094", {}).items() if v})
        s["v094_policy"].update({k: v for k, v in r.get("policy", {}).items() if k.startswith("v094_")})
        s["v095"].update(r.get("v095", {}))  # v0.95
        s["v095_games_with"].update({k: 1 for k, v in r.get("v095", {}).items() if v})
        s["v095_policy"].update({k: v for k, v in r.get("policy", {}).items() if k.startswith("v095_")})
        s["v096"].update(r.get("v096", {}))  # v0.96
        s["v096_games_with"].update({k: 1 for k, v in r.get("v096", {}).items() if v})
        s["v096_policy"].update({k: v for k, v in r.get("policy", {}).items() if k.startswith("v096_")})
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

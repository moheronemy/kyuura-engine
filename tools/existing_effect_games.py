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
    EndTurn, EvolvePokemon, IllegalActionError, Phase, PlayTrainer, ResolveDecision, Retreat, UnsupportedError, UseAttack, UsePokemonPower, apply_command,
    check_invariants, max_hp, new_game, preset_deck,
)
from kyuura_engine.cards import EnergyType, can_pay_cost  # noqa: E402
from kyuura_engine.commands import DiscardFromPlay  # noqa: E402
from kyuura_engine.decisions import (  # noqa: E402
    ARRANGE_DECK_TOP, PEEK_CARD, SELECT_DECK_OWNER, SELECT_HAND_CARD, SELECT_LOOK_COUNT, SELECT_PRIZE_CARD,
    ATTACH_FROM_DECK, ATTACH_FROM_DISCARD, ATTACH_FROM_HAND, BENCH_FROM_DECK, DISCARD_ENERGY, DISCARD_FROM_HAND, DISCARD_TO_DECK_TOP, ENTRY_POWER, FORCED_SWITCH, HAND_TO_DECK,
    MOVE_ENERGY, MOVE_OPPONENT_ENERGY, RECOVER_POKEMON,
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
from kyuura_engine.decisions import BENCH_FROM_DISCARD  # noqa: E402  v0.51
from kyuura_engine.effects import bench_from_discard_candidates  # noqa: E402  v0.51
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
# 決められない姿・MH1 で拒否される操作のコード（v0.49。場から確かめてから別の操作を続ける）
V049_FORM_STOPS = ("UNRESOLVED_TRANSFORM_COPIED_POWER", "UNRESOLVED_TRANSFORM_MODIFIED_DEFENDER", "UNRESOLVED_SHAPESHIFT_SUPPRESSED",
                   "UNRESOLVED_MAX_HP_DROP")
TARGETS = (V0_28 + V0_29 + V0_30 + V0_31 + V0_32 + V0_33 + V0_34 + V0_35 + V0_36 + V0_37 + V0_38 + V0_39 + V0_40 + V0_41 + V0_42 + V0_43
           + V0_44 + V0_45 + V0_46 + V0_47 + V0_48 + V0_49 + V0_50 + V0_51)  # ワザの選び方を重ね、動きを数えるカード
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
BATCHES = {"v0.28": PAIRINGS, "v0.29": PAIRINGS_V0_29, "v0.30": PAIRINGS_V0_30, "v0.31": PAIRINGS_V0_31, "v0.32": PAIRINGS_V0_32,
           "v0.33": PAIRINGS_V0_33, "v0.34": PAIRINGS_V0_34, "v0.35": PAIRINGS_V0_35, "v0.36": PAIRINGS_V0_36, "v0.37": PAIRINGS_V0_37,
           "v0.38": PAIRINGS_V0_38, "v0.39": PAIRINGS_V0_39, "v0.40": PAIRINGS_V0_40, "v0.41": PAIRINGS_V0_41, "v0.42": PAIRINGS_V0_42,
           "v0.43": PAIRINGS_V0_43, "v0.44": PAIRINGS_V0_44, "v0.45": PAIRINGS_V0_45, "v0.46": PAIRINGS_V0_46, "v0.47": PAIRINGS_V0_47,
           "v0.48": PAIRINGS_V0_48, "v0.49": PAIRINGS_V0_49, "v0.50": PAIRINGS_V0_50, "v0.51": PAIRINGS_V0_51}
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
V031_STOPS = {
    # v0.49: ［へんしん］のメタモンが、タイプのエネルギーの数を数える・トラッシュするワザを使う（どの色としても数えるかが決まらない。TE1）
    "UNRESOLVED_TRANSFORM_ENERGY_COUNT": lambda st, c: any_color_energy(st, _attacker(st, c)),
    "UNRESOLVED_DISCARD_ENERGY_TIMING": lambda st, c: _attacker(st, c).conditions.confused,  # HC1
    # HC4（第4弾のコダック・v0.34 のシャワーズの「みずでっぽう」）
    "UNRESOLVED_EXTRA_ENERGY_COLORLESS": lambda st, c: type(_attack_effect(st, c)).__name__ == "ExtraEnergyDamageMixed",
    "UNRESOLVED_PREVENTED_EFFECT_COIN": lambda st, c: attack_barrier(st, _defender(st, c)) is not None,  # HC3
    "UNRESOLVED_DESTINY_BOND_KNOCKOUT": lambda st, c: destiny_bond(st, _defender(st, c)) is not None,  # HC2
    # しっぽをふる。v0.40: すごむ（効果を与えたポケモンがバトル場にいる間）
    "ATTACK_PREVENTED": lambda st, c: (cannot_attack(st, _attacker(st, c)) is not None
                                       or cannot_attack_while_source_active(st, _attacker(st, c)) is not None),
    "UNRESOLVED_DISCARD_DECK_SHORT": lambda st, c: (  # HC6: マグマふんしゅつ（自分の山札 5 枚未満）・やまやき（相手の山札 0 枚）
        (_attack_definition(st, c).id, c.attack_index) == (BLAINES_MAGMAR, 1) and len(st.players[c.player].deck) < 5
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
                                 and len(st.players[c.player].bench) >= st.rules.max_bench),
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
    "UNRESOLVED_MULTIPLE_ATTACK_CHECKS": lambda st, c: len(attack_coin_checks(st, _attacker(st, c))) >= 2,
    # v0.45: 相手の対戦ポケモンが返す効果（クロスカウンター。ほのおのかべ・こうらがえしも）を持ち、そろってきぜつしうる（W24・S37）
    "UNRESOLVED_RETALIATION_DOUBLE_KNOCKOUT": lambda st, c: retaliation(st, _defender(st, c)) is not None,
    # v0.48: ［へんしょく］で変えた色の読み方が 2 つある（使った番のあと・ベンチにもどったあと・この力が消えている）場のポケモンがいる（VS1。読み方で結果が変わるときだけ
    # 止まる。止まらない場合は場から確かめられないので、止まったときに読み方が 2 つあるポケモンがいることだけを確かめる）
    "UNRESOLVED_SHIFT_COLOR_DURATION": lambda st, c: any(len(type_readings(st, p)) > 1 for pl in st.players for p in pl.in_play()),
    # v0.50: たいかビーム（自分のワザ・相手のワザとして使うワザ）で、自分・相手の場の進化ポケモンがどれも「ばける」でのせたカードのポケモン（DV5）
    "UNRESOLVED_DEVOLUTION_TARGET_DISGUISED": lambda st, c: _all_devolution_targets_disguised(st, c),
    # v0.48: テクスチャー1（相手の対戦ポケモンに弱点がない）・テクスチャー2（自分に抵抗力がない）。相手のワザとして使うワザなら、相手の対戦ポケモンのワザのどれか（PG1）
    "UNRESOLVED_CHANGE_ABSENT_WEAKNESS_RESISTANCE": lambda st, c: _conversion_absent(st, c),
}


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
            if amount is None or amount <= 0:
                return True
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
    if "trainer_locked" in tried or len(p.bench) >= state.rules.max_bench:
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
            card = state.card_def(pokemon.card)
            if card.id in V0_48 and card.hp is not None and max_hp(state, pokemon) != card.hp:
                counts[f"v048_max_hp_{card.id}_{'over_printed' if pokemon.damage >= card.hp else 'raised'}"] += 1


def _v048_power(state, tried, counts):
    """v0.48 の宣言する特殊能力を使う手順: モルフォンの［へんしょく］（この番にまだ使っておらず、ねむり・マヒ・こんらんでなく、決まって場にいる色があるとき。
    バトル場・ベンチのどちらでも使う）。拒否を起こさない。"""
    player = state.current_player
    p = state.players[player]
    for pokemon in p.in_play():
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


def _v044_power(state, tried, counts):
    """v0.44 の宣言する特殊能力を使う手順: キョウのコクーンの［うか］（この番にまだ使っておらず、ねむり・マヒ・こんらんでなく、その番の最初から場にいて、おたがいの最初の番
    でないとき。山札にキョウのスピアーがなくても 2 回までは使う（「おもて」で重ねられない場合を起こす））。拒否を起こさない。"""
    player = state.current_player
    p = state.players[player]
    if state.turn_number <= 2:
        return None
    for pokemon in p.in_play():
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
            early = (_v043_decision(state, counts) or _v044_decision(state, counts)  # v0.44 の決定も元の手順より先に答える
                     or _v045_decision(state, counts) or _v046_decision(state, counts)  # v0.45・v0.46 の決定も
                     or _v047_decision(state, counts) or _v048_decision(state, counts)  # v0.47・v0.48
                     or _v049_decision(state, counts) or _v050_decision(state, counts)  # v0.49・v0.50
                     or _v051_decision(state, counts))  # v0.51
            if early is not None:
                return early
        command = base(state, janken_winner=janken_winner, cure=cure, tried=tried)
        if state.phase is Phase.DECISION:
            return (_v031_decision(state, counts) or _v039_decision(state, counts) or _v040_decision(state, counts) or _v041_decision(state, counts)
                    or _v042_decision(state, counts) or command)
        if state.phase is Phase.MAIN and isinstance(command, (UseAttack, EndTurn)):
            power = (_v031_power(state, tried, counts) or _v042_power(state, tried, counts) or _v043_power(state, tried, counts)
                     or _v044_power(state, tried, counts) or _v044_trainer(state, tried, counts)
                     or _v047_power(state, tried, counts) or _v047_trainer(state, tried, counts)  # v0.47
                     or _v048_power(state, tried, counts)  # v0.48
                     or _v049_power(state, tried, counts) or _v049_trainer(state, tried, counts)  # v0.49
                     or _v050_trainer(state, tried, counts) or _v051_trainer(state, tried, counts))  # v0.50・v0.51
            if power is not None:
                return power
            virtual = _v049_attack(state, tried, counts)  # v0.49: 出どころがいちばん上のカードでないワザ
            if virtual is not None:
                return virtual
            probe = _v036_retreat_probe(state, tried, counts)  # v0.36
            if probe is not None:
                return probe
            retreat = _v046_retreat(state, tried, counts)  # v0.46
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
        if card_id in V0_38 + V0_39 + V0_40 + V0_41 + V0_42 + V0_43 + V0_44 + V0_45 + V0_46 + V0_47 + V0_48 + V0_51 and all(used[i] >= 1 for i in usable) and any(used[a.index] == 0 and a.index not in usable for a in attacks):
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
        return _v049_answer(state, command, counts)  # v0.49: 決められない姿・MH1 で拒否される決定の答えを避ける

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
    watch = any(state.cards[uid].card_id in V0_47 + V0_47_TRAINERS + V0_48 for uid in state.cards)  # v0.48: 観測の今有効な値も
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
    uses = {cid: Counter() for cid in TARGETS + V0_47_TRAINERS + V0_49_TRAINERS + V0_50_TRAINERS + V0_51_TRAINERS}
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

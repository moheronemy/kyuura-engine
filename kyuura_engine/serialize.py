"""ゲーム状態を JSON にできる辞書にする（画面やほかの言語に渡すため・テストで比べるため）。

形式は 27 あります（``format_version``）。

- 1（既定）: v0.1 と同じ形。v0.1 の固定値のテストと互換性の参照データは、この形で比べる。
- 2: 1 に次を加えたもの（v0.2a）。``format_version``、``effects``（効果の登録表の id）、
  ``next_pokemon_id``、``next_decision_id``、``decision``（保留中の決定）、場のポケモンごとの ``pokemon_id``。
- 3: 2 に ``trainer_in_use``（使っている最中のトレーナーカード）を加えたもの（v0.2b）。
- 4: 3 に、場のポケモンごとの ``trainers``（ついているトレーナーカード）を加えたもの（v0.2c）。
- 5: 4 に、場のポケモンごとの ``special_conditions``（特殊状態。どくなら ``{"poison": {"damage": 10}}``、
  なければ ``{}``）を加えたもの（v0.3a）。v0.3b で、ねむり ``"sleep": {}``・マヒ ``"paralysis": {"turn": n}``
  （``n`` はマヒ状態になった番。回復する番はここから決まる）の項目を加えた。どくだけの状態・特殊状態のない状態の
  書き出しは v0.3a と同じ（項目の意味を変えていないので形式 6 にはしていない。知らない項目のある辞書は、読む側が
  拒否すること）。v0.3c で、こんらん ``"confusion": {}`` の項目を同じ理由で加えた。
- 6: 5 に、場のポケモンごとの ``retreat_failed_turn``（こんらん状態で「にげる」に失敗した番。なければ ``None``。
  そのポケモンは、その番の間「にげる」を宣言できない。p.311）を加えたもの（v0.3c）。
- 7: 6 に、場のポケモンごとの ``evolution_stack``（いちばん上のカードの下に重なっているポケモンのカード。下から順に
  ``{"card": uid, "card_id": id}``。進化していなければ ``[]``）・``played_turn``（場に出た番。対戦準備なら 0）・
  ``evolved_turn``（いまの姿に進化した番。進化していなければ ``None``）を加えたもの（v0.4a）。``card``・``card_id``・
  ``name``・``hp`` はいちばん上のカード（そのポケモンを表すカード。p.310）。v0.4c の 2 進化では ``evolution_stack`` が
  2 つ（たねポケモン・1 進化ポケモンの順）になるだけで、項目と意味は同じ（形式 8 のまま。docs/stage2-state-v0.4c.md）。
- 8: 7 に、場のポケモンごとの ``persistent_effects``（ワザによる持続する効果。v0.4b。p.322・p.323）を加えたもの。
  1 つにつき ``{"effect": 種類, "source_card": uid, "source_card_id": id, "source_player": プレイヤー,
  "created_turn": 効果を与えた番, "active_turn": はたらく番}``。v0.4b の種類は ``"prevent_damage"``（「かたまる」の
  「次の相手の番、このカードはダメージを受けない」。はたらく番の終わりに消える）だけ。なければ ``[]``。v0.12 で種類
  ``"retaliation"``（R団のファイヤーの「ほのおのかべ」の「次の相手の番、このカードが相手のワザによるダメージを受けたとき、…相手に
  10ダメージを与える」。はたらく番の終わりに消える）を加え、その種類だけ ``"attack_index"``（効果を与えたワザの位置）・``"amount"``
  （与えるダメージ）を加える（項目の意味を変えていないので形式 9 のまま。docs/architecture-v0.12.md 5 章）。v0.13 で種類
  ``"retaliation_received_damage"``（わるいカメールの「こうらがえし」の「…そのポケモンにも同じダメージを与える」。与えるダメージは
  受けたダメージで決まる）を加え、その種類は ``"attack_index"`` だけを加える（形式 9 のまま。docs/architecture-v0.13.md 5 章）。
  v0.27 で種類 ``"next_turn_attack_damage"``（ストライクの「つるぎのまい」の「次の自分の番、このカードが使う「きりさく」のダメージは「60」に
  なる」。はたらく番は次の自分の番（``created_turn`` + 2）で、その番の終わりに消える）を加え、その種類だけ ``"attack_index"``（効果を与えた
  ワザの位置）・``"target_attack_index"``（ダメージが変わるワザの位置）・``"amount"``（変えたあとのダメージ）を加える（項目の意味を変えて
  いないので形式 9 のまま。docs/scyther-v0.27.md）。
- 9: 8 に、``energy_attached_by_powers_this_turn``（この番に、ポケモンパワーの効果で手札から場のポケモンにつけたエネルギー
  カードの枚数。v0.6 のカメックスの「あまごい」。手札からつける通常の操作の回数 ``energy_attachments_this_turn`` とは別。
  番の最初に 0）を加えたもの（v0.6。docs/architecture-v0.6.md 5 章）。この数が 1 以上の番には、通常の操作が原典で決められない
  （``UNRESOLVED_ATTACH_AFTER_POWER_ATTACH``）ので、状態に持ち、書き出しで表す。形式 1〜8 は、この数が 0 でなければ
  ``ValueError``（0 なら形式 1〜8 の書き出しは v0.5 と同じ）。
- 10: 9 に、``power_uses_this_turn``（この番に使った「自分の番ごとに1回使える」特殊能力。[場のポケモンの番号, 特殊能力の位置] の並び。
  v0.31 のカツラのロコンの「しぜんになおる」。番の最初に空）と ``energy_burn``（この番に「炎」エネルギーになったエネルギーカード。
  [場のポケモンの番号, エネルギーカードの uid] の並び。v0.31 のリザードンの「エナジーバーン」。番の終わりに空）を加えたもの（v0.31。
  docs/held-cards-v0.31.md）。形式 1〜9 は、どちらかが空でなければ ``ValueError``（空なら形式 1〜9 の書き出しは v0.30 と同じ）。
  v0.31 の持続する効果の種類 ``"destiny_bond"``（みちづれ）・``"attack_barrier"``（バリアー）・``"damage_reduction"``（ちいさくなる。
  ``"amount"`` を加える）・``"cannot_attack"``（しっぽをふる。相手に与える効果で、``source_card``・``source_player`` は効果を与えたワザを
  使ったポケモンのカードとプレイヤー）は、v0.27 と同じく形式 8 の ``persistent_effects`` の種類の値を加えただけ（形式は変えない）。
- 11: 10 に、場のポケモンごとの ``attacks_used_once``（「このワザは、このカードが場に出てから、1回しか使えない」ワザを、この場のポケモンが使った記録。
  [ワザを持つカードの uid, ワザの位置] の並び。なければ ``[]``）と ``evolution_permission_turn``（トレーナー「サカキ」で、場に出た番・進化した番でも
  進化させてよい番。なければ ``None``。番の終わりに消える）を加えたもの（v0.44。docs/search-evolution-once-attacks-v0.44.md 3 章）。形式 1〜10 は、どちらかが
  空でない・None でないポケモンがいると ``ValueError``（なければ形式 1〜10 の書き出しは v0.43 と同じ）。使った記録はログから数えず状態に持つので、書き出しにも
  加えた（場をはなれるまで残る）。
- 12: 11 に、``trainer_locks``（プレイヤーに与えた、期限のあるトレーナーカードの使用の禁止。コダックの「ずつう」・マチスのサンダースの「こうしゅうは」。
  ``{"player", "source_player", "source_card", "source_card_id", "effect", "created_turn", "expires_turn"}`` の並び（与えた順）。なければ ``[]``）を加えたもの
  （v0.47。docs/fossil-hidden-info-v0.47.md 5 章）。形式 1〜11 は、禁止があると ``ValueError``（なければ形式 1〜11 の書き出しは v0.46 と同じ）。禁止は場のポケモンの
  持続する効果ではなくプレイヤーの記録なので、ポケモンの項目ではなく最上位の項目にした（消える番の終わりに消える）。v0.47 のなにかの化石・ピッピ人形は、場に
  いるあいだも書き出しの形を変えない（場のポケモンの ``card``・``card_id`` はそのカード。ポケモンとしてあつかうことは、状態の定義（``GameState.card_def``）が決める）。
- 13: 12 に、場のポケモンごとの ``type_shift``（特殊能力で色（タイプ）を変えた記録。モルフォンの［へんしょく］。``{"color", "turn", "source_card",
  "source_card_id", "returned_to_bench"}``、なければ ``None``）を加えたもの（v0.48。docs/effective-pokemon-properties-v0.48.md 7 章）。形式 1〜12 は、記録のある
  ポケモンがいると ``ValueError``（なければ形式 1〜12 の書き出しは v0.47 と同じ）。変えた色が今有効かは、記録・番・場所・特殊状態・かがくへんかガスから求める（VS1。
  状態の項目にしない）ので、記録だけを書く。v0.48 の持続する効果の種類 ``"weakness_change"``・``"resistance_change"``（ポリゴンの「テクスチャー1」「テクスチャー2」。
  ``color`` を加える）・``"max_hp_set"``（キョウのメタモンの「きょだいか」。``amount`` を加える）は、形式 8 の ``persistent_effects`` の種類の値を加えただけ（形式は
  変えない。v0.47 までの書き出しを読む側は、知らない種類として拒否すること）。場のポケモンの ``hp`` は、これまでどおりいちばん上のカード（場での役割を含むカードの
  定義）の HP で、今有効な最大HP（［ガスのからだ］・「きょだいか」）ではない（今有効な値は状態から求める値で、観測 ``observation.observe`` が書く）。
- 14: 13 に、場のポケモンごとの ``disguise``（タケシのキュウコンの「ばける」でのせた進化カード。``{"card", "card_id"}``、なければ ``None``）と、最上位の
  ``recalls``（この番に使った「思い出させる」の記録。``{"player", "turn", "pokemon_id", "card", "card_id", "trainer", "trainer_card_id"}`` の並び。なければ ``[]``）を
  加えたもの（v0.49。docs/virtual-attacks-transformation-v0.49.md 8 章）。持続する効果は、ワザの出どころがワザを使ったポケモンのいちばん上のカードと違うとき
  （［サイコリンク］・［へんしん］・「ばける」・「思い出させる」で使ったワザ）だけ ``attack_card``（効果を与えたワザを印刷したカードの id）、「ドわすれ」で
  受けたポケモンのいちばん上のカードでないワザを選んだときだけ ``target_attack_card`` を加える。``power_uses_this_turn`` には、のせたカードの特殊能力を使った記録
  （[場のポケモンの番号, 特殊能力の位置, そのカードの uid]）が入る。形式 1〜13 は、のせたカード・記録・その項目のある効果・3 つの値の使用の記録があると
  ``ValueError``（なければ形式 1〜13 の書き出しは v0.48 と同じ）。今の姿（［へんしん］で同じカードとしてあつかう相手のカードなど）・今使えるワザは、状態から求める
  値なので書かない（観測 ``observation.observe`` が書く）。
- 15: 14 に、場のポケモンごとの ``devolved_turn``（最後に退化した番。退化していなければ ``None``）を加えたもの（v0.50。ミュウの「たいかビーム」・退化スプレー。
  docs/mew-devolution-spray-v0.50.md 7 章）。``power_uses_this_turn`` の 3 つの値の記録に、いちばん上のカードとして使ったあとで進化・退化していちばん上でなくなった
  カードの記録（[場のポケモンの番号, 特殊能力の位置, 使ったカードの uid]。``evolution.retag_power_uses``）が入る。形式 1〜14 は、退化した番のあるポケモン・その記録
  （今の番の特殊能力の宣言のログが「ばける」でのせたカードの使用でない 3 つの値の記録）があると ``ValueError``（なければ形式 1〜14 の書き出しは v0.49 と同じ）。
- 16: 15 に、最上位の ``trainer_effects``（トレーナーを使ったプレイヤーに与えた期限のある効果。カスミ・キョウ・見えない壁。``{"kind", "player", "source_card",
  "card_id", "created_turn", "expires_turn"}`` の並び）を加え、``trainer_locks`` の禁止に出どころ ``origin``（``"attack"``・``"trainer"``。ロケット団の実験の「うら」）を
  加えたもの（v0.56。docs/trainer-decisions-turn-effects-v0.56.md 8 章）。形式 1〜15 は、期限のあるトレーナーの効果・トレーナーの効果の禁止があると ``ValueError``
  （なければ形式 1〜15 の書き出しは v0.55 と同じ。ワザの禁止だけなら形式 12〜15 で今までどおり書ける）。
- 17: 16 に、最上位の ``stadium``（場に出ているスタジアム。``{"owner", "card", "card_id", "placed_turn"}`` か ``None``）・``stadium_uses_this_turn``
  （この番にスタジアムの効果を使った記録。[プレイヤー, スタジアムのカードの uid] の並び）と、``trainer_in_use`` の ``user``（錯乱ジムで相手プレイヤーが
  借りて使っているときの使っているプレイヤー。持ち主が使っていれば ``None``）を加えたもの（v0.57。docs/stadiums-v0.57.md 8 章）。形式 1〜16 は、場に
  スタジアムがある・使った記録がある・借りて使っている最中のトレーナーがあると ``ValueError``（なければ形式 1〜16 の書き出しは v0.56 と同じ）。
- 18: 17 に、最上位の ``trainer_stack``（内側のトレーナーを使い終わるのを待っている外側のトレーナーの使用。``{"player", "card", "card_id", "user", "via"}`` の並び。
  外側から順）と、``trainer_in_use`` の ``via``（外側のトレーナー（ナツメのサイキックコントロール）の効果で相手のトラッシュから使っているときの、外側のカードの uid。
  手札から使っていれば ``None``）を加えたもの（v0.58。docs/stadium-reuse-special-energy-v0.58.md 7 章）。形式 1〜17 は、外側のトレーナーの使用・相手のトラッシュから
  使っている最中のトレーナーがあると ``ValueError``（なければ形式 1〜17 の書き出しは v0.57 と同じ）。
- 19: 18 に、最上位の ``energy_roles``（エネルギーとしてついているカードの記録。マルマインの［エネエネ］。``{"card", "card_id", "energy_type", "units", "owner",
  "turn"}`` の並び）を加えたもの（v0.59。docs/energy-control-power-suppression-v0.59.md 8 章）。形式 1〜18 は、記録があると ``ValueError``（なければ形式 1〜18 の
  書き出しは v0.58 と同じ）。v0.59 の持続する効果の種類 ``"cannot_use_powers"``（「ショックアイ」）・``"cannot_attach_energy"``（「クリスタルビーム」）は共通の項目だけで、
  形式 8 から書ける（種類の値を加えただけ）。タケシの保護（場をはなれるまでついたまま）のついているトレーナーの ``discard_at_end_of_turn`` は ``None``。
  v0.60: 持続する効果の種類 ``"tails_damage_guard"``（R団のストライクの「かげぶんしん」）も共通の項目だけで、形式 8 から書ける（形式は増やしていない）。
- 20: 19 に、場のポケモンごとの ``history``（ワザの履歴。``{"kind": "used", "turn", "card", "declared", "processed"}``・``{"kind": "received", "turn", "card", "player",
  "source", "declared", "processed", "damage", "reached", "voided"}``・``{"kind": "other_received", "turn", "card"}`` の並び。ワザは [カード id, 位置]）を加えたもの（v0.62。
  docs/history-attacks-v0.62.md 9 章）。履歴を読むワザのカードが対戦にないときは記録しないので空。形式 1〜19 は、記録があると ``ValueError``（なければ形式 1〜19 の
  書き出しは v0.61 と同じ）。
- 21: 20 に、最上位の ``set_aside``（一時的に置いておくカードのまとまり。``{"kind", "owner", "cards", "card_ids", "visible_to", "user", "trainer_card", "card_id",
  "created_turn", "return_turn"}`` の並び。くすぐりマシーン・たたきつけろ!挑戦状・カツラのクイズ その3）・``face_up_prizes``（おもてになっているサイドのカードの uid の並び。
  ロケット団参上!）を加えたもの（v0.63。docs/hidden-card-trainers-v0.63.md 7 章）。内部の完全な記録なので、置いたカード・おもてのサイドのカードを書く（プレイヤーに渡す
  ときは観測 ``observation.observe`` を使う）。形式 1〜20 は、どちらかがあると ``ValueError``（なければ形式 1〜20 の書き出しは v0.62 と同じ）。

- 22: 21 に、最上位の ``face_down_cards``（うらにしてベンチに出したカードの uid の並び。マチスの秘策）を加えたもの（v0.67。docs/secret-plan-preflight-v0.67.md 7 章）。
  内部の完全な記録なので、場のポケモンの ``card_id``・``name``・``hp`` は本当のカードの値を書く（プレイヤーに渡すときは観測 ``observation.observe`` を使う）。形式 1〜21 は、
  うらのカードがあると ``ValueError``（なければ形式 1〜21 の書き出しは v0.66 と同じ）。
  v0.86: 持続する効果の種類 ``"powers_stopped"``（わるいモココの「スタンウェーブ」）・``"bench_protection"``（エンテイ PF2-008 の「ほのおのまもり」）は共通の項目だけで、
  形式 8 から書ける（形式は増やしていない）。v0.114: ``"bench_powers_stopped"``（ププリンの［じっとみる］。特殊能力で与えた効果。``source_card`` は特殊能力を使ったポケモン）も
  共通の項目だけ（形式は増やしていない）。反応の続き（決定の ``context`` の ``followup``・``reaction``）は既存の ``decision`` の項目で書く。
- 23: 22 に、最上位の ``color_effects``（特殊能力で、この番が終わるまで色を変える効果。``{"kind", "player", "source", "source_card", "card_id", "power_index", "target",
  "color", "turn", "left_play"}`` の並び。ランターンの［せんすい］・ポリゴン2の［エナジーコンバーター］）を加えたもの（v0.88。docs/type-energy-colors-v0.88.md 2 章）。形式 1〜22 は、
  その効果があると ``ValueError``（なければ形式 1〜22 の書き出しは v0.87 と同じ）。
- 24: 23 に、場のポケモンごとの ``markers``（のっているマーカー・ダメージカウンター以外のカウンター。のせた順に ``{"kind", "player", "source_card", "source_card_id", "effect",
  "turn"}``、色マーカーだけ ``"color"`` を加える。なければ ``[]``）を加えたもの（v0.90。docs/markers-counters-v0.90.md 3 章）。形式 1〜23 は、マーカー・カウンターがあると
  ``ValueError``（なければ形式 1〜23 の書き出しは v0.89 と同じ）。
  v0.92・v0.93: 期間を明示した持続する効果（v0.92 の ``"period_retreat_lock"``・``"period_attack_lock"``・``"received_attack_damage_bonus"``、v0.93 の ``"period_leave_lock"``
  （「バトル場をはなれられない」。あるときだけ ``"knockout_exception"``・``"source_left"``）・``"period_attack_coin_check"``（かぶりつく））は、形式 8 の ``persistent_effects`` の
  種類の値と種類ごとの項目を加えただけ（形式は 24 のまま。docs/active-leave-locks-v0.93.md 11 章。前の版の書き出しを読む側は、知らない種類として拒否すること）。
  v0.108: 期間を明示した持続する効果の種類 ``"dealt_attack_damage_reduction"``（マイナスイオン・あまえる。使うワザのダメージを減らす数 ``"amount"`` を加える）も、同じく種類の値と
  項目を加えただけ（形式は 26 のまま。v0.107 までの書き出しを読む側は、知らない種類として拒否すること。docs/damage-modifiers-condition-bonuses-v0.108.md 7 章）。
  v0.109: 持続する効果の種類 ``"timed_damage_guard"``（ぬるぬる・かわす・ブリンク。``"prevent_on"``・``"flipper"``・``"scope"`` を加える）も、同じく種類の値と項目を加えただけ（形式は
  26 のまま。v0.108 までの書き出しを読む側は、知らない種類として拒否すること。docs/timed-damage-guards-v0.109.md 7 章）。
  v0.110: 持続する効果の種類 ``"knockout_survival"``（こらえる・こうてつか。``"end_turn"``・``"scope"``・``"remaining_hp"`` を加える）も、同じく種類の値と項目を加えただけ（形式は
  26 のまま。v0.109 までの書き出しを読む側は、知らない種類として拒否すること。docs/endure-armor-up-v0.110.md 8 章）。
  v0.116: 持続する効果の種類 ``"status_on_energy_attach"``（しこみどく・エナジーショック。``"condition"``・``"attack"`` を加える）・``"evolution_lock"``（やみのしょくしゅ。共通の項目だけ）も、
  同じく種類の値と項目を加えただけ（形式は 26 のまま。v0.115 までの書き出しを読む側は、知らない種類として拒否すること。docs/energy-movement-attachment-devolution-v0.116.md 8 章）。
  v0.114: 持続する効果の種類 ``"bench_powers_stopped"``（じっとみる。共通の項目だけ）も、同じく種類の値を加えただけ（形式は 26 のまま。v0.113 までの書き出しを読む側は、知らない
  種類として拒否すること。docs/baby-rules-evolution-v0.114.md 7 章）。ベイビィポケモンの段階・進化先・重なりのいちばん下のベイビィポケモンカードは、カードの id とカードのデータで
  決まるので、書き出しの項目は変えていない（ブビィの「モクモク」の期限は、既存のトレーナーの効果の ``expires_turn``）。
- 25:24 の場のポケモンの ``history`` の受けた記録（``"kind": "received"``）に、``active_damage``（受けたダメージ ``damage`` のうち、受けた時に持ち主のバトル場にいた分。場所の
  分からない記録の写しは ``None``）を加えたもの（v0.99。docs/unown-perform-help-history-v0.99.md 6 章）。形式 20〜24 の受けた記録は合計だけなので、場所の分かる 0 より大きい
  ダメージの記録があると ``ValueError``（合計が 0 の記録・場所の分からない記録だけなら形式 20〜24 の書き出しは v0.98 と同じ。形式 24 の受けた記録を読む側は、合計が 0 より大きい
  記録の場所を分からないものとして読み、すべてバトル場・すべてベンチにしないこと）。
- 26: 25 に、最上位の ``turn_history``（プレイヤーの番ごとの記録。番の順に、使ったワザ ``{"kind": "turn_attack", "turn", "player", "pokemon_id", "card", "declared", "processed"}``
  と、番でないプレイヤーの場にいたカード ``{"kind": "turn_field", "turn", "player", "cards", "face_down"}``）を加えたもの（v0.100。docs/sketch-perish-song-history-v0.100.md 7 章）。
  ドーブルの「スケッチ」のカードがある対戦だけが記録を持つ。形式 1〜25 は、記録があると ``ValueError``（なければ形式 1〜25 の書き出しは v0.99 と同じ）。形式 25 までの書き出しを
  読む側は、記録がないことを「前の番にワザを使わなかった」と読まないこと（記録していない）。
- 27: 26 に、場のポケモンの特殊状態のどくの ``multiplier``（ポケモンチェックでのせる「どく」によるダメージカウンターの数にかける数。ツボツボの「どくどくエキス」の 2。1 なら書かない）と、
  最上位の ``poison_mists``（マタドガスの［ポイズンミスト］の「おもて」の効果。``{"player", "pokemon_id", "source_card", "card_id", "power_index", "created_turn", "poisoned_before",
  "interrupted"}`` の並び）と、最上位の ``replacement_poisons``（マタドガスの「ガスばくはつ」の、かわりに出てくる対戦ポケモンへのまだ与えていないどく。``{"player", "knocked_pokemon_id",
  "card_id", "attack_index", "attacker_player", "attacker_pokemon_id", "attacker_card", "attacker_evolved", "created_turn", "status"}`` の並び。きぜつの判定・サイド・ふしちょう・バトル場に
  出す決定を待つ間だけある。docs 6 章）を加えたもの（v0.119。docs/damage-reactions-poison-sleep-v0.119.md 5 章）。どくの量の性質（固定の量と、ダメージカウンターの数にかける数）は意味が
  違うので、かける数を固定の量に直して古い形式に書かない: 形式 1〜26 は、かける数が 1 でないどく・［ポイズンミスト］の効果・「ガスばくはつ」のまだ与えていないどくがあると ``ValueError``
  （なければ形式 1〜26 の書き出しは v0.118 と同じ）。
  v0.119 の［シェルアーマー］を使うかの決定（``damage_option``）・ほかの新しい決定・持続する効果の種類は、これまでと同じく種類の値と項目を加えただけ（形式は変えない。知らない種類は
  読む側が拒否すること）
- 28: 27 に、場のポケモンの ``basic_entry``（進化カードを進化元を重ねずにベンチに出し、場ではたねポケモンとしてあつかう事実。カブトの［なかまのふっかつ］・オムナイトの［かせきのふっかつ］・
  たまごの化石。``{"card", "card_id", "source", "source_card", "source_card_id", "zone", "turn"}``。ないポケモンは書かない）を加えたもの（v0.120。docs/fossil-basic-virtual-attacks-v0.120.md
  6 章・8 章）。印刷の段階からは分からない場の分類なので、古い形式に黙って落とさない: 形式 1〜27 は、この事実のあるポケモンがいると ``ValueError``（いなければ形式 1〜27 の書き出しは
  v0.119 と同じ）。v0.120 の新しい決定（``revive_source``・``bench_from_deck_or_hand``）・ワザの途中の決定の続きの情報（ESPのやり直しを聞いたワザ ``esp_asked``・ワザを選ぶ範囲
  ``copy_source``）は、これまでと同じく種類の値と項目を加えただけ（知らない種類・項目は読む側が拒否すること）
- 29: 28 に、場のポケモンの ``super_transform``（［すごいへんしん］で選んだ変身のもと。``{"source", "card", "card_id", "turn", "left_active"}``。ないポケモンは書かない）と、最上位の
  ``frozen_forms``（ワザ・宣言する特殊能力・トレーナーカードの処理のあいだ固定した変身の状態。``{"pokemon_id", "card", "card_id", "kind", "source"}`` の並び。処理の決定を待つ間だけある）を
  加えたもの（v0.124。docs/super-transform-dark-pulse-v0.124.md 7 章）。今の場から求め直せない状態なので古い形式に黙って落とさない: 形式 1〜28 は、どちらかがあると ``ValueError``
  （なければ形式 1〜28 の書き出しは v0.123 と同じ）。新しいログ（``super_transform``・``super_transform_reverted``・``dark_pulse``）は種類の値と項目を加えただけ
- 30: 29 に、持続する効果 ``"damage_reduction"`` の ``non_attack_unresolved``（真のときだけ書く。プクリンの「ふくらむ」の効果で、はたらく番にワザ以外のダメージに当てはめるかが
  決まらない印。IF1）を加えたもの（v0.125。docs/wigglytuff-helping-hand-v0.125.md 6 章）。古い形式で項目を落とすと「ちいさくなる」などワザのダメージだけを減らす効果と区別できないので
  黙って落とさない: 形式 1〜29 は、この印のある効果があると ``ValueError``（なければ形式 1〜29 の書き出しは v0.124 と同じ）。［てだすけ］の使用・コイン・回復は、既存の記録
  （``power_uses_this_turn``・ログ ``pokemon_power``・``coin_flip``・``special_conditions_removed``）で表す
- 31: 30 に、最上位の ``face_up_deck``（フラッシュでおもてを上にして山札に置かれたカードの uid の並び。置いた順）を加えたもの（v0.126。docs/flash-faceup-deck-v0.126.md 7 章）。
  今のカードの並びから求め直せない状態（どのカードがおもてか）なので古い形式に黙って落とさない: 形式 1〜30 は、空でなければ ``ValueError``（空なら形式 1〜30 の書き出しは v0.125 と同じ）。
  並べ替えの途中（相手が並べたあと・使ったプレイヤーの答えの前）は、使用中のトレーナー・決定（``ARRANGE_DECK_TOP``・続きの情報の ``stage``）・ログ（``look_at_deck_top``・
  ``arrange_deck_top``・``flash_face_up``）で表す。プレイヤーが知っている情報は書き出しに別の項目を持たない（観測が状態とログから求める）
- 32: 31 の ``halt`` に、途中停止の記録 ``interruption``（``interruption.public_record``。中断の種類・停止コード・論点・発生元・対象・止まった要素・必要な数・処理できる数・未完了の
  処理・在途のカード・ログの位置。なければ null）を加えたもの（v0.127。docs/deferred-shortage-user-promos-v0.127.md 8 章）。途中停止の状態を古い形式に書くと、在途のカード（使用中の
  トレーナー）を残した終端と通常の停止を区別できないので黙って落とさない: 形式 1〜31 は、途中停止の記録があると ``ValueError``（なければ形式 1〜31 の書き出しは v0.126 と同じ）。

形式 1・2 は、トレーナーを使っている最中（決定を待っている間）の状態を表せない（そのカードがどの
ゾーンにも出てこない）。その状態を形式 1・2 で書き出そうとすると ``ValueError`` にする（黙って
カードを落とさない）。同じように、形式 1〜3 はポケモンについているトレーナー（プラスパワーなど）を
表せないので、ついているトレーナーがあると ``ValueError`` にする。トレーナーを使う対戦では形式 4 を使う。
形式 1〜4 は特殊状態（v0.3a）を表せないので、特殊状態のポケモンがいると ``ValueError`` にする（形式 5 を使う）。
形式 1〜5 は「にげる」に失敗した記録（v0.3c）を表せないので、記録のあるポケモンがいると ``ValueError`` にする
（形式 6 を使う。記録は番の終わりに消えるので、その番の間だけ）。
形式 1〜6 は進化したポケモンのカードの重なり（v0.4a）を表せないので、進化したポケモンがいると ``ValueError`` にする
（形式 7 を使う）。形式 1〜7 はワザによる持続する効果（v0.4b）を表せないので、持続する効果を受けているポケモンがいると
``ValueError`` にする（形式 8 を使う。効果は次の相手の番の終わりに消えるので、その間だけ）。持続する効果のない状態の
形式 1〜7 の書き出しは v0.4a と同じ。進化していないポケモンの場に出た番（``played_turn``）は、どの形式にも入るログ（対戦準備の
``place_starting_pokemon``・``play_to_bench``、v0.32 からワザの効果で山札から出した ``bench_from_deck`` の番）から分かるので、形式 1〜6 の書き出しは v0.3d と同じ。
形式 1 は保留中の決定の中身を持たないので、ポケモンチェックの中のきぜつのあとの決定（続きが「ポケモンチェックの
残りをして次の番を始める」。決定の ``context`` の ``then``）を表せない。その状態を形式 1 で書き出そうとすると
``ValueError`` にする。同じように、ワザの途中の決定（``resume`` が ``"attack"``。v0.4d の「ふきとばし」で相手が選ぶ控え）も
形式 1 では ``ValueError`` にする（v0.4c までは、製品の登録表のワザはこの決定を出さなかった）。

ワザの途中の決定（v0.4d）は、形式 2 以上の ``decision``（``id``・``kind``・``player``（決定するプレイヤー。「ふきとばし」では
ワザを使われた側）・``options``（場のポケモンの番号）・``min_choices``・``max_choices``・``resume``（``"attack"``）・``context``
（``use`` = [プレイヤー, 場のポケモンの番号, カード id, ワザの位置]、``target`` = 入れ替える相手の対戦ポケモンの番号））と、
``current_player``（ワザを使ったプレイヤーのまま）・``turn_number`` で表せるので、新しい形式はない（形式 8 のまま）。

ワザのあとのきぜつの判定で「こんじょう」を使うかの決定（v0.11。``kind`` が ``"ko_prevention"``、``resume`` が ``"knock_out"``、
``min_choices`` 0・``max_choices`` 1、``options`` は対象のポケモンの番号、``context`` は ``attack`` = [プレイヤー, 場のポケモンの番号,
カード id, ワザの位置]・``power`` = [カード id, パワーの位置]）も、形式 2 以上の ``decision`` で表せるので、新しい形式はない（形式 9 の
まま）。決定を待つ間、対象のポケモンは HP 以上のダメージのまま場にいる（``players`` の場のポケモンの ``damage``）。コインは決定の
あとで投げるので、乱数の状態（``rng_state_sha256``）は決定を出したときのまま。形式 1 では ``ValueError``。

きぜつしたときに「ふしちょう」を使うかの決定（v0.12。``kind`` が ``"post_knockout_power"``、``resume`` が ``"post_knockout"``、
``min_choices`` 0・``max_choices`` 1、``options`` はトラッシュにあるそのカードの uid、``context`` は ``power`` = [カード id, パワーの位置]
（ポケモンチェックの中のきぜつなら ``then`` も））と、その前のサイドを取る決定の ``context`` の ``post_knockout``（= [[持ち主, カードの
uid, カード id, パワーの位置]]。候補があるときだけ）も、形式 2 以上の ``decision`` で表せるので、新しい形式はない（形式 9 のまま）。
形式 1 では ``ValueError``。

コインの結果（v0.2d）は、ログの ``coin_flip`` にだけ残る（状態に残る値はない）。ログはどの形式にも入るので、
コインのための新しい形式はない。この先のコインの結果を決める乱数の状態は ``rng_state_sha256``（指紋）。

どれも、エンジンの内部の完全な状態の写しで、隠れた情報（山札の順番・相手の手札・サイドの中身）を
すべて含みます。プレイヤー・観戦者に見せる形ではありません（その形はまだありません。
docs/architecture-v0.2a.md の「非公開の情報」）。乱数の状態は指紋だけで、そこから乱数はもどせません
（保存には ``rng.rng_state_to_json`` を使う）。
"""

from __future__ import annotations

from typing import Any

from .interruption import public_record
from .rng import rng_fingerprint
from .state import (
    RETALIATION_FIXED,
    RETALIATION_RECEIVED,
    AttackBarrier,
    AttackReceived,
    AttackUsed,
    OtherReceived,
    AttackCoinCheck,
    ZeroDamageBelow,
    Asleep,
    CannotAttack,
    CannotAttackWhileSourceActive,
    CannotRetreat,
    CannotUsePowers,
    CannotAttachEnergy,
    Confused,
    DamageReduction,
    DestinyBond,
    GameState,
    HalvedDamage,
    DoubledDamage,
    MaxHpSet,
    TailsDamageGuard,
    TimedDamageGuard,
    KnockOutSurvival,
    StatusOnEnergyAttach,
    PursuitOnRetreat,
    RetreatCostIncrease,
    EvolutionLock,
    ReflectShield,
    StatusImmunityWhileActive,
    ZeroDamageAtLeast,
    BenchAttackDamageGuard,
    AttackEffectGuard,
    StatusImmunityNextTurn,
    PowersStopped,
    BenchPowersStopped,
    BenchProtection,
    PERIOD_AMOUNT_TYPES,
    PERIOD_EFFECT_TYPES,
    NEXT_TURN_MULTIPLY,
    CannotUseAttack,
    CannotUseOwnAttack,
    NextTurnAttackDamage,
    Paralyzed,
    PokemonInPlay,
    PreventDamage,
    ReducedDamageToSource,
    ResistanceChange,
    Retaliation,
    SecretePoison,
    NextTurnFailureWaiver,
    TurnAttack,
    TurnField,
    WeaknessChange,
)

FORMAT_VERSIONS = (1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32)


def _special_conditions(pokemon: PokemonInPlay) -> dict[str, Any]:
    """形式 5 の ``special_conditions``（p.322 の順: どく・ねむり・マヒ・こんらん）。"""
    conditions = pokemon.conditions
    data: dict[str, Any] = {}
    if conditions.poison is not None:
        data["poison"] = {"damage": conditions.poison.damage}
        if conditions.poison.multiplier != 1:
            data["poison"]["multiplier"] = conditions.poison.multiplier  # v0.119（形式 27。``state_to_dict`` が形式 1〜26 で拒否する）
    if isinstance(conditions.exclusive, Asleep):
        data["sleep"] = {}
    elif isinstance(conditions.exclusive, Paralyzed):
        data["paralysis"] = {"turn": conditions.exclusive.turn}
    elif isinstance(conditions.exclusive, Confused):
        data["confusion"] = {}
    elif conditions.exclusive is not None:
        raise ValueError(f"書き出せない特殊状態 {conditions.exclusive!r}")
    return data


def _persistent_effect(state: GameState, effect) -> dict[str, Any]:
    """形式 8 の ``persistent_effects`` の 1 つ。v0.12 の ``"retaliation"``（「ほのおのかべ」）には、``attack_index``（効果を与えた
    ワザの位置）と ``amount``（与えるダメージの基本となるダメージ）を加える（ほかの種類の形は v0.4b と同じ。v0.3b の特殊状態の項目と同じく、
    種類の値を加えただけなので形式は変えない。知らない種類のある辞書は、読む側が拒否すること）。v0.13 の
    ``"retaliation_received_damage"``（「こうらがえし」。与えるダメージは受けたダメージと同じ）は ``attack_index`` だけを加える。v0.27 の
    ``"next_turn_attack_damage"``（「つるぎのまい」）は ``attack_index``・``target_attack_index``・``amount`` を加える。v0.31 の
    ``"damage_reduction"``（「ちいさくなる」）は ``amount`` を加え、``"destiny_bond"``・``"attack_barrier"``・``"cannot_attack"`` は共通の項目だけ。
    v0.34 の ``"reduced_damage_to_source"``（「なきつく」）は ``amount`` を加える。v0.35 の ``"next_turn_attack_damage_multiplier"``（「きあいだめ」。
    ``NextTurnAttackDamage`` の「数をかける」決め方）は ``attack_index``・``target_attack_index``・``amount``（かける数）・``includes_self_damage`` を、
    ``"cannot_use_own_attack"``（「あわあわ」）・``"cannot_use_attack"``（「ドわすれ」）は ``attack_index``・``target_attack_index`` を加える（どれも種類の
    値を加えただけで形式は変えない。v0.34 までの書き出しを読む側は、知らない種類として拒否すること）。v0.36 の ``"attack_coin_check"``（「すなかけ」・
    「えんまく」など。p.309 の手順 4 のコイン）は ``single_use``（「効果は1回できえる」）を加え、``"cannot_retreat"``（「アイスバーン」・「わしづかみ」）は共通の
    項目だけ（どちらも相手に与える効果。``source_card`` は効果を与えたワザを使ったポケモン。形式は変えない。v0.35 までの書き出しを読む側は、知らない種類として
    拒否すること）。v0.40 の ``"cannot_attack_while_source_active"``（「すごむ」。相手に与える効果。``source_card`` は効果を与えたワザを使ったポケモン
    （「このカード」））は共通の項目だけ（形式は変えない。v0.39 までの書き出しを読む側は、知らない種類として拒否すること）。v0.45 の
    ``"retaliation_received_damage_scaled"``（「クロスカウンター」。受けたダメージの倍数とコインの条件のある返す効果）は ``attack_index``・``multiplier``・
    ``on_heads`` を、``"zero_damage_below"``（「かたくなる」）は ``threshold`` を加え、``"attack_coin_check"`` の期限のない効果（「スミをかける」の「それ以後」）
    だけ ``lasting``（True）を加える（v0.44 までの形は変えない。形式は変えない。v0.44 までの書き出しを読む側は、知らない種類・項目として拒否すること）。v0.46 の
    ``"halved_damage"``（「リフレクター」）は共通の項目だけ（形式は変えない。v0.45 までの書き出しを読む側は、知らない種類として拒否すること）。"""
    data: dict[str, Any] = {
        "effect": effect.kind,
        "source_card": effect.source_card,
        "source_card_id": state.cards[effect.source_card].card_id,
        "source_player": effect.source_player,
        "created_turn": effect.created_turn,
        "active_turn": effect.active_turn,
    }
    if isinstance(effect, Retaliation):
        data["attack_index"] = effect.attack_index
        if effect.basis == RETALIATION_FIXED:
            data["amount"] = effect.amount
        elif effect.basis != RETALIATION_RECEIVED:
            raise ValueError(f"書き出せない持続する効果 {effect!r}")
        if effect.scaled:
            data["multiplier"] = effect.multiplier  # v0.45: 「クロスカウンター」（種類 "retaliation_received_damage_scaled"）だけ
            data["on_heads"] = effect.on_heads
        # v0.13: 受けたダメージで決まる種類（"retaliation_received_damage"。「こうらがえし」）は、量が効果を与えたときに決まって
        # いないので amount を書かない（受けたダメージはワザ 1 回の中の値で、状態に持たない）
    elif isinstance(effect, NextTurnAttackDamage):
        data["attack_index"] = effect.attack_index
        data["target_attack_index"] = effect.target_attack_index
        data["amount"] = effect.amount
        if effect.operation == NEXT_TURN_MULTIPLY:
            data["includes_self_damage"] = effect.includes_self_damage  # v0.35: 「きあいだめ」（種類 "next_turn_attack_damage_multiplier"）だけ
        elif effect.includes_self_damage:
            raise ValueError(f"書き出せない持続する効果 {effect!r}（「その数にする」効果の自分へのダメージ）")
    elif isinstance(effect, (CannotUseOwnAttack, CannotUseAttack)):
        data["attack_index"] = effect.attack_index  # v0.35: 「あわあわ」・「ドわすれ」
        data["target_attack_index"] = effect.target_attack_index
    elif isinstance(effect, (DamageReduction, ReducedDamageToSource)):
        data["amount"] = effect.amount  # v0.34: "reduced_damage_to_source"（「なきつく」）も減らす量を加える
        if isinstance(effect, DamageReduction) and effect.non_attack_unresolved:
            data["non_attack_unresolved"] = True  # v0.125（形式 30）: 「ふくらむ」の効果だけ書く（``state_to_dict`` が形式 1〜29 で拒否する）
    elif isinstance(effect, AttackCoinCheck):
        data["single_use"] = effect.single_use  # v0.36: 「すなかけ」（PMCG1-051）の「効果は1回できえる」
        if effect.lasting:
            data["lasting"] = True  # v0.45: 「スミをかける」の「それ以後」（期限のない効果だけ書く）
    elif isinstance(effect, ZeroDamageBelow):
        data["threshold"] = effect.threshold  # v0.45: 「かたくなる」
    elif isinstance(effect, (WeaknessChange, ResistanceChange)):
        data["color"] = effect.color.value  # v0.48: 「テクスチャー1」「テクスチャー2」の変えた色
    elif isinstance(effect, MaxHpSet):
        data["amount"] = effect.amount  # v0.48: 「きょだいか」の最大HP
    elif isinstance(effect, ReflectShield):
        data["attack_index"] = effect.attack_index  # v0.83: 「リフレクトシールド」（相手に与えるダメージ）
        data["amount"] = effect.amount
    elif isinstance(effect, TimedDamageGuard):
        # v0.109: 受けるときのコインで防ぐ期限つきの効果（ぬるぬる・かわす・ブリンク）。ダメージを受けない面・説明が書く投げる人・範囲。種類の値と項目を加えただけで形式は変えない
        # （v0.108 までの書き出しを読む側は、知らない種類として拒否すること）
        data["prevent_on"] = effect.prevent_on
        data["flipper"] = effect.flipper
        data["scope"] = effect.scope
    elif isinstance(effect, KnockOutSurvival):
        # v0.110: 残りHPがなくなっても「きぜつ」しない効果（こらえる・こうてつか）。最後の番・範囲・「きぜつ」しないときの残りHP。種類の値と項目を加えただけで形式は変えない
        # （v0.109 までの書き出しを読む側は、知らない種類として拒否すること）
        data["end_turn"] = effect.end_turn
        data["scope"] = effect.scope
        data["remaining_hp"] = effect.remaining_hp
    elif isinstance(effect, StatusOnEnergyAttach):
        # v0.116: エネルギーカードがついたときになる特殊状態と、効果を与えたワザ（AttackKey の文字列）。種類の値と項目を加えただけで形式は変えない
        data["condition"] = effect.condition
        data["attack"] = effect.attack
    elif isinstance(effect, PursuitOnRetreat):
        # v0.117: おいうちの「にげる」ときのダメージの量と、効果を与えたワザ（AttackKey の文字列）。種類の値と項目を加えただけで形式は変えない
        data["amount"] = effect.amount
        data["attack"] = effect.attack
    elif isinstance(effect, NextTurnFailureWaiver):
        # v0.121: ロックオン（``"next_turn_failure_waiver"``）の効果を与えたワザ・失敗しなくなるワザの位置と、失効を決める受けた相手（プレイヤー・場の番号）。種類の値と項目を加えただけで
        # 形式は変えない（v0.92 の期間を明示した効果と同じ。v0.120 までの書き出しを読む側は、知らない種類として拒否すること）
        data["attack_index"] = effect.attack_index
        data["target_attack_index"] = effect.target_attack_index
        data["target_player"] = effect.target_player
        data["target_pokemon"] = effect.target_pokemon
    elif isinstance(effect, SecretePoison):
        # v0.119: どくをだすの控えポケモンへのダメージの量と、効果を与えたワザの位置（``"secrete_poison"``）。種類の値と項目を加えただけで形式は変えない（v0.118 までの書き出しを読む側は、
        # 知らない種類として拒否すること）
        data["attack_index"] = effect.attack_index
        data["amount"] = effect.amount
    elif isinstance(effect, RetreatCostIncrease):
        # v0.118: しめつづけるの「にげる」ときに増やすエネルギーの数と、効果を与えたワザ（AttackKey の文字列）。種類の値（``"retreat_cost_increase"``）と項目を加えただけで形式は変えない
        # （v0.117 までの書き出しを読む側は、知らない種類として拒否すること）
        data["amount"] = effect.amount
        data["attack"] = effect.attack
    elif isinstance(effect, StatusImmunityWhileActive):
        data["attack_index"] = effect.attack_index  # v0.84: 「きらめきタッチ」（効果を与えたワザと、それを使ったポケモンのカード）
        data["given_by"] = effect.given_by
    elif isinstance(effect, ZeroDamageAtLeast):
        data["threshold"] = effect.threshold  # v0.84: 「パルスガード」
    elif isinstance(effect, PERIOD_EFFECT_TYPES):
        # v0.92: 期間を明示した効果（``"period_retreat_lock"``・``"period_attack_lock"``・``"received_attack_damage_bonus"``。v0.93 で ``"period_leave_lock"``・
        # ``"period_attack_coin_check"``、v0.108 で ``"dealt_attack_damage_reduction"`` を加えた）。期間の終わり（null は期限なし）・発生源の場の番号と、
        # あるときだけ発生源がバトル場にいる間だけの印・明記された消える契機、いやなおとは増やす数。種類の値を加えただけで形式は変えない（v0.84・v0.86 と同じ。v0.91 までの書き出しを
        # 読む側は、知らない種類として拒否すること）
        data["end_turn"] = effect.end_turn
        data["source_pokemon"] = effect.source_pokemon
        if effect.while_source_active:
            data["while_source_active"] = True
        if effect.ends_on:
            data["ends_on"] = list(effect.ends_on)
        if isinstance(effect, PERIOD_AMOUNT_TYPES):
            data["amount"] = effect.amount  # いやなおと・かみくだくの増やす数、v0.108 のマイナスイオン・あまえるの減らす数
        if getattr(effect, "knockout_exception", False):
            data["knockout_exception"] = True  # v0.93: 「バトル場をはなれられない」効果の「(「きぜつ」した場合をのぞく)」（あるときだけ）
        if getattr(effect, "source_left", False):
            data["source_left"] = True  # v0.93: くいつくの発生源が与えたあとにバトル場をはなれた印（あるときだけ）
    elif not isinstance(effect, (PreventDamage, DestinyBond, AttackBarrier, CannotAttack, CannotRetreat, CannotAttackWhileSourceActive, HalvedDamage,
                                         CannotUsePowers, CannotAttachEnergy, TailsDamageGuard, DoubledDamage, BenchAttackDamageGuard, AttackEffectGuard,
                                         StatusImmunityNextTurn, PowersStopped, BenchProtection, BenchPowersStopped, EvolutionLock)):
        raise ValueError(f"書き出せない持続する効果 {effect!r}")
    # v0.49（形式 14）: ワザを印刷したカードの id（いちばん上のカードと違うときだけ。状態の書き出しの前に、形式 14 より古い形式では拒否している）
    for name in ("attack_card", "target_attack_card"):
        if getattr(effect, name, None) is not None:
            data[name] = getattr(effect, name)
    return data


def _uses_v049_fields(state: GameState) -> bool:
    """形式 14（v0.49）だけが表せる値があるか: 「ばける」でのせたカード・「思い出させる」の記録・ワザを印刷したカードを持つ持続する効果・のせたカードの特殊能力の
    使用の記録。"""
    if state.recalls or any(len(use) != 2 for use in state.power_uses_this_turn):
        return True
    for p in state.players:
        for pokemon in p.in_play():
            if pokemon.disguise is not None:
                return True
            if any(getattr(e, "attack_card", None) is not None or getattr(e, "target_attack_card", None) is not None for e in pokemon.persistent_effects):
                return True
    return False


def _disguise_power_records(state: GameState) -> set[tuple[int, int, int]]:
    """今の番の特殊能力の宣言のログのうち、いちばん上のカードでないカード（「ばける」でのせたカード。ログの ``card``）の特殊能力を使ったもの（v0.49 の 3 つの値の記録）。"""
    found = set()
    for event in reversed(state.log):
        if event["kind"] == "turn_start":
            break
        if event["kind"] == "pokemon_power" and event.get("card") is not None:
            found.add((event.get("pokemon_id"), event.get("power_index"), event.get("card")))
    return found


def _uses_v050_fields(state: GameState) -> bool:
    """形式 15（v0.50）だけが表せる値があるか: 退化した番のあるポケモン・進化・退化でいちばん上でなくなったカードの「自分の番ごとに1回」の記録（形式 14 の 3 つの値の
    記録は「ばける」でのせたカードの使用だけを表すので、それと区別する。区別はログの宣言で確かめる。状態は変えない）。"""
    if any(pokemon.devolved_turn is not None for p in state.players for pokemon in p.in_play()):
        return True
    retagged = [use for use in state.power_uses_this_turn if len(use) == 3]
    return bool(retagged) and not set(retagged) <= _disguise_power_records(state)


def _uses_v099_fields(state: GameState) -> bool:
    """v0.99: 形式 24 までの受けた記録（合計だけ）では落ちる、受けた場所の分かる 0 より大きいダメージの記録があるか（合計が 0 なら場所によらず 0。場所の分からない記録はそのまま書ける）。"""
    return any(isinstance(record, AttackReceived) and record.damage > 0 and record.active_damage is not None
               for p in state.players for pokemon in p.in_play() for record in pokemon.history)


def _pokemon(state: GameState, pokemon: PokemonInPlay | None, format_version: int) -> dict[str, Any] | None:
    if pokemon is None:
        return None
    # v0.67: うらにしてベンチに出したカードも、内部の完全な記録なので本当のカードの定義を書く（うらであることは最上位の ``face_down_cards``）
    definition = state.in_play_def(pokemon.card) if state.is_face_down(pokemon) else state.card_def(pokemon.card)
    data = {
        "card": pokemon.card,
        "card_id": definition.id,
        "name": definition.name_ja,
        "hp": definition.hp,
        "damage": pokemon.damage,
        "energy": list(pokemon.energy),
    }
    if format_version >= 2:
        data["pokemon_id"] = pokemon.pokemon_id
    if format_version >= 4:
        data["trainers"] = [
            {
                "card": t.card,
                "card_id": state.cards[t.card].card_id,
                "player": t.player,
                "discard_at_end_of_turn": t.discard_at_end_of_turn,
            }
            for t in pokemon.trainers
        ]
    if format_version >= 5:
        data["special_conditions"] = _special_conditions(pokemon)
    if format_version >= 6:
        data["retreat_failed_turn"] = pokemon.retreat_failed_turn
    if format_version >= 7:
        data["evolution_stack"] = [{"card": uid, "card_id": state.cards[uid].card_id} for uid in pokemon.evolution_stack]
        data["played_turn"] = pokemon.played_turn
        data["evolved_turn"] = pokemon.evolved_turn
    if format_version >= 8:
        data["persistent_effects"] = [_persistent_effect(state, e) for e in pokemon.persistent_effects]
    if format_version >= 11:
        data["attacks_used_once"] = [list(entry) for entry in pokemon.attacks_used_once]
        data["evolution_permission_turn"] = pokemon.evolution_permission_turn
    if format_version >= 13:
        shift = pokemon.type_shift
        data["type_shift"] = None if shift is None else {
            "color": shift.color.value, "turn": shift.turn, "source_card": shift.source_card,
            "source_card_id": state.cards[shift.source_card].card_id, "returned_to_bench": shift.returned_to_bench,
        }
    if format_version >= 14:
        data["disguise"] = None if pokemon.disguise is None else {"card": pokemon.disguise, "card_id": state.cards[pokemon.disguise].card_id}
    if format_version >= 15:
        data["devolved_turn"] = pokemon.devolved_turn  # v0.50
    if format_version >= 20:
        data["history"] = [history_record(record, format_version) for record in pokemon.history]  # v0.62（v0.99: 形式 25 から受けた記録の場所）
    if format_version >= 24:
        data["markers"] = [marker_record(state, marker) for marker in pokemon.markers]  # v0.90
    if format_version >= 28 and pokemon.basic_entry is not None:
        data["basic_entry"] = basic_entry_record(state, pokemon.basic_entry)  # v0.120（なければ書かない）
    if format_version >= 29 and pokemon.super_transform is not None:
        data["super_transform"] = super_transform_record(state, pokemon.super_transform)  # v0.124（なければ書かない）
    return data


def super_transform_record(state: GameState, record) -> dict[str, Any]:
    """v0.124: ［すごいへんしん］で選んだ変身のもと（``state.SuperTransform``）。選んだ場の個体の番号・同じカードとしてあつかうカード・選んだ番・バトル場をはなれたか。"""
    return {"source": record.source, "card": record.card, "card_id": state.cards[record.card].card_id, "turn": record.turn, "left_active": record.left_active}


def frozen_form_record(state: GameState, record) -> dict[str, Any]:
    """v0.124: 処理のあいだ固定した変身の状態 1 つ（``state.FrozenForm``）。"""
    return {"pokemon_id": record.pokemon, "card": record.card, "card_id": state.cards[record.card].card_id, "kind": record.kind, "source": record.source}


def basic_entry_record(state: GameState, entry) -> dict[str, Any]:
    """v0.120: 進化元を重ねずに出し、場ではたねポケモンとしてあつかう進化カードの事実（``state.BasicEntry``）。"""
    return {"card": entry.card, "card_id": state.cards[entry.card].card_id, "source": entry.source, "source_card": entry.source_card,
            "source_card_id": state.cards[entry.source_card].card_id, "zone": entry.zone, "turn": entry.turn}


def marker_record(state: GameState, marker) -> dict[str, Any]:
    """v0.90: マーカー・カウンター 1 つ（``state.Marker``）。色マーカーだけ ``color`` を書く。"""
    data: dict[str, Any] = {"kind": marker.kind, "player": marker.player, "source_card": marker.source_card,
                            "source_card_id": state.cards[marker.source_card].card_id, "effect": marker.attack, "turn": marker.turn}
    if marker.color is not None:
        data["color"] = marker.color.value
    return data


def history_record(record, format_version: int | None = None) -> dict[str, Any]:
    """v0.62: ワザの履歴の記録 1 つ（``AttackUsed``・``AttackReceived``・``OtherReceived``）。v0.99: ``format_version`` が 25 以上（None は最新。観測が使う）なら、受けた記録に
    ``active_damage`` を書く。"""
    if isinstance(record, AttackUsed):
        return {"kind": "used", "turn": record.turn, "card": record.card, "declared": list(record.declared),
                "processed": None if record.processed is None else list(record.processed)}
    if isinstance(record, AttackReceived):
        data = {"kind": "received", "turn": record.turn, "card": record.card, "player": record.player, "source": record.source,
                "declared": list(record.declared), "processed": list(record.processed), "damage": record.damage, "reached": list(record.reached),
                "voided": [list(v) for v in record.voided]}
        if format_version is None or format_version >= 25:
            data["active_damage"] = record.active_damage
        return data
    if isinstance(record, OtherReceived):
        return {"kind": "other_received", "turn": record.turn, "card": record.card}
    raise ValueError(f"ワザの履歴の記録の型 {type(record).__name__} は書き出せない")


def _plain(value: Any) -> Any:
    if isinstance(value, tuple):
        return [_plain(v) for v in value]
    if isinstance(value, dict):
        return {k: _plain(v) for k, v in value.items()}
    return value


def state_to_dict(state: GameState, format_version: int = 1) -> dict[str, Any]:
    if format_version not in FORMAT_VERSIONS:
        raise ValueError(f"知らない形式 {format_version!r}（{FORMAT_VERSIONS}）")
    if state.trainer_in_use is not None and format_version < 3:
        raise ValueError(f"形式 {format_version} は、使っている最中のトレーナーカードを表せない（format_version=3 以上を使う）")
    if format_version < 4 and any(pokemon.trainers for p in state.players for pokemon in p.in_play()):
        raise ValueError(f"形式 {format_version} は、ポケモンについているトレーナーカードを表せない（format_version=4 を使う）")
    if format_version < 5 and any(pokemon.conditions.names() for p in state.players for pokemon in p.in_play()):
        raise ValueError(f"形式 {format_version} は、特殊状態（どく・ねむり・マヒ・こんらん）を表せない（format_version=5 以上を使う）")
    if format_version < 6 and any(pokemon.retreat_failed_turn is not None for p in state.players for pokemon in p.in_play()):
        raise ValueError(f"形式 {format_version} は、こんらん状態で「にげる」に失敗した記録を表せない（format_version=6 を使う）")
    if format_version < 7 and any(pokemon.evolution_stack for p in state.players for pokemon in p.in_play()):
        raise ValueError(f"形式 {format_version} は、進化したポケモンのカードの重なりを表せない（format_version=7 を使う）")
    if format_version < 8 and any(pokemon.persistent_effects for p in state.players for pokemon in p.in_play()):
        raise ValueError(f"形式 {format_version} は、ワザによる持続する効果を表せない（format_version=8 を使う）")
    if format_version < 9 and state.energy_attached_by_powers_this_turn != 0:
        raise ValueError(
            f"形式 {format_version} は、この番にポケモンパワーで手札からつけたエネルギーの枚数を表せない（format_version=9 を使う）"
        )
    if format_version < 10 and (state.power_uses_this_turn or state.energy_burn):
        raise ValueError(
            f"形式 {format_version} は、この番に使った回数の制限のある特殊能力・「炎」エネルギーになったエネルギーを表せない（format_version=10 を使う）"
        )
    if format_version < 11 and any(pokemon.attacks_used_once or pokemon.evolution_permission_turn is not None
                                   for p in state.players for pokemon in p.in_play()):
        raise ValueError(
            f"形式 {format_version} は、場に出てから1回しか使えないワザの使った記録・「サカキ」の進化の許可を表せない（format_version=11 を使う）"
        )
    if format_version < 12 and state.trainer_locks:
        raise ValueError(f"形式 {format_version} は、プレイヤーに与えた期限のあるトレーナーカードの使用の禁止を表せない（format_version=12 を使う）")
    if format_version < 13 and any(pokemon.type_shift is not None for p in state.players for pokemon in p.in_play()):
        raise ValueError(f"形式 {format_version} は、特殊能力で色を変えた記録（［へんしょく］）を表せない（format_version=13 を使う）")
    if format_version < 14 and _uses_v049_fields(state):
        raise ValueError(
            f"形式 {format_version} は、「ばける」でのせたカード・「思い出させる」の記録・ワザを印刷したカードを持つ持続する効果・のせたカードの特殊能力の使用の記録を"
            "表せない（format_version=14 を使う）"
        )
    if format_version < 15 and _uses_v050_fields(state):
        raise ValueError(
            f"形式 {format_version} は、退化した番・進化や退化でいちばん上でなくなったカードの特殊能力の使用の記録を表せない（format_version=15 を使う）"
        )
    if format_version < 16 and (state.trainer_effects or any(lock.origin != "attack" for lock in state.trainer_locks)):
        raise ValueError(
            f"形式 {format_version} は、期限のあるトレーナーの効果（カスミ・キョウ・見えない壁）・トレーナーの効果によるトレーナーの使用の禁止を表せない（format_version=16 を使う）"
        )
    if format_version < 17 and (
        state.stadium is not None or state.stadium_uses_this_turn
        or (state.trainer_in_use is not None and state.trainer_in_use.user is not None)
    ):
        raise ValueError(
            f"形式 {format_version} は、場のスタジアム・スタジアムの効果を使った記録・借りて使っているトレーナーを表せない（format_version=17 を使う）"
        )
    if format_version < 18 and (state.trainer_stack or (state.trainer_in_use is not None and state.trainer_in_use.via is not None)):
        raise ValueError(
            f"形式 {format_version} は、外側のトレーナーの効果で相手のトラッシュから使っている最中のトレーナー（ナツメのサイキックコントロール）を表せない（format_version=18 を使う）"
        )
    if format_version < 19 and state.energy_roles:
        raise ValueError(f"形式 {format_version} は、エネルギーとしてついているカード（マルマインの［エネエネ］）を表せない（format_version=19 を使う）")
    if format_version < 20 and any(pokemon.history for p in state.players for pokemon in p.in_play()):
        raise ValueError(f"形式 {format_version} は、場のポケモンのワザの履歴（使ったワザ・受けたワザ）を表せない（format_version=20 を使う）")
    if format_version < 21 and (state.set_aside or state.face_up_prizes):
        raise ValueError(f"形式 {format_version} は、一時的に置いておくカード・おもてのサイドを表せない（format_version=21 を使う）")
    if format_version < 22 and state.face_down_cards:
        raise ValueError(f"形式 {format_version} は、うらにしてベンチに出したカード（マチスの秘策）を表せない（format_version=22 を使う）")
    if format_version < 23 and state.color_effects:
        raise ValueError(f"形式 {format_version} は、特殊能力で色を変える効果（［せんすい］・［エナジーコンバーター］）を表せない（format_version=23 を使う）")
    if format_version < 24 and any(pokemon.markers for p in state.players for pokemon in p.in_play()):
        raise ValueError(f"形式 {format_version} は、場のポケモンのマーカー・カウンター（ダメージカウンター以外）を表せない（format_version=24 を使う）")
    if format_version < 25 and _uses_v099_fields(state):
        raise ValueError(f"形式 {format_version} は、場のポケモンの受けた記録の、ダメージを受けた場所（バトル場・ベンチ）を表せない（format_version=25 を使う）")
    if format_version < 26 and state.turn_history:
        raise ValueError(f"形式 {format_version} は、プレイヤーの番ごとの記録（使ったワザ・場にいたカード）を表せない（format_version=26 を使う）")
    if format_version < 27 and (state.poison_mists or any(pokemon.conditions.poison is not None and pokemon.conditions.poison.multiplier != 1
                                                          for p in state.players for pokemon in p.in_play())):
        raise ValueError(f"形式 {format_version} は、ダメージカウンターの数を倍にするどく・［ポイズンミスト］の効果を表せない（format_version=27 を使う）")
    if format_version < 27 and state.replacement_poisons:
        raise ValueError(f"形式 {format_version} は、「ガスばくはつ」のかわりに出てくる対戦ポケモンへのまだ与えていないどくを表せない（format_version=27 を使う）")
    if format_version < 29 and (state.frozen_forms or any(pokemon.super_transform is not None for p in state.players for pokemon in p.in_play())):
        # v0.124: 選んだ変身のもと・処理のあいだ固定した姿は、今のカードの並びから求め直せない（相手の対戦ポケモンを読む［へんしん］の形に落とすと意味が変わる）ので古い形式に書かない
        raise ValueError(f"形式 {format_version} は、［すごいへんしん］で選んだ変身のもと・処理のあいだ固定した変身の状態を表せない（format_version=29 を使う）")
    if format_version < 30 and any(isinstance(effect, DamageReduction) and effect.non_attack_unresolved
                                   for p in state.players for pokemon in p.in_play() for effect in pokemon.persistent_effects):
        # v0.125: 「ふくらむ」の効果（ワザ以外のダメージに当てはめるかが決まらない印）を落とすと、ワザのダメージだけを減らす効果と区別できないので古い形式に書かない
        raise ValueError(f"形式 {format_version} は、ワザ以外のダメージに当てはめるかが決まらない「ふくらむ」の効果を表せない（format_version=30 を使う）")
    if format_version < 32 and state.halt is not None and state.halt.interruption is not None:
        # v0.127: 途中停止の状態（在途のカードを残した終端）は、古い形式では通常の停止と区別できないので書かない
        raise ValueError(f"形式 {format_version} は、途中停止の状態（数量のチェック地点で止めた終端）を表せない（format_version=32 を使う）")
    if format_version < 31 and state.face_up_deck:
        # v0.126: おもてを上にした山札のカード（フラッシュ）は、今のカードの並びから求め直せないので古い形式に書かない（落とすと、うらの山札と区別できない）
        raise ValueError(f"形式 {format_version} は、おもてを上にして山札に置かれたカード（フラッシュ）を表せない（format_version=31 を使う）")
    if format_version < 28 and any(pokemon.basic_entry is not None for p in state.players for pokemon in p.in_play()):
        raise ValueError(f"形式 {format_version} は、進化元を重ねずに出して場ではたねポケモンとしてあつかう進化カードを表せない（format_version=28 を使う）")
    if format_version == 1 and state.decision is not None and state.decision.context_value("then") is not None:
        raise ValueError("形式 1 は、ポケモンチェックの中のきぜつのあとの決定（続き）を表せない（format_version=2 以上を使う）")
    if format_version == 1 and state.decision is not None and state.decision.resume == "attack":
        # v0.4d: v0.1 の形には、ワザの途中の決定（「ふきとばし」で相手が選ぶ控えなど）の項目がない（段階 "decision" だけが残り、
        # 決定するプレイヤー・選べるもの・続きの情報が落ちる）。黙って落とさない
        raise ValueError("形式 1 は、ワザの途中の決定を表せない（format_version=2 以上を使う）")
    if format_version == 1 and state.decision is not None and state.decision.resume == "power":
        # v0.42: v0.1 の形には、特殊能力の途中の決定（決定するプレイヤー・選べるもの・続きの情報）の項目がない。黙って落とさない
        raise ValueError("形式 1 は、特殊能力の途中の決定を表せない（format_version=2 以上を使う）")
    if format_version == 1 and state.decision is not None and state.decision.resume == "knock_out":
        # v0.11: v0.1 の形には、ワザのあとのきぜつの判定で「こんじょう」を使うかの決定（決定するプレイヤー・選べるもの・選ぶ数 0〜1・
        # 続きの情報）の項目がない。黙って落とさない
        raise ValueError("形式 1 は、「こんじょう」を使うかの決定を表せない（format_version=2 以上を使う）")
    if format_version == 1 and state.decision is not None and (
        state.decision.resume == "post_knockout" or state.decision.context_value("post_knockout") is not None
    ):
        # v0.12: v0.1 の形には、「ふしちょう」を使うかの決定（決定するプレイヤー・トラッシュのカード・選ぶ数 0〜1）の項目も、サイドを取る
        # 決定のあとに「ふしちょう」の決定が続くこと（context の post_knockout）を表す項目もない。黙って落とさない
        raise ValueError("形式 1 は、「ふしちょう」を使うかの決定（とその前のサイドを取る決定）を表せない（format_version=2 以上を使う）")
    data = {
        "rules": state.rules.id,
        "card_data": {"repository": state.card_data.repository, "commit": state.card_data.commit, "path": state.card_data.path},
        "seed": state.seed,
        # 乱数の状態（この先のコインの結果などを決める）。同じ値なら同じ乱数の続きになる
        "rng_state_sha256": rng_fingerprint(state.rng),
        "phase": state.phase.value,
        "turn_number": state.turn_number,
        "current_player": state.current_player,
        "first_player": state.first_player,
        "energy_attachments_this_turn": state.energy_attachments_this_turn,
        "pending_prizes": {str(k): v for k, v in sorted(state.pending_prizes.items())},
        "pending_promotions": list(state.pending_promotions),
        "mulligan_rounds": [list(r) for r in state.mulligan_rounds],
        "cards": {str(uid): {"card_id": c.card_id, "owner": c.owner} for uid, c in sorted(state.cards.items())},
        "players": [
            {
                "deck": list(p.deck),
                "hand": list(p.hand),
                "prizes": list(p.prizes),
                "discard": list(p.discard),
                "active": _pokemon(state, p.active, format_version),
                "bench": [_pokemon(state, b, format_version) for b in p.bench],
                "placed_starting_pokemon": p.placed_starting_pokemon,
                "mulligans": p.mulligans,
                "mulligan_draws_remaining": p.mulligan_draws_remaining,
            }
            for p in state.players
        ],
        "result": None
        if state.result is None
        else {
            "outcome": state.result.outcome,
            "winner": state.result.winner,
            "conditions": [list(c) for c in state.result.conditions],
        },
        "halt": None
        if state.halt is None
        else {"code": state.halt.code, "message": state.halt.message, "references": list(state.halt.references),
              **({"interruption": None if state.halt.interruption is None else public_record(state.halt.interruption)} if format_version >= 32 else {})},
        "log": [_plain(dict(event)) for event in state.log],
    }
    if format_version == 1:
        return data
    d = state.decision
    data.update({
        "format_version": format_version,
        "effects": state.effects.id,
        "next_pokemon_id": state.next_pokemon_id,
        "next_decision_id": state.next_decision_id,
        "decision": None if d is None else {
            "id": d.id,
            "kind": d.kind,
            "player": d.player,
            "options": list(d.options),
            "min_choices": d.min_choices,
            "max_choices": d.max_choices,
            "resume": d.resume,
            "context": {name: _plain(value) for name, value in d.context},
        },
    })
    if format_version == 2:
        return data
    used = state.trainer_in_use
    data["trainer_in_use"] = None if used is None else {
        "player": used.player,
        "card": used.card,
        "card_id": state.cards[used.card].card_id,
        **({"user": used.user} if format_version >= 17 else {}),
        **({"via": used.via} if format_version >= 18 else {}),
    }
    if format_version >= 9:
        data["energy_attached_by_powers_this_turn"] = state.energy_attached_by_powers_this_turn
    if format_version >= 10:
        data["power_uses_this_turn"] = [list(use) for use in state.power_uses_this_turn]
        data["energy_burn"] = [list(pair) for pair in state.energy_burn]
    if format_version >= 12:
        data["trainer_locks"] = [
            {"player": lock.player, "source_player": lock.source_player, "source_card": lock.source_card,
             "source_card_id": state.cards[lock.source_card].card_id, "effect": lock.effect, "created_turn": lock.created_turn,
             "expires_turn": lock.expires_turn, **({"origin": lock.origin} if format_version >= 16 else {})}
            for lock in state.trainer_locks
        ]
    if format_version >= 14:
        data["recalls"] = [
            {"player": r.player, "turn": r.turn, "pokemon_id": r.pokemon_id, "card": r.card, "card_id": state.cards[r.card].card_id,
             "trainer": r.trainer, "trainer_card_id": state.cards[r.trainer].card_id}
            for r in state.recalls
        ]
    if format_version >= 16:
        data["trainer_effects"] = [
            {"kind": e.kind, "player": e.player, "source_card": e.source_card, "card_id": e.card_id, "created_turn": e.created_turn,
             "expires_turn": e.expires_turn, **({} if e.pokemon_id is None else {"pokemon_id": e.pokemon_id}),  # v0.80: 退化スプレーHYPER の禁止だけ
             **({} if e.attack_index is None else {"attack_index": e.attack_index})}  # v0.87: ワザで与えた効果（ふしぎなガス）だけ
            for e in state.trainer_effects
        ]
    if format_version >= 17:
        stadium = state.stadium
        data["stadium"] = None if stadium is None else {
            "owner": stadium.owner, "card": stadium.card, "card_id": state.cards[stadium.card].card_id, "placed_turn": stadium.placed_turn,
        }
        data["stadium_uses_this_turn"] = [list(use) for use in state.stadium_uses_this_turn]
    if format_version >= 18:
        data["trainer_stack"] = [
            {"player": outer.player, "card": outer.card, "card_id": state.cards[outer.card].card_id, "user": outer.user, "via": outer.via}
            for outer in state.trainer_stack
        ]
    if format_version >= 19:
        data["energy_roles"] = [
            {"card": r.card, "card_id": state.cards[r.card].card_id, "energy_type": r.energy_type.value, "units": r.units, "owner": r.owner, "turn": r.turn}
            for r in state.energy_roles
        ]
    if format_version >= 21:
        data["set_aside"] = [
            {"kind": g.kind, "owner": g.owner, "cards": list(g.cards), "card_ids": [state.cards[uid].card_id for uid in g.cards], "visible_to": list(g.visible_to),
             "user": g.user, "trainer_card": g.trainer_card, "card_id": g.card_id, "created_turn": g.created_turn, "return_turn": g.return_turn}
            for g in state.set_aside
        ]
        data["face_up_prizes"] = list(state.face_up_prizes)
    if format_version >= 22:
        data["face_down_cards"] = list(state.face_down_cards)  # v0.67
    if format_version >= 23:
        data["color_effects"] = [
            {"kind": e.kind, "player": e.player, "source": e.source, "source_card": e.source_card, "card_id": state.cards[e.source_card].card_id,
             "power_index": e.power_index, "target": e.target, "color": e.color.value, "turn": e.turn, "left_play": e.left_play}
            for e in state.color_effects
        ]  # v0.88
    if format_version >= 26:
        data["turn_history"] = [turn_record(record) for record in state.turn_history]  # v0.100
    if format_version >= 27:
        data["poison_mists"] = [poison_mist_record(state, record) for record in state.poison_mists]  # v0.119
        data["replacement_poisons"] = [replacement_poison_record(record) for record in state.replacement_poisons]  # v0.119
    if format_version >= 29:
        data["frozen_forms"] = [frozen_form_record(state, record) for record in state.frozen_forms]  # v0.124
    if format_version >= 31:
        data["face_up_deck"] = list(state.face_up_deck)  # v0.126
    return data


def replacement_poison_record(record) -> dict[str, Any]:
    """v0.119: 「ガスばくはつ」のまだ与えていないどく 1 つ（``state.ReplacementPoison``）。観測も同じ形を使う（どれも表の情報）。"""
    return {"player": record.player, "knocked_pokemon_id": record.knocked_pokemon_id, "card_id": record.card_id, "attack_index": record.attack_index,
            "attacker_player": record.attacker_player, "attacker_pokemon_id": record.attacker_pokemon_id, "attacker_card": record.attacker_card,
            "attacker_evolved": record.attacker_evolved, "created_turn": record.created_turn, "status": record.status}


def poison_mist_record(state: GameState, record) -> dict[str, Any]:
    """v0.119: ［ポイズンミスト］の効果 1 つ（``state.PoisonMist``）。観測も同じ形を使う（どれも表の情報）。"""
    return {"player": record.player, "pokemon_id": record.pokemon_id, "source_card": record.source_card, "card_id": record.card_id, "power_index": record.power_index,
            "created_turn": record.created_turn, "poisoned_before": list(record.poisoned_before), "interrupted": record.interrupted}


def turn_record(record) -> dict[str, Any]:
    """v0.100: プレイヤーの番ごとの記録 1 つ（``TurnAttack``・``TurnField``）。観測も同じ形を使う（どちらも表の情報。うらのカードは数だけ）。"""
    if isinstance(record, TurnAttack):
        return {"kind": "turn_attack", "turn": record.turn, "player": record.player, "pokemon_id": record.pokemon_id, "card": record.card,
                "declared": list(record.declared), "processed": None if record.processed is None else list(record.processed)}
    if isinstance(record, TurnField):
        return {"kind": "turn_field", "turn": record.turn, "player": record.player, "cards": list(record.cards), "face_down": record.face_down}
    raise ValueError(f"プレイヤーの番ごとの記録の型 {type(record).__name__} は書き出せない")

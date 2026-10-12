"""ルールの組（どの時期のルールで対戦するか）。

v0.1 が持つのは「ポケットモンスターカードゲーム公式ルール 2000.02.14版」だけです。
数値をコードに直接書かず、ここにまとめておくことで、後でほかの版（第4版の冊子など）を
加えるときに、違う項目だけを差し替えられるようにしています。ルールの組の切り替えそのものは
v0.1 では実装していません。

出典の記号（P43 など）と記録 id（NEO-2000-OFFICIAL-RULES、mulligan など）は kyuura の
docs/sources.md・data/rule_history.json・data/rule_differences.json のものです。
ページは『ポケモンカードオフィシャルブック2000』[P43] の誌面のノンブルです。
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class RuleSet:
    id: str
    title: str
    deck_size: int
    max_copies_per_name: int
    opening_hand_size: int
    max_setup_bench: int
    max_bench: int
    prize_count: int
    mulligan_draw_max_per_mulligan: int
    first_player_draws_on_first_turn: bool
    energy_attachments_per_turn: int
    weakness_multiplier: int
    damage_per_counter: int  # ダメージカウンター 1 個が表すダメージ（p.319）


RULES_2000_02_14 = RuleSet(
    id="JP-2000.02.14",
    title="ポケットモンスターカードゲーム公式ルール 2000.02.14版",
    deck_size=60,
    max_copies_per_name=4,
    opening_hand_size=7,
    max_setup_bench=5,
    max_bench=5,
    prize_count=6,
    mulligan_draw_max_per_mulligan=2,
    first_player_draws_on_first_turn=True,
    energy_attachments_per_turn=1,
    weakness_multiplier=2,
    damage_per_counter=10,
)


@dataclass(frozen=True)
class RuleReference:
    """実装した規定と、その根拠（誌面のページと kyuura の記録 id）。"""

    item: str
    summary: str
    pages: str
    kyuura_ids: tuple[str, ...]


# kyuura の rule_differences.json の項目 id があるものはそれを item にしている
RULE_REFERENCES: dict[str, RuleReference] = {
    ref.item: ref
    for ref in [
        RuleReference("deck", "デッキはぴったり 60 枚。たねポケモン（ベイビィポケモン）を必ず入れる", "p.308", ("NEO-2000-OFFICIAL-RULES",)),
        RuleReference("same_name", "同じ名前のカードは 4 枚まで。基本エネルギーカードは制限なし。名前が同じならレベル・HP・ワザが違っても同じ名前", "p.308", ("NEO-2000-OFFICIAL-RULES",)),
        RuleReference("opening_hand", "山札の一番上から 7 枚取って手札にする", "p.308", ("NEO-2000-OFFICIAL-RULES",)),
        RuleReference("mulligan", "たねポケモンがなければ手札を見せて切り直す。来るまでくりかえす。相手は切り直し 1 回ごとに最大 2 枚引ける（サイドを置いた後）。両方ともなかったときはどちらも引かない", "p.308", ("NEO-2000-OFFICIAL-RULES", "mulligan")),
        RuleReference("setup_bench", "バトル場に 1 枚、ベンチに最大 5 枚まで裏にして出す（出さなくてもよい）", "p.308", ("NEO-2000-OFFICIAL-RULES", "setup_bench")),
        RuleReference("prizes", "山札の一番上から 6 枚をサイドにする", "p.308, p.312", ("NEO-2000-OFFICIAL-RULES", "prizes")),
        RuleReference("first_player", "ジャンケンで勝った人が先攻、負けた人が後攻（サイドを置いた後）", "p.308", ("NEO-2000-OFFICIAL-RULES", "first_player")),
        RuleReference("turn_order", "場のポケモンがすべて表になった時点で先攻の番が始まる。番の後にポケモンチェックをして、交互にくりかえす", "p.309", ("NEO-2000-OFFICIAL-RULES",)),
        RuleReference("first_turn_draw", "自分の番の最初に必ず 1 枚引く。先攻の最初の番の例外は書かれていない", "p.309", ("NEO-2000-OFFICIAL-RULES", "first_turn_draw")),
        RuleReference("bench", "手札のたねポケモンをベンチに出せる。ベンチは 5 匹まで。1 番に出す数の制限はない。手札から直接バトル場には出せない", "p.309, p.313", ("NEO-2000-OFFICIAL-RULES",)),
        RuleReference("energy_attach", "エネルギーカードは 1 番に 1 枚、自分の場のポケモンにつけられる。相手のポケモンにはつけられない", "p.310", ("NEO-2000-OFFICIAL-RULES",)),
        RuleReference("retreat_count", "にげるは、にげるエネルギーの数ぶんトラッシュして控えと入れ替える。1 番に何度でも。控えがいなければ宣言できない", "pp.310-311", ("NEO-2000-OFFICIAL-RULES", "retreat_count")),
        RuleReference("attack", "番ごとに一度だけ、バトル場のポケモンがワザを使える。必要なエネルギー以上がついていること（無色はどの色でもよい）。使い終わったら番は自動的に終わる。ワザを使わずに番を終えてもよい", "p.309, p.320", ("NEO-2000-OFFICIAL-RULES",)),
        RuleReference("weakness_resistance", "ダメージ計算の 8 段階。弱点は 2 倍、抵抗力は抵抗力の数字をマイナス。0 以下なら「ダメージを与えなかった」", "p.315, p.319, p.321", ("NEO-2000-OFFICIAL-RULES", "NEO-2000-PLAYRULE", "weakness_resistance")),
        RuleReference("knockout_timing", "HP 以上のダメージを受けるときぜつし、ついていたカードとともにトラッシュする。相手はサイドを 1 枚選んで取る", "p.315, p.319, p.323", ("NEO-2000-OFFICIAL-RULES", "knockout_timing")),
        RuleReference("promote", "バトル場のポケモンがいなくなったら、ベンチからすぐに代わりを出す。出せなければ負け。両方同時なら番でない側が先に出す", "p.313, pp.323-324", ("NEO-2000-OFFICIAL-RULES",)),
        RuleReference("win_conditions", "サイドを取り終えた、バトル場に出せるポケモンがいない、番の最初に山札がない。同時に満たしたら勝敗の表（条件の数が多いほうの勝ち、同じならサドン・デス）", "p.309, p.311, p.312", ("NEO-2000-OFFICIAL-RULES", "sudden_death")),
        RuleReference("sudden_death", "サドン・デスは、カードをすべてデッキにもどし、サイド 1 枚で最初から対戦をやり直す", "p.324", ("NEO-2000-OFFICIAL-RULES", "sudden_death")),
        RuleReference("pokemon_check", "ポケモンチェックはどちらの番でもない。指示されたこと → どく → ねむり → マヒ。きぜつの判定は手順にない", "p.323", ("NEO-2000-OFFICIAL-RULES", "knockout_timing")),
        # v0.2b（トレーナー）
        RuleReference("trainer", "手札のトレーナーカードを自分の番に使える。1 番に何枚でも。手札から出して見せ、名前を伝え、使うための条件・説明の順にしたがう。使ったカードはトラッシュ（使いすて）。使っている最中はほかのことはできない。番の最初に引く前・ワザの最中は使えない", "p.309, p.310", ("NEO-2000-OFFICIAL-RULES", "first_turn_actions")),
        RuleReference("draw_by_effect", "「カードを引く」は自分の山札の一番上を手札に。引いたカードは見せなくてよい。トレーナー・ワザの効果で引くときは、山札が足りなくても負けにならず、引けるだけ引く。最後の 1 枚を引いて山札がなくなっても負けではない", "p.311, p.312", ("NEO-2000-OFFICIAL-RULES",)),
        RuleReference("damage_counter", "ダメージは 10 の倍数で、ダメージカウンター 1 個が 10 ダメージ。回復はダメージカウンターをとりのぞくこと。すべてとりのぞいたら、それ以上は回復しない", "p.319, p.320", ("NEO-2000-OFFICIAL-RULES",)),
        RuleReference("switch", "対戦ポケモンと控えポケモンを入れ替えることを「ポケモンの入れ替え」と呼ぶ。「にげる」もその一つ。移動するポケモンのカード・カウンターはいっしょに移動する", "p.311, p.325", ("NEO-2000-OFFICIAL-RULES",)),
        RuleReference("same_timing", "同じタイミングで複数のことがらが起こったら、特に指示がないかぎり、番のプレイヤーが処理の順番を決める", "p.325", ("NEO-2000-OFFICIAL-RULES",)),
        # v0.2d（コイン・コインを投げるワザ）
        RuleReference("coin_toss", "ワザなどを使うとき、コインを投げて「おもて」か「うら」かを判定する（コイントス）。コインは何でもよい。両方のプレイヤーに見えないところに落ちたら投げなおす", "p.319", ("NEO-2000-OFFICIAL-RULES",)),
        RuleReference("attack_text", "ワザを使う手順の 6 で、ワザの説明に書かれている順番にしたがって処理する。ダメージの目安に「×」があれば、説明にしたがって計算した数のダメージ（0 倍になり、ダメージがなくなることもある）。説明で特に指定されていなければ、ダメージを受けるのは相手の対戦ポケモン", "p.309, p.320", ("NEO-2000-OFFICIAL-RULES",)),
        RuleReference("attack_failure", "ワザが失敗した場合でも、そのポケモンは、そのワザを使ったことになる", "p.323", ("NEO-2000-OFFICIAL-RULES",)),
    ]
}

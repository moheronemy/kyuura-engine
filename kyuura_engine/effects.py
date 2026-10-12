"""カードの効果の実装の登録表（v0.2a、レビューの M5。v0.2b でトレーナーを加えた）。

カードのデータ（kyuura の写し。印刷された文面と数値）と、エンジンが実装している処理を分けます。
あるワザ・トレーナーを対戦で使えるのは、この登録表にその実装が登録されているときだけです。
説明文が空であることは、実装がある証拠として扱いません（説明文のないワザも、効果のないワザとして
明示的に登録します）。

識別子は、ワザなら ``AttackKey``（カード id とワザの位置）、トレーナーならカード id です。
名前は識別子にしません。同じ名前でも、カードが違えば別の登録です。登録するときに確かめた名前・文面
（``AttackEntry.name_ja``、``TrainerEntry.name_ja``・``text_ja``）は、データが変わったときに
気づくための照合にだけ使います。

登録している実装:

- ワザ: ``DamageOnly``（説明のないワザ）、``CoinFlipDamage``（v0.2d。コインを投げ、「おもて」の数×の
  ダメージ。ドードーの「みだれづき」。p.231 の最新の説明。docs/coin-attacks-v0.2d.md）
- トレーナー（v0.2b）: マサキ ``DrawCards``、きずぐすり ``RemoveDamageCounters``、
  ポケモンいれかえ ``SwitchWithBench``。処理は『ポケモンカードオフィシャルブック2000』p.254 の
  「最新の説明」にしたがう（``TrainerEntry.play_text_ja``。docs/trainers-v0.2b.md）
- つけて使うトレーナー（v0.2c）: プラスパワー ``AttachedAttackBonus``（p.257 の最新の説明。
  docs/pluspower-v0.2c.md）。カードはポケモンについて場に残り（``PokemonInPlay.trainers``）、
  ダメージ計算の 5 段階で効果を出し、番の終わりにエンジンがトラッシュする
- つけて使うトレーナー（v0.2e）: ディフェンダー ``AttachedDamageReduction``（p.257 の最新の説明。
  docs/defender-v0.2e.md）。自分の場のポケモンを選んでつけ、ついているポケモンがワザで受けるダメージを
  7 段階で減らし、次の相手の番の終わりにエンジンがトラッシュする

ポケモンパワー・特殊エネルギー・ほかの効果のあるワザ・ほかのトレーナーは、実装を登録するまで未対応です。
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Iterable, Mapping

from .coins import flip_coins
from .damage import DamageModifier, calculate_attack_damage
from .decisions import SELECT_POKEMON, push_trainer_decision
from .errors import UnsupportedError
from .zones import attach_trainer, draw_cards

if TYPE_CHECKING:
    from .cards import Attack, CardDefinition
    from .state import AttachedTrainer, GameState, PendingDecision, PokemonInPlay


@dataclass(frozen=True, order=True)
class AttackKey:
    """ワザの安定した識別子: カード id とワザの位置（カードに印刷された順、0 から）。"""

    card_id: str
    attack_index: int

    def __str__(self) -> str:
        return f"{self.card_id}#{self.attack_index}"


@dataclass(frozen=True)
class AttackUse:
    """ワザを 1 回使ったときの情報。効果の処理（``resolve``・``resume``）に渡す。"""

    player: int
    pokemon_id: int
    key: AttackKey


class AttackEffect:
    """ワザの効果の実装の基底。

    - ``check``: カードのデータ（説明文・ダメージ）がこの実装で処理できる形かを確かめ、問題を返す。
      登録の誤り（効果のあるワザを、効果のない実装に登録するなど）を見つけるため。
    - ``resolve``: ワザの処理（p.309 の手順 6「ワザの説明にしたがって処理」）。途中でプレイヤーの
      決定が要るときは、``decisions.push_decision`` で決定を出して戻る。
    - ``resume``: 出した決定が選ばれたあとの続き。さらに決定を出してもよい（複数段階の選択）。

    決定がなくなったら、エンジンがワザの後の処理（きぜつ・サイド・番の終わり）を続ける。
    """

    implementation_id = "abstract"

    def check(self, attack: Attack) -> list[str]:
        return []

    def resolve(self, state: GameState, use: AttackUse) -> None:
        raise NotImplementedError

    def resume(self, state: GameState, use: AttackUse, decision: PendingDecision, choices: tuple[int, ...]) -> None:
        raise NotImplementedError(f"{self.implementation_id} は決定を出さない")


@dataclass(frozen=True)
class DamageOnly(AttackEffect):
    """説明のないワザ: ダメージの目安の数字ぶんのダメージを、相手のバトル場のポケモンに与える（p.309, p.320）。

    ダメージは p.321 の順番で計算する（``damage.calculate_attack_damage``）。
    """

    implementation_id = "damage_only"

    def check(self, attack: Attack) -> list[str]:
        problems = []
        if attack.text_ja is not None or attack.text_en is not None:
            problems.append("説明文のあるワザを、効果のないワザとして登録している")
        if attack.damage_modifier is not None:
            problems.append(f"ダメージの「{attack.damage_modifier}」があるワザを、効果のないワザとして登録している")
        if type(attack.damage) is not int or attack.damage <= 0 or attack.damage % 10:
            problems.append("ダメージが 10 の倍数の正の数ではない")
        return problems

    def resolve(self, state: GameState, use: AttackUse) -> None:
        _, attacker = state.find_pokemon(use.pokemon_id)
        attack = state.card_def(attacker.card).attacks[use.key.attack_index]
        damage_opponent_active(state, use, attack.damage)


@dataclass(frozen=True)
class CoinFlipDamage(AttackEffect):
    """コインを ``coins`` 枚投げ、「おもて」の数 × ``damage_per_heads`` のダメージを、相手の対戦ポケモンに与える
    （v0.2d。ドードーの「みだれづき」。p.231 の最新の説明「コインを2枚投げ、「おもて」の数×10のダメージ。」）。

    - ダメージの目安に「×」があるワザは、ワザの説明にしたがって計算した数のダメージを与える。0 倍になり、
      ダメージがなくなることもある（p.320）。ダメージを受けるのは、説明で特に指定されていないので、相手の
      対戦ポケモン（p.320）。
    - コインはワザの説明にしたがう処理（p.309 の手順 6）の中で投げる。必要なエネルギーの確認（手順 2）など、
      ワザを使えるかの確認は、エンジンが投げる前に済ませている。
    - 「おもて」の数 × ``damage_per_heads`` が p.321 の 1 段階（基本となるダメージ）。「おもて」が 0 枚なら 0 で、
      2 段階までで 0 以下なので計算を終え、「ダメージを与えなかった」（弱点・抵抗力・プラスパワーは計算しない）。
      これはワザの「失敗」（p.323）ではない（説明に「失敗」とは書かれていない）。どちらでも、ワザは使ったことになる。
    """

    coins: int
    damage_per_heads: int
    implementation_id = "coin_flip_damage"

    def __post_init__(self) -> None:
        if not isinstance(self.coins, int) or isinstance(self.coins, bool) or self.coins < 1:
            raise ValueError(f"コインの枚数は 1 以上の整数（{self.coins!r}）")
        if type(self.damage_per_heads) is not int or self.damage_per_heads <= 0 or self.damage_per_heads % 10:
            raise ValueError(f"「おもて」1 枚あたりのダメージは 10 の倍数の正の数（{self.damage_per_heads!r}）")

    def check(self, attack: Attack) -> list[str]:
        problems = []
        if attack.damage_modifier != "×":
            problems.append("ダメージの目安に「×」のないワザを、「おもて」の数×のワザとして登録している")
        if attack.damage != self.damage_per_heads:
            problems.append(f"ダメージの目安の数字 {attack.damage!r} と、登録した「おもて」1 枚あたりのダメージ {self.damage_per_heads} が違う")
        if attack.text_ja is None:
            problems.append("説明文のないワザを、コインを投げるワザとして登録している")
        return problems

    def resolve(self, state: GameState, use: AttackUse) -> None:
        _, attacker = state.find_pokemon(use.pokemon_id)
        flips = flip_coins(
            state, use.player, self.coins, source="attack", effect=str(use.key), card=attacker.card, pokemon_id=attacker.pokemon_id
        )
        damage_opponent_active(state, use, flips.heads * self.damage_per_heads)


def damage_opponent_active(state: GameState, use: AttackUse, base: int) -> None:
    """ワザで、相手の対戦ポケモンに、基本となるダメージ ``base`` から p.321 の順番で計算したダメージを与える。

    計算は ``damage.calculate_attack_damage``。ログの ``damage`` は v0.1 と同じ形で、変更効果を計算したとき
    だけ ``modifiers``（v0.2c）、2 段階までで 0 以下になって計算を終えたときだけ ``stopped_after_step_2``（v0.2d）を加える。
    """
    _, attacker = state.find_pokemon(use.pokemon_id)
    attacker_def = state.card_def(attacker.card)
    opponent = 1 - use.player
    defender = state.players[opponent].active
    defender_def = state.card_def(defender.card)
    modifiers = attack_damage_modifiers(state, attacker, defender)
    calc = calculate_attack_damage(base, attacker_def, defender_def, state.rules, modifiers)
    defender.damage += calc.final
    extra = {}
    if calc.modifiers:
        # v0.2c: どのカードの効果を、どの段階で計算したか（変更効果がないときは v0.1 と同じ形）
        extra["modifiers"] = tuple((m.step, m.source, m.amount) for m in calc.modifiers)
    if calc.stopped_after_step_2:
        # v0.2d: 基本となるダメージ（と 2 段階）で 0 以下。弱点・抵抗力・5〜8 段階は計算していない（p.321）
        extra["stopped_after_step_2"] = True
    state.add_event(
        "damage",
        player=opponent,
        pokemon=defender.card,
        amount=calc.final,
        steps=calc.steps,
        weakness=calc.weakness_applied,
        resistance=calc.resistance_applied,
        total_damage=defender.damage,
        **extra,
    )


def attack_damage_modifiers(state: GameState, attacker: PokemonInPlay, defender: PokemonInPlay) -> tuple[DamageModifier, ...]:
    """ワザで相手の対戦ポケモンにダメージを与えるときの、ついているカードによる変更効果（v0.2c）。

    ワザを使うポケモンについているカードは 5 段階、ワザを受けるポケモンについているカードは 7 段階（p.321）。
    効果の内容は、ついているカードのカード id で効果の登録表から引く（エンジンはカードの種類を知らない）。
    """
    modifiers: list[DamageModifier] = []
    for holder, role in ((attacker, "attacker"), (defender, "defender")):
        for attached in holder.trainers:
            entry = state.effects.trainer_entry(state.cards[attached.card].card_id)
            modifiers.extend(entry.effect.damage_modifiers(state, attached, role))
    return tuple(modifiers)


DAMAGE_ONLY = DamageOnly()


@dataclass(frozen=True)
class AttackEntry:
    """登録の 1 件: 実装と、登録したときに確かめたワザ名。

    説明文のあるワザ（v0.2d から）は、次も書く（説明文のないワザは None のまま）。

    - ``text_ja``: 登録したときに照合した kyuura の写しの説明文（データが変わったら使えなくなる。
      印刷の文面で、処理の根拠ではない）
    - ``play_text_ja``: 実装がしたがう文面（『オフィシャルブック2000』の「最新の説明」）
    - ``source``: ``play_text_ja`` の出典（誌面のページ）
    """

    effect: AttackEffect
    name_ja: str
    text_ja: str | None = None
    play_text_ja: str | None = None
    source: str | None = None


# ---------------------------------------------------------------- トレーナー（v0.2b）


@dataclass(frozen=True)
class TrainerUse:
    """トレーナーカードを 1 回使ったときの情報。効果の処理（``check_playable``・``resolve``・``resume``）に渡す。"""

    player: int
    card: int  # 使っているトレーナーカードの uid
    card_id: str


class TrainerEffect:
    """トレーナーカードの効果の実装の基底（v0.2b）。

    エンジン（``engine._play_trainer``）が、公式ルールの「トレーナーカードを使う」（p.310）の順番で呼ぶ。

    - ``check``: カードのデータがこの実装で扱える形かを確かめ、問題を返す（登録の誤りを見つけるため）。
    - ``check_playable``: 使えるかを確かめる。状態は変えない。カードに書かれた「使うための条件」を
      満たせないなら ``IllegalActionError``、原典で決められない場合は ``UnsupportedError``。
      拒否したら、カードは手札に残る。
    - ``resolve``: カードの説明にしたがう。途中でプレイヤーの決定が要るときは
      ``decisions.push_trainer_decision`` で決定を出して戻る。
    - ``resume``: 出した決定が選ばれたあとの続き。さらに決定を出してもよい（複数段階の選択）。

    手札から出す・相手に見せる・使い終わったらトラッシュする・番の続きにもどる、はエンジンが行う。

    つけて使うトレーナー（v0.2c）は ``stays_in_play = True`` にし、``resolve``（対象を選ぶなら ``resume``）で
    カードを場のポケモンにつける（``zones.attach_trainer``）。使い終わってもトラッシュせず、ついている間
    ``damage_modifiers`` でダメージ計算に効果を出す。トラッシュは、つけたときに決めた番の終わりに、エンジンが
    行う。その番は ``attachment_discard_turn``（使った番 + ``discard_turn_offset``）。番は 1 番ずつ交互に
    進む（p.309）ので、0 は使った番（自分の番）、1 は次の相手の番（v0.2e）。
    """

    implementation_id = "abstract"
    stays_in_play = False  # True: 使い終わったら場に残る（つけて使うトレーナー）。False: 使いすて（p.310）
    discard_turn_offset = 0  # つけて使うトレーナーをトラッシュする番: 使った番から数えていくつ後の番の終わりか

    def check(self, definition: CardDefinition) -> list[str]:
        if definition.trainer_kinds:
            return [f"種類 {list(definition.trainer_kinds)} のトレーナーは、この実装では扱えない"]
        return []

    def check_playable(self, state: GameState, use: TrainerUse) -> None:
        return None

    def resolve(self, state: GameState, use: TrainerUse) -> None:
        raise NotImplementedError

    def resume(self, state: GameState, use: TrainerUse, decision: PendingDecision, choices: tuple[int, ...]) -> None:
        raise NotImplementedError(f"{self.implementation_id} は決定を出さない")

    def damage_modifiers(self, state: GameState, attached: AttachedTrainer, role: str) -> list[DamageModifier]:
        """ついているポケモンがワザを使う（``role="attacker"``）・受ける（``"defender"``）ときの変更効果。"""
        return []

    def attachment_discard_turn(self, state: GameState) -> int:
        """今つけるなら、トラッシュする番（``GameState.turn_number``）。"""
        return state.turn_number + self.discard_turn_offset


@dataclass(frozen=True)
class DrawCards(TrainerEffect):
    """山札からカードを ``count`` 枚引いて、手札に加える（マサキ。p.254 の最新の説明）。

    - 引くのは自分の山札の一番上から（p.312「カードを引く」）。
    - 山札が足りなくても負けにはならず、引けるだけ引く。山札が 0 枚なら 0 枚（p.312）。
      山札がなくなった段階でも負けではない。負けになるのは、番の最初に引けないとき（p.309, p.312）。
    - 引いたカードを相手に見せる必要はない（p.312）。乱数は使わない。
    """

    count: int
    implementation_id = "draw_cards"

    def resolve(self, state: GameState, use: TrainerUse) -> None:
        deck = state.players[use.player].deck
        draw_cards(state, use.player, min(self.count, len(deck)))


@dataclass(frozen=True)
class RemoveDamageCounters(TrainerEffect):
    """自分の場のポケモンを 1 匹選び、のっているダメージカウンターを ``counters`` 個とりのぞく
    （きずぐすり。p.254 の最新の説明「あなたの場にいるポケモンを1匹選び、そのポケモンにのっている
    ダメージカウンターを、2個とりのぞく。」）。

    - 選ぶのは自分の場（バトル場とベンチ。p.312）のポケモン 1 匹。場のポケモンの番号で選ぶ。
    - とりのぞく数は選べない。のっている数が ``counters`` 個以上なら ``counters`` 個（p.254 の解説
      「2個のっていたら2個とってください」）、少なければ全部（すべてとりのぞいたら、それ以上は回復しない。p.320）。
    - ダメージカウンター 1 個は 10 ダメージ（p.319。``RuleSet.damage_per_counter``）。

    原典で決められないので扱わない（``UnsupportedError``）:

    - 自分の場にダメージカウンターののったポケモンが 1 匹もいないときに使えるか
    - ダメージカウンターののっていないポケモンを選べるか（選べるものには入れるが、選ぶと拒否する）
    """

    counters: int
    implementation_id = "remove_damage_counters"

    def check_playable(self, state: GameState, use: TrainerUse) -> None:
        if not any(pokemon.damage > 0 for pokemon in state.players[use.player].in_play()):
            raise UnsupportedError(
                "UNRESOLVED_POTION_WITHOUT_DAMAGE",
                "自分の場にダメージカウンターののったポケモンがいない。このときに「きずぐすり」を使えるかは、"
                "『オフィシャルブック2000』（p.254・p.310）から決められないので扱わない",
            )

    def resolve(self, state: GameState, use: TrainerUse) -> None:
        own = state.players[use.player].in_play()
        push_trainer_decision(
            state,
            use,
            kind=SELECT_POKEMON,
            player=use.player,
            options=[pokemon.pokemon_id for pokemon in own],
            unresolved_choices=[pokemon.pokemon_id for pokemon in own if pokemon.damage == 0],
            unresolved_code="UNRESOLVED_POTION_UNDAMAGED_TARGET",
            unresolved_reason=(
                "ダメージカウンターののっていないポケモンを「きずぐすり」の対象に選べるかは、"
                "『オフィシャルブック2000』（p.254・p.320）から決められないので扱わない"
            ),
        )

    def resume(self, state: GameState, use: TrainerUse, decision: PendingDecision, choices: tuple[int, ...]) -> None:
        _, pokemon = state.find_pokemon(choices[0])
        per_counter = state.rules.damage_per_counter
        removed = min(self.counters, pokemon.damage // per_counter)
        pokemon.damage -= removed * per_counter
        state.add_event(
            "remove_damage_counters",
            player=use.player,
            pokemon=pokemon.card,
            pokemon_id=pokemon.pokemon_id,
            counters=removed,
            total_damage=pokemon.damage,
        )


@dataclass(frozen=True)
class SwitchWithBench(TrainerEffect):
    """自分の控えポケモンを 1 匹選び、自分の対戦ポケモンと入れ替える（ポケモンいれかえ。p.254 の最新の説明）。

    - 「にげる」ではない（「にげる」も「ポケモンの入れ替え」の一つだが、逆ではない。p.325）。にげる
      エネルギーは払わない。「にげる」は 1 番に何度でもできる（p.311）ので、回数の管理とは関係しない。
    - 移動するポケモンについているカード・ダメージカウンターは、いっしょに移動する（p.311）。
      場のポケモン（``PokemonInPlay``）ごと入れ替えるので、カードの uid・場のポケモンの番号も変わらない。

    原典で決められないので扱わない（``UnsupportedError``）: 控えポケモンがいないときに使えるか。
    """

    implementation_id = "switch_with_bench"

    def check_playable(self, state: GameState, use: TrainerUse) -> None:
        if not state.players[use.player].bench:
            raise UnsupportedError(
                "UNRESOLVED_SWITCH_WITHOUT_BENCH",
                "控えポケモンがいない。このときに「ポケモンいれかえ」を使えるかは、"
                "『オフィシャルブック2000』（p.254・p.310）から決められないので扱わない",
            )

    def resolve(self, state: GameState, use: TrainerUse) -> None:
        bench = state.players[use.player].bench
        push_trainer_decision(
            state, use, kind=SELECT_POKEMON, player=use.player, options=[pokemon.pokemon_id for pokemon in bench]
        )

    def resume(self, state: GameState, use: TrainerUse, decision: PendingDecision, choices: tuple[int, ...]) -> None:
        p = state.players[use.player]
        index = next(i for i, pokemon in enumerate(p.bench) if pokemon.pokemon_id == choices[0])
        old = p.active
        p.active, p.bench[index] = p.bench[index], old
        state.add_event(
            "switch",
            player=use.player,
            old_active=old.card,
            new_active=p.active.card,
            old_active_pokemon_id=old.pokemon_id,
            new_active_pokemon_id=p.active.pokemon_id,
        )


@dataclass(frozen=True)
class AttachedAttackBonus(TrainerEffect):
    """自分の対戦ポケモンにつけて使い、自分の番の終わりにトラッシュする。つけているポケモンのワザが
    対戦ポケモンにダメージを与えるとき、そのダメージは ``+amount``（プラスパワー。p.257 の最新の説明）。

    - つけるのは自分の対戦ポケモン（バトル場のポケモン）。選ぶものはないので決定は出さない。
    - 効果はダメージ計算の 5 段階（弱点・抵抗力のあと。p.321）。計算の途中の 0・マイナスはそのまま続ける。
      2 段階までで 0 以下なら計算を終える（ダメージを与えないワザには効果がない）。
    - 有効期限は、使った番の終わり。カードはついているポケモンといっしょに移り（にげる・入れ替え。p.311）、
      きぜつしたらいっしょにトラッシュする（p.323）。
    - 控えポケモンへのダメージは変えない（最新の説明）。自分自身へのダメージ（p.257 の解説では +10 される）
      を与えるワザはまだないので、``attack_damage_modifiers`` は相手の対戦ポケモンへのダメージにだけ使う。
    """

    amount: int
    implementation_id = "attached_attack_bonus"
    stays_in_play = True

    def resolve(self, state: GameState, use: TrainerUse) -> None:
        active = state.players[use.player].active
        attach_trainer(state, use.player, use.card, active, discard_at_end_of_turn=self.attachment_discard_turn(state))

    def damage_modifiers(self, state: GameState, attached: AttachedTrainer, role: str) -> list[DamageModifier]:
        if role != "attacker":
            return []
        name = state.card_def(attached.card).name_ja
        return [DamageModifier(step=5, amount=self.amount, label=name, source=attached.card)]


@dataclass(frozen=True)
class AttachedDamageReduction(TrainerEffect):
    """自分の場のポケモンを 1 匹選んでつけ、次の相手の番の終わりにトラッシュする。つけているポケモンが
    ワザによるダメージを受けるとき、そのダメージは ``-amount``（ディフェンダー。p.257 の最新の説明
    「このカードは、あなたの場にいるポケモンにつけて使い、次の相手の番の終わりにトラッシュする。このカードを
    つけているポケモンがワザによるダメージを受けるとき、そのダメージは「-20」される。」。docs/defender-v0.2e.md）。

    - つけるのは自分の場（バトル場とベンチ。p.312・p.313）のポケモン。1 匹でも選ぶ決定を出す（場のポケモンの番号）。
    - 効果はダメージ計算の 7 段階（ワザを受けるポケモンについているカードの効果。p.321 がディフェンダーを例に
      挙げる）。弱点・抵抗力・5 段階（プラスパワー）のあと。途中の 0・マイナスはそのまま続ける。2 段階までで
      0 以下なら計算を終える（7 段階に進まない）。
    - 有効期限は次の相手の番の終わり（``discard_turn_offset = 1``）。効果はカードがついている間だけあり、
      カードをトラッシュする時点で終わる（最新の説明では、効果の終わりとトラッシュの時点が同じ）。
    - ワザで受けるダメージだけを減らす（ワザを使うときのダメージは変えない。どくのダメージは変えない。p.322）。
      自分のワザで自分が受けるダメージにも効く（p.257 の解説）が、そのワザはまだない。今は、相手のワザで
      対戦ポケモンが受けるダメージ（``attack_damage_modifiers`` の ``role="defender"``）にだけ使う。
    """

    amount: int
    implementation_id = "attached_damage_reduction"
    stays_in_play = True
    discard_turn_offset = 1

    def resolve(self, state: GameState, use: TrainerUse) -> None:
        own = state.players[use.player].in_play()
        push_trainer_decision(state, use, kind=SELECT_POKEMON, player=use.player, options=[pokemon.pokemon_id for pokemon in own])

    def resume(self, state: GameState, use: TrainerUse, decision: PendingDecision, choices: tuple[int, ...]) -> None:
        owner, pokemon = state.find_pokemon(choices[0])
        if owner != use.player:
            raise RuntimeError(f"相手の場のポケモン {choices[0]} にディフェンダーをつけようとした（エンジンの不具合）")
        attach_trainer(state, use.player, use.card, pokemon, discard_at_end_of_turn=self.attachment_discard_turn(state))

    def damage_modifiers(self, state: GameState, attached: AttachedTrainer, role: str) -> list[DamageModifier]:
        if role != "defender":
            return []
        name = state.card_def(attached.card).name_ja
        return [DamageModifier(step=7, amount=-self.amount, label=name, source=attached.card)]


@dataclass(frozen=True)
class TrainerEntry:
    """トレーナーの登録の 1 件。

    - ``effect``: 実装
    - ``name_ja``・``text_ja``: 登録したときに照合した kyuura の写しの名前・文面（データが変わったら
      使えなくなる。印刷の文面で、処理の根拠ではない）
    - ``play_text_ja``: 実装がしたがう文面（『オフィシャルブック2000』の「最新の説明」）
    - ``source``: ``play_text_ja`` の出典（誌面のページ）
    """

    effect: TrainerEffect
    name_ja: str
    text_ja: str
    play_text_ja: str
    source: str


# ---------------------------------------------------------------- 登録表


class EffectRegistry:
    """カードの効果の実装の登録表。対戦ごとに 1 つ使う（``GameState.effects``）。

    ワザ（``AttackKey`` → ``AttackEntry``）と、トレーナー（カード id → ``TrainerEntry``、v0.2b）を
    登録できます。ポケモンパワー・特殊エネルギーの実装は、それを加えるときに同じ形（安定した識別子 →
    実装）で欄を加えます。それまでは、これらのカードは未対応です。登録表は変えられません
    （``with_*``・``without_*`` は新しい登録表を返す）。
    """

    def __init__(
        self,
        registry_id: str,
        attacks: Mapping[AttackKey, AttackEntry] | Iterable[tuple[AttackKey, AttackEntry]],
        trainers: Mapping[str, TrainerEntry] | Iterable[tuple[str, TrainerEntry]] = (),
    ):
        self.id = registry_id
        self._attacks: dict[AttackKey, AttackEntry] = dict(attacks)
        self._trainers: dict[str, TrainerEntry] = dict(trainers)

    def __repr__(self) -> str:
        return f"EffectRegistry({self.id!r}, {len(self._attacks)} attacks, {len(self._trainers)} trainers)"

    # --- ワザ ---

    def attack_keys(self) -> tuple[AttackKey, ...]:
        return tuple(sorted(self._attacks))

    def attack_entry(self, card_id: str, attack_index: int) -> AttackEntry | None:
        return self._attacks.get(AttackKey(card_id, attack_index))

    def attack_problem(self, card_id: str, attack: Attack) -> str | None:
        """このワザを使えない理由。使えるなら None。"""
        entry = self.attack_entry(card_id, attack.index)
        if entry is None:
            features = []
            if attack.text_ja is not None or attack.text_en is not None:
                features.append("説明文あり")
            if attack.damage_display is not None:
                features.append(f"ダメージ「{attack.damage_display}」")
            detail = f"（{'・'.join(features)}）" if features else ""
            return f"ワザの効果の実装が登録されていない{detail}"
        if entry.name_ja != attack.name_ja:
            return f"登録したワザ名「{entry.name_ja}」と、データのワザ名「{attack.name_ja}」が違う"
        if entry.text_ja != attack.text_ja:
            return "登録したときに照合した説明文と、データの説明文が違う（データが変わった。照合し直す必要がある）"
        problems = entry.effect.check(attack)
        return "; ".join(problems) or None

    def attack_effect(self, card_id: str, attack: Attack) -> AttackEffect | None:
        """使えるワザなら実装を返す。登録がない・データと合わないなら None。"""
        if self.attack_problem(card_id, attack) is not None:
            return None
        return self.attack_entry(card_id, attack.index).effect

    def with_attacks(self, registry_id: str, attacks: Mapping[AttackKey, AttackEntry]) -> EffectRegistry:
        """登録を加えた新しい登録表（元の登録表は変えない）。テストや、実装を段階的に加えるときに使う。"""
        return EffectRegistry(registry_id, {**self._attacks, **attacks}, self._trainers)

    def without_attacks(self, registry_id: str, keys: Iterable[AttackKey]) -> EffectRegistry:
        """登録を除いた新しい登録表（元の登録表は変えない）。"""
        removed = set(keys)
        return EffectRegistry(registry_id, {k: v for k, v in self._attacks.items() if k not in removed}, self._trainers)

    # --- トレーナー（v0.2b） ---

    def trainer_ids(self) -> tuple[str, ...]:
        return tuple(sorted(self._trainers))

    def trainer_entry(self, card_id: str) -> TrainerEntry | None:
        return self._trainers.get(card_id)

    def trainer_problem(self, definition: CardDefinition) -> str | None:
        """このトレーナーカードを使えない理由。使えるなら None。名前や説明文の有無では決めない。"""
        if definition.category != "trainer":
            return "トレーナーカードではない"
        entry = self.trainer_entry(definition.id)
        if entry is None:
            return "トレーナーカードの効果の実装が登録されていない"
        if entry.name_ja != definition.name_ja:
            return f"登録した名前「{entry.name_ja}」と、データの名前「{definition.name_ja}」が違う"
        if entry.text_ja != definition.trainer_text_ja:
            return "登録したときに照合した文面と、データの文面が違う（データが変わった。照合し直す必要がある）"
        problems = entry.effect.check(definition)
        return "; ".join(problems) or None

    def trainer_effect(self, definition: CardDefinition) -> TrainerEffect | None:
        """使えるトレーナーなら実装を返す。登録がない・データと合わないなら None。"""
        if self.trainer_problem(definition) is not None:
            return None
        return self.trainer_entry(definition.id).effect

    def with_trainers(self, registry_id: str, trainers: Mapping[str, TrainerEntry]) -> EffectRegistry:
        """トレーナーの登録を加えた新しい登録表（元の登録表は変えない）。"""
        return EffectRegistry(registry_id, self._attacks, {**self._trainers, **trainers})

    def without_trainers(self, registry_id: str, card_ids: Iterable[str]) -> EffectRegistry:
        """トレーナーの登録を除いた新しい登録表（元の登録表は変えない）。"""
        removed = set(card_ids)
        return EffectRegistry(registry_id, self._attacks, {k: v for k, v in self._trainers.items() if k not in removed})

    def describe(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "attacks": {
                str(k): {"implementation": e.effect.implementation_id, "name_ja": e.name_ja}
                | ({} if e.source is None else {"source": e.source})
                for k, e in sorted(self._attacks.items())
            },
            "trainers": {
                k: {"implementation": e.effect.implementation_id, "name_ja": e.name_ja, "source": e.source}
                for k, e in sorted(self._trainers.items())
            },
        }


def _damage_only(entries: Iterable[tuple[str, int, str]]) -> dict[AttackKey, AttackEntry]:
    return {AttackKey(card_id, index): AttackEntry(DAMAGE_ONLY, name) for card_id, index, name in entries}


# 登録。ワザは v0.1 で使えたワザ（説明文のない固定ダメージのワザ）を、効果のないワザとして登録する。
# どれも『ポケモンカードオフィシャルブック2000』のカードのページで、「ワザ」欄に説明文がないことを
# 画像で確かめた（kyuura_engine/data/card_verification.json）。ワザ名は kyuura の写しの値（照合用）。
# トレーナー（v0.2b）は p.254、プラスパワー（v0.2c）・ディフェンダー（v0.2e）は p.257、ドードーの「みだれづき」
# （v0.2d）は p.231 の画像で「最新の説明」を確かめた（同じファイル。docs/trainers-v0.2b.md・
# docs/pluspower-v0.2c.md・docs/coin-attacks-v0.2d.md・docs/defender-v0.2e.md）。
DEFAULT_EFFECTS = EffectRegistry(
    "kyuura-engine-0.2e",
    _damage_only([
        ("PMCG1-016", 0, "けりとばす"),  # ポニータ。p.75 は「けとばす」（kyuura との食い違い。data-provenance.md）
        ("PMCG1-016", 1, "ほのおのしっぽ"),
        ("PMCG1-018", 0, "ほのお"),  # ガーディ p.72
        ("PMCG1-025", 0, "ひらてうち"),  # ヒトデマン p.110
        ("PMCG1-029", 0, "ずつき"),  # パウワウ p.101
        ("PMCG1-037", 0, "たいあたり"),  # ビリリダマ p.136
        ("PMCG1-052", 0, "あなをほる"),  # ディグダ p.182
        ("PMCG1-052", 1, "どろかけ"),
        ("PMCG1-053", 0, "けたぐり"),  # ワンリキー p.189
        ("PMCG1-058", 0, "ジャブ"),  # エビワラー p.203
        ("PMCG1-058", 1, "スペシャルパンチ"),
        ("PMCG1-060", 0, "かみつく"),  # コラッタ p.217
        ("PMCG1-065", 0, "はたく"),  # ミニリュウ p.246
        # ヒトカゲ（参照カード。デッキには入らない）の「ひっかく」。p.63 で説明文がないことを確かめた。
        # もう 1 つのワザ「ひのこ」は効果があり、登録していない（カードは未対応のまま）
        ("PMCG1-014", 0, "ひっかく"),
    ])
    | {
        # ドードー（v0.2d）p.231。ダメージの目安「10×」、説明はコイン 2 枚の「おもて」の数×10
        AttackKey("PMCG1-061", 0): AttackEntry(
            CoinFlipDamage(coins=2, damage_per_heads=10),
            "みだれづき",
            text_ja="コインを2枚投げて「おもて」の数×10のダメージをあたえる。",
            play_text_ja="コインを2枚投げ、「おもて」の数×10のダメージ。",
            source="P43 p.231",
        ),
    },
    {
        "PMCG1-071": TrainerEntry(
            RemoveDamageCounters(counters=2),
            "きずぐすり",
            "自分の場のポケモンにのっているダメージカウンターを2個まで、とりのぞくことができる。",
            "あなたの場にいるポケモンを1匹選び、そのポケモンにのっているダメージカウンターを、2個とりのぞく。",
            "P43 p.254",
        ),
        "PMCG1-073": TrainerEntry(
            SwitchWithBench(),
            "ポケモンいれかえ",
            "自分の場の対戦ポケモンと控えポケモンを入れ替える。「にげる」ためのエネルギーを支払う必要はない。",
            "あなたの控えポケモンを1匹選び、あなたの対戦ポケモンと入れ替える。",
            "P43 p.254",
        ),
        "PMCG1-074": TrainerEntry(
            DrawCards(count=2),
            "マサキ",
            "山札からカードを2枚引いて、手札に加える。",
            "山札からカードを2枚引いて、手札に加える。",
            "P43 p.254",
        ),
        "PMCG1-079": TrainerEntry(
            AttachedDamageReduction(amount=20),
            "ディフェンダー",
            "次の相手の番の終わりまで、「ワザ」によって受けるダメージを、「-20」できる。自分の場のポケモンにつけて使い、次の自分の番の最初にはがしてすてる。",
            "このカードは、あなたの場にいるポケモンにつけて使い、次の相手の番の終わりにトラッシュする。このカードをつけているポケモンがワザによるダメージを受けるとき、そのダメージは「-20」される。",
            "P43 p.257",
        ),
        "PMCG1-081": TrainerEntry(
            AttachedAttackBonus(amount=10),
            "プラスパワー",
            "自分の対戦ポケモンの「ワザ」によって与えるダメージを「+10」できる。自分の対戦ポケモンにつけて使い、自分の番の終わりに、はがしてすてる。",
            "このカードはあなたの対戦ポケモンにつけて使い、あなたの番の終わりにトラッシュする。このカードをつけているポケモンのワザが、対戦ポケモンにダメージを与えるとき、そのダメージは「+10」される。(控えポケモンへのダメージは、そのまま)",
            "P43 p.257",
        ),
    },
)

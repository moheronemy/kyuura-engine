"""わるいカメール（v0.13）を含む 60 枚のデッキで、正式な対戦開始（new_game）から勝敗まで。

わるいカメールのワザ「こうらがえし」（次の相手の番、このカードが相手のワザによってダメージを受けたとき、（それによってこのカードが「きぜつ」
しても、）そのポケモンにも同じダメージを与える。（ダメージ以外の効果は与えない）。p.89）と「おうふくびんた」（コイン 2 枚の「おもて」の数 × 10）
が、自然な対戦の中で、

- 第4弾・第1弾のゼニガメから進化したわるいカメールが使い、効果が次の相手の番にだけはたらき、相手のワザによるダメージを受けたとき、受けた
  ダメージ（最終ダメージ。HP で上限をつけない）を基本となるダメージにして、ダメージを与えた相手の対戦ポケモンに返すこと（弱点・抵抗力・
  ディフェンダー・「とうめい」を計算する。「はんげき」がはたらく）、ダメージ以外の効果より先に返すこと、
- 効果がその番の終わり・ベンチにもどったとき・きぜつしたときに消えること、原典で決められない場合（S37。W24 と同じコード）で止まること、
- 固定の量の「ほのおのかべ」（v0.12）が同じ仕組みで変わらずに動くこと

を確かめる（docs/v0.13-verification.md）。

- わるいカメールのデッキ（``WARTORTLE_DECK``）: 第4弾のゼニガメ 3・第1弾のゼニガメ 1・わるいカメール 4・ヒトデマン 3・パウワウ 2・トレーナー・水。
- 相手は、v0.12 の 2 つのデッキ（R団のファイヤーと炎のたねポケモン（弱点 水）。カイリキー・ゴースト・ベトベトン・バタフリー・ビードル・
  ユンゲラー・ピカチュウ（わるいカメールの弱点 雷）・サカキのカイリキー・R団のファイヤーなど）と、同じわるいカメールのデッキ（ミラー）。

盤面を直接作ったテスト（tests/test_shell_attack_v0_13.py）とは別に数える。根拠のページは docs/shell-attack-v0.13.md（p.88・p.89・p.309・
p.310・p.320〜p.325）。手順は tests/test_moltres_games_v0_12.py の ``policy_command`` に、次を加えたもの（対戦相手の AI ではない）:

- バトル場のわるいカメールは、こうらがえしを使えて番の番号が 3 の倍数でなければこうらがえし、そうでなければおうふくびんた（試していない
  ワザのうち）。
- ワザが ``UNRESOLVED_RETALIATION_DOUBLE_KNOCKOUT``（S37・W24）で止まったら、相手の対戦ポケモンに今の番にはたらく「こうらがえし」か
  「ほのおのかべ」があることを場から確かめ、その番はほかの使えるワザを 1 度だけ試し、なければ番を終える。

受けたダメージは、エンジンの関数を使わずにログから確かめる（``retaliation`` の ``received_damage`` は、直前の効果を持つポケモンへのダメージの
ログの ``amount``）。
"""

import hashlib
import json
import pickle
import unittest
from collections import Counter

from kyuura_engine import (
    AttachEnergy, EvolvePokemon, IllegalActionError, Phase, UnsupportedError, UseAttack, UsePokemonPower, apply_command,
    check_invariants, new_game, state_to_dict,
)
from kyuura_engine.decisions import POST_KNOCKOUT_POWER
from kyuura_engine.rng import copy_rng, rng_fingerprint
from tests.helpers import (
    CARD_DATA_COMMIT,
    with_card_data_commit_before_v0_69,
    BILL, DARK_WARTORTLE, DEFENDER, GIOVANNIS_MACHAMP, HAUNTER, MACHAMP, MUK, PLUSPOWER, POTION, ROCKET_SQUIRTLE, ROCKETS_MOLTRES, SEEL,
    SQUIRTLE, STARYU, SWITCH, WATER, coin_events, expand_decklist,
)
from tests.log_audit import log_problems, serialization_problems
from tests.test_alakazam_games_v0_7 import POWER_REJECTIONS
from tests.test_blastoise_games_v0_6 import R13
from tests.test_confusion_games import TERMINAL
from tests.test_evolution_games_v0_4a import EVOLUTION_REJECTIONS
from tests.test_giovanni_games_v0_11 import EFFECT_STOP, guts_available
from tests.test_harden_games_v0_4b import REJECTIONS
from tests.test_haunter_games_v0_9 import EVADED_COIN, affordable, card_id, gas_on
from tests.test_haunter_games_v0_9 import working as evasion_working
from tests.test_machamp_games_v0_10 import DOUBLE_KO
from tests.test_machamp_games_v0_10 import working as counter_working
from tests.test_moltres_games_v0_12 import MOLTRES_DECK_A, MOLTRES_DECK_B
from tests.test_moltres_games_v0_12 import policy_command as moltres_policy_command
from tests.test_stage2_games_v0_4c import STAGE2_REJECTIONS

# わるいカメールのデッキ（第4弾・第1弾のゼニガメからわるいカメールに進化する。「ゼニガメ」は名前が同じなので合わせて 4 枚まで。p.308）
WARTORTLE_DECK = expand_decklist({
    ROCKET_SQUIRTLE: 3, SQUIRTLE: 1, DARK_WARTORTLE: 4, STARYU: 3, SEEL: 2, SWITCH: 2, POTION: 2, BILL: 4, DEFENDER: 2, PLUSPOWER: 2,
    WATER: 35,
})
SEEDS = tuple(range(100))
RETALIATION_STOP = "UNRESOLVED_RETALIATION_DOUBLE_KNOCKOUT"
SHELL = f"{DARK_WARTORTLE}#1"
FIRE_WALL = f"{ROCKETS_MOLTRES}#0"
RECEIVED_KIND = "retaliation_received_damage"


def full(state):
    return state_to_dict(state, format_version=9)


def decks(seed):
    """seed を 4 で割った余りで相手を決め（0: R団のファイヤーと炎、1・2: いろいろなワザ、3: ミラー）、2 で割った余りで席を入れかえる。"""
    opponent = (MOLTRES_DECK_A, MOLTRES_DECK_B, MOLTRES_DECK_B, WARTORTLE_DECK)[seed % 4]
    return (WARTORTLE_DECK, opponent) if seed % 2 == 0 else (opponent, WARTORTLE_DECK)


def retaliation_on(state, pokemon):
    """今の番にはたらく、ダメージを返す効果（「こうらがえし」「ほのおのかべ」）を持つか（エンジンの関数を使わない。効果の値と番だけを見る）。"""
    return pokemon is not None and any(
        e.kind in ("retaliation", RECEIVED_KIND) and e.active_turn == state.turn_number for e in pokemon.persistent_effects)


def wartortle_attack(state, player, tried):
    """わるいカメールのワザ: こうらがえしを使えて番の番号が 3 の倍数でなければこうらがえし、そうでなければおうふくびんた（試していないもの）。"""
    usable = [i for i in affordable(state, player) if ("attack_index", i) not in tried]
    if 1 in usable and state.turn_number % 3 != 0:
        return UseAttack(player, 1)
    if 0 in usable:
        return UseAttack(player, 0)
    return UseAttack(player, 1) if 1 in usable else None


def policy_command(state, *, janken_winner, cure, tried):
    command = moltres_policy_command(state, janken_winner=janken_winner, cure=cure, tried=tried)
    if state.phase is not Phase.MAIN or not isinstance(command, UseAttack):
        return command
    player = state.current_player
    if card_id(state, state.players[player].active) == DARK_WARTORTLE and "retaliation_double" not in tried:
        return wartortle_attack(state, player, tried) or command
    return command


def play_game(seed, *, cure=True, max_steps=10000):
    """終わるまで進める。受け付けた操作の列と、拒否された操作・場面の観測を返す。"""
    state = new_game(*decks(seed), seed)
    commands, observed, tried = [], Counter(), {}
    for _ in range(max_steps):
        if state.phase in TERMINAL:
            return state, commands, observed
        while True:
            turn_tried = tried.setdefault(state.turn_number, set())
            command = policy_command(state, janken_winner=seed % 2, cure=cure, tried=turn_tried)
            try:
                new = apply_command(state, command)
                break
            except (IllegalActionError, UnsupportedError) as error:
                observed["rejected"] += 1
                if isinstance(command, UsePokemonPower):
                    kind = card_id(state, state.find_pokemon(command.pokemon)[1])
                    if error.code == "POWER_NOT_USABLE_NOW" and kind in (ROCKETS_MOLTRES, GIOVANNIS_MACHAMP) and not gas_on(state):
                        observed[f"rejected_declare_{kind}"] += 1
                        continue
                    if error.code == "POWER_NOT_DECLARABLE" and kind in (MUK, MACHAMP, HAUNTER):
                        observed[f"rejected_declare_{kind}"] += 1
                        continue
                    if error.code == "POWER_SUPPRESSED" and gas_on(state):
                        observed["suppressed_power"] += 1
                        continue
                    if error.code not in POWER_REJECTIONS:
                        raise
                    observed[f"rejected_power_{error.code}"] += 1
                    continue
                if isinstance(command, UseAttack) and error.code == RETALIATION_STOP:
                    # S37・W24: 相手の対戦ポケモンに、今の番にはたらくダメージを返す効果があるとき（エンジンとは別に場から確かめる）
                    target = state.players[1 - state.current_player].active
                    if not retaliation_on(state, target):
                        raise AssertionError(f"ダメージを返す効果がはたらいていないのに {RETALIATION_STOP}: {command}")
                    which = "shell" if any(e.kind == RECEIVED_KIND for e in target.persistent_effects) else "fire_wall"
                    observed[f"stopped_attack_{RETALIATION_STOP}"] += 1
                    observed[f"stopped_attack_{RETALIATION_STOP}_{which}"] += 1
                    turn_tried.update({"retaliation_double", ("attack_index", command.attack_index)})
                    continue
                if isinstance(command, UseAttack) and error.code == EFFECT_STOP:
                    target = state.players[1 - state.current_player].active
                    if not guts_available(state, target):
                        raise AssertionError(f"「こんじょう」を使えないのに {EFFECT_STOP}: {command}")
                    observed[f"stopped_attack_{EFFECT_STOP}"] += 1
                    turn_tried.update({"guts_effect", ("attack_index", command.attack_index)})
                    continue
                if isinstance(command, UseAttack) and error.code == DOUBLE_KO:
                    target = state.players[1 - state.current_player].active
                    if not counter_working(state, target):
                        raise AssertionError(f"「はんげき」がはたらいていないのに {DOUBLE_KO}: {command}")
                    observed[f"stopped_attack_{DOUBLE_KO}"] += 1
                    turn_tried.update({"counter_double", ("attack_index", command.attack_index)})
                    continue
                if isinstance(command, UseAttack) and error.code == EVADED_COIN:
                    target = state.players[1 - state.current_player].active
                    if not evasion_working(state, target):
                        raise AssertionError(f"「とうめい」がはたらいていないのに {EVADED_COIN}: {command}")
                    observed[f"stopped_attack_{EVADED_COIN}"] += 1
                    turn_tried.update({"evaded_coin", ("attack_index", command.attack_index)})
                    continue
                if isinstance(command, AttachEnergy):
                    if error.code != R13:
                        raise
                    observed[f"stopped_attach_{error.code}"] += 1
                    turn_tried.add("attach_blocked")
                    continue
                if isinstance(command, EvolvePokemon):
                    stage2 = state.card_def(command.card).is_stage2_pokemon
                    if error.code in (STAGE2_REJECTIONS if stage2 else EVOLUTION_REJECTIONS):
                        observed[f"rejected_{'evolve2' if stage2 else 'evolve'}_{error.code}"] += 1
                        turn_tried.add("evolve2" if stage2 else "evolve")
                        continue
                if error.code not in REJECTIONS:
                    raise
                kind = "attack" if isinstance(command, UseAttack) else "retreat"
                observed[f"rejected_{kind}_{error.code}"] += 1
                turn_tried.add(kind)
        problems = check_invariants(new)
        if problems:
            raise AssertionError(problems)
        observed["accepted"] += 1
        observe(state, new, observed)
        commands.append(command)
        state = new
    raise AssertionError("決まった手数で終わらなかった")


def observe(state, new, observed):
    """受け付けた操作のログを数え、受けたダメージ（retaliation の received_damage）を直前のダメージのログと比べる。"""
    events = [dict(e) for e in new.log[len(state.log):]]
    last_damage = {}  # 場のポケモンの番号（または card）→ 直前に受けたワザのダメージのログ
    shell_back = False  # 直前のイベントが「こうらがえし」（そのあとのダメージの要素はわるいカメールのワザ）
    shell_holder = None
    for e in events:
        kind = e["kind"]
        if kind == "evolve" and e["to_card_id"] == DARK_WARTORTLE:
            observed["evolve_dark_wartortle"] += 1
            observed[f"evolve_dark_wartortle_from_{e['from_card_id']}"] += 1
        if kind == "attack" and new.cards[e["pokemon"]].card_id == DARK_WARTORTLE:
            observed[f"attack_{e['attack']}"] += 1
        if kind == "damage" and not e.get("retaliation"):
            last_damage[e.get("pokemon_id", e["pokemon"])] = e
            last_damage[e["pokemon"]] = e
        if kind == "attack_evaded" and shell_back:
            observed["shell_evaded"] += 1
        if kind in ("damage", "attack_evaded", "damage_prevented"):
            if kind == "damage" and e.get("retaliation") and shell_back:
                observed["shell_damage_events"] += 1
                observed["shell_final_total"] += e["amount"]
                observed["shell_weakness"] += bool(e["weakness"])
                observed["shell_resistance"] += bool(e["resistance"])
                observed["shell_defender"] += bool(e.get("modifiers"))
                if e["total_damage"] >= new.card_def(e["pokemon"]).hp:
                    observed["shell_knock_out"] += 1
                if e["amount"] != observed_base[0]:
                    observed["shell_final_differs_from_base"] += 1
            shell_back = False
        if kind == "retaliation" and e.get("basis") == "received_damage":
            # 受けたダメージは、直前の効果を持つポケモンへのワザのダメージのログの最終ダメージ（エンジンの関数を使わない確認）
            trigger = last_damage.get(e["pokemon"])
            if trigger is None or trigger["amount"] != e["received_damage"] or e["amount"] != e["received_damage"]:
                raise AssertionError(f"受けたダメージが直前のダメージと違う: {e} {trigger}")
            observed["shell_triggered"] += 1
            observed["shell_received_total"] += e["received_damage"]
            observed["shell_base_total"] += e["amount"]
            observed_base[0] = e["amount"]
            shell_back, shell_holder = True, e["pokemon"]
        elif kind == "retaliation":
            observed["fire_wall_triggered"] += 1
            if e["amount"] != 10 or "basis" in e:
                raise AssertionError(f"ほのおのかべの量が 10 ではない: {e}")
        if kind == "retaliation_skipped":
            observed[f"retaliation_skipped_{'shell' if e['effect'] == SHELL else 'fire_wall'}"] += 1
        if kind == "knock_out" and shell_holder is not None and e["pokemon"] == shell_holder:
            observed["shell_holder_knocked_out"] += 1  # 返したわるいカメールが同じワザできぜつ（S36）
        if kind in ("turn_end", "knock_out") and shell_holder is not None and (kind == "turn_end" or e["pokemon"] == shell_holder):
            shell_holder = None  # 番の終わりのポケモンチェック（どく）のきぜつは数えない
        if kind == "counterattack" and e["effect"] == SHELL:
            observed["counterattack_after_shell"] += 1
        if kind == "persistent_effect_added":
            observed[f"effect_added_{e['persistent_effect']}"] += 1
        if kind == "persistent_effect_removed":
            observed[f"effect_removed_{e['persistent_effect']}_{e['reason']}"] += 1
        if kind == "persistent_effect_skipped":
            observed[f"effect_skipped_{e['persistent_effect']}"] += 1
    if new.decision is not None and new.decision.kind == POST_KNOCKOUT_POWER:
        observed["rebirth_offered"] += 1


observed_base = [None]  # 直前の「こうらがえし」の基本となるダメージ（observe の中だけで使う）


def count_events(state):
    """ログから数える。"""
    counted = Counter()
    for e in state.log:
        kind = e["kind"]
        if kind == "take_prize":
            counted["take_prize"] += 1
        elif kind == "knock_out" and e.get("simultaneous"):
            counted["knock_out_simultaneous"] += 1
    counted = Counter({k: v for k, v in counted.items() if v})
    counted[f"phase_{state.phase.value}"] += 1
    if state.phase is Phase.GAME_OVER:
        counted["decisive"] += 1
    if state.phase is Phase.HALTED:
        counted[f"halted_{state.halt.code}"] += 1
    return counted


# 自然な対戦（SEEDS の 100 局）で数えた回数（v0.13）。手順・デッキ・乱数の使い方が変わると変わる。99 局は勝敗が決まり、1 局（seed 27）は
# 対戦準備の既存の未解決の裁定（UNRESOLVED_MULLIGAN_COMPENSATION。v0.1 から。わるいカメールとは関係しない）で止まった。
# わるいカメールへの進化 202 回（第4弾のゼニガメから 140・第1弾のゼニガメから 62）。おうふくびんた 334 回・こうらがえし 409 回（効果を与えた 409 回）。
# 効果がはたらいた 151 回（返すダメージ 143 回・「とうめい」で受けなかった 8 回）。受けたダメージの合計 2480 = 返すダメージの基本となるダメージの
# 合計 2480、返したダメージ（最終ダメージ）の合計 2580（弱点 13 回・ディフェンダー 5 回で、基本となるダメージと違う 18 回。水の抵抗力を持つ
# ポケモンは対応カードにないので抵抗力 0 回）。返すダメージでワザを使ったポケモンが HP 以上 25 回、返したわるいカメールが同じワザできぜつ 40 回、
# 返すダメージで「はんげき」1 回、ワザを使ったポケモンが自分へのダメージですでに HP 以上で返さなかった 1 回（そのわるいカメールもきぜつ。
# 効果がきぜつで消えた 41 回 = 40 + 1）。効果が期限で消えた 358 回・ふきとばしで消えた 3 回。S37（W24 と同じコード）で止めたワザ 34 回
# （「ほのおのかべ」では 6 回）。「ほのおのかべ」は 28 回はたらき、どれも 10 を返した。
EXPECTED_COUNTS = {
    "accepted": 11281, "attack_おうふくびんた": 334, "attack_こうらがえし": 409, "counterattack_after_shell": 1, "decisive": 99,
    "effect_added_prevent_damage": 6, "effect_added_retaliation": 52, "effect_added_retaliation_received_damage": 409,
    "effect_removed_prevent_damage_expired": 6, "effect_removed_retaliation_expired": 36, "effect_removed_retaliation_knock_out": 7,
    "effect_removed_retaliation_received_damage_expired": 358, "effect_removed_retaliation_received_damage_forced_switch": 3,
    "effect_removed_retaliation_received_damage_knock_out": 41, "effect_skipped_retaliation": 1, "evolve_dark_wartortle": 202,
    "evolve_dark_wartortle_from_PMCG1-023": 62, "evolve_dark_wartortle_from_PMCG4-018": 140, "fire_wall_triggered": 28,
    "halted_UNRESOLVED_MULLIGAN_COMPENSATION": 1, "knock_out_simultaneous": 6, "phase_game_over": 99, "phase_halted": 1,
    "rebirth_offered": 37, "rejected": 838, "rejected_attack_POKEMON_ASLEEP": 30, "rejected_attack_POKEMON_PARALYZED": 60,
    "rejected_attack_UNRESOLVED_CONFUSION_DAMAGE_MODIFIERS": 1, "rejected_declare_PMCG1-057": 55, "rejected_declare_PMCG3-007": 44,
    "rejected_declare_PMCG3-030": 94, "rejected_declare_PMCG5-020": 98, "rejected_declare_PMCG6-061": 9,
    "rejected_evolve2_EVOLVED_THIS_TURN": 41, "rejected_evolve_FIRST_TURN_EVOLUTION": 62, "rejected_evolve_PLAYED_THIS_TURN": 159,
    "rejected_retreat_POKEMON_ASLEEP": 31, "rejected_retreat_POKEMON_PARALYZED": 65, "rejected_retreat_RETREAT_ALREADY_FAILED": 1,
    "retaliation_skipped_shell": 1, "shell_base_total": 2480, "shell_damage_events": 143, "shell_defender": 5, "shell_evaded": 8,
    "shell_final_differs_from_base": 18, "shell_final_total": 2580, "shell_holder_knocked_out": 40, "shell_knock_out": 25,
    "shell_received_total": 2480, "shell_resistance": 0, "shell_triggered": 151, "shell_weakness": 13,
    "stopped_attack_UNRESOLVED_COUNTERATTACK_DOUBLE_KNOCKOUT": 12, "stopped_attack_UNRESOLVED_RETALIATION_DOUBLE_KNOCKOUT": 40,
    "stopped_attack_UNRESOLVED_RETALIATION_DOUBLE_KNOCKOUT_fire_wall": 6,
    "stopped_attack_UNRESOLVED_RETALIATION_DOUBLE_KNOCKOUT_shell": 34, "suppressed_power": 36, "take_prize": 534,
}
HALTED_SEEDS = {27}

# わるいカメールの「こうらがえし」で返したダメージ（弱点・きぜつ・プラスパワーで受けたダメージが基本となるダメージと違う）がある対戦
GOLDEN_SEED = 24
GOLDEN_SHAPE = (46, 12, Phase.GAME_OVER)
GOLDEN_DIGEST = "6b3c2161038085fbdfc1f00f855931ed2deae4d7421cc23c33a6b8fc51759d30"
ORDER_SEED = 12  # 返したあとに、そのワザのコイン（ダメージ以外の効果）がある対戦
FIRE_SEED = 0  # 「ほのおのかべ」がはたらいた対戦


class FullGameWithDarkWartortleTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.games = {seed: play_game(seed, cure=seed % 3 != 0) for seed in SEEDS}

    def total(self):
        counted = Counter()
        for state, _, observed in self.games.values():
            counted.update(count_events(state))
            counted.update(observed)
        return counted

    def test_counts(self):
        """自然な対戦の中で、わるいカメールに進化し（両方のゼニガメから）、おうふくびんた・こうらがえしを使い、効果がはたらき（受けたダメージを返す・
        弱点・ディフェンダー・「とうめい」・「はんげき」・きぜつ・わるいカメールがきぜつしても返す）、期限・ふきとばし・きぜつで消え、S37 で止まる
        （1 回も起こらない試験を成功と数えない）。"""
        counted = self.total()
        for key in ("evolve_dark_wartortle_from_PMCG4-018", "evolve_dark_wartortle_from_PMCG1-023", "attack_おうふくびんた", "attack_こうらがえし",
                    "shell_triggered", "shell_damage_events", "shell_weakness", "shell_defender", "shell_evaded", "shell_knock_out",
                    "shell_holder_knocked_out", "counterattack_after_shell", "effect_removed_retaliation_received_damage_expired",
                    "effect_removed_retaliation_received_damage_forced_switch", "effect_removed_retaliation_received_damage_knock_out",
                    "stopped_attack_UNRESOLVED_RETALIATION_DOUBLE_KNOCKOUT_shell", "fire_wall_triggered", "phase_game_over"):
            self.assertGreater(counted[key], 0, (key, counted))
        self.assertEqual(counted["attack_こうらがえし"], counted["effect_added_retaliation_received_damage"])
        self.assertEqual(counted["shell_triggered"], counted["shell_damage_events"] + counted["shell_evaded"])
        self.assertEqual(counted["shell_received_total"], counted["shell_base_total"])
        self.assertEqual(counted["shell_final_differs_from_base"], counted["shell_weakness"] + counted["shell_defender"] + counted["shell_resistance"])
        self.assertEqual(counted["effect_removed_retaliation_received_damage_knock_out"],
                         counted["shell_holder_knocked_out"] + counted["retaliation_skipped_shell"])
        self.assertEqual(dict(counted), EXPECTED_COUNTS)
        halted = {seed for seed, (state, _, _) in self.games.items() if state.phase is Phase.HALTED}
        self.assertEqual(halted, HALTED_SEEDS)

    def test_states_logs_and_serialization(self):
        """どの対戦も、不変条件・ログの監査（「こうらがえし」の受けたダメージ・返すダメージ・期限を含む）・書き出しの監査（形式 1〜9）に通る。"""
        for seed, (state, _, _) in self.games.items():
            with self.subTest(seed=seed):
                self.assertIn(state.phase, TERMINAL)
                self.assertEqual(check_invariants(state), [])
                self.assertEqual(log_problems(state), [])
                self.assertEqual(serialization_problems(state), [])

    def test_randomness_is_only_coins(self):
        """対戦準備のあとの乱数はコインだけ（「こうらがえし」は乱数を使わない。おうふくびんたはコイン 2 枚。「とうめい」のコインは受けるときに 1 枚）。"""
        for seed, (state, _, _) in self.games.items():
            with self.subTest(seed=seed):
                expected = copy_rng(new_game(*decks(seed), seed).rng)
                for event in coin_events(state):
                    self.assertEqual(event["result"], "heads" if expected.getrandbits(1) else "tails")
                self.assertEqual(rng_fingerprint(state.rng), rng_fingerprint(expected))

    def test_replay_and_save_restore_while_the_effect_is_active(self):
        """同じ seed と同じ操作の列で同じ結果。「こうらがえし」の効果がはたらく番の状態で保存して（pickle）再開しても、結果は同じ（D5）。"""
        restored = Counter()
        for seed, (state, commands, _) in self.games.items():
            replayed = new_game(*decks(seed), seed)
            for command in commands:
                if any(e.kind == RECEIVED_KIND for p in replayed.players for pk in p.in_play() for e in pk.persistent_effects):
                    replayed = pickle.loads(pickle.dumps(replayed))
                    restored["shell_effect"] += 1
                replayed = apply_command(replayed, command)
            with self.subTest(seed=seed):
                self.assertEqual(full(replayed), full(state))
        self.assertGreater(restored["shell_effect"], EXPECTED_COUNTS["shell_triggered"])


class GoldenDarkWartortleGameTest(unittest.TestCase):
    """「こうらがえし」で返したダメージがある対戦（GOLDEN_SEED）の結果の固定値（Python 3.11・3.12・3.13 で同じ。v0.13）。"""

    def test_seed(self):
        state, commands, observed = play_game(GOLDEN_SEED, cure=GOLDEN_SEED % 3 != 0)
        self.assertEqual((len(commands), state.turn_number, state.phase), GOLDEN_SHAPE)
        self.assertGreater(observed["shell_triggered"], 0)
        data = full(state)
        # v0.69・v0.97: 写しの元を上げた（7d3f4ca・73a1690）。固定値は変えず、写しの元の 2 か所だけを確かめた移行でもどして比べる（tests/helpers.py）
        self.assertEqual(data["card_data"]["commit"], CARD_DATA_COMMIT)
        data = with_card_data_commit_before_v0_69(data)
        self.assertEqual(data.pop("effects"), "kyuura-engine-0.13")
        self.assertEqual(hashlib.sha256(json.dumps(data, sort_keys=True, ensure_ascii=False).encode()).hexdigest(), GOLDEN_DIGEST)


def replay_until(seed, stop):
    """``seed`` の対戦を、操作のあとの状態が ``stop(state)`` になるまで進めた状態（同じ手順・同じ操作の列）。"""
    _, commands, _ = play_game(seed, cure=seed % 3 != 0)
    state = new_game(*decks(seed), seed)
    for command in commands:
        state = apply_command(state, command)
        if stop(state):
            return state
    raise AssertionError("その状態にならなかった")


def first(log, test, start=0):
    return next(i for i in range(start, len(log)) if test(log[i]))


class LogAuditShellAttackTest(unittest.TestCase):
    """ログの監査（tests/log_audit.py）が、「こうらがえし」のログ・状態の食い違い（D6 の 16 種類）を見つけること（監査が何でも通すのではない
    ことの確認）。GOLDEN_SEED の対戦（プラスパワーで受けたダメージが基本となるダメージと違う・弱点・返すダメージできぜつ）、ORDER_SEED の
    対戦（返したあとにワザのコイン）、FIRE_SEED の対戦（「ほのおのかべ」）のログ・途中の状態を書きかえて、それぞれの種類の誤りを報告することを
    確かめる。"""

    @classmethod
    def setUpClass(cls):
        cls.state = play_game(GOLDEN_SEED, cure=GOLDEN_SEED % 3 != 0)[0]
        log = cls.state.log
        is_shell = lambda e: e["kind"] == "retaliation" and e.get("basis") == "received_damage"  # noqa: E731
        # 受けたダメージ（プラスパワー 2 枚で 30 → 50）が元のワザの基本となるダメージと違う「こうらがえし」
        cls.boosted = first(log, lambda e: is_shell(e) and e["received_damage"] != _trigger(log, log.index(e))["steps"][0][1])
        cls.trigger = max(i for i in range(cls.boosted) if log[i]["kind"] == "damage")
        cls.back = cls.boosted + 1
        # 弱点で 2 倍にした返すダメージ・返すダメージできぜつ
        cls.weak = first(log, lambda e: e["kind"] == "damage" and e.get("retaliation") and e["weakness"])
        cls.ko_back = first(log, lambda e: e["kind"] == "damage" and e.get("retaliation")
                            and e["total_damage"] >= cls.state.card_def(e["pokemon"]).hp)
        cls.ko = first(log, lambda e: e["kind"] == "knock_out", cls.ko_back)
        cls.prize = first(log, lambda e: e["kind"] == "take_prize", cls.ko)
        holder = log[cls.boosted]["pokemon_id"]
        created = log[cls.boosted]["turn"] - 1
        cls.added = first(log, lambda e: e["kind"] == "persistent_effect_added" and (e["pokemon_id"], e["turn"]) == (holder, created))
        cls.expired = first(log, lambda e: e["kind"] == "persistent_effect_removed" and e["reason"] == "expired"
                            and e["persistent_effect"] == RECEIVED_KIND)
        cls.order = play_game(ORDER_SEED, cure=ORDER_SEED % 3 != 0)[0]
        cls.order_shell = first(cls.order.log, is_shell)
        cls.fire = play_game(FIRE_SEED, cure=FIRE_SEED % 3 != 0)[0]
        cls.fire_wall = first(cls.fire.log, lambda e: e["kind"] == "retaliation" and e["effect"] == FIRE_WALL)

    def broken(self, change_log, state=None):
        state = (state or self.state).clone()
        log = [dict(e) for e in state.log]
        change_log(log)
        state.log = tuple(log)
        return self.audit(state)

    @staticmethod
    def audit(state):
        try:
            return log_problems(state)
        except (KeyError, ValueError, StopIteration, AttributeError, IndexError, TypeError) as error:
            return [f"組み立て直せない（{type(error).__name__}）"]

    def assert_reported(self, problems, text):
        self.assertTrue(any(text in p for p in problems), problems)

    def test_original_passes(self):
        for state in (self.state, self.order, self.fire):
            self.assertEqual(log_problems(state), [])
        log = self.state.log
        self.assertEqual(log[self.boosted]["received_damage"], log[self.trigger]["amount"])
        self.assertNotEqual(log[self.trigger]["steps"][0][1], log[self.trigger]["amount"])
        self.assertEqual(log[self.back]["kind"], "damage")

    def test_1_missing_return(self):
        """はたらいた「こうらがえし」が欠ける（retaliation とその返すダメージのログがない）。"""
        def drop(log):
            del log[self.boosted:self.back + 1]

        self.assert_reported(self.broken(drop), "はたらいた「ほのおのかべ」・「こうらがえし」")

    def test_2_returned_twice(self):
        """「こうらがえし」が 2 回ある。"""
        def twice(log):
            log[self.back + 1:self.back + 1] = [dict(log[self.boosted]), dict(log[self.back])]

        self.assert_reported(self.broken(twice), "が 2 回")

    def test_3_wrong_received_damage(self):
        """受けたダメージ（received_damage）が、きっかけのダメージのログの最終ダメージと違う。"""
        def wrong(log):
            log[self.boosted] = {**log[self.boosted], "received_damage": log[self.boosted]["received_damage"] + 10}

        self.assert_reported(self.broken(wrong), "受けたダメージ")

    def test_4_attack_base_damage_used(self):
        """元のワザの基本となるダメージ（30）を、受けたダメージ（50）の代わりに使った（「こうらがえし」の反撃を元のワザの基本ダメージにしない）。"""
        def base(log):
            attack_base = log[self.trigger]["steps"][0][1]
            log[self.boosted] = {**log[self.boosted], "received_damage": attack_base, "amount": attack_base}

        self.assert_reported(self.broken(base), "受けたダメージ")

    def test_5_weakness_forgotten(self):
        """返すダメージで、ワザを使ったポケモンの弱点を計算していない。"""
        def forget(log):
            event = log[self.weak]
            base = event["steps"][0][1]
            log[self.weak] = {**event, "weakness": False, "amount": base, "steps": event["steps"][:1],
                              "total_damage": event["total_damage"] - event["amount"] + base}

        self.assert_reported(self.broken(forget), "弱点 False")

    def test_6_resistance_wrong(self):
        """返すダメージの抵抗力の印が、ワザを使ったポケモンの抵抗力とわるいカメールのタイプに合わない（水の抵抗力を持つ対応カードはないので、
        抵抗力を計算しなかった誤りは、この照らし合わせで見つける）。"""
        def resist(log):
            log[self.back] = {**log[self.back], "resistance": True}

        self.assert_reported(self.broken(resist), "抵抗力 True")

    def test_7_wrong_target(self):
        """返すダメージを受けたのが、ダメージを与えた相手の対戦ポケモンではない（効果を持つわるいカメール自身）。"""
        def target(log):
            log[self.back] = {**log[self.back], "pokemon_id": log[self.boosted]["pokemon_id"]}

        self.assert_reported(self.broken(target), "ダメージを与えた相手の対戦ポケモン")

    def test_8_effect_survives_its_turn(self):
        """効果が期限（はたらく番の終わり）のあとも残る。"""
        def keep(log):
            del log[self.expired]

        self.assert_reported(self.broken(keep), "が残っている")

    def test_9_effect_removed_too_early(self):
        """効果が早すぎる時点（与えた番）で期限で消える。"""
        def early(log):
            added = first(log, lambda e: e["kind"] == "persistent_effect_added" and e["pokemon_id"] == log[self.expired]["pokemon_id"]
                          and e["turn"] == log[self.expired]["created_turn"])
            removed = log.pop(self.expired)
            log.insert(added + 1, {**removed, "turn": log[added]["turn"]})

        self.assert_reported(self.broken(early), "期限で消えた（早すぎる")

    def test_10_returned_after_zero_damage(self):
        """きっかけのダメージが 0（ダメージを受けなかった）なのに返した。"""
        def zero(log):
            event = log[self.trigger]
            log[self.trigger] = {**event, "amount": 0, "total_damage": event["total_damage"] - event["amount"]}

        self.assert_reported(self.broken(zero), "はたらく理由")

    def test_11_knock_out_by_the_return_missed(self):
        """返すダメージで HP 以上になったポケモンのきぜつの処理（knock_out）がない。"""
        def miss(log):
            del log[self.ko]

        self.assertNotEqual(self.broken(miss), [])

    def test_12_wrong_prize(self):
        """返すダメージによるきぜつのサイドを、きぜつしたポケモンの持ち主が取った（p.323）。"""
        def prize(log):
            log[self.prize] = {**log[self.prize], "player": 1 - log[self.prize]["player"]}

        self.assertNotEqual(self.broken(prize), [])

    def test_13_returned_after_the_attack_effect(self):
        """返すダメージが、そのワザのダメージ以外の効果（コイン）より後にある（p.89。S34）。"""
        def late(log):
            coin = first(log, lambda e: e["kind"] == "coin_flip" and e["source"] == "attack", self.order_shell)
            moved = log[self.order_shell:self.order_shell + 2]
            del log[self.order_shell:self.order_shell + 2]
            coin -= 2
            log[coin + 1:coin + 1] = moved

        self.assert_reported(self.broken(late, self.order), "より先に coin_flip がある")

    def test_14_fire_wall_amount_changed(self):
        """「ほのおのかべ」の量（固定の 10）が変わる・受けたダメージの形になる（v0.12 の固定の量を壊さない）。"""
        def twenty(log):
            log[self.fire_wall] = {**log[self.fire_wall], "amount": 20}

        def received(log):
            log[self.fire_wall] = {**log[self.fire_wall], "basis": "received_damage", "received_damage": 10}

        self.assert_reported(self.broken(twenty, self.fire), "の登録と違う")
        self.assert_reported(self.broken(received, self.fire), "の登録と違う")

    def test_15_save_restore_changes_the_effect(self):
        """保存・復元（pickle）で効果は変わらない。変わった状態（受けたダメージの量の効果が固定の 10 になった）は監査と不変条件が見つける。"""
        import dataclasses
        alive = replay_until(GOLDEN_SEED, lambda s: any(retaliation_on(s, pk) for p in s.players for pk in p.in_play()))
        restored = pickle.loads(pickle.dumps(alive))
        self.assertEqual(full(restored), full(alive))
        self.assertEqual(log_problems(restored), [])
        for p in restored.players:
            for pk in p.in_play():
                pk.persistent_effects = tuple(dataclasses.replace(e, basis="fixed", amount=10) for e in pk.persistent_effects)
        self.assert_reported(self.audit(restored), "ログで与えた retaliation_received_damage と違う")
        self.assertNotEqual(check_invariants(restored), [])

    def test_16_chained_return(self):
        """返すダメージで、ワザを使ったポケモン側の効果が返した（連鎖。番の進み方から起こらない）。"""
        def chain(log):
            event = log[self.boosted]
            back = log[self.back]
            log[self.back + 1:self.back + 1] = [
                {**event, "player": event["attacker"], "pokemon": event["attacker_pokemon"], "pokemon_id": event["attacker_pokemon_id"],
                 "attacker": event["player"], "attacker_pokemon": event["pokemon"], "attacker_pokemon_id": event["pokemon_id"]},
                {**back, "player": event["player"], "pokemon": event["pokemon"], "pokemon_id": event["pokemon_id"]},
            ]

        self.assertNotEqual(self.broken(chain), [])
        self.assert_reported(self.broken(chain), "ダメージを与えたワザの処理の中にない")


def _trigger(log, index):
    """``index`` の retaliation のきっかけのダメージのログ。"""
    return log[max(i for i in range(index) if log[i]["kind"] == "damage")]


if __name__ == "__main__":
    unittest.main()

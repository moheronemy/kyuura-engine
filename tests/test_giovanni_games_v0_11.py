"""サカキのワンリキー → サカキのゴーリキー → サカキのカイリキー（v0.11）を含む 60 枚のデッキで、正式な対戦開始（new_game）から勝敗まで。

サカキのカイリキーのポケモンパワー「こんじょう」（相手のワザによるダメージで「きぜつ」するとき、使える。コインを投げて「おもて」なら
「きぜつ」せず、残り HP が 10。ダメージを受けるとき、すでにねむり・マヒ・こんらんなら使えない。p.193）が、自然な対戦の中で、使うかを
持ち主が決め（使う・使わない）、「おもて」で残り HP 10 になって場に残り（サイドを取られない）、「うら」・使わないときにきぜつすること、
かがくへんかガス（v0.8）・特殊状態で使えないこと、原典で決められない場合（G37）で止まることを確かめる（docs/v0.11-verification.md 2.2）。

- 一方のデッキは、サカキのワンリキー・ゴーリキー・カイリキーとエビワラー。
- もう一方のデッキは、サカキのカイリキーに使うワザの種類を多くした（ワンリキー・ゴーリキー・カイリキー（はんげき・ちきゅうなげ 60）、
  ケーシィ・ユンゲラー（ちょうねんりき 50 × 弱点 2）、ピカチュウ（でんげき）、キャタピー（いとをはく。G37 で止まる）、ロケット団の
  ベトベター・ベトベトン（かがくへんかガス）、ロコン（こんらん）、サカキのワンリキー・ゴーリキー・カイリキー（ミラー））。

盤面を直接作ったテスト（tests/test_guts_v0_11.py）とは別に数える。根拠のページは tests/test_guts_v0_11.py（p.100・p.193・p.309・p.311・
p.319〜p.324）・tests/test_giovanni_machamp_line_v0_11.py（p.189・p.191・p.193・p.310）。手順は tests/test_machamp_games_v0_10.py の
``policy_command`` に、次を加えたもの（対戦相手の AI ではない）:

- 「こんじょう」を使うかの決定には、番の番号が ``DECLINE_EVERY`` の倍数なら使わない、それ以外は使うと答える（手順の決まりごと。ルール
  ではない。どちらの答えも受け付けることを確かめるため）。
- 番の番号を 7 で割った余りが 3 の番は、自分の場にサカキのカイリキーがいれば一度だけ、UsePokemonPower で「こんじょう」を試す（決められた
  とき以外なので POWER_NOT_USABLE_NOW。かがくへんかガスがはたらいていれば POWER_SUPPRESSED）。
- ワザが ``UNRESOLVED_KO_PREVENTION_ATTACK_EFFECT``（G37）で止まったら、その番はほかの使えるワザ（試していないもの）を 1 度だけ試し、
  なければ番を終える。

「こんじょう」を使えるかは、エンジンの関数を使わずに場から求める（``guts_available``。サカキのカイリキー（いちばん上のカード）が、ねむり・
マヒ・こんらんでなく、はたらいているベトベトンがいない）。ワザ・決定の答えを受け付けるたびに、受け付ける前の場と比べて、決定が出るのは
使えるサカキのカイリキーが相手のワザで HP 以上になったときだけで、使えるのに決定がないままきぜつしていないことを確かめる。
"""

import hashlib
import json
import unittest
from collections import Counter

from kyuura_engine import (
    AttachEnergy, EndTurn, EvolvePokemon, IllegalActionError, Phase, ResolveDecision, UnsupportedError, UseAttack, UsePokemonPower,
    apply_command, check_invariants, new_game, state_to_dict,
)
from kyuura_engine.decisions import KO_PREVENTION
from kyuura_engine.rng import copy_rng, rng_fingerprint
from tests.helpers import (
    CARD_DATA_COMMIT,
    with_card_data_commit_before_v0_69,
    ABRA, BILL, CATERPIE, DEFENDER, FIGHTING, FIRE, GIOVANNIS_MACHAMP, GIOVANNIS_MACHOKE, GIOVANNIS_MACHOP, GRASS, GRIMER, HITMONCHAN,
    KADABRA, MACHAMP, MUK, PLUSPOWER, POTION, PSYCHIC, SWITCH, VULPIX, coin_events, expand_decklist,
)
from tests.log_audit import log_problems, serialization_problems
from tests.test_alakazam_games_v0_7 import POWER_REJECTIONS
from tests.test_blastoise_games_v0_6 import R13
from tests.test_confusion_games import TERMINAL
from tests.test_evolution_games_v0_4a import EVOLUTION_REJECTIONS
from tests.test_harden_games_v0_4b import REJECTIONS
from tests.test_haunter_games_v0_9 import EVADED_COIN, blocked, card_id, gas_on
from tests.test_haunter_games_v0_9 import working as evasion_working
from tests.test_machamp_games_v0_10 import DOUBLE_KO, alternative_attack
from tests.test_machamp_games_v0_10 import policy_command as machamp_policy_command
from tests.test_machamp_games_v0_10 import working as counter_working
from tests.test_stage2_games_v0_4c import STAGE2_REJECTIONS

# サカキのワンリキー・ゴーリキー・カイリキーとエビワラー
GIOVANNI_DECK_A = expand_decklist({
    GIOVANNIS_MACHOP: 4, GIOVANNIS_MACHOKE: 4, GIOVANNIS_MACHAMP: 4, HITMONCHAN: 2, SWITCH: 2, POTION: 2, BILL: 4, DEFENDER: 2, PLUSPOWER: 2,
    FIGHTING: 34,
})
# サカキのカイリキーのミラーに、サカキのカイリキーに使うワザの種類を加えたデッキ（ケーシィ・ユンゲラー（ちょうねんりき 50 × 弱点 2）、
# ロケット団のベトベター・ベトベトン（かがくへんかガス）、ロコン（あやしいひかり。こんらん）、キャタピー（いとをはく。G37 で止まる））
GIOVANNI_DECK_B = expand_decklist({
    GIOVANNIS_MACHOP: 4, GIOVANNIS_MACHOKE: 4, GIOVANNIS_MACHAMP: 3, ABRA: 3, KADABRA: 3, GRIMER: 2, MUK: 1, VULPIX: 2, CATERPIE: 2,
    PLUSPOWER: 2, BILL: 4, FIGHTING: 18, PSYCHIC: 8, GRASS: 3, FIRE: 1,
})
SEEDS = tuple(range(100))
DECLINE_EVERY = 3  # 手順の決まりごと（ルールの制限ではない）
EFFECT_STOP = "UNRESOLVED_KO_PREVENTION_ATTACK_EFFECT"
GUTS_EVENTS = ("ko_prevention_declined", "ko_prevention_declared", "ko_prevented", "ko_prevention_failed")


def full(state):
    return state_to_dict(state, format_version=9)


def decks(seed):
    return (GIOVANNI_DECK_A, GIOVANNI_DECK_B) if seed % 2 == 0 else (GIOVANNI_DECK_B, GIOVANNI_DECK_A)


def guts_available(state, pokemon):
    """「こんじょう」を使えるか（エンジンの関数を使わない。p.193・p.48）。"""
    return pokemon is not None and card_id(state, pokemon) == GIOVANNIS_MACHAMP and not blocked(pokemon) and not gas_on(state)


def policy_command(state, *, janken_winner, cure, tried):
    if state.phase is Phase.DECISION and state.decision.kind == KO_PREVENTION:
        d = state.decision
        use = state.turn_number % DECLINE_EVERY != 0
        return ResolveDecision(d.player, d.id, d.options[:1] if use else ())
    command = machamp_policy_command(state, janken_winner=janken_winner, cure=cure, tried=tried)
    if state.phase is not Phase.MAIN:
        return command
    player = state.current_player
    if isinstance(command, (UseAttack, EndTurn)) and state.turn_number % 7 == 3 and "declare_guts" not in tried:
        machamp = next((pk for pk in state.players[player].in_play() if card_id(state, pk) == GIOVANNIS_MACHAMP), None)
        if machamp is not None:
            tried.add("declare_guts")
            return UsePokemonPower(player, machamp.pokemon_id, 0)
    if isinstance(command, UseAttack) and ("guts_effect" in tried or ("attack_index", command.attack_index) in tried):
        return alternative_attack(state, player, tried) or EndTurn(player)
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
                    if error.code == "POWER_NOT_USABLE_NOW" and kind == GIOVANNIS_MACHAMP and not gas_on(state):
                        observed["rejected_declare_guts"] += 1
                        continue
                    if error.code == "POWER_NOT_DECLARABLE" and kind in (MUK, MACHAMP):
                        observed[f"rejected_declare_{kind}"] += 1
                        continue
                    if error.code == "POWER_SUPPRESSED" and gas_on(state):
                        observed["suppressed_power"] += 1
                        continue
                    if error.code not in POWER_REJECTIONS:
                        raise
                    observed[f"rejected_power_{error.code}"] += 1
                    continue
                if isinstance(command, UseAttack) and error.code == EFFECT_STOP:
                    # G37: 相手の対戦ポケモンのサカキのカイリキーの「こんじょう」を使えるとき（エンジンとは別に場から確かめる）
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
        observe_guts(state, new, command, observed)
        commands.append(command)
        state = new
    raise AssertionError("決まった手数で終わらなかった")


def observe_guts(state, new, command, observed):
    """受け付けた操作のログ・決定を、操作の前の場から求めた「こんじょう」と比べて数える。"""
    events = [dict(e) for e in new.log[len(state.log):]]
    owners = {pk.pokemon_id: player for player, p in enumerate(state.players) for pk in p.in_play()}
    by_card = {pk.card: pk for p in state.players for pk in p.in_play()}
    attacker_player = state.current_player
    if new.decision is not None and new.decision.kind == KO_PREVENTION:
        if state.decision is not None and state.decision.kind == KO_PREVENTION:
            raise AssertionError("「こんじょう」の決定が続けて出た")
        pid = new.decision.options[0]
        before = next(pk for p in state.players for pk in p.in_play() if pk.pokemon_id == pid)
        after = new.find_pokemon(pid)[1]
        if not (isinstance(command, (UseAttack, ResolveDecision)) and owners[pid] != attacker_player and guts_available(state, before)
                and after.damage >= state.card_def(after.card).hp):
            raise AssertionError(f"「こんじょう」を使えないはずの決定: {command} {new.decision}")
        observed["guts_offered"] += 1
        if state.players[owners[pid]].active is not before:
            observed["guts_offered_on_bench"] += 1
    for e in events:
        kind = e["kind"]
        if kind in GUTS_EVENTS:
            observed[kind] += 1
        if kind == "ko_prevented":
            pokemon = new.find_pokemon(e["pokemon_id"])
            if pokemon is None or pokemon[1].damage != new.card_def(pokemon[1].card).hp - 10:
                raise AssertionError(f"「おもて」のあとに残り HP 10 で場にいない: {e}")
        if kind == "knock_out":
            pokemon = by_card.get(e["pokemon"])
            if pokemon is None or card_id(state, pokemon) != GIOVANNIS_MACHAMP:
                continue
            observed["knock_out_giovannis_machamp"] += 1
            guts_seen = [g for g in events if g["kind"] in ("ko_prevention_declined", "ko_prevention_failed")
                         and g["pokemon_id"] == pokemon.pokemon_id]
            if guts_seen:
                continue
            if e.get("timing") == "pokemon_check":
                observed["guts_not_applicable_poison"] += 1
            elif owners[pokemon.pokemon_id] == attacker_player:
                observed["guts_not_applicable_own_turn"] += 1  # 自分のワザ・こんらん・「はんげき」（相手のワザのダメージではない）
            elif blocked(pokemon):
                observed["guts_blocked_by_condition"] += 1
            elif gas_on(state):
                observed["guts_suppressed_by_gas"] += 1
            else:
                raise AssertionError(f"「こんじょう」を使えるのに決定がないまま、きぜつした: {command} {e}")


def count_events(state):
    """ログから数える。"""
    counted = Counter()
    for e in state.log:
        kind = e["kind"]
        if kind == "evolve":
            counted[f"evolve_to_{e['to_card_id']}"] += 1
        elif kind == "attack":
            if state.cards[e["pokemon"]].card_id in (GIOVANNIS_MACHOP, GIOVANNIS_MACHOKE, GIOVANNIS_MACHAMP):
                counted[f"attack_{e['attack']}"] += 1
        elif kind == "coin_flip" and e["effect"] == f"{GIOVANNIS_MACHAMP}#0":
            counted[f"hurricane_punch_{e['result']}"] += 1
        elif kind == "take_prize":
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


# 自然な対戦（SEEDS の 100 局）で数えた回数（v0.11）。手順・デッキ・乱数の使い方が変わると変わる。止まった 3 局は対戦準備の切り直しの
# 補償（v0.1 からの未解決）。サカキのカイリキーへの進化 79 回。「こんじょう」を使うかの決定 36 回（使う 20 回: 「おもて」12 回で残り HP 10・
# 「うら」8 回できぜつ、使わない 16 回できぜつ）。かがくへんかガスで使えずにきぜつ 3 回。ベンチのサカキのカイリキーへの決定 0 回（ベンチに
# ダメージを与えるワザが対応カードにない）。特殊状態で使えずにきぜつ・どくのきぜつ・G37 で止めたワザは、この 100 局では 0 回（単体テストで
# 確かめる）。ハリケーンパンチ 105 回（コイン 420 枚: 「おもて」195・「うら」225）。UsePokemonPower での「こんじょう」の試みの拒否 54 回。
EXPECTED_COUNTS = {
    "accepted": 5780, "attack_いかりのスーパーパンチ": 285, "attack_いちかばちか": 137, "attack_チョップ": 156, "attack_ハリケーンパンチ": 105,
    "decisive": 97, "evolve_to_PMCG1-046": 47, "evolve_to_PMCG3-007": 16, "evolve_to_PMCG6-059": 189, "evolve_to_PMCG6-061": 79,
    "guts_offered": 36, "guts_suppressed_by_gas": 3, "halted_UNRESOLVED_MULLIGAN_COMPENSATION": 3, "hurricane_punch_heads": 195,
    "hurricane_punch_tails": 225, "knock_out_giovannis_machamp": 27, "ko_prevented": 12, "ko_prevention_declared": 20,
    "ko_prevention_declined": 16, "ko_prevention_failed": 8, "phase_game_over": 97, "phase_halted": 3, "rejected": 354,
    "rejected_attack_POKEMON_PARALYZED": 12, "rejected_declare_PMCG3-007": 24, "rejected_declare_guts": 54,
    "rejected_evolve2_EVOLVED_THIS_TURN": 87, "rejected_evolve_FIRST_TURN_EVOLUTION": 92, "rejected_evolve_PLAYED_THIS_TURN": 66,
    "rejected_retreat_POKEMON_PARALYZED": 7, "suppressed_power": 12, "take_prize": 372,
}

# 「こんじょう」を使わない 2 回（同じサカキのカイリキーが「おもて」で残り HP 10 になったあとの 2 回目を含む）・「うら」1 回・「おもて」1 回の対戦
GOLDEN_SEED = 58
GOLDEN_SHAPE = (124, 36, Phase.GAME_OVER)
GOLDEN_DIGEST = "dbcc48c1b3790bcdf4c831f225f25ec08ec4e82785b35a0f19b7c2cdee157e7e"


class FullGameWithGiovannisMachampTest(unittest.TestCase):
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
        """自然な対戦の中で、サカキのカイリキーに進化し、「こんじょう」を使うか決め（使う・使わない）、「おもて」で残り HP 10、「うら」・使わない
        ときにきぜつし、かがくへんかガスで使えず、ハリケーンパンチを使う（1 回も起こらない試験を成功と数えない）。"""
        counted = self.total()
        for key in ("evolve_to_PMCG6-061", "guts_offered", "ko_prevention_declared", "ko_prevention_declined", "ko_prevented",
                    "ko_prevention_failed", "guts_suppressed_by_gas", "rejected_declare_guts", "attack_ハリケーンパンチ",
                    "attack_いかりのスーパーパンチ", "attack_いちかばちか", "attack_チョップ", "phase_game_over"):
            self.assertGreater(counted[key], 0, (key, counted))
        self.assertEqual(counted["ko_prevention_declared"], counted["ko_prevented"] + counted["ko_prevention_failed"])
        self.assertEqual(counted["guts_offered"], counted["ko_prevention_declared"] + counted["ko_prevention_declined"])
        self.assertEqual(counted["hurricane_punch_heads"] + counted["hurricane_punch_tails"], 4 * counted["attack_ハリケーンパンチ"])
        self.assertEqual(counted["guts_offered_on_bench"], 0)
        self.assertEqual(dict(counted), EXPECTED_COUNTS)

    def test_states_logs_and_serialization(self):
        """どの対戦も、不変条件・ログの監査（「こんじょう」の決定・コイン・残り HP・きぜつ・サイドの対応を含む）・書き出しの監査（形式 1〜9）に通る。"""
        for seed, (state, _, _) in self.games.items():
            with self.subTest(seed=seed):
                self.assertIn(state.phase, TERMINAL)
                self.assertEqual(check_invariants(state), [])
                self.assertEqual(log_problems(state), [])
                self.assertEqual(serialization_problems(state), [])

    def test_randomness_is_only_coins(self):
        """対戦準備のあとの乱数はコインだけ（「こんじょう」は使うときに 1 枚、使わないときは投げない）。"""
        for seed, (state, _, _) in self.games.items():
            with self.subTest(seed=seed):
                expected = copy_rng(new_game(*decks(seed), seed).rng)
                for event in coin_events(state):
                    self.assertEqual(event["result"], "heads" if expected.getrandbits(1) else "tails")
                self.assertEqual(rng_fingerprint(state.rng), rng_fingerprint(expected))
                kinds = [e["kind"] for e in state.log]
                power_coins = [e for e in coin_events(state) if e["source"] == "power"]
                self.assertEqual(len(power_coins), kinds.count("ko_prevention_declared"))

    def test_replay_and_save_restore_at_the_decision(self):
        """同じ seed と同じ操作の列で同じ結果。「こんじょう」を使うかの決定を待つ状態で保存して（pickle）再開しても、結果は同じ。"""
        import pickle
        restored = 0
        for seed, (state, commands, _) in self.games.items():
            if not any(e["kind"] in GUTS_EVENTS for e in state.log) and seed > 2:
                continue
            replayed = new_game(*decks(seed), seed)
            for command in commands:
                if replayed.decision is not None and replayed.decision.kind == KO_PREVENTION:
                    replayed = pickle.loads(pickle.dumps(replayed))
                    restored += 1
                replayed = apply_command(replayed, command)
            with self.subTest(seed=seed):
                self.assertEqual(full(replayed), full(state))
        self.assertEqual(restored, EXPECTED_COUNTS["guts_offered"])


class GoldenGiovanniGameTest(unittest.TestCase):
    """「こんじょう」を使わない・「うら」・「おもて」がある対戦（GOLDEN_SEED）の結果の固定値（Python 3.11・3.12・3.13 で同じ。v0.11）。"""

    def test_seed(self):
        state, commands, observed = play_game(GOLDEN_SEED, cure=GOLDEN_SEED % 3 != 0)
        self.assertEqual((len(commands), state.turn_number, state.phase), GOLDEN_SHAPE)
        kinds = Counter(e["kind"] for e in state.log)
        self.assertEqual((kinds["ko_prevention_declined"], kinds["ko_prevented"], kinds["ko_prevention_failed"]), (2, 1, 1))
        data = full(state)
        # v0.69・v0.97: 写しの元を上げた（7d3f4ca・73a1690）。固定値は変えず、写しの元の 2 か所だけを確かめた移行でもどして比べる（tests/helpers.py）
        self.assertEqual(data["card_data"]["commit"], CARD_DATA_COMMIT)
        data = with_card_data_commit_before_v0_69(data)
        self.assertEqual(data.pop("effects"), "kyuura-engine-0.13")  # v0.12・v0.13 で登録表の id だけ変わった（結果は同じ）
        self.assertEqual(hashlib.sha256(json.dumps(data, sort_keys=True, ensure_ascii=False).encode()).hexdigest(), GOLDEN_DIGEST)


class LogAuditGutsTest(unittest.TestCase):
    """ログの監査（tests/log_audit.py）が、「こんじょう」のログの食い違い（D7 の 14 種類）を見つけること（監査が何でも通すのではないことの
    確認）。GOLDEN_SEED の対戦のログ（使わない → きぜつ、使う → 「うら」→ きぜつ、使う → 「おもて」→ 残り HP 10、同じポケモンで使わない →
    きぜつ）を書きかえて、それぞれの種類の誤りを報告することを確かめる。"""

    @classmethod
    def setUpClass(cls):
        cls.state = play_game(GOLDEN_SEED, cure=GOLDEN_SEED % 3 != 0)[0]
        log = cls.state.log
        index = {kind: [i for i, e in enumerate(log) if e["kind"] == kind] for kind in GUTS_EVENTS}
        cls.declined = index["ko_prevention_declined"][0]
        cls.failed = index["ko_prevention_failed"][0]
        cls.tails_declared = cls.failed - 2
        cls.prevented = index["ko_prevented"][0]
        cls.heads_declared = cls.prevented - 2

    def broken(self, change_log):
        state = self.state.clone()
        log = [dict(e) for e in state.log]
        change_log(log)
        state.log = tuple(log)
        try:
            return log_problems(state)
        except (KeyError, ValueError, StopIteration, AttributeError, IndexError, TypeError) as error:
            return [f"組み立て直せない（{type(error).__name__}）"]

    def assert_reported(self, change_log, text):
        problems = self.broken(change_log)
        self.assertTrue(any(text in p for p in problems), problems)

    def test_original_passes(self):
        self.assertEqual(log_problems(self.state), [])
        log = self.state.log
        self.assertEqual([log[i]["kind"] for i in range(self.heads_declared, self.prevented + 1)],
                         ["ko_prevention_declared", "coin_flip", "ko_prevented"])
        self.assertEqual(log[self.failed + 1]["kind"], "knock_out")

    def test_1_missing_use_record(self):
        """こんじょうの使用記録（使うかの決定）がないまま、使えるサカキのカイリキーがきぜつした。"""
        def drop(log):
            del log[self.declined]

        self.assert_reported(drop, "使うかの決定（ko_prevention_declined・ko_prevention_declared）がないまま、きぜつした")

    def test_2_wrong_coin_result(self):
        def flip(log):
            log[self.prevented - 1] = {**log[self.prevented - 1], "result": "tails"}

        self.assert_reported(flip, "同じ結果のコインがない・結果が合わない")

    def test_3_knocked_out_after_heads(self):
        """「うら」の結果を「おもて」に書きかえると、そのあとのきぜつが「おもて」なのにきぜつになる。"""
        def heads(log):
            failed = log[self.failed]
            log[self.failed - 1] = {**log[self.failed - 1], "result": "heads"}
            log[self.failed] = {**failed, "kind": "ko_prevented", "result": "heads", "damage_before": failed["total_damage"], "total_damage": 90,
                                "remaining_hp": 10}

        self.assert_reported(heads, "「おもて」のポケモン")

    def test_4_survived_after_tails(self):
        def tails(log):
            prevented = log[self.prevented]
            log[self.prevented - 1] = {**log[self.prevented - 1], "result": "tails"}
            log[self.prevented] = {k: v for k, v in {**prevented, "kind": "ko_prevention_failed", "result": "tails",
                                                     "total_damage": prevented["damage_before"]}.items() if k not in ("damage_before", "remaining_hp")}

        self.assert_reported(tails, "「うら」のポケモン")

    def test_5_remaining_hp_is_not_10(self):
        def hp20(log):
            log[self.prevented] = {**log[self.prevented], "total_damage": log[self.prevented]["total_damage"] - 10}

        self.assert_reported(hp20, "残り HP 10")

    def test_6_used_while_unable(self):
        """ダメージを受ける前に、サカキのカイリキーをねむりにしたログを書き足すと、使えないのに使ったことになる（G25）。"""
        def asleep(log):
            target = log[self.heads_declared]
            damage = max(i for i in range(self.heads_declared) if log[i]["kind"] == "damage" and log[i].get("player") == target["player"])
            log.insert(damage, {"kind": "special_condition", "turn": target["turn"], "player": target["player"], "pokemon": target["pokemon"],
                                "pokemon_id": target["pokemon_id"], "condition": "sleep", "effect": "test"})

        self.assert_reported(asleep, "状態だった（使えない")

    def test_7_used_under_gas(self):
        """ワザの前にベトベトンを場に出したログを書き足すと、かがくへんかガスで消えている「こんじょう」を使ったことになる（G31）。"""
        def gas(log):
            muk = next(uid for uid, card in self.state.cards.items() if card.card_id == MUK)
            attack = max(i for i in range(self.heads_declared) if log[i]["kind"] == "attack")
            log.insert(attack, {"kind": "play_to_bench", "turn": log[attack]["turn"], "player": self.state.cards[muk].owner, "card": muk})

        self.assert_reported(gas, "かがくへんかガス")

    def test_8_wrong_cause(self):
        """使うかの決定を、ワザのあとではなく、ポケモンチェック（どく）のあとに移すと、きぜつの原因が相手のワザではない（G3・G7）。"""
        def move(log):
            event = log.pop(self.declined)
            check = next(i for i in range(self.declined, len(log)) if log[i]["kind"] == "pokemon_check")
            log.insert(check + 1, event)

        self.assert_reported(move, "相手のワザのあとのきぜつの判定の中にない")

    def test_9_unneeded_prize(self):
        """「おもて」のあとに、ワザを使った側のサイドを取ったログを書き足すと、きぜつより多くサイドを取ったことになる（G33）。"""
        def prize(log):
            attacker = 1 - log[self.prevented]["player"]
            card = self.state.players[attacker].prizes[0] if self.state.players[attacker].prizes else next(
                uid for uid, c in self.state.cards.items() if c.owner == attacker)
            log.insert(self.prevented + 1, {"kind": "take_prize", "turn": log[self.prevented]["turn"], "player": attacker, "card": card,
                                            "remaining": 0})

        self.assert_reported(prize, "より多くサイドを取った")

    def test_10_missing_knock_out(self):
        def drop(log):
            del log[self.failed + 1]

        self.assert_reported(drop, "きぜつしていない")

    def test_11_wrong_order(self):
        """宣言とコインの順番を入れかえる（宣言の前にコイン）。"""
        def swap(log):
            log[self.heads_declared], log[self.heads_declared + 1] = log[self.heads_declared + 1], log[self.heads_declared]

        self.assert_reported(swap, "のすぐあとに")

    def test_12_double_processing(self):
        def twice(log):
            log[self.prevented + 1:self.prevented + 1] = [dict(e) for e in log[self.heads_declared:self.prevented + 1]]

        self.assert_reported(twice, "2 回以上")

    def test_13_extra_coin(self):
        """「こんじょう」のコインが 2 枚（乱数を余計に使った記録）。"""
        def extra(log):
            log.insert(self.prevented, dict(log[self.prevented - 1]))

        self.assert_reported(extra, "その結果")

    def test_14_choice_does_not_match(self):
        """「使わない」と答えた記録なのに、コインと結果がある（決定の答えと処理が合わない）。"""
        def mismatch(log):
            log[self.tails_declared] = {k: v for k, v in log[self.tails_declared].items() if k != "hp"} | {"kind": "ko_prevention_declined"}

        self.assert_reported(mismatch, "使わなかった")


if __name__ == "__main__":
    unittest.main()

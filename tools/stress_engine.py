"""大規模なストレス実行（v0.4e のテストの段階 C。docs/integration-audit-v0.4e.md 10 章）。ふだんの単体テストでは走らせない。

使い方（リポジトリの直下で）::

    python3 tools/stress_engine.py                         # すべての組 × 40 seed × 600 手
    python3 tools/stress_engine.py --seeds 200 --steps 800 --report stress.json
    python3 tools/stress_engine.py --scenario butterfree --start 1000 --seeds 50
    python3 tools/stress_engine.py --scenario venusaur --scenario venusaur_status   # v0.5（ポケモンパワー）
    python3 tools/stress_engine.py --scenario blastoise --scenario blastoise_mixed  # v0.6（あまごい）

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
ALL_SCENARIOS = (*driver.SCENARIOS, *POWER_SCENARIOS)
POWER_RATE = 0.35  # 自分の場にフシギバナ・カメックスがいる番で、ポケモンパワーを試す割合
POWER_USERS = (VENUSAUR, BLASTOISE)


def choose_command(state, rng: random.Random, illegal_rate: float):
    """駆動の操作に、ポケモンパワー（エナジートランス・あまごい）の使用を混ぜる。自分の番（MAIN）に自分の場にフシギバナ・カメックスが
    いなければ、駆動と同じ（v0.4e と同じ）。フシギバナだけがいれば v0.5 と同じ（乱数の使い方も同じ）。"""
    player = state.current_player
    if state.phase is not engine.Phase.MAIN or player not in (0, 1):
        return driver.choose_command(engine, state, rng, illegal_rate)
    mine = state.players[player].in_play()
    kinds = [card_id for card_id in POWER_USERS if any(state.cards[pk.card].card_id == card_id for pk in mine)]
    if not kinds or rng.random() >= POWER_RATE:
        return driver.choose_command(engine, state, rng, illegal_rate)
    kind = kinds[0] if len(kinds) == 1 else rng.choice(kinds)
    return _power_command(state, rng) if kind == VENUSAUR else _rain_dance_command(state, rng)


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


def run_game(scenario, seed: int, *, steps: int, illegal_rate: float, serialize_every: int) -> tuple[Counter, list[str]]:
    """1 局を進め、数えた結果と問題を返す。"""
    counted, problems = Counter(), []
    rng = random.Random(f"kyuura-stress:{scenario.name}:{seed}")
    state = engine.new_game(driver._deck(scenario.deck0), driver._deck(scenario.deck1), seed)
    for index in range(steps):
        if state.phase in engine.TERMINAL_PHASES:
            break
        command = choose_command(state, rng, illegal_rate)
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
            continue
        except Exception as error:  # noqa: BLE001  内部の誤り
            counted["internal_error"] += 1
            problems.append(f"{index} 手目 {engine.command_to_dict(command)}: {type(error).__name__}: {error}")
            break
        counted["accepted"] += 1
        counted[f"accepted:{type(command).__name__}"] += 1
        if isinstance(command, engine.UsePokemonPower) and new.log[-1]["kind"] == "power_attach_energy":
            counted["accepted:rain_dance"] += 1
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
          f"ポケモンパワー（受け付けた） {counts.get('accepted:UsePokemonPower', 0)}（うちあまごい {counts.get('accepted:rain_dance', 0)}）"
          f"（{result['seconds']} 秒）")
    for failure in result["failures"]:
        print(f"- {failure['scenario']} seed {failure['seed']}: {failure['problems'][0]}")
    return 1 if result["failures"] else 0


if __name__ == "__main__":
    sys.exit(main())

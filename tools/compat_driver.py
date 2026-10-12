"""版の比較の駆動（v0.4e。docs/compatibility-v0.4e.md）。標準ライブラリだけを使う。

同じ入力（デッキ・seed・操作の列）を、ある版のエンジンに渡し、1 手ごとの記録（送った操作・受け付けたか・拒否のコード・状態の
指紋・乱数の指紋・ログの長さ・形式 1〜8 の書き出し）を作る。操作は、エンジンの公開の API（``new_game``・``apply_command``・
``state_to_dict``・コマンドのクラス・状態の読み取り）だけを見て決める（版ごとのテストの道具・手順には頼らない）。どの版でも、
状態が同じなら同じ操作を選ぶので、記録の食い違いは、その手でエンジンの動きが変わったことを表す。

操作の選び方は対戦相手の AI ではない: 駆動用の乱数（エンジンの乱数とは別）で、ルール上できそうな操作（ベンチに出す・進化・
エネルギー・トレーナー・にげる・ワザ・番を終える・決定への答え）と、わざと不正な操作（ほかのプレイヤー・ない番号・段階の違う
コマンドなど）を混ぜる。

2 つの使い方:

- 別のプロセスで: ``python3 -I tools/compat_driver.py --tree DIR --out FILE [--scenario NAME ...] [--dump NAME SEED INDEX]``。
  ``DIR`` の ``kyuura_engine`` だけを読み込む（``-I`` で環境変数・利用者の site を読まず、スクリプトの場所も ``sys.path`` に
  入れない。読み込んだ ``kyuura_engine.__file__`` が ``DIR`` の下にあることを確かめる）。
  tools/compare_engine_versions.py が、比べる 2 つの版のそれぞれで起動する。
- 同じプロセスで: ``run_scenario(engine, scenario, seed)``（``engine`` は読み込んだ ``kyuura_engine``）。
  tests/test_cross_version_compatibility.py の軽い回帰テストが、今の版で使う。
"""

from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import random
import sys
from dataclasses import dataclass, field

# 比べるときに除く項目: 効果の登録表の id（版ごとの名前。登録の中身は記録の動きに表れる）だけ。ルールの動きに関わる状態・ログは
# 除かない（docs/compatibility-v0.4e.md 3 章）
EXCLUDED_TOP_LEVEL = ("effects",)

GRASS, FIRE, WATER, LIGHTNING, FIGHTING = "PMCG1-097", "PMCG1-098", "PMCG1-099", "PMCG1-100", "PMCG1-102"
CATERPIE, METAPOD, BUTTERFREE = "PMCG1-002", "PMCG1-003", "PMCG2-007"
WEEDLE, KAKUNA, BEEDRILL = "PMCG1-004", "PMCG1-009", "PMCG1-012"
PARAS, PARASECT, SEEL, DEWGONG = "PMCG2-003", "PMCG2-010", "PMCG1-029", "PMCG1-030"
VULPIX, PONYTA, GROWLITHE, STARYU, VOLTORB = "PMCG1-015", "PMCG1-016", "PMCG1-018", "PMCG1-025", "PMCG1-037"
DIGLETT, MACHOP, HITMONCHAN, RATTATA, DRATINI, DODUO, PIKACHU = (
    "PMCG1-052", "PMCG1-053", "PMCG1-058", "PMCG1-060", "PMCG1-065", "PMCG1-061", "PMCG1-035")
POTION, SWITCH, BILL, DEFENDER, PLUSPOWER = "PMCG1-071", "PMCG1-073", "PMCG1-074", "PMCG1-079", "PMCG1-081"


def _deck(counts: dict[str, int]) -> list[str]:
    cards = [card_id for card_id, n in counts.items() for _ in range(n)]
    if len(cards) != 60:
        raise ValueError(f"デッキが {len(cards)} 枚")
    return cards


@dataclass(frozen=True)
class Scenario:
    """比べる対戦の組: デッキ 2 つ・seed の並び・1 局の手数の上限・不正な操作を混ぜる割合。"""

    name: str
    deck0: dict[str, int]
    deck1: dict[str, int]
    seeds: tuple[int, ...]
    steps: int = 400
    illegal_rate: float = 0.15
    tags: tuple[str, ...] = field(default=())


SCENARIOS = (
    Scenario("basics", {GROWLITHE: 4, PONYTA: 4, RATTATA: 4, DRATINI: 4, VOLTORB: 4, FIRE: 40},
             {STARYU: 4, SEEL: 4, DIGLETT: 4, MACHOP: 4, HITMONCHAN: 4, WATER: 20, FIGHTING: 20}, tuple(range(6)),
             tags=("たねポケモンだけ",)),
    Scenario("trainers", {DODUO: 4, GROWLITHE: 4, RATTATA: 4, DRATINI: 4, VOLTORB: 4, BILL: 4, POTION: 4, SWITCH: 4, PLUSPOWER: 4,
                          DEFENDER: 4, FIRE: 20},
             {STARYU: 4, SEEL: 4, DIGLETT: 4, MACHOP: 4, PIKACHU: 4, BILL: 4, POTION: 2, SWITCH: 2, PLUSPOWER: 2, DEFENDER: 2,
              WATER: 14, LIGHTNING: 14}, tuple(range(6)), tags=("トレーナー", "プラスパワー", "ディフェンダー")),
    Scenario("status", {WEEDLE: 4, CATERPIE: 4, PARAS: 4, VULPIX: 4, RATTATA: 4, SWITCH: 2, BILL: 2, GRASS: 28, FIRE: 8},
             {WEEDLE: 4, CATERPIE: 4, PARAS: 4, VULPIX: 4, PIKACHU: 4, POTION: 2, BILL: 2, GRASS: 24, FIRE: 6, LIGHTNING: 6},
             tuple(range(6)), tags=("どく", "ねむり", "マヒ", "こんらん")),
    Scenario("evolution", {PARAS: 4, PARASECT: 4, SEEL: 4, DEWGONG: 4, RATTATA: 4, SWITCH: 2, POTION: 2, GRASS: 18, WATER: 18},
             {PARAS: 4, PARASECT: 3, SEEL: 4, DEWGONG: 3, GROWLITHE: 4, DEFENDER: 2, BILL: 2, GRASS: 14, WATER: 14, FIRE: 10},
             tuple(range(6)), tags=("パラス→パラセクト", "パウワウ→ジュゴン")),
    Scenario("harden", {CATERPIE: 4, METAPOD: 4, WEEDLE: 4, KAKUNA: 4, DODUO: 4, PLUSPOWER: 2, SWITCH: 2, GRASS: 36},
             {CATERPIE: 4, METAPOD: 4, WEEDLE: 4, KAKUNA: 4, PIKACHU: 4, DEFENDER: 2, BILL: 2, GRASS: 28, LIGHTNING: 8},
             tuple(range(6)), tags=("キャタピー→トランセル", "ビードル→コクーン", "かたまる")),
    Scenario("stage2", {WEEDLE: 4, KAKUNA: 4, BEEDRILL: 4, DODUO: 4, SWITCH: 2, POTION: 2, GRASS: 40},
             {WEEDLE: 4, KAKUNA: 4, BEEDRILL: 3, VULPIX: 4, DEFENDER: 2, BILL: 2, GRASS: 33, FIRE: 8},
             tuple(range(6)), tags=("スピアー",)),
    Scenario("butterfree", {CATERPIE: 4, METAPOD: 4, BUTTERFREE: 4, RATTATA: 4, DEFENDER: 2, PLUSPOWER: 2, SWITCH: 2, GRASS: 38},
             {CATERPIE: 4, METAPOD: 4, BUTTERFREE: 3, WEEDLE: 4, KAKUNA: 3, PARAS: 2, DEFENDER: 2, POTION: 2, GRASS: 36},
             tuple(range(6)), tags=("バタフリー", "ふきとばし", "メガドレイン")),
    Scenario("all", {CATERPIE: 4, METAPOD: 3, BUTTERFREE: 2, SEEL: 3, DEWGONG: 2, DODUO: 2, VULPIX: 2, PLUSPOWER: 2, DEFENDER: 2,
                     SWITCH: 2, BILL: 3, POTION: 2, GRASS: 17, WATER: 10, FIRE: 4},
             {WEEDLE: 4, KAKUNA: 3, BEEDRILL: 2, PARAS: 3, PARASECT: 2, PIKACHU: 2, GROWLITHE: 2, PLUSPOWER: 2, DEFENDER: 2,
              SWITCH: 2, BILL: 2, POTION: 2, GRASS: 20, LIGHTNING: 6, FIRE: 6}, tuple(range(8)), steps=500,
             tags=("すべての対応カード",)),
)
SCENARIOS_BY_NAME = {s.name: s for s in SCENARIOS}


def _digest(value) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False, default=str).encode()).hexdigest()


def comparable_state(engine, state) -> dict:
    """比べる状態: 形式 8 の書き出しから、効果の登録表の id だけを除いたもの（ログ・乱数の指紋・決定・止めた理由を含む）。"""
    data = engine.state_to_dict(state, format_version=8)
    for key in EXCLUDED_TOP_LEVEL:
        data.pop(key, None)
    return data


def format_record(engine, state) -> list[str]:
    """形式 1〜8 の書き出し: 書き出せたら（登録表の id を除いた）指紋、表せなければ ``ValueError``。"""
    out = []
    for version in range(1, 9):
        try:
            data = engine.state_to_dict(state, format_version=version)
        except ValueError:
            out.append("ValueError")
            continue
        for key in EXCLUDED_TOP_LEVEL:
            data.pop(key, None)
        out.append(_digest(data)[:16])
    return out


def choose_command(engine, state, rng: random.Random, illegal_rate: float):
    """今の状態で送る操作を 1 つ選ぶ（公開の API だけを見る）。"""
    Phase = engine.Phase
    phase = state.phase
    players = state.players
    if rng.random() < illegal_rate:
        return _odd_command(engine, state, rng)
    if phase is Phase.SETUP_PLACEMENT:
        player = 0 if not players[0].placed_starting_pokemon else 1
        basics = [u for u in players[player].hand if state.card_def(u).is_basic_pokemon]
        bench = tuple(b for b in basics[1:6] if rng.random() < 0.8)
        return engine.PlaceStartingPokemon(player, basics[0], bench)
    if phase is Phase.SETUP_MULLIGAN_DRAW:
        player = 0 if players[0].mulligan_draws_remaining else 1
        return engine.DrawMulliganCards(player, min(rng.randint(0, 2), len(players[player].deck)))
    if phase is Phase.SETUP_FIRST_PLAYER:
        return engine.ReportJankenResult(rng.randint(0, 1))
    d = state.decision
    if d is not None:
        if phase is Phase.TAKE_PRIZE and rng.random() < 0.5:
            return engine.TakePrize(d.player, rng.randrange(len(d.options)))
        if phase is Phase.PROMOTE_ACTIVE and rng.random() < 0.5:
            chosen = rng.choice(d.options)
            pokemon = next(p for p in players[d.player].bench if p.pokemon_id == chosen)
            return engine.PromoteActive(d.player, pokemon.card)
        count = rng.randint(d.min_choices, min(d.max_choices, len(d.options)))
        return engine.ResolveDecision(d.player, d.id, tuple(rng.sample(list(d.options), count)))
    if phase is not Phase.MAIN:
        return engine.EndTurn(state.current_player if state.current_player in (0, 1) else 0)
    return _main_command(engine, state, rng)


def _main_command(engine, state, rng):
    player = state.current_player
    p = state.players[player]
    hand = list(p.hand)
    weighted = []
    for uid in hand:
        definition = state.card_def(uid)
        if definition.is_basic_pokemon and len(p.bench) < 5:
            weighted.append((4, engine.PlayBasicToBench(player, uid)))
        elif definition.category == "pokemon":
            for target in p.in_play():
                if definition.evolves_from == state.card_def(target.card).name_ja:
                    weighted.append((6, engine.EvolvePokemon(player, uid, target.pokemon_id)))
        elif definition.category == "trainer":
            weighted.append((3, engine.PlayTrainer(player, uid)))
    energies = [u for u in hand if state.card_def(u).is_basic_energy]
    if energies and state.energy_attachments_this_turn == 0:
        for target in p.in_play():
            weighted.append((5 if target is p.active else 2, engine.AttachEnergy(player, energies[0], target.card)))
    if p.bench and p.active is not None:
        cost = state.card_def(p.active.card).retreat_cost
        for target in p.bench:
            weighted.append((1, engine.Retreat(player, tuple(p.active.energy[:cost]), target.card)))
    if p.active is not None:
        definition = state.card_def(p.active.card)
        for index, attack in enumerate(definition.attacks):
            payable = engine.can_pay_cost(attack.cost, state.energy_types(p.active))
            weighted.append((8 if payable else 1, engine.UseAttack(player, index)))
    weighted.append((2, engine.EndTurn(player)))
    total = sum(w for w, _ in weighted)
    pick = rng.random() * total
    for weight, command in weighted:
        pick -= weight
        if pick < 0:
            return command
    return weighted[-1][1]


def _odd_command(engine, state, rng):
    """わざと不正な・段階の違う操作（ほかのプレイヤー・ない番号・選べない答えなど）。"""
    player = state.current_player if state.current_player in (0, 1) else rng.randint(0, 1)
    other = 1 - player
    uids = sorted(state.cards)
    ids = [p.pokemon_id for q in state.players for p in q.in_play()] + [0, 999]
    d = state.decision
    choices = [
        engine.EndTurn(other), engine.EndTurn(player), engine.UseAttack(player, rng.choice([2, 5, -1])),
        engine.UseAttack(other, 0), engine.PlayBasicToBench(player, rng.choice(uids + [-1])),
        engine.AttachEnergy(player, rng.choice(uids), rng.choice(uids)), engine.PlayTrainer(player, rng.choice(uids)),
        engine.EvolvePokemon(player, rng.choice(uids), rng.choice(ids)), engine.Retreat(player, (), rng.choice(uids)),
        engine.TakePrize(rng.randint(0, 1), rng.randint(-1, 6)), engine.PromoteActive(rng.randint(0, 1), rng.choice(uids)),
        engine.ResolveDecision(rng.randint(0, 1), rng.randint(0, 9), (rng.choice(ids),)), engine.DrawMulliganCards(player, 2),
        engine.ReportJankenResult(player), engine.PlaceStartingPokemon(player, rng.choice(uids)),
    ]
    if d is not None:
        choices += [
            engine.ResolveDecision(1 - d.player, d.id, d.options[:1]), engine.ResolveDecision(d.player, d.id + 1, d.options[:1]),
            engine.ResolveDecision(d.player, d.id, ()), engine.ResolveDecision(d.player, d.id, (rng.choice(ids),)),
            engine.ResolveDecision(d.player, d.id, tuple(d.options) + tuple(d.options[:1])),
        ]
    return rng.choice(choices)


def run_scenario(engine, scenario: Scenario, seed: int, *, dump_index: int | None = None):
    """1 局を進め、1 手ごとの記録の並びを返す。``dump_index`` を渡したら、その手の詳しい情報（前の状態・操作・結果・ログの
    増えた部分・乱数）だけを返す（食い違いの診断用）。"""
    rng = random.Random(f"kyuura-compat:{scenario.name}:{seed}")
    deck0, deck1 = _deck(scenario.deck0), _deck(scenario.deck1)
    state = engine.new_game(deck0, deck1, seed)
    records = [{"i": 0, "cmd": {"command": "new_game", "seed": seed}, "res": "ok", "state": _digest(comparable_state(engine, state)),
                "rng": engine.state_to_dict(state, format_version=8)["rng_state_sha256"], "phase": state.phase.value,
                "log": len(state.log), "formats": format_record(engine, state)}]
    for index in range(1, scenario.steps + 1):
        if state.phase in engine.TERMINAL_PHASES:
            break
        command = choose_command(engine, state, rng, scenario.illegal_rate)
        before = comparable_state(engine, state) if dump_index == index else None
        before_digest = records[-1]["state"]  # 前の手の記録（同じ状態）の指紋
        try:
            new = engine.apply_command(state, command)
            result = "ok"
        except engine.EngineError as error:
            new, result = state, f"{type(error).__name__}:{error.code}"
        except Exception as error:  # エンジンの内部の誤り（比べる記録に残して止める）
            records.append({"i": index, "cmd": engine.command_to_dict(command), "res": f"INTERNAL:{type(error).__name__}:{error}"})
            break
        if result != "ok" and _digest(comparable_state(engine, state)) != before_digest:
            result += ":STATE_CHANGED_BY_REJECTION"  # 拒否したのに渡した状態が変わった（エンジンの誤り）
        record = {
            "i": index, "cmd": engine.command_to_dict(command), "res": result, "state": _digest(comparable_state(engine, new)),
            "rng": engine.state_to_dict(new, format_version=8)["rng_state_sha256"], "phase": new.phase.value, "log": len(new.log),
            "formats": format_record(engine, new),
        }
        if dump_index == index:
            return {"scenario": scenario.name, "seed": seed, "index": index, "record": record, "before": before,
                    "after": comparable_state(engine, new), "log_added": [dict(e) for e in new.log[len(state.log):]]}
        records.append(record)
        state = new
    return records


def record_digest(record: dict) -> str:
    return _digest(record)[:20]


def _load_engine(tree: pathlib.Path):
    tree = tree.resolve()
    sys.path.insert(0, str(tree))
    import kyuura_engine  # noqa: PLC0415

    location = pathlib.Path(kyuura_engine.__file__).resolve()
    if tree not in location.parents:
        raise SystemExit(f"kyuura_engine を {tree} から読み込めなかった（{location}）")
    return kyuura_engine


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="版の比較の駆動（1 つの版で記録を作る）")
    parser.add_argument("--tree", required=True, type=pathlib.Path, help="kyuura_engine のある木（この版だけを読み込む）")
    parser.add_argument("--out", required=True, type=pathlib.Path)
    parser.add_argument("--scenario", action="append", help="比べる組の名前（省略ですべて）")
    parser.add_argument("--seeds", type=int, default=None, help="組ごとに使う seed の数（省略で組の既定）")
    parser.add_argument("--steps", type=int, default=None, help="1 局の手数の上限（省略で組の既定）")
    parser.add_argument("--dump", nargs=3, metavar=("SCENARIO", "SEED", "INDEX"), help="1 手の詳しい情報だけを書き出す")
    args = parser.parse_args(argv)
    engine = _load_engine(args.tree)
    if args.dump:
        name, seed, index = args.dump[0], int(args.dump[1]), int(args.dump[2])
        scenario = SCENARIOS_BY_NAME[name]
        if args.steps:
            scenario = Scenario(**{**scenario.__dict__, "steps": args.steps})
        args.out.write_text(json.dumps(run_scenario(engine, scenario, seed, dump_index=index), ensure_ascii=False, default=str))
        return 0
    output = {"engine_file": engine.__file__, "version": getattr(engine, "__version__", None), "games": []}
    for scenario in SCENARIOS:
        if args.scenario and scenario.name not in args.scenario:
            continue
        if args.steps:
            scenario = Scenario(**{**scenario.__dict__, "steps": args.steps})
        seeds = scenario.seeds if args.seeds is None else tuple(range(args.seeds))
        for seed in seeds:
            output["games"].append({"scenario": scenario.name, "seed": seed, "records": run_scenario(engine, scenario, seed)})
    args.out.write_text(json.dumps(output, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())

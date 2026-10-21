"""v0.62: 前の番のワザの履歴を読むワザ・相手を手札にもどすワザの 5 枚と、確定した修正を当てはめたベロリンガ（docs/history-attacks-v0.62.md）。

6 枚: ピジョン（PMCG1-066。ふきとばし・オウムがえし）・オニスズメ（PMCG2-034。つつく・オウムがえし）・オニドリル（PMCG2-038。こうそくいどう・ドリルくちばし）・
ピジョット（PMCG2-043。つばさでうつ・ハリケーン）・タケシのダグトリオ（PMCG6-060。あながくれ・ドリルホール）・ベロリンガ（PMCG2-041。まきつくベロ・ちょうおんぱ）。
どれも kyuura データの採用（採用したデータのコミット ecb2d69）と pcg-search.com の同じ版のページとの照合。ベロリンガのワザ 1 の名前・レベルは、kyuura の照合の記録
CC-PMCG2-041-P234（研究の基準のコミット 3f34908。修正のコミット f52a8e2）の確定した修正を写しに当てはめた値。ガイドブックは読んでいない。

場のポケモンのワザの履歴（``PokemonInPlay.history``）は、使ったワザ（A。``AttackUsed``）・受けたワザ（B）と実際に受けた結果（C）（``AttackReceived``）・ワザ以外で受けたこと
（``OtherReceived``）を分けて持つ。新しい停止コード: MM1・MM2・OM1・OM2。コードのない問い: ED1。エンジンの未対応: UNSUPPORTED_MIRROR_MOVE_EFFECT・
UNSUPPORTED_MIRROR_MOVE_ATTACK。
"""

from __future__ import annotations

import json
import pathlib
import pickle
import re
import subprocess
import unittest

from kyuura_engine import (
    EndTurn,
    IllegalActionError,
    PlayTrainer,
    ResolveDecision,
    Retreat,
    UnsupportedError,
    UseAttack,
    check_invariants,
    state_to_dict,
)
from kyuura_engine import effects as E
from kyuura_engine.cards import classify_record, load_card_pool
from kyuura_engine.history import (
    VOID_ATTACK_BARRIER,
    VOID_DAMAGE_ONLY,
    history_needed,
)
from kyuura_engine.observation import observe
from kyuura_engine.resolution.questions import QUESTIONS
from kyuura_engine.serialize import FORMAT_VERSIONS
from kyuura_engine.state import AttackReceived, AttackUsed, OtherReceived
from tests.helpers import (
    BROCKS_DIGLETT,
    BROCKS_DUGTRIO,
    BROCKS_MANKEY,
    BROCKS_PRIMEAPE,
    CLEFAIRY,
    DIGGER,
    FEAROW,
    FIGHTING,
    GIOVANNIS_MACHAMP,
    GIOVANNIS_MACHOKE,
    GIOVANNIS_MACHOP,
    GRASS,
    HAUNTER,
    HITMONCHAN,
    LICKITUNG,
    MACHAMP,
    MACHOKE,
    MACHOP,
    PIDGEOT,
    PIDGEOTTO,
    PIDGEY,
    PLUSPOWER,
    PSYCHIC,
    RATTATA,
    SPEAROW,
    SWITCH,
    V0_62_CARDS,
    CoinSide,
    apply_kernel,
    build_test_state,
    with_coin_results,
)
from tests.log_audit import LATEST_FORMAT, observation_problems, serialization_problems

ROOT = pathlib.Path(__file__).resolve().parent.parent
DOC = ROOT / "docs" / "history-attacks-v0.62.md"
KYUURA = ROOT.parent / "kyuura"
H, T = CoinSide.HEADS, CoinSide.TAILS
F, G, P = FIGHTING, GRASS, PSYCHIC
TURN = 5  # 先攻（プレイヤー 0）の番


def mon(card, energy=(), **extra):
    return {"card": card, "energy": list(energy), **extra}


def dugtrio(energy=(F, F, F), **extra):
    return mon(BROCKS_DUGTRIO, energy, evolved_from=BROCKS_DIGLETT, **extra)


def pidgeotto(energy=(G, G, G), **extra):
    return mon(PIDGEOTTO, energy, evolved_from=PIDGEY, **extra)


def pidgeot(energy=(G, G, G), **extra):
    return mon(PIDGEOT, energy, evolved_from=[PIDGEY, PIDGEOTTO], **extra)


def table(active, bench=(RATTATA,), *, opponent_active=None, opponent_bench=(RATTATA,), current=0, turn=TURN, hand=(), opponent_hand=()):
    me = {"active": active, "bench": list(bench), "deck": [G] * 10, "prizes": 3, "hand": list(hand)}
    them = {"active": opponent_active or mon(LICKITUNG, (G, G)), "bench": list(opponent_bench), "deck": [F] * 10, "prizes": 3,
            "hand": list(opponent_hand)}
    return build_test_state([me, them], turn_number=turn, current_player=current)


def act(state, command, *coins, **options):
    if coins:
        state = with_coin_results(state, *coins)
    return apply_kernel(state, command, **options)


def answer(state, choices, *coins):
    return act(state, ResolveDecision(state.decision.player, state.decision.id, tuple(choices)), *coins)


def since(new, old):
    return list(new.log[len(old.log):])


def kinds(events):
    return [e["kind"] for e in events]


def snapshot(state):
    return state_to_dict(state, format_version=max(FORMAT_VERSIONS)), [dict(e) for e in state.log], repr(state.rng.getstate())


def active(state, player):
    return state.players[player].active


def audited(test, state):
    test.assertEqual(check_invariants(state), [])
    test.assertEqual(serialization_problems(state), [])
    test.assertEqual(observation_problems(state), [])


def assert_stops(test, state, command, code, error=UnsupportedError, *coins):
    if coins:
        state = with_coin_results(state, *coins)
    before = snapshot(state)
    with test.assertRaises(error) as caught:
        apply_kernel(state, command)
    test.assertEqual(caught.exception.code, code)
    test.assertEqual(snapshot(state), before)  # 状態・ログ・乱数は変わらない


class RegistryTest(unittest.TestCase):
    """6 枚のどのワザも登録した（ワザ 12）。数は登録表から数える。"""

    def test_all_six_cards_and_twelve_attacks_supported(self):
        data = json.loads((ROOT / "kyuura_engine" / "data" / "kyuura_cards.json").read_text(encoding="utf-8"))
        records = {c["id"]: c for c in data["cards"]}
        attacks = 0
        for card_id in V0_62_CARDS:
            definition = classify_record(records[card_id], E.DEFAULT_EFFECTS)
            self.assertTrue(definition.supported, card_id)
            for index, attack in enumerate(definition.attacks):
                self.assertIsNotNone(E.DEFAULT_EFFECTS.attack_entry(card_id, index), (card_id, attack.name_ja))
                attacks += 1
        self.assertEqual(attacks, 12)

    def test_counts(self):
        pool = load_card_pool()
        supported = [d for d in pool.definitions.values() if d.supported]
        by_category = {c: sum(1 for d in supported if d.category == c) for c in ("pokemon", "trainer", "energy")}
        self.assertEqual(by_category, {"pokemon": 695, "trainer": 213, "energy": 35})  # v0.79 でポケモン 52 枚（ワザ 94）を加えた  # v0.78 で悪・鋼エネルギー 5 枚とポケモン 8 枚（ワザ 16）を加えた  # v0.77 で neo 期の拡張パックの 52 枚（ポケモン 50・ワザ 77・トレーナー 2）を加えた  # v0.76 で拡張パック以外の商品のポケモン 24 枚（ワザ 48）を加えた  # v0.75 で拡張パック以外の商品のポケモン 15 枚（ワザ 30）を加えた  # v0.74 で拡張パック以外の商品のスタジアム 13 枚  # v0.73 で拡張パック以外の商品のトレーナー 18 枚  # v0.72 で拡張パック以外の商品のポケモン 43 枚  # v0.71 で拡張パック以外の商品の再録 78 枚（ポケモン 11・トレーナー 67）  # v0.70 で拡張パック以外の商品のポケモン 82 枚  # v0.69 で拡張パック以外の商品の同じカード 96 枚  # v0.68 でポケモン 3 枚  # v0.63 でトレーナー 4 枚、v0.64 でポケモン 3 枚、v0.65 でポケモン 2 枚・トレーナー 1 枚  # v0.66 でトレーナー 3 枚  # v0.67 でトレーナー 1 枚
        self.assertEqual(len(E.DEFAULT_EFFECTS.attack_keys()), 1182)  # v0.79 でポケモン 52 枚（ワザ 94）を加えた  # v0.78 で悪・鋼エネルギー 5 枚とポケモン 8 枚（ワザ 16）を加えた  # v0.77 で neo 期の拡張パックの 52 枚（ポケモン 50・ワザ 77・トレーナー 2）を加えた  # v0.76 で拡張パック以外の商品のポケモン 24 枚（ワザ 48）を加えた  # v0.75 で拡張パック以外の商品のポケモン 15 枚（ワザ 30）を加えた  # v0.72 でワザ 77（拡張パック以外の商品のポケモン 43 枚）  # v0.71 でワザ 15（拡張パック以外の商品の再録）  # v0.70 でワザ 136（拡張パック以外の商品のポケモン 82 枚）  # v0.69 でワザ 92（拡張パック以外の商品の同じカード。元のカードの登録を写した）  # v0.68 でワザ 4 つ  # v0.64 でワザ 5 つ、v0.65 でワザ 2 つを加えた
        self.assertEqual(len(E.DEFAULT_EFFECTS.power_keys()), 74)  # v0.71 で 6（再録）  # v0.69 で 10  # v0.68 で 2 つ  # v0.65 で［にげこむ］・［ベンチガード］を加えた

    def test_history_readers(self):
        readers = {type(e.effect).__name__ for e in E.DEFAULT_EFFECTS._attacks.values() if e.effect.reads_history}
        self.assertEqual(readers, {"DamageIfUsedAttackLastTurn", "RepeatReceivedAttack", "ReflectReceivedDamageAndEffects"})

    def test_history_only_recorded_when_a_reader_is_in_the_game(self):
        # 履歴を読むワザのない対戦では記録しない（v0.61 までと同じ状態・書き出し）
        state = build_test_state([{"active": mon(HITMONCHAN, (F, F, F)), "deck": [F] * 5, "prizes": 1},
                                  {"active": mon(RATTATA, (G,)), "deck": [G] * 5, "prizes": 1}], turn_number=TURN)
        self.assertFalse(history_needed(state))
        after = act(state, EndTurn(0))
        after = act(after, UseAttack(1, 0))
        self.assertTrue(all(not p.history for pl in after.players for p in pl.in_play()))
        self.assertEqual(serialization_problems(after), [])
        self.assertTrue(history_needed(table(dugtrio())))

    def test_no_card_id_branches_in_engine(self):
        for path in [ROOT / "kyuura_engine" / "engine.py", ROOT / "kyuura_engine" / "history.py", *(ROOT / "kyuura_engine" / "resolution").glob("*.py")]:
            text = path.read_text(encoding="utf-8")
            for card_id in V0_62_CARDS:
                self.assertNotIn(f'"{card_id}"', text, path.name)


class CorrectionTest(unittest.TestCase):
    """ベロリンガの確定した修正（CC-PMCG2-041-P234）。v0.62〜v0.68 はエンジンが写しの元（ecb2d69）の値に当てはめていた（CONFIRMED_CORRECTIONS）。
    v0.69 から、kyuura が data/cards.json に当てはめた（台帳 data/curation/card_corrections.json の FIX-PMCG2-041-ATK0-NAME・FIX-PMCG2-041-LEVEL）ので、
    エンジンは当てはめ直さず、台帳・カードの記録・前後のコミットの値を確かめる（scripts/extract_kyuura_cards.py の KYUURA_CORRECTIONS）。"""

    def setUp(self):
        self.data = json.loads((ROOT / "kyuura_engine" / "data" / "kyuura_cards.json").read_text(encoding="utf-8"))
        self.card = next(c for c in self.data["cards"] if c["id"] == LICKITUNG)

    def test_corrected_values_in_copy(self):
        self.assertEqual(self.card["pokemon"]["attacks"][0]["name"]["ja"], "まきつくベロ")
        self.assertEqual(self.card["jp_print"]["level"], 26)
        # 修正の欄のほかの処理に使う欄は直す前から同じ。出典の記録の欄（notes・ja_text_source）は kyuura の値（v0.69 から写しの元が 7d3f4ca）
        self.assertEqual(self.card["pokemon"]["attacks"][0]["text"]["ja"], "コインを投げて「おもて」なら、相手を「マヒ」状態にする。")
        self.assertEqual(self.card["pokemon"]["attacks"][0]["cost"], ["colorless"])
        self.assertEqual(self.card["pokemon"]["attacks"][0]["damage"]["display"], "10")
        self.assertEqual({x["id"] for x in self.card["corrections"]}, {"FIX-PMCG2-041-ATK0-NAME", "FIX-PMCG2-041-LEVEL"})

    def test_corrections_recorded_with_source(self):
        self.assertEqual(self.data["source"]["commit"], "7d3f4ca76c084774efb4ac6a1d3a943387e183c3")
        self.assertNotIn("corrections", self.data)  # エンジンが当てはめる修正はもうない（二重の修正をしない）
        fields = {(c["card_id"], c["field"]): c for c in self.data["kyuura_corrections"] if c["card_id"] == LICKITUNG}
        self.assertEqual(set(fields), {(LICKITUNG, "pokemon.attacks[0].name.ja"), (LICKITUNG, "jp_print.level")})
        for c in fields.values():
            self.assertEqual(c["basis"], "kyuura_source_check")
            self.assertEqual(c["record"], "CC-PMCG2-041-P234")
            self.assertEqual(c["commit"], "f52a8e2e9d65055727f7b8bc3165e0fd15b96967")
            self.assertEqual(c["applied_in_source"], self.data["source"]["commit"])
            self.assertEqual(c["previous_source"], "ecb2d694e6280ec5dc9ddd2a8f709cea16a6b691")
        self.assertEqual(fields[(LICKITUNG, "pokemon.attacks[0].name.ja")]["before"], "したでなめる")
        self.assertEqual(fields[(LICKITUNG, "jp_print.level")]["before"], 29)

    def test_only_lickitung_and_kangaskhan_are_corrected(self):
        # v0.71: 写しに加えたナツメのスリーパー（GD6-010。ふりこののろいのダメージの「×」。kyuura の前の判定による台帳の修正）
        self.assertEqual({c["card_id"] for c in self.data["kyuura_corrections"]}, {LICKITUNG, "PMCG2-046", "GD6-010"})
        self.assertEqual({c["id"] for c in self.data["cards"] if c.get("corrections")}, {LICKITUNG, "PMCG2-046", "GD6-010"})

    @unittest.skipUnless((KYUURA / ".git").exists(), "../kyuura がない")
    def test_correction_sources_check_and_tampering(self):
        import importlib.util

        spec = importlib.util.spec_from_file_location("extract_kyuura_cards", ROOT / "scripts" / "extract_kyuura_cards.py")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        source = module.read_kyuura_cards(KYUURA)
        previous = json.loads(module._show(KYUURA, module.PREVIOUS_KYUURA_COMMIT, module.KYUURA_PATH).decode("utf-8"))
        pool = module.all_pool_cards() + module.REFERENCE_ONLY
        self.assertEqual(module.kyuura_correction_problems(KYUURA, source, previous, pool), [])
        self.assertEqual(module.previous_copy_problems(source, previous, pool), [])
        targets = module.equivalent_targets(KYUURA)
        self.assertEqual(module.render(module.build_extract(source, targets, module.reprint_targets(KYUURA))), (ROOT / "kyuura_engine" / "data" / "kyuura_cards.json").read_text(encoding="utf-8"))
        original = list(module.KYUURA_CORRECTIONS)
        try:
            # 前の値・あとの値・記録・コミットが台帳やコミットの値と違えば、書き出さない
            module.KYUURA_CORRECTIONS[:] = [dict(original[0], before="ちがう名前"), *original[1:]]
            self.assertTrue(any("前の写しの元" in p for p in module.kyuura_correction_problems(KYUURA, source, previous, pool)))
            module.KYUURA_CORRECTIONS[:] = [dict(original[0], after="ちがう名前"), *original[1:]]
            self.assertTrue(any("当てはまっていない" in p for p in module.kyuura_correction_problems(KYUURA, source, previous, pool)))
            module.KYUURA_CORRECTIONS[:] = [dict(original[0], record="CC-PMCG2-041-P999"), *original[1:]]
            self.assertTrue(any("照合の記録" in p for p in module.kyuura_correction_problems(KYUURA, source, previous, pool)))
            # 台帳の修正を挙げていなければ、知らない修正として書き出さない
            module.KYUURA_CORRECTIONS[:] = original[1:]
            self.assertTrue(any("挙げていない" in p for p in module.kyuura_correction_problems(KYUURA, source, previous, pool)))
            # 修正の欄を当てはめずに比べると、前の写しの元と違う欄として見つかる（修正のほかの欄の変化を見落とさない）
            module.KYUURA_CORRECTIONS[:] = original[2:]
            self.assertTrue(any("PMCG2-041" in p for p in module.previous_copy_problems(source, previous, pool)))
        finally:
            module.KYUURA_CORRECTIONS[:] = original
        result = subprocess.run(["python3", str(ROOT / "scripts" / "extract_kyuura_cards.py"), "--kyuura", str(KYUURA), "--check"], capture_output=True, text=True, check=False)
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_registered_name_is_corrected_name(self):
        self.assertEqual(E.DEFAULT_EFFECTS.attack_entry(LICKITUNG, 0).name_ja, "まきつくベロ")
        self.assertIsInstance(E.DEFAULT_EFFECTS.attack_entry(LICKITUNG, 0).effect, E.ParalyzeOnHeads)
        self.assertIsInstance(E.DEFAULT_EFFECTS.attack_entry(LICKITUNG, 1).effect, E.ConfuseOnHeadsWithoutDamage)

    def test_lickitung_attacks(self):
        state = table(mon(LICKITUNG, (G, G)), opponent_active=mon(RATTATA, (G,)))
        after = act(state, UseAttack(0, 0), H)
        self.assertEqual(active(after, 1).damage, 10)
        self.assertTrue(active(after, 1).conditions.paralyzed)
        after = act(state, UseAttack(0, 1), H)
        self.assertEqual(active(after, 1).damage, 0)
        self.assertTrue(active(after, 1).conditions.confused)


class UsedHistoryTest(unittest.TestCase):
    """使ったワザの記録（A）と、タケシのダグトリオの「ドリルホール」。"""

    def test_lie_low_recorded_at_declaration(self):
        state = table(dugtrio())
        after = act(state, UseAttack(0, 0))
        record = active(after, 0).history
        self.assertEqual(record, (AttackUsed(TURN, active(after, 0).card, (BROCKS_DUGTRIO, 0)),))
        self.assertIn("damage_reduction", [e.kind for e in active(after, 0).persistent_effects])
        audited(self, after)

    def test_earthdrill_needs_lie_low_on_previous_own_turn(self):
        state = table(dugtrio())
        assert_stops(self, state, UseAttack(0, 1), "PREVIOUS_ATTACK_NOT_USED", IllegalActionError)
        state = act(state, UseAttack(0, 0))        # 5 番: あながくれ
        state = act(state, UseAttack(1, 0), T)     # 6 番: 相手のまきつくベロ（-20 で 0）
        self.assertEqual(active(state, 0).damage, 0)
        after = act(state, UseAttack(0, 1))        # 7 番: ドリルホール
        damage = next(e for e in since(after, state) if e["kind"] == "damage")
        self.assertEqual(damage["steps"][0], ("1 基本となる計算", 60))
        audited(self, after)

    def test_earthdrill_not_with_lie_low_two_own_turns_ago(self):
        state = table(dugtrio())
        state = act(state, UseAttack(0, 0))   # 5 番
        state = act(state, EndTurn(1))        # 6 番
        state = act(state, EndTurn(0))        # 7 番（何もしない）
        state = act(state, EndTurn(1))        # 8 番
        self.assertEqual(active(state, 0).history, ())  # 2 つ前の番より古い記録は消える
        assert_stops(self, state, UseAttack(0, 1), "PREVIOUS_ATTACK_NOT_USED", IllegalActionError)

    def test_earthdrill_not_with_previous_opponent_turn(self):
        # 前の相手の番のこと（受けたワザ）は「前の自分の番に使っていた」ではない
        state = table(dugtrio(), current=1, turn=TURN - 1)
        state = act(state, UseAttack(1, 0), T)
        self.assertIsInstance(active(state, 0).history[0], AttackReceived)
        assert_stops(self, state, UseAttack(0, 1), "PREVIOUS_ATTACK_NOT_USED", IllegalActionError)

    def test_failed_declaration_counts_as_used(self):
        # こんらんの「うら」でも、宣言したワザは使ったことになる（p.323「12」・v0.3d の A12。v0.44 の 1 度だけ使えるワザと同じ時点）
        state = table(dugtrio(confusion=True))
        state = act(state, UseAttack(0, 0), T)
        self.assertEqual(active(state, 0).damage, 20)
        self.assertEqual([type(r) for r in active(state, 0).history], [AttackUsed])
        state = act(state, EndTurn(1))
        after = act(state, UseAttack(0, 1), H)
        self.assertEqual(next(e for e in since(after, state) if e["kind"] == "damage")["steps"][0], ("1 基本となる計算", 60))

    def test_rejected_declaration_is_not_recorded(self):
        state = table(dugtrio(energy=()))
        assert_stops(self, state, UseAttack(0, 0), "INSUFFICIENT_ENERGY", IllegalActionError)

    def test_history_survives_switching(self):
        # にげる・入れ替えでは消えない（使ったことは変わらない）
        state = table(dugtrio(), bench=(mon(RATTATA, (G,)),), hand=(SWITCH, SWITCH))
        state = act(state, UseAttack(0, 0))
        state = act(state, EndTurn(1))
        switches = [u for u in state.players[0].hand if state.cards[u].card_id == SWITCH]
        state = act(state, PlayTrainer(0, switches[0]))
        state = answer(state, (state.decision.options[0],))
        self.assertEqual(state.cards[state.players[0].bench[0].card].card_id, BROCKS_DUGTRIO)
        self.assertEqual(len(state.players[0].bench[0].history), 1)
        state = act(state, PlayTrainer(0, switches[1]))
        state = answer(state, (state.decision.options[0],))
        after = act(state, UseAttack(0, 1))   # ベンチにもどって、同じ番にバトル場にもどっても、前の自分の番に使った記録は残る
        self.assertIn("damage", kinds(since(after, state)))

    def test_devolution_and_evolution_clear_history(self):
        from kyuura_engine import evolution

        state = table(dugtrio())
        state = act(state, UseAttack(0, 0))
        working = state.clone()
        pokemon = working.players[0].active
        evolution.devolve(working, 0, pokemon, 1, destination=evolution.DEVOLVE_TO_DISCARD, by_player=1, trainer=working.players[0].bench[0].card)
        self.assertEqual(pokemon.history, ())

    def test_copied_earthdrill_condition(self):
        # ピッピの「ゆびをふる」で相手のドリルホールを選ぶ: ピッピが前の自分の番に「あながくれ」を使っていないので、説明にしたがうピッピは選べない
        state = table(mon(CLEFAIRY, (G, G, G)), opponent_active=dugtrio())
        after = act(state, UseAttack(0, 1))
        self.assertEqual(after.decision.kind, "select_attack")
        self.assertNotIn(1, after.decision.options)


class RepeatReceivedTest(unittest.TestCase):
    """ピジョンの「オウムがえし」: 前の相手の番で受けたワザ（B）と同じワザを出す。"""

    def received(self, opponent_attack, *coins, opponent=None, **kwargs):
        state = table(pidgeotto(**kwargs), opponent_active=opponent or mon(LICKITUNG, (G, G)), current=1, turn=TURN - 1)
        return act(state, UseAttack(1, opponent_attack), *coins)

    def test_no_received_attack_does_nothing(self):
        state = table(pidgeotto())
        after = act(state, UseAttack(0, 1))
        self.assertIn("mirror_move_none", kinds(since(after, state)))
        self.assertEqual(active(after, 1).damage, 0)
        audited(self, after)

    def test_repeats_same_attack_with_new_coins(self):
        state = self.received(1, H)          # ちょうおんぱ: こんらん
        self.assertTrue(active(state, 0).conditions.confused)
        after = act(state, UseAttack(0, 1), H, H)   # こんらんのコイン（おもて）→ ちょうおんぱのコイン（おもて）
        events = since(after, state)
        copy = next(e for e in events if e["kind"] == "copy_attack")
        self.assertEqual((copy["copied"], copy["received_turn"]), (f"{LICKITUNG}#1", TURN - 1))
        self.assertTrue(active(after, 1).conditions.confused)
        self.assertEqual(active(after, 0).history[-1], AttackUsed(TURN, active(after, 0).card, (PIDGEOTTO, 1), (LICKITUNG, 1)))
        audited(self, after)
        tails = act(state, UseAttack(0, 1), H, T)    # 前のコインの結果を使わない
        self.assertFalse(active(tails, 1).conditions.confused)

    def test_damage_uses_this_cards_type_and_current_target(self):
        state = self.received(0, T)          # まきつくベロ 10
        after = act(state, UseAttack(0, 1), T)
        self.assertEqual(active(after, 1).damage, 10)

    def test_whole_attack_voided_by_barrier_is_not_received(self):
        state = table(mon(FEAROW, (G, G, G), evolved_from=SPEAROW), opponent_active=mon(SPEAROW, (G,)))
        state = act(state, UseAttack(0, 0), H)   # こうそくいどう（おもて）: 次の相手の番、ワザをうけない
        state = act(state, UseAttack(1, 0))      # つつく
        record = active(state, 0).history[-1]
        self.assertEqual((record.reached, record.voided), ((), (("damage", VOID_ATTACK_BARRIER),)))
        audited(self, state)

    def test_damage_only_voided_is_mm1(self):
        working = build_test_state([{"active": pidgeotto(prevent_damage=TURN - 2), "bench": [RATTATA], "deck": [G] * 10, "prizes": 3},
                                    {"active": mon(LICKITUNG, (G, G)), "bench": [RATTATA], "deck": [F] * 10, "prizes": 3}],
                                   turn_number=TURN - 1, current_player=1)
        working = act(working, UseAttack(1, 0), T)    # まきつくベロのダメージを受けない（「ダメージを受けない」状態。ダメージだけ）
        record = active(working, 0).history[-1]
        self.assertEqual(record.voided, (("damage", VOID_DAMAGE_ONLY),))
        assert_stops(self, working, UseAttack(0, 1), "UNRESOLVED_MIRROR_MOVE_RECEIVED_ATTACK")

    def test_copied_received_attack_is_mm1(self):
        # 受けたワザが「ゆびをふる」で使った相手のワザ（宣言したワザ PMCG1-067#1・処理したワザ PMCG1-066#0 が違う）
        state = table(pidgeotto(), bench=(), opponent_active=mon(CLEFAIRY, (G, G, G)), current=1, turn=TURN - 1)
        state = act(state, UseAttack(1, 1))
        state = answer(state, (0,))   # ピジョンのふきとばし（ピジョンに控えはいないので、ダメージだけ）
        record = active(state, 0).history[-1]
        self.assertEqual((record.declared, record.processed), ((CLEFAIRY, 1), (PIDGEOTTO, 0)))
        self.assertEqual(active(state, 1).history[-1], AttackUsed(TURN - 1, active(state, 1).card, (CLEFAIRY, 1), (PIDGEOTTO, 0)))
        audited(self, state)
        assert_stops(self, state, UseAttack(0, 1), "UNRESOLVED_MIRROR_MOVE_RECEIVED_ATTACK")

    def test_energy_not_payable_is_mm2(self):
        # 受けたドリルホール（闘闘無）を、草のエネルギーのピジョンで出す
        state = table(pidgeotto(), opponent_active=dugtrio(), current=1, turn=TURN - 1)
        working = state.clone()
        state = act(state, EndTurn(1))
        state = act(state, EndTurn(0))
        state = act(state, UseAttack(1, 0))     # 6 番: あながくれ
        state = act(state, EndTurn(0))
        state = act(state, UseAttack(1, 1))     # 8 番: ドリルホール（ピジョンが受ける）
        self.assertEqual(active(state, 0).history[-1].processed, (BROCKS_DUGTRIO, 1))
        assert_stops(self, state, UseAttack(0, 1), "UNRESOLVED_MIRROR_MOVE_ATTACK_CONDITIONS")
        del working

    def test_whirlwind_repeated_opponent_chooses(self):
        # 受けたふきとばしを出す: 入れ替える控えは相手が選ぶ（既存の相手が選ぶ入れ替え）
        state = table(pidgeotto(), bench=(), opponent_active=pidgeotto(), opponent_bench=(RATTATA, RATTATA), current=1, turn=TURN - 1)
        state = act(state, UseAttack(1, 0))   # ピジョンのふきとばし（受けるピジョンに控えはいない）
        self.assertEqual(active(state, 0).history[-1].processed, (PIDGEOTTO, 0))
        after = act(state, UseAttack(0, 1))
        self.assertEqual((after.decision.kind, after.decision.player), ("forced_switch", 1))
        after = answer(after, (after.decision.options[-1],))
        self.assertEqual(after.cards[active(after, 1).card].card_id, RATTATA)
        audited(self, after)

class ReflectReceivedTest(unittest.TestCase):
    """オニスズメの「オウムがえし」: 前の相手の番に受けたダメージと効果（C）を相手に与える。"""

    def received(self, opponent_attack, *coins, spearow=None, opponent=None):
        state = table(spearow or mon(SPEAROW, (G, G, G)), opponent_active=opponent or mon(LICKITUNG, (G, G)), current=1, turn=TURN - 1)
        return act(state, UseAttack(1, opponent_attack), *coins)

    def test_reflects_received_damage_recalculated(self):
        state = self.received(0, T)   # まきつくベロ 10
        self.assertEqual(active(state, 0).history[-1].damage, 10)
        after = act(state, UseAttack(0, 1))
        self.assertEqual(active(after, 1).damage, 10)
        event = next(e for e in since(after, state) if e["kind"] == "reflect_received")
        self.assertEqual((event["damage"], event["effects"]), (10, ()))
        audited(self, after)

    def test_reflected_damage_is_calculated_as_this_attack(self):
        # 受けた量（10）と与える量は別に計算する（プラスパワー +10）
        state = self.received(0, T, spearow=mon(SPEAROW, (G, G, G), trainers=[(PLUSPOWER, TURN)]))
        after = act(state, UseAttack(0, 1))
        self.assertEqual(active(after, 1).damage, 20)

    def test_reflects_paralysis(self):
        state = self.received(0, H)   # まきつくベロ: 10 とマヒ
        working = state.clone()
        working.players[0].active.conditions = type(working.players[0].active.conditions)()  # マヒを直した盤面（受けた記録は変わらない）
        after = act(working, UseAttack(0, 1))
        self.assertEqual(active(after, 1).damage, 10)
        self.assertTrue(active(after, 1).conditions.paralyzed)

    def test_lasting_effect_is_om1(self):
        state = self.received(1, H)   # ちょうおんぱ: こんらん（続く特殊状態）
        assert_stops(self, state, UseAttack(0, 1), "UNRESOLVED_MIRROR_MOVE_LASTING_EFFECT", UnsupportedError, H)

    def test_non_attack_receipt_is_om2(self):
        state = table(mon(SPEAROW, (G, G, G)), opponent_active=mon(LICKITUNG, (G, G)), current=1, turn=TURN - 1, opponent_hand=(DIGGER,))
        state = act(state, PlayTrainer(1, state.players[1].hand[-1]), H, T)   # 相手から投げ、オニスズメの持ち主が「うら」
        self.assertEqual(active(state, 0).damage, 10)
        self.assertEqual(active(state, 0).history, (OtherReceived(TURN - 1, active(state, 0).card),))
        state = act(state, EndTurn(1))
        assert_stops(self, state, UseAttack(0, 1), "UNRESOLVED_MIRROR_MOVE_NON_ATTACK")

    def test_own_trainer_is_not_a_receipt(self):
        state = table(mon(SPEAROW, (G, G, G)), opponent_active=mon(LICKITUNG, (G, G)), hand=(PLUSPOWER,))
        after = act(state, PlayTrainer(0, state.players[0].hand[-1]))
        after = answer(after, (active(after, 0).pokemon_id,)) if after.decision is not None else after
        self.assertEqual(active(after, 0).history, ())

    def test_nothing_received_does_nothing(self):
        state = table(mon(SPEAROW, (G, G, G)))
        after = act(state, UseAttack(0, 1))
        self.assertIn("mirror_move_none", kinds(since(after, state)))
        self.assertEqual(active(after, 1).damage, 0)

    def test_forced_switch_is_unsupported(self):
        # 受けた入れ替え（ふきとばし）を与えるのはエンジンの未対応（ルールの問いではない）
        state = table(mon(SPEAROW, (G, G, G)), bench=(mon(RATTATA, (G,)),), opponent_active=pidgeotto(), current=1, turn=TURN - 1)
        state = act(state, UseAttack(1, 0))
        state = answer(state, (state.decision.options[0],))
        spearow = next(p for p in state.players[0].bench if state.cards[p.card].card_id == SPEAROW)
        self.assertIn("forced_switch", spearow.history[-1].reached)
        self.assertEqual(spearow.history[-1].damage, 20)
        # オニスズメをバトル場にもどして使う（ポケモンいれかえではなく、にげる。にげるエネルギー 0）
        state = act(state, Retreat(0, (), spearow.card))
        assert_stops(self, state, UseAttack(0, 1), "UNSUPPORTED_MIRROR_MOVE_EFFECT")

    def test_evolution_clears_history(self):
        # オニスズメからオニドリルへの通常の進化: 進化したポケモンは別のポケモン（p.310）なので、履歴を消す
        from kyuura_engine import EvolvePokemon

        state = table(mon(SPEAROW, (G, G, G, G)), opponent_active=mon(LICKITUNG, (G, G)), current=1, turn=TURN - 1, hand=(FEAROW,))
        state = act(state, UseAttack(1, 0), T)
        self.assertTrue(active(state, 0).history)
        fearow = next(u for u in state.players[0].hand if state.cards[u].card_id == FEAROW)
        after = act(state, EvolvePokemon(0, fearow, active(state, 0).pokemon_id))
        self.assertEqual(active(after, 0).history, ())
        self.assertEqual(active(after, 0).pokemon_id, active(state, 0).pokemon_id)
        after = act(after, UseAttack(0, 1))   # ドリルくちばし 40
        self.assertEqual(active(after, 1).damage, 40)
        self.assertEqual(active(after, 0).history, (AttackUsed(TURN, active(after, 0).card, (FEAROW, 1)),))
        audited(self, after)

    def test_transformed_ditto_reflects_its_own_received_damage(self):
        # ［へんしん］のメタモン: 今の姿はオニスズメ。受けた記録は場のポケモン（このカード = メタモン）のもの
        from tests.helpers import DITTO

        state = table(mon(DITTO, (G, G, G)), opponent_active=mon(SPEAROW, (G, G, G)), current=1, turn=TURN - 1)
        state = act(state, UseAttack(1, 0))
        self.assertEqual(active(state, 0).history[-1].damage, 10)
        after = act(state, UseAttack(0, 1))
        event = next(e for e in since(after, state) if e["kind"] == "reflect_received")
        self.assertEqual((event["damage"], event["received_turn"]), (10, TURN - 1))
        self.assertEqual(active(after, 1).damage, 10)
        audited(self, after)

    def test_returned_to_hand_and_played_again_has_no_history(self):
        # 場をはなれたら記録もなくなる（記録は場のポケモンにある。出し直したポケモンは新しいポケモン）
        from kyuura_engine import PlayBasicToBench

        state = table(pidgeot(), opponent_active=mon(LICKITUNG, (G,)), opponent_bench=(mon(RATTATA, (G,)),))
        state = act(state, UseAttack(0, 0))                 # つばさでうつ。ベロリンガに受けた記録
        state = act(state, EndTurn(1))
        old = active(state, 1)
        self.assertGreater(old.history[-1].damage, 0)
        state = act(state, UseAttack(0, 1))                 # ハリケーン（HP 90 のベロリンガはきぜつしない）
        self.assertIn(old.card, state.players[1].hand)
        state = answer(state, (state.decision.options[0],))
        replayed = act(state, PlayBasicToBench(1, old.card))
        again = next(p for p in replayed.players[1].bench if p.card == old.card)
        self.assertNotEqual(again.pokemon_id, old.pokemon_id)
        self.assertEqual(again.history, ())
        audited(self, replayed)


class HurricaneTest(unittest.TestCase):
    """ピジョットの「ハリケーン」。"""

    def test_returns_opponent_and_all_attached_cards_to_hand(self):
        state = table(pidgeot(), opponent_active=mon(LICKITUNG, (G, G), trainers=[(PLUSPOWER, TURN - 1)]), opponent_bench=(RATTATA,))
        opponent = active(state, 1)
        cards = set(opponent.cards()) | set(opponent.energy) | {t.card for t in opponent.trainers}
        after = act(state, UseAttack(0, 1))
        self.assertIsNone(after.players[1].active)
        self.assertTrue(cards <= set(after.players[1].hand))
        event = next(e for e in since(after, state) if e["kind"] == "return_in_play_to_hand")
        self.assertEqual((event["player"], event["damage"]), (1, 30))
        self.assertEqual(after.decision.kind, "promote_active")
        self.assertEqual(after.decision.player, 1)
        audited(self, after)

    def test_knocked_out_is_not_returned(self):
        state = table(pidgeot(), opponent_active=mon(RATTATA, (G,)))
        after = act(state, UseAttack(0, 1))
        self.assertNotIn("return_in_play_to_hand", kinds(since(after, state)))
        self.assertIn("knock_out", kinds(since(after, state)))

    def test_no_bench_loses(self):
        state = table(pidgeot(), opponent_active=mon(LICKITUNG, (G, G)), opponent_bench=())
        after = act(state, UseAttack(0, 1))
        self.assertIsNotNone(after.result)
        self.assertEqual(after.result.winner, 0)

    def test_evolved_stack_returns(self):
        state = table(pidgeot(), opponent_active=mon(FEAROW, (G,), evolved_from=SPEAROW))
        opponent = active(state, 1)
        after = act(state, UseAttack(0, 1))
        self.assertTrue(set(opponent.cards()) <= set(after.players[1].hand))

    def test_transparency_evades_return(self):
        state = table(pidgeot(), opponent_active=mon(HAUNTER, (P,), evolved_from="PMCG3-029"))
        after = act(state, UseAttack(0, 1), H)
        self.assertIsNotNone(after.players[1].active)

    def test_guts_target_is_g37(self):
        # HP 以上になる相手がこんじょうを使えるなら、残ったポケモンをもどすかは G37（宣言の前）
        target = mon(GIOVANNIS_MACHAMP, (F,), evolved_from=[GIOVANNIS_MACHOP, GIOVANNIS_MACHOKE], damage=80, evolved_turn=TURN - 1)
        assert_stops(self, table(pidgeot(), opponent_active=target), UseAttack(0, 1), "UNRESOLVED_KO_PREVENTION_ATTACK_EFFECT")

    def test_counterattack_knockout_is_rd9(self):
        # はんげきでピジョットが HP 以上になる場合に相手をもどすかは RD9（v0.36 と同じ問い）
        target = mon(MACHAMP, (F,), evolved_from=[MACHOP, MACHOKE], evolved_turn=TURN - 1)
        assert_stops(self, table(pidgeot(damage=70), opponent_active=target), UseAttack(0, 1), "UNRESOLVED_RETURN_IN_PLAY_TO_DECK_KNOCKOUT")

    def test_scram_remaining_ten_is_sc1(self):
        # 残り HP 10 の［ずらかる］と、ワザの残りの要素（手札にもどす）の順番は SC1（v0.61 と同じ問い）
        target = mon(BROCKS_PRIMEAPE, (F,), evolved_from=BROCKS_MANKEY, damage=30)
        assert_stops(self, table(pidgeot(), opponent_active=target), UseAttack(0, 1), "UNRESOLVED_SCRAM_TIMING")


class SaveTest(unittest.TestCase):
    def test_format_20_and_older_formats(self):
        state = act(table(dugtrio()), UseAttack(0, 0))
        self.assertEqual(LATEST_FORMAT, 22)  # v0.67 で 22
        data = state_to_dict(state, format_version=20)
        self.assertEqual(data["players"][0]["active"]["history"][0]["kind"], "used")
        for version in range(1, 20):
            with self.assertRaises(ValueError):
                state_to_dict(state, format_version=version)
        restored = pickle.loads(pickle.dumps(state))
        self.assertEqual(state_to_dict(restored, format_version=20), data)
        audited(self, state)

    def test_preflight_modes_agree(self):
        state = act(act(table(dugtrio()), UseAttack(0, 0)), UseAttack(1, 0), T)
        results = [state_to_dict(act(state, UseAttack(0, 1), preflight=mode), format_version=20) for mode in ("derived", "derived_full", "legacy")]
        self.assertEqual(results[0], results[1])
        self.assertEqual(results[0], results[2])

    def test_observation_has_history(self):
        state = act(table(dugtrio()), UseAttack(0, 0))
        view = observe(state, 1)
        self.assertEqual(view["players"][0]["active"]["history"][0]["declared"], [BROCKS_DUGTRIO, 0])


class QuestionsTest(unittest.TestCase):
    def test_codes(self):
        expected = {"mirror_move_received_attack": "UNRESOLVED_MIRROR_MOVE_RECEIVED_ATTACK", "mirror_move_attack_conditions": "UNRESOLVED_MIRROR_MOVE_ATTACK_CONDITIONS",
                    "mirror_move_lasting_effect": "UNRESOLVED_MIRROR_MOVE_LASTING_EFFECT", "mirror_move_non_attack": "UNRESOLVED_MIRROR_MOVE_NON_ATTACK",
                    "earthdrill_copied_use": None, "mirror_move_unsupported_effect": "UNSUPPORTED_MIRROR_MOVE_EFFECT",
                    "mirror_move_unsupported_attack": "UNSUPPORTED_MIRROR_MOVE_ATTACK"}
        for key, code in expected.items():
            self.assertEqual(QUESTIONS[key].code, code)

    def test_doc_mentions_codes(self):
        text = DOC.read_text(encoding="utf-8")
        for code in ("MM1", "MM2", "OM1", "OM2", "ED1", "UNSUPPORTED_MIRROR_MOVE_EFFECT", "CONFIRMED_CORRECTIONS", "CC-PMCG2-041-P234"):
            self.assertIn(code, text)
        self.assertFalse(re.search(r"claude-[a-z]+-\d", text))


if __name__ == "__main__":
    unittest.main()

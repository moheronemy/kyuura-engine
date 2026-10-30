"""v0.114（docs/baby-rules-evolution-v0.114.md）: 写しの元・研究の基準の移行（73a1690 → e519b99）・ナツメのESPのやり直しのあとの入れ替えの結果・ベイビィポケモン 13 枚と
ベイビィの共通のルール（デッキ・対戦準備・ベンチ・ワザの前のルールのコイン・ベイビィからの進化・場の分類・カードの説明の範囲）。

2 章: 移行は連鎖（ecb2d69 → 7d3f4ca → 73a1690 → e519b99）で、v0.69・v0.97 の段の記録は書き換えない（v0.97 の段のあとは 73a1690 に固定した）。73a1690 → e519b99 の data/cards.json で
値が変わったのはベイビィ 13 枚だけで、写しの 1,250 枚の値は v0.113 と同じ。研究の基準の新しい条項・裁定・論点（UQ-NEO-TEXT-BABY-CATEGORIES）・事例を研究の対応表に結ぶ。
"""

from __future__ import annotations

import copy
import importlib.util
import json
import pathlib
import pickle
import re
import subprocess
import unittest
from collections import Counter
from unittest import mock

from kyuura_engine import (
    EndTurn,
    EvolvePokemon,
    PlayBasicToBench,
    PlayTrainer,
    ResolveDecision,
    UseAttack,
    UsePokemonPower,
)
from kyuura_engine import effects as E
from kyuura_engine.cards import EnergyType, read_extract
from kyuura_engine.coins import CoinSide
from kyuura_engine.conditions import PARALYSIS, POISON
from kyuura_engine.decisions import ESP_REDO, FORCED_SWITCH
from kyuura_engine.engine import check_invariants
from kyuura_engine.errors import IllegalActionError, UnsupportedError
from kyuura_engine.resolution import programs as P
from kyuura_engine.state import MARKER_COLOR
from scripts import check_card_sources as cs
from tests import helpers as H
from tests import test_variable_coins_search_attachments_v0_113 as V113
from tests.helpers import apply_kernel
from tests.release_catalog import cards_after
from tests.test_neo_trainer_components_v0_80 import audited, new_events
from tests.test_unown_family_powers_v0_96 import snap

ROOT = pathlib.Path(__file__).resolve().parent.parent
KYUURA = ROOT.parent / "kyuura"
DOC = ROOT / "docs" / "baby-rules-evolution-v0.114.md"
ECB, V069, V097, V0114 = ("ecb2d694e6280ec5dc9ddd2a8f709cea16a6b691", "7d3f4ca76c084774efb4ac6a1d3a943387e183c3", "73a169063463bbf7bcaa3137d70cbf9721d11534",
                          "e519b99e2adcc6c2cd0998569ae5ee1101de6e89")
V0113 = "2d113b5eeea0dbd4f7466e144f7a1345494405c0"  # 確認済みの完成版（固定した v0.113）
BABIES = ("neo1-022", "neo1-042", "neo1-044", "neo1-070", "neo2-033", "neo2-050", "neo3-031", "PF2-007", "NIP1X-002", "NIP2X-002", "PRN-012", "PRN-031", "PRN-037")
RULE_FILLED = BABIES[:6]  # ルール文を kyuura が画像で埋めた neo 第1〜2弾の 6 枚
HD, TL = CoinSide.HEADS, CoinSide.TAILS
LINKS_PATH = ROOT / "kyuura_engine" / "data" / "research_links.json"


def extract_module():
    spec = importlib.util.spec_from_file_location("extract_v0114", ROOT / "scripts" / "extract_kyuura_cards.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def needs_kyuura(test):
    return unittest.skipUnless((KYUURA / ".git").exists(), "../kyuura がない")(test)


def needs_history(test):
    return unittest.skipUnless((ROOT / ".git").exists(), "このリポジトリの git の履歴がない（取り出した木）")(test)


def kyuura_json(commit: str, path: str):
    return json.loads(subprocess.check_output(["git", "-C", str(KYUURA), "show", f"{commit}:{path}"]))


class MigrationTest(unittest.TestCase):
    """2 章: 写しの元・研究の基準を e519b99 に上げる移行（カードの登録・挙動は変えない）。"""

    def test_chain_and_fixed_old_steps(self):
        module = extract_module()
        # v0.121: 段 v0.121（e519b99 → 2fe0bc0）を加えた。v0.114 の段のあとは V0_114_KYUURA_COMMIT（e519b99）に固定した。今の写しの元は最後の段のあと
        self.assertEqual((module.V0_114_KYUURA_COMMIT, module.V0_97_KYUURA_COMMIT, module.V0_69_KYUURA_COMMIT, module.PREVIOUS_KYUURA_COMMIT), (V0114, V097, V069, ECB))
        self.assertEqual(module.migration_problems(), [])
        self.assertEqual([(s["id"], s["from"], s["to"], s["document"]) for s in module.KYUURA_MIGRATIONS[:3]],
                         [("v0.69", ECB, V069, "docs/equivalent-non-pack-cards-v0.69.md"), ("v0.97", V069, V097, "docs/unown-research-idfnj-v0.97.md"),
                          ("v0.114", V097, V0114, "docs/baby-rules-evolution-v0.114.md")])
        extract = read_extract()
        self.assertEqual([(s["id"], s["from"], s["to"]) for s in extract["source_migrations"]], [(s["id"], s["from"], s["to"]) for s in module.KYUURA_MIGRATIONS])
        self.assertEqual((extract["source"]["commit"], extract["previous_source"]["commit"]), (module.KYUURA_MIGRATIONS[-1]["to"], ECB))
        self.assertEqual(module.KYUURA_COMMIT, module.KYUURA_MIGRATIONS[-1]["to"])
        # v0.97 の段のあとを写しの元の定数にもどすと、写しの元を上げたときに過去の段のあとまで変わる（連鎖が切れて止まる）
        steps = module.KYUURA_MIGRATIONS
        try:
            module.KYUURA_MIGRATIONS = (steps[0], {**steps[1], "to": module.KYUURA_COMMIT}, *steps[2:])
            self.assertTrue(any("その前の段のあと" in p for p in module.migration_problems()))
        finally:
            module.KYUURA_MIGRATIONS = steps
        # 利用者が示した PR1-069 の名前の訂正は、今の写しの元でも同じ値（kyuura はまだ直していない）
        self.assertEqual([(c["card_id"], c["field"], c["before"], c["after"], c["source_commit"]) for c in extract["engine_user_corrections"]],
                         [("PR1-069", "name.ja", "？？？", "ミュウ", module.KYUURA_COMMIT)])

    def test_adoption_records_are_not_rewritten(self):
        sources = cs.load_sources()
        migrations = sources["data_migrations"][:3]  # v0.121: 4 段目を加えた（3 段目までは書き換えない）
        self.assertEqual([(m["from"], m["to"], m["on"], m["document"]) for m in migrations],
                         [(ECB, V069, "2026-10-19", "docs/equivalent-non-pack-cards-v0.69.md"), (V069, V097, "2026-10-25", "docs/unown-research-idfnj-v0.97.md"),
                          (V097, V0114, "2026-10-28", "docs/baby-rules-evolution-v0.114.md")])
        self.assertEqual(cs.data_migrations(sources, read_extract())[1], [])
        # 採用したときのデータのコミットは書き換えない（v0.113 までの 1,163 件。過去の原典照合のカードの記録 4 件はコミットなし）
        # （v0.115 から、v0.114 のあとに足したカードの記録も除く。v0.113 のあとの写しのカードで切る）
        later = cards_after(read_extract(), "0.113")
        self.assertTrue(set(BABIES) <= later)
        old = {card: record for card, record in sources["cards"].items() if card not in later}
        self.assertEqual(Counter(r.get("kyuura_commit") for r in old.values()), {ECB: 378, V069: 700, V097: 81, None: 4})

    @needs_history
    def test_extract_cards_are_the_v0_113_cards(self):
        """写しの 1,250 枚（v0.113 の写しのカード）の値は、写しの元を上げても変わらない（固定した v0.113 の写しと比べる）。"""
        before = json.loads(subprocess.check_output(["git", "-C", str(ROOT), "show", f"{V0113}:kyuura_engine/data/kyuura_cards.json"]))
        now = {card["id"]: card for card in read_extract()["cards"]}
        self.assertEqual(len(before["cards"]), 1250)
        for card in before["cards"]:
            self.assertEqual(now[card["id"]], card, card["id"])
        self.assertEqual((before["equivalent_targets"], before["reprint_targets"]), (read_extract()["equivalent_targets"], read_extract()["reprint_targets"]))

    def test_research_links(self):
        links = json.loads(LINKS_PATH.read_text(encoding="utf-8"))
        # v0.121: 研究の基準と写しの元を 2fe0bc0 に上げた（今の値は tests/test_research_links_v0_18e.py）。v0.114 で結んだ事例・採用の記録の id は残る
        self.assertEqual((links["research_commit"], links["card_data_commit"], links["engine_import_id"]), (read_extract()["source"]["commit"],) * 2 + ("ENGINE-46A3E2E",))
        cases = [c for c in links["kyuura_cases_without_engine_ruling"]["cases"]
                 if c["kyuura_issue"] == "UQ-NEO-TEXT-BABY-CATEGORIES" or (c["kyuura_issue"], c["card_id"]) == ("UQ-ATTACK-PRE-DAMAGE-COIN-ORDER", "neo1-042")]
        self.assertEqual(sorted((c["kyuura_issue"], c["card_id"], c["target"]) for c in cases),
                         [("UQ-ATTACK-PRE-DAMAGE-COIN-ORDER", "neo1-042", "card"), ("UQ-NEO-TEXT-BABY-CATEGORIES", "NIP1-021", "trainer"),
                          ("UQ-NEO-TEXT-BABY-CATEGORIES", "neo1-074", "trainer"), ("UQ-NEO-TEXT-BABY-CATEGORIES", "neo2-056", "trainer"),
                          ("UQ-NEO-TEXT-BABY-CATEGORIES", "neo3-049", "attack/0"), ("UQ-NEO-TEXT-BABY-CATEGORIES", "neo3-056", "trainer"),
                          ("UQ-NEO-TEXT-BABY-CATEGORIES", "neo4-038", "attack/0")])
        sources = cs.load_sources()["cards"]
        added = {"PMCG1-086": "CR-DEVOLUTION-SPRAY-EVOLVED-BABY", "PR1-005": "CR-NEUTRAL-SHIELD-EVOLVED-BABY", "PR1-012": "CR-NEUTRAL-SHIELD-EVOLVED-BABY",
                 "neo1-074": "UQ-NEO-TEXT-BABY-CATEGORIES", "neo2-056": "UQ-NEO-TEXT-BABY-CATEGORIES", "neo3-056": "UQ-NEO-TEXT-BABY-CATEGORIES",
                 "NIP1-021": "UQ-NEO-TEXT-BABY-CATEGORIES"}
        self.assertEqual({card: (record,) for card, record in added.items()}, H.V0_114_KYUURA_RECORDS_ADDED)
        for card, record in added.items():
            self.assertIn(record, sources[card]["kyuura_records"], card)
            self.assertLess(sources[card]["recorded_on"], "2026-10-28", card)  # 記録を読み直したのではなく、id の対応を直した（記録した日は変えない）

    @needs_kyuura
    def test_kyuura_difference_is_only_the_thirteen_babies(self):
        """73a1690 → e519b99 の data/cards.json の全 1,377 件: 値が変わったのはベイビィ 13 枚だけ（6 枚のルール文・13 枚の進化先・notes・corrections・data_gaps）。"""
        old, new = (kyuura_json(commit, "data/cards.json") for commit in (V097, V0114))
        self.assertEqual({k: v for k, v in old.items() if k != "cards"}, {k: v for k, v in new.items() if k != "cards"})
        self.assertEqual([c["id"] for c in old["cards"]], [c["id"] for c in new["cards"]])
        self.assertEqual(len(new["cards"]), 1377)
        before = {c["id"]: c for c in old["cards"]}
        changed = {c["id"]: {f for f in set(c) | set(before[c["id"]]) if c.get(f) != before[c["id"]].get(f)} for c in new["cards"] if c != before[c["id"]]}
        self.assertEqual(set(changed), set(BABIES))
        for card, fields in changed.items():
            self.assertEqual(fields, {"pokemon", "notes", "corrections"} | ({"data_gaps"} if card in RULE_FILLED else set()), card)
            pokemon = {c["id"]: c for c in new["cards"]}[card]["pokemon"]
            old_pokemon = before[card]["pokemon"]
            self.assertEqual({k for k in set(pokemon) | set(old_pokemon) if pokemon.get(k) != old_pokemon.get(k)},
                             {"evolves_to"} | ({"rules_text"} if card in RULE_FILLED else set()), card)
        # 写しの元を上げても、v0.69・v0.71 の選定の記録は 73a1690 の一覧から読む（e519b99 の一覧では、選んだカードはどれも registered）
        module = extract_module()
        self.assertEqual(module.TARGET_SELECTION_COMMIT, V097)
        self.assertEqual(module.current_target_status_problems(KYUURA), [])
        targets = {c["id"]: c for c in kyuura_json(V0114, "data/engine_targets.json")["cards"]}
        self.assertEqual({targets[card]["engine_status"] for card in module.POOL_V0_69 + module.POOL_V0_71}, {"registered"})


class EspSwitchContinuationTest(unittest.TestCase):
    """3 章: ナツメのESPのやり直しのあとに、前の要素の入れ替えの結果（``ForceSwitch`` の、入れ替えて出た控えの番号）を続きの情報 ``switched_results`` で運ぶ（エンジンの不具合の限定した
    修正。公式の裁定・kyuura の論点の解決ではない）。通常の登録・操作（手札のナツメのESPを ``PlayTrainer`` でナツメのフーディンにつけ、超の色マーカーをのせたわるいアリアドス（neo4-011）の
    「からめとる」を［サイコリンク］で使う。ESPの関数・解決の部品を差しかえない）。"""

    ARIADOS = "neo4-011"

    def board(self):
        provider = {"card": self.ARIADOS, "energy": [], "markers": [(MARKER_COLOR, EnergyType.PSYCHIC)], "evolved_from": ["neo1-004"]}
        state = V113.board(V113.mon(V113.ALAKAZAM, (H.GRASS, H.WATER)), bench=(provider,), opponent=V113.mon(H.HITMONCHAN), opponent_bench=(H.RATTATA, H.MACHOP),
                           hand=(V113.ESP_CARD,))
        played = apply_kernel(state, PlayTrainer(0, V113.uid(state, V113.ESP_CARD)))
        return V113.answer(played, (played.players[0].active.pokemon_id,))

    def switched(self):
        """「からめとる」を宣言した、入れ替える控えの決定の状態と、入れ替える控え（1 匹目）の番号。"""
        state = self.board()
        switch = V113.attack(state, 0, card=V113.provider_card(state, self.ARIADOS))
        self.assertEqual(switch.decision.kind, FORCED_SWITCH)
        return switch, switch.decision.options[0]

    def test_redo_and_keep_with_both_faces(self):
        """やり直さない「おもて」・「うら」、やり直して「うら」→「おもて」・「おもて」→「うら」。採った最後の面が「おもて」のときだけ、新しく出てきたポケモン（入れ替えた控え）がマヒ。
        入れ替え・マヒは 1 回だけ（入れ替え・コインを処理し直さない）。コインは最初の 1 枚と、やり直したときの 1 枚。"""
        switch, bench = self.switched()
        for redo, first, again, paralyzed in (((), HD, None, True), ((), TL, None, False), ((1,), TL, HD, True), ((1,), HD, TL, False)):
            with self.subTest(redo=redo, first=first, again=again):
                esp = V113.answer(switch, (bench,), first)
                self.assertEqual(esp.decision.kind, ESP_REDO)
                self.assertEqual(dict(esp.decision.context)["switched_results"], (("switch", bench),))
                audited(self, esp)
                done = V113.same_answers(self, esp, redo, *(() if again is None else (again,)))
                self.assertEqual((done.players[1].active.pokemon_id, done.players[1].active.conditions.paralyzed), (bench, paralyzed))
                events = new_events(switch, done)
                self.assertEqual([e["kind"] for e in events].count("forced_switch"), 1)
                self.assertEqual(len([e for e in events if e["kind"] == "special_condition" and e.get("condition") == PARALYSIS]), int(paralyzed))
                self.assertEqual(len([e for e in events if e["kind"] == "coin_flip" and e.get("source") == "attack"]), 1 + len(redo))

    def test_saved_across_the_switch_decision_and_invalid_answers(self):
        """入れ替え先の決定・ESPの決定をまたいで clone・deepcopy・pickle しても同じ続きになる。ESPの決定への不正な答え（決めるプレイヤーの違い・選べない値・重複）は、状態・乱数・ログ・
        決定を変えない。運んだ値を除いた v0.113 までの続きの形では、マヒを黙って省く（この修正が直したもの）。"""
        switch, bench = self.switched()
        expected = V113.answer(switch, (bench,), HD)
        for other in (switch.clone(), copy.deepcopy(switch), pickle.loads(pickle.dumps(switch))):
            self.assertEqual(snap(V113.answer(other, (bench,), HD)), snap(expected))
        before = snap(expected)
        for player, choices in ((1, ()), (0, (2,)), (0, (1, 1))):
            with self.assertRaises(IllegalActionError):
                apply_kernel(expected, ResolveDecision(player, expected.decision.id, choices))
        self.assertEqual(snap(expected), before)
        self.assertTrue(V113.answer(expected, ()).players[1].active.conditions.paralyzed)
        old_form = copy.deepcopy(expected)  # 決定は複製のあいだで共有されることがあるので、deepcopy した状態の決定だけを書きかえる
        object.__setattr__(old_form.decision, "context", tuple(item for item in old_form.decision.context if item[0] != "switched_results"))
        self.assertFalse(V113.answer(old_form, ()).players[1].active.conditions.paralyzed)

    def test_invariant_and_uncarried_results(self):
        """不変条件: 運んだ入れ替えの結果が、この番に入れ替えて出た相手の場のポケモンでなければ違反。続きの情報で運べない種類の結果を、ESPのやり直しのあとの要素が読む並び（今の写しには
        ない。登録の型の並びを一時的に置きかえて作る）は、黙って省かずに宣言の前に ``UNSUPPORTED_ESP_CONTINUATION`` で拒否する（状態を変えない）。"""
        switch, bench = self.switched()
        esp = V113.answer(switch, (bench,), HD)
        broken = copy.deepcopy(esp)
        other = esp.players[1].bench[0].pokemon_id
        object.__setattr__(broken.decision, "context", tuple(("switched_results", (("switch", other),)) if key == "switched_results" else (key, value)
                                                             for key, value in broken.decision.context))
        self.assertTrue(any("入れ替えの結果" in p for p in check_invariants(broken)))
        state = self.board()
        before = snap(state)
        # 前の要素の結果（真偽の値。続きの情報で運ばない種類）を、コインを投げる要素が名前で読む並び
        uncarried = {E.SwitchOpponentThenParalyzeNewOnHeads: lambda e: (P.OpponentStatusCheck("checked", (POISON,)),
                                                                         P.Status(PARALYSIS, local_coin=HD, after_switch="checked"))}
        with mock.patch.dict(P.BUILDERS, uncarried), self.assertRaises(UnsupportedError) as caught:
            V113.attack(state, 0, card=V113.provider_card(state, self.ARIADOS))
        self.assertEqual(caught.exception.code, "UNSUPPORTED_ESP_CONTINUATION")
        self.assertEqual(snap(state), before)


# ---------------------------------------------------------------- 4 章〜: ベイビィ 13 枚と共通の処理
# 盤面は ``build_test_state``（V113.board）で作った、1 か所の規定を確かめるためのもの（``new_game`` からの自然な対戦の結果ではない。対戦は tools/existing_effect_games.py の
# ``--batch v0.114``）。公式ガイドブックの読み直し・カードの画像の照合はしていない

PICHU, ELEKID, CLEFFA, TYROGUE, IGGLY, SMOOCHUM, MAGBY = "neo1-042", "neo1-044", "neo1-070", "neo2-033", "neo2-050", "neo3-031", "neo1-022"
PICHU_PF2, MAGBY_X, PICHU_X, CLEFFA_P, IGGLY_P, SMOOCHUM_P = "PF2-007", "NIP1X-002", "NIP2X-002", "PRN-012", "PRN-031", "PRN-037"
ELECTABUZZ, JIGGLYPUFF = "PMCG1-041", "PMCG2-035"
MEW_SHIELD = "PR1-005"  # ミュウ（［ニュートラルシールド］）
VULPIX_REVIVE = "GD5-002"  # カツラのロコン（［しぜんになおる］。たねポケモン・特殊能力あり）
KOFFING_POWER = "ES2-003"  # ドガース（［ぶんれつ］。たねポケモン・特殊能力あり）
MAGCARGO_HOT_PLATE = "neo4-023"  # わるいマグカルゴ（［ヒートプレート］）
SUPER_ROD, BREEDER_COUPLE, MASTER_BALL_NEO, MASTER_BALL_GD6, DEVOLUTION_HYPER = "neo1-074", "neo3-056", "NIP1-021", "GD6-023", "neo2-056"
REVIVE_PMCG1 = "PMCG1-078"  # 元気のかけら（ネオより前）
TURN = 7


def mon(card, energy=(), **extra):
    return {"card": card, "energy": list(energy), **extra}


def evolved_baby(card, baby, energy=(), **extra):
    """ベイビィポケモンの上にたねポケモンカードを重ねたポケモン（GR-2000-P310-BABY-EVOLUTION）。"""
    return {"card": card, "energy": list(energy), "evolved_from": [baby], **extra}


def coins_of(before, after, source):
    return [e["result"] for e in new_events(before, after, "coin_flip") if e.get("source") == source]


def rejected(test, state, command, code, error=UnsupportedError):
    before = snap(state)
    with test.assertRaises(error) as caught:
        apply_kernel(state, command)
    test.assertEqual(caught.exception.code, code)
    test.assertEqual(snap(state), before)  # 状態・乱数・ログは変わらない（コインを投げない）


class BabyRegistrationTest(unittest.TestCase):
    """4 章: 13 枚の分類（ベイビィの段階・進化先・ルール・ワザのないベイビィ）と登録・採用の記録。"""

    def test_thirteen_babies_are_playable_with_explicit_fields(self):
        from kyuura_engine.cards import load_card_pool

        pool = load_card_pool()
        evolves = {MAGBY: ("ブーバー",), PICHU: ("ピカチュウ",), ELEKID: ("エレブー",), CLEFFA: ("ピッピ",), TYROGUE: ("エビワラー", "サワムラー", "カポエラー"),
                   IGGLY: ("プリン",), SMOOCHUM: ("ルージュラ",), PICHU_PF2: ("ピカチュウ",), MAGBY_X: ("ブーバー",), PICHU_X: ("ピカチュウ",), CLEFFA_P: ("ピッピ",),
                   IGGLY_P: ("プリン",), SMOOCHUM_P: ("ルージュラ",)}
        for card in BABIES:
            with self.subTest(card=card):
                d = pool.get(card)
                self.assertTrue(pool.is_playable(card))
                self.assertEqual((d.stage, d.hp, d.weakness, d.resistance, d.retreat_cost, d.baby_rule), ("baby", 30, None, None, 0, True))
                self.assertTrue(d.is_baby_pokemon and d.is_baby_or_basic_pokemon and not d.is_basic_pokemon and not d.is_evolution_pokemon)
                self.assertEqual(d.evolves_to, evolves[card])
        self.assertEqual(pool.get(SMOOCHUM_P).pokemon_type, EnergyType.WATER)  # PRN-037 は水（写しの値）
        self.assertEqual([pool.get(card).attacks for card in (ELEKID, IGGLY)], [(), ()])  # CR-BABY-WITHOUT-ATTACKS（ワザのないベイビィ）
        self.assertFalse(any(getattr(pool.get(card).powers[0], "kind", None) is None for card in (ELEKID, IGGLY)))
        self.assertNotIn("PRN-030", pool.playable_ids)  # カポエラー（PRN-030）は加えていない

    def test_registrations_and_records(self):
        expected = {
            (MAGBY, 0): E.DamageThenFieldPowerSuppressionUntilOwnNextTurn, (PICHU, 0): E.PowerHoldersSpreadDamage, (CLEFFA, 0): E.ShuffleHandIntoDeckThenDraw,
            (TYROGUE, 0): E.FailOnTailsDamage, (SMOOCHUM, 0): E.CoinReturnOpponentSpecialEnergyToDeck, (PICHU_PF2, 0): E.PutBabyFromDeckOntoBenchOrFail,
            (MAGBY_X, 0): E.DamageOnly, (PICHU_X, 0): E.DamageOnly, (CLEFFA_P, 0): E.DrawCardsAttack, (IGGLY_P, 0): E.PutToSleep,
            (SMOOCHUM_P, 0): E.PlaceCountersOnChosenOpponentPokemon,
        }
        for (card, index), kind in expected.items():
            with self.subTest(card=card):
                self.assertIs(type(E.DEFAULT_EFFECTS.attack_entry(card, index).effect), kind)
        self.assertIs(type(E.DEFAULT_EFFECTS.power_entry(ELEKID, 0).effect), E.CoinDamageOpponentActiveThenEndTurn)
        self.assertIs(type(E.DEFAULT_EFFECTS.power_entry(IGGLY, 0).effect), E.StopOpponentBenchPowersThisTurn)
        sources = cs.load_sources()["cards"]
        links = json.loads(LINKS_PATH.read_text(encoding="utf-8"))
        rule = ["CR-BABY-RULE-COIN", "CR-BABY-RULE-COIN-STEP", "CR-BABY-RULE-NOT-POWER"]
        extra = {PICHU: ["CR-NEUTRAL-SHIELD-EVOLVED-BABY", "UQ-ATTACK-PRE-DAMAGE-COIN-ORDER"], ELEKID: ["CR-BABY-WITHOUT-ATTACKS"], IGGLY: ["CR-BABY-WITHOUT-ATTACKS"]}
        for card in BABIES:
            with self.subTest(card=card):
                record = sources[card]
                self.assertEqual((record["basis"], record["status"], record["kyuura_commit"], record["external_checks"], record["issues"], record["recorded_on"]),
                                 ("kyuura_data", "adopted", V0114, [], [], "2026-10-28"))
                self.assertEqual(record["kyuura_records"], sorted(rule + extra.get(card, [])))
                self.assertIn("エンジンは画像を見ていない", record["notes"])
        self.assertIn("修正前の版", sources[PICHU]["notes"])  # neo1-042 の画像は修正前の版（採用の根拠と画像の確認を分ける）
        targets = {f"{card}/attack/0" for card in BABIES if card not in (ELEKID, IGGLY, MAGBY_X, PICHU_X)} | {f"{ELEKID}/power/0", f"{IGGLY}/power/0"}
        self.assertTrue(targets <= set(links["latest_descriptions"]["adopted_printed_text"]))
        for code, rid in (("UNRESOLVED_BABY_RULE_COIN_ORDER", "BQ1"), ("UNRESOLVED_NEO_TEXT_BASIC_BABY", "NB1"), ("UNRESOLVED_NEO_TEXT_EVOLUTION_CARD_BABY", "NB2"),
                          ("UNRESOLVED_TRANSFORM_BABY", "BX1"), ("UNRESOLVED_HOT_PLATE_BABY_EVOLUTION", "HP2"), ("UNRESOLVED_STOPPED_POWER_HOLDER", "HV1")):
            self.assertEqual(links["stop_codes"][code]["engine_rulings"], [{"version": "v0.114", "document": "docs/baby-rules-evolution-v0.114.md", "ruling_id": rid}])
        self.assertNotIn("neo_text_baby_categories", links["codeless_questions"])  # NB0（移行の時点のコードのない問い）は NB1・NB2 にした
        H.assert_stop_code_counts_since(self, links, 243, 244)

    def test_text_eras_are_registered_for_every_reader(self):
        """説明の「たねポケモン」「進化カード」の範囲を版で読む登録（``TEXT_ERAS``）は、版を読む型の登録のカードとちょうど同じで、版はカードのデータの商品と合う（ネオより前の
        商品は ``TEXT_PRE_NEO``、neo の商品は ``TEXT_NEO``。解決の部品はカードの id・接頭辞で版を決めない。これはテストの照らし）。"""
        import inspect

        from kyuura_engine.cards import read_extract

        def reads(cls) -> bool:
            return "text_era(" in "".join(inspect.getsource(k) for k in cls.__mro__ if k.__module__ in (E.__name__, P.__name__))

        def program(effect):
            builder = P.BUILDERS.get(type(effect))
            return builder(effect) if builder is not None else ()

        registry = E.DEFAULT_EFFECTS
        uses = set()
        for key, entry in (*registry._attacks.items(), *registry._powers.items(), *registry._trainers.items()):
            card = key if isinstance(key, str) else key.card_id
            # 要素（resolution/programs.py）が版を読む並び（タイプで山札からベンチに出す・トラッシュからベンチに出す・しんかのうた）は、その要素の項目が版を読む場面のときだけ。
            # v0.117: 相手のワザを選んで使えなくする要素（``OpponentAttackLock``）が版を読むのは、相手が「たねポケモン」かを確かめるいかく（``basic_only``）だけ（ドわすれは読まない）
            elements = [element for element in program(entry.effect) if reads(type(element))
                        and not (isinstance(element, P.BenchFromDeck) and element.pokemon_type is None)
                        and not (isinstance(element, P.OpponentAttackLock) and not element.basic_only)]
            if reads(type(entry.effect)) or elements:
                uses.add(card)
        self.assertEqual(set(E.TEXT_ERAS), uses)
        neo_sets = {"neo1", "neo2", "neo3", "neo4", "NIP1", "NIP2", "NIP1X", "NIP2X", "PF1", "PF2", "PF3", "PRN"}
        jp_set = {c["id"]: c["jp_set"] for c in read_extract()["cards"]}
        for card, era in E.TEXT_ERAS.items():
            with self.subTest(card=card):
                self.assertEqual(era, E.TEXT_NEO if jp_set[card] in neo_sets else E.TEXT_PRE_NEO)
        with self.assertRaises(RuntimeError):
            E.text_era("PMCG1-001")  # 登録のないカード（版を読まない）は、エンジンの不具合として止める


class DeckSetupTest(unittest.TestCase):
    """5.1 節: デッキ・対戦準備・ベンチ（GR-2000-P308-BABY-SETUP・GR-2000-P309-BABY-BENCH）。"""

    def test_deck_needs_a_baby_or_basic_and_four_copies_by_name(self):
        from kyuura_engine.deck import deck_problems

        babies_only = [PICHU] * 2 + [PICHU_PF2] * 2 + [CLEFFA] * 2 + [H.LIGHTNING] * 54
        self.assertEqual(deck_problems(babies_only), [])
        no_pokemon = [H.LIGHTNING] * 60
        self.assertTrue(any(p.startswith("NO_BASIC_POKEMON") for p in deck_problems(no_pokemon)))
        five = [PICHU] * 2 + [PICHU_PF2] * 2 + [PICHU_X] + [H.LIGHTNING] * 55  # 同じ名前「ピチュー」は版によらず 4 枚まで
        self.assertTrue(any("ピチュー" in p and p.startswith("TOO_MANY_COPIES") for p in deck_problems(five)))

    def test_mulligan_only_without_baby_or_basic(self):
        from kyuura_engine import new_game

        deck = [PICHU] * 2 + [PICHU_PF2] * 2 + [CLEFFA] * 2 + [CLEFFA_P] * 2 + [H.LIGHTNING] * 52
        seen_mulligan = False
        for seed in range(12):
            state = new_game(deck, deck, seed)
            for e in state.log:
                if e["kind"] == "mulligan":
                    seen_mulligan = True
                    self.assertFalse(any(state.card_def(uid).is_baby_or_basic_pokemon for uid in e["revealed_hand"]))
            for p in state.players:
                self.assertTrue(any(state.card_def(uid).is_baby_or_basic_pokemon for uid in p.hand))
        self.assertTrue(seen_mulligan)

    def test_setup_and_bench_from_hand(self):
        from kyuura_engine import new_game
        from kyuura_engine.commands import PlaceStartingPokemon

        deck = [PICHU] * 4 + [CLEFFA] * 4 + [H.LIGHTNING] * 52
        state = next(s for s in (new_game(deck, deck, seed) for seed in range(20)) if s.phase.value == "setup_placement")
        player = 0 if not state.players[0].placed_starting_pokemon else 1
        babies = [u for u in state.players[player].hand if state.card_def(u).is_baby_pokemon]
        placed = apply_kernel(state, PlaceStartingPokemon(player, babies[0], tuple(babies[1:6])))
        self.assertEqual(placed.cards[placed.players[player].active.card].card_id, PICHU)
        board = V113.board(mon(H.RATTATA, (H.WATER,)), bench=(), hand=(PICHU, ELEKID))
        benched = apply_kernel(board, PlayBasicToBench(0, V113.uid(board, PICHU)))
        self.assertEqual([benched.cards[p.card].card_id for p in benched.players[0].bench], [PICHU])
        audited(self, benched)


class BabyRuleTest(unittest.TestCase):
    """5.2 節: ベイビィポケモンのルール（GR-2000-P314-BABY-RULE・CR-BABY-RULE-COIN・CR-BABY-RULE-COIN-STEP・CR-BABY-RULE-NOT-POWER）。"""

    def test_tails_fails_and_ends_the_turn_heads_continues(self):
        state = V113.board(mon(H.RATTATA, (H.WATER,)), opponent=mon(PICHU))
        tails = V113.attack(state, 0, TL)
        self.assertEqual(coins_of(state, tails, "baby_rule"), ["tails"])
        failed = [e for e in new_events(state, tails, "attack_failed")]
        self.assertEqual([e["reason"] for e in failed], ["baby_rule"])
        self.assertEqual(new_events(state, tails, "damage"), [])
        self.assertEqual((tails.current_player, tails.turn_number), (1, TURN + 1))  # ワザを使ったことになり、番は終わる
        heads = V113.attack(state, 0, HD)
        self.assertEqual(coins_of(state, heads, "baby_rule"), ["heads"])
        self.assertEqual([e["amount"] for e in new_events(state, heads, "damage")], [20])
        coin = new_events(state, heads, "baby_rule_coin")[0]
        self.assertEqual((coin["player"], coin["baby_pokemon_id"], coin["heads"]), (0, state.players[1].active.pokemon_id, True))
        audited(self, tails)
        audited(self, heads)

    def test_no_coin_for_bench_babies_evolved_babies_and_rejected_attacks(self):
        bench_baby = V113.board(mon(H.RATTATA, (H.WATER,)), opponent=mon(H.RATTATA), opponent_bench=(PICHU,))
        self.assertEqual(coins_of(bench_baby, V113.attack(bench_baby, 0), "baby_rule"), [])
        evolved = V113.board(mon(H.RATTATA, (H.WATER,)), opponent=evolved_baby(H.PIKACHU, PICHU))
        self.assertEqual(coins_of(evolved, V113.attack(evolved, 0), "baby_rule"), [])
        self.assertTrue(E.is_evolution_in_play(evolved, evolved.players[1].active))  # GR-2000-P315-EVOLVED-BABY
        unpaid = V113.board(mon(H.RATTATA), opponent=mon(PICHU))
        rejected(self, unpaid, UseAttack(0, 0), "INSUFFICIENT_ENERGY", IllegalActionError)  # 宣言の前の拒否ではコインを投げない

    def test_not_a_power_and_not_redone_by_esp(self):
        """特殊能力を止める効果（かがくへんかガス）でも止まらない。ナツメのESPのやり直しは、ワザの説明のコインだけ（ルールのコインを投げ直さない）。"""
        gas = V113.board(mon(H.RATTATA, (H.WATER,)), opponent=mon(PICHU), opponent_bench=(mon(H.MUK, evolved_from=["PMCG3-003"]),))
        self.assertEqual(len(coins_of(gas, V113.attack(gas, 0, HD), "baby_rule")), 1)
        provider = {"card": "neo4-011", "energy": [], "markers": [(MARKER_COLOR, EnergyType.PSYCHIC)], "evolved_from": ["neo1-004"]}
        state = V113.board(V113.mon(V113.ALAKAZAM, (H.GRASS, H.WATER)), bench=(provider,), opponent=mon(PICHU), opponent_bench=(H.RATTATA, H.MACHOP),
                           hand=(V113.ESP_CARD,))
        played = apply_kernel(state, PlayTrainer(0, V113.uid(state, V113.ESP_CARD)))
        armed = V113.answer(played, (played.players[0].active.pokemon_id,))
        switch = V113.attack(armed, 0, HD, card=V113.provider_card(armed, "neo4-011"))  # ルールのコイン「おもて」→ 入れ替える控えの決定
        self.assertEqual(switch.decision.kind, FORCED_SWITCH)
        esp = V113.answer(switch, (switch.decision.options[0],), TL)
        self.assertEqual(esp.decision.kind, ESP_REDO)  # やり直すかを聞くのは、ワザの説明のコイン（マヒの要素）だけ
        redone = V113.answer(esp, (1,), HD)
        self.assertEqual(coins_of(armed, redone, "baby_rule"), ["heads"])
        self.assertEqual(coins_of(armed, redone, "attack"), ["tails", "heads"])

    def test_order_questions_stop_before_the_coin(self):
        confused = V113.board(mon(H.RATTATA, (H.WATER,), confusion=True), opponent=mon(PICHU))
        rejected(self, confused, UseAttack(0, 0), "UNRESOLVED_BABY_RULE_COIN_ORDER")  # BQ1（こんらんのコインとの順番）
        ditto = V113.board(mon(H.RATTATA, (H.WATER,)), bench=(PICHU,), opponent=mon(H.DITTO))
        self.assertIsNone(E.transform_baby_question(ditto, ditto.players[1].active))  # メタモンは相手のバトル場（ラッタ）を写す
        copied = V113.board(mon(PICHU, (H.WATER,)), opponent=mon(H.DITTO))
        rejected(self, copied, UseAttack(0, 0), "UNRESOLVED_TRANSFORM_BABY")  # BX1（ベイビィの姿のメタモン）
        # 既存の HC1: 「はがしてすてる」がワザを使うための条件か効果かで、「うら」でトラッシュするかが変わる（ミュウツーのバリアー）。相手がベイビィでなければ止めない
        barrier = V113.board(mon(H.MEWTWO, (H.PSYCHIC, H.PSYCHIC)), opponent=mon(PICHU))
        rejected(self, barrier, UseAttack(0, 1), "UNRESOLVED_DISCARD_ENERGY_TIMING")
        plain = V113.board(mon(H.MEWTWO, (H.PSYCHIC, H.PSYCHIC)), opponent=mon(H.RATTATA))
        chosen = V113.attack(plain, 1)  # 相手がベイビィでなければ止めず、トラッシュするカードの決定に進む
        self.assertEqual(chosen.decision.kind, "discard_energy")
        self.assertEqual(len(V113.answer(chosen, chosen.decision.options[:1]).players[0].active.energy), 1)

    def test_vermilion_and_ninja_trick_stop_before_the_coin(self):
        """クチバシシティジムのコインとの順番（既存の VM1）・変わり身の術の入れ替えとの順番（既存の NT1。控えのベイビィがバトル場に出うる）も、コインの前に止める。"""
        gym = V113.board(mon("PMCG5-056", (H.FIRE, H.FIRE)), hand=(H.VERMILION_CITY_GYM,), opponent=mon(PICHU))
        placed = apply_kernel(gym, PlayTrainer(0, V113.uid(gym, H.VERMILION_CITY_GYM)))
        rejected(self, placed, UseAttack(0, 1, stadium_coin=True), "UNRESOLVED_VERMILION_GYM_ATTACK_ORDER")
        trick = V113.board(mon(H.RATTATA, (H.WATER,)), opponent=mon(H.KOGAS_KOFFING, trainers=[(H.KOGAS_NINJA_TRICK, None)]), opponent_bench=(PICHU,))
        rejected(self, trick, UseAttack(0, 0), "UNRESOLVED_NINJA_TRICK_ATTACK_COIN_ORDER")

    def test_saved_across_a_decision_without_reflipping(self):
        state = V113.board(mon(SMOOCHUM_P, (H.WATER,)), opponent=mon(PICHU), opponent_bench=(H.RATTATA,))
        chosen = V113.attack(state, 0, HD)
        self.assertEqual(chosen.decision.kind, "select_pokemon")
        done = V113.same_answers(self, chosen, (chosen.decision.options[-1],))
        self.assertEqual(len(coins_of(state, done, "baby_rule")), 1)
        from kyuura_engine.observation import visible_log

        for viewer in (0, 1, None):
            self.assertIn("baby_rule_coin", [e["kind"] for e in visible_log(done, viewer)])


class BabyEvolutionTest(unittest.TestCase):
    """5.3 節: ベイビィからの進化（GR-2000-P310-BABY-EVOLUTION・GR-2000-P315-EVOLVED-BABY・GR-2000-P313-POKEMON-COMPOSITION）と、場の分類。"""

    def test_evolve_from_hand_and_restrictions(self):
        state = V113.board(mon(PICHU, played_turn=1), hand=(H.PIKACHU, ELECTABUZZ, H.RAICHU))
        pid = state.players[0].active.pokemon_id
        evolved = apply_kernel(state, EvolvePokemon(0, V113.uid(state, H.PIKACHU), pid))
        active = evolved.players[0].active
        self.assertEqual(([evolved.cards[u].card_id for u in active.evolution_stack], evolved.cards[active.card].card_id), ([PICHU], H.PIKACHU))
        self.assertTrue(E.is_evolution_in_play(evolved, active) and not E.is_baby_in_play(evolved, active))
        audited(self, evolved)
        rejected(self, state, EvolvePokemon(0, V113.uid(state, ELECTABUZZ), pid), "EVOLUTION_NAME_MISMATCH", IllegalActionError)
        rejected(self, state, EvolvePokemon(0, V113.uid(state, H.RAICHU), pid), "EVOLUTION_NAME_MISMATCH", IllegalActionError)  # ライチュウはピカチュウから
        fresh = V113.board(mon(PICHU, played_turn=TURN), hand=(H.PIKACHU,))
        rejected(self, fresh, EvolvePokemon(0, V113.uid(fresh, H.PIKACHU), fresh.players[0].active.pokemon_id), "PLAYED_THIS_TURN", IllegalActionError)
        later = V113.board(evolved_baby(H.PIKACHU, PICHU, evolved_turn=TURN - 2), hand=(H.RAICHU,))
        raichu = apply_kernel(later, EvolvePokemon(0, V113.uid(later, H.RAICHU), later.players[0].active.pokemon_id))
        self.assertEqual(len(raichu.players[0].active.evolution_stack), 2)  # ベイビィ → たね → 1 進化
        audited(self, raichu)
        other = V113.board(mon(H.RATTATA, played_turn=1), hand=(H.PIKACHU,))
        rejected(self, other, EvolvePokemon(0, V113.uid(other, H.PIKACHU), other.players[0].active.pokemon_id), "NOT_EVOLUTION_CARD", IllegalActionError)

    def test_evolved_baby_is_an_evolution_pokemon_for_neutral_shield(self):
        """CR-NEUTRAL-SHIELD-EVOLVED-BABY: ベイビィから進化したたねポケモンのワザは、ミュウ（PR1-005）が受けない。進化していないベイビィのワザは受ける。"""
        evolved = V113.board(evolved_baby(H.PIKACHU, PICHU, (H.LIGHTNING,)), opponent=mon(MEW_SHIELD))
        after = V113.attack(evolved, 0)
        self.assertEqual(new_events(evolved, after, "damage"), [])
        baby = V113.board(mon(PICHU_X, (H.LIGHTNING,)), opponent=mon(MEW_SHIELD))
        self.assertEqual([e["amount"] for e in new_events(baby, V113.attack(baby, 0), "damage")], [10])

    def test_devolution_spray_peels_the_basic(self):
        """CR-DEVOLUTION-SPRAY-EVOLVED-BABY: 退化スプレーで、ベイビィの上のたねポケモンカードをはがして捨てられる（たねポケモンカードにもどる）。"""
        state = V113.board(evolved_baby(H.PIKACHU, PICHU, damage=10), hand=(H.DEVOLUTION_SPRAY,))
        played = apply_kernel(state, PlayTrainer(0, V113.uid(state, H.DEVOLUTION_SPRAY)))
        while played.decision is not None:
            played = V113.answer(played, played.decision.options[-1:])
        self.assertEqual(played.cards[played.players[0].active.card].card_id, PICHU)
        self.assertTrue(any(played.cards[u].card_id == H.PIKACHU for u in played.players[0].discard))
        audited(self, played)

    def test_hot_plate_evolution_stops(self):
        state = V113.board(mon(PICHU, played_turn=1), hand=(H.PIKACHU,), opponent=mon(MAGCARGO_HOT_PLATE, evolved_from=["neo3-008"]))
        rejected(self, state, EvolvePokemon(0, V113.uid(state, H.PIKACHU), state.players[0].active.pokemon_id), "UNRESOLVED_HOT_PLATE_BABY_EVOLUTION")


class TextEraTest(unittest.TestCase):
    """5.4 節: カードの説明の「たねポケモン」「進化カード」とベイビィ（GR-2000-P325-PRE-NEO-BABY・UQ-NEO-TEXT-BABY-CATEGORIES）。"""

    def test_queries(self):
        from kyuura_engine.cards import load_card_pool

        pool = load_card_pool()
        baby, basic = pool.get(PICHU), pool.get(H.PIKACHU)
        self.assertEqual((E.card_is_basic_in_text(baby, E.TEXT_PRE_NEO), E.card_is_basic_in_text(baby, E.TEXT_NEO)), (True, None))
        self.assertEqual((E.card_is_basic_in_text(basic, E.TEXT_NEO), E.card_is_evolution_in_text(basic, E.TEXT_PRE_NEO)), (True, False))
        self.assertEqual((E.deck_baby_evolution_card_in_text(E.TEXT_PRE_NEO), E.deck_baby_evolution_card_in_text(E.TEXT_NEO)), (False, None))
        state = V113.board(evolved_baby(H.PIKACHU, PICHU), bench=(PICHU,))
        evolved, bench = state.players[0].active, state.players[0].bench[0]
        self.assertEqual((E.field_is_basic_in_text(state, bench, E.TEXT_PRE_NEO), E.field_is_basic_in_text(state, bench, E.TEXT_NEO)), (True, None))
        self.assertEqual((E.field_is_basic_in_text(state, evolved, E.TEXT_PRE_NEO), E.top_is_evolution_card_in_text(state, evolved, E.TEXT_PRE_NEO),
                          E.top_is_evolution_card_in_text(state, evolved, E.TEXT_NEO)), (False, True, None))

    def test_neo_trainers_stop_on_baby_choices(self):
        """ポケモン育て屋夫婦（neo）の場の「たねポケモン」: ベイビィ・ベイビィから進化したポケモンだけなら使う前に NB1。退化スプレーHYPER（neo）の「進化カード」: ベイビィの上の
        たねポケモンカードだけなら使う前に NB2（選べるが選ぶと止める候補だけ）。"""
        breeder = V113.board(mon(PICHU), bench=(evolved_baby(H.PIKACHU, PICHU_X),), hand=(BREEDER_COUPLE,))
        rejected(self, breeder, PlayTrainer(0, V113.uid(breeder, BREEDER_COUPLE)), "UNRESOLVED_NEO_TEXT_BASIC_BABY")
        hyper = V113.board(evolved_baby(H.PIKACHU, PICHU), hand=(DEVOLUTION_HYPER,))
        rejected(self, hyper, PlayTrainer(0, V113.uid(hyper, DEVOLUTION_HYPER)), "UNRESOLVED_NEO_TEXT_EVOLUTION_CARD_BABY")

    def test_pre_neo_revive_benches_a_baby_and_super_rod_stops(self):
        revive = V113.board(mon(H.RATTATA), hand=(REVIVE_PMCG1,), discard=(PICHU,))
        played = apply_kernel(revive, PlayTrainer(0, V113.uid(revive, REVIVE_PMCG1)))
        while played.decision is not None:
            played = V113.answer(played, played.decision.options[:1])
        self.assertIn(PICHU, [played.cards[p.card].card_id for p in played.players[0].bench])
        rod = V113.board(mon(H.RATTATA), hand=(SUPER_ROD,), discard=(PICHU, H.PIKACHU, H.RAICHU))
        tails = apply_kernel(H.with_coin_results(rod, TL), PlayTrainer(0, V113.uid(rod, SUPER_ROD)))
        self.assertEqual(tails.decision.context_value("unresolved_code"), "UNRESOLVED_NEO_TEXT_BASIC_BABY")
        self.assertIn(V113.uid(rod, PICHU, zone="discard"), tails.decision.context_value("unresolved_choices"))


class BabyAttackTest(unittest.TestCase):
    """6 章: 11 のワザ。"""

    def test_smokescreen_lasts_until_the_end_of_the_next_own_turn(self):
        state = V113.board(mon(MAGBY, (H.FIRE,)))
        after = V113.attack(state, 0)
        record = [r for r in after.trainer_effects if r.kind == E.ATTACK_FIELD_POWER_SUPPRESSION]
        self.assertEqual([(r.created_turn, r.expires_turn) for r in record], [(TURN, TURN + 2)])
        self.assertEqual([e["amount"] for e in new_events(state, after, "damage")], [10])
        audited(self, after)

    def test_pachipachi_hits_power_holders_on_both_sides_and_stops_on_hv1(self):
        state = V113.board(mon(PICHU, (H.LIGHTNING,)), bench=(mon(VULPIX_REVIVE), H.RATTATA), opponent=mon(KOFFING_POWER), opponent_bench=(H.RATTATA, mon(VULPIX_REVIVE)))
        after = V113.attack(state, 0)
        hit = sorted((e.get("target", "opponent_active"), e["amount"]) for e in new_events(state, after, "damage"))
        self.assertEqual(hit, [("opponent_active", 20), ("opponent_bench", 20), ("self_bench", 20)])
        audited(self, after)
        gas = V113.board(mon(PICHU, (H.LIGHTNING,)), opponent=mon(H.RATTATA), opponent_bench=(mon(H.MUK, evolved_from=["PMCG3-003"]), mon(VULPIX_REVIVE)))
        rejected(self, gas, UseAttack(0, 0), "UNRESOLVED_STOPPED_POWER_HOLDER")  # かがくへんかガスで［しぜんになおる］の消えたロコン（HV1）

    def test_draws_sleep_and_damage_only(self):
        cleffa = V113.board(mon(CLEFFA, (H.WATER,)), hand=(H.WATER, H.WATER), deck=[H.FIRE] * 10)
        after = V113.attack(cleffa, 0)
        self.assertEqual(len(after.players[0].hand), 7)
        two = V113.board(mon(CLEFFA_P, (H.WATER,)))
        self.assertEqual(len(V113.attack(two, 0).players[0].hand), 2)
        sleep = V113.attack(V113.board(mon(IGGLY_P, (H.WATER,))), 0, TL)  # 番の終わりのポケモンチェックのねむりのコインは「うら」
        self.assertTrue(sleep.players[1].active.conditions.asleep)
        for card in (MAGBY_X, PICHU_X):
            board = V113.board(mon(card, (H.WATER,)))
            self.assertEqual([e["amount"] for e in new_events(board, V113.attack(board, 0), "damage")], [10])
        punch = V113.board(mon(TYROGUE, (H.WATER,)), opponent=mon(H.MACHOP))
        self.assertEqual([e["reason"] for e in new_events(punch, V113.attack(punch, 0, TL), "attack_failed")], ["coin"])

    def test_psychic_kiss(self):
        none = V113.board(mon(SMOOCHUM, (H.PSYCHIC,)))
        self.assertEqual(coins_of(none, V113.attack(none, 0), "attack"), [])  # 選べる特殊エネルギーカードがなければコインを投げない
        state = V113.board(mon(SMOOCHUM, (H.PSYCHIC,)), opponent=mon(H.RATTATA, (H.DOUBLE_COLORLESS_ENERGY, H.WATER)))
        tails = V113.attack(state, 0, TL)
        self.assertEqual(tails.players[1].active.energy, state.players[1].active.energy)
        heads = V113.attack(state, 0, HD)
        self.assertEqual(heads.decision.kind, "select_attached_special_energy")
        dce = state.players[1].active.energy[0]
        self.assertEqual(heads.decision.options, (dce,))
        done = V113.same_answers(self, heads, (dce,))
        self.assertNotIn(dce, done.players[1].active.energy)
        self.assertIn(dce, done.players[1].deck)
        self.assertEqual([e["kind"] for e in new_events(heads, done, "attached_energy_to_deck", "shuffle")], ["attached_energy_to_deck", "shuffle"])
        audited(self, done)
        protected = V113.board(mon(SMOOCHUM, (H.PSYCHIC,)), opponent=mon(H.RATTATA, (H.DOUBLE_COLORLESS_ENERGY,), trainers=[(H.BROCKS_PROTECTION, None)]))
        self.assertEqual(coins_of(protected, V113.attack(protected, 0), "attack"), [])  # タケシの保護のポケモンのカードは選べない

    def test_play_together_babies_only_and_full_bench_fails(self):
        state = V113.board(mon(PICHU_PF2, (H.LIGHTNING,)), bench=(), deck=[H.PIKACHU, CLEFFA, H.WATER, PICHU])
        chosen = V113.attack(state, 0)
        self.assertEqual(sorted(state.cards[u].card_id for u in chosen.decision.options), sorted([CLEFFA, PICHU]))
        done = V113.answer(chosen, chosen.decision.options[:1])
        self.assertEqual(len(done.players[0].bench), 1)
        audited(self, done)
        full = V113.board(mon(PICHU_PF2, (H.LIGHTNING,)), bench=(H.RATTATA,) * 5, deck=[PICHU])
        after = V113.attack(full, 0)
        self.assertEqual([e["reason"] for e in new_events(full, after, "attack_failed")], ["bench_full"])
        self.assertEqual(new_events(full, after, "shuffle"), [])

    def test_blow_kiss_places_a_counter_not_damage(self):
        state = V113.board(mon(SMOOCHUM_P, (H.WATER,)), opponent=mon(H.RATTATA), opponent_bench=(H.MACHOP,))
        chosen = V113.attack(state, 0)
        bench = state.players[1].bench[0].pokemon_id
        done = V113.answer(chosen, (bench,))
        self.assertEqual((done.players[1].bench[0].damage, new_events(chosen, done, "damage")), (10, []))
        audited(self, done)


class BabyPowerTest(unittest.TestCase):
    """6 章: ［わんぱくパンチ］・［じっとみる］。"""

    def test_bratty_punch(self):
        state = V113.board(mon(ELEKID), opponent=mon(H.MACHOP))
        pid = state.players[0].active.pokemon_id
        heads = apply_kernel(H.with_coin_results(state, HD), UsePokemonPower(0, pid, 0))
        self.assertEqual([e["amount"] for e in new_events(state, heads, "power_damage")], [20])
        self.assertEqual(heads.current_player, 1)  # 使ったら番は終わる
        tails = apply_kernel(H.with_coin_results(state, TL), UsePokemonPower(0, pid, 0))
        self.assertEqual((new_events(state, tails, "power_damage"), tails.current_player), ([], 1))
        audited(self, heads)
        audited(self, tails)
        lightning_weak = V113.board(mon(ELEKID), opponent=mon("PMCG1-063"))  # カモネギ（弱点 雷）: 弱点・抵抗力を計算するかで結果が変わる（Z9。コインの前）
        rejected(self, lightning_weak, UsePokemonPower(0, lightning_weak.players[0].active.pokemon_id, 0), "UNRESOLVED_POWER_DAMAGE_WEAKNESS_RESISTANCE")
        asleep = V113.board(mon(ELEKID, sleep=True))
        rejected(self, asleep, UsePokemonPower(0, asleep.players[0].active.pokemon_id, 0), "POKEMON_ASLEEP", IllegalActionError)

    def test_stare_stops_a_bench_power_until_active_or_turn_end(self):
        state = V113.board(mon(IGGLY, sleep=True), opponent=mon(H.RATTATA), opponent_bench=(mon(VULPIX_REVIVE), H.MACHOP))
        user, target, other = state.players[0].active.pokemon_id, state.players[1].bench[0].pokemon_id, state.players[1].bench[1].pokemon_id
        rejected(self, state, UsePokemonPower(0, user, 0, target=other), "TARGET_WITHOUT_POWER", IllegalActionError)
        rejected(self, state, UsePokemonPower(0, user, 0, target=state.players[1].active.pokemon_id), "TARGET_NOT_ON_BENCH", IllegalActionError)
        stared = apply_kernel(state, UsePokemonPower(0, user, 0, target=target))  # 説明に特殊状態の制限はない（ねむりでも使える）
        from kyuura_engine.persistent import powers_stopped

        self.assertIsNotNone(powers_stopped(stared, stared.players[1].bench[0]))
        audited(self, stared)
        rejected(self, stared, UsePokemonPower(0, user, 0, target=target), "POWER_ALREADY_USED", IllegalActionError)
        gust = V113.board(mon(IGGLY), opponent=mon(H.RATTATA), opponent_bench=(mon(VULPIX_REVIVE),), hand=(H.GUST,))
        gust_target = gust.players[1].bench[0].pokemon_id
        gust_stared = apply_kernel(gust, UsePokemonPower(0, gust.players[0].active.pokemon_id, 0, target=gust_target))
        pulled = apply_kernel(gust_stared, PlayTrainer(0, V113.uid(gust_stared, H.GUST)))
        while pulled.decision is not None:
            pulled = V113.answer(pulled, (gust_target,))
        self.assertEqual((pulled.players[1].active.pokemon_id, pulled.players[1].active.persistent_effects), (gust_target, ()))
        self.assertIn("entered_active", [e["reason"] for e in new_events(gust_stared, pulled, "persistent_effect_removed")])  # バトル場に出てきたとき、消える
        audited(self, pulled)
        ended = apply_kernel(stared, EndTurn(0))
        self.assertEqual(ended.players[1].bench[0].persistent_effects, ())
        self.assertIn("expired", [e["reason"] for e in new_events(stared, ended, "persistent_effect_removed")])


class DocumentTest(unittest.TestCase):
    def test_migration_chapter(self):
        text = DOC.read_text(encoding="utf-8")
        for word in (V0114, V097, "KYUURA_MIGRATIONS", "V0_97_KYUURA_COMMIT", "TARGET_SELECTION_COMMIT", "current_target_status_problems", "field_added_from_print",
                     "card_image_checks.json", "existing_transcription", "UQ-NEO-TEXT-BABY-CATEGORIES", "NB0", "ENGINE-46A3E2E", "with_card_data_commit_at"):
            self.assertIn(word, text)
        provenance = (ROOT / "docs" / "data-provenance.md").read_text(encoding="utf-8")
        self.assertIn("## v0.114: 写しの元・研究の基準を kyuura e519b99 に上げる移行", provenance)

    def test_esp_chapter(self):
        text = DOC.read_text(encoding="utf-8")
        for word in ("ENG-V0113-ESP-REDO-SWITCH-RESULT", "switched_results", "UNSUPPORTED_ESP_CONTINUATION", "_esp_carry_check", "EspSwitchContinuationTest", "からめとる",
                     "サカキのニャース（PMCG6-063）"):
            self.assertIn(word, text)
        v0113 = (ROOT / "docs" / "variable-coins-search-attachments-v0.113.md").read_text(encoding="utf-8")
        self.assertNotIn("カスミのニャース（PMCG6-063）", v0113)
        self.assertIn("6,315 件のうち失敗 2", v0113)  # v0.113 の全体のテストの記録はそのまま

    def test_card_chapters(self):
        """4〜12 章: 裁定の id・研究の記録の対応・説明の範囲の登録・検証の記録。ほかの文書（実装状況・README・ルールの仕様・データの出典）の v0.114 の項。"""
        text = DOC.read_text(encoding="utf-8")
        for word in ("BQ1", "NB1", "NB2", "BX1", "HP2", "HV1", *(f"BY-R{n}" for n in range(1, 15)), "TEXT_ERAS", "GR-2000-P325-PRE-NEO-BABY", "CR-BABY-RULE-NOT-POWER",
                     "PRN-030", "IMG-neo1-042", "エンジンは画像を見ていない", "1,263", "(114, 50, 64)", "UNRESOLVED_BABY_RULE_COIN_ORDER", "remove_on_entering_active",
                     "## 12. 検証", "lockstep", "単体のテストだけ"):
            self.assertIn(word, text)
        for card in BABIES:
            self.assertIn(card, text)
        status = (ROOT / "docs" / "implementation-status.md").read_text(encoding="utf-8")
        # v0.115: 題の範囲と README の「今のエンジンの版」は版を上げるたびに変わるので、v0.114 以後の範囲であることと、v0.114 の項（0.114.0）が残っていることを確かめる
        self.assertGreaterEqual(int(re.search(r"^# 実装状況（v0\.1〜v0\.(\d+)）", status, re.MULTILINE).group(1)), 114)
        self.assertIn("## v0.114: ベイビィポケモン 13 枚・ベイビィの共通のルール・ベイビィからの進化", status)
        self.assertNotIn("\n- ベイビィポケモン\n", status)  # 未実装の一覧から除いた
        self.assertRegex((ROOT / "README.md").read_text(encoding="utf-8"), r"\n- v0\.114（(今のエンジンの版。)?`kyuura_engine` の版は 0\.114\.0）: ベイビィポケモン 13 枚")
        self.assertIn("### v0.114: ベイビィポケモン 13 枚", (ROOT / "docs" / "rules-2000-02-14.md").read_text(encoding="utf-8"))
        self.assertIn("## v0.114: ベイビィポケモン 13 枚", (ROOT / "docs" / "data-provenance.md").read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()

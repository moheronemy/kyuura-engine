"""v0.71（docs/reprint-text-variants-v0.71.md）: 拡張パック以外の商品の再録のカード 78 枚（トレーナー 67 枚・ポケモン 11 枚。写しの組 pool_v0_71）。

- 元のカードと日本語のゲーム用データの差は、効果の文面と、ポケモン図鑑の名前の空白 1 つだけ（写しで確かめる）。登録は effects.REPRINT_CARDS（v0.69 の EQUIVALENT_CARDS とは別の表）が、
  元のカードの登録から作る: 照合する文面はこの版の印刷の文面、文面を引数に持つ型は引数をこの版の文面にし（型の check が数・種類・対象・順番を確かめる）、処理に使う文面と出典は
  元のカードが記録の最新の説明・エラッタにしたがう登録ならその登録と同じ（元のカードの記録の範囲を当てはめたもの。再録の版を照合した記録ではない）、印刷の文面にしたがう登録なら
  この版の印刷の文面
- 処理が違う 3 つ: エネルギー転送の再録の版（GD4-015・QSG-048。見せる・選ばなくてよい）・ポケモンジム第1弾の元気のかけら（GD1-017。使えない場合・選ぶ数・カウンターの順番）・
  プロモのリザードン（PR1-030）の「ほのおのうず」（エネルギーカード 2 枚。トラッシュはワザの効果。足りなければダメージは 0）
- ポケモン図鑑の 2 つの名前（「ポケモン図鑑HANDY505」「ポケモン図鑑 HANDY505」）は、デッキの同じ名前の数え方でまとめる（deck.SAME_NAME_SPELLINGS）

盤面を直接作るテスト（build_test_state）は 1 か所の規定を確かめるためだけに使い、正式な対戦開始からの対戦は GameTest（tools/existing_effect_games.py の
--batch v0.71）が確かめる。処理に使う文面の根拠は、元のカードの記録（card_verification.json・kyuura の LD-・TXT-CHARIZARD）と、このリポジトリの記録（card_sources.json の
reprint_scope）。ガイドブックは読んでいない。
"""

from __future__ import annotations

import copy
import dataclasses
import json
import unittest
from pathlib import Path

from kyuura_engine import (
    IllegalActionError,
    PlayTrainer,
    ResolveDecision,
    UnsupportedError,
    UseAttack,
    check_invariants,
    state_to_dict,
)
from kyuura_engine import effects as E
from kyuura_engine import engine as engine_module
from kyuura_engine.cards import load_card_pool, pool_from_extract, read_extract
from kyuura_engine.coins import CoinSide
from kyuura_engine.decisions import (
    BENCH_FROM_DISCARD,
    DISCARD_ENERGY,
    SEARCH_DECK,
    SELECT_ATTACK,
)
from kyuura_engine.deck import SAME_NAME_SPELLINGS, deck_problems, same_name
from kyuura_engine.resolution import PREFLIGHT_MODES, v013_checks
from scripts import check_card_sources as cs
from tests.helpers import (
    ATTACK_TYPES_SINCE_V0_17,
    CHARIZARD,
    CLEFAIRY,
    DOUBLE_COLORLESS_ENERGY,
    ENERGY_SEARCH,
    FIRE,
    FULL_HEAL,
    HITMONCHAN,
    NARROW_GYM,
    POKEDEX,
    POTION,
    PSYCHIC,
    RAINBOW_ENERGY,
    RATTATA,
    REVIVE,
    V0_71_CARDS,
    V0_71_POKEMON,
    V0_71_TRAINERS,
    WATER,
    apply_kernel,
    build_test_state,
    with_coin_results,
)
from tests.log_audit import observation_problems, serialization_problems

ROOT = Path(__file__).resolve().parent.parent
DOC = ROOT / "docs" / "reprint-text-variants-v0.71.md"
EXTRACT = read_extract()
CARDS = {c["id"]: c for c in EXTRACT["cards"]}
POOL_V0_71 = tuple(EXTRACT["pool_v0_71"])
H, T = CoinSide.HEADS, CoinSide.TAILS
TURN = 7
# 依頼の 78 枚（新しい id → 元のカード）
REQUESTED = {
    "GD1-006": "PMCG5-047", "GD1-014": "PMCG1-076", "GD1-016": "PMCG1-071", "GD1-017": "PMCG1-078", "GD1-018": "PMCG5-089", "GD1-020": "PMCG1-080",
    "GD1-021": "PMCG1-073", "GD1-022": "PMCG1-082", "GD1-023": "PMCG1-083", "GD1-024": "PMCG5-079", "GD2-019": "PMCG1-071", "GD2-020": "PMCG1-079",
    "GD2-021": "PMCG1-072", "GD2-022": "PMCG2-048", "GD2-023": "PMCG5-080", "GD3-014": "PMCG1-075", "GD3-017": "PMCG1-079", "GD3-018": "PMCG1-072",
    "GD3-019": "PMCG1-080", "GD3-020": "PMCG1-073", "GD3-023": "PMCG2-048", "GD3-024": "PMCG5-076", "GD4-004": "PMCG5-014", "GD4-014": "PMCG1-076",
    "GD4-015": "PMCG3-044", "GD4-019": "PMCG5-074", "GD4-020": "PMCG1-071", "GD4-021": "PMCG1-079", "GD4-022": "PMCG1-080", "GD4-023": "PMCG1-081",
    "GD4-024": "PMCG1-073", "GD4-025": "PMCG3-047", "GD4-027": "PMCG5-078", "GD5-011": "PMCG6-031", "GD5-018": "PMCG1-071", "GD5-020": "PMCG1-080",
    "GD5-022": "PMCG1-073", "GD5-023": "PMCG1-082", "GD5-024": "PMCG6-085", "GD6-010": "PMCG6-051", "GD6-014": "PMCG1-076", "GD6-015": "PMCG1-071",
    "GD6-016": "PMCG1-079", "GD6-020": "PMCG1-080", "GD6-021": "PMCG1-081", "GD6-022": "PMCG1-083", "GD6-024": "PMCG6-080", "GD6-025": "PMCG6-090",
    "QSG-047": "PMCG1-076", "QSG-048": "PMCG3-044", "QSG-049": "PMCG1-071", "QSG-050": "PMCG3-045", "QSG-051": "PMCG1-072", "QSG-052": "PMCG1-073",
    "QSG-053": "PMCG1-093", "IP1-007": "PMCG1-071", "IP1-019": "PMCG1-073", "IP1-028": "PMCG1-072", "IP2-007": "PMCG1-080", "IP2-009": "PMCG1-024",
    "IP2-019": "PMCG1-070", "IP2-024": "PMCG1-071", "IPH-001": "PMCG1-011", "IPH-002": "PMCG1-032", "PR1-028": "PMCG1-032", "PR1-029": "PMCG1-011",
    "PR1-030": "PMCG1-021", "PR1-033": "PMCG1-063", "NIP1-007": "PMCG1-080", "NIP1-015": "PMCG1-071", "NIP1-020": "PMCG1-074", "NIP1X-006": "PMCG1-081",
    "NIP1X-007": "PMCG1-073", "NIP2-008": "PMCG1-080", "NIP2-020": "PMCG1-071", "NIP2-025": "PMCG1-074", "NIP2X-006": "PMCG1-079", "NIP2X-007": "PMCG1-072",
}
BEHAVIOR = {"GD4-015": ("trainer",), "QSG-048": ("trainer",), "GD1-017": ("trainer",), "PR1-030": ("attack/0",),
            # v0.72: なんでもなおしの再録の版（対象を明示する）・ポケモン図鑑の再録の版（「最大」だけで 0 枚を選べるとは読まない）も処理が違う登録にした
            # （docs/status-coins-effect-reuse-v0.72.md 2 章）
            **{c: ("trainer",) for c in ("GD1-020", "GD3-019", "GD4-022", "GD5-020", "GD6-020", "IP2-007", "NIP1-007", "NIP2-008", "GD1-022", "GD5-023")}}
# 処理に使う文面が、元のカードの記録（card_verification.json の最新の説明・kyuura の LD-・TXT-CHARIZARD）のもの
REUSED = {"PMCG1-071": "trainer", "PMCG1-072": "trainer", "PMCG1-073": "trainer", "PMCG1-074": "trainer", "PMCG1-076": "trainer", "PMCG1-079": "trainer",
          "PMCG1-081": "trainer", "PMCG1-093": "trainer"}
POTION_GYM, REVIVE_GYM, ENERGY_SEARCH_GYM, ENERGY_SEARCH_QSG = "GD1-016", "GD1-017", "GD4-015", "QSG-048"
CHARIZARD_PROMO, POKEDEX_GYM, POKEDEX_GYM5 = "PR1-030", "GD1-022", "GD5-023"
SWITCH_GYM, GUST_GYM, RETRIEVAL_GYM = "GD1-021", "GD2-021", "GD1-014"
MISTYS_PSYDUCK, CLEFABLE = "PMCG5-021", "PMCG2-044"
CHARMANDER, CHARMELEON = "PMCG1-014", "PMCG1-017"


def board(hand=(), *, active=HITMONCHAN, bench=(RATTATA,), deck=None, discard=(), opponent=HITMONCHAN, opponent_bench=(RATTATA,), seed=0):
    me = {"active": active, "bench": list(bench), "hand": list(hand), "discard": list(discard)}
    if deck is not None:
        me["deck"] = list(deck)
    them = {"active": opponent, "bench": list(opponent_bench)}
    return build_test_state([me, them], turn_number=TURN, current_player=0, seed=seed)


def charizard(energy, *, player=0, **extra):
    """2 進化のリザードン（プロモ）。進化した番は持ち主の前の番（今の番に進化したポケモンは特殊状態を持てない）。"""
    return {"card": CHARIZARD_PROMO, "energy": list(energy), "evolved_from": [CHARMANDER, CHARMELEON], "evolved_turn": TURN - 2 if player == 0 else TURN - 1,
            **extra}


def uid(state, card_id, zone="hand", player=0, nth=0):
    return [u for u in getattr(state.players[player], zone) if state.cards[u].card_id == card_id][nth]


def play(state, card_id, player=0):
    return apply_kernel(state, PlayTrainer(player, uid(state, card_id, player=player)))


def answer(state, choices, *, mode="derived"):
    d = state.decision
    return apply_kernel(state, ResolveDecision(d.player, d.id, tuple(choices)), preflight=mode)


def snapshot(state):
    return state_to_dict(state, format_version=22), [dict(e) for e in state.log], repr(state.rng.getstate())


def events(state, since, kind=None):
    return [dict(e) for e in state.log[since:] if kind is None or e["kind"] == kind]


def audited(test, state):
    test.assertEqual(check_invariants(state), [])
    test.assertEqual(serialization_problems(state), [])
    test.assertEqual(observation_problems(state), [])
    return state


def assert_rejected(test, state, command, code, exception=IllegalActionError):
    """どの先読みの方法でも ``code`` で拒否し、状態・乱数・ログが変わらない。"""
    before = snapshot(state)
    for mode in PREFLIGHT_MODES:
        with test.subTest(mode=mode), test.assertRaises(exception) as raised:
            apply_kernel(state, command, preflight=mode)
        test.assertEqual(raised.exception.code, code)
    test.assertEqual(snapshot(state), before)


def total_cards(state):
    total = sum(len(p.hand) + len(p.deck) + len(p.discard) + len(p.prizes) + sum(len(pk.cards()) + len(pk.energy) + len(pk.trainers) for pk in p.in_play())
                for p in state.players)
    return total + (state.trainer_in_use is not None)


def modified_pool(card_id, change):
    extract = copy.deepcopy(read_extract())
    change(next(c for c in extract["cards"] if c["id"] == card_id))
    return pool_from_extract(extract)


# ---------------------------------------------------------------- 対象・写し・登録・数


class TargetTest(unittest.TestCase):

    def test_targets_are_the_requested_78_cards(self):
        self.assertEqual(POOL_V0_71, tuple(REQUESTED))
        self.assertEqual(POOL_V0_71, V0_71_CARDS)
        self.assertEqual(set(V0_71_POKEMON) | set(V0_71_TRAINERS), set(POOL_V0_71))
        self.assertEqual((len(V0_71_POKEMON), len(V0_71_TRAINERS)), (11, 67))
        self.assertEqual({k: v.original for k, v in E.REPRINT_CARDS.items()}, REQUESTED)
        earlier = {c for key, pool in EXTRACT.items() if key.startswith("pool_") and key not in ("pool_v0_71", "pool_v0_72", "pool_v0_73") for c in pool}
        self.assertEqual(len(earlier), 635)
        self.assertFalse(set(POOL_V0_71) & earlier)
        self.assertTrue(set(REQUESTED.values()) <= earlier)
        self.assertFalse(set(POOL_V0_71) & set(E.EQUIVALENT_CARDS))
        self.assertEqual(len(EXTRACT["cards"]) - len(EXTRACT["pool_v0_73"]), 756)  # v0.72 で 43 枚を加えた（v0.73 の 18 枚を除いて比べる）
        targets = {c["id"]: c for c in EXTRACT["reprint_targets"]["cards"]}
        for new, original in REQUESTED.items():
            with self.subTest(card=new):
                self.assertEqual([x["id"] for x in targets[new]["nearest_registered"]], [original])
                self.assertEqual(CARDS[new]["same_card_group"], CARDS[original]["same_card_group"])

    def test_only_effect_text_and_the_pokedex_space_differ(self):
        """日本語のゲーム用データ（HP・タイプ・弱点・抵抗力・にげる・段階・進化元・ワザの名前と必要なエネルギーとダメージ・特殊能力の名前と種類・トレーナーの種類）は元のカードと
        同じ。違うのは効果の文面と、ポケモン図鑑の名前の空白だけ。"""
        for new, original in REQUESTED.items():
            with self.subTest(card=new):
                self.assertEqual(cs.text_free_view(CARDS[new]), cs.text_free_view(CARDS[original]))
                self.assertNotEqual(cs.engine_view(CARDS[new]), cs.engine_view(CARDS[original]))  # 文面は違う（同じなら v0.69 の写しの表）
                names = (CARDS[new]["name"]["ja"], CARDS[original]["name"]["ja"])
                if new in (POKEDEX_GYM, POKEDEX_GYM5):
                    self.assertEqual(names, ("ポケモン図鑑HANDY505", "ポケモン図鑑 HANDY505"))
                else:
                    self.assertEqual(names[0], names[1])

    def test_counts_from_the_registry(self):
        pool = load_card_pool()
        playable = pool.playable_ids - set(EXTRACT["pool_v0_73"])  # v0.73 の 18 枚（トレーナー）を除いて比べる
        self.assertEqual(len(playable), 756)  # v0.72 で拡張パック以外の商品のポケモン 43 枚（ワザ 77）を加えた
        counts = {k: sum(1 for c in playable if pool.get(c).category == k) for k in ("pokemon", "trainer", "energy")}
        self.assertEqual(counts, {"pokemon": 546, "trainer": 180, "energy": 30})
        registry = E.DEFAULT_EFFECTS
        self.assertEqual((len(registry.attack_keys()), len(registry.power_keys()), len([c for c in registry.trainer_ids() if c not in EXTRACT["pool_v0_73"]]), len(registry.energy_ids())), (917, 74, 180, 12))
        self.assertTrue(all(pool.get(c).supported for c in POOL_V0_71))

    def test_new_type_is_a_kernel_program_outside_the_v013_contract(self):
        self.assertIn(E.DiscardEnergyCardsThenDamageZeroIfLacking, ATTACK_TYPES_SINCE_V0_17)
        self.assertNotIn(E.DiscardEnergyCardsThenDamageZeroIfLacking, v013_checks.VERIFIED)
        self.assertIs(E.DiscardEnergyCardsThenDamageZeroIfLacking.resolve, E.AttackEffect.resolve)

    def test_no_card_specific_branch_in_the_engine(self):
        for path in ("kyuura_engine/engine.py", *sorted(str(p.relative_to(ROOT)) for p in (ROOT / "kyuura_engine" / "resolution").glob("*.py"))):
            text = (ROOT / path).read_text(encoding="utf-8")
            for card_id in POOL_V0_71:
                self.assertNotIn(f'"{card_id}"', text, path)


class RegistrationTest(unittest.TestCase):
    """登録は元のカードの登録から決まりどおりに作る（effects._with_reprint_cards）。"""

    def test_settings_table(self):
        """登録の型と引数: 処理が同じものは元のカードの実装（文面を引数に持つ型は引数をこの版の文面に）。処理が違うものはその型。"""
        registry = E.DEFAULT_EFFECTS
        mine_all = {}
        for new, original in REQUESTED.items():
            mine, theirs = cs._registrations(registry, new), cs._registrations(registry, original)
            self.assertEqual(set(mine), set(theirs), new)
            for target, entry in mine.items():
                base = theirs[target]
                with self.subTest(card=new, target=target):
                    if base.text_ja is None:
                        self.assertIs(entry, base)
                        continue
                    self.assertEqual(entry.text_ja, cs.printed_text(CARDS[new], target))
                    if target in BEHAVIOR.get(new, ()):
                        self.assertNotEqual(entry.effect, base.effect)
                        self.assertEqual((entry.play_text_ja, entry.source), (entry.text_ja, "kyuura data/cards.json"))
                        continue
                    expected = base.effect
                    if any(f.name == "text" for f in dataclasses.fields(expected)):
                        expected = dataclasses.replace(expected, text=entry.text_ja)
                    self.assertEqual(entry.effect, expected)
                    if REUSED.get(original) == target or base.source != "kyuura data/cards.json":
                        self.assertEqual((entry.play_text_ja, entry.source), (base.play_text_ja, base.source))
                    else:
                        self.assertEqual((entry.play_text_ja, entry.source), (entry.text_ja, "kyuura data/cards.json"))
                    mine_all[(new, target)] = entry
        behavior = {new: tuple(r.behavior) for new, r in E.REPRINT_CARDS.items() if r.behavior}
        self.assertEqual(behavior, BEHAVIOR)
        search = registry.trainer_entry(ENERGY_SEARCH_GYM).effect
        self.assertEqual((type(search), search.target, search.count, search.optional, search.reveal, search.coin, search.discard_cost),
                         (E.SearchDeckTrainer, E.CardFilter("basic_energy"), 1, True, True, False, 0))
        self.assertIs(registry.trainer_entry(ENERGY_SEARCH_QSG), registry.trainer_entry(ENERGY_SEARCH_GYM))
        original = registry.trainer_entry(ENERGY_SEARCH).effect
        self.assertEqual((original.optional, original.reveal), (False, False))  # 化石の秘密の版は変えていない（ST1）
        self.assertIsInstance(registry.trainer_entry(REVIVE_GYM).effect, E.BenchBasicFromOwnDiscardThenCounters)
        self.assertIsInstance(registry.trainer_entry(REVIVE).effect, E.BenchBasicFromOwnDiscardWithCounters)
        self.assertEqual(registry.attack_entry(CHARIZARD_PROMO, 0).effect, E.DiscardEnergyCardsThenDamageZeroIfLacking(2))
        self.assertEqual(registry.attack_entry(CHARIZARD, 0).effect, E.DiscardEnergyBeforeDamage(None, 2, "unresolved", "condition"))  # HC1 のまま

    def test_identical_reprints_share_entries(self):
        """同じ元のカード・同じ印刷の文面の再録（同じデータのカード 33 枚）は、同じ登録の値（不変なオブジェクト）を使う。違う文面のものはまとめない。"""
        registry = E.DEFAULT_EFFECTS
        groups = {}
        for new in POOL_V0_71:
            groups.setdefault(json.dumps(cs.engine_view(CARDS[new]), ensure_ascii=False, sort_keys=True), []).append(new)
        self.assertEqual(len(groups), 45)
        self.assertEqual(sum(len(g) - 1 for g in groups.values()), 33)
        for members in groups.values():
            first = cs._registrations(registry, members[0])
            for other in members[1:]:
                mine = cs._registrations(registry, other)
                self.assertTrue(all(mine[t] is first[t] for t in first), other)
        self.assertIsNot(registry.trainer_entry("GD1-016"), registry.trainer_entry("NIP1-015"))  # 文面が違う

    def test_helper_rejects_bad_tables(self):
        good = E.REPRINT_CARDS["GD1-016"]
        base = E.DEFAULT_EFFECTS
        cases = {
            "already registered": {POTION: good},
            "original not registered": {"XX-001": dataclasses.replace(good, original="PMCG1-009")},
            "original is an equivalent copy": {"XX-001": dataclasses.replace(good, original=next(iter(E.EQUIVALENT_CARDS)))},
            "original is another reprint": {"XX-001": dataclasses.replace(good, original="GD1-016"), "GD1-016": good},
            "text targets differ": {"XX-001": dataclasses.replace(good, texts={"attack/0": "x"})},
            "behavior outside the texts": {"XX-001": dataclasses.replace(good, behavior={"attack/0": E.DAMAGE_ONLY})},
        }
        for label, table in cases.items():
            with self.subTest(case=label), self.assertRaises(RuntimeError):
                E._with_reprint_cards(base, table)


class UnsupportedWithoutRegistrationTest(unittest.TestCase):
    """登録を除けば未対応にもどる。データ（文面・名前・HP・必要なエネルギー）が登録と合わなければ未対応。"""

    def test_without_the_reprint_registrations_the_cards_are_unsupported(self):
        registry = E.DEFAULT_EFFECTS
        registry = registry.without_attacks("t", [k for k in registry.attack_keys() if k.card_id in POOL_V0_71]) \
            .without_powers("t", [k for k in registry.power_keys() if k.card_id in POOL_V0_71]) \
            .without_trainers("t", [c for c in registry.trainer_ids() if c in POOL_V0_71])
        pool = pool_from_extract(read_extract(), registry)
        self.assertEqual([c for c in POOL_V0_71 if pool.get(c).supported], [])
        self.assertEqual(len(pool.playable_ids - set(EXTRACT["pool_v0_73"])), 678)  # v0.72 の 43 枚を含む（v0.71 の時点は 635。v0.73 の 18 枚は除いて比べる）

    def test_data_mismatch_makes_the_card_unsupported(self):
        def trainer_text(value):
            return lambda c: c["trainer"]["text"].__setitem__("ja", value)

        cases = [
            # きずぐすり: 数
            ("GD1-016", trainer_text("あなたの場のポケモン1匹を選び、そのポケモンにのっているダメージカウンターを最大3個、とりのぞいてよい。")),
            # エネルギー転送: 「相手プレイヤーに見せてから」を除く（見せる設定と合わない）・2 枚
            (ENERGY_SEARCH_GYM, trainer_text("あなたの山札から「基本エネルギーカード」を1枚選び出し、手札に加えてよい。その後、その山札をよく切る。")),
            (ENERGY_SEARCH_GYM, trainer_text("あなたの山札から「基本エネルギーカード」を最大2枚選び出し、相手プレイヤーに見せてから、手札に加えてよい。その後、その山札をよく切る。")),
            # 元気のかけら: 文面の違い
            (REVIVE_GYM, trainer_text(E.REVIVE_GYM_TEXT.replace("ベンチに出す。その後", "ベンチに出す。そして"))),
            # なんでもなおし・ポケモン図鑑・いいきずぐすり・ギャンブラー・エネルギー・リムーブ: 数・種類・対象
            ("GD1-020", trainer_text("あなたの対戦ポケモンの「どく・ねむり」状態を、すべて回復させる。")),
            (POKEDEX_GYM, trainer_text("あなたの山札の上から最大3枚のカードを見て、好きな順番に入れ替えてから、山札の上にもどす。")),
            ("GD3-014", trainer_text("あなたの場にいるポケモンから、エネルギーカードのついているものを1匹選ぶ。そのポケモンについているエネルギーカードを1枚トラッシュして、そのポケモンにのっているダメージカウンターを最大3個、とりのぞく。")),
            ("QSG-050", trainer_text("相手の手札をすべて山札にもどし、その山札をよく切る。その後、コインを投げて「おもて」なら8枚、「うら」なら1枚のカードを山札から引いて、手札にする。")),
            ("IP2-019", trainer_text("相手の場のポケモンを1匹選ぶ。そのポケモンについているエネルギーカードを2枚選び、トラッシュさせる。")),
            ("GD1-023", trainer_text("あなたの場の、ダメージカウンターがのっているすべてのポケモンから、ダメージカウンターをすべてとりのぞく。")),
            # ほのおのうず: 枚数・必要なエネルギー・ダメージ
            (CHARIZARD_PROMO, lambda c: c["pokemon"]["attacks"][0]["text"].__setitem__("ja", E.DISCARD_ENERGY_CARDS_ZERO_IF_LACKING_TEXT.format(count=3))),
            (CHARIZARD_PROMO, lambda c: c["pokemon"]["attacks"][0].__setitem__("damage", {"base": 100, "modifier": "+", "display": "100+"})),
            # 名前
            ("GD1-021", lambda c: c["name"].__setitem__("ja", "ポケモンいれかえ2")),
            # ワザ・特殊能力の書き方
            ("GD1-006", lambda c: c["pokemon"]["attacks"][0]["text"].__setitem__("ja", CARDS["GD1-006"]["pokemon"]["attacks"][0]["text"]["ja"].replace("(自分のベンチに空きがない時、このワザは使えない)", ""))),
            ("GD6-010", lambda c: c["pokemon"]["attacks"][0]["text"].__setitem__("ja", E.INVIGORATE_TEXT.replace("半分", "4分の1"))),
        ]
        for card_id, change in cases:
            with self.subTest(card=card_id):
                self.assertTrue(load_card_pool().get(card_id).supported)
                self.assertFalse(modified_pool(card_id, change).get(card_id).supported)

    def test_added_wordings_are_tied_to_the_registered_settings(self):
        """書き方を受け付ける一覧に加えたのは、意味を確かめた書き方 1 通りずつ。登録の引数（数・種類・プレイヤー）と合わないものは受け付けない。"""
        pool = load_card_pool()
        pokedex = pool.get(POKEDEX_GYM)
        self.assertEqual(E.ArrangeOwnDeckTopTrainer(pokedex.trainer_text_ja, 5, zero_allowed=False).check(pokedex), [])
        self.assertTrue(E.ArrangeOwnDeckTopTrainer(pokedex.trainer_text_ja, 4, zero_allowed=False).check(pokedex))
        # v0.72: 再録の版の「最大」は 0 枚を選べる設定（旧版の「ことができる」）と結びつけない
        self.assertTrue(E.ArrangeOwnDeckTopTrainer(pokedex.trainer_text_ja, 5).check(pokedex))
        full_heal = pool.get("GD1-020")
        self.assertEqual(E.CureSpecialConditionsTrainer(full_heal.trainer_text_ja, E.FULL_HEAL_SCOPE_OWN_ACTIVE).check(full_heal), [])
        self.assertTrue(E.CureSpecialConditionsTrainer(full_heal.trainer_text_ja).check(full_heal))
        old_full_heal = pool.get("PMCG1-080")
        self.assertTrue(E.CureSpecialConditionsTrainer(old_full_heal.trainer_text_ja, E.FULL_HEAL_SCOPE_OWN_ACTIVE).check(old_full_heal))
        center = pool.get("GD1-023")
        self.assertEqual(E.HealEachDamagedPokemonTrainer(center.trainer_text_ja, E.HEAL_SELF, None, True).check(center), [])
        self.assertTrue(E.HealEachDamagedPokemonTrainer(center.trainer_text_ja, E.HEAL_SELF, None, False).check(center))
        super_potion = pool.get("GD3-014")
        self.assertEqual(E.DiscardEnergyThenHealTrainer(super_potion.trainer_text_ja, 4).check(super_potion), [])
        self.assertTrue(E.DiscardEnergyThenHealTrainer(super_potion.trainer_text_ja, 3).check(super_potion))
        gambler = pool.get("QSG-050")
        good = E.DEFAULT_EFFECTS.trainer_entry("QSG-050").effect
        self.assertEqual(good.check(gambler), [])
        self.assertTrue(dataclasses.replace(good, who=E.HANDS_OPPONENT).check(gambler))
        removal = pool.get("IP2-019")
        self.assertEqual(E.DiscardAttachedEnergyTrainer(removal.trainer_text_ja, 1, 0).check(removal), [])
        self.assertTrue(E.DiscardAttachedEnergyTrainer(removal.trainer_text_ja, 2, 0).check(removal))
        self.assertEqual(len(E.FULL_HEAL_TEXTS), 2)
        self.assertEqual(len(E.INVIGORATE_TEXTS), 2)
        self.assertEqual(len(E.DEFENSIVE_POLLEN_TEXTS), 2)
        self.assertEqual(len(E.ONCE_AFTER_ENTRY_NO_DAMAGE_ON_TAILS_TEXTS), 3)
        search = pool.get(ENERGY_SEARCH_GYM)
        for wrong in ({"reveal": False}, {"optional": False}, {"count": 2}, {"coin": True}):
            with self.subTest(wrong=wrong):
                self.assertTrue(dataclasses.replace(E.DEFAULT_EFFECTS.trainer_entry(ENERGY_SEARCH_GYM).effect, **wrong).check(search))


class SameNameTest(unittest.TestCase):
    """ポケモン図鑑の名前の空白（「ポケモン図鑑HANDY505」と「ポケモン図鑑 HANDY505」）: 名前はそのまま持ち、デッキの同じ名前の数え方でだけまとめる（表に書いた組だけ）。"""

    def test_names_are_kept_and_counted_together(self):
        pool = load_card_pool()
        self.assertEqual({pool.get(c).name_ja for c in (POKEDEX_GYM, POKEDEX_GYM5)}, {"ポケモン図鑑HANDY505"})
        self.assertEqual(pool.get(POKEDEX).name_ja, "ポケモン図鑑 HANDY505")
        self.assertEqual(dict(SAME_NAME_SPELLINGS), {"ポケモン図鑑HANDY505": "ポケモン図鑑 HANDY505"})
        names = {pool.get(c).name_ja for c in pool.playable_ids}
        self.assertTrue(set(SAME_NAME_SPELLINGS) | set(SAME_NAME_SPELLINGS.values()) <= names)
        self.assertEqual(same_name("ポケモンいれかえ"), "ポケモンいれかえ")
        base = [WATER] * 48 + ["PMCG1-024"] * 4 + ["PMCG1-074"] * 4
        four = base + [POKEDEX_GYM, POKEDEX_GYM, POKEDEX_GYM5, POKEDEX]
        self.assertEqual(deck_problems(four), [])
        five = base[:-1] + [POKEDEX_GYM, POKEDEX_GYM, POKEDEX_GYM5, POKEDEX, POKEDEX]
        self.assertEqual([p for p in deck_problems(five) if p.startswith("TOO_MANY_COPIES")],
                         ["TOO_MANY_COPIES: 「ポケモン図鑑 HANDY505」が 5 枚（同じ名前は 4 枚まで）"])

    def test_other_spaced_names_are_not_merged(self):
        """空白を一律に除かない（表にない名前はそのまま数える）。"""
        self.assertEqual(same_name("ポケモン図鑑 HANDY505X"), "ポケモン図鑑 HANDY505X")
        self.assertEqual(same_name("ポケモン図鑑HANDY505 "), "ポケモン図鑑HANDY505 ")


# ---------------------------------------------------------------- 元のカードの記録を当てはめた処理


class ReusedLatestDescriptionTest(unittest.TestCase):

    def test_potion_removes_two_when_two_or_more(self):
        """きずぐすりの再録の版（「最大2個、とりのぞいてよい」）も、元のカードの照合の記録（p.254）の最新の説明と解説「2個のっていたら2個とってください」にしたがう
        （とりのぞく数を選ぶ決定を作らない）。1 個なら 1 個。"""
        for card_id in ("GD1-016", "QSG-049", "NIP1-015"):
            for counters, left in ((3, 1), (2, 0), (1, 0)):
                with self.subTest(card=card_id, counters=counters):
                    state = board([card_id], active={"card": HITMONCHAN, "damage": counters * 10})
                    state = play(state, card_id)
                    self.assertEqual(state.decision.kind, "select_pokemon")
                    after = audited(self, answer(state, (state.players[0].active.pokemon_id,)))
                    self.assertIsNone(after.decision)
                    self.assertEqual(after.players[0].active.damage, left * 10)

    def test_existing_unresolved_stops_are_kept(self):
        """印刷の文面の「控えがいない時、このカードは使えない」「最大2枚選び、手札に加えてよい」で、元のカードの止める処理（UNRESOLVED_SWITCH_WITHOUT_BENCH・GW5・ER9・ER10・
        きずぐすりの UNRESOLVED_POTION_WITHOUT_DAMAGE）を決めない。"""
        cases = (
            (SWITCH_GYM, board([SWITCH_GYM], bench=()), "UNRESOLVED_SWITCH_WITHOUT_BENCH"),
            ("NIP1X-007", board(["NIP1X-007"], bench=()), "UNRESOLVED_SWITCH_WITHOUT_BENCH"),
            (GUST_GYM, board([GUST_GYM], opponent_bench=()), "UNRESOLVED_GUST_WITHOUT_OPPONENT_BENCH"),
            ("NIP2X-007", board(["NIP2X-007"], opponent_bench=()), "UNRESOLVED_GUST_WITHOUT_OPPONENT_BENCH"),
            (RETRIEVAL_GYM, board([RETRIEVAL_GYM, RATTATA]), "UNRESOLVED_ENERGY_RETRIEVAL_WITHOUT_TARGET"),
            (POTION_GYM, board([POTION_GYM]), "UNRESOLVED_POTION_WITHOUT_DAMAGE"),
        )
        for card_id, state, code in cases:
            with self.subTest(card=card_id):
                assert_rejected(self, state, PlayTrainer(0, uid(state, card_id)), code, UnsupportedError)
        state = play(board([RETRIEVAL_GYM, RATTATA], discard=[FIRE, WATER]), RETRIEVAL_GYM)
        state = answer(state, (uid(state, RATTATA),))
        before = snapshot(state)
        with self.assertRaises(UnsupportedError) as raised:
            answer(state, ())
        self.assertEqual(raised.exception.code, "UNRESOLVED_ENERGY_RETRIEVAL_ZERO_CHOICE")
        self.assertEqual(snapshot(state), before)
        after = audited(self, answer(state, tuple(state.decision.options)))
        self.assertEqual(sorted(after.cards[u].card_id for u in after.players[0].hand), sorted([FIRE, WATER]))

    def test_full_heal_reprints_cure_only_the_own_active(self):
        """v0.72: なんでもなおしの再録の版（「あなたの対戦ポケモンの「どく・ねむり・マヒ・こんらん」状態を、すべて回復させる。」）は、文面のとおり自分の対戦ポケモンだけを
        回復する。相手の対戦ポケモンが特殊状態でも止めず、相手の特殊状態は残す（v0.71 は FH1 で止めていた。必要より広い拒否）。自分の対戦ポケモンに特殊状態がないときに
        使えるかは別の問い（FH2）で、止めたまま（状態を変えない）。旧版（PMCG1-080。対象を書かない）の FH1 は変えない。"""
        for card_id in ("GD1-020", "GD3-019", "GD4-022", "GD5-020", "GD6-020", "IP2-007", "NIP1-007", "NIP2-008"):
            with self.subTest(card=card_id):
                state = board([card_id], active={"card": HITMONCHAN, "poison": 10, "confusion": True})
                done = audited(self, play(state, card_id))
                self.assertIsNone(done.decision)
                self.assertEqual(done.players[0].active.conditions.names(), ())
                both = board([card_id], active={"card": HITMONCHAN, "poison": 10}, opponent={"card": HITMONCHAN, "sleep": True})
                done = audited(self, play(both, card_id))
                self.assertEqual(done.players[0].active.conditions.names(), ())
                self.assertEqual(done.players[1].active.conditions.names(), both.players[1].active.conditions.names())
                self.assertTrue(done.players[1].active.conditions.names())
                removed = [e for e in done.log[len(both.log):] if e["kind"] == "special_conditions_removed"]
                self.assertEqual([e["player"] for e in removed], [0])
                self.assertIn(card_id, [done.cards[u].card_id for u in done.players[0].discard])
                only_opponent = board([card_id], opponent={"card": HITMONCHAN, "sleep": True})
                assert_rejected(self, only_opponent, PlayTrainer(0, uid(only_opponent, card_id)), "UNRESOLVED_FULL_HEAL_WITHOUT_CONDITION", UnsupportedError)
                assert_rejected(self, board([card_id]), PlayTrainer(0, uid(board([card_id]), card_id)), "UNRESOLVED_FULL_HEAL_WITHOUT_CONDITION", UnsupportedError)
        old_both = board([FULL_HEAL], active={"card": HITMONCHAN, "poison": 10}, opponent={"card": HITMONCHAN, "sleep": True})
        assert_rejected(self, old_both, PlayTrainer(0, uid(old_both, FULL_HEAL)), "UNRESOLVED_FULL_HEAL_SCOPE", UnsupportedError)
        assert_rejected(self, board([FULL_HEAL]), PlayTrainer(0, uid(board([FULL_HEAL]), FULL_HEAL)), "UNRESOLVED_FULL_HEAL_SCOPE", UnsupportedError)
        old = audited(self, play(board([FULL_HEAL], active={"card": HITMONCHAN, "poison": 10}), FULL_HEAL))
        self.assertEqual(old.players[0].active.conditions.names(), ())

    def test_pokedex_reprints_stop_only_on_zero(self):
        """v0.72: ポケモン図鑑の再録の版（「あなたの山札の上から最大5枚のカードを見て、…もどす。」）は「てよい」「ことができる」がなく、山札があるのに 0 枚を選べるかは
        決まらない（kyuura の UQ-UP-TO-ZERO-CHOICE と同じ形。PD2）。0 枚の答えだけを止め（決定は待ったまま・状態は変わらない）、1〜min(5, 山札) 枚は見る。旧版（PMCG1-082）の
        「…ことができる」の 0 枚（PD1。見ない）と、山札が 0 枚で見るカードがない場合は変えない。"""
        deck = [RATTATA] * 3
        for card_id in (POKEDEX_GYM, POKEDEX_GYM5):
            with self.subTest(card=card_id):
                state = play(board([card_id], deck=deck), card_id)
                self.assertEqual(state.decision.kind, "select_look_count")
                self.assertEqual(state.decision.options, (0, 1, 2, 3))
                before = snapshot(state)
                with self.assertRaises(UnsupportedError) as raised:
                    answer(state, (0,))
                self.assertEqual(raised.exception.code, "UNRESOLVED_POKEDEX_UP_TO_ZERO")
                self.assertEqual(snapshot(state), before)
                for count in (1, 2, 3):
                    after = audited(self, answer(state, (count,)))
                    looked = [e for e in after.log if e["kind"] == "look_at_deck_top"]
                    self.assertEqual(looked[-1]["count"], count)
                empty = audited(self, play(board([card_id], deck=[]), card_id))
                self.assertEqual([e["kind"] for e in empty.log[-3:]].count("look_at_deck_top_none"), 1)
                self.assertIsNone(empty.decision)
        old = play(board([POKEDEX], deck=deck), POKEDEX)
        declined = audited(self, answer(old, (0,)))
        self.assertIn("look_at_deck_top_declined", [e["kind"] for e in declined.log])

    def test_rain_dance_reprints_follow_the_latest_description(self):
        """カメックスの再録（IPH-002 の「この力は、自分の中で何度でも使える」は「番」が落ちた候補）も、元のカードの最新の説明（LD-PMCG1-032-PWR0）。写しは直さない。"""
        for card_id in ("IPH-002", "PR1-028"):
            entry = E.DEFAULT_EFFECTS.power_entry(card_id, 0)
            base = E.DEFAULT_EFFECTS.power_entry("PMCG1-032", 0)
            self.assertEqual((entry.play_text_ja, entry.source, entry.effect), (base.play_text_ja, base.source, base.effect))
        self.assertIn("この力は、自分の中で何度でも使える。", CARDS["IPH-002"]["pokemon"]["powers"][0]["text"]["ja"])
        record = cs.load_sources()["cards"]["IPH-002"]
        self.assertEqual([i["affects_behavior"] for i in record["issues"]], [False])

    def test_energy_burn_reprint_uses_txt_charizard(self):
        entry = E.DEFAULT_EFFECTS.power_entry(CHARIZARD_PROMO, 0)
        self.assertEqual((entry.source, entry.effect), ("TXT-CHARIZARD", E.ConvertAttachedEnergy(E.EnergyType.FIRE)))
        self.assertEqual(entry.play_text_ja, E.DEFAULT_EFFECTS.power_entry(CHARIZARD, 0).play_text_ja)
        self.assertEqual(CARDS[CHARIZARD_PROMO]["copies"], [{"page": "1stp030", "list_number": "-/-"}])


# ---------------------------------------------------------------- エネルギー転送の再録の版


class EnergySearchReprintTest(unittest.TestCase):
    """あなたの山札から「基本エネルギーカード」を1枚選び出し、相手プレイヤーに見せてから、手札に加えてよい。その後、その山札をよく切る。"""

    def test_reveal_and_shuffle(self):
        state = board([ENERGY_SEARCH_GYM], deck=[RATTATA, WATER, POTION, FIRE, DOUBLE_COLORLESS_ENERGY, RAINBOW_ENERGY])
        state = play(state, ENERGY_SEARCH_GYM)
        d = state.decision
        self.assertEqual((d.kind, d.min_choices, d.max_choices), (SEARCH_DECK, 0, 1))
        self.assertEqual(sorted(state.cards[u].card_id for u in d.options), sorted([WATER, FIRE]))  # 特殊エネルギーは選べない
        since = len(state.log)
        water = next(u for u in d.options if state.cards[u].card_id == WATER)
        after = audited(self, answer(state, (water,)))
        kinds = [e["kind"] for e in events(after, since)]
        self.assertEqual(kinds[:2], ["reveal_from_deck", "shuffle"])
        self.assertIn(water, after.players[0].hand)
        self.assertEqual(total_cards(after), total_cards(state))
        self.assertFalse(any(e["kind"] == "search_deck" for e in after.log))
        log_text = json.dumps(events(after, 0, "play_trainer"), ensure_ascii=False)
        self.assertNotIn(str(d.options), log_text)  # 選べるものの一覧はログに書かない

    def test_choose_none_and_no_target(self):
        """選ばなくてよい（0 枚）・選べるカードがない: 止めずに選ばずに終わり、山札を切る（化石の秘密の版は ST1 で止める）。"""
        for deck in ([RATTATA, WATER], [RATTATA, POTION], []):
            with self.subTest(deck=deck):
                state = board([ENERGY_SEARCH_GYM], deck=deck)
                since = len(state.log)
                state = play(state, ENERGY_SEARCH_GYM)
                if state.decision is not None:  # 選べるカードがあれば決定（0 枚を選ぶ）。なければ決定を出さずに終わる
                    state = answer(state, ())
                after = audited(self, state)
                kinds = [e["kind"] for e in events(after, since)]
                self.assertEqual(kinds[kinds.index("trainer_take_none"):kinds.index("trainer_take_none") + 2], ["trainer_take_none", "shuffle"])
                self.assertIsNone(after.trainer_in_use)
        state = board([ENERGY_SEARCH], deck=[RATTATA, POTION])
        assert_rejected(self, state, PlayTrainer(0, uid(state, ENERGY_SEARCH)), "UNRESOLVED_SEARCH_TRAINER_WITHOUT_TARGET", UnsupportedError)

    def test_invalid_answers_keep_the_decision(self):
        state = play(board([ENERGY_SEARCH_QSG], deck=[WATER, FIRE, RATTATA]), ENERGY_SEARCH_QSG)
        rattata = uid(state, RATTATA, "deck")
        before = snapshot(state)
        for choices in ((rattata,), tuple(state.decision.options)):
            with self.subTest(choices=choices), self.assertRaises(IllegalActionError):
                answer(state, choices)
            self.assertEqual(snapshot(state), before)


# ---------------------------------------------------------------- ポケモンジム第1弾の元気のかけら


class ReviveGymTest(unittest.TestCase):
    """あなたのトラッシュから、たねポケモンカードを1枚選び、あなたのベンチに出す。その後、そのポケモンに、HPの半分(切りすて)のダメージカウンターをのせる。
    （あなたのトラッシュにたねポケモンカードがない時や、あなたのベンチに空きがない時、このカードは使えない）"""

    def test_cannot_be_used_without_a_basic_or_bench_space(self):
        cases = (
            (board([REVIVE_GYM], discard=[FIRE, CHARMELEON]), "NO_BASIC_POKEMON_IN_DISCARD"),
            (board([REVIVE_GYM], bench=(RATTATA,) * 5, discard=[HITMONCHAN]), "BENCH_FULL"),
        )
        for state, code in cases:
            with self.subTest(code=code):
                assert_rejected(self, state, PlayTrainer(0, uid(state, REVIVE_GYM)), code)
        # せまいジム（ベンチは 4 匹まで）
        state = board([NARROW_GYM, REVIVE_GYM], bench=(RATTATA,) * 4, discard=[HITMONCHAN])
        state = play(state, NARROW_GYM)
        assert_rejected(self, state, PlayTrainer(0, uid(state, REVIVE_GYM)), "BENCH_FULL")
        # 第1弾の版は RV1 のまま
        state = board([REVIVE], discard=[FIRE])
        assert_rejected(self, state, PlayTrainer(0, uid(state, REVIVE)), "UNRESOLVED_REVIVE_WITHOUT_TARGET", UnsupportedError)

    def test_exactly_one_card_then_counters_after_entering(self):
        state = board([REVIVE_GYM], discard=[HITMONCHAN, CHARMANDER, FIRE])
        state = play(state, REVIVE_GYM)
        d = state.decision
        self.assertEqual((d.kind, d.min_choices, d.max_choices, d.player), (BENCH_FROM_DISCARD, 1, 1, 0))
        self.assertEqual(sorted(state.cards[u].card_id for u in d.options), sorted([HITMONCHAN, CHARMANDER]))
        before = snapshot(state)
        with self.assertRaises(IllegalActionError):
            answer(state, ())  # 選ばない答えはない
        self.assertEqual(snapshot(state), before)
        with self.assertRaises(IllegalActionError):
            answer(state, (uid(state, FIRE, "discard"),))
        self.assertEqual(snapshot(state), before)
        hitmonchan = uid(state, HITMONCHAN, "discard")
        since = len(state.log)
        after = audited(self, answer(state, (hitmonchan,)))
        log = events(after, since)
        self.assertEqual([e["kind"] for e in log[:2]], ["bench_from_discard", "trainer_place_damage_counters"])
        self.assertNotIn("counters", log[0])  # 出すときにはのせない
        self.assertEqual((log[1]["counters"], log[1]["damage_before"], log[1]["total_damage"]), (3, 0, 30))  # HP 70 の半分（切りすて）
        pokemon = after.players[0].bench[-1]
        self.assertEqual((pokemon.card, pokemon.damage, pokemon.played_turn), (hitmonchan, 30, TURN))
        self.assertEqual(total_cards(after), total_cards(state))
        self.assertEqual(sum(1 for e in after.log if e["kind"] == "trainer_place_damage_counters"), 1)

    def test_counters_follow_the_effective_max_hp_after_entering(self):
        """のせる数は出したあとの今有効な最大HP の半分（今の対応カードのたねポケモンでは、印刷の HP の半分と同じ。第1弾の版は出す前のカードの HP）。"""
        pool = load_card_pool()
        for card_id in sorted(c for c in pool.playable_ids if pool.get(c).is_basic_pokemon)[:40]:
            with self.subTest(card=card_id):
                state = play(board([REVIVE_GYM], discard=[card_id]), REVIVE_GYM)
                after = answer(state, tuple(state.decision.options))
                pokemon = after.players[0].bench[-1]
                self.assertEqual(pokemon.damage, pool.get(card_id).hp // 20 * 10)
                self.assertEqual(pokemon.damage // 10, E.half_hp_counters(after, E.max_hp(after, pokemon)))

    def test_save_and_restore_while_waiting(self):
        import pickle

        state = play(board([REVIVE_GYM], discard=[HITMONCHAN]), REVIVE_GYM)
        self.assertIsNotNone(state.trainer_in_use)
        self.assertEqual(total_cards(state), total_cards(board([REVIVE_GYM], discard=[HITMONCHAN])))
        restored = pickle.loads(pickle.dumps(state))
        self.assertEqual(snapshot(restored), snapshot(state))
        a = answer(state, tuple(state.decision.options))
        b = answer(restored, tuple(restored.decision.options))
        self.assertEqual(snapshot(a), snapshot(b))
        self.assertIsNone(a.trainer_in_use)
        self.assertIn(uid(board([REVIVE_GYM]), REVIVE_GYM), a.players[0].discard)


# ---------------------------------------------------------------- プロモのリザードンの「ほのおのうず」


class FireSpinPromoTest(unittest.TestCase):
    """このカードについているエネルギーカードを2枚トラッシュする。(トラッシュできない時、このワザのダメージは0になる)"""

    def test_discards_two_cards_of_any_type_then_damage(self):
        state = board(active=charizard([FIRE, FIRE, FIRE, FIRE, DOUBLE_COLORLESS_ENERGY, WATER]))
        state = apply_kernel(state, UseAttack(0, 0))
        d = state.decision
        self.assertEqual((d.kind, d.min_choices, d.max_choices), (DISCARD_ENERGY, 2, 2))
        self.assertEqual(set(d.options), set(state.players[0].active.energy))  # どのタイプでも。無色2個エネルギーも 1 枚
        dce = next(u for u in d.options if state.cards[u].card_id == DOUBLE_COLORLESS_ENERGY)
        water = next(u for u in d.options if state.cards[u].card_id == WATER)
        since = len(state.log)
        after = audited(self, answer(state, (dce, water)))
        log = events(after, since)
        self.assertEqual([e["kind"] for e in log if e["kind"] in ("discard_energy", "damage")], ["discard_energy", "discard_energy", "damage"])
        self.assertEqual(log[[e["kind"] for e in log].index("damage")]["amount"], 100)
        self.assertEqual(len(after.players[0].active.energy), 4)
        self.assertTrue({dce, water} <= set(after.players[0].discard))

    def test_confusion_is_checked_before_the_discard(self):
        """トラッシュはワザの効果（こんらんのコインのあと）。第1弾の版の HC1 は当たらない。"""
        energy = [FIRE, FIRE, FIRE, FIRE]
        tails = apply_kernel(with_coin_results(board(active=charizard(energy, confusion=True)), T), UseAttack(0, 0))
        self.assertFalse(any(e["kind"] == "discard_energy" for e in tails.log))
        self.assertTrue(any(e["kind"] == "confusion_damage" for e in tails.log))
        heads = apply_kernel(with_coin_results(board(active=charizard(energy, confusion=True)), H), UseAttack(0, 0))
        self.assertEqual(heads.decision.kind, DISCARD_ENERGY)
        state = board(active={"card": CHARIZARD, "energy": energy, "evolved_from": [CHARMANDER, CHARMELEON], "evolved_turn": TURN - 2, "confusion": True})
        assert_rejected(self, state, UseAttack(0, 0), "UNRESOLVED_DISCARD_ENERGY_TIMING", UnsupportedError)

    def test_copied_with_one_card_deals_zero_without_discarding(self):
        """カスミのコダックの「ちょうのうりょく」（説明が条件を書かない）でこのワザを使い、エネルギーカードが 2 枚より少ない（超 1 枚）: 1 枚もトラッシュせず、ダメージは 0
        （ワザの失敗・使うための条件の違反ではない）。ピクシー（条件がたりなければ使えない）は HC9（v0.31 と同じ。選べるワザがこれだけなので宣言の前）。ピッピ（無色 3 つ）は 2 枚以上つく。"""
        state = with_coin_results(board(active={"card": MISTYS_PSYDUCK, "energy": [PSYCHIC]}, opponent=charizard([FIRE] * 4, player=1)), H, H, H)
        state = apply_kernel(state, UseAttack(0, 0))
        self.assertEqual((state.decision.kind, tuple(state.decision.options)), (SELECT_ATTACK, (0,)))
        since = len(state.log)
        after = audited(self, answer(state, (0,)))
        log = events(after, since)
        kinds = [e["kind"] for e in log]
        failed = log[kinds.index("discard_energy_failed")]
        self.assertEqual((failed["needed"], failed["attached"], failed["outcome"]), (2, 1, "zero"))
        self.assertNotIn("discard_energy", kinds)
        self.assertNotIn("attack_failed", kinds)
        self.assertFalse([e for e in log if e["kind"] == "damage" and e["amount"] > 0])
        self.assertEqual(len(after.players[0].active.energy), 1)
        state = board(active={"card": CLEFABLE, "energy": [PSYCHIC], "evolved_from": CLEFAIRY}, opponent=charizard([FIRE] * 4, player=1))
        assert_rejected(self, state, UseAttack(0, 0), "UNRESOLVED_COPIED_ATTACK", UnsupportedError)  # 選べるワザがこれだけなので宣言の前
        state = apply_kernel(board(active={"card": CLEFAIRY, "energy": [WATER, DOUBLE_COLORLESS_ENERGY]}, opponent=charizard([FIRE] * 4, player=1)), UseAttack(0, 1))
        self.assertEqual(answer(state, (0,)).decision.kind, DISCARD_ENERGY)

    def test_every_preflight_mode_gives_the_same_result(self):
        results = []
        for mode in PREFLIGHT_MODES:
            state = board(active=charizard([FIRE] * 5))
            state = apply_kernel(state, UseAttack(0, 0), preflight=mode)
            state = answer(state, tuple(state.decision.options[:2]), mode=mode)
            results.append(snapshot(state))
        self.assertTrue(all(r == results[0] for r in results))

    def test_invalid_answer_keeps_the_state(self):
        state = apply_kernel(board(active=charizard([FIRE] * 4)), UseAttack(0, 0))
        before = snapshot(state)
        for choices in ((state.decision.options[0],), tuple(state.decision.options[:3])):
            with self.subTest(choices=choices), self.assertRaises(IllegalActionError):
                answer(state, choices)
            self.assertEqual(snapshot(state), before)


# ---------------------------------------------------------------- 記録


class RecordTest(unittest.TestCase):

    def test_records_pass_and_point_to_the_original(self):
        self.assertEqual(cs.problems(), [])
        sources = cs.load_sources()["cards"]
        verification = json.loads((ROOT / "kyuura_engine" / "data" / "card_verification.json").read_text(encoding="utf-8"))["cards"]
        for new, original in REQUESTED.items():
            record = sources[new]
            with self.subTest(card=new):
                self.assertEqual((record["reprint_of"], record["status"], record["external_checks"], record["kyuura_records"]), (original, "adopted", [], []))
                self.assertEqual(record["recorded_on"], "2026-10-19")
                self.assertNotIn(new, verification)
                self.assertNotIn("equivalent_to", record)
                for target, scope in record.get("reprint_scope", {}).items():
                    self.assertEqual(record["play_text"][target], cs.REPRINT)
                    if original in verification:
                        self.assertEqual(scope["verification"], f"card_verification {original}")
        listed = {new: scope["listed_product"] for new, r in sources.items() if "reprint_of" in r for scope in r.get("reprint_scope", {}).values()}
        self.assertEqual(listed["GD1-016"], "ポケモンジム第1弾タケシ")
        self.assertEqual(listed["QSG-049"], "クイックスターターギフトパック")
        self.assertIsNone(listed["NIP1-015"])  # 2001 年のイントロパック★neo は、2000 年の本の収録の一覧にない
        self.assertEqual(listed["GD2-019"], "ポケモンジム第1弾カスミ")
        self.assertIsNone(listed["IPH-001"])  # フシギバナの照合の記録の収録は「ポケモンカード第1弾」だけ

    def test_scope_check_rejects_other_game_data(self):
        """登録の照合（名前・文面）が見ない欄（HP・必要なエネルギー・ダメージ・トレーナーの種類）が元のカードと違えば、記録の検査が拒否する（再録の関係の確かめ）。"""
        def hp(c):
            c["pokemon"]["hp"] = 50

        def cost(c):
            c["pokemon"]["attacks"][1]["cost"] = ["fighting"]
            c["pokemon"]["attacks"][1]["cost_total"] = 1

        def kinds(c):
            c["trainer"]["kinds"] = ["stadium"]

        def group(c):
            c["same_card_group"] = "SC-OTHER"

        for card_id, change in (("GD1-006", hp), ("GD1-006", cost), ("GD1-016", kinds), ("GD1-016", group)):
            with self.subTest(card=card_id, change=change.__name__):
                extract = copy.deepcopy(read_extract())
                change(next(c for c in extract["cards"] if c["id"] == card_id))
                self.assertTrue([p for p in cs.problems(extract=extract) if p.startswith(card_id)])

    def test_bad_records_are_rejected(self):
        base = cs.load_sources()

        def run(change):
            sources = copy.deepcopy(base)
            change(sources["cards"])
            return cs.problems(sources)

        cases = {
            "wrong original": lambda c: c["GD1-016"].update(reprint_of="PMCG1-073"),
            "printed basis for a reused text": lambda c: c["GD1-016"].update(play_text={"trainer": cs.PRINTED_TEXT}),
            "listed product changed": lambda c: c["GD1-016"]["reprint_scope"]["trainer"].update(listed_product=None),
            "records changed": lambda c: c["GD1-021"]["reprint_scope"]["trainer"].update(records=[]),
            "behavior missing": lambda c: c[ENERGY_SEARCH_GYM].update(behavior_differs=[]),
            "missing record": lambda c: c.pop(ENERGY_SEARCH_QSG),
            "scope quote missing": lambda c: c[CHARIZARD_PROMO]["reprint_scope"]["power/0"].pop("scope_quote"),
            "external check added": lambda c: c["GD1-016"]["external_checks"].append(copy.deepcopy(base["cards"][REVIVE]["external_checks"][0])),
        }
        for label, change in cases.items():
            with self.subTest(case=label):
                self.assertTrue(run(change))

    def test_research_links(self):
        links = json.loads((ROOT / "kyuura_engine" / "data" / "research_links.json").read_text(encoding="utf-8"))
        section = links["latest_descriptions"]
        self.assertEqual(set(section["reprint_registrations"]), {"IPH-001/power/0", "PR1-029/power/0", "IPH-002/attack/0", "IPH-002/power/0",
                                                                  "PR1-028/attack/0", "PR1-028/power/0", "PR1-030/power/0"})
        printed = {t for t in section["adopted_printed_text"] if t.split("/")[0] in POOL_V0_71}
        self.assertEqual(printed, {"GD1-006/attack/0", "GD1-006/attack/1", "GD4-004/attack/0", "GD4-004/power/0", "GD5-011/attack/0", "GD5-011/attack/1",
                                   "GD6-010/attack/0", "GD6-010/attack/1", "IP2-009/attack/0", "PR1-030/attack/0", "PR1-033/attack/0"})
        self.assertIn("GR-P43-P6-LATEST-DESCRIPTION", {r["kyuura_record"] for r in links["applied_rule_records"]})


class SecretPlanCandidatesTest(unittest.TestCase):
    """マチスの秘策の確かめで試すカードは、今までどおり公開の情報だけから作る（v0.71 で 572。上限 512 は変えない）。1 枚を指定するコマンドの試す回数は 247。"""

    def test_candidates(self):
        pool = load_card_pool()
        candidates = engine_module._identity_candidates(pool)
        basics = [c for c in candidates if pool.get(c).is_basic_pokemon]
        v072 = set(EXTRACT["pool_v0_72"]) | set(EXTRACT["pool_v0_73"])  # v0.72: 試すカードの数は固定しない（v0.72 の 43 枚・v0.73 の 18 枚を除いて比べる）
        self.assertEqual((len(set(candidates) - v072), len(set(basics) - v072)), (572, 245))
        self.assertEqual(engine_module._IDENTITY_TRIAL_LIMIT, 512)
        self.assertLessEqual(1 + len(basics) + 1, engine_module._IDENTITY_TRIAL_LIMIT)
        self.assertEqual(len(set(candidates) & set(POOL_V0_71)), 45)  # 同じデータの 33 枚は 1 枚で代表する


# ---------------------------------------------------------------- 正式な対戦開始からの対戦


class GameTest(unittest.TestCase):
    """正式な対戦開始（new_game・60 枚・サイド 6 枚）から、再録のカードと前の版のカードを混ぜたデッキ（tools/existing_effect_games.py の R71・G71・W71）。決まった seed・
    席の入れかえ。勝敗は判断に使わない。"""

    @classmethod
    def setUpClass(cls):
        from tools import existing_effect_games as games

        cls.games = games
        cls.results = games.run(range(2), pairings=games.PAIRINGS_V0_71)

    def test_games_finish_without_audit_failures(self):
        for name, run in self.results.items():
            for game in run["games"]:
                with self.subTest(run=name, seed=game["seed"]):
                    self.assertIn(game["outcome"], ("game_over", "sudden_death", "halted"), game.get("error"))
                    self.assertEqual(game["audit"], {})

    def test_decks_mix_reprints_and_earlier_ids(self):
        for label in ("R71", "G71", "W71"):
            deck = self.games.deck_cards(label)
            self.assertTrue(set(deck) & set(POOL_V0_71))
            self.assertTrue(set(deck) - set(POOL_V0_71))
            self.assertEqual(deck_problems(deck), [])
        r71 = self.games.deck_cards("R71")
        self.assertEqual(sum(r71.count(c) for c in (POKEDEX_GYM, POKEDEX_GYM5, POKEDEX)), 3)

    def test_behavior_different_cards_are_used(self):
        totals = {}
        for run in self.results.values():
            for game in run["games"]:
                for key, value in game.get("v071", {}).items():
                    totals[key] = totals.get(key, 0) + value
        for key in ("revive_bench", "revive_counters", "energy_search_reveal", "fire_spin_discard", "fire_spin_damage", "attack_PR1-030_0",
                    "trainer_GD1-017", "trainer_GD4-015"):
            with self.subTest(key=key):
                self.assertGreater(totals.get(key, 0), 0)


class DocumentTest(unittest.TestCase):
    def test_document(self):
        text = DOC.read_text(encoding="utf-8")
        for card_id in POOL_V0_71:
            self.assertIn(card_id, text)
        for word in ("REPRINT_CARDS", "SAME_NAME_SPELLINGS", "DiscardEnergyCardsThenDamageZeroIfLacking", "BenchBasicFromOwnDiscardThenCounters",
                     "reprint_scope", "GR-P43-P6-LATEST-DESCRIPTION", "572", "未確認"):
            self.assertIn(word, text)


if __name__ == "__main__":
    unittest.main()

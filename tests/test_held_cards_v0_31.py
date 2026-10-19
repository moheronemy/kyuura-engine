"""v0.31: v0.30 で保留した 22 枚と、その進化元として加えた 7 枚のカードごとのテスト（docs/held-cards-v0.31.md）。

- 写しのカードデータと登録（名前・照合用の文面・処理に使う文面・出典）が合うこと、22 枚が v0.30 の文書の 4 章の一覧と同じこと
- 29 枚がどれも対戦に使え（すべてのワザ・特殊能力に登録がある）、進化の系統がそろっていて、通常の進化の操作で進化できること
- すべてのワザ（52）と特殊能力（3）を、1 か所の規定を確かめる盤面（``build_test_state``）で 1 回以上使い、印刷の文面（または採用した最新の説明・
  エラッタ）のとおりの結果になること。ワザは、先読みの方法（``derived``・``derived_full``・``legacy``）のどれでも同じ結果・乱数になること

根拠（ガイドブックは読んでいない。2026-10-15 からのカードデータの方針）:

- kyuura の data/cards.json（写しの元 ecb2d69）の印刷の文面と、採用の記録（kyuura_engine/data/card_sources.json）。pcg-search.com との照合は
  同じ記録の external_checks。
- キュウコンの「だいもんじ」は kyuura の RUL-ENERGY-DISCARD-ATTACKS の最新の説明（記録の範囲として当てはめた。errata_scope）、リザードンの
  「エナジーバーン」は kyuura の TXT-CHARIZARD、ピッピの「ゆびをふる」は kyuura の data/curation/card_differences.json の PMCG1-067 の記録の
  最新の説明と解説（FOLLOW_TEXT）。わるいマルマインの「エナジーボム」の「とうめい」の扱いは kyuura の CR-TRANSPARENCY-ENERGY-BOMB。
- 一般の規定は既存の記録の再利用（p.309 のワザの手順・p.321 のダメージの計算・p.323 のワザの失敗・p.312 の効果で引く規定など）。

仕組みごとの決定・境界・原子性・持続する効果・特殊能力は tests/test_held_cards_v0_31_mechanisms.py、原典で決められない場合の止め方は
tests/test_held_cards_v0_31_stops.py、正式な対戦開始からの対戦は tests/test_held_cards_v0_31_games.py。
"""

from __future__ import annotations

import json
import pathlib
import re
import unittest

from kyuura_engine import EvolvePokemon, IllegalActionError, ResolveDecision, UseAttack, state_to_dict
from kyuura_engine import effects as E
from kyuura_engine.cards import load_card_pool, read_extract
from kyuura_engine.decisions import (
    ATTACH_FROM_DISCARD,
    ATTACH_TO_BENCH,
    DISCARD_ENERGY,
    DISCARD_OPPONENT_ENERGY,
    FORCED_SWITCH,
    RECOVER_TRAINER,
    SELECT_ATTACK,
    SELECT_POKEMON,
)
from kyuura_engine.resolution import PREFLIGHT_MODES
from kyuura_engine.rng import rng_fingerprint
from scripts import check_card_sources as cs
from tests.helpers import (
    BASE_GASTLY,
    BLAINES_ARCANINE,
    BLAINES_CHARMANDER,
    BLAINES_CHARMELEON,
    BLAINES_GROWLITHE,
    BLAINES_MAGMAR,
    BLAINES_NINETALES,
    BLAINES_VULPIX,
    BULBASAUR,
    CHARIZARD,
    CHARMANDER,
    CHARMELEON,
    CLEFABLE,
    CLEFAIRY,
    DARK_CHARIZARD,
    DARK_CHARMELEON,
    DARK_ELECTRODE,
    DARK_FLAREON,
    DARK_GOLDUCK,
    DARK_RAPIDASH,
    EEVEE,
    FIGHTING,
    FIRE,
    GRASS,
    HITMONCHAN,
    LIGHTNING,
    LT_SURGES_ELECTABUZZ,
    LT_SURGES_PIKACHU,
    LT_SURGES_RAICHU,
    MEWTWO,
    MISTYS_GOLDUCK,
    MISTYS_PSYDUCK,
    MOLTRES,
    PLUSPOWER,
    POTION,
    PSYCHIC,
    PSYDUCK,
    RATTATA,
    ROCKET_PONYTA,
    ROCKET_VOLTORB,
    SLOWPOKE,
    V0_31_DEPENDENCIES,
    V0_31_POKEMON,
    V0_31_TARGETS,
    VULPIX,
    WATER,
    ZAPDOS,
    NINETALES,
    H,
    T,
    apply_kernel,
    build_test_state,
    with_coin_results,
)

ROOT = pathlib.Path(__file__).resolve().parent.parent
TURN = 7
PRINTED = cs.PRINTED_TEXT_SOURCE
# 進化しているカードの下のカード（たねポケモン、または [たね, 1 進化]）
BELOW = {
    NINETALES: VULPIX, CHARIZARD: [CHARMANDER, CHARMELEON], CLEFABLE: CLEFAIRY, DARK_RAPIDASH: ROCKET_PONYTA,
    DARK_CHARMELEON: CHARMANDER, DARK_FLAREON: EEVEE, DARK_CHARIZARD: [CHARMANDER, DARK_CHARMELEON], DARK_GOLDUCK: PSYDUCK,
    DARK_ELECTRODE: ROCKET_VOLTORB, MISTYS_GOLDUCK: MISTYS_PSYDUCK, BLAINES_CHARMELEON: BLAINES_CHARMANDER,
    BLAINES_NINETALES: BLAINES_VULPIX, BLAINES_ARCANINE: BLAINES_GROWLITHE, LT_SURGES_RAICHU: LT_SURGES_PIKACHU,
}
# 処理に使う文面が印刷の文面でないもの: (カード id, 種類, 位置) → 出典
NOT_PRINTED = {
    (NINETALES, "attack", 1): "RUL-ENERGY-DISCARD-ATTACKS",
    (CHARIZARD, "power", 0): "TXT-CHARIZARD",
    (CLEFAIRY, "attack", 1): "kyuura data/curation/card_differences.json#PMCG1-067",
}


def mon(card, energy=(), **extra):
    spec = {"card": card, "energy": list(energy), **extra}
    if card in BELOW and "evolved_from" not in spec:
        spec["evolved_from"] = BELOW[card]
    return spec


def board(active, opponent=None, *, bench=(), opponent_bench=(RATTATA,), hand=(), discard=(), deck=None, opponent_deck=None,
          opponent_discard=()):
    me = {"active": active, "bench": list(bench), "hand": list(hand), "discard": list(discard)}
    if deck is not None:
        me["deck"] = list(deck)
    them = {"active": opponent or mon(HITMONCHAN, (FIGHTING,)), "bench": list(opponent_bench), "discard": list(opponent_discard)}
    if opponent_deck is not None:
        them["deck"] = list(opponent_deck)
    return build_test_state([me, them], turn_number=TURN)


def full(state):
    return state_to_dict(state, format_version=10)


def play(state, command, answers=(), *, mode="derived"):
    """コマンドを処理し、決定には ``answers`` の順に答える（関数なら決定を受け取って選んだものを返す）。最後の状態を返す。"""
    state = apply_kernel(state, command, preflight=mode)
    for answer in answers:
        d = state.decision
        assert d is not None, "決定がない"
        choice = answer(d) if callable(answer) else tuple(answer)
        state = apply_kernel(state, ResolveDecision(d.player, d.id, choice), preflight=mode)
    return state


def events(state, since, kind=None):
    return [dict(e) for e in state.log[since:] if kind is None or e["kind"] == kind]


def dealt(state, since):
    """そのあとのログで、相手の対戦ポケモンが受けた最終ダメージの並び（きぜつして場を離れても数えられる）。"""
    return [e["amount"] for e in state.log[since:] if e["kind"] == "damage" and "target" not in e and e["player"] == 1]


def first(n=1):
    return lambda d: tuple(d.options[:n])


def last(n=1):
    return lambda d: tuple(d.options[-n:])


class CardDataTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.pool = load_card_pool()
        cls.copy = {c["id"]: c for c in read_extract()["cards"]}

    def test_targets_are_the_cards_held_in_v0_30(self):
        """対象の 22 枚は、v0.30 の文書の 4 章（保留したカード）に挙げた 22 枚と同じ。進化元として加えた 7 枚は対象と重ならない。"""
        text = (ROOT / "docs" / "discard-energy-attacks-v0.30.md").read_text(encoding="utf-8")
        chapter = text.split("\n## 4", 1)[1].split("\n## 5", 1)[0]
        held = set(re.findall(r"PMCG\d-\d{3}", chapter))
        self.assertEqual(set(V0_31_TARGETS), held)
        self.assertEqual(len(V0_31_TARGETS), 22)
        self.assertEqual(len(V0_31_DEPENDENCIES), 7)
        self.assertFalse(set(V0_31_TARGETS) & set(V0_31_DEPENDENCIES))
        self.assertEqual(list(V0_31_POKEMON), read_extract()["pool_v0_31"])

    def test_every_card_attack_and_power_is_supported(self):
        """29 枚がどれも対戦に使える（すべてのワザ・特殊能力に登録があり、データと合う。ワザ単位でなくカード単位で対応）。"""
        for card_id in V0_31_POKEMON:
            definition = self.pool.get(card_id)
            with self.subTest(card=card_id):
                self.assertTrue(self.pool.is_playable(card_id))
                self.assertTrue(definition.supported)
                self.assertTrue(all(attack.supported for attack in definition.attacks))
                for power in definition.powers:
                    self.assertIsNotNone(E.DEFAULT_EFFECTS.power_effect(card_id, power))
        attacks = sum(len(self.pool.get(c).attacks) for c in V0_31_POKEMON)
        powers = sum(len(self.pool.get(c).powers) for c in V0_31_POKEMON)
        self.assertEqual((attacks, powers), (52, 3))

    def test_registrations_follow_the_copy(self):
        """登録の名前・照合用の文面は写しと同じ。処理に使う文面は、記録のある 3 つ（エラッタ・card_differences）を除いて印刷の文面と同じで、
        出典は ``kyuura data/cards.json``（説明文のないワザは文面なし）。"""
        for card_id in V0_31_POKEMON:
            card = self.copy[card_id]["pokemon"]
            for index, attack in enumerate(card["attacks"]):
                entry = E.DEFAULT_EFFECTS.attack_entry(card_id, index)
                with self.subTest(card=card_id, attack=index):
                    self.assertEqual(entry.name_ja, attack["name"]["ja"])
                    text = (attack.get("text") or {}).get("ja")
                    self.assertEqual(entry.text_ja, text)
                    expected = NOT_PRINTED.get((card_id, "attack", index))
                    if text is None:
                        self.assertIsNone(entry.play_text_ja)
                    elif expected is None:
                        self.assertEqual((entry.play_text_ja, entry.source), (text, PRINTED))
                    else:
                        self.assertNotEqual(entry.play_text_ja, text)
                        self.assertEqual(entry.source.split(" ")[0] if expected.startswith("RUL") else entry.source, expected)
            for index, power in enumerate(card.get("powers", [])):
                entry = E.DEFAULT_EFFECTS.power_entry(card_id, index)
                with self.subTest(card=card_id, power=index):
                    self.assertEqual(entry.name_ja, power["name"]["ja"])
                    self.assertEqual(entry.text_ja, power["text"]["ja"])
                    expected = NOT_PRINTED.get((card_id, "power", index))
                    self.assertEqual(entry.source, expected or PRINTED)
                    self.assertEqual(entry.play_text_ja == entry.text_ja, expected is None)

    def test_adoption_records(self):
        """29 枚どれも、kyuura データの採用の記録（``adopted``）を持ち、過去の原典照合の記録（card_verification.json）には入れない。
        pcg-search.com との照合（対象の版の一覧の番号・結果）が 1 つあり、見つけた違いはどれも挙動に影響しない（kyuura への報告事項）。"""
        records = json.loads((ROOT / "kyuura_engine" / "data" / "card_sources.json").read_text(encoding="utf-8"))["cards"]
        verification = json.loads((ROOT / "kyuura_engine" / "data" / "card_verification.json").read_text(encoding="utf-8"))
        self.assertTrue(set(V0_31_POKEMON) <= set(records))
        self.assertFalse(set(V0_31_POKEMON) & set(verification["cards"]))
        for card_id in V0_31_POKEMON:
            record = records[card_id]
            with self.subTest(card=card_id):
                self.assertEqual((record["basis"], record["status"], record["kyuura_commit"]),
                                 ("kyuura_data", "adopted", read_extract()["previous_source"]["commit"]))  # v0.69: 採用したときのデータのコミット
                [check] = record["external_checks"]
                self.assertEqual(check["site"], "pcg-search.com")
                self.assertTrue(check["url"].startswith("https://pcg-search.com/"))
                self.assertRegex(check["edition"]["list_number"], r"^\d{3}/\d{3}$")
                self.assertIn(check["result"], ("match", "differences"))
                self.assertTrue(all(not d["affects_behavior"] for d in check.get("differences", ())))

    def test_evolution_lines(self):
        """進化しているカードは、写しの「○○から進化」の名前の進化元が写しにあって対戦に使える（進化元として 7 枚を加えた。ほかの進化元は
        v0.30 までに対応）。7 枚はどれも、対象のカードの進化元。"""
        names = {}
        for card_id in self.pool.playable_ids:
            names.setdefault(self.pool.get(card_id).name_ja, set()).add(card_id)
        for card_id in V0_31_TARGETS:
            definition = self.pool.get(card_id)
            if definition.stage == "basic":
                continue
            below = BELOW[card_id]
            parent = below[-1] if isinstance(below, list) else below
            with self.subTest(card=card_id):
                self.assertEqual(self.pool.get(parent).name_ja, definition.evolves_from)
                self.assertTrue(self.pool.is_playable(parent))
        parents = {(BELOW[c][0] if isinstance(BELOW[c], list) else BELOW[c]) for c in BELOW}
        self.assertTrue(set(V0_31_DEPENDENCIES) <= parents)

    def test_evolve_with_the_normal_command(self):
        """1 進化・2 進化のカードは、通常の進化の操作（``EvolvePokemon``）で進化できる（p.310。系統の名前が合う）。"""
        for card_id, below in BELOW.items():
            stack = below if isinstance(below, list) else [below]
            spec = {"card": stack[-1], "energy": []}
            if len(stack) > 1:
                spec["evolved_from"] = stack[0]
                spec["evolved_turn"] = 3
            state = build_test_state([{"active": spec, "hand": [card_id]}, {"active": HITMONCHAN}], turn_number=TURN)
            target = state.players[0].active
            with self.subTest(card=card_id):
                new = apply_kernel(state, EvolvePokemon(0, state.players[0].hand[0], target.pokemon_id))
                self.assertEqual(new.card_def(new.players[0].active.card).id, card_id)
                self.assertEqual(new.players[0].active.pokemon_id, target.pokemon_id)


class AttackTest(unittest.TestCase):
    """すべてのワザを 1 回以上使う。先読みの方法のどれでも、同じ結果（形式 10 の書き出し）・乱数・ログになる。"""

    def run_all_modes(self, state, command, answers=()):
        results = [play(state, command, answers, mode=mode) for mode in PREFLIGHT_MODES]
        for mode, other in zip(PREFLIGHT_MODES[1:], results[1:]):
            with self.subTest(mode=mode):
                self.assertEqual(full(other), full(results[0]))
                self.assertEqual(rng_fingerprint(other.rng), rng_fingerprint(results[0].rng))
        return results[0]

    def damage_log(self, state, since):
        return [(e["total_damage"] if "total_damage" in e else None, e.get("damage"), e.get("target", "opponent_active"))
                for e in events(state, since, "damage")]

    def opp(self, state):
        return state.players[1].active

    # ---- 1 枚目: キュウコン・リザードン・サンダー・ゴース・ミュウツー

    def test_ninetales(self):
        """かどわかす: ワザを使ったプレイヤーが相手の控えを選び、相手の対戦ポケモンと入れ替える。だいもんじ: 炎 1 枚を選んでトラッシュ → 80。"""
        state = board(mon(NINETALES, (FIRE, FIRE)), opponent_bench=(RATTATA, BULBASAUR))
        bench = [p.pokemon_id for p in state.players[1].bench]
        new = self.run_all_modes(state, UseAttack(0, 0), [lambda d: (self.assertEqual((d.kind, d.player, tuple(d.options)),
                                                                                       (FORCED_SWITCH, 0, tuple(bench))), (bench[1],))[1]])
        self.assertEqual(self.opp(new).pokemon_id, bench[1])
        self.assertEqual([e["kind"] for e in events(new, len(state.log)) if e["kind"] in ("damage", "forced_switch")], ["forced_switch"])
        state = board(mon(NINETALES, (FIRE, FIRE, FIRE, FIRE)), opponent=mon(HITMONCHAN))
        new = self.run_all_modes(state, UseAttack(0, 1), [first()])
        self.assertEqual((dealt(new, len(state.log)), len(new.players[0].active.energy)), ([80], 3))

    def test_charizard_fire_spin(self):
        """ほのおのうず: エネルギーカード（タイプを問わない）を 2 枚選んでトラッシュ → 100。"""
        state = board(mon(CHARIZARD, (FIRE, FIRE, FIRE, FIRE, WATER)), opponent=mon(HITMONCHAN))
        new = self.run_all_modes(state, UseAttack(0, 0), [lambda d: (self.assertEqual((d.kind, d.min_choices, d.max_choices, len(d.options)),
                                                                                       (DISCARD_ENERGY, 2, 2, 5)), (d.options[0], d.options[4]))[1]])
        self.assertEqual((dealt(new, len(state.log)), len(new.players[0].active.energy), len(new.players[0].discard)), ([100], 3, 2))

    def test_zapdos(self):
        """かみなり: 60、「うら」なら自分にも 30（抵抗力 闘 のサンダーに自分のタイプ 雷 の 30）。10まんボルト: エネルギーカードをすべてトラッシュ（決定なし）→ 100。"""
        energy = (LIGHTNING, LIGHTNING, LIGHTNING, LIGHTNING)
        for coin, self_damage in ((H, 0), (T, 30)):
            state = with_coin_results(board(mon(ZAPDOS, energy), opponent=mon(HITMONCHAN)), coin)
            new = self.run_all_modes(state, UseAttack(0, 0))
            self.assertEqual((self.opp(new).damage, new.players[0].active.damage), (60, self_damage))
        state = board(mon(ZAPDOS, energy), opponent=mon(HITMONCHAN))
        new = self.run_all_modes(state, UseAttack(0, 1))
        self.assertNotEqual(new.decision and new.decision.kind, DISCARD_ENERGY)  # すべてトラッシュするので選ばない
        self.assertEqual((dealt(new, len(state.log)), new.players[0].active.energy), ([100], []))
        self.assertEqual(len([e for e in events(new, len(state.log), "discard_energy")]), 4)

    def test_base_gastly(self):
        """さいみんガス: 「おもて」ならねむり、「うら」なら何もしない。みちづれ: 超 1 枚を選んでトラッシュ → 自分に「みちづれ」の持続する効果
        （次の相手の番。相手の番の処理は仕組みのテスト）。"""
        for coin, asleep in ((H, True), (T, False)):
            new = self.run_all_modes(with_coin_results(board(mon(BASE_GASTLY, (PSYCHIC,))), coin), UseAttack(0, 0))
            self.assertEqual(self.opp(new).conditions.asleep, asleep)
        state = board(mon(BASE_GASTLY, (PSYCHIC, PSYCHIC)))
        new = self.run_all_modes(state, UseAttack(0, 1), [first()])
        gastly = new.players[0].active
        self.assertEqual([type(e).__name__ for e in gastly.persistent_effects], ["DestinyBond"])
        self.assertEqual((len(gastly.energy), gastly.persistent_effects[0].active_turn), (1, TURN + 1))

    def test_mewtwo(self):
        """サイコキネシス: 10 + 相手についているエネルギーカード × 10。バリアー: 超 1 枚を選んでトラッシュ → 「ワザをうけない」持続する効果。"""
        for count in (0, 1, 3):
            state = board(mon(MEWTWO, (PSYCHIC, PSYCHIC)), opponent=mon(HITMONCHAN, (FIGHTING,) * count))
            new = self.run_all_modes(state, UseAttack(0, 0))
            self.assertEqual(dealt(new, len(state.log)), [(10 + 10 * count) * 2])  # エビワラーの弱点 超
        new = self.run_all_modes(board(mon(MEWTWO, (PSYCHIC, PSYCHIC))), UseAttack(0, 1), [first()])
        self.assertEqual([type(e).__name__ for e in new.players[0].active.persistent_effects], ["AttackBarrier"])
        self.assertEqual(len(new.players[0].active.energy), 1)

    # ---- ピクシー・ピッピ（ゆびをふる）

    def test_clefable_and_clefairy_metronome(self):
        """ゆびをふる: 相手の対戦ポケモンのワザを選び（ワザを使ったプレイヤー）、自分のワザとして使う。必要なエネルギーはいらない。弱点・抵抗力は
        ワザを使ったポケモン（無色）のタイプで計算する。"""
        for card, index, energy in ((CLEFABLE, 0, (FIRE,)), (CLEFAIRY, 1, (FIRE, FIRE, FIRE))):
            state = board(mon(card, energy), opponent=mon(HITMONCHAN))
            with self.subTest(card=card):
                new = self.run_all_modes(state, UseAttack(0, index), [
                    lambda d: (self.assertEqual((d.kind, d.player, tuple(d.options), d.context_value("copy_from")),
                                                (SELECT_ATTACK, 0, (0, 1), HITMONCHAN)), (1,))[1]])
                self.assertEqual(self.opp(new).damage, 40)  # エビワラーの「スペシャルパンチ」（闘闘無）40
                copied = events(new, len(state.log), "copy_attack")
                self.assertEqual([e["copied"] for e in copied], [f"{HITMONCHAN}#1"])

    def test_clefable_minimize_and_clefairy_sing(self):
        """ちいさくなる: 次の相手の番に受けるダメージが 20 へる持続する効果。うたう: 「おもて」ならねむり。"""
        new = self.run_all_modes(board(mon(CLEFABLE, (FIRE, FIRE))), UseAttack(0, 1))
        effects = new.players[0].active.persistent_effects
        self.assertEqual([(type(e).__name__, e.amount) for e in effects], [("DamageReduction", 20)])
        for coin, asleep in ((H, True), (T, False)):
            new = self.run_all_modes(with_coin_results(board(mon(CLEFAIRY, (FIRE,))), coin), UseAttack(0, 0))
            self.assertEqual(self.opp(new).conditions.asleep, asleep)

    # ---- 化石の秘密: ファイヤー・ヤドン

    def test_moltres(self):
        """やまやき: 炎を好きなだけ（1 枚以上）選んでトラッシュ → 同じ枚数を相手の山札の上からトラッシュ。ゴッドバード: 「うら」なら失敗（ダメージなし・
        番は終わる）、「おもて」なら 80。"""
        state = board(mon(MOLTRES, (FIRE, FIRE, FIRE)), opponent_deck=[WATER, GRASS, FIGHTING, FIRE])
        top = state.players[1].deck[:2]
        new = self.run_all_modes(state, UseAttack(0, 0), [
            lambda d: (self.assertEqual((d.kind, d.min_choices, d.max_choices), (DISCARD_ENERGY, 0, 3)), tuple(d.options[:2]))[1]])
        self.assertEqual((len(new.players[0].active.energy), new.players[1].deck[:2] != top, new.players[1].discard), (1, True, top))
        energy = (FIRE, FIRE, FIRE, FIRE)
        for coin, damage in ((H, 80), (T, 0)):
            state = with_coin_results(board(mon(MOLTRES, energy), opponent=mon(HITMONCHAN)), coin)
            new = self.run_all_modes(state, UseAttack(0, 1))
            self.assertEqual(dealt(new, len(state.log)), [damage] if damage else [])
            self.assertEqual(len(events(new, len(state.log), "attack_failed")), 1 if coin is T else 0)
            if coin is T:
                self.assertEqual(new.current_player, 1)  # 失敗してもワザを使ったことになり、番は終わる（p.323）

    def test_slowpoke(self):
        """ぼーっとする: ダメージカウンターがなければ使えない（拒否）。「おもて」なら 1 つとりのぞく。ゴミあさり: 超 1 枚をトラッシュし、トラッシュの
        トレーナーを 1 枚選んで手札に加える（トレーナーがなければ何もしない）。"""
        state = board(mon(SLOWPOKE, (PSYCHIC,)))
        with self.assertRaises(IllegalActionError) as ctx:
            apply_kernel(state, UseAttack(0, 0))
        self.assertEqual(ctx.exception.code, "NO_DAMAGE_COUNTERS")
        for coin, after in ((H, 10), (T, 20)):
            new = self.run_all_modes(with_coin_results(board(mon(SLOWPOKE, (PSYCHIC,), damage=20)), coin), UseAttack(0, 0))
            self.assertEqual(new.players[0].active.damage, after)
        state = board(mon(SLOWPOKE, (PSYCHIC, PSYCHIC)), discard=(POTION, FIRE, PLUSPOWER))
        trainers = [uid for uid in state.players[0].discard if state.card_def(uid).category == "trainer"]
        new = self.run_all_modes(state, UseAttack(0, 1), [first(), lambda d: (self.assertEqual(
            (d.kind, tuple(d.options)), (RECOVER_TRAINER, tuple(trainers))), (trainers[1],))[1]])
        self.assertIn(trainers[1], new.players[0].hand)
        self.assertEqual(len(new.players[0].active.energy), 1)
        new = self.run_all_modes(board(mon(SLOWPOKE, (PSYCHIC, PSYCHIC)), discard=(FIRE,)), UseAttack(0, 1), [first()])
        self.assertIsNone(new.decision)
        self.assertEqual(new.players[0].hand, [])

    # ---- ロケット団: わるいギャロップ・わるいリザード・わるいブースター・わるいリザードン・わるいゴルダック・わるいマルマイン・コダック

    def test_dark_rapidash(self):
        """うしろげり 20。ひばしら: 30 のあと、のぞむなら炎 1 枚をトラッシュして相手の控えを 1 匹選び 10（弱点・抵抗力に関係なく）。のぞまなければ何もしない。"""
        new = self.run_all_modes(board(mon(DARK_RAPIDASH, (FIRE, FIRE)), opponent=mon(HITMONCHAN)), UseAttack(0, 0))
        self.assertEqual(self.opp(new).damage, 20)
        state = board(mon(DARK_RAPIDASH, (FIRE, FIRE)), opponent=mon(HITMONCHAN), opponent_bench=(RATTATA, BULBASAUR))
        bench = [p.pokemon_id for p in state.players[1].bench]
        new = self.run_all_modes(state, UseAttack(0, 1), [
            lambda d: (self.assertEqual((d.kind, d.min_choices, d.max_choices), (DISCARD_ENERGY, 0, 1)), (d.options[0],))[1],
            lambda d: (self.assertEqual((d.kind, d.player, tuple(d.options)), (SELECT_POKEMON, 0, tuple(bench))), (bench[1],))[1]])
        self.assertEqual((self.opp(new).damage, [p.damage for p in new.players[1].bench]), (30, [0, 10]))
        self.assertEqual(len(new.players[0].active.energy), 1)
        new = self.run_all_modes(state, UseAttack(0, 1), [()])
        self.assertEqual((self.opp(new).damage, [p.damage for p in new.players[1].bench], len(new.players[0].active.energy)), (30, [0, 0], 2))

    def test_dark_charmeleon(self):
        """しっぽでたたく 20。ファイヤーボール: 「うら」なら失敗、「おもて」なら炎 1 枚を選んでトラッシュ → 70。"""
        new = self.run_all_modes(board(mon(DARK_CHARMELEON, (FIRE, FIRE)), opponent=mon(HITMONCHAN)), UseAttack(0, 0))
        self.assertEqual(self.opp(new).damage, 20)
        state = with_coin_results(board(mon(DARK_CHARMELEON, (FIRE, FIRE, FIRE)), opponent=mon(HITMONCHAN)), H)
        new = self.run_all_modes(state, UseAttack(0, 1), [first()])
        self.assertEqual((dealt(new, len(state.log)), len(new.players[0].active.energy)), ([70], 2))
        state = with_coin_results(board(mon(DARK_CHARMELEON, (FIRE, FIRE, FIRE)), opponent=mon(HITMONCHAN)), T)
        new = self.run_all_modes(state, UseAttack(0, 1))
        self.assertEqual((self.opp(new).damage, len(new.players[0].active.energy)), (0, 3))
        self.assertEqual(len(events(new, len(state.log), "attack_failed")), 1)

    def test_dark_flareon(self):
        """いかり: 10 + 自分のダメージカウンター × 10。ひあそび: 「おもて」なら +20 と炎 1 枚のトラッシュ、「うら」なら 30 だけ。"""
        for damage in (0, 30):
            state = board(mon(DARK_FLAREON, (FIRE,), damage=damage), opponent=mon(HITMONCHAN))
            self.assertEqual(self.opp(self.run_all_modes(state, UseAttack(0, 0))).damage, 10 + damage)
        state = with_coin_results(board(mon(DARK_FLAREON, (FIRE, FIRE)), opponent=mon(HITMONCHAN)), H)
        new = self.run_all_modes(state, UseAttack(0, 1), [first()])
        self.assertEqual((self.opp(new).damage, len(new.players[0].active.energy)), (50, 1))
        state = with_coin_results(board(mon(DARK_FLAREON, (FIRE, FIRE)), opponent=mon(HITMONCHAN)), T)
        new = self.run_all_modes(state, UseAttack(0, 1))
        self.assertEqual((self.opp(new).damage, len(new.players[0].active.energy)), (30, 2))

    def test_dark_charizard(self):
        """つめではじく 10。れんぞくファイヤーボール: 炎の枚数ぶんのコインで「おもて」の数 × 50、その後「おもて」の数の炎をトラッシュ（決定はちょうどその数）。"""
        new = self.run_all_modes(board(mon(DARK_CHARIZARD, (FIRE,)), opponent=mon(HITMONCHAN, damage=0)), UseAttack(0, 0))
        self.assertEqual(self.opp(new).damage, 10)
        state = with_coin_results(board(mon(DARK_CHARIZARD, (FIRE, FIRE, FIRE)), opponent=mon(HITMONCHAN)), H, T, H)
        new = self.run_all_modes(state, UseAttack(0, 1), [
            lambda d: (self.assertEqual((d.kind, d.min_choices, d.max_choices), (DISCARD_ENERGY, 2, 2)), tuple(d.options[:2]))[1]])
        self.assertEqual((dealt(new, len(state.log)), len(new.players[0].active.energy)), ([100], 1))
        state = with_coin_results(board(mon(DARK_CHARIZARD, (FIRE, FIRE)), opponent=mon(HITMONCHAN)), T, T)
        new = self.run_all_modes(state, UseAttack(0, 1))
        self.assertEqual((self.opp(new).damage, len(new.players[0].active.energy), new.decision), (0, 2, None))

    def test_dark_golduck(self):
        """だい3のめ: エネルギーカード（タイプを問わない）を 1 枚選んでトラッシュ → 山札から 3 枚引く（足りなければ引けるだけ）。ちょうねんりき 50。"""
        state = board(mon(DARK_GOLDUCK, (PSYCHIC, WATER)), deck=[FIRE, WATER, GRASS, FIGHTING])
        top = state.players[0].deck[:3]
        new = self.run_all_modes(state, UseAttack(0, 0), [lambda d: (self.assertEqual(len(d.options), 2), (d.options[1],))[1]])
        self.assertEqual((new.players[0].hand, len(new.players[0].active.energy)), (top, 1))
        state = board(mon(DARK_GOLDUCK, (PSYCHIC,)), deck=[FIRE])
        new = self.run_all_modes(state, UseAttack(0, 0), [first()])
        self.assertEqual((len(new.players[0].hand), new.players[0].deck), (1, []))
        new = self.run_all_modes(board(mon(DARK_GOLDUCK, (PSYCHIC, PSYCHIC, PSYCHIC)), opponent=mon(HITMONCHAN)), UseAttack(0, 1))
        self.assertEqual(self.opp(new).damage, 50)

    def test_dark_electrode(self):
        """ころがりタックル 10。エナジーボム: 30 のあと、ついているエネルギーカードをすべて、1 枚ずつ自分の控えに選んでつける（控えがいなければトラッシュ）。"""
        new = self.run_all_modes(board(mon(DARK_ELECTRODE, (LIGHTNING,)), opponent=mon(HITMONCHAN)), UseAttack(0, 0))
        self.assertEqual(self.opp(new).damage, 10)
        state = board(mon(DARK_ELECTRODE, (LIGHTNING, LIGHTNING, FIRE)), opponent=mon(HITMONCHAN), bench=(RATTATA, BULBASAUR))
        energy = list(state.players[0].active.energy)
        bench = [p.pokemon_id for p in state.players[0].bench]
        new = self.run_all_modes(state, UseAttack(0, 1), [
            lambda d: (self.assertEqual((d.kind, tuple(d.options), d.context_value("energy")), (ATTACH_TO_BENCH, tuple(bench), energy[0])),
                       (bench[0],))[1], (bench[1],), (bench[1],)])
        self.assertEqual((self.opp(new).damage, new.players[0].active.energy), (30, []))
        self.assertEqual([p.energy for p in new.players[0].bench], [[energy[0]], energy[1:]])
        new = self.run_all_modes(board(mon(DARK_ELECTRODE, (LIGHTNING, LIGHTNING)), opponent=mon(HITMONCHAN)), UseAttack(0, 1))
        self.assertEqual((new.players[0].active.energy, len(new.players[0].discard), new.decision), ([], 2, None))

    def test_psyduck(self):
        """めまい: 山札から 1 枚引く。みずでっぽう: 多い水エネルギーがない（読み方で数が変わらない）なら 20（多いときは HC4。止め方のテスト）。"""
        state = board(mon(PSYDUCK, (PSYCHIC,)))
        new = self.run_all_modes(state, UseAttack(0, 0))
        self.assertEqual(new.players[0].hand, state.players[0].deck[:1])
        new = self.run_all_modes(board(mon(PSYDUCK, (WATER, FIRE)), opponent=mon(HITMONCHAN)), UseAttack(0, 1))
        self.assertEqual(self.opp(new).damage, 20)

    # ---- リーダーズスタジアム: カスミのゴルダック・カスミのコダック・マチスのエレブー・マチスのピカチュウ

    def test_mistys_golduck(self):
        """エクストラビーム: 40、「うら」なら自分のエネルギーカードをすべてトラッシュ。スーパーデストロイ: 「おもて」なら相手と相手の控え全員から、それぞれ
        エネルギーカードを 1 枚ずつ（ワザを使ったプレイヤーが）選んでトラッシュ（エネルギーのないポケモンは飛ばす）。"""
        for coin, left in ((H, 2), (T, 0)):
            state = with_coin_results(board(mon(MISTYS_GOLDUCK, (WATER, PSYCHIC)), opponent=mon(HITMONCHAN)), coin)
            new = self.run_all_modes(state, UseAttack(0, 0))
            self.assertEqual((self.opp(new).damage, len(new.players[0].active.energy)), (40, left))
        state = with_coin_results(board(mon(MISTYS_GOLDUCK, (WATER, PSYCHIC)), opponent=mon(HITMONCHAN, (FIGHTING, FIGHTING)),
                                        opponent_bench=(mon(RATTATA, (FIRE,)), RATTATA, mon(BULBASAUR, (GRASS, GRASS)))), H)
        targets = [state.players[1].active.pokemon_id, state.players[1].bench[0].pokemon_id, state.players[1].bench[2].pokemon_id]
        seen = []

        def pick(d):
            self.assertEqual((d.kind, d.player), (DISCARD_OPPONENT_ENERGY, 0))
            seen.append(d.context_value("target"))
            return (d.options[0],)

        new = self.run_all_modes(state, UseAttack(0, 1), [pick, pick, pick])
        self.assertEqual(seen[:3], targets)
        self.assertEqual([len(p.energy) for p in [new.players[1].active, *new.players[1].bench]], [1, 0, 0, 1])
        state = with_coin_results(board(mon(MISTYS_GOLDUCK, (WATER, PSYCHIC)), opponent=mon(HITMONCHAN, (FIGHTING,))), T)
        new = self.run_all_modes(state, UseAttack(0, 1))
        self.assertEqual((len(self.opp(new).energy), new.decision), (1, None))

    def test_mistys_psyduck(self):
        """ちょうのうりょく: コイン 3 枚の「おもて」が 1 枚なら 1 枚引く、2 枚なら相手に 20、3 枚なら相手のワザを選んで自分のワザとして使う、0 枚なら何もしない。"""
        cases = {(T, T, T): (0, 0), (H, T, T): (0, 1), (H, H, T): (20, 0)}
        for coins, (damage, drawn) in cases.items():
            state = with_coin_results(board(mon(MISTYS_PSYDUCK, (PSYCHIC,)), opponent=mon(HITMONCHAN)), *coins)
            new = self.run_all_modes(state, UseAttack(0, 0))
            self.assertEqual((self.opp(new).damage, len(new.players[0].hand)), (damage, drawn))
        state = with_coin_results(board(mon(MISTYS_PSYDUCK, (PSYCHIC,)), opponent=mon(HITMONCHAN)), H, H, H)
        new = self.run_all_modes(state, UseAttack(0, 0), [lambda d: (self.assertEqual(d.kind, SELECT_ATTACK), (0,))[1]])
        self.assertEqual(self.opp(new).damage, 20)  # エビワラーの「ジャブ」（闘）20

    def test_lt_surges_electabuzz(self):
        """たいでん: トラッシュの雷を最大 2 枚選んで自分につける（なければ何もしない）。ほうでん: 雷をすべてトラッシュ → その枚数のコインで「おもて」× 30。"""
        state = board(mon(LT_SURGES_ELECTABUZZ, (LIGHTNING,)), discard=(LIGHTNING, FIRE, LIGHTNING, LIGHTNING))
        candidates = [uid for uid in state.players[0].discard if state.card_def(uid).id == LIGHTNING]
        new = self.run_all_modes(state, UseAttack(0, 0), [
            lambda d: (self.assertEqual((d.kind, d.min_choices, d.max_choices, tuple(d.options)), (ATTACH_FROM_DISCARD, 0, 2, tuple(candidates))),
                       (candidates[2], candidates[0]))[1]])
        self.assertEqual(new.players[0].active.energy[1:], [candidates[0], candidates[2]])  # トラッシュの並びの順につける
        new = self.run_all_modes(board(mon(LT_SURGES_ELECTABUZZ, (LIGHTNING,)), discard=(FIRE,)), UseAttack(0, 0))
        self.assertEqual((new.decision, len(new.players[0].active.energy)), (None, 1))
        state = with_coin_results(board(mon(LT_SURGES_ELECTABUZZ, (LIGHTNING, LIGHTNING, FIRE)), opponent=mon(HITMONCHAN)), H, T)
        new = self.run_all_modes(state, UseAttack(0, 1))
        self.assertEqual((self.opp(new).damage, len(new.players[0].active.energy)), (30, 1))
        self.assertEqual(len([e for e in events(new, len(state.log), "coin_flip") if e.get("source") == "attack"]), 2)

    def test_lt_surges_pikachu_and_eevee_quick_attack(self):
        """でんこうせっか（マチスのピカチュウ・イーブイ）: 10、「おもて」なら +20。"""
        for card in (LT_SURGES_PIKACHU, EEVEE):
            for coin, damage in ((H, 30), (T, 10)):
                state = with_coin_results(board(mon(card, (FIRE, FIRE)), opponent=mon(HITMONCHAN)), coin)
                index = 0 if card == LT_SURGES_PIKACHU else 1
                self.assertEqual(self.opp(self.run_all_modes(state, UseAttack(0, index))).damage, damage, (card, coin))

    # ---- 闇からの挑戦: カツラのヒトカゲ・リザード・ブーバー・キュウコン・ロコン・ウインディ・ガーディ、マチスのライチュウ

    def test_blaines_charmander(self):
        """メラメラ: 10 のあと、自分と相手のエネルギーカードを 1 枚ずつ（ワザを使ったプレイヤーが、自分 → 相手の順に）選んでトラッシュ。きりさく 20。"""
        state = board(mon(BLAINES_CHARMANDER, (FIRE, WATER)), opponent=mon(HITMONCHAN, (FIGHTING, FIGHTING)))
        kinds = []
        new = self.run_all_modes(state, UseAttack(0, 0), [
            lambda d: (kinds.append((d.kind, d.player)), (d.options[1],))[1], lambda d: (kinds.append((d.kind, d.player)), (d.options[0],))[1]])
        self.assertEqual(kinds[:2], [(DISCARD_ENERGY, 0), (DISCARD_OPPONENT_ENERGY, 0)])
        self.assertEqual((self.opp(new).damage, len(new.players[0].active.energy), len(self.opp(new).energy)), (10, 1, 1))
        new = self.run_all_modes(board(mon(BLAINES_CHARMANDER, (FIRE, FIRE)), opponent=mon(HITMONCHAN)), UseAttack(0, 1))
        self.assertEqual(self.opp(new).damage, 20)

    def test_blaines_charmeleon(self):
        """ほのおのつめ 30。やきはらう: コイン 3 枚の「おもて」の数の炎をトラッシュし、相手と相手の控え全員に「おもて」× 10（弱点・抵抗力に関係なく）。"""
        new = self.run_all_modes(board(mon(BLAINES_CHARMELEON, (FIRE, FIRE)), opponent=mon(HITMONCHAN)), UseAttack(0, 0))
        self.assertEqual(self.opp(new).damage, 30)
        state = with_coin_results(board(mon(BLAINES_CHARMELEON, (FIRE, FIRE, FIRE)), opponent=mon(BULBASAUR),
                                        opponent_bench=(RATTATA, BULBASAUR)), H, H, T)
        new = self.run_all_modes(state, UseAttack(0, 1), [first(2)])
        self.assertEqual((self.opp(new).damage, [p.damage for p in new.players[1].bench]), (20, [20, 20]))  # 弱点 炎のフシギダネも 20
        self.assertEqual(len(new.players[0].active.energy), 1)

    def test_blaines_magmar(self):
        """ひをふく: 10、「おもて」なら +10。マグマふんしゅつ: 自分の山札の上から 5 枚トラッシュし、その中の炎エネルギーカード × 20。"""
        for coin, damage in ((H, 20), (T, 10)):
            state = with_coin_results(board(mon(BLAINES_MAGMAR, (FIRE,)), opponent=mon(HITMONCHAN)), coin)
            self.assertEqual(self.opp(self.run_all_modes(state, UseAttack(0, 0))).damage, damage)
        state = board(mon(BLAINES_MAGMAR, (FIRE, FIRE, FIRE)), opponent=mon(HITMONCHAN), deck=[FIRE, WATER, FIRE, GRASS, POTION, FIRE])
        top = state.players[0].deck[:5]
        new = self.run_all_modes(state, UseAttack(0, 1))
        self.assertEqual((self.opp(new).damage, new.players[0].discard, len(new.players[0].deck)), (40, top, 1))

    def test_blaines_ninetales_attack(self):
        """しゃくねつ: 50、「うら」なら自分の炎エネルギーカードをすべてトラッシュ（ほかのタイプは残る）。"""
        for coin, left in ((H, 3), (T, 1)):
            state = with_coin_results(board(mon(BLAINES_NINETALES, (FIRE, FIRE, WATER)), opponent=mon(HITMONCHAN)), coin)
            new = self.run_all_modes(state, UseAttack(0, 0))
            self.assertEqual((self.opp(new).damage, len(new.players[0].active.energy)), (50, left))

    def test_blaines_arcanine(self):
        """ヒートタックル: 40、自分にも 10。ほのおのあらし: 炎 3 枚を選んでトラッシュ → 120。"""
        new = self.run_all_modes(board(mon(BLAINES_ARCANINE, (FIRE, FIRE, FIRE)), opponent=mon(HITMONCHAN)), UseAttack(0, 0))
        self.assertEqual((self.opp(new).damage, new.players[0].active.damage), (40, 10))
        state = board(mon(BLAINES_ARCANINE, (FIRE, FIRE, FIRE, FIRE, WATER)), opponent=mon(HITMONCHAN, damage=0))
        new = self.run_all_modes(state, UseAttack(0, 1), [
            lambda d: (self.assertEqual((d.kind, d.min_choices, d.max_choices, len(d.options)), (DISCARD_ENERGY, 3, 3, 4)), first(3)(d))[1]])
        self.assertEqual((dealt(new, len(state.log)), len(new.players[0].active.energy)), ([120], 2))
        discarded = [new.card_def(e["energy"]).id for e in events(new, len(state.log), "discard_energy")]
        self.assertEqual(discarded, [FIRE, FIRE, FIRE])

    def test_blaines_vulpix_and_growlithe(self):
        """しっぽでまどわす: 20、「おもて」ならこんらん。もえひろがる: 20 と、相手のベンチの草ポケモン全員に 10（弱点・抵抗力に関係なく）。"""
        for coin, confused in ((H, True), (T, False)):
            state = with_coin_results(board(mon(BLAINES_VULPIX, (FIRE, FIRE, FIRE)), opponent=mon(HITMONCHAN)), coin)
            new = self.run_all_modes(state, UseAttack(0, 0))
            self.assertEqual((self.opp(new).damage, self.opp(new).conditions.confused), (20, confused))
        state = board(mon(BLAINES_GROWLITHE, (FIRE, FIRE)), opponent=mon(HITMONCHAN), opponent_bench=(BULBASAUR, RATTATA, BULBASAUR))
        new = self.run_all_modes(state, UseAttack(0, 0))
        self.assertEqual((self.opp(new).damage, [p.damage for p in new.players[1].bench]), (20, [10, 0, 10]))

    def test_lt_surges_raichu(self):
        """バリバリ: 20、「おもて」なら +30 と自分の雷をすべてトラッシュ。でんきタックル: 40、「おもて」ならマヒ、「うら」なら自分にも 20。"""
        for coin, damage, left in ((H, 50, 1), (T, 20, 3)):
            state = with_coin_results(board(mon(LT_SURGES_RAICHU, (LIGHTNING, LIGHTNING, FIRE)), opponent=mon(HITMONCHAN)), coin)
            new = self.run_all_modes(state, UseAttack(0, 0))
            self.assertEqual((self.opp(new).damage, len(new.players[0].active.energy)), (damage, left))
        for coin, paralyzed, self_damage in ((H, True, 0), (T, False, 20)):
            state = with_coin_results(board(mon(LT_SURGES_RAICHU, (LIGHTNING,) * 4), opponent=mon(HITMONCHAN)), coin)
            new = self.run_all_modes(state, UseAttack(0, 1))
            self.assertEqual((self.opp(new).damage, self.opp(new).conditions.paralyzed, new.players[0].active.damage), (40, paralyzed, self_damage))

    def test_eevee_tail_wag(self):
        """しっぽをふる: 「おもて」なら、相手の対戦ポケモンに「次の相手の番にワザを使えない」持続する効果（相手の番の処理は仕組みのテスト）。"""
        for coin, locked in ((H, ["CannotAttack"]), (T, [])):
            new = self.run_all_modes(with_coin_results(board(mon(EEVEE, (FIRE,))), coin), UseAttack(0, 0))
            self.assertEqual([type(e).__name__ for e in self.opp(new).persistent_effects], locked)

    def test_every_attack_is_covered_here(self):
        """このクラスのテストが、v0.31 の 29 枚のすべてのワザ（52）を使う（説明文のないワザも含む）。新しいワザを加えたら、ここにも加える。"""
        covered = {
            NINETALES: (0, 1), CHARIZARD: (0,), ZAPDOS: (0, 1), BASE_GASTLY: (0, 1), MEWTWO: (0, 1), CLEFABLE: (0, 1), CLEFAIRY: (0, 1),
            MOLTRES: (0, 1), SLOWPOKE: (0, 1), DARK_RAPIDASH: (0, 1), DARK_CHARMELEON: (0, 1), DARK_FLAREON: (0, 1), DARK_CHARIZARD: (0, 1),
            DARK_GOLDUCK: (0, 1), DARK_ELECTRODE: (0, 1), PSYDUCK: (0, 1), MISTYS_GOLDUCK: (0, 1), MISTYS_PSYDUCK: (0,),
            LT_SURGES_ELECTABUZZ: (0, 1), LT_SURGES_PIKACHU: (0,), EEVEE: (0, 1), BLAINES_CHARMANDER: (0, 1), BLAINES_CHARMELEON: (0, 1),
            BLAINES_MAGMAR: (0, 1), BLAINES_NINETALES: (0,), BLAINES_ARCANINE: (0, 1), BLAINES_VULPIX: (0,), BLAINES_GROWLITHE: (0,),
            LT_SURGES_RAICHU: (0, 1),
        }
        pool = load_card_pool()
        self.assertEqual({(c, i) for c, indexes in covered.items() for i in indexes},
                         {(c, a.index) for c in V0_31_POKEMON for a in pool.get(c).attacks})


if __name__ == "__main__":
    unittest.main()

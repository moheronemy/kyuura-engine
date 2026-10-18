"""v0.49: ワザの出どころ・今の姿・持っている特殊能力を区別する共通の処理と、それを使う 4 枚（docs/virtual-attacks-transformation-v0.49.md）。

4 枚: ナツメのフーディン（PMCG6-053。［サイコリンク］・メガバーン）・メタモン（PMCG3-042。［へんしん］）・タケシのキュウコン（PMCG5-019。「ばける」・おにび）・
思い出させる（PMCG5-071。トレーナー）。どれも kyuura データの採用（処理に使う文面は kyuura の印刷の文面。採用したデータのコミット ecb2d69）と pcg-search.com の同じ版の
ページとの照合。ガイドブックは読んでいない。

根拠にした既存の記録: kyuura の ERR-BROCK-NINETALES・data/curation/card_differences.json の PMCG5-019（2000.02.14 版の基準（『オフィシャルブック2000』）では、
「ばける」でのせたカードの特殊能力ははたらき・使える。「手札から場に出したときに使える能力は、[ばける]で場に出したときには使えません」（p.69 の解説）。のせたカードの
特殊能力をはたらかなくした変更の公表は 2000年5月で、この基準のあと。持ち込まない）・GR-2000-P310-EVOLUTION（進化前に持っていたワザ）・GR-2000-P309-ATTACK-PROCEDURE・
GR-2000-P321-DAMAGE-ORDER・GR-2000-P322-PERSISTENT-EFFECTS と、エンジンの v0.31（ゆびをふる）・v0.35（あわあわ・ドわすれ）・v0.42（特殊能力の決定と再開）・
v0.44（1 度だけ使えるワザ）・v0.46（常にはたらく特殊能力）・v0.47（印刷の定義と場での役割）・v0.48（今有効な最大HP・タイプ・弱点・抵抗力。VS1・MH1）の記録。

新しい停止コードは 11: TE1・TF1・TF2・DG1・DG2・DG3・VA1・RC1・RC2・RC3・RC4（docs 10 章）。
"""

from __future__ import annotations

import dataclasses
import json
import pathlib
import unittest

from kyuura_engine import (
    EndTurn,
    EngineError,
    EvolvePokemon,
    IllegalActionError,
    Phase,
    PlayTrainer,
    PromoteActive,
    RemoveDisguise,
    ResolveDecision,
    Retreat,
    UnsupportedError,
    UseAttack,
    UsePokemonPower,
    available_attacks,
    check_invariants,
    command_from_dict,
    command_to_dict,
    current_form,
    max_hp,
    observe,
    powers_of,
    resistance_of,
    state_to_dict,
    type_readings,
    weakness_of,
)
from kyuura_engine import effects as E
from kyuura_engine.cards import EnergyType, load_card_pool, pool_from_extract, read_extract
from kyuura_engine.decisions import SELECT_EVOLUTION_CARD
from kyuura_engine.evolution import evolution_block
from kyuura_engine.observation import PUBLIC_EVENTS
from kyuura_engine.resolution import PREFLIGHT_MODES, contract, programs, v013_checks
from kyuura_engine.serialize import FORMAT_VERSIONS
from kyuura_engine.state import CannotUseOwnAttack
from scripts import check_card_sources as cs
from tests.helpers import (
    ABRA,
    ALAKAZAM,
    ATTACK_TYPES_SINCE_V0_17,
    BROCKS_NINETALES,
    BROCKS_VULPIX,
    BULBASAUR,
    CHARMANDER,
    CHANSEY,
    CHARIZARD,
    CHARMELEON,
    CLEFAIRY,
    DARK_CHARIZARD,
    DARK_CHARMELEON,
    DARK_DRAGONITE,
    DARK_GOLBAT,
    DITTO,
    FARFETCHD,
    FIGHTING,
    FIRE,
    GRASS,
    GIOVANNIS_MACHAMP,
    GIOVANNIS_MACHOKE,
    GIOVANNIS_MACHOP,
    GRIMER,
    GUST,
    HITMONCHAN,
    IVYSAUR,
    JIGGLYPUFF,
    JYNX,
    KADABRA,
    KOGAS_BEEDRILL,
    KOGAS_DITTO,
    KOGAS_KAKUNA,
    KOGAS_PIDGEY_40,
    KOGAS_WEEDLE,
    LAPRAS,
    MACHAMP,
    MR_MIME,
    MUK,
    MYSTERIOUS_FOSSIL,
    POKEMON_BREEDER,
    POLIWAG,
    POLIWHIRL,
    PSYCHIC,
    RATTATA,
    RECALL,
    RHYDON,
    ROCKET_CHARMANDER,
    SABRINAS_ABRA,
    SABRINAS_ALAKAZAM,
    SABRINAS_GASTLY,
    SABRINAS_KADABRA,
    SABRINAS_SLOWBRO,
    SABRINAS_SLOWPOKE,
    SNORLAX,
    SWITCH,
    V0_49_CARDS,
    V0_49_POKEMON,
    VENOMOTH,
    VENONAT,
    VENUSAUR,
    WATER,
    H,
    T,
    apply_kernel,
    build_test_state,
    with_coin_results,
)
from tests.log_audit import observation_problems, serialization_problems

ROOT = pathlib.Path(__file__).resolve().parent.parent
DOC = ROOT / "docs" / "virtual-attacks-transformation-v0.49.md"
TURN = 7
P, R, W, G, F = PSYCHIC, FIRE, WATER, GRASS, FIGHTING
TE1 = "UNRESOLVED_TRANSFORM_ENERGY_COUNT"
TF1 = "UNRESOLVED_TRANSFORM_COPIED_POWER"
TF2 = "UNRESOLVED_TRANSFORM_MODIFIED_DEFENDER"
DG1 = "UNRESOLVED_SHAPESHIFT_SUPPRESSED"
DG2 = "UNRESOLVED_SHAPESHIFT_ENTRY_POWER"
DG3 = "UNRESOLVED_SHAPESHIFT_AGAIN"
VA1 = "UNRESOLVED_VIRTUAL_ONCE_ATTACK"
RC1 = "UNRESOLVED_RECALL_WITHOUT_PRE_EVOLUTION_ATTACK"
RC2 = "UNRESOLVED_RECALL_EARLIER_STAGE"
RC3 = "UNRESOLVED_RECALL_TARGET_CHANGED"
RC4 = "UNRESOLVED_RECALL_FORM"
VS1 = "UNRESOLVED_SHIFT_COLOR_DURATION"
MH1 = "UNRESOLVED_MAX_HP_DROP"
NEW_CODES = (TE1, TF1, TF2, DG1, DG2, DG3, VA1, RC1, RC2, RC3, RC4)
# pcg-search.com の対象の版（サイトの一覧の番号）
EDITIONS = {SABRINAS_ALAKAZAM: "046/098", DITTO: "042/048", BROCKS_NINETALES: "020/096", RECALL: "068/096"}
# 進化しているポケモンの下のカード（build_test_state の "evolved_from"）
BELOW = {SABRINAS_ALAKAZAM: [SABRINAS_ABRA, SABRINAS_KADABRA], SABRINAS_KADABRA: SABRINAS_ABRA, BROCKS_NINETALES: BROCKS_VULPIX, KADABRA: ABRA,
         CHARMELEON: CHARMANDER, VENOMOTH: VENONAT, MUK: GRIMER, VENUSAUR: [BULBASAUR, IVYSAUR], IVYSAUR: BULBASAUR, MACHAMP: None,
         SABRINAS_SLOWBRO: SABRINAS_SLOWPOKE, POLIWHIRL: POLIWAG, KOGAS_BEEDRILL: [KOGAS_WEEDLE, KOGAS_KAKUNA]}


def mon(card, energy=(), **extra):
    spec = {"card": card, "energy": list(energy), **extra}
    if BELOW.get(card) and "evolved_from" not in spec:
        spec["evolved_from"] = BELOW[card]
    return spec


def bench_spec(b):
    return mon(b) if isinstance(b, str) else b


def board(active, opponent=None, *, bench=(RATTATA,), opponent_bench=(RATTATA,), hand=(), opponent_hand=(), turn=TURN, current=0, deck=None,
          opponent_deck=None):
    me = {"active": active, "bench": [bench_spec(b) for b in bench], "hand": list(hand)}
    them = {"active": opponent or mon(HITMONCHAN, (F, F, F)), "bench": [bench_spec(b) for b in opponent_bench], "hand": list(opponent_hand)}
    if deck is not None:
        me["deck"] = list(deck)
    if opponent_deck is not None:
        them["deck"] = list(opponent_deck)
    return build_test_state([me, them], turn_number=turn, current_player=current)


def full(state):
    return state_to_dict(state, format_version=max(FORMAT_VERSIONS))


def snapshot(state):
    return full(state), [dict(e) for e in state.log], repr(state.rng.getstate())


def audited(test, state):
    """不変条件・書き出し・観測の監査（盤面を直接作ったテスト。ログの監査は正式な対戦のテストで確かめる）。"""
    test.assertEqual(check_invariants(state), [])
    test.assertEqual(serialization_problems(state), [])
    test.assertEqual(observation_problems(state), [])
    return state


def events(state, since, kind=None):
    return [dict(e) for e in state.log[since:] if kind is None or e["kind"] == kind]


def answer(state, choices, *, mode="derived"):
    d = state.decision
    return apply_kernel(state, ResolveDecision(d.player, d.id, tuple(choices)), preflight=mode)


def option(state, route, card_id, index, *, provider=None, pokemon=None):
    pokemon = state.players[state.current_player].active if pokemon is None else pokemon
    found = [o for o in available_attacks(state, pokemon)
             if o.route == route and o.card_id == card_id and o.attack_index == index and (provider is None or o.provider == provider)]
    assert len(found) == 1, (route, card_id, index, available_attacks(state, pokemon))
    return found[0]


def use(state, opt, *sides, mode="derived"):
    state = with_coin_results(state, *sides) if sides else state
    return apply_kernel(state, UseAttack(state.current_player, opt.attack_index, card=opt.card), preflight=mode)


def assert_stops(test, state, command, code, *, exception=UnsupportedError):
    """どの先読みの方法でも ``code`` で拒否し、状態・乱数・ログが変わらない。"""
    before = snapshot(state)
    for mode in PREFLIGHT_MODES:
        with test.subTest(mode=mode), test.assertRaises(exception) as raised:
            apply_kernel(state, command, preflight=mode)
        test.assertEqual(raised.exception.code, code)
    test.assertEqual(snapshot(state), before)


def assert_rejected(test, state, command, code, exception=EngineError):
    before = snapshot(state)
    with test.assertRaises(exception) as raised:
        apply_kernel(state, command)
    test.assertEqual(raised.exception.code, code)
    test.assertEqual(snapshot(state), before)


def end_turn(state):
    return apply_kernel(state, EndTurn(state.current_player))


def card_of(state, player, card, zone="hand", nth=0):
    return [u for u in getattr(state.players[player], zone) if state.cards[u].card_id == card][nth]


def routes(state, pokemon=None):
    pokemon = state.players[state.current_player].active if pokemon is None else pokemon
    return [(o.route, o.card_id, o.attack_index, o.provider, o.problem and o.problem[0]) for o in available_attacks(state, pokemon)]


def shapeshift(state, card_id, *, player=0, pokemon=None):
    """タケシのキュウコンの「ばける」で、手札の ``card_id`` をのせる（宣言 → 決定への答え）。"""
    pokemon = state.players[player].active if pokemon is None else pokemon
    state = apply_kernel(state, UsePokemonPower(player, pokemon.pokemon_id, 0))
    return answer(state, [card_of(state, player, card_id)])


# ---------------------------------------------------------------- 登録・写し・記録


class CardDataTest(unittest.TestCase):
    """4 枚の写し・登録・記録。"""

    @classmethod
    def setUpClass(cls):
        cls.pool = load_card_pool()

    def test_targets_are_the_four_requested_cards(self):
        """写しの組 pool_v0_49 は依頼の 4 枚（並び）。どれも対応で、どのワザも、どの特殊能力も、トレーナーの効果も登録した。同じ名前の別のカードと取りちがえない。"""
        self.assertEqual(read_extract()["pool_v0_49"], list(V0_49_CARDS))
        self.assertEqual(V0_49_POKEMON, V0_49_CARDS[:3])
        names = {SABRINAS_ALAKAZAM: "ナツメのフーディン", DITTO: "メタモン", BROCKS_NINETALES: "タケシのキュウコン", RECALL: "思い出させる"}
        for card in V0_49_CARDS:
            with self.subTest(card=card):
                definition = self.pool.get(card)
                self.assertEqual(definition.name_ja, names[card])
                self.assertTrue(self.pool.is_playable(card))
        self.assertEqual(self.pool.get(RECALL).category, "trainer")
        self.assertEqual((self.pool.get(SABRINAS_ALAKAZAM).stage, self.pool.get(SABRINAS_ALAKAZAM).evolves_from), ("stage2", "ナツメのユンゲラー"))
        self.assertEqual((self.pool.get(BROCKS_NINETALES).stage, self.pool.get(BROCKS_NINETALES).evolves_from), ("stage1", "タケシのロコン"))
        # メタモン（化石の秘密）はキョウのメタモン（PMCG6-072）と別のカード。ワザがなく、［へんしん］で今の姿のワザを持つ
        self.assertEqual((self.pool.get(DITTO).attacks, self.pool.get(DITTO).stage), ((), "basic"))
        self.assertNotEqual(DITTO, "PMCG6-072")
        # 特殊能力の登録を除くと対応にならない（ワザのないメタモンも、ワザだけの登録で対応と数えない）
        for card in V0_49_POKEMON:
            effects = E.DEFAULT_EFFECTS.without_powers(f"test-no-{card}", [E.PowerKey(card, 0)])
            with self.subTest(card=card):
                self.assertFalse(pool_from_extract(read_extract(), effects).is_playable(card))

    def test_registrations_use_kyuura_printed_text(self):
        """処理に使う文面は kyuura の印刷の文面（LD-・エラッタはない。ERR-BROCK-NINETALES は 2000年5月の変更で、この基準に持ち込まない）。"""
        alakazam = self.pool.get(SABRINAS_ALAKAZAM)
        entry = E.DEFAULT_EFFECTS.attack_entry(SABRINAS_ALAKAZAM, 0)
        self.assertIsInstance(entry.effect, E.DamageThenLockSelf)
        self.assertEqual((entry.name_ja, entry.text_ja, entry.play_text_ja, entry.source),
                         (alakazam.attacks[0].name_ja, alakazam.attacks[0].text_ja, alakazam.attacks[0].text_ja, cs.PRINTED_TEXT_SOURCE))
        self.assertIsInstance(E.DEFAULT_EFFECTS.attack_entry(BROCKS_NINETALES, 0).effect, E.DamageOnly)
        powers = {SABRINAS_ALAKAZAM: E.AttacksOfOwnTypePokemon(EnergyType.PSYCHIC), DITTO: E.TransformIntoDefender(),
                  BROCKS_NINETALES: E.Shapeshift("タケシのキュウコン")}
        for card, effect in powers.items():
            power = self.pool.get(card).powers[0]
            entry = E.DEFAULT_EFFECTS.power_entry(card, 0)
            with self.subTest(card=card):
                self.assertEqual(entry.effect, effect)
                self.assertEqual((entry.name_ja, entry.text_ja, entry.play_text_ja, entry.source),
                                 (power.name_ja, power.text_ja, power.text_ja, cs.PRINTED_TEXT_SOURCE))
                self.assertEqual(entry.effect.check(power), [])
                self.assertTrue(entry.effect.check(dataclasses.replace(power, text_ja=power.text_ja + "あ")))
        # ［サイコリンク］・［へんしん］は常にはたらく（宣言しない）。「ばける」は宣言して、自分の番に 1 回
        self.assertFalse(powers[SABRINAS_ALAKAZAM].declared or powers[DITTO].declared)
        self.assertTrue(powers[BROCKS_NINETALES].declared and powers[BROCKS_NINETALES].once_per_turn)
        self.assertTrue(powers[DITTO].supplies_attacks)
        trainer = E.DEFAULT_EFFECTS.trainer_entry(RECALL)
        self.assertIsInstance(trainer.effect, E.RecallPreEvolutionAttacks)
        printed = self.pool.get(RECALL).trainer_text_ja
        self.assertEqual((trainer.text_ja, trainer.play_text_ja, trainer.source), (printed, printed, cs.PRINTED_TEXT_SOURCE))

    def test_no_new_attack_types_and_existing_types_stay_outside_the_v013_contract(self):
        """v0.49 はワザの型を加えていない（メガバーンはあわあわ（v0.35）・きあいずつき（v0.41）と同じ ``DamageThenLockSelf``、おにびは ``DamageOnly``）。"""
        self.assertIn(E.DamageThenLockSelf, ATTACK_TYPES_SINCE_V0_17)
        self.assertNotIn(E.DamageThenLockSelf, v013_checks.VERIFIED)
        self.assertIn(E.DamageThenLockSelf, programs.BUILDERS)
        self.assertFalse(contract.is_contract(contract.program_for(E.DEFAULT_EFFECTS.attack_entry(SABRINAS_ALAKAZAM, 0).effect)))

    def test_adoption_records_and_external_checks(self):
        """採用の記録（kyuura データの採用）と pcg-search.com の同じ版との照合。タケシのキュウコンは ERR-BROCK-NINETALES を研究の基準のコミットで指す（当てはめない記録）。
        ガイドブックの項目は書かない。"""
        records = json.loads((ROOT / "kyuura_engine" / "data" / "card_sources.json").read_text(encoding="utf-8"))["cards"]
        for card in V0_49_CARDS:
            with self.subTest(card=card):
                record = records[card]
                self.assertEqual((record["basis"], record["status"]), ("kyuura_data", "adopted"))
                self.assertEqual(record["kyuura_records"], ["ERR-BROCK-NINETALES"] if card == BROCKS_NINETALES else [])
                checks = record["external_checks"]
                self.assertEqual(len(checks), 1)
                self.assertTrue(checks[0]["url"].startswith("https://pcg-search.com/"))
                self.assertEqual(checks[0]["edition"]["list_number"], EDITIONS[card])
                self.assertEqual(checks[0]["result"], "match")
                for forbidden in ("page", "pdf_page", "latest_description_ja", "card_image_text_ja"):
                    self.assertNotIn(forbidden, json.dumps(record, ensure_ascii=False).replace("list_number", ""))
        self.assertEqual(cs.problems(), [])

    def test_public_events_and_stop_codes(self):
        self.assertTrue({"disguise", "disguise_removed", "recall"} <= PUBLIC_EVENTS)
        links = json.loads((ROOT / "kyuura_engine" / "data" / "research_links.json").read_text(encoding="utf-8"))
        for code in NEW_CODES:
            with self.subTest(code=code):
                self.assertEqual(links["stop_codes"][code]["kyuura_disposition"], "not_in_kyuura")
        # v0.49 で 75・76。v0.50 で DV1〜DV5 の 5 件を加えた（docs/mew-devolution-spray-v0.50.md）
        self.assertEqual((links["counts"]["engine_stop_codes"], links["counts"]["engine_unresolved_rulings"]), (132, 134))  # v0.51 で RV1・FT1、v0.52 で FJ1・SU1・SU2、v0.53 で ST1・NG1 を加えた、v0.55 で MW1・EM1・SP1・FH1・GL1・GL2・SB1・SB2 を加えた、v0.56 で LS1・RT1・RG1・MY1・MS1・KG1 を加えた、v0.57 で STB1・TG1・FG1・FG2・EX1・VG1・VM1・CH1、v0.58 で RB1〜RB4・TE2・RT1 を加えた、v0.59 で GG1・BL1・CB1・BZ1〜BZ4 を加えた。v0.60 で TS1 を加え、コードのない SS1 を数えた。v0.61 で SH1・SC1・SC2・TD1 を加え、Z9 に停止コードを付けた。v0.62 で MM1・MM2・OM1・OM2 を加え、コードのない ED1 を数えた


# ---------------------------------------------------------------- ［サイコリンク］・メガバーン


def alakazam_board(*, energy=(P, P, P, P), bench=(JYNX,), hand=(), opponent=None, **extra):
    return board(mon(SABRINAS_ALAKAZAM, energy, **extra), opponent or mon(LAPRAS), bench=bench, hand=hand)


class PsylinkTest(unittest.TestCase):
    """ナツメのフーディンの［サイコリンク］: 自分の場の「超」ポケモンのワザを、このカードのワザとして使う（docs 3 章）。"""

    def test_linked_attacks_come_from_own_psychic_pokemon_in_play(self):
        """持つワザは、自分の場のこのカード以外の「超」ポケモンの今の姿のカードのワザ。「超」でないポケモン・相手のポケモンのワザは持たない。並びは今の姿のワザ →
        ［サイコリンク］のワザ（供給するポケモンをバトル場 → ベンチの順に）。"""
        state = alakazam_board(bench=(JYNX, RATTATA, mon(KADABRA)))
        jynx, _, kadabra = state.players[0].bench
        self.assertEqual(routes(state), [("form", SABRINAS_ALAKAZAM, 0, None, None),
                                         ("psylink", JYNX, 0, jynx.pokemon_id, None), ("psylink", JYNX, 1, jynx.pokemon_id, None),
                                         ("psylink", KADABRA, 0, kadabra.pokemon_id, None), ("psylink", KADABRA, 1, kadabra.pokemon_id, None)])
        linked = option(state, "psylink", JYNX, 0)
        self.assertEqual(linked.card, jynx.card)
        audited(self, state)

    def test_using_a_linked_attack_processes_the_alakazam(self):
        """ワザを使うポケモンはフーディン（供給するポケモンは処理しない）。必要なエネルギー・エネルギーのトラッシュ・「このカード」はフーディンについて処理する。
        ユンゲラーの「じこさいせい」（超のエネルギーカードを 1 枚トラッシュし、このカードのダメージカウンターをすべてとりのぞく）をフーディンが使う。"""
        state = alakazam_board(bench=(mon(KADABRA, (P, P), damage=30),), damage=40)
        kadabra = state.players[0].bench[0]
        heal = option(state, "psylink", KADABRA, 0)
        since = len(state.log)
        state = use(state, heal)
        self.assertIsNotNone(state.decision)  # 決定: フーディンについている超のエネルギーカード
        alakazam = state.players[0].active
        self.assertEqual(state.decision.options, tuple(alakazam.energy))
        state = answer(state, [alakazam.energy[0]])
        alakazam, kadabra_after = state.players[0].active, state.players[0].bench[0]
        self.assertEqual((alakazam.damage, len(alakazam.energy)), (0, 3))
        self.assertEqual((kadabra_after.damage, len(kadabra_after.energy)), (30, 2))
        attack_log = events(state, since, "attack")[0]
        self.assertEqual((attack_log["card"], attack_log["card_id"], attack_log["route"], attack_log["provider"], attack_log["pokemon"]),
                         (kadabra.card, KADABRA, "psylink", kadabra.pokemon_id, alakazam.card))
        self.assertEqual(events(state, since, "discard_energy")[0]["pokemon"], alakazam.card)

    def test_linked_attack_needs_its_energy_and_uses_alakazams_type(self):
        """必要なエネルギーはそのワザのもの（フーディンについているエネルギーで払う。「ゆびをふる」の免除はない）。弱点・抵抗力はフーディンのタイプで計算する。"""
        state = alakazam_board(energy=(P,), bench=(JYNX,))
        pose = option(state, "psylink", JYNX, 1)  # ヨガのポーズ（超超無）
        assert_rejected(self, state, UseAttack(0, pose.attack_index, card=pose.card), "INSUFFICIENT_ENERGY", IllegalActionError)
        state = board(mon(SABRINAS_ALAKAZAM, (P,)), mon(SABRINAS_ALAKAZAM, (P,)), bench=(mon(CHARMANDER),), opponent_bench=())
        # 自分の場に「超」ポケモンがいなければ、［サイコリンク］のワザはない（相手のフーディン・ルージュラのワザは持たない）
        self.assertEqual(routes(state), [("form", SABRINAS_ALAKAZAM, 0, None, None)])
        state = board(mon(SABRINAS_ALAKAZAM, (P,)), mon(SABRINAS_ALAKAZAM), bench=(JYNX,), opponent_bench=())
        since = len(state.log)
        state = use(state, option(state, "psylink", JYNX, 0), H, H)
        damage = events(state, since, "damage")[0]
        self.assertTrue(damage["weakness"])  # 相手のナツメのフーディンの弱点は超。ワザを使うのは超のフーディン
        self.assertEqual(damage["amount"], 40)

    def test_power_disappears_with_status_and_chemical_gas(self):
        """ねむり・マヒ・こんらん状態・かがくへんかガスで、［サイコリンク］の力は消える（持つワザは今の姿のワザだけ）。どくは関係しない。"""
        expected = [("form", SABRINAS_ALAKAZAM, 0, None, None)]
        for status in ({"confusion": True}, {"sleep": True}, {"paralysis": TURN - 1}):
            with self.subTest(status=status):
                self.assertEqual(routes(alakazam_board(**status)), expected)
        poisoned = alakazam_board(poison=10)
        self.assertEqual(len(available_attacks(poisoned, poisoned.players[0].active)), 3)
        gas = board(mon(SABRINAS_ALAKAZAM, (P,)), mon(MUK), bench=(JYNX,))
        self.assertEqual(routes(gas), expected)
        # ベンチにいても力ははたらく（「このカードも持っている」。ワザを使えるのはバトル場のときだけ）
        state = board(mon(JYNX), bench=(mon(SABRINAS_ALAKAZAM),))
        bench_alakazam = state.players[0].bench[0]
        self.assertEqual([o.route for o in available_attacks(state, bench_alakazam)], ["form", "psylink", "psylink"])

    def test_two_psylinks_do_not_recurse_or_grow(self):
        """2 匹のナツメのフーディン: バトル場のフーディンが持つのは、ベンチのフーディンの今の姿のワザ（メガバーン）と、ルージュラのワザ。ベンチのフーディンが
        ［サイコリンク］で持つワザは数えない（再帰・増え続けはない）。どちらのフーディンが見ても同じ自分の場の集まり。"""
        state = alakazam_board(bench=(mon(SABRINAS_ALAKAZAM), JYNX))
        other, jynx = state.players[0].bench
        self.assertEqual(routes(state), [("form", SABRINAS_ALAKAZAM, 0, None, None),
                                         ("psylink", SABRINAS_ALAKAZAM, 0, other.pokemon_id, None),
                                         ("psylink", JYNX, 0, jynx.pokemon_id, None), ("psylink", JYNX, 1, jynx.pokemon_id, None)])
        active = state.players[0].active
        self.assertEqual([(o.route, o.card_id, o.provider) for o in available_attacks(state, other)],
                         [("form", SABRINAS_ALAKAZAM, None), ("psylink", SABRINAS_ALAKAZAM, active.pokemon_id), ("psylink", JYNX, jynx.pokemon_id)] +
                         [("psylink", JYNX, jynx.pokemon_id)])

    def test_same_attack_from_two_providers_is_two_options_with_the_same_key(self):
        """同じワザ（同じカードの同じ位置）を 2 匹が持つときは、出どころ（カードの uid）ごとに選べる。どちらを選んでも同じワザ（``AttackKey``）。"""
        state = alakazam_board(bench=(JYNX, JYNX))
        first, second = state.players[0].bench
        options = [o for o in available_attacks(state, state.players[0].active) if o.card_id == JYNX and o.attack_index == 0]
        self.assertEqual([(o.card, o.provider) for o in options], [(first.card, first.pokemon_id), (second.card, second.pokemon_id)])
        self.assertEqual({o.key for o in options}, {E.AttackKey(JYNX, 0)})
        for opt in options:
            since = len(state.log)
            after = use(state, opt, T, T)
            with self.subTest(provider=opt.provider):
                self.assertEqual(events(after, since, "attack")[0]["card"], opt.card)
        # 印刷したカードの uid がワザを持たないカード（相手のカード・フーディン自身の下のカード）なら INVALID_ATTACK
        assert_rejected(self, state, UseAttack(0, 0, card=state.players[1].active.card), "INVALID_ATTACK", IllegalActionError)
        assert_rejected(self, state, UseAttack(0, 0, card=state.players[0].active.evolution_stack[0]), "INVALID_ATTACK", IllegalActionError)

    def test_provider_changes_are_followed(self):
        """供給するポケモンの進化・移動・きぜつ・特殊状態に応じて、今のワザの一覧を求める（状態に持たない）。"""
        state = alakazam_board(bench=(mon(SABRINAS_ABRA),), hand=(SABRINAS_KADABRA,), played_turn=0)
        abra = state.players[0].bench[0]
        self.assertEqual([o.card_id for o in available_attacks(state, state.players[0].active)], [SABRINAS_ALAKAZAM, SABRINAS_ABRA])
        state = apply_kernel(state, EvolvePokemon(0, card_of(state, 0, SABRINAS_KADABRA), abra.pokemon_id))
        self.assertEqual([o.card_id for o in available_attacks(state, state.players[0].active)], [SABRINAS_ALAKAZAM, SABRINAS_KADABRA, SABRINAS_KADABRA])
        # 供給するポケモンが進化しても、場のポケモンの番号は同じ。ワザはいちばん上のカードのワザ（進化前のケーシィのワザは持たない）
        self.assertEqual({o.provider for o in available_attacks(state, state.players[0].active) if o.route == "psylink"}, {abra.pokemon_id})


class MegaBurnTest(unittest.TestCase):
    """メガバーン: 次の自分の番、このカードは「メガバーン」を使えない（v0.35 のあわあわと同じ型 ``DamageThenLockSelf``。ワザは ``AttackKey`` で識別する）。"""

    def test_own_mega_burn_locks_every_source_of_the_same_attack(self):
        """自分のメガバーンを使うと、次の自分の番、自分のメガバーンも、［サイコリンク］で持つほかのフーディンのメガバーンも使えない。ほかのワザは使える。"""
        state = alakazam_board(bench=(mon(SABRINAS_ALAKAZAM), JYNX))
        since = len(state.log)
        state = apply_kernel(state, UseAttack(0, 0))
        effect = state.players[0].active.persistent_effects[0]
        self.assertIsInstance(effect, CannotUseOwnAttack)
        self.assertEqual((effect.created_turn, effect.active_turn, effect.attack_index, effect.target_attack_index), (TURN, TURN + 2, 0, 0))
        self.assertEqual(events(state, since, "damage")[0]["amount"], 60)
        state = end_turn(state)  # ワザで番が終わり、相手の番を終える
        other = state.players[0].bench[0]
        linked = option(state, "psylink", SABRINAS_ALAKAZAM, 0, provider=other.pokemon_id)
        assert_rejected(self, state, UseAttack(0, 0), "ATTACK_LOCKED", IllegalActionError)
        assert_rejected(self, state, UseAttack(0, 0, card=linked.card), "ATTACK_LOCKED", IllegalActionError)
        after = use(state, option(state, "psylink", JYNX, 0), T, T)
        self.assertEqual(after.turn_number, TURN + 3)
        # その次の自分の番には使える（効果ははたらく番の終わりに消える）
        state = end_turn(end_turn(state))
        self.assertEqual(state.players[0].active.persistent_effects, ())
        apply_kernel(state, UseAttack(0, 0))

    def test_linked_mega_burn_locks_the_attacker(self):
        """［サイコリンク］でほかのフーディンのメガバーンを使うと、「このカード」はワザを使ったフーディン。次の自分の番、そのフーディンはどの出どころのメガバーンも
        使えない（供給したフーディンは使える）。同じカードの id のワザなので、効果の形は自分のメガバーンと同じ（``attack_card`` は None。書き出しは形式 13 でもよい）。"""
        state = alakazam_board(bench=(mon(SABRINAS_ALAKAZAM, (P, P, P, P)),))
        other = state.players[0].bench[0]
        linked = option(state, "psylink", SABRINAS_ALAKAZAM, 0, provider=other.pokemon_id)
        state = use(state, linked)
        effect = state.players[0].active.persistent_effects[0]
        self.assertEqual((effect.attack_card, effect.attack_index, effect.target_attack_index), (None, 0, 0))
        self.assertEqual(state.players[0].bench[0].persistent_effects, ())
        state_to_dict(state, format_version=13)
        audited(self, state)
        state = end_turn(state)
        assert_rejected(self, state, UseAttack(0, 0), "ATTACK_LOCKED", IllegalActionError)
        assert_rejected(self, state, UseAttack(0, 0, card=other.card), "ATTACK_LOCKED", IllegalActionError)
        # 供給したフーディンをバトル場に出せば、そのフーディンはメガバーンを使える（効果は受けていない）
        state = apply_kernel(state, Retreat(0, tuple(state.players[0].active.energy[:3]), other.card))
        apply_kernel(state, UseAttack(0, 0))

    def test_effect_from_another_cards_attack_records_the_printing_card(self):
        """［サイコリンク］でナツメのヤドランの「きあいずつき」（次の自分の番、このカードは「きあいずつき」を使えない）を使う。効果を受けるのはワザを使ったフーディンで、
        使えないワザはヤドランのカードの「きあいずつき」（``AttackKey``）。効果はワザを印刷したカードの id を ``attack_card``・``target_attack_card`` に持つ（形式 14。
        形式 13 では書き出せない）。フーディン自身のメガバーンは使える。"""
        state = alakazam_board(bench=(mon(SABRINAS_SLOWBRO),))
        headbutt = option(state, "psylink", SABRINAS_SLOWBRO, 1)
        state = use(state, headbutt)
        effect = state.players[0].active.persistent_effects[0]
        self.assertIsInstance(effect, CannotUseOwnAttack)
        self.assertEqual((effect.attack_card, effect.attack_index, effect.target_attack_index), (SABRINAS_SLOWBRO, 1, 1))
        self.assertEqual(getattr(effect, "target_attack_card", SABRINAS_SLOWBRO), SABRINAS_SLOWBRO)
        with self.assertRaises(ValueError):
            state_to_dict(state, format_version=13)
        written = full(state)["players"][0]["active"]["persistent_effects"][0]
        self.assertEqual(written["attack_card"], SABRINAS_SLOWBRO)
        audited(self, state)
        state = end_turn(state)
        assert_rejected(self, state, UseAttack(0, headbutt.attack_index, card=headbutt.card), "ATTACK_LOCKED", IllegalActionError)
        since = len(state.log)
        after = apply_kernel(state, UseAttack(0, 0))  # メガバーン（位置は同じ 0 番目でも別のワザ）
        self.assertEqual([(e["attack"], e.get("card_id")) for e in events(after, since, "attack")], [("メガバーン", None)])



# ---------------------------------------------------------------- ［へんしん］


def ditto_board(opponent, *, energy=(R, R), bench=(RATTATA,), opponent_bench=(RATTATA,), hand=(), opponent_hand=(), current=0, turn=TURN, **extra):
    return board(mon(DITTO, energy, **extra), opponent, bench=bench, opponent_bench=opponent_bench, hand=hand, opponent_hand=opponent_hand,
                 current=current, turn=turn)


class TransformTest(unittest.TestCase):
    """メタモンの［へんしん］: バトル場にいる限り、相手の対戦ポケモンと同じカードとしてあつかう（docs 5 章）。"""

    def test_form_reads_the_defenders_card_and_keeps_the_real_card(self):
        """今の姿は相手の対戦ポケモンのいちばん上のカード。名前・段階・最大HP・タイプ・弱点・抵抗力・にげる・ワザはそのカードの定義から読む。実際のカード（uid・持ち主・
        ついているカード）はメタモンのまま。相手のポケモンが受けている効果（ダメージ・特殊状態）は写さない。"""
        state = ditto_board(mon(LAPRAS, damage=30, confusion=True))
        ditto, lapras = state.players[0].active, state.players[1].active
        form = current_form(state, ditto)
        self.assertEqual((form.card, form.kind, form.defender), (lapras.card, "transform", lapras.pokemon_id))
        self.assertEqual(state.cards[ditto.card].card_id, DITTO)
        self.assertEqual(state.cards[ditto.card].owner, 0)
        self.assertEqual(E.form_def(state, ditto).name_ja, "ラプラス")
        self.assertEqual((max_hp(state, ditto), type_readings(state, ditto), weakness_of(state, ditto), resistance_of(state, ditto)),
                         (80, (EnergyType.WATER,), EnergyType.LIGHTNING, (None, 0)))
        self.assertEqual((ditto.damage, ditto.conditions.exclusive), (0, None))
        self.assertEqual(routes(state), [("form", LAPRAS, 0, None, None), ("form", LAPRAS, 1, None, None)])
        self.assertEqual([slot.key for slot in powers_of(state, ditto)], [E.PowerKey(DITTO, 0)])  # 写した特殊能力は持たない（ラプラスにはない）
        retreat = E.retreat_cost(state, 0)
        self.assertEqual((retreat.minimum, retreat.maximum), (2, 2))  # ラプラスのにげる 2（メタモンは 1）
        audited(self, state)

    def test_energy_cards_pay_any_color_but_count_once(self):
        """エネルギーカードはどの色のエネルギーとしても使える（炎 2 枚で「あやしいひかり」（水水））。1 枚が出すエネルギーは 1 つのまま（炎 1 枚では払えない）。"""
        state = ditto_board(mon(LAPRAS), energy=(R, R))
        since = len(state.log)
        after = apply_kernel(with_coin_results(state, T), UseAttack(0, 1))
        attack_log = events(after, since, "attack")[0]
        self.assertEqual((attack_log["card"], attack_log["card_id"], attack_log["route"]), (state.players[1].active.card, LAPRAS, "form"))
        self.assertEqual(attack_log["pokemon"], state.players[0].active.card)
        self.assertEqual(events(after, since, "damage")[0]["amount"], 10)
        assert_rejected(self, ditto_board(mon(LAPRAS), energy=(R,)), UseAttack(0, 1), "INSUFFICIENT_ENERGY", IllegalActionError)
        # ［へんしん］がはたらいていなければ（ベンチ・特殊状態）、ワザはない
        assert_rejected(self, ditto_board(mon(LAPRAS), energy=(R, R), confusion=True), UseAttack(0, 1), "INVALID_ATTACK", IllegalActionError)

    def test_counting_typed_energy_is_te1(self):
        """ワザの説明がタイプのエネルギーの数を数えるとき（ラプラスの「みずでっぽう」: 水エネルギーの数で追加のダメージ）、ほかの色のエネルギーカードを水として数えるかは
        決まらない（TE1）。すべて水なら読み方は 1 つ（止めない）。トラッシュする「炎エネルギーカード」はカードの印刷の種類（ヒトカゲの「ひのこ」に水のカードは選べない →
        読み方で選べるカードが変わるので TE1）。"""
        assert_stops(self, ditto_board(mon(LAPRAS), energy=(R, R, R)), UseAttack(0, 0), TE1)
        since = 0
        after = apply_kernel(ditto_board(mon(LAPRAS), energy=(W, W, W)), UseAttack(0, 0))
        self.assertEqual(events(after, since, "damage")[-1]["amount"], 30)  # 10 + 水 2 つぶん（上限 2）×10
        assert_stops(self, ditto_board(mon(CHARMANDER), energy=(W, W)), UseAttack(0, 1), TE1)
        state = ditto_board(mon(CHARMANDER), energy=(R, R))
        after = apply_kernel(state, UseAttack(0, 1))  # 炎のカードだけ: 読み方は 1 つ。決定でトラッシュする炎のカードを選ぶ
        self.assertEqual(after.decision.options, tuple(state.players[0].active.energy))

    def test_power_follows_location_status_and_gas(self):
        """ベンチ・ねむり・マヒ・こんらん・かがくへんかガスでは力が消え、メタモン自身（ワザなし・HP 50・無色）。どくは関係しない。"""
        for label, state in (("bench", board(mon(RATTATA), bench=(mon(DITTO),))),
                             ("sleep", ditto_board(mon(LAPRAS), sleep=True)), ("paralysis", ditto_board(mon(LAPRAS), paralysis=TURN - 1)),
                             ("confusion", ditto_board(mon(LAPRAS), confusion=True)), ("gas", ditto_board(mon(LAPRAS), bench=(mon(MUK),)))):
            ditto = next(p for p in state.players[0].in_play() if state.cards[p.card].card_id == DITTO)
            with self.subTest(label=label):
                self.assertEqual(current_form(state, ditto).kind, "printed")
                self.assertEqual((available_attacks(state, ditto), max_hp(state, ditto)), ((), 50))
        poisoned = ditto_board(mon(LAPRAS), poison=10)
        self.assertEqual(current_form(poisoned, poisoned.players[0].active).kind, "transform")

    def test_form_follows_the_defender(self):
        """相手の入れ替え（突風）・進化・きぜつ・メタモンの「にげる」に、問い合わせのたびの答えが追随する（状態に持たない）。"""
        state = ditto_board(mon(LAPRAS), hand=(GUST,), opponent_bench=(mon(CHARMANDER),))
        state = apply_kernel(state, PlayTrainer(0, card_of(state, 0, GUST)))
        state = answer(state, [state.players[1].bench[0].pokemon_id])
        self.assertEqual(state.cards[current_form(state, state.players[0].active).card].card_id, CHARMANDER)
        self.assertEqual(max_hp(state, state.players[0].active), 50)
        # 相手の番に、相手のヒトカゲがリザードに進化すると、メタモンは今のリザードと同じカード
        state = ditto_board(mon(CHARMANDER, played_turn=0), current=1, turn=TURN + 1, opponent_hand=(CHARMELEON,))
        state = apply_kernel(state, EvolvePokemon(1, card_of(state, 1, CHARMELEON), state.players[1].active.pokemon_id))
        ditto = state.players[0].active
        self.assertEqual((E.form_def(state, ditto).name_ja, max_hp(state, ditto)), ("リザード", 80))
        # メタモンのワザで相手の対戦ポケモンがきぜつ → バトル場が空いている間はメタモン自身。相手が出したポケモンと同じカード
        state = ditto_board(mon(CHARMANDER, damage=40), opponent_bench=(mon(LAPRAS),))
        state = apply_kernel(state, UseAttack(0, 0))
        self.assertEqual(current_form(state, state.players[0].active).kind, "printed")
        while state.decision is not None and state.decision.kind != "promote_active":
            state = answer(state, state.decision.options[:1])
        state = apply_kernel(state, PromoteActive(1, state.players[1].bench[0].card))
        self.assertEqual(E.form_def(state, state.players[0].active).name_ja, "ラプラス")
        audited(self, state)

    def test_evolution_cards_cannot_be_attached(self):
        """「このカードに進化カードをつけることはできない」: ヒトカゲと同じカードとしてあつかわれていても、リザードを重ねられない（名前が合っても。どの進化の入口も
        ``evolution_block`` で止める）。"""
        state = ditto_board(mon(CHARMANDER), hand=(CHARMELEON,))
        ditto = state.players[0].active
        assert_rejected(self, state, EvolvePokemon(0, card_of(state, 0, CHARMELEON), ditto.pokemon_id), "EVOLUTION_PREVENTED", IllegalActionError)
        self.assertEqual(evolution_block(state, ditto, state.card_def(card_of(state, 0, CHARMELEON)))[0], "EVOLUTION_PREVENTED")
        bench_ditto = board(mon(RATTATA), bench=(mon(DITTO),)).players[0].bench[0]
        self.assertEqual(E.evolution_forbidden(board(mon(RATTATA), bench=(mon(DITTO),)), bench_ditto)[0], "EVOLUTION_PREVENTED")

    def test_copied_powers_are_tf1(self):
        """写したカードの特殊能力を持つかは決まらない（TF1）。常にはたらく・自動的にはたらく特殊能力を持つ相手と同じカードになる操作は受け付けない（状態・乱数・ログは
        そのまま）。宣言して使う特殊能力なら姿にはなれるが、写した特殊能力を使う宣言は TF1。メタモン自身の［へんしん］は宣言できない。"""
        state = board(mon(RATTATA), mon(MR_MIME), bench=(mon(DITTO),))
        assert_stops(self, state, Retreat(0, (), state.players[0].bench[0].card), TF1)
        state = ditto_board(mon(VENUSAUR, (G,)), bench=(RATTATA,))
        ditto, venusaur = state.players[0].active, state.players[1].active
        self.assertEqual(current_form(state, ditto).kind, "transform")
        assert_stops(self, state, UsePokemonPower(0, ditto.pokemon_id, 0, card=venusaur.card), TF1)
        assert_stops(self, state, UsePokemonPower(0, ditto.pokemon_id, 0), TF1)  # ``card`` を書かなければ今の姿のカード（フシギバナ）の特殊能力
        assert_rejected(self, state, UsePokemonPower(0, ditto.pokemon_id, 0, card=ditto.card), "POWER_NOT_DECLARABLE", IllegalActionError)

    def test_promote_that_only_creates_tf1_halts(self):
        """相手がバトル場に出すポケモンがどれも TF1 になるなら（答えのない決定を残さず）その前の状態で対戦を止める。ほかの答えがあれば、その答えだけを受け付けない。"""
        state = ditto_board(mon(CHARMANDER, damage=40), opponent_bench=(mon(MR_MIME), mon(RATTATA)))
        state = apply_kernel(state, UseAttack(0, 0))
        while state.decision is not None and state.decision.kind != "promote_active":
            state = answer(state, state.decision.options[:1])
        mime, rattata = state.players[1].bench
        assert_stops(self, state, PromoteActive(1, mime.card), TF1)
        apply_kernel(state, PromoteActive(1, rattata.card))
        state = ditto_board(mon(CHARMANDER, damage=40), opponent_bench=(mon(MR_MIME),))
        state = apply_kernel(state, UseAttack(0, 0))
        while state.decision is not None and state.decision.kind != "promote_active":
            state = answer(state, state.decision.options[:1])
        halted = apply_kernel(state, PromoteActive(1, state.players[1].bench[0].card))
        self.assertEqual((halted.phase, halted.halt.code), (Phase.HALTED, TF1))
        self.assertEqual(halted.players[1].active, None)  # 出す前の状態で止める
        audited(self, halted)

    def test_modified_defender_is_tf2(self):
        """相手の対戦ポケモンが「ばける」でほかのポケモンとしてあつかわれている・ポケモンとして出したなにかの化石なら、どのカードと同じにあつかうかは決まらない（TF2）。"""
        state = ditto_board(mon(BROCKS_NINETALES, (R, R)), current=1, turn=TURN + 1, opponent_hand=(CHARMELEON,))
        ninetales = state.players[1].active
        assert_stops(self, state, UsePokemonPower(1, ninetales.pokemon_id, 0), TF2)
        state = board(mon(RATTATA), {"card": MYSTERIOUS_FOSSIL}, bench=(mon(DITTO),))
        assert_stops(self, state, Retreat(0, (), state.players[0].bench[0].card), TF2)

    def test_ditto_against_ditto_and_alakazam(self):
        """メタモンどうし: 相手のメタモンのいちばん上のカード（メタモン）と同じカード（ワザなし・HP 50）。相手の今の姿をたどらないので循環しない。
        ナツメのフーディン（常にはたらく［サイコリンク］）と同じカードにはならない（TF1）。"""
        state = ditto_board(mon(DITTO, (R,)), bench=(RATTATA,))
        mine, theirs = state.players[0].active, state.players[1].active
        self.assertEqual((current_form(state, mine).card, current_form(state, theirs).card), (theirs.card, mine.card))
        self.assertEqual((available_attacks(state, mine), max_hp(state, mine)), ((), 50))
        state = board(mon(RATTATA), mon(SABRINAS_ALAKAZAM), bench=(mon(DITTO),))
        assert_stops(self, state, Retreat(0, (), state.players[0].bench[0].card), TF1)

    def test_knock_out_keeps_card_conservation(self):
        """相手と同じカードとしてあつかわれていても、きぜつしてトラッシュするのはメタモンとついているカード（相手のカードは動かさない）。"""
        state = ditto_board(mon(CHARMANDER, (R,)), energy=(R,), damage=0, current=1, turn=TURN + 1)
        state = with_coin_results(state, H)
        ditto = state.players[0].active
        ditto_cards = set(ditto.cards()) | set(ditto.energy)
        defender = state.players[1].active
        state.players[0].active.damage = 40  # 盤面を直接作る（ヒトカゲのひっかく 10 できぜつする）
        after = apply_kernel(state, UseAttack(1, 0))
        self.assertTrue(ditto_cards <= set(after.players[0].discard))
        self.assertIn(defender.card, after.players[1].active.cards())
        knock = events(after, len(state.log), "knock_out")[0]
        self.assertEqual(knock["pokemon"], ditto.card)



# ---------------------------------------------------------------- 「ばける」


def ninetales_board(*, hand=(CHARMELEON, RHYDON, R), energy=(R, R, R), opponent=None, current=0, turn=TURN, **extra):
    return board(mon(BROCKS_NINETALES, energy, **extra), opponent or mon(LAPRAS), hand=hand, current=current, turn=turn)


class ShapeshiftTest(unittest.TestCase):
    """タケシのキュウコンの「ばける」（docs 4 章。2000.02.14 版の基準: のせたカードの特殊能力ははたらく。ERR-BROCK-NINETALES（2000年5月）は持ち込まない）。"""

    def test_place_any_evolution_card_and_be_treated_as_it(self):
        """手札の進化カード（名前・段階の一致は要らない。1 進化のリザード・サイドン）から 1 枚選んでのせ、そのポケモンとしてあつかう。進化の重なりではないので、
        場のポケモンの番号・場に出た番・進化した番・ダメージ・エネルギーは変えない。のせたカードは手札から ``disguise`` へ（カードの保存則）。"""
        state = ninetales_board(damage=20)
        ninetales = state.players[0].active
        state = apply_kernel(state, UsePokemonPower(0, ninetales.pokemon_id, 0))
        decision = state.decision
        self.assertEqual((decision.kind, decision.player, decision.min_choices, decision.max_choices), (SELECT_EVOLUTION_CARD, 0, 1, 1))
        self.assertEqual(decision.options, (card_of(state, 0, CHARMELEON), card_of(state, 0, RHYDON)))
        charmeleon = card_of(state, 0, CHARMELEON)
        since = len(state.log)
        state = answer(state, [charmeleon])
        after = state.players[0].active
        self.assertEqual((after.pokemon_id, after.card, after.evolution_stack, after.damage, after.energy, after.played_turn, after.evolved_turn),
                         (ninetales.pokemon_id, ninetales.card, ninetales.evolution_stack, 20, ninetales.energy, ninetales.played_turn, ninetales.evolved_turn))
        self.assertEqual(after.disguise, charmeleon)
        self.assertNotIn(charmeleon, state.players[0].hand)
        self.assertEqual(current_form(state, after), E.Form(charmeleon, "disguise"))
        self.assertEqual((max_hp(state, after), type_readings(state, after), E.form_def(state, after).name_ja), (80, (EnergyType.FIRE,), "リザード"))
        self.assertEqual(routes(state), [("form", CHARMELEON, 0, None, None), ("form", CHARMELEON, 1, None, None)])
        self.assertEqual([e["kind"] for e in events(state, since)], ["disguise"])
        self.assertEqual(events(state, since, "disguise")[0]["card"], charmeleon)
        audited(self, state)
        # のせたカードのワザを使う（ワザを使うのはキュウコン。ログはワザを印刷したカード）
        since = len(state.log)
        used = apply_kernel(state, UseAttack(0, 1))
        attack_log = events(used, since, "attack")[0]
        self.assertEqual((attack_log["pokemon"], attack_log["card"], attack_log["card_id"]), (ninetales.card, charmeleon, CHARMELEON))

    def test_once_per_turn_again_and_revert(self):
        """自分の番に 1 回（もどしても同じ番にはもう使えない）。次の番にのせたままもう一度使うのは DG3。自分の番に、のせたカードをトラッシュしてもどせる（``RemoveDisguise``）。
        のっていなければ ``NOT_DISGUISED``。相手の番・決定を待つ間はできない。"""
        state = shapeshift(ninetales_board(), CHARMELEON)
        ninetales = state.players[0].active
        assert_rejected(self, state, UsePokemonPower(0, ninetales.pokemon_id, 0, card=ninetales.card), "POWER_ALREADY_USED", IllegalActionError)
        reverted = apply_kernel(state, RemoveDisguise(0, ninetales.pokemon_id))
        self.assertIsNone(reverted.players[0].active.disguise)
        self.assertIn(ninetales.disguise, reverted.players[0].discard)
        self.assertEqual(events(reverted, len(state.log), "disguise_removed")[0]["card"], ninetales.disguise)
        assert_rejected(self, reverted, UsePokemonPower(0, ninetales.pokemon_id, 0), "POWER_ALREADY_USED", IllegalActionError)
        assert_rejected(self, reverted, RemoveDisguise(0, ninetales.pokemon_id), "NOT_DISGUISED", IllegalActionError)
        later = end_turn(end_turn(state))
        # 次の自分の番: のせたままもう一度使うのは DG3（宣言の前に止める）
        assert_stops(self, later, UsePokemonPower(0, ninetales.pokemon_id, 0, card=ninetales.card), DG3)
        opponent_turn = end_turn(state)
        assert_rejected(self, opponent_turn, RemoveDisguise(0, ninetales.pokemon_id), "NOT_YOUR_TURN", IllegalActionError)
        with_decision = apply_kernel(ninetales_board(), UsePokemonPower(0, ninetales.pokemon_id, 0))
        assert_rejected(self, with_decision, RemoveDisguise(0, ninetales.pokemon_id), "WRONG_PHASE", IllegalActionError)
        self.assertEqual(command_from_dict(command_to_dict(RemoveDisguise(0, 3))), RemoveDisguise(0, 3))

    def test_no_evolution_card_is_pw3_and_bench_can_shapeshift(self):
        state = ninetales_board(hand=(R, RATTATA))
        assert_stops(self, state, UsePokemonPower(0, state.players[0].active.pokemon_id, 0), "UNRESOLVED_POWER_ZERO_CARDS")
        bench = board(mon(RATTATA), bench=(mon(BROCKS_NINETALES),), hand=(CHARMELEON,))
        target = bench.players[0].bench[0]
        bench = shapeshift(bench, CHARMELEON, pokemon=target)
        self.assertEqual(current_form(bench, bench.players[0].bench[0]).kind, "disguise")

    def test_retreat_cost_and_bench_keep_the_disguise(self):
        """にげるエネルギーはのせたカードの数（サイドンは 3）。ベンチにもどっても、のせたカードのポケモンとしてあつかう（場所の条件は説明にない）。"""
        state = shapeshift(ninetales_board(), RHYDON)
        cost = E.retreat_cost(state, 0)
        self.assertEqual((cost.minimum, cost.maximum), (3, 3))
        state = apply_kernel(state, Retreat(0, tuple(state.players[0].active.energy), state.players[0].bench[0].card))
        benched = state.players[0].bench[-1]
        self.assertEqual((current_form(state, benched).kind, E.form_def(state, benched).name_ja), ("disguise", "サイドン"))
        audited(self, state)

    def test_special_condition_reverts_and_discards_the_card(self):
        """ねむり・マヒ・こんらん状態になったら、のせたカードをトラッシュしてもどる（ログ ``disguise_removed``）。相手のプリンの「こもりうた」でねむりにする。"""
        state = shapeshift(ninetales_board(opponent=mon(JIGGLYPUFF, (R,))), CHARMELEON)
        overlay = state.players[0].active.disguise
        state = end_turn(state)
        since = len(state.log)
        state = apply_kernel(state, UseAttack(1, 0))
        ninetales = state.players[0].active
        self.assertIsNone(ninetales.disguise)
        self.assertIn(overlay, state.players[0].discard)
        kinds = [e["kind"] for e in events(state, since)]
        self.assertEqual(kinds[:3], ["attack", "special_condition", "disguise_removed"])  # 特殊状態になった直後にもどる
        removed = events(state, since, "disguise_removed")[0]
        self.assertEqual((removed["card"], removed["reason"], removed["effect"]), (overlay, "special_condition", f"{JIGGLYPUFF}#0"))
        self.assertEqual(current_form(state, ninetales).kind, "printed")
        audited(self, state)

    def test_reverting_with_damage_at_or_over_the_original_hp_is_mh1(self):
        """リザード（HP 80）としてあつかわれ、70 のダメージがのっている（タケシのキュウコンの HP は 70）。もどす操作は MH1（v0.48。状態は変えない）。
        相手のワザでねむりになって、ワザの中でもどるなら、ワザのあとのきぜつの判定できぜつする（v0.48 と同じ）。"""
        state = shapeshift(ninetales_board(opponent=mon(JIGGLYPUFF, (R,))), CHARMELEON)
        state.players[0].active.damage = 70  # 盤面を直接作る（70 のダメージ）
        assert_stops(self, state, RemoveDisguise(0, state.players[0].active.pokemon_id), MH1)
        ninetales = state.players[0].active
        state = end_turn(state)
        since = len(state.log)
        state = apply_kernel(state, UseAttack(1, 0))
        self.assertEqual([e["kind"] for e in events(state, since)], ["attack", "special_condition", "disguise_removed", "knock_out"])
        self.assertEqual(events(state, since, "knock_out")[0]["pokemon"], ninetales.card)
        self.assertIn(ninetales.card, state.players[0].discard)
        self.assertEqual(state.phase, Phase.TAKE_PRIZE)

    def test_overlay_powers_work_but_not_entry_powers(self):
        """のせたカードの特殊能力ははたらき・使える（2000.02.14 版の基準）。印刷したカード（のせたカードの uid）で識別する。フーディンの［ダメージスワップ］を使う。
        「手札から場に出した時」の特殊能力（わるいゴルバットの［こっそりかみつく］）は、のせたときには使う機会がない。「場に出た時」の特殊能力（わるいカイリューの
        ［てしたをよぶ］）を持つカードは DG2（選べるが選ぶと止める。それしかなければ宣言の前）。"""
        state = shapeshift(board(mon(BROCKS_NINETALES, (R,), damage=20), mon(LAPRAS), bench=(RATTATA,), hand=(ALAKAZAM,)), ALAKAZAM)
        ninetales = state.players[0].active
        slots = powers_of(state, ninetales)
        self.assertEqual([(slot.card, slot.key) for slot in slots], [(ninetales.disguise, E.PowerKey(ALAKAZAM, 0)), (ninetales.card, E.PowerKey(BROCKS_NINETALES, 0))])
        rattata = state.players[0].bench[0]
        moved = apply_kernel(state, UsePokemonPower(0, ninetales.pokemon_id, 0, source=ninetales.pokemon_id, target=rattata.pokemon_id))
        self.assertEqual((moved.players[0].active.damage, moved.players[0].bench[0].damage), (10, 10))
        state = shapeshift(ninetales_board(hand=(DARK_GOLBAT,)), DARK_GOLBAT)
        self.assertIsNone(state.decision)
        state = ninetales_board(hand=(DARK_DRAGONITE, CHARMELEON))
        state = apply_kernel(state, UsePokemonPower(0, state.players[0].active.pokemon_id, 0))
        dragonite = card_of(state, 0, DARK_DRAGONITE)
        self.assertEqual(state.decision.context_value("unresolved_choices"), (dragonite,))
        assert_stops(self, state, ResolveDecision(0, state.decision.id, (dragonite,)), DG2)
        only = ninetales_board(hand=(DARK_DRAGONITE,))
        assert_stops(self, only, UsePokemonPower(0, only.players[0].active.pokemon_id, 0), DG2)

    def test_overlay_psylink_supplies_attacks(self):
        """ナツメのフーディンをのせると、［サイコリンク］がはたらき、自分の場の「超」ポケモンのワザも持つ（ワザを使うのはキュウコン）。"""
        state = shapeshift(board(mon(BROCKS_NINETALES, (P, P, P, P)), mon(LAPRAS), bench=(JYNX,), hand=(SABRINAS_ALAKAZAM,)), SABRINAS_ALAKAZAM)
        self.assertEqual([o.route for o in available_attacks(state, state.players[0].active)], ["form", "psylink", "psylink"])

    def test_chemical_gas_is_dg1(self):
        """「ばける」の力がかがくへんかガスで消える（のせたカードのガス・相手のガス）と、どうなるか決まらない（DG1）。ベトベトンはのせられず（選べるが選ぶと止める）、
        のせているときに相手がベトベトンに進化するのは受け付けない。"""
        state = ninetales_board(hand=(MUK, CHARMELEON))
        state = apply_kernel(state, UsePokemonPower(0, state.players[0].active.pokemon_id, 0))
        muk = card_of(state, 0, MUK)
        assert_stops(self, state, ResolveDecision(0, state.decision.id, (muk,)), DG1)
        state = board(mon(BROCKS_NINETALES, (R,)), mon(GRIMER, played_turn=0), current=0, hand=(CHARMELEON,), opponent_hand=(MUK,))
        state = end_turn(shapeshift(state, CHARMELEON))
        assert_stops(self, state, EvolvePokemon(1, card_of(state, 1, MUK), state.players[1].active.pokemon_id), DG1)

    def test_disguised_pokemon_cannot_evolve(self):
        """「(ただし「進化・退化」はできない)」: リザードとしてあつかわれていても、リザードンを重ねられない。"""
        state = shapeshift(ninetales_board(hand=(CHARMELEON, CHARIZARD)), CHARMELEON)
        state = end_turn(end_turn(state))
        assert_rejected(self, state, EvolvePokemon(0, card_of(state, 0, CHARIZARD), state.players[0].active.pokemon_id), "EVOLUTION_PREVENTED",
                        IllegalActionError)

    def test_knock_out_discards_every_card(self):
        """のせたカードのあるポケモンがきぜつしたら、キュウコン・ロコン・のせたカード・エネルギーをトラッシュする（ログ ``knock_out`` の ``disguise``）。"""
        state = shapeshift(ninetales_board(opponent=mon(JIGGLYPUFF, (R, R))), CHARMELEON)
        ninetales = state.players[0].active
        cards = set(ninetales.cards()) | {ninetales.disguise} | set(ninetales.energy)
        state = end_turn(state)
        state.players[0].active.damage = 70  # 盤面を直接作る（はたく 20 できぜつ）
        state = apply_kernel(state, UseAttack(1, 1))
        self.assertTrue(cards <= set(state.players[0].discard))
        knock = [e for e in state.log if e["kind"] == "knock_out"][-1]
        self.assertEqual((knock["pokemon"], knock["disguise"]), (ninetales.card, ninetales.disguise))



# ---------------------------------------------------------------- 思い出させる


def recall_board(active, *, hand=(RECALL,), bench=(RATTATA,), **extra):
    return board(active, mon(LAPRAS), bench=bench, hand=hand, **extra)


def play_recall(state, player=0):
    return apply_kernel(state, PlayTrainer(player, card_of(state, player, RECALL)))


class RecallTest(unittest.TestCase):
    """思い出させる: あなたの対戦ポケモンが進化カードなら、この番だけ、進化前に持っていたワザを自分のワザとして使ってよい（docs 6 章）。"""

    def test_immediate_pre_evolution_attack_with_its_cost(self):
        """重なっている進化前のカード（ケーシィ）のワザを、ユンゲラーのワザとして使う。必要なエネルギー（超）はそのワザのもの。使ったトレーナーはトラッシュに置き、
        この番の記録（``recalls``）を置く。番の終わりに消える。"""
        state = recall_board(mon(KADABRA, (P,)))
        kadabra = state.players[0].active
        trainer = card_of(state, 0, RECALL)
        since = len(state.log)
        state = play_recall(state)
        self.assertIn(trainer, state.players[0].discard)
        self.assertEqual(state.trainer_in_use, None)
        self.assertEqual([(r.player, r.turn, r.pokemon_id, r.card, r.trainer) for r in state.recalls], [(0, TURN, kadabra.pokemon_id, kadabra.card, trainer)])
        self.assertEqual(events(state, since, "recall")[0]["pokemon_id"], kadabra.pokemon_id)
        recalled = option(state, "recall", ABRA, 0)
        self.assertEqual((recalled.card, recalled.problem), (kadabra.evolution_stack[0], None))
        with self.assertRaises(ValueError):
            state_to_dict(state, format_version=13)
        self.assertEqual(full(state)["recalls"][0]["trainer"], trainer)
        audited(self, state)
        since = len(state.log)
        after = use(state, recalled, T)
        attack_log = events(after, since, "attack")[0]
        self.assertEqual((attack_log["card"], attack_log["card_id"], attack_log["route"]), (recalled.card, ABRA, "recall"))
        self.assertEqual(after.recalls, ())  # ワザで番が終わり、記録は消える
        state_to_dict(after, format_version=13)
        no_energy = play_recall(recall_board(mon(KADABRA)))
        opt = option(no_energy, "recall", ABRA, 0)
        assert_rejected(self, no_energy, UseAttack(0, opt.attack_index, card=opt.card), "INSUFFICIENT_ENERGY", IllegalActionError)

    def test_not_evolved_is_rc1_and_disguised_is_rc4(self):
        """対戦ポケモンが進化していない（効果のないトレーナー）とき使えるかは決まらない（RC1）。「ばける」でほかのポケモンとしてあつかわれているときは RC4。
        どちらも使う前に止める（トレーナーは手札のまま）。"""
        assert_stops(self, recall_board(mon(LAPRAS)), PlayTrainer(0, card_of(recall_board(mon(LAPRAS)), 0, RECALL)), RC1)
        state = shapeshift(recall_board(mon(BROCKS_NINETALES, (R,)), hand=(RECALL, CHARMELEON)), CHARMELEON)
        assert_stops(self, state, PlayTrainer(0, card_of(state, 0, RECALL)), RC4)
        # 使ったあとに「ばける」でのせると、進化前のワザ（タケシのロコン）を選ぶと RC4
        state = play_recall(recall_board(mon(BROCKS_NINETALES, (R, R)), hand=(RECALL, CHARMELEON)))
        state = shapeshift(state, CHARMELEON)
        recalled = option(state, "recall", BROCKS_VULPIX, 0)
        self.assertEqual(recalled.problem[0], RC4)
        assert_stops(self, state, UseAttack(0, recalled.attack_index, card=recalled.card), RC4)

    def test_stage2_lower_stage_is_rc2(self):
        """2 進化ポケモン: すぐ下の 1 進化カード（ナツメのユンゲラー）のワザは使える。いちばん下のたねポケモン（ナツメのケーシィ）のワザは決まらない（RC2）。"""
        state = play_recall(recall_board(mon(SABRINAS_ALAKAZAM, (P, P, P))))
        self.assertEqual([(o.card_id, o.problem and o.problem[0]) for o in available_attacks(state, state.players[0].active) if o.route == "recall"],
                         [(SABRINAS_KADABRA, None), (SABRINAS_KADABRA, None), (SABRINAS_ABRA, RC2)])
        lower = option(state, "recall", SABRINAS_ABRA, 0)
        assert_stops(self, state, UseAttack(0, lower.attack_index, card=lower.card), RC2)

    def test_breeder_stack_uses_the_card_actually_below(self):
        """ポケモン育て屋さんでフシギダネにフシギバナを重ねた 2 進化ポケモン: すぐ下のカードはフシギダネ（飛ばしたフシギソウのカードは場にない）。"""
        state = board(mon(BULBASAUR, (G, G), played_turn=0), mon(LAPRAS), hand=(POKEMON_BREEDER, VENUSAUR, RECALL))
        state = apply_kernel(state, PlayTrainer(0, card_of(state, 0, POKEMON_BREEDER)))
        state = answer(state, [state.players[0].active.pokemon_id])
        state = answer(state, [card_of(state, 0, VENUSAUR)])
        state = play_recall(state)
        self.assertEqual([(o.card_id, o.problem) for o in available_attacks(state, state.players[0].active) if o.route == "recall"], [(BULBASAUR, None)])
        since = len(state.log)
        after = use(state, option(state, "recall", BULBASAUR, 0))
        self.assertEqual(events(after, since, "attack")[0]["card_id"], BULBASAUR)

    def test_target_changed_is_rc3(self):
        """使ったあと対戦ポケモンが入れかわった（ポケモンいれかえ）・進化したら、進化前のワザを選ぶと RC3（使ったときの対戦ポケモンにだけ当てはまるかが決まらない）。"""
        state = play_recall(recall_board(mon(KADABRA, (P,)), hand=(RECALL, SWITCH), bench=(mon(CHARMELEON, (R,)),)))
        state = apply_kernel(state, PlayTrainer(0, card_of(state, 0, SWITCH)))
        state = answer(state, [state.players[0].bench[0].pokemon_id])
        recalled = option(state, "recall", CHARMANDER, 0)
        self.assertEqual(recalled.problem[0], RC3)
        assert_stops(self, state, UseAttack(0, recalled.attack_index, card=recalled.card), RC3)
        state = play_recall(recall_board(mon(CHARMELEON, (R, R)), hand=(RECALL, CHARIZARD)))
        state = apply_kernel(state, EvolvePokemon(0, card_of(state, 0, CHARIZARD), state.players[0].active.pokemon_id))
        self.assertEqual({o.problem[0] for o in available_attacks(state, state.players[0].active) if o.route == "recall"}, {RC3})


# ---------------------------------------------------------------- まねるワザ・1 度だけのワザ・VS1・観測


class CopiedAndVirtualAttackTest(unittest.TestCase):
    """既存のまねるワザから見た今のワザ（ゆびをふる・ドわすれ）と、1 度だけ使えるワザ（VA1）・［へんしょく］（VS1）。"""

    def test_metronome_sees_linked_attacks_once_per_attack(self):
        """ピッピの「ゆびをふる」は、相手の対戦ポケモンが今持つワザ（［サイコリンク］のワザを含む）から、ワザ（``AttackKey``）ごとに 1 つ選ぶ（同じワザを 2 匹が
        供給しても 1 つ）。選べるものが v0.48 までの並びと違うので、決定は ``copy_attacks`` を持つ。メガバーン（番をまたぐ効果）は今までどおりエンジンの未対応。"""
        state = board(mon(CLEFAIRY, (P, P, P)), mon(SABRINAS_ALAKAZAM, (P,)), opponent_bench=(JYNX, JYNX))
        state = apply_kernel(state, UseAttack(0, 1))
        decision = state.decision
        self.assertEqual(decision.options, (0, 1, 2))
        self.assertEqual(decision.context_value("copy_attacks"), ((SABRINAS_ALAKAZAM, 0), (JYNX, 0), (JYNX, 1)))
        self.assertEqual(decision.context_value("unsupported_choices"), (0,))
        since = len(state.log)
        after = answer(with_coin_results(state, H, H), [1])
        self.assertEqual(events(after, since, "damage")[0]["amount"], 20)
        audited(self, after)
        # 相手が今の姿のワザだけなら、v0.48 までと同じ形（``copy_from``）
        plain = apply_kernel(board(mon(CLEFAIRY, (P, P, P)), mon(LAPRAS)), UseAttack(0, 1))
        self.assertIsNone(plain.decision.context_value("copy_attacks"))

    def test_amnesia_locks_a_linked_attack(self):
        """ニョロゾの「ドわすれ」で、相手のナツメのフーディンが［サイコリンク］で持つルージュラの「おうふくびんた」を選ぶ。次の相手の番、フーディンはそのワザ
        （どの出どころでも）を使えない。メガバーンは使える。"""
        state = board(mon(POLIWHIRL, (W, W)), mon(SABRINAS_ALAKAZAM, (P, P, P, P)), opponent_bench=(JYNX,))
        state = apply_kernel(state, UseAttack(0, 0))
        self.assertEqual(state.decision.context_value("lock_attacks"), ((SABRINAS_ALAKAZAM, 0), (JYNX, 0), (JYNX, 1)))
        state = answer(state, [1])
        effect = state.players[1].active.persistent_effects[0]
        self.assertEqual((effect.target_attack_index, effect.target_attack_card), (0, JYNX))
        jynx_attack = option(state, "psylink", JYNX, 0, pokemon=state.players[1].active)
        assert_rejected(self, state, UseAttack(1, jynx_attack.attack_index, card=jynx_attack.card), "ATTACK_LOCKED", IllegalActionError)
        apply_kernel(state, UseAttack(1, 0))
        audited(self, state)

    def test_once_attacks_through_another_card_are_va1(self):
        """「このワザは、このカードが場に出てから、1回しか使えない」ワザを、ほかのカードのワザとして使う（［へんしん］でカモネギと同じカード・「ばける」でキョウのスピアー）
        のは VA1（選べるが選ぶと止める）。カモネギ自身の「ネギでたたく」は v0.44 のまま。"""
        state = ditto_board(mon(FARFETCHD), energy=(R, R, R))
        leek = option(state, "form", FARFETCHD, 0)
        self.assertEqual(leek.problem[0], VA1)
        assert_stops(self, state, UseAttack(0, 0), VA1)
        apply_kernel(state, UseAttack(0, 1))  # ナベでたたく（1 度だけのワザではない）
        state = shapeshift(ninetales_board(hand=(KOGAS_BEEDRILL,), energy=(R, R, R)), KOGAS_BEEDRILL)
        self.assertEqual(option(state, "form", KOGAS_BEEDRILL, 1).problem[0], VA1)
        own = board(mon(FARFETCHD, (R,)), mon(LAPRAS))
        self.assertIsNone(option(own, "form", FARFETCHD, 0).problem)

    def test_shift_color_supplier_after_its_turn_is_vs1(self):
        """モルフォンの［へんしょく］で「超」にした番には、フーディンはモルフォンのワザを持つ。使った番のあと（色が続くか決まらない。VS1）は、そのワザを選ぶと VS1。"""
        state = alakazam_board(energy=(G, G, G, P), bench=(mon(VENOMOTH),))
        venomoth = state.players[0].bench[0]
        state = apply_kernel(state, UsePokemonPower(0, venomoth.pokemon_id, 0))
        state = answer(state, [E.COLORS.index(EnergyType.PSYCHIC)])
        self.assertEqual({o.problem for o in available_attacks(state, state.players[0].active) if o.route == "psylink"}, {None})
        state = end_turn(end_turn(state))
        linked = [o for o in available_attacks(state, state.players[0].active) if o.route == "psylink"]
        self.assertTrue(linked)
        self.assertEqual({o.problem[0] for o in linked}, {VS1})
        assert_stops(self, state, UseAttack(0, linked[0].attack_index, card=linked[0].card), VS1)


class ObservationAndSerializationTest(unittest.TestCase):
    """観測・書き出し（形式 14）・コマンドの辞書・先読みの方法の一致。"""

    def test_observation_shows_form_attacks_and_real_card(self):
        """観測は、実際のカード（``card``・``card_id``）と今の姿（``form``）・今のワザ（``attacks``）・特殊能力（``powers``）を分けて見せる。「ばける」でのせたカードは
        表向きなので両方のプレイヤーに見える。「ばける」の決定の選べるもの（手札のカード）は決めるプレイヤーだけ。"""
        state = ditto_board(mon(LAPRAS))
        seen = observe(state, 1)["players"][0]["active"]
        self.assertEqual((seen["card_id"], seen["form"]["card_id"], seen["form"]["kind"]), (DITTO, LAPRAS, "transform"))
        self.assertEqual([a["card_id"] for a in seen["attacks"]], [LAPRAS, LAPRAS])
        self.assertEqual([p["card_id"] for p in seen["powers"]], [DITTO])
        self.assertEqual(seen["hp"], 80)
        state = shapeshift(ninetales_board(), CHARMELEON)
        for viewer in (0, 1):
            seen = observe(state, viewer)["players"][0]["active"]
            with self.subTest(viewer=viewer):
                self.assertEqual(seen["disguise"]["card_id"], CHARMELEON)
                self.assertEqual(seen["form"]["kind"], "disguise")
        pending = apply_kernel(ninetales_board(), UsePokemonPower(0, ninetales_board().players[0].active.pokemon_id, 0))
        self.assertEqual(observation_problems(pending), [])
        self.assertNotIn("options", observe(pending, 1).get("decision") or {})

    def test_format_14_and_older_formats(self):
        """「ばける」でのせたカード・「思い出させる」の記録・ほかのカードのワザが与えた効果は形式 14 で書き出す。形式 1〜13 は書き出せない（``ValueError``。黙って落とさない）。
        どれもなければ形式 13 と同じ。v0.50 で形式 15（退化した番。``devolved_turn``）を加えた（退化していなければ None）。"""
        self.assertEqual(max(FORMAT_VERSIONS), 20)  # v0.56 で 16（trainer_effects）、v0.57 で 17（stadium）、v0.58 で 18（trainer_stack）、v0.59 で 19（energy_roles）を加えた
        plain = ninetales_board()
        latest, older = state_to_dict(plain, format_version=14), state_to_dict(plain, format_version=13)
        self.assertEqual(latest["recalls"], [])
        for player in latest["players"]:
            for pokemon in [player["active"], *player["bench"]]:
                self.assertIsNone(pokemon.pop("disguise"))
        del latest["recalls"]
        self.assertEqual({k: v for k, v in latest.items() if k != "format_version"}, {k: v for k, v in older.items() if k != "format_version"})
        state = shapeshift(ninetales_board(), CHARMELEON)
        with self.assertRaises(ValueError):
            state_to_dict(state, format_version=13)
        self.assertEqual(full(state)["players"][0]["active"]["disguise"], {"card": state.players[0].active.disguise, "card_id": CHARMELEON})
        self.assertEqual(serialization_problems(state), [])

    def test_commands_round_trip(self):
        for command in (UseAttack(0, 1, card=5), UsePokemonPower(0, 3, 0, card=7), RemoveDisguise(1, 4)):
            with self.subTest(command=command):
                self.assertEqual(command_from_dict(command_to_dict(command)), command)
        self.assertNotIn("card", command_to_dict(UseAttack(0, 1)))  # v0.48 までの形
        self.assertNotIn("card", command_to_dict(UsePokemonPower(0, 3, 0)))

    def test_preflight_modes_agree_on_virtual_attacks(self):
        """［サイコリンク］・［へんしん］・「ばける」・「思い出させる」のワザは、どの先読みの方法でも同じ結果（状態・ログ・乱数）。"""
        cases = (
            (alakazam_board(bench=(JYNX,)), lambda s: option(s, "psylink", JYNX, 0)),
            (ditto_board(mon(LAPRAS)), lambda s: option(s, "form", LAPRAS, 1)),
            (shapeshift(ninetales_board(), CHARMELEON), lambda s: option(s, "form", CHARMELEON, 1)),
            (play_recall(recall_board(mon(KADABRA, (P,)))), lambda s: option(s, "recall", ABRA, 0)),
        )
        for state, pick in cases:
            opt = pick(state)
            results = {mode: snapshot(use(state, opt, H, T, H, mode=mode)) for mode in PREFLIGHT_MODES}
            with self.subTest(card=opt.card_id):
                self.assertEqual(len({repr(r) for r in results.values()}), 1)



# ---------------------------------------------------------------- 新しく到達する組み合わせ（docs 7 章）


class ReachableCombinationTest(unittest.TestCase):
    """v0.49 のワザ・姿の変更で到達するようになった組み合わせ。内部エラーにせず、明示的に止めるか、正しく続ける。"""

    def test_trainer_with_only_dead_end_answers_is_refused_before_play(self):
        """ポケモンいれかえの答えがどれも決められない姿（相手のメタモンの TF1）になるなら、使う前に止める（使用中のトレーナーを残したまま止めない）。ほかの答えがあれば、
        その答えだけを受け付けない。"""
        state = ditto_board(mon(LAPRAS), opponent_bench=(mon(SABRINAS_GASTLY, (P,)),), opponent_hand=(SWITCH,), current=1, turn=TURN + 1)
        assert_stops(self, state, PlayTrainer(1, card_of(state, 1, SWITCH)), TF1)
        state = ditto_board(mon(LAPRAS), opponent_bench=(mon(SABRINAS_GASTLY, (P,)), RATTATA), opponent_hand=(SWITCH,), current=1, turn=TURN + 1)
        state = apply_kernel(state, PlayTrainer(1, card_of(state, 1, SWITCH)))
        gastly, rattata = state.players[1].bench
        assert_stops(self, state, ResolveDecision(1, state.decision.id, (gastly.pokemon_id,)), TF1)
        after = answer(state, [rattata.pokemon_id])
        self.assertEqual(E.form_def(after, after.players[0].active).name_ja, "コラッタ")
        audited(self, after)

    def test_max_hp_set_and_gaseous_form_never_meet(self):
        """「きょだいか」（最大HPを 80 にする）と［ガスのからだ］（最大HPを大きくする）が同じポケモンにはたらく組（``max_hp`` が RuntimeError にする組）は、
        メタモンがキョウのメタモンと同じカードとして「きょだいか」を使い、そのあと相手の対戦ポケモンがナツメのゴースになるときに起こりうるが、［ガスのからだ］は常に
        はたらく特殊能力なので TF1 で止める（その状態にならない）。"""
        state = ditto_board(mon(KOGAS_DITTO), energy=(R, R), opponent_bench=(mon(SABRINAS_GASTLY, (P,)),), opponent_hand=(SWITCH,))
        state = apply_kernel(with_coin_results(state, H), UseAttack(0, 0))
        ditto = state.players[0].active
        self.assertEqual(max_hp(state, ditto), 80)
        assert_stops(self, state, PlayTrainer(1, card_of(state, 1, SWITCH)), TF1)

    def test_switch_max_hp_drop_depends_on_the_chosen_bench(self):
        """メタモンの最大HPは相手の対戦ポケモンで変わるので、突風で選ぶ控えによって MH1 になるかが変わる。下がる控えだけを受け付けない（v0.48 の
        ``switch_max_hp_drop_check`` は、どの控えでも下がるときだけ使う前に止める）。"""
        state = ditto_board(mon(LAPRAS), opponent_bench=(mon(CHARMANDER), mon(CHANSEY)), damage=60, hand=(GUST,))
        state = apply_kernel(state, PlayTrainer(0, card_of(state, 0, GUST)))
        charmander, chansey = state.players[1].bench
        assert_stops(self, state, ResolveDecision(0, state.decision.id, (charmander.pokemon_id,)), MH1)
        after = answer(state, [chansey.pokemon_id])
        self.assertEqual(max_hp(after, after.players[0].active), 120)
        # カビゴン（［めんえき］は常にはたらく特殊能力）を選ぶと TF1。どの控えも止まるなら使う前に止める（最初に見つけた理由）
        mixed = ditto_board(mon(LAPRAS), opponent_bench=(mon(CHARMANDER), mon(SNORLAX)), damage=60, hand=(GUST,))
        assert_stops(self, mixed, PlayTrainer(0, card_of(mixed, 0, GUST)), MH1)
        only = ditto_board(mon(LAPRAS), opponent_bench=(mon(CHARMANDER),), damage=60, hand=(GUST,))
        assert_stops(self, only, PlayTrainer(0, card_of(only, 0, GUST)), MH1)

    def test_guts_after_a_discard_decision_keeps_its_record(self):
        """わるいリザードンの「れんぞくファイヤーボール」（ダメージのあとにエネルギーをトラッシュする決定）でサカキのカイリキーが HP 以上になる。決定をまたいで
        こんじょうの写しを運び、きぜつの判定で「こんじょう」を使うかを聞く（v0.48 までは内部エラー。v0.49 で「ばける」・［へんしん］からも使えるようになったので直した）。"""
        def case(state):
            state = use(state, option(state, "form", DARK_CHARIZARD, 1), H, H)
            self.assertEqual(state.decision.kind, "discard_energy")
            state = answer(state, state.decision.options[:state.decision.min_choices])
            self.assertEqual((state.decision.kind, state.decision.player), ("ko_prevention", 1))
            audited(self, state)
        machamp = mon(GIOVANNIS_MACHAMP, (F,), damage=90, evolved_from=[GIOVANNIS_MACHOP, GIOVANNIS_MACHOKE])
        case(board(mon(DARK_CHARIZARD, (R, R, R), evolved_from=[ROCKET_CHARMANDER, DARK_CHARMELEON]), machamp))
        case(shapeshift(board(mon(BROCKS_NINETALES, (R, R, R)), machamp, hand=(DARK_CHARIZARD,)), DARK_CHARIZARD))

    def test_guts_after_a_linked_attack(self):
        """［サイコリンク］のワザでサカキのカイリキーが HP 以上になる。「こんじょう」の決定のワザのカード id はワザを印刷したカード（ルージュラ）。"""
        machamp = mon(GIOVANNIS_MACHAMP, (F,), damage=90, evolved_from=[GIOVANNIS_MACHOP, GIOVANNIS_MACHOKE])
        state = alakazam_board(bench=(JYNX,), opponent=machamp)
        state = use(state, option(state, "psylink", JYNX, 0), H, H)
        self.assertEqual(state.decision.context_value("attack")[2], JYNX)
        audited(self, state)

    def test_message_attack_through_transform_returns_ditto(self):
        """メタモンがキョウのポッポ（40）と同じカードとして「でんれい」を使う。山札にもどるのはメタモン（実際のカード）で、そのあとの決定の続きはワザを印刷したカードの id。"""
        state = ditto_board(mon(KOGAS_PIDGEY_40), energy=(R,), bench=(RATTATA,))
        ditto = state.players[0].active
        state = apply_kernel(state, UseAttack(0, 0))
        self.assertIn(ditto.card, state.players[0].deck)
        self.assertEqual(state.decision.context_value("use")[2], KOGAS_PIDGEY_40)
        audited(self, state)
        while state.decision is not None and state.decision.resume == "attack":
            state = answer(state, state.decision.options[:max(1, state.decision.min_choices)])
        audited(self, state)



class GameTest(unittest.TestCase):
    """正式な対戦開始（new_game・60 枚・サイド 6 枚）からの対戦（tools/existing_effect_games.py の v0.49 の組の手順）。"""

    def test_batch_runs_without_audit_failures(self):
        """v0.49 の 4 組を 2 seed ずつ（席を入れかえて 16 局）。どれも監査の失敗（やり直し・不変条件・ログ・書き出し・観測）・想定外の拒否・内部エラー・手数の上限がなく、
        4 枚の処理（［サイコリンク］のワザ・メガバーン・［へんしん］の今の姿のワザ・「ばける」とおにび・のせたカードをもどす操作・思い出させる）が使われる（勝敗は判断に使わない）。
        決められない姿で拒否された決定の答えは、別の答えで続ける（どの答えでも止まる局は ``halted``）。"""
        from tools import existing_effect_games as games

        results = games.run(range(2), pairings=games.PAIRINGS_V0_49)
        totals, policy = {}, {}
        for run in results.values():
            for game in run["games"]:
                self.assertEqual(game["audit"], {}, game["seed"])
                self.assertNotIn(game["outcome"], ("internal_error", "unexpected_rejection", "step_limit"), game.get("error"))
                if game["outcome"] == "halted":
                    self.assertIn(game["halt_code"], NEW_CODES + (MH1,))
                for key, count in game["policy"].items():
                    policy[key] = policy.get(key, 0) + count
                for card, uses in game.get("card_uses", {}).items():
                    for key, count in uses.items():
                        totals[(card, key)] = totals.get((card, key), 0) + count
        for card, key in ((SABRINAS_ALAKAZAM, "v049_route_psylink"), (SABRINAS_ALAKAZAM, "attack#0"), (SABRINAS_ALAKAZAM, "persistent_effect_added#0"),
                          (DITTO, "v049_route_form"), (BROCKS_NINETALES, "disguise"), (BROCKS_NINETALES, "disguise_removed_revert"),
                          (BROCKS_NINETALES, "damage#0"), (RECALL, "recall")):
            with self.subTest(card=card, key=key):
                self.assertGreater(totals.get((card, key), 0), 0)
        for key in ("v049_attack_psylink", "v049_attack_form_transform", "v049_attack_recall", "v049_attack_form_disguise"):
            with self.subTest(key=key):
                self.assertGreater(policy.get(key, 0), 0)


class DocumentTest(unittest.TestCase):
    def test_document_names_the_stop_codes(self):
        text = DOC.read_text(encoding="utf-8")
        for code in NEW_CODES:
            self.assertIn(code, text)


if __name__ == "__main__":
    unittest.main()

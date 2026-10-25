"""v0.100（docs/sketch-perish-song-history-v0.100.md）: ドーブル・ムウマの 2 枚（ワザ 3）と、前の相手の番のワザの記録・ワザの効果による直接の「きぜつ」。

根拠は kyuura データの採用（kyuura ``73a1690`` の data/cards.json の日本語の印刷の文面。2 枚を指す LD-・CC-・CR-・UQ-・エラッタはない）と、既存の規定と読み方の記録
（v0.62 の履歴の「このカード」・受けた記録の意味・使った時点、v0.31 の相手のワザを自分のワザとして使う処理と ``copy_status``、v0.72 の「めざめのキッス」の順番、v0.3b のねむり）。
英語版の文面（「Smeargle was in play during that attack」「anything else required」）・現代のルール・後年の裁定（『トレーナーズ』Vol.9 の Q&A）は持ち込まない。公式ガイドブックの
新しい読み直し・カードの画像の照合はしていない。盤面は ``build_test_state`` で作った 1 か所の規定を確かめるためのもので、``new_game`` からの自然な対戦の結果ではない（対戦は
tools/existing_effect_games.py の ``--batch v0.100``）。前の番の記録は、盤面の前の番から実際にコマンドを処理して作る（記録・特殊状態を手で置くのは、今の写しで自然には起こりにくい
組み合わせ（ねむりの相手がバリアーで受けなかった記録など）と前の版の状態の写しの確かめだけで、そう書いた）。
"""

from __future__ import annotations

import copy
import dataclasses
import json
import pathlib
import pickle
import unittest

from kyuura_engine import (
    DEFAULT_EFFECTS,
    AttachEnergy,
    AttackKey,
    EndTurn,
    PlayBasicToBench,
    PlayTrainer,
    ResolveDecision,
    Retreat,
    UseAttack,
)
from kyuura_engine import effects as E
from kyuura_engine.cards import load_card_pool, pool_from_extract, read_extract
from kyuura_engine.coins import CoinSide
from kyuura_engine.errors import IllegalActionError
from kyuura_engine.history import (
    NOT_RECEIVED,
    RECEIVED,
    RECEIVED_UNDETERMINED,
    history_needed,
    named_attack_received,
    turn_attack,
    turn_field,
    turn_history_needed,
)
from kyuura_engine.observation import observe
from kyuura_engine.resolution.questions import QUESTIONS
from kyuura_engine.serialize import FORMAT_VERSIONS, state_to_dict
from kyuura_engine.state import ASLEEP, SpecialConditions, TurnAttack
from tests import helpers as H
from tests.helpers import apply_kernel, with_coin_results
from tests.release_catalog import cards_after, cards_before
from tests.test_neo_trainer_components_v0_80 import audited, new_events, rejects
from tests.test_power_suppression_lasting_locks_v0_92 import mon, uid
from tests.test_unown_family_powers_v0_96 import board
from tests.test_unown_idfnj_powers_v0_97 import snap

ROOT = pathlib.Path(__file__).resolve().parent.parent
DOC = ROOT / "docs" / "sketch-perish-song-history-v0.100.md"
HD, TL = CoinSide.HEADS, CoinSide.TAILS
W, PS, G, F = H.WATER, H.PSYCHIC, H.GRASS, H.FIRE
SMEARGLE, MISDREAVUS = "neo2-052", "neo3-035"
V0100 = (SMEARGLE, MISDREAVUS)
V0100_ATTACKS = [AttackKey(SMEARGLE, 0), AttackKey(MISDREAVUS, 0), AttackKey(MISDREAVUS, 1)]
SK1, SK2, PSG1 = "UNRESOLVED_SKETCH_PRESENCE", "UNRESOLVED_SKETCH_COPIED_ATTACK", "UNRESOLVED_PERISH_SONG_RECEIVED_ATTACK"
HC9, COPY_UNSUPPORTED, MISSING = "UNRESOLVED_COPIED_ATTACK", "UNSUPPORTED_COPIED_ATTACK", "UNSUPPORTED_HISTORY_TURN_RECORD_MISSING"
# 依頼で示された固定データの日本語（写しの文面と照らす。広い正規化をしない）
QUOTED = {
    AttackKey(SMEARGLE, 0): ("前の相手の番に、相手のポケモンがワザを使っていたなら、そのワザを、このカードが持っているワザとして使う。(そのワザに必要な「エネルギー」がついていなくても、"
                             "かまわない。)前の相手の番、このカードが場に出ていなければ、このワザは失敗する。"),
    AttackKey(MISDREAVUS, 0): "相手を「ねむり」状態にする。",
    AttackKey(MISDREAVUS, 1): "このワザを受ける相手が「ねむり」状態で、前の自分の番に「やみのひとみ」を受けていたなら、相手は「きぜつ」する。",
}
NAMES = {AttackKey(SMEARGLE, 0): "スケッチ", AttackKey(MISDREAVUS, 0): "やみのひとみ", AttackKey(MISDREAVUS, 1): "ほろびのうた"}
TURN = 7
EFFECT_GUARD = "ES2-033"


def attack(state, index=0, *coins, player=None):
    player = state.current_player if player is None else player
    return apply_kernel(with_coin_results(state, *coins) if coins else state, UseAttack(player, index))


def end(state, *coins):
    return apply_kernel(with_coin_results(state, *coins) if coins else state, EndTurn(state.current_player))


def settle(state):
    """待っている決定（サイドを取る・バトル場に出す）に、選べるものの最初で答える（番が進むまで）。"""
    while state.decision is not None:
        d = state.decision
        state = apply_kernel(state, ResolveDecision(d.player, d.id, tuple(d.options[:max(1, d.min_choices)])))
    return state


def pid(state, card_id, player=0):
    return next(p.pokemon_id for p in state.players[player].in_play() if state.cards[p.card].card_id == card_id)


def pokemon(state, card_id, player=0):
    return state.find_pokemon(pid(state, card_id, player))[1]


def kinds(before, after, *names):
    return [e["kind"] for e in new_events(before, after, *names)]


def damages(before, after):
    """ダメージのログの (受けたポケモンのカード, 量)。"""
    return [(e["pokemon"], e["amount"]) for e in new_events(before, after, "damage")]


def card(state, card_id, player=0):
    return pokemon(state, card_id, player).card


def opponent_turn(me_active, opponent, *, act=None, index=0, coins=(), my_coins=(), turn=TURN, **kw):
    """``turn - 2`` 番（自分の番）を終え、``turn - 1`` 番（相手の番）に ``act``（盤面を受けて盤面を返す）を行い、ワザ ``index`` を使って（None なら番を終える）、``turn`` 番
    （自分の番）になった盤面。番の始めの記録（プレイヤーの記録 ``TurnField``）はエンジンが作る。"""
    state = board(me_active, opponent=opponent, current=0, turn=turn - 2, **kw)
    state = settle(end(state, *my_coins))
    if act is not None:
        state = act(state)
    state = settle(end(state, *coins) if index is None else attack(state, index, *coins))
    assert (state.turn_number, state.current_player, state.decision) == (turn, 0, None), (state.turn_number, state.current_player, state.decision)
    return state


# ---------------------------------------------------------------- 2 章: 対象・登録・文面・記録


class RegistrationTest(unittest.TestCase):
    def test_every_attack_is_registered_with_the_printed_text(self):
        pool = load_card_pool()
        self.assertEqual(tuple(read_extract()["pool_v0_100"]), V0100)
        for key, text in QUOTED.items():
            with self.subTest(key=key):
                entry = DEFAULT_EFFECTS.attack_entry(key.card_id, key.attack_index)
                printed = pool.definitions[key.card_id].attacks[key.attack_index]
                self.assertEqual((printed.name_ja, printed.text_ja, printed.damage, printed.damage_display), (NAMES[key], text, None, None))
                self.assertEqual((entry.name_ja, entry.text_ja, entry.play_text_ja, entry.source), (NAMES[key], text, text, "kyuura data/cards.json"))
                self.assertIsNone(DEFAULT_EFFECTS.attack_problem(key.card_id, printed, pool.definitions[key.card_id].attacks))
        self.assertEqual(DEFAULT_EFFECTS.attack_entry(SMEARGLE, 0).effect, E.UseLastOpponentAttack())
        self.assertIs(type(DEFAULT_EFFECTS.attack_entry(MISDREAVUS, 0).effect), E.PutToSleep)  # v0.3b の既存の型（ダメージの要素を作らない）
        self.assertEqual(DEFAULT_EFFECTS.attack_entry(MISDREAVUS, 1).effect, E.KnockOutIfAsleepAndReceived("やみのひとみ"))
        smeargle, misdreavus = pool.definitions[SMEARGLE], pool.definitions[MISDREAVUS]
        self.assertEqual((smeargle.stage, smeargle.hp, smeargle.pokemon_type, smeargle.weakness, smeargle.resistance, smeargle.retreat_cost, smeargle.powers),
                         ("basic", 50, E.EnergyType.COLORLESS, E.EnergyType.FIGHTING, E.EnergyType.PSYCHIC, 1, ()))
        self.assertEqual((misdreavus.stage, misdreavus.hp, misdreavus.pokemon_type, misdreavus.weakness, misdreavus.resistance, misdreavus.retreat_cost),
                         ("basic", 50, E.EnergyType.PSYCHIC, None, E.EnergyType.FIGHTING, 1))
        self.assertEqual([tuple(t.value for t in a.cost) for a in misdreavus.attacks], [("psychic",), ("psychic",) * 3])
        self.assertEqual(tuple(t.value for t in smeargle.attacks[0].cost), ("colorless", "colorless"))
        for card in V0100:
            self.assertIn(card, pool.playable_ids)

    def test_texts_are_not_normalized(self):
        """引用と 1 字ずつ同じ文面だけを受け付ける（条件・ワザの名前・数を変えた文面、英語版の条件を足した文面は受け付けない）。"""
        pool = load_card_pool()
        sketch = pool.definitions[SMEARGLE].attacks[0]
        perish = pool.definitions[MISDREAVUS].attacks[1]
        for effect, printed, changed in (
            (E.UseLastOpponentAttack(), sketch, sketch.text_ja.replace("(そのワザに必要な「エネルギー」がついていなくても、かまわない。)", "")),
            (E.UseLastOpponentAttack(), sketch, sketch.text_ja.replace("「エネルギー」", "「エネルギー」やほかの条件")),
            (E.UseLastOpponentAttack(), sketch, sketch.text_ja.replace("前の相手の番、このカードが場に出ていなければ、このワザは失敗する。", "")),
            (E.UseLastOpponentAttack(), sketch, sketch.text_ja.replace("相手のポケモン", "相手の対戦ポケモン")),
            (E.KnockOutIfAsleepAndReceived("やみのひとみ"), perish, perish.text_ja.replace("やみのひとみ", "さいみんじゅつ")),
            (E.KnockOutIfAsleepAndReceived("やみのひとみ"), perish, perish.text_ja.replace("「ねむり」状態で、", "")),
            (E.KnockOutIfAsleepAndReceived("やみのひとみ"), perish, perish.text_ja.replace("前の自分の番", "前の相手の番")),
        ):
            with self.subTest(changed=changed):
                self.assertNotEqual(effect.check(dataclasses.replace(printed, text_ja=changed)), [])
        self.assertNotEqual(E.KnockOutIfAsleepAndReceived("さいみんじゅつ").check(perish), [])
        self.assertNotEqual(E.KnockOutIfAsleepAndReceived("さいみんじゅつ").card_problems(perish, pool.definitions[MISDREAVUS].attacks), [])
        self.assertEqual(E.KnockOutIfAsleepAndReceived("やみのひとみ").card_problems(perish, pool.definitions[MISDREAVUS].attacks), [])

    def test_types(self):
        sketch, perish = E.UseLastOpponentAttack(), E.KnockOutIfAsleepAndReceived("やみのひとみ")
        self.assertEqual((sketch.reads_turn_history, sketch.reads_history, sketch.opponent_effect_elements), (True, False, ()))
        self.assertEqual((perish.reads_turn_history, perish.reads_history, perish.opponent_effect_elements), (False, True, (E.KNOCK_OUT_ELEMENT,)))
        self.assertIn(E.KNOCK_OUT_ELEMENT, E.ATTACK_ELEMENTS)
        self.assertEqual(E.PutToSleep.opponent_effect_elements, (E.SLEEP,))

    def test_unregistered_without_the_v0_100_entries(self):
        """今回の登録を除くと対戦に使えなくなるのは、ちょうど 2 枚。過去の範囲は ``cards_before``・``cards_after`` で切り出す。"""
        registry = DEFAULT_EFFECTS.without_attacks(DEFAULT_EFFECTS.id, V0100_ATTACKS)
        before = pool_from_extract(read_extract(), registry)
        self.assertEqual(load_card_pool().playable_ids - before.playable_ids, frozenset(V0100))
        self.assertEqual(set(V0100) & set(cards_before(read_extract(), "0.100")), set())
        self.assertEqual(set(cards_after(read_extract(), "0.99")), set(V0100))

    def test_extract_values(self):
        cards = {c["id"]: c for c in read_extract()["cards"]}
        for card in V0100:
            self.assertNotIn("corrections", cards[card])
            self.assertEqual(cards[card]["data_gaps"], [])
            self.assertIsNone(cards[card]["pokemon"]["rules_text"])
        self.assertEqual({c: cards[c]["jp_print"]["level"] for c in V0100}, {SMEARGLE: 27, MISDREAVUS: 25})
        self.assertEqual(cards[SMEARGLE]["ja_text_source"], "https://nazonobasho.com/neo2-052-doble/")
        self.assertIn("pokemonwiki.com", cards[MISDREAVUS]["ja_text_source"])
        # 日英の違いの記録（確度: 確実）は写しに残る（処理に使う文面にしない）
        self.assertEqual([d["summary"] for d in cards[SMEARGLE]["jp_en_differences"]], ["ワザ スケッチ（Sketch）でコピーしたワザの条件"])
        self.assertEqual(read_extract()["source"]["commit"], "73a169063463bbf7bcaa3137d70cbf9721d11534")  # 写しの元は v0.97 のまま

    def test_adoption_records_and_research_links(self):
        data = json.loads((ROOT / "kyuura_engine" / "data" / "card_sources.json").read_text(encoding="utf-8"))["cards"]
        for card, parts in ((SMEARGLE, ("attack/0",)), (MISDREAVUS, ("attack/0", "attack/1"))):
            with self.subTest(card=card):
                item = data[card]
                self.assertEqual((item["basis"], item["status"], item["kyuura_commit"], item["recorded_on"], item["external_checks"], item["issues"],
                                  item["kyuura_records"], item["play_text"]),
                                 ("kyuura_data", "adopted", "73a169063463bbf7bcaa3137d70cbf9721d11534", "2026-10-25", [], [], [],
                                  {part: "kyuura_printed_text" for part in parts}))
        self.assertIn("card_differences.json#neo2-052", data[SMEARGLE]["notes"])
        self.assertIn("2000.02.14 版の裁定として新しく採らない", data[SMEARGLE]["notes"])
        links = json.loads((ROOT / "kyuura_engine" / "data" / "research_links.json").read_text(encoding="utf-8"))
        self.assertEqual([k for k in links["latest_descriptions"]["adopted_printed_text"] if k.split("/")[0] in V0100],
                         ["neo2-052/attack/0", "neo3-035/attack/0", "neo3-035/attack/1"])
        for code, label in ((SK1, "SK1"), (SK2, "SK2"), (PSG1, "PSG1")):
            entry = links["stop_codes"][code]
            self.assertEqual((entry["kyuura_issue"], entry["kyuura_disposition"], [r["ruling_id"] for r in entry["engine_rulings"]]),
                             (None, "not_in_kyuura", [label]))
        self.assertNotIn(MISSING, links["stop_codes"])  # エンジンの持つ情報の不足（研究上の未解決ではない）
        self.assertEqual([c for c in links["kyuura_cases_without_engine_ruling"]["cases"] if c["card_id"] in V0100], [])

    def test_abbreviations_are_separated(self):
        """v0.99 の［PERFORM］の問いの略号は PFM1（v0.100 で PF1 から改めた）。v0.47 の PF1 の問い・どちらの長い停止コードも変えない。新しい略号は重ならない。"""
        links = json.loads((ROOT / "kyuura_engine" / "data" / "research_links.json").read_text(encoding="utf-8"))
        labels = {}
        for code, entry in links["stop_codes"].items():
            for ruling in entry["engine_rulings"]:
                labels.setdefault(ruling["ruling_id"], set()).add(code)
        self.assertEqual(labels["PF1"], {"UNRESOLVED_PLAY_AS_POKEMON_SETUP"})
        self.assertEqual(labels["PFM1"], {"UNRESOLVED_PERFORM_DAMAGE_PLACES"})
        for label in ("SK1", "SK2", "PSG1"):
            self.assertEqual(len(labels[label]), 1)
        self.assertEqual((QUESTIONS["sketch_presence"].rulings, QUESTIONS["sketch_copied_attack"].rulings, QUESTIONS["perish_song_received_attack"].rulings),
                         (("SK1",), ("SK2",), ("PSG1",)))
        self.assertEqual(links["counts"], {"engine_unresolved_rulings": 232, "engine_stop_codes": 231, "kyuura_issues": 72})
        v099 = (ROOT / "docs" / "unown-perform-help-history-v0.99.md").read_text(encoding="utf-8")
        self.assertIn("PF1 は v0.47 の `UNRESOLVED_PLAY_AS_POKEMON_SETUP`", v099)  # 訂正の注記
        self.assertIn("PFM1 `UNRESOLVED_PERFORM_DAMAGE_PLACES`", v099)



# ---------------------------------------------------------------- 3 章: プレイヤーの番ごとの記録（共通の処理）

DCE = H.DOUBLE_COLORLESS_ENERGY
PARAS, VULPIX, DODUO, GYARADOS, SLOWPOKE, CLEFAIRY, PIDGEOTTO = H.PARAS, H.VULPIX, H.DODUO, H.GYARADOS, H.SLOWPOKE, H.CLEFAIRY, H.PIDGEOTTO
HORSEA_NEO = "neo1-023"  # タッツー（ひれがえし）


class TurnHistoryTest(unittest.TestCase):
    def test_records_only_when_a_reader_is_in_the_game(self):
        """「スケッチ」のある対戦だけがプレイヤーの記録を持つ（番の始めの場のカード・使ったワザ）。ムウマだけの対戦は場のポケモンの履歴だけ、どちらもない対戦は v0.99 と同じ。"""
        state = opponent_turn(mon(SMEARGLE, (W, W)), mon(H.RATTATA, (G,)))
        rattata = pid(state, H.RATTATA, 1)
        self.assertTrue(turn_history_needed(state))
        self.assertEqual([type(r).__name__ for r in state.turn_history], ["TurnField", "TurnAttack", "TurnField"])
        self.assertEqual(turn_attack(state, TURN - 1), TurnAttack(TURN - 1, 1, rattata, pokemon(state, H.RATTATA, 1).card, (H.RATTATA, 0)))
        field = turn_field(state, TURN - 1, 0)
        self.assertEqual((field.cards, field.face_down), (tuple(p.card for p in state.players[0].in_play()), 0))  # 番の始めの自分の場
        self.assertEqual(turn_field(state, TURN, 1).player, 1)  # 今の番（自分の番）には、番でない相手の場を記録する
        only_perish = opponent_turn(mon(MISDREAVUS, (PS,)), mon(H.RATTATA, (G,)))
        self.assertEqual((turn_history_needed(only_perish), history_needed(only_perish), only_perish.turn_history), (False, True, ()))
        self.assertTrue(pokemon(only_perish, MISDREAVUS).history)
        neither = opponent_turn(mon(H.RATTATA, (G,)), mon(H.RATTATA, (G,)))
        self.assertEqual((turn_history_needed(neither), history_needed(neither), neither.turn_history), (False, False, ()))
        self.assertIsInstance(state_to_dict(neither, 25), dict)  # 記録がなければ形式 25 でも書ける
        audited(self, state)

    def test_records_keep_two_turns(self):
        """番の最初に 2 つ前の番より古い記録を消す（前の相手の番・前の自分の番だけを読む）。"""
        state = opponent_turn(mon(SMEARGLE, (W, W)), mon(H.RATTATA, (G,)))
        later = settle(end(settle(end(state))))
        self.assertEqual(later.turn_number, TURN + 2)
        self.assertEqual(sorted({r.turn for r in later.turn_history}), [TURN, TURN + 1, TURN + 2])
        self.assertIsNone(turn_attack(later, TURN - 1))
        audited(self, later)

    def test_serialization_observation_and_invariants(self):
        """形式 26 は最上位の ``turn_history`` を書く。形式 25 以前は記録があると書き出さない。観測はどの見る人にも同じ記録（表の情報）。"""
        from kyuura_engine.engine import _turn_history_problems

        state = opponent_turn(mon(SMEARGLE, (W, W)), mon(H.RATTATA, (G,)))
        latest = state_to_dict(state, 26)
        self.assertIn(26, FORMAT_VERSIONS)
        self.assertEqual([r["kind"] for r in latest["turn_history"]], ["turn_field", "turn_attack", "turn_field"])
        self.assertEqual(latest["turn_history"][1]["declared"], [H.RATTATA, 0])
        for version in (20, 25):
            with self.subTest(version=version), self.assertRaises(ValueError):
                state_to_dict(state, version)
        for viewer in (0, 1, None):
            self.assertEqual(observe(state, viewer)["turn_history"], latest["turn_history"])
        broken = state.clone()
        broken.turn_history = tuple(dataclasses.replace(r, player=0) if isinstance(r, TurnAttack) else r for r in broken.turn_history)
        self.assertTrue(any("プレイヤー" in p for p in _turn_history_problems(broken)))
        self.assertEqual(_turn_history_problems(state), [])
        audited(self, state)

    def test_attack_record_survives_the_attacker_leaving(self):
        """相手のロコン（どく）が「あやしいひかり」を使い、番の終わりのどくできぜつ（パラスに交代）: 使った事実は残り、スケッチは今の相手の場から探さない。"""
        state = opponent_turn(mon(SMEARGLE, (W, W)), mon(VULPIX, (F, F), damage=30, poison=10), opponent_bench=(PARAS,), coins=(TL,))
        vulpix_record = turn_attack(state, TURN - 1)
        self.assertEqual(vulpix_record.declared, (VULPIX, 0))
        self.assertIsNone(state.find_pokemon(vulpix_record.pokemon_id))  # ワザを使ったポケモンは場にいない
        self.assertEqual(state.cards[state.players[1].active.card].card_id, PARAS)
        done = attack(state, 0, HD)
        copy_event = new_events(state, done, "copy_attack")[0]
        self.assertEqual((copy_event["copied"], copy_event["used_turn"], copy_event["used_by"]), (f"{VULPIX}#0", TURN - 1, vulpix_record.pokemon_id))
        # 使う側（ドーブル。無色）のワザとして計算する: パラスの弱点「炎」は当たらない（10。ロコンが使えば 20）。コインは新しく投げる
        self.assertEqual(damages(state, done), [(card(state, PARAS, 1), 10)])
        self.assertEqual([e["result"] for e in new_events(state, done, "coin_flip")], ["heads"])
        audited(self, done)


# ---------------------------------------------------------------- 4 章: ドーブル「スケッチ」


class SketchTest(unittest.TestCase):
    def test_uses_the_attack_with_new_coins(self):
        """ドードーの「みだれづき」（コイン 2 枚の「おもて」×10）: 相手の前の番の結果（0）を写さず、新しく投げる（20）。使った記録の処理したワザはまねたワザ。"""
        state = opponent_turn(mon(SMEARGLE, (W, W)), mon(DODUO, (G,)), coins=(TL, TL))
        done = attack(state, 0, HD, HD)
        self.assertEqual(kinds(state, done)[:4], ["attack", "copy_attack", "coin_flip", "coin_flip"])
        self.assertEqual(damages(state, done), [(card(state, DODUO, 1), 20)])
        self.assertEqual(turn_attack(done, TURN), TurnAttack(TURN, 0, pid(state, SMEARGLE), pokemon(state, SMEARGLE).card, (SMEARGLE, 0), (DODUO, 0)))
        for other in (state.clone(), copy.deepcopy(state), pickle.loads(pickle.dumps(state))):
            self.assertEqual(snap(attack(other, 0, HD, HD)), snap(done))
        audited(self, done)

    def test_no_attack_last_turn_does_nothing(self):
        """前の相手の番に相手がワザを使っていなければ、処理の対象がないので何もしない（失敗ではない。番は終わる）。"""
        state = opponent_turn(mon(SMEARGLE, (W, W)), mon(H.RATTATA, (G,)), index=None)
        self.assertIsNone(turn_attack(state, TURN - 1))
        done = attack(state)
        self.assertEqual([(e["reason"], e["used_turn"]) for e in new_events(state, done, "sketch_none")], [("no_attack", TURN - 1)])
        self.assertEqual(new_events(state, done, "attack_failed", "damage"), [])
        self.assertEqual((done.turn_number, done.current_player), (TURN + 1, 1))
        audited(self, done)

    def test_energy_is_waived_but_sketch_needs_its_own(self):
        """ギャラドスの「りゅうのいかり」（水水水）を、無色の 2 個だけのドーブルが使う（50）。スケッチ自体の無色 2 個は要る。"""
        state = opponent_turn(mon(H.RATTATA), mon(GYARADOS, (W, W, W), evolved_from=H.MAGIKARP), bench=(mon(SMEARGLE, (W, W)),))
        self.assertIs(state.players[0].active, pokemon(state, SMEARGLE))  # コラッタはきぜつして、ベンチにいたドーブルを出した
        done = attack(state)
        self.assertEqual(damages(state, done), [(card(state, GYARADOS, 1), 50)])
        short = opponent_turn(mon(H.RATTATA), mon(GYARADOS, (W, W, W), evolved_from=H.MAGIKARP), bench=(mon(SMEARGLE, (W,)),))
        rejects(self, short, UseAttack(0, 0), "INSUFFICIENT_ENERGY", error=IllegalActionError)

    def test_other_conditions_are_not_waived(self):
        """ヤドンの「ぼーっとする」（このカードにダメージカウンターがのってない時には使えない）: ダメージのないドーブルは条件をみたさず、説明が処理を書かないので HC9。のっていれば使える。"""
        state = opponent_turn(mon(SMEARGLE, (W, W)), mon(SLOWPOKE, (PS,), damage=20), coins=(TL,))
        self.assertEqual(turn_attack(state, TURN - 1).declared, (SLOWPOKE, 0))
        rejects(self, state, UseAttack(0, 0), HC9)
        damaged = opponent_turn(mon(SMEARGLE, (W, W), damage=20), mon(SLOWPOKE, (PS,), damage=20), coins=(TL,))
        done = attack(damaged, 0, HD)
        self.assertLess(pokemon(done, SMEARGLE).damage, 20)  # ドーブルからとりのぞく（「このカード」は使う側）

    def test_copied_attacks_are_sk2_and_copy_attacks_stay_hc9(self):
        """相手のピッピが「ゆびをふる」で自分のコラッタの「かみつく」を使った: 「そのワザ」が宣言したワザか処理したワザかで変わるので SK2。何もしなかった「オウムがえし」は、
        まねるワザをまねるので HC9（既存の未解決のまま）。"""
        clefairy = opponent_turn(mon(H.RATTATA), mon(CLEFAIRY, (W, W, W)), bench=(mon(SMEARGLE, (W, W)),), index=1)
        self.assertEqual(turn_attack(clefairy, TURN - 1).processed, (H.RATTATA, 0))
        moved = apply_kernel(clefairy, Retreat(0, (), pokemon(clefairy, SMEARGLE).card))
        rejects(self, moved, UseAttack(0, 0), SK2)
        mirror = opponent_turn(mon(SMEARGLE, (W, W)), mon(PIDGEOTTO, (W, W, W), evolved_from=H.PIDGEY), index=1)
        record = turn_attack(mirror, TURN - 1)
        self.assertEqual((record.declared, record.processed), ((PIDGEOTTO, 1), None))
        rejects(self, mirror, UseAttack(0, 0), HC9)

    def test_failed_original_attack_still_counts(self):
        """相手のこんらんのコラッタが「うら」で自分に 20（ワザは失敗）: 宣言のときに使ったことになる（v0.44・v0.62 の時点のまま）ので、ドーブルは「かみつく」を使う。"""
        state = opponent_turn(mon(SMEARGLE, (W, W)), mon(H.RATTATA, (G,), confusion=True), coins=(TL,))
        self.assertEqual(turn_attack(state, TURN - 1).declared, (H.RATTATA, 0))
        self.assertEqual(pokemon(state, SMEARGLE).damage, 0)
        done = attack(state)
        self.assertEqual(damages(state, done), [(card(state, H.RATTATA, 1), 20)])

    def test_this_card_is_the_user(self):
        """タッツーの「ひれがえし」を使うと、「このカード」はドーブル（前の相手の番にドーブルが受けたダメージで +10）。"""
        state = opponent_turn(mon(SMEARGLE, (W, W)), mon(HORSEA_NEO, (W, W)))
        self.assertEqual(pokemon(state, SMEARGLE).damage, 20)
        self.assertEqual(damages(state, attack(state)), [(card(state, HORSEA_NEO, 1), 30)])

    def test_decision_in_the_copied_attack(self):
        """ピジョンの「ふきとばし」（入れ替える控えは相手が選ぶ）を使う: 相手の決定。複製・deepcopy・pickle から同じ答えで同じ結果。不正な答えは状態・乱数・ログを変えない。
        決定のあとで、コイン・使った記録・切りかえを重ねない。"""
        state = opponent_turn(mon(SMEARGLE, (W, W)), mon(PIDGEOTTO, (W, W), evolved_from=H.PIDGEY), opponent_bench=(H.RATTATA, PARAS))
        # 前の番の相手のふきとばしで、ドーブルはベンチにもどり、自分の決定でコラッタを出した（settle）。コラッタからにげてドーブルにもどる
        moved = apply_kernel(state, Retreat(0, (), pokemon(state, SMEARGLE).card))
        waiting = attack(moved)
        d = waiting.decision
        self.assertEqual((d.kind, d.player, d.context_value("copied")), ("forced_switch", 1, (PIDGEOTTO, 0)))
        audited(self, waiting)
        rejects(self, waiting, ResolveDecision(0, d.id, (d.options[0],)), "NOT_YOUR_DECISION", error=IllegalActionError)
        rejects(self, waiting, ResolveDecision(1, d.id, (pid(waiting, PIDGEOTTO, 1),)), "INVALID_CHOICE", error=IllegalActionError)
        expected = apply_kernel(waiting, ResolveDecision(1, d.id, (d.options[-1],)))
        for other in (waiting.clone(), copy.deepcopy(waiting), pickle.loads(pickle.dumps(waiting))):
            self.assertEqual(snap(apply_kernel(other, ResolveDecision(1, d.id, (d.options[-1],)))), snap(expected))
        self.assertEqual(kinds(waiting, expected).count("copy_attack"), 0)
        self.assertEqual(sum(isinstance(r, TurnAttack) and r.turn == TURN for r in expected.turn_history), 1)
        audited(self, expected)


def play_to_active(state, card_uid, energy_uid=None):
    """手札のカード ``card_uid`` をベンチに出し、にげるの 0 個のバトル場のコラッタと入れ替え、手札の ``energy_uid`` をつける（今の番に場に出たポケモン）。"""
    state = apply_kernel(state, PlayBasicToBench(0, card_uid))
    state = apply_kernel(state, Retreat(0, (), card_uid))
    if energy_uid is not None:
        state = apply_kernel(state, AttachEnergy(0, energy_uid, card_uid))
    return state


class SketchPresenceTest(unittest.TestCase):
    """「前の相手の番、このカードが場に出ていなければ、このワザは失敗する」（ワザの効果。宣言の拒否にしない）と、読み方で失敗するかが変わる境界（SK1）。"""

    def test_played_this_turn_fails(self):
        """前の相手の番に手札にあり、今の番に出したドーブル: 失敗（ログ attack_failed の not_in_play。使ったことになり、番は終わる）。前の相手の番にワザは使われていた。"""
        state = opponent_turn(mon(H.RATTATA), mon(H.RATTATA, (G,)), hand=(SMEARGLE, DCE))
        ready = play_to_active(state, uid(state, SMEARGLE), uid(state, DCE))
        self.assertEqual(pokemon(ready, SMEARGLE).current_form_turn, TURN)
        done = attack(ready)
        self.assertEqual([e["reason"] for e in new_events(ready, done, "attack_failed")], ["not_in_play"])
        self.assertEqual(new_events(ready, done, "copy_attack", "damage"), [])
        self.assertEqual((done.turn_number, done.current_player), (TURN + 1, 1))
        self.assertEqual(turn_attack(done, TURN).declared, (SMEARGLE, 0))  # 失敗しても使ったことになる
        audited(self, done)

    def test_on_the_bench_last_turn_is_in_play(self):
        """前の相手の番の始めからベンチにいたドーブルを、今の番にバトル場に出す: 場に出ていた（場所は問わない）。"""
        state = opponent_turn(mon(H.RATTATA), mon(DODUO, (G,)), bench=(mon(SMEARGLE, (W, W)),), coins=(TL, TL))
        moved = apply_kernel(state, Retreat(0, (), pokemon(state, SMEARGLE).card))
        self.assertEqual(kinds(moved, attack(moved, 0, HD, TL))[:2], ["attack", "copy_attack"])

    def test_entered_during_the_last_opponent_turn_is_sk1(self):
        """前の相手の番に、相手のポケモンの笛で自分のトラッシュからベンチに出されたドーブル: その番の途中から場にいた（記録 ``TurnField`` に加わる）ので、失敗するかが決まらない（SK1）。
        前の相手の番の始めからベンチにいたドーブルは止めない。"""
        me = {"active": mon(H.RATTATA), "bench": [mon(H.RATTATA)], "hand": [DCE], "deck": [W] * 10, "discard": [SMEARGLE], "prizes": 6}
        them = {"active": mon(H.RATTATA, (G,)), "bench": [mon(H.RATTATA)], "hand": [H.POKEMON_FLUTE], "deck": [W] * 10, "discard": [], "prizes": 6}
        state = settle(end(H.build_test_state([me, them], turn_number=TURN - 2, current_player=0)))
        flute = apply_kernel(state, PlayTrainer(1, uid(state, H.POKEMON_FLUTE, 1)))
        smeargle_card = uid(state, SMEARGLE, 0, "discard")
        fluted = apply_kernel(flute, ResolveDecision(1, flute.decision.id, (smeargle_card,)))
        self.assertIn(smeargle_card, turn_field(fluted, TURN - 1, 0).cards)
        after = settle(attack(fluted))
        self.assertEqual(pokemon(after, SMEARGLE).current_form_turn, TURN - 1)
        ready = apply_kernel(apply_kernel(after, Retreat(0, (), smeargle_card)), AttachEnergy(0, uid(after, DCE), smeargle_card))
        rejects(self, ready, UseAttack(0, 0), SK1)

    def test_returned_and_played_again_is_sk1(self):
        """前の相手の番にピジョットの「ハリケーン」で手札にもどされ、今の番に出し直したドーブル（同じカード）: 前の相手の番に場にいたカードだが、場に出た番は新しくなる。
        どちらの読み方かで失敗するかが変わるので SK1。手札にあった別のドーブルを出したなら失敗する。"""
        turn = TURN + 2  # 2 進化のピジョット（相手は 4 番に 1 進化・6 番に 2 進化）
        pidgeot = mon(H.PIDGEOT, (W, W, W), evolved_from=[H.PIDGEY, H.PIDGEOTTO], evolved_turn=turn - 3)
        start = board(mon(SMEARGLE, (W, W)), opponent=pidgeot, hand=(SMEARGLE, DCE), current=0, turn=turn - 2)
        other_smeargle = uid(start, SMEARGLE)
        returned = start.players[0].active.card
        state = settle(attack(settle(end(start)), 1))
        self.assertEqual((state.turn_number, state.current_player), (turn, 0))
        self.assertIn(returned, state.players[0].hand)
        self.assertIn(returned, turn_field(state, turn - 1, 0).cards)
        rejects(self, play_to_active(state, returned, uid(state, DCE)), UseAttack(0, 0), SK1)
        fresh = play_to_active(state, other_smeargle, uid(state, DCE))
        done = attack(fresh)
        self.assertEqual([e["reason"] for e in new_events(fresh, done, "attack_failed")], ["not_in_play"])

    def test_first_turn_of_the_game_is_sk1(self):
        """先攻の最初の番（前の相手の番がない。対戦準備は相手の番ではない）: 失敗するか・何もしないかが決まらない（SK1）。"""
        state = board(mon(SMEARGLE, (DCE,)), opponent=mon(H.RATTATA), current=0, turn=1)
        rejects(self, state, UseAttack(0, 0), SK1)

    def test_face_down_card_last_turn_is_sk1_without_reading_it(self):
        """前の相手の番に、自分の場にうらのカード（マチスの秘策）があった: 正体を記録しないので、今の番に出したドーブルがそのカードでないと言えず SK1（うらのカードの正体を
        読まない。正体がドーブルでなくても同じ答え）。うらのカードがなければ失敗する。"""
        from tests.test_secret_plan_v0_67 import place

        for hidden in (H.RATTATA, H.DODUO):
            with self.subTest(hidden=hidden):
                start = board(mon(H.RATTATA), opponent=mon(H.RATTATA, (G,)), hand=(H.LT_SURGES_SECRET_PLAN, hidden, SMEARGLE, DCE), current=0, turn=TURN - 2)
                placed = place(start, hidden)
                state = settle(attack(settle(end(placed))))
                self.assertEqual(turn_field(state, TURN - 1, 0).face_down, 1)
                self.assertNotIn(placed.face_down_cards[0], turn_field(state, TURN - 1, 0).cards)
                rejects(self, play_to_active(state, uid(state, SMEARGLE), uid(state, DCE)), UseAttack(0, 0), SK1)

    def test_missing_records_are_not_read_as_no_attack(self):
        """記録していない前の番（v0.99 までの状態の写し: ``turn_history`` がない）: 「使わなかった」「場にいなかった」と読まず、エンジンの情報の不足（研究上の未解決ではない）。"""
        state = opponent_turn(mon(SMEARGLE, (W, W)), mon(H.RATTATA, (G,)), hand=(SMEARGLE, DCE))
        old = state.clone()
        old.turn_history = ()
        rejects(self, old, UseAttack(0, 0), MISSING)
        legacy = pickle.loads(pickle.dumps(state))
        del legacy.__dict__["turn_history"]  # 項目のない写しは既定値（空）
        self.assertEqual(legacy.turn_history, ())
        rejects(self, legacy, UseAttack(0, 0), MISSING)
        self.assertEqual(kinds(state, attack(state))[:2], ["attack", "copy_attack"])  # 記録があれば止めない


# ---------------------------------------------------------------- 5 章・6 章: ムウマ「やみのひとみ」「ほろびのうた」と、ワザの効果による直接の「きぜつ」

MISDREAVUS_FULL = mon(MISDREAVUS, (PS, PS, PS))


def slept(target, *, me=None, check_coins=(TL, TL), **kw):
    """``TURN - 2`` 番に自分のムウマが「やみのひとみ」を使い（相手の対戦ポケモンはねむり）、番の終わりのポケモンチェックのねむりのコイン（``check_coins`` の 1 つ目）、
    ``TURN - 1`` 番の相手は番を終え（2 つ目）、``TURN`` 番（自分の番）になった盤面。"""
    state = board(me or MISDREAVUS_FULL, opponent=target, current=0, turn=TURN - 2, **kw)
    state = attack(state, 0, check_coins[0])
    state = settle(end(state, check_coins[1]))
    assert (state.turn_number, state.current_player, state.decision) == (TURN, 0, None)
    return state


def sing(state, *coins):
    return attack(state, 1, *coins)


class NightEyesTest(unittest.TestCase):
    def test_puts_to_sleep_without_damage(self):
        """「やみのひとみ」はダメージの要素のない既存のねむり（v0.3b の ``PutToSleep``）。受けた記録の受けた要素は sleep（ダメージ 0 の要素を作らない）。"""
        state = board(MISDREAVUS_FULL, opponent=mon(H.RATTATA, (G,)), current=0, turn=TURN - 2)
        done = attack(state, 0, TL)
        self.assertEqual(new_events(state, done, "damage"), [])
        record = pokemon(done, H.RATTATA, 1).history[-1]
        self.assertEqual((record.processed, record.reached, record.damage), ((MISDREAVUS, 0), ("sleep",), 0))
        self.assertTrue(pokemon(done, H.RATTATA, 1).conditions.asleep)


class PerishSongTest(unittest.TestCase):
    def test_knocks_out_without_damage(self):
        """ねむりで、前の自分の番に「やみのひとみ」を受けていた相手は「きぜつ」する: ダメージ・ダメージカウンターをのせない。きぜつの処理・サイド・バトル場に出す決定は既存の処理。"""
        state = slept(mon(H.RATTATA, (G,)), opponent_bench=(PARAS,))
        target = pokemon(state, H.RATTATA, 1)
        done = sing(state)
        condition, ko = new_events(state, done, "knock_out_condition")[0], new_events(state, done, "effect_knock_out")[0]
        self.assertEqual((condition["asleep"], condition["received"], condition["received_turn"]), (True, RECEIVED, TURN - 2))
        self.assertEqual((ko["target_pokemon_id"], ko["pokemon_id"], ko["effect"]), (target.pokemon_id, pid(state, MISDREAVUS), f"{MISDREAVUS}#1"))
        self.assertEqual(new_events(state, done, "damage"), [])
        knocked = new_events(state, done, "knock_out")
        self.assertEqual([(e["player"], e["pokemon"]) for e in knocked], [(1, target.card)])
        self.assertIsNone(done.find_pokemon(target.pokemon_id))
        self.assertIn(target.card, done.players[1].discard)
        self.assertEqual((done.decision.kind, done.decision.player), ("take_prize", 0))
        for other in (state.clone(), copy.deepcopy(state), pickle.loads(pickle.dumps(state))):
            self.assertEqual(snap(sing(other)), snap(done))
        audited(self, done)
        after = settle(done)
        self.assertEqual((len(after.players[0].prizes), after.cards[after.players[1].active.card].card_id), (5, PARAS))

    def test_each_condition_alone_does_not_knock_out(self):
        """片方だけなら「きぜつ」しない（ワザは使え、何もしない）: 目を覚ました（今ねむりでない）・ほかのワザ（キノコのほうし）でねむった・2 つ前より前に受けた。"""
        woke = slept(mon(H.RATTATA, (G,)), check_coins=(TL, HD))
        self.assertFalse(pokemon(woke, H.RATTATA, 1).conditions.asleep)
        done = sing(woke)
        self.assertEqual([(e["asleep"], e["received"]) for e in new_events(woke, done, "knock_out_condition")], [(False, None)])
        self.assertEqual(new_events(woke, done, "effect_knock_out", "knock_out"), [])
        paras = board(mon(PARAS, (G, G, PS)), bench=(MISDREAVUS_FULL,), opponent=mon(H.RATTATA, (G,)), current=0, turn=TURN - 2)
        spore = settle(end(attack(paras, 1, TL), TL))
        moved = apply_kernel(spore, Retreat(0, (pokemon(spore, PARAS).energy[2],), pokemon(spore, MISDREAVUS).card))
        self.assertTrue(pokemon(moved, H.RATTATA, 1).conditions.asleep)
        sung = sing(moved)
        self.assertEqual([(e["asleep"], e["received"]) for e in new_events(moved, sung, "knock_out_condition")], [(True, NOT_RECEIVED)])
        self.assertEqual(new_events(moved, sung, "knock_out"), [])
        older = board(MISDREAVUS_FULL, opponent=mon(H.RATTATA, (G,)), current=0, turn=TURN - 4)
        older = settle(end(settle(end(settle(end(attack(older, 0, TL), TL)), TL)), TL))
        self.assertEqual((older.turn_number, pokemon(older, H.RATTATA, 1).conditions.asleep), (TURN, True))
        self.assertEqual([e["received"] for e in new_events(older, sing(older), "knock_out_condition")], [NOT_RECEIVED])

    def test_another_misdreavus_is_the_same_named_attack(self):
        """前の自分の番にやみのひとみを使ったのが別のムウマでも、受けたワザの名前で照らす（「同じムウマから」の条件を置かない）。"""
        state = slept(mon(H.RATTATA, (G,)), me=mon(MISDREAVUS, (PS, PS)), bench=(MISDREAVUS_FULL,))
        first = state.players[0].active
        second = next(p for p in state.players[0].bench if state.cards[p.card].card_id == MISDREAVUS)
        moved = apply_kernel(state, Retreat(0, (first.energy[0],), second.card))
        done = sing(moved)
        self.assertEqual([e["pokemon_id"] for e in new_events(moved, done, "effect_knock_out")], [second.pokemon_id])

    def test_effect_guard_now_prevents_it(self):
        """相手への効果なので、効果だけを無効にする効果（前の相手の番につけたエフェクトガード）があれば「きぜつ」しない（ログ effect_prevented）。"""
        state = board(MISDREAVUS_FULL, opponent=mon(H.RATTATA, (G,)), opponent_hand=(EFFECT_GUARD,), current=0, turn=TURN - 2)
        state = attack(state, 0, TL)
        used = apply_kernel(state, PlayTrainer(1, uid(state, EFFECT_GUARD, 1)))
        if used.decision is not None:
            used = apply_kernel(used, ResolveDecision(1, used.decision.id, (pid(used, H.RATTATA, 1),)))
        guarded = settle(end(used, TL))
        self.assertTrue(pokemon(guarded, H.RATTATA, 1).trainers)
        done = sing(guarded)
        self.assertEqual([e["element"] for e in new_events(guarded, done, "effect_prevented")], [E.KNOCK_OUT_ELEMENT])
        self.assertEqual(new_events(guarded, done, "effect_knock_out", "knock_out"), [])

    def test_damage_only_protection_does_not_prevent_it(self):
        """ダメージだけを変える効果（ディフェンダー）では防がれない（効果。ダメージの計算はしない）。"""
        state = slept(mon(H.RATTATA, (G,), trainers=[(H.DEFENDER, TURN)]))
        done = sing(state)
        self.assertEqual(len(new_events(state, done, "effect_knock_out")), 1)

    def test_effect_only_voided_night_eyes_is_psg1(self):
        """前の自分の番のやみのひとみを、エフェクトガードで受けなかった（効果の要素だけ。もとからねむり）: 受けていたことになるかが決まらず、今ねむりなら PSG1。目を覚ましていれば
        「きぜつ」しないことは決まるので止めない。"""
        start = board(MISDREAVUS_FULL, opponent=mon(H.RATTATA, (G,), sleep=True, trainers=[(EFFECT_GUARD, TURN - 2)]), current=0, turn=TURN - 2)
        voided = attack(start, 0, TL)
        record = pokemon(voided, H.RATTATA, 1).history[-1]
        self.assertEqual((record.reached, record.voided), ((), (("sleep", "effect_only"),)))
        asleep = settle(end(voided, TL))
        self.assertEqual(named_attack_received(asleep, pokemon(asleep, H.RATTATA, 1), TURN - 2, "やみのひとみ")[0], RECEIVED_UNDETERMINED)
        rejects(self, asleep, UseAttack(0, 1), PSG1)
        awake = settle(end(voided, HD))
        self.assertEqual(new_events(awake, sing(awake), "knock_out"), [])

    def test_copied_night_eyes_is_psg1(self):
        """前の自分の番に、ピッピの「ゆびをふる」で相手のムウマの「やみのひとみ」を使った（宣言したワザと処理したワザが違う）: 受けたワザがどちらかが決まらず PSG1。"""
        start = board(mon(CLEFAIRY, (PS, PS, PS)), bench=(MISDREAVUS_FULL,), opponent=mon(MISDREAVUS, (PS,)), current=0, turn=TURN - 2)
        choosing = attack(start, 1)
        night_eyes = choosing.decision.options[0]  # 相手のムウマの今持つワザの並びの最初（やみのひとみ）
        copied = apply_kernel(with_coin_results(choosing, TL), ResolveDecision(0, choosing.decision.id, (night_eyes,)))  # 答えのあとの番の終わりのねむりのコインは「うら」
        record = pokemon(copied, MISDREAVUS, 1).history[-1]
        self.assertEqual((record.declared, record.processed), ((CLEFAIRY, 1), (MISDREAVUS, 0)))
        asleep = settle(end(copied, TL))
        self.assertEqual((asleep.turn_number, asleep.current_player), (TURN, 0))
        moved = apply_kernel(asleep, Retreat(0, (pokemon(asleep, CLEFAIRY).energy[0],), pokemon(asleep, MISDREAVUS).card))
        self.assertTrue(pokemon(moved, MISDREAVUS, 1).conditions.asleep)
        rejects(self, moved, UseAttack(0, 1), PSG1)

    def test_metronome_reads_the_user_and_the_current_target(self):
        """ピッピの「ゆびをふる」で相手のムウマの「ほろびのうた」を使う: 使うプレイヤーの前の自分の番に、今の相手（そのムウマ）がやみのひとみを受けていたか（印刷したムウマの持ち主の
        履歴にしない）。"""
        start = board(MISDREAVUS_FULL, bench=(mon(CLEFAIRY, (PS, PS, PS)),), opponent=mon(MISDREAVUS, (PS, PS, PS)), current=0, turn=TURN - 2)
        state = settle(end(attack(start, 0, TL), TL))
        moved = apply_kernel(state, Retreat(0, (pokemon(state, MISDREAVUS).energy[0],), pokemon(state, CLEFAIRY).card))
        choosing = attack(moved, 1)
        perish = choosing.decision.options[1]  # 相手のムウマの今持つワザの並びの 2 つ目（ほろびのうた）
        done = apply_kernel(choosing, ResolveDecision(0, choosing.decision.id, (perish,)))
        ko = new_events(choosing, done, "effect_knock_out")
        self.assertEqual([(e["pokemon_id"], e["target_pokemon_id"], e["effect"]) for e in ko],
                         [(pid(moved, CLEFAIRY), pid(moved, MISDREAVUS, 1), f"{MISDREAVUS}#1")])

    def test_guts_final_beam_and_rebirth_are_not_offered(self):
        """ダメージによらない「きぜつ」: サカキのカイリキーの［こんじょう］（「ダメージで」）は使えない（v0.99 までの原因の写しの不足による内部エラーにならない）。わるいギャラドスの
        ［ファイナルビーム］・R団のファイヤーの「ふしちょう」は、ねむりのまま「きぜつ」するので使えない（既存の確かめ）。カイリキーの［はんげき］（ダメージを受けたとき）もはたらかない。"""
        cases = {
            "こんじょう": mon(H.GIOVANNIS_MACHAMP, (F, F, F, F), evolved_from=[H.GIOVANNIS_MACHOP, H.GIOVANNIS_MACHOKE], evolved_turn=TURN - 1),
            "ファイナルビーム": mon(H.DARK_GYARADOS, (W, W, W), evolved_from=H.MAGIKARP),
            "ふしちょう": mon(H.ROCKETS_MOLTRES, (F, F, F)),
            "はんげき": mon(H.MACHAMP, (F, F, F, F), evolved_from=[H.MACHOP, H.MACHOKE], evolved_turn=TURN - 1),
        }
        for label, target in cases.items():
            with self.subTest(label=label):
                state = self._slept_late(target)
                done = sing(state)
                self.assertEqual(len(new_events(state, done, "effect_knock_out")), 1)
                self.assertEqual(new_events(state, done, "damage", "counterattack_damage", "power_damage"), [])
                self.assertEqual((done.decision.kind, done.decision.player), ("take_prize", 0))
                audited(self, done)
                after = settle(done)
                self.assertEqual(after.phase.value, "main")

    def _slept_late(self, target):
        # 2 進化の相手（4 番に 1 進化・6 番に 2 進化）のために、7 番にやみのひとみを使い、9 番を「今の番」にした盤面（slept と同じ流れ）
        state = board(MISDREAVUS_FULL, opponent=target, current=0, turn=TURN)
        state = attack(state, 0, TL)
        state = settle(end(state, TL))
        assert (state.turn_number, state.current_player) == (TURN + 2, 0)
        return state

    def test_recycle_energy_returns_and_last_prize_wins(self):
        """きぜつの処理は既存のまま: ついていたリサイクルエネルギーは持ち主の手札にもどる。最後のサイドを取れば勝ち、相手の場にポケモンがいなくなれば勝ち。"""
        state = slept(mon(H.RATTATA, (H.RECYCLE_ENERGY,)), opponent_bench=(PARAS,))
        recycle = pokemon(state, H.RATTATA, 1).energy[0]
        done = sing(state)
        self.assertIn(recycle, done.players[1].hand)
        last_prize = slept(mon(H.RATTATA, (G,)), prizes=1, opponent_bench=(PARAS,))
        won = settle(sing(last_prize))
        self.assertEqual((won.result.outcome, won.result.winner), ("win", 0))
        alone = slept(mon(H.RATTATA, (G,)), opponent_bench=())
        won = settle(sing(alone))
        self.assertEqual(won.result.winner, 0)


class ReceivedRecordMeaningTest(unittest.TestCase):
    """「やみのひとみを受けていた」を、v0.62 の受けた記録の意味で読む（使った記録・今の特殊状態からは決めない）。"""

    def test_already_asleep_target_received_it(self):
        """もとからねむりの相手がやみのひとみを受けた（効果の要素は届いた）: 受けていた。ほろびのうたで「きぜつ」する。"""
        state = slept(mon(H.RATTATA, (G,), sleep=True))
        self.assertEqual(named_attack_received(state, pokemon(state, H.RATTATA, 1), TURN - 2, "やみのひとみ")[0], RECEIVED)
        self.assertEqual(len(new_events(state, sing(state), "effect_knock_out")), 1)

    def test_immune_target_received_it_but_is_not_asleep(self):
        """カビゴンの［めんえき］でねむりにならなかった: 効果の要素は受けた（v0.62 の記録の意味）。今ねむりではないので「きぜつ」しない（ねむりを受けた証拠に読み替えない）。"""
        state = slept(mon(H.SNORLAX, (G, G, G, G)))
        snorlax = pokemon(state, H.SNORLAX, 1)
        self.assertEqual((snorlax.history[-1].reached, snorlax.history[-1].voided), ((), (("sleep", "immune"),)))
        self.assertEqual(named_attack_received(state, snorlax, TURN - 2, "やみのひとみ")[0], RECEIVED)
        self.assertFalse(snorlax.conditions.asleep)
        self.assertEqual(new_events(state, sing(state), "effect_knock_out"), [])

    def test_barrier_means_not_received(self):
        """ミュウツーの「バリアー」（ワザをうけない）で受けなかったやみのひとみは、受けていない（v0.62 の「どの要素も受けなかった」）。ねむりの相手でも「きぜつ」しない
        （ねむりは手で置いた。バリアーのあとにねむりになる流れは今の写しで作りにくい）。"""
        start = board(MISDREAVUS_FULL, opponent=mon(H.MEWTWO, (PS, PS, PS)), current=1, turn=TURN - 3)
        barrier = settle(attack(start, 1))
        voided = attack(barrier, 0, TL)
        record = pokemon(voided, H.MEWTWO, 1).history[-1]
        self.assertEqual((record.reached, record.voided), ((), (("sleep", "attack_barrier"),)))
        state = settle(end(voided))
        self.assertEqual(named_attack_received(state, pokemon(state, H.MEWTWO, 1), TURN - 2, "やみのひとみ")[0], NOT_RECEIVED)
        asleep = state.clone()
        asleep.players[1].active.conditions = SpecialConditions(exclusive=ASLEEP)
        done = sing(asleep)
        self.assertEqual([(e["asleep"], e["received"]) for e in new_events(asleep, done, "knock_out_condition")], [(True, NOT_RECEIVED)])
        self.assertEqual(new_events(asleep, done, "effect_knock_out"), [])


class CopyInteractionTest(unittest.TestCase):
    def test_metronome_on_smeargle_leaves_no_unanswerable_decision(self):
        """相手のドーブルにピッピの「ゆびをふる」: 選べるワザはスケッチだけで、まねるワザをまねるので処理できない。答えのない決定を出さず、宣言の前に HC9 で止める（状態を変えない）。"""
        state = board(mon(CLEFAIRY, (W, W, W)), opponent=mon(SMEARGLE, (W, W)), current=0, turn=TURN)
        rejects(self, state, UseAttack(0, 1), HC9)

    def test_sketch_cannot_copy_the_sketch_of_a_copy(self):
        """相手のドーブルがスケッチで自分のワザを使った（宣言したワザ スケッチ・処理したワザ かみつく）: 自分のドーブルのスケッチは SK2。"""
        start = board(mon(H.RATTATA, (G,)), bench=(mon(SMEARGLE, (W, W)),), opponent=mon(SMEARGLE, (W, W)), current=0, turn=TURN - 2)
        state = settle(attack(settle(attack(start)), 0))  # 5 番に自分のコラッタが「かみつく」→ 6 番に相手のドーブルがスケッチで「かみつく」
        self.assertEqual(turn_attack(state, TURN - 1).processed, (H.RATTATA, 0))
        moved = apply_kernel(state, Retreat(0, (), pokemon(state, SMEARGLE).card))
        rejects(self, moved, UseAttack(0, 0), SK2)


class EffectKnockOutCauseTest(unittest.TestCase):
    """ワザの効果による「きぜつ」の原因（``Resolution.effect_ko``）を、決定の続きの情報で運び、もどす共通の処理（今の写しでは、ほろびのうたのあとにきぜつの判定の決定・ワザの途中の
    決定は起こらないので、運ぶ・もどす関数を直接確かめる）。"""

    def test_cause_round_trip(self):
        from kyuura_engine.resolution.kernel import (
            Resolution,
            effect_ko_entries,
            ko_cause,
            restore_effect_ko,
        )

        state = slept(mon(H.RATTATA, (G,)))
        res = Resolution(state.clone())
        res.effect_ko[5] = (0, 1)
        res.forced.add(5)
        self.assertEqual(effect_ko_entries(res), ((5, 0, 1),))
        self.assertEqual(ko_cause(res, 5), (0, 1, True))
        again = Resolution(state.clone())
        restore_effect_ko(again, effect_ko_entries(res))
        self.assertEqual((again.forced, again.effect_ko), ({5}, {5: (0, 1)}))
        self.assertIsNone(ko_cause(Resolution(state.clone()), 5))


class DocumentTest(unittest.TestCase):
    def test_document_lists_the_cards_codes_and_unhit_boundaries(self):
        text = DOC.read_text(encoding="utf-8")
        for needle in (*V0100, "スケッチ", "やみのひとみ", "ほろびのうた", SK1, SK2, PSG1, "SK1", "SK2", "PSG1", "PFM1", HC9, MISSING, "73a1690", "形式 26",
                       "対戦で一度も起こらなかったもの", "FOLLOW_TEXT", "MM2", "UQ-COPIED-ATTACK"):
            self.assertIn(needle, text)


class MidTurnStateTest(unittest.TestCase):
    def test_states_built_mid_turn_do_not_invent_records(self):
        """番の途中から作った状態（番の始めの記録がない。v0.99 までの写しと同じ）で、相手のポケモンが場に出ても、途中から番の始めの記録を作らない（内部エラーにもしない）。
        前の相手の番の記録がないので、スケッチはエンジンの情報の不足で止まる。"""
        me = {"active": mon(SMEARGLE, (W, W)), "bench": [], "hand": [H.POKEMON_FLUTE], "deck": [W] * 10, "discard": [], "prizes": 6}
        them = {"active": mon(H.RATTATA, (G,)), "bench": [], "hand": [], "deck": [W] * 10, "discard": [H.RATTATA], "prizes": 6}
        state = H.build_test_state([me, them], turn_number=TURN, current_player=0)
        flute = apply_kernel(state, PlayTrainer(0, uid(state, H.POKEMON_FLUTE)))
        fluted = apply_kernel(flute, ResolveDecision(0, flute.decision.id, (flute.decision.options[0],)))
        self.assertEqual(len(fluted.players[1].bench), 1)
        self.assertEqual(fluted.turn_history, ())
        rejects(self, fluted, UseAttack(0, 0), MISSING)
        audited(self, fluted)


class SketchSourceTest(unittest.TestCase):
    """スケッチが読むのは前の相手の番に相手が使ったワザの事実で、ドーブルが受けたか・今の相手の対戦ポケモンは問わない。"""

    def test_attack_that_did_not_reach_this_card(self):
        """相手のムウマの「やみのひとみ」（ダメージのないワザ）でねむったバトル場のコラッタを、ポケモンいれかえでベンチのドーブルと入れ替える: ドーブルは受けていない（受けた記録が
        ない）が、スケッチはやみのひとみを使い、相手をねむりにする（使う側のワザとして処理する）。"""
        state = opponent_turn(mon(H.RATTATA), mon(MISDREAVUS, (PS,)), bench=(mon(SMEARGLE, (W, W)),), hand=(H.SWITCH,), coins=(TL,))
        self.assertTrue(pokemon(state, H.RATTATA).conditions.asleep)
        played = apply_kernel(state, PlayTrainer(0, uid(state, H.SWITCH)))
        switched = apply_kernel(played, ResolveDecision(0, played.decision.id, (pid(played, SMEARGLE),)))
        self.assertIs(switched.players[0].active, pokemon(switched, SMEARGLE))
        self.assertEqual(pokemon(switched, SMEARGLE).history, ())  # ドーブルは前の相手の番にワザを受けていない
        done = attack(switched)
        self.assertEqual([e["copied"] for e in new_events(switched, done, "copy_attack")], [f"{MISDREAVUS}#0"])
        self.assertEqual([(e["pokemon_id"], e["condition"]) for e in new_events(switched, done, "special_condition")], [(pid(switched, MISDREAVUS, 1), "sleep")])
        audited(self, done)

    def test_attacker_moved_to_the_bench(self):
        """前の相手の番に「みだれづき」を使ったドードーを、今の番に突風でベンチにもどす: スケッチは今の相手の対戦ポケモン（パラス）のワザから選ばず、みだれづきを使う。"""
        state = opponent_turn(mon(SMEARGLE, (W, W)), mon(DODUO, (G,)), opponent_bench=(PARAS,), hand=(H.GUST,), coins=(TL, TL))
        played = apply_kernel(state, PlayTrainer(0, uid(state, H.GUST)))
        gusted = apply_kernel(played, ResolveDecision(0, played.decision.id, (pid(played, PARAS, 1),)))
        self.assertEqual(gusted.cards[gusted.players[1].active.card].card_id, PARAS)
        done = attack(gusted, 0, HD, HD)
        copy_event = new_events(gusted, done, "copy_attack")[0]
        self.assertEqual((copy_event["copied"], copy_event["used_by"]), (f"{DODUO}#0", pid(gusted, DODUO, 1)))
        self.assertEqual(damages(gusted, done), [(card(gusted, PARAS, 1), 20)])  # 無色のドーブルのワザ（パラスの弱点「炎」は当たらない）


class PerishSongTargetTest(unittest.TestCase):
    def test_a_different_target_did_not_receive_it(self):
        """前の自分の番にやみのひとみを受けたコラッタが、相手のポケモンいれかえでベンチにもどり、パラスが出た: 今の相手（パラス）は受けていない。ベンチのコラッタの記録を今の相手に
        移さない（ねむりもベンチにもどって消えた）。"""
        start = board(MISDREAVUS_FULL, opponent=mon(H.RATTATA, (G,)), opponent_bench=(PARAS,), opponent_hand=(H.SWITCH,), current=0, turn=TURN - 2)
        slept_state = attack(start, 0, TL)
        played = apply_kernel(slept_state, PlayTrainer(1, uid(slept_state, H.SWITCH, 1)))
        switched = apply_kernel(played, ResolveDecision(1, played.decision.id, (pid(played, PARAS, 1),)))
        state = settle(end(switched))
        self.assertEqual((state.turn_number, state.cards[state.players[1].active.card].card_id), (TURN, PARAS))
        self.assertEqual(named_attack_received(state, pokemon(state, H.RATTATA, 1), TURN - 2, "やみのひとみ")[0], RECEIVED)
        self.assertEqual(named_attack_received(state, pokemon(state, PARAS, 1), TURN - 2, "やみのひとみ")[0], NOT_RECEIVED)
        done = sing(state)
        self.assertEqual([(e["target_pokemon_id"], e["asleep"]) for e in new_events(state, done, "knock_out_condition")], [(pid(state, PARAS, 1), False)])
        self.assertEqual(new_events(state, done, "effect_knock_out"), [])

if __name__ == "__main__":
    unittest.main()

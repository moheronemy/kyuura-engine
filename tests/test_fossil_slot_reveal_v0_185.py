"""v0.185（docs/fossil-slot-reveal-v0.185.md。設計は docs/fossil-slot-reveal-identification-design.md）: 化石の発掘の山札の側と、スロットゲームの束全体の識別。

- F: 化石の発掘（ES1-035）で山札から選んだ「なにかの化石」の ``reveal_from_deck`` に、見せたカード自身の ``card_id``（``identify=True``）。トラッシュの側（``retrieve_trainer``）は変えない
- S: スロットゲーム（neo1-090）の束の出来事 ``reveal_deck_top`` に ``card_ids``（``cards`` と同じ長さ・同じ順。``card_ids[i]`` は ``cards[i]`` のカードの ID）。束を見せた時点で固定する
- 盤面は既存のテストの盤面の関数（構築盤面。new_game からの到達の実績には数えない）。進め方と 4 つの入口・閲覧用記録の確かめは v0.184 のテストの ``Run``・``Recorder`` を再利用する
- 共有する可視性の対照（パソコン通信・``reveal=False``・ポケモンギア・みずかき）は v0.184 のテストにある。ここでは本人だけの束の代表（マスターボール・新ポケモン図鑑HANDY808）だけを足す
"""

from __future__ import annotations

import ast
import copy
import json
import unittest

from kyuura_engine import check_invariants
from kyuura_engine.view_record import dumps_view_record, loads_view_record, validate_view_record
from tests import helpers as H
from tests import test_exeggutor_bilingual_names_v0_131 as T131
from tests import test_neo_trainer_components_v0_80 as T80
from tests import test_remaining_stadiums_v0_74 as T74
from tests import test_search_recovery_trainers_v0_73 as T73
from tests.test_reveal_identify_v0_184 import REQ, ROOT, Recorder, Run, uid

FE, MF, CD = T73.FOSSIL_EXCAVATION, H.MYSTERIOUS_FOSSIL, H.CLEFAIRY_DOLL
ENDS = ("0", "1", "spectator", "host")
BUNDLE_KEYS = ["card_ids", "cards", "count", "kind", "player", "trainer_card", "turn"]  # 0.184.0 の項目 + card_ids


def fossil_board():
    return T73.board([FE], deck=[H.FIRE, MF, CD], discard=[MF, CD])


def events(run, key, kind):
    return [e["event"] for e in run.log(key) if e["event"]["kind"] == kind]


def uids_in(entries):
    """出来事のカードの uid の項目（card・cards）に出た uid。"""
    out = set()
    for e in entries:
        ev = e["event"]
        if type(ev.get("card")) is int:
            out.add(ev["card"])
        out |= {u for u in ev.get("cards") or () if type(u) is int}
    return out


def view_record_events(run, viewer):
    return [e for item in run.views[viewer].record().data["entries"] for e in item.get("events") or []]


class FossilExcavationTest(unittest.TestCase):
    def test_f1_f2_f3_deck_pick_is_identified_when_shown(self):
        """F1: 山札から選んだカードの reveal_from_deck に、4 つの入口とも本当の card_id。F2: 選ぶ前は本人以外に組・選べるものの数が届かない。F3: 後の受理で前の項目は変わらない。"""
        st = fossil_board()
        fossil, doll = uid(st, 0, "deck", MF), uid(st, 0, "deck", CD)
        with Recorder() as rec:
            run = Run(self, st, rec)
            run.step(0, "play_trainer", [[uid(st, 0, "hand", FE)]], "使う")
            for key in ("1", "spectator", "host"):  # F2: 決定の時点
                view = run.ends[key].handle({**REQ, "type": "view"})["observation"]
                self.assertEqual(set(view["decision"]), {"kind", "player"}, key)  # 選べるもの・その数は見せない
                self.assertNotIn((fossil, MF), run.known(key))
                self.assertNotIn(fossil, uids_in(run.log(key)))  # uid も出来事に出ない
            run.step(0, "answer_decision", [[fossil]], "山札から加える")
            run.step(0, "end_turn", [], "後の受理（番を終える）")
            run.check_all(["effects.py:SearchNamedFromDeckOrDiscard.resume"])
        for key in ENDS:
            (shown,) = events(run, key, "reveal_from_deck")
            self.assertEqual(shown, {"kind": "reveal_from_deck", "turn": shown["turn"], "player": 0, "card": fossil, "card_id": MF})  # 見せたカード自身の card_id だけ
            if key != "0":
                self.assertNotIn((doll, CD), run.known(key))  # 選ばなかった山札のカードは出ない
                self.assertNotIn(doll, uids_in(run.log(key)))

    def test_n2_discard_pick_unchanged(self):
        """トラッシュの側: retrieve_trainer は 0.184.0 と同じ形（card_id を足さない。トラッシュは公開で、動く前の観測に組がある）。"""
        st = fossil_board()
        trashed = uid(st, 0, "discard", MF)
        with Recorder() as rec:
            run = Run(self, st, rec)
            self.assertIn({"card": trashed, "card_id": MF}, run.ends["1"].handle({**REQ, "type": "view"})["observation"]["players"][0]["discard"])
            run.step(0, "play_trainer", [[uid(st, 0, "hand", FE)]], "使う")
            run.step(0, "answer_decision", [[trashed]], "トラッシュから加える")
            self.assertEqual(rec.calls, [])  # 見せるヘルパーを通らない
        for key in ENDS:
            (got,) = events(run, key, "retrieve_trainer")
            self.assertEqual(sorted(got), ["card", "kind", "player", "trainer_card", "turn"])
            self.assertEqual(events(run, key, "reveal_from_deck"), [])

    def test_n2_none_no_target_and_tower(self):
        """選ばない・選べるものなし・ポケモンタワーの下で選ばない: 見せる出来事はない。タワーの下で山札から選ぶと F と同じく card_id。"""
        st = fossil_board()
        with Recorder() as rec:
            run = Run(self, st, rec)
            run.step(0, "play_trainer", [[uid(st, 0, "hand", FE)]], "使う")
            run.step(0, "answer_decision", [[]], "選ばない")
        st2 = T73.board([FE], deck=[H.FIRE, CD])
        with Recorder() as rec2:
            run2 = Run(self, st2, rec2)
            run2.step(0, "play_trainer", [[uid(st2, 0, "hand", FE)]], "選べるものなし")
        for r in (run, run2):
            self.assertEqual(r.rec.calls, [])
            for key in ENDS:
                self.assertEqual(events(r, key, "reveal_from_deck"), [])
                self.assertEqual(len(events(r, key, "trainer_take_none")), 1)
        tower = T74.placed(T74.POKEMON_TOWER, hand=[FE], deck=[MF, H.GRASS], discard=[MF])
        with Recorder() as rec3:
            run3 = Run(self, tower, rec3)
            run3.step(0, "play_trainer", [[uid(tower, 0, "hand", FE)]], "使う（タワー）")
            run3.step(0, "answer_decision", [[uid(tower, 0, "deck", MF)]], "山札から加える（タワー）")
            run3.check_all(["effects.py:SearchNamedFromDeckOrDiscard.resume"])


class SlotGameTest(unittest.TestCase):
    def play(self, state):
        with Recorder() as rec:
            run = Run(self, state, rec)
            for key in ENDS:  # 公開の前には束の出来事はない
                self.assertEqual(events(run, key, "reveal_deck_top"), [])
            deck_before = list(state.players[0].deck)
            run.step(0, "play_trainer", [[uid(state, 0, "hand", T80.SLOT_GAME)]], "使う")
            run.step(0, "end_turn", [], "後の受理（番を終える）")
        after = run.state
        bundles = {key: events(run, key, "reveal_deck_top") for key in ENDS}
        first = bundles["spectator"][0]
        for key in ENDS:
            (b,) = bundles[key]
            self.assertEqual(sorted(b), BUNDLE_KEYS, key)
            self.assertEqual(b, first, key)  # 4 つの入口で同じ値（公開）
            self.assertEqual((len(b["cards"]), len(b["card_ids"]), b["count"]), (3, 3, 3))
            self.assertEqual(len(set(b["cards"])), 3)
            self.assertTrue(set(b["cards"]) <= set(deck_before))
            self.assertEqual(b["card_ids"], [run.true_ids[u] for u in b["cards"]])  # 位置ごとの対応（まとめない・並べかえない）
            taken = events(run, key, "reveal_from_deck")
            for t in taken:  # 手札に加えたカードは束の同じ位置の値
                self.assertIn(t["card"], b["cards"])
                self.assertEqual(t["card_id"], b["card_ids"][b["cards"].index(t["card"])])
            returned = [u for u in b["cards"] if u not in {t["card"] for t in taken}]
            self.assertTrue(all(u in after.players[0].deck for u in returned))
            if key != "0":
                for u in b["cards"]:  # もどしたカードも、束を見せた時点で識別できる
                    self.assertIn((u, run.true_ids[u]), {(c, i) for c, i in zip(b["cards"], b["card_ids"])})
        for key, v in (("0", 0), ("1", 1), ("spectator", None)):
            self.assertEqual(run.log(key), view_record_events(run, v), key)
        for i, snap in enumerate(run.snapshots[:-1]):  # 後の受理で前の項目は変わらない
            for key, entries in snap.items():
                self.assertEqual(run.log(key)[:len(entries)], entries, (i, key))
        self.assertEqual(check_invariants(after), [])
        return run, first, {key: events(run, key, "reveal_from_deck") for key in ENDS}

    def test_s1_two_same_named_and_one_returned(self):
        run, b, taken = self.play(T80.board([T80.SLOT_GAME], deck=[T80.W, T80.W, T80.G]))
        self.assertEqual(sorted(b["card_ids"]), sorted([T80.W, T80.W, T80.G]))
        self.assertEqual(len(taken["1"]), 2)

    def test_s2_three_with_the_same_card_id_are_kept_per_position(self):
        run, b, taken = self.play(T80.board([T80.SLOT_GAME], deck=[T80.W, T80.W, T80.W]))
        self.assertEqual(b["card_ids"], [T80.W, T80.W, T80.W])
        self.assertEqual(len(taken["spectator"]), 3)

    def test_s3_no_pair_all_returned_but_identified(self):
        run, b, taken = self.play(T80.board([T80.SLOT_GAME], deck=[T80.W, T80.G, T80.F]))
        self.assertEqual(sorted(b["card_ids"]), sorted([T80.W, T80.G, T80.F]))
        self.assertEqual(taken["1"], [])

    def test_s3_top_three_of_a_longer_deck(self):
        run, b, taken = self.play(T80.board([T80.SLOT_GAME], deck=[T80.W, T80.W, T80.G, T80.F, T80.L, T80.P]))
        self.assertEqual(len(run.state.players[0].deck) + len(taken["0"]), 6)

    def test_s4_name_variants_different_card_ids(self):
        st = T131.board(T131.mon(T131.HITMONCHAN, (T131.FIGHTING,)), hand=(T131.SLOT_GAME,), deck=[T131.EXEGGUTOR, T131.PROMO, T131.RATTATA])
        run, b, taken = self.play(st)
        self.assertEqual(sorted(b["card_ids"]), sorted([T131.EXEGGUTOR, T131.PROMO, T131.RATTATA]))
        self.assertEqual(sorted(t["card_id"] for t in taken["1"]), sorted([T131.EXEGGUTOR, T131.PROMO]))

    def test_n1_short_deck_is_refused_before_use(self):
        """山札 2 枚: 既存の TOP1 で使う前に止まり、公開は増えない（カーネルでは状態・ログ・乱数も同じ）。"""
        state = T80.board([T80.SLOT_GAME], deck=[T80.W, T80.W])
        T80.rejects(self, state, lambda s: T80.PlayTrainer(0, T80.card_of(s, T80.SLOT_GAME)), T80.NEW_CODES["TOP1"])
        with Recorder() as rec:
            run = Run(self, state, rec)
            before = {k: run.log(k) for k in ENDS}
            session = run.hub._host.session(0)
            c = session.candidates()
            for cand in [x for x in c["candidates"] if x["kind"] == "play_trainer"]:
                stages = (session.inputs(c["game"], c["revision"], cand["id"]) or {}).get("stages") or []
                ids = [o["id"] for o in stages[0]["options"] if o.get("card") == uid(state, 0, "hand", T80.SLOT_GAME)] if stages else []
                if ids:
                    self.assertNotEqual(session.submit(c["game"], c["revision"], cand["id"], tuple(ids[:1])).outcome, "accepted")
            self.assertEqual({k: run.log(k) for k in ENDS}, before)


class PrivateBundleTest(unittest.TestCase):
    """N3: 本人だけが見る束（代表）。相手・観戦者・ホストに uid・card_id の組も card_ids も届かない。"""

    def assert_private_look(self, run, owner=0):
        for key in ENDS:
            for e in events(run, key, "look_at_deck_top") + events(run, key, "arrange_deck_top"):
                self.assertNotIn("card_ids", e)
                if key != str(owner):
                    self.assertNotIn("cards", e, key)
                    self.assertIn("cards", e.get("hidden") or {}, key)

    def test_master_ball(self):
        st = T73.board([T73.MASTER_BALL], deck=[T73.RATTATA] + [T73.FIRE] * 7)
        with Recorder() as rec:
            run = Run(self, st, rec)
            run.step(0, "play_trainer", [[uid(st, 0, "hand", T73.MASTER_BALL)]], "")
            run.step(0, "answer_decision", [[uid(st, 0, "deck", T73.RATTATA)]], "加える")
        self.assert_private_look(run)
        fires = set(u for u in st.players[0].deck if st.cards[u].card_id == T73.FIRE)
        for key in ("1", "spectator", "host"):
            self.assertFalse({u for u, _ in run.known(key)} & fires, key)

    def test_pokedex_808(self):
        st = T80.board([T80.POKEDEX_808], deck=[T80.W, T80.G, T80.F, T80.L, T80.P, T80.W])
        with Recorder() as rec:
            run = Run(self, st, rec)
            run.step(0, "play_trainer", [[uid(st, 0, "hand", T80.POKEDEX_808)]], "")
            run.step(0, "answer_decision", [list(run.state.decision.options)], "並べる")
            self.assertEqual(rec.calls, [])
        self.assert_private_look(run)
        for key in ("1", "spectator", "host"):
            self.assertFalse({u for u, _ in run.known(key)} & set(st.players[0].deck), key)


class FormatAndScopeTest(unittest.TestCase):
    def test_n5_old_bundle_without_card_ids_still_loads(self):
        """card_ids のない旧形式の束の出来事をふくむ閲覧用記録も読み込め、検査の結果が同じ（補う処理はない）。"""
        with Recorder() as rec:
            run = Run(self, T80.board([T80.SLOT_GAME], deck=[T80.W, T80.G, T80.F]), rec)
            run.step(0, "play_trainer", [[uid(run.state, 0, "hand", T80.SLOT_GAME)]], "使う")
        data = copy.deepcopy(run.views[1].record().data)
        stripped = 0
        for e in data["entries"]:
            for x in e.get("events") or []:
                if x["event"]["kind"] == "reveal_deck_top":
                    x["event"].pop("card_ids")
                    stripped += 1
        self.assertEqual(stripped, 1)
        text = json.dumps(data, ensure_ascii=False)
        record = loads_view_record(text)
        self.assertEqual(json.loads(dumps_view_record(record)), json.loads(text))
        self.assertNotIn("card_ids", dumps_view_record(record))
        self.assertEqual(validate_view_record(record), validate_view_record(loads_view_record(json.dumps(run.views[1].record().data, ensure_ascii=False))))

    def test_s5_single_bundle_generator_writes_card_ids(self):
        """reveal_deck_top を生成するのはパッケージの中で RevealDeckTopTakeSameNamed.resolve の 1 か所だけで、card_ids を cards から作る。"""
        found = []
        for path in sorted((ROOT / "kyuura_engine").rglob("*.py")):
            tree = ast.parse(path.read_text(encoding="utf-8"))
            for cls in [n for n in ast.walk(tree) if isinstance(n, ast.ClassDef)]:
                for fn in [n for n in cls.body if isinstance(n, ast.FunctionDef)]:
                    for n in ast.walk(fn):
                        if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute) and n.func.attr == "add_event" and n.args \
                                and isinstance(n.args[0], ast.Constant) and n.args[0].value == "reveal_deck_top":
                            found.append((path.name, cls.name, fn.name, sorted(k.arg for k in n.keywords)))
        self.assertEqual(found, [("effects.py", "RevealDeckTopTakeSameNamed", "resolve", ["card_ids", "cards", "count", "player", "trainer_card"])])
        src = (ROOT / "kyuura_engine" / "effects.py").read_text(encoding="utf-8")
        self.assertEqual(src.count('"reveal_deck_top"'), 1)

    def test_n6_fossil_call_site(self):
        """化石の発掘の山札の側だけが identify=True。トラッシュの側は retrieve_trainer のまま。"""
        src = (ROOT / "kyuura_engine" / "effects.py").read_text(encoding="utf-8")
        start = src.index("class SearchNamedFromDeckOrDiscard(")
        body = src[start:src.index("\nclass ", start + 1)]
        self.assertEqual(body.count("reveal_deck_to_hand("), 1)
        self.assertIn("reveal_deck_to_hand(state, use.player, card, identify=True)", body)
        self.assertIn('state.add_event("retrieve_trainer", player=use.player, card=card, trainer_card=use.card)', body)


if __name__ == "__main__":
    unittest.main()

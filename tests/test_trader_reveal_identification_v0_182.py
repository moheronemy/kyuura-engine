"""v0.182: ポケモン交換おじさん（PMCG1-093）の「相手プレイヤーに見せる」2 枚（手札から山札にもどすカード・山札から選んで手札に加えるカード）を、
公開の出来事 ``return_to_deck``・``reveal_from_deck`` の ``card_id`` で、その時点に識別できるようにする（docs/trader-reveal-identification-design.md 6 章の案 A。
docs/pokemon-trader-v0.24.md の PT6・PT13）。

- 生成: ``zones.return_hand_to_deck``・``zones.reveal_deck_to_hand`` のキーワードだけの引数 ``identify``（既定 False）。真のときだけ出来事に ``card_id`` を書く。
  ``effects.TradePokemonWithDeck`` の 2 つの呼ぶ箇所だけが真を渡す。ほかの呼ぶ箇所の出来事の形・公開の範囲は今までどおり。
- 配信: 2 つの出来事は ``PUBLIC_EVENTS`` のままなので、使用者・相手・観戦者に同じ値が届く。パソコン通信の ``search_deck`` は ``PRIVATE_FIELDS`` のまま非公開。
- 盤面は既存の ``tests/test_pokemon_trader_v0_24.board``・``tests/test_computer_search_v0_22.board``（構築盤面。new_game からの到達の実績には数えない）。
  進め方は ``ClientHub.from_state`` の ``ActionHost`` のプレイヤーのセッション（候補 → 入力 → 送信）。閲覧用記録は ``ViewRecorder.attach``。
"""

from __future__ import annotations

import copy
import inspect
import json
import re
import unittest
from pathlib import Path

from kyuura_engine import check_invariants, zones
from kyuura_engine.client_api import ClientHub
from kyuura_engine.observation import visible_log
from kyuura_engine.view_record import ViewRecorder, dumps_view_record, loads_view_record, validate_view_record
from tests import test_computer_search_v0_22 as CS
from tests import test_pokemon_trader_v0_24 as PT
from tests.helpers import BILL, DEWGONG, FIRE, IVYSAUR, PONYTA, SEEL, WATER

ROOT = Path(__file__).resolve().parent.parent
VIEWERS = (0, 1, None)
TRADER, COMPUTER_SEARCH = "PMCG1-093", "PMCG1-090"


def _pairs(obj, out):
    """値の中で、同じ辞書に card（uid）と card_id が並ぶ組。"""
    if isinstance(obj, dict):
        if isinstance(obj.get("card"), int) and isinstance(obj.get("card_id"), str):
            out.add((obj["card"], obj["card_id"]))
        for v in obj.values():
            _pairs(v, out)
    elif isinstance(obj, (list, tuple)):
        for v in obj:
            _pairs(v, out)
    return out


def _ints(obj, out):
    if isinstance(obj, bool):
        return out
    if isinstance(obj, int):
        out.add(obj)
    elif isinstance(obj, dict):
        for v in obj.values():
            _ints(v, out)
    elif isinstance(obj, (list, tuple)):
        for v in obj:
            _ints(v, out)
    return out


class Game:
    """構築盤面を ClientHub の正規の入口で進め、3 閲覧者の閲覧用記録と公開の更新を集める。"""

    def __init__(self, state):
        assert not check_invariants(state)
        self.hub = ClientHub.from_state(state, verifier=self._on)
        self.recorders = {v: ViewRecorder.attach(v, self.hub._state()) for v in VIEWERS}
        self.delivered = {v: [] for v in VIEWERS}

    def _on(self, actor, result):
        for v in VIEWERS:
            self.recorders[v].add(result)

    @property
    def state(self):
        return self.hub._state()

    def collect(self):
        """今までに各閲覧者へ届いた値（更新と閲覧用記録の全項目）。"""
        for v in VIEWERS:
            self.delivered[v] += self.hub.take_updates(v if v is not None else "spectator")
        return {v: {"updates": list(self.delivered[v]), "record": self.recorders[v].record().data} for v in VIEWERS}

    def submit(self, kind, uids):
        session = self.hub._host.session(0)
        c = session.candidates()
        for cand in c["candidates"]:
            if cand["kind"] != kind:
                continue
            for st in (session.inputs(c["game"], c["revision"], cand["id"]) or {}).get("stages") or []:
                ids = tuple(o["id"] for o in st.get("options") or [] if o.get("card") in uids)
                if ids:
                    result = session.submit(c["game"], c["revision"], cand["id"], ids)
                    assert result.outcome == "accepted", result
                    assert not check_invariants(self.state)
                    return result
        raise AssertionError(f"候補 {kind} に {uids} がない")


class TraderBase(unittest.TestCase):
    def start(self, hand=(DEWGONG, FIRE), deck=(WATER, SEEL, BILL, PT.BULBASAUR, IVYSAUR), give=DEWGONG, take=IVYSAUR, take_index=0):
        state = PT.board(hand=hand, deck=deck)
        game = Game(state)
        trader = PT.by_id(state, 0, "hand", TRADER)[0]
        returned = PT.by_id(state, 0, "hand", give)[0]
        taken = PT.by_id(state, 0, "deck", take)[take_index]
        return game, trader, returned, taken

    def run_both(self, **kw):
        game, trader, returned, taken = self.start(**kw)
        points = {"T1": game.collect()}
        game.submit("play_trainer", {trader})
        points["T1b"] = game.collect()
        game.submit("answer_decision", {returned})
        points["T2"] = game.collect()
        game.submit("answer_decision", {taken})
        points["T4"] = game.collect()
        return game, returned, taken, points


class EventFieldTest(TraderBase):
    def test_return_event_has_card_id_of_the_returned_card(self):
        game, returned, taken, _ = self.run_both()
        events = [dict(e) for e in game.state.log if e["kind"] == "return_to_deck"]
        self.assertEqual(events, [{"kind": "return_to_deck", "turn": PT.TURN, "player": 0, "card": returned, "card_id": DEWGONG}])

    def test_reveal_event_has_card_id_of_the_chosen_card(self):
        game, returned, taken, _ = self.run_both()
        events = [dict(e) for e in game.state.log if e["kind"] == "reveal_from_deck"]
        self.assertEqual(events, [{"kind": "reveal_from_deck", "turn": PT.TURN, "player": 0, "card": taken, "card_id": IVYSAUR}])
        self.assertEqual(game.state.cards[taken].card_id, IVYSAUR)

    def test_event_kinds_and_order_unchanged(self):
        game, returned, taken, _ = self.run_both()
        kinds = [e["kind"] for e in game.state.log[-5:]]
        self.assertEqual(kinds, ["play_trainer", "return_to_deck", "reveal_from_deck", "shuffle", "discard_trainer"])


class ViewersTest(TraderBase):
    def identified(self, delivered, uid, card_id):
        return (uid, card_id) in _pairs(delivered, set())

    def test_all_viewers_identify_the_returned_card_when_it_is_shown(self):
        game, returned, taken, p = self.run_both()
        for v in VIEWERS:
            self.assertTrue(self.identified(p["T2"][v], returned, DEWGONG), v)
            if v != 0:
                self.assertFalse(self.identified(p["T1b"][v], returned, DEWGONG), v)  # 選ぶ前には出さない

    def test_all_viewers_identify_the_taken_card_when_it_is_shown(self):
        game, returned, taken, p = self.run_both()
        for v in VIEWERS:
            self.assertTrue(self.identified(p["T4"][v], taken, IVYSAUR), v)
            if v != 0:
                for t in ("T1", "T1b", "T2"):  # 選ぶ前（決定のあいだもふくむ）には、uid もカード ID も出さない
                    self.assertFalse(self.identified(p[t][v], taken, IVYSAUR), (v, t))
                    events = [x["event"] for e in p[t][v]["record"]["entries"] for x in e.get("events") or []]
                    self.assertFalse(any(ev.get("card") == taken or taken in (ev.get("cards") or ()) for ev in events), (v, t))

    def test_nothing_new_before_use_or_before_choosing(self):
        game, returned, taken, p = self.run_both()
        for v in (1, None):
            for t in ("T1", "T1b"):
                text = json.dumps(p[t][v], ensure_ascii=False)
                self.assertNotIn(f'"card": {returned}, "card_id"', text)
                self.assertNotIn(f'"card": {taken}, "card_id"', text)

    def test_other_hand_and_deck_cards_are_not_shown(self):
        game, returned, taken, p = self.run_both()
        st = game.state
        hidden = (set(st.players[0].deck) | set(st.players[0].hand)) - {returned, taken}
        for v in (1, None):
            for e in visible_log(st, v)[-5:]:
                written = set(e.get("cards", ())) | ({e["card"]} if "card" in e else set())
                self.assertTrue(hidden.isdisjoint(written), (v, e))
            known = {u for (u, _) in _pairs(p["T4"][v], set())}
            self.assertTrue(hidden.isdisjoint(known - {returned, taken}), v)

    def test_view_record_events_equal_visible_log(self):
        game, returned, taken, p = self.run_both()
        for v in VIEWERS:
            entries = p["T4"][v]["record"]["entries"]
            recorded = [x["event"] for e in entries[1:] for x in e.get("events") or []]
            self.assertEqual(recorded, list(visible_log(game.state, v))[-len(recorded):], v)

    def test_earlier_view_record_entries_do_not_change_after_later_actions(self):
        game, returned, taken, p = self.run_both()
        before = {v: copy.deepcopy(p["T2"][v]["record"]["entries"]) for v in VIEWERS}
        session = game.hub._host.session(0)
        c = session.candidates()
        end = next(x for x in c["candidates"] if x["kind"] == "end_turn")
        self.assertEqual(session.submit(c["game"], c["revision"], end["id"], ()).outcome, "accepted")
        after = game.collect()
        for v in VIEWERS:
            self.assertEqual(after[v]["record"]["entries"][:len(before[v])], before[v], v)


class SameNameTest(TraderBase):
    def test_same_card_id_copy_is_not_confused(self):
        """もどすカード（手札のジュゴン）と同じカード ID の別の 1 枚（山札のジュゴン）を選ぶ。2 つの出来事の uid は別で、どちらも正しい card_id。"""
        game, returned, taken, p = self.run_both(hand=(DEWGONG, FIRE), deck=(WATER, SEEL, BILL, DEWGONG, IVYSAUR), give=DEWGONG, take=DEWGONG, take_index=0)
        self.assertNotEqual(returned, taken)
        ret = next(e for e in game.state.log if e["kind"] == "return_to_deck")
        rev = next(e for e in game.state.log if e["kind"] == "reveal_from_deck")
        self.assertEqual((ret["card"], ret["card_id"]), (returned, DEWGONG))
        self.assertEqual((rev["card"], rev["card_id"]), (taken, DEWGONG))
        for v in (1, None):
            known = _pairs(p["T2"][v], set())
            self.assertIn((returned, DEWGONG), known)
            self.assertNotIn((taken, DEWGONG), known)  # 選ぶ前に、山札の同名の 1 枚を出さない


class ComputerSearchControlTest(unittest.TestCase):
    def test_searched_card_stays_hidden_and_discards_stay_public(self):
        state = CS.board()
        game = Game(state)
        cs = CS.by_id(state, 0, "hand", COMPUTER_SEARCH)[0]
        disc = [CS.by_id(state, 0, "hand", FIRE)[0], CS.by_id(state, 0, "hand", PONYTA)[0]]
        pick = CS.by_id(state, 0, "deck", BILL)[0]
        game.submit("play_trainer", {cs})
        game.submit("answer_decision", set(disc))
        game.submit("answer_decision", {pick})
        got = game.collect()
        for v in (1, None):
            search = [e for e in visible_log(game.state, v) if e["kind"] == "search_deck"]
            self.assertEqual(search, [{"kind": "search_deck", "turn": 5, "player": 0, "hidden": {"card": None}}], v)
            self.assertNotIn(pick, _ints([x.get("events") for x in got[v]["record"]["entries"]], set()), v)
            self.assertNotIn(pick, {u for (u, _) in _pairs(got[v], set())}, v)
            known = _pairs(got[v], set())
            for u in disc:
                self.assertIn((u, game.state.cards[u].card_id), known, v)  # トラッシュ（公開）の既存の公開は同じ
        own = [e for e in visible_log(game.state, 0) if e["kind"] == "search_deck"]
        self.assertEqual(own[0]["card"], pick)


class HelperDefaultTest(unittest.TestCase):
    def test_identify_is_keyword_only_and_false_by_default(self):
        for fn in (zones.return_hand_to_deck, zones.reveal_deck_to_hand):
            p = inspect.signature(fn).parameters["identify"]
            self.assertEqual((p.kind, p.default), (inspect.Parameter.KEYWORD_ONLY, False), fn.__name__)

    def test_default_call_keeps_the_previous_event_shape(self):
        state = PT.board()
        card = PT.by_id(state, 0, "hand", DEWGONG)[0]
        zones.return_hand_to_deck(state, 0, card)
        self.assertEqual(dict(state.log[-1]), {"kind": "return_to_deck", "turn": PT.TURN, "player": 0, "card": card})
        state = PT.board()
        card = PT.by_id(state, 0, "deck", IVYSAUR)[0]
        zones.reveal_deck_to_hand(state, 0, card)
        self.assertEqual(dict(state.log[-1]), {"kind": "reveal_from_deck", "turn": PT.TURN, "player": 0, "card": card})

    def test_only_trader_passes_identify(self):
        """パッケージの中で identify=True を渡すのは effects.TradePokemonWithDeck の 2 つの呼ぶ箇所だけ。ほかの呼ぶ箇所（effects.py の 12・
        resolution/programs.py の 6。設計の時点で数えた 8 は effects.py の一部だけだった。docs/trader-reveal-identification-v0.182.md）は既定のまま。"""
        counts, with_identify = {}, []
        for path in sorted((ROOT / "kyuura_engine").rglob("*.py")):
            src = path.read_text(encoding="utf-8")
            if path.name == "zones.py":
                continue
            calls = [m for m in re.finditer(r"\b(return_hand_to_deck|reveal_deck_to_hand)\(", src) if not src[:m.start()].endswith("def ")]
            if calls:
                counts[path.relative_to(ROOT).as_posix()] = len(calls)
            for m in calls:
                line = src[m.start():src.index("\n", m.start())]
                self.assertNotIn("identify=False", line)
                if "identify" in line:
                    self.assertIn("identify=True", line)
                    with_identify.append((path.name, re.findall(r"^class (\w+)", src[:m.start()], re.M)[-1], m.group(1)))
        self.assertEqual(counts, {"kyuura_engine/effects.py": 14, "kyuura_engine/resolution/programs.py": 6})
        self.assertEqual(with_identify, [("effects.py", "TradePokemonWithDeck", "return_hand_to_deck"),
                                         ("effects.py", "TradePokemonWithDeck", "reveal_deck_to_hand")])


class OldFormatTest(TraderBase):
    def test_view_record_without_card_id_still_loads(self):
        """card_id のない旧形式の出来事をふくむ閲覧用記録も、読み込み・検査で壊れない（card_id を補う処理はない）。"""
        game, returned, taken, p = self.run_both()
        data = copy.deepcopy(p["T4"][1]["record"])
        for e in data["entries"]:
            for x in e.get("events") or []:
                if x["event"]["kind"] in ("return_to_deck", "reveal_from_deck"):
                    x["event"].pop("card_id", None)
        text = json.dumps(data, ensure_ascii=False)
        record = loads_view_record(text)
        self.assertEqual(json.loads(dumps_view_record(record)), json.loads(text))
        self.assertEqual(validate_view_record(record), validate_view_record(loads_view_record(json.dumps(p["T4"][1]["record"], ensure_ascii=False))))


if __name__ == "__main__":
    unittest.main()

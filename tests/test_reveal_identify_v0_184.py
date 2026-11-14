"""v0.184（docs/reveal-identify-v0.184.md。再現と設計は docs/reveal-call-sites-repro-fix-design.md）: 「相手プレイヤーに見せてから」手札に加える・山札にもどす
17 の呼ぶ箇所で、出来事（``reveal_from_deck``・``return_to_deck``）に見せたカード自身の ``card_id`` を書く（``identify=True``）。

- 盤面は既存のテストの盤面の関数（再現の単位と同じ。構築盤面で、new_game からの到達の実績には数えない）。進め方は ``ClientHub.from_state`` のプレイヤーのセッション（候補 → 入力 → 送信）
- 呼ぶ箇所の通過は、effects・programs のモジュールの名前のヘルパーを、呼び元を記録するだけの包みに置きかえて確かめる（同じ引数で元の関数を呼ぶ。受理した状態への呼び出しだけを数える）
- 閲覧者は、山札の持ち主・その相手・観戦者・ホスト（観戦者の写し）。相手・観戦者の識別は、その入口の ``log`` に届いた出来事の uid と card_id の組だけで判定する
- 同じ呼ぶ箇所を通るほかのカード（同じ処理の登録）は、ここでは実行していない（docs 3 章の「共有」）
"""

from __future__ import annotations

import copy
import sys
import unittest
from pathlib import Path
from unittest import mock

from kyuura_engine import check_invariants, effects, zones
from kyuura_engine.client_api import CONTRACT, FORMAT, ClientHub
from kyuura_engine.coins import CoinSide
from kyuura_engine.resolution import programs
from kyuura_engine.view_record import ViewRecorder
from tests import helpers as H
from tests import test_computer_search_v0_22 as T22
from tests import test_deck_search_decision_presence_v0_150 as T150
from tests import test_declared_entry_powers_v0_43 as T43
from tests import test_light_powers_evolution_v0_84 as T84
from tests import test_neo_trainer_components_v0_80 as T80
from tests import test_search_recovery_trainers_v0_73 as T73
from tests import test_search_retrieval_v0_53 as T53
from tests import test_unown_idfnj_powers_v0_97 as T97
from tests import test_variable_coins_search_attachments_v0_113 as T113

ROOT = Path(__file__).resolve().parent.parent
HD = CoinSide.HEADS
VIEWERS = (0, 1, None)
REQ = {"contract": CONTRACT, "format": FORMAT}
SHOWN = ("reveal_from_deck", "return_to_deck")


def uid(state, player, zone, card_id, index=0):
    return [u for u in getattr(state.players[player], zone) if state.cards[u].card_id == card_id][index]


def pairs(obj, out):
    if isinstance(obj, dict):
        if isinstance(obj.get("card"), int) and isinstance(obj.get("card_id"), str):
            out.add((obj["card"], obj["card_id"]))
        for v in obj.values():
            pairs(v, out)
    elif isinstance(obj, (list, tuple)):
        for v in obj:
            pairs(v, out)
    return out


class Recorder:
    """呼ぶ箇所の通過の記録（effects・programs のモジュールの名前を包む）。"""

    def __init__(self):
        self.calls = []
        self._patches = []

    def __enter__(self):
        for mod in (effects, programs):
            for name in ("reveal_deck_to_hand", "return_hand_to_deck"):
                if hasattr(mod, name):
                    original = getattr(zones, name)

                    def wrapper(*args, _name=name, _original=original, **kwargs):
                        f = sys._getframe(1)
                        self.calls.append({"state": args[0], "helper": _name, "where": f"{Path(f.f_code.co_filename).name}:{f.f_code.co_qualname}",
                                           "card": args[2], "identify": kwargs.get("identify", False)})
                        return _original(*args, **kwargs)

                    p = mock.patch.object(mod, name, wrapper)
                    p.start()
                    self._patches.append(p)
        return self

    def __exit__(self, *exc):
        for p in self._patches:
            p.stop()


class Run:
    """構築盤面を ClientHub で進め、4 つの入口の log と 3 閲覧者の閲覧用記録を集める。"""

    def __init__(self, test, state, rec):
        assert not check_invariants(state)
        self.test, self.rec = test, rec
        self.hub = ClientHub.from_state(state)
        self.views = {v: ViewRecorder.attach(v, self.state) for v in VIEWERS}
        self.hub._verifier = lambda actor, result: [self.views[v].add(result) for v in VIEWERS]
        self.ends = {"0": self.hub.player(0), "1": self.hub.player(1), "spectator": self.hub.spectator(), "host": self.hub.host()}
        self.true_ids = {u: c.card_id for u, c in self.state.cards.items()}
        self.targets = []  # (段の名前, 呼び元, uid, 持ち主, identify)
        self.snapshots = []  # 各段のあとの log の写し（前の項目が変わらないことの確かめ）

    @property
    def state(self):
        return self.hub._state()

    def log(self, key):
        entries, start = [], None
        while True:
            a = self.ends[key].handle({**REQ, "type": "log", **({} if start is None else {"from": start})})
            self.test.assertTrue(a["ok"], a)
            entries += a["entries"]
            start = a["next"]
            if a["complete"]:
                return entries

    def known(self, key):
        return pairs(self.log(key), set())

    def step(self, actor, kind, picks=(), label=""):
        session = self.hub._host.session(actor)
        c = session.candidates()
        cand = next(x for x in c["candidates"] if x["kind"] == kind)
        stages = (session.inputs(c["game"], c["revision"], cand["id"]) or {}).get("stages") or []
        choices = []
        for i, stage in enumerate(stages):
            wanted = list(picks[i]) if i < len(picks) else []
            for o in stage.get("options") or []:
                key = o["value"] if "value" in o else (o.get("pokemon") if stage.get("meaning") == "pokemon" else (o.get("attack_index") if stage.get("meaning") == "attack" else o.get("card")))
                if key in wanted:
                    choices.append(o["id"])
                    wanted.remove(key)
            self.test.assertEqual(wanted, [], (label, kind, i))
        before = {k: self.known(k) for k in self.ends}
        mark = len(self.rec.calls)
        self.test.assertTrue(session.check(c["game"], c["revision"], cand["id"], tuple(choices)).get("valid"), (label, kind))
        result = session.submit(c["game"], c["revision"], cand["id"], tuple(choices))
        self.test.assertEqual(result.outcome, "accepted", (label, kind, result.refusal))
        self.test.assertEqual(check_invariants(self.state), [])
        final = self.state
        calls = [cl for cl in self.rec.calls[mark:] if cl["state"] is final]
        for cl in calls:
            self.targets.append({"label": label or kind, "where": cl["where"], "helper": cl["helper"], "uid": cl["card"], "owner": final.cards[cl["card"]].owner,
                                 "identify": cl["identify"], "before": {k: (cl["card"], self.true_ids[cl["card"]]) in before[k] for k in before}})
        self.snapshots.append({k: copy.deepcopy(self.log(k)) for k in self.ends})
        return calls

    def check_all(self, expected_where):
        """持ち主・相手・観戦者・ホストの識別、閲覧用記録との一致、選ぶ前の非公開、前の項目の不変。"""
        t = self.test
        hit = sorted({x["where"] for x in self.targets})
        t.assertEqual(hit, sorted(set(expected_where)))
        t.assertTrue(self.targets)
        for x in self.targets:
            cid = self.true_ids[x["uid"]]
            for key in self.ends:
                events = [e["event"] for e in self.log(key) if e["event"]["kind"] in SHOWN and e["event"].get("card") == x["uid"]]
                t.assertEqual(len(events), 1, (key, x["label"]))
                t.assertEqual(events[0].get("card_id"), cid, (key, x["label"]))  # 見せたカード自身の card_id
                t.assertIn((x["uid"], cid), self.known(key))
                if key != str(x["owner"]):
                    t.assertFalse(x["before"][key], (key, x["label"]))  # 選ぶ前・見せる前には組がない
            t.assertTrue(x["identify"], x)  # 公開の値を確かめたあとで、呼び出しの引数（補助）
        for key, v in (("0", 0), ("1", 1), ("spectator", None)):
            rec = [e for item in self.views[v].record().data["entries"] for e in item.get("events") or []]
            t.assertEqual(self.log(key), rec, key)
        t.assertEqual(self.log("host"), self.log("spectator"))
        for i, snap in enumerate(self.snapshots[:-1]):  # 後の段のあとも、前に固定した log の項目は同じ
            for key, entries in snap.items():
                t.assertEqual(self.log(key)[:len(entries)], entries, (i, key))


A_TRAINER, B_POWER, C_ATTACK = "A", "B", "C"


class IdentifiedTest(unittest.TestCase):
    """17 の呼ぶ箇所（docs 2 章の表）。各テストは 1 つの事例。"""

    def go(self, state, steps, where):
        with Recorder() as rec:
            run = Run(self, state, rec)
            for step in steps:
                actor, kind, picks, label = step(run) if callable(step) else step
                run.step(actor, kind, picks, label)
            run.check_all(where)
        return run

    # ---- A トレーナー（effects.py）
    def test_a_search_deck_trainer_reveal_true(self):
        st = H.with_coin_results(T53.board([T53.POKE_BALL], deck=[T53.GRASS, T53.MYSTERIOUS_FOSSIL, T53.DARK_GOLBAT, T53.RATTATA]), HD)
        r = uid(st, 0, "deck", T53.RATTATA)
        self.go(st, [(0, "play_trainer", [[uid(st, 0, "hand", T53.POKE_BALL)]], "使う"), (0, "answer_decision", [[r]], "加える"),
                     (0, "play_basic", [[r]], "後でベンチに出す")], ["effects.py:SearchDeckTrainer.resume"])

    def test_a_master_ball(self):
        st = T73.board([T73.MASTER_BALL], deck=[T73.RATTATA] + [T73.FIRE] * 7)
        self.go(st, [(0, "play_trainer", [[uid(st, 0, "hand", T73.MASTER_BALL)]], ""), (0, "answer_decision", [[uid(st, 0, "deck", T73.RATTATA)]], "加える")],
                ["effects.py:LookTopTakePokemonThenShuffle.resume"])

    def test_a_energy_ark(self):
        st = H.with_coin_results(T80.board([T80.ENERGY_ARK], deck=[T80.W, T80.G, H.RATTATA, T80.F]), HD, HD)
        self.go(st, [(0, "play_trainer", [[uid(st, 0, "hand", T80.ENERGY_ARK)]], ""), (0, "answer_decision", [[uid(st, 0, "deck", T80.W), uid(st, 0, "deck", T80.G)]], "加える")],
                ["effects.py:CoinsSearchBasicEnergyPerHeads.resume"])

    def test_a_energy_amplifier_return_and_take(self):
        import random
        st = None
        for seed in range(200):  # 山札を切ってからコインを投げる: 既存の補助 answer_with_first_coin と同じ方法で、最初のコインが「おもて」になる乱数（テスト専用）
            probe = T80.board([T80.ENERGY_AMPLIFIER, T80.G], deck=[T80.W, H.RATTATA])
            probe.rng = random.Random(seed)
            waiting = T80.use(probe.clone(), T80.ENERGY_AMPLIFIER)
            after = T80.answer(waiting, waiting.decision.options)
            if [e["result"] for e in after.log[len(waiting.log):] if e["kind"] == "coin_flip"][:1] == [HD.value]:
                st = probe
                break
        self.assertIsNotNone(st)
        self.go(st, [(0, "play_trainer", [[uid(st, 0, "hand", T80.ENERGY_AMPLIFIER)]], ""), (0, "answer_decision", [[uid(st, 0, "hand", T80.G)]], "もどす"),
                     lambda run: (0, "answer_decision", [[uid(run.state, 0, "deck", T80.W)]], "加える")],
                ["effects.py:ReturnHandEnergyThenCoinSearchBasicEnergy.resume"])

    def test_a_slot_game_taken_cards_only(self):
        run = self.go(T80.board([T80.SLOT_GAME], deck=[T80.W, T80.W, T80.W]),
                      [lambda run: (0, "play_trainer", [[uid(run.state, 0, "hand", T80.SLOT_GAME)]], "見せて加える")], ["effects.py:RevealDeckTopTakeSameNamed.resolve"])
        bundle = [e["event"] for e in run.log("1") if e["event"]["kind"] == "reveal_deck_top"]
        self.assertEqual(len(bundle), 1)
        self.assertNotIn("card_id", bundle[0])  # 束全体の出来事は対象外（変えていない。uid だけ）

    def test_a_pokegear(self):
        st = T80.board([T80.POKEGEAR], deck=[H.POTION, T80.W, H.SWITCH, T80.W, T80.W, T80.W, T80.W])
        run = self.go(st, [(0, "play_trainer", [[uid(st, 0, "hand", T80.POKEGEAR)]], ""), (0, "answer_decision", [[uid(st, 0, "deck", H.POTION)]], "加える")],
                      ["effects.py:LookTopTakeTrainerThenShuffleLock.resume"])
        not_taken = uid(st, 0, "deck", H.SWITCH)
        for key in ("1", "spectator", "host"):
            self.assertNotIn(not_taken, {u for (u, _c) in run.known(key)})  # 見た束の選ばなかったトレーナー
            looked = [e["event"] for e in run.log(key) if e["event"]["kind"] == "look_at_deck_top"]
            self.assertEqual([("cards" in e, e.get("hidden", {}).get("cards")) for e in looked], [(False, 7)])

    def test_a_breeder_couple(self):
        st = T84.board(T84.mon(H.MACHOP_NEO4, (T84.FT,), played_turn=1), bench=(T84.mon(H.MACHOP_NEO4, played_turn=1),), hand=(H.BREEDER_COUPLE,),
                       opponent=T84.mon(H.HITMONCHAN), deck=[T84.W, H.LIGHT_MACHOKE, T84.W])
        st = H.with_coin_results(st, HD)
        self.go(st, [(0, "play_trainer", [[uid(st, 0, "hand", H.BREEDER_COUPLE)]], ""), (0, "answer_decision", [[st.players[0].active.pokemon_id]], "ポケモン"),
                     (0, "answer_decision", [[uid(st, 0, "deck", H.LIGHT_MACHOKE)]], "加える")], ["effects.py:BreederCoupleSearch.resume"])

    # ---- B 特殊能力（effects.py）
    def test_b_evolutionary_light(self):
        st = T43.board(T43.mon(T43.DARK_DRAGONAIR, ()), deck=(T43.FIRE, T43.DARK_DRAGONITE, T43.RATTATA, T43.ERIKAS_CLEFABLE, T43.GRASS), prizes=0)
        self.go(st, [(0, "use_power", [[st.players[0].active.pokemon_id]], ""), (0, "answer_decision", [[uid(st, 0, "deck", T43.DARK_DRAGONITE)]], "加える")],
                ["effects.py:SearchEvolutionCardToHand.resume"])

    def test_b_gift_both_players(self):
        berry = "neo1-073"
        togepi = T84.mon(H.TOGEPI_NEO1, (T84.W,), played_turn=1)
        st = T84.board(togepi, hand=(H.LIGHT_TOGETIC,), opponent=T84.mon(H.HITMONCHAN), deck=[T84.W, berry, T84.W], opponent_deck=[T84.W, berry, T84.W])
        run = self.go(st, [(0, "evolve", [[uid(st, 0, "hand", H.LIGHT_TOGETIC)], [st.players[0].active.pokemon_id]], ""), (0, "answer_decision", [[1]], "使う"),
                           (0, "answer_decision", [[1]], "見る"), (0, "answer_decision", [[uid(st, 0, "deck", berry)]], "加える（使った人）"),
                           (1, "answer_decision", [[1]], "見る（相手）"), (1, "answer_decision", [[uid(st, 1, "deck", berry)]], "加える（相手）")],
                      ["effects.py:EachPlayerSearchToolOnEntry.resume"])
        self.assertEqual(sorted(x["owner"] for x in run.targets), [0, 1])

    def test_b_find(self):
        m = T97.mon
        st = T97.board(m(H.RATTATA), bench=(m(T97.UF), m(T97.UI), m(T97.UN), m(T97.UD)), deck=[T97.W, H.POTION, T97.W], prizes=0)
        finder = next(p for p in st.players[0].bench if st.cards[p.card].card_id == T97.UF)
        self.go(st, [(0, "use_power", [[finder.pokemon_id]], ""), (0, "answer_decision", [[uid(st, 0, "deck", H.POTION)]], "加える")],
                ["effects.py:SearchDeckWithBenchLettersToHand.resume"])

    # ---- C ワザの要素（programs.py）
    def t150(self, name, where):
        p = next(x for x in T150.PATHS if x.name.startswith(name))
        st = T150.board(p)
        steps = [(0, "use_attack", [[p.index]], "宣言")]
        for f in p.prelude:
            steps.append(lambda run, f=f: (0, "answer_decision", [list(f(run.state))], "前の決定"))
        steps.append(lambda run: (0, "answer_decision", [[next(u for u in run.state.players[0].deck if run.state.cards[u].card_id == p.target)]], "加える"))
        return self.go(st, steps, [where])

    def test_c_denrei(self):
        self.t150("でんれい", "programs.py:RevealPokemonFromDeck.resume")

    def test_c_named_pokemon_any_and_exactly_one(self):
        self.t150("くらげのむれ", "programs.py:RevealNamedPokemonFromDeck.resume")
        self.t150("りゅうのきずな", "programs.py:RevealNamedPokemonFromDeck.resume")

    def test_c_trainer_or_energy_zero_to_one_required_and_energy(self):
        for name in ("おつかい", "ひらめく", "おつきみ"):
            with self.subTest(name=name):
                self.t150(name, "programs.py:RevealTrainerFromDeck.resume")

    def test_c_heads_or_fewer(self):
        st = T113.board(T113.mon(T113.CLEFAIRY_N1, (T113.W,) * 3), bench=(H.RATTATA, H.RATTATA), opponent=T113.mon(T113.CHANSEY), deck=[T113.W, T113.W, T113.F] + [H.RATTATA] * 6)
        st = H.with_coin_results(st, HD, HD, HD, HD, HD)
        run = self.go(st, [(0, "use_attack", [[1]], ""), (0, "answer_decision", [[uid(st, 0, "deck", T113.W), uid(st, 0, "deck", T113.F)]], "加える")],
                      ["programs.py:RevealTrainerFromDeck.resume"])
        self.assertEqual(len(run.targets), 2)

    def test_c_tejina_return_hidden_then_reveal(self):
        run = self.t150("てじな", "programs.py:ReturnHandThenRevealEnergy.resume")
        for key in ("1", "spectator", "host"):
            back = [e["event"] for e in run.log(key) if e["event"]["kind"] == "hand_to_deck"]
            self.assertEqual(len(back), 1)
            self.assertNotIn("cards", back[0])  # 見せないもどし（対象外）は伏せたまま
            self.assertNotIn("card_id", back[0])

    def test_c_mizukaki_both_players(self):
        W = T84.W
        st = T84.board(T84.mon(H.LIGHT_GOLDUCK, (W,), evolved_from="PMCG3-010"), deck=[W, H.RATTATA, W, W, W], opponent_deck=[W, H.RATTATA, W, W, W])
        run = self.go(st, [(0, "use_attack", [[0]], ""), (0, "answer_decision", [[uid(st, 0, "deck", W)]], "加える（使った人）"),
                           (1, "answer_decision", [[uid(st, 1, "deck", W)]], "加える（相手）")], ["programs.py:EachPlayerLooksTakesBasicEnergy.apply"])
        self.assertEqual(sorted(x["owner"] for x in run.targets), [0, 1])
        for key, own in (("0", 0), ("1", 1)):
            other = 1 - own
            looked = [e["event"] for e in run.log(key) if e["event"]["kind"] == "look_at_deck_top" and e["event"]["player"] == other]
            self.assertEqual(["cards" in e for e in looked], [False])  # 相手の見た束は伏せたまま


class PrivateControlTest(unittest.TestCase):
    """非公開の対照（対象外の経路は変えていない）。"""

    def test_energy_search_reveal_false_and_computer_search(self):
        for name, st, steps in (
            ("エネルギー転送", T53.board([T53.ENERGY_SEARCH], deck=[T53.GRASS, T53.RATTATA, T53.FIRE]),
             [lambda r: (0, "play_trainer", [[uid(r.state, 0, "hand", T53.ENERGY_SEARCH)]], ""), lambda r: (0, "answer_decision", [[uid(r.state, 0, "deck", T53.GRASS)]], "")]),
            ("パソコン通信", T22.board(),
             [lambda r: (0, "play_trainer", [[uid(r.state, 0, "hand", "PMCG1-090")]], ""),
              lambda r: (0, "answer_decision", [[uid(r.state, 0, "hand", H.FIRE), uid(r.state, 0, "hand", H.PONYTA)]], ""),
              lambda r: (0, "answer_decision", [[uid(r.state, 0, "deck", H.BILL)]], "")]),
        ):
            with self.subTest(name=name), Recorder() as rec:
                run = Run(self, st, rec)
                for s in steps:
                    run.step(*s(run))
                self.assertEqual(run.targets, [])  # 17 か所のヘルパーを通らない
                for key in ("1", "spectator", "host"):
                    search = [e["event"] for e in run.log(key) if e["event"]["kind"] == "search_deck"]
                    self.assertEqual([e.get("hidden") for e in search], [{"card": None}])
                    self.assertNotIn("card_id", search[0])

    def test_fossil_excavation_unchanged(self):
        """化石の発掘（E。判断待ち）は既定のまま: 山札から見せる出来事に card_id を書かない。"""
        src = (ROOT / "kyuura_engine" / "effects.py").read_text(encoding="utf-8")
        start = src.index("class SearchNamedFromDeckOrDiscard(")
        body = src[start:src.index("\nclass ", start + 1)]
        self.assertIn("reveal_deck_to_hand(state, use.player, card)", body)
        self.assertNotIn("identify=True", body)


class ScopeTest(unittest.TestCase):
    def test_identify_true_sites(self):
        """補助の確かめ: identify=True を渡すのは、交換おじさんの 2 か所と、この版の 17 か所（effects.py 11・programs.py 6）だけ。"""
        import ast
        found = []
        for rel in ("kyuura_engine/effects.py", "kyuura_engine/resolution/programs.py"):
            tree = ast.parse((ROOT / rel).read_text(encoding="utf-8"))
            for cls in [n for n in tree.body if isinstance(n, ast.ClassDef)]:
                for n in ast.walk(cls):
                    if isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id in ("reveal_deck_to_hand", "return_hand_to_deck"):
                        if any(k.arg == "identify" for k in n.keywords):
                            self.assertTrue(any(k.arg == "identify" and isinstance(k.value, ast.Constant) and k.value.value is True for k in n.keywords))
                            found.append((rel.split("/")[-1], cls.name, n.func.id))
        expected = sorted([("effects.py", "TradePokemonWithDeck", "return_hand_to_deck"), ("effects.py", "TradePokemonWithDeck", "reveal_deck_to_hand"),
                           ("effects.py", "SearchDeckTrainer", "reveal_deck_to_hand"), ("effects.py", "LookTopTakePokemonThenShuffle", "reveal_deck_to_hand"),
                           ("effects.py", "CoinsSearchBasicEnergyPerHeads", "reveal_deck_to_hand"), ("effects.py", "ReturnHandEnergyThenCoinSearchBasicEnergy", "return_hand_to_deck"),
                           ("effects.py", "ReturnHandEnergyThenCoinSearchBasicEnergy", "reveal_deck_to_hand"), ("effects.py", "RevealDeckTopTakeSameNamed", "reveal_deck_to_hand"),
                           ("effects.py", "LookTopTakeTrainerThenShuffleLock", "reveal_deck_to_hand"), ("effects.py", "BreederCoupleSearch", "reveal_deck_to_hand"),
                           ("effects.py", "SearchEvolutionCardToHand", "reveal_deck_to_hand"), ("effects.py", "EachPlayerSearchToolOnEntry", "reveal_deck_to_hand"),
                           ("effects.py", "SearchDeckWithBenchLettersToHand", "reveal_deck_to_hand"),
                           ("programs.py", "RevealPokemonFromDeck", "reveal_deck_to_hand"), ("programs.py", "RevealNamedPokemonFromDeck", "reveal_deck_to_hand"),
                           ("programs.py", "RevealTrainerFromDeck", "reveal_deck_to_hand"), ("programs.py", "RevealTrainerFromDeck", "reveal_deck_to_hand"),
                           ("programs.py", "ReturnHandThenRevealEnergy", "reveal_deck_to_hand"), ("programs.py", "EachPlayerLooksTakesBasicEnergy", "reveal_deck_to_hand")])
        self.assertEqual(sorted(found), expected)

    def test_helper_default_stays_false(self):
        import inspect
        for fn in (zones.return_hand_to_deck, zones.reveal_deck_to_hand):
            p = inspect.signature(fn).parameters["identify"]
            self.assertEqual((p.kind, p.default), (inspect.Parameter.KEYWORD_ONLY, False))


if __name__ == "__main__":
    unittest.main()

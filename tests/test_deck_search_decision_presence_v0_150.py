"""v0.150（docs/deck-search-decision-presence-v0.150.md）: 山札をさがす効果の「決定の有無」による情報漏れの修正（両モード共通。PSP-DECK-SEARCH-DECISION-PRESENCE-OTHERS）。

山札にカードがあって選べるカードがないとき、決定を出さずに ``…_none`` で進んでいた経路（ベンチに出す・見せて手札に加える・山札からつける・［うか］）は、決定の有無とログが相手・観戦者に
見え、選べるカードが山札にあるか（なければサイドなどにある）が伝わった。山札にカードがあれば、選べるカードがなくても決定を出す（v0.84 の A3・v0.149 と同じ）。「てよい」の 0 枚の答えは、
選ばなかった・選べるものがなかったを同じ公開のログにし、理由は本人だけが見る。山札が 0 枚・コインの「うら」・控えがいないなど、公開の情報で決まる場合は今までどおり決定を出さない。

盤面の種類を分ける（docs 1 章）:
- 構築盤面（``build_test_state``）: ``board`` の始まり。``new_game`` からの合法な操作の列ではない
- 構築盤面からの合法な操作: ``tickled``（v0.149。相手がくすぐりマシーンを使い、番を終える）・宣言・答えのコマンド
- 双子（テストだけの操作）: ``swap_hidden``（山札とうらのサイド）・``swap_set_aside``（山札と持ち主に見えない置いておくカード）
- 補助関数だけの確かめ: ``required_search_choices``・``empty_search_problems``・``observation`` の見える範囲
"""

from __future__ import annotations

import pathlib
import pickle
import unittest
from dataclasses import dataclass, field

from kyuura_engine import ResolveDecision, UseAttack, UsePokemonPower, apply_command
from kyuura_engine import effects as E
from kyuura_engine import observation as O
from kyuura_engine.cards import load_card_pool
from kyuura_engine.coins import CoinSide
from kyuura_engine.observation import observe, visible_log
from tests import helpers as H
from tests.helpers import with_coin_results
from tests.log_audit import command_outcome, public_view, twin_command_problems
from tests.test_deck_content_prechecks_v0_147 import (
    SETS,
    W,
    mon,
    snapshot,
    state_of,
    swap_hidden,
)
from tests.test_optional_deck_evolution_presence_v0_149 import swap_set_aside, tickled

ROOT = pathlib.Path(__file__).resolve().parent.parent
DOC = ROOT / "docs" / "deck-search-decision-presence-v0.150.md"
DEFS = load_card_pool().definitions
OPPONENT_VIEWS = (1, None)
P = H.POTION  # 山札・サイドの埋め草（ポケモン・エネルギーでないカード）
TYPE_ENERGY = {"grass": H.GRASS, "fire": H.FIRE, "water": H.WATER, "lightning": H.LIGHTNING, "psychic": H.PSYCHIC, "fighting": H.FIGHTING}
HEADS, TAILS = CoinSide.HEADS, CoinSide.TAILS
FC1, RB2 = "UNRESOLVED_STATED_CARDS_SHORT", "UNRESOLVED_RAINBOW_ATTACH_AS_TYPE"


def by_name(name):
    return next(cid for cid, d in DEFS.items() if d.name_ja == name and d.supported and d.category == "pokemon" and d.is_basic_pokemon)


def attacker(card, index):
    """ワザ ``index`` を使える場のポケモン（エネルギーはワザの必要なエネルギーの色。進化ポケモンは下のカードを書く）。"""
    d = DEFS[card]
    chain, cur = [], d
    while cur.is_evolution_pokemon:
        cur = next(x for x in DEFS.values() if x.name_ja == cur.evolves_from and x.supported and x.category == "pokemon")
        chain.insert(0, cur.id)
    kw = {} if not chain else {"evolved_from": chain if len(chain) > 1 else chain[0]}
    return mon(card, [TYPE_ENERGY.get(getattr(c, "value", c), W) for c in d.attacks[index].cost], **kw)


@dataclass(frozen=True)
class Path:
    """対象の経路 1 つ（docs 2 章の表の行）。``optional`` は「てよい」（0 枚の答えが辞退）。``prelude`` は山札をさがす決定の前の答え（ポケモンを選ぶ・手札をもどす）。"""

    name: str
    card: str
    index: int
    target: str
    optional: bool
    kind: str
    filler: str = P
    coin: bool = False
    bench: tuple = ()
    hand: tuple = ()
    prelude: tuple = ()
    shuffles: int = 1
    result: str = ""  # 選んだときの公開のログ
    none: str = ""  # 必ずの経路の、選べるもののない決定の答えのあとのログ
    extra: dict = field(default_factory=dict)


def first_bench(x):
    return (x.decision.options[0],)


def first_hand_card(x):
    return (x.players[0].hand[0],)


PATHS = (
    # BenchFromDeck（bench_from_deck_none の 1 か所の呼び出し元）
    Path("なかまをよぶ（PMCG3-013）", "PMCG3-013", 0, by_name("クラブ"), False, "bench_from_deck", result="bench_from_deck", none="bench_from_deck_none"),
    Path("なかまをよぶ・失敗（neo3-043）", "neo3-043", 0, "neo3-043", False, "bench_from_deck", result="bench_from_deck", none="bench_from_deck_none"),
    Path("いっしょにあそぼ（PF2-007）", "PF2-007", 0, "neo1-042", False, "bench_from_deck", result="bench_from_deck", none="bench_from_deck_none"),
    Path("たすけをよぶ・闘（PMCG2-032）", "PMCG2-032", 1, by_name("イシツブテ"), False, "bench_from_deck", result="bench_from_deck", none="bench_from_deck_none"),
    Path("たすけをよぶ・タケシ（PMCG5-047）", "PMCG5-047", 0, "PMCG5-047", True, "bench_from_deck", coin=True, result="bench_from_deck"),
    # RevealTrainerFromDeck・RevealNamedPokemonFromDeck・RevealPokemonFromDeck・ReturnHandThenRevealEnergy（reveal_from_deck_none の 4 か所）
    Path("おつかい（PMCG5-007）", "PMCG5-007", 1, P, True, "search_deck", filler=W, coin=True, result="reveal_from_deck"),
    Path("ひらめく（SI-014）", "SI-014", 0, P, False, "search_deck", filler=W, coin=True, result="reveal_from_deck", none="reveal_from_deck_none"),
    Path("おつきみ（GD4-012）", "GD4-012", 0, H.GRASS, True, "search_deck", result="reveal_from_deck"),
    Path("くらげのむれ（GD2-003）", "GD2-003", 1, by_name("メノクラゲ"), True, "search_deck", result="reveal_from_deck"),
    Path("りゅうのきずな（neo3-022）", "neo3-022", 1, H.GYARADOS, False, "search_deck", result="reveal_from_deck", none="reveal_from_deck_none"),
    Path("でんれい（PMCG6-067）", "PMCG6-067", 0, by_name("ポッポ"), False, "search_deck", bench=(H.RATTATA,), prelude=(first_bench,),
         result="reveal_from_deck", none="reveal_from_deck_none"),
    Path("てじな（PMCG6-046）", "PMCG6-046", 0, H.GRASS, False, "search_deck", hand=(P,), prelude=(first_hand_card,), result="reveal_from_deck",
         none="reveal_from_deck_none"),
    # AttachFromDeck・AttachFromDeckToBench（attach_energy_from_deck_none の 6 か所のうち 2 つの要素）
    Path("ひなたぼっこ（PMCG4-032）", "PMCG4-032", 0, H.PSYCHIC, True, "attach_from_deck", result="attach_energy_from_deck"),
    Path("じゅうでん（QSG-021）", "QSG-021", 0, H.LIGHTNING, True, "attach_from_deck", result="attach_energy_from_deck"),
    Path("もえあがる（GD5-006）", "GD5-006", 0, H.FIRE, False, "attach_from_deck", result="attach_energy_from_deck", none="attach_energy_from_deck_none"),
    Path("しおまねき（ES3-014）", "ES3-014", 0, H.WATER, False, "attach_from_deck", coin=True, shuffles=0, result="attach_energy_from_deck",
         none="attach_energy_from_deck_none"),
    Path("エナジーサポート（GD6-009）", "GD6-009", 0, H.PSYCHIC, False, "attach_from_deck", bench=(H.RATTATA,), result="attach_to_bench",
         none="attach_energy_from_deck_none"),
    Path("あたためる（neo4-019）", "neo4-019", 0, H.FIRE, False, "attach_from_deck", bench=(H.RATTATA,), prelude=(first_bench,), result="attach_energy_from_deck",
         none="attach_energy_from_deck_none"),
)
# 必ず選ぶ経路の「のぞむなら」でない 0 枚: しおまねきの「最大3枚」の 0 枚は HC7（答えのときに止める）。選べるものがあるときの 0 枚の答えを試さない
ZERO_STOPS = {"しおまねき（ES3-014）"}


def board(path, *, deck=True, conventions=None, prizes=None):
    me = {"active": attacker(path.card, path.index), "deck": ([path.target] if deck else []) + [path.filler] * (5 if deck else 0),
          "prizes": list(prizes if prizes is not None else [path.filler] * 6), "bench": list(path.bench), "hand": list(path.hand)}
    s = state_of(me, conventions=conventions)
    return with_coin_results(s, HEADS) if path.coin else s


def answer(state, choices, player=0):
    return apply_command(state, ResolveDecision(player, state.decision.id, tuple(choices)))


def to_search(state, path):
    """宣言して、山札をさがす決定まで進める（合法なコマンド）。"""
    x = apply_command(state, UseAttack(0, path.index))
    for step in path.prelude:
        x = answer(x, step(x))
    return x


def steps_to_search(path):
    return [UseAttack(0, path.index), *(lambda x, f=f: ResolveDecision(0, x.decision.id, f(x)) for f in path.prelude)]


def opponent_views(state):
    return [public_view(state, viewer) for viewer in OPPONENT_VIEWS]


def new_kinds(before, after, kinds):
    return [e["kind"] for e in after.log[len(before.log):] if e["kind"] in kinds]


class DecisionPresenceTwinTest(unittest.TestCase):
    """選べるカードが山札にある・ない（サイド）だけが違う双子で、山札をさがす決定まで相手・観戦者の観測とログが同じ（3 つの集合・すべての経路）。修正の前の木では、選べるカードが
    ないほうだけ決定が出なかった（``…_none``）。"""

    def test_search_decision_does_not_depend_on_the_deck(self):
        for conventions in SETS:
            for path in PATHS:
                with self.subTest(conventions=conventions, path=path.name):
                    s = board(path, conventions=conventions)
                    twin = swap_hidden(s, path.target)
                    steps = steps_to_search(path)
                    self.assertEqual(twin_command_problems([s, twin], steps, viewers=OPPONENT_VIEWS, owner_knowledge=True, until_public_difference=False), [])
                    asked = [to_search(x, path) for x in (s, twin)]
                    self.assertEqual(opponent_views(asked[0]), opponent_views(asked[1]))
                    for x in asked:
                        self.assertEqual(x.decision.kind, path.kind)
                        for viewer in OPPONENT_VIEWS:
                            self.assertEqual(observe(x, viewer)["decision"], {"kind": path.kind, "player": 0})  # 選べるものの数・空であることも見せない

    def test_hidden_set_aside_twin(self):
        # 山札と、持ち主に見えない置いておくカード（くすぐりマシーン）の双子（代表の 3 つ。構築盤面から合法な操作で置いたあと）
        for conventions in SETS:
            for path in (PATHS[0], PATHS[5], PATHS[12]):
                with self.subTest(conventions=conventions, path=path.name):
                    me = {"active": attacker(path.card, path.index), "deck": [path.filler, path.target] + [path.filler] * 5, "prizes": [path.filler] * 6,
                          "bench": list(path.bench)}
                    s = tickled(me, conventions=conventions, set_aside=(H.FIGHTING, H.FIGHTING))
                    s = with_coin_results(s, HEADS) if path.coin else s
                    twin = swap_set_aside(s, path.target)
                    self.assertEqual(twin_command_problems([s, twin], steps_to_search(path), viewers=OPPONENT_VIEWS, owner_knowledge=True,
                                                           until_public_difference=False), [])

    def test_optional_decline_and_no_target_look_the_same(self):
        # 「てよい」: 0 枚の答えは、選ばなかった（山札にある）・選べるカードがなかった（サイド）のどちらも同じ公開のログ。理由は本人だけ
        for conventions in SETS:
            for path in (p for p in PATHS if p.optional):
                with self.subTest(conventions=conventions, path=path.name):
                    s = board(path, conventions=conventions)
                    twin = swap_hidden(s, path.target)
                    steps = [*steps_to_search(path), lambda x: ResolveDecision(0, x.decision.id, ())]
                    self.assertEqual(twin_command_problems([s, twin], steps, viewers=OPPONENT_VIEWS, owner_knowledge=True, until_public_difference=False), [])
                    done = [answer(to_search(x, path), ()) for x in (s, twin)]
                    self.assertEqual(opponent_views(done[0]), opponent_views(done[1]))
                    own = [[e.get("reason") for e in visible_log(x, 0) if e.get("player") == 0 and str(e.get("reason")) in ("declined", "no_target", "no_candidates")]
                           for x in done]
                    self.assertEqual(own, [["declined"], ["no_candidates" if path.kind == "attach_from_deck" else "no_target"]])

    def test_required_result_is_the_public_outcome(self):
        # 必ず選ぶ経路: 決定の有無・形（相手に見える部分）は分かれない。答えのあとの結果（出した・加えた・つけた／しなかった）は、原文の処理が公開する結果（v0.84 の A3・v0.149 の
        # つきのちから）。ここで分かれるのは修正の対象ではない
        for path in (p for p in PATHS if not p.optional):
            with self.subTest(path=path.name):
                s = board(path)
                asked = [to_search(x, path) for x in (s, swap_hidden(s, path.target))]
                self.assertEqual([(x.decision.min_choices > 0, len(x.decision.options) > 0) for x in asked], [(path.name not in ZERO_STOPS, True), (False, False)])
                self.assertEqual((asked[1].decision.min_choices, asked[1].decision.max_choices), (0, 0))
                found = answer(asked[0], asked[0].decision.options[:1])
                while found.decision is not None and found.decision.player == 0 and found.current_player == 0:
                    found = answer(found, found.decision.options[:1])  # つける控え（エナジーサポート）
                self.assertIn(path.result if path.result != "attach_to_bench" else "attach_energy_from_deck", [e["kind"] for e in visible_log(found, 1)])
                none = answer(asked[1], ())
                self.assertEqual(new_kinds(asked[1], none, (path.none,)), [path.none])


class OwnerAndNormalUseTest(unittest.TestCase):
    """山札をさがし始めたあとは、本人に実際の候補を見せて選ばせる。選んだ結果の公開・配置・付与・山札を切ること（正常な使用）は今までどおり。"""

    def test_owner_sees_the_real_candidates_and_uses_them(self):
        for conventions in SETS:
            for path in PATHS:
                with self.subTest(conventions=conventions, path=path.name):
                    s = board(path, conventions=conventions)
                    asked = to_search(s, path)
                    self.assertEqual([s.cards[u].card_id for u in asked.decision.options], [path.target])
                    self.assertEqual([o["card_id"] for o in observe(asked, 0)["decision"]["options"]], [path.target])
                    done = answer(asked, asked.decision.options[:1])
                    while done.decision is not None and done.decision.player == 0 and done.current_player == 0:
                        done = answer(done, done.decision.options[:1])
                    kinds = [e["kind"] for e in done.log[len(asked.log):]]
                    self.assertIn(path.result if path.result != "attach_to_bench" else "attach_energy_from_deck", kinds)
                    self.assertEqual(sum(1 for e in done.log[len(asked.log):] if e["kind"] == "shuffle" and e["player"] == 0), path.shuffles)
                    self.assertNotIn(path.target, [s.cards[u].card_id for u in done.players[0].deck])

    def test_no_candidate_decision_and_shuffle(self):
        for path in PATHS:
            with self.subTest(path=path.name):
                s = swap_hidden(board(path), path.target)
                asked = to_search(s, path)
                self.assertEqual((asked.decision.kind, asked.decision.options), (path.kind, ()))
                expected = (0, 1) if path.optional and path.name not in ("くらげのむれ（GD2-003）",) else (0, 0)
                self.assertEqual((asked.decision.min_choices, asked.decision.max_choices), expected)
                done = answer(asked, ())
                self.assertEqual(sum(1 for e in done.log[len(asked.log):] if e["kind"] == "shuffle" and e["player"] == 0), path.shuffles)
                self.assertEqual(sorted(s.cards[u].card_id for u in done.players[0].deck), sorted(s.cards[u].card_id for u in asked.players[0].deck))

    def test_optional_decline_with_a_candidate(self):
        for path in (p for p in PATHS if p.optional):
            with self.subTest(path=path.name):
                asked = to_search(board(path), path)
                done = answer(asked, ())
                self.assertIn(path.target, [done.cards[u].card_id for u in done.players[0].deck])
                self.assertEqual(sum(1 for e in done.log[len(asked.log):] if e["kind"] == "shuffle" and e["player"] == 0), path.shuffles)

    def test_empty_deck_has_no_decision(self):
        # 山札が 0 枚（枚数は公開）: さがさないので決定を出さない（今までどおり ``…_none``）。てじな・でんれいは山札にもどすので 0 枚にならない
        for path in PATHS:
            if path.prelude and path.name != "あたためる（neo4-019）":
                continue
            with self.subTest(path=path.name):
                s = board(path, deck=False, prizes=[path.filler])
                done = to_search(s, path) if path.prelude else apply_command(s, UseAttack(0, path.index))
                self.assertTrue(done.decision is None or done.decision.player != 0 or done.current_player != 0)
                kinds = {e["kind"] for e in done.log[len(s.log):]}
                self.assertTrue(kinds & {"bench_from_deck_none", "reveal_from_deck_none", "attach_energy_from_deck_none"}, kinds)

    def test_coin_tails_does_not_search(self):
        # この要素のコインの「うら」: 山札を見ない・切らない（決定もログも出さない）
        for path in (p for p in PATHS if p.coin):
            with self.subTest(path=path.name):
                s = with_coin_results(board(path), TAILS)
                done = apply_command(s, UseAttack(0, path.index))
                self.assertIsNone(done.decision)
                self.assertFalse([e for e in done.log[len(s.log):] if e["kind"] in ("shuffle", path.none or "-", "bench_from_deck_declined", "reveal_from_deck_declined")])

    def test_public_conditions_still_have_no_decision(self):
        # 公開の情報で決まる「さがさない」: 控えがいない（エナジーサポート。今までどおり no_bench で決定なし）
        path = next(p for p in PATHS if p.card == "GD6-009")
        s = state_of({"active": attacker(path.card, path.index), "deck": [path.target] + [P] * 5, "prizes": [P] * 6})
        done = apply_command(s, UseAttack(0, path.index))
        self.assertIsNone(done.decision)
        self.assertEqual([e["reason"] for e in done.log if e["kind"] == "attach_energy_from_deck_none"], ["no_bench"])
        self.assertIn("reason", [k for e in visible_log(done, 1) if e["kind"] == "attach_energy_from_deck_none" for k in e])  # 公開の理由は今までどおり見える

    def test_known_card_outside_the_deck_does_not_change_presence(self):
        # 選べるカードが山札の外の公開の場所（トラッシュ）にあると相手にも分かっているときも、さがす決定は同じように出る（選べるものは空。公開の情報で決まる場合も決定の有無を変えない）。
        # うらのサイドにある盤面と比べて、決定の種類・決めるプレイヤーは同じ（公開の情報はトラッシュの違いだけ）
        for path in (PATHS[0], PATHS[5], PATHS[12]):
            with self.subTest(path=path.name):
                hidden = swap_hidden(board(path), path.target)
                me ={"active": attacker(path.card, path.index), "deck": [path.filler] * 6, "prizes": [path.filler] * 6, "bench": list(path.bench),
                      "hand": list(path.hand), "discard": [path.target]}
                public = state_of(me)
                public = with_coin_results(public, HEADS) if path.coin else public
                asked = [to_search(x, path) for x in (hidden, public)]
                self.assertEqual([(x.decision.kind, x.decision.options) for x in asked], [(path.kind, ())] * 2)
                self.assertEqual([observe(x, 1)["decision"] for x in asked], [{"kind": path.kind, "player": 0}] * 2)


class InvalidAnswerTest(unittest.TestCase):
    """不正な答え（選べないカード・数の違う答え・相手プレイヤーの答え、必ず選ぶ決定の 0 枚）は拒否し、状態・乱数・ログを変えない。相手プレイヤーの答えの拒否は双子で同じ。"""

    def test_invalid_answers_change_nothing(self):
        for path in PATHS:
            with self.subTest(path=path.name):
                s = board(path)
                asked = [to_search(x, path) for x in (s, swap_hidden(s, path.target))]
                stray = next(u for u in asked[0].players[0].discard + asked[0].players[1].deck)
                cases = [(0, (stray,)), (1, ())]
                if not path.optional and path.name not in ZERO_STOPS:
                    cases.append((0, ()))
                for player, choices in cases:
                    for i, x in enumerate(asked):
                        if (player, choices) == (0, ()) and i == 1:
                            continue  # 選べるもののない決定の 0 枚は正しい答え
                        before = snapshot(x)
                        outcome = command_outcome(x, ResolveDecision(player, x.decision.id, choices))[0]
                        self.assertNotEqual(outcome[0], "accepted", (player, choices))
                        self.assertEqual(snapshot(x), before)
                outcomes = [command_outcome(x, ResolveDecision(1, x.decision.id, ()))[0] for x in asked]
                self.assertEqual(outcomes[0], outcomes[1])
                self.assertEqual(command_outcome(asked[1], ResolveDecision(0, asked[1].decision.id, (asked[0].decision.options[0],)))[0][0] != "accepted", True)


class SaveRestoreTest(unittest.TestCase):
    """選べるもののない決定・選べるものがある決定を待つ状態を保存・復元しても、同じ決定・同じ答えの結果（pickle の往復。v0.148・v0.149 と同じ）。"""

    def test_pending_decision_survives_save_and_restore(self):
        for path in PATHS:
            with self.subTest(path=path.name):
                s = board(path)
                for x in (s, swap_hidden(s, path.target)):
                    asked = to_search(x, path)
                    restored = pickle.loads(pickle.dumps(asked))
                    self.assertEqual(restored.decision, asked.decision)
                    self.assertEqual(opponent_views(restored), opponent_views(asked))
                    choices = asked.decision.options[:1] if asked.decision.min_choices or (path.name in ZERO_STOPS and asked.decision.options) else ()
                    self.assertEqual(snapshot(answer(restored, choices)), snapshot(answer(asked, choices)))


class CocoonPowerTest(unittest.TestCase):
    """［うか］（キョウのコクーン。``CoinEvolveSelfFromDeck``。必ず重ねる特殊能力）: 山札にカードがあれば、重ねられるカードがなくても選べるもののない決定（0〜0 枚）。"""

    def cocoon(self, deck=(H.KOGAS_BEEDRILL,) + (W,) * 5, conventions=None):
        return state_of({"active": mon(H.KOGAS_KAKUNA, (H.GRASS,), evolved_from=[H.KOGAS_WEEDLE]), "deck": list(deck), "prizes": [W] * 6}, conventions=conventions)

    def use(self, s):
        return apply_command(s, UsePokemonPower(0, s.players[0].active.pokemon_id, 0))

    def test_twins_and_answers(self):
        for conventions in SETS:
            with self.subTest(conventions=conventions):
                s = with_coin_results(self.cocoon(conventions=conventions), HEADS)
                twin = swap_hidden(s, H.KOGAS_BEEDRILL)
                asked = [self.use(x) for x in (s, twin)]
                self.assertEqual(opponent_views(asked[0]), opponent_views(asked[1]))
                self.assertEqual([(x.decision.min_choices, x.decision.max_choices) for x in asked], [(1, 1), (0, 0)])
                evolved = answer(asked[0], asked[0].decision.options)
                self.assertEqual(evolved.cards[evolved.players[0].active.card].card_id, H.KOGAS_BEEDRILL)  # 公開の結果
                none = answer(asked[1], ())
                self.assertEqual(new_kinds(asked[1], none, ("evolve_from_deck_none", "shuffle")), ["evolve_from_deck_none", "shuffle"])
                for x in asked:
                    before = snapshot(x)
                    self.assertNotEqual(command_outcome(x, ResolveDecision(1, x.decision.id, ()))[0][0], "accepted")
                    self.assertEqual(snapshot(x), before)
                self.assertNotEqual(command_outcome(asked[0], ResolveDecision(0, asked[0].decision.id, ()))[0][0], "accepted")
                restored = pickle.loads(pickle.dumps(asked[1]))
                self.assertEqual(snapshot(answer(restored, ())), snapshot(none))

    def test_empty_deck_and_tails(self):
        s = with_coin_results(self.cocoon(deck=()), HEADS)
        done = self.use(s)
        self.assertIsNone(done.decision)
        self.assertEqual(new_kinds(s, done, ("evolve_from_deck_none",)), ["evolve_from_deck_none"])
        s = with_coin_results(self.cocoon(), TAILS)
        done = self.use(s)
        self.assertIsNone(done.decision)
        self.assertFalse(new_kinds(s, done, ("evolve_from_deck_none", "shuffle", "evolve")))


class AlreadyUniformTest(unittest.TestCase):
    """修正の前から決定の有無が山札の中身によらなかった経路（v0.84 の A3 の形。修正していない）: せいでんき・みんなでおどる。双子で同じことを確かめる。"""

    def test_already_uniform_paths(self):
        for card, index, target, coins in (("neo1-038", 0, H.LIGHTNING, ()), ("neo1-063", 1, H.GRASS, (HEADS,) * 4)):
            with self.subTest(card=card):
                s = state_of({"active": attacker(card, index), "deck": [target] + [P] * 5, "prizes": [P] * 6})
                s = with_coin_results(s, *coins) if coins else s
                self.assertEqual(twin_command_problems([s, swap_hidden(s, target)], [UseAttack(0, index)], viewers=OPPONENT_VIEWS, owner_knowledge=True,
                                                       until_public_difference=False), [])


class BoundaryHelperTest(unittest.TestCase):
    """補助関数だけの確かめ: 選ぶ数・山札 0 枚の決定の確かめ・つけなかった理由の見える範囲。"""

    def test_helpers(self):
        self.assertEqual(E.required_search_choices((5,)), (1, 1))
        self.assertEqual(E.required_search_choices(()), (0, 0))
        self.assertEqual(E.required_search_choices((5, 6), 2), (2, 2))
        path = PATHS[6]
        asked = to_search(swap_hidden(board(path), path.target), path)
        self.assertEqual(E.empty_search_problems(asked, 0, "x", asked.decision), [])
        empty = asked.clone()
        empty.players[0].deck = []
        self.assertTrue(E.empty_search_problems(empty, 0, "x", asked.decision))
        for reason, public in (("declined", False), ("no_candidates", False), ("attach_prevented", True), ("no_bench", True), ("no_heads", True),
                               ("no_target", True), ("no_count", True)):
            event = {"kind": "attach_energy_from_deck_none", "player": 0, "reason": reason}
            self.assertEqual([O._deck_search_reason(event, viewer) for viewer in (0, 1, None)], [True, public, public])
        for kind in ("bench_from_deck_declined", "reveal_from_deck_declined", "attach_energy_from_deck_none"):
            self.assertIn(kind, O.PRIVATE_FIELDS)
            self.assertNotIn(kind, O.PUBLIC_EVENTS)


class HowlMiracleEnergyTwinTest(unittest.TestCase):
    """v0.149 の未確認事項: ［おたけび］（エンテイ。``DiscardDeckTopAttachTypeEnergyThenEndTurn.accept_problem``）のミラクルエネルギーの確かめ（MEC1。v0.149 で候補集合を
    ``searchable_deck_cards`` にした）。山札とうらのサイド・山札と持ち主に見えない置いておくカードの双子で、受理・拒否・コード・理由の文が同じ（3 つの集合。構築盤面から合法な操作で
    置いたあと）。理由の文にミラクルエネルギーの uid を書かない。"""

    def test_miracle_energy_check_does_not_depend_on_the_distribution(self):
        from tests.test_optional_deck_evolution_presence_v0_149 import (
            bench as bench_command,
        )
        from tests.test_optional_deck_evolution_presence_v0_149 import (
            run_steps,
            use_offered,
        )

        for conventions in SETS:
            with self.subTest(conventions=conventions):
                s = tickled({"active": mon(H.CHARMANDER), "deck": [H.ENTEI_NEO3, W, H.MIRACLE_ENERGY] + [W] * 6, "prizes": [W] * 6, "discard": [H.FIRE]},
                            conventions=conventions)
                steps = (bench_command(H.ENTEI_NEO3), use_offered)
                expected = run_steps(s, steps)
                self.assertEqual(expected[-1][:2], ("UnsupportedError", E.MIRACLE_TYPE_CODE))
                miracle = [u for u in (*s.players[0].deck, *s.players[0].prizes) if s.cards[u].card_id == H.MIRACLE_ENERGY]
                self.assertFalse([u for u in miracle if f" {u}" in expected[-1][2] or f"[{u}" in expected[-1][2]])
                for twin in (swap_hidden(s, H.MIRACLE_ENERGY), swap_set_aside(s, H.MIRACLE_ENERGY)):
                    self.assertEqual([public_view(s, v) for v in (0, 1, None)], [public_view(twin, v) for v in (0, 1, None)])  # 前提（持ち主を含む）
                    self.assertEqual(run_steps(twin, steps), expected)


class SeparateStopOracleTest(unittest.TestCase):
    """別件（PSP-DECK-SEARCH-STOP-ORACLES。docs 6 章。直していない）: 山札をさがす前の研究上の停止（RB2・FC1）が実際の山札を読み、山札とサイドの配分で宣言・答えの受理・拒否と
    理由の文（uid・枚数）が変わる。決定の有無の漏れとは別の形（v0.147・v0.148 の使う前の確かめの形）。漏れがないことを確かめるテストを ``expectedFailure`` で置く（漏れを正常な仕様
    として固定しない）。"""

    def assert_same(self, states, steps):
        outcomes = []
        for x in states:
            result = []
            for step in steps:
                command = step(x) if callable(step) else step
                out = command_outcome(x, command)[0]
                result.append(out)
                if out[0] != "accepted":
                    break
                x = apply_command(x, command)
            outcomes.append(result)
        self.assertEqual(outcomes[0], outcomes[1])

    @unittest.expectedFailure
    def test_attach_rainbow_rb2_at_declaration(self):
        # ひなたぼっこ（AttachFromDeck の rainbow_attach_question）: 山札のレインボーエネルギーで宣言を RB2 で拒否（理由の文に uid）。サイドにあれば受理
        s = state_of({"active": attacker("PMCG4-032", 0), "deck": [H.RAINBOW_ENERGY] + [P] * 5, "prizes": [P] * 6})
        self.assert_same([s, swap_hidden(s, H.RAINBOW_ENERGY)], [UseAttack(0, 0)])

    @unittest.expectedFailure
    def test_belly_drum_fc1_at_declaration(self):
        # はらだいこ（AttachBasicEnergyFromDeckToSelf）: 山札の基本エネルギーカードが 1 枚（2 枚を選ぶ）なら宣言の前の先読みが FC1 で拒否。2 枚あれば受理
        s = state_of({"active": attacker("neo2-016", 0), "deck": [H.GRASS, H.GRASS] + [P] * 5, "prizes": [P] * 6})
        self.assert_same([s, swap_hidden(s, H.GRASS)], [UseAttack(0, 0)])

    @unittest.expectedFailure
    def test_trick_fc1_at_return_answer(self):
        # てじな（ReturnHandThenRevealEnergy）: 手札をもどす答え（山札を見る前）が、山札の基本エネルギーカードの枚数で FC1 の拒否（理由の文に枚数。決定は待ったまま）になる
        s = state_of({"active": attacker("PMCG6-046", 0), "deck": [H.GRASS] + [P] * 5, "prizes": [P] * 6, "hand": [P, P]})
        self.assert_same([s, swap_hidden(s, H.GRASS)], [UseAttack(0, 0), lambda x: ResolveDecision(0, x.decision.id, tuple(x.players[0].hand[:2]))])


class DocumentTest(unittest.TestCase):
    def test_document_records_the_fix(self):
        text = DOC.read_text(encoding="utf-8")
        for needle in ("PSP-DECK-SEARCH-DECISION-PRESENCE-OTHERS", "PSP-DECK-SEARCH-STOP-ORACLES", "bench_from_deck_declined", "reveal_from_deck_declined",
                       "attach_energy_from_deck_none", "required_search_choices", "OtherDecisionPresenceNoLeakTest"):
            self.assertIn(needle, text)


if __name__ == "__main__":
    unittest.main()

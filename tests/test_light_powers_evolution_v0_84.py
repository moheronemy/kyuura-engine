"""v0.84（docs/light-powers-evolution-v0.84.md）: v0.83 の不具合 3 件（A1〜A3）の修正と、やさしいポケモン 12 枚・ポケモン育て屋夫婦。

根拠は kyuura データの採用（kyuura ``7d3f4ca`` の data/cards.json の日本語の印刷の文面）と、既存の規定の記録（GR-2000-P321-DAMAGE-ORDER・GR-2000-P310-EVOLUTION・
GR-2000-P322-PERSISTENT-EFFECTS など。docs 各章）。公式ガイドブックの新しい読み直し・カードの画像・pcg-search.com との照合はしていない。
"""

from __future__ import annotations

import copy
import pickle
import unittest

from kyuura_engine import (
    EndTurn,
    EvolvePokemon,
    PlayTrainer,
    ResolveDecision,
    Retreat,
    UseAttack,
    UsePokemonPower,
)
from kyuura_engine.errors import IllegalActionError
from kyuura_engine.observation import observe, visible_log
from kyuura_engine.persistent import reflect_shield
from kyuura_engine.state import ReflectShield, TailsDamageGuard
from tests import helpers as H
from tests.helpers import apply_kernel, with_coin_results
from tests.test_neo_trainer_components_v0_80 import audited, mon, new_events, rejects
from tests.test_shining_gentle_v0_83 import (
    DCE,
    ECO,
    FT,
    HD,
    RE,
    TL,
    F,
    G,
    L,
    P,
    W,
    amounts,
    answer,
    attack,
    board,
    play,
)

FLOOR = "PMCG1-062"  # ラッタ（第1弾。進化しない名前の別のカードとして使わない）


def fingerprint(state):
    from kyuura_engine.serialize import state_to_dict
    return state_to_dict(state, format_version=22)


# ---------------------------------------------------------------- 2 章 A1: 「リフレクトシールド」の「おもて」の 20 を決定をまたいで運ぶ


class ReflectShieldCarryTest(unittest.TestCase):
    """v0.83 では、「おもて」と決まった 20（送る効果）を決定の続きの情報で運ぶと、再開のときに「ダメージを受けたとき」の窓の候補から探し直して見つからず、
    不変条件の違反（``運んだ送る効果 reflect_shield が、ポケモン 1 に 0 つある``）になっていた（kernel.restore_deferred）。"""

    def shielded(self):
        state = board(mon(H.SHINING_MEWTWO, (P, L)), bench=(H.RATTATA,), opponent=mon(H.BLAINES_RHYHORN, (FT, FT, FT)), opponent_bench=(H.RATTATA,))
        return attack(state, 0)  # リフレクトシールド（番が終わる）

    def charged(self):
        # かけぬける: 相手の対戦ポケモン（ひかるミュウツー）に 20 → リフレクトシールドのコイン「おもて」→ かけぬけるのコイン「おもて」→ 控えを選ぶ決定
        shielded = self.shielded()
        return shielded, attack(shielded, 1, (HD, HD))

    def test_heads_return_survives_the_decision(self):
        shielded, waiting = self.charged()
        self.assertEqual(waiting.decision.kind, "select_pokemon")
        self.assertEqual(dict(dict(waiting.decision.context)["frame"])["pending"], ((0, waiting.players[0].active.pokemon_id, "reflect_shield", 0),))
        done = answer(waiting, waiting.decision.options[:1])
        events = [(e["kind"], e.get("amount")) for e in new_events(shielded, done)
                  if e["kind"] in ("reflect_shield_check", "reflect_shield_damage", "damage", "coin_flip")]
        # コインは 2 枚だけ（盾・かけぬける）。盾の 20 は 1 回だけ（サイホーンの弱点は草なので 20）
        self.assertEqual([k for k, _ in events].count("coin_flip"), 2)
        self.assertEqual([k for k, _ in events].count("reflect_shield_damage"), 1)
        self.assertEqual(done.players[1].active.damage, 20)
        self.assertEqual(done.players[0].active.damage, 0)
        self.assertIsNotNone(reflect_shield(waiting, waiting.players[0].active))
        audited(self, done)

    def test_clone_deepcopy_pickle_keep_the_carry(self):
        _shielded, waiting = self.charged()
        expected = fingerprint(answer(waiting, waiting.decision.options[:1]))
        for copied in (waiting.clone(), copy.deepcopy(waiting), pickle.loads(pickle.dumps(waiting))):
            self.assertEqual(fingerprint(answer(copied, copied.decision.options[:1])), expected)
        self.assertEqual(fingerprint(waiting), fingerprint(pickle.loads(pickle.dumps(waiting))))

    def test_tails_has_no_return(self):
        shielded = self.shielded()
        waiting = attack(shielded, 1, (TL, HD))
        done = answer(waiting, waiting.decision.options[:1])
        self.assertEqual(new_events(shielded, done, "reflect_shield_damage"), [])
        self.assertEqual(done.players[0].active.damage, 20)
        audited(self, done)


# ---------------------------------------------------------------- 2 章 A2: 「かげぶんしん」と「リフレクトシールド」が 1 匹に重なる


class ReflectShieldOverlapTest(unittest.TestCase):
    """ピッピの「ゆびをふる」で「かげぶんしん」と「リフレクトシールド」を写し、1 匹に重ねた。v0.83 は先読みの中で RuntimeError（「重なった」）になっていた。"""

    def overlapped(self):
        state = board(mon(H.CLEFAIRY, (W, W, W)), bench=(H.RATTATA,), opponent=mon(H.ROCKETS_SCYTHER, (G, G)),
                      opponent_bench=(H.SHINING_MEWTWO, mon(H.HITMONCHAN, (FT, FT))), opponent_hand=(H.SWITCH, H.SWITCH))
        s = answer(with_coin_results(attack(state, 1), HD), (0,))  # ゆびをふる → かげぶんしん（番が終わる）
        mewtwo = next(p for p in s.players[1].bench if s.cards[p.card].card_id == H.SHINING_MEWTWO)
        s = answer(play(s, H.SWITCH, player=1), (mewtwo.pokemon_id,))
        s = apply_kernel(s, EndTurn(1))
        s = answer(attack(s, 1), (0,))  # ゆびをふる → リフレクトシールド
        hitmonchan = next(p for p in s.players[1].bench if s.cards[p.card].card_id == H.HITMONCHAN)
        return answer(play(s, H.SWITCH, player=1), (hitmonchan.pokemon_id,))

    def test_overlap_stops_before_any_coin(self):
        s = self.overlapped()
        effects = {type(e) for e in s.players[0].active.persistent_effects}
        self.assertTrue({TailsDamageGuard, ReflectShield} <= effects)
        rejects(self, s, UseAttack(1, 0), "UNRESOLVED_REFLECT_SHIELD_OVERLAP")
        for mode in ("derived", "derived_full", "legacy"):
            rejects(self, s, UseAttack(1, 0), "UNRESOLVED_REFLECT_SHIELD_OVERLAP", preflight=mode)

    def test_single_effects_still_work(self):
        # ふつうの側: 「かげぶんしん」だけ・「リフレクトシールド」だけなら、それぞれのコインで処理する
        state = board(mon(H.CLEFAIRY, (W, W, W)), opponent=mon(H.ROCKETS_SCYTHER, (G, G)), opponent_bench=(mon(H.HITMONCHAN, (FT, FT)),),
                      opponent_hand=(H.SWITCH,))
        guarded = answer(with_coin_results(attack(state, 1), HD), (0,))
        hitmonchan = guarded.players[1].bench[0]
        guarded = answer(play(guarded, H.SWITCH, player=1), (hitmonchan.pokemon_id,))
        audited(self, attack(guarded, 0, (TL,)))
        shielded = board(mon(H.SHINING_MEWTWO, (P, L)), opponent=mon(H.HITMONCHAN, (FT, FT)))
        audited(self, attack(attack(shielded, 0), 0, (HD,)))


# ---------------------------------------------------------------- 2 章 A3: みずかきの見えない情報


class FlipperStrokeLeakTest(unittest.TestCase):
    """v0.83 は、見た中に基本エネルギーカードがなければ決定を出さずに次のプレイヤーへ進んでいた。相手には、決定するプレイヤー・ログの並び・切る時点から、山札の上の
    中身が分かっていた。"""

    def golduck(self, own_deck, opponent_deck=None):
        state = board(mon(H.LIGHT_GOLDUCK, (W,), evolved_from="PMCG3-010"), deck=own_deck, opponent_deck=opponent_deck or [W, H.RATTATA, W, W, W])
        return state, attack(state, 0)

    def public_view(self, before, after, viewer):
        events = visible_log(after, viewer)[len(visible_log(before, viewer)):]
        view = observe(after, viewer)
        return [(e["kind"], e.get("player")) for e in events], (view.get("decision") or {}).get("player"), (view.get("decision") or {}).get("kind")

    def test_progress_does_not_depend_on_private_candidates(self):
        a = [H.RATTATA, H.BULBASAUR, H.CHARMANDER, W]  # 上の 3 枚に基本エネルギーカードがない
        b = [W, H.RATTATA, H.BULBASAUR, H.CHARMANDER]  # 1 枚ある
        c = [W, W, H.RATTATA, H.BULBASAUR]  # 2 枚ある
        views = []
        for deck in (a, b, c):
            state, waiting = self.golduck(deck)
            self.assertEqual((waiting.decision.player, waiting.decision.kind), (0, "take_looked_cards"))
            views.append(self.public_view(state, waiting, 1))
            declined = answer(waiting, ())
            self.assertEqual((declined.decision.player, declined.decision.kind), (1, "take_looked_cards"))
            views.append(self.public_view(state, declined, 1))
        self.assertEqual(views[0], views[2])
        self.assertEqual(views[0], views[4])
        self.assertEqual(views[1], views[3])
        self.assertEqual(views[1], views[5])

    def test_opponent_stage_with_and_without_candidates(self):
        for opponent_deck, count in (([H.RATTATA, H.RATTATA, H.RATTATA, W], 0), ([W, H.RATTATA, H.RATTATA, W], 1), ([W, W, H.RATTATA, W], 2)):
            state, waiting = self.golduck([W, W, W, W], opponent_deck)
            mine = answer(waiting, waiting.decision.options[:1])
            self.assertEqual((mine.decision.player, len(mine.decision.options)), (1, count))
            self.assertEqual(observe(mine, 0)["decision"].get("options"), None)  # 相手の選べるものは見えない
            done = answer(mine, ())
            self.assertIsNone(done.decision)
            self.assertEqual(len(new_events(state, done, "shuffle")), 2)
            audited(self, done)
            if count:
                taken = answer(mine, mine.decision.options[:1])
                self.assertEqual(len(new_events(state, taken, "reveal_from_deck")), 2)
                audited(self, taken)

    def test_empty_decision_is_answerable_only_with_nothing(self):
        state, waiting = self.golduck([H.RATTATA, H.BULBASAUR, H.CHARMANDER, W])
        self.assertEqual((waiting.decision.options, waiting.decision.min_choices, waiting.decision.max_choices), ((), 0, 0))
        uid = waiting.players[0].deck[0]
        with self.assertRaises(IllegalActionError):
            apply_kernel(waiting, ResolveDecision(0, waiting.decision.id, (uid,)))
        reasons = [e.get("reason") for e in new_events(state, answer(waiting, ()), "deck_top_take_declined")]
        self.assertEqual(reasons, ["no_target"])  # 理由は見たプレイヤーだけが見る（観測の非公開の項目）




# ---------------------------------------------------------------- 4 章: 入れ替え・守り・場の移動のワザ


class GlitterTouchTest(unittest.TestCase):
    def test_switch_and_new_active_never_gets_conditions(self):
        state = board(mon(H.LIGHT_LEDIAN, (G,), evolved_from=H.LEDYBA_NEO1), bench=(H.RATTATA, H.BULBASAUR), opponent=mon("PMCG1-024", (W,)))
        waiting = attack(state, 0)
        self.assertEqual((waiting.decision.kind, waiting.decision.player), ("select_pokemon", 0))
        target = waiting.players[0].bench[1]
        done = answer(waiting, (target.pokemon_id,))
        self.assertIs(done.players[0].active.pokemon_id, target.pokemon_id)
        self.assertEqual([type(e).__name__ for e in done.players[0].active.persistent_effects], ["StatusImmunityWhileActive"])
        audited(self, done)

    def test_new_active_is_not_poisoned_until_it_leaves(self):
        tentacruel = mon("PMCG3-017", (W, W), evolved_from="PMCG3-011")
        state = board(mon(H.LIGHT_LEDIAN, (G,), evolved_from=H.LEDYBA_NEO1), bench=(mon(H.HITMONCHAN, (FT, FT)),), opponent=tentacruel)
        touched = answer(attack(state, 0), (state.players[0].bench[0].pokemon_id,))
        hit = attack(touched, 1)  # 「クラゲばり」（10 → どく）: ダメージは受け、どくにならない
        self.assertEqual(hit.players[0].active.damage, 10)
        self.assertIsNone(hit.players[0].active.conditions.poison)
        prevented = new_events(touched, hit, "special_condition_prevented")
        self.assertEqual([(e["condition"], e.get("persistent_effect"), e.get("source_card")) for e in prevented],
                         [("poison", "status_immunity_while_active", state.players[0].active.card)])
        audited(self, hit)
        # バトル場をはなれると消える（にげる。理由 retreat）。ベンチの控えに効果は残らない
        hitmonchan = hit.players[0].active
        retreated = apply_kernel(hit, Retreat(0, tuple(hitmonchan.energy), hit.players[0].bench[0].card))
        benched = next(p for p in retreated.players[0].bench if p.pokemon_id == hitmonchan.pokemon_id)
        self.assertEqual(benched.persistent_effects, ())
        self.assertEqual([e["reason"] for e in new_events(hit, retreated, "persistent_effect_removed")], ["retreat"])

    def test_no_bench_fails(self):
        state = board(mon(H.LIGHT_LEDIAN, (G,), evolved_from=H.LEDYBA_NEO1), bench=())
        done = attack(state, 0)
        self.assertEqual([e.get("reason") for e in new_events(state, done, "attack_failed")], ["no_bench"])
        self.assertEqual(done.current_player, 1)


class WelcomeFireTest(unittest.TestCase):
    def test_bench_basic_from_own_discard(self):
        state = board(mon(H.LIGHT_NINETALES, (F,), evolved_from=H.VULPIX_NEO4), bench=(), discard=(H.RATTATA, F, "PMCG1-062"),
                      opponent_discard=(H.BULBASAUR,))
        waiting = attack(state, 0)
        self.assertEqual(waiting.decision.kind, "bench_from_discard")
        own = [u for u in state.players[0].discard if state.cards[u].card_id == H.RATTATA]
        self.assertEqual(waiting.decision.options, tuple(own))  # 進化カード（ラッタ）・エネルギー・相手のトラッシュは選べない
        done = answer(waiting, own)
        self.assertEqual(done.players[0].bench[0].damage, 0)
        self.assertEqual(done.players[0].bench[0].played_turn, done.turn_number - 1)
        audited(self, done)

    def test_full_bench_fails_and_empty_discard_does_nothing(self):
        state = board(mon(H.LIGHT_NINETALES, (F,), evolved_from=H.VULPIX_NEO4), bench=(H.RATTATA,) * 5, discard=(H.RATTATA,))
        done = attack(state, 0)
        self.assertEqual([e.get("reason") for e in new_events(state, done, "attack_failed")], ["bench_full"])
        state = board(mon(H.LIGHT_NINETALES, (F,), evolved_from=H.VULPIX_NEO4), bench=(), discard=(F,))
        done = attack(state, 0)
        self.assertEqual(len(new_events(state, done, "bench_from_discard_none")), 1)


class ReturnToMountainTest(unittest.TestCase):
    def test_return_bench_with_cards_to_deck(self):
        state = board(mon(H.LIGHT_MACHOKE, (FT,), evolved_from=H.MACHOP_NEO4), bench=(mon(H.RATTATA, (W,), damage=20),), deck=[W] * 5)
        waiting = attack(state, 0)
        target = waiting.players[0].bench[0]
        done = answer(waiting, (target.pokemon_id,))
        self.assertEqual(done.players[0].bench, [])
        self.assertEqual(len(done.players[0].deck), 7)
        self.assertEqual(new_events(state, done, "knock_out"), [])
        self.assertEqual(len(new_events(state, done, "shuffle")), 1)
        audited(self, done)

    def test_no_bench_fails(self):
        state = board(mon(H.LIGHT_MACHOKE, (FT,), evolved_from=H.MACHOP_NEO4), bench=())
        done = attack(state, 0)
        self.assertEqual([e.get("reason") for e in new_events(state, done, "attack_failed")], ["no_bench"])


class BubbleJumpTest(unittest.TestCase):
    def azumarill(self, energy, bench=(H.RATTATA,), opponent=None, **extra):
        return board(mon(H.LIGHT_AZUMARILL, energy, evolved_from=H.MARILL_NEO1), bench=bench, opponent=opponent or mon(H.HITMONCHAN), **extra)

    def test_heads_moves_two_cards_and_returns_to_hand(self):
        state = self.azumarill((W, W, DCE))
        waiting = attack(state, 1, (HD,))
        self.assertEqual(waiting.decision.kind, "select_pokemon")
        target = waiting.players[0].bench[0]
        energy = answer(waiting, (target.pokemon_id,))
        self.assertEqual((energy.decision.kind, energy.decision.min_choices, energy.decision.max_choices), ("move_energy", 2, 2))
        cards = energy.decision.options[:2]
        done = answer(energy, cards)
        self.assertEqual(amounts(state, done), [("opponent_active", 30)])
        azumarill = state.players[0].active
        self.assertIn(azumarill.card, done.players[0].hand)
        self.assertIn(azumarill.energy[2], done.players[0].hand)  # はがさなかったカードもいっしょに手札にもどる
        # 空いたバトル場には、ワザのあと、控えから出す（バトル場に出す決定。番でないプレイヤーの決定はない）
        self.assertEqual((done.decision.kind, done.decision.player, done.decision.options), ("promote_active", 0, (target.pokemon_id,)))
        self.assertEqual(list(done.players[0].bench[0].energy), list(cards))
        self.assertEqual(new_events(state, done, "energy_returned_to_hand"), [])  # トラッシュに置かない
        audited(self, done)

    def test_exactly_two_cards_no_energy_decision_and_tails(self):
        state = self.azumarill((W, DCE))
        waiting = attack(state, 1, (HD,))
        target = waiting.players[0].bench[0]
        done = answer(waiting, (target.pokemon_id,))
        self.assertIn(state.players[0].active.card, done.players[0].hand)
        audited(self, done)
        tails = attack(state, 1, (TL,))
        self.assertEqual(tails.players[0].active.card, state.players[0].active.card)

    def test_no_bench_keeps_damage_but_no_coin(self):
        state = self.azumarill((W, W, W), bench=())
        done = attack(state, 1)
        self.assertEqual(amounts(state, done), [("opponent_active", 30)])
        self.assertEqual(new_events(state, done, "coin_flip"), [])

    def test_one_card_left_after_energy_drain_is_fc1(self):
        # 30 ダメージのあとの［だつりょくえき］の「おもて」で 1 枚トラッシュすると、ついているエネルギーカードが 1 枚になる（2 枚をはがせない）。宣言の前に止める
        state = self.azumarill((W, DCE), opponent=mon(H.KOGAS_MUK, (G,), evolved_from=H.KOGAS_GRIMER))
        rejects(self, state, UseAttack(0, 1), "UNRESOLVED_STATED_CARDS_SHORT")

    def test_ko_with_return_is_rd9(self):
        state = self.azumarill((W, DCE), opponent=mon(H.RATTATA))
        rejects(self, state, UseAttack(0, 1), "UNRESOLVED_RETURN_IN_PLAY_TO_DECK_KNOCKOUT")

    def test_copied_by_metronome(self):
        state = board(mon(H.CLEFAIRY, (W, DCE)), bench=(H.RATTATA,), opponent=mon(H.LIGHT_AZUMARILL, (W, W, W), evolved_from=H.MARILL_NEO1))
        waiting = attack(state, 1)
        copied = answer(with_coin_results(waiting, HD), (1,))
        target = copied.players[0].bench[0]
        done = answer(copied, (target.pokemon_id,))
        self.assertIn(state.players[0].active.card, done.players[0].hand)
        audited(self, done)


class CrushStadiumTest(unittest.TestCase):
    def test_optional_discard_stadium(self):
        state = board(mon(H.LIGHT_PILOSWINE, (W, W, W), evolved_from=H.SWINUB_NEO4), hand=(ECO,), opponent=mon(H.HITMONCHAN))
        state = play(state, ECO)
        waiting = attack(state, 0)
        self.assertEqual((waiting.decision.kind, waiting.decision.min_choices), ("discard_stadium", 0))
        kept = answer(waiting, ())
        self.assertIsNotNone(kept.stadium)
        gone = answer(waiting, waiting.decision.options)
        self.assertIsNone(gone.stadium)
        audited(self, gone)
        plain = attack(board(mon(H.LIGHT_PILOSWINE, (W, W, W), evolved_from=H.SWINUB_NEO4), opponent=mon(H.HITMONCHAN)), 0)
        self.assertIsNone(plain.decision)
        # 相手がきぜつしても、のぞむならトラッシュできる（ダメージの結果によらない）
        ko = play(board(mon(H.LIGHT_PILOSWINE, (W, W, W), evolved_from=H.SWINUB_NEO4), hand=(ECO,)), ECO)
        self.assertEqual(attack(ko, 0).decision.kind, "discard_stadium")


class AngelKissTest(unittest.TestCase):
    def test_opponent_decides_draw(self):
        state = board(mon(H.LIGHT_TOGETIC, (W, W), evolved_from=H.TOGEPI_NEO1), opponent=mon(H.HITMONCHAN))
        waiting = attack(state, 0)
        self.assertEqual((waiting.decision.kind, waiting.decision.player, waiting.decision.options), ("select_draw_count", 1, (0, 1)))
        drew = answer(waiting, (1,))
        self.assertEqual(len(new_events(waiting, drew, "draw")), 2)  # 「てんしのキッス」の 1 枚と、相手の番の最初の 1 枚
        self.assertEqual(len(drew.players[1].hand), 2)
        audited(self, drew)
        # 相手の山札が 0 枚なら決定を出さず、引かない（山札の枚数は公開の情報）。負けになるのは、そのあとの相手の番の最初に引けないとき（p.312）
        empty = board(mon(H.LIGHT_TOGETIC, (W, W), evolved_from=H.TOGEPI_NEO1), opponent=mon(H.HITMONCHAN), opponent_deck=[])
        done = attack(empty, 0)
        self.assertEqual([e.get("reason") for e in new_events(empty, done, "attack_draw_declined")], ["empty_deck"])
        self.assertEqual(len([e for e in new_events(empty, done) if e["kind"] == "draw" and e.get("player") == 1]), 0)


class ProtectionTest(unittest.TestCase):
    def test_ice_pillar_guards_bench_not_active(self):
        lanturn = mon(H.LIGHT_LANTURN, (L, L), evolved_from="neo1-037")
        state = board(mon(H.LIGHT_DEWGONG, (W, W, W), evolved_from=H.SEEL_NEO4), bench=(H.RATTATA,), opponent=lanturn)
        guarded = attack(state, 1)
        waiting = attack(guarded, 1)
        bench = waiting.players[0].bench[0]
        done = answer(waiting, (bench.pokemon_id,))
        self.assertEqual(done.players[0].bench[0].damage, 0)
        self.assertEqual(done.players[0].active.damage, 60)  # バトル場のジュゴンは守られない（30 × 弱点 雷）
        self.assertEqual([e.get("persistent_effect") for e in new_events(guarded, done, "damage_prevented")], ["bench_attack_damage_guard"])
        audited(self, done)
        # コインが控えへのダメージだけを決めるワザは、選べるどの控えもダメージを受けないなら、v0.4b の問い（見えない壁と同じ）
        rhyhorn = attack(board(mon(H.LIGHT_DEWGONG, (W, W, W), evolved_from=H.SEEL_NEO4), bench=(H.RATTATA,),
                               opponent=mon(H.BLAINES_RHYHORN, (FT, FT, FT))), 1)
        rejects(self, rhyhorn, UseAttack(1, 1), "UNRESOLVED_PREVENTED_COIN_DAMAGE")
        # バトル場をはなれると消える（突風）
        gust = board(mon(H.LIGHT_DEWGONG, (W, W, W), evolved_from=H.SEEL_NEO4), bench=(H.RATTATA,), opponent=lanturn, opponent_hand=(H.GUST,))
        gusted = attack(gust, 1)
        gusted = answer(play(gusted, H.GUST, player=1), (gusted.players[0].bench[0].pokemon_id,))
        self.assertEqual(gusted.players[0].bench[0].persistent_effects, ())
        hit = answer(attack(gusted, 1), (gusted.players[0].bench[0].pokemon_id,))
        self.assertEqual(hit.players[0].bench[0].damage, 10)

    def test_pulse_guard_threshold(self):
        state = board(mon(H.LIGHT_JOLTEON, (L,), evolved_from="PMCG4-049"), opponent=mon(H.RATTATA, (W,)))
        guarded = attack(state, 0)
        self.assertEqual(attack(guarded, 0).players[0].active.damage, 20)  # 20 は 30 より小さいので受ける
        strong = board(mon(H.LIGHT_JOLTEON, (L,), evolved_from="PMCG4-049"), opponent=mon(H.HITMONCHAN, (FT,)))
        guarded = attack(strong, 0)
        hit = attack(guarded, 0)  # ジャブ 20 × 弱点 闘 = 40（8 段階の時点で 30 以上）
        self.assertEqual(hit.players[0].active.damage, 0)
        audited(self, hit)

    def test_light_pulse_blocks_effects_not_damage(self):
        dragonite = mon(H.LIGHT_DRAGONITE, (W, W, W), evolved_from=[H.DRATINI, H.LIGHT_DRAGONAIR])
        state = board(dragonite, opponent=mon("PMCG3-017", (W, W), evolved_from="PMCG3-011"))
        guarded = attack(state, 0)
        hit = attack(guarded, 1)  # ドククラゲの「クラゲばり」（10 → どく）: ダメージは受け、どくにはならない
        self.assertEqual(hit.players[0].active.damage, 10)
        self.assertIsNone(hit.players[0].active.conditions.poison)
        self.assertEqual([e.get("persistent_effect") for e in new_events(guarded, hit, "effect_prevented")], ["attack_effect_guard"])
        audited(self, hit)
        # 効果だけを決めるコイン（「あわ」の「おもて」でマヒ）は、エフェクトガードと同じく HC3
        azumarill = attack(board(dragonite, opponent=mon(H.LIGHT_AZUMARILL, (W,), evolved_from=H.MARILL_NEO1)), 0)
        rejects(self, azumarill, UseAttack(1, 0), "UNRESOLVED_PREVENTED_EFFECT_COIN")


# ---------------------------------------------------------------- 8 章: 相手で決まるダメージ・コインのワザ


class DamageValueTest(unittest.TestCase):
    def test_gentle_flame_by_stage(self):
        arcanine = mon(H.LIGHT_ARCANINE, (F, F, W), evolved_from=H.GROWLITHE_NEO4)
        basic = board(arcanine, opponent=mon(H.HITMONCHAN))
        self.assertEqual(amounts(basic, attack(basic, 0)), [("opponent_active", 30)])
        stage1 = board(arcanine, opponent=mon(H.LIGHT_PILOSWINE, (), evolved_from=H.SWINUB_NEO4))
        self.assertEqual(amounts(stage1, attack(stage1, 0)), [("opponent_active", 50)])

    def test_gentle_kick_by_counters(self):
        machoke = mon(H.LIGHT_MACHOKE, (FT, FT), evolved_from=H.MACHOP_NEO4)
        clean = board(machoke, opponent=mon(H.HITMONCHAN))
        self.assertEqual(amounts(clean, attack(clean, 1)), [("opponent_active", 40)])
        hurt = board(machoke, opponent=mon(H.HITMONCHAN, damage=10))
        self.assertEqual(amounts(hurt, attack(hurt, 1)), [("opponent_active", 20)])

    def test_seiken_coin_only_against_dark(self):
        machamp = mon(H.LIGHT_MACHAMP, (FT, FT, FT), evolved_from=[H.MACHOP_NEO4, H.LIGHT_MACHOKE])
        plain = board(machamp, opponent=mon(H.HITMONCHAN))
        done = attack(plain, 0)
        self.assertEqual((amounts(plain, done), new_events(plain, done, "coin_flip")), ([("opponent_active", 50)], []))
        dark = board(machamp, opponent=mon(H.DARK_MUK, (), evolved_from=H.GRIMER), opponent_bench=(H.RATTATA,))
        heads = attack(dark, 0, (HD,))
        self.assertEqual((amounts(dark, heads), len(new_events(dark, heads, "coin_flip"))), ([("opponent_active", 100)], 1))
        tails = attack(dark, 0, (TL,))
        self.assertEqual(amounts(dark, tails), [("opponent_active", 50)])
        # 「悪」ポケモン（タイプ）も同じ（デルビル neo1-089 は悪）
        houndour = board(machamp, opponent=mon(H.HOUNDOUR_NEO2), opponent_bench=(H.RATTATA,))
        self.assertEqual(len(new_events(houndour, attack(houndour, 0, (TL,)), "coin_flip")), 1)

    def test_thunder_needle_one_coin_set(self):
        jolteon = mon(H.LIGHT_JOLTEON, (L, L, W), evolved_from="PMCG4-049")
        state = board(jolteon, opponent=mon(H.HITMONCHAN))
        two = attack(state, 1, (HD, HD, TL))
        self.assertEqual(amounts(state, two), [("opponent_active", 40)])
        self.assertIsNotNone(two.players[1].active.conditions.paralyzed)
        self.assertEqual(len(new_events(state, two, "coin_flip")), 3)
        one = attack(state, 1, (HD, TL, TL))
        self.assertEqual(amounts(state, one), [("opponent_active", 20)])
        self.assertIsNone(one.players[1].active.conditions.exclusive)
        audited(self, two)

    def test_freezing_breath_one_coin(self):
        dewgong = mon(H.LIGHT_DEWGONG, (W, W), evolved_from=H.SEEL_NEO4)
        state = board(dewgong, opponent=mon(H.HITMONCHAN))
        self.assertIsNotNone(attack(state, 0, (HD,)).players[1].active.conditions.paralyzed)
        self.assertIsNotNone(attack(state, 0, (TL,)).players[1].active.conditions.asleep)


# ---------------------------------------------------------------- 5 章: 特殊能力


class DriveOffTest(unittest.TestCase):
    def arcanine(self, **extra):
        return board(mon(H.LIGHT_ARCANINE, (F,), evolved_from=H.GROWLITHE_NEO4), opponent=mon(H.HITMONCHAN),
                     opponent_bench=extra.pop("opponent_bench", (H.RATTATA, H.BULBASAUR)), **extra)

    def test_opponent_chooses(self):
        state = self.arcanine()
        pid = state.players[0].active.pokemon_id
        waiting = apply_kernel(state, UsePokemonPower(0, pid))
        self.assertEqual((waiting.decision.kind, waiting.decision.player), ("select_pokemon", 1))
        chosen = waiting.players[1].bench[1]
        done = answer(waiting, (chosen.pokemon_id,))
        self.assertIs(done.players[1].active.pokemon_id, chosen.pokemon_id)
        self.assertEqual(new_events(state, done, "coin_flip"), [])
        self.assertEqual(done.current_player, 0)  # 番は続く
        rejects(self, done, UsePokemonPower(0, pid), "POWER_ALREADY_USED", IllegalActionError)
        audited(self, done)

    def test_rejections(self):
        state = self.arcanine(opponent_bench=())
        pid = state.players[0].active.pokemon_id
        rejects(self, state, UsePokemonPower(0, pid), "NO_OPPONENT_BENCH", IllegalActionError)
        asleep = board(mon(H.LIGHT_ARCANINE, (F,), evolved_from=H.GROWLITHE_NEO4, sleep=True), opponent=mon(H.HITMONCHAN))
        rejects(self, asleep, UsePokemonPower(0, asleep.players[0].active.pokemon_id), "POKEMON_ASLEEP", IllegalActionError)
        bench = board(mon(H.HITMONCHAN), bench=(mon(H.LIGHT_ARCANINE, (F,), evolved_from=H.GROWLITHE_NEO4),), opponent=mon(H.HITMONCHAN))
        rejects(self, bench, UsePokemonPower(0, bench.players[0].bench[0].pokemon_id), "POKEMON_NOT_ACTIVE", IllegalActionError)


class FluffyWoolTest(unittest.TestCase):
    def piloswine(self, **extra):
        return board(mon(H.LIGHT_PILOSWINE, (W,), evolved_from=H.SWINUB_NEO4, **extra), opponent=mon(H.HITMONCHAN, (FT,)), current=1, turn=8)

    def test_heads_puts_attacker_to_sleep(self):
        state = self.piloswine()
        done = attack(state, 0, (HD,))
        self.assertIsNotNone(done.players[1].active.conditions.asleep)
        self.assertEqual([e["asleep"] for e in new_events(state, done, "power_sleep")], [True])
        audited(self, done)
        tails = attack(state, 0, (TL,))
        self.assertIsNone(tails.players[1].active.conditions.exclusive)

    def test_not_working_when_already_confused_or_on_bench(self):
        confused = self.piloswine(confusion=True)
        done = attack(confused, 0)
        self.assertEqual(new_events(confused, done, "power_sleep"), [])
        own_turn = board(mon(H.LIGHT_PILOSWINE, (W, W, W), evolved_from=H.SWINUB_NEO4), opponent=mon(H.HITMONCHAN))
        self.assertEqual(new_events(own_turn, attack(own_turn, 0), "power_sleep"), [])

    def test_works_even_if_knocked_out(self):
        state = board(mon(H.LIGHT_PILOSWINE, (W,), evolved_from=H.SWINUB_NEO4, damage=80), bench=(H.RATTATA,), opponent=mon(H.HITMONCHAN, (FT,)), current=1, turn=8)
        done = attack(state, 0, (HD,))
        self.assertEqual([e["asleep"] for e in new_events(state, done, "power_sleep")], [True])


def evolve(state, card_id, target, player=0):
    uid = next(u for u in state.players[player].hand if state.cards[u].card_id == card_id)
    return apply_kernel(state, EvolvePokemon(player, uid, target))


class TagTeamTest(unittest.TestCase):
    def machoke_on_bench(self, **extra):
        machoke = mon(H.LIGHT_MACHOKE, (FT,), evolved_from=H.MACHOP_NEO4, played_turn=1, evolved_turn=3)
        return board(mon(H.HITMONCHAN, (FT,), damage=50), bench=(machoke,), hand=(H.LIGHT_MACHAMP,), opponent=mon(H.HITMONCHAN), **extra)

    def test_bench_evolution_offers_and_heals_then_switches(self):
        state = self.machoke_on_bench()
        machoke = state.players[0].bench[0]
        offered = evolve(state, H.LIGHT_MACHAMP, machoke.pokemon_id)
        d = offered.decision
        self.assertEqual((d.kind, d.player, d.options, d.context_value("entry"), d.context_value("entry_zone")), ("entry_power", 0, (machoke.pokemon_id,), "hand", "bench"))
        used = answer(offered, (machoke.pokemon_id,))
        self.assertIs(used.players[0].active.pokemon_id, machoke.pokemon_id)
        hitmonchan = used.players[0].bench[0]
        self.assertEqual(hitmonchan.damage, 20)  # 50 から 3 個とりのぞく
        self.assertEqual([e["counters"] for e in new_events(state, used, "tag_team_heal")], [3])
        audited(self, used)
        declined = answer(offered, ())
        self.assertEqual(declined.players[0].active.damage, 50)
        # 機会が過ぎたあとに MAIN から使えない
        rejects(self, declined, UsePokemonPower(0, machoke.pokemon_id), "POWER_NOT_USABLE_NOW", IllegalActionError)

    def test_fewer_counters_and_no_damage(self):
        state = board(mon(H.HITMONCHAN, (FT,), damage=10), bench=(mon(H.LIGHT_MACHOKE, (FT,), evolved_from=H.MACHOP_NEO4, played_turn=1, evolved_turn=3),),
                      hand=(H.LIGHT_MACHAMP,), opponent=mon(H.HITMONCHAN))
        used = answer(evolve(state, H.LIGHT_MACHAMP, state.players[0].bench[0].pokemon_id), (state.players[0].bench[0].pokemon_id,))
        self.assertEqual(used.players[0].bench[0].damage, 0)
        clean = board(mon(H.HITMONCHAN, (FT,)), bench=(mon(H.LIGHT_MACHOKE, (FT,), evolved_from=H.MACHOP_NEO4, played_turn=1, evolved_turn=3),),
                      hand=(H.LIGHT_MACHAMP,), opponent=mon(H.HITMONCHAN))
        used = answer(evolve(clean, H.LIGHT_MACHAMP, clean.players[0].bench[0].pokemon_id), (clean.players[0].bench[0].pokemon_id,))
        self.assertEqual([e["counters"] for e in new_events(clean, used, "tag_team_heal")], [0])
        self.assertIs(used.players[0].active.pokemon_id, clean.players[0].bench[0].pokemon_id)

    def test_active_evolution_has_no_opportunity(self):
        state = board(mon(H.LIGHT_MACHOKE, (FT,), evolved_from=H.MACHOP_NEO4, played_turn=1, evolved_turn=3), hand=(H.LIGHT_MACHAMP,),
                      opponent=mon(H.HITMONCHAN))
        done = evolve(state, H.LIGHT_MACHAMP, state.players[0].active.pokemon_id)
        self.assertIsNone(done.decision)

    def test_breeder_from_hand_on_bench(self):
        machop = mon(H.MACHOP_NEO4, (FT,), played_turn=1)
        state = board(mon(H.HITMONCHAN, (FT,), damage=30), bench=(machop,), hand=(H.POKEMON_BREEDER, H.LIGHT_MACHAMP), opponent=mon(H.HITMONCHAN))
        played = play(state, H.POKEMON_BREEDER)
        pid = state.players[0].bench[0].pokemon_id
        card = answer(played, (pid,))
        offered = answer(card, card.decision.options)
        self.assertEqual((offered.decision.kind, offered.decision.context_value("entry_zone")), ("entry_power", "bench"))
        used = answer(offered, (pid,))
        self.assertIs(used.players[0].active.pokemon_id, pid)
        audited(self, used)


class GiftTest(unittest.TestCase):
    def togepi(self, deck=None, opponent_deck=None):
        togepi = mon(H.TOGEPI_NEO1, (W,), played_turn=1)
        return board(togepi, hand=(H.LIGHT_TOGETIC,), opponent=mon(H.HITMONCHAN), deck=deck, opponent_deck=opponent_deck)

    def test_each_player_may_search_a_tool(self):
        berry = "neo1-073"
        state = self.togepi(deck=[W, berry, W], opponent_deck=[W, W, W])
        offered = evolve(state, H.LIGHT_TOGETIC, state.players[0].active.pokemon_id)
        look = answer(offered, offered.decision.options)
        self.assertEqual((look.decision.kind, look.decision.player), ("accept_request", 0))
        take = answer(look, (1,))
        self.assertEqual((take.decision.kind, take.decision.player, take.decision.max_choices), ("search_deck", 0, 1))
        theirs = answer(take, take.decision.options)
        self.assertEqual((theirs.decision.kind, theirs.decision.player), ("accept_request", 1))
        # 相手は見る（どうぐはない）: 選べるもののない決定で答えを待つ
        empty = answer(theirs, (1,))
        self.assertEqual((empty.decision.kind, empty.decision.player, empty.decision.options), ("search_deck", 1, ()))
        done = answer(empty, ())
        self.assertEqual([e["player"] for e in new_events(state, done, "shuffle")], [0, 1])
        self.assertEqual([e["card"] for e in new_events(state, done, "reveal_from_deck")], [state.players[0].deck[1]])
        audited(self, done)

    def test_not_looking_does_not_shuffle_and_hides_counts(self):
        state = self.togepi(opponent_deck=["neo1-073", W, W])
        offered = evolve(state, H.LIGHT_TOGETIC, state.players[0].active.pokemon_id)
        mine = answer(answer(offered, offered.decision.options), ())
        self.assertNotIn("options", observe(answer(mine, (1,)), 0)["decision"])
        done = answer(answer(mine, (1,)), ())
        self.assertEqual([e["player"] for e in new_events(state, done, "shuffle")], [1])


class EvolutionSongTest(unittest.TestCase):
    def wigglytuff(self, **extra):
        return board(mon(H.LIGHT_WIGGLYTUFF, (W,), evolved_from=H.JIGGLYPUFF_NEO4), bench=(mon(H.MACHOP_NEO4, played_turn=1),),
                     opponent=mon(H.TOGEPI_NEO1, played_turn=1), **extra)

    def test_each_player_evolves_own_pokemon(self):
        state = self.wigglytuff(deck=[W, H.LIGHT_MACHOKE, W], opponent_deck=[W, H.LIGHT_TOGETIC, W])
        mine = attack(state, 0)
        self.assertEqual((mine.decision.kind, mine.decision.player, mine.decision.min_choices), ("evolution_song_pokemon", 0, 0))
        machop = state.players[0].bench[0].pokemon_id
        card = answer(mine, (machop,))
        self.assertEqual((card.decision.kind, card.decision.options), ("search_deck", (state.players[0].deck[1],)))
        theirs = answer(card, card.decision.options)
        self.assertEqual(theirs.players[0].bench[0].card, state.players[0].deck[1])
        self.assertEqual((theirs.decision.kind, theirs.decision.player), ("evolution_song_pokemon", 1))
        togepi = state.players[1].active.pokemon_id
        their_card = answer(theirs, (togepi,))
        done = answer(their_card, their_card.decision.options)
        self.assertEqual(state.cards[done.players[1].active.card].card_id, H.LIGHT_TOGETIC)
        self.assertIsNone(new_events(state, done, "entry_power_declined") or None)  # 山札から重ねたので［おくりもの］の機会はない
        self.assertEqual([e["player"] for e in new_events(state, done, "shuffle")], [0, 1])
        audited(self, done)

    def test_decline_does_not_look(self):
        state = self.wigglytuff()
        done = answer(answer(attack(state, 0), ()), ())
        self.assertEqual(new_events(state, done, "shuffle"), [])

    def test_no_card_still_waits(self):
        state = self.wigglytuff(deck=[W, W, W])
        card = answer(attack(state, 0), (state.players[0].bench[0].pokemon_id,))
        self.assertEqual((card.decision.kind, card.decision.options, card.decision.max_choices), ("search_deck", (), 0))
        self.assertNotIn("options", observe(card, 1)["decision"])

    def test_attacker_evolves_itself_then_opponent_decides(self):
        # やさしいプクリンから進化するカードはない（2 進化はない）ので、ワザを使ったポケモンが進化するのは、たねポケモンのワザとして使う場合（ゆびをふる）
        clefairy = mon(H.CLEFAIRY, (W, W, W), played_turn=1)
        state = board(clefairy, deck=[W, "PMCG2-044", W], opponent=mon(H.LIGHT_WIGGLYTUFF, (W,), evolved_from=H.JIGGLYPUFF_NEO4))
        song = answer(attack(state, 1), (0,))
        card = answer(song, (state.players[0].active.pokemon_id,))
        theirs = answer(card, card.decision.options)
        self.assertEqual(state.cards[theirs.players[0].active.card].card_id, "PMCG2-044")
        self.assertEqual((theirs.decision.kind, theirs.decision.player), ("evolution_song_pokemon", 1))
        done = answer(theirs, ())
        audited(self, done)


class BreederCoupleTest(unittest.TestCase):
    def two_machop(self, deck):
        return board(mon(H.MACHOP_NEO4, (FT,), played_turn=1), bench=(mon(H.MACHOP_NEO4, played_turn=1),), hand=(H.BREEDER_COUPLE,),
                     opponent=mon(H.HITMONCHAN), deck=deck)

    def test_each_heads_takes_a_distinct_card_then_shuffles(self):
        state = self.two_machop([W, H.LIGHT_MACHOKE, W, H.LIGHT_MACHOKE])
        chosen = play(state, H.BREEDER_COUPLE)
        self.assertEqual((chosen.decision.kind, chosen.decision.max_choices), ("select_pokemon", 2))
        coined = answer(with_coin_results(chosen, HD, HD), [p.pokemon_id for p in state.players[0].in_play()])
        first = coined.decision
        self.assertEqual(first.options, (state.players[0].deck[1], state.players[0].deck[3]))
        second = answer(coined, (state.players[0].deck[1],))
        self.assertEqual(second.decision.options, (state.players[0].deck[3],))
        done = answer(second, second.decision.options)
        self.assertEqual(len([u for u in done.players[0].hand if done.cards[u].card_id == H.LIGHT_MACHOKE]), 2)
        self.assertEqual([e["player"] for e in new_events(state, done, "shuffle")], [0])
        self.assertEqual(len(new_events(state, done, "reveal_from_deck")), 2)
        audited(self, done)

    def test_same_uid_is_never_taken_twice(self):
        state = self.two_machop([W, H.LIGHT_MACHOKE, W])
        coined = answer(with_coin_results(play(state, H.BREEDER_COUPLE), HD, HD), [p.pokemon_id for p in state.players[0].in_play()])
        second = answer(coined, coined.decision.options)
        self.assertEqual((second.decision.options, second.decision.max_choices), ((), 0))
        self.assertNotIn("options", observe(second, 1)["decision"])
        done = answer(second, ())
        self.assertEqual(len(new_events(state, done, "shuffle")), 1)

    def test_tails_still_shuffles_and_zero_and_no_target_stop(self):
        state = self.two_machop([W, H.LIGHT_MACHOKE, W])
        done = answer(with_coin_results(play(state, H.BREEDER_COUPLE), TL), (state.players[0].active.pokemon_id,))
        self.assertIsNone(done.decision)
        self.assertEqual(len(new_events(state, done, "shuffle")), 1)
        rejects(self, play(state, H.BREEDER_COUPLE), ResolveDecision(0, play(state, H.BREEDER_COUPLE).decision.id, ()), "UNRESOLVED_TRAINER_UP_TO_ZERO_CHOICE")
        stage2 = board(mon(H.LIGHT_MACHAMP, (FT,), evolved_from=[H.MACHOP_NEO4, H.LIGHT_MACHOKE]), bench=(), hand=(H.BREEDER_COUPLE,), opponent=mon(H.HITMONCHAN))
        uid = stage2.players[0].hand[0]
        rejects(self, stage2, PlayTrainer(0, uid), "UNRESOLVED_TRAINER_UP_TO_WITHOUT_TARGET")


class MiraculousWindTest(unittest.TestCase):
    def dragonite(self, **kw):
        return mon(H.LIGHT_DRAGONITE, kw.pop("energy", ()), evolved_from=[H.DRATINI, H.LIGHT_DRAGONAIR], **kw)

    def test_double_colorless_counts_one_colorless(self):
        state = board(self.dragonite(energy=(DCE, W)), opponent=mon(H.HITMONCHAN))
        rejects(self, state, UseAttack(0, 0), "INSUFFICIENT_ENERGY", IllegalActionError)
        asleep = board(self.dragonite(energy=(DCE, W), sleep=True), opponent=mon(H.HITMONCHAN))
        self.assertIsNotNone(asleep)  # ねむりの間は力が消える（宣言はねむりで拒否されるので、支払いは単体の問い合わせで見る）
        from kyuura_engine.effects import attack_cost_payable, special_energy_effect
        pokemon = asleep.players[0].active
        self.assertTrue(attack_cost_payable(asleep, pokemon, asleep.card_def(pokemon.card).attacks[0]))
        dce = state.players[0].active.energy[0]
        self.assertEqual(special_energy_effect(state, dce).__class__.__name__, "WindNeutralizedEnergy")

    def test_darkness_bonus_and_recycle_return_are_gone(self):
        dark = board(self.dragonite(energy=(W, W, H.DARKNESS_ENERGY_NEO1)), opponent=mon(H.HITMONCHAN))
        self.assertEqual(amounts(dark, attack(dark, 0)), [("opponent_active", 40)])
        calm = board(self.dragonite(energy=(W, W, H.DARKNESS_ENERGY_NEO1), confusion=True), opponent=mon(H.HITMONCHAN))
        self.assertEqual(amounts(calm, attack(calm, 0, coins=(HD,))), [("opponent_active", 50)])
        recycle = board(mon(H.HITMONCHAN, (RE, RE)), opponent=self.dragonite())
        energy = recycle.players[0].active.energy
        retreated = apply_kernel(recycle, Retreat(0, tuple(energy), recycle.players[0].bench[0].card))
        self.assertEqual(new_events(recycle, retreated, "energy_returned_to_hand"), [])
        self.assertTrue(set(energy) <= set(retreated.players[0].discard))
        audited(self, retreated)

    def test_buzzap_under_wind_stops_before_declaring(self):
        from tests.test_energy_control_power_suppression_v0_59 import electrode
        state = board(mon(H.HITMONCHAN, (FT,)), bench=(electrode(),), opponent=self.dragonite())
        rejects(self, state, UsePokemonPower(0, state.players[0].bench[0].pokemon_id, 0), "UNRESOLVED_MIRACULOUS_WIND_CONVERTED_ENERGY")

    def test_energy_burn_on_special_energy_under_wind_is_wd2(self):
        """エナジーバーンで特殊エネルギーカードを「炎」にする状態は、かぜの場で決まらない（WD2）。そうなる宣言は受け付けない。かぜがなければ使える。"""
        charizard = mon("PMCG1-021", (DCE, F), evolved_from=[H.CHARMANDER, "PMCG1-017"])
        state = board(self.dragonite(), bench=(charizard,), opponent=mon(H.HITMONCHAN))
        pid = state.players[0].bench[0].pokemon_id
        rejects(self, state, UsePokemonPower(0, pid, 0), "UNRESOLVED_MIRACULOUS_WIND_ENERGY_BURN")
        calm = board(self.dragonite(sleep=True), bench=(charizard,), opponent=mon(H.HITMONCHAN))
        used = apply_kernel(calm, UsePokemonPower(0, calm.players[0].bench[0].pokemon_id, 0))
        audited(self, used)

    def test_wind_returning_in_pokemon_check_halts_before_the_coin(self):
        """ねむりのやさしいカイリューの場（かぜは消えている）で［エネエネ］を使い、ポケモンチェックでカイリューが回復すると WD1 の状態になる。ねむりのコインの
        結果によらず、コインの前に対戦を止める（v0.48 の MH1 と同じ、ポケモンチェックの決められない状態の確かめ）。"""
        from tests.test_energy_control_power_suppression_v0_59 import electrode
        state = board(self.dragonite(sleep=True), bench=(electrode(), H.RATTATA), opponent=mon(H.HITMONCHAN))
        declared = apply_kernel(state, UsePokemonPower(0, state.players[0].bench[0].pokemon_id, 0))
        converted = answer(answer(declared, (state.players[0].active.pokemon_id,)), (5,))
        while converted.decision is not None:
            converted = answer(converted, converted.decision.options[:1])
        for coin in (HD, TL):
            halted = apply_kernel(with_coin_results(converted, coin), EndTurn(0))
            self.assertEqual((halted.phase.name, halted.halt.code), ("HALTED", "UNRESOLVED_MIRACULOUS_WIND_CONVERTED_ENERGY"))


class RegistryTest(unittest.TestCase):
    def test_counts_and_unsupported_without_the_v0_84_registrations(self):
        """v0.84 の登録（ワザ 19・特殊能力 5・トレーナー 1）を除くと、13 枚とも未対応にもどり、対応するカードは v0.83 の 1,026 枚（docs 1 章）。"""
        from kyuura_engine import effects as E
        from kyuura_engine.cards import load_card_pool, pool_from_extract, read_extract
        extract = read_extract()
        self.assertEqual(tuple(extract["pool_v0_84"]), H.V0_84_CARDS)
        self.assertEqual((len(E.V0_84_ATTACKS), len(E.V0_84_POWERS), len(E.V0_84_TRAINERS)), (19, 5, 1))
        pool = load_card_pool()
        categories = [pool.get(c).category for c in pool.playable_ids]
        self.assertEqual((len(categories), categories.count("pokemon"), categories.count("trainer"), categories.count("energy")), (1091, 794, 260, 37))  # v0.88 でポケモン 11 枚（ワザ 15・特殊能力 5）を加えた  # v0.87 でポケモン 14 枚（ワザ 14・特殊能力 14）を加えた  # v0.86 でポケモン 13 枚を加えた
        reg = E.DEFAULT_EFFECTS
        self.assertEqual((len(reg.attack_keys()), len(reg.power_keys()), len(reg.trainer_ids()), len(reg.energy_ids())), (1327, 119, 260, 19))  # v0.88 でポケモン 11 枚（ワザ 15・特殊能力 5）を加えた  # v0.87 でポケモン 14 枚（ワザ 14・特殊能力 14）を加えた  # v0.86 でワザ 14・特殊能力 12 を加えた
        stripped = reg.without_attacks("without-v0.84-attacks", list(E.V0_84_ATTACKS))
        stripped = stripped.without_powers("without-v0.84-powers", list(E.V0_84_POWERS))
        stripped = stripped.without_trainers("without-v0.84", list(E.V0_84_TRAINERS))
        before = pool_from_extract(extract, stripped)
        self.assertFalse(before.playable_ids & set(H.V0_84_CARDS))
        self.assertEqual(len(before.playable_ids), 1026 + len(extract["pool_v0_85"]) + len(extract["pool_v0_86"]) + len(extract["pool_v0_87"]) + len(extract["pool_v0_88"]))  # v0.88 の 11 枚も対応  # v0.85 から、あとの版の 14 枚（pool_v0_85）も対応。v0.86 の 13 枚（pool_v0_86）も
        self.assertEqual(pool.playable_ids - before.playable_ids, frozenset(H.V0_84_CARDS))
        # 未対応（kyuura data/engine_targets.json（7d3f4ca）の対象 1,377 件から今の登録を差し引く）。../kyuura がなければ確かめない
        import json
        import pathlib
        import subprocess
        kyuura = pathlib.Path(__file__).resolve().parent.parent.parent / "kyuura"
        if (kyuura / ".git").exists():
            targets = json.loads(subprocess.check_output(["git", "-C", str(kyuura), "show", f"{extract['source']['commit']}:data/engine_targets.json"]))
            missing = [c for c in targets["cards"] if c["id"] not in pool.playable_ids]
            self.assertEqual((len(targets["cards"]), len(missing), sum(1 for c in missing if c["id"].startswith("neo")),
                              sum(1 for c in missing if c["product_group"] != "expansion_pack")), (1377, 286, 132, 154))  # v0.88 でポケモン 11 枚（ワザ 15・特殊能力 5）を加えた  # v0.87 でポケモン 14 枚（ワザ 14・特殊能力 14）を加えた  # v0.86 でポケモン 13 枚を加えた  # v0.85 でポケモン 13 枚・ミラクルエネルギーを加えた

    def test_new_events_and_decisions_are_classified(self):
        from kyuura_engine.observation import (
            OPTION_MEANINGS,
            PRIVATE_FIELDS,
            PUBLIC_EVENTS,
        )
        for kind in ("power_sleep", "power_sleep_skipped", "tag_team_heal", "gift_declined", "breeder_couple_coins", "stadium_discard_declined"):
            self.assertIn(kind, PUBLIC_EVENTS)
        self.assertIn("gift_take_none", PRIVATE_FIELDS)
        self.assertEqual((OPTION_MEANINGS["discard_stadium"], OPTION_MEANINGS["evolution_song_pokemon"]), ("card", "pokemon"))


if __name__ == "__main__":
    unittest.main()

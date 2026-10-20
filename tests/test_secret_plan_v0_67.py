"""v0.67: マチスの秘策（PMCG5-093）とうらのカード、先読みのフォールバックの修正（docs/secret-plan-preflight-v0.67.md）。

根拠は kyuura データの採用（kyuura の印刷の文面。kyuura_engine/data/card_sources.json の PMCG5-093）と、既存の記録の再利用（「効果の対象として指定されないかぎり、
裏のままでOK」は p.277 のかがくへんかガスの解説の記録。全体に働く効果でおもてにしないことだけを読み、ほかの処理に広げない）。誌面を読み直していない。決められない場合は
FD1（うらのあいだに決まらない項目を読む処理）・FD2（ロケット団の爆発ジム）で止める（kyuura の未解決の一覧にない）。
"""

from __future__ import annotations

import unittest
from unittest import mock

from kyuura_engine import (
    AttachEnergy,
    EndTurn,
    EvolvePokemon,
    PlayTrainer,
    ResolveDecision,
    Retreat,
    RevealFaceDown,
    UseAttack,
    UsePokemonPower,
)
from kyuura_engine.cards import FACE_DOWN_DEFINITION, FACE_DOWN_HIDDEN_FIELDS
from kyuura_engine.decisions import SECRET_PLAN_CARD
from kyuura_engine.effects import (
    DEFAULT_EFFECTS,
    LT_SURGES_SECRET_PLAN_TEXT,
    SECRET_PLAN_MINEFIELD_CODE,
    PlaceFaceDownOnBench,
)
from kyuura_engine.engine import (
    SECRET_PLAN_IDENTITIES_CODE,
    apply_command,
    check_invariants,
)
from kyuura_engine.errors import (
    SECRET_PLAN_HIDDEN_CODE,
    HiddenPropertyRead,
    IllegalActionError,
    UnsupportedError,
)
from kyuura_engine.observation import UID_FIELDS, observe, visible_log
from kyuura_engine.resolution import events, flow, preflight
from kyuura_engine.rng import rng_fingerprint
from kyuura_engine.serialize import state_to_dict
from kyuura_engine.zones import SECRET_PLAN_LOST_TARGET_CODE
from tests.helpers import (
    ABRA,
    CHARITY,
    DIGLETT,
    DITTO,
    DODUO,
    FIGHTING,
    FIRE,
    GASTLY,
    GENGAR,
    GUST,
    HAUNTER,
    HITMONCHAN,
    KADABRA,
    LT_SURGES_SECRET_PLAN,
    PEWTER_CITY_GYM,
    PLUSPOWER,
    PSYCHIC,
    RATTATA,
    ROCKETS_MINEFIELD_GYM,
    apply_kernel,
    build_test_state,
    with_coin_results,
)
from tests.log_audit import observation_problems, serialization_problems
from tests.test_preflight_v0_15c import preflight_results

H, T = "heads", "tails"


def full(state):
    return (state_to_dict(state, format_version=22), rng_fingerprint(state.rng))


def board(hand=(), bench=(), opponent=None, opponent_bench=(), opponent_hand=(), active=None, stadium_hand=(), turn_number=3, current_player=0):
    """自分（プレイヤー 0）の手札にマチスの秘策と ``hand``。自分のバトル場は闘エネルギー 2 枚のエビワラー（にげる 2）、相手のバトル場は闘エネルギー 1 枚のエビワラー（ジャブ 20）。"""
    return build_test_state([
        {"active": active or {"card": HITMONCHAN, "energy": [FIGHTING, FIGHTING]}, "bench": list(bench),
         "hand": [LT_SURGES_SECRET_PLAN, *hand, *stadium_hand], "deck": [FIRE] * 10},
        {"active": opponent or {"card": HITMONCHAN, "energy": [FIGHTING]}, "bench": list(opponent_bench), "hand": list(opponent_hand),
         "deck": [FIRE] * 10},
    ], turn_number=turn_number, current_player=current_player)


def uid_of(state, card_id, player=0):
    return next(u for u in state.players[player].hand if state.cards[u].card_id == card_id)


def place(state, card_id, player=0):
    """マチスの秘策を使い、``card_id`` の手札のカードをうらにしてベンチに出す。"""
    state = apply_command(state, PlayTrainer(player, uid_of(state, LT_SURGES_SECRET_PLAN, player)))
    assert state.decision is not None and state.decision.kind == SECRET_PLAN_CARD
    return apply_command(state, ResolveDecision(player, state.decision.id, (uid_of(state, card_id, player),)))


def face_down(state, player=0):
    return [q for q in state.players[player].in_play() if state.is_face_down(q)]


def kinds(state, since=0):
    return [e["kind"] for e in state.log[since:]]


def to_active(state, pokemon, player=0):
    """にげるで、うらでないバトル場のポケモンとベンチの ``pokemon`` を入れ替える（バトル場のエビワラーの闘エネルギー 2 枚をトラッシュ）。"""
    active = state.players[player].active
    return apply_command(state, Retreat(player, tuple(active.energy), pokemon.card))


def opponent_turn(state):
    """番を終えて相手の番にする（ポケモンチェックのあと）。"""
    return apply_command(state, EndTurn(state.current_player))


class RegistrationTest(unittest.TestCase):
    def test_registered_with_the_kyuura_printed_text(self):
        """kyuura データの採用（印刷の文面）。型の ``check`` が文面と処理（1 枚・うら・おもてにする時・トラッシュ）を照らす。"""
        entry = DEFAULT_EFFECTS.trainer_entry(LT_SURGES_SECRET_PLAN)
        self.assertIsInstance(entry.effect, PlaceFaceDownOnBench)
        self.assertEqual(entry.effect.implementation_id, "place_face_down_on_bench")
        self.assertEqual(entry.play_text_ja, LT_SURGES_SECRET_PLAN_TEXT)
        self.assertEqual(entry.source, "kyuura data/cards.json")

    def test_face_down_definition_hides_everything_but_basic_pokemon(self):
        """うらのカードは「たねポケモン」としてあつかわれる（印刷の文面）だけで、ほかの項目は決まらない（読むと FD1）。"""
        self.assertEqual((FACE_DOWN_DEFINITION.category, FACE_DOWN_DEFINITION.stage, FACE_DOWN_DEFINITION.powers), ("pokemon", "basic", ()))
        self.assertTrue(FACE_DOWN_DEFINITION.is_basic_pokemon)
        for field in FACE_DOWN_HIDDEN_FIELDS:
            with self.subTest(field=field), self.assertRaises(HiddenPropertyRead) as ctx:
                getattr(FACE_DOWN_DEFINITION, field)
            self.assertEqual(ctx.exception.code, SECRET_PLAN_HIDDEN_CODE)


class PlacementTest(unittest.TestCase):
    def test_any_card_can_be_placed_face_down(self):
        """手札のどのカードでも（たねポケモン・1 進化・2 進化・トレーナー・エネルギー）うらにしてベンチに出せる（「「たねポケモン」でなくてもよく」）。"""
        for card_id in (DIGLETT, KADABRA, "PMCG1-011", PLUSPOWER, FIRE):
            with self.subTest(card=card_id):
                state = board(hand=(card_id,))
                before = sorted(state.cards)
                hidden = uid_of(state, card_id)
                state = place(state, card_id)
                (pokemon,) = face_down(state)
                self.assertEqual((pokemon.card, state.face_down_cards, pokemon.played_turn), (hidden, (hidden,), state.turn_number))
                self.assertEqual(state.card_def(hidden), FACE_DOWN_DEFINITION)
                self.assertNotIn(hidden, state.players[0].hand)
                self.assertIn(uid_of_discard(state, LT_SURGES_SECRET_PLAN), state.players[0].discard)
                self.assertEqual(sorted(state.cards), before)  # カードの保存則（不変条件も確かめる）
                self.assertEqual(check_invariants(state), [])
                self.assertEqual(observation_problems(state), [])
                self.assertEqual(serialization_problems(state), [])

    def test_zero_cards_empty_hand_and_full_bench_do_nothing(self):
        """「出してよい」の出さないこと（0 枚）・手札にカードがない・ベンチに空きがないとき、何もしない（使うための条件ではない）。"""
        state = board(hand=(DIGLETT,))
        state = apply_command(state, PlayTrainer(0, uid_of(state, LT_SURGES_SECRET_PLAN)))
        state = apply_command(state, ResolveDecision(0, state.decision.id, ()))
        self.assertEqual((face_down(state), kinds(state)[-2]), ([], "secret_plan_declined"))
        state = apply_command(board(), PlayTrainer(0, uid_of(board(), LT_SURGES_SECRET_PLAN)))
        self.assertEqual([e["reason"] for e in state.log if e["kind"] == "secret_plan_none"], ["no_cards"])
        state = board(hand=(DIGLETT,), bench=(RATTATA,) * 5)
        state = apply_command(state, PlayTrainer(0, uid_of(state, LT_SURGES_SECRET_PLAN)))
        self.assertEqual([e["reason"] for e in state.log if e["kind"] == "secret_plan_none"], ["bench_full"])
        self.assertIsNone(state.decision)

    def test_minefield_gym_stops_every_placement(self):
        """場にロケット団の爆発ジムがあれば、どのカードを選んでも FD2（選べるが選ぶと止める）。出さないことは答え。"""
        state = board(hand=(DIGLETT,), stadium_hand=(ROCKETS_MINEFIELD_GYM,))
        state = apply_command(state, PlayTrainer(0, uid_of(state, ROCKETS_MINEFIELD_GYM)))
        state = apply_command(state, PlayTrainer(0, uid_of(state, LT_SURGES_SECRET_PLAN)))
        self.assertEqual(state.decision.context_value("unresolved_code"), SECRET_PLAN_MINEFIELD_CODE)
        before = full(state)
        with self.assertRaises(UnsupportedError) as ctx:
            apply_command(state, ResolveDecision(0, state.decision.id, (uid_of(state, DIGLETT),)))
        self.assertEqual(ctx.exception.code, SECRET_PLAN_MINEFIELD_CODE)
        self.assertEqual(full(state), before)
        declined = apply_command(state, ResolveDecision(0, state.decision.id, ()))
        self.assertEqual(face_down(declined), [])


def uid_of_discard(state, card_id, player=0):
    return next(u for u in state.players[player].discard if state.cards[u].card_id == card_id)


class HiddenInformationTest(unittest.TestCase):
    def test_opponent_view_does_not_depend_on_the_hidden_card(self):
        """うらのカードだけが違う 2 つの状態で、相手・観戦者の観測とログの写しが同じ（本当のカードは持ち主だけに見える）。"""
        states = [place(board(hand=(card_id,)), card_id) for card_id in (DIGLETT, FIRE)]
        for viewer in (1, None):
            with self.subTest(viewer=viewer):
                self.assertEqual(observe(states[0], viewer), observe(states[1], viewer))
                self.assertEqual(visible_log(states[0], viewer), visible_log(states[1], viewer))
        owner = observe(states[0], 0)["players"][0]["bench"][0]
        self.assertEqual(owner["real"]["card"], states[0].face_down_cards[0])
        self.assertNotIn("real", observe(states[0], 1)["players"][0]["bench"][0])

    def test_hidden_uid_is_masked_until_revealed(self):
        """うらのあいだは、相手のログの写しにカードの uid がない（uid はデッキの並びからカードがわかる）。おもてにしたら見える。"""
        state = place(board(hand=(DIGLETT,)), DIGLETT)
        hidden = state.face_down_cards[0]
        uid_fields = [(e["kind"], k) for e in visible_log(state, 1) for k, v in e.items()
                      if (k in UID_FIELDS or k.endswith(("_card", "_cards"))) and hidden in (v if isinstance(v, tuple) else (v,))]
        self.assertEqual(uid_fields, [])
        revealed = apply_command(state, RevealFaceDown(0, face_down(state)[0].pokemon_id))
        self.assertTrue(any(e.get("card") == hidden for e in visible_log(revealed, 1) if e["kind"] == "secret_plan_placed" or e["kind"] == "secret_plan_revealed"))


class RevealTest(unittest.TestCase):
    def test_optional_reveal_of_a_basic_keeps_the_pokemon(self):
        """「あなたはいつでもそのカードをおもてにしてよい」: たねポケモンなら同じ場のポケモン（番号・場に出た番）のまま。"""
        state = place(board(hand=(DIGLETT,)), DIGLETT)
        (pokemon,) = face_down(state)
        revealed = apply_command(state, RevealFaceDown(0, pokemon.pokemon_id))
        after = revealed.players[0].find_by_pokemon_id(pokemon.pokemon_id)
        self.assertEqual((revealed.is_face_down(after), after.card, after.played_turn), (False, pokemon.card, pokemon.played_turn))
        self.assertEqual(revealed.card_def(after.card).id, DIGLETT)

    def test_non_basic_is_trashed_with_its_attachments_and_no_prize(self):
        """たねポケモンでなければ、そのカードとついているすべてのカードをトラッシュする（きぜつではない。サイドは取られない）。"""
        state = place(board(hand=(KADABRA, PSYCHIC)), KADABRA)
        (pokemon,) = face_down(state)
        state = apply_command(state, AttachEnergy(0, uid_of(state, PSYCHIC), pokemon.card))
        energy = pokemon_energy = state.players[0].find_by_pokemon_id(pokemon.pokemon_id).energy
        revealed = apply_command(state, RevealFaceDown(0, pokemon.pokemon_id))
        self.assertIsNone(revealed.players[0].find_by_pokemon_id(pokemon.pokemon_id))
        self.assertTrue({pokemon.card, *energy} <= set(revealed.players[0].discard))
        self.assertNotIn("knock_out", kinds(revealed, len(state.log)))
        self.assertEqual(len(revealed.players[1].prizes), len(state.players[1].prizes))
        self.assertEqual(pokemon_energy, energy)

    def test_reveal_rejections_leave_the_state(self):
        """相手のうらのカード・うらでないポケモン・自分の番でないときの ``RevealFaceDown`` は拒否し、状態を変えない。"""
        state = place(board(hand=(DIGLETT,)), DIGLETT)
        pid = face_down(state)[0].pokemon_id
        cases = ((RevealFaceDown(1, pid), "NOT_YOUR_TURN"), (RevealFaceDown(0, state.players[0].active.pokemon_id), "NOT_FACE_DOWN"))
        for command, code in cases:
            before = full(state)
            with self.subTest(code=code), self.assertRaises(IllegalActionError) as ctx:
                apply_command(state, command)
            self.assertEqual((ctx.exception.code, full(state)), (code, before))
        other = opponent_turn(state)
        with self.assertRaises(IllegalActionError) as ctx:
            apply_command(other, RevealFaceDown(1, pid))
        self.assertEqual(ctx.exception.code, "POKEMON_NOT_YOURS")

    def test_opponent_attack_damage_reveals_first(self):
        """相手のワザのダメージを受ける時、その前におもてにする。たねポケモンならダメージを受け、そうでなければトラッシュして交代。"""
        for card_id, survives in ((DIGLETT, True), (FIRE, False)):
            with self.subTest(card=card_id):
                state = place(board(hand=(card_id,), bench=(RATTATA,)), card_id)
                pokemon = face_down(state)[0]
                state = opponent_turn(to_active(state, pokemon))
                after = apply_command(state, UseAttack(1, 0))
                causes = [e["cause"] for e in after.log if e["kind"] == "secret_plan_revealed"]
                self.assertEqual(causes, ["damage"])
                kept = after.players[0].find_by_pokemon_id(pokemon.pokemon_id)
                self.assertEqual(kept is not None, survives)
                if survives:
                    self.assertGreater(kept.damage, 0)
                else:
                    self.assertEqual((after.decision.kind, after.decision.player), ("promote_active", 0))
                    self.assertEqual(len(after.players[1].prizes), len(state.players[1].prizes))
                self.assertEqual(observation_problems(after), [])

    def test_global_effects_do_not_reveal(self):
        """全体に働く効果（スタジアム・番の終わり・ポケモンチェック）では、おもてにしない（p.277 の解説の記録）。"""
        state = place(board(hand=(KADABRA,), stadium_hand=(PEWTER_CITY_GYM,)), KADABRA)
        state = apply_command(state, PlayTrainer(0, uid_of(state, PEWTER_CITY_GYM)))
        state = opponent_turn(state)
        state = apply_command(state, EndTurn(1))
        self.assertEqual(len(face_down(state)), 1)
        self.assertNotIn("secret_plan_revealed", kinds(state))

    def test_own_attack_and_retreat_reveal_first(self):
        """うらのカードがワザを使う・にげる時は、その前におもてにする。たねポケモンでなければトラッシュし（コマンドの操作はおこらない）、交代のあと番にもどる。"""
        for command_kind in ("attack", "retreat"):
            with self.subTest(kind=command_kind):
                state = place(board(hand=(KADABRA,), bench=(RATTATA,)), KADABRA)
                state = to_active(state, face_down(state)[0])
                state = opponent_turn(opponent_turn(state))
                command = UseAttack(0, 0) if command_kind == "attack" else Retreat(0, (), state.players[0].bench[0].card)
                after = apply_command(state, command)
                self.assertEqual([e["cause"] for e in after.log if e["kind"] == "secret_plan_revealed"], [command_kind])
                self.assertEqual((after.decision.kind, after.current_player), ("promote_active", 0))

    def test_evolution_reveals_and_keeps_the_entered_turn(self):
        """進化させる時もおもてにする。うらにして出した番には進化できない（場に出た番は出した番）ので、コマンドごと拒否する（うらのまま）。"""
        state = place(board(hand=(ABRA, KADABRA)), ABRA)
        pid = face_down(state)[0].pokemon_id
        before = full(state)
        with self.assertRaises(IllegalActionError):
            apply_command(state, EvolvePokemon(0, uid_of(state, KADABRA), pid))
        self.assertEqual(full(state), before)
        state = opponent_turn(opponent_turn(state))
        evolved = apply_command(state, EvolvePokemon(0, uid_of(state, KADABRA), pid))
        self.assertEqual([e["cause"] for e in evolved.log if e["kind"] == "secret_plan_revealed"], ["evolve"])
        self.assertEqual(evolved.card_def(evolved.players[0].find_by_pokemon_id(pid).card).id, KADABRA)

    def test_evolving_a_non_basic_trashes_it_and_keeps_the_card_in_hand(self):
        """たねポケモンでないうらのカードに進化カードを重ねようとしたら、おもてにしてトラッシュする（コマンドは受け付ける。進化カードは手札に残る）。"""
        state = place(board(hand=(FIRE, KADABRA)), FIRE)
        pid = face_down(state)[0].pokemon_id
        state = opponent_turn(opponent_turn(state))
        after = apply_command(state, EvolvePokemon(0, uid_of(state, KADABRA), pid))
        self.assertIsNone(after.players[0].find_by_pokemon_id(pid))
        self.assertIn(uid_of(state, KADABRA), after.players[0].hand)


class IdentityIndependenceTest(unittest.TestCase):
    def test_power_target_on_a_face_down_card_is_refused_for_every_identity(self):
        """相手の特殊能力の対象（ゲンガーの［のろい］の移動先）にうらのカードを選ぶと、たねポケモンでなければそのあとを扱えないので止める。本当のカードがたねポケモンでも、
        ありうるカードのどれかで止まるので、同じコード・同じ理由の文で拒否する（受け付けるかが本当のカードで変わらない）。"""
        results = []
        for card_id in (DIGLETT, FIRE):
            state = place(board(hand=(card_id,), active={"card": HITMONCHAN, "energy": [FIGHTING], "damage": 10},
                                opponent={"card": GENGAR, "evolved_from": [GASTLY, HAUNTER]}, turn_number=7), card_id)
            state = opponent_turn(state)
            target = face_down(state, 0)[0].pokemon_id
            source = state.players[0].active.pokemon_id
            before = full(state)
            with self.assertRaises(UnsupportedError) as ctx:
                apply_command(state, UsePokemonPower(1, state.players[1].active.pokemon_id, 0, source=source, target=target))
            self.assertEqual(full(state), before)
            results.append((ctx.exception.code, ctx.exception.message))
        self.assertEqual(results[0], results[1])
        self.assertEqual(results[0][0], SECRET_PLAN_LOST_TARGET_CODE)

    def test_gust_on_a_face_down_card_ends_the_trainer_when_lost(self):
        """突風でうらのカードを選んだら、おもてにする。たねポケモンでなければトラッシュして突風は終わる（入れ替えない）。たねポケモンなら入れ替える。"""
        for card_id, lost in ((FIRE, True), (DIGLETT, False)):
            with self.subTest(card=card_id):
                state = opponent_turn(place(board(hand=(card_id,), opponent_hand=(GUST,)), card_id))
                state = apply_command(state, PlayTrainer(1, uid_of(state, GUST, 1)))
                target = face_down(state, 0)[0].pokemon_id
                after = apply_command(state, ResolveDecision(1, state.decision.id, (target,)))
                self.assertEqual("secret_plan_target_lost" in kinds(after), lost)
                self.assertEqual(after.players[0].active.pokemon_id == target, not lost)
                self.assertEqual(observation_problems(after), [])

    def test_transform_against_a_face_down_defender_stops_for_every_identity(self):
        """相手の［へんしん］のメタモンは相手の対戦ポケモンのカードを今の姿にするが、うらのカードの名前・HP・ワザは決まらない（v0.49 の TF2 と同じく、写すものが決まらない）。
        うらのカードをバトル場に出す操作は、本当のカードによらず FD1 で受け付けない（状態を変えない）。"""
        for card_id in (DIGLETT, FIRE):
            with self.subTest(card=card_id):
                state = place(board(hand=(card_id,), opponent=DITTO), card_id)
                before = full(state)
                with self.assertRaises(UnsupportedError) as ctx:
                    to_active(state, face_down(state)[0])
                self.assertEqual((ctx.exception.code, full(state)), (SECRET_PLAN_HIDDEN_CODE, before))

    def test_promotion_that_always_stops_halts_the_game(self):
        """バトル場に出す決定で、出せるのが［へんしん］のメタモンの前のうらのカードだけなら、どの答えも FD1 で受け付けられないので、答えのない決定を残さずに、
        その前の状態で対戦を止める（``Phase.HALTED``。コードは FD1。本当のカードによらない）。"""
        for card_id in (DIGLETT, FIRE):
            with self.subTest(card=card_id):
                state = place(board(hand=(card_id,), active={"card": HITMONCHAN, "energy": [FIGHTING, FIGHTING], "damage": 60},
                                    opponent={"card": DITTO, "energy": [FIGHTING]}), card_id)
                state = apply_command(opponent_turn(state), UseAttack(1, 0))
                state = apply_command(state, ResolveDecision(1, state.decision.id, (0,)))
                self.assertEqual(state.decision.kind, "promote_active")
                halted = apply_command(state, ResolveDecision(0, state.decision.id, state.decision.options[:1]))
                self.assertEqual((halted.phase.name, halted.halt.code), ("HALTED", SECRET_PLAN_HIDDEN_CODE))
                self.assertEqual(len(face_down(halted)), 1)

    def test_identity_combination_limit_code(self):
        self.assertEqual(SECRET_PLAN_IDENTITIES_CODE, "UNSUPPORTED_SECRET_PLAN_IDENTITIES")


class PreflightFallbackTest(unittest.TestCase):
    """v0.66 の文書 2.5 節の修正: お上品攻撃がついている・うらのカードがあるとき、先読みの上限を超えても v0.13 の止める関数で確かめない（上限の数は上げない）。"""

    def doduo(self, *, charity=False, face_down_card=None):
        players = [
            {"active": {"card": DODUO, "energy": [FIRE, FIRE], "trainers": [(CHARITY, 4)] if charity else []}, "hand": [LT_SURGES_SECRET_PLAN, DIGLETT], "deck": [FIRE] * 10},
            {"active": RATTATA, "deck": [FIRE] * 10},
        ]
        state = build_test_state(players, turn_number=3)
        if face_down_card:
            state = place(state, DIGLETT)
        return with_coin_results(state, H, T)

    def test_unaffected_board_keeps_the_old_fallback(self):
        """（対照）どちらもない盤面は、上限を超えたら今までどおり v0.13 の止める関数で確かめる（方法 ``legacy_after_limit``）。"""
        state = self.doduo()
        with mock.patch.object(preflight, "MAX_BRANCHES", 1):
            results = preflight_results(state, UseAttack(0, 0))
        self.assertEqual([r.mode for r in results], ["derived", "legacy_after_limit"])

    def test_charity_or_face_down_refuses_over_the_limit(self):
        for label, kwargs in (("charity", {"charity": True}), ("face_down", {"face_down_card": True})):
            with self.subTest(label=label):
                state = self.doduo(**kwargs)
                self.assertTrue(flow.legacy_unknown_features(state, state.players[0].active))
                before = full(state)
                with mock.patch.object(preflight, "MAX_BRANCHES", 1), self.assertRaises(UnsupportedError) as ctx:
                    apply_command(state, UseAttack(0, 0))
                self.assertEqual((ctx.exception.code, full(state)), ("UNSUPPORTED_PREFLIGHT_LIMIT", before))
                accepted = apply_command(state, UseAttack(0, 0))  # 上限の中なら受け付ける（上限の数は 4,096 のまま）
                self.assertEqual(preflight.MAX_BRANCHES, 4096)
                self.assertIsNotNone(accepted)

    def test_legacy_mode_tries_every_result_on_affected_boards(self):
        """比べる方法 legacy でも、知らない選択・役割があれば、すべての結果を試す方法（``derived_full``）で確かめる。"""
        plain = preflight_results(self.doduo(), UseAttack(0, 0), mode="legacy")
        affected = preflight_results(self.doduo(face_down_card=True), UseAttack(0, 0), mode="legacy")
        self.assertEqual([r.mode for r in plain], ["legacy"])
        self.assertEqual([r.mode for r in affected], ["derived_full"])
        self.assertTrue(all(isinstance(r, events.PreflightResult) for r in plain + affected))
        apply_kernel(self.doduo(face_down_card=True), UseAttack(0, 0), preflight="legacy")


class GamesTest(unittest.TestCase):
    """正式な対戦開始（new_game・60 枚・サイド 6 枚）からの対戦（tools/existing_effect_games.py の v0.67 の組の手順）。"""

    def test_batch_runs_without_audit_failures(self):
        """v0.67 の 4 組を 3 seed ずつ（席を入れかえて 24 局）。監査（ログの組み立て直し・観測・書き出し）の失敗・想定外の拒否・内部エラー・手数の上限がなく、マチスの秘策で
        うらにして出し、選んで・進化で・ワザで・相手のダメージでおもてにし、たねポケモンなら残り、そうでなければトラッシュする（勝敗は判断に使わない）。"""
        from tools import existing_effect_games as games

        results = games.run(range(3), pairings=games.PAIRINGS_V0_67)
        totals = {}
        for run_ in results.values():
            for game in run_["games"]:
                self.assertEqual(game["audit"], {}, game["seed"])
                self.assertNotIn(game["outcome"], ("internal_error", "unexpected_rejection", "step_limit"), game.get("error"))
                if game["outcome"] == "halted":
                    self.assertEqual(game["halt_code"], "UNRESOLVED_MULLIGAN_COMPENSATION")
                for key, count in game.get("v067", {}).items():
                    totals[key] = totals.get(key, 0) + count
        # v0.68: 相手のダメージでおもてにする場面（revealed_damage）は、この 24 局では化石の秘密のゴローニャのじばく（相手の控えのうらのカード 2 枚以上）だけで起こっていた。
        # v0.68 から、2 枚以上を指定するコマンドは受け付けない（エンジンの未対応 UNSUPPORTED_SECRET_PLAN_IDENTITIES。docs/final-pmcg-cards-v0.68.md 5.3 節・7 章。
        # 対戦の手順は場から確かめて別の操作を続ける）ので、対戦では起こらなくなった（seed 0〜7 でも 0）。相手のダメージでおもてにすることは RevealTest で確かめる
        for key in ("placed", "revealed_choice", "revealed_evolve", "revealed_attack", "revealed_basic", "discarded", "none_bench_full"):
            self.assertGreater(totals.get(key, 0), 0, key)
        self.assertEqual(totals.get("revealed_damage", 0), 0)


if __name__ == "__main__":
    unittest.main()

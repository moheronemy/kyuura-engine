"""コインの前の検証（v0.3d。docs/effect-preflight-v0.3d.md）。

正しく宣言したワザが、原典で決められない場合に当たるかどうかは、コインの結果で変わってはいけない（コインを投げてから
「決められない」と分かる形だと、拒否されるかどうかでこの先のコインの結果が分かってしまう。CLAUDE.md「コインを投げる効果
は、投げる前に使えるかどうか・原典で決められない場合を確かめ終えておきます」）。ここでは次を確かめる。

- 対応カードのワザの実装ごとに、ワザを使うポケモン・相手のポケモンの特殊状態・ダメージ・プラスパワーの組み合わせで、
  コインの結果の全通りについて、受け付けるか・どのコードで拒否するかが同じ
- マヒにするワザ（``ParalyzeOnHeads``）の再付与の確認（``paralysis_problem``）は、不変条件を満たすどの状態でも
  相手の対戦ポケモンには働かない（コインのあとで見つかることがない）ことの証明
- エンジンは ``AttackEffect.problem`` を、宣言（ログ ``attack``）とこんらんのコインの前に聞き、こんらんの「うら」なら
  ワザの処理（``resolve``）を呼ばない

根拠のページ: p.309（ワザを使う手順 1〜6）、p.322（こんらん・マヒ）、p.323（ポケモンチェックの 4）。
"""

import itertools
import unittest

from kyuura_engine import EngineError, PlayTrainer, UseAttack, apply_command, check_invariants, load_card_pool
from kyuura_engine.conditions import paralysis_problem, paralysis_recovery_turn
from kyuura_engine.effects import DEFAULT_EFFECTS, AttackEntry, AttackKey, ConfuseOnHeads
from kyuura_engine.rng import rng_fingerprint
from kyuura_engine.state import turn_owner

from tests.helpers import (
    BEEDRILL, BULBASAUR, BUTTERFREE, CATERPIE, DODUO, FIGHTING, FIRE, GRASS, GROWLITHE, H, IVYSAUR, KAKUNA, LIGHTNING, METAPOD, PARAS, PIKACHU,
    PLUSPOWER, PONYTA,
    PSYCHIC, RATTATA, T, VULPIX, WATER, WEEDLE, build_test_state, with_coin_results,
    BLASTOISE, SQUIRTLE, WARTORTLE, ABRA, ALAKAZAM, KADABRA, GRIMER, MUK, GASTLY, HAUNTER, MACHOP, MACHOKE, MACHAMP,
    GIOVANNIS_MACHAMP, GIOVANNIS_MACHOKE, GIOVANNIS_MACHOP, ROCKETS_MOLTRES, ROCKET_SQUIRTLE, DARK_WARTORTLE, GIOVANNIS_MEOWTH, ROCKETS_SNORLAX,
)

ENERGY = {"grass": GRASS, "fire": FIRE, "water": WATER, "lightning": LIGHTNING, "psychic": PSYCHIC, "fighting": FIGHTING}
# 実装ごとに 1 つ（v0.3d の登録表のワザの実装はこの 7 種類。v0.4b で「かたまる」、v0.4c で 2 進化のスピアーの 2 つ、v0.4d で
# 2 進化のバタフリーの 2 つ（「ふきとばし」は相手の決定を待つ状態で受け付ける）、v0.5 でフシギダネの「やどりぎのタネ」・1 進化の
# フシギソウの「どくのこな」（どちらもコインを投げない新しい実装）を加えた。v0.6 でゼニガメの「あわ」・「からにこもる」（実装は
# キャタピーの「いとをはく」・トランセルの「かたまる」と同じだが、別のカードの登録なので加える）と、2 進化のカメックスの
# 「ハイドロポンプ」（ついている「水」エネルギーの数でダメージを追加する新しい実装。コインなし）を加えた。v0.7 でケーシィの「ねんりき」・
# 1 進化のユンゲラーの「じこさいせい」（エネルギーをトラッシュしてダメージカウンターをすべてとりのぞく新しい実装。ワザを使ったプレイヤーの
# 決定を待つ状態で受け付ける。コインなし）・「ちょうねんりき」・2 進化のフーディンの「あやしいひかり」を加えた。v0.8 でロケット団の
# ベトベターの「どくガス」（ダメージなしでどく。新しい実装）・「ねばりつく」（コインで 20 を追加してマヒ。新しい実装）と、1 進化の
# ベトベトンの「ヘドロこうげき」を加えた。v0.9 で化石の秘密のゴースの「したでなめる」・「エナジーへんかん」（トラッシュのエネルギーを
# 手札に加えて自分に 10。新しい実装。トラッシュにエネルギーがなければ決定なし）と、1 進化のゴーストの「あくむ」（ダメージのあと
# ねむり。新しい実装）を加えた。相手の対戦ポケモンが「とうめい」を持つ場合は tests/test_transparency_v0_9.py の CoinIndependenceTest）
ATTACKS = [
    (GROWLITHE, 0),  # DamageOnly
    (DODUO, 0),  # CoinFlipDamage（コイン 2 枚）
    (PIKACHU, 1),  # SelfDamageOnTails
    (WEEDLE, 0),  # PoisonOnHeads
    (CATERPIE, 0),  # ParalyzeOnHeads
    (PARAS, 1),  # PutToSleep
    (VULPIX, 0),  # ConfuseOnHeads
    (METAPOD, 0),  # PreventDamageOnHeads（v0.4b。トランセルの「かたまる」。1 進化なので、キャタピーから進化したものとして置く）
    (BEEDRILL, 0),  # CoinFlipDamage（v0.4c。スピアーの「ダブルニードル」。2 進化なので、ビードル → コクーンと進化したものとして置く）
    (BEEDRILL, 1),  # PoisonOnHeads（v0.4c。スピアーの「どくばり」）
    (BUTTERFREE, 0),  # DamageAndForceSwitch（v0.4d。バタフリーの「ふきとばし」。相手が決定する。キャタピー → トランセルと進化したものとして置く）
    (BUTTERFREE, 1),  # DamageAndDrain（v0.4d。バタフリーの「メガドレイン」）
    (BULBASAUR, 0),  # DamageAndRemoveCounters（v0.5。フシギダネの「やどりぎのタネ」）
    (IVYSAUR, 1),  # PoisonOpponent（v0.5。フシギソウの「どくのこな」。コインなし。1 進化なので、フシギダネから進化したものとして置く）
    (SQUIRTLE, 0),  # ParalyzeOnHeads（v0.6。ゼニガメの「あわ」）
    (SQUIRTLE, 1),  # PreventDamageOnHeads（v0.6。ゼニガメの「からにこもる」）
    (BLASTOISE, 0),  # ExtraEnergyDamage（v0.6。カメックスの「ハイドロポンプ」。ゼニガメ → カメールと進化したものとして置く）
    (ABRA, 0),  # ParalyzeOnHeads（v0.7。ケーシィの「ねんりき」）
    (KADABRA, 0),  # DiscardEnergyAndRemoveAllCounters（v0.7。ユンゲラーの「じこさいせい」。ケーシィから進化したものとして置く）
    (KADABRA, 1),  # DamageOnly（v0.7。ユンゲラーの「ちょうねんりき」）
    (ALAKAZAM, 0),  # ConfuseOnHeads（v0.7。フーディンの「あやしいひかり」。ケーシィ → ユンゲラーと進化したものとして置く）
    (GRIMER, 0),  # PoisonWithoutDamage（v0.8。ロケット団のベトベターの「どくガス」。ダメージなし・コインなし）
    (GRIMER, 1),  # CoinBonusDamageAndParalyze（v0.8。ロケット団のベトベターの「ねばりつく」。コインの前に確かめる。「ダメージを受けない」相手にも投げる）
    (MUK, 0),  # PoisonOnHeads（v0.8。ベトベトンの「ヘドロこうげき」。ベトベターから進化したものとして置く）
    (GASTLY, 0),  # ParalyzeOnHeads（v0.9。化石の秘密のゴースの「したでなめる」）
    (GASTLY, 1),  # RecoverEnergyAndSelfDamage（v0.9。「エナジーへんかん」。トラッシュは空なので決定を出さない）
    (HAUNTER, 0),  # SleepOpponent（v0.9。化石の秘密のゴーストの「あくむ」。ゴースから進化したものとして置く）
    (MACHOKE, 0),  # DamageReducedByOwnCounters（v0.10。ゴーリキーの「からてチョップ」。ワンリキーから進化したものとして置く）
    (MACHOKE, 1),  # DamageAndSelfDamage（v0.10。ゴーリキーの「じごくぐるま」）
    (MACHAMP, 0),  # DamageOnly（v0.10。カイリキーの「ちきゅうなげ」。ワンリキー → ゴーリキーと進化したものとして置く）
    (GIOVANNIS_MACHOP, 0),  # DamageOnly（v0.11。サカキのワンリキーの「チョップ」）
    (GIOVANNIS_MACHOP, 1),  # CoinHeadsDamagePerOwnCounter（v0.11。「いかりのスーパーパンチ」。コインでダメージの量を決める要素だけ）
    (GIOVANNIS_MACHOKE, 0),  # SelfDamageInsteadOnTails（v0.11。サカキのゴーリキーの「いちかばちか」。サカキのワンリキーから進化したものとして置く）
    (GIOVANNIS_MACHOKE, 1),  # CoinBonusDamageAndParalyze（v0.11。「じごくがため」）
    (GIOVANNIS_MACHAMP, 0),  # CoinFlipDamage（v0.11。サカキのカイリキーの「ハリケーンパンチ」。コイン 4 枚。サカキのワンリキー → ゴーリキーと進化したもの）
    (ROCKETS_MOLTRES, 0),  # DamageAndRetaliation（v0.12。R団のファイヤーの「ほのおのかべ」。相手に 40、自分に次の相手の番の効果。乱数なし）
    (ROCKET_SQUIRTLE, 0),  # DamageOnly（v0.13。第4弾のゼニガメの「こうらアタック」）
    (DARK_WARTORTLE, 0),  # CoinFlipDamage（v0.13。わるいカメールの「おうふくびんた」。コイン 2 枚。第4弾のゼニガメから進化したものとして置く）
    (DARK_WARTORTLE, 1),  # ReturnReceivedDamage（v0.13。「こうらがえし」。ダメージなし・コインなし。自分に次の相手の番の効果）
    (GIOVANNIS_MEOWTH, 0),  # ConfuseOnHeadsWithoutDamage（v0.17a。サカキのニャースの「ねこノミ」。ダメージなし・コインでこんらん）
    (ROCKETS_SNORLAX, 0),  # DamageAndSelfSleep（v0.17b。R団のカビゴンの「たおれこむ」。ダメージを与えなかった場合は宣言の前に止める）
]
# 進化したポケモン（v0.4b の 1 進化・v0.4c の 2 進化）は進化したものとして置く。進化した番は持ち主の 3 番以降の番（2 進化は
# その前に 1 進化した持ち主の番がある）なので、盤面を進化の回数 × 2 番あとにずらす
EVOLVED_FROM = {METAPOD: (CATERPIE,), BEEDRILL: (WEEDLE, KAKUNA), BUTTERFREE: (CATERPIE, METAPOD), IVYSAUR: (BULBASAUR,),
                BLASTOISE: (SQUIRTLE, WARTORTLE), KADABRA: (ABRA,), ALAKAZAM: (ABRA, KADABRA), MUK: (GRIMER,),
                HAUNTER: (GASTLY,), MACHOKE: (MACHOP,), MACHAMP: (MACHOP, MACHOKE), GIOVANNIS_MACHOKE: (GIOVANNIS_MACHOP,),
                GIOVANNIS_MACHAMP: (GIOVANNIS_MACHOP, GIOVANNIS_MACHOKE), DARK_WARTORTLE: (ROCKET_SQUIRTLE,)}
# コインでダメージの量を決める要素だけのワザ（CoinFlipDamage。v0.11 のいかりのスーパーパンチ（CoinHeadsDamagePerOwnCounter）も）
COIN_DAMAGE = {(DODUO, 0), (BEEDRILL, 0), (GIOVANNIS_MACHOP, 1), (GIOVANNIS_MACHAMP, 0), (DARK_WARTORTLE, 0)}
ATTACKER_STATES = [{}, {"poison": 10}, {"confusion": True}, {"poison": 10, "confusion": True}]
DEFENDER_STATES = [{}, {"poison": 10}, {"sleep": True}, {"paralysis": 2}, {"paralysis": 3}, {"confusion": True},
                   {"poison": 10, "confusion": True},
                   # v0.4b: 相手の対戦ポケモンが、前の番（相手の番）に「かたまる」で「ダメージを受けない」状態になっている
                   {"prevent_damage": 2}, {"prevent_damage": 2, "poison": 10}]
COINS = list(itertools.product((H, T), repeat=3))  # こんらん 1 枚 + ワザの説明 2 枚まで


def energy_for(card_id, index):
    definition = load_card_pool().get(card_id)
    own = definition.pokemon_type.value if definition.pokemon_type.value in ENERGY else "fire"
    return [ENERGY[own if cost.value == "colorless" else cost.value] for cost in definition.attacks[index].cost]


def outcome(state, command):
    try:
        new = apply_command(state, command)
    except EngineError as error:
        return error.code
    assert check_invariants(new) == []
    return "accepted"


class CoinIndependenceTest(unittest.TestCase):
    def test_acceptance_does_not_depend_on_the_coins(self):
        """受け付けるか・拒否のコードが、コインの結果（8 通り）で変わらない。"""
        checked = 0
        for (card, index), attacker_state, defender_state, near_ko, pluspower in itertools.product(
            ATTACKS, ATTACKER_STATES, DEFENDER_STATES, (False, True), (False, True)
        ):
            hp = load_card_pool().get(GROWLITHE).hp
            shift = 2 * len(EVOLVED_FROM.get(card, ()))  # 盤面の番をずらす（v0.4b・v0.4c）
            attacker = {"card": card, "energy": energy_for(card, index), **attacker_state}
            if card in EVOLVED_FROM:
                attacker.update(evolved_from=list(EVOLVED_FROM[card]), evolved_turn=1 + shift)
            defender = {"card": GROWLITHE, "damage": hp - 10 if near_ko else 0, **defender_state}
            for key in ("paralysis", "prevent_damage"):
                if key in defender:
                    defender[key] += shift
            state = build_test_state([
                {"active": attacker, "bench": [PONYTA], "hand": [PLUSPOWER] if pluspower else []},
                {"active": defender, "bench": [RATTATA]},
            ], turn_number=3 + shift)
            if pluspower:
                state = apply_command(state, PlayTrainer(0, state.players[0].hand[0]))
            results = {outcome(with_coin_results(state, *coins), UseAttack(0, index)) for coins in COINS}
            with self.subTest(card=card, attacker=attacker_state, defender=defender_state, near_ko=near_ko, pluspower=pluspower):
                self.assertEqual(len(results), 1, results)
                if (card, index) in COIN_DAMAGE and "prevent_damage" in defender_state:
                    # v0.4b: コインでダメージの量を決めるワザの要素が無効になるとき、そのコインを投げるかは決められない
                    # （p.321。docs/persistent-damage-v0.4b.md 5 章）。こんらんのコインの前に止める
                    self.assertEqual(results, {"UNRESOLVED_PREVENTED_COIN_DAMAGE"})
                elif card == ROCKETS_SNORLAX and "prevent_damage" in defender_state:
                    # v0.17b: たおれこむのダメージが「ダメージを受けない」状態で無効なら、自分をねむりにするかは決められない（Z23）。止める問いの優先度は
                    # ワザの実装の problem と同じ（こんらんのダメージの変更効果より先。questions の priority 10）
                    self.assertEqual(results, {"UNRESOLVED_EFFECT_AFTER_NO_DAMAGE"})
                elif pluspower and attacker_state.get("confusion"):
                    self.assertEqual(results, {"UNRESOLVED_CONFUSION_DAMAGE_MODIFIERS"})
                else:
                    self.assertEqual(results, {"accepted"})
            checked += 1
        self.assertEqual(checked, len(ATTACKS) * len(ATTACKER_STATES) * len(DEFENDER_STATES) * 4)


class ReparalysisProofTest(unittest.TestCase):
    """``ParalyzeOnHeads`` は相手の対戦ポケモンだけをマヒにする。番 T（番のプレイヤー p）に相手のポケモンがマヒ状態で
    残っているのは、マヒ状態になった番 t の回復する番（t より後の、相手の最初の番）が T 以上のとき、つまり t = T か
    t = T − 1 のときだけで（それより前なら、相手の番 T − 1 の終わりに回復している。不変条件で確かめている）、どちらも
    回復する番は T + 1。再付与の番（T）から数えても T + 1 なので同じになり、``paralysis_problem`` は働かない
    （p.322・p.323。docs/effect-preflight-v0.3d.md 4 章）。"""

    def test_opponent_paralysis_never_needs_the_unresolved_ruling(self):
        checked = 0
        for turn in range(2, 12):
            player = turn_owner(build_test_state([{"active": GROWLITHE}, {"active": RATTATA}]), turn)
            opponent = 1 - player
            for paralyzed_turn in range(1, turn + 1):
                specs = [{"active": GROWLITHE}, {"active": RATTATA}]
                specs[opponent] = {"active": {"card": RATTATA, "paralysis": paralyzed_turn}}
                state = build_test_state(specs, current_player=player, turn_number=turn)
                target = state.players[opponent].active
                if paralysis_recovery_turn(state, opponent, paralyzed_turn) < turn:
                    # 回復しているはずのマヒが残っている状態は作れない（不変条件の違反）
                    self.assertTrue(check_invariants(state))
                    continue
                self.assertEqual(check_invariants(state), [])
                self.assertIn(paralyzed_turn, (turn - 1, turn))
                self.assertIsNone(paralysis_problem(state, opponent, target))
                checked += 1
        self.assertGreater(checked, 0)

    def test_own_pokemon_can_need_it(self):
        """自分のポケモンを自分の番にマヒにする効果なら、回復する番が変わることがある（v0.3d の対応カードにはない）。"""
        state = build_test_state([{"active": {"card": GROWLITHE, "paralysis": 2}}, {"active": RATTATA}])
        self.assertIsNotNone(paralysis_problem(state, 0, state.players[0].active))


class PreflightOrderTest(unittest.TestCase):
    """エンジンが ``problem`` を聞く位置と、こんらんの「うら」で ``resolve`` を呼ばないこと。"""

    def spy_registry(self, calls, problem=None):
        class Spy(ConfuseOnHeads):
            implementation_id = "test_spy"

            def problem(self, state, use):
                calls.append(("problem", len(state.log), rng_fingerprint(state.rng)))
                return problem

            def resolve(self, state, use):
                calls.append(("resolve", len(state.log), rng_fingerprint(state.rng)))
                super().resolve(state, use)

        text = load_card_pool().get(VULPIX).attacks[0].text_ja
        return DEFAULT_EFFECTS.with_attacks("test-spy", {AttackKey(VULPIX, 0): AttackEntry(Spy(), "あやしいひかり", text_ja=text)})

    def board(self, effects, *sides, confused=False):
        state = build_test_state([
            {"active": {"card": VULPIX, "energy": [FIRE, FIRE], **({"confusion": True} if confused else {})}, "bench": [PONYTA]},
            {"active": GROWLITHE, "bench": [RATTATA]},
        ], effects=effects)
        return with_coin_results(state, *sides)

    def test_problem_is_asked_before_the_declaration_and_any_coin(self):
        for confused in (False, True):
            for side in (H, T):
                with self.subTest(confused=confused, side=side):
                    calls = []
                    state = self.board(self.spy_registry(calls), side, side, confused=confused)
                    start, fingerprint = len(state.log), rng_fingerprint(state.rng)
                    apply_command(state, UseAttack(0, 0))
                    self.assertEqual(calls[0], ("problem", start, fingerprint))  # 宣言の前・乱数を使う前
                    resolved = [c for c in calls if c[0] == "resolve"]
                    self.assertEqual(len(resolved), 0 if confused and side is T else 1)  # 「うら」なら手順 6 はない

    def test_problem_stops_without_resolving(self):
        from kyuura_engine import UnsupportedError

        for confused in (False, True):
            with self.subTest(confused=confused):
                calls = []
                effects = self.spy_registry(calls, problem=UnsupportedError("UNRESOLVED_TEST", "テスト専用"))
                state = self.board(effects, H, H, confused=confused)
                with self.assertRaises(UnsupportedError):
                    apply_command(state, UseAttack(0, 0))
                self.assertEqual([c[0] for c in calls], ["problem"])


if __name__ == "__main__":
    unittest.main()

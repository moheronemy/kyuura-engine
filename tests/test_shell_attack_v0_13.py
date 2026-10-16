"""わるいカメールのワザ「こうらがえし」・「おうふくびんた」と第4弾のゼニガメ（v0.13。盤面を直接作るテスト）。

最新の説明（『ポケモンカードオフィシャルブック2000』p.89）: 「●おうふくびんた コインを2枚投げ、「おもて」の数×10のダメージ。」「●こうらがえし
次の相手の番、このカードが相手のワザによってダメージを受けたとき、（それによってこのカードが「きぜつ」しても、）そのポケモンにも同じダメージを
与える。（ダメージ以外の効果は与えない）」 解説（p.89）: 「相手の対戦ポケモンがこの「わるいカメール」に与えたダメージが、そのままその相手に
返ってくる」「相手のワザのダメージがこの「わるいカメール」のHP以上だったときでも、そのダメージがそのまま返ります。仮に100ダメージを受けたら
そのまま100ダメージが返る」「「わるいカメール」が弱点とする雷ポケモンが相手の場合は、ワザのダメージが2倍になるため、2倍のまま相手にダメージが
返ります。逆に相手が「わるいカメール」の水を弱点にしていた場合は、「こうらがえし」で返すダメージは「ワザによるダメージ」なので、2倍になって
相手に返ります」。ワザ解説「相手の番ではたらく効果」（p.89）: 返すのは相手のワザのダメージの処理のあと・ダメージ以外の効果の前（「ふきとばし」・
「スターブーメラン」の例）、効果の対象はワザを使ったポケモン自身、効果の持続は次の相手の番の最後、ベンチにもどると消える。一般規定: p.309・
p.310・p.320・p.321（「8」の例「わるいカメールが「こうらがえし」の効果で、相手の番で受けた20ダメージを、相手の番に返した場合、そのダメージは
効果によるダメージではなく、「こうらがえし」のダメージとしてあつかいます。」・計算の順番）・p.322（持続する効果）・p.324（同時のきぜつ）。
第4弾のゼニガメは p.88。kyuura の記録 id: PMCG4-018・PMCG4-021・NEO-2000-OFFICIAL-RULES。

裁定（S1〜S41）は docs/shell-attack-v0.13.md、カードの照合は docs/dark-wartortle-v0.13.md、可変の量の仕組みは docs/variable-retaliation-v0.13.md。
S37（わるいカメールとワザを使ったポケモンがそろってきぜつ）は v0.12 の W24 と同じ問いなので、同じコード
（``UNRESOLVED_RETALIATION_DOUBLE_KNOCKOUT``）でワザの宣言の前に止める。
"""

import copy
import dataclasses
import itertools
import pickle
import unittest

from kyuura_engine import (
    DEFAULT_EFFECTS, AttackKey, EndTurn, EngineError, EvolvePokemon, Phase, ResolveDecision, Retreat, TakePrize, UseAttack,
    UsePokemonPower, apply_command, check_invariants, state_to_dict,
)
from kyuura_engine.cards import load_card_pool, pool_from_extract, read_extract, read_verification
from kyuura_engine.errors import UnsupportedError
from kyuura_engine.decisions import KO_PREVENTION, POST_KNOCKOUT_POWER
from kyuura_engine.effects import (
    DAMAGE_ONLY, AttackEffect, AttackEntry, CoinFlipDamage, DamageProfile, OPPONENT_ACTIVE, ReturnReceivedDamage, deal_attack_damage,
    finish_damage_elements,
)
from kyuura_engine.persistent import retaliation
from kyuura_engine.rng import rng_fingerprint
from kyuura_engine.state import RETALIATION_FIXED, RETALIATION_RECEIVED, Retaliation
from tests.helpers import (
    ABRA, ALAKAZAM, BLASTOISE, BULBASAUR, BUTTERFREE, CATERPIE, DARK_WARTORTLE, DEFENDER, DODUO, FIGHTING, FIRE, GASTLY,
    GIOVANNIS_MACHAMP, GIOVANNIS_MACHOKE, GIOVANNIS_MACHOP, GRASS, GRIMER, GROWLITHE, H, HAUNTER, IVYSAUR, KADABRA, LIGHTNING, MACHAMP,
    MACHOKE, MACHOP, METAPOD, MUK, PIKACHU, PLUSPOWER, PONYTA, PSYCHIC, RATTATA, ROCKET_SQUIRTLE, ROCKETS_MOLTRES, SQUIRTLE, STARYU, T,
    VENUSAUR, WARTORTLE, WATER, WEEDLE, build_test_state, with_coin_results,
)
from tests.log_audit import serialization_problems

DOUBLESLAP = AttackKey(DARK_WARTORTLE, 0)
SHELL = AttackKey(DARK_WARTORTLE, 1)
SHELL_LATEST = (
    "次の相手の番、このカードが相手のワザによってダメージを受けたとき、（それによってこのカードが「きぜつ」しても、）そのポケモンにも同じダメージを"
    "与える。（ダメージ以外の効果は与えない）"
)
SHELL_PRINTED = (
    "次の相手の番で、このカードが相手のワザによってダメージを受けた時、(このカードが「きぜつ」するしないにかかわらず、)そのポケモンにも同じダメージを"
    "与える。(ダメージ以外の効果は与えない)"
)
DOUBLESLAP_LATEST = "コインを2枚投げ、「おもて」の数×10のダメージ。"
DOUBLESLAP_PRINTED = "コインを2枚投げて「おもて」の数×10のダメージ。"
TURN = 7  # プレイヤー 0 の番（先攻はプレイヤー 0）。プレイヤー 1 のわるいカメールが 6 番に「こうらがえし」を使った盤面
DARK = {"card": DARK_WARTORTLE, "evolved_from": ROCKET_SQUIRTLE}
STOP = "UNRESOLVED_RETALIATION_DOUBLE_KNOCKOUT"
RECEIVED_KIND = "retaliation_received_damage"


def full(state):
    return state_to_dict(state, format_version=9)


def kinds(state, start=0):
    return [e["kind"] for e in state.log[start:]]


def board(attacker, *, wartortle=None, attacker_bench=(RATTATA,), wartortle_bench=(PONYTA,), turn=TURN, effect=True, **kwargs):
    """プレイヤー 0 の ``attacker`` が、前の番に「こうらがえし」を使ったプレイヤー 1 のわるいカメールを攻撃する盤面。"""
    holder = {**DARK, **({"retaliation_received": turn - 1} if effect else {}), **(wartortle or {})}
    return build_test_state([
        {"active": attacker, "bench": list(attacker_bench)},
        {"active": holder, "bench": list(wartortle_bench)},
    ], turn_number=turn, **kwargs)


def returned(state):
    """返したダメージのログ（damage の retaliation）。"""
    return [e for e in state.log if e["kind"] == "damage" and e.get("retaliation")]


def triggered(state):
    return [e for e in state.log if e["kind"] == "retaliation"]


def pool_with(card, **changes):
    """テスト専用の記録（対応カードに、その弱点・抵抗力を持つポケモンがない場面のため）。"""
    extract = copy.deepcopy(read_extract())
    record = next(c for c in extract["cards"] if c["id"] == card)
    record["pokemon"].update(changes)
    return pool_from_extract(extract)


PONYTA_ATTACKER = {"card": PONYTA, "energy": [FIRE, FIRE]}  # ほのおのしっぽ 30（弱点 水）
PIKACHU_ATTACKER = {"card": PIKACHU, "energy": [LIGHTNING, LIGHTNING]}  # かじる 10・でんげき 30（わるいカメールの弱点 雷）
KADABRA_ATTACKER = {"card": KADABRA, "evolved_from": ABRA, "energy": [PSYCHIC] * 3}  # ちょうねんりき 50（HP 60）


class RegistrationTest(unittest.TestCase):
    """カードの照合と登録（S1・S2。docs/dark-wartortle-v0.13.md）。"""

    def test_registered_with_the_latest_description(self):
        shell = DEFAULT_EFFECTS.attack_entry(DARK_WARTORTLE, 1)
        self.assertEqual(shell.effect, ReturnReceivedDamage())
        self.assertEqual((shell.name_ja, shell.text_ja, shell.play_text_ja, shell.source), ("こうらがえし", SHELL_PRINTED, SHELL_LATEST, "P43 p.89"))
        slap = DEFAULT_EFFECTS.attack_entry(DARK_WARTORTLE, 0)
        self.assertEqual(slap.effect, CoinFlipDamage(coins=2, damage_per_heads=10))
        self.assertEqual((slap.name_ja, slap.text_ja, slap.play_text_ja, slap.source), ("おうふくびんた", DOUBLESLAP_PRINTED, DOUBLESLAP_LATEST, "P43 p.89"))
        self.assertEqual(DEFAULT_EFFECTS.attack_entry(ROCKET_SQUIRTLE, 0).effect, DAMAGE_ONLY)

    def test_card_data(self):
        """わるいカメール（HP 60・水・弱点 雷・抵抗力なし・にげる 1）。こうらがえしは水無でダメージなし（S1・S2）。"""
        pool = load_card_pool()
        dark = pool.get(DARK_WARTORTLE)
        self.assertEqual((dark.hp, dark.pokemon_type.value, dark.weakness.value, dark.resistance, dark.evolves_from), (60, "water", "lightning", None, "ゼニガメ"))
        slap, shell = dark.attacks
        self.assertEqual(([c.value for c in slap.cost], slap.damage, slap.damage_modifier), (["water"], 10, "×"))
        self.assertEqual(([c.value for c in shell.cost], shell.damage, shell.text_ja), (["water", "colorless"], None, SHELL_PRINTED))
        squirtle = pool.get(ROCKET_SQUIRTLE)
        self.assertEqual((squirtle.hp, squirtle.name_ja, [c.value for c in squirtle.attacks[0].cost], squirtle.attacks[0].damage),
                         (50, "ゼニガメ", ["colorless", "colorless"], 20))

    def test_verification_record(self):
        record = read_verification()["cards"][DARK_WARTORTLE]
        self.assertEqual((record["status"], record["page"], record["pdf_page"], record["rules_page"]), ("不一致あり", 89, 91, 321))
        self.assertEqual(record["latest_description_ja"], {"0": DOUBLESLAP_LATEST, "1": SHELL_LATEST})
        self.assertEqual([m["kyuura"] for m in record["mismatches"]], [DOUBLESLAP_PRINTED, SHELL_PRINTED])
        squirtle = read_verification()["cards"][ROCKET_SQUIRTLE]
        self.assertEqual((squirtle["status"], squirtle["page"], squirtle["pdf_page"]), ("一致", 88, 90))

    def test_evolves_from_either_squirtle(self):
        """「ゼニガメから進化」は名前で決まる（p.310）。第4弾のゼニガメからも第1弾のゼニガメからも進化できる。第4弾のゼニガメから第1弾の
        カメールにも進化できる（p.88 の解説「「カメール（第1弾）」に進化すれば、すぐに「かみつく」が使えます」）。"""
        for base, evolution in ((ROCKET_SQUIRTLE, DARK_WARTORTLE), (SQUIRTLE, DARK_WARTORTLE), (ROCKET_SQUIRTLE, WARTORTLE)):
            with self.subTest(base=base, evolution=evolution):
                state = build_test_state([{"active": base, "hand": [evolution]}, {"active": MACHOP}], turn_number=3)
                state = apply_command(state, EvolvePokemon(0, state.players[0].hand[0], state.players[0].active.pokemon_id))
                self.assertEqual(state.card_def(state.players[0].active.card).id, evolution)
                self.assertEqual(check_invariants(state), [])


class EffectCreationTest(unittest.TestCase):
    """こうらがえし・おうふくびんたを使う番（S1〜S4・S33）。"""

    def wartortle_turn(self, defender=MACHOP, **wartortle):
        return build_test_state([
            {"active": {**DARK, "energy": [WATER, WATER], **wartortle}, "bench": [PONYTA]},
            {"active": defender, "bench": [MACHOP]},
        ], turn_number=5)

    def test_effect_on_itself_without_damage_or_coins(self):
        """ダメージなし（S2）・コインなし。自分に持続する効果（量は受けたダメージで決まるので持たない）。はたらくのは次の相手の番（S3）。"""
        state = self.wartortle_turn()
        start, rng = len(state.log), rng_fingerprint(state.rng)
        state = apply_command(state, UseAttack(0, 1))
        self.assertEqual(kinds(state, start)[:2], ["attack", "persistent_effect_added"])
        self.assertNotIn("damage", kinds(state, start))
        added = state.log[start + 1]
        self.assertEqual((added["persistent_effect"], added["active_turn"], added["effect"]), ("retaliation_received_damage", 6, str(SHELL)))
        wartortle = state.players[0].active
        self.assertEqual(wartortle.persistent_effects, (Retaliation(wartortle.card, 0, 5, 6, 1, None, RETALIATION_RECEIVED),))
        self.assertEqual(rng_fingerprint(state.rng), rng)
        self.assertEqual((state.turn_number, state.current_player), (6, 1))
        self.assertIsNotNone(retaliation(state, wartortle))

    def test_not_working_on_other_turns(self):
        """はたらくのは効果を与えた番の次の番だけ（S3・S4）。"""
        state = board(PONYTA_ATTACKER)
        wartortle = state.players[1].active
        for turn in (TURN - 1, TURN + 1):
            other = state.clone()
            other.turn_number = turn
            self.assertIsNone(retaliation(other, wartortle))

    def test_expires_at_the_end_of_the_next_opponent_turn(self):
        """次の相手の番の終わりに消える（S33。p.89「効果の持続：次の相手の番の最後」）。turn_end の前、ポケモンチェックの前。"""
        state = apply_command(self.wartortle_turn(), UseAttack(0, 1))
        state = apply_command(state, EndTurn(1))
        events = [e for e in state.log if e["kind"] in ("persistent_effect_removed", "turn_end", "pokemon_check")]
        self.assertEqual([e["kind"] for e in events[-3:]], ["persistent_effect_removed", "turn_end", "pokemon_check"])
        self.assertEqual((events[-3]["reason"], events[-3]["turn"], events[-3]["persistent_effect"]), ("expired", 6, "retaliation_received_damage"))
        self.assertEqual(state.players[0].active.persistent_effects, ())

    def test_doubleslap(self):
        """おうふくびんた: コイン 2 枚の「おもて」の数 × 10（ガーディは弱点 水で 2 倍）。コインはワザを使ったプレイヤーが 2 枚。"""
        for coins, amount in (((H, H), 40), ((H, T), 20), ((T, T), 0)):
            with self.subTest(coins=coins):
                state = with_coin_results(self.wartortle_turn(defender=GROWLITHE), *coins)
                start = len(state.log)
                state = apply_command(state, UseAttack(0, 0))
                flips = [e for e in state.log[start:] if e["kind"] == "coin_flip"]
                self.assertEqual([(e["player"], e["effect"]) for e in flips], [(0, str(DOUBLESLAP))] * 2)
                damage = next(e for e in state.log[start:] if e["kind"] == "damage")
                self.assertEqual(damage["amount"], amount)


class ReceivedDamageTest(unittest.TestCase):
    """「同じダメージ」= 受けたダメージ（相手のワザによる最終ダメージ。S9〜S18）。元のワザの基本となるダメージではない。"""

    def test_received_final_damage_is_the_base_and_differs_from_the_final_return(self):
        """ポニータのほのおのしっぽ 30 → 受けた 30 → 返すダメージの基本となるダメージ 30 → ポニータの弱点 水で 60（S9・S10・S20・S21）。
        ログは retaliation（amount 30・received_damage 30）のあとに返すダメージ（amount 60）。"""
        state = board(PONYTA_ATTACKER)
        start = len(state.log)
        state = apply_command(state, UseAttack(0, 1))
        self.assertEqual(kinds(state, start)[:4], ["attack", "damage", "retaliation", "damage"])
        event = state.log[start + 2]
        self.assertEqual((event["amount"], event["basis"], event["received_damage"], event["effect"], event["trigger"]),
                         (30, RETALIATION_RECEIVED, 30, str(SHELL), f"{PONYTA}#1"))
        back = state.log[start + 3]
        self.assertEqual((back["amount"], back["weakness"], back["retaliation"], back["effect"]), (60, True, True, str(SHELL)))
        self.assertEqual(back["steps"], (("1 基本となる計算", 30), ("3 弱点", 60)))

    def test_weakness_of_the_wartortle_is_included(self):
        """わるいカメールの弱点（雷）で 2 倍になったダメージがそのまま返る（S11。p.89「2倍のまま相手にダメージが返ります」）: かじる 10 → 20 → 20。"""
        state = apply_command(board(PIKACHU_ATTACKER), UseAttack(0, 0))
        self.assertEqual(triggered(state)[0]["received_damage"], 20)
        self.assertEqual(returned(state)[0]["amount"], 20)

    def test_resistance_of_the_wartortle_is_included(self):
        """受ける側の抵抗力で減ったダメージが返る（S12。わるいカメールに抵抗力はないので、炎 −30 のテスト専用の記録）: ほのおのかべ 40 − 30 = 10。"""
        pool = pool_with(DARK_WARTORTLE, resistances=[{"type": "fire", "operator": "-", "value": 30}])
        moltres = {"card": ROCKETS_MOLTRES, "energy": [FIRE] * 3}
        state = apply_command(board(moltres, pool=pool), UseAttack(0, 0))
        self.assertEqual(triggered(state)[0]["received_damage"], 10)
        self.assertEqual(returned(state)[0]["amount"], 10)

    def test_pluspower_of_the_attacker_is_included(self):
        """攻撃側のプラスパワーで増えたダメージが返る（S13。SUPPORTED）: 30 + 10 = 40 → 40 → 弱点で 80。"""
        state = apply_command(board({**PONYTA_ATTACKER, "trainers": [(PLUSPOWER, TURN)]}), UseAttack(0, 1))
        self.assertEqual(triggered(state)[0]["received_damage"], 40)
        self.assertEqual(returned(state)[0]["amount"], 80)

    def test_defender_on_the_wartortle_is_included(self):
        """受ける側のディフェンダーで減ったダメージが返る（S14。SUPPORTED。p.279 の「お上品攻撃」の解説）: 30 − 20 = 10 → 10 → 弱点で 20。"""
        state = apply_command(board(PONYTA_ATTACKER, wartortle={"trainers": [(DEFENDER, TURN)]}), UseAttack(0, 1))
        self.assertEqual(triggered(state)[0]["received_damage"], 10)
        self.assertEqual(returned(state)[0]["amount"], 20)

    def test_zero_received_does_not_return(self):
        """最終ダメージ 0 は「ダメージを受けなかった」（S16。p.319・p.321）: かじる 20 − ディフェンダー 20 = 0。"""
        state = apply_command(board(PIKACHU_ATTACKER, wartortle={"trainers": [(DEFENDER, TURN)]}), UseAttack(0, 0))
        self.assertEqual(next(e for e in state.log if e["kind"] == "damage")["amount"], 0)
        self.assertEqual(triggered(state), [])

    def test_no_hp_cap_and_knocked_out_wartortle_still_returns(self):
        """残り HP 10 で 50 を受けたら 50 を返す（S17。p.89「仮に100ダメージを受けたらそのまま100ダメージが返る」）。わるいカメールがきぜつしても
        返す（S18・S36。CONFIRMED）。きぜつで効果は消える（S31）。"""
        state = apply_command(board(KADABRA_ATTACKER, wartortle={"damage": 50}), UseAttack(0, 1))
        self.assertEqual((triggered(state)[0]["received_damage"], returned(state)[0]["amount"]), (50, 50))
        self.assertEqual(state.players[0].active.damage, 50)
        removed = next(e for e in state.log if e["kind"] == "persistent_effect_removed")
        self.assertEqual((removed["reason"], removed["persistent_effect"]), ("knock_out", "retaliation_received_damage"))
        knocked = [e["player"] for e in state.log if e["kind"] == "knock_out"]
        self.assertEqual(knocked, [1])

    def test_return_is_not_the_attack_base_damage(self):
        """元のワザの基本となるダメージ（ダメージの目安の数字）を返すのではない: かじる（目安 10）で返すのは 20（受けた量）。"""
        state = apply_command(board(PIKACHU_ATTACKER), UseAttack(0, 0))
        attack = load_card_pool().get(PIKACHU).attacks[0]
        self.assertEqual(attack.damage, 10)
        self.assertNotEqual(triggered(state)[0]["amount"], attack.damage)


class ReturnDamageTest(unittest.TestCase):
    """返すダメージ（S19〜S25）: ワザを使ったポケモンへ、「こうらがえし」のワザによるダメージとして p.321 の順番で計算する。"""

    def test_target_is_the_attacking_pokemon(self):
        """返す相手はダメージを与えたポケモン（S19。p.89「そのポケモンにも」）。ベンチには返さない。"""
        state = board(PONYTA_ATTACKER)
        attacker = state.players[0].active.pokemon_id
        state = apply_command(state, UseAttack(0, 1))
        self.assertEqual((triggered(state)[0]["attacker_pokemon_id"], returned(state)[0]["pokemon_id"]), (attacker, attacker))
        self.assertEqual([pk.damage for pk in state.players[0].bench], [0])

    def test_resistance_of_the_attacker_applies(self):
        """返すダメージに受ける側（ワザを使ったポケモン）の抵抗力（S22。SUPPORTED。水の抵抗力を持つ対応カードはないので、テスト専用の記録）:
        20 − 30 = 0。"""
        pool = pool_with(PIKACHU, resistances=[{"type": "water", "operator": "-", "value": 30}])
        state = apply_command(board(PIKACHU_ATTACKER, pool=pool), UseAttack(0, 0))
        back = returned(state)[0]
        self.assertEqual((back["amount"], back["resistance"]), (0, True))

    def test_defender_on_the_attacker_applies(self):
        """ワザを使ったポケモンについているディフェンダー（S23。SUPPORTED）: 30 → 弱点で 60 − 20 = 40。"""
        state = apply_command(board({**PONYTA_ATTACKER, "trainers": [(DEFENDER, TURN + 1)]}), UseAttack(0, 1))
        back = returned(state)[0]
        self.assertEqual(back["amount"], 40)
        self.assertEqual(back["modifiers"][0][0], 7)

    def test_transparency_of_the_attacker(self):
        """ゴーストの「とうめい」（S24。SUPPORTED）: 「おもて」なら返すダメージを受けない、「うら」なら受ける。コインはゴースト側のプレイヤー。
        そのあと、あくむのねむりはわるいカメールに（ダメージ以外の効果。S34）。"""
        haunter = {"card": HAUNTER, "evolved_from": GASTLY, "energy": [PSYCHIC, PSYCHIC]}
        heads = apply_command(with_coin_results(board(haunter), H), UseAttack(0, 0))
        self.assertEqual(returned(heads), [])
        evade = next(e for e in heads.log if e["kind"] == "evade_check")
        self.assertEqual((evade["player"], evade["effect"]), (0, str(SHELL)))
        tails = apply_command(with_coin_results(board(haunter), T), UseAttack(0, 0))
        self.assertEqual(returned(tails)[0]["amount"], 10)
        order = [k for k in kinds(tails) if k in ("damage", "retaliation", "evade_check", "special_condition")]
        self.assertEqual(order[-5:], ["damage", "retaliation", "evade_check", "damage", "special_condition"])
        sleep = next(e for e in tails.log if e["kind"] == "special_condition")
        self.assertEqual((sleep["player"], sleep["condition"]), (1, "sleep"))  # 番の終わりのポケモンチェックで目覚めることもある

    def test_counterattack_of_the_attacker_and_no_chain(self):
        """返すダメージはワザによるダメージなので、ワザを使ったカイリキーの「はんげき」がはたらく（S25。SUPPORTED）。「はんげき」のダメージは
        特殊能力によるダメージなので、「こうらがえし」は再びはたらかない（連鎖しない）。ちきゅうなげ 60 − ディフェンダー 20 = 40 → 40 → 10。"""
        machamp = {"card": MACHAMP, "evolved_from": [MACHOP, MACHOKE], "energy": [FIGHTING] * 4}
        state = apply_command(board(machamp, wartortle={"trainers": [(DEFENDER, TURN)]}), UseAttack(0, 0))
        self.assertEqual([k for k in kinds(state) if k in ("damage", "retaliation", "counterattack")],
                         ["damage", "retaliation", "damage", "counterattack"])
        counter = next(e for e in state.log if e["kind"] == "counterattack")
        self.assertEqual((counter["effect"], counter["total_damage"]), (str(SHELL), 50))
        self.assertEqual(len(triggered(state)), 1)

    def test_turn_player_effects_are_never_active(self):
        """返すダメージを受けるのは番のプレイヤーのポケモンで、その持続する効果がはたらくのは持ち主の相手の番だけ（与えた番 + 1）なので、返す
        ダメージで別の「こうらがえし」「ほのおのかべ」がはたらくことはない（連鎖しない。docs/variable-retaliation-v0.13.md 6 章の B5）。
        番のプレイヤーのポケモンに今の番にはたらく効果がある盤面は、不変条件の違反（持ち主の番でない番に与えている）。"""
        broken = build_test_state([
            {"active": {**DARK, "energy": [WATER], "retaliation_received": TURN - 1}, "bench": [RATTATA]},
            {"active": {**DARK, "retaliation_received": TURN - 1}, "bench": [PONYTA]},
        ], turn_number=TURN)
        self.assertTrue(any("持ち主の番でない" in p for p in check_invariants(broken)))


class RemovalAndChainTest(unittest.TestCase):
    """消える契機（S26〜S31）と連鎖（B5）。"""

    def test_shared_removal_for_every_reason(self):
        """ベンチにもどる（にげる・ポケモンいれかえ・ふきとばし）・進化・きぜつ・期限で消すのは、v0.4b からの共通の関数（``remove_persistent_effects``）。
        わるいカメールが効果を持つ間に進化・にげる・ポケモンいれかえをすることはない（効果を与えた番はワザで終わり、持ち主の次の番の前に期限で
        消える。S27〜S30 は対応カードでは起こらない）ので、関数を直接呼んで、受けたダメージの量の効果も同じに消えることを確かめる。"""
        from kyuura_engine.conditions import EVOLVE, FORCED_SWITCH, RETREAT, SWITCH
        from kyuura_engine.persistent import EXPIRED, KNOCK_OUT, remove_persistent_effects
        for reason in (EVOLVE, RETREAT, SWITCH, FORCED_SWITCH, KNOCK_OUT, EXPIRED):
            with self.subTest(reason=reason):
                state = board(PONYTA_ATTACKER)
                wartortle = state.players[1].active
                remove_persistent_effects(state, 1, wartortle, reason)
                self.assertEqual(wartortle.persistent_effects, ())
                event = state.log[-1]
                self.assertEqual((event["kind"], event["persistent_effect"], event["reason"]), ("persistent_effect_removed", RECEIVED_KIND, reason))

    def test_chain_is_refused_even_in_a_broken_state(self):
        """番のプレイヤーのポケモンに今の番にはたらく効果がある壊れた盤面（不変条件の違反）でワザを使うと、返すダメージで別の効果がはたらく
        ところで、回数の上限ではなくエンジンの不具合として止まる（RuntimeError）。渡した状態は変わらない。"""
        state = build_test_state([
            {"active": {**DARK, "energy": [WATER], "retaliation_received": TURN - 1}, "bench": [RATTATA]},
            {"active": {**DARK, "retaliation_received": TURN - 1}, "bench": [PONYTA]},
        ], turn_number=TURN)
        before = full(state)
        with self.assertRaisesRegex(RuntimeError, "番の進み方の前提"):
            apply_command(with_coin_results(state, H, H), UseAttack(0, 0))
        self.assertEqual(full(state), before)


class OrderTest(unittest.TestCase):
    """返す時点（S34・S35・S38・S40・S41）: 相手のワザのダメージの処理のあと、ダメージ以外の効果の前（p.89。CONFIRMED）。"""

    def test_before_the_poison_coin(self):
        """どくばり（10。「おもて」ならどく）: damage → retaliation → 返すダメージ → コイン → どく（S34）。ビードルはどくにならない（S41）。"""
        state = apply_command(with_coin_results(board({"card": WEEDLE, "energy": [GRASS]}), H), UseAttack(0, 0))
        order = [k for k in kinds(state) if k in ("damage", "retaliation", "coin_flip", "special_condition")]
        self.assertEqual(order[-5:], ["damage", "retaliation", "damage", "coin_flip", "special_condition"])
        self.assertEqual(state.players[1].active.conditions.poison is not None, True)
        self.assertIsNone(state.players[0].active.conditions.poison)

    def test_after_the_self_damage(self):
        """でんげき（「うら」なら自分にも 10）: 自分へのダメージの要素のあとに返す（ダメージの処理がすべて終わったところ）。ピカチュウは 10 + 40
        できぜつし、わるいカメール（60 − 20 = 40）はきぜつしない。"""
        state = with_coin_results(board(PIKACHU_ATTACKER, wartortle={"trainers": [(DEFENDER, TURN)]}), T)
        state = apply_command(state, UseAttack(0, 1))
        damages = [e for e in state.log if e["kind"] in ("damage", "retaliation")]
        self.assertEqual([(e["kind"], e.get("target"), e.get("retaliation")) for e in damages[-4:]],
                         [("damage", None, None), ("damage", "self", None), ("retaliation", None, None), ("damage", None, True)])
        self.assertEqual(triggered(state)[0]["received_damage"], 40)
        self.assertEqual([e["player"] for e in state.log if e["kind"] == "knock_out"], [0])

    def test_whirlwind_after_the_return(self):
        """ふきとばし: 返すダメージのあとに相手が入れ替える（p.89 の「ふきとばし」の例。S34・S40）。ベンチにもどったわるいカメールの効果は消える（S26）。"""
        butterfree = {"card": BUTTERFREE, "evolved_from": [CATERPIE, METAPOD], "energy": [GRASS, GRASS]}
        state = apply_command(board(butterfree), UseAttack(0, 0))
        self.assertEqual((state.phase, state.decision.player), (Phase.DECISION, 1))
        self.assertEqual(returned(state)[0]["amount"], 20)
        d = state.decision
        state = apply_command(state, ResolveDecision(d.player, d.id, d.options[:1]))
        removed = [e for e in state.log if e["kind"] == "persistent_effect_removed"]
        self.assertEqual((removed[0]["reason"], removed[0]["persistent_effect"]), ("forced_switch", "retaliation_received_damage"))
        wartortle = next(pk for pk in state.players[1].bench if state.card_def(pk.card).id == DARK_WARTORTLE)
        self.assertEqual(wartortle.persistent_effects, ())

    def test_attacker_knocked_out_still_blows_away_but_skips_its_own_effects(self):
        """返すダメージでワザを使ったポケモンが HP 以上: 相手への効果（ふきとばし）は処理する（S40）。自分への効果（メガドレインの回復）は処理しない
        （S35。p.89 の「スターブーメラン」の例からの一般化。SUPPORTED。v0.10 の C16）。"""
        butterfree = {"card": BUTTERFREE, "evolved_from": [CATERPIE, METAPOD], "damage": 50, "energy": [GRASS] * 4}
        blown = apply_command(board(butterfree), UseAttack(0, 0))
        self.assertEqual((blown.phase, blown.decision.player), (Phase.DECISION, 1))
        self.assertGreaterEqual(blown.players[0].active.damage, 70)
        self.assertEqual(check_invariants(blown), [])
        drained = apply_command(board({**butterfree, "damage": 30}), UseAttack(0, 1))
        self.assertIn("drain_heal_skipped", kinds(drained))
        self.assertEqual(triggered(drained)[0]["received_damage"], 40)

    def test_fire_wall_knocked_out_by_the_return_gets_no_effect_but_can_use_phoenix(self):
        """R団のファイヤーのほのおのかべ（40）: 返す 40 で HP 以上 → 自分への持続する効果は与えない（S35。persistent_effect_skipped）。きぜつの処理の
        あと、サイドを取るのはわるいカメールの持ち主、そのあと「ふしちょう」を使うかを R団のファイヤーの持ち主が決める（v0.12）。"""
        moltres = {"card": ROCKETS_MOLTRES, "damage": 20, "energy": [FIRE] * 3}
        state = apply_command(board(moltres), UseAttack(0, 0))
        skipped = next(e for e in state.log if e["kind"] == "persistent_effect_skipped")
        self.assertEqual((skipped["persistent_effect"], skipped["reason"]), ("retaliation", "knocked_out"))
        self.assertEqual((state.phase, state.decision.player), (Phase.TAKE_PRIZE, 1))
        state = apply_command(state, TakePrize(1, 0))
        self.assertEqual((state.decision.kind, state.decision.player), (POST_KNOCKOUT_POWER, 0))


class StarBoomerang(AttackEffect):
    """テスト専用: カスミのヒトデマン（p.111。LV.16／HP40・水・弱点 雷）の「スターブーメラン」（20。「コインを投げて「おもて」なら、自分と
    自分についているすべてのカードを手札にもどす。」）の、コインが「おもて」の場合を模した効果（D2。p.89 のワザ解説の例）。

    第1弾のヒトデマン（PMCG1-025。HP 40・水・弱点 雷。ひらてうち 20）の位置 0 に登録する。手札にもどす処理（とバトル場の補充）は v0.13 の
    範囲外で実装しないので、カードは動かさず、「手札にもどす」効果の要素を処理する時点に来たか・そのときの状態を ``calls`` に記録する。
    p.89: 「「スターブーメラン」のダメージを受けたタイミングで、「こうらがえし」の状態によるダメージを与えます。その後、相手はそのダメージで
    きぜつしなければ「スターブーメラン」の効果で手札にもどることになります。」"""

    implementation_id = "test_star_boomerang"
    calls: list = []

    def damage_profile(self, state, use):
        return DamageProfile(opponent=(20,))

    def resolve(self, state, use):
        _, attacker = state.find_pokemon(use.pokemon_id)
        deal_attack_damage(state, use, OPPONENT_ACTIVE, 20)
        finish_damage_elements(state, use)  # 「こうらがえし」（ダメージの処理のあと、効果の前。p.89）
        knocked_out = attacker.damage >= state.card_def(attacker.card).hp
        StarBoomerang.calls.append({
            "log_index": len(state.log),
            "attacker_damage": attacker.damage,
            "returned_before": any(e["kind"] == "retaliation" for e in state.log),
            "return_to_hand": not knocked_out,  # きぜつしていなければ手札にもどる（「おもて」の場合）
        })


class StarBoomerangMockTest(unittest.TestCase):
    """p.89 の「スターブーメラン」の例（D2）。返すのはダメージの処理のあと、手札にもどす効果の前。ワザを使ったポケモンが返すダメージで
    きぜつしたら、手札にもどす効果は処理しない（S38。CONFIRMED）。ほかのワザへの一般化は S35（SUPPORTED）で、このテストの範囲ではない。"""

    def setUp(self):
        StarBoomerang.calls = []
        attack = load_card_pool().get(STARYU).attacks[0]
        self.effects = DEFAULT_EFFECTS.with_attacks("test", {AttackKey(STARYU, 0): AttackEntry(StarBoomerang(), attack.name_ja, attack.text_ja)})

    def staryu(self, damage=0):
        return {"card": STARYU, "energy": [WATER], "damage": damage}

    def test_returns_before_the_hand_effect(self):
        """スターブーメラン 20 → こうらがえし 20 → ヒトデマンはきぜつしない（20 < 40）→ 手札にもどす効果の時点（「おもて」なら手札へ）。"""
        state = board(self.staryu(), effects=self.effects)
        start = len(state.log)
        state = apply_command(state, UseAttack(0, 0))
        self.assertEqual(kinds(state, start)[:4], ["attack", "damage", "retaliation", "damage"])
        call = StarBoomerang.calls[0]
        self.assertEqual((call["returned_before"], call["attacker_damage"], call["return_to_hand"]), (True, 20, True))
        self.assertEqual(call["log_index"], start + 4)  # 返すダメージのログのすぐあと
        self.assertEqual((state.phase, state.turn_number), (Phase.MAIN, TURN + 1))

    def test_knocked_out_by_the_return_does_not_go_to_hand(self):
        """ヒトデマン（ダメージ 20）が返す 20 できぜつ → 手札にもどす効果は処理しない（S38）。きぜつの処理でトラッシュ（エネルギーも）・サイドは
        わるいカメールの持ち主。わるいカメール（20 < 60）はきぜつしない。"""
        state = board(self.staryu(20), effects=self.effects)
        staryu_card = state.players[0].active.card
        energy = state.players[0].active.energy
        state = apply_command(state, UseAttack(0, 0))
        call = StarBoomerang.calls[0]
        self.assertEqual((call["attacker_damage"], call["return_to_hand"]), (40, False))
        self.assertIn(staryu_card, state.players[0].discard)
        self.assertTrue(set(energy) <= set(state.players[0].discard))
        self.assertNotIn(staryu_card, state.players[0].hand)
        self.assertEqual((state.phase, state.decision.player), (Phase.TAKE_PRIZE, 1))
        state = apply_command(state, TakePrize(1, 0))
        self.assertEqual(len(state.players[1].prizes), 5)

    def test_wartortle_knocked_out_and_staryu_survives(self):
        """わるいカメール（ダメージ 40）がスターブーメランできぜつしても返す（S18）。ヒトデマンはきぜつしないので手札にもどす効果の時点に来る。"""
        state = apply_command(board(self.staryu(), wartortle={"damage": 40}, effects=self.effects), UseAttack(0, 0))
        call = StarBoomerang.calls[0]
        self.assertEqual((call["returned_before"], call["return_to_hand"]), (True, True))
        self.assertEqual([e["player"] for e in state.log if e["kind"] == "knock_out"], [1])

    def test_both_knocked_out_is_stopped(self):
        """わるいカメールがスターブーメランで、ヒトデマンが返すダメージで、そろってきぜつしうる → W24 と同じ問い（S37）で宣言の前に止める。"""
        state = board(self.staryu(20), wartortle={"damage": 40}, effects=self.effects)
        before, rng = full(state), rng_fingerprint(state.rng)
        with self.assertRaises(EngineError) as ctx:
            apply_command(state, UseAttack(0, 0))
        self.assertEqual(ctx.exception.code, STOP)
        self.assertEqual((full(state), rng_fingerprint(state.rng)), (before, rng))
        self.assertEqual(StarBoomerang.calls, [])


class DoubleKnockOutTest(unittest.TestCase):
    """S37: わるいカメールがワザのダメージで、ワザを使ったポケモンが返すダメージで、そろってきぜつする（v0.12 の W24 と同じ問い。UNRESOLVED）。"""

    def assert_stopped(self, state, index):
        before, rng = full(state), rng_fingerprint(state.rng)
        with self.assertRaises(EngineError) as ctx:
            apply_command(state, UseAttack(0, index))
        self.assertEqual(ctx.exception.code, STOP)
        self.assertEqual((full(state), rng_fingerprint(state.rng)), (before, rng))
        return ctx.exception

    def test_stopped_before_the_declaration(self):
        """ほのおのしっぽ 30 → わるいカメール（ダメージ 30）がきぜつ → 返す 60 でポニータもきぜつ。新しいコードではなく W24 のコード。"""
        error = self.assert_stopped(board(PONYTA_ATTACKER, wartortle={"damage": 30}), 1)
        self.assertIn("こうらがえし", error.message)

    def test_per_coin_outcome(self):
        """みだれづき（0・10・20）でわるいカメール（ダメージ 50）はきぜつしうる。返すのはその結果の受けたダメージなので、ドードーがダメージ 30 なら
        20 の結果できぜつしうる（止める）、ダメージ 20 ならどの結果でもきぜつしない（受け付ける。コインの結果で受け付けるかは変わらない）。"""
        doduo = {"card": DODUO, "energy": [FIRE]}
        self.assert_stopped(board({**doduo, "damage": 30}, wartortle={"damage": 50}), 0)
        for coins in itertools.product((H, T), repeat=2):
            with self.subTest(coins=coins):
                state = apply_command(with_coin_results(board({**doduo, "damage": 20}, wartortle={"damage": 50}), *coins), UseAttack(0, 0))
                self.assertEqual(check_invariants(state), [])

    def test_hurricane_punch_is_always_stopped(self):
        """ハリケーンパンチ（0〜120）: 120 でわるいカメールがきぜつし、返す 120 でサカキのカイリキー（HP 100）もきぜつしうるので、ダメージ 0 でも止める。
        「こんじょう」で解決したことにしない（v0.11 の G39）。"""
        giovanni = {"card": GIOVANNIS_MACHAMP, "evolved_from": [GIOVANNIS_MACHOP, GIOVANNIS_MACHOKE], "energy": [FIGHTING] * 4}
        self.assert_stopped(board(giovanni), 0)

    def test_not_stopped_when_only_one_is_knocked_out(self):
        """片方だけきぜつするなら止めない（過剰に止めない）: ちょうねんりき 50 で、わるいカメール（ダメージ 0）はきぜつせず、ユンゲラー（ダメージ 10）
        は返す 50 できぜつする。"""
        state = apply_command(board({**KADABRA_ATTACKER, "damage": 10}), UseAttack(0, 1))
        self.assertEqual([e["player"] for e in state.log if e["kind"] == "knock_out"], [0])


class InteractionTest(unittest.TestCase):
    """ほかの特殊能力・効果との組み合わせ（D3）。"""

    def test_guts_of_the_turn_player_after_the_return(self):
        """返すダメージで番のプレイヤーのサカキのカイリキーが HP 以上 → 番のプレイヤーが「こんじょう」を使うか決める（v0.12 の W26 と同じ。SUPPORTED）。
        ハリケーンパンチでは S37 で止まるので、テスト専用の効果（相手に 40）を同じ位置に登録して確かめる。"""
        attack = load_card_pool().get(GIOVANNIS_MACHAMP).attacks[0]

        class Punch(AttackEffect):
            implementation_id = "test_punch"

            def damage_profile(self, state, use):
                return DamageProfile(opponent=(40,))

            def resolve(self, state, use):
                deal_attack_damage(state, use, OPPONENT_ACTIVE, 40)

        effects = DEFAULT_EFFECTS.with_attacks("test", {AttackKey(GIOVANNIS_MACHAMP, 0): AttackEntry(Punch(), attack.name_ja, attack.text_ja)})
        giovanni = {"card": GIOVANNIS_MACHAMP, "evolved_from": [GIOVANNIS_MACHOP, GIOVANNIS_MACHOKE], "damage": 70, "energy": [FIGHTING] * 4}
        state = apply_command(with_coin_results(board(giovanni, effects=effects), H), UseAttack(0, 0))
        d = state.decision
        self.assertEqual((d.kind, d.player), (KO_PREVENTION, 0))
        self.assertEqual(check_invariants(state), [])
        state = apply_command(state, ResolveDecision(0, d.id, d.options))
        self.assertIn("ko_prevented", kinds(state))
        self.assertEqual(state.players[0].active.damage, 90)

    def test_chemical_gas_does_not_stop_it(self):
        """かがくへんかガスは特殊能力だけを消す（ワザの効果は消さない。S32 と同じ考え）。どちらの場のベトベトンでも返す。"""
        muk = {"card": MUK, "evolved_from": GRIMER}
        for side in (0, 1):
            with self.subTest(side=side):
                state = board(PONYTA_ATTACKER, attacker_bench=[muk] if side == 0 else [RATTATA], wartortle_bench=[muk] if side == 1 else [PONYTA])
                state = apply_command(state, UseAttack(0, 1))
                self.assertEqual(returned(state)[0]["amount"], 60)

    def test_special_conditions_of_the_wartortle_do_not_stop_it(self):
        """わるいカメールが特殊状態でも返す（S32。p.322「持続する効果」は特殊状態と重複する）。"""
        for condition in ({"sleep": True}, {"paralysis": 6}, {"confusion": True}, {"poison": 10}):
            with self.subTest(condition=condition):
                state = apply_command(board(PONYTA_ATTACKER, wartortle=condition), UseAttack(0, 1))
                self.assertEqual(returned(state)[0]["amount"], 60)

    def test_damage_swap_is_not_damage(self):
        """ダメージカウンターの移動は「ダメージを受けた」ことにならない（p.320）。フーディンの持ち主が自分のポケモンのあいだで動かしても返さない。
        そのあとのあやしいひかり 30 → 30 を返す（フーディンのダメージは 10 + 30）。"""
        state = board({"card": ALAKAZAM, "evolved_from": [ABRA, KADABRA], "energy": [PSYCHIC] * 3},
                      attacker_bench=[{"card": KADABRA, "evolved_from": ABRA, "damage": 20}])
        alakazam, kadabra = state.players[0].active, state.players[0].bench[0]
        state = apply_command(state, UsePokemonPower(0, alakazam.pokemon_id, 0, source=kadabra.pokemon_id, target=alakazam.pokemon_id))
        self.assertEqual(triggered(state), [])
        state = apply_command(with_coin_results(state, T), UseAttack(0, 0))
        self.assertEqual(triggered(state)[0]["received_damage"], 30)
        self.assertEqual(state.players[0].active.damage, 40)

    def test_energy_powers_are_not_damage(self):
        """エナジートランス・あまごいはダメージを与えないので返さない。そのあとのワザのダメージだけを返す（ソーラービーム 60 → わるいカメールは
        きぜつ・60 を返す。ハイドロポンプ 40 + 10 → 50 を返す）。"""
        venusaur = {"card": VENUSAUR, "evolved_from": [BULBASAUR, IVYSAUR], "energy": [GRASS] * 3}
        state = board(venusaur, attacker_bench=[{"card": BULBASAUR, "energy": [GRASS]}])
        bulbasaur = state.players[0].bench[0]
        state = apply_command(state, UsePokemonPower(0, state.players[0].active.pokemon_id, 0, energy=bulbasaur.energy[0],
                                                     source=bulbasaur.pokemon_id, target=state.players[0].active.pokemon_id))
        self.assertEqual(triggered(state), [])
        state = apply_command(state, UseAttack(0, 0))
        self.assertEqual((triggered(state)[0]["received_damage"], returned(state)[0]["amount"]), (60, 60))
        blastoise = {"card": BLASTOISE, "evolved_from": [SQUIRTLE, WARTORTLE], "energy": [WATER] * 3}
        state = build_test_state([
            {"active": blastoise, "bench": [RATTATA], "hand": [WATER]},
            {"active": {**DARK, "retaliation_received": TURN - 1}, "bench": [PONYTA]},
        ], turn_number=TURN)
        state = apply_command(state, UsePokemonPower(0, state.players[0].active.pokemon_id, 0, energy=state.players[0].hand[0],
                                                     target=state.players[0].active.pokemon_id))
        self.assertEqual(triggered(state), [])
        state = apply_command(state, UseAttack(0, 0))
        self.assertEqual(triggered(state)[0]["received_damage"], 50)

    def test_fire_wall_and_shell_attack_in_turn(self):
        """固定の量（ほのおのかべ）と受けたダメージの量（こうらがえし）が同じ仕組みで動く: 7 番に R団のファイヤーがほのおのかべ 40 → わるいカメールが
        40 を返す → R団のファイヤーに効果（8 番にはたらく）。8 番にわるいカメールがおうふくびんた 20 → ほのおのかべは受けた量に関わらず 10 を返す。"""
        moltres = {"card": ROCKETS_MOLTRES, "energy": [FIRE] * 3}
        state = board(moltres, wartortle={"energy": [WATER]})
        state = apply_command(state, UseAttack(0, 0))
        self.assertEqual((triggered(state)[0]["received_damage"], returned(state)[0]["amount"]), (40, 40))
        fire_wall = state.players[0].active.persistent_effects
        self.assertEqual([(e.kind, e.amount, e.basis) for e in fire_wall], [("retaliation", 10, RETALIATION_FIXED)])
        state = apply_command(with_coin_results(state, H, H), UseAttack(1, 0))
        event = triggered(state)[-1]
        self.assertEqual((event["amount"], event["effect"]), (10, f"{ROCKETS_MOLTRES}#0"))
        self.assertNotIn("basis", event)
        self.assertNotIn("received_damage", event)
        self.assertEqual(returned(state)[-1]["amount"], 10)


class AtomicityTest(unittest.TestCase):
    """不正な操作・止めた操作・エンジンの不具合として止まる操作で、状態・ログ・乱数が変わらない（D4）。"""

    def test_invalid_commands_change_nothing(self):
        state = board({**PONYTA_ATTACKER, "energy": [FIRE]})
        before, rng = full(state), rng_fingerprint(state.rng)
        for command in (UseAttack(0, 1), UseAttack(1, 0), UseAttack(1, 1), Retreat(0, (), 0), UsePokemonPower(0, 1, 0), EndTurn(1)):
            with self.subTest(command=command):
                with self.assertRaises(EngineError):
                    apply_command(state, command)
                self.assertEqual((full(state), rng_fingerprint(state.rng)), (before, rng))

    def test_two_damage_elements_are_refused_without_a_partial_state(self):
        """1 つのワザで、効果がはたらいているポケモンが 2 回ダメージを受ける場合（S7）は、エンジンは推測で返さずに止める（v0.12 から。C34・C35 と
        同じ問い）。v0.30 までは対応カードで起こらないので RuntimeError にしていた。v0.31 で複数のポケモンにダメージを与えるワザを加えたので、
        同じ問いにコード ``UNRESOLVED_MULTIPLE_DAMAGE_TRIGGERS`` を付けた（分類は変えていない）。渡した状態は変わらない。"""
        attack = load_card_pool().get(PONYTA).attacks[1]

        class TwoHits(AttackEffect):
            implementation_id = "test_two_hits"

            def damage_profile(self, state, use):
                return DamageProfile(opponent=(10,))

            def resolve(self, state, use):
                deal_attack_damage(state, use, OPPONENT_ACTIVE, 10)
                deal_attack_damage(state, use, OPPONENT_ACTIVE, 10)

        effects = DEFAULT_EFFECTS.with_attacks("test", {AttackKey(PONYTA, 1): AttackEntry(TwoHits(), attack.name_ja, attack.text_ja)})
        state = board(PONYTA_ATTACKER, effects=effects)
        before, rng = full(state), rng_fingerprint(state.rng)
        with self.assertRaises(UnsupportedError) as caught:
            apply_command(state, UseAttack(0, 1))
        self.assertEqual(caught.exception.code, "UNRESOLVED_MULTIPLE_DAMAGE_TRIGGERS")
        self.assertEqual((full(state), rng_fingerprint(state.rng)), (before, rng))


class SaveRestoreAndInvariantTest(unittest.TestCase):
    """効果がある状態の保存・復元（D5）・書き出し・不変条件。"""

    def assert_same_after_copy(self, state, commands):
        for copied in (pickle.loads(pickle.dumps(state)), copy.deepcopy(state), state.clone()):
            with self.subTest(kind=type(copied).__name__):
                self.assertEqual(full(copied), full(state))
                for command in commands:
                    try:
                        expected = full(apply_command(state, command))
                    except EngineError as error:
                        with self.assertRaises(EngineError) as ctx:
                            apply_command(copied, command)
                        self.assertEqual(ctx.exception.code, error.code)
                        continue
                    self.assertEqual(full(apply_command(copied, command)), expected)

    def test_variable_only(self):
        """受けたダメージの量の効果だけ: 返す直前（ワザ）・期限の直前（番の終わり）。"""
        self.assert_same_after_copy(board(PONYTA_ATTACKER), [UseAttack(0, 1), UseAttack(0, 0), EndTurn(0)])

    def test_fixed_and_variable(self):
        """固定（ほのおのかべ）と受けたダメージの量（こうらがえし）の効果が両方ある状態（盤面を直接作った。自然な対戦では、ワザで番が終わるので、
        両方がある状態は外から見えない）。"""
        state = build_test_state([
            {"active": {"card": ROCKETS_MOLTRES, "energy": [FIRE] * 3, "retaliation": TURN}, "bench": [RATTATA]},
            {"active": {**DARK, "retaliation_received": TURN - 1}, "bench": [PONYTA]},
        ], turn_number=TURN)
        self.assertEqual(check_invariants(state), [])
        self.assertEqual({e.kind for p in state.players for e in p.active.persistent_effects}, {"retaliation", "retaliation_received_damage"})
        self.assert_same_after_copy(state, [EndTurn(0)])

    def test_after_the_return_and_knock_out(self):
        """返したあと・きぜつの処理の途中（サイドを取る決定）。"""
        state = apply_command(board(PONYTA_ATTACKER), UseAttack(0, 1))
        self.assertEqual(state.phase, Phase.TAKE_PRIZE)
        self.assert_same_after_copy(state, [TakePrize(1, 0)])

    def test_before_the_unresolved_stop(self):
        """止める直前（S37）: 復元しても同じコードで止まり、状態は変わらない。"""
        self.assert_same_after_copy(board(PONYTA_ATTACKER, wartortle={"damage": 30}), [UseAttack(0, 1), UseAttack(0, 0)])

    def test_serialization(self):
        """形式 8・9 は種類 ``retaliation_received_damage`` に ``attack_index`` だけを加える（量は書かない。形式 9 のまま）。形式 1〜7 は ValueError。"""
        state = board(PONYTA_ATTACKER)
        effect = state_to_dict(state, format_version=9)["players"][1]["active"]["persistent_effects"]
        self.assertEqual(effect, [{"effect": "retaliation_received_damage", "source_card": state.players[1].active.card,
                                   "source_card_id": DARK_WARTORTLE, "source_player": 1, "created_turn": TURN - 1, "active_turn": TURN,
                                   "attack_index": 1}])
        for version in range(1, 8):
            with self.assertRaises(ValueError):
                state_to_dict(state, format_version=version)
        self.assertEqual(serialization_problems(state), [])

    def test_value_checks(self):
        """決め方と量の組は型が確かめる: 決まった量は量が要り、受けたダメージの量は量を持たない。知らない決め方は作れない。"""
        with self.assertRaises(ValueError):
            Retaliation(1, 0, 5, 6, 1, 10, RETALIATION_RECEIVED)
        with self.assertRaises(ValueError):
            Retaliation(1, 0, 5, 6, 0, None)
        with self.assertRaises(ValueError):
            Retaliation(1, 0, 5, 6, 0, 10, "double")
        effect = Retaliation(1, 0, 5, 6, 1, None, RETALIATION_RECEIVED)
        self.assertEqual((effect.kind, effect.base_damage(70)), ("retaliation_received_damage", 70))
        self.assertEqual((Retaliation(1, 0, 5, 6, 0, 10).kind, Retaliation(1, 0, 5, 6, 0, 10).base_damage(70)), ("retaliation", 10))

    def test_invariants(self):
        """決め方・ワザの位置・はたらく番が登録と違う効果は、不変条件の違反（「ほのおのかべ」と取りちがえない）。"""
        state = board(PONYTA_ATTACKER)
        for change in ({"basis": RETALIATION_FIXED, "amount": 10}, {"attack_index": 0}, {"active_turn": TURN + 1}):
            broken = state.clone()
            target = broken.players[1].active
            target.persistent_effects = (dataclasses.replace(target.persistent_effects[0], **change),)
            with self.subTest(change=change):
                self.assertNotEqual(check_invariants(broken), [])
        self.assertEqual(check_invariants(state), [])


if __name__ == "__main__":
    unittest.main()

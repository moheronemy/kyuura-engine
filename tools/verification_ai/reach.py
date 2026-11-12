"""到達目的の方策 reach（版 1・版 2。docs/verification-ai-reach-policy.md 3 章・12 章・14 章・15 章）。

目標（P6・U-R3a）に当たる候補・段の選べるものを先に選び、ほかは rules-v2（``RulePolicy`` の版 2）で選ぶ。方策が決めるのは、ランナーが渡した範囲の中の候補と、
行動生成が渡した段の選べるものの位置（選好）と、送る前の評価で送らないことだけ。合法性・費用・受理を判定しない。

- 読むのは、候補・段の契約の値（種類・理由・``face_down``・段の数・``role``・``decision_kind``・選べるものの ``card_id``）、本人の観測（自分の場の ``face_down`` の位置・
  手札の ``card_id``・区間と番の番号・番のプレイヤー）、計画の設定（``config.reach``）だけ。観測の ``real``・相手の秘密・エンジンの状態と乱数は読まない
- ``kyuura_engine`` を import しない。カード ID は設定の値として照らすだけ（共通の行動生成・範囲・判定に分岐を加えない）
- 目標の試行は、両方の主体を合わせて 1 局 1 回（``ReachBudget``。実行の制御）。数えるのは、ランナーが目標の操作の submit を実際に呼んだあとの通知（``notify_submit``）だけ
- 試行を使ったあと・保護の期間を使い切ったあとは、rules-v2 と同じ選び方・プロファイル deep の範囲（``scope_profile``）に戻る

版 2（設定の ``version`` が 2。版 1 の設定は版 1 と同じ選び方・同じ乱数の使い方のまま）:

- V2-a: R2（秘策を優先）は両方の目標で、手札に ``place_cards`` があるときだけ（なければ R2 を当てず rules-v2 の順位）
- V2-c: ``target_input_cards`` が空でないとき、本人の観測で、おもての自分のポケモンにそのカードがついているのが見えるときだけ R0。見えないあいだ、目標の候補は
  ``DEMOTED_RANK``（end_turn より後ろ）へ下げる（候補を除かない。下げた候補しか残らなければ選ぶ）
- V2-d: R0 の段で、選べるものの参照（``pokemon``・``card``）が本人の観測の参照と一致する、そのカードとそれがついたおもてのポケモンを優先する。参照が欠ける・
  一致しない・あいまい（同じ参照が 2 つ）なら推測せず均等（既存の通常の入力生成と同じ）。前の段で選んだポケモンについていないカードは優先しない
- 準備が見えても、特殊状態・使用回数・同じポケモン・エネルギーの種類などで拒否されることはありうる（方策は能力の合法性を確かめない。エンジンが決める）
"""

from __future__ import annotations

import json
from typing import Any

from .policies import DEMOTED_RANK, PRIORITY, REPEAT_THRESHOLD, STAGE, RulePolicy, UniformPolicy, candidate_identity, turn_of

REACH_NAME = "reach"
REACH_VERSION = 1
REACH_DISTRIBUTION = "reach-v1-goal+rules-v2-candidate+uniform-stage"
REACH_VERSION_2 = 2
REACH_DISTRIBUTION_2 = "reach-v2-goal+rules-v2-candidate+target-input-stage"
DISTRIBUTIONS = {REACH_VERSION: REACH_DISTRIBUTION, REACH_VERSION_2: REACH_DISTRIBUTION_2}
GOALS = ("p6", "u_r3a")
FACE_DOWN_REASON = "face_down_reveal_not_evaluated"  # judge.FACE_DOWN_REASON と同じ値（テストで一致を確かめる）
PROFILE_REACH, PROFILE_BASE = "boundary", "deep"
SETTING_KEYS = ("goal", "version", "place_trainers", "place_cards", "move_to_active", "protect_own_turns", "tries_per_game", "base")  # 版 1
SETTING_KEYS_2 = SETTING_KEYS + ("target_input_cards",)  # 版 2
KEYS_BY_VERSION = {REACH_VERSION: SETTING_KEYS, REACH_VERSION_2: SETTING_KEYS_2}
MAX_PROTECT_TURNS = 10


class ReachSettingsError(ValueError):
    pass


def validate_settings(settings: Any) -> dict[str, Any]:
    """reach の設定の厳密な検証（知らない版・項目・型・値を拒否する。版を読み替えない）。正規化した写しを返す。"""
    if not isinstance(settings, dict):
        raise ReachSettingsError(f"reach の設定がオブジェクトでない: {settings!r}")
    version = settings.get("version")
    if type(version) is not int or version not in KEYS_BY_VERSION:
        raise ReachSettingsError(f"version {version!r} は {sorted(KEYS_BY_VERSION)} のどれでもない")
    keys = KEYS_BY_VERSION[version]
    problems = []
    unknown = sorted(set(settings) - set(keys))
    missing = [k for k in keys if k not in settings]
    if unknown:
        problems.append(f"知らない項目 {unknown}")
    if missing:
        problems.append(f"項目がない {missing}")
    if problems:
        raise ReachSettingsError("; ".join(problems))
    goal = settings["goal"]
    if goal not in GOALS:
        problems.append(f"goal {goal!r} は {list(GOALS)} のどれでもない")
    for key in ("place_trainers", "place_cards") + (("target_input_cards",) if version == REACH_VERSION_2 else ()):
        value = settings[key]
        if not isinstance(value, list) or not all(isinstance(v, str) and v for v in value) or len(set(value)) != len(value):
            problems.append(f"{key} は重ならない文字列の並びでない: {value!r}")
    if isinstance(settings["place_trainers"], list) and not settings["place_trainers"]:
        problems.append("place_trainers が空")
    if goal == "u_r3a" and isinstance(settings["place_cards"], list) and not settings["place_cards"]:
        problems.append("u_r3a の place_cards が空（対象のカードを計画で指定する）")
    if version == REACH_VERSION_2:
        if goal == "p6" and isinstance(settings["place_cards"], list) and not settings["place_cards"]:
            problems.append("版 2 の p6 の place_cards が空（対象のたねポケモンを計画で指定する）")
        if goal == "p6" and isinstance(settings["target_input_cards"], list) and settings["target_input_cards"]:
            problems.append("版 2 の p6 の target_input_cards は空だけ（目標の操作の入力を変えない）")
    if type(settings["move_to_active"]) is not bool:
        problems.append("move_to_active が真偽値でない")
    elif goal == "u_r3a" and settings["move_to_active"]:
        problems.append("u_r3a はバトル場への移動を求めない（move_to_active は偽）")
    turns = settings["protect_own_turns"]
    if type(turns) is not int or not 1 <= turns <= MAX_PROTECT_TURNS:
        problems.append(f"protect_own_turns {turns!r} は 1〜{MAX_PROTECT_TURNS} の整数でない")
    if settings["tries_per_game"] != 1 or type(settings["tries_per_game"]) is not int:
        problems.append(f"tries_per_game {settings['tries_per_game']!r} は 1 でない（両方の主体を合わせて 1 局 1 回）")
    if settings["base"] != "rules-v2":
        problems.append(f"base {settings['base']!r} は rules-v2 でない")
    if problems:
        raise ReachSettingsError("; ".join(problems))
    return json.loads(json.dumps(settings))


def is_p6_candidate(candidate: dict[str, Any]) -> bool:
    """P6（本人のうらのバトル場のポケモンのにげる）の候補か。契約の値だけ: にげるで、理由に face_down_reveal_not_evaluated（うらの分岐だけが付ける）。"""
    return candidate.get("kind") == "retreat" and FACE_DOWN_REASON in (candidate.get("reasons") or [])


def is_u_r3a_candidate(candidate: dict[str, Any]) -> bool:
    """U-R3a（本人のうらのカードの、宣言の段が 2〜3 段の特殊能力）の候補か。judge.is_face_down_power と同じ条件に、入力の段の数 2〜3 を加える。"""
    return (candidate.get("kind") == "use_power" and (candidate.get("power") or {}).get("face_down") is True
            and (candidate.get("pokemon") or {}).get("face_down") is True and FACE_DOWN_REASON in (candidate.get("reasons") or [])
            and 2 <= len(candidate.get("input_stages") or []) <= 3)


def is_target(goal: str, candidate: dict[str, Any]) -> bool:
    return is_p6_candidate(candidate) if goal == "p6" else is_u_r3a_candidate(candidate)


def is_normal_retreat(candidate: dict[str, Any]) -> bool:
    return candidate.get("kind") == "retreat" and not is_p6_candidate(candidate)


def key_designates_face_down(key: str) -> bool:
    """同じ意味の操作の鍵（policies.action_key）の入力に、face_down の選べるもの（場のうらのカード）があるか。"""
    try:
        parts = json.loads(key).get("input") or []
    except (ValueError, AttributeError):
        return False
    return any(isinstance(item, dict) and item.get("face_down") is True for part in parts for item in part.get("items") or [])


def key_card_ids(key: str) -> list[str]:
    try:
        parts = json.loads(key).get("input") or []
    except (ValueError, AttributeError):
        return []
    return [item.get("card_id") for part in parts for item in part.get("items") or [] if isinstance(item, dict) and item.get("card_id")]


def own_input_references(me: dict[str, Any], cards: list[str]) -> dict[str, Any]:
    """版 2 の準備（V2-c・V2-d）: 本人の観測の自分の場の、おもてのポケモン（``face_down`` が真でない）についている ``cards`` のカードの参照。

    返すもの: ``hosts`` はポケモンの番号 → (カードの参照 ``card``, ``card_id``)、``energy`` はカードの参照 → (ついているポケモンの番号, ``card_id``)。
    参照が整数でない・欠ける項目、同じ参照が 2 回出る項目（あいまい）は入れない（推測しない）。うらのポケモンと ``real`` は読まない。"""
    entries = [me.get("active")] + list(me.get("bench") or [])
    pokemon: dict[int, tuple[int, str]] = {}
    seen_pokemon: set[int] = set()
    energy: dict[int, tuple[int, str]] = {}
    seen_energy: set[int] = set()
    for entry in entries:
        if not isinstance(entry, dict) or entry.get("face_down") is True:
            continue
        pid, card, cid = entry.get("pokemon_id"), entry.get("card"), entry.get("card_id")
        if type(pid) is not int or type(card) is not int or not isinstance(cid, str):
            continue
        if pid in seen_pokemon:
            pokemon.pop(pid, None)
            continue
        seen_pokemon.add(pid)
        pokemon[pid] = (card, cid)
        for e in entry.get("energy") or []:
            if not isinstance(e, dict) or type(e.get("card")) is not int or e.get("card_id") not in cards:
                continue
            if e["card"] in seen_energy:
                energy.pop(e["card"], None)
                continue
            seen_energy.add(e["card"])
            energy[e["card"]] = (pid, e["card_id"])
    energy = {k: v for k, v in energy.items() if v[0] in pokemon}
    hosts = {pid: pokemon[pid] for pid in sorted({v[0] for v in energy.values()})}
    return {"hosts": hosts, "energy": energy}


class ReachBudget:
    """局ごとの目標の試行の回数（実行の制御。両方の主体の reach の方策が同じものを持つ）。持つのは上限と使った回数だけで、送った操作の中身・submit の結果・主体を持たない。"""

    def __init__(self, tries: int):
        self.tries = tries
        self.used = 0

    def exhausted(self) -> bool:
        return self.used >= self.tries

    def use(self) -> None:
        self.used += 1


class ReachPolicy(RulePolicy):
    """到達目的の方策（版 1・版 2。設定の ``version`` で決める）。土台は rules-v2（RulePolicy の版 2・閾値 ``threshold``）。``actor`` は本人のプレイヤーの番号
    （観測の自分の場を読むため）。"""

    name = REACH_NAME

    def __init__(self, seed: str, distribution: str = STAGE, *, actor: int, settings: dict[str, Any], budget: ReachBudget,
                 threshold: int = REPEAT_THRESHOLD):
        super().__init__(seed, version=2, threshold=threshold)
        self.reach = validate_settings(settings)
        if actor not in (0, 1):
            raise ReachSettingsError(f"actor {actor!r} は 0 か 1 でない")
        self.version = self.reach["version"]
        self.rules_version = 2
        self.distribution = DISTRIBUTIONS[self.version]
        self.actor = actor
        self.goal = self.reach["goal"]
        self.budget = budget
        # 保護の期間（主体ごと）: 最初に保護した自分の番を 1 番目、次の自分の番へ移るたびに 1 増やす。うらのカードが消えても数え直さない
        self.protect_turns = 0
        self.last_own_turn = None
        self.expired = False
        self.target_submits = 0  # この主体が目標の操作の submit を呼んだ回数（通知で数える）
        self.rule_turn = {"R1": None, "R2": None}  # R1・R2 を使った番（番に 1 回）
        self.vetoes = 0
        self.step: tuple[str, str] | None = None  # このエピソードで選んだ候補の規則と候補の番号
        self.fd = {"active": False, "bench": 0}
        self.hand: list[str] = []
        self.own_turn = False
        self.turn = None
        # 版 2: 本人の観測の準備（target_input_cards がおもての自分のポケモンについているか）と、R0 の段で前に選んだポケモンの番号（このエピソードだけ）
        self.inputs: dict[str, dict] = {"hosts": {}, "energy": {}}
        self.r0_pokemon = None

    # ---------------------------------------------------------------- 状態

    def active(self) -> bool:
        return not self.budget.exhausted() and not self.expired

    def v2(self) -> bool:
        return self.version == REACH_VERSION_2

    def input_ready(self) -> bool:
        """V2-c: 目標の操作を R0 で選ぶ準備が本人の観測で見えるか（target_input_cards が空なら常に真。版 1 は常に真）。"""
        return not (self.v2() and self.reach["target_input_cards"]) or bool(self.inputs["energy"])

    def protecting(self) -> bool:
        return self.active() and self.protect_turns > 0 and (self.fd["active"] or self.fd["bench"] > 0)

    def _refresh(self, view: dict[str, Any] | None) -> None:
        """本人の観測から自分のうらのカードの位置・手札・番を読み、保護の期間を進める（同じ番では増えない。何度呼んでも同じ）。"""
        if not isinstance(view, dict):
            return
        obs = view.get("observation") or {}
        players = obs.get("players") or []
        me = players[self.actor] if len(players) > self.actor and isinstance(players[self.actor], dict) else {}
        active = me.get("active") or {}
        bench = me.get("bench") or []
        self.fd = {"active": bool(active.get("face_down")), "bench": sum(1 for b in bench if isinstance(b, dict) and b.get("face_down"))}
        self.hand = [c.get("card_id") for c in ((me.get("hand") or {}).get("cards") or []) if isinstance(c, dict)]
        if self.v2() and self.reach["target_input_cards"]:
            self.inputs = own_input_references(me, self.reach["target_input_cards"])
        self.turn = turn_of(view)
        self.own_turn = obs.get("current_player") == self.actor
        if not self.active() or not self.own_turn:
            return
        if self.protect_turns == 0:
            if self.fd["active"] or self.fd["bench"]:
                self.protect_turns, self.last_own_turn = 1, self.turn
        elif self.turn != self.last_own_turn:
            self.protect_turns += 1
            self.last_own_turn = self.turn
        if self.protect_turns > self.reach["protect_own_turns"]:
            self.expired = True

    def state(self) -> dict[str, Any]:
        out = {"goal": self.goal, "active": self.active(), "budget_used": self.budget.used, "budget_tries": self.budget.tries,
               "target_submits": self.target_submits, "protect_turns": self.protect_turns, "protect_limit": self.reach["protect_own_turns"],
               "expired": self.expired, "vetoes": self.vetoes, "face_down": dict(self.fd)}
        if self.v2():  # 版 2 だけ（版 1 の記録の形を変えない）。参照の値は書かない（数だけ）
            out["version"] = self.version
            out["input_ready"] = self.input_ready()
            out["input_cards_seen"] = len(self.inputs["energy"])
        return out

    def scope_profile(self, view: dict[str, Any]) -> str:
        """範囲のプロファイル（ランナーが候補の範囲を決める前に問う）。目標を試すあいだは boundary、試行を使ったあと・保護を使い切ったあとは deep。"""
        self._refresh(view)
        return PROFILE_REACH if self.active() else PROFILE_BASE

    # ---------------------------------------------------------------- 方策の入口

    def begin_episode(self) -> dict[str, Any]:
        super().begin_episode()
        self.step = None
        self.r0_pokemon = None
        return {"mode": "reach" if self.active() else "rule", "reach": self.state()}

    def choose(self, purpose: str, items: list[Any], context: dict[str, Any]) -> tuple[int, str]:
        if purpose == "candidate":
            self._refresh(context.get("view"))
            if not self.active():
                index, reason = RulePolicy.choose(self, purpose, items, context)
                return index, "reach:off:" + reason
            return self._candidate(items, context)
        if not self.active():
            index, reason = UniformPolicy.choose(self, purpose, items, context)
            return index, "reach:off:" + reason
        return self._stage(purpose, items, context)

    def review(self, candidate: dict[str, Any], key: str, turn) -> dict[str, Any]:
        if not self.active():
            return RulePolicy.review(self, candidate, key, turn)
        if is_target(self.goal, candidate):
            return {"send": True, "reason": "reach:target_send"}  # 数えない（数えるのは submit を呼んだあとの通知）
        cid = candidate_identity(candidate)
        if cid not in self.memory.demoted:
            if self.step is not None and self.step[0] == "R2" and candidate.get("kind") == "play_trainer" \
                    and not set(key_card_ids(key)) & set(self.reach["place_trainers"]):
                return self._veto(cid, "reach:trainer_not_offered")
            if self.protecting() and candidate.get("kind") not in ("answer_decision", "retreat") and key_designates_face_down(key):
                return self._veto(cid, "reach:protect_veto")
        return RulePolicy.review(self, candidate, key, turn)

    def notify_submit(self, candidate: dict[str, Any], key: str) -> None:
        """ランナーが submit を実際に呼んだあとの通知（送った候補と操作の鍵だけ。受理・拒否の結果は渡されない）。目標の操作なら局の 1 回を使う。"""
        if self.active() and is_target(self.goal, candidate):
            self.budget.use()
            self.target_submits += 1

    # ---------------------------------------------------------------- 候補

    def _veto(self, cid: str, reason: str) -> dict[str, Any]:
        self.memory.demoted.add(cid)  # このエピソードでは下げる。下げた候補しか残らなければ rules-v2 の評価で送る（rule2:no_alternative）
        self.vetoes += 1
        return {"send": False, "reason": reason}

    def _pick(self, pool: list[int], reason: str) -> tuple[int, str]:
        if len(pool) == 1:
            return pool[0], reason
        self.draws += 1
        return pool[self._rng.randrange(len(pool))], f"{reason}:tie{len(pool)}"

    def _candidate(self, items: list[Any], context: dict[str, Any]) -> tuple[int, str]:
        if not items:
            raise ValueError("選べるものがない場面で方策を呼んだ（行動生成の誤り）")
        cands = [c if isinstance(c, dict) else {} for c in items]
        demoted = self.memory.demoted
        targets = [i for i, c in enumerate(cands) if is_target(self.goal, c) and candidate_identity(c) not in demoted]
        held: set[str] = set()
        if targets and not self.input_ready():  # V2-c: 準備が見えないあいだは R0 を当てず、目標の候補を下げる（除かない）
            held = {candidate_identity(cands[i]) for i in targets}
        elif targets:
            return self._choose_rule("R0", targets, cands)
        any_fd = self.fd["active"] or self.fd["bench"] > 0
        if (self.goal == "p6" and self.reach["move_to_active"] and self.fd["bench"] and not self.fd["active"] and self.own_turn
                and self.rule_turn["R1"] != self.turn):
            pool = [i for i, c in enumerate(cands) if is_normal_retreat(c) and candidate_identity(c) not in demoted]
            if pool:
                self.rule_turn["R1"] = self.turn
                return self._choose_rule("R1", pool, cands)
        if not any_fd and self.own_turn and self.rule_turn["R2"] != self.turn and set(self.hand) & set(self.reach["place_trainers"]) \
                and ((self.goal != "u_r3a" and not self.v2()) or set(self.hand) & set(self.reach["place_cards"])):  # V2-a: 版 2 は両方の目標で対象が手札にあるときだけ
            pool = [i for i, c in enumerate(cands) if c.get("kind") == "play_trainer" and candidate_identity(c) not in demoted]
            if pool:
                self.rule_turn["R2"] = self.turn
                return self._choose_rule("R2", pool, cands)
        return self._base(cands, context, held)

    def _choose_rule(self, rule: str, pool: list[int], cands: list[dict[str, Any]]) -> tuple[int, str]:
        index, reason = self._pick(pool, f"reach:{self.goal}:{rule}:{cands[pool[0]].get('kind')}")
        self.step = (rule, cands[index].get("id"))
        return index, reason

    def _base(self, cands: list[dict[str, Any]], context: dict[str, Any], held: set[str] = frozenset()) -> tuple[int, str]:
        """rules-v2 の順位（同じエピソードで下げた候補は end_turn より後ろ）。保護のあいだは reveal_face_down も下げる。``held`` は版 2 で準備が見えない目標の候補
        （end_turn より後ろへ下げる。版 1 は常に空で、版 1 と同じ選び方・同じ乱数の使い方）。"""
        self.step = None
        protect = self.protecting()
        if not protect and not held:
            index, reason = self._rule_candidate(cands, context)
            return index, "reach:base:" + reason
        ranks = []
        for c in cands:
            r = PRIORITY.get(c.get("kind"))
            cid = candidate_identity(c)
            if r is not None and (cid in self.memory.demoted or cid in held or (protect and c.get("kind") == "reveal_face_down")):
                r = DEMOTED_RANK
            ranks.append(r)
        name = "protect" if protect else "hold"
        known = [r for r in ranks if r is not None]
        if not known:
            index, _ = UniformPolicy.choose(self, "candidate", cands, context)
            return index, f"reach:{name}:fallback:no_priority"
        best = min(known)
        pool = [i for i, r in enumerate(ranks) if r == best]
        return self._pick(pool, f"reach:{name}:priority{best}:{cands[pool[0]].get('kind')}")

    # ---------------------------------------------------------------- 段

    def _stage(self, purpose: str, items: list[Any], context: dict[str, Any]) -> tuple[int, str]:
        stage = context.get("stage") or {}
        candidate = context.get("candidate") or {}
        by_id = {o.get("id"): o for o in stage.get("options") or [] if isinstance(o, dict)}
        dk, role = stage.get("decision_kind"), stage.get("role")
        rule = self.step[0] if self.step is not None and self.step[1] == candidate.get("id") else None
        if dk == "secret_plan_card":
            wanted = self._placeable([o for o in by_id.values()])
            if purpose == "count" and all(type(k) is int for k in items):
                want = 1 if wanted else 0
                if want in items:
                    return items.index(want), f"reach:{self.goal}:place:count{want}"
            if purpose == "option" and wanted:
                return self._prefer(purpose, items, context, lambda o: o in wanted, "place:card", by_id)
            return self._uniform(purpose, items, context)
        if rule == "R2" and role == "trainer" and purpose == "option":
            return self._prefer(purpose, items, context, lambda o: o.get("card_id") in self.reach["place_trainers"], "R2:trainer", by_id)
        if rule == "R1" and role == "new_active" and purpose == "option":
            return self._prefer(purpose, items, context, lambda o: o.get("face_down") is True, "R1:face_down_new_active", by_id)
        if dk == "promote_active" and purpose == "option":
            if self.goal == "p6" and self.fd["bench"]:
                return self._prefer(purpose, items, context, lambda o: o.get("face_down") is True, "promote:face_down", by_id)
            return self._uniform(purpose, items, context)
        if rule == "R0":
            if self.v2() and self.reach["target_input_cards"] and purpose == "option":
                return self._input_stage(purpose, items, context, by_id)
            return self._uniform(purpose, items, context)
        if self.protecting() and purpose == "option":
            return self._prefer(purpose, items, context, lambda o: o.get("face_down") is not True, "protect:not_face_down", by_id)
        return self._uniform(purpose, items, context)

    def _input_stage(self, purpose, items, context, by_id) -> tuple[int, str]:
        """V2-d: R0 の段の選べるもの。ポケモンの段（選べるものに ``pokemon``）は対象のカードがついたおもてのポケモン、カードの段は対象のカードそのもの（前の段で
        選んだポケモンについているもの）を、参照（``pokemon``・``card``・``card_id``）が本人の観測と一致するときだけ優先する。合うものがなければ均等。"""
        hosts, energy = self.inputs["hosts"], self.inputs["energy"]

        def host(o):
            pid = o.get("pokemon")
            return (o.get("face_down") is not True and type(pid) is int and pid in hosts
                    and (o.get("card"), o.get("card_id")) == hosts[pid])

        def card(o):
            ref = o.get("card")
            if "pokemon" in o or type(ref) is not int or ref not in energy or o.get("card_id") != energy[ref][1]:
                return False
            return self.r0_pokemon is None or energy[ref][0] == self.r0_pokemon

        if any(isinstance(by_id.get(oid), dict) and "pokemon" in by_id[oid] for oid in items):
            index, reason = self._prefer(purpose, items, context, host, "R0:input_host", by_id)
            chosen = by_id.get(items[index])
            pid = chosen.get("pokemon") if isinstance(chosen, dict) else None
            self.r0_pokemon = pid if type(pid) is int and pid in hosts else -1  # -1: 準備のないポケモンを選んだ（あとの段のカードを優先しない）
            return index, reason
        return self._prefer(purpose, items, context, card, "R0:input_card", by_id)

    def _placeable(self, options: list[dict[str, Any]]) -> list[dict[str, Any]]:
        cards = self.reach["place_cards"]
        return [o for o in options if not cards or o.get("card_id") in cards]

    def _uniform(self, purpose, items, context) -> tuple[int, str]:
        index, reason = UniformPolicy.choose(self, purpose, items, context)
        return index, "reach:stage:" + reason

    def _prefer(self, purpose, items, context, pred, name, by_id) -> tuple[int, str]:
        """選べるもの（番号）のうち、条件に合うものの中で均等に選ぶ。合うものがない・すべて合うなら均等（選好が成り立たない）。"""
        pool = [i for i, oid in enumerate(items) if isinstance(by_id.get(oid), dict) and pred(by_id[oid])]
        if not pool or len(pool) == len(items):
            index, reason = UniformPolicy.choose(self, purpose, items, context)
            return index, f"reach:{name}:{'none' if not pool else 'all'}:" + reason
        return self._pick(pool, f"reach:{self.goal}:{name}")

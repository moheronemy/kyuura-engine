"""決定を出す箇所の走査（U7 の決定の入力の監査。docs/legal-actions-decision-audit.md）。

``scan()`` は、パッケージのソースの AST から、決定を出す呼び出し（``decisions.push_*``・``AttackRun.suspend``・``codec`` の決定・``_boundary_answer``・
``_push_cards``）を集め、決定の種類を解決する（定数・クラス属性とその部分型・既知の動的な出し方）。返す値は (種類, ファイル, クラス, 関数) の組と、
決めるプレイヤー・選べるもの・選ぶ数の上限の式。監査の一覧（``build_legal_actions_api_design.DECISION_SITES``）と照らし、加わった・消えた出し方を見つける
（数ではなく組で照らす）。
"""

from __future__ import annotations

import ast
import pathlib
import sys

PUSHERS = {"push_decision": (None, 1), "push_attack_decision": (None, 1), "push_trainer_decision": (None, 2), "push_power_decision": (None, 2),
           "push_stadium_decision": (None, 1), "attack_decision": (None, None), "ko_check_decision": (None, None), "exp_all_decision": (None, None),
           "suspend": (None, None), "_boundary_answer": (1, 3), "_push_cards": (2, 3), "prize_decision": (None, None), "promote_decision": (None, None),
           "post_knockout_decision": (None, None), "prize_first_decision": (None, None)}
FIXED = {"exp_all_decision": "exp_all_energy", "prize_decision": "take_prize", "promote_decision": "promote_active", "post_knockout_decision": "post_knockout_power",
         "prize_first_decision": "prize_first", "ko_check_decision": "ko_prevention"}

# 種類を値として受け取って出すだけの包み（呼ぶ側の出し方を数える）
WRAPPERS = frozenset({
    ("kyuura_engine/decisions.py", None, "push_attack_decision"), ("kyuura_engine/decisions.py", None, "push_trainer_decision"),
    ("kyuura_engine/decisions.py", None, "push_power_decision"), ("kyuura_engine/decisions.py", None, "push_stadium_decision"),
    ("kyuura_engine/resolution/codec.py", None, "ko_check_decision"), ("kyuura_engine/resolution/codec.py", None, "_make"),
    ("kyuura_engine/resolution/contract.py", "ContractRuntime", "push_decision"), ("kyuura_engine/resolution/programs.py", "AttackRun", "suspend"),
    ("kyuura_engine/resolution/programs.py", None, "_boundary_answer"), ("kyuura_engine/effects.py", "FossilEggRevive", "_push_cards"),
})
# 種類をクラス属性・メソッド・式から決める出し方（コードを読んで決めた種類。走査はこの組と照らす）
DYNAMIC = {
    ("kyuura_engine/effects.py", "TakeFromDiscardTrainer", "_choose"): ("discard_to_deck", "discard_to_deck_top", "recover_trainer"),  # decision_kind() の対応表
    ("kyuura_engine/effects.py", "CoinsTakePokemonOrTrainerFromDiscard", "resolve"): ("recover_pokemon", "recover_trainer"),  # コイン 2 枚の「おもて」の数
    ("kyuura_engine/engine.py", None, "_offer_trainer_reaction"): ("reaction_power",),
    ("kyuura_engine/reactions.py", None, "_run_step"): ("restore",),  # 退避した決定を同じ種類・選べるもので戻す（元の出し方の情報源を引き継ぐ）
    ("kyuura_engine/resolution/programs.py", "EachPlayerRecoversFromDiscard", "decision_kind"): ("discard_to_deck", "recover_pokemon"),
}


def _const_map(root: pathlib.Path) -> dict[str, str]:
    sys.path.insert(0, str(root))
    from kyuura_engine import decisions as Dm

    return {n: v for n, v in vars(Dm).items() if isinstance(v, str) and n.isupper()}


def scan(root: pathlib.Path | None = None) -> list[dict]:
    root = pathlib.Path(__file__).resolve().parent.parent if root is None else root
    const = _const_map(root)
    trees, classes = {}, {}
    for path in sorted((root / "kyuura_engine").rglob("*.py")):
        rel = path.relative_to(root).as_posix()
        trees[rel] = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(trees[rel]):
            if isinstance(node, ast.ClassDef):
                attrs = {}
                for st in node.body:
                    target, value = None, None
                    if isinstance(st, ast.AnnAssign) and isinstance(st.target, ast.Name):
                        target, value = st.target.id, st.value
                    elif isinstance(st, ast.Assign) and len(st.targets) == 1 and isinstance(st.targets[0], ast.Name):
                        target, value = st.targets[0].id, st.value
                    if target and isinstance(value, ast.Name) and value.id in const:
                        attrs[target] = const[value.id]
                bases = [b.id if isinstance(b, ast.Name) else (b.attr if isinstance(b, ast.Attribute) else "") for b in node.bases]
                classes[node.name] = (attrs, bases)

    def subclasses(name):
        found = {name}
        changed = True
        while changed:
            changed = False
            for cname, (_, bases) in classes.items():
                if cname not in found and any(b in found for b in bases):
                    found.add(cname)
                    changed = True
        return found

    def inherited(cname, attr):
        attrs, bases = classes.get(cname, ({}, []))
        if attr in attrs:
            return attrs[attr]
        for b in bases:
            value = inherited(b, attr)
            if value is not None:
                return value
        return None

    sites = []
    for rel, tree in trees.items():
        def visit(node, func=None, cls=None, rel=rel):
            for child in ast.iter_child_nodes(node):
                if isinstance(child, ast.ClassDef):
                    visit(child, func, child.name, rel)
                    continue
                if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    visit(child, child, cls, rel)
                    continue
                if isinstance(child, ast.Call):
                    name = child.func.attr if isinstance(child.func, ast.Attribute) else (child.func.id if isinstance(child.func, ast.Name) else None)
                    key = (rel, cls, None if func is None else func.name)
                    if name in PUSHERS and key not in WRAPPERS:
                        kind_pos, opt_pos = PUSHERS[name]
                        kw = {k.arg: k.value for k in child.keywords if k.arg}
                        kind = kw.get("kind")
                        if kind is None and kind_pos is not None and len(child.args) > kind_pos:
                            kind = child.args[kind_pos]
                        opts = kw.get("options")
                        if opts is None and opt_pos is not None and len(child.args) > opt_pos:
                            opts = child.args[opt_pos]
                        if kind is None and name in FIXED:
                            kinds = (FIXED[name],)
                        elif isinstance(kind, ast.Name) and kind.id in const:
                            kinds = (const[kind.id],)
                        elif isinstance(kind, ast.Attribute) and isinstance(kind.value, ast.Name) and kind.value.id == "self" and cls is not None:
                            kinds = tuple(sorted({v for c in subclasses(cls) if (v := inherited(c, kind.attr)) is not None}))
                            if not kinds and key in DYNAMIC:
                                kinds = DYNAMIC[key]
                            if kind.attr == "decision_kind" and ("kyuura_engine/resolution/programs.py", "EachPlayerRecoversFromDiscard", "decision_kind") in DYNAMIC \
                                    and "EachPlayerRecoversFromDiscard" in subclasses(cls):
                                kinds = tuple(sorted(set(kinds) | set(DYNAMIC[("kyuura_engine/resolution/programs.py", "EachPlayerRecoversFromDiscard", "decision_kind")])))
                        else:
                            kinds = DYNAMIC.get(key, ("dynamic:" + ast.unparse(kind),))
                        player = kw.get("player")
                        if player is None and name == "_boundary_answer" and len(child.args) > 2:
                            player = child.args[2]
                        mx = kw.get("max_choices")
                        for k in kinds:
                            sites.append({"kind": k, "file": rel, "class": cls, "func": None if func is None else func.name, "line": child.lineno,
                                          "player": None if player is None else ast.unparse(player)[:60],
                                          "options": None if opts is None else ast.unparse(opts)[:120],
                                          "max": "1" if mx is None else ast.unparse(mx)[:60]})
                visit(child, func, cls, rel)

        visit(tree)
    return sites


def site_keys(sites: list[dict]) -> set[tuple]:
    return {(s["kind"], s["file"], s["class"], s["func"]) for s in sites}

# 監査の一覧（v0.162。(種類, ファイル, クラス, 関数) → (情報源の区分, 答えの並び)）。--check が走査（scan）の組と照らす。手で書いた判定（コードを読んだ判断）
AUDIT = {
    ('accept_request', 'kyuura_engine/effects.py', 'EachPlayerMayReturnHandThenDrawOnEntry', '_ask'): ('public', 'single'),
    ('accept_request', 'kyuura_engine/effects.py', 'EachPlayerSearchToolOnEntry', '_ask'): ('public', 'single'),
    ('accept_request', 'kyuura_engine/effects.py', 'LookOpponentPrizesMayRedeal', 'resolve'): ('public', 'single'),
    ('accept_request', 'kyuura_engine/effects.py', None, '_ask_opponent'): ('public', 'single'),
    ('accept_request', 'kyuura_engine/effects.py', 'SwapPleaseTrainer', 'resume'): ('public', 'single'),
    ('accept_request', 'kyuura_engine/engine.py', None, '_chaos_tails'): ('public', 'single'),
    ('allocate_damage', 'kyuura_engine/resolution/programs.py', 'AllocateDamage', 'run'): ('public', 'single'),
    ('arrange_deck_top', 'kyuura_engine/effects.py', 'ArrangeOwnDeckTopTrainer', 'resume'): ('started_search', 'significant'),
    ('arrange_deck_top', 'kyuura_engine/effects.py', 'FlashTrainer', '_offer'): ('started_search', 'significant'),
    ('arrange_deck_top', 'kyuura_engine/effects.py', 'ShuffleThenArrangeDeckTop', 'resolve'): ('started_search', 'significant'),
    ('arrange_deck_top', 'kyuura_engine/resolution/programs.py', 'ArrangeDeckTop', '_look'): ('started_search', 'significant'),
    ('attach_from_deck', 'kyuura_engine/effects.py', 'CoinAttachEnergyFromDeckToOwnPokemon', 'resolve'): ('started_search', 'single'),
    ('attach_from_deck', 'kyuura_engine/effects.py', 'CoinAttachFromDeckOnEntry', 'resolve'): ('started_search', 'unconfirmed'),
    ('attach_from_deck', 'kyuura_engine/resolution/programs.py', 'AttachBasicEnergyFromDeckToSelf', 'run'): ('started_search', 'unconfirmed'),
    ('attach_from_deck', 'kyuura_engine/resolution/programs.py', 'AttachFromDeck', 'run'): ('started_search', 'unconfirmed'),
    ('attach_from_deck', 'kyuura_engine/resolution/programs.py', 'AttachFromDeckByHeads', 'run'): ('started_search', 'unconfirmed'),
    ('attach_from_deck', 'kyuura_engine/resolution/programs.py', 'AttachFromDeckToBench', '_bench_first_resume'): ('started_search', 'unconfirmed'),
    ('attach_from_deck', 'kyuura_engine/resolution/programs.py', 'AttachFromDeckToBench', 'run'): ('started_search', 'unconfirmed'),
    ('attach_from_deck', 'kyuura_engine/resolution/programs.py', 'AttachFromDeckUpToNamedCount', 'run'): ('started_search', 'unconfirmed'),
    ('attach_from_discard', 'kyuura_engine/effects.py', 'CoinAttachFromDiscardToTypePokemon', 'resolve'): ('public', 'single'),
    ('attach_from_discard', 'kyuura_engine/resolution/programs.py', 'AttachFromDiscard', 'run'): ('public', 'not_significant'),
    ('attach_from_hand', 'kyuura_engine/resolution/programs.py', 'AttachFromHand', 'run'): ('own_cards', 'not_significant'),
    ('attach_from_hand', 'kyuura_engine/resolution/programs.py', 'AttachFromHandToChosen', 'resume'): ('own_cards', 'not_significant'),
    ('attach_to_bench', 'kyuura_engine/resolution/programs.py', 'AttachFromDeckToBench', '_bench_first_run'): ('public', 'single'),
    ('attach_to_bench', 'kyuura_engine/resolution/programs.py', 'AttachFromDeckToBench', 'resume'): ('public', 'single'),
    ('attach_to_bench', 'kyuura_engine/resolution/programs.py', 'MoveOneEnergyToBench', 'resume'): ('public', 'single'),
    ('attach_to_bench', 'kyuura_engine/resolution/programs.py', 'MoveOwnEnergyToBench', '_next'): ('public', 'single'),
    ('bench_from_deck', 'kyuura_engine/effects.py', 'BenchBasicsFromDeckOnEntry', 'resolve'): ('started_search', 'unconfirmed'),
    ('bench_from_deck', 'kyuura_engine/effects.py', 'BenchNameGroupFromDeckOnEntry', 'resolve'): ('started_search', 'single'),
    ('bench_from_deck', 'kyuura_engine/effects.py', 'BenchNameGroupFromDeckTrainer', 'resolve'): ('started_search', 'single'),
    ('bench_from_deck', 'kyuura_engine/effects.py', 'CoinBenchNamedFromDeck', 'resolve'): ('started_search', 'unconfirmed'),
    ('bench_from_deck', 'kyuura_engine/effects.py', 'CoinBenchOwnerBasicFromDeckStadium', 'activate'): ('started_search', 'single'),
    ('bench_from_deck', 'kyuura_engine/effects.py', 'CoinReviveFromDeck', 'resolve'): ('started_search', 'unconfirmed'),
    ('bench_from_deck', 'kyuura_engine/effects.py', 'EachPlayerMayBenchBasicFromDeck', '_offer'): ('started_search', 'single'),
    ('bench_from_deck', 'kyuura_engine/resolution/programs.py', 'BenchFromDeck', 'run'): ('started_search', 'unconfirmed'),
    ('bench_from_deck', 'kyuura_engine/resolution/programs.py', 'BenchFromDeckAny', 'run'): ('started_search', 'unconfirmed'),
    ('bench_from_deck_or_hand', 'kyuura_engine/effects.py', 'FossilEggRevive', 'resume'): ('started_search', 'single'),
    ('bench_from_discard', 'kyuura_engine/effects.py', 'BenchBasicFromOwnDiscardThenCounters', 'resolve'): ('public', 'single'),
    ('bench_from_discard', 'kyuura_engine/effects.py', 'DiscardEnergyThenBenchBasicFromDiscard', 'resume'): ('public', 'single'),
    ('bench_from_discard', 'kyuura_engine/effects.py', '_BenchBasicFromDiscardTrainer', 'resolve'): ('public', 'single'),
    ('bench_from_discard', 'kyuura_engine/resolution/programs.py', 'BenchBabyOrBasicFromOwnDiscard', 'run'): ('public', 'single'),
    ('bench_from_discard', 'kyuura_engine/resolution/programs.py', 'BenchFromEitherDiscard', 'run'): ('public', 'single'),
    ('bench_from_discard', 'kyuura_engine/resolution/programs.py', 'BenchFromOpponentDiscard', 'run'): ('public', 'single'),
    ('bench_guard', 'kyuura_engine/resolution/programs.py', 'CoinPerOpponentPokemon', '_deal'): ('public', 'significant'),
    ('bench_guard', 'kyuura_engine/resolution/programs.py', None, 'guarded_damages'): ('public', 'significant'),
    ('challenge_bench', 'kyuura_engine/effects.py', 'ChallengeBenchFromDecks', '_offer'): ('started_search', 'unconfirmed'),
    ('damage_option', 'kyuura_engine/resolution/programs.py', None, 'guarded_damages'): ('public', 'single'),
    ('damage_option', 'kyuura_engine/resolution/programs.py', None, 'suspend_damage_option'): ('public', 'single'),
    ('damage_reduction', 'kyuura_engine/resolution/programs.py', None, 'suspend_damage_reduction'): ('public', 'single'),
    ('damage_step_order', 'kyuura_engine/resolution/programs.py', None, 'suspend_step_order'): ('public', 'single'),
    ('deck_top_from_hand', 'kyuura_engine/effects.py', 'DrawThenPutHandCardOnDeckTop', 'resolve'): ('own_cards', 'single'),
    ('discard_energy', 'kyuura_engine/effects.py', 'DiscardAttachedEnergyTrainer', 'resolve'): ('public', 'not_significant'),
    ('discard_energy', 'kyuura_engine/effects.py', 'DiscardEnergyThenHealTrainer', 'resume'): ('public', 'single'),
    ('discard_energy', 'kyuura_engine/resolution/programs.py', 'DiscardEachType', '_ask'): ('public', 'single'),
    ('discard_energy', 'kyuura_engine/resolution/programs.py', 'DiscardOwnEnergy', 'run'): ('public', 'significant'),
    ('discard_energy', 'kyuura_engine/resolution/programs.py', 'OptionalDiscardBenchDamage', 'run'): ('public', 'single'),
    ('discard_energy', 'kyuura_engine/resolution/programs.py', 'OptionalDiscardForBonus', 'run'): ('public', 'not_significant'),
    ('discard_from_hand', 'kyuura_engine/effects.py', 'DiscardEnergyThenBenchBasicFromDiscard', 'resolve'): ('own_cards', 'unconfirmed'),
    ('discard_from_hand', 'kyuura_engine/effects.py', 'DiscardFromHandThenDrawTrainer', 'resolve'): ('own_cards', 'unconfirmed'),
    ('discard_from_hand', 'kyuura_engine/effects.py', 'DiscardFromHandThenRetrieveEnergy', 'resolve'): ('own_cards', 'unconfirmed'),
    ('discard_from_hand', 'kyuura_engine/effects.py', 'DiscardFromHandThenSearchDeck', 'resolve'): ('own_cards', 'unconfirmed'),
    ('discard_from_hand', 'kyuura_engine/effects.py', 'DiscardThenDraw', 'resolve'): ('own_cards', 'single'),
    ('discard_from_hand', 'kyuura_engine/effects.py', 'ReturnHandsToDeckTrainer', 'resolve'): ('own_cards', 'unconfirmed'),
    ('discard_from_hand', 'kyuura_engine/effects.py', 'SearchDeckTrainer', 'resolve'): ('own_cards', 'unconfirmed'),
    ('discard_from_hand', 'kyuura_engine/effects.py', 'TakeFromDiscardTrainer', 'resolve'): ('own_cards', 'unconfirmed'),
    ('discard_from_hand', 'kyuura_engine/effects.py', 'TrainerTurnEffectTrainer', 'resolve'): ('own_cards', 'unconfirmed'),
    ('discard_from_hand', 'kyuura_engine/engine.py', None, '_start_trainer_use'): ('own_cards', 'unconfirmed'),
    ('discard_opponent_energy', 'kyuura_engine/effects.py', 'DiscardAttachedEnergyTrainer', '_opponent_stage'): ('public', 'single'),
    ('discard_opponent_energy', 'kyuura_engine/effects.py', 'DiscardAttachedEnergyTrainer', 'resume'): ('public', 'not_significant'),
    ('discard_opponent_energy', 'kyuura_engine/resolution/programs.py', 'DiscardChosenTypedEnergyUntilTails', 'run'): ('public', 'not_significant'),
    ('discard_opponent_energy', 'kyuura_engine/resolution/programs.py', 'DiscardOpponentEnergy', '_next'): ('public', 'single'),
    ('discard_opponent_energy', 'kyuura_engine/resolution/programs.py', 'DiscardOpponentEnergyByHeads', 'run'): ('public', 'not_significant'),
    ('discard_opponent_energy', 'kyuura_engine/resolution/programs.py', 'DiscardOpponentEnergyUpToHeads', 'run'): ('public', 'not_significant'),
    ('discard_stadium', 'kyuura_engine/resolution/programs.py', 'OptionalDiscardStadium', 'run'): ('public', 'single'),
    ('discard_to_deck', 'kyuura_engine/effects.py', 'CoinReturnEnergyFromDiscardToDeck', 'resolve'): ('public', 'not_significant'),
    ('discard_to_deck', 'kyuura_engine/effects.py', 'EachPlayerReturnDiscardToDeckThenHandLock', '_offer'): ('public', 'not_significant'),
    ('discard_to_deck', 'kyuura_engine/effects.py', 'TakeFromDiscardTrainer', '_choose'): ('public', 'not_significant'),
    ('discard_to_deck', 'kyuura_engine/resolution/programs.py', 'CoinDiscardCardToDeckThenShuffle', 'run'): ('public', 'single'),
    ('discard_to_deck', 'kyuura_engine/resolution/programs.py', 'EachPlayerStep', '_offer'): ('public', 'not_significant'),
    ('discard_to_deck_top', 'kyuura_engine/effects.py', 'TakeFromDiscardTrainer', '_choose'): ('public', 'unconfirmed'),
    ('discard_to_deck_top', 'kyuura_engine/resolution/programs.py', 'OpponentDiscardToDeckTop', 'run'): ('public', 'single'),
    ('energy_drain_discard', 'kyuura_engine/resolution/programs.py', None, 'fire_or_suspend'): ('public', 'single'),
    ('entry_power', 'kyuura_engine/effects.py', None, 'offer_entry_power'): ('public', 'single'),
    ('esp_redo', 'kyuura_engine/resolution/programs.py', None, 'suspend_esp_redo'): ('public', 'single'),
    ('evolution_heal', 'kyuura_engine/effects.py', None, 'offer_evolution_heal'): ('public', 'single'),
    ('evolution_heal', 'kyuura_engine/resolution/programs.py', 'EachPlayerEvolvesFromDeck', 'resume'): ('public', 'single'),
    ('evolution_heal', 'kyuura_engine/resolution/programs.py', 'EvolveChosenFromDeck', 'resume'): ('public', 'single'),
    ('evolution_heal', 'kyuura_engine/resolution/programs.py', None, 'suspend_evolution_heal'): ('public', 'single'),
    ('evolution_song_pokemon', 'kyuura_engine/resolution/programs.py', 'EachPlayerEvolvesFromDeck', '_offer'): ('owner_knowledge', 'single'),
    ('evolution_song_pokemon', 'kyuura_engine/resolution/programs.py', 'EachPlayerStep', '_offer'): ('owner_knowledge', 'single'),
    ('exp_all_energy', 'kyuura_engine/resolution/codec.py', None, 'exp_all_decision'): ('public', 'single'),
    ('exp_all_energy', 'kyuura_engine/resolution/flow.py', None, '_finish_attack'): ('public', 'single'),
    ('forced_switch', 'kyuura_engine/resolution/programs.py', 'ForceSwitch', 'run'): ('public', 'single'),
    ('hand_to_active', 'kyuura_engine/effects.py', 'BenchActiveThenHandBasicToActive', 'resolve'): ('own_cards', 'single'),
    ('hand_to_deck', 'kyuura_engine/effects.py', 'DrawThenReturnHandCardsToDeck', 'resolve'): ('own_cards', 'unconfirmed'),
    ('hand_to_deck', 'kyuura_engine/effects.py', 'ReturnHandToDeckThenDraw', 'resolve'): ('own_cards', 'unconfirmed'),
    ('hand_to_deck', 'kyuura_engine/effects.py', 'SearchDeckTrainer', 'resolve'): ('own_cards', 'unconfirmed'),
    ('hand_to_deck', 'kyuura_engine/resolution/programs.py', 'ReturnHandThenRevealEnergy', 'run'): ('own_cards', 'unconfirmed'),
    ('hand_to_deck', 'kyuura_engine/resolution/programs.py', 'ReturnHandToDeck', 'run'): ('own_cards', 'unconfirmed'),
    ('heal_allocation', 'kyuura_engine/resolution/programs.py', 'AllocateHeal', 'run'): ('public', 'single'),
    ('janken_hand', 'kyuura_engine/effects.py', 'RockPaperScissorsRefreshHand', '_ask'): ('public', 'single'),
    ('janken_hand', 'kyuura_engine/effects.py', 'RockPaperScissorsRefreshHand', 'resume'): ('public', 'single'),
    ('knock_out_power', 'kyuura_engine/resolution/flow.py', None, '_finish_attack'): ('public', 'single'),
    ('ko_prevention', 'kyuura_engine/resolution/flow.py', None, '_finish_attack'): ('public', 'single'),
    ('magma_pool_energy', 'kyuura_engine/reactions.py', None, 'process'): ('public', 'single'),
    ('magma_pool_energy', 'kyuura_engine/resolution/programs.py', None, '_apply_move'): ('public', 'single'),
    ('move_energy', 'kyuura_engine/effects.py', 'ChargeBenchEnergyToSelf', 'resolve'): ('public', 'not_significant'),
    ('move_energy', 'kyuura_engine/effects.py', 'GatherTypeEnergyCardsToSelf', 'resolve'): ('public', 'not_significant'),
    ('move_energy', 'kyuura_engine/effects.py', 'TakeEnergiesToSelf', 'resolve'): ('public', 'not_significant'),
    ('move_energy', 'kyuura_engine/resolution/programs.py', 'BubbleJump', 'resume'): ('public', 'significant'),
    ('move_energy', 'kyuura_engine/resolution/programs.py', 'MoveOneEnergyToBench', 'run'): ('public', 'single'),
    ('move_opponent_energy', 'kyuura_engine/resolution/programs.py', 'MoveOpponentEnergyToBench', 'run'): ('public', 'single'),
    ('move_opponent_energy', 'kyuura_engine/resolution/programs.py', 'MoveOpponentFieldEnergy', 'run'): ('public', 'single'),
    ('ninja_trick', 'kyuura_engine/resolution/programs.py', None, 'offer_ninja_trick'): ('public', 'single'),
    ('opponent_hand_to_bench', 'kyuura_engine/effects.py', 'LookOpponentHandThenBenchBasics', 'resolve'): ('started_search', 'unconfirmed'),
    ('opponent_hand_to_bench', 'kyuura_engine/resolution/programs.py', 'EachPlayerHandToBench', '_stage'): ('started_search', 'unconfirmed'),
    ('opponent_hand_to_bench', 'kyuura_engine/resolution/programs.py', 'OpponentHandToBenchThenSwitch', 'run'): ('started_search', 'single'),
    ('opponent_hand_to_deck', 'kyuura_engine/effects.py', 'CoinLookOpponentHandMayReturnTrainer', 'resolve'): ('started_search', 'single'),
    ('opponent_hand_to_deck', 'kyuura_engine/effects.py', 'LookOpponentHandReturnOneThenMayDraw', 'resolve'): ('started_search', 'single'),
    ('opponent_hand_to_deck', 'kyuura_engine/effects.py', 'OpponentHandTrainerToDeck', 'resolve'): ('started_search', 'single'),
    ('opponent_hand_to_deck', 'kyuura_engine/resolution/programs.py', 'LookHandTrainerToDeck', 'run'): ('started_search', 'single'),
    ('optional_coin', 'kyuura_engine/resolution/programs.py', 'OptionalCoin', 'run'): ('public', 'single'),
    ('optional_discard_all', 'kyuura_engine/resolution/programs.py', 'OptionalDiscardAll', 'run'): ('public', 'single'),
    ('optional_drain', 'kyuura_engine/resolution/programs.py', 'Drain', 'run'): ('public', 'single'),
    ('optional_heal', 'kyuura_engine/resolution/programs.py', 'OptionalHealSelf', 'run'): ('public', 'single'),
    ('optional_shuffle', 'kyuura_engine/effects.py', 'CoinPeekOpponentDeckTopMayShuffle', 'resolve'): ('public', 'single'),
    ('peek_card', 'kyuura_engine/effects.py', 'PeekCard', 'resolve'): ('own_cards', 'single'),
    ('post_knockout_power', 'kyuura_engine/resolution/codec.py', None, 'post_knockout_decision'): ('public', 'single'),
    ('post_knockout_power', 'kyuura_engine/resolution/flow.py', None, '_offer_post_knockout'): ('public', 'single'),
    ('prize_first', 'kyuura_engine/resolution/codec.py', None, 'prize_first_decision'): ('public', 'single'),
    ('prize_first', 'kyuura_engine/resolution/flow.py', None, '_next_prize_or_judge'): ('public', 'single'),
    ('promote_active', 'kyuura_engine/resolution/codec.py', None, 'promote_decision'): ('public', 'single'),
    ('promote_active', 'kyuura_engine/resolution/flow.py', None, '_next_promotion_or_end'): ('public', 'single'),
    ('quiz_answer', 'kyuura_engine/effects.py', 'BlainesQuiz', 'resume'): ('public', 'single'),
    ('quiz_answer', 'kyuura_engine/effects.py', 'GuessOpponentPrizeKind', 'resume'): ('public', 'single'),
    ('quiz_answer', 'kyuura_engine/effects.py', 'SetAsideGuessKindQuiz', 'resume'): ('public', 'single'),
    ('quiz_attack', 'kyuura_engine/effects.py', 'BlainesQuiz', 'resume'): ('public', 'single'),
    ('quiz_card', 'kyuura_engine/effects.py', 'BlainesHeightQuiz', 'resolve'): ('own_cards', 'single'),
    ('quiz_card', 'kyuura_engine/effects.py', 'BlainesQuiz', 'resolve'): ('own_cards', 'single'),
    ('quiz_card', 'kyuura_engine/effects.py', 'SetAsideGuessKindQuiz', 'resolve'): ('own_cards', 'single'),
    ('quiz_height_answer', 'kyuura_engine/effects.py', 'BlainesHeightQuiz', 'resume'): ('public', 'single'),
    ('reaction_order', 'kyuura_engine/reactions.py', None, '_process_same'): ('public', 'single'),
    ('reaction_order', 'kyuura_engine/resolution/programs.py', None, '_settle_move_step'): ('public', 'single'),
    ('reaction_power', 'kyuura_engine/engine.py', None, '_offer_trainer_reaction'): ('public', 'single'),
    ('reaction_power', 'kyuura_engine/reactions.py', None, '_offer_use'): ('public', 'single'),
    ('reaction_switch', 'kyuura_engine/resolution/programs.py', None, 'offer_flee'): ('public', 'single'),
    ('recover_energy', 'kyuura_engine/resolution/programs.py', 'RecoverEnergy', 'run'): ('public', 'significant'),
    ('recover_energy', 'kyuura_engine/resolution/programs.py', 'RecoverEnergyByHeads', 'run'): ('public', 'not_significant'),
    ('recover_energy', 'kyuura_engine/resolution/programs.py', 'RecoverSpecialEnergy', 'run'): ('public', 'single'),
    ('recover_pokemon', 'kyuura_engine/effects.py', 'CoinTakeEvolutionOrBasicFromDiscard', 'resolve'): ('public', 'single'),
    ('recover_pokemon', 'kyuura_engine/effects.py', 'CoinsTakePokemonOrTrainerFromDiscard', 'resolve'): ('public', 'single'),
    ('recover_pokemon', 'kyuura_engine/effects.py', 'RecoverPokemonFromDiscardOnEntry', 'resolve'): ('public', 'not_significant'),
    ('recover_pokemon', 'kyuura_engine/resolution/programs.py', 'EachPlayerStep', '_offer'): ('public', 'not_significant'),
    ('recover_trainer', 'kyuura_engine/effects.py', 'CoinRecoverNamedFromDiscard', 'resolve'): ('public', 'single'),
    ('recover_trainer', 'kyuura_engine/effects.py', 'CoinRecoverTrainerWithBenchLetters', 'resolve'): ('public', 'single'),
    ('recover_trainer', 'kyuura_engine/effects.py', 'CoinsTakePokemonOrTrainerFromDiscard', 'resolve'): ('public', 'single'),
    ('recover_trainer', 'kyuura_engine/effects.py', 'TakeFromDiscardTrainer', '_choose'): ('public', 'not_significant'),
    ('recover_trainer', 'kyuura_engine/resolution/programs.py', 'RecoverTrainer', 'run'): ('public', 'single'),
    ('remove_counters', 'kyuura_engine/resolution/programs.py', 'ChosenOpponentHealThenDraw', 'resume'): ('public', 'single'),
    ('restore', 'kyuura_engine/reactions.py', None, '_run_step'): ('inherits', 'unconfirmed'),
    ('retrieve_energy', 'kyuura_engine/effects.py', 'CoinRetrieveBasicEnergyStadium', 'activate'): ('public', 'single'),
    ('retrieve_energy', 'kyuura_engine/effects.py', 'DiscardFromHandThenRetrieveEnergy', 'resume'): ('own_cards', 'not_significant'),
    ('return_energy', 'kyuura_engine/effects.py', 'CoinsUntilTailsReturnOpponentActiveEnergyThenEndTurn', 'resolve'): ('public', 'not_significant'),
    ('return_energy', 'kyuura_engine/effects.py', 'ReturnBasicEnergyToHandTrainer', 'resolve'): ('public', 'not_significant'),
    ('return_energy', 'kyuura_engine/resolution/programs.py', 'DiscardOwnEnergy', 'run'): ('public', 'significant'),
    ('return_to_deck', 'kyuura_engine/effects.py', 'ReturnHandEnergyThenCoinSearchBasicEnergy', 'resolve'): ('owner_knowledge', 'single'),
    ('return_to_deck', 'kyuura_engine/effects.py', 'TradePokemonWithDeck', 'resolve'): ('own_cards', 'single'),
    ('revive_source', 'kyuura_engine/effects.py', 'FossilEggRevive', 'resolve'): ('own_cards', 'single'),
    ('search_deck', 'kyuura_engine/effects.py', 'BreederCoupleSearch', '_next'): ('started_search', 'unconfirmed'),
    ('search_deck', 'kyuura_engine/effects.py', 'CoinEvolveSelfFromDeck', 'resolve'): ('started_search', 'unconfirmed'),
    ('search_deck', 'kyuura_engine/effects.py', 'CoinsSearchBasicEnergyPerHeads', 'resolve'): ('started_search', 'unconfirmed'),
    ('search_deck', 'kyuura_engine/effects.py', 'DiscardFromHandThenSearchDeck', 'resume'): ('started_search', 'unconfirmed'),
    ('search_deck', 'kyuura_engine/effects.py', 'EachPlayerSearchToolOnEntry', 'resume'): ('started_search', 'unconfirmed'),
    ('search_deck', 'kyuura_engine/effects.py', 'ReturnHandEnergyThenCoinSearchBasicEnergy', 'resume'): ('started_search', 'unconfirmed'),
    ('search_deck', 'kyuura_engine/effects.py', 'SearchDeckTrainer', '_search'): ('started_search', 'unconfirmed'),
    ('search_deck', 'kyuura_engine/effects.py', 'SearchDeckWithBenchLettersToHand', 'resolve'): ('started_search', 'single'),
    ('search_deck', 'kyuura_engine/effects.py', 'SearchEvolutionCardToHand', 'resolve'): ('started_search', 'single'),
    ('search_deck', 'kyuura_engine/effects.py', 'SearchNamedTrainerOnEntry', 'resolve'): ('started_search', 'single'),
    ('search_deck', 'kyuura_engine/effects.py', 'TradePokemonWithDeck', 'resume'): ('started_search', 'single'),
    ('search_deck', 'kyuura_engine/reactions.py', None, '_offer_search'): ('started_search', 'unconfirmed'),
    ('search_deck', 'kyuura_engine/resolution/programs.py', 'EachPlayerEvolvesFromDeck', 'resume'): ('started_search', 'unconfirmed'),
    ('search_deck', 'kyuura_engine/resolution/programs.py', 'EvolveAttackerFromDeck', '_required_run'): ('started_search', 'unconfirmed'),
    ('search_deck', 'kyuura_engine/resolution/programs.py', 'EvolveAttackerFromDeck', 'run'): ('started_search', 'single'),
    ('search_deck', 'kyuura_engine/resolution/programs.py', 'EvolveChosenFromDeck', '_next'): ('started_search', 'unconfirmed'),
    ('search_deck', 'kyuura_engine/resolution/programs.py', 'EvolveFromDeck', 'run'): ('started_search', 'unconfirmed'),
    ('search_deck', 'kyuura_engine/resolution/programs.py', 'ReturnHandThenRevealEnergy', 'resume'): ('started_search', 'unconfirmed'),
    ('search_deck', 'kyuura_engine/resolution/programs.py', 'RevealNamedPokemonFromDeck', 'run'): ('started_search', 'unconfirmed'),
    ('search_deck', 'kyuura_engine/resolution/programs.py', 'RevealPokemonFromDeck', 'run'): ('started_search', 'unconfirmed'),
    ('search_deck', 'kyuura_engine/resolution/programs.py', 'RevealTrainerFromDeck', 'run'): ('started_search', 'unconfirmed'),
    ('search_deck_or_discard', 'kyuura_engine/effects.py', 'SearchNamedFromDeckOrDiscard', 'resolve'): ('started_search', 'single'),
    ('secret_plan_card', 'kyuura_engine/effects.py', 'PlaceFaceDownOnBench', 'resolve'): ('own_cards', 'single'),
    ('select_attached_special_energy', 'kyuura_engine/resolution/programs.py', 'ReturnAttachedSpecialEnergyToDeck', 'run'): ('public', 'single'),
    ('select_attached_trainer', 'kyuura_engine/resolution/programs.py', 'ReturnAttachedTrainerToDeck', 'run'): ('public', 'single'),
    ('select_attack', 'kyuura_engine/resolution/programs.py', 'CopyChosenAttack', 'run'): ('public', 'single'),
    ('select_attack', 'kyuura_engine/resolution/programs.py', 'CopyOpponentAttack', 'run'): ('public', 'single'),
    ('select_color', 'kyuura_engine/effects.py', 'ConvertBasicEnergyColor', 'resolve'): ('public', 'single'),
    ('select_color', 'kyuura_engine/effects.py', 'ConvertSelfToEnergy', 'resume'): ('public', 'single'),
    ('select_color', 'kyuura_engine/effects.py', 'ShiftColor', 'resolve'): ('public', 'single'),
    ('select_color', 'kyuura_engine/resolution/programs.py', 'ChooseColor', 'run'): ('public', 'single'),
    ('select_color', 'kyuura_engine/resolution/programs.py', 'OpponentWeaknessColor', 'run'): ('public', 'single'),
    ('select_color', 'kyuura_engine/resolution/programs.py', 'SelfResistanceColor', 'run'): ('public', 'single'),
    ('select_counter_count', 'kyuura_engine/effects.py', 'DiscardEnergyThenHealTrainer', 'resume'): ('public', 'single'),
    ('select_counter_count', 'kyuura_engine/effects.py', 'HealNamedPokemonUpTo', 'resume'): ('public', 'single'),
    ('select_deck_owner', 'kyuura_engine/resolution/programs.py', 'ArrangeDeckTop', 'run'): ('public', 'single'),
    ('select_devolve_count', 'kyuura_engine/effects.py', 'DevolveOwnPokemon', 'resume'): ('public', 'single'),
    ('select_draw_count', 'kyuura_engine/effects.py', 'EachPlayerMayDraw', '_offer'): ('public', 'single'),
    ('select_draw_count', 'kyuura_engine/effects.py', 'LookOpponentHandReturnOneThenMayDraw', 'resume'): ('public', 'single'),
    ('select_draw_count', 'kyuura_engine/resolution/programs.py', 'EachPlayerStep', '_offer'): ('public', 'unconfirmed'),
    ('select_evolution_card', 'kyuura_engine/effects.py', 'EvolveBasicToStage2', 'resume'): ('own_cards', 'single'),
    ('select_evolution_card', 'kyuura_engine/effects.py', 'FossilEggRevive', 'resolve'): ('own_cards', 'single'),
    ('select_evolution_card', 'kyuura_engine/effects.py', 'FossilEggRevive', 'resume'): ('own_cards', 'single'),
    ('select_evolution_card', 'kyuura_engine/effects.py', 'Shapeshift', 'resolve'): ('own_cards', 'single'),
    ('select_exchange_card', 'kyuura_engine/effects.py', 'SwapPleaseTrainer', 'resolve'): ('started_search', 'single'),
    ('select_exchange_card', 'kyuura_engine/effects.py', 'SwapPleaseTrainer', 'resume'): ('started_search', 'single'),
    ('select_hand_card', 'kyuura_engine/resolution/programs.py', 'LookHandCardToDeck', 'run'): ('public', 'single'),
    ('select_hand_positions', 'kyuura_engine/effects.py', 'CoinReturnOpponentHandPositions', 'resolve'): ('public', 'not_significant'),
    ('select_look_count', 'kyuura_engine/effects.py', 'ArrangeOwnDeckTopTrainer', 'resolve'): ('public', 'single'),
    ('select_look_count', 'kyuura_engine/effects.py', 'LookDeckTopStadium', 'activate'): ('public', 'single'),
    ('select_look_count', 'kyuura_engine/resolution/programs.py', 'ArrangeDeckTop', 'resume'): ('public', 'single'),
    ('select_marker_count', 'kyuura_engine/resolution/programs.py', 'OptionalRemoveOwnMarkers', 'run'): ('public', 'single'),
    ('select_opponent_attack', 'kyuura_engine/resolution/programs.py', 'OpponentAttackLock', 'run'): ('public', 'single'),
    ('select_opponent_prize', 'kyuura_engine/effects.py', 'GuessOpponentPrizeKind', 'resolve'): ('public', 'single'),
    ('select_pokemon', 'kyuura_engine/effects.py', 'AttachedDamageReduction', 'resolve'): ('public', 'single'),
    ('select_pokemon', 'kyuura_engine/effects.py', 'AttachedEffectGuard', 'resolve'): ('public', 'single'),
    ('select_pokemon', 'kyuura_engine/effects.py', 'BreederCoupleSearch', 'resolve'): ('public', 'not_significant'),
    ('select_pokemon', 'kyuura_engine/effects.py', 'ChooseFossilEvolvedThenCoinDevolveAll', 'resolve'): ('public', 'single'),
    ('select_pokemon', 'kyuura_engine/effects.py', 'ChooseOwnPokemonCoinsHeal', 'resolve'): ('public', 'single'),
    ('select_pokemon', 'kyuura_engine/effects.py', 'CoinAttachEnergyFromDeckToOwnPokemon', 'resume'): ('public', 'single'),
    ('select_pokemon', 'kyuura_engine/effects.py', 'CoinAttachFromDiscardToTypePokemon', 'resume'): ('public', 'single'),
    ('select_pokemon', 'kyuura_engine/effects.py', 'CoinReturnOpponentPokemonToHandOnEntry', 'resolve'): ('public', 'single'),
    ('select_pokemon', 'kyuura_engine/effects.py', 'CoinReturnOtherGroupToHandOnEntry', 'resolve'): ('public', 'single'),
    ('select_pokemon', 'kyuura_engine/effects.py', 'CoinReturnOwnPokemonWithAttachedToHand', 'resolve'): ('public', 'single'),
    ('select_pokemon', 'kyuura_engine/effects.py', 'CoinReturnOwnerPokemonStadium', 'activate'): ('public', 'single'),
    ('select_pokemon', 'kyuura_engine/effects.py', 'CoinsReturnOpponentBenchElseEndTurn', 'resolve'): ('public', 'single'),
    ('select_pokemon', 'kyuura_engine/effects.py', 'ConvertSelfToEnergy', 'resolve'): ('public', 'single'),
    ('select_pokemon', 'kyuura_engine/effects.py', 'DamageOpponentPokemonOnEntry', 'resolve'): ('public', 'single'),
    ('select_pokemon', 'kyuura_engine/effects.py', 'DevolveOneToHandWithBan', 'resolve'): ('public', 'single'),
    ('select_pokemon', 'kyuura_engine/effects.py', 'DevolveOwnPokemon', 'resolve'): ('public', 'single'),
    ('select_pokemon', 'kyuura_engine/effects.py', 'DiscardAttachedEnergyTrainer', '_opponent_stage'): ('public', 'single'),
    ('select_pokemon', 'kyuura_engine/effects.py', 'DiscardDeckTopAttachTypeEnergyThenEndTurn', '_next'): ('public', 'single'),
    ('select_pokemon', 'kyuura_engine/effects.py', 'DiscardEnergyThenHealTrainer', 'resolve'): ('public', 'single'),
    ('select_pokemon', 'kyuura_engine/effects.py', 'EvolutionPermissionForOwnerPokemon', 'resolve'): ('public', 'single'),
    ('select_pokemon', 'kyuura_engine/effects.py', 'EvolveBasicToStage2', 'resolve'): ('own_cards', 'single'),
    ('select_pokemon', 'kyuura_engine/effects.py', 'HealNamedPokemonUpTo', 'resolve'): ('public', 'single'),
    ('select_pokemon', 'kyuura_engine/effects.py', 'HealOwnPokemonOnHeads', 'resolve'): ('public', 'single'),
    ('select_pokemon', 'kyuura_engine/effects.py', 'HealOwnerPokemonThenDiscardHand', 'resolve'): ('public', 'single'),
    ('select_pokemon', 'kyuura_engine/effects.py', 'MoveAllEnergyBetweenOwnerPokemon', 'resolve'): ('public', 'single'),
    ('select_pokemon', 'kyuura_engine/effects.py', 'MoveAllEnergyBetweenOwnerPokemon', 'resume'): ('public', 'single'),
    ('select_pokemon', 'kyuura_engine/effects.py', 'OpponentChoosesMySwitchThenISwitchTheirs', '_offer'): ('public', 'single'),
    ('select_pokemon', 'kyuura_engine/effects.py', 'PinpointLens', 'resolve'): ('public', 'single'),
    ('select_pokemon', 'kyuura_engine/effects.py', 'PokemonToolEffect', 'resolve'): ('public', 'single'),
    ('select_pokemon', 'kyuura_engine/effects.py', 'ProtectAttachedEnergy', 'resolve'): ('public', 'single'),
    ('select_pokemon', 'kyuura_engine/effects.py', 'RedoAttackCoins', 'resolve'): ('public', 'single'),
    ('select_pokemon', 'kyuura_engine/effects.py', 'RemoveDamageCounters', 'resolve'): ('public', 'single'),
    ('select_pokemon', 'kyuura_engine/effects.py', 'ReturnBenchedPokemonToDeck', 'resolve'): ('public', 'single'),
    ('select_pokemon', 'kyuura_engine/effects.py', 'ReturnOwnPokemonBasicToHand', 'resolve'): ('public', 'single'),
    ('select_pokemon', 'kyuura_engine/effects.py', 'SuperTransformPower', 'resolve'): ('public', 'single'),
    ('select_pokemon', 'kyuura_engine/effects.py', 'SwitchBothActivesTrainer', '_offer'): ('public', 'single'),
    ('select_pokemon', 'kyuura_engine/effects.py', 'SwitchOpponentChosenByOpponent', 'resolve'): ('public', 'single'),
    ('select_pokemon', 'kyuura_engine/effects.py', 'SwitchOpponentOnHeads', 'resolve'): ('public', 'single'),
    ('select_pokemon', 'kyuura_engine/effects.py', 'SwitchOpponentWithBench', 'resolve'): ('public', 'single'),
    ('select_pokemon', 'kyuura_engine/effects.py', 'SwitchWithBench', 'resolve'): ('public', 'single'),
    ('select_pokemon', 'kyuura_engine/reactions.py', None, '_lightning_burst'): ('public', 'single'),
    ('select_pokemon', 'kyuura_engine/reactions.py', None, '_vine_pull'): ('public', 'single'),
    ('select_pokemon', 'kyuura_engine/resolution/programs.py', 'AttachFromDeckByHeads', '_ask_target'): ('public', 'single'),
    ('select_pokemon', 'kyuura_engine/resolution/programs.py', 'AttachFromHandToChosen', 'run'): ('public', 'single'),
    ('select_pokemon', 'kyuura_engine/resolution/programs.py', 'BatonPass', 'run'): ('public', 'single'),
    ('select_pokemon', 'kyuura_engine/resolution/programs.py', 'BubbleJump', 'run'): ('public', 'single'),
    ('select_pokemon', 'kyuura_engine/resolution/programs.py', 'ChooseOpponentBench', 'run'): ('public', 'single'),
    ('select_pokemon', 'kyuura_engine/resolution/programs.py', 'ChooseTarget', 'run'): ('public', 'single'),
    ('select_pokemon', 'kyuura_engine/resolution/programs.py', 'ChosenBenchCoinDamage', 'run'): ('public', 'single'),
    ('select_pokemon', 'kyuura_engine/resolution/programs.py', 'ChosenBenchDamage', 'run'): ('public', 'single'),
    ('select_pokemon', 'kyuura_engine/resolution/programs.py', 'ChosenBenchDamages', 'run'): ('public', 'significant'),
    ('select_pokemon', 'kyuura_engine/resolution/programs.py', 'ChosenOpponentHealThenDraw', 'run'): ('public', 'single'),
    ('select_pokemon', 'kyuura_engine/resolution/programs.py', 'CoinChosenSideHeal', 'run'): ('public', 'single'),
    ('select_pokemon', 'kyuura_engine/resolution/programs.py', 'DevolveChosenPokemon', 'run'): ('public', 'single'),
    ('select_pokemon', 'kyuura_engine/resolution/programs.py', 'DevolveOpponentToDeck', 'run'): ('public', 'single'),
    ('select_pokemon', 'kyuura_engine/resolution/programs.py', 'EvolveChosenFromDeck', 'run'): ('public', 'not_significant'),
    ('select_pokemon', 'kyuura_engine/resolution/programs.py', 'EvolveFromDeck', 'resume'): ('started_search', 'single'),
    ('select_pokemon', 'kyuura_engine/resolution/programs.py', 'HealChosenOwnBench', 'run'): ('public', 'single'),
    ('select_pokemon', 'kyuura_engine/resolution/programs.py', 'MoveOpponentEnergyToBench', 'resume'): ('public', 'single'),
    ('select_pokemon', 'kyuura_engine/resolution/programs.py', 'MoveOpponentFieldEnergy', 'resume'): ('public', 'single'),
    ('select_pokemon', 'kyuura_engine/resolution/programs.py', 'OptionalDiscardBenchDamage', 'resume'): ('public', 'single'),
    ('select_pokemon', 'kyuura_engine/resolution/programs.py', 'PromoteFromBench', 'run'): ('public', 'single'),
    ('select_pokemon', 'kyuura_engine/resolution/programs.py', 'ReturnOwnBenchToDeck', 'run'): ('public', 'single'),
    ('select_pokemon', 'kyuura_engine/resolution/programs.py', 'ReturnOwnPokemonToHand', 'run'): ('public', 'not_significant'),
    ('select_pokemon', 'kyuura_engine/resolution/programs.py', 'SelfSwitch', 'run'): ('public', 'single'),
    ('select_pokemon', 'kyuura_engine/resolution/programs.py', 'SwitchSelfThenStatusGuard', 'run'): ('public', 'single'),
    ('select_pokemon', 'kyuura_engine/resolution/programs.py', 'WashOwnBench', 'run'): ('public', 'single'),
    ('select_prize_card', 'kyuura_engine/effects.py', 'AskOpponentEachTakePrizeElseDraw', '_offer_prize'): ('public', 'single'),
    ('select_prize_card', 'kyuura_engine/effects.py', 'LookOwnPrizeCard', 'resolve'): ('public', 'single'),
    ('select_prize_card', 'kyuura_engine/effects.py', 'LookPrizeAskSwapElseDraw', 'resolve'): ('public', 'single'),
    ('select_prize_card', 'kyuura_engine/effects.py', 'SwapPrizeWithDeckTop', 'resolve'): ('public', 'single'),
    ('select_special_condition', 'kyuura_engine/effects.py', 'ConditionOwnActiveTrainer', 'resolve'): ('public', 'single'),
    ('select_special_condition', 'kyuura_engine/resolution/programs.py', 'ChosenStatus', 'run'): ('public', 'single'),
    ('split_from_deck', 'kyuura_engine/resolution/programs.py', None, 'fire_or_suspend'): ('started_search', 'unconfirmed'),
    ('stadium_from_discard', 'kyuura_engine/effects.py', 'CoinPutStadiumFromDiscard', 'resolve'): ('public', 'single'),
    ('stadium_return_bench', 'kyuura_engine/effects.py', 'BenchLimitStadium', '_ask'): ('public', 'single'),
    ('swap_with_prize', 'kyuura_engine/effects.py', 'LookPrizeAskSwapElseDraw', 'resume'): ('own_cards', 'single'),
    ('take_looked_cards', 'kyuura_engine/effects.py', 'LookTopTakeRestDiscardTrainer', 'resolve'): ('started_search', 'unconfirmed'),
    ('take_looked_cards', 'kyuura_engine/resolution/programs.py', 'EachPlayerLooksTakesBasicEnergy', '_offer'): ('started_search', 'unconfirmed'),
    ('take_looked_cards', 'kyuura_engine/resolution/programs.py', 'EachPlayerStep', '_offer'): ('started_search', 'unconfirmed'),
    ('take_looked_cards', 'kyuura_engine/resolution/programs.py', 'LookTopTakeOne', 'run'): ('started_search', 'single'),
    ('take_looked_pokemon', 'kyuura_engine/effects.py', 'LookTopTakePokemonThenShuffle', 'resolve'): ('started_search', 'single'),
    ('take_looked_trainer', 'kyuura_engine/effects.py', 'LookTopTakeTrainerThenShuffleLock', 'resolve'): ('started_search', 'single'),
    ('take_prize', 'kyuura_engine/resolution/codec.py', None, 'prize_decision'): ('public', 'single'),
    ('take_prize', 'kyuura_engine/resolution/flow.py', None, '_next_prize_or_judge'): ('public', 'single'),
    ('take_prize', 'kyuura_engine/resolution/flow.py', None, '_resume_prize_first'): ('public', 'single'),
    ('use_discard_trainer', 'kyuura_engine/effects.py', 'UseOpponentDiscardTrainer', 'resolve'): ('public', 'single'),
}

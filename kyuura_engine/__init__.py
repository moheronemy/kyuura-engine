"""kyuura-engine: 旧裏ポケモンカードゲームの対戦エンジン（v0.2c）。

ルールは「ポケットモンスターカードゲーム公式ルール 2000.02.14版」（『ポケモンカードオフィシャルブック2000』
pp.306〜326）。カードデータの正本は kyuura（https://github.com/moheronemy/kyuura）。
"""

from .cards import CardDefinition, CardPool, EnergyType, can_pay_cost, load_card_pool
from .commands import (
    AttachEnergy,
    DrawMulliganCards,
    EndTurn,
    EvolvePokemon,
    PlaceStartingPokemon,
    PlayBasicToBench,
    PlayTrainer,
    PromoteActive,
    ReportJankenResult,
    ResolveDecision,
    Retreat,
    TakePrize,
    UseAttack,
    UsePokemonPower,
    command_from_dict,
    command_to_dict,
)
from .deck import deck_problems, expand_decklist, validate_deck
from .effects import DEFAULT_EFFECTS, AttackKey, EffectRegistry, TrainerEntry
from .engine import apply_command, check_invariants, new_game
from .errors import DeckValidationError, EngineError, IllegalActionError, StateIntegrityError, UnsupportedError
from .rules import RULE_REFERENCES, RULES_2000_02_14, RuleSet
from .serialize import state_to_dict
from .state import TERMINAL_PHASES, AttachedTrainer, GameResult, GameState, PendingDecision, Phase, TrainerInUse

__version__ = "0.2.0c0"

__all__ = [
    "AttachEnergy",
    "AttachedTrainer",
    "AttackKey",
    "CardDefinition",
    "CardPool",
    "DEFAULT_EFFECTS",
    "DeckValidationError",
    "DrawMulliganCards",
    "EffectRegistry",
    "EndTurn",
    "EnergyType",
    "EngineError",
    "EvolvePokemon",
    "GameResult",
    "GameState",
    "IllegalActionError",
    "PendingDecision",
    "Phase",
    "PlaceStartingPokemon",
    "PlayBasicToBench",
    "PlayTrainer",
    "PromoteActive",
    "RULE_REFERENCES",
    "RULES_2000_02_14",
    "ReportJankenResult",
    "ResolveDecision",
    "Retreat",
    "RuleSet",
    "StateIntegrityError",
    "TERMINAL_PHASES",
    "TakePrize",
    "TrainerEntry",
    "TrainerInUse",
    "UnsupportedError",
    "UseAttack",
    "UsePokemonPower",
    "apply_command",
    "can_pay_cost",
    "check_invariants",
    "command_from_dict",
    "command_to_dict",
    "deck_problems",
    "expand_decklist",
    "load_card_pool",
    "new_game",
    "state_to_dict",
    "validate_deck",
]

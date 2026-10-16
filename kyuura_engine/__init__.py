"""kyuura-engine: 旧裏ポケモンカードゲームの対戦エンジン（v0.26）。

ルールは「ポケットモンスターカードゲーム公式ルール 2000.02.14版」（『ポケモンカードオフィシャルブック2000』
pp.306〜326）。カードデータの正本は kyuura（https://github.com/moheronemy/kyuura）。
"""

from .cards import CardDefinition, CardPool, EnergyType, can_pay_cost, load_card_pool
from .coins import CoinSide
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
from .continuous import power_suppressors, working_power_suppressors
from .deck import deck_problems, expand_decklist, validate_deck
from .decks import PRESET_DECKS, PresetDeck, preset_deck, preset_deck_ids
from .effects import (
    DEFAULT_EFFECTS,
    AttackKey,
    EffectRegistry,
    PowerEntry,
    PowerKey,
    TrainerEntry,
    available_ko_prevention_power,
    working_counterattack_power,
    working_evasion_power,
)
from .engine import apply_command, check_invariants, new_game
from .errors import DeckValidationError, EngineError, IllegalActionError, StateIntegrityError, UnsupportedError
from .rules import RULE_REFERENCES, RULES_2000_02_14, RuleSet
from .serialize import state_to_dict
from .state import (
    TERMINAL_PHASES,
    Asleep,
    AttachedTrainer,
    Confused,
    GameResult,
    GameState,
    Paralyzed,
    PendingDecision,
    NextTurnAttackDamage,
    Phase,
    Poison,
    PreventDamage,
    Retaliation,
    SpecialConditions,
    TrainerInUse,
)

__version__ = "0.37.0"

__all__ = [
    "Asleep",
    "AttachEnergy",
    "AttachedTrainer",
    "AttackKey",
    "CardDefinition",
    "CardPool",
    "CoinSide",
    "Confused",
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
    "Paralyzed",
    "PendingDecision",
    "PowerEntry",
    "PowerKey",
    "Phase",
    "Poison",
    "PreventDamage",
    "Retaliation",
    "NextTurnAttackDamage",
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
    "SpecialConditions",
    "TrainerInUse",
    "UnsupportedError",
    "UseAttack",
    "UsePokemonPower",
    "apply_command",
    "available_ko_prevention_power",
    "can_pay_cost",
    "check_invariants",
    "command_from_dict",
    "command_to_dict",
    "deck_problems",
    "expand_decklist",
    "PRESET_DECKS",
    "PresetDeck",
    "preset_deck",
    "preset_deck_ids",
    "load_card_pool",
    "new_game",
    "power_suppressors",
    "state_to_dict",
    "validate_deck",
    "working_power_suppressors",
    "working_counterattack_power",
    "working_evasion_power",
]

"""デッキの規定（『オフィシャルブック2000』p.308「対戦の前に」、kyuura NEO-2000-OFFICIAL-RULES）。"""

import copy
import unittest

from kyuura_engine import DeckValidationError, deck_problems, expand_decklist, new_game, validate_deck
from kyuura_engine.cards import pool_from_extract, read_extract

from tests.helpers import (
    CHARMANDER, DIGLETT, FIGHTING, FIRE, FIRE_DECK, GROWLITHE, MACHOP, PONYTA, POTION, WATER_FIGHTING_DECK,
)


def codes(problems):
    return [p.split(":")[0] for p in problems]


class DeckSizeTest(unittest.TestCase):
    """デッキにふくまれるカードはぴったり60枚（p.308）。"""

    def test_sixty_cards_is_legal(self):
        self.assertEqual(deck_problems(FIRE_DECK), [])
        self.assertEqual(deck_problems(WATER_FIGHTING_DECK), [])

    def test_fifty_nine_and_sixty_one_are_rejected(self):
        self.assertEqual(codes(deck_problems(FIRE_DECK[:-1])), ["DECK_SIZE"])
        self.assertEqual(codes(deck_problems(FIRE_DECK + [FIRE])), ["DECK_SIZE"])

    def test_new_game_rejects_illegal_deck(self):
        with self.assertRaises(DeckValidationError) as ctx:
            new_game(FIRE_DECK[:30], WATER_FIGHTING_DECK, seed=0)
        self.assertTrue(any("player 0: DECK_SIZE" in p for p in ctx.exception.problems))


class SameNameTest(unittest.TestCase):
    """同じ名前のカードは4枚まで。基本エネルギーカードだけはすきなだけ（p.308）。"""

    def test_five_copies_are_rejected(self):
        deck = expand_decklist({PONYTA: 5, GROWLITHE: 4, FIRE: 51})
        self.assertEqual(codes(deck_problems(deck)), ["TOO_MANY_COPIES"])

    def test_four_copies_are_legal(self):
        self.assertEqual(deck_problems(expand_decklist({PONYTA: 4, FIRE: 56})), [])

    def test_basic_energy_is_unlimited(self):
        self.assertEqual(deck_problems(expand_decklist({MACHOP: 1, FIGHTING: 59})), [])

    def test_same_name_counts_across_different_cards(self):
        """レベルやHPがちがっていても、名前が同じなら同じ名前のカード（p.308）。"""
        extract = copy.deepcopy(read_extract())
        other = copy.deepcopy(next(c for c in extract["cards"] if c["id"] == DIGLETT))
        other["id"] = "TEST-DIGLETT-OTHER-PRINT"
        other["pokemon"]["hp"] = 40
        extract["cards"].append(other)
        extract["pool_v0_1"].append(other["id"])
        pool = pool_from_extract(extract)
        deck = expand_decklist({DIGLETT: 3, "TEST-DIGLETT-OTHER-PRINT": 2, FIGHTING: 55})
        self.assertEqual(codes(deck_problems(deck, pool)), ["TOO_MANY_COPIES"])


class BasicPokemonTest(unittest.TestCase):
    def test_deck_without_basic_pokemon_is_rejected(self):
        """デッキには、かならずベイビィポケモンカードまたはたねポケモンカードが必要（p.308）。"""
        self.assertEqual(codes(deck_problems([FIRE] * 60)), ["NO_BASIC_POKEMON"])


class SupportedCardsTest(unittest.TestCase):
    """未対応のカードはデッキに入れられない（効果がないものとして扱わない）。"""

    def test_unsupported_cards_are_rejected(self):
        deck = expand_decklist({CHARMANDER: 1, POTION: 1, PONYTA: 4, FIRE: 54})
        problems = deck_problems(deck)
        self.assertEqual(codes(problems), ["UNSUPPORTED_CARD", "UNSUPPORTED_CARD"])
        self.assertIn("ひのこ", problems[0])

    def test_unknown_card_is_rejected(self):
        deck = expand_decklist({"PMCG1-999": 1, PONYTA: 4, FIRE: 55})
        self.assertEqual(codes(deck_problems(deck)), ["UNKNOWN_CARD"])

    def test_validate_deck_raises(self):
        with self.assertRaises(DeckValidationError):
            validate_deck([FIRE] * 60)


if __name__ == "__main__":
    unittest.main()

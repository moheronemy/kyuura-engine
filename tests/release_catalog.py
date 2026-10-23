"""Select release cohorts without enumerating every later release.

These are catalog slices, not a replay of an older engine's behaviour.
"""

import re


def _version(value: str) -> tuple[int, int, str]:
    match = re.fullmatch(r"(?:pool_)?v?(\d+)[._](\d+)([a-z]*)", value)
    if match is None:
        raise ValueError(f"Invalid release: {value!r}")
    major, minor, suffix = match.groups()
    return int(major), int(minor), suffix


def cards_after(extract: dict, release: str) -> frozenset[str]:
    """All cards in pools strictly newer than release, including future pools."""
    boundary = _version(release)
    return frozenset(
        card
        for key, cards in extract.items()
        if key.startswith("pool_v") and _version(key) > boundary
        for card in cards
    )


def cards_before(extract: dict, release: str) -> frozenset[str]:
    """All cards in pools strictly older than release."""
    boundary = _version(release)
    return frozenset(
        card
        for key, cards in extract.items()
        if key.startswith("pool_v") and _version(key) < boundary
        for card in cards
    )

"""Deterministic test-suite configuration."""

import os

from hypothesis import settings

DETERMINISTIC_PROFILE = "deterministic"

settings.register_profile(
    DETERMINISTIC_PROFILE,
    deadline=None,
    derandomize=True,
    print_blob=True,
)
settings.load_profile(os.environ.get("HYPOTHESIS_PROFILE", DETERMINISTIC_PROFILE))

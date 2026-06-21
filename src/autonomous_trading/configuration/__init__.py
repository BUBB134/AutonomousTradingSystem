"""Typed, versioned, fail-closed configuration interfaces."""

from .loader import load_configuration, loads_configuration
from .schema import (
    CONFIGURATION_SCHEMA_VERSION,
    Configuration,
    ConfigurationError,
    ConfigurationSnapshot,
    InstrumentUniverse,
    LiveSettings,
    OperatingEnvironment,
    PaperSettings,
    PromotionGates,
    ResearchBudget,
    SecretReference,
)

__all__ = [
    "CONFIGURATION_SCHEMA_VERSION",
    "Configuration",
    "ConfigurationError",
    "ConfigurationSnapshot",
    "InstrumentUniverse",
    "LiveSettings",
    "OperatingEnvironment",
    "PaperSettings",
    "PromotionGates",
    "ResearchBudget",
    "SecretReference",
    "load_configuration",
    "loads_configuration",
]

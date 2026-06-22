"""Immutable configuration schemas and deterministic snapshots."""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from decimal import Decimal
from enum import StrEnum

CONFIGURATION_SCHEMA_VERSION = 1

_SYMBOL_PATTERN = re.compile(r"[A-Z][A-Z0-9.-]{0,31}\Z")
_SECRET_NAME_PATTERN = re.compile(r"[a-z][a-z0-9_]{0,63}\Z")
_ENVIRONMENT_VARIABLE_PATTERN = re.compile(r"[A-Z][A-Z0-9_]{0,127}\Z")


class ConfigurationError(ValueError):
    """Raised when untrusted configuration fails the versioned schema."""


class OperatingEnvironment(StrEnum):
    """Operating environments permitted by the trading mandate."""

    RESEARCH = "research"
    BACKTEST = "backtest"
    VALIDATION = "validation"
    PAPER = "paper"


def _validate_bool(name: str, value: bool) -> None:
    if type(value) is not bool:
        raise ConfigurationError(f"{name} must be a boolean")


def _validate_positive_int(name: str, value: int) -> None:
    if type(value) is not int or value <= 0:
        raise ConfigurationError(f"{name} must be a positive integer")


def _validate_decimal(
    name: str,
    value: Decimal,
    *,
    minimum: Decimal,
    maximum: Decimal | None = None,
    minimum_inclusive: bool = True,
) -> None:
    if type(value) is not Decimal or not value.is_finite():
        raise ConfigurationError(f"{name} must be a finite decimal")
    minimum_valid = value >= minimum if minimum_inclusive else value > minimum
    if not minimum_valid:
        qualifier = "at least" if minimum_inclusive else "greater than"
        raise ConfigurationError(f"{name} must be {qualifier} {minimum}")
    if maximum is not None and value > maximum:
        raise ConfigurationError(f"{name} must be at most {maximum}")


def _canonical_decimal(value: Decimal) -> str:
    sign, digits, exponent = value.as_tuple()
    if type(exponent) is not int:
        raise ConfigurationError("snapshot decimals must be finite")
    if all(digit == 0 for digit in digits):
        return "0e0"

    significant_digits = list(digits)
    adjusted_exponent = exponent
    while significant_digits[-1] == 0:
        significant_digits.pop()
        adjusted_exponent += 1

    coefficient = "".join(str(digit) for digit in significant_digits)
    prefix = "-" if sign else ""
    return f"{prefix}{coefficient}e{adjusted_exponent}"


@dataclass(frozen=True, slots=True)
class ResearchBudget:
    """Deterministic upper bounds for research work."""

    max_experiments: int
    max_parameter_combinations: int
    max_runtime_seconds: int

    def __post_init__(self) -> None:
        _validate_positive_int("research_budget.max_experiments", self.max_experiments)
        _validate_positive_int(
            "research_budget.max_parameter_combinations",
            self.max_parameter_combinations,
        )
        _validate_positive_int("research_budget.max_runtime_seconds", self.max_runtime_seconds)


@dataclass(frozen=True, slots=True)
class InstrumentUniverse:
    """Explicit long-only instrument identifiers approved for the run."""

    symbols: tuple[str, ...]

    def __post_init__(self) -> None:
        if type(self.symbols) is not tuple or not self.symbols:
            raise ConfigurationError("instrument_universe.symbols must be a non-empty tuple")
        if len(set(self.symbols)) != len(self.symbols):
            raise ConfigurationError("instrument_universe.symbols must not contain duplicates")
        for symbol in self.symbols:
            if type(symbol) is not str or _SYMBOL_PATTERN.fullmatch(symbol) is None:
                raise ConfigurationError(
                    "instrument_universe.symbols must contain uppercase identifiers using only "
                    "letters, digits, periods, and hyphens"
                )


@dataclass(frozen=True, slots=True)
class PromotionGates:
    """Thresholds required by future independent promotion checks."""

    require_independent_validation: bool
    minimum_observations: int
    minimum_out_of_sample_fraction: Decimal
    maximum_drawdown_fraction: Decimal

    def __post_init__(self) -> None:
        _validate_bool(
            "promotion_gates.require_independent_validation",
            self.require_independent_validation,
        )
        if not self.require_independent_validation:
            raise ConfigurationError(
                "promotion_gates.require_independent_validation must remain true"
            )
        _validate_positive_int(
            "promotion_gates.minimum_observations",
            self.minimum_observations,
        )
        _validate_decimal(
            "promotion_gates.minimum_out_of_sample_fraction",
            self.minimum_out_of_sample_fraction,
            minimum=Decimal(0),
            maximum=Decimal(1),
            minimum_inclusive=False,
        )
        _validate_decimal(
            "promotion_gates.maximum_drawdown_fraction",
            self.maximum_drawdown_fraction,
            minimum=Decimal(0),
            maximum=Decimal(1),
        )


@dataclass(frozen=True, slots=True)
class PaperSettings:
    """Settings for isolated, long-only, unlevered paper simulation."""

    enabled: bool
    starting_cash: Decimal
    max_position_fraction: Decimal
    max_open_positions: int
    leverage_enabled: bool
    short_selling_enabled: bool

    def __post_init__(self) -> None:
        _validate_bool("paper.enabled", self.enabled)
        _validate_decimal(
            "paper.starting_cash",
            self.starting_cash,
            minimum=Decimal(0),
            minimum_inclusive=False,
        )
        _validate_decimal(
            "paper.max_position_fraction",
            self.max_position_fraction,
            minimum=Decimal(0),
            maximum=Decimal(1),
            minimum_inclusive=False,
        )
        _validate_positive_int("paper.max_open_positions", self.max_open_positions)
        _validate_bool("paper.leverage_enabled", self.leverage_enabled)
        _validate_bool("paper.short_selling_enabled", self.short_selling_enabled)
        if self.leverage_enabled:
            raise ConfigurationError("paper.leverage_enabled must remain false")
        if self.short_selling_enabled:
            raise ConfigurationError("paper.short_selling_enabled must remain false")


@dataclass(frozen=True, slots=True)
class LiveSettings:
    """False-only live-capital settings retained as explicit safety evidence."""

    enabled: bool
    leverage_enabled: bool
    short_selling_enabled: bool

    def __post_init__(self) -> None:
        _validate_bool("live.enabled", self.enabled)
        _validate_bool("live.leverage_enabled", self.leverage_enabled)
        _validate_bool("live.short_selling_enabled", self.short_selling_enabled)
        if self.enabled:
            raise ConfigurationError("live.enabled must remain false")
        if self.leverage_enabled:
            raise ConfigurationError("live.leverage_enabled must remain false")
        if self.short_selling_enabled:
            raise ConfigurationError("live.short_selling_enabled must remain false")


@dataclass(frozen=True, slots=True)
class SecretReference:
    """A logical secret reference without a secret value."""

    name: str
    environment_variable: str

    def __post_init__(self) -> None:
        if type(self.name) is not str or _SECRET_NAME_PATTERN.fullmatch(self.name) is None:
            raise ConfigurationError(
                "secret_references.name must use lowercase letters, digits, and underscores"
            )
        if (
            type(self.environment_variable) is not str
            or _ENVIRONMENT_VARIABLE_PATTERN.fullmatch(self.environment_variable) is None
        ):
            raise ConfigurationError(
                "secret_references.environment_variable must be an uppercase environment "
                "variable identifier"
            )


@dataclass(frozen=True, slots=True)
class ConfigurationSnapshot:
    """Canonical, content-addressed configuration evidence."""

    schema_version: int
    canonical_json: str
    sha256: str


@dataclass(frozen=True, slots=True)
class Configuration:
    """Root versioned configuration object."""

    schema_version: int
    environment: OperatingEnvironment
    research_budget: ResearchBudget
    instrument_universe: InstrumentUniverse
    promotion_gates: PromotionGates
    paper: PaperSettings
    live: LiveSettings
    secret_references: tuple[SecretReference, ...]

    def __post_init__(self) -> None:
        if type(self.schema_version) is not int or (
            self.schema_version != CONFIGURATION_SCHEMA_VERSION
        ):
            raise ConfigurationError(f"schema_version must be {CONFIGURATION_SCHEMA_VERSION}")
        if type(self.environment) is not OperatingEnvironment:
            raise ConfigurationError("environment must be a supported operating environment")
        if type(self.research_budget) is not ResearchBudget:
            raise ConfigurationError("research_budget must be a ResearchBudget")
        if type(self.instrument_universe) is not InstrumentUniverse:
            raise ConfigurationError("instrument_universe must be an InstrumentUniverse")
        if type(self.promotion_gates) is not PromotionGates:
            raise ConfigurationError("promotion_gates must be PromotionGates")
        if type(self.paper) is not PaperSettings:
            raise ConfigurationError("paper must be PaperSettings")
        if type(self.live) is not LiveSettings:
            raise ConfigurationError("live must be LiveSettings")
        if type(self.secret_references) is not tuple:
            raise ConfigurationError("secret_references must be a tuple")
        for reference in self.secret_references:
            if type(reference) is not SecretReference:
                raise ConfigurationError("secret_references must contain SecretReference values")
        reference_names = [reference.name for reference in self.secret_references]
        environment_variables = [
            reference.environment_variable for reference in self.secret_references
        ]
        if len(set(reference_names)) != len(reference_names):
            raise ConfigurationError("secret_references names must be unique")
        if len(set(environment_variables)) != len(environment_variables):
            raise ConfigurationError("secret_references environment variables must be unique")

        paper_environment = self.environment is OperatingEnvironment.PAPER
        if self.paper.enabled != paper_environment:
            raise ConfigurationError(
                "paper.enabled must be true only for the paper environment and false otherwise"
            )

    def snapshot(self) -> ConfigurationSnapshot:
        """Return deterministic, content-addressed evidence for this configuration."""
        payload = {
            "environment": self.environment.value,
            "instrument_universe": {"symbols": list(self.instrument_universe.symbols)},
            "live": {
                "enabled": self.live.enabled,
                "leverage_enabled": self.live.leverage_enabled,
                "short_selling_enabled": self.live.short_selling_enabled,
            },
            "paper": {
                "enabled": self.paper.enabled,
                "leverage_enabled": self.paper.leverage_enabled,
                "max_open_positions": self.paper.max_open_positions,
                "max_position_fraction": _canonical_decimal(self.paper.max_position_fraction),
                "short_selling_enabled": self.paper.short_selling_enabled,
                "starting_cash": _canonical_decimal(self.paper.starting_cash),
            },
            "promotion_gates": {
                "maximum_drawdown_fraction": _canonical_decimal(
                    self.promotion_gates.maximum_drawdown_fraction
                ),
                "minimum_observations": self.promotion_gates.minimum_observations,
                "minimum_out_of_sample_fraction": _canonical_decimal(
                    self.promotion_gates.minimum_out_of_sample_fraction
                ),
                "require_independent_validation": (
                    self.promotion_gates.require_independent_validation
                ),
            },
            "research_budget": {
                "max_experiments": self.research_budget.max_experiments,
                "max_parameter_combinations": (self.research_budget.max_parameter_combinations),
                "max_runtime_seconds": self.research_budget.max_runtime_seconds,
            },
            "schema_version": self.schema_version,
            "secret_references": [
                {
                    "environment_variable": reference.environment_variable,
                    "name": reference.name,
                }
                for reference in self.secret_references
            ],
        }
        canonical_json = json.dumps(
            payload,
            ensure_ascii=True,
            separators=(",", ":"),
            sort_keys=True,
        )
        digest = hashlib.sha256(canonical_json.encode("utf-8")).hexdigest()
        return ConfigurationSnapshot(
            schema_version=self.schema_version,
            canonical_json=canonical_json,
            sha256=digest,
        )

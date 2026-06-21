"""Strict TOML loading for the versioned configuration boundary."""

from __future__ import annotations

import tomllib
from collections.abc import Mapping
from decimal import Decimal
from pathlib import Path
from typing import cast

from .schema import (
    Configuration,
    ConfigurationError,
    InstrumentUniverse,
    LiveSettings,
    OperatingEnvironment,
    PaperSettings,
    PromotionGates,
    ResearchBudget,
    SecretReference,
)

_ROOT_FIELDS = frozenset(
    {
        "schema_version",
        "environment",
        "research_budget",
        "instrument_universe",
        "promotion_gates",
        "paper",
        "live",
        "secret_references",
    }
)


def _require_exact_fields(
    value: Mapping[str, object],
    expected: frozenset[str],
    path: str,
) -> None:
    actual = frozenset(value)
    missing = sorted(expected - actual)
    unknown = sorted(actual - expected)
    failures: list[str] = []
    if missing:
        failures.append(f"missing fields: {', '.join(missing)}")
    if unknown:
        failures.append(f"unknown fields: {', '.join(unknown)}")
    if failures:
        raise ConfigurationError(f"{path} has {'; '.join(failures)}")


def _table(value: Mapping[str, object], key: str, path: str) -> Mapping[str, object]:
    candidate = value[key]
    if not isinstance(candidate, dict):
        raise ConfigurationError(f"{path}.{key} must be a table")
    return cast(Mapping[str, object], candidate)


def _string(value: Mapping[str, object], key: str, path: str) -> str:
    candidate = value[key]
    if type(candidate) is not str:
        raise ConfigurationError(f"{path}.{key} must be a string")
    return candidate


def _integer(value: Mapping[str, object], key: str, path: str) -> int:
    candidate = value[key]
    if type(candidate) is not int:
        raise ConfigurationError(f"{path}.{key} must be an integer")
    return candidate


def _boolean(value: Mapping[str, object], key: str, path: str) -> bool:
    candidate = value[key]
    if type(candidate) is not bool:
        raise ConfigurationError(f"{path}.{key} must be a boolean")
    return candidate


def _decimal(value: Mapping[str, object], key: str, path: str) -> Decimal:
    candidate = value[key]
    if type(candidate) not in {int, Decimal}:
        raise ConfigurationError(f"{path}.{key} must be a number")
    if type(candidate) is int:
        return Decimal(candidate)
    return cast(Decimal, candidate)


def _string_tuple(value: Mapping[str, object], key: str, path: str) -> tuple[str, ...]:
    candidate = value[key]
    if not isinstance(candidate, list):
        raise ConfigurationError(f"{path}.{key} must be an array")
    strings: list[str] = []
    for index, item in enumerate(cast(list[object], candidate)):
        if type(item) is not str:
            raise ConfigurationError(f"{path}.{key}[{index}] must be a string")
        strings.append(item)
    return tuple(strings)


def _secret_references(value: object) -> tuple[SecretReference, ...]:
    if not isinstance(value, list):
        raise ConfigurationError("configuration.secret_references must be an array of tables")
    references: list[SecretReference] = []
    for index, item in enumerate(cast(list[object], value)):
        path = f"configuration.secret_references[{index}]"
        if not isinstance(item, dict):
            raise ConfigurationError(f"{path} must be a table")
        table = cast(Mapping[str, object], item)
        _require_exact_fields(
            table,
            frozenset({"name", "environment_variable"}),
            path,
        )
        references.append(
            SecretReference(
                name=_string(table, "name", path),
                environment_variable=_string(table, "environment_variable", path),
            )
        )
    return tuple(references)


def _parse_configuration(
    document: Mapping[str, object],
    *,
    expected_environment: OperatingEnvironment,
) -> Configuration:
    _require_exact_fields(document, _ROOT_FIELDS, "configuration")

    environment_value = _string(document, "environment", "configuration")
    try:
        environment = OperatingEnvironment(environment_value)
    except ValueError as error:
        supported = ", ".join(item.value for item in OperatingEnvironment)
        raise ConfigurationError(
            f"configuration.environment must be one of: {supported}"
        ) from error
    if environment is not expected_environment:
        raise ConfigurationError(
            "configuration.environment does not match the expected environment "
            f"{expected_environment.value!r}"
        )

    research_budget_table = _table(document, "research_budget", "configuration")
    _require_exact_fields(
        research_budget_table,
        frozenset(
            {
                "max_experiments",
                "max_parameter_combinations",
                "max_runtime_seconds",
            }
        ),
        "configuration.research_budget",
    )

    instrument_universe_table = _table(
        document,
        "instrument_universe",
        "configuration",
    )
    _require_exact_fields(
        instrument_universe_table,
        frozenset({"symbols"}),
        "configuration.instrument_universe",
    )

    promotion_gates_table = _table(document, "promotion_gates", "configuration")
    _require_exact_fields(
        promotion_gates_table,
        frozenset(
            {
                "require_independent_validation",
                "minimum_observations",
                "minimum_out_of_sample_fraction",
                "maximum_drawdown_fraction",
            }
        ),
        "configuration.promotion_gates",
    )

    paper_table = _table(document, "paper", "configuration")
    _require_exact_fields(
        paper_table,
        frozenset(
            {
                "enabled",
                "starting_cash",
                "max_position_fraction",
                "max_open_positions",
                "leverage_enabled",
                "short_selling_enabled",
            }
        ),
        "configuration.paper",
    )

    live_table = _table(document, "live", "configuration")
    _require_exact_fields(
        live_table,
        frozenset({"enabled", "leverage_enabled", "short_selling_enabled"}),
        "configuration.live",
    )

    return Configuration(
        schema_version=_integer(document, "schema_version", "configuration"),
        environment=environment,
        research_budget=ResearchBudget(
            max_experiments=_integer(
                research_budget_table,
                "max_experiments",
                "configuration.research_budget",
            ),
            max_parameter_combinations=_integer(
                research_budget_table,
                "max_parameter_combinations",
                "configuration.research_budget",
            ),
            max_runtime_seconds=_integer(
                research_budget_table,
                "max_runtime_seconds",
                "configuration.research_budget",
            ),
        ),
        instrument_universe=InstrumentUniverse(
            symbols=_string_tuple(
                instrument_universe_table,
                "symbols",
                "configuration.instrument_universe",
            )
        ),
        promotion_gates=PromotionGates(
            require_independent_validation=_boolean(
                promotion_gates_table,
                "require_independent_validation",
                "configuration.promotion_gates",
            ),
            minimum_observations=_integer(
                promotion_gates_table,
                "minimum_observations",
                "configuration.promotion_gates",
            ),
            minimum_out_of_sample_fraction=_decimal(
                promotion_gates_table,
                "minimum_out_of_sample_fraction",
                "configuration.promotion_gates",
            ),
            maximum_drawdown_fraction=_decimal(
                promotion_gates_table,
                "maximum_drawdown_fraction",
                "configuration.promotion_gates",
            ),
        ),
        paper=PaperSettings(
            enabled=_boolean(paper_table, "enabled", "configuration.paper"),
            starting_cash=_decimal(
                paper_table,
                "starting_cash",
                "configuration.paper",
            ),
            max_position_fraction=_decimal(
                paper_table,
                "max_position_fraction",
                "configuration.paper",
            ),
            max_open_positions=_integer(
                paper_table,
                "max_open_positions",
                "configuration.paper",
            ),
            leverage_enabled=_boolean(
                paper_table,
                "leverage_enabled",
                "configuration.paper",
            ),
            short_selling_enabled=_boolean(
                paper_table,
                "short_selling_enabled",
                "configuration.paper",
            ),
        ),
        live=LiveSettings(
            enabled=_boolean(live_table, "enabled", "configuration.live"),
            leverage_enabled=_boolean(
                live_table,
                "leverage_enabled",
                "configuration.live",
            ),
            short_selling_enabled=_boolean(
                live_table,
                "short_selling_enabled",
                "configuration.live",
            ),
        ),
        secret_references=_secret_references(document["secret_references"]),
    )


def loads_configuration(
    data: str | bytes,
    *,
    expected_environment: OperatingEnvironment,
) -> Configuration:
    """Load configuration from TOML text without reading ambient process state."""
    if type(expected_environment) is not OperatingEnvironment:
        raise ConfigurationError("expected_environment must be an OperatingEnvironment")
    if isinstance(data, bytes):
        try:
            text = data.decode("utf-8")
        except UnicodeDecodeError as error:
            raise ConfigurationError("configuration must be valid UTF-8") from error
    else:
        text = data
    try:
        document = cast(
            Mapping[str, object],
            tomllib.loads(text, parse_float=Decimal),
        )
    except tomllib.TOMLDecodeError as error:
        raise ConfigurationError(f"configuration TOML is invalid: {error}") from error
    return _parse_configuration(document, expected_environment=expected_environment)


def load_configuration(
    path: str | Path,
    *,
    expected_environment: OperatingEnvironment,
) -> Configuration:
    """Load configuration from a local TOML file and fail closed on I/O errors."""
    configuration_path = Path(path)
    try:
        data = configuration_path.read_bytes()
    except OSError as error:
        raise ConfigurationError(
            f"configuration file could not be read: {configuration_path}"
        ) from error
    return loads_configuration(data, expected_environment=expected_environment)

"""Tests for the typed, fail-closed configuration boundary."""

from __future__ import annotations

import json
from dataclasses import FrozenInstanceError
from pathlib import Path

import pytest
from hypothesis import assume, given
from hypothesis import strategies as st

from autonomous_trading.configuration import (
    ConfigurationError,
    OperatingEnvironment,
    load_configuration,
    loads_configuration,
)


def _configuration_toml(
    *,
    environment: str = "research",
    paper_enabled: bool = False,
    paper_leverage_enabled: bool = False,
    paper_short_selling_enabled: bool = False,
    live_enabled: bool = False,
    live_leverage_enabled: bool = False,
    live_short_selling_enabled: bool = False,
    max_experiments: int = 8,
    symbols: str = '"SPY", "TLT"',
    secret_references: str = "",
) -> str:
    secret_section = secret_references or "secret_references = []"
    return f"""
schema_version = 1
environment = "{environment}"
{secret_section}

[research_budget]
max_experiments = {max_experiments}
max_parameter_combinations = 64
max_runtime_seconds = 900

[instrument_universe]
symbols = [{symbols}]

[promotion_gates]
require_independent_validation = true
minimum_observations = 252
minimum_out_of_sample_fraction = 0.25
maximum_drawdown_fraction = 0.20

[paper]
enabled = {str(paper_enabled).lower()}
starting_cash = 100000.00
max_position_fraction = 0.25
max_open_positions = 4
leverage_enabled = {str(paper_leverage_enabled).lower()}
short_selling_enabled = {str(paper_short_selling_enabled).lower()}

[live]
enabled = {str(live_enabled).lower()}
leverage_enabled = {str(live_leverage_enabled).lower()}
short_selling_enabled = {str(live_short_selling_enabled).lower()}
"""


def test_valid_research_configuration_is_typed_and_immutable() -> None:
    """A complete research document becomes immutable typed configuration."""
    configuration = loads_configuration(
        _configuration_toml(),
        expected_environment=OperatingEnvironment.RESEARCH,
    )

    assert configuration.environment is OperatingEnvironment.RESEARCH
    assert configuration.research_budget.max_experiments == 8
    assert configuration.instrument_universe.symbols == ("SPY", "TLT")
    assert configuration.paper.enabled is False
    assert configuration.live.enabled is False

    with pytest.raises(FrozenInstanceError):
        configuration.paper.enabled = True  # pyright: ignore[reportAttributeAccessIssue]


def test_valid_paper_configuration_requires_explicit_paper_environment() -> None:
    """Paper settings activate only when both document and caller expect paper."""
    configuration = loads_configuration(
        _configuration_toml(environment="paper", paper_enabled=True),
        expected_environment=OperatingEnvironment.PAPER,
    )

    assert configuration.environment is OperatingEnvironment.PAPER
    assert configuration.paper.enabled is True
    assert configuration.paper.leverage_enabled is False
    assert configuration.paper.short_selling_enabled is False


@pytest.mark.parametrize(
    "environment",
    [OperatingEnvironment.BACKTEST, OperatingEnvironment.VALIDATION],
)
def test_valid_non_paper_environments_keep_paper_disabled(
    environment: OperatingEnvironment,
) -> None:
    """Backtest and validation configurations remain separate from paper mode."""
    configuration = loads_configuration(
        _configuration_toml(environment=environment.value),
        expected_environment=environment,
    )

    assert configuration.environment is environment
    assert configuration.paper.enabled is False


@pytest.mark.parametrize(
    ("environment", "paper_enabled", "expected_environment"),
    [
        ("research", True, OperatingEnvironment.RESEARCH),
        ("backtest", True, OperatingEnvironment.BACKTEST),
        ("validation", True, OperatingEnvironment.VALIDATION),
        ("paper", False, OperatingEnvironment.PAPER),
    ],
)
def test_paper_environment_mismatches_fail_closed(
    environment: str,
    paper_enabled: bool,
    expected_environment: OperatingEnvironment,
) -> None:
    """Paper enablement cannot contradict the selected environment."""
    with pytest.raises(ConfigurationError, match=r"paper\.enabled must be true only"):
        loads_configuration(
            _configuration_toml(
                environment=environment,
                paper_enabled=paper_enabled,
            ),
            expected_environment=expected_environment,
        )


def test_caller_environment_mismatch_fails_closed() -> None:
    """A research process cannot accidentally consume a paper configuration."""
    with pytest.raises(ConfigurationError, match="does not match the expected environment"):
        loads_configuration(
            _configuration_toml(environment="paper", paper_enabled=True),
            expected_environment=OperatingEnvironment.RESEARCH,
        )


@pytest.mark.parametrize(
    (
        "live_enabled",
        "live_leverage_enabled",
        "live_short_selling_enabled",
        "paper_leverage_enabled",
        "paper_short_selling_enabled",
    ),
    [
        (True, False, False, False, False),
        (False, True, False, False, False),
        (False, False, True, False, False),
        (False, False, False, True, False),
        (False, False, False, False, True),
    ],
)
def test_unsafe_permissions_fail_closed(
    live_enabled: bool,
    live_leverage_enabled: bool,
    live_short_selling_enabled: bool,
    paper_leverage_enabled: bool,
    paper_short_selling_enabled: bool,
) -> None:
    """Live, leveraged, and short-selling permissions are false-only."""
    with pytest.raises(ConfigurationError, match="must remain false"):
        loads_configuration(
            _configuration_toml(
                live_enabled=live_enabled,
                live_leverage_enabled=live_leverage_enabled,
                live_short_selling_enabled=live_short_selling_enabled,
                paper_leverage_enabled=paper_leverage_enabled,
                paper_short_selling_enabled=paper_short_selling_enabled,
            ),
            expected_environment=OperatingEnvironment.RESEARCH,
        )


@given(
    live_enabled=st.booleans(),
    live_leverage_enabled=st.booleans(),
    live_short_selling_enabled=st.booleans(),
    paper_leverage_enabled=st.booleans(),
    paper_short_selling_enabled=st.booleans(),
)
def test_any_unsafe_permission_combination_is_rejected(
    live_enabled: bool,
    live_leverage_enabled: bool,
    live_short_selling_enabled: bool,
    paper_leverage_enabled: bool,
    paper_short_selling_enabled: bool,
) -> None:
    """No combination of unsafe permission flags can pass validation."""
    assume(
        any(
            (
                live_enabled,
                live_leverage_enabled,
                live_short_selling_enabled,
                paper_leverage_enabled,
                paper_short_selling_enabled,
            )
        )
    )

    with pytest.raises(ConfigurationError, match="must remain false"):
        loads_configuration(
            _configuration_toml(
                live_enabled=live_enabled,
                live_leverage_enabled=live_leverage_enabled,
                live_short_selling_enabled=live_short_selling_enabled,
                paper_leverage_enabled=paper_leverage_enabled,
                paper_short_selling_enabled=paper_short_selling_enabled,
            ),
            expected_environment=OperatingEnvironment.RESEARCH,
        )


@pytest.mark.parametrize(
    ("original", "replacement", "expected_message"),
    [
        (
            "schema_version = 1",
            "schema_version = 2",
            "schema_version must be 1",
        ),
        (
            "max_experiments = 8",
            "max_experiments = 0",
            "must be a positive integer",
        ),
        (
            "max_experiments = 8",
            "max_experiments = true",
            "must be an integer",
        ),
        (
            "minimum_out_of_sample_fraction = 0.25",
            "minimum_out_of_sample_fraction = 0.0",
            "must be greater than 0",
        ),
        (
            "maximum_drawdown_fraction = 0.20",
            "maximum_drawdown_fraction = 1.01",
            "must be at most 1",
        ),
        (
            "require_independent_validation = true",
            "require_independent_validation = false",
            "must remain true",
        ),
    ],
)
def test_invalid_versions_types_and_boundaries_fail_closed(
    original: str,
    replacement: str,
    expected_message: str,
) -> None:
    """Schema versions, primitive types, and numeric boundaries are strict."""
    with pytest.raises(ConfigurationError, match=expected_message):
        loads_configuration(
            _configuration_toml().replace(original, replacement),
            expected_environment=OperatingEnvironment.RESEARCH,
        )


def test_decimal_precision_is_preserved_before_safety_validation() -> None:
    """An over-limit decimal cannot round down through binary floating point."""
    document = _configuration_toml().replace(
        "max_position_fraction = 0.25",
        "max_position_fraction = 1.0000000000000001",
    )

    with pytest.raises(ConfigurationError, match="must be at most 1"):
        loads_configuration(
            document,
            expected_environment=OperatingEnvironment.RESEARCH,
        )


@pytest.mark.parametrize(
    ("document", "expected_message"),
    [
        (
            _configuration_toml().replace(
                'environment = "research"',
                'environment = "research"\nunknown = true',
            ),
            "unknown fields: unknown",
        ),
        (
            _configuration_toml().replace("secret_references = []\n", ""),
            "missing fields: secret_references",
        ),
        (
            _configuration_toml().replace("max_runtime_seconds = 900\n", ""),
            "missing fields: max_runtime_seconds",
        ),
        (
            _configuration_toml().replace(
                "max_runtime_seconds = 900",
                "max_runtime_seconds = 900\nunexpected = 1",
            ),
            "unknown fields: unexpected",
        ),
    ],
)
def test_missing_and_unknown_fields_fail_closed(
    document: str,
    expected_message: str,
) -> None:
    """Strict schemas reject both omissions and silent extensions."""
    with pytest.raises(ConfigurationError, match=expected_message):
        loads_configuration(
            document,
            expected_environment=OperatingEnvironment.RESEARCH,
        )


@pytest.mark.parametrize(
    "symbols",
    [
        "",
        '"SPY", "SPY"',
        '"spy"',
        '"SPY", 123',
    ],
)
def test_invalid_instrument_universes_fail_closed(symbols: str) -> None:
    """Instrument universes must be non-empty, unique, and syntactically explicit."""
    with pytest.raises(ConfigurationError):
        loads_configuration(
            _configuration_toml(symbols=symbols),
            expected_environment=OperatingEnvironment.RESEARCH,
        )


def test_secret_references_store_identifiers_not_values() -> None:
    """A valid reference is retained without resolving or storing a secret value."""
    configuration = loads_configuration(
        _configuration_toml(
            secret_references="""
[[secret_references]]
name = "artifact_signing_key"
environment_variable = "RESEARCH_ARTIFACT_SIGNING_KEY"
"""
        ),
        expected_environment=OperatingEnvironment.RESEARCH,
    )

    assert len(configuration.secret_references) == 1
    reference = configuration.secret_references[0]
    assert reference.name == "artifact_signing_key"
    assert reference.environment_variable == "RESEARCH_ARTIFACT_SIGNING_KEY"


@pytest.mark.parametrize(
    ("secret_references", "expected_message"),
    [
        (
            """
[[secret_references]]
name = "artifact_signing_key"
environment_variable = "RESEARCH_ARTIFACT_SIGNING_KEY"
value = "not-allowed"
""",
            "unknown fields: value",
        ),
        (
            """
[[secret_references]]
name = "artifact_signing_key"
environment_variable = "lowercase-is-invalid"
""",
            "must be an uppercase environment variable identifier",
        ),
        (
            """
[[secret_references]]
name = "artifact_signing_key"
environment_variable = "RESEARCH_ARTIFACT_SIGNING_KEY"

[[secret_references]]
name = "artifact_signing_key"
environment_variable = "SECOND_KEY"
""",
            "names must be unique",
        ),
    ],
)
def test_invalid_or_literal_secret_entries_fail_closed(
    secret_references: str,
    expected_message: str,
) -> None:
    """Secret values and ambiguous references cannot cross the boundary."""
    with pytest.raises(ConfigurationError, match=expected_message):
        loads_configuration(
            _configuration_toml(secret_references=secret_references),
            expected_environment=OperatingEnvironment.RESEARCH,
        )


def test_snapshots_are_canonical_and_content_addressed() -> None:
    """Equivalent typed inputs produce stable canonical evidence."""
    first = loads_configuration(
        _configuration_toml(),
        expected_environment=OperatingEnvironment.RESEARCH,
    ).snapshot()
    second = loads_configuration(
        (
            _configuration_toml()
            .replace(
                "max_parameter_combinations = 64\nmax_runtime_seconds = 900",
                "max_runtime_seconds = 900\nmax_parameter_combinations = 64",
            )
            .replace("starting_cash = 100000.00", "starting_cash = 100000.0")
            .replace(
                "maximum_drawdown_fraction = 0.20",
                "maximum_drawdown_fraction = 0.2",
            )
        ),
        expected_environment=OperatingEnvironment.RESEARCH,
    ).snapshot()

    assert first == second
    assert len(first.sha256) == 64
    assert '"live":{"enabled":false' in first.canonical_json


def test_snapshots_preserve_distinct_high_precision_decimal_values() -> None:
    """Snapshot hashing does not round through the active Decimal context."""
    first_value = "0.12345678901234567890123456789"
    second_value = "0.123456789012345678901234567891"
    first = loads_configuration(
        _configuration_toml().replace(
            "minimum_out_of_sample_fraction = 0.25",
            f"minimum_out_of_sample_fraction = {first_value}",
        ),
        expected_environment=OperatingEnvironment.RESEARCH,
    ).snapshot()
    second = loads_configuration(
        _configuration_toml().replace(
            "minimum_out_of_sample_fraction = 0.25",
            f"minimum_out_of_sample_fraction = {second_value}",
        ),
        expected_environment=OperatingEnvironment.RESEARCH,
    ).snapshot()

    first_payload = json.loads(first.canonical_json)
    second_payload = json.loads(second.canonical_json)

    assert first.sha256 != second.sha256
    assert first.canonical_json != second.canonical_json
    assert (
        first_payload["promotion_gates"]["minimum_out_of_sample_fraction"]
        == "12345678901234567890123456789e-29"
    )
    assert (
        second_payload["promotion_gates"]["minimum_out_of_sample_fraction"]
        == "123456789012345678901234567891e-30"
    )


def test_inclusive_numeric_boundaries_are_accepted() -> None:
    """Documented inclusive fractions remain valid at their exact boundaries."""
    document = (
        _configuration_toml()
        .replace(
            "minimum_out_of_sample_fraction = 0.25",
            "minimum_out_of_sample_fraction = 1.0",
        )
        .replace(
            "maximum_drawdown_fraction = 0.20",
            "maximum_drawdown_fraction = 0.0",
        )
        .replace("max_position_fraction = 0.25", "max_position_fraction = 1.0")
    )

    configuration = loads_configuration(
        document,
        expected_environment=OperatingEnvironment.RESEARCH,
    )

    assert str(configuration.promotion_gates.minimum_out_of_sample_fraction) == "1.0"
    assert str(configuration.promotion_gates.maximum_drawdown_fraction) == "0.0"
    assert str(configuration.paper.max_position_fraction) == "1.0"


@given(max_experiments=st.integers(min_value=1, max_value=10_000))
def test_snapshot_hash_is_deterministic_for_repeated_inputs(max_experiments: int) -> None:
    """Repeated identical versioned inputs always produce the same digest."""
    document = _configuration_toml(max_experiments=max_experiments)

    first = loads_configuration(
        document,
        expected_environment=OperatingEnvironment.RESEARCH,
    ).snapshot()
    second = loads_configuration(
        document.encode("utf-8"),
        expected_environment=OperatingEnvironment.RESEARCH,
    ).snapshot()

    assert first.sha256 == second.sha256
    assert first.canonical_json == second.canonical_json


def test_snapshot_hash_changes_with_material_configuration() -> None:
    """A material budget change creates distinct provenance evidence."""
    baseline = loads_configuration(
        _configuration_toml(max_experiments=8),
        expected_environment=OperatingEnvironment.RESEARCH,
    ).snapshot()
    changed = loads_configuration(
        _configuration_toml(max_experiments=9),
        expected_environment=OperatingEnvironment.RESEARCH,
    ).snapshot()

    assert baseline.sha256 != changed.sha256


def test_missing_file_and_malformed_toml_fail_closed(tmp_path: Path) -> None:
    """I/O and TOML parser failures never produce fallback configuration."""
    with pytest.raises(ConfigurationError, match="could not be read"):
        load_configuration(
            tmp_path / "missing.toml",
            expected_environment=OperatingEnvironment.RESEARCH,
        )

    with pytest.raises(ConfigurationError, match="TOML is invalid"):
        loads_configuration(
            "schema_version = [",
            expected_environment=OperatingEnvironment.RESEARCH,
        )

    with pytest.raises(ConfigurationError, match="valid UTF-8"):
        loads_configuration(
            b"\xff",
            expected_environment=OperatingEnvironment.RESEARCH,
        )


def test_parser_value_errors_are_wrapped_as_configuration_errors() -> None:
    """Untrusted numeric literals cannot escape the public error boundary."""
    oversized_integer = "9" * 5_000
    document = _configuration_toml().replace(
        "max_experiments = 8",
        f"max_experiments = {oversized_integer}",
    )

    with pytest.raises(ConfigurationError, match="TOML is invalid") as error:
        loads_configuration(
            document,
            expected_environment=OperatingEnvironment.RESEARCH,
        )

    assert isinstance(error.value.__cause__, ValueError)


def test_unknown_environment_fails_closed() -> None:
    """Only mandate-authorised environment names cross the boundary."""
    with pytest.raises(ConfigurationError, match="must be one of"):
        loads_configuration(
            _configuration_toml(environment="production"),
            expected_environment=OperatingEnvironment.RESEARCH,
        )

# Configuration

## Current boundary

The `autonomous_trading.configuration` package loads schema version 1 TOML into immutable typed
objects. It supports the operating environments permitted by `TRADING_MANDATE.md`:

- `research`
- `backtest`
- `validation`
- `paper`

The caller must state the expected environment when loading a file. A mismatch is an error; a
research process cannot silently consume a paper configuration.

```python
from autonomous_trading.configuration import (
    OperatingEnvironment,
    load_configuration,
)

configuration = load_configuration(
    "research.toml",
    expected_environment=OperatingEnvironment.RESEARCH,
)
snapshot = configuration.snapshot()
print(snapshot.sha256)
```

The loader reads only the supplied local file. It does not inspect environment variables, resolve
secrets, use the wall clock, make network calls, or fall back to defaults.

## Schema version 1

Every field shown below is required. Unknown fields are rejected at every level.

```toml
schema_version = 1
environment = "research"
secret_references = []

[research_budget]
max_experiments = 8
max_parameter_combinations = 64
max_runtime_seconds = 900

[instrument_universe]
symbols = ["SPY", "TLT"]

[promotion_gates]
require_independent_validation = true
minimum_observations = 252
minimum_out_of_sample_fraction = 0.25
maximum_drawdown_fraction = 0.20

[paper]
enabled = false
starting_cash = 100000.00
max_position_fraction = 0.25
max_open_positions = 4
leverage_enabled = false
short_selling_enabled = false

[live]
enabled = false
leverage_enabled = false
short_selling_enabled = false
```

For the `paper` environment, set `environment = "paper"` and `paper.enabled = true`. Paper
enablement in any other environment is rejected. `live.enabled`, both leverage flags, and both
short-selling flags are false-only in schema version 1.

## Secret references

Configuration files may identify where a future, separately authorised runtime should look for a
secret, but they cannot contain the value:

```toml
[[secret_references]]
name = "artifact_signing_key"
environment_variable = "RESEARCH_ARTIFACT_SIGNING_KEY"
```

The loader records these two identifiers and does not read the named environment variable. A
`value`, token, password, broker key, or other unknown field is rejected. Runtime secret resolution
and broker credentials are outside the repository's current authority.

## Snapshots and hashes

`Configuration.snapshot()` returns canonical JSON and its SHA-256 digest. The representation:

- includes the schema version and every material typed setting;
- parses TOML decimal values directly without a binary floating-point round trip;
- serializes decimals from their exact coefficient and exponent without consulting the active
  decimal context;
- normalizes numerically equal decimal values as the same coefficient/exponent strings;
- sorts object keys;
- includes secret reference identifiers but cannot include secret values; and
- is deterministic for identical typed inputs.

Future experiment manifests may attach the digest and canonical JSON as provenance. A snapshot is
evidence of configuration content, not authority to promote, deploy, or trade.

## Failure behaviour

The boundary raises `ConfigurationError` for unreadable files, invalid UTF-8 or TOML (including
numeric conversion failures raised by the parser), unsupported versions or environments,
expected-environment mismatches, missing or unknown fields, invalid types or ranges, duplicate or
malformed instruments, unsafe permission flags, and malformed or duplicate secret references.
There is no permissive fallback configuration.

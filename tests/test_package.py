"""Package bootstrap tests."""

from autonomous_trading import __version__


def test_package_has_a_version() -> None:
    """The package exposes the version used by build metadata."""
    assert __version__ == "0.1.0"

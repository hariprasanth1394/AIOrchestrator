"""Common provider types."""

from dataclasses import dataclass


class ConfigurationError(Exception):
    """A provider cannot start (missing settings or SDK). Never falls back to mock."""


@dataclass
class ProviderResult:
    """What a provider returns for one case.

    Exactly one of raw_output / error is set. token_usage stays None unless
    the provider actually reported it; it is never estimated.
    """

    raw_output: str | None = None
    error: dict | None = None  # {"kind": ..., "message": ...}
    token_usage: dict | None = None

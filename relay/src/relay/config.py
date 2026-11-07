"""Configuration from environment variables.

The composition root is the only place that reads env vars. Every other
module receives plain values from this config object.

Environment variables:
    RELAY_HOST                   (default: "0.0.0.0")
    RELAY_PORT                   (default: 8765)
    RELAY_TOKENS                 (required) "token1:proj1,token2:proj2"
    RELAY_STORE                  (default: "memory") "memory" | "redis"
    RELAY_BUS                    (default: "memory") "memory" | "redis"
    RELAY_REDIS_URL              (default: "redis://localhost:6379/0")
    RELAY_LOG_LEVEL              (default: "INFO")
    RELAY_RATE_CAPACITY          (default: 100)
    RELAY_RATE_REFILL            (default: 10.0)

`RELAY_STORE` and `RELAY_BUS` are read but only "memory" is implemented
in this iteration. Redis adapters land in L7; this config already has
the switch, so L7 only needs to add the adapter files.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field

from relay.domain.types import ProjectId


class ConfigError(ValueError):
    """Raised when the environment is misconfigured."""


def _env(name: str, default: str | None = None) -> str:
    value = os.environ.get(name, default)
    if value is None:
        raise ConfigError(f"missing required environment variable: {name}")
    return value


def _env_int(name: str, default: int) -> int:
    raw = os.environ.get(name)
    if raw is None or raw == "":
        return default
    try:
        return int(raw)
    except ValueError as exc:
        raise ConfigError(f"{name} must be an integer, got {raw!r}") from exc


def _env_float(name: str, default: float) -> float:
    raw = os.environ.get(name)
    if raw is None or raw == "":
        return default
    try:
        return float(raw)
    except ValueError as exc:
        raise ConfigError(f"{name} must be a number, got {raw!r}") from exc


def parse_tokens(raw: str) -> dict[str, ProjectId]:
    """Parse "token1:proj1,token2:proj2" into a mapping.

    Splits each pair on the FIRST colon only, so tokens containing
    colons (e.g. JWT-like tokens during local dev) are preserved.
    Raises ConfigError on malformed input, empty tokens, or duplicate
    tokens (ambiguous mapping is a bug, not a feature).
    """
    if not raw.strip():
        raise ConfigError("RELAY_TOKENS must contain at least one token")
    mapping: dict[str, ProjectId] = {}
    for pair in raw.split(","):
        pair = pair.strip()
        if not pair:
            continue
        if ":" not in pair:
            raise ConfigError(
                f"RELAY_TOKENS entry must be 'token:projectId', got {pair!r}"
            )
        token, project = pair.split(":", 1)
        if not token:
            raise ConfigError(f"empty token in RELAY_TOKENS entry {pair!r}")
        if not project:
            raise ConfigError(f"empty project id in RELAY_TOKENS entry {pair!r}")
        if token in mapping:
            raise ConfigError(f"duplicate token in RELAY_TOKENS: {token!r}")
        mapping[token] = ProjectId(project)
    if not mapping:
        raise ConfigError("RELAY_TOKENS produced no valid tokens")
    return mapping


@dataclass(frozen=True)
class Config:
    host: str
    port: int
    tokens: dict[str, ProjectId]
    store_backend: str
    bus_backend: str
    redis_url: str
    log_level: str
    rate_capacity: int
    rate_refill: float


def load_config() -> Config:
    """Read the process environment and build a Config."""
    store = _env("RELAY_STORE", "memory")
    bus = _env("RELAY_BUS", "memory")
    if store not in {"memory", "redis"}:
        raise ConfigError(f"RELAY_STORE must be 'memory' or 'redis', got {store!r}")
    if bus not in {"memory", "redis"}:
        raise ConfigError(f"RELAY_BUS must be 'memory' or 'redis', got {bus!r}")

    return Config(
        host=_env("RELAY_HOST", "0.0.0.0"),
        port=_env_int("RELAY_PORT", 8765),
        tokens=parse_tokens(_env("RELAY_TOKENS")),
        store_backend=store,
        bus_backend=bus,
        redis_url=_env("RELAY_REDIS_URL", "redis://localhost:6379/0"),
        log_level=_env("RELAY_LOG_LEVEL", "INFO").upper(),
        rate_capacity=_env_int("RELAY_RATE_CAPACITY", 100),
        rate_refill=_env_float("RELAY_RATE_REFILL", 10.0),
    )

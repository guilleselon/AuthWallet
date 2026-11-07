"""Configuration from environment variables."""
from __future__ import annotations

import os
from dataclasses import dataclass

from auth_service.domain.types import ChainId, make_chain_id


class ConfigError(ValueError):
    pass


def _env(name: str, default: str | None = None) -> str:
    v = os.environ.get(name, default)
    if v is None:
        raise ConfigError(f"missing required env var: {name}")
    return v


def _env_int(name: str, default: int) -> int:
    raw = os.environ.get(name)
    if raw is None or raw == "":
        return default
    try:
        return int(raw)
    except ValueError as e:
        raise ConfigError(f"{name} must be int, got {raw!r}") from e


def _env_bool(name: str, default: bool) -> bool:
    raw = os.environ.get(name)
    if raw is None or raw == "":
        return default
    lv = raw.strip().lower()
    if lv in {"1", "true", "yes", "on"}:
        return True
    if lv in {"0", "false", "no", "off"}:
        return False
    raise ConfigError(f"{name} must be bool, got {raw!r}")


def _env_list(name: str) -> tuple[str, ...]:
    raw = os.environ.get(name, "")
    return tuple(x.strip() for x in raw.split(",") if x.strip())


def _parse_chain_id(raw: str) -> ChainId:
    try:
        v = int(raw)
    except ValueError as e:
        raise ConfigError(f"AUTH_CHAIN_ID must be int, got {raw!r}") from e
    try:
        return make_chain_id(v)
    except Exception as e:
        raise ConfigError(f"AUTH_CHAIN_ID invalid: {e}") from e


@dataclass(frozen=True)
class Config:
    host: str
    port: int
    log_level: str
    domain: str
    uri: str
    chain_id: ChainId
    statement: str
    cookie_secret: str
    cookie_name: str
    cookie_secure: bool
    session_ttl_seconds: int
    nonce_ttl_seconds: int
    max_message_age_seconds: int
    cors_origins: tuple[str, ...]
    store_backend: str
    redis_url: str


def load_config() -> Config:
    store = _env("AUTH_STORE", "memory")
    if store not in {"memory", "redis"}:
        raise ConfigError(f"AUTH_STORE must be 'memory' or 'redis', got {store!r}")

    secret = _env("AUTH_COOKIE_SECRET")
    if len(secret) < 32:
        raise ConfigError("AUTH_COOKIE_SECRET must be at least 32 chars")

    return Config(
        host=_env("AUTH_HOST", "127.0.0.1"),
        port=_env_int("AUTH_PORT", 8080),
        log_level=_env("AUTH_LOG_LEVEL", "INFO").upper(),
        domain=_env("AUTH_DOMAIN"),
        uri=_env("AUTH_URI"),
        chain_id=_parse_chain_id(_env("AUTH_CHAIN_ID")),
        statement=_env("AUTH_STATEMENT", "Sign in"),
        cookie_secret=secret,
        cookie_name=_env("AUTH_COOKIE_NAME", "auth_session"),
        cookie_secure=_env_bool("AUTH_COOKIE_SECURE", True),
        session_ttl_seconds=_env_int("AUTH_SESSION_TTL", 86_400),
        nonce_ttl_seconds=_env_int("AUTH_NONCE_TTL", 300),
        max_message_age_seconds=_env_int("AUTH_MAX_MESSAGE_AGE", 600),
        cors_origins=_env_list("AUTH_CORS_ORIGINS"),
        store_backend=store,
        redis_url=_env("REDIS_URL", "redis://localhost:6379/0"),
    )

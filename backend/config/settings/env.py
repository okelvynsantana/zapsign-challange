"""Typed helpers for reading configuration from environment variables.

Every setting in this project is env-driven. These helpers give the settings modules
(and any other consumer) explicit, statically-checkable coercion with a uniform failure
mode: a missing variable with no default raises :class:`MissingEnvVarError`.
"""

import os

__all__ = [
    "MissingEnvVarError",
    "env_bool",
    "env_int",
    "env_list",
    "env_str",
]

_TRUE_VALUES: frozenset[str] = frozenset({"1", "true", "t", "yes", "y", "on"})
_FALSE_VALUES: frozenset[str] = frozenset({"0", "false", "f", "no", "n", "off"})


class MissingEnvVarError(RuntimeError):
    """Raised when a required environment variable is absent and has no default."""

    def __init__(self, name: str) -> None:
        super().__init__(f"Required environment variable {name!r} is not set.")
        self.name = name


def _raw(name: str) -> str | None:
    """Return the stripped raw value of ``name``, or ``None`` when unset/blank."""
    value = os.environ.get(name)
    if value is None:
        return None
    stripped = value.strip()
    return stripped or None


def env_str(name: str, default: str | None = None) -> str:
    """Return ``name`` as a string, falling back to ``default``."""
    value = _raw(name)
    if value is not None:
        return value
    if default is None:
        raise MissingEnvVarError(name)
    return default


def env_bool(name: str, default: bool | None = None) -> bool:
    """Return ``name`` as a boolean (``1/true/yes/on`` vs ``0/false/no/off``)."""
    value = _raw(name)
    if value is None:
        if default is None:
            raise MissingEnvVarError(name)
        return default
    lowered = value.lower()
    if lowered in _TRUE_VALUES:
        return True
    if lowered in _FALSE_VALUES:
        return False
    raise ValueError(f"Environment variable {name!r} is not a valid boolean: {value!r}")


def env_int(name: str, default: int | None = None) -> int:
    """Return ``name`` as an integer, falling back to ``default``."""
    value = _raw(name)
    if value is None:
        if default is None:
            raise MissingEnvVarError(name)
        return default
    try:
        return int(value)
    except ValueError as exc:
        raise ValueError(
            f"Environment variable {name!r} is not a valid integer: {value!r}"
        ) from exc


def env_list(
    name: str,
    default: list[str] | None = None,
    separator: str = ",",
) -> list[str]:
    """Return ``name`` split on ``separator`` with blank entries dropped."""
    value = _raw(name)
    if value is None:
        if default is None:
            raise MissingEnvVarError(name)
        return list(default)
    return [item.strip() for item in value.split(separator) if item.strip()]

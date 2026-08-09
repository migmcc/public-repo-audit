"""Optional scoring configuration.

Category weights are fixed by default. A user may override them with a TOML
file passed explicitly on the command line.

The config is never discovered automatically inside the audited repository.
That is deliberate: this tool audits repositories that the operator may not
control, and a repository that could ship its own weights could raise its own
score.
"""

from __future__ import annotations

import math
import tomllib
from pathlib import Path
from typing import Any

DEFAULT_CATEGORY_WEIGHTS: dict[str, float] = {
    "Identity": 15,
    "Public readiness": 20,
    "Python project health": 25,
    "CI/readiness": 15,
    "Documentation": 15,
    "Safety": 10,
}


class ConfigError(ValueError):
    """Raised when a scoring configuration file cannot be used."""


def load_weights(path: str | Path) -> dict[str, float]:
    """Return category weights from `path`, merged over the defaults.

    A partial table is allowed: unlisted categories keep their default weight.
    """
    config_path = Path(path)
    if not config_path.is_file():
        raise ConfigError(f"Config file not found: {config_path}")

    try:
        with config_path.open("rb") as handle:
            data = tomllib.load(handle)
    except tomllib.TOMLDecodeError as exc:
        raise ConfigError(f"Config file is not valid TOML: {config_path} ({exc})") from exc

    if "weights" not in data:
        raise ConfigError(f"Config file has no [weights] table: {config_path}")

    weights = data["weights"]
    if not isinstance(weights, dict):
        raise ConfigError(f"[weights] must be a table, got {type(weights).__name__}.")

    resolved = dict(DEFAULT_CATEGORY_WEIGHTS)
    known = ", ".join(sorted(DEFAULT_CATEGORY_WEIGHTS))

    for name, value in weights.items():
        if name not in DEFAULT_CATEGORY_WEIGHTS:
            raise ConfigError(f"Unknown category {name!r}. Known categories: {known}.")
        resolved[name] = _coerce_weight(name, value)

    if not any(weight > 0 for weight in resolved.values()):
        raise ConfigError("At least one category weight must be greater than zero.")

    return resolved


def _coerce_weight(name: str, value: Any) -> float:
    # bool is a subclass of int; `weight = true` is a mistake, not a weight of 1.
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ConfigError(
            f"Weight for {name!r} must be a number, got {type(value).__name__}."
        )
    if not math.isfinite(value):
        raise ConfigError(f"Weight for {name!r} must be finite, got {value}.")
    if value < 0:
        raise ConfigError(f"Weight for {name!r} must not be negative, got {value}.")
    return float(value)

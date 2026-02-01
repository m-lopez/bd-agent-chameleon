"""Configuration management for bd-agent-chameleon role definitions."""

import tomllib
from pathlib import Path
from typing import Any

from bd_agent_chameleon.models import Role


class ConfigManager:
    """Loads and provides Role configurations from a TOML file."""

    def __init__(self, config_path: Path) -> None:
        """Initialize with the path to the TOML configuration file."""
        self._config_path: Path = config_path

    def load_role(self, name: str) -> Role:
        """Resolve a role name to a Role from the config file."""
        with open(self._config_path, "rb") as f:
            config: dict[str, Any] = tomllib.load(f)

        if name not in config:
            raise KeyError(f"Role '{name}' not found in {self._config_path}")

        role_data: dict[str, Any] = config[name]
        return Role(
            name=name,
            prompt=role_data["prompt"],
            interactive=role_data["interactive"],
            agent=role_data.get("agent"),
        )

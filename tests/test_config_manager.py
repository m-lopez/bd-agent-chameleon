"""Unit tests for ConfigManager."""

import tomllib
from pathlib import Path

import pytest

from bd_agent_chameleon.config_manager import ConfigManager
from bd_agent_chameleon.models import Role


class TestLoadRole:
    """Tests for ConfigManager.load_role with valid configs."""

    def test_loads_minimal_role(self, tmp_path: Path) -> None:
        """A role with only required fields loads correctly."""
        config_file: Path = tmp_path / "roles.toml"
        config_file.write_text(
            '[reviewer]\nprompt = "Review the code."\ninteractive = false\n'
        )
        mgr: ConfigManager = ConfigManager(config_path=config_file)
        role: Role | None = mgr.load_role("reviewer")

        assert role is not None
        assert role.name == "reviewer"
        assert role.prompt == "Review the code."
        assert role.interactive is False

    def test_loads_interactive_role(self, tmp_path: Path) -> None:
        """A role with interactive=true loads correctly."""
        config_file: Path = tmp_path / "roles.toml"
        config_file.write_text(
            '[writer]\nprompt = "Write docs."\ninteractive = true\n'
        )
        mgr: ConfigManager = ConfigManager(config_path=config_file)
        role: Role | None = mgr.load_role("writer")

        assert role is not None
        assert role.interactive is True

    def test_loads_correct_role_from_multi_role_file(
        self, tmp_path: Path
    ) -> None:
        """The correct role is returned when multiple roles are defined."""
        config_file: Path = tmp_path / "roles.toml"
        config_file.write_text(
            '[reviewer]\nprompt = "Review."\ninteractive = false\n\n'
            '[writer]\nprompt = "Write."\ninteractive = true\n'
        )
        mgr: ConfigManager = ConfigManager(config_path=config_file)

        reviewer: Role | None = mgr.load_role("reviewer")
        writer: Role | None = mgr.load_role("writer")

        assert reviewer is not None
        assert reviewer.name == "reviewer"
        assert reviewer.prompt == "Review."
        assert writer is not None
        assert writer.name == "writer"
        assert writer.prompt == "Write."

    def test_returns_none_for_missing_role(self, tmp_path: Path) -> None:
        """None is returned when the requested role is not in the config."""
        config_file: Path = tmp_path / "roles.toml"
        config_file.write_text(
            '[reviewer]\nprompt = "Review."\ninteractive = false\n'
        )
        mgr: ConfigManager = ConfigManager(config_path=config_file)

        assert mgr.load_role("ghost") is None


class TestLoadRoleErrors:
    """Tests for ConfigManager.load_role error cases."""

    def test_missing_file_raises_file_not_found(self, tmp_path: Path) -> None:
        """FileNotFoundError is raised when the config file does not exist."""
        mgr: ConfigManager = ConfigManager(
            config_path=tmp_path / "nonexistent.toml"
        )

        with pytest.raises(FileNotFoundError):
            mgr.load_role("reviewer")

    def test_malformed_toml_raises_decode_error(
        self, tmp_path: Path
    ) -> None:
        """TOMLDecodeError is raised when the config file is not valid TOML."""
        config_file: Path = tmp_path / "bad.toml"
        config_file.write_text("this is not [valid toml ===")
        mgr: ConfigManager = ConfigManager(config_path=config_file)

        with pytest.raises(tomllib.TOMLDecodeError):
            mgr.load_role("anything")

    def test_missing_prompt_raises_key_error(self, tmp_path: Path) -> None:
        """KeyError is raised when a role is missing the prompt field."""
        config_file: Path = tmp_path / "roles.toml"
        config_file.write_text("[broken]\ninteractive = false\n")
        mgr: ConfigManager = ConfigManager(config_path=config_file)

        with pytest.raises(KeyError):
            mgr.load_role("broken")

    def test_missing_interactive_raises_key_error(
        self, tmp_path: Path
    ) -> None:
        """KeyError is raised when a role is missing the interactive field."""
        config_file: Path = tmp_path / "roles.toml"
        config_file.write_text('[broken]\nprompt = "p"\n')
        mgr: ConfigManager = ConfigManager(config_path=config_file)

        with pytest.raises(KeyError):
            mgr.load_role("broken")

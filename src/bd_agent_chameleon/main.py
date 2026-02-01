"""CLI entry point for bd-agent-chameleon."""

import signal
from datetime import timedelta
from pathlib import Path
from types import FrameType
from typing import Annotated

import typer

from bd_agent_chameleon.beads_task_manager import BeadsTaskManager
from bd_agent_chameleon.chameleon import Chameleon
from bd_agent_chameleon.claude_launcher import ClaudeLauncher
from bd_agent_chameleon.config_manager import ConfigManager

app: typer.Typer = typer.Typer()


@app.command()
def run(
    role: Annotated[str, typer.Option(help="Role name to load from config.")],
    config: Annotated[Path, typer.Option(help="Path to the TOML config file.")],
    db: Annotated[Path, typer.Option(help="Path to the beads database directory.")],
    poll_interval: Annotated[
        float, typer.Option(help="Poll interval in seconds.")
    ] = 2.0,
) -> None:
    """Run bd-agent-chameleon with the given role configuration."""
    config_mgr: ConfigManager = ConfigManager(config)
    task_mgr: BeadsTaskManager = BeadsTaskManager(db)
    launcher: ClaudeLauncher = ClaudeLauncher()
    interval: timedelta = timedelta(seconds=poll_interval)
    chameleon: Chameleon = Chameleon(config_mgr, task_mgr, launcher, role, interval)

    def _handle_signal(signum: int, frame: FrameType | None) -> None:
        """Set chameleon to shutdown on signal."""
        chameleon.shutdown()

    signal.signal(signal.SIGINT, _handle_signal)
    signal.signal(signal.SIGTERM, _handle_signal)

    chameleon.run()


def main() -> None:
    """Entry point for the bd-agent-chameleon CLI."""
    app()


if __name__ == "__main__":
    main()

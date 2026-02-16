"""CLI entry point for bd-agent-chameleon."""

from datetime import timedelta
from pathlib import Path
from typing import Annotated

import typer

from bd_agent_chameleon.beads_task_manager import BeadsTaskManager
from bd_agent_chameleon.chameleon import Chameleon
from bd_agent_chameleon.claude_launcher import ClaudeLauncher
from bd_agent_chameleon.config_manager import ConfigManager
from bd_agent_chameleon.models import RunMode

app: typer.Typer = typer.Typer()


@app.command()
def run(
    config: Annotated[Path, typer.Option(help="Path to the TOML config file.")],
    poll_interval: Annotated[
        float, typer.Option(help="Poll interval in seconds.")
    ] = 2.0,
    mode: Annotated[
        RunMode, typer.Option(help="Execution mode.")
    ] = RunMode.ONE_SHOT,
) -> None:
    """Run bd-agent-chameleon with dynamic role resolution."""
    config_mgr: ConfigManager = ConfigManager(config)
    task_mgr: BeadsTaskManager = BeadsTaskManager()
    launcher: ClaudeLauncher = ClaudeLauncher()
    interval: timedelta = timedelta(seconds=poll_interval)
    chameleon: Chameleon = Chameleon(config_mgr, task_mgr, launcher, interval)

    if mode == RunMode.ONE_SHOT:
        chameleon.run_once()
    else:
        chameleon.run()


def main() -> None:
    """Entry point for the bd-agent-chameleon CLI."""
    app()


if __name__ == "__main__":
    main()

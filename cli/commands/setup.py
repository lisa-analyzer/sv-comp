# Standard library imports
from pathlib import Path

# Standard library imports
from vendor.package_loader import load_packages
load_packages()

# Project-local imports
from cli.models.config import Config

# Third-party imports
import rich
import typer
from rich.prompt import Prompt

# CLI setup
cli = typer.Typer()

@cli.command()
def setup():
    """
        A prompt.
        Points and records (to the local config file) to essential directories for the tool
        (e.g., location of LiSA instance, SV COMP benchmark source files, where to output results)
    """

    config = Config.get()

    if not config.is_empty():
        override_config = Prompt.ask(
            "[bold red]Configuration is not empty![/bold red] [bold]Do you want to override it?[/bold]",
            choices=["y", "n"],
            default="n"
        )

        if override_config != "y":
            raise typer.Exit()

    path_to_sv_comp_dir_str = Prompt.ask("[bold]Enter path to [green]SV-COMP[/green] benchmark directory[/bold]")
    config.path_to_sv_comp_benchmark_dir = __validate_path(path_to_sv_comp_dir_str)

    path_to_lisa_str = Prompt.ask("[bold]Enter path to [cyan]LiSA[/cyan] instance[/bold]")
    config.path_to_lisa_instance = __validate_path(path_to_lisa_str)

    path_to_output_str = Prompt.ask("[bold]Enter path to [magenta]result output[/magenta] directory[/bold]")
    config.path_to_output_dir = __validate_path(path_to_output_str)

    config.save()

    rich.print(
        "[bold magenta]Setup is complete![/bold magenta] "
        "You can now run the tool. Use [bold]--help[/bold] to explore commands like "
        "[yellow]harvest[/yellow] or [yellow]analyse[/yellow]."
    )


def __validate_path(path_str: str) -> Path:
    path: Path = Path(path_str)

    if not path.exists():
        rich.print(f"Specified location [bold red]doesn't exist[/bold red]: {path}")
        raise typer.Exit()

    return path
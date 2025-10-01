# Load vendored packages
from vendor.package_loader import load_packages
load_packages()

# Third-party imports
import typer

# Project-local imports
from cli.utils.util import get_meta_info

# CLI setup
cli = typer.Typer(
    name=get_meta_info("project.name"),
    rich_markup_mode="rich",
    help="This CLI tool is intended to help you work with [bold]SV-COMP benchmark suites[/bold].\n\n",
    no_args_is_help=True,
    add_completion=False,
    epilog=(
        "\n[dim]Developed and maintained by the[/dim] "
        "[bold blue][link=https://unive-ssv.github.io]Software and System Verification (SSV)[/link][/bold blue] group\n"
        "@ Università Ca' Foscari Venezia, Italy"
    )
)

from cli.commands.setup import cli as setup
from cli.commands.harvest import cli as harvest
from cli.commands.analyse import cli as analyse
from cli.commands.statistics import cli as statistics
from cli.commands.version import cli as version

cli.add_typer(setup)
cli.add_typer(harvest)
cli.add_typer(analyse)
cli.add_typer(statistics)
cli.add_typer(version)

if __name__ == "__main__":
    cli()
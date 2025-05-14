# Load vendored packages
from vendor.package_loader import load_packages
load_packages()

# Project-local imports
from cli.utils.util import get_meta_info

# Third-party imports
import rich
import typer

# CLI setup
cli = typer.Typer()

@cli.command()
def version():
    """
        Shows version of the CLI
    """

    version = get_meta_info("project.version")
    rich.print(f"[bold cyan]SV-COMP Helper CLI[/bold cyan] [dim]Version:[/dim] [green]{version}[/green]")
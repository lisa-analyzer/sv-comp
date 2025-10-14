# Standard library imports
import subprocess
import sys

# Load vendored packages
from vendor.package_loader import load_packages
load_packages()

# Project-local imports
from cli.models.config import Config

# Third-party imports
import rich
import typer

# CLI setup
cli = typer.Typer()
config = Config.get()


@cli.command()
def version():
    """
        Shows a version of the LiSA's instance in use
    """

    if config.is_empty():
        typer.echo("Configuration is empty. "
                   "Run [bold]setup[/bold] first and make sure that LiSA instance is specified!")
        raise typer.Exit()

    command = f"{config.path_to_lisa_instance} -v"

    try:
        result = subprocess.run(command, shell=True, check=True, capture_output=True, text=True)
        version = result.stdout.split(":")[1].strip()
        rich.print(f"[green]v{version}[/green]")

    except Exception as e:
        print(f"An unexpected error occurred: {e}", file=sys.stderr)

# Standard library imports
import subprocess
import sys

# Load vendored packages
from vendor.package_loader import load_packages
load_packages()

# Project-local imports
from cli.models.config.config import Config
from cli.models.config.fields.analysis_language import AnalysisLanguage
from cli.utils.util import get_lisa_frontend_main_class

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

    main_class = get_lisa_frontend_main_class(config)

    command = f"java -cp {config.path_to_lisa_instance} {main_class} -v"

    try:
        result = subprocess.run(command, shell=True, check=True, capture_output=True, text=True)
        version = result.stdout.split(":")[1].strip()
        rich.print(f"[green]v{version}[/green]")

    except Exception as e:
        print(f"An unexpected error occurred: {e}", file=sys.stderr)

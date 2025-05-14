# Standard library imports
import sys
import json
import subprocess

# Load vendored packages
from vendor.package_loader import load_packages
load_packages()

# Third-party imports
import rich
import typer

# Project-local imports
from cli.models.config import Config

# CLI setup
cli = typer.Typer()
config = Config.get()

@cli.command()
def analyse():
    """
        Sends collected tasks to the LiSA instance for analysis
    """

    tasks = []
    with open(config.path_to_output_dir / "tasks.json", 'r', encoding='utf-8') as f:
        tasks = json.load(f)

    for task in tasks:
        command = [
            str(config.path_to_lisa_instance),
            "-s", str(task["input_file"]),
            "-o", str(config.path_to_output_dir)
        ]

        rich.print(f"Running command: [bold blue]{' '.join(command)}[/bold blue]")

        try:
            subprocess.run(command, check=True)
            rich.print("[green]Command executed.[/green]")

        except Exception as e:
            print(f"An unexpected error occurred: {e}", file=sys.stderr)
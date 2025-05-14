# Standard library imports
import os
import json
from pathlib import Path
from typing import List

# Load vendored packages
from vendor.package_loader import load_packages
load_packages()

# Third-party imports
import yaml
import rich
import typer

# Project-local imports
from cli.models.config import Config
from cli.utils.util import json_serializer
from cli.models.task_definition.fields.property import Property
from cli.models.task_definition.task_definition import TaskDefinition

# CLI setup
cli = typer.Typer()
config = Config.get()

@cli.command()
def harvest():
    """
        Harvests task definitions (.yml files) and saves them in tasks.json
    """

    if config.is_empty():
        typer.echo("Configuration is empty. Run [bold]setup[/bold] first!")
        raise typer.Exit()

    rich.print("[yellow]Harvesting task definitions from SV-COMP benchmark directory...[/yellow]")
    __construct_task_definition(__harvest_task_definitions())


def __harvest_task_definitions() -> list[str]:
    paths_to_definition_files: list[str] = []

    for root, dirs, files in os.walk(config.path_to_sv_comp_benchmark_dir / "java"):
        for file in files:
            if file.endswith(".yml"):
                paths_to_definition_files.append(os.path.join(root, file))

    return paths_to_definition_files

def __construct_task_definition(paths_to_definition_files: list[str]) -> None:
    definitions: List[TaskDefinition] = []

    for path_str in paths_to_definition_files:
        path = Path(path_str)

        try:
            with path.open("r") as stream:
                task_data = yaml.safe_load(stream)
        except yaml.YAMLError as e:
            rich.print(f"[bold red]Error parsing YAML file:[/bold red] {path}\n{e}")
            continue
        except FileNotFoundError:
            rich.print(f"[bold red]File not found:[/bold red] {path}")
            continue

        input_file = (
            config.path_to_sv_comp_benchmark_dir
            / "java"
            / path.parent
            / task_data["input_files"][1]
            / "Main.java"
        )

        properties = [
            Property(
                property_file=prop["property_file"],
                expected_verdict=prop["expected_verdict"]
            )
            for prop in task_data.get("properties", [])
        ]

        definitions.append(TaskDefinition(
            file_name=path.name,
            path_to_definition=path,
            input_file=input_file,
            properties=properties
        ))

    tasks_file: Path = config.path_to_output_dir / "tasks.json"
    tasks_file.write_text(json.dumps(definitions, indent=4, default=json_serializer))

    rich.print("[green]Task definitions saved to[/green] [italic]tasks.json[/italic].")
    rich.print("Proceed to [bold magenta]analyse[/bold magenta] command.")
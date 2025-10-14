# Standard library imports
import json
import dataclasses
from pathlib import Path
from typing import Optional
from dataclasses import dataclass

# Load vendored packages
from vendor.package_loader import load_packages
load_packages()

# Third-party imports
import typer
import rich
from rich.markup import escape

# Project-local imports
from cli.utils.util import json_serializer

# CLI setup
cli = typer.Typer()

@dataclass
class Config:
    """
        Data model for the application's configuration settings
    """

    path_to_sv_comp_benchmark_dir: Optional[Path] = None
    path_to_lisa_instance: Optional[Path] = None
    path_to_output_dir: Optional[Path] = None

    @classmethod
    def get(cls) -> 'Config':
        """
            Loads configuration from a JSON file. Returns a new Config instance with the loaded settings
        """

        script_dir = Path(__file__).resolve().parents[2]
        config_file = script_dir / "config.json"

        if not config_file.exists():
            rich.print(f"[bold yellow]Missing configuration file.[/bold yellow]")
            return cls()

        config_dict = json.loads(config_file.read_text())
        return cls(
            path_to_sv_comp_benchmark_dir=Path(config_dict.get('path_to_sv_comp_benchmark_dir')) if config_dict.get(
                'path_to_sv_comp_benchmark_dir') else None,
            path_to_lisa_instance=Path(str(Path(__file__).resolve().parents[2]) + "/" + config_dict.get('path_to_lisa_instance')) if config_dict.get(
                'path_to_lisa_instance') else None,
            path_to_output_dir=Path(config_dict.get('path_to_output_dir')) if config_dict.get(
                'path_to_output_dir') else None
        )

    def is_empty(self) -> bool:
        """
            A utility method to check if the configuration is empty
        """

        return (
                self.path_to_sv_comp_benchmark_dir is None and
                self.path_to_lisa_instance is None and
                self.path_to_output_dir is None
        )

    def save(self):
        config_file: Path = Path.cwd() / "config.json"
        config_file.write_text(json.dumps(dataclasses.asdict(self), indent=4, default=json_serializer))
        rich.print(f"[bold green]Saved configuration to:[/bold green] [cyan]{escape(str(config_file))}[/cyan]")

    def validate(self) -> None:
        """
            A utility method to validate the configuration.
            As most of the CLI commands require this check-up, therefore, packed into a single referenceable method
        """

        if self.is_empty():
            typer.echo("Configuration is empty. Run [bold]setup[/bold] first!")
            raise typer.Exit()

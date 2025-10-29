# Standard library imports
import json
import dataclasses
import os
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
from cli.utils.util import json_serializer, resource_path

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

        config_file = resource_path("config.json")

        if not config_file.exists():
            rich.print(f"[bold yellow]Missing configuration file.[/bold yellow]")
            return cls()
        
        config_dict = json.loads(config_file.read_text())
        bench_dir = config_dict.get('path_to_sv_comp_benchmark_dir')
        lisa_inst = config_dict.get('path_to_lisa_instance')
        lisa_inst_clean = lisa_inst[1:-1] if lisa_inst and lisa_inst.endswith('"') else lisa_inst
        lisa_inst_clean = lisa_inst_clean[:-1] if lisa_inst_clean and lisa_inst_clean.endswith('*') else lisa_inst_clean
        if not os.path.exists(lisa_inst_clean):
            lisa_inst = resource_path(config_dict.get('path_to_lisa_instance'))
        out_dir = config_dict.get('path_to_output_dir')
        
        return cls(
            path_to_sv_comp_benchmark_dir=Path(bench_dir) if bench_dir else None,
            path_to_lisa_instance=Path(lisa_inst) if lisa_inst else None,
            path_to_output_dir=Path(out_dir) if out_dir else None
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

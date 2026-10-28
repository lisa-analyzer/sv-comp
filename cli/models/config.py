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
    path_to_jlisa_wit_instance: Optional[Path] = None
    # internal feature flag: on UNKNOWN, look for a violation with the bug-finding mode of jlisa-wit
    enable_find_bug_fallback: bool = False
    find_bug_time_limit: int = 120
    # the numerical domain of jlisa (option -n)
    numerical_domain: str = "ConstantPropagation"
    # whether jlisa writes the JSON graphs of the analyzed methods (off: option --no-graphs)
    jlisa_graphs: bool = True

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
        lisa_inst = cls.__resolve_classpath(config_dict.get('path_to_lisa_instance'))
        jlisa_wit_inst = cls.__resolve_classpath(config_dict.get('path_to_jlisa_wit_instance'))
        out_dir = config_dict.get('path_to_output_dir')
        
        return cls(
            path_to_sv_comp_benchmark_dir=Path(bench_dir) if bench_dir else None,
            path_to_lisa_instance=Path(lisa_inst) if lisa_inst else None,
            path_to_output_dir=Path(out_dir) if out_dir else None,
            path_to_jlisa_wit_instance=Path(jlisa_wit_inst) if jlisa_wit_inst else None,
            enable_find_bug_fallback=config_dict.get('enable_find_bug_fallback', False),
            find_bug_time_limit=config_dict.get('find_bug_time_limit', 120),
            numerical_domain=config_dict.get('numerical_domain', "ConstantPropagation"),
            jlisa_graphs=config_dict.get('jlisa_graphs', True)
        )

    @staticmethod
    def __resolve_classpath(classpath: Optional[str]) -> Optional[str]:
        """
            A classpath (e.g. "jlisa-0.1/lib/*", quotes included) relative to the working directory,
            else to the bundle (see resource_path)
        """

        if not classpath:
            return None
        if os.path.exists(Config.lib_dir(classpath)):
            return classpath
        return str(resource_path(classpath))

    @staticmethod
    def lib_dir(classpath) -> Path:
        """
            The directory of a classpath, without its quotes and trailing *
        """

        return Path(str(classpath).replace('"', '').removesuffix('*'))

    def has_jlisa(self) -> bool:
        return self.path_to_lisa_instance is not None and self.lib_dir(self.path_to_lisa_instance).is_dir()

    def has_jlisa_wit(self) -> bool:
        return self.path_to_jlisa_wit_instance is not None and self.lib_dir(self.path_to_jlisa_wit_instance).is_dir()

    def is_empty(self) -> bool:
        """
            A utility method to check if the configuration is empty
        """

        return (
                self.path_to_sv_comp_benchmark_dir is None and
                self.path_to_lisa_instance is None and
                self.path_to_output_dir is None and
                self.path_to_jlisa_wit_instance is None
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

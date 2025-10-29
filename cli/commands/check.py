# Standard library imports
from pathlib import Path
import subprocess
import shutil
import json
import sys

# Load vendored packages
from vendor.package_loader import load_packages

load_packages()

# Third-party imports
import rich
import typer

# Project-local imports
from cli.models.config import Config
from cli.models.property import Property
from cli.models.lisa_report.lisa_report import LisaReport
from cli.commands.analyse import get_lisa_cmd

# CLI setup
cli = typer.Typer()
config = Config.get()

# Constants
PROPERTY_ASSERT_TEXT = "CHECK( init(Main.main()), LTL(G assert) )\n"
PROPERTY_RUNTIME_TEXT = "CHECK(init(Main.main()), LTL(G ! uncaught(java.lang.RuntimeException)))\n"

@cli.command()
def check(
        inputs: str = typer.Option(
            ...,
            "-i",
            "--inputs",
            help="In double quotes provide input files separated by empty space",
        ),
        property: str = typer.Option(
            ...,
            "-p",
            "--property",
            help="Provide path to the property file or property name to check")):
    """
    Check input files against a specified property
    """

    __clean_output_directory()
    __validate_input_paths(inputs)
    property_to_check = __resolve_property(property)

    lisa_report = __run_analysis(inputs)

    if lisa_report:
        __display_results(property_to_check, lisa_report)


def __clean_output_directory():
    if config.path_to_output_dir and config.path_to_output_dir.exists():
        for item in config.path_to_output_dir.iterdir():
            if item.is_file():
                item.unlink()
            elif item.is_dir():
                shutil.rmtree(item)


def __resolve_property(property: str) -> Property:
    property_path = Path(property)

    if property_path.exists():
        property_content = property_path.read_text()

        if property_content == PROPERTY_ASSERT_TEXT:
            return Property.ASSERT
        elif property_content == PROPERTY_RUNTIME_TEXT:
            return Property.RUNTIME
        else:
            rich.print(f"[bold red]Specified property is not supported:[/bold red] {property_content.strip()}")
            raise typer.Exit(code=1)
    else:
        return Property(property.lower())


def __validate_input_paths(inputs: str) -> list[Path]:
    paths = [Path(p) for p in inputs.split(" ")]

    for path in paths:
        if not path.exists():
            rich.print(f"[bold red]Input file not found:[/bold red] '{path}'")
            rich.print("Please ensure correct path to the input file")
            raise typer.Exit(code=1)

    return paths

def __run_analysis(inputs: str) -> LisaReport | None:
    command = get_lisa_cmd(config, inputs, None, 10)
    (f"java"
                f" -Xmx10G"
                f" -cp {config.path_to_lisa_instance}"
                f" it.unive.jlisa.Main"
                f" -s {inputs}"
                f" -o {config.path_to_output_dir}"
                f" -n ConstantPropagation"
                f" -m Statistics"
                f" -c Assert"
                f" --no-html"
                f" --l ERROR"
            )

    proc = subprocess.Popen(
        command,
        shell=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )
    
    try:
        proc.wait()
        if proc.returncode == 0:
            report_path = config.path_to_output_dir / "report.json"
            with open(report_path, encoding="utf-8") as f:
                return LisaReport(**json.load(f))
        else:
            rich.print(f"[bold red]LiSA analysis failed with exit code {proc.returncode}[/bold red]")
            if proc.stderr:
                error_output = proc.stderr.read().strip()
                rich.print(f"[red]Error: {error_output}[/red]")
        return None
    except Exception as e:
        rich.print(f"[bold red]An unexpected error occurred:[/bold red] {e}")
        print(f"Error details: {e}", file=sys.stderr)
        return None


def __display_results(property: Property, lisa_report: LisaReport):
    if property == Property.ASSERT:
        __display_assert_results(lisa_report)
    elif property == Property.RUNTIME:
        __display_runtime_results(lisa_report)


def __display_assert_results(lisa_report: LisaReport):
    if not lisa_report.has_assert_warnings():
        rich.print("[bold green]NO ASSERT WARNING[/bold green]")
    elif lisa_report.has_possible_assert_warning():
        rich.print("[bold orange3]ASSERT[/bold orange3] [bold yellow]POSSIBLY HOLDS[/bold yellow]")
    elif lisa_report.check_definite_holds_and_not_holds_assert_warnings():
        rich.print("[bold orange3]ASSERT[/bold orange3] [bold green]HOLDS FOR SOME CASES[/bold green] BUT [bold red]NOT FOR OTHERS[/bold red]")
    elif lisa_report.has_definite_holds_assert_warning():
        rich.print("[bold orange3]ASSERT[/bold orange3] [bold green]DOES HOLD[/bold green]")
    elif lisa_report.has_definite_not_holds_assert_warning():
        rich.print("[bold orange3]ASSERT[/bold orange3] [bold red]DOES NOT HOLD[/bold red]")


def __display_runtime_results(lisa_report: LisaReport):
    if not lisa_report.has_runtime_warnings():
        rich.print("[bold green]NO RUNTIME WARNING[/bold green]")
    elif lisa_report.has_possible_runtime_warning():
        rich.print("[bold orange3]RUNTIME[/bold orange3] [bold yellow]POSSIBLY HOLDS[/bold yellow]")
    elif lisa_report.has_definite_holds_assert_warning():
        rich.print("[bold orange3]RUNTIME[/bold orange3] [bold green]DOES HOLD[/bold green]")
    elif lisa_report.has_definite_not_holds_assert_warning():
        rich.print("[bold orange3]RUNTIME[/bold orange3] [bold red]DOES NOT HOLD[/bold red]")

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
from cli.models.property import Property, SVCOMP_NAMES
from cli.models.lisa_report.lisa_report import LisaReport
from cli.commands.analyse import get_lisa_cmd
from cli.utils.util import classify_asserts, AssertClassification, classify_runtime, RuntimeClassification
from cli.utils.jlisa_wit import parse_property, run_jlisa_wit

# CLI setup
cli = typer.Typer()
config = Config.get()

# Constants
PROPERTY_ASSERT_TEXT = "CHECK( init(Main.main()), LTL(G assert) )\n"
PROPERTY_RUNTIME_TEXT = "CHECK(init(Main.main()), LTL(G ! uncaught(java.lang.RuntimeException)))\n"
# the violation witness, in the working directory, where the validators of SV-COMP read it
WITNESS_FILE = "witness.yml"

@cli.command()
def check(
        inputs: list[str] = typer.Argument(
            ...,
            help="The input files and directories of the task",
        ),
        property: str = typer.Option(
            ...,
            "-p",
            "--property",
            help="Provide path to the property file or property name to check")):
    """
    Check input files against a specified property
    """

    if not config.has_jlisa():
        print("jlisa analysis not included in this build", file=sys.stderr)
        print("UNKNOWN")
        raise typer.Exit(code=1)

    __use_writable_output_directory()
    __clean_output_directory()
    Path(WITNESS_FILE).unlink(missing_ok=True)
    __validate_input_paths(inputs)
    property_to_check = __resolve_property(property)

    property_file = property if Path(property).is_file() else None
    if property_file is None:
        print(f"jlisa: {property} is not a property file, no violation witness is written", file=sys.stderr)
    lisa_report = __run_analysis(inputs, property_file)

    if lisa_report:
        __display_results(property_to_check, lisa_report, inputs, property)


def __use_writable_output_directory():
    """
    jlisa writes its results, and the witness, to outputs/ in the working directory, where BenchExec
    collects the result files. The output directory of config.json is a path of the machine where the
    archive was built, outside the working directory of a BenchExec run.
    """
    config.path_to_output_dir = Path.cwd() / "outputs"
    config.path_to_output_dir.mkdir(parents=True, exist_ok=True)


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


def __validate_input_paths(inputs: list[str]) -> list[Path]:
    paths = [Path(p) for p in inputs]

    for path in paths:
        if not path.exists():
            rich.print(f"[bold red]Input file not found:[/bold red] '{path}'")
            rich.print("Please ensure correct path to the input file")
            raise typer.Exit(code=1)

    return paths

def __run_analysis(inputs: list[str], property_file: str | None) -> LisaReport | None:
    command = get_lisa_cmd(config, inputs, None, 10, property_files=[property_file] if property_file else None)

    proc = subprocess.Popen(
        command,
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


def __display_results(property: Property, lisa_report: LisaReport, inputs: list[str], property_file: str):
    if property == Property.ASSERT:
        verdict = classify_asserts(lisa_report).value[1]
    elif property == Property.RUNTIME:
        verdict = classify_runtime(lisa_report).value[1]
    else:
        return
    __keep_witness(property, verdict == "FALSE")
    # bug finding fallback mode only if jlisa returns unknown and the flag is active (experimental).
    if verdict == "UNKNOWN" and config.enable_find_bug_fallback:
        verdict = __find_bug(inputs, property_file)
    __print_verdict(verdict)


def __keep_witness(property: Property, keep: bool):
    """
    jlisa writes the violation witness of a definite violation of the property to
    outputs/witness/<property>/witness.yml. It is moved to the working directory when the verdict is FALSE,
    and removed otherwise.
    """
    witness = config.path_to_output_dir / "witness" / SVCOMP_NAMES[property] / WITNESS_FILE
    if not witness.is_file():
        return
    if keep:
        shutil.move(witness, WITNESS_FILE)
    else:
        witness.unlink()


def __print_verdict(verdict: str):
    match verdict:
        case "TRUE":
            rich.print("[bold green]TRUE[/bold green]")
        case "FALSE":
            rich.print("[bold red]FALSE[/bold red]")
        case "UNKNOWN":
            rich.print("[bold orange3]UNKNOWN[/bold orange3]")


def __find_bug(inputs: list[str], property_file: str) -> str:
    """
    when jlisa returns unknown, look for inputs that violate the property, with the bug-finding mode of
    jlisa-wit (it runs the program and only reports a violation that a run really reaches).
    Returns FALSE if it finds one, otherwise UNKNOWN. It never returns TRUE.
    """
    paths = inputs
    if (not config.has_jlisa_wit() or not Path(property_file).is_file()
            or not all(Path(p).is_dir() for p in paths)):
        return "UNKNOWN"
    property_name = parse_property(property_file)
    if property_name is None:
        return "UNKNOWN"
    time_limit = config.find_bug_time_limit
    try:
        output = run_jlisa_wit(config, paths, property_name, ["--find-bug", "--time-limit", str(time_limit)],
                               timeout=float(time_limit) + 60)
    except (subprocess.TimeoutExpired, OSError) as e:
        print(f"jlisa: UNKNOWN; bug finding failed: {e}", file=sys.stderr)
        return "UNKNOWN"
    found = "Violation found" in [line.strip() for line in output.splitlines()]
    print(f"jlisa: UNKNOWN; bug finding: {'violation found' if found else 'nothing found'}", file=sys.stderr)
    return "FALSE" if found else "UNKNOWN"

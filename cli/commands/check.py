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
from cli.utils.util import classify_asserts, AssertClassification, classify_runtime, RuntimeClassification
from cli.utils.jlisa import BUG_FINDING_TIME_LIMIT, find_bug, get_lisa_cmd

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
            help="Provide path to the property file or property name to check"),
        bug_finding_fallback: bool = typer.Option(
            False,
            "--bug-finding-fallback",
            help="When jlisa ends with UNKNOWN or fails, look for a violation with the bug-finding mode of jlisa-wit"),
        bug_finding_time_limit: int = typer.Option(
            BUG_FINDING_TIME_LIMIT,
            "--bug-finding-time-limit",
            help="Time of the search of the bug-finding fallback, in seconds")):
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

    # the time of the search of the bug-finding fallback, or None without it
    time_limit = bug_finding_time_limit if bug_finding_fallback else None
    if lisa_report:
        __display_results(property_to_check, lisa_report, inputs, property, time_limit)
    else:
        # jlisa failed (e.g., a construct its frontend does not support): only the bug finding can still tell
        __print_verdict(__bug_finding(inputs, property, time_limit) if time_limit else "UNKNOWN")


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
        # reads the output while waiting: a full pipe would block jlisa
        _, errors = proc.communicate()
        if proc.returncode == 0:
            report_path = config.path_to_output_dir / "report.json"
            with open(report_path, encoding="utf-8") as f:
                return LisaReport(**json.load(f))
        else:
            rich.print(f"[bold red]LiSA analysis failed with exit code {proc.returncode}[/bold red]")
            if errors:
                rich.print(f"[red]Error: {errors.strip()}[/red]")
        return None
    except Exception as e:
        rich.print(f"[bold red]An unexpected error occurred:[/bold red] {e}")
        print(f"Error details: {e}", file=sys.stderr)
        return None


def __display_results(property: Property, lisa_report: LisaReport, inputs: list[str], property_file: str,
                      time_limit: int | None):
    if property == Property.ASSERT:
        verdict = classify_asserts(lisa_report).value[1]
    elif property == Property.RUNTIME:
        verdict = classify_runtime(lisa_report).value[1]
    else:
        return
    __keep_witness(property, verdict == "FALSE")
    # the bug-finding fallback, only with --bug-finding-fallback
    if verdict == "UNKNOWN" and time_limit:
        verdict = __bug_finding(inputs, property_file, time_limit)
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


def __bug_finding(inputs: list[str], property_file: str, time_limit: int) -> str:
    """
    The bug-finding fallback, when jlisa ends with UNKNOWN or fails: jlisa-wit looks for inputs that violate the
    property, and writes the violation witness of the violation it finds to the working directory. Returns FALSE
    if it finds one, otherwise UNKNOWN; it never returns TRUE.
    """
    verdict, reason = find_bug(config, inputs, property_file, time_limit, Path(WITNESS_FILE).absolute())
    print(f"jlisa: UNKNOWN; bug finding: {verdict}{f' ({reason})' if reason else ''}", file=sys.stderr)
    return "FALSE" if verdict == "FALSE" else "UNKNOWN"

# Standard library imports
import os
import sys

# Load vendored packages
from vendor.package_loader import load_packages

load_packages()

# Third-party imports
import typer

# Project-local imports
from cli.models.config import Config
from cli.utils.jlisa import jlisa_verdict, run_jlisa_wit

# CLI setup
cli = typer.Typer()
config = Config.get()

# The validator's verdict -> the verdict printed as last line, as for `jlisa check`
# (for a validator, FALSE means that the witness, i.e. the violation, is confirmed; ERROR (invalid witness format)
# means that its version of the witness format is not supported (only 2.4 is), ERROR (parsing failed) that it
# cannot be read, ERROR (invalid witness type) that it is not of the kind given with --type)
VERDICTS = {
    "Witness Correct": "FALSE",
    "Witness Spurious": "TRUE",
    "Could not validate": "UNKNOWN",
    "Invalid witness format": "ERROR (invalid witness format)",
    "Parsing failed": "ERROR (parsing failed)",
    "Invalid witness type": "ERROR (invalid witness type)",
}

# The kinds of witness for --type
WITNESS_TYPES = ("violation", "correctness")


@cli.command()
def validate(
        witness: str = typer.Option(
            ...,
            "-w",
            "--witness",
            help="Provide path to the witness to validate (format 2.4)"),
        property: str = typer.Option(
            ...,
            "-p",
            "--property",
            help="Provide path to the property file"),
        inputs: list[str] = typer.Argument(
            ...,
            help="The input directories of the task"),
        witness_type: str | None = typer.Option(
            None,
            "--type",
            help="The kind of witness expected: violation or correctness. A witness of the other kind gives "
                 "ERROR (invalid witness type) (default: any kind, read from the witness)")):
    """
    Validate a witness against the input files and a specified property
    """

    if not config.has_jlisa():
        print("jlisa not included in this build", file=sys.stderr)
        print("UNKNOWN")
        raise typer.Exit(code=1)

    if not os.path.isfile(witness):
        print(f"witness file not found: {witness}", file=sys.stderr)
        raise typer.Exit(code=1)

    if not os.path.isfile(property):
        print(f"property file not found: {property}", file=sys.stderr)
        raise typer.Exit(code=1)

    if witness_type is not None and witness_type not in WITNESS_TYPES:
        print(f"--type must be violation or correctness, not {witness_type}", file=sys.stderr)
        raise typer.Exit(code=1)

    # jlisa-wit reads the property file, and cannot validate other properties
    output = run_jlisa_wit(config, "validate", inputs, property,
                           ["--witness", os.path.abspath(witness)] + (["--type", witness_type] if witness_type else []))

    verdict = jlisa_verdict(output)
    if verdict not in VERDICTS:
        verdict = "Could not validate"
    # the validator's own verdict on stderr (in the log), before the verdict, which must be the last line
    print(verdict, file=sys.stderr, flush=True)
    print(VERDICTS[verdict])

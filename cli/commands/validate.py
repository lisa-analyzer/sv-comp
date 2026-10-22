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
from cli.utils.jlisa_wit import parse_property, run_jlisa_wit

# CLI setup
cli = typer.Typer()
config = Config.get()

# The validator's verdict -> the verdict printed as last line, as for `jlisa check`
# (for a validator, FALSE means that the witness, i.e. the violation, is confirmed)
VERDICTS = {
    "Witness Correct": "FALSE",
    "Witness Spurious": "TRUE",
    "Could not validate": "UNKNOWN",
}


@cli.command()
def validate(
        witness: str = typer.Option(
            ...,
            "-w",
            "--witness",
            help="Provide path to the violation witness to validate"),
        property: str = typer.Option(
            ...,
            "-p",
            "--property",
            help="Provide path to the property file"),
        inputs: str = typer.Option(
            ...,
            "-i",
            "--inputs",
            help="In double quotes provide input directories separated by empty space")):
    """
    Validate a violation witness against the input files and a specified property
    """

    if not config.has_jlisa_wit():
        print("jlisa-wit not included in this build", file=sys.stderr)
        print("UNKNOWN")
        raise typer.Exit(code=1)

    if not os.path.isfile(witness):
        print(f"witness file not found: {witness}", file=sys.stderr)
        raise typer.Exit(code=1)

    if not os.path.isfile(property):
        print(f"property file not found: {property}", file=sys.stderr)
        raise typer.Exit(code=1)

    property_name = parse_property(property)
    if property_name is None:
        print(f"unsupported property: {property}", file=sys.stderr)
        raise typer.Exit(code=1)

    paths = [p for p in inputs.split(" ") if p]
    output = run_jlisa_wit(config, paths, property_name, ["--witness", os.path.abspath(witness)])

    verdicts = [line.strip() for line in output.splitlines() if line.strip() in VERDICTS]
    verdict = verdicts[-1] if verdicts else "Could not validate"
    # the validator's own verdict on stderr (in the log), before the verdict, which must be the last line
    print(verdict, file=sys.stderr, flush=True)
    print(VERDICTS[verdict])

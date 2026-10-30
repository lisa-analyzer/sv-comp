# Load vendored packages
from vendor.package_loader import load_packages
load_packages()

# Project-local imports
from cli.models.config import Config

# Third-party imports
import typer

# CLI setup
cli = typer.Typer()
config = Config.get()


@cli.command()
def components():
    """
        Lists the tools included in this build, one per line: jlisa (check) and jlisa-wit (validate, and the
        bug-finding fallback of check), both from the jlisa package
    """

    if config.has_jlisa():
        print("jlisa")
        print("jlisa-wit")

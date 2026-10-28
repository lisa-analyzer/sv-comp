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
        Lists the tools included in this build, one per line: jlisa (check) and jlisa-wit (validate), and
        find-bug when check falls back to the bug-finding mode of jlisa-wit on UNKNOWN
    """

    if config.has_jlisa():
        print("jlisa")
    if config.has_jlisa_wit():
        print("jlisa-wit")
    if config.has_jlisa() and config.has_jlisa_wit() and config.enable_find_bug_fallback:
        print("find-bug")

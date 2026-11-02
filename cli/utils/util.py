# Standard library imports
import json
import tomllib
import dataclasses
import sys
from pathlib import Path
from enum import Enum

from cli.models.lisa_report.lisa_report import LisaReport

def json_serializer(obj):
    """
        Converts path objects or other complex types to strings for JSON serialization
    """

    if isinstance(obj, Path):
        return str(obj)
    elif dataclasses.is_dataclass(obj):
        return dataclasses.asdict(obj)
    else:
        return json.JSONEncoder.default(obj)

def resource_path(relative_path: str) -> Path:
    """
    Get the absolute path to a resource, works for dev and PyInstaller bundle.

    When running as a PyInstaller bundle, files are unpacked to a temporary folder
    accessible via sys._MEIPASS. This function returns the correct path to the resource.

    Args:
        relative_path: Relative path to the resource file inside your project or bundle.

    Returns:
        An absolute Path object to the resource.
    """
    if hasattr(sys, '_MEIPASS'):
        # Running in PyInstaller bundle
        base_path = Path(sys._MEIPASS)
    else:
        # Running in normal Python environment
        base_path = Path(__file__).resolve().parent.parent.parent

    return base_path / relative_path

def get_meta_info(field: str):
    """
        Get field value from a pyproject.toml
    """
    pyproject_path = resource_path("pyproject.toml")

    if not pyproject_path.exists():
        raise FileNotFoundError(f"pyproject.toml not found at {pyproject_path}")
    
    with pyproject_path.open("rb") as f:
        data = tomllib.load(f)

    keys = field.split(".")
    try:
        for key in keys:
            data = data[key]
        return data
    except (KeyError, TypeError):
        raise KeyError(f"Field '{field}' not found in {pyproject_path}")

class AssertClassification(Enum):
    ### FORMAT: (code, sv-comp verdict)
    # jlisa issues a possible warning for each assertion that the analysis cannot prove, and then verifies
    # them: a warning is either confirmed (definite), refuted, or left possible

    # no warnings are issued: the analysis proves all assertions
    NO_WARNINGS = 1, "TRUE"

    # all warnings are refuted by their verification
    ONLY_REFUTED = 2, "TRUE"

    # some warnings are possible, and none is definite
    POSSIBLE = 3, "UNKNOWN"

    # some warning is definite: its violation has been confirmed
    DEFINITE = 4, "FALSE"


def classify_asserts(lisa_report: LisaReport):
    if not lisa_report.has_assert_warnings():
        return AssertClassification.NO_WARNINGS
    elif lisa_report.has_definite_assert_warning():
        return AssertClassification.DEFINITE
    elif lisa_report.has_only_refuted_assert_warnings():
        return AssertClassification.ONLY_REFUTED
    return AssertClassification.POSSIBLE


class RuntimeClassification(Enum):
    ### FORMAT: (code, sv-comp verdict)
    # as for assertions, with the warnings about uncaught runtime exceptions

    # no warnings are issued: the analysis proves that no runtime exception escapes the main method
    NO_WARNINGS = 1, "TRUE"

    # all warnings are refuted by their verification
    ONLY_REFUTED = 2, "TRUE"

    # some warnings are possible, and none is definite
    POSSIBLE = 3, "UNKNOWN"

    # some warning is definite: an uncaught runtime exception has been confirmed
    DEFINITE = 4, "FALSE"


def classify_runtime(lisa_report: LisaReport):
    if not lisa_report.has_runtime_warnings():
        return RuntimeClassification.NO_WARNINGS
    elif lisa_report.has_definite_runtime_warning():
        return RuntimeClassification.DEFINITE
    elif lisa_report.has_only_refuted_runtime_warnings():
        return RuntimeClassification.ONLY_REFUTED
    return RuntimeClassification.POSSIBLE

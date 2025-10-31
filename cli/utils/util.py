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

    # no warnings are issued
    NO_WARNINGS = 1, "TRUE" # was UNKNOWN

    # only "assertion definitely holds" warnings are issued
    ONLY_DEFINITE_HOLDS = 2, "TRUE"
    
    # only "assertion possibly does not hold" warnings are issued
    ONLY_POSSIBLE_NOT_HOLDS = 3, "UNKNOWN"
    
    # only "assertion definitely does not hold" warnings are issued
    ONLY_DEFINITE_NOT_HOLDS = 4, "FALSE" # was UNKNOWN
    
    # both "assertion possibly does not hold" 
    # and "assertion definitely does not hold" warnings are issued,
    # but no "assertion definitely holds" warning is issued
    CONFLICTING_NOT_HOLDS = 5, "UNKNOWN"

    # both "assertion definitely holds" 
    # and "assertion definitely does not hold" warnings are issued,
    # but no "assertion possibly does not hold" warning is issued
    CONFLICTING_HOLDS_AND_NOT_HOLDS = 6, "FALSE" # was UNKNOWN

    # both "assertion definitely holds" 
    # and "assertion possibly does not hold" warnings are issued,
    # but no "assertion definitely does not hold" warning is issued
    CONFLICTING_HOLDS_AND_POSSIBLY_NOT_HOLDS = 7, "UNKNOWN"

    # "assertion definitely holds", 
    # "assertion definitely does not hold", 
    # and "assertion possibly does not hold" warnings are issued
    ALL = 8, "FALSE" # was UNKNOWN
    
    # unknown classification
    UNKNOWN = 9, "UNKNOWN"

def classify_asserts(lisa_report: LisaReport):
    if not lisa_report.has_assert_warnings():
        return AssertClassification.NO_WARNINGS
    elif lisa_report.has_only_definite_holds_assert_warning():
        return AssertClassification.ONLY_DEFINITE_HOLDS
    elif lisa_report.has_only_possibly_not_holds_assert_warning():
        return AssertClassification.ONLY_POSSIBLE_NOT_HOLDS
    elif lisa_report.has_only_definite_not_holds_assert_warning():
        return AssertClassification.ONLY_DEFINITE_NOT_HOLDS
    elif lisa_report.has_possibly_not_holds_assert_warning() and lisa_report.has_definite_not_holds_assert_warning() and not lisa_report.has_definite_holds_assert_warning():
        return AssertClassification.CONFLICTING_NOT_HOLDS
    elif not lisa_report.has_possibly_not_holds_assert_warning() and lisa_report.has_definite_not_holds_assert_warning() and lisa_report.has_definite_holds_assert_warning():
        return AssertClassification.CONFLICTING_HOLDS_AND_NOT_HOLDS
    elif lisa_report.has_possibly_not_holds_assert_warning() and not lisa_report.has_definite_not_holds_assert_warning() and not lisa_report.has_definite_holds_assert_warning():
        return AssertClassification.CONFLICTING_HOLDS_AND_POSSIBLY_NOT_HOLDS
    elif lisa_report.has_possibly_not_holds_assert_warning() and lisa_report.has_definite_not_holds_assert_warning() and lisa_report.has_definite_holds_assert_warning():
        return AssertClassification.ALL
    return AssertClassification.UNKNOWN

class RuntimeClassification(Enum):
    ### FORMAT: (code, sv-comp verdict)
    
    # no warnings are issued
    NO_WARNINGS = 1, "TRUE"
    
    # only "possible runtime exception" warnings are issued
    ONLY_POSSIBLE_NOT_HOLDS = 2, "UNKNOWN"
    
    # only "definite runtime exception" warnings are issued
    ONLY_DEFINITE_NOT_HOLDS = 3, "FALSE"

    # both "possible runtime exception" and "definite runtime exception" warnings are issued
    CONFLICTING_NOT_HOLDS = 4, "FALSE"
    
    # unknown classification
    UNKNOWN = 5, "UNKNOWN"

def classify_runtime(lisa_report: LisaReport):
    if not lisa_report.has_runtime_warnings():
        return RuntimeClassification.NO_WARNINGS
    elif lisa_report.has_only_possibly_not_holds_runtime_warning():
        return RuntimeClassification.ONLY_POSSIBLE_NOT_HOLDS
    elif lisa_report.has_only_definite_not_holds_runtime_warning():
        return RuntimeClassification.ONLY_DEFINITE_NOT_HOLDS
    elif lisa_report.has_possibly_not_holds_runtime_warning() and lisa_report.has_definite_not_holds_runtime_warning():
        return RuntimeClassification.CONFLICTING_NOT_HOLDS
    return RuntimeClassification.UNKNOWN
# Standard library imports
import json
import tomllib
import dataclasses
import sys
from pathlib import Path

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

# Standard library imports
import json
import tomllib
import dataclasses
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


def get_meta_info(field: str):
    """
        Get field value from a pyproject.toml
    """

    pyproject_path = Path.cwd() / "pyproject.toml"
    with pyproject_path.open("rb") as f:
        data = tomllib.load(f)

    keys = field.split(".")
    try:
        for key in keys:
            data = data[key]
        return data
    except (KeyError, TypeError):
        raise KeyError(f"Field '{field}' not found in {pyproject_path}")
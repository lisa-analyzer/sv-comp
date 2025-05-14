# Standard library imports
from typing import List
from pathlib import Path
from dataclasses import dataclass

# Project-local imports
from cli.models.task_definition.fields.property import Property

@dataclass
class TaskDefinition:
    """
        Represents the definition of a task
    """

    file_name: str
    path_to_definition: Path
    input_file: Path
    properties: List[Property]
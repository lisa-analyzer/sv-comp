# Standard library imports
from typing import List, Optional
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

    def __init__(self, file_name:str, path_to_definition: Path, input_file:Path, properties: List[Property]):
        self.file_name = file_name
        self.path_to_definition = path_to_definition
        self.input_file = input_file
        self.properties = [
            p if isinstance(p, Property) else Property(**p)
            for p in properties
        ]

    def are_assertions_expected(self) -> Optional[bool]:
        for prop in self.properties:
            if "assert" in prop.property_file:
                return prop.expected_verdict
        return None

    def are_runtime_exceptions_expected(self) -> Optional[bool]:
        for prop in self.properties:
            if "runtime-exception" in prop.property_file:
                return prop.expected_verdict
        return None
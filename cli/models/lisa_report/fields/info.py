# Standard library imports
from dataclasses import dataclass

@dataclass
class Info:
    """
        Represents an 'info' field of a LiSA's 'report' JSON file
    """

    warnings: int

    def __init__(self, warnings, **_):
        self.warnings = int(warnings)
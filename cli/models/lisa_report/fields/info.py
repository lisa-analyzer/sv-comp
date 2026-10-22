# Standard library imports
from dataclasses import dataclass


@dataclass
class Info:
    """
    Represents an 'info' field of a LiSA's 'report' JSON file
    """

    warnings: int
    notices: int

    def __init__(self, warnings, notices=0, **_):
        self.warnings = int(warnings)
        self.notices = int(notices)

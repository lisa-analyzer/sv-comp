# Standard library imports
from dataclasses import dataclass

@dataclass
class Property:
    """
        Represents a single 'properties' field of a task definition
        E.g.:
        properties:
            - property_file: ../properties/assert_java.prp
              expected_verdict: false
    """

    property_file: str
    expected_verdict: bool
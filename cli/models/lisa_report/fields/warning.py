# Standard library imports
import re
from dataclasses import dataclass

@dataclass
class Warning:
    """
        Represents a 'warning' field of a LiSA's 'report' JSON file
    """

    message: str

    def extract_warning(self) -> str:
        """
        Extracts the analysis warning (e.g. how assertion holds, etc.)
        """

        if not self.message:
            return ""
        match = re.search(r"\[[A-Z]+\]\s*(.*)$", self.message)
        return match.group(1) if match else ""

    def is_assertion_warning(self) -> bool:
        return "the assertion" in self.extract_warning()

    def is_runtime_warning(self) -> bool:
        return "uncaught runtime exception" in self.extract_warning()
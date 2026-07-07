# Standard library imports
import re
from dataclasses import dataclass


@dataclass
class Warning:
    """
    Represents a 'notice' field of a LiSA's 'report' JSON file
    """

    message: str

    def extract_notice(self) -> str:
        """
        Extracts the analysis notice (e.g. some event happened, etc.)
        """

        if not self.message:
            return ""
        match = re.search(r"\[[A-Z]+\]\s*(.*)$", self.message)
        return match.group(1) if match else ""

    def is_bottom_notice(self) -> bool:
        return "Analysis produced" in self.extract_notice()

    def is_open_call_notice(self) -> bool:
        return "to any target and is thus open" in self.extract_notice()

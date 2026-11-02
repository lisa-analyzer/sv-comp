# Standard library imports
from dataclasses import dataclass


@dataclass
class Notice:
    """
    Represents a 'notice' field of a LiSA's 'report' JSON file
    """

    message: str
    location: str | None = None
    cfg: str | None = None
    text: str | None = None
    context: str | None = None
    target_kind: str | None = None

    def __init__(self, message, location=None, cfg=None, text=None, context=None, targetKind=None, **_):
        self.message = message
        self.location = location
        self.cfg = cfg
        self.text = text
        self.context = context
        self.target_kind = targetKind

    def extract_notice(self) -> str:
        """
        Extracts the analysis notice (e.g. some event happened, etc.)
        """

        return self.message or ""

    def describe(self) -> str:
        """
        The notice with where it was issued, e.g. "['Main.java':3:4] on 'void Main::main(...)': <message>"
        """

        where = f"[{self.location}]" if self.location else ""
        if self.cfg:
            where += f" on '{self.cfg}'"
        if self.context:
            where += f" in context {self.context}"
        return f"{where}: {self.message}" if where else self.message

    def is_bottom_notice(self) -> bool:
        return "Analysis produced" in self.extract_notice()

    def is_open_call_notice(self) -> bool:
        return "to any target and is thus open" in self.extract_notice()

# Standard library imports
from dataclasses import dataclass, field

# The messages of the warnings issued by the assert checker of jlisa, one for each property
ASSERTION_MESSAGE = "the assertion might not hold"
RUNTIME_MESSAGE = "uncaught runtime exception in main method"


@dataclass
class ReproducingInput:
    """
    Represents a reproducing input of a confirmed warning: the value that a source (e.g., the return of a
    nondeterministic call, or a parameter) takes in an execution that reproduces the warning
    """

    source: str
    value: str
    location: str | None = None
    type: str | None = None

    def __init__(self, source, value, location=None, type=None, **_):
        self.source = source
        self.value = value
        self.location = location
        self.type = type


@dataclass
class Warning:
    """
    Represents a 'warning' field of a LiSA's 'report' JSON file. Checks issue possible warnings, and the
    verification of warnings then either confirms them (definite, with the inputs that reproduce them, if
    any) or refutes them (refuted: they are false alarms). Warnings that are neither confirmed nor refuted
    stay possible.
    """

    message: str
    location: str | None = None
    cfg: str | None = None
    text: str | None = None
    context: str | None = None
    target_kind: str | None = None
    definite: bool = False
    refuted: bool = False
    reproducing_inputs: list[ReproducingInput] = field(default_factory=list)

    def __init__(self, message, location=None, cfg=None, text=None, context=None, targetKind=None,
                 definite=False, refuted=False, reproducingInputs=(), **_):
        self.message = message
        self.location = location
        self.cfg = cfg
        self.text = text
        self.context = context
        self.target_kind = targetKind
        self.definite = bool(definite)
        self.refuted = bool(refuted)
        self.reproducing_inputs = [
            ReproducingInput(**i) if isinstance(i, dict) else i for i in (reproducingInputs or ())
        ]

    def is_assertion_warning(self) -> bool:
        return self.message == ASSERTION_MESSAGE

    def is_runtime_warning(self) -> bool:
        return self.message == RUNTIME_MESSAGE

    def is_possible(self) -> bool:
        """
        Whether the warning has been neither confirmed nor refuted
        """
        return not self.definite and not self.refuted

# Standard library imports
from dataclasses import dataclass, field

# The messages of the warnings issued by the assert checker of jlisa, one for each property
ASSERTION_MESSAGE = "the assertion might not hold"
RUNTIME_MESSAGE = "uncaught runtime exception in main method"

# The reasons why the verification of a warning can leave it possible, as the text of the explanations of the
# verifiers of LiSA identifies them. An explanation (that may span several lines, e.g., when several analysis results
# were verified, or when a counterexample contains strings with newlines) can give more than one reason (e.g., a
# counterexample that both starts in a callee and relies on imprecise values).
POSSIBLE_REASONS = [
    ("not verified: the verification stopped at the first confirmed warning", "not verified (stopped at the first confirmed warning)"),
    ("from states that are not the initial ones of the program", "counterexample from a callee context"),
    ("relying on values that are not computed precisely", "counterexample relying on imprecise values"),
    ("budget exhausted", "budget exhausted"),
    ("but no inductive invariant found", "bound reached, no inductive invariant"),
    ("no violation found within", "bound reached"),
    ("no SMT solver available", "no SMT solver"),
    ("the solver could not decide", "solver could not decide"),
    ("the solver failed", "solver failure"),
    ("the verification failed", "verification failure"),
    ("no analysis result for the context of the warning", "no analysis result"),
    ("the warning reports no violation to verify", "no violation to verify"),
]
# The reason of a possible warning whose verification gave no explanation
UNEXPLAINED = "unexplained"
# The reason of a possible warning whose explanation gives no known reason, followed by the start of the explanation
OTHER = "other"
# How many characters of an explanation with no known reason are kept
OTHER_LENGTH = 60


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
    # why the verification confirmed, refuted, or left possible the warning, if known
    explanation: str | None = None

    def __init__(self, message, location=None, cfg=None, text=None, context=None, targetKind=None,
                 definite=False, refuted=False, reproducingInputs=(), explanation=None, **_):
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
        self.explanation = explanation

    def is_assertion_warning(self) -> bool:
        return self.message == ASSERTION_MESSAGE

    def is_runtime_warning(self) -> bool:
        return self.message == RUNTIME_MESSAGE

    def is_possible(self) -> bool:
        """
        Whether the warning has been neither confirmed nor refuted
        """
        return not self.definite and not self.refuted

    def possible_reasons(self) -> set[str]:
        """
        Why the verification left the warning possible, as POSSIBLE_REASONS (UNEXPLAINED without an explanation;
        OTHER followed by the start of the explanation, on a single line and without separators, when no known
        reason matches it). Empty if the warning is not possible.
        """
        if not self.is_possible():
            return set()
        if not self.explanation:
            return {UNEXPLAINED}
        reasons = {reason for text, reason in POSSIBLE_REASONS if text in self.explanation}
        if reasons:
            return reasons
        start = " ".join(self.explanation.split())[:OTHER_LENGTH].replace(";", ",").replace(": ", " ")
        return {f"{OTHER} ({start})"}

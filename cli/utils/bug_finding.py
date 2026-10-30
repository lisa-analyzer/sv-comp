# Standard library imports
import json
import os
from pathlib import Path

# Load vendored packages
from vendor.package_loader import load_packages

load_packages()

# Project-local imports
from cli.models.config import Config
from cli.models.lisa_report.lisa_report import LisaReport
from cli.models.property import Property, SVCOMP_NAMES
from cli.models.task_definition.task_definition import TaskDefinition
from cli.utils.jlisa import find_bug, property_files
from cli.utils.util import classify_asserts, classify_runtime

# The folder, in the results of a task, with the verdict of the bug-finding fallback on each property
# (<property>.txt: the verdict, then the reason of jlisa-wit)
BUG_FINDING_DIR = "bug-finding"
# The files that jlisa writes in the results of a task when it fails, as the statistics read them
ERROR_FILES = ("frontend.csv", "frontend-noparsing.csv", "analysis.csv")


def jlisa_verdict(results_dir: Path, property: Property) -> str:
    """
    The verdict of jlisa on the property, from the results of its analysis: UNKNOWN when it failed (one of
    ERROR_FILES, or no report), as the statistics count it.
    """
    report = results_dir / "report.json"
    if any((results_dir / name).is_file() for name in ERROR_FILES) or not report.is_file():
        return "UNKNOWN"
    with open(report, encoding="utf-8") as f:
        lisa_report = LisaReport(**json.load(f))
    classification = classify_asserts(lisa_report) if property == Property.ASSERT else classify_runtime(lisa_report)
    return classification.value[1]


def run_bug_finding_fallback(config: Config, task: TaskDefinition, results_dir: Path, time_limit: int):
    """
    The bug-finding fallback of `check`, on the results of the analysis of a task: for each property where jlisa
    ends with UNKNOWN (or fails), jlisa-wit looks for a violation. Its witness replaces the one of jlisa in
    witness/<property>/witness.yml (as in `check`, the witness of jlisa is only kept with FALSE), and its
    verdict and reason go to bug-finding/<property>.txt.
    """
    properties = {name: property for property, name in SVCOMP_NAMES.items()}
    for property_file in property_files(task):
        name = Path(property_file).stem
        if jlisa_verdict(results_dir, properties[name]) != "UNKNOWN":
            continue
        witness = results_dir / "witness" / name / "witness.yml"
        verdict, reason = find_bug(config, str(task.input_file).split(), property_file, time_limit, witness)
        result = results_dir / BUG_FINDING_DIR / f"{name}.txt"
        result.parent.mkdir(parents=True, exist_ok=True)
        result.write_text(f"{verdict}\n{reason}\n")


def read_bug_finding(results_dir: str, property: Property) -> str:
    """
    The verdict of the bug-finding fallback on the property (first line of bug-finding/<property>.txt), or ""
    if it did not run on it.
    """
    result = os.path.join(results_dir, BUG_FINDING_DIR, f"{SVCOMP_NAMES[property]}.txt")
    if not os.path.isfile(result):
        return ""
    with open(result, encoding="utf-8") as f:
        return f.readline().strip()

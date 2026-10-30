# Standard library imports
import csv
import os
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

# Load vendored packages
from vendor.package_loader import load_packages

load_packages()

# Third-party imports
import rich

# Project-local imports
from cli.models.config import Config
from cli.models.task_definition.task_definition import TaskDefinition
from cli.utils.jlisa import WITNESS_CORRECT, validate_witness

# The file, next to each witness, with the verdict of jlisa-wit on it (first line) and its reason
VALIDATION_FILE = "validation.txt"


def validate_run_witnesses(config: Config, witnesses: list[tuple[TaskDefinition, str]], timeout: int,
                           parallelism: int):
    """
    Validates with jlisa-wit the violation witnesses that jlisa wrote in a run, one for each task and property
    file given, in results/<task>/witness/<property>/witness.yml (those that do not exist are skipped).
    Writes the verdict of jlisa-wit and its reason to validation.txt next to each witness (read by the
    statistics), and all of them to witness-validation.csv in the output directory.
    """
    jobs = []
    for task, property_file in witnesses:
        property_name = Path(property_file).stem
        witness = (Path(str(config.path_to_output_dir)) / "results" / task.file_name / "witness" / property_name
                   / "witness.yml")
        if witness.is_file():
            jobs.append((task, property_name, property_file, witness))

    rich.print(f"Validating {len(jobs)} violation witnesses with jlisa-wit")

    def validate(job):
        task, property_name, property_file, witness = job
        start = time.time()
        verdict, reason = validate_witness(config, str(task.input_file).split(), property_file, witness, timeout)
        (witness.parent / VALIDATION_FILE).write_text(f"{verdict}\n{reason}\n")
        return task.file_name, property_name, verdict, reason, round(time.time() - start, 1)

    with ThreadPoolExecutor(max_workers=parallelism) as executor:
        results = list(executor.map(validate, jobs))

    with open(os.path.join(str(config.path_to_output_dir), "witness-validation.csv"), "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["Test case", "Property", "Verdict", "Reason", "Seconds"])
        writer.writerows(results)

    validated = sum(verdict == WITNESS_CORRECT for _, _, verdict, _, _ in results)
    rich.print(f"Violation witnesses: {len(results)} validated, {validated} validated successfully")


def read_validation(witness_dir: str) -> str:
    """
    The verdict of jlisa-wit on the witness in the given folder (first line of validation.txt), or "" if the
    witness was not validated.
    """
    validation = os.path.join(witness_dir, VALIDATION_FILE)
    if not os.path.isfile(validation):
        return ""
    with open(validation, encoding="utf-8") as f:
        return f.readline().strip()

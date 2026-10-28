# Standard library imports
import csv
import json
import os
import subprocess
import tempfile
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

# Load vendored packages
from vendor.package_loader import load_packages

load_packages()

# Third-party imports
import rich
import typer

# Project-local imports
from cli.models.config import Config
from cli.models.property import SVCOMP_NAMES, Property
from cli.utils.jlisa_wit import run_jlisa_wit

# CLI setup
cli = typer.Typer()
config = Config.get()

# Exceptions caused by the environment where jlisa-wit runs the program, not by the program (e.g., AWT
# without a display): a run that ends with one of them is not a violation
ENVIRONMENT_EXCEPTIONS = {
    "java.awt.HeadlessException",
}

# The property of a row of svcomp.csv -> the name of its property file
PROPERTY_FILES = {
    "assert": "valid-assert.prp",
    "runtime": "no-runtime-exception.prp",
}


@cli.command()
def findbug(
        parallel: int = typer.Option(6, "-p", "--parallel", help="Number of runs of jlisa-wit at the same time"),
        time_limit: int = typer.Option(None, "-t", "--time-limit",
                                       help="Time limit of the search of each run, in seconds "
                                            "(default: find_bug_time_limit of the configuration)")
):
    """
        Applies the bug-finding fallback of the check command to the results of the analyse command: for
        each property where jlisa ended with UNKNOWN (not with a timeout, which already used the whole
        time), jlisa-wit looks for a run that violates it, and writes the violation witness of each violation
        found to find-bug/<task>/<property>/witness.yml. Writes find-bug.csv and svcomp-find-bug.csv (the
        results of svcomp.csv with the violations found) in the output directory, and prints the scores.
        Run it after the statistics command.
    """

    if not config.has_jlisa_wit():
        rich.print("[red]jlisa-wit not included in this build[/red]")
        raise typer.Exit(1)
    out = config.path_to_output_dir
    if not (out / "svcomp.csv").is_file():
        rich.print("[red]Missing svcomp.csv: run the statistics command first[/red]")
        raise typer.Exit(1)
    limit = time_limit or config.find_bug_time_limit
    # the working directories of jlisa-wit go to the output directory
    tempfile.tempdir = str(out / "find-bug-tmp")
    os.makedirs(tempfile.tempdir, exist_ok=True)

    tasks = {t["file_name"]: t for t in json.loads((out / "tasks.json").read_text())}
    rows = list(csv.DictReader(open(out / "svcomp.csv")))
    pending = [r for r in rows if r["Virdict"].startswith("UNKNOWN")]
    rich.print(f"[yellow]Bug finding on {len(pending)} of {len(rows)} results (UNKNOWN, no timeout)[/yellow]")

    def search(row):
        name, prop, _ = row["Test case"].split("|")
        task = tasks.get(name)
        if task is None:
            return row["Test case"], "skipped", "", 0.0
        property_file = os.path.join(os.path.dirname(task["path_to_definition"]), "..", "properties",
                                     PROPERTY_FILES[prop])
        if not os.path.isfile(property_file):
            return row["Test case"], "skipped", "", 0.0
        witness = out / "find-bug" / Path(name).stem / SVCOMP_NAMES[Property(prop)] / "witness.yml"
        witness.parent.mkdir(parents=True, exist_ok=True)
        witness.unlink(missing_ok=True)
        start = time.time()
        witness_note = ""
        try:
            output, errors = run_jlisa_wit(config, task["input_file"].split(), property_file,
                                           ["--find-bug", "--time-limit", str(limit),
                                            "--witness-output", str(witness.absolute())],
                                           timeout=float(limit) + 60, with_stderr=True)
            found = "Violation found" in [line.strip() for line in output.splitlines()]
            # the reason of the violation names the exception that ended the run, and says why there is
            # no witness
            reason = next((line for line in errors.splitlines() if "found/violation-found:" in line), "")
            if found and any(exception in reason for exception in ENVIRONMENT_EXCEPTIONS):
                result = "UNKNOWN (environment)"
            else:
                result = "FALSE" if found else "UNKNOWN"
            if result == "FALSE":
                witness_note = "yes" if witness.is_file() else reason.partition("; no witness: ")[2] or "no"
        except (subprocess.TimeoutExpired, OSError):
            result = "UNKNOWN"
        if result != "FALSE":
            witness.unlink(missing_ok=True)
        return row["Test case"], result, witness_note, round(time.time() - start, 1)

    with ThreadPoolExecutor(max_workers=parallel) as pool:
        results = {}
        for i, (case, result, witness_note, seconds) in enumerate(pool.map(search, pending), 1):
            results[case] = (result, witness_note, seconds)
            if result == "FALSE":
                rich.print(f"[red]{i}/{len(pending)} violation found:[/red] {case} ({seconds}s)")

    with open(out / "find-bug.csv", "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["Test case", "Verdict before", "Bug finding", "Witness", "Seconds"])
        for row in pending:
            result, witness_note, seconds = results[row["Test case"]]
            writer.writerow([row["Test case"], row["Virdict"], result, witness_note, seconds])

    before = sum(int(r["Score"]) for r in rows)
    found = wrong = with_witness = 0
    for row in rows:
        result, witness_note, _ = results.get(row["Test case"], (None, "", 0))
        if result == "FALSE":
            expected = row["Test case"].split("|")[2]
            row["Virdict"] = "FALSE (bug finding)"
            row["Score"] = "1" if expected == "False" else "-16"
            row["Witness"] = "yes" if witness_note == "yes" else ""
            found += 1
            wrong += expected != "False"
            with_witness += witness_note == "yes"
    with open(out / "svcomp-find-bug.csv", "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
    after = sum(int(r["Score"]) for r in rows)
    rich.print(f"Bug finding: {found} violations found, {wrong} wrong, {with_witness} with a witness")
    rich.print(f"Score: {before} -> {after}")
    # as the statistics command, with the witnesses of jlisa and those of the bug finding
    for name, label in (("runtime", "Runtime"), ("assert", "Assert")):
        of_property = [r for r in rows if f"|{name}|" in r["Test case"]]
        written = [r for r in of_property if r.get("Witness") == "yes"]
        correct_false = [r for r in of_property if r["Virdict"].startswith("FALSE") and r["Test case"].endswith("|False")]
        correct_with_witness = [r for r in correct_false if r.get("Witness") == "yes"]
        rich.print(f"{label} witnesses: {len(written)} written, {len(correct_with_witness)} of {len(correct_false)} "
                   "correct FALSE results with a witness")

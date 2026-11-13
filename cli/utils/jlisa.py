# Standard library imports
import os
import subprocess
import sys
from pathlib import Path

# Project-local imports
from cli.models.config import Config
from cli.utils.util import resource_path
from cli.models.property import SVCOMP_NAMES
from cli.models.task_definition.task_definition import TaskDefinition

JLISA_MAIN_CLASS = "it.unive.jlisa.Main"

# The verdict of jlisa-wit that confirms a violation witness, and the one when it cannot tell
WITNESS_CORRECT = "Witness Correct"
COULD_NOT_VALIDATE = "Could not validate"
# Prefix for extracting the witness verdict from the output of jlisa validate.
VERDICT_PREFIX = "[VERDICT] "

# The time of the search of the bug-finding fallback, in seconds, when not given
BUG_FINDING_TIME_LIMIT = 120


# The folder with the z3 executable that build_jlisa.sh downloads and ships next to the jlisa executable
Z3_DIR = "z3"


def bundled_z3() -> str | None:
    """
    The path to the z3 executable shipped with the archive (z3/z3, next to the jlisa executable, or in the
    project folder when running from the sources), or None if there is none.
    """
    base = Path(sys.executable).parent if getattr(sys, "frozen", False) else resource_path(".")
    z3 = base / Z3_DIR / "z3"
    return str(z3.absolute()) if z3.is_file() else None


def property_files(task: TaskDefinition) -> list[str]:
    """
    The property files of the task that jlisa checks and writes violation witnesses for (valid-assert and
    no-runtime-exception), as absolute paths.
    """
    names = {f"{name}.prp" for name in SVCOMP_NAMES.values()}
    return [
        str((Path(task.path_to_definition).parent / prop.property_file).resolve())
        for prop in task.properties
        if Path(prop.property_file).name in names
    ]



def run_name(task: TaskDefinition, property_file: str) -> str:
    """
    The name of the run checking the given property of the task, that is, the folder of its results in the
    results of a run of analyse: <task>/<property> (e.g. "Main/valid-assert"), as each property of a task is
    checked by a run of its own.
    """
    return f"{task.file_name}/{Path(property_file).stem}"


def get_lisa_cmd(
    config: Config, input_files: list[str], file_name: str, max_memory: int, debug: bool = False,
    property_files: list[str] | None = None, dump_graphs: bool = False, z3: str | None = None,
    verifier: str = "Reachability", time_limit: int | None = None, log_level: str = "ERROR",
    certification: bool = False
) -> list[str]:
    """
    Get the command to run LiSA from the configuration file, as a list of arguments. With debug, jlisa
    also writes the debug information (open calls, bottom states) and the exceptions that the statistics use.
    With dump_graphs, jlisa also writes the JSON graphs of the analyzed methods.
    With z3, jlisa uses that z3 executable to verify its warnings (otherwise, the one in the PATH, if any).
    The verifier is the one jlisa uses to verify its warnings: Reachability (through the results of the
    analysis) or Combined (the SV-COMP verifier, falling back to model checking with z3).
    With time_limit (in seconds), jlisa ends the verification of its warnings in time to write its results
    within that time (warnings not verified by then stay possible).
    The log level is the one of the logs that jlisa prints (e.g. ERROR or INFO).
    With certification, jlisa certifies the counterexamples that its verification cannot confirm by validating
    their violation witnesses (running the program with their values), confirming the warnings whose witnesses
    are correct.
    For each property file, jlisa also writes the violation witness of a definite violation of that property,
    to witness/<property>/witness.yml in the output directory.

    The command is:
        java -Xmx<max_memory>G -cp <path_to_lisa_instance> it.unive.jlisa.Main check
            -s <input-1> <...> <input-N> -o <output-dir>
            -n <numerical_domain> -m Statistics -c Assert -t <verifier> -l <log_level> [-d -e] [--dump-graphs]
            [--z3 <z3>] [--time-limit <time_limit>] [--certification]
            [--svcomp-property <property-file-1> <...> --svcomp-property <property-file-N>]
    """
    out = (
        str(config.path_to_output_dir)
        if not file_name
        else f"{str(config.path_to_output_dir)}/{file_name}"
    )
    # the classpath is saved with the quotes of a shell command line, and no shell runs the command
    classpath = str(config.path_to_lisa_instance).replace('"', '')
    return [
        "java",
        f"-Xmx{max_memory}G",
        "-cp", classpath,
        JLISA_MAIN_CLASS, "check",
        "-s", *input_files,
        "-o", out,
        "-n", config.numerical_domain,
        "-m", "Statistics",
        "-c", "Assert",
        "-t", verifier,
        "-l", log_level,
    ] + (["-d", "-e"] if debug else []) + (["--dump-graphs"] if dump_graphs else []) + (
        ["--z3", z3] if z3 else []
    ) + (["--time-limit", str(time_limit)] if time_limit else []) + (
        ["--certification"] if certification else []
    ) + [
        arg for property_file in (property_files or []) for arg in ("--svcomp-property", property_file)
    ]


def run_jlisa_wit(config: Config, sub_command: str, inputs: list[str], property_file: str, args: list[str],
                  timeout: float | None = None) -> str:
    """
    Runs jlisa-wit (the sub-command validate or find-bug of jlisa) on a task as SV-COMP gives it to the tool
    (its inputs and its property file), returning its stdout: its verdict (see jlisa_verdict), the reason for
    it (see jlisa_reason) and its logs, at level ERROR. The paths are passed as they were given, since
    jlisa-wit writes them in its witnesses; jlisa-wit runs the programs in a temporary directory of its own.
    """

    java = os.path.join(os.environ["JAVA_HOME"], "bin", "java") if "JAVA_HOME" in os.environ else "java"
    classpath = os.path.abspath(str(config.path_to_lisa_instance).replace('"', ''))
    command = [java, "--add-modules", "jdk.jdi", "-cp", classpath, JLISA_MAIN_CLASS, sub_command,
               "-l", "ERROR", *args,
               "--svcomp-property", property_file,
               # last, since it takes all the following arguments
               "--source", *inputs]

    return subprocess.run(command, stdout=subprocess.PIPE, text=True, timeout=timeout).stdout


def jlisa_verdict(output: str) -> str | None:
    """
    The verdict in the given output of jlisa-wit (e.g. "Witness Correct"): its last line that starts with
    VERDICT_PREFIX, without the prefix, or None if there is none.
    """
    prefix = VERDICT_PREFIX.strip()
    verdicts = [line.strip()[len(prefix):].strip() for line in output.splitlines()
                if line.strip().startswith(prefix)]
    return verdicts[-1] if verdicts else None


def jlisa_reason(output: str) -> str:
    """
    The reason jlisa-wit gives for its verdict in the given output: its last [REASON] line, or "".
    """
    reasons = [line.split("[REASON]", 1)[1].strip() for line in output.splitlines() if "[REASON]" in line]
    return reasons[-1] if reasons else ""


def validate_witness(config: Config, inputs: list[str], property_file: str, witness: Path,
                     timeout: float | None = None) -> tuple[str, str]:
    """
    Validates a violation witness with jlisa-wit, returning its verdict (e.g. "Witness Correct") and the
    reason it gives for it (or "").
    """
    try:
        output = run_jlisa_wit(config, "validate", inputs, property_file,
                               ["--witness", str(witness.absolute())], timeout=timeout)
    except subprocess.TimeoutExpired:
        return COULD_NOT_VALIDATE, f"timeout after {timeout} s"
    except OSError as e:
        return COULD_NOT_VALIDATE, f"jlisa-wit cannot run: {e}"
    return jlisa_verdict(output) or COULD_NOT_VALIDATE, jlisa_reason(output)


def find_bug(config: Config, inputs: list[str], property_file: str, time_limit: int,
             witness: Path) -> tuple[str, str]:
    """
    Looks for a violation of the property with the bug-finding mode of jlisa-wit, which runs the program and
    only reports a violation that a run really reaches, and writes its violation witness to the given file.
    Returns the verdict and the reason jlisa-wit gives for it: FALSE if a run violates the property, otherwise
    UNKNOWN. It never returns TRUE. The witness is only kept with FALSE. jlisa-wit needs the property file and
    input directories, as SV-COMP gives them.
    """
    witness.unlink(missing_ok=True)
    if not Path(property_file).is_file() or not all(Path(p).is_dir() for p in inputs):
        return "UNKNOWN", "bug finding needs the property file and input directories"
    witness.parent.mkdir(parents=True, exist_ok=True)
    try:
        output = run_jlisa_wit(config, "find-bug", inputs, property_file,
                               ["--time-limit", str(time_limit), "--witness-output", str(witness.absolute())],
                               timeout=float(time_limit) + 60)
    except (subprocess.TimeoutExpired, OSError) as e:
        return "UNKNOWN", f"bug finding failed: {e}"
    reason = jlisa_reason(output)
    verdict = "FALSE" if jlisa_verdict(output) == "Violation found" else "UNKNOWN"
    if verdict != "FALSE":
        witness.unlink(missing_ok=True)
    return verdict, reason

# Standard library imports
import os
import subprocess
from pathlib import Path

# Project-local imports
from cli.models.config import Config
from cli.models.property import SVCOMP_NAMES
from cli.models.task_definition.task_definition import TaskDefinition

# The main classes of the jlisa package: jlisa, and its witness validator jlisa-wit
JLISA_MAIN_CLASS = "it.unive.jlisa.Main"
JLISA_WIT_MAIN_CLASS = "it.unive.jlisa.witness.validator.Main"

# The verdict of jlisa-wit that confirms a violation witness, and the one when it cannot tell
WITNESS_CORRECT = "Witness Correct"
COULD_NOT_VALIDATE = "Could not validate"

# The time of the search of the bug-finding fallback, in seconds, when not given
BUG_FINDING_TIME_LIMIT = 120
# Exceptions caused by the environment where jlisa-wit runs the program, not by the program (e.g., AWT
# without a display): a run that ends with one of them is not a violation
ENVIRONMENT_EXCEPTIONS = {
    "java.awt.HeadlessException",
}


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



def get_lisa_cmd(
    config: Config, input_files: list[str], file_name: str, max_memory: int, debug: bool = False,
    property_files: list[str] | None = None
) -> list[str]:
    """
    Get the command to run LiSA from the configuration file, as a list of arguments. With debug, jlisa
    also writes the debug information (open calls, bottom states) and the exceptions that the statistics use.
    For each property file, jlisa also writes the violation witness of a definite violation of that property,
    to witness/<property>/witness.yml in the output directory.

    The command is:
        java -Xmx<max_memory>G -cp <path_to_lisa_instance> it.unive.jlisa.Main
            -s <input-1> <...> <input-N> -o <output-dir>
            -n <numerical_domain> -m Statistics -c Assert --no-html --l ERROR [-d -e] [--no-graphs]
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
        JLISA_MAIN_CLASS,
        "-s", *input_files,
        "-o", out,
        "-n", config.numerical_domain,
        "-m", "Statistics",
        "-c", "Assert",
        "--no-html",
        "--l", "ERROR",
    ] + (["-d", "-e"] if debug else []) + ([] if config.jlisa_graphs else ["--no-graphs"]) + [
        arg for property_file in (property_files or []) for arg in ("--svcomp-property", property_file)
    ]


def run_jlisa_wit(config: Config, inputs: list[str], property_file: str, args: list[str],
                  timeout: float | None = None, with_stderr: bool = False) -> str | tuple[str, str]:
    """
    Runs jlisa-wit on a task as SV-COMP gives it to the tool (its inputs and its property file), returning
    its stdout, or its stdout and its stderr (where it explains its verdict) with with_stderr. The paths are
    passed as they were given, since jlisa-wit writes them in its witnesses; jlisa-wit runs the programs in
    a temporary directory of its own.
    """

    java = os.path.join(os.environ["JAVA_HOME"], "bin", "java") if "JAVA_HOME" in os.environ else "java"
    classpath = os.path.abspath(str(config.path_to_lisa_instance).replace('"', ''))
    command = [java, "--add-modules", "jdk.jdi", "-cp", classpath, JLISA_WIT_MAIN_CLASS, *args,
               "--svcomp-property", property_file,
               # last, since it takes all the following arguments
               "--source", *inputs]

    process = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE if with_stderr else None,
                             text=True, timeout=timeout)
    return (process.stdout, process.stderr) if with_stderr else process.stdout


def validate_witness(config: Config, inputs: list[str], property_file: str, witness: Path,
                     timeout: float | None = None) -> tuple[str, str]:
    """
    Validates a violation witness with jlisa-wit, returning its verdict (the last line it prints, e.g.
    "Witness Correct") and the reason it gives for it (its last [REASON] line, or "").
    """
    try:
        output, errors = run_jlisa_wit(config, inputs, property_file, ["--witness", str(witness.absolute())],
                                       timeout=timeout, with_stderr=True)
    except subprocess.TimeoutExpired:
        return COULD_NOT_VALIDATE, f"timeout after {timeout} s"
    except OSError as e:
        return COULD_NOT_VALIDATE, f"jlisa-wit cannot run: {e}"
    verdicts = [line.strip() for line in output.splitlines() if line.strip()]
    reasons = [line.split("[REASON]", 1)[1].strip() for line in errors.splitlines() if "[REASON]" in line]
    return verdicts[-1] if verdicts else COULD_NOT_VALIDATE, reasons[-1] if reasons else ""


def find_bug(config: Config, inputs: list[str], property_file: str, time_limit: int,
             witness: Path) -> tuple[str, str]:
    """
    Looks for a violation of the property with the bug-finding mode of jlisa-wit, which runs the program and
    only reports a violation that a run really reaches, and writes its violation witness to the given file.
    Returns the verdict and the reason jlisa-wit gives for it: FALSE if a run violates the property, otherwise
    UNKNOWN ("UNKNOWN (environment)" when the run ends with one of the ENVIRONMENT_EXCEPTIONS). It never
    returns TRUE. The witness is only kept with FALSE. jlisa-wit needs the property file and input
    directories, as SV-COMP gives them.
    """
    witness.unlink(missing_ok=True)
    if not Path(property_file).is_file() or not all(Path(p).is_dir() for p in inputs):
        return "UNKNOWN", "bug finding needs the property file and input directories"
    witness.parent.mkdir(parents=True, exist_ok=True)
    try:
        output, errors = run_jlisa_wit(config, inputs, property_file,
                                       ["--find-bug", "--time-limit", str(time_limit),
                                        "--witness-output", str(witness.absolute())],
                                       timeout=float(time_limit) + 60, with_stderr=True)
    except (subprocess.TimeoutExpired, OSError) as e:
        return "UNKNOWN", f"bug finding failed: {e}"
    found = "Violation found" in [line.strip() for line in output.splitlines()]
    reasons = [line.split("[REASON]", 1)[1].strip() for line in errors.splitlines() if "[REASON]" in line]
    reason = reasons[-1] if reasons else ""
    if found and any(exception in reason for exception in ENVIRONMENT_EXCEPTIONS):
        verdict = "UNKNOWN (environment)"
    else:
        verdict = "FALSE" if found else "UNKNOWN"
    if verdict != "FALSE":
        witness.unlink(missing_ok=True)
    return verdict, reason

# Standard library imports
import os
import subprocess

# Project-local imports
from cli.models.config import Config

MAIN_CLASS = "it.unive.jlisa.witness.validator.Main"


def run_jlisa_wit(config: Config, inputs: list[str], property_file: str, args: list[str],
                  timeout: float | None = None, with_stderr: bool = False) -> str | tuple[str, str]:
    """
    Runs jlisa-wit on a task as SV-COMP gives it to the tool (its inputs and its property file), returning
    its stdout, or its stdout and its stderr (where it explains its verdict) with with_stderr. The paths are
    passed as they were given, since jlisa-wit writes them in its witnesses; jlisa-wit runs the programs in
    a temporary directory of its own.
    """

    java = os.path.join(os.environ["JAVA_HOME"], "bin", "java") if "JAVA_HOME" in os.environ else "java"
    classpath = os.path.abspath(str(config.path_to_jlisa_wit_instance).replace('"', ''))
    command = [java, "--add-modules", "jdk.jdi", "-cp", classpath, MAIN_CLASS, *args,
               "--svcomp-property", property_file,
               # last, since it takes all the following arguments
               "--source", *inputs]

    process = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE if with_stderr else None,
                             text=True, timeout=timeout)
    return (process.stdout, process.stderr) if with_stderr else process.stdout

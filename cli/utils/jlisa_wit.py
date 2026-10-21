# Standard library imports
import os
import re
import shutil
import subprocess
import tempfile
from pathlib import Path

# Project-local imports
from cli.models.config import Config

MAIN_CLASS = "it.unive.jlisa.witness.validator.Main"

# LTL formula (whitespace removed) -> property name understood by the validator
PROPERTIES = {
    "Gassert": "assert",
    "G!uncaught(java.lang.RuntimeException)": "runtime",
}


def parse_property(path: str) -> str | None:
    """
    The validator's name of the property in a .prp file, or None if it is not supported
    """

    content = re.sub(r"\s+", "", Path(path).read_text())
    match = re.match(r"^CHECK\(init\((\S+)\(\)\),LTL\((\S+)\)\)$", content)
    return PROPERTIES.get(match.group(2)) if match else None


def benchmark_inputs(paths: list[str]) -> tuple[list[str], str]:
    """
    The inputs to copy, and the benchmark among them (the input with Main.java).

    An input inside another input is left out: it is compiled with its parent, and a
    second copy would define its classes twice.
    """

    paths = [os.path.normpath(p) for p in paths]
    real = [os.path.realpath(p) for p in paths]
    inputs = [p for p, rp in zip(paths, real)
              if not any(rp != other and rp.startswith(other + os.sep) for other in real)]
    benchmark = next((p for p in inputs if os.path.isfile(os.path.join(p, "Main.java"))), inputs[-1])
    return inputs, benchmark


def run_jlisa_wit(config: Config, paths: list[str], property_name: str, args: list[str],
                  timeout: float | None = None) -> str:
    """
    Runs the jlisa-wit validator on a benchmark (its input directories), returning its stdout
    """

    java = os.path.join(os.environ["JAVA_HOME"], "bin", "java") if "JAVA_HOME" in os.environ else "java"
    classpath = str(config.path_to_jlisa_wit_instance).replace('"', '')
    inputs, benchmark = benchmark_inputs(paths)

    with tempfile.TemporaryDirectory(prefix="jlisa-wit-") as workdir:
        copies = []
        for i, path in enumerate(inputs):
            dest = os.path.join(workdir, str(i), os.path.basename(path))
            shutil.copytree(path, dest)
            copies.append(os.path.relpath(dest, workdir))
        # the validator finds the benchmark directory by the name of the task file
        task_file = os.path.join(workdir, os.path.basename(benchmark) + ".yml")
        with open(task_file, "w") as f:
            f.write("input_files:\n" + "".join("  - '%s/'\n" % c for c in copies))

        command = [java, "--add-modules", "jdk.jdi", "-cp", classpath, MAIN_CLASS,
                   "--benchmark", task_file, "--property", property_name, *args]
        return subprocess.run(command, stdout=subprocess.PIPE, text=True, timeout=timeout).stdout

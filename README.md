### SV-COMP Helper CLI for LiSA

This repository contains a command-line interface (CLI) app, written in Python v3.13 and crafted to aid LiSA and its frontends in competing in [SV-COMP](https://sv-comp.sosy-lab.org) — hence the name (abbreviated simply as `SVH`). To avoid cluttering the core implementation of LiSA with components meant solely for working with SV-COMP benchmarks, all such concerns are handled within this app.

## Table of Contents

- [Overview](#overview)
- [Quick Analysis Example](#quick-analysis-example)
- [Comparing Results](#comparing-results)
- [Installation and Setup](#installation-and-setup)
- [Development](#development)
- [Docker](#docker)
- [Build SV-COMP Executable](#build-sv-comp-executable)
- [Running the Executable](#running-the-executable)

#### Overview

The CLI app is built on the [Typer library](https://typer.tiangolo.com), described as the "FastAPI of the CLI world." It is a core dependency that provides a structured framework and enables the app to `speak for itself`.

```terminaloutput
> cd ./sv-comp
> python main.py

Usage: main.py [OPTIONS] COMMAND [ARGS]...

 This CLI tool is intended to help you work with SV-COMP benchmark suites.

╭─ Options ────────────────────────────────────────────────────────────────────────────────────────────────────────────╮
│ --version  -v        Show the CLI version and exit                                                                   │
│ --help               Show this message and exit.                                                                     │
╰──────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╯
╭─ Commands ───────────────────────────────────────────────────────────────────────────────────────────────────────────╮
│ setup        A prompt.                                                                                               │
│              Points and records (to the local config file) to essential directories for the tool                     │
│              (e.g., location of LiSA instance, SV COMP benchmark source files, where to output results)              │
│ harvest      Harvests task definitions (.yml files) and saves them in tasks.json                                     │
│ analyse      Sends collected tasks to the LiSA instance for analysis                                                 │
│ check        Check input files against a specified property                                                          │
│ validate     Validate a violation witness against the input files and a specified property                           │
│ components   Lists the tools included in this build: jlisa (check) and/or jlisa-wit (validate)            │
│ statistics   Computes statistics on analysis results                                                                 │
│ compare      Compares two SV-COMP results tables (produced by command 'statistics') to find differences              │
│ version      Shows a version of the LiSA's instance in use                                                           │
╰──────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╯

 Developed and maintained by the Software and System Verification (SSV) group
 @ Università Ca' Foscari Venezia, Italy
```

### Quick Analysis Example

There are two ways to carry out the analysis. First, the iterative (start by `python main.py`) and `SVH` will guide you through the process. Otherwise, one-enter-launch is also supported:

```terminaloutput
> python main.py analyse --help

 Usage: main.py analyse [OPTIONS]

 Sends collected tasks to the LiSA instance for analysis
 
╭─ Options ────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╮
│ --benchdir  -b      PATH  Path to the SV-COMP benchmark directory                                                                    │
│ --lisadir   -l      PATH  Path to the LiSA instance                                                                                  │
│ --outdir    -o      PATH  Path to the output directory                                                                               │
╰──────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╯
 
 > python main.py analyse -b [...] --lisadir [...] --outdir [...]
```

### Comparing Results

The CLI tool comes along with the `compare` command. It allows to diff two results tables produced by `statistics` command.
More precisely it uses `svcomp.csv` file that `statistics` command produce among others. 

For the example let's consider that there are two output folders of two separate analysis results, each containing its own `svcomp.csv`:

```terminaloutput
 ../svh/output-old/svcomp.csv
 ../svh/output-new/svcomp.csv
```

The user have a choice to just print out in the console the diff:
```shell
  python main.py compare -f ../svh/output-old/svcomp.csv -s ../svh/output-new/svcomp.csv
```

Or, additionally, by providing the `-o` argument, it is possible to save the comparison to a specified file, e.g:

```shell
  python main.py compare -f ../svh/output-old/svcomp.csv -s ../svh/output-new/svcomp.csv -o ../svh/output/comparison.csv
```

```terminaloutput
> python main.py compare --help

 Usage: main.py compare [OPTIONS]

 Compares two SV-COMP results tables (produced by command 'statistics') to find differences

╭─ Options ────────────────────────────────────────────────────────────────────╮
│ --first   -f      TEXT  Path to the first SV-COMP results table (produced by │
│                         command 'statistics')                                │
│ --second  -s      TEXT  Path to the second SV-COMP results table (produced   │
│                         by command 'statistics')                             │
│ --output  -o      TEXT  Path to the output file for the comparison results.  │
│                         If provided, the comparison is saved there;          │
│                         otherwise it is only printed to the console.         │
╰────────────────────────────────────────────────────────────────────────────╯
```

#### Installation and Setup

`SVH` aims to be self-sufficient, with the only system requirement being that `Python` is installed and available via the conventional `python` command. All dependencies are stored in its subfolder `/vendor`. On a new system (e.g., after an initial `git clone`), it is necessary to *vendor the packages* based on the `requirements.txt` and `pyproject.toml` specifications. 

For this reason, the only prerequisite is to execute the script as shown below: 

```bash
> cd ./sv-comp
> python ./vendor/vendorize.py

Installing packages to: .../sv-comp/vendor/lib/python3.13/site-packages
...
Vendoring complete.
```
Under `/vendor`, it populates `/lib/python3.13/site-packages`, where all the dependencies will be stored. Once vendoring is complete, you may proceed with `python main.py` and execute commands such as `setup` and `harvest`.

#### Development

If you plan to develop or extend the CLI's capabilities, please note how to import vendored packages into your newly created files.

```python
# Load vendored packages
from vendor.package_loader import load_packages
load_packages()

# Afterward, you may add third-party imports. E.g.:
import typer
```

#### Docker
The CLI tool comes equipped with a Docker image to run the process end-to-end.
The docker image expects:

- a zip file containing the jar files obtained by the compilation of JLiSA. These can be obtained by running `gradle distZip` on the JLiSA project, and then the zip file will be in the directory `build/distributions`. Note that JLiSA must be compile with Java 21 or below.
- a zip file containing the root of the SV-COMP Benchmarks. This can be downloaded from [here](https://gitlab.com/sosy-lab/benchmarking/sv-benchmarks/-/archive/main/sv-benchmarks-main.zip). Unfortunately, this archive is **huge**, so it is better to remove all the benchmarks that are not in the `java` subfolder.

The Docker image can be run as follows
```bash
> docker volume create analysis_results
> docker build -t jlisa/svcomp .
> docker run --mount type=volume,src=analysis_results,dst=/app/output jlisa/svcomp
```

#### Build SV-COMP Executable
##### Requirements
- Java 21 or higher – Make sure the JAVA_HOME environment variable is set.
- Python 3.12 or higher
- zip and unzip utilities installed
##### Building
To build the SV-COMP executable, a shell script is provided. The archive can include JLiSA (the verifier, run by `jlisa check`), JLiSA-Wit (the violation witness validator, run by `jlisa validate`), or both.
1. Clone the repositories of the tools to include, and check out the version to build:
```bash
> git clone https://github.com/lisa-analyzer/jlisa
> git clone https://github.com/lisa-analyzer/jlisa-witness-validator
```
2. Create a GitHub Personal Access Token (PAT) by following [this guide](https://docs.github.com/en/enterprise-cloud@latest/authentication/keeping-your-account-and-data-secure/creating-a-personal-access-token) and grant it the read:packages permission.
3. Inside each project folder, create a file named gradle.properties with the following content:
```bash
gpr.user=your-github-username
gpr.key=github-access-token
```
4. Run the build_jlisa.sh script, giving the JLiSA project folder with `--jlisa-dir`, the JLiSA-Wit project folder with `--jlisa-wit-dir`, or both. At least one of the two is required, and the archive includes only the tools that are given. For example:
```bash
> ./build_jlisa.sh --jlisa-dir ../jlisa/jlisa --jlisa-wit-dir ../jlisa-witness-validator
```
When both are given, JLiSA-Wit is built on the same JLiSA. When only `--jlisa-wit-dir` is given, JLiSA-Wit is built on the JLiSA checkout `../jlisa/jlisa` next to it, or on the one in the JLISA_HOME environment variable.

This script will generate a jlisa.zip file. The zip contains the executable along with the license, README, and smoketest script. The script runs the smoketest on the unzipped archive at the end of the build.
To run the smoketest on the sources instead, without building:
```bash
> JLISA="python3 main.py" bash dist-template/smoketest.sh
```

#### Running the Executable
Unzip the jlisa.zip file. `./jlisa components` lists the tools included in the archive.

To verify a program:
```bash
> ./jlisa check --inputs "<input-1> <...> <input-N>" --property "<property-file.prp>"
```
The last line of the output is the verdict: TRUE (the property holds), FALSE (the property is violated) or UNKNOWN. The results of the analysis, and the violation witness, are written to the folder `outputs/` in the working directory (the witness is `outputs/witness/witness.graphml`).

To validate a violation witness:
```bash
> ./jlisa validate --witness "<witness-file>" --inputs "<input-dir-1> <...> <input-dir-N>" --property "<property-file.prp>"
```
As for SV-COMP validators, the verdict is about the property, and the last line of the output is one of:
- FALSE: the violation of the witness is reproduced, and the witness is confirmed (the line before it is `Witness Correct`)
- TRUE: the program runs with the values of the witness without the violation, and the witness is rejected as spurious (`Witness Spurious`)
- UNKNOWN: the witness could not be validated (`Could not validate`)
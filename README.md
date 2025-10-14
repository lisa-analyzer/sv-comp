### SV-COMP Helper CLI for LiSA

This repository contains a command-line interface (CLI) app, written in Python v3.13 and crafted to aid LiSA and its frontends in competing in [SV-COMP](https://sv-comp.sosy-lab.org) — hence the name (abbreviated simply as `SVH`). To avoid cluttering the core implementation of LiSA with components meant solely for working with SV-COMP benchmarks, all such concerns are handled within this app.

## Table of Contents

- [Overview](#overview)
- [Quick Analysis Example](#quick-analysis-example)
- [Installation and Setup](#installation-and-setup)
- [Development](#development)
- [Docker](#docker)

#### Overview

The CLI app is built on the [Typer library](https://typer.tiangolo.com), described as the "FastAPI of the CLI world." It is a core dependency that provides a structured framework and enables the app to `speak for itself`.

```terminaloutput
> cd ./sv-comp
> python main.py

Usage: main.py [OPTIONS] COMMAND [ARGS]...

 This CLI tool is intended to help you work with SV-COMP benchmark suites.

╭─ Options ──────────────────────────────────────────────────────────────────╮
│ --help          Show this message and exit.                                │
╰────────────────────────────────────────────────────────────────────────────╯
╭─ Commands ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╮
│ setup        A prompt.                                                                                                                                                                         │
│              Points and records (to the local config file) to essential directories for the tool                                                                                               │
│              (e.g., location of LiSA instance, SV COMP benchmark source files, where to output results)                                                                                        │
│ harvest      Harvests task definitions (.yml files) and saves them in tasks.json                                                                                                               │
│ analyse      Sends collected tasks to the LiSA instance for analysis                                                                                                                           │
│ check        Check input files against a specified property                                                                                                                                    │
│ statistics   Computes statistics on analysis results                                                                                                                                           │
│ version      Shows a version of the LiSA's instance in use                                                                                                                                     │
╰────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╯

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

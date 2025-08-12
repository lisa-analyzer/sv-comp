# Standard library imports
import sys
import json
import subprocess
from pathlib import Path
from typing import Annotated
from typing_extensions import Optional

# Load vendored packages
from vendor.package_loader import load_packages
load_packages()

# Third-party imports
import rich
import typer

# Project-local imports
from cli.models.config import Config
from cli.commands.harvest import fetch_tasks
from cli.models.task_definition.task_definition import TaskDefinition

# CLI setup
cli = typer.Typer()
config = Config.get()


@cli.command()
def analyse(
        benchdir: Annotated[Optional[Path], typer.Option(
            "--benchdir", "-b",
            help="Path to the SV-COMP benchmark directory"
        )] = None,
        lisadir: Annotated[Optional[Path], typer.Option(
            "--lisadir", "-l",
            help="Path to the LiSA instance",

        )] = None,
        outdir: Annotated[Optional[Path], typer.Option(
            "--outdir", "-o",
            help="Path to the output directory"
        )] = None
):
    """
        Sends collected tasks to the LiSA instance for analysis
    """
    some_args_provided = any([benchdir, lisadir, outdir])
    all_args_provided = all([benchdir, lisadir, outdir])

    tasks = []
    if some_args_provided and not all_args_provided:
        raise typer.BadParameter(
            "If any of --benchdir, --lisadir, or --outdir is used, all three must be provided."
        )

    if all_args_provided:
        config.path_to_sv_comp_benchmark_dir = benchdir
        config.path_to_lisa_instance = lisadir
        config.path_to_output_dir = outdir
        tasks = fetch_tasks(benchdir)
    else:
        tasks_file = config.path_to_output_dir / "tasks.json"
        with tasks_file.open(encoding="utf-8") as f:
            raw_tasks = json.load(f)
        tasks: list[TaskDefinition] = [TaskDefinition(**t) for t in raw_tasks]

    __perform_analysis(tasks)


def __perform_analysis(tasks: list[TaskDefinition]):
    for task in tasks:
        command = (f"java "
                   f" -cp {config.path_to_lisa_instance}"
                   f" it.unive.jlisa.Main "
                   f" -s {task.input_file}"
                   f" -o {str(config.path_to_output_dir)}/results/{str(task.file_name)}"
                   f" -n ConstantPropagation" #TODO This will become dynamic/a parameter at some point
                   )
        expected_result = None
        for property in task.properties:
            if property["property_file"].endswith("assert_java.prp"):
                command = f"{command} -c Assert"
                expected_result = property["expected_verdict"]
        rich.print(f"Running command: [bold blue]{command}[/bold blue]")
        try:
            subprocess.run(command, shell=True, check=True)
            rich.print("[green]Command executed.[/green]")
            if expected_result!=None:
                report_file = f"{str(config.path_to_output_dir)}/results/{str(task.file_name)}/report.json"
                with open(report_file, encoding="utf-8") as f:
                    report = json.load(f)
                n_warns = int(report["info"]["warnings"])
                #TODO: This is quite approximative, we should distinguish true/false positives/negatives and iterate the analysis
                report["result"] = (n_warns>0)==expected_result
                with open(report_file, mode="w", encoding="utf-8") as f:
                    json.dump(report, f)

        except Exception as e:
            print(f"An unexpected error occurred: {e}", file=sys.stderr)

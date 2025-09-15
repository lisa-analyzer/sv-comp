# Standard library imports
import subprocess
import sys
from pathlib import Path

# Load vendored packages
from vendor.package_loader import load_packages
load_packages()

# Third-party imports
import rich
import typer
from typing import Annotated
from typing_extensions import Optional

# Project-local imports
from cli.models.config import Config
from cli.commands.harvest import fetch_tasks, get_tasks
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

    if some_args_provided and not all_args_provided:
        raise typer.BadParameter(
            "If any of --benchdir, --lisadir, or --outdir is used, all three must be provided."
        )

    tasks: list[TaskDefinition]
    if all_args_provided:
        config.path_to_sv_comp_benchmark_dir = benchdir
        config.path_to_lisa_instance = lisadir
        config.path_to_output_dir = outdir
        tasks = fetch_tasks(benchdir)
    else:
        tasks = get_tasks()

    __perform_analysis(tasks)


def __perform_analysis(tasks: list[TaskDefinition]):
    for task in tasks:
        command = (f"java"
                   f" -cp {config.path_to_lisa_instance}"
                   f" it.unive.jlisa.Main"
                   f" -s {task.input_file}"
                   f" -o {str(config.path_to_output_dir)}/results/{str(task.file_name)}"
                   f" -n ConstantPropagation" #TODO This will become dynamic/a parameter at some point
                   f" -m Statistics "
                   f" -c Assert" #TODO
                   )

        rich.print(f"Running command: [bold blue]{command}[/bold blue]")
        try:
            subprocess.run(command, shell=True, check=True)
            rich.print("[green]Command executed.[/green]")

        except Exception as e:
            print(f"An unexpected error occurred: {e}", file=sys.stderr)

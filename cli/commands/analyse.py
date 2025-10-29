# Standard library imports
import subprocess
import sys
from pathlib import Path
import time
import shutil
import os
import signal
from concurrent.futures import ThreadPoolExecutor
from threading import Lock

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

class WorkerTask:
    def __init__(self, task: TaskDefinition, start_time: float, timeout: int, max_memory: int, timed_out: list[str], total_tasks: int, task_idx: int, lock: Lock):
        self.task = task
        self.start_time = start_time
        self.timeout = timeout
        self.max_memory = max_memory
        self.timed_out = timed_out
        self.total_tasks = total_tasks
        self.task_idx = task_idx
        self.lock = lock

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
        )] = None,
        timeout: Annotated[Optional[int], typer.Option(
            "--timeout", "-t",
            help="Timeout for each analysis in seconds"
        )] = 300, # 5 minutes
        max_memory: Annotated[Optional[int], typer.Option(
            "--max-memory", "-m",
            help="Maximum memory for each analysis in GB"
        )] = 10, # 10 GB
        parallelism: Annotated[Optional[int], typer.Option(
            "--parallelism", "-p",
            help="Number of parallel analyses to run"
        )] = 1,
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

    workdir = f"{str(config.path_to_output_dir)}/results"
    if os.path.exists(workdir):
        shutil.rmtree(workdir, ignore_errors=True)
    
    start_time = time.time()
    timed_out = []
    total_tasks = len(tasks)
    lock = Lock()
    
    with ThreadPoolExecutor(max_workers=parallelism) as executor:
        i = 1
        for task in tasks:
            tsk = WorkerTask(task, start_time, timeout, max_memory, timed_out, total_tasks, i, lock)
            i += 1
            executor.submit(__perform_analysis, tsk)
    
    if timed_out:
        rich.print("[red]The following tasks timed out:[/red]")
        with open(f"{str(config.path_to_output_dir)}/timed_out.txt", 'w') as f:
            for t in timed_out:
                rich.print(f"[red]- {t}[/red]")
                f.write(f"{t}\n")

def __perform_analysis(task: WorkerTask):
    command = (f"java"
                f" -Xmx{task.max_memory}G"
                f" -cp {config.path_to_lisa_instance}"
                f" it.unive.jlisa.Main"
                f" -s {task.task.input_file}"
                f" -o {str(config.path_to_output_dir)}/results/{str(task.task.file_name)}"
                f" -n ConstantPropagation"
                f" -m Statistics "
                f" -c Assert"
                f" --no-html"
                f" --l ERROR"
            )

    rich.print(f"Running command {task.task_idx}/{task.total_tasks}: [bold blue]{command}[/bold blue]")
    proc = subprocess.Popen(command, shell=True, preexec_fn=os.setsid)
    try:
        proc.wait(timeout=task.timeout)
        if proc.returncode != 0:
            raise subprocess.CalledProcessError(proc.returncode, command)
        elapsed = time.time() - task.start_time
        elapsed_hms = time.strftime('%H:%M:%S', time.gmtime(elapsed))
        rich.print(f"[green]Command {task.task_idx} successful. Elapsed time: {elapsed_hms}[/green]")
    except subprocess.TimeoutExpired:
        rich.print(f"[yellow]Command {task.task_idx} timed out, waiting for termination...[/yellow]")
        os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
        proc.wait()
        with task.lock:
            task.timed_out.append(str(task.task.file_name))
        elapsed = time.time() - task.start_time
        elapsed_hms = time.strftime('%H:%M:%S', time.gmtime(elapsed))
        rich.print(f"[yellow]Command {task.task_idx} terminated. Elapsed time: {elapsed_hms}[/yellow]")
    except Exception as e:
        print(f"An unexpected error occurred: {e}", file=sys.stderr)
        elapsed = time.time() - task.start_time
        elapsed_hms = time.strftime('%H:%M:%S', time.gmtime(elapsed))
        rich.print(f"[red]Command {task.task_idx} failed. Elapsed time: {elapsed_hms}[/red]")


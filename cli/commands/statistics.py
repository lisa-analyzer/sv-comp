# Standard library imports
import os
import json
from typing import List, Tuple

# Load vendored packages
from vendor.package_loader import load_packages
load_packages()

# Project-local imports
from cli.models.config import Config
from cli.commands.harvest import get_task
from cli.models.lisa_report.lisa_report import LisaReport
from cli.models.task_definition.task_definition import TaskDefinition

# Third-party imports
import rich
import typer
import pandas
from pandas import DataFrame, concat
from rich.text import Text

# CLI setup
cli = typer.Typer()
config = Config.get()

ASSERTIONS_TRUE = "Assertions set to TRUE"
ASSERTIONS_FALSE = "Assertions set to FALSE"
ASSERTION_ABSENT = "Assertion property is absent from .yml file. The score is left as zero."
RUNTIME_TRUE = "Runtime exceptions set to TRUE"
RUNTIME_FALSE = "Runtime exceptions set to FALSE"
RUNTIME_ABSENT = "Runtime exceptions property is absent from .yml file. The score is left as zero."

DEFINITE_WARNING = "LiSA produced a DEFINITE warning"
DEFINITE_NOT_WARNING = "LiSA produced a DEFINITE NOT holds warning"
POSSIBLE_WARNING = "LiSA produced a POSSIBLE warning"
CONFLICT_WARNING = "LiSA produced both DEFINITE 'holds' and 'does not hold' warnings"
NO_WARNINGS = "LiSA produced no warnings"


@cli.command()
def statistics():
    """
        Computes statistics on analysis results
    """
    output_dir = os.path.join(str(config.path_to_output_dir), "results")

    parsing_error_table = None
    frontend_error_table = None
    analysis_error_table = None
    score_table = DataFrame()

    parsing_error_counter = 0
    frontend_error_counter = 0
    analysis_error_counter = 0
    test_case_counter = 0

    def process_csv(file_path, dataframe):
        temp = pandas.read_csv(file_path, sep=";")[["Message", "Type"]].groupby(["Message"]).count()
        return __add_row(temp, dataframe, os.path.basename(os.path.dirname(file_path)))

    for dir_name in os.listdir(output_dir):
        results_dir = os.path.join(output_dir, dir_name)
        if not os.path.isdir(results_dir):
            continue

        test_case_counter += 1
        treated = False

        for file in os.listdir(results_dir):
            file_path = os.path.join(results_dir, file)

            if file == "frontend.csv":
                parsing_error_table = process_csv(file_path, parsing_error_table)
                parsing_error_counter += 1
                treated = True

            elif file == "frontend-noparsing.csv":
                frontend_error_table = process_csv(file_path, frontend_error_table)
                frontend_error_counter += 1
                treated = True

            elif file == "analysis.csv":
                analysis_error_table = process_csv(file_path, analysis_error_table)
                analysis_error_counter += 1
                treated = True

        if not treated:
            this_iteration_df = __compute_score(results_dir, dir_name)
            score_table = score_table._append(this_iteration_df)
                

    timed_out_tasks = []
    if os.path.exists(f"{str(config.path_to_output_dir)}/timed_out.txt"):
        with open(f"{str(config.path_to_output_dir)}/timed_out.txt", "r") as f:
            timed_out_tasks = [line.strip() for line in f.readlines()]

    __save_output_csvs(parsing_error_table, frontend_error_table, analysis_error_table, score_table)
    __save_summary(test_case_counter, score_table, parsing_error_counter, frontend_error_counter, analysis_error_counter, timed_out_tasks)


def __add_row(temp, dataframe, test_case):
    temp["Test_cases"] = str(test_case) + "\n"
    if dataframe is None:
        dataframe = temp
    else:
        merge = pandas.merge(dataframe, temp, left_index=True, right_index=True, how="outer")
        merge["Test_cases_x"] = merge["Test_cases_x"].fillna("")
        merge["Test_cases_y"] = merge["Test_cases_y"].fillna("")
        merge = merge.fillna(0)
        merge["Type"] = merge["Type_x"] + merge["Type_y"]
        merge["Test_cases"] = merge["Test_cases_x"].astype(str) + merge["Test_cases_y"].astype(str)
        dataframe = merge[["Type", "Test_cases"]]
    return dataframe


def __compute_score(results_dir: str, file_name: str) -> DataFrame:

    task: TaskDefinition = get_task(file_name)
    with open(os.path.join(results_dir, "report.json"), encoding="utf-8") as f:
        lisa_report = LisaReport(**json.load(f))

    sv_runtime, lisa_runtime, due_runtime = __score_runtime_exceptions(task, lisa_report)
    sv_assert, lisa_assert, due_assert = __score_assertions(task, lisa_report)

    data = [
        [file_name, "runtime", sv_runtime, lisa_runtime, "\n".join(due_runtime)],
        [file_name, "assert", sv_assert, lisa_assert, "\n".join(due_assert)],
    ]

    score_table = DataFrame(
        data,
        columns=["Test case", "Type", "SV-COMP score", "LiSA internal score", "Due to"]
    )

    return score_table


def __score_assertions(task: TaskDefinition, lisa_report: LisaReport) -> Tuple[int, int, List[str]]:
    sv_comp_score = 0
    lisa_internal_score = 0
    due_to: List[str] = []

    expected = task.are_assertions_expected()
    if expected: # TRUE
        if not lisa_report.has_assert_warnings():  # EMPTY
            # Case 9
            sv_comp_score += 2
            lisa_internal_score += 2
            due_to.append(f"{ASSERTIONS_TRUE}, and {NO_WARNINGS}")
        elif lisa_report.has_possible_assert_warning():
            # Case 1, 2, 3
            sv_comp_score += 0
            lisa_internal_score -= 16
            due_to.append(f"{ASSERTIONS_TRUE}, and {POSSIBLE_WARNING}")
        elif lisa_report.check_definite_holds_and_not_holds_assert_warnings():
            # Case 4
            sv_comp_score += 0
            lisa_internal_score -= 16
            due_to.append(f"{ASSERTIONS_TRUE}, and {CONFLICT_WARNING}")
        elif lisa_report.has_definite_holds_assert_warning():
            # Case 5, 6
            sv_comp_score += 2
            lisa_internal_score += 2
            due_to.append(f"{ASSERTIONS_TRUE}, and {DEFINITE_WARNING}")
        elif lisa_report.has_definite_not_holds_assert_warning():
            # Case 7, 8
            sv_comp_score -= 16
            lisa_internal_score -= 16
            due_to.append(f"{ASSERTIONS_TRUE}, and {DEFINITE_NOT_WARNING}")
    elif expected is False:
        if not lisa_report.has_assert_warnings():  # EMPTY
            # Case 18
            sv_comp_score -= 32
            lisa_internal_score -= 32
            due_to.append(f"{ASSERTIONS_FALSE}, and {NO_WARNINGS}")
        elif lisa_report.has_possible_assert_warning():
            # Case 10, 11, 12
            sv_comp_score += 0
            lisa_internal_score -= 32
            due_to.append(f"{ASSERTIONS_FALSE}, and {POSSIBLE_WARNING}")
        elif lisa_report.check_definite_holds_and_not_holds_assert_warnings():
            # Case 13
            sv_comp_score += 0
            lisa_internal_score -= 32
            due_to.append(f"{ASSERTIONS_FALSE}, and {CONFLICT_WARNING}")
        elif lisa_report.has_definite_holds_assert_warning():
            # Case 14, 15
            sv_comp_score -= 32
            lisa_internal_score -= 32
            due_to.append(f"{ASSERTIONS_FALSE}, and {DEFINITE_WARNING}")
        elif lisa_report.has_definite_not_holds_assert_warning():
            # Case 16, 17
            sv_comp_score += 1
            lisa_internal_score += 1
            due_to.append(f"{ASSERTIONS_FALSE}, and {DEFINITE_NOT_WARNING}")
    else: # PROPERTY IS ABSENT
        # Case 31
        sv_comp_score += 0
        lisa_internal_score += 0
        due_to.append(f"{ASSERTION_ABSENT}")

    return sv_comp_score, lisa_internal_score, due_to


def __score_runtime_exceptions(task: TaskDefinition, lisa_report: LisaReport) -> Tuple[int, int, List[str]]:
    sv_comp_score = 0
    lisa_internal_score = 0
    due_to: List[str] = []

    expected = task.are_runtime_exceptions_expected()
    if expected: # TRUE
        if not lisa_report.has_runtime_warnings():  # EMPTY
            # Case 24
            sv_comp_score += 2
            lisa_internal_score += 2
            due_to.append(f"{RUNTIME_TRUE}, and {NO_WARNINGS}")
        elif lisa_report.has_possible_runtime_warning():
            # Case 19, 21, 22
            sv_comp_score += 0
            lisa_internal_score -= 16
            due_to.append(f"{RUNTIME_TRUE}, and {POSSIBLE_WARNING}")
        elif lisa_report.has_definite_runtime_warning():
            # Case 20, 23
            sv_comp_score -= 16
            lisa_internal_score -= 16
            due_to.append(f"{RUNTIME_TRUE}, and {DEFINITE_WARNING}")
    elif expected is False:
        if not lisa_report.has_runtime_warnings():  # EMPTY
            # Case 30
            sv_comp_score -= 32
            lisa_internal_score -= 32
            due_to.append(f"{RUNTIME_FALSE}, and {NO_WARNINGS}")
        elif lisa_report.has_possible_runtime_warning():
            # Case 25, 27, 28
            sv_comp_score += 0
            lisa_internal_score -= 32
            due_to.append(f"{RUNTIME_FALSE}, and {POSSIBLE_WARNING}")
        elif lisa_report.has_definite_runtime_warning():
            # Case 26, 29
            sv_comp_score += 1
            lisa_internal_score += 1
            due_to.append(f"{RUNTIME_FALSE}, and {DEFINITE_WARNING}")
    else: # PROPERTY IS ABSENT
        # Case 32
        sv_comp_score += 0
        lisa_internal_score += 0
        due_to.append(f"{RUNTIME_ABSENT}")

    return sv_comp_score, lisa_internal_score, due_to


def __save_output_csvs(
    parsing_error_table=None,
    frontend_error_table=None,
    analysis_error_table=None,
    score_table=None,
):

    def __save_sorted_csv(df, filename):
        if df is not None:
            sorted_df = df.sort_values("Type", ascending=False)
            sorted_df.to_csv(
                os.path.join(config.path_to_output_dir, filename), index=True
            )

    __save_sorted_csv(parsing_error_table, "parsing.csv")
    __save_sorted_csv(frontend_error_table, "frontend.csv")
    __save_sorted_csv(analysis_error_table, "analysis.csv")

    if score_table is not None:
        score_table = concat([score_table]).reset_index(drop=True)
        score_table.index += 1
        score_table["No."] = score_table["Test case"].factorize()[0] + 1
        score_table.set_index("No.", inplace=True)
        score_table.to_csv(os.path.join(config.path_to_output_dir, "score.csv"))


def __save_summary(
    test_case_counter: int,
    score_table,
    parsing_error_counter: int,
    frontend_error_counter: int,
    analysis_error_counter: int,
    timed_out_tasks: List[str],
):

    sv_comp_total_passed = (score_table["SV-COMP score"] > 0).sum()
    sv_comp_total_zero = (score_table["SV-COMP score"] == 0).sum()
    sv_comp_total_failed = (score_table["SV-COMP score"] < 0).sum()

    sv_comp_passed_runtime = (score_table.loc[score_table["Type"] == "runtime", "SV-COMP score"] > 0).sum()
    sv_comp_zero_runtime = (score_table.loc[score_table["Type"] == "runtime", "SV-COMP score"] == 0).sum()
    sv_comp_failed_runtime = (score_table.loc[score_table["Type"] == "runtime", "SV-COMP score"] < 0).sum()

    sv_comp_passed_assert = (score_table.loc[score_table["Type"] == "assert", "SV-COMP score"] > 0).sum()
    sv_comp_zero_assert = (score_table.loc[score_table["Type"] == "assert", "SV-COMP score"] == 0).sum()
    sv_comp_failed_assert = (score_table.loc[score_table["Type"] == "assert", "SV-COMP score"] < 0).sum()

    lisa_total_passed = (score_table["LiSA internal score"] > 0).sum()
    lisa_total_zero = (score_table["LiSA internal score"] == 0).sum()
    lisa_total_failed = (score_table["LiSA internal score"] < 0).sum()

    lisa_passed_runtime = (score_table.loc[score_table["Type"] == "runtime", "LiSA internal score"] > 0).sum()
    lisa_zero_runtime = (score_table.loc[score_table["Type"] == "runtime", "LiSA internal score"] == 0).sum()
    lisa_failed_runtime = (score_table.loc[score_table["Type"] == "runtime", "LiSA internal score"] < 0).sum()

    lisa_passed_assert = (score_table.loc[score_table["Type"] == "assert", "LiSA internal score"] > 0).sum()
    lisa_zero_assert = (score_table.loc[score_table["Type"] == "assert", "LiSA internal score"] == 0).sum()
    lisa_failed_assert = (score_table.loc[score_table["Type"] == "assert", "LiSA internal score"] < 0).sum()

    summary_lines = [
        f"Total test cases: [bold blue]{test_case_counter}[/bold blue]",
        f"Effective test cases (per property): [bold blue]{test_case_counter * 2}[/bold blue]\n",

        "[bold]SV-COMP[/bold]\n",
        f"[italic]Results[/italic]",
        f"Overall: [bold green]{sv_comp_total_passed} passed[/bold green] / [bold yellow]{sv_comp_total_zero} inconclusive[/bold yellow] / [bold red]{sv_comp_total_failed} failed[/bold red]",
        f"Runtime: [bold green]{sv_comp_passed_runtime} passed[/bold green] / [bold yellow]{sv_comp_zero_runtime} inconclusive[/bold yellow] / [bold red]{sv_comp_failed_runtime} failed[/bold red]",
        f"Assert: [bold green]{sv_comp_passed_assert} passed[/bold green] / [bold yellow]{sv_comp_zero_assert} inconclusive[/bold yellow] / [bold red]{sv_comp_failed_assert} failed[/bold red]\n",
        f"[italic]Scores[/italic]",
        f"Absolute: [bold green]{score_table['SV-COMP score'].sum()}[/bold green]",
        f"Runtime: [bold blue]{score_table.loc[score_table['Type'] == 'runtime', 'SV-COMP score'].sum()}[/bold blue]",
        f"Assert: [bold yellow]{score_table.loc[score_table['Type'] == 'assert', 'SV-COMP score'].sum()}[/bold yellow]\n",

        "[bold]LiSA internal[/bold]\n",
        f"[italic]Results[/italic]",
        f"Overall: [bold green]{lisa_total_passed} passed[/bold green] / [bold yellow]{lisa_total_zero} inconclusive[/bold yellow] / [bold red]{lisa_total_failed} failed[/bold red]",
        f"Runtime: [bold green]{lisa_passed_runtime} passed[/bold green] / [bold yellow]{lisa_zero_runtime} inconclusive[/bold yellow] / [bold red]{lisa_failed_runtime} failed[/bold red]",
        f"Assert: [bold green]{lisa_passed_assert} passed[/bold green] / [bold yellow]{lisa_zero_assert} inconclusive[/bold yellow] / [bold red]{lisa_failed_assert} failed[/bold red]\n",
        f"[italic]Scores[/italic]",
        f"Absolute: [bold green]{score_table['LiSA internal score'].sum()}[/bold green]",
        f"Runtime: [bold blue]{score_table.loc[score_table['Type'] == 'runtime', 'LiSA internal score'].sum()}[/bold blue]",
        f"Assert: [bold yellow]{score_table.loc[score_table['Type'] == 'assert', 'LiSA internal score'].sum()}[/bold yellow]\n",

        f"[red bold]Errors[/red bold] (check corresponding .csv files)",
        f"Parsing: [bold red]{parsing_error_counter}[/bold red]",
        f"Frontend: [bold red]{frontend_error_counter}[/bold red]",
        f"Analysis: [bold red]{analysis_error_counter}[/bold red]",
        f"Timeouts: [bold red]{len(timed_out_tasks)}[/bold red]",
    ]

    for line in summary_lines:
        rich.print(line)

    summary_path = os.path.join(config.path_to_output_dir, "summary.txt")
    with open(summary_path, "w") as f:
        for line in summary_lines:
            f.write(Text.from_markup(line).plain + "\n")
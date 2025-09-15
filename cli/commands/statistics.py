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


@cli.command()
def statistics():
    """
        Computes statistics on analysis results
    """
    output_dir = os.path.join(str(config.path_to_output_dir), "results")

    parsing_error_table = None
    frontend_error_table = None
    analysis_error_table = None
    # score_table = DataFrame(columns=["Test case", "SV-COMP score", "LiSA internal score", "Due to"])
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

    __save_output_csvs(parsing_error_table, frontend_error_table, analysis_error_table, score_table)

    __save_summary(test_case_counter, score_table, parsing_error_counter, frontend_error_counter, analysis_error_counter)


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

    sv_comp_score = sv_runtime + sv_assert
    lisa_internal_score = lisa_runtime + lisa_assert
    due_to = due_runtime + due_assert

    dataframe_score = DataFrame(columns=["Test case", "SV-COMP score", "LiSA internal score", "Due to"])
    dataframe_score.loc[-1] = [file_name, sv_comp_score, lisa_internal_score, "\n".join(due_to)]
    dataframe_score.index += 1
    dataframe_score.sort_index()

    return dataframe_score


def __score_assertions(task: TaskDefinition, lisa_report: LisaReport) -> Tuple[int, int, List[str]]:
    sv_comp_score = 0
    lisa_internal_score = 0
    due_to: List[str] = []

    if task.are_assertions_expected():
        if not lisa_report.has_assert_warnings():  # EMPTY
            # Case 9
            sv_comp_score += 2
            lisa_internal_score += 2
            due_to.append("Assertions were expected, and LiSA produced no warnings")
        elif lisa_report.has_possible_assert_warning():
            # Case 1, 2, 3
            sv_comp_score += 0
            lisa_internal_score -= 16
            due_to.append("Assertions were expected, and LiSA gave a POSSIBLE warning")
        elif lisa_report.check_definite_holds_and_not_holds_assert_warnings():
            # Case 4
            sv_comp_score += 0
            lisa_internal_score -= 16
            due_to.append("Assertions were expected, and LiSA produced a conflict, issuing both 'holds' and 'does not hold' warnings")
        elif lisa_report.has_definite_holds_assert_warning():
            # Case 5, 6
            sv_comp_score += 2
            lisa_internal_score += 2
            due_to.append("Assertions were expected, and LiSA produced a DEFINITE: the assertion holds warning")
        elif lisa_report.has_definite_not_holds_assert_warning():
            # Case 7, 8
            sv_comp_score -= 16
            lisa_internal_score -= 16
            due_to.append("Assertions were expected, and LiSA produced a DEFINITE: the assertion does not hold warning")
    else:
        if not lisa_report.has_assert_warnings():  # EMPTY
            # Case 18
            sv_comp_score -= 32
            lisa_internal_score -= 32
            due_to.append("Assertions were not expected, and LiSA produced no warnings")
        elif lisa_report.has_possible_assert_warning():
            # Case 10, 11, 12
            sv_comp_score += 0
            lisa_internal_score -= 32
            due_to.append("Assertions were not expected, and LiSA produced a POSSIBLE warning")
        elif lisa_report.check_definite_holds_and_not_holds_assert_warnings():
            # Case 13
            sv_comp_score += 0
            lisa_internal_score -= 32
            due_to.append("Assertions were not expected, and LiSA produced a conflict, issuing both 'holds' and 'does not hold' warnings")
        elif lisa_report.has_definite_holds_assert_warning():
            # Case 14, 15
            sv_comp_score -= 32
            lisa_internal_score -= 32
            due_to.append("Assertions were not expected, and LiSA produced a DEFINITE: the assertion holds warning")
        elif lisa_report.has_definite_not_holds_assert_warning():
            # Case 16, 17
            sv_comp_score += 1
            lisa_internal_score += 1
            due_to.append("Assertions were not expected, and LiSA produced a DEFINITE: the assertion does not hold warning")

    return sv_comp_score, lisa_internal_score, due_to


def __score_runtime_exceptions(task: TaskDefinition, lisa_report: LisaReport) -> Tuple[int, int, List[str]]:
    sv_comp_score = 0
    lisa_internal_score = 0
    due_to: List[str] = []

    if task.are_runtime_exceptions_expected(): # TRUE
        if not lisa_report.has_runtime_warnings():  # EMPTY
            # Case 24
            sv_comp_score += 2
            lisa_internal_score += 2
            due_to.append("Runtime exceptions were expected, and LiSA produced no warnings")
        elif lisa_report.has_possible_runtime_warning():
            # Case 19, 21, 22
            sv_comp_score += 0
            lisa_internal_score -= 16
            due_to.append("Runtime exceptions were expected, and LiSA produced a POSSIBLE warning")
        elif lisa_report.has_definite_runtime_warning():
            # Case 20, 23
            sv_comp_score -= 16
            lisa_internal_score -= 16
            due_to.append("Runtime exceptions were expected, and LiSA produced a DEFINITE warning")
    else: # FALSE
        if not lisa_report.has_runtime_warnings():  # EMPTY
            # Case 30
            sv_comp_score -= 32
            lisa_internal_score -= 32
            due_to.append("Runtime exceptions were not expected, and LiSA produced no warnings")
        elif lisa_report.has_possible_runtime_warning():
            # Case 25, 27, 28
            sv_comp_score += 0
            lisa_internal_score -= 32
            due_to.append("Runtime exceptions were not expected, and LiSA produced a POSSIBLE warning")
        elif lisa_report.has_definite_runtime_warning():
            # Case 26, 29
            sv_comp_score += 1
            lisa_internal_score += 1
            due_to.append("Runtime exceptions were not expected, and LiSA produced a DEFINITE warning")

    return sv_comp_score, lisa_internal_score, due_to


def __save_output_csvs(
    parsing_error_table=None,
    frontend_error_table=None,
    analysis_error_table=None,
    score_table=None,
):

    def save_sorted_csv(df, filename):
        if df is not None:
            df.sort_values("Type", ascending=False).to_csv(
                os.path.join(config.path_to_output_dir, filename), index=False
            )

    save_sorted_csv(parsing_error_table, "parsing.csv")
    save_sorted_csv(frontend_error_table, "frontend.csv")
    save_sorted_csv(analysis_error_table, "analysis.csv")

    if score_table is not None:
        score_table = concat([score_table], ignore_index=True)
        score_table.index = range(1, len(score_table) + 1)
        score_table.index.name = "No."
        score_table.to_csv(os.path.join(config.path_to_output_dir, "score.csv"))


def __save_summary(
    test_case_counter: int,
    score_table,
    parsing_error_counter: int,
    frontend_error_counter: int,
    analysis_error_counter: int,
):
    summary_lines = [
        f"No. of test cases: [bold blue]{test_case_counter}[/bold blue]\n",
        f"SV-COMP score: [bold green]{score_table['SV-COMP score'].sum()}[/bold green]",
        f"LiSA internal score: [bold green]{score_table['LiSA internal score'].sum()}[/bold green]\n",
        f"Parsing errors (parsing.csv): [bold red]{parsing_error_counter}[/bold red]",
        f"Frontend errors (frontend.csv): [bold red]{frontend_error_counter}[/bold red]",
        f"Analysis errors (analysis.csv): [bold red]{analysis_error_counter}[/bold red]",
    ]

    for line in summary_lines:
        rich.print(line)

    summary_path = os.path.join(config.path_to_output_dir, "summary.txt")
    with open(summary_path, "w") as f:
        for line in summary_lines:
            f.write(Text.from_markup(line).plain + "\n")
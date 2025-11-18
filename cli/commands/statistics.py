# Standard library imports
import os
import json
from typing import List, Tuple

# Load vendored packages
from vendor.package_loader import load_packages
load_packages()

# Project-local imports
from cli.models.config import Config
from cli.commands.harvest import get_task, get_tasks
from cli.models.lisa_report.lisa_report import LisaReport
from cli.models.task_definition.task_definition import TaskDefinition
from cli.utils.util import classify_asserts, AssertClassification, classify_runtime, RuntimeClassification

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
RUNTIME_TRUE = "Runtime exceptions set to TRUE"
RUNTIME_FALSE = "Runtime exceptions set to FALSE"

DEFINITE_WARNING = "LiSA produced only DEFINITE HOLDS warnings"
DEFINITE_NOT_WARNING = "LiSA produced only DEFINITE NOT holds warnings"
POSSIBLE_NOT_WARNING = "LiSA produced only POSSIBLY NOT holds warnings"
CONFLICT_NOT_WARNING = "LiSA produced both DEFINITE and POSSIBLE 'does not hold' warnings"
CONFLICT_HOLDS_AND_NOT_WARNING = "LiSA produced both DEFINITE 'holds' and 'does not hold' warnings"
CONFLICT_HOLDS_AND_POSSIBLY_NOT_WARNING = "LiSA produced both DEFINITE 'holds' and POSSIBLE 'does not hold' warnings"
CONFLICT_ALL_WARNING = "LiSA produced both DEFINITE 'holds' and 'does not hold', and POSSIBLE 'does not hold' warnings"
UNKNOWN_WARNING = "LiSA classification unknown"
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
    svcomp_scores = DataFrame()

    parsing_error_counter = 0
    frontend_error_counter = 0
    analysis_error_counter = 0

    def process_csv(file_path, dataframe):
        temp = pandas.read_csv(file_path, sep=";")[["Message", "Type"]].groupby(["Message"]).count()
        return __add_row(temp, dataframe, os.path.basename(os.path.dirname(file_path)))

    for dir_name in os.listdir(output_dir):
        results_dir = os.path.join(output_dir, dir_name)
        if not os.path.isdir(results_dir):
            continue

        treated = False

        for file in os.listdir(results_dir):
            file_path = os.path.join(results_dir, file)

            if file == "frontend.csv":
                parsing_error_table = process_csv(file_path, parsing_error_table)
                svcomp_iteration_df = __to_svcomp_table_entry(dir_name, "UNKNOWN", 0)
                svcomp_scores = svcomp_scores._append(svcomp_iteration_df)
                parsing_error_counter += 1
                treated = True

            elif file == "frontend-noparsing.csv":
                frontend_error_table = process_csv(file_path, frontend_error_table)
                svcomp_iteration_df = __to_svcomp_table_entry(dir_name, "UNKNOWN", 0)
                svcomp_scores = svcomp_scores._append(svcomp_iteration_df)
                frontend_error_counter += 1
                treated = True

            elif file == "analysis.csv":
                analysis_error_table = process_csv(file_path, analysis_error_table)
                svcomp_iteration_df = __to_svcomp_table_entry(dir_name, "UNKNOWN", 0)
                svcomp_scores = svcomp_scores._append(svcomp_iteration_df)
                analysis_error_counter += 1
                treated = True

        if not treated:
            this_iteration_df, svcomp_iteration_df = __compute_score(results_dir, dir_name)
            score_table = score_table._append(this_iteration_df)
            svcomp_scores = svcomp_scores._append(svcomp_iteration_df)
                

    timed_out_tasks = []
    if os.path.exists(f"{str(config.path_to_output_dir)}/timed_out.txt"):
        with open(f"{str(config.path_to_output_dir)}/timed_out.txt", "r") as f:
            timed_out_tasks = [line.strip() for line in f.readlines()]
    for t in timed_out_tasks:
        svcomp_iteration_df = __to_svcomp_table_entry(t, "TIMEOUT", 0)
        svcomp_scores = svcomp_scores._append(svcomp_iteration_df)

    __save_output_csvs(parsing_error_table, frontend_error_table, analysis_error_table, score_table, svcomp_scores)
    __save_summary(score_table, parsing_error_counter, frontend_error_counter, analysis_error_counter, timed_out_tasks)

def __to_svcomp_table_entry(file_name, virdict, score):
    task: TaskDefinition = get_task(file_name)
    svcomp_data = []
    if task.are_runtime_exceptions_expected() is not None:
        svcomp_data.append([file_name, f"runtime|{task.are_runtime_exceptions_expected()}", virdict, score])
    if task.are_assertions_expected() is not None:
        svcomp_data.append([file_name, f"assert|{task.are_assertions_expected()}", virdict, score])
    svcomp_iteration_df = DataFrame(
        svcomp_data,
        columns=["Test case", "Type", "Virdict", "Score"]
    )
    return svcomp_iteration_df

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

    sv_runtime, due_runtime, virdict_runtime = __score_runtime_exceptions(task, lisa_report)
    sv_assert, due_assert, virdict_assert = __score_assertions(task, lisa_report)
    
    internal_data = []
    svcomp_data = []
    if task.are_runtime_exceptions_expected() is not None:
        internal_data.append([file_name, "runtime", sv_runtime, "\n".join(due_runtime)])
        svcomp_data.append([file_name, f"runtime|{task.are_runtime_exceptions_expected()}", virdict_runtime, sv_runtime])
    if task.are_assertions_expected() is not None:
        internal_data.append([file_name, "assert", sv_assert, "\n".join(due_assert)])
        svcomp_data.append([file_name, f"assert|{task.are_assertions_expected()}", virdict_assert, sv_assert])

    score_table = DataFrame(
        internal_data,
        columns=["Test case", "Type", "SV-COMP score", "Due to"]
    )
    svcomp_table = DataFrame(
        svcomp_data,
        columns=["Test case", "Type", "Virdict", "Score"]
    )

    return score_table, svcomp_table


def __score_assertions(task: TaskDefinition, lisa_report: LisaReport) -> Tuple[int, List[str]]:
    sv_comp_score = 0
    due_to: List[str] = []

    expected = task.are_assertions_expected()
    classification = classify_asserts(lisa_report)
    virdict = classification.value[1]
    if expected: # TRUE
        expected_res = ASSERTIONS_TRUE
        match classification.value[1]:
            case "TRUE":
                sv_comp_score = 2
            case "FALSE":
                sv_comp_score = -16
            case "UNKNOWN":
                sv_comp_score = 0
    elif expected is False: # FALSE
        expected_res = ASSERTIONS_FALSE
        match classification.value[1]:
            case "TRUE":
                sv_comp_score = -32
            case "FALSE":
                sv_comp_score = 1
            case "UNKNOWN":
                sv_comp_score = 0
    else: # PROPERTY IS ABSENT
        return 0, []

    match classification:
        case AssertClassification.NO_WARNINGS:
            due_to.append(f"{expected_res}, and {NO_WARNINGS}")
        case AssertClassification.ONLY_DEFINITE_HOLDS:
            due_to.append(f"{expected_res}, and {DEFINITE_WARNING}")
        case AssertClassification.ONLY_POSSIBLE_NOT_HOLDS:
            due_to.append(f"{expected_res}, and {POSSIBLE_NOT_WARNING}")
        case AssertClassification.ONLY_DEFINITE_NOT_HOLDS:
            due_to.append(f"{expected_res}, and {DEFINITE_NOT_WARNING}")
        case AssertClassification.CONFLICTING_NOT_HOLDS:
            due_to.append(f"{expected_res}, and {CONFLICT_NOT_WARNING}")
        case AssertClassification.CONFLICTING_HOLDS_AND_NOT_HOLDS:
            due_to.append(f"{expected_res}, and {CONFLICT_HOLDS_AND_NOT_WARNING}")
        case AssertClassification.CONFLICTING_HOLDS_AND_POSSIBLY_NOT_HOLDS:
            due_to.append(f"{expected_res}, and {CONFLICT_HOLDS_AND_POSSIBLY_NOT_WARNING}")
        case AssertClassification.ALL:
            due_to.append(f"{expected_res}, and {CONFLICT_ALL_WARNING}")
        case AssertClassification.UNKNOWN:
            due_to.append(f"{expected_res}, and {UNKNOWN_WARNING}")

    return sv_comp_score, due_to, virdict


def __score_runtime_exceptions(task: TaskDefinition, lisa_report: LisaReport) -> Tuple[int, List[str]]:
    sv_comp_score = 0
    due_to: List[str] = []

    expected = task.are_runtime_exceptions_expected()
    classification = classify_runtime(lisa_report)
    virdict = classification.value[1]
    if expected: # TRUE
        expected_res = RUNTIME_TRUE
        match classification.value[1]:
            case "TRUE":
                sv_comp_score = 2
            case "FALSE":
                sv_comp_score = -16
            case "UNKNOWN":
                sv_comp_score = 0
    elif expected is False: # FALSE
        expected_res = RUNTIME_FALSE
        match classification.value[1]:
            case "TRUE":
                sv_comp_score = -32
            case "FALSE":
                sv_comp_score = 1
            case "UNKNOWN":
                sv_comp_score = 0
    else: # PROPERTY IS ABSENT
        return 0, []

    match classification:
        case RuntimeClassification.NO_WARNINGS:
            due_to.append(f"{expected_res}, and {NO_WARNINGS}")
        case RuntimeClassification.ONLY_POSSIBLE_NOT_HOLDS:
            due_to.append(f"{expected_res}, and {POSSIBLE_NOT_WARNING}")
        case RuntimeClassification.ONLY_DEFINITE_NOT_HOLDS:
            due_to.append(f"{expected_res}, and {DEFINITE_NOT_WARNING}")
        case RuntimeClassification.CONFLICTING_NOT_HOLDS:
            due_to.append(f"{expected_res}, and {CONFLICT_NOT_WARNING}")
        case RuntimeClassification.UNKNOWN:
            due_to.append(f"{expected_res}, and {UNKNOWN_WARNING}")
    
    return sv_comp_score, due_to, virdict


def __save_output_csvs(
    parsing_error_table=None,
    frontend_error_table=None,
    analysis_error_table=None,
    score_table=None,
    svcomp_scores=None,
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
    
    if svcomp_scores is not None:
        svcomp_scores = concat([svcomp_scores]).reset_index(drop=True)
        svcomp_scores.index += 1
        svcomp_scores["No."] = svcomp_scores["Test case"].factorize()[0] + 1
        svcomp_scores.set_index("No.", inplace=True)
        svcomp_scores.to_csv(os.path.join(config.path_to_output_dir, "svcomp.csv"))

    if score_table is not None:
        score_table = concat([score_table]).reset_index(drop=True)
        score_table.index += 1
        score_table["No."] = score_table["Test case"].factorize()[0] + 1
        score_table.set_index("No.", inplace=True)
        score_table.to_csv(os.path.join(config.path_to_output_dir, "score.csv"))


def __save_summary(
    score_table,
    parsing_error_counter: int,
    frontend_error_counter: int,
    analysis_error_counter: int,
    timed_out_tasks: List[str],
):
    all_tasks = get_tasks()
    assert_tasks = 0
    runtime_tasks = 0
    for task in all_tasks:
        if task.are_assertions_expected() is not None:
            assert_tasks += 1
        if task.are_runtime_exceptions_expected() is not None:
            runtime_tasks += 1

    sv_comp_total_passed = (score_table["SV-COMP score"] > 0).sum()
    sv_comp_total_zero = (score_table["SV-COMP score"] == 0).sum()
    sv_comp_total_failed = (score_table["SV-COMP score"] < 0).sum()

    sv_comp_passed_runtime = (score_table.loc[score_table["Type"] == "runtime", "SV-COMP score"] > 0).sum()
    sv_comp_zero_runtime = (score_table.loc[score_table["Type"] == "runtime", "SV-COMP score"] == 0).sum()
    sv_comp_failed_runtime = (score_table.loc[score_table["Type"] == "runtime", "SV-COMP score"] < 0).sum()

    sv_comp_passed_assert = (score_table.loc[score_table["Type"] == "assert", "SV-COMP score"] > 0).sum()
    sv_comp_zero_assert = (score_table.loc[score_table["Type"] == "assert", "SV-COMP score"] == 0).sum()
    sv_comp_failed_assert = (score_table.loc[score_table["Type"] == "assert", "SV-COMP score"] < 0).sum()
    
    runtime_score = score_table.loc[score_table['Type'] == 'runtime', 'SV-COMP score'].sum()
    assert_score = score_table.loc[score_table['Type'] == 'assert', 'SV-COMP score'].sum()
    norm_score = ((runtime_score / runtime_tasks) + (assert_score / assert_tasks)) * ((runtime_tasks + assert_tasks) / 2)

    summary_lines = [
        f"Test files: [bold blue]{len(all_tasks)}[/bold blue]",
        f"Test files with assert task: [bold blue]{assert_tasks}[/bold blue]",
        f"Test files with runtime exceptions task: [bold blue]{runtime_tasks}[/bold blue]",
        f"Total tasks: [bold blue]{assert_tasks + runtime_tasks}[/bold blue]\n",

        f"[italic]Results[/italic]",
        f"Overall: [bold green]{sv_comp_total_passed} passed[/bold green] / [bold yellow]{sv_comp_total_zero} inconclusive[/bold yellow] / [bold red]{sv_comp_total_failed} failed[/bold red]",
        f"Runtime: [bold green]{sv_comp_passed_runtime} passed[/bold green] / [bold yellow]{sv_comp_zero_runtime} inconclusive[/bold yellow] / [bold red]{sv_comp_failed_runtime} failed[/bold red]",
        f"Assert: [bold green]{sv_comp_passed_assert} passed[/bold green] / [bold yellow]{sv_comp_zero_assert} inconclusive[/bold yellow] / [bold red]{sv_comp_failed_assert} failed[/bold red]\n",
        f"[italic]Scores[/italic]",
        f"Absolute: [bold green]{score_table['SV-COMP score'].sum()}[/bold green]",
        f"Normalized: [bold green]{norm_score}[/bold green]",
        f"Runtime: [bold blue]{runtime_score}[/bold blue]",
        f"Assert: [bold yellow]{assert_score}[/bold yellow]\n",

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


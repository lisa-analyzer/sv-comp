# Standard library imports
import json
import os

# Load vendored packages
from vendor.package_loader import load_packages

load_packages()

# Project-local imports
import pandas

# Third-party imports
import rich
import typer
from pandas import DataFrame, concat
from rich.text import Text

from cli.commands.harvest import get_task, get_tasks
from cli.models.config import Config
from cli.models.lisa_report.lisa_report import LisaReport
from cli.models.property import Property, SVCOMP_NAMES
from cli.models.task_definition.task_definition import TaskDefinition
from cli.utils.jlisa import WITNESS_CORRECT
from cli.utils.bug_finding import read_bug_finding
from cli.utils.witness_validation import read_validation
from cli.utils.util import (
    AssertClassification,
    RuntimeClassification,
    classify_asserts,
    classify_runtime,
)

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
CONFLICT_NOT_WARNING = (
    "LiSA produced both DEFINITE and POSSIBLE 'does not hold' warnings"
)
CONFLICT_HOLDS_AND_NOT_WARNING = (
    "LiSA produced both DEFINITE 'holds' and 'does not hold' warnings"
)
CONFLICT_HOLDS_AND_POSSIBLY_NOT_WARNING = (
    "LiSA produced both DEFINITE 'holds' and POSSIBLE 'does not hold' warnings"
)
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
    all_bottoms = []
    all_opens = []

    parsing_error_counter = 0
    frontend_error_counter = 0
    analysis_error_counter = 0

    timed_out_tasks = []
    if os.path.exists(f"{config.path_to_output_dir!s}/timed_out.txt"):
        with open(f"{config.path_to_output_dir!s}/timed_out.txt", "r") as f:
            timed_out_tasks = [line.strip() for line in f]

    def process_csv(file_path, dataframe):
        temp = (
            pandas.read_csv(file_path, sep=";")[["Message", "Type"]]
            .groupby(["Message"])
            .count()
        )
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
                svcomp_iteration_df = __to_svcomp_table_entry(
                    dir_name, "UNKNOWN (parsing)", 0
                )
                svcomp_scores = svcomp_scores._append(svcomp_iteration_df)
                parsing_error_counter += 1
                treated = True

            elif file == "frontend-noparsing.csv":
                frontend_error_table = process_csv(file_path, frontend_error_table)
                svcomp_iteration_df = __to_svcomp_table_entry(
                    dir_name, "UNKNOWN (frontend)", 0
                )
                svcomp_scores = svcomp_scores._append(svcomp_iteration_df)
                frontend_error_counter += 1
                treated = True

            elif file == "analysis.csv":
                analysis_error_table = process_csv(file_path, analysis_error_table)
                svcomp_iteration_df = __to_svcomp_table_entry(
                    dir_name, "UNKNOWN (analysis)", 0
                )
                svcomp_scores = svcomp_scores._append(svcomp_iteration_df)
                analysis_error_counter += 1
                treated = True

        if not treated and dir_name not in timed_out_tasks:
            svcomp_iteration_df, bottoms, opens = __compute_score(results_dir, dir_name)
            for notice in bottoms:
                all_bottoms.append((dir_name, notice.message))
            for notice in opens:
                all_opens.append((dir_name, notice.message))
            svcomp_scores = svcomp_scores._append(svcomp_iteration_df)

    for t in timed_out_tasks:
        svcomp_iteration_df = __to_svcomp_table_entry(t, "TIMEOUT", 0)
        svcomp_scores = svcomp_scores._append(svcomp_iteration_df)

    svcomp_scores, bug_finding = __apply_bug_finding(svcomp_scores, output_dir)

    __save_output_csvs(
        parsing_error_table,
        frontend_error_table,
        analysis_error_table,
        svcomp_scores,
        all_bottoms,
        all_opens,
    )
    __save_summary(
        svcomp_scores,
        parsing_error_counter,
        frontend_error_counter,
        analysis_error_counter,
        timed_out_tasks,
        bug_finding,
    )


def __apply_bug_finding(scores: DataFrame, output_dir: str) -> tuple[DataFrame, bool]:
    """
    The results with the verdicts of the bug-finding fallback (`analyse --bug-finding-fallback`), where jlisa
    ends with UNKNOWN or fails: a violation found gives "FALSE (bug finding)", scored as a FALSE result, with its
    witness. The column "Score (jlisa)" keeps the score of jlisa alone. Also returns whether the bug-finding
    fallback ran on some result.
    """
    scores = scores.reset_index(drop=True)
    scores["Score (jlisa)"] = scores["Score"]
    for column in ("Witness", "Witness validation"):
        if column not in scores:
            scores[column] = ""
    ran = False
    for i, row in scores.iterrows():
        name, prop, expected = row["Test case"].split("|")
        results_dir = os.path.join(output_dir, name)
        verdict = read_bug_finding(results_dir, Property(prop))
        ran = ran or verdict != ""
        if verdict != "FALSE":
            continue
        scores.at[i, "Virdict"] = "FALSE (bug finding)"
        scores.at[i, "Score"] = 1 if expected == "False" else -16
        scores.at[i, "Witness"] = __witness(results_dir, Property(prop))
        scores.at[i, "Witness validation"] = __witness_validation(results_dir, Property(prop))
    return scores, ran


def __to_svcomp_table_entry(file_name, virdict, score):
    task: TaskDefinition = get_task(file_name)
    svcomp_data = []
    if task.are_runtime_exceptions_expected() is not None:
        svcomp_data.append(
            [
                f"{file_name}|runtime|{task.are_runtime_exceptions_expected()}",
                virdict,
                score,
            ]
        )
    if task.are_assertions_expected() is not None:
        svcomp_data.append(
            [f"{file_name}|assert|{task.are_assertions_expected()}", virdict, score]
        )
    svcomp_iteration_df = DataFrame(
        svcomp_data, columns=["Test case", "Virdict", "Score"]
    )
    return svcomp_iteration_df


def __add_row(temp, dataframe, test_case):
    temp["Test_cases"] = str(test_case) + "\n"
    if dataframe is None:
        dataframe = temp
    else:
        merge = pandas.merge(
            dataframe, temp, left_index=True, right_index=True, how="outer"
        )
        merge["Test_cases_x"] = merge["Test_cases_x"].fillna("")
        merge["Test_cases_y"] = merge["Test_cases_y"].fillna("")
        merge = merge.fillna(0)
        merge["Type"] = merge["Type_x"] + merge["Type_y"]
        merge["Test_cases"] = merge["Test_cases_x"].astype(str) + merge[
            "Test_cases_y"
        ].astype(str)
        dataframe = merge[["Type", "Test_cases"]]
    return dataframe


def __compute_score(results_dir: str, file_name: str) -> DataFrame:
    task: TaskDefinition = get_task(file_name)
    with open(os.path.join(results_dir, "report.json"), encoding="utf-8") as f:
        lisa_report = LisaReport(**json.load(f))

    sv_runtime, due_runtime, virdict_runtime = __score_runtime_exceptions(
        task, lisa_report
    )
    sv_assert, due_assert, virdict_assert = __score_assertions(task, lisa_report)

    svcomp_data = []
    if task.are_runtime_exceptions_expected() is not None:
        svcomp_data.append(
            [
                f"{file_name}|runtime|{task.are_runtime_exceptions_expected()}",
                virdict_runtime,
                sv_runtime,
                "\n".join(due_runtime),
                lisa_report.count_bottom_notices(),
                lisa_report.count_open_call_notices(),
                __witness(results_dir, Property.RUNTIME),
                __witness_validation(results_dir, Property.RUNTIME),
            ]
        )
    if task.are_assertions_expected() is not None:
        svcomp_data.append(
            [
                f"{file_name}|assert|{task.are_assertions_expected()}",
                virdict_assert,
                sv_assert,
                "\n".join(due_assert),
                lisa_report.count_bottom_notices(),
                lisa_report.count_open_call_notices(),
                __witness(results_dir, Property.ASSERT),
                __witness_validation(results_dir, Property.ASSERT),
            ]
        )

    svcomp_table = DataFrame(
        svcomp_data,
        columns=[
            "Test case",
            "Virdict",
            "Score",
            "Due to",
            "Num Bottom",
            "Num Open Calls",
            "Witness",
            "Witness validation",
        ],
    )

    return (
        svcomp_table,
        lisa_report.get_bottom_notices(),
        lisa_report.get_open_call_notices(),
    )


def __witness(results_dir: str, property: Property) -> str:
    """
    "yes" if jlisa wrote the violation witness of the property, in witness/<property>/witness.yml of the
    results of the task, otherwise "".
    """
    witness = os.path.join(results_dir, "witness", SVCOMP_NAMES[property], "witness.yml")
    return "yes" if os.path.isfile(witness) else ""


def __witness_validation(results_dir: str, property: Property) -> str:
    """
    The verdict of jlisa-wit on the violation witness of the property (first line of validation.txt next to
    the witness, written by `analyse --validate-witnesses`), or "" if the witness was not validated.
    """
    return read_validation(os.path.join(results_dir, "witness", SVCOMP_NAMES[property]))


def __score_assertions(
    task: TaskDefinition, lisa_report: LisaReport
) -> tuple[int, list[str]]:
    sv_comp_score = 0
    due_to: list[str] = []

    expected = task.are_assertions_expected()
    classification = classify_asserts(lisa_report)
    virdict = classification.value[1]
    if expected:  # TRUE
        expected_res = ASSERTIONS_TRUE
        match classification.value[1]:
            case "TRUE":
                sv_comp_score = 2
            case "FALSE":
                sv_comp_score = -16
            case "UNKNOWN":
                sv_comp_score = 0
    elif expected is False:  # FALSE
        expected_res = ASSERTIONS_FALSE
        match classification.value[1]:
            case "TRUE":
                sv_comp_score = -32
            case "FALSE":
                sv_comp_score = 1
            case "UNKNOWN":
                sv_comp_score = 0
    else:  # PROPERTY IS ABSENT
        return 0, [], "UNKNOWN"

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
            due_to.append(
                f"{expected_res}, and {CONFLICT_HOLDS_AND_POSSIBLY_NOT_WARNING}"
            )
        case AssertClassification.ALL:
            due_to.append(f"{expected_res}, and {CONFLICT_ALL_WARNING}")
        case AssertClassification.UNKNOWN:
            due_to.append(f"{expected_res}, and {UNKNOWN_WARNING}")

    return sv_comp_score, due_to, virdict


def __score_runtime_exceptions(
    task: TaskDefinition, lisa_report: LisaReport
) -> tuple[int, list[str]]:
    sv_comp_score = 0
    due_to: list[str] = []

    expected = task.are_runtime_exceptions_expected()
    classification = classify_runtime(lisa_report)
    virdict = classification.value[1]
    if expected:  # TRUE
        expected_res = RUNTIME_TRUE
        match classification.value[1]:
            case "TRUE":
                sv_comp_score = 2
            case "FALSE":
                sv_comp_score = -16
            case "UNKNOWN":
                sv_comp_score = 0
    elif expected is False:  # FALSE
        expected_res = RUNTIME_FALSE
        match classification.value[1]:
            case "TRUE":
                sv_comp_score = -32
            case "FALSE":
                sv_comp_score = 1
            case "UNKNOWN":
                sv_comp_score = 0
    else:  # PROPERTY IS ABSENT
        return 0, [], "UNKNOWN"

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
    svcomp_scores=None,
    bottom_locations=None,
    open_locations=None,
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

    bottoms_table = DataFrame(
        bottom_locations,
        columns=[
            "Test case",
            "Notice",
        ],
    )
    bottoms_table.to_csv(os.path.join(config.path_to_output_dir, "bottoms.csv"))
    opens_table = DataFrame(
        open_locations,
        columns=[
            "Test case",
            "Notice",
        ],
    )
    opens_table.to_csv(os.path.join(config.path_to_output_dir, "opens.csv"))


def __save_summary(
    scores,
    parsing_error_counter: int,
    frontend_error_counter: int,
    analysis_error_counter: int,
    timed_out_tasks: list[str],
    bug_finding: bool,
):
    all_tasks = get_tasks()
    assert_tasks = 0
    runtime_tasks = 0
    for task in all_tasks:
        if task.are_assertions_expected() is not None:
            assert_tasks += 1
        if task.are_runtime_exceptions_expected() is not None:
            runtime_tasks += 1

    # the results and scores of jlisa alone, and, when the bug-finding fallback ran, of jlisa with it
    results_lines = __results_and_scores(scores, "Score (jlisa)", runtime_tasks, assert_tasks, "")
    if bug_finding:
        results_lines += __results_and_scores(scores, "Score", runtime_tasks, assert_tasks, " (jlisa + bug finding)")

    count_bot = int(scores["Num Bottom"].sum())
    count_open = int(scores["Num Open Calls"].sum())

    # the violation witnesses of each property, and the correct FALSE results of that property (the verdict is
    # FALSE and the expected verdict is False)
    witness_lines = []
    for name, label in (("runtime", "Runtime"), ("assert", "Assert")):
        rows = scores.loc[scores["Test case"].str.contains(rf"\|{name}\|", na=False)]
        # the rows of tasks with errors or timeouts have no witness. When every task has one, the column is missing
        written = rows["Witness"] == "yes" if "Witness" in rows else pandas.Series(False, index=rows.index)
        correct_false = rows["Virdict"].str.startswith("FALSE", na=False) & rows["Test case"].str.endswith("|False")
        # the verdicts of jlisa-wit, when `analyse --validate-witnesses` ran
        validations = rows["Witness validation"] if "Witness validation" in rows else pandas.Series("", index=rows.index)
        checked = written & (validations.fillna("") != "")
        validated = written & (validations == WITNESS_CORRECT)
        validation_note = (
            f"[bold blue]{int(validated.sum())}[/bold blue] validated successfully" if checked.any()
            else "not validated"
        )
        witness_lines.append(
            f"{label}: [bold blue]{int(written.sum())}[/bold blue] written ({validation_note}), "
            f"[bold blue]{int((written & correct_false).sum())}[/bold blue] of {int(correct_false.sum())} "
            "correct FALSE results with a witness"
        )
    witness_lines[-1] += "\n"

    summary_lines = [
        f"Test files: [bold blue]{len(all_tasks)}[/bold blue]",
        f"Test files with assert task: [bold blue]{assert_tasks}[/bold blue]",
        f"Test files with runtime exceptions task: [bold blue]{runtime_tasks}[/bold blue]",
        f"Total tasks: [bold blue]{assert_tasks + runtime_tasks}[/bold blue]\n",
        *results_lines,
        "[italic]Violation witnesses[/italic]",
        *witness_lines,
        "[red bold]Errors[/red bold] (check corresponding .csv files)",
        f"Parsing: [bold red]{parsing_error_counter}[/bold red]",
        f"Frontend: [bold red]{frontend_error_counter}[/bold red]",
        f"Analysis: [bold red]{analysis_error_counter}[/bold red]",
        f"Timeouts: [bold red]{len(timed_out_tasks)}[/bold red]",
        f"Number of suspicious bottom states computed: [bold red]{count_bot}[/bold red]",
        f"Number of open calls produced: [bold red]{count_open}[/bold red]",
    ]

    for line in summary_lines:
        rich.print(line)

    summary_path = os.path.join(config.path_to_output_dir, "summary.txt")
    with open(summary_path, "w") as f:
        for line in summary_lines:
            f.write(Text.from_markup(line).plain + "\n")


def __results_and_scores(scores: DataFrame, column: str, runtime_tasks: int, assert_tasks: int,
                         title: str) -> list[str]:
    """
    The lines of the summary with the results (passed, inconclusive, failed) and the scores of the given score
    column, under the headers "Results" and "Scores" followed by the given title.
    """
    runtime = scores["Test case"].str.contains(r"\|runtime\|", na=False)
    assert_ = scores["Test case"].str.contains(r"\|assert\|", na=False)

    def counts(rows) -> str:
        values = scores.loc[rows, column]
        return (f"[bold green]{(values > 0).sum()} passed[/bold green] / "
                f"[bold yellow]{(values == 0).sum()} inconclusive[/bold yellow] / "
                f"[bold red]{(values < 0).sum()} failed[/bold red]")

    runtime_score = scores.loc[runtime, column].sum()
    assert_score = scores.loc[assert_, column].sum()
    norm_score = round(
        ((runtime_score / runtime_tasks) + (assert_score / assert_tasks))
        * ((runtime_tasks + assert_tasks) / 2)
    )
    return [
        f"[italic]Results{title}[/italic]",
        f"Overall: {counts(runtime | assert_)}",
        f"Runtime: {counts(runtime)}",
        f"Assert: {counts(assert_)}\n",
        f"[italic]Scores{title}[/italic]",
        f"Absolute: [bold green]{scores[column].sum()}[/bold green]",
        f"Normalized: [bold green]{norm_score}[/bold green]",
        f"Runtime: [bold blue]{runtime_score}[/bold blue]",
        f"Assert: [bold yellow]{assert_score}[/bold yellow]\n",
    ]

# Standard library imports

# Load vendored packages
from vendor.package_loader import load_packages
load_packages()

# Project-local imports
from cli.models.config import Config

# Third-party imports
import rich
import typer
from typing import Annotated
from typing_extensions import Optional
import pandas as pd

# CLI setup
cli = typer.Typer()
config = Config.get()

@cli.command()
def compare(
        first: Annotated[Optional[str], typer.Option(
            "--first", "-f",
            help="Path to the first SV-COMP results table (produced by command 'statistics')"
        )] = None,
        second: Annotated[Optional[str], typer.Option(
            "--second", "-s",
            help="Path to the second SV-COMP results table (produced by command 'statistics')",
        )] = None,
        output: Annotated[Optional[str], typer.Option(
            "--output", "-o",
            help="Path to the output file for the comparison results",
        )] = 'comparison.csv'
):
    """
        Compares two SV-COMP results tables (produced by command 'statistics') to find differences
    """
    if not all([first, second]):
        raise typer.BadParameter(
            "Both --first and --second must be provided."
        )
    
    __compare_csv_files(first, second, output)

def __compare_csv_files(file1: str, file2: str, output: str = "comparison.csv"):
    """Compare two CSV files and create a comparison dataframe."""
    
    # Read both files
    rich.print(f"Reading first file: {file1}")
    df1 = pd.read_csv(file1)
    rich.print(f"Reading second file: {file2}")
    df2 = pd.read_csv(file2)
    
    # Get all unique test cases from both files
    all_testcases = set(df1['Test case'].unique()) | set(df2['Test case'].unique())
    
    first_testcases = len(df1)
    first_total_score = df1['Score'].sum()
    first_correct_true = len(df1[(df1['Virdict'] == 'TRUE') & (df1['Score'] == 2)])
    first_correct_false = len(df1[(df1['Virdict'] == 'FALSE') & (df1['Score'] == 1)])
    first_incorrect_true = len(df1[(df1['Virdict'] == 'TRUE') & (df1['Score'] == -32)])
    first_incorrect_false = len(df1[(df1['Virdict'] == 'FALSE') & (df1['Score'] == -16)])
    first_unknown = len(df1[(df1['Virdict'] == 'UNKNOWN') & (df1['Score'] == 0)])
    first_unknown_parsing = len(df1[(df1['Virdict'] == 'UNKNOWN (parsing)') & (df1['Score'] == 0)])
    first_unknown_frontend = len(df1[(df1['Virdict'] == 'UNKNOWN (frontend)') & (df1['Score'] == 0)])
    first_unknown_analysis = len(df1[(df1['Virdict'] == 'UNKNOWN (analysis)') & (df1['Score'] == 0)])
    first_timeout = len(df1[(df1['Virdict'] == 'TIMEOUT') & (df1['Score'] == 0)])
    
    second_testcases = len(df2)
    second_total_score = df2['Score'].sum()
    second_correct_true = len(df2[(df2['Virdict'] == 'TRUE') & (df2['Score'] == 2)])
    second_correct_false = len(df2[(df2['Virdict'] == 'FALSE') & (df2['Score'] == 1)])
    second_incorrect_true = len(df2[(df2['Virdict'] == 'TRUE') & (df2['Score'] == -32)])
    second_incorrect_false = len(df2[(df2['Virdict'] == 'FALSE') & (df2['Score'] == -16)])
    second_unknown = len(df2[(df2['Virdict'] == 'UNKNOWN') & (df2['Score'] == 0)])
    second_unknown_parsing = len(df2[(df2['Virdict'] == 'UNKNOWN (parsing)') & (df2['Score'] == 0)])
    second_unknown_frontend = len(df2[(df2['Virdict'] == 'UNKNOWN (frontend)') & (df2['Score'] == 0)])
    second_unknown_analysis = len(df2[(df2['Virdict'] == 'UNKNOWN (analysis)') & (df2['Score'] == 0)])
    second_timeout = len(df2[(df2['Virdict'] == 'TIMEOUT') & (df2['Score'] == 0)])
    
    positive_changes = 0
    total_score_increase = 0
    negative_changes = 0
    total_score_decrease = 0
    results = []
    for testcase in all_testcases:
        row1 = df1[df1['Test case'] == testcase]
        row2 = df2[df2['Test case'] == testcase]
        
        in_file1 = not row1.empty
        in_file2 = not row2.empty
        
        if in_file1 and in_file2:
            # Test case exists in both files
            old_verdict = row1.iloc[0]['Virdict']
            new_verdict = row2.iloc[0]['Virdict']
            old_score = row1.iloc[0]['Score']
            new_score = row2.iloc[0]['Score']
            
            if old_verdict == new_verdict:
                verdict_str = f"{old_verdict} (same)"
            else:
                verdict_str = f"{old_verdict} -> {new_verdict}"
            
            if old_score == new_score:
                score_str = f"{old_score} (same)"
            else:
                score_str = f"{old_score} -> {new_score}"
                if new_score > old_score:
                    total_score_increase += (new_score - old_score)
                    positive_changes += 1
                else:
                    total_score_decrease += (old_score - new_score)
                    negative_changes += 1
                
        elif in_file1 and not in_file2:
            # Test case only in first file (deleted)
            old_verdict = row1.iloc[0]['Virdict']
            old_score = row1.iloc[0]['Score']
            verdict_str = f"{old_verdict} (deleted)"
            score_str = f"{old_score} (deleted)"
            
        else:  # in_file2 and not in_file1
            # Test case only in second file (new)
            new_verdict = row2.iloc[0]['Virdict']
            new_score = row2.iloc[0]['Score']
            verdict_str = f"{new_verdict} (new)"
            score_str = f"{new_score} (new)"
        
        results.append({
            'Test case': testcase,
            'Virdict': verdict_str,
            'Score': score_str
        })
    
    # Create comparison dataframe
    comparison_df = pd.DataFrame(results)
    
    # Sort by test case
    comparison_df = comparison_df.sort_values('Test case').reset_index(drop=True)
    
    # Save to CSV
    comparison_df.to_csv(output, index=False)
    
    rich.print(f"Comparison saved to {output}")
    rich.print(f"[bold]Summary:[/bold]")
    rich.print(f"  First file ({file1}):")
    rich.print(f"    Total test cases: {first_testcases}")
    rich.print(f"    Total score: {first_total_score}")
    rich.print(f"    Correct results: {first_correct_true + first_correct_false}")
    rich.print(f"      Correct true (2 each): {first_correct_true}")
    rich.print(f"      Correct false (1 each): {first_correct_false}")
    rich.print(f"    Incorrect results: {first_incorrect_true + first_incorrect_false}")
    rich.print(f"      Incorrect true (-32 each): {first_incorrect_true}")
    rich.print(f"      Incorrect false (-16 each): {first_incorrect_false}")
    rich.print(f"    Inconclusive results (0 each): {first_unknown + first_unknown_parsing + first_unknown_frontend + first_unknown_analysis + first_timeout}")
    rich.print(f"      Unknown results: {first_unknown}")
    rich.print(f"      Failures: {first_unknown_parsing + first_unknown_frontend + first_unknown_analysis + first_timeout}")
    rich.print(f"        Parsing: {first_unknown_parsing}")
    rich.print(f"        Frontend: {first_unknown_frontend}")
    rich.print(f"        Analysis: {first_unknown_analysis}")
    rich.print(f"        Timeouts: {first_timeout}")
    rich.print(f"  Second file ({file2}):")
    rich.print(f"    Total test cases: {second_testcases}")
    rich.print(f"    Total score: {second_total_score}")
    rich.print(f"    Correct results: {second_correct_true + second_correct_false}")
    rich.print(f"      Correct true (2 each): {second_correct_true}")
    rich.print(f"      Correct false (1 each): {second_correct_false}")
    rich.print(f"    Incorrect results: {second_incorrect_true + second_incorrect_false}")
    rich.print(f"      Incorrect true (-32 each): {second_incorrect_true}")
    rich.print(f"      Incorrect false (-16 each): {second_incorrect_false}")
    rich.print(f"    Inconclusive results (0 each): {second_unknown + second_unknown_parsing + second_unknown_frontend + second_unknown_analysis + second_timeout}")
    rich.print(f"      Unknown results: {second_unknown}")
    rich.print(f"      Failures: {second_unknown_parsing + second_unknown_frontend + second_unknown_analysis + second_timeout}")
    rich.print(f"        Parsing: {second_unknown_parsing}")
    rich.print(f"        Frontend: {second_unknown_frontend}")
    rich.print(f"        Analysis: {second_unknown_analysis}")
    rich.print(f"        Timeouts: {second_timeout}")
    rich.print(f"[bold]Diff:[/bold]")
    rich.print(f"  Changed verdicts: {comparison_df['Virdict'].str.contains('->').sum()}")
    rich.print(f"  Changed scores: {comparison_df['Score'].str.contains('->').sum()}")
    rich.print(f"    Positive changes: [green]{positive_changes} (+{total_score_increase})[/green]")
    rich.print(f"    Negative changes: [red]{negative_changes} (-{total_score_decrease})[/red]")
    rich.print(f"  New test cases: {comparison_df['Virdict'].str.contains('new').sum()}")
    rich.print(f"  Deleted test cases: {comparison_df['Virdict'].str.contains('deleted').sum()}")
    
    return comparison_df
    

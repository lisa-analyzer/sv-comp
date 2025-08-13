import os
import pandas
import json

from pathlib import Path
from typing import Annotated
from typing_extensions import Optional
# Project-local imports
from cli.models.config import Config
from cli.commands.harvest import fetch_tasks
from cli.models.task_definition.task_definition import TaskDefinition

import rich
import typer

# CLI setup
cli = typer.Typer()
config = Config.get()


@cli.command()
def statistics():
    """
        Compute statics about LiSA analysis on SV-COMP
    """
    outdir = f"{str(config.path_to_output_dir)}/results"
    
    dataframe_parsing= None
    dataframe_frontend= None
    dataframe_analysis= None
    successfull_correct = 0
    successfull_wrong = 0
    error_parsing = 0
    error_frontend = 0
    error_analysis = 0
    test_cases = 0
    for dir in os.listdir(outdir):
        treated = False
        res_dir = f"{outdir}/{dir}"
        if(os.path.isdir(res_dir)):
            test_cases = test_cases+1
            for file in os.listdir(res_dir):
                if(file=="frontend.csv"):
                    temp = pandas.read_csv(os.path.join(res_dir, file), sep=";")[["Message", "Type"]].groupby(["Message"]).count()
                    dataframe_parsing = add_row(temp, dataframe_parsing, dir)
                    error_parsing = error_parsing + 1
                    treated = True
                if(file=="frontend-noparsing.csv"):
                    temp = pandas.read_csv(os.path.join(res_dir, file), sep=";")[["Message", "Type"]].groupby(["Message"]).count()
                    dataframe_frontend = add_row(temp, dataframe_frontend, dir)
                    error_frontend = error_frontend + 1
                    treated = True
                if(file=="analysis.csv"):
                    temp = pandas.read_csv(os.path.join(res_dir, file), sep=";")[["Message", "Type"]].groupby(["Message"]).count()
                    dataframe_analysis = add_row(temp, dataframe_analysis, dir)
                    error_analysis = error_analysis + 1
                    treated = True
            if(treated == False):
                with open(f"{res_dir}/report.json", encoding="utf-8") as f:
                    report = json.load(f)
                if(report["result"]):
                    successfull_correct = successfull_correct + 1
                else:
                    successfull_wrong = successfull_wrong + 1
    dataframe_parsing = dataframe_parsing.sort_values("Type", ascending=False)  
    dataframe_frontend = dataframe_frontend.sort_values("Type", ascending=False)  
    dataframe_analysis = dataframe_analysis.sort_values("Type", ascending=False)                
    dataframe_parsing.to_csv(f"{config.path_to_output_dir}/parsing.csv")
    dataframe_frontend.to_csv(f"{config.path_to_output_dir}/frontend.csv")
    dataframe_analysis.to_csv(f"{config.path_to_output_dir}/analysis.csv")

    rich.print(f"Number of test cases: [bold blue]{test_cases}[/bold blue]")
    rich.print(f"Successfull analyses with the expected result: [bold green]{successfull_correct}[/bold green]")
    rich.print(f"Successfull analyses with not the expected result: [bold yellow]{successfull_wrong}[/bold yellow]")
    rich.print(f"Parsing errors (dumped to parsing.csv): [bold red]{error_parsing}[/bold red]")
    rich.print(f"Frontend errors (dumped to frontend.csv): [bold red]{error_frontend}[/bold red]")
    rich.print(f"Analysis errors (dumped to analysis.csv): [bold red]{error_analysis}[/bold red]")


def add_row(temp, dataframe, test_case):
    temp["Test_cases"] = str(test_case)+"\n"
    if dataframe is None:
        dataframe = temp
    else :
        merge = pandas.merge(dataframe, temp, left_index=True, right_index=True, how = "outer")
        merge["Test_cases_x"] = merge["Test_cases_x"].fillna("")
        merge["Test_cases_y"] = merge["Test_cases_y"].fillna("")
        merge = merge.fillna(0)
        merge["Type"] = merge["Type_x"]+merge["Type_y"]
        merge["Test_cases"] = merge["Test_cases_x"].astype(str)+merge["Test_cases_y"].astype(str)
        dataframe = merge[["Type", "Test_cases"]]
    return dataframe
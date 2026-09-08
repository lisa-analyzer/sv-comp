from enum import Enum


class AnalysisLanguage(str, Enum):
    """
    Represents the 'analysis_language' field in CLI's config file.
    """
    JAVA = "java"
    PYTHON = "python"
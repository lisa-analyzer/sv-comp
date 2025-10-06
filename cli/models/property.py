from enum import Enum


class Property(Enum):
    """
    Represents an enumeration of properties of interest that are accepted and passed to LiSA
    """
    
    ASSERT = "assert"
    RUNTIME = "runtime"

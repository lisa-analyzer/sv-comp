from enum import Enum


class Property(Enum):
    """
    Represents an enumeration of properties of interest that are accepted and passed to LiSA
    """
    
    ASSERT = "assert"
    RUNTIME = "runtime"


# the names of the properties in SV-COMP, which are also the names of the folders where jlisa writes their
# violation witnesses, inside outputs/witness/
SVCOMP_NAMES = {Property.ASSERT: "valid-assert", Property.RUNTIME: "no-runtime-exception"}

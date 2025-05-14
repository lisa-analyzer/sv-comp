# Standard library imports
import os
import sys

def load_packages():
    """
        Loads vendored project dependencies and makes them available in the.py file
    """

    parent_dir = os.path.abspath(os.path.dirname(__file__))
    vendor_dir = os.path.join(parent_dir, f"../vendor/lib/python{sys.version_info.major}.{sys.version_info.minor}/site-packages")
    vendor_dir = os.path.normpath(vendor_dir)

    if os.path.exists(vendor_dir):
        sys.path.insert(0, vendor_dir)

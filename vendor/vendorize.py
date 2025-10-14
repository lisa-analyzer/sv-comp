# Standard library imports
import sys
import shutil
import subprocess
from pathlib import Path

def vendorize() -> None:
    """
        Install dependencies from requirements.txt into vendor/lib/pythonX.Y/site-packages.
    """
    project_root = Path(__file__).resolve().parents[1]
    requirements = project_root / "requirements.txt"

    if not requirements.exists():
        print("Requirements.txt not found.")
        sys.exit(1)

    #version = f"python{sys.version_info.major}.{sys.version_info.minor}"
    target = project_root / "vendor" / "lib" / "site-packages"

    if target.exists():
        print(f"Removing existing vendor folder: {target}")
        shutil.rmtree(target)

    target.mkdir(parents=True, exist_ok=True)

    print(f"Installing packages to: {target}")
    subprocess.run([
        sys.executable, "-m", "pip", "install",
        "-r", str(requirements),
        "--target", str(target)
    ], check=True)

    print("Vendoring complete.")

if __name__ == "__main__":
    vendorize()
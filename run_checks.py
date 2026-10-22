"""Run scientific and app-state checks directly from VSCode (requires pytest)."""
from pathlib import Path
import subprocess
import sys


if __name__ == "__main__":
    raise SystemExit(subprocess.call([sys.executable,"-m","pytest","tests","-q"],
                                    cwd=Path(__file__).resolve().parent))

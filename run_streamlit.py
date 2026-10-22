"""Select the gift_streamlit environment, then run this file in VSCode."""
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parent
PORT = 8501  # Change if another local app already uses this port.


def main():
    command = [sys.executable, "-m", "streamlit", "run", str(ROOT / "app.py"),
               f"--server.port={PORT}", "--server.address=127.0.0.1", "--server.headless=false"]
    print(f"Opening GIFT Habitat Explorer at http://localhost:{PORT}")
    print("Stop this terminal with Ctrl+C to close the local server.")
    try:
        subprocess.run(command, cwd=ROOT, check=True)
    except KeyboardInterrupt:
        pass
    except subprocess.CalledProcessError as exc:
        raise SystemExit(exc.returncode) from exc


if __name__ == "__main__":
    main()

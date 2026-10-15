"""Optional Windows launcher.

For the initial development stage, run the application with:
    streamlit run app.py

A dedicated Windows launcher can be implemented after the app structure is stable.
"""
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parent

def main():
    subprocess.run(
        [sys.executable, "-m", "streamlit", "run", str(ROOT / "app.py")],
        cwd=str(ROOT),
        check=False,
    )

if __name__ == "__main__":
    main()

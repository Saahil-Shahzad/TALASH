from pathlib import Path
import subprocess
import sys


def process_all_subfolders(root_folder: str) -> None:
    root = Path(root_folder)
    if not root.exists() or not root.is_dir():
        raise ValueError(f"Invalid root folder: {root_folder}")

    run_script = Path(__file__).resolve().parent / "run_pipeline.py"
    for child in sorted(root.iterdir()):
        if child.is_dir():
            print(f"\n>>> Processing folder: {child}")
            subprocess.run([sys.executable, str(run_script), str(child)], check=False)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Batch process multiple CV folders.")
    parser.add_argument("root", help="Root folder containing subfolders of CV PDFs")
    args = parser.parse_args()
    process_all_subfolders(args.root)

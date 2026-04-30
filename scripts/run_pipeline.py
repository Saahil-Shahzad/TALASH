import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT))

from backend.app.db.mongo import get_db
from backend.app.services.parser_service import ParserService


def main() -> None:
    parser = argparse.ArgumentParser(description="Run TALASH Milestone 1 preprocessing pipeline.")
    parser.add_argument("folder", help="Path to folder containing CV PDFs")
    parser.add_argument("--overwrite", action="store_true", help="Overwrite existing candidates")
    args = parser.parse_args()

    db = get_db()
    service = ParserService(db)
    result = service.process_folder(args.folder, overwrite_existing=args.overwrite)

    print("=== TALASH Pipeline Result ===")
    print(f"Processed: {result['processed_count']}")
    print(f"Skipped:   {result['skipped_count']}")
    print(f"Failed:    {result['failed_count']}")
    print(f"CSV:       {result['export_csv']}")
    print(f"Excel:     {result['export_xlsx']}")
    export_tables = result.get("export_tables") or {}
    if export_tables:
        print("Tables:")
        for name, path in export_tables.items():
            print(f"- {name}: {path}")
    print("Files:")
    for item in result["files"]:
        print(f"- {item}")


if __name__ == "__main__":
    main()

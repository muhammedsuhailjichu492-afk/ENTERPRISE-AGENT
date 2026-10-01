
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.database import init_db, seed_sample_data
from app import vector_store


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--force", action="store_true", help="Wipe and reseed business data tables.")
    args = parser.parse_args()

    print("Initializing schema...")
    init_db()

    print("Seeding sample enterprise data...")
    seed_sample_data(force=args.force)

    print("Seeding vector store (knowledge base)...")
    vector_store.seed_if_empty()

    print("Done. Run the API with: uvicorn app.main:app --reload")


if __name__ == "__main__":
    main()

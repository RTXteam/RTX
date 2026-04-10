#!/usr/bin/env python3
"""
Extract the first N distinct concept names from the staging table,
strip whitespace, and save to a text file (one name per line).

Usage:
    python extract_sample_names.py [--sample-size 1000] [--db-path PATH] [--output PATH]
"""
import argparse
import os
import sqlite3
import sys

NGD_DIR = os.path.dirname(os.path.abspath(__file__))


def main():
    parser = argparse.ArgumentParser(description="Extract sample names from staging table")
    parser.add_argument("--sample-size", type=int, default=1000)
    parser.add_argument(
        "--db-path", type=str,
        default=os.path.join(NGD_DIR, "conceptname_to_pmids.sqlite"),
    )
    parser.add_argument(
        "--output", type=str,
        default=os.path.join(NGD_DIR, "sample_names.txt"),
    )
    args = parser.parse_args()

    if not os.path.exists(args.db_path):
        print(f"ERROR: Database not found at {args.db_path}")
        sys.exit(1)

    conn = sqlite3.connect(args.db_path)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT DISTINCT concept_name FROM staging LIMIT ?",
        (args.sample_size,)
    )
    raw_names = [row[0] for row in cursor.fetchall()]
    conn.close()

    # Clean and drop empties
    names = [n.strip() for n in raw_names if n and n.strip()]

    with open(args.output, "w") as f:
        for name in names:
            f.write(name + "\n")

    print(f"Wrote {len(names)} cleaned names to {args.output}")


if __name__ == "__main__":
    main()

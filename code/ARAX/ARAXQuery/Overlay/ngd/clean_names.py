#!/usr/bin/env python3
"""
Cleans sample_names.txt by stripping leading/trailing punctuation,
quotes, and whitespace from each name. Drops empty lines and duplicates.

Usage:
    python clean_names.py [--input PATH] [--output PATH]
"""
import argparse
import os
import re

NGD_DIR = os.path.dirname(os.path.abspath(__file__))


def clean_name(name: str) -> str:
    # Remove all characters except alphanumeric, spaces, hyphens,
    # parentheses, and commas
    name = re.sub(r'[^a-zA-Z0-9\s\-(),]', '', name)
    # Collapse multiple spaces
    name = re.sub(r'\s+', ' ', name)
    return name.strip()


def main():
    parser = argparse.ArgumentParser(description="Clean sample names file")
    parser.add_argument("--input", default=os.path.join(NGD_DIR, "sample_names.txt"))
    parser.add_argument("--output", default=os.path.join(NGD_DIR, "sample_names.txt"))
    args = parser.parse_args()

    with open(args.input) as f:
        raw = [line.rstrip("\n") for line in f]

    seen = set()
    cleaned = []
    for line in raw:
        name = clean_name(line)
        # Skip empty, too short, or names with no letters
        if not name or len(name) < 3 or not re.search(r'[a-zA-Z]', name):
            continue
        if name not in seen:
            seen.add(name)
            cleaned.append(name)

    with open(args.output, "w") as f:
        for name in cleaned:
            f.write(name + "\n")

    print(f"Read {len(raw)} lines, wrote {len(cleaned)} cleaned unique names to {args.output}")


if __name__ == "__main__":
    main()

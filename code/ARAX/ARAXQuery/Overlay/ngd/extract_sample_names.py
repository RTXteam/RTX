#!/usr/bin/env python3
"""
Extract sample concept names from the staging table, clean them,
and print before/after for review.

Usage:
    python extract_sample_names.py [--sample-size 50] [--db-path PATH]
"""
import argparse
import html
import os
import re
import sqlite3
import sys
import unicodedata
import urllib.parse

NGD_DIR = os.path.dirname(os.path.abspath(__file__))


def _greek_replacer(match: re.Match) -> str:
    ch = match.group(0)
    try:
        name = unicodedata.name(ch)
    except ValueError:
        return ch
    if name.startswith('GREEK SMALL LETTER '):
        return name[len('GREEK SMALL LETTER '):].split()[0].lower()
    if name.startswith('GREEK CAPITAL LETTER '):
        return name[len('GREEK CAPITAL LETTER '):].split()[0].capitalize()
    return ch


_GREEK_LETTER_RE = re.compile(r'[\u0370-\u03ff\u1f00-\u1fff]')


def clean_name(name: str) -> str:
    """Clean a concept name while preserving meaningful punctuation."""
    s = name.strip()

    # Decode HTML entities (e.g. &amp;, &#x06FC0;, &agr;)
    s = html.unescape(s)

    # Decode URL percent-encoding (e.g. '%20Type%202' -> ' Type 2').
    # unquote leaves unrelated '%' alone, so a standalone '% α-helicity'
    # stays intact and the leading '%' is stripped below.
    try:
        s = urllib.parse.unquote(s, errors='strict')
    except (UnicodeDecodeError, ValueError):
        pass
    s = s.strip()

    # Strip HTML/XML artifacts: leading ">
    s = re.sub(r'^["\']*>', '', s)

    # Strip mid-string HTML attribute artifacts like '">' or "'>",
    # which appear when scraping HTML (e.g. '...%202">Diabetes Mellitus').
    s = re.sub(r'["\']>', ' ', s)

    # Repair malformed HTML numeric character references where the '&' and/or
    # trailing ';' were lost in scraping, e.g. '#x003B2' -> 'β', '#x00A0' -> nbsp.
    # Must run before the leading '#' strip below so we don't lose the anchor.
    def _repair_entity(m: re.Match) -> str:
        return html.unescape(f'&#{m.group(1)};')
    s = re.sub(r'#(x[0-9A-Fa-f]+|[0-9]+);?', _repair_entity, s)

    # Strip any leading '#' or '%' (e.g. hashtags) — never allowed up front
    s = re.sub(r'^[#%]+\s*', '', s)

    # Replace Greek letters with their English names, so that scientific
    # names like 'α-helicity' become 'alpha-helicity' and 'Ω incision'
    # becomes 'Omega incision'.
    s = _GREEK_LETTER_RE.sub(_greek_replacer, s)

    # Replace double quotes (ASCII + curly/smart) with a space so that
    # adjacent words don't get smashed together, e.g.
    #   '"Anti-energy"coefficient' -> 'Anti-energy coefficient'
    # Whitespace is collapsed below.
    s = re.sub(r'[\u0022\u201c\u201d\u201e\u201f\u2033\u2036]', ' ', s)

    # Strip leading/trailing commas, semicolons, colons, periods
    s = re.sub(r'^[,;:.]+', '', s)
    s = re.sub(r'[,;:.]+$', '', s)

    s = s.strip()

    # Strip unmatched trailing/leading parens and brackets
    for _ in range(3):
        if s.endswith(')') and s.count(')') > s.count('('):
            s = s[:-1].rstrip()
        if s.startswith('(') and s.count('(') > s.count(')'):
            s = s[1:].lstrip()
        if s.endswith(']') and s.count(']') > s.count('['):
            s = s[:-1].rstrip()
        if s.startswith('[') and s.count('[') > s.count(']'):
            s = s[1:].lstrip()

    # Strip trailing hyphens (incomplete names)
    s = re.sub(r'-+$', '', s).rstrip()

    # Replace unicode arrows with ASCII ->
    s = s.replace('\u2192', '->').replace('\u2190', '<-')

    # Replace other common unicode oddities with ASCII
    s = re.sub(r'[\u2009\u200a\u00a0]', ' ', s)  # thin/hair/nbsp -> space

    # Collapse multiple spaces
    s = re.sub(r'\s+', ' ', s)

    return s.strip()


_LATEX_MARKERS = re.compile(r'[$\\]|\$\$|\^\{|_\{')


def looks_like_latex(s: str) -> bool:
    """Return True for strings containing LaTeX/math markup dregs.
    Concept names with '$', backslash commands, or math subscripts like
    '^{...}' / '_{...}' are poorly cleanable and should be discarded.
    """
    return bool(_LATEX_MARKERS.search(s))


def is_english(s: str) -> bool:
    """Return True if the string contains only Latin/Greek letters (plus
    digits, punctuation, symbols). Strings containing letters from other
    scripts (CJK, Cyrillic, Arabic, Hebrew, Devanagari, Hangul, Thai, ...)
    are considered non-English and discarded by the caller.

    Greek is permitted because Greek letters are routinely used inline in
    English scientific writing (e.g. 'Ω incision', 'α-synuclein').
    """
    has_latin = False
    for ch in s:
        if not ch.isalpha():
            continue
        try:
            name = unicodedata.name(ch)
        except ValueError:
            return False
        if name.startswith('LATIN'):
            has_latin = True
        elif name.startswith('GREEK'):
            continue
        else:
            return False
    return has_latin


def main():
    parser = argparse.ArgumentParser(description="Extract and clean sample names")
    parser.add_argument("--sample-size", type=int, default=50)
    parser.add_argument(
        "--db-path", type=str,
        default=os.path.join(NGD_DIR, "conceptname_to_pmids.sqlite"),
    )
    args = parser.parse_args()

    if not os.path.exists(args.db_path):
        print(f"ERROR: Database not found at {args.db_path}")
        sys.exit(1)

    conn = sqlite3.connect(args.db_path)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT DISTINCT concept_name FROM conceptname_to_pmids LIMIT ?",
        (args.sample_size,)
    )
    raw_names = [row[0] for row in cursor.fetchall()]
    conn.close()

    seen = set()
    kept = []
    dropped_empty = 0
    dropped_dupe = 0
    dropped_nonenglish = 0
    dropped_latex = 0

    for raw in raw_names:
        cleaned = clean_name(raw)

        if not cleaned:
            print(f"  EMPTY:  {raw.strip()!r} -> dropped")
            dropped_empty += 1
            continue

        if looks_like_latex(cleaned):
            print(f"  LATEX:  {raw.strip()!r} -> {cleaned!r} (LaTeX/math, dropped)")
            dropped_latex += 1
            continue

        if not is_english(cleaned):
            print(f"  NONEN:  {raw.strip()!r} -> {cleaned!r} (non-English, dropped)")
            dropped_nonenglish += 1
            continue

        if cleaned in seen:
            print(f"  DUPE:   {raw.strip()!r} -> {cleaned!r} (already seen)")
            dropped_dupe += 1
            continue

        seen.add(cleaned)
        kept.append(cleaned)

        if raw.strip() != cleaned:
            print(f"  BEFORE: {raw.strip()!r}")
            print(f"  AFTER:  {cleaned!r}")
            print()
        else:
            print(f"  OK:     {raw.strip()!r}")

    output = os.path.join(NGD_DIR, "sample_names.txt")
    with open(output, "w") as f:
        for name in kept:
            f.write(name + "\n")

    print(
        f"\n{len(kept)} kept, {dropped_empty} empty, "
        f"{dropped_dupe} duplicates, {dropped_nonenglish} non-English, "
        f"{dropped_latex} LaTeX/math"
    )
    print(f"Wrote to {output}")


if __name__ == "__main__":
    main()

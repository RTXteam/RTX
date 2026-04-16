#!/usr/bin/env python3

import html
import re
import urllib.parse

# -------------------------
# Regex
# -------------------------
MESH_TAG_RE = re.compile(r'\[\s*(mesh|mesh term)[^\]]*\]', re.IGNORECASE)

UNICODE_DASHES_RE = re.compile(r'[\u2010-\u2015\u2212]')
QUOTES_RE = re.compile(r'[\u0022\u201c\u201d\u201e\u201f\u2033\u2036]')
APOSTROPHE_RE = re.compile(r'[\u2018\u2019\u201a\u201b\u2032\u2035]')
WHITESPACE_RE = re.compile(r'\s+')

LEADING_JUNK_RE = re.compile(r'^[#%"\'>\s\-\+\)\(]+')
TRAILING_JUNK_RE = re.compile(r'[\s,;:.]+$')

NON_ASCII_RE = re.compile(r'[^\x00-\x7F]')
LATEX_RE = re.compile(r'[$\\]|\^\{|_\{')
MARKUP_RE = re.compile(r'[<&]')
PROSE_RE = re.compile(r'\.\s+[A-Z]')
HASHTAG_RE = re.compile(r'(?:^|\s)#\w')
BOOLEAN_RE = re.compile(r'\b(AND|OR|NOT)\b', re.IGNORECASE)


# Sentence-y junk that almost never appears in MeSH descriptors but does
# appear in author-supplied keywords. Words that are part of legitimate MeSH
# (model, mice, rats, study, analysis, design, induced, method, technique,
# procedure, approach, protocol) were removed -- they were rejecting valid
# concepts like "mouse model", "meta-analysis", "induced pluripotent stem
# cells", "principal component analysis".
EXPERIMENT_RE = re.compile(
    r'\b(experimental design|study design|case[- ]control study)\b',
    re.IGNORECASE
)

MEASUREMENT_RE = re.compile(
    r'\b(per gram|dose per|body fat|energy percent|mg/ml|g/kg|id/g|v/v)\b',
    re.IGNORECASE
)

METHOD_RE = re.compile(
    r'\b(strategy)\b',
    re.IGNORECASE
)

PHYSICS_CODE_RE = re.compile(r'^\(?\d{3}\.\d{4}\)')
NUMERIC_PREFIX_RE = re.compile(r'^\d+\s+[A-Za-z]')
# Require a longer lowercase prefix so biological short prefixes like
# m/c/si/ds/ss/sn/mi/pre + RNA|DNA pass through (mRNA, cDNA, siRNA, dsDNA).
CAMEL_RE = re.compile(r'[a-z]{3,}[A-Z]{2,}')
# Allow short gene/protein names like p53, p21, c-Myc-style stems.
SHORT_GENE_RE = re.compile(r'^[a-zA-Z]{1,3}\d{1,4}$')
SOCIAL_RE = re.compile(r'(twitter|instagram|challenge|mask|pets|ivory|foam|hashtag)', re.IGNORECASE)

TRAILING_META_RE = re.compile(
    r'(?:\s*\((?:[A-Za-z][A-Za-z0-9 /._-]*:\s*[^()]*'
    r'|(?:PubChem\s*CID|CAS|CID|InChIKey|SMILES|DrugBank|ChEBI|KEGG|HMDB)[^()]*)\))+\s*$',
    re.IGNORECASE,
)

INLINE_META_RE = re.compile(
    r'\b(PubChem\s*CID|CAS|CID|InChIKey|SMILES|DrugBank|ChEBI|KEGG|HMDB)\b.*',
    re.IGNORECASE,
)

ISOTOPE_RE = re.compile(r'\((\d+)\)\s*([A-Z])')

# -------------------------
# Greek map
# -------------------------
GREEK_MAP = {
    'α': 'alpha', 'β': 'beta', 'γ': 'gamma', 'δ': 'delta',
    'ε': 'epsilon', 'θ': 'theta', 'λ': 'lambda', 'μ': 'mu',
    'π': 'pi', 'σ': 'sigma', 'τ': 'tau', 'φ': 'phi',
    'ω': 'omega', 'Ω': 'Omega', 'Δ': 'Delta'
}

def replace_greek(s):
    return ''.join(GREEK_MAP.get(c, c) for c in s)

# -------------------------
# Cleaning
# -------------------------
def clean_name(s):
    s = s.strip()

    s = re.sub(r'([A-Za-z])\s+(\d+[A-Za-z])', r'\1\2', s)
    s = re.sub(r'\s*->\s*', '->', s)
    s = re.sub(r'\s*-\s*', '-', s)

    s = re.sub(r"(\w)'\s+(\w)", r"\1 \2", s)
    s = re.sub(r"'\b", '', s)

    s = MESH_TAG_RE.sub('', s)

    s = html.unescape(s)
    try:
        s = urllib.parse.unquote(s)
    except Exception:
        pass

    s = UNICODE_DASHES_RE.sub('-', s)
    s = QUOTES_RE.sub(' ', s)
    s = APOSTROPHE_RE.sub("'", s)

    s = replace_greek(s)

    s = ISOTOPE_RE.sub(r'\1\2', s)

    s = re.sub(r'(\d)([a-z])', r'\1 \2', s)

    s = LEADING_JUNK_RE.sub('', s)

    s = INLINE_META_RE.sub('', s)

    for _ in range(2):
        new_s = TRAILING_META_RE.sub('', s).rstrip()
        if new_s == s:
            break
        s = new_s

    s = s.replace('\u2192', '->').replace('\u2190', '<-')
    s = s.replace('\u00a0', ' ')

    s = WHITESPACE_RE.sub(' ', s)
    s = TRAILING_JUNK_RE.sub('', s)
    s = re.sub(r'^[^A-Za-z0-9]+', '', s)

    # safe bracket cleanup
    for _ in range(2):
        if s.endswith(')') and s.count(')') > s.count('('):
            s = s[:-1].rstrip()
        if s.startswith('(') and s.count('(') > s.count(')'):
            s = s[1:].lstrip()
        if s.endswith(']') and s.count(']') > s.count('['):
            s = s[:-1].rstrip()
        if s.startswith('[') and s.count('[') > s.count(']'):
            s = s[1:].lstrip()

    return s.strip()

# -------------------------
# Validation
# -------------------------
GENERIC_TERMS = {
    "healthy diet", "one body", "results", "study", "patients"
}

def is_valid(s):
    # allow isotopes early
    if re.match(r'\(?\d+[A-Za-z]{1,2}\)?', s):
        return True

    if re.match(r'\d+[pq]\d', s):
        return True

    if re.match(r'^\(?[RSZErsze]\)?-', s):
        return True

    # allow biomedical abbreviations
    if re.fullmatch(r'[A-Z0-9\-]{2,10}', s):
        return True

    # allow short gene/protein names like p53, p21
    if SHORT_GENE_RE.match(s):
        return True

    if re.search(r'\b(rRNA|DNA|RNA|kDa)\b', s):
        return True

    if len(s) < 4 or len(s) > 120:
        return False

    if re.fullmatch(r'x[0-9A-Fa-f]+', s):
        return False

    if re.search(r'\d+\+\d+', s):
        return False

    if EXPERIMENT_RE.search(s):
        return False

    if not any(c.isalpha() for c in s):
        return False

    # relaxed parentheses rule
    if abs(s.count('(') - s.count(')')) > 1:
        return False

    if PHYSICS_CODE_RE.match(s):
        return False

    if LATEX_RE.search(s):
        return False

    if MARKUP_RE.search(s):
        return False

    if '=' in s or '{' in s or '}' in s or HASHTAG_RE.search(s):
        return False

    if BOOLEAN_RE.search(s):
        return False

    if PROSE_RE.search(s):
        return False

    if MEASUREMENT_RE.search(s):
        return False

    if METHOD_RE.search(s):
        return False

    if NUMERIC_PREFIX_RE.match(s) and not re.search(r'\b[A-Za-z]{3,}\b', s):
        return False

    if CAMEL_RE.search(s) or SOCIAL_RE.search(s):
        return False

    if len(s.split()) > 12:
        return False

    if s.lower() in GENERIC_TERMS:
        return False

    return True

# -------------------------
# Canonical form
# -------------------------
def canonicalize(s):
    return re.sub(r'[^a-z0-9]', '', s.lower())

# -------------------------
# Main
# -------------------------
def process_names(raw_names):
    seen = set()
    cleaned_names = []

    for raw in raw_names:
        if not raw:
            continue

        cleaned = clean_name(raw)

        if not cleaned or not is_valid(cleaned):
            continue

        key = canonicalize(cleaned)

        if key in seen:
            continue

        seen.add(key)
        cleaned_names.append(cleaned)

    return cleaned_names

#!/usr/bin/env bash
set -euo pipefail
# Purpose: sets up symbolic links for ARAX database files
# The databases and their file names are read from RTX/code/config_dbs.json
# (the source of truth), so this script does not need editing when a
# database version changes there.
# Usage: it's a three-step process
#   1. configure the `DB_DIR` shell variable below (or export it); it must
#      hold the databases laid out as on arax-databases.rtx.ai, e.g.
#      ${DB_DIR}/tier0-20260621/curie_ngd_v1.1_tier0-20260621.sqlite
#   2. `cd` to the directory just above the `RTX` root code directory
#   3. `RTX/code/generate-db-symlinks.sh`
# `LATEST_TIER0_VER` defaults to the tier0 version of `tier0_sqlite` in
# config_dbs.json. Set it to link a different tier0 build; databases that
# config_dbs.json keeps in another directory (e.g. fda_approved_drugs) are
# not affected by it.
# The pytest suite only runs the database manager if you pass
# `--withdatabases`, so by default it won't attempt to download 200 GiB
# worth of databases to your development machine.

# Stephen Ramsey, Oregon State University

DB_DIR="${DB_DIR:-/mnt/data/orangeboard/databases}"

CONFIG_DBS="RTX/code/config_dbs.json"

if [[ ! -d "RTX" ]]; then
  echo "ERROR: Expected to find directory 'RTX' in the current working directory: $(pwd)" >&2
  echo "       Run this script from the directory one level above RTX." >&2
  exit 1
fi

# One "key<TAB>dir<TAB>file" line per entry under database_downloads, e.g.
#   curie_ngd	tier0-20260621	curie_ngd_v1.1_tier0-20260621.sqlite
db_entries="$(python3 -c '
import json, sys
with open(sys.argv[1]) as f:
    downloads = json.load(f)["database_downloads"]
for key, path in downloads.items():
    print("\t".join([key] + path.split("/")[-2:]))
' "$CONFIG_DBS")"

config_tier0_ver="$(awk -F'\t' '$1 == "tier0_sqlite" {print $2}' <<< "$db_entries")"
if [[ -z "$config_tier0_ver" ]]; then
  echo "ERROR: No database_downloads.tier0_sqlite entry in $CONFIG_DBS" >&2
  exit 1
fi
LATEST_TIER0_VER="${LATEST_TIER0_VER:-$config_tier0_ver}"

# Where each database goes in the RTX tree. Must match `local_paths` in
# ARAX_database_manager.py (and the Tier0 dir that ARAX_decorator.py reads).
dest_dir_for() {
  case "$1" in
    cohd_database)            echo "RTX/code/ARAX/KnowledgeSources/COHD_local/data" ;;
    curie_to_pmids|curie_ngd) echo "RTX/code/ARAX/KnowledgeSources/NormalizedGoogleDistance" ;;
    kg2c_sqlite)              echo "RTX/code/ARAX/KnowledgeSources/KG2c" ;;
    tier0_sqlite)             echo "RTX/code/ARAX/KnowledgeSources/Tier0" ;;
    fda_approved_drugs)       echo "RTX/code/ARAX/KnowledgeSources" ;;
    autocomplete)             echo "RTX/code/autocomplete" ;;
    explainable_dtd_db)       echo "RTX/code/ARAX/KnowledgeSources/Prediction" ;;
    *)                        return 1 ;;
  esac
}

# Fail before creating any links if config_dbs.json has a database this
# script does not know where to put.
while IFS=$'\t' read -r key _ _; do
  if ! dest_dir_for "$key" > /dev/null; then
    echo "ERROR: $CONFIG_DBS has database '$key' but $0 has no destination for it." >&2
    echo "       Add it to dest_dir_for(), matching ARAX_database_manager.py." >&2
    exit 1
  fi
done <<< "$db_entries"

link() {
  local src="$1"
  local dest="$2"

  if [[ ! -e "$src" ]]; then
    echo "ERROR: Source does not exist: $src" >&2
    exit 1
  fi

  # Safety: refuse to overwrite a non-symlink destination (file or directory).
  # Allow replacing an existing symlink (including a broken symlink).
  if [[ -e "$dest" && ! -L "$dest" ]]; then
    echo "ERROR: Refusing to overwrite existing non-symlink path: $dest" >&2
    echo "       (Move it aside or delete it, then re-run.)" >&2
    exit 1
  fi

  mkdir -p "$(dirname "$dest")"
  ln -sfn "$src" "$dest"
}

while IFS=$'\t' read -r key dir file; do
  if [[ "$dir" == "$config_tier0_ver" ]]; then
    dir="$LATEST_TIER0_VER"
    file="${file//$config_tier0_ver/$LATEST_TIER0_VER}"
  fi
  link "${DB_DIR}/${dir}/${file}" "$(dest_dir_for "$key")/${file}"
done <<< "$db_entries"

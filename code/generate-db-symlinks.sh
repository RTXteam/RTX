#!/usr/bin/env bash
set -euo pipefail
# Purpose: sets up symbolic links for ARAX database files
# Usage: it's a three-step process
#   1. configure `DB_DIR` and `LATEST_KG2_VER` shell variabless
#   2. `cd` to the directory just above the `RTX` root code directory
#   3. `./generate-db-symlinks.sy`
# When you run the pytest suite, don't forget to pass `--nodatabases`
# so that the database manager won't attempt to download 200 GiB worth
# of databases to your development machine.

# Stephen Ramsey, Oregon State University

LATEST_TIER0_VER="tier0-20260408"
DB_DIR="/Users/sramsey/Work/big-files/arax-dbs"

if [[ ! -d "RTX" ]]; then
  echo "ERROR: Expected to find directory 'RTX' in the current working directory: $(pwd)" >&2
  echo "       Run this script from the directory one level above RTX." >&2
  exit 1
fi

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

link "${DB_DIR}/${LATEST_TIER0_VER}/COHDdatabase_v1.0_${LATEST_TIER0_VER}.db" "RTX/code/ARAX/KnowledgeSources/COHD_local/data/COHDdatabase_v1.0_${LATEST_TIER0_VER}.db"

# commented out pending readiness of new xCRG code in: https://github.com/Translator-CATRAX/shepherd/issues
#link "${DB_DIR}/KG2.10.0/xcrg_decrease_model_v1.0.KG2.10.0_new_version.pt" "RTX/code/ARAX/ARAXQuery/Infer/data/xCRG_data/xcrg_decrease_model_v1.0.KG2.10.0_new_version.pt"
#link "${DB_DIR}/KG2.10.0/xcrg_increase_model_v1.0.KG2.10.0_new_version.pt" "RTX/code/ARAX/ARAXQuery/Infer/data/xCRG_data/xcrg_increase_model_v1.0.KG2.10.0_new_version.pt"
#link "${DB_DIR}/${LATEST_TIER0_VER}/chemical_gene_embeddings_v1.0.KG2.10.0_refreshedTo_${LATEST_TIER0_VER}.npz" "RTX/code/ARAX/ARAXQuery/Infer/data/xCRG_data/chemical_gene_embeddings_v1.0.KG2.10.0_refreshedTo_${LATEST_TIER0_VER}.npz"

link "${DB_DIR}/${LATEST_TIER0_VER}/ExplainableDTD_${LATEST_TIER0_VER}.db" "RTX/code/ARAX/KnowledgeSources/Prediction/ExplainableDTD_${LATEST_TIER0_VER}.db"

# commented out pending resolution of ARAX issue 2732
#link "${DB_DIR}/${LATEST_TIER0_VER}/curie_ngd_v1.0_${LATEST_TIER0_VER}.sqlite" "RTX/code/ARAX/KnowledgeSources/NormalizedGoogleDistance/curie_ngd_v1.0_${LATEST_TIER0_VER}.sqlite"

link "${DB_DIR}/${LATEST_TIER0_VER}/curie_to_pmids_v1.0_${LATEST_TIER0_VER}.sqlite" "RTX/code/ARAX/KnowledgeSources/NormalizedGoogleDistance/curie_to_pmids_v1.0_${LATEST_TIER0_VER}.sqlite"
link "${DB_DIR}/${LATEST_TIER0_VER}/fda_approved_drugs_v1.0.pickle" "RTX/code/ARAX/KnowledgeSources/fda_approved_drugs_v1.0.pickle"
link "${DB_DIR}/${LATEST_TIER0_VER}/tier0-info-for-overlay_v1.0_${LATEST_TIER0_VER}.sqlite" "RTX/code/ARAX/KnowledgeSources/KG2c/tier0-info-for-overlay_v1.0_${LATEST_TIER0_VER}.sqlite"
link "${DB_DIR}/${LATEST_TIER0_VER}/autocomplete_v1.0_${LATEST_TIER0_VER}.sqlite" "RTX/code/autocomplete/autocomplete_v1.0_${LATEST_TIER0_VER}.sqlite"


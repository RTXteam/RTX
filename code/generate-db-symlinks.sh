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

LATEST_KG2_VER="KG2.10.2"
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

link "${DB_DIR}/KG2.8.0/COHDdatabase_v1.0_KG2.8.0.db" "RTX/code/ARAX/KnowledgeSources/COHD_local/data/COHDdatabase_v1.0_KG2.8.0.db"
link "${DB_DIR}/KG2.10.0/xcrg_decrease_model_v1.0.KG2.10.0_new_version.pt" "RTX/code/ARAX/ARAXQuery/Infer/data/xCRG_data/xcrg_decrease_model_v1.0.KG2.10.0_new_version.pt"
link "${DB_DIR}/KG2.10.0/xcrg_increase_model_v1.0.KG2.10.0_new_version.pt" "RTX/code/ARAX/ARAXQuery/Infer/data/xCRG_data/xcrg_increase_model_v1.0.KG2.10.0_new_version.pt"
link "${DB_DIR}/${LATEST_KG2_VER}/chemical_gene_embeddings_v1.0.KG2.10.0_refreshedTo_${LATEST_KG2_VER}.npz" "RTX/code/ARAX/ARAXQuery/Infer/data/xCRG_data/chemical_gene_embeddings_v1.0.KG2.10.0_refreshedTo_${LATEST_KG2_VER}.npz"
link "${DB_DIR}/${LATEST_KG2_VER}/ExplainableDTD_v1.0_KG2.10.0_refreshedTo_${LATEST_KG2_VER}.db" "RTX/code/ARAX/KnowledgeSources/Prediction/ExplainableDTD_v1.0_KG2.10.0_refreshedTo_${LATEST_KG2_VER}.db"
link "${DB_DIR}/${LATEST_KG2_VER}/curie_ngd_v1.0_${LATEST_KG2_VER}.sqlite" "RTX/code/ARAX/KnowledgeSources/NormalizedGoogleDistance/curie_ngd_v1.0_${LATEST_KG2_VER}.sqlite"
link "${DB_DIR}/${LATEST_KG2_VER}/curie_to_pmids_v1.0_${LATEST_KG2_VER}.sqlite" "RTX/code/ARAX/KnowledgeSources/NormalizedGoogleDistance/curie_to_pmids_v1.0_${LATEST_KG2_VER}.sqlite"
link "${DB_DIR}/${LATEST_KG2_VER}/fda_approved_drugs_v1.0_${LATEST_KG2_VER}c.pickle" "RTX/code/ARAX/KnowledgeSources/fda_approved_drugs_v1.0_${LATEST_KG2_VER}c.pickle"
link "${DB_DIR}/${LATEST_KG2_VER}/kg2c_v1.0_${LATEST_KG2_VER}.sqlite" "RTX/code/ARAX/KnowledgeSources/KG2c/kg2c_v1.0_${LATEST_KG2_VER}.sqlite"
link "${DB_DIR}/${LATEST_KG2_VER}/node_synonymizer_v1.0_${LATEST_KG2_VER}.sqlite" "RTX/code/ARAX/NodeSynonymizer/node_synonymizer_v1.0_${LATEST_KG2_VER}.sqlite"
link "${DB_DIR}/${LATEST_KG2_VER}/autocomplete_v1.0_${LATEST_KG2_VER}.sqlite" "RTX/code/autocomplete/autocomplete_v1.0_${LATEST_KG2_VER}.sqlite"


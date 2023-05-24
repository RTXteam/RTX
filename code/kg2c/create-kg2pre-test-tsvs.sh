#!/usr/bin/env bash
# This script creates test (small) versions of the KG2pre TSV files.
# Usage: bash -x create-kg2pre-test-tsvs.sh

set -e

kg2c_dir="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"  # Thanks https://stackoverflow.com/a/246128
kg2pre_tsv_dir="${kg2c_dir}/kg2pre_tsvs"

tail -100000 ${kg2pre_tsv_dir}/nodes.tsv > ${kg2pre_tsv_dir}/nodes.tsv_TEMP
mv ${kg2pre_tsv_dir}/nodes.tsv_TEMP ${kg2pre_tsv_dir}/nodes.tsv
tail -100000 ${kg2pre_tsv_dir}/edges.tsv > ${kg2pre_tsv_dir}/edges.tsv_TEMP
mv ${kg2pre_tsv_dir}/edges.tsv_TEMP ${kg2pre_tsv_dir}/edges.tsv
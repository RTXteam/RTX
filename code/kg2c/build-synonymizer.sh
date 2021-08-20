#!/usr/bin/env bash
# This script builds an ARAX NodeSynonymizer off of the KG2 version pointed to in your configv2.json file.
# Usage: bash -x build-synonymizer.sh

set -e

script_dir="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"  # Thanks https://stackoverflow.com/a/246128
code_dir=${script_dir}/..
synonymizer_dir=${code_dir}/ARAX/NodeSynonymizer

# Build a NodeSynonymizer using the KG2 endpoint specified under the "KG2" slot in the ARAX config file
cd ${synonymizer_dir}
rm -f sri_node_normalizer_requests_cache.sqlite  # Cache may be stale, so we delete
python3 -u dump_kg2_node_data.py
python3 -u sri_node_normalizer.py --build
python3 -u node_synonymizer.py --build

# Build the autocomplete database
cd ${code_dir}/autocomplete
python3 -u create_load_db.py --input ${synonymizer_dir}/kg2_node_info.tsv --output ${synonymizer_dir}/autocomplete.sqlite
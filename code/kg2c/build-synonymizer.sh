#!/usr/bin/env bash
# This script builds an ARAX NodeSynonymizer off of the KG2 version pointed to in your configv2.json file.
# Usage: bash -x build-synonymizer.sh <name to give new synonymizer>

set -e

script_dir="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"  # Thanks https://stackoverflow.com/a/246128
arax_dir=${script_dir}/../ARAX
synonymizer_name=$1

# Build a NodeSynonymizer using the KG2 endpoint specified under the "KG2" slot in the ARAX config file
cd ${arax_dir}/NodeSynonymizer
rm -f sri_node_normalizer_requests_cache.sqlite  # Cache may be stale, so we delete
python3 -u dump_kg2_node_data.py
python3 -u sri_node_normalizer.py --build
python3 -u node_synonymizer.py --build
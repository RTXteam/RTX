#!/usr/bin/env bash
# This script creates a gzipped tarball of the KG2c TSvs.
# Usage: bash -x make-kg2c-tarball.sh

set -e

test_suffix=$1

kg2c_dir="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"  # Thanks https://stackoverflow.com/a/246128

cd ${kg2c_dir}

tar -czvf kg2c-tsv.tar.gz${test_suffix} nodes_c.tsv${test_suffix} nodes_c_header.tsv${test_suffix} edges_c.tsv${test_suffix} edges_c_header.tsv${test_suffix}

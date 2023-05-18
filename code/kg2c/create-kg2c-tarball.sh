#!/usr/bin/env bash
# This script creates a gzipped tarball of the KG2c TSvs.
# Usage: bash -x create-kg2c-tarball.sh

set -e

kg2c_dir="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"  # Thanks https://stackoverflow.com/a/246128

cd ${kg2c_dir}

tar -czvf kg2c-tsv.tar.gz nodes_c.tsv nodes_c_header.tsv edges_c.tsv edges_c_header.tsv

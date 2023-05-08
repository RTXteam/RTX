#!/usr/bin/env bash
# This script creates test (small) versions of the KG2pre TSV files.
# Usage: bash -x create-kg2pre-test-tsvs.sh

set -e

kg2c_dir="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"  # Thanks https://stackoverflow.com/a/246128

kg2pre_tarball_name="kg2-tsv-for-neo4j.tar.gz"
aws s3 cp --no-progress --region us-west-2 s3://rtx-kg2/${kg2pre_tarball_name} ${kg2c_dir}

kg2pre_tsv_dir="${kg2c_dir}/kg2pre_tsvs"
mkdir -p ${kg2pre_tsv_dir}
tar -xvzf ${kg2c_dir}/${kg2pre_tarball_name} -C ${kg2pre_tsv_dir}

tail -100000 ${kg2pre_tsv_dir}/nodes.tsv > ${kg2pre_tsv_dir}/nodes.tsv_TEMP
mv ${kg2pre_tsv_dir}/nodes.tsv_TEMP ${kg2pre_tsv_dir}/nodes.tsv
tail -100000 ${kg2pre_tsv_dir}/edges.tsv > ${kg2pre_tsv_dir}/edges.tsv_TEMP
mv ${kg2pre_tsv_dir}/edges.tsv_TEMP ${kg2pre_tsv_dir}/edges.tsv
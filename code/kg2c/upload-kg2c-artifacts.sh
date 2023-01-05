#!/usr/bin/env bash
# This script uploads artifacts from the KG2c build to arax.ncats.io at the specified path.
# Usage: bash -x upload-kg2c-artifacts.sh <destination_path_on_arax_ncats_io>

set -e

script_dir="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"  # Thanks https://stackoverflow.com/a/246128
db_host=$1
remote_database_dir=$2
remote_database_subdir="${remote_database_dir}/extra_files"

# Make sure the necessary directories exist on arax.ncats.io (will not hurt if these directories already exist)
ssh rtxconfig@${db_host} "mkdir -p ${remote_database_dir}"
ssh rtxconfig@${db_host} "mkdir -p ${remote_database_subdir}"

cd ${script_dir}
scp kg2c.sqlite rtxconfig@${db_host}:${remote_database_dir}
scp kg2c_meta_kg.json rtxconfig@${db_host}:${remote_database_dir}
scp kg2c-tsv.tar.gz rtxconfig@${db_host}:${remote_database_subdir}
scp fda_approved_drugs.pickle rtxconfig@${db_host}:${remote_database_dir}
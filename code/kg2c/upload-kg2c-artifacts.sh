#!/usr/bin/env bash
# This script uploads artifacts from the KG2c build to the databases server at the specified path.
# Usage: bash -x upload-kg2c-artifacts.sh <destination_path_on_arax_databases_rtx_ai>

set -e

script_dir="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"  # Thanks https://stackoverflow.com/a/246128
db_host=$1
kg2c_db_version=$2
kg2_version=$3
remote_database_dir=$4
test_suffix=$5
remote_database_subdir="${remote_database_dir}/extra_files"

# Make sure the necessary directories exist on arax-databases.rtx.ai (will not hurt if these directories already exist)
ssh rtxconfig@${db_host} "mkdir -p ${remote_database_dir}"
ssh rtxconfig@${db_host} "mkdir -p ${remote_database_subdir}"

cd ${script_dir}

# First upload required files
scp kg2c.sqlite rtxconfig@${db_host}:${remote_database_dir}/kg2c_${kg2c_db_version}_KG${kg2_version}.sqlite${test_suffix}
scp meta_kg.json rtxconfig@${db_host}:${remote_database_dir}/meta_kg_${kg2c_db_version}_KG${kg2_version}c.json${test_suffix}
scp fda_approved_drugs.pickle rtxconfig@${db_host}:${remote_database_dir}/fda_approved_drugs_${kg2c_db_version}_KG${kg2_version}c.pickle${test_suffix}

# Then upload files not actually needed for running ARAX code
scp kg2c-tsv.tar.gz rtxconfig@${db_host}:${remote_database_subdir}/kg2c-tsv.tar.gz${test_suffix}

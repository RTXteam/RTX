#!/usr/bin/env bash
# This script uploads artifacts from the NodeSynonymizer build to arax-databases.rtx.ai at the specified path.
# Usage: bash -x upload-synonymizer-artifacts.sh <destination_path_on_arax_ncats_io> <name_of_synonymizer_sqlite>

set -e

script_dir="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"  # Thanks https://stackoverflow.com/a/246128
arax_dir=${script_dir}/../ARAX
db_host=$1
remote_database_dir=$2
synonymizer_name=$3
remote_database_subdir="${remote_database_dir}/extra_files"

# Make sure the necessary directories exist on arax-databases.rtx.ai (will not hurt if these directories already exist)
ssh rtxconfig@${db_host} "mkdir -p ${remote_database_dir}"
ssh rtxconfig@${db_host} "mkdir -p ${remote_database_subdir}"

cd ${arax_dir}/NodeSynonymizer
scp ${synonymizer_name} rtxconfig@${db_host}:${remote_database_dir}
scp kg2_node_info.tsv rtxconfig@${db_host}:${remote_database_subdir}
scp kg2_equivalencies.tsv rtxconfig@${db_host}:${remote_database_subdir}
scp kg2_synonyms.json rtxconfig@${db_host}:${remote_database_subdir}
scp Problems.tsv rtxconfig@${db_host}:${remote_database_subdir}
scp Exceptions.txt rtxconfig@${db_host}:${remote_database_subdir}
scp sri_node_normalizer_curie_cache.pickle rtxconfig@${db_host}:${remote_database_subdir}
scp sri_node_normalizer_requests_cache.sqlite rtxconfig@${db_host}:${remote_database_subdir}
scp autocomplete.sqlite rtxconfig@${db_host}:${remote_database_dir}
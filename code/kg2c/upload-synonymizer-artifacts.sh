#!/usr/bin/env bash
# This script uploads artifacts from the NodeSynonymizer build to arax.ncats.io at the specified path.
# Usage: bash -x upload-synonymizer-artifacts.sh <destination_path_on_arax_ncats_io> <name_of_synonymizer_sqlite>

set -e

script_dir="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"  # Thanks https://stackoverflow.com/a/246128
arax_dir=${script_dir}/../ARAX
remote_database_dir=$1
synonymizer_name=$2
remote_database_subdir="${remote_database_dir}/extra_files"

# Make sure the necessary directories exist on arax.ncats.io (will not hurt if these directories already exist)
ssh rtxconfig@arax.ncats.io "mkdir -p ${remote_database_dir}"
ssh rtxconfig@arax.ncats.io "mkdir -p ${remote_database_subdir}"

cd ${arax_dir}/NodeSynonymizer
scp ${synonymizer_name} rtxconfig@arax.ncats.io:${remote_database_dir}
scp kg2_node_info.tsv rtxconfig@arax.ncats.io:${remote_database_subdir}
scp kg2_equivalencies.tsv rtxconfig@arax.ncats.io:${remote_database_subdir}
scp kg2_synonyms.json rtxconfig@arax.ncats.io:${remote_database_subdir}
scp Problems.tsv rtxconfig@arax.ncats.io:${remote_database_subdir}
scp Exceptions.txt rtxconfig@arax.ncats.io:${remote_database_subdir}
scp sri_node_normalizer_curie_cache.pickle rtxconfig@arax.ncats.io:${remote_database_subdir}
scp sri_node_normalizer_requests_cache.sqlite rtxconfig@arax.ncats.io:${remote_database_subdir}
scp autocomplete.sqlite rtxconfig@arax.ncats.io:${remote_database_dir}
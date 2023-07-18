#!/usr/bin/env bash
# This script uploads artifacts from the NodeSynonymizer build to arax-databases.rtx.ai at the specified path.
# Usage: bash -x upload-synonymizer-artifacts.sh <destination_path_on_arax_databases_rtx_ai> <name_of_synonymizer_sqlite>

set -e

kg2c_dir="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"  # Thanks https://stackoverflow.com/a/246128
synonymizer_build_dir=${kg2c_dir}/synonymizer_build
db_host=$1
remote_database_dir=$2
synonymizer_db_version=$3
kg2_version=$4
test_suffix=$5
remote_database_subdir="${remote_database_dir}/extra_files"

# Make sure the necessary directories exist on arax-databases.rtx.ai (will not hurt if these directories already exist)
ssh rtxconfig@${db_host} "mkdir -p ${remote_database_dir}"
ssh rtxconfig@${db_host} "mkdir -p ${remote_database_subdir}"

cd ${synonymizer_build_dir}

# Upload required databases
scp node_synonymizer.sqlite rtxconfig@${db_host}:${remote_database_dir}/node_synonymizer_${synonymizer_db_version}_KG${kg2_version}.sqlite${test_suffix}
scp autocomplete.sqlite rtxconfig@${db_host}:${remote_database_dir}/autocomplete_${synonymizer_db_version}_KG${kg2_version}.sqlite${test_suffix}

# Upload 'extra files' (nice for debugging; not needed by running ARAX code)
for file_name in  \
3_merged_match_nodes.tsv \
3_merged_match_edges.tsv \
4_match_nodes_preprocessed.tsv \
4_match_edges_preprocessed.tsv \
5_report_category_counts.tsv \
5_report_cluster_sizes.tsv \
5_report_cluster_sizes_non_sri_nodes.tsv \
5_report_major_branch_counts.tsv \
5_report_oversized_clusters.tsv \
5_report_predicate_counts.tsv \
5_report_primary_knowledge_source_counts.tsv \
5_report_upstream_resource_counts.tsv \
kg2_nodes_not_in_sri_nn.tsv; do
  scp ${file_name} rtxconfig@${db_host}:${remote_database_subdir}/${file_name}${test_suffix}
done
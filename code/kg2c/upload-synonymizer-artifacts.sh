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
remote_database_subdir="${remote_database_dir}/extra_files"

# Make sure the necessary directories exist on arax-databases.rtx.ai (will not hurt if these directories already exist)
ssh rtxconfig@${db_host} "mkdir -p ${remote_database_dir}"
ssh rtxconfig@${db_host} "mkdir -p ${remote_database_subdir}"

cd ${synonymizer_build_dir}

# Upload required databases
scp node_synonymizer.sqlite rtxconfig@${db_host}:${remote_database_dir}/node_synonymizer_${synonymizer_db_version}_KG${kg2_version}.sqlite
scp autocomplete.sqlite rtxconfig@${db_host}:${remote_database_dir}/autocomplete_${synonymizer_db_version}_KG${kg2_version}.sqlite

# Upload 'extra files' (nice for debugging; not needed by running ARAX code)
scp 3_merged_match_nodes.tsv rtxconfig@${db_host}:${remote_database_subdir}
scp 3_merged_match_edges.tsv rtxconfig@${db_host}:${remote_database_subdir}
scp 4_cluster_member_map.tsv rtxconfig@${db_host}:${remote_database_subdir}
scp 5_report_category_counts.tsv rtxconfig@${db_host}:${remote_database_subdir}
scp 5_report_cluster_sizes.tsv rtxconfig@${db_host}:${remote_database_subdir}
scp 5_report_cluster_sizes_non_sri_nodes.tsv rtxconfig@${db_host}:${remote_database_subdir}
scp 5_report_major_branch_counts.tsv rtxconfig@${db_host}:${remote_database_subdir}
scp 5_report_oversized_clusters.tsv rtxconfig@${db_host}:${remote_database_subdir}
scp 5_report_predicate_counts.tsv rtxconfig@${db_host}:${remote_database_subdir}
scp 5_report_primary_knowledge_source_counts.tsv rtxconfig@${db_host}:${remote_database_subdir}
scp 5_report_upstream_resource_counts.tsv rtxconfig@${db_host}:${remote_database_subdir}

#!/usr/bin/env bash
# This script uploads artifacts from the NodeSynonymizer build to arax.ncats.io at the specified path.
# Usage: bash -x upload-synonymizer-artifacts.sh <destination_path_on_arax_ncats_io>

set -e

script_dir="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"  # Thanks https://stackoverflow.com/a/246128
arax_dir=${script_dir}/../ARAX
remote_destination=$1
synonymizer_name=$2

cd ${arax_dir}/NodeSynonymizer
scp ${synonymizer_name} rtxconfig@arax.ncats.io:${remote_destination}
scp kg2_node_info.tsv rtxconfig@arax.ncats.io:${remote_destination}
scp kg2_equivalencies.tsv rtxconfig@arax.ncats.io:${remote_destination}
scp kg2_synonyms.json rtxconfig@arax.ncats.io:${remote_destination}
scp Problems.tsv rtxconfig@arax.ncats.io:${remote_destination}
scp Exceptions.txt rtxconfig@arax.ncats.io:${remote_destination}
scp sri_node_normalizer_curie_cache.pickle rtxconfig@arax.ncats.io:${remote_destination}
scp sri_node_normalizer_requests_cache.sqlite rtxconfig@arax.ncats.io:${remote_destination}
import math
import os
import sys
import re

import logging

from datetime import datetime

import redis

from ngd_calculation_process import run_ngd_calculation_process
from curie_pmids_into_memory import curie_pmids_into_memory
from RedisConnector import RedisConnector

sys.path.append(os.path.dirname(os.path.abspath(__file__)) + "/../../")
from RTXConfiguration import RTXConfiguration


def get_curie_to_pmids_path():
    pathlist = os.path.realpath(__file__).split(os.path.sep)
    RTXindex = pathlist.index("RTX")
    filepath = os.path.sep.join(
        [*pathlist[:(RTXindex + 1)], 'code', 'ARAX', 'KnowledgeSources', 'NormalizedGoogleDistance'])
    sqlite_name = RTXConfiguration().curie_to_pmids_path.split("/")[-1]
    match = re.search(r'KG(\d+\.\d+\.\d+)', sqlite_name)
    if match:
        curie_to_pmids_version = match.group(1)
    else:
        raise Exception("Cannot find version in the path")
    return f"{filepath}{os.path.sep}{sqlite_name}", curie_to_pmids_version


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    logging.info(f"Start time: {datetime.now()}")

    curie_to_pmids_path, version = get_curie_to_pmids_path()
    curie_ngd_db_name = f"curie_ngd_v1.0_KG{version}.sqlite"
    logging.info(f"This script will build {curie_ngd_db_name} database")

    redis_host = 'localhost'
    redis_port = 6379
    redis_db = 0
    number_of_PubMed_citations_and_abstracts_of_biomedical_literature = 3.5e+7
    average_MeSH_terms_per_article = 20
    NGD_normalizer = number_of_PubMed_citations_and_abstracts_of_biomedical_literature * average_MeSH_terms_per_article

    logging.info("Make sure to download a proper version of curie_to_pmids database.")
    logging.info(f"curie_to_pmids_path: {curie_to_pmids_path}")
    logging.info("Make sure to connect to a proper version of PloverDB.")
    logging.info(f"PloverDB url: {RTXConfiguration().plover_url}")
    logging.info(f"redis host: {redis_host}")
    logging.info(f"redis port: {redis_port}")
    logging.info(f"redis db: {redis_db}")
    logging.info(
        f"Number of PubMed citations and abstracts of biomedical literature: {number_of_PubMed_citations_and_abstracts_of_biomedical_literature}")
    logging.info(f"Average MeSH terms per article: {average_MeSH_terms_per_article}")

    redis_client = redis.Redis(host=redis_host, port=redis_port, db=redis_db)
    curie_pmids_into_memory(curie_to_pmids_path, version, redis_client)

    log_NGD_normalizer = math.log(NGD_normalizer)
    redis_connector = RedisConnector(redis_client)
    run_ngd_calculation_process(curie_to_pmids_path, curie_ngd_db_name, log_NGD_normalizer, redis_connector)

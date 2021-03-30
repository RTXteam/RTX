#!/usr/bin/env python3
"""
This class builds a sqlite database that maps (canonicalized) curies to PubMed articles they appear in. It creates these
mappings using data from a PubMed XML download and from KG2.
There are two halves to the (full) build process:
1. Create an intermediary file called "conceptname_to_pmids.db"
     - Contains mappings from "concept names" to the list of articles (PMIDs) they appear in (where "concept names"
       include MESH Descriptor/Qualifier names, Keywords, and Chemical names)
     - These mappings are obtained by scraping all of the PubMed XML files
     - This file needs updating very infrequently (i.e., only with new PubMed releases)
2. Create the final file called "curie_to_pmids.sqlite"
     - Contains mappings from canonicalized curies to their list of PMIDs based on the data scraped from Pubmed AND
       from KG2 data (node.publications and edge.publications)
     - The NodeSynonymizer is used to link curies to concept names from step 1
Usage: python build_ngd_database.py <path to directory containing PubMed xml files> [--test] [--full]
       By default, only step 2 above will be performed. To do a "full" build, use the --full flag.
"""
import argparse
import ast
import gzip
import json
import os
import sqlite3
import sys
import time
import traceback
from typing import List, Dict, Set, Union

from lxml import etree
import pickledb
from neo4j import GraphDatabase

pathlist = os.path.realpath(__file__).split(os.path.sep)
RTXindex = pathlist.index("RTX")

sys.path.append(os.path.sep.join([*pathlist[:(RTXindex + 1)], 'code', 'ARAX', 'NodeSynonymizer']))
from node_synonymizer import NodeSynonymizer
sys.path.append(os.path.sep.join([*pathlist[:(RTXindex + 1)], 'code']))  # code directory
from RTXConfiguration import RTXConfiguration


class NGDDatabaseBuilder:
    def __init__(self, pubmed_directory_path, is_test):
        self.pubmed_directory_path = pubmed_directory_path
        self.conceptname_to_pmids_db_name = "conceptname_to_pmids.db"
        self.curie_to_pmids_db_name = "curie_to_pmids.sqlite"
        self.status = 'OK'
        self.synonymizer = NodeSynonymizer()
        self.is_test = is_test

    def build_conceptname_to_pmids_db(self):
        # This function extracts curie -> PMIDs mappings from a Pubmed XML download (saves data in a pickledb)
        print(f"Starting to build {self.conceptname_to_pmids_db_name} from pubmed files..")
        start = time.time()
        pubmed_directory = os.fsencode(self.pubmed_directory_path)
        all_file_names = [os.fsdecode(file) for file in os.listdir(pubmed_directory)]
        pubmed_file_names = [file_name for file_name in all_file_names if file_name.startswith('pubmed') and
                             file_name.endswith('.xml.gz')]
        if not pubmed_file_names:
            print(f"ERROR: Couldn't find any PubMed XML files to scrape. Provide the path to the directory "
                  f"containing your PubMed download as a command line argument.")
            self.status = 'ERROR'
        else:
            conceptname_to_pmids_map = dict()
            # Go through each downloaded pubmed file and build our dictionary of mappings
            pubmed_file_names_to_process = pubmed_file_names if not self.is_test else pubmed_file_names[:1]
            for file_name in pubmed_file_names_to_process:
                print(f"  Starting to process file '{file_name}'.. ({pubmed_file_names_to_process.index(file_name) + 1}"
                      f" of {len(pubmed_file_names_to_process)})")
                file_start_time = time.time()
                with gzip.open(f"{self.pubmed_directory_path}/{file_name}") as pubmed_file:
                    file_contents_tree = etree.parse(pubmed_file)
                pubmed_articles = file_contents_tree.xpath("//PubmedArticle")

                for article in pubmed_articles:
                    # Link each concept name to the PMID of this article
                    current_pmid = article.xpath(".//MedlineCitation/PMID/text()")[0]
                    descriptor_names = article.xpath(".//MedlineCitation/MeshHeadingList/MeshHeading/DescriptorName/text()")
                    qualifier_names = article.xpath(".//MedlineCitation/MeshHeadingList/MeshHeading/QualifierName/text()")
                    chemical_names = article.xpath(".//MedlineCitation/ChemicalList/Chemical/NameOfSubstance/text()")
                    gene_symbols = article.xpath(".//MedlineCitation/GeneSymbolList/GeneSymbol/text()")
                    keywords = article.xpath(".//MedlineCitation/KeywordList/Keyword/text()")
                    all_concept_names = descriptor_names + qualifier_names + chemical_names + gene_symbols + keywords
                    unique_concept_names = {concept_name for concept_name in all_concept_names if concept_name}
                    for concept_name in unique_concept_names:
                        self._add_pmids_mapping(concept_name, current_pmid, conceptname_to_pmids_map)

                self._destroy_etree(file_contents_tree)  # Hack around lxml memory leak
                print(f"    took {round((time.time() - file_start_time) / 60, 2)} minutes")

            # Save the data to the PickleDB after we're done
            print("  Loading data into PickleDB..")
            conceptname_to_pmids_db = pickledb.load(self.conceptname_to_pmids_db_name, False)
            for concept_name, pmid_list in conceptname_to_pmids_map.items():
                conceptname_to_pmids_db.set(concept_name, list({self._create_pmid_curie_from_local_id(pmid) for pmid in pmid_list}))
            print("  Saving PickleDB file..")
            conceptname_to_pmids_db.dump()
            print(f"Done! Building {self.conceptname_to_pmids_db_name} took {round(((time.time() - start) / 60) / 60, 3)} hours")

    def build_curie_to_pmids_db(self):
        # This function creates a final sqlite database of curie->PMIDs mappings using data scraped from Pubmed AND KG2
        print(f"Starting to build {self.curie_to_pmids_db_name}..")
        start = time.time()
        curie_to_pmids_map = dict()
        self._add_pmids_from_pubmed_scrape(curie_to_pmids_map)
        if self.status != 'OK':
            return
        self._add_pmids_from_kg2_edges(curie_to_pmids_map)
        self._add_pmids_from_kg2_nodes(curie_to_pmids_map)
        print(f"  In the end, found PMID lists for {len(curie_to_pmids_map)} (canonical) curies")
        self._save_data_in_sqlite_db(curie_to_pmids_map)
        print(f"Done! Building {self.curie_to_pmids_db_name} took {round((time.time() - start) / 60)} minutes.")

    # Helper methods

    def _add_pmids_from_kg2_edges(self, curie_to_pmids_map):
        print(f"  Getting PMIDs from edges in KG2 neo4j..")
        edge_query = f"match (n)-[e]->(m) where e.publications is not null " \
                     f"return distinct n.id, m.id, e.publications{' limit 100' if self.is_test else ''}"
        edge_results = self._run_cypher_query(edge_query)
        print(f"  Processing results..")
        node_ids = {result['n.id'] for result in edge_results}.union(result['m.id'] for result in edge_results)
        canonicalized_curies_dict = self._get_canonicalized_curies_dict(list(node_ids))
        for result in edge_results:
            canonicalized_node_ids = {canonicalized_curies_dict[result['n.id']],
                                      canonicalized_curies_dict[result['m.id']]}
            pmids = self._extract_and_format_pmids(result['e.publications'])
            if pmids:  # Sometimes publications list includes only non-PMID identifiers (like ISBN)
                for canonical_curie in canonicalized_node_ids:
                    self._add_pmids_mapping(canonical_curie, pmids, curie_to_pmids_map)

    def _add_pmids_from_kg2_nodes(self, curie_to_pmids_map):
        print(f"  Getting PMIDs from nodes in KG2 neo4j..")
        node_query = f"match (n) where n.publications is not null " \
                     f"return distinct n.id, n.publications{' limit 100' if self.is_test else ''}"
        node_results = self._run_cypher_query(node_query)
        print(f"  Processing results..")
        node_ids = {result['n.id'] for result in node_results}
        canonicalized_curies_dict = self._get_canonicalized_curies_dict(list(node_ids))
        for result in node_results:
            canonical_curie = canonicalized_curies_dict[result['n.id']]
            pmids = self._extract_and_format_pmids(result['n.publications'])
            if pmids:  # Sometimes publications list includes only non-PMID identifiers (like ISBN)
                self._add_pmids_mapping(canonical_curie, pmids, curie_to_pmids_map)

    def _add_pmids_from_pubmed_scrape(self, curie_to_pmids_map):
        # Load the data from the first half of the build process (scraping pubmed)
        print(f"  Loading pickle DB containing pubmed scrapings ({self.conceptname_to_pmids_db_name})..")
        conceptname_to_pmids_db = pickledb.load(self.conceptname_to_pmids_db_name, False)
        if not conceptname_to_pmids_db.getall():
            print(f"ERROR: {self.conceptname_to_pmids_db_name} must exist to do a partial build. Use --full or locate "
                  f"that file.")
            self.status = 'ERROR'
            return

        # Get canonical curies for all of the concept names in our big pubmed pickleDB using the NodeSynonymizer
        concept_names = list(conceptname_to_pmids_db.getall())
        print(f"  Sending NodeSynonymizer.get_canonical_curies() a list of {len(concept_names)} concept names..")
        canonical_curies_dict = self.synonymizer.get_canonical_curies(names=concept_names)
        print(f"  Got results back from NodeSynonymizer. (Returned dict contains {len(canonical_curies_dict)} keys.)")

        # Map all of the concept names scraped from pubmed to curies
        if canonical_curies_dict:
            recognized_concepts = {concept for concept in canonical_curies_dict if canonical_curies_dict.get(concept)}
            print(f"  NodeSynonymizer recognized {round((len(recognized_concepts) / len(concept_names)) * 100)}% of "
                  f"concept names scraped from pubmed.")
            # Store which concept names the NodeSynonymizer didn't know about, for learning purposes
            unrecognized_concepts = set(canonical_curies_dict).difference(recognized_concepts)
            with open('unrecognized_pubmed_concept_names.txt', 'w+') as unrecognized_concepts_file:
                unrecognized_concepts_file.write(f"{unrecognized_concepts}")
            print(f"  Unrecognized concept names were written to 'unrecognized_pubmed_concept_names.txt'.")

            # Map the canonical curie for each recognized concept to the concept's PMID list
            print(f"  Mapping canonical curies to PMIDs..")
            for concept_name in recognized_concepts:
                canonical_curie = canonical_curies_dict[concept_name].get('preferred_curie')
                pmids_for_this_concept = conceptname_to_pmids_db.get(concept_name)
                self._add_pmids_mapping(canonical_curie, pmids_for_this_concept, curie_to_pmids_map)
            print(f"  Mapped {len(curie_to_pmids_map)} canonical curies to PMIDs based on pubmed scrapings.")
        else:
            print(f"ERROR: NodeSynonymizer didn't return anything!")
            self.status = 'ERROR'

    def _save_data_in_sqlite_db(self, curie_to_pmids_map):
        print("  Loading data into sqlite database..")
        # Remove any preexisting version of this database
        if os.path.exists(self.curie_to_pmids_db_name):
            os.remove(self.curie_to_pmids_db_name)
        connection = sqlite3.connect(self.curie_to_pmids_db_name)
        cursor = connection.cursor()
        cursor.execute("CREATE TABLE curie_to_pmids (curie TEXT, pmids TEXT)")
        cursor.execute("CREATE UNIQUE INDEX unique_curie ON curie_to_pmids (curie)")
        print(f"  Gathering row data..")
        rows = [[curie, json.dumps(list(filter(None, {self._get_local_id_as_int(pmid) for pmid in pmids})))]
                for curie, pmids in curie_to_pmids_map.items()]
        rows_in_chunks = self._divide_list_into_chunks(rows, 5000)
        print(f"  Inserting row data into database..")
        for chunk in rows_in_chunks:
            cursor.executemany(f"INSERT INTO curie_to_pmids (curie, pmids) VALUES (?, ?)", chunk)
            connection.commit()
        # Log how many rows we've added in the end (for debugging purposes)
        cursor.execute(f"SELECT COUNT(*) FROM curie_to_pmids")
        count = cursor.fetchone()[0]
        print(f"  Done saving data in sqlite; database contains {count} rows.")
        cursor.close()

    def _get_canonicalized_curies_dict(self, curies: List[str]) -> Dict[str, str]:
        print(f"  Sending a batch of {len(curies)} curies to NodeSynonymizer.get_canonical_curies()")
        canonicalized_nodes_info = self.synonymizer.get_canonical_curies(curies)
        canonicalized_curies_dict = dict()
        for input_curie, preferred_info_dict in canonicalized_nodes_info.items():
            if preferred_info_dict:
                canonicalized_curies_dict[input_curie] = preferred_info_dict.get('preferred_curie', input_curie)
            else:
                canonicalized_curies_dict[input_curie] = input_curie
        print(f"  Got results back from synonymizer")
        return canonicalized_curies_dict

    def _extract_and_format_pmids(self, publications: List[str]) -> List[str]:
        pmids = {publication_id for publication_id in publications if publication_id.upper().startswith('PMID')}
        # Make sure all PMIDs are given in same format (e.g., PMID:18299583 rather than PMID18299583)
        formatted_pmids = [self._create_pmid_curie_from_local_id(pmid.replace('PMID', '').replace(':', '')) for pmid in pmids]
        return formatted_pmids

    @staticmethod
    def _add_pmids_mapping(key: str, value_to_append: Union[str, List[str]], mappings_dict: Dict[str, List[str]]):
        if key not in mappings_dict:
            mappings_dict[key] = []
        if isinstance(value_to_append, list):
            mappings_dict[key] += value_to_append
        else:
            mappings_dict[key].append(value_to_append)

    @staticmethod
    def _create_pmid_curie_from_local_id(pmid):
        return f"PMID:{pmid}"

    @staticmethod
    def _get_local_id_as_int(curie):
        # Converts "PMID:1234" to 1234
        curie_pieces = curie.split(":")
        local_id_str = curie_pieces[-1]
        # Remove any strange characters (like in "PMID:_19960544")
        stripped_id_str = "".join([character for character in local_id_str if character.isdigit()])
        return int(stripped_id_str) if stripped_id_str else None

    @staticmethod
    def _destroy_etree(file_contents_tree):
        # Thank you to https://stackoverflow.com/a/49139904 for this method; important to prevent memory blow-up
        root = file_contents_tree.getroot()
        element_tracker = {root: [0, None]}
        for element in root.iterdescendants():
            parent = element.getparent()
            element_tracker[element] = [element_tracker[parent][0] + 1, parent]
        element_tracker = sorted([(depth, parent, child) for child, (depth, parent)
                                  in element_tracker.items()], key=lambda x: x[0], reverse=True)
        for _, parent, child in element_tracker:
            if parent is None:
                break
            parent.remove(child)
        del file_contents_tree

    @staticmethod
    def _run_cypher_query(cypher_query: str) -> List[Dict[str, any]]:
        rtxc = RTXConfiguration()
        rtxc.live = "KG2"
        try:
            driver = GraphDatabase.driver(rtxc.neo4j_bolt, auth=(rtxc.neo4j_username, rtxc.neo4j_password))
            with driver.session() as session:
                query_results = session.run(cypher_query).data()
            driver.close()
        except Exception:
            tb = traceback.format_exc()
            error_type, error, _ = sys.exc_info()
            print(f"Encountered an error interacting with KG2 neo4j. {tb}")
            return []
        else:
            return query_results

    @staticmethod
    def _divide_list_into_chunks(input_list: List[any], chunk_size: int) -> List[List[any]]:
        num_chunks = len(input_list) // chunk_size if len(input_list) % chunk_size == 0 else (len(input_list) // chunk_size) + 1
        start_index = 0
        stop_index = chunk_size
        all_chunks = []
        for num in range(num_chunks):
            chunk = input_list[start_index:stop_index] if stop_index <= len(input_list) else input_list[start_index:]
            all_chunks.append(chunk)
            start_index += chunk_size
            stop_index += chunk_size
        return all_chunks


def main():
    # Load command-line arguments
    arg_parser = argparse.ArgumentParser(description="Builds database of curie->PMID mappings needed for NGD")
    arg_parser.add_argument("pubmedDirectory", type=str, nargs='?', default=os.getcwd())
    arg_parser.add_argument("--full", dest="full", action="store_true", default=False)
    arg_parser.add_argument("--test", dest="test", action="store_true", default=False)
    args = arg_parser.parse_args()

    # Build the database(s)
    database_builder = NGDDatabaseBuilder(args.pubmedDirectory, args.test)
    if args.full:
        database_builder.build_conceptname_to_pmids_db()
    if database_builder.status == 'OK':
        database_builder.build_curie_to_pmids_db()


if __name__ == '__main__':
    main()

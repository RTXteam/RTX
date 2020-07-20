#!/usr/bin/env python3
"""
This class builds a PickleDB that maps (canonicalized) curies from the NodeSynonymizer to PubMed articles (PMIDs).
There are two halves to the (full) build process:
1. Creates an intermediary file called "conceptname_to_pmids.db"
     - Contains mappings from "concept names" to the list of articles (PMIDs) they appear in (where "concept names"
       include MESH Descriptor/Qualifier names, Keywords, and Chemical names)
     - These mappings are obtained by scraping ALL of the PubMed XML files
     - This file needs updating very infrequently (i.e., only with new PubMed releases)
2. Creates the final file called "curie_to_pmids.db"
     - Contains mappings from canonicalized curies in the NodeSynonymizer to their list of associated articles (PMIDs)
     - The NodeSynonymizer is used to link curies to concept names (which were linked to PMIDs in step 1)
Usage: python build_ngd_database.py <path to directory containing PubMed xml files> [--full]
       By default, only step 2 above will be performed. To do a "full" build, use the --full flag.
"""
import argparse
import os
import sys
import gzip
import time

from lxml import etree
import pickledb

sys.path.append(f"{os.path.dirname(os.path.abspath(__file__))}/../../../NodeSynonymizer/")
from node_synonymizer import NodeSynonymizer

CONCEPTNAME_TO_PMIDS_DB_FILE_NAME = "conceptname_to_pmids.db"
CURIE_TO_PMIDS_DB_FILE_NAME = "curie_to_pmids.db"


class NGDDatabaseBuilder:
    def __init__(self, pubmed_directory_path):
        self.conceptname_to_pmids_db = pickledb.load(CONCEPTNAME_TO_PMIDS_DB_FILE_NAME, False)
        self.curie_to_pmids_db = pickledb.load(CURIE_TO_PMIDS_DB_FILE_NAME, False)
        self.pubmed_directory_path = pubmed_directory_path
        self.status = 'OK'

    def build_conceptname_to_pmids_db(self):
        print(f"Starting to build {CONCEPTNAME_TO_PMIDS_DB_FILE_NAME} from pubmed files..")
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
            for file_name in pubmed_file_names:
                print(f"  Starting to process file '{file_name}'.. ({pubmed_file_names.index(file_name) + 1} of "
                      f"{len(pubmed_file_names)})")
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
                        self._add_mapping(concept_name, current_pmid, conceptname_to_pmids_map)

                self._destroy_etree(file_contents_tree)  # Hack around lxml memory leak
                print(f"    took {round((time.time() - file_start_time) / 60, 2)} minutes")

            # Save the data to the PickleDB after we're done
            print("  Loading data into PickleDB..")
            for concept_name, pmid_list in conceptname_to_pmids_map.items():
                self.conceptname_to_pmids_db.set(concept_name, list({self._create_pmid_string(pmid) for pmid in pmid_list}))
            print("  Saving PickleDB file..")
            self.conceptname_to_pmids_db.dump()
            print(f"Done! Building {CONCEPTNAME_TO_PMIDS_DB_FILE_NAME} took {round(((time.time() - start) / 60) / 60, 3)} hours")

    def build_curie_to_pmids_db(self):
        print(f"Starting to build {CURIE_TO_PMIDS_DB_FILE_NAME}..")
        start = time.time()
        if not self.conceptname_to_pmids_db.getall():
            print(f"ERROR: {CONCEPTNAME_TO_PMIDS_DB_FILE_NAME} must exist to do a partial build. Use --full or locate "
                  f"that file.")
            self.status = 'ERROR'
            return

        # Get canonical curies for all of the concept names in our big pubmed pickleDB using the NodeSynonymizer
        concept_names = list(self.conceptname_to_pmids_db.getall())
        synonymizer = NodeSynonymizer()
        print(f"  Sending NodeSynonymizer.get_canonical_curies() a list of {len(concept_names)} concept names..")
        canonical_curies_dict = synonymizer.get_canonical_curies(names=concept_names)
        print(f"  Got results back from NodeSynonymizer. (Returned dict contains {len(canonical_curies_dict)} keys.)")

        curie_to_pmids_map = dict()
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
                pmids_for_this_concept = self.conceptname_to_pmids_db.get(concept_name)
                self._add_mapping(canonical_curie, pmids_for_this_concept, curie_to_pmids_map)
            print(f"  In total, mapped {len(curie_to_pmids_map)} canonical curies to PMIDs.")

            # Save the data to our final pickleDB
            print("  Loading data into PickleDB..")
            for curie, pmid_list in curie_to_pmids_map.items():
                self.curie_to_pmids_db.set(curie, list(set(pmid_list)))
            print("  Saving PickleDB file..")
            self.curie_to_pmids_db.dump()
            print(f"Done! Building {CURIE_TO_PMIDS_DB_FILE_NAME} took {round((time.time() - start) / 60)} minutes.")
        else:
            print(f"ERROR: NodeSynonymizer didn't return anything!")
            self.status = 'ERROR'

    # Helper methods

    @staticmethod
    def _add_mapping(key, value_to_append, mappings_dict):
        if key not in mappings_dict:
            mappings_dict[key] = []
        if isinstance(value_to_append, list):
            mappings_dict[key] += value_to_append
        else:
            mappings_dict[key].append(value_to_append)

    @staticmethod
    def _create_pmid_string(pmid):
        return f"PMID:{pmid}"

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


def main():
    # Load command-line arguments
    arg_parser = argparse.ArgumentParser(description="Builds pickle database of curie->PMID mappings needed for NGD")
    arg_parser.add_argument("pubmedDirectory", type=str, nargs='?', default=os.getcwd())
    arg_parser.add_argument("--full", dest="full", action="store_true", default=False)
    args = arg_parser.parse_args()

    # Build the database(s)
    database_builder = NGDDatabaseBuilder(args.pubmedDirectory)
    if args.full:
        database_builder.build_conceptname_to_pmids_db()
    if database_builder.status == 'OK':
        database_builder.build_curie_to_pmids_db()


if __name__ == '__main__':
    main()

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
import pickledb
import gzip
import time
from lxml import etree


class NGDDatabaseBuilder:
    def __init__(self, pubmed_directory_path):
        self.conceptname_to_pmids_db = pickledb.load("conceptname_to_pmids.db", False)
        self.curie_to_pmids_db = pickledb.load("curie_to_pmids.db", False)
        self.pubmed_directory_path = pubmed_directory_path

    def build_conceptname_to_pmids_db(self):
        print("Extracting conceptname->PMIDs mappings from pubmed files...")
        start = time.time()
        pubmed_directory = os.fsencode(self.pubmed_directory_path)
        all_file_names = [os.fsdecode(file) for file in os.listdir(pubmed_directory)]
        pubmed_file_names = [file_name for file_name in all_file_names if file_name.startswith("pubmed") and file_name.endswith(".xml.gz")]
        if not pubmed_file_names:
            print(f"Sorry, couldn't find any PubMed XML files to scrape.")
        else:
            conceptname_to_pmids_map = dict()
            # Go through each downloaded pubmed file and build our dictionary of mappings
            for file_name in pubmed_file_names:
                print(f"  Starting to process file '{file_name}'... ({pubmed_file_names.index(file_name) + 1} of {len(pubmed_file_names)})")
                file_start_time = time.time()
                with gzip.open(f"{self.pubmed_directory_path}/{file_name}") as pubmed_file:
                    file_contents_tree = etree.parse(pubmed_file)
                pubmed_articles = file_contents_tree.xpath('//PubmedArticle')
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

                self._destroy_etree(file_contents_tree)
                print(f"    took {round((time.time() - file_start_time) / 60, 2)} minutes")

            # Save the data to the PickleDB after we're done
            print("Loading conceptname->PMIDs dictionary into PickleDB...")
            for concept_name, pmid_list in conceptname_to_pmids_map.items():
                self.conceptname_to_pmids_db.set(concept_name, list({self._create_pmid_string(pmid) for pmid in pmid_list}))
            print("Saving PickleDB file...")
            self.conceptname_to_pmids_db.dump()
            print(f"Done! Building the conceptname->PMIDs database took {round(((time.time() - start) / 60) / 60, 3)} hours")

    def build_curie_to_pmids_db(self):
        # Loop through all keys in conceptname_to_pmid_db and send them to the NodeSynonymizer
        # If we get a canonical curie back for a concept name, add the concept name to the curie's list in a temp dict
        # Once we have the entire curie->conceptnames dict, go through each curie, grab each name, and in turn grab
        # their PMIDs from the conceptname_to_pmid_db; coallesce and add that curie->pmidlist info to another temp dict
        # Then dump to our final pickledb (or periodically dump)
        print(f"Still need to implement the second half of the build process!")

    # Helper methods

    @staticmethod
    def _add_mapping(key, value_to_append, mappings_dict):
        if key not in mappings_dict:
            mappings_dict[key] = []
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
    arg_parser.add_argument("pubmedDirectory", type=str)
    arg_parser.add_argument("--full", dest="full", action="store_true", default=False)
    args = arg_parser.parse_args()

    # Build the database(s)
    database_builder = NGDDatabaseBuilder(args.pubmedDirectory)
    if args.full:
        database_builder.build_conceptname_to_pmids_db()
    database_builder.build_curie_to_pmids_db()


if __name__ == '__main__':
    main()

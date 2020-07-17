#!/usr/bin/env python3
"""
This class builds a PickleDB that maps (canonicalized) curies from the NodeSynonymizer to PubMed articles (PMIDs).
There are two halves to the (full) build process:
1. Creates an intermediary file called "keyword_to_pmid.db"
     - Contains mappings from MESH term names and article "keywords" to the list of articles (PMIDs) they appear in
     - These mappings are obtained by scraping ALL of the PubMed XML files
     - This file needs updating very infrequently (i.e., only with new PubMed releases)
2. Creates the final file called "curie_to_pmid.db"
     - Contains mappings from canonicalized curies in the NodeSynonymizer to their list of associated articles (PMIDs)
     - The NodeSynonymizer is used to link curies to keywords/MESH term names (which were linked to PMIDs in step 1)
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
        self.keyword_to_pmid_db = pickledb.load("keyword_to_pmid.db", False)
        self.curie_to_pmid_db = pickledb.load("curie_to_pmid.db", False)
        self.pubmed_directory_path = pubmed_directory_path

    def build_keyword_to_pmid_db(self):
        print("Extracting keyword/meshname->PMID mappings from pubmed files...")
        start = time.time()
        pubmed_directory = os.fsencode(self.pubmed_directory_path)
        keyword_to_pmid_map = dict()
        # Go through all the downloaded pubmed files and build our dictionary of mappings
        file_names = [os.fsdecode(file) for file in os.listdir(pubmed_directory)]
        pubmed_file_names = [file_name for file_name in file_names if file_name.startswith("pubmed") and
                             file_name.endswith(".xml.gz")]
        for file_name in pubmed_file_names:
            print(f"  Starting to process file '{file_name}'... ({pubmed_file_names.index(file_name) + 1} of {len(file_names)})")
            file_start_time = time.time()
            pubmed_file = gzip.open(self.pubmed_directory_path + "/" + file_name, 'r')
            file_contents = pubmed_file.read()
            pubmed_file.close()
            parsed_file_contents = etree.fromstring(file_contents)
            pubmed_articles = parsed_file_contents.xpath('//PubmedArticle')

            # Record keyword/mesh term name -> PMID mappings found in each article in this file
            for article in pubmed_articles:
                current_pmid = article.xpath(".//MedlineCitation/PMID/text()")[0]
                mesh_heading_names = article.xpath(".//MedlineCitation/MeshHeadingList/MeshHeading/DescriptorName/text()")
                for name in mesh_heading_names:
                    if name not in keyword_to_pmid_map:
                        keyword_to_pmid_map[name] = []
                    keyword_to_pmid_map[name].append(self._create_pmid_string(current_pmid))
                keywords = article.xpath(".//MedlineCitation/KeywordList/Keyword/text()")
                for keyword in keywords:
                    if keyword not in keyword_to_pmid_map:
                        keyword_to_pmid_map[keyword] = []
                    keyword_to_pmid_map[keyword].append(self._create_pmid_string(current_pmid))
            print(f"    took {round((time.time() - file_start_time) / 60, 2)} minutes")

        # Save the data to the PickleDB after we're done
        print("Loading keyword/meshname->PMID dictionary into PickleDB...")
        for keyword, pmid_list in keyword_to_pmid_map.items():
            self.keyword_to_pmid_db.set(keyword, list(set(pmid_list)))
        print("Saving PickleDB file...")
        self.keyword_to_pmid_db.dump()
        print(f"Done! Building the keyword/meshname->PMID database took {round((time.time() - start) / 60)} minutes")

    @staticmethod
    def _create_pmid_string(pmid):
        return f"PMID:{pmid}"

    def build_curie_to_pmid_db(self):
        # TODO
        print(f"Still need to implement the second half of the build process!")


def main():
    # Load command-line arguments
    arg_parser = argparse.ArgumentParser(description="Builds pickle database of curie->PMID mappings needed for NGD")
    arg_parser.add_argument("pubmedDirectory", type=str)
    arg_parser.add_argument("--full", dest="full", action="store_true", default=False)
    args = arg_parser.parse_args()

    # Build the database(s)
    database_builder = NGDDatabaseBuilder(args.pubmedDirectory)
    if args.full:
        database_builder.build_keyword_to_pmid_db()
    database_builder.build_curie_to_pmid_db()


if __name__ == '__main__':
    main()

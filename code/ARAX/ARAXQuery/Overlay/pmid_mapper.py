#!/usr/bin/env python3
# This script loops through all the downloaded PubMed xml files and creates a PickleDB mapping each MESH term in
# 'curie_to_mesh.db' to its corresponding PMIDs.

import os
import pickledb
import gzip
import time
from lxml import etree

__author__ = 'Amy Glen'
__copyright__ = 'Oregon State University'
__credits__ = ['Stephen Ramsey', 'Amy Glen', 'Finn Womack', 'David Koslicki']
__license__ = 'MIT'
__version__ = '0.1.0'
__maintainer__ = ''
__email__ = ''
__status__ = 'Prototype'

PICKLEDB_AUTO_DUMP = False  # Note: It's MUCH faster to not use auto dump, and just dump the db at the end
MESH_PICKLEDB_FILE_NAME = "curie_to_mesh.db"
PMID_PICKLEDB_FILE_NAME = "mesh_to_pmid.db"
PUBMED_DIRECTORY_PATH = "/home/ubuntu/pubmed_files"
MESH_PREFIX = "MESH"
PMID_PREFIX = "PMID"


class PMIDMapper:
    def __init__(self):
        self.mesh_db = pickledb.load(MESH_PICKLEDB_FILE_NAME, PICKLEDB_AUTO_DUMP)
        self.pmid_db = pickledb.load(PMID_PICKLEDB_FILE_NAME, PICKLEDB_AUTO_DUMP)

    def __get_relevant_mesh_terms(self):
        print("Gathering the set of MESH terms that need to be mapped to PMIDs...")
        mapped_curies = self.mesh_db.getall()
        mesh_terms_mapped_to = set()
        for curie in mapped_curies:
            for mesh_term in self.mesh_db.get(curie):
                assert mesh_term.startswith(MESH_PREFIX)
                mesh_terms_mapped_to.add(mesh_term)
        return mesh_terms_mapped_to

    def __build_mesh_to_pmid_dict(self, set_of_mesh_terms_to_map):
        print("Extracting mappings from pubmed files...")
        pubmed_directory = os.fsencode(PUBMED_DIRECTORY_PATH)
        mesh_to_pmid_dict = dict()

        # Go through all the downloaded pubmed files and build a MESH->PMID dictionary
        for file in os.listdir(pubmed_directory):
            file_name = os.fsdecode(file)
            if file_name.startswith("pubmed") and file_name.endswith(".xml.gz"):
                print(f"    Starting to process file '{file_name}'...")
                start = time.time()

                # Read the contents of this file into a string
                pubmed_file = gzip.open(PUBMED_DIRECTORY_PATH + "/" + file_name, 'r')
                file_contents = pubmed_file.read()
                pubmed_file.close()

                parsed_file_contents = etree.fromstring(file_contents)
                pubmed_articles = parsed_file_contents.xpath('//PubmedArticle')

                # Build our giant dictionary of mesh terms to PMIDs
                for article in pubmed_articles:
                    pmid = article.xpath(".//MedlineCitation/PMID/text()")[0]
                    mesh_headings = article.xpath(".//MedlineCitation/MeshHeadingList/MeshHeading/DescriptorName/@UI")
                    mesh_terms = [MESH_PREFIX + ":" + mesh_heading for mesh_heading in mesh_headings]

                    # Map this article's mesh terms to its PMID
                    for mesh_term in mesh_terms:
                        if mesh_term in set_of_mesh_terms_to_map:
                            if mesh_term not in mesh_to_pmid_dict:
                                mesh_to_pmid_dict[mesh_term] = []
                            mesh_to_pmid_dict[mesh_term].append(PMID_PREFIX + ":" + pmid)

                print(f"           took {round((time.time() - start) / 60, 4)} minutes")

        return mesh_to_pmid_dict

    def map_mesh_terms_to_pmids(self):
        set_of_mesh_terms_to_map = self.__get_relevant_mesh_terms()
        mesh_to_pmid_dict = self.__build_mesh_to_pmid_dict(set_of_mesh_terms_to_map)

        print("Loading MESH->PMID dictionary into PickleDB...")
        for mesh_term, pmid_list in mesh_to_pmid_dict.items():
            self.pmid_db.set(mesh_term, list(set(pmid_list)))

        print("Saving PickleDB file...")
        self.pmid_db.dump()

        print("Done!")


def main():
    pm = PMIDMapper()
    pm.map_mesh_terms_to_pmids()


if __name__ == '__main__':
    main()

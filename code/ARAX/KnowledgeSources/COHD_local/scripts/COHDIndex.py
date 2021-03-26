"""This script will build a database and query an index of records for KG and COHD.

Author: Chunyu Ma
"""

import os
import sys
import re
import timeit
import argparse
import sqlite3
import pickle
import itertools

sys.path.append(os.path.dirname(os.path.abspath(__file__))+"/../../../../")
from RTXConfiguration import RTXConfiguration
RTXConfig = RTXConfiguration()
RTXConfig.live = "Production"

# import internal modules
pathlist = os.path.realpath(__file__).split(os.path.sep)
RTXindex = pathlist.index("RTX")
sys.path.append(os.path.sep.join([*pathlist[:(RTXindex + 1)], 'code', 'reasoningtool', 'QuestionAnswering']))
sys.path.append(os.path.sep.join([*pathlist[:(RTXindex + 1)], 'code', 'ARAX', 'NodeSynonymizer']))
from node_synonymizer import NodeSynonymizer

DEBUG = True


class COHDIndex:

    # Constructor
    def __init__(self):
        filepath = os.path.sep.join([*pathlist[:(RTXindex + 1)], 'code', 'ARAX', 'KnowledgeSources', 'COHD_local', 'data'])
        self.databaseLocation = filepath
        # lastest_version = "v1.0"
        # kg = 'KG2.5.2'
        # self.databaseName = f"COHDdatabase_{lastest_version}_{kg}.db"
        self.databaseName = RTXConfig.cohd_database_path.split('/')[-1]
        self.success_con = self.connect()
        self.synonymizer = NodeSynonymizer()

    # Destructor
    def __del__(self):
        self.disconnect()

    # Create and store a database connection
    def connect(self):

        database = f"{self.databaseLocation}/{self.databaseName}"

        if os.path.exists(database):
            self.connection = sqlite3.connect(database)
            print("INFO: Connecting to database", flush=True)
            return True
        else:
            # required_files = ['single_concept_counts.txt', 'patient_count.txt', 'domain_pair_concept_counts.txt', 'paired_concept_counts_associations.txt', 'domain_concept_counts.txt', 'concepts.txt', 'dataset.txt', 'preferred_synonyms_kg2_5_2_with_concepts.pkl']
            # has_files = [f for f in os.listdir(self.databaseLocation) if os.path.isfile(os.path.join(self.databaseLocation, f))]
            # for file in required_files:
            #     if file in has_files:
            #         pass
            #     else:
            #         print(f"Error: no file '{file}' in {self.databaseLocation}! Please make sure these files {required_files} exist before build database.", flush=True)
            #         return False

            # delete the old version of COHD database
            # old_version_database = "COHDdatabase_v1.0.db"
            # if os.path.exists(f"{self.databaseLocation}/{old_version_database}"):
            #     os.remove(f"{self.databaseLocation}/{old_version_database}")
            # copy the database file to local if it doesn't exist
            #os.system(f"scp rtxconfig@arax.ncats.io:/data/orangeboard/databases/KG2.3.4/{self.databaseName} {database}")
            os.system(f"scp {RTXConfig.cohd_database_username}@{RTXConfig.cohd_database_host}:{RTXConfig.cohd_database_path} {database}")

            self.connection = sqlite3.connect(database)
            print("INFO: Connecting to database", flush=True)
            return True

    # Destroy the database connection
    def disconnect(self):

        if self.success_con is True:
            self.connection.commit()
            self.connection.close()
            print("INFO: Disconnecting from database", flush=True)
            self.success_con = False
        else:
            print("Info: No database was connected! So skip disconnecting from database.", flush=True)
            return

    # Delete and create the tables
    def create_tables(self):

        return
        # if self.success_con is True:
        #     print("INFO: Creating database " + self.databaseName, flush=True)
        #     self.connection.execute(f"DROP TABLE IF EXISTS CURIE_TO_OMOP_MAPPING")
        #     self.connection.execute(f"CREATE TABLE CURIE_TO_OMOP_MAPPING( preferred_curie VARCHAR(255), concept_id INT )")
        #     self.connection.execute(f"DROP TABLE IF EXISTS SINGLE_CONCEPT_COUNTS")
        #     self.connection.execute(f"CREATE TABLE SINGLE_CONCEPT_COUNTS( dataset_id TINYINT, concept_id INT, concept_count INT, concept_prevalence FLOAT )")
        #     self.connection.execute(f"DROP TABLE IF EXISTS CONCEPTS")
        #     self.connection.execute(f"CREATE TABLE CONCEPTS( concept_id INT PRIMARY KEY, concept_name VARCHAR(255), domain_id VARCHAR(255), vocabulary_id VARCHAR(255), concept_class_id VARCHAR(255), concept_code VARCHAR(255) )")
        #     self.connection.execute(f"DROP TABLE IF EXISTS PATIENT_COUNT")
        #     self.connection.execute(f"CREATE TABLE PATIENT_COUNT( dataset_id TINYINT PRIMARY KEY, count INT)")
        #     self.connection.execute(f"DROP TABLE IF EXISTS DATASET")
        #     self.connection.execute(f"CREATE TABLE DATASET( dataset_id TINYINT PRIMARY KEY, dataset_name VARCHAR(255), dataset_description VARCHAR(255))")
        #     self.connection.execute(f"DROP TABLE IF EXISTS DOMAIN_CONCEPT_COUNTS")
        #     self.connection.execute(f"CREATE TABLE DOMAIN_CONCEPT_COUNTS( dataset_id TINYINT, domain_id VARCHAR(255), count INT)")
        #     self.connection.execute(f"DROP TABLE IF EXISTS DOMAIN_PAIR_CONCEPT_COUNTS")
        #     self.connection.execute(f"CREATE TABLE DOMAIN_PAIR_CONCEPT_COUNTS( dataset_id TINYINT, domain_id_1 VARCHAR(255), domain_id_2 VARCHAR(255), count INT)")
        #     self.connection.execute(f"DROP TABLE IF EXISTS PAIRED_CONCEPT_COUNTS_ASSOCIATIONS")
        #     self.connection.execute(f"CREATE TABLE PAIRED_CONCEPT_COUNTS_ASSOCIATIONS( concept_pair_id VARCHAR(255), dataset_id TINYINT, concept_id_1 INT, concept_id_2 INT, concept_count INT, concept_prevalence FLOAT, chi_square_t FLOAT, chi_square_p FLOAT, expected_count FLOAT, ln_ratio FLOAT, rel_freq_1 FLOAT, rel_freq_2 FLOAT)")

        #     print(f"INFO: Creating tables is completed", flush=True)

    ## Populate the tables
    def populate_table(self):

        return
        # if self.success_con is True:
        #     # read all tables from COHD database to local database
        #     COHD_database_files = ['single_concept_counts.txt', 'patient_count.txt', 'domain_pair_concept_counts.txt', 'domain_concept_counts.txt', 'concepts.txt', 'dataset.txt']

        #     for file_name in COHD_database_files:

        #         current_table_name = file_name.replace('.txt', '').upper()
        #         print(f"INFO: Populating table {current_table_name}", flush=True)
        #         with open(f"{self.databaseLocation}/{file_name}", 'r') as file:
        #             content_list = file.readlines()
        #             col_name = content_list.pop(0)
        #             insert_command1 = f"INSERT INTO {current_table_name}("
        #             insert_command2 = f" values ("
        #             for col in col_name.strip().split("\t"):
        #                 insert_command1 = insert_command1 + f"{col},"
        #                 insert_command2 = insert_command2 + f"?,"

        #             insert_command = insert_command1 + ")" + insert_command2 + ")"
        #             insert_command = insert_command.replace(',)', ')')

        #             if DEBUG:
        #                 print(insert_command, flush=True)
        #                 print(tuple(content_list[0].strip().split("\t")), flush=True)

        #             for line in content_list:
        #                 line = tuple(line.strip().split("\t"))
        #                 self.connection.execute(insert_command, line)

        #             self.connection.commit()

        #     paired_file = 'paired_concept_counts_associations.txt'
        #     current_table_name = paired_file.replace('.txt', '').upper()
        #     print(f"INFO: Populating table {current_table_name}", flush=True)
        #     with open(f"{self.databaseLocation}/{paired_file}", 'r') as file:
        #         content_list = file.readlines()
        #         col_name = content_list.pop(0)
        #         insert_command1 = f"INSERT INTO {current_table_name}(concept_pair_id,"
        #         insert_command2 = f" values (?,"
        #         for col in col_name.strip().split("\t"):
        #             insert_command1 = insert_command1 + f"{col},"
        #             insert_command2 = insert_command2 + f"?,"

        #         insert_command = insert_command1 + ")" + insert_command2 + ")"
        #         insert_command = insert_command.replace(',)', ')')

        #     if DEBUG:
        #         print(insert_command, flush=True)
        #         content_col = content_list[0].strip().split("\t")
        #         concept_pair_id = f"{content_col[1]}_{content_col[2]}"
        #         content_col.insert(0, concept_pair_id)
        #         print(tuple(content_col), flush=True)

        #     for line in content_list:
        #         content_col = line.strip().split("\t")
        #         concept_pair_id = f"{content_col[1]}_{content_col[2]}"
        #         content_col.insert(0, concept_pair_id)
        #         record = tuple(content_col)
        #         self.connection.execute(insert_command, record)

        #     self.connection.commit()

        #     # read KG1 and KG2 mapping
        #     # with open(f"{self.databaseLocation}/synonyms_kg2_with_concepts.pkl", "rb") as file:
        #     #     kg_mapping = pickle.load(file)

        #     # with open(f"{self.databaseLocation}/synonyms_kg1_with_concepts.pkl", "rb") as file:
        #     #     kg1_mapping = pickle.load(file)
        #     # for key in kg1_mapping:
        #     #     if key not in kg_mapping:
        #     #         kg_mapping[key] = kg1_mapping[key]
        #     with open(f"{self.databaseLocation}/preferred_synonyms_kg2_5_2_with_concepts.pkl", "rb") as file:
        #         kg = pickle.load(file)

        #     insert_command = 'INSERT INTO CURIE_TO_OMOP_MAPPING(preferred_curie,concept_id) values (?,?)'
        #     count = 0
        #     total_key = [key for key in kg if len(kg[key]['concept_ids']) != 0]

        #     print(f"INFO: Populating table CURIE_TO_OMOP_MAPPING", flush=True)
        #     if DEBUG:
        #         key = total_key[0]
        #         records = list(itertools.product([key], list(kg[key]['concept_ids'])))
        #         print(records, flush=True)

        #     for key in total_key:
        #         if len(kg[key]['concept_ids']) > 0:
        #             count = count + 1
        #             records = list(itertools.product([key], list(kg[key]['concept_ids'])))
        #             self.connection.executemany(insert_command, records)

        #             if count % 10000 == 0:
        #                 self.connection.commit()
        #                 percentage = round((count * 100.0 / len(total_key)), 2)
        #                 print(str(percentage) + "%..", end='', flush=True)

        #     self.connection.commit()
        #     percentage = round((count * 100.0 / len(total_key)), 2)
        #     print(str(percentage) + "%..", end='', flush=True)

        #     print(f"INFO: Populating tables is completed", flush=True)

    ## create indexes for the tables
    def create_indexes(self):

        return
        # if self.success_con is True:
        #     print(f"INFO: Creating INDEXes on CURIE_TO_OMOP_MAPPING", flush=True)
        #     self.connection.execute(f"CREATE INDEX idx_CURIE_TO_OMOP_MAPPING_preferred_curie ON CURIE_TO_OMOP_MAPPING(preferred_curie)")
        #     self.connection.execute(f"CREATE INDEX idx_CURIE_TO_OMOP_MAPPING_concept_id ON CURIE_TO_OMOP_MAPPING(concept_id)")

        #     print(f"INFO: Creating INDEXes on SINGLE_CONCEPT_COUNTS", flush=True)
        #     self.connection.execute(f"CREATE INDEX idx_SINGLE_CONCEPT_COUNTS_dataset_id ON SINGLE_CONCEPT_COUNTS(dataset_id)")
        #     self.connection.execute(f"CREATE INDEX idx_SINGLE_CONCEPT_COUNTS_concept_id ON SINGLE_CONCEPT_COUNTS(concept_id)")

        #     print(f"INFO: Creating INDEXes on CONCEPTS", flush=True)
        #     self.connection.execute(f"CREATE INDEX idx_CONCEPTS_concept_id ON CONCEPTS(concept_id)")

        #     print(f"INFO: Creating INDEXes on PAIRED_CONCEPT_COUNTS_ASSOCIATIONS", flush=True)
        #     self.connection.execute(f"CREATE INDEX idx_PAIRED_CONCEPT_COUNTS_ASSOCIATIONS_dataset_id ON PAIRED_CONCEPT_COUNTS_ASSOCIATIONS(dataset_id)")
        #     self.connection.execute(f"CREATE INDEX idx_PAIRED_CONCEPT_COUNTS_ASSOCIATIONS_concept_pair_id ON PAIRED_CONCEPT_COUNTS_ASSOCIATIONS(concept_pair_id)")
        #     self.connection.execute(f"CREATE INDEX idx_PAIRED_CONCEPT_COUNTS_ASSOCIATIONS_concept_id_1 ON PAIRED_CONCEPT_COUNTS_ASSOCIATIONS(concept_id_1)")
        #     self.connection.execute(f"CREATE INDEX idx_PAIRED_CONCEPT_COUNTS_ASSOCIATIONS_concept_id_2 ON PAIRED_CONCEPT_COUNTS_ASSOCIATIONS(concept_id_2)")

        #     print(f"INFO: Creating INDEXes is completed", flush=True)

    def get_concept_ids(self, curie):
        """Search for OMOP concept ids by curie id.

        Args:
            curie (required, str): Compacy URI (CURIE) of the concept to map, e.g., "DOID:8398"

        Returns:
            list: a list which contains OMOP concepts for the given curie id, or empty list if no
            example:
                [75617, 80180, 1570333, 4025957, 4035441, 4079750, 4083695, 4083696, 4110738, 36516824, 36569386, 45618044]
        """
        if isinstance(curie, str):
            preferred_curie = self.synonymizer.get_canonical_curies(curie)[curie]
            if preferred_curie is None:
                print("Can't convert {curie} to preferred curie in get_concept_ids", flush=True)
                return []
            else:
                preferred_curie = preferred_curie['preferred_curie']
        else:
            print("The 'curie' in get_concept_ids should be a str", flush=True)
            return []

        results_list = []
        cursor = self.connection.cursor()
        cursor.execute(f"select distinct preferred_curie, concept_id from CURIE_TO_OMOP_MAPPING where preferred_curie='{preferred_curie}';")
        res = cursor.fetchall()
        if len(res) == 0:
            return []
        else:
            results_list = [row[1] for row in res]
            return results_list

    def get_curies_from_concept_id(self, concept_id):
        """Search for curie ids by OMOP concept ids.

        Args:
            concept_id (required, int): an OMOP concept id, e.g., 192855

        Returns:
            list: a list which contains curies for each given OMOP concept id, or None if no
            example:
                ['CUI:C0154091', 'CUI:C0855181', 'NCIT:C3644', 'MONDO:0004703', 'DOID:9053']
        """
        if isinstance(concept_id, int):
            pass
        else:
            print("The 'concept_id' in get_curies_from_concept_id should be an int", flush=True)
            return []

        results_list = []
        cursor = self.connection.cursor()
        cursor.execute(f"select distinct preferred_curie, concept_id from CURIE_TO_OMOP_MAPPING where concept_id={concept_id};")
        res = cursor.fetchall()
        if len(res) != 0:
            results_list = list(set([record[0] for record in res]))
        else:
            results_list = []

        return results_list

    def get_paired_concept_freq(self, concept_id_1=[], concept_id_2=[], concept_id_pair=None, dataset_id=1):
        """Retrieve observed clinical frequencies of a pair of concepts.

        Args:
            concept_id_1 (optional, list): an OMOP id, e.g., [192855] or [192855, 8507]
            concept_id_2 (optional, list): an OMOP id, e.g., [2008271] or [2008271, 939259] If concept_id_2 is unspecified, then this method
                will return all pairs of concepts with concept_id_1.
            concept_id_pair (optional, str or list): the concatenation of two concept ids, e.g. "192855_2008271" or ["192855_2008271","8507_939259"]
            dataset_id (optional, int): The dataset_id of the dataset to query. Default dataset is the 5-year dataset e.g. 1,2,3

        Returns:
            array: an sorted(decreasing concept_frequency) array of dictionaries which contains a numeric frequency and a numeric concept count
            example:
            [
                {
                    "concept_count": 10,
                    "concept_frequency": 0.000005585247351056813,
                    "concept_id_1": 192855,
                    "concept_id_2": 2008271,
                    "dataset_id": 1
                }
            ]
        """
        if concept_id_pair is None:
            if not isinstance(concept_id_1, list):
                print("Please provide either 'concept_id_1' or 'concept_id_pair'. The 'concept_id_1' in get_paired_concept_freq should be a list", flush=True)
                return []
            else:
                if len(concept_id_1) == 0:
                    print("The 'concept_id_1' in get_paired_concept_freq should not be a empty list", flush=True)
                    return []

            if not isinstance(concept_id_2, list):
                print("The 'concept_id_2' in get_paired_concept_freq should be a list", flush=True)
                return []
        else:
            if isinstance(concept_id_pair, str):
                concept_id_pair1 = concept_id_pair
                concept_id_pair2 = f"{concept_id_pair.split('_')[1]}_{concept_id_pair.split('_')[0]}"
            elif isinstance(concept_id_pair, list):
                if len(concept_id_pair) == 0:
                    print("The 'concept_id_pair' in get_paired_concept_freq is an empty list", flush=True)
                    return []
                else:
                    concept_id_pair1 = concept_id_pair
                    concept_id_pair2 = [f"{pair.split('_')[1]}_{pair.split('_')[0]}" for pair in concept_id_pair]
            else:
                print("The 'concept_id_pair' in get_paired_concept_freq should be a str or a list", flush=True)
                return []

        if not isinstance(dataset_id, int):
            print("The 'dataset_id' in get_paired_concept_freq should be an int", flush=True)
            return []
        else:
            if dataset_id == 1 or dataset_id == 2 or dataset_id == 3:
                pass
            else:
                print("The 'dataset_id' in get_paired_concept_freq should be 1, 2 or 3", flush=True)
                return []

        results_array = []
        cursor = self.connection.cursor()
        if concept_id_pair is None:
            if len(concept_id_2) == 0:
                if len(concept_id_1) == 1:
                    cursor.execute(f"select distinct dataset_id,concept_id_1,concept_id_2,concept_count,concept_prevalence from PAIRED_CONCEPT_COUNTS_ASSOCIATIONS where concept_id_1={concept_id_1[0]};")
                else:
                    cursor.execute(f"select distinct dataset_id,concept_id_1,concept_id_2,concept_count,concept_prevalence from PAIRED_CONCEPT_COUNTS_ASSOCIATIONS where concept_id_1 in {tuple(set(concept_id_1))};")
                res = cursor.fetchall()
                if len(res) == 0:
                    if len(concept_id_1) == 1:
                        cursor.execute(f"select distinct dataset_id,concept_id_2,concept_id_1,concept_count,concept_prevalence from PAIRED_CONCEPT_COUNTS_ASSOCIATIONS where concept_id_2={concept_id_1[0]};")
                    else:
                        cursor.execute(f"select distinct dataset_id,concept_id_2,concept_id_1,concept_count,concept_prevalence from PAIRED_CONCEPT_COUNTS_ASSOCIATIONS where concept_id_2 in {tuple(set(concept_id_1))};")
                    res = cursor.fetchall()
                    if len(res) == 0:
                        pass
                    else:
                        for row in res:
                            if row[0] == dataset_id:
                                results_array.append({'dataset_id': row[0],
                                                        'concept_id_1': row[1],
                                                        'concept_id_2': row[2],
                                                        'concept_count': row[3],
                                                        'concept_frequency': row[4]})
                else:
                    for row in res:
                        if row[0] == dataset_id:
                            results_array.append({'dataset_id': row[0],
                                                    'concept_id_1': row[1],
                                                    'concept_id_2': row[2],
                                                    'concept_count': row[3],
                                                    'concept_frequency': row[4]})

                    if len(concept_id_1) == 1:
                        cursor.execute(f"select distinct dataset_id,concept_id_2,concept_id_1,concept_count,concept_prevalence from PAIRED_CONCEPT_COUNTS_ASSOCIATIONS where concept_id_2={concept_id_1[0]};")
                    else:
                        cursor.execute(f"select distinct dataset_id,concept_id_2,concept_id_1,concept_count,concept_prevalence from PAIRED_CONCEPT_COUNTS_ASSOCIATIONS where concept_id_2 in {tuple(set(concept_id_1))};")
                    res = cursor.fetchall()
                    if len(res) == 0:
                        pass
                    else:
                        for row in res:
                            if row[0] == dataset_id:
                                results_array.append({'dataset_id': row[0],
                                                        'concept_id_1': row[1],
                                                        'concept_id_2': row[2],
                                                        'concept_count': row[3],
                                                        'concept_frequency': row[4]})
            else:
                if len(concept_id_1) == 1 and len(concept_id_2) == 1:
                    cursor.execute(f"select distinct dataset_id,concept_id_1,concept_id_2,concept_count,concept_prevalence from PAIRED_CONCEPT_COUNTS_ASSOCIATIONS where concept_id_1={concept_id_1[0]} and concept_id_2={concept_id_2[0]};")
                elif len(concept_id_1) == 1:
                    cursor.execute(f"select distinct dataset_id,concept_id_1,concept_id_2,concept_count,concept_prevalence from PAIRED_CONCEPT_COUNTS_ASSOCIATIONS where concept_id_1={concept_id_1[0]} and concept_id_2 in {tuple(set(concept_id_2))};")
                elif len(concept_id_2) == 1:
                    cursor.execute(f"select distinct dataset_id,concept_id_1,concept_id_2,concept_count,concept_prevalence from PAIRED_CONCEPT_COUNTS_ASSOCIATIONS where concept_id_1 in {tuple(set(concept_id_1))} and concept_id_2={concept_id_2[0]};")
                else:
                    cursor.execute(f"select distinct dataset_id,concept_id_1,concept_id_2,concept_count,concept_prevalence from PAIRED_CONCEPT_COUNTS_ASSOCIATIONS where concept_id_1 in {tuple(set(concept_id_1))} and concept_id_2 in {tuple(set(concept_id_2))};")
                res = cursor.fetchall()
                if len(res) == 0:
                    if len(concept_id_1) == 1 and len(concept_id_2) == 1:
                        cursor.execute(f"select distinct dataset_id,concept_id_2,concept_id_1,concept_count,concept_prevalence from PAIRED_CONCEPT_COUNTS_ASSOCIATIONS where concept_id_2={concept_id_1[0]} and concept_id_1={concept_id_2[0]};")
                    elif len(concept_id_1) == 1:
                        cursor.execute(f"select distinct dataset_id,concept_id_2,concept_id_1,concept_count,concept_prevalence from PAIRED_CONCEPT_COUNTS_ASSOCIATIONS where concept_id_2={concept_id_1[0]} and concept_id_1 in {tuple(set(concept_id_2))};")
                    elif len(concept_id_2) == 1:
                        cursor.execute(f"select distinct dataset_id,concept_id_2,concept_id_1,concept_count,concept_prevalence from PAIRED_CONCEPT_COUNTS_ASSOCIATIONS where concept_id_2 in {tuple(set(concept_id_1))} and concept_id_1={concept_id_2[0]};")
                    else:
                        cursor.execute(f"select distinct dataset_id,concept_id_2,concept_id_1,concept_count,concept_prevalence from PAIRED_CONCEPT_COUNTS_ASSOCIATIONS where concept_id_2 in {tuple(set(concept_id_1))} and concept_id_1 in {tuple(set(concept_id_2))};")
                    res = cursor.fetchall()
                    if len(res) == 0:
                        pass
                    else:
                        for row in res:
                            if row[0] == dataset_id:
                                results_array.append({'dataset_id': row[0],
                                                        'concept_id_1': row[1],
                                                        'concept_id_2': row[2],
                                                        'concept_count': row[3],
                                                        'concept_frequency': row[4]})
                else:
                    for row in res:
                        if row[0] == dataset_id:
                            results_array.append({'dataset_id': row[0],
                                                    'concept_id_1': row[1],
                                                    'concept_id_2': row[2],
                                                    'concept_count': row[3],
                                                    'concept_frequency': row[4]})

                    if len(concept_id_1) == 1 and len(concept_id_2) == 1:
                        cursor.execute(f"select distinct dataset_id,concept_id_2,concept_id_1,concept_count,concept_prevalence from PAIRED_CONCEPT_COUNTS_ASSOCIATIONS where concept_id_2={concept_id_1[0]} and concept_id_1={concept_id_2[0]};")
                    elif len(concept_id_1) == 1:
                        cursor.execute(f"select distinct dataset_id,concept_id_2,concept_id_1,concept_count,concept_prevalence from PAIRED_CONCEPT_COUNTS_ASSOCIATIONS where concept_id_2={concept_id_1[0]} and concept_id_1 in {tuple(set(concept_id_2))};")
                    elif len(concept_id_2) == 1:
                        cursor.execute(f"select distinct dataset_id,concept_id_2,concept_id_1,concept_count,concept_prevalence from PAIRED_CONCEPT_COUNTS_ASSOCIATIONS where concept_id_2 in {tuple(set(concept_id_1))} and concept_id_1={concept_id_2[0]};")
                    else:
                        cursor.execute(f"select distinct dataset_id,concept_id_2,concept_id_1,concept_count,concept_prevalence from PAIRED_CONCEPT_COUNTS_ASSOCIATIONS where concept_id_2 in {tuple(set(concept_id_1))} and concept_id_1 in {tuple(set(concept_id_2))};")
                    res = cursor.fetchall()
                    if len(res) == 0:
                        pass
                    else:
                        for row in res:
                            if row[0] == dataset_id:
                                results_array.append({'dataset_id': row[0],
                                                        'concept_id_1': row[1],
                                                        'concept_id_2': row[2],
                                                        'concept_count': row[3],
                                                        'concept_frequency': row[4]})
        else:
            if isinstance(concept_id_pair, str):
                cursor.execute(f"select distinct dataset_id,concept_id_1,concept_id_2,concept_count,concept_prevalence from PAIRED_CONCEPT_COUNTS_ASSOCIATIONS where concept_pair_id='{concept_id_pair1}';")
                res = cursor.fetchall()
                if len(res) == 0:
                    cursor.execute(f"select distinct dataset_id,concept_id_2,concept_id_1,concept_count,concept_prevalence from PAIRED_CONCEPT_COUNTS_ASSOCIATIONS where concept_pair_id='{concept_id_pair2}';")
                    res = cursor.fetchall()
                    if len(res) == 0:
                        pass
                    else:
                        for row in res:
                            if row[0] == dataset_id:
                                results_array.append({'dataset_id': row[0],
                                                        'concept_id_1': row[1],
                                                        'concept_id_2': row[2],
                                                        'concept_count': row[3],
                                                        'concept_frequency': row[4]})
                else:
                    for row in res:
                        if row[0] == dataset_id:
                            results_array.append({'dataset_id': row[0],
                                                    'concept_id_1': row[1],
                                                    'concept_id_2': row[2],
                                                    'concept_count': row[3],
                                                    'concept_frequency': row[4]})

                    cursor.execute(f"select distinct dataset_id,concept_id_2,concept_id_1,concept_count,concept_prevalence from PAIRED_CONCEPT_COUNTS_ASSOCIATIONS where concept_pair_id='{concept_id_pair2}';")
                    res = cursor.fetchall()
                    if len(res) == 0:
                        pass
                    else:
                        for row in res:
                            if row[0] == dataset_id:
                                results_array.append({'dataset_id': row[0],
                                                        'concept_id_1': row[1],
                                                        'concept_id_2': row[2],
                                                        'concept_count': row[3],
                                                        'concept_frequency': row[4]})
            else:
                if len(concept_id_pair) == 1:
                    cursor.execute(f"select distinct dataset_id,concept_id_1,concept_id_2,concept_count,concept_prevalence from PAIRED_CONCEPT_COUNTS_ASSOCIATIONS where concept_pair_id='{concept_id_pair1[0]}';")
                else:
                    cursor.execute(f"select distinct dataset_id,concept_id_1,concept_id_2,concept_count,concept_prevalence from PAIRED_CONCEPT_COUNTS_ASSOCIATIONS where concept_pair_id in {tuple(set(concept_id_pair1))};")
                res = cursor.fetchall()
                if len(res) == 0:
                    if len(concept_id_pair) == 1:
                        cursor.execute(f"select distinct dataset_id,concept_id_2,concept_id_1,concept_count,concept_prevalence from PAIRED_CONCEPT_COUNTS_ASSOCIATIONS where concept_pair_id='{concept_id_pair2[0]}';")
                    else:
                        cursor.execute(f"select distinct dataset_id,concept_id_2,concept_id_1,concept_count,concept_prevalence from PAIRED_CONCEPT_COUNTS_ASSOCIATIONS where concept_pair_id in {tuple(set(concept_id_pair2))};")
                    res = cursor.fetchall()
                    if len(res) == 0:
                        pass
                    else:
                        for row in res:
                            if row[0] == dataset_id:
                                results_array.append({'dataset_id': row[0],
                                                        'concept_id_1': row[1],
                                                        'concept_id_2': row[2],
                                                        'concept_count': row[3],
                                                        'concept_frequency': row[4]})
                else:
                    for row in res:
                        if row[0] == dataset_id:
                            results_array.append({'dataset_id': row[0],
                                                    'concept_id_1': row[1],
                                                    'concept_id_2': row[2],
                                                    'concept_count': row[3],
                                                    'concept_frequency': row[4]})

                    if len(concept_id_pair) == 1:
                        cursor.execute(f"select distinct dataset_id,concept_id_2,concept_id_1,concept_count,concept_prevalence from PAIRED_CONCEPT_COUNTS_ASSOCIATIONS where concept_pair_id='{concept_id_pair2[0]}';")
                    else:
                        cursor.execute(f"select distinct dataset_id,concept_id_2,concept_id_1,concept_count,concept_prevalence from PAIRED_CONCEPT_COUNTS_ASSOCIATIONS where concept_pair_id in {tuple(set(concept_id_pair2))};")
                    res = cursor.fetchall()
                    if len(res) == 0:
                        pass
                    else:
                        for row in res:
                            if row[0] == dataset_id:
                                results_array.append({'dataset_id': row[0],
                                                        'concept_id_1': row[1],
                                                        'concept_id_2': row[2],
                                                        'concept_count': row[3],
                                                        'concept_frequency': row[4]})

        if len(results_array) != 0:
            results_array = sorted(results_array, key=lambda x: x['concept_frequency'], reverse=True)

        return results_array

    def get_individual_concept_freq(self, concept_id, dataset_id=1):
        """Retrieve observed clinical frequencies of individual concepts.

        Args:
            concept_id (required, int): an OMOP id, e.g., 192855
            dataset_id (optional, int): The dataset_id of the dataset to query. Default dataset is the 5-year dataset e.g. 1,2,3

        Returns:
            dictionary: a dictionary which contains a numeric frequency and a numeric concept count
            example:
                {
                    "concept_count": 368,
                    "concept_frequency": 0.0002055371025188907,
                    "concept_id": 192855,
                    "dataset_id": 1
                }
        """
        if not isinstance(concept_id, int):
            print("The 'concept_id' in get_individual_concept_freq should be an int", flush=True)
            return {}

        if not isinstance(dataset_id, int):
            print("The 'dataset_id' in get_individual_concept_freq should be an int", flush=True)
            return {}
        else:
            if dataset_id == 1 or dataset_id == 2 or dataset_id == 3:
                pass
            else:
                print("The 'dataset_id' in get_individual_concept_freq should be 1, 2 or 3", flush=True)
                return {}

        results_dict = {}
        cursor = self.connection.cursor()
        cursor.execute(f"select distinct * from SINGLE_CONCEPT_COUNTS where concept_id = {concept_id} and dataset_id = {dataset_id};")
        res = cursor.fetchone()

        if len(res) == 0:
            pass
        else:
            results_dict["dataset_id"] = res[0]
            results_dict["concept_id"] = res[1]
            results_dict["concept_count"] = res[2]
            results_dict["concept_frequency"] = res[3]

        return results_dict

    def get_associated_concept_domain_freq(self, concept_id, domain, dataset_id=1):
        """Retrieve observed clinical frequencies of all pairs of concepts given a concept id restricted by domain of the associated concept_id.

        Args:
            concept_id (required, int): an OMOP id, e.g., 192855
            domain (required, str): An OMOP domain id, e.g., "Condition", "Drug", "Procedure", etc.
            dataset_id (optional, int): The dataset_id of the dataset to query. Default dataset is the 5-year dataset (1).

        Returns:
            array: an array which contains frequency dictionaries, or an empty array if no data obtained
            example:
            [
                {
                    "associated_concept_id": 2213283,
                    "associated_concept_name": "Level IV - Surgical pathology, gross and microscopic examination Abortion - spontaneous/missed Artery, biopsy Bone marrow, biopsy Bone exostosis Brain/meninges, other than for tumor resection Breast, biopsy, not requiring microscopic evaluation of surgica",
                    "associated_domain_id": "Procedure",
                    "concept_count": 302,
                    "concept_frequency": 0.00016867447000191573,
                    "concept_id": 192855,
                    "dataset_id": 1
                },
                {
                    "associated_concept_id": 2211361,
                    "associated_concept_name": "Radiologic examination, chest, 2 views, frontal and lateral",
                    "associated_domain_id": "Procedure",
                    "concept_count": 257,
                    "concept_frequency": 0.00014354085692216007,
                    "concept_id": 192855,
                    "dataset_id": 1
                },
                ...
            ]
        """
        if not isinstance(concept_id, int):
            print("The 'concept_id' in get_associated_concept_domain_freq should be an int", flush=True)
            return []

        if not isinstance(domain, str):
            print("The 'domain' in get_associated_concept_domain_freq should be a str", flush=True)
            return []

        if not isinstance(dataset_id, int):
            print("The 'dataset_id' in get_associated_concept_domain_freq should be an int", flush=True)
            return []
        else:
            if dataset_id == 1 or dataset_id == 2 or dataset_id == 3:
                pass
            else:
                print("The 'dataset_id' in get_associated_concept_domain_freq should be 1, 2 or 3", flush=True)
                return []

        results_array = []
        cursor = self.connection.cursor()
        cursor.execute(f"select distinct p.dataset_id,p.concept_id_1,p.concept_id_2,p.concept_count,p.concept_prevalence,c.concept_name,c.domain_id from PAIRED_CONCEPT_COUNTS_ASSOCIATIONS p inner join CONCEPTS c on p.concept_id_2 = c.concept_id where p.concept_id_1 = {concept_id} and c.domain_id = '{domain}';")
        res = cursor.fetchall()

        if len(res) == 0:
            cursor.execute(f"select distinct p.dataset_id,p.concept_id_1,p.concept_id_2,p.concept_count,p.concept_prevalence,c.concept_name,c.domain_id from PAIRED_CONCEPT_COUNTS_ASSOCIATIONS p inner join CONCEPTS c on p.concept_id_1 = c.concept_id where p.concept_id_2 = {concept_id} and c.domain_id = '{domain}';")
            res = cursor.fetchall()
            if len(res) == 0:
                pass
            else:
                all_assoct = [row for row in res if row[0] == dataset_id]
                if len(all_assoct) == 0:
                    pass
                else:
                    for row in all_assoct:
                        results_array.append({'associated_concept_id': row[1],
                                                'associated_concept_name': row[5],
                                                'associated_domain_id': row[6],
                                                'concept_count': row[3],
                                                'concept_frequency': row[4],
                                                'concept_id': row[2],
                                                'dataset_id': row[0]})
        else:
            all_assoct = [row for row in res if row[0] == dataset_id]
            if len(all_assoct) == 0:
                cursor.execute(f"select distinct p.dataset_id,p.concept_id_1,p.concept_id_2,p.concept_count,p.concept_prevalence,c.concept_name,c.domain_id from PAIRED_CONCEPT_COUNTS_ASSOCIATIONS p inner join CONCEPTS c on p.concept_id_1 = c.concept_id where p.concept_id_2 = {concept_id} and c.domain_id = '{domain}';")
                res = cursor.fetchall()
                if len(res) == 0:
                    pass
                else:
                    all_assoct = [row for row in res if row[0] == dataset_id]
                    if len(all_assoct) == 0:
                        pass
                    else:
                        for row in all_assoct:
                            results_array.append({'associated_concept_id': row[1],
                                                    'associated_concept_name': row[5],
                                                    'associated_domain_id': row[6],
                                                    'concept_count': row[3],
                                                    'concept_frequency': row[4],
                                                    'concept_id': row[2],
                                                    'dataset_id': row[0]})
            else:
                for row in all_assoct:
                    results_array.append({'associated_concept_id': row[2],
                                            'associated_concept_name': row[5],
                                            'associated_domain_id': row[6],
                                            'concept_count': row[3],
                                            'concept_frequency': row[4],
                                            'concept_id': row[1],
                                            'dataset_id': row[0]})

                cursor.execute(f"select distinct p.dataset_id,p.concept_id_1,p.concept_id_2,p.concept_count,p.concept_prevalence,c.concept_name,c.domain_id from PAIRED_CONCEPT_COUNTS_ASSOCIATIONS p inner join CONCEPTS c on p.concept_id_1 = c.concept_id where p.concept_id_2 = {concept_id} and c.domain_id = '{domain}';")
                res = cursor.fetchall()
                if len(res) == 0:
                    pass
                else:
                    all_assoct = [row for row in res if row[0] == dataset_id]
                    if len(all_assoct) == 0:
                        pass
                    else:
                        for row in all_assoct:
                            results_array.append({'associated_concept_id': row[1],
                                                    'associated_concept_name': row[5],
                                                    'associated_domain_id': row[6],
                                                    'concept_count': row[3],
                                                    'concept_frequency': row[4],
                                                    'concept_id': row[2],
                                                    'dataset_id': row[0]})

        return results_array

    def get_concepts(self, concept_ids):
        """Concept definitions from concept ID returning the OMOP concept names and domains for the given list of concept IDs.

        Args:
            concept_ids (required, int or list): concept id array,  e.g., 192855 or [192855, 2008271]

        Returns:
            array: an array which contains concept name, domain id and etc., or an empty array if no data obtained
            example:
            [
                {
                    "concept_class_id": "Clinical Finding",
                    "concept_code": "92546004",
                    "concept_id": 192855,
                    "concept_name": "Cancer in situ of urinary bladder",
                    "domain_id": "Condition",
                    "vocabulary_id": "SNOMED"
                },
                {
                    "concept_class_id": "4-dig billing code",
                    "concept_code": "99.25",
                    "concept_id": 2008271,
                    "concept_name": "Injection or infusion of cancer chemotherapeutic substance",
                    "domain_id": "Procedure",
                    "vocabulary_id": "ICD9Proc"
                },
                ...
            ]
        """
        if isinstance(concept_ids, int):
            pass
        elif isinstance(concept_ids, list):
            if len(concept_ids) != 0:
                pass
            else:
                print("The 'concept_ids' in get_concepts is an empty list", flush=True)
                return []
        else:
            print("The 'concept_ids' in get_concepts should be an int or a list", flush=True)
            return []

        results_array = []
        cursor = self.connection.cursor()
        if isinstance(concept_ids, int):
            cursor.execute(f"select distinct * from CONCEPTS where concept_id={concept_ids};")
            res = cursor.fetchone()
            if len(res) != 0:
                results_array.append({'concept_class_id': res[4],
                                        'concept_code': res[5],
                                        'concept_id': res[0],
                                        'concept_name': res[1],
                                        'domain_id': res[2],
                                        'vocabulary_id': res[3]})
        else:
            cursor.execute(f"select distinct * from CONCEPTS where concept_id in {tuple(set(concept_ids))};")
            res = cursor.fetchall()
            if len(res) != 0:
                for row in res:
                    results_array.append({'concept_class_id': row[4],
                                            'concept_code': row[5],
                                            'concept_id': row[0],
                                            'concept_name': row[1],
                                            'domain_id': row[2],
                                            'vocabulary_id': row[3]})

        return results_array

    def get_vocabularies(self):
        """List of vocabularies. List of vocabulary_ids. Useful if you need to use /omop/mapToStandardConceptID to map a concept code from a source vocabulary to the OMOP standard vocabulary.

        Returns:
            list: an list of all vocabularies
            example:
            [ "ABMS", "AMT", "APC", ...]
        """
        cursor = self.connection.cursor()
        res = cursor.execute(f"select distinct vocabulary_id from CONCEPTS;")
        results_list = list(set([voc[0] for voc in res]))

        return results_list

    def get_associated_concept_freq(self, concept_id, dataset_id=1):
        """Retrieve observed clinical frequencies of all pairs of concepts given a concept id. Results are returned in descending order of paired concept count. Note that the largest paired concept counts are often dominated by associated concepts with high prevalence.

        Args:
            concept_id (rquired, int): An OMOP concept id, e.g., 192855
            dataset_id (optional, int): The dataset_id of the dataset to query. Default dataset is the 5-year dataset (1).

        Returns:
            array: an sorted(descreasing concept_frequency) array which contains frequency dictionaries, or an empty array if no data obtained
            example:
            [
                {
                    "associated_concept_id": 2213216,
                    "associated_concept_name": "Cytopathology, selective cellular enhancement technique with interpretation (eg, liquid based slide preparation method), except cervical or vaginal",
                    "associated_domain_id": "Measurement",
                    "concept_count": 330,
                    "concept_frequency": 0.0001843131625848748,
                    "concept_id": 192855,
                    "dataset_id": 1
                },
                {
                    "associated_concept_id": 4214956,
                    "associated_concept_name": "History of clinical finding in subject",
                    "associated_domain_id": "Observation",
                    "concept_count": 329,
                    "concept_frequency": 0.00018375463784976913,
                    "concept_id": 192855,
                    "dataset_id": 1
                },
                ...
            ]
        """
        if not isinstance(concept_id, int):
            print("The 'concept_id' in get_associated_concept_freq should be an int", flush=True)
            return []

        if not isinstance(dataset_id, int):
            print("The 'dataset_id' in get_associated_concept_freq should be an int", flush=True)
            return []
        else:
            if dataset_id == 1 or dataset_id == 2 or dataset_id == 3:
                pass
            else:
                print("The 'dataset_id' in get_associated_concept_freq should be 1, 2 or 3", flush=True)
                return []

        results_array = []
        cursor = self.connection.cursor()
        cursor.execute(f"select distinct p.dataset_id,p.concept_id_1,p.concept_id_2,p.concept_count,p.concept_prevalence,c.concept_name,c.domain_id from PAIRED_CONCEPT_COUNTS_ASSOCIATIONS p inner join CONCEPTS c on p.concept_id_2 = c.concept_id where p.concept_id_1 = {concept_id};")
        res = cursor.fetchall()

        if len(res) == 0:
            cursor.execute(f"select distinct p.dataset_id,p.concept_id_1,p.concept_id_2,p.concept_count,p.concept_prevalence,c.concept_name,c.domain_id from PAIRED_CONCEPT_COUNTS_ASSOCIATIONS p inner join CONCEPTS c on p.concept_id_1 = c.concept_id where p.concept_id_2 = {concept_id};")
            res = cursor.fetchall()
            if len(res) == 0:
                pass
            else:
                all_assoct = [row for row in res if row[0] == dataset_id]
                if len(all_assoct) == 0:
                    pass
                else:
                    for row in all_assoct:
                        results_array.append({'associated_concept_id': row[1],
                                                'associated_concept_name': row[5],
                                                'associated_domain_id': row[6],
                                                'concept_count': row[3],
                                                'concept_frequency': row[4],
                                                'concept_id': row[2],
                                                'dataset_id': row[0]})
        else:
            all_assoct = [row for row in res if row[0] == dataset_id]
            if len(all_assoct) == 0:
                cursor.execute(f"select distinct p.dataset_id,p.concept_id_1,p.concept_id_2,p.concept_count,p.concept_prevalence,c.concept_name,c.domain_id from PAIRED_CONCEPT_COUNTS_ASSOCIATIONS p inner join CONCEPTS c on p.concept_id_1 = c.concept_id where p.concept_id_2 = {concept_id};")
                res = cursor.fetchall()
                if len(res) == 0:
                    pass
                else:
                    all_assoct = [row for row in res if row[0] == dataset_id]
                    if len(all_assoct) == 0:
                        pass
                    else:
                        for row in all_assoct:
                            results_array.append({'associated_concept_id': row[1],
                                                    'associated_concept_name': row[5],
                                                    'associated_domain_id': row[6],
                                                    'concept_count': row[3],
                                                    'concept_frequency': row[4],
                                                    'concept_id': row[2],
                                                    'dataset_id': row[0]})
            else:
                for row in all_assoct:
                    results_array.append({'associated_concept_id': row[2],
                                            'associated_concept_name': row[5],
                                            'associated_domain_id': row[6],
                                            'concept_count': row[3],
                                            'concept_frequency': row[4],
                                            'concept_id': row[1],
                                            'dataset_id': row[0]})

                cursor.execute(f"select distinct p.dataset_id,p.concept_id_1,p.concept_id_2,p.concept_count,p.concept_prevalence,c.concept_name,c.domain_id from PAIRED_CONCEPT_COUNTS_ASSOCIATIONS p inner join CONCEPTS c on p.concept_id_1 = c.concept_id where p.concept_id_2 = {concept_id};")
                res = cursor.fetchall()
                if len(res) == 0:
                    pass
                else:
                    all_assoct = [row for row in res if row[0] == dataset_id]
                    if len(all_assoct) == 0:
                        pass
                    else:
                        for row in all_assoct:
                            results_array.append({'associated_concept_id': row[1],
                                                    'associated_concept_name': row[5],
                                                    'associated_domain_id': row[6],
                                                    'concept_count': row[3],
                                                    'concept_frequency': row[4],
                                                    'concept_id': row[2],
                                                    'dataset_id': row[0]})

        if len(results_array) != 0:
            results_array = sorted(results_array, key=lambda x: x['concept_frequency'], reverse=True)

        return results_array

    def get_most_frequent_concepts(self, num, domain="", dataset_id=1):
        """Retrieve the most frequent concepts.

        Args:
            num (required, int): The number of concepts to retreieve, e.g., 10
            domain (optional, str): The domain_id to restrict to, e.g., "Condition", "Drug", "Procedure"
            dataset_id (optional, int): The dataset_id of the dataset to query. Default dataset is the 5-year dataset.

        Returns:
            array: an sorted(decreasing concept_frequency) array which contains frequency dictionaries
            example:
            [
                {
                    "concept_class_id": "Clinical Finding",
                    "concept_count": 233790,
                    "concept_frequency": 0.1305774978203572,
                    "concept_id": 320128,
                    "concept_name": "Essential hypertension",
                    "dataset_id": 1,
                    "domain_id": "Condition",
                    "vocabulary_id": "SNOMED"
                },
                {
                    "concept_class_id": "Clinical Finding",
                    "concept_count": 152005,
                    "concept_frequency": 0.08489855235973907,
                    "concept_id": 77670,
                    "concept_name": "Chest pain",
                    "dataset_id": 1,
                    "domain_id": "Condition",
                    "vocabulary_id": "SNOMED"
                },
            ]
        """
        if not isinstance(num, int):
            print("The 'num' in get_most_frequent_concepts should be an int", flush=True)
            return []

        if not isinstance(domain, str):
            print("The 'domain' in get_most_frequent_concepts should be a str", flush=True)
            return []

        if not isinstance(dataset_id, int):
            print("The 'dataset_id' in get_most_frequent_concepts should be an int", flush=True)
            return []
        else:
            if dataset_id == 1 or dataset_id == 2 or dataset_id == 3:
                pass
            else:
                print("The 'dataset_id' in get_most_frequent_concepts should be 1, 2 or 3", flush=True)
                return []

        results_array = []
        cursor = self.connection.cursor()
        cursor.execute(f"select distinct c.concept_class_id,s.concept_count,s.concept_prevalence,c.concept_id,c.concept_name,s.dataset_id,c.domain_id,c.vocabulary_id from CONCEPTS c inner join SINGLE_CONCEPT_COUNTS s on c.concept_id = s.concept_id;")
        res = cursor.fetchall()

        if domain == "":
            for row in res:
                if row[5] == dataset_id:
                    results_array.append({'concept_class_id': row[0],
                                            'concept_count': row[1],
                                            'concept_frequency': row[2],
                                            'concept_id': row[3],
                                            'concept_name': row[4],
                                            'dataset_id': row[5],
                                            'domain_id': row[6],
                                            'vocabulary_id': row[7]})
        else:
            for row in res:
                if row[5] == dataset_id and row[6] == domain:
                    results_array.append({'concept_class_id': row[0],
                                            'concept_count': row[1],
                                            'concept_frequency': row[2],
                                            'concept_id': row[3],
                                            'concept_name': row[4],
                                            'dataset_id': row[5],
                                            'domain_id': row[6],
                                            'vocabulary_id': row[7]})

        if len(results_array) != 0:
            results_array = sorted(results_array, key=lambda x: x['concept_frequency'], reverse=True)
            results_array = results_array[:num]

        return results_array

    def get_obs_exp_ratio(self, concept_id_1=[], concept_id_2=[], concept_id_pair=None, domain="", dataset_id=1):
        """Return the natural logarithm of the ratio between the observed count and expected count.

            Expected count is calculated from the single concept frequencies and assuming independence between the concepts. Results are returned in descending order of ln_ratio.

            expected_count = Count_1_and_2 * num_patients / (Count_1 * Count_2)
            ln_ratio = ln( expected_count )
            This method has overloaded behavior based on the specified parameters:
                1. concept_id_1 and concept_id_2: Results for the pair (concept_id_1, concept_id_2)
                2. concept_id_1: Results for all pairs of concepts that include concept_id_1
                3. concept_id_1 and domain: Results for all pairs of concepts including concept_id_1 and where concept_id_2
                    belongs to the specified domain

        Args:
            concept_id_1 (optional, list): an OMOP id, e.g., [192855] or [192855, 8507]
            concept_id_2 (optional, list): an OMOP id, e.g., [2008271] or [2008271, 939259] If concept_id_2 is unspecified, then this method
                will return all pairs of concepts with concept_id_1.
            concept_id_pair (optional, str or list): the concatenation of two concept ids, e.g. "192855_2008271" or ["192855_2008271","8507_939259"]
            domain (optional, str): An OMOP domain id, e.g., "Condition", "Drug", "Procedure", etc., to restrict the associated
                concept (concept_id_2) to. If this parameter is not specified, then the domain is unrestricted.
            dataset_id (optional, int): The dataset_id of the dataset to query. Default dataset is the 5-year dataset (1).

        Returns:
            array: an sorted(decreasing ln_ratio) array of dictionaries which contains  the natural logarithm of the ratio between the observed
                count and expected count
            example:
            [
                {
                    "concept_id_1": 192855,
                    "concept_id_2": 2008271,
                    "dataset_id": 1,
                    "expected_count": 0.3070724311632227,
                    "ln_ratio": 3.483256720088832,
                    "observed_count": 10
                }
            ]
        """
        if concept_id_pair is None:
            if not isinstance(concept_id_1, list):
                print("Please provide either 'concept_id_1' or 'concept_id_pair'. The 'concept_id_1' in get_obs_exp_ratio should be a list", flush=True)
                return []
            else:
                if len(concept_id_1) == 0:
                    print("The 'concept_id_1' in get_obs_exp_ratio should not be a empty list", flush=True)
                    return []

            if not isinstance(concept_id_2, list):
                print("The 'concept_id_2' in get_obs_exp_ratio should be a list", flush=True)
                return []
        else:
            if isinstance(concept_id_pair, str):
                concept_id_pair1 = concept_id_pair
                concept_id_pair2 = f"{concept_id_pair.split('_')[1]}_{concept_id_pair.split('_')[0]}"
            elif isinstance(concept_id_pair, list):
                if len(concept_id_pair) == 0:
                    print("The 'concept_id_pair' in get_obs_exp_ratio is an empty list", flush=True)
                    return []
                else:
                    concept_id_pair1 = concept_id_pair
                    concept_id_pair2 = [f"{pair.split('_')[1]}_{pair.split('_')[0]}" for pair in concept_id_pair]
            else:
                print("The 'concept_id_pair' in get_obs_exp_ratio should be a str or a list", flush=True)
                return []

        if not isinstance(domain, str):
            print("The 'domain' in get_obs_exp_ratio should be a str", flush=True)
            return []

        if not isinstance(dataset_id, int):
            print("The 'dataset_id' in get_obs_exp_ratio should be an int", flush=True)
            return []
        else:
            if dataset_id == 1 or dataset_id == 2 or dataset_id == 3:
                pass
            else:
                print("The 'dataset_id' in get_obs_exp_ratio should be 1, 2 or 3", flush=True)
                return []

        results_array = []
        cursor = self.connection.cursor()
        if concept_id_pair is None:
            if len(concept_id_2) == 0:
                if domain == "":
                    if len(concept_id_1) == 1:
                        cursor.execute(f"select distinct concept_id_1,concept_id_2,dataset_id,expected_count,ln_ratio,concept_count from PAIRED_CONCEPT_COUNTS_ASSOCIATIONS where concept_id_1={concept_id_1[0]};")
                    else:
                        cursor.execute(f"select distinct concept_id_1,concept_id_2,dataset_id,expected_count,ln_ratio,concept_count from PAIRED_CONCEPT_COUNTS_ASSOCIATIONS where concept_id_1 in {tuple(set(concept_id_1))};")
                    res = cursor.fetchall()
                    if len(res) == 0:
                        if len(concept_id_1) == 1:
                            cursor.execute(f"select distinct concept_id_1,concept_id_2,dataset_id,expected_count,ln_ratio,concept_count from PAIRED_CONCEPT_COUNTS_ASSOCIATIONS where concept_id_2={concept_id_1[0]};")
                        else:
                            cursor.execute(f"select distinct concept_id_1,concept_id_2,dataset_id,expected_count,ln_ratio,concept_count from PAIRED_CONCEPT_COUNTS_ASSOCIATIONS where concept_id_2 in {tuple(set(concept_id_1))};")
                        res = cursor.fetchall()
                        if len(res) == 0:
                            pass
                        else:
                            for row in res:
                                if row[2] == dataset_id:
                                    results_array.append({'concept_id_1': row[1],
                                                            'concept_id_2': row[0],
                                                            'dataset_id': row[2],
                                                            'expected_count': row[3],
                                                            'ln_ratio': float(row[4]),
                                                            'observed_count': row[5]})
                    else:
                        for row in res:
                            if row[2] == dataset_id:
                                results_array.append({'concept_id_1': row[0],
                                                        'concept_id_2': row[1],
                                                        'dataset_id': row[2],
                                                        'expected_count': row[3],
                                                        'ln_ratio': float(row[4]),
                                                        'observed_count': row[5]})

                        if len(concept_id_1) == 1:
                            cursor.execute(f"select distinct concept_id_1,concept_id_2,dataset_id,expected_count,ln_ratio,concept_count from PAIRED_CONCEPT_COUNTS_ASSOCIATIONS where concept_id_2={concept_id_1[0]};")
                        else:
                            cursor.execute(f"select distinct concept_id_1,concept_id_2,dataset_id,expected_count,ln_ratio,concept_count from PAIRED_CONCEPT_COUNTS_ASSOCIATIONS where concept_id_2 in {tuple(set(concept_id_1))};")
                        res = cursor.fetchall()
                        if len(res) == 0:
                            pass
                        else:
                            for row in res:
                                if row[2] == dataset_id:
                                    results_array.append({'concept_id_1': row[1],
                                                            'concept_id_2': row[0],
                                                            'dataset_id': row[2],
                                                            'expected_count': row[3],
                                                            'ln_ratio': float(row[4]),
                                                            'observed_count': row[5]})
                else:
                    if len(concept_id_1) == 1:
                        cursor.execute(f"select distinct p.concept_id_1,p.concept_id_2,p.dataset_id,p.expected_count,p.ln_ratio,p.concept_count from PAIRED_CONCEPT_COUNTS_ASSOCIATIONS p inner join CONCEPTS c on p.concept_id_2 = c.concept_id  where p.concept_id_1={concept_id_1[0]} and c.domain_id='{domain}';")
                    else:
                        cursor.execute(f"select distinct p.concept_id_1,p.concept_id_2,p.dataset_id,p.expected_count,p.ln_ratio,p.concept_count from PAIRED_CONCEPT_COUNTS_ASSOCIATIONS p inner join CONCEPTS c on p.concept_id_2 = c.concept_id  where p.concept_id_1 in {tuple(set(concept_id_1))} and c.domain_id='{domain}';")
                    res = cursor.fetchall()
                    if len(res) == 0:
                        if len(concept_id_1) == 1:
                            cursor.execute(f"select distinct p.concept_id_1,p.concept_id_2,p.dataset_id,p.expected_count,p.ln_ratio,p.concept_count from PAIRED_CONCEPT_COUNTS_ASSOCIATIONS p inner join CONCEPTS c on p.concept_id_1 = c.concept_id  where p.concept_id_2={concept_id_1[0]} and c.domain_id='{domain}';")
                        else:
                            cursor.execute(f"select distinct p.concept_id_1,p.concept_id_2,p.dataset_id,p.expected_count,p.ln_ratio,p.concept_count from PAIRED_CONCEPT_COUNTS_ASSOCIATIONS p inner join CONCEPTS c on p.concept_id_1 = c.concept_id  where p.concept_id_2 in {tuple(set(concept_id_1))} and c.domain_id='{domain}';")
                        res = cursor.fetchall()
                        if len(res) == 0:
                            pass
                        else:
                            for row in res:
                                if row[2] == dataset_id:
                                    results_array.append({'concept_id_1': row[1],
                                                            'concept_id_2': row[0],
                                                            'dataset_id': row[2],
                                                            'expected_count': row[3],
                                                            'ln_ratio': float(row[4]),
                                                            'observed_count': row[5]})
                    else:
                        for row in res:
                            if row[2] == dataset_id:
                                results_array.append({'concept_id_1': row[0],
                                                        'concept_id_2': row[1],
                                                        'dataset_id': row[2],
                                                        'expected_count': row[3],
                                                        'ln_ratio': float(row[4]),
                                                        'observed_count': row[5]})

                        if len(concept_id_1) == 1:
                            cursor.execute(f"select distinct p.concept_id_1,p.concept_id_2,p.dataset_id,p.expected_count,p.ln_ratio,p.concept_count from PAIRED_CONCEPT_COUNTS_ASSOCIATIONS p inner join CONCEPTS c on p.concept_id_1 = c.concept_id  where p.concept_id_2={concept_id_1[0]} and c.domain_id='{domain}';")
                        else:
                            cursor.execute(f"select distinct p.concept_id_1,p.concept_id_2,p.dataset_id,p.expected_count,p.ln_ratio,p.concept_count from PAIRED_CONCEPT_COUNTS_ASSOCIATIONS p inner join CONCEPTS c on p.concept_id_1 = c.concept_id  where p.concept_id_2 in {tuple(set(concept_id_1))} and c.domain_id='{domain}';")
                        res = cursor.fetchall()
                        if len(res) == 0:
                            pass
                        else:
                            for row in res:
                                if row[2] == dataset_id:
                                    results_array.append({'concept_id_1': row[1],
                                                            'concept_id_2': row[0],
                                                            'dataset_id': row[2],
                                                            'expected_count': row[3],
                                                            'ln_ratio': float(row[4]),
                                                            'observed_count': row[5]})
            else:
                if domain == "":
                    if len(concept_id_1) == 1 and len(concept_id_2) == 1:
                        cursor.execute(f"select distinct concept_id_1,concept_id_2,dataset_id,expected_count,ln_ratio,concept_count from PAIRED_CONCEPT_COUNTS_ASSOCIATIONS where concept_id_1={concept_id_1[0]} and concept_id_2={concept_id_2[0]};")
                    elif len(concept_id_1) == 1:
                        cursor.execute(f"select distinct concept_id_1,concept_id_2,dataset_id,expected_count,ln_ratio,concept_count from PAIRED_CONCEPT_COUNTS_ASSOCIATIONS where concept_id_1={concept_id_1[0]} and concept_id_2 in {tuple(set(concept_id_2))};")
                    elif len(concept_id_2) == 1:
                        cursor.execute(f"select distinct concept_id_1,concept_id_2,dataset_id,expected_count,ln_ratio,concept_count from PAIRED_CONCEPT_COUNTS_ASSOCIATIONS where concept_id_1 in {tuple(set(concept_id_1))} and concept_id_2={concept_id_2[0]};")
                    else:
                        cursor.execute(f"select distinct concept_id_1,concept_id_2,dataset_id,expected_count,ln_ratio,concept_count from PAIRED_CONCEPT_COUNTS_ASSOCIATIONS where concept_id_1 in {tuple(set(concept_id_1))} and concept_id_2 in {tuple(set(concept_id_2))};")
                    res = cursor.fetchall()
                    if len(res) == 0:
                        if len(concept_id_1) == 1 and len(concept_id_2) == 1:
                            cursor.execute(f"select distinct concept_id_1,concept_id_2,dataset_id,expected_count,ln_ratio,concept_count from PAIRED_CONCEPT_COUNTS_ASSOCIATIONS where concept_id_1={concept_id_2[0]} and concept_id_2={concept_id_1[0]};")
                        elif len(concept_id_1) == 1:
                            cursor.execute(f"select distinct concept_id_1,concept_id_2,dataset_id,expected_count,ln_ratio,concept_count from PAIRED_CONCEPT_COUNTS_ASSOCIATIONS where concept_id_1 in {tuple(set(concept_id_2))} and concept_id_2={concept_id_1[0]};")
                        elif len(concept_id_2) == 1:
                            cursor.execute(f"select distinct concept_id_1,concept_id_2,dataset_id,expected_count,ln_ratio,concept_count from PAIRED_CONCEPT_COUNTS_ASSOCIATIONS where concept_id_1={concept_id_2[0]} and concept_id_2 in {tuple(set(concept_id_1))};")
                        else:
                            cursor.execute(f"select distinct concept_id_1,concept_id_2,dataset_id,expected_count,ln_ratio,concept_count from PAIRED_CONCEPT_COUNTS_ASSOCIATIONS where concept_id_1 in {tuple(set(concept_id_2))} and concept_id_2 in {tuple(set(concept_id_1))};")
                        res = cursor.fetchall()
                        if len(res) == 0:
                            pass
                        else:
                            for row in res:
                                if row[2] == dataset_id:
                                    results_array.append({'concept_id_1': row[1],
                                                            'concept_id_2': row[0],
                                                            'dataset_id': row[2],
                                                            'expected_count': row[3],
                                                            'ln_ratio': float(row[4]),
                                                            'observed_count': row[5]})
                    else:
                        for row in res:
                            if row[2] == dataset_id:
                                results_array.append({'concept_id_1': row[0],
                                                        'concept_id_2': row[1],
                                                        'dataset_id': row[2],
                                                        'expected_count': row[3],
                                                        'ln_ratio': float(row[4]),
                                                        'observed_count': row[5]})

                        if len(concept_id_1) == 1 and len(concept_id_2) == 1:
                            cursor.execute(f"select distinct concept_id_1,concept_id_2,dataset_id,expected_count,ln_ratio,concept_count from PAIRED_CONCEPT_COUNTS_ASSOCIATIONS where concept_id_1={concept_id_2[0]} and concept_id_2={concept_id_1[0]};")
                        elif len(concept_id_1) == 1:
                            cursor.execute(f"select distinct concept_id_1,concept_id_2,dataset_id,expected_count,ln_ratio,concept_count from PAIRED_CONCEPT_COUNTS_ASSOCIATIONS where concept_id_1 in {tuple(set(concept_id_2))} and concept_id_2={concept_id_1[0]};")
                        elif len(concept_id_2) == 1:
                            cursor.execute(f"select distinct concept_id_1,concept_id_2,dataset_id,expected_count,ln_ratio,concept_count from PAIRED_CONCEPT_COUNTS_ASSOCIATIONS where concept_id_1={concept_id_2[0]} and concept_id_2 in {tuple(set(concept_id_1))};")
                        else:
                            cursor.execute(f"select distinct concept_id_1,concept_id_2,dataset_id,expected_count,ln_ratio,concept_count from PAIRED_CONCEPT_COUNTS_ASSOCIATIONS where concept_id_1 in {tuple(set(concept_id_2))} and concept_id_2 in {tuple(set(concept_id_1))};")
                        res = cursor.fetchall()
                        if len(res) == 0:
                            pass
                        else:
                            for row in res:
                                if row[2] == dataset_id:
                                    results_array.append({'concept_id_1': row[1],
                                                            'concept_id_2': row[0],
                                                            'dataset_id': row[2],
                                                            'expected_count': row[3],
                                                            'ln_ratio': float(row[4]),
                                                            'observed_count': row[5]})

                else:
                    if len(concept_id_1) == 1 and len(concept_id_2) == 1:
                        cursor.execute(f"select distinct p.concept_id_1,p.concept_id_2,p.dataset_id,p.expected_count,p.ln_ratio,p.concept_count from PAIRED_CONCEPT_COUNTS_ASSOCIATIONS p inner join CONCEPTS c on p.concept_id_2 = c.concept_id  where p.concept_id_1={concept_id_1[0]} and p.concept_id_2={concept_id_2[0]} and c.domain_id='{domain}';")
                    elif len(concept_id_1) == 1:
                        cursor.execute(f"select distinct p.concept_id_1,p.concept_id_2,p.dataset_id,p.expected_count,p.ln_ratio,p.concept_count from PAIRED_CONCEPT_COUNTS_ASSOCIATIONS p inner join CONCEPTS c on p.concept_id_2 = c.concept_id  where p.concept_id_1={concept_id_1[0]} and p.concept_id_2 in {tuple(set(concept_id_2))} and c.domain_id='{domain}';")
                    elif len(concept_id_2) == 1:
                        cursor.execute(f"select distinct p.concept_id_1,p.concept_id_2,p.dataset_id,p.expected_count,p.ln_ratio,p.concept_count from PAIRED_CONCEPT_COUNTS_ASSOCIATIONS p inner join CONCEPTS c on p.concept_id_2 = c.concept_id  where p.concept_id_1 in {tuple(set(concept_id_1))} and p.concept_id_2={concept_id_2[0]} and c.domain_id='{domain}';")
                    else:
                        cursor.execute(f"select distinct p.concept_id_1,p.concept_id_2,p.dataset_id,p.expected_count,p.ln_ratio,p.concept_count from PAIRED_CONCEPT_COUNTS_ASSOCIATIONS p inner join CONCEPTS c on p.concept_id_2 = c.concept_id  where p.concept_id_1 in {tuple(set(concept_id_1))} and p.concept_id_2 in {tuple(set(concept_id_2))} and c.domain_id='{domain}';")
                    res = cursor.fetchall()
                    if len(res) == 0:
                        if len(concept_id_1) == 1 and len(concept_id_2) == 1:
                            cursor.execute(f"select distinct p.concept_id_1,p.concept_id_2,p.dataset_id,p.expected_count,p.ln_ratio,p.concept_count from PAIRED_CONCEPT_COUNTS_ASSOCIATIONS p inner join CONCEPTS c on p.concept_id_1 = c.concept_id  where p.concept_id_1={concept_id_2[0]} and p.concept_id_2={concept_id_1[0]} and c.domain_id='{domain}';")
                        elif len(concept_id_1) == 1:
                            cursor.execute(f"select distinct p.concept_id_1,p.concept_id_2,p.dataset_id,p.expected_count,p.ln_ratio,p.concept_count from PAIRED_CONCEPT_COUNTS_ASSOCIATIONS p inner join CONCEPTS c on p.concept_id_1 = c.concept_id  where p.concept_id_1 in {tuple(set(concept_id_2))} and p.concept_id_2={concept_id_1[0]} and c.domain_id='{domain}';")
                        elif len(concept_id_2) == 1:
                            cursor.execute(f"select distinct p.concept_id_1,p.concept_id_2,p.dataset_id,p.expected_count,p.ln_ratio,p.concept_count from PAIRED_CONCEPT_COUNTS_ASSOCIATIONS p inner join CONCEPTS c on p.concept_id_1 = c.concept_id  where p.concept_id_1={concept_id_2[0]} and p.concept_id_2 in {tuple(set(concept_id_1))} and c.domain_id='{domain}';")
                        else:
                            cursor.execute(f"select distinct p.concept_id_1,p.concept_id_2,p.dataset_id,p.expected_count,p.ln_ratio,p.concept_count from PAIRED_CONCEPT_COUNTS_ASSOCIATIONS p inner join CONCEPTS c on p.concept_id_1 = c.concept_id  where p.concept_id_1 in {tuple(set(concept_id_2))} and p.concept_id_2 in {tuple(set(concept_id_1))} and c.domain_id='{domain}';")
                        res = cursor.fetchall()
                        if len(res) == 0:
                            pass
                        else:
                            for row in res:
                                if row[2] == dataset_id:
                                    results_array.append({'concept_id_1': row[1],
                                                            'concept_id_2': row[0],
                                                            'dataset_id': row[2],
                                                            'expected_count': row[3],
                                                            'ln_ratio': float(row[4]),
                                                            'observed_count': row[5]})
                    else:
                        for row in res:
                            if row[2] == dataset_id:
                                results_array.append({'concept_id_1': row[0],
                                                        'concept_id_2': row[1],
                                                        'dataset_id': row[2],
                                                        'expected_count': row[3],
                                                        'ln_ratio': float(row[4]),
                                                        'observed_count': row[5]})

                        if len(concept_id_1) == 1 and len(concept_id_2) == 1:
                            cursor.execute(f"select distinct p.concept_id_1,p.concept_id_2,p.dataset_id,p.expected_count,p.ln_ratio,p.concept_count from PAIRED_CONCEPT_COUNTS_ASSOCIATIONS p inner join CONCEPTS c on p.concept_id_1 = c.concept_id  where p.concept_id_1={concept_id_2[0]} and p.concept_id_2={concept_id_1[0]} and c.domain_id='{domain}';")
                        elif len(concept_id_1) == 1:
                            cursor.execute(f"select distinct p.concept_id_1,p.concept_id_2,p.dataset_id,p.expected_count,p.ln_ratio,p.concept_count from PAIRED_CONCEPT_COUNTS_ASSOCIATIONS p inner join CONCEPTS c on p.concept_id_1 = c.concept_id  where p.concept_id_1 in {tuple(set(concept_id_2))} and p.concept_id_2={concept_id_1[0]} and c.domain_id='{domain}';")
                        elif len(concept_id_2) == 1:
                            cursor.execute(f"select distinct p.concept_id_1,p.concept_id_2,p.dataset_id,p.expected_count,p.ln_ratio,p.concept_count from PAIRED_CONCEPT_COUNTS_ASSOCIATIONS p inner join CONCEPTS c on p.concept_id_1 = c.concept_id  where p.concept_id_1={concept_id_2[0]} and p.concept_id_2 in {tuple(set(concept_id_1))} and c.domain_id='{domain}';")
                        else:
                            cursor.execute(f"select distinct p.concept_id_1,p.concept_id_2,p.dataset_id,p.expected_count,p.ln_ratio,p.concept_count from PAIRED_CONCEPT_COUNTS_ASSOCIATIONS p inner join CONCEPTS c on p.concept_id_1 = c.concept_id  where p.concept_id_1 in {tuple(set(concept_id_2))} and p.concept_id_2 in {tuple(set(concept_id_1))} and c.domain_id='{domain}';")
                        res = cursor.fetchall()
                        if len(res) == 0:
                            pass
                        else:
                            for row in res:
                                if row[2] == dataset_id:
                                    results_array.append({'concept_id_1': row[1],
                                                            'concept_id_2': row[0],
                                                            'dataset_id': row[2],
                                                            'expected_count': row[3],
                                                            'ln_ratio': float(row[4]),
                                                            'observed_count': row[5]})
        else:
            if isinstance(concept_id_pair, str):
                if domain == "":
                    cursor.execute(f"select distinct concept_id_1,concept_id_2,dataset_id,expected_count,ln_ratio,concept_count from PAIRED_CONCEPT_COUNTS_ASSOCIATIONS where concept_pair_id='{concept_id_pair1}';")
                    res = cursor.fetchall()
                    if len(res) == 0:
                        cursor.execute(f"select distinct concept_id_1,concept_id_2,dataset_id,expected_count,ln_ratio,concept_count from PAIRED_CONCEPT_COUNTS_ASSOCIATIONS where concept_pair_id='{concept_id_pair2}';")
                        res = cursor.fetchall()
                        if len(res) == 0:
                            pass
                        else:
                            for row in res:
                                if row[2] == dataset_id:
                                    results_array.append({'concept_id_1': row[1],
                                                            'concept_id_2': row[0],
                                                            'dataset_id': row[2],
                                                            'expected_count': row[3],
                                                            'ln_ratio': float(row[4]),
                                                            'observed_count': row[5]})
                    else:
                        for row in res:
                            if row[2] == dataset_id:
                                results_array.append({'concept_id_1': row[0],
                                                        'concept_id_2': row[1],
                                                        'dataset_id': row[2],
                                                        'expected_count': row[3],
                                                        'ln_ratio': float(row[4]),
                                                        'observed_count': row[5]})

                        cursor.execute(f"select distinct concept_id_1,concept_id_2,dataset_id,expected_count,ln_ratio,concept_count from PAIRED_CONCEPT_COUNTS_ASSOCIATIONS where concept_pair_id='{concept_id_pair2}';")
                        res = cursor.fetchall()
                        if len(res) == 0:
                            pass
                        else:
                            for row in res:
                                if row[2] == dataset_id:
                                    results_array.append({'concept_id_1': row[1],
                                                            'concept_id_2': row[0],
                                                            'dataset_id': row[2],
                                                            'expected_count': row[3],
                                                            'ln_ratio': float(row[4]),
                                                            'observed_count': row[5]})
                else:
                    cursor.execute(f"select distinct p.concept_id_1,p.concept_id_2,p.dataset_id,p.expected_count,p.ln_ratio,p.concept_count from PAIRED_CONCEPT_COUNTS_ASSOCIATIONS p inner join CONCEPTS c on p.concept_id_2 = c.concept_id where p.concept_pair_id='{concept_id_pair1}' and c.domain_id='{domain}';")
                    res = cursor.fetchall()
                    if len(res) == 0:
                        cursor.execute(f"select distinct p.concept_id_1,p.concept_id_2,p.dataset_id,p.expected_count,p.ln_ratio,p.concept_count from PAIRED_CONCEPT_COUNTS_ASSOCIATIONS p inner join CONCEPTS c on p.concept_id_1 = c.concept_id where p.concept_pair_id='{concept_id_pair2}' and c.domain_id='{domain}';")
                        res = cursor.fetchall()
                        if len(res) == 0:
                            pass
                        else:
                            for row in res:
                                if row[2] == dataset_id:
                                    results_array.append({'concept_id_1': row[1],
                                                            'concept_id_2': row[0],
                                                            'dataset_id': row[2],
                                                            'expected_count': row[3],
                                                            'ln_ratio': float(row[4]),
                                                            'observed_count': row[5]})
                    else:
                        for row in res:
                            if row[2] == dataset_id:
                                results_array.append({'concept_id_1': row[0],
                                                        'concept_id_2': row[1],
                                                        'dataset_id': row[2],
                                                        'expected_count': row[3],
                                                        'ln_ratio': float(row[4]),
                                                        'observed_count': row[5]})

                        cursor.execute(f"select distinct p.concept_id_1,p.concept_id_2,p.dataset_id,p.expected_count,p.ln_ratio,p.concept_count from PAIRED_CONCEPT_COUNTS_ASSOCIATIONS p inner join CONCEPTS c on p.concept_id_1 = c.concept_id where p.concept_pair_id='{concept_id_pair2}' and c.domain_id='{domain}';")
                        res = cursor.fetchall()
                        if len(res) == 0:
                            pass
                        else:
                            for row in res:
                                if row[2] == dataset_id:
                                    results_array.append({'concept_id_1': row[1],
                                                            'concept_id_2': row[0],
                                                            'dataset_id': row[2],
                                                            'expected_count': row[3],
                                                            'ln_ratio': float(row[4]),
                                                            'observed_count': row[5]})
            else:
                if domain == "":
                    if len(concept_id_pair) == 1:
                        cursor.execute(f"select distinct concept_id_1,concept_id_2,dataset_id,expected_count,ln_ratio,concept_count from PAIRED_CONCEPT_COUNTS_ASSOCIATIONS where concept_pair_id='{concept_id_pair1[0]}';")
                    else:
                        cursor.execute(f"select distinct concept_id_1,concept_id_2,dataset_id,expected_count,ln_ratio,concept_count from PAIRED_CONCEPT_COUNTS_ASSOCIATIONS where concept_pair_id in {tuple(set(concept_id_pair1))};")
                    res = cursor.fetchall()
                    if len(res) == 0:
                        if len(concept_id_pair) == 1:
                            cursor.execute(f"select distinct concept_id_1,concept_id_2,dataset_id,expected_count,ln_ratio,concept_count from PAIRED_CONCEPT_COUNTS_ASSOCIATIONS where concept_pair_id='{concept_id_pair2[0]}';")
                        else:
                            cursor.execute(f"select distinct concept_id_1,concept_id_2,dataset_id,expected_count,ln_ratio,concept_count from PAIRED_CONCEPT_COUNTS_ASSOCIATIONS where concept_pair_id in {tuple(set(concept_id_pair2))};")
                        res = cursor.fetchall()
                        if len(res) == 0:
                            pass
                        else:
                            for row in res:
                                if row[2] == dataset_id:
                                    results_array.append({'concept_id_1': row[1],
                                                            'concept_id_2': row[0],
                                                            'dataset_id': row[2],
                                                            'expected_count': row[3],
                                                            'ln_ratio': float(row[4]),
                                                            'observed_count': row[5]})
                    else:
                        for row in res:
                            if row[2] == dataset_id:
                                results_array.append({'concept_id_1': row[0],
                                                        'concept_id_2': row[1],
                                                        'dataset_id': row[2],
                                                        'expected_count': row[3],
                                                        'ln_ratio': float(row[4]),
                                                        'observed_count': row[5]})

                        if len(concept_id_pair) == 1:
                            cursor.execute(f"select distinct concept_id_1,concept_id_2,dataset_id,expected_count,ln_ratio,concept_count from PAIRED_CONCEPT_COUNTS_ASSOCIATIONS where concept_pair_id='{concept_id_pair2[0]}';")
                        else:
                            cursor.execute(f"select distinct concept_id_1,concept_id_2,dataset_id,expected_count,ln_ratio,concept_count from PAIRED_CONCEPT_COUNTS_ASSOCIATIONS where concept_pair_id in {tuple(set(concept_id_pair2))};")
                        res = cursor.fetchall()
                        if len(res) == 0:
                            pass
                        else:
                            for row in res:
                                if row[2] == dataset_id:
                                    results_array.append({'concept_id_1': row[1],
                                                            'concept_id_2': row[0],
                                                            'dataset_id': row[2],
                                                            'expected_count': row[3],
                                                            'ln_ratio': float(row[4]),
                                                            'observed_count': row[5]})
                else:
                    if len(concept_id_pair) == 1:
                        cursor.execute(f"select distinct p.concept_id_1,p.concept_id_2,p.dataset_id,p.expected_count,p.ln_ratio,p.concept_count from PAIRED_CONCEPT_COUNTS_ASSOCIATIONS p inner join CONCEPTS c on p.concept_id_2 = c.concept_id where p.concept_pair_id='{concept_id_pair1[0]}' and c.domain_id='{domain}';")
                    else:
                        cursor.execute(f"select distinct p.concept_id_1,p.concept_id_2,p.dataset_id,p.expected_count,p.ln_ratio,p.concept_count from PAIRED_CONCEPT_COUNTS_ASSOCIATIONS p inner join CONCEPTS c on p.concept_id_2 = c.concept_id where p.concept_pair_id in {tuple(set(concept_id_pair1))} and c.domain_id='{domain}';")
                    res = cursor.fetchall()
                    if len(res) == 0:
                        if len(concept_id_pair) == 1:
                            cursor.execute(f"select distinct p.concept_id_1,p.concept_id_2,p.dataset_id,p.expected_count,p.ln_ratio,p.concept_count from PAIRED_CONCEPT_COUNTS_ASSOCIATIONS p inner join CONCEPTS c on p.concept_id_1 = c.concept_id where p.concept_pair_id='{concept_id_pair2[0]}' and c.domain_id='{domain}';")
                        else:
                            cursor.execute(f"select distinct p.concept_id_1,p.concept_id_2,p.dataset_id,p.expected_count,p.ln_ratio,p.concept_count from PAIRED_CONCEPT_COUNTS_ASSOCIATIONS p inner join CONCEPTS c on p.concept_id_1 = c.concept_id where p.concept_pair_id in {tuple(set(concept_id_pair2))} and c.domain_id='{domain}';")
                        res = cursor.fetchall()
                        if len(res) == 0:
                            pass
                        else:
                            for row in res:
                                if row[2] == dataset_id:
                                    results_array.append({'concept_id_1': row[1],
                                                            'concept_id_2': row[0],
                                                            'dataset_id': row[2],
                                                            'expected_count': row[3],
                                                            'ln_ratio': float(row[4]),
                                                            'observed_count': row[5]})
                    else:
                        for row in res:
                            if row[2] == dataset_id:
                                results_array.append({'concept_id_1': row[0],
                                                        'concept_id_2': row[1],
                                                        'dataset_id': row[2],
                                                        'expected_count': row[3],
                                                        'ln_ratio': float(row[4]),
                                                        'observed_count': row[5]})

                        if len(concept_id_pair) == 1:
                            cursor.execute(f"select distinct p.concept_id_1,p.concept_id_2,p.dataset_id,p.expected_count,p.ln_ratio,p.concept_count from PAIRED_CONCEPT_COUNTS_ASSOCIATIONS p inner join CONCEPTS c on p.concept_id_1 = c.concept_id where p.concept_pair_id='{concept_id_pair2[0]}' and c.domain_id='{domain}';")
                        else:
                            cursor.execute(f"select distinct p.concept_id_1,p.concept_id_2,p.dataset_id,p.expected_count,p.ln_ratio,p.concept_count from PAIRED_CONCEPT_COUNTS_ASSOCIATIONS p inner join CONCEPTS c on p.concept_id_1 = c.concept_id where p.concept_pair_id in {tuple(set(concept_id_pair2))} and c.domain_id='{domain}';")
                        res = cursor.fetchall()
                        if len(res) == 0:
                            pass
                        else:
                            for row in res:
                                if row[2] == dataset_id:
                                    results_array.append({'concept_id_1': row[1],
                                                            'concept_id_2': row[0],
                                                            'dataset_id': row[2],
                                                            'expected_count': row[3],
                                                            'ln_ratio': float(row[4]),
                                                            'observed_count': row[5]})

        if len(results_array) != 0:
            results_array = sorted(results_array, key=lambda x: x['ln_ratio'], reverse=True)

        return results_array

    def get_chi_square(self, concept_id_1=[], concept_id_2=[], concept_id_pair=None, domain='', dataset_id=1):
        """Return the chi-square statistic and p-value between pairs of concepts.

            Results are returned in descending order of the chi-square statistic.
            Note that due to large sample sizes, the chi-square can become very large.
            The expected frequencies for the chi-square analysis are calculated based on the single concept frequencies and assuming independence between concepts.
            P-value is calculated with 1 DOF.

            This method has overloaded behavior based on the specified parameters:
                1. concept_id_1 and concept_id_2: Result for the pair (concept_id_1, concept_id_2)
                2. concept_id_1: Results for all pairs of concepts that include concept_id_1
                3. concept_id_1 and domain: Results for all pairs of concepts including concept_id_1 and where concept_id_2 belongs to the specified domain
        Args:
            concept_id_1 (optional, list): an OMOP id, e.g., [192855] or [192855, 8507]
            concept_id_2 (optional, list): an OMOP id, e.g., [2008271] or [2008271, 939259] If this parameter is specified, then the chi-square
                between concept_id_1 and concept_id_2 is returned. If this parameter is not specified, then a list of
                chi-squared results between concept_id_1 and other concepts is returned.
            concept_id_pair (optional, str or list): the concatenation of two concept ids, e.g. "192855_2008271" or ["192855_2008271","8507_939259"]
            domain (optional, str): An OMOP domain id, e.g., "Condition", "Drug", "Procedure", etc., to restrict the associated
                concept (concept_id_2) to. If this parameter is not specified, then the domain is unrestricted.
            dataset_id (int): The dataset_id of the dataset to query. Default dataset is the 5-year dataset (1).

        Returns:
            array: an sorted(increasing pvalue) array of chi-square dictionaries.
            example:
            [
                {
                    "chi_square": 306.2816108187519,
                    "concept_id_1": 192855,
                    "concept_id_2": 2008271,
                    "dataset_id": 1,
                    "p-value": 1.4101531778039801e-68
                }
            ]
        """
        if concept_id_pair is None:
            if not isinstance(concept_id_1, list):
                print("Please provide either 'concept_id_1' or 'concept_id_pair'. The 'concept_id_1' in get_chi_square should be a list", flush=True)
                return []
            else:
                if len(concept_id_1) == 0:
                    print("The 'concept_id_1' in get_chi_square should not be a empty list", flush=True)
                    return []

            if not isinstance(concept_id_2, list):
                print("The 'concept_id_2' in get_chi_square should be a list", flush=True)
                return []
        else:
            if isinstance(concept_id_pair, str):
                concept_id_pair1 = concept_id_pair
                concept_id_pair2 = f"{concept_id_pair.split('_')[1]}_{concept_id_pair.split('_')[0]}"
            elif isinstance(concept_id_pair, list):
                if len(concept_id_pair) == 0:
                    print("The 'concept_id_pair' in get_chi_square is an empty list", flush=True)
                    return []
                else:
                    concept_id_pair1 = concept_id_pair
                    concept_id_pair2 = [f"{pair.split('_')[1]}_{pair.split('_')[0]}" for pair in concept_id_pair]
            else:
                print("The 'concept_id_pair' in get_chi_square should be a str or a list", flush=True)
                return []

        if not isinstance(domain, str):
            print("The 'domain' in get_chi_square should be a str", flush=True)
            return []

        if not isinstance(dataset_id, int):
            print("The 'dataset_id' in get_chi_square should be an int", flush=True)
            return []
        else:
            if dataset_id == 1 or dataset_id == 2 or dataset_id == 3:
                pass
            else:
                print("The 'dataset_id' in get_chi_square should be 1, 2 or 3", flush=True)
                return []

        results_array = []
        cursor = self.connection.cursor()
        if concept_id_pair is None:
            if len(concept_id_2) == 0:
                if domain == "":
                    if len(concept_id_1) == 1:
                        cursor.execute(f"select distinct chi_square_t,concept_id_1,concept_id_2,dataset_id,chi_square_p from PAIRED_CONCEPT_COUNTS_ASSOCIATIONS where concept_id_1={concept_id_1[0]};")
                    else:
                        cursor.execute(f"select distinct chi_square_t,concept_id_1,concept_id_2,dataset_id,chi_square_p from PAIRED_CONCEPT_COUNTS_ASSOCIATIONS where concept_id_1 in {tuple(set(concept_id_1))};")
                    res = cursor.fetchall()
                    if len(res) == 0:
                        if len(concept_id_1) == 1:
                            cursor.execute(f"select distinct chi_square_t,concept_id_1,concept_id_2,dataset_id,chi_square_p from PAIRED_CONCEPT_COUNTS_ASSOCIATIONS where concept_id_2={concept_id_1[0]};")
                        else:
                            cursor.execute(f"select distinct chi_square_t,concept_id_1,concept_id_2,dataset_id,chi_square_p from PAIRED_CONCEPT_COUNTS_ASSOCIATIONS where concept_id_2 in {tuple(set(concept_id_1))};")
                        res = cursor.fetchall()
                        if len(res) == 0:
                            pass
                        else:
                            for row in res:
                                if row[3] == dataset_id:
                                    results_array.append({'chi_square': row[0],
                                                            'concept_id_1': row[2],
                                                            'concept_id_2': row[1],
                                                            'dataset_id': row[3],
                                                            'p-value': row[4]})
                    else:
                        for row in res:
                            if row[3] == dataset_id:
                                results_array.append({'chi_square': row[0],
                                                        'concept_id_1': row[1],
                                                        'concept_id_2': row[2],
                                                        'dataset_id': row[3],
                                                        'p-value': row[4]})

                        if len(concept_id_1) == 1:
                            cursor.execute(f"select distinct chi_square_t,concept_id_1,concept_id_2,dataset_id,chi_square_p from PAIRED_CONCEPT_COUNTS_ASSOCIATIONS where concept_id_2={concept_id_1[0]};")
                        else:
                            cursor.execute(f"select distinct chi_square_t,concept_id_1,concept_id_2,dataset_id,chi_square_p from PAIRED_CONCEPT_COUNTS_ASSOCIATIONS where concept_id_2 in {tuple(set(concept_id_1))};")
                        res = cursor.fetchall()
                        if len(res) == 0:
                            pass
                        else:
                            for row in res:
                                if row[3] == dataset_id:
                                    results_array.append({'chi_square': row[0],
                                                            'concept_id_1': row[2],
                                                            'concept_id_2': row[1],
                                                            'dataset_id': row[3],
                                                            'p-value': row[4]})
                else:
                    if len(concept_id_1) == 1:
                        cursor.execute(f"select distinct p.chi_square_t,p.concept_id_1,p.concept_id_2,p.dataset_id,p.chi_square_p from PAIRED_CONCEPT_COUNTS_ASSOCIATIONS p inner join CONCEPTS c on p.concept_id_2 = c.concept_id  where p.concept_id_1={concept_id_1[0]} and c.domain_id='{domain}';")
                    else:
                        cursor.execute(f"select distinct p.chi_square_t,p.concept_id_1,p.concept_id_2,p.dataset_id,p.chi_square_p from PAIRED_CONCEPT_COUNTS_ASSOCIATIONS p inner join CONCEPTS c on p.concept_id_2 = c.concept_id  where p.concept_id_1 in {tuple(set(concept_id_1))} and c.domain_id='{domain}';")
                    res = cursor.fetchall()
                    if len(res) == 0:
                        if len(concept_id_1) == 1:
                            cursor.execute(f"select distinct p.chi_square_t,p.concept_id_1,p.concept_id_2,p.dataset_id,p.chi_square_p from PAIRED_CONCEPT_COUNTS_ASSOCIATIONS p inner join CONCEPTS c on p.concept_id_1 = c.concept_id  where p.concept_id_2={concept_id_1[0]} and c.domain_id='{domain}';")
                        else:
                            cursor.execute(f"select distinct p.chi_square_t,p.concept_id_1,p.concept_id_2,p.dataset_id,p.chi_square_p from PAIRED_CONCEPT_COUNTS_ASSOCIATIONS p inner join CONCEPTS c on p.concept_id_1 = c.concept_id  where p.concept_id_2 in {tuple(set(concept_id_1))} and c.domain_id='{domain}';")
                        res = cursor.fetchall()
                        if len(res) == 0:
                            pass
                        else:
                            for row in res:
                                if row[3] == dataset_id:
                                    results_array.append({'chi_square': row[0],
                                                            'concept_id_1': row[2],
                                                            'concept_id_2': row[1],
                                                            'dataset_id': row[3],
                                                            'p-value': row[4]})
                    else:
                        for row in res:
                            chi_square, concept_id_1, concept_id_2, dataset_id_row, pvalue = row
                            if row[3] == dataset_id:
                                results_array.append({'chi_square': row[0],
                                                        'concept_id_1': row[1],
                                                        'concept_id_2': row[2],
                                                        'dataset_id': row[3],
                                                        'p-value': row[4]})

                        if len(concept_id_1) == 1:
                            cursor.execute(f"select distinct p.chi_square_t,p.concept_id_1,p.concept_id_2,p.dataset_id,p.chi_square_p from PAIRED_CONCEPT_COUNTS_ASSOCIATIONS p inner join CONCEPTS c on p.concept_id_1 = c.concept_id  where p.concept_id_2={concept_id_1[0]} and c.domain_id='{domain}';")
                        else:
                            cursor.execute(f"select distinct p.chi_square_t,p.concept_id_1,p.concept_id_2,p.dataset_id,p.chi_square_p from PAIRED_CONCEPT_COUNTS_ASSOCIATIONS p inner join CONCEPTS c on p.concept_id_1 = c.concept_id  where p.concept_id_2 in {tuple(set(concept_id_1))} and c.domain_id='{domain}';")
                        res = cursor.fetchall()
                        if len(res) == 0:
                            pass
                        else:
                            for row in res:
                                if row[3] == dataset_id:
                                    results_array.append({'chi_square': row[0],
                                                            'concept_id_1': row[2],
                                                            'concept_id_2': row[1],
                                                            'dataset_id': row[3],
                                                            'p-value': row[4]})

            else:
                if domain == "":
                    if len(concept_id_1) == 1 and len(concept_id_2) == 1:
                        cursor.execute(f"select distinct chi_square_t,concept_id_1,concept_id_2,dataset_id,chi_square_p from PAIRED_CONCEPT_COUNTS_ASSOCIATIONS where concept_id_1={concept_id_1[0]} and concept_id_2={concept_id_2[0]};")
                    elif len(concept_id_1) == 1:
                        cursor.execute(f"select distinct chi_square_t,concept_id_1,concept_id_2,dataset_id,chi_square_p from PAIRED_CONCEPT_COUNTS_ASSOCIATIONS where concept_id_1={concept_id_1[0]} and concept_id_2 in {tuple(set(concept_id_2))};")
                    elif len(concept_id_2) == 1:
                        cursor.execute(f"select distinct chi_square_t,concept_id_1,concept_id_2,dataset_id,chi_square_p from PAIRED_CONCEPT_COUNTS_ASSOCIATIONS where concept_id_1 in {tuple(set(concept_id_1))} and concept_id_2={concept_id_2[0]};")
                    else:
                        cursor.execute(f"select distinct chi_square_t,concept_id_1,concept_id_2,dataset_id,chi_square_p from PAIRED_CONCEPT_COUNTS_ASSOCIATIONS where concept_id_1 in {tuple(set(concept_id_1))} and concept_id_2 in {tuple(set(concept_id_2))};")
                    res = cursor.fetchall()
                    if len(res) == 0:
                        if len(concept_id_1) == 1 and len(concept_id_2) == 1:
                            cursor.execute(f"select distinct chi_square_t,concept_id_1,concept_id_2,dataset_id,chi_square_p from PAIRED_CONCEPT_COUNTS_ASSOCIATIONS where concept_id_1={concept_id_2[0]} and concept_id_2={concept_id_1[0]};")
                        elif len(concept_id_1) == 1:
                            cursor.execute(f"select distinct chi_square_t,concept_id_1,concept_id_2,dataset_id,chi_square_p from PAIRED_CONCEPT_COUNTS_ASSOCIATIONS where concept_id_1 in {tuple(set(concept_id_2))} and concept_id_2={concept_id_1[0]};")
                        elif len(concept_id_2) == 1:
                            cursor.execute(f"select distinct chi_square_t,concept_id_1,concept_id_2,dataset_id,chi_square_p from PAIRED_CONCEPT_COUNTS_ASSOCIATIONS where concept_id_1={concept_id_2[0]} and concept_id_2 in {tuple(set(concept_id_1))};")
                        else:
                            cursor.execute(f"select distinct chi_square_t,concept_id_1,concept_id_2,dataset_id,chi_square_p from PAIRED_CONCEPT_COUNTS_ASSOCIATIONS where concept_id_1 in {tuple(set(concept_id_2))} and concept_id_2 in {tuple(set(concept_id_1))};")
                        res = cursor.fetchall()
                        if len(res) == 0:
                            pass
                        else:
                            for row in res:
                                if row[3] == dataset_id:
                                    results_array.append({'chi_square': row[0],
                                                            'concept_id_1': row[2],
                                                            'concept_id_2': row[1],
                                                            'dataset_id': row[3],
                                                            'p-value': row[4]})
                    else:
                        for row in res:
                            if row[3] == dataset_id:
                                results_array.append({'chi_square': row[0],
                                                        'concept_id_1': row[1],
                                                        'concept_id_2': row[2],
                                                        'dataset_id': row[3],
                                                        'p-value': row[4]})

                        if len(concept_id_1) == 1 and len(concept_id_2) == 1:
                            cursor.execute(f"select distinct chi_square_t,concept_id_1,concept_id_2,dataset_id,chi_square_p from PAIRED_CONCEPT_COUNTS_ASSOCIATIONS where concept_id_1={concept_id_2[0]} and concept_id_2={concept_id_1[0]};")
                        elif len(concept_id_1) == 1:
                            cursor.execute(f"select distinct chi_square_t,concept_id_1,concept_id_2,dataset_id,chi_square_p from PAIRED_CONCEPT_COUNTS_ASSOCIATIONS where concept_id_1 in {tuple(set(concept_id_2))} and concept_id_2={concept_id_1[0]};")
                        elif len(concept_id_2) == 1:
                            cursor.execute(f"select distinct chi_square_t,concept_id_1,concept_id_2,dataset_id,chi_square_p from PAIRED_CONCEPT_COUNTS_ASSOCIATIONS where concept_id_1={concept_id_2[0]} and concept_id_2 in {tuple(set(concept_id_1))};")
                        else:
                            cursor.execute(f"select distinct chi_square_t,concept_id_1,concept_id_2,dataset_id,chi_square_p from PAIRED_CONCEPT_COUNTS_ASSOCIATIONS where concept_id_1 in {tuple(set(concept_id_2))} and concept_id_2 in {tuple(set(concept_id_1))};")
                        res = cursor.fetchall()
                        if len(res) == 0:
                            pass
                        else:
                            for row in res:
                                if row[3] == dataset_id:
                                    results_array.append({'chi_square': row[0],
                                                            'concept_id_1': row[2],
                                                            'concept_id_2': row[1],
                                                            'dataset_id': row[3],
                                                            'p-value': row[4]})

                else:
                    if len(concept_id_1) == 1 and len(concept_id_2) == 1:
                        cursor.execute(f"select distinct p.chi_square_t,p.concept_id_1,p.concept_id_2,p.dataset_id,p.chi_square_p from PAIRED_CONCEPT_COUNTS_ASSOCIATIONS p inner join CONCEPTS c on p.concept_id_2 = c.concept_id  where p.concept_id_1={concept_id_1[0]} and p.concept_id_2={concept_id_2[0]} and c.domain_id='{domain}';")
                    elif len(concept_id_1) == 1:
                        cursor.execute(f"select distinct p.chi_square_t,p.concept_id_1,p.concept_id_2,p.dataset_id,p.chi_square_p from PAIRED_CONCEPT_COUNTS_ASSOCIATIONS p inner join CONCEPTS c on p.concept_id_2 = c.concept_id  where p.concept_id_1={concept_id_1[0]} and p.concept_id_2 in {tuple(set(concept_id_2))} and c.domain_id='{domain}';")
                    elif len(concept_id_2) == 1:
                        cursor.execute(f"select distinct p.chi_square_t,p.concept_id_1,p.concept_id_2,p.dataset_id,p.chi_square_p from PAIRED_CONCEPT_COUNTS_ASSOCIATIONS p inner join CONCEPTS c on p.concept_id_2 = c.concept_id  where p.concept_id_1 in {tuple(set(concept_id_1))} and p.concept_id_2={concept_id_2[0]} and c.domain_id='{domain}';")
                    else:
                        cursor.execute(f"select distinct p.chi_square_t,p.concept_id_1,p.concept_id_2,p.dataset_id,p.chi_square_p from PAIRED_CONCEPT_COUNTS_ASSOCIATIONS p inner join CONCEPTS c on p.concept_id_2 = c.concept_id  where p.concept_id_1 in {tuple(set(concept_id_1))} and p.concept_id_2 in {tuple(set(concept_id_2))} and c.domain_id='{domain}';")
                    res = cursor.fetchall()
                    if len(res) == 0:
                        if len(concept_id_1) == 1 and len(concept_id_2) == 1:
                            cursor.execute(f"select distinct p.chi_square_t,p.concept_id_1,p.concept_id_2,p.dataset_id,p.chi_square_p from PAIRED_CONCEPT_COUNTS_ASSOCIATIONS p inner join CONCEPTS c on p.concept_id_1 = c.concept_id  where p.concept_id_1={concept_id_2[0]} and p.concept_id_2={concept_id_1[0]} and c.domain_id='{domain}';")
                        elif len(concept_id_1) == 1:
                            cursor.execute(f"select distinct p.chi_square_t,p.concept_id_1,p.concept_id_2,p.dataset_id,p.chi_square_p from PAIRED_CONCEPT_COUNTS_ASSOCIATIONS p inner join CONCEPTS c on p.concept_id_1 = c.concept_id  where p.concept_id_1 in {tuple(set(concept_id_2))} and p.concept_id_2={concept_id_1[0]} and c.domain_id='{domain}';")
                        elif len(concept_id_2) == 1:
                            cursor.execute(f"select distinct p.chi_square_t,p.concept_id_1,p.concept_id_2,p.dataset_id,p.chi_square_p from PAIRED_CONCEPT_COUNTS_ASSOCIATIONS p inner join CONCEPTS c on p.concept_id_1 = c.concept_id  where p.concept_id_1={concept_id_2[0]} and p.concept_id_2 in {tuple(set(concept_id_1))} and c.domain_id='{domain}';")
                        else:
                            cursor.execute(f"select distinct p.chi_square_t,p.concept_id_1,p.concept_id_2,p.dataset_id,p.chi_square_p from PAIRED_CONCEPT_COUNTS_ASSOCIATIONS p inner join CONCEPTS c on p.concept_id_1 = c.concept_id  where p.concept_id_1 in {tuple(set(concept_id_2))} and p.concept_id_2 in {tuple(set(concept_id_1))} and c.domain_id='{domain}';")
                        res = cursor.fetchall()
                        if len(res) == 0:
                            pass
                        else:
                            for row in res:
                                if row[3] == dataset_id:
                                    results_array.append({'chi_square': row[0],
                                                            'concept_id_1': row[2],
                                                            'concept_id_2': row[1],
                                                            'dataset_id': row[3],
                                                            'p-value': row[4]})
                    else:
                        for row in res:
                            if row[3] == dataset_id:
                                results_array.append({'chi_square': row[0],
                                                        'concept_id_1': row[1],
                                                        'concept_id_2': row[2],
                                                        'dataset_id': row[3],
                                                        'p-value': row[4]})

                        if len(concept_id_1) == 1 and len(concept_id_2) == 1:
                            cursor.execute(f"select distinct p.chi_square_t,p.concept_id_1,p.concept_id_2,p.dataset_id,p.chi_square_p from PAIRED_CONCEPT_COUNTS_ASSOCIATIONS p inner join CONCEPTS c on p.concept_id_1 = c.concept_id  where p.concept_id_1={concept_id_2[0]} and p.concept_id_2={concept_id_1[0]} and c.domain_id='{domain}';")
                        elif len(concept_id_1) == 1:
                            cursor.execute(f"select distinct p.chi_square_t,p.concept_id_1,p.concept_id_2,p.dataset_id,p.chi_square_p from PAIRED_CONCEPT_COUNTS_ASSOCIATIONS p inner join CONCEPTS c on p.concept_id_1 = c.concept_id  where p.concept_id_1 in {tuple(set(concept_id_2))} and p.concept_id_2={concept_id_1[0]} and c.domain_id='{domain}';")
                        elif len(concept_id_2) == 1:
                            cursor.execute(f"select distinct p.chi_square_t,p.concept_id_1,p.concept_id_2,p.dataset_id,p.chi_square_p from PAIRED_CONCEPT_COUNTS_ASSOCIATIONS p inner join CONCEPTS c on p.concept_id_1 = c.concept_id  where p.concept_id_1={concept_id_2[0]} and p.concept_id_2 in {tuple(set(concept_id_1))} and c.domain_id='{domain}';")
                        else:
                            cursor.execute(f"select distinct p.chi_square_t,p.concept_id_1,p.concept_id_2,p.dataset_id,p.chi_square_p from PAIRED_CONCEPT_COUNTS_ASSOCIATIONS p inner join CONCEPTS c on p.concept_id_1 = c.concept_id  where p.concept_id_1 in {tuple(set(concept_id_2))} and p.concept_id_2 in {tuple(set(concept_id_1))} and c.domain_id='{domain}';")
                        res = cursor.fetchall()
                        if len(res) == 0:
                            pass
                        else:
                            for row in res:
                                if row[3] == dataset_id:
                                    results_array.append({'chi_square': row[0],
                                                            'concept_id_1': row[2],
                                                            'concept_id_2': row[1],
                                                            'dataset_id': row[3],
                                                            'p-value': row[4]})
        else:
            if isinstance(concept_id_pair, str):
                if domain == "":
                    cursor.execute(f"select distinct chi_square_t,concept_id_1,concept_id_2,dataset_id,chi_square_p from PAIRED_CONCEPT_COUNTS_ASSOCIATIONS where concept_pair_id='{concept_id_pair1}';")
                    res = cursor.fetchall()
                    if len(res) == 0:
                        cursor.execute(f"select distinct chi_square_t,concept_id_1,concept_id_2,dataset_id,chi_square_p from PAIRED_CONCEPT_COUNTS_ASSOCIATIONS where concept_pair_id='{concept_id_pair2}';")
                        res = cursor.fetchall()
                        if len(res) == 0:
                            pass
                        else:
                            for row in res:
                                if row[3] == dataset_id:
                                    results_array.append({'chi_square': row[0],
                                                            'concept_id_1': row[2],
                                                            'concept_id_2': row[1],
                                                            'dataset_id': row[3],
                                                            'p-value': row[4]})
                    else:
                        for row in res:
                            if row[3] == dataset_id:
                                results_array.append({'chi_square': row[0],
                                                        'concept_id_1': row[1],
                                                        'concept_id_2': row[2],
                                                        'dataset_id': row[3],
                                                        'p-value': row[4]})

                        cursor.execute(f"select distinct chi_square_t,concept_id_1,concept_id_2,dataset_id,chi_square_p from PAIRED_CONCEPT_COUNTS_ASSOCIATIONS where concept_pair_id='{concept_id_pair2}';")
                        res = cursor.fetchall()
                        if len(res) == 0:
                            pass
                        else:
                            for row in res:
                                if row[3] == dataset_id:
                                    results_array.append({'chi_square': row[0],
                                                            'concept_id_1': row[2],
                                                            'concept_id_2': row[1],
                                                            'dataset_id': row[3],
                                                            'p-value': row[4]})
                else:
                    cursor.execute(f"select distinct p.chi_square_t,p.concept_id_1,p.concept_id_2,p.dataset_id,p.chi_square_p from PAIRED_CONCEPT_COUNTS_ASSOCIATIONS p inner join CONCEPTS c on p.concept_id_2 = c.concept_id where p.concept_pair_id='{concept_id_pair1}' and c.domain_id='{domain}';")
                    res = cursor.fetchall()
                    if len(res) == 0:
                        cursor.execute(f"select distinct p.chi_square_t,p.concept_id_1,p.concept_id_2,p.dataset_id,p.chi_square_p from PAIRED_CONCEPT_COUNTS_ASSOCIATIONS p inner join CONCEPTS c on p.concept_id_1 = c.concept_id where p.concept_pair_id='{concept_id_pair2}' and c.domain_id='{domain}';")
                        res = cursor.fetchall()
                        if len(res) == 0:
                            pass
                        else:
                            for row in res:
                                if row[3] == dataset_id:
                                    results_array.append({'chi_square': row[0],
                                                            'concept_id_1': row[2],
                                                            'concept_id_2': row[1],
                                                            'dataset_id': row[3],
                                                            'p-value': row[4]})
                    else:
                        for row in res:
                            if row[3] == dataset_id:
                                results_array.append({'chi_square': row[0],
                                                        'concept_id_1': row[1],
                                                        'concept_id_2': row[2],
                                                        'dataset_id': row[3],
                                                        'p-value': row[4]})

                        cursor.execute(f"select distinct p.chi_square_t,p.concept_id_1,p.concept_id_2,p.dataset_id,p.chi_square_p from PAIRED_CONCEPT_COUNTS_ASSOCIATIONS p inner join CONCEPTS c on p.concept_id_1 = c.concept_id where p.concept_pair_id='{concept_id_pair2}' and c.domain_id='{domain}';")
                        res = cursor.fetchall()
                        if len(res) == 0:
                            pass
                        else:
                            for row in res:
                                if row[3] == dataset_id:
                                    results_array.append({'chi_square': row[0],
                                                            'concept_id_1': row[2],
                                                            'concept_id_2': row[1],
                                                            'dataset_id': row[3],
                                                            'p-value': row[4]})
            else:
                if domain == "":
                    if len(concept_id_pair) == 1:
                        cursor.execute(f"select distinct chi_square_t,concept_id_1,concept_id_2,dataset_id,chi_square_p from PAIRED_CONCEPT_COUNTS_ASSOCIATIONS where concept_pair_id='{concept_id_pair1[0]}';")
                    else:
                        cursor.execute(f"select distinct chi_square_t,concept_id_1,concept_id_2,dataset_id,chi_square_p from PAIRED_CONCEPT_COUNTS_ASSOCIATIONS where concept_pair_id in {tuple(set(concept_id_pair1))};")
                    res = cursor.fetchall()
                    if len(res) == 0:
                        if len(concept_id_pair) == 1:
                            cursor.execute(f"select distinct chi_square_t,concept_id_1,concept_id_2,dataset_id,chi_square_p from PAIRED_CONCEPT_COUNTS_ASSOCIATIONS where concept_pair_id='{concept_id_pair2[0]}';")
                        else:
                            cursor.execute(f"select distinct chi_square_t,concept_id_1,concept_id_2,dataset_id,chi_square_p from PAIRED_CONCEPT_COUNTS_ASSOCIATIONS where concept_pair_id in {tuple(set(concept_id_pair2))};")
                        res = cursor.fetchall()
                        if len(res) == 0:
                            pass
                        else:
                            for row in res:
                                if row[3] == dataset_id:
                                    results_array.append({'chi_square': row[0],
                                                            'concept_id_1': row[2],
                                                            'concept_id_2': row[1],
                                                            'dataset_id': row[3],
                                                            'p-value': row[4]})
                    else:
                        for row in res:
                            if row[3] == dataset_id:
                                results_array.append({'chi_square': row[0],
                                                        'concept_id_1': row[1],
                                                        'concept_id_2': row[2],
                                                        'dataset_id': row[3],
                                                        'p-value': row[4]})

                        if len(concept_id_pair) == 1:
                            cursor.execute(f"select distinct chi_square_t,concept_id_1,concept_id_2,dataset_id,chi_square_p from PAIRED_CONCEPT_COUNTS_ASSOCIATIONS where concept_pair_id='{concept_id_pair2[0]}';")
                        else:
                            cursor.execute(f"select distinct chi_square_t,concept_id_1,concept_id_2,dataset_id,chi_square_p from PAIRED_CONCEPT_COUNTS_ASSOCIATIONS where concept_pair_id in {tuple(set(concept_id_pair2))};")
                        res = cursor.fetchall()
                        if len(res) == 0:
                            pass
                        else:
                            for row in res:
                                if row[3] == dataset_id:
                                    results_array.append({'chi_square': row[0],
                                                            'concept_id_1': row[2],
                                                            'concept_id_2': row[1],
                                                            'dataset_id': row[3],
                                                            'p-value': row[4]})
                else:
                    if len(concept_id_pair) == 1:
                        cursor.execute(f"select distinct p.chi_square_t,p.concept_id_1,p.concept_id_2,p.dataset_id,p.chi_square_p from PAIRED_CONCEPT_COUNTS_ASSOCIATIONS p inner join CONCEPTS c on p.concept_id_2 = c.concept_id where p.concept_pair_id='{concept_id_pair1[0]}' and c.domain_id='{domain}';")
                    else:
                        cursor.execute(f"select distinct p.chi_square_t,p.concept_id_1,p.concept_id_2,p.dataset_id,p.chi_square_p from PAIRED_CONCEPT_COUNTS_ASSOCIATIONS p inner join CONCEPTS c on p.concept_id_2 = c.concept_id where p.concept_pair_id in {tuple(set(concept_id_pair1))} and c.domain_id='{domain}';")
                    res = cursor.fetchall()
                    if len(res) == 0:
                        if len(concept_id_pair) == 1:
                            cursor.execute(f"select distinct p.chi_square_t,p.concept_id_1,p.concept_id_2,p.dataset_id,p.chi_square_p from PAIRED_CONCEPT_COUNTS_ASSOCIATIONS p inner join CONCEPTS c on p.concept_id_1 = c.concept_id where p.concept_pair_id='{concept_id_pair2[0]}' and c.domain_id='{domain}';")
                        else:
                            cursor.execute(f"select distinct p.chi_square_t,p.concept_id_1,p.concept_id_2,p.dataset_id,p.chi_square_p from PAIRED_CONCEPT_COUNTS_ASSOCIATIONS p inner join CONCEPTS c on p.concept_id_1 = c.concept_id where p.concept_pair_id in {tuple(set(concept_id_pair2))} and c.domain_id='{domain}';")
                        res = cursor.fetchall()
                        if len(res) == 0:
                            pass
                        else:
                            for row in res:
                                if row[3] == dataset_id:
                                    results_array.append({'chi_square': row[0],
                                                            'concept_id_1': row[2],
                                                            'concept_id_2': row[1],
                                                            'dataset_id': row[3],
                                                            'p-value': row[4]})
                    else:
                        for row in res:
                            if row[3] == dataset_id:
                                results_array.append({'chi_square': row[0],
                                                        'concept_id_1': row[1],
                                                        'concept_id_2': row[2],
                                                        'dataset_id': row[3],
                                                        'p-value': row[4]})

                        if len(concept_id_pair) == 1:
                            cursor.execute(f"select distinct p.chi_square_t,p.concept_id_1,p.concept_id_2,p.dataset_id,p.chi_square_p from PAIRED_CONCEPT_COUNTS_ASSOCIATIONS p inner join CONCEPTS c on p.concept_id_1 = c.concept_id where p.concept_pair_id='{concept_id_pair2[0]}' and c.domain_id='{domain}';")
                        else:
                            cursor.execute(f"select distinct p.chi_square_t,p.concept_id_1,p.concept_id_2,p.dataset_id,p.chi_square_p from PAIRED_CONCEPT_COUNTS_ASSOCIATIONS p inner join CONCEPTS c on p.concept_id_1 = c.concept_id where p.concept_pair_id in {tuple(set(concept_id_pair2))} and c.domain_id='{domain}';")
                        res = cursor.fetchall()
                        if len(res) == 0:
                            pass
                        else:
                            for row in res:
                                if row[3] == dataset_id:
                                    results_array.append({'chi_square': row[0],
                                                            'concept_id_1': row[2],
                                                            'concept_id_2': row[1],
                                                            'dataset_id': row[3],
                                                            'p-value': row[4]})

        if len(results_array) != 0:
            results_array = sorted(results_array, key=lambda x: x['chi_square'], reverse=True)

        return results_array

    def get_relative_frequency(self, concept_id_1=[], concept_id_2=[], concept_id_pair=None, domain='', dataset_id=1):
        """Relative frequency between pairs of concepts.

            Calculates the relative frequency (i.e., conditional probability) between pairs of concepts. Results are
            returned in descending order of relative frequency. Note that due to the randomization of the counts, the
            calcaulted relative frequencies can exceed the limit of 1.0.
            Relative Frequency = Count_1_and_2 / Count_2
            This method has overloaded behavior based on the specified parameters:
                1. concept_id_1 and concept_id_2: Result for the pair (concept_id_1, concept_id_2)
                2. concept_id_1: Results for all pairs of concepts that include concept_id_1
                3. concept_id_1 and domain: Results for all pairs of concepts including concept_id_1 and where concept_id_2
                    belongs to the specified domain

        Args:
            concept_id_1 (optional, list): an OMOP id, e.g., [192855] or [192855, 8507]
            concept_id_2 (optional, list): an OMOP id, e.g., [2008271] or [2008271, 939259] If concept_id_2 is unspecified, then this method
                will return all pairs of concepts with concept_id_1.
            concept_id_pair (optional, str or list): the concatenation of two concept ids, e.g. "192855_2008271" or ["192855_2008271","8507_939259"]
            domain (optional, str): An OMOP domain id, e.g., "Condition", "Drug", "Procedure", etc., to restrict the associated
                concept (concept_id_2) to. If this parameter is not specified, then the domain is unrestricted.
            dataset_id (optional, int): The dataset_id of the dataset to query. Default dataset is the 5-year dataset (1).

        Returns:
            array: an sorted(decreasing relative_frequency) array of dictionaries which contains the relative frequency between pairs of concepts
            example:
            [
                {
                    "concept_2_count": 1494,
                    "concept_id_1": 192855,
                    "concept_id_2": 2008271,
                    "concept_pair_count": 10,
                    "dataset_id": 1,
                    "relative_frequency": 0.006693440428380187
                }
            ]
        """
        if concept_id_pair is None:
            if not isinstance(concept_id_1, list):
                print("Please provide either 'concept_id_1' or 'concept_id_pair'. The 'concept_id_1' in get_relative_frequency should be a list", flush=True)
                return []
            else:
                if len(concept_id_1) == 0:
                    print("The 'concept_id_1' in get_relative_frequency should not be a empty list", flush=True)
                    return []

            if not isinstance(concept_id_2, list):
                print("The 'concept_id_2' in get_relative_frequency should be a list", flush=True)
                return []
        else:
            if isinstance(concept_id_pair, str):
                concept_id_pair1 = concept_id_pair
                concept_id_pair2 = f"{concept_id_pair.split('_')[1]}_{concept_id_pair.split('_')[0]}"
            elif isinstance(concept_id_pair, list):
                if len(concept_id_pair) == 0:
                    print("The 'concept_id_pair' in get_relative_frequency is an empty list", flush=True)
                    return []
                else:
                    concept_id_pair1 = concept_id_pair
                    concept_id_pair2 = [f"{pair.split('_')[1]}_{pair.split('_')[0]}" for pair in concept_id_pair]
            else:
                print("The 'concept_id_pair' in get_relative_frequency should be a str or a list", flush=True)
                return []

        if not isinstance(domain, str):
            print("The 'domain' in get_relative_frequency should be a str", flush=True)
            return []

        if not isinstance(dataset_id, int):
            print("The 'dataset_id' in get_relative_frequency should be an int", flush=True)
            return []
        else:
            if dataset_id == 1 or dataset_id == 2 or dataset_id == 3:
                pass
            else:
                print("The 'dataset_id' in get_relative_frequency should be 1, 2 or 3", flush=True)
                return []

        results_array = []
        cursor = self.connection.cursor()
        if concept_id_pair is None:
            if len(concept_id_2) == 0:
                if domain == "":
                    if len(concept_id_1) == 1:
                        cursor.execute(f"select distinct s.concept_count,p.concept_id_1,p.concept_id_2,p.concept_count,p.dataset_id from PAIRED_CONCEPT_COUNTS_ASSOCIATIONS p inner join SINGLE_CONCEPT_COUNTS s on p.concept_id_2 = s.concept_id and p.dataset_id = s.dataset_id where p.concept_id_1={concept_id_1[0]};")
                    else:
                        cursor.execute(f"select distinct s.concept_count,p.concept_id_1,p.concept_id_2,p.concept_count,p.dataset_id from PAIRED_CONCEPT_COUNTS_ASSOCIATIONS p inner join SINGLE_CONCEPT_COUNTS s on p.concept_id_2 = s.concept_id and p.dataset_id = s.dataset_id where p.concept_id_1 in {tuple(set(concept_id_1))};")
                    res = cursor.fetchall()
                    if len(res) == 0:
                        if len(concept_id_1) == 1:
                            cursor.execute(f"select distinct s.concept_count,p.concept_id_2,p.concept_id_1,p.concept_count,p.dataset_id from PAIRED_CONCEPT_COUNTS_ASSOCIATIONS p inner join SINGLE_CONCEPT_COUNTS s on p.concept_id_1 = s.concept_id and p.dataset_id = s.dataset_id where p.concept_id_2={concept_id_1[0]};")
                        else:
                            cursor.execute(f"select distinct s.concept_count,p.concept_id_2,p.concept_id_1,p.concept_count,p.dataset_id from PAIRED_CONCEPT_COUNTS_ASSOCIATIONS p inner join SINGLE_CONCEPT_COUNTS s on p.concept_id_1 = s.concept_id and p.dataset_id = s.dataset_id where p.concept_id_2 in {tuple(set(concept_id_1))};")
                        res = cursor.fetchall()
                        if len(res) == 0:
                            pass
                        else:
                            for row in res:
                                if row[4] == dataset_id:
                                    results_array.append({'concept_2_count': row[0],
                                                            'concept_id_1': row[1],
                                                            'concept_id_2': row[2],
                                                            'concept_pair_count': row[3],
                                                            'dataset_id_row': row[4],
                                                            'relative_frequency': row[3] / row[0]})
                    else:
                        for row in res:
                            if row[4] == dataset_id:
                                results_array.append({'concept_2_count': row[0],
                                                        'concept_id_1': row[1],
                                                        'concept_id_2': row[2],
                                                        'concept_pair_count': row[3],
                                                        'dataset_id_row': row[4],
                                                        'relative_frequency': row[3] / row[0]})

                        if len(concept_id_1) == 1:
                            cursor.execute(f"select distinct s.concept_count,p.concept_id_2,p.concept_id_1,p.concept_count,p.dataset_id from PAIRED_CONCEPT_COUNTS_ASSOCIATIONS p inner join SINGLE_CONCEPT_COUNTS s on p.concept_id_1 = s.concept_id and p.dataset_id = s.dataset_id where p.concept_id_2={concept_id_1[0]};")
                        else:
                            cursor.execute(f"select distinct s.concept_count,p.concept_id_2,p.concept_id_1,p.concept_count,p.dataset_id from PAIRED_CONCEPT_COUNTS_ASSOCIATIONS p inner join SINGLE_CONCEPT_COUNTS s on p.concept_id_1 = s.concept_id and p.dataset_id = s.dataset_id where p.concept_id_2 in {tuple(set(concept_id_1))};")
                        res = cursor.fetchall()
                        if len(res) == 0:
                            pass
                        else:
                            for row in res:
                                if row[4] == dataset_id:
                                    results_array.append({'concept_2_count': row[0],
                                                            'concept_id_1': row[1],
                                                            'concept_id_2': row[2],
                                                            'concept_pair_count': row[3],
                                                            'dataset_id_row': row[4],
                                                            'relative_frequency': row[3] / row[0]})
                else:
                    if len(concept_id_1) == 1:
                        cursor.execute(f"select distinct s.concept_count,p.concept_id_1,p.concept_id_2,p.concept_count,p.dataset_id from PAIRED_CONCEPT_COUNTS_ASSOCIATIONS p inner join SINGLE_CONCEPT_COUNTS s on p.concept_id_2 = s.concept_id and p.dataset_id = s.dataset_id inner join CONCEPTS c on p.concept_id_2 = c.concept_id where p.concept_id_1={concept_id_1[0]} and c.domain_id='{domain}';")
                    else:
                        cursor.execute(f"select distinct s.concept_count,p.concept_id_1,p.concept_id_2,p.concept_count,p.dataset_id from PAIRED_CONCEPT_COUNTS_ASSOCIATIONS p inner join SINGLE_CONCEPT_COUNTS s on p.concept_id_2 = s.concept_id and p.dataset_id = s.dataset_id inner join CONCEPTS c on p.concept_id_2 = c.concept_id where p.concept_id_1 in {tuple(set(concept_id_1))} and c.domain_id='{domain}';")
                    res = cursor.fetchall()
                    if len(res) == 0:
                        if len(concept_id_1) == 1:
                            cursor.execute(f"select distinct s.concept_count,p.concept_id_2,p.concept_id_1,p.concept_count,p.dataset_id from PAIRED_CONCEPT_COUNTS_ASSOCIATIONS p inner join SINGLE_CONCEPT_COUNTS s on p.concept_id_1 = s.concept_id and p.dataset_id = s.dataset_id inner join CONCEPTS c on p.concept_id_1 = c.concept_id where p.concept_id_2={concept_id_1[0]} and c.domain_id='{domain}';")
                        else:
                            cursor.execute(f"select distinct s.concept_count,p.concept_id_2,p.concept_id_1,p.concept_count,p.dataset_id from PAIRED_CONCEPT_COUNTS_ASSOCIATIONS p inner join SINGLE_CONCEPT_COUNTS s on p.concept_id_1 = s.concept_id and p.dataset_id = s.dataset_id inner join CONCEPTS c on p.concept_id_1 = c.concept_id where p.concept_id_2 in {tuple(set(concept_id_1))} and c.domain_id='{domain}';")
                        res = cursor.fetchall()
                        if len(res) == 0:
                            pass
                        else:
                            for row in res:
                                if row[4] == dataset_id:
                                    results_array.append({'concept_2_count': row[0],
                                                            'concept_id_1': row[1],
                                                            'concept_id_2': row[2],
                                                            'concept_pair_count': row[3],
                                                            'dataset_id_row': row[4],
                                                            'relative_frequency': row[3] / row[0]})
                    else:
                        for row in res:
                            if row[4] == dataset_id:
                                results_array.append({'concept_2_count': row[0],
                                                        'concept_id_1': row[1],
                                                        'concept_id_2': row[2],
                                                        'concept_pair_count': row[3],
                                                        'dataset_id_row': row[4],
                                                        'relative_frequency': row[3] / row[0]})

                        if len(concept_id_1) == 1:
                            cursor.execute(f"select distinct s.concept_count,p.concept_id_2,p.concept_id_1,p.concept_count,p.dataset_id from PAIRED_CONCEPT_COUNTS_ASSOCIATIONS p inner join SINGLE_CONCEPT_COUNTS s on p.concept_id_1 = s.concept_id and p.dataset_id = s.dataset_id inner join CONCEPTS c on p.concept_id_1 = c.concept_id where p.concept_id_2={concept_id_1[0]} and c.domain_id='{domain}';")
                        else:
                            cursor.execute(f"select distinct s.concept_count,p.concept_id_2,p.concept_id_1,p.concept_count,p.dataset_id from PAIRED_CONCEPT_COUNTS_ASSOCIATIONS p inner join SINGLE_CONCEPT_COUNTS s on p.concept_id_1 = s.concept_id and p.dataset_id = s.dataset_id inner join CONCEPTS c on p.concept_id_1 = c.concept_id where p.concept_id_2 in {tuple(set(concept_id_1))} and c.domain_id='{domain}';")
                        res = cursor.fetchall()
                        if len(res) == 0:
                            pass
                        else:
                            for row in res:
                                if row[4] == dataset_id:
                                    results_array.append({'concept_2_count': row[0],
                                                            'concept_id_1': row[1],
                                                            'concept_id_2': row[2],
                                                            'concept_pair_count': row[3],
                                                            'dataset_id_row': row[4],
                                                            'relative_frequency': row[3] / row[0]})
            else:
                if domain == "":
                    if len(concept_id_1) == 1 and len(concept_id_2) == 1:
                        cursor.execute(f"select distinct s.concept_count,p.concept_id_1,p.concept_id_2,p.concept_count,p.dataset_id from PAIRED_CONCEPT_COUNTS_ASSOCIATIONS p inner join SINGLE_CONCEPT_COUNTS s on p.concept_id_2 = s.concept_id and p.dataset_id = s.dataset_id where p.concept_id_1={concept_id_1[0]} and p.concept_id_2={concept_id_2[0]};")
                    elif len(concept_id_1) == 1:
                        cursor.execute(f"select distinct s.concept_count,p.concept_id_1,p.concept_id_2,p.concept_count,p.dataset_id from PAIRED_CONCEPT_COUNTS_ASSOCIATIONS p inner join SINGLE_CONCEPT_COUNTS s on p.concept_id_2 = s.concept_id and p.dataset_id = s.dataset_id where p.concept_id_1={concept_id_1[0]} and p.concept_id_2 in {tuple(set(concept_id_2))};")
                    elif len(concept_id_2) == 1:
                        cursor.execute(f"select distinct s.concept_count,p.concept_id_1,p.concept_id_2,p.concept_count,p.dataset_id from PAIRED_CONCEPT_COUNTS_ASSOCIATIONS p inner join SINGLE_CONCEPT_COUNTS s on p.concept_id_2 = s.concept_id and p.dataset_id = s.dataset_id where p.concept_id_1 in {tuple(set(concept_id_1))} and p.concept_id_2={concept_id_2[0]};")
                    else:
                        cursor.execute(f"select distinct s.concept_count,p.concept_id_1,p.concept_id_2,p.concept_count,p.dataset_id from PAIRED_CONCEPT_COUNTS_ASSOCIATIONS p inner join SINGLE_CONCEPT_COUNTS s on p.concept_id_2 = s.concept_id and p.dataset_id = s.dataset_id where p.concept_id_1 in {tuple(set(concept_id_1))} and p.concept_id_2 in {tuple(set(concept_id_2))};")
                    res = cursor.fetchall()
                    if len(res) == 0:
                        if len(concept_id_1) == 1 and len(concept_id_2) == 1:
                            cursor.execute(f"select distinct s.concept_count,p.concept_id_2,p.concept_id_1,p.concept_count,p.dataset_id from PAIRED_CONCEPT_COUNTS_ASSOCIATIONS p inner join SINGLE_CONCEPT_COUNTS s on p.concept_id_1 = s.concept_id and p.dataset_id = s.dataset_id where p.concept_id_1={concept_id_2[0]} and p.concept_id_2={concept_id_1[0]};")
                        elif len(concept_id_1) == 1:
                            cursor.execute(f"select distinct s.concept_count,p.concept_id_2,p.concept_id_1,p.concept_count,p.dataset_id from PAIRED_CONCEPT_COUNTS_ASSOCIATIONS p inner join SINGLE_CONCEPT_COUNTS s on p.concept_id_1 = s.concept_id and p.dataset_id = s.dataset_id where p.concept_id_1 in {tuple(set(concept_id_2))} and p.concept_id_2={concept_id_1[0]};")
                        elif len(concept_id_2) == 1:
                            cursor.execute(f"select distinct s.concept_count,p.concept_id_2,p.concept_id_1,p.concept_count,p.dataset_id from PAIRED_CONCEPT_COUNTS_ASSOCIATIONS p inner join SINGLE_CONCEPT_COUNTS s on p.concept_id_1 = s.concept_id and p.dataset_id = s.dataset_id where p.concept_id_1={concept_id_2[0]} and p.concept_id_2 in {tuple(set(concept_id_1))};")
                        else:
                            cursor.execute(f"select distinct s.concept_count,p.concept_id_2,p.concept_id_1,p.concept_count,p.dataset_id from PAIRED_CONCEPT_COUNTS_ASSOCIATIONS p inner join SINGLE_CONCEPT_COUNTS s on p.concept_id_1 = s.concept_id and p.dataset_id = s.dataset_id where p.concept_id_1 in {tuple(set(concept_id_2))} and p.concept_id_2 in {tuple(set(concept_id_1))};")
                        res = cursor.fetchall()
                        if len(res) == 0:
                            pass
                        else:
                            for row in res:
                                if row[4] == dataset_id:
                                    results_array.append({'concept_2_count': row[0],
                                                            'concept_id_1': row[1],
                                                            'concept_id_2': row[2],
                                                            'concept_pair_count': row[3],
                                                            'dataset_id_row': row[4],
                                                            'relative_frequency': row[3] / row[0]})
                    else:
                        for row in res:
                            if row[4] == dataset_id:
                                results_array.append({'concept_2_count': row[0],
                                                        'concept_id_1': row[1],
                                                        'concept_id_2': row[2],
                                                        'concept_pair_count': row[3],
                                                        'dataset_id_row': row[4],
                                                        'relative_frequency': row[3] / row[0]})

                        if len(concept_id_1) == 1 and len(concept_id_2) == 1:
                            cursor.execute(f"select distinct s.concept_count,p.concept_id_2,p.concept_id_1,p.concept_count,p.dataset_id from PAIRED_CONCEPT_COUNTS_ASSOCIATIONS p inner join SINGLE_CONCEPT_COUNTS s on p.concept_id_1 = s.concept_id and p.dataset_id = s.dataset_id where p.concept_id_1={concept_id_2[0]} and p.concept_id_2={concept_id_1[0]};")
                        elif len(concept_id_1) == 1:
                            cursor.execute(f"select distinct s.concept_count,p.concept_id_2,p.concept_id_1,p.concept_count,p.dataset_id from PAIRED_CONCEPT_COUNTS_ASSOCIATIONS p inner join SINGLE_CONCEPT_COUNTS s on p.concept_id_1 = s.concept_id and p.dataset_id = s.dataset_id where p.concept_id_1 in {tuple(set(concept_id_2))} and p.concept_id_2={concept_id_1[0]};")
                        elif len(concept_id_2) == 1:
                            cursor.execute(f"select distinct s.concept_count,p.concept_id_2,p.concept_id_1,p.concept_count,p.dataset_id from PAIRED_CONCEPT_COUNTS_ASSOCIATIONS p inner join SINGLE_CONCEPT_COUNTS s on p.concept_id_1 = s.concept_id and p.dataset_id = s.dataset_id where p.concept_id_1={concept_id_2[0]} and p.concept_id_2 in {tuple(set(concept_id_1))};")
                        else:
                            cursor.execute(f"select distinct s.concept_count,p.concept_id_2,p.concept_id_1,p.concept_count,p.dataset_id from PAIRED_CONCEPT_COUNTS_ASSOCIATIONS p inner join SINGLE_CONCEPT_COUNTS s on p.concept_id_1 = s.concept_id and p.dataset_id = s.dataset_id where p.concept_id_1 in {tuple(set(concept_id_2))} and p.concept_id_2 in {tuple(set(concept_id_1))};")
                        res = cursor.fetchall()
                        if len(res) == 0:
                            pass
                        else:
                            for row in res:
                                if row[4] == dataset_id:
                                    results_array.append({'concept_2_count': row[0],
                                                            'concept_id_1': row[1],
                                                            'concept_id_2': row[2],
                                                            'concept_pair_count': row[3],
                                                            'dataset_id_row': row[4],
                                                            'relative_frequency': row[3] / row[0]})

                else:
                    if len(concept_id_1) == 1 and len(concept_id_2) == 1:
                        cursor.execute(f"select distinct s.concept_count,p.concept_id_1,p.concept_id_2,p.concept_count,p.dataset_id from PAIRED_CONCEPT_COUNTS_ASSOCIATIONS p inner join SINGLE_CONCEPT_COUNTS s on p.concept_id_2 = s.concept_id and p.dataset_id = s.dataset_id inner join CONCEPTS c on p.concept_id_2 = c.concept_id where p.concept_id_1={concept_id_1[0]} and p.concept_id_2={concept_id_2[0]} and c.domain_id='{domain}';")
                    elif len(concept_id_1) == 1:
                        cursor.execute(f"select distinct s.concept_count,p.concept_id_1,p.concept_id_2,p.concept_count,p.dataset_id from PAIRED_CONCEPT_COUNTS_ASSOCIATIONS p inner join SINGLE_CONCEPT_COUNTS s on p.concept_id_2 = s.concept_id and p.dataset_id = s.dataset_id inner join CONCEPTS c on p.concept_id_2 = c.concept_id where p.concept_id_1={concept_id_1[0]} and p.concept_id_2 in {tuple(set(concept_id_2))} and c.domain_id='{domain}';")
                    elif len(concept_id_2) == 1:
                        cursor.execute(f"select distinct s.concept_count,p.concept_id_1,p.concept_id_2,p.concept_count,p.dataset_id from PAIRED_CONCEPT_COUNTS_ASSOCIATIONS p inner join SINGLE_CONCEPT_COUNTS s on p.concept_id_2 = s.concept_id and p.dataset_id = s.dataset_id inner join CONCEPTS c on p.concept_id_2 = c.concept_id where p.concept_id_1 in {tuple(set(concept_id_1))} and p.concept_id_2={concept_id_2[0]} and c.domain_id='{domain}';")
                    else:
                        cursor.execute(f"select distinct s.concept_count,p.concept_id_1,p.concept_id_2,p.concept_count,p.dataset_id from PAIRED_CONCEPT_COUNTS_ASSOCIATIONS p inner join SINGLE_CONCEPT_COUNTS s on p.concept_id_2 = s.concept_id and p.dataset_id = s.dataset_id inner join CONCEPTS c on p.concept_id_2 = c.concept_id where p.concept_id_1 in {tuple(set(concept_id_1))} and p.concept_id_2 in {tuple(set(concept_id_2))} and c.domain_id='{domain}';")
                    res = cursor.fetchall()
                    if len(res) == 0:
                        if len(concept_id_1) == 1 and len(concept_id_2) == 1:
                            cursor.execute(f"select distinct s.concept_count,p.concept_id_2,p.concept_id_1,p.concept_count,p.dataset_id from PAIRED_CONCEPT_COUNTS_ASSOCIATIONS p inner join SINGLE_CONCEPT_COUNTS s on p.concept_id_1 = s.concept_id and p.dataset_id = s.dataset_id inner join CONCEPTS c on p.concept_id_1 = c.concept_id where p.concept_id_2={concept_id_1[0]} and p.concept_id_1={concept_id_2[0]} and c.domain_id='{domain}';")
                        elif len(concept_id_1) == 1:
                            cursor.execute(f"select distinct s.concept_count,p.concept_id_2,p.concept_id_1,p.concept_count,p.dataset_id from PAIRED_CONCEPT_COUNTS_ASSOCIATIONS p inner join SINGLE_CONCEPT_COUNTS s on p.concept_id_1 = s.concept_id and p.dataset_id = s.dataset_id inner join CONCEPTS c on p.concept_id_1 = c.concept_id where p.concept_id_2={concept_id_1[0]} and p.concept_id_1 in {tuple(set(concept_id_2))} and c.domain_id='{domain}';")
                        elif len(concept_id_2) == 1:
                            cursor.execute(f"select distinct s.concept_count,p.concept_id_2,p.concept_id_1,p.concept_count,p.dataset_id from PAIRED_CONCEPT_COUNTS_ASSOCIATIONS p inner join SINGLE_CONCEPT_COUNTS s on p.concept_id_1 = s.concept_id and p.dataset_id = s.dataset_id inner join CONCEPTS c on p.concept_id_1 = c.concept_id where p.concept_id_2 in {tuple(set(concept_id_1))} and p.concept_id_1={concept_id_2[0]} and c.domain_id='{domain}';")
                        else:
                            cursor.execute(f"select distinct s.concept_count,p.concept_id_2,p.concept_id_1,p.concept_count,p.dataset_id from PAIRED_CONCEPT_COUNTS_ASSOCIATIONS p inner join SINGLE_CONCEPT_COUNTS s on p.concept_id_1 = s.concept_id and p.dataset_id = s.dataset_id inner join CONCEPTS c on p.concept_id_1 = c.concept_id where p.concept_id_2 in {tuple(set(concept_id_1))} and p.concept_id_1 in {tuple(set(concept_id_2))} and c.domain_id='{domain}';")
                        res = cursor.fetchall()
                        if len(res) == 0:
                            pass
                        else:
                            for row in res:
                                if row[4] == dataset_id:
                                    results_array.append({'concept_2_count': row[0],
                                                            'concept_id_1': row[1],
                                                            'concept_id_2': row[2],
                                                            'concept_pair_count': row[3],
                                                            'dataset_id_row': row[4],
                                                            'relative_frequency': row[3] / row[0]})
                    else:
                        for row in res:
                            if row[4] == dataset_id:
                                results_array.append({'concept_2_count': row[0],
                                                        'concept_id_1': row[1],
                                                        'concept_id_2': row[2],
                                                        'concept_pair_count': row[3],
                                                        'dataset_id_row': row[4],
                                                        'relative_frequency': row[3] / row[0]})

                        if len(concept_id_1) == 1 and len(concept_id_2) == 1:
                            cursor.execute(f"select distinct s.concept_count,p.concept_id_2,p.concept_id_1,p.concept_count,p.dataset_id from PAIRED_CONCEPT_COUNTS_ASSOCIATIONS p inner join SINGLE_CONCEPT_COUNTS s on p.concept_id_1 = s.concept_id and p.dataset_id = s.dataset_id inner join CONCEPTS c on p.concept_id_1 = c.concept_id where p.concept_id_2={concept_id_1[0]} and p.concept_id_1={concept_id_2[0]} and c.domain_id='{domain}';")
                        elif len(concept_id_1) == 1:
                            cursor.execute(f"select distinct s.concept_count,p.concept_id_2,p.concept_id_1,p.concept_count,p.dataset_id from PAIRED_CONCEPT_COUNTS_ASSOCIATIONS p inner join SINGLE_CONCEPT_COUNTS s on p.concept_id_1 = s.concept_id and p.dataset_id = s.dataset_id inner join CONCEPTS c on p.concept_id_1 = c.concept_id where p.concept_id_2={concept_id_1[0]} and p.concept_id_1 in {tuple(set(concept_id_2))} and c.domain_id='{domain}';")
                        elif len(concept_id_2) == 1:
                            cursor.execute(f"select distinct s.concept_count,p.concept_id_2,p.concept_id_1,p.concept_count,p.dataset_id from PAIRED_CONCEPT_COUNTS_ASSOCIATIONS p inner join SINGLE_CONCEPT_COUNTS s on p.concept_id_1 = s.concept_id and p.dataset_id = s.dataset_id inner join CONCEPTS c on p.concept_id_1 = c.concept_id where p.concept_id_2 in {tuple(set(concept_id_1))} and p.concept_id_1={concept_id_2[0]} and c.domain_id='{domain}';")
                        else:
                            cursor.execute(f"select distinct s.concept_count,p.concept_id_2,p.concept_id_1,p.concept_count,p.dataset_id from PAIRED_CONCEPT_COUNTS_ASSOCIATIONS p inner join SINGLE_CONCEPT_COUNTS s on p.concept_id_1 = s.concept_id and p.dataset_id = s.dataset_id inner join CONCEPTS c on p.concept_id_1 = c.concept_id where p.concept_id_2 in {tuple(set(concept_id_1))} and p.concept_id_1 in {tuple(set(concept_id_2))} and c.domain_id='{domain}';")
                        res = cursor.fetchall()
                        if len(res) == 0:
                            pass
                        else:
                            for row in res:
                                if row[4] == dataset_id:
                                    results_array.append({'concept_2_count': row[0],
                                                            'concept_id_1': row[1],
                                                            'concept_id_2': row[2],
                                                            'concept_pair_count': row[3],
                                                            'dataset_id_row': row[4],
                                                            'relative_frequency': row[3] / row[0]})
        else:
            if isinstance(concept_id_pair, str):
                if domain == "":
                    cursor.execute(f"select distinct s.concept_count,p.concept_id_1,p.concept_id_2,p.concept_count,p.dataset_id from PAIRED_CONCEPT_COUNTS_ASSOCIATIONS p inner join SINGLE_CONCEPT_COUNTS s on p.concept_id_2 = s.concept_id and p.dataset_id = s.dataset_id where p.concept_pair_id='{concept_id_pair1}';")
                    res = cursor.fetchall()
                    if len(res) == 0:
                        cursor.execute(f"select distinct s.concept_count,p.concept_id_2,p.concept_id_1,p.concept_count,p.dataset_id from PAIRED_CONCEPT_COUNTS_ASSOCIATIONS p inner join SINGLE_CONCEPT_COUNTS s on p.concept_id_1 = s.concept_id and p.dataset_id = s.dataset_id where p.concept_pair_id='{concept_id_pair2}';")
                        res = cursor.fetchall()
                        if len(res) == 0:
                            pass
                        else:
                            for row in res:
                                if row[4] == dataset_id:
                                    results_array.append({'concept_2_count': row[0],
                                                            'concept_id_1': row[1],
                                                            'concept_id_2': row[2],
                                                            'concept_pair_count': row[3],
                                                            'dataset_id_row': row[4],
                                                            'relative_frequency': row[3] / row[0]})
                    else:
                        for row in res:
                            if row[4] == dataset_id:
                                results_array.append({'concept_2_count': row[0],
                                                        'concept_id_1': row[1],
                                                        'concept_id_2': row[2],
                                                        'concept_pair_count': row[3],
                                                        'dataset_id_row': row[4],
                                                        'relative_frequency': row[3] / row[0]})

                        cursor.execute(f"select distinct s.concept_count,p.concept_id_2,p.concept_id_1,p.concept_count,p.dataset_id from PAIRED_CONCEPT_COUNTS_ASSOCIATIONS p inner join SINGLE_CONCEPT_COUNTS s on p.concept_id_1 = s.concept_id and p.dataset_id = s.dataset_id where p.concept_pair_id='{concept_id_pair2}';")
                        res = cursor.fetchall()
                        if len(res) == 0:
                            pass
                        else:
                            for row in res:
                                if row[4] == dataset_id:
                                    results_array.append({'concept_2_count': row[0],
                                                            'concept_id_1': row[1],
                                                            'concept_id_2': row[2],
                                                            'concept_pair_count': row[3],
                                                            'dataset_id_row': row[4],
                                                            'relative_frequency': row[3] / row[0]})
                else:
                    cursor.execute(f"select distinct s.concept_count,p.concept_id_1,p.concept_id_2,p.concept_count,p.dataset_id from PAIRED_CONCEPT_COUNTS_ASSOCIATIONS p inner join SINGLE_CONCEPT_COUNTS s on p.concept_id_2 = s.concept_id and p.dataset_id = s.dataset_id inner join CONCEPTS c on p.concept_id_2 = c.concept_id where p.concept_pair_id='{concept_id_pair1}' and c.domain_id='{domain}';")
                    res = cursor.fetchall()
                    if len(res) == 0:
                        cursor.execute(f"select distinct s.concept_count,p.concept_id_2,p.concept_id_1,p.concept_count,p.dataset_id from PAIRED_CONCEPT_COUNTS_ASSOCIATIONS p inner join SINGLE_CONCEPT_COUNTS s on p.concept_id_1 = s.concept_id and p.dataset_id = s.dataset_id inner join CONCEPTS c on p.concept_id_1 = c.concept_id where p.concept_pair_id='{concept_id_pair2}' and c.domain_id='{domain}';")
                        res = cursor.fetchall()
                        if len(res) == 0:
                            pass
                        else:
                            for row in res:
                                if row[4] == dataset_id:
                                    results_array.append({'concept_2_count': row[0],
                                                            'concept_id_1': row[1],
                                                            'concept_id_2': row[2],
                                                            'concept_pair_count': row[3],
                                                            'dataset_id_row': row[4],
                                                            'relative_frequency': row[3] / row[0]})
                    else:
                        for row in res:
                            if row[4] == dataset_id:
                                results_array.append({'concept_2_count': row[0],
                                                        'concept_id_1': row[1],
                                                        'concept_id_2': row[2],
                                                        'concept_pair_count': row[3],
                                                        'dataset_id_row': row[4],
                                                        'relative_frequency': row[3] / row[0]})

                        cursor.execute(f"select distinct s.concept_count,p.concept_id_2,p.concept_id_1,p.concept_count,p.dataset_id from PAIRED_CONCEPT_COUNTS_ASSOCIATIONS p inner join SINGLE_CONCEPT_COUNTS s on p.concept_id_1 = s.concept_id and p.dataset_id = s.dataset_id inner join CONCEPTS c on p.concept_id_1 = c.concept_id where p.concept_pair_id='{concept_id_pair2}' and c.domain_id='{domain}';")
                        res = cursor.fetchall()
                        if len(res) == 0:
                            pass
                        else:
                            for row in res:
                                if row[4] == dataset_id:
                                    results_array.append({'concept_2_count': row[0],
                                                            'concept_id_1': row[1],
                                                            'concept_id_2': row[2],
                                                            'concept_pair_count': row[3],
                                                            'dataset_id_row': row[4],
                                                            'relative_frequency': row[3] / row[0]})
            else:
                if domain == "":
                    if len(concept_id_pair) == 1:
                        cursor.execute(f"select distinct s.concept_count,p.concept_id_1,p.concept_id_2,p.concept_count,p.dataset_id from PAIRED_CONCEPT_COUNTS_ASSOCIATIONS p inner join SINGLE_CONCEPT_COUNTS s on p.concept_id_2 = s.concept_id and p.dataset_id = s.dataset_id where p.concept_pair_id='{concept_id_pair1[0]}';")
                    else:
                        cursor.execute(f"select distinct s.concept_count,p.concept_id_1,p.concept_id_2,p.concept_count,p.dataset_id from PAIRED_CONCEPT_COUNTS_ASSOCIATIONS p inner join SINGLE_CONCEPT_COUNTS s on p.concept_id_2 = s.concept_id and p.dataset_id = s.dataset_id where p.concept_pair_id in {tuple(set(concept_id_pair1))};")
                    res = cursor.fetchall()
                    if len(res) == 0:
                        if len(concept_id_pair) == 1:
                            cursor.execute(f"select distinct s.concept_count,p.concept_id_2,p.concept_id_1,p.concept_count,p.dataset_id from PAIRED_CONCEPT_COUNTS_ASSOCIATIONS p inner join SINGLE_CONCEPT_COUNTS s on p.concept_id_1 = s.concept_id and p.dataset_id = s.dataset_id where p.concept_pair_id='{concept_id_pair2[0]}';")
                        else:
                            cursor.execute(f"select distinct s.concept_count,p.concept_id_2,p.concept_id_1,p.concept_count,p.dataset_id from PAIRED_CONCEPT_COUNTS_ASSOCIATIONS p inner join SINGLE_CONCEPT_COUNTS s on p.concept_id_1 = s.concept_id and p.dataset_id = s.dataset_id where p.concept_pair_id in {tuple(set(concept_id_pair2))};")
                        res = cursor.fetchall()
                        if len(res) == 0:
                            pass
                        else:
                            for row in res:
                                if row[4] == dataset_id:
                                    results_array.append({'concept_2_count': row[0],
                                                            'concept_id_1': row[1],
                                                            'concept_id_2': row[2],
                                                            'concept_pair_count': row[3],
                                                            'dataset_id_row': row[4],
                                                            'relative_frequency': row[3] / row[0]})
                    else:
                        for row in res:
                            if row[4] == dataset_id:
                                results_array.append({'concept_2_count': row[0],
                                                        'concept_id_1': row[1],
                                                        'concept_id_2': row[2],
                                                        'concept_pair_count': row[3],
                                                        'dataset_id_row': row[4],
                                                        'relative_frequency': row[3] / row[0]})

                        if len(concept_id_pair) == 1:
                            cursor.execute(f"select distinct s.concept_count,p.concept_id_2,p.concept_id_1,p.concept_count,p.dataset_id from PAIRED_CONCEPT_COUNTS_ASSOCIATIONS p inner join SINGLE_CONCEPT_COUNTS s on p.concept_id_1 = s.concept_id and p.dataset_id = s.dataset_id where p.concept_pair_id='{concept_id_pair2[0]}';")
                        else:
                            cursor.execute(f"select distinct s.concept_count,p.concept_id_2,p.concept_id_1,p.concept_count,p.dataset_id from PAIRED_CONCEPT_COUNTS_ASSOCIATIONS p inner join SINGLE_CONCEPT_COUNTS s on p.concept_id_1 = s.concept_id and p.dataset_id = s.dataset_id where p.concept_pair_id in {tuple(set(concept_id_pair2))};")
                        res = cursor.fetchall()
                        if len(res) == 0:
                            pass
                        else:
                            for row in res:
                                if row[4] == dataset_id:
                                    results_array.append({'concept_2_count': row[0],
                                                            'concept_id_1': row[1],
                                                            'concept_id_2': row[2],
                                                            'concept_pair_count': row[3],
                                                            'dataset_id_row': row[4],
                                                            'relative_frequency': row[3] / row[0]})
                else:
                    if len(concept_id_pair) == 1:
                        cursor.execute(f"select distinct s.concept_count,p.concept_id_1,p.concept_id_2,p.concept_count,p.dataset_id from PAIRED_CONCEPT_COUNTS_ASSOCIATIONS p inner join SINGLE_CONCEPT_COUNTS s on p.concept_id_2 = s.concept_id and p.dataset_id = s.dataset_id inner join CONCEPTS c on p.concept_id_2 = c.concept_id where p.concept_pair_id='{concept_id_pair1[0]}' and c.domain_id='{domain}';")
                    else:
                        cursor.execute(f"select distinct s.concept_count,p.concept_id_1,p.concept_id_2,p.concept_count,p.dataset_id from PAIRED_CONCEPT_COUNTS_ASSOCIATIONS p inner join SINGLE_CONCEPT_COUNTS s on p.concept_id_2 = s.concept_id and p.dataset_id = s.dataset_id inner join CONCEPTS c on p.concept_id_2 = c.concept_id where p.concept_pair_id in {tuple(set(concept_id_pair1))} and c.domain_id='{domain}';")
                    res = cursor.fetchall()
                    if len(res) == 0:
                        if len(concept_id_pair) == 1:
                            cursor.execute(f"select distinct s.concept_count,p.concept_id_2,p.concept_id_1,p.concept_count,p.dataset_id from PAIRED_CONCEPT_COUNTS_ASSOCIATIONS p inner join SINGLE_CONCEPT_COUNTS s on p.concept_id_1 = s.concept_id and p.dataset_id = s.dataset_id inner join CONCEPTS c on p.concept_id_1 = c.concept_id where p.concept_pair_id='{concept_id_pair2[0]}' and c.domain_id='{domain}';")
                        else:
                            cursor.execute(f"select distinct s.concept_count,p.concept_id_2,p.concept_id_1,p.concept_count,p.dataset_id from PAIRED_CONCEPT_COUNTS_ASSOCIATIONS p inner join SINGLE_CONCEPT_COUNTS s on p.concept_id_1 = s.concept_id and p.dataset_id = s.dataset_id inner join CONCEPTS c on p.concept_id_1 = c.concept_id where p.concept_pair_id in {tuple(set(concept_id_pair2))} and c.domain_id='{domain}';")
                        res = cursor.fetchall()
                        if len(res) == 0:
                            pass
                        else:
                            for row in res:
                                if row[4] == dataset_id:
                                    results_array.append({'concept_2_count': row[0],
                                                            'concept_id_1': row[1],
                                                            'concept_id_2': row[2],
                                                            'concept_pair_count': row[3],
                                                            'dataset_id_row': row[4],
                                                            'relative_frequency': row[3] / row[0]})
                    else:
                        for row in res:
                            if row[4] == dataset_id:
                                results_array.append({'concept_2_count': row[0],
                                                        'concept_id_1': row[1],
                                                        'concept_id_2': row[2],
                                                        'concept_pair_count': row[3],
                                                        'dataset_id_row': row[4],
                                                        'relative_frequency': row[3] / row[0]})

                        if len(concept_id_pair) == 1:
                            cursor.execute(f"select distinct s.concept_count,p.concept_id_2,p.concept_id_1,p.concept_count,p.dataset_id from PAIRED_CONCEPT_COUNTS_ASSOCIATIONS p inner join SINGLE_CONCEPT_COUNTS s on p.concept_id_1 = s.concept_id and p.dataset_id = s.dataset_id inner join CONCEPTS c on p.concept_id_1 = c.concept_id where p.concept_pair_id='{concept_id_pair2[0]}' and c.domain_id='{domain}';")
                        else:
                            cursor.execute(f"select distinct s.concept_count,p.concept_id_2,p.concept_id_1,p.concept_count,p.dataset_id from PAIRED_CONCEPT_COUNTS_ASSOCIATIONS p inner join SINGLE_CONCEPT_COUNTS s on p.concept_id_1 = s.concept_id and p.dataset_id = s.dataset_id inner join CONCEPTS c on p.concept_id_1 = c.concept_id where p.concept_pair_id in {tuple(set(concept_id_pair2))} and c.domain_id='{domain}';")
                        res = cursor.fetchall()
                        if len(res) == 0:
                            pass
                        else:
                            for row in res:
                                if row[4] == dataset_id:
                                    results_array.append({'concept_2_count': row[0],
                                                            'concept_id_1': row[1],
                                                            'concept_id_2': row[2],
                                                            'concept_pair_count': row[3],
                                                            'dataset_id_row': row[4],
                                                            'relative_frequency': row[3] / row[0]})

        if len(results_array) != 0:
            results_array = sorted(results_array, key=lambda x: x['relative_frequency'], reverse=True)

        return results_array

    def get_datasets(self):
        """Enumerate the datasets available in COHD.

        Returns:
            array: a list of datasets, including dataset ID, name, and description.
            example:
                [
                    {
                        'dataset_description': "Clinical data from 2013-2017. Each concept's count reflects the use of that specific concept.",
                        'dataset_id': 1,
                        'dataset_name': "5-year non-hierarchical"
                    },
                    {
                        'dataset_description': "Clinical data from all years in the database. Each concept's count reflects the use of that specific concept.",
                        'dataset_id': 2,
                        'dataset_name': "Lifetime non-hierarchical"
                    },
                    {
                        'dataset_description': "Clinical data from 2013-2017. Each concept's count includes use of that concept and descendant concepts.",
                        'dataset_id': 3,
                        'dataset_name': "5-year hierarchical"
                    }
                ]
        """
        results_array = []
        cursor = self.connection.cursor()
        res = cursor.execute(f"select distinct * from DATASET;")
        for row in res:
            results_array.append({
                'dataset_id': row[0],
                'dataset_name': row[1],
                'dataset_description': row[2]
            })

        return results_array

    def get_domain_counts(self, dataset_id=1):
        """The number of concepts in each domain.

        Args:
            dataset_id (required, int): The dataset_id of the dataset to query. Default dataset is the 5-year dataset (1).

        Returns:
            array: a list of domains and the number of concepts in each domain.
        """
        if not isinstance(dataset_id, int):
            print("The 'dataset_id' in get_domain_counts should be an int", flush=True)
            return []
        else:
            if dataset_id == 1 or dataset_id == 2 or dataset_id == 3:
                pass
            else:
                print("The 'dataset_id' in get_domain_counts should be 1, 2 or 3", flush=True)
                return []

        results_array = []
        cursor = self.connection.cursor()
        res = cursor.execute(f"select distinct * from DOMAIN_CONCEPT_COUNTS where dataset_id={dataset_id}")

        domain_dict = dict()
        domain_dict['dataset_id'] = dataset_id
        for row in res:
            domain_dict[row[1]] = row[2]

        results_array.append(domain_dict)

        return results_array

    def get_domain_pair_counts(self, dataset_id=1):
        """The number of pairs of concepts in each pair of domains.

            Args:
                dataset_id (required, int): The dataset_id of the dataset to query. Default dataset is the 5-year dataset (1).

            Returns:
                array:  a list of pairs of domains and the number of pairs of concepts in each.
        """
        if not isinstance(dataset_id, int):
            print("The 'dataset_id' in get_domain_pair_counts should be an int", flush=True)
            return []
        else:
            if dataset_id == 1 or dataset_id == 2 or dataset_id == 3:
                pass
            else:
                print("The 'dataset_id' in get_domain_pair_counts should be 1, 2 or 3", flush=True)
                return []

        results_array = []
        cursor = self.connection.cursor()
        res = cursor.execute(f"select distinct * from DOMAIN_PAIR_CONCEPT_COUNTS where dataset_id={dataset_id}")

        for row in res:
            domain_dict = dict()
            domain_dict['dataset_id'] = row[0]
            domain_dict['domain_1'] = row[1]
            domain_dict['domain_2'] = row[2]
            domain_dict['count'] = row[3]
            results_array.append(domain_dict)

        return results_array

    def get_patient_count(self):
        """The number of patients in the dataset.

            Returns:
                array:  a list of dictionaries which contains the number of patients
                example:
                [
                    {
                        "count": 1790431,
                        "dataset_id": 1
                    }
                ]
        """
        results_array = []
        cursor = self.connection.cursor()
        res = cursor.execute(f"select distinct * from PATIENT_COUNT;")
        for row in res:
            results_array.append({
                'dataset_id': row[0],
                'patient_count': row[1]
            })

        return results_array

####################################################################################################


def main():

    parser = argparse.ArgumentParser(description="Tests or rebuilds the COHD Node Index", formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument('-b', '--build', action="store_true", help="If set, (re)build the index from scratch", default=False)
    parser.add_argument('-t', '--test', action="store_true", help="If set, run a test of the index by doing several lookups", default=False)
    args = parser.parse_args()

    if not args.build and not args.test:
        parser.print_help()
        sys.exit(2)

    cohdIndex = COHDIndex()

    # To (re)build
    if args.build:
        cohdIndex.create_tables()
        cohdIndex.populate_table()
        cohdIndex.create_indexes()

    # Exit here if tests are not requested
    if not args.test:
        return

    print("==== Testing for search for OMOP concept ids by curie id ====", flush=True)
    print(cohdIndex.get_concept_ids('DOID:8398')) # 'HP:0031120' doesn't have omop concept ids

    print("==== Testing for retrieving observed clinical frequencies of a pair of concepts ====", flush=True)
    print(cohdIndex.get_paired_concept_freq(concept_id_1=[192855], concept_id_2=[2008271], dataset_id=3))
    print(cohdIndex.get_paired_concept_freq(concept_id_1=[192855], concept_id_2=[2008271], dataset_id=1))
    print(cohdIndex.get_paired_concept_freq(concept_id_1=[192855], concept_id_2=[2008271], dataset_id=2))
    print(cohdIndex.get_paired_concept_freq(concept_id_1=[192855], concept_id_2=[2008271], dataset_id=3))
    print(cohdIndex.get_paired_concept_freq(concept_id_pair='192855_2008271', dataset_id=2))

    print("==== Testing for retrieving observed clinical frequencies of individual concepts ====", flush=True)
    print(cohdIndex.get_individual_concept_freq(192855))

    print("==== Testing for retrieving observed clinical frequencies of all pairs of concepts given a concept id restricted by domain of the associated concept_id ====", flush=True)
    if len(cohdIndex.get_associated_concept_domain_freq(192855, 'Procedure')) > 0:
        for row in cohdIndex.get_associated_concept_domain_freq(192855, 'Procedure'):
            print(row)

    print("==== Testing for returning the natural logarithm of the ratio between the observed count and expected count ====", flush=True)
    print("The results of get_obs_exp_ratio(concept_id_1=[192855])")
    if len(cohdIndex.get_obs_exp_ratio(concept_id_1=[192855])) > 0:
        for row in cohdIndex.get_obs_exp_ratio(concept_id_1=[192855]):
            print(row)

    print("The results of get_obs_exp_ratio(concept_id_1=[192855],concept_id_2=[2008271]")
    if len(cohdIndex.get_obs_exp_ratio(concept_id_1=[192855], concept_id_2=[2008271])) > 0:
        for row in cohdIndex.get_obs_exp_ratio(concept_id_1=[192855], concept_id_2=[2008271]):
            print(row)

    print("The results of get_obs_exp_ratio(concept_id_1=[192855], concept_id_2=[2008271], domain='Procedure')")
    if len(cohdIndex.get_obs_exp_ratio(concept_id_1=[192855], concept_id_2=[2008271], domain='Procedure')) > 0:
        for row in cohdIndex.get_obs_exp_ratio(concept_id_1=[192855], concept_id_2=[2008271], domain='Procedure'):
            print(row)

    print("The results of get_obs_exp_ratio(concept_id_pair='192855_2008271',domain='Procedure')")
    if len(cohdIndex.get_obs_exp_ratio(concept_id_pair='192855_2008271', domain='Procedure')) > 0:
        for row in cohdIndex.get_obs_exp_ratio(concept_id_pair='192855_2008271', domain='Procedure'):
            print(row)

    print("==== Testing for returning the chi-square statistic and p-value between pairs of concepts ====", flush=True)
    print("The results of get_chi_square(concept_id_1=[192855])")
    if len(cohdIndex.get_chi_square(concept_id_1=[192855])) > 0:
        for row in cohdIndex.get_chi_square(concept_id_1=[192855]):
            print(row)

    print("The results of get_chi_square(concept_id_1=[192855], concept_id_2=[2008271])")
    if len(cohdIndex.get_chi_square(concept_id_1=[192855], concept_id_2=[2008271])) > 0:
        for row in cohdIndex.get_chi_square(concept_id_1=[192855], concept_id_2=[2008271]):
            print(row)

    print("The results of get_chi_square(concept_id_1=[192855], concept_id_2=[2008271],domain='Procedure')")
    if len(cohdIndex.get_chi_square(concept_id_1=[192855], concept_id_2=[2008271], domain='Procedure')) > 0:
        for row in cohdIndex.get_chi_square(concept_id_1=[192855], concept_id_2=[2008271], domain='Procedure'):
            print(row)

    print("The results of get_chi_square(concept_id_pair='192855_2008271', domain='Procedure')")
    if len(cohdIndex.get_chi_square(concept_id_pair='192855_2008271', domain='Procedure')) > 0:
        for row in cohdIndex.get_chi_square(concept_id_pair='192855_2008271', domain='Procedure'):
            print(row)

    print("==== Testing for returning the OMOP concept names and domains for the given list of concept IDs ====", flush=True)
    concept_ids = 2008271
    print(cohdIndex.get_concepts(concept_ids))
    concept_ids = [192855, 2008271]
    for res in cohdIndex.get_concepts(concept_ids):
        print(res)

    print("=== Testing for getting a list of vocabularies ===", flush=True)
    print(cohdIndex.get_vocabularies())

    print("=== Testing for retrieving observed clinical frequencies of all pairs of concepts given a concept id", flush=True)
    for row in cohdIndex.get_associated_concept_freq(192855):
        print(row)

    print("=== Testing for retrieving the most frequent concepts ===", flush=True)
    res = cohdIndex.get_most_frequent_concepts(10, domain="Drug", dataset_id=3)
    for row in res:
        print(row)

    print("=== Testing for getting relative frequency between pairs of concepts ===", flush=True)
    res = cohdIndex.get_relative_frequency(192855, domain='Drug')
    for row in res:
        print(row)

    print("=== Testing for getting datasets available in COHD ===", flush=True)
    res = cohdIndex.get_datasets()
    for row in res:
        print(row)

    print("=== Testing for getting concept count in each domain in given dataset ===", flush=True)
    res = cohdIndex.get_domain_counts(2)
    print(res)

    print("=== Testing for getting concept count in each pair of domains in given dataset ===", flush=True)
    res = cohdIndex.get_domain_pair_counts(3)
    for row in res:
        print(row)

    print("=== Testing for getting patient count of each dataset available in COHD ===", flush=True)
    res = cohdIndex.get_patient_count()
    for row in res:
        print(row)

    print("=== Search for curie ids by OMOP concept ids ===", flush=True)
    res = cohdIndex.get_curies_from_concept_id(192855)
    print(res)

####################################################################################################


if __name__ == "__main__":
    main()


# This script will build a database and query an index of records for KG and COHD

import os
import sys
import re
import timeit
import argparse
import sqlite3

#import internal modules
pathlist = os.path.realpath(__file__).split(os.path.sep)
RTXindex = pathlist.index("RTX")
sys.path.append(os.path.sep.join([*pathlist[:(RTXindex + 1)], 'code', 'reasoningtool', 'QuestionAnswering']))

DEBUG=True


class COHDIndex:

    # Constructor
    def __init__(self):
        filepath = os.path.sep.join([*pathlist[:(RTXindex + 1)], 'code', 'ARAX', 'KnowledgeSources', 'COHD_local', 'data'])
        self.databaseLocation = filepath
        self.lookup_table = {}

        self.databaseName = "COHDIndex.sqlite"
        self.engine_type = "sqlite"

        self.success_con = self.connect()

    # Create and store a database connection
    def connect(self):

        database = f"{self.databaseLocation}/{self.databaseName}"

        if os.path.exists(database):
            self.connection = sqlite3.connect(f"{self.databaseLocation}/{self.databaseName}")
            print("INFO: Connecting to database")
            return True
        else:
            required_files = ['single_concept_counts.txt', 'patient_count.txt', 'domain_pair_concept_counts.txt',
                              'paired_concept_counts_associations.txt', 'domain_concept_counts.txt', 'concepts.txt',
                              'dataset.txt'] #'KG1_OMOP_mapping.pkl']
            has_files = [f for f in os.listdir(self.databaseLocation) if os.path.isfile(os.path.join(self.databaseLocation, f))]
            for file in required_files:
                if file in has_files:
                    pass
                else:
                    print(f"Error: no file '{file}' in {self.databaseLocation}! Please make sure these files {required_files} exist before build database.")
                    return False

            self.connection = sqlite3.connect(f"{self.databaseLocation}/{self.databaseName}")
            print("INFO: Connecting to database")
            return True


    # Destroy the database connection
    def disconnect(self):

        if self.success_con is True:
            self.connection.close()
            print("INFO: Disconnecting from database")
            self.success_con = False
        else:
            print("Info: No database was connected! So skip disconnecting from database.")


    # Delete and create the tables
    def create_tables(self):
        if self.success_con is True:
            print("INFO: Creating database "+self.databaseName)
            #self.connection.execute(f"DROP TABLE IF EXISTS KG1_OMOP_MAPPING")
            #self.connection.execute(f"CREATE TABLE KG1_OMOP_MAPPING( curie VARCHAR(255) PRIMARY KEY, name VARCHAR(255) NOT NULL, type VARCHAR(255) NOT NULL, OMOP_id VARCHAR(255) )")
            self.connection.execute(f"DROP TABLE IF EXISTS SINGLE_CONCEPT_COUNTS")
            self.connection.execute(f"CREATE TABLE SINGLE_CONCEPT_COUNTS( dataset_id TINYINT, concept_id INT, concept_count INT, concept_prevalence FLOAT )")
            self.connection.execute(f"DROP TABLE IF EXISTS CONCEPTS")
            self.connection.execute(f"CREATE TABLE CONCEPTS( concept_id INT PRIMARY KEY, concept_name VARCHAR(255), domain_id VARCHAR(255), vocabulary_id VARCHAR(255), concept_class_id VARCHAR(255), concept_code VARCHAR(255) )")
            self.connection.execute(f"DROP TABLE IF EXISTS PATIENT_COUNT")
            self.connection.execute(f"CREATE TABLE PATIENT_COUNT( dataset_id TINYINT PRIMARY KEY, count INT)")
            self.connection.execute(f"DROP TABLE IF EXISTS DATASET")
            self.connection.execute(f"CREATE TABLE DATASET( dataset_id TINYINT PRIMARY KEY, dataset_name VARCHAR(255), dataset_description VARCHAR(255))")
            self.connection.execute(f"DROP TABLE IF EXISTS DOMAIN_CONCEPT_COUNTS")
            self.connection.execute(f"CREATE TABLE DOMAIN_CONCEPT_COUNTS( dataset_id TINYINT, domain_id VARCHAR(255), count INT)")
            self.connection.execute(f"DROP TABLE IF EXISTS DOMAIN_PAIR_CONCEPT_COUNTS")
            self.connection.execute(f"CREATE TABLE DOMAIN_PAIR_CONCEPT_COUNTS( dataset_id TINYINT, domain_id_1 VARCHAR(255), domain_id_2 VARCHAR(255), count INT)")
            self.connection.execute(f"DROP TABLE IF EXISTS PAIRED_CONCEPT_COUNTS_ASSOCIATIONS")
            self.connection.execute(f"CREATE TABLE PAIRED_CONCEPT_COUNTS_ASSOCIATIONS( dataset_id TINYINT, concept_id_1 INT, concept_id_2 INT, concept_count INT, concept_prevalence FLOAT, chi_square_t FLOAT, chi_square_p FLOAT, expected_count FLOAT, ln_ratio FLOAT, rel_freq_1 FLOAT, rel_freq_2 FLOAT)")

    # Populate the tables
    def populate_table(self):

        # read all tables from COHD database to local database
        COHD_database_files = ['single_concept_counts.txt', 'patient_count.txt', 'domain_pair_concept_counts.txt',
                          'paired_concept_counts_associations.txt', 'domain_concept_counts.txt', 'concepts.txt',
                          'dataset.txt']

        for file_name in COHD_database_files:

            with open(f"{self.databaseLocation}/{file_name}",'r') as file:
                content_list = file.readlines()
                col_name = content_list.pop(0)
                file_content = [tuple(line.strip().split("\t")) for line in content_list]
                current_table_name = file_name.replace('.txt', '').upper()
                print(f"INFO: Populating table {current_table_name}")
                insert_command1 = f"INSERT INTO {current_table_name}("
                insert_command2 = f" values ("
                for col in col_name.strip().split("\t"):
                    insert_command1 = insert_command1+f"{col},"
                    insert_command2 = insert_command2+f"?,"

                insert_command = insert_command1+")"+insert_command2+")"
                insert_command = insert_command.replace(',)', ')')

                if DEBUG:
                    print(insert_command)
                    print(file_content[:10])

                self.connection.executemany(insert_command, file_content)


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

    # Exit here if tests are not requested


####################################################################################################
if __name__ == "__main__":
    main()


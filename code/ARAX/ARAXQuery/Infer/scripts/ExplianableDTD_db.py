
"""This script will build a database for the pre-computation of explainable DTD model.
Author: Chunyu Ma
"""

import os
import sys
import argparse
import sqlite3
import logging
import pandas as pd
import numpy as np
import tqdm

sys.path.append(os.path.dirname(os.path.abspath(__file__)) + "/../../")  # ARAXQuery directory
from ARAX_response import ARAXResponse

# import internal modules
pathlist = os.path.realpath(__file__).split(os.path.sep)
RTXindex = pathlist.index("RTX")
sys.path.append(os.path.sep.join([*pathlist[:(RTXindex + 1)], 'code']))
from RTXConfiguration import RTXConfiguration  #noqa: E402
RTXConfig = RTXConfiguration()
from ARAX_database_manager import ARAXDatabaseManager  #noqa: E402


DEBUG = True

def get_logger(logname):
    """
    Get a logger object
    Args:
        logname (str): path to the log file
    """
    logger = logging.getLogger(logname)
    logger.setLevel(logging.DEBUG)
    formatter = logging.Formatter('%(asctime)s  [%(levelname)s]  %(message)s', datefmt="%Y-%m-%d %H:%M:%S")
    ch = logging.StreamHandler(sys.stdout)
    ch.setFormatter(formatter)
    logger.addHandler(ch)

    return logger

class ExplainableDTD(object):

    # Constructor
    def __init__(self,
                 path_to_score_results=None,
                 path_to_path_results=None,
                 database_name=None,
                 outdir=os.path.sep.join([*pathlist[:(RTXindex + 1)], 'code', 'ARAX', 'KnowledgeSources', 'Prediction']),
                 build=False,
                 response=None):
        """
        Args:
            path_to_score_results (str): path to a folder containing the prediction score results of all diseases
            path_to_path_results (str): path to a folder containing the path results of all diseases
            database_name (str, optional): database name (Defaults: ExplainableDTD.db).
            outdir (str, optional): path to a folder where the database is generated (Defaults: ./).
        """
        self.logger = get_logger('log')
        if response is None:
            self.response = ARAXResponse()
        else:
            self.response = response
        # Property to keep track if the database is already connected or not
        self.is_connected = False
        self.test_iter = 1
        self.success_con = False

        if build:
            if path_to_score_results is None:
                self.logger.error("Please set a path to 'path_to_score_results'")
                raise
            elif not os.path.exists(path_to_score_results) or not len(os.listdir(path_to_score_results)) > 0:
                self.logger.error(f"The given path '{path_to_score_results}' doesn't exist or is an empty folder")
                raise
            else:
                self.path_to_score_results = path_to_score_results
            if path_to_path_results is None:
                self.logger.error("Please set a path to 'path_to_path_results'")
                raise
            elif not os.path.exists(path_to_path_results) or not len(os.listdir(path_to_path_results)) > 0:
                self.logger.error(f"The given path '{path_to_path_results}' doesn't exist or is an empty folder")
                raise
            else:
                self.path_to_path_results = path_to_path_results
            if database_name is None:
                self.database_name = "ExplainableDTD.db"
            else:
                self.database_name = database_name
            if outdir is None:
                self.database_name = './'
            else:
                if not os.path.exists(outdir):
                    os.makedirs(outdir)
                self.outdir = outdir
        else:
            if database_name is None:
                self.database_name = RTXConfig.explainable_dtd_db_path.split("/")[-1]
            else:
                self.database_name = database_name
            if outdir is None:
                self.database_name = './'
            else:
                if not os.path.exists(outdir):
                    os.makedirs(outdir)
                self.outdir = outdir
        self.success_con = self.connect()

    #def __del__(self):
    #    self.disconnect()

    # Create and store a database connection
    def connect(self):
        database = f"{self.outdir}/{self.database_name}"
        if self.is_connected is False:
            # Get if locally
            if os.path.exists(database):
                self.connection = sqlite3.connect(database)
                self.logger.info("Connecting to database")
                self.test_iter += 1
                #self.logger.info(f"Test iteration: {self.test_iter}")
                self.is_connected = True
                return True
            else:
                # get it remotely
                DBmanager = ARAXDatabaseManager()
                if DBmanager.check_versions():
                    raise FileNotFoundError("ARAX database manager indicates that there are missing databases")
                self.connection = sqlite3.connect(database)
                print("INFO: Connecting to database", flush=True)
                self.is_connected = True
                return True
        else:
            return True

    # Destroy the database connection
    def disconnect(self):
        #self.logger.info("Disconnecting from database")
        if self.success_con is True or self.is_connected is True:
            try:
                self.connection.commit()
                self.connection.close()
            except sqlite3.ProgrammingError:
                self.logger.info("Database appears to be already disconnected")
            self.success_con = False
        else:
            self.logger.info("No database was connected! So skip disconnecting from database.")
            return

    # Delete and create the tables
    def create_tables(self):

        if self.success_con is True:
            self.logger.info(f"Creating database {self.database_name}")
            self.connection.execute("DROP TABLE IF EXISTS PREDICTION_SCORE_TABLE")
            self.connection.execute("CREATE TABLE PREDICTION_SCORE_TABLE( drug_id VARCHAR(255), drug_name VARCHAR(255), disease_id VARCHAR(255), disease_name VARCHAR(255), tn_score FLOAT, tp_score FLOAT, unknown_score FLOAT)")
            self.connection.execute("DROP TABLE IF EXISTS PATH_RESULT_TABLE")
            self.connection.execute("CREATE TABLE PATH_RESULT_TABLE(  drug_id VARCHAR(255), drug_name VARCHAR(255), disease_id VARCHAR(255), disease_name VARCHAR(255), path VARCHAR(255), path_score FLOAT )")
            self.logger.info("Creating tables is completed")

    ## Populate the tables
    def populate_table(self):

        if self.success_con is True:
            # save score results to local database
            score_reulst_list = os.listdir(self.path_to_score_results)
            for file_name in tqdm(score_reulst_list):

                with open(f"{self.path_to_score_results}/{file_name}", 'r') as file_in:
                    content_list = file_in.readlines()
                    col_name = content_list.pop(0)
                    insert_command1 = "INSERT INTO PREDICTION_SCORE_TABLE("
                    insert_command2 = " values ("
                    for col in col_name.strip().split("\t"):
                        insert_command1 = insert_command1 + f"{col},"
                        insert_command2 = insert_command2 + "?,"

                    insert_command = insert_command1 + ")" + insert_command2 + ")"
                    insert_command = insert_command.replace(',)', ')')

                    if DEBUG:
                        print(insert_command, flush=True)
                        print(tuple(content_list[0].strip().split("\t")), flush=True)

                    for line in content_list:
                        line = tuple(line.strip().split("\t"))
                        self.connection.execute(insert_command, line)

                    self.connection.commit()
            self.connection.commit()

            # save path results to local database
            path_reulst_list = os.listdir(self.path_to_path_results)
            for file_name in tqdm(path_reulst_list):

                with open(f"{self.path_to_path_results}/{file_name}", 'r') as file_in:
                    content_list = file_in.readlines()
                    col_name = content_list.pop(0)
                    insert_command1 = "INSERT INTO PATH_RESULT_TABLE("
                    insert_command2 = " values ("
                    for col in col_name.strip().split("\t"):
                        insert_command1 = insert_command1 + f"{col},"
                        insert_command2 = insert_command2 + "?,"

                    insert_command = insert_command1 + ")" + insert_command2 + ")"
                    insert_command = insert_command.replace(',)', ')')

                    if DEBUG:
                        print(insert_command, flush=True)
                        print(tuple(content_list[0].strip().split("\t")), flush=True)

                    for line in content_list:
                        line = tuple(line.strip().split("\t"))
                        self.connection.execute(insert_command, line)

                    self.connection.commit()
            self.connection.commit()

            self.logger.info("Populating tables is completed")

    def create_indexes(self):

        if self.success_con is True:
            self.logger.info("Creating INDEXes on PREDICTION_SCORE_TABLE",)
            self.connection.execute("CREATE INDEX idx_PREDICTION_SCORE_TABLE_drug_id ON PREDICTION_SCORE_TABLE(drug_id)")
            self.connection.execute("CREATE INDEX idx_PREDICTION_SCORE_TABLE_drug_name ON PREDICTION_SCORE_TABLE(drug_name)")
            self.connection.execute("CREATE INDEX idx_PREDICTION_SCORE_TABLE_disease_id ON PREDICTION_SCORE_TABLE(disease_id)")
            self.connection.execute("CREATE INDEX idx_PREDICTION_SCORE_TABLE_disease_name ON PREDICTION_SCORE_TABLE(disease_name)")

            self.logger.info("Creating INDEXes on PREDICTION_SCORE_TABLE",)
            self.connection.execute("CREATE INDEX idx_PATH_RESULT_TABLE_drug_id ON PATH_RESULT_TABLE(drug_id)")
            self.connection.execute("CREATE INDEX idx_PATH_RESULT_TABLE_drug_name ON PATH_RESULT_TABLE(drug_name)")
            self.connection.execute("CREATE INDEX idx_PATH_RESULT_TABLE_disease_id ON PATH_RESULT_TABLE(disease_id)")
            self.connection.execute("CREATE INDEX idx_PATH_RESULT_TABLE_disease_name ON PATH_RESULT_TABLE(disease_name)")

            self.logger.info("INFO: Creating INDEXes is completed")

    def get_score_table(self, drug_curie_ids=None, disease_curie_ids=None):
        """get the score table for given drug and/or disease curie ids

        Args:
            drug_curie_ids (str|list): a string of drug curie id or a list of drug curies, e.g. "CHEMBL.COMPOUND:CHEMBL55643" or ["CHEMBL.COMPOUND:CHEMBL55643","CHEBI:6908"]
            disease_curie_ids (str|list): a string of disease curie id or a list of disease curies, e.g. "MONDO:0008753" or ["MONDO:0008753","MONDO:0005148","MONDO:0005155"]

        Returns:
            res_table (pd.DataFrame): the score table for given drug and/or disease curie ids
        """
        
        if drug_curie_ids or disease_curie_ids:
            cursor = self.connection.cursor()
            columns = ["drug_id","drug_name","disease_id","disease_name","tn_score","tp_score","unknown_score"]
            if drug_curie_ids and disease_curie_ids:
                if isinstance(drug_curie_ids, str) and isinstance(disease_curie_ids, str):
                    cursor.execute(f"select drug_id,drug_name,disease_id,disease_name,tn_score,tp_score,unknown_score from PREDICTION_SCORE_TABLE where drug_id='{drug_curie_ids}' and disease_id='{disease_curie_ids}';")
                    res = cursor.fetchall()
                    return pd.DataFrame(res, columns=columns)
                elif isinstance(drug_curie_ids, list) and isinstance(disease_curie_ids, list):
                    cursor.execute(f"select drug_id,drug_name,disease_id,disease_name,tn_score,tp_score,unknown_score from PREDICTION_SCORE_TABLE where drug_id in {tuple(set(drug_curie_ids))} and disease_id in {tuple(set(disease_curie_ids))};")
                    res = cursor.fetchall()
                    return pd.DataFrame(res, columns=columns)
                elif isinstance(drug_curie_ids, str) and isinstance(disease_curie_ids, list):
                    cursor.execute(f"select drug_id,drug_name,disease_id,disease_name,tn_score,tp_score,unknown_score from PREDICTION_SCORE_TABLE where drug_id='{drug_curie_ids}' and disease_id in {tuple(set(disease_curie_ids))};")
                    res = cursor.fetchall()
                    return pd.DataFrame(res, columns=columns)
                elif isinstance(drug_curie_ids, list) and isinstance(disease_curie_ids, str):
                    cursor.execute(f"select drug_id,drug_name,disease_id,disease_name,tn_score,tp_score,unknown_score from PREDICTION_SCORE_TABLE where drug_id in {tuple(set(drug_curie_ids))} and disease_id='{disease_curie_ids}';")
                    res = cursor.fetchall()
                    return pd.DataFrame(res, columns=columns)
                else:
                    print("The 'drug_curie_ids' and 'disease_curie_ids' in get_score_table should be a string or a list", flush=True)
                    return pd.DataFrame([], columns=columns)
            elif drug_curie_ids:
                if isinstance(drug_curie_ids, str):
                    cursor.execute(f"select drug_id,drug_name,disease_id,disease_name,tn_score,tp_score,unknown_score from PREDICTION_SCORE_TABLE where drug_id='{drug_curie_ids}';")
                    res = cursor.fetchall()
                    return pd.DataFrame(res, columns=columns)
                elif isinstance(drug_curie_ids, list):
                    cursor.execute(f"select drug_id,drug_name,disease_id,disease_name,tn_score,tp_score,unknown_score from PREDICTION_SCORE_TABLE where drug_id in {tuple(set(drug_curie_ids))};")
                    res = cursor.fetchall()
                    return pd.DataFrame(res, columns=columns)
                else:
                    print("The 'drug_curie_ids' in get_score_table should be a string or a list", flush=True)
                    return pd.DataFrame([], columns=columns)
            elif disease_curie_ids:
                if isinstance(disease_curie_ids, str):
                    cursor.execute(f"select drug_id,drug_name,disease_id,disease_name,tn_score,tp_score,unknown_score from PREDICTION_SCORE_TABLE where disease_id='{disease_curie_ids}';")
                    res = cursor.fetchall()
                    res_table = pd.DataFrame(res, columns=columns)
                elif isinstance(disease_curie_ids, list):
                    cursor.execute(f"select drug_id,drug_name,disease_id,disease_name,tn_score,tp_score,unknown_score from PREDICTION_SCORE_TABLE where disease_id in {tuple(set(disease_curie_ids))};")
                    res = cursor.fetchall()
                    res_table = pd.DataFrame(res, columns=columns)
                else:
                    print("The 'disease_curie_ids' in get_score_table should be a string or a list", flush=True)
                    res_table = pd.DataFrame([], columns=columns)
                return res_table
        else:
            print("Please provide at least one of drug_curie_ids or disease_curie_ids", flush=True)
            return pd.DataFrame([], columns=columns)

    def get_top_path(self, drug_curie_ids=None, disease_curie_ids=None):
        """get the top path for given drug and/or disease curie ids

        Args:
            drug_curie_ids (str|list): a string of drug curie id or a list of drug curies, e.g. "CHEMBL.COMPOUND:CHEMBL55643" or ["CHEMBL.COMPOUND:CHEMBL55643","CHEBI:6908"]
            disease_curie_ids (str|list): a string of disease curie id or a list of disease curies, e.g. "MONDO:0008753" or ["MONDO:0008753","MONDO:0005148","MONDO:0005155"]

        Returns:
            top_paths (dict): the top paths for given drug and/or disease curie ids
        """
        if drug_curie_ids or disease_curie_ids:
            cursor = self.connection.cursor()
            columns = ["drug_id","drug_name","disease_id","disease_name","path","path_score"]
            top_paths = dict()
            if drug_curie_ids and disease_curie_ids:
                if isinstance(drug_curie_ids, str) and isinstance(disease_curie_ids, str):
                    cursor.execute(f"select drug_id,drug_name,disease_id,disease_name,path,path_score from PATH_RESULT_TABLE where drug_id='{drug_curie_ids}' and disease_id='{disease_curie_ids}';")
                    self._extracted_from_get_top_path(cursor, columns, top_paths)
                elif isinstance(drug_curie_ids, list) and isinstance(disease_curie_ids, list):
                    cursor.execute(f"select drug_id,drug_name,disease_id,disease_name,path,path_score from PATH_RESULT_TABLE where drug_id in {tuple(set(drug_curie_ids))} and disease_id in {tuple(set(disease_curie_ids))};")
                    self._extracted_from_get_top_path(cursor, columns, top_paths)
                elif isinstance(drug_curie_ids, str) and isinstance(disease_curie_ids, list):
                    cursor.execute(f"select drug_id,drug_name,disease_id,disease_name,path,path_score from PATH_RESULT_TABLE where drug_id='{drug_curie_ids}' and disease_id in {tuple(set(disease_curie_ids))};")
                    self._extracted_from_get_top_path(cursor, columns, top_paths)
                elif isinstance(drug_curie_ids, list) and isinstance(disease_curie_ids, str):
                    cursor.execute(f"select drug_id,drug_name,disease_id,disease_name,path,path_score from PATH_RESULT_TABLE where drug_id in {tuple(set(drug_curie_ids))} and disease_id='{disease_curie_ids}';")
                    self._extracted_from_get_top_path(cursor, columns, top_paths)
                else:
                    print("The 'drug_curie_ids' and 'disease_curie_ids' in get_top_path should be a string or a list", flush=True)
                return top_paths
            elif drug_curie_ids:
                if isinstance(drug_curie_ids, str):
                    cursor.execute(f"select drug_id,drug_name,disease_id,disease_name,path,path_score from PATH_RESULT_TABLE where drug_id='{drug_curie_ids}';")
                    self._extracted_from_get_top_path(cursor, columns, top_paths)
                elif isinstance(drug_curie_ids, list):
                    cursor.execute(f"select drug_id,drug_name,disease_id,disease_name,path,path_score from PATH_RESULT_TABLE where drug_id in {tuple(set(drug_curie_ids))};")
                    self._extracted_from_get_top_path(cursor, columns, top_paths)
                else:
                    print("The 'drug_curie_ids' in get_top_path should be a string or a list", flush=True)
                return top_paths
            elif disease_curie_ids:
                if isinstance(disease_curie_ids, str):
                    cursor.execute(f"select drug_id,drug_name,disease_id,disease_name,path,path_score from PATH_RESULT_TABLE where disease_id='{disease_curie_ids}';")
                    self._extracted_from_get_top_path(cursor, columns, top_paths)
                elif isinstance(disease_curie_ids, list):
                    cursor.execute(f"select drug_id,drug_name,disease_id,disease_name,path,path_score from PATH_RESULT_TABLE where disease_id in {tuple(set(disease_curie_ids))};")
                    self._extracted_from_get_top_path(cursor, columns, top_paths)
                else:
                    print("The 'disease_curie_ids' in get_top_path should be a string or a list", flush=True)

                return top_paths
        else:
            print("Please provide at least one of drug_curie_ids or disease_curie_ids", flush=True)
            return dict()

    def _extracted_from_get_top_path(self, cursor, columns, top_paths):
        res = cursor.fetchall()
        temp_df = pd.DataFrame(res, columns=columns)
        for drug_id, disease_id in temp_df[['drug_id','disease_id']].drop_duplicates().values:
            temp = np.array(temp_df.loc[(temp_df['drug_id']==drug_id) & (temp_df['disease_id']==disease_id),['path','path_score']].values).tolist()
            if len(temp) > 0:
                top_paths[(drug_id, disease_id)] = temp

####################################################################################################

def main():

    parser = argparse.ArgumentParser(description="Tests or builds the ExplainableDTD Database", formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument('--build', action="store_true", required=False, help="If set, (re)build the index from scratch", default=False)
    parser.add_argument('--test', action="store_true", required=False, help="If set, run a test of database by doing several lookups", default=False)
    parser.add_argument('--path_to_score_results', type=str, required=True, help="Path to a folder containing the prediction score results of all diseases")
    parser.add_argument('--path_to_path_results', type=str, required=True, help="Path to a folder containing the path results of all diseases")
    parser.add_argument('--database_name', type=str, required=False, help="Database name", default="ExplainableDTD.db")
    parser.add_argument('--outdir', type=str, required=False, help="Path to a folder where the database is generated", default="./")
    args = parser.parse_args()

    if not args.build and not args.test:
        parser.print_help()
        sys.exit(2)

    EDTDdb = ExplainableDTD(args.path_to_score_results, args.path_to_path_results, database_name=args.database_name, outdir=args.outdir)

    # To (re)build
    if args.build:
        EDTDdb.create_tables()
        EDTDdb.populate_table()
        EDTDdb.create_indexes()

    # Exit here if tests are not requested
    if not args.test:
        return

    print("==== Testing for search for top drugs by disease id ====", flush=True)
    print(EDTDdb.get_top_drugs_for_disease('MONDO:0005148'))
    # print(EDTDdb.get_top_drugs_for_disease(["MONDO:0008753","MONDO:0005148","MONDO:0005155"]))

    print("==== Testing for search for top paths by disease id ====", flush=True)
    print(EDTDdb.get_top_paths_for_disease('MONDO:0005148'))
    # print(EDTDdb.get_top_paths_for_disease(["MONDO:0008753","MONDO:0005148","MONDO:0005155"]))

####################################################################################################

if __name__ == "__main__":
    main()

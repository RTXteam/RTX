import os
import pandas as pd
import numpy as np
import sqlite3
try:
    from sklearn.externals import joblib
except:
    try:
        from sklearn.utils import _joblib as joblib
    except:
        import joblib


import sys
pathlist = os.path.realpath(__file__).split(os.path.sep)
RTXindex = pathlist.index("RTX")
sys.path.append(os.path.sep.join([*pathlist[:(RTXindex + 1)], 'code']))
from RTXConfiguration import RTXConfiguration
RTXConfig = RTXConfiguration()
RTXConfig.live = "Production"



class predictor():
    def __init__(self, DTD_prob_file=os.path.sep.join([*pathlist[:(RTXindex + 1)], 'code', 'ARAX', 'KnowledgeSources', 'Prediction', RTXConfig.dtd_prob_path.split('/')[-1]]), model_file=os.path.sep.join([*pathlist[:(RTXindex + 1)], 'code', 'ARAX', 'KnowledgeSources', 'Prediction', RTXConfig.log_model_path.split('/')[-1]]), use_prob_db=True, live = None):
        if live is not None:
            RTXConfig.live = live
            model_file = os.path.sep.join([*pathlist[:(RTXindex + 1)], 'code', 'ARAX', 'KnowledgeSources', 'Prediction', RTXConfig.log_model_path.split('/')[-1]])
            DTD_prob_file = os.path.sep.join([*pathlist[:(RTXindex + 1)], 'code', 'ARAX', 'KnowledgeSources', 'Prediction', RTXConfig.dtd_prob_path.split('/')[-1]])
        self.use_prob_db = use_prob_db
        if self.use_prob_db is True:
            self.connection = sqlite3.connect(DTD_prob_file)
        else:
            self.model = joblib.load(model_file)
            self.graph_cur = None
            self.X = None

    def prob(self, X):
        """
        Predicts the probability of feature vectors being of each class

        :param X: a 2-D numpy array containing the feature vectors
        """
        return self.model.predict_proba(X)

    def predict(self, X):
        """
        Predicts the classes for a numpy array of feature vectors

        :param X: a 2-D numpy array containing the feature vectors
        """
        return self.model.predict(X)

    def get_feature(self, curie_name):
        """
        Retrieve the feature of given curie id from database

        :param curie_name: a curie name
        return a feature list
        """
        if not isinstance(curie_name, str):
            print(f"ERROR: The 'curie_name' has to be a str")
            return None

        row = self.graph_cur.execute(f"select * from GRAPH where curie='{curie_name}'")
        res = row.fetchone()
        if res is None:
            print(f"No curie named '{curie_name}' was found from database")
            return None
        res = list(res)
        res.pop(0)
        return res

    def import_file(self, file, graph_database=os.path.sep.join([*pathlist[:(RTXindex + 1)], 'code', 'ARAX', 'KnowledgeSources', 'Prediction', RTXConfig.graph_database_path.split('/')[-1]]), live = None):
        """
        Imports all necisary files to take curie ids and extract their feature vectors.

        :param file: A string containing the filename or path of a csv containing the source and target curie ids to make predictions on (If set to None will just import the graph and map files)
        :param graph_database: A string containing the filename or path of the sqlite file containing the feature vectors for each node
        """
        #graph = pd.read_csv(graph_file, sep=' ', skiprows=1, header=None, index_col=None)
        #self.graph = graph.sort_values(0).reset_index(drop=True)
        if live is not None:
            RTXConfig.live = live
            graph_database = os.path.sep.join([*pathlist[:(RTXindex + 1)], 'code', 'ARAX', 'KnowledgeSources', 'Prediction', RTXConfig.graph_database_path.split('/')[-1]])
        
        if self.use_prob_db is not True:
            conn = sqlite3.connect(graph_database)
            self.graph_cur = conn.cursor()

            if file is not None:
                data = pd.read_csv(file, index_col=None)

                map_dict = {}
                X_list = []
                drop_list = []
                for row in range(len(data)):
                    source_curie = data['source'][row]
                    target_curie = data['target'][row]
                    source_feature = self.get_feature(source_curie)
                    target_feature = self.get_feature(target_curie)

                    if source_feature is not None and target_feature is not None:
                        X_list += [[a * b for a, b in zip(source_feature, target_feature)]]  # use 'Hadamard product' method instead of 'Concatenate' method
                        #X_list += [list(self.graph.iloc[source_id, 1:]) + list(self.graph.iloc[target_id, 1:])]
                    else:
                        drop_list += [row]

                self.X = np.array(X_list)
                self.data = data.drop(data.index[drop_list]).reset_index(drop=True)
                self.dropped_data = data.iloc[drop_list].reset_index(drop=True)

    def prob_file(self):
        """
        Generate probabilities of the classes of the imported data
        """
        if self.X is None:
            print('Error: Must first run predictor.import_file(<filename>) before calling this method')
            return None
        else:
            return self.prob(self.X)

    def predict_file(self):
        """
        Predicts the classes of the imported data
        """
        if self.X is None:
            print('Error: Must first run predictor.import_file(<filename>) before calling this method')
            return None
        else:
            return self.predict(self.X)

    def build_pred_df(self):
        """
        Builds a dataframe containing the curies used for prediction and both the predicted class and the probability of that class sorted by probability
        """
        probs = self.prob_file()
        preds = self.predict_file()
        df = self.data.copy()
        df['treat_prob'] = [prob[1] for prob in probs]
        df['prediction'] = preds
        df = df.sort_values('treat_prob', ascending=False).reset_index(drop=True)
        return df

    def build_pred_df_all(self):
        """
        Builds a dataframe containing the curies used for prediction and both the predicted class and the probability of that class sorted by probability and appends the curies for which no match was found for
        """
        probs = self.prob_file()
        preds = self.predict_file()
        df = pd.concat([self.data, self.dropped_data])
        df['treat_prob'] = [prob[1] for prob in probs] + [np.nan] * len(self.dropped_data)
        df['prediction'] = list(preds) + [np.nan] * len(self.dropped_data)
        df = df.sort_values('treat_prob', ascending=False).reset_index(drop=True)
        return df

    def predict_single(self, source_curie, target_curie):
        """
        Predicts the class of a single pair of source and target curie ids

        :param source_curie: A string containg the curie id of the source node
        :param target_curie: A string containg the curie id of the target node
        """
        if self.use_prob_db is not True:
            if self.graph_cur is None:
                self.import_file(None)

            source_feature = self.get_feature(source_curie)
            target_feature = self.get_feature(target_curie)
            if source_feature is not None and target_feature is not None:
                X = np.array([[a*b for a,b in zip(source_feature, target_feature)]]) # use 'Hadamard product' method instead of 'Concatenate' method
                #X = np.array([list(self.graph.iloc[source_id, 1:]) + list(self.graph.iloc[target_id, 1:])])
                return self.predict(X)
            elif source_feature is not None:
                pass
                # print(target_curie + ' was not in the largest connected component of graph.')
            elif target_feature is not None:
                pass
                # print(source_curie + ' was not in the largest connected component of graph.')
            else:
                # print(source_curie + ' and ' + target_curie + ' were not in the largest connected component of graph.')
                pass
            return None

    def predict_all(self, source_target_curie_list):
        """
        Predicts the class of multiple pairs of source and target curie ids

        :source_target_curie_list: A list containing a bunch of tuples which contain the curie ids of the source and target nodes
        """
        if self.use_prob_db is not True:
            if self.graph_cur is None:
                self.import_file(None)

            if isinstance(source_target_curie_list, list):

                X_list = []
                for (equiv_source_curie, equiv_target_curie) in source_target_curie_list:

                    source_feature = self.get_feature(equiv_source_curie)
                    target_feature = self.get_feature(equiv_target_curie)

                    if source_feature is not None and target_feature is not None:
                        X_list += [[a * b for a, b in zip(source_feature, target_feature)]]
                    else:
                        continue

                if len(X_list) != 0:
                    X = np.array(X_list)
                    return list(self.predict(X))
                else:
                    return None
            else:

                return None

    def prob_single(self, source_curie, target_curie):
        """
        Generates the probability of a single pair of source and target curie ids being classified as the positive class

        :param source_curie: A string containg the curie id of the source node
        :param target_curie: A string containg the curie id of the target node
        """
        if self.use_prob_db is not True:
            if self.graph_cur is None:
                self.import_file(None)

            source_feature = self.get_feature(source_curie)
            target_feature = self.get_feature(target_curie)
            if source_feature is not None and target_feature is not None:
                X = np.array([[a * b for a, b in zip(source_feature, target_feature)]])  # use 'Hadamard product' method instead of 'Concatenate' method
                # X = np.array([list(self.graph.iloc[source_id, 1:]) + list(self.graph.iloc[target_id, 1:])])
                return self.prob(X)[:, 1]
            elif source_feature is not None:
                # print(target_curie + ' was not in the largest connected component of graph.')
                pass
            elif target_feature is not None:
                # print(source_curie + ' was not in the largest connected component of graph.')
                pass
            else:
                # print(source_curie + ' and ' + target_curie + ' were not in the largest connected component of graph.')
                pass
            return None

    def prob_all(self, source_target_curie_list):
        """
        Generates the probability of multiple pairs of source and target curie ids being classified as the positive class

        :source_target_curie_list: A list containing a bunch of tuples which contain the curie ids of the source and target nodes
        """
        if self.use_prob_db is not True:
            if self.graph_cur is None:
                self.import_file(None)

            if isinstance(source_target_curie_list, list):

                X_list = []
                out_source_target_curie_list = list()
                for (equiv_source_curie, equiv_target_curie) in source_target_curie_list:

                    source_feature = self.get_feature(equiv_source_curie)
                    target_feature = self.get_feature(equiv_target_curie)

                    if source_feature is not None and target_feature is not None:
                        out_source_target_curie_list += [(equiv_source_curie, equiv_target_curie)]
                        X_list += [[a * b for a, b in zip(source_feature, target_feature)]]
                    else:
                        continue
                if len(X_list)!=0:
                    X = np.array(X_list)
                    return [out_source_target_curie_list, list(self.prob(X)[:, 1])]
                else:
                    return None
            else:
                return None

    def get_prob_from_DTD_db(self, source_curie, target_curie):
        """
        Get the probability of a single pair of source and target curie ids from DTD probability database

        :param source_curie: A string containg the curie id of the source node
        :param target_curie: A string containg the curie id of the target node
        """

        if self.use_prob_db is True:
            cursor = self.connection.cursor()
            drug = source_curie
            disease = target_curie

            row = cursor.execute(f"select * from DTD_PROBABILITY where disease = '{disease}' and drug = '{drug}'")
            res = row.fetchone()
            if res is None:
                return None
            else:
                return res[2]

    def get_probs_from_DTD_db_based_on_disease(self, disease_id_list):
        """
        Get the probabilities of all pairs of source and target curie ids from DTD probability database based on given disease ids

        :param disease_id_list: A list containg the curie ids of queried disease
        """

        if self.use_prob_db is True:
            cursor = self.connection.cursor()

            row = cursor.execute(f"select * from DTD_PROBABILITY where disease in {tuple(set(disease_id_list))}")
            res = row.fetchall()
            if len(res)!=0:
                return res
            else:
                return None

    def get_probs_from_DTD_db_based_on_drug(self, drug_id_list):
        """
        Get the probabilities of all pairs of source and target curie ids from DTD probability database based on given drug ids

        :param drug_id_list: A list containg the curie ids of queried drug
        """

        if self.use_prob_db is True:
            cursor = self.connection.cursor()

            if len(drug_id_list) == 0:
                return None
            elif len(drug_id_list) == 1:
                row = cursor.execute(f"select * from DTD_PROBABILITY where drug='{drug_id_list[0]}'")
            else:
                row = cursor.execute(f"select * from DTD_PROBABILITY where drug in {tuple(set(drug_id_list))}")
            res = row.fetchall()
            if len(res)!=0:
                return res
            else:
                return None

    def test(self):
        self.import_file('test_set.csv')
        print('df w/o nodes not in largest connected component:')
        print('------------------------------------------------')
        df = self.build_pred_df()
        print(df)
        print('\n\n')
        print('df with nodes not in largest connected component:')
        print('-------------------------------------------------')
        df_all = self.build_pred_df_all()
        print(df_all)

    def single_test(self):
        # Naproxen and Osteoarthritis:
        print(self.predict_single('ChEMBL:154', 'DOID:8398'))
        # Naproxen and Osteoarthritis w/ HP id:
        print(self.predict_single('ChEMBL:154', 'HP:0002758'))
        # Heparin (blood thinner) and Epistaxis (nosebleed):
        print(self.predict_single('ChEMBL:1909300', 'HP:0000421'))
        # Testing not in lcc message:
        print(self.predict_single(':D', 'DOID:8398'))
        print(self.predict_single('ChEMBL:154', ':D'))
        print(self.predict_single(':D', ':D'))
        print('-------------------------------------------')
        print(self.prob_single('ChEMBL:154', 'DOID:8398'))
        print(self.prob_single('ChEMBL:154', 'HP:0002758'))
        print(self.prob_single('ChEMBL:1909300', 'HP:0000421'))
        print(self.prob_single(':D', 'DOID:8398'))
        print(self.prob_single('ChEMBL:154', ':D'))
        print(self.prob_single(':D', ':D'))



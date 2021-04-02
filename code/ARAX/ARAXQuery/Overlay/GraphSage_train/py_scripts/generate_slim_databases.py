import sys
import os
import pandas as pd
import numpy as np
import sqlite3
import pickle

import argparse

parser = argparse.ArgumentParser()
parser.add_argument("-c", "--cohd", action='store_true')
parser.add_argument("-d", "--dtd", action='store_true')
arguments = parser.parse_args()

pathlist = os.path.realpath(__file__).split(os.path.sep)
RTXindex = pathlist.index("RTX")
sys.path.append(os.path.sep.join([*pathlist[:(RTXindex + 1)], 'code', 'ARAX', 'ARAXQuery']))
from ARAX_query import ARAXQuery
from ARAX_response import ARAXResponse
sys.path.append(os.path.sep.join([*pathlist[:(RTXindex + 1)], 'code', 'ARAX', 'NodeSynonymizer/']))
from node_synonymizer import NodeSynonymizer ##Note: For different version of kg2, use corresponding nodesynonymizer

# Get the file paths for the databases
dtd_filepath = os.path.sep.join([*pathlist[:(RTXindex + 1)], 'code', 'ARAX', 'KnowledgeSources', 'Prediction'])
cohd_filepath = os.path.sep.join([*pathlist[:(RTXindex + 1)], 'code', 'ARAX', 'KnowledgeSources', 'COHD_local', 'data'])

# Import RTX config
sys.path.append(os.path.sep.join([*pathlist[:(RTXindex + 1)], 'code']))
from RTXConfiguration import RTXConfiguration

RTXConfig = RTXConfiguration()

########## paramters ###############
#database = 'COHD' # 'DTD' or 'COHD'
if arguments.cohd:
    database = 'COHD'
elif arguments.dtd:
    database = 'DTD'
else:
    print(f'Neither --dtd not --cohd supplied defaulting to cohd...')
    database = 'COHD'
## if database = 'DTD', provide the path of following database files, default is None
#db_file = None ## example: RTX/code/ARAX/KnowledgeSources/Prediction/GRAPH_v1.0_KG2.3.4.sqlite
#DTD_prob_db_file = None ## example: RTX/code/ARAX/KnowledgeSources/Prediction/DTD_probability_database_v1.0_KG2.3.4.db
## FW: below is an exampe of how you would do the dtd and graph databases
db_file = f"{dtd_filepath}{os.path.sep}{RTXConfig.graph_database_path.split('/')[-1]}"
DTD_prob_db_file = f"{dtd_filepath}{os.path.sep}{RTXConfig.dtd_prob_path.split('/')[-1]}"
## if database = 'COHD', provide the path of following database files, default is None
#cohd_file = '/home/cqm5886/work/RTX/code/ARAX/KnowledgeSources/COHD_local/data/COHDdatabase_v2.0_KG2.3.4.db' ##  example: RTX/code/ARAX/KnowledgeSources/COHD_local/data/COHDdatabase_v2.0_KG2.3.4.db
cohd_file = f"{cohd_filepath}{os.path.sep}{RTXConfig.cohd_database_path.split('/')[-1]}"
#output_folder = '/home/cqm5886/work/RTX/code/ARAX/KnowledgeSources/COHD_local/data/' ## os.getcwd()
cohd_output_folder = f"{cohd_filepath}{os.path.sep}"
dtd_output_folder = f"{dtd_filepath}{os.path.sep}"
if database == 'COHD':
    output_folder = cohd_output_folder
elif database == 'DTD':
    output_folder = dtd_output_folder

cohd_DSL_queries = [
{"operations": {"actions": [
        "add_qnode(id=UMLS:C0015967, key=n00)",
        "add_qnode(category=biolink:ChemicalSubstance, key=n01)",
        "add_qedge(subject=n00, object=n01, key=e00)",
        "expand(edge_key=e00, kp=COHD, COHD_method=paired_concept_freq, COHD_method_percentile=95)",
        "return(message=true, store=false)"
    ]}},
{"operations": {"actions": [
        "add_qnode(id=DOID:10718, key=n00)",
        "add_qnode(category=biolink:ChemicalSubstance, key=n01)",
        "add_qedge(subject=n00, object=n01, key=e00)",
        "expand(edge_key=e00, kp=COHD, COHD_method=observed_expected_ratio, COHD_method_percentile=95)",
        "return(message=true, store=false)"
    ]}},
{"operations": {"actions": [
        "add_qnode(id=DOID:5844, key=n00)",
        "add_qnode(category=biolink:ChemicalSubstance, key=n01)",
        "add_qedge(subject=n00, object=n01, key=e00)",
        "expand(edge_key=e00, kp=COHD, COHD_method=chi_square, COHD_method_percentile=95)",
        "return(message=true, store=false)"
    ]}},
{"operations": {"actions": [
        "create_message",
        "add_qnode(name=DOID:1588, key=n0)",
        "add_qnode(category=biolink:ChemicalSubstance, key=n1)",
        "add_qedge(subject=n0, object=n1, key=e0)",
        "expand(edge_key=e0, kp=ARAX/KG1)",
        "overlay(action=overlay_clinical_info, COHD_method=paired_concept_frequency)",
        "resultify()",
        "return(message=true, store=false)",
    ]}},
{"operations": {"actions": [
        "create_message",
        "add_qnode(name=DOID:1588, key=n0)",
        "add_qnode(category=biolink:ChemicalSubstance, key=n1)",
        "add_qedge(subject=n0, object=n1, key=e0)",
        "expand(edge_key=e0, kp=ARAX/KG1)",
        "overlay(action=overlay_clinical_info, COHD_method=observed_expected_ratio)",
        "resultify()",
        "return(message=true, store=false)",
    ]}},
{"operations": {"actions": [
        "create_message",
        "add_qnode(name=DOID:1588, key=n0)",
        "add_qnode(category=biolink:ChemicalSubstance, key=n1)",
        "add_qedge(subject=n0, object=n1, key=e0)",
        "expand(edge_key=e0, kp=ARAX/KG1)",
        "overlay(action=overlay_clinical_info, COHD_method=chi_square)",
        "resultify()",
        "return(message=true, store=false)",
    ]}},
{"operations": {"actions": [
        "create_message",
        "add_qnode(name=acetaminophen, key=n0)",
        "add_qnode(name=Sotos syndrome, key=n1)",
        "expand(kp=ARAX/KG2)",
        "overlay(action=overlay_clinical_info,COHD_method=paired_concept_frequency,virtual_relation_label=C1,subject_qnode_key=n0,object_qnode_key=n1)",
        "overlay(action=overlay_clinical_info,COHD_method=observed_expected_ratio,virtual_relation_label=C2,subject_qnode_key=n0,object_qnode_key=n1)",
        "overlay(action=overlay_clinical_info,COHD_method=chi_square,virtual_relation_label=C3,subject_qnode_key=n0,object_qnode_key=n1)",
        "resultify()",
        "return(message=true, store=false)"
    ]}},
{"operations": {"actions": [
        "create_message",
        "add_qnode(name=DOID:1588, key=n0)",
        "add_qnode(category=biolink:ChemicalSubstance, key=n1)",
        "add_qedge(subject=n0, object=n1, key=e0)",
        "expand(edge_key=e0, kp=ARAX/KG1)",
        "overlay(action=overlay_clinical_info, paired_concept_frequency=true, subject_qnode_key=n0, object_qnode_key=n1, virtual_relation_label=CP1)",
        "resultify()",
        "return(message=true, store=false)",
    ]}},
{"operations": {"actions": [
        "create_message",
        "add_qnode(name=DOID:1588, key=n0)",
        "add_qnode(category=biolink:ChemicalSubstance, key=n1)",
        "add_qedge(subject=n0, object=n1, key=e0)",
        "expand(edge_key=e0, kp=ARAX/KG1)",
        "overlay(action=overlay_clinical_info,observed_expected_ratio=true, subject_qnode_key=n0, object_qnode_key=n1, virtual_relation_label=CP1)",
        "resultify()",
        "return(message=true, store=false)",
    ]}},
{"operations": {"actions": [
        "create_message",
        "add_qnode(name=DOID:1588, key=n0)",
        "add_qnode(category=biolink:ChemicalSubstance, key=n1)",
        "add_qedge(subject=n0, object=n1, key=e0)",
        "expand(edge_key=e0, kp=ARAX/KG1)",
        "overlay(action=overlay_clinical_info, chi_square=true, subject_qnode_key=n0, object_qnode_key=n1, virtual_relation_label=CP1)",
        "resultify()",
        "return(message=true, store=false)",
    ]}},
{"operations": {"actions": [
        "create_message",
        "add_qnode(name=DOID:1588, key=n0)",
        "add_qnode(category=biolink:ChemicalSubstance, key=n1)",
        "add_qedge(subject=n0, object=n1, key=e0)",
        "expand(edge_key=e0, kp=ARAX/KG1)",
        "overlay(action=overlay_clinical_info, paired_concept_frequency=true, subject_qnode_key=n1, object_qnode_key=n0, virtual_relation_label=V1)",
        "resultify()",
        "return(message=true, store=false)",
    ]}},
{"operations": {"actions": [
        "create_message",
        "add_qnode(name=DOID:1588, key=n0)",
        "add_qnode(category=biolink:ChemicalSubstance, key=n1)",
        "add_qedge(subject=n0, object=n1, key=e0)",
        "expand(edge_key=e0, kp=ARAX/KG1)",
        "overlay(action=overlay_clinical_info, paired_concept_frequency=true)",
        "resultify()",
        "return(message=true, store=false)",
    ]}},
{"operations": {"actions": [
        "create_message",
        "add_qnode(name=UniProtKB:Q13627, key=n0)",
        "add_qnode(category=biolink:ChemicalSubstance, key=n1)",
        "add_qedge(subject=n0, object=n1, key=e0)",
        "expand(edge_key=e0, kp=ARAX/KG1)",
        "overlay(action=overlay_clinical_info, paired_concept_frequency=true, subject_qnode_key=n1, object_qnode_key=n0, virtual_relation_label=V1)",
        "resultify()",
        "return(message=true, store=false)",
    ]}},
{"operations": {"actions": [
        "create_message",
        "add_qnode(name=UniProtKB:Q13627, key=n0)",
        "add_qnode(category=biolink:ChemicalSubstance, key=n1)",
        "add_qedge(subject=n0, object=n1, key=e0)",
        "expand(edge_key=e0, kp=ARAX/KG1)",
        "overlay(action=overlay_clinical_info, paired_concept_frequency=true)",
        "resultify()",
        "return(message=true, store=false)",
    ]}},
{"operations": {"actions": [
        "add_qnode(name=DOID:9406, key=n00)",
        "add_qnode(category=biolink:ChemicalSubstance, is_set=true, key=n01)",
        "add_qnode(category=biolink:Protein, key=n02)",
        "add_qedge(subject=n00, object=n01, key=e00)",
        "add_qedge(subject=n01, object=n02, key=e01)",
        "expand(edge_key=[e00,e01], kp=ARAX/KG1)",
        "overlay(action=overlay_clinical_info, observed_expected_ratio=true, virtual_relation_label=C1, subject_qnode_key=n00, object_qnode_key=n01)",
        "resultify(ignore_edge_direction=true, debug=true)",
        "return(message=true, store=false)"
    ]}},
{"operations": {"actions": [
        "create_message",
        "add_qnode(name=DOID:11830, key=n00)",
        "add_qnode(category=biolink:Protein, is_set=true, key=n01)",
        "add_qnode(category=biolink:ChemicalSubstance, key=n02)",
        "add_qedge(subject=n00, object=n01, key=e00)",
        "add_qedge(subject=n01, object=n02, key=e01, predicate=biolink:molecularly_interacts_with)",
        "expand(edge_key=[e00,e01], kp=ARAX/KG2)",
        # overlay a bunch of clinical info
        "overlay(action=overlay_clinical_info, paired_concept_frequency=true, subject_qnode_key=n00, object_qnode_key=n02, virtual_relation_label=C1)",
        "overlay(action=overlay_clinical_info, observed_expected_ratio=true, subject_qnode_key=n00, object_qnode_key=n02, virtual_relation_label=C2)",
        "overlay(action=overlay_clinical_info, chi_square=true, subject_qnode_key=n00, object_qnode_key=n02, virtual_relation_label=C3)",
        # return results
        "resultify(ignore_edge_direction=true)",
        "return(message=true, store=false)",
    ]}},
{"operations": {"actions": [
        "create_message",
        "add_qnode(name=DOID:11830, key=n00)",
        "add_qnode(category=biolink:ChemicalSubstance, key=n01)",
        "add_qedge(subject=n00, object=n01, key=e00)",
        "expand(edge_key=e00, kp=ARAX/KG2)",
        # overlay a bunch of clinical info
        "overlay(action=overlay_clinical_info, paired_concept_frequency=true)",
        "overlay(action=overlay_clinical_info, observed_expected_ratio=true)",
        "overlay(action=overlay_clinical_info, chi_square=true)",
        # return results
        "resultify(ignore_edge_direction=true)",
        "return(message=true, store=false)",
    ]}},
{"operations": {"actions": [
            "create_message",
            f"add_qnode(id=DOID:11830, key=n00, category=biolink:Disease)",
            "add_qnode(category=biolink:ChemicalSubstance, key=n01)",
            "add_qedge(subject=n00, object=n01, key=e00)",
            "expand(edge_key=e00, kp=ARAX/KG2)",
            "expand(edge_key=e00, kp=BTE)",
            "overlay(action=overlay_clinical_info, observed_expected_ratio=true)",
            # "overlay(action=predict_drug_treats_disease)",
            # "filter_kg(action=remove_edges_by_attribute, edge_attribute=probability_treats, direction=below, threshold=0.75, remove_connected_nodes=true, qnode_key=n01)",
            # "overlay(action=compute_ngd)",
            "resultify(ignore_edge_direction=true)",
            # "filter_results(action=limit_number_of_results, max_results=50)",
            "return(message=true, store=false)",
        ]}}

]

## Below queries are for DTD
dtd_DSL_queries = [
{"operations": {"actions": [
        "add_qnode(name=acetaminophen, key=n0)",
        "add_qnode(name=Sotos syndrome, key=n1)",
        "add_qedge(subject=n0, object=n1, key=e0)",
        "expand(edge_key=e0, kp=DTD, DTD_threshold=0, DTD_slow_mode=True)",
        "return(message=true, store=false)"
    ]}},
{"operations": {"actions": [
"add_qnode(name=acetaminophen, key=n0)",
        "add_qnode(category=disease, key=n1)",
        "add_qedge(subject=n0, object=n1, key=e0)",
        "expand(edge_key=e0, kp=DTD, DTD_threshold=0.8, DTD_slow_mode=True)",
        "return(message=true, store=false)"
    ]}},
{"operations": {"actions": [
        "create_message",
        "add_qnode(id=DOID:9008, key=n0, category=biolink:Disease)",
        "add_qnode(category=biolink:ChemicalSubstance, key=n1)",
        "add_qedge(subject=n0, object=n1, key=e0)",
        "expand(edge_key=e0, kp=ARAX/KG1)",
        "overlay(action=predict_drug_treats_disease, subject_qnode_key=n1, object_qnode_key=n0, virtual_relation_label=P1)",
        "resultify()",
        "return(message=true, store=false)"
    ]}},
{"operations": {"actions": [
        "create_message",
        "add_qnode(id=DOID:9008, key=n0)",
        "add_qnode(category=biolink:ChemicalSubstance, key=n1)",
        "add_qedge(subject=n0, object=n1, key=e0)",
        "expand(edge_key=e0, kp=ARAX/KG1)",
        "overlay(action=predict_drug_treats_disease)",
        "resultify()",
        "return(message=true, store=false)"
    ]}},
{"operations": {"actions": [
        "create_message",
        "add_qnode(id=DOID:9008, key=n0)",
        "add_qnode(category=biolink:ChemicalSubstance, key=n1)",
        "add_qedge(subject=n0, object=n1, key=e0)",
        "expand(edge_key=e0, kp=ARAX/KG1)",
        "overlay(action=predict_drug_treats_disease, subject_qnode_key=n1, object_qnode_key=n0, virtual_relation_label=P1)",
        "resultify()",
        "return(message=true, store=false)"
    ]}},
{"operations": {"actions": [
        "create_message",
        "add_qnode(id=UniProtKB:Q13627, key=n0)",
        "add_qnode(category=biolink:ChemicalSubstance, key=n1)",
        "add_qedge(subject=n0, object=n1, key=e0)",
        "expand(edge_key=e0, kp=ARAX/KG1)",
        "overlay(action=predict_drug_treats_disease, subject_qnode_key=n1, object_qnode_key=n0, virtual_relation_label=P1)",
        "resultify()",
        "return(message=true, store=false)",
    ]}},
{"operations": {"actions": [
        "add_qnode(id=DOID:11830, category=biolink:Disease, key=n00)",
        "add_qnode(category=biolink:Gene, id=[UniProtKB:P39060, UniProtKB:O43829, UniProtKB:P20849], is_set=true, key=n01)",
        "add_qnode(category=biolink:ChemicalSubstance, key=n02)",
        "add_qedge(subject=n00, object=n01, key=e00)",
        "add_qedge(subject=n01, object=n02, key=e01)",
        "expand(kp=BTE)",
        "overlay(action=predict_drug_treats_disease, subject_qnode_key=n02, object_qnode_key=n00, virtual_relation_label=P1)",
        "resultify(ignore_edge_direction=true)",
        "return(message=true, store=false)"
    ]}},
{"operations": {"actions": [
        "create_message",
        "add_qnode(name=DOID:14330, key=n00)",
        "add_qnode(category=biolink:Protein, is_set=true, key=n01)",
        "add_qnode(category=biolink:ChemicalSubstance, key=n02)",
        "add_qedge(subject=n00, object=n01, key=e00)",
        "add_qedge(subject=n01, object=n02, key=e01, predicate=biolink:physically_interacts_with)",
        "expand(edge_key=[e00,e01], kp=ARAX/KG1)",
        "overlay(action=compute_jaccard, start_node_key=n00, intermediate_node_key=n01, end_node_key=n02, virtual_relation_label=J1)",
        "filter_kg(action=remove_edges_by_attribute, edge_attribute=jaccard_index, direction=below, threshold=.2, remove_connected_nodes=t, qnode_key=n02)",
        "filter_kg(action=remove_edges_by_property, edge_property=provided_by, property_value=Pharos)",
        "overlay(action=predict_drug_treats_disease, subject_qnode_key=n02, object_qnode_key=n00, virtual_relation_label=P1)",
        "return(message=true, store=false)",
    ]}},
{"operations": {"actions": [
            "create_message",
            f"add_qnode(id=DOID:11830, key=n00, category=biolink:Disease)",
            "add_qnode(category=biolink:ChemicalSubstance, key=n01)",
            "add_qedge(subject=n00, object=n01, key=e00)",
            "expand(edge_key=e00, kp=ARAX/KG2)",
            "expand(edge_key=e00, kp=BTE)",
            "overlay(action=overlay_clinical_info, observed_expected_ratio=true)",
            "overlay(action=predict_drug_treats_disease)",
            "return(message=true, store=false)",
        ]}}
]
# # example:
# [{"operations": {"actions": [
#         "add_qnode(name=acetaminophen, key=n0)",
#         "add_qnode(name=Sotos syndrome, key=n1)",
#         "add_qedge(subject=n0, object=n1, key=e0)",
#         "expand(edge_key=e0, kp=DTD, DTD_threshold=0, DTD_slow_mode=True)",
#         "return(message=true, store=false)"
# ]}},
# {"operations": {"actions": [
# "add_qnode(name=acetaminophen, key=n0)",
#         "add_qnode(category=disease, key=n1)",
#         "add_qedge(subject=n0, object=n1, key=e0)",
#         "expand(edge_key=e0, kp=DTD, DTD_threshold=0.8, DTD_slow_mode=True)",
#         "return(message=true, store=false)"
# ]}},
# {"operations": {"actions": [
#         "create_message",
#         "add_qnode(id=DOID:9008, key=n0, category=biolink:Disease)",
#         "add_qnode(category=biolink:ChemicalSubstance, key=n1)",
#         "add_qedge(subject=n0, object=n1, key=e0)",
#         "expand(edge_key=e0, kp=ARAX/KG1)",
#         # "overlay(action=predict_drug_treats_disease, subject_qnode_key=n1, object_qnode_key=n0, virtual_relation_label=P1)",
#         "resultify()",
#         "return(message=true, store=false)",
#     ]}}
# ]

#####################################

if database == 'COHD':
    DSL_queries = cohd_DSL_queries
elif database == 'DTD':
    DSL_queries = dtd_DSL_queries

########### Below is the main code to run script ##################
araxq = ARAXQuery()
response = ARAXResponse()
synonymizer = NodeSynonymizer()

target_curie_list = []
check_wrong_queries = []
for index, query in enumerate(DSL_queries):
    # print(query)
    result = araxq.query(query)
    response = araxq.response
    if result.status != 'OK':
        # print(response.show(level=ARAXResponse.DEBUG))
        check_wrong_queries += [index + 1]
    else:
        message = response.envelope.message
        target_curie_list += [node_key for node_key, _ in message.knowledge_graph.nodes.items()]

if database == 'DTD':
    if len(check_wrong_queries) != 0:
        print(f'Something wrong occurred in these DSL queries {check_wrong_queries}')
        exit()
    else:
        target_curie_list = list(set(target_curie_list))
        target_curie_list = [synonymizer.get_canonical_curies(curie)[curie]['preferred_curie'] for curie in target_curie_list if synonymizer.get_canonical_curies(curie)[curie] is not None]
        # print(target_curie_list)
        if os.path.isfile(DTD_prob_db_file):
            ## pull all data from `DTD_probability_database.db` database
            con = sqlite3.connect(DTD_prob_db_file)
            table = pd.read_sql_query("SELECT * from DTD_PROBABILITY", con)
            con.close()
            drug_list = [synonymizer.get_canonical_curies(curie)[curie]['preferred_curie'] for curie in target_curie_list if synonymizer.get_canonical_curies(curie)[curie] is not None and synonymizer.get_canonical_curies(curie)[curie]['preferred_category'] in ['drug','chemical_substance','biolink:Drug','biolink:ChemicalSubstance']]
            disease_list = [synonymizer.get_canonical_curies(curie)[curie]['preferred_curie'] for curie in target_curie_list if synonymizer.get_canonical_curies(curie)[curie] is not None and synonymizer.get_canonical_curies(curie)[curie]['preferred_category'] in ['disease','disease_or_phenotypic_feature','phenotypic_feature', 'biolink:Disease','biolink:DiseaseOrPhenotypicFeature','biolink:PhenotypicFeature']]
            table = table.loc[table.disease.isin(disease_list) & table.drug.isin(drug_list),:]
            for col in table.columns:
                table[col] = table[col].astype(str)
            databasefile = list(table.to_records(index=False))
            print(f"Start building the slim version of DTD_probability_database_slim.db", flush=True)
            #con = sqlite3.connect(os.path.join(output_folder, 'DTD_probability_database_slim.db'))
            con = sqlite3.connect(DTD_prob_db_file.replace(".db", "_slim.db"))
            con.execute(f"DROP TABLE IF EXISTs DTD_PROBABILITY")
            con.execute(f"CREATE TABLE DTD_PROBABILITY( disease VARCHAR(255), drug VARCHAR(255), probability FLOAT )")
            insert_command = "INSERT INTO DTD_PROBABILITY VALUES (?, ?, ?)"

            print(f"INFO: Populating table", flush=True)
            insert_command = "INSERT INTO DTD_PROBABILITY VALUES (?, ?, ?)"
            batch = list(range(0 ,len(databasefile), 5000))
            batch.append(len(databasefile))
            count = 0
            for i in range(len(batch)):
                if((i+1) < len(batch)):
                    start = batch[i]
                    end = batch[i+1]
                    rows = databasefile[start:end]
                    con.executemany(insert_command, rows)
                    con.commit()
                    count = count + len(rows)
                    percentage = round((count * 100.0 / len(databasefile)), 2)
                    print(str(percentage) + "%..", end='', flush=True)

            print(f"INFO: Populating tables is completed", flush=True)

            print(f"INFO: Creating INDEXes on DTD_PROBABILITY", flush=True)
            con.execute(f"CREATE INDEX idx_DTD_PROBABILITY_disease ON DTD_PROBABILITY(disease)")
            con.execute(f"CREATE INDEX idx_DTD_PROBABILITY_drug ON DTD_PROBABILITY(drug)")
            con.commit()
            con.close()
            print(f"INFO: Creating INDEXes is completed", flush=True)
        else:
            print(f'Not found {DTD_prob_db_file}')
            exit(0)

        if os.path.isfile(db_file):
            con = sqlite3.connect(db_file)
            table = con.execute(f"select * from GRAPH where curie in {tuple(target_curie_list)}")
            table = pd.DataFrame(table)
            for col in table.columns:
                table[col] = table[col].astype(str)
            databasefile = list(table.to_records(index=False))
            con.close()
            print(f"Start building the slim version of GRAPH_slim.db", flush=True)
            #con = sqlite3.connect(os.path.join(output_folder, 'GRAPH_slim.sqlite'))
            con = sqlite3.connect(db_file.replace(".sqlite", "_slim.sqlite"))
            insert_command1 = f"CREATE TABLE GRAPH(curie VARCHAR(255)"
            for num in range(1,table.shape[1]):
                insert_command1 = insert_command1 + f", col{num} INT"
            insert_command1 = insert_command1 + ")"
            con.execute(insert_command1)
            con.commit()
            print(f"INFO: Populating table", flush=True)
            insert_command1 = f"INSERT INTO GRAPH"
            insert_command2 = f" values ("
            for col in range(table.shape[1]):
                insert_command2 = insert_command2 + f"?,"
            insert_command = insert_command1 + insert_command2 + ")"
            insert_command = insert_command.replace(',)', ')')
            batch = list(range(0 ,len(databasefile), 5000))
            batch.append(len(databasefile))
            count = 0
            for i in range(len(batch)):
                if((i+1) < len(batch)):
                    start = batch[i]
                    end = batch[i+1]
                    rows = databasefile[start:end]
                    con.executemany(insert_command, rows)
                    con.commit()
                    count = count + len(rows)
                    percentage = round((count * 100.0 / len(databasefile)), 2)
                    print(str(percentage) + "%..", end='', flush=True)

            print(f"INFO: Populating tables is completed", flush=True)

            con.execute(f"CREATE INDEX idx_GRAPH_curie ON GRAPH(curie)")
            con.commit()
            con.close()
            print(f"INFO: Database created successfully", flush=True)
        else:
            print(f'Not found {db_file}')
            exit(0)

elif database == 'COHD':
    if len(check_wrong_queries) != 0:
        print(f'Something wrong occurred in these DSL queries {check_wrong_queries}')
        exit()
    else:
        target_curie_list = list(set(target_curie_list))
        target_curie_list = [synonymizer.get_canonical_curies(curie)[curie]['preferred_curie'] for curie in target_curie_list if synonymizer.get_canonical_curies(curie)[curie] is not None]
        # print(target_curie_list)
        if os.path.isfile(cohd_file):
            con = sqlite3.connect(cohd_file)
            curie_to_omop_mapping = con.execute(f"select * from CURIE_TO_OMOP_MAPPING where preferred_curie in {tuple(target_curie_list)}")
            curie_to_omop_mapping = pd.DataFrame(curie_to_omop_mapping)
            cursor = con.execute(f"select * from CURIE_TO_OMOP_MAPPING")
            names = list(map(lambda x: x[0], cursor.description))
            curie_to_omop_mapping.columns = names

            single_concept_counts = con.execute(f"select * from SINGLE_CONCEPT_COUNTS where concept_id in {tuple(list(curie_to_omop_mapping.concept_id))}")
            single_concept_counts = pd.DataFrame(single_concept_counts)
            cursor = con.execute(f"select * from SINGLE_CONCEPT_COUNTS")
            names = list(map(lambda x: x[0], cursor.description))
            single_concept_counts.columns = names

            concepts = con.execute(f"select * from CONCEPTS where concept_id in {tuple(list(curie_to_omop_mapping.concept_id))}")
            concepts = pd.DataFrame(concepts)
            cursor = con.execute(f"select * from CONCEPTS")
            names = list(map(lambda x: x[0], cursor.description))
            concepts.columns = names

            patient_count = pd.read_sql_query("SELECT * from PATIENT_COUNT", con)
            dataset = pd.read_sql_query("SELECT * from DATASET", con)
            domain_concept_counts = pd.read_sql_query("SELECT * from DOMAIN_CONCEPT_COUNTS", con)
            domain_pair_concept_counts = pd.read_sql_query("SELECT * from DOMAIN_PAIR_CONCEPT_COUNTS", con)

            paired_concept_counts_associations = con.execute(f"select * from PAIRED_CONCEPT_COUNTS_ASSOCIATIONS where concept_id_1 in {tuple(list(curie_to_omop_mapping.concept_id))} and concept_id_2 in {tuple(list(curie_to_omop_mapping.concept_id))}")
            paired_concept_counts_associations = pd.DataFrame(paired_concept_counts_associations)
            cursor = con.execute(f"select * from PAIRED_CONCEPT_COUNTS_ASSOCIATIONS")
            names = list(map(lambda x: x[0], cursor.description))
            paired_concept_counts_associations.columns = names
            con.close()
            all_tables = [curie_to_omop_mapping, single_concept_counts, concepts, patient_count, dataset, domain_concept_counts, domain_pair_concept_counts, paired_concept_counts_associations]
            all_table_names = ['CURIE_TO_OMOP_MAPPING', 'SINGLE_CONCEPT_COUNTS', 'CONCEPTS', 'PATIENT_COUNT', 'DATASET', 'DOMAIN_CONCEPT_COUNTS', 'DOMAIN_PAIR_CONCEPT_COUNTS', 'PAIRED_CONCEPT_COUNTS_ASSOCIATIONS']
            # data = [all_tables, all_table_names]
            # with open(os.path.join(output_folder,'temp.pkl'),'wb') as outfile:
            #     pickle.dump(data, outfile)
            #################################################
            print(f"Start building the slim version of COHDdatabase.db", flush=True)
            #con = sqlite3.connect(os.path.join(output_folder, 'COHDdatabase_slim.db'))
            con = sqlite3.connect(cohd_file.replace(".db", "_slim.db"))
            con.execute(f"DROP TABLE IF EXISTS CURIE_TO_OMOP_MAPPING")
            con.execute(f"CREATE TABLE CURIE_TO_OMOP_MAPPING( preferred_curie VARCHAR(255), concept_id INT )")
            con.execute(f"DROP TABLE IF EXISTS SINGLE_CONCEPT_COUNTS")
            con.execute(f"CREATE TABLE SINGLE_CONCEPT_COUNTS( dataset_id TINYINT, concept_id INT, concept_count INT, concept_prevalence FLOAT )")
            con.execute(f"DROP TABLE IF EXISTS CONCEPTS")
            con.execute(f"CREATE TABLE CONCEPTS( concept_id INT PRIMARY KEY, concept_name VARCHAR(255), domain_id VARCHAR(255), vocabulary_id VARCHAR(255), concept_class_id VARCHAR(255), concept_code VARCHAR(255) )")
            con.execute(f"DROP TABLE IF EXISTS PATIENT_COUNT")
            con.execute(f"CREATE TABLE PATIENT_COUNT( dataset_id TINYINT PRIMARY KEY, count INT)")
            con.execute(f"DROP TABLE IF EXISTS DATASET")
            con.execute(f"CREATE TABLE DATASET( dataset_id TINYINT PRIMARY KEY, dataset_name VARCHAR(255), dataset_description VARCHAR(255))")
            con.execute(f"DROP TABLE IF EXISTS DOMAIN_CONCEPT_COUNTS")
            con.execute(f"CREATE TABLE DOMAIN_CONCEPT_COUNTS( dataset_id TINYINT, domain_id VARCHAR(255), count INT)")
            con.execute(f"DROP TABLE IF EXISTS DOMAIN_PAIR_CONCEPT_COUNTS")
            con.execute(f"CREATE TABLE DOMAIN_PAIR_CONCEPT_COUNTS( dataset_id TINYINT, domain_id_1 VARCHAR(255), domain_id_2 VARCHAR(255), count INT)")
            con.execute(f"DROP TABLE IF EXISTS PAIRED_CONCEPT_COUNTS_ASSOCIATIONS")
            con.execute(f"CREATE TABLE PAIRED_CONCEPT_COUNTS_ASSOCIATIONS( concept_pair_id VARCHAR(255), dataset_id TINYINT, concept_id_1 INT, concept_id_2 INT, concept_count INT, concept_prevalence FLOAT, chi_square_t FLOAT, chi_square_p FLOAT, expected_count FLOAT, ln_ratio FLOAT, rel_freq_1 FLOAT, rel_freq_2 FLOAT)")

            print(f"INFO: Creating tables is completed", flush=True)
            # ################################################

            for index in range(len(all_table_names)):
                table_name = all_table_names[index]
                print(f"Start building {table_name}", flush=True)
                table = all_tables[index]
                for col in table.columns:
                    table[col] = table[col].astype(str)
                databasefile = list(table.to_records(index=False))
                insert_command1 = f"INSERT INTO {table_name}"
                insert_command2 = f" values ("
                for col in range(table.shape[1]):
                    insert_command2 = insert_command2 + f"?,"
                insert_command = insert_command1 + insert_command2 + ")"
                insert_command = insert_command.replace(',)', ')')
                batch = list(range(0 ,len(databasefile), 5000))
                batch.append(len(databasefile))
                count = 0
                for i in range(len(batch)):
                    if((i+1) < len(batch)):
                        start = batch[i]
                        end = batch[i+1]
                        rows = databasefile[start:end]
                        con.executemany(insert_command, rows)
                        con.commit()
                        count = count + len(rows)
                        percentage = round((count * 100.0 / len(databasefile)), 2)
                        print(str(percentage) + "%..", end='', flush=True)

                print(f"INFO: Populating tables is completed", flush=True)
                con.commit()
            # ################################################
            print(f"INFO: Creating INDEXes on CURIE_TO_OMOP_MAPPING", flush=True)
            con.execute(f"CREATE INDEX idx_CURIE_TO_OMOP_MAPPING_preferred_curie ON CURIE_TO_OMOP_MAPPING(preferred_curie)")
            con.execute(f"CREATE INDEX idx_CURIE_TO_OMOP_MAPPING_concept_id ON CURIE_TO_OMOP_MAPPING(concept_id)")

            print(f"INFO: Creating INDEXes on SINGLE_CONCEPT_COUNTS", flush=True)
            con.execute(f"CREATE INDEX idx_SINGLE_CONCEPT_COUNTS_dataset_id ON SINGLE_CONCEPT_COUNTS(dataset_id)")
            con.execute(f"CREATE INDEX idx_SINGLE_CONCEPT_COUNTS_concept_id ON SINGLE_CONCEPT_COUNTS(concept_id)")

            print(f"INFO: Creating INDEXes on CONCEPTS", flush=True)
            con.execute(f"CREATE INDEX idx_CONCEPTS_concept_id ON CONCEPTS(concept_id)")

            print(f"INFO: Creating INDEXes on PAIRED_CONCEPT_COUNTS_ASSOCIATIONS", flush=True)
            con.execute(f"CREATE INDEX idx_PAIRED_CONCEPT_COUNTS_ASSOCIATIONS_dataset_id ON PAIRED_CONCEPT_COUNTS_ASSOCIATIONS(dataset_id)")
            con.execute(f"CREATE INDEX idx_PAIRED_CONCEPT_COUNTS_ASSOCIATIONS_concept_pair_id ON PAIRED_CONCEPT_COUNTS_ASSOCIATIONS(concept_pair_id)")
            con.execute(f"CREATE INDEX idx_PAIRED_CONCEPT_COUNTS_ASSOCIATIONS_concept_id_1 ON PAIRED_CONCEPT_COUNTS_ASSOCIATIONS(concept_id_1)")
            con.execute(f"CREATE INDEX idx_PAIRED_CONCEPT_COUNTS_ASSOCIATIONS_concept_id_2 ON PAIRED_CONCEPT_COUNTS_ASSOCIATIONS(concept_id_2)")

            print(f"INFO: Creating INDEXes is completed", flush=True)

        else:
            print(f'Not found {cohd_file}')
            exit(0)
else:
    print(f"This script only supports 'COHD' or 'DTD'")
import sys
import os
import pandas as pd
import numpy as np
import sqlite3
import argparse

def refresh_drug(curie, synonymizer):

    if curie is not None:
        res = synonymizer.get_canonical_curies(curie)
        if res[curie] is not None and res[curie]['preferred_category'] in ['biolink:Drug','biolink:ChemicalSubstance']:
            return res[curie]['preferred_curie']
        else:
            return None
    else:
        return None

def refresh_disease(curie, synonymizer):

    if curie is not None:
        res = synonymizer.get_canonical_curies(curie)
        if res[curie] is not None and res[curie]['preferred_category'] in ['biolink:Disease','biolink:DiseaseOrPhenotypicFeature','biolink:PhenotypicFeature']:
            return res[curie]['preferred_curie']
        else:
            return None
    else:
        return None

def main():

    parser = argparse.ArgumentParser(description="Refresh DTD model and database", formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument('--synoymizer_folder', type=str, help="Full path of folder containing NodeSynonymizer", default='~/RTX/code/ARAX/NodeSynonymizer/')
    parser.add_argument('--DTD_prob_db_file', type=str, help="Full path of DTD probability database file", default='~/work/RTX/code/ARAX/KnowledgeSources/Prediction/DTD_probability_database_v1.0_KG2.3.4.db')
    parser.add_argument('--emb_file', type=str, help="Full path of DTD model embedding file", default='~/work/RTX/code/ARAX/KnowledgeSources/Prediction/rel_max_v1.0_KG2.3.4.emb.gz')
    parser.add_argument('--map_file', type=str, help="Full path of DTD model mapping file", default='~/work/RTX/code/ARAX/KnowledgeSources/Prediction/map_v1.0_KG2.3.4.txt')
    parser.add_argument('--output_folder', type=str, help="Full path of output folder", default='~/work/RTX/code/ARAX/KnowledgeSources/Prediction/')
    args = parser.parse_args()

    if os.path.isdir(args.synoymizer_folder):
        sys.path.append(args.synoymizer_folder)
        from node_synonymizer import NodeSynonymizer
        synonymizer = NodeSynonymizer()
    else:
        print(f"Error: Not found this folder: {args.synoymizer_folder}")
        exit(0)

    if os.path.isfile(args.DTD_prob_db_file):
        print(f'Start to refresh DTD_probability_database.db', flush=True)
        con = sqlite3.connect(args.DTD_prob_db_file)
        DTD_prob_table = pd.read_sql_query("SELECT * from DTD_PROBABILITY", con)
        con.close()
        DTD_prob_table = DTD_prob_table.apply(lambda row: [refresh_disease(row[0], synonymizer),refresh_drug(row[1], synonymizer),row[2]], axis=1, result_type='expand')
        DTD_prob_table = DTD_prob_table.dropna().reset_index(drop=True)
        con = sqlite3.connect(os.path.join(args.output_folder, 'DTD_probability_database_refreshed.db'))
        con.execute(f"CREATE TABLE DTD_PROBABILITY( disease VARCHAR(255), drug VARCHAR(255), probability FLOAT )")
        insert_command = "INSERT INTO DTD_PROBABILITY VALUES (?, ?, ?)"
        databasefile = list(DTD_prob_table.to_records(index=False))

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
        print(f"Error: Not found this file: {args.DTD_prob_db_file}")
        exit(0)

    if os.path.isfile(args.emb_file) and os.path.isfile(args.map_file):
        rel_max = pd.read_csv(args.emb_file, sep=' ', skiprows=1, header=None)
        mapfile = pd.read_csv(args.map_file, sep='\t', header=0)
        merged_table = mapfile.merge(rel_max, left_on='id', right_on=0)
        merged_table = merged_table.loc[:,['curie']+list(merged_table.columns)[3:]]
        new_curie_ids = [synonymizer.get_canonical_curies(curie)[curie]['preferred_curie'] if synonymizer.get_canonical_curies(curie)[curie] is not None else None for curie in list(merged_table.curie)]
        graph = pd.concat([pd.DataFrame(new_curie_ids), merged_table.iloc[:,1:]], axis=1)
        graph = graph.dropna().reset_index(drop=True)

        con = sqlite3.connect(os.path.join(args.output_folder, 'GRAPH_refreshed.sqlite'))
        con.execute(f"DROP TABLE IF EXISTs GRAPH")
        insert_command1 = f"CREATE TABLE GRAPH(curie VARCHAR(255)"
        for num in range(1,graph.shape[1]):
            insert_command1 = insert_command1 + f", col{num} INT"
        insert_command1 = insert_command1 + ")"
        con.execute(insert_command1)
        con.commit()

        count = 0

        print(f"Insert data into database", flush=True)
        for row in range(graph.shape[0]):
            count = count + 1
            insert_command1 = f"INSERT INTO GRAPH"
            insert_command2 = f" values ("

            for _ in range(graph.shape[1]):
                insert_command2 = insert_command2 + f"?,"

            insert_command = insert_command1 + insert_command2 + ")"
            insert_command = insert_command.replace(',)', ')')
            line = tuple(graph.loc[row, :])
            con.execute(insert_command, line)
            if count%5000==0:
                con.commit()
                percentage = int(count*100.0/graph.shape[0])
                print(str(percentage) + "%..", end='', flush=True)

        con.commit()
        percentage = int(count*100.0/graph.shape[0])
        print(str(percentage) + "%..", end='', flush=True)

        con.execute(f"CREATE INDEX idx_GRAPH_curie ON GRAPH(curie)")
        con.commit()
        con.close()
        print(f"INFO: Database created successfully", flush=True)

####################################################################################################

if __name__ == "__main__":
    main()
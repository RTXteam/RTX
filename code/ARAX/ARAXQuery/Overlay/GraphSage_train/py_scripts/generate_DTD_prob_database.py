import pandas as pd
import argparse
import sqlite3
import pickle
import os

parser = argparse.ArgumentParser()
parser.add_argument("-i", "--inputfolder", type=str, help="The path of folder containing individual disease's results")
parser.add_argument("-o", "--outpath", type=str, help="The output path")

args = parser.parse_args()

file_list = os.listdir(args.inputfolder)
databasefile = pd.concat([pd.read_csv(os.path.join(args.inputfolder, file_name), sep='\t', header=None) for file_name in file_list]).rename(columns={0:'disease', 1:'drug', 2:'prob'})
lastest_version = "v1.0"

## generate database text file
outfile = f"{args.outpath}/databasefile_{lastest_version}.pkl"
with open(args.outpath + '/databasefile.pkl', 'wb') as file:
    pickle.dump(databasefile, file)

## generate database sqlite3 file
databaseName = f"DTD_probability_database_{lastest_version}.db"
database = f"{args.outpath}/{databaseName}"
connection = sqlite3.connect(database)
print("INFO: Connecting to database", flush=True)
print("INFO: Creating database " + databaseName, flush=True)
connection.execute(f"DROP TABLE IF EXISTS CURIE_TO_OMOP_MAPPING")
connection.execute(f"CREATE TABLE DTD_PROBABILITY( disease VARCHAR(255), drug VARCHAR(255), probability FLOAT )")
databasefile = list(databasefile.to_records(index=False))

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
        connection.executemany(insert_command, rows)
        connection.commit()
        count = count + len(rows)
        percentage = round((count * 100.0 / len(databasefile)), 2)
        print(str(percentage) + "%..", end='', flush=True)

print(f"INFO: Populating tables is completed", flush=True)

print(f"INFO: Creating INDEXes on DTD_PROBABILITY", flush=True)
connection.execute(f"CREATE INDEX idx_DTD_PROBABILITY_disease ON DTD_PROBABILITY(disease)")
connection.execute(f"CREATE INDEX idx_DTD_PROBABILITY_drug ON DTD_PROBABILITY(drug)")

print(f"INFO: Creating INDEXes is completed", flush=True)

import pandas as pd
import sqlite3
import argparse

parser = argparse.ArgumentParser()
parser.add_argument("-e", "--embfile", type=str, help="The path of .emb file")
parser.add_argument("-m", "--mapfile", type=str, help="The path of map.txt file")
parser.add_argument("-o", "--output", type=str, help="The path of output folder")
args = parser.parse_args()

conn = sqlite3.connect(args.output + '/GRAPH_v1.0.sqlite')

graph = pd.read_csv(args.embfile, sep=' ', skiprows=1, header=None, index_col=None)
graph = graph.sort_values(0).reset_index(drop=True)
map_df = pd.read_csv(args.mapfile, sep='\t', index_col=None)
graph.loc[:, 0] = map_df.loc[:, 'curie']

conn.execute(f"DROP TABLE IF EXISTs GRAPH")

insert_command1 = f"CREATE TABLE GRAPH(curie VARCHAR(255)"

for num in range(1,graph.shape[1]):
    insert_command1 = insert_command1 + f", col{num} INT"
insert_command1 = insert_command1 + ")"

conn.execute(insert_command1)
conn.commit()

count = 0

print(f"Insert data into database", flush=True)
for row in range(graph.shape[0]):
    count = count + 1
    insert_command1 = f"INSERT INTO GRAPH"
    insert_command2 = f" values ("

    for col in range(graph.shape[1]):
        insert_command2 = insert_command2 + f"?,"

    insert_command = insert_command1 + insert_command2 + ")"
    insert_command = insert_command.replace(',)', ')')
    line = tuple(graph.loc[row, :])
    conn.execute(insert_command, line)
    if count%5000==0:
        conn.commit()
        percentage = int(count*100.0/graph.shape[0])
        print(str(percentage) + "%..", end='', flush=True)

conn.commit()
percentage = int(count*100.0/graph.shape[0])
print(str(percentage) + "%..", end='', flush=True)

conn.execute(f"CREATE INDEX idx_GRAPH_curie ON GRAPH(curie)")
conn.commit()
conn.close()
print(f"INFO: Database created successfully", flush=True)

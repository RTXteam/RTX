#!/bin/env python3

import os
import re
import sqlite3

try:
    os.remove('dict.db')
except:
    pass

#create a data structure
conn = sqlite3.connect('dict.db')
conn.text_factory = str
#conn.enable_load_extension(True)
#conn.load_extension("./spellfix")
c = conn.cursor()

#Create question table
c.execute("Create TABLE questions(str TEXT, rank INTEGER)")
c.execute("CREATE UNIQUE INDEX q_idx ON questions(str)")

#### Create a dict to track the state of tables
tables = dict()
c.execute("SELECT name FROM sqlite_master WHERE type='table'");
rows = c.fetchall()
for row in rows:
    tablename = row[0]
    tables[tablename] = "pre-existing"
    print("INFO: Table %s is pre-existing" % tablename)

#insert links into table
def insertNode(curie,name,type):
    if type in tables and tables[type] == "pre-existing":
        print("INFO: Dropping table %s" % type)
        c.execute("DROP TABLE %s(str TEXT)" % (type))
        tables[type] = "dropped"
    if type not in tables or tables[type] == "dropped":
        #rank for Q's so far only, no need here
        #ident needed for nodes so used here
        print("INFO: Creating table %s" % type)
        c.execute("CREATE TABLE %s(str TEXT)" % (type))
        c.execute("CREATE UNIQUE INDEX idx_%s_str ON %s(str)" % (type, type))
        tables[type] = "created"
    c.execute("INSERT OR IGNORE INTO %s(str) VALUES(?)" % (type), (name,))

    #### Also put the complete information into the node table
    tablename = "node"
    rank = 1
    if tablename in tables and tables[tablename] == "pre-existing":
        print("INFO: Dropping table %s" % tablename)
        c.execute("DROP TABLE %s" % tablename)
        tables[tablename] = "dropped"
    if tablename not in tables or tables[tablename] == "dropped":
        print("INFO: Creating table %s" % tablename)
        c.execute("CREATE TABLE %s(curie TEXT, name TEXT, type TEXT, rank INTEGER)" % (tablename))
        c.execute("CREATE INDEX idx_%s_name ON %s(name)" % (tablename, tablename))
        c.execute("CREATE INDEX idx_%s_curie ON %s(curie)" % (tablename, tablename))
        tables[tablename] = "created"
    c.execute("INSERT OR IGNORE INTO %s(curie,name,type,rank) VALUES(?,?,?,?)" % (tablename), (curie,name,type,rank,))


def insertQ(item,rank):
    c.execute("INSERT OR IGNORE INTO questions(str,rank) VALUES(?,?)", (item,rank))
        
with open("../../data/KGmetadata/NodeNamesDescriptions.tsv", 'r', encoding="latin-1", errors="replace") as nodeData:
    print("working on nodes")
    for line in nodeData.readlines():
        curie, name, type = line[:-1].split("\t")
        insertNode(curie,name,type)

with open("../../code/reasoningtool/QuestionAnswering/Questions.tsv") as qData:
    print("working on qs")
    stripVar = re.compile("\$[a-z0-9]*",re.IGNORECASE)
    stripNon = re.compile("[^a-z^0-9 \t,\$]",re.IGNORECASE)
    whiteToNew = re.compile(" *, *")
    lines = qData.readlines()
    for line in lines[1:]:
        line = line.split("\t")[1]
        insertQ(line,1)

filename = "data/mostCommonQueries.dat"
if os.path.isfile(filename):
    with open(filename) as common:
        print("Loading '%s'" % filename)
        lines = common.readlines()
        for line in lines:
            line = line.strip()
            num, line = line.split(" ",1)
            num = int(num)
            insertQ(line,num)
else:
    print("ERROR: Did not find file '%s'. Skipping.." % filename)

#print "creating spelling table"
#c.execute("CREATE VIRTUAL TABLE spell USING spellfix1")
#c.execute("INSERT INTO spell(word) SELECT str FROM dict")
                
conn.commit()
conn.close()

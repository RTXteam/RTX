
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

#insert links into table
def insertN(table,item):
    c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='%s'" % (table));
    if (len(c.fetchall()) == 0):
        #rank for Q's so far only, no need here
        #ident needed for nodes so used here
        c.execute("Create TABLE %s(str TEXT)" % (table))
        c.execute("CREATE UNIQUE INDEX %s_idx ON %s(str)" % (table, table))
    c.execute("INSERT OR IGNORE INTO %s(str) VALUES(?)" % (table), (item,))
        

def insertQ(item,rank):
    c.execute("INSERT OR IGNORE INTO questions(str,rank) VALUES(?,?)", (item,rank))
        
with open("data/NodeNamesDescriptions.tsv", 'r', encoding="latin-1", errors="replace") as nodeData:
    print("working on nodes")
    for line in nodeData.readlines():
        trash, name, table = line[:-1].split("\t")
        insertN(table,name)

with open("data/Questions.tsv") as qData:
    print("working on qs")
    stripVar = re.compile("\$[a-z0-9]*",re.IGNORECASE)
    stripNon = re.compile("[^a-z^0-9 \t,\$]",re.IGNORECASE)
    whiteToNew = re.compile(" *, *")
    lines = qData.readlines()
    for line in lines[1:]:
        line = line.split("\t")[1]
        insertQ(line,1)

with open("data/mostCommonQueries.dat") as common:
    print("working on common")
    lines = common.readlines()
    for line in lines:
        line = line.strip()
        num, line = line.split(" ",1)
        num = int(num)
        insertQ(line,num)

#print "creating spelling table"
#c.execute("CREATE VIRTUAL TABLE spell USING spellfix1")
#c.execute("INSERT INTO spell(word) SELECT str FROM dict")
                
conn.commit()
conn.close()

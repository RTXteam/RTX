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
conn.enable_load_extension(True)
conn.load_extension("./spellfix")
c = conn.cursor()

#Create table
c.execute("Create TABLE dict(str TEXT)")
c.execute("CREATE UNIQUE INDEX dict_idx ON dict(str)")

#insert links into table
def insert(item):
    c.execute("INSERT OR IGNORE INTO dict(str) VALUES(?)", (item,))
    #conn.commit()

with open("../../data/autocomplete/NodeNamesDescriptions.tsv") as nodeData:
    with open("pynode.tmp","wb") as outtmp:
        print "working on nodes"
        for line in nodeData.readlines():
            insert(line.split("\t")[1][:-1])

with open("../../data/autocomplete/Questions.tsv") as qData:
    with open("pyquestions.tmp","wb") as outtmp:
        print "working on qs"
        stripVar = re.compile("\$[a-z0-9]*",re.IGNORECASE)
        stripNon = re.compile("[^a-z^0-9 \t,]",re.IGNORECASE)
        whiteToNew = re.compile(" *, *")
        lines = qData.readlines()
        for line in lines[1:]:
            line = ",".join(line.split("\t")[1:3])
            line = stripVar.sub("",line)
            line = stripNon.sub("",line)
            line = whiteToNew.sub("\n",line)
            line = line.split("\n")
            for item in line:
                #print item
                insert(item)

print "creating spelling table"
c.execute("CREATE VIRTUAL TABLE spell USING spellfix1")
c.execute("INSERT INTO spell(word) SELECT str FROM dict")
                
conn.commit()
conn.close()

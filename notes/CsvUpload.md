# Csv Upload for Nodes and Relationships into Neo4j Docker Instance with apoc

## 1) Tranfer the csv files into the import directory used for docker.

If you have an external neo4j import directory simply place the csv files into that directory.

If, however, your neo4j import folder is contained within your docker container then you can use `sudo docker cp` to tranfer the file into the container.

E.g. for the rtxdev container the neo4j import directory is within the continer with the path: `/var/lib/neo4j/import` Thus, to copy individual the files enter the following into a terminal:

```
sudo docker cp /Path/To/File/name.csv rtxdev:/var/lib/neo4j/import/File.csv
```

If instead, you have a directory only containing the files you want to import then to copy all of thos files in one command you can enter the following:

```
sudo docker cp /Path/To/File/. rtxdev:/var/lib/neo4j/import/
```

## 2) Import the Nodes into Neo4j.

Suppose you have a single csv called nodes.csv for your nodes structured in the following way:

| string | number1 | number2 | uid |
| ------ | ------- | ------- | --- |
| abcdef | 1235813 | 213455  |   1 |
| efghjk | 3581321 | 345589  |   2 |
| jklmno | 1235813 | 345589  |   3 |
| abcdef | 5589144 | 581321  |   4 |
| ...    | ...     | ...     | ... |

We would first need to get into the cypher shell by entering the following command into the terminal:

```
sudo docker exec -ti rtxdev bin/cypher-shell
```

This should then after enjerin the username and password enter the following commands to load the node csv:

```
USING PERIODIC COMMIT 1000
LOAD CSV WITH HEADERS FROM 'file:///nodes.csv' as Line
CREATE (n:Node {string:Line.string, number1:Line.number1, number2:Line.number2, uid:Line.uid});
```

When this command finishes running the nodes should be uploaded into Neo4j. Next, in order to **dramitally** speed up the relationship upload process you can run the following command on a a **unique** property of the nodes.

```
CREATE CONSTRAINT ON (n:Node) ASSERT n.uid IS UNIQUE;
```

**Important:** The property that you use to create the constraint must be unique to each node. This is the property you want to use in your relationship csv to generate the relationships as it will make the process much faster.

## 3) Import the reltionships 

Suppose you have a single csv containing the the relationships structured as follows:

| relation | subjectId | objectId | relProperty |
| -------- | --------- | -------- | ----------- |
| ASDF_GHJ |         3 |       5  |         abc |
| ASDF_GHJ |         1 |       9  |         def |
| QWERTYUI |         3 |       9  |         abc |
| ZXC_VBNM |         4 |       1  |         ghj |
| ...      | ...       | ...      | ...         |

_**IMPORTANT:** The subject/object id in this example should be the node property that is **unique** to the individual nodes for which we ran the canstraint command on in the last example otherwise the upload process will be very slow._

Then to upload the relationships we enter the following commands into the cypher shell:

```
USING PERIODIC COMMIT 1000
LOAD CSV WITH HEADERS FROM 'file:///relationships.csv' as Line
WITH Line
MATCH(node0:Node {id:Line.subjectId})
MATCH(node1:Node {id:Line.objectId})
WITH node0, node1, Line
CALL apoc.create.relationship(node0, Line.relation, {property:Line.relProperty}, node1) YIELD rel
RETURN count(*);
```

This will then upload the relationships and output a count of the relationships uploaded.

## 4) Check to see if the nodes and relationships uploaded correctly

You can check by querying nodes/relationships, quering the counts of nodes/relationships, looking at subgraphs, etc.

If everything checks out you've now successfully updated your nodes and relationships into neo4j. If everything went well it shouldn't take too terably long. When I uploaded csvs with ~500,000 nodes and ~91,000,000 relationships using this method it took just a moment to upload the nodes and ~2h40m to upload the relationships.

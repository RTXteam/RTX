# Reasoning Tool Team to share Cypher queries here

# Q1 Team: 

## APIs that we are using to query Neo4j:

- [neo4jrestclient](https://pypi.python.org/pypi/neo4jrestclient/)

This package uses a REST/HTTPS protocol to communicate with Neo4j

- [neo4j python driver](https://neo4j.com/developer/python/)

This package uses the Bolt protocol to communicate with Neo4j.

- [RNeo4j](https://github.com/nicolewhite/RNeo4j)

The `RNeo4j` package uses a REST/HTTP protocol to communicate with Neo4j.  See 
our [example code](genetic_conditions/get_node_ids_of_genetic_conditions.R).

## Cypher queries that we are using:

- If you want to find the ID of a node of type `disease` for which attribute `attr1` has value `abc` (limiting to one node):

        MATCH (n:disease) WHERE n.attr1=abc RETURN ID(n) LIMIT 1

- If you want to find the shortest-undirected-path (max 3 steps) form node 12345 to node 23456:

        START start_node=NODE(12345), end_node=NODE(23456) MATCH path=shortestPath((start_node)-[r*0..3]-(end_node)) \
        RETURN path

- If you want to find the shortest-undirected-path (max 3 steps) from node 12345 to node 23456 excluding edges of type `isDefinedBy`:

        START start_node=NODE(12345), end_node=NODE(23456) MATCH path=shortestPath((start_node)-[r*0..3]-(end_node)) \
        WHERE NONE (rel in r WHERE type(rel)='isDefinedBy') RETURN path

- If you have two nodes corresponding to the same disease (for example) and you want to know which node has higher "degree" in the network

        MATCH (n:disease)--(other) WHERE ID(n)=486897 OR ID(n)=1633994 RETURN ID(n), count(other);

## Disease ID

| name                           | id      |
|--------------------------------|---------|
| _Alcohol dependence_           | 486897  |
| _alcohol dependence_           | 1633994 |
| Alkaptonuria                   | 6358    |
| Alzheimer Disease              | 1131907 |
| asthma                         | 2592883 |
| cholera                        | 2543486 |
| Diabetes Mellitus, Type 2      | 1122087 |
| Duchenne muscular dystrophy    | 53523   |
| Huntington Disease             | 8138    |
| Hypercholesterolemia           | 1132179 |
| malaria                        | 2542350 |
| myocardial infarction          | 2549074 |
| _Niemann-Pick Disease Type C_  | 7888    |
| _Niemann-Pick disease type C_  | 843637  |
| osteomalacia                   | 2612545 |
| osteoporosis                   | 2185483 |
| post-traumatic stress disorder | 5186887 |
| Sickle Cell Disease            | 7955    |

# Q2 Team: 

## Cypher queries that we are using:

    FILL IN CYPHER QUERIES HERE
    


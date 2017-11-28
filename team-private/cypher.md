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

- From Yao:  code to compute the in- and out-degree of a set of nodes:

        WITH [5570241, 2294705, 57088, 41913, 2294706, 813839] AS id_list
        MATCH (o)-[r]-()
        WHERE id(o) IN id_list
        WITH o, count(r) as degree, id_list
        MATCH (o)<-[r]-()
        WHERE id(o) IN id_list
        WITH o, degree, count(r) AS indegree
        return id(o) AS ID, degree, indegree, degree - indegree AS outdegree

## Disease DOID

|                Disease                 | Disease name in [disease-ontology](http://disease-ontology.org/) | DOID         |
| :------------------------------------: | ---------------------------------------- | ------------ |
|              Osteoporosis              | osteoporosis                             | DOID:11476   |
| Human Immunodeficiency Virus Infection | human immunodeficiency virus infectious disease | DOID:526     |
|                Cholera                 | cholera                                  | DOID:1498    |
|         Ebola Virus Infection          | Ebola hemorrhagic fever                  | DOID:4325    |
|                Malaria                 | malaria                                  | DOID:12365   |
|              Osteomalacia              | Osteomalacia                             | DOID:10573   |
|          Hypercholesterolemia          | familial hypercholesterolemia            | DOID:13810   |
|       Diabetes Mellitus, Type 2        | type 2 diabetes mellitus                 | DOID:9352    |
|                 Asthma                 | asthma                                   | DOID:2841    |
|          Chronic Pancreatitis          | pancreatitis                             | DOID:4989    |
|           Alzheimer Disease            | Alzheimer's Disease                      | DOID:10652   |
|         Myocardial Infarction          | myocardial infarction                    | DOID:5844    |
|      Duchenne Muscular Dystrophy       | Duchenne Muscular Dystrophy              | DOID:11723   |
|      Deficiency of N-glycanase 1       | NGLY1-deficiency                         | DOID:0060728 |
|           Alcohol Dependence           | Alcohol Dependence                       | DOID:0050741 |
|            Major Depression            | major depressive disorder                | DOID:1470    |
|          Niemann Pick Type C           | Niemann Pick Type C                      | DOID:14504   |
|           Huntington Disease           | Huntington's Disease                     | DOID:12858   |
|              Alkaptonuria              | Alkaptonuria                             | DOID:9270    |
|          Sickle Cell Disease           | sickle cell anemia                       | DOID:10923   |
|     Post-Traumatic Stress Disorder     | post-traumatic stress disorder           | DOID:2055    |

## 

## Known Genetic Conditions Giving Protection 

| Genetic Condition                        | Disease                                |
| ---------------------------------------- | -------------------------------------- |
|                                          | Osteoporosis                           |
|                                          | Human Immunodeficiency Virus Infection |
| cystic fibrosis                          | Cholera                                |
|                                          | Ebola Virus Infection                  |
| SCA, glucose-six-phosphate-dehydrogenase Duffy | Malaria                                |
|                                          | Osteomalacia                           |
| PCSK9                                    | Hypercholesterolemia                   |
|                                          | Diabetes Mellitus, Type 2              |
| Familial Mediterranean Fever             | Asthma                                 |
|                                          | Chronic Pancreatitis                   |
|                                          | Alzheimer Disease                      |
|                                          | Myocardial Infarction                  |
|                                          | Duchenne Muscular Dystrophy            |
|                                          | Deficiency of N-glycanase 1            |
|                                          | Alcohol Dependence                     |
|                                          | Major Depression                       |
|                                          | Niemann Pick Type C                    |
|                                          | Huntington Disease                     |
|                                          | Alkaptonuria                           |
|                                          | Sickle Cell Disease                    |
|                                          | Post-Traumatic Stress Disorder         |

## High-level Nodes

```python
ignore_list = [41913, 813839, 57088, 401035, 2294705, 2294706, 5570241]
```

- 41913: `association`, father of all `(:association)` nodes. Exclude this node to exclude all `(:disease)-->(:association)-->41913<--(:association)<--(:disease)` paths.
- 813839: MONARCH top importer, alpha version. This is an ontology that collects a subset of core ontologies required by MONARCH. 
  - 57088 (-[:isDefinedBy]-> 813839): `has phenotype`, a relationship that holds between a biological entity and a phenotype. 1541615 `association` nodes are pointing to this node. Exclude this node to exclude all `(:disease)-->(:association)-->57088<--(:association)<--(:disease)` paths.
  - 401035 (-[:isDefinedBy]-> 813839): `has_part`, a core relation that holds between a whole and its part. 25% of the phenotypes in neo4j are pointing to this node. However this nodes has an out-degree of 22 only, all of which are also highly abstract. Exclude this node to exclude all `(:Phenotype)-->401035<--(:Phenotype)` paths.
  - 2294705 (-[:isDefinedBy]-> 813839): `Autosomal recessive inheritance`. 3048 diseases are pointing to this node while its out-degree is only 3. Exclude this node to exclude all `(:disease)-->2294705<--(:disease)` paths.
  - 2294706 (-[:isDefinedBy]-> 813839): `Autosomal dominant inheritance`. 2802 diseases are pointing to this node while its out-degree is only 3. Exclude this node to exclude all `(:disease)-->2294706<--(:disease)` paths.
- 5570241: iri http://www.orpha.net/ORDO/Orphanet_377788. Looks like a marker of the top term "disease" in ORDO (Orphanet Rare Disease Ontolog). 3698 diseases are pointing to this node while its out-degree is 0. Exclude this node to exclude all `(:disease)-->5570241<--(:disease)` paths


# Q2 Team: 

## Cypher queries that we are using:

    FILL IN CYPHER QUERIES HERE
​    


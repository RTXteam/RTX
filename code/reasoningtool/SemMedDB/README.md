# Conecting to and using the SemMedDB MySQL container on rtxdev

## Starting the necisary containers from a stopped state

First, make sure that rtxdev.saramsey.org is running then ssh into it and run the following commands:

```
sudo docker start semmeddb
sudo docker start umls
sudo docker start semrep
sudo docker exec -d semrep /semrep/public_mm/bin/skrmedpostctl start
sudo docker exec -d semrep /semrep/public_mm/bin/wsdserverctl start
```

Then wait a few seconds for everything to initialize and you should be good to go.

## Using SemMedInterface.py

**NOTE:** Currently all functions return the response as a pandas dataframe with column headers

#### Establishing a Connection

After importing the SemMedInterface class (`from  SemMedInterface import SemMedInterface`) all you need to do to esablish a connection with the SemMedDB, UMLS, and semrep containers on rtxdev.saramsey.org is run the following:

```
smdbi = SemMedInterface()
```

#### Retreaving info on relationships between a subject and object

If you want to get information about the edges between a subject with the cui C1234567 and a object with the cui C7654321 run the following:

```
smdbt.get_edges_between_snodes('C0000001','Name1','C0000002','Name2')
```

This will return a pandas dataframe with the columns: PMID, SUBJECT_NAME, PREDICATE, OBJECT_NAME 

If you want diffent columns in the response add them as a list of strings using the result_col option:

```
smdb.get_edges_between_nodes('C0000001','Name1','C0000002','Name2',result_col = ['the', 'columns', 'you', 'want'])
```
The available columns are:
* PMID
* PREDICATE
* SUBJECT_CUI
* SUBJECT_NAME
* SUBJECT_SEMTYPE
* OBJECT_CUI
* OBJECT_NAME
* OBJECT_SEMTYPE

If you want to specify the predicate connecting the two nodes use the predicate option:

```
smdb.get_edges_between_nodes('C0000001','Name1','C0000002','Name2',predicate = 'ISA')
```

If you don't want to specify if either node is a subject or object you can do so by using the bidirectional option:

```
smdb.get_edges_between_nodes('C0000001','Name1','C0000002','Name2',bidirectional = True)
```

## Getting connections between nodes with multiple hops

If you want to get all of the connections between node with a secific number of pivots use the following:

```
smdb.get_edges_between_subject_object_with_pivot('C0000001','Name1','C0000002','Name2',pivots = 5)
```

If you want the shortest path between a subject and object (under a maximum length) instead use the following:

```
get_short_paths_between_subject_object('C0000001','Name1','C0000002','Name2',max_length = 3)
```

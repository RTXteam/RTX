# Conecting to and using the MySQL containers on rtxdev

## Using QuerySemMedDB.py

**NOTE:** Currently all functions return the response as a pandas dataframe with column headers

#### Establishing a Connection

After importing the class QuerySemMedDB from QuerySemMedDB.py you first must establish the connection to the mysql container on rtxdev. You can do this with the following:

```
smdb = QuerySemMedDB('rtxdev.saramsey.org', '3306', 'rtx_read', 'password', 'semmeddb')
```

#### Retreaving info on relationships between a subject and object

If you want to get information about the edges between a subject with the cui C1234567 and a object with the cui C7654321 run the following:

```
smdb.get_edges_between_subject_object('C1234567','C7654321')
```

This will return a pandas dataframe with the columns: PMID, SUBJECT_NAME, PREDICATE, OBJECT_NAME 

If you want diffent columns in the response add them as a list of strings using the result_col option:

```
smdb.get_edges_between_subject_object('C1234567','C7654321',result_col = ['the', 'columns', 'you', 'want'])
```
The available columns are:
* PREDICATION_ID
* SENTENCE_ID
* PMID
* PREDICATE
* SUBJECT_CUI
* SUBJECT_NAME
* SUBJECT_SEMTYPE
* SUBJECT_NOVELTY
* OBJECT_CUI
* OBJECT_NAME
* OBJECT_SEMTYPE
* OBJECT_NOVELTY 

If you want to specify the predicate connecting the two nodes use the predicate option:

```
smdb.get_edges_between_subject_object('C1234567','C7654321',predicate = 'ISA')
```

If you don't want to specify if either node is a subject or object you can use the function `get_edges_between_nodes` which has all of the same options as `get_edges_between_subject_object`

## Getting connections between nodes with multiple hops

If you want to get all of the connections between node with a secific number of pivots use the following:

```
smdb.get_edges_between_subject_object_with_pivot('C1234567','C7654321',pivots = 5)
```

If you want the shortest path between a subject and object (under a maximum length) instead use the following:

```
get_short_paths_between_subject_object('C1234567',''C7654321',max_length = 5)
```

## Conecting to UMLS

**NOTE:** Currently all functions return the response as a pandas dataframe with column headers

#### Establishing a Connection

After importing the class QueryUMLSSQL from QueryUMLSSQL.py you first must establish the connection to the mysql container on rtxdev. You can do this with the following:

```
umlsdb = QueryUMLSSQL('rtxdev.saramsey.org', '3406', 'rtx_read', 'password', 'umls')
```
#### Converting from GO, HP, and OMIM

To convert from GO, HP or OMIM to cui then you can use the function the following functions:

* GO

```
umlsdb.get_cui_for_go_id('GO:0000252')
```

* HP

```
umlsdb.get_cui_for_hp_id('HP:0000176')
```

* OMIM

```
umlsdb.get_cui_for_omim_id('OMIM:610837')
```

#### Converting to cui fron normalized word

**NOTE:** normalization is defined [here](https://www.ncbi.nlm.nih.gov/books/NBK9684/#ch02.sec2.7.3.2)

to convert from a normalzed word use the following function:

```
umlsdb.get_cui_cloud_for_word('alox15')
```

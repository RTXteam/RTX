# Conecting to and using the MySQL containers on rtxdev

## Setting up your user

In oder to connect the the mysql container you need to first go into the container and add yourself as a user. 
You can get into the container instance by endering the following into the terminal (example for semmeddb):

```
ssh ubuntu@rtxdev.saramsey.org
sudo docker exec -ti summeddb mysql -p
```
(swap semmeddb for umls to do this for the umls container)

This will then prompt you for the root password. After entering this you should see a welcome message and the terminal should now be displaying `mysql>`.
You can now add yourself as an admin by running the following commands:

```
CREATE USER 'user'@'your.ip.address' IDENTIFIED BY 'your_password';

GRANT ALL PRIVILEGES ON *.* TO 'user'@'your.ip.address' WITH GRANT OPTION;

FLUSH PRIVILEGES;
```

Now you should be all set to connect to the mysql server at rtxdev.saramsey.org:3306 (or :3406 for umls).

## Using QuerySemMedDB.py

**NOTE:** Currently all functions return the response as a pandas dataframe with column headers

#### Establishing a Connection

After importing the class QuerySemMedDB from QuerySemMedDB.py you first must establish the connection to the mysql container on rtxdev. You can do this with the following:

```
smdb = QuerySemMedDB('rtxdev.saramsey.org', '3306', 'your_password', 'semmeddb')
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


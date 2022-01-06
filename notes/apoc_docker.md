# How to get apoc running on a docker container with a neo4j image

## 1) Download Apoc

To download apoc simply open the directory you wish to download it to in the terminal then enter the following:

```
wget https://github.com/neo4j-contrib/neo4j-apoc-procedures/releases/download/3.3.0.2/apoc-3.3.0.2-all.jar
```
**IMPORTANT:** This version of apoc (3.3.0.2) is for neo4j version 3.3.x if you are using a different version of neo4j you can find a apoc - neo4j version compatability chart on the [apoc docs website](https://neo4j-contrib.github.io/neo4j-apoc-procedures/#_version_compatibility_matrix) and find the correct download link by going to the [apoc releases webpage,](https://github.com/neo4j-contrib/neo4j-apoc-procedures/releases) finding the correct version, and getting the download link from there.

**IMPORTANT:** After using the apoc .jar file we found that both in apoc vertion 3.3.0.2 and version 3.2.3.6 the .jar file was missing a dependency for the function `apoc.path.subgraphALL`. Thus when calling the function we recieved the following error:

```
Failed to invoke procedure `apoc.path.subgraphAll`: Caused by: java.lang.NoClassDefFoundError: org/apache/commons/collections/IteratorUtils
```

To fix this issue and be able to use this function we need to download the apache commons collections dependency and put it into the apoc .jar file. The apache commons collections 3.2.2 binaries (not 4.X) can be downloaded from the [apache commons website.](https://commons.apache.org/proper/commons-collections/download_collections.cgi "Apache commons collections downloads page") Then, once downloaded extract the contents of the tarball/zip.

Next, extract the .jar file and locate the directory `<path to where you extracted the apoc .jar>/org/apache/commons/` and into that directory copy the following directory and its contents: `<path to where you extracted the apache collections files>/commons-collections-3.2.2/org/apache/commons/collections/`. Aditionally, find the directory: `<path to where you extracted the apoc .jar>/META-INFO/maven/` and into that directory copy the following directory and its contents: `<path to where you extracted the apache collections files>/commons-collections-3.2.2/META-INFO/maven/commons-collections/`. Lastly, repack the apoc .jar file with added dependency.

## 2) Upload to docker

If you do not already have a container with neo4j you can run the following:

```
sudo docker run --name <container name> -p <host port>:7474 -p <host port>:7687 -p <host port>:7473 \
                -e NEO4J_AUTH=neo4j/<password> -v <the directory you wish to store your data into>:/data \
                -v <path to directory containing the apoc .jar file>:/plugins \
                neo4j:3.3.3
```

*Note: If you do not pass the option `-v <path to directory used above>/plugins:/plugins` you will have to copy the plugin file into the container using the `docker cp` command as shown in the following instructions.*

If you already have a docker container running neo4j you will need to copy the .jar file into the directory your docker container looks for neo4j plugins. By default this is in `/var/lib/neo4j/plugins` and this is where it is located in rtxdev.
 
To copy the .jar file into this ditectory siply open the directory containing the .jar file in the terminal and run the following command:

```
sudo docker cp apoc-3.3.0.2-all.jar <container name>:<path to plugins folder within the container>
```
## 3) Edit the neo4j config file

Neo4j will block certain apoc functions unless you give it permission to run. To do this you need to edit the config file.

To get into your docker container just enter the following:
```
sudo docker exec -it <container name> bash
```
once in you then will need to navigate to the config file location. By default this is at `/var/lib/neo4j/conf/neo4j.conf` and in rtxdev it is located at `/etc/neo4j/neo4j.conf`

Then, add the line `dbms.security.procedures.unrestricted=apoc.*` under the Other Neo4j system properties section. Save the file and you will be done.

## 4) Use apoc

Next you can go to either use the neo4j web tool or open the cyper shell with docker. If you want to access the cypher shell enter:
```
docker exec -ti <container name> bin/cypher-shell
```

A list of apoc commands can be found in the [apoc documentation.](https://neo4j-contrib.github.io/neo4j-apoc-procedures/#_overview_of_apoc_procedures_functions)

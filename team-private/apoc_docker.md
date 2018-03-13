# How to get apoc running on a docker container with a neo4j image

*NOTE: The neo4j version used in these istructions is 3.3.3 and the apoc version used is 3.3.0.2 and they assume a linux system*

## Setting up the docker container

#### First, in order to get apoc installed on the neo4j instance we need to make directories for imports, data, and plugins downloading apoc in the process.

Start by opening the directory you wish to store plugin files etc. in the terminal then enter the following:

```
mkdir plugins
pushd plugins
wget https://github.com/neo4j-contrib/neo4j-apoc-procedures/releases/download/3.3.0.2/apoc-3.3.0.2-all.jar
popd

mkdir imports
mkdir data
```

#### Next we build the docker container

run the following:

```
sudo docker run --name <container name> -p <host port>:7474 -p <host port>:7687 -p <host port>:7473 \
                -e NEO4J_AUTH=neo4j/<password> -v <path to directory used above>/data:/data \
                -v <path to directory used above>/plugins:/plugins \ 
                -v <path to directory used above>/imports:/var/lib/neo4j/import \
                neo4j:3.3.3
```

*Note: For installing apoc the important option to pass here is `-v <path to directory used above>/plugins:/plugins` as the part to the left of the colon will tell the docker container where to look for your apoc installation.*

## Accessing the docker container

If you want to get into your newly created docker container just enter the following:
```
sudo docker exec -it <container name> bash
```

If you want to access the cypher shell enter:
```
docker exec -ti <container name> bin/cypher-shell
```

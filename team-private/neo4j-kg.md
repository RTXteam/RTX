# ***NOTE: This document is incomplete***
# Build, test, and deploy the Neo4j KG for RTX

## Starting EC2 instance
To start or stop an EC2 instance do the following:
* Follow this [link](http://ec2startstop.saramsey.org/cgi-bin/manage-instances-cgi.py)
* Enter the username and password when prompted
* Look to see that the ec2 instance is not already in the state you want it to be in. You will want to start/stop the instance named 'ramseyst-rtxsteve-8xlarge'
* Check the bubble next to the instance
* Check start (or stop) instance
* Enter the instance specific passcode
* Click on the submit button

**NOTE:** If you do not have the username or password please email Finn or message him on the isb-ncats slack channel.

## Starting docker containers
After starting up the ec2 instance you will need to start up the docker containers you wish to use. First connect to the ec2 instance by entering the following into the terminal:
```
ssh -A ubuntu@rtxsteve.saramsey.org
```
Once you are connected to the ec2 instance, enter the following commands
* ```sudo docker start rtxsteve``` (This starts up the rtxsteve container)
* ```sudo docker exec -it rtxsteve bash``` (Enter the docker container)
* ```service neo4j start``` (Starts up the neo4j service)

To update the git repo, open a shell in the “rtxdev” container (as described above) and then run the following commands:
```
su - rt
cd /mnt/data/orangeboard/RTX
git pull origin master
```
Change current directory to where the ``run_build_master_kg.sh`` is located and execute it:
```
cd /mnt/data/orangeboard/RTX/code/reasoningtool/kg-construction
./run_build_master_kg.sh
```

## Stopping docker containers
Once the kg-build is successfully complete, you will need to stop the neo4j instance, and the docker container that were in use with the following commands:
```
service neo4j stop
exit
exit
```


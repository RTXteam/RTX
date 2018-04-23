# Deployment of the RTX POC software into a Docker container

In order to run the RTX POC software in a Docker container, it is easiest to use our Docker image 
[tarball (S3 link; 2.5 GB)](https://s3-us-west-2.amazonaws.com/ramseylab/ncats/ncats.saramsey.org/ncats3_version3.tar.gz).
This procedure will require the AWS CLI to be installed into the host OS:
    
    sudo pip3 install awscli

and configured.
    
Next, you'll need to make sure that you have a file system (at least 100 GB) mounted as `/mnt/data`. 
To unpack and run the RTX POC software in Docker:

    cd /mnt/data
    aws s3 cp s3://ramseylab/ncats/ncats.saramsey.org/ncats3_version3.tar.gz .
    docker load < ncats3_version3.tar.gz
    docker run -td -p 80:80 -p 7474:7474 -p 7687:7687 --name PRODUCTION --mount type=bind,source=/mnt/data,target=/mnt/data ncats3:version4
    sudo docker exec -it PRODUCTION bash
    (in the container)# mkdir -p /mnt/data/orangeboard/code
    (in the container)# cd /mnt/data/orangeboard
    (in the container)# wget http://rtxkgdump.saramsey.org/040918-175406.tar.gz
    (in the container)# tar xvzf 040918-175406.tar.gz
    (in the container)# mkdir code
    (in the container)# chown rt.rt code
    (in the container)# service neo4j start
    (in the container)# service apache2 start
    (in the container)# su - rt
    (in the container)$ cd code
    (in the container)$ git clone https://github.com/dkoslicki/NCATS.git
    (in the container)$ cd NCATS/code/reasoningtool
    (in the contianer)$ aws s3 cp s3://ramseylab/ncats/ncats.saramsey.org/orangeboard.sqlite .

The above steps should prepare the RTX POC software to be used with your Docker container.

# Running BuildMasterKG.py from the host OS:

- Update code:

    sudo docker exec -it rtxsteve /usr/bin/sudo -H -u rt bash -c 'cd ~/kg-construction && git pull origin master'
    
- Run in a screen session:

    screen
    
- Within the screen session, run the knowledge graph generator:

    sudo docker exec -it rtxsteve /usr/bin/sudo -H -u rt bash -c 'cd ~/kg-construction && sh run_build_master_kg.sh'

# Starting the RTX docker container

    docker run -td -p 7474:7474 -p 80:80 -p 7687:7687 --name PRODUCTION --mount type=bind,source=/mnt/data,target=/mnt/data ncats:version2

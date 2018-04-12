# Deployment of the RTX POC software into a Docker container

In order to run the RTX POC software in a Docker container, it is easiest to use our Docker image 
[tarball (S3 link; 2.5 GB)](https://s3-us-west-2.amazonaws.com/ramseylab/ncats/ncats.saramsey.org/ncats3_version3.tar.gz).
This procedure will require the AWS CLI to be installed into the host OS:
    
    sudo pip3 install awscli
    
Next, you'll need to make sure that you have a file system (at least 100 GB) mounted as `/mnt/data`. 
To unpack and run the RTX POC software in Docker using the `run_container_ncats.saramsey.org.sh` script.

    cd /mnt/data
    wget https://raw.githubusercontent.com/dkoslicki/NCATS/master/code/docker/run_container_ncats.saramsey.org.sh
    aws s3 cp s3://ramseylab/ncats/ncats.saramsey.org/ncats3_version3.tar.gz .
    docker load < ncats3_version3.tar.gz
    sh run_container_ncats.saramsey.org.sh
    sudo docker exec -it ncats bash
    (in the container)# mkdir -p /mnt/data/orangeboard/code
    (in the container)# cd /mnt/data/orangeboard
    (in the container)# aws s3 cp s3://ramseylab/ncats/ncats.saramsey.org/neo4j_graphdb.tar.gz .
    (in the container)# tar xvzf neo4j_graphdb.tar.gz
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

    sudo docker exec -it rtxsteve /usr/bin/sudo -H -u rt bash -c 'cd ~/kg-construction && git pull origin newkg'
    screen
    sudo docker exec -it rtxsteve /usr/bin/sudo -H -u rt bash -c 'cd ~/kg-construction && sh run_build_master_kg.sh'
    

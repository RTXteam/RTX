

Root Password for mysql server in docker container NCATS2:  on a post-it note in Steve's middle desk drawer.

Neo4j database password:  (same as root mysql password)

Command to create a docker container for Question 1:

    docker run -it --expose 7687 --expose 7473 --name NCATS --network host \
               --mount type=bind,source=/mnt/data,target=/mnt/data ncats:version7 bash

Command to create a docker container for Question 2:
    
    docker run -it --expose 7787 --expose 7573 --expose 3306 --name NCATS2 --network host \
               --mount type=bind,source=/mnt/data,target=/mnt/data ncats2:version2 bash

Docker images are backed up to the [ramseylab S3 bucket](https://s3.console.aws.amazon.com/s3/buckets/ramseylab/ncats/?region=us-west-2&tab=overview)

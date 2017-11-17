## How To Commit A Docker Image

```bash
# SSH into the container, outside any docker
johndoe:~$ ssh admin@lysine.ncats.io

# First check the available space in / (root directory)
# Images are saved incrementally so it won't take a huge chunk of space
admin@star-trek:~$ df -h

# Check committed images
admin@star-trek:~$ sudo docker image ls
REPOSITORY          TAG                 IMAGE ID            CREATED             SIZE
ncats3              version2            YYYYYYYYYYYY        43 hours ago        5.45GB
ncats3              version1            ZZZZZZZZZZZZ        2 days ago          5.45GB

# Commit current image
# Usage: docker commit [ImageName] [Repository:Tag]
admin@star-trek:~$ sudo docker commit NCATS3 ncats3:version3

# Check again
admin@star-trek:~$ sudo docker image ls
REPOSITORY          TAG                 IMAGE ID            CREATED             SIZE
ncats3              version3            XXXXXXXXXXXX        4 seconds ago       5.5GB
ncats3              version2            YYYYYYYYYYYY        43 hours ago        5.45GB
ncats3              version1            ZZZZZZZZZZZZ        2 days ago          5.45GB
```

-----

Root Password for mysql server in docker container NCATS2:  on a post-it note in Steve's middle desk drawer.

Neo4j database password:  (same as root mysql password)

Command to create a docker container for Question 1:

    docker run -it --expose 7687 --expose 7473 --name NCATS --network host \
               --mount type=bind,source=/mnt/data,target=/mnt/data ncats:version7 bash

Command to create a docker container for Question 2:
    
    docker run -it --expose 7787 --expose 7573 --name NCATS2 --network host \
               --mount type=bind,source=/mnt/data,target=/mnt/data ncats2:version2 bash

Docker images are backed up to the [ramseylab S3 bucket](https://s3.console.aws.amazon.com/s3/buckets/ramseylab/ncats/?region=us-west-2&tab=overview)

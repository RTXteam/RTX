# Installing RTX on an empty EC2 instance

NOTE: For the purposes of this guide it is asummed that the ec2 instance is running ubuntu 18.04 and has passwordless sudo setup on a user named ubuntu.

### Installing prerequisite programs

Install the following programs:

1. Docker
2. Git

### Scp the current rtx image and data

Navigate to the directory you wish to download the image to and download the docker image (after insuring your rsa key is added to the list of authorized keys) by running the following:

```
scp ubuntu@arax.rtx.ai:rtx1-20191205-docker-image.tar.gz rtx1-20191205-docker-image.tar.gz
```

### Load the docker image

In the same directory run the following command:

```
sudo docker load < rtx1-20191205-docker-image.tar.gz
```

### Run the docker container

```
sudo docker run --name <container name> -d -t rtx1:20191205
```

**TODO: scp data and add it to the container as a volume**


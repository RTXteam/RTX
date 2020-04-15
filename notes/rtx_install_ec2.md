# Installing RTX on an empty EC2 instance

NOTE: For the purposes of this guide it is asummed that the ec2 instance is running ubuntu 18.04 and has passwordless sudo setup on a user named ubuntu.

### Installing prerequisite programs

Install git:
```
sudo apt update
sudo apt install git
```

clone the RTX repository:
```
git clone https://github.com/RTXteam/RTX.git
```

Install docker:
```
bash RTX/code/kg2/install-docker.sh
```

### Scp the current rtx image and data

Navigate to the directory you wish to download the image to and download the docker image by running the following:

```
curl https://s3-us-west-2.amazonaws.com/arax-public/rtx2-20191205-docker-image.tar.gz > rtx2-20191205-docker-image.tar.gz
```

### Load the docker image

In the same directory run the following command:

```
sudo docker load < rtx1-20191205-docker-image.tar.gz
```

### Copy over data from arax.rtx.ai

Use `rsync` to copy files over from the `data/` directory.


### Setup nginx

Setup nginex with the cofig file located in [RTX/notes/ARAX/rtx-host-os-nginx-config](https://github.com/RTXteam/RTX/blob/master/notes/ARAX/rtx-host-os-nginx-config)

### Setup letsencrypt

Setup letsencrypt with the config file located in [RTX/notes/ARAX/letsencrypt-arax.rtx.ai.conf](https://github.com/RTXteam/RTX/blob/master/notes/ARAX/letsencrypt-arax.rtx.ai.conf)

### Run the docker container

```
sudo docker run -d -it --name <container name> --mount type=bind,source=<path to directory with data files>,target=/mnt/data -p 8080:80 -p 7473:7473 -p 7474:7474 -p 7687:7687 rtx1:20191205
```

**TODO: flesh out letsencrypt and nginx sections**


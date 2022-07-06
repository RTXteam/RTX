# ARAX Response Regestry Setup Process

NOTE: This was tested on ubuntu 20.04

1. Install git and docker
```
apt-get update
apt-get install -y git docker.io
```

2. Clone the RTX repo 
```
git clone https://github.com/RTXteam/RTX.git
```

3. Edit the dockerfile in `RTX/DockerBuild/arax-response-registry/` to add the root password you wish to use

4. Run the image build script
```
cd RTX/DockerBuild/arax-response-registry && bash ./build-image.sh
```

5. Open a bash shell inside the container
```
sudo docker exec -ti arax-responses bash
```

6. Configure `/etc/mysql/mysql.d/mysqld.cnf` to have the bind-address of 0.0.0.0 in order to allow remote connections to mysql.

7. Log into mysql console as mysql user `root`

8. Create user `'rt'@'localhost'` and user `'rt'@'%'`

9. Create databsae `ResponseCache`

10. Assign all rights for `ResponseCache` to both `rt` users
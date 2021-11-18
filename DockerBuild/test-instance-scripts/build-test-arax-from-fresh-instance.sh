#!/usr/bin/env bash

set -o nounset -o pipefail -o errexit

arax_base=/mnt/data/orangeboard

sudo apt-get update
sudo apt-get install -y emacs  # convenience for Steve
sudo apt-get install -y netcat # useful for debugging
sudo apt-get install -y docker.io
export VENV_DIR=/home/ubuntu/venv
source <(curl -s https://raw.githubusercontent.com/RTXteam/RTX-KG2/master/setup-python37-in-ubuntu18.shinc)
git clone https://github.com/RTXteam/RTX.git
cat /dev/zero | ssh-keygen -q -N ""
sudo mkdir -p ${arax_base}/databases
sudo chown ubuntu.ubuntu ${arax_base}/databases
scp araxconfig@araxconfig.rtx.ai:configv2.json ~
cat ~/configv2.json | \
    sed 's|https://arax.ncats.io/beta/api/rtxkg2/v1.2|http://localhost:5008/api/rtxkg2/v1.2|g' > \
	RTX/code/config_local.json

# download the database files (this step takes a long time)
venv/bin/python3 RTX/code/ARAX/ARAXQuery/ARAX_database_manager.py -m


cp RTX/DockerBuild/Merged-Dockerfile .

# --------------------------------------------------------------------------------------------------
# the following are just for convenience in testing and debugging inside the container:
echo <<EOF >> ./Merged-Dockerfile
RUN apt-get install -y netcat 
RUN apt-get install -y emacs
EOF
# --------------------------------------------------------------------------------------------------

sed -i 's/checkout production/checkout master/g' ./Merged-Dockerfile  # for issue 1740; temporary fix during code freeze until commit `ffbd287` can be merged to `production` branch

# build the Docker image
sudo docker build --file ./Merged-Dockerfile --no-cache --rm --tag arax:1.0 ./RTX/DockerBuild/

# create the Docker container
sudo docker create --name arax --tty --publish 80:80 \
    --mount type=bind,source="${arax_base}"/databases,target="${arax_base}"/databases \
    arax:1.0

# start the container
sudo docker start arax

# for config_file in configv2.json config_local.json
# do
#     for devarea in kg2 production
#     do
# 	sudo docker cp ~/${config_file} arax:${arax_base}/${devarea}/RTX/code
# 	sudo docker exec arax chown rt.rt ${arax_base}/${devarea}/RTX/code/${config_file}
#     done
# done

# create the required symbolic links for ARAX/KG2 database files, inside the container
sudo docker exec arax bash -c "su rt; cd /mnt/data/orangeboard/production/RTX; python3 code/ARAX/ARAXQuery/ARAX_database_manager.py"

# start all the services
sudo docker exec arax service apache2 start
sudo docker exec arax service RTX_OpenAPI_kg2 start
sudo docker exec arax service RTX_OpenAPI_production start
sudo docker exec arax service RTX_Complete start

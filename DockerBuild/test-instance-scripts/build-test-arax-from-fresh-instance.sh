#!/usr/bin/env bash

set -o nounset -o pipefail -o errexit

arax_base=/mnt/data/orangeboard

sudo apt-get update

# --------------------------------------------------------------------------------------------------
# the following are optional; they are just for convenience in testing and debugging in the instance:
sudo apt-get install -y emacs  # convenience for Steve
sudo apt-get install -y netcat # useful for debugging
# --------------------------------------------------------------------------------------------------

sudo apt-get install -y docker.io

# install python3.7 (with pip) into the host OS, using the Ubuntu packages
rm -r -f ./venv
export VENV_DIR=./venv   # have to set this environment variable for setup-python37-in-ubuntu18.shinc to work properly
source <(curl -s https://raw.githubusercontent.com/RTXteam/RTX-KG2/master/setup-python37-in-ubuntu18.shinc)

# clone the ARAX software repo from GitHub (master branch)
rm -r -f RTX
git clone https://github.com/RTXteam/RTX.git

# create the directory for the databases, if it doesn't exist already (don't delete it if it already exists!)
sudo mkdir -p ${arax_base}/databases
sudo chown ubuntu.ubuntu ${arax_base}/databases

# copy the config file into the RTX/code directory
scp araxconfig@araxconfig.rtx.ai:configv2.json RTX/code

# create config_local.json that points to the local RTX-KG2 API
cat RTX/code/configv2.json | \
    sed 's|https://arax.ncats.io/beta/api/rtxkg2/v1.2|http://localhost:5008/api/rtxkg2/v1.2|g' > \
	RTX/code/config_local.json

# download the database files (this step takes a long time)
./venv/bin/python3 RTX/code/ARAX/ARAXQuery/ARAX_database_manager.py --mnt --skip-if-exists

# copy the dockerfile to the CWD so we can modify it in-place
cp RTX/DockerBuild/Merged-Dockerfile .

# --------------------------------------------------------------------------------------------------
# the following are optional; they are just for convenience in testing and debugging inside the container:
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

# copy the config files into the devareas in the container

for devarea in kg2 production
do
    for config_file in configv2.json config_local.json
    do
	sudo docker cp RTX/code/${config_file} arax:${arax_base}/${devarea}/RTX/code
	sudo docker exec arax chown rt.rt ${arax_base}/${devarea}/RTX/code/${config_file}
    done
    # create the required symbolic links for ARAX/KG2 database files, inside the container
    sudo docker exec arax bash -c "sudo -u rt bash -c 'cd ${arax_base}/${devarea}/RTX && python3 code/ARAX/ARAXQuery/ARAX_database_manager.py'"
done

# start all the services
sudo docker exec arax service apache2 start
sudo docker exec arax service RTX_OpenAPI_kg2 start
sudo docker exec arax service RTX_OpenAPI_production start
sudo docker exec arax service RTX_Complete start

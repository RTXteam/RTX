#!/usr/bin/env bash

# Stephen Ramsey, Oregon State University

# When you run this shell script, make sure your CWD is in `/home/ubuntu`
# In a bash terminal session, run the script like this
# (in this example, port 8080 is specified on the CLI):
# 
#   cd ~ && source <(curl -s https://raw.githubusercontent.com/RTXteam/RTX/master/DockerBuild/test-instance-scripts/build-test-arax-from-fresh-instance.sh) 8080

set -o nounset -o pipefail -o errexit

arax_base=/mnt/data/orangeboard

port_number=${1:-80}
echo "Port Number: ${port_number}"  # use 8080 if installing on arax2.rtx.ai

sudo apt-get update

# --------------------------------------------------------------------------------------------------
# the following are optional; they are just for convenience in testing and debugging in the instance:
# sudo apt-get install -y emacs  # convenience for Steve
# sudo apt-get install -y netcat # useful for debugging
# --------------------------------------------------------------------------------------------------

sudo apt-get install -y docker.io

# clone the ARAX software repo from GitHub (master branch)
rm -r -f RTX
git clone https://github.com/RTXteam/RTX.git

# create the directory for the databases, if it doesn't exist already (don't delete it if it already exists!)
sudo mkdir -p ${arax_base}/databases
sudo chown ubuntu.ubuntu ${arax_base}/databases

# do a test login to arax.ncats.io, to make sure rsync won't hang up later
ssh -q -oStrictHostKeyChecking=no rtxconfig@arax-databases.rtx.ai exit

# do a test login to araxconfig.rtx.ai, to make sure the scp won't hang up later
ssh -q -oStrictHostKeyChecking=no araxconfig@araxconfig.rtx.ai exit

# copy the config secrets file into the RTX/code directory
scp araxconfig@araxconfig.rtx.ai:config_secrets.json RTX/code

# download the database files (this step takes a long time)
python3 RTX/code/ARAX/ARAXQuery/ARAX_database_manager.py --mnt --skip-if-exists

# copy the dockerfile to the CWD so we can modify it in-place
cp RTX/DockerBuild/Merged-Dockerfile .

# --------------------------------------------------------------------------------------------------
# the following are optional; they are just for convenience in testing and debugging inside the container:
# cat >./Merged-Dockerfile <<EOF 
# RUN apt-get install -y netcat 
# RUN apt-get install -y emacs
# EOF
# --------------------------------------------------------------------------------------------------

# build the Docker image
sudo docker build --file ./Dockerfile --no-cache --rm --tag arax:1.0 ./RTX/DockerBuild/

# create the Docker container
sudo docker create --name arax --tty --publish "${port_number}":80 \
    --mount type=bind,source="${arax_base}"/databases,target="${arax_base}"/databases \
    arax:1.0

# start the container
sudo docker start arax

# copy the config files into the devareas in the container

for devarea in production
do
    sudo docker cp RTX/code/config_secrets.json arax:${arax_base}/${devarea}/RTX/code
    sudo docker exec arax chown rt.rt ${arax_base}/${devarea}/RTX/code/config_secrets.json
    # create the required symbolic links for ARAX/KG2 database files, inside the container
    sudo docker exec arax bash -c "sudo -u rt bash -c 'cd ${arax_base}/${devarea}/RTX && python3 code/ARAX/ARAXQuery/ARAX_database_manager.py'"
done

# start all the services
sudo docker exec arax service apache2 start
sudo docker exec arax service RTX_OpenAPI_production start
sudo docker exec arax service RTX_Complete start  # this is autocomplete; can be commented out for a simple test of ARAX

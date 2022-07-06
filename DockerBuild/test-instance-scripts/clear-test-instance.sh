#!/usr/bin/env bash

# Stephen Ramsey, Oregon State University

set -o nounset -o pipefail -o errexit

read -p "Are you sure you are running this command in the ARAX test instance and not on some other instance? " -n 1 -r
echo    # (optional) move to a new line
if [[ $REPLY =~ ^[Yy]$ ]]
then
    cd ~
    sudo docker exec arax service RTX_OpenAPI_production stop
    sudo docker exec arax service RTX_OpenAPI_kg2 stop
    sudo docker exec arax service apache2 stop
    sudo docker stop arax
    sudo docker rm arax
    sudo docker image rm arax:1.0
    sudo rm -r -f RTX venv Merged-Dockerfile build-test-arax-from-fresh-instance.sh
fi

#!/usr/bin/env bash

set -o nounset -o pipefail -o errexit

sudo docker image build -t arax-responses --rm ./docker
sudo docker create -p 3306:3306 --name arax-responses arax-responses:latest 
sudo docker start arax-responses



#!/usr/bin/env bash

set -o nounset -o pipefail -o errexit

sudo apt-get update
sudo apt-get install -y emacs  # convenience for Steve
sudo apt-get install -y docker.io
export VENV_DIR=/home/ubuntu/venv
source <(curl -s https://raw.githubusercontent.com/RTXteam/RTX-KG2/master/setup-python37-in-ubuntu18.shinc)
git clone https://github.com/RTXteam/RTX.git
sudo mkdir -p /mnt/data/orangeboard/databases
sudo chown ubuntu.ubuntu /mnt/data/orangeboard/databases
venv/bin/python3 RTX/code/ARAX/ARAXQuery/ARAX_database_manager.py -m


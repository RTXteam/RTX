#!/bin/bash
# rename config file
cp /configv2/configv2.json /mnt/data/orangeboard/production/RTX/code/config_local.json
su rt 
cd /mnt/data/orangeboard/production/RTX 
sudo python3 code/ARAX/ARAXQuery/ARAX_database_manager.py
sudo service apache2 start
sudo service RTX_OpenAPI_production start
# this line is added to stop container completes with exit code 0
tail -f /dev/null

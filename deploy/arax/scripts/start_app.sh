#!/bin/bash
# rename config file
cp /configs/configv2.json /mnt/data/orangeboard/production/RTX/code/config_local.json

# Update database directory permission which is mounted from a PVC
chmod -R 777 /mnt/data/orangeboard/databases/
# change owner and groups for database dir
chown -R rt:rt /mnt/data/orangeboard/databases/

# the instructions below are from the deployment wiki at https://github.com/RTXteam/RTX/wiki/ARAX-Docker-Deployment
su rt 
cd /mnt/data/orangeboard/production/RTX 
python3 code/ARAX/ARAXQuery/ARAX_database_manager.py

sudo service apache2 start
sudo service RTX_OpenAPI_production start
sudo service RTX_Complete start
# this line is added to stop container completes with exit code 0
tail -f /var/log/apache2/access.log

#!/bin/bash
# rename config file
cp /configv2/configv2.json /mnt/data/orangeboard/production/RTX/code/config_local.json

# Update database directory permission which is mounted from a PVC
chmod -R 755 /mnt/data/orangeboard/databases/

# Update permission on /mnt/data/orangeboard/production/RTX/code/ARAX/KnowledgeSources/db_versions.json
# since code/ARAX/ARAXQuery/ARAX_database_manager.py will be read and write to it while its permission is 644
chmod 777 /mnt/data/orangeboard/production/RTX/code/ARAX/KnowledgeSources/db_versions.json

# the instructions below are from the deployment wiki at https://github.com/RTXteam/RTX/wiki/ARAX-Docker-Deployment
su rt 
cd /mnt/data/orangeboard/production/RTX 
python3 code/ARAX/ARAXQuery/ARAX_database_manager.py
# change back to root user
exit

service apache2 start
service RTX_OpenAPI_production start
# this line is added to stop container completes with exit code 0
tail -f /dev/null

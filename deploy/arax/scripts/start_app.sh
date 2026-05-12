#!/bin/bash

set -euo pipefail

warn() {
    echo "$*" >&2
}

warn "Running start_app.sh..."
# rename config file
cp /configs/config_secrets.json /mnt/data/orangeboard/production/RTX/code/config_secrets.json

# Update database directory permission which is mounted from a PVC
chmod -R 777 /mnt/data/orangeboard/databases/
# change owner and groups for database dir

chown -R rt:rt /mnt/data/orangeboard/databases/

warn "Running the ARAX_database_manager.py"
# the instructions below are from the deployment wiki at https://github.com/RTXteam/RTX/wiki/ARAX-Docker-Deployment
su - rt -c 'cd /mnt/data/orangeboard/production/RTX && python3 code/ARAX/ARAXQuery/ARAX_database_manager.py'

warn "Starting apache2"
sudo service apache2 start

warn "Starting ARAX"
sudo service RTX_OpenAPI_production start

warn "Starting ARAX-autocomplete"
sudo service RTX_Complete start

# this line is added to stop container completes with exit code 0
tail -f /tmp/RTX_OpenAPI_production.elog


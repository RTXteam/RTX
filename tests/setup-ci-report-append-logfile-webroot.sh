#!/bin/bash

set -o nounset -o pipefail -o errexit

sudo apt-get update
sudo apt-get install -y nginx certbot python3-certbot-nginx
sudo sed -i 's/server_name _;/server_name cicd.rtx.ai;/g' /etc/nginx/sites-enabled/default
sudo servic nginx reload
sudo certbot --no-eff-email --agree-tos --redirect --nginx -m ramseyst@oregonstate.edu -d cicd.rtx.ai

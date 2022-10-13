#!/bin/bash
# ci-report-append-logfile-webroot.sh: run this script as user ubuntu on cicd.rtx.ai to append
# the result of the CICD status check to a logfile under Nginx document root.

set -o nounset -o pipefail -o errexit

sudo bash -c "cd /home/ubuntu/actions-runner && ./svc.sh status | grep runsvc.sh | grep python >> /var/www/html/cicd.txt"

#!/bin/sh

### BEGIN INTRO
#   Function: This script is to dump the Neo4j database and transfer the backup file to http://rtxkgdump.saramsey.org/
#   Instance: 'kgdump' docker container in 'rtxsteve.saramesy.org' instance
#   Where to run the script: any directory
#   Who can run the script: root
#   How to run the script: sh neo4j-backup.sh
#   The backup files will be stored in the /var/www/html folder of the 'rtxkgdump.saramsey.org' instance.
#   The backup files can be accessed in http://rtxkgdump.saramsey.org/
### END INTRO

### BEGIN PREREQUISITE
#   folder and file permissions on 'rtxkgdump.saramsey.org' instance
#   user: ubuntu
#   command:
#   sudo chown -R ubuntu:ubuntu /var/www/html
#   sudo chmod -R 755 /var/www/html
### END PREREQUISITE

# Author: Deqing Qu

set -e

file=`date '+%m%d%y-%H%M%S'`

wall Neo4j will be shut down

echo 'shut down Neo4j ...'
service neo4j stop

echo 'start backup ...'
if [ ! -d "/mnt/data/backup/" ]; then
    mkdir /mnt/data/backup/
fi
neo4j-admin dump --database=graph --to=/mnt/data/backup/$file.cypher

echo 'backup complete ...'
echo 'start Neo4j ...'
service neo4j start

echo 'zip the backup file ...'
cd /mnt/data/backup/
tar -czvf $file.tar.gz $file.cypher

echo 'start transfering the backup file ...'
chown rt:rt $file.tar.gz
su - rt -c "scp /mnt/data/backup/$file.tar.gz ubuntu@52.42.109.175:/var/www/html"

echo 'file transfer complete ...'



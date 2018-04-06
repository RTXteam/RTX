#!/bin/sh

### BEGIN INTRO
#   This script is to dump the Neo4j database and transfer the backup file to http://rtxkgdump.saramsey.org/
#   If you want to run the script, you can log in to the 'rtxsteve.saramesy.org' instance, then log in to the 'kgdump' docker container
#   As the root user of 'kgdump' docker container, you can run the script in any folder using 'sh neo4j-back.sh'
#   The backup files will be stored in the /var/www/html folder of the 'rtxkgdump.saramsey.org' instance.
#   The backup files can be accessed in http://rtxkgdump.saramsey.org/
### END INTRO

# Author: Deqing Qu

set -e

file=`date '+%m%d%y-%H%M%S'`

echo 'shut down Neo4j ...'
service neo4j stop

echo 'start backup ...'
if [ ! -d "/mnt/data/test/" ]; then
    mkdir /mnt/data/test/
fi
neo4j-admin dump --database=graph --to=/mnt/data/test/$file.cypher

echo 'backup complete ...'
echo 'start Neo4j ...'
service neo4j start

echo 'zip the backup file ...'
cd /mnt/data/test/
tar -czvf $file.tar.gz $file.cypher

echo 'start transfering the backup file ...'
su - rt -c "scp /mnt/data/test/$file.tar.gz ubuntu@52.42.109.175:/var/www/html"

echo 'file transfer complete ...'



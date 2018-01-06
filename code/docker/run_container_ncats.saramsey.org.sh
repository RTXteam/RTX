#!/bin/bash
sudo docker run -td --expose 80 --expose 7473 --expose 7687 --expose 7474 --name NCATS \
                    --network host --mount type=bind,source=/mnt/data,target=/mnt/data \
                    ncats3:version4


#!/bin/bash
sudo docker run -td --expose 80 --expose 7473 --expose 7687 --name NCATS3 \
                   --network host --mount type=bind,source=/mnt/data,target=/mnt/data \
                   ncats3:version5

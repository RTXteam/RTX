#!/bin/bash
sudo docker run -it --expose 80 --expose 7473 --expose 7687 --name ncats \
           --network host --mount type=bind,source=/mnt/data,target=/mnt/data \
           ncats3:version2 bash

# Starting ARAX on arax.rtx.ai:

```
docker run -d -it --name rtx1 --mount type=bind,source=/data,target=/mnt/data -p 8080:80 -p 7473:7473 -p 7474:7474 -p 7687:7687 rtx1:20191205
```

# Q1 Container

## 1. Login

```bash
ssh ubuntu@ncats.saramsey.org
sudo docker exec -it NCATS bash
```

Note that `NCATS` is for Q1 while `NCATS2` for Q2.

## 2. Neo4J 

### 2.1 Start/Stop Service

```bash
service neo4j start
service neo4j stop
```

### 2.2 Directories

```txt
root@NCATS:/# neo4j console
Active database: graph
Directories in use:
  home:         /var/lib/neo4j
  config:       /etc/neo4j
  logs:         /var/log/neo4j
  plugins:      /var/lib/neo4j/plugins
  import:       /var/lib/neo4j/import
  data:         /mnt/data/monarch
  certificates: /var/lib/neo4j/certificates
  run:          /var/run/neo4j
```

### 2.3 Memory Config

Neo4j configuration file is `/etc/neo4j/neo4j.conf`. 

#### 2.3.1 Official Document

Memory configurations are done according to [Neo4J Operations Manual: 9.1 Memory Tuning](https://neo4j.com/docs/operations-manual/3.3/performance/#memory-tuning).

Takeaways:

- Actual memory left for the OS = available RAM - (page cache + heap size)
- OS Memory = 1GB + (size of `<data>/databases/<active_database>/index`) + (size of `<data>/databases/<active_database>/schema`)
- page cache = 120% * `<total-database-file-size>`, where `<total-database-file-sizes>` is the sum of 
	1. total size of all `<data>/databases/<active_database>/*store.db*`
	2. total size of all `<data>/databases/<active_database>/schema/index/**/native*/*`
- Generally speaking, it is beneficial to configure a large enough heap space to sustain concurrent operations. For many setups, a heap size between 8G and 16G is large enough to run Neo4j reliably. It is recommended to set these two parameters to the same value to avoid unwanted full garbage collection pauses.
	- The ratio of the size between the old generation and the new generation of the heap is controlled by the JVM flag `-XX:NewRatio=N`. `N` is typically between 2 and 8 by default.

#### 2.3.2 Memory Facts Of This Container

- Total OS memory: 119G. 

```bash
root@NCATS:/# free -g
              total        used        free      shared  buff/cache   available
Mem:            119          55          19           0          45          63
Swap:             0           0           0
```

- `<data>/databases/<active_database>/index` and `<data>/databases/<active_database>/schema` have no significant sizes and should be able to reside in the left OS memory

```bash
root@NCATS:/# cd /mnt/data/monarch/databases/graph
root@NCATS:/mnt/data/monarch/databases/graph# du -hc index | tail -n1
3.6G	total
root@NCATS:/mnt/data/monarch/databases/graph# du -hc schema | tail -n1
836M	total
```

- `<data>/databases/<active_database>/*store.db*` size: 40G

```bash
root@NCATS:/# cd /mnt/data/monarch/databases/graph
root@NCATS:/mnt/data/monarch/databases/graph# du -hc *store.db* | tail -n1
40G	total
```

- `<data>/databases/<active_database>/schema/index/**/native*/*` size: 0
- JVM flag `-XX:NewRatio=2` (default)

```bash
root@NCATS:/# java -XX:+PrintFlagsFinal -version | grep NewRatio
    uintx NewRatio                = 2                {product}
```

#### 2.3.3 Key memory settings in `/etc/neo4j/neo4j.conf`

```ini
# Java Heap Size
dbms.memory.heap.initial_size=16G
dbms.memory.heap.max_size=16G

# The amount of memory to use for mapping the store files
# Some StackOverflow threads suggested 150% ratio for even better performance
dbms.memory.pagecache.size=60g
```
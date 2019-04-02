# Instructions on how to build a new KG from scratch

## Base requirements for using the RTX proof-of-concept reasoning tool software

- Python 3.5 or newer.  Specific packages that are required are listed for each
  command-line script in the RTX POC software, in subsections below. For each
  package requirement, a version number is indicated; that is the version number
  of the package that we have tested with the RTX POC software.
- Neo4j Community Edition, version 3.3.0 (installed locally is recommended for
  best performance).

[NOTE: script-specific requirements are enumerated below]

## Requirements for running `BuildMasterKG.py`

### Python packages required
- `neo4j-driver` (version 1.5.0)
- `requests` (version 2.18.4)
- `requests-cache` (version 0.4.13)
- `pandas` (version 0.21.0)
- `mygene` (version 3.0.0)
- `lxml` (version 4.1.1)
- `CacheControl` (version 0.12.5)

# Building a new KG

## Using `BuildMasterKG.py`

`BuildMasterKG.py` is the script that we use to build a knowledge graph seeded
with the 21 Q1 diseases, a set of 8,000 genetic conditions from OMIM, and the
1,000 pairs of drugs and conditions for Q2.  Each of these entities is expanded
three steps in the knowledge graph, to make a Neo4j database with approximately
1.5M relationships and 46,000 nodes.  To run `BuildMasterKG.py`, first, make
sure Neo4j is running and available on `bolt://localhost:7687`.  Then run:

    python3 BuildMasterKG.py -u xxxx -p xxxx 1>stdout.log 2>stderr.log
    
or equivalently:

    sh run_build_master_kg.sh
    
## Using `UpdateNodesName.py`
`UpdateNodesName.py` is the script that retrieves names from Uniprot and update protein nodes

    python3 UpdateNodesName.py
    
## Using `UpdateIndex.py`
`UpdateIndex.py` is the script that set all needed index

    python3 UpdateIndex.py -u xxxx -p xxxx


# Backing up KG
`neo4j-backup` is the script to dump the Neo4j database and transfer the backup file to http://rtxkgdump.saramsey.org/

    sh neo4j-backup.sh

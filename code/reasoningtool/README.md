# Requirements

## Universal requirements for using the RTX proof-of-concept reasoning tool software

[NOTE: script-specific requirements are enumerated below]

### Base python requirements:
- Python 3.5 or newer 

## Requirements for running `BuildMasterKG.py`

### Python packages required
- `neo4j-driver` (version 1.5.0)
- `requests` (version 2.18.4)
- `requests-cache` (version 0.4.13)
- `pandas` (version 0.21.0)
- `mygene` (version 3.0.0)
- `lxml` (version 4.1.1)

## Using `BuildMasterKG.py`

First, make sure Neo4j is running and available on `bolt://localhost:7687`.  Then run:

    python3 -u BuildMasterKG.py 1>stdout.log 2>stderr.log

or equivalently:

    sh run_build_master_kg.sh
    
## Neo4j:  Community Edition, version 3.3.0 (installed locally)


# What is the Orangeboard?

Orangeboard is a simple implementation of the Blackboard architectural pattern
for modeling a knowledge graph (orange because it is the color for both OSU and
ISB).  You can add nodes and relationships to the Orangeboard, and they get
represented as python `Node` or `Rel` objects.  Nodes can be marked with a
`nodetype` and a `name` (the combination of which is unique).  Every node also
gets a UUID assigned internally by the Blackboard.  Nodes can also have
properties which will get mapped to Neo4j properties when the graph is exported
to Neo4j. You can also add relationships (which I shorten to `rel` in much of
the code) to the graph in the Blackboard.  A relationship has a `reltype` which
is like a category of relationships (think `is_child_of` or `is_member_of`, that
kind of thing).  Each `reltype` is mapped (by a hard-coded `dict` in the
`ReasoningTool.py` script) to a `boolean` value indicating whether or not that
`reltype` is to be directed or not (`True` means directed, `False` means
undirected). Each relationship object also has a `sourcedb` label that is
free-form but I'm using as a controlled vocabulary to describe where I got the
relationship from, e.g., `reactome` or `OMIM` or whatever). Relationships also
get assigned UUIDs internally by the Orangeboard. The first node that you put
into an empty Orangeboard *must* be marked as `seed_node=True`. Subsequently,
every node or relationship that gets added to the Orangeboard as the knowledge
graph is expanded from that seed node will be marked as being associated with
that "seed node", using the seed node's UUID. At any time, you can subsequently
add a second (or third, or ...) node and mark it with `seed_node=True`. This
resets things so that after you add the second "seed node", any new nodes or
relationships that are subsequently added to the knowledge graph are marked as
coming from the *second* seed node. Thus, each node or relationship in the
Orangeboard is marked with a "seed node UUID". This marking is what enables
Orangeboard to have the capability to delete all nodes and relationships that
derive from a single seed node (though of course, Orangeboard also has a method
for completely deleting all nodes and relationships, to restore ).

# Knowledge sources:

Each "knowledge source" is a remote database that we are querying via some kind
of network protocol (HTTP/REST query, etc.). 

## Knowledge sources for which we have query classes that we are currently using in `ReasoningTool.py`:

- `QueryOMIM.py`:  we use this to find the gene or protein that is "hit" by a genetic condition.
- `QueryReactome.py`: we use this to find the pathways with which a protein is
  associated, and the proteins that are members of a pathway (so repeated invocations of this class
  would yield a bipartite graph of proteins and pathways). Also gives us protein-protein interactions.
- `QueryDisGeNet.py`: we use this to map a gene to a disease
- `QueryDisont.py`: we use this to map a disease to "child diseases" that are special cases of the parent disease
- `QueryMyGene.py`: enables us to interconvert between 
- `QueryBioLink.py`:  this gives us disease-phenotype relationships, disease-gene relationships, 
and gene-phenotype relationships.
- `QueryMiRGate.py`: gives us microRNA-to-target-gene relationships
- `QueryMiRBase.py`: used for identifier mapping for microRNAs (gene symbols to mature microRNA IDs, etc.)
- `QueryGeneProf.py`: TF-to-target gene interactions

## Knowledge sources for which query classes have been written but not yet integrated into ReasoningTool.py:

- `QueryPC2.py`: queries Pathway Commons 2.0 (PC2) for protein-pathway
  relationships. Querying PC2 can be very slow, so we are not using it at this time. But this knowledge
  base is potentially useful for literature-curated protein-DNA interactions ("controls-expression-of");
  maybe we could make our own "knowledge source" based on their SIF file?
- `QueryUniprot.py`: can map a Uniprot protein to Reactome pathways; not sure what this buys us because
  we are already doing it with Reactome.
  
## Knowledge sources for which our query classes are not yet implemented or are broken in some way:

- `QueryPazar.py`: not sure we will ever end up remotely querying Pazar; Pazar looks useful but the web API is 
SOAP-based and semi-undocumented. (SAR)

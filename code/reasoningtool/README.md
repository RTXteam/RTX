# Requirements

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

## Requirements for running `Q1Solution.py` or `Q2Solution.py`

### Python packages required
- `networkx` (2.0)
- `numpy` (1.13.3)
- `ipython-cypher` (version 0.2.4)
- `neo4j-driver` (version 1.5.0)
- `requests` (version 2.18.4)
- `requests-cache` (version 0.4.13)

# Using the RTX POC software

## Using `BuildMasterKG.py`

`BuildMasterKG.py` is the script that we use to build a knowledge graph seeded
with the 21 Q1 diseases, a set of 8,000 genetic conditions from OMIM, and the
1,000 pairs of drugs and conditions for Q2.  Each of these entities is expanded
three steps in the knowledge graph, to make a Neo4j database with approximately
1.5M relationships and 46,000 nodes.  To run `BuildMasterKG.py`, first, make
sure Neo4j is running and available on `bolt://localhost:7687`.  Then run:

    python3 -u BuildMasterKG.py 1>stdout.log 2>stderr.log

or equivalently:

    sh run_build_master_kg.sh

## Using `Q1Solution.py`

First, make sure Neo4j is running and available on `bolt://lysine.ncats.io:7687`.  Then, 
to query for a genetic condition that may protect against a disease (for example, `cholera`),

    python3 Q1Solution.py -m 3 -i cholera
    
To query for genetic conditions that protect against each of the 21 Q1 diseases,

    python3 Q1Solution.py -m 3 -a

## Using `Q2Solution.py`

First, make sure Neo4j is running and available on `bolt://lysine.ncats.io:7687`.  Then, 
to query for the clinical outcome pathway between a drug (e.g., `lovastatin`) and 
a condition (e.g., `hypercholesterolemia`),

    python3 Q2Solution.py -r lovastatin -d hypercholesterolemia
    
To find clinical outcome pathways for all 1,000 pairs of drugs and conditions for Q2,

    python3 Q2Solution.py -a

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

- `QueryMyGene.py`: enables us to interconvert between gene IDs and protein IDs
- `QueryChEMBL.py`: we use this to find relationships between drugs and target proteins
- `QueryPharos.py`: we use this to find relationships between drugs and target proteins
- `QueryOMIM.py`:  we use this to find the gene or protein that is "hit" by a genetic condition.
- `QueryReactome.py`: we use this to find the pathways with which a protein is
  associated, and the proteins that are members of a pathway (so repeated invocations of this class
  would yield a bipartite graph of proteins and pathways). Also gives us protein-protein interactions.
- `QueryDisGeNet.py`: we use this to map a gene to a disease
- `QueryDisont.py`: we use this to map a disease to "child diseases" that are special cases of the parent disease
- `QueryBioLink.py`:  this gives us disease-phenotype relationships, disease-gene relationships, 
and gene-phenotype relationships.
- `QueryMiRGate.py`: gives us microRNA-to-target-gene relationships
- `QueryMiRBase.py`: used for identifier mapping for microRNAs (gene symbols to mature microRNA IDs, etc.)
- `QueryGeneProf.py`: TF-to-target gene interactions
- `QueryPhenont.py`: enables us to map between a human phenotype and child phenotypes in the human phenotype ontology
- `QueryPC2.py`: enables us to obtain protein-protein interactions and TF-gene interactions.
- `QueryNCBIeUtils.py`: enables us to do PubMed searches to find semantic
  distance between biomedical terms; also enables us to interconvert between
  MeSH IDs and OMIM identifiers.
- `QuerySciGraph.py`: enables us to interconvert between a MeSH ID and a disease ontology ID.

# Algorithmic approaches for proof of concept questions 1 and 2 

## Q1 approach
To find genetic conditions that protect from a disease, we first find all genetic conditions near the disease 
(i.e. short path distances within a threshold). We then utilize a Markov chain (trained on example condition-disease pairs) to specify path
"templates" between the condition and the disease. A template is a path through the knowledge graph that specifies node 
labels and relationship types, without specifying which nodes and relationships are chosen). These path "templates" are 
then used select from the nearby genetic conditions those that have a high probability of fulfilling the query. Of the 
remaining conditions, we use text mining (PubMed [Google distance](https://en.wikipedia.org/wiki/Normalized_Google_distance) 
between MeSH terms) to select the well studied conditions. These are prioritized based on a confidence score which is a combination of small PubMed 
Google distance and high Markov chain path probability. 

## Q2 approach
To find a clinical outcome pathway for a drug-disease pair, we first find all paths between the source drug and the target 
disease that contain at least one [uniprot](http://www.uniprot.org/) protein, [reactome](https://reactome.org/) pathway, 
and/or [Monarch](https://monarchinitiative.org/)-[BioLink](https://github.com/biolink/biolink-api) [Uberon](https://uberon.github.io/) annotated 
tissue/anatomy node. We then find all proteins that appear in both reactome pathway node and anatomy/tissue node containing paths. 
The anatomy nodes are prioritized using the 
PubMed [Google distance](https://en.wikipedia.org/wiki/Normalized_Google_distance) based on MeSH terms and their knowledge 
graph distance to the aforementioned proteins. Paths are then found that start at the drug, go through the nearby protein(s), nearby 
pathway(s), and the prioritized anatomy node(s). Confidence values calculated as a combination of Google 
distance and path length between nodes. If given training data (known paths connecting drugs and diseases), it would be 
straightforward to solve Q2 by utilizing the same Markov chain approach that we used for Q1. We intend to use this 
Markov chain approach for the production version of the RTX.

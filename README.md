# RTX Reasoning Tool proof-of-concept (POC) software 

The RTX Reasoning Tool POC software is being collaboratively developed by
Team X-ray, a
[team of investigators](#rtx-leadership-team) 
at Oregon State University and the Institute for Systems Biology.

## Organization of this repository

### subdirectory `code`

All software code files for the RTX proof-of-concept (POC) are accessible (and
version-controlled) under this subdirectory. The RTX POC software code is 97%
Python3, with the remainder being bash scripts, Cypher queries, etc.

### subdirectory `code/kg2`

This subdirectory contains all of the code for building the RTX second-generation
knowledge graph, KG2 (see [the README file in the code/kg2 subdirectory](https://github.com/RTXteam/RTX/tree/master/code/kg2/README.md)
for details).

### subdirectory `data`

Text data files for the RTX system that are deployed using git are stored under
this subdirectory. There are only a few such files because the RTX POC software
obtaines most of the information that makes up the biomedical knowledge graph by
RESTfully querying web-based knowledge sources, rather than by loading flat files.

### subdirectory `team-private`

This subdirectory contains notes and other documents for sharing within the RTX team.

### License

The software that we would develop if awarded OT2 research support to build RTX
would be made publicly available, under the MIT open-source software license, in
the [RTX GitHub area](https://github.com/RTXteam/RTX).

### Dependencies outside of GitHub

- The RTX POC software depends on a SQLite cache file, `orangeboard.sqlite`. The
POC software can build this cache file if the cache file is not pre-installed by
the user; however, the POC software will build the knowledge graph much more
rapidly the first time, if our pre-built cache file (63 GB) is used. The
pre-built cache file is stored in Amazon S3
[(link; requires pre-arrangement for access)](https://s3-us-west-2.amazonaws.com/ramseylab/ncats/ncats.saramsey.org/orangeboard.sqlite).

- Neo4j and Python modules: please see [the README file in the code subdirectory](https://github.com/RTXteam/RTX/tree/master/code/README.md)
for more information.


### Issue tracking

Our team makes extensive use of the GitHub Issues system for project
management. Browsing the open and (~100) closed
[RTX issues](https://github.com/RTXTEam/RTX/issues) will provide a sense of
our team's workflow and organizational style, at least for a one-month POC
project.

## RTX team's institutional affiliations

- Oregon State University (Lead Proposing Institution)
- Institute for Systems Biology (Subaward #1)

## RTX leadership team

| Name           | Role                                        | Email                             | GitHub username                               | Areas of relevant expertise      |
| -------------- | ------------------------------------------- | --------------------------------- | --------------------------------------------- | -------------------------------- |
| Stephen Ramsey | Project PI, Oregon State University         | `stephen.ramsey@oregonstate.edu`  | [saramsey](https://github.com/saramsey)       | compbio, systems biology         |
| David Koslicki | Project Co-PI, Oregon State University      | `dkoslicki@math.oregonstate.edu`  | [dkoslicki](https://github.com/dkoslicki)     | compbio, graph algorithms        |
| Eric Deutsch   | PI, subaward, Institute for Systems Biology | `eric.deutsch@systemsbiology.org` | [edeutsch](https://github.com/edeutsch)       | bioinformatics, data management  | 

## RTX other key personnel

| Name             | Affiliation                   | Email                                 | GitHub username                                     | Areas of relevant expertise |
| ---------------- | ----------------------------- | ------------------------------------- | --------------------------------------------------- | --------------------------- |
| Jared Roach      | Institute for Systems Biology | `jared.roach@systemsbiology.org`      |                                                     | genomics, genetics, medicine, systems biology | 
| Andrew Hoffman   | Radboud University, NL        | `A.Hoffman@ftr.ru.nl`                 |                                                     | ethnographer of data science and cyberinfrastructure  |



 


# About ARA Expand, the Translator project, and ARAX

We are **ARA Expand**, a team of researchers and software experts working within
a consortium effort called the **Biomedical Data Translator** program
("Translator program"). Initiated by the NIH National Center for Advancing
Translational Sciences (NCATS), the Translator program's goal is to accelerate
the development of disease therapies by harnessing artificial intelligence,
distributed computing, and computationally-assisted biomedical knowledge
exploration.  Although the Translator program is only in its third year,
Translator tools are already being used by biomedical researchers for hypothesis
generation and by analysts who are supporting clinical management of rare
disease cases. Key intended applications of Translator include repositioning
already-approved drugs for new indications (thus accelerating time-to-market),
identifying molecular targets for developing new therapeutic agents, and
providing software infrastructure that could enable development of more powerful
clinical decision support tools. The 18 teams on the translator project are
working with NCATS to achieve this goal by building the **Translator** software,
a modular system of standards-based Web services for biomedical knowledge
exploration, reasoning, and hypothesis generation. 

After a multi-year feasibility assessment, during which our team built a
prototype Translator reasoning tool called **RTX,** the Translator program is
moving into a prototype development phase during early 2020. In this new phase,
our team is building a modular web-based software system, **ARAX**, that enables
expressive, automatable, and reproducible exploration and analysis of biomedical
knowledge graphs without requiring computer programming expertise. As we develop
ARAX, we will provide up-to-date software code for ARAX and RTX to the
scientific community via this software repository. While ARAX is currently under
development, our team will demonstrate ARAX for NCATS in mid-March 2020; at that
time we will make ARAX publicly available on the Web and we will provide
demonstration web pages and notebooks that illustrate how to access and operate
it.

# ARAX analyzes knowledge graphs to answer biomedical questions

ARAX is a tool for querying, manipulating, filtering, and exploring biomedical
knowledge graphs. It is designed to be a type of middleware&mdash;an *autonomous
relay agent*&mdash;within the Translator system. The top-level layer of
Translator (which is called the *autonomous relay system*) will issue structured
queries to ARAX via ARAX's web application programming interface; based on the
query type, ARAX will determine which *knowledge sources* it needs to consult in
order to be able to answer the query; ARAX will then query the required
knowledge sources, synthesize the information that it gets from those queries,
and respond to the top-level layer in a standardized structured data
format. When completed, ARAX will contribute to and advance the Translator
program in four ways:

1. ARAX provides a powerful **domain-specific language (DSL)**, called
**ARAXi**, that is designed designed to enable researchers and clinicians to
formulate, reuse, comprehend, and share workflows for biomedical knowledge
exploration. One of the key advantages of ARAXi is that it is *not* a
general-purpose programming language; it is purpose-built for the task of
describing&mdash;in user friendly syntax&mdash;a knowledge graph manipulation
workflow in terms of ARAX's modular capabilities. Using ARAXi, an analyst can:
  - define a small *query graph*; query for entities (e.g., proteins, pathways, or
diseases) that match the search criteria represented in the query graph; 
  - *expand* a knowledge graph, pulling in concepts that are related to
  concepts that are already in the knowledge graph
  - filter a knowledge graph, eliminating concepts or relationships that do
  not match a given set of search criteria
  - *overlay* contextual information from large datasets (such as co-occurrence of
terms in clinical health records or in abstracts of articles in the biomedical
literature)
  - *resultify*: enumerate and return matches of a query graph against a larger
  knowledge graph; as a sub-case of this step, ARAX can return as a single
  result, all concepts from the knowledge graph that match a given concept type
  and that match a given pattern of neighbor-concept-type relationships.


2. ARAX is based on a *modular architecture*. It provides distinct, orthogonal,
and human-understandable knowledge graph manipulation and analysis capabilities
via five operations (`query graph`, `expand`, `overlay`, `filter`, and
`resultify`) that can be accessed individually or in combination by the
Translator top-level layer, other Translator tools, or by individual researchers
directly using ARAX. Due to this transparent and modular design, the five ARAX
operations are easy-to-use in isolation and easy to compose into
workflows. Unifying these modules within a single service framework (ARAX) also
provides significant speed benefits for workflows that are implemented
end-to-end within ARAX, because the knowledge graph is stored on the server and
does not need to round-trip to the client with each operation. Through example
ARAX-powered analysis vignettes linked below, we describe how an ARAX workflow
using ARAXi can be much more powerful than the sum of its individual
parts.

3. ARAX natively speaks the information standard&mdash;called the **Reasoners
Standard Application Programming Interface**&mdash;that Translator has adopted for
data interchange between Translator components. Team ARA Expand has been at the
forefront of the development and stewardship of the Reasoners Standard API (as
described [below](#api)), and with this perspective, ARAX was built from the
ground up to seamlessly interoperate with other Translator software components.

4. ARAX is integrated with the _RTX_ reasoning tool's knowledge graphs and graph
visualization capabilities. During the NCATS Translator feasibility asssessment
phase (2017-2019), our team built a prototype reasoning tool system called RTX,
whose knowledge graphs (both the first-generation knowledge graph **RTX-KG1**
and the second-generation knowledge graph **RTX-KG2**) and user interface
capabilities are now available through ARAX. This integration enables a user of
ARAX to seamlessly refer a server-side knowledge graph or result-set for
graphical visualization within a web browser. It also provides ARAX with
significant speed efficiencies for graph expansion and identifier mapping.

# How does ARAX work?

When the ARAX server is queried by the Autonomous Relay System or by another
application, four things happen in sequence:

1. From the query data structure that is provided to ARAX in accordance with the
Reasoners Standard API, ARAX extracts a series of ARAXi commands or a natural-language
question that has been interpreted by ARAX to be of a specific question type.

2. ARAX chooses&mdash;based on the ARAXi commands or the interpreted
question&mdash;which upstream *knowledge providers* to query in order to obtain
the information required to answer the question

3. ARAX integrates and processes the information returned from the knowledge
providers, as required by the initial question

4. ARAX responds to the question with an answer that complies with the Reasoners
   Standard API. ARAX's responses to questions or queries typically contain
   three parts:

   - a recapitulation of the original query (which may involve a restatement of
the question or a structured representation of a small *query graph* of
biomedical concepts)
   - a list of *results*, each of which may be a concept (e.g., "imatinib" or
     "BCR-Abl tyrosine kinase")) or a small graph of concepts and relationships
     between the concepts
   - a *knowledge graph* representing the union of concepts in all of the results,
   along with all known relationships among the concepts in the union.

# Team ARA Expand: who we are

Our team includes investigators from Oregon State University, the Pennsylvania
State University, Institute for Systems Biology, and Radboud University in the
Netherlands. For our work on the Translator program, we also extensively
collaborate and cooperate with investigators at Oregon Health &amp; Science
University, Lawrence Berkeley National Laboratory, University of North Carolina
Chapel Hill, and the University of Alabama Birmingham.

## Principal investigators

| Name           | Role                                        | Email                             | GitHub username                               | Areas of relevant expertise      |
| -------------- | ------------------------------------------- | --------------------------------- | --------------------------------------------- | -------------------------------- |
| Stephen&nbsp;Ramsey | PI, Oregon State University                 | `stephen.ramsey@oregonstate.edu`  | [saramsey](https://github.com/saramsey)       | compbio, systems biology         |
| David&nbsp;Koslicki | PI, Penn State University                   | `dmk333@psu.edu`                  | [dkoslicki](https://github.com/dkoslicki)     | compbio, graph algorithms        |
| Eric&nbsp;Deutsch   | PI, Institute for Systems Biology           | `eric.deutsch@systemsbiology.org` | [edeutsch](https://github.com/edeutsch)       | bioinformatics, data management  | 

## Key personnel

| Name             | Affiliation                   | Email                                 | GitHub username                                     | Areas of relevant expertise |
| ---------------- | ----------------------------- | ------------------------------------- | --------------------------------------------------- | --------------------------- |
| Jared&nbsp;Roach      | Institute for Systems Biology | `jared.roach@systemsbiology.org`      |                                                     | genomics, genetics, medicine, systems biology | 
| Luis&nbsp;Mendoza     | Institute for Systems Biology | `luis.mendoza@systemsbiology.org`     | [isbluis](https://github.com/isbluis)               | software engineering, proteomics, systems biology |
| Andrew&nbsp;Hoffman   | Radboud University, NL        | `A.Hoffman@ftr.ru.nl`                 | [parrhesiastic](https://github.com/parrhesiastic)   | ethnographer of data science and cyberinfrastructure  |

# What is RTX? How does it differ from ARAX?

During the Translator program's feasibility assessment phase (2017-2019), our
team&mdash;under the name "X-ray" that was assigned in accordance with the
feasibility assessment's team-naming scheme based on the electromagnetic
spectrum&mdash;built and released a prototype biomedical reasoning tool called RTX, which is
why this software repository is called `RTX`. Our design for the ARAX software
system builds on the code-base for RTX and leverages the already-built user
interface and knowledge graph for RTX. Think of ARAX as extending RTX's
capabilities by adding powerful new graph exploration capabilities and by adding
a user-friendly language

# Organization of the ARAX/RTX software repository

ARAX and RTX are mostly written in the Python programming language and a small
amount of Javascript and bash shell. YAML and JSON are extensively used for
configuration files. Many examples of analysis workflow code that access RTX
and/or ARAX are provided in Jupyter notebook format, in several places in the 
code-base.

## subdirectory `code`

All software code files for ARAX and RTX are stored under this directory [link](code/README.md).

### subdirectory `code/ARAX`

This subdirectory contains the core software code for ARAX [link](code/ARAX/README.md).

### subdirectory `code/UI/OpenAPI`

This subdirectory contains (1) the YAML code that defines the Reasoners Standard
API and (2) the code for the Reasoners Standard API python object model that is
used to describe a knowledge graph, query nodes, and results
[link](code/UI/OpenAPI/python-flask-server/README.md).

### subdirectory `code/UI/Feedback`

This subdirectory contains the code for the server-side logging system for the
RTX web browser-based user interface [link](code/UI/Feedback/README.md).

### subdirectory `code/UI/interactive`

This subdirectory contains the code for the RTX web browser-based user interface 
[link](code/UI/interactive/README.md).

### subdirectory `code/kg2`

This subdirectory contains the code for building the RTX second-generation
knowledge graph (RTX-KG2) and hosting it in Neo4j [link](code/kg/README.md).

### subdirectory `code/reasoningtool/kg-construction`

This subdirectory contains the code for building the RTX first-generation
knowledge graph (RTX-KG1) [link](code/reasoningtool/kg-construction/README.md).

### subdirectory `code/reasoningtool/SemMedDB`

This subdirectory contains the code for a python interface to an instance of the
Semantic Medline Database (SemMedDB) that is being hosted in a MySQL database
[link](code/reasoningtool/SemMedDB/README.md).

### subdirectory `code/reasoningtool/QuestionAnswering`

This subdirectory contains the code for parsing and answering questions
posed to the RTX reasoning tool [link](code/reasoningtool/QuestionAnswering/README.md).

### subdirectory `code/reasoningtool/MLDrugRepurposing`

This subdirectory contains the code that is used for the machine-learning
model for drug repositioning that was described in the article
*Leveraging distributed biomedical knowledge sources to discover novel uses for known drugs*
by Womack, McClelland, and Koslicki [link](https://doi.org/10.1101/765305).

### subdirectory `code/autocomplete`

This subdirectory contains the code for the concept autocomplete feature in the
RTX web browser-based user interface [link](code/autocomplete/README.md).

## subdirectory `data`

Text data files for the RTX system that are deployed using git are stored under
this subdirectory. There are only a few such files because the RTX POC software
obtaines most of the information that makes up the biomedical knowledge graph by
RESTfully querying web-based knowledge sources, rather than by loading flat files
[link](data/README.md).

## Key repository branches

The most up-to-date branch of the RTX repository (including the latest code for
the ARAX system) is `demo`. The `master` branch contains the most stable recent
release of RTX.

# License

ARAX and RTX are furnished under the MIT open-source software license; see the
`LICENSE.txt` file for details.

# Credits

Many people contributed to the development of ARAX and RTX. A list of code contributors
can be found under [contributors](graphs/contributors), in addition to the team
members listed above. Support for the development of RTX was provided by NCATS
through the Translator program award OT2TR002520.  Support for the development
of ARAX was provided by NCATS through the Translator program award OT2TR003428.

# Installation and dependencies

ARAX is designed to be installed on a `m5a.4xlarge` instance (which has
16&nbsp;vCPUs and 64&nbsp;GiB of RAM) in an Amazon Web Services Elastic Compute
Cloud (EC2) instance with 1,023&nbsp;TiB of elastic block storage, with host OS
Ubuntu&nbsp;18.04. The host OS has nginx v1.14.0 installed and configured (see
`team-private/ARAX/rtx-host-os-nginx-config` for configuration details) for
SSL/TLS temination and proxying of HTTP traffic to `localhost:8080`. The SSL
site certificate was generated using Letsencrypt (certbot version 0.27.0). ARAX
and all of its database dependencies run inside a Docker container (Docker
version 19.03.5) on that instance that is configured to map TCP ports as
follows: 7473:7473, 7474:7474, 7687:7687, and 8080:80 (for details see
`team-private/ARAX/arax-run-container-nodes.md`). Within the Docker container,
ARAX uses Apache&nbsp;v2.4.18, python&nbsp;v3.7.3, Neo4j&nbsp;v3.2.6,
OpenJDK&nbsp;v1.8.0_131, and mysql&nbsp;v5.7.19-0ubuntu0.16.04.1. The python
package requirements for ARAX are described in the top-level `requirements.txt` file.
RTX makes extensive use of internal caching via SQLite&nbsp;v3.11.0.

# Try ARAX/RTX

## Via web browser

Here is the link to access the web browser interface to RTX:  [arax.rtx.ai](https://arax.rtx.ai)

## Via web API

Here is the link to documentation on the web API interface to RTX:  [arax.rtx.ai/api/rtx/v1/ui](https://arax.rtx.ai/api/rtx/v1/ui/)

## Via Jupyter Notebooks

STEVE TO PUT LINKS HERE

# Links

- [Biomedical Data Translator consortium-wide project information (ncats.nih.gov)](https://ncats.nih.gov/translator/about)
- [Biomedical Data Translator 2020 funding opportunity announcement (grants.nih.gov)](https://grants.nih.gov/grants/guide/notice-files/NOT-TR-19-028.html)
- [Biomedical Data Translator open-source software repository (github.com)](https://github.com/NCATS-Tangerine/)

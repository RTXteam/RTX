[![Build Status](https://github.com/RTXteam/rtx/actions/workflows/pytest.yml/badge.svg)](https://github.com/RTXteam/RTX/actions/workflows/pytest.yml)
[![DOI](https://zenodo.org/badge/111240202.svg)](https://zenodo.org/badge/latestdoi/111240202)

# Table of contents

- [About the Translator project, Team Expander Agent, and ARAX](#about-the-translator-project-team-expander-agent-and-arax)
- [ARAX analyzes knowledge graphs to answer biomedical questions](#arax-analyzes-knowledge-graphs-to-answer-biomedical-questions)
- [How does ARAX work?](#how-does-arax-work)
- [The Reasoners Standard Application Programming Interface](#the-reasoners-standard-application-programming-interface)
- [What knowledge providers does ARAX use?](#what-knowledge-providers-does-arax-use)
  - [RTX-KG1](#rtx-kg1)
  - [RTX-KG2](#rtx-kg2)
  - [Columbia Open Health Data (COHD)](#columbia-open-health-data-cohd)
  - [PubMed](#pubmed)
  - [Identifier mapping](#identifier-mapping)
- [Team Expander Agent: who we are](#team-expander-agent-who-we-are)
  - [Principal investigators](#principal-investigators)
  - [Team members](#team-members)
- [What is RTX? How does it differ from ARAX?](#what-is-rtx-how-does-it-differ-from-arax)
- [Organization of the ARAX/RTX software repository](#organization-of-the-araxrtx-software-repository)
  - [subdirectory `code`](#subdirectory-code)
    - [subdirectory `code/ARAX`](#subdirectory-codearax)
    - [subdirectory `code/ARAX/Examples`](#subdirectory-codearaxexamples)
    - [subdirectory `code/UI/OpenAPI`](#subdirectory-codeuiopenapi)
    - [subdirectory `code/UI/Feedback`](#subdirectory-codeuifeedback)
    - [subdirectory `code/UI/interactive`](#subdirectory-codeuiinteractive)
    - [subdirectory `code/kg2`](#subdirectory-codekg2)
    - [subdirectory `code/kg2/mediKanren`](#subdirectory-codekg2medikanren)
    - [subdirectory `code/reasoningtool/kg-construction`](#subdirectory-codereasoningtoolkg-construction)
    - [subdirectory `code/reasoningtool/SemMedDB`](#subdirectory-codereasoningtoolsemmeddb)
    - [subdirectory `code/reasoningtool/QuestionAnswering`](#subdirectory-codereasoningtoolquestionanswering)
    - [subdirectory `code/reasoningtool/MLDrugRepurposing`](#subdirectory-codereasoningtoolmldrugrepurposing)
    - [subdirectory `code/autocomplete`](#subdirectory-codeautocomplete)
  - [subdirectory `data`](#subdirectory-data)
  - [Key repository branches](#key-repository-branches)
- [License](#license)
- [Disclaimer](#disclaimer)
- [Credits](#credits)
- [Installation and dependencies](#installation-and-dependencies)
- [Contact us](#contact-us)
- [Try out ARAX/RTX...](#try-out-araxrtx)
  - [...in your web browser](#in-your-web-browser)
  - [...using our web API](#using-our-web-api)
  - [...by customizing a Jupyter Notebook](#by-customizing-a-jupyter-notebook)
- [Links](#links)
  - [General links for the Biomedical Data Translator project](#general-links-for-the-biomedical-data-translator-project)
  - [ARAX- and RTX-specific links](#arax--and-rtx-specific-links)
  
# About the Translator project, Team Expander Agent, and ARAX

We are **Expander Agent**, a team of researchers and software experts
working within a consortium effort called the **Biomedical Data Translator**
program ("Translator program"). Initiated by the NIH National Center for
Advancing Translational Sciences (NCATS), the Translator program's goal is to
accelerate the development of disease therapies by harnessing artificial
intelligence, Web-based distributed computing, and computationally-assisted
biomedical knowledge exploration. Although the Translator program is only in its
third year, Translator tools are already being used by biomedical researchers
for hypothesis generation and by analysts who are supporting clinical management
of rare disease cases. Key intended applications of Translator include
repositioning already-approved drugs for new indications (thus accelerating
time-to-market), identifying molecular targets for developing new therapeutic
agents, and providing software infrastructure that could enable development of
more powerful clinical decision support tools. The 18 teams on the translator
project are working with NCATS to achieve this goal by building the
**Translator** software, a modular system of Web services for biomedical
knowledge exploration, reasoning, and hypothesis generation.

After a multiyear feasibility assessment (2017-2019), during which our team built a
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
queries to ARAX via ARAX's web application programming interface. Then, based on the
query type, ARAX will determine which *knowledge providers* it needs to consult in
order to be able to answer the query; ARAX will then query the required
knowledge providers, synthesize the information that it gets from those queries,
and respond to the top-level layer in a standardized structured data
format. When completed, ARAX will contribute to and advance the Translator
program in four key ways:

1. ARAX provides a powerful **domain-specific language (DSL)**, called **ARAXi**
(technical documentation on ARAXi can be found
[here](code/ARAX/Documentation/DSL_Documentation.md)), that is designed
to enable researchers and clinicians to formulate, reuse, comprehend, and share
workflows for biomedical knowledge exploration. One of the key advantages of
ARAXi is that it is *not* a general-purpose programming language; it is
purpose-built for the task of describing&mdash;in user friendly syntax&mdash;a
knowledge graph manipulation workflow in terms of ARAX's modular
capabilities. All of ARAX's capabilities are exposed through ARAXi. Using ARAXi,
an analyst can:
  - define a small *query graph*; query for entities (e.g., proteins, pathways, or
diseases) that match the search criteria represented in the query graph 
  - *expand* a knowledge graph, pulling in concepts that are related to
  concepts that are already in the knowledge graph
  - *filter* a knowledge graph, eliminating concepts or relationships that do
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

3. ARAX is a Web service that speaks the information standard&mdash;called the
**Reasoners Standard Application Programming Interface**&mdash;that Translator
has adopted for data interchange between Translator components. Team
Expander Agent has been at the forefront of the development and stewardship
of the Reasoners Standard API (as described
[below](#the-reasoners-standard-application-programming-interface)), and with
this perspective, ARAX was built from the ground up to seamlessly interoperate
with other Translator software components.  In addition to complying with the
Translator standard for inter-reasoner communication, ARAX uses knowledge
sources (see [below](#what-knowledge-providers-does-arax-use)) that comply with
the *Biomedical Data Translator Knowledge Graph Standard* (for which our team
has been an active participant in the standards development process) which is
based on the [Biolink Model](https://biolink.github.io/biolink-model).

4. ARAX is integrated with the _RTX_ reasoning tool's knowledge graphs and graph
visualization capabilities. During the NCATS Translator feasibility assessment
phase, our team built a prototype reasoning tool system called RTX, whose
knowledge graphs (both the first-generation knowledge graph **RTX-KG1** and the
second-generation knowledge graph **RTX-KG2**) and user interface capabilities
are now available through ARAX. This integration enables a user of ARAX to
seamlessly refer a server-side knowledge graph or result-set for RTX-based
graphical visualization within a web browser. It also provides ARAX with
significant speed efficiencies for graph expansion and identifier mapping.

# How does ARAX work?

When the ARAX server is queried by the Autonomous Relay System or by another
application, four things happen in sequence:

1. From the query data structure that is provided to ARAX in accordance with the
Reasoners Standard API, ARAX extracts a series of ARAXi commands, a query graph,
or a natural-language question that has been interpreted by ARAX to be of a
specific question type.

2. ARAX chooses&mdash;based on the ARAXi commands, the query graph, or the
interpreted question&mdash;which upstream *knowledge providers* to query in
order to obtain the information required to answer the question

3. ARAX integrates and processes the information returned from the knowledge
providers, in accordance with the query type.

4. ARAX responds to the question with an answer that complies with the Reasoners
   Standard API. ARAX's responses to questions or queries typically contain
   three parts:

   - a recapitulation of the original query (which may involve a restatement of
the question or a structured representation of a small *query graph* of
biomedical concepts)
   - a list of *results*, each of which may be a concept (e.g., "imatinib" or
     "BCR-Abl tyrosine kinase") or a small graph of concepts and relationships
     between the concepts
   - a *knowledge graph* representing the union of concepts in all of the results,
   along with all known relationships among the concepts in the union.

# The Reasoners Standard Application Programming Interface

During the Feasibility Assessment Phase of the Biomedical Data Translator
program, a data interchange standard (the Reasoners Standard Application
Programming Interface) for communication to/from Translator reasoning tools was
developed and ratified by the Translator stakeholders. The Reasoners Standard
API is formally defined by a Yet Another Markup Language (YAML)
[file](https://github.com/NCATS-Tangerine/NCATS-ReasonerStdAPI/blob/master/API/TranslatorReasonersAPI.yaml)
that is in OpenAPI 3.0.1 format and that is versioned on GitHub. The current
version of the Reasoners Standard API is 0.9.1. The GitHub
[repository](https://github.com/NCATS-Tangerine/NCATS-ReasonerStdAPI) for the
Reasoners Standard API contains an issue list (the primary forum for documented
and archived discussion of issues and proposed changes with the standard),
automated regression tests, some presentation slide decks that provide information
about the standard, and (of course) the YAML file that defines the standard.
Team Expander Agent (and under our previous name during the Feasibility
Assessment phase, Team X-ray) is an active participant in the ongoing
development process for the Reasoners Standard API.

# What knowledge providers does ARAX use?

Currently, ARAX/RTX directly accesses four main knowledge providers in order to
handle queries, along with several additional APIs for identifier mapping.

## RTX-KG1

RTX-KG1 is a knowledge graph comprising 130k nodes and 3.5M relationships that
is built by integrating concepts and concept-predicate-concept triples obtained
from 17 different knowledge providers by way of their web APIs:

1. Pathway Commons 2
2. Disease Ontology
3. Monarch Project Biolink API
4. Drug-Gene Interactions Database
5. KEGG
6. UniProtKB
7. DisGeNet
8. OMIM
9. ChEMBL
10. SIDER
11. Pharos
12. MyChem.info
13. miRGate
14. Gene Ontology
15. Monarch SciGraph API
16. Reactome
17. PubChem

RTX-KG1 complies with the Biolink model-based Translator Knowledge Graph object
model standard. RTX-KG1 is hosted in a Neo4j graph database server and can be
accessed at [kg1endpoint.rtx.ai:7474](http://kg1endpoint.rtx.ai:7474) (username
is `neo4j`; contact Team Expander Agent for the password). Alternatively, a
Neo4j dump file (in gzipped tar archive format) of KG1 can be downloaded without
password from the [kg1endpoint server](http://kg1endpoint.rtx.ai).

## RTX-KG2

RTX-KG2 is a knowledge graph comprising 7.5M nodes and 34.3M relationships
that is built by integrating concepts and concept-predicate-concept triples
obtained from:

1. *All of the KG1 knowledge providers*
2. Unified Medical Language System (UMLS; including SNOMED CT)
3. NCBI Genes
4. Ensembl Genes
5. UniChem
6. Semantic Medline Database (SemMedDB)

RTX-KG2 complies with the Biomedical Data Translator Knowledge Graph object
model standard, which is based on the Biolink model. RTX-KG2 is hosted in a
Neo4j graph database server and can be accessed at
[kg2endpoint2.rtx.ai:7474](http://kg2endpoint2.rtx.ai:7474) (username is
`neo4j`; contact Team Expander Agent for the password). Alternatively, a
JSON dump of KG2 is available from the
[RTX-KG2 S3 bucket](http://rtx-kg2-public.s3-website-us-west-2.amazonaws.com/).
A version of KG2 that is formatted and indexed for the knowledge graph
exploration tool [mediKanren](https://github.com/webyrd/mediKanren) is
available; contact Team Expander Agent for details. For extensive technical
documentation on RTX-KG2, see this repository's [KG2 subdirectory](code/kg2).

## Columbia Open Health Data (COHD)

ARAX accesses the Columbia Open Health Data (COHD) resource (provided by the
Red Team and the Tatonetti Lab from the NCATS Translator Feasibility
Assessment Phase) for overlaying clinical health record co-occurrence
significance information for biomedical concepts in a knowledge graph, 
via the `overlay` feature (for more information, see `code/ARAX`). ARAX
accesses COHD via a web API.

## PubMed

ARAX accesses PubMed for overlaying biomedical literature abstract co-occurrence
significance information for biomedical concepts in a knowledge graph, via the
`overlay` feature (for more information, see `code/ARAX`). For overlaying
literature co-occurrence information, ARAX uses a pre-indexed version of PubMed
(indexed for Medical Subject Heading or MeSH terms). For any concepts that
cannot be mapped to MeSH, ARAX queries PubMed via a web API.

## Identifier mapping

RTX's reasoning code uses several different web services for on-the-fly mapping
between certain identifier types:
1. Ontology Lookup Service 
2. MyChem.info
3. Disease Ontology
4. PubChem
5. NCBI eUtils
6. Human Metabolome Database

A computable file enumerating and summarizing the external APIs that are
used by ARAX/RTX, in YAML format, can be found
[here](code/ARAX/KnowledgeSources/API_LIST.yaml). 

# Team Expander Agent: who we are

Our team includes investigators from Oregon State University, the Pennsylvania
State University, Institute for Systems Biology, and Radboud University in the
Netherlands. 

## Principal investigators

| Name           | Role                                        | Email                             | GitHub username                               | Areas of relevant expertise      |
| -------------- | ------------------------------------------- | --------------------------------- | --------------------------------------------- | -------------------------------- |
| Stephen&nbsp;Ramsey | OSU                 | `stephen.ramsey@oregonstate.edu`  | [saramsey](https://github.com/saramsey)       | compbio, systems biology         |
| David&nbsp;Koslicki | PSU                   | `dmk333@psu.edu`                  | [dkoslicki](https://github.com/dkoslicki)     | compbio, graph algorithms        |
| Eric&nbsp;Deutsch   | ISB           | `eric.deutsch@systemsbiology.org` | [edeutsch](https://github.com/edeutsch)       | bioinformatics, data management, standards development  | 

## Team members

| Name             | Affiliation                   | Email                                 | GitHub username                                     | Areas of relevant expertise |
| ---------------- | ----------------------------- | ------------------------------------- | --------------------------------------------------- | --------------------------- |
| Jared&nbsp;Roach      | ISB | `jared.roach@systemsbiology.org`      |                                                     | genomics, genetics, medicine, systems biology | 
| Luis&nbsp;Mendoza     | ISB | `luis.mendoza@systemsbiology.org`     | [isbluis](https://github.com/isbluis)               | software engineering, proteomics, systems biology |
| Finn&nbsp;Womack           | OSU       | `womackf@oregonstate.edu`        | [finnagin](https://github.com/finnagin)   | drug repositioning, Neo4j  |
| Amy&nbsp;Glen           | OSU       | `glena@oregonstate.edu`        | [amykglen](https://github.com/amykglen)   | knowledge graphs  |
| Arun&nbsp;Muluka          | PSU       | `avm6604@psu.edu`        | [aruntejam1](https://github.com/aruntejam1)   | knowledge graphs  |
| Chunyu&nbsp;Ma        | PSU     | `cqm5886@psu.edu` | [chunyuma](https://github.com/chunyuma) | programmer/analyst | 
| Andrew&nbsp;Hoffman   | RU      | `A.Hoffman@ftr.ru.nl`                 | [parrhesiastic](https://github.com/parrhesiastic)   | ethnographer of data science and cyberinfrastructure  |

For our work on the Translator program, we also extensively
collaborate and cooperate with investigators at Oregon Health &amp; Science
University, Lawrence Berkeley National Laboratory, University of North Carolina
Chapel Hill, and the University of Alabama Birmingham.

# What is RTX? How does it differ from ARAX?

During the Translator program's feasibility assessment phase (2017-2019), our
team&mdash;under the name "X-ray" that was assigned in accordance with the
feasibility assessment's team-naming scheme based on the electromagnetic
spectrum&mdash;built and released a prototype biomedical reasoning tool called
RTX, which is why this software repository is called `RTX`. RTX's capabilities
center around answering questions from a list of natural-language question
templates (e.g., *what proteins does acetaminophen target?* or *what drugs
target proteins associated with the glycolysis pathway?*) and around graphical
construction of a "query graph" that is used as a template for finding subgraphs
of the RTX-KG1 knowledge graph. The design for the ARAX software system
relates to RTX in four ways:
1. ARAX builds on the code-base for RTX and leverages the
already-built user interface and knowledge graphs for RTX (RTX-KG1 and RTX-KG2).
2. Through the expressive (but user-friendly) domain-specific language ARAXi, ARAX exposes RTX's graph
exploration and analysis capabilities so that they can be used (in combination
or individually) by Translator tools or workflows in accordance with the
Translator standard for inter-tool communication (Reasoners Standard API).
3. ARAX adds new and powerful graph exploration and analysis capabilities, such
as `expand`, `overlay` and `filter`, that make ARAX significantly more flexible
(in terms of the types of graph exploration/analysis workflows that it can
implement) than RTX.
4. RTX could produce results in the Reasoners Standard API format. However, its 
more extensive reasoning capabilities could not be queried in this API format without 
specialized knowledge of the RTX system. In contrast, ARAX can now perform its complex 
reasoning capabilities upon receiving any input Reasoners Standard API, while still 
producing such a standardized output format. As such, ARAX and its reasoning capabilities 
will be accessible to any automated reasoning agent, automated reasoning system, or 
knowledge provider capable of sending a Reasoners Standard API message.

# Organization of the ARAX/RTX software repository

ARAX and RTX are mostly written in the Python programming language and a small
amount of JavaScript and bash shell. Yet Another Markup Language (YAML) and
JavaScript Object Notation (JSON) are extensively used for configuration
files. Many examples of analysis workflow code that access RTX and/or ARAX are
provided in Jupyter notebook format, in several places in the code-base.

## subdirectory `code`

All software code files for ARAX and RTX are stored under this directory [link](code).

### subdirectory `code/ARAX`

Contains the core software code for ARAX [link](code/ARAX).

### subdirectory `code/ARAX/Examples`

Contains example Jupyter notebooks for using ARAX from
software [link](code/ARAX/Examples)

### subdirectory `code/UI/OpenAPI`

Contains (1) the YAML code that defines the Reasoners Standard
API and (2) the code for the Reasoners Standard API python object model that is
used to describe a knowledge graph, query nodes, and results
[(link)](code/UI/OpenAPI/python-flask-server).

### subdirectory `code/UI/Feedback`

Contains the code for the server-side logging system for the
RTX web browser-based user interface [(link)](code/UI/Feedback).

### subdirectory `code/UI/interactive`

Contains the code for the RTX web browser-based user interface 
[(link)](code/UI/interactive).

### subdirectory `code/kg2`

Contains the code for building the RTX second-generation
knowledge graph (RTX-KG2) and hosting it in Neo4j [(link)](code/kg2).

### subdirectory `code/kg2/mediKanren`

Contains the code for exporting a version of the RTX-KG2
knowledge graph that is formatted and indexed for use with the [mediKanren](https://github.com/webyrd/mediKanren) knowledge graph exploration tool [(link)](code/kg2/mediKanren).

### subdirectory `code/reasoningtool/kg-construction`

Contains the code for building the RTX first-generation
knowledge graph (RTX-KG1) [(link)](code/reasoningtool/kg-construction).

### subdirectory `code/reasoningtool/SemMedDB`

Contains the code for a python interface to an instance of the
Semantic Medline Database (SemMedDB) that is being hosted in a MySQL database
[(link)](code/reasoningtool/SemMedDB).

### subdirectory `code/reasoningtool/QuestionAnswering`

Contains the code for parsing and answering questions
posed to the RTX reasoning tool [(link)](code/reasoningtool/QuestionAnswering).

### subdirectory `code/reasoningtool/MLDrugRepurposing`

Contains the code that is used for the machine-learning model for drug
repositioning that was described in the article *Leveraging distributed
biomedical knowledge sources to discover novel uses for known drugs*
[article](https://doi.org/10.1101/765305) by Finn Womack, Jason McClelland, and
David Koslicki [(link)](code/reasoningtool/MLDrugRepurposing).

### subdirectory `code/autocomplete`

Contains the code for the concept autocomplete feature in the
RTX web browser-based user interface [(link)](code/autocomplete).

## subdirectory `data`

Text data files for the RTX system that are deployed using git are stored under
this subdirectory. There are only a few such files because the RTX software
obtains most of the information that makes up the RTX-KG1 knowledge graph by
querying external knowledge providers via web APIs, rather than by loading flat
files [(link)](data).

## Key repository branches

The most up-to-date branch of the RTX repository (including the latest code for
the ARAX system) is `demo`. The `master` branch contains the most stable recent
release of RTX.

# License

ARAX and RTX are furnished under the MIT open-source software license; see the
`LICENSE` file for details. For the copyright on the code in the
`code/NLPCode` subdirectory, see the `LICENSE` file in that subdirectory.

# Disclaimer

Per the MIT [license](LICENSE), the ARAX and RTX software are provided
"as-is" without warranty of any kind. The content of this site and the RTX and
ARAX software is solely the responsibility of the authors and does not
necessarily represent the official views of the National Institutes of Health.

# Credits

Many people contributed to the development of ARAX and RTX. A list of code
contributors can be found under the
[contributors tab for this repository](https://github.com/RTXteam/RTX/graphs/contributors), in addition to the
current team members listed above. In addition to the code contributors, we
gratefully acknowledge technical assistance, contributions, and helpful feedback
from NCATS staff (Christine Colvis, Noel Southall, Mark Williams, Trung Nguyen,
Tyler Beck, Sarah Stemann, Debbi Adelakun, Dena Procaccini, and Tyler Peryea),
and Will Byrd, Greg Rosenblatt, Michael Patton, Chunlei Wu, Kevin Xin, Tom
Conlin, Harold Solbrig, Matt Brush, Karamarie Fecho, Julie McMurray, Kent
Shefchek, Chris Bizon, Steve Cox, Deepak Unni, Tim Putman, Patrick Wang, Sui
Huang, Theo Knijnenburg, Gustavo Glusman, John Earls, Andrew Su, Chris Mungall,
Marcin Joachimiak, Michel Dumontier, Richard Bruskiewich, and Melissa
Haendel. Support for the development of RTX was provided by NCATS through the
Translator program award OT2TR002520.  Support for the development of ARAX was
provided by NCATS through the Translator program award OT2TR003428.

# Installation and dependencies

ARAX is designed to be installed on an Amazon Web Services Elastic Compute Cloud
(EC2) instance with the following minimum requirements (we use a `m5a.4xlarge` instance):

- 16 vCPUs
- 64 GiB of RAM
- 1,023 GiB of elastic block storage
- host OS Ubuntu v18.04. 

The host OS has nginx v1.14.0 installed and configured
(see `notes/ARAX/rtx-host-os-nginx-config` for configuration details) for
SSL/TLS termination and proxying of HTTP traffic to `localhost:8080`. The SSL
site certificate was generated using Letsencrypt (certbot v0.27.0). ARAX
and all of its database dependencies run inside a Docker container
(Docker v19.03.5) that is configured to map TCP ports as
follows (host-port:container-port):

- 7473:7473
- 7474:7474
- 7687:7687
- 8080:80 

(for the specific Docker run command, see
`notes/ARAX/arax-run-container-nodes.md`). Within the Docker container,
ARAX uses

- Ubuntu v16.04
- Apache v2.4.18 
- python v3.7.3
- Neo4j v3.2.6 (see [`code/reasoningtool/kg-construction`](code/reasoningtool/kg-construction) on how to set up Neo4j for running ARAX/RTX)
- OpenJDK v1.8.0_131
- mysql v5.7.19-0ubuntu0.16.04.1

The python package requirements for ARAX are described in the top-level
`requirements.txt` file.  RTX makes extensive use of internal caching via
SQLite v3.11.0.

# Contact us

The best way to contact Team Expander Agent is by 

- sending an email message to
**[`expander.agent@gmail.com`](mailto:expander.agent@gmail.com)**
- logging an [issue](../../issues/) in this GitHub repository
- (for members of the Biomedical Data Translator consortium) messaging us on the
[NCATS Translator Slack](https://ncatstranslator.slack.com). 

See also the contact information for the Team Expander Agent PIs above.

# Try out ARAX/RTX...

## ...in your web browser

Here is the link to access the web browser interface to RTX:
[arax.rtx.ai](https://arax.rtx.ai)

## ...using our web API

Here is the link to documentation on the web API interface to RTX:
[arax.rtx.ai/api/rtx/v1/ui](https://arax.rtx.ai/api/rtx/v1/ui/).

## ...by customizing a Jupyter Notebook

Three Jupyter notebooks that demonstrate how to programmatically use ARAX are provided
[here](code/ARAX/Examples).

# Links

## General links for the Biomedical Data Translator project

- [Biomedical Data Translator consortium-wide project information (ncats.nih.gov)](https://ncats.nih.gov/translator/about)
- [Biomedical Data Translator 2020 funding opportunity announcement (grants.nih.gov)](https://grants.nih.gov/grants/guide/notice-files/NOT-TR-19-028.html)
- [Biomedical Data Translator Feasibility Assessment Phase open-source software repository (github.com)](https://github.com/NCATS-Tangerine/)
- [Biomedical Data Translator open-source software repository (github.com)](https://github.com/NCATSTranslator)
- [Biomedical Data Translator Knowledge Graph object model standard (github.io)](https://biolink.github.io/biolink-model)
- [Biomedical Data Translator Reasoners Standard API (github.com)](https://github.com/NCATS-Tangerine/NCATS-ReasonerStdAPI)

## ARAX- and RTX-specific links

- [ARAX browser-based interface (arax.rtx.ai)](https://arax.rtx.ai)
- [Technical documentation on ARAXi, the ARAX domain-specific language (this repo)](code/ARAX/Documentation/DSL_Documentation.md)
- [Technical documentation on the ARAX web API interface (arax.rtx.ai)](https://arax.rtx.ai/api/rtx/v1/ui/)
- [Example notebooks on how to programmatically use ARAX (this repo)](code/ARAX/Examples)


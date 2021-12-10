# Workflow B: DILI Drug Repurposing

DILI (drug-induced liver injury) is the outcome of a drug exposure in rare patients with heightened sensitivity to drug-related hepatic sequela. Drugs account for 20-40% of all instances of fulminant hepatic failure, and drug-induced hepatic injury is the most common cited reason for withdrawal of an approved drug from the market.

DILI has only one consensus treatment: discontinuation of the causal agent. While DILI may resolve after the causal agent is discontinued, complete resolution may require months or years and, in many cases, the condition deterioriates before resolving and/or becomes chronic. Moreover, DILI is associated with high healthcare costs and high morbidity and mortality, often leading to hospitalization, liver transplant, and other poor outcomes.

The intent of Workflow B is two-fold: 

1. Suggest drugs for repurposing, along with evidence of biological plausibility to justify the suggestion. The goal here is to suggest candidates for clinical trials. Indeed, this is of great interest to the international DILI Network Steering Committee, which is arguably the leading authority on DILI and the only body with a continuous 20-year registry of patients with DILI.

* In natural language, one might ask *are there drugs that can be repurposed to treat DILI-associated phenotypes or outcomes, or allow a patient to continue on a drug that is otherwise effective?*

2. Suggest chemicals for liver-on-a-chip screening (or other *in vitro* screening assays), along with evidence of biological plausibility, again, to justify the suggestion. The goals here is to suggest candidates for laboratory testing at NCATS, NIEHS, or elsewhere.

* In natural language, one might ask *are there chemical substances that may serve as drug targets for development of new treatments for DILI-associated phenotypes or outcomes, or allow a patient to continue on a drug that is otherwise effective?*

The workflow is structured as an initial three-hop TRAPI query that runs from input DiseaseOrPhenotypicFeature CURIE (e.g., DILI, chronic DILI [see suggestions below] to DiseaseOrPhenotypicFeature to Gene to ChemicalSubstance (including approved drugs). A fourth hop then seeks clinical real-world evidence on whether any of the suggested approved drugs are used to treat (biolink:correlated_with, biolink:related_to, biolink:has_real_world_evidence_of_association_with) the diseases or phenotypic features identified from the first hop, or whether they are used to treat (biolink:correlated_with, biolink:realted_to, biolink:has_real_world_evidence_of_association_with) other potentially related traits/diseases, or whether they are associated with adverse events. 

For the purpose of the December demo, the current plan is to precompute the first three-hop TRAPI query, review the answers with Paul Watkins (SME and member of the DILI Network Steering Committee). In addition to (hopefully) identifying drugs repurposing and chemicals for testing, the workflow and demo are intended to: (1) provide real-world evidence that might assist with ranking/sorting of answers and/or SME evaluation of results from the third hop and (2) highlight or showcase Translator KPs, all of which provide open to access to clinical data and/or computational models applied to those data. 

Suggested input CURIES for three-hop TRAPI queries from DiseaseOrPhenotypicFeature:

* DILI - MONDO:0005359
* Toxic liver disease with acute hepatitis - SNOMEDCT:197358007
* Chronic DILI - MESH:D056487
* Hospitalization - MESH:D006760
* Transplanted liver complication - NCIT:C26991

[Node Normalizer equivalent identifiers](https://drive.google.com/file/d/1rtvBM7J3AQpYFbLZquG3UUC1Ck5h_lA1/view?usp=sharing)

**Important:** While this workflow narrative focuses on DILI, the workflow itself is intended to be disease-agnostic. The focus on DILI is only to highlight Translator capabilities in the context of a compelling use case and engaged user community.

*For reference, here is the [workflow mural board](https://app.mural.co/t/ncats3030/m/ncats3030/1620608471364/d9d6ca5aefb8c7af4f756312d2500f0a3f465008), [pre-relay meeting materials](https://drive.google.com/drive/folders/1sCA6iouNHOh9I4ivXrR6DCct6fGgXbXp?usp=sharing), and [Spring 2021 relay meeting materials](https://github.com/ranking-agent/robogallery/tree/master/relay_spring_2021/DILI). Also see mini-hackathon issues #43, #44, #45, #46, #48, and #49.*

*Note that Workflow B was tested using [multihop.py](https://github.com/NCATS-Tangerine/icees-api-config/tree/master/cli), which is a script that Hao Xu wrote to chain together KPs and ARAs, such that KP1's output becomes KP2's input, and so on. We used this tool to troubleshoot the workflow, in terms of ARA and KP debugging, and initiate evaluation of answers for scientific impact, given timeout issues related to the ARS. Testing results can be found [here](https://drive.google.com/drive/folders/1sCA6iouNHOh9I4ivXrR6DCct6fGgXbXp?usp=sharing). Note that the testing was extremely useful and surfaced multiple issues, since resolved. We are now testing the workflow via direct ARA query. We are also exploring the use of alternative node categories to replace biolink:Gene, for instance, biolink:BiologicalProcessOrActivity. The intent here is to determine whether the use of less common categories addresses the timeout issue.*

*A successful ARS three-hop query using MESH:D056487 can be accessed using PK = f02e762d-de0d-4069-935c-a6ed821998ac.*

### Related Workflow

Related to the above workflow, this workflow aims to explore biological mechanisms that might explain for the few genes (see list below) that are known or suspected to play a causal role in DILI. In natural language, one might ask *what biological mechanisms might explain the causal relationship between GeneX and DILI?* In this sense, the alternative workflow might be considered an "explain" workflow.

Suggested input CURIES for one-hop TRAPI query from Gene, structured as biolink:Gene -> biolink:interacts_with -> biolink:BiologicalProcessOrActivity:

* class I HLA-A - NCBIGene:3105
* class I HLA-B - NCBIGene:3106
* ERAP2 - NCBIGene:64167
* EXOC4 - NCBIGene:60412
* PTPN22 - NCBIGene:26191

*Note that the alternative workflow (or a variation of it) was suggested during the May 2021 relay meeting, perhaps as an entry path into the main workflow. As it addresses a different question than the main workflow, I'm not entirely sure how to weave it into the narrative for the December demo, but I think this issue will resolve naturally when we dive a bit deeper into answers.*

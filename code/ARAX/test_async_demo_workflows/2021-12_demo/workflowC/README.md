# Clinical real-world evidence: current drugs and potential new insights

_Immune-mediated inflammatory diseases (IMIDs)_

[Slides in google drive](https://drive.google.com/drive/folders/1gQC9RhE6jxPWRHm7fMf4MPW3ewq-LH0i)

## Queries

1. **Drugs** used for patients with **diseases XYZ** in the real world.
2. Investigate expert-recommended **candidate drugs for repurposing** for **disease Q** and look for connections with **gene pathway P**
3. Search broadly for **drugs** used in the real world for patients with **diseases QRS** that are **connected to gene pathway P**

## SME User Scenario 1

**Philip Mease, MD** is a rheumatologist who is working on immune-mediated inflammatory diseases (IMIDs) with an interdisciplinary team including gastroenterologists and data scientists. Team members want to learn more about the many-to-many maps between thousands of IMIDs and immunomodulatory drugs. **Systemic sclerosis** (sometimes called **scleroderma** ) is a spectrum of rare diseases related to excess collagen, which can lead to fibrosis of the skin, internal organs, or both.

### Query C1: Team looking at drugs used for patients with IMIDs

[ARS](https://arax.ncats.io/?r=d206d96a-635d-4749-a0af-384d9b9b6eb8), [ARAX](https://arax.ncats.io/?r=33608), [JSON](https://github.com/NCATSTranslator/minihackathons/blob/main/2021-12_demo/workflowC/C1.json)

Literature shows a vast number of medications that have been considered to treat IMIDs. However, the team wants to see real world use of drugs for IMIDs: approved and off-label. Structured EHR data does not track _why_ a drug is prescribed because it's usually obvious to other clinicians, and unusual treatments are explained only in free text notes. If you looked only co-occurance rates of drugs in patients with scleroderma, you&#39;ll see a vast list, with things like acetaminophen (Tylenol) because it&#39;s commonly used by patients in general. Translator has EHR-derived knowledge about which drugs that are **likely to be related** to a specific disease. These might be disease modifying drugs, or medications that treats symptoms or secondary conditions related to the disease.

Choose Aragorn, ARAX: The team is familiar with thousands of drugs and can quickly scan through them. **Note**: methotrexate, dexamethasone and sulfasalazine are common immunomodulatory drugs used to treat many IMIDs.

**Tofacitinib** is a JAK inhibitor, which they know used for some of their patients IMIDs.
Click on the **psoriasis** COHD edge. This shows knowledge derived from EHR data, including Chi squared and observed to expected ratio.

They are interested to see it's also being used in patients with **systemic sclerosis**. Click on **Biothings Multiomics**. This shows knowledge derived using machine learning models. This drug suggests a slightly increased likelihood that the patient also has systemic sclerosis. This shows the **size of the population,** reported in **log** to avoid differential privacy attacks: order of magnitude is log 7 **10,000,000** patients, log 3, **1,000** with systemic sclerosis.

## SME User Scenario 2

**Dr. Sergio Baranzini, PhD** is a biomedical expert in Multiple Sclerosis. There have been great advances in treating multiple sclerosis exacerbations, but not in stopping the underlying progressive demyelination on nerves. Dr. Baranzini is interested in drugs that interact with the central nervous systems (CNS) myelination gene pathways. A recent [paper](https://pubmed.ncbi.nlm.nih.gov/31100209) included a list of eight candidates for drug repurposing for progressive multiple sclerosis. He would like to see whether/how these drugs connect with CNS myelination pathways.

### Query C2: Investigating whether drug repurposing candidates connect to CNS myelination

[ARS with BTE ](https://arax.ncats.io/?r=5a1e4475-e01c-4f5d-b86a-efda20dddbe9), [older ARS with Aragon ](https://arax.ncats.io/index.html?r=aa62c8b3-d934-4b2f-ac11-2ce0c2c719a1), [ARAX](https://arax.ncats.io/index.html?r=32963), [JSON](https://github.com/NCATSTranslator/minihackathons/blob/main/2021-12_demo/workflowC/C2.json)

Aragorn or ARAX. Choose **clemastine**. Click on edge to STAT3. This is now in clinical trials for remyelination.

Choose **nimodipine**. Click on the edges to multiple sclerosis. SME thinks the mechanism of action makes sense. See nimodipine note on **PMID:28381594**. Nimodipine fosters remyelination in a mouse model.

### Query C3: Investigation of potential candidates connected to CNS myelination

[latest ARS](https://arax.ncats.io/?r=f070eda1-5095-4587-b021-3a5831d6b5ea), [ARAX](https://arax.ncats.io/?r=32966), [JSON](https://github.com/NCATSTranslator/minihackathons/blob/main/2021-12_demo/workflowC/C3.json)

Translator independently finds both existing drugs and several that experts suggested, including: metformin and tamoxifen.

The SME is intrigued by **quercetin** (which is plant-based), and **dasatinib** (a tyrosine kinase inhibitor), and will be investigating further.

Optional: Sometimes, nifedipine or another calcium channel blockers are in the results from some ARAs. There is new evidence for nimodipine in mouse models: [PMID 33709265](https://pubmed.ncbi.nlm.nih.gov/33709265).

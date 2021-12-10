# Purpose
The EGFR (epidermal growth factor receptor) gene has an overactive variant that results in Acanthosis nigricans, an overgrowth of skin in some areas of the body that can be uncomfortable and disfiguring, but not life threatening. The purpose of this workflow is to help a clinician find an existing drug already FDA approved that can decrease the activity of the EGFR gene and provide relief to the patient. This [query](https://docs.google.com/presentation/d/1393qJ_Pcsl-hkwrsScqNLycEOuk-7dDkp5ey4UuEBbA/edit#slide=id.gd73e060e6f_0_2512) came to us by way of UAB's Precision Medicine Institute.

# Query Notes
```
{"message":
    {"query_graph":
        {
          "nodes": {
            "n0": {
            #This is where we specify that we want our answer to be a chemical substance, e.g., a drug
              "categories": [
                "biolink:ChemicalSubstance"
              ],
              "name": "Chemical Substance",
              #This section imposes the constraint that we want to find ONLY substances that have already been FDA approved
              "constraints": [
                {
                    "id":"biolink:highest_FDA_approval_status",
                    "name":"highest FDA approval status",
                    "operator":"==",
                    "value":"regular approval"
                }
              ]
            },
            "n1": {
            #This is where we specify the gene of interest. We know that EGFR is causal for our disease of interest.
              "name": "EGFR",
              "ids": ["NCBIGene:1956"]
            }
          },
          "edges": {
            "e0": {
              "subject": "n0",
              "object": "n1",
              #We want to know what decreases the activity of EGFR. This relationship is expressed in many different ways across different data sources. Here we 
              #gather together the relevant relationships and search across all of them.
              "predicates": [
                "biolink:decreases_abundance_of",
                "biolink:decreases_activity_of",
                "biolink:decreases_expression_of",
                "biolink:decreases_synthesis_of",
                "biolink:increases_degradation_of",
                "biolink:disrupts",
                "biolink:entity_negatively_regulates_entity"
              ]
            }
          }
        }
    }
}
```

### NCATS Kownledge Graph

| Node type           | Number of nodes |
| :------------------ | --------------- |
| "omim_disease"      | 8480            |
| "uniprot_protein"   | 17747           |
| "phenont_phenotype" | 9770            |
| "disont_disease"    | 3291            |
| "reactome_pathway"  | 639             |
| "anatont_anatomy"   | 673             |
| "ncbigene_microrna" | 1637            |
| "pharos_drug"       | 1000            |



| Relationship type        | Number of relationships |
| ------------------------ | ----------------------- |
| "is_parent_of"           | 9454                    |
| "controls_expression_of" | 519404                  |
| "gene_assoc_with"        | 19033                   |
| "interacts_with"         | 581274                  |
| "is_expressed_in"        | 35984                   |
| "phenotype_assoc_with"   | 257181                  |
| "targets"                | 3398                    |
| "disease_affects"        | 5066                    |
| "is_member_of"           | 162487                  |
| "gene_assoc_with"        | 19033                   |

# Node properties

- name: the human-readable name for the node (e.g. G protein-coupled receptor, rhodopsin-like)
- id: the CURIE ID for the node (e.g., UniProt:Q9NS67)
- uri: a URI for the node (e.g., http://www.uniprot.org/uniprot/Q9NS67)
- category: the biolink semantic type of the node
- rtx_name: DEPRECATED; currently used internally by BioNetExpander.py in the RTX system
- extended_info_json: the full node properties JSON blob (per David K.'s request, issue #49)


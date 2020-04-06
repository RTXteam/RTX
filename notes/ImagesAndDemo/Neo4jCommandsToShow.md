# Statistics of the graph
## Number and kind of nodes:
MATCH (n) RETURN distinct labels(n)[1], count(*)

## Total number of nodes
match (n) return count(n)

## Number and kind of relationships:
MATCH path=()-[r]-() RETURN distinct extract (rel in relationships(path) | type(rel) )[0] as types, count(*)

## Total number of relationships
match ()-[r]-() return count(r)


# Question and associated cypher query:

## What drugs does acetaminophen target?
match p=(s:pharos_drug{name:"acetaminophen"})-[:targets]-(t:uniprot_protein) return p limit 15

## what genetic conditions might offer protection against malaria?
match (n) where n.name in ["P00738","OMIM:603903"] or n.description in ["malaria"] return n

### The full explanitory pathway [from Cell paper](http://dx.doi.org/10.1016/j.cell.2011.03.049)
match p=(:omim_disease{name:"OMIM:603903"})--(:uniprot_protein{description:"HBB"})--(:reactome_pathway)--(:uniprot_protein {description:"NFE2"})--(:uniprot_protein {description:"HMOX1"})--(:disont_disease {name:"DOID:14069"})--(:disont_disease {name:"DOID:12365"}) return p


## what is the clinical outcome pathway of imatinib for treatment of Hypereosinophilic Syndrome?
match (n) where n.name in ["imatinib"] or n.description in ["BCR","Signaling by the B cell receptor (BCR)", "FOXP3", "blood", "hypereosinophilic syndrome"] return n

[citation](https://www.ncbi.nlm.nih.gov/pmc/articles/PMC2579962/pdf/nihms-69803.pdf)


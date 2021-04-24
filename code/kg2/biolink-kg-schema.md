# Translator Project knowledge graph schema
## Generated from the Biolink model version 1.4.0
## by the script [`biolink_yaml_to_schema_documentation.py`](biolink_yaml_to_schema_documentation.py)

# Node


*Biolink knowledge graph node*


## Properties


- **`id`** *(uriorcurie)*: A unique identifier for an entity. Must be either a CURIE shorthand for a URI or a complete URI; **required: True**.

- **`iri`** *(uriorcurie)*: An IRI for an entity. This is determined by the id using expansion rules.; required: False.

- **`category`** *(['uriorcurie'])*: Name of the high level ontology class in which this entity is categorized. Corresponds to the label for the biolink entity type class.In a neo4j database this MAY correspond to the neo4j label tag.In an RDF database it should be a biolink model class URI.This field is multi-valued. It should include values for ancestors of the biolink class; for example, a protein such as Shh would have category values `biolink:Protein`, `biolink:GeneProduct`, `biolink:MolecularEntity`, ...In an RDF database, nodes will typically have an rdf:type triples. This can be to the most specific biolink class, or potentially to a class more specific than something in biolink. For example, a sequence feature `f` may have a rdf:type assertion to a SO class such as TF_binding_site, which is more specific than anything in biolink. Here we would have categories {biolink:GenomicEntity, biolink:MolecularEntity, biolink:NamedThing}; **required: True**.

- **`type`** *(string)*: ; semantic URI: rdf:type; required: False.

- **`name`** *(string)*: A human-readable name for an attribute or entity.; semantic URI: rdfs:label; required: False.

- **`description`** *(string)*: a human-readable description of an entity; semantic URI: dct:description; required: False.

- **`source`** *(string)*: a lightweight analog to the association class 'has provider' slot, which is the string name, or the authoritative (i.e. database) namespace, designating the origin of the entity to which the slot belongs.; required: False.

- **`provided_by`** *(['agent'])*: connects an association to the agent (person, organization or group) that provided it; required: False.

- **`has_attribute`** *(['attribute'])*: connects any entity to an attribute; required: False.

# Edge


*Biolink knowledge graph edge*


## Properties


- **`id`** *(uriorcurie)*: A unique identifier for an entity. Must be either a CURIE shorthand for a URI or a complete URI; **required: True**.

- **`iri`** *(uriorcurie)*: An IRI for an entity. This is determined by the id using expansion rules.; required: False.

- **`category`** *(['uriorcurie'])*: Name of the high level ontology class in which this entity is categorized. Corresponds to the label for the biolink entity type class.In a neo4j database this MAY correspond to the neo4j label tag.In an RDF database it should be a biolink model class URI.This field is multi-valued. It should include values for ancestors of the biolink class; for example, a protein such as Shh would have category values `biolink:Protein`, `biolink:GeneProduct`, `biolink:MolecularEntity`, ...In an RDF database, nodes will typically have an rdf:type triples. This can be to the most specific biolink class, or potentially to a class more specific than something in biolink. For example, a sequence feature `f` may have a rdf:type assertion to a SO class such as TF_binding_site, which is more specific than anything in biolink. Here we would have categories {biolink:GenomicEntity, biolink:MolecularEntity, biolink:NamedThing}; required: False.

- **`type`** *(string)*: ; semantic URI: rdf:type; required: False.

- **`name`** *(string)*: A human-readable name for an attribute or entity.; semantic URI: rdfs:label; required: False.

- **`description`** *(string)*: a human-readable description of an entity; semantic URI: dct:description; required: False.

- **`source`** *(string)*: a lightweight analog to the association class 'has provider' slot, which is the string name, or the authoritative (i.e. database) namespace, designating the origin of the entity to which the slot belongs.; required: False.

- **`provided_by`** *(['agent'])*: connects an association to the agent (person, organization or group) that provided it; required: False.

- **`has_attribute`** *(['attribute'])*: connects any entity to an attribute; required: False.

- **`subject`** *(node-id)*: connects an association to the subject of the association. For example, in a gene-to-phenotype association, the gene is subject and phenotype is object.; semantic URI: rdf:subject; **required: True**.

- **`predicate`** *(uriorcurie)*: A high-level grouping for the relationship type. AKA minimal predicate. This is analogous to category for nodes.; semantic URI: rdf:predicate; **required: True**.

- **`object`** *(node-id)*: connects an association to the object of the association. For example, in a gene-to-phenotype association, the gene is subject and phenotype is object.; semantic URI: rdf:object; **required: True**.

- **`relation`** *(uriorcurie)*: The relation which describes an association between a subject and an object in a more granular manner. Usually this is a term from Relation Ontology, but it can be any edge CURIE.; **required: True**.

- **`negated`** *(boolean)*: if set to true, then the association is negated i.e. is not true; required: False.

- **`qualifiers`** *(['ontology class'])*: connects an association to qualifiers that modify or qualify the meaning of that association; required: False.

- **`publications`** *(['publication'])*: connects an association to publications supporting the association; required: False.

# JSON Example
To see an example JSON serialization of a simple KG, refer to the document [KGX Format](https://github.com/biolink/kgx/blob/master/specification/kgx-format.md).

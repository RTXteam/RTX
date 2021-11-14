### Expand's logic

This is a high-level explanation of how Expand works and the decisions it makes, focused on the parts that may need fine-tuning/tweaking over time.

1. Expand determines what order to expand the QEdges in, starting from a "pinned" QNode (i.e., a QNode with curies specified in its `ids` property). It loops through those QEdges, expanding them one-by-one.
2. **Pre-prune**: First Expand does a "pre-prune" step:
   1. If there are more than N Nodes in the KnowledgeGraph fulfilling either of the current QEdge's two QNodes, Expand will prune those Nodes back so that there are only N of them
   2. Currently, N (the prune "threshold") is set as follows (corresponding code is [here](https://github.com/RTXteam/RTX/blob/a5c4b9e780fe6cda3372f885c02774a74affdbad/code/ARAX/ARAXQuery/ARAX_expander.py#L1191-L1214)):
      1. If both of the QNodes are pinned: 5000
      2. Otherwise:
         1. If the unpinned QNode's categories include `NamedThing` or `ChemicalEntity` **and** the predicates include `related_to`: 100
         2. If the unpinned QNode's categories include `NamedThing` or `ChemicalEntity` but the predicate(s) are more specific than `related_to`: 200
         3. Otherwise: 500
   3. When there are more than N nodes for a particular QNode, Expand prunes them back with:
      1. FET: It overlays FET if there are fewer than 100,000 edges already in the KG
         1. This 100k limit was added to prevent slowdowns that were happening when the KG is very large (100k is rather arbitrary)
      2. The Ranker: It then forms "intermediate" results using Resultify and runs those through the Ranker
3. **KP selection**: For each QEdge, KPs are selected based on their `/meta_knowledge_graph` endpoints. A KP is selected if its `MetaKnowledgeGraph` has at least one `MetaEdge` whose:
   1. Subject is in the subject QNode's categories or is a descendant of those categories,
   2. Predicate is in the QEdge's predicates or is a descendant of those predicates, and
   3. Object is in the object QNode's categories or is a descendant of those categories 
4. **Curie conversion**: Expand creates a local `QueryGraph` for each QEdge that contains the QEdge and its two QNodes (this is the `QueryGraph` it sends to KPs)
   1. If this is an intermediate hop, curies returned from the previous hop(s) will be fed into this hop by adding them to the local QueryGraph as appropriate (in the appropriate QNode's `ids` property)
   2. Each KP gets its own variation of this local QueryGraph using only curies of the kind they support:
      1. Curies in the QueryGraph are left as they are (not converted/transformed) if the KP's `MetaKnowledgeGraph` says that they support the curie's prefix (for the category at hand)
      2. If the KP does not support the curie's prefix, then Expand looks for an equivalent curie with a prefix that they do support (using the NodeSynonymizer)
         1. If there are multiple supported prefixes with equivalent curies, Expand (essentially randomly) chooses one prefix to send
         2. All equivalent curies using the chosen supported prefix are sent to the KP (e.g., if Expand chooses to use the NCBIGene prefix and the synonym cluster for the given curie contains two NCBIGene curies, both will be sent to the KP)
5. **Timeouts**: When Expand sends the local QG for the current QEdge to each KP, it waits a certain amount of time for a response before timing out. The timeout for each QEdge is set as follows:
   1. If the user specified a timeout (in `Query`->`query_options`-> `kp_timeout`), that timeout will be used (note that the units are seconds)
   2. Otherwise if the KP being queried is RTX-KG2, the timeout is 10 minutes
      1. This is a crude way to avoid issues where KG2 times out on large queries for which it's the only KP that can answer
   3. Otherwise, the timeout is 2 minutes
6. After getting answers from KPs for the current QEdge, Expand canonicalizes and merges their answers into the main `KnowledgeGraph` and moves onto the next QEdge (if any remain)
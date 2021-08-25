### BiolinkHelper

This module provides a few methods for easy access to Biolink Model info. It uses a local (cached) copy of the Biolink Model, transformed for easy lookups. Its data source is the [Biolink Model YAML](https://github.com/biolink/biolink-model/blob/master/biolink-model.yaml) file.

#### How to use
Start by creating an instance of the helper:
```
from biolink_helper import BiolinkHelper
biolink_helper = BiolinkHelper()
```
It will automatically use the Biolink Model version that ARAX is currently on (as specified in the ARAX OpenAPI YAML file). If you want to use a different version, you can specify it via the optional `biolink_version` parameter (not recommended).

Examples of ways to get **ancestors**:
```
biolink_helper.get_ancestors("biolink:Drug")
biolink_helper.get_ancestors(["biolink:Drug", "biolink:Protein"])
biolink_helper.get_ancestors("biolink:Drug", include_mixins=False)
biolink_helper.get_ancestors("biolink:Protein", include_conflations=False)
biolink_helper.get_ancestors("biolink:treats")
```

Examples of ways to get **descendants**:
```
biolink_helper.get_descendants("biolink:ChemicalEntity")
biolink_helper.get_descendants(["biolink:ChemicalEntity", "biolink:Protein"])
biolink_helper.get_descendants("biolink:ChemicalEntity", include_mixins=False)
biolink_helper.get_descendants("biolink:Protein", include_conflations=False)
biolink_helper.get_descendants("biolink:related_to")
```

Ancestors/descendants are always returned in a list. Relevant mixins are included in the returned list by default, but you can turn that behavior off via the `include_mixins` parameter, as shown in some of the above examples. Inclusion of ARAX-defined conflations can be controlled via the `include_conflations` parameter (default is True).

Other available methods include getting **canonical predicates**:

```
biolink_helper.get_canonical_predicates("biolink:treated_by")
biolink_helper.get_canonical_predicates(["biolink:treated_by", "biolink:related_to"])
```

And **filtering out mixins**:

```
biolink_helper.filter_out_mixins(["biolink:ChemicalEntity", "biolink:PhysicalEssence"]])
```

You can also get the **current ARAX Biolink version** (parsed from the OpenAPI YAML) like so:

```
biolink_helper.get_current_arax_biolink_version()
```

#### Debugging

If desired, you can view the local copy of the BiolinkHelper's lookup map in your clone of the repo at `RTX/code/ARAX/BiolinkHelper/biolink_lookup_map_X.Y.Z.json`, where X.Y.Z is the Biolink version (e.g., 2.1.0).

Note that you must run an ARAX query in order for this map to be generated (after that first query, the map is never regenerated or updated for the given Biolink version). BiolinkHelper actually uses a pickle version of this map; the JSON version is just there for easier debugging/viewing.

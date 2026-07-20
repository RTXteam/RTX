"""
Round-1 audit of the proposed blocklist (issue-2654), done by hand-judgment on
NAME + CATEGORY only (no model features / scores consulted).

Policy (set by the domain team): specific entities are KEPT in the graph, not
blocklisted. So specific organs, cell types, genes, proteins, cell lines,
devices, organisms, cohorts, etc. that the model flagged are FALSE POSITIVES and
become hard negatives (label 0) for retraining. Only genuine umbrella terms in
those categories stay "generic".

Scope: round 1 covers the SPECIFIC-ENTITY categories, where the model's
"high-degree => generic" error is unambiguous and low-risk to correct. The
genuinely MIXED categories (ChemicalEntity, Disease, BiologicalProcess,
Procedure, PhenotypicFeature, Pathway, MolecularActivity) are DEFERRED to a
later round -- they need a broad-class-vs-specific split that is riskier to do
blind, and the entity fix is the high-value win first.

Output:
  hard_negatives_round1.txt   node ids the model wrongly flagged (label 0)
  confirmed_generics_round1.txt  umbrella terms correctly flagged (optional label 1)
Deferred/mixed-category candidates are left out (stay unlabeled, label -1).
"""
import pandas as pd

PROPOSED = "/home/hodgesf/Desktop/code/proposed_blocklist.csv"
HARDNEG_OUT = "/home/hodgesf/Desktop/code/hard_negatives_round1.txt"
GENERIC_OUT = "/home/hodgesf/Desktop/code/confirmed_generics_round1.txt"

# Specific-entity categories: default every candidate here to HARD NEGATIVE,
# except names in GENERIC_NAMES below.
HARDNEG_CATEGORIES = {
    "biolink:AnatomicalEntity", "biolink:GrossAnatomicalStructure",
    "biolink:Gene", "biolink:Protein", "biolink:Polypeptide",
    "biolink:Cell", "biolink:CellularComponent", "biolink:Device",
    "biolink:OrganismTaxon", "biolink:Cohort", "biolink:NucleicAcidEntity",
    "biolink:GenomicEntity", "biolink:Human", "biolink:NamedThing",
    "biolink:Event", "biolink:Publication", "biolink:SubjectOfInvestigation",
    "biolink:ClinicalAttribute", "biolink:Attribute", "biolink:MolecularMixture",
    "biolink:SmallMolecule", "biolink:Behavior", "biolink:Activity",
    "biolink:ActivityAndBehavior", "biolink:Agent", "biolink:PhysicalEntity",
    "biolink:InformationContentEntity", "biolink:DiseaseOrPhenotypicFeature",
    "biolink:BiologicalEntity", "biolink:Phenomenon", "biolink:PhysiologicalProcess",
}

# Mixed categories -- deferred to round 2, left unlabeled this round.
DEFERRED_CATEGORIES = {
    "biolink:ChemicalEntity", "biolink:Disease", "biolink:BiologicalProcess",
    "biolink:Procedure", "biolink:PhenotypicFeature", "biolink:Pathway",
    "biolink:MolecularActivity", "biolink:ComplexMolecularMixture", "biolink:Drug",
}

# Genuine umbrella terms found WITHIN the specific-entity categories. These are
# correctly generic -> keep on blocklist, do NOT turn into hard negatives.
# Matched case-insensitively on the node name.
GENERIC_NAMES = {
    # anatomy / cells / components
    "anatomical entity", "anatomical structure", "material anatomical entity",
    "organ", "tissue", "body system", "body regions", "cellular_component",
    "cells", "cell", "bodily fluid", "body fluids", "multi cell part structure",
    "disconnected anatomical group", "developing anatomical structure",
    "microanatomic structure", "presumptive structure", "lateral structure",
    "abnormal cell", "cell line", "cell line, transformed", "organelle",
    "intracellular organelle", "membrane-bounded organelle",
    "intracellular membrane-bounded organelle", "organism substance",
    "tissue specimen", "biospecimen", "membrane", "protein-containing complex",
    "blood component", "parenchyma", "anatomical lobe",
    "non-connected functional system", "eukaryotic cell", "precursor cell",
    "normal cell", "viable cells", "entire cell", "cell region", "envelope",
    "subcellular fractions", "cellular anatomical structure", "membrane tissue",
    "human cell line", "mammalian cell specimen", "cultured cell",
    "multicellular anatomical structure", "organ part", "anatomical conduit",
    "organ subunit", "multi-tissue structure", "organ system subdivision",
    "body proper", "tube", "skeletal element", "regional part of nervous system",
    "germ layer", "stem cells", "protoplasm",
    # genes
    "genes", "genome", "oncogenes", "proto-oncogenes", "tumor suppressor genes",
    "pseudogenes", "gene family", "structural gene", "genetic structures",
    "homologous gene", "orthologous gene", "wild type",
    # organisms (kingdom / domain level)
    "organism", "microorganism", "prokaryote", "plants", "invertebrates",
    "algae", "parasites", "yeasts", "host organism", "fungi", "bacteria",
    "viruses", "eukaryota", "archaea", "chimera", "hybrids",
    "gram-positive bacteria", "rna viruses", "oncogenic viruses", "mosaic viruses",
    # devices
    "medical devices", "prosthesis", "imaging device", "monitoring device",
    "monitor device", "sensor device", "implants", "probes", "stimulator",
    "monitoring device", "drug delivery systems", "biosensors",
    # behavior / small molecule umbrellas
    "behavior", "small molecule",
}
GENERIC_NAMES = {n.lower() for n in GENERIC_NAMES}


def main() -> None:
    df = pd.read_csv(PROPOSED)
    df["name_l"] = df["name"].fillna("").str.lower()

    in_scope = df[df["category"].isin(HARDNEG_CATEGORIES)]
    is_generic = in_scope["name_l"].isin(GENERIC_NAMES)

    hardneg = in_scope[~is_generic]
    generic = in_scope[is_generic]
    deferred = df[df["category"].isin(DEFERRED_CATEGORIES)]

    hardneg["id"].to_csv(HARDNEG_OUT, index=False, header=False)
    generic["id"].to_csv(GENERIC_OUT, index=False, header=False)

    print(f"hard negatives (round 1): {len(hardneg):,}  -> {HARDNEG_OUT}")
    print(f"confirmed generics:       {len(generic):,}  -> {GENERIC_OUT}")
    print(f"deferred to round 2:      {len(deferred):,}  (mixed categories, left unlabeled)")
    print(f"total candidates:         {len(df):,}")
    print("\nhard negatives by category:")
    print(hardneg["category"].value_counts().to_string())


if __name__ == "__main__":
    main()

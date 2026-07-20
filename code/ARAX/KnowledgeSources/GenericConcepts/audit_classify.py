"""
Comprehensive hand-audit of the proposed blocklist (issue-2654), by NAME +
CATEGORY judgment only (no model features/scores). Supersedes audit_round1.py.

Policy (locked with the domain team):
  1. When uncertain whether something is a generic hub or a useful specific
     concept -> KEEP it (specific / hard negative). Bias against blocklisting.
  2. Broad drug/agent classes (Antibiotics, Opioids, ...) -> blocklist (generic).
     Elements / simple substances (Iron, Calcium, Phosphate ion) -> keep.
  3. Output is a PROPOSED list for human review; production general_concepts.json
     is never overwritten here.

Outputs (cumulative, cover the whole candidate set):
  hard_negatives.txt      specific concepts the model must learn are NOT generic
  confirmed_generics.txt   genuine umbrella/class terms (kept on blocklist)
Everything else is left unlabeled (label -1) -- the safe default.
"""
import re
import pandas as pd

# Candidate sources: the original score>=0.979 set, plus any later rounds'
# surfaced candidates (round3_candidates.csv, etc.). Missing files are skipped.
CANDIDATE_FILES = [
    "/home/hodgesf/Desktop/code/proposed_blocklist.csv",
    "/home/hodgesf/Desktop/code/round3_candidates.csv",
]
HARDNEG_OUT = "/home/hodgesf/Desktop/code/hard_negatives.txt"
GENERIC_OUT = "/home/hodgesf/Desktop/code/confirmed_generics.txt"

# Disease/anatomy umbrella patterns (broad category terms) -> generic.
GENERIC_PATTERNS = [
    re.compile(r"\bsystem (disorder|disease|neoplasm|cancer|tumou?r)s?$", re.I),
    re.compile(r"^(regulation|positive regulation|negative regulation) of ", re.I),
]

# Categories whose members are specific entities by default -> hard negative,
# unless the name is a genuine umbrella term (GENERIC_NAMES).
ENTITY_CATEGORIES = {
    "biolink:AnatomicalEntity", "biolink:GrossAnatomicalStructure", "biolink:Gene",
    "biolink:Protein", "biolink:Polypeptide", "biolink:Cell",
    "biolink:CellularComponent", "biolink:Device", "biolink:OrganismTaxon",
    "biolink:Cohort", "biolink:NucleicAcidEntity", "biolink:GenomicEntity",
    "biolink:Human", "biolink:NamedThing", "biolink:Event", "biolink:Publication",
    "biolink:SubjectOfInvestigation", "biolink:ClinicalAttribute",
    "biolink:Attribute", "biolink:MolecularMixture", "biolink:SmallMolecule",
    "biolink:Behavior", "biolink:Activity", "biolink:ActivityAndBehavior",
    "biolink:Agent", "biolink:PhysicalEntity", "biolink:InformationContentEntity",
    "biolink:DiseaseOrPhenotypicFeature", "biolink:BiologicalEntity",
    "biolink:Phenomenon", "biolink:PhysiologicalProcess",
    # mixed categories that are specific-dominated (umbrellas are the exception):
    "biolink:Disease", "biolink:BiologicalProcess", "biolink:Procedure",
    "biolink:PhenotypicFeature", "biolink:MolecularActivity", "biolink:Pathway",
}
# Categories left UNLABELED by default (broad classes must not be taught as
# "specific"); only their enumerated specific members become hard negatives.
CHEM_CATEGORIES = {
    "biolink:ChemicalEntity", "biolink:Drug", "biolink:ComplexMolecularMixture",
}

# --- Genuine umbrella / class terms -> confirmed generic (kept on blocklist) ---
GENERIC_NAMES = {n.lower() for n in {
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
    # organisms (kingdom / domain / very high level)
    "organism", "microorganism", "prokaryote", "plants", "invertebrates",
    "algae", "parasites", "yeasts", "host organism", "fungi", "bacteria",
    "viruses", "eukaryota", "archaea", "chimera", "hybrids",
    "gram-positive bacteria", "rna viruses", "oncogenic viruses", "mosaic viruses",
    "viridiplantae", "helminths", "aquatic organisms", "protista", "microalgae",
    "plankton", "enveloped virus", "human virus",
    # devices
    "medical devices", "prosthesis", "imaging device", "monitoring device",
    "monitor device", "sensor device", "implants", "probes", "stimulator",
    "drug delivery systems", "biosensors",
    # proteins / polypeptides (broad classes) -- fixes round-1 slip
    "protein", "proteins", "peptide", "peptides", "polypeptide", "antibody",
    "antibodies", "monoclonal antibodies", "immunoglobulins", "receptor",
    "cytokine", "chemokine", "growth factor", "amino acid", "amino acids",
    "enzyme", "enzymes", "hormone", "hormones", "vaccine", "vaccines", "venoms",
    "serpins", "peptide hydrolases", "protein subunits", "oligopeptides",
    "glycopeptides", "cyclic peptides", "micrornas", "kinins", "neuropeptides",
    "lymphokines", "gonadotropins", "interferons", "amino acids, essential",
    # disease umbrellas (top-level only; specific diseases are kept)
    "disease", "human disease", "cancer", "neoplasm", "disorder by site",
    "neoplasm by special category", "genetic disease", "cardiovascular disorder",
    "infectious disease", "neurodegenerative disease", "viral disease",
    "mental disorder", "cns disorder", "pathologic processes", "pathogenesis",
    "disease progression", "wounds and injuries", "injury", "complication",
    "adverse effect", "adverse effects", "fibrosis", "necrosis",
    "inflammatory response", "functional disorder", "syndrome", "carcinogenesis",
    "metastasis", "neoplasm metastasis", "noncommunicable diseases",
    "neoplasm by morphology", "neoplasms by histologic type",
    "nervous system disorder", "musculoskeletal system disorder",
    "digestive system disorder", "endocrine system disorder", "skin disorder",
    "lung disorder", "heart disorder", "kidney disorder", "liver disorder",
    "eye disorder", "retinal disease", "brain disorder", "reproductive disorder",
    "hematologic disorder", "cancer or benign tumor",
    "neoplastic disease or syndrome", "non-neoplastic disorder",
    "associated disease", "primary disorders", "recurrent disease",
    "neglected diseases", "nutritional and metabolic diseases",
    "autosome disorders", "chromosome aberrations", "infection", "sepsis",
    "poisoning", "trauma", "physical trauma", "major injury",
    # biological process umbrellas (top-level GO / broad only)
    "biological process", "biological_process", "cellular process",
    "metabolic process", "biological regulation", "regulation of biological process",
    "regulation of cellular process", "primary metabolic process",
    "developmental process", "response to stimulus", "transport", "localization",
    "establishment of localization", "biosynthetic process", "signaling",
    "secretion", "multicellular organismal process", "cellular component organization",
    "system development", "system process", "macromolecule metabolic process",
    "catabolic process", "regulation of macromolecule metabolic process",
    "regulation of primary metabolic process", "regulation of biosynthetic process",
    "nucleobase-containing compound metabolic process", "macromolecule biosynthetic process",
    "establishment of localization in cell", "cellular localization",
    "cellular response to chemical stimulus", "gene expression",
    "biological adaptation to stress", "cell communication", "signal release",
    # molecular activity umbrellas
    "gene product or complex activity", "enzyme activity", "catalytic activity",
    "binding [molecular function]", "protein binding", "molecular_function",
    "signal transduction pathways", "signal pathways", "biochemical pathway",
    "biochemical reaction", "biosynthetic pathways", "metabolic control",
    "protein function", "receptor binding", "ligand binding", "receptor signaling",
    # procedure umbrellas
    "therapeutic procedure", "interventional procedure", "surgical procedures",
    "operative surgical procedures", "diagnosis", "medical imaging",
    "diagnostic tests", "complementary therapies", "screening procedure",
    "manipulation procedure", "injection procedure", "implantation procedure",
    "treatment protocols", "combined modality therapy", "conservative treatment",
    # phenotypic-feature umbrellas
    "sign or symptom", "phenotypic abnormality", "symptom", "sign", "test result",
    "laboratory test result", "finding by cause", "disability", "lesion",
    "pathology result", "histopathology result", "signs and symptoms",
    "morbidity", "high risk", "high risk of", "high level", "low level",
    "moderate level",
    # chemical / drug classes (structural classes + drug classes -> blocklist)
    "chemical entity", "molecular entity", "molecule", "organic molecular entity",
    "organic molecule", "organic compound", "inorganic molecular entity",
    "compound", "ion", "anion", "cation", "organic ion", "inorganic ion",
    "organic cation", "organic anion", "inorganic cation", "inorganic ion",
    "macromolecule", "polymer", "lipid", "lipids", "carbohydrate",
    "carbohydrates and carbohydrate derivatives", "nucleic acid", "dna", "rna",
    "steroid", "fatty acid", "hydrocarbon", "alcohol", "aldehyde", "ketone",
    "ester", "ether", "amine", "amide", "phenols", "acid", "organic acid",
    "carboxylic acid", "hydroxides", "oxide", "salt", "mineral", "metabolite",
    "small molecule", "atom", "group", "organic group", "polysaccharide",
    "oligosaccharide", "glycan", "glycoside", "sterol", "terpene", "terpenoid",
    "isoprenoid", "flavonoids", "polyphenol", "alkaloid", "nucleotide",
    "nucleoside", "nucleobase", "prostaglandin", "quinone", "polyketide",
    "aromatic compound", "polycyclic compound", "heterocyclic compound",
    "cyclic compound", "organic cyclic compound", "organic heterocyclic compound",
    "organooxygen compound", "organonitrogen compound", "organosulfur compound",
    "organic aromatic compound", "carbonyl compound", "carboxamide", "lactone",
    "lactam", "macrocycle", "phospholipid", "glycerolipid", "glyceride",
    "triglyceride", "phosphoric acid derivative", "amino-acid residue",
    "reactive oxygen species", "messenger rna", "ribosomal rna",
    "biopolymers", "information biomacromolecule", "coordination entity",
    # drug/agent classes (decision 2 -> blocklist)
    "pharmaceutical preparations", "antibiotics", "opioids", "opiates",
    "diuretics", "anticoagulants", "antioxidants", "analgesic", "analgesics",
    "anesthetics", "stimulant", "anticonvulsants", "antidepressive agents",
    "antipsychotic agents", "protease inhibitors", "agonists", "inhibitor",
    "activator", "anti-inflammatory agents", "anti-inflammatory agents, non-steroidal",
    "immunomodulators", "immunosuppressive agents", "calcium channel blockers",
    "adrenergic beta-antagonists", "antineoplastic agent", "neurotransmitters",
    "vitamins", "vitamin", "hormone", "toxin", "antigens", "electrolytes",
    "buffers", "dyes", "reagents", "vaccines, dna", "biological factors",
    "biological products", "natural products", "xenobiotics", "second messenger",
    "signaling molecule", "neurohormones", "neuromodulators", "cytokinins",
    "auxins", "biological response modifiers", "immunological adjuvant",
    "antimalarials", "antidiabetics", "anticholesteremic agents", "herbicides",
    "insecticides", "irritants", "mycotoxin", "allergens", "trace elements",
    "culture media", "fixatives", "solvents", "organic solvent product",
    "biogenic amines", "steroid hormone", "gonadal hormones", "sex hormones",
    "chemical cofactor", "second messenger systems",
    # round 3: chemical structural classes newly surfaced (all generic)
    "polyatomic cation", "ammonium ion derivative", "benzenes", "sulfonamide",
    "monoatomic cation", "organic sulfate", "macrolide", "purines", "naphthalenes",
    "unsaturated fatty acid", "pyridines", "heterotricyclic compound", "indoles",
    "ceramide", "azole", "glycolipid", "pyrimidines", "glycosphingolipid",
    "sphingolipid", "hydroxy acids", "quinolines", "chlorobenzenes", "benzopyran",
    "cyclic ether", "piperidines", "monovalent inorganic cation",
    "carbohydrate phosphate", "glucoside", "elemental hydrogen", "dicarboxylate",
    "epoxide", "nucleobase-containing molecular entity", "phosphatidylcholine",
    "saponin", "pyrrolidines", "monosaccharide", "piperazines", "benzamides",
    "acyl-coa", "amino-acid zwitterion", "flavonoid", "triol", "cyclic amide",
    "amino sugar", "diglyceride", "sulfide", "glycerophospholipid",
    "long-chain fatty acid", "phosphatidylethanolamine", "anthracenes", "furans",
    "hydroxy steroid", "acetamides", "disaccharide", "pyranone", "amino alcohol",
    "nitro compound", "quaternary ammonium ion", "fatty acids, volatile", "sugars",
    "glycoconjugates", "metals", "diphosphonates", "barbiturates",
    "dietary carbohydrates", "adrenal cortex hormones", "pyranone",
    # round 3: disease umbrellas (broad category terms)
    "benign neoplasm", "hematopoietic and lymphoid cell neoplasm", "rare diseases",
    "metabolic disease", "inflammatory disease", "intestinal disorder",
    "connective tissue disorder", "immune system disorder",
    "lymphoproliferative syndrome", "soft tissue neoplasm", "metastatic neoplasm",
    "neuromuscular disease", "childhood neoplasm", "hepatobiliary disorder",
    "neuroendocrine neoplasm", "pediatric disorder", "recurrent tumor",
    "rare disease",
    # round 3: molecular-function / process umbrellas
    "hydrolase activity", "oxidoreductase activity", "dna metabolic process",
    "protein localization",
}}

# --- ChemicalEntity: specific molecules / elements -> HARD NEGATIVE (keep) -----
# CHEBI/UMLS/MESH:D specific molecules & elements we read in the ChemicalEntity
# list (namespaces UNII / PUBCHEM.COMPOUND / DRUGBANK / MESH:C are handled as
# specific by prefix below, so they are not repeated here).
CHEM_SPECIFIC_NAMES = {n.lower() for n in {
    "graphite", "ammonia", "phosphate ion", "phosphorus", "cholesterol",
    "nitrogen", "adenosine", "glutathione", "cysteine", "sodium chloride",
    "iron", "d-glucose", "acetylcholine", "arginine", "calcium", "urea",
    "tryptophan", "serotonin", "glycerin", "carbon dioxide", "sucrose",
    "warfarin", "glutamic acid", "glycine", "choline", "salicylic acid",
    "taurine", "l-glutamine", "dopamine", "water", "oxygen atom", "hydron",
    "copper", "zinc", "iodine", "potassium atom", "sodium atom", "magnesium atom",
    "manganese atom", "calcium cation", "chloride ion", "bicarbonate ion",
    "proton", "superoxide", "nitric oxide", "carbon monoxide", "hydrogen(.)",
    "ethanol", "methanol", "acetic acid", "formaldehyde", "hydrochloric acid",
    "phosphoric acid", "leucine", "proline", "alanine", "histidine", "serine",
    "valine", "isoleucine", "phenylalanine", "tyrosine", "asparagine",
    "aspartic acid", "lysine", "threonine", "methionine", "glutamine",
    "estradiol", "testosterone", "progesterone", "corticosterone", "aldosterone",
    "hydrocortisone", "dexamethasone", "epinephrine", "norepinephrine",
    "histamine", "melatonin", "morphine", "cocaine", "nicotine", "caffeine",
    "atp", "adp", "amp", "nadh", "nad(+)", "cyclic amp", "gtp", "ctp", "utp",
    "biotin", "thiamine", "folic acid", "ascorbic acid", "quercetin",
    "resveratrol", "curcumin", "cisplatin", "doxorubicin", "tamoxifen",
    "aspirin", "acetaminophen", "lidocaine", "propranolol", "diazepam",
    "propofol", "verapamil", "clonidine", "levodopa", "sorbitol", "inositol",
    "heparin", "hyaluronic acid", "chlorophyll", "rotenone", "atrazine",
    "palmitic acid", "arachidonate", "dopamine", "gaba", "aminobutyrates",
    "creatinine", "bilirubin", "lactate", "pyruvate", "citrate", "glycogen",
    "sodium arsenite", "cadmium", "chromium", "nickel atom", "cobalt chloride",
    "silicon", "silicon dioxide", "aluminium atom", "arsenic atom", "selenium",
    "vitamin a", "vitamin b", "vitamin k", "vitamin d+metabolites",
    "ergocalciferol", "folate", "tretinoin", "retinoid",
}}


def main() -> None:
    import os
    frames = [pd.read_csv(f) for f in CANDIDATE_FILES if os.path.exists(f)]
    df = pd.concat(frames, ignore_index=True).drop_duplicates("id")
    df["name_l"] = df["name"].fillna("").str.lower()
    df["prefix"] = df["id"].str.split(":").str[0]

    def is_generic_name(name: str) -> bool:
        return name in GENERIC_NAMES or any(p.search(name) for p in GENERIC_PATTERNS)

    hardneg, generic = set(), set()
    for _, r in df.iterrows():
        cat, name, nid, pfx = r["category"], r["name_l"], r["id"], r["prefix"]
        if is_generic_name(name):
            generic.add(nid)
        elif cat in ENTITY_CATEGORIES:
            hardneg.add(nid)                                  # specific entity
        elif cat in CHEM_CATEGORIES:
            if pfx in {"UNII", "PUBCHEM.COMPOUND", "DRUGBANK", "CHEMBL.COMPOUND"} \
               or nid.startswith("MESH:C") or name in CHEM_SPECIFIC_NAMES:
                hardneg.add(nid)                              # specific molecule/element
            # else: broad chemical class -> leave UNLABELED (safe)

    pd.Series(sorted(hardneg)).to_csv(HARDNEG_OUT, index=False, header=False)
    pd.Series(sorted(generic)).to_csv(GENERIC_OUT, index=False, header=False)
    print(f"hard negatives:     {len(hardneg):,}  -> {HARDNEG_OUT}")
    print(f"confirmed generics: {len(generic):,}  -> {GENERIC_OUT}")
    print(f"left unlabeled:     {len(df) - len(hardneg) - len(generic):,}")
    print("\nhard negatives by category:")
    print(df[df.id.isin(hardneg)]["category"].value_counts().to_string())


if __name__ == "__main__":
    main()

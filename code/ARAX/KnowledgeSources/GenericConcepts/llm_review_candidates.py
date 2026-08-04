"""
Classify generic-concept candidates with an LLM (issue-2654).

Sends the candidate names to an OpenAI-compatible endpoint in batches and
records a binary verdict for each: the concept is a class of things, or it is
one identifiable thing. Written against the OpenAI client, so the same script
drives a local vLLM server by changing --base-url.

Verdicts accumulate across rounds. Each run skips candidates already named in
the output files and appends only the new ones, so retraining on a round's
verdicts and reviewing the candidates that fall out of it grows the labelled
set instead of replacing it. A node keeps whatever verdict it was first
given; it is never reclassified.

Input:
    CANDIDATES: id, name, category and score, from the training script.
    OUT_POS / OUT_NEG: verdicts from previous rounds, if any.

Output:
    OUT_POS / OUT_NEG: node ids the model judged generic and specific, which
    the labels build folds in as supplemental positives and hard negatives.
"""

import argparse
import asyncio
import datetime
import json
import os
import time

import pandas as pd
from openai import AsyncOpenAI

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CANDIDATES = os.path.expanduser("~/Desktop/code/generic_candidates.csv")
OUT_POS = os.path.expanduser("~/Desktop/code/llm_confirmed_generics.txt")
OUT_NEG = os.path.expanduser("~/Desktop/code/llm_hard_negatives.txt")
ROUNDS_FILE = os.path.join(BASE_DIR, "data", "review_rounds.tsv")

MAX_ATTEMPTS = 3

# Categories whose Biolink label is withheld from the model. See tag().
SUPPRESSED_CATEGORIES = {"biolink:GeneFamily"}

# Holds the first request exception of the run, so it is printed once instead
# of per batch.
FIRST_ERROR: list[Exception] = []

VERDICT_SCHEMA = {
    "type": "object",
    "properties": {
        "verdicts": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "i": {"type": "integer"},
                    "v": {"type": "string", "enum": ["G", "S"]},
                },
                "required": ["i", "v"],
            },
        },
    },
    "required": ["verdicts"],
}

SYSTEM_PROMPT = """\
You classify biomedical knowledge-graph nodes as GENERIC or SPECIFIC.

GENERIC ("G"): the node primarily names an umbrella class, family, role, or
category. Its members are the more informative answers a user wants.

SPECIFIC ("S"): the node names a recognized, identifiable biomedical concept
at answer granularity.

## CORE TEST

Would a knowledgeable user receiving this node as an answer have to ask
"which one?" before they could act on it?

  proton pump inhibitor -> omeprazole, pantoprazole, lansoprazole   G
  omeprazole            -> already identifies one drug              S

Having descendants is NOT the test. Almost every node has descendants. What
matters is what KIND they are:

  ALTERNATIVES: the children are different things, and naming one of them is
  a better answer. The node is a placeholder.                        -> G
  REFINEMENTS: the children describe the same thing in more detail. The node
  already picks out something you can point at.                      -> S

  transport            | ion transport, protein transport and lipid
                         transport are DIFFERENT processes              G
  sodium ion transport | the modifier already picks out one process     S

Ignore part-of, anatomical components, pathway steps and participants,
process inputs and outputs, locations, physical instances, individual
organisms, and occurrences. None of them bear on this.

## BREADTH IS NOT GENERICNESS

Ontology children, many parts, and recognized subtypes never make a node
generic. Nearly every biomedical concept can be described more precisely.
All of these are SPECIFIC:

  brain   respiratory system   blood   Alzheimer disease   macrophage
  Homo sapiens   glycolysis   cholesterol metabolic process

The question is whether the node's primary semantic role is to GROUP
alternative answer-level concepts.

## IDENTIFIERS AND UNKNOWN LABELS

Accessions, database identifiers, gene symbols and catalogue labels denote
one catalogued entity. They are SPECIFIC even when their meaning is unknown:

  CHEMBL5407267 | C6orf180 | sytl2b | 4933405D12Rik | A0A0S2Z3D6_HUMAN
  C01A2.4 | US11504367, Example 349

Do not extend this to unfamiliar natural-language labels. An unfamiliar
phrase may still name a class, family, or role.

## ABBREVIATIONS

Expand before classifying. PPI (proton pump inhibitor), NSAID, SSRI are G.
ATP, TP53, IL-6, HIV-1 are S.

## DOMAIN CONTRASTS

GENERIC left of the bar, SPECIFIC right.

processes   Word count is NOT a signal. Short names are often SPECIFIC and
            long names are often GENERIC. Judge the concept.

            A process term is GENERIC only when it is a bare umbrella root
            with no qualifying modifier. As soon as a modifier picks out
            what the process acts on, where, or in which direction, the
            term is SPECIFIC.

            biological process, cellular process, metabolic process,
            transport, development, localization, binding, signaling,
            response to stimulus, regulation of cellular process,
            positive regulation of biological process          -> G

            sodium ion transport, forebrain development, translation,
            endocytosis, apoptosis, glycolysis, gliogenesis, remyelination,
            cell-matrix adhesion, peptide hormone secretion,
            DNA-templated transcription, regulation of T cell activation,
            cellular response to estrogen stimulus, ceramide metabolic
            process, macrophage activation, protein localization to
            chromatin, myosin binding                          -> S
            An enzyme and its activity are different concepts:
              phosphatase activity G | S-formylglutathione hydrolase S

pathways    signaling pathway, metabolic pathway
            | TNF signaling, Retinol Metabolism, Digestion,
              Nucleotide Excision Repair, Visual phototransduction
            Every NAMED pathway is S. A "(Homo sapiens)" tag or database
            suffix is not part of the judgement.

anatomy     anatomical structure, tissue, epithelium, mucosa, gland, artery,
            blood vessel, nerve, organ system
            | thymus, bronchial artery, cervix epithelium, respiratory
              system, sarcoplasmic reticulum, aortic intima, hindgut,
              popliteal region
            Containing many parts does not make a structure generic.

taxa        organism, bacterium, virus, species, taxon
            | Homo sapiens, Escherichia coli, Coronaviridae, Alphavirus,
              Eucalyptus
            A formally named taxon is S at ANY rank. But UNSPECIFIED
            constructions stay G: "Proteus species", "unclassified virus",
            "an Enterobacteriaceae bacterium".

genes       gene, protein, gene family, kinase family, membrane protein,
            ion channel, transcription factor, cytokine, CYCLIN
            | TP53, BRCA1, EGFR, interleukin-6, hemoglobin,
              APOLIPOPROTEIN B, TELOMERASE REVERSE TRANSCRIPTASE
            Do not call a named protein generic merely because a source
            files it under a family.

chemicals   lipid, alcohol, ester, polysaccharide, halide, metal,
            amino acid, alkaloid, steroid
            | Gold, FLUORIDE, aspartate, cholesterol, ATP, D-glucose

drugs       drug, pharmaceutical preparation, kinase inhibitor, beta
            blocker, anticoagulant, antiviral agent
            | omeprazole, propranolol, imatinib, aspirin, etanercept

diseases    disease, disorder, cancer, carcinoma, lymphoma, anemia,
            cardiovascular disorder, disorder of knee
            | breast cancer, HER2-positive breast cancer, Alzheimer
              disease, asthma, myelitis, alopecia, ankylosis,
              complex partial epilepsy

procedures  surgery, imaging, therapy, screening, measurement, laboratory
            test, diagnostic procedure
            | Cardiopulmonary Bypass, Craniectomy, Ultrafast MRI,
              Bronchoalveolar Lavage, systolic blood pressure, hematocrit,
              Serum Calcium Level

cells       cell, immune cell, epithelial cell, precursor cell
            | macrophage, neutrophil, hepatocyte, osteoblast

devices     medical device, prosthesis, pacemaker, syringe, catheter
            | a uniquely named device model or product

people      nurses, oncologists, miners, graduate students, Canadian people
            and every other occupational or demographic category are G

Head words such as "inhibitor", "protein", "process", "activity", "disease"
or "device" are weak evidence, never a rule. A sufficiently identifying
modifier makes the whole concept SPECIFIC.

## WHEN UNSURE

Choose S if the label looks like a canonical named concept or a unique
identifier. Choose G only when the umbrella reading clearly dominates.
Require clear evidence before assigning G: wrongly removing a specific
concept deletes a valid answer, while a missed generic only leaves noise.

## OUTPUT

Return exactly one valid JSON object and nothing else:
{"verdicts":[{"i":1,"v":"G"},{"i":2,"v":"S"}]}

"G" = GENERIC, "S" = SPECIFIC. Emit exactly one verdict per input item.
Preserve the supplied numbers and order; numbering starts at 1. Never omit,
duplicate, renumber, or invent entries. No explanations, confidence scores,
comments, markdown, or code fences."""
def read_ids(path: str) -> list[str]:
    """
    Read one node id per line, tolerating the file not existing yet.

    Input:
        path: an output file from a previous round.

    Output:
        The ids it names in file order, or an empty list on the first round.
    """
    if not os.path.exists(path):
        return []
    with open(path, encoding="utf-8") as handle:
        return [line.strip() for line in handle if line.strip()]


def next_round(path: str) -> int:
    """
    Work out which round this run is.

    Input:
        path: the append-only round log.

    Output:
        The number of rounds already recorded, so the first run is 0. Read
        off the file rather than tracked separately, which keeps the log the
        single source of truth for how far the loop has gone.
    """
    if not os.path.exists(path):
        return 0
    with open(path, encoding="utf-8") as handle:
        return max(0, sum(1 for _ in handle) - 1)


def append_round(path: str, row: dict) -> None:
    """
    Add one row to the round log, writing a header if the file is new.

    Input:
        path: the append-only round log.
        row: column name to value, in column order.

    Output:
        None. Appends rather than rewrites so a crashed or interrupted round
        cannot cost the history of the ones before it.
    """
    os.makedirs(os.path.dirname(path), exist_ok=True)
    write_header = not os.path.exists(path)
    with open(path, "a", encoding="utf-8") as handle:
        if write_header:
            handle.write("\t".join(row) + "\n")
        handle.write("\t".join(str(value) for value in row.values()) + "\n")


def tag(category: str) -> str:
    """
    Format the category suffix for one item.

    Input:
        category: the node's Biolink category.

    Output:
        A bracketed suffix, or empty for a category that misleads more than
        it informs. PANTHER files every entry as GeneFamily whether it names
        a real family or a single protein, so the tag asserts "family" on
        SACSIN and APOLIPOPROTEIN B and the prompt then rules them generic.
        Suppressing it leaves the name to be judged on its own.
    """
    if category in SUPPRESSED_CATEGORIES:
        return ""
    return f" [{category.replace('biolink:', '')}]"


def render(rows: pd.DataFrame) -> str:
    """
    Format one batch as a numbered list.

    Input:
        rows: candidates with name and category.

    Output:
        One line per item, numbered from 1. Category is included because a
        bare name is often ambiguous: interleukin-6 reads as a class until
        its Protein category settles it. The numbering has to match the
        worked example in SYSTEM_PROMPT: against a 0-based list the model
        reconciles a highest label of 9 with an example starting at 1 by
        returning nine verdicts for ten items, and the batch is discarded.
    """
    return "\n".join(
        f"{n}. {row.name_}{tag(row.category)}"
        for n, row in enumerate(rows.itertuples(), 1))


def parse(reply: str, size: int) -> dict[int, str] | None:
    """
    Pull verdicts out of one reply.

    Input:
        reply: raw model output.
        size: how many items the batch contained.

    Output:
        Position to verdict, or None if the reply is unusable. A partial or
        malformed answer is rejected outright rather than salvaged, because a
        silently dropped index shifts every verdict after it.
    """
    try:
        payload = json.loads(reply[reply.index("{"):reply.rindex("}") + 1])
        verdicts = {int(v["i"]): v["v"].strip().upper()[:1]
                    for v in payload["verdicts"]}
    except (ValueError, KeyError, TypeError):
        return None

    if set(verdicts) != set(range(1, size + 1)):
        return None
    if not set(verdicts.values()) <= {"G", "S"}:
        return None
    return verdicts


async def classify(client: AsyncOpenAI, model: str, rows: pd.DataFrame,
                   gate: asyncio.Semaphore) -> list[str | None]:
    """
    Classify one batch, retrying on an unusable reply.

    Input:
        client: OpenAI-compatible client.
        model: model id to request.
        rows: the batch.
        gate: caps how many requests are in flight at once.

    Output:
        A verdict per row, None where every attempt failed. Decoding is
        constrained to VERDICT_SCHEMA rather than relying on the model to
        produce well-formed output. Temperature is zero throughout: this is a
        classification, and Qwen ships a generation_config defaulting to 0.7
        that would otherwise apply.
    """
    async with gate:
        for _ in range(MAX_ATTEMPTS):
            try:
                response = await client.chat.completions.create(
                    model=model,
                    messages=[
                        {"role": "system", "content": SYSTEM_PROMPT},
                        {"role": "user", "content": render(rows)}],
                    temperature=0.0,
                    max_tokens=16 * len(rows) + 64,
                    response_format={"type": "json_object"},
                    extra_body={"guided_json": VERDICT_SCHEMA})
            except Exception as error:
                # Reported once rather than per batch. Without this a wrong
                # --model 404s on every request and the run reports the
                # result as unparseable, which points at the prompt instead
                # of at the one-line cause.
                if not FIRST_ERROR:
                    FIRST_ERROR.append(error)
                    print(f"  request failed: {type(error).__name__}: "
                          f"{str(error)[:160]}")
                await asyncio.sleep(2)
                continue

            verdicts = parse(response.choices[0].message.content, len(rows))
            if verdicts is not None:
                return [verdicts[n] for n in range(1, len(rows) + 1)]

        return [None] * len(rows)


async def run(candidates: pd.DataFrame, args: argparse.Namespace
              ) -> tuple[pd.DataFrame, float]:
    """
    Classify every candidate.

    Input:
        candidates: rows to classify.
        args: parsed command line.

    Output:
        The same frame with a verdict column added, and how long it took.
    """
    client = AsyncOpenAI(base_url=args.base_url, api_key=args.api_key)
    gate = asyncio.Semaphore(args.concurrency)
    batches = [candidates.iloc[i:i + args.batch_size]
               for i in range(0, len(candidates), args.batch_size)]

    print(f"{len(candidates):,} candidates in {len(batches)} batches, "
          f"{args.concurrency} concurrent")
    started = time.monotonic()
    results = await asyncio.gather(
        *(classify(client, args.model, batch, gate) for batch in batches))
    elapsed = time.monotonic() - started

    candidates = candidates.copy()
    candidates["verdict"] = [v for batch in results for v in batch]
    failed = int(candidates["verdict"].isna().sum())
    print(f"done in {elapsed:.1f}s "
          f"({len(candidates) / elapsed:.0f} items/sec)"
          + (f"   {failed:,} unparseable" if failed else ""))
    return candidates, elapsed


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default="http://localhost:8000/v1")
    parser.add_argument("--api-key", default=os.environ.get(
        "OPENAI_API_KEY", "not-needed"))
    parser.add_argument("--model", default="Qwen/Qwen2.5-32B-Instruct-AWQ")
    parser.add_argument("--batch-size", type=int, default=10)
    parser.add_argument("--concurrency", type=int, default=16)
    args = parser.parse_args()

    candidates = pd.read_csv(CANDIDATES)
    candidates = candidates.rename(columns={"name": "name_"})

    existing = {path: read_ids(path) for path in (OUT_POS, OUT_NEG)}
    reviewed = {node for ids in existing.values() for node in ids}
    pending = candidates[~candidates["id"].isin(reviewed)]
    pending = pending.reset_index(drop=True)

    print(f"{len(reviewed):,} already reviewed, "
          f"{len(pending):,} of {len(candidates):,} candidates to classify")
    if pending.empty:
        print("nothing new to review")
        return

    scored, elapsed = asyncio.run(run(pending, args))

    totals = {}
    for path, verdict in ((OUT_POS, "G"), (OUT_NEG, "S")):
        fresh = list(scored.loc[scored["verdict"] == verdict, "id"])
        ids = list(dict.fromkeys(existing[path] + fresh))
        with open(path, "w", encoding="utf-8") as handle:
            handle.write("\n".join(ids) + "\n")
        print(f"wrote {len(ids):>6,} to {path}   (+{len(fresh):,} new)")
        totals[verdict] = (len(fresh), len(ids))

    unparseable = int(scored["verdict"].isna().sum())
    row = {
        "round": next_round(ROUNDS_FILE),
        "timestamp": datetime.datetime.now().isoformat(timespec="seconds"),
        "model": args.model,
        "batch_size": args.batch_size,
        "concurrency": args.concurrency,
        "candidates": len(candidates),
        "classified": len(pending),
        "unparseable": unparseable,
        "confirmed_new": totals["G"][0],
        "rejected_new": totals["S"][0],
        "confirmed_total": totals["G"][1],
        "rejected_total": totals["S"][1],
        "seconds": round(elapsed, 1),
    }
    append_round(ROUNDS_FILE, row)
    print(f"logged round {row['round']} to {ROUNDS_FILE}")


if __name__ == "__main__":
    main()

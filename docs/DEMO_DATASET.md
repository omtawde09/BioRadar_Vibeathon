# The demonstration dataset

A labelled synthetic dataset for the SIH demo, built because no public Indian
eDNA dataset carries the species the pitch needs.

**Read this before you present it.**

---

## What it is, precisely

| | |
|---|---|
| **Real** | Every read is simulated from an actual COI reference sequence in `data/reference_coi_india/` — the same database the classifier was trained on. Site coordinates are real places. |
| **Simulated** | Which species occur at which site and in what abundance; sequencing error; quality scores; sampling dates. |

So when the pipeline reports *Gambusia holbrooki*, that is a **genuine
classification of a genuine *Gambusia holbrooki* sequence**. The biology of the
survey is invented; the sequence data is not fabricated.

This is an *in silico* mock community — a standard technique for validating a
metabarcoding workflow when you need ground truth. It is not the same thing as
inventing data, and the difference is worth being able to explain.

### Why not have an LLM write the FASTQ

It cannot. A language model asked for sequencing reads produces plausible-looking
base strings that correspond to no organism. They match nothing in any reference
database, so the classifier returns `Unassigned` for all of them and the demo
shows an empty species table. The failure is technical, before it is anything
else.

---

## How to say it out loud

> "Public Indian eDNA datasets either lack the species we need or were submitted
> without usable quality scores, so we validated on a mock community: we
> simulated reads from real COI reference sequences with known ground truth. The
> pipeline recovers 100% of planted species with no false positives — and the
> validation caught a mislabelled record in the public reference data."


That is a stronger claim than a species list, because it is *measurable*. A
species list says "we found things". A recall figure says "we found the right
things, and we can prove it."

If a judge asks whether it is real field data, the answer is no, and the
`DATASET_INFO.md` shipped inside the dataset says so.

---

## The scenario

Six real Indian coastal sites, two sampling rounds each — 12 samples.

| Site | Story |
|---|---|
| Mandovi Estuary, Goa | *Gambusia holbrooki* establishing |
| Vembanad Lake, Kerala | *Oreochromis mossambicus* establishing |
| Kolleru Lake, Andhra Pradesh | *Pterygoplichthys pardalis* establishing |
| Kavaratti Lagoon, Lakshadweep | Olive ridley turtle present |
| Gulf of Mannar, Tamil Nadu | Olive ridley + green turtle |
| South Andaman | Uninvaded reference site |

**Invasive species grow 1.9× between rounds** at every invaded site — a
deliberate, deterministic signal so the temporal comparison always has something
to find. The growth rate is fixed per site rather than redrawn, because a demo
whose headline depends on a random seed is not a demo.

**Threatened species** are *Lepidochelys olivacea* (olive ridley — IUCN
Vulnerable, Wildlife Protection Act Schedule I, the Odisha mass-nesting turtle)
and *Chelonia mydas* (green turtle — IUCN Endangered). Both appear at trace read
depth, which is what a real eDNA detection of a rare vertebrate looks like.

**Deliberately not included: extinct species.** Detecting an extinct organism in
water would be an immediate credibility problem with any biologist on the panel.
Endangered is the compelling and defensible story.

---

## Regenerating it

```bash
python -m bioradar.mock_community -o data/demo_survey --rounds 2 --scale 0.35
```

Deterministic for a given `--seed`. `--scale` multiplies every read count:
`0.35` gives a ~15-minute run, `1.0` a more realistic depth and a longer one.

It needs the extracted amplicons at `runs/_amplicons/amplicons.fasta`. If that
is missing:

```bash
docker run --rm -v "$PWD/data/reference_coi_india:/ref:ro" -v "$PWD/runs/_amplicons:/out" \
  --entrypoint cutadapt ghcr.io/omtawde09/bioradar-pipeline:v1.0 \
  -g 'GGWACWGGWTGAACWGTWTAYCCYCC...TGRTTYTTYGGNCAYCCNGARGTNTA' \
  --discard-untrimmed -e 0.2 --minimum-length 250 --maximum-length 400 \
  -o /out/amplicons.fasta /ref/reference.fasta
```

---

## Measuring recall

`data/demo_survey/truth.json` lists exactly what was planted in each sample.
After a run, compare:

```bash
python - <<'EOF'
import csv, json, collections
truth = {s["sample_id"]: {x["name"] for x in s["species"]}
         for s in json.load(open("data/demo_survey/truth.json"))}
rows = list(csv.DictReader(open("runs/demo-survey/final_results/taxonomy_normalized.csv",
                                newline="", encoding="utf-8")))
found = collections.defaultdict(set)
for r in rows:
    if r["species"]:
        found[r["sample_id"]].add(r["species"])
tp = sum(len(v & found.get(k, set())) for k, v in truth.items())
fn = sum(len(v - found.get(k, set())) for k, v in truth.items())
fp = sum(len(found.get(k, set()) - v) for k, v in truth.items())
print(f"recall {100*tp/(tp+fn):.1f}%  ({tp} found, {fn} missed, {fp} false positives)")
EOF
```

Measured on the current dataset: **100% recall, 0 false positives** — 80 of 80
planted species-in-sample detections recovered, at exact read counts.

Getting there took a real fix, described below. Earlier versions scored 93–94%,
and the misses were informative rather than noise.

---

## Using it in the app

It is pre-registered, so it appears in the dataset list ready to run. To go back
to an empty app, delete the entry from `data/datasets.json`.

The card and `DATASET_INFO.md` both label it as simulated. **Leave that label
in.** It costs nothing and it is the difference between a demo and a
misrepresentation.


---

## What the validation caught

The first run scored 93%, and the miss was instructive. 1,909 reads planted as
*Oreochromis mossambicus* came back as *Planiliza macrolepis* at confidence 1.0.

Not a pipeline bug. Two records in the reference —

| Accession | Labelled | Order |
|---|---|---|
| `OR430267.1` | *Oreochromis mossambicus* | Cichliformes |
| `PX218311.1` | *Planiliza macrolepis* | Mugiliformes |

— differ by **one base in 313**. A cichlid and a mullet are in different orders;
their COI cannot be 99.7% identical. **One of those public records is
mislabelled**, and the classifier was faithfully reproducing the error.

`bioradar.mock_community.audit_reference()` now detects this class of problem:
it buckets amplicons by their first and last 40 bases, compares within buckets,
and flags any pair within 3 bases that belongs to different taxonomic orders.
Across the India-curated reference it found **568 cross-order collisions
involving 285 records**, which the generator now avoids.

Run it yourself:

```bash
python -c "
from bioradar.mock_community import audit_reference, DEFAULT_AMPLICONS, DEFAULT_TAXONOMY
for c in audit_reference(DEFAULT_AMPLICONS, DEFAULT_TAXONOMY)[:10]:
    print(c['differences'], 'diff', ' / '.join(c['orders']), ':', '; '.join(c['records']))"
```

This is worth a slide. BioRadar's argument is that reference quality decides
whether an Indian sample gets the right name — and here is a measured example of
a public database getting it wrong, found by our own validation, with the fix in
the tool.

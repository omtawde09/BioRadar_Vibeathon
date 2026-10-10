# Simulated demonstration dataset

**This is synthetic data. Do not present it as field-collected samples.**

## What is real

Every read is simulated from a **real COI reference sequence** in
`data/reference_coi_india/`, the same database the classifier was trained on.
When the pipeline reports a species, it is a genuine classification of a genuine
sequence for that species. The site coordinates are real locations.

## What is simulated

- Which species occur at which site, and in what abundance
- Sequencing error and Phred quality scores
- Sampling dates

In other words: the *experimental design* is invented, the *sequence data* is
derived from real references. This is a standard in-silico mock community, the
usual way to validate a metabarcoding workflow when ground truth is needed.

## Ground truth

`truth.json` lists exactly which species were planted in each sample and at what
read depth. Compare it against the pipeline output to measure recall — that
comparison is a far stronger result to show than a species list alone.

## Scenario

- **6 sites** across the Indian coast, **2 sampling rounds** each
- Invasive establishment at Mandovi, Vembanad and Kolleru, increasing between
  rounds so temporal comparison has something to find
- Threatened species at Kavaratti, Gulf of Mannar and South Andaman
- South Andaman acts as an uninvaded reference site

Invasive species planted: Clarias gariepinus, Cyprinus carpio, Gambusia holbrooki, Oreochromis mossambicus, Pterygoplichthys pardalis

Threatened species planted: Chelonia mydas (Endangered), Lepidochelys olivacea (Vulnerable, WPA Schedule I)

## Reproducing

    python -m bioradar.mock_community -o demo_survey --seed 2026

Deterministic for a given seed.

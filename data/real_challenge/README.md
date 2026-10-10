# data/real_challenge: the real public data for the Odyssey challenge

Everything here comes from public archives, byte for byte. Nothing was created, trimmed, converted or edited.
Pipeline data elsewhere under `data/` (india_*, indo_martapura) is left alone.

```
real_challenge/
  README.md              this file
  selection.json         which real sample answers which condition of the brief, and why (+ what is excluded)
  manifest.json          every dataset, file name, source URL, md5, sample ID and submitter metadata
  COMPLIANCE.md          generated: each challenge condition as PASS / PARTIAL / GAP (runner verify)
  datasets/
    ZENODO4025362_fish_egg_mock/        12 pooled libraries of 6 fish-egg mock communities with PUBLISHED proportions (COI, 16S) + the authors' reference library + ground_truth/   (12 runs)
    PRJNA1059782_pearl_river_12S/       12 mock communities + Pearl River Delta water, 2019-08 and 2019-11   (33 runs)
    PRJNA1433820_martapura_12S/         Martapura River freshwater fish, Indonesia, 2025-08                  (2 runs)
    PRJNA1269473_british_columbia_12S/  low-yield field samples: 361 and 814 reads                           (2 runs)
    PRJNA985779_uk_12S/                 field water blank, 343 reads                                         (1 run)
    PRJEB108476_bge_records/            archive run records only (metadata), for the data guard             (5,119 rows)
      each: README.md, manifest.json, raw/ (reads, not committed) or records/
  reference/
    refseq_fish_12s/     reference list: RefSeq fish mitogenomes cut to the MiFish-U amplicon (+ version, query)
    refseq_fish_coi_16s/ the same mitogenomes cut to the COI and 16S regions (published primers), for the fish-egg data
    cache/               downloaded mitogenomes (not committed; rebuilt by fetch)
  boundary/              protected-area polygon from OpenStreetMap (ODbL) for the GPS rule
  lists/                 invasive_species.json: documented invasive fish, danger levels, source links
  results/               computed output (not committed; rebuilt by `runner all`)
```

Commands (from the repo root):

```bash
python -m bioradar.adjudicate.runner fetch    # download the reads listed in manifest.json, md5-verified (retries; safe to re-run)
python -m bioradar.adjudicate.runner all      # process every sample
python -m bioradar.adjudicate.runner verify   # check every condition of the brief -> COMPLIANCE.md
```

Reads are R1 only for the 12S projects (the fish-egg files are already merged pairs). Raw reads and results are gitignored and rebuilt by the commands above. The built reference, the
records snapshot and the boundary are committed, so `fetch` does not re-download them; `fetch reference` / `--refresh` rebuild from NCBI.

## Ground truth for the fish-egg mixtures

`datasets/ZENODO4025362_fish_egg_mock/ground_truth/fish_egg_ground_truth.json` holds the paper's own Table 1 (proportion of eggs of each fish in each mock
community) and its supplementary Table S1 (which library is which community and primer set, and the false hits the authors list). Nothing in it was invented:
the proportions were typed from the open-access article text and checked by a script (each community sums to 1; species counts 4/9/7/4/10/17; 23 species in all),
and the library key and false-positive list were parsed from the supplement, not typed. The checker never sees this file while it works; it is only used to judge the result.

## Do not trust a number you cannot trace

Every number on screen comes from a file here. `python -m bioradar.adjudicate.runner verify` rewrites `COMPLIANCE.md` from those files, never from memory.

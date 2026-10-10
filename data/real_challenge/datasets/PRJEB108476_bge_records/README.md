# PRJEB108476: archive run records (metadata only)

- Public archive: PRJEB108476 (https://www.ebi.ac.uk/ena/browser/view/PRJEB108476), 12S metabarcoding of water samples
- File: `records/PRJEB108476_runs.tsv` (5119 run records, md5 `28a4f5635ead4b7e1a788c7ad62fc56d`), the archive's own response, saved unmodified
- Used for the **data guard** only: real records with future collection dates (2027/2028), sample IDs shared by several runs,
  missing GPS pins, and pins inside/outside the selected boundary. No reads from this project are analysed.
- Re-create: `python -m bioradar.adjudicate.fetch records`

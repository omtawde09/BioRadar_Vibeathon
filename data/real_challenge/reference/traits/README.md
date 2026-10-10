# Species trait tables (relative finder)

`bioradar/relatives/traits.py` reads every `*.csv` file in this folder. The relative finder uses
the rows in two ways:

1. **Evidence**: only for a factor that was actually observed for the sample or specimen. For an
   eDNA water sample, that means the country in `geo_loc_name` and the habitat, when the dataset
   title, design note or isolation source names it in words. Diet, karyotype, genome size and
   hormones cannot be read from a DNA fragment in water. They count as evidence only when a user
   enters a measurement taken from a physical specimen.
2. **Inferred profile**: for factors that were not observed, the profile shows what the nearest
   relatives are documented to have, weighted by relative weight and listed with their sources.
   This is what to expect if the hypothesis is right. It is never a measurement of the sample.

## CSV schema

One row is one documented value of one factor for one species.

| column       | required | meaning |
|--------------|----------|---------|
| `species`    | yes | Scientific name, e.g. `Labeo rohita`. Matching ignores case and extra spaces. |
| `factor`     | yes | One of the factor names below. |
| `value`      | yes | The value. Categorical factors may join several values with `;`. |
| `unit`       | no  | Unit of a numeric value, e.g. `cm`, `pg`. |
| `source`     | **yes** | Where the value comes from: a database, paper or curated file. |
| `source_url` | no  | Link to the source. For in-repo seed rows, the repository path. |
| `retrieved`  | no  | Date the value was taken from the source (`YYYY-MM-DD`). Leave it empty when the date is not known. |

**Every row must carry a source.** The loader rejects a row with an empty `source`, an unknown
factor, an empty value or a non-numeric value for a numeric factor. Rejected rows go into
`TraitTable.skipped`, with the reason.

## Factors

| factor           | type | values / unit | used as evidence when observed |
|------------------|------|---------------|--------------------------------|
| `habitat`        | categorical | `freshwater`, `brackish`, `marine` (`;`-joined) | yes. Also comes from sample metadata. |
| `country_native` | categorical | country names (`;`-joined) | yes. Comes from `geo_loc_name`. "Inconsistent" only means "not native there". |
| `diet`           | categorical | `herbivore`, `omnivore`, `carnivore`, `detritivore`, `planktivore` | only with a specimen observation |
| `trophic_level`  | numeric | dimensionless | only with a specimen observation (tolerance 0.5) |
| `karyotype_2n`   | numeric | diploid chromosome number | only with a specimen observation (tolerance 2) |
| `genome_size_pg` | numeric | pg (C-value) | only with a specimen observation (tolerance 20%) |
| `max_length_cm`  | numeric | cm | **never.** It appears in the inferred profile only. |
| `hormone`        | free text | free text | only with a specimen observation, and only as a text match |

The factor weights and tolerances are listed in `RULES` in `traits.py`, with a reason for each.
They are priors chosen by hand and documented there. They are not calibrated.

**Hormone:** no structured species-level source of hormone data exists. The channel is there so
that a user can supply rows, and it stays empty unless someone does. Without rows, the inferred
profile reports `no data in trait tables`.

## Files

### `bioradar_in_repo.csv`

The seed rows come only from data that is already in this repository:

- `data/species_traits.csv`: `max_size_cm` becomes `max_length_cm` (unit `cm`), and
  `trophic_level` stays `trophic_level`. That file records no original source or retrieval date,
  so `source` says so and `retrieved` is empty.
- `data/species_pool.csv` was checked as well. Its `india_status` column gives a species' status
  in India only, not its native range. Turning it into `country_native` would give a partial list,
  and a partial list would label a species as "not native" in countries where it is native, for
  example a fish native to both India and China. So no rows come from it.
- No habitat or diet values were inferred from species names or common names.

To add data from a documented source (for example a FishBase or Eschmeyer export), add a new CSV
file with the same columns and fill in `source`, `source_url` and `retrieved` on every row.

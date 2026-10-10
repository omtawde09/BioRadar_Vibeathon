"""BioRadar Layer 1 integration package.

Owns the boundary between the forked eDNA Snakemake pipeline and the rest of the
BioRadar stack:

* `contract`         -- the frozen schemas every team member codes against
* `fetch_data`       -- download public datasets and lay them out for the pipeline
* `build_reference`  -- assemble an India-curated COI reference from NCBI
* `train_classifier` -- train a QIIME2 classifier inside the pipeline container
* `normalize`        -- raw QIIME2 output -> contract CSVs
* `report`           -- normalized output -> readable biodiversity report
* `pipeline_runner` -- run the pipeline for one sample, from Python
* `chain_client`    -- hash artifacts and commit them to the custody ledger
* `time_machine`    -- diff two runs from the same site over time
* `mockgen`         -- realistic mock data so others can build before a real run
"""

__version__ = "0.1.0"

__all__ = [
    "build_reference",
    "chain_client",
    "contract",
    "fetch_data",
    "mockgen",
    "normalize",
    "pipeline_runner",
    "report",
    "time_machine",
    "train_classifier",
]

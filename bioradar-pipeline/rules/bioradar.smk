# BioRadar additions to the forked eDNA pipeline.
#
# Everything upstream stops at `finish`, which assembles final_results/. These
# two rules extend the DAG with the pieces the BioRadar stack needs:
#
#   normalize_taxonomy -> the frozen integration contract that Anshika, Tanay
#                         and Parth all read
#   emit_hash          -> the genesis record of the chain-of-custody ledger
#
# Both use `run:` blocks rather than `shell:` so they execute in Snakemake's own
# interpreter -- the bioradar package is stdlib-only, so no extra environment is
# needed, and there is no shell quoting to get wrong.
#
# config keys consumed here (all optional, with defaults):
#   bioradar_pkg_path  -- directory containing the `bioradar` package
#   sample_id          -- BioRadar sample code; defaults to the project name
#   pipeline_run_id    -- UUID for this run, supplied by pipeline_runner.py
#   backend_url        -- FastAPI backend base URL
#   chain_queue_dir    -- where unsent chain records are parked


def _bioradar_on_path():
    """Make the bioradar package importable from inside a Snakemake run block."""
    import sys

    pkg_path = config.get("bioradar_pkg_path", "")
    if pkg_path and pkg_path not in sys.path:
        sys.path.insert(0, pkg_path)


FAST_MODE = str(config.get("fast", "true")).lower() not in ("false", "0", "no")


rule collect_fast:
    """Assemble final_results/ without the upstream QC report chain.

    Upstream's `finish` rule *moves* qiime2/loci/asvs into final_results and only
    runs after the PDF is built. In fast mode there is no PDF, and moving is a
    trap anyway -- deleting final_results/ then destroys the DADA2 output and
    forces a full re-denoise. This copies instead.
    """
    input:
        "qiime2/loci/asvs/asv_count_tax_seqs_summary.csv",
    output:
        marker="final_results/.collected",
    run:
        import shutil
        from pathlib import Path

        destination = Path("final_results")
        destination.mkdir(parents=True, exist_ok=True)
        shutil.copytree("qiime2/loci/asvs", destination / "asvs", dirs_exist_ok=True)
        for extra in ("qiime2/loci/paired-end-demux.qzv", "config.yaml",
                      "manifest/manifest.tsv"):
            source = Path(extra)
            if source.is_file():
                shutil.copy2(source, destination / source.name)
        Path(output.marker).write_text("collected\n", encoding="utf-8")


rule normalize_taxonomy:
    """Translate raw QIIME2 output into the frozen BioRadar contract."""
    input:
        report=("final_results/.collected" if FAST_MODE
                else "final_results/final-report.pdf"),
    output:
        taxonomy="final_results/taxonomy_normalized.csv",
        summary="final_results/sample_summary.csv",
    run:
        _bioradar_on_path()
        from pathlib import Path

        from bioradar.normalize import normalize_results

        written = normalize_results(
            Path("final_results"),
            Path("final_results"),
            classification_method=config.get("classification_method", "sklearn"),
        )
        print(f"normalized taxonomy -> {written['taxonomy']}")
        print(f"sample summary      -> {written['summary']}")


rule emit_hash:
    """Hash the run's artifacts and commit them to the chain-of-custody ledger.

    Writes the record locally before attempting the POST, so a backend that is
    not up yet costs nothing -- `python -m bioradar.chain_client --flush` replays
    the queue once it is.
    """
    input:
        taxonomy="final_results/taxonomy_normalized.csv",
        summary="final_results/sample_summary.csv",
    output:
        hash_record="final_results/hash_record.json",
    run:
        _bioradar_on_path()
        import json
        from pathlib import Path

        from bioradar.chain_client import ChainClient, build_event

        artifacts = {
            "taxonomy": Path(input.taxonomy),
            "summary": Path(input.summary),
        }
        for name, relative in (
            ("biom", "final_results/asvs/asv-table.tsv"),
            ("report", "final_results/final-report.pdf"),
        ):
            candidate = Path(relative)
            if candidate.is_file():
                artifacts[name] = candidate

        event = build_event(
            sample_id=str(config.get("sample_id", config.get("project", "unknown"))),
            event_type="pipeline_complete",
            artifacts=artifacts,
            pipeline_run_id=config.get("pipeline_run_id"),
            extra={
                "classifier": config.get("classifier", ""),
                "fprimer": config.get("fprimer", ""),
                "rprimer": config.get("rprimer", ""),
                "project": config.get("project", ""),
            },
        )

        client = ChainClient(
            backend_url=config.get("backend_url", "http://localhost:8000"),
            queue_dir=Path(config.get("chain_queue_dir", "final_results/_chain_queue")),
        )
        result = client.record(event)

        Path(output.hash_record).write_text(
            json.dumps({"event": event, "delivery": result}, indent=2, sort_keys=True),
            encoding="utf-8",
        )

        if result["committed"]:
            print(f"chain record committed: {event['payload_hash'][:16]}...")
        else:
            print(f"chain record QUEUED (backend unreachable): {result['error']}")
            print(f"replay later with: python -m bioradar.chain_client --flush")

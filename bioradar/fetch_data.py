"""Fetch real eDNA datasets from ENA and prepare them for the BioRadar pipeline.

Public sequence archives hand you files named `SRR26872904_1.fastq.gz`. The
pipeline derives its sample id from the filename prefix before the first
underscore (`sample=${R1%%_*}` upstream), and expects the Illumina convention
`<SAMPLE>_S1_L001_R1_001.fastq.gz`. Feeding archive filenames straight in gives
every sample the id `SRR26872904` — or worse, silently collapses samples
together. This module does the download and the rename correctly.

It also harvests the geographic metadata that the archive already holds --
`lat_lon`, `geo_loc_name`, `collection_date` -- and writes it as a BioRadar
`sites.csv` and `samples.csv`. That closes the gap where nothing in the
FASTQ-to-taxonomy path carries coordinates, so the dashboard map gets real pins
from real samples instead of invented ones.

    # look before you leap: no download, just the manifest and metadata
    python -m bioradar.fetch_data --project PRJNA1040471 -o data/goa --dry-run

    # fetch it
    python -m bioradar.fetch_data --project PRJNA1040471 -o data/goa

    # then
    python -m bioradar.pipeline_runner data/goa/fastq --mode docker

Nothing here is BioRadar-specific to one dataset: point it at any ENA study of
paired amplicon runs and it will lay them out correctly.
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import sys
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any, Iterable

ENA_PORTAL = "https://www.ebi.ac.uk/ena/portal/api/search"


def _ssl_context() -> Any:
    """Build an SSL context that works behind TLS-inspecting antivirus/proxies.

    Several team laptops run software that re-signs HTTPS with a locally
    installed CA. That CA is in the OS trust store but not in certifi's bundle,
    so plain urllib fails with CERTIFICATE_VERIFY_FAILED while curl succeeds.
    `truststore` bridges Python to the OS store and fixes it.

    Verification is never disabled -- we are downloading files whose integrity we
    then hash into a chain of custody, and silently accepting any certificate
    would make that hash meaningless.
    """
    import ssl

    try:
        import truststore

        return truststore.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    except ImportError:
        pass

    try:
        import certifi

        return ssl.create_default_context(cafile=certifi.where())
    except ImportError:
        return ssl.create_default_context()


def _urlopen(url: str, timeout: int):
    """urlopen with the hardened context, and an actionable TLS error message."""
    import ssl

    try:
        return urllib.request.urlopen(url, timeout=timeout, context=_ssl_context())
    except urllib.error.URLError as exc:
        if isinstance(exc.reason, ssl.SSLCertVerificationError):
            raise FetchError(
                "TLS certificate verification failed. This usually means "
                "antivirus or a corporate proxy is intercepting HTTPS.\n"
                "  Fix: pip install truststore\n"
                "  (uses your OS certificate store; do not disable verification)"
            ) from exc
        raise

FIELDS = (
    "run_accession",
    "sample_accession",
    "sample_title",
    "scientific_name",
    "instrument_model",
    "library_strategy",
    "library_layout",
    "read_count",
    "base_count",
    "fastq_ftp",
    "fastq_bytes",
    "fastq_md5",
    "country",
    "location",
    "collection_date",
)

# "15.60592 N 73.72356 E" -> (15.60592, 73.72356)
_LATLON_RE = re.compile(
    r"([\d.]+)\s*([NS])\s+([\d.]+)\s*([EW])", re.IGNORECASE
)


class FetchError(RuntimeError):
    pass


def query_ena(project: str, fields: Iterable[str] = FIELDS) -> list[dict[str, str]]:
    """Ask ENA for every run in a study."""
    params = urllib.parse.urlencode(
        {
            "result": "read_run",
            "query": f'study_accession="{project}"',
            "fields": ",".join(fields),
            "format": "tsv",
            "limit": "0",
        }
    )
    try:
        with _urlopen(f"{ENA_PORTAL}?{params}", timeout=120) as response:
            payload = response.read().decode("utf-8")
    except FetchError:
        raise
    except Exception as exc:  # noqa: BLE001
        raise FetchError(f"ENA query failed for {project}: {exc}") from exc

    rows = list(csv.DictReader(payload.splitlines(), delimiter="\t"))
    if not rows:
        raise FetchError(
            f"{project} returned no runs. Check the accession, or the study may be "
            "under embargo."
        )
    return rows


NCBI_EUTILS = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
NCBI_FASTQ = "https://trace.ncbi.nlm.nih.gov/Traces/sra-reads-be/fastq"


def query_sra(project: str) -> list[dict[str, str]]:
    """Fall back to NCBI when ENA has not mirrored a study.

    ENA lags SRA by days to weeks for freshly released projects, and some are
    never mirrored. Rather than tell the user to install sra-toolkit, we read
    the run list from E-utilities and stream FASTQ from NCBI's own endpoint.

    Returns rows shaped like `query_ena` so the rest of the module does not care
    where the data came from. `fastq_ftp` is left empty -- the SRA download path
    is keyed off that.
    """
    search = urllib.parse.urlencode(
        {"db": "sra", "term": project, "retmax": "500", "retmode": "json"}
    )
    with _urlopen(f"{NCBI_EUTILS}/esearch.fcgi?{search}", timeout=120) as response:
        ids = json.loads(response.read().decode("utf-8"))["esearchresult"]["idlist"]
    if not ids:
        raise FetchError(f"{project} not found in SRA either")

    fetch = urllib.parse.urlencode(
        {"db": "sra", "id": ",".join(ids), "rettype": "xml"}
    )
    with _urlopen(f"{NCBI_EUTILS}/efetch.fcgi?{fetch}", timeout=180) as response:
        xml = response.read().decode("utf-8", errors="replace")

    rows: list[dict[str, str]] = []
    for package in re.split(r"(?=<EXPERIMENT_PACKAGE>)", xml):
        run = re.search(r'<RUN [^>]*accession="(\w+)"[^>]*total_spots="(\d+)"', package)
        if not run:
            continue

        def tag(name: str) -> str:
            match = re.search(
                rf"<TAG>{name}</TAG>\s*<VALUE>(.*?)</VALUE>", package, re.S
            )
            return match.group(1).strip() if match else ""

        title = re.search(r"<TITLE>([^<]{1,80})</TITLE>", package)
        layout = re.search(r"<LIBRARY_LAYOUT>\s*<(\w+)", package)
        rows.append(
            {
                "run_accession": run.group(1),
                "read_count": run.group(2),
                "sample_title": title.group(1).strip() if title else "",
                "library_layout": layout.group(1) if layout else "",
                "country": tag("geo_loc_name"),
                "location": tag("lat_lon"),
                "collection_date": tag("collection_date"),
                "scientific_name": tag("env_medium") or tag("isolation_source"),
                "instrument_model": "",
                "fastq_ftp": "",
                "fastq_bytes": "",
                "fastq_md5": "",
            }
        )
    return rows


def download_sra_run(
    run: str, sample_id: str, fastq_dir: Path, *, swap_mates: bool = False
) -> list[Path]:
    """Stream one SRA run and split interleaved reads into R1/R2.

    NCBI's endpoint returns both mates of a spot consecutively, sharing a spot
    id (`@SRR34723561.1 ... /1` then `@SRR34723561.1 ... /2`). We split on that
    rather than on a fixed alternation, so a run that turns out to be single-end
    produces one file instead of two silently-misaligned ones -- which DADA2
    would otherwise happily denoise into nonsense.
    """
    import gzip

    fastq_dir.mkdir(parents=True, exist_ok=True)
    # swap_mates writes the second mate as R1. Some libraries are sequenced in
    # the reverse orientation, so the reverse primer lands on R1; cutadapt runs
    # with --p-discard-untrimmed, which would throw those pairs away. Swapping
    # turns the dominant orientation into the expected one. Check with
    # `bioradar.fetch_data --inspect-primers` before using it.
    order = (2, 1) if swap_mates else (1, 2)
    targets = [
        fastq_dir / f"{sample_id}_S1_L001_R{mate}_001.fastq.gz" for mate in order
    ]
    if all(t.is_file() and t.stat().st_size > 0 for t in targets):
        print(f"    have {targets[0].name} (+ mate)")
        return targets

    url = f"{NCBI_FASTQ}?{urllib.parse.urlencode({'acc': run})}"
    print(f"    get  {run} -> {targets[0].name} (+ mate)", flush=True)

    handles = [gzip.open(t.with_suffix(t.suffix + ".part"), "wt") for t in targets]
    counts = [0, 0]
    try:
        with _urlopen(url, timeout=1800) as response:
            stream = gzip.GzipFile(fileobj=response)
            current_spot = None
            mate_index = 0
            record: list[str] = []
            for raw in stream:
                line = raw.decode("utf-8", errors="replace").rstrip("\n")
                record.append(line)
                if len(record) < 4:
                    continue

                spot = record[0].split()[0]
                if spot == current_spot:
                    mate_index = 1
                else:
                    current_spot = spot
                    mate_index = 0

                target = min(mate_index, 1)
                handles[target].write("\n".join(record) + "\n")
                counts[target] += 1
                record = []
    finally:
        for handle in handles:
            handle.close()

    written: list[Path] = []
    for index, target in enumerate(targets):
        part = target.with_suffix(target.suffix + ".part")
        if counts[index] == 0:
            part.unlink(missing_ok=True)
            continue
        part.replace(target)
        written.append(target)

    if len(written) != 2:
        for target in written:
            target.unlink(missing_ok=True)
        raise FetchError(
            f"{run} yielded {len(written)} read file(s), not a pair. "
            "The pipeline requires paired-end data."
        )
    print(f"      {counts[0]:,} read pairs")
    return written


def parse_lat_lon(value: str) -> tuple[float | None, float | None]:
    """Parse ENA's `lat_lon` string into signed decimal degrees."""
    match = _LATLON_RE.search(value or "")
    if not match:
        return None, None
    lat, lat_hemisphere, lon, lon_hemisphere = match.groups()
    latitude = float(lat) * (-1 if lat_hemisphere.upper() == "S" else 1)
    longitude = float(lon) * (-1 if lon_hemisphere.upper() == "W" else 1)
    return latitude, longitude


def site_id_from_location(location: str, fallback: str) -> str:
    """Derive a stable, underscore-free site id from a free-text place name.

    Underscores matter: the pipeline splits the sample id on the first one, so a
    site id containing an underscore would truncate every sample id derived from
    it.
    """
    text = (location or "").split(":")[-1].strip() or fallback
    slug = re.sub(r"[^A-Za-z0-9]+", "-", text).strip("-").upper()
    return slug or fallback.upper()


def filter_rows(rows: list[dict[str, str]], pattern: str) -> list[dict[str, str]]:
    """Keep only runs whose title/source matches `pattern` (case-insensitive).

    Multi-marker studies are common: PRJNA1296846 has 18S and COI runs side by
    side for the same three atolls. Feeding both into one pipeline run would
    trim with the wrong primers and silently discard most reads, so the marker
    must be chosen at download time.
    """
    regex = re.compile(pattern, re.IGNORECASE)
    kept = [
        r
        for r in rows
        if regex.search(
            " ".join(
                (
                    r.get("sample_title", ""),
                    r.get("scientific_name", ""),
                    r.get("run_accession", ""),
                )
            )
        )
    ]
    if not kept:
        raise FetchError(
            f"--match {pattern!r} matched none of the {len(rows)} runs. "
            "Check the sample titles with --dry-run and no --match."
        )
    return kept


def build_plan(
    rows: list[dict[str, str]],
    *,
    prefix: str = "BR",
    limit: int | None = None,
) -> list[dict[str, Any]]:
    """Decide the BioRadar sample id and target filenames for each run.

    Runs without exactly two FASTQ files are dropped: the pipeline is paired-end
    only, and a single-end run would fail deep inside DADA2 with a confusing
    error rather than here with a clear one.
    """
    plan: list[dict[str, Any]] = []
    per_site: dict[str, int] = {}

    def is_paired(row: dict[str, str]) -> bool:
        urls = row.get("fastq_ftp") or ""
        if urls:
            return len(urls.split(";")) == 2
        # SRA-sourced rows carry no URLs; trust the declared layout instead.
        return row.get("library_layout", "").upper() == "PAIRED"

    paired = [r for r in rows if is_paired(r)]

    # Archives often record only a country ("India") while the actual sampling
    # stations are distinguished by coordinates alone. Grouping by rounded
    # lat/lon (2 dp, roughly 1 km) recovers the real stations, so the dashboard
    # gets separate pins instead of every sample stacking on one point.
    coordinate_groups: dict[tuple[float, float], int] = {}
    for row in paired:
        latitude, longitude = parse_lat_lon(row.get("location", ""))
        if latitude is None:
            continue
        key = (round(latitude, 2), round(longitude, 2))
        coordinate_groups.setdefault(key, len(coordinate_groups) + 1)

    multiple_stations = len(coordinate_groups) > 1

    for row in paired:
        urls = [u for u in (row.get("fastq_ftp") or "").split(";") if u]

        run = row["run_accession"]
        latitude, longitude = parse_lat_lon(row.get("location", ""))
        base = site_id_from_location(
            row.get("country", "") or row.get("sample_title", ""), run
        )
        if multiple_stations and latitude is not None:
            station = coordinate_groups[(round(latitude, 2), round(longitude, 2))]
            site_id = f"{base}-ST{station:02d}"
        else:
            site_id = base
        per_site[site_id] = per_site.get(site_id, 0) + 1

        # Sample ids must not contain underscores -- see contract.sample_id_from_fastq.
        sample_id = f"{prefix}-{site_id}-{per_site[site_id]:02d}".replace("_", "-")

        sizes = [int(b) for b in (row.get("fastq_bytes") or "0;0").split(";") if b]
        md5s = [m for m in (row.get("fastq_md5") or "").split(";") if m]

        plan.append(
            {
                "run_accession": run,
                "sample_id": sample_id,
                "site_id": site_id,
                "latitude": latitude,
                "longitude": longitude,
                "collection_date": row.get("collection_date", ""),
                "country": row.get("country", ""),
                "scientific_name": row.get("scientific_name", ""),
                "instrument_model": row.get("instrument_model", ""),
                "read_count": int(row.get("read_count") or 0),
                "bytes": sum(sizes),
                "source": "ena" if urls else "sra",
                "downloads": [
                    {
                        "url": url if url.startswith("http") else f"https://{url}",
                        "target": f"{sample_id}_S1_L001_R{index + 1}_001.fastq.gz",
                        "md5": md5s[index] if index < len(md5s) else "",
                        "bytes": sizes[index] if index < len(sizes) else 0,
                    }
                    for index, url in enumerate(sorted(urls))
                ],
            }
        )

        if limit and len(plan) >= limit:
            break

    return plan


def download(url: str, destination: Path, expected_bytes: int = 0) -> Path:
    """Download one file, skipping it if a complete copy is already present."""
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.is_file() and (
        not expected_bytes or destination.stat().st_size == expected_bytes
    ):
        print(f"    have {destination.name}")
        return destination

    print(f"    get  {destination.name} ({expected_bytes / 1e6:.1f} MB)", flush=True)
    temporary = destination.with_suffix(destination.suffix + ".part")
    with _urlopen(url, timeout=300) as response, temporary.open("wb") as out:
        while chunk := response.read(1 << 20):
            out.write(chunk)
    temporary.replace(destination)
    return destination


def write_metadata(plan: list[dict[str, Any]], output: Path, project: str) -> None:
    """Emit BioRadar-shaped sites.csv and samples.csv from archive metadata."""
    sites: dict[str, dict[str, Any]] = {}
    for entry in plan:
        site = sites.setdefault(
            entry["site_id"],
            {
                "site_id": entry["site_id"],
                "site_name": entry["country"] or entry["site_id"],
                "state": "",
                "waterbody": "",
                "waterbody_type": entry["scientific_name"],
                "latitude": entry["latitude"],
                "longitude": entry["longitude"],
                "protected_status": "unknown",
                "notes": f"from {project}",
            },
        )
        if site["latitude"] is None and entry["latitude"] is not None:
            site["latitude"] = entry["latitude"]
            site["longitude"] = entry["longitude"]

    _write_csv(output / "sites.csv", list(sites.values()))
    _write_csv(
        output / "samples.csv",
        [
            {
                "sample_id": e["sample_id"],
                "site_id": e["site_id"],
                "run_accession": e["run_accession"],
                "latitude": e["latitude"],
                "longitude": e["longitude"],
                "collected_at": e["collection_date"],
                "instrument": e["instrument_model"],
                "read_count": e["read_count"],
                "source_project": project,
            }
            for e in plan
        ],
    )


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="bioradar.fetch_data",
        description="Download an ENA/SRA study and lay it out for the pipeline.",
    )
    parser.add_argument("--project", required=True, help="e.g. PRJNA1040471")
    parser.add_argument("-o", "--output", type=Path, required=True)
    parser.add_argument("--prefix", default="BR", help="sample id prefix")
    parser.add_argument("--limit", type=int, default=None, help="first N runs only")
    parser.add_argument(
        "--match",
        default=None,
        help="only runs whose title/source matches this regex, e.g. COI. "
        "Required for multi-marker studies -- markers must not be mixed.",
    )
    parser.add_argument(
        "--swap-mates",
        action="store_true",
        help="write mate 2 as R1 (for libraries sequenced in reverse orientation)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="write the manifest and metadata but download nothing",
    )
    args = parser.parse_args(argv)

    rows: list[dict[str, str]] = []
    source = "ena"
    try:
        rows = query_ena(args.project)
        if not any(r.get("fastq_ftp") for r in rows):
            raise FetchError("ENA has the study registered but no FASTQ mirrored")
    except FetchError as exc:
        print(f"ENA unavailable ({exc}); falling back to NCBI SRA", file=sys.stderr)
        try:
            rows = query_sra(args.project)
            source = "sra"
        except FetchError as inner:
            print(f"error: {inner}", file=sys.stderr)
            return 1
    print(f"source      : {source.upper()}")

    if args.match:
        try:
            rows = filter_rows(rows, args.match)
        except FetchError as exc:
            print(f"error: {exc}", file=sys.stderr)
            return 1
        print(f"filter      : {args.match} -> {len(rows)} runs")

    plan = build_plan(rows, prefix=args.prefix, limit=args.limit)
    dropped = len(rows) - len(plan)
    if not plan:
        print(
            f"error: {args.project} has no paired-end runs "
            f"({len(rows)} runs found). The pipeline requires paired reads.",
            file=sys.stderr,
        )
        return 1

    total = sum(e["bytes"] for e in plan)
    print(f"project     : {args.project}")
    print(f"paired runs : {len(plan)}" + (f"  ({dropped} non-paired skipped)" if dropped else ""))
    print(f"download    : {total / 1e9:.2f} GB")
    print(f"instrument  : {sorted({e['instrument_model'] for e in plan})}")
    print(f"sites       : {sorted({e['site_id'] for e in plan})}")
    print()

    args.output.mkdir(parents=True, exist_ok=True)
    (args.output / "manifest.json").write_text(
        json.dumps({"project": args.project, "runs": plan}, indent=2), encoding="utf-8"
    )
    write_metadata(plan, args.output, args.project)

    if args.dry_run:
        for entry in plan:
            print(f"  {entry['run_accession']} -> {entry['sample_id']}")
            for item in entry["downloads"]:
                print(f"      {item['target']}")
        print(f"\ndry run: manifest and metadata written to {args.output}")
        return 0

    fastq_dir = args.output / "fastq"
    for index, entry in enumerate(plan, 1):
        print(f"[{index}/{len(plan)}] {entry['run_accession']} -> {entry['sample_id']}")
        if entry.get("source") == "sra" or not entry["downloads"]:
            try:
                download_sra_run(
                    entry["run_accession"],
                    entry["sample_id"],
                    fastq_dir,
                    swap_mates=args.swap_mates,
                )
            except FetchError as exc:
                print(f"    skipped: {exc}", file=sys.stderr)
            continue
        for item in entry["downloads"]:
            download(item["url"], fastq_dir / item["target"], item["bytes"])

    print(f"\nready: {fastq_dir}")
    print(f"run it: python -m bioradar.pipeline_runner {fastq_dir} --mode docker")
    return 0


if __name__ == "__main__":
    sys.exit(main())

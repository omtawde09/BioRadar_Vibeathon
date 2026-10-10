#!/usr/bin/env bash
#
# BioRadar integration check.
#
# Run this after every commit. It verifies the boundaries between team members --
# the places where hackathons actually break -- rather than any one component's
# internals.
#
#   ./ci/check_integration.sh          full check
#   ./ci/check_integration.sh --fast   skip anything needing Docker
#
# Exit codes: 0 all good, 1 a contract is broken.

set -uo pipefail

cd "$(dirname "$0")/.." || exit 1

FAST=0
[[ "${1:-}" == "--fast" ]] && FAST=1

# Repo-relative scratch space. Deliberately not /tmp: half the team is on
# Windows, where Python resolves /tmp to C:\tmp while Git Bash means something
# else entirely, and the checks silently read each other's stale output.
WORK=".ci-work"
rm -rf "$WORK"
mkdir -p "$WORK/out"

PYTHON="${PYTHON:-python}"
PASS=0
FAIL=0
SKIP=0

green() { printf '\033[32m%s\033[0m\n' "$1"; }
red()   { printf '\033[31m%s\033[0m\n' "$1"; }
grey()  { printf '\033[90m%s\033[0m\n' "$1"; }

check() {
    local name="$1"; shift
    if "$@" >$WORK/check.log 2>&1; then
        green "  PASS  $name"
        PASS=$((PASS + 1))
    else
        red   "  FAIL  $name"
        sed 's/^/          /' $WORK/check.log | tail -15
        FAIL=$((FAIL + 1))
    fi
}

skip() {
    grey "  SKIP  $1 ($2)"
    SKIP=$((SKIP + 1))
}

echo
echo "BioRadar integration check"
echo "=========================="

# ---------------------------------------------------------------------------
echo
echo "1. Package imports"
check "bioradar package imports"        $PYTHON -c "import bioradar, bioradar.contract, bioradar.normalize, bioradar.chain_client, bioradar.time_machine, bioradar.mockgen, bioradar.pipeline_runner"
check "no third-party deps in contract" $PYTHON -c "
import ast, sys
tree = ast.parse(open('bioradar/normalize.py').read())
allowed = {'argparse','csv','io','re','sys','zipfile','pathlib','typing','bioradar','__future__'}
for node in ast.walk(tree):
    if isinstance(node, ast.Import):
        mods = [a.name.split('.')[0] for a in node.names]
    elif isinstance(node, ast.ImportFrom):
        mods = [(node.module or '').split('.')[0]]
    else:
        continue
    for m in mods:
        if m and m not in allowed:
            sys.exit(f'normalize.py imports {m}; it must stay stdlib-only so the backend can import it')
"

# ---------------------------------------------------------------------------
echo
echo "2. Unit and contract tests"
check "pytest suite" $PYTHON -m pytest tests/ -q

# ---------------------------------------------------------------------------
echo
echo "3. Contract 1: pipeline -> Anshika / Tanay / Parth"
check "normalizer runs on real pipeline output" \
    $PYTHON -m bioradar.normalize testing_data/final_results.zip -o $WORK/out

check "normalized output matches the frozen schema" $PYTHON -c "
import csv, sys
from bioradar.contract import TAXONOMY_COLUMNS, validate_taxonomy_rows
rows = list(csv.DictReader(open('$WORK/out/taxonomy_normalized.csv', newline='', encoding='utf-8')))
if list(rows[0]) != list(TAXONOMY_COLUMNS):
    sys.exit('column drift: taxonomy_normalized.csv no longer matches contract.TAXONOMY_COLUMNS')
validate_taxonomy_rows(rows)
print(f'{len(rows)} detections validated')
"

# ---------------------------------------------------------------------------
echo
echo "4. Contract 2: mock data is interchangeable with real output"
check "mock generator runs" $PYTHON -m bioradar.mockgen -o $WORK/out/mock --rounds 2

check "mock and real share a schema" $PYTHON -c "
import csv, sys
real = list(csv.DictReader(open('$WORK/out/taxonomy_normalized.csv', newline='', encoding='utf-8')))
mock = list(csv.DictReader(open('$WORK/out/mock/taxonomy_normalized.csv', newline='', encoding='utf-8')))
if list(real[0]) != list(mock[0]):
    sys.exit('mock data has drifted from real pipeline output; downstream code will break on the switch')
print('mock and real columns identical')
"

# ---------------------------------------------------------------------------
echo
echo "5. Contract 3: chain of custody"
check "hash -> POST -> verify round trip" $PYTHON -c "
import json, urllib.request
from pathlib import Path
from bioradar.chain_client import ChainClient, build_event
from integration.mock_backend import MockBackend, reset

reset()
artifact = Path('$WORK/out/taxonomy_normalized.csv')
with MockBackend(port=0) as server:
    client = ChainClient(server.url, Path('$WORK/out/queue'))
    for event_type in ('pipeline_complete', 'flagging_complete', 'cbi_computed'):
        result = client.record(build_event('CI-SAMPLE', event_type, {'taxonomy': artifact}))
        assert result['committed'], result
    body = json.loads(urllib.request.urlopen(server.url + '/api/v1/chain/verify/CI-SAMPLE').read())
assert body['chain_intact'], body
assert body['event_count'] == 3, body
print('chain verified across 3 events')
"

check "offline pipeline still succeeds (queue fallback)" $PYTHON -c "
from pathlib import Path
from bioradar.chain_client import ChainClient, build_event
client = ChainClient('http://127.0.0.1:9', Path('$WORK/out/offline_queue'))
result = client.record(build_event('CI-OFFLINE', 'pipeline_complete',
                                   {'taxonomy': Path('$WORK/out/taxonomy_normalized.csv')}))
assert result['committed'] is False
assert Path(result['queued_at']).is_file(), 'record was lost when the backend was down'
print('offline record queued, nothing lost')
"

# ---------------------------------------------------------------------------
echo
echo "6. Contract 4: Time Machine -> Ishwar's Trends view"
check "temporal diff produces a usable shape" $PYTHON -c "
import json, sys
from bioradar.time_machine import compare_files
from bioradar.contract import TIME_MACHINE_FIELDS
diff = compare_files(
    '$WORK/out/mock/by_sample/BR-2026-GOA-MANDOVI-R01.csv',
    '$WORK/out/mock/by_sample/BR-2026-GOA-MANDOVI-R02.csv',
    site_id='GOA-MANDOVI',
)
missing = set(TIME_MACHINE_FIELDS) - set(diff)
if missing:
    sys.exit(f'time machine output missing fields: {sorted(missing)}')
print('diff fields complete; summary =', json.dumps(diff['summary']['turnover']))
"

# ---------------------------------------------------------------------------
echo
echo "7. Pre-flight input checks"
check "preflight passes clean test data" $PYTHON -c "
from pathlib import Path
from bioradar import preflight
from bioradar.pipeline_runner import discover_pairs
result = preflight.run(discover_pairs(Path('testing_data/fastq_data')))
assert result.ok, result.render()
print('bundled test data passes preflight')
"

check "preflight rejects flat quality scores" $PYTHON -c "
import gzip
from pathlib import Path
from bioradar import preflight
tmp = Path('$WORK/flatq'); tmp.mkdir(parents=True, exist_ok=True)
record = chr(10).join(['@r', 'ACGTACGTAC', '+', '??????????']) + chr(10)
for mate in (1, 2):
    with gzip.open(tmp / ('x_S1_L001_R%d_001.fastq.gz' % mate), 'wt') as fh:
        fh.write(record * 100)
result = preflight.run([tmp / 'x_S1_L001_R1_001.fastq.gz'])
assert not result.ok, 'flat-quality data was not rejected'
print('flat-quality data correctly rejected')
"

# ---------------------------------------------------------------------------
echo
echo "8. Container compatibility (Python 3.8)"
# The web app imports the whole package INSIDE the pipeline image, which ships
# Python 3.8. Subscripted builtins outside annotations (`Callable[[dict[...]]]`
# as a runtime assignment) raise TypeError there but are fine on the dev
# machine's 3.10+. This catches that class of regression.
if command -v docker >/dev/null 2>&1 && docker info >/dev/null 2>&1 && [[ $FAST -eq 0 ]]; then
    # env MSYS_NO_PATHCONV=1: Git Bash rewrites the /bioradar paths in the -v
    # and -e arguments into Windows paths, and the import then fails for the
    # wrong reason.
    check "package imports under the container Python" \
        env MSYS_NO_PATHCONV=1 docker run --rm \
        -v "$(pwd):/bioradar" -e PYTHONPATH=/bioradar -w /bioradar \
        --entrypoint python "${BIORADAR_PIPELINE_IMAGE:-ghcr.io/omtawde09/bioradar-pipeline:v1.0}" -c "
import bioradar.contract, bioradar.normalize, bioradar.chain_client
import bioradar.time_machine, bioradar.mockgen, bioradar.pipeline_runner
import bioradar.preflight, bioradar.report, bioradar.webapp
print('all modules import on Python 3.8')
"
else
    skip "package imports under the container Python" "needs docker (or --fast given)"
fi

# ---------------------------------------------------------------------------
echo
echo "9. Pipeline definition"
if [[ $FAST -eq 1 ]]; then
    skip "Snakemake DAG dry-run" "--fast"
elif ! command -v docker >/dev/null 2>&1; then
    skip "Snakemake DAG dry-run" "docker not on PATH"
elif ! docker info >/dev/null 2>&1; then
    skip "Snakemake DAG dry-run" "docker daemon not running"
else
    check "pipeline DAG is valid (dry run)" $PYTHON -m bioradar.pipeline_runner \
        testing_data/fastq_data --mode docker --dry-run --run-id "ci-$(date +%s)"
fi

# ---------------------------------------------------------------------------
echo
echo "10. Downstream contracts (activate as components land)"

# These stay skipped until the owning component exists, then start enforcing
# automatically. Nobody has to remember to switch them on.
if $PYTHON -c "import bioradar.flagging" 2>/dev/null; then
    check "pipeline output -> flagging engine" $PYTHON -c "
import csv
from bioradar.flagging import flagging_engine
rows = list(csv.DictReader(open('$WORK/out/taxonomy_normalized.csv', newline='', encoding='utf-8')))
alerts = flagging_engine.run(rows)
assert 'alerts' in alerts and 'summary' in alerts, 'alerts JSON missing required keys'
print(f\"{len(alerts['alerts'])} alerts generated from real pipeline output\")
"
else
    skip "pipeline output -> flagging engine" "bioradar.flagging not implemented yet (Anshika)"
fi

if $PYTHON -c "import bioradar.analytics" 2>/dev/null; then
    check "flagging output -> analytics / CBI" $PYTHON -c "
import json
from bioradar.analytics import cbi
alerts = json.load(open('$WORK/out/mock/alerts.example.json', encoding='utf-8'))
score = cbi.compute(alerts)
assert 0 <= score['cbi'] <= 100, f\"CBI out of range: {score['cbi']}\"
print(f\"CBI = {score['cbi']}\")
"
else
    skip "flagging output -> analytics / CBI" "bioradar.analytics not implemented yet (Tanay)"
fi

# ---------------------------------------------------------------------------
echo
echo "11. Export formats"
check "Darwin Core Archive is structurally valid" $PYTHON -c "
import csv, io, zipfile
from bioradar import exports
from bioradar.report import analyse
rows = list(csv.DictReader(open('$WORK/out/taxonomy_normalized.csv', newline='', encoding='utf-8')))
result = analyse(rows)
archive = zipfile.ZipFile(io.BytesIO(exports.darwin_core_archive(rows, result, [], meta={'run_id':'ci'})))
missing = {'occurrence.txt','dna.txt','meta.xml','eml.xml'} - set(archive.namelist())
assert not missing, f'DwC-A is missing {missing}'
lines = archive.read('occurrence.txt').decode('utf-8').rstrip(chr(10)).split(chr(10))
widths = {len(l.split(chr(9))) for l in lines}
assert widths == {len(exports.OCCURRENCE_FIELDS)}, f'ragged TSV: {widths}'
core = {l.split(chr(9))[0] for l in lines[1:]}
ext = {l.split(chr(9))[0] for l in archive.read('dna.txt').decode('utf-8').rstrip(chr(10)).split(chr(10))[1:]}
assert core == ext, 'the DNA extension does not join to the occurrence core'
print(f'{len(core)} occurrences, extension joined')
"

check "printable report references nothing external" $PYTHON -c "
import csv, re, sys
from bioradar import exports
from bioradar.report import analyse
rows = list(csv.DictReader(open('$WORK/out/taxonomy_normalized.csv', newline='', encoding='utf-8')))
html = exports.printable_report(analyse(rows), {'title': 'CI'}).decode('utf-8')
for pattern in ('<script', '<link', 'src=', '@import'):
    if pattern in html:
        sys.exit(f'the report pulls in {pattern!r}; it must survive being emailed and opened offline')
print('self-contained')
"

# ---------------------------------------------------------------------------
echo
echo "12. Frontend"
check "every static asset the page loads exists" $PYTHON -c "
import re, sys
from pathlib import Path
static = Path('bioradar/webapp_static')
html = (static / 'index.html').read_text(encoding='utf-8')
refs = re.findall(r'(?:src|href)=\"/static/([^\"]+)\"', html)
missing = [r for r in refs if not (static / r).is_file()]
if missing:
    sys.exit(f'index.html references files that do not exist: {missing}')
print(f'{len(refs)} assets, all present')
"

check "no external asset is loaded at page load" $PYTHON -c "
import re, sys
from pathlib import Path
# The app is served from inside the pipeline image and demonstrated on
# conference wifi. A CDN font or script would be a blank page at the worst
# possible moment. Map *tiles* are fetched at runtime and are exempt --
# they degrade to a grey square, not a broken app.
html = Path('bioradar/webapp_static/index.html').read_text(encoding='utf-8')
external = re.findall(r'(?:src|href)=\"(https?://[^\"]+)\"', html)
if external:
    sys.exit(f'index.html loads external resources: {external}')
print('no external <script> or <link>')
"

check "the design system defines exactly five shadow tokens" $PYTHON -c "
import re, sys
from pathlib import Path
# Section 7 of the UI guide: five, no more, no less. Inventing a sixth
# mid-development is the single most reliable way to make neumorphism look
# improvised, so the count is enforced rather than trusted.
css = Path('bioradar/webapp_static/app.css').read_text(encoding='utf-8')
tokens = sorted(set(re.findall(r'--(neu-[a-z-]+):', css)))
expected = ['neu-input', 'neu-pressed', 'neu-raised', 'neu-raised-lg', 'neu-raised-sm']
if tokens != expected:
    sys.exit(f'shadow tokens drifted: {tokens} != {expected}')
print('5 shadow tokens')
"

check "no global selector matches the document root" $PYTHON -c "
import re, sys
from pathlib import Path
# The bug this prevents cost the whole app. <body> carries data-lang as the
# *active* language; the language switcher bound its click handler with
# document.querySelectorAll('[data-lang]'), which also matched <body>. Every
# click anywhere in the app then bubbled into that handler, which rebuilt the
# shell, which bound another body handler -- so clicks doubled on every
# interaction until the page stopped responding. Nothing about it was visible
# in review.
static = Path('bioradar/webapp_static')
html = (static / 'index.html').read_text(encoding='utf-8')
root_attrs = set()
for tag in ('html', 'body'):
    match = re.search(r'<' + tag + r'\b([^>]*)>', html)
    if match:
        root_attrs.update(re.findall(r'(data-[a-z-]+)\s*=', match.group(1)))
offenders = []
for name in ('app.js', 'ui.js', 'charts.js', 'mapkit.js', 'i18n.js', 'registry.js'):
    source = (static / name).read_text(encoding='utf-8')
    for attr in re.findall(r'document\.querySelectorAll\(\s*[\"\x27]\[(data-[a-z-]+)[\]=]', source):
        if attr in root_attrs:
            offenders.append(f'{name}: document-wide [{attr}] also matches <body>/<html>')
if offenders:
    sys.exit(chr(10).join(offenders))
print(f'no document-wide selector collides with {sorted(root_attrs) or \"the root elements\"}')
"

check "animations cannot strand the UI on a wrong value" $PYTHON -c "
import re, sys
from pathlib import Path
# requestAnimationFrame does not fire in a backgrounded tab and does not fire
# at all in some embedded browser panes. A count-up that stalls does not just
# lose an animation -- it leaves a KPI tile reading 0 when the answer is 16,
# and a bar frozen at 0%. Every helper that animates toward a final value must
# therefore reach that value without depending on frames.
source = Path('bioradar/webapp_static/ui.js').read_text(encoding='utf-8')
def body(text, start):
    # Up to the next top-level declaration, whichever comes first.
    ends = [text.find(marker, start + 1)
            for marker in (chr(10) + '  function ', chr(10) + '  global.')]
    ends = [e for e in ends if e != -1]
    return text[start:min(ends)] if ends else text[start:]
for name in ('function countUp', 'function growBars'):
    if 'setTimeout' not in body(source, source.index(name)):
        sys.exit(f'{name} animates without a non-rAF backstop; a stalled frame '
                 'loop would leave the wrong number on screen')
app = Path('bioradar/webapp_static/app.js').read_text(encoding='utf-8')
block = app[app.index('function scheduleRender'):]
block = block[:block.index(chr(10) + '  }')]
if 'setTimeout' not in block:
    sys.exit('scheduleRender queues on rAF alone; a missed frame latches the '
             'queued flag and the UI never updates again')
print('count-up, bars and the render scheduler all settle without rAF')
"

check "no hardcoded hex colour outside the token block" $PYTHON -c "
import re, sys
from pathlib import Path
css = Path('bioradar/webapp_static/app.css').read_text(encoding='utf-8')
# Everything after the [data-theme=\"light\"] block must use var(--token).
body = css.split('/* ── Base', 1)[-1]
strays = [h for h in re.findall(r'#[0-9a-fA-F]{3,8}\b', body)
          if h.lower() not in {'#fff', '#ffffff', '#000', '#04231b', '#241a04',
                               '#131a1a', '#06202e', '#2b0d1f', '#1a1a1a', '#ccc'}]
if strays:
    sys.exit(f'hardcoded colours outside the token block: {sorted(set(strays))}')
print('colours come from tokens')
"

# ---------------------------------------------------------------------------
echo
echo "13. Reference data"
check "sites.csv has coordinates for every site" $PYTHON -c "
import csv, sys
rows = list(csv.DictReader(open('data/sites.csv', newline='', encoding='utf-8')))
for row in rows:
    lat, lon = float(row['latitude']), float(row['longitude'])
    if not (6 <= lat <= 38) or not (67 <= lon <= 98):
        sys.exit(f\"{row['site_id']} is outside India's bounding box: {lat},{lon}\")
print(f'{len(rows)} sites, all within India')
"

echo
echo "=========================="
printf 'passed %d, failed %d, skipped %d\n' "$PASS" "$FAIL" "$SKIP"
echo

if [[ $FAIL -gt 0 ]]; then
    red "INTEGRATION BROKEN -- do not merge"
    exit 1
fi
green "integration OK"
exit 0

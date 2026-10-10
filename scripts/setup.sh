#!/usr/bin/env bash
#
# BioRadar one-command setup.
#
# Brings a fresh machine -- a teammate's laptop, a demo machine, a judge's
# machine -- to the point where the pipeline runs and the stack starts.
#
#   ./scripts/setup.sh              full setup
#   ./scripts/setup.sh --no-pull    skip the 11.7 GB image pull
#
# Safe to re-run: every step checks before doing anything.

set -uo pipefail
cd "$(dirname "$0")/.." || exit 1

IMAGE="${BIORADAR_PIPELINE_IMAGE:-ghcr.io/omtawde09/bioradar-pipeline:v1.0}"
PYTHON="${PYTHON:-python}"
PULL=1
[[ "${1:-}" == "--no-pull" ]] && PULL=0

STEP=0
ok()   { printf '  \033[32mOK\033[0m    %s\n' "$1"; }
warn() { printf '  \033[33mWARN\033[0m  %s\n' "$1"; }
die()  { printf '  \033[31mFAIL\033[0m  %s\n' "$1"; exit 1; }
step() { STEP=$((STEP+1)); printf '\n%d. %s\n' "$STEP" "$1"; }

echo "BioRadar setup"
echo "=============="

# ---------------------------------------------------------------------------
step "Prerequisites"
command -v docker >/dev/null 2>&1 || die "docker not found. Install Docker Desktop."
docker info >/dev/null 2>&1 || die "docker daemon not running. Start Docker Desktop."
ok "docker $(docker version --format '{{.Server.Version}}' 2>/dev/null)"

$PYTHON --version >/dev/null 2>&1 || die "python not found"
ok "$($PYTHON --version)"

# truststore matters on machines with TLS-inspecting antivirus, which silently
# breaks every HTTPS download from Python while curl keeps working.
if $PYTHON -c "import truststore" 2>/dev/null; then
    ok "truststore installed (archive downloads will work behind AV proxies)"
else
    warn "truststore not installed -- run: pip install truststore"
fi

# ---------------------------------------------------------------------------
step "Pipeline image"
if docker image inspect "$IMAGE" >/dev/null 2>&1; then
    ok "$IMAGE present ($(docker image inspect "$IMAGE" --format '{{.Size}}' | awk '{printf "%.1f GB", $1/1e9}'))"
elif [[ $PULL -eq 1 ]]; then
    echo "     pulling $IMAGE (11.7 GB, this takes a while)..."
    docker pull "$IMAGE" || die "pull failed"
    ok "pulled $IMAGE"
else
    warn "$IMAGE missing and --no-pull given"
fi

# ---------------------------------------------------------------------------
step "Classifiers"
DB="bioradar-pipeline/database/qiime2-qza"
if compgen -G "$DB/*.qza" >/dev/null; then
    ok "$(ls "$DB"/*.qza | wc -l) classifier(s) present"
else
    echo "     extracting classifiers from the image (22 MB)..."
    mkdir -p "$DB"
    CID=$(docker create "$IMAGE") || die "could not create container"
    docker cp "$CID:/opt/bioradar/classifiers/." "$DB/" \
        && ok "classifiers extracted" || warn "extraction failed -- copy from a teammate"
    docker rm -f "$CID" >/dev/null 2>&1
fi

# ---------------------------------------------------------------------------
step "Environment file"
if [[ -f .env ]]; then
    ok ".env exists"
else
    SECRET=$($PYTHON -c "import secrets; print(secrets.token_urlsafe(32))")
    sed "s|^JWT_SECRET=.*|JWT_SECRET=$SECRET|" .env.example > .env
    ok ".env created with a generated JWT_SECRET"
fi

# ---------------------------------------------------------------------------
step "Mock data (unblocks everyone who is not running the pipeline)"
if [[ -f mock/taxonomy_normalized.csv ]]; then
    ok "mock data present"
else
    $PYTHON -m bioradar.mockgen -o mock --rounds 3 >/dev/null 2>&1 \
        && ok "mock data generated" || warn "mock generation failed"
fi

# ---------------------------------------------------------------------------
step "Database"
if docker compose ps db --format '{{.State}}' 2>/dev/null | grep -q running; then
    ok "PostGIS already running"
else
    docker compose up -d db >/dev/null 2>&1 && ok "PostGIS started" \
        || warn "could not start PostGIS (port 5432 in use?)"
fi

# ---------------------------------------------------------------------------
step "Verification"
if ./ci/check_integration.sh --fast >/tmp/bioradar_setup_ci.log 2>&1; then
    ok "integration checks pass"
else
    warn "integration checks failed -- see /tmp/bioradar_setup_ci.log"
fi

# ---------------------------------------------------------------------------
cat <<'EOF'

Setup complete.

Next:
  python -m bioradar.pipeline_runner testing_data/fastq_data --mode docker
      run the pipeline on the bundled test data (~7 min)

  python -m bioradar.fetch_data --project PRJNA1296846 -o data/india_lakshadweep \
      --prefix BR-LKD --match COI --swap-mates
      download the Indian Lakshadweep COI dataset

  docs/TESTING.md
      how to verify each layer

EOF

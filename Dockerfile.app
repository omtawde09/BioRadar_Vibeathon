# BioRadar control panel — a GUI-runnable image.
#
# The upstream eDNA image has ENTRYPOINT ["./app.py"], which starts the old
# Flask GUI. Docker Desktop's Run dialog cannot override an entrypoint, so the
# stock image cannot launch BioRadar by point-and-click. This layer changes only
# the entrypoint and working directory — no packages, no code copied — so it
# builds in seconds and adds nothing to the 11.7 GB base.
#
# The repo itself is bind-mounted at run time rather than copied in, so runs and
# reports land on the host and survive the container.
#
#   docker build -f Dockerfile.app -t bioradar/app:latest .
#
# Then in Docker Desktop: Images → bioradar/app → Run, map port 8080, and mount
# the repo at /bioradar. See docs/RUNNING.md §0.

FROM ghcr.io/omtawde09/bioradar-pipeline:v1.0

LABEL org.opencontainers.image.title="BioRadar control panel"
LABEL org.opencontainers.image.description="Run the eDNA pipeline from a browser"

WORKDIR /bioradar

ENV PYTHONPATH=/bioradar \
    PYTHONUNBUFFERED=1

EXPOSE 8080

# Overrides the upstream Flask entrypoint.
ENTRYPOINT ["python", "-u", "-m", "bioradar.webapp", "--host", "0.0.0.0", "--port", "8080"]

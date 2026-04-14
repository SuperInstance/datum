FROM python:3.12-slim

# ── Metadata ─────────────────────────────────────────────────────────────────
LABEL maintainer="SuperInstance Fleet"
LABEL description="Datum — Self-bootstrapping fleet Quartermaster runtime"
LABEL org.opencontainers.image.source="https://github.com/SuperInstance/datum-runtime"
LABEL org.opencontainers.image.title="datum-runtime"
LABEL org.opencontainers.image.description="Datum Quartermaster: fleet audit, analysis, and hygiene"

# ── Install system dependencies ─────────────────────────────────────────────
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        git \
        curl \
    && rm -rf /var/lib/apt/lists/*

# ── Create non-root user ─────────────────────────────────────────────────────
RUN groupadd --gid 1000 datum && \
    useradd --create-home --home-dir /home/datum --shell /bin/bash \
        --uid 1000 --gid datum datum

USER datum
WORKDIR /home/datum

# ── Copy package source ──────────────────────────────────────────────────────
COPY --chown=datum:datum . /home/datum/datum-runtime/

# ── Install the package ─────────────────────────────────────────────────────
RUN cd /home/datum/datum-runtime && \
    pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -e .

# ── Boot: initialize the workshop ───────────────────────────────────────────
RUN datum-rt boot --workshop /home/datum/workshop --non-interactive || true

# ── Environment ──────────────────────────────────────────────────────────────
ENV DATUM_WORKSHOP=/home/datum/workshop
ENV KEEPER_URL=http://keeper:7742
ENV PATH="/home/datum/datum-runtime/bin:${PATH}"
ENV PYTHONUNBUFFERED=1

# ── Health check ─────────────────────────────────────────────────────────────
HEALTHCHECK --interval=60s --timeout=10s --start-period=10s --retries=3 \
    CMD python -c "from datum_runtime import __version__; print('ok')" || exit 1

# ── Default command ──────────────────────────────────────────────────────────
CMD ["datum-rt", "status"]

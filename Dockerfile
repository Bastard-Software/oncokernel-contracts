# Development / CI image.
#
# This library is NOT deployed as a container — it is a Python package that gets
# installed into the images of the services that consume it (ingestion-engine,
# copilot-ai, dashboard). This image exists only to run the test suite in a
# reproducible environment, on a machine that may not have a suitable Python or
# any particular package manager.
#
#   docker build -t oncokernel-contracts .
#   docker run --rm oncokernel-contracts                    # test suite
#   docker run --rm oncokernel-contracts ruff check src tests
#   docker run --rm oncokernel-contracts python -m oncokernel_contracts.schemas --check

FROM python:3.12-slim

WORKDIR /app

# Dependency metadata first so the install layer caches across source edits.
COPY pyproject.toml README.md ./
COPY src/ ./src/

RUN python -m pip install --no-cache-dir --upgrade pip \
    && python -m pip install --no-cache-dir -e ".[dev]"

COPY tests/ ./tests/
COPY schemas/ ./schemas/

CMD ["python", "-m", "pytest", "-q"]

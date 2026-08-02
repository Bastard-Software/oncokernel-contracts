# oncokernel-contracts

Shared Pydantic v2 data contracts for the OncoKernel platform. Every payload that crosses a service boundary is defined here, together with the validators that reject invalid payloads.

Dependencies: Pydantic v2 and the standard library. No I/O, no business logic.

**Reference documentation:** [`docs/`](docs/index.md)

---

## Requirements

- Python ≥ 3.12
- [uv](https://docs.astral.sh/uv/getting-started/installation/) — the supported toolchain

## Installation

### uv

```bash
git clone https://github.com/Bastard-Software/oncokernel-contracts.git
```

```bash
cd oncokernel-contracts && uv sync
```

`uv sync` creates `.venv`, installs the project and its dev dependencies from `uv.lock`, and needs no pre-existing Python — uv fetches an interpreter if none matches.

### pip

Fallback for an environment without uv. Windows:

```bash
python -m venv .venv && .venv\Scripts\python -m pip install -e ".[dev]"
```

Linux / macOS:

```bash
python -m venv .venv && .venv/bin/python -m pip install -e ".[dev]"
```

Substitute `.venv\Scripts\python` (or `.venv/bin/python`) for `uv run python` in every command below.

### Docker

```bash
docker build -t oncokernel-contracts .
```

Dev/CI image only — this library is not deployed as a container. See the header of `Dockerfile`.

## Running the tests

```bash
uv run pytest
```

```bash
docker run --rm oncokernel-contracts
```

## Lint and format

```bash
uv run ruff check src tests
```

```bash
uv run ruff format --check src tests
```

## Regenerating JSON Schemas

Schemas in `schemas/` are generated from the models and committed. CI verifies them.

```bash
uv run python -m oncokernel_contracts.schemas
```

```bash
uv run python -m oncokernel_contracts.schemas --check
```

`--check` exits non-zero if a committed schema no longer matches its model. Regenerate and commit `schemas/` whenever a model changes.

## Reproducing CI locally

Runs the same steps as the `check` job, in the same order:

```bash
uv sync --locked && uv run ruff check src tests && uv run ruff format --check src tests && uv run pytest && uv run python -m oncokernel_contracts.schemas --check
```

---

## Using the library

### As a dependency

```bash
uv add "oncokernel-contracts @ git+https://github.com/Bastard-Software/oncokernel-contracts@v0.1.0"
```

```bash
pip install "oncokernel-contracts @ git+https://github.com/Bastard-Software/oncokernel-contracts@v0.1.0"
```

Pin a tag.

### Example

```python
from uuid import uuid4

from oncokernel_contracts import project
from oncokernel_contracts.fixtures import tumor_normal_genome_wide

profile = tumor_normal_genome_wide()             # GenomicProfile   (on-premise)
crossed = project(profile, sample_uuid=uuid4())  # PseudonymizedProfile (egress)

crossed.model_dump(mode="json")
```

`project()` drops `sample_id`, `vcf_path` and `germline_variants`. See [Projection](docs/api-reference.md#projection).

### Fixtures

| Function | `sample_mode` | Territory | `validation_status` |
|---|---|---|---|
| `tumor_normal_genome_wide()` | `tumor_normal` | `genome_wide` | `validated` |
| `tumor_only_genome_wide()` | `tumor_only` | `genome_wide` | `validated` |
| `tumor_normal_panel()` | `tumor_normal` | `panel` | `validated` |
| `unvalidated_chr22_run()` | `tumor_normal` | `subset` | `unvalidated_resources` |

```python
from oncokernel_contracts.fixtures import ALL_FIXTURES

for name, build in ALL_FIXTURES.items():
    profile = build()
```

---

## Package layout

| Module | Contents |
|---|---|
| `enums.py` | `SampleMode`, `Territory`, `TmbMethod`, `MsiStatus`, `ValidationStatus`, `CaveatCode` |
| `panels.py` | `Panel` registry, `PanelSpec`, `TMB_FOOTPRINT_FLOOR_MB` |
| `regions.py` | `RegionsAnalysed`, `GENOME_WIDE` |
| `provenance.py` | `Provenance` |
| `limitations.py` | `Limitation`, `DEFAULT_RENDERINGS`, `limitation()`, `codes()` |
| `variants.py` | `Variant` |
| `profiles.py` | `GenomicProfile`, `PseudonymizedProfile` |
| `projection.py` | `project()`, `FIELD_DISPOSITION`, `Disposition` |
| `identifiers.py` | `assert_pseudonymous()`, `IdentifierHygieneError` |
| `fixtures.py` | Golden payloads |
| `schemas.py` | JSON Schema generation and drift check |

`schemas/` holds generated, committed JSON Schemas. `docs/` holds reference documentation.

## Documentation

| Page | Contents |
|---|---|
| [API reference](docs/api-reference.md) | Models, fields, types, functions |
| [Validation rules](docs/validation-rules.md) | Every rule and the error it raises |
| [Panel registry](docs/panels.md) | Registered panels; how to add one |
| [Caveat codes](docs/caveat-codes.md) | `CaveatCode` catalogue and rendering requirements |
| [Migrations](docs/migrations.md) | Version history |

# API reference

All public names are importable from the package root: `from oncokernel_contracts import GenomicProfile`.

Every model sets `model_config = ConfigDict(extra="forbid", frozen=True)`. Unknown fields raise `ValidationError`; instances are immutable after construction.

---

## Models

### `GenomicProfile`

On-premise record. Produced by the ingestion adapter. Not for transmission outside the hospital network.

| Field | Type | Default | Constraints |
|---|---|---|---|
| `schema_version` | `str` | `"1.0.0"` | |
| `sample_id` | `str` | *required* | Passed through `assert_pseudonymous()` |
| `sample_mode` | `SampleMode` | *required* | |
| `regions_analysed` | `RegionsAnalysed` | *required* | |
| `vcf_path` | `str \| None` | `None` | Not present on `PseudonymizedProfile` |
| `somatic_variants` | `tuple[Variant, ...]` | `()` | |
| `germline_variants` | `tuple[Variant, ...]` | `()` | Requires `sample_mode == tumor_normal`. Not present on `PseudonymizedProfile` |
| `tumor_purity` | `float \| None` | `None` | `> 0.0`, `<= 1.0` |
| `ploidy` | `float \| None` | `None` | `> 0.0` |
| `tmb` | `float \| None` | `None` | `>= 0.0` |
| `tmb_method` | `TmbMethod \| None` | `None` | Set if and only if `tmb` is set |
| `msi_status` | `MsiStatus \| None` | `None` | |
| `hla_type` | `tuple[str, ...]` | `()` | |
| `provenance` | `Provenance` | *required* | |
| `limitations` | `tuple[Limitation, ...]` | `()` | Must be non-empty when `sample_mode == tumor_only` |

Metric availability depends on `sample_mode` and `regions_analysed` — see [Validation rules](validation-rules.md#metric-permission-matrix).

### `PseudonymizedProfile`

Egress payload. The only structure permitted to leave the hospital network.

Same fields as `GenomicProfile` except:

| Change | Detail |
|---|---|
| Added | `sample_uuid: UUID` *(required)* |
| Removed | `sample_id`, `vcf_path`, `germline_variants` |

Construct via [`project()`](#projection), not directly.

### `RegionsAnalysed`

| Field | Type | Default |
|---|---|---|
| `kind` | `Territory` | *required* |
| `panel` | `Panel \| None` | `None` |
| `regions` | `tuple[str, ...]` | `()` |

| `kind` | `panel` | `regions` |
|---|---|---|
| `genome_wide` | must be `None` | must be empty |
| `panel` | required | must be empty |
| `subset` | must be `None` | at least one entry |

**Properties and methods**

| Name | Returns | Description |
|---|---|---|
| `is_genome_wide` | `bool` | `kind is Territory.GENOME_WIDE` |
| `supports_genome_wide_metrics()` | `bool` | Whether `tumor_purity`, `ploidy`, `msi_status` are permitted |
| `supports_tmb(sample_mode)` | `bool` | Whether `tmb` is permitted for the given mode |

**Constant**

`GENOME_WIDE` — a prebuilt `RegionsAnalysed(kind=Territory.GENOME_WIDE)`.

### `Provenance`

| Field | Type | Default | Example |
|---|---|---|---|
| `engine` | `str` | *required* | `"oncoanalyser@2.3.0"` |
| `resource_bundle` | `str` | *required* | `"hmf@5.34"`, `"public-unvalidated@<hash>"` |
| `validation_status` | `ValidationStatus` | *required* | |
| `pipeline_git_sha` | `str` | *required* | |
| `tool_versions` | `dict[str, str]` | `{}` | `{"sage": "3.4"}` |
| `container_digests` | `dict[str, str]` | `{}` | `{"sage": "sha256:…"}` |

**Property:** `is_validated -> bool` — `validation_status is ValidationStatus.VALIDATED`.

### `Limitation`

| Field | Type | Default |
|---|---|---|
| `code` | `CaveatCode` | *required* |
| `rendering` | `str` | Filled from `DEFAULT_RENDERINGS[code]` when omitted or empty |

### `Variant`

| Field | Type | Default | Constraints |
|---|---|---|---|
| `chrom` | `str` | *required* | |
| `pos` | `int` | *required* | `> 0` (1-based, VCF convention) |
| `ref` | `str` | *required* | length ≥ 1 |
| `alt` | `str` | *required* | length ≥ 1 |
| `gene` | `str \| None` | `None` | |
| `vaf` | `float \| None` | `None` | `0.0 … 1.0` |
| `tier` | `str \| None` | `None` | Caller tier, e.g. `"HOTSPOT"` |
| `filter` | `str \| None` | `None` | VCF `FILTER`, e.g. `"PASS"` |

---

## Enumerations

| Enum | Members |
|---|---|
| `SampleMode` | `tumor_normal`, `tumor_only` |
| `Territory` | `genome_wide`, `panel`, `subset` |
| `TmbMethod` | `genome_wide`, `panel_derived` |
| `MsiStatus` | `MSI`, `MSS` |
| `ValidationStatus` | `validated`, `unvalidated_resources` |
| `CaveatCode` | See [Caveat codes](caveat-codes.md) |
| `Disposition` | `MAPPED`, `TRANSFORMED`, `DROPPED` |

All except `Disposition` are `StrEnum` and serialise as plain strings.

---

## Projection

### `project(profile, *, sample_uuid)`

```python
def project(profile: GenomicProfile, *, sample_uuid: UUID) -> PseudonymizedProfile
```

| Parameter | Type | Description |
|---|---|---|
| `profile` | `GenomicProfile` | Source record |
| `sample_uuid` | `UUID` | Keyword-only. Supplied by the caller; the library holds no identifier mapping |

Returns a `PseudonymizedProfile`. Raises `ValidationError` if the result violates any rule.

### `FIELD_DISPOSITION`

`Mapping[str, tuple[Disposition, str]]` — every `GenomicProfile` field mapped to its disposition and a reason string.

| Field | Disposition |
|---|---|
| `schema_version`, `sample_mode`, `regions_analysed`, `somatic_variants`, `tumor_purity`, `ploidy`, `tmb`, `tmb_method`, `msi_status`, `hla_type`, `provenance`, `limitations` | `MAPPED` |
| `sample_id` | `TRANSFORMED` → `sample_uuid` |
| `vcf_path`, `germline_variants` | `DROPPED` |

Derived sets: `MAPPED_FIELDS`, `TRANSFORMED_FIELDS`, `DROPPED_FIELDS` (all `frozenset[str]`).

A `GenomicProfile` field absent from `FIELD_DISPOSITION` fails `tests/test_projection.py`.

---

## Functions

### `assert_pseudonymous(value, *, field="identifier")`

```python
def assert_pseudonymous(value: str, *, field: str = "identifier") -> str
```

Returns `value` unchanged, or raises `IdentifierHygieneError` (a `ValueError`). Rejection patterns are listed in [Validation rules](validation-rules.md#identifier-hygiene).

### `limitation(code)`

```python
def limitation(code: CaveatCode) -> Limitation
```

Builds a `Limitation` with the default rendering for `code`.

### `codes(limitations)`

```python
def codes(limitations: tuple[Limitation, ...]) -> frozenset[CaveatCode]
```

---

## Panels

### `Panel`

`StrEnum`. Members and footprints: [Panel registry](panels.md).

| Property | Type | Description |
|---|---|---|
| `spec` | `PanelSpec` | Static registry entry |
| `footprint_mb` | `float` | Coding footprint |
| `supports_tmb` | `bool` | `footprint_mb >= TMB_FOOTPRINT_FLOOR_MB` |

### `PanelSpec`

Frozen dataclass: `footprint_mb: float`, `provenance: str`, `assay_version: str`.

### `TMB_FOOTPRINT_FLOOR_MB`

`float` — `1.0`.

---

## Schema generation

### `oncokernel_contracts.schemas`

| Name | Signature | Description |
|---|---|---|
| `MODELS` | `tuple[type[BaseModel], ...]` | Models with committed schemas |
| `SCHEMA_DIR` | `Path` | Output directory (`schemas/`) |
| `write()` | `() -> list[Path]` | Regenerate and write |
| `check()` | `() -> list[str]` | Drift descriptions; empty means clean |
| `main()` | `() -> int` | CLI entry point |

```bash
python -m oncokernel_contracts.schemas [--check]
```

---

## Constants

| Name | Type | Value |
|---|---|---|
| `SCHEMA_VERSION` | `str` | `"1.0.0"` |
| `__version__` | `str` | `"0.1.0"` |
| `TMB_FOOTPRINT_FLOOR_MB` | `float` | `1.0` |
| `GENOME_WIDE` | `RegionsAnalysed` | `kind=genome_wide` |
| `DEFAULT_RENDERINGS` | `Mapping[CaveatCode, str]` | See [Caveat codes](caveat-codes.md) |

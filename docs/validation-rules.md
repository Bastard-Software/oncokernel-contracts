# Validation rules

Every rule below raises `pydantic.ValidationError` on violation.

---

## Metric permission matrix

`sample_mode` and `regions_analysed.kind` together determine which metrics may be set. Any other combination raises.

| `sample_mode` | `genome_wide` | `panel` (≥ 1.0 Mb) | `panel` (< 1.0 Mb) | `subset` |
|---|---|---|---|---|
| `tumor_normal` | `tumor_purity`, `ploidy`, `msi_status`, `tmb` | `tmb` only | — | — |
| `tumor_only` | `tumor_purity`, `ploidy`, `msi_status`, `tmb` | — | — | — |

Cells marked `—` permit no metrics.

### Errors

| Condition | Message contains |
|---|---|
| `tumor_purity`, `ploidy` or `msi_status` set when `kind != genome_wide` | `require genome-wide coverage` |
| `tmb` set on a combination not in the matrix | `tmb is not permitted` |
| `tmb` set without `tmb_method` | `tmb requires an explicit tmb_method` |
| `tmb_method` set without `tmb` | `tmb_method set without a tmb value` |
| `tmb_method` inconsistent with territory | `does not match territory` |

### `tmb_method` values

| Territory | Required `tmb_method` |
|---|---|
| `genome_wide` | `genome_wide` |
| `panel` | `panel_derived` |

---

## Limitations

| Condition | Requirement | Message contains |
|---|---|---|
| `sample_mode == tumor_only` | `limitations` non-empty | `must carry limitations` |
| `sample_mode == tumor_only` | `TUMOR_ONLY_GERMLINE_UNSEPARATED` present | `TUMOR_ONLY_GERMLINE_UNSEPARATED` |
| `provenance.validation_status == unvalidated_resources` | `RESOURCES_UNVALIDATED` present | `RESOURCES_UNVALIDATED` |

`sample_mode == tumor_normal` with an empty `limitations` tuple is valid.

---

## Germline data

| Condition | Result | Message contains |
|---|---|---|
| `germline_variants` non-empty and `sample_mode != tumor_normal` | rejected | `there is no normal sample` |
| `germline_variants` on `PseudonymizedProfile` | field does not exist | — |

---

## Identifier hygiene

Applied to `GenomicProfile.sample_id`. Raises `IdentifierHygieneError`.

| Pattern | Example rejected |
|---|---|
| Empty or whitespace-only | `""`, `"   "` |
| Leading or trailing whitespace | `"  OK-0001  "` |
| Contains a space | `"Jan Kowalski"` |
| 11 digits, not digit-adjacent (PESEL) | `"85010112345"`, `"pat_85010112345"` |
| Date, not digit-adjacent (`YYYY-MM-DD`, `DD.MM.YYYY`, and `/` `.` `-` variants) | `"MRN-1985-01-01"`, `"pat_01.01.1985"` |
| Run of 9 or more digits | `"MRN123456789"` |

Accepted examples: `OK-TN-0001`, `a3f9c2`, `sample-22-b`, `OK_0001`.

`PseudonymizedProfile.sample_uuid` is typed `UUID`; non-UUID input raises during parsing.

---

## Territory shape

| `kind` | Rule | Message contains |
|---|---|---|
| `genome_wide` | `panel` and `regions` both unset | `neither panel nor regions` |
| `panel` | `panel` set | `requires a registered panel` |
| `panel` | `regions` unset | `takes no explicit regions` |
| `subset` | `regions` non-empty | `requires at least one region` |
| `subset` | `panel` unset | `takes no panel` |

An unregistered panel identifier fails enum parsing.

### Excluded regions

Permitted only on `genome_wide`, which may report genome-wide metrics as rates over what survived.

| Rule | Message contains |
|---|---|
| `excluded` or `analysed_bases` set on `panel` or `subset` | `neither excluded nor analysed_bases` |
| `excluded` set without a positive `analysed_bases` | `require a positive analysed_bases` |
| `analysed_bases` set without `excluded` | `without any excluded regions` |
| Span not of the form `chr6:0-60000000` | `is not of the form` |
| Span ends at or before it starts | `ends at or before it starts` |
| Two spans overlap on one contig | `overlap on <contig>` |
| Excluded fraction over `MAX_EXCLUDED_FRACTION` (0.20) | `over the 20% ceiling` |

The fraction is `excluded / (excluded + analysed_bases)`. Abutting spans are legal; the coordinates are half-open.

---

## Model configuration

| Rule | Applies to | Effect |
|---|---|---|
| `extra="forbid"` | all models | Unknown field raises `ValidationError` |
| `frozen=True` | all models | Attribute assignment raises `ValidationError` |

---

## Field constraints

| Field | Constraint |
|---|---|
| `tumor_purity` | `> 0.0`, `<= 1.0` |
| `ploidy` | `> 0.0` |
| `tmb` | `>= 0.0` |
| `Variant.pos` | `> 0` |
| `Variant.ref`, `Variant.alt` | length ≥ 1 |
| `Variant.vaf` | `0.0 … 1.0` |

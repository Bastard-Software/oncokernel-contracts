# Migrations

Every model carries `schema_version`. Changes are additive: new fields are optional with defaults. A breaking change requires a major version bump and an entry here.

## Upgrade order

Because egress models set `extra="forbid"`, an older consumer receiving a newer payload raises `ValidationError` rather than ignoring the unknown field.

**Bump consumers before producers.**

## `1.0.0` — initial release

Baseline. No migration required.

| Added | Detail |
|---|---|
| `GenomicProfile` | On-premise record |
| `PseudonymizedProfile` | Egress payload |
| `project()` | Projection plus `FIELD_DISPOSITION` table |
| Metric permission matrix | `sample_mode` × `regions_analysed` gating, incl. `tumor_normal`-only panel TMB |
| `Panel` | Registry with 2 seeded entries (unapproved) |
| `Provenance` | `engine`, `resource_bundle`, `validation_status` as independent fields |
| `Limitation` / `CaveatCode` | Forced codes for `tumor_only` and `unvalidated_resources` |
| `assert_pseudonymous()` | Identifier hygiene on `sample_id`; `UUID` on egress |
| `fixtures` | 4 golden payloads covering both tracks |

Not included: copilot and dashboard contracts.

## Unversioned — territory exclusions

Additive, so no version bump: `schema_version` stays `1.0.0` and `__version__` stays `0.1.0`. Taken deliberately because the ingestion engine is the only consumer; the addition would otherwise require a consumer bump first, per the upgrade order above.

| Added | Detail |
|---|---|
| `RegionsAnalysed.excluded` | Half-open spans removed from an otherwise genome-wide territory |
| `RegionsAnalysed.analysed_bases` | What survived; required whenever `excluded` is set |
| `MAX_EXCLUDED_FRACTION` | 0.20 ceiling, above which the territory is not genome-wide |
| `CaveatCode.TERRITORY_PARTIALLY_EXCLUDED` | Required when `excluded` is non-empty |

Genome-wide metrics remain permitted on a partly excluded territory. Consumers reading `tmb` must treat it as a rate over `analysed_bases`, not over the genome.

The next consumer to appear makes this a real bump, and this entry becomes its migration note.

## Planned

| Trigger | Change | Breaking |
|---|---|---|
| Ingestion MV | `validation_status` becomes `validated`; `RESOURCES_UNVALIDATED` no longer emitted | No — data change only |
| Panel approved | New `Panel` member + `PanelSpec` | No — additive; requires consumer bump to reference |
| Copilot build starts | `GraphAnnotation`, `ActionableVariant`, `AIInferenceLayer`, `TherapeuticMatrix` | No — new models |

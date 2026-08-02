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

## Planned

| Trigger | Change | Breaking |
|---|---|---|
| Ingestion MV | `validation_status` becomes `validated`; `RESOURCES_UNVALIDATED` no longer emitted | No — data change only |
| Panel approved | New `Panel` member + `PanelSpec` | No — additive; requires consumer bump to reference |
| Copilot build starts | `GraphAnnotation`, `ActionableVariant`, `AIInferenceLayer`, `TherapeuticMatrix` | No — new models |

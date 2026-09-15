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

## Unversioned — the gene model behind a transcript

Additive in shape, **breaking in validation**: a profile whose variants carry a `transcript` no longer validates unless `provenance.gene_model` is set. Nothing that previously validated without annotation is affected.

`schema_version` stays `1.0.0` and `__version__` stays `0.1.0`, on the same reasoning as the territory-exclusion entry above: the ingestion engine is still the only producer, and the two committed evidence profiles it has emitted are regenerable.

| Added | Detail |
|---|---|
| `GeneModel` | `source`, `release`, `assembly`, `annotator` — the catalogue that minted the transcript ids |
| `GeneModelSource` | `ensembl`, `refseq` |
| `Provenance.gene_model` | Optional; required by the rule below |
| `_annotation_requires_its_gene_model` | Any `transcript` on `somatic_variants` or `germline_variants` demands it |

**Why it is worth a break.** PAVE emits transcript ids unversioned — measured at 510/510 and 660/660 across the two evidence profiles. `ENST00000646891` is `.1` in Ensembl 103 and `.2` in Ensembl 115, so a consumer mapping transcript → protein → residue without the release silently uses whichever one it holds. The output is wrong and looks plausible, which is the failure mode this library exists to prevent.

**What a producer must do.** Populate `provenance.gene_model` from the release that actually ran, not from a default. The ingestion engine pins `homo_sapiens_core_110_38` in `setup.sh`; anything hard-coding a release in the consumer instead is the bug this closes.

**What a consumer must do.** Nothing, unless it constructs profiles. `gene_model` is `MAPPED`, so it crosses the boundary with `provenance` and needs no projection change.

## Planned

| Trigger | Change | Breaking |
|---|---|---|
| Ingestion MV | `validation_status` becomes `validated`; `RESOURCES_UNVALIDATED` no longer emitted | No — data change only |
| Panel approved | New `Panel` member + `PanelSpec` | No — additive; requires consumer bump to reference |
| Copilot build starts | `GraphAnnotation`, `ActionableVariant`, `AIInferenceLayer`, `TherapeuticMatrix` | No — new models |

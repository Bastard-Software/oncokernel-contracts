# Caveat codes

`CaveatCode` is defined in [`enums.py`](../src/oncokernel_contracts/enums.py); default renderings in [`limitations.py`](../src/oncokernel_contracts/limitations.py).

A `Limitation` carries a `code` and a `rendering`. Omitting `rendering` fills it from `DEFAULT_RENDERINGS`.

## Codes

| Code | Default rendering | Enforced when |
|---|---|---|
| `TUMOR_ONLY_GERMLINE_UNSEPARATED` | "No matched normal was sequenced. Somatic and germline variants could not be cleanly separated; rare private germline variants may appear as somatic findings." | **Required** when `sample_mode == tumor_only` |
| `PURITY_FIT_DEGRADED` | "Tumor purity and ploidy were fitted without a matched normal and are less well constrained than on the tumor/normal track." | Set by the producer; not enforced |
| `RESOURCES_UNVALIDATED` | "This run used public substitute reference resources, not the licensed clinical bundle. Output is a wiring artefact and must not be used clinically." | **Required** when `provenance.validation_status == unvalidated_resources` |
| `NOT_GENOME_WIDE` | "Analysis covered a restricted territory. Genome-wide metrics are not reported." | Set by the producer; not enforced |
| `TERRITORY_PARTIALLY_EXCLUDED` | "Part of the genome was excluded from analysis and the reported metrics are rates over the remainder. See regions_analysed.excluded and regions_analysed.analysed_bases." | **Required** when `regions_analysed.excluded` is non-empty |
| `ORACLES_BYPASSED` | "The quantitative sanity checks were disabled for this run. Nothing verified that germline separation, sample identity or variant density are plausible, so this profile is a wiring artefact and must not be used clinically." | Set by the producer; not enforced |
| `ORACLES_FAILED` | "One or more quantitative sanity checks failed for this run. The call set is not what a somatic call set should look like, and the reason is named in the oracle report published beside this profile. Not for clinical use." | Set by the producer; not enforced |
| `GENE_ANNOTATION_UNAVAILABLE` | "No gene model reached this run, so no variant carries a gene, transcript or protein change. An absent gene records that nothing looked, not that the variant lies outside a gene." | Set by the producer; not enforced |

## Consumer requirements

| Requirement |
|---|
| Render every code present in `limitations`. There is no severity field to filter on. |
| Never render a profile carrying `RESOURCES_UNVALIDATED` as a patient report. |
| Never read an absent `gene` as intergenic when `GENE_ANNOTATION_UNAVAILABLE` is present. Nothing looked. |
| Where profiles of both `sample_mode` values are displayed together, the difference must be visible without inspecting a field. |

## Usage

```python
from oncokernel_contracts import CaveatCode, limitation

limitation(CaveatCode.PURITY_FIT_DEGRADED)
# Limitation(code=<CaveatCode.PURITY_FIT_DEGRADED>, rendering='Tumor purity and …')
```

```python
from oncokernel_contracts import Limitation, CaveatCode

Limitation(code=CaveatCode.NOT_GENOME_WIDE, rendering="Custom wording.")
```

## Adding a code

1. Add the member to `CaveatCode`.
2. Add its wording to `DEFAULT_RENDERINGS`. `tests/test_limitations.py` fails if any code lacks one.
3. Add a row to the table above.
4. Notify consuming services — an unrendered code is not displayed to the user.

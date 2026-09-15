"""Golden fixtures, shipped with the package.

Every consuming service tests against *identical* payloads — that is what makes
"independently buildable against a fixed shape" true rather than aspirational,
and it means a mock is a fixture rather than a hand-written JSON file that
drifts.

Both tracks are covered on purpose, so no consumer builds against only the
gold-standard shape and meets the other one in production.
"""

from uuid import UUID

from oncokernel_contracts.enums import (
    CaveatCode,
    GeneModelSource,
    MsiStatus,
    SampleMode,
    Territory,
    TmbMethod,
    ValidationStatus,
)
from oncokernel_contracts.limitations import limitation
from oncokernel_contracts.panels import Panel
from oncokernel_contracts.profiles import GenomicProfile
from oncokernel_contracts.provenance import GeneModel, Provenance
from oncokernel_contracts.regions import GENOME_WIDE, RegionsAnalysed
from oncokernel_contracts.variants import Variant

SAMPLE_UUID = UUID("11111111-2222-3333-4444-555555555555")

#: `_VARIANTS` carries a transcript, so every fixture provenance needs the release
#: that minted it. Ensembl 110 is what the ingestion engine's `setup.sh` pins.
_GENE_MODEL = GeneModel(
    source=GeneModelSource.ENSEMBL,
    release="110",
    assembly="GRCh38",
    annotator="pave@1.9",
)

_UNVALIDATED = Provenance(
    engine="sage-minimal",
    resource_bundle="public-unvalidated@0000000000000000",
    validation_status=ValidationStatus.UNVALIDATED_RESOURCES,
    pipeline_git_sha="0" * 40,
    tool_versions={"sage": "3.4"},
    container_digests={"sage": "sha256:" + "0" * 64},
    gene_model=_GENE_MODEL,
)

_VALIDATED = Provenance(
    engine="oncoanalyser@2.3.0",
    resource_bundle="hmf@5.34",
    validation_status=ValidationStatus.VALIDATED,
    pipeline_git_sha="1" * 40,
    tool_versions={"sage": "3.4", "purple": "4.0", "amber": "4.0", "cobalt": "1.16"},
    container_digests={"sage": "sha256:" + "1" * 64},
    gene_model=_GENE_MODEL,
)

_VARIANTS = (
    Variant(
        chrom="chr22",
        pos=29083731,
        ref="C",
        alt="T",
        gene="CHEK2",
        vaf=0.31,
        tier="HIGH_CONFIDENCE",
        filter="PASS",
    ),
    Variant(
        chrom="chr22",
        pos=23180263,
        ref="G",
        alt="A",
        gene="BCR",
        vaf=0.18,
        tier="PANEL",
        filter="PASS",
    ),
    # Annotated, so the schema examples carry the shape a consumer reasons over.
    # Real values rather than invented ones: the canonical missense of the field.
    Variant(
        chrom="chr7",
        pos=140753336,
        ref="A",
        alt="T",
        gene="BRAF",
        vaf=0.63,
        tier="HOTSPOT",
        filter="PASS",
        transcript="ENST00000646891",
        consequence="missense_variant",
        hgvs_coding="c.1799T>A",
        hgvs_protein="p.Val600Glu",
    ),
)


def tumor_normal_genome_wide() -> GenomicProfile:
    """The gold-standard shape: matched normal, genome-wide, licensed resources."""
    return GenomicProfile(
        sample_id="OK-TN-0001",
        sample_mode=SampleMode.TUMOR_NORMAL,
        regions_analysed=GENOME_WIDE,
        vcf_path="/data/onprem/OK-TN-0001/somatic.vcf.gz",
        somatic_variants=_VARIANTS,
        germline_variants=(
            Variant(chrom="chr22", pos=29091840, ref="A", alt="G", gene="CHEK2", vaf=0.49),
        ),
        tumor_purity=0.62,
        ploidy=2.1,
        tmb=7.4,
        tmb_method=TmbMethod.GENOME_WIDE,
        msi_status=MsiStatus.MSS,
        hla_type=("A*02:01", "A*01:01", "B*07:02", "B*08:01", "C*07:01", "C*07:02"),
        provenance=_VALIDATED,
    )


def tumor_only_genome_wide() -> GenomicProfile:
    """The compromised track: no matched normal, so mandatory caveats."""
    return GenomicProfile(
        sample_id="OK-TO-0002",
        sample_mode=SampleMode.TUMOR_ONLY,
        regions_analysed=GENOME_WIDE,
        vcf_path="/data/onprem/OK-TO-0002/somatic.vcf.gz",
        somatic_variants=_VARIANTS,
        tumor_purity=0.55,
        ploidy=2.0,
        tmb=9.1,
        tmb_method=TmbMethod.GENOME_WIDE,
        msi_status=MsiStatus.MSS,
        hla_type=("A*02:01", "A*03:01", "B*07:02", "B*15:01", "C*03:04", "C*07:02"),
        provenance=_VALIDATED,
        limitations=(
            limitation(CaveatCode.TUMOR_ONLY_GERMLINE_UNSEPARATED),
            limitation(CaveatCode.PURITY_FIT_DEGRADED),
        ),
    )


def tumor_normal_panel() -> GenomicProfile:
    """Panel-derived TMB — legal only because this is the tumor/normal track."""
    return GenomicProfile(
        sample_id="OK-TN-0003",
        sample_mode=SampleMode.TUMOR_NORMAL,
        regions_analysed=RegionsAnalysed(kind=Territory.PANEL, panel=Panel.MSK_IMPACT_V468),
        somatic_variants=_VARIANTS,
        tmb=11.2,
        tmb_method=TmbMethod.PANEL_DERIVED,
        provenance=_VALIDATED,
        limitations=(limitation(CaveatCode.NOT_GENOME_WIDE),),
    )


def unvalidated_chr22_run() -> GenomicProfile:
    """What M1 actually emits: a wiring artefact, structurally quarantined."""
    return GenomicProfile(
        sample_id="OK-DEV-0004",
        sample_mode=SampleMode.TUMOR_NORMAL,
        regions_analysed=RegionsAnalysed(kind=Territory.SUBSET, regions=("chr22",)),
        vcf_path="/data/dev/OK-DEV-0004/somatic.vcf.gz",
        somatic_variants=_VARIANTS,
        provenance=_UNVALIDATED,
        limitations=(
            limitation(CaveatCode.RESOURCES_UNVALIDATED),
            limitation(CaveatCode.NOT_GENOME_WIDE),
        ),
    )


ALL_FIXTURES = {
    "tumor_normal_genome_wide": tumor_normal_genome_wide,
    "tumor_only_genome_wide": tumor_only_genome_wide,
    "tumor_normal_panel": tumor_normal_panel,
    "unvalidated_chr22_run": unvalidated_chr22_run,
}

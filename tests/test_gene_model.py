"""The gene model behind a transcript id, and the rule that demands it.

`Variant` refuses an HGVS string without its transcript. This is the same rule
one level up: a transcript id is only a coordinate against the catalogue release
that minted it, and PAVE emits them unversioned — `ENST00000646891` is `.1` in
Ensembl 103 and `.2` in Ensembl 115.
"""

import pytest
from pydantic import ValidationError

from oncokernel_contracts import (
    CaveatCode,
    GeneModel,
    GeneModelSource,
    GenomicProfile,
    RegionsAnalysed,
    SampleMode,
    Territory,
    Variant,
    limitation,
    project,
)
from oncokernel_contracts.fixtures import _VALIDATED, SAMPLE_UUID

SUBSET = RegionsAnalysed(kind=Territory.SUBSET, regions=("chr22",))

ANNOTATED = Variant(
    chrom="chr7",
    pos=140753336,
    ref="A",
    alt="T",
    gene="BRAF",
    transcript="ENST00000646891",
    consequence="missense_variant",
    hgvs_coding="c.1799T>A",
    hgvs_protein="p.Val600Glu",
)
BARE = Variant(chrom="chr1", pos=12345, ref="G", alt="C")

GENE_MODEL = GeneModel(
    source=GeneModelSource.ENSEMBL,
    release="110",
    assembly="GRCh38",
    annotator="pave@1.9",
)


def build(*, variants=(), germline=(), gene_model=GENE_MODEL, mode=SampleMode.TUMOR_NORMAL):
    return GenomicProfile(
        sample_id="OK-GM-0001",
        sample_mode=mode,
        regions_analysed=SUBSET,
        somatic_variants=variants,
        germline_variants=germline,
        provenance=_VALIDATED.model_copy(update={"gene_model": gene_model}),
        limitations=(
            (limitation(CaveatCode.TUMOR_ONLY_GERMLINE_UNSEPARATED),)
            if mode is SampleMode.TUMOR_ONLY
            else ()
        ),
    )


def test_an_annotated_profile_declaring_its_gene_model_is_accepted():
    profile = build(variants=(ANNOTATED,))

    assert profile.provenance.gene_model.release == "110"
    assert profile.provenance.gene_model.source is GeneModelSource.ENSEMBL


def test_an_annotated_profile_without_a_gene_model_is_refused():
    """The defect this rule exists for: a consumer resolving transcript to
    residue against whichever release it happens to hold draws the wrong residue
    and looks plausible doing it.
    """
    with pytest.raises(ValidationError, match=r"provenance\.gene_model is required"):
        build(variants=(ANNOTATED,), gene_model=None)


def test_an_unannotated_profile_needs_no_gene_model():
    """Half of a real call set is intergenic. A run that annotated nothing has no
    gene model to declare, and must not be forced to invent one.
    """
    profile = build(variants=(BARE,), gene_model=None)

    assert profile.provenance.gene_model is None


def test_a_germline_transcript_also_demands_the_gene_model():
    """The rule reads both variant collections. `germline_variants` exists only on
    `GenomicProfile`, which is exactly why the base class asks rather than assumes.
    """
    with pytest.raises(ValidationError, match=r"provenance\.gene_model is required"):
        build(germline=(ANNOTATED,), gene_model=None)


def test_a_transcript_without_hgvs_still_demands_the_gene_model():
    """The common case — an intronic call with a transcript and no protein change.
    The transcript is the thing that needs the release, not the HGVS string.
    """
    intronic = Variant(
        chrom="chr21",
        pos=22000000,
        ref="C",
        alt="T",
        gene="NCAM2",
        transcript="ENST00000400546",
        consequence="intron_variant",
    )

    with pytest.raises(ValidationError, match=r"provenance\.gene_model is required"):
        build(variants=(intronic,), gene_model=None)


def test_an_empty_release_is_not_a_release():
    """`gene_model` present but blank would satisfy the rule while carrying nothing."""
    with pytest.raises(ValidationError):
        GeneModel(
            source=GeneModelSource.ENSEMBL, release="", assembly="GRCh38", annotator="pave@1.9"
        )


def test_the_gene_model_is_frozen_and_forbids_extras():
    with pytest.raises(ValidationError):
        GeneModel(
            source=GeneModelSource.ENSEMBL,
            release="110",
            assembly="GRCh38",
            annotator="pave@1.9",
            uniprot="P15056",
        )


def test_the_gene_model_crosses_the_boundary():
    """It describes a public reference resource, not the patient, and every cloud
    consumer has the same transcript-resolution problem. `provenance` is already
    MAPPED, so this rides along with it.
    """
    crossed = project(build(variants=(ANNOTATED,)), sample_uuid=SAMPLE_UUID)

    assert crossed.provenance.gene_model == GENE_MODEL

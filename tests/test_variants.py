"""The variant record, and the annotation a consumer reasons over.

`gene` alone names a region; the transcript and HGVS strings are what turn a
coordinate into a protein change — which is what the downstream translation and
folding stages consume.
"""

import pytest
from pydantic import ValidationError

from oncokernel_contracts.variants import Variant

BRAF = {
    "chrom": "chr7",
    "pos": 140753336,
    "ref": "A",
    "alt": "T",
    "gene": "BRAF",
    "transcript": "ENST00000646891",
    "consequence": "missense_variant",
    "hgvs_coding": "c.1799T>A",
    "hgvs_protein": "p.Val600Glu",
}


def test_the_annotation_round_trips():
    variant = Variant(**BRAF)

    assert variant.hgvs_protein == "p.Val600Glu"
    assert variant.transcript == "ENST00000646891"
    assert variant.model_dump()["consequence"] == "missense_variant"


def test_annotation_is_optional():
    """An unannotated call set is still a valid one — intergenic variants carry
    no consequence, and a run without a gene model annotates nothing at all.
    """
    bare = Variant(chrom="chr1", pos=877772, ref="G", alt="C")

    assert bare.gene is None
    assert bare.hgvs_protein is None


def test_a_protein_change_without_its_transcript_is_refused():
    """`p.Val600Glu` names residue 600 of *something*. Annotators emit the two
    together, so this catches a parser that dropped one.
    """
    with pytest.raises(ValidationError, match="require transcript"):
        Variant(**{**BRAF, "transcript": None})


def test_a_coding_change_without_its_transcript_is_refused():
    with pytest.raises(ValidationError, match="require transcript"):
        Variant(chrom="chr7", pos=140753336, ref="A", alt="T", hgvs_coding="c.1799T>A")


def test_a_transcript_without_hgvs_is_allowed():
    """The common case for a non-coding consequence: PAVE names the transcript
    an intron belongs to and leaves the protein field empty.
    """
    intronic = Variant(
        chrom="chr21",
        pos=22370000,
        ref="C",
        alt="T",
        gene="NCAM2",
        transcript="ENST00000400546",
        consequence="intron_variant",
    )

    assert intronic.hgvs_protein is None


def test_co_occurring_consequences_are_not_rejected():
    """Annotators join terms with `&` and the vocabulary is open, so an enum here
    would fail on a term that is merely unfamiliar.
    """
    spliced = Variant(
        chrom="chr17",
        pos=7673803,
        ref="G",
        alt="A",
        gene="TP53",
        transcript="ENST00000269305",
        consequence="splice_acceptor_variant&intron_variant",
    )

    assert "&" in spliced.consequence


def test_unknown_fields_are_still_forbidden():
    """`extra="forbid"` is what makes the contract a contract."""
    with pytest.raises(ValidationError):
        Variant(chrom="chr1", pos=1, ref="A", alt="T", clinical_significance="pathogenic")

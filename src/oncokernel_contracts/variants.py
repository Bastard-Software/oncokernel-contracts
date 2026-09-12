"""The minimal variant record.

Deliberately small: this library defines what the ingestion adapter must
*produce*, not everything a VCF can express. Fields grow when a consumer needs
them, additively.
"""

from pydantic import BaseModel, ConfigDict, Field, model_validator


class Variant(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    chrom: str
    pos: int = Field(gt=0, description="1-based, VCF convention")
    ref: str = Field(min_length=1)
    alt: str = Field(min_length=1)
    gene: str | None = None
    vaf: float | None = Field(default=None, ge=0.0, le=1.0)
    tier: str | None = Field(default=None, description="caller tier, e.g. SAGE HOTSPOT")
    filter: str | None = Field(default=None, description="VCF FILTER, e.g. PASS")

    #: The transcript the HGVS strings below are relative to. `p.Val600Glu`
    #: names a residue in one transcript and is ambiguous without it.
    transcript: str | None = Field(
        default=None, description="Ensembl transcript id, e.g. ENST00000646891"
    )

    #: Sequence Ontology term for the canonical transcript. A string rather than
    #: an enum: the vocabulary is open and annotators join co-occurring terms
    #: with `&`, so an unfamiliar consequence must not fail validation.
    consequence: str | None = Field(
        default=None, description="e.g. missense_variant, splice_acceptor_variant&intron_variant"
    )

    hgvs_coding: str | None = Field(default=None, description="HGVS c., e.g. c.1799T>A")
    hgvs_protein: str | None = Field(default=None, description="HGVS p., e.g. p.Val600Glu")

    @model_validator(mode="after")
    def _hgvs_needs_its_transcript(self) -> "Variant":
        """An HGVS string without a transcript names a residue in nothing.

        Annotators emit the two together, so this catches a parser that dropped
        one — not a caller that never supplied it.
        """
        if (self.hgvs_coding or self.hgvs_protein) and not self.transcript:
            raise ValueError(
                "hgvs_coding/hgvs_protein require transcript: a protein change is "
                "only interpretable against the transcript it was called on"
            )
        return self

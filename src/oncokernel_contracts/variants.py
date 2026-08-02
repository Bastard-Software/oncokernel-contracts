"""The minimal variant record.

Deliberately small: this library defines what the ingestion adapter must
*produce*, not everything a VCF can express. Fields grow when a consumer needs
them, additively.
"""

from pydantic import BaseModel, ConfigDict, Field


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

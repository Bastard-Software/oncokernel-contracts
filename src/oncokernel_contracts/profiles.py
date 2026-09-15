"""The two ingestion profiles, and the invariants they enforce.

`GenomicProfile` is the complete on-prem record. `PseudonymizedProfile` is the
egress projection — the only payload that crosses the hospital boundary.

Both carry the same metric-permission rules, because a rule that only holds on
one side of the boundary is a rule someone will route around.
"""

from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from oncokernel_contracts.enums import (
    CaveatCode,
    MsiStatus,
    SampleMode,
    TmbMethod,
    ValidationStatus,
)
from oncokernel_contracts.identifiers import assert_pseudonymous
from oncokernel_contracts.limitations import Limitation, codes
from oncokernel_contracts.provenance import Provenance
from oncokernel_contracts.regions import RegionsAnalysed
from oncokernel_contracts.variants import Variant
from oncokernel_contracts.version import SCHEMA_VERSION


class _ProfileBase(BaseModel):
    """Fields and invariants common to both sides of the boundary.

    `extra="forbid"` is the house default and a non-negotiable invariant on
    egress: Pydantic silently ignores unknown fields otherwise, which on this
    boundary is a leak vector and — with a typo'd field name — a silent data
    loss. `frozen=True` because a payload that can be mutated after validation
    is a payload whose validation proved nothing about what actually gets sent.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: str = SCHEMA_VERSION
    sample_mode: SampleMode
    regions_analysed: RegionsAnalysed

    somatic_variants: tuple[Variant, ...] = ()

    tumor_purity: float | None = Field(default=None, gt=0.0, le=1.0)
    ploidy: float | None = Field(default=None, gt=0.0)
    tmb: float | None = Field(default=None, ge=0.0)
    tmb_method: TmbMethod | None = None
    msi_status: MsiStatus | None = None

    #: Germline-derived, and the one deliberate exception to "germline does not
    #: cross" — it is required downstream for immunotherapy reasoning and crosses
    #: as a type call rather than as variant records.
    hla_type: tuple[str, ...] = ()

    provenance: Provenance
    limitations: tuple[Limitation, ...] = ()

    @model_validator(mode="after")
    def _genome_wide_metrics_require_genome_wide_territory(self) -> "_ProfileBase":
        if self.regions_analysed.supports_genome_wide_metrics():
            return self
        offenders = [
            name
            for name in ("tumor_purity", "ploidy", "msi_status")
            if getattr(self, name) is not None
        ]
        if offenders:
            raise ValueError(
                f"{', '.join(offenders)} require genome-wide coverage, but "
                f"regions_analysed.kind is {self.regions_analysed.kind.value!r}"
            )
        return self

    @model_validator(mode="after")
    def _tmb_requires_permitted_territory_and_mode(self) -> "_ProfileBase":
        if self.tmb is None:
            if self.tmb_method is not None:
                raise ValueError("tmb_method set without a tmb value")
            return self

        if self.tmb_method is None:
            raise ValueError("tmb requires an explicit tmb_method")

        if not self.regions_analysed.supports_tmb(self.sample_mode):
            raise ValueError(
                f"tmb is not permitted for sample_mode={self.sample_mode.value!r} on "
                f"territory {self.regions_analysed.kind.value!r}: panel-derived TMB "
                f"requires tumor_normal and a registered panel of at least 1.0 Mb; "
                f"tumor_only requires genome-wide coverage"
            )

        expected = (
            TmbMethod.GENOME_WIDE
            if self.regions_analysed.is_genome_wide
            else TmbMethod.PANEL_DERIVED
        )
        if self.tmb_method is not expected:
            raise ValueError(
                f"tmb_method {self.tmb_method.value!r} does not match territory "
                f"{self.regions_analysed.kind.value!r} (expected {expected.value!r})"
            )
        return self

    @model_validator(mode="after")
    def _tumor_only_must_carry_its_caveat(self) -> "_ProfileBase":
        if self.sample_mode is not SampleMode.TUMOR_ONLY:
            return self
        if not self.limitations:
            raise ValueError(
                "a tumor_only profile must carry limitations; an empty list is not a "
                "valid state for that track"
            )
        if CaveatCode.TUMOR_ONLY_GERMLINE_UNSEPARATED not in codes(self.limitations):
            raise ValueError("a tumor_only profile must carry TUMOR_ONLY_GERMLINE_UNSEPARATED")
        return self

    @model_validator(mode="after")
    def _excluded_territory_must_carry_its_caveat(self) -> "_ProfileBase":
        """Metrics survive an exclusion; silence about it does not.

        The territory model permits a genome-wide claim with holes in it precisely
        so purity, ploidy, TMB and MSI keep flowing. That trade is only honest if
        the holes are declared where a consumer will render them.
        """
        if self.regions_analysed.excluded and CaveatCode.TERRITORY_PARTIALLY_EXCLUDED not in codes(
            self.limitations
        ):
            raise ValueError(
                "regions_analysed.excluded is set, so the profile must carry the "
                "TERRITORY_PARTIALLY_EXCLUDED caveat"
            )
        return self

    def _all_variants(self) -> tuple[Variant, ...]:
        """Every variant on this profile, whichever side of the boundary it is.

        `germline_variants` exists only on `GenomicProfile` — the projection drops
        it — so a rule that has to hold on both sides asks rather than assumes.
        """
        return (*self.somatic_variants, *getattr(self, "germline_variants", ()))

    @model_validator(mode="after")
    def _annotation_requires_its_gene_model(self) -> "_ProfileBase":
        """A transcript id names a residue in nothing without its release.

        `Variant` already refuses an HGVS string without its transcript. This is
        that rule one level up: the transcript is itself only a coordinate against
        the catalogue release that minted it, and PAVE emits them unversioned.
        """
        if any(v.transcript for v in self._all_variants()) and self.provenance.gene_model is None:
            raise ValueError(
                "a variant carries a transcript, so provenance.gene_model is required: "
                "an unversioned transcript id names a residue only against the gene "
                "model release that minted it"
            )
        return self

    @model_validator(mode="after")
    def _unvalidated_resources_must_carry_its_caveat(self) -> "_ProfileBase":
        if (
            self.provenance.validation_status is ValidationStatus.UNVALIDATED_RESOURCES
            and CaveatCode.RESOURCES_UNVALIDATED not in codes(self.limitations)
        ):
            raise ValueError(
                "validation_status=unvalidated_resources must carry the "
                "RESOURCES_UNVALIDATED caveat; it cannot be emitted without it"
            )
        return self


class GenomicProfile(_ProfileBase):
    """The complete on-prem record. Never leaves the hospital network."""

    #: Hospital-supplied pseudonym. Shape-checked, never a direct identifier.
    sample_id: str

    #: On-prem filesystem path. Deliberately absent from the egress projection:
    #: across the boundary it either leaks infrastructure detail or implies the
    #: consumer opens the file.
    vcf_path: str | None = None

    #: Present only on the tumor/normal track. Permanently dropped by the
    #: projection — germline variants are the most durably identifying data in
    #: the pipeline and implicate blood relatives as well as the patient.
    germline_variants: tuple[Variant, ...] = ()

    @field_validator("sample_id")
    @classmethod
    def _sample_id_is_pseudonymous(cls, value: str) -> str:
        return assert_pseudonymous(value, field="sample_id")

    @model_validator(mode="after")
    def _germline_requires_a_matched_normal(self) -> "GenomicProfile":
        if self.germline_variants and self.sample_mode is not SampleMode.TUMOR_NORMAL:
            raise ValueError(
                "germline_variants present but sample_mode is not tumor_normal — "
                "there is no normal sample they could have come from"
            )
        return self


class PseudonymizedProfile(_ProfileBase):
    """The egress projection — the only payload that crosses the moat.

    Built exclusively via `projection.project()`, which is what guarantees every
    source field was explicitly mapped or explicitly dropped.
    """

    sample_uuid: UUID

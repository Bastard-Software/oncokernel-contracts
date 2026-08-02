"""What territory an analysis covered — one half of the metric-permission rule."""

from pydantic import BaseModel, ConfigDict, model_validator

from oncokernel_contracts.enums import SampleMode, Territory
from oncokernel_contracts.panels import Panel


class RegionsAnalysed(BaseModel):
    """The genomic territory an analysis actually covered.

    Together with `SampleMode` this decides which metrics a profile is entitled
    to carry. Purity, ploidy and MSI require genome-wide coverage. TMB is
    additionally allowed from a large enough registered panel — but only on the
    tumor/normal track (see `supports_tmb`).
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    kind: Territory
    panel: Panel | None = None
    regions: tuple[str, ...] = ()

    @model_validator(mode="after")
    def _check_shape(self) -> "RegionsAnalysed":
        match self.kind:
            case Territory.GENOME_WIDE:
                if self.panel is not None or self.regions:
                    raise ValueError("genome_wide territory takes neither panel nor regions")
            case Territory.PANEL:
                if self.panel is None:
                    raise ValueError("panel territory requires a registered panel")
                if self.regions:
                    raise ValueError("panel territory takes no explicit regions")
            case Territory.SUBSET:
                if not self.regions:
                    raise ValueError("subset territory requires at least one region")
                if self.panel is not None:
                    raise ValueError("subset territory takes no panel")
        return self

    @property
    def is_genome_wide(self) -> bool:
        return self.kind is Territory.GENOME_WIDE

    def supports_genome_wide_metrics(self) -> bool:
        """Purity, ploidy and MSI are only meaningful genome-wide."""
        return self.is_genome_wide

    def supports_tmb(self, sample_mode: SampleMode) -> bool:
        """Whether TMB may be claimed for this territory *on this track*.

        Panel-derived TMB is mathematically indefensible without a matched
        normal: at a ~1 Mb footprint the true somatic count is on the order of
        ten variants, so a handful of retained private germline calls — exactly
        the ones population databases cannot filter, and exactly the ones
        enriched in the cancer genes a panel targets — moves a patient across
        the clinical threshold. Genome-wide, the same leakage is diluted across
        a denominator three orders of magnitude larger.
        """
        if self.is_genome_wide:
            return True
        if self.kind is Territory.PANEL and self.panel is not None:
            return self.panel.supports_tmb and sample_mode is SampleMode.TUMOR_NORMAL
        return False


GENOME_WIDE = RegionsAnalysed(kind=Territory.GENOME_WIDE)

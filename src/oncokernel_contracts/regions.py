"""What territory an analysis covered — one half of the metric-permission rule."""

import re
from itertools import pairwise

from pydantic import BaseModel, ConfigDict, model_validator

from oncokernel_contracts.enums import SampleMode, Territory
from oncokernel_contracts.panels import Panel

#: Fraction of an otherwise genome-wide territory that may be excluded before the
#: run stops being genome-wide.
#:
#: This bounds bias, not coverage. Coverage is not the constraint — see
#: `panels.TMB_FOOTPRINT_FLOOR_MB`, which permits a TMB estimate from 1.0 Mb of
#: coding territory. What exclusion costs is representativeness: somatic mutation
#: rate varies at megabase scale with replication timing and chromatin state, so a
#: smaller territory is also a differently-composed one. Measured across one
#: tumour genome's per-contig rates, excluding a fifth of the territory moves the
#: estimate by at most ~9%.
#:
#: 0.20 rather than a rounder 0.25 because the directions are not symmetric:
#: raising this later accepts payloads that were already valid, while lowering it
#: rejects payloads already emitted.
MAX_EXCLUDED_FRACTION = 0.20

#: `chr6:0-60000000`. Half-open, and coordinates are mandatory: this library holds
#: no contig lengths, so a bare `chrX` would be an exclusion of unknown size and
#: the excluded fraction could not be computed. The producer expands whole contigs.
_SPAN = re.compile(r"^(?P<contig>[^\s:]+):(?P<start>\d+)-(?P<end>\d+)$")


def _parse_span(span: str) -> tuple[str, int, int]:
    matched = _SPAN.fullmatch(span)
    if matched is None:
        raise ValueError(f"excluded region {span!r} is not of the form chr6:0-60000000")
    start, end = int(matched["start"]), int(matched["end"])
    if end <= start:
        raise ValueError(f"excluded region {span!r} ends at or before it starts")
    return matched["contig"], start, end


def _refuse_overlaps(spans: list[tuple[str, int, int]]) -> None:
    """Overlapping spans double-count the removal, understating what survived."""
    for contig in {contig for contig, _, _ in spans}:
        ordered = sorted((s, e) for c, s, e in spans if c == contig)
        for (_, first_end), (second_start, _) in pairwise(ordered):
            if second_start < first_end:
                raise ValueError(f"excluded regions overlap on {contig}")


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

    #: Regions removed from an otherwise genome-wide analysis, as `chr6:0-60000000`.
    #: Permitted only on `genome_wide` — a subset already enumerates what it covered.
    excluded: tuple[str, ...] = ()

    #: Bases actually analysed. Required whenever `excluded` is non-empty, because
    #: a rate over an unstated denominator is not a rate.
    analysed_bases: int | None = None

    @model_validator(mode="after")
    def _check_shape(self) -> "RegionsAnalysed":
        match self.kind:
            case Territory.GENOME_WIDE:
                if self.panel is not None or self.regions:
                    raise ValueError("genome_wide territory takes neither panel nor regions")
                self._check_exclusions()
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

        if self.kind is not Territory.GENOME_WIDE and (self.excluded or self.analysed_bases):
            raise ValueError(
                f"{self.kind.value} territory takes neither excluded nor analysed_bases; "
                "a restricted territory states what it covered, not what it left out"
            )
        return self

    def _check_exclusions(self) -> None:
        """Exclusions are only meaningful with a surviving denominator and a bound."""
        if not self.excluded:
            if self.analysed_bases is not None:
                raise ValueError("analysed_bases set without any excluded regions")
            return

        if self.analysed_bases is None or self.analysed_bases <= 0:
            raise ValueError(
                "excluded regions require a positive analysed_bases: a rate over an "
                "unstated denominator is not a rate"
            )

        spans = [_parse_span(span) for span in self.excluded]
        _refuse_overlaps(spans)

        removed = sum(end - start for _, start, end in spans)
        fraction = removed / (removed + self.analysed_bases)
        if fraction > MAX_EXCLUDED_FRACTION:
            raise ValueError(
                f"{fraction:.1%} of the territory is excluded, over the "
                f"{MAX_EXCLUDED_FRACTION:.0%} ceiling — declare this a subset rather "
                "than a genome-wide run with holes in it"
            )

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

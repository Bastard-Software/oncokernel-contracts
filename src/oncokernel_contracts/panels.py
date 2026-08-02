"""The panel registry — compiled-in static data, never I/O.

The TMB rule needs a panel's coding footprint at validation time. Reading that
from a file or a service would drag a parser, a fetch client and a failure mode
into every environment this library imports into (on-prem hospital box, GPU
cloud, public cloud). So the registry is *code*: a `StrEnum` for the wire plus a
frozen mapping for the specs, resolved by attribute access inside a synchronous
validator.

Adding a panel is therefore a pull request with the megabase figure and its
source visible in the diff — the right amount of friction for a clinical
parameter that gates a patient-facing number. The sign-off record lives in
`docs/panels.md`.
"""

from collections.abc import Mapping
from dataclasses import dataclass
from enum import StrEnum
from types import MappingProxyType

#: Coding footprint below which a panel cannot support a TMB estimate.
#:
#: TMB is a rate, so it does not need whole-genome coverage — it needs enough
#: coding territory for the estimate to be stable. ~1.0 Mb is the practical
#: floor established by the Friends of Cancer Research TMB Harmonization work;
#: below it, sampling variance dominates and the number stops meaning anything.
TMB_FOOTPRINT_FLOOR_MB = 1.0


@dataclass(frozen=True, slots=True)
class PanelSpec:
    """Static facts about a panel. Frozen: a registry entry is not editable at runtime."""

    footprint_mb: float
    provenance: str
    assay_version: str


class Panel(StrEnum):
    """Registered panels.

    Members are **assay-versioned** on purpose: revisions change footprint, and a
    TMB validated against last year's territory is not validated against this
    year's.

    Seeded with two publicly documented assays so the mechanism has real test
    coverage on both sides of the floor. **The footprint figures below are taken
    from public documentation and require clinical sign-off before any
    production use** — see `docs/panels.md`.
    """

    FOUNDATION_ONE_CDX_V1 = "foundation_one_cdx_v1"
    MSK_IMPACT_V468 = "msk_impact_v468"

    @property
    def spec(self) -> PanelSpec:
        return _PANEL_SPECS[self]

    @property
    def footprint_mb(self) -> float:
        return self.spec.footprint_mb

    @property
    def supports_tmb(self) -> bool:
        """Whether this panel's territory is large enough for a TMB estimate.

        Note this is necessary but *not* sufficient — panel-derived TMB also
        requires `SampleMode.TUMOR_NORMAL`. See `profiles.py`.
        """
        return self.footprint_mb >= TMB_FOOTPRINT_FLOOR_MB


_PANEL_SPECS: Mapping[Panel, PanelSpec] = MappingProxyType(
    {
        Panel.FOUNDATION_ONE_CDX_V1: PanelSpec(
            footprint_mb=0.8,
            provenance="FoundationOne CDx, ~324 genes; public assay documentation",
            assay_version="v1",
        ),
        Panel.MSK_IMPACT_V468: PanelSpec(
            footprint_mb=1.5,
            provenance="MSK-IMPACT, 468-gene panel; public assay documentation",
            assay_version="468-gene",
        ),
    }
)

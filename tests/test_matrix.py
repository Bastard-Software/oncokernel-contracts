"""The mode x territory permission matrix, tested cell by cell.

|                  | genome_wide                  | panel >= 1.0 Mb        | subset |
|------------------|------------------------------|------------------------|--------|
| tumor_normal     | purity, ploidy, msi, tmb      | tmb only (panel)       | none   |
| tumor_only       | purity*, ploidy*, msi, tmb    | NOTHING - tmb forbidden| none   |

The two cells that matter most are the panel column: panel-derived TMB is legal
on the tumor/normal track and forbidden on tumor-only.
"""

import pytest
from pydantic import ValidationError

from oncokernel_contracts import (
    CaveatCode,
    GenomicProfile,
    MsiStatus,
    Panel,
    RegionsAnalysed,
    SampleMode,
    Territory,
    TmbMethod,
    limitation,
)
from oncokernel_contracts.fixtures import _VALIDATED

PANEL_BIG = RegionsAnalysed(kind=Territory.PANEL, panel=Panel.MSK_IMPACT_V468)
PANEL_SMALL = RegionsAnalysed(kind=Territory.PANEL, panel=Panel.FOUNDATION_ONE_CDX_V1)
SUBSET = RegionsAnalysed(kind=Territory.SUBSET, regions=("chr22",))
GW = RegionsAnalysed(kind=Territory.GENOME_WIDE)

TUMOR_ONLY_CAVEATS = (limitation(CaveatCode.TUMOR_ONLY_GERMLINE_UNSEPARATED),)


def build(mode, regions, **metrics):
    kwargs = {
        "sample_id": "OK-0001",
        "sample_mode": mode,
        "regions_analysed": regions,
        "provenance": _VALIDATED,
        **metrics,
    }
    if mode is SampleMode.TUMOR_ONLY:
        kwargs.setdefault("limitations", TUMOR_ONLY_CAVEATS)
    return GenomicProfile(**kwargs)


# --------------------------------------------------------------------------
# The panel column - the cells this whole rule exists for
# --------------------------------------------------------------------------


def test_panel_tmb_accepted_on_tumor_normal():
    profile = build(
        SampleMode.TUMOR_NORMAL, PANEL_BIG, tmb=11.2, tmb_method=TmbMethod.PANEL_DERIVED
    )
    assert profile.tmb == 11.2
    assert profile.tmb_method is TmbMethod.PANEL_DERIVED


def test_panel_tmb_rejected_on_tumor_only():
    """The single most important red test in the library.

    At a ~1 Mb footprint the true somatic count is on the order of ten variants,
    so retained private germline calls move a patient across the clinical
    threshold. Without a matched normal there is nothing to remove them.
    """
    with pytest.raises(ValidationError, match="tmb is not permitted"):
        build(SampleMode.TUMOR_ONLY, PANEL_BIG, tmb=11.2, tmb_method=TmbMethod.PANEL_DERIVED)


def test_sub_threshold_panel_rejected_even_on_tumor_normal():
    assert Panel.FOUNDATION_ONE_CDX_V1.footprint_mb < 1.0
    with pytest.raises(ValidationError, match="tmb is not permitted"):
        build(SampleMode.TUMOR_NORMAL, PANEL_SMALL, tmb=11.2, tmb_method=TmbMethod.PANEL_DERIVED)


@pytest.mark.parametrize("mode", list(SampleMode))
def test_panel_never_supports_genome_wide_metrics(mode):
    with pytest.raises(ValidationError, match="require genome-wide coverage"):
        build(mode, PANEL_BIG, tumor_purity=0.6)


# --------------------------------------------------------------------------
# The genome-wide column
# --------------------------------------------------------------------------


@pytest.mark.parametrize("mode", list(SampleMode))
def test_genome_wide_permits_every_metric(mode):
    profile = build(
        mode,
        GW,
        tumor_purity=0.6,
        ploidy=2.0,
        msi_status=MsiStatus.MSS,
        tmb=7.4,
        tmb_method=TmbMethod.GENOME_WIDE,
    )
    assert profile.tumor_purity == 0.6
    assert profile.tmb_method is TmbMethod.GENOME_WIDE


def test_tumor_only_reaches_tmb_only_through_genome_wide():
    """Genome-wide is the only route to TMB that the tumor-only track has."""
    profile = build(SampleMode.TUMOR_ONLY, GW, tmb=9.1, tmb_method=TmbMethod.GENOME_WIDE)
    assert profile.tmb == 9.1


# --------------------------------------------------------------------------
# The subset column - nothing is claimable
# --------------------------------------------------------------------------


@pytest.mark.parametrize("mode", list(SampleMode))
@pytest.mark.parametrize(
    ("field", "value"),
    [("tumor_purity", 0.6), ("ploidy", 2.0), ("msi_status", MsiStatus.MSS)],
)
def test_subset_forbids_genome_wide_metrics(mode, field, value):
    with pytest.raises(ValidationError, match="require genome-wide coverage"):
        build(mode, SUBSET, **{field: value})


@pytest.mark.parametrize("mode", list(SampleMode))
def test_subset_forbids_tmb(mode):
    with pytest.raises(ValidationError, match="tmb is not permitted"):
        build(mode, SUBSET, tmb=7.4, tmb_method=TmbMethod.GENOME_WIDE)


# --------------------------------------------------------------------------
# tmb_method consistency
# --------------------------------------------------------------------------


def test_tmb_requires_a_method():
    with pytest.raises(ValidationError, match="tmb requires an explicit tmb_method"):
        build(SampleMode.TUMOR_NORMAL, GW, tmb=7.4)


def test_method_without_tmb_rejected():
    with pytest.raises(ValidationError, match="tmb_method set without a tmb value"):
        build(SampleMode.TUMOR_NORMAL, GW, tmb_method=TmbMethod.GENOME_WIDE)


def test_method_must_match_territory():
    """A panel TMB labelled genome_wide would let downstream compare it to a WGS cut-off."""
    with pytest.raises(ValidationError, match="does not match territory"):
        build(SampleMode.TUMOR_NORMAL, PANEL_BIG, tmb=11.2, tmb_method=TmbMethod.GENOME_WIDE)
    with pytest.raises(ValidationError, match="does not match territory"):
        build(SampleMode.TUMOR_NORMAL, GW, tmb=7.4, tmb_method=TmbMethod.PANEL_DERIVED)

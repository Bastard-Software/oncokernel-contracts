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


# --------------------------------------------------------------------------
# The excluded column - genome-wide with holes in it
# --------------------------------------------------------------------------

#: 13.8% of a 3,031.0 Mb territory: the two lost arms and the lost chromosome of
#: a real matched normal, expanded to spans because the contract holds no lengths.
LOST_ARMS = ("chr6:0-60000000", "chr16:40000000-90000000", "chrX:0-156040895")
SURVIVING_BASES = 2_613_900_000

EXCLUDED_CAVEAT = limitation(CaveatCode.TERRITORY_PARTIALLY_EXCLUDED)


def partly_excluded(excluded=LOST_ARMS, analysed_bases=SURVIVING_BASES):
    return RegionsAnalysed(
        kind=Territory.GENOME_WIDE, excluded=excluded, analysed_bases=analysed_bases
    )


def test_an_exclusion_inside_the_ceiling_keeps_every_genome_wide_metric():
    """The reason this exists: a normal with lost arms must not cost four metrics."""
    profile = build(
        SampleMode.TUMOR_NORMAL,
        partly_excluded(),
        tumor_purity=1.0,
        ploidy=2.82,
        msi_status=MsiStatus.MSS,
        tmb=1.667,
        tmb_method=TmbMethod.GENOME_WIDE,
        limitations=(EXCLUDED_CAVEAT,),
    )

    assert profile.tmb == 1.667
    assert profile.tumor_purity == 1.0
    assert profile.regions_analysed.is_genome_wide
    assert profile.regions_analysed.analysed_bases == SURVIVING_BASES


def test_an_exclusion_over_the_ceiling_is_not_genome_wide():
    with pytest.raises(ValidationError, match="over the 20% ceiling"):
        partly_excluded(excluded=("chr1:0-1000000000",), analysed_bases=2_000_000_000)


def test_the_ceiling_is_a_fraction_of_the_whole_not_of_what_survived():
    """1,000 of 5,000 Mb is 20% and allowed; the same removal from 4,000 is not."""
    partly_excluded(excluded=("chr1:0-1000000000",), analysed_bases=4_000_000_000)

    with pytest.raises(ValidationError, match="ceiling"):
        partly_excluded(excluded=("chr1:0-1000000000",), analysed_bases=3_900_000_000)


def test_an_exclusion_without_a_surviving_denominator_is_refused():
    """A rate over an unstated denominator is not a rate."""
    with pytest.raises(ValidationError, match="require a positive analysed_bases"):
        RegionsAnalysed(kind=Territory.GENOME_WIDE, excluded=LOST_ARMS)


def test_a_denominator_without_an_exclusion_is_refused():
    """Nothing was removed, so the whole territory is the denominator already."""
    with pytest.raises(ValidationError, match="without any excluded regions"):
        RegionsAnalysed(kind=Territory.GENOME_WIDE, analysed_bases=SURVIVING_BASES)


@pytest.mark.parametrize(
    "span", ["chrX", "chr6:0", "chr6-60000000", "chr6:60000000-0", "chr6:100-100", ""]
)
def test_an_unusable_span_is_refused(span):
    with pytest.raises(ValidationError):
        partly_excluded(excluded=(span,))


def test_overlapping_exclusions_are_refused():
    """They double-count the removal, so the surviving fraction reads too high."""
    with pytest.raises(ValidationError, match="overlap on chr6"):
        partly_excluded(excluded=("chr6:0-60000000", "chr6:50000000-70000000"))


def test_exclusions_on_neighbouring_contigs_do_not_read_as_overlapping():
    partly_excluded(excluded=("chr6:0-60000000", "chr7:0-60000000"))


def test_abutting_exclusions_are_allowed():
    """Half-open, so one ending where the next begins removes each base once."""
    partly_excluded(excluded=("chr6:0-30000000", "chr6:30000000-60000000"))


@pytest.mark.parametrize("kind", [Territory.SUBSET, Territory.PANEL])
def test_a_restricted_territory_takes_no_exclusions(kind):
    """It states what it covered; what it left out is the whole complement."""
    shape = (
        {"regions": ("chr22",)} if kind is Territory.SUBSET else {"panel": Panel.MSK_IMPACT_V468}
    )
    with pytest.raises(ValidationError, match="neither excluded nor analysed_bases"):
        RegionsAnalysed(kind=kind, excluded=LOST_ARMS, analysed_bases=SURVIVING_BASES, **shape)


def test_an_excluded_territory_must_declare_itself_in_the_limitations():
    """Metrics survive an exclusion; silence about it does not."""
    with pytest.raises(ValidationError, match="TERRITORY_PARTIALLY_EXCLUDED"):
        build(SampleMode.TUMOR_NORMAL, partly_excluded(), tumor_purity=1.0)


def test_an_unexcluded_genome_wide_run_needs_no_such_caveat():
    """The regression guard for every existing caller."""
    profile = build(SampleMode.TUMOR_NORMAL, GW, tumor_purity=0.6)

    assert profile.regions_analysed.excluded == ()
    assert profile.limitations == ()

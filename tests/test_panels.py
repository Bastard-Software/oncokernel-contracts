"""The registry is code, not data: synchronous, I/O-free, exhaustively specified."""

import pytest
from pydantic import ValidationError

from oncokernel_contracts import TMB_FOOTPRINT_FLOOR_MB, Panel, RegionsAnalysed, Territory
from oncokernel_contracts.panels import _PANEL_SPECS


def test_every_member_has_a_spec():
    """A member without a spec would raise KeyError inside a validator at runtime."""
    for panel in Panel:
        assert panel in _PANEL_SPECS, f"{panel} has no registered spec"


def test_every_spec_is_fully_populated():
    for panel in Panel:
        spec = panel.spec
        assert spec.footprint_mb > 0, f"{panel} has a non-positive footprint"
        assert spec.provenance.strip(), f"{panel} has no recorded provenance"
        assert spec.assay_version.strip(), f"{panel} is not assay-versioned"


def test_lookup_performs_no_io(monkeypatch):
    """Break `open` and the registry keeps working — it is compiled in."""

    def explode(*args, **kwargs):
        raise AssertionError("panel lookup must not touch the filesystem")

    monkeypatch.setattr("builtins.open", explode)
    for panel in Panel:
        assert isinstance(panel.footprint_mb, float)
        assert isinstance(panel.supports_tmb, bool)


def test_threshold_is_megabases_not_gene_count():
    assert Panel.MSK_IMPACT_V468.footprint_mb >= TMB_FOOTPRINT_FLOOR_MB
    assert Panel.MSK_IMPACT_V468.supports_tmb is True

    assert Panel.FOUNDATION_ONE_CDX_V1.footprint_mb < TMB_FOOTPRINT_FLOOR_MB
    assert Panel.FOUNDATION_ONE_CDX_V1.supports_tmb is False


def test_panel_serialises_as_a_plain_string():
    """Keeps JSON Schema readable for non-Python consumers."""
    regions = RegionsAnalysed(kind=Territory.PANEL, panel=Panel.MSK_IMPACT_V468)
    assert regions.model_dump(mode="json")["panel"] == "msk_impact_v468"


def test_unregistered_panel_id_is_a_validation_error():
    """There is no path by which an unregistered panel produces a profile."""
    with pytest.raises(ValidationError):
        RegionsAnalysed(kind=Territory.PANEL, panel="some_vendor_panel_we_never_reviewed")


# --------------------------------------------------------------------------
# Territory shape rules
# --------------------------------------------------------------------------


def test_panel_territory_requires_a_panel():
    with pytest.raises(ValidationError, match="requires a registered panel"):
        RegionsAnalysed(kind=Territory.PANEL)


def test_genome_wide_takes_nothing_else():
    with pytest.raises(ValidationError, match="neither panel nor regions"):
        RegionsAnalysed(kind=Territory.GENOME_WIDE, panel=Panel.MSK_IMPACT_V468)


def test_subset_requires_regions():
    with pytest.raises(ValidationError, match="requires at least one region"):
        RegionsAnalysed(kind=Territory.SUBSET)

"""The dual-track safety mechanism: caveats that cannot be omitted."""

import pytest
from pydantic import ValidationError

from oncokernel_contracts import (
    CaveatCode,
    GenomicProfile,
    Limitation,
    SampleMode,
    ValidationStatus,
    limitation,
)
from oncokernel_contracts.fixtures import _UNVALIDATED, _VALIDATED
from oncokernel_contracts.limitations import DEFAULT_RENDERINGS
from oncokernel_contracts.regions import GENOME_WIDE


def build(mode, provenance, limitations=()):
    return GenomicProfile(
        sample_id="OK-0001",
        sample_mode=mode,
        regions_analysed=GENOME_WIDE,
        provenance=provenance,
        limitations=limitations,
    )


def test_tumor_only_with_empty_limitations_is_rejected():
    """Emptiness is not a valid state for the compromised track."""
    with pytest.raises(ValidationError, match="must carry limitations"):
        build(SampleMode.TUMOR_ONLY, _VALIDATED, ())


def test_tumor_only_must_name_the_germline_caveat_specifically():
    """Some other caveat is not a substitute for the one that defines the track."""
    with pytest.raises(ValidationError, match="TUMOR_ONLY_GERMLINE_UNSEPARATED"):
        build(SampleMode.TUMOR_ONLY, _VALIDATED, (limitation(CaveatCode.PURITY_FIT_DEGRADED),))


def test_tumor_only_with_its_caveat_is_accepted():
    profile = build(
        SampleMode.TUMOR_ONLY,
        _VALIDATED,
        (limitation(CaveatCode.TUMOR_ONLY_GERMLINE_UNSEPARATED),),
    )
    assert CaveatCode.TUMOR_ONLY_GERMLINE_UNSEPARATED in {i.code for i in profile.limitations}


def test_tumor_normal_may_have_no_caveats():
    """A clean gold-standard run should not be forced to invent a caveat."""
    profile = build(SampleMode.TUMOR_NORMAL, _VALIDATED, ())
    assert profile.limitations == ()


def test_unvalidated_resources_must_carry_its_caveat():
    with pytest.raises(ValidationError, match="RESOURCES_UNVALIDATED"):
        build(SampleMode.TUMOR_NORMAL, _UNVALIDATED, ())


def test_unvalidated_resources_with_its_caveat_is_accepted():
    profile = build(
        SampleMode.TUMOR_NORMAL, _UNVALIDATED, (limitation(CaveatCode.RESOURCES_UNVALIDATED),)
    )
    assert profile.provenance.validation_status is ValidationStatus.UNVALIDATED_RESOURCES
    assert not profile.provenance.is_validated


def test_rendering_is_filled_from_the_code():
    item = limitation(CaveatCode.PURITY_FIT_DEGRADED)
    assert item.rendering == DEFAULT_RENDERINGS[CaveatCode.PURITY_FIT_DEGRADED]
    assert item.rendering


def test_explicit_rendering_is_preserved():
    item = Limitation(code=CaveatCode.NOT_GENOME_WIDE, rendering="Custom wording.")
    assert item.rendering == "Custom wording."


def test_every_caveat_code_has_a_default_rendering():
    for code in CaveatCode:
        assert DEFAULT_RENDERINGS[code].strip(), f"{code} has no rendering"

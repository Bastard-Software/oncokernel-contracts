"""Identifier hygiene — the shapes direct identifiers actually take."""

import pytest
from pydantic import ValidationError

from oncokernel_contracts import GenomicProfile, IdentifierHygieneError, SampleMode
from oncokernel_contracts.fixtures import _VALIDATED
from oncokernel_contracts.identifiers import assert_pseudonymous
from oncokernel_contracts.regions import GENOME_WIDE

REJECTED = [
    pytest.param("85010112345", id="pesel"),
    pytest.param("pat_85010112345", id="pesel-after-underscore"),
    pytest.param("MRN-1985-01-01", id="date-of-birth-dashes"),
    pytest.param("pat_01.01.1985", id="date-of-birth-dots"),
    pytest.param("sample_1985/01/01", id="date-of-birth-slashes"),
    pytest.param("MRN123456789", id="long-digit-run"),
    pytest.param("Jan Kowalski", id="name-with-space"),
    pytest.param("  OK-0001  ", id="padded"),
    pytest.param("", id="empty"),
    pytest.param("   ", id="whitespace-only"),
]

ACCEPTED = ["OK-TN-0001", "a3f9c2", "sample-22-b", "OK_0001"]


@pytest.mark.parametrize("value", REJECTED)
def test_direct_identifier_shapes_are_rejected(value):
    with pytest.raises(IdentifierHygieneError):
        assert_pseudonymous(value, field="sample_id")


@pytest.mark.parametrize("value", ACCEPTED)
def test_pseudonyms_are_accepted(value):
    assert assert_pseudonymous(value) == value


def test_profile_rejects_an_mrn_shaped_sample_id():
    with pytest.raises(ValidationError):
        GenomicProfile(
            sample_id="85010112345",
            sample_mode=SampleMode.TUMOR_NORMAL,
            regions_analysed=GENOME_WIDE,
            provenance=_VALIDATED,
        )


def test_egress_identifier_is_a_uuid_not_a_string():
    """The strongest available guarantee: the type itself excludes a hospital id."""
    from oncokernel_contracts import PseudonymizedProfile

    annotation = PseudonymizedProfile.model_fields["sample_uuid"].annotation
    assert annotation.__name__ == "UUID"

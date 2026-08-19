"""The boundary: exhaustiveness, egress strictness, and what must not cross."""

import pytest
from pydantic import ValidationError

from oncokernel_contracts import (
    DROPPED_FIELDS,
    FIELD_DISPOSITION,
    MAPPED_FIELDS,
    TRANSFORMED_FIELDS,
    CaveatCode,
    GenomicProfile,
    PseudonymizedProfile,
    limitation,
    project,
)
from oncokernel_contracts.fixtures import SAMPLE_UUID, tumor_normal_genome_wide

# --------------------------------------------------------------------------
# (b) Omission - a new field nobody decided about
# --------------------------------------------------------------------------


def test_every_source_field_has_an_explicit_disposition():
    """Add a field to GenomicProfile without deciding its fate and this fails.

    `extra="forbid"` cannot catch this: nothing about Pydantic notices that a
    projection function ignored a field. Only this test does.
    """
    declared = set(GenomicProfile.model_fields)
    covered = set(FIELD_DISPOSITION)

    assert declared - covered == set(), (
        f"fields with no disposition decision: {sorted(declared - covered)} — "
        "decide whether each may leave the hospital, in the diff"
    )
    assert covered - declared == set(), (
        f"disposition table references fields that no longer exist: {sorted(covered - declared)}"
    )


def test_dispositions_partition_the_model():
    assert set(GenomicProfile.model_fields) == MAPPED_FIELDS | DROPPED_FIELDS | TRANSFORMED_FIELDS
    assert not (MAPPED_FIELDS & DROPPED_FIELDS)
    assert not (MAPPED_FIELDS & TRANSFORMED_FIELDS)
    assert not (DROPPED_FIELDS & TRANSFORMED_FIELDS)


def test_every_disposition_carries_a_reason():
    for name, (_, reason) in FIELD_DISPOSITION.items():
        assert reason.strip(), f"{name} has no recorded reason"


# --------------------------------------------------------------------------
# What must not cross
# --------------------------------------------------------------------------


def test_germline_and_paths_are_dropped():
    assert "germline_variants" in DROPPED_FIELDS
    assert "vcf_path" in DROPPED_FIELDS


def test_egress_model_has_no_germline_or_path_field():
    """Not merely unmapped — structurally absent from the egress shape."""
    egress = set(PseudonymizedProfile.model_fields)
    assert "germline_variants" not in egress
    assert "vcf_path" not in egress
    assert "sample_id" not in egress


def test_projection_drops_germline_from_a_real_profile():
    source = tumor_normal_genome_wide()
    assert source.germline_variants, "fixture must actually carry germline data to prove the drop"

    crossed = project(source, sample_uuid=SAMPLE_UUID)

    dumped = crossed.model_dump()
    assert "germline_variants" not in dumped
    assert "vcf_path" not in dumped
    assert "sample_id" not in dumped
    assert crossed.sample_uuid == SAMPLE_UUID


def test_projection_preserves_the_mapped_payload():
    source = tumor_normal_genome_wide()
    crossed = project(source, sample_uuid=SAMPLE_UUID)

    assert crossed.somatic_variants == source.somatic_variants
    assert crossed.tumor_purity == source.tumor_purity
    assert crossed.provenance == source.provenance
    assert crossed.sample_mode is source.sample_mode
    # the deliberate germline-derived exception
    assert crossed.hla_type == source.hla_type


# --------------------------------------------------------------------------
# (a) Smuggling - unknown keys arriving at the boundary
# --------------------------------------------------------------------------


@pytest.mark.parametrize("model", [PseudonymizedProfile, GenomicProfile])
def test_models_forbid_extra_fields_by_config(model):
    """Asserted on the config itself, so a refactor cannot quietly relax it."""
    assert model.model_config.get("extra") == "forbid"


def test_egress_model_is_frozen():
    """A payload mutable after validation is one whose validation proved nothing."""
    assert PseudonymizedProfile.model_config.get("frozen") is True


def test_unknown_key_is_rejected_at_the_boundary():
    source = tumor_normal_genome_wide()
    payload = project(source, sample_uuid=SAMPLE_UUID).model_dump()
    payload["patient_name"] = "Kowalski"

    with pytest.raises(ValidationError, match="patient_name"):
        PseudonymizedProfile(**payload)


def test_frozen_payload_cannot_be_mutated():
    crossed = project(tumor_normal_genome_wide(), sample_uuid=SAMPLE_UUID)
    with pytest.raises(ValidationError):
        crossed.tumor_purity = 0.99


def test_an_excluded_territory_crosses_the_boundary_intact():
    """A metric is a rate, and downstream cannot check the rate without the
    denominator. `regions_analysed` is MAPPED, so the exclusions travel with it —
    this pins that, because dropping them would leave a TMB nobody can interpret.
    """
    source = tumor_normal_genome_wide()
    partial = source.model_copy(
        update={
            "regions_analysed": source.regions_analysed.model_copy(
                update={
                    "excluded": ("chr6:0-60000000",),
                    "analysed_bases": 2_971_000_000,
                }
            ),
            "limitations": (limitation(CaveatCode.TERRITORY_PARTIALLY_EXCLUDED),),
        }
    )

    crossed = project(GenomicProfile.model_validate(partial.model_dump()), sample_uuid=SAMPLE_UUID)

    assert crossed.regions_analysed.excluded == ("chr6:0-60000000",)
    assert crossed.regions_analysed.analysed_bases == 2_971_000_000

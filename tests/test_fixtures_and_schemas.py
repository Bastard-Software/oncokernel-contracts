"""Fixtures are valid and cover both tracks; committed schemas match the models."""

import json

import pytest

from oncokernel_contracts import (
    CaveatCode,
    GenomicProfile,
    SampleMode,
    ValidationStatus,
    project,
)
from oncokernel_contracts.fixtures import ALL_FIXTURES, SAMPLE_UUID
from oncokernel_contracts.schemas import MODELS, check


@pytest.mark.parametrize("name", sorted(ALL_FIXTURES))
def test_fixture_builds_and_round_trips(name):
    profile = ALL_FIXTURES[name]()
    assert isinstance(profile, GenomicProfile)

    payload = profile.model_dump(mode="json")
    assert json.loads(json.dumps(payload)) == payload

    assert GenomicProfile.model_validate(payload) == profile


@pytest.mark.parametrize("name", sorted(ALL_FIXTURES))
def test_every_fixture_projects_cleanly(name):
    crossed = project(ALL_FIXTURES[name](), sample_uuid=SAMPLE_UUID)
    assert crossed.sample_uuid == SAMPLE_UUID


def test_fixtures_cover_both_tracks():
    """No consumer should build against only the gold-standard shape."""
    modes = {fixture().sample_mode for fixture in ALL_FIXTURES.values()}
    assert modes == set(SampleMode)


def test_fixtures_cover_the_quarantined_state():
    """M1 output is a wiring artefact; consumers must see that shape too."""
    unvalidated = [
        fixture()
        for fixture in ALL_FIXTURES.values()
        if fixture().provenance.validation_status is ValidationStatus.UNVALIDATED_RESOURCES
    ]
    assert unvalidated, "no fixture exercises unvalidated_resources"
    for profile in unvalidated:
        assert CaveatCode.RESOURCES_UNVALIDATED in {i.code for i in profile.limitations}


def test_committed_schemas_match_the_models():
    problems = check()
    assert not problems, (
        f"JSON Schema drift: {problems}. Run: python -m oncokernel_contracts.schemas"
    )


@pytest.mark.parametrize("model", MODELS, ids=lambda m: m.__name__)
def test_schema_generation_is_deterministic(model):
    assert model.model_json_schema() == model.model_json_schema()

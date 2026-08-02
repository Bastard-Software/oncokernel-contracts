"""The one-way projection from the on-prem profile to the egress payload.

Two mechanisms guard this boundary, and they are **not** interchangeable:

1. ``extra="forbid"`` on the egress model (see `profiles.py`) stops *smuggling* —
   unknown keys arriving where they do not belong, at runtime, in production.
2. The disposition table below stops *omission* — a field added to
   `GenomicProfile` that nobody decided about. Pydantic notices nothing here;
   only `tests/test_projection.py` does, at build time, in review.

Neither substitutes for the other. A new field on `GenomicProfile` cannot reach
a release without someone deciding, in a diff, whether it may leave the hospital.
"""

from collections.abc import Mapping
from enum import Enum, auto
from types import MappingProxyType
from uuid import UUID

from oncokernel_contracts.profiles import GenomicProfile, PseudonymizedProfile


class Disposition(Enum):
    """What the projection does with a given source field."""

    #: Copied across unchanged.
    MAPPED = auto()
    #: Crosses in a different form (e.g. sample_id -> sample_uuid).
    TRANSFORMED = auto()
    #: Deliberately does not cross. The reason is recorded in FIELD_DISPOSITION.
    DROPPED = auto()


#: Every field of `GenomicProfile` and what happens to it. Exhaustiveness is
#: asserted by tests — an unlisted field fails the suite.
FIELD_DISPOSITION: Mapping[str, tuple[Disposition, str]] = MappingProxyType(
    {
        "schema_version": (Disposition.MAPPED, "consumers may assert on it"),
        "sample_mode": (
            Disposition.MAPPED,
            "downstream must know which track produced this, or it cannot render caveats",
        ),
        "regions_analysed": (
            Disposition.MAPPED,
            "downstream must know what territory a metric is entitled to describe",
        ),
        "somatic_variants": (Disposition.MAPPED, "the payload"),
        "tumor_purity": (Disposition.MAPPED, "gated by territory"),
        "ploidy": (Disposition.MAPPED, "gated by territory"),
        "tmb": (Disposition.MAPPED, "gated by territory and mode"),
        "tmb_method": (
            Disposition.MAPPED,
            "so a panel TMB can never be compared against a WGS cut-off",
        ),
        "msi_status": (Disposition.MAPPED, "gated by territory"),
        "hla_type": (
            Disposition.MAPPED,
            "DELIBERATE germline-derived exception: required downstream for "
            "immunotherapy reasoning, crosses as a type call not variant records",
        ),
        "provenance": (Disposition.MAPPED, "the audit trail travels with the payload"),
        "limitations": (
            Disposition.MAPPED,
            "the only thing standing between a compromised profile and a dashboard "
            "that renders it as gold-standard",
        ),
        "sample_id": (
            Disposition.TRANSFORMED,
            "hospital pseudonym becomes an opaque UUID at the boundary",
        ),
        "vcf_path": (
            Disposition.DROPPED,
            "a hospital filesystem path either leaks infrastructure detail or implies "
            "the consumer opens the file; neither is acceptable",
        ),
        "germline_variants": (
            Disposition.DROPPED,
            "germline variants are the most durably identifying data in the pipeline, "
            "do not change over a lifetime, and implicate blood relatives",
        ),
    }
)

#: Convenience views, used by tests and by anyone auditing the boundary.
MAPPED_FIELDS = frozenset(
    name for name, (d, _) in FIELD_DISPOSITION.items() if d is Disposition.MAPPED
)
DROPPED_FIELDS = frozenset(
    name for name, (d, _) in FIELD_DISPOSITION.items() if d is Disposition.DROPPED
)
TRANSFORMED_FIELDS = frozenset(
    name for name, (d, _) in FIELD_DISPOSITION.items() if d is Disposition.TRANSFORMED
)


def project(profile: GenomicProfile, *, sample_uuid: UUID) -> PseudonymizedProfile:
    """Project an on-prem profile onto the payload that may cross the boundary.

    The `sample_uuid` is supplied by the caller because pseudonymization is the
    hospital's act, not this library's: the re-identification mapping lives
    on-prem and never enters this codebase.
    """
    payload = {name: getattr(profile, name) for name in MAPPED_FIELDS}
    return PseudonymizedProfile(sample_uuid=sample_uuid, **payload)

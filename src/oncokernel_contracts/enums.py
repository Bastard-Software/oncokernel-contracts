"""Closed vocabularies shared across every OncoKernel service.

All of these are `StrEnum`, so they serialise as plain strings on the wire and
appear in JSON Schema as string enums that a non-Python consumer can read.
"""

from enum import StrEnum


class SampleMode(StrEnum):
    """The clinical track a profile was produced on.

    `TUMOR_NORMAL` is the baseline. `TUMOR_ONLY` is a supported but structurally
    compromised fallback — it triggers stricter rules elsewhere in this library.
    """

    TUMOR_NORMAL = "tumor_normal"
    TUMOR_ONLY = "tumor_only"


class Territory(StrEnum):
    """What genomic territory the analysis actually covered."""

    GENOME_WIDE = "genome_wide"
    PANEL = "panel"
    SUBSET = "subset"


class TmbMethod(StrEnum):
    """How a TMB value was derived. Never let these two be compared to one another."""

    GENOME_WIDE = "genome_wide"
    PANEL_DERIVED = "panel_derived"


class MsiStatus(StrEnum):
    MSI = "MSI"
    MSS = "MSS"


class ValidationStatus(StrEnum):
    """Whether the run used licensed reference resources or public substitutes."""

    UNVALIDATED_RESOURCES = "unvalidated_resources"
    VALIDATED = "validated"


class CaveatCode(StrEnum):
    """Machine-readable limitations. Consumers are expected to render these."""

    TUMOR_ONLY_GERMLINE_UNSEPARATED = "TUMOR_ONLY_GERMLINE_UNSEPARATED"
    PURITY_FIT_DEGRADED = "PURITY_FIT_DEGRADED"
    RESOURCES_UNVALIDATED = "RESOURCES_UNVALIDATED"
    NOT_GENOME_WIDE = "NOT_GENOME_WIDE"
    TERRITORY_PARTIALLY_EXCLUDED = "TERRITORY_PARTIALLY_EXCLUDED"
    ORACLES_BYPASSED = "ORACLES_BYPASSED"
    ORACLES_FAILED = "ORACLES_FAILED"
    GENE_ANNOTATION_UNAVAILABLE = "GENE_ANNOTATION_UNAVAILABLE"

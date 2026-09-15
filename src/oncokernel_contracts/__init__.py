"""OncoKernel shared data contracts — the typed spine every service speaks.

This library carries **invariants, not just shapes**. Importing a model gets you
the rules with it: what may cross the hospital boundary, which metrics a given
analysis is entitled to claim, and what an identifier may look like.

No I/O. No business logic. Pydantic v2 and the standard library only, so it
imports cleanly on an on-prem hospital box, a GPU cloud node, and a public-cloud
web service alike.
"""

from oncokernel_contracts.enums import (
    CaveatCode,
    GeneModelSource,
    MsiStatus,
    SampleMode,
    Territory,
    TmbMethod,
    ValidationStatus,
)
from oncokernel_contracts.identifiers import IdentifierHygieneError, assert_pseudonymous
from oncokernel_contracts.limitations import (
    DEFAULT_RENDERINGS,
    Limitation,
    codes,
    limitation,
)
from oncokernel_contracts.panels import TMB_FOOTPRINT_FLOOR_MB, Panel, PanelSpec
from oncokernel_contracts.profiles import GenomicProfile, PseudonymizedProfile
from oncokernel_contracts.projection import (
    DROPPED_FIELDS,
    FIELD_DISPOSITION,
    MAPPED_FIELDS,
    TRANSFORMED_FIELDS,
    Disposition,
    project,
)
from oncokernel_contracts.provenance import GeneModel, Provenance
from oncokernel_contracts.regions import GENOME_WIDE, MAX_EXCLUDED_FRACTION, RegionsAnalysed
from oncokernel_contracts.variants import Variant
from oncokernel_contracts.version import SCHEMA_VERSION, __version__

__all__ = [
    "DEFAULT_RENDERINGS",
    "DROPPED_FIELDS",
    "FIELD_DISPOSITION",
    "GENOME_WIDE",
    "MAPPED_FIELDS",
    "MAX_EXCLUDED_FRACTION",
    "SCHEMA_VERSION",
    "TMB_FOOTPRINT_FLOOR_MB",
    "TRANSFORMED_FIELDS",
    "CaveatCode",
    "Disposition",
    "GeneModel",
    "GeneModelSource",
    "GenomicProfile",
    "IdentifierHygieneError",
    "Limitation",
    "MsiStatus",
    "Panel",
    "PanelSpec",
    "Provenance",
    "PseudonymizedProfile",
    "RegionsAnalysed",
    "SampleMode",
    "Territory",
    "TmbMethod",
    "ValidationStatus",
    "Variant",
    "__version__",
    "assert_pseudonymous",
    "codes",
    "limitation",
    "project",
]

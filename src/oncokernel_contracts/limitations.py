"""The caveat block — the dual-track safety mechanism.

The two clinical tracks emit structurally identical JSON apart from one field,
which is precisely the confusion this library exists to prevent: a tumor-only
profile rendered in the dashboard as though it were gold-standard.

So limitations are machine-readable codes rather than free text, they are
required on egress, and an empty list is not a valid state for the tumor-only
track. Consumers are expected to render them; this library's job is to make them
impossible to omit.
"""

from collections.abc import Mapping
from types import MappingProxyType

from pydantic import BaseModel, ConfigDict, model_validator

from oncokernel_contracts.enums import CaveatCode

#: Default human-readable rendering per code. Consumers may localise these, but
#: the code is the contract and the wording travels with it so that two services
#: cannot describe the same limitation differently.
DEFAULT_RENDERINGS: Mapping[CaveatCode, str] = MappingProxyType(
    {
        CaveatCode.TUMOR_ONLY_GERMLINE_UNSEPARATED: (
            "No matched normal was sequenced. Somatic and germline variants could not be "
            "cleanly separated; rare private germline variants may appear as somatic findings."
        ),
        CaveatCode.PURITY_FIT_DEGRADED: (
            "Tumor purity and ploidy were fitted without a matched normal and are less "
            "well constrained than on the tumor/normal track."
        ),
        CaveatCode.RESOURCES_UNVALIDATED: (
            "This run used public substitute reference resources, not the licensed clinical "
            "bundle. Output is a wiring artefact and must not be used clinically."
        ),
        CaveatCode.NOT_GENOME_WIDE: (
            "Analysis covered a restricted territory. Genome-wide metrics are not reported."
        ),
    }
)


class Limitation(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    code: CaveatCode
    rendering: str

    @model_validator(mode="before")
    @classmethod
    def _fill_default_rendering(cls, data: object) -> object:
        """Supply the canonical wording when a caller gives only the code.

        Runs before construction so the model stays genuinely frozen — no
        post-validation mutation of a supposedly immutable payload.
        """
        if isinstance(data, dict) and not data.get("rendering"):
            code = data.get("code")
            try:
                resolved = CaveatCode(code)
            except ValueError:
                return data  # let normal validation report the bad code
            return {**data, "rendering": DEFAULT_RENDERINGS[resolved]}
        return data


def limitation(code: CaveatCode) -> Limitation:
    """Build a limitation with its default rendering."""
    return Limitation(code=code)


def codes(limitations: tuple[Limitation, ...]) -> frozenset[CaveatCode]:
    return frozenset(item.code for item in limitations)

"""Run provenance, captured at emit time.

Platform hardening requires an immutable audit log of what ran, when, and
against which resource versions. Provenance not captured at emit time is
unrecoverable — you cannot retrofit an audit trail onto a profile written six
months ago. Cheap now, impossible later.

`engine` and `resource_bundle` are **independent axes** on purpose. A run can be
`oncoanalyser` (engine) on public substitute resources (bundle); one field
cannot express both, and conflating them makes the tag lie exactly when the
resource swap matters.
"""

from pydantic import BaseModel, ConfigDict, Field

from oncokernel_contracts.enums import ValidationStatus

PUBLIC_UNVALIDATED_PREFIX = "public-unvalidated"


class Provenance(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    engine: str = Field(description="e.g. 'sage-minimal' or 'oncoanalyser@2.3.0'")
    resource_bundle: str = Field(
        description="e.g. 'public-unvalidated@<manifest-hash>' or 'hmf@<version>'"
    )
    validation_status: ValidationStatus
    pipeline_git_sha: str
    tool_versions: dict[str, str] = Field(default_factory=dict)
    container_digests: dict[str, str] = Field(default_factory=dict)

    @property
    def is_validated(self) -> bool:
        return self.validation_status is ValidationStatus.VALIDATED

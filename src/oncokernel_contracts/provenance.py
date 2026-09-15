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

from oncokernel_contracts.enums import GeneModelSource, ValidationStatus

PUBLIC_UNVALIDATED_PREFIX = "public-unvalidated"


class GeneModel(BaseModel):
    """The catalogue release that minted a profile's transcript ids.

    A bare transcript id is not a coordinate. `ENST00000646891` is `.1` in
    Ensembl 103 and `.2` in Ensembl 115, and PAVE emits them unversioned, so a
    consumer resolving transcript to protein to residue without the release
    silently uses whichever one it happens to hold. That failure draws the wrong
    residue and looks entirely plausible doing it.

    `annotator` is the tool that assigned the transcripts, not the tool that
    called the variants: two runs of the same caller against different PAVE
    versions can disagree about which transcript is canonical.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    source: GeneModelSource
    release: str = Field(min_length=1, description="catalogue release, e.g. '110'")
    assembly: str = Field(min_length=1, description="e.g. 'GRCh38'")
    annotator: str = Field(
        min_length=1, description="tool that assigned the transcripts, e.g. 'pave@1.9'"
    )


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

    #: The catalogue behind `Variant.transcript`. Optional because a run that
    #: annotated nothing has no gene model to declare; `_ProfileBase` requires it
    #: as soon as any variant carries a transcript.
    gene_model: GeneModel | None = None

    @property
    def is_validated(self) -> bool:
        return self.validation_status is ValidationStatus.VALIDATED

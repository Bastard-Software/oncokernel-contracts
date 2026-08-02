# Panel registry

Defined in [`src/oncokernel_contracts/panels.py`](../src/oncokernel_contracts/panels.py) as a `StrEnum` plus a frozen `PanelSpec` mapping. Compiled into the library; no file or network access at validation time.

## Registered panels

> ⚠️ Both entries are seeded for test coverage. Footprint figures are taken from public assay documentation and have **not** been through clinical sign-off. No production profile should claim `panel_derived` TMB until the figure is confirmed and the sign-off column below is filled in.

| Member | Value | Footprint (Mb) | `supports_tmb` | Assay version | Source | Signed off | Date |
|---|---|---|---|---|---|---|---|
| `FOUNDATION_ONE_CDX_V1` | `foundation_one_cdx_v1` | 0.8 | `False` | v1 | Public assay documentation, ~324 genes | — | — |
| `MSK_IMPACT_V468` | `msk_impact_v468` | 1.5 | `True` | 468-gene | Public assay documentation | — | — |

## TMB eligibility

`Panel.supports_tmb` is `footprint_mb >= TMB_FOOTPRINT_FLOOR_MB` (1.0).

Eligibility is necessary but not sufficient. `panel_derived` TMB additionally requires `sample_mode == tumor_normal` — see [Validation rules](validation-rules.md#metric-permission-matrix).

The threshold is measured in megabases of coding territory, not gene count.

## Adding a panel

1. Add a member to `Panel` with an assay-versioned name (`VENDOR_ASSAY_V2`).
2. Add its `PanelSpec` to `_PANEL_SPECS`: `footprint_mb`, `provenance`, `assay_version`.
3. Add a row to the table above, including the source and the name of whoever signed off the footprint.
4. Regenerate schemas: `python -m oncokernel_contracts.schemas`.
5. Release a new version; consumers must bump to use the new member.

## Enforced by tests

`tests/test_panels.py` fails if any member:

- has no entry in `_PANEL_SPECS`
- has a non-positive `footprint_mb`
- has an empty `provenance` or `assay_version`

It also asserts that lookup performs no filesystem access.

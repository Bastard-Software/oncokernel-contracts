"""Library and schema versions.

`SCHEMA_VERSION` travels on every payload. Consumers pin a library version and
may assert on the schema version they were built against; changes are additive
by default, and a breaking change requires a major bump plus a migration note in
`docs/migrations.md`.
"""

__version__ = "0.1.0"

SCHEMA_VERSION = "1.0.0"

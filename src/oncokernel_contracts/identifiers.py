"""Identifier hygiene.

The pipeline accepts an *already pseudonymized* sample identifier. This module
asserts that shape. It cannot prove an identifier is a pseudonym — nothing can —
but it can reject the shapes that direct identifiers actually take, which is
what catches the realistic accident: a hospital LIMS export where the normal
sample is labelled with the patient's own record number.

Getting this wrong is a notifiable incident, not a bug. The assertion is cheaper
than the alternative.
"""

import re

# Note on boundaries: these use digit-lookarounds rather than `\b`. `_` is a word
# character, so `\b` does NOT match between `_` and a digit — which would let
# `pat_01.01.1985` through, precisely the shape a LIMS export produces.

# 11 consecutive digits — the Polish PESEL national identifier.
_PESEL = re.compile(r"(?<!\d)\d{11}(?!\d)")

# Long digit runs — medical record numbers, national identifiers, insurance ids.
_LONG_DIGIT_RUN = re.compile(r"\d{9,}")

# Dates in the formats a hospital export realistically uses.
_DATE_LIKE = re.compile(
    r"(?<!\d)("
    r"\d{4}[-/.]\d{1,2}[-/.]\d{1,2}"  # 1970-01-01, 1970/01/01
    r"|\d{1,2}[-/.]\d{1,2}[-/.]\d{4}"  # 01.01.1970, 01/01/1970
    r")(?!\d)"
)


class IdentifierHygieneError(ValueError):
    """Raised when a value looks like a direct identifier rather than a pseudonym."""


def assert_pseudonymous(value: str, *, field: str = "identifier") -> str:
    """Reject values shaped like direct identifiers. Returns the value unchanged."""
    if not value or not value.strip():
        raise IdentifierHygieneError(f"{field} must not be empty")

    if value != value.strip():
        raise IdentifierHygieneError(f"{field} must not have leading/trailing whitespace")

    if " " in value:
        # Free text in an identifier field is how names arrive.
        raise IdentifierHygieneError(f"{field} must not contain spaces (got {value!r})")

    if _PESEL.search(value):
        raise IdentifierHygieneError(f"{field} looks like a PESEL national identifier")

    if _DATE_LIKE.search(value):
        raise IdentifierHygieneError(f"{field} contains a date — possible date of birth")

    if _LONG_DIGIT_RUN.search(value):
        raise IdentifierHygieneError(
            f"{field} contains a run of 9+ digits — possible MRN or national identifier"
        )

    return value

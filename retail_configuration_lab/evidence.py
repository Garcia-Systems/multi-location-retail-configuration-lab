"""The controlled evidence vocabulary used throughout the lab."""

from enum import StrEnum


class EvidenceCategory(StrEnum):
    """Classifies where a claim comes from and what it can establish."""

    MODELED_ASSUMPTION = "MODELED ASSUMPTION"
    OBSERVED_LAB_RESULT = "OBSERVED LAB RESULT"
    OBSERVED_IMPLEMENTATION_STRUCTURE = "OBSERVED IMPLEMENTATION STRUCTURE"
    SENSITIVITY_ASSUMPTION = "SENSITIVITY ASSUMPTION"
    MODELED_ALTERNATIVE_ASSUMPTION = "MODELED ALTERNATIVE ASSUMPTION"


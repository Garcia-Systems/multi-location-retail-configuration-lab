"""Executable configuration-first retail lab."""

from .baseline import assess, load_baseline
from .models import BaselineAssessment, BaselineCase, BaselineValidationError

__all__ = [
    "BaselineAssessment",
    "BaselineCase",
    "BaselineValidationError",
    "assess",
    "load_baseline",
]


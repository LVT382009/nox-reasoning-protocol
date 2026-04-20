"""
NOX Type System - Uncertainty and Safety Types

This module defines the type system for NOX, which encodes uncertainty
and safety constraints at the type level to prevent illegal rewrites.
"""

from enum import Enum
from dataclasses import dataclass
from typing import Optional, Set


class UncertaintyType(Enum):
    """Uncertainty types for reasoning components."""
    CERTAIN = "Certain"
    PROBABLE = "Probable"
    HYPOTHETICAL = "Hypothetical"
    VERIFIED = "Verified"
    UNVERIFIED = "Unverified"
    PRESERVED = "Preserved"
    IMMUTABLE = "Immutable"


@dataclass
class TypeConstraints:
    """Constraints on type transformations."""
    can_downgrade_certainty: bool = False
    can_upgrade_certainty: bool = False
    can_lose_verification: bool = False
    can_modify_immutable: bool = False
    allowed_transformations: Set[str] = None

    def __post_init__(self):
        if self.allowed_transformations is None:
            self.allowed_transformations = set()


# Type preservation rules
TYPE_PRESERVATION_RULES = {
    # Certainty cannot be downgraded
    (UncertaintyType.CERTAIN, UncertaintyType.CERTAIN): True,
    (UncertaintyType.CERTAIN, UncertaintyType.PROBABLE): False,
    (UncertaintyType.CERTAIN, UncertaintyType.HYPOTHETICAL): False,
    
    # Hypothetical cannot become certain
    (UncertaintyType.HYPOTHETICAL, UncertaintyType.HYPOTHETICAL): True,
    (UncertaintyType.HYPOTHETICAL, UncertaintyType.CERTAIN): False,
    
    # Verification cannot be lost
    (UncertaintyType.VERIFIED, UncertaintyType.VERIFIED): True,
    (UncertaintyType.VERIFIED, UncertaintyType.UNVERIFIED): False,
    
    # Preserved must stay preserved
    (UncertaintyType.PRESERVED, UncertaintyType.PRESERVED): True,
    
    # Immutable cannot be modified
    (UncertaintyType.IMMUTABLE, UncertaintyType.IMMUTABLE): True,
}


def type_preservation_allowed(
    original: UncertaintyType,
    transformed: UncertaintyType
) -> bool:
    """
    Check if type transformation is allowed.
    
    Args:
        original: Original uncertainty type
        transformed: Transformed uncertainty type
    
    Returns:
        True if transformation is allowed, False otherwise
    """
    return TYPE_PRESERVATION_RULES.get(
        (original, transformed),
        False
    )


def extract_uncertainty_types(expr) -> Set[UncertaintyType]:
    """
    Extract all uncertainty types from an expression.
    
    Args:
        expr: Expression to extract types from
    
    Returns:
        Set of uncertainty types found in expression
    """
    types = set()
    
    # This will be implemented based on AST structure
    # For now, return empty set
    return types


def apply_uncertainty_qualifier(
    text: str,
    uncertainty: UncertaintyType
) -> str:
    """
    Apply uncertainty qualifier to text.
    
    Args:
        text: Base text
        uncertainty: Uncertainty type
    
    Returns:
        Text with uncertainty qualifier applied
    """
    qualifiers = {
        UncertaintyType.CERTAIN: "",
        UncertaintyType.PROBABLE: "probably ",
        UncertaintyType.HYPOTHETICAL: "hypothetically ",
        UncertaintyType.VERIFIED: "verified ",
        UncertaintyType.UNVERIFIED: "allegedly ",
        UncertaintyType.PRESERVED: "preserved ",
        UncertaintyType.IMMUTABLE: "immutable ",
    }
    
    qualifier = qualifiers.get(uncertainty, "")
    return f"{qualifier}{text}"


@dataclass
class TypeViolation:
    """Represents a type system violation."""
    original_type: UncertaintyType
    transformed_type: UncertaintyType
    reason: str
    location: str


def check_type_preservation(
    original_expr,
    transformed_expr
) -> tuple[bool, list[TypeViolation]]:
    """
    Check that types are preserved between expressions.
    
    Args:
        original_expr: Original expression
        transformed_expr: Transformed expression
    
    Returns:
        Tuple of (passed, violations)
    """
    # Extract types from both expressions
    orig_types = extract_uncertainty_types(original_expr)
    trans_types = extract_uncertainty_types(transformed_expr)
    
    violations = []
    
    # Check each type transformation
    for orig_type, trans_type in zip(orig_types, trans_types):
        if not type_preservation_allowed(orig_type, trans_type):
            violations.append(TypeViolation(
                original_type=orig_type,
                transformed_type=trans_type,
                reason=f"Cannot transform {orig_type.value} to {trans_type.value}",
                location="expression"
            ))
    
    return len(violations) == 0, violations

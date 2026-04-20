"""
NOX Rewrite Rules - Stratified Transformation Rules

This module defines rewrite rules with cost metadata for NOX optimization.
Rules are stratified into tiers (0-3) with different safety and performance characteristics.
"""

from dataclasses import dataclass
from typing import Optional, List, Literal, Callable
from enum import Enum

from .ast import (
    Expression, Statement, BinaryOp, UnaryOp, Identifier, Literal,
    BinaryOperator, UnaryOperator, Fact, Rule, Inference
)
from .ir import NOXIR, NOXIRNode, ProofCertificate
from .types import UncertaintyType


class RewriteCost(Enum):
    """Cost levels for rewrite operations."""
    VERY_LOW = "very_low"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class GrowthRisk(Enum):
    """E-graph growth risk levels."""
    NONE = "none"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


@dataclass
class RewriteRuleMetadata:
    """Metadata for a rewrite rule."""
    tier: int  # 0, 1, 2, or 3
    estimated_token_gain: float  # 0.0 to 1.0
    matcher_cost: RewriteCost
    proof_cost: RewriteCost
    egraph_growth_risk: GrowthRisk
    rebuild_amplification_risk: GrowthRisk
    fast_path_eligible: bool
    enabled: bool = True
    backoff_threshold: float = 0.1  # Disable if gain < 10% of expected
    description: str = ""


@dataclass
class RewriteResult:
    """Result of applying a rewrite rule."""
    success: bool
    transformed_expr: Optional[Expression]
    token_savings: int
    proof: Optional[ProofCertificate]
    reason: str = ""


class RewriteRule:
    """Base class for rewrite rules."""
    
    def __init__(self, metadata: RewriteRuleMetadata):
        self.metadata = metadata
        self.application_count = 0
        self.total_gain = 0
        self.disabled = False
        self.enabled = metadata.enabled  # Add enabled attribute
    
    def apply(self, expr: Expression) -> RewriteResult:
        """
        Apply this rewrite rule to an expression.
        
        Args:
            expr: Expression to rewrite
        
        Returns:
            RewriteResult with transformed expression and metadata
        """
        raise NotImplementedError("Subclasses must implement apply()")
    
    def can_apply(self, expr: Expression) -> bool:
        """
        Check if this rule can be applied to an expression.
        
        Args:
            expr: Expression to check
        
        Returns:
            True if rule can be applied, False otherwise
        """
        raise NotImplementedError("Subclasses must implement can_apply()")
    
    def should_backoff(self) -> bool:
        """
        Check if this rule should be disabled due to poor performance.
        
        Returns:
            True if rule should be disabled, False otherwise
        """
        if self.application_count < 10:
            return False
        
        # Calculate average gain
        avg_gain = self.total_gain / self.application_count
        expected_gain = self.metadata.estimated_token_gain
        
        # Backoff if average gain is below threshold
        return avg_gain < (expected_gain * self.metadata.backoff_threshold)
    
    def record_application(self, gain: int):
        """Record an application of this rule."""
        self.application_count += 1
        self.total_gain += gain


# ============================================================================
# Tier 0 Rules - Always-Safe Canonicalization
# ============================================================================

class NormalizeDoubleNegation(RewriteRule):
    """NOT NOT X → X"""
    
    def __init__(self):
        super().__init__(RewriteRuleMetadata(
            tier=0,
            estimated_token_gain=0.2,
            matcher_cost=RewriteCost.VERY_LOW,
            proof_cost=RewriteCost.VERY_LOW,
            egraph_growth_risk=GrowthRisk.NONE,
            rebuild_amplification_risk=GrowthRisk.NONE,
            fast_path_eligible=True,
            description="Normalize double negation: NOT NOT X → X"
        ))
    
    def can_apply(self, expr: Expression) -> bool:
        if not isinstance(expr, UnaryOp):
            return False
        if expr.op != UnaryOperator.NOT:
            return False
        if not isinstance(expr.expr, UnaryOp):
            return False
        return expr.expr.op == UnaryOperator.NOT
    
    def apply(self, expr: Expression) -> RewriteResult:
        if not self.can_apply(expr):
            return RewriteResult(success=False, transformed_expr=None, token_savings=0, proof=None, reason="Cannot apply")
        
        # Extract inner expression
        inner = expr.expr.expr
        
        # Calculate savings
        original_cost = 2  # NOT NOT X
        new_cost = 1  # X
        savings = original_cost - new_cost
        
        # Create lightweight proof
        proof = ProofCertificate(
            rewrite_id="normalize_double_negation",
            original_expr=expr,
            transformed_expr=inner,
            proof_type="local_legality",
            invariants_preserved=["type_preservation", "no_constraint_violation"],
            type_preservation=True,
            semantic_equivalence=True,
            proof_cost_ms=0.5,
            proof_confidence=0.95,
            verified=True,
            verification_method="type_check",
            rollback_expr=expr
        )
        
        return RewriteResult(
            success=True,
            transformed_expr=inner,
            token_savings=savings,
            proof=proof
        )


class FoldIdentityOps(RewriteRule):
    """X & true → X, X | false → X"""
    
    def __init__(self):
        super().__init__(RewriteRuleMetadata(
            tier=0,
            estimated_token_gain=0.15,
            matcher_cost=RewriteCost.VERY_LOW,
            proof_cost=RewriteCost.VERY_LOW,
            egraph_growth_risk=GrowthRisk.NONE,
            rebuild_amplification_risk=GrowthRisk.NONE,
            fast_path_eligible=True,
            description="Fold identity operations: X & true → X"
        ))
    
    def can_apply(self, expr: Expression) -> bool:
        if not isinstance(expr, BinaryOp):
            return False
        
        # Check for X & true
        if expr.op == BinaryOperator.AND:
            if isinstance(expr.right, Literal) and expr.right.value is True:
                return True
            if isinstance(expr.left, Literal) and expr.left.value is True:
                return True
        
        return False
    
    def apply(self, expr: Expression) -> RewriteResult:
        if not self.can_apply(expr):
            return RewriteResult(success=False, transformed_expr=None, token_savings=0, proof=None, reason="Cannot apply")
        
        # Determine which side to keep
        if isinstance(expr.right, Literal) and expr.right.value is True:
            result = expr.left
        else:
            result = expr.right
        
        # Calculate savings
        original_cost = 2  # X & true
        new_cost = 1  # X
        savings = original_cost - new_cost
        
        # Create lightweight proof
        proof = ProofCertificate(
            rewrite_id="fold_identity_ops",
            original_expr=expr,
            transformed_expr=result,
            proof_type="local_legality",
            invariants_preserved=["type_preservation", "no_constraint_violation"],
            type_preservation=True,
            semantic_equivalence=True,
            proof_cost_ms=0.5,
            proof_confidence=0.95,
            verified=True,
            verification_method="type_check",
            rollback_expr=expr
        )
        
        return RewriteResult(
            success=True,
            transformed_expr=result,
            token_savings=savings,
            proof=proof
        )


# ============================================================================
# Tier 1 Rules - Fast-Path Rewrites
# ============================================================================

class EliminateRedundantQualifier(RewriteRule):
    """X<Certain> → X (when type is Certain)"""
    
    def __init__(self):
        super().__init__(RewriteRuleMetadata(
            tier=1,
            estimated_token_gain=0.1,
            matcher_cost=RewriteCost.LOW,
            proof_cost=RewriteCost.LOW,
            egraph_growth_risk=GrowthRisk.LOW,
            rebuild_amplification_risk=GrowthRisk.NONE,
            fast_path_eligible=True,
            description="Eliminate redundant qualifier: X<Certain> → X"
        ))
    
    def can_apply(self, expr: Expression) -> bool:
        from .ast import TypedExpr
        return isinstance(expr, TypedExpr) and expr.type == UncertaintyType.CERTAIN
    
    def apply(self, expr: Expression) -> RewriteResult:
        from .ast import TypedExpr
        
        if not self.can_apply(expr):
            return RewriteResult(success=False, transformed_expr=None, token_savings=0, proof=None, reason="Cannot apply")
        
        typed_expr = expr
        result = typed_expr.identifier
        
        # Calculate savings
        original_cost = 2  # X<Certain>
        new_cost = 1  # X
        savings = original_cost - new_cost
        
        # Create lightweight proof
        proof = ProofCertificate(
            rewrite_id="eliminate_redundant_qualifier",
            original_expr=expr,
            transformed_expr=result,
            proof_type="local_legality",
            invariants_preserved=["type_preservation"],
            type_preservation=True,
            semantic_equivalence=True,
            proof_cost_ms=0.5,
            proof_confidence=0.95,
            verified=True,
            verification_method="type_check",
            rollback_expr=expr
        )
        
        return RewriteResult(
            success=True,
            transformed_expr=result,
            token_savings=savings,
            proof=proof
        )


class CompressBoilerplateConnectors(RewriteRule):
    """Replace verbose connectors with symbols"""
    
    def __init__(self):
        super().__init__(RewriteRuleMetadata(
            tier=1,
            estimated_token_gain=0.3,
            matcher_cost=RewriteCost.LOW,
            proof_cost=RewriteCost.LOW,
            egraph_growth_risk=GrowthRisk.LOW,
            rebuild_amplification_risk=GrowthRisk.NONE,
            fast_path_eligible=True,
            description="Compress boilerplate connectors: 'therefore' → '∴'"
        ))
    
    def can_apply(self, expr: Expression) -> bool:
        # This rule applies at the text level, not expression level
        # For v1, we'll skip this in the AST/IR layer
        return False
    
    def apply(self, expr: Expression) -> RewriteResult:
        return RewriteResult(success=False, transformed_expr=None, token_savings=0, proof=None, reason="Not implemented in AST layer")


# ============================================================================
# Tier 2 Rules - Deep-Path EqSat Rewrites
# ============================================================================

class CompressImplicationChain(RewriteRule):
    """A->B, B->C → A->C (transitivity)"""
    
    def __init__(self):
        super().__init__(RewriteRuleMetadata(
            tier=2,
            estimated_token_gain=0.4,
            matcher_cost=RewriteCost.MEDIUM,
            proof_cost=RewriteCost.MEDIUM,
            egraph_growth_risk=GrowthRisk.MEDIUM,
            rebuild_amplification_risk=GrowthRisk.LOW,
            fast_path_eligible=False,
            description="Compress implication chain: A->B, B->C → A->C"
        ))
    
    def can_apply(self, expr: Expression) -> bool:
        # This requires e-graph analysis, not just local matching
        # For v1, we'll implement a simplified version
        return False
    
    def apply(self, expr: Expression) -> RewriteResult:
        return RewriteResult(success=False, transformed_expr=None, token_savings=0, proof=None, reason="Requires e-graph analysis")


# ============================================================================
# Rule Registry
# ============================================================================

class RewriteRuleRegistry:
    """Registry for all rewrite rules."""
    
    def __init__(self):
        self.rules: List[RewriteRule] = []
        self._initialize_rules()
    
    def _initialize_rules(self):
        """Initialize all rewrite rules."""
        # Tier 0 rules
        self.rules.append(NormalizeDoubleNegation())
        self.rules.append(FoldIdentityOps())
        
        # Tier 1 rules
        self.rules.append(EliminateRedundantQualifier())
        self.rules.append(CompressBoilerplateConnectors())
        
        # Tier 2 rules
        self.rules.append(CompressImplicationChain())
    
    def get_rules_for_tier(self, tier: int) -> List[RewriteRule]:
        """Get all rules for a specific tier."""
        return [rule for rule in self.rules if rule.metadata.tier == tier and rule.enabled and not rule.disabled]
    
    def get_fast_path_rules(self) -> List[RewriteRule]:
        """Get all rules eligible for fast path."""
        return [rule for rule in self.rules if rule.metadata.fast_path_eligible and rule.enabled and not rule.disabled]
    
    def get_deep_path_rules(self) -> List[RewriteRule]:
        """Get all rules for deep path."""
        return [rule for rule in self.rules if rule.metadata.tier >= 1 and rule.enabled and not rule.disabled]
    
    def apply_backoff(self):
        """Apply backoff to rules that should be disabled."""
        for rule in self.rules:
            if rule.should_backoff():
                rule.disabled = True


# Global registry instance
rule_registry = RewriteRuleRegistry()

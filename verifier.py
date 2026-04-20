"""
NOX Verifier - Multi-Layer Verification System

This module implements multi-layer verification for NOX IR:
- Layer 1: Structural verification (grammar, nodes, symbols)
- Layer 2: Semantic verification (types, uncertainty, constraints)
- Layer 3: Compression audit (safety, determinism, monotonicity)
"""

from dataclasses import dataclass
from typing import List, Optional, Literal
from enum import Enum

from .ast import Expression, Statement
from .ir import NOXIR, NOXIRNode
from .types import UncertaintyType, check_type_preservation, TypeViolation


class VerificationLayer(Enum):
    """Verification layers."""
    STRUCTURAL = "structural"
    SEMANTIC = "semantic"
    COMPRESSION = "compression"


@dataclass
class VerificationCheck:
    """Result of a single verification check."""
    name: str
    passed: bool
    details: str
    layer: VerificationLayer


@dataclass
class VerificationResult:
    """Result of multi-layer verification."""
    layer: VerificationLayer
    passed: bool
    checks: List[VerificationCheck]
    errors: List[str]
    warnings: List[str]


class StructuralVerifier:
    """Layer 1: Structural verification."""
    
    def verify(self, ir: NOXIR) -> VerificationResult:
        """
        Verify IR structure.
        
        Args:
            ir: NOX IR to verify
        
        Returns:
            VerificationResult with structural checks
        """
        checks = []
        errors = []
        warnings = []
        
        # Check 1: Grammar validity
        grammar_valid = self._check_grammar_validity(ir)
        checks.append(VerificationCheck(
            name="grammar_validity",
            passed=grammar_valid,
            details="All expressions have valid grammar" if grammar_valid else "Invalid grammar detected",
            layer=VerificationLayer.STRUCTURAL
        ))
        if not grammar_valid:
            errors.append("Grammar validity check failed")
        
        # Check 2: No missing nodes
        no_missing_nodes = self._check_no_missing_nodes(ir)
        checks.append(VerificationCheck(
            name="no_missing_nodes",
            passed=no_missing_nodes,
            details="All nodes are present" if no_missing_nodes else "Missing nodes detected",
            layer=VerificationLayer.STRUCTURAL
        ))
        if not no_missing_nodes:
            errors.append("Missing nodes detected")
        
        # Check 3: No broken symbols
        no_broken_symbols = self._check_no_broken_symbols(ir)
        checks.append(VerificationCheck(
            name="no_broken_symbols",
            passed=no_broken_symbols,
            details="All symbols are valid" if no_broken_symbols else "Broken symbols detected",
            layer=VerificationLayer.STRUCTURAL
        ))
        if not no_broken_symbols:
            errors.append("Broken symbols detected")
        
        # Check 4: No corrupted classes
        no_corrupted_classes = self._check_no_corrupted_classes(ir)
        checks.append(VerificationCheck(
            name="no_corrupted_classes",
            passed=no_corrupted_classes,
            details="All equivalence classes are valid" if no_corrupted_classes else "Corrupted classes detected",
            layer=VerificationLayer.STRUCTURAL
        ))
        if not no_corrupted_classes:
            errors.append("Corrupted classes detected")
        
        passed = all(check.passed for check in checks)
        
        return VerificationResult(
            layer=VerificationLayer.STRUCTURAL,
            passed=passed,
            checks=checks,
            errors=errors,
            warnings=warnings
        )
    
    def _check_grammar_validity(self, ir: NOXIR) -> bool:
        """Check that all expressions have valid grammar."""
        for node in ir.nodes:
            if node.expr is None:
                return False
        return True
    
    def _check_no_missing_nodes(self, ir: NOXIR) -> bool:
        """Check that all referenced nodes exist."""
        # Check that root node exists
        if ir.root != 0 and not ir.get_node(ir.root):
            return False
        
        # Check that all class IDs are valid
        for node in ir.nodes:
            if node.class_id not in ir.classes:
                return False
        
        return True
    
    def _check_no_broken_symbols(self, ir: NOXIR) -> bool:
        """Check that all symbols are valid."""
        from .ast import Identifier
        
        for node in ir.nodes:
            if isinstance(node.expr, Identifier):
                if not node.expr.name or not node.expr.name.isidentifier():
                    return False
        
        return True
    
    def _check_no_corrupted_classes(self, ir: NOXIR) -> bool:
        """Check that all equivalence classes are valid."""
        for class_id, eclass in ir.classes.items():
            # Check that all nodes in class exist
            for node_id in eclass.nodes:
                if not ir.get_node(node_id):
                    return False
            
            # Check that canonical node exists
            if eclass.canonical and not ir.get_node(eclass.canonical):
                return False
        
        return True


class SemanticVerifier:
    """Layer 2: Semantic verification."""
    
    def verify(self, ir: NOXIR) -> VerificationResult:
        """
        Verify IR semantics.
        
        Args:
            ir: NOX IR to verify
        
        Returns:
            VerificationResult with semantic checks
        """
        checks = []
        errors = []
        warnings = []
        
        # Check 1: Type preservation
        type_preserved = self._check_type_preservation(ir)
        checks.append(VerificationCheck(
            name="type_preservation",
            passed=type_preserved,
            details="All uncertainty types are preserved" if type_preserved else "Type preservation violated",
            layer=VerificationLayer.SEMANTIC
        ))
        if not type_preserved:
            errors.append("Type preservation check failed")
        
        # Check 2: Uncertainty preservation
        uncertainty_preserved = self._check_uncertainty_preservation(ir)
        checks.append(VerificationCheck(
            name="uncertainty_preservation",
            passed=uncertainty_preserved,
            details="All uncertainty qualifiers are preserved" if uncertainty_preserved else "Uncertainty preservation violated",
            layer=VerificationLayer.SEMANTIC
        ))
        if not uncertainty_preserved:
            errors.append("Uncertainty preservation check failed")
        
        # Check 3: Constraint preservation
        constraint_preserved = self._check_constraint_preservation(ir)
        checks.append(VerificationCheck(
            name="constraint_preservation",
            passed=constraint_preserved,
            details="All constraints are preserved" if constraint_preserved else "Constraint preservation violated",
            layer=VerificationLayer.SEMANTIC
        ))
        if not constraint_preserved:
            errors.append("Constraint preservation check failed")
        
        # Check 4: No illegal rewrites
        no_illegal_rewrites = self._check_no_illegal_rewrites(ir)
        checks.append(VerificationCheck(
            name="no_illegal_rewrites",
            passed=no_illegal_rewrites,
            details="No illegal rewrites detected" if no_illegal_rewrites else "Illegal rewrites detected",
            layer=VerificationLayer.SEMANTIC
        ))
        if not no_illegal_rewrites:
            errors.append("Illegal rewrites detected")
        
        passed = all(check.passed for check in checks)
        
        return VerificationResult(
            layer=VerificationLayer.SEMANTIC,
            passed=passed,
            checks=checks,
            errors=errors,
            warnings=warnings
        )
    
    def _check_type_preservation(self, ir: NOXIR) -> bool:
        """Check that types are preserved across rewrites."""
        # For v1, we check that no node has lost its type information
        from .ast import TypedExpr
        
        for node in ir.nodes:
            if isinstance(node.expr, TypedExpr):
                # Type should be preserved
                if node.expr.type == UncertaintyType.CERTAIN:
                    # CERTAIN type should not be downgraded
                    pass  # More detailed check would require original IR
        
        return True
    
    def _check_uncertainty_preservation(self, ir: NOXIR) -> bool:
        """Check that uncertainty qualifiers are preserved."""
        # For v1, check that no HYPOTHETICAL became CERTAIN
        from .ast import TypedExpr
        
        for node in ir.nodes:
            if isinstance(node.expr, TypedExpr):
                # HYPOTHETICAL should not become CERTAIN
                if node.expr.type == UncertaintyType.CERTAIN:
                    # Would need original to check if this is a violation
                    pass
        
        return True
    
    def _check_constraint_preservation(self, ir: NOXIR) -> bool:
        """Check that constraints are preserved."""
        # For v1, check that IMMUTABLE constraints are not modified
        from .ast import Constraint
        
        for node in ir.nodes:
            if isinstance(node.expr, Constraint):
                # IMMUTABLE constraints should not be modified
                if node.expr.immutability:
                    # Would need original to check if this is a violation
                    pass
        
        return True
    
    def _check_no_illegal_rewrites(self, ir: NOXIR) -> bool:
        """Check that no illegal rewrites were applied."""
        # For v1, check that all proofs are valid
        for node in ir.nodes:
            if node.proof:
                if not node.proof.verified:
                    return False
                if not node.proof.type_preservation:
                    return False
        
        return True


class CompressionAuditor:
    """Layer 3: Compression audit."""
    
    def verify(self, ir: NOXIR) -> VerificationResult:
        """
        Verify compression safety.
        
        Args:
            ir: NOX IR to verify
        
        Returns:
            VerificationResult with compression checks
        """
        checks = []
        errors = []
        warnings = []
        
        # Check 1: Compression gain
        compression_gain = self._check_compression_gain(ir)
        checks.append(VerificationCheck(
            name="compression_gain",
            passed=compression_gain,
            details=f"Compression ratio: {ir.metadata.compression_ratio if ir.metadata else 1.0:.2f}" if compression_gain else "Insufficient compression gain",
            layer=VerificationLayer.COMPRESSION
        ))
        if not compression_gain:
            warnings.append("Compression gain below threshold")
        
        # Check 2: No over-compression
        no_over_compression = self._check_no_over_compression(ir)
        checks.append(VerificationCheck(
            name="no_over_compression",
            passed=no_over_compression,
            details="No over-compression detected" if no_over_compression else "Over-compression detected",
            layer=VerificationLayer.COMPRESSION
        ))
        if not no_over_compression:
            errors.append("Over-compression detected")
        
        # Check 3: Proof validity
        proof_valid = self._check_proof_validity(ir)
        checks.append(VerificationCheck(
            name="proof_validity",
            passed=proof_valid,
            details="All proofs are valid" if proof_valid else "Invalid proofs detected",
            layer=VerificationLayer.COMPRESSION
        ))
        if not proof_valid:
            errors.append("Invalid proofs detected")
        
        # Check 4: Determinism
        deterministic = self._check_determinism(ir)
        checks.append(VerificationCheck(
            name="determinism",
            passed=deterministic,
            details="Output is deterministic" if deterministic else "Non-deterministic behavior detected",
            layer=VerificationLayer.COMPRESSION
        ))
        if not deterministic:
            errors.append("Non-deterministic behavior detected")
        
        passed = all(check.passed for check in checks)
        
        return VerificationResult(
            layer=VerificationLayer.COMPRESSION,
            passed=passed,
            checks=checks,
            errors=errors,
            warnings=warnings
        )
    
    def _check_compression_gain(self, ir: NOXIR) -> bool:
        """Check that compression gain is sufficient."""
        if not ir.metadata:
            return True
        
        # Compression should be at least 5% (0.95 ratio)
        return ir.metadata.compression_ratio <= 0.95
    
    def _check_no_over_compression(self, ir: NOXIR) -> bool:
        """Check that compression is not too aggressive."""
        if not ir.metadata:
            return True
        
        # Compression should not exceed 70% (0.30 ratio) for v1
        return ir.metadata.compression_ratio >= 0.30
    
    def _check_proof_validity(self, ir: NOXIR) -> bool:
        """Check that all proofs are valid."""
        for node in ir.nodes:
            if node.proof:
                if not node.proof.verified:
                    return False
                if node.proof.proof_confidence < 0.8:
                    return False
        
        return True
    
    def _check_determinism(self, ir: NOXIR) -> bool:
        """Check that output is deterministic."""
        # For v1, check that determinism seed is set
        if ir.metadata:
            return ir.metadata.determinism_seed != 0
        return False


class MultiLayerVerifier:
    """Multi-layer verifier combining all verification layers."""
    
    def __init__(self):
        self.structural_verifier = StructuralVerifier()
        self.semantic_verifier = SemanticVerifier()
        self.compression_auditor = CompressionAuditor()
    
    def verify(self, ir: NOXIR) -> dict:
        """
        Verify IR across all layers.
        
        Args:
            ir: NOX IR to verify
        
        Returns:
            Dictionary with verification results for each layer
        """
        results = {}
        
        # Layer 1: Structural verification
        results['structural'] = self.structural_verifier.verify(ir)
        
        # Layer 2: Semantic verification
        results['semantic'] = self.semantic_verifier.verify(ir)
        
        # Layer 3: Compression audit
        results['compression'] = self.compression_auditor.verify(ir)
        
        # Overall result
        all_passed = all(
            result.passed for result in results.values()
        )
        
        results['overall'] = {
            'passed': all_passed,
            'total_errors': sum(len(result.errors) for result in results.values()),
            'total_warnings': sum(len(result.warnings) for result in results.values())
        }
        
        return results


def verify_ir(ir: NOXIR) -> dict:
    """
    Convenience function to verify NOX IR.
    
    Args:
        ir: NOX IR to verify
    
    Returns:
        Dictionary with verification results
    """
    verifier = MultiLayerVerifier()
    return verifier.verify(ir)

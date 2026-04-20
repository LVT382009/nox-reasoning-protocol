"""
NOX Optimizer - E-Graph Optimization with Fast/Deep Paths

This module implements the NOX optimizer with bounded equality saturation,
progressive early stopping, and automatic fallback.
"""

import time
from typing import List, Optional, Tuple, Literal
from dataclasses import dataclass

from .ast import Expression, Statement, estimate_expression_cost
from .ir import NOXIR, NOXIRNode, ProofCertificate
from .rewrite_rules import RewriteRule, RewriteRuleRegistry, rule_registry, RewriteResult
from .types import UncertaintyType


@dataclass
class OptimizationConfig:
    """Configuration for optimization."""
    path: Literal["fast", "deep"]
    max_iterations: int
    max_nodes: int
    max_time_ms: float
    improvement_threshold: float
    determinism_seed: int


@dataclass
class OptimizationResult:
    """Result of optimization."""
    success: bool
    ir: NOXIR
    iterations: int
    time_ms: float
    token_savings: int
    compression_ratio: float
    fallback_triggered: bool
    reason: str = ""


class AbortController:
    """Controller for aborting optimization based on cost/benefit analysis."""
    
    def __init__(self, config: OptimizationConfig):
        self.config = config
        self.start_time = time.time()
        self.abort_reason: Optional[str] = None
    
    def should_abort(self, current_cost: int, expected_gain: int, proof_cost: float) -> bool:
        """
        Check if optimization should be aborted.
        
        Args:
            current_cost: Current optimization cost
            expected_gain: Expected token gain
            proof_cost: Proof generation cost
        
        Returns:
            True if should abort, False otherwise
        """
        # Check time budget
        elapsed_ms = (time.time() - self.start_time) * 1000
        if elapsed_ms >= self.config.max_time_ms:
            self.abort_reason = f"Time budget exceeded ({elapsed_ms:.1f}ms >= {self.config.max_time_ms}ms)"
            return True
        
        # Check if cost exceeds expected gain
        if current_cost > expected_gain * 2:  # Cost is more than 2x expected gain
            self.abort_reason = f"Optimization cost ({current_cost}) exceeds expected gain ({expected_gain})"
            return True
        
        # Check if proof cost significantly exceeds benefit
        # Only abort if proof cost is more than 2x the expected gain
        if expected_gain > 0 and proof_cost > expected_gain * 2:
            self.abort_reason = f"Proof cost ({proof_cost}) exceeds rewrite benefit ({expected_gain})"
            return True
        
        return False
    
    def get_abort_reason(self) -> Optional[str]:
        """Get the reason for abort, if any."""
        return self.abort_reason


class NOXOptimizer:
    """NOX optimizer with fast and deep paths."""
    
    def __init__(self):
        self.rule_registry = rule_registry
    
    def optimize(self, ir: NOXIR, config: OptimizationConfig) -> OptimizationResult:
        """
        Optimize NOX IR.
        
        Args:
            ir: NOX IR to optimize
            config: Optimization configuration
        
        Returns:
            OptimizationResult with optimized IR and metadata
        """
        start_time = time.time()
        original_cost = ir.metadata.total_cost if ir.metadata else 0
        
        # Select rules based on path
        if config.path == "fast":
            rules = self.rule_registry.get_fast_path_rules()
        else:
            rules = self.rule_registry.get_deep_path_rules()
        
        # Initialize abort controller
        abort_controller = AbortController(config)
        
        # Apply rewrite rules
        iterations = 0
        total_savings = 0
        
        try:
            for iteration in range(config.max_iterations):
                iterations = iteration + 1
                
                # Check abort conditions
                if abort_controller.should_abort(iteration, total_savings, 0.5):
                    return OptimizationResult(
                        success=False,
                        ir=ir,
                        iterations=iterations,
                        time_ms=(time.time() - start_time) * 1000,
                        token_savings=total_savings,
                        compression_ratio=ir.metadata.compression_ratio if ir.metadata else 1.0,
                        fallback_triggered=True,
                        reason=abort_controller.get_abort_reason() or "Abort triggered"
                    )
                
                # Check bounds
                if not ir.is_bounded(config.max_nodes, config.max_nodes * 2):
                    return OptimizationResult(
                        success=False,
                        ir=ir,
                        iterations=iterations,
                        time_ms=(time.time() - start_time) * 1000,
                        token_savings=total_savings,
                        compression_ratio=ir.metadata.compression_ratio if ir.metadata else 1.0,
                        fallback_triggered=True,
                        reason="Node count exceeded bounds"
                    )
                
                # Apply one round of rewrites
                iteration_savings = self._apply_rewrite_round(ir, rules)
                
                # Check early stopping
                if iteration_savings < (original_cost * config.improvement_threshold):
                    # Improvement below threshold, stop
                    break
                
                total_savings += iteration_savings
                
                # Check if we've reached target compression
                if ir.metadata and ir.metadata.compression_ratio <= (1.0 - config.improvement_threshold):
                    break
        
        except Exception as e:
            return OptimizationResult(
                success=False,
                ir=ir,
                iterations=iterations,
                time_ms=(time.time() - start_time) * 1000,
                token_savings=total_savings,
                compression_ratio=ir.metadata.compression_ratio if ir.metadata else 1.0,
                fallback_triggered=True,
                reason=f"Optimization error: {str(e)}"
            )
        
        elapsed_time = (time.time() - start_time) * 1000
        
        # Update IR metadata
        ir.update_metadata(config.path, 2 if config.path == "deep" else 0, original_cost)
        
        return OptimizationResult(
            success=True,
            ir=ir,
            iterations=iterations,
            time_ms=elapsed_time,
            token_savings=total_savings,
            compression_ratio=ir.metadata.compression_ratio if ir.metadata else 1.0,
            fallback_triggered=False
        )
    
    def _apply_rewrite_round(self, ir: NOXIR, rules: List[RewriteRule]) -> int:
        """
        Apply one round of rewrite rules to IR.
        
        Args:
            ir: NOX IR to rewrite
            rules: List of rewrite rules to apply
        
        Returns:
            Total token savings from this round
        """
        total_savings = 0
        
        for node in ir.nodes:
            # Try each rule on this node
            for rule in rules:
                if rule.can_apply(node.expr):
                    result = rule.apply(node.expr)
                    
                    if result.success:
                        # Update node expression
                        node.expr = result.transformed_expr
                        node.proof = result.proof
                        
                        # Update cost
                        old_cost = node.cost
                        node.cost = estimate_expression_cost(node.expr)
                        savings = old_cost - node.cost
                        total_savings += savings
                        
                        # Record application
                        rule.record_application(savings)
                        
                        # Only apply one rule per node per round
                        break
        
        return total_savings
    
    def optimize_fast_path(self, ir: NOXIR) -> OptimizationResult:
        """
        Optimize using fast path (bounded rewrite, no saturation).
        
        Args:
            ir: NOX IR to optimize
        
        Returns:
            OptimizationResult with optimized IR
        """
        config = OptimizationConfig(
            path="fast",
            max_iterations=20,  # N=20 for fast path
            max_nodes=300,  # M=300 for fast path
            max_time_ms=15.0,  # 15ms budget
            improvement_threshold=0.05,  # 5% improvement threshold
            determinism_seed=ir.metadata.determinism_seed if ir.metadata else 0
        )
        
        return self.optimize(ir, config)
    
    def optimize_deep_path(self, ir: NOXIR) -> OptimizationResult:
        """
        Optimize using deep path (bounded equality saturation).
        
        Args:
            ir: NOX IR to optimize
        
        Returns:
            OptimizationResult with optimized IR
        """
        config = OptimizationConfig(
            path="deep",
            max_iterations=100,  # N=100 for deep path
            max_nodes=2000,  # M=2000 for deep path
            max_time_ms=30.0,  # 30ms budget
            improvement_threshold=0.02,  # 2% improvement threshold
            determinism_seed=ir.metadata.determinism_seed if ir.metadata else 0
        )
        
        return self.optimize(ir, config)


def optimize_ir(ir: NOXIR, path: str = "fast") -> OptimizationResult:
    """
    Convenience function to optimize NOX IR.
    
    Args:
        ir: NOX IR to optimize
        path: Optimization path (fast or deep)
    
    Returns:
        OptimizationResult with optimized IR
    """
    optimizer = NOXOptimizer()
    
    if path == "fast":
        return optimizer.optimize_fast_path(ir)
    else:
        return optimizer.optimize_deep_path(ir)

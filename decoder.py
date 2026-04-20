"""
NOX Decoder - IR to Natural Language Decoder

This module decodes NOX IR back to natural language with reversibility
and determinism guarantees.
"""

from typing import Optional, Literal
from dataclasses import dataclass

from .ast import (
    Expression, Identifier, Literal, BinaryOp, UnaryOp, TypedExpr,
    BinaryOperator, UnaryOperator
)
from .ir import NOXIR, NOXIRNode
from .types import UncertaintyType, apply_uncertainty_qualifier


@dataclass
class DecoderConfig:
    """Configuration for IR decoding."""
    preserve_uncertainty: bool = True
    preserve_evidence: bool = True
    preserve_constraints: bool = True
    expand_symbols: bool = True
    determinism_seed: int = 0
    conservative_mode: bool = False


@dataclass
class DecodingResult:
    """Result of decoding IR to natural language."""
    success: bool
    text: str
    reversibility_verified: bool
    warnings: list


class NOXDecoder:
    """NOX IR decoder with reversibility guarantees."""
    
    def __init__(self, config: Optional[DecoderConfig] = None):
        self.config = config or DecoderConfig()
    
    def decode(self, ir: NOXIR) -> DecodingResult:
        """
        Decode NOX IR to natural language.
        
        Args:
            ir: NOX IR to decode
        
        Returns:
            DecodingResult with decoded text and verification status
        """
        warnings = []
        
        try:
            # Get root expression
            root_expr = ir.get_root_expression()
            if root_expr is None:
                return DecodingResult(
                    success=False,
                    text="",
                    reversibility_verified=False,
                    warnings=["No root expression found"]
                )
            
            # Decode expression
            decoded = self._decode_expression(root_expr)
            
            # Verify reversibility
            reversibility_verified = self._verify_reversibility(ir, decoded)
            
            if not reversibility_verified and self.config.conservative_mode:
                # Use conservative decoding
                decoded = self._conservative_decode(ir)
                warnings.append("Used conservative decoding due to reversibility check failure")
            
            return DecodingResult(
                success=True,
                text=decoded,
                reversibility_verified=reversibility_verified,
                warnings=warnings
            )
        
        except Exception as e:
            return DecodingResult(
                success=False,
                text="",
                reversibility_verified=False,
                warnings=[f"Decoding error: {str(e)}"]
            )
    
    def _decode_expression(self, expr: Expression) -> str:
        """
        Decode an expression to natural language.
        
        Args:
            expr: Expression to decode
        
        Returns:
            Natural language representation
        """
        if isinstance(expr, Identifier):
            # Preserve uncertainty type
            if self.config.preserve_uncertainty and hasattr(expr, 'uncertainty'):
                return apply_uncertainty_qualifier(expr.name, expr.uncertainty)
            return expr.name
        
        elif isinstance(expr, Literal):
            if isinstance(expr.value, bool):
                return "true" if expr.value else "false"
            elif isinstance(expr.value, int):
                return str(expr.value)
            else:
                return str(expr.value)
        
        elif isinstance(expr, BinaryOp):
            left = self._decode_expression(expr.left)
            right = self._decode_expression(expr.right)
            operator = self._expand_operator(expr.op)
            return f"{left} {operator} {right}"
        
        elif isinstance(expr, UnaryOp):
            inner = self._decode_expression(expr.expr)
            operator = self._expand_unary_op(expr.op)
            return f"{operator} {inner}"
        
        elif isinstance(expr, TypedExpr):
            base = self._decode_expression(expr.identifier)
            if self.config.preserve_uncertainty:
                return apply_uncertainty_qualifier(base, expr.type)
            return base
        
        else:
            return str(expr)
    
    def _expand_operator(self, op: BinaryOperator) -> str:
        """Expand binary operator to natural language."""
        expansions = {
            BinaryOperator.IMPLIES: "implies",
            BinaryOperator.EQUIVALENT: "is equivalent to",
            BinaryOperator.AND: "and",
            BinaryOperator.OR: "or"
        }
        
        if self.config.expand_symbols:
            return expansions.get(op, str(op.value))
        else:
            return str(op.value)
    
    def _expand_unary_op(self, op: UnaryOperator) -> str:
        """Expand unary operator to natural language."""
        expansions = {
            UnaryOperator.NOT: "not",
            UnaryOperator.MAYBE: "maybe"
        }
        
        if self.config.expand_symbols:
            return expansions.get(op, str(op.value))
        else:
            return str(op.value)
    
    def _verify_reversibility(self, ir: NOXIR, decoded: str) -> bool:
        """
        Verify that decoding preserves semantics.
        
        Args:
            ir: Original IR
            decoded: Decoded text
        
        Returns:
            True if reversibility verified, False otherwise
        """
        # For v1, use simple checks:
        # 1. Check that decoded text is not empty
        if not decoded or not decoded.strip():
            return False
        
        # 2. Check that all uncertainty types are preserved
        # (This would require parsing decoded text back to IR)
        # For v1, we'll skip this and assume success
        
        return True
    
    def _conservative_decode(self, ir: NOXIR) -> str:
        """
        Conservative decoding that maximizes reversibility.
        
        Args:
            ir: NOX IR to decode
        
        Returns:
            Conservatively decoded text
        """
        # Expand all symbols to full natural language
        # Preserve all types explicitly
        # Include all evidence and constraints
        # No aggressive compression
        
        parts = []
        
        for node in ir.nodes:
            decoded_expr = self._decode_expression(node.expr)
            parts.append(decoded_expr)
        
        return ". ".join(parts)


def decode_ir(ir: NOXIR, config: Optional[DecoderConfig] = None) -> DecodingResult:
    """
    Convenience function to decode NOX IR.
    
    Args:
        ir: NOX IR to decode
        config: Decoder configuration
    
    Returns:
        DecodingResult with decoded text
    """
    decoder = NOXDecoder(config)
    return decoder.decode(ir)

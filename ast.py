"""
NOX AST - Abstract Syntax Tree Definitions

This module defines the AST for NOX, which represents parsed natural language
reasoning in a structured form with type annotations.
"""

from dataclasses import dataclass
from typing import List, Optional, Union, Literal
from enum import Enum

from .types import UncertaintyType


class BinaryOperator(Enum):
    """Binary operators for NOX expressions."""
    IMPLIES = "->"
    EQUIVALENT = "|="
    AND = "&"
    OR = "|"


class UnaryOperator(Enum):
    """Unary operators for NOX expressions."""
    NOT = "NOT"
    MAYBE = "MAYBE"


@dataclass
class Identifier:
    """Identifier node in AST."""
    name: str
    uncertainty: UncertaintyType = UncertaintyType.CERTAIN


@dataclass
class Literal:
    """Literal node in AST."""
    value: Union[bool, int, str]


@dataclass
class BinaryOp:
    """Binary operation node in AST."""
    left: "Expression"
    op: BinaryOperator
    right: "Expression"


@dataclass
class UnaryOp:
    """Unary operation node in AST."""
    op: UnaryOperator
    expr: "Expression"


@dataclass
class TypedExpr:
    """Typed expression node with explicit type annotation."""
    identifier: Identifier
    type: UncertaintyType


# Expression type union
Expression = Union[Identifier, Literal, BinaryOp, UnaryOp, TypedExpr]


@dataclass
class Fact:
    """Fact statement in AST."""
    expr: Expression


@dataclass
class Rule:
    """Rule statement in AST (implication)."""
    condition: Expression
    consequence: Expression


@dataclass
class Inference:
    """Inference statement in AST."""
    expr: Expression


@dataclass
class Assumption:
    """Assumption statement in AST."""
    expr: Expression
    uncertainty: UncertaintyType


@dataclass
class Evidence:
    """Evidence statement in AST."""
    expr: Expression
    uncertainty: UncertaintyType


@dataclass
class Constraint:
    """Constraint statement in AST."""
    expr: Expression
    immutability: bool  # True if immutable


# Statement type union
Statement = Union[Fact, Rule, Inference, Assumption, Evidence, Constraint]


@dataclass
class NOXProgram:
    """Complete NOX program (AST root)."""
    statements: List[Statement]
    metadata: "ProgramMetadata"


@dataclass
class ProgramMetadata:
    """Metadata for NOX program."""
    path: str  # "fast" or "deep"
    tier: int  # 0, 1, 2, or 3
    compression_estimate: float
    original_text: Optional[str] = None


# AST visitor pattern for traversals
class ASTVisitor:
    """Base class for AST visitors."""
    
    def visit(self, node):
        """Visit a node."""
        method_name = f"visit_{type(node).__name__}"
        visitor = getattr(self, method_name, self.generic_visit)
        return visitor(node)
    
    def generic_visit(self, node):
        """Default visitor method."""
        # For dataclasses, visit all fields
        if hasattr(node, '__dataclass_fields__'):
            for field_name, field_value in node.__dict__.items():
                if isinstance(field_value, list):
                    for item in field_value:
                        if isinstance(item, (Expression, Statement)):
                            self.visit(item)
                elif isinstance(field_value, (Expression, Statement)):
                    self.visit(field_value)


class ASTTransformer:
    """Base class for AST transformers."""
    
    def transform(self, node):
        """Transform a node."""
        method_name = f"transform_{type(node).__name__}"
        transformer = getattr(self, method_name, self.generic_transform)
        return transformer(node)
    
    def generic_transform(self, node):
        """Default transformer method."""
        # For dataclasses, transform all fields
        if hasattr(node, '__dataclass_fields__'):
            new_values = {}
            for field_name, field_value in node.__dict__.items():
                if isinstance(field_value, list):
                    new_values[field_name] = [
                        self.transform(item) if isinstance(item, (Expression, Statement))
                        else item
                        for item in field_value
                    ]
                elif isinstance(field_value, (Expression, Statement)):
                    new_values[field_name] = self.transform(field_value)
                else:
                    new_values[field_name] = field_value
            return type(node)(**new_values)
        return node


# Utility functions
def get_expression_type(expr: Expression) -> UncertaintyType:
    """Get the uncertainty type of an expression."""
    if isinstance(expr, Identifier):
        return expr.uncertainty
    elif isinstance(expr, TypedExpr):
        return expr.type
    elif isinstance(expr, BinaryOp):
        # Binary ops preserve the type of their operands
        left_type = get_expression_type(expr.left)
        right_type = get_expression_type(expr.right)
        # Return the more uncertain type
        return max([left_type, right_type], key=lambda t: t.value)
    elif isinstance(expr, UnaryOp):
        # Unary ops preserve the type of their operand
        return get_expression_type(expr.expr)
    else:
        return UncertaintyType.CERTAIN


def is_fast_path_statement(stmt: Statement) -> bool:
    """
    Check if a statement is allowed in fast path.
    
    Fast path allows:
    - Simple facts (no complex expressions)
    - Simple rules (direct implication between identifiers)
    - Simple inferences (single identifier)
    
    Fast path excludes:
    - Recursive expressions
    - High-fanout expansions
    - Global reasoning operators
    """
    if isinstance(stmt, Fact):
        # Fast path if expression is simple identifier or literal
        return isinstance(stmt.expr, (Identifier, Literal))
    
    elif isinstance(stmt, Rule):
        # Fast path if both sides are simple identifiers
        return (
            isinstance(stmt.condition, Identifier) and
            isinstance(stmt.consequence, Identifier)
        )
    
    elif isinstance(stmt, Inference):
        # Fast path if expression is simple identifier
        return isinstance(stmt.expr, Identifier)
    
    elif isinstance(stmt, (Assumption, Evidence, Constraint)):
        # These are not allowed in fast path
        return False
    
    return False


def estimate_expression_cost(expr: Expression) -> int:
    """
    Estimate token cost of an expression.
    
    Returns approximate token count for the expression.
    """
    if isinstance(expr, Identifier):
        return 1
    elif isinstance(expr, Literal):
        return 1
    elif isinstance(expr, BinaryOp):
        left_cost = estimate_expression_cost(expr.left)
        right_cost = estimate_expression_cost(expr.right)
        return left_cost + right_cost + 1  # +1 for operator
    elif isinstance(expr, UnaryOp):
        expr_cost = estimate_expression_cost(expr.expr)
        return expr_cost + 1  # +1 for operator
    elif isinstance(expr, TypedExpr):
        return estimate_expression_cost(expr.identifier) + 1  # +1 for type
    else:
        return 1


def estimate_statement_cost(stmt: Statement) -> int:
    """
    Estimate token cost of a statement.
    
    Returns approximate token count for the statement.
    """
    if isinstance(stmt, Fact):
        return estimate_expression_cost(stmt.expr) + 1  # +1 for FACT[]
    elif isinstance(stmt, Rule):
        return (
            estimate_expression_cost(stmt.condition) +
            estimate_expression_cost(stmt.consequence) +
            2  # +2 for RULE[] and ->
        )
    elif isinstance(stmt, Inference):
        return estimate_expression_cost(stmt.expr) + 1  # +1 for INFER[]
    elif isinstance(stmt, Assumption):
        return estimate_expression_cost(stmt.expr) + 1  # +1 for ASSUME[]
    elif isinstance(stmt, Evidence):
        return estimate_expression_cost(stmt.expr) + 1  # +1 for EVIDENCE[]
    elif isinstance(stmt, Constraint):
        return estimate_expression_cost(stmt.expr) + 1  # +1 for CONSTRAINT[]
    else:
        return 1

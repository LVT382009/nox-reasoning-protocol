"""
NOX Parser - Natural Language to AST Parser

This module parses natural language reasoning into NOX AST.
For v1, this is a simplified parser that handles basic patterns.
"""

import re
from typing import List, Optional, Tuple
from dataclasses import dataclass

from .ast import (
    NOXProgram, ProgramMetadata, Statement,
    Fact, Rule, Inference, Assumption, Evidence, Constraint,
    Expression, Identifier, Literal, BinaryOp, UnaryOp, TypedExpr,
    BinaryOperator, UnaryOperator
)
from .types import UncertaintyType


class ParseError(Exception):
    """Error during parsing."""
    pass


@dataclass
class ParseResult:
    """Result of parsing."""
    program: NOXProgram
    errors: List[str]
    warnings: List[str]


class NOXParser:
    """Parser for natural language reasoning into NOX AST."""
    
    # Pattern for identifying reasoning structures
    PATTERNS = {
        # Fact patterns
        r'fact\s*\[([^\]]+)\]': 'fact',
        r'it is a fact that\s+(.+?)(?:\.|$)': 'fact',
        r'(.+?)\s+is true': 'fact',
        
        # Rule patterns
        r'rule\s*\[([^\]]+)\s*->\s*([^\]]+)\]': 'rule',
        r'if\s+(.+?)\s+then\s+(.+?)(?:\.|$)': 'rule',
        r'(.+?)\s+implies\s+(.+?)(?:\.|$)': 'rule',
        r'(.+?)\s+means\s+(.+?)(?:\.|$)': 'rule',
        
        # Inference patterns
        r'infer\s*\[([^\]]+)\]': 'inference',
        r'we can infer\s+(.+?)(?:\.|$)': 'inference',
        r'therefore\s+(.+?)(?:\.|$)': 'inference',
        r'consequently\s+(.+?)(?:\.|$)': 'inference',
        
        # Assumption patterns
        r'assume\s*\[([^\]]+)\]': 'assumption',
        r'let\'s assume\s+(.+?)(?:\.|$)': 'assumption',
        r'assuming\s+(.+?)(?:\.|$)': 'assumption',
        
        # Evidence patterns
        r'evidence\s*\[([^\]]+)\]': 'evidence',
        r'according to\s+(.+?)(?:\.|$)': 'evidence',
        r'based on\s+(.+?)(?:\.|$)': 'evidence',
        
        # Constraint patterns
        r'constraint\s*\[([^\]]+)\]': 'constraint',
        r'we must\s+(.+?)(?:\.|$)': 'constraint',
        r'it is required that\s+(.+?)(?:\.|$)': 'constraint',
    }
    
    def __init__(self):
        self.errors: List[str] = []
        self.warnings: List[str] = []
    
    def parse(self, text: str, path: str = "fast") -> ParseResult:
        """
        Parse natural language text into NOX program.
        
        Args:
            text: Natural language text to parse
            path: Optimization path (fast or deep)
        
        Returns:
            ParseResult with program and any errors/warnings
        """
        self.errors = []
        self.warnings = []
        
        # Normalize text
        text = text.strip()
        if not text:
            self.errors.append("Empty input")
            return ParseResult(
                program=NOXProgram(statements=[], metadata=ProgramMetadata(path=path, tier=1, compression_estimate=1.0)),
                errors=self.errors,
                warnings=self.warnings
            )
        
        # Split into sentences
        sentences = self._split_sentences(text)
        
        # Parse each sentence
        statements = []
        for sentence in sentences:
            stmt = self._parse_sentence(sentence)
            if stmt:
                statements.append(stmt)
        
        # Determine tier based on path
        tier = 0 if path == "fast" else 2
        
        # Estimate compression
        compression_estimate = self._estimate_compression(statements)
        
        # Create program
        program = NOXProgram(
            statements=statements,
            metadata=ProgramMetadata(
                path=path,
                tier=tier,
                compression_estimate=compression_estimate,
                original_text=text
            )
        )
        
        return ParseResult(
            program=program,
            errors=self.errors,
            warnings=self.warnings
        )
    
    def _split_sentences(self, text: str) -> List[str]:
        """Split text into sentences."""
        # Simple sentence splitting on periods, question marks, exclamation marks
        sentences = re.split(r'[.!?]+', text)
        return [s.strip() for s in sentences if s.strip()]
    
    def _parse_sentence(self, sentence: str) -> Optional[Statement]:
        """Parse a single sentence into a statement."""
        sentence = sentence.strip()
        if not sentence:
            return None
        
        # Try each pattern
        for pattern, stmt_type in self.PATTERNS.items():
            match = re.match(pattern, sentence, re.IGNORECASE)
            if match:
                if stmt_type == 'fact':
                    return self._parse_fact(match)
                elif stmt_type == 'rule':
                    return self._parse_rule(match)
                elif stmt_type == 'inference':
                    return self._parse_inference(match)
                elif stmt_type == 'assumption':
                    return self._parse_assumption(match)
                elif stmt_type == 'evidence':
                    return self._parse_evidence(match)
                elif stmt_type == 'constraint':
                    return self._parse_constraint(match)
        
        # If no pattern matched, treat as simple fact
        self.warnings.append(f"No pattern matched for: '{sentence}', treating as fact")
        return Fact(expr=self._parse_expression(sentence))
    
    def _parse_fact(self, match) -> Fact:
        """Parse a fact statement."""
        expr_text = match.group(1).strip()
        expr = self._parse_expression(expr_text)
        return Fact(expr=expr)
    
    def _parse_rule(self, match) -> Rule:
        """Parse a rule statement."""
        condition_text = match.group(1).strip()
        consequence_text = match.group(2).strip()
        
        condition = self._parse_expression(condition_text)
        consequence = self._parse_expression(consequence_text)
        
        return Rule(condition=condition, consequence=consequence)
    
    def _parse_inference(self, match) -> Inference:
        """Parse an inference statement."""
        expr_text = match.group(1).strip()
        expr = self._parse_expression(expr_text)
        return Inference(expr=expr)
    
    def _parse_assumption(self, match) -> Assumption:
        """Parse an assumption statement."""
        expr_text = match.group(1).strip()
        expr = self._parse_expression(expr_text)
        uncertainty = UncertaintyType.HYPOTHETICAL
        return Assumption(expr=expr, uncertainty=uncertainty)
    
    def _parse_evidence(self, match) -> Assumption:
        """Parse an evidence statement."""
        expr_text = match.group(1).strip()
        expr = self._parse_expression(expr_text)
        uncertainty = UncertaintyType.VERIFIED
        return Evidence(expr=expr, uncertainty=uncertainty)
    
    def _parse_constraint(self, match) -> Constraint:
        """Parse a constraint statement."""
        expr_text = match.group(1).strip()
        expr = self._parse_expression(expr_text)
        immutability = True
        return Constraint(expr=expr, immutability=immutability)
    
    def _parse_expression(self, text: str) -> Expression:
        """Parse an expression from text."""
        text = text.strip()
        
        # Check for uncertainty qualifiers
        uncertainty = self._extract_uncertainty(text)
        if uncertainty:
            # Remove qualifier from text
            text = re.sub(r'\b(probably|hypothetically|verified|allegedly|preserved|immutable)\b\s*', '', text, flags=re.IGNORECASE)
            text = text.strip()
        
        # Check for binary operators
        for op_str, op_enum in [('->', BinaryOperator.IMPLIES), ('|=', BinaryOperator.EQUIVALENT), ('&', BinaryOperator.AND), ('or', BinaryOperator.OR)]:
            if op_str in text.lower():
                parts = text.split(op_str, 1)
                if len(parts) == 2:
                    left = self._parse_expression(parts[0].strip())
                    right = self._parse_expression(parts[1].strip())
                    return BinaryOp(left=left, op=op_enum, right=right)
        
        # Check for unary operators
        if text.lower().startswith(('not ', 'maybe ')):
            op_text = text.split()[0].lower()
            expr_text = text[len(op_text):].strip()
            op = UnaryOperator.NOT if op_text == 'not' else UnaryOperator.MAYBE
            expr = self._parse_expression(expr_text)
            return UnaryOp(op=op, expr=expr)
        
        # Check for literal
        if text.lower() in ('true', 'false'):
            return Literal(value=text.lower() == 'true')
        
        # Check for number
        if text.isdigit():
            return Literal(value=int(text))
        
        # Default: identifier
        identifier = Identifier(name=text)
        if uncertainty:
            return TypedExpr(identifier=identifier, type=uncertainty)
        return identifier
    
    def _extract_uncertainty(self, text: str) -> Optional[UncertaintyType]:
        """Extract uncertainty type from text."""
        uncertainty_map = {
            'probably': UncertaintyType.PROBABLE,
            'hypothetically': UncertaintyType.HYPOTHETICAL,
            'verified': UncertaintyType.VERIFIED,
            'allegedly': UncertaintyType.UNVERIFIED,
            'preserved': UncertaintyType.PRESERVED,
            'immutable': UncertaintyType.IMMUTABLE,
        }
        
        text_lower = text.lower()
        for qualifier, uncertainty in uncertainty_map.items():
            if qualifier in text_lower:
                return uncertainty
        
        return None
    
    def _estimate_compression(self, statements: List[Statement]) -> float:
        """Estimate compression ratio for statements."""
        if not statements:
            return 1.0
        
        # For v1, use simple heuristic
        # Fast path: ~30% compression
        # Deep path: ~50% compression
        return 0.7


def parse_text(text: str, path: str = "fast") -> ParseResult:
    """
    Convenience function to parse text.
    
    Args:
        text: Natural language text to parse
        path: Optimization path (fast or deep)
    
    Returns:
        ParseResult with program and any errors/warnings
    """
    parser = NOXParser()
    return parser.parse(text, path)

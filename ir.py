"""
NOX IR - Intermediate Representation with E-Graph Support

This module defines the NOX Intermediate Representation as an e-graph,
which enables equality saturation and optimization.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Literal
from enum import Enum
import random

from .ast import Expression, Statement, NOXProgram, estimate_expression_cost
from .types import UncertaintyType


class EGraphClass:
    """Equivalence class in e-graph."""
    
    def __init__(self, class_id: int):
        self.id = class_id
        self.nodes: Set[int] = set()  # Node IDs in this class
        self.canonical: Optional[int] = None  # Canonical node ID
    
    def add_node(self, node_id: int):
        """Add a node to this equivalence class."""
        self.nodes.add(node_id)
    
    def merge(self, other: "EGraphClass"):
        """Merge another equivalence class into this one."""
        self.nodes.update(other.nodes)
        # Keep the smaller ID as canonical (deterministic)
        if other.id < self.id:
            self.id = other.id
        if self.canonical is None or (other.canonical is not None and other.canonical < self.canonical):
            self.canonical = other.canonical


@dataclass
class NOXIRNode:
    """Single node in NOX IR e-graph."""
    id: int
    expr: Expression
    class_id: int  # E-graph equivalence class
    cost: int  # Estimated token cost
    proof: Optional["ProofCertificate"] = None
    tier: Literal[0, 1, 2, 3] = 1  # Rewrite tier that created this node
    
    def __hash__(self):
        return hash(self.id)
    
    def __eq__(self, other):
        if not isinstance(other, NOXIRNode):
            return False
        return self.id == other.id


@dataclass
class ProofCertificate:
    """Proof of semantic preservation for a rewrite."""
    rewrite_id: str
    original_expr: Expression
    transformed_expr: Expression
    proof_type: Literal["local_legality", "compositional", "full_semantic"]
    
    # Proof content
    invariants_preserved: List[str]
    type_preservation: bool
    semantic_equivalence: bool
    
    # Cost metadata
    proof_cost_ms: float
    proof_confidence: float  # 0.0 to 1.0
    
    # Verification status
    verified: bool
    verification_method: Literal["type_check", "structural", "semantic"]
    
    # Rollback path
    rollback_expr: Expression


@dataclass
class IRMetadata:
    """Metadata for NOX IR."""
    path: Literal["fast", "deep"]
    tier: Literal[0, 1, 2, 3]
    total_cost: int
    original_cost: int
    compression_ratio: float
    determinism_seed: int
    node_count: int
    class_count: int


@dataclass
class NOXIR:
    """NOX Intermediate Representation as e-graph."""
    nodes: List[NOXIRNode] = field(default_factory=list)
    classes: Dict[int, EGraphClass] = field(default_factory=dict)
    root: int = 0  # Root node for extraction
    metadata: Optional[IRMetadata] = None
    next_node_id: int = 1
    next_class_id: int = 1
    
    def add_node(self, expr: Expression, tier: Literal[0, 1, 2, 3] = 1) -> NOXIRNode:
        """
        Add a node to the e-graph.
        
        Args:
            expr: Expression to add
            tier: Rewrite tier that created this node
        
        Returns:
            The created node
        """
        cost = estimate_expression_cost(expr)
        
        # Create new equivalence class for this node
        class_id = self.next_class_id
        self.next_class_id += 1
        eclass = EGraphClass(class_id)
        self.classes[class_id] = eclass
        
        # Create node
        node = NOXIRNode(
            id=self.next_node_id,
            expr=expr,
            class_id=class_id,
            cost=cost,
            tier=tier
        )
        self.next_node_id += 1
        
        # Add node to its class
        eclass.add_node(node.id)
        eclass.canonical = node.id
        
        # Add to nodes list
        self.nodes.append(node)
        
        return node
    
    def merge_classes(self, class_id1: int, class_id2: int) -> bool:
        """
        Merge two equivalence classes.
        
        Args:
            class_id1: First class ID
            class_id2: Second class ID
        
        Returns:
            True if merge was successful, False otherwise
        """
        if class_id1 not in self.classes or class_id2 not in self.classes:
            return False
        
        if class_id1 == class_id2:
            return True  # Already merged
        
        # Merge class2 into class1
        class1 = self.classes[class_id1]
        class2 = self.classes[class_id2]
        
        class1.merge(class2)
        
        # Update all nodes in class2 to point to class1
        for node_id in class2.nodes:
            node = self.get_node(node_id)
            if node:
                node.class_id = class_id1
        
        # Remove class2
        del self.classes[class_id2]
        
        return True
    
    def get_node(self, node_id: int) -> Optional[NOXIRNode]:
        """Get a node by ID."""
        for node in self.nodes:
            if node.id == node_id:
                return node
        return None
    
    def get_class(self, class_id: int) -> Optional[EGraphClass]:
        """Get an equivalence class by ID."""
        return self.classes.get(class_id)
    
    def find_canonical_node(self, node_id: int) -> Optional[NOXIRNode]:
        """
        Find the canonical node for a given node ID.
        
        Args:
            node_id: Node ID to find canonical for
        
        Returns:
            Canonical node, or None if not found
        """
        node = self.get_node(node_id)
        if not node:
            return None
        
        eclass = self.get_class(node.class_id)
        if not eclass:
            return node
        
        if eclass.canonical is None:
            return node
        
        return self.get_node(eclass.canonical)
    
    def update_metadata(self, path: Literal["fast", "deep"], tier: Literal[0, 1, 2, 3], original_cost: int):
        """Update IR metadata."""
        total_cost = sum(node.cost for node in self.nodes)
        compression_ratio = total_cost / original_cost if original_cost > 0 else 1.0
        
        self.metadata = IRMetadata(
            path=path,
            tier=tier,
            total_cost=total_cost,
            original_cost=original_cost,
            compression_ratio=compression_ratio,
            determinism_seed=random.randint(0, 2**31 - 1),
            node_count=len(self.nodes),
            class_count=len(self.classes)
        )
    
    def get_root_expression(self) -> Optional[Expression]:
        """Get the expression at the root node."""
        root_node = self.get_node(self.root)
        if root_node:
            return root_node.expr
        return None
    
    def is_bounded(self, max_nodes: int, max_classes: int) -> bool:
        """
        Check if IR is within bounds.
        
        Args:
            max_nodes: Maximum allowed nodes
            max_classes: Maximum allowed classes
        
        Returns:
            True if within bounds, False otherwise
        """
        return len(self.nodes) <= max_nodes and len(self.classes) <= max_classes
    
    def clone(self) -> "NOXIR":
        """Create a deep copy of this IR."""
        new_ir = NOXIR()
        new_ir.root = self.root
        new_ir.next_node_id = self.next_node_id
        new_ir.next_class_id = self.next_class_id
        
        # Clone nodes
        for node in self.nodes:
            new_node = NOXIRNode(
                id=node.id,
                expr=node.expr,
                class_id=node.class_id,
                cost=node.cost,
                proof=node.proof,
                tier=node.tier
            )
            new_ir.nodes.append(new_node)
        
        # Clone classes
        for class_id, eclass in self.classes.items():
            new_eclass = EGraphClass(class_id)
            new_eclass.nodes = eclass.nodes.copy()
            new_eclass.canonical = eclass.canonical
            new_ir.classes[class_id] = new_eclass
        
        # Clone metadata
        if self.metadata:
            new_ir.metadata = IRMetadata(
                path=self.metadata.path,
                tier=self.metadata.tier,
                total_cost=self.metadata.total_cost,
                original_cost=self.metadata.original_cost,
                compression_ratio=self.metadata.compression_ratio,
                determinism_seed=self.metadata.determinism_seed,
                node_count=self.metadata.node_count,
                class_count=self.metadata.class_count
            )
        
        return new_ir


def create_ir_from_program(program: NOXProgram, path: Literal["fast", "deep"]) -> NOXIR:
    """
    Create NOX IR from a NOX program.
    
    Args:
        program: NOX program to convert
        path: Optimization path (fast or deep)
    
    Returns:
        NOX IR representation
    """
    ir = NOXIR()
    
    # Calculate original cost
    original_cost = sum(
        estimate_expression_cost(stmt.expr) if hasattr(stmt, 'expr')
        else estimate_expression_cost(stmt.condition) + estimate_expression_cost(stmt.consequence) if isinstance(stmt, type(program).__dataclass_fields__['condition'].default)
        else 1
        for stmt in program.statements
    )
    
    # Add each statement as a node
    for stmt in program.statements:
        if hasattr(stmt, 'expr'):
            ir.add_node(stmt.expr, tier=program.metadata.tier)
        elif hasattr(stmt, 'condition'):
            # For rules, add both condition and consequence
            ir.add_node(stmt.condition, tier=program.metadata.tier)
            ir.add_node(stmt.consequence, tier=program.metadata.tier)
    
    # Set root to first node
    if ir.nodes:
        ir.root = ir.nodes[0].id
    
    # Update metadata
    ir.update_metadata(path, program.metadata.tier, original_cost)
    
    return ir

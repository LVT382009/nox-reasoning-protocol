"""
NOX Integration - Main Integration Module for Hermes Agent

This module provides the main NOX integration with Hermes Agent,
including the full compiler pipeline and automatic fallback.
"""

import time
from typing import Optional, Dict, Any, Literal
from dataclasses import dataclass

from .parser import NOXParser, ParseResult
from .ir import NOXIR, create_ir_from_program
from .optimizer import NOXOptimizer, OptimizationResult
from .verifier import verify_ir
from .decoder import NOXDecoder, DecoderConfig, DecodingResult
from .types import UncertaintyType


@dataclass
class NOXIntegrationResult:
    """Result of NOX integration."""
    success: bool
    original_response: str
    optimized_response: Optional[str]
    token_savings: int
    context_savings: int
    validation_time_ms: float
    nox_metadata: Dict[str, Any]
    fallback_triggered: bool
    reason: str = ""


class NOXAgentIntegrator:
    """
    Automatic NOX integration for Hermes Agent.
    
    This class provides automatic validation and optimization of agent responses
    without requiring manual invocation by the user.
    """
    
    def __init__(self):
        self.parser = NOXParser()
        self.optimizer = NOXOptimizer()
        self.decoder = NOXDecoder()
        self._enabled: Optional[bool] = None
        self._stats: Dict[str, Any] = {
            "total_validations": 0,
            "total_time_ms": 0.0,
            "total_token_savings": 0,
            "total_context_savings": 0,
            "validation_failures": 0,
            "fallback_count": 0
        }
    
    def is_enabled(self) -> bool:
        """Check if NOX integration is enabled."""
        if self._enabled is None:
            # Check status file
            try:
                import json
                from pathlib import Path
                
                status_file = Path.home() / ".hermes" / "nox_status.json"
                if status_file.exists():
                    with open(status_file, 'r') as f:
                        status = json.load(f)
                        self._enabled = status.get("enabled", False)
                else:
                    self._enabled = False
            except Exception:
                self._enabled = False
        
        return self._enabled if self._enabled else False
    
    def apply_nox_validation(
        self,
        response: str,
        messages: list,
        config: Optional[Dict[str, Any]] = None
    ) -> tuple[str, Dict[str, Any]]:
        """
        Apply NOX validation and optimization to a response.
        
        Args:
            response: Original response from agent
            messages: Conversation messages
            config: Optional configuration
        
        Returns:
            Tuple of (optimized_response, metadata)
        """
        start_time = time.time()
        
        # Initialize metadata
        metadata = {
            "nox_applied": False,
            "original_length": len(response),
            "optimized_length": len(response),
            "token_reduction": 0.0,
            "validation_time_ms": 0.0,
            "path": "none",
            "fallback_triggered": False,
            "reason": ""
        }
        
        try:
            # Determine optimization path
            path = self._determine_path(response, config)
            
            # Parse response to NOX program
            parse_result = self.parser.parse(response, path=path)
            
            if parse_result.errors:
                # Parse errors, fallback to original
                metadata["fallback_triggered"] = True
                metadata["reason"] = f"Parse errors: {', '.join(parse_result.errors)}"
                self._stats["validation_failures"] += 1
                self._stats["fallback_count"] += 1
                return response, metadata
            
            # Create IR from program
            ir = create_ir_from_program(parse_result.program, path=path)
            
            # Optimize IR
            if path == "fast":
                opt_result = self.optimizer.optimize_fast_path(ir)
            else:
                opt_result = self.optimizer.optimize_deep_path(ir)
            
            if not opt_result.success or opt_result.fallback_triggered:
                # Optimization failed, fallback to original
                metadata["fallback_triggered"] = True
                metadata["reason"] = opt_result.reason or "Optimization failed"
                self._stats["validation_failures"] += 1
                self._stats["fallback_count"] += 1
                return response, metadata
            
            # Verify optimized IR
            verification_results = verify_ir(opt_result.ir)
            
            if not verification_results['overall']['passed']:
                # Verification failed, fallback to original
                metadata["fallback_triggered"] = True
                metadata["reason"] = f"Verification failed: {verification_results['overall']['total_errors']} errors"
                self._stats["validation_failures"] += 1
                self._stats["fallback_count"] += 1
                return response, metadata
            
            # Decode IR back to natural language
            decode_result = self.decoder.decode(opt_result.ir)
            
            if not decode_result.success:
                # Decoding failed, fallback to original
                metadata["fallback_triggered"] = True
                metadata["reason"] = f"Decoding failed: {', '.join(decode_result.warnings)}"
                self._stats["validation_failures"] += 1
                self._stats["fallback_count"] += 1
                return response, metadata
            
            # Calculate metrics
            original_length = len(response)
            optimized_length = len(decode_result.text)
            token_reduction = ((original_length - optimized_length) / original_length) * 100 if original_length > 0 else 0.0
            validation_time = (time.time() - start_time) * 1000
            
            # Update metadata
            metadata.update({
                "nox_applied": True,
                "optimized_length": optimized_length,
                "token_reduction": token_reduction,
                "validation_time_ms": validation_time,
                "path": path,
                "iterations": opt_result.iterations,
                "compression_ratio": opt_result.compression_ratio,
                "reversibility_verified": decode_result.reversibility_verified
            })
            
            # Update stats
            self._stats["total_validations"] += 1
            self._stats["total_time_ms"] += validation_time
            self._stats["total_token_savings"] += (original_length - optimized_length)
            
            return decode_result.text, metadata
        
        except Exception as e:
            # Exception occurred, fallback to original
            metadata["fallback_triggered"] = True
            metadata["reason"] = f"Exception: {str(e)}"
            self._stats["validation_failures"] += 1
            self._stats["fallback_count"] += 1
            return response, metadata
    
    def _determine_path(self, response: str, config: Optional[Dict[str, Any]]) -> Literal["fast", "deep"]:
        """
        Determine optimization path based on response complexity.
        
        Args:
            response: Response to analyze
            config: Optional configuration
        
        Returns:
            "fast" or "deep" path
        """
        # For v1, use fast path for most queries
        # Use deep path only for complex responses
        
        response_length = len(response)
        
        # Simple heuristic: use deep path for long responses
        if response_length > 1000:
            return "deep"
        
        # Check config for override
        if config:
            path = config.get("path")
            if path in ("fast", "deep"):
                return path
        
        return "fast"
    
    def get_stats(self) -> Dict[str, Any]:
        """Get NOX integration statistics."""
        return self._stats.copy()


# Global integrator instance
_integrator = NOXAgentIntegrator()


def is_nox_enabled() -> bool:
    """Check if NOX is currently enabled."""
    return _integrator.is_enabled()


def should_apply_nox() -> bool:
    """Check if NOX should be applied to current response."""
    return is_nox_enabled()


def apply_nox_validation(
    response: str,
    messages: list,
    config: Optional[Dict[str, Any]] = None
) -> tuple[str, Dict[str, Any]]:
    """
    Apply NOX validation and optimization.
    
    Args:
        response: Original response from agent
        messages: Conversation messages
        config: Optional configuration
    
    Returns:
        Tuple of (optimized_response, metadata)
    """
    return _integrator.apply_nox_validation(response, messages, config)


def get_nox_metadata() -> Dict[str, Any]:
    """Get NOX configuration and status."""
    return {
        "enabled": is_nox_enabled(),
        "stats": _integrator.get_stats()
    }

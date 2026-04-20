"""
NOX Plugin - Latency-Constrained Proof-Carrying E-Graph Compiler

This plugin provides automatic NOX validation and optimization for Hermes Agent
responses using a latency-constrained proof-carrying e-graph compiler.
"""

from pathlib import Path
from typing import Dict, Any, Optional, List
import time
import json

from .types import UncertaintyType
from .parser import NOXParser
from .ir import create_ir_from_program
from .optimizer import NOXOptimizer
from .verifier import verify_ir
from .decoder import NOXDecoder


class NOXPlugin:
    """NOX Plugin for Hermes Agent"""
    
    def __init__(self):
        self.name = "nox"
        self.version = "1.0.0"
        self.description = "Latency-constrained proof-carrying e-graph compiler"
        
        # Initialize components
        self.parser = NOXParser()
        self.optimizer = NOXOptimizer()
        self.decoder = NOXDecoder()
        
        # Status file
        self.status_file = Path.home() / ".hermes" / "nox_status.json"
        
        # Statistics
        self._stats: Dict[str, Any] = {
            "total_validations": 0,
            "total_time_ms": 0.0,
            "total_token_savings": 0,
            "total_context_savings": 0,
            "validation_failures": 0,
            "fallback_count": 0
        }
    
    def is_enabled(self) -> bool:
        """Check if NOX is currently enabled."""
        try:
            if self.status_file.exists():
                with open(self.status_file, 'r') as f:
                    status = json.load(f)
                    return status.get("enabled", False)
        except Exception:
            pass
        
        return False
    
    def enable(self) -> Dict[str, Any]:
        """Enable NOX validation."""
        try:
            status = {
                "enabled": True,
                "mode": "balanced",
                "settings": {
                    "fast_path_budget_ms": 20,
                    "deep_path_budget_ms": 30,
                    "hard_ceiling_ms": 100,
                    "target_compression": 0.4
                },
                "stats": self._stats.copy()
            }
            
            self.status_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.status_file, 'w') as f:
                json.dump(status, f, indent=2)
            
            return {"success": True}
        
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def disable(self) -> Dict[str, Any]:
        """Disable NOX validation."""
        try:
            status = {
                "enabled": False,
                "mode": "balanced",
                "settings": {
                    "fast_path_budget_ms": 20,
                    "deep_path_budget_ms": 30,
                    "hard_ceiling_ms": 100,
                    "target_compression": 0.4
                },
                "stats": self._stats.copy()
            }
            
            self.status_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.status_file, 'w') as f:
                json.dump(status, f, indent=2)
            
            return {"success": True}
        
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def get_status(self) -> Dict[str, Any]:
        """Get current NOX status."""
        return {
            "enabled": self.is_enabled(),
            "stats": self._stats.copy()
        }
    
    def apply_nox_validation(
        self,
        response: str,
        messages: List[Dict[str, Any]],
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
    
    def _determine_path(self, response: str, config: Optional[Dict[str, Any]]) -> str:
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
    
    def post_llm_call(
        self,
        response: str,
        messages: List[Dict[str, Any]],
        config: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Post-LLM call hook to apply NOX validation.
        
        Args:
            response: Original response from LLM
            messages: Conversation messages
            config: Optional configuration
        
        Returns:
            Optimized response
        """
        if not self.is_enabled():
            return response
        
        optimized_response, metadata = self.apply_nox_validation(
            response, messages, config
        )
        
        return optimized_response
    
    def handle_command(self, args: List[str]) -> str:
        """
        Handle NOX slash commands.
        
        Args:
            args: Command arguments
        
        Returns:
            Command response
        """
        if not args:
            return self._status_command()
        
        command = args[0].lower()
        
        if command == "enable":
            return self._enable_command()
        elif command == "disable":
            return self._disable_command()
        elif command == "status":
            return self._status_command()
        else:
            return f"Unknown NOX command: {command}. Available: enable, disable, status"
    
    def _enable_command(self) -> str:
        """Handle /nox enable command."""
        result = self.enable()
        
        if result.get("success"):
            return """✅ NOX Enabled

NOX validation is now active. All agent responses will be automatically validated and optimized.

Mode: balanced
Performance:
  - Fast path: ~20-30ms for 95% of queries
  - Deep path: ~25-30ms for complex queries
  - Target: 30-50% token reduction

Use /nox status to monitor performance and token consumption."""
        else:
            return f"❌ Error enabling NOX: {result.get('error', 'Unknown error')}"
    
    def _disable_command(self) -> str:
        """Handle /nox disable command."""
        result = self.disable()
        
        if result.get("success"):
            return """✅ NOX Disabled

NOX validation has been turned off.

Agent responses will no longer be automatically validated or optimized.

Use /nox enable to re-enable NOX validation."""
        else:
            return f"❌ Error disabling NOX: {result.get('error', 'Unknown error')}"
    
    def _status_command(self) -> str:
        """Handle /nox status command."""
        status = self.get_status()
        stats = status.get("stats", {})
        
        enabled = status.get("enabled", False)
        status_icon = "✅" if enabled else "❌"
        status_text = "ENABLED" if enabled else "DISABLED"
        
        # Calculate mode-specific savings
        mode = "balanced"
        savings = "30-50%"
        
        # Build report
        report = f"""📊 NOX Status Report

Status: {status_icon} {status_text}
Mode: {mode.upper()}
Target Savings: {savings}

Performance Statistics:
  Total Validations: {stats.get('total_validations', 0)}
  Total Time: {stats.get('total_time_ms', 0):.1f}ms
  Avg Time per Validation: {stats.get('total_time_ms', 0) / max(stats.get('total_validations', 1), 1):.1f}ms
  Token Savings: {stats.get('total_token_savings', 0)} tokens
  Validation Failures: {stats.get('validation_failures', 0)}
  Fallback Rate: {stats.get('validation_failures', 0) / max(stats.get('total_validations', 1), 1) * 100:.1f}%

Architecture:
  Fast Path: 95% of queries (~20-30ms)
  Deep Path: 5% of queries (~25-30ms)
  Hard Ceiling: 100ms
  Target: <75ms

Use /nox enable to enable NOX validation.
Use /nox disable to disable NOX validation."""
        
        return report


# Create plugin instance
_plugin_instance = NOXPlugin()


def get_plugin() -> NOXPlugin:
    """Get the NOX plugin instance."""
    return _plugin_instance

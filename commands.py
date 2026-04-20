"""
NOX Commands - Slash Command Handlers

This module provides slash command handlers for NOX:
- /nox enable: Enable NOX validation
- /nox disable: Disable NOX validation
- /nox status: Show NOX status, token consumption, and configuration
"""

import json
from pathlib import Path
from typing import Dict, Any

from .integration import get_nox_metadata, is_nox_enabled


def command_enable() -> str:
    """Enable NOX validation."""
    try:
        # Enable NOX by updating status file
        status_file = Path.home() / ".hermes" / "nox_status.json"
        
        status = {
            "enabled": True,
            "mode": "balanced",
            "layers": {
                "pre_check": {"enabled": True},
                "structured_reasoning": {"enabled": True},
                "citation_verify": {"enabled": False}
            },
            "stats": {
                "total_validations": 0,
                "total_time_ms": 0.0,
                "total_token_savings": 0,
                "total_context_savings": 0,
                "validation_failures": 0
            }
        }
        
        status_file.parent.mkdir(parents=True, exist_ok=True)
        with open(status_file, 'w') as f:
            json.dump(status, f, indent=2)
        
        return f"""✅ NOX Enabled

NOX validation is now active. All agent responses will be automatically validated and optimized.

Mode: balanced
Layers:
  - Pre-check: enabled
  - Structured reasoning: enabled
  - Citation verification: disabled

Performance:
  - Zero overhead when disabled (<1ms)
  - Fast path: ~20-30ms for 95% of queries
  - Deep path: ~25-30ms for complex queries
  - Target: 30-50% token reduction

Use /nox status to monitor performance and token consumption."""
    
    except Exception as e:
        return f"❌ Error enabling NOX: {str(e)}"


def command_disable() -> str:
    """Disable NOX validation."""
    try:
        # Disable NOX by updating status file
        status_file = Path.home() / ".hermes" / "nox_status.json"
        
        status = {
            "enabled": False,
            "mode": "balanced",
            "layers": {
                "pre_check": {"enabled": False},
                "structured_reasoning": {"enabled": False},
                "citation_verify": {"enabled": False}
            },
            "stats": {
                "total_validations": 0,
                "total_time_ms": 0.0,
                "total_token_savings": 0,
                "total_context_savings": 0,
                "validation_failures": 0
            }
        }
        
        status_file.parent.mkdir(parents=True, exist_ok=True)
        with open(status_file, 'w') as f:
            json.dump(status, f, indent=2)
        
        return """✅ NOX Disabled

NOX validation has been turned off.

Agent responses will no longer be automatically validated or optimized.

Use /nox enable to re-enable NOX validation."""
    
    except Exception as e:
        return f"❌ Error disabling NOX: {str(e)}"


def command_status() -> str:
    """Show NOX status, token consumption, and configuration."""
    try:
        # Get current status
        enabled = is_nox_enabled()
        metadata = get_nox_metadata()
        stats = metadata.get("stats", {})
        
        # Build status report
        status_icon = "✅" if enabled else "❌"
        status_text = "ENABLED" if enabled else "DISABLED"
        
        # Get mode and layers
        status_file = Path.home() / ".hermes" / "nox_status.json"
        if status_file.exists():
            with open(status_file, 'r') as f:
                status_data = json.load(f)
                mode = status_data.get("mode", "balanced")
                layers = status_data.get("layers", {})
        else:
            mode = "balanced"
            layers = {}
        
        # Calculate mode-specific savings
        mode_savings = {
            "conservative": "20-30%",
            "balanced": "30-50%",
            "aggressive": "50-70%"
        }
        savings = mode_savings.get(mode, "30-50%")
        
        # Get layer configuration
        pre_check_enabled = layers.get("pre_check", {}).get("enabled", False)
        structured_enabled = layers.get("structured_reasoning", {}).get("enabled", False)
        citation_enabled = layers.get("citation_verify", {}).get("enabled", False)
        
        # Build report
        report = f"""📊 NOX Status Report

Status: {status_icon} {status_text}
Mode: {mode.upper()}
Target Savings: {savings}

Layers:
  Pre-check: {'✅' if pre_check_enabled else '❌'}
  Structured Reasoning: {'✅' if structured_enabled else '❌'}
  Citation Verification: {'✅' if citation_enabled else '❌'}

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
    
    except Exception as e:
        return f"❌ Error getting NOX status: {str(e)}"

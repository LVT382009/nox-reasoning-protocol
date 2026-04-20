"""
NOX Toggle - Enable/Disable NOX Validation

This module provides functions to enable and disable NOX validation,
with proper status management and configuration.
"""

import json
from pathlib import Path
from typing import Dict, Any, Optional


NOX_STATUS_FILE = Path.home() / ".hermes" / "nox_status.json"


def is_nox_enabled() -> bool:
    """
    Check if NOX is currently enabled.
    
    Returns:
        bool: True if NOX is enabled, False otherwise
    """
    try:
        if NOX_STATUS_FILE.exists():
            with open(NOX_STATUS_FILE, 'r') as f:
                status = json.load(f)
                return status.get("enabled", False)
    except Exception:
        pass
    
    return False


def get_nox_mode() -> str:
    """
    Get current NOX mode.
    
    Returns:
        str: Current mode (conservative, balanced, aggressive)
    """
    try:
        if NOX_STATUS_FILE.exists():
            with open(NOX_STATUS_FILE, 'r') as f:
                status = json.load(f)
                return status.get("mode", "balanced")
    except Exception:
        pass
    
    return "balanced"


def get_layer_config() -> Dict[str, Any]:
    """
    Get NOX layer configuration.
    
    Returns:
        dict: Layer configuration
    """
    try:
        if NOX_STATUS_FILE.exists():
            with open(NOX_STATUS_FILE, 'r') as f:
                status = json.load(f)
                return status.get("layers", {})
    except Exception:
        pass
    
    return {
        "pre_check": {"enabled": False},
        "structured_reasoning": {"enabled": False},
        "citation_verify": {"enabled": False}
    }


def enable_nox() -> Dict[str, Any]:
    """
    Enable NOX validation.
    
    Returns:
        dict: Result with success status and metadata
    """
    try:
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
        
        NOX_STATUS_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(NOX_STATUS_FILE, 'w') as f:
            json.dump(status, f, indent=2)
        
        return {"success": True}
    
    except Exception as e:
        return {"success": False, "error": str(e)}


def disable_nox() -> Dict[str, Any]:
    """
    Disable NOX validation.
    
    Returns:
        dict: Result with success status and metadata
    """
    try:
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
        
        NOX_STATUS_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(NOX_STATUS_FILE, 'w') as f:
            json.dump(status, f, indent=2)
        
        return {"success": True}
    
    except Exception as e:
        return {"success": False, "error": str(e)}


def get_nox_status() -> Dict[str, Any]:
    """
    Get current NOX status as a dictionary.
    
    Returns:
        dict: Current NOX status
    """
    return {
        "enabled": is_nox_enabled(),
        "mode": get_nox_mode(),
        "layers": get_layer_config()
    }


def print_status() -> None:
    """Print current NOX status."""
    status = get_nox_status()
    
    enabled = status.get("enabled", False)
    mode = status.get("mode", "balanced")
    layers = status.get("layers", {})
    
    status_icon = "✅" if enabled else "❌"
    status_text = "ENABLED" if enabled else "DISABLED"
    
    print(f"Status: {status_icon} {status_text}")
    print(f"Mode: {mode}")
    print(f"Layers:")
    print(f"  Pre-check: {'enabled' if layers.get('pre_check', {}).get('enabled') else 'disabled'}")
    print(f"  Structured Reasoning: {'enabled' if layers.get('structured_reasoning', {}).get('enabled') else 'disabled'}")
    print(f"  Citation Verification: {'enabled' if layers.get('citation_verify', {}).get('enabled') else 'disabled'}")

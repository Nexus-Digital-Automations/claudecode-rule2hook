#!/usr/bin/env python3
"""
Custom exceptions for rule2hook MCP server.

This module provides a hierarchy of domain-specific exceptions that enable
precise error handling and clear error messages throughout the application.
"""

from typing import Optional, Dict, Any, List
from dataclasses import dataclass


class Rule2HookError(Exception):
    """
    Base exception for all rule2hook errors.
    
    Provides structured error information with optional details dictionary
    for additional context that can be used for debugging or user feedback.
    """
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        self.message = message
        self.details = details or {}
    
    def __str__(self) -> str:
        if self.details:
            details_str = ", ".join(f"{k}={v}" for k, v in self.details.items())
            return f"{self.message} ({details_str})"
        return self.message


class ValidationError(Rule2HookError):
    """
    Input validation failed.
    
    Raised when user input doesn't meet expected format or constraints.
    """
    pass


class InstallationError(Rule2HookError):
    """
    Installation process failed.
    
    Raised when file operations or directory creation fails during
    rule2hook installation.
    """
    pass


class RuleParsingError(Rule2HookError):
    """
    Failed to parse rule into hook configuration.
    
    Raised when a natural language rule cannot be converted into
    a valid hook configuration.
    """
    def __init__(self, rule: str, reason: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            f"Failed to parse rule '{rule}': {reason}",
            details or {}
        )
        self.rule = rule
        self.reason = reason


class ConflictError(Rule2HookError):
    """
    Hook configuration conflict detected.
    
    Raised when attempting to merge hooks that would create conflicts.
    """
    def __init__(self, conflicts: List[Dict[str, str]], details: Optional[Dict[str, Any]] = None):
        conflict_count = len(conflicts)
        super().__init__(
            f"Detected {conflict_count} hook conflict{'s' if conflict_count != 1 else ''}",
            details or {"conflicts": conflicts}
        )
        self.conflicts = conflicts


class FileOperationError(Rule2HookError):
    """
    File operation failed.
    
    Raised when file read/write operations fail.
    """
    def __init__(self, operation: str, path: str, reason: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            f"Failed to {operation} file '{path}': {reason}",
            details or {"operation": operation, "path": path}
        )
        self.operation = operation
        self.path = path


class ConfigurationError(Rule2HookError):
    """
    Configuration is invalid or missing.
    
    Raised when required configuration is missing or malformed.
    """
    pass


class ToolExecutionError(Rule2HookError):
    """
    Tool execution failed.
    
    Raised when an MCP tool encounters an unrecoverable error during execution.
    """
    def __init__(self, tool_name: str, reason: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            f"Tool '{tool_name}' failed: {reason}",
            details or {"tool": tool_name}
        )
        self.tool_name = tool_name


@dataclass
class ErrorContext:
    """
    Context information for error handling.
    
    Provides structured information about where and why an error occurred.
    """
    operation: str
    location: str
    user_input: Optional[Any] = None
    system_state: Optional[Dict[str, Any]] = None
    recovery_suggestions: Optional[List[str]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for error details."""
        return {
            k: v for k, v in {
                "operation": self.operation,
                "location": self.location,
                "user_input": self.user_input,
                "system_state": self.system_state,
                "recovery_suggestions": self.recovery_suggestions
            }.items() if v is not None
        }
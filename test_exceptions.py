#!/usr/bin/env python3
"""
Test suite for custom exceptions module.

Tests the exception hierarchy, error context, and structured error information.
"""

import pytest
from exceptions import (
    Rule2HookError, ValidationError, InstallationError,
    RuleParsingError, ConflictError, FileOperationError,
    ConfigurationError, ToolExecutionError, ErrorContext
)


class TestExceptionHierarchy:
    """Test the exception class hierarchy."""
    
    def test_base_exception(self):
        """Test Rule2HookError base exception."""
        exc = Rule2HookError("Test error")
        assert str(exc) == "Test error"
        assert exc.message == "Test error"
        assert exc.details == {}
        
    def test_base_exception_with_details(self):
        """Test Rule2HookError with details."""
        details = {"key": "value", "number": 42}
        exc = Rule2HookError("Test error", details)
        assert exc.message == "Test error"
        assert exc.details == details
        assert str(exc) == "Test error (key=value, number=42)"
        
    def test_validation_error(self):
        """Test ValidationError."""
        exc = ValidationError("Invalid input")
        assert isinstance(exc, Rule2HookError)
        assert str(exc) == "Invalid input"
        
    def test_installation_error(self):
        """Test InstallationError."""
        exc = InstallationError("Failed to install", {"path": "/test"})
        assert isinstance(exc, Rule2HookError)
        assert exc.details["path"] == "/test"
        
    def test_rule_parsing_error(self):
        """Test RuleParsingError with custom attributes."""
        rule = "Format Python files"
        reason = "No command found"
        exc = RuleParsingError(rule, reason, {"line": 1})
        
        assert isinstance(exc, Rule2HookError)
        assert exc.rule == rule
        assert exc.reason == reason
        assert exc.details["line"] == 1
        assert str(exc) == f"Failed to parse rule '{rule}': {reason} (line=1)"
        
    def test_conflict_error(self):
        """Test ConflictError with conflict list."""
        conflicts = [
            {"event": "PostToolUse", "matcher": "Edit", "existing": "cmd1", "new": "cmd2"},
            {"event": "PreToolUse", "matcher": "Write", "existing": "cmd3", "new": "cmd4"}
        ]
        exc = ConflictError(conflicts)
        
        assert isinstance(exc, Rule2HookError)
        assert exc.conflicts == conflicts
        assert len(exc.conflicts) == 2
        assert "Detected 2 hook conflicts" in str(exc)
        
    def test_conflict_error_single(self):
        """Test ConflictError with single conflict."""
        conflicts = [{"event": "Stop", "matcher": "", "existing": "cmd1", "new": "cmd2"}]
        exc = ConflictError(conflicts)
        assert "Detected 1 hook conflict" in str(exc)  # No 's' for singular
        
    def test_file_operation_error(self):
        """Test FileOperationError."""
        exc = FileOperationError("read", "/path/to/file", "Permission denied")
        
        assert isinstance(exc, Rule2HookError)
        assert exc.operation == "read"
        assert exc.path == "/path/to/file"
        assert str(exc) == "Failed to read file '/path/to/file': Permission denied"
        
    def test_configuration_error(self):
        """Test ConfigurationError."""
        exc = ConfigurationError("Missing API key")
        assert isinstance(exc, Rule2HookError)
        
    def test_tool_execution_error(self):
        """Test ToolExecutionError."""
        exc = ToolExecutionError("convert_rules", "Invalid JSON input", {"line": 42})
        
        assert isinstance(exc, Rule2HookError)
        assert exc.tool_name == "convert_rules"
        assert str(exc) == "Tool 'convert_rules' failed: Invalid JSON input"
        assert exc.details["line"] == 42


class TestErrorContext:
    """Test the ErrorContext dataclass."""
    
    def test_minimal_context(self):
        """Test ErrorContext with minimal information."""
        ctx = ErrorContext(
            operation="test_op",
            location="test_module"
        )
        
        assert ctx.operation == "test_op"
        assert ctx.location == "test_module"
        assert ctx.user_input is None
        assert ctx.system_state is None
        assert ctx.recovery_suggestions is None
        
    def test_full_context(self):
        """Test ErrorContext with all fields."""
        ctx = ErrorContext(
            operation="parse_rule",
            location="rule_parser.py:123",
            user_input="Format Python files",
            system_state={"rules_processed": 5},
            recovery_suggestions=["Check rule syntax", "Use backticks for commands"]
        )
        
        assert ctx.operation == "parse_rule"
        assert ctx.location == "rule_parser.py:123"
        assert ctx.user_input == "Format Python files"
        assert ctx.system_state["rules_processed"] == 5
        assert len(ctx.recovery_suggestions) == 2
        
    def test_context_to_dict(self):
        """Test ErrorContext.to_dict() method."""
        # Minimal context
        ctx1 = ErrorContext("op1", "loc1")
        dict1 = ctx1.to_dict()
        assert dict1 == {"operation": "op1", "location": "loc1"}
        assert "user_input" not in dict1  # None values excluded
        
        # Full context
        ctx2 = ErrorContext(
            operation="op2",
            location="loc2",
            user_input="input",
            system_state={"key": "value"},
            recovery_suggestions=["tip1"]
        )
        dict2 = ctx2.to_dict()
        assert dict2["operation"] == "op2"
        assert dict2["location"] == "loc2"
        assert dict2["user_input"] == "input"
        assert dict2["system_state"] == {"key": "value"}
        assert dict2["recovery_suggestions"] == ["tip1"]


class TestExceptionUsagePatterns:
    """Test common usage patterns for exceptions."""
    
    def test_exception_chaining(self):
        """Test that exceptions can be chained properly."""
        try:
            try:
                raise ValueError("Original error")
            except ValueError as e:
                raise ValidationError("Wrapped error", {"original": str(e)}) from e
        except ValidationError as exc:
            assert exc.__cause__ is not None
            assert isinstance(exc.__cause__, ValueError)
            assert exc.details["original"] == "Original error"
            
    def test_exception_context_integration(self):
        """Test integrating ErrorContext with exceptions."""
        ctx = ErrorContext(
            operation="validate_input",
            location="validator.py:50",
            user_input={"rule": "test"},
            recovery_suggestions=["Check input format"]
        )
        
        exc = ValidationError("Invalid format", details=ctx.to_dict())
        
        assert exc.details["operation"] == "validate_input"
        assert exc.details["location"] == "validator.py:50"
        assert exc.details["recovery_suggestions"] == ["Check input format"]
        
    def test_nested_exception_details(self):
        """Test exceptions with nested detail structures."""
        details = {
            "operation": "complex_op",
            "errors": [
                {"field": "name", "error": "too long"},
                {"field": "path", "error": "invalid"}
            ],
            "metadata": {
                "timestamp": "2025-01-03T12:00:00",
                "version": "1.0"
            }
        }
        
        exc = ToolExecutionError("complex_tool", "Multiple validation failures", details)
        
        assert len(exc.details["errors"]) == 2
        assert exc.details["metadata"]["version"] == "1.0"
        
    @pytest.mark.parametrize("exc_class,args", [
        (ValidationError, ("Test",)),
        (InstallationError, ("Test", {"path": "/"})),
        (ConfigurationError, ("Test",)),
        (FileOperationError, ("read", "/file", "Error")),
        (ToolExecutionError, ("tool", "Error")),
    ])
    def test_all_exceptions_are_rule2hook_errors(self, exc_class, args):
        """Test that all custom exceptions inherit from Rule2HookError."""
        exc = exc_class(*args)
        assert isinstance(exc, Rule2HookError)
        assert isinstance(exc, Exception)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
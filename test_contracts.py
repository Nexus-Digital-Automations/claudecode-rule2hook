#!/usr/bin/env python3
"""
Test suite for Design by Contract implementation.

Tests preconditions, postconditions, and contract validators.
"""

import pytest
import asyncio
from pathlib import Path
import tempfile
import json

from contracts import (
    require, ensure,
    path_exists, path_is_directory, string_not_empty,
    list_not_empty, valid_json, result_has_key, result_status_success
)
from exceptions import ValidationError


class TestPreconditions:
    """Test the @require decorator for preconditions."""
    
    def test_sync_function_passing_precondition(self):
        """Test synchronous function with passing precondition."""
        @require(lambda args: args['value'] > 0)
        def add_one(value: int) -> int:
            return value + 1
        
        assert add_one(5) == 6
        assert add_one(100) == 101
        
    def test_sync_function_failing_precondition(self):
        """Test synchronous function with failing precondition."""
        @require(lambda args: args['value'] > 0)
        def add_one(value: int) -> int:
            return value + 1
        
        with pytest.raises(ValidationError) as exc_info:
            add_one(-1)
        assert "Precondition failed" in str(exc_info.value)
        
    @pytest.mark.asyncio
    async def test_async_function_passing_precondition(self):
        """Test async function with passing precondition."""
        @require(lambda args: len(args['text']) > 0)
        async def process_text(text: str) -> str:
            await asyncio.sleep(0.01)
            return text.upper()
        
        result = await process_text("hello")
        assert result == "HELLO"
        
    @pytest.mark.asyncio
    async def test_async_function_failing_precondition(self):
        """Test async function with failing precondition."""
        @require(lambda args: len(args['text']) > 0)
        async def process_text(text: str) -> str:
            await asyncio.sleep(0.01)
            return text.upper()
        
        with pytest.raises(ValidationError) as exc_info:
            await process_text("")
        assert "Precondition failed" in str(exc_info.value)
        
    def test_multiple_preconditions(self):
        """Test function with multiple preconditions."""
        @require(
            lambda args: args['a'] > 0,
            lambda args: args['b'] > 0,
            lambda args: args['a'] < args['b']
        )
        def divide(a: int, b: int) -> float:
            return a / b
        
        assert divide(1, 2) == 0.5
        
        # First condition fails
        with pytest.raises(ValidationError):
            divide(-1, 2)
            
        # Second condition fails
        with pytest.raises(ValidationError):
            divide(1, 0)
            
        # Third condition fails
        with pytest.raises(ValidationError):
            divide(2, 1)
            
    def test_precondition_with_default_args(self):
        """Test precondition with default arguments."""
        @require(lambda args: args['multiplier'] > 0)
        def multiply(value: int, multiplier: int = 2) -> int:
            return value * multiplier
        
        assert multiply(5) == 10  # Uses default multiplier=2
        assert multiply(5, 3) == 15
        
        # Should fail when explicit multiplier is invalid
        with pytest.raises(ValidationError):
            multiply(5, -1)
            
    def test_precondition_with_docstring(self):
        """Test that precondition docstrings are included in error messages."""
        def positive_value(args):
            """Value must be positive"""
            return args['value'] > 0
        
        @require(positive_value)
        def sqrt(value: float) -> float:
            return value ** 0.5
        
        with pytest.raises(ValidationError) as exc_info:
            sqrt(-1)
        assert "Value must be positive" in str(exc_info.value)


class TestPostconditions:
    """Test the @ensure decorator for postconditions."""
    
    def test_sync_function_passing_postcondition(self):
        """Test synchronous function with passing postcondition."""
        @ensure(lambda result, args: result > args['value'])
        def increment(value: int) -> int:
            return value + 1
        
        assert increment(5) == 6
        
    def test_sync_function_failing_postcondition(self):
        """Test synchronous function with failing postcondition."""
        @ensure(lambda result, args: result > args['value'])
        def bad_increment(value: int) -> int:
            return value  # Bug: doesn't actually increment
        
        with pytest.raises(ValidationError) as exc_info:
            bad_increment(5)
        assert "Postcondition failed" in str(exc_info.value)
        
    @pytest.mark.asyncio
    async def test_async_function_postcondition(self):
        """Test async function with postcondition."""
        @ensure(lambda result, args: len(result) == len(args['text']))
        async def process(text: str) -> str:
            await asyncio.sleep(0.01)
            return text.upper()
        
        result = await process("hello")
        assert result == "HELLO"
        
    def test_postcondition_validates_type(self):
        """Test postcondition that validates return type."""
        @ensure(lambda result, args: isinstance(result, dict))
        @ensure(lambda result, args: 'status' in result)
        def create_response(message: str) -> dict:
            return {"status": "ok", "message": message}
        
        response = create_response("test")
        assert response["status"] == "ok"
        
        # Test with buggy implementation
        @ensure(lambda result, args: isinstance(result, dict))
        def buggy_response(message: str) -> dict:
            return "not a dict"  # Type error
        
        with pytest.raises(ValidationError):
            buggy_response("test")
            
    def test_combined_pre_and_postconditions(self):
        """Test function with both preconditions and postconditions."""
        @require(lambda args: args['n'] >= 0)
        @ensure(lambda result, args: result >= 1)
        def factorial(n: int) -> int:
            if n == 0:
                return 1
            result = 1
            for i in range(1, n + 1):
                result *= i
            return result
        
        assert factorial(0) == 1
        assert factorial(5) == 120
        
        # Precondition fails
        with pytest.raises(ValidationError):
            factorial(-1)


class TestContractValidators:
    """Test the predefined contract validator functions."""
    
    def test_path_exists_validator(self):
        """Test path_exists validator."""
        with tempfile.TemporaryDirectory() as tmpdir:
            temp_file = Path(tmpdir) / "test.txt"
            temp_file.write_text("test")
            
            validator = path_exists('file_path')
            
            # Existing path
            assert validator({'file_path': str(temp_file)}) is True
            
            # Non-existing path
            assert validator({'file_path': str(Path(tmpdir) / "missing.txt")}) is False
            
            # None value (should return True to let other validators handle)
            assert validator({'file_path': None}) is True
            
    def test_path_is_directory_validator(self):
        """Test path_is_directory validator."""
        with tempfile.TemporaryDirectory() as tmpdir:
            temp_file = Path(tmpdir) / "test.txt"
            temp_file.write_text("test")
            
            validator = path_is_directory('dir_path')
            
            # Directory
            assert validator({'dir_path': tmpdir}) is True
            
            # File (not directory)
            assert validator({'dir_path': str(temp_file)}) is False
            
            # Non-existing path
            assert validator({'dir_path': str(Path(tmpdir) / "missing")}) is False
            
    def test_string_not_empty_validator(self):
        """Test string_not_empty validator."""
        validator = string_not_empty('name')
        
        assert validator({'name': 'test'}) is True
        assert validator({'name': '  spaces  '}) is True
        assert validator({'name': ''}) is False
        assert validator({'name': '   '}) is False  # Only whitespace
        assert validator({'name': None}) is True  # Let other validators handle None
        assert validator({'name': 123}) is False  # Not a string
        
    def test_list_not_empty_validator(self):
        """Test list_not_empty validator."""
        validator = list_not_empty('items')
        
        assert validator({'items': [1, 2, 3]}) is True
        assert validator({'items': ['a']}) is True
        assert validator({'items': []}) is False
        assert validator({'items': None}) is True  # Let other validators handle None
        assert validator({'items': 'not a list'}) is False
        
    def test_valid_json_validator(self):
        """Test valid_json validator."""
        validator = valid_json('json_data')
        
        assert validator({'json_data': '{"key": "value"}'}) is True
        assert validator({'json_data': '[]'}) is True
        assert validator({'json_data': 'null'}) is True
        assert validator({'json_data': '{"invalid": json}'}) is False
        assert validator({'json_data': ''}) is False
        assert validator({'json_data': None}) is True
        assert validator({'json_data': 123}) is True  # Not a string, so skip
        
    def test_result_has_key_validator(self):
        """Test result_has_key validator."""
        validator = result_has_key('status')
        
        assert validator({'status': 'ok'}, {}) is True
        assert validator({'status': None}, {}) is True  # Key exists, value is None
        assert validator({'other': 'value'}, {}) is False
        assert validator([], {}) is False  # Not a dict
        
    def test_result_status_success_validator(self):
        """Test result_status_success validator."""
        validator = result_status_success()
        
        assert validator({'status': 'success'}, {}) is True
        assert validator({'other': 'data'}, {}) is True  # No status key is ok
        assert validator({'status': 'error'}, {}) is False
        assert validator({'status': 'warning'}, {}) is False
        assert validator([], {}) is False  # Not a dict


class TestContractIntegration:
    """Test integration of contracts with real functions."""
    
    def test_file_processing_with_contracts(self):
        """Test a file processing function with contracts."""
        @require(
            string_not_empty('file_path'),
            path_exists('file_path')
        )
        @ensure(
            lambda result, args: isinstance(result, str),
            lambda result, args: len(result) > 0
        )
        def read_file_uppercase(file_path: str) -> str:
            with open(file_path, 'r') as f:
                return f.read().upper()
        
        with tempfile.NamedTemporaryFile(mode='w', delete=False) as tmp:
            tmp.write("hello world")
            tmp_path = tmp.name
        
        try:
            result = read_file_uppercase(tmp_path)
            assert result == "HELLO WORLD"
            
            # Test with empty path
            with pytest.raises(ValidationError):
                read_file_uppercase("")
                
            # Test with non-existent path
            with pytest.raises(ValidationError):
                read_file_uppercase("/non/existent/path")
        finally:
            Path(tmp_path).unlink()
            
    @pytest.mark.asyncio
    async def test_async_api_call_with_contracts(self):
        """Test an async API call function with contracts."""
        @require(
            string_not_empty('endpoint'),
            lambda args: args['timeout'] > 0
        )
        @ensure(
            result_has_key('status'),
            result_has_key('data')
        )
        async def mock_api_call(endpoint: str, timeout: int = 30) -> dict:
            await asyncio.sleep(0.01)
            return {
                "status": "success",
                "data": {"endpoint": endpoint, "timeout": timeout}
            }
        
        result = await mock_api_call("/api/test")
        assert result["status"] == "success"
        
        # Test precondition failures
        with pytest.raises(ValidationError):
            await mock_api_call("")  # Empty endpoint
            
        with pytest.raises(ValidationError):
            await mock_api_call("/api/test", timeout=-1)  # Invalid timeout


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
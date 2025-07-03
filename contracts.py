#!/usr/bin/env python3
"""
Design by Contract implementation for rule2hook MCP server.

This module provides decorators and utilities for implementing contracts
(preconditions, postconditions, and invariants) following ADDER+ protocols.
"""

import asyncio
import inspect
from functools import wraps
from typing import Callable, Any, Dict, List, Optional, TypeVar, Union
from pathlib import Path

from exceptions import ValidationError, ErrorContext

T = TypeVar('T')


def require(*conditions: Callable[[Dict[str, Any]], bool]) -> Callable:
    """
    Precondition decorator for validating function inputs.
    
    Each condition is a callable that receives the bound arguments
    as a dictionary and returns True if the condition is satisfied.
    
    Example:
        @require(
            lambda args: args['value'] > 0,
            lambda args: len(args['text']) < 1000
        )
        async def process(value: int, text: str): ...
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            # Bind arguments to get a dictionary of all parameters
            sig = inspect.signature(func)
            bound = sig.bind(*args, **kwargs)
            bound.apply_defaults()
            
            # Check each precondition
            for i, condition in enumerate(conditions):
                try:
                    if not condition(bound.arguments):
                        # Try to get condition description from docstring or name
                        cond_name = getattr(condition, '__doc__', f'Precondition {i+1}')
                        if not cond_name or cond_name.strip() == '':
                            cond_name = f'Precondition {i+1}'
                        
                        context = ErrorContext(
                            operation=f"Calling {func.__name__}",
                            location=f"{func.__module__}.{func.__name__}",
                            user_input=bound.arguments
                        )
                        raise ValidationError(
                            f"Precondition failed in {func.__name__}: {cond_name}",
                            details=context.to_dict()
                        )
                except Exception as e:
                    if isinstance(e, ValidationError):
                        raise
                    # Re-raise other exceptions with context
                    raise ValidationError(
                        f"Error evaluating precondition in {func.__name__}: {str(e)}",
                        details={"original_error": str(e), "condition_index": i}
                    )
            
            return await func(*args, **kwargs)
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            sig = inspect.signature(func)
            bound = sig.bind(*args, **kwargs)
            bound.apply_defaults()
            
            for i, condition in enumerate(conditions):
                try:
                    if not condition(bound.arguments):
                        cond_name = getattr(condition, '__doc__', f'Precondition {i+1}')
                        if not cond_name or cond_name.strip() == '':
                            cond_name = f'Precondition {i+1}'
                        
                        context = ErrorContext(
                            operation=f"Calling {func.__name__}",
                            location=f"{func.__module__}.{func.__name__}",
                            user_input=bound.arguments
                        )
                        raise ValidationError(
                            f"Precondition failed in {func.__name__}: {cond_name}",
                            details=context.to_dict()
                        )
                except Exception as e:
                    if isinstance(e, ValidationError):
                        raise
                    raise ValidationError(
                        f"Error evaluating precondition in {func.__name__}: {str(e)}",
                        details={"original_error": str(e), "condition_index": i}
                    )
            
            return func(*args, **kwargs)
        
        # Return appropriate wrapper based on function type
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    
    return decorator


def ensure(*conditions: Callable[[Any, Dict[str, Any]], bool]) -> Callable:
    """
    Postcondition decorator for validating function outputs.
    
    Each condition is a callable that receives the result and original
    arguments as parameters and returns True if satisfied.
    
    Example:
        @ensure(
            lambda result, args: result > args['input_value'],
            lambda result, args: isinstance(result, int)
        )
        async def calculate(input_value: int) -> int: ...
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            sig = inspect.signature(func)
            bound = sig.bind(*args, **kwargs)
            bound.apply_defaults()
            
            # Execute the function
            result = await func(*args, **kwargs)
            
            # Check each postcondition
            for i, condition in enumerate(conditions):
                try:
                    if not condition(result, bound.arguments):
                        cond_name = getattr(condition, '__doc__', f'Postcondition {i+1}')
                        if not cond_name or cond_name.strip() == '':
                            cond_name = f'Postcondition {i+1}'
                        
                        context = ErrorContext(
                            operation=f"Result validation for {func.__name__}",
                            location=f"{func.__module__}.{func.__name__}",
                            user_input=bound.arguments,
                            system_state={"result": result}
                        )
                        raise ValidationError(
                            f"Postcondition failed in {func.__name__}: {cond_name}",
                            details=context.to_dict()
                        )
                except Exception as e:
                    if isinstance(e, ValidationError):
                        raise
                    raise ValidationError(
                        f"Error evaluating postcondition in {func.__name__}: {str(e)}",
                        details={"original_error": str(e), "condition_index": i}
                    )
            
            return result
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            sig = inspect.signature(func)
            bound = sig.bind(*args, **kwargs)
            bound.apply_defaults()
            
            result = func(*args, **kwargs)
            
            for i, condition in enumerate(conditions):
                try:
                    if not condition(result, bound.arguments):
                        cond_name = getattr(condition, '__doc__', f'Postcondition {i+1}')
                        if not cond_name or cond_name.strip() == '':
                            cond_name = f'Postcondition {i+1}'
                        
                        context = ErrorContext(
                            operation=f"Result validation for {func.__name__}",
                            location=f"{func.__module__}.{func.__name__}",
                            user_input=bound.arguments,
                            system_state={"result": result}
                        )
                        raise ValidationError(
                            f"Postcondition failed in {func.__name__}: {cond_name}",
                            details=context.to_dict()
                        )
                except Exception as e:
                    if isinstance(e, ValidationError):
                        raise
                    raise ValidationError(
                        f"Error evaluating postcondition in {func.__name__}: {str(e)}",
                        details={"original_error": str(e), "condition_index": i}
                    )
            
            return result
        
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    
    return decorator


# Predefined validation functions for common scenarios
def path_exists(param_name: str) -> Callable[[Dict[str, Any]], bool]:
    """Validates that a path parameter exists."""
    def validator(args: Dict[str, Any]) -> bool:
        path = args.get(param_name)
        if path is None:
            return True  # Let other validators handle None
        return Path(path).exists()
    validator.__doc__ = f"Path '{param_name}' must exist"
    return validator


def path_is_directory(param_name: str) -> Callable[[Dict[str, Any]], bool]:
    """Validates that a path parameter is a directory."""
    def validator(args: Dict[str, Any]) -> bool:
        path = args.get(param_name)
        if path is None:
            return True
        p = Path(path)
        return p.exists() and p.is_dir()
    validator.__doc__ = f"Path '{param_name}' must be a directory"
    return validator


def string_not_empty(param_name: str) -> Callable[[Dict[str, Any]], bool]:
    """Validates that a string parameter is not empty."""
    def validator(args: Dict[str, Any]) -> bool:
        value = args.get(param_name)
        if value is None:
            return True
        return isinstance(value, str) and len(value.strip()) > 0
    validator.__doc__ = f"Parameter '{param_name}' must not be empty"
    return validator


def list_not_empty(param_name: str) -> Callable[[Dict[str, Any]], bool]:
    """Validates that a list parameter is not empty."""
    def validator(args: Dict[str, Any]) -> bool:
        value = args.get(param_name)
        if value is None:
            return True
        return isinstance(value, list) and len(value) > 0
    validator.__doc__ = f"List '{param_name}' must not be empty"
    return validator


def valid_json(param_name: str) -> Callable[[Dict[str, Any]], bool]:
    """Validates that a string parameter contains valid JSON."""
    import json
    def validator(args: Dict[str, Any]) -> bool:
        value = args.get(param_name)
        if value is None or not isinstance(value, str):
            return True
        try:
            json.loads(value)
            return True
        except json.JSONDecodeError:
            return False
    validator.__doc__ = f"Parameter '{param_name}' must be valid JSON"
    return validator


def result_has_key(key: str) -> Callable[[Any, Dict[str, Any]], bool]:
    """Validates that result dictionary has a specific key."""
    def validator(result: Any, args: Dict[str, Any]) -> bool:
        return isinstance(result, dict) and key in result
    validator.__doc__ = f"Result must have key '{key}'"
    return validator


def result_status_success() -> Callable[[Any, Dict[str, Any]], bool]:
    """Validates that result has status='success' or no status key."""
    def validator(result: Any, args: Dict[str, Any]) -> bool:
        if not isinstance(result, dict):
            return False
        status = result.get('status')
        return status is None or status == 'success'
    validator.__doc__ = "Result status must be 'success' or undefined"
    return validator
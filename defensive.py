#!/usr/bin/env python3
"""
Defensive programming utilities for rule2hook MCP server.

This module provides guard clauses, safe defaults, and validation utilities
to ensure robust error handling and prevent edge case failures.
"""

import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Union, TypeVar, Callable
from functools import wraps
import logging

from exceptions import ValidationError, FileOperationError, ErrorContext

T = TypeVar('T')

# Configure logging for defensive operations
logger = logging.getLogger(__name__)


def guard_not_none(value: Optional[T], name: str, default: Optional[T] = None) -> T:
    """
    Guard clause that ensures a value is not None.
    
    Args:
        value: The value to check
        name: Parameter name for error messages
        default: Optional default value if None
        
    Returns:
        The value if not None, or default if provided
        
    Raises:
        ValidationError: If value is None and no default provided
    """
    if value is None:
        if default is not None:
            logger.debug(f"Using default value for {name}: {default}")
            return default
        raise ValidationError(
            f"Required parameter '{name}' cannot be None",
            details={"parameter": name}
        )
    return value


def guard_path_exists(path: Union[str, Path], name: str) -> Path:
    """
    Guard clause that ensures a path exists.
    
    Args:
        path: Path to validate
        name: Parameter name for error messages
        
    Returns:
        Path object if path exists
        
    Raises:
        ValidationError: If path doesn't exist
    """
    path_obj = Path(path).expanduser().resolve()
    if not path_obj.exists():
        raise ValidationError(
            f"Path '{path}' does not exist",
            details={
                "parameter": name,
                "path": str(path),
                "resolved_path": str(path_obj)
            }
        )
    return path_obj


def guard_directory_writable(path: Union[str, Path], name: str, create: bool = False) -> Path:
    """
    Guard clause that ensures a directory exists and is writable.
    
    Args:
        path: Directory path to validate
        name: Parameter name for error messages
        create: Whether to create directory if it doesn't exist
        
    Returns:
        Path object if directory is writable
        
    Raises:
        ValidationError: If directory doesn't exist or isn't writable
    """
    path_obj = Path(path).expanduser().resolve()
    
    if not path_obj.exists():
        if create:
            try:
                path_obj.mkdir(parents=True, exist_ok=True)
                logger.info(f"Created directory: {path_obj}")
            except Exception as e:
                raise FileOperationError(
                    "create directory",
                    str(path_obj),
                    str(e),
                    details={"parameter": name}
                )
        else:
            raise ValidationError(
                f"Directory '{path}' does not exist",
                details={"parameter": name, "path": str(path)}
            )
    
    if not path_obj.is_dir():
        raise ValidationError(
            f"Path '{path}' is not a directory",
            details={"parameter": name, "path": str(path)}
        )
    
    # Check if writable by attempting to create a temp file
    test_file = path_obj / ".write_test"
    try:
        test_file.touch()
        test_file.unlink()
    except Exception as e:
        raise ValidationError(
            f"Directory '{path}' is not writable",
            details={
                "parameter": name,
                "path": str(path),
                "error": str(e)
            }
        )
    
    return path_obj


def safe_json_parse(json_string: str, default: Optional[Dict] = None) -> Dict[str, Any]:
    """
    Safely parse JSON with fallback to default.
    
    Args:
        json_string: JSON string to parse
        default: Default value if parsing fails
        
    Returns:
        Parsed JSON or default value
    """
    if not json_string or not isinstance(json_string, str):
        logger.debug("Empty or non-string JSON input, returning default")
        return default or {}
    
    try:
        return json.loads(json_string)
    except json.JSONDecodeError as e:
        logger.warning(f"Failed to parse JSON: {e}")
        if default is not None:
            return default
        raise ValidationError(
            "Invalid JSON format",
            details={
                "error": str(e),
                "position": e.pos if hasattr(e, 'pos') else None,
                "line": e.lineno if hasattr(e, 'lineno') else None
            }
        )


def safe_file_read(file_path: Union[str, Path], encoding: str = 'utf-8') -> str:
    """
    Safely read a file with proper error handling.
    
    Args:
        file_path: Path to file
        encoding: File encoding
        
    Returns:
        File contents as string
        
    Raises:
        FileOperationError: If file cannot be read
    """
    path_obj = Path(file_path).expanduser().resolve()
    
    try:
        with open(path_obj, 'r', encoding=encoding) as f:
            return f.read()
    except FileNotFoundError:
        raise FileOperationError(
            "read",
            str(path_obj),
            "File not found"
        )
    except PermissionError:
        raise FileOperationError(
            "read",
            str(path_obj),
            "Permission denied"
        )
    except UnicodeDecodeError as e:
        raise FileOperationError(
            "read",
            str(path_obj),
            f"Unicode decode error: {e}",
            details={"encoding": encoding}
        )
    except Exception as e:
        raise FileOperationError(
            "read",
            str(path_obj),
            str(e)
        )


def safe_file_write(
    file_path: Union[str, Path],
    content: str,
    encoding: str = 'utf-8',
    create_parents: bool = True,
    backup: bool = False
) -> Path:
    """
    Safely write to a file with proper error handling.
    
    Args:
        file_path: Path to file
        content: Content to write
        encoding: File encoding
        create_parents: Whether to create parent directories
        backup: Whether to create backup of existing file
        
    Returns:
        Path object of written file
        
    Raises:
        FileOperationError: If file cannot be written
    """
    path_obj = Path(file_path).expanduser().resolve()
    
    # Create parent directories if needed
    if create_parents and not path_obj.parent.exists():
        try:
            path_obj.parent.mkdir(parents=True, exist_ok=True)
            logger.info(f"Created parent directories for: {path_obj}")
        except Exception as e:
            raise FileOperationError(
                "create parent directory",
                str(path_obj.parent),
                str(e)
            )
    
    # Backup existing file if requested
    if backup and path_obj.exists():
        backup_path = path_obj.with_suffix(path_obj.suffix + '.backup')
        try:
            import shutil
            shutil.copy2(path_obj, backup_path)
            logger.info(f"Created backup: {backup_path}")
        except Exception as e:
            logger.warning(f"Failed to create backup: {e}")
    
    # Write the file
    try:
        with open(path_obj, 'w', encoding=encoding) as f:
            f.write(content)
        return path_obj
    except PermissionError:
        raise FileOperationError(
            "write",
            str(path_obj),
            "Permission denied"
        )
    except Exception as e:
        raise FileOperationError(
            "write",
            str(path_obj),
            str(e)
        )


def bounded_string(value: str, max_length: int, name: str) -> str:
    """
    Ensure string is within length bounds.
    
    Args:
        value: String to validate
        max_length: Maximum allowed length
        name: Parameter name for error messages
        
    Returns:
        The string if within bounds
        
    Raises:
        ValidationError: If string exceeds max length
    """
    if len(value) > max_length:
        raise ValidationError(
            f"Parameter '{name}' exceeds maximum length of {max_length}",
            details={
                "parameter": name,
                "actual_length": len(value),
                "max_length": max_length,
                "preview": value[:50] + "..." if len(value) > 50 else value
            }
        )
    return value


def sanitize_path_component(component: str) -> str:
    """
    Sanitize a string to be safe for use in file paths.
    
    Args:
        component: String to sanitize
        
    Returns:
        Sanitized string safe for file paths
    """
    # Remove or replace unsafe characters
    unsafe_chars = ['/', '\\', ':', '*', '?', '"', '<', '>', '|', '\0']
    sanitized = component
    for char in unsafe_chars:
        sanitized = sanitized.replace(char, '_')
    
    # Remove leading/trailing dots and spaces
    sanitized = sanitized.strip('. ')
    
    # Ensure not empty
    if not sanitized:
        sanitized = "unnamed"
    
    return sanitized


def retry_on_error(
    max_attempts: int = 3,
    exceptions: tuple = (Exception,),
    delay: float = 0.1
) -> Callable:
    """
    Decorator to retry a function on specific exceptions.
    
    Args:
        max_attempts: Maximum number of attempts
        exceptions: Tuple of exceptions to catch
        delay: Delay between attempts in seconds
        
    Returns:
        Decorated function
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            import asyncio
            last_exception = None
            
            for attempt in range(max_attempts):
                try:
                    return await func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    if attempt < max_attempts - 1:
                        logger.warning(
                            f"Attempt {attempt + 1} failed for {func.__name__}: {e}. Retrying..."
                        )
                        await asyncio.sleep(delay * (attempt + 1))
                    else:
                        logger.error(
                            f"All {max_attempts} attempts failed for {func.__name__}"
                        )
            
            raise last_exception
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            import time
            last_exception = None
            
            for attempt in range(max_attempts):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    if attempt < max_attempts - 1:
                        logger.warning(
                            f"Attempt {attempt + 1} failed for {func.__name__}: {e}. Retrying..."
                        )
                        time.sleep(delay * (attempt + 1))
                    else:
                        logger.error(
                            f"All {max_attempts} attempts failed for {func.__name__}"
                        )
            
            raise last_exception
        
        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    
    return decorator
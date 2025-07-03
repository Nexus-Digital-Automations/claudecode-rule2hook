#!/usr/bin/env python3
"""
Rule2Hook MCP Server v2 - Enhanced with ADDER+ techniques

This MCP server provides tools for:
1. Installing rule2hook command in a project
2. Converting rules to hooks
3. Validating hooks configuration
4. Detecting merge conflicts

Enhanced with:
- Design by Contract (preconditions/postconditions)
- Defensive programming patterns
- Comprehensive error handling
- Type safety
"""

import json
import os
import re
import shutil
import sys
import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Literal, NewType, TypedDict
from typing_extensions import Annotated

from fastmcp import FastMCP, Context
from pydantic import Field

# Import our advanced error handling modules
from exceptions import (
    ValidationError, InstallationError, RuleParsingError,
    ConflictError, FileOperationError, ConfigurationError,
    ToolExecutionError, ErrorContext
)
from contracts import (
    require, ensure, path_exists, path_is_directory,
    string_not_empty, valid_json, result_has_key, result_status_success
)
from defensive import (
    guard_not_none, guard_path_exists, guard_directory_writable,
    safe_json_parse, safe_file_read, safe_file_write,
    bounded_string, sanitize_path_component, retry_on_error
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/rule2hook_mcp.log'),
        logging.StreamHandler(sys.stderr)
    ]
)
logger = logging.getLogger(__name__)

# Type definitions for better type safety
ProjectPath = NewType('ProjectPath', Path)
HooksConfig = TypedDict('HooksConfig', {'hooks': Dict[str, List[Dict[str, any]]]})
RuleConversion = TypedDict('RuleConversion', {
    'rule': str,
    'event': str,
    'tools': List[str],
    'command': str
})

# Initialize the MCP server
mcp = FastMCP(
    name="rule2hook-setup-v2",
    version="2.0.0",
    instructions="Enhanced MCP server with advanced error handling and contracts. Use install_rule2hook to set up the command in a project, then use convert_rules to transform natural language rules into Claude Code hooks."
)

# Path to the rule2hook.md template (relative to this script)
SCRIPT_DIR = Path(__file__).parent
RULE2HOOK_TEMPLATE = SCRIPT_DIR / ".claude" / "commands" / "rule2hook.md"

# Constants with validation
MAX_RULE_LENGTH = 500
MAX_COMMAND_LENGTH = 1000
MAX_PATH_LENGTH = 4096

# Hook events and their characteristics
HOOK_EVENTS = {
    "PreToolUse": {
        "keywords": ["before", "check", "validate", "prevent", "scan", "verify"],
        "description": "Runs BEFORE a tool is executed"
    },
    "PostToolUse": {
        "keywords": ["after", "following", "once done", "when finished"],
        "description": "Runs AFTER a tool completes successfully"
    },
    "Stop": {
        "keywords": ["finish", "complete", "end task", "done", "wrap up"],
        "description": "Runs when Claude Code finishes responding"
    },
    "Notification": {
        "keywords": ["notify", "alert", "inform", "message"],
        "description": "Runs when Claude Code sends notifications"
    }
}

# Tool matchers for different tools
TOOL_MATCHERS = [
    "Task", "Bash", "Glob", "Grep", "Read", "Edit", 
    "MultiEdit", "Write", "WebFetch", "WebSearch", 
    "TodoRead", "TodoWrite"
]


@mcp.tool()
@require(
    string_not_empty('project_path'),
    lambda args: len(args['project_path']) < MAX_PATH_LENGTH
)
@ensure(
    result_has_key('status'),
    result_has_key('message')
)
async def install_rule2hook(
    project_path: Annotated[str, Field(description="Path to the project where rule2hook should be installed")],
    ctx: Context,
    installation_type: Annotated[Literal["project", "global"], Field(description="Whether to install for this project only or globally")] = "project"
) -> Dict[str, str]:
    """
    Install the rule2hook command in a project or globally.
    
    This copies the necessary files to enable the /project:rule2hook or /rule2hook command
    in Claude Code.
    
    Contracts:
        Preconditions:
            - project_path must not be empty
            - project_path length < MAX_PATH_LENGTH
        Postconditions:
            - Result contains 'status' and 'message' keys
    """
    try:
        # Defensive: Validate and sanitize inputs
        project_path_obj = guard_path_exists(project_path, "project_path")
        
        if not project_path_obj.is_dir():
            raise ValidationError(
                f"Project path is not a directory: {project_path}",
                details={"path": str(project_path)}
            )
        
        # Check if source file exists
        if not RULE2HOOK_TEMPLATE.exists():
            raise ConfigurationError(
                f"rule2hook.md template not found at {RULE2HOOK_TEMPLATE}",
                details={"template_path": str(RULE2HOOK_TEMPLATE)}
            )
        
        # Determine target directory with validation
        if installation_type == "global":
            target_dir = guard_directory_writable(
                Path.home() / ".claude" / "commands",
                "global_commands_dir",
                create=True
            )
            command_prefix = "/rule2hook"
        else:
            target_dir = guard_directory_writable(
                project_path_obj / ".claude" / "commands",
                "project_commands_dir",
                create=True
            )
            command_prefix = "/project:rule2hook"
        
        await ctx.info(f"Target directory prepared: {target_dir}")
        
        # Copy the rule2hook.md file
        target_file = target_dir / "rule2hook.md"
        
        # Check if file already exists
        if target_file.exists():
            await ctx.warning(f"rule2hook.md already exists at {target_file}")
            return {
                "status": "warning",
                "message": f"rule2hook command already installed. Use {command_prefix} in Claude Code.",
                "location": str(target_file),
                "existing": True
            }
        
        # Copy the file with error handling
        try:
            shutil.copy2(RULE2HOOK_TEMPLATE, target_file)
            await ctx.info(f"Successfully copied rule2hook.md to {target_file}")
        except Exception as e:
            raise InstallationError(
                f"Failed to copy template file: {e}",
                details={
                    "source": str(RULE2HOOK_TEMPLATE),
                    "destination": str(target_file),
                    "error": str(e)
                }
            )
        
        logger.info(f"Installed rule2hook to {target_file} ({installation_type})")
        
        return {
            "status": "success",
            "message": f"Successfully installed rule2hook command. Use {command_prefix} in Claude Code when in the project directory.",
            "location": str(target_file),
            "command": command_prefix,
            "installation_type": installation_type
        }
        
    except Exception as e:
        logger.error(f"Failed to install rule2hook: {e}")
        if isinstance(e, (ValidationError, InstallationError, ConfigurationError)):
            raise
        # Wrap unexpected errors
        raise ToolExecutionError(
            "install_rule2hook",
            str(e),
            details={"project_path": project_path, "installation_type": installation_type}
        )


@mcp.tool()
@require(
    string_not_empty('rules'),
    lambda args: len(args['rules']) < MAX_RULE_LENGTH * 10  # Allow multiple rules
)
@ensure(
    result_has_key('status'),
    result_has_key('hooks_config'),
    lambda result, args: result['status'] in ['success', 'partial', 'error']
)
async def convert_rules(
    rules: Annotated[str, Field(description="Comma-separated natural language rules to convert to hooks")],
    ctx: Context,
    merge_with_existing: Annotated[bool, Field(description="Whether to merge with existing hooks or create new config")] = True
) -> Dict[str, any]:
    """
    Convert natural language rules into Claude Code hook configurations.
    
    Examples:
    - "Format Python files with black after editing"
    - "Run git status when finishing a task"
    - "Check for TODO comments before committing"
    
    Contracts:
        Preconditions:
            - rules must not be empty
            - rules total length must be reasonable
        Postconditions:
            - Result contains status and hooks_config
            - Status is one of: success, partial, error
    """
    try:
        # Defensive: Sanitize and validate input
        rules_text = bounded_string(rules.strip(), MAX_RULE_LENGTH * 10, "rules")
        
        # Split rules by comma or semicolon
        rule_list = [
            bounded_string(r.strip(), MAX_RULE_LENGTH, f"rule_{i}")
            for i, r in enumerate(re.split(r'[,;]', rules_text))
            if r.strip()
        ]
        
        if not rule_list:
            raise ValidationError("No valid rules found after parsing")
        
        hooks_config: HooksConfig = {"hooks": {}}
        converted_rules: List[RuleConversion] = []
        failed_rules: List[Dict[str, str]] = []
        
        for rule in rule_list:
            try:
                await ctx.info(f"Analyzing rule: {rule}")
                
                # Analyze the rule with error handling
                event = _determine_event(rule)
                tools = _determine_tools(rule)
                command = _extract_command(rule)
                
                if not command:
                    raise RuleParsingError(
                        rule,
                        "Could not determine command from rule"
                    )
                
                # Validate command
                command = bounded_string(command, MAX_COMMAND_LENGTH, "command")
                
                # Create hook configuration
                hook_entry = {
                    "type": "command",
                    "command": command
                }
                
                # Build the configuration
                if event not in hooks_config["hooks"]:
                    hooks_config["hooks"][event] = []
                
                # Check if we need a matcher
                if event != "Stop" and tools:
                    matcher = "|".join(tools)
                    hook_group = {
                        "matcher": matcher,
                        "hooks": [hook_entry]
                    }
                else:
                    hook_group = {
                        "hooks": [hook_entry]
                    }
                
                hooks_config["hooks"][event].append(hook_group)
                
                converted_rules.append({
                    "rule": rule,
                    "event": event,
                    "tools": tools,
                    "command": command
                })
                
                await ctx.info(f"Converted: {rule} -> {event} event with command: {command}")
                
            except RuleParsingError as e:
                logger.warning(f"Failed to parse rule: {e}")
                failed_rules.append({
                    "rule": rule,
                    "error": str(e)
                })
                await ctx.warning(f"Could not parse rule: {rule}")
            except Exception as e:
                logger.error(f"Unexpected error parsing rule '{rule}': {e}")
                failed_rules.append({
                    "rule": rule,
                    "error": f"Unexpected error: {str(e)}"
                })
        
        # Determine overall status
        if not converted_rules:
            status = "error"
            message = f"Failed to convert any rules. {len(failed_rules)} rules had errors."
        elif failed_rules:
            status = "partial"
            message = f"Converted {len(converted_rules)} rules, {len(failed_rules)} failed."
        else:
            status = "success"
            message = f"Successfully converted {len(converted_rules)} rules"
        
        logger.info(f"Rule conversion completed: {status} - {message}")
        
        return {
            "status": status,
            "message": message,
            "hooks_config": hooks_config,
            "converted_rules": converted_rules,
            "failed_rules": failed_rules,
            "json": json.dumps(hooks_config, indent=2)
        }
        
    except Exception as e:
        logger.error(f"Failed to convert rules: {e}")
        if isinstance(e, (ValidationError, RuleParsingError)):
            raise
        raise ToolExecutionError(
            "convert_rules",
            str(e),
            details={"rules": rules[:100] + "..." if len(rules) > 100 else rules}
        )


# Continue with other tools...
# (The rest of the implementation would follow similar patterns)
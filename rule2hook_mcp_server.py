#!/usr/bin/env python3
"""
Rule2Hook MCP Server - Helps users install and use claudecode-rule2hook in their projects

This MCP server provides tools for:
1. Installing rule2hook command in a project
2. Converting rules to hooks
3. Validating hooks configuration
4. Detecting merge conflicts
"""

import json
import os
import re
import shutil
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Literal
from typing_extensions import Annotated

from fastmcp import FastMCP, Context
from pydantic import Field

# Initialize the MCP server
mcp = FastMCP(
    name="rule2hook-setup",
    version="1.0.0",
    instructions="MCP server to help install and use claudecode-rule2hook in projects. Use install_rule2hook to set up the command in a project, then use convert_rules to transform natural language rules into Claude Code hooks."
)

# Path to the rule2hook.md template (relative to this script)
SCRIPT_DIR = Path(__file__).parent
RULE2HOOK_TEMPLATE = SCRIPT_DIR / ".claude" / "commands" / "rule2hook.md"

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
async def install_rule2hook(
    project_path: Annotated[str, Field(description="Path to the project where rule2hook should be installed")],
    ctx: Context,
    installation_type: Annotated[Literal["project", "global"], Field(description="Whether to install for this project only or globally")] = "project"
) -> Dict[str, str]:
    """
    Install the rule2hook command in a project or globally.
    
    This copies the necessary files to enable the /project:rule2hook or /rule2hook command
    in Claude Code.
    """
    project_path = Path(project_path).expanduser().resolve()
    
    # Validate project path
    if not project_path.exists():
        return {"status": "error", "message": f"Project path does not exist: {project_path}"}
    
    if not project_path.is_dir():
        return {"status": "error", "message": f"Project path is not a directory: {project_path}"}
    
    # Check if source file exists
    if not RULE2HOOK_TEMPLATE.exists():
        return {"status": "error", "message": f"rule2hook.md template not found at {RULE2HOOK_TEMPLATE}"}
    
    # Determine target directory
    if installation_type == "global":
        target_dir = Path.home() / ".claude" / "commands"
        command_prefix = "/rule2hook"
    else:
        target_dir = project_path / ".claude" / "commands"
        command_prefix = "/project:rule2hook"
    
    # Create target directory if it doesn't exist
    target_dir.mkdir(parents=True, exist_ok=True)
    await ctx.info(f"Created directory: {target_dir}")
    
    # Copy the rule2hook.md file
    target_file = target_dir / "rule2hook.md"
    
    # Check if file already exists
    if target_file.exists():
        await ctx.warning(f"rule2hook.md already exists at {target_file}")
        return {
            "status": "warning",
            "message": f"rule2hook command already installed. Use {command_prefix} in Claude Code.",
            "location": str(target_file)
        }
    
    # Copy the file
    shutil.copy2(RULE2HOOK_TEMPLATE, target_file)
    await ctx.info(f"Copied rule2hook.md to {target_file}")
    
    return {
        "status": "success",
        "message": f"Successfully installed rule2hook command. Use {command_prefix} in Claude Code when in the project directory.",
        "location": str(target_file),
        "command": command_prefix
    }


@mcp.tool()
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
    """
    # Split rules by comma or semicolon
    rule_list = [r.strip() for r in re.split(r'[,;]', rules) if r.strip()]
    
    if not rule_list:
        return {"status": "error", "message": "No rules provided"}
    
    hooks_config = {"hooks": {}}
    converted_rules = []
    
    for rule in rule_list:
        await ctx.info(f"Analyzing rule: {rule}")
        
        # Analyze the rule
        event = _determine_event(rule)
        tools = _determine_tools(rule)
        command = _extract_command(rule)
        
        if not command:
            await ctx.warning(f"Could not determine command for rule: {rule}")
            continue
        
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
    
    return {
        "status": "success",
        "message": f"Successfully converted {len(converted_rules)} rules",
        "hooks_config": hooks_config,
        "converted_rules": converted_rules,
        "json": json.dumps(hooks_config, indent=2)
    }


@mcp.tool()
async def validate_hooks(
    hooks_file_path: Annotated[str, Field(description="Path to the hooks.json file to validate")],
    ctx: Context
) -> Dict[str, any]:
    """
    Validate a hooks.json file for correct structure and common issues.
    """
    file_path = Path(hooks_file_path).expanduser().resolve()
    
    if not file_path.exists():
        return {"status": "error", "message": f"File does not exist: {file_path}"}
    
    try:
        with open(file_path, 'r') as f:
            config = json.load(f)
        await ctx.info("Successfully parsed JSON")
    except json.JSONDecodeError as e:
        return {"status": "error", "message": f"JSON parsing error: {e}"}
    
    # Validate structure
    issues = []
    warnings = []
    hook_count = 0
    
    if not isinstance(config, dict):
        issues.append("Root element must be an object")
        return {"status": "error", "message": "Invalid structure", "issues": issues}
    
    if "hooks" not in config:
        issues.append("Missing 'hooks' key")
        return {"status": "error", "message": "Invalid structure", "issues": issues}
    
    hooks = config["hooks"]
    if not isinstance(hooks, dict):
        issues.append("'hooks' must be an object")
        return {"status": "error", "message": "Invalid structure", "issues": issues}
    
    # Validate each event type
    valid_events = {"PreToolUse", "PostToolUse", "Stop", "Notification"}
    hooks_summary = []
    
    for event, event_hooks in hooks.items():
        if event not in valid_events:
            warnings.append(f"Unknown event type: {event}")
        
        if not isinstance(event_hooks, list):
            issues.append(f"Value of {event} must be an array")
            continue
        
        await ctx.info(f"Validating {event} ({len(event_hooks)} configurations)")
        
        for i, hook_group in enumerate(event_hooks):
            if not isinstance(hook_group, dict):
                issues.append(f"{event}[{i}] must be an object")
                continue
            
            # Check matcher (optional)
            matcher = hook_group.get("matcher", "")
            
            # Check hooks array
            if "hooks" not in hook_group:
                issues.append(f"{event}[{i}] missing 'hooks' array")
                continue
            
            hook_list = hook_group["hooks"]
            if not isinstance(hook_list, list):
                issues.append(f"{event}[{i}].hooks must be an array")
                continue
            
            for j, hook in enumerate(hook_list):
                if not isinstance(hook, dict):
                    issues.append(f"{event}[{i}].hooks[{j}] must be an object")
                    continue
                
                # Validate hook type and command
                hook_type = hook.get("type")
                command = hook.get("command")
                
                if hook_type != "command":
                    warnings.append(f"{event}[{i}].hooks[{j}] has type: {hook_type} (expected: command)")
                
                if not command:
                    issues.append(f"{event}[{i}].hooks[{j}] missing command")
                else:
                    hook_count += 1
                    hooks_summary.append({
                        "event": event,
                        "matcher": matcher or "All tools",
                        "command": command[:50] + "..." if len(command) > 50 else command
                    })
    
    await ctx.report_progress(100, 100, "Validation complete")
    
    return {
        "status": "success" if not issues else "error",
        "message": f"Found {hook_count} valid hooks",
        "issues": issues,
        "warnings": warnings,
        "hooks_summary": hooks_summary,
        "total_hooks": hook_count
    }


@mcp.tool()
async def detect_conflicts(
    existing_hooks_path: Annotated[str, Field(description="Path to existing hooks.json file")],
    new_hooks_json: Annotated[str, Field(description="JSON string of new hooks to check for conflicts")],
    ctx: Context
) -> Dict[str, any]:
    """
    Check if new hooks would conflict with existing hooks (same event + matcher).
    """
    existing_path = Path(existing_hooks_path).expanduser().resolve()
    
    if not existing_path.exists():
        return {
            "status": "success",
            "message": "No existing hooks file - no conflicts possible",
            "has_conflicts": False
        }
    
    try:
        with open(existing_path, 'r') as f:
            existing_config = json.load(f)
        new_config = json.loads(new_hooks_json)
    except json.JSONDecodeError as e:
        return {"status": "error", "message": f"JSON parsing error: {e}"}
    
    existing_hooks = existing_config.get("hooks", {})
    new_hooks = new_config.get("hooks", {})
    
    conflicts = []
    
    # Build a mapping of existing event/matcher combinations
    existing_matchers = {}
    for event, hooks_list in existing_hooks.items():
        existing_matchers[event] = {}
        for hook_group in hooks_list:
            matcher = hook_group.get("matcher", "")
            if matcher:
                # Store the first command found for this event/matcher pair
                first_command = hook_group.get("hooks", [{}])[0].get("command", "")
                existing_matchers[event][matcher] = first_command
    
    # Check if any new hook conflicts with existing ones
    for event, new_hooks_list in new_hooks.items():
        if event in existing_matchers:
            for new_hook_group in new_hooks_list:
                new_matcher = new_hook_group.get("matcher", "")
                if new_matcher and new_matcher in existing_matchers[event]:
                    # CONFLICT! Same event and matcher already defined
                    existing_command = existing_matchers[event][new_matcher]
                    new_command = new_hook_group.get("hooks", [{}])[0].get("command", "")
                    
                    conflicts.append({
                        "event": event,
                        "matcher": new_matcher,
                        "existing_command": existing_command,
                        "new_command": new_command
                    })
                    
                    await ctx.warning(f"Conflict in {event} for matcher '{new_matcher}'")
    
    return {
        "status": "success",
        "message": f"Found {len(conflicts)} conflicts" if conflicts else "No conflicts found",
        "has_conflicts": len(conflicts) > 0,
        "conflicts": conflicts
    }


@mcp.tool()
async def list_project_rules(
    project_path: Annotated[str, Field(description="Path to the project to check for CLAUDE.md files")],
    ctx: Context
) -> Dict[str, any]:
    """
    List rules found in CLAUDE.md files in a project.
    """
    project_path = Path(project_path).expanduser().resolve()
    
    if not project_path.exists() or not project_path.is_dir():
        return {"status": "error", "message": f"Invalid project path: {project_path}"}
    
    # Look for CLAUDE.md files
    claude_files = [
        project_path / "CLAUDE.md",
        project_path / "CLAUDE.local.md",
        Path.home() / ".claude" / "CLAUDE.md"
    ]
    
    all_rules = []
    files_found = []
    
    for claude_file in claude_files:
        if claude_file.exists():
            await ctx.info(f"Reading {claude_file}")
            files_found.append(str(claude_file))
            
            with open(claude_file, 'r') as f:
                content = f.read()
            
            # Extract rules (look for lines that start with - or * in rules sections)
            rules = []
            in_rules_section = False
            
            for line in content.split('\n'):
                line_lower = line.lower()
                
                # Check if we're entering a rules section
                if 'rules' in line_lower and line.startswith('#'):
                    in_rules_section = True
                    continue
                
                # Check if we're leaving the rules section
                if in_rules_section and line.startswith('#') and 'rules' not in line_lower:
                    in_rules_section = False
                
                # Extract rules
                if in_rules_section and (line.strip().startswith('-') or line.strip().startswith('*')):
                    rule = line.strip().lstrip('-*').strip()
                    if rule:
                        rules.append(rule)
            
            all_rules.extend(rules)
    
    return {
        "status": "success",
        "message": f"Found {len(all_rules)} rules in {len(files_found)} files",
        "files_found": files_found,
        "rules": all_rules
    }


# Helper functions for rule analysis
def _determine_event(rule: str) -> str:
    """Determine the hook event from the rule text."""
    rule_lower = rule.lower()
    
    # Check for event keywords
    for event, info in HOOK_EVENTS.items():
        for keyword in info["keywords"]:
            if keyword in rule_lower:
                return event
    
    # Default to PostToolUse for rules about "editing" or "modifying"
    if any(word in rule_lower for word in ["edit", "modify", "save", "write"]):
        return "PostToolUse"
    
    return "Stop"  # Default fallback


def _determine_tools(rule: str) -> List[str]:
    """Determine which tools should be matched from the rule text."""
    rule_lower = rule.lower()
    tools = []
    
    # Check for file-related operations
    if any(word in rule_lower for word in ["edit", "modify", "save", "file", "code"]):
        tools.extend(["Edit", "MultiEdit", "Write"])
    
    # Check for command execution
    if any(word in rule_lower for word in ["command", "bash", "shell", "execute", "run"]):
        if "bash" not in tools:
            tools.append("Bash")
    
    # Check for search operations
    if any(word in rule_lower for word in ["search", "find", "grep"]):
        tools.extend(["Grep", "Glob"])
    
    # Check for reading operations
    if "read" in rule_lower:
        tools.append("Read")
    
    # Check for web operations
    if any(word in rule_lower for word in ["web", "fetch", "download"]):
        tools.extend(["WebFetch", "WebSearch"])
    
    # Check for todo operations
    if "todo" in rule_lower:
        tools.extend(["TodoRead", "TodoWrite"])
    
    # Remove duplicates while preserving order
    seen = set()
    unique_tools = []
    for tool in tools:
        if tool not in seen:
            seen.add(tool)
            unique_tools.append(tool)
    return unique_tools


def _extract_command(rule: str) -> Optional[str]:
    """Extract or generate a command from the rule text."""
    rule_lower = rule.lower()
    
    # Check for commands in backticks or quotes
    backtick_match = re.search(r'`([^`]+)`', rule)
    if backtick_match:
        return backtick_match.group(1)
    
    quote_match = re.search(r'"([^"]+)"', rule)
    if quote_match and any(char in quote_match.group(1) for char in [' ', '/', '-']):
        return quote_match.group(1)
    
    # Common patterns
    if "black" in rule_lower and "python" in rule_lower:
        return "black . --quiet 2>/dev/null || true"
    
    if "prettier" in rule_lower:
        return "prettier --write . 2>/dev/null || true"
    
    if "git status" in rule_lower:
        return "git status"
    
    if "npm test" in rule_lower:
        return "npm test 2>/dev/null || echo 'Tests need attention'"
    
    if "npm run lint" in rule_lower:
        return "npm run lint 2>/dev/null || true"
    
    if "todo" in rule_lower and "comment" in rule_lower:
        return "grep -r 'TODO' . 2>/dev/null || echo 'No TODOs found'"
    
    if "secret" in rule_lower or "credential" in rule_lower:
        return "git secrets --scan 2>/dev/null || echo 'No secrets found'"
    
    # Try to extract a verb and object
    verb_match = re.search(r'\b(run|execute|check|validate|format|scan)\s+(\S+)', rule_lower)
    if verb_match:
        return f"{verb_match.group(2)} 2>/dev/null || true"
    
    return None


# Resources
@mcp.resource("data://rule2hook/examples")
def get_rule_examples() -> Dict[str, List[Dict[str, str]]]:
    """Provides example rules and their conversions."""
    return {
        "formatting": [
            {
                "rule": "Format Python files with black after editing",
                "event": "PostToolUse",
                "matcher": "Edit|MultiEdit|Write",
                "command": "black . --quiet 2>/dev/null || true"
            },
            {
                "rule": "Run prettier on JavaScript files after saving",
                "event": "PostToolUse",
                "matcher": "Edit|MultiEdit|Write",
                "command": "prettier --write '**/*.js' 2>/dev/null || true"
            }
        ],
        "testing": [
            {
                "rule": "Run tests after modifying test files",
                "event": "PostToolUse",
                "matcher": "Edit|MultiEdit|Write",
                "command": "npm test 2>/dev/null || echo 'Tests need attention'"
            }
        ],
        "git": [
            {
                "rule": "Show git status when finishing work",
                "event": "Stop",
                "matcher": "",
                "command": "git status"
            }
        ],
        "validation": [
            {
                "rule": "Check for TODO comments before committing",
                "event": "PreToolUse",
                "matcher": "Bash",
                "command": "grep -r 'TODO' . 2>/dev/null || echo 'No TODOs found'"
            }
        ]
    }


@mcp.resource("data://rule2hook/documentation")
def get_documentation() -> str:
    """Provides documentation for using rule2hook."""
    return """# Rule2Hook MCP Server Documentation

## Overview
This MCP server helps you install and use the claudecode-rule2hook functionality in your projects.

## Tools Available

### 1. install_rule2hook
Installs the rule2hook command in a project or globally.

**Parameters:**
- `project_path`: Path to the project
- `installation_type`: "project" (default) or "global"

**Example:**
```
install_rule2hook("/path/to/my/project", "project")
```

### 2. convert_rules
Converts natural language rules into Claude Code hook configurations.

**Parameters:**
- `rules`: Comma-separated rules
- `merge_with_existing`: Whether to merge with existing hooks

**Example:**
```
convert_rules("Format Python files after editing, Run git status when done", true)
```

### 3. validate_hooks
Validates a hooks.json file for correct structure.

**Parameters:**
- `hooks_file_path`: Path to hooks.json file

### 4. detect_conflicts
Checks if new hooks would conflict with existing ones.

**Parameters:**
- `existing_hooks_path`: Path to existing hooks.json
- `new_hooks_json`: JSON string of new hooks

### 5. list_project_rules
Lists rules found in CLAUDE.md files in a project.

**Parameters:**
- `project_path`: Path to the project

## Common Rule Patterns

1. **Formatting**: "Format [language] files after editing"
2. **Testing**: "Run tests when modifying test files"
3. **Git**: "Execute git [command] when [event]"
4. **Validation**: "Check/Validate [something] before [action]"
5. **Custom**: Use backticks for specific commands: "Run `npm run build` after editing"

## Best Practices

1. Be specific about when hooks should run (before/after)
2. Use backticks for exact commands
3. Test hooks before applying them widely
4. Use quiet flags to avoid cluttering output
5. Add error handling with `|| true` to prevent blocking
"""


def main():
    """Main entry point for the MCP server."""
    import sys
    
    # Check for command line arguments
    if len(sys.argv) > 1 and sys.argv[1] == "--http":
        print("Running server on http://127.0.0.1:8000", file=sys.stderr)
        mcp.run(transport="streamable-http", host="127.0.0.1", port=8000)
    else:
        # Default to stdio for Claude Desktop
        mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
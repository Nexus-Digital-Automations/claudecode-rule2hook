#!/usr/bin/env python3
"""
Test suite for the Rule2Hook MCP Server
"""

import json
import pytest
import tempfile
from pathlib import Path
from fastmcp import Client
from rule2hook_mcp_server import mcp as mcp_server


@pytest.fixture
def mcp():
    """Provides the server instance for tests."""
    return mcp_server


@pytest.fixture
def temp_project_dir():
    """Creates a temporary project directory for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.mark.asyncio
async def test_install_rule2hook_project(mcp, temp_project_dir):
    """Test installing rule2hook in a project."""
    async with Client(mcp) as client:
        result = await client.call_tool(
            "install_rule2hook",
            {
                "project_path": str(temp_project_dir),
                "installation_type": "project"
            }
        )
        
        result_data = json.loads(result[0].text)
        assert result_data["status"] == "success"
        assert "Successfully installed" in result_data["message"]
        assert "/project:rule2hook" in result_data["command"]
        
        # Check that the file was created
        rule2hook_file = temp_project_dir / ".claude" / "commands" / "rule2hook.md"
        assert rule2hook_file.exists()


@pytest.mark.asyncio
async def test_convert_rules_basic(mcp):
    """Test converting basic rules to hooks."""
    async with Client(mcp) as client:
        result = await client.call_tool(
            "convert_rules",
            {
                "rules": "Format Python files with black after editing",
                "merge_with_existing": False
            }
        )
        
        result_data = json.loads(result[0].text)
        assert result_data["status"] == "success"
        assert len(result_data["converted_rules"]) == 1
        
        # Check the generated hook
        hooks_config = result_data["hooks_config"]
        assert "PostToolUse" in hooks_config["hooks"]
        assert len(hooks_config["hooks"]["PostToolUse"]) == 1
        
        hook_group = hooks_config["hooks"]["PostToolUse"][0]
        assert hook_group["matcher"] == "Edit|MultiEdit|Write"
        assert "black" in hook_group["hooks"][0]["command"]


@pytest.mark.asyncio
async def test_convert_multiple_rules(mcp):
    """Test converting multiple rules."""
    async with Client(mcp) as client:
        result = await client.call_tool(
            "convert_rules",
            {
                "rules": "Run git status when done, Check for TODOs before committing",
                "merge_with_existing": False
            }
        )
        
        result_data = json.loads(result[0].text)
        assert result_data["status"] == "success"
        assert len(result_data["converted_rules"]) == 2
        
        hooks_config = result_data["hooks_config"]
        # Should have Stop event for git status
        assert "Stop" in hooks_config["hooks"]
        # Should have PreToolUse for TODO check
        assert "PreToolUse" in hooks_config["hooks"]


@pytest.mark.asyncio
async def test_validate_hooks_valid(mcp, temp_project_dir):
    """Test validating a valid hooks file."""
    # Create a valid hooks file
    hooks_file = temp_project_dir / "hooks.json"
    valid_hooks = {
        "hooks": {
            "PostToolUse": [
                {
                    "matcher": "Edit",
                    "hooks": [
                        {
                            "type": "command",
                            "command": "echo 'test'"
                        }
                    ]
                }
            ]
        }
    }
    
    with open(hooks_file, 'w') as f:
        json.dump(valid_hooks, f)
    
    async with Client(mcp) as client:
        result = await client.call_tool(
            "validate_hooks",
            {"hooks_file_path": str(hooks_file)}
        )
        
        result_data = json.loads(result[0].text)
        assert result_data["status"] == "success"
        assert result_data["total_hooks"] == 1
        assert len(result_data["issues"]) == 0


@pytest.mark.asyncio
async def test_validate_hooks_invalid(mcp, temp_project_dir):
    """Test validating an invalid hooks file."""
    # Create an invalid hooks file
    hooks_file = temp_project_dir / "hooks.json"
    invalid_hooks = {
        "hooks": {
            "InvalidEvent": "not-an-array"  # Should be an array
        }
    }
    
    with open(hooks_file, 'w') as f:
        json.dump(invalid_hooks, f)
    
    async with Client(mcp) as client:
        result = await client.call_tool(
            "validate_hooks",
            {"hooks_file_path": str(hooks_file)}
        )
        
        result_data = json.loads(result[0].text)
        assert result_data["status"] == "error"
        assert len(result_data["issues"]) > 0


@pytest.mark.asyncio
async def test_detect_conflicts_no_conflicts(mcp, temp_project_dir):
    """Test conflict detection with no conflicts."""
    # Create existing hooks file
    existing_file = temp_project_dir / "existing.json"
    existing_hooks = {
        "hooks": {
            "PostToolUse": [
                {
                    "matcher": "Edit",
                    "hooks": [{"type": "command", "command": "black ."}]
                }
            ]
        }
    }
    
    with open(existing_file, 'w') as f:
        json.dump(existing_hooks, f)
    
    # New hooks with different matcher
    new_hooks = {
        "hooks": {
            "PostToolUse": [
                {
                    "matcher": "Write",
                    "hooks": [{"type": "command", "command": "prettier ."}]
                }
            ]
        }
    }
    
    async with Client(mcp) as client:
        result = await client.call_tool(
            "detect_conflicts",
            {
                "existing_hooks_path": str(existing_file),
                "new_hooks_json": json.dumps(new_hooks)
            }
        )
        
        result_data = json.loads(result[0].text)
        assert result_data["status"] == "success"
        assert not result_data["has_conflicts"]


@pytest.mark.asyncio
async def test_detect_conflicts_with_conflicts(mcp, temp_project_dir):
    """Test conflict detection with conflicts."""
    # Create existing hooks file
    existing_file = temp_project_dir / "existing.json"
    existing_hooks = {
        "hooks": {
            "PostToolUse": [
                {
                    "matcher": "Edit",
                    "hooks": [{"type": "command", "command": "black ."}]
                }
            ]
        }
    }
    
    with open(existing_file, 'w') as f:
        json.dump(existing_hooks, f)
    
    # New hooks with same matcher - conflict!
    new_hooks = {
        "hooks": {
            "PostToolUse": [
                {
                    "matcher": "Edit",
                    "hooks": [{"type": "command", "command": "autopep8 ."}]
                }
            ]
        }
    }
    
    async with Client(mcp) as client:
        result = await client.call_tool(
            "detect_conflicts",
            {
                "existing_hooks_path": str(existing_file),
                "new_hooks_json": json.dumps(new_hooks)
            }
        )
        
        result_data = json.loads(result[0].text)
        assert result_data["status"] == "success"
        assert result_data["has_conflicts"]
        assert len(result_data["conflicts"]) == 1
        assert result_data["conflicts"][0]["matcher"] == "Edit"


@pytest.mark.asyncio
async def test_list_project_rules(mcp, temp_project_dir):
    """Test listing rules from CLAUDE.md files."""
    # Create a CLAUDE.md file with rules
    claude_file = temp_project_dir / "CLAUDE.md"
    with open(claude_file, 'w') as f:
        f.write("""# Project Memory

## Project Rules

- Format Python files with black after editing
- Run tests before committing
- Check for TODO comments

## Other Section

This is not a rule.
""")
    
    async with Client(mcp) as client:
        result = await client.call_tool(
            "list_project_rules",
            {"project_path": str(temp_project_dir)}
        )
        
        result_data = json.loads(result[0].text)
        assert result_data["status"] == "success"
        assert len(result_data["rules"]) == 3
        assert "Format Python files with black after editing" in result_data["rules"]


@pytest.mark.asyncio
async def test_read_examples_resource(mcp):
    """Test reading the examples resource."""
    async with Client(mcp) as client:
        result = await client.read_resource("data://rule2hook/examples")
        
        examples_data = json.loads(result[0].text)
        assert "formatting" in examples_data
        assert "testing" in examples_data
        assert "git" in examples_data
        assert len(examples_data["formatting"]) > 0


@pytest.mark.asyncio
async def test_read_documentation_resource(mcp):
    """Test reading the documentation resource."""
    async with Client(mcp) as client:
        result = await client.read_resource("data://rule2hook/documentation")
        
        doc_text = result[0].text
        assert "Rule2Hook MCP Server Documentation" in doc_text
        assert "install_rule2hook" in doc_text
        assert "convert_rules" in doc_text


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v"])
# Rule2Hook MCP Server 🪝🤖

An MCP (Model Context Protocol) server that helps you install and use the claudecode-rule2hook functionality in your projects. This server provides tools to automate the setup and management of Claude Code hooks through natural language rules.

## 🚀 Features

- **Easy Installation**: Install rule2hook command in any project with a single tool call
- **Rule Conversion**: Convert natural language rules to Claude Code hooks
- **Validation**: Validate hooks.json files for correctness
- **Conflict Detection**: Check for conflicts before merging hooks
- **Project Scanning**: Find existing rules in CLAUDE.md files

## 📦 Installation

### Prerequisites

- Python 3.10+
- FastMCP library

```bash
# Install dependencies
pip install "fastmcp[all]"
```

### Setup

1. Clone this repository:
```bash
git clone https://github.com/zxdxjtu/claudecode-rule2hook.git
cd claudecode-rule2hook
```

2. The MCP server is ready to use!

## 🔧 Usage

### Running the Server

#### For Claude Desktop (stdio transport):
```bash
python rule2hook_mcp_server.py
```

#### For HTTP access:
```bash
python rule2hook_mcp_server.py --http
```

### Configuring Claude Desktop

Add to your Claude Desktop configuration (`claude_desktop_config.json`):

```json
{
  "mcpServers": {
    "rule2hook": {
      "command": "python",
      "args": ["/path/to/claudecode-rule2hook/rule2hook_mcp_server.py"]
    }
  }
}
```

## 🛠️ Available Tools

### 1. `install_rule2hook`

Install the rule2hook command in a project.

**Parameters:**
- `project_path` (string): Path to the project
- `installation_type` (string): "project" or "global"

**Example:**
```python
await client.call_tool("install_rule2hook", {
    "project_path": "/path/to/my/project",
    "installation_type": "project"
})
```

### 2. `convert_rules`

Convert natural language rules into Claude Code hooks.

**Parameters:**
- `rules` (string): Comma-separated rules
- `merge_with_existing` (boolean): Whether to merge with existing hooks

**Example:**
```python
await client.call_tool("convert_rules", {
    "rules": "Format Python files after editing, Run git status when done",
    "merge_with_existing": true
})
```

### 3. `validate_hooks`

Validate a hooks.json file.

**Parameters:**
- `hooks_file_path` (string): Path to hooks.json

**Example:**
```python
await client.call_tool("validate_hooks", {
    "hooks_file_path": "~/.claude/hooks.json"
})
```

### 4. `detect_conflicts`

Check for conflicts between new and existing hooks.

**Parameters:**
- `existing_hooks_path` (string): Path to existing hooks.json
- `new_hooks_json` (string): JSON string of new hooks

**Example:**
```python
await client.call_tool("detect_conflicts", {
    "existing_hooks_path": "~/.claude/hooks.json",
    "new_hooks_json": '{"hooks": {...}}'
})
```

### 5. `list_project_rules`

List rules found in CLAUDE.md files.

**Parameters:**
- `project_path` (string): Path to the project

**Example:**
```python
await client.call_tool("list_project_rules", {
    "project_path": "/path/to/project"
})
```

## 📚 Resources

The server provides two resources:

### `data://rule2hook/examples`
Returns example rules and their conversions, organized by category (formatting, testing, git, validation).

### `data://rule2hook/documentation`
Returns comprehensive documentation for using the rule2hook MCP server.

## 🧪 Testing

Run the test suite:

```bash
pytest test_rule2hook_server.py -v
```

## 💡 Example Workflow

1. **Install rule2hook in your project:**
   ```
   Use install_rule2hook tool with your project path
   ```

2. **List existing rules (if any):**
   ```
   Use list_project_rules to find rules in CLAUDE.md
   ```

3. **Convert rules to hooks:**
   ```
   Use convert_rules with your natural language rules
   ```

4. **Validate the configuration:**
   ```
   Use validate_hooks to ensure correctness
   ```

5. **Check for conflicts (if merging):**
   ```
   Use detect_conflicts before applying new hooks
   ```

## 🎯 Supported Rule Patterns

- **Formatting**: "Format [language] files after editing"
- **Testing**: "Run tests when modifying test files"
- **Git**: "Execute git [command] when [event]"
- **Validation**: "Check/Validate [something] before [action]"
- **Custom**: Use backticks for commands: "Run `npm build` after editing"

## 🔐 Security Notes

- The server runs with full user permissions
- Commands in hooks are executed with shell access
- Always validate commands before adding them to hooks
- Use error handling (`|| true`) to prevent blocking

## 🤝 Contributing

Contributions are welcome! Please ensure:
- All tests pass
- Code follows Python best practices
- Documentation is updated

## 📄 License

MIT License - see the main project LICENSE file.

## 🔗 Related

- [claudecode-rule2hook](https://github.com/zxdxjtu/claudecode-rule2hook) - The main project
- [FastMCP](https://github.com/jlowin/fastmcp) - The MCP framework
- [Claude Desktop](https://claude.ai/desktop) - Claude's desktop application
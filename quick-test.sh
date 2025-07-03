#!/bin/bash

# Strict Mode
set -e
set -u
set -o pipefail

# Color definitions
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Constants
HOOKS_FILE="$HOME/.claude/hooks.json"
BACKUP_FILE="$HOME/.claude/hooks.json.test_backup"
TEST_PY_FILE="temp_test_file.py"

# --- Helper Functions ---

# Function to be called on script exit to ensure cleanup
cleanup() {
    echo -e "\n${YELLOW}Running cleanup...${NC}"
    # Restore original hooks if a backup exists
    if [ -f "$BACKUP_FILE" ]; then
        mv "$BACKUP_FILE" "$HOOKS_FILE"
        echo -e "${GREEN}✓ Restored original hooks.${NC}"
    fi
    # Remove temporary test file
    rm -f "$TEST_PY_FILE"
    echo -e "${GREEN}✓ Removed temporary files.${NC}"
}

# Trap the EXIT signal to run the cleanup function automatically
trap cleanup EXIT

# Function to run a single rule test
run_test() {
    local rule="$1"
    local description="$2"
    local expected_command_part="$3"

    echo -e "\n${YELLOW}▶️  TEST: ${description}${NC}"
    echo "   Rule: \"$rule\""

    # This is the command the user must run manually in Claude Code
    echo -e "   ${GREEN}ACTION: Please run the following in Claude Code and press Enter when done:${NC}"
    echo "   /project:rule2hook \"$rule\""
    read -r

    # Validation Step
    echo "   Validating result..."
    if ! grep -q "$expected_command_part" "$HOOKS_FILE"; then
        echo -e "   ${RED}❌ FAILED: Expected to find command fragment '${expected_command_part}' in hooks file.${NC}"
        # set -e will cause the script to exit here
        exit 1
    fi
    echo -e "   ${GREEN}✓ PASSED: Found expected command in hooks file.${NC}"
}

# Function to validate JSON structure
validate_json() {
    if ! python3 -m json.tool < "$HOOKS_FILE" > /dev/null 2>&1; then
        echo -e "${RED}❌ Invalid JSON in hooks file${NC}"
        return 1
    fi
    return 0
}

# Function to display current hooks summary
display_hooks_summary() {
    echo -e "\n${YELLOW}📋 Current Hooks Summary:${NC}"
    if [ -f "$HOOKS_FILE" ] && validate_json; then
        python3 validate-hooks.py "$HOOKS_FILE" 2>/dev/null || {
            echo -e "${RED}❌ Hooks validation failed${NC}"
            return 1
        }
    else
        echo "   No valid hooks file found"
    fi
}

# --- Main Script ---

main() {
    echo "🧪 claudecode-rule2hook Quick Test Script"
    echo "=========================================="
    
    # Check prerequisites
    if ! command -v python3 &> /dev/null; then
        echo -e "${RED}❌ Python 3 is required but not installed.${NC}"
        exit 1
    fi
    
    if [ ! -f "validate-hooks.py" ]; then
        echo -e "${RED}❌ validate-hooks.py not found in current directory.${NC}"
        exit 1
    fi
    
    # Backup existing hooks
    if [ -f "$HOOKS_FILE" ]; then
        cp "$HOOKS_FILE" "$BACKUP_FILE"
        echo -e "${GREEN}✓ Backed up existing hooks to ${BACKUP_FILE}${NC}"
    fi
    
    # Start with a clean slate
    echo '{"hooks": {}}' > "$HOOKS_FILE"
    echo -e "${GREEN}✓ Initialized empty hooks file${NC}"
    
    echo -e "\n${YELLOW}Preparation:${NC}"
    echo "1. Ensure you are in Claude Code"
    echo "2. Ensure current directory is project directory"
    echo "3. Be ready to copy and paste commands"
    echo ""
    echo "Press Enter to start testing..."
    read -r

    # --- Test Cases ---
    
    # Test 1: Python Formatting
    run_test "Format Python files with black after editing" \
             "Python Formatting Rule" \
             "black"
    
    # Verify hook was added correctly
    display_hooks_summary

    # Test 2: Git Workflow
    run_test "Run git status when finishing a task" \
             "Git Workflow Rule" \
             "git status"
    
    # Test 3: Code Check
    run_test "Check for TODO comments before committing" \
             "Code Check Rule" \
             "TODO"
    
    # Test 4: Complex Command
    run_test "Run 'npm run lint && npm run test' after editing source files" \
             "Complex Command Rule" \
             "npm run lint && npm run test"
    
    # Test 5: Read from CLAUDE.md
    echo -e "\n${YELLOW}▶️  TEST: Read rules from CLAUDE.md${NC}"
    echo -e "   ${GREEN}ACTION: Please run the following in Claude Code and press Enter when done:${NC}"
    echo "   /project:rule2hook"
    read -r
    
    # Validate that hooks were added from CLAUDE.md
    echo "   Validating CLAUDE.md rules..."
    if grep -q "prettier" "$HOOKS_FILE" && grep -q "npm test" "$HOOKS_FILE"; then
        echo -e "   ${GREEN}✓ PASSED: Found hooks from CLAUDE.md${NC}"
    else
        echo -e "   ${RED}❌ FAILED: Expected hooks from CLAUDE.md not found${NC}"
        exit 1
    fi
    
    # --- Conflict Detection Test ---
    
    echo -e "\n${YELLOW}▶️  TEST: Conflict Detection${NC}"
    echo "   Testing pre-merge conflict detection..."
    
    # Create a conflicting hook fragment
    cat > temp_conflict_hook.json <<EOF
{
  "hooks": {
    "PostToolUse": [
      {
        "matcher": "Edit",
        "hooks": [
          {
            "type": "command",
            "command": "echo 'This is a conflicting command'"
          }
        ]
      }
    ]
  }
}
EOF
    
    # Test conflict detection
    if python3 validate-hooks.py "$HOOKS_FILE" temp_conflict_hook.json > /dev/null 2>&1; then
        echo -e "   ${RED}❌ FAILED: Conflict detection should have failed${NC}"
        rm -f temp_conflict_hook.json
        exit 1
    else
        echo -e "   ${GREEN}✓ PASSED: Conflict detection working correctly${NC}"
    fi
    rm -f temp_conflict_hook.json
    
    # --- Final Validation ---
    
    echo -e "\n${GREEN}All tests passed successfully! ✨${NC}"
    echo "Final hooks configuration:"
    
    # Use python -m json.tool for pretty-printing
    if command -v python3 &> /dev/null; then
        python3 -m json.tool < "$HOOKS_FILE" 2>/dev/null || cat "$HOOKS_FILE"
    else
        cat "$HOOKS_FILE"
    fi
    
    # Final validation with our script
    echo -e "\n${YELLOW}Running final validation:${NC}"
    python3 validate-hooks.py "$HOOKS_FILE"
}

# Execute the main function
main
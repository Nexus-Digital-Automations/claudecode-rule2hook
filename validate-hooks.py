#!/usr/bin/env python3
"""
Validate the generated hooks.json file
"""

import json
import sys
from pathlib import Path


def validate_hooks_file(file_path):
    """Validate hooks.json file"""
    print(f"🔍 Validating file: {file_path}")
    print("-" * 50)
    
    # Check if file exists
    if not file_path.exists():
        print("❌ File does not exist")
        return False
    
    # Read and parse JSON
    try:
        with open(file_path, 'r') as f:
            config = json.load(f)
        print("✅ JSON format is valid")
    except json.JSONDecodeError as e:
        print(f"❌ JSON parsing error: {e}")
        return False
    
    # Validate structure
    if not isinstance(config, dict):
        print("❌ Root element must be an object")
        return False
    
    if "hooks" not in config:
        print("❌ Missing 'hooks' key")
        return False
    
    hooks = config["hooks"]
    if not isinstance(hooks, dict):
        print("❌ 'hooks' must be an object")
        return False
    
    # Validate each event type
    valid_events = {"PreToolUse", "PostToolUse", "Stop", "Notification"}
    hook_count = 0
    
    for event, event_hooks in hooks.items():
        if event not in valid_events:
            print(f"⚠️  Unknown event type: {event}")
        
        if not isinstance(event_hooks, list):
            print(f"❌ Value of {event} must be an array")
            return False
        
        print(f"\n📌 {event} ({len(event_hooks)} configurations)")
        
        for i, hook_group in enumerate(event_hooks):
            if not isinstance(hook_group, dict):
                print(f"  ❌ Configuration {i+1} must be an object")
                continue
            
            # Check matcher (optional)
            matcher = hook_group.get("matcher", "")
            if matcher:
                print(f"  Matcher: {matcher}")
            
            # Check hooks array
            if "hooks" not in hook_group:
                print(f"  ❌ Configuration {i+1} missing 'hooks' array")
                continue
            
            hook_list = hook_group["hooks"]
            if not isinstance(hook_list, list):
                print(f"  ❌ 'hooks' must be an array")
                continue
            
            for j, hook in enumerate(hook_list):
                if not isinstance(hook, dict):
                    print(f"    ❌ Hook {j+1} must be an object")
                    continue
                
                # Validate hook type and command
                hook_type = hook.get("type")
                command = hook.get("command")
                
                if hook_type != "command":
                    print(f"    ⚠️  Hook {j+1} type: {hook_type} (expected: command)")
                
                if not command:
                    print(f"    ❌ Hook {j+1} missing command")
                else:
                    print(f"    ✅ Command: {command[:50]}{'...' if len(command) > 50 else ''}")
                    hook_count += 1
    
    print(f"\n📊 Total: {hook_count} hooks")
    print("✅ Validation passed" if hook_count > 0 else "⚠️  No valid hooks found")
    
    return True


def detect_merge_conflicts(existing_path, new_path):
    """
    Simulates a merge and detects potential conflicts.
    Returns True if safe to merge, False if conflicts are found.
    """
    if not existing_path.exists():
        print("✅ No existing hooks file - safe to create new hooks")
        return True

    try:
        with open(existing_path, 'r') as f:
            existing_config = json.load(f)
        with open(new_path, 'r') as f:
            new_config = json.load(f)
    except json.JSONDecodeError as e:
        print(f"❌ JSON parsing error: {e}")
        return False

    existing_hooks = existing_config.get("hooks", {})
    new_hooks = new_config.get("hooks", {})
    
    has_conflicts = False

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
                    has_conflicts = True
                    existing_command = existing_matchers[event][new_matcher]
                    new_command = new_hook_group.get("hooks", [{}])[0].get("command", "")
                    
                    print(f"\n🚨 CONFLICT DETECTED in event '{event}' for matcher '{new_matcher}':")
                    print(f"  - Existing command: \"{existing_command}\"")
                    print(f"  - New conflicting command: \"{new_command}\"")
                    print("  - Aborting merge to prevent overwriting the existing hook.")

    return not has_conflicts


def display_hooks_summary(file_path):
    """Display hooks summary"""
    with open(file_path, 'r') as f:
        config = json.load(f)
    
    print("\n📋 Hooks Summary")
    print("=" * 50)
    
    for event, event_hooks in config.get("hooks", {}).items():
        print(f"\n{event}:")
        for hook_group in event_hooks:
            matcher = hook_group.get("matcher", "All tools")
            for hook in hook_group.get("hooks", []):
                command = hook.get("command", "")
                print(f"  [{matcher}] → {command}")


if __name__ == "__main__":
    if len(sys.argv) == 3:
        # Mode: Pre-merge conflict detection
        existing_hooks_file = Path(sys.argv[1])
        new_hook_fragment_file = Path(sys.argv[2])
        
        print(f"🔬 Performing pre-merge validation...")
        print(f"  - Existing Hooks: {existing_hooks_file}")
        print(f"  - New Hooks: {new_hook_fragment_file}")
        
        if not detect_merge_conflicts(existing_hooks_file, new_hook_fragment_file):
            print("\n❌ Merge conflict detected. Aborting.")
            sys.exit(1)
        else:
            print("\n✅ No merge conflicts found. Safe to merge.")
            
    elif len(sys.argv) == 2:
        # Mode: Standard validation of a single file
        hooks_file = Path(sys.argv[1])
        if validate_hooks_file(hooks_file):
            display_hooks_summary(hooks_file)
        else:
            print("\n❌ Validation failed")
            sys.exit(1)
            
    else:
        print("Usage:")
        print("  - To validate a file: python3 validate-hooks.py <path_to_hooks.json>")
        print("  - To check for merge conflicts: python3 validate-hooks.py <existing_hooks.json> <new_hook_fragment.json>")
        sys.exit(1)
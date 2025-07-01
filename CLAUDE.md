# Project Rules

## Code Quality
- Format Python files with `black` after editing .py files
- Run `prettier --write` on JavaScript and TypeScript files after modifications
- Check for console.log statements before committing JavaScript code

## Development Workflow
- Run `git status` when finishing any task
- Execute `npm test` after modifying files in the tests/ directory
- Clear build cache when .env file is modified

## Security
- Scan for hardcoded API keys before saving configuration files
- Validate environment variables before running deployment scripts
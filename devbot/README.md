# DevBot

**AI Engineering Teammate** - A CLI plugin that attaches to any repository and provides AI-assisted development using OpenSpec and Claude Code.

## Overview

DevBot acts as an intelligent development partner that integrates with your codebase to provide:

- **Project Analysis** - Scan and understand your project's tech stack
- **Code Knowledge Graph** - Build a semantic understanding of your codebase
- **Feature Planning** - Create specifications using OpenSpec format
- **AI-Powered Implementation** - Generate code using Claude Code
- **Task Orchestration** - Execute multi-step workflows with AI agents

## Features

| Feature | Description |
|---------|-------------|
| Project Scanning | Detect languages, frameworks, dependencies |
| Code Graph | Build knowledge graph of files, classes, functions |
| OpenSpec | Create structured feature specifications |
| Task Planning | Generate execution DAGs from specifications |
| Code Generation | AI-powered code implementation |
| Git Integration | Branch creation, commits, patches |
| Telegram Bot | Remote control via Telegram (optional) |

## Installation

```bash
# Clone or navigate to the devbot directory
cd devbot

# Install in development mode
pip install -e .

# Or install dependencies only
pip install -r requirements.txt
```

## Quick Start

```bash
# 1. Attach to your project
devbot attach .

# 2. Scan the project
devbot scan

# 3. Build code graph (optional)
devbot graph

# 4. Create a feature
devbot feature payment-service --description "Handle payment transactions"

# 5. Generate task plan
devbot plan payment-service

# 6. Implement via AI
devbot implement payment-service
```

## CLI Commands

### attach
Attach DevBot to a repository and create project profile.

```bash
devbot attach .                    # Attach to current directory
devbot attach /path/to/project    # Attach to specific path
```

Creates `.devbot/` folder with:
- `project_profile.json` - Project metadata
- `devbot_state.json` - DevBot state
- `code_graph.json` - Code knowledge graph

### scan
Scan project and detect tech stack.

```bash
devbot scan
devbot scan --path /path/to/project
```

Detects:
- Programming languages
- Frameworks (Django, Flask, React, etc.)
- Dependencies
- Configuration files
- Databases
- Tools

### graph
Build a code knowledge graph.

```bash
devbot graph
```

Creates nodes for:
- Files
- Classes
- Functions

Creates edges for:
- Imports
- Dependencies

### feature
Create a new OpenSpec feature specification.

```bash
devbot feature user-auth
devbot feature payment-service --description "Handle payments"
```

Creates: `openspec/features/<feature-name>.md`

### plan
Generate task plan from feature specification.

```bash
devbot plan payment-service
```

Generates:
- Task DAG with parallel execution levels
- Agent assignments (code, test, deploy)

### implement
Implement a feature using AI agents.

```bash
devbot implement payment-service
```

Executes:
1. Reads feature spec and plan
2. Spawns appropriate agents
3. Generates code via Claude Code
4. Creates git branch and commits

### list
List all available features.

```bash
devbot list
```

### status
Show DevBot status.

```bash
devbot status
```

## Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `CLAUDE_MODEL` | Claude model to use | sonnet |
| `TELEGRAM_BOT_TOKEN` | Telegram bot token | - |
| `PROJECT_PATH` | Default project path | . |

### Python Configuration

```python
from devbot import DevBot

config = {
    'tracing': True,
    'openspec_path': './openspec',
    'max_workers': 4,
    'retry_attempts': 3,
    'claude': {
        'model': 'sonnet',
        'cli_path': 'claude'
    },
    'git': {
        'commit_prefix': '[DevBot]'
    }
}

bot = DevBot('./my-project', config)
```

## OpenSpec Format

Features are stored as markdown files:

```markdown
# Feature: payment-service

## Overview
Payment service for handling transactions

## Version
1.0.0

## Status
draft

## Tasks

### Phase 1: Design
- [ ] Design API endpoints
- [ ] Define data models

### Phase 2: Implementation
- [ ] Implement core functionality

### Phase 3: Testing
- [ ] Write unit tests
- [ ] Write integration tests

### Phase 4: Deployment
- [ ] Deploy to staging
- [ ] Deploy to production

## Dependencies

## Notes
```

## Architecture

DevBot is built with a modular architecture:

```
devbot/
├── cli/              # Click-based CLI
├── core/             # Main DevBot orchestrator
├── scanner/          # Project analysis
├── graph/            # Code knowledge graph
├── spec/             # OpenSpec management
├── agents/           # AI agents
├── orchestrator/     # Task execution
├── tools/            # Tool wrappers
├── integrations/     # External services
├── memory/           # Context memory
└── observability/   # Logging & tracing
```

See [ARCHITECTURE.md](./ARCHITECTURE.md) for detailed architecture documentation.

## Requirements

- Python 3.8+
- Git
- Claude Code CLI (for AI features)

### Optional

- python-telegram-bot (for Telegram integration)
- pytest (for testing)

## Development

```bash
# Run tests
pytest

# Run CLI directly
python -m devbot.cli.devbot_cli --help

# Run in verbose mode
python -m devbot.cli.devbot_cli scan -v
```

## License

MIT License

## Author

DevBot Team

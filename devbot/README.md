# DevBot

AI Engineering Teammate - A CLI plugin that attaches to any repository and provides AI-assisted development using OpenSpec and Claude Code.

## Features

- **Attach to any repository** - Initialize DevBot in any project
- **Project scanning** - Detect tech stack, frameworks, and dependencies
- **Code graph building** - Build knowledge graph of your codebase
- **OpenSpec integration** - Create feature specifications
- **AI Planning** - Generate task DAGs from specifications
- **Code generation** - Use Claude Code to generate implementation
- **Git integration** - Automatic branch creation and commits

## Installation

```bash
pip install -e .
```

Or from PyPI (when published):

```bash
pip install devbot
```

## Quick Start

```bash
# Attach to a project
devbot attach .

# Scan the project
devbot scan

# Build code graph
devbot graph

# Create a feature
devbot feature payment-service

# Plan a feature
devbot plan payment-service

# Implement a feature
devbot implement payment-service
```

## Commands

| Command | Description |
|---------|-------------|
| `devbot attach <path>` | Attach DevBot to a repository |
| `devbot scan` | Scan project and detect stack |
| `devbot graph` | Build code knowledge graph |
| `devbot feature <name>` | Create a new feature spec |
| `devbot plan <name>` | Generate task plan from spec |
| `devbot implement <name>` | Implement feature via AI |
| `devbot status` | Show DevBot status |

## Configuration

DevBot can be configured via environment variables:

- `CLAUDE_MODEL` - Claude model to use (default: sonnet)
- `TELEGRAM_BOT_TOKEN` - Telegram bot token (optional)

## OpenSpec Integration

DevBot uses OpenSpec for feature specifications. Features are stored in:

```
openspec/
  features/
    payment-service.md
  plans/
    payment-service-plan.md
```

## Project Structure

```
devbot/
  cli/           # Command-line interface
  core/          # Main DevBot class
  scanner/      # Project scanning
  graph/        # Code graph building
  spec/         # OpenSpec integration
  agents/       # AI agents (planner, code, test, deploy)
  orchestrator/ # Task execution
  tools/        # Tool wrappers (Claude CLI, Git)
  integrations/ # Telegram bot
  memory/       # Short/long-term memory
  observability/ # Logging and tracing
```

## Development

```bash
# Install in development mode
pip install -e .

# Run tests
pytest

# Run with verbose output
devbot --help
```

## License

MIT License

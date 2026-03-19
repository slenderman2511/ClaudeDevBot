# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**ClaudeDevBot** (`claudebot/`) — Unified AI development assistant combining CLI tooling and FastAPI plugin system.

- **CLI**: `claudebot init`, `scan`, `graph`, `feature`, `plan`, `implement`, `config`, `status`
- **API**: FastAPI server with REST/WebSocket endpoints, SQLite task DB, rate limiting, auth
- **Agents**: Async agents for spec, code, test, deploy, debug, and planning
- **Telegram**: Built-in Telegram bot integration

## Installation

```bash
pip install -e ./claudebot
```

## CLI Commands

```bash
claudebot init                     # Full setup: scan + graph (interactive)
claudebot --path <dir> init        # Init a specific directory

claudebot scan                     # Detect tech stack → .devbot/project_profile.json
claudebot graph                    # Build code graph → .devbot/code_graph.json

claudebot feature <name>           # Create OpenSpec feature
claudebot feature <name> -d "desc" # Create with description
claudebot plan <name>              # Generate task plan from feature
claudebot implement <name>         # Implement feature via AI agents

claudebot config --list            # Show all config
claudebot config --get key        # Get specific key
claudebot config --set key val    # Set a value
claudebot status                   # Show DevBot status

claudebot serve --port 8765       # Start FastAPI server
claudebot run code "task desc"    # Run a task directly (spec|code|test|deploy|debug)
```

## Architecture

```
claudebot/
├── cli.py                         # Unified CLI (main entry point)
├── cli_commands/                  # devbot-style command implementations
├── api/                           # FastAPI server + routes
│   ├── server.py                  # App factory
│   └── routes/ (health, tasks, telegram, websocket)
├── agents/                        # Async agents
│   ├── base_agent.py              # AgentContext, AgentResult dataclasses
│   ├── code_agent.py              # Multi-file code generation
│   ├── spec_agent.py              # Spec generation
│   ├── test_agent.py              # Test generation
│   ├── deploy_agent.py            # Deployment
│   ├── debug_agent.py             # Debug assistance
│   ├── planner_agent.py           # Task graph planning (from devbot)
│   └── task_graph.py              # DAG planning (from devbot)
├── scanner/                       # Project analysis (from devbot)
│   ├── project_scanner.py
│   └── stack_detector.py
├── graph/                         # Code knowledge graph (from devbot)
│   ├── code_graph_builder.py
│   └── symbol_parser.py
├── spec/                          # OpenSpec management (from devbot)
│   ├── openspec_sync.py
│   └── spec_generator.py
├── observability/                 # Structured logging (from devbot)
│   ├── logger.py                  # get_logger(), configure_logging()
│   └── tracing.py
├── memory/                        # Memory (from devbot)
│   ├── memory.py
│   ├── short_term_memory.py
│   └── long_term_memory.py
├── tools/                         # Tool wrappers
│   ├── claude_cli.py              # ClaudeCLITool (async)
│   ├── git_tools.py               # GitTool (richer)
│   └── tool.py, tool_registry.py
├── db/                            # SQLite task DB
├── orchestrator/                  # Task execution
│   ├── task_manager.py            # (claudebot)
│   └── executor.py                # (from devbot)
├── config.py                      # YAML + .claudebotrc config
├── config.yaml                    # Default config
└── pyproject.toml                  # Dependencies
```

## Workspace Structure

When `claudebot init` runs in a project:
```
project/
├── .devbot/
│   ├── config.yaml           # Configuration
│   ├── project_profile.json   # Scan results (language, stack)
│   ├── code_graph.json       # Knowledge graph (426 nodes)
│   └── devbot_state.json     # State
├── openspec/
│   ├── features/             # Feature specs
│   ├── context/              # Project context
│   └── plans/               # Task plans
```

## Environment Variables

```bash
export CLAUDE_API_KEY="your-key"
export TELEGRAM_BOT_TOKEN="optional"
export GITHUB_TOKEN="optional"
export CLAUDE_MODEL="claude-sonnet"
```

## Running Tests

```bash
pytest ./claudebot/ -v
```
